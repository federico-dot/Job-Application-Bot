import sqlite3
import json
from datetime import datetime
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  
    return conn


def init_db():
    """Crea le tabelle se non esistono ancora."""
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS offerte (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            titolo        TEXT NOT NULL,
            azienda       TEXT NOT NULL,
            link          TEXT UNIQUE NOT NULL,
            fonte         TEXT,
            location      TEXT,
            descrizione   TEXT,
            data_trovata  TEXT DEFAULT (datetime('now')),
            score_ai      INTEGER,
            motivi_match  TEXT,   -- JSON list
            red_flags     TEXT,   -- JSON list
            candidare     INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS candidature (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            offerta_id      INTEGER REFERENCES offerte(id),
            data_invio      TEXT DEFAULT (datetime('now')),
            cover_letter    TEXT,
            cv_versione     TEXT,
            stato           TEXT DEFAULT 'inviata',  -- inviata | risposta | colloquio | rifiutata
            note            TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS aziende (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            nome                TEXT UNIQUE NOT NULL,
            settore             TEXT,
            dimensione          TEXT,
            sede                TEXT,
            analisi_politica    TEXT,   -- testo libero generato da AI
            orientamento        TEXT,   -- progressista / conservatore / neutro / non determinabile
            score_cultura       INTEGER,
            rating_glassdoor    REAL,
            fonti_usate         TEXT,   -- JSON list di URL
            data_analisi        TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Tabelle inizializzate.")


# ── OFFERTE ──────────────────────────────────────────────────

def salva_offerta(titolo, azienda, link, fonte=None, location=None, descrizione=None):
    """Inserisce un'offerta. Ignora duplicati (stesso link)."""
    conn = get_conn()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO offerte (titolo, azienda, link, fonte, location, descrizione)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (titolo, azienda, link, fonte, location, descrizione))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Errore salva_offerta: {e}")
        return False
    finally:
        conn.close()


def aggiorna_score(link, score, motivi, red_flags, candidare):
    conn = get_conn()
    conn.execute("""
        UPDATE offerte
        SET score_ai     = ?,
            motivi_match = ?,
            red_flags    = ?,
            candidare    = ?
        WHERE link = ?
    """, (score, json.dumps(motivi), json.dumps(red_flags), int(candidare), link))
    conn.commit()
    conn.close()


def offerte_da_valutare():
    """Restituisce offerte non ancora valutate dall'AI."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM offerte WHERE score_ai IS NULL"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def offerte_da_candidare():
    """Restituisce offerte approvate ma non ancora candidato."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT o.* FROM offerte o
        LEFT JOIN candidature c ON c.offerta_id = o.id
        WHERE o.candidare = 1 AND c.id IS NULL
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def link_gia_visto(link):
    conn = get_conn()
    row = conn.execute("SELECT id FROM offerte WHERE link = ?", (link,)).fetchone()
    conn.close()
    return row is not None



def salva_candidatura(offerta_id, cover_letter, cv_versione="v1"):
    conn = get_conn()
    conn.execute("""
        INSERT INTO candidature (offerta_id, cover_letter, cv_versione)
        VALUES (?, ?, ?)
    """, (offerta_id, cover_letter, cv_versione))
    conn.commit()
    conn.close()


def aggiorna_stato_candidatura(offerta_id, stato, note=None):
    conn = get_conn()
    conn.execute("""
        UPDATE candidature SET stato = ?, note = ?
        WHERE offerta_id = ?
    """, (stato, note, offerta_id))
    conn.commit()
    conn.close()


# ── AZIENDE ──────────────────────────────────────────────────

def salva_analisi_azienda(nome, analisi_politica, orientamento,
                           score_cultura=None, rating_glassdoor=None,
                           settore=None, dimensione=None, sede=None,
                           fonti_usate=None):
    conn = get_conn()
    conn.execute("""
        INSERT INTO aziende
            (nome, settore, dimensione, sede, analisi_politica,
             orientamento, score_cultura, rating_glassdoor, fonti_usate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(nome) DO UPDATE SET
            analisi_politica = excluded.analisi_politica,
            orientamento     = excluded.orientamento,
            score_cultura    = excluded.score_cultura,
            rating_glassdoor = excluded.rating_glassdoor,
            data_analisi     = datetime('now')
    """, (nome, settore, dimensione, sede, analisi_politica,
          orientamento, score_cultura, rating_glassdoor,
          json.dumps(fonti_usate or [])))
    conn.commit()
    conn.close()


def get_analisi_azienda(nome):
    """Recupera analisi già fatta (evita di rifarla ogni volta)."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM aziende WHERE nome = ?", (nome,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None



def stats():
    conn = get_conn()
    totale       = conn.execute("SELECT COUNT(*) FROM offerte").fetchone()[0]
    valutate     = conn.execute("SELECT COUNT(*) FROM offerte WHERE score_ai IS NOT NULL").fetchone()[0]
    approvate    = conn.execute("SELECT COUNT(*) FROM offerte WHERE candidare = 1").fetchone()[0]
    candidature  = conn.execute("SELECT COUNT(*) FROM candidature").fetchone()[0]
    risposte     = conn.execute("SELECT COUNT(*) FROM candidature WHERE stato != 'inviata'").fetchone()[0]
    conn.close()

    print(f"""
┌─────────────────────────────┐
│  📊  Statistiche job bot    │
├─────────────────────────────┤
│  Offerte trovate  : {totale:<8}│
│  Valutate AI      : {valutate:<8}│
│  Approvate        : {approvate:<8}│
│  Candidature      : {candidature:<8}│
│  Risposte ricevute: {risposte:<8}│
└─────────────────────────────┘
""")


if __name__ == "__main__":
    init_db()
    stats()