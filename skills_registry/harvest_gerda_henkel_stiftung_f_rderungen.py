def harvest_gerda_henkel_stiftung_f_rderungen(html: str, base_url: str) -> list[dict]:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    soup = BeautifulSoup(html, 'html.parser')
    funder = 'Gerda Henkel Stiftung - Förderungen'
    items = []
    seen = set()

    for a in soup.find_all('a', href=True):
        href = a.get('href', '').strip()
        text = a.get_text(' ', strip=True)
        p = a.find_parent('p')
        context = p.get_text(' ', strip=True) if p else text
        low_href = href.lower()
        low_context = context.lower()

        if ('foerderung' in low_href or 'grants' in low_href or
                'förderbereich' in low_context or 'grants' in low_context):
            link = urljoin(base_url, href)
            if link in seen:
                continue
            seen.add(link)

            if 'grants' in low_href or 'grants' in low_context:
                title = 'Grants information (English)'
            else:
                title = 'Förderbereich'

            items.append({
                'title': title,
                'funder': funder,
                'deadline': 'Not specified',
                'link': link,
                'description': context,
                'target_group': 'Not specified'
            })

    return items