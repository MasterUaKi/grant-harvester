def harvest_stipendien_bmftr(html: str, base_url: str) -> list[dict]:
    """Deterministic harvester for BMFTR scholarship overview pages."""
    import re
    from urllib.parse import urljoin
    from bs4 import BeautifulSoup

    FUNDER = "Stipendien- BMFTR"
    NO_DEADLINE = "Not specified"
    DEFAULT_GROUP = "Studierende und Nachwuchswissenschaftlerinnen und -wissenschaftler"

    if not html or not isinstance(html, str) or not html.strip():
        return []

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style", "noscript", "header", "footer", "nav", "form"]):
        tag.decompose()

    containers = []
    for selector in (
        "div.l-article__content",
        "div.s-article-content",
        "div.l-article",
        "main.l-main",
        "main",
        "#content",
    ):
        containers = soup.select(selector)
        if containers:
            break
    if not containers:
        containers = [soup]

    keywords = ("stipend", "begabtenf", "bafoeg", "bafög", "foerder", "förder")

    target_rules = (
        ("promotionsstipend", "Doktorandinnen und Doktoranden"),
        ("aufstiegsstipendium", "Berufserfahrene"),
        ("weiterbildungsstipendium", "Berufseinsteigerinnen und Berufseinsteiger nach der Ausbildung"),
        ("auszubildende", "Auszubildende"),
        ("deutschlandstipendium", "Studierende an Hochschulen"),
        ("begabtenfoerderungswerk", "Studierende und Promovierende"),
    )

    date_re = re.compile(r"\b\d{1,2}\.\s?\d{1,2}\.\s?\d{4}\b")
    deadline_re = re.compile(
        r"(?:Bewerbungsfrist|Bewerbungsschluss|Deadline)[^.;:]{0,80}", re.IGNORECASE
    )
    title_clean_re = re.compile(
        r"\s*\((?:www\.)?[A-Za-z0-9.-]+\.(?:de|org|com|eu|net)\)\s*$", re.IGNORECASE
    )

    base_key = base_url.split("#")[0].rstrip("/")
    items, seen = [], set()

    for container in containers:
        for anchor in container.find_all("a", href=True):
            href = anchor["href"].strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            link = urljoin(base_url, href)
            if not link.startswith(("http://", "https://")):
                continue
            link_key = link.split("#")[0].rstrip("/")
            if link_key == base_key or link_key in seen:
                continue

            title = " ".join(anchor.get_text(" ", strip=True).split())
            if not title:
                title = " ".join((anchor.get("title") or "").split())
            title = title_clean_re.sub("", title).strip()
            if not title:
                continue

            haystack = (title + " " + link).lower()
            if not any(k in haystack for k in keywords):
                continue

            context = ""
            parent_li = anchor.find_parent("li")
            if parent_li is not None:
                context = " ".join(parent_li.get_text(" ", strip=True).split())

            deadline = NO_DEADLINE
            match = deadline_re.search(context) or date_re.search(context)
            if match:
                deadline = match.group(0).strip()

            description = ""
            if context and context != title:
                description = context
                if description.startswith(title):
                    description = description[len(title):].strip(" -–—:|")
            if description:
                description = description[:500]

            target_group = DEFAULT_GROUP
            lowered = title.lower()
            for probe, label in target_rules:
                if probe in lowered:
                    target_group = label
                    break

            seen.add(link_key)
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

    return items