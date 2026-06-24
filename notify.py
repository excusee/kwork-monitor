"""
Отправляет в Telegram уведомления о новых релевантных заказах с готовым черновиком
отклика. Сам не отправляет ничего на Kwork — только уведомляет, отклик отправляет
человек вручную.
"""
import json
import os
import sys

import requests

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"


def send_message(text: str) -> None:
    resp = requests.post(
        API_URL,
        data={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout=20,
    )
    resp.raise_for_status()


def format_card(card: dict) -> str:
    return (
        f"🆕 {card['title']}\n"
        f"💰 {card['budget']}\n"
        f"🔗 {card['url']}\n\n"
        f"Черновик отклика:\n{card['draft']}"
    )


def run(cards: list[dict]) -> None:
    if not cards:
        return
    for card in cards:
        send_message(format_card(card))


if __name__ == "__main__":
    cards = json.load(sys.stdin)
    run(cards)
