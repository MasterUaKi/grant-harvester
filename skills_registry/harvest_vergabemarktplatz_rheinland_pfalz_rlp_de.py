def harvest_vergabemarktplatz_rheinland_pfalz_rlp_de(html, base_url):
    import re
    from urllib.parse import urljoin
    from bs4 import BeautifulSoup

    items = []
    seen = set()
    if not html:
        return items

    soup = BeautifulSoup(html, 'html.parser')
    root = soup.find(id='contentContainer') or soup.find('main') or soup

    def clean(node):
        if node is None:
            return ''
        return re.sub(r'\s+', ' ', node.get_text(' ', strip=True)).strip()

    def cell_date(cell):
        if cell is None:
            return ''
        abbr = cell.find('abbr')
        raw = abbr.get('title') if abbr is not None and abbr.get('title') else clean(cell)
        raw = re.sub(r'\s+', ' ', raw or '').strip()
        if not raw:
            return ''
        if 'nicht vorhanden' in raw.lower():
            return 'nv'
        return raw.replace(' Uhr', '').replace(' um ', ' ').strip()

    def target_group_for(procedure, title):
        blob = (procedure + ' ' + title).lower()
        if ('langholz' in blob or 'forsteinrichtung' in blob or 'pflanzenbeschaffung' in blob
                or 'bodenschutzkalkung' in blob or 'lwaldg' in blob or 'forstamtsbereich' in blob):
            return 'Forstunternehmen, Holz- und Dienstleistungsbetriebe'
        if 'bewachungsdienst' in blob:
            return 'Sicherheitsdienstleister (Bewachungsgewerbe)'
        if 'feuerl\u00f6scher' in blob or 'wartung' in blob:
            return 'Wartungs- und Brandschutzdienstleister'
        if '\u00f6lspuren' in blob:
            return 'Entsorgungs- und Umweltserviceunternehmen'
        if 'gr\u00fcnpflege' in blob:
            return 'Landschafts- und Gr\u00fcnpflegebetriebe'
        return 'Bauunternehmen / gewerbliche Bieter (VOB/A, VgV, UVgO)'

    table = None
    for cand in root.find_all('table'):
        if 'Kurzbezeichnung' in clean(cand.find('thead')):
            table = cand
            break
    if table is None:
        return items

    tbody = table.find('tbody')
    if tbody is None:
        return items

    for row in tbody.find_all('tr', recursive=False):
        cells = row.find_all('td', recursive=False)
        if len(cells) < 6:
            continue

        title = clean(cells[2])
        anchor = cells[5].find('a', href=True)
        if not title and anchor is not None:
            title = (anchor.get('aria-label') or anchor.get('title') or '').strip()
        if not title:
            continue

        funder = clean(cells[4])
        published = cell_date(cells[0])
        deadline = cell_date(cells[1]) or 'nv'

        type_cell = cells[3]
        for ab in type_cell.find_all('abbr'):
            ab.replace_with(ab.get('title') or ab.get_text() or '')
        procedure = re.sub(r'\s+', ' ', type_cell.get_text(' ', strip=True)).strip()

        link = ''
        if anchor is not None:
            link = urljoin(base_url, anchor['href'].strip())
        if not link:
            link = urljoin(base_url, '/VMPCenter/company/welcome.do')

        fragments = [procedure] if procedure else []
        if published:
            fragments.append('ver\u00f6ffentlicht am ' + published + ' Uhr')
        if funder:
            fragments.append('Vergabestelle: ' + funder)
        description = '; '.join(fragments).strip()
        if not description:
            description = 'Bekanntmachung auf dem Vergabemarktplatz Rheinland-Pfalz'

        key = link or title
        if key in seen:
            continue
        seen.add(key)

        items.append({
            'title': title,
            'funder': funder or 'Vergabemarktplatz Rheinland-Pfalz (rlp.de)',
            'deadline': deadline,
            'link': link,
            'description': description,
            'target_group': target_group_for(procedure, title),
        })

    return items