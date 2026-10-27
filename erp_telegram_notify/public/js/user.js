frappe.ui.form.on("User", {
	refresh(frm) {
		if (frm.doc.name !== frappe.session.user) return;
		frm.add_custom_button(__("Link Telegram"), () => {
			frappe.call("erp_telegram_notify.api.generate_link_code").then((r) => {
				frappe.msgprint(
					`Open the company bot in Telegram and send:<br><b>/start ${r.message}</b><br>(valid for 10 minutes)`
				);
			});
		});
	},
});
