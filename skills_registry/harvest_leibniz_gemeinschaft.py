def harvest_leibniz_gemeinschaft(html: str, base_url: str) -> list[dict]:
    """Deterministic harvester for Leibniz-Gemeinschaft funding pages.

    Returns [] when the fetched document is the TYPO3 error page
    ('Seite nicht gefunden') instead of a real funding overview.
    Otherwise extracts funding lines / programmes from headings and cards.
    """
    import re
    from urllib.parse import urljoin, urlparse

    from bs4 import BeautifulSoup

    FUNDER = "Leibniz-Gemeinschaft"
    KEYWORDS = (
        "förder", "foerder", "stipend", "ausschreib", "programm",
        "fellowship", "grant", "promotion", "postdoc", "nachwuchs",
        "preis", "karriere", "finanzier", "call",
    )
    ERROR_MARKERS = (
        "seite nicht gefunden",
        "leider existiert die von ihnen gewaehlte seite nicht mehr",
        "leider existiert die von ihnen gewählte seite nicht mehr",
    )

    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    # 1) Hard gate: detect the soft-404 page before any extraction.
    visible = soup.get_text(" ", strip=True).lower()
    if any(marker in visible for marker in ERROR_MARKERS):
        return []

    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "form"]):
        tag.decompose()

    root = soup.find("main") or soup.body or soup
    host = urlparse(base_url).netloc

    items = []
    seen = set()

    def _clean(value):
        return re.sub(r"\s+", " ", value or "").strip()

    def _add(title, href, description=""):
        title = _clean(title).strip(" -–—|·>")
        if not title or not (5 <= len(title) <= 200):
            return
        link = urljoin(base_url, href) if href else base_url
        link = link.split("#")[0]
        parsed = urlparse(link)
        if parsed.scheme not in ("http", "https"):
            return
        if parsed.netloc and host and parsed.netloc != host:
            return
        key = (title.lower(), link)
        if key in seen:
            return
        seen.add(key)
        items.append({
            "title": title,
            "funder": FUNDER,
            "deadline": "laufend",
            "link": link,
            "description": _clean(description),
            "target_group": "Wissenschaftlerinnen und Wissenschaftler",
        })

    # 2) Structured teaser / card components (TYPO3 markup patterns).
    card_selectors = (
        "article", ".card", ".teaser", ".teaser-item", ".c-card",
        ".ce-teaser", ".list-item", ".accordion-item", "li.item",
    )
    for selector in card_selectors:
        for node in root.select(selector):
            heading = node.find(["h2", "h3", "h4", "h5"])
            anchor = node.find("a", href=True)
            if heading is None or anchor is None:
                continue
            title = heading.get_text(" ", strip=True)
            if not any(k in title.lower() for k in KEYWORDS):
                continue
            para = node.find("p")
            _add(title, anchor["href"], para.get_text(" ", strip=True) if para else "")

    # 3) Fallback: heading-driven extraction inside the primary content area.
    for node in root.select("h2, h3, h4"):
        title = node.get_text(" ", strip=True)
        if not any(k in title.lower() for k in KEYWORDS):
            continue
        anchor = node.find("a", href=True)
        if anchor is None:
            block = node.find_parent(["a", "div", "li", "section"])
            anchor = block.find("a", href=True) if block else None
        href = anchor["href"] if anchor else ""
        para = node.find_next("p")
        _add(title, href, para.get_text(" ", strip=True) if para else "")

    return items