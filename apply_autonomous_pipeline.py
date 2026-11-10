# Version: 1.8.0 | Release Date: 2026-11-09
"""Скрипт развертывания автономного конвейера Fail-to-Skill для pycognition."""

from pathlib import Path

FILES = {
    "config.py": """# Version: 1.8.0 | Release Date: 2026-11-09
from pathlib import Path
from typing import List, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_BROWSER_HEADERS: Dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}

class HarvesterSettings(BaseSettings):
    DISCOVERY_QUERIES: List[str] = [
        "Foerderdatenbank Forschung Wissenschaft Foerderprogramme",
        "DFG Aktuelle Ausschreibungen Information Wissenschaft 2026",
        "DAAD Stipendiendatenbank Promotionsstipendien Postdoc",
        "Stipendienlotse Bundesministerium Studierende Master",
        "Forschungsfoerderung Stiftungen Deutschland Ausschreibungen"
    ]

    SEED_SOURCES: List[Dict[str, str]] = [
        {
            "name": "DFG - Information für die Wissenschaft",
            "category": "DFG",
            "url": "https://www.dfg.de/de/aktuelles/neuigkeiten-themen/info-wissenschaft",
            "target_group": "Wissenschaftler, Postdocs & Teams"
        },
        {
            "name": "Förderdatenbank des Bundes (Forschung & Innovation)",
            "category": "BMBF / Bund",
            "url": "https://www.foerderdatenbank.de/SiteGlobals/FDB/Forms/Suche/Foerderprogrammsuche_Formular.html?cl2Categories_Bereich=forschung",
            "target_group": "Hochschulen, Forschungseinrichtungen & KMU"
        },
        {
            "name": "VolkswagenStiftung - Unsere Förderprogramme",
            "category": "Фонды и фондовые стипендии",
            "url": "https://www.volkswagenstiftung.de/de/foerderung/unsere-foerderprogramme",
            "target_group": "Nachwuchsforscher & Pionierprojekte"
        },
        {
            "name": "Fritz Thyssen Stiftung - Projektförderung",
            "category": "Фонды и фондовые стипендии",
            "url": "https://www.fritz-thyssen-stiftung.de/foerderung/foerderarten/projektfoerderung/",
            "target_group": "Geistes-, Sozial- und Naturwissenschaften"
        },
        {
            "name": "Fritz Thyssen Stiftung - Stipendien",
            "category": "Фонды и фондовые стипендии",
            "url": "https://www.fritz-thyssen-stiftung.de/foerderung/foerderarten/stipendien/",
            "target_group": "Promovierte Wissenschaftler (Postdocs)"
        },
        {
            "name": "DAAD - Internationale Programme & Stipendien",
            "category": "DAAD",
            "url": "https://www2.daad.de/deutschland/stipendium/datenbank/de/21148-stipendiendatenbank/",
            "target_group": "Studierende, Graduierte & Promovierende"
        }
    ]

    INTERVAL_MINUTES: int = 60
    OUTPUT_DIR: Path = Path("./output")
    REGISTRY_FILE: Path = Path("./sources_registry.json")
    REQUEST_TIMEOUT_SEC: float = 30.0
    BROWSER_HEADERS: Dict[str, str] = DEFAULT_BROWSER_HEADERS

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = HarvesterSettings()
""",

    "discovery.py": """# Version: 1.8.0 | Release Date: 2026-11-09
import json
import logging
import re
import urllib.parse
from typing import List, Dict
import httpx
from bs4 import BeautifulSoup

from config import settings, DEFAULT_BROWSER_HEADERS

logger = logging.getLogger("SourceDiscovery")

class SourceDiscoveryManager:
    def __init__(self):
        self.registry_file = settings.REGISTRY_FILE

    def load_registry(self) -> List[Dict[str, str]]:
        sources_dict = {s["name"]: s for s in settings.SEED_SOURCES}
        if self.registry_file.exists():
            try:
                data = json.loads(self.registry_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "name" in item and item["name"] not in sources_dict:
                            sources_dict[item["name"]] = item
            except Exception:
                pass

        merged = list(sources_dict.values())
        self.save_registry(merged)
        return merged

    def save_registry(self, sources: List[Dict[str, str]]) -> None:
        self.registry_file.write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8")

    async def discover_new_sources(self) -> List[Dict[str, str]]:
        known_sources = self.load_registry()
        known_urls = {s["url"].rstrip("/").lower() for s in known_sources}

        headers = getattr(settings, "BROWSER_HEADERS", DEFAULT_BROWSER_HEADERS).copy()
        headers["Referer"] = "https://www.google.com/"

        new_found_count = 0
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SEC, follow_redirects=True) as client:
            for query in settings.DISCOVERY_QUERIES:
                try:
                    # Используем GET к lite.duckduckgo.com для обхода блокировок
                    resp = await client.get(
                        "https://lite.duckduckgo.com/lite/",
                        params={"q": query},
                        headers=headers
                    )
                    if resp.status_code != 200:
                        continue

                    soup = BeautifulSoup(resp.text, "html.parser")
                    links = soup.find_all("a", class_="result-link") or soup.find_all("a", class_="result__a")
                    for a_tag in links[:4]:
                        raw_href = a_tag.get("href", "")
                        actual_url = raw_href
                        if "uddg=" in raw_href:
                            try:
                                actual_url = urllib.parse.unquote(raw_href.split("uddg=")[1].split("&")[0])
                            except Exception:
                                pass

                        if not actual_url.startswith("http") or any(x in actual_url for x in ["duckduckgo.com", "youtube.com", "wikipedia.org"]):
                            continue

                        clean_root = actual_url.rstrip("/").lower()
                        if clean_root not in known_urls:
                            known_urls.add(clean_root)
                            name = a_tag.get_text(strip=True) or "Forschungsförderung Portal"

                            cat = "Прочее финансирование"
                            if "dfg" in actual_url or "dfg" in name.lower():
                                cat = "DFG"
                            elif "daad" in actual_url or "daad" in name.lower():
                                cat = "DAAD"
                            elif "stipend" in actual_url or "stipend" in name.lower():
                                cat = "Студенческие стипендии"
                            elif "stift" in actual_url or "stift" in name.lower():
                                cat = "Фонды и фондовые стипендии"
                            elif "bund" in actual_url or "bmbf" in actual_url:
                                cat = "BMBF / Bund"

                            known_sources.append({
                                "name": name[:75],
                                "category": cat,
                                "url": actual_url,
                                "target_group": "Wissenschaftler & Studierende"
                            })
                            new_found_count += 1
                except Exception as e:
                    logger.debug(f"Поиск по '{query}': {e}")

        if new_found_count > 0:
            logger.info(f"Обнаружено {new_found_count} новых порталов финансирования! Реестр дополнен.")
            self.save_registry(known_sources)

        return known_sources
""",

    "harvester.py": """# Version: 1.8.0 | Release Date: 2026-11-09
import ast
import importlib.util
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import httpx
from bs4 import BeautifulSoup

from pycognition.engine.runtime import CognitiveRuntime
from pycognition.engine.meta_arbiter import MetaArbiter
from pycognition.engine.procedural_runner import ProceduralRunner
from pycognition.engine.llm_deliberator import LLMDeliberator, LLMProvider
from pycognition.memory.vector_store import VectorStoreMemory
from pycognition.engine.skill_crystallizer import SkillCrystallizer
from pycognition.memory.registry import SkillRegistry
from pycognition.schemas import Task, ExecutionStatus
from config import settings, DEFAULT_BROWSER_HEADERS
from schemas import GrantItem, FunderCategory, MultiSourceHarvestResult
from discovery import SourceDiscoveryManager
from widget_builder import render_all_grants_catalog

load_dotenv()
logger = logging.getLogger("AutonomousSelfHealingHarvester")

class MultiPortalGrantHarvester:
    def __init__(self):
        self.output_dir = Path(settings.OUTPUT_DIR).resolve()
        self.skills_dir = Path(os.getenv("PYCOGNITION_SKILLS_DIR", "./skills_registry")).resolve()
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        self.memory = VectorStoreMemory()
        self.system1 = ProceduralRunner()
        self.registry = SkillRegistry(storage_dir=self.skills_dir, runner=self.system1)
        if hasattr(self.registry, "load_all"):
            self.registry.load_all()

        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        model = os.getenv("PYCOGNITION_MODEL", "deepseek-chat")

        self.system2 = LLMDeliberator(
            provider=LLMProvider.DEEPSEEK if hasattr(LLMProvider, "DEEPSEEK") else LLMProvider.OPENAI,
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout=90.0
        )

        threshold = float(os.getenv("PYCOGNITION_ARBITER_THRESHOLD", "0.55"))
        self.arbiter = MetaArbiter(memory=self.memory, confidence_threshold=threshold)
        self.crystallizer = SkillCrystallizer(storage_dir=self.skills_dir)

        self.runtime = CognitiveRuntime(
            arbiter=self.arbiter,
            system1=self.system1,
            system2=self.system2,
            memory=self.memory,
            auto_crystallize=False
        )

        self.discovery_manager = SourceDiscoveryManager()

    def _slugify(self, text: str) -> str:
        slug = re.sub(r'[^a-zA-Z0-9_]', '_', text.lower())
        return re.sub(r'_+', '_', slug).strip('_')

    async def fetch_url(self, url: str) -> tuple[str, int, str]:
        headers = getattr(settings, "BROWSER_HEADERS", DEFAULT_BROWSER_HEADERS)
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SEC, follow_redirects=True) as client:
            try:
                resp = await client.get(url, headers=headers)
                return resp.text, resp.status_code, str(resp.url)
            except Exception as e:
                logger.error(f"Сетевой сбой при обращении к {url}: {e}")
                return "", 500, url

    def _execute_crystallized_skill(self, skill_func_name: str, html: str, base_url: str) -> list[dict]:
        \"\"\"Быстрое процедурное исполнение Системой 1 скомпилированного Python-модуля.\"\"\"
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
                    if isinstance(result, list):
                        return result
        except Exception as exc:
            logger.warning(f"Сбой исполнения локального навыка {skill_func_name}: {exc}")
        return []

    async def _solve_failure_with_system2(self, source_info: dict, error_type: str, details: str, html_sample: str) -> list[dict]:
        \"\"\"
        Контур самоисцеления: DeepSeek решает проблему, возвращает данные
        и компилирует подпрограмму для Системы 1 в skills_registry/.
        \"\"\"
        name = source_info["name"]
        url = source_info["url"]
        slug = self._slugify(name)
        skill_func_name = f"harvest_{slug}"

        logger.warning(f"[Система 2: Решение проблемы] Анализ сбоя '{error_type}' для '{name}' через DeepSeek...")

        prompt = (
            f"You are the System 2 meta-architect of pycognition. A grant harvester encountered a failure.\n"
            f"Source Name: {name}\n"
            f"Original URL: {url}\n"
            f"Failure Type: {error_type}\n"
            f"Error details: {details[:2000]}\n"
            f"HTML Sample: {html_sample[:3000]}\n\n"
            f"TASK:\n"
            f"1. Diagnose the issue and propose the direct solution (e.g. updated active URL, specific headers, or parsing logic).\n"
            f"2. Return JSON with:\n"
            f"   - 'discovered_items': list of extracted grant dictionaries (title, funder, deadline, link, description, target_group)\n"
            f"   - 'python_subroutine': complete Python function code: `def {skill_func_name}(html: str, base_url: str) -> list[dict]` using BeautifulSoup.\n"
            f"   - 'active_url': valid corrected URL if original was 404/moved.\n\n"
            f"Return ONLY valid JSON format."
        )

        task = Task(prompt=prompt, payload={"source_name": name, "url": url, "error": error_type})
        heal_res = await self.system2.deliberate(task)
        raw_output = getattr(heal_res, "output", getattr(heal_res, "result", ""))

        try:
            clean_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", str(raw_output).strip())
            data = json.loads(clean_json)
        except Exception as e:
            logger.error(f"Не удалось разобрать решение Системы 2: {e}")
            return []

        if data.get("active_url") and str(data["active_url"]).startswith("http"):
            source_info["url"] = str(data["active_url"])
            logger.info(f"[Самоисцеление URL]: Обновлен адрес для {name}: {data['active_url']}")

        # Кристаллизуем сгенерированный код в файл навыка
        subroutine_code = data.get("python_subroutine", "")
        if subroutine_code and skill_func_name in subroutine_code:
            try:
                ast.parse(subroutine_code)  # Проверка синтаксиса AST
                skill_file = self.skills_dir / f"{skill_func_name}.py"
                skill_file.write_text(subroutine_code, encoding="utf-8")
                logger.info(f"[Кристаллизация]: Синтезирована детерминированная подпрограмма: {skill_file.name}")
            except Exception as ast_err:
                logger.warning(f"Синтаксическая ошибка в сгенерированном коде: {ast_err}")

        items = data.get("discovered_items", [])
        return items if isinstance(items, list) else []

    async def process_source(self, source_info: dict) -> list[GrantItem]:
        name = source_info["name"]
        url = source_info["url"]
        slug = self._slugify(name)
        skill_func_name = f"harvest_{slug}"
        cat_str = source_info.get("category", "Прочее финансирование")

        category = FunderCategory.OTHER
        for c in FunderCategory:
            if c.value == cat_str or c.name == cat_str:
                category = c
                break

        logger.info(f"==> Запрос к источнику: {name}")
        html, status, final_url = await self.fetch_url(url)

        raw_items = []

        # 1. Попытка детерминированного выполнения через Систему 1 (0 токенов, <1 ms)
        if status == 200 and html:
            raw_items = self._execute_crystallized_skill(skill_func_name, html, final_url)
            if raw_items:
                logger.info(f"[СИСТЕМА 1] Навык {skill_func_name} отработал успешно! Извлечено {len(raw_items)} программ (0 токенов).")

        # 2. Если навыка еще нет, статус с ошибкой или парсер вернул 0 (DOM Drift) -> вызов Системы 2
        if not raw_items:
            err_type = f"HTTP_{status}" if status != 200 else "EMPTY_DOM_DRIFT"
            raw_items = await self._solve_failure_with_system2(
                source_info=source_info,
                error_type=err_type,
                details=f"Status: {status}, Final URL: {final_url}",
                html_sample=html[:3500] if html else ""
            )

        # Валидация через Pydantic
        grants = []
        for it in raw_items:
            if not isinstance(it, dict) or not it.get("title"):
                continue

            link = str(it.get("link", "")).strip()
            if link.startswith("/"):
                link = str(httpx.URL(final_url).join(link))
            elif not link.startswith("http"):
                link = final_url

            grants.append(GrantItem(
                title=str(it.get("title", "")).strip(),
                funder=str(it.get("funder", name)).strip(),
                funder_category=category,
                target_group=str(it.get("target_group", source_info.get("target_group", "Wissenschaftler"))),
                deadline=it.get("deadline"),
                funding_amount=it.get("funding_amount"),
                link=link,
                description=str(it.get("description", "")).strip(),
                source_portal=name,
                is_newly_discovered=(category in [FunderCategory.DISCOVERY, FunderCategory.FOUNDATION])
            ))

        logger.info(f"Итог по источнику {name}: получено {len(grants)} программ.")
        return grants

    async def run_full_harvest_cycle(self) -> MultiSourceHarvestResult:
        logger.info("=== Запуск цикла: Обнаружение источников -> Самоисцеление сбоев -> Каталог ===")

        sources = await self.discovery_manager.discover_new_sources()
        logger.info(f"В реестре активно {len(sources)} источников финансирования.")

        all_grants: list[GrantItem] = []
        active_sources_count = 0

        for src in sources:
            try:
                grants = await self.process_source(src)
                if grants:
                    all_grants.extend(grants)
                    active_sources_count += 1
            except Exception as err:
                logger.error(f"Необработанный сбой при обработке {src.get('name')}: {err}")

        # Дедупликация
        seen_titles = set()
        unique_grants = []
        new_count = 0

        for g in all_grants:
            norm = re.sub(r'\\s+', ' ', g.title.lower().strip())
            if norm not in seen_titles:
                seen_titles.add(norm)
                unique_grants.append(g)
                if g.is_newly_discovered:
                    new_count += 1

        result_payload = MultiSourceHarvestResult(
            harvested_at=datetime.now().isoformat(),
            total_grants=len(unique_grants),
            active_sources=active_sources_count,
            new_grantors_found=new_count,
            grants=unique_grants
        )

        self.output_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.output_dir / "all_grants.json"
        catalog_path = self.output_dir / "all_grants_catalog.html"

        json_path.write_text(result_payload.model_dump_json(indent=2), encoding="utf-8")
        render_all_grants_catalog(result_payload, catalog_path)

        logger.info(f"============================================================")
        logger.info(f"ИТОГ: Успешно собрано {len(unique_grants)} программ из {active_sources_count} источников!")
        logger.info(f"Каталог сформирован: {catalog_path.resolve()}")
        logger.info(f"Следующий плановый запуск через {settings.INTERVAL_MINUTES} минут (ежечасно).")
        logger.info(f"============================================================")
        return result_payload
"""
}

def main():
    for filename, content in FILES.items():
        Path(filename).write_text(content.strip(), encoding="utf-8")
        print(f"  [+] Обновлен файл: {filename}")
    print("\nКонвейер успешно обновлен.")

if __name__ == "__main__":
    main()