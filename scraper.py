import time
import random
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from database import salva_offerta, link_gia_visto
from config import KEYWORDS_RICERCA, LOCATIONS, FONTI_ABILITATE, PAUSA_TRA_CANDIDATURE



def pausa(minimo=2, massimo=5):
    """Pausa random anti-ban tra le richieste."""
    time.sleep(random.uniform(minimo, massimo))


def headers_browser():
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8",
    }


# Linkedin
def scrape_linkedin(keyword, location, max_pagine=3):
    """
    Scraping offerte LinkedIn (senza login, sezione pubblica).
    Restituisce lista di dict {titolo, azienda, link, location, descrizione}.
    """
    offerte = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=headers_browser()["User-Agent"],
            locale="it-IT",
        )
        page = context.new_page()

        for pagina in range(max_pagine):
            start = pagina * 25
            url = (
                f"https://www.linkedin.com/jobs/search/"
                f"?keywords={keyword.replace(' ', '%20')}"
                f"&location={location.replace(' ', '%20')}"
                f"&start={start}"
            )
            print(f"[LinkedIn] Pagina {pagina + 1}: {url}")

            try:
                page.goto(url, timeout=20000)
                page.wait_for_selector(".jobs-search__results-list", timeout=10000)
            except PWTimeout:
                print(f"[LinkedIn] Timeout alla pagina {pagina + 1}, salto.")
                break

            cards = page.query_selector_all(".base-card")
            if not cards:
                print("[LinkedIn] Nessuna card trovata, fine paginazione.")
                break

            for card in cards:
                try:
                    titolo   = card.query_selector(".base-search-card__title")
                    azienda  = card.query_selector(".base-search-card__subtitle")
                    link_el  = card.query_selector("a.base-card__full-link")
                    loc_el   = card.query_selector(".job-search-card__location")

                    if not (titolo and azienda and link_el):
                        continue

                    link = link_el.get_attribute("href").split("?")[0]

                    if link_gia_visto(link):
                        continue

                    offerte.append({
                        "titolo":      titolo.inner_text().strip(),
                        "azienda":     azienda.inner_text().strip(),
                        "link":        link,
                        "fonte":       "linkedin",
                        "location":    loc_el.inner_text().strip() if loc_el else location,
                        "descrizione": "",  
                    })
                except Exception as e:
                    print(f"[LinkedIn] Errore card: {e}")

            pausa(3, 6)

        for offerta in offerte:
            try:
                page.goto(offerta["link"], timeout=15000)
                page.wait_for_selector(".description__text", timeout=8000)
                desc = page.query_selector(".description__text")
                if desc:
                    offerta["descrizione"] = desc.inner_text().strip()[:3000]
            except Exception:
                pass
            pausa(2, 4)

        browser.close()

    print(f"[LinkedIn] Trovate {len(offerte)} nuove offerte per '{keyword}' in '{location}'.")
    return offerte


# Indeed

def scrape_indeed(keyword, location, max_pagine=3):
    """
    Scraping offerte Indeed Italia.
    """
    offerte = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=headers_browser()["User-Agent"],
            locale="it-IT",
        )
        page = context.new_page()

        for pagina in range(max_pagine):
            start = pagina * 10
            url = (
                f"https://it.indeed.com/jobs"
                f"?q={keyword.replace(' ', '+')}"
                f"&l={location.replace(' ', '+')}"
                f"&start={start}"
            )
            print(f"[Indeed] Pagina {pagina + 1}: {url}")

            try:
                page.goto(url, timeout=20000)
                page.wait_for_selector(".job_seen_beacon", timeout=10000)
            except PWTimeout:
                print(f"[Indeed] Timeout alla pagina {pagina + 1}, salto.")
                break

            cards = page.query_selector_all(".job_seen_beacon")
            if not cards:
                break

            for card in cards:
                try:
                    titolo_el  = card.query_selector("h2.jobTitle span")
                    azienda_el = card.query_selector("[data-testid='company-name']")
                    link_el    = card.query_selector("h2.jobTitle a")
                    loc_el     = card.query_selector("[data-testid='text-location']")
                    desc_el    = card.query_selector(".job-snippet")

                    if not (titolo_el and azienda_el and link_el):
                        continue

                    href = link_el.get_attribute("href")
                    link = f"https://it.indeed.com{href}" if href.startswith("/") else href
                    link = link.split("?")[0]

                    if link_gia_visto(link):
                        continue

                    offerte.append({
                        "titolo":      titolo_el.inner_text().strip(),
                        "azienda":     azienda_el.inner_text().strip(),
                        "link":        link,
                        "fonte":       "indeed",
                        "location":    loc_el.inner_text().strip() if loc_el else location,
                        "descrizione": desc_el.inner_text().strip() if desc_el else "",
                    })
                except Exception as e:
                    print(f"[Indeed] Errore card: {e}")

            pausa(3, 5)

        browser.close()

    print(f"[Indeed] Trovate {len(offerte)} nuove offerte per '{keyword}' in '{location}'.")
    return offerte


#  Dispatcher principale

def scrapa_tutto():
    """
    Lancia lo scraping su tutte le combinazioni keyword × location
    per tutte le fonti abilitate in config.py.
    Salva tutto nel database e restituisce la lista completa.
    """
    tutte = []

    for keyword in KEYWORDS_RICERCA:
        for location in LOCATIONS:

            if FONTI_ABILITATE.get("linkedin"):
                try:
                    offerte = scrape_linkedin(keyword, location)
                    for o in offerte:
                        salva_offerta(**o)
                    tutte.extend(offerte)
                except Exception as e:
                    print(f"[Scraper] LinkedIn error: {e}")
                pausa(5, 10)

            if FONTI_ABILITATE.get("indeed"):
                try:
                    offerte = scrape_indeed(keyword, location)
                    for o in offerte:
                        salva_offerta(**o)
                    tutte.extend(offerte)
                except Exception as e:
                    print(f"[Scraper] Indeed error: {e}")
                pausa(5, 10)

    print(f"\n[Scraper] Totale nuove offerte salvate: {len(tutte)}")
    return tutte


if __name__ == "__main__":
    from database import init_db
    init_db()
    scrapa_tutto()