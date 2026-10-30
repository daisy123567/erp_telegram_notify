frappe.ui.form.on("Telegram Notification Settings", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Check Connection"), () => {
			frappe.call({ method: "erp_telegram_notify.api.check_connection", freeze: true }).then((r) => {
				const d = r.message;
				frappe.msgprint(
					`<b>Bot:</b> @${d.bot}<br><b>Webhook:</b> ${d.webhook_url}<br>` +
					`<b>Pending updates:</b> ${d.pending}<br><b>Last error:</b> ${d.last_error}`
				);
			});
		});

		frm.add_custom_button(__("Reconnect"), () => {
			frappe.call({ method: "erp_telegram_notify.api.register_webhook", freeze: true }).then((r) => {
				frappe.msgprint(r.message);
				frm.reload_doc();
			});
		});

		frm.add_custom_button(__("Send Test to Me"), () => {
			frappe.call({ method: "erp_telegram_notify.api.send_test", freeze: true }).then(() => {
				frappe.show_alert({ message: __("Test message sent"), indicator: "green" });
			});
		});
	},
});
