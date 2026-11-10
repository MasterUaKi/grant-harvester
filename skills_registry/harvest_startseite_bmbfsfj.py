def harvest_startseite_bmbfsfj(html, base_url):
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    import re
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    seen = set()
    def add(title, link, description, target_group='Not specified'):
        title = re.sub(r'\s+', ' ', title or '').strip()
        link = urljoin(base_url, link) if link else base_url
        if not title or link in seen:
            return
        seen.add(link)
        items.append({
            'title': title,
            'funder': 'Startseite - BMBFSFJ',
            'deadline': 'Not specified',
            'link': link,
            'description': re.sub(r'\s+', ' ', description or '').strip(),
            'target_group': target_group
        })
    for a in soup.select('main .agenda-item-teaser a.text-link, main .aktuelles-module__single-module-wrapper a.flyout-item__link, main .single-teaser a'):
        title = a.get_text(' ', strip=True)
        href = a.get('href')
        if not href or not title:
            continue
        parent = a.find_parent(['div', 'article', 'section', 'li']) or a
        kicker_el = parent.select_one('.kicker, .aktuelles-module__dachzeile')
        if kicker_el:
            kicker = kicker_el.get_text(' ', strip=True)
            if kicker and kicker.lower() not in title.lower():
                title = kicker + ' – ' + title
        context = parent.get_text(' ', strip=True)
        haystack = (title + ' ' + context).lower()
        if any(k in haystack for k in ('wettbewerb', 'förder', 'foerder', 'ausschreibung', 'preis', 'stipendium', 'zuschuss', 'antrag', 'fonds')):
            desc_el = parent.select_one('.agenda-item-paragraph, .aktuelles-module__module-textblock, .single-teaser--text')
            desc = desc_el.get_text(' ', strip=True) if desc_el else context
            target = 'Not specified'
            if 'mixed up' in haystack:
                target = 'Schulen, Kindertagesstätten und Akteure der Kulturellen Bildung'
            add(title, href, desc, target)
    for a in soup.select('.logo-ribbon-item a.logo-item-link'):
        title = a.get_text(' ', strip=True)
        href = a.get('href')
        if not href or not title:
            continue
        low = title.lower()
        if any(k in low for k in ('fonds', 'stiftung', 'jugend stärken', 'jugend staerken', 'bürgerfonds', 'buergerfonds', 'aktion zusammen wachsen')):
            img = a.find_previous('img')
            alt = img.get('alt', '') if img else ''
            target = 'Not specified'
            if 'jugend' in low:
                target = 'Jugendliche'
            elif 'mutter' in low or 'kind' in low:
                target = 'Schwangere/Mütter und Familien'
            elif 'missbrauch' in low:
                target = 'Betroffene sexuellen Missbrauchs'
            elif 'bürgerfonds' in low or 'buergerfonds' in low:
                target = 'Deutsch-französische Bürgerprojekte'
            elif 'aktion zusammen wachsen' in low:
                target = 'Bildungspatenschaften und Integration'
            add(title, href, alt or title, target)
    for a in soup.select('.onlinetools a.module-item-link'):
        title = a.get_text(' ', strip=True)
        href = a.get('href')
        if not href or not title:
            continue
        low = title.lower()
        if any(k in low for k in ('elterngeld', 'kinderzuschlag')):
            parent = a.find_parent('div', class_='module-item-wrapper') or a
            desc_el = parent.select_one('.module-item-description')
            desc = desc_el.get_text(' ', strip=True) if desc_el else title
            target = 'Eltern / werdende Eltern' if 'elterngeld' in low else 'Familien mit Kindern'
            add(title, href, desc, target)
    return items