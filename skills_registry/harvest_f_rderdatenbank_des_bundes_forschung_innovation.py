def harvest_f_rderdatenbank_des_bundes_forschung_innovation(html: str, base_url: str) -> list[dict]:
    """Parse Förderdatenbank des Bundes programme-search result pages.

    Hardened against WAF/bot-challenge interstitials (Radware perfdrive /
    hCaptcha): such pages yield [] so the harvester can escalate instead of
    emitting garbage records. Output order is deterministic (title, link).
    """
    import re
    from urllib.parse import urljoin, urlparse
    from bs4 import BeautifulSoup

    FUNDER = "Förderdatenbank des Bundes (Forschung & Innovation)"
    BASE_HOST = "foerderdatenbank.de"
    items: list[dict] = []

    if not isinstance(html, str) or not html.strip():
        return items

    soup = BeautifulSoup(html, "html.parser")

    # 1) WAF / bot-challenge guard: never emit records from an interstitial
    if soup.select_one("div.h-captcha, input#cf_input"):
        return items
    guard = soup.get_text(" ", strip=True).lower()
    if "captcha" in guard and ("bot" in guard or "unblock" in guard):
        return items

    # 2) Result containers, most specific selectors first
    containers = soup.select(
        "div.listEntry, li.listEntry, div.result, li.result, div.teaser, li.teaser, "
        "ul.list > li, ol.list > li, div.fdb-result, article, table tbody tr"
    )
    if not containers:
        containers = soup.select("main, #content, .content, body") or [soup]

    DATE_RE = re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b|\b\d{4}-\d{2}-\d{2}\b")
    DEADLINE_RE = re.compile(
        r"(?:antragsfrist|einreichungsfrist|frist|deadline|bewerbungsschluss)\s*[:\-–]?\s*([^\n;|]{0,80})",
        re.I,
    )
    TARGET_RE = re.compile(
        r"(?:zielgruppe|zuwendungsempf(?:ä|ae)nger|antragsberechtigt\w*|wer wird gef(?:ö|oe)rdert)\s*[:\-–]?\s*([^\n;|]{0,160})",
        re.I,
    )
    DETAIL_RE = re.compile(r"(foerderprogramm|FDB/|/FDB|detail|programm)", re.I)
    SKIP_RE = re.compile(
        r"(validate\.perfdrive\.com|captcha|javascript:|mailto:|tel:|/login|/logout|"
        r"/impressum|/datenschutz|/kontakt)",
        re.I,
    )

    seen: set[str] = set()
    for node in containers:
        for a in node.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if not href or SKIP_RE.search(href):
                continue
            title = " ".join(a.get_text(" ", strip=True).split())
            if len(title) < 4:
                continue

            link = urljoin(base_url, href)
            parts = urlparse(link)
            if BASE_HOST not in parts.netloc.lower():
                continue
            if link in seen:
                continue
            if len(title) < 12 and not DETAIL_RE.search(parts.path + parts.query):
                continue
            seen.add(link)

            scope = a.find_parent(["li", "article", "tr", "div", "section"]) or node
            snippet = " ".join(scope.get_text(" ", strip=True).split())
            description = snippet[len(title):] if snippet.startswith(title) else snippet
            description = " ".join(description.split()).strip(" :–-|")[:400]

            deadline = ""
            m = DEADLINE_RE.search(snippet)
            if m:
                dm = DATE_RE.search(m.group(1))
                deadline = dm.group(0) if dm else m.group(1).strip(" .;|")
            else:
                dm = DATE_RE.search(snippet)
                deadline = dm.group(0) if dm else ""

            target_group = ""
            tm = TARGET_RE.search(snippet)
            if tm:
                target_group = tm.group(1).strip(" .;|")[:160]

            items.append(
                {
                    "title": title,
                    "funder": FUNDER,
                    "deadline": deadline,
                    "link": link,
                    "description": description,
                    "target_group": target_group,
                }
            )

    items.sort(key=lambda r: (r["title"].lower(), r["link"]))
    return items