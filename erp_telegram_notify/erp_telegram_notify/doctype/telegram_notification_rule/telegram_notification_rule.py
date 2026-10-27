import frappe
from frappe.model.document import Document

from erp_telegram_notify.notifications import EVENT_WORKFLOW, clear_rules_cache


class TelegramNotificationRule(Document):
    def validate(self):
        meta = frappe.get_meta(self.document_type)
        if meta.istable or self.document_type == self.doctype:
            frappe.throw("Choose a normal document type (not a child table or this rule doctype).")

        if self.event != EVENT_WORKFLOW and not self.roles:
            frappe.throw("Add at least one role to notify.")

        if self.event == EVENT_WORKFLOW and not frappe.db.exists(
            "Workflow", {"document_type": self.document_type, "is_active": 1}
        ):
            frappe.msgprint(
                f"There is no active Workflow for {self.document_type} yet. "
                "Nothing will be sent until you create one.",
                indicator="orange",
            )

        if self.condition:
            try:
                compile(self.condition, "<condition>", "eval")
            except SyntaxError as e:
                frappe.throw(f"Condition is not valid Python: {e}")

    def on_update(self):
        clear_rules_cache()

    def on_trash(self):
        clear_rules_cache()
