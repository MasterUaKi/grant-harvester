def harvest_promotionsstipendium_f_rderwerke_h_he_bewerbung(html: str, base_url: str) -> list[dict]:
    import re
    from html import unescape

    FUNDER = 'Promotionsstipendium: Förderwerke, Höhe & Bewerbung'
    items = []

    def clean(text: str) -> str:
        text = re.sub(r'<[^>]+>', ' ', text or '')
        text = unescape(text)
        return re.sub(r'\s+', ' ', text).strip()

    def add(title, link, description, target_group='Promovierende'):
        title = clean(title)
        if len(title) < 8:
            return
        if link and link.startswith('/'):
            link = base_url.rstrip('/') + link
        items.append({
            'title': title,
            'funder': FUNDER,
            'deadline': 'laufend',
            'link': link or base_url,
            'description': clean(description),
            'target_group': target_group,
        })

    # 1) Begabtenförderungswerke table rows
    for row in re.findall(r'<tr>(.*?)</tr>', html, flags=re.S | re.I):
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, flags=re.S | re.I)
        if len(cells) < 4:
            continue
        name_cell, ausrichtung, termine, besonderheit = cells[:4]
        m = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', name_cell, flags=re.S | re.I)
        if not m:
            continue
        link, name = m.group(1), m.group(2)
        desc = 'Ausrichtung: %s. Bewerbungstermine: %s. %s' % (
            clean(ausrichtung), clean(termine), clean(besonderheit))
        add(name, link, desc)

    # 2) Fachbezogene Stiftungen / DAAD / Landesförderung from list items
    for li in re.findall(r'<li>(.*?)</li>', html, flags=re.S | re.I):
        m = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', li, flags=re.S | re.I)
        if not m:
            continue
        link, name = m.group(1), m.group(2)
        desc = clean(li)
        if len(desc) < 20:
            continue
        add(name, link, desc)

    # 3) DAAD program listing (explicit)
    daad = re.search(
        r'<a[^>]+href="(https://www2\.daad\.de/[^"]+)"[^>]*>(.*?)</a>',
        html, flags=re.S | re.I)
    if daad:
        add('DAAD – Promotionsstipendium für ausländische Doktoranden in Deutschland',
            daad.group(1),
            'Monatliche Rate von 1.400 € sowie Versicherungsleistungen und jährliche Forschungsbeihilfe.',
            'Ausländische Promovierende in Deutschland')

    # 4) Landesgraduiertenförderung links
    for m in re.finditer(
        r'<a[^>]+href="([^"]+)"[^>]*>(Landesstipendienverordnung|Graduiertenförderungsverordnung)</a>',
        html, flags=re.S | re.I):
        add('Landesgraduiertenförderung – ' + clean(m.group(2)), m.group(1),
            'Landesstipendium; Bewerbung über die Hochschule.', 'Promovierende')

    # Deduplicate by link+title
    seen = set()
    unique = []
    for it in items:
        key = (it['title'], it['link'])
        if key in seen:
            continue
        seen.add(key)
        unique.append(it)

    return unique