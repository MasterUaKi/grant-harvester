# File: harvester.py
# Version: 2.1.0 | Release Date: 2026-11-12
# EN: Autonomous multi-portal grant harvester powered by PyCognition v1.2.0 skills subsystem.
# DE: Autonomer Multi-Portal-Fördermittel-Harvester auf Basis des PyCognition v1.2.0 Skills-Subsystems.

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import inspect
import json
import logging
import os
import re
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

# Ensure local PyCognition source tree is resolvable even without editable reinstall
_LOCAL_PYCOGNITION_SRC = Path(r"C:\Entwiklung\pycognition\src")
if _LOCAL_PYCOGNITION_SRC.exists() and str(_LOCAL_PYCOGNITION_SRC) not in sys.path:
    sys.path.insert(0, str(_LOCAL_PYCOGNITION_SRC))

# Core PyCognition v1.2.0 imports / Kern-Importe aus PyCognition v1.2.0
from pycognition.skills import (
    AnomalyThresholds,
    ExecutionScope,
    SkillCapability,
    SkillCrystallizer,
    SkillExecutionTelemetry,
    TelemetryEvaluator,
)

try:
    from pycognition.engine.llm_deliberator import LLMDeliberator
except ImportError:
    LLMDeliberator = None  # type: ignore

# Local harvester modules / Lokale Harvester-Module
try:
    from config import settings
except ImportError:
    settings = None

import schemas
from schemas import GrantItem
from storage import GrantStorage

try:
    from browser_fetcher import StealthBrowserEngine as _BrowserCls
except ImportError:
    from browser_fetcher import StealthBrowser as _BrowserCls

try:
    from discovery import SourceDiscoveryManager as _DiscoveryCls
except ImportError:
    from discovery import SourceDiscovery as _DiscoveryCls

try:
    from unprocessed_tracker import UnprocessedTracker
except ImportError:
    UnprocessedTracker = None  # type: ignore

try:
    import widget_builder
except ImportError:
    widget_builder = None  # type: ignore


logger = logging.getLogger("AutonomousSelfHealingHarvester")


# ==============================================================================
# Main Autonomous Harvester / Hauptklasse des autonomen Harvesters
# ==============================================================================

class AutonomousSelfHealingHarvester:
    """
    EN: Dual-tier cognitive harvester delegating AST capability auditing, sandbox
        dry-runs, telemetry scoring, and regression-guarded skill crystallization
        to PyCognition v1.2.0 (`pycognition.skills`).
    DE: Zweistufiger kognitiver Harvester, der AST-Capability-Audits, Sandbox-Tests,
        Telemetrie-Bewertung und regressionsgeschützte Skill-Kristallisierung an
        PyCognition v1.2.0 (`pycognition.skills`) delegiert.
    """

    CORRUPT_TITLE_PATTERNS: Tuple[str, ...] = (
        "cannot extract",
        "can't extract",
        "snippet is empty",
        "no title",
        "не удалось извлечь",
        "не могу извлечь",
        "фрагмент пуст",
        "nicht extrahiert werden",
        "skip to content",
        "zum hauptinhalt",
        "cookie",
        "datenschutz",
        "impressum",
        "mehr erfahren",
        "read more",
        "weiterlesen",
    )

    SPA_DOMAIN_HINTS: Tuple[str, ...] = (
        "ec.europa.eu",
        "erc.europa.eu",
        "kas.de",
        "daad.de",
        "funding-tenders",
        "bayer-foundation.com",
    )

    VALID_FUNDER_CATEGORIES: Tuple[str, ...] = (
        "DFG",
        "BMBF / Bund",
        "EU Funding / EU-Förderung",
        "Foundations / Stiftungen",
        "Scholarships / Stipendien",
        "Discovered Sources / Neu entdeckte Quellen",
        "Other / Sonstige",
    )

    ALLOWED_SKILL_MODULES: Set[str] = {
        "bs4", "re", "json", "typing", "datetime", "urllib", "math", "html"
    }

    def __init__(
        self,
        max_crawl_depth: Optional[int] = None,
        max_reflection_attempts: Optional[int] = None,
        max_pages_per_source: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        self.base_dir = Path(__file__).resolve().parent
        self.skills_dir = self.base_dir / "skills_registry"
        self.output_dir = self.base_dir / "output"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.max_crawl_depth: int = (
            max_crawl_depth if max_crawl_depth is not None else self._get_cfg("MAX_CRAWL_DEPTH", 6, int)
        )
        self.max_reflection_attempts: int = (
            max_reflection_attempts
            if max_reflection_attempts is not None
            else self._get_cfg("MAX_REFLECTION_ATTEMPTS", 2, int)
        )
        self.max_pages_per_source: int = (
            max_pages_per_source
            if max_pages_per_source is not None
            else self._get_cfg("MAX_PAGES_PER_SOURCE", 10, int)
        )
        self.deepseek_api_key: str = self._get_cfg("DEEPSEEK_API_KEY", "", str)
        self.deepseek_base_url: str = self._get_cfg("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1", str).rstrip("/")
        self.fast_model: str = self._get_cfg("PYCOGNITION_FAST_MODEL", "deepseek-chat", str)
        self.reasoner_model: str = self._get_cfg("PYCOGNITION_REASONER_MODEL", "deepseek-reasoner", str)

        # PyCognition v1.2.0 Telemetry & Crystallization Engine
        self.telemetry_evaluator = TelemetryEvaluator(
            required_key="title",
            min_length=5,
            max_length=260,
            thresholds=AnomalyThresholds(
                max_corruption_ratio=0.25,
                min_sample_size_for_ratio=3,
                trigger_on_zero_yield_first_pass=True,
            ),
            custom_validator=self._validate_domain_record,
        )
        self.crystallizer = SkillCrystallizer(
            registry_dir=self.skills_dir,
            evaluator=self.telemetry_evaluator,
            version_tag="2.1.0",
        )

        # Harvester domain subsystems / Domain-Subsysteme
        self.storage = GrantStorage()
        self.discovery = _DiscoveryCls()
        self.browser: Optional[Any] = None
        self._browser_entered: bool = False
        self.tracker = UnprocessedTracker() if UnprocessedTracker is not None else None
        self._loaded_skills: Dict[str, Any] = {}
        self._schema_error_logged: bool = False

        self.deliberator: Optional[Any] = None
        if LLMDeliberator is not None and self.deepseek_api_key:
            try:
                self.deliberator = LLMDeliberator(
                    api_key=self.deepseek_api_key,
                    base_url=self.deepseek_base_url,
                    model=self.reasoner_model,
                )
            except Exception:
                self.deliberator = None

    @staticmethod
    def _get_cfg(key: str, default: Any, cast: type) -> Any:
        val = None
        if settings is not None:
            val = getattr(settings, key, None) or getattr(settings, key.lower(), None)
        if val is None:
            val = os.getenv(key)
        if val is None or val == "":
            return default
        try:
            return cast(val)
        except (ValueError, TypeError):
            return default

    # --------------------------------------------------------------------------
    # Public Entrypoints / Öffentliche Einstiegspunkte
    # --------------------------------------------------------------------------

    async def run_full_harvest_cycle(self) -> Dict[str, Any]:
        """
        EN: Executes a complete autonomous cycle: Source Discovery -> Graph Crawl &
            PyCognition Self-Healing -> SQLite Vault -> Bilingual HTML/JSON Catalog.
        DE: Führt einen vollständigen autonomen Zyklus aus: Quellenermittlung ->
            Graph-Crawl & PyCognition-Selbstheilung -> SQLite-Vault -> HTML/JSON-Katalog.
        """
        logger.info(
            "=== EN: Starting Harvest Cycle (PyCognition v1.2.0 Core): Discovery -> Self-Healing -> Vault -> Catalog ===\n"
            "=== DE: Starte Erfassungszyklus (PyCognition v1.2.0 Core): Discovery -> Selbstheilung -> Vault -> Katalog ==="
        )
        logger.info(
            f"Configuration / Konfiguration: Depth/Tiefe={self.max_crawl_depth}, "
            f"Reflection/Reflexion={self.max_reflection_attempts}, MaxPages/MaxSeiten={self.max_pages_per_source}"
        )

        sources = await self._discover_sources()
        total_sources = len(sources)
        logger.info(
            f"EN: Active registry contains {total_sources} distinct sources / "
            f"DE: Aktives Register enthält {total_sources} eigenständige Quellen."
        )

        total_cycle_harvested = 0

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=15.0),
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0"
                    ),
                    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
                },
            ) as http_client:
                for idx, source in enumerate(sources, start=1):
                    src_name = source.get("name") or source.get("title") or f"Source-{idx}"
                    src_url = source.get("url") or source.get("seed_url") or ""
                    src_cat = source.get("category") or source.get("funder_category") or ""
                    if not src_url:
                        continue

                    pct = ((idx - 1) / max(1, total_sources)) * 100.0
                    logger.info(
                        f"\n{'=' * 60}\n"
                        f"[{pct:5.1f}% CYCLE / ZYKLUS] Source / Quelle {idx}/{total_sources}: {src_name}\n"
                        f"{'=' * 60}"
                    )

                    step_count = await self._crawl_and_harvest_source(
                        source_name=src_name,
                        seed_url=src_url,
                        funder_category=src_cat,
                        http_client=http_client,
                    )
                    total_cycle_harvested += step_count

                    done_pct = (idx / max(1, total_sources)) * 100.0
                    logger.info(
                        f"[{done_pct:5.1f}% CYCLE / ZYKLUS] Completed / Abgeschlossen {idx}/{total_sources} "
                        f"({src_name}). Harvested in step / In diesem Schritt erfasst: {step_count}."
                    )
        finally:
            await self._close_browser()

        active_count = await self._export_artifacts(total_sources=total_sources)

        logger.info(
            f"[100.0% CYCLE COMPLETE / ZYKLUS ABGESCHLOSSEN] "
            f"Active / Aktiv: {active_count} programs from {total_sources} sources!"
        )
        return {
            "sources_processed": total_sources,
            "cycle_harvested": total_cycle_harvested,
            "active_vault_total": active_count,
        }

    async def run_cycle(self) -> Dict[str, Any]:
        return await self.run_full_harvest_cycle()

    # --------------------------------------------------------------------------
    # Source Discovery & Catalog Export / Quellenermittlung & Katalog-Export
    # --------------------------------------------------------------------------

    async def _discover_sources(self) -> List[Dict[str, Any]]:
        for method_name in (
            "discover_and_get_sources",
            "discover_new_sources",
            "get_active_sources",
            "load_registry",
            "get_sources",
        ):
            fn = getattr(self.discovery, method_name, None)
            if callable(fn):
                res = fn()
                if inspect.isawaitable(res):
                    res = await res
                if isinstance(res, list) and res:
                    return [
                        item.model_dump() if hasattr(item, "model_dump") else dict(item)
                        for item in res
                    ]

        if settings is not None and hasattr(settings, "SEED_SOURCES"):
            return list(settings.SEED_SOURCES)
        return []

    async def _export_artifacts(self, total_sources: int = 0) -> int:
        all_grants: List[Any] = []
        for getter_name in ("get_all_active_grants", "get_active_grants", "get_all_grants", "fetch_all"):
            fn = getattr(self.storage, getter_name, None)
            if callable(fn):
                res = fn()
                if inspect.isawaitable(res):
                    res = await res
                if isinstance(res, list):
                    all_grants = res
                    break

        grant_models: List[GrantItem] = []
        for g in all_grants:
            if isinstance(g, GrantItem):
                grant_models.append(g)
            elif isinstance(g, dict):
                converted = self._to_grant_item(
                    g,
                    source_name=str(g.get("source_portal") or g.get("funder") or "Vault"),
                    page_url=str(g.get("link") or g.get("url") or "https://localhost"),
                    funder_category=str(g.get("funder_category") or ""),
                )
                if converted is not None:
                    grant_models.append(converted)

        serialized_grants = [
            g.model_dump() if hasattr(g, "model_dump") else dict(g)
            for g in (grant_models or all_grants)
        ]

        json_path = self.output_dir / "all_grants.json"
        try:
            json_path.write_text(
                json.dumps(serialized_grants, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            logger.info(f"EN: Exported JSON snapshot / DE: JSON-Snapshot exportiert: {json_path}")
        except Exception as exc:
            logger.error(f"Failed to write JSON snapshot: {exc}")

        catalog_path = self.output_dir / "all_grants_catalog.html"
        if widget_builder is not None:
            harvest_result_obj = self._build_harvest_result_model(grant_models, total_sources)
            render_fn = getattr(widget_builder, "render_all_grants_catalog", None)
            if callable(render_fn):
                try:
                    r_res = render_fn(harvest_result_obj, str(catalog_path))
                    if inspect.isawaitable(r_res):
                        await r_res
                except TypeError:
                    r_res = render_fn(harvest_result_obj, catalog_path)
                    if inspect.isawaitable(r_res):
                        await r_res
                logger.info(f"EN: Built interactive web catalog / DE: Interaktiver Web-Katalog erstellt: {catalog_path}")
            else:
                for builder_name in ("build_catalog", "generate_catalog", "build_html_catalog"):
                    b_fn = getattr(widget_builder, builder_name, None)
                    if callable(b_fn):
                        b_res = b_fn(serialized_grants)
                        if inspect.isawaitable(b_res):
                            await b_res
                        break

        return len(serialized_grants)

    @staticmethod
    def _build_harvest_result_model(grants: List[GrantItem], total_sources: int) -> Any:
        result_cls = getattr(schemas, "MultiSourceHarvestResult", None)
        if result_cls is None:
            return {"grants": grants, "total_grants": len(grants), "active_sources": total_sources}

        now_iso = datetime.now(timezone.utc).isoformat()
        unique_portals = sorted(
            {
                str(getattr(g, "source_portal", None) or getattr(g, "funder", "Unknown"))
                for g in grants
            }
        )
        effective_source_count = total_sources if total_sources > 0 else len(unique_portals)

        model_fields = getattr(result_cls, "model_fields", None)
        active_sources_val: Any = effective_source_count
        if isinstance(model_fields, dict) and "active_sources" in model_fields:
            ann_str = str(getattr(model_fields["active_sources"], "annotation", ""))
            if any(seq_tok in ann_str.lower() for seq_tok in ("list", "set", "sequence", "tuple")):
                active_sources_val = unique_portals

        candidate_fields: Dict[str, Any] = {
            "grants": grants,
            "items": grants,
            "results": grants,
            "total_grants": len(grants),
            "total_programs": len(grants),
            "active_grants": len(grants),
            "active_sources": active_sources_val,
            "total_sources": effective_source_count,
            "sources_count": effective_source_count,
            "sources_processed": effective_source_count,
            "new_grants_count": sum(1 for g in grants if getattr(g, "is_newly_discovered", False)),
            "harvest_timestamp": now_iso,
            "timestamp": now_iso,
            "generated_at": now_iso,
        }

        if isinstance(model_fields, dict):
            payload = {k: v for k, v in candidate_fields.items() if k in model_fields}
        else:
            payload = candidate_fields

        return result_cls(**payload)

    # --------------------------------------------------------------------------
    # Directed Graph Crawl & Supervisory Loop / Gerichteter Graph-Crawl & Supervisor
    # --------------------------------------------------------------------------

    async def _crawl_and_harvest_source(
        self,
        source_name: str,
        seed_url: str,
        funder_category: str,
        http_client: httpx.AsyncClient,
    ) -> int:
        logger.info(
            f"==> EN: Starting crawl / DE: Starte Crawl: {source_name} "
            f"(Depth / Tiefe: {self.max_crawl_depth}, Pages / Seiten: {self.max_pages_per_source})"
        )

        skill_name = self._slugify_skill_name(source_name)
        seed_domain = urlparse(seed_url).netloc.lower()

        queue: deque[Tuple[str, int]] = deque([(seed_url, 1)])
        visited: Set[str] = set()
        pages_crawled = 0
        source_unique_items: Dict[str, GrantItem] = {}
        reflection_attempts_used = 0

        while queue and pages_crawled < self.max_pages_per_source:
            current_url, depth = queue.popleft()
            norm_url = current_url.split("#")[0].rstrip("/")
            if norm_url in visited or depth > self.max_crawl_depth:
                continue
            visited.add(norm_url)

            html = await self._fetch_page_html(current_url, http_client)
            if not html:
                continue
            pages_crawled += 1

            skill_module = self._load_skill_module(skill_name)
            if skill_module is None and reflection_attempts_used < self.max_reflection_attempts:
                reflection_attempts_used += 1
                logger.info(
                    f"[SYSTEM 2 ARCHITECT] Synthesizing initial procedural skill '{skill_name}' for {source_name}..."
                )
                synthesized = await self._synthesize_or_refactor_skill(
                    skill_name=skill_name,
                    source_name=source_name,
                    url=current_url,
                    html=html,
                    current_code=None,
                    diagnostic_report="Initial skill synthesis required for unmapped funding portal.",
                )
                if synthesized:
                    skill_module = self._load_skill_module(skill_name, force_reload=True)

            if skill_module is None:
                logger.warning(f"[SYSTEM 2] Unable to synthesize valid skill for {source_name}. Quarantining.")
                if self.tracker is not None and hasattr(self.tracker, "record_failure"):
                    self.tracker.record_failure(source_name, seed_url, "Skill synthesis failed")
                break

            telemetry = self._execute_system1_with_telemetry(
                skill_module=skill_module,
                skill_name=skill_name,
                url=current_url,
                html=html,
            )

            should_refactor = telemetry.is_degraded or (
                depth == 1 and telemetry.total_raw_candidates == 0
            )

            if should_refactor and reflection_attempts_used < self.max_reflection_attempts:
                reflection_attempts_used += 1
                diagnostic = telemetry.to_diagnostic_prompt()
                logger.warning(
                    f"[SYSTEM 2 SUPERVISOR] Skill '{skill_name}' degraded on {current_url} "
                    f"(Corruption: {telemetry.corruption_ratio:.1%}, "
                    f"Valid: {telemetry.valid_count}/{telemetry.total_raw_candidates}). "
                    f"Initiating PyCognition skill refactoring (Attempt {reflection_attempts_used}/{self.max_reflection_attempts})..."
                )

                current_code = self._read_skill_source(skill_name)
                refactored = await self._synthesize_or_refactor_skill(
                    skill_name=skill_name,
                    source_name=source_name,
                    url=current_url,
                    html=html,
                    current_code=current_code,
                    diagnostic_report=diagnostic,
                    baseline_valid_count=telemetry.valid_count,
                )
                if refactored:
                    skill_module = self._load_skill_module(skill_name, force_reload=True)
                    if skill_module is not None:
                        telemetry = self._execute_system1_with_telemetry(
                            skill_module=skill_module,
                            skill_name=skill_name,
                            url=current_url,
                            html=html,
                        )
                        logger.info(
                            f"[SYSTEM 2 SUPERVISOR] Post-refactor telemetry for '{skill_name}': "
                            f"Valid={telemetry.valid_count}/{telemetry.total_raw_candidates} "
                            f"(Corruption: {telemetry.corruption_ratio:.1%})."
                        )

            logger.info(
                f"[SYSTEM 1] (Depth / Tiefe {depth}) Skill {skill_name} "
                f"extracted / extrahierte {telemetry.valid_count} programs."
            )

            for raw_item in telemetry.valid_records:
                grant_obj = self._to_grant_item(raw_item, source_name, current_url, funder_category)
                if grant_obj is not None:
                    fp = self._compute_fingerprint(grant_obj)
                    source_unique_items[fp] = grant_obj

            if depth < self.max_crawl_depth:
                next_links = self._extract_internal_links(html, current_url, seed_domain)
                for link in next_links:
                    if link.split("#")[0].rstrip("/") not in visited:
                        queue.append((link, depth + 1))

        if source_unique_items:
            self._persist_grants_batch(list(source_unique_items.values()))

        logger.info(
            f"EN: Summary for {source_name}: {pages_crawled} pages, {len(source_unique_items)} programs / "
            f"DE: Fazit für {source_name}: {pages_crawled} Seiten, {len(source_unique_items)} Programme."
        )
        return len(source_unique_items)

    # --------------------------------------------------------------------------
    # System 1 Execution & PyCognition Telemetry / System-1-Ausführung
    # --------------------------------------------------------------------------

    def _execute_system1_with_telemetry(
        self,
        skill_module: Any,
        skill_name: str,
        url: str,
        html: str,
    ) -> SkillExecutionTelemetry:
        extract_fn = getattr(skill_module, "extract", None)
        if not callable(extract_fn):
            return self.telemetry_evaluator.evaluate(
                skill_name=skill_name,
                target_uri=url,
                raw_output=None,
                execution_error="Missing callable 'extract(html, base_url)' in skill module.",
            )

        try:
            sig = inspect.signature(extract_fn)
            if len(sig.parameters) >= 2:
                raw_results = extract_fn(html, url)
            else:
                raw_results = extract_fn(html)
            return self.telemetry_evaluator.evaluate(
                skill_name=skill_name,
                target_uri=url,
                raw_output=raw_results,
                execution_error=None,
            )
        except Exception as exc:
            return self.telemetry_evaluator.evaluate(
                skill_name=skill_name,
                target_uri=url,
                raw_output=None,
                execution_error=f"{type(exc).__name__}: {exc}",
            )

    @classmethod
    def _validate_domain_record(cls, record: Dict[str, Any]) -> bool:
        title = re.sub(r"\s+", " ", str(record.get("title") or "")).strip()
        if len(title) < 5 or len(title) > 260:
            return False
        if len(re.findall(r"[A-Za-zÄÖÜäöüß]", title)) < 3:
            return False
        lowered = title.lower()
        return not any(pat in lowered for pat in cls.CORRUPT_TITLE_PATTERNS)

    # --------------------------------------------------------------------------
    # System 2 Architectural Reflection & PyCognition Crystallization
    # --------------------------------------------------------------------------

    async def _synthesize_or_refactor_skill(
        self,
        skill_name: str,
        source_name: str,
        url: str,
        html: str,
        current_code: Optional[str],
        diagnostic_report: str,
        baseline_valid_count: int = 0,
    ) -> bool:
        distilled_dom = self._distill_html_for_llm(html, max_chars=24000)

        structural_hints = await self._call_llm(
            model=self.fast_model,
            system_prompt=(
                "You are a senior DOM structural analyst. Identify the exact HTML container tags, "
                "CSS classes, and link patterns that represent genuine academic funding programs, "
                "grants, fellowships, or calls for proposals. Ignore navigation bars, cookie banners, "
                "social icons, and empty anchor tags."
            ),
            user_prompt=(
                f"Source: {source_name}\nURL: {url}\n\n"
                f"Identify the repeating DOM structure for funding calls in this HTML snippet:\n"
                f"```html\n{distilled_dom[:14000]}\n```"
            ),
        )

        mode_label = "REFACTOR DEGRADED SKILL" if current_code else "SYNTHESIZE NEW SKILL"
        existing_block = (
            f"CURRENT DEFECTIVE CODE:\n```python\n{current_code}\n```\n\n"
            if current_code
            else ""
        )

        synthesized_raw = await self._call_llm(
            model=self.reasoner_model,
            system_prompt=(
                "You are the System 2 Cognitive Architect of PyCognition. Your task is to write a clean, "
                "deterministic Python extraction module using BeautifulSoup (`from bs4 import BeautifulSoup`) "
                "and `urllib.parse.urljoin`.\n"
                "STRICT CONSTRAINTS:\n"
                "1. Define `def extract(html: str, base_url: str) -> list[dict]:`.\n"
                "2. Allowed imports ONLY: `bs4`, `re`, `json`, `typing`, `datetime`, `urllib.parse`, `html`.\n"
                "3. NEVER import `os`, `sys`, `subprocess`, `requests`, `httpx`, or `pathlib`.\n"
                "4. Filter out empty containers INSIDE `extract()`: skip any card where the cleaned title "
                "has fewer than 5 characters or lacks real words.\n"
                "5. Each returned dict must contain keys: `title` (str), `link` (str, resolved via urljoin), "
                "`deadline` (str or ''), `description` (str or ''), `funder` (str).\n"
                "6. Output ONLY valid Python code inside a ```python ... ``` block."
            ),
            user_prompt=(
                f"TASK: {mode_label}\n"
                f"Source Name: {source_name}\n"
                f"URL: {url}\n\n"
                f"DIAGNOSTIC TELEMETRY:\n{diagnostic_report}\n\n"
                f"{existing_block}"
                f"TIER-1 STRUCTURAL ANALYSIS:\n{structural_hints}\n\n"
                f"TARGET PAGE DOM:\n```html\n{distilled_dom}\n```"
            ),
        )

        candidate_code = self._extract_python_code_block(synthesized_raw)
        if not candidate_code:
            logger.warning(f"[SYSTEM 2] Failed to extract Python code block for '{skill_name}'.")
            return False

        # Delegate AST capability audit, sandbox execution, regression guard & disk persistence
        # directly to PyCognition v1.2.0 SkillCrystallizer
        capability = SkillCapability(
            skill_name=skill_name,
            allowed_scope=ExecutionScope.PARSE_DATA,
            allowed_modules=set(self.ALLOWED_SKILL_MODULES),
            required_entrypoint="extract",
        )

        cryst_result = self.crystallizer.crystallize(
            source_code=candidate_code,
            capability=capability,
            sample_args=(html, url),
            target_uri=url,
            baseline_valid_count=baseline_valid_count,
            max_allowed_corruption=0.20,
            source_label=source_name,
        )

        if not cryst_result.accepted:
            logger.warning(
                f"[PYCOGNITION CRYSTALLIZER] Rejected skill '{skill_name}': {cryst_result.reason}"
            )
            return False

        logger.info(
            f"[PYCOGNITION CRYSTALLIZER] Persisted verified skill: {Path(cryst_result.persisted_path or '').name}"
        )
        return True

    # --------------------------------------------------------------------------
    # LLM Client & DOM Distillation / LLM-Client & DOM-Destillation
    # --------------------------------------------------------------------------

    async def _call_llm(self, model: str, system_prompt: str, user_prompt: str) -> str:
        if not self.deepseek_api_key:
            logger.error("DEEPSEEK_API_KEY is missing; System 2 reflection cannot execute.")
            return ""

        endpoint = f"{self.deepseek_base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if "reasoner" not in model.lower() and "r1" not in model.lower():
            payload["temperature"] = 0.1

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=15.0)) as client:
                resp = await client.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {self.deepseek_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"] or ""
        except Exception as exc:
            logger.error(f"[SYSTEM 2 LLM ERROR] Model={model}: {exc}")
            return ""

    @staticmethod
    def _distill_html_for_llm(html: str, max_chars: int = 24000) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "svg", "noscript", "iframe", "meta", "link"]):
            tag.decompose()
        main_node = soup.find("main") or soup.find("body") or soup
        cleaned = re.sub(r"\n\s*\n+", "\n", str(main_node))
        return cleaned[:max_chars]

    @staticmethod
    def _extract_python_code_block(llm_text: str) -> str:
        match = re.search(r"```python\s*(.*?)```", llm_text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        match_generic = re.search(r"```\s*(.*?)```", llm_text, re.DOTALL)
        if match_generic:
            return match_generic.group(1).strip()
        return ""

    # --------------------------------------------------------------------------
    # Network Fetching & Link Graph Traversal / Netzwerkabruf & Link-Graph
    # --------------------------------------------------------------------------

    async def _fetch_page_html(self, url: str, http_client: httpx.AsyncClient) -> str:
        use_browser = any(hint in url.lower() for hint in self.SPA_DOMAIN_HINTS)

        if not use_browser:
            try:
                resp = await http_client.get(url)
                if resp.status_code == 200 and len(resp.text) > 800:
                    return resp.text
                use_browser = True
            except Exception:
                use_browser = True

        if use_browser:
            return await self._fetch_via_stealth_browser(url)
        return ""

    async def _fetch_via_stealth_browser(self, url: str) -> str:
        if self.browser is None:
            self.browser = _BrowserCls()
            if hasattr(self.browser, "__aenter__") and not self._browser_entered:
                await self.browser.__aenter__()
                self._browser_entered = True
            else:
                for init_name in ("initialize", "start", "launch"):
                    init_fn = getattr(self.browser, init_name, None)
                    if callable(init_fn):
                        res = init_fn()
                        if inspect.isawaitable(res):
                            await res
                        break

        for fetch_name in ("fetch_page_html", "fetch_html", "fetch_page", "get_page_html", "fetch"):
            fetch_fn = getattr(self.browser, fetch_name, None)
            if callable(fetch_fn):
                try:
                    res = fetch_fn(url)
                    if inspect.isawaitable(res):
                        res = await res
                    if isinstance(res, tuple):
                        return str(res[0] or "")
                    return str(res or "")
                except Exception as exc:
                    logger.warning(f"[StealthBrowser] Fetch failed for {url}: {exc}")
                    return ""
        return ""

    async def _close_browser(self) -> None:
        if self.browser is not None:
            try:
                if self._browser_entered and hasattr(self.browser, "__aexit__"):
                    await self.browser.__aexit__(None, None, None)
                else:
                    for close_name in ("close", "shutdown", "stop"):
                        close_fn = getattr(self.browser, close_name, None)
                        if callable(close_fn):
                            res = close_fn()
                            if inspect.isawaitable(res):
                                await res
                            break
            finally:
                self.browser = None
                self._browser_entered = False

    @staticmethod
    def _extract_internal_links(html: str, base_url: str, allowed_domain: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: List[str] = []
        seen: Set[str] = set()

        skip_extensions = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".zip", ".doc", ".docx", ".xlsx", ".mp4")
        skip_tokens = ("{{", "}}", "%7b%7b", "%7d%7d", "javascript:", "mailto:", "tel:")

        for anchor in soup.find_all("a", href=True):
            raw_href = str(anchor["href"]).strip()
            if not raw_href or raw_href.startswith("#"):
                continue
            if any(tok in raw_href.lower() for tok in skip_tokens):
                continue

            full_url = urljoin(base_url, raw_href).split("#")[0]
            parsed = urlparse(full_url)
            if parsed.scheme not in ("http", "https"):
                continue
            if parsed.netloc.lower() != allowed_domain:
                continue
            if parsed.path.lower().endswith(skip_extensions):
                continue

            if full_url not in seen:
                seen.add(full_url)
                links.append(full_url)

        return links[:25]

    # --------------------------------------------------------------------------
    # Skill Module Loading & Schema Normalization / Skill-Laden & Normalisierung
    # --------------------------------------------------------------------------

    @staticmethod
    def _slugify_skill_name(source_name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", source_name.lower()).strip("_")
        return f"harvest_{slug[:55]}"

    def _read_skill_source(self, skill_name: str) -> Optional[str]:
        skill_path = self.skills_dir / f"{skill_name}.py"
        if skill_path.exists():
            return skill_path.read_text(encoding="utf-8")
        return None

    def _load_skill_module(self, skill_name: str, force_reload: bool = False) -> Optional[Any]:
        if not force_reload and skill_name in self._loaded_skills:
            return self._loaded_skills[skill_name]

        skill_path = self.skills_dir / f"{skill_name}.py"
        if not skill_path.exists():
            return None

        try:
            spec = importlib.util.spec_from_file_location(skill_name, str(skill_path))
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            sys.modules[skill_name] = module
            spec.loader.exec_module(module)
            self._loaded_skills[skill_name] = module
            return module
        except Exception as exc:
            logger.error(f"Failed to load skill module '{skill_name}': {exc}")
            return None

    @classmethod
    def _normalize_funder_category(cls, raw_category: str, source_name: str) -> str:
        if raw_category in cls.VALID_FUNDER_CATEGORIES:
            return raw_category

        combined = f"{raw_category} {source_name}".lower()
        if "dfg" in combined or "deutsche forschungsgemeinschaft" in combined:
            return "DFG"
        if "bmbf" in combined or "bmftr" in combined or "bund" in combined:
            return "BMBF / Bund"
        if any(k in combined for k in ("eu ", "european", "horizon", "erc", "europa")):
            return "EU Funding / EU-Förderung"
        if any(k in combined for k in ("stipend", "scholarship", "studienförderung", "cusanus", "boell", "böll", "boeckler", "böckler")):
            return "Scholarships / Stipendien"
        if any(k in combined for k in ("stiftung", "foundation", "fonds", "thyssen", "henkel", "volkswagen", "humboldt")):
            return "Foundations / Stiftungen"
        return "Discovered Sources / Neu entdeckte Quellen"

    def _to_grant_item(
        self,
        raw: Dict[str, Any],
        source_name: str,
        page_url: str,
        funder_category: str = "",
    ) -> Optional[GrantItem]:
        if not self._validate_domain_record(raw):
            return None

        title = re.sub(r"\s+", " ", str(raw.get("title") or "")).strip()
        raw_link = str(raw.get("link") or raw.get("url") or page_url).strip()
        if not raw_link.startswith(("http://", "https://")):
            raw_link = urljoin(page_url, raw_link)

        funder = str(raw.get("funder") or source_name).strip()
        deadline = str(raw.get("deadline") or "").strip() or "Rolling / Laufend"
        description = str(raw.get("description") or "").strip() or title
        target_group = str(raw.get("target_group") or "Researchers / Wissenschaftler").strip()
        funding_amount = str(raw.get("funding_amount") or "See Call / Laut Ausschreibung").strip()
        normalized_cat = self._normalize_funder_category(
            str(raw.get("funder_category") or funder_category),
            source_name,
        )

        candidate_payload: Dict[str, Any] = {
            "title": title,
            "funder": funder,
            "funder_category": normalized_cat,
            "target_group": target_group,
            "deadline": deadline,
            "funding_amount": funding_amount,
            "link": raw_link,
            "url": raw_link,
            "description": description,
            "source_portal": source_name,
            "source": source_name,
        }

        model_fields = getattr(GrantItem, "model_fields", None)
        if isinstance(model_fields, dict):
            filtered_payload = {k: v for k, v in candidate_payload.items() if k in model_fields}
        else:
            filtered_payload = candidate_payload

        try:
            return GrantItem(**filtered_payload)
        except Exception as exc:
            if not self._schema_error_logged:
                logger.error(f"[SCHEMA MISMATCH] GrantItem validation error: {exc}")
                self._schema_error_logged = True
            return None

    @staticmethod
    def _compute_fingerprint(item: GrantItem) -> str:
        item_link = str(getattr(item, "link", None) or getattr(item, "url", "")).lower().strip()
        raw_sig = f"{item.title.lower().strip()}|{item_link}"
        return hashlib.sha256(raw_sig.encode("utf-8")).hexdigest()

    def _persist_grants_batch(self, items: List[GrantItem]) -> None:
        for batch_method in ("upsert_grants", "save_grants", "add_grants"):
            fn = getattr(self.storage, batch_method, None)
            if callable(fn):
                fn(items)
                return

        for single_method in ("upsert_grant", "save_grant", "add_grant", "insert_grant"):
            fn = getattr(self.storage, single_method, None)
            if callable(fn):
                for item in items:
                    try:
                        fn(item)
                    except TypeError:
                        fn(item.model_dump())
                return


# Compatibility aliases / Kompatibilitäts-Aliase
AutonomousGrantHarvester = AutonomousSelfHealingHarvester
MultiPortalGrantHarvester = AutonomousSelfHealingHarvester