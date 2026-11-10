# File: config.py
# Version: 2.9.0 | Release Date: 2026-11-10
"""
EN: Central configuration settings and seed registries for the grant harvester.
DE: Zentrale Konfigurationseinstellungen und Seed-Register für den Grant Harvester.
"""

from pathlib import Path
from typing import Any, Dict, List
from pydantic_settings import BaseSettings, SettingsConfigDict


class HarvesterSettings(BaseSettings):
    """
    EN: Strongly typed settings loaded from environment variables and .env file.
    DE: Typsichere Einstellungen, geladen aus Umgebungsvariablen und der .env-Datei.
    """

    # EN: Web search discovery queries / DE: Suchanfragen zur Ermittlung neuer Förderprogramme
    DISCOVERY_QUERIES: List[str] = [
        "Ausschreibungen Forschung Wissenschaft Foerderprogramme Deutschland 2026",
        "BMBF Bekanntmachungen Forschungsfoerderung",
        "Stipendien Begabtenfoerderungswerke Studierende Master Promotion",
        "Forschungsfoerderung Stiftungen Postdoc Deutschland Ausschreibungen",
        "Promotionsstipendien Deutschland Foerderung Graduierte",
        "Horizon Europe Calls for Proposals 2026 EU Funding",
        "European Research Council ERC Grants Starting Consolidator Advanced",
        "EU Funding & Tenders Portal Research Innovation"
    ]

    # EN: Curated baseline funding registries / DE: Kuratierte Basis-Förderportale
    SEED_SOURCES: List[Dict[str, Any]] = [
        # --- NATIONAL GERMAN RESEARCH FUNDS / NATIONALE DEUTSCHE FORSCHUNGSFÖRDERER ---
        {
            "name": "DFG - Information für die Wissenschaft",
            "category": "DFG",
            "url": "https://www.dfg.de/de/aktuelles/neuigkeiten-themen/info-wissenschaft",
            "target_group": "Researchers of all disciplines / Forscher*innen aller Disziplinen"
        },
        {
            "name": "BMBF - Aktuelle Bekanntmachungen",
            "category": "BMBF / Bund",
            "url": "https://www.bmftr.bund.de/DE/Home/home_node.html",
            "target_group": "Universities & Research Institutes / Hochschulen und Forschungseinrichtungen"
        },

        # --- EUROPEAN UNION FUNDING / EU-FORSCHUNGSFÖRDERUNG ---
        {
            "name": "EU Funding & Tenders Portal - Horizon Europe",
            "category": "EU Funding / EU-Förderung",
            "url": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search",
            "target_group": "Consortia, Universities & SMEs / Verbünde, Universitäten und KMU"
        },
        {
            "name": "European Research Council (ERC) - Calls for Proposals",
            "category": "EU Funding / EU-Förderung",
            "url": "https://erc.europa.eu/apply-grant/calls-for-proposals",
            "target_group": "Principal Investigators & Postdocs / Spitzenforscher und Postdocs"
        },

        # --- INDEPENDENT FOUNDATIONS / UNABHÄNGIGE STIFTUNGEN ---
        {
            "name": "Alexander von Humboldt-Stiftung - Förderprogramme",
            "category": "Foundations / Stiftungen",
            "url": "https://www.humboldt-foundation.de/bewerben/foerderprogramme",
            "target_group": "International Postdocs & Fellows / Internationale Postdocs und Fellows"
        },
        {
            "name": "VolkswagenStiftung - Förderangebot",
            "category": "Foundations / Stiftungen",
            "url": "https://www.volkswagenstiftung.de/de",
            "target_group": "Early Career Researchers & Teams / Nachwuchsforscher und Projektteams"
        },
        {
            "name": "Fritz Thyssen Stiftung - Projektförderung",
            "category": "Foundations / Stiftungen",
            "url": "https://www.fritz-thyssen-stiftung.de/foerderung/foerderarten/projektfoerderung/",
            "target_group": "Humanities & Social Sciences / Geistes- und Sozialwissenschaften"
        },
        {
            "name": "Fritz Thyssen Stiftung - Stipendien & Tagungen",
            "category": "Foundations / Stiftungen",
            "url": "https://www.fritz-thyssen-stiftung.de/foerderung/foerderarten/allgemeines/",
            "target_group": "Postdocs / Promovierte Wissenschaftler"
        },
        {
            "name": "Gerda Henkel Stiftung - Förderungen",
            "category": "Foundations / Stiftungen",
            "url": "https://www.gerda-henkel-stiftung.de/foerderung",
            "target_group": "Historical Humanities & PhD / Historische Geisteswissenschaften & Promotion"
        },
        {
            "name": "Boehringer Ingelheim Fonds - Fellowships & Grants",
            "category": "Foundations / Stiftungen",
            "url": "https://bifonds.de/fellowships-grants/fellowships-grants.html",
            "target_group": "Biomedical Basic Research (PhD & MD) / Biomedizinische Grundlagenforschung"
        },

        # --- SCHOLARSHIP FOUNDATIONS / BEGABTENFÖRDERUNGSWERKE ---
        {
            "name": "Studienstiftung des deutschen Volkes",
            "category": "Scholarships / Stipendien",
            "url": "https://www.studienstiftung.de/",
            "target_group": "Students & Doctoral Candidates / Studierende und Promovierende"
        },
        {
            "name": "Friedrich-Ebert-Stiftung",
            "category": "Scholarships / Stipendien",
            "url": "https://www.fes.de/studienfoerderung/",
            "target_group": "Students & Doctoral Candidates / Studierende und Promovierende"
        },
        {
            "name": "Konrad-Adenauer-Stiftung",
            "category": "Scholarships / Stipendien",
            "url": "https://www.kas.de/de/studienfoerderung",
            "target_group": "Students, PhD & Early Career Researchers / Studierende, Promovierende & Nachwuchs"
        },
        {
            "name": "Hans-Böckler-Stiftung - Studienförderung",
            "category": "Scholarships / Stipendien",
            "url": "https://www.boeckler.de/de/index.htm",
            "target_group": "Bachelor, Master & Second Chance Education / Studierende aller Fachrichtungen"
        },
        {
            "name": "Heinrich-Böll-Stiftung - Studienförderwerk",
            "category": "Scholarships / Stipendien",
            "url": "https://www.boell.de/de/stipendien",
            "target_group": "Students & Doctoral Candidates / Studierende und Promovierende"
        },
        {
            "name": "Cusanuswerk – Bischöfliche Studienförderung",
            "category": "Scholarships / Stipendien",
            "url": "https://www.cusanuswerk.de/startseite",
            "target_group": "Catholic Students & PhD Candidates / Katholische Studierende und Promovierende"
        }
    ]

    # --- SYSTEM 2 MODEL POOL / MODELL-POOL FÜR SYSTEM 2 ---
    FAST_MODEL: str = "deepseek-chat"              # EN: Fast analysis (Step 1) / DE: Schnelle Erstanalyse (Schritt 1)
    REASONER_MODEL: str = "deepseek-reasoner"      # EN: Deep reasoning (Steps 2..N) / DE: Tiefenreflexion (Schritte 2..N)

    # --- CRAWLING & REFLECTION LIMITS / GRENZWERTE FÜR CRAWLING & REFLEXION ---
    MAX_CRAWL_DEPTH: int = 6                       # EN: Graph link traversal depth / DE: Link-Traversierungstiefe
    MAX_REFLECTION_ATTEMPTS: int = 2               # EN: Max LLM self-healing attempts / DE: Maximale Selbstheilungsversuche
    MAX_PAGES_PER_SOURCE: int = 10                 # EN: Max pages per portal / DE: Maximale Seitenzahl pro Portal

    # --- INTERVALS & TIMEOUTS / INTERVALLE & TIMEOUTS ---
    INTERVAL_MINUTES: int = 60
    REQUEST_TIMEOUT_SEC: float = 30.0

    # --- PATHS & STORAGE / PFADE & SPEICHERORTE ---
    OUTPUT_DIR: Path = Path("./output")
    REGISTRY_FILE: Path = Path("./sources_registry.json")
    VAULT_DB_FILE: Path = Path("./output/grants_vault.db")
    UNPROCESSED_FILE: Path = Path("./unprocessed_sources.json")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = HarvesterSettings()