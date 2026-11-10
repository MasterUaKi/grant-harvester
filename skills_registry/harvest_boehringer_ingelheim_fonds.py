def harvest_boehringer_ingelheim_fonds(html, base_url):
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    FUNDER = 'Boehringer Ingelheim Fonds'
    items = []
    seen = set()

    soup = BeautifulSoup(html, 'html.parser')

    # 1) Injected cards (if present)
    for art in soup.select('#pycognition-injected-grants article'):
        a = art.find('a', href=True)
        title_el = art.find(['h2', 'h3', 'h4'])
        title = title_el.get_text(' ', strip=True) if title_el else (a.get_text(' ', strip=True) if a else '')
        if not title:
            continue
        link = urljoin(base_url, a['href']) if a else base_url
        desc_el = art.find('p')
        desc = desc_el.get_text(' ', strip=True) if desc_el else ''
        key = (title, link)
        if key in seen:
            continue
        seen.add(key)
        items.append({
            'title': title,
            'funder': FUNDER,
            'deadline': 'laufend',
            'link': link,
            'description': desc,
            'target_group': ''
        })

    # 2) Homepage teaser tiles (flex-content blocks)
    for content in soup.select('div.flex-content'):
        parent_a = content.find_parent('a', href=True)
        if not parent_a:
            continue
        title_el = content.select_one('h2.teaser-title')
        if not title_el:
            continue
        # Normalize title: collapse <br/> and <strong> into single spaces
        title = title_el.get_text(' ', strip=True)
        title = ' '.join(title.split())
        if not title:
            continue
        link = urljoin(base_url, parent_a['href'])
        desc_el = content.select_one('.teaser-text')
        desc = desc_el.get_text(' ', strip=True) if desc_el else ''
        key = (title, link)
        if key in seen:
            continue
        seen.add(key)
        items.append({
            'title': title,
            'funder': FUNDER,
            'deadline': 'laufend',
            'link': link,
            'description': desc,
            'target_group': ''
        })

    # 3) DAAD-style result lists (defensive, in case of portal drift)
    for li in soup.select('ul.resultlist li.entry, li[class*="entry"]'):
        a = li.select_one('h2 > a, h3 > a')
        if not a or not a.get('href'):
            continue
        title = a.get_text(' ', strip=True)
        # strip funder span suffix like ' • DAAD'
        for span in a.find_all('span'):
            span.decompose()
        title = a.get_text(' ', strip=True)
        title = ' '.join(title.split())
        if not title:
            continue
        link = urljoin(base_url, a['href'])
        desc_el = li.select_one('p.entry-detail, div.col')
        desc = desc_el.get_text(' ', strip=True) if desc_el else ''
        target = ''
        for dt in li.find_all('dt'):
            if 'status' in dt.get_text(strip=True).lower():
                dd = dt.find_next_sibling('dd')
                if dd:
                    target = dd.get_text(' ', strip=True)
        key = (title, link)
        if key in seen:
            continue
        seen.add(key)
        items.append({
            'title': title,
            'funder': FUNDER,
            'deadline': 'laufend',
            'link': link,
            'description': desc,
            'target_group': target
        })

    # 4) Modern SPA teasers (defensive)
    for card in soup.select('.c-teaser, .s-results__item, article, div[class*="card"]'):
        a = card.find('a', href=True)
        if not a:
            continue
        title_el = card.find(['h2', 'h3', 'h4'])
        title = title_el.get_text(' ', strip=True) if title_el else a.get_text(' ', strip=True)
        title = ' '.join(title.split())
        if not title:
            continue
        link = urljoin(base_url, a['href'])
        desc_el = card.find('p')
        desc = desc_el.get_text(' ', strip=True) if desc_el else ''
        key = (title, link)
        if key in seen:
            continue
        seen.add(key)
        items.append({
            'title': title,
            'funder': FUNDER,
            'deadline': 'laufend',
            'link': link,
            'description': desc,
            'target_group': ''
        })

    return items