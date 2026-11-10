def harvest_auto_kopen_via_een_online_handelsplaats_pas_op_voor_frauduleuze(html: str, base_url: str) -> list:
    # Deterministic harvester for the AVROTROS Opgelicht?! help-article template.
    # The live DOM of this page contains a full consumer-fraud article and zero
    # grant programmes, so the keyword gate below must resolve to [].
    from urllib.parse import urljoin
    from bs4 import BeautifulSoup

    GRANT_KEYWORDS = (
        'grant', 'subsidy', 'subsidie', 'funding', 'fellowship', 'scholarship',
        'stipend', 'call for proposals', 'call for papers', 'open call', 'beurs',
        'förderung', 'forderung', 'award', 'prize', 'financiering', 'tender',
        'aanbesteding', 'onderzoeksprogramma', 'research programme', 'apply now',
        'deadline', 'solliciteer', 'aanvraagformulier',
    )
    NEGATIVE_KEYWORDS = (
        'oplichting', 'opgelicht', 'phishing', 'fraude', 'frauduleus', 'spoofing',
        'slachtoffer', 'aangifte', 'waarschuwing', 'nieuwsbrief', 'newsletter',
        'download de app', 'cookie', 'privacy', 'artikel delen', 'lees ook',
    )
    MONTHS = {
        'jan': 1, 'feb': 2, 'mrt': 3, 'mar': 3, 'apr': 4, 'mei': 5, 'may': 5,
        'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'oct': 10,
        'nov': 11, 'dec': 12,
    }
    DEFAULT_FUNDER = 'Auto kopen via een online handelsplaats? Pas op voor frauduleuze ...'

    def _clean(value, limit=400):
        if not value:
            return ''
        text = ' '.join(str(value).split())
        return text[:limit].rstrip()

    def _find_deadline(*texts):
        # Deterministic NL/EN month-year scanner; no regex, no locale deps.
        for text in texts:
            tokens = _clean(text, 2000).replace(',', ' ').replace(';', ' ').split()
            for index, token in enumerate(tokens):
                key = token.lower().strip('.:()[]')
                if 3 <= len(key) <= 4 and key[:3] in MONTHS:
                    for follower in tokens[index + 1:index + 3]:
                        digits = follower.strip('.:(),[]')
                        if digits.isdigit() and len(digits) == 4:
                            return '%02d/%s' % (MONTHS[key[:3]], digits)
        return ''

    if not html or not html.strip():
        return []

    soup = BeautifulSoup(html, 'html.parser')

    heading = soup.find('h1')
    page_title = _clean(heading.get_text(' ', strip=True), 300) if heading else ''
    funder = page_title or DEFAULT_FUNDER

    results = []
    seen = set()

    for anchor in soup.find_all('a', href=True):
        raw_href = (anchor.get('href') or '').strip()
        if not raw_href or raw_href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
            continue

        aria_label = _clean(anchor.get('aria-label') or '', 300)
        label = _clean(anchor.get_text(' ', strip=True), 300) or aria_label
        if len(label) < 8:
            continue

        haystack = (label + ' ' + aria_label).lower()
        if not any(keyword in haystack for keyword in GRANT_KEYWORDS):
            continue
        if any(negative in haystack for negative in NEGATIVE_KEYWORDS):
            continue

        link = urljoin(base_url, raw_href)
        if not link.startswith(('http://', 'https://')):
            continue

        dedupe_key = (label.lower(), link.split('#')[0])
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        container = anchor
        for _ in range(4):
            parent = container.parent
            if parent is None or getattr(parent, 'name', None) in (None, 'body', 'html'):
                break
            container = parent

        container_text = _clean(container.get_text(' ', strip=True), 2000)
        description = ''
        for node in container.find_all(['p', 'span', 'div'], limit=40):
            text = _clean(node.get_text(' ', strip=True), 400)
            if len(text) >= 40 and text.lower() != label.lower() and text[:60] != container_text[:60]:
                description = text
                break

        results.append({
            'title': label,
            'funder': funder,
            'deadline': _find_deadline(description, container_text, page_title),
            'link': link,
            'description': description or page_title,
            'target_group': 'Not specified',
        })

    return results