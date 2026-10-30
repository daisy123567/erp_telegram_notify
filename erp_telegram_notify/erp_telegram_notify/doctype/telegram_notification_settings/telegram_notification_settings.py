import frappe
from frappe.model.document import Document
from frappe.utils import get_url


class TelegramNotificationSettings(Document):
    def validate(self):
        if not self.webhook_secret:
            self.webhook_secret = frappe.generate_hash(length=32)
        if not self.site_url:
            self.site_url = get_url()
        self.site_url = self.site_url.strip().rstrip("/")
        if (
            self.enabled
            and self.connection_mode == "Webhook"
            and not self.site_url.startswith("https://")
        ):
            frappe.msgprint(
                "Webhook mode needs a public https:// address. Set Public Site URL to your "
                "https domain, or switch Connection Mode to Polling.",
                indicator="orange",
            )

    def on_update(self):
        if not self.enabled:
            return
        from erp_telegram_notify.api import apply_connection

        try:
            apply_connection(self)
        except Exception as e:
            self.status = f"Not connected: {e}"
            frappe.db.set_single_value(self.doctype, "status", self.status)
            frappe.msgprint(f"Could not connect to Telegram: {e}", indicator="red")
