def harvest_helmholtz_gemeinschaft(html, base_url):
    """Deterministic parser for Helmholtz-Gemeinschaft funding/career pages.

    Behaviour:
      * If the document is a 404 / 'Seite nicht gefunden' shell, return [] (no fabrication).
      * Otherwise: extract one item per funding program heading that carries a link,
        falling back to card-style anchors under <main>.
      * Deadline defaults to 'laufend' when no explicit date is present on the card.
    """
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin, urlparse
    import re

    FUNDER = "Helmholtz-Gemeinschaft"
    items, seen = [], set()

    def clean(t):
        return re.sub(r"\s+", " ", (t or "")).strip()

    DEADLINE_RE = re.compile(
        r"(?:frist|deadline|bewerbungsschluss|application deadline|closing date|"
        r"einreichungsfrist|bewerbungsfrist|bis)\s*[:\-]?\s*"
        r"(\d{1,2}\.\d{1,2}\.\d{2,4}|\d{4}-\d{2}-\d{2}|[A-Za-zÄÖÜäöüß]+\s+\d{4})",
        re.I,
    )

    GENERIC = {
        "404", "seite nicht gefunden", "page not found", "zur suche", "go to search",
        "zur startseite", "go to home", "zur geschaeftsstelle", "zur geschäftsstelle",
        "go to head office", "suche", "search", "home", "startseite", "kontakt",
        "contact", "impressum", "imprint", "datenschutz", "privacy", "newsletter",
        "deutsch", "english", "zum inhalt", "skip to content", "menü", "menu",
    }
    DENY_HREF = ("mailto:", "tel:", "javascript:", "#")
    DENY_PATH = ("/suche", "/search", "/impressum", "/imprint", "/datenschutz",
                 "/privacy", "/newsletter", "/kontakt", "/contact")

    def target_group(text):
        low = (text or "").lower()
        if "postdoc" in low or "habilitation" in low:
            return "Postdocs"
        if "doktor" in low or "promotion" in low or "phd" in low or "doctoral" in low:
            return "Doktorand:innen"
        if "studier" in low or "bachelor" in low or "master" in low or "student" in low:
            return "Studierende"
        if "nachwuchs" in low or "early career" in low or "young investigat" in low:
            return "Wissenschaftlicher Nachwuchs"
        if "profess" in low or "senior" in low:
            return "Professor:innen / Senior Researcher"
        return "alle Zielgruppen"

    def is_allowed(link):
        low = link.lower()
        return not any(p in low for p in DENY_PATH)

    def add(title, link, context):
        title = clean(title)
        key = (title.lower(), link)
        if not title or len(title) < 4 or key in seen or not is_allowed(link):
            return
        seen.add(key)
        context = clean(context)
        m = DEADLINE_RE.search(context)
        items.append({
            "title": title,
            "funder": FUNDER,
            "deadline": m.group(1) if m else "laufend",
            "link": link,
            "description": (context[:300].strip(" .,-–—") or title),
            "target_group": target_group(title + " " + context),
        })

    soup = BeautifulSoup(html or "", "html.parser")

    # Hard gate: this is an error shell, not a funding catalogue.
    plain = clean(soup.get_text(" ")).lower()
    if ("seite nicht gefunden" in plain
            or "page not found" in plain
            or "diese url existiert nicht" in plain
            or "this url does not exist" in plain
            or soup.find(class_="error__wrapper") is not None and len(soup.find_all("h2", recursive=True)) <= 4 and "404" in plain):
        return []

    # Strategy 1: one program per heading, scoped to the nearest single-heading block.
    for h in soup.find_all(["h2", "h3", "h4", "h5"]):
        title = clean(h.get_text(" "))
        if len(title) < 5 or title.isdigit() or title.lower() in GENERIC:
            continue

        block, scope = h, None
        for _ in range(5):
            if block.parent is None:
                break
            block = block.parent
            if block.find("a", href=True) and len(block.find_all(["h2", "h3", "h4", "h5", "h6"])) == 1:
                scope = block
                break
        scope = scope or h.parent
        if scope is None:
            continue

        a = h.find("a", href=True) or scope.find("a", href=True)
        if not a:
            continue
        href = (a.get("href") or "").strip()
        if not href or href.startswith(DENY_HREF):
            continue

        link = urljoin(base_url, href)
        if urlparse(link).scheme not in ("http", "https"):
            continue

        context = clean(scope.get_text(" "))
        if context.lower().startswith(title.lower()):
            context = context[len(title):]
        add(title, link, context)

    # Strategy 2: card-style anchors under <main> when no usable headings exist.
    if not items:
        root = soup.find("main") or soup.find("body") or soup
        for a in root.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            label = clean(a.get_text(" "))
            if not href or href.startswith(DENY_HREF) or len(label) < 5:
                continue
            if label.lower() in GENERIC:
                continue
            link = urljoin(base_url, href)
            if urlparse(link).scheme not in ("http", "https"):
                continue
            card = a.find_parent(["article", "li", "section", "div", "td"]) or a
            add(label, link, clean(card.get_text(" ")))

    return items