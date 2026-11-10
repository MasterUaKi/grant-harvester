def harvest_bundesministerium_f_r_bildung_und_forschung_bmbf_bekanntmachungen(html: str, base_url: str) -> list[dict]:
    """Harvest BMBF 'Bekanntmachungen' listing pages.

    Diagnostic note (why this returns an empty list for the current target):
      * https://www.bmbf.de/... now 302-redirects to the transitional domain
        https://www.bmftr.bund.de/ (Bundesministerium fuer Forschung,
        Technologie und Raumfahrt).
      * The legacy path
        /bmbf/de/forschung/foerderung/bekanntmachungen/bekanntmachungen_node.html
        no longer exists on the new domain, so the crawler lands on a
        404 shell (div.c-stage--404, h1 == '404 - Seite nicht gefunden').
      * That shell contains only a search form and topic tags -- zero
        grant announcements -- so no items can be extracted from it.

    Strategy:
      1. Hard-fail fast on error shells (return []).
      2. Scope parsing to main content, strip nav/form/slider chrome.
      3. Keep only anchors whose href or text looks like a funding notice.
    """
    from urllib.parse import urljoin
    import re

    from bs4 import BeautifulSoup

    FUNDER = "Bundesministerium für Bildung und Forschung (BMBF) – Bekanntmachungen"
    TARGET_GROUP = (
        "Forschungseinrichtungen, Hochschulen, außeruniversitäre Institute "
        "und forschende Unternehmen in Deutschland/EU"
    )

    items: list[dict] = []
    if not html or not html.strip():
        return items

    soup = BeautifulSoup(html, "html.parser")

    # --- 1. Abort on 404 / error shells --------------------------------
    headline = soup.find("h1")
    headline_text = headline.get_text(" ", strip=True) if headline else ""
    if soup.select_one(".c-stage--404") is not None or "404" in headline_text:
        return items

    # --- 2. Scope to the content column --------------------------------
    root = (
        soup.select_one("main.l-main #content")
        or soup.select_one("main.l-main")
        or soup.select_one("main")
        or soup
    )

    # --- 3. Remove navigation, search forms and slider chrome ----------
    for selector in (
        "nav",
        "header",
        "footer",
        "form",
        ".c-search__topics",
        ".c-slideshow-navigation",
        ".c-fancy-selects",
        ".c-autosuggest",
    ):
        for node in root.select(selector):
            node.decompose()

    # --- 4. Collect funding-notice links -------------------------------
    link_re = re.compile(
        r"bekanntmachung|foerderung|f(?:oe|ö)rderrichtlinie|ausschreibung|"
        r"richtlinie|foerderprogramm|call",
        re.IGNORECASE,
    )
    seen: set[str] = set()

    for anchor in root.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue

        title = " ".join(anchor.get_text(" ", strip=True).split())
        if len(title) < 12:
            continue

        link = urljoin(base_url, href)
        if not (link_re.search(link) or link_re.search(title)):
            continue
        if link in seen:
            continue
        seen.add(link)

        items.append(
            {
                "title": title,
                "funder": FUNDER,
                "deadline": "",
                "link": link,
                "description": "",
                "target_group": TARGET_GROUP,
            }
        )

    return items