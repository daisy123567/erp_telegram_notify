import frappe
import requests


def _api(method, payload):
    token = frappe.conf.get("telegram_bot_token")
    if not token:
        frappe.throw("telegram_bot_token is missing in site_config.json")
    r = requests.post(
        f"https://api.telegram.org/bot{token}/{method}", json=payload, timeout=10
    )
    r.raise_for_status()
    return r.json()


def send_message(chat_id, text, buttons=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if buttons:
        # buttons: list of (label, callback_data), one per row
        payload["reply_markup"] = {
            "inline_keyboard": [[{"text": l, "callback_data": d}] for l, d in buttons]
        }
    return _api("sendMessage", payload)


def edit_message(chat_id, message_id, text):
    return _api(
        "editMessageText",
        {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"},
    )


def answer_callback(callback_id, text):
    return _api("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})
