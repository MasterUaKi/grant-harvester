def harvest_startseite_stipendienkompass(html: str, base_url: str) -> list[dict]:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    soup = BeautifulSoup(html, 'html.parser')
    items = []
    funder = 'Startseite - Stipendienkompass'

    def clean(text):
        return ' '.join((text or '').split()).strip()

    for section in soup.find_all('section'):
        text = clean(section.get_text(' ', strip=True))
        if 'Schülerstipendien: Chancen, Wege, Möglichkeiten' in text:
            deadline = ''
            for p in section.find_all('p'):
                pt = clean(p.get_text(' ', strip=True))
                if pt.startswith('Am '):
                    deadline = clean(pt.split(' laden')[0].replace('Am ', '', 1))
                    break
            link = ''
            for a in section.find_all('a', href=True):
                href = a['href']
                if 'zoom.us' in href:
                    link = urljoin(base_url, href)
                    break
            desc = ''
            for p in section.find_all('p'):
                pt = clean(p.get_text(' ', strip=True))
                if 'digitalen Veranstaltung' in pt:
                    desc = pt
                    break
            target = ''
            for p in section.find_all('p'):
                pt = clean(p.get_text(' ', strip=True))
                if 'richtet sich insbesondere an' in pt:
                    target = pt
                    break
            items.append({
                'title': 'Schülerstipendien: Chancen, Wege, Möglichkeiten',
                'funder': funder,
                'deadline': deadline,
                'link': link,
                'description': desc,
                'target_group': target
            })
            break

    for a in soup.find_all('a', href=True):
        label = clean(a.get('title', '')) or clean(a.get_text(' ', strip=True))
        href = a['href']
        if label == 'Stipendienüberblick' or 'stipendienueberblick' in href:
            items.append({
                'title': 'Stipendienüberblick',
                'funder': funder,
                'deadline': '',
                'link': urljoin(base_url, href),
                'description': 'Informationsservice mit Überblick über Fördermöglichkeiten in der deutschen Stipendienlandschaft.',
                'target_group': 'Schülerinnen und Schüler, Studierende, Eltern, Lehrkräfte und weitere Bildungsakteurinnen und -akteure'
            })
            break

    for section in soup.find_all('section'):
        text = clean(section.get_text(' ', strip=True))
        if 'Stipendium-O-Mat' in text:
            link = ''
            for a in section.find_all('a', href=True):
                href = a['href']
                if 'stipendium-o-mat' in href:
                    link = urljoin(base_url, href)
                    break
            desc = ''
            for p in section.find_all('p'):
                pt = clean(p.get_text(' ', strip=True))
                if 'zeigt verschiedene Möglichkeiten' in pt:
                    desc = pt
                    break
            items.append({
                'title': 'Der Stipendium-O-Mat: Welches Stipendium passt zu dir?',
                'funder': funder,
                'deadline': '',
                'link': link,
                'description': desc,
                'target_group': 'Studieninteressierte und Personen, die ein Studium in Deutschland planen'
            })
            break

    seen = set()
    unique = []
    for item in items:
        key = (item.get('title', ''), item.get('link', ''))
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique