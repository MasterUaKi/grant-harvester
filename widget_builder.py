# File: widget_builder.py
# Version: 2.1.0 | Release Date: 2026-11-10
from datetime import datetime
import html
import json
from pathlib import Path
from typing import List
from schemas import GrantItem, MultiSourceHarvestResult


def render_all_grants_catalog(harvest_result: MultiSourceHarvestResult, output_file: Path | str) -> None:
    """
    Генерирует автономную интерактивную веб-витрину каталога грантов.
    Интерфейс выполнен на двух языках (English / Deutsch).
    Кнопки фильтрации строятся динамически по реально собранным источникам и фондам.
    """
    out_path = Path(output_file).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    grants: List[GrantItem] = harvest_result.grants

    # Извлечение уникальных найденных фондов и источников для динамических кнопок
    funders_counter = {}
    for g in grants:
        funder_name = g.funder.strip() if g.funder else "Other / Sonstige"
        funders_counter[funder_name] = funders_counter.get(funder_name, 0) + 1

    # Сортировка кнопок по количеству найденных программ
    sorted_funders = sorted(funders_counter.items(), key=lambda x: x[1], reverse=True)

    # Формирование карточек
    cards_html = []
    for g in grants:
        safe_title = html.escape(g.title or "Untitled / Ohne Titel")
        safe_funder = html.escape(g.funder or "Unknown Funder / Unbekannter Förderer")
        safe_desc = html.escape(g.description or "No description provided / Keine Beschreibung verfügbar")
        safe_target = html.escape(g.target_group or "Researchers / Wissenschaftler")
        safe_deadline = html.escape(g.deadline or "ongoing / laufend")
        safe_source = html.escape(g.source_portal or safe_funder)
        safe_link = html.escape(g.link)

        # Вычисление бейджа дедлайна
        deadline_lower = safe_deadline.lower()
        if "laufend" in deadline_lower or "ongoing" in deadline_lower or "siehe" in deadline_lower:
            deadline_class = "deadline-ongoing"
        else:
            deadline_class = "deadline-fixed"

        new_tag_html = (
            '<span class="badge badge-new">New / Neu</span>'
            if g.is_newly_discovered
            else '<span class="badge badge-verified">Verified / Verifiziert</span>'
        )

        amount_html = ""
        if g.funding_amount:
            amount_html = f'<div class="meta-item"><strong>Funding / Förderhöhe:</strong> {html.escape(g.funding_amount)}</div>'

        card = f"""
        <article class="grant-card" data-funder="{safe_funder}" data-source="{safe_source}">
            <div class="card-header">
                <div class="funder-badges">
                    <span class="funder-name">{safe_funder}</span>
                    {new_tag_html}
                </div>
                <div class="deadline-badge {deadline_class}">
                    <span>Deadline / Frist:</span> <strong>{safe_deadline}</strong>
                </div>
            </div>
            
            <h3 class="card-title">
                <a href="{safe_link}" target="_blank" rel="noopener noreferrer">{safe_title}</a>
            </h3>
            
            <div class="card-meta">
                <div class="meta-item"><strong>Target Group / Zielgruppe:</strong> {safe_target}</div>
                <div class="meta-item"><strong>Source / Quelle:</strong> {safe_source}</div>
                {amount_html}
            </div>

            <p class="card-description">{safe_desc}</p>
            
            <div class="card-footer">
                <a class="action-btn" href="{safe_link}" target="_blank" rel="noopener noreferrer">
                    Open Call &rarr; / Ausschreibung &ouml;ffnen &rarr;
                </a>
            </div>
        </article>
        """
        cards_html.append(card)

    rendered_cards = "\n".join(cards_html)

    # Генерация динамических кнопок
    filter_buttons_html = [
        f'<button class="filter-btn active" data-filter="ALL">All Sources / Alle Quellen ({len(grants)})</button>'
    ]
    for funder, count in sorted_funders:
        safe_funder_name = html.escape(funder)
        filter_buttons_html.append(
            f'<button class="filter-btn" data-filter="{safe_funder_name}">{safe_funder_name} ({count})</button>'
        )
    rendered_buttons = "\n".join(filter_buttons_html)

    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Research Funding & Grants / Forschungsf&ouml;rderung & Stipendien</title>
    <style>
        :root {{
            --primary: #0052cc;
            --primary-hover: #0747a6;
            --bg: #f4f5f7;
            --surface: #ffffff;
            --text-main: #172b4d;
            --text-muted: #5e6c84;
            --border: #dfe1e6;
            --badge-green: #e3fcef;
            --badge-green-text: #006644;
            --badge-blue: #deebff;
            --badge-blue-text: #0747a6;
            --deadline-bg: #fff0b3;
            --deadline-text: #172b4d;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            padding: 24px;
            line-height: 1.5;
        }}
        .header {{
            max-width: 1400px;
            margin: 0 auto 24px auto;
            background: var(--surface);
            padding: 24px;
            border-radius: 8px;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .header h1 {{
            font-size: 26px;
            margin-bottom: 8px;
            color: var(--primary);
        }}
        .header-meta {{
            font-size: 14px;
            color: var(--text-muted);
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        .search-container {{
            margin-top: 16px;
        }}
        .search-input {{
            width: 100%;
            padding: 12px 16px;
            font-size: 15px;
            border: 2px solid var(--border);
            border-radius: 6px;
            outline: none;
            transition: border-color 0.2s;
        }}
        .search-input:focus {{
            border-color: var(--primary);
        }}
        .filters-container {{
            max-width: 1400px;
            margin: 0 auto 20px auto;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .filter-btn {{
            background: var(--surface);
            border: 1px solid var(--border);
            padding: 8px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 500;
            color: var(--text-main);
            cursor: pointer;
            transition: all 0.2s;
        }}
        .filter-btn:hover {{
            background: #ebecf0;
        }}
        .filter-btn.active {{
            background: var(--primary);
            color: #ffffff;
            border-color: var(--primary);
        }}
        .grid-container {{
            max-width: 1400px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
            gap: 20px;
        }}
        .grant-card {{
            background: var(--surface);
            border-radius: 8px;
            border: 1px solid var(--border);
            padding: 20px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.15s, box-shadow 0.15s;
        }}
        .grant-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
            margin-bottom: 12px;
        }}
        .funder-name {{
            font-weight: 700;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--primary);
        }}
        .badge {{
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 12px;
            font-weight: 600;
            margin-left: 6px;
        }}
        .badge-new {{ background: var(--badge-green); color: var(--badge-green-text); }}
        .badge-verified {{ background: var(--badge-blue); color: var(--badge-blue-text); }}
        .deadline-badge {{
            font-size: 12px;
            padding: 4px 10px;
            border-radius: 4px;
            white-space: nowrap;
        }}
        .deadline-fixed {{ background: var(--deadline-bg); color: var(--deadline-text); }}
        .deadline-ongoing {{ background: #ebecf0; color: var(--text-muted); }}
        .card-title {{
            font-size: 17px;
            margin-bottom: 12px;
            line-height: 1.4;
        }}
        .card-title a {{
            color: var(--text-main);
            text-decoration: none;
        }}
        .card-title a:hover {{
            color: var(--primary);
            text-decoration: underline;
        }}
        .card-meta {{
            font-size: 13px;
            margin-bottom: 12px;
            color: var(--text-muted);
            border-left: 3px solid var(--border);
            padding-left: 10px;
        }}
        .card-meta strong {{
            color: var(--text-main);
        }}
        .card-description {{
            font-size: 14px;
            color: var(--text-main);
            margin-bottom: 16px;
            flex-grow: 1;
            display: -webkit-box;
            -webkit-line-clamp: 4;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        .card-footer {{
            border-top: 1px solid var(--border);
            padding-top: 14px;
            display: flex;
            justify-content: flex-end;
        }}
        .action-btn {{
            background: var(--primary);
            color: #ffffff;
            padding: 8px 16px;
            border-radius: 4px;
            text-decoration: none;
            font-size: 13px;
            font-weight: 600;
            transition: background 0.2s;
        }}
        .action-btn:hover {{
            background: var(--primary-hover);
        }}
    </style>
</head>
<body>

    <header class="header">
        <h1>Research Funding &amp; Grants / Forschungsf&ouml;rderung &amp; Stipendien</h1>
        <div class="header-meta">
            <span><strong>Updated / Zuletzt aktualisiert:</strong> {now_str}</span>
            <span><strong>Active Programs / Aktive Programme:</strong> <span id="visible-count">{len(grants)}</span> / {len(grants)}</span>
            <span><strong>Active Sources / Aktive Quellen:</strong> {len(sorted_funders)}</span>
        </div>
        <div class="search-container">
            <input type="text" id="searchInput" class="search-input" placeholder="Search by title, keywords, disciplines, or funder... / Suche nach Titel, F&auml;chern, Stichw&ouml;rtern oder F&ouml;rderern...">
        </div>
    </header>

    <nav class="filters-container" id="filtersGroup">
        {rendered_buttons}
    </nav>

    <main class="grid-container" id="grantsGrid">
        {rendered_cards}
    </main>

    <script>
        const searchInput = document.getElementById('searchInput');
        const cards = Array.from(document.querySelectorAll('.grant-card'));
        const filterBtns = Array.from(document.querySelectorAll('.filter-btn'));
        const visibleCountEl = document.getElementById('visible-count');
        let activeFunder = 'ALL';

        function filterCards() {{
            const query = searchInput.value.toLowerCase().trim();
            let visibleCount = 0;

            cards.forEach(card => {{
                const cardFunder = card.getAttribute('data-funder');
                const cardText = card.innerText.toLowerCase();

                const matchesFunder = (activeFunder === 'ALL' || cardFunder === activeFunder);
                const matchesQuery = query === '' || cardText.includes(query);

                if (matchesFunder && matchesQuery) {{
                    card.style.display = 'flex';
                    visibleCount++;
                }} else {{
                    card.style.display = 'none';
                }}
            }});

            if (visibleCountEl) visibleCountEl.textContent = visibleCount;
        }}

        filterBtns.forEach(btn => {{
            btn.addEventListener('click', () => {{
                filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                activeFunder = btn.getAttribute('data-filter');
                filterCards();
            }});
        }});

        searchInput.addEventListener('input', filterCards);
    </script>
</body>
</html>
"""
    out_path.write_text(full_html, encoding="utf-8")