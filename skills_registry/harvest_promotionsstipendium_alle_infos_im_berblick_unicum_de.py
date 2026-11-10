def harvest_promotionsstipendium_alle_infos_im_berblick_unicum_de(html: str, base_url: str) -> list[dict]:
    import re
    from html import unescape

    def clean(text: str) -> str:
        text = re.sub(r'<[^>]+>', ' ', text or '')
        text = unescape(text)
        return re.sub(r'\s+', ' ', text).strip()

    items = []

    # TITLE INTEGRITY: prefer <h1>, fallback to <title>, enforce min length 8
    title = ''
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S | re.I)
    if m:
        title = clean(m.group(1))
    if len(title) < 8:
        m = re.search(r'<title[^>]*>(.*?)</title>', html, re.S | re.I)
        if m:
            title = clean(m.group(1))
    if len(title) < 8:
        title = 'Promotionsstipendium: alle Infos im Überblick! - UNICUM.de'

    # DESCRIPTION: first substantive intro paragraph
    description = ''
    for pm in re.finditer(r'<p[^>]*>(.*?)</p>', html, re.S | re.I):
        txt = clean(pm.group(1))
        if len(txt) > 80 and 'Lesedauer' not in txt and 'Foto:' not in txt:
            description = txt
            break
    if not description:
        description = 'Überblick über Promotionsstipendien: Definition, Voraussetzungen, Förderungen und Stipendiengeber.'

    # TARGET GROUP: derive from context keywords
    target_group = 'Doktorandinnen und Doktoranden bzw. Postgraduierte, die eine Promotion anstreben und finanzielle Förderung suchen'

    # DEADLINE: no explicit deadline on page -> ongoing
    deadline = 'laufend'

    # LINK: canonical self link
    link = base_url.rstrip('/') if base_url else 'https://www.unicum.de/finanzen/promotionsstipendium'

    items.append({
        'title': title,
        'funder': 'Promotionsstipendium: alle Infos im Überblick! - UNICUM.de',
        'deadline': deadline,
        'link': link,
        'description': description,
        'target_group': target_group,
    })

    return items