import os
import time
import argparse
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

from database import init_db, stats, offerte_da_candidare
from scraper import scrapa_tutto
from ai_filter import valuta_tutte, riepilogo_giornaliero
from applicator import candidatura_batch
from analyzer import analizza_azienda, stampa_report
from config import SCHEDULE_ORE, INVIA_CANDIDATURE, REPORTS_DIR



def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def intestazione():
    print("""
╔══════════════════════════════════════════════════╗
║            🤖  JOB APPLICATION BOT                ║
║     Scraping · Filtraggio AI · Candidatura       ║
╚══════════════════════════════════════════════════╝
""")


def assicura_cartelle():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs("assets", exist_ok=True)



def ciclo_completo():
    """
    Esegue l'intero pipeline:
    1. Scraping nuove offerte
    2. Valutazione AI e filtraggio
    3. Analisi aziendale per le offerte approvate
    4. Candidatura automatica
    5. Generazione report
    """
    log("═" * 50)
    log("INIZIO CICLO COMPLETO")
    log("═" * 50)

    #Step 1: Scraping 
    log("STEP 1/4 — Scraping offerte...")
    try:
        scrapa_tutto()
    except Exception as e:
        log(f"Errore scraping: {e}")

    # Step 2: Valutazione AI 
    log("STEP 2/4 — Valutazione AI offerte...")
    try:
        approvate = valuta_tutte()
        log(f"Offerte approvate: {len(approvate)}")
    except Exception as e:
        log(f"Errore valutazione AI: {e}")
        approvate = []

    #  Step 3: Analisi aziendali 
    log("STEP 3/4 — Analisi posizione aziendale...")
    analisi_map = {}
    aziende_da_analizzare = list({o["azienda"] for o in approvate})

    for azienda in aziende_da_analizzare:
        try:
            analisi = analizza_azienda(azienda)
            analisi_map[azienda] = analisi
        except Exception as e:
            log(f"Errore analisi '{azienda}': {e}")

    # Step 4: Candidature
    log(f"STEP 4/4 — Candidature (modalità: {'REALE' if INVIA_CANDIDATURE else 'DRY-RUN'})...")
    try:
        candidatura_batch()
    except Exception as e:
        log(f"Errore candidature: {e}")

    #Report finale
    log("Generazione report...")
    try:
        genera_report_html(approvate, analisi_map)
    except Exception as e:
        log(f"Errore generazione report: {e}")

    log("CICLO COMPLETATO")
    stats()


# Generazione report HTML 

def _badge(valore: str) -> str:
    colori = {
        "positiva":            ("d4edda", "155724"),
        "negativa":            ("f8d7da", "721c24"),
        "neutra":              ("e2e3e5", "383d41"),
        "insufficiente_info":  ("fff3cd", "856404"),
        "progressista":        ("cce5ff", "004085"),
        "conservatore":        ("f8d7da", "721c24"),
        "centrista":           ("e2e3e5", "383d41"),
        "non_determinabile":   ("fff3cd", "856404"),
        "alta":                ("d4edda", "155724"),
        "media":               ("fff3cd", "856404"),
        "bassa":               ("f8d7da", "721c24"),
        "full_remote":         ("d4edda", "155724"),
        "ibrido":              ("cce5ff", "004085"),
        "in_presenza":         ("f8d7da", "721c24"),
    }
    bg, fg = colori.get(valore, ("e2e3e5", "383d41"))
    return f'<span style="background:#{bg};color:#{fg};padding:2px 8px;border-radius:4px;font-size:12px">{valore}</span>'


def genera_report_html(offerte_approvate: list, analisi_map: dict):
    """
    Genera un report HTML con tutte le offerte approvate
    e la relativa analisi aziendale.
    """
    data_oggi = datetime.now().strftime("%Y-%m-%d")
    nome_file = os.path.join(REPORTS_DIR, f"report_{data_oggi}.html")

    righe_offerte = ""
    for o in offerte_approvate:
        analisi   = analisi_map.get(o["azienda"], {})
        temi      = analisi.get("temi", {})
        orientam  = analisi.get("orientamento", "non_determinabile")
        sc        = analisi.get("score_cultura", "—")
        affidab   = analisi.get("affidabilita_analisi", "—")
        sintesi   = analisi.get("sintesi_generale", "Analisi non disponibile.")
        raccom    = analisi.get("raccomandazione", "—")

        righe_offerte += f"""
        <div class="card">
          <div class="card-header">
            <div>
              <h2>{o['titolo']}</h2>
              <span class="azienda">{o['azienda']}</span>
              <span class="location">📍 {o.get('location','—')}</span>
            </div>
            <div class="score-box">
              <div class="score-num">{o.get('score','—')}</div>
              <div class="score-label">match score</div>
            </div>
          </div>

          <div class="section">
            <h3>Perché candidarsi</h3>
            <ul>{''.join(f"<li>{m}</li>" for m in o.get('motivi_match',[]))}</ul>
          </div>

          {"" if not o.get('red_flags') else f'''
          <div class="section red">
            <h3>⚠ Red flags</h3>
            <ul>{"".join(f"<li>{r}</li>" for r in o.get("red_flags",[]))}</ul>
          </div>'''}

          <div class="section">
            <h3>Analisi aziendale — {o['azienda']}</h3>
            <div class="analisi-grid">
              <div><b>Orientamento</b><br>{_badge(orientam)}</div>
              <div><b>Score cultura</b><br><strong>{sc}/100</strong></div>
              <div><b>DEI</b><br>{_badge(temi.get('DEI',{}).get('valutazione','insufficiente_info'))}</div>
              <div><b>ESG</b><br>{_badge(temi.get('ESG',{}).get('valutazione','insufficiente_info'))}</div>
              <div><b>Smart working</b><br>{_badge(temi.get('smart_working',{}).get('politica','non_determinabile'))}</div>
              <div><b>Controversie</b><br>{_badge('negativa' if temi.get('controversie',{}).get('presenti') else 'positiva')}</div>
              <div><b>Affidabilità analisi</b><br>{_badge(affidab)}</div>
            </div>
            <p class="sintesi">{sintesi}</p>
            <p class="raccom"><b>Raccomandazione valoriale:</b> {raccom}</p>
          </div>

          <div class="footer-card">
            <a href="{o['link']}" target="_blank">🔗 Vedi offerta</a>
            &nbsp;|&nbsp; Fonte: {o.get('fonte','—')}
          </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Job Bot Report — {data_oggi}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f4f5f7; color: #172b4d; padding: 24px; }}
  h1   {{ font-size: 22px; margin-bottom: 4px; }}
  h2   {{ font-size: 17px; font-weight: 600; margin-bottom: 4px; }}
  h3   {{ font-size: 13px; font-weight: 600; color: #5e6c84;
         text-transform: uppercase; letter-spacing: .5px; margin-bottom: 8px; }}
  .meta {{ color: #5e6c84; font-size: 13px; margin-bottom: 24px; }}
  .card {{ background: #fff; border-radius: 8px; border: 1px solid #dfe1e6;
           padding: 20px 24px; margin-bottom: 20px; }}
  .card-header {{ display: flex; justify-content: space-between;
                  align-items: flex-start; margin-bottom: 16px; }}
  .azienda {{ font-size: 14px; font-weight: 500; color: #0052cc; margin-right: 12px; }}
  .location {{ font-size: 13px; color: #5e6c84; }}
  .score-box {{ text-align: center; background: #0052cc; color: #fff;
                border-radius: 8px; padding: 10px 16px; min-width: 72px; }}
  .score-num   {{ font-size: 26px; font-weight: 700; line-height: 1; }}
  .score-label {{ font-size: 11px; opacity: .8; margin-top: 2px; }}
  .section  {{ margin-bottom: 14px; padding: 12px 14px;
               background: #f8f9fa; border-radius: 6px; }}
  .section.red {{ background: #fff5f5; border-left: 3px solid #e53e3e; }}
  .section ul {{ padding-left: 18px; font-size: 14px; line-height: 1.7; }}
  .analisi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px,1fr));
                   gap: 10px; margin-bottom: 10px; font-size: 13px; }}
  .analisi-grid div {{ background: #fff; border: 1px solid #dfe1e6;
                       border-radius: 6px; padding: 8px 10px; }}
  .sintesi {{ font-size: 13px; line-height: 1.6; color: #333;
              margin-top: 8px; }}
  .raccom  {{ font-size: 13px; margin-top: 6px; color: #333; }}
  .footer-card {{ margin-top: 12px; font-size: 13px; color: #5e6c84; }}
  .footer-card a {{ color: #0052cc; text-decoration: none; }}
  .empty {{ text-align: center; padding: 48px; color: #5e6c84; }}
</style>
</head>
<body>
  <h1>🤖 Job Bot — Report offerte</h1>
  <p class="meta">Generato il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}
     &nbsp;·&nbsp; {len(offerte_approvate)} offerte approvate</p>

  {"".join([righe_offerte]) if offerte_approvate else '<div class="empty">Nessuna offerta approvata in questo ciclo.</div>'}

</body>
</html>"""

    with open(nome_file, "w", encoding="utf-8") as f:
        f.write(html)

    log(f"Report salvato: {nome_file}")
    return nome_file


def parse_args():
    p = argparse.ArgumentParser(description="Job Application Bot")
    p.add_argument(
        "comando",
        nargs="?",
        default="ciclo",
        choices=["ciclo", "scrape", "valuta", "candida", "analizza", "stats", "schedule"],
        help=(
            "ciclo    = pipeline completo (default)\n"
            "scrape   = solo scraping\n"
            "valuta   = solo valutazione AI\n"
            "candida  = solo candidature\n"
            "analizza = analisi aziendale interattiva\n"
            "stats    = mostra statistiche DB\n"
            "schedule = avvia scheduler automatico"
        ),
    )
    p.add_argument("--azienda", help="Nome azienda da analizzare (usato con 'analizza')")
    return p.parse_args()



def avvia_scheduler():
    scheduler = BlockingScheduler(timezone="Europe/Rome")

    for orario in SCHEDULE_ORE:
        ora, minuto = orario.split(":")
        scheduler.add_job(
            ciclo_completo,
            trigger="cron",
            hour=int(ora),
            minute=int(minuto),
            id=f"ciclo_{orario}",
        )
        log(f"Ciclo schedulato alle {orario}")

    log("Scheduler avviato. Premi Ctrl+C per fermare.")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        log("Scheduler fermato.")


#Entry point
if __name__ == "__main__":
    intestazione()
    assicura_cartelle()
    init_db()

    args = parse_args()

    if args.comando == "ciclo":
        ciclo_completo()

    elif args.comando == "scrape":
        log("Avvio solo scraping...")
        scrapa_tutto()

    elif args.comando == "valuta":
        log("Avvio solo valutazione AI...")
        approvate = valuta_tutte()
        print(riepilogo_giornaliero(approvate))

    elif args.comando == "candida":
        log("Avvio solo candidature...")
        candidatura_batch()

    elif args.comando == "analizza":
        azienda = args.azienda or input("Nome azienda da analizzare: ").strip()
        analisi = analizza_azienda(azienda, forza_rianalisi=True)
        stampa_report(azienda, analisi)

    elif args.comando == "stats":
        stats()

    elif args.comando == "schedule":
        avvia_scheduler()