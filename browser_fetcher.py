# File: browser_fetcher.py
# Version: 2.5.0 | Release Date: 2026-11-10
"""
EN: Stealth browser engine using Playwright for WAF bypass and DOM hydration.
DE: Stealth-Browser-Engine mit Playwright zur WAF-Umgehung und DOM-Hydrierung.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger("StealthBrowser")


class StealthBrowserEngine:
    """
    EN: Edge/Chromium automation engine with anti-bot evasion and DOM synthesis.
    DE: Edge/Chromium-Automatisierungs-Engine mit Anti-Bot-Umgehung und DOM-Synthese.
    """

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def _ensure_browser(self):
        """
        EN: Initializes the headless browser instance with stealth arguments.
        DE: Initialisiert die Headless-Browser-Instanz mit Stealth-Parametern.
        """
        if self._browser is None:
            self._playwright = await async_playwright().start()
            try:
                self._browser = await self._playwright.chromium.launch(
                    channel="msedge",
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-infobars",
                    ]
                )
                logger.info(
                    "EN: Microsoft Edge browser engine initialized / "
                    "DE: Microsoft Edge Browser-Engine initialisiert."
                )
            except Exception as e:
                logger.warning(
                    f"EN: Falling back to Chromium ({e}) / "
                    f"DE: Fallback auf Standard-Chromium ({e})..."
                )
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
                )

            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
                ),
                locale="de-DE",
                timezone_id="Europe/Berlin"
            )

    @staticmethod
    def _get_js_extractor_script() -> str:
        """
        EN: In-browser evaluation script to harvest program cards directly from memory.
        DE: Im Browser ausgeführtes Skript zur direkten Extraktion von Programmkarten aus dem DOM.
        """
        return """
        () => {
            let results = [];
            let seen = new Set();

            function addGrant(title, link, container) {
                if (!title || title.length < 8) return;
                let cleanTitle = title.replace(/\\s+/g, ' ').trim();
                let cleanLink = link ? link.trim() : window.location.href;
                if (!cleanLink.startsWith('http')) {
                    try { cleanLink = new URL(cleanLink, window.location.href).href; } catch(e){}
                }
                let normKey = cleanTitle.toLowerCase() + '|' + cleanLink;
                if (seen.has(normKey)) return;
                seen.add(normKey);

                let lower = cleanTitle.toLowerCase();
                let noise = [
                    'cookie', 'datenschutz', 'impressum', 'privacy', 'accept',
                    'alle ablehnen', 'navigation', 'anmelden', 'login', 'kontakt',
                    'sitemap', 'newsletter', 'abonnieren'
                ];
                if (noise.some(w => lower.includes(w))) return;

                let snippet = '';
                let deadline = 'laufend / ongoing';
                let amount = '';

                if (container) {
                    let text = container.innerText || '';
                    snippet = text.slice(0, 350).replace(/\\s+/g, ' ').trim();
                    let dMatch = text.match(/(?:Bewerbungsfrist|Frist|Deadline|Antragsfrist)[:\\s]+([^\\n\\r]+)/i);
                    if (dMatch) deadline = dMatch[1].trim().slice(0, 80);
                    let aMatch = text.match(/(?:Fördersumme|Funding|Stipendienrate|Dotierung)[:\\s]+([^\\n\\r]+)/i);
                    if (aMatch) amount = aMatch[1].trim().slice(0, 80);
                }

                results.push({
                    title: cleanTitle,
                    link: cleanLink,
                    description: snippet,
                    deadline: deadline,
                    funding_amount: amount
                });
            }

            // Strategy 1: Target cards and semantic teaser wrappers
            let cardSelectors = [
                'ul.resultlist li.entry', 'li.entry', '.c-teaser', '.s-results__item',
                '.search-result', '.scholarship-list-item', 'article', '.result-item',
                '[class*="teaser"]', '[class*="card"]', '[class*="overview-list__item"]'
            ];
            cardSelectors.forEach(sel => {
                document.querySelectorAll(sel).forEach(card => {
                    let heading = card.querySelector('h2 a, h3 a, h2, h3, h4, .title, [class*="title"]');
                    let a = card.querySelector('a[href]') || card.closest('a[href]');
                    if (heading) {
                        let link = (heading.tagName === 'A' && heading.href) ? heading.href : (a ? a.href : window.location.href);
                        addGrant(heading.innerText, link, card);
                    }
                });
            });

            // Strategy 2: Target anchors with academic funding signatures
            document.querySelectorAll('a[href]').forEach(a => {
                let href = a.href || '';
                let lowerHref = href.toLowerCase();
                let hasSignature = lowerHref.includes('detail=') || lowerHref.includes('/detail/') ||
                                   lowerHref.includes('stipendium') || lowerHref.includes('scholarship') ||
                                   lowerHref.includes('foerder') || lowerHref.includes('programme/') ||
                                   lowerHref.includes('call');
                if (hasSignature) {
                    let text = a.innerText ? a.innerText.trim() : '';
                    if (text.length >= 8) {
                        let container = a.closest('li, div, article');
                        addGrant(text, href, container);
                    }
                }
            });

            return results;
        }
        """

    async def fetch_page_html(self, url: str, wait_timeout_sec: float = 20.0) -> str:
        """
        EN: Navigates to a target URL, awaits DOM hydration, and injects clean program cards.
        DE: Navigiert zur Ziel-URL, wartet auf DOM-Hydrierung und injiziert saubere Programmkarten.
        """
        await self._ensure_browser()
        page: Page = await self._context.new_page()

        try:
            logger.info(
                f"EN: Browser navigating to / DE: Browser-Navigation nach: {url}"
            )
            await page.goto(url, wait_until="domcontentloaded", timeout=35000)

            is_spa = any(h in url.lower() for h in ["daad.de", "study-in-germany.de", "europa.eu", "kas.de"])

            if is_spa:
                try:
                    await page.wait_for_selector(
                        ".c-teaser, .search-result, article, tbody tr, .card",
                        timeout=8000
                    )
                except Exception:
                    await asyncio.sleep(2.0)

                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1.5)

                extracted_items = await page.evaluate(self._get_js_extractor_script())

                if extracted_items and len(extracted_items) > 0:
                    inject_dom_script = """
                    (items) => {
                        let container = document.getElementById('pycognition-injected-grants');
                        if (!container) {
                            container = document.createElement('section');
                            container.id = 'pycognition-injected-grants';
                            container.style.display = 'block';
                            document.body.appendChild(container);
                        }
                        container.innerHTML = '';
                        items.forEach(it => {
                            let art = document.createElement('article');
                            art.className = 'grant-injected-card';
                            art.innerHTML = `
                                <h3><a href="${it.link}">${it.title}</a></h3>
                                <p class="description">${it.description}</p>
                                <span class="deadline">${it.deadline}</span>
                            `;
                            container.appendChild(art);
                        });
                    }
                    """
                    await page.evaluate(inject_dom_script, extracted_items)
                    logger.info(
                        f"EN: Injected {len(extracted_items)} cards into DOM / "
                        f"DE: {len(extracted_items)} Karten in DOM injiziert: {url}"
                    )
            else:
                await asyncio.sleep(1.5)

            html = await page.content()
            return html
        except Exception as err:
            logger.error(
                f"EN: Browser fetch error / DE: Fehler beim Browser-Abruf für {url}: {err}"
            )
            return ""
        finally:
            await page.close()

    async def close(self):
        """
        EN: Releases browser instances, contexts, and Playwright worker processes.
        DE: Gibt Browser-Instanzen, Kontexte und Playwright-Worker-Prozesse frei.
        """
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None