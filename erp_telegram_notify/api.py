import frappe
from frappe.model.workflow import apply_workflow

from erp_telegram_notify import telegram


@frappe.whitelist()
def generate_link_code():
    """Called from the 'Link Telegram' button on the logged-in user's own User form."""
    code = frappe.generate_hash(length=8)
    frappe.cache().set_value(f"tg_link:{code}", frappe.session.user, expires_in_sec=600)
    return code


@frappe.whitelist(allow_guest=True)
def webhook():
    # Telegram sends our secret in this header (set via setWebhook secret_token)
    secret = frappe.request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not secret or secret != frappe.conf.get("telegram_webhook_secret"):
        frappe.throw("Forbidden", frappe.PermissionError)

    update = frappe.request.get_json() or {}
    if "message" in update:
        _handle_message(update["message"])
    elif "callback_query" in update:
        _handle_callback(update["callback_query"])
    return "ok"


def _handle_message(msg):
    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()
    if not text.startswith("/start"):
        return
    parts = text.split()
    if len(parts) < 2:
        telegram.send_message(chat_id, "Use the 'Link Telegram' button in ERPNext to get your code.")
        return
    code = parts[1]
    user = frappe.cache().get_value(f"tg_link:{code}")
    if not user:
        telegram.send_message(chat_id, "Code invalid or expired. Generate a new one in ERPNext.")
        return
    frappe.db.set_value("User", user, "telegram_chat_id", str(chat_id))
    frappe.cache().delete_value(f"tg_link:{code}")
    telegram.send_message(chat_id, f"Linked to ERPNext user <b>{user}</b>. You'll get notifications here.")


def _handle_callback(cb):
    chat_id = cb["message"]["chat"]["id"]
    message_id = cb["message"]["message_id"]

    # Identify the ERP user from the chat id - never trust anything in the payload
    user = frappe.db.get_value("User", {"telegram_chat_id": str(chat_id), "enabled": 1})
    if not user:
        telegram.answer_callback(cb["id"], "Your Telegram is not linked to an ERP user.")
        return

    try:
        token = cb["data"].split("|", 1)[1]
        data = frappe.cache().get_value(f"tg_cb:{token}")
        if not data or data["user"] != user:
            telegram.answer_callback(cb["id"], "This button has expired.")
            return

        frappe.set_user(user)  # act with that user's permissions
        doc = frappe.get_doc(data["doctype"], data["name"])
        apply_workflow(doc, data["action"])  # enforces workflow role + doc permissions
        frappe.cache().delete_value(f"tg_cb:{token}")

        telegram.edit_message(
            chat_id, message_id,
            f"{data['doctype']} {data['name']}: <b>{data['action']}</b> done by {user}",
        )
        telegram.answer_callback(cb["id"], f"{data['action']} done")
    except Exception as e:
        frappe.db.rollback()
        # most common reason: someone else already actioned it
        telegram.answer_callback(cb["id"], f"Not possible: {str(e)[:150]}")
