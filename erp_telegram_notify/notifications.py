import frappe
from frappe.utils import escape_html, get_url_to_form

from erp_telegram_notify import telegram

CACHE_KEY = "tg_notify_rules"
RULE_DT = "Telegram Notification Rule"

EVENT_WORKFLOW = "Workflow Action Required"
EVENT_NEW = "New Document"
EVENT_SUBMIT = "On Submit"

# which hook method fires which rule type
METHOD_FOR_EVENT = {
    EVENT_WORKFLOW: "on_update",
    EVENT_NEW: "after_insert",
    EVENT_SUBMIT: "on_submit",
}
EVENT_TEXT = {
    EVENT_WORKFLOW: "needs your action",
    EVENT_NEW: "was created",
    EVENT_SUBMIT: "was submitted",
}


# ---------- rule cache ----------
def get_rules():
    rules = frappe.cache().get_value(CACHE_KEY)
    if rules is None:
        rules = {}
        if frappe.db.table_exists(RULE_DT):
            for name in frappe.get_all(RULE_DT, filters={"enabled": 1}, pluck="name"):
                r = frappe.get_doc(RULE_DT, name)
                rules.setdefault(r.document_type, []).append(
                    {
                        "name": r.name,
                        "event": r.event,
                        "condition": r.condition,
                        "roles": [d.role for d in r.roles],
                    }
                )
        frappe.cache().set_value(CACHE_KEY, rules)
    return rules


def clear_rules_cache():
    frappe.cache().delete_value(CACHE_KEY)


# ---------- hook entry point (runs for EVERY doctype save) ----------
def handle(doc, method=None):
    flags = frappe.flags
    if flags.in_install or flags.in_migrate or flags.in_patch or flags.in_import:
        return

    rules = get_rules().get(doc.doctype)
    if not rules:
        return  # no rule for this doctype -> nothing to do (cheap exit)

    for rule in rules:
        if METHOD_FOR_EVENT.get(rule["event"]) != method:
            continue
        if rule["event"] == EVENT_WORKFLOW and (
            not doc.get("workflow_state") or not doc.has_value_changed("workflow_state")
        ):
            continue
        if rule["condition"]:
            try:
                if not frappe.safe_eval(rule["condition"], None, {"doc": doc}):
                    continue
            except Exception:
                frappe.log_error(title=f"Telegram rule {rule['name']}: bad condition")
                continue

        # Queue it so a slow Telegram call never blocks saving the document
        frappe.enqueue(
            "erp_telegram_notify.notifications.process_rule",
            queue="short",
            enqueue_after_commit=True,
            rule_name=rule["name"],
            doctype=doc.doctype,
            name=doc.name,
            triggered_by=frappe.session.user,
        )


# ---------- background job ----------
def process_rule(rule_name, doctype, name, triggered_by):
    rule = frappe.get_doc(RULE_DT, rule_name)
    if not rule.enabled:
        return
    doc = frappe.get_doc(doctype, name)

    users = frappe.get_all(
        "User",
        filters={"enabled": 1, "telegram_chat_id": ["is", "set"]},
        fields=["name", "telegram_chat_id"],
    )

    transitions = []
    if rule.event == EVENT_WORKFLOW:
        wf = frappe.db.get_value("Workflow", {"document_type": doctype, "is_active": 1})
        if not wf:
            return
        transitions = frappe.get_all(
            "Workflow Transition",
            filters={"parent": wf, "state": doc.workflow_state},
            fields=["action", "allowed"],
        )
        if not transitions:
            return  # end state, nobody to ask
    else:
        wanted_roles = {d.role for d in rule.roles}

    text = _build_text(rule, doc)

    for u in users:
        roles = set(frappe.get_roles(u.name))
        buttons = None

        if rule.event == EVENT_WORKFLOW:
            actions = [t.action for t in transitions if t.allowed in roles]
            if not actions:
                continue
            buttons = [(a, _make_button(u.name, doctype, name, a)) for a in actions]
        else:
            if not (roles & wanted_roles) or u.name == triggered_by:
                continue

        # never leak a document to someone who can't read it in ERPNext
        if not frappe.has_permission(doctype, "read", doc=doc, user=u.name):
            continue

        try:
            telegram.send_message(u.telegram_chat_id, text, buttons)
        except Exception:
            frappe.log_error(title=f"Telegram send failed for {u.name}")


def _make_button(user, doctype, name, action):
    # callback_data is limited to 64 bytes, so store details server-side
    token = frappe.generate_hash(length=10)
    frappe.cache().set_value(
        f"tg_cb:{token}",
        {"user": user, "doctype": doctype, "name": name, "action": action},
        expires_in_sec=7 * 24 * 3600,
    )
    return f"wf|{token}"


def _build_text(rule, doc):
    link = get_url_to_form(doc.doctype, doc.name)
    if rule.message:
        return frappe.render_template(rule.message, {"doc": doc, "link": link})
    lines = [
        f"<b>{escape_html(doc.doctype)}</b> <a href=\"{link}\">{escape_html(doc.name)}</a> "
        f"{EVENT_TEXT[rule.event]}",
    ]
    if doc.get("workflow_state"):
        lines.append(f"Status: {escape_html(doc.workflow_state)}")
    lines.append(f"By: {escape_html(doc.owner)}")
    return "\n".join(lines)
