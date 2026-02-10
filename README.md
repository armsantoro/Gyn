# GynTracker

Applicazione per la gestione e analisi degli interventi chirurgici ginecologici.
Basata su Streamlit con database SQLite.

## Funzionalità

- **Dashboard** con statistiche, grafici a torta, trend mensili e KPI
- **Inserimento interventi** con form guidato, dropdown pre-popolati e validazione
- **Ricerca avanzata** con filtri multipli combinabili e paginazione
- **Reportistica** (casistica annuale, complicanze, tecniche, performance operatori, sala operatoria)
- **Analisi avanzate** (scatter plot durate, curva apprendimento, correlazione ASA-complicanze, box plot degenza)
- **Gestione** (backup manuale, import Excel, impostazioni, eliminazione interventi)
- **Export** in Excel e CSV

## Requisiti

- Python 3.9+
- Dipendenze elencate in `requirements.txt`

## Installazione

```bash
pip install -r requirements.txt
```

## Esecuzione

```bash
streamlit run app.py
```

L'applicazione si apre nel browser su `http://localhost:8501`.

Al primo avvio vengono creati automaticamente:
- Il database SQLite (`gyn_tracker.db`)
- Le categorie di intervento pre-popolate (44 voci)
- 20 interventi di esempio per testing

## Compilazione in .exe (Windows)

```bash
pip install pyinstaller
pyinstaller app.spec
```

L'eseguibile standalone viene generato nella cartella `dist/`.

## Struttura file

```
├── app.py              # Applicazione Streamlit principale
├── database.py         # Modulo database (schema, CRUD, statistiche)
├── requirements.txt    # Dipendenze Python
├── app.spec            # Configurazione PyInstaller
├── gyn_tracker.db      # Database SQLite (creato al primo avvio)
└── backup/             # Cartella backup (creata automaticamente)
```

## Tassonomia interventi

Le categorie pre-popolate coprono:
- **Oncologia ginecologica**: utero, ovaio, cervice, endometrio, vulva/vagina
- **Patologia benigna**: fibromatosi, endometriosi, uroginecologia, annessi, malformazioni
- **Emergenze**: gravidanza extrauterina, emorragie, torsioni, ascessi
- **Gravidanza**: cerchiaggio, IVG, revisione post-partum
- **Diagnostiche/operative**: isteroscopia, laparoscopia, biopsia
