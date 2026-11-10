def harvest_fritz_thyssen_stiftung_stipendien(html: str, base_url: str) -> list[dict]:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    metadata = {
        'Projektförderung': {
            'deadline': 'Not specified',
            'description': 'Project funding for research projects in the foundation funding areas.',
            'target_group': 'Researchers and scholars',
        },
        'Tagungen': {
            'deadline': 'Not specified',
            'description': 'Funding for academic conferences and meetings.',
            'target_group': 'Researchers and academic institutions',
        },
        'Reisebeihilfen': {
            'deadline': 'Not specified',
            'description': 'Travel grants for researchers.',
            'target_group': 'Researchers and scholars',
        },
        'Druckbeihilfen': {
            'deadline': 'Not specified',
            'description': 'Publication subsidies for academic works.',
            'target_group': 'Researchers and scholars',
        },
        'ThyssenLesezeit': {
            'deadline': 'Not specified',
            'description': 'Funding format ThyssenLesezeit.',
            'target_group': 'Researchers and scholars',
        },
        'Sonderprogramme': {
            'deadline': 'Not specified',
            'description': 'Special funding programmes.',
            'target_group': 'Varies by programme',
        },
    }

    order = [
        'Projektförderung',
        'Tagungen',
        'Reisebeihilfen',
        'Druckbeihilfen',
        'ThyssenLesezeit',
        'Sonderprogramme',
    ]

    soup = BeautifulSoup(html, 'html.parser')
    items = []
    seen = set()

    for anchor in soup.find_all('a', href=True):
        title = anchor.get_text(' ', strip=True)
        if title not in metadata:
            continue
        link = urljoin(base_url, anchor['href'])
        if link in seen:
            continue
        seen.add(link)
        meta = metadata[title]
        items.append({
            'title': title,
            'funder': 'Fritz Thyssen Stiftung - Stipendien',
            'deadline': meta['deadline'],
            'link': link,
            'description': meta['description'],
            'target_group': meta['target_group'],
        })

    items.sort(key=lambda x: order.index(x['title']) if x['title'] in order else len(order))
    return items