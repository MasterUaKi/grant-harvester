# File: storage.py
# Version: 1.0.0 | Release Date: 2026-11-10
"""
EN: SQLite persistence engine and grant lifecycle management.
DE: SQLite-Persistenz-Engine und Lebenszyklusverwaltung für Förderungen.
"""

from datetime import datetime, timedelta
import hashlib
import logging
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from schemas import FunderCategory, GrantItem

logger = logging.getLogger("GrantStorage")


class GrantStorage:
    """
    EN: Manages SQLite database operations, grant deduplication, and lifecycle tracking.
    DE: Verwaltet SQLite-Datenbankoperationen, Förderungs-Deduplizierung und Lebenszyklusverfolgung.
    """

    def __init__(self, db_path: Path | str = "./output/grants_vault.db"):
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """
        EN: Returns a configured SQLite connection with foreign keys enabled.
        DE: Gibt eine konfigurierte SQLite-Verbindung mit aktivierten Fremdschlüsseln zurück.
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        """
        EN: Creates relational tables and search indexes if they do not exist.
        DE: Erstellt relationale Tabellen und Suchindizes, sofern diese nicht existieren.
        """
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS grants (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    funder TEXT NOT NULL,
                    funder_category TEXT NOT NULL,
                    target_group TEXT NOT NULL,
                    deadline TEXT NOT NULL,
                    funding_amount TEXT,
                    link TEXT NOT NULL,
                    description TEXT,
                    source_portal TEXT NOT NULL,
                    is_newly_discovered INTEGER DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_grants_status ON grants(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_grants_funder ON grants(funder);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_grants_deadline ON grants(deadline);")
            conn.commit()
        logger.info(
            f"EN: Database initialized at / DE: Datenbank initialisiert unter: {self.db_path}"
        )

    @staticmethod
    def _generate_grant_id(title: str, link: str, funder: str) -> str:
        """
        EN: Generates deterministic SHA-256 fingerprint for a grant entity.
        DE: Erzeugt einen deterministischen SHA-256-Fingerprint für eine Förderungsentität.
        """
        clean_key = f"{title.strip().lower()}|{link.strip()}|{funder.strip().lower()}"
        return hashlib.sha256(clean_key.encode("utf-8")).hexdigest()

    def upsert_grants(self, grants: List[GrantItem]) -> Tuple[int, int]:
        """
        EN: Inserts new grants or updates last_seen timestamp for existing records.
        DE: Fügt neue Förderungen ein oder aktualisiert den Zeitstempel für bestehende Einträge.
        """
        if not grants:
            return 0, 0

        now_iso = datetime.now().isoformat()
        new_count = 0
        updated_count = 0

        with self._get_connection() as conn:
            cursor = conn.cursor()
            for g in grants:
                grant_id = self._generate_grant_id(g.title, g.link, g.funder)

                cursor.execute("SELECT id FROM grants WHERE id = ?", (grant_id,))
                existing = cursor.fetchone()

                if existing:
                    cursor.execute("""
                        UPDATE grants
                        SET last_seen = ?,
                            status = 'ACTIVE',
                            deadline = ?,
                            funding_amount = ?,
                            description = ?
                        WHERE id = ?
                    """, (now_iso, g.deadline, g.funding_amount, g.description, grant_id))
                    updated_count += 1
                else:
                    cursor.execute("""
                        INSERT INTO grants (
                            id, title, funder, funder_category, target_group,
                            deadline, funding_amount, link, description,
                            source_portal, is_newly_discovered, status,
                            first_seen, last_seen
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                    """, (
                        grant_id,
                        g.title,
                        g.funder,
                        g.funder_category.value,
                        g.target_group,
                        g.deadline,
                        g.funding_amount,
                        g.link,
                        g.description,
                        g.source_portal,
                        1 if g.is_newly_discovered else 0,
                        now_iso,
                        now_iso
                    ))
                    new_count += 1

            conn.commit()

        logger.info(
            f"EN: Database sync complete: {new_count} new, {updated_count} confirmed / "
            f"DE: Datenbank-Sync abgeschlossen: {new_count} neu, {updated_count} bestätigt."
        )
        return new_count, updated_count

    def update_lifecycle_statuses(self, archive_threshold_days: int = 45) -> Tuple[int, int]:
        """
        EN: Marks unseen records as EXPIRED or ARCHIVED based on last observation date.
        DE: Markiert nicht mehr gesehene Einträge als EXPIRED oder ARCHIVED basierend auf dem Datum.
        """
        threshold_date = (datetime.now() - timedelta(days=archive_threshold_days)).isoformat()
        expired_count = 0
        archived_count = 0

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE grants
                SET status = 'ARCHIVED'
                WHERE status = 'ACTIVE' AND last_seen < ?
            """, (threshold_date,))
            archived_count = cursor.rowcount
            conn.commit()

        return expired_count, archived_count

    def get_active_grants(self) -> List[GrantItem]:
        """
        EN: Retrieves all currently active grants from the database.
        DE: Ruft alle derzeit aktiven Förderungen aus der Datenbank ab.
        """
        results: List[GrantItem] = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT title, funder, funder_category, target_group,
                       deadline, funding_amount, link, description,
                       source_portal, is_newly_discovered
                FROM grants
                WHERE status = 'ACTIVE'
                ORDER BY funder ASC, title ASC
            """)
            for row in cursor.fetchall():
                cat_val = row["funder_category"]
                category = FunderCategory.OTHER
                for c in FunderCategory:
                    if c.value == cat_val or c.name == cat_val:
                        category = c
                        break

                results.append(GrantItem(
                    title=row["title"],
                    funder=row["funder"],
                    funder_category=category,
                    target_group=row["target_group"],
                    deadline=row["deadline"],
                    funding_amount=row["funding_amount"],
                    link=row["link"],
                    description=row["description"],
                    source_portal=row["source_portal"],
                    is_newly_discovered=bool(row["is_newly_discovered"])
                ))
        return results

    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        EN: Computes global metrics across all stored grant records.
        DE: Berechnet globale Metriken über alle gespeicherten Förderungsdatensätze.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM grants;")
            total_records = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM grants WHERE status = 'ACTIVE';")
            active_grants = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT funder) FROM grants WHERE status = 'ACTIVE';")
            unique_active_funders = cursor.fetchone()[0]

        return {
            "total_records": total_records,
            "active_grants": active_grants,
            "unique_active_funders": unique_active_funders
        }