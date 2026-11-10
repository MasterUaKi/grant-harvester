def harvest_4_800_stipendienprogramme_deutschlands_gr_te(html, base_url):
    """Defensive harvester for mystipendium.de (EMPTY_DOM_DRIFT tolerant).

    The live response returned HTTP 200 but the cleaned DOM contained only
    an anchor stub (<a id="main-content"></a>) - i.e. the listing grid was
    rendered client-side or replaced by a JS shell. This routine therefore
    never assumes a populated DOM: it returns [] on the stub, and otherwise
    scrapes grant cards defensively (article/li/card/teaser containers plus
    an anchor-driven fallback), de-duplicates by (title, link) and extracts
    deadline / target group with conservative regexes.
    """
    import re
    from urllib.parse import urljoin, urlparse

    try:
        from bs4 import BeautifulSoup
    except ImportError:  # pragma: no cover
        return []

    items = []
    if not html or not isinstance(html, str) or not html.strip():
        return items

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return items

    # EMPTY_DOM_DRIFT guard: stub pages have no meaningful tag tree.
    if soup.find() is None:
        return items
    if len(soup.get_text(strip=True)) < 20 and not soup.find("a", href=True):
        return items

    FUNDER = "4.800 Stipendienprogramme - Deutschlands größte …"

    DEADLINE_RE = re.compile(
        r"(?i)(?:bewerbungsschluss|deadline|frist|termin|bis\s+zum)\s*[:\-]?\s*"
        r"([0-3]?\d[./][01]?\d[./]\d{2,4}"
        r"|\d{1,2}\.\s*[A-ZÄÖÜ][a-zäöüß]+\s*\d{4}"
        r"|laufend|fortlaufend)"
    )
    TARGET_RE = re.compile(
        r"(?i)(schüler(?:innen)?|studierende|studenten|studis|doktorand(?:innen)?"
        r"|promovierende|postdocs?|absolvent(?:innen)?|berufstätige"
        r"|auszubildende|azubis?|lehrende|forschende)"
    )
    GRANT_HINT_RE = re.compile(
        r"(?i)(stipendium|stipendien|förderung|foerderung|grant|preis"
        r"|auszeichnung|programm|bewerbung|frist)"
    )

    def clean(txt):
        return re.sub(r"\s+", " ", (txt or "")).strip()

    def norm_link(href):
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            return None
        absolute = urljoin(base_url, href.strip())
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            return None
        return absolute.split("#")[0]

    selectors = (
        "article, li, .teaser, .card, .views-row, .search-result, "
        "[class*='stipend'], [class*='teaser'], [class*='card'], "
        "[class*='result'], [class*='listing']"
    )
    candidates = list(soup.select(selectors))
    for a in soup.find_all("a", href=True):
        candidates.append(a.find_parent(["article", "li", "div", "td", "section"]) or a)

    seen = set()
    for node in candidates:
        try:
            link_el = node.find("a", href=True)
            link = norm_link(link_el["href"]) if link_el else None

            heading = node.find(["h1", "h2", "h3", "h4", "h5", "strong"])
            if heading is not None:
                title = clean(heading.get_text(" ", strip=True))
            elif link_el is not None:
                title = clean(link_el.get_text(" ", strip=True))
            else:
                title = ""

            if not title or len(title) < 4 or len(title) > 300:
                continue

            text = clean(node.get_text(" ", strip=True))
            if len(text) < 15:
                continue
            if not GRANT_HINT_RE.search(title) and not GRANT_HINT_RE.search(text):
                continue
            if link and link.rstrip("/") == (base_url or "").rstrip("/"):
                continue

            key = (title.lower(), link)
            if key in seen:
                continue
            seen.add(key)

            m = DEADLINE_RE.search(text)
            deadline = clean(m.group(1)) if m else ""

            t = TARGET_RE.search(text)
            target = t.group(1).lower() if t else ""

            description = text
            if heading is not None and title and title in description:
                description = clean(description.replace(title, "", 1))

            items.append({
                "title": title,
                "funder": FUNDER,
                "deadline": deadline,
                "link": link or base_url,
                "description": description[:600],
                "target_group": target,
            })
        except Exception:
            continue

    return items