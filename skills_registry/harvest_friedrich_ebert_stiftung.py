def harvest_friedrich_ebert_stiftung(html: str, base_url: str) -> list[dict]:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    import re

    soup = BeautifulSoup(html, 'html.parser')
    items = []
    seen = set()
    grant_pattern = re.compile(r'(stipend|stipendien|studienf(?:oe|ö)rderung|f(?:oe|ö)rderung)', re.I)
    block_pattern = re.compile(r'(veranstaltungen|events|presse|stellenangebote|publikationen|archiv|bibliothek|kontakt|impressum|datenschutz|sitemap|login)', re.I)

    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        text = ' '.join(a.get_text(' ', strip=True).split())
        if not href or href.startswith(('javascript:', 'mailto:', 'tel:')):
            continue
        full = urljoin(base_url, href)
        combined = f'{text} {full}'
        if not grant_pattern.search(combined):
            continue
        if block_pattern.search(full) or block_pattern.search(text):
            continue
        if full in seen:
            continue
        seen.add(full)
        items.append({
            'title': text or 'Friedrich-Ebert-Stiftung funding opportunity',
            'funder': 'Friedrich-Ebert-Stiftung',
            'deadline': '',
            'link': full,
            'description': '',
            'target_group': ''
        })
    return items