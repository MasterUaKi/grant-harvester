# File: schemas.py
# Version: 1.0.0 | Release Date: 2026-11-10
"""
EN: Pydantic schemas and data models for academic funding programs and harvest cycles.
DE: Pydantic-Schemata und Datenmodelle für akademische Förderprogramme und Erfassungszyklen.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class FunderCategory(str, Enum):
    """
    EN: Categorization of research funding organizations.
    DE: Kategorisierung von Forschungsförderungsorganisationen.
    """
    DFG = "DFG"
    BMBF_BUND = "BMBF / Bund"
    EU_FUNDING = "EU Funding / EU-Förderung"
    FOUNDATION = "Foundations / Stiftungen"
    STUDENT_SCHOLARSHIP = "Scholarships / Stipendien"
    DISCOVERY = "Discovered Sources / Neu entdeckte Quellen"
    OTHER = "Other / Sonstige"


class GrantItem(BaseModel):
    """
    EN: Standardized entity representing an academic grant or fellowship program.
    DE: Standardisierte Entität für ein akademisches Förder- oder Stipendienprogramm.
    """
    title: str = Field(
        ...,
        description="EN: Official title of the funding program. / DE: Offizieller Titel des Förderprogramms."
    )
    funder: str = Field(
        ...,
        description="EN: Name of the granting organization. / DE: Name der Förderorganisation."
    )
    funder_category: FunderCategory = Field(
        default=FunderCategory.OTHER,
        description="EN: Category of the funding institution. / DE: Kategorie der Fördereinrichtung."
    )
    target_group: str = Field(
        default="Researchers / Wissenschaftler",
        description="EN: Target academic group (e.g., Postdocs, PhD). / DE: Zielgruppe (z. B. Postdocs, Promotion)."
    )
    deadline: str = Field(
        default="ongoing / laufend",
        description="EN: Application deadline or submission notice. / DE: Bewerbungsfrist oder Einreichungshinweis."
    )
    funding_amount: Optional[str] = Field(
        default=None,
        description="EN: Financial volume or fellowship rate. / DE: Fördervolumen oder Stipendienrate."
    )
    link: str = Field(
        ...,
        description="EN: Absolute URL to the official announcement. / DE: Absolute URL zur offiziellen Ausschreibung."
    )
    description: str = Field(
        default="",
        description="EN: Short summary of eligibility and funding scope. / DE: Kurzbeschreibung der Kriterien und Förderschwerpunkte."
    )
    source_portal: str = Field(
        ...,
        description="EN: Originating portal name. / DE: Name des Ausgangsportals."
    )
    is_newly_discovered: bool = Field(
        default=False,
        description="EN: Flag indicating discovery in the active cycle. / DE: Kennzeichen für Neuentdeckung im aktuellen Zyklus."
    )


class MultiSourceHarvestResult(BaseModel):
    """
    EN: Aggregated payload containing results of an entire harvest cycle.
    DE: Aggregiertes Datenpaket mit den Ergebnissen eines vollständigen Erfassungszyklus.
    """
    harvested_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="EN: ISO timestamp of cycle completion. / DE: ISO-Zeitstempel des Zyklusabschlusses."
    )
    total_grants: int = Field(
        ...,
        description="EN: Total number of active verified grants. / DE: Gesamtzahl aktiver verifizierter Förderprogramme."
    )
    active_sources: int = Field(
        ...,
        description="EN: Count of distinct contributing funding sources. / DE: Anzahl beitragender Förderquellen."
    )
    new_grantors_found: int = Field(
        default=0,
        description="EN: Count of newly identified programs/grantors. / DE: Anzahl neu identifizierter Programme/Förderer."
    )
    grants: List[GrantItem] = Field(
        default_factory=list,
        description="EN: List of collected funding programs. / DE: Liste der erfassten Förderprogramme."
    )