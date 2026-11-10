def harvest_konrad_adenauer_stiftung(html: str, base_url: str) -> list:
    import re
    from urllib.parse import urljoin
    from bs4 import BeautifulSoup

    items = []
    if not html:
        return items

    soup = BeautifulSoup(html, 'html.parser')
    page_text = soup.get_text(' ', strip=True).lower()

    # Hard stop: WAF / bot-challenge interstitials carry zero grant data.
    for marker in ('ihre anfrage wurde aus sicherheitsgründen blockiert',
                   'fehler-id', 'access denied', 'request blocked',
                   'cf-error-details', 'captcha'):
        if marker in page_text:
            return items

    FUNDER = 'Konrad-Adenauer-Stiftung'

    deadline_re = re.compile(
        r'(?:bewerbungsschluss|bewerbungsfrist|antragsfrist|frist|deadline)'
        r'\s*[:\-–]?\s*'
        r'(\d{1,2}\.\d{1,2}\.\d{2,4}|\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})',
        re.IGNORECASE)
    bare_date_re = re.compile(r'\b\d{1,2}\.\d{1,2}\.\d{4}\b')

    target_map = (
        ('promov', 'Promovierende / Doktorand:innen'),
        ('doktor', 'Promovierende / Doktorand:innen'),
        ('postdoc', 'Postdoktorand:innen / Habilitand:innen'),
        ('habilit', 'Postdoktorand:innen / Habilitand:innen'),
        ('studier', 'Studierende'),
        ('master', 'Studierende (Master)'),
        ('bachelor', 'Studierende (Bachelor)'),
        ('ausländ', 'Internationale Bewerber:innen'),
        ('international', 'Internationale Bewerber:innen'),
        ('journalis', 'Journalist:innen'),
        ('graduiert', 'Graduierte / Nachwuchswissenschaftler:innen'),
    )

    containers = soup.select('article, li.c-teaser, div.c-teaser, div.teaser, '
                             'div[class*=teaser], div[class*=card], li[class*=teaser]')
    if not containers:
        containers = [soup]

    seen = set()
    for node in containers:
        heading = node.find(['h1', 'h2', 'h3', 'h4'])
        if heading is None:
            continue
        title = heading.get_text(' ', strip=True)
        if len(title) < 4:
            continue

        anchor = heading.find('a', href=True) or node.find('a', href=True)
        link = urljoin(base_url, anchor['href']) if anchor else base_url

        key = (title.lower(), link)
        if key in seen:
            continue
        seen.add(key)

        block = node.get_text(' ', strip=True)
        para = node.find('p')
        description = para.get_text(' ', strip=True) if para else block[:280]

        match = deadline_re.search(block) or bare_date_re.search(block)
        deadline = match.group(match.lastindex or 0) if match else 'not specified'

        lowered = block.lower()
        target_group = 'not specified'
        for needle, label in target_map:
            if needle in lowered:
                target_group = label
                break

        items.append({
            'title': title,
            'funder': FUNDER,
            'deadline': deadline,
            'link': link,
            'description': description,
            'target_group': target_group,
        })

    return items