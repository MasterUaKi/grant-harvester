def harvest_ffentlicheausschreibungenaus_dem_land_rheinland_pfalz_jahre(html: str, base_url: str) -> list[dict]:
    import re
    from urllib.parse import urljoin
    from bs4 import BeautifulSoup

    if not html or not isinstance(html, str):
        return []

    soup = BeautifulSoup(html, 'html.parser')
    root = soup.find(id='content') or soup
    items = []
    seen = set()

    for card in root.select('div.card'):
        header = card.find('h3')
        if header is None:
            continue
        anchor = header.select_one('span.offer-header a') or header.find('a', href=True)
        if anchor is None:
            continue
        href = (anchor.get('href') or '').strip()
        title = anchor.get_text(' ', strip=True)
        if not href or not title:
            continue
        link = urljoin(base_url, href)
        if link in seen:
            continue
        seen.add(link)

        funder = reg_no = street = city = postal = nuts = contact = ''
        place = card.select_one('.card-place-container')
        if place is not None:
            for br in place.find_all('br'):
                br.replace_with('\n')
            for line in place.get_text().split('\n'):
                line = line.strip()
                if not line:
                    continue
                key, _, value = line.partition(':')
                key = key.strip().lower()
                value = value.strip()
                if key == 'offizielle bezeichnung':
                    funder = value
                elif key == 'registrierungsnummer':
                    reg_no = value
                elif key == 'postanschrift':
                    street = value
                elif key == 'stadt':
                    city = value
                elif key == 'postleitzahl':
                    postal = value
                elif key.startswith('land, gliederung'):
                    nuts = value
                elif key == 'kontaktperson':
                    contact = value

        published = ''
        for span in card.select('span[title]'):
            if (span.get('title') or '').startswith('Publikationsdatum'):
                published = span.get_text(' ', strip=True)
                if published:
                    break

        cpv = ''
        category = ''
        for div in card.select('div.col-md-3'):
            txt = div.get_text(' ', strip=True)
            if txt.upper().startswith('CPV'):
                cpv = re.sub(r'\D', '', txt)[:8]
                sibling = div.find_next_sibling('div')
                if sibling is not None:
                    category = sibling.get_text(' ', strip=True)
                break

        details = []
        if cpv:
            details.append('CPV %s - %s' % (cpv, category) if category else 'CPV %s' % cpv)
        if city:
            details.append('Ort: %s%s' % (city, ', ' + postal if postal else ''))
        if nuts:
            details.append('NUTS: %s' % nuts)
        if published:
            details.append('Veröffentlicht/Absendung: %s' % published)
        if reg_no:
            details.append('Registrierungsnummer: %s' % reg_no)
        if contact:
            details.append('Kontakt: %s' % contact)
        if funder:
            details.append('Auftraggeber: %s%s' % (funder, ', ' + street if street else ''))

        items.append({
            'title': title,
            'funder': funder or 'Öffentliche Ausschreibungen Rheinland-Pfalz',
            'deadline': 'nicht angegeben (siehe Bekanntmachung)',
            'link': link,
            'description': ' | '.join(details),
            'target_group': 'Unternehmen / Bieter (gewerbliche Anbieter)',
        })

    return items