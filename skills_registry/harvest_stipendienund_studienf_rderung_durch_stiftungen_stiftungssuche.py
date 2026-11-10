def harvest_stipendienund_studienf_rderung_durch_stiftungen_stiftungssuche(html: str, base_url: str) -> list[dict]:
    from urllib.parse import urljoin
    from bs4 import BeautifulSoup

    FUNDER = 'Stipendienund Studienförderung durch Stiftungen - Stiftungssuche'
    DEFAULT_TARGET = 'Studierende und Promovierende'
    DEFAULT_DEADLINE = 'laufend / siehe Website'

    soup = BeautifulSoup(html or '', 'html.parser')
    root = (soup.select_one('#main .entry-content')
            or soup.select_one('.entry-content')
            or soup.select_one('main')
            or soup)

    items = []
    seen = set()

    for p in root.find_all('p'):
        a = p.find('a')
        if a is None:
            continue
        href = (a.get('href') or '').strip()
        if not href or href.startswith('#') or href.lower().startswith('javascript:'):
            continue
        title = a.get_text(' ', strip=True)
        if not title:
            continue
        link = urljoin(base_url, href)

        # tab panel context (bundesweit / universitaetsbezogen / Linksammlung)
        panel = p.find_parent(class_='vc_tta-panel')
        panel_title = ''
        if panel is not None:
            head = panel.select_one('.vc_tta-panel-title')
            if head is not None:
                panel_title = head.get_text(' ', strip=True)

        # sub-section heading (Parteinahe Stiftungen, zur Uni gehoerig, ...)
        separator = p.find_previous('div', class_='vc_separator')
        if separator is not None and separator.find_parent(class_='vc_tta-panel') is not panel:
            separator = None
        subgroup = separator.get_text(' ', strip=True) if separator is not None else ''

        text = p.get_text(' ', strip=True)
        rest = text[len(title):] if text.startswith(title) else text.replace(title, '', 1)
        rest = rest.strip()
        if rest.endswith('()'):
            rest = rest[:-2].strip()
        rest = rest.lstrip(':–—- ').strip()

        # trailing parenthetical -> target group hint
        paren = ''
        if rest.endswith(')') and '(' in rest:
            idx = rest.rfind('(')
            inner = rest[idx + 1:-1]
            if '(' not in inner and ')' not in inner:
                paren = inner.strip()
                rest = rest[:idx].strip().lstrip(':–—- ').strip()

        target_group = DEFAULT_TARGET
        if paren and 'nah' not in paren.lower():
            target_group = paren

        parts = []
        if subgroup:
            parts.append(subgroup)
        if rest:
            parts.append(rest)
        if paren and 'nah' in paren.lower():
            parts.append('(' + paren + ')')
        if panel_title == 'Linksammlung':
            parts.append('Datenbank/Rechercheportal')

        key = (title.lower(), link)
        if key in seen:
            continue
        seen.add(key)

        items.append({
            'title': title,
            'funder': FUNDER,
            'deadline': DEFAULT_DEADLINE,
            'link': link,
            'description': '; '.join(parts),
            'target_group': target_group,
        })

    return items