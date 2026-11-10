def harvest_promotionsstipendium_stipendiengeber_im_berblick(html, base_url):
    import re
    from html import unescape

    def clean(text):
        text = re.sub(r'<[^>]+>', ' ', text or '')
        text = unescape(text)
        return re.sub(r'\s+', ' ', text).strip()

    items = []
    title = 'Promotionsstipendium: Stipendiengeber im Überblick'
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S | re.I)
    if m:
        candidate = clean(m.group(1))
        if len(candidate) >= 8:
            title = candidate

    description = ''
    m = re.search(r'<div class="artikel-bewerbung-summary">(.*?)</div>', html, re.S | re.I)
    if m:
        description = clean(m.group(1))
    if not description:
        m = re.search(r'<div class="field-name-body[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.S | re.I)
        if m:
            description = clean(m.group(1))[:1500]

    target_group = 'Promovierende aller Fachrichtungen sowie Promovierende spezifischer Fächer'
    if 'Humanmedizin' in html or 'Psychologie' in html:
        target_group = 'Promovierende aller Fachrichtungen sowie Promovierende spezifischer Fächer (u. a. Chemie, Psychologie, Humanmedizin, Geisteswissenschaften, Rechtswissenschaften)'

    link = base_url.rstrip('/')
    if '/stipendien/promotionsstipendium' not in link:
        link = link + '/stipendien/promotionsstipendium'

    items.append({
        'title': title,
        'funder': 'Promotionsstipendium: Stipendiengeber im Überblick',
        'deadline': 'laufend',
        'link': link,
        'description': description,
        'target_group': target_group,
    })
    return items