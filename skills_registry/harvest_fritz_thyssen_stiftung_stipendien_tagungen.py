def harvest_fritz_thyssen_stiftung_stipendien_tagungen(html, base_url):
    from bs4 import BeautifulSoup
    funder = 'Fritz Thyssen Stiftung - Stipendien & Tagungen'
    target_group = 'Hochschulen bzw. gemeinnützige Forschungseinrichtungen im In- und Ausland; Förderung i.d.R. nur für Vorhaben mit Bezug zum deutschen Wissenschaftssystem'
    specs = {
        'Projekte': {
            'title': 'Projekte',
            'deadline': '1. Februar und 1. September (i.d.R.)',
            'fallback_description': 'Zeitlich befristete Forschungsprojekte; beantragbar sind Personal-, Sach- und Reisemittel.'
        },
        'Tagungen': {
            'title': 'Tagungen',
            'deadline': '28. Februar, 31. Mai, 31. August oder 30. November',
            'fallback_description': 'Kleinere wissenschaftliche Tagungen; Entscheidung acht bis zehn Wochen nach Ablauf der Einreichungsfrist.'
        },
        'Reisebeihilfen': {
            'title': 'Reisebeihilfen',
            'deadline': 'jederzeit',
            'fallback_description': 'Reisebeihilfen; Kongressreisen werden nicht gefördert.'
        },
        'Druckbeihilfen': {
            'title': 'Druckbeihilfen',
            'deadline': 'jederzeit',
            'fallback_description': 'Druckbeihilfen nur für Publikationen, die aus bereits geförderten Vorhaben hervorgehen.'
        }
    }
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    for h5 in soup.find_all('h5'):
        title = ' '.join(h5.get_text(' ', strip=True).split())
        if title not in specs:
            continue
        spec = specs[title]
        ul = h5.find_next_sibling('ul')
        desc_parts = []
        if ul is not None:
            for li in ul.find_all('li'):
                text = ' '.join(li.get_text(' ', strip=True).split())
                if text:
                    desc_parts.append(text)
        description = ' '.join(desc_parts) if desc_parts else spec['fallback_description']
        items.append({
            'title': spec['title'],
            'funder': funder,
            'deadline': spec['deadline'],
            'link': base_url,
            'description': description,
            'target_group': target_group
        })
    return items