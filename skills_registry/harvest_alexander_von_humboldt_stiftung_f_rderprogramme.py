def harvest_alexander_von_humboldt_stiftung_f_rderprogramme(html: str, base_url: str) -> list[dict]:
    import re
    from urllib.parse import urljoin, urlparse
    from bs4 import BeautifulSoup

    FUNDER = 'Alexander von Humboldt-Stiftung - Förderprogramme'
    DEADLINE = 'Unknown'
    DEFAULT_BASE = 'https://www.humboldt-foundation.de/bewerben/foerderprogramme'

    if not isinstance(html, str) or not html.strip():
        return []

    base = (base_url or '').strip() or DEFAULT_BASE
    soup = BeautifulSoup(html, 'html.parser')

    def norm(value):
        return re.sub(r'\s+', ' ', value or '').strip()

    def guess_target_group(title, description):
        t = (title or '').lower()
        blob = t + ' ' + (description or '').lower()
        if 'preis' in t or 'award' in t:
            return 'Bewerber*innen/Nominierte für Preise und Auszeichnungen'
        if 'symposium' in blob or 'symposia' in blob:
            return 'Herausragende junge Wissenschaftler*innen aus Partnerländern'
        if 'residency' in blob:
            return 'Wissenschaftler*innen aller Disziplinen (Residency-Programm)'
        if 'köpfe' in blob or 'koepfe' in blob:
            return 'Spitzenforschende (Zusatzstipendien des BMFTR)'
        if 'postdoc' in blob or 'postdok' in blob:
            return 'Postdocs und erfahrene Forschende aller Nationen und Fachgebiete'
        if 'stipendium' in blob or 'stipendien' in blob:
            return 'Bewerber*innen für Stipendien'
        if 'geschlecht' in blob or 'familie' in blob or 'forscherin' in blob:
            return 'Forscherinnen und Forschende mit Familienaufgaben'
        return 'Forschende aller Nationen und Fachgebiete'

    items = []
    seen = set()

    def add_item(title, href, description):
        title = norm(title)
        href = norm(href)
        description = norm(description)
        if not title or not href:
            return
        if href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
            return
        absolute = urljoin(base, href)
        parsed = urlparse(absolute)
        if not parsed.scheme.startswith('http') or not parsed.netloc:
            return
        if parsed.path in ('', '/'):
            return
        if absolute in seen:
            return
        seen.add(absolute)
        items.append({
            'title': title,
            'funder': FUNDER,
            'deadline': DEADLINE,
            'link': absolute,
            'description': description,
            'target_group': guess_target_group(title, description),
        })

    # 1) Teaser cards: category link-lists and CTA cards
    for art in soup.select('article.teaser'):
        head_el = art.select_one('.teaser__headline')
        text_el = art.select_one('.teaser__text')
        title = norm(head_el.get_text(' ')) if head_el else ''
        description = norm(text_el.get_text(' ')) if text_el else ''
        cta = art.select_one('.teaser__link a[href]')
        if cta is not None:
            add_item(title or cta.get_text(' '), cta['href'], description)
            continue
        for a in art.select('.teaser__list a[href]'):
            label = norm(a.get_text(' '))
            composed = ('%s – %s' % (title, label)) if title else label
            add_item(composed, a['href'], description)

    # 2) Figure teasers: large promo banner with a leading headline anchor
    for art in soup.select('article.figure-teaser'):
        a = art.select_one('a.headline__link[href]') or art.select_one('h3 a[href]')
        if a is None:
            continue
        sub = a.select_one('span.f-w-light')
        full = norm(a.get_text(' '))
        sub_text = norm(sub.get_text(' ')) if sub is not None else ''
        title = norm(full.replace(sub_text, ' ')) if sub_text else full
        if not title:
            title = full
        description = sub_text
        if not description:
            img = art.select_one('figure img[alt]')
            description = norm(img['alt']) if img is not None and img.get('alt') else ''
        add_item(title, a['href'], description)

    # 3) Catch-all: remaining programme links inside <main> (layout drift resilience)
    for a in soup.select('main a[href]'):
        href = a['href']
        if '/bewerben/foerderprogramme/' not in href and '1000-koepfe-plus' not in href:
            continue
        add_item(a.get_text(' '), href, '')

    return items