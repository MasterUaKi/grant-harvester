# File: unprocessed_tracker.py
# Version: 1.1.0 | Release Date: 2026-11-10
"""
EN: Quarantine tracker for stubborn or unparseable academic portals.
DE: Quarantäne-Tracker für schwer zugängliche oder unvollständig parsbare Förderportale.
"""

from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("UnprocessedTracker")


class UnprocessedTracker:
    """
    EN: Manages the quarantine registry of funding sources requiring secondary triage.
    DE: Verwaltet das Quarantäne-Register von Förderquellen, die eine sekundäre Triage erfordern.
    """

    def __init__(self, registry_path: Path | str = "./unprocessed_sources.json"):
        self.registry_path = Path(registry_path).resolve()
        self.items: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        """
        EN: Loads quarantine records from disk.
        DE: Lädt Quarantäneeinträge von der Festplatte.
        """
        if not self.registry_path.exists():
            self.items = {}
            return

        try:
            content = self.registry_path.read_text(encoding="utf-8").strip()
            if not content:
                self.items = {}
                return

            raw_list = json.loads(content)
            if isinstance(raw_list, list):
                self.items = {item["source_name"]: item for item in raw_list if "source_name" in item}
            elif isinstance(raw_list, dict):
                self.items = raw_list
        except Exception as err:
            logger.error(
                f"Error loading quarantine registry / Fehler beim Laden des Quarantäne-Registers "
                f"{self.registry_path}: {err}"
            )
            self.items = {}

    def save(self) -> None:
        """
        EN: Atomically saves quarantine entries formatted as JSON.
        DE: Speichert Quarantäneeinträge atomar als formatierte JSON-Datei.
        """
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            export_list = list(self.items.values())
            self.registry_path.write_text(
                json.dumps(export_list, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as err:
            logger.error(
                f"Failed writing quarantine file / Fehler beim Schreiben der Quarantänedatei "
                f"{self.registry_path}: {err}"
            )

    def record_unprocessed(
        self,
        source_name: str,
        url: str,
        failure_type: str,
        details: str,
        html_sample: Optional[str] = None,
        suggested_strategy: Optional[str] = None
    ) -> None:
        """
        EN: Registers or updates an unharvested source in the quarantine pool.
        DE: Registriert oder aktualisiert eine nicht erfasste Förderquelle im Quarantäne-Pool.
        """
        now_iso = datetime.now().isoformat()

        if source_name in self.items:
            record = self.items[source_name]
            record["attempts"] = record.get("attempts", 1) + 1
            record["last_failed_at"] = now_iso
            record["last_error"] = details[:1000]
            record["failure_type"] = failure_type
            if suggested_strategy:
                record["suggested_strategy"] = suggested_strategy
            if html_sample and len(html_sample) > 50:
                record["dom_sample"] = html_sample[:4000]
        else:
            self.items[source_name] = {
                "source_name": source_name,
                "url": url,
                "status": "PENDING_TRIAGE",  # PENDING_TRIAGE | IN_TRIAGE | RESOLVED | ABANDONED
                "failure_type": failure_type,
                "attempts": 1,
                "first_failed_at": now_iso,
                "last_failed_at": now_iso,
                "last_error": details[:1000],
                "suggested_strategy": suggested_strategy or "DEEP_FORM_OR_NETWORK_ANALYSIS",
                "dom_sample": (html_sample[:4000] if html_sample else "")
            }

        self.save()
        logger.warning(
            f"[Quarantine / Quarantäne] Source recorded for triage / Quelle für Triage erfasst: "
            f"'{source_name}' ({failure_type})"
        )

    def get_pending_items(self) -> List[Dict[str, Any]]:
        """
        EN: Returns list of items awaiting resolution.
        DE: Gibt die Liste der noch zu lösenden Einträge zurück.
        """
        return [
            item for item in self.items.values()
            if item.get("status") in ("PENDING_TRIAGE", "IN_TRIAGE")
        ]

    def mark_resolved(self, source_name: str, resolved_url: str, skill_name: str) -> None:
        """
        EN: Marks an issue as successfully resolved after triage synthesis.
        DE: Markiert ein Problem nach erfolgreicher Triage-Synthese als behoben.
        """
        if source_name in self.items:
            self.items[source_name]["status"] = "RESOLVED"
            self.items[source_name]["resolved_at"] = datetime.now().isoformat()
            self.items[source_name]["resolved_url"] = resolved_url
            self.items[source_name]["crystallized_skill"] = skill_name
            self.save()
            logger.info(
                f"[Quarantine / Quarantäne] Successfully resolved / Erfolgreich behoben: '{source_name}'"
            )

    def should_skip(self, source_name: str, max_tolerated_failures: int = 2) -> bool:
        """
        EN: Determines if the main harvester should bypass this portal during regular cycles.
        DE: Prüft, ob der Haupt-Harvester dieses Portal im regulären Zyklus überspringen soll.
        """
        if source_name not in self.items:
            return False
        item = self.items[source_name]
        return item.get("status") == "PENDING_TRIAGE" and item.get("attempts", 0) >= max_tolerated_failures