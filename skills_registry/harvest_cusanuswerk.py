def harvest_cusanuswerk(html, base_url):
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    import re

    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    items = []
    seen = set()
    kw = re.compile('stipend|f(?:ö|oe)rder|grant|funding|bewerb|deadline|frist|termin|studien|promotion|ausland', re.I)

    for a in soup.find_all('a', href=True):
        text = ' '.join(a.get_text(' ', strip=True).split())
        href = a.get('href', '').strip()
        if not text or not href:
            continue
        if href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
            continue
        if not kw.search(text + ' ' + href):
            continue
        if len(text) < 3:
            continue

        link = urljoin(base_url, href)
        parent = a.find_parent(['article', 'li', 'section', 'div'])
        container_text = ' '.join((parent.get_text(' ', strip=True) if parent else text).split())

        title = text
        if parent:
            h = parent.find(['h1', 'h2', 'h3', 'h4', 'h5', 'strong'])
            if h:
                ht = ' '.join(h.get_text(' ', strip=True).split())
                if ht:
                    title = ht

        key = (title.lower(), link)
        if key in seen:
            continue
        seen.add(key)

        deadline = ''
        m = re.search('(?:Deadline|Frist|Bewerbungsschluss|Termin)[^A-Za-z0-9]{0,5}([^.;]{3,80})', container_text, re.I)
        if m:
            deadline = m.group(1).strip()

        target_group = ''
        tm = re.search('(?:Zielgruppe|Für|For)[^A-Za-z0-9]{0,5}([^.;]{3,80})', container_text, re.I)
        if tm:
            target_group = tm.group(1).strip()

        description = container_text if container_text != title else ''
        items.append({
            'title': title,
            'funder': 'Cusanuswerk',
            'deadline': deadline,
            'link': link,
            'description': description[:500],
            'target_group': target_group
        })

    return items