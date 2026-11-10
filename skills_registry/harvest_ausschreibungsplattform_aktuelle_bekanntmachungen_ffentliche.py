def harvest_ausschreibungsplattform_aktuelle_bekanntmachungen_ffentliche(html, base_url):
    import re
    from urllib.parse import urljoin
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or '', 'html.parser')
    root = soup.find(id='content') or soup
    base = base_url if base_url.endswith('/') else base_url + '/'

    def clean(value):
        return re.sub(r'\s+', ' ', value or '').strip()

    def field(text, label, stops):
        stop = '|'.join(re.escape(s) for s in stops)
        pattern = r'(?<![A-Za-zÄÖÜäöüß])' + re.escape(label) + r'\s*:\s*(.+?)(?=\s*(?:' + stop + r')\s*:|$)'
        match = re.search(pattern, text)
        return clean(match.group(1)) if match else ''

    def span_value(card, title_prefix):
        for node in card.find_all('span'):
            title = (node.get('title') or '').strip().lower()
            if title.startswith(title_prefix):
                value = clean(node.get_text(' ', strip=True))
                if value:
                    return value
        return ''

    HEADER_STOPS = ['Registrierungsnummer', 'Postanschrift', 'Stadt', 'Postleitzahl',
                    'Land, Gliederung (NUTS)', 'Land', 'Kontaktperson', 'Telefon',
                    'E-Mail', 'Internetadresse']
    NO_DEADLINE = 'n/a (keine Frist veröffentlicht)'
    TARGET_GROUP = 'Unternehmen / Bieter (öffentliche Vergabe)'

    items = []
    seen = set()

    for card in root.select('div.card'):
        if card.get('id') == 'footer':
            continue
        anchor = card.select_one('h3 a[href]')
        if anchor is None:
            continue
        title = clean(anchor.get_text(' ', strip=True))
        href = (anchor.get('href') or '').strip()
        if not title or not href:
            continue
        link = href if href.startswith('http') else urljoin(base, href.lstrip('/'))
        if link in seen:
            continue
        seen.add(link)

        place = card.select_one('div.card-place-container')
        place_text = clean(place.get_text(' ', strip=True)) if place else ''
        funder = field(place_text, 'Offizielle Bezeichnung', HEADER_STOPS) or 'unbekannt'
        registration = field(place_text, 'Registrierungsnummer', HEADER_STOPS)
        street = field(place_text, 'Postanschrift', HEADER_STOPS)
        city = field(place_text, 'Stadt', HEADER_STOPS) or span_value(card, 'ort des auftraggebers')
        postal = field(place_text, 'Postleitzahl', HEADER_STOPS)
        nuts = field(place_text, 'Land, Gliederung (NUTS)', HEADER_STOPS)
        contact = field(place_text, 'Kontaktperson', HEADER_STOPS)
        state = span_value(card, 'land des auftraggebers')
        published = span_value(card, 'publikationsdatum')
        dispatched = span_value(card, 'absendedatum')

        cpv_code = ''
        cpv_label = ''
        for node in card.select('div.col-sm-6.col-md-3'):
            match = re.search(r'CPV\s*:?\s*(\d{5,8})', clean(node.get_text(' ', strip=True)))
            if match:
                cpv_code = match.group(1)
                sibling = node.find_next_sibling('div')
                if sibling is not None:
                    cpv_label = clean(sibling.get_text(' ', strip=True))
                break

        fragments = []
        if cpv_code:
            fragments.append('CPV ' + cpv_code + ((' ' + cpv_label) if cpv_label else ''))
        if postal or city:
            fragments.append('Ort: ' + ' '.join(part for part in [postal, city] if part))
        if state:
            fragments.append('Bundesland: ' + state)
        if nuts:
            fragments.append('NUTS: ' + nuts)
        if street:
            fragments.append('Anschrift: ' + street)
        if registration:
            fragments.append('Registrierungsnummer: ' + registration)
        if contact:
            fragments.append('Kontakt: ' + contact)
        if published:
            fragments.append('Publikationsdatum: ' + published)
        if dispatched:
            fragments.append('Absendedatum: ' + dispatched)

        items.append({
            'title': title,
            'funder': funder,
            'deadline': NO_DEADLINE,
            'link': link,
            'description': ' | '.join(fragments),
            'target_group': TARGET_GROUP,
        })

    if not items:
        for anchor in root.find_all('a', href=True):
            href = (anchor.get('href') or '').strip()
            if not re.match(r'^/?\d{6,}_', href):
                continue
            title = clean(anchor.get_text(' ', strip=True))
            if not title:
                continue
            link = href if href.startswith('http') else urljoin(base, href.lstrip('/'))
            if link in seen:
                continue
            seen.add(link)
            items.append({
                'title': title,
                'funder': 'unbekannt',
                'deadline': NO_DEADLINE,
                'link': link,
                'description': 'Fallback: Link aus Uebersichtsliste ohne Detailfelder',
                'target_group': TARGET_GROUP,
            })

    return items