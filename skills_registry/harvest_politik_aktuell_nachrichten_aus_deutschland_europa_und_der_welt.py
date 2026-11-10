def harvest_politik_aktuell_nachrichten_aus_deutschland_europa_und_der_welt(html, base_url):
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    import re

    # This source is a general news portal (t-online.de/nachrichten).
    # EMPTY_DOM_DRIFT here is a true negative: the DOM renders correctly but
    # contains zero funding opportunities. Keep a strict grant lexicon so that
    # ordinary news teasers are never promoted to grant records.
    GRANT_KEYWORDS = (
        'förder', 'foerder', 'fördermittel', 'stipendium', 'stipendien',
        'grant', 'grants', 'funding', 'fellowship', 'call for', 'ausschreibung',
        'bewerbung', 'bewerbungsschluss', 'zuwendung', 'drittmittel',
        'projektförderung', 'förderprogramm', 'preisgeld', 'frist', 'deadline',
    )

    DEADLINE_RE = re.compile(
        r'\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b'
        r'|\b\d{1,2}\.\s*(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+\d{4}\b',
        re.IGNORECASE,
    )

    DEFAULT_FUNDER = 'Politik aktuell: Nachrichten aus Deutschland, Europa und der Welt'

    if not html or not isinstance(html, str) or not html.strip():
        return []

    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'noscript', 'svg', 'template']):
        tag.decompose()

    def norm(value):
        return re.sub(r'\s+', ' ', value or '').strip()

    containers = soup.select('article')
    if not containers:
        containers = soup.find_all('a', href=True)

    items = []
    seen = set()

    for node in containers:
        title_node = node.select_one('[data-tb-title]')
        if title_node is None and node.name in ('h1', 'h2', 'h3', 'h4', 'a'):
            title_node = node
        if title_node is None:
            title_node = node.find(['h1', 'h2', 'h3', 'h4'])
        if title_node is None:
            continue

        title = norm(title_node.get_text(' ', strip=True))
        if not title:
            continue

        link_node = node.select_one('[data-tb-link]')
        if link_node is None:
            link_node = node if node.name == 'a' else node.find('a', href=True)
        href = link_node.get('href') if link_node is not None else None
        link = urljoin(base_url, href) if href else base_url

        kicker_node = node.select_one('[data-tb-kicker]')
        kicker = norm(kicker_node.get_text(' ', strip=True)) if kicker_node is not None else ''

        # Deterministic gate: only nodes whose headline/kicker carry grant
        # vocabulary survive. On a pure news homepage this yields an empty list.
        haystack = (title + ' ' + kicker).lower()
        if not any(keyword in haystack for keyword in GRANT_KEYWORDS):
            continue

        body_text = norm(node.get_text(' ', strip=True))
        deadline_match = DEADLINE_RE.search(body_text)
        deadline = norm(deadline_match.group(0)) if deadline_match else ''

        funder_node = node.select_one('[data-tb-author]')
        funder = norm(funder_node.get_text(' ', strip=True)) if funder_node is not None else DEFAULT_FUNDER
        if not funder:
            funder = DEFAULT_FUNDER

        dedupe_key = (title.lower(), link)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        items.append(dict(
            title=title,
            funder=funder,
            deadline=deadline,
            link=link,
            description=kicker or title,
            target_group='',
        ))

    return items