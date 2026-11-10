def harvest_finanzielle_fo_rderung_stipendien_unterst_tzung_bayerisches(html, base_url):
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    FUNDER = 'Finanzielle Förderung /Stipendien| Unterstützung | Bayerisches ...'
    soup = BeautifulSoup(html, 'html.parser')
    items = []

    for acc in soup.select('div.rxModuleAccordion'):
        btn = acc.find('button', class_='rxModuleAccordionButton')
        if not btn:
            continue
        title = btn.get_text(' ', strip=True)
        content = acc.find('div', class_='rxModuleAccordionContent')
        if not content:
            continue

        # Description: concatenate paragraphs from the text module
        text_mod = content.find('div', class_='rxModuleTextImage')
        paragraphs = []
        if text_mod:
            for p in text_mod.find_all('p'):
                t = p.get_text(' ', strip=True)
                if t:
                    paragraphs.append(t)
        description = ' '.join(paragraphs)

        # Link: first external link in the link module, else first link
        link = ''
        link_mod = content.find('div', class_='rxModuleLink')
        anchor = None
        if link_mod:
            anchor = link_mod.find('a', href=True)
        if anchor is None:
            anchor = content.find('a', href=True)
        if anchor and anchor.get('href'):
            link = urljoin(base_url, anchor['href'])

        # Target group: try to extract from a paragraph following 'Zielgruppe'
        target_group = ''
        if text_mod:
            ps = text_mod.find_all('p')
            for i, p in enumerate(ps):
                strong = p.find('strong')
                if strong and 'zielgruppe' in strong.get_text(strip=True).lower():
                    if i + 1 < len(ps):
                        target_group = ps[i + 1].get_text(' ', strip=True)
                    break

        items.append({
            'title': title,
            'funder': FUNDER,
            'deadline': 'laufend',
            'link': link,
            'description': description,
            'target_group': target_group,
        })

    return items