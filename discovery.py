# File: discovery.py
# Version: 1.0.0 | Release Date: 2026-11-10
"""
EN: Autonomous discovery manager for German and EU academic funding portals.
DE: Autonomer Discovery-Manager für deutsche und europäische Förderportale.
"""

import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List
import urllib.parse
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import httpx

from config import settings
from pycognition.engine.llm_deliberator import LLMDeliberator
from pycognition.schemas import Task

load_dotenv()
logger = logging.getLogger("SourceDiscovery")


class SourceDiscoveryManager:
    """
    EN: Manages the discovery, registration, and curation of academic funding websites.
    DE: Verwaltet die Entdeckung, Registrierung und Kuration akademischer Förderportale.
    """

    def __init__(self, registry_file: Path | str = settings.REGISTRY_FILE):
        self.registry_file = Path(registry_file).resolve()
        self.sources: List[Dict[str, Any]] = self.load_registry()

    def load_registry(self) -> List[Dict[str, Any]]:
        """
        EN: Loads verified sources from disk or initializes with seed baseline.
        DE: Lädt verifizierte Quellen von der Festplatte oder initialisiert mit Basis-Seeds.
        """
        if self.registry_file.exists():
            try:
                data = json.loads(self.registry_file.read_text(encoding="utf-8"))
                if isinstance(data, list) and len(data) > 0:
                    return data
            except Exception as e:
                logger.error(
                    f"EN: Failed loading registry ({e}). Rebuilding... / "
                    f"DE: Fehler beim Laden des Registers ({e}). Neuaufbau..."
                )
        return list(settings.SEED_SOURCES)

    def save_registry(self, sources: List[Dict[str, Any]]) -> None:
        """
        EN: Persists the active source catalog to disk.
        DE: Speichert den aktiven Quellenkatalog auf der Festplatte.
        """
        self.sources = sources
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        self.registry_file.write_text(
            json.dumps(sources, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    async def _query_search_engine(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        """
        EN: Executes a lightweight web search to locate research announcements.
        DE: Führt eine leichtgewichtige Websuche nach Ausschreibungen durch.
        """
        encoded_query = urllib.parse.quote_plus(query)
        search_url = f"https://www.bing.com/search?q={encoded_query}&setlang=de"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        results = []
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(search_url, headers=headers)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for li in soup.select("li.b_algo"):
                        h2 = li.find("h2")
                        a_tag = h2.find("a") if h2 else None
                        if a_tag and a_tag.get("href"):
                            raw_title = a_tag.get_text(strip=True)
                            href = a_tag["href"]
                            if (
                                href.startswith("http")
                                and not any(
                                    b in href.lower()
                                    for b in ["wikipedia.org", "youtube.com", "bing.com"]
                                )
                            ):
                                results.append({
                                    "name": raw_title[:80],
                                    "category": "Foundations / Stiftungen",
                                    "url": href,
                                    "target_group": "Researchers / Wissenschaftler"
                                })
                        if len(results) >= limit:
                            break
        except Exception as err:
            logger.debug(
                f"EN: Search request error / DE: Fehler bei Suchanfrage ({query}): {err}"
            )
        return results

    async def discover_new_sources(self, system2: LLMDeliberator | None = None) -> List[Dict[str, Any]]:
        """
        EN: Identifies novel research funding portals using LLM reasoning and web queries.
        DE: Identifiziert neuartige Förderportale mittels LLM-Reasoning und Websuche.
        """
        discovered: List[Dict[str, Any]] = list(self.sources)
        known_urls = {s["url"].rstrip("/").lower() for s in discovered}

        if system2:
            logger.info(
                "EN: [LLM Search Engine] Querying DeepSeek for German/EU research foundations... / "
                "DE: [LLM Search Engine] Frage DeepSeek nach deutschen/EU-Forschungsstiftungen ab..."
            )
            prompt = (
                "You are an academic research intelligence agent. Return a JSON list of 8 official, "
                "active funding portals for German and EU researchers (e.g., Boehringer Ingelheim Fonds, "
                "Bayer Foundation, Fritz Thyssen, VolkswagenStiftung, DFG, Horizon Europe).\n"
                "Format: Strictly JSON array of objects:\n"
                '[{"name": "...", "category": "Foundations / Stiftungen", "url": "https://...", "target_group": "..."}]'
            )
            task = Task(prompt=prompt, payload={})
            try:
                res = await system2.deliberate(task)
                text = getattr(res, "output", getattr(res, "result", "")).strip()
                clean = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
                clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", clean.strip())
                start = clean.find('[')
                end = clean.rfind(']')
                if start != -1 and end != -1:
                    llm_items = json.loads(clean[start:end+1])
                    for item in llm_items:
                        u = item.get("url", "").rstrip("/").lower()
                        if u.startswith("http") and u not in known_urls:
                            known_urls.add(u)
                            discovered.append(item)
                    logger.info(
                        f"EN: [LLM Search Engine] Added {len(llm_items)} verified sources / "
                        f"DE: [LLM Search Engine] {len(llm_items)} verifizierte Quellen hinzugefügt."
                    )
            except Exception as e:
                logger.debug(
                    f"EN: LLM discovery parsing error / DE: Fehler beim Parsen der LLM-Entdeckung: {e}"
                )

        # Web search query expansion
        for query in settings.DISCOVERY_QUERIES:
            hits = await self._query_search_engine(query, limit=2)
            for hit in hits:
                norm = hit["url"].rstrip("/").lower()
                if norm not in known_urls:
                    known_urls.add(norm)
                    discovered.append(hit)

        return discovered