def harvest_cusanuswerk_bisch_fliche_studienf_rderung(html: str, base_url: str) -> list[dict]:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    seen = set()
    funder = 'Cusanuswerk – Bischöfliche Studienförderung'

    def add_item(title, link, description, deadline='', target_group=''):
        if not title:
            return
        key = (title, link)
        if key in seen:
            return
        seen.add(key)
        items.append({
            'title': title,
            'funder': funder,
            'deadline': deadline,
            'link': link,
            'description': description,
            'target_group': target_group,
        })

    for box in soup.select('div.frame-greybox'):
        h3 = box.select_one('.ce-bodytext h3')
        if h3 is None:
            continue
        title = h3.get_text(' ', strip=True)
        lower_title = title.lower()
        if 'förder' not in lower_title and 'auszubildende' not in lower_title:
            continue
        a = h3.find('a', href=True)
        if a is None:
            a = h3.find_parent('a', href=True)
        link = urljoin(base_url, a['href']) if a and a.has_attr('href') else ''
        desc_parts = []
        for p in box.select('.ce-bodytext p'):
            txt = p.get_text(' ', strip=True)
            if txt and not txt.startswith('»'):
                desc_parts.append(txt)
        description = ' '.join(desc_parts)
        deadline = ''
        target_group = 'Stipendiatinnen und Stipendiaten'
        if 'auszubildende' in lower_title:
            target_group = 'Auszubildende'
            if 'vom ' in description:
                deadline = description.split('vom ', 1)[1]
                deadline = deadline.split(' möglich', 1)[0]
                deadline = deadline.replace('bis zum', 'bis').strip()
        add_item(title, link, description, deadline, target_group)

    for article in soup.select('div.singleNews'):
        h3 = article.select_one('h3')
        if h3 is None:
            continue
        title = h3.get_text(' ', strip=True)
        lower_title = title.lower()
        if 'förderpreis' not in lower_title:
            continue
        if 'preisträgerkonzert' in lower_title:
            continue
        a = h3.find('a', href=True)
        if a is None:
            a = h3.find_parent('a', href=True)
        link = urljoin(base_url, a['href']) if a and a.has_attr('href') else ''
        gump = article.select_one('.gump')
        description = gump.get_text(' ', strip=True) if gump else title
        target_group = ''
        if 'musik' in lower_title or 'musiker' in lower_title:
            target_group = 'Musikerinnen und Musiker'
        add_item(title, link, description, '', target_group)

    return items