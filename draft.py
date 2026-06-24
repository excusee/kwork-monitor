"""
Для каждого кандидата от monitor.py просит Claude (через claude CLI, на Pro-подписке)
оценить релевантность и, если заказ подходит, написать черновик персонализированного
отклика. Не подходящие заказы отбрасываются здесь же (второй, более надёжный фильтр
после простого keyword-отсева в monitor.py).
"""
import json
import subprocess
import sys

BRIEF = """
Контекст обо мне (используй при написании отклика, не упоминай это как "бриф"):
- Я дизайнер карточек маркетплейсов (Wildberries, Ozon) с собственной стилистикой
  + сильной экспертизой в нейросетях (AI-генерация изображений, промпт-инжиниринг).
- Моё УТП: анализирую конкурентов в нише клиента и пишу более продающие тексты
  для карточек; через нейросети делаю визуалы, которые обычный дизайнер за 500-3000₽
  не сделает или сделает хуже.
- Тон: уверенный, конкретный, без воды и без "шаблонных" фраз типа "буду рад сотрудничеству".
  Сразу по делу: что конкретно сделаю и почему это даст результат именно под этот заказ.
"""

PROMPT_TEMPLATE = """{brief}

Вот заказ с биржи Kwork:
Заголовок: {title}
Бюджет: {budget}
Описание: {description}

Задача:
1. Оцени, действительно ли это заказ на ДИЗАЙН карточек/объявлений товаров или услуг
   для маркетплейсов и досок объявлений (Wildberries, Ozon, Авито и подобные)
   или AI-генерацию изображений/визуалов в этой тематике (не копирайт, не SEO,
   не разработка, не случайное совпадение по ключевым словам).
2. Если НЕ подходит — ответь ровно одним словом: NOT_RELEVANT
3. Если подходит — напиши короткий персонализированный отклик (4-7 предложений,
   на русском) от первого лица конкретно под ЭТОТ заказ: что сделаю, как именно
   решу его задачу, почему через меня это будет лучше/быстрее. Без приветствий
   типа "Здравствуйте, увидел ваш заказ" — сразу по делу. Без markdown, чистый текст.

Ответ дай ТОЛЬКО текстом отклика (или ровно NOT_RELEVANT), без пояснений.
"""


def ask_claude(prompt: str) -> str:
    result = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {result.stderr}")
    return result.stdout.strip()


def run(candidates: list[dict]) -> list[dict]:
    drafted = []
    for card in candidates:
        prompt = PROMPT_TEMPLATE.format(
            brief=BRIEF,
            title=card["title"],
            budget=card["budget"],
            description=card["description"],
        )
        try:
            response = ask_claude(prompt)
        except Exception as e:
            print(f"Ошибка генерации для {card['id']}: {e}", file=sys.stderr)
            continue

        if response.strip() == "NOT_RELEVANT" or "NOT_RELEVANT" in response[:20]:
            continue

        drafted.append({**card, "draft": response})
    return drafted


if __name__ == "__main__":
    candidates = json.load(sys.stdin)
    result = run(candidates)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
