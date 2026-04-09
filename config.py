
# ── API Keys ─────────────────────────────────────────────────
ANTHROPIC_API_KEY = ""   # chiave Anthropic
NEWS_API_KEY      = ""     #  newsapi.org per notizie aziendali

# ── Il tuo profilo ───────────────────────────────────────────
CV_TESTO = """
NOME COGNOME
email@esempio.com | LinkedIn: linkedin.com/in/tuoprofilo

ESPERIENZE
- 2021-oggi  | Azienda X | Ruolo Y
  Descrizione breve delle responsabilità.

- 2018-2021  | Azienda Z | Ruolo W
  Descrizione breve delle responsabilità.

FORMAZIONE
- Laurea Magistrale in ... | Università di ... | 2018

COMPETENZE
Python, SQL, Project Management, ...

LINGUE
Italiano (madrelingua), Inglese (C1)
"""

# ── Criteri di ricerca ───────────────────────────────────────
KEYWORDS_RICERCA = [
    "data analyst",
    "python developer",
    "backend engineer",
    "software developer",
    "junior developer"
]

LOCATIONS = [
    "Italia",
    "Milano",
    "Roma",
    "Firenze"
    "Remote",
]

#Se non e almeno 50% non matcha tanto saresti troppo inadeguato
SCORE_MINIMO = 65  

# ── Fonti da scraping ────────────────────────────────────────
FONTI_ABILITATE = {
    "linkedin":  True,
    "indeed":    True,
    "infojobs":  False,  
    "glassdoor": False,   
}

# ── Candidatura ──────────────────────────────────────────────
# Se FALSO NON invia candidature 
INVIA_CANDIDATURE = False

# Antiban in secondi
PAUSA_TRA_CANDIDATURE = 30

CV_PDF_PATH = "assets/cv.pdf"

# ── Analisi aziendale ────────────────────────────────────────
MAX_NOTIZIE = 10

# Temi analisi
TEMI_ANALISI = [
    "diversità e inclusione (DEI)",
    "ambiente e sostenibilità (ESG)",
    "posizione politica del CEO",
    "cultura aziendale",
    "controversie recenti",
    "lavoro da remoto / smart working",
]

# ── Database & Report ────────────────────────────────────────
DB_PATH      = "job_bot.db"
REPORTS_DIR  = "reports"

# ── Scheduling ───────────────────────────────────────────────
# Quando funziona il bot
SCHEDULE_ORE = ["09:00", "14:00", "18:00"]