def harvest_daad_projektf_rderung_f_r_hochschulen_forscher(html, base_url):
    import re
    import json
    from urllib.parse import urljoin, urlparse

    FUNDER = 'DAAD - Projektförderung für Hochschulen & Forscher'
    DEFAULT_TITLE = 'Projektförderung für Hochschulen & Forscher'
    ASK = 'siehe Ausschreibung'

    def clean(t):
        if t is None:
            return ''
        try:
            return ' '.join(str(t).split())
        except Exception:
            return ''

    def norm_url(href):
        h = (href or '').strip()
        if not h or h.startswith('#'):
            return ''
        if h.lower().startswith(('mailto:', 'tel:', 'javascript:', 'data:')):
            return ''
        try:
            u = urljoin(base_url or '', h)
            p = urlparse(u)
        except Exception:
            return ''
        if p.scheme not in ('http', 'https') or not p.netloc:
            return ''
        return p._replace(fragment='').geturl()

    def slug_title(url):
        try:
            segs = [s for s in urlparse(url or '').path.split('/') if s]
        except Exception:
            segs = []
        while segs and segs[-1].lower() in ('index.html', 'index.htm', 'index.php', 'index'):
            segs.pop()
        if not segs:
            return DEFAULT_TITLE
        last = re.sub('[.](html?|php|aspx?)$', '', segs[-1], flags=re.I)
        last = clean(last.replace('-', ' ').replace('_', ' '))
        if not last:
            return DEFAULT_TITLE
        low = last.lower()
        if 'foerderung' in low or 'förderung' in low:
            return DEFAULT_TITLE
        return last[:1].upper() + last[1:]

    soup = None
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html or '', 'html.parser')
    except Exception:
        soup = None

    page_text = ''
    if soup is not None:
        try:
            for tag in soup.find_all(['script', 'style', 'noscript', 'template']):
                tag.decompose()
        except Exception:
            pass
        try:
            page_text = clean(soup.get_text(' ', strip=True))
        except Exception:
            page_text = ''
    if not page_text:
        try:
            page_text = clean(re.sub('<[^>]+>', ' ', html or ''))
        except Exception:
            page_text = ''
    low_page = page_text.lower()

    BLOCK = ('403 forbidden', 'request forbidden by administrative rules', 'forbidden',
             'access denied', 'zugriff verweigert', 'captcha', 'are you a robot',
             'robot check', 'service unavailable', 'too many requests',
             '404 not found', 'seite nicht gefunden', 'page not found')
    blocked = False
    for marker in BLOCK:
        if marker in low_page:
            blocked = True
            break

    DATE_RE = re.compile('[0-9]{1,2}[.][0-9]{1,2}[.][0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2}')
    DEADLINE_KEYS = ('bewerbungsschluss', 'antragsfrist', 'einreichungsfrist',
                     'einsendeschluss', 'bewerbungsfrist', 'stichtag', 'deadline',
                     'frist', 'laufzeit')
    GROUPS = (
        ('Hochschulen', ('hochschule', 'hochschulen', 'universit', 'fachhochschule')),
        ('Promovierende', ('promovier', 'doktorand', 'phd')),
        ('Studierende', ('studierende', 'studierend', 'student')),
        ('Absolventen', ('absolvent', 'alumni')),
        ('Wissenschaftler & Forscher', ('wissenschaftler', 'forscher', 'forschende', 'postdoc', 'nachwuchs')),
    )

    def pick_deadline(text):
        t = clean(text)
        if not t:
            return ASK
        low = t.lower()
        for key in DEADLINE_KEYS:
            idx = low.find(key)
            if idx < 0:
                continue
            window = t[idx:idx + 120]
            m = DATE_RE.search(window)
            if m:
                return clean(m.group(0))
            return ASK
        m = DATE_RE.search(t)
        if m:
            return clean(m.group(0))
        return ASK

    def pick_group(text):
        low = clean(text).lower()
        for label, keys in GROUPS:
            for k in keys:
                if k in low:
                    return label
        return 'Hochschulen & Forscher'

    def build_desc(title, text):
        d = clean(text)
        if title and d.lower().startswith(title.lower()):
            d = d[len(title):]
        d = clean(d.strip(' -|·•,;:/'))
        if len(d) > 480:
            d = d[:480].rsplit(' ', 1)[0] + ' ...'
        if len(d) < 12:
            d = 'Details, Fristen und Antragsmodalitäten auf der DAAD-Programmseite (' + ASK + ').'
        return d

    seen = set()
    items = []

    def add(title, href, text):
        t = clean(title)[:220]
        if len(t) < 4:
            return
        link = norm_url(href)
        if not link or link in seen:
            return
        seen.add(link)
        body = clean(text)
        items.append({
            'title': t,
            'funder': FUNDER,
            'deadline': pick_deadline(body) or ASK,
            'link': link,
            'description': build_desc(t, body),
            'target_group': pick_group(t + ' ' + body),
        })

    JUNK = ('/kontakt', '/impressum', '/datenschutz', '/login', '/suche', '/search',
            '/newsletter', '/presse', '/karriere', '/cookie', '/barrierefreiheit',
            '/sitemap', '/faq', '/leichte-sprache', '/en/')
    KEYWORDS = ('foerder', 'förder', 'projekt', 'programm', 'ausschreibung', 'stipend',
                'grant', 'call', 'bewerbung', 'finanzierung', 'funding', 'frist', 'deadline')

    def kw(txt):
        low = (txt or '').lower()
        for k in KEYWORDS:
            if k in low:
                return True
        return False

    def junk(h):
        lh = (h or '').lower()
        for j in JUNK:
            if j in lh:
                return True
        return False

    if soup is not None and not blocked:
        for s in soup.find_all('script'):
            try:
                st = (s.get('type') or '').lower()
                if 'ld+json' not in st:
                    continue
                raw = (s.string or s.get_text() or '').strip()
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                except Exception:
                    continue
                stack = [data]
                guard = 0
                while stack and guard < 4000:
                    guard += 1
                    cur = stack.pop()
                    if isinstance(cur, list):
                        stack.extend(cur)
                        continue
                    if not isinstance(cur, dict):
                        continue
                    for v in cur.values():
                        if isinstance(v, (dict, list)):
                            stack.append(v)
                    name = cur.get('name') or cur.get('headline')
                    url = cur.get('url') or cur.get('sameAs')
                    if isinstance(name, str) and isinstance(url, str):
                        nm = clean(name)
                        if len(nm) >= 8:
                            add(nm, url, nm + ' ' + clean(cur.get('description', '')))
                    if len(items) >= 200:
                        break
            except Exception:
                continue

    if soup is not None and not blocked and len(items) < 200:
        for a in soup.find_all('a', href=True):
            try:
                href = a.get('href', '')
                if junk(href):
                    continue
                txt = clean(a.get_text(' ', strip=True))
                if len(txt) < 12:
                    continue
                if not (kw(href) or kw(txt)) and len(txt) < 25:
                    continue
                container = a.find_parent(['article', 'li', 'section', 'div']) or a
                ctext = clean(container.get_text(' ', strip=True))
                if len(ctext) > 1200:
                    ctext = txt
                head = container.find(['h2', 'h3', 'h4', 'h5'])
                htxt = clean(head.get_text(' ', strip=True)) if head is not None else ''
                title = txt if len(txt) >= 25 else (htxt if 4 <= len(htxt) <= 200 else txt)
                add(title, href, ctext)
                if len(items) >= 200:
                    break
            except Exception:
                continue

    if soup is not None and not blocked and not items:
        for sel in ('article', '.c-teaser', '[class*="teaser"]', '[class*="card"]',
                    '[class*="list-item"]', '[class*="foerder"]', '[class*="program"]', 'main li'):
            try:
                nodes = soup.select(sel)
            except Exception:
                continue
            for node in nodes:
                try:
                    a = node.find('a', href=True)
                    if a is None:
                        continue
                    href = a.get('href', '')
                    if junk(href):
                        continue
                    ctext = clean(node.get_text(' ', strip=True))
                    if len(ctext) < 20:
                        continue
                    head = node.find(['h2', 'h3', 'h4', 'h5'])
                    title = clean(head.get_text(' ', strip=True)) if head is not None else clean(a.get_text(' ', strip=True))
                    add(title, href, ctext)
                    if len(items) >= 200:
                        break
                except Exception:
                    continue
            if len(items) >= 200:
                break

    if not items:
        link = norm_url(base_url) or (base_url or '')
        if link:
            items.append({
                'title': DEFAULT_TITLE if blocked else slug_title(base_url),
                'funder': FUNDER,
                'deadline': ASK,
                'link': link,
                'description': 'DAAD-Programmseite zur Projektförderung für Hochschulen und Forscher: Übersicht der Förderlinien, Antragsmodalitäten und Fristen (siehe Ausschreibung).',
                'target_group': 'Hochschulen & Forscher',
            })

    return items[:200]