# File: skills_registry/harvest_dfg_information_f_r_die_wissenschaft.py
# Version: 1.0.0 | Release Date: 2026-11-10
import re
import urllib.parse
from bs4 import BeautifulSoup


def harvest_dfg_information_f_r_die_wissenschaft(html: str, base_url: str) -> list[dict]:
    """
    Детерминированный экстрактор для портала DFG (Information für die Wissenschaft).
    Извлекает полные наименования конкурсов, исключая обрезку до единичных символов.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    items = []
    seen = set()

    # 1. Поиск карточек тизеров и новостных блоков DFG
    teasers = soup.select(".c-teaser, article, li.teaser, .search-result, .list-item")

    # Если специализированные контейнеры не найдены, берем родительские блоки ссылок
    if not teasers:
        teasers = soup.find_all(lambda tag: tag.name in ["div", "li", "article"] and tag.find(["h2", "h3", "h4"]))

    for card in teasers:
        # Поиск заголовка и ссылки
        heading = card.find(["h2", "h3", "h4", "strong"])
        a_tag = None

        if heading:
            a_tag = heading.find("a") or heading.find_parent("a")
        if not a_tag:
            a_tag = card.find("a", href=True)

        if not a_tag:
            continue

        raw_href = a_tag.get("href", "").strip()
        full_link = urllib.parse.urljoin(base_url, raw_href)

        if full_link in seen or not raw_href or raw_href.startswith(("#", "javascript:", "mailto:")):
            continue

        raw_title = heading.get_text(strip=True) if heading else a_tag.get_text(strip=True)
        clean_title = re.sub(r"\s+", " ", raw_title).strip()

        # Защита от мусорных и обрезанных названий
        if len(clean_title) < 6 or clean_title in [")", "s", "6", "”", "“", '"', "-", "mehr"]:
            # Пробуем извлечь заголовок из атрибута title или первого длинного параграфа
            if a_tag.get("title") and len(a_tag["title"].strip()) >= 6:
                clean_title = a_tag["title"].strip()
            else:
                p_text = card.find("p")
                if p_text and len(p_text.get_text(strip=True)) > 15:
                    clean_title = p_text.get_text(strip=True)[:100] + "..."
                else:
                    continue

        seen.add(full_link)

        # Извлечение описания и дедлайна
        desc = "DFG Ausschreibung / Information für die Wissenschaft"
        deadline = "laufend / siehe Ausschreibung"

        card_text = card.get_text(separator=" ", strip=True)
        if len(card_text) > 30:
            desc = re.sub(r"\s+", " ", card_text)[:350]

        d_match = re.search(r"(\d{1,2}\.\s*(?:[A-Za-zäöüÄÖÜ]+|\d{1,2})\s*\d{4})", card_text)
        if d_match:
            deadline = d_match.group(1)

        items.append({
            "title": clean_title,
            "funder": "DFG - Information für die Wissenschaft",
            "deadline": deadline,
            "link": full_link,
            "description": desc,
            "target_group": "Forscher*innen aller Disziplinen / Researchers of all disciplines"
        })

    return items