def harvest_promotionsstipendium_bmftr(html, base_url):
    import re, json

    def _clean(s):
        if not s:
            return ''
        s = re.sub(r'<[^>]+>', ' ', s)
        s = re.sub(r'\s+', ' ', s)
        return s.strip()

    items = []

    # --- TITLE (Integritätsregel: >= 8 Zeichen, kein Einzelzeichen) ---
    title = ''
    m = re.search(r'<h1[^>]*class="[^"]*l-intro__headline[^"]*"[^>]*>(.*?)</h1>', html, re.S | re.I)
    if m:
        title = _clean(m.group(1))
    if len(title) < 8:
        m = re.search(r'<title[^>]*>(.*?)</title>', html, re.S | re.I)
        if m:
            title = _clean(m.group(1)).split('|')[0].strip()
    if len(title) < 8:
        title = 'Promotionsstipendium'

    # --- DEADLINE ---
    # Kein explizites Datum im DOM -> laufende Bewerbung
    deadline = 'laufend'
    m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', html)
    if m:
        deadline = '{:02d}.{:02d}.{}'.format(int(m.group(1)), int(m.group(2)), m.group(3))

    # --- LINK (erster externer stipendiumplus-Link) ---
    link = base_url
    m = re.search(r'href="(https?://[^"]*stipendiumplus\.de[^"]*)"', html, re.I)
    if m:
        link = m.group(1)

    # --- DESCRIPTION (aus Intro + Finanzierungs-Abschnitt) ---
    desc_parts = []
    m = re.search(r'<p class="c-topline[^"]*"[^>]*>(.*?)</p>', html, re.S | re.I)
    intro = ''
    m2 = re.search(r'<div class="l-intro__text">(.*?)</div>', html, re.S | re.I)
    if m2:
        ps = re.findall(r'<p[^>]*>(.*?)</p>', m2.group(1), re.S | re.I)
        for p in ps:
            t = _clean(p)
            if len(t) > 40:
                intro = t
                break
    if intro:
        desc_parts.append(intro)

    m = re.search(r'<h2[^>]*>\s*Welche Finanzierung bieten die Promotionsstipendien[^<]*</h2>\s*<p[^>]*>(.*?)</p>', html, re.S | re.I)
    if m:
        desc_parts.append(_clean(m.group(1)))

    m = re.search(r'<h2[^>]*>\s*Wie lange kann ich gef\xc3\xb6rdert werden\?[^<]*</h2>\s*<p[^>]*>(.*?)</p>', html, re.S | re.I)
    if m:
        desc_parts.append(_clean(m.group(1)))

    description = ' '.join(desc_parts).strip()
    if not description:
        description = 'Promotionsstipendien der 13 Begabtenf\xc3\xb6rderungswerke des BMFTR.'

    # --- TARGET GROUP ---
    target_group = ''
    m = re.search(r'Bei der Bewerbung um ein Promotionsstipendium kommt es zudem darauf an, dass(.*?)</ul>', html, re.S | re.I)
    if m:
        target_group = 'Promovierende mit besonderer Bef\xc3\xa4higung zu wissenschaftlicher Arbeit, z\xc3\xbcgig durchgef\xc3\xbchrtem Studium, wissenschaftlich bedeutsamem Vorhaben und gesellschaftlichem Engagement.'
    if not target_group:
        target_group = 'Promovierende und Nachwuchswissenschaftlerinnen und Nachwuchswissenschaftler'

    items.append({
        'title': title,
        'funder': 'Promotionsstipendium - BMFTR',
        'deadline': deadline,
        'link': link,
        'description': description,
        'target_group': target_group,
    })

    return items