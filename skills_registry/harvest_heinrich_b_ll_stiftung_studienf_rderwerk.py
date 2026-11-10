def harvest_heinrich_b_ll_stiftung_studienf_rderwerk(html: str, base_url: str) -> list[dict]:
    import re
    from urllib.parse import urljoin
    from bs4 import BeautifulSoup

    FUNDER = "Heinrich-Böll-Stiftung - Studienförderwerk"
    DEFAULT_TARGET = "Studierende und Promovierende aller Fächer und Hochschulen im In- und Ausland"
    SKIP = ("alumni", "kooperation", "unterstuetzer", "einblicke", "podcast", "kontakt", "datenschutz", "faq")

    soup = BeautifulSoup(html or "", "html.parser")
    page_text = soup.get_text(" ", strip=True)

    # Bewerbungszeiträume: alle DD.MM.YYYY-Ranges deterministisch einsammeln
    ranges = []
    for m in re.finditer(r"(\d{2}\.\d{2}\.\d{4})\s*(?:bis|\u2013|-)\s*(\d{2}\.\d{2}\.\d{4})", page_text):
        rng = m.group(1) + " - " + m.group(2)
        if rng not in ranges:
            ranges.append(rng)
    deadline = "; ".join(ranges)

    items = []
    seen = set()

    def add(title, link, description, target_group):
        title = (title or "").strip()
        link = (link or "").strip()
        if not title or not link:
            return
        key = (title.lower(), link)
        if key in seen:
            return
        seen.add(key)
        items.append({
            "title": title,
            "funder": FUNDER,
            "deadline": deadline,
            "link": link,
            "description": (description or "").strip(),
            "target_group": target_group,
        })

    # 1) Dach-Programm aus dem Hero-Titlebox
    hero = soup.select_one("h1.grid-box-titlebox__title")
    if hero is not None:
        sub = soup.select_one("h2.grid-box-titlebox__subtitle")
        add(hero.get_text(" ", strip=True),
            base_url,
            sub.get_text(" ", strip=True) if sub is not None else "",
            DEFAULT_TARGET)

    # 2) Wegweiser-Kacheln (Programm- und Förderbausteine)
    for box in soup.select("div.grid-box-topics"):
        a = box.find("a", href=True)
        if a is None:
            continue
        link = urljoin(base_url, a["href"].strip())
        low = link.lower()
        if any(tok in low for tok in SKIP):
            continue
        title_el = box.select_one("h2.topics-box__title")
        if title_el is None:
            title_el = box.find(["h2", "h3"])
        title = title_el.get_text(" ", strip=True) if title_el is not None else ""
        img = box.find("img")
        desc = (img.get("alt") or "").strip() if img is not None else ""
        probe = (title + " " + low).lower()
        if "promotion" in probe:
            target = "Promovierende und Promotionsinteressierte aller Fächer"
        elif "studienstart" in probe or "studium" in probe or "bewerbung" in probe:
            target = "Studierende (Bachelor/Master) und Promovierende aller Fächer"
        else:
            target = DEFAULT_TARGET
        add(title, link, desc, target)

    return items