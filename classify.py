"""
Бесплатный смысловой фильтр кандидатов от monitor.py через Groq API
(бесплатный тариф, без карты, ~1000 запросов/день — с запасом покрывает
наш реальный расход). Понимает смысл, а не буквы — переживает любые
опечатки/жаргон/перефразировки заказчика без ручного словаря синонимов.
Только то, что Groq сочтёт релевантным, идёт дальше на Claude (draft.py)
для финальной проверки и написания черновика.
"""
import json
import os
import sys

import requests

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

PROMPT_TEMPLATE = """Заказ с биржи фриланса Kwork:
Заголовок: {title}
Описание: {description}

Вопрос: относится ли этот заказ к ДИЗАЙНУ карточек/изображений товаров или \
объявлений ИМЕННО для размещения НА КОНКРЕТНОЙ площадке-маркетплейсе или доске \
объявлений (Wildberries, Ozon, Авито и подобные, под любым названием и с любыми \
опечатками) — включая инфографику, баннеры и оформление на странице товара, \
в поиске/каталоге самой площадки, а также AI-генерацию изображений/визуалов для \
этой же цели?

ОТНОСИТСЯ, если место размещения — сама площадка маркетплейса (например "баннер \
в поиске на WB", "карточка для Ozon", "обложка для объявления на Авито").

НЕ ОТНОСИТСЯ: копирайт/наполнение текстом, SEO/продвижение, разработка сайтов, \
дизайн НЕ для товаров/маркетплейсов (логотипы кафе, веб-дизайн и т.п.), \
видеомонтаж, а также рекламные креативы/баннеры для ВНЕШНИХ рекламных сетей \
и соцсетей (Яндекс Директ, РСЯ, ВКонтакте, таргет и т.п.), НЕ привязанные \
к конкретному маркетплейсу — даже если в описании есть слово "баннер" \
или "креатив".

Ответь СТРОГО одним словом: YES или NO."""


def ask_groq(prompt: str) -> str:
    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 5,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip().upper()


def run(candidates: list[dict]) -> list[dict]:
    relevant = []
    for card in candidates:
        prompt = PROMPT_TEMPLATE.format(
            title=card["title"], description=card["description"]
        )
        try:
            answer = ask_groq(prompt)
        except Exception as e:
            # Если Groq недоступен — пропускаем заказ дальше на Claude, а не теряем
            # его молча (Claude всё равно сделает финальную проверку релевантности).
            print(f"Groq недоступен для {card['id']}: {e}", file=sys.stderr)
            relevant.append(card)
            continue

        if answer.startswith("YES"):
            relevant.append(card)
    return relevant


if __name__ == "__main__":
    candidates = json.load(sys.stdin)
    result = run(candidates)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
