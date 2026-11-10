def harvest_startseite_bmftr(html: str, base_url: str) -> list[dict]:
    import re
    from urllib.parse import urljoin, urlsplit
    from bs4 import BeautifulSoup

    FUNDER = 'Startseite - BMFTR'
    UNKNOWN = ''
    items = []
    seen = set()

    soup = BeautifulSoup(html or '', 'html.parser')

    EXCLUDE_PATHS = ('/SharedDocs/', '/SiteGlobals/', '/DE/Home/', '/DE/Service/', '/DE/Impressum')
    INCLUDE_PATHS = ('/DE/Forschung/', '/DE/Technologie/', '/DE/Raumfahrt/')

    CARD_SELECTOR = 'div.c-teaser-image-slider, div.c-teaser, div.c-teaser-story'
    TITLE_SELECTORS = (
        'h3.c-teaser__headline',
        'h3.c-teaser-image-slider__headline',
        'h3.c-teaser-story__headline',
    )
    TEXT_SELECTORS = ('div.c-teaser__text', 'div.c-teaser-story__text')

    TARGET_MAP = (
        ('sprunginnovation', 'Erfinder:innen, Start-ups und Forschende'),
        ('forschungszulage', 'Unternehmen (insbesondere KMU) mit F&E-Vorhaben'),
        ('innovative hochschule', 'Hochschulen, insbesondere HAW'),
        ('hochschule', 'Hochschulen'),
        ('kreb', 'Forschende der medizinischen Forschung'),
        ('quanten', 'Forschende und Unternehmen (Quantentechnologien)'),
        ('supercomputing', 'Forschende aus Wissenschaft und Industrie'),
        ('robotik', 'Forschende und Unternehmen (Robotik)'),
        ('intelligenz', 'Forschende und Unternehmen (KI)'),
        ('hightech', 'Forschende und Unternehmen (Technologieentwicklung)'),
        ('technologie', 'Forschende und Unternehmen (Technologieentwicklung)'),
        ('international', 'Forschende und Forschungseinrichtungen'),
    )

    DATE_RE = re.compile(r'\b\d{1,2}\.\d{1,2}\.\d{4}\b')

    def clean(value):
        return re.sub(r'\s+', ' ', value or '').strip()

    def is_funding_page(url):
        parts = urlsplit(url)
        if parts.scheme not in ('http', 'https'):
            return False
        if parts.netloc and not parts.netloc.endswith('bmftr.bund.de'):
            return False
        path = parts.path or '/'
        if any(path.startswith(p) for p in EXCLUDE_PATHS):
            return False
        return any(path.startswith(p) for p in INCLUDE_PATHS)

    def target_group(title, description):
        haystack = (title + ' ' + description).lower()
        for needle, group in TARGET_MAP:
            if needle in haystack:
                return group
        return UNKNOWN

    for card in soup.select(CARD_SELECTOR):
        link_el = None
        link_url = ''
        for anchor in card.find_all('a', href=True):
            candidate = urljoin(base_url, anchor['href'].strip())
            if is_funding_page(candidate):
                link_el, link_url = anchor, candidate
                break
        if link_el is None or link_url in seen:
            continue

        title = ''
        for selector in TITLE_SELECTORS:
            node = card.select_one(selector)
            if node is not None:
                title = clean(node.get_text(' '))
                if title:
                    break
        if not title:
            title = clean(link_el.get_text(' '))
        if not title:
            continue

        description = ''
        for selector in TEXT_SELECTORS:
            node = card.select_one(selector)
            if node is not None:
                description = clean(node.get_text(' '))
                if description:
                    break

        match = DATE_RE.search(clean(card.get_text(' ')))
        deadline = match.group(0) if match else UNKNOWN

        seen.add(link_url)
        items.append({
            'title': title,
            'funder': FUNDER,
            'deadline': deadline,
            'link': link_url,
            'description': description,
            'target_group': target_group(title, description),
        })

    return items