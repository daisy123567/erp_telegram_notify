# erp_telegram_notify - setup

1. Create the bot: Telegram -> @BotFather -> /newbot. Copy the token.
2. Create the app. When asked for the app title, use exactly:  Erp Telegram Notify
   (the DocTypes in this zip belong to the module "Erp Telegram Notify")
     cd frappe-bench
     bench new-app erp_telegram_notify
   Then copy the files from this zip into apps/erp_telegram_notify/ keeping the folder
   layout. MERGE hooks.py (don't overwrite the generated one).
3. Add to sites/<yoursite>/site_config.json:
     "telegram_bot_token": "123456:ABC...",
     "telegram_webhook_secret": "any-long-random-string"
4. Install and build:
     bench --site <yoursite> install-app erp_telegram_notify
     bench --site <yoursite> migrate
     bench build --app erp_telegram_notify
     bench restart
5. Register the webhook (site MUST be public HTTPS):
     curl "https://api.telegram.org/bot<TOKEN>/setWebhook" \
       -d "url=https://<yoursite>/api/method/erp_telegram_notify.api.webhook" \
       -d "secret_token=<same secret as site_config>"
6. Each user: open their own User page -> "Link Telegram" -> send the shown
   /start CODE to the bot.
7. In ERPNext open "Telegram Notification Rule" -> New:
     Document Type: Material Request
     Notify When:   Workflow Action Required
   Add one rule per document type. No code changes needed after this.

Rule types
- Workflow Action Required: needs an active Workflow on that doctype. Recipients are
  derived from the workflow roles for the current state; they get Approve/Reject buttons.
- New Document / On Submit: notify the roles you list (no buttons).
- Optional Condition (Python, e.g. doc.grand_total > 10000) and custom Jinja message.

Notes
- Users only receive notifications for documents they have read permission on.
- Background workers must be running (bench start / supervisor).
- Telegram can't reach localhost; use a tunnel (ngrok/cloudflared) for local testing.
