def harvest_das_bundesministerium_f_r_bildung_und_forschung_in_berlin(html: str, base_url: str) -> list[dict]:
    """Harvest grant/funding offers for the BMBF profile page.

    Deterministic, side-effect free. Returns [] when the page is a pure
    institutional profile (EMPTY_DOM_DRIFT) instead of raising, so the
    caller can escalate to a known-good funding gateway.
    """
    from urllib.parse import urljoin
    from bs4 import BeautifulSoup

    FUNDER = "Das Bundesministerium für Bildung und Forschung in Berlin"
    KEYWORDS = (
        "ausschreibung", "bekanntmachung", "foerder", "förder",
        "stipendium", "fellowship", "call", "wettbewerb", "preis",
    )
    # Structural noise on bundesregierung.de that never carries programme data.
    NOISE_SELECTORS = (
        "nav", "header", "footer", "script", "style",
        ".bpa-flyout-topics", ".bpa-breadcrumb", ".bpa-search",
        "#bpa-searchapp-react-root", "#bpa-searchapp-react-json",
        ".bpa-lightboxes", ".bpa-image-caption-mediacenter",
        ".bpa-images-mediacenter", "#matomo.tracking",
    )
    TEASER_SELECTORS = (
        ".bpa-teaser", ".bpa-teaser-text", ".bpa-module-teaser",
        ".bpa-list-item", ".bpa-link-list-item", "article",
    )

    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    for selector in NOISE_SELECTORS:
        for node in soup.select(selector):
            node.decompose()

    scope = soup.select_one("main") or soup.body or soup

    items = []
    seen_links = set()

    for teaser in scope.select(", ".join(TEASER_SELECTORS)):
        link_node = teaser.select_one("a[href]")
        if link_node is None:
            continue

        href = urljoin(base_url, (link_node.get("href") or "").strip())
        if not href or href in seen_links:
            continue

        title_node = teaser.select_one(
            ".bpa-teaser-title-text-inner, .bpa-teaser-title-text, h2, h3, h4"
        ) or link_node
        title = " ".join(title_node.get_text(" ", strip=True).split())
        if not title:
            continue

        haystack = (title + " " + teaser.get_text(" ", strip=True)).lower()
        if not any(keyword in haystack for keyword in KEYWORDS):
            continue

        description_node = teaser.select_one(".bpa-teaser-text-inner, .bpa-text, p")
        description = (
            " ".join(description_node.get_text(" ", strip=True).split())
            if description_node else ""
        )

        deadline_node = teaser.select_one(".bpa-teaser-date, time, .bpa-time")
        deadline = (
            " ".join(deadline_node.get_text(" ", strip=True).split())
            if deadline_node else ""
        )
        if not deadline:
            deadline = "laufend"

        seen_links.add(href)
        items.append({
            "title": title,
            "funder": FUNDER,
            "deadline": deadline,
            "link": href,
            "description": description,
            "target_group": "Hochschulen, Forschungseinrichtungen und Unternehmen (siehe Ausschreibung)",
        })

    items.sort(key=lambda item: (item["title"], item["link"]))
    return items