# File: harvester.py
# Version: 2.15.0 | Release Date: 2026-11-10
"""
EN: Autonomous multi-portal grant harvester with two-tier System 2 reflection.
DE: Autonomer Multi-Portal-Grant-Harvester mit zweistufiger System-2-Reflexion.
"""

import ast
from collections import deque
from datetime import datetime
import importlib.util
import json
import logging
import os
from pathlib import Path
import re
import urllib.parse
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import httpx

from browser_fetcher import StealthBrowserEngine
from config import settings
from discovery import SourceDiscoveryManager
from pycognition.engine.llm_deliberator import LLMDeliberator, LLMProvider
from pycognition.engine.meta_arbiter import MetaArbiter
from pycognition.engine.procedural_runner import ProceduralRunner
from pycognition.engine.runtime import CognitiveRuntime
from pycognition.engine.skill_crystallizer import SkillCrystallizer
from pycognition.memory.registry import SkillRegistry
from pycognition.memory.vector_store import VectorStoreMemory
from pycognition.schemas import ExecutionStatus, SkillCapability, SkillSignature, Task
from schemas import FunderCategory, GrantItem, MultiSourceHarvestResult
from storage import GrantStorage
from unprocessed_tracker import UnprocessedTracker
from widget_builder import render_all_grants_catalog

load_dotenv()
logger = logging.getLogger("AutonomousSelfHealingHarvester")

NAV_KEYWORDS = [
    "foerder", "stipend", "programm", "ausschreib", "grant", "fellowship",
    "nachwuchs", "call", "bekanntmachung", "finanzier", "bewerb", "opportunity",
    "research-funding", "calls-for-proposals"
]

NOISE_KEYWORDS = [
    "impressum", "datenschutz", "privacy", "cookie", "login", "kontakt",
    "contact", "sitemap", "newsletter", "presse", "faq", "agb", "terms"
]

IGNORE_EXTENSIONS = (
    ".pdf", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".docx", ".xlsx", ".csv", ".mp4", ".tar", ".gz"
)


def clean_html_for_llm(raw_html: str, max_chars: int = 35000) -> str:
    """
    EN: Strips non-informative markup, scripts, and styling to preserve LLM token context.
    DE: Entfernt Skripte, Stylesheets und Navigationsstrukturen zur Optimierung des LLM-Kontexts.
    """
    if not raw_html:
        return ""
    try:
        soup = BeautifulSoup(raw_html, "html.parser")
        for tag in soup(["script", "style", "svg", "noscript", "header", "footer", "nav", "aside", "meta", "link"]):
            tag.decompose()

        for nav_div in soup.find_all(id=re.compile(r"nav|menu|cookie|consent|banner", re.I)):
            nav_div.decompose()
        for nav_class in soup.find_all(class_=re.compile(r"nav|menu|cookie|consent|banner", re.I)):
            nav_class.decompose()

        body = soup.body or soup
        return str(body)[:max_chars]
    except Exception:
        return raw_html[:max_chars]


def extract_promising_navigation_links(
    html: str, current_url: str, base_domain: str, max_links: int = 3
) -> list[str]:
    """
    EN: Evaluates and ranks internal links for directed graph exploration (Best-First Search).
    DE: Bewertet und ordnet interne Links für die gerichtete Graph-Exploration (Best-First Search).
    """
    if not html:
        return []
    try:
        soup = BeautifulSoup(html, "html.parser")
        scored_links = []
        seen = set()

        for a in soup.find_all("a", href=True):
            raw_href = a["href"].strip()
            if not raw_href or raw_href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            clean_href = raw_href.split("?")[0].lower()
            if clean_href.endswith(IGNORE_EXTENSIONS):
                continue

            full_url = urllib.parse.urljoin(current_url, raw_href)
            parsed = urllib.parse.urlparse(full_url)

            if not parsed.netloc.endswith(base_domain) and base_domain not in parsed.netloc:
                continue

            href_lower = full_url.lower()
            text_lower = (a.get_text() or "").lower()

            if any(noise in href_lower or noise in text_lower for noise in NOISE_KEYWORDS):
                continue

            norm_url = full_url.split("#")[0].rstrip("/")
            if norm_url in seen or norm_url == current_url.rstrip("/"):
                continue

            seen.add(norm_url)

            score = 0
            for kw in NAV_KEYWORDS:
                if kw in href_lower:
                    score += 3
                if kw in text_lower:
                    score += 2

            if score > 0:
                scored_links.append((score, full_url))

        scored_links.sort(key=lambda x: x[0], reverse=True)
        return [url for _, url in scored_links[:max_links]]
    except Exception:
        return []


class MultiPortalGrantHarvester:
    """
    EN: Main orchestrator coordinating graph crawls, deterministic skills, and LLM reflection.
    DE: Haupt-Orchestrator für Graph-Crawls, deterministische Skills und LLM-Reflexion.
    """

    def __init__(self):
        self.output_dir = Path(settings.OUTPUT_DIR).resolve()
        self.skills_dir = Path(os.getenv("PYCOGNITION_SKILLS_DIR", "./skills_registry")).resolve()
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.yields_file = self.skills_dir / "skills_yields.json"
        self.skill_yields = self._load_yields()

        self.storage = GrantStorage(settings.VAULT_DB_FILE)
        self.unprocessed_tracker = UnprocessedTracker(settings.UNPROCESSED_FILE)

        self.memory = VectorStoreMemory()
        self.system1 = ProceduralRunner()
        self.registry = SkillRegistry(storage_dir=self.skills_dir, runner=self.system1)

        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        provider = LLMProvider.DEEPSEEK if hasattr(LLMProvider, "DEEPSEEK") else LLMProvider.OPENAI

        fast_model = os.getenv("PYCOGNITION_FAST_MODEL", settings.FAST_MODEL)
        reasoner_model = os.getenv("PYCOGNITION_REASONER_MODEL", settings.REASONER_MODEL)

        # EN: Tier 1: Fast LLM for step 1 / DE: Stufe 1: Schnelles LLM für Schritt 1
        self.system2_fast = LLMDeliberator(
            provider=provider,
            api_key=api_key,
            model=fast_model,
            base_url=base_url,
            timeout=90.0
        )

        # EN: Tier 2: Deep reasoning R1 for steps 2..N / DE: Stufe 2: Tiefenreflexion R1 für Schritte 2..N
        self.system2_reasoner = LLMDeliberator(
            provider=provider,
            api_key=api_key,
            model=reasoner_model,
            base_url=base_url,
            timeout=180.0
        )

        threshold = float(os.getenv("PYCOGNITION_ARBITER_THRESHOLD", "0.55"))
        self.arbiter = MetaArbiter(memory=self.memory, confidence_threshold=threshold)
        self.crystallizer = SkillCrystallizer(storage_dir=self.skills_dir)

        self.runtime = CognitiveRuntime(
            arbiter=self.arbiter,
            system1=self.system1,
            system2=self.system2_fast,
            memory=self.memory,
            auto_crystallize=False
        )

        self.discovery_manager = SourceDiscoveryManager()
        self.browser_engine = StealthBrowserEngine()

        if hasattr(self.registry, "load_all"):
            self.registry.load_all()

    def _load_yields(self) -> dict[str, int]:
        if self.yields_file.exists():
            try:
                data = json.loads(self.yields_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return {str(k): int(v) for k, v in data.items()}
            except Exception:
                pass
        return {}

    def _record_yield(self, skill_name: str, count: int) -> None:
        if count >= self.skill_yields.get(skill_name, 0):
            self.skill_yields[skill_name] = count
            try:
                self.yields_file.write_text(
                    json.dumps(self.skill_yields, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
            except Exception as err:
                logger.debug(f"Failed updating yields / Fehler beim Aktualisieren der Yields: {err}")

    def _slugify(self, text: str) -> str:
        slug = re.sub(r'[^a-zA-Z0-9_]', '_', text.lower())
        return re.sub(r'_+', '_', slug).strip('_')

    async def fetch_url(self, url: str) -> tuple[str, int, str]:
        """
        EN: Hybrid fetcher with automated fallback to StealthBrowserEngine on bot barriers.
        DE: Hybrider Abruf mit automatischem Fallback auf StealthBrowserEngine bei Bot-Sperren.
        """
        stealth_domains = ["daad.de", "foerderdatenbank.de", "perfdrive", "kas.de", "studis-online.de", "europa.eu"]
        requires_stealth_browser = any(h in url.lower() for h in stealth_domains)

        if requires_stealth_browser:
            rendered_html = await self.browser_engine.fetch_page_html(url)
            if rendered_html:
                return rendered_html, 200, url

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "Upgrade-Insecure-Requests": "1"
        }
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SEC, follow_redirects=True) as client:
            try:
                resp = await client.get(url, headers=headers)
                if (
                    resp.status_code in (403, 401)
                    or "perfdrive" in str(resp.url)
                    or "challenge" in str(resp.url)
                    or "botmanager" in resp.text.lower()
                ):
                    logger.info(
                        f"EN: Bot challenge detected on {url}. Switching to Edge / "
                        f"DE: Bot-Challenge erkannt auf {url}. Wechsel zu Edge..."
                    )
                    rendered_html = await self.browser_engine.fetch_page_html(url)
                    if rendered_html:
                        return rendered_html, 200, str(resp.url)
                return resp.text, resp.status_code, str(resp.url)
            except Exception as e:
                logger.debug(
                    f"EN: HTTP client error ({e}). Retrying with browser / "
                    f"DE: HTTP-Fehler ({e}). Neuer Versuch mit Browser: {url}"
                )
                rendered_html = await self.browser_engine.fetch_page_html(url)
                if rendered_html:
                    return rendered_html, 200, url
                return "", 500, url

    def _execute_crystallized_skill(self, skill_func_name: str, html: str, base_url: str) -> list[dict]:
        skill_file = self.skills_dir / f"{skill_func_name}.py"
        if not skill_file.exists():
            return []

        try:
            spec = importlib.util.spec_from_file_location(skill_func_name, str(skill_file))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                func = getattr(mod, skill_func_name, None)
                if callable(func):
                    result = func(html, base_url)
                    if isinstance(result, list) and len(result) > 0:
                        return result
        except Exception as exc:
            logger.debug(
                f"EN: Skill {skill_func_name} raised exception / "
                f"DE: Skill {skill_func_name} warf Ausnahme: {exc}"
            )
        return []

    async def _resolve_mangled_title(self, item_snippet: str, source_name: str) -> str:
        """
        EN: Employs System 2 to restore clean titles when extractors yield single characters.
        DE: Nutzt System 2 zur Rekonstruktion vollständiger Titel bei fehlerhafter Extraktion.
        """
        prompt = (
            f"You are a scientific data cleaner for German/EU research grants.\n"
            f"Funder: {source_name}\n"
            f"A web extractor failed and returned an invalid/corrupted 1-character title from this snippet:\n"
            f"--- SNIPPET START ---\n{item_snippet[:1500]}\n--- SNIPPET END ---\n\n"
            f"TASK: Extract the exact, full official title of the grant call or announcement.\n"
            f"Rules:\n"
            f"1. Return ONLY the clean, full title string.\n"
            f"2. Do NOT add JSON, quotes, or markdown wrappers."
        )
        task = Task(prompt=prompt, payload={"source_name": source_name})
        try:
            res = await self.system2_fast.deliberate(task)
            out = getattr(res, "output", getattr(res, "result", "")).strip()
            out = re.sub(r"<think>.*?</think>", "", out, flags=re.DOTALL).strip('`"\' \n')
            if len(out) >= 6:
                return out
        except Exception:
            pass
        return ""

    async def _solve_with_reflection_loop(
        self,
        source_info: dict,
        error_type: str,
        details: str,
        html_body: str,
        current_url: str,
        max_attempts: int = 2
    ) -> tuple[list[dict], str]:
        """
        EN: Two-tier reflection loop synthesizing parsing subroutines via Fast LLM and Reasoner R1.
        DE: Zweistufige Reflexionsschleife zur Synthese von Parser-Subroutinen via Fast LLM und R1.
        """
        name = source_info["name"]
        slug = self._slugify(name)
        skill_func_name = f"harvest_{slug}"
        clean_sample = clean_html_for_llm(html_body, max_chars=32000)
        baseline = self.skill_yields.get(skill_func_name, 0)

        previous_error = ""
        previous_code = ""
        discovered_items = []
        active_url = current_url

        for attempt in range(1, max_attempts + 1):
            if attempt == 1:
                active_deliberator = self.system2_fast
                active_model_name = settings.FAST_MODEL
                logger.warning(
                    f"[System 2: Fast Analysis / Schnellanlyse ({active_model_name})] "
                    f"Processing / Verarbeite '{name}' on {current_url}..."
                )
                reflection_block = ""
            else:
                active_deliberator = self.system2_reasoner
                active_model_name = settings.REASONER_MODEL
                logger.warning(
                    f"[System 2: R1 Deep Reflection / Tiefenreflexion #{attempt}/{max_attempts} ({active_model_name})] "
                    f"Healing error for / Behebe Fehler für '{name}': {previous_error}"
                )
                reflection_block = (
                    f"\nCRITICAL FEEDBACK FROM PREVIOUS ATTEMPT (Attempt #{attempt - 1} FAILED):\n"
                    f"Error encountered: {previous_error}\n"
                    f"Your previous code was:\n"
                    f"--- CODE START ---\n"
                    f"{previous_code}\n"
                    f"--- CODE END ---\n"
                    f"Please fix this exact error. Ensure your selectors extract FULL titles, not single letters!\n"
                )

            prompt = (
                f"You are the System 2 Extraction Architect of the pycognition autonomous framework.\n"
                f"Target Name: {name}\n"
                f"Failing URL: {current_url}\n"
                f"Error Context: {error_type} ({details[:500]})\n"
                f"{reflection_block}\n\n"
                f"CRITICAL EXTRACTION INTEGRITY RULES:\n"
                f"1. TITLE INTEGRITY: Full human-readable title is REQUIRED (minimum 8 characters). Never extract single letters like 's', ')', '6'!\n"
                f"2. DEADLINE: Format as 'DD.MM.YYYY' or 'laufend / ongoing'.\n"
                f"3. CONSTRAINTS: No secondary network requests (no urllib/requests) inside the function.\n\n"
                f"Clean HTML content from the page:\n"
                f"{clean_sample}\n\n"
                f"Synthesize a deterministic function:\n"
                f"`def {skill_func_name}(html: str, base_url: str) -> list[dict]:`\n"
                f"Return strictly valid JSON:\n"
                f"{{\n"
                f'  "active_url": "{current_url}",\n'
                f'  "discovered_items": [\n'
                f'    {{"title": "...", "funder": "{name}", "deadline": "laufend / ongoing", "link": "...", "description": "...", "target_group": "..."}}\n'
                f"  ],\n"
                f'  "python_subroutine": "def {skill_func_name}(html, base_url):\\n    ...\\n    return items"\n'
                f"}}\n"
            )

            task = Task(prompt=prompt, payload={"source_name": name, "url": current_url, "attempt": attempt})
            heal_res = await active_deliberator.deliberate(task)
            raw_output = getattr(heal_res, "output", getattr(heal_res, "result", ""))

            try:
                clean_text = re.sub(r"<think>.*?</think>", "", str(raw_output), flags=re.DOTALL)
                clean_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", clean_text.strip())
                start_idx = clean_text.find('{')
                end_idx = clean_text.rfind('}')

                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    data = json.loads(clean_text[start_idx : end_idx + 1])
                else:
                    raise ValueError("JSON object not found in System 2 response.")
            except Exception as e:
                previous_error = f"JSON decode error: {e}"
                continue

            active_url = data.get("active_url") or current_url
            items = data.get("discovered_items", [])
            subroutine = data.get("python_subroutine", "")

            if not subroutine or skill_func_name not in subroutine:
                previous_error = f"Function '{skill_func_name}' was not found in synthesized code."
                continue

            clean_code = re.sub(r"^```(?:python)?\s*|\s*```$", "", subroutine.strip())
            previous_code = clean_code

            test_args = (html_body, active_url)
            success, msg, yld = self.crystallizer.crystallize_with_regression_guard(
                code=clean_code,
                func_name=skill_func_name,
                capability=SkillCapability.DATA_EXTRACTOR,
                test_args=test_args,
                baseline_yield=baseline
            )

            if success:
                self._record_yield(skill_func_name, yld)
                logger.info(
                    f"[Crystallization / Kristallisation]: Skill '{skill_func_name}' "
                    f"verified (yield / ausbeute: {yld})."
                )
                if hasattr(self.registry, "load_all"):
                    self.registry.load_all()
                return (items if isinstance(items, list) else []), active_url
            else:
                previous_error = msg
                logger.warning(
                    f"[Reflection / Reflexion] Candidate rejected / Kandidat abgelehnt: {msg}"
                )

        return (discovered_items if isinstance(discovered_items, list) else []), active_url

    async def process_source(
        self,
        source_info: dict,
        max_depth: int | None = None,
        max_pages: int | None = None
    ) -> list[GrantItem]:
        """
        EN: Executes directed graph crawling across a specific funding portal.
        DE: Führt gerichtetes Graph-Crawling über ein bestimmtes Förderportal aus.
        """
        depth_limit = max_depth or settings.MAX_CRAWL_DEPTH
        pages_limit = max_pages or settings.MAX_PAGES_PER_SOURCE
        reflection_limit = settings.MAX_REFLECTION_ATTEMPTS

        name = source_info["name"]
        start_url = source_info["url"]
        slug = self._slugify(name)
        skill_func_name = f"harvest_{slug}"
        cat_str = source_info.get("category", "Other / Sonstige")

        category = FunderCategory.OTHER
        for c in FunderCategory:
            if c.value == cat_str or c.name == cat_str:
                category = c
                break

        base_domain = urllib.parse.urlparse(start_url).netloc.split(":")[0]
        if base_domain.startswith("www."):
            base_domain = base_domain[4:]

        queue = deque([(start_url, 1)])
        visited = {start_url.split("#")[0].rstrip("/").lower()}
        grants: list[GrantItem] = []
        seen_links = set()
        pages_processed = 0

        logger.info(
            f"==> EN: Starting crawl / DE: Starte Crawl: {name} "
            f"(Depth / Tiefe: {depth_limit}, Pages / Seiten: {pages_limit})"
        )

        while queue and pages_processed < pages_limit:
            current_url, current_depth = queue.popleft()
            pages_processed += 1

            html, status, final_url = await self.fetch_url(current_url)
            page_raw_items = []

            # 1. System 1 deterministic execution
            if status == 200 and html:
                page_raw_items = self._execute_crystallized_skill(skill_func_name, html, final_url)
                if page_raw_items:
                    self._record_yield(skill_func_name, len(page_raw_items))
                    logger.info(
                        f"[SYSTEM 1] (Depth / Tiefe {current_depth}) Skill {skill_func_name} "
                        f"extracted / extrahierte {len(page_raw_items)} programs."
                    )

            # 2. System 2 reflection on initial failures
            if not page_raw_items and not grants and current_depth <= 3:
                err_type = f"HTTP_{status}" if status != 200 else "EMPTY_DOM_DRIFT"
                discovered, healed_url = await self._solve_with_reflection_loop(
                    source_info=source_info,
                    error_type=err_type,
                    details=f"Status: {status}, Final URL: {final_url}",
                    html_body=html,
                    current_url=final_url,
                    max_attempts=reflection_limit
                )
                if discovered:
                    page_raw_items = discovered
                    if healed_url != start_url and healed_url.startswith("http"):
                        logger.info(
                            f"EN: [Route Updated] Source '{name}' now points to {healed_url} / "
                            f"DE: [Route aktualisiert] Quelle '{name}' verweist nun auf {healed_url}"
                        )
                        source_info["url"] = healed_url

            # 3. Item normalization and Title Quality Barrier
            for it in page_raw_items:
                if not isinstance(it, dict):
                    continue

                raw_title = str(it.get("title", "")).strip()
                rel_link = str(it.get("link", "")).strip()
                abs_link = urllib.parse.urljoin(final_url, rel_link) if rel_link else final_url

                if abs_link in seen_links:
                    continue

                # Title Quality Barrier: Reject single characters and restore via System 2
                if len(raw_title) < 6 or raw_title in [")", "s", "6", "”", "“", '"', "-", "mehr"]:
                    desc_snippet = str(it.get("description", ""))
                    recovered_title = await self._resolve_mangled_title(desc_snippet, name)
                    if recovered_title:
                        raw_title = recovered_title
                        logger.info(
                            f"[System 2: Title Recovery / Titelwiederherstellung] "
                            f"Restored / Wiederhergestellt: '{raw_title}'"
                        )
                    else:
                        continue

                seen_links.add(abs_link)

                grants.append(GrantItem(
                    title=raw_title,
                    funder=str(it.get("funder", name)).strip(),
                    funder_category=category,
                    target_group=str(it.get("target_group", source_info.get("target_group", "Researchers / Wissenschaftler"))),
                    deadline=it.get("deadline") or "laufend / ongoing",
                    funding_amount=it.get("funding_amount"),
                    link=abs_link,
                    description=str(it.get("description", "")).strip(),
                    source_portal=name,
                    is_newly_discovered=(category in [FunderCategory.DISCOVERY, FunderCategory.FOUNDATION])
                ))

            # 4. Enqueue promising child URLs
            if current_depth < depth_limit and status == 200 and html:
                child_links = extract_promising_navigation_links(html, final_url, base_domain, max_links=2)
                for cl in child_links:
                    norm_cl = cl.split("#")[0].rstrip("/").lower()
                    if norm_cl not in visited:
                        visited.add(norm_cl)
                        queue.append((cl, current_depth + 1))
                        logger.debug(
                            f"[Queue / Warteschlange] Scheduled / Eingeplant: "
                            f"depth {current_depth + 1} -> {cl}"
                        )

        if len(grants) == 0:
            self.unprocessed_tracker.record_unprocessed(
                source_name=name,
                url=start_url,
                failure_type="ZERO_YIELD_OR_DOM_DRIFT",
                details=f"Visited {pages_processed} pages (depth {depth_limit}), 0 programs harvested.",
                html_sample=html[:2000] if 'html' in locals() and html else None
            )

        logger.info(
            f"EN: Summary for {name}: {pages_processed} pages, {len(grants)} programs / "
            f"DE: Fazit für {name}: {pages_processed} Seiten, {len(grants)} Programme."
        )
        return grants

    async def run_full_harvest_cycle(self) -> MultiSourceHarvestResult:
        """
        EN: Coordinates full monitoring cycle across all known and newly discovered sources.
        DE: Koordiniert den vollständigen Überwachungszyklus über alle bekannten und neuen Quellen.
        """
        logger.info(
            "=== EN: Starting Harvest Cycle: Discovery -> Self-Healing -> Vault -> Catalog ===\n"
            "=== DE: Starte Erfassungszyklus: Discovery -> Selbstheilung -> Vault -> Katalog ==="
        )
        logger.info(
            f"Configuration / Konfiguration: Depth/Tiefe={settings.MAX_CRAWL_DEPTH}, "
            f"Reflection/Reflexion={settings.MAX_REFLECTION_ATTEMPTS}, "
            f"MaxPages/MaxSeiten={settings.MAX_PAGES_PER_SOURCE}"
        )

        sources = await self.discovery_manager.discover_new_sources(system2=self.system2_fast)

        unique_sources = []
        seen_names = set()
        for s in sources:
            if s["name"] not in seen_names:
                seen_names.add(s["name"])
                unique_sources.append(s)

        self.discovery_manager.save_registry(unique_sources)
        total_sources = len(unique_sources)
        logger.info(
            f"EN: Active registry contains {total_sources} distinct sources / "
            f"DE: Aktives Register enthält {total_sources} eigenständige Quellen."
        )

        current_run_grants: list[GrantItem] = []

        for idx, src in enumerate(unique_sources, start=1):
            progress_pct = round(((idx - 1) / total_sources) * 100, 1)
            src_name = src.get("name", "Unknown Source / Unbekannte Quelle")

            logger.info(
                f"\n============================================================\n"
                f"[{progress_pct:5.1f}% CYCLE / ZYKLUS] Source / Quelle {idx}/{total_sources}: {src_name}\n"
                f"============================================================"
            )

            try:
                grants = await self.process_source(src)
                if grants:
                    current_run_grants.extend(grants)
            except Exception as err:
                logger.error(
                    f"EN: Unhandled error in source / DE: Unbehandelter Fehler in Quelle {src_name}: {err}"
                )

            completed_pct = round((idx / total_sources) * 100, 1)
            found_this_step = len(grants) if 'grants' in locals() and grants else 0
            logger.info(
                f"[{completed_pct:5.1f}% CYCLE / ZYKLUS] Completed / Abgeschlossen {idx}/{total_sources} ({src_name}). "
                f"Harvested in step / In diesem Schritt erfasst: {found_this_step}."
            )

        new_count, verified_count = self.storage.upsert_grants(current_run_grants)
        expired_count, archived_count = self.storage.update_lifecycle_statuses(archive_threshold_days=45)

        active_consolidated_grants = self.storage.get_active_grants()
        stats = self.storage.get_summary_statistics()

        result_payload = MultiSourceHarvestResult(
            harvested_at=datetime.now().isoformat(),
            total_grants=len(active_consolidated_grants),
            active_sources=stats["unique_active_funders"],
            new_grantors_found=new_count,
            grants=active_consolidated_grants
        )

        self.output_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.output_dir / "all_grants.json"
        catalog_path = self.output_dir / "all_grants_catalog.html"

        json_path.write_text(result_payload.model_dump_json(indent=2), encoding="utf-8")
        render_all_grants_catalog(result_payload, catalog_path)

        await self.browser_engine.close()

        logger.info("============================================================")
        logger.info(
            f"[100.0% CYCLE COMPLETE / ZYKLUS ABGESCHLOSSEN] "
            f"Active / Aktiv: {stats['active_grants']} programs from {stats['unique_active_funders']} sources! "
            f"(New/Neu: {new_count}, Confirmed/Bestätigt: {verified_count}, Expired/Ausgelaufen: {expired_count}, Total Vault: {stats['total_records']})"
        )
        logger.info(f"EN: Catalog generated / DE: Katalog generiert: {catalog_path.resolve()}")
        logger.info(f"EN: Next scheduled run in / DE: Nächster Durchlauf in: {settings.INTERVAL_MINUTES} min.")
        logger.info("============================================================")
        return result_payload