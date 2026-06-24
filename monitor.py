"""
Мониторинг биржи проектов Kwork без авторизации.
Ищет заказы по ключевым словам/категориям, фильтрует по релевантности,
сверяет с уже виденными (seen.json) и выводит новые подходящие заказы как JSON.
"""
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SEEN_FILE = Path(__file__).parent / "seen.json"

# Категория "Дизайн" на бирже проектов (c=15) + прямой поиск по ключевым словам.
# Категория покрывает большинство релевантных заказов, поиск по словам расширяет охват
# на заказы, размещённые в других рубриках.
SOURCES = [
    "https://kwork.ru/projects?c=15",
    "https://kwork.ru/projects?keyword=" + "%20".join(["карточка", "маркетплейс"]),
    "https://kwork.ru/projects?keyword=" + "%20".join(["инфографика", "товара"]),
    "https://kwork.ru/projects?keyword=" + "%20".join(["нейросеть", "карточка"]),
    "https://kwork.ru/projects?keyword=" + "%20".join(["карточка", "авито"]),
]

# Заказ должен упоминать тематику карточек/маркетплейса И визуальную/дизайнерскую
# работу (или AI-генерацию) — иначе ловим копирайт/SEO/наполнение по слову "карточка".
TOPIC_HINTS = [
    "карточ", "инфографик", "маркетплейс", "wildberries", "вайлдберри",
    "ozon", "озон", "wb ", "вб ", "авито", "avito",
]
VISUAL_HINTS = [
    "дизайн", "оформлен", "макет", "баннер", "изображ", "фотошоп",
    "визуал", "иллюстрац", "фото", "картин", "график",
]
AI_HINTS = ["нейросет", "нейронк", " ai ", "иишн", " ии ", "генерац", "neural"]
EXCLUDE_HINTS = [
    "наполнен", "копирован текст", "seo", "продвижен", "повышен", "трафик",
    "wordpress", "вордпресс",
]


MARKETPLACE_HINTS = [
    "маркетплейс", "wildberries", "вайлдберри", "ozon", "озон", "wb ", "вб ",
    "авито", "avito",
]


def is_relevant(title: str, description: str) -> bool:
    text = f"{title} {description}".lower()
    if any(kw in text for kw in EXCLUDE_HINTS):
        return False
    # Явная связка "карточка" + конкретный маркетплейс — почти всегда дизайн-заказ,
    # пропускаем без доп. условий (даже если описание обрезано "Показать полностью").
    if "карточ" in text and any(kw in text for kw in MARKETPLACE_HINTS):
        return True
    has_topic = any(kw in text for kw in TOPIC_HINTS)
    has_visual = any(kw in text for kw in VISUAL_HINTS)
    has_ai = any(kw in text for kw in AI_HINTS)
    return has_topic and (has_visual or has_ai)


def load_seen() -> set[str]:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen: set[str]) -> None:
    SEEN_FILE.write_text(json.dumps(sorted(seen), ensure_ascii=False, indent=2))


def extract_cards(page) -> list[dict]:
    cards = []
    title_links = page.locator(".wants-card__header-title a").all()
    for link in title_links:
        href = link.get_attribute("href") or ""
        m = re.search(r"/projects/(\d+)", href)
        if not m:
            continue
        project_id = m.group(1)
        title = link.inner_text().strip()

        card_root = link.evaluate_handle("e => e.closest('.want-card')")
        description = ""
        budget = ""
        try:
            desc_el = card_root.as_element().query_selector(
                ".wants-card__description-text"
            )
            # textContent захватывает и скрытый блок "полного" текста
            # (видимый блок обрезан кнопкой "Показать полностью").
            description = (desc_el.text_content() or "").strip() if desc_el else ""
            price_el = card_root.as_element().query_selector(".wants-card__price")
            if price_el:
                budget = price_el.inner_text().strip().replace("\n", " ")
        except Exception:
            pass

        cards.append(
            {
                "id": project_id,
                "title": title,
                "description": description,
                "budget": budget,
                "url": f"https://kwork.ru/projects/{project_id}",
            }
        )
    return cards


def run() -> list[dict]:
    seen = load_seen()
    new_relevant = []
    found_ids = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for url in SOURCES:
            page.goto(url, timeout=30000)
            page.wait_for_timeout(3500)
            for card in extract_cards(page):
                if card["id"] in found_ids:
                    continue
                found_ids.add(card["id"])
                if card["id"] in seen:
                    continue
                if is_relevant(card["title"], card["description"]):
                    new_relevant.append(card)
        browser.close()

    seen |= found_ids
    save_seen(seen)
    return new_relevant


if __name__ == "__main__":
    result = run()
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
