# File: skills_registry/harvest_daad_stipendiendatenbank_alle_programme.py
# Version: 1.0.0 | Release Date: 2026-11-10
import re
import urllib.parse
from bs4 import BeautifulSoup

def harvest_daad_stipendiendatenbank_alle_programme(html: str, base_url: str) -> list[dict]:
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    items = []
    seen = set()

    # 1. Карточки из прямой DOM-инъекции
    for card in soup.select("#pycognition-injected-grants article, .grant-injected-card"):
        a = card.find("a")
        title = a.get_text(strip=True) if a else ""
        link = a.get("href", "") if a else ""
        if title and len(title) > 10 and link not in seen:
            seen.add(link)
            desc_el = card.find(class_="description")
            dead_el = card.find(class_="deadline")
            items.append({
                "title": title,
                "funder": "DAAD",
                "deadline": dead_el.get_text(strip=True) if dead_el else "siehe Detailseite / laufend",
                "link": urllib.parse.urljoin(base_url, link),
                "description": desc_el.get_text(strip=True) if desc_el else "Förderprogramm",
                "target_group": "Studierende, Graduierte, Promovierende & Postdocs"
            })

    # 2. Нативная разметка по правилам конфигурации
    if not items:
        entries = soup.select("ul.resultlist li.entry, li.entry")
        for entry in entries:
            a_tag = entry.select_one("h2 a") or entry.find("a")
            if not a_tag:
                continue
            raw_href = a_tag.get("href", "").strip()
            if not raw_href:
                continue
            full_link = urllib.parse.urljoin(base_url, raw_href)
            if full_link in seen:
                continue

            # Удаление служебных span (например, '• DAAD')
            span = a_tag.find("span")
            if span:
                span.decompose()

            title = re.sub(r"\s+", " ", a_tag.get_text(strip=True))
            if not title or len(title) < 8:
                continue
            seen.add(full_link)

            target_group = "Studierende, Graduierte, Promovierende & Postdocs"
            dl_tag = entry.find("dl")
            if dl_tag:
                dt_status = dl_tag.find(lambda t: t.name == "dt" and "Status:" in t.get_text())
                if dt_status and dt_status.find_next_sibling("dd"):
                    target_group = re.sub(r"\s+", " ", dt_status.find_next_sibling("dd").get_text(strip=True))

            desc_p = entry.select_one("p.entry-detail")
            desc = re.sub(r"\s+", " ", desc_p.get_text(strip=True)) if desc_p else f"Förderprogramm: {title}"

            d_match = re.search(r"(\d{1,2}\.s*(?:[A-Za-zäöüÄÖÜ]+|\d{1,2})\s*\d{4})", desc)
            deadline = d_match.group(1) if d_match else "siehe Detailseite / laufend"

            items.append({
                "title": title,
                "funder": "DAAD",
                "deadline": deadline,
                "link": full_link,
                "description": desc,
                "target_group": target_group
            })

    return items
