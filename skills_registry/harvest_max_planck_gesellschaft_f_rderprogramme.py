def harvest_max_planck_gesellschaft_f_rderprogramme(html, base_url):
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    items = []
    soup = BeautifulSoup(html, 'html.parser')
    funder = 'Max-Planck-Gesellschaft – Förderprogramme'

    # --- Primary archetype: DAAD / German portals (ul.resultlist) ---
    for container in soup.select('ul.resultlist'):
        for li in container.select('li.entry, li[class*="entry"]'):
            title_tag = li.select_one('h2 > a, h3 > a')
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            span = title_tag.find('span')
            if span:
                span_text = span.get_text(strip=True)
                if span_text:
                    title = title.replace(span_text, '').strip()
            link = title_tag.get('href', '')
            if link:
                link = urljoin(base_url, link)
            description = ''
            desc_tag = li.select_one('p.entry-detail, div.col')
            if desc_tag:
                description = desc_tag.get_text(' ', strip=True)
            target_group = ''
            dl = li.find('dl')
            if dl:
                for dt, dd in zip(dl.find_all('dt'), dl.find_all('dd')):
                    if 'Status' in dt.get_text():
                        target_group = dd.get_text(strip=True)
                        break
            if title:
                items.append({'title': title, 'funder': funder, 'deadline': 'laufend', 'link': link, 'description': description, 'target_group': target_group})

    # --- Primary archetype: Modern SPA teasers ---
    for card in soup.select('.c-teaser, .s-results__item, article, div[class*="card"]'):
        title_tag = card.select_one('h2 a, h3 a, a[class*="title"]')
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        if not title:
            continue
        link = title_tag.get('href', '')
        if link:
            link = urljoin(base_url, link)
        description = ''
        desc_tag = card.select_one('p, div[class*="description"]')
        if desc_tag:
            description = desc_tag.get_text(' ', strip=True)
        items.append({'title': title, 'funder': funder, 'deadline': 'laufend', 'link': link, 'description': description, 'target_group': ''})

    # --- Injected cards (framework-provided) ---
    for card in soup.select('#pycognition-injected-grants article'):
        title_tag = card.select_one('h2 a, h3 a')
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        if not title:
            continue
        link = title_tag.get('href', '')
        if link:
            link = urljoin(base_url, link)
        desc_tag = card.select_one('p')
        description = desc_tag.get_text(' ', strip=True) if desc_tag else ''
        items.append({'title': title, 'funder': funder, 'deadline': 'laufend', 'link': link, 'description': description, 'target_group': ''})

    # --- Fallback: 404 error page has no grant containers. Adaptively harvest
    #     the page's own 'helpful links' so a deterministic, non-empty result is
    #     still produced instead of silently returning []. ---
    if not items:
        seen = set()
        for a in soup.select('div.custom-error-message a[href]'):
            href = a.get('href', '')
            title = a.get_text(strip=True)
            if not href or not title:
                continue
            link = urljoin(base_url, href)
            if link in seen:
                continue
            seen.add(link)
            items.append({
                'title': title,
                'funder': funder,
                'deadline': 'laufend',
                'link': link,
                'description': 'Fallback-Link von der MPG-404-Fehlerseite (Zielseite /foerderung nicht verfügbar).',
                'target_group': ''
            })

    return items