# Grant Harvester: Autonomous Academic Funding Monitoring Framework
### Autonomes Framework zur Überwachung akademischer Forschungsförderung

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-brightgreen.svg)](https://www.python.org/)
[![Playwright: Stealth](https://img.shields.io/badge/Browser-Playwright%20Edge%20Stealth-blueviolet.svg)](https://playwright.dev/)
[![LLM: DeepSeek R1 / Chat](https://img.shields.io/badge/AI%20Reflection-DeepSeek%20Chat%20%26%20R1-orange.svg)](https://deepseek.com/)
[![Standard: KDSF 2.1 Ready](https://img.shields.io/badge/Standard-KDSF%202.1%20Ready-informational.svg)](https://kerndatensatz-forschung.de/)

---

## Overview / Übersicht

### English
**Grant Harvester** is an autonomous, self-healing information harvesting framework engineered to discover, extract, and monitor academic funding calls, fellowships, and research grants across Germany and the European Union (including **DFG, BMBF, EU Horizon Europe, ERC, and major independent research foundations**). 

The platform employs a dual-tier cognitive architecture:
1. **System 1 (Procedural Execution):** High-speed, deterministic parsing routines executed without external LLM latency or token consumption.
2. **System 2 (Two-Tier Cognitive Reflection):** An automated self-healing supervisor combining fast structural identification (`deepseek-chat`) with deep architectural reflection (`deepseek-reasoner` / R1) to resolve DOM mutations, bot-protection barriers, and navigation graph depth.

### Deutsch
**Grant Harvester** ist ein autonomes, selbstheilendes Informationserfassungs-Framework zur Entdeckung, Extraktion und kontinuierlichen Überwachung akademischer Förderausschreibungen, Stipendien und Forschungsprogramme in Deutschland und der Europäischen Union (u. a. **DFG, BMBF, EU Horizon Europe, ERC und namhafte Stiftungen**).

Das System basiert auf einer zweistufigen kognitiven Architektur:
1. **System 1 (Prozedurale Ausführung):** Hochperformante, deterministische Parsing-Routinen, die ohne LLM-Latenz und ohne Token-Verbrauch arbeiten.
2. **System 2 (Zweistufige kognitive Reflexion):** Eine automatisierte Selbstheilungs-Ebene, die schnelle Strukturanalysen (`deepseek-chat`) mit tiefgehender logischer Reflexion (`deepseek-reasoner` / R1) kombiniert, um DOM-Drift, Bot-Schutzbarrieren und Navigationsgraphen autonom zu bewältigen.

---

## Architectural Pillars / Architektur-Säulen

| Component / Komponente | Implementation / Umsetzung | Function / Funktion |
| :--- | :--- | :--- |
| **System 1 Runner** | `ProceduralRunner` & `bs4` | Executes validated Python parsing subroutines directly on page HTML. / Führt validierte Extraktionsroutinen direkt aus. |
| **System 2 Fast (Tier 1)** | `deepseek-chat` | Rapid semantic extraction of container cards and layout signatures. / Schnelle Identifikation von Container- und Layoutstrukturen. |
| **System 2 R1 (Tier 2)** | `deepseek-reasoner` | Deep diagnostic reflection on parser failures, WAF challenges, and schema drift. / Tiefendiagnose bei Parser-Fehlern und Schema-Abweichungen. |
| **Stealth Engine** | Playwright + MS Edge / Chromium | Evaluates dynamic JavaScript trees, handles DOM hydration, and bypasses bot gates. / Rendert dynamische SPAs und umgeht Bot-Barrieren. |
| **Title Quality Barrier** | Automated String Validator | Rejects single-character corrupt titles (`s`, `)`, `6`, `”`) and restores authentic calls. / Verhindert verstümmelte Titel und stellt Originaltitel wieder her. |
| **Quarantine Manager** | `UnprocessedTracker` | Isolates stubborn portals into `unprocessed_sources.json` without stalling cycles. / Isoliert komplexe Quellen ohne Blockierung des Zyklus. |
| **Persistence Vault** | SQLite (`grants_vault.db`) | Deduplicates records via SHA-256 fingerprints and tracks grant lifecycles. / Dedupliziert Einträge per SHA-256 und pflegt den Lebenszyklus. |
| **Web Catalog** | `widget_builder.py` | Generates a standalone, bilingual (EN/DE) HTML catalog with dynamic source buttons. / Erstellt einen eigenständigen zweisprachigen HTML-Katalog. |

---

## Directory Layout / Verzeichnisstruktur

```text
grant-harvester/
│
├── config.py                 # EN: Typed settings & seed registries / DE: Typisierte Einstellungen & Seed-Register
├── main.py                   # EN: Background daemon entrypoint / DE: Daemon-Haupteinstiegspunkt
├── harvester.py              # EN: Graph crawler & System 2 reflection / DE: Graph-Crawler & System-2-Reflexion
├── browser_fetcher.py        # EN: Stealth Playwright browser engine / DE: Stealth-Browser-Engine
├── storage.py                # EN: SQLite vault & lifecycle manager / DE: SQLite-Vault & Lebenszyklusverwaltung
├── discovery.py              # EN: Web & LLM source discovery agent / DE: Quellen-Erkundungsagent
├── widget_builder.py         # EN: Bilingual HTML catalog generator / DE: Zweisprachiger HTML-Kataloggenerator
├── unprocessed_tracker.py    # EN: Quarantine registry manager / DE: Quarantäne-Register-Manager
├── schemas.py                # EN: Pydantic data schemas / DE: Pydantic-Datenschemata
│
├── skills_registry/          # EN: Validated procedural skills / DE: Validierte prozedurale Skills
├── output/                   # EN: Generated vault, catalogs & JSON / DE: Generierte Vault-, HTML- & JSON-Dateien
│   ├── grants_vault.db       # EN: Primary SQLite database / DE: Primäre SQLite-Datenbank
│   ├── all_grants.json       # EN: Machine-readable snapshot / DE: Maschinenlesbarer Daten-Snapshot
│   └── all_grants_catalog.html # EN: Interactive web catalog / DE: Interaktiver Web-Katalog
│
├── pyproject.toml            # EN: Build specifications (PEP 518/621) / DE: Build-Spezifikationen
├── requirements.txt          # EN: Pinned dependencies / DE: Fixierte Abhängigkeiten
├── .env.example              # EN: Environment variable template / DE: Vorlage für Umgebungsvariablen
├── .gitignore                # EN: Git tracking exclusion rules / DE: Git-Ausschlussregeln
├── LICENSE                   # EN/DE: MIT License
└── CITATION.cff              # EN/DE: Citation File Format metadata
```

---

## Installation & Setup / Installation & Einrichtung

### 1. Prerequisites / Voraussetzungen
* **Python 3.11** or higher / oder höher
* **Microsoft Edge** or **Google Chrome** installed / installiert
* **DeepSeek API Key** (or compatible OpenAI-format endpoint / oder kompatibler Endpunkt)
* **Git** installed / installiert

### 2. Download & Install / Herunterladen & Installieren
Download the framework directly from GitHub and set up the isolated environment.

#### Windows (Command Prompt / PowerShell)
```bat
:: Clone the repository / Repository klonen
git clone https://github.com/MasterUaKi/grant-harvester.git
cd grant-harvester

:: Create and activate virtual environment / Virtuelle Umgebung erstellen und aktivieren
python -m venv .venv
.venv\Scripts\activate

:: Install runtime dependencies / Abhängigkeiten installieren
pip install -r requirements.txt

:: Initialize Playwright browser binaries / Playwright-Browserkomponenten initialisieren
playwright install chromium
```

#### Linux (Debian / Ubuntu)
```bash
# Clone the repository / Repository klonen
git clone https://github.com/MasterUaKi/grant-harvester.git
cd grant-harvester

# Create and activate virtual environment / Virtuelle Umgebung erstellen und aktivieren
python3 -m venv .venv
source .venv/bin/activate

# Install runtime dependencies / Abhängigkeiten installieren
pip install -r requirements.txt

# Initialize Playwright browser binaries / Playwright-Browserkomponenten initialisieren
playwright install --with-deps chromium
```

### 3. Configuration / Konfiguration
The system requires an API key to perform System 2 LLM reflection. Copy the template file and insert your credentials.

#### Windows
```bat
copy .env.example .env
notepad .env
```

#### Linux
```bash
cp .env.example .env
nano .env
```

**Content of `.env` / Inhalt der `.env`:**
```env
# LLM API Settings
DEEPSEEK_API_KEY=sk-your-actual-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

---

## Usage / Verwendung

### Run the Harvester Daemon / Harvester-Daemon starten
```bash
python main.py
```

### Generate the HTML Web Catalog / HTML-Web-Katalog generieren
```bash
python widget_builder.py
```
The compiled catalog will be saved to `output/all_grants_catalog.html`. / Der kompilierte Katalog wird unter `output/all_grants_catalog.html` gespeichert.

---

## License & Citation / Lizenz & Zitierung
Distributed under the **MIT License**. See `LICENSE` and `CITATION.cff` for more information. / Veröffentlicht unter der **MIT-Lizenz**. Weitere Informationen finden Sie in `LICENSE` und `CITATION.cff`.
