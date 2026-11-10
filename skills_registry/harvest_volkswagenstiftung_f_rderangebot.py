def harvest_volkswagenstiftung_f_rderangebot(html: str, base_url: str) -> list[dict]:
    # System-2 deterministic extractor for VolkswagenStiftung funding pages.
    # Handles the EMPTY_DOM_DRIFT case: the homepage is returned instead of the
    # funding list, so funding entry points are recovered from the landing page.
    from urllib.parse import urljoin
    from bs4 import BeautifulSoup

    FUNDER = 'VolkswagenStiftung - Förderangebot'
    DEFAULT_TARGET = 'Forschende (researchers)'
    DEADLINE_UNKNOWN = 'unknown'

    items = []
    seen = set()

    if not isinstance(html, str) or not html.strip():
        return items

    soup = BeautifulSoup(html, 'html.parser')
    root = soup.find('main') or soup

    def _clean(node_or_str):
        if node_or_str is None:
            return ''
        if isinstance(node_or_str, str):
            txt = node_or_str
        else:
            txt = node_or_str.get_text(' ', strip=True)
        return ' '.join(txt.split())

    def _add(title, href, description='', target_group=DEFAULT_TARGET, deadline=DEADLINE_UNKNOWN):
        t = _clean(title)
        if not t:
            return
        key = t.lower()
        if key in seen:
            return
        seen.add(key)
        link = urljoin(base_url, href.strip()) if href else base_url
        items.append({
            'title': t,
            'funder': FUNDER,
            'deadline': deadline,
            'link': link,
            'description': _clean(description),
            'target_group': target_group,
        })

    # 1) Stage CTA -> complete funding list (#foerderungen_liste)
    for a in root.select('.stage-detail__links a[href]'):
        href = a.get('href', '')
        if 'foerderung' in href.lower():
            _add(_clean(a) or 'Förderangebote ansehen', href,
                 'Übersicht aller aktuellen Förderangebote der VolkswagenStiftung.',
                 'Forschende aller Disziplinen')

    # 2) Profile-area cards (Profilbereiche) -> funding strands
    for card in root.select('article.profile-item, .profile-item'):
        a = card.select_one('a[href]')
        if a is None:
            continue
        _add(_clean(card.select_one('.profile-item__headline')) or _clean(a),
             a.get('href', ''),
             _clean(card.select_one('.profile-item__text')),
             'Forschende im jeweiligen Profilbereich')

    # 3) Fallback sweep: every remaining internal funding link
    for a in root.find_all('a', href=True):
        href = a['href'].strip()
        low = href.lower()
        if 'foerderung' not in low:
            continue
        if low.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
            continue
        _add(_clean(a) or _clean(a.parent), href, '', DEFAULT_TARGET)

    return items