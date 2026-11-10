def harvest_volkswagenstiftung_unsere_f_rderprogramme(html, base_url):
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin, urlsplit
    import re

    items = []
    if not html or not html.strip():
        return items
    soup = BeautifulSoup(html, 'html.parser')
    funder = 'VolkswagenStiftung - Unsere Förderprogramme'
    base = base_url or 'https://www.volkswagenstiftung.de/'
    main = (soup.find('main', id='content') or soup.find('main')
            or soup.find('div', class_='region-content') or soup.body or soup)
    text_all = main.get_text(' ', strip=True).lower()
    h1 = main.find('h1')
    h1_text = h1.get_text(' ', strip=True).lower() if h1 else ''

    # Deterministic guard against HTTP 404 / error templates: never emit items.
    error_markers = ('seite nicht gefunden', 'nicht gefunden', 'es tut uns leid',
                     'die angefragte webseite oder das dokument')
    if h1_text and any(m in h1_text for m in error_markers):
        return items
    if 'die angefragte webseite oder das dokument' in text_all:
        return items

    date_re = re.compile(r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b')
    open_re = re.compile(r'(laufend|fortlaufend|keine frist|ohne frist|rolling)', re.I)
    skip_paths = {'', '/', '/de', '/en', '/de/foerderung',
                  '/de/foerderung/unsere-foerderprogramme', '/en/funding',
                  '/de/search', '/de/suche'}
    seen = set()

    for a in main.find_all('a', href=True):
        href = (a.get('href') or '').strip()
        if not href or href.startswith(('#', 'mailto:', 'tel:', 'javascript:', 'file:')):
            continue
        absolute = urljoin(base, href)
        parts = urlsplit(absolute)
        if parts.scheme not in ('http', 'https'):
            continue
        if 'volkswagenstiftung.de' not in parts.netloc.lower():
            continue
        path = (parts.path.rstrip('/') or '/').lower()
        if path in skip_paths:
            continue
        if not re.search(r'/(de|en)/foerderung/', path):
            continue
        if re.search(r'/(suche|search|kontakt|impressum|datenschutz|newsletter)(/|$)', path):
            continue
        if path.endswith(('.pdf', '.jpg', '.png', '.webp', '.zip', '.docx')):
            continue
        key = (parts.netloc.lower(), path)
        if key in seen:
            continue
        seen.add(key)

        card = a
        title = ''
        for anc in a.parents:
            name = getattr(anc, 'name', None)
            if name in (None, '[document]', 'main', 'body', 'html'):
                break
            h = anc.find(['h2', 'h3', 'h4', 'h5'])
            if h is not None:
                t = h.get_text(' ', strip=True)
                if t:
                    title = t
                    card = anc
                    break
        if not title:
            title = a.get_text(' ', strip=True)
        title = re.sub(r'\s+', ' ', title).strip()
        if len(title) < 4:
            continue

        card_text = re.sub(r'\s+', ' ', card.get_text(' ', strip=True)).strip()
        desc = ''
        p = card.find('p')
        if p is not None:
            desc = re.sub(r'\s+', ' ', p.get_text(' ', strip=True)).strip()
        if not desc:
            desc = card_text[:400]

        deadline = ''
        d = date_re.search(card_text)
        if d:
            deadline = '%s.%s.%s' % (d.group(1).zfill(2), d.group(2).zfill(2), d.group(3))
        elif open_re.search(card_text):
            deadline = 'laufend / keine feste Frist'

        target_group = ''
        for kw, label in (('promovierend', 'Promovierende'),
                          ('doktorand', 'Doktorand:innen'),
                          ('postdoc', 'Postdocs'),
                          ('nachwuchs', 'Wissenschaftlicher Nachwuchs'),
                          ('habilit', 'Habilitand:innen'),
                          ('studierend', 'Studierende'),
                          ('professor', 'Professor:innen'),
                          ('forschend', 'Forschende')):
            if kw in card_text.lower():
                target_group = label
                break

        items.append({'title': title,
                      'funder': funder,
                      'deadline': deadline,
                      'link': absolute,
                      'description': desc,
                      'target_group': target_group})
    return items