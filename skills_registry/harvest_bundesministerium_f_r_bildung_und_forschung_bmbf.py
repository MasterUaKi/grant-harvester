def harvest_bundesministerium_f_r_bildung_und_forschung_bmbf(html, base_url):
    # BMBF (bmbf.de / bmftr.bund.de) funding-programme harvester.
    # Deliberately free of import statements: the host runtime already injects
    # BeautifulSoup, and a bare import raises ImportError: __import__ not found.
    FUNDER = 'Bundesministerium für Bildung und Forschung (BMBF)'
    TARGET = ('Forschende, Hochschulen, ausseruniversitaere Forschungseinrichtungen '
              'und Unternehmen in Deutschland/EU')
    DIGITS = '0123456789'
    MONTHS = ('januar', 'februar', 'märz', 'maerz', 'april', 'mai', 'juni', 'juli',
              'august', 'september', 'oktober', 'november', 'dezember')
    HINTS = ('frist', 'deadline', 'einreichungsfrist', 'antragsfrist', 'bewerbungsschluss')

    items = []
    if not html or not isinstance(html, str):
        return items

    try:
        soup = BeautifulSoup(html, 'html.parser')
    except Exception:
        return items

    def _text(el):
        if el is None:
            return ''
        try:
            return ' '.join(el.get_text(' ', strip=True).split())
        except Exception:
            return ''

    def _abs(href):
        href = (href or '').strip()
        if not href:
            return ''
        if href.startswith('http://') or href.startswith('https://'):
            return href
        if href.startswith('//'):
            return 'https:' + href
        if not base_url or not isinstance(base_url, str):
            return href
        m = base_url.find('//')
        if m == -1:
            return href
        slash = base_url.find('/', m + 2)
        origin = base_url if slash == -1 else base_url[:slash]
        if href.startswith('/'):
            return origin + href
        base = base_url if base_url.endswith('/') else base_url[:base_url.rfind('/') + 1]
        return base + href

    def _usable(href):
        low = (href or '').lower()
        if not low or low.startswith('#'):
            return False
        for bad in ('/siteglobals/', '/shareddocs/', '/service/', 'javascript:',
                    'mailto:', 'tel:', 'expertensuche', 'autosuggest', '/suche'):
            if bad in low:
                return False
        return True

    def _date_in(text):
        # manual scan (no re module needed): dd.mm.yyyy | dd.mm.yy | dd. Monat yyyy
        low = (text or '').lower()
        n = len(low)
        i = 0
        while i < n - 3:
            if low[i] in DIGITS and i + 2 < n and low[i + 1] in DIGITS and low[i + 2] == '.':
                j = i + 3
                while j < n and low[j] == ' ':
                    j += 1
                k = j
                while k < n and low[k] in DIGITS:
                    k += 1
                if 1 <= k - j <= 2 and k < n and low[k] == '.':
                    m = k + 1
                    while m < n and low[m] == ' ':
                        m += 1
                    p = m
                    while p < n and low[p] in DIGITS:
                        p += 1
                    if p - m in (2, 4):
                        return text[i:p].strip()
                q = j
                while q < n and (low[q].isalpha() or low[q] == '.'):
                    q += 1
                word = low[j:q].strip('. ')
                if word in MONTHS:
                    r = q
                    while r < n and low[r] == ' ':
                        r += 1
                    s = r
                    while s < n and low[s] in DIGITS:
                        s += 1
                    if s - r == 4:
                        return text[i:s].strip()
            i += 1
        return ''

    # ---- hard / soft-404 guard -------------------------------------------------
    # The BMBF portal answers dead URLs with a fully rendered 404 stage that only
    # contains a search form. Never emit items from such a page.
    try:
        if soup.select_one('.c-stage--404, .s-stage--404, .c-stage--error, '
                           '.c-error, .error-page') is not None:
            return items
    except Exception:
        pass

    h1_text = _text(soup.find('h1')).lower()
    if h1_text and ('404' in h1_text or 'nicht gefunden' in h1_text
                    or 'not found' in h1_text or 'fehler' in h1_text):
        return items

    main = soup.find('main') or soup.find('body') or soup
    main_text = _text(main).lower()
    for marker in ('seite nicht gefunden', 'page not found',
                   'die angeforderte seite scheint nicht'):
        if marker in main_text:
            return items

    # ---- programme extraction --------------------------------------------------
    selectors = (
        'main article a[href]',
        'main .c-teaser a[href]',
        'main .c-link-list a[href]',
        'main .c-list a[href]',
        'main .c-paragraph a[href]',
        'main li a[href]',
    )

    seen_links = set()
    seen_titles = set()

    for sel in selectors:
        try:
            nodes = soup.select(sel)
        except Exception:
            continue
        for node in nodes:
            href = node.get('href') or ''
            if not _usable(href):
                continue
            title = _text(node)
            if len(title) < 8:
                continue
            link = _abs(href)
            link_key = link.split('#')[0]
            title_key = title.casefold()
            if not link_key or link_key in seen_links or title_key in seen_titles:
                continue
            seen_links.add(link_key)
            seen_titles.add(title_key)

            try:
                box = node.find_parent(['article', 'li', 'section', 'div']) or node
            except Exception:
                box = node
            context = _text(box)
            para = box.find('p') if box is not None else None
            description = _text(para) or title

            deadline = _date_in(context)
            if not deadline:
                low = context.lower()
                if any(h in low for h in HINTS):
                    deadline = 'siehe Ausschreibung'
                else:
                    deadline = 'laufend'

            items.append({
                'title': title,
                'funder': FUNDER,
                'deadline': deadline,
                'link': link,
                'description': description,
                'target_group': TARGET,
            })

    return items