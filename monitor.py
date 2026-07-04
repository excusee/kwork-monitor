"""
Мониторинг биржи проектов Kwork без авторизации.
Собирает заказы из категории "Дизайн" и доп. поисков по словам, сверяет
с уже виденными (seen.json) и выводит ВСЕ новые заказы как JSON — без
keyword/fuzzy-фильтра по смыслу (это не умеет понимать смысл, только буквы).
Смысловую фильтрацию делает отдельный шаг classify.py (бесплатная Groq).
"""
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SEEN_FILE = Path(__file__).parent / "seen.json"

# Категория "Дизайн" — основной источник, плюс прямой поиск по словам
# в других категориях для расширения охвата.
SOURCES = [
    "https://kwork.ru/projects?c=15",
    "https://kwork.ru/projects?c=15&page=2",
    "https://kwork.ru/projects?keyword=" + "%20".join(["карточка", "маркетплейс"]),
    "https://kwork.ru/projects?keyword=" + "%20".join(["карточка", "маркетплейс"]) + "&page=2",
    "https://kwork.ru/projects?keyword=" + "%20".join(["инфографика", "товара"]),
    "https://kwork.ru/projects?keyword=" + "%20".join(["нейросеть", "карточка"]),
    "https://kwork.ru/projects?keyword=" + "%20".join(["карточка", "авито"]),
]


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
        max_budget = ""
        try:
            # У описания два вложенных div: видимый обрезанный ("Показать полностью")
            # и скрытый полный. Берём последний — это полный текст без дублирования
            # обрезанной версии перед ним.
            desc_parts = card_root.as_element().query_selector_all(
                ".wants-card__description-text > div"
            )
            if desc_parts:
                description = (desc_parts[-1].text_content() or "").strip()
                # Убираем хвостовое "Скрыть"/"Показать полностью" — это просто
                # текст кнопки-тоггла, попавший в text_content.
                description = re.sub(
                    r"\s*(Скрыть|Показать полностью)\s*$", "", description
                )
            price_el = card_root.as_element().query_selector(".wants-card__price")
            if price_el:
                budget = price_el.inner_text().strip().replace("\n", " ")
            max_price_el = card_root.as_element().query_selector(
                ".wants-card__description-higher-price"
            )
            if max_price_el:
                max_budget = " ".join(max_price_el.inner_text().split())
        except Exception:
            pass

        cards.append(
            {
                "id": project_id,
                "title": title,
                "description": description,
                "budget": budget,
                "max_budget": max_budget,
                "url": f"https://kwork.ru/projects/{project_id}",
            }
        )
    return cards


def run() -> list[dict]:
    seen = load_seen()
    new_cards = []
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
                new_cards.append(card)
        browser.close()

    seen |= found_ids
    save_seen(seen)
    return new_cards


if __name__ == "__main__":
    result = run()
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
