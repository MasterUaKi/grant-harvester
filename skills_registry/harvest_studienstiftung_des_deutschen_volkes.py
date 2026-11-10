def harvest_studienstiftung_des_deutschen_volkes(html: str, base_url: str) -> list[dict]:
    import re
    from urllib.parse import urljoin, urlparse
    from bs4 import BeautifulSoup

    FUNDER = "Studienstiftung des deutschen Volkes"
    items = []

    if not html or not isinstance(html, str):
        return items

    soup = BeautifulSoup(html, "html.parser")
    root = (
        soup.find("main", id="main")
        or soup.find("main")
        or soup.find("article")
        or soup.body
    )
    if root is None:
        return items

    # --- Guard: the harvested document is an error / 404 page -> no grants ---
    h1 = root.find("h1")
    h1_text = h1.get_text(" ", strip=True).lower() if h1 else ""
    if (
        "nicht gefunden" in h1_text
        or "not found" in h1_text
        or "seite existiert nicht" in h1_text
        or re.search(r"\b404\b", h1_text)
    ):
        return items

    # --- Deterministic extraction patterns ---
    DATE_DOT = re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b")
    DATE_TEXT = re.compile(
        r"\b\d{1,2}\.\s*(?:Januar|Februar|März|April|Mai|Juni|Juli|August|"
        r"September|Oktober|November|Dezember)\s*\d{4}\b",
        re.I,
    )
    DEADLINE_HINT = re.compile(
        r"(bewerbungsschluss|bewerbungsfrist|einsendeschluss|antragsfrist|"
        r"deadline|frist|jährlich|rolling|fortlaufend)",
        re.I,
    )
    GRANT_HINT = re.compile(
        r"(stipendium|stipendien|förderung|foerderung|programm|preis|"
        r"ausschreibung|bewerbung|grant|fellowship|kolleg)",
        re.I,
    )
    TARGET_HINTS = (
        (re.compile(r"(schüler|schueler|schulabgänger|abitur)", re.I), "Schülerinnen und Schüler"),
        (re.compile(r"(doktorand|promotion|phd|dissertation)", re.I), "Doktorandinnen und Doktoranden"),
        (re.compile(r"(postdoc|habilitand)", re.I), "Postdocs"),
        (re.compile(r"(studierend|student|bachelor|master)", re.I), "Studierende"),
        (re.compile(r"(absolvent|alumni|berufstätig)", re.I), "Absolventinnen und Absolventen"),
    )

    def _clean(node) -> str:
        return re.sub(r"\s+", " ", node.get_text(" ", strip=True)) if node else ""

    def _deadline(text: str) -> str:
        match = DATE_DOT.search(text) or DATE_TEXT.search(text)
        if match:
            return match.group(0)
        hint = DEADLINE_HINT.search(text)
        return hint.group(0).capitalize() if hint else ""

    def _target_group(text: str) -> str:
        for pattern, label in TARGET_HINTS:
            if pattern.search(text):
                return label
        return ""

    def _context(anchor) -> str:
        parent = anchor.find_parent(["li", "article", "div", "section", "p"])
        return _clean(parent)[:400] if parent is not None else _clean(anchor)[:400]

    seen = set()
    for anchor in root.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        link = urljoin(base_url, href)
        parsed = urlparse(link)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.path in ("", "/") or parsed.path.lower().endswith(
            (".pdf", ".jpg", ".png", ".zip")
        ):
            continue

        title = _clean(anchor)
        if len(title) < 4:
            continue

        context = _context(anchor)
        haystack = " ".join((title, link, context))
        if not GRANT_HINT.search(haystack):
            continue

        key = link.rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)

        items.append(
            {
                "title": title,
                "funder": FUNDER,
                "deadline": _deadline(haystack),
                "link": link,
                "description": context,
                "target_group": _target_group(haystack),
            }
        )

    return items