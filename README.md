# erp_telegram_notify

Telegram notifications and approvals for ERPNext / Frappe.

- Send Telegram messages when documents are created, submitted, or need approval.
- Approvers get **Approve / Reject** buttons directly in Telegram.
- Rule-driven: add any document type from the ERPNext UI. No code changes needed.

Requires Frappe / ERPNext **v15**.

## Install

Run on your Frappe server, in the bench folder.

```bash
cd ~/frappe-bench
bench get-app git@github.com:daisy123567/erp_telegram_notify.git --branch main
bench --site <yoursite> install-app erp_telegram_notify
bench --site <yoursite> migrate
bench build --app erp_telegram_notify
bench restart
```

This is a private repo, so the server needs access. Generate a key on the server
(`ssh-keygen -t ed25519`), then add the contents of `~/.ssh/id_ed25519.pub` to the repo
under **Settings -> Deploy keys** (leave write access off). Test with `ssh -T git@github.com`.

Take a backup before installing on any real system:

```bash
bench --site <yoursite> backup --with-files
```

## Setup

1. **Create the bot:** Telegram -> @BotFather -> `/newbot`. Copy the token.
2. **Add keys** to `sites/<yoursite>/site_config.json`, then run `bench restart`:
   ```json
   "telegram_bot_token": "123456:ABC...",
   "telegram_webhook_secret": "any-long-random-string"
   ```
3. **Register the webhook** (the site must be reachable over public HTTPS):
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/setWebhook" \
     -d "url=https://<yoursite>/api/method/erp_telegram_notify.api.webhook" \
     -d "secret_token=<same secret as site_config>"
   ```
   Check it with `https://api.telegram.org/bot<TOKEN>/getWebhookInfo`.
4. **Link each user:** open your own **User** page -> **Link Telegram** -> send the shown
   `/start CODE` to the bot within 10 minutes.
5. **Create rules:** open **Telegram Notification Rule** -> New, for example:
   - Document Type: `Material Request`
   - Notify When: `Workflow Action Required`

   Add one rule per document type.

## Rule types

| Notify When | Who is notified | Buttons |
|---|---|---|
| Workflow Action Required | Users whose role can act on the current workflow state (needs an active Workflow on that doctype) | Approve / Reject (workflow actions) |
| New Document | Roles you list | No |
| On Submit | Roles you list | No |

Optional per rule:
- **Condition** (Python), for example `doc.grand_total > 10000`
- **Custom Message** (Jinja + Telegram HTML), for example `<b>{{ doc.name }}</b> from {{ doc.owner }}`

## Notes

- Users only receive notifications for documents they have read permission on.
- Background workers must be running (`bench start` in dev, supervisor in production).
- Telegram cannot reach localhost. For local testing use a tunnel (ngrok / cloudflared).
  Without a public HTTPS URL, notifications still send but the buttons will not work.
- Use a separate bot for testing and production. A bot can only have one webhook.
- Never commit your bot token or webhook secret. They belong only in `site_config.json`.

## Updating

```bash
cd ~/frappe-bench/apps/erp_telegram_notify
git pull origin main
cd ~/frappe-bench
bench --site <yoursite> migrate
bench build --app erp_telegram_notify
bench restart
```

## Troubleshooting

- No messages: check **Error Log** and **RQ Job** in ERPNext, and confirm workers are running.
- Buttons do nothing: check `getWebhookInfo` for errors and confirm the secret matches `site_config.json`.
- A user gets nothing: confirm their User record has a Telegram Chat ID, they have the required role,
  and they can read the document.
- "Not possible" on a button: the document was already actioned by someone else, or the button expired (7 days).

## Uninstalling

Take a backup first:

```bash
bench --site <yoursite> backup --with-files
```

**Quick off switch (no uninstall):** untick **Enabled** on each Telegram Notification Rule, or delete
the rules. Nothing will be sent and nothing else changes.

**Full uninstall:**

```bash
bench --site <yoursite> uninstall-app erp_telegram_notify
bench remove-app erp_telegram_notify      # optional: removes the code from apps/
bench --site <yoursite> clear-cache
bench restart
```

This deletes the Telegram Notification Rule and Telegram Rule Role DocTypes, including any rules created.

**Clean up leftovers.** The custom field `Telegram Chat ID` on User may remain. Delete it under
**Customize Form -> User**, or in `bench --site <yoursite> console`:

```python
frappe.delete_doc("Custom Field", "User-telegram_chat_id")
frappe.db.commit()
```

Stop Telegram from contacting the server, and remove the keys from `site_config.json`:

```bash
curl "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
```

**If the site breaks:**
1. Run the `uninstall-app` command above from the terminal.
2. If that fails, comment out the `doc_events` block in
   `apps/erp_telegram_notify/erp_telegram_notify/hooks.py` and run `bench restart`.
3. As a last resort, restore your backup:
   `bench --site <yoursite> restore <database.sql.gz>`
   (backups are in `sites/<yoursite>/private/backups/`).