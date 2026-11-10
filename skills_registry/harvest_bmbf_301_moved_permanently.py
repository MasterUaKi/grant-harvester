def harvest_bmbf_301_moved_permanently(html: str, base_url: str) -> list[dict]:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    soup = BeautifulSoup(html, 'html.parser')
    rules = [
        {
            'fragments': ['forschungszulage'],
            'title': 'Forschungszulage',
            'description': 'Die Forschungszulage ist eine unbürokratische Fördermöglichkeit für Forschungs- und Entwicklungsprojekte von Unternehmen.',
            'target_group': 'Unternehmen mit Forschungs- und Entwicklungsprojekten',
        },
        {
            'fragments': ['innovativehochschule'],
            'title': 'Innovative Hochschule',
            'description': 'Die Bund-Länder-Initiative fördert den Transfer von Ideen, Wissen und Ergebnissen aus den Hochschulen in die Praxis.',
            'target_group': 'Hochschulen und Praxispartner',
        },
        {
            'fragments': ['agenturfuersprunginnovationen', 'sprunginnovation'],
            'title': 'Bundesagentur für Sprunginnovationen (SPRIND)',
            'description': 'Die Bundesagentur für Sprunginnovationen (SPRIND) unterstützt dabei, zukunftsweisende Erfindungen und Ideen voranzubringen.',
            'target_group': 'Innovatorinnen und Innovatoren, Forschende und Unternehmen',
        },
    ]

    items = []
    seen = set()

    for a in soup.find_all('a', href=True):
        href = a.get('href', '').strip()
        if not href:
            continue

        text = ' '.join(a.get_text(' ', strip=True).split())
        haystack = (href + ' ' + text).lower()

        matched = None
        for rule in rules:
            if any(fragment in haystack for fragment in rule['fragments']):
                matched = rule
                break

        if matched is None:
            lower_text = text.lower()
            if not any(k in lower_text for k in ['förder', 'forschungszulage', 'sprunginnovation', 'innovative hochschule']):
                continue
            title = text
            description = text
            target_group = 'Not specified'
        else:
            title = matched['title']
            description = matched['description']
            target_group = matched['target_group']

        link = urljoin(base_url, href)
        if link in seen:
            continue
        seen.add(link)

        items.append({
            'title': title,
            'funder': 'Bundesministerium für Forschung, Technologie und Raumfahrt (BMFTR)',
            'deadline': 'Not specified',
            'link': link,
            'description': description,
            'target_group': target_group,
        })

    return items