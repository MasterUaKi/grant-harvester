def harvest_fritz_thyssen_stiftung_projektf_rderung(html: str, base_url: str) -> list[dict]:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    soup = BeautifulSoup(html, 'html.parser')
    funder = 'Fritz Thyssen Stiftung - Projektförderung'
    items = []
    all_text = soup.get_text(' ', strip=True)
    deadline = '1. Februar (Sommersitzung im Juni); 1. September (Wintersitzung im Februar), Datum des Poststempels'
    if '1. Februar' not in all_text or '1. September' not in all_text:
        deadline = 'Siehe Einreichungsfristen auf der Seite'
    row0 = soup.find('section', id='row-0')
    if row0:
        for a in row0.select('ul li a[href]'):
            title = a.get_text(' ', strip=True)
            href = a.get('href')
            if not title or not href:
                continue
            link = urljoin(base_url, href)
            items.append({'title': title, 'funder': funder, 'deadline': deadline, 'link': link, 'description': 'Thematischer Förderbereich, in dem eine Antragstellung im Rahmen der Projektförderung möglich ist; interdisziplinäre Projekte werden begrüßt.', 'target_group': 'Promovierte/habilitierte Forschende an Hochschulen bzw. gemeinnützigen Forschungseinrichtungen mit Bezug zum deutschen Wissenschaftssystem.'})
    for sec in soup.select('section.fce-accordion'):
        h5 = sec.find('h5')
        if not h5:
            continue
        title = h5.get_text(' ', strip=True)
        if title.startswith('Antragstellung '):
            title = title[len('Antragstellung '):]
        if 'Medizin' in title:
            target_group = 'Personen mit MD- und/oder PhD-Abschluss in früher eigenständiger akademischer Laufbahn, von der aufnehmenden Institution unterstützt und mit gesicherter Finanzierung der eigenen Stelle; nicht etablierte Lehrstuhlinhaber:innen/Klinikdirektor:innen.'
            description = 'Projektförderung für medizinische Forschungsvorhaben; in der Regel bis zu drei Jahre, zunächst zwei Jahre bewilligt; klinisch tätige Forschende sollen mindestens 80 Prozent freigestellt werden; Antrag postalisch und zusätzlich elektronisch.'
        else:
            target_group = 'Promovierte/habilitierte Personen an Hochschulen oder gemeinnützigen Forschungseinrichtungen; Nachwuchspromovierte können im Projekt die eigene Stelle beantragen; Projektmitarbeitende können nicht antragsberechtigt sein.'
            description = 'Projektförderung für geistes- und sozialwissenschaftliche Forschungsvorhaben; in der Regel bis zu drei Jahre, zunächst zwei Jahre bewilligt; interdisziplinäre Projekte sind willkommen; Antrag postalisch und zusätzlich elektronisch.'
        items.append({'title': title, 'funder': funder, 'deadline': deadline, 'link': base_url, 'description': description, 'target_group': target_group})
    seen = set()
    unique = []
    for it in items:
        key = (it.get('title'), it.get('link'))
        if key not in seen:
            seen.add(key)
            unique.append(it)
    return unique