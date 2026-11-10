def harvest_auftr_ge_f_r_ihre_branche_ffentlicheausschreibungen(html, base_url):
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    import re
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    seen = set()
    funder = 'Aufträge für Ihre Branche | ÖffentlicheAusschreibungen'
    marker = None
    for text in soup.find_all(string=re.compile(r'Oft\s+gesucht')):
        marker = text
        break
    container = marker.find_parent('p') if marker else None
    if container is None:
        container = soup
    links = container.find_all('a', href=True)
    if marker is None:
        links = [a for a in soup.find_all('a', href=True) if re.search(r'/(ausschreibungen-|auftraege-ausschreibungen)', a.get('href', ''))]
    for a in links:
        href = a.get('href', '')
        title = a.get_text(' ', strip=True)
        if not title or href in seen:
            continue
        if marker is None and not re.search(r'/(ausschreibungen-|auftraege-ausschreibungen)', href):
            continue
        seen.add(href)
        items.append({
            'title': title,
            'funder': funder,
            'deadline': '',
            'link': urljoin(base_url, href),
            'description': 'Branchenspezifische Suche nach öffentlichen Ausschreibungen.',
            'target_group': title,
        })
    return items