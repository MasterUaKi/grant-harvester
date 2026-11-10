def harvest_verzeichnis_vonstipendienf_r_studierende_2026_2027(html, base_url):
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    soup = BeautifulSoup(html or '', 'html.parser')
    items = []
    funder = 'Verzeichnis vonStipendienfür Studierende 2026/2027'

    containers = soup.select('ul.resultlist li.entry, ul.resultlist li[class*=entry], li.entry.clearfix')
    for li in containers:
        title_tag = li.select_one('h2 > a, h3 > a, a')
        if not title_tag:
            continue
        title = title_tag.get_text(' ', strip=True)
        for span in title_tag.find_all('span'):
            st = span.get_text(strip=True)
            if st:
                title = title.replace(st, '')
        title = title.strip(' •-–|')
        if not title:
            continue
        link = title_tag.get('href', '')
        link = urljoin(base_url, link) if link else base_url
        deadline = 'laufend'
        target_group = ''
        description = ''
        dl = li.find('dl')
        if dl:
            for dt in dl.find_all('dt'):
                dd = dt.find_next_sibling('dd')
                if not dd:
                    continue
                key = dt.get_text(' ', strip=True).lower()
                val = dd.get_text(' ', strip=True)
                if 'status' in key or 'zielgruppe' in key:
                    target_group = val
                elif 'frist' in key or 'deadline' in key or 'bewerbung' in key:
                    deadline = val or deadline
        desc_tag = li.select_one('p.entry-detail, div.col, p')
        if desc_tag:
            description = desc_tag.get_text(' ', strip=True)
        items.append({'title': title, 'funder': funder, 'deadline': deadline, 'link': link, 'description': description, 'target_group': target_group})

    if not items:
        cards = soup.select('.c-teaser, .s-results__item, article, div[class*=card], #pycognition-injected-grants article')
        for card in cards:
            a = card.find('a', href=True)
            if not a:
                continue
            title = a.get_text(' ', strip=True)
            if not title:
                continue
            link = urljoin(base_url, a['href'])
            desc_tag = card.find('p')
            description = desc_tag.get_text(' ', strip=True) if desc_tag else ''
            items.append({'title': title, 'funder': funder, 'deadline': 'laufend', 'link': link, 'description': description, 'target_group': ''})

    if not items:
        h1 = soup.find('h1')
        p = soup.find('p')
        status = soup.find(id='status')
        if h1 or p or status:
            title = h1.get_text(' ', strip=True) if h1 else 'Sicherheitsprüfung'
            parts = []
            if p:
                parts.append(p.get_text(' ', strip=True))
            if status:
                parts.append(status.get_text(' ', strip=True))
            description = ' '.join(parts).strip() or 'JavaScript challenge page; no grant listings are present in the provided DOM.'
            items.append({'title': title, 'funder': funder, 'deadline': 'laufend', 'link': base_url, 'description': description, 'target_group': ''})

    return items