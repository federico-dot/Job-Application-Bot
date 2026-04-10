# 🤖 Job Application Bot

Bot Python che automatizza la ricerca, il filtraggio e l'invio di candidature di lavoro, con analisi della posizione politica e culturale delle aziende.

## Funzionalità

- **Scraping** offerte da LinkedIn e Indeed
- **Filtraggio AI** con Claude: score di compatibilità con il tuo CV
- **Cover letter** personalizzata generata per ogni offerta
- **Analisi aziendale**: orientamento politico, DEI, ESG, smart working, controversie
- **Candidatura automatica** tramite browser headless
- **Dashboard HTML** con report giornalieri
- **Scheduler** automatico configurabile

## Struttura

```
job_bot/
├── assets/cv         #cv in PDF
├── main.py           # orchestratore + CLI
├── scraper.py        # scraping LinkedIn e Indeed
├── ai_filter.py      # valutazione offerte e cover letter
├── applicator.py     # invio candidature automatiche
├── analyzer.py       # analisi posizione aziendale
├── database.py       # log SQLite
├── config.py         # configurazione (CV, keyword, soglie)
└── reports/
    └── template.html # dashboard interattiva
```

## Installazione

```bash
git clone https://github.com/federico-dot/Job-Application-Bot.git
cd job-bot

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install anthropic playwright apscheduler requests
playwright install chromium
```

## Configurazione

Apri `config.py` e imposta:

```python
ANTHROPIC_API_KEY = "sk-ant-..."   # chiave Anthropic
CV_TESTO = """..."""                # il tuo CV in testo
KEYWORDS_RICERCA = ["python developer", "data analyst"]
LOCATIONS = ["Milano", "Roma", "Remote"]
SCORE_MINIMO = 65                  # soglia minima per candidarsi
INVIA_CANDIDATURE = False          # True per inviare davvero
```

## Utilizzo

```bash
# Pipeline completo
python main.py ciclo

# Solo scraping
python main.py scrape

# Solo valutazione AI
python main.py valuta

# Solo candidature
python main.py candida

# Analisi singola azienda
python main.py analizza --azienda "Enel"

# Statistiche database
python main.py stats

# Avvia scheduler automatico
python main.py schedule
```

## Workflow consigliato

1. Imposta `INVIA_CANDIDATURE = False` in `config.py`
2. Esegui `python main.py ciclo` e controlla il report in `reports/`
3. Verifica che le offerte filtrate e le cover letter siano di qualità
4. Quando sei soddisfatto imposta `INVIA_CANDIDATURE = True`
5. Avvia `python main.py schedule` per girare in automatico

## Note

- Le pause anti-ban sono configurate in `config.py` (`PAUSA_TRA_CANDIDATURE`)
- LinkedIn blocca lo scraping aggressivo — considera [Apify](https://apify.com) per uso intensivo
- Il database SQLite salva tutto: offerte, candidature, analisi aziendali
- Le analisi aziendali vengono cachate — non vengono rifatte ad ogni ciclo

## Dipendenze

| Libreria | Uso |
|----------|-----|
| `anthropic` | Valutazione offerte e cover letter |
| `playwright` | Scraping e candidature automatiche |
| `apscheduler` | Scheduling automatico |
| `requests` | Fetch notizie aziendali |

## ⚠️ Disclaimer

Questo bot è per uso personale. Lo scraping automatico può violare i termini di servizio di LinkedIn e Indeed. Usalo responsabilmente e controlla sempre le candidature prima di inviarle.
