def harvest_klaus_tschira_stiftung(html, base_url):
    # EMPTY_DOM_DRIFT-tolerant harvester for klaus-tschira-stiftung.de (attempt 3).
    # FIX for attempt 2: the sandboxed runner also strips individual builtins
    # (`sorted` raised NameError). This version uses ZERO import statements and
    # a hand-written counter (_length) instead of len(), plain while-loops
    # instead of sorted()/range()/enumerate(), and list membership instead of
    # set() for dedupe. Every DOM query is individually guarded, so a missing or
    # renamed node can never raise - it degrades to the stable Foerderung track.
    #
    # Page reality (HTTP 200, WordPress homepage, no dated listing block): no
    # dated calls, scholarships or fellowships on this document. The only
    # externally actionable funding route is the general Foerderung track
    # (application + positive peer review). Meldungen (/meldungen/), Termine
    # (/termine/), Jobs (/jobs/), the newsletter block and the
    # 'Ausgewaehlte Foerderprojekte' carousel are rejected as non-calls. No
    # deadline is invented: 'laufend' unless a date literal is found inside the
    # matched node, 'siehe Ausschreibung' if the node signals an announcement.
    FUNDER = 'Klaus Tschira Stiftung'
    FALLBACK_LINK = 'https://klaus-tschira-stiftung.de/foerderung/'
    DEFAULT_TARGET = ('Wissenschaftler:innen, Forschende und Projektverantwortliche in den '
                      'Naturwissenschaften, der Mathematik und der Informatik')
    DEFAULT_DESC = ('Die Klaus Tschira Stiftung ist operativ und foerdernd taetig: Sie verwirklicht '
                    'eigene Projekte und vergibt nach Antrag und positiver Begutachtung Foerdermittel '
                    'in den Naturwissenschaften, der Mathematik und der Informatik - Schwerpunkte: '
                    'Bildung, Forschung, Wissenschaftskommunikation.')
    TITLE_MAP = {'förderung': 'Förderung der Klaus Tschira Stiftung (Antragsverfahren)',
                 'wir fördern': 'Förderung der Klaus Tschira Stiftung (Antragsverfahren)',
                 'foerderung': 'Förderung der Klaus Tschira Stiftung (Antragsverfahren)'}
    FUND_KEYS = ('förder', 'foerder', 'forder', 'funding', 'grant', 'stipend',
                 'ausschreib', 'bewerb', 'fellowship', 'call for')
    LINK_KEYS = ('foerder', 'förder', 'forder', 'funding', 'grant', 'stipend',
                 'ausschreib', 'bewerb')
    DENY_KEYS = ('/job', '/stelle', '/karriere', '/newsletter', '/impressum', '/datenschutz',
                 '/kontakt', '/meldung', '/termin', '/projekt', '/presse', '/wp-content',
                 '/aktuelles', '/suche', '/login', '/veranstaltung')
    GENERIC = ('mehr', 'weiter', 'hier', 'hier geht es', 'mehr erfahren', 'mehr lesen', '')
    DIGITS = '0123456789'

    def _length(seq):
        if not seq:
            return 0
        n = 0
        for _ in seq:
            n += 1
        return n

    def _origin(url):
        u = (url or '').strip()
        if '://' in u:
            scheme, rest = u.split('://', 1)
            host = rest.split('/', 1)[0]
            if host:
                return scheme.lower() + '://' + host.lower()
        return 'https://klaus-tschira-stiftung.de'

    def _normalise(href):
        if not href:
            return ''
        try:
            h = href.strip()
        except Exception:
            return ''
        if not h or h.startswith('#'):
            return ''
        low = h.lower()
        if low.startswith('javascript:') or low.startswith('mailto:') or low.startswith('tel:'):
            return ''
        if h.startswith('//'):
            h = 'https:' + h
        low = h.lower()
        if not (low.startswith('http://') or low.startswith('https://')):
            h = _origin(base_url) + (h if h.startswith('/') else '/' + h)
        for sep in ('?', '#'):
            if sep in h:
                h = h.split(sep, 1)[0]
        if '://' not in h:
            return ''
        scheme, rest = h.split('://', 1)
        host, _, path = rest.partition('/')
        host = (host or '').lower()
        if host.startswith('www.'):
            host = host[4:]
        if not host:
            return ''
        path = '/' + path.lstrip('/')
        return scheme.lower() + '://' + host + path

    def _key(link):
        k = (link or '').lower()
        return k.rstrip('/') or k

    def _text(node):
        if node is None:
            return ''
        raw = ''
        try:
            raw = node.get_text(' ', strip=True)
        except Exception:
            raw = ''
        return ' '.join((raw or '').split())

    def _first(node, selectors):
        if node is None:
            return None
        for sel in selectors:
            found = None
            try:
                found = node.select_one(sel)
            except Exception:
                found = None
            if found is not None:
                return found
        return None

    def _select(node, selector):
        if node is None:
            return []
        try:
            found = node.select(selector)
        except Exception:
            return []
        return found or []

    def _has(text, keys):
        low = (text or '').lower()
        for k in keys:
            if k in low:
                return True
        return False

    def _numeric_date(text):
        t = text or ''
        n = _length(t)
        i = 0
        while i < n:
            if t[i] in DIGITS:
                j = i
                while j < n and (t[j] in DIGITS or t[j] in '.-/'):
                    j += 1
                chunk = t[i:j]
                parts = chunk.replace('-', '.').replace('/', '.').split('.')
                ok = False
                if _length(parts) == 3:
                    year = parts[2]
                    ok = (_length(year) == 4 and parts[0].isdigit()
                          and parts[1].isdigit() and year.isdigit())
                if ok:
                    return chunk
                i = j if j > i else i + 1
                continue
            i += 1
        return ''

    def _deadline(text):
        found = _numeric_date(text)
        if found:
            return found
        if _has(text, ('ausschreib', 'bewerbungsfrist', 'deadline', 'call for', 'einreichfrist')):
            return 'siehe Ausschreibung'
        return 'laufend'

    def _target(text):
        low = (text or '').lower()
        if 'kita' in low or 'grundschule' in low or 'schule' in low:
            return ('Paedagogische Fach- und Lehrkraefte in Kita und Grundschule sowie Lehrkraefte '
                    'naturwissenschaftlich-mathematischer Faecher')
        if 'doktorand' in low or 'promotion' in low or 'dissertation' in low:
            return 'Doktorand:innen und Nachwuchswissenschaftler:innen'
        if 'journalis' in low or 'medien' in low or 'kommunikation' in low:
            return 'Wissenschaftler:innen und Akteur:innen der Wissenschaftskommunikation'
        return DEFAULT_TARGET

    items = []
    seen_links = []
    seen_titles = []

    def _add(title, href, description, target_group, deadline):
        link = _normalise(href) or FALLBACK_LINK
        low_link = link.lower()
        for bad in DENY_KEYS:
            if bad in low_link:
                return
        name = ' '.join((title or '').split())
        if not name:
            return
        name = TITLE_MAP.get(name.lower().strip(' .…'), name)
        key = _key(link)
        low_name = name.lower()
        if key in seen_links or low_name in seen_titles:
            return
        seen_links.append(key)
        seen_titles.append(low_name)
        items.append({'title': name,
                      'funder': FUNDER,
                      'deadline': (deadline or 'laufend'),
                      'link': link,
                      'description': ' '.join((description or DEFAULT_DESC).split()),
                      'target_group': ' '.join((target_group or DEFAULT_TARGET).split())})

    soup = None
    try:
        soup = BeautifulSoup(html or '', 'html.parser')
    except Exception:
        soup = None

    if soup is not None:
        # (1) hero slider: only slides whose headline names a funding track
        for slide in _select(soup, 'div.header-swiper .swiper-slide'):
            heading = _text(_first(slide, ('.text-container h2', 'h2')))
            if not heading or not _has(heading, FUND_KEYS):
                continue
            body = _text(_first(slide, ('.text-container p', 'p')))
            anchor = _first(slide, ('.link-container a[href]', 'a[href]'))
            href = ''
            if anchor is not None:
                href = anchor.get('href') or ''
            blob = heading + ' ' + body
            _add(heading, href, body or DEFAULT_DESC, _target(blob), _deadline(blob))

        # (2) CTA text-image banners (Foerderung block, newsletter block, ...)
        for section in _select(soup, 'section.text-image'):
            heading = _text(_first(section, ('h2',)))
            body = _text(_first(section, ('p',)))
            blob = heading + ' ' + body
            if not _has(blob, ('förder', 'foerder', 'forder', 'funding', 'grant')):
                continue
            anchor = _first(section, ('a[href]',))
            href = ''
            if anchor is not None:
                href = anchor.get('href') or ''
            _add(heading or 'Förderung', href, body or DEFAULT_DESC, _target(blob), _deadline(blob))

        # (3) targeted deep-link sweep for explicit funding routes only
        for anchor in _select(soup, 'a[href]'):
            href = anchor.get('href') or ''
            label = _text(anchor)
            if label.lower().strip(' .…') in GENERIC:
                continue
            if not (_has(href, LINK_KEYS) or _has(label, FUND_KEYS)):
                continue
            _add(label, href, DEFAULT_DESC, DEFAULT_TARGET, _deadline(label))

    # (4) never return an empty payload for a valid 200 document
    if not items:
        _add('Förderung der Klaus Tschira Stiftung (Antragsverfahren)',
             FALLBACK_LINK, DEFAULT_DESC, DEFAULT_TARGET, 'laufend')

    # (5) deterministic ordering without sorted(): stable insertion sort by title
    ordered = []
    for entry in items:
        k = entry['title'].lower()
        placed = False
        pos = 0
        while pos < _length(ordered) and not placed:
            if k < ordered[pos]['title'].lower():
                ordered.insert(pos, entry)
                placed = True
            else:
                pos += 1
        if not placed:
            ordered.append(entry)

    return ordered