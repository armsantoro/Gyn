"""
Modulo database per GynTracker - Gestione interventi ginecologici.
Gestisce la creazione dello schema SQLite, il seeding dei dati
e tutte le operazioni CRUD.
"""

import sqlite3
import os
import shutil
from datetime import datetime, date, timedelta
from pathlib import Path
import random

DB_NAME = "gyn_tracker.db"
BACKUP_DIR = "backup"


def get_db_path():
    """Restituisce il percorso del database nella directory dell'applicazione."""
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, DB_NAME)


def get_connection():
    """Crea e restituisce una connessione al database SQLite."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """
    Inizializza il database: crea le tabelle, gli indici,
    popola le categorie e inserisce dati di esempio se il DB è nuovo.
    Restituisce True se è il primo avvio.
    """
    first_run = not os.path.exists(get_db_path())
    conn = get_connection()
    _create_tables(conn)
    _create_indexes(conn)
    if first_run:
        _seed_categorie(conn)
        _seed_interventi_esempio(conn)
    conn.close()
    return first_run


# ---------------------------------------------------------------------------
# Creazione schema
# ---------------------------------------------------------------------------

def _create_tables(conn):
    """Crea tutte le tabelle dello schema."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS interventi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_intervento DATE NOT NULL,
            codice_paziente TEXT,
            eta_paziente INTEGER,
            categoria TEXT,
            sottocategoria TEXT,
            procedura_specifica TEXT,
            codice_icd10 TEXT,
            urgenza TEXT DEFAULT 'elettiva',
            tecnica TEXT,
            chirurgo_principale TEXT,
            assistenti TEXT,
            durata_prevista_min INTEGER,
            durata_effettiva_min INTEGER,
            classe_asa INTEGER CHECK(classe_asa BETWEEN 1 AND 5),
            complicanze TEXT,
            grado_clavien_dindo INTEGER CHECK(grado_clavien_dindo BETWEEN 0 AND 5),
            degenza_prevista_giorni INTEGER,
            degenza_effettiva_giorni INTEGER,
            riammissione_30gg BOOLEAN DEFAULT 0,
            esito_istologico TEXT,
            note TEXT,
            data_inserimento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS categorie (
            id INTEGER PRIMARY KEY,
            categoria TEXT NOT NULL,
            sottocategoria TEXT NOT NULL,
            procedura_esempio TEXT
        );

        CREATE TABLE IF NOT EXISTS backup_log (
            id INTEGER PRIMARY KEY,
            data_backup TIMESTAMP,
            numero_record INTEGER,
            path_file TEXT
        );

        CREATE TABLE IF NOT EXISTS impostazioni (
            chiave TEXT PRIMARY KEY,
            valore TEXT
        );
    """)
    conn.commit()


def _create_indexes(conn):
    """Crea gli indici per ottimizzare le query frequenti."""
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_interventi_data
            ON interventi(data_intervento);
        CREATE INDEX IF NOT EXISTS idx_interventi_categoria
            ON interventi(categoria);
        CREATE INDEX IF NOT EXISTS idx_interventi_chirurgo
            ON interventi(chirurgo_principale);
        CREATE INDEX IF NOT EXISTS idx_interventi_urgenza
            ON interventi(urgenza);
        CREATE INDEX IF NOT EXISTS idx_interventi_tecnica
            ON interventi(tecnica);
    """)
    conn.commit()


# ---------------------------------------------------------------------------
# Seeding categorie
# ---------------------------------------------------------------------------

CATEGORIE_DATA = [
    # Oncologia ginecologica
    ("oncologica", "Utero", "Isterectomia radicale"),
    ("oncologica", "Utero", "Staging linfonodale"),
    ("oncologica", "Utero", "Linfadenectomia pelvica/lomboaortica"),
    ("oncologica", "Ovaio", "Cistectomia oncologica"),
    ("oncologica", "Ovaio", "Annessiectomia"),
    ("oncologica", "Ovaio", "Debulking"),
    ("oncologica", "Ovaio", "HIPEC"),
    ("oncologica", "Cervice", "Conizzazione LEEP/laser"),
    ("oncologica", "Cervice", "Tracheliectomia"),
    ("oncologica", "Cervice", "Isterectomia radicale"),
    ("oncologica", "Endometrio", "Isterectomia staging"),
    ("oncologica", "Endometrio", "Biopsia linfonodo sentinella"),
    ("oncologica", "Vulva/Vagina", "Vulvectomia"),
    ("oncologica", "Vulva/Vagina", "Linfoadenectomia inguinale"),

    # Patologia benigna
    ("benigna", "Fibromatosi", "Miomectomia"),
    ("benigna", "Fibromatosi", "Isterectomia"),
    ("benigna", "Endometriosi", "Exeresi cisti endometriosica"),
    ("benigna", "Endometriosi", "Nodulectomia"),
    ("benigna", "Endometriosi", "Neurectomia presacrale"),
    ("benigna", "Uroginecologia", "Colposacropessi"),
    ("benigna", "Uroginecologia", "TOT/TVT"),
    ("benigna", "Uroginecologia", "Cistopessi"),
    ("benigna", "Uroginecologia", "Colpoperineoplastica"),
    ("benigna", "Annessi", "Cistectomia ovarica"),
    ("benigna", "Annessi", "Salpingectomia"),
    ("benigna", "Annessi", "Salpingooforectomia"),
    ("benigna", "Malformazioni", "Metroplastica"),
    ("benigna", "Malformazioni", "Resezione setti"),

    # Emergenze
    ("emergenza", "Gravidanza extrauterina", "Salpingectomia"),
    ("emergenza", "Gravidanza extrauterina", "Salpingostomia"),
    ("emergenza", "Emorragie", "Revisione cavità"),
    ("emergenza", "Emorragie", "Emostasi"),
    ("emergenza", "Torsioni", "Detorsione"),
    ("emergenza", "Torsioni", "Annessiectomia"),
    ("emergenza", "Ascessi", "Drenaggio"),
    ("emergenza", "Ascessi", "Annessiectomia"),

    # Gravidanza
    ("gravidanza", "Gravidanza", "Cerchiaggio cervicale"),
    ("gravidanza", "Gravidanza", "IVG"),
    ("gravidanza", "Gravidanza", "Revisione cavità uterina post-partum"),

    # Diagnostiche/operative
    ("diagnostica", "Isteroscopia", "Isteroscopia diagnostica"),
    ("diagnostica", "Isteroscopia", "Isteroscopia operativa"),
    ("diagnostica", "Laparoscopia", "Laparoscopia diagnostica"),
    ("diagnostica", "Biopsia", "Biopsia endometriale"),
]


def _seed_categorie(conn):
    """Popola la tabella categorie con la tassonomia predefinita."""
    conn.executemany(
        "INSERT INTO categorie (categoria, sottocategoria, procedura_esempio) VALUES (?, ?, ?)",
        CATEGORIE_DATA,
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Seeding interventi di esempio
# ---------------------------------------------------------------------------

def _seed_interventi_esempio(conn):
    """Inserisce 20 interventi di esempio per il testing."""
    chirurghi = ["Dott. Rossi", "Dott.ssa Bianchi", "Dott. Verdi", "Dott.ssa Neri"]
    tecniche = ["laparoscopica", "laparotomica", "robotica", "isteroscopica", "vaginale"]
    urgenze = ["elettiva", "elettiva", "elettiva", "urgente", "emergenza"]

    esempi = [
        ("oncologica", "Utero", "Isterectomia radicale", "C54.1", "laparotomica", 180, 195, 2, "", 0, 5, 6),
        ("oncologica", "Ovaio", "Debulking", "C56", "laparotomica", 240, 270, 3, "Sanguinamento intraoperatorio", 2, 7, 9),
        ("oncologica", "Cervice", "Conizzazione LEEP", "D06.9", "isteroscopica", 30, 25, 1, "", 0, 1, 1),
        ("oncologica", "Endometrio", "Isterectomia staging", "C54.1", "laparoscopica", 150, 140, 2, "", 0, 3, 3),
        ("oncologica", "Vulva/Vagina", "Vulvectomia", "C51.9", "laparotomica", 120, 135, 2, "Infezione ferita", 1, 5, 7),
        ("benigna", "Fibromatosi", "Miomectomia", "D25.1", "laparoscopica", 90, 85, 1, "", 0, 2, 2),
        ("benigna", "Endometriosi", "Exeresi cisti endometriosica", "N80.1", "laparoscopica", 75, 90, 1, "", 0, 2, 2),
        ("benigna", "Uroginecologia", "Colposacropessi", "N81.2", "laparoscopica", 120, 110, 2, "", 0, 3, 3),
        ("benigna", "Annessi", "Cistectomia ovarica", "D27", "laparoscopica", 60, 55, 1, "", 0, 1, 1),
        ("benigna", "Annessi", "Salpingectomia", "N70.1", "laparoscopica", 45, 40, 1, "", 0, 1, 1),
        ("benigna", "Fibromatosi", "Isterectomia", "D25.9", "vaginale", 90, 100, 2, "", 0, 3, 4),
        ("benigna", "Malformazioni", "Resezione setti", "Q51.1", "isteroscopica", 30, 35, 1, "", 0, 1, 1),
        ("emergenza", "Gravidanza extrauterina", "Salpingectomia", "O00.1", "laparoscopica", 60, 50, 1, "", 0, 2, 2),
        ("emergenza", "Emorragie", "Revisione cavità", "N93.9", "isteroscopica", 30, 25, 2, "", 0, 1, 1),
        ("emergenza", "Torsioni", "Detorsione", "N83.5", "laparoscopica", 45, 55, 1, "", 0, 2, 2),
        ("gravidanza", "Gravidanza", "Cerchiaggio cervicale", "O34.3", "vaginale", 30, 25, 1, "", 0, 1, 1),
        ("gravidanza", "Gravidanza", "IVG", "O04", "isteroscopica", 20, 15, 1, "", 0, 1, 1),
        ("diagnostica", "Isteroscopia", "Isteroscopia diagnostica", "Z12.4", "isteroscopica", 15, 12, 1, "", 0, 0, 0),
        ("diagnostica", "Isteroscopia", "Isteroscopia operativa", "N84.0", "isteroscopica", 30, 35, 1, "", 0, 1, 1),
        ("diagnostica", "Laparoscopia", "Laparoscopia diagnostica", "R10.4", "laparoscopica", 45, 40, 1, "", 0, 1, 1),
    ]

    base_date = date(2025, 1, 15)
    for i, (cat, sottocat, proc, icd, tec, dur_prev, dur_eff, asa, compl, clavien, deg_prev, deg_eff) in enumerate(esempi):
        d = base_date + timedelta(days=i * 14 + random.randint(0, 7))
        chir = chirurghi[i % len(chirurghi)]
        assist = chirurghi[(i + 1) % len(chirurghi)]
        codice = f"PAZ-2025-{i+1:03d}"
        eta = random.randint(25, 75)
        urgenza = "emergenza" if cat == "emergenza" else random.choice(["elettiva", "elettiva", "urgente"])
        riamm = 1 if compl and random.random() < 0.3 else 0

        conn.execute("""
            INSERT INTO interventi (
                data_intervento, codice_paziente, eta_paziente,
                categoria, sottocategoria, procedura_specifica,
                codice_icd10, urgenza, tecnica,
                chirurgo_principale, assistenti,
                durata_prevista_min, durata_effettiva_min,
                classe_asa, complicanze, grado_clavien_dindo,
                degenza_prevista_giorni, degenza_effettiva_giorni,
                riammissione_30gg, esito_istologico, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d.isoformat(), codice, eta,
            cat, sottocat, proc,
            icd, urgenza, tec,
            chir, assist,
            dur_prev, dur_eff,
            asa, compl, clavien,
            deg_prev, deg_eff,
            riamm, "", ""
        ))

    conn.commit()


# ---------------------------------------------------------------------------
# Operazioni CRUD
# ---------------------------------------------------------------------------

def inserisci_intervento(data: dict) -> int:
    """Inserisce un nuovo intervento e restituisce l'ID generato."""
    conn = get_connection()
    cols = [
        "data_intervento", "codice_paziente", "eta_paziente",
        "categoria", "sottocategoria", "procedura_specifica",
        "codice_icd10", "urgenza", "tecnica",
        "chirurgo_principale", "assistenti",
        "durata_prevista_min", "durata_effettiva_min",
        "classe_asa", "complicanze", "grado_clavien_dindo",
        "degenza_prevista_giorni", "degenza_effettiva_giorni",
        "riammissione_30gg", "esito_istologico", "note",
    ]
    values = [data.get(c) for c in cols]
    placeholders = ", ".join(["?"] * len(cols))
    col_names = ", ".join(cols)
    cursor = conn.execute(
        f"INSERT INTO interventi ({col_names}) VALUES ({placeholders})", values
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def aggiorna_intervento(intervento_id: int, data: dict):
    """Aggiorna un intervento esistente."""
    conn = get_connection()
    sets = ", ".join([f"{k} = ?" for k in data.keys()])
    values = list(data.values()) + [intervento_id]
    conn.execute(f"UPDATE interventi SET {sets} WHERE id = ?", values)
    conn.commit()
    conn.close()


def elimina_intervento(intervento_id: int):
    """Elimina un intervento dato il suo ID."""
    conn = get_connection()
    conn.execute("DELETE FROM interventi WHERE id = ?", (intervento_id,))
    conn.commit()
    conn.close()


def cerca_interventi(filtri: dict, limit=100, offset=0):
    """
    Cerca interventi con filtri combinabili.
    Restituisce una lista di dict e il conteggio totale.
    """
    conn = get_connection()
    where_clauses = []
    params = []

    if filtri.get("data_da"):
        where_clauses.append("data_intervento >= ?")
        params.append(filtri["data_da"])
    if filtri.get("data_a"):
        where_clauses.append("data_intervento <= ?")
        params.append(filtri["data_a"])
    if filtri.get("categoria"):
        where_clauses.append("categoria = ?")
        params.append(filtri["categoria"])
    if filtri.get("sottocategoria"):
        where_clauses.append("sottocategoria = ?")
        params.append(filtri["sottocategoria"])
    if filtri.get("chirurgo"):
        where_clauses.append("chirurgo_principale = ?")
        params.append(filtri["chirurgo"])
    if filtri.get("tecnica"):
        where_clauses.append("tecnica = ?")
        params.append(filtri["tecnica"])
    if filtri.get("urgenza"):
        where_clauses.append("urgenza = ?")
        params.append(filtri["urgenza"])
    if filtri.get("con_complicanze") is True:
        where_clauses.append("complicanze IS NOT NULL AND complicanze != ''")
    elif filtri.get("con_complicanze") is False:
        where_clauses.append("(complicanze IS NULL OR complicanze = '')")
    if filtri.get("procedura"):
        where_clauses.append("procedura_specifica LIKE ?")
        params.append(f"%{filtri['procedura']}%")

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    count_row = conn.execute(
        f"SELECT COUNT(*) as cnt FROM interventi WHERE {where_sql}", params
    ).fetchone()
    total = count_row["cnt"]

    rows = conn.execute(
        f"SELECT * FROM interventi WHERE {where_sql} ORDER BY data_intervento DESC LIMIT ? OFFSET ?",
        params + [limit, offset],
    ).fetchall()

    conn.close()
    return [dict(r) for r in rows], total


def get_intervento(intervento_id: int):
    """Restituisce un singolo intervento per ID."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM interventi WHERE id = ?", (intervento_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_categorie():
    """Restituisce tutte le categorie dalla tassonomia."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM categorie ORDER BY categoria, sottocategoria").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_categorie_uniche():
    """Restituisce la lista di categorie distinte."""
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT categoria FROM categorie ORDER BY categoria").fetchall()
    conn.close()
    return [r["categoria"] for r in rows]


def get_sottocategorie(categoria: str):
    """Restituisce le sottocategorie per una data categoria."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT sottocategoria FROM categorie WHERE categoria = ? ORDER BY sottocategoria",
        (categoria,),
    ).fetchall()
    conn.close()
    return [r["sottocategoria"] for r in rows]


def get_procedure(categoria: str, sottocategoria: str):
    """Restituisce le procedure per categoria e sottocategoria."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT procedura_esempio FROM categorie WHERE categoria = ? AND sottocategoria = ?",
        (categoria, sottocategoria),
    ).fetchall()
    conn.close()
    return [r["procedura_esempio"] for r in rows]


def get_chirurghi():
    """Restituisce la lista di chirurghi dallo storico."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT chirurgo_principale FROM interventi WHERE chirurgo_principale IS NOT NULL AND chirurgo_principale != '' ORDER BY chirurgo_principale"
    ).fetchall()
    conn.close()
    return [r["chirurgo_principale"] for r in rows]


# ---------------------------------------------------------------------------
# Statistiche
# ---------------------------------------------------------------------------

def get_statistiche(anno: int = None, chirurgo: str = None):
    """Calcola statistiche aggregate per dashboard."""
    conn = get_connection()
    where = []
    params = []

    if anno:
        where.append("strftime('%Y', data_intervento) = ?")
        params.append(str(anno))
    if chirurgo:
        where.append("chirurgo_principale = ?")
        params.append(chirurgo)

    where_sql = " AND ".join(where) if where else "1=1"

    # Totale interventi
    totale = conn.execute(
        f"SELECT COUNT(*) as cnt FROM interventi WHERE {where_sql}", params
    ).fetchone()["cnt"]

    # Distribuzione per categoria
    dist_cat = conn.execute(
        f"SELECT categoria, COUNT(*) as cnt FROM interventi WHERE {where_sql} GROUP BY categoria",
        params,
    ).fetchall()

    # Trend mensile
    trend = conn.execute(
        f"""SELECT strftime('%Y-%m', data_intervento) as mese, COUNT(*) as cnt
            FROM interventi WHERE {where_sql}
            GROUP BY mese ORDER BY mese""",
        params,
    ).fetchall()

    # Tasso complicanze
    con_compl = conn.execute(
        f"SELECT COUNT(*) as cnt FROM interventi WHERE {where_sql} AND complicanze IS NOT NULL AND complicanze != ''",
        params,
    ).fetchone()["cnt"]
    tasso_compl = (con_compl / totale * 100) if totale > 0 else 0

    # Degenza media per categoria
    degenza = conn.execute(
        f"""SELECT categoria, AVG(degenza_effettiva_giorni) as media
            FROM interventi WHERE {where_sql} AND degenza_effettiva_giorni IS NOT NULL
            GROUP BY categoria""",
        params,
    ).fetchall()

    # Totale anno precedente per confronto
    totale_prec = 0
    if anno:
        totale_prec = conn.execute(
            f"SELECT COUNT(*) as cnt FROM interventi WHERE strftime('%Y', data_intervento) = ?"
            + (f" AND chirurgo_principale = ?" if chirurgo else ""),
            [str(anno - 1)] + ([chirurgo] if chirurgo else []),
        ).fetchone()["cnt"]

    conn.close()
    return {
        "totale": totale,
        "totale_anno_precedente": totale_prec,
        "distribuzione_categoria": {r["categoria"]: r["cnt"] for r in dist_cat},
        "trend_mensile": {r["mese"]: r["cnt"] for r in trend},
        "tasso_complicanze": round(tasso_compl, 1),
        "degenza_media": {r["categoria"]: round(r["media"], 1) for r in degenza},
    }


def get_statistiche_avanzate(anno: int = None):
    """Statistiche avanzate per analisi."""
    conn = get_connection()
    where = []
    params = []
    if anno:
        where.append("strftime('%Y', data_intervento) = ?")
        params.append(str(anno))
    where_sql = " AND ".join(where) if where else "1=1"

    # Durata prevista vs effettiva
    durate = conn.execute(
        f"""SELECT procedura_specifica, durata_prevista_min, durata_effettiva_min,
                   data_intervento, tecnica
            FROM interventi WHERE {where_sql}
            AND durata_prevista_min IS NOT NULL AND durata_effettiva_min IS NOT NULL""",
        params,
    ).fetchall()

    # Correlazione ASA - complicanze
    asa_compl = conn.execute(
        f"""SELECT classe_asa,
                   COUNT(*) as totale,
                   SUM(CASE WHEN complicanze IS NOT NULL AND complicanze != '' THEN 1 ELSE 0 END) as con_compl
            FROM interventi WHERE {where_sql} AND classe_asa IS NOT NULL
            GROUP BY classe_asa ORDER BY classe_asa""",
        params,
    ).fetchall()

    # Degenza per categoria (box plot data)
    degenza_box = conn.execute(
        f"""SELECT categoria, degenza_effettiva_giorni
            FROM interventi WHERE {where_sql}
            AND degenza_effettiva_giorni IS NOT NULL""",
        params,
    ).fetchall()

    # Performance operatori
    perf = conn.execute(
        f"""SELECT chirurgo_principale,
                   COUNT(*) as volume,
                   AVG(durata_effettiva_min) as durata_media,
                   SUM(CASE WHEN complicanze IS NOT NULL AND complicanze != '' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as tasso_compl
            FROM interventi WHERE {where_sql} AND chirurgo_principale IS NOT NULL
            GROUP BY chirurgo_principale""",
        params,
    ).fetchall()

    # Distribuzione tecniche
    tecniche = conn.execute(
        f"""SELECT tecnica, COUNT(*) as cnt
            FROM interventi WHERE {where_sql} AND tecnica IS NOT NULL
            GROUP BY tecnica""",
        params,
    ).fetchall()

    # Ore sala operatoria per mese
    ore_sala = conn.execute(
        f"""SELECT strftime('%Y-%m', data_intervento) as mese,
                   SUM(durata_effettiva_min) / 60.0 as ore
            FROM interventi WHERE {where_sql} AND durata_effettiva_min IS NOT NULL
            GROUP BY mese ORDER BY mese""",
        params,
    ).fetchall()

    conn.close()
    return {
        "durate": [dict(r) for r in durate],
        "asa_complicanze": [dict(r) for r in asa_compl],
        "degenza_box": [dict(r) for r in degenza_box],
        "performance": [dict(r) for r in perf],
        "tecniche": {r["tecnica"]: r["cnt"] for r in tecniche},
        "ore_sala": {r["mese"]: round(r["ore"], 1) for r in ore_sala},
    }


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

def esegui_backup():
    """Esegue un backup del database e registra nel log."""
    base = os.path.dirname(os.path.abspath(__file__))
    backup_dir = os.path.join(base, BACKUP_DIR)
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"gyn_tracker_{timestamp}.db")

    # Copia il database
    shutil.copy2(get_db_path(), backup_path)

    # Conta record
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) as cnt FROM interventi").fetchone()["cnt"]

    # Registra nel log
    conn.execute(
        "INSERT INTO backup_log (data_backup, numero_record, path_file) VALUES (?, ?, ?)",
        (datetime.now().isoformat(), count, backup_path),
    )
    conn.commit()

    # Mantieni solo ultimi 12 backup
    backups = sorted(Path(backup_dir).glob("gyn_tracker_*.db"), key=os.path.getmtime)
    while len(backups) > 12:
        backups[0].unlink()
        backups.pop(0)

    conn.close()
    return backup_path


def get_backup_log():
    """Restituisce lo storico dei backup."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM backup_log ORDER BY data_backup DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Impostazioni
# ---------------------------------------------------------------------------

def get_impostazione(chiave: str, default: str = ""):
    """Legge un'impostazione."""
    conn = get_connection()
    row = conn.execute("SELECT valore FROM impostazioni WHERE chiave = ?", (chiave,)).fetchone()
    conn.close()
    return row["valore"] if row else default


def set_impostazione(chiave: str, valore: str):
    """Salva un'impostazione."""
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO impostazioni (chiave, valore) VALUES (?, ?)",
        (chiave, valore),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Import da Excel
# ---------------------------------------------------------------------------

def import_da_excel(file_path: str) -> tuple:
    """
    Importa interventi da file Excel.
    Restituisce (numero_importati, lista_errori).
    """
    import pandas as pd

    df = pd.read_excel(file_path)
    importati = 0
    errori = []

    col_mapping = {
        "data_intervento": "data_intervento",
        "codice_paziente": "codice_paziente",
        "eta_paziente": "eta_paziente",
        "categoria": "categoria",
        "sottocategoria": "sottocategoria",
        "procedura_specifica": "procedura_specifica",
        "codice_icd10": "codice_icd10",
        "urgenza": "urgenza",
        "tecnica": "tecnica",
        "chirurgo_principale": "chirurgo_principale",
        "assistenti": "assistenti",
        "durata_prevista_min": "durata_prevista_min",
        "durata_effettiva_min": "durata_effettiva_min",
        "classe_asa": "classe_asa",
        "complicanze": "complicanze",
        "grado_clavien_dindo": "grado_clavien_dindo",
        "degenza_prevista_giorni": "degenza_prevista_giorni",
        "degenza_effettiva_giorni": "degenza_effettiva_giorni",
        "riammissione_30gg": "riammissione_30gg",
        "esito_istologico": "esito_istologico",
        "note": "note",
    }

    for idx, row in df.iterrows():
        try:
            data = {}
            for col in col_mapping:
                if col in df.columns:
                    val = row[col]
                    if pd.isna(val):
                        val = None
                    elif col == "data_intervento" and val is not None:
                        val = str(val)[:10]
                    elif col in ("eta_paziente", "durata_prevista_min", "durata_effettiva_min",
                                 "classe_asa", "grado_clavien_dindo", "degenza_prevista_giorni",
                                 "degenza_effettiva_giorni"):
                        val = int(val) if val is not None else None
                    elif col == "riammissione_30gg":
                        val = bool(val) if val is not None else False
                    else:
                        val = str(val) if val is not None else None
                    data[col] = val

            if data.get("data_intervento"):
                inserisci_intervento(data)
                importati += 1
        except Exception as e:
            errori.append(f"Riga {idx + 2}: {str(e)}")

    return importati, errori
