def harvest_deutsches_vergabeportal_dtvp_e_vergabe_plattform(html: str, base_url: str) -> list[dict]:
    '''Harvest opportunity channels from the DTVP homepage.

    The DTVP homepage publishes no grant programmes: it is the public front-end
    of the German e-procurement (E-Vergabe) platform. The routine therefore
    returns the deterministic set of tender/opportunity entry points instead of
    grant records: the live tender-search endpoint derived from the homepage
    search form, the CTA tiles and the notification-service promo.
    '''
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin, urlsplit, urlunsplit, urlencode, parse_qsl

    SOURCE = 'Deutsches Vergabeportal | DTVP | E-Vergabe-Plattform'
    base_url = base_url or 'https://dtvp.de/'

    def clean_text(node):
        if node is None:
            return ''
        return ' '.join(node.get_text(' ', strip=True).split()).strip(' .:')

    def clean_url(href):
        if not href:
            return ''
        parts = urlsplit(urljoin(base_url, href))
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                 if not k.lower().startswith('utm_')]
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ''))

    soup = BeautifulSoup(html or '', 'html.parser')
    main = soup.find('main', id='site-main') or soup
    items = []
    seen = set()

    def add(title, link, description, target_group, deadline='n/a (laufend)'):
        title = ' '.join((title or '').split()).strip(' .:')
        link = clean_url(link) or base_url
        if not title or link in seen:
            return
        seen.add(link)
        items.append({
            'title': title,
            'funder': SOURCE,
            'deadline': deadline,
            'link': link,
            'description': ' '.join((description or '').split()).strip(),
            'target_group': ' '.join((target_group or '').split()).strip() or 'n/a',
        })

    # (1) Live tender-search endpoint rebuilt from the homepage search form.
    form = main.find('form', id='search_ausschreibungen')
    if form is not None:
        params = []
        for field in form.find_all('input'):
            name = field.get('name')
            itype = (field.get('type') or 'text').lower()
            if not name or itype in ('text', 'search', 'submit', 'button'):
                continue
            params.append((name, field.get('value') or ''))
        action = form.get('action') or base_url
        if params:
            action = action + ('&' if '?' in action else '?') + urlencode(params)
        add('Aktuelle Ausschreibungen durchsuchen',
            action,
            'Oeffentliche Ausschreibungen im DTVP; Volltextsuche ueber den '
            'Parameter searchString. Kein Foerderprogramm, sondern eine '
            'Ausschreibungsdatenbank.',
            'Bieter/Unternehmen und oeffentliche Auftraggeber')

    # (2) CTA tiles of the intro block (incl. the right-hand mini tiles).
    for tile in main.select('div.bg-light'):
        heading = tile.find(['h2', 'h3', 'h4', 'h5'])
        anchor = tile.find('a', href=True)
        if heading is None or anchor is None:
            continue
        badge = tile.select_one('.highlight-text')
        paragraph = tile.find('p')
        desc = [clean_text(paragraph)]
        cta = clean_text(anchor)
        if cta:
            desc.append('CTA: ' + cta)
        add(clean_text(heading),
            anchor.get('href'),
            ' '.join(part for part in desc if part),
            clean_text(badge) if badge is not None else 'n/a')

    # (3) Notification / newsletter promo box.
    for box in main.select('div.newsletterreg'):
        heading = box.find(['h2', 'h3', 'h4', 'h5'])
        anchor = box.find('a', href=True)
        if heading is None or anchor is None:
            continue
        desc = [clean_text(box.find('p')), 'CTA: ' + clean_text(anchor)]
        add(clean_text(heading),
            anchor.get('href'),
            ' '.join(part for part in desc if part),
            'Bieter/Unternehmen')

    return items