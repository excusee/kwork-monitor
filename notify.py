"""
Отправляет в Telegram уведомления о новых релевантных заказах с готовым черновиком
отклика. Сам не отправляет ничего на Kwork — только уведомляет, отклик отправляет
человек вручную.

Черновик оформлен как code-block (тап = копирование целиком, без лимита в 256
символов, который есть у кнопки copy_text). Кнопка "Перейти к заказу" открывает
страницу проекта. Если человек хочет поправить текст — копирует код-блок, редактирует
и отправляет Reply на это же сообщение бота; отдельный Cloudflare Worker-вебхук
(cloudflare-worker/webhook.js) подхватывает Reply, достаёт ссылку на заказ из текста
исходного сообщения и прикрепляет такую же кнопку к отредактированному сообщению.
"""
import html
import json
import os
import sys

import requests

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"


def send_message(text: str, url: str) -> None:
    resp = requests.post(
        API_URL,
        json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "reply_markup": {
                "inline_keyboard": [[{"text": "🔗 Перейти к заказу", "url": url}]]
            },
        },
        timeout=20,
    )
    resp.raise_for_status()


def format_card(card: dict) -> str:
    draft_html = html.escape(card["draft"])
    return (
        f"🆕 {html.escape(card['title'])}\n"
        f"💰 {html.escape(card['budget'])}\n"
        f"🔗 {html.escape(card['url'])}\n\n"
        f"Черновик отклика (тапни — скопируется целиком):\n"
        f"<pre>{draft_html}</pre>"
    )


def run(cards: list[dict]) -> None:
    if not cards:
        return
    for card in cards:
        send_message(format_card(card), card["url"])


if __name__ == "__main__":
    cards = json.load(sys.stdin)
    run(cards)
