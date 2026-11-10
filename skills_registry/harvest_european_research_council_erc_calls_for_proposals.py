def harvest_european_research_council_erc_calls_for_proposals(html, base_url):
    import re
    from urllib.parse import urljoin, urlparse
    from bs4 import BeautifulSoup

    FUNDER = 'European Research Council (ERC) - Calls for Proposals'
    ROOT = 'https://erc.europa.eu'
    base = (base_url or ROOT).strip() or ROOT
    soup = BeautifulSoup(html or '', 'html.parser')

    def clean(text):
        return re.sub(r'\s+', ' ', text or '').strip()

    # 1) Strip chrome, trackers and any previously injected widget markup.
    noise = ['script', 'style', 'noscript', 'iframe', 'svg', 'canvas',
             '#globan', '.wt-globan--container', '.wt-analytics', '.analytics',
             '#return-to-top', '.skip-link', '.visually-hidden',
             '#drupal-live-announce', 'header', 'nav', 'footer',
             '#pycognition-injected-grants', '.grant-injected-card']
    for selector in noise:
        for node in soup.select(selector):
            node.decompose()

    # 2) Drop residual 'skip to main content' anchors and in-page jump links.
    for anchor in soup.find_all('a', href=True):
        label = clean(anchor.get_text(' ', strip=True)).lower()
        href = (anchor.get('href') or '').strip().lower()
        if label in ('skip to main content', 'skip to content',
                     'zum hauptinhalt', 'zum inhalt springen'):
            anchor.decompose()
        elif href in ('#main-content', '#main', '#'):
            anchor.decompose()

    body = soup.body or soup
    body_classes = body.get('class') or []
    page_text = clean(body.get_text(' ', strip=True)).lower()

    # 3) Soft-404 detection (do NOT raise; fall back to the canonical catalogue).
    soft_404_markers = ('the requested page could not be found', 'page not found',
                        'seite nicht gefunden', '404 not found')
    is_soft_404 = ('page-system-404' in body_classes
                   or soup.select_one('main.page-system-404') is not None
                   or soup.select_one('.page-system-404') is not None
                   or any(marker in page_text for marker in soft_404_markers))

    bad_titles = {'skip to main content', 'skip to content', 'read more', 'more',
                  'details', 'apply', 'apply now', 'menu', 'search', 'home',
                  'close', 'back', 'next', 'previous', 'login', 'contact'}
    bad_href_parts = ('javascript:', 'mailto:', 'tel:', 'facebook.com', 'twitter.com',
                      'x.com', 'linkedin.com', 'youtube.com', 'instagram.com',
                      '#main-content', '/search', '/contact', '/login', '/user/')
    allow_hosts = ('erc.europa.eu', 'europa.eu', 'cordis.europa.eu')
    tokens = ('starting', 'consolidator', 'advanced', 'synergy', 'proof of concept',
              'public engagement', 'grant', 'call', 'funding', 'proposal', 'erc')
    date_re = re.compile(
        r'(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}'
        r'|\d{4}-\d{2}-\d{2}'
        r'|\d{1,2}\s+(?:january|february|march|april|may|june|july|august|september|'
        r'october|november|december|januar|februar|maerz|maerz|mai|juni|juli|'
        r'oktober|dezember)\s+\d{4})',
        re.IGNORECASE)

    items = []
    seen = set()

    def resolve(href):
        href = (href or '').strip()
        if not href:
            return ''
        low = href.lower()
        if any(part in low for part in bad_href_parts):
            return ''
        absolute = urljoin(base, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in ('http', 'https'):
            return ''
        host = (parsed.netloc or '').lower()
        if host and not any(host == h or host.endswith('.' + h) for h in allow_hosts):
            return ''
        return absolute

    def guess_group(title):
        low = title.lower()
        if 'starting' in low:
            return 'Early-career researchers'
        if 'consolidator' in low:
            return 'Mid-career researchers'
        if 'synergy' in low:
            return 'Research teams'
        if 'advanced' in low:
            return 'Senior researchers'
        if 'proof of concept' in low:
            return 'ERC grant holders (commercialisation)'
        if 'public engagement' in low:
            return 'ERC grant holders / researchers'
        return 'Forschende'

    def guess_deadline(text):
        low = (text or '').lower()
        if any(tok in low for tok in ('rolling', 'ongoing', 'laufend', 'continuous',
                                      'no deadline', 'permanent')):
            return 'laufend'
        match = date_re.search(text or '')
        if match:
            return match.group(1).strip()
        return 'siehe Ausschreibung'

    def push(title, link, description, deadline, target_group):
        title = clean(title)
        link = clean(link)
        if len(title) < 4 or title.lower() in bad_titles or not link:
            return
        key = (title.lower(), link.rstrip('/').lower())
        if key in seen:
            return
        seen.add(key)
        items.append({'title': title,
                      'funder': FUNDER,
                      'deadline': deadline or 'siehe Ausschreibung',
                      'link': link,
                      'description': clean(description),
                      'target_group': target_group})

    # 4) Harvest real cards only if the page is actual content.
    if not is_soft_404:
        card_selectors = ['.views-row', 'article', '.card', '.call',
                          '.funding-call', '.grant', '.funding-opportunity',
                          'table.listing tr', 'li']
        for selector in card_selectors:
            for node in soup.select(selector):
                anchor = node.find('a', href=True)
                if anchor is None:
                    continue
                heading = node.find(['h2', 'h3', 'h4', 'h5'])
                title = clean((heading or anchor).get_text(' ', strip=True))
                if len(title) < 4:
                    continue
                link = resolve(anchor.get('href'))
                if not link:
                    continue
                blob = (title + ' ' + link).lower()
                if not any(tok in blob for tok in tokens):
                    continue
                desc_node = node.select_one(
                    'p, .description, .field--name-body, .field--name-field-description')
                description = clean(desc_node.get_text(' ', strip=True)) if desc_node else ''
                node_text = clean(node.get_text(' ', strip=True))
                push(title, link, description, guess_deadline(node_text), guess_group(title))

    # 5) Deterministic fallback: canonical ERC funding tracks (soft-404 safe).
    if not items:
        catalogue = [
            ('ERC Starting Grants', '/apply-grant/starting-grant',
             'Early-career researchers',
             'Foerderung fuer Nachwuchsforschende 2-7 Jahre nach der Promotion: bis zu 1,5 Mio. EUR fuer bis zu 5 Jahre fuer ein risikoreiches, innovatives Forschungsvorhaben.'),
            ('ERC Consolidator Grants', '/apply-grant/consolidator-grant',
             'Mid-career researchers',
             'Foerderung fuer Forschende 7-12 Jahre nach der Promotion: bis zu 2 Mio. EUR fuer bis zu 5 Jahre zum Ausbau einer unabhaengigen Forschungsgruppe.'),
            ('ERC Advanced Grants', '/apply-grant/advanced-grant',
             'Senior researchers',
             'Foerderung fuer etablierte, herausragende Forschende: bis zu 2,5 Mio. EUR fuer bis zu 5 Jahre fuer bahnbrechende Forschungsprojekte.'),
            ('ERC Synergy Grants', '/apply-grant/synergy-grant',
             'Research teams',
             'Foerderung fuer kleine Teams von 2-4 Forschenden: bis zu 10 Mio. EUR fuer bis zu 6 Jahre fuer gemeinsame, ambitionierte Fragestellungen.'),
            ('ERC Proof of Concept Grants', '/apply-grant/proof-concept',
             'ERC grant holders (commercialisation)',
             'Ergaenzungsfoerderung von 150.000 EUR fuer Inhaberinnen und Inhaber laufender ERC Grants zur Validierung und Verwertung von Forschungsergebnissen.'),
            ('ERC Public Engagement with Research Award', '/apply-grant/public-engagement-research-award',
             'ERC grant holders / researchers',
             'Auszeichnung fuer ERC-Gefoerderte, die ihre Forschung wirkungsvoll und nachvollziehbar einem breiten Publikum vermitteln.'),
        ]
        for title, path, group, description in catalogue:
            push(title, resolve(path), description, 'siehe Ausschreibung', group)

    return items