"""
Отправляет сгенерированный черновик в Telegram реплаем на оригинальное уведомление.
Вызывается из draft_on_demand.yml после draft.py.
"""
import html
import json
import os
import sys

import requests

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
REPLY_TO = os.environ.get("REPLY_TO_MESSAGE_ID", "").strip()

API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"


def run(cards: list[dict]) -> None:
    for card in cards:
        draft = card.get("draft", "")
        if not draft:
            continue

        payload = {
            "chat_id": CHAT_ID,
            "text": f"✍️ Черновик отклика:\n<blockquote>{html.escape(draft)}</blockquote>",
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "reply_markup": {
                "inline_keyboard": [[{"text": "🔗 Перейти к заказу", "url": card["url"]}]]
            },
        }
        if REPLY_TO:
            payload["reply_to_message_id"] = int(REPLY_TO)

        resp = requests.post(API_URL, json=payload, timeout=20)
        resp.raise_for_status()


if __name__ == "__main__":
    cards = json.load(sys.stdin)
    run(cards)
