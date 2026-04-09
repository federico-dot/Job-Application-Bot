import json
import anthropic
from config import ANTHROPIC_API_KEY, CV_TESTO, SCORE_MINIMO
from database import offerte_da_valutare, aggiorna_score

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def chiedi_claude(prompt, max_tokens=1000):
    """Chiamata base a Claude. Restituisce il testo della risposta."""
    risposta = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return risposta.content[0].text.strip()


def parse_json_risposta(testo):
    """
    Estrae il JSON dalla risposta di Claude anche se contiene
    testo prima o dopo le parentesi graffe.
    """
    try:
        inizio = testo.index("{")
        fine   = testo.rindex("}") + 1
        return json.loads(testo[inizio:fine])
    except (ValueError, json.JSONDecodeError) as e:
        print(f"[AI Filter] Errore parsing JSON: {e}")
        print(f"[AI Filter] Testo ricevuto: {testo[:300]}")
        return None



def valuta_offerta(offerta: dict) -> dict | None:
    """
    Manda l'offerta a Claude insieme al CV e ottiene:
    - score 0-100
    - motivi di match
    - red flags
    - raccomandazione candidare sì/no

    Restituisce il dict con i risultati o None in caso di errore.
    """
    prompt = f"""Sei un career coach esperto. Analizza questa offerta di lavoro rispetto al CV fornito.

=== CV ===
{CV_TESTO}

=== OFFERTA ===
Titolo:   {offerta.get('titolo', 'N/D')}
Azienda:  {offerta.get('azienda', 'N/D')}
Location: {offerta.get('location', 'N/D')}
Fonte:    {offerta.get('fonte', 'N/D')}

Descrizione:
{offerta.get('descrizione', 'Descrizione non disponibile.')[:2500]}

=== ISTRUZIONI ===
Rispondi ESCLUSIVAMENTE con un oggetto JSON valido, senza testo prima o dopo.
Il JSON deve avere esattamente questi campi:

{{
  "score": <intero 0-100, compatibilità complessiva>,
  "motivi_match": [<lista di stringhe, punti di forza del match>],
  "red_flags": [<lista di stringhe, criticità o dubbi>],
  "candidare": <true se score >= {SCORE_MINIMO}, false altrimenti>,
  "sintesi": "<frase breve di 1-2 righe sul match>"
}}
"""

    testo = chiedi_claude(prompt, max_tokens=800)
    risultato = parse_json_risposta(testo)

    if risultato:
        print(
            f"[AI Filter] '{offerta['titolo']}' @ {offerta['azienda']} "
            f"→ score {risultato.get('score', '?')} "
            f"| candidare: {risultato.get('candidare', '?')}"
        )
    return risultato



def genera_cover_letter(offerta: dict) -> str:
    """
    Genera una cover letter personalizzata per l'offerta.
    Tono professionale, in italiano, circa 200-250 parole.
    """
    prompt = f"""Sei un esperto di scrittura professionale. Scrivi una cover letter in italiano.

=== CV DEL CANDIDATO ===
{CV_TESTO}

=== OFFERTA DI LAVORO ===
Titolo:   {offerta.get('titolo', 'N/D')}
Azienda:  {offerta.get('azienda', 'N/D')}
Location: {offerta.get('location', 'N/D')}

Descrizione offerta:
{offerta.get('descrizione', '')[:2000]}

=== ISTRUZIONI ===
- Lunghezza: 200-250 parole
- Tono: professionale ma non rigido, autentico
- Struttura: apertura forte → valore che porto → interesse specifico per l'azienda → chiusura
- Personalizza in base alla descrizione dell'offerta
- Non usare frasi banali come "mi permetto di candidarmi"
- Inizia direttamente con il corpo della lettera (senza "Oggetto:" o intestazione)
- Firma con il nome del candidato dal CV
"""

    cover = chiedi_claude(prompt, max_tokens=600)
    print(f"[AI Filter] Cover letter generata per '{offerta['titolo']}' @ {offerta['azienda']}")
    return cover



def valuta_tutte():
    """
    Recupera dal DB tutte le offerte non ancora valutate,
    le manda a Claude e salva i risultati.
    Restituisce le offerte approvate (candidare=True).
    """
    offerte = offerte_da_valutare()

    if not offerte:
        print("[AI Filter] Nessuna offerta da valutare.")
        return []

    print(f"[AI Filter] Valuto {len(offerte)} offerte...")
    approvate = []

    for offerta in offerte:
        try:
            risultato = valuta_offerta(offerta)

            if not risultato:
                continue

            aggiorna_score(
                link      = offerta["link"],
                score     = risultato["score"],
                motivi    = risultato.get("motivi_match", []),
                red_flags = risultato.get("red_flags", []),
                candidare = risultato.get("candidare", False),
            )

            if risultato.get("candidare"):
                approvate.append({**offerta, **risultato})

        except Exception as e:
            print(f"[AI Filter] Errore su '{offerta.get('titolo')}': {e}")

    print(f"[AI Filter] Approvate: {len(approvate)} / {len(offerte)}")
    return approvate



def riepilogo_giornaliero(offerte_approvate: list) -> str:
    """
    Genera un breve riepilogo delle offerte approvate,
    utile da stampare o inviare via email/Telegram.
    """
    if not offerte_approvate:
        return "Nessuna nuova offerta approvata oggi."

    elenco = "\n".join(
        f"- {o['titolo']} @ {o['azienda']} (score: {o.get('score', '?')})"
        for o in offerte_approvate
    )

    prompt = f"""Scrivi un brevissimo riepilogo (max 5 righe) delle seguenti offerte di lavoro
approvate oggi dal bot di candidatura. Tono diretto, evidenzia le più promettenti.

{elenco}
"""
    return chiedi_claude(prompt, max_tokens=300)


if __name__ == "__main__":
    from database import init_db
    init_db()
    approvate = valuta_tutte()
    if approvate:
        print("\n=== RIEPILOGO ===")
        print(riepilogo_giornaliero(approvate))