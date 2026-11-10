def harvest_helmholtz_gemeinschaft_deutscher_forschungszentren(html: str, base_url: str) -> list[dict]:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    soup = BeautifulSoup(html, 'html.parser')
    page_text = soup.get_text(' ', strip=True).lower()
    if 'seite nicht gefunden' in page_text or 'page not found' in page_text:
        return []
    items = []
    seen = set()
    selectors = ['article', 'div.card', 'div.teaser', 'li.grant', 'div[class*=funding]', 'div[class*=foerder]', 'div[class*=grant]']
    for node in soup.select(','.join(selectors)):
        title_el = node.select_one('h1, h2, h3, h4, .headline__heading')
        if title_el is None:
            continue
        title = title_el.get_text(' ', strip=True)
        if not title or title.lower() in ('404', 'seite nicht gefunden', 'page not found'):
            continue
        link_el = node.select_one('a[href]')
        link = urljoin(base_url, link_el['href']) if link_el is not None else base_url
        if link in seen:
            continue
        seen.add(link)
        desc_el = node.select_one('p')
        description = desc_el.get_text(' ', strip=True) if desc_el is not None else ''
        text = node.get_text(' ', strip=True)
        low = text.lower()
        deadline = ''
        for marker in ('deadline', 'frist', 'bewerbungsschluss'):
            idx = low.find(marker)
            if idx != -1:
                deadline = text[idx:idx + 80].strip()
                break
        target_group = ''
        if 'nachwuchs' in page_text or 'early career' in page_text:
            target_group = 'Nachwuchskräfte / early-career researchers'
        items.append({
            'title': title,
            'funder': 'Helmholtz-Gemeinschaft Deutscher Forschungszentren',
            'deadline': deadline,
            'link': link,
            'description': description,
            'target_group': target_group
        })
    return items