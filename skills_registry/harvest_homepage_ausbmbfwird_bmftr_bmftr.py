def harvest_homepage_ausbmbfwird_bmftr_bmftr(html: str, base_url: str) -> list[dict]:
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return []

    FUNDER = 'Homepage - AusBMBFwird BMFTR! - BMFTR'
    DEADLINE = 'laufend'
    TARGET = 'Studierende, Studieninteressierte und Nachwuchswissenschaftler:innen'
    DEFAULT_BASE = 'https://www.bmftr.bund.de/DE/Forschung/AkademischeLaufbahn/Studium/Finanzierung/Stipendien/begabtenfoerderungswerke/begabtenfoerderungswerke_node.html'
    UMBRELLA_SUFFIX = (' Die 13 Begabtenförderungswerke vergeben einkommensabhängige Stipendien '
                       'orientiert am BAföG zuzüglich 300 Euro monatlicher Studienkostenpauschale; '
                       'die ideelle Förderung ergänzt die finanzielle Förderung. Eine Bewerbung ist '
                       'ausschließlich direkt beim jeweiligen Werk möglich.')
    WORK_DESC = ('Begabtenförderungswerk im Hochschulbereich: finanzielle und ideelle Förderung '
                 'begabter Studierender; Bewerbung direkt beim Werk.')
    WORK_DESC_EXTRA = ' Der verlinkte Einstieg verweist auf die Ausbildungsförderung des Werkes.'
    RELATED = {
        'BAföG': ('Gesetzliche Ausbildungsförderung nach dem BAföG; Antrag beim zuständigen Amt für Ausbildungsförderung.', 'Studierende in der Erstausbildung'),
        'Aufstiegsstipendium': ('Stipendium für Berufserfahrene mit abgeschlossener Ausbildung oder mehrjähriger Berufspraxis vor dem Studium.', 'Berufserfahrene Studieninteressierte'),
        'Weiterbildungsstipendium': ('Förderung der beruflichen Weiterbildung besonders begabter junger Fachkräfte.', 'Junge Fachkräfte mit abgeschlossener Ausbildung'),
        'Promotionsstipendium': ('Stipendien für die Promotion, vergeben über die Begabtenförderungswerke.', 'Doktorandinnen und Doktoranden'),
        'Stipendien für Auszubildende': ('Stipendien der Begabtenförderungswerke für Auszubildende.', 'Auszubildende'),
    }
    RELATED_DEFAULT = ('Verwandtes Förderangebot des BMFTR (Detailseite).', TARGET)
    base = base_url or DEFAULT_BASE

    def clean(txt):
        return ' '.join((txt or '').split())

    def abs_url(href):
        href = (href or '').strip()
        if not href:
            return base
        if href.startswith('//'):
            return 'https:' + href
        if href.startswith('http://') or href.startswith('https://'):
            return href
        if href.startswith('/'):
            parts = base.split('/')
            if len(parts) >= 3:
                return parts[0] + '//' + parts[2] + href
            return href
        if base.endswith('/'):
            return base + href
        return base.rsplit('/', 1)[0] + '/' + href

    items = []
    seen = set()

    def add(title, href, desc, target):
        title = clean(title)
        if not title:
            return
        key = title.casefold()
        if key in seen:
            return
        seen.add(key)
        items.append({
            'title': title,
            'funder': FUNDER,
            'deadline': DEADLINE,
            'link': abs_url(href),
            'description': clean(desc),
            'target_group': target,
        })

    soup = BeautifulSoup(html or '', 'html.parser')
    root = soup.select_one('#content') or soup.select_one('main') or soup

    h1 = root.select_one('h1.l-intro__headline') or root.select_one('h1')
    title_text = clean(h1.get_text(' ', strip=True)) if h1 is not None else ''

    lead = ''
    intro = root.select_one('.l-intro__text')
    if intro is not None:
        for p in intro.find_all('p'):
            txt = clean(p.get_text(' ', strip=True))
            if len(txt) > len(lead):
                lead = txt

    if title_text:
        add('Stipendien der ' + title_text + ' (akademische Begabtenförderung)',
            None, lead + UMBRELLA_SUFFIX, TARGET)

    works = root.select('ul.js-content-highlighted__end-column > li > a')
    if not works:
        works = [a for a in root.select('.l-article__content a.RichTextExtLink')
                 if 'stipendiumplus.de' not in (a.get('href') or '')]

    for a in works:
        href = a.get('href') or ''
        name = clean(a.get_text(' ', strip=True))
        low = (href + ' ' + (a.get('title') or '')).lower()
        desc = WORK_DESC
        if 'ausbildung' in low or 'auszubildende' in low:
            desc += WORK_DESC_EXTRA
        add(name + ' – Stipendium der Begabtenförderung', href, desc, TARGET)

    for a in root.select('div.l-module-wrapper--list a.c-list-icon__link'):
        name = clean(a.get_text(' ', strip=True))
        if not name:
            continue
        desc, target = RELATED.get(name, RELATED_DEFAULT)
        add(name, a.get('href') or '', desc, target)

    return items