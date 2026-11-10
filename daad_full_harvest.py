# File: daad_full_harvest.py
# Version: 1.0.0 | Release Date: 2026-11-09
import sys
import os
import shutil
import json
import time

# Хак для совместимости Python 3.14 и undetected-chromedriver
try:
    import distutils
except ModuleNotFoundError:
    import setuptools
    import distutils.core
    sys.modules['distutils.version'] = sys.modules.get('setuptools._distutils.version', None)

import platform
if platform.system() == "Windows":
    appdata = os.getenv('LOCALAPPDATA', '')
    uc_cache_path = os.path.join(appdata, 'nowsecure', 'undetected-chromedriver')
    if os.path.exists(uc_cache_path):
        try:
            shutil.rmtree(uc_cache_path)
        except Exception:
            pass

import undetected_chromedriver as uc

MAX_PAGES = 10  # Ограничение глубины пагинации
BASE_URL = "https://study-in-germany.de"


def init_browser() -> uc.Chrome:
    """Инициализация браузера с подавлением автоматических флагов."""
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    return uc.Chrome(options=options, version_main=156)


def extract_page_items(driver) -> list[dict]:
    """Инъекция JS для сбора карточек программ с текущего экрана."""
    js_extractor = """
    let results = [];
    document.querySelectorAll('h3, h4').forEach(h => {
        let text = h.innerText ? h.innerText.trim() : '';
        if (text.length > 15) {
            let parentA = h.closest('a') || h.querySelector('a');
            if (parentA && parentA.href) {
                results.push({
                    'title': text,
                    'link': parentA.href
                });
            }
        }
    });

    document.querySelectorAll('a').forEach(a => {
        let text = a.innerText ? a.innerText.trim() : '';
        let href = a.href || '';
        if (text.length > 10 && (href.includes('detail=') || href.includes('scholarship') || href.includes('programme/'))) {
            results.push({
                'title': text,
                'link': href
            });
        }
    });
    return results;
    """
    raw_items = driver.execute_script(js_extractor)
    clean_items = []
    seen_links = set()

    for item in raw_items:
        title = item.get('title', '').replace('\n', ' ').strip()
        link = item.get('link', '').strip()

        if len(title) > 15 and link not in seen_links:
            if not any(word in title.lower() for word in ['cookie', 'accept', 'menu', 'privacy', 'imprint']):
                seen_links.add(link)
                clean_items.append({"title": title, "link": link})

    return clean_items


def go_to_next_page(driver) -> bool:
    """Клик по кнопке пагинации через JS."""
    js_pager = """
    let nextBtn = document.querySelector('button[aria-label="Next page"], a.pagination__next, .page-item.next a, button.next');
    if (nextBtn && !nextBtn.disabled && nextBtn.offsetParent !== null) {
        nextBtn.click();
        return true;
    }
    return false;
    """
    return bool(driver.execute_script(js_pager))


def enrich_grant_details(driver, grant: dict) -> dict:
    """Переход на страницу гранта и сбор дедлайна, суммы и требований."""
    url = grant.get("link")
    if not url or not url.startswith("http"):
        return grant

    try:
        driver.get(url)
        time.sleep(3.5)

        js_details = """
        let body = document.body ? document.body.innerText : '';
        let deadline = 'laufend / siehe Ausschreibung';
        let amount = 'Nicht spezifiziert';

        // Поиск дедлайна
        let dMatch = body.match(/(?:Bewerbungsfrist|Application deadline|Frist|Deadline)[:\\s]+([^\\n\\r]+)/i);
        if (dMatch) {
            deadline = dMatch[1].trim().slice(0, 80);
        }

        // Поиск суммы финансирования
        let aMatch = body.match(/(?:Fördersumme|Funding|Stipendienrate|Dotierung)[:\\s]+([^\\n\\r]+)/i);
        if (aMatch) {
            amount = aMatch[1].trim().slice(0, 80);
        }

        return {
            'deadline': deadline,
            'funding_amount': amount,
            'description': body.slice(0, 500).replace(/\\s+/g, ' ').trim()
        };
        """
        details = driver.execute_script(js_details)
        grant.update(details)
    except Exception as err:
        print(f"  [!] Пропуск деталей для {url}: {err}")

    return grant


def main():
    print("Запуск анти-детекта и сборщика программ...")
    driver = init_browser()
    all_grants = []
    seen_urls = set()

    try:
        print(f"Подключение к порталу: {BASE_URL}")
        driver.get(BASE_URL)
        print("Ожидание первичного рендеринга Angular (12 сек)...")
        time.sleep(12)

        # 1. Цикл пагинации
        for page_idx in range(1, MAX_PAGES + 1):
            print(f"\n[Страница {page_idx}] Сбор элементов через JS-инъекцию...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            page_items = extract_page_items(driver)
            new_on_page = 0

            for item in page_items:
                if item["link"] not in seen_urls:
                    seen_urls.add(item["link"])
                    all_grants.append(item)
                    new_on_page += 1

            print(f"  Найдено на странице: {len(page_items)}, новых программ: {new_on_page}")

            if not go_to_next_page(driver):
                print("  Кнопка 'Следующая страница' не найдена или достигнут конец выдачи.")
                break

            time.sleep(4)

        print(f"\nВсего обнаружено {len(all_grants)} программ. Начинаем сбор детальной информации...")

        # 2. Сбор детальной информации по каждой ссылке
        enriched_grants = []
        for idx, g in enumerate(all_grants, start=1):
            print(f"[{idx}/{len(all_grants)}] Извлечение деталей: {g['title'][:50]}...")
            enriched_grants.append(enrich_grant_details(driver, g))
            time.sleep(1.5)

        # 3. Сохранение итогового результата
        output_file = "grants_full.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(enriched_grants, f, indent=2, ensure_ascii=False)

        print("\n--- УСПЕШНО ЗАВЕРШЕНО ---")
        print(f"Сохранено {len(enriched_grants)} полных профилей грантов в файл {output_file}")

    except Exception as e:
        print(f"Критический сбой выполнения: {e}")
    finally:
        try:
            driver.close()
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()