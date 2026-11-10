def harvest_deutsche_forschungsgemeinschaft_dfg(html, base_url):
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(' ', strip=True).lower()
    if '404 page not found' in text or 'wir konnten diese seite nicht finden' in text:
        return []

    main = soup.find('main') or soup
    excluded = {
        '/de/suche',
        '/de',
        '/de/foerderung/foerdermoeglichkeiten/programme',
        '/de/foerderung/antrag-foerderprozess/formulare-merkblaetter',
    }
    excluded_norm = {x.rstrip('/') for x in excluded}

    items = []
    seen = set()

    for a in main.find_all('a', href=True):
        href = a.get('href', '').strip()
        title = a.get_text(' ', strip=True)
        if not href or not title:
            continue

        abs_url = urljoin(base_url, href)
        if '/de/foerderung/' not in abs_url:
            continue
        if href.rstrip('/') in excluded_norm:
            continue

        low = abs_url.lower()
        if any(skip in low for skip in ('/suche', '/formulare', '/merkblaetter', '/antrag-foerderprozess')):
            continue
        if len(title) < 5 or title.lower() in {'mehr', 'weiter', 'details', 'link'}:
            continue
        if abs_url in seen:
            continue

        seen.add(abs_url)
        items.append({
            'title': title,
            'funder': 'Deutsche Forschungsgemeinschaft (DFG)',
            'deadline': '',
            'link': abs_url,
            'description': '',
            'target_group': '',
        })

    return items