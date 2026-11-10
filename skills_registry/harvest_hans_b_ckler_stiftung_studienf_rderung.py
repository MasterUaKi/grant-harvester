def harvest_hans_b_ckler_stiftung_studienf_rderung(html: str, base_url: str) -> list[dict]:
    import re
    from urllib.parse import urljoin
    from bs4 import BeautifulSoup

    FUNDER = 'Hans-Böckler-Stiftung - Studienförderung'
    items: list[dict] = []
    if not html:
        return items

    soup = BeautifulSoup(html, 'html.parser')
    body_text = soup.get_text(' ', strip=True)

    # Guard: harvested document is the site's 404 template -> nothing to extract.
    if re.search(r'404\s*-\s*Seite nicht gefunden', body_text, re.I):
        return items

    grant_re = re.compile(r'stipend\w*|f(?:oe|ö)rder\w*|promotion\w*|studienf(?:oe|ö)rderung', re.I)
    deadline_re = re.compile(r'(?:Bewerbungsschluss|Bewerbungsfrist|Frist|Deadline|Bewerbung bis)\s*:?\s*([^.;]{3,60})', re.I)
    targets = (
        (re.compile(r'promov|doktor', re.I), 'Promovierende / Doktorand:innen'),
        (re.compile(r'postdoc|habilit', re.I), 'Postdocs / Habilitierende'),
        (re.compile(r'studierend|studium|bachelor|master', re.I), 'Studierende'),
    )
    skip_prefixes = ('#', 'mailto:', 'javascript:', 'tel:', 'data:')

    seen = set()
    for anchor in soup.find_all('a', href=True):
        label = anchor.get_text(' ', strip=True)
        href = anchor['href'].strip()
        if not label or href.lower().startswith(skip_prefixes):
            continue
        link = urljoin(base_url, href)
        if link in seen:
            continue
        if not (grant_re.search(label) or grant_re.search(link)):
            continue
        container = anchor.find_parent(['article', 'li', 'section', 'div']) or anchor
        context = re.sub(r'\s+', ' ', container.get_text(' ', strip=True))
        deadline = deadline_re.search(context)
        target_group = 'Studierende'
        for pattern, name in targets:
            if pattern.search(context):
                target_group = name
                break
        seen.add(link)
        items.append({
            'title': label,
            'funder': FUNDER,
            'deadline': deadline.group(1).strip() if deadline else 'siehe Seite',
            'link': link,
            'description': context[:300],
            'target_group': target_group,
        })
    return items