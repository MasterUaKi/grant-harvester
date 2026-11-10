def harvest_eu_funding_tenders_portal_horizon_europe(html: str, base_url: str) -> list[dict]:
    """Deterministic harvester for the EU Funding & Tenders Portal (Horizon Europe).

    The portal is a client-side Angular SPA (app-root / sedia-opportunities-v19).
    If the server only ships the application shell (EMPTY_DOM_DRIFT: an
    'eui-block-content--blocked' node is present and no server-rendered offer
    links exist) this function returns an empty list instead of inventing
    programmes. Real offer cards are parsed whenever they are present in HTML.
    """
    import re
    from urllib.parse import urljoin
    from bs4 import BeautifulSoup

    FUNDER = "EU Funding & Tenders Portal - Horizon Europe"
    NAV_TEXT = {
        "about", "accessibility", "free text search", "it helpdesk", "cookies",
        "legal notice", "apis", "show more", "search", "home", "login",
        "register", "help", "faq", "contact", "sitemap", "privacy statement",
        "cookie policy", "english", "deutsch",
    }
    DATE_RE = re.compile(
        r"\b(\d{1,2}[./]\d{1,2}[./]\d{4}"
        r"|\d{4}-\d{2}-\d{2}"
        r"|\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{4})\b",
        re.IGNORECASE,
    )
    DEADLINE_LABEL_RE = re.compile(
        r"(deadline|closing date|submission deadline|opening date|cut-?off)",
        re.IGNORECASE,
    )
    OFFER_HREF_RE = re.compile(
        r"/(?:opportunities|funding-tenders)/.*"
        r"(?:topic|call|tender|programme|fellowship|grant)",
        re.IGNORECASE,
    )
    CARD_SELECTOR = (
        "eui-card, [data-e2e='eui-card'], [data-e2e*='result-item'], "
        "[data-e2e*='opportunity-card'], article, table tbody tr"
    )
    BLOCK_CONTAINERS = ("li", "tr", "div", "article", "section")

    items = []
    if not html or not isinstance(html, str):
        return items

    soup = BeautifulSoup(html, "html.parser")

    def clean(node):
        if node is None:
            return ""
        getter = getattr(node, "get_text", None)
        text = getter(" ", strip=True) if getter is not None else str(node)
        return re.sub(r"\s+", " ", text).strip()

    offer_links = [
        a for a in soup.find_all("a", href=True)
        if OFFER_HREF_RE.search(a["href"])
    ]
    shell_blocked = soup.select_one(".eui-block-content--blocked") is not None
    if shell_blocked and not offer_links:
        return items

    seen = set()

    def add_item(title, href, context_text, context_node):
        title = clean(title)
        if len(title) < 6 or title.lower() in NAV_TEXT:
            return
        href = (href or "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            return
        link = urljoin(base_url or "", href)
        key = (title.lower(), link)
        if key in seen:
            return
        seen.add(key)

        deadline = "laufend"
        context_text = context_text or ""
        label = DEADLINE_LABEL_RE.search(context_text)
        if label is not None:
            date_match = DATE_RE.search(context_text[label.end():])
            if date_match is not None:
                deadline = date_match.group(1)
        if deadline == "laufend":
            date_match = DATE_RE.search(context_text)
            if date_match is not None:
                deadline = date_match.group(1)

        description = ""
        if context_node is not None:
            for selector in ("p", "[class*='description']",
                             "[class*='summary']", "eui-card-text"):
                node = context_node.select_one(selector)
                if node is not None and len(clean(node)) >= 20:
                    description = clean(node)
                    break
        if not description:
            description = context_text[:400].strip()
        if len(description) > 500:
            description = description[:497].rstrip() + "..."

        target_group = "siehe Ausschreibung"
        tg = re.search(
            r"(?:target group|who can apply|eligib\w+)\s*[:\-]\s*([^.;|]{3,120})",
            context_text,
            re.IGNORECASE,
        )
        if tg is not None:
            target_group = clean(tg.group(1))

        items.append({
            "title": title,
            "funder": FUNDER,
            "deadline": deadline,
            "link": link,
            "description": description,
            "target_group": target_group,
        })

    for card in soup.select(CARD_SELECTOR):
        anchor = None
        for candidate in card.find_all("a", href=True):
            href = candidate["href"].strip()
            if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            if clean(candidate).lower() in NAV_TEXT:
                continue
            anchor = candidate
            break
        if anchor is None:
            continue

        heading = card.find(["h1", "h2", "h3", "h4", "h5", "h6"])
        title = clean(heading) if heading is not None else ""
        if not title:
            for selector in ("[class*='title']", "eui-card-title", "strong"):
                node = card.select_one(selector)
                if node is not None and clean(node):
                    title = clean(node)
                    break
        if not title:
            title = clean(anchor)

        add_item(title, anchor["href"], clean(card), card)

    if not items:
        for anchor in offer_links:
            context = anchor.find_parent(BLOCK_CONTAINERS)
            if context is None:
                context = anchor
            add_item(clean(anchor), anchor["href"], clean(context), context)

    return items