def harvest_robert_bosch_stiftung(html: str, base_url: str) -> list[dict]:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    soup = BeautifulSoup(html, 'html.parser')
    funder = 'Robert Bosch Stiftung'
    items = []
    seen = set()

    def add_item(title, link, description, target_group, deadline='Not specified'):
        title = (title or '').strip()
        link = (link or '').strip()
        if not title:
            return
        key = (title, link)
        if key in seen:
            return
        seen.add(key)
        items.append({
            'title': title,
            'funder': funder,
            'deadline': deadline,
            'link': link,
            'description': (description or '').strip(),
            'target_group': (target_group or 'Not specified').strip(),
        })

    # Current call/application links
    for a in soup.select('a[href]'):
        label = a.get_text(' ', strip=True)
        href = (a.get('href') or '').strip()
        if not label or not href:
            continue
        low_href = href.lower()
        low_label = label.lower()
        if 'ausschreibung' not in low_label and 'deutscher-schulpreis' not in low_href:
            continue
        link = urljoin(base_url, href)
        target = 'Schulen' if ('schulpreis' in low_label or 'deutscher-schulpreis' in low_href) else 'Not specified'
        add_item(label, link, label, target, 'Not specified on page')

    # Funding areas from the 'Fördergebiete' section
    heading = soup.find(id='foerdergebiete')
    if heading:
        section = heading.find_parent('section')
        if section:
            target_map = {
                'Gesundheit': 'Organisationen im Gesundheitswesen',
                'Bildung': 'Bildungsorganisationen und Schulen',
                'Globale Fragen': 'Organisationen und zivilgesellschaftliche Akteure',
                'Weitere Förderungen': 'Zivilgesellschaftliche Akteure in der Ukraine',
            }
            for card in section.select('.icon-card'):
                h = card.select_one('.icon-card__headline')
                if not h:
                    continue
                title = h.get_text(' ', strip=True)
                body = card.select_one('.icon-card__body')
                desc = body.get_text(' ', strip=True) if body else ''
                link = urljoin(base_url, '#foerdergebiete')
                add_item(title, link, desc, target_map.get(title, 'Not specified'))

    return items