import requests
import json
from datetime import datetime
from config import ANTHROPIC_API_KEY, NEWS_API_KEY, MAX_NOTIZIE, TEMI_ANALISI
from database import salva_analisi_azienda, get_analisi_azienda
import anthropic

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def cerca_notizie_newsapi(azienda: str) -> list[dict]:
    """
    Cerca notizie recenti sull'azienda via NewsAPI.
    Richiede NEWS_API_KEY in config.py (piano gratuito: 100 req/giorno).
    """
    if not NEWS_API_KEY:
        print("[Analyzer] NEWS_API_KEY non impostata, salto NewsAPI.")
        return []

    url = "https://newsapi.org/v2/everything"
    params = {
        "q":        f'"{azienda}"',
        "language": "it",
        "sortBy":   "publishedAt",
        "pageSize": MAX_NOTIZIE,
        "apiKey":   NEWS_API_KEY,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        articoli = r.json().get("articles", [])
        return [
            {
                "titolo":    a["title"],
                "fonte":     a["source"]["name"],
                "data":      a["publishedAt"][:10],
                "sommario":  a.get("description") or "",
                "url":       a["url"],
            }
            for a in articoli
            if a.get("title") and "[Removed]" not in a.get("title", "")
        ]
    except Exception as e:
        print(f"[Analyzer] Errore NewsAPI: {e}")
        return []


def cerca_notizie_gnews(azienda: str) -> list[dict]:
    """
    Alternativa gratuita a NewsAPI: GNews (100 req/giorno senza chiave).
    """
    url = "https://gnews.io/api/v4/search"
    params = {
        "q":        azienda,
        "lang":     "it",
        "max":      MAX_NOTIZIE,
        "sortby":   "publishedAt",
        "token":    "free",  
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return []
        articoli = r.json().get("articles", [])
        return [
            {
                "titolo":   a["title"],
                "fonte":    a["source"]["name"],
                "data":     a["publishedAt"][:10],
                "sommario": a.get("description") or "",
                "url":      a["url"],
            }
            for a in articoli
        ]
    except Exception as e:
        print(f"[Analyzer] Errore GNews: {e}")
        return []


def cerca_glassdoor_rating(azienda: str) -> float | None:
    """
    Placeholder: recupera rating Glassdoor via scraping o API di terze parti.
    Integra qui Apify actor 'glassdoor-scraper' se vuoi dati reali.
    Restituisce float (es. 3.8) o None se non trovato.
    """
    print(f"[Analyzer] Glassdoor rating per '{azienda}': richiede integrazione Apify.")
    return None


def raccogli_dati_azienda(azienda: str) -> dict:
    """
    Aggrega tutte le fonti disponibili per un'azienda.
    Restituisce un dict con notizie, rating, fonti usate.
    """
    print(f"[Analyzer] Raccolta dati per: {azienda}")

    notizie = cerca_notizie_newsapi(azienda)

    if not notizie:
        notizie = cerca_notizie_gnews(azienda)

    rating = cerca_glassdoor_rating(azienda)

    fonti_usate = list({n["url"] for n in notizie})

    return {
        "notizie":         notizie,
        "rating_glassdoor": rating,
        "fonti_usate":     fonti_usate,
    }


# Analisi AI 

def _formatta_notizie(notizie: list[dict]) -> str:
    if not notizie:
        return "Nessuna notizia recente trovata."
    righe = []
    for n in notizie:
        righe.append(
            f"[{n['data']}] {n['fonte']}: {n['titolo']}\n  {n['sommario']}"
        )
    return "\n\n".join(righe)


def analizza_con_claude(azienda: str, dati: dict) -> dict:
    """
    Manda i dati raccolti a Claude e ottiene un'analisi strutturata
    della posizione politica, cultura e valori aziendali.
    """
    temi_str = "\n".join(f"- {t}" for t in TEMI_ANALISI)
    notizie_str = _formatta_notizie(dati["notizie"])

    prompt = f"""Sei un analista specializzato in cultura aziendale e posizionamento valoriale delle imprese.

Analizza l'azienda "{azienda}" basandoti sulle informazioni disponibili qui sotto.

=== NOTIZIE E FONTI RACCOLTE ===
{notizie_str}

=== TEMI DA ANALIZZARE ===
{temi_str}

=== ISTRUZIONI ===
Produci un'analisi obiettiva e basata sui fatti disponibili.
Se non hai informazioni sufficienti su un tema, dichiaralo esplicitamente.
Non fare supposizioni non supportate da dati.

Rispondi ESCLUSIVAMENTE con un oggetto JSON valido con questa struttura:

{{
  "orientamento": "<una di: progressista | conservatore | centrista | neutro | non_determinabile>",
  "score_cultura": <intero 0-100, dove 100 = cultura eccellente>,
  "settore": "<settore principale dell'azienda>",
  "dimensione": "<una di: startup | PMI | grande_azienda | multinazionale>",
  "sede_principale": "<città, paese>",
  "sintesi_generale": "<paragrafo di 3-5 righe di sintesi>",
  "temi": {{
    "DEI": {{
      "valutazione": "<positiva | negativa | neutra | insufficiente_info>",
      "dettaglio": "<2-3 righe>"
    }},
    "ESG": {{
      "valutazione": "<positiva | negativa | neutra | insufficiente_info>",
      "dettaglio": "<2-3 righe>"
    }},
    "leadership": {{
      "valutazione": "<positiva | negativa | neutra | insufficiente_info>",
      "dettaglio": "<2-3 righe>"
    }},
    "cultura_interna": {{
      "valutazione": "<positiva | negativa | neutra | insufficiente_info>",
      "dettaglio": "<2-3 righe>"
    }},
    "controversie": {{
      "presenti": <true | false>,
      "dettaglio": "<2-3 righe o 'Nessuna controversia rilevata'>"
    }},
    "smart_working": {{
      "politica": "<full_remote | ibrido | in_presenza | non_determinabile>",
      "dettaglio": "<1-2 righe>"
    }}
  }},
  "raccomandazione": "<frase finale: vale la pena candidarsi da un punto di vista valoriale?>",
  "affidabilita_analisi": "<alta | media | bassa — in base alla quantità di dati disponibili>"
}}
"""

    try:
        risposta = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        testo = risposta.content[0].text.strip()

        inizio = testo.index("{")
        fine   = testo.rindex("}") + 1
        return json.loads(testo[inizio:fine])

    except Exception as e:
        print(f"[Analyzer] Errore analisi Claude per '{azienda}': {e}")
        return {}



def analizza_azienda(azienda: str, forza_rianalisi=False) -> dict:
    """
    Funzione principale: analizza un'azienda e salva nel DB.
    Se l'analisi esiste già e non forzi, la restituisce dal DB.
    """
    if not forza_rianalisi:
        esistente = get_analisi_azienda(azienda)
        if esistente:
            print(f"[Analyzer] Analisi già presente per '{azienda}', recupero dal DB.")
            return esistente

    dati = raccogli_dati_azienda(azienda)

    analisi = analizza_con_claude(azienda, dati)

    if not analisi:
        print(f"[Analyzer] Analisi fallita per '{azienda}'.")
        return {}


    salva_analisi_azienda(
        nome              = azienda,
        analisi_politica  = analisi.get("sintesi_generale", ""),
        orientamento      = analisi.get("orientamento", "non_determinabile"),
        score_cultura     = analisi.get("score_cultura"),
        rating_glassdoor  = dati.get("rating_glassdoor"),
        settore           = analisi.get("settore"),
        dimensione        = analisi.get("dimensione"),
        sede              = analisi.get("sede_principale"),
        fonti_usate       = dati.get("fonti_usate", []),
    )

    print(f"[Analyzer] Analisi completata per '{azienda}': "
          f"orientamento={analisi.get('orientamento')} | "
          f"score_cultura={analisi.get('score_cultura')}")

    return analisi


def analizza_batch(nomi_aziende: list[str]) -> dict[str, dict]:
    """
    Analizza una lista di aziende e restituisce un dizionario
    nome_azienda → risultato_analisi.
    """
    risultati = {}
    for nome in nomi_aziende:
        risultati[nome] = analizza_azienda(nome)
    return risultati



def stampa_report(azienda: str, analisi: dict):
    if not analisi:
        print(f"Nessuna analisi disponibile per {azienda}.")
        return

    temi = analisi.get("temi", {})
    print(f"""
╔══════════════════════════════════════════════════╗
  ANALISI AZIENDALE: {azienda}
╚══════════════════════════════════════════════════╝

  Orientamento    : {analisi.get('orientamento', 'N/D')}
  Score cultura   : {analisi.get('score_cultura', 'N/D')}/100
  Settore         : {analisi.get('settore', 'N/D')}
  Dimensione      : {analisi.get('dimensione', 'N/D')}
  Sede            : {analisi.get('sede_principale', 'N/D')}
  Affidabilità    : {analisi.get('affidabilita_analisi', 'N/D')}

  SINTESI
  {analisi.get('sintesi_generale', 'N/D')}

  DEI             : {temi.get('DEI', {}).get('valutazione', 'N/D')}
  ESG             : {temi.get('ESG', {}).get('valutazione', 'N/D')}
  Leadership      : {temi.get('leadership', {}).get('valutazione', 'N/D')}
  Cultura interna : {temi.get('cultura_interna', {}).get('valutazione', 'N/D')}
  Smart working   : {temi.get('smart_working', {}).get('politica', 'N/D')}
  Controversie    : {'Sì' if temi.get('controversie', {}).get('presenti') else 'No'}

  RACCOMANDAZIONE
  {analisi.get('raccomandazione', 'N/D')}
""")


if __name__ == "__main__":
    from database import init_db
    init_db()

    test_azienda = "Enel"
    analisi = analizza_azienda(test_azienda)
    stampa_report(test_azienda, analisi)