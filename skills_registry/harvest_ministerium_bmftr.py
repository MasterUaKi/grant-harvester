def harvest_ministerium_bmftr(html: str, base_url: str) -> list[dict]:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    import re

    soup = BeautifulSoup(html, 'html.parser')
    items = []
    seen = set()
    funding_re = re.compile(r'förder|foerder|ausschreib|call|grant|funding|zuwendung|projektförder|projektfoerder|förderprogramm|foerderprogramm', re.I)
    for a in soup.find_all('a', href=True):
        title = ' '.join(a.get_text(' ', strip=True).split())
        href = a.get('href', '').strip()
        if not title or not href:
            continue
        if not funding_re.search(title) and not funding_re.search(href):
            continue
        link = urljoin(base_url, href)
        if link in seen:
            continue
        seen.add(link)
        container = a.find_parent(['li', 'div', 'article', 'section', 'p']) or a
        context = ' '.join(container.get_text(' ', strip=True).split())
        description = context if context != title else ''
        items.append({
            'title': title,
            'funder': 'Ministerium - BMFTR',
            'deadline': '',
            'link': link,
            'description': description,
            'target_group': ''
        })
    return items