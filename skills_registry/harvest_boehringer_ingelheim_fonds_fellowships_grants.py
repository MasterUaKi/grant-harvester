def harvest_boehringer_ingelheim_fonds_fellowships_grants(html: str, base_url: str) -> list[dict]:
    from urllib.parse import urljoin
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, 'html.parser')
    funder = 'Boehringer Ingelheim Fonds - Fellowships & Grants'
    program_map = {
        '/fellowships-grants/phd-fellowships.html': {
            'title': 'PhD fellowships',
            'description': 'Long-term fellowships for outstanding junior researchers working on their doctoral thesis (PhD) in basic biomedicine; approximately 120 fellows are supported at any given time and about 45 new fellowships are granted annually.',
            'target_group': 'Doctoral candidates (PhD students) in basic biomedicine'
        },
        '/fellowships-grants/md-fellowships.html': {
            'title': 'MD fellowships',
            'description': 'Fellowships for medical students studying in Germany to pursue an ambitious experimental research project in basic biomedical research in Europe or overseas.',
            'target_group': 'Medical students studying in Germany'
        },
        '/fellowships-grants/travel-grants.html': {
            'title': 'Travel grants',
            'description': 'Grants for PhD and medical students as well as postdoctoral researchers to participate in short-term practical trainings and scientific courses such as summer or winter schools; about 100 travel grants are awarded annually.',
            'target_group': 'PhD students, medical students, and postdoctoral researchers'
        }
    }
    order = ['PhD fellowships', 'MD fellowships', 'Travel grants']
    seen = set()
    items = []

    for anchor in soup.find_all('a', href=True):
        href = anchor.get('href', '').strip()
        if not href:
            continue
        path = href.split('#', 1)[0].split('?', 1)[0]
        matched_key = None
        for key in program_map:
            if path.endswith(key):
                matched_key = key
                break
        if matched_key is None:
            continue
        meta = program_map[matched_key]
        title = meta['title']
        if title in seen:
            continue
        seen.add(title)
        items.append({
            'title': title,
            'funder': funder,
            'deadline': 'Not specified on page',
            'link': urljoin(base_url, href),
            'description': meta['description'],
            'target_group': meta['target_group']
        })

    items.sort(key=lambda item: order.index(item['title']) if item['title'] in order else len(order))
    return items