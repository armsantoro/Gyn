"""
GynTracker - Applicazione per la gestione degli interventi ginecologici.
Avviare con: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
from io import BytesIO

import database as db

# ---------------------------------------------------------------------------
# Configurazione pagina
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="GynTracker",
    page_icon="\U0001FA7A",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inizializzazione database
if "db_initialized" not in st.session_state:
    first_run = db.init_db()
    st.session_state.db_initialized = True
    st.session_state.first_run = first_run

# ---------------------------------------------------------------------------
# Sidebar navigazione
# ---------------------------------------------------------------------------

st.sidebar.title("GynTracker")
st.sidebar.markdown("---")

PAGES = {
    "Dashboard": "dashboard",
    "Nuovo Intervento": "nuovo",
    "Ricerca e Visualizzazione": "ricerca",
    "Reportistica": "report",
    "Analisi Avanzate": "analisi",
    "Gestione": "gestione",
}

page = st.sidebar.radio("Navigazione", list(PAGES.keys()))

# Pulsante rapido sempre visibile
if st.sidebar.button("+ Nuovo Intervento", type="primary", use_container_width=True):
    page = "Nuovo Intervento"

st.sidebar.markdown("---")
st.sidebar.caption("GynTracker v1.0")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def df_to_excel(dataframe: pd.DataFrame) -> bytes:
    """Converte un DataFrame in bytes Excel per il download."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Interventi")
    return output.getvalue()


def df_to_csv(dataframe: pd.DataFrame) -> bytes:
    """Converte un DataFrame in bytes CSV."""
    return dataframe.to_csv(index=False).encode("utf-8-sig")


CATEGORIE_VALIDE = ["oncologica", "benigna", "emergenza", "gravidanza", "diagnostica"]
URGENZE = ["elettiva", "urgente", "emergenza"]
TECNICHE = ["laparoscopica", "laparotomica", "robotica", "isteroscopica", "vaginale"]


# ---------------------------------------------------------------------------
# PAGINA: Dashboard
# ---------------------------------------------------------------------------

def pagina_dashboard():
    st.title("Dashboard")

    # Filtri
    col1, col2, col3 = st.columns(3)
    with col1:
        anno = st.selectbox("Anno", list(range(datetime.now().year, 2019, -1)), index=0)
    with col2:
        chirurghi = ["Tutti"] + db.get_chirurghi()
        chirurgo_sel = st.selectbox("Chirurgo", chirurghi)
    with col3:
        periodo = st.selectbox("Periodo", ["Anno intero", "1\u00b0 Semestre", "2\u00b0 Semestre",
                                            "1\u00b0 Trimestre", "2\u00b0 Trimestre",
                                            "3\u00b0 Trimestre", "4\u00b0 Trimestre"])

    chirurgo_filtro = chirurgo_sel if chirurgo_sel != "Tutti" else None
    stats = db.get_statistiche(anno=anno, chirurgo=chirurgo_filtro)

    # KPI principali
    st.markdown("---")
    k1, k2, k3, k4 = st.columns(4)

    delta_totale = stats["totale"] - stats["totale_anno_precedente"] if stats["totale_anno_precedente"] > 0 else None
    k1.metric("Totale Interventi", stats["totale"],
              delta=f"{delta_totale:+d} vs anno prec." if delta_totale is not None else None)
    k2.metric("Tasso Complicanze", f"{stats['tasso_complicanze']}%")

    degenze = stats.get("degenza_media", {})
    deg_media_glob = sum(degenze.values()) / len(degenze) if degenze else 0
    k3.metric("Degenza Media", f"{deg_media_glob:.1f} gg")
    k4.metric("Categorie Attive", len(stats["distribuzione_categoria"]))

    st.markdown("---")

    # Grafici
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Distribuzione per Categoria")
        if stats["distribuzione_categoria"]:
            df_cat = pd.DataFrame(
                list(stats["distribuzione_categoria"].items()),
                columns=["Categoria", "Conteggio"],
            )
            fig_pie = px.pie(df_cat, values="Conteggio", names="Categoria",
                             color_discrete_sequence=px.colors.qualitative.Set2)
            fig_pie.update_layout(margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Nessun dato disponibile per questo periodo.")

    with col_right:
        st.subheader("Trend Mensile")
        if stats["trend_mensile"]:
            df_trend = pd.DataFrame(
                list(stats["trend_mensile"].items()),
                columns=["Mese", "Interventi"],
            )
            fig_line = px.line(df_trend, x="Mese", y="Interventi", markers=True,
                               color_discrete_sequence=["#2E86AB"])
            fig_line.update_layout(margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Nessun dato disponibile per questo periodo.")

    # Degenza media per categoria
    st.subheader("Degenza Media per Categoria")
    if degenze:
        df_deg = pd.DataFrame(
            list(degenze.items()),
            columns=["Categoria", "Giorni Medi"],
        )
        fig_bar = px.bar(df_deg, x="Categoria", y="Giorni Medi",
                         color_discrete_sequence=["#A23B72"])
        fig_bar.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_bar, use_container_width=True)


# ---------------------------------------------------------------------------
# PAGINA: Nuovo Intervento
# ---------------------------------------------------------------------------

def pagina_nuovo_intervento():
    st.title("Nuovo Intervento")

    with st.form("form_intervento", clear_on_submit=True):
        st.subheader("Dati Intervento")

        col1, col2, col3 = st.columns(3)
        with col1:
            data_intervento = st.date_input("Data intervento *", value=date.today(), max_value=date.today())
            codice_paziente = st.text_input("Codice paziente", placeholder="PAZ-2025-XXX")
            eta_paziente = st.number_input("Et\u00e0 paziente", min_value=0, max_value=120, value=45)

        with col2:
            categoria = st.selectbox("Categoria *", CATEGORIE_VALIDE)
            # Sottocategorie dinamiche
            sottocategorie = db.get_sottocategorie(categoria) if categoria else []
            sottocategoria = st.selectbox("Sottocategoria", sottocategorie if sottocategorie else [""])
            # Procedure dinamiche
            procedure = db.get_procedure(categoria, sottocategoria) if sottocategoria else []
            procedura = st.selectbox("Procedura specifica", procedure if procedure else [""])

        with col3:
            codice_icd10 = st.text_input("Codice ICD-10", placeholder="es. C54.1")
            urgenza = st.selectbox("Urgenza", URGENZE)
            tecnica = st.selectbox("Tecnica", TECNICHE)

        st.markdown("---")
        st.subheader("Team e Tempistiche")

        col4, col5 = st.columns(2)
        with col4:
            chirurghi_esistenti = db.get_chirurghi()
            chirurgo = st.selectbox(
                "Chirurgo principale *",
                options=[""] + chirurghi_esistenti,
                index=0,
            )
            chirurgo_nuovo = st.text_input("Oppure inserisci nuovo chirurgo")
            chirurgo_finale = chirurgo_nuovo if chirurgo_nuovo else chirurgo

            assistenti = st.text_input("Assistenti", placeholder="Separati da virgola")

        with col5:
            durata_prevista = st.number_input("Durata prevista (min)", min_value=0, value=60)
            durata_effettiva = st.number_input("Durata effettiva (min)", min_value=0, value=60)
            if durata_prevista > 0 and durata_effettiva > 0:
                scostamento = durata_effettiva - durata_prevista
                perc = (scostamento / durata_prevista) * 100
                st.caption(f"Scostamento: {scostamento:+d} min ({perc:+.1f}%)")

        st.markdown("---")
        st.subheader("Esiti e Degenza")

        col6, col7 = st.columns(2)
        with col6:
            classe_asa = st.selectbox("Classe ASA", [1, 2, 3, 4, 5], index=0)
            complicanze = st.text_area("Complicanze", placeholder="Descrivere se presenti, lasciare vuoto se assenti")
            grado_clavien = st.selectbox("Grado Clavien-Dindo", [0, 1, 2, 3, 4, 5], index=0)

        with col7:
            degenza_prevista = st.number_input("Degenza prevista (giorni)", min_value=0, value=2)
            degenza_effettiva = st.number_input("Degenza effettiva (giorni)", min_value=0, value=2)
            if degenza_prevista > 0 and degenza_effettiva > 0:
                sco_deg = degenza_effettiva - degenza_prevista
                st.caption(f"Scostamento degenza: {sco_deg:+d} giorni")
            riammissione = st.checkbox("Riammissione entro 30 giorni")

        esito_istologico = st.text_area("Esito istologico")
        note = st.text_area("Note")

        submitted = st.form_submit_button("Salva Intervento", type="primary", use_container_width=True)

        if submitted:
            # Validazione
            errori = []
            if not data_intervento:
                errori.append("La data intervento \u00e8 obbligatoria.")
            if not categoria:
                errori.append("La categoria \u00e8 obbligatoria.")
            if not chirurgo_finale:
                errori.append("Il chirurgo principale \u00e8 obbligatorio.")

            if errori:
                for e in errori:
                    st.error(e)
            else:
                intervento = {
                    "data_intervento": data_intervento.isoformat(),
                    "codice_paziente": codice_paziente,
                    "eta_paziente": eta_paziente,
                    "categoria": categoria,
                    "sottocategoria": sottocategoria,
                    "procedura_specifica": procedura,
                    "codice_icd10": codice_icd10,
                    "urgenza": urgenza,
                    "tecnica": tecnica,
                    "chirurgo_principale": chirurgo_finale,
                    "assistenti": assistenti,
                    "durata_prevista_min": durata_prevista,
                    "durata_effettiva_min": durata_effettiva,
                    "classe_asa": classe_asa,
                    "complicanze": complicanze,
                    "grado_clavien_dindo": grado_clavien,
                    "degenza_prevista_giorni": degenza_prevista,
                    "degenza_effettiva_giorni": degenza_effettiva,
                    "riammissione_30gg": riammissione,
                    "esito_istologico": esito_istologico,
                    "note": note,
                }
                new_id = db.inserisci_intervento(intervento)
                st.success(f"Intervento salvato con successo! (ID: {new_id})")


# ---------------------------------------------------------------------------
# PAGINA: Ricerca e Visualizzazione
# ---------------------------------------------------------------------------

def pagina_ricerca():
    st.title("Ricerca e Visualizzazione")

    # Filtri
    with st.expander("Filtri di ricerca", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            data_da = st.date_input("Dal", value=date(date.today().year, 1, 1), key="data_da")
            data_a = st.date_input("Al", value=date.today(), key="data_a")
        with col2:
            cat_filtro = st.selectbox("Categoria", ["Tutte"] + CATEGORIE_VALIDE, key="filt_cat")
            tec_filtro = st.selectbox("Tecnica", ["Tutte"] + TECNICHE, key="filt_tec")
        with col3:
            chirurghi = ["Tutti"] + db.get_chirurghi()
            chir_filtro = st.selectbox("Chirurgo", chirurghi, key="filt_chir")
            urg_filtro = st.selectbox("Urgenza", ["Tutte"] + URGENZE, key="filt_urg")

        compl_filtro = st.radio(
            "Complicanze", ["Tutte", "Con complicanze", "Senza complicanze"],
            horizontal=True,
        )

    # Costruisci filtri
    filtri = {
        "data_da": data_da.isoformat(),
        "data_a": data_a.isoformat(),
    }
    if cat_filtro != "Tutte":
        filtri["categoria"] = cat_filtro
    if tec_filtro != "Tutte":
        filtri["tecnica"] = tec_filtro
    if chir_filtro != "Tutti":
        filtri["chirurgo"] = chir_filtro
    if urg_filtro != "Tutte":
        filtri["urgenza"] = urg_filtro
    if compl_filtro == "Con complicanze":
        filtri["con_complicanze"] = True
    elif compl_filtro == "Senza complicanze":
        filtri["con_complicanze"] = False

    # Paginazione
    page_size = 100
    if "search_page" not in st.session_state:
        st.session_state.search_page = 0

    risultati, totale = db.cerca_interventi(
        filtri, limit=page_size, offset=st.session_state.search_page * page_size
    )

    st.markdown(f"**{totale} interventi trovati**")

    if risultati:
        df = pd.DataFrame(risultati)
        # Colonne da mostrare nella tabella
        cols_display = [
            "id", "data_intervento", "codice_paziente", "categoria",
            "sottocategoria", "procedura_specifica", "tecnica", "urgenza",
            "chirurgo_principale", "durata_effettiva_min", "complicanze",
            "degenza_effettiva_giorni",
        ]
        cols_presenti = [c for c in cols_display if c in df.columns]
        df_show = df[cols_presenti]

        st.dataframe(df_show, use_container_width=True, hide_index=True)

        # Paginazione
        total_pages = max(1, (totale + page_size - 1) // page_size)
        col_prev, col_info, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("\u25c0 Precedente", disabled=st.session_state.search_page == 0):
                st.session_state.search_page -= 1
                st.rerun()
        with col_info:
            st.caption(f"Pagina {st.session_state.search_page + 1} di {total_pages}")
        with col_next:
            if st.button("Successivo \u25b6", disabled=st.session_state.search_page >= total_pages - 1):
                st.session_state.search_page += 1
                st.rerun()

        # Export
        st.markdown("---")
        st.subheader("Esporta risultati")
        # Per export scarica tutti i risultati (senza paginazione)
        all_results, _ = db.cerca_interventi(filtri, limit=999999, offset=0)
        df_all = pd.DataFrame(all_results)

        col_ex1, col_ex2, col_ex3 = st.columns(3)
        with col_ex1:
            st.download_button(
                "Scarica Excel",
                data=df_to_excel(df_all),
                file_name=f"interventi_{date.today().isoformat()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        with col_ex2:
            st.download_button(
                "Scarica CSV",
                data=df_to_csv(df_all),
                file_name=f"interventi_{date.today().isoformat()}.csv",
                mime="text/csv",
            )
    else:
        st.info("Nessun intervento trovato con i filtri selezionati.")


# ---------------------------------------------------------------------------
# PAGINA: Reportistica
# ---------------------------------------------------------------------------

def pagina_report():
    st.title("Reportistica")

    anno = st.selectbox("Anno", list(range(datetime.now().year, 2019, -1)), key="rep_anno")
    stats_avanzate = db.get_statistiche_avanzate(anno=anno)
    stats = db.get_statistiche(anno=anno)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Casistica Annuale", "Complicanze", "Tecniche",
        "Performance Operatori", "Sala Operatoria",
    ])

    with tab1:
        st.subheader(f"Casistica Annuale {anno}")
        if stats["distribuzione_categoria"]:
            df_cas = pd.DataFrame(
                list(stats["distribuzione_categoria"].items()),
                columns=["Categoria", "Interventi"],
            )
            col1, col2 = st.columns(2)
            with col1:
                st.dataframe(df_cas, use_container_width=True, hide_index=True)
            with col2:
                fig = px.bar(df_cas, x="Categoria", y="Interventi",
                             color="Categoria", color_discrete_sequence=px.colors.qualitative.Set2)
                st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Analisi Complicanze")
        asa_data = stats_avanzate.get("asa_complicanze", [])
        if asa_data:
            df_asa = pd.DataFrame(asa_data)
            df_asa["tasso_%"] = (df_asa["con_compl"] / df_asa["totale"] * 100).round(1)
            st.dataframe(df_asa.rename(columns={
                "classe_asa": "Classe ASA",
                "totale": "Totale",
                "con_compl": "Con Complicanze",
                "tasso_%": "Tasso %",
            }), use_container_width=True, hide_index=True)

            fig = px.bar(df_asa, x="classe_asa", y="tasso_%",
                         labels={"classe_asa": "Classe ASA", "tasso_%": "Tasso Complicanze %"},
                         color_discrete_sequence=["#E8573A"])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessun dato disponibile.")

    with tab3:
        st.subheader("Distribuzione Tecniche Chirurgiche")
        tecniche_data = stats_avanzate.get("tecniche", {})
        if tecniche_data:
            df_tec = pd.DataFrame(list(tecniche_data.items()), columns=["Tecnica", "Interventi"])
            fig = px.pie(df_tec, values="Interventi", names="Tecnica",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessun dato disponibile.")

    with tab4:
        st.subheader("Performance Operatori")
        perf = stats_avanzate.get("performance", [])
        if perf:
            df_perf = pd.DataFrame(perf)
            df_perf["durata_media"] = df_perf["durata_media"].round(1)
            df_perf["tasso_compl"] = df_perf["tasso_compl"].round(1)
            st.dataframe(df_perf.rename(columns={
                "chirurgo_principale": "Chirurgo",
                "volume": "Volume",
                "durata_media": "Durata Media (min)",
                "tasso_compl": "Tasso Compl. %",
            }), use_container_width=True, hide_index=True)
        else:
            st.info("Nessun dato disponibile.")

    with tab5:
        st.subheader("Occupazione Sala Operatoria (ore/mese)")
        ore = stats_avanzate.get("ore_sala", {})
        if ore:
            df_ore = pd.DataFrame(list(ore.items()), columns=["Mese", "Ore"])
            fig = px.bar(df_ore, x="Mese", y="Ore", color_discrete_sequence=["#2E86AB"])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessun dato disponibile.")

    # Export report
    st.markdown("---")
    st.subheader("Esporta Report")
    all_results, _ = db.cerca_interventi({"data_da": f"{anno}-01-01", "data_a": f"{anno}-12-31"}, limit=999999)
    if all_results:
        df_export = pd.DataFrame(all_results)
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Scarica Report Excel",
                data=df_to_excel(df_export),
                file_name=f"report_annuale_{anno}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        with col2:
            st.download_button(
                "Scarica Report CSV",
                data=df_to_csv(df_export),
                file_name=f"report_annuale_{anno}.csv",
                mime="text/csv",
            )


# ---------------------------------------------------------------------------
# PAGINA: Analisi Avanzate
# ---------------------------------------------------------------------------

def pagina_analisi():
    st.title("Analisi Avanzate")

    anno = st.selectbox("Anno", list(range(datetime.now().year, 2019, -1)), key="an_anno")
    stats = db.get_statistiche_avanzate(anno=anno)

    tab1, tab2, tab3, tab4 = st.tabs([
        "Durata Prevista vs Effettiva",
        "Curva di Apprendimento",
        "ASA vs Complicanze",
        "Box Plot Degenza",
    ])

    with tab1:
        st.subheader("Confronto Durata Prevista vs Effettiva")
        durate = stats.get("durate", [])
        if durate:
            df_dur = pd.DataFrame(durate)
            fig = px.scatter(
                df_dur,
                x="durata_prevista_min",
                y="durata_effettiva_min",
                color="tecnica",
                hover_data=["procedura_specifica", "data_intervento"],
                labels={
                    "durata_prevista_min": "Durata Prevista (min)",
                    "durata_effettiva_min": "Durata Effettiva (min)",
                },
            )
            # Linea di riferimento (prevista = effettiva)
            max_val = max(df_dur["durata_prevista_min"].max(), df_dur["durata_effettiva_min"].max())
            fig.add_trace(go.Scatter(
                x=[0, max_val], y=[0, max_val],
                mode="lines", name="Prevista = Effettiva",
                line=dict(dash="dash", color="gray"),
            ))
            fig.update_layout(margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessun dato disponibile.")

    with tab2:
        st.subheader("Curva di Apprendimento per Tecnica")
        durate = stats.get("durate", [])
        if durate:
            df_dur = pd.DataFrame(durate)
            tecnica_sel = st.selectbox("Seleziona tecnica", df_dur["tecnica"].unique())
            df_tec = df_dur[df_dur["tecnica"] == tecnica_sel].sort_values("data_intervento")
            df_tec = df_tec.reset_index(drop=True)
            df_tec["numero_progressivo"] = range(1, len(df_tec) + 1)

            fig = px.scatter(
                df_tec,
                x="numero_progressivo",
                y="durata_effettiva_min",
                trendline="lowess",
                hover_data=["procedura_specifica", "data_intervento"],
                labels={
                    "numero_progressivo": "Intervento N.",
                    "durata_effettiva_min": "Durata (min)",
                },
                color_discrete_sequence=["#2E86AB"],
            )
            fig.update_layout(margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessun dato disponibile.")

    with tab3:
        st.subheader("Correlazione ASA - Complicanze")
        asa_data = stats.get("asa_complicanze", [])
        if asa_data:
            df_asa = pd.DataFrame(asa_data)
            df_asa["tasso"] = (df_asa["con_compl"] / df_asa["totale"] * 100).round(1)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_asa["classe_asa"].astype(str),
                y=df_asa["totale"],
                name="Totale interventi",
                marker_color="#2E86AB",
            ))
            fig.add_trace(go.Bar(
                x=df_asa["classe_asa"].astype(str),
                y=df_asa["con_compl"],
                name="Con complicanze",
                marker_color="#E8573A",
            ))
            fig.update_layout(
                barmode="group",
                xaxis_title="Classe ASA",
                yaxis_title="Numero",
                margin=dict(t=20, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessun dato disponibile.")

    with tab4:
        st.subheader("Box Plot Degenza per Categoria")
        deg_data = stats.get("degenza_box", [])
        if deg_data:
            df_deg = pd.DataFrame(deg_data)
            fig = px.box(
                df_deg,
                x="categoria",
                y="degenza_effettiva_giorni",
                color="categoria",
                labels={
                    "categoria": "Categoria",
                    "degenza_effettiva_giorni": "Degenza (giorni)",
                },
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(margin=dict(t=20, b=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessun dato disponibile.")


# ---------------------------------------------------------------------------
# PAGINA: Gestione
# ---------------------------------------------------------------------------

def pagina_gestione():
    st.title("Gestione")

    tab1, tab2, tab3, tab4 = st.tabs(["Backup", "Import Excel", "Impostazioni", "Elimina Intervento"])

    with tab1:
        st.subheader("Backup Database")
        if st.button("Esegui Backup Manuale", type="primary"):
            try:
                path = db.esegui_backup()
                st.success(f"Backup eseguito: {path}")
            except Exception as e:
                st.error(f"Errore durante il backup: {e}")

        st.markdown("---")
        st.subheader("Storico Backup")
        log = db.get_backup_log()
        if log:
            df_log = pd.DataFrame(log)
            st.dataframe(df_log[["data_backup", "numero_record", "path_file"]],
                         use_container_width=True, hide_index=True)
        else:
            st.info("Nessun backup effettuato.")

    with tab2:
        st.subheader("Import da Excel")
        st.markdown("""
        Il file Excel deve avere le colonne con gli stessi nomi dei campi del database.
        Colonna obbligatoria: `data_intervento`.
        """)
        uploaded = st.file_uploader("Carica file Excel", type=["xlsx", "xls"])
        if uploaded and st.button("Importa"):
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                tmp.write(uploaded.getvalue())
                tmp_path = tmp.name
            importati, errori = db.import_da_excel(tmp_path)
            st.success(f"Importati {importati} interventi.")
            if errori:
                st.warning("Errori durante l'importazione:")
                for err in errori:
                    st.text(err)

    with tab3:
        st.subheader("Impostazioni")
        nome_reparto = st.text_input(
            "Nome Reparto",
            value=db.get_impostazione("nome_reparto", "Ginecologia e Ostetricia"),
        )
        if st.button("Salva Impostazioni"):
            db.set_impostazione("nome_reparto", nome_reparto)
            st.success("Impostazioni salvate.")

        st.markdown("---")
        st.subheader("Lista Chirurghi nello Storico")
        chirurghi = db.get_chirurghi()
        if chirurghi:
            for c in chirurghi:
                st.text(f"- {c}")
        else:
            st.info("Nessun chirurgo registrato.")

    with tab4:
        st.subheader("Elimina Intervento")
        st.warning("Questa operazione \u00e8 irreversibile.")
        id_elimina = st.number_input("ID intervento da eliminare", min_value=1, step=1)
        intervento = db.get_intervento(int(id_elimina))
        if intervento:
            st.json({
                "ID": intervento["id"],
                "Data": intervento["data_intervento"],
                "Paziente": intervento["codice_paziente"],
                "Procedura": intervento["procedura_specifica"],
            })
            conferma = st.checkbox("Confermo l'eliminazione di questo intervento")
            if conferma and st.button("Elimina", type="primary"):
                db.elimina_intervento(int(id_elimina))
                st.success("Intervento eliminato.")
                st.rerun()
        else:
            st.info("Inserisci un ID valido per visualizzare i dettagli.")


# ---------------------------------------------------------------------------
# Welcome screen (primo avvio)
# ---------------------------------------------------------------------------

def welcome_screen():
    st.balloons()
    st.title("Benvenuto in GynTracker!")
    st.markdown("""
    ### Configurazione iniziale completata

    Il database \u00e8 stato creato con successo. Sono stati inseriti:
    - **44 categorie** di intervento pre-popolate
    - **20 interventi di esempio** per il testing

    #### Come iniziare:
    1. **Dashboard** - Visualizza le statistiche degli interventi
    2. **Nuovo Intervento** - Inserisci un nuovo intervento chirurgico
    3. **Ricerca** - Cerca e filtra gli interventi esistenti
    4. **Reportistica** - Genera report e grafici
    5. **Analisi** - Analisi statistiche avanzate
    6. **Gestione** - Backup, import e impostazioni

    Usa il menu laterale per navigare tra le sezioni.
    """)
    if st.button("Inizia a usare GynTracker", type="primary"):
        st.session_state.first_run = False
        st.rerun()


# ---------------------------------------------------------------------------
# Router principale
# ---------------------------------------------------------------------------

if st.session_state.get("first_run"):
    welcome_screen()
else:
    if page == "Dashboard":
        pagina_dashboard()
    elif page == "Nuovo Intervento":
        pagina_nuovo_intervento()
    elif page == "Ricerca e Visualizzazione":
        pagina_ricerca()
    elif page == "Reportistica":
        pagina_report()
    elif page == "Analisi Avanzate":
        pagina_analisi()
    elif page == "Gestione":
        pagina_gestione()
