# ============================================================
#  applicator.py  –  Compilazione e invio candidature automatiche
# ============================================================

import time
import random
import os
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from ai_filter import genera_cover_letter
from database import offerte_da_candidare, salva_candidatura, aggiorna_stato_candidatura
from config import (
    INVIA_CANDIDATURE,
    PAUSA_TRA_CANDIDATURE,
    CV_PDF_PATH,
    ANTHROPIC_API_KEY,
)


#Utility

def pausa(minimo=2, massimo=6):
    time.sleep(random.uniform(minimo, massimo))


def log(msg):
    print(f"[Applicator] {msg}")


# LinkedIn Easy Apply 

def candidati_linkedin(page, offerta: dict, cover_letter: str) -> bool:
    """
    Tenta la candidatura su LinkedIn tramite il pulsante Easy Apply.
    Restituisce True se completata, False altrimenti.

    NOTA: LinkedIn cambia spesso il DOM — se smette di funzionare
    aggiorna i selettori controllando il sorgente della pagina.
    """
    try:
        page.goto(offerta["link"], timeout=20000)
        page.wait_for_load_state("domcontentloaded")
        pausa(2, 4)

        # Cerca il pulsante Easy Apply
        btn = page.query_selector("button.jobs-apply-button")
        if not btn:
            log(f"Nessun bottone Easy Apply trovato per: {offerta['titolo']}")
            return False

        btn.click()
        pausa(1, 3)

        # Step 1: Informazioni di contatto (di solito pre-compilate)
        _compila_campo_se_presente(page, "input[name='phoneNumber']", "")
        pausa(1, 2)

        # Step 2: Upload CV se richiesto
        upload = page.query_selector("input[type='file']")
        if upload and os.path.exists(CV_PDF_PATH):
            upload.set_input_files(CV_PDF_PATH)
            log("CV caricato.")
            pausa(1, 2)

        # Step 3: Cover letter se c'è un textarea
        textarea = page.query_selector("textarea")
        if textarea:
            textarea.fill(cover_letter)
            log("Cover letter inserita.")
            pausa(1, 2)

       
        for _ in range(8):   
            btn_avanti = (
                page.query_selector("button[aria-label='Invia candidatura']")
                or page.query_selector("button[aria-label='Submit application']")
                or page.query_selector("button:has-text('Invia')")
                or page.query_selector("button:has-text('Avanti')")
                or page.query_selector("button:has-text('Next')")
                or page.query_selector("button:has-text('Review')")
            )
            if not btn_avanti:
                break

            testo_btn = btn_avanti.inner_text().strip().lower()
            btn_avanti.click()
            pausa(1, 3)

            if any(k in testo_btn for k in ["invia", "submit"]):
                log(f"Candidatura inviata: {offerta['titolo']} @ {offerta['azienda']}")
                return True

        log(f"Wizard non completato per: {offerta['titolo']}")
        return False

    except PWTimeout:
        log(f"Timeout durante candidatura: {offerta['titolo']}")
        return False
    except Exception as e:
        log(f"Errore candidatura LinkedIn '{offerta['titolo']}': {e}")
        return False


#Indeed Apply

def candidati_indeed(page, offerta: dict, cover_letter: str) -> bool:
    """
    Tenta la candidatura su Indeed.
    Molte offerte Indeed reindirizzano al sito esterno dell'azienda —
    in quel caso il bot rileva il redirect e lo segnala.
    """
    try:
        page.goto(offerta["link"], timeout=20000)
        page.wait_for_load_state("domcontentloaded")
        pausa(2, 4)

        # Bottone candidatura Indeed
        btn = (
            page.query_selector("button#indeedApplyButton")
            or page.query_selector("a[data-tn-element='applyButton']")
            or page.query_selector("button:has-text('Candidati ora')")
        )

        if not btn:
            log(f"Nessun bottone candidatura su Indeed per: {offerta['titolo']}")
            return False

        btn.click()
        pausa(2, 4)

        # Controlla se siamo ancora su Indeed o reindirizzati
        url_attuale = page.url
        if "indeed.com" not in url_attuale:
            log(f"Reindirizzato a sito esterno ({url_attuale[:60]}...) — candidatura manuale necessaria.")
            return False

        # Compila cover letter
        textarea = page.query_selector("textarea")
        if textarea:
            textarea.fill(cover_letter)
            pausa(1, 2)

        # Upload CV
        upload = page.query_selector("input[type='file']")
        if upload and os.path.exists(CV_PDF_PATH):
            upload.set_input_files(CV_PDF_PATH)
            pausa(1, 2)

        # Invia
        btn_submit = (
            page.query_selector("button[type='submit']")
            or page.query_selector("button:has-text('Invia')")
        )
        if btn_submit:
            btn_submit.click()
            pausa(2, 3)
            log(f"Candidatura inviata: {offerta['titolo']} @ {offerta['azienda']}")
            return True

        return False

    except Exception as e:
        log(f"Errore candidatura Indeed '{offerta['titolo']}': {e}")
        return False


# Campo helper

def _compila_campo_se_presente(page, selettore: str, valore: str):
    """Compila un input solo se presente e vuoto."""
    try:
        el = page.query_selector(selettore)
        if el and not el.input_value():
            el.fill(valore)
    except Exception:
        pass




def candidati(page, offerta: dict, cover_letter: str) -> bool:
    fonte = offerta.get("fonte", "")
    if fonte == "linkedin":
        return candidati_linkedin(page, offerta, cover_letter)
    elif fonte == "indeed":
        return candidati_indeed(page, offerta, cover_letter)
    else:
        log(f"Fonte '{fonte}' non supportata per candidatura automatica.")
        return False


# Ciclo principale

def candidatura_batch():
    """
    Recupera dal DB le offerte approvate ma non ancora candidato,
    genera cover letter e invia le candidature.

    Se INVIA_CANDIDATURE=False in config.py gira in modalità
    dry-run: genera la cover letter e la salva ma NON invia.
    """
    offerte = offerte_da_candidare()

    if not offerte:
        log("Nessuna offerta in coda per la candidatura.")
        return

    log(f"Offerte da candidare: {len(offerte)}")

    if not INVIA_CANDIDATURE:
        log("⚠️  Modalità DRY-RUN attiva (INVIA_CANDIDATURE=False).")
        log("    Le cover letter vengono generate e salvate ma non inviate.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=INVIA_CANDIDATURE)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="it-IT",
        )
        page = context.new_page()

        for offerta in offerte:
            log(f"Processo: {offerta['titolo']} @ {offerta['azienda']}")

            try:
                cover = genera_cover_letter(offerta)
            except Exception as e:
                log(f"Errore generazione cover letter: {e}")
                continue

            if INVIA_CANDIDATURE:
                successo = candidati(page, offerta, cover)
            else:
                successo = True
                log(f"[DRY-RUN] Cover letter generata per '{offerta['titolo']}'")

            salva_candidatura(
                offerta_id   = offerta["id"],
                cover_letter = cover,
                cv_versione  = os.path.basename(CV_PDF_PATH),
            )

            if not successo:
                aggiorna_stato_candidatura(
                    offerta_id = offerta["id"],
                    stato      = "errore",
                    note       = "Candidatura automatica fallita — verificare manualmente.",
                )
                log(f"❌ Fallita: {offerta['titolo']}")
            else:
                log(f"✅ {'Simulata' if not INVIA_CANDIDATURE else 'Inviata'}: {offerta['titolo']}")

            # Pausa anti-ban tra candidature
            time.sleep(PAUSA_TRA_CANDIDATURE + random.uniform(0, 10))

        browser.close()

    log("Ciclo candidature completato.")



def candidatura_singola(offerta: dict):
    """
    Utile per testare una singola offerta senza passare dal DB.
    Apre il browser in modalità visibile per debug.
    """
    cover = genera_cover_letter(offerta)
    print("\n=== COVER LETTER GENERATA ===")
    print(cover)
    print("=" * 40)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  
        page = browser.new_page()
        risultato = candidati(page, offerta, cover)
        print(f"\nRisultato: {'✅ Successo' if risultato else '❌ Fallita'}")
        input("Premi INVIO per chiudere il browser...")
        browser.close()


if __name__ == "__main__":
    from database import init_db
    init_db()
    candidatura_batch()