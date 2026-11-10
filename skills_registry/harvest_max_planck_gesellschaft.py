def harvest_max_planck_gesellschaft(html: str, base_url: str) -> list[dict]:
    """Parse Max-Planck-Gesellschaft funding/qualification programmes.

    Deterministic: same html -> same list. Returns [] for error/soft-404 pages
    (the /foerderprogramme endpoint currently serves a 404 page whose only
    content is site navigation, which must NOT be emitted as grant items).
    """
    import re
    from urllib.parse import urljoin
    from bs4 import BeautifulSoup

    FUNDER = "Max-Planck-Gesellschaft"
    DEFAULT_TARGET = "Nachwuchswissenschaftler:innen (Promotion/Postdoc) und Forschende"
    KEYWORDS = (
        "förder", "foerder", "funding", "stipend", "fellowship", "grant",
        "programm", "program", "ausschreibung", "research group",
        "research school", "nachwuchs", "career", "stelle", "position",
    )
    NAV_BLOCKLIST = {
        "newsroom", "jobboard", "jobboerse", "institutes", "facts-and-figures",
        "zahlen-und-fakten", "keyword-collection", "themensammlung",
        "mpresearch", "maxplanckforschung", "impressum", "privacy", "datenschutz",
        "kontakt", "contact", "login", "suche", "search", "404",
    }

    items = []
    seen = set()

    if not html or not isinstance(html, str):
        return items

    soup = BeautifulSoup(html, "html.parser")

    page_text = soup.get_text(" ", strip=True).lower()
    error_markers = (
        "404-fehlerseite", "404 error page", "can't be found",
        "seite kann nicht gefunden werden", "page you are looking for",
    )
    if any(marker in page_text for marker in error_markers):
        return items

    def clean(value) -> str:
        return re.sub(r"\s+", " ", (value or "")).strip()

    def relevant(text: str, href: str) -> bool:
        blob = (str(text) + " " + str(href)).lower()
        if any(bad in blob for bad in NAV_BLOCKLIST):
            return False
        return any(kw in blob for kw in KEYWORDS)

    def add(title, href, description="", target_group=""):
        title = clean(title)
        link = urljoin(base_url, href) if href else base_url
        if len(title) < 4 or not link.startswith("http"):
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
            "description": clean(description) or (
                title + " – Förder- bzw. Qualifizierungsprogramm der Max-Planck-Gesellschaft."
            ),
            "target_group": clean(target_group) or DEFAULT_TARGET,
        })

    # 1) structured cards / teasers / accordion entries / list items
    containers = soup.select(
        "article, .card, .teaser, .c-card, .program, .funding, .accordion__item, li"
    )
    for node in containers:
        heading = node.find(["h2", "h3", "h4", "h5"])
        anchor = node.find("a", href=True)
        if not heading or not anchor:
            continue
        heading_text = heading.get_text(" ", strip=True)
        if not relevant(heading_text, anchor["href"]):
            continue
        desc_node = node.find("p")
        add(
            heading_text,
            anchor["href"],
            desc_node.get_text(" ", strip=True) if desc_node else "",
        )

    # 2) headings carrying their own link
    if not items:
        for heading in soup.find_all(["h2", "h3", "h4"]):
            anchor = heading.find("a", href=True)
            if anchor is None:
                anchor = heading.find_next("a", href=True)
            if anchor is None:
                continue
            heading_text = heading.get_text(" ", strip=True)
            if not relevant(heading_text, anchor.get("href", "")):
                continue
            add(heading_text, anchor.get("href", ""))

    # 3) keyword sweep over anchors (skip pure navigation)
    if not items:
        for anchor in soup.find_all("a", href=True):
            label = anchor.get_text(" ", strip=True)
            if relevant(label, anchor.get("href", "")):
                add(label, anchor.get("href", ""))

    return items