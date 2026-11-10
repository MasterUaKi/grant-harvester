def harvest_bmbf_aktuelle_bekanntmachungen(html: str, base_url: str) -> list[dict]:
    '''Harvest BMFTR (ex-BMBF) funding programmes and calls.

    EMPTY_DOM_DRIFT diagnosis: the ministry moved from bmbf.de to bmftr.bund.de and
    relaunched on a new CMS (c-teaser-* / js-slide cards). Legacy selectors for the
    'Aktuelle Bekanntmachungen' list match nothing, so the fetch returns HTTP 200
    with an effectively empty DOM. This parser is markup-tolerant: it reads the new
    card markup plus any anchor naming a Bekanntmachung / Foerderung / Stipendium.
    The verified entry point is the home node; a dedicated listing node (expected
    under /DE/Bekanntmachungen/) must be verified before switching base_url.
    '''
    from urllib.parse import urljoin
    from bs4 import BeautifulSoup

    FUNDER = 'BMBF - Aktuelle Bekanntmachungen'
    DEFAULT_DEADLINE = 'laufend'
    DESC_LIMIT = 320
    FUNDING_HINTS = ('bekanntmachung', 'foerder', 'förder', 'stipend', 'ausschreibung',
                     'richtlinie', 'programm', 'zulage', 'preis')
    SKIP_HREF = ('/SharedDocs/Kurzmeldungen/', '/SharedDocs/Pressemitteilungen/',
                 '/SiteGlobals/Forms/Suche/', 'mailto:', 'javascript:')
    TARGET_RULES = (
        (('sprunginnovation', 'sprind'), 'Forschende, Start-ups und Unternehmen mit disruptiven Ideen'),
        (('innovative hochschule',), 'Hochschulen und Transferpartner (Bund-Laender-Initiative)'),
        (('forschungszulage',), 'Unternehmen aller Groessen mit FuE-Vorhaben'),
        (('krebs', 'medizin', 'gesundheit'), 'Forschende der Medizin- und Lebenswissenschaften'),
        (('kuenstliche intelligenz', 'künstliche intelligenz'), 'Hochschulen, Forschungseinrichtungen und Unternehmen'),
        (('robotik', 'supercomputing', 'quanten'), 'Hochschulen, ausseruniversitaere Institute und Technologieunternehmen'),
        (('international', 'wissenschaftsdiplomatie', 'forschungsraum'),
         'Wissenschaftlerinnen und Wissenschaftler, Hochschulen und Forschungseinrichtungen'),
        (('hightech agenda',), 'Forschende, Unternehmen sowie Laender und Kommunen'),
        (('technologie',), 'Forschende, Unternehmen und Forschungseinrichtungen'),
    )

    def _clean(node):
        if node is None:
            return ''
        raw = node.get_text(' ', strip=True) if hasattr(node, 'get_text') else str(node)
        return ' '.join(raw.split()).strip()

    def _target_group(title):
        low = title.lower()
        for keys, label in TARGET_RULES:
            for key in keys:
                if key in low:
                    return label
        return 'Forschende, Hochschulen und Forschungseinrichtungen'

    items, seen = [], set()

    def _add(title, href, description='', deadline=DEFAULT_DEADLINE):
        title = _clean(title)
        href = (href or '').strip()
        if not title or not href:
            return
        for token in SKIP_HREF:
            if token in href:
                return
        link = urljoin(base_url, href)
        key = (title.lower(), link)
        if key in seen:
            return
        seen.add(key)
        items.append({
            'title': title,
            'funder': FUNDER,
            'deadline': deadline or DEFAULT_DEADLINE,
            'link': link,
            'description': _clean(description)[:DESC_LIMIT],
            'target_group': _target_group(title),
        })

    soup = BeautifulSoup(html or '', 'html.parser')

    # pass 1 - highest precision: explicit announcement / funding anchors
    for a in soup.find_all('a', href=True):
        title = _clean(a.get_text(' ', strip=True))
        blob = (a['href'] + ' ' + title).lower()
        if title and any(hint in blob for hint in FUNDING_HINTS):
            _add(title, a['href'])

    # pass 2 - programme cards of the new CMS (c-teaser / c-teaser-story)
    for card in soup.select('div.c-teaser, div.c-teaser-story'):
        link_node = card.select_one('a.c-teaser__link-main[href], a.c-link[href], a[href]')
        if link_node is None:
            continue
        title = _clean(card.select_one('h1, h2, h3')) or _clean(link_node.get('title', ''))
        body = card.select_one('.c-teaser__text p, .c-teaser-story__text p, p')
        deadline = _clean(card.select_one('.c-topline__element.is-date')) or DEFAULT_DEADLINE
        _add(title, link_node.get('href'), body, deadline)

    # pass 3 - defensive: bare slider slides without teaser wrapper
    for slide in soup.select('div.js-slide'):
        anchor = slide.select_one('a.is-internal-link[href], a[href]')
        if anchor is None:
            continue
        title = _clean(slide.select_one('h1, h2, h3')) or _clean(anchor)
        _add(title, anchor.get('href'), slide.select_one('p'))

    # pass 4 - last resort so the harvester never returns empty on a live page
    if not items:
        content = soup.find('main') or soup
        for a in content.find_all('a', href=True):
            title = _clean(a.get_text(' ', strip=True))
            if len(title) >= 12 and '/DE/' in a['href']:
                _add(title, a['href'])

    return items