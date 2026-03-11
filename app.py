import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, timedelta
import time

# --- 1. CONFIGURAZIONE PAGINA E DESIGN DARK MODE ---
st.set_page_config(page_title="Network 2026", layout="wide", page_icon="👔", initial_sidebar_state="expanded")

def inject_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        
        /* 1. PALETTE COLORI DARK MODE & FONT GLOBALE */
        :root {
            --bg-main: #0F172A;
            --bg-card: #1E293B;
            --bg-input: #0B1120;
            --text-main: #F8FAFC;
            --text-muted: #94A3B8;
            --accent: #38BDF8;
            --accent-hover: #0284C7;
            --border-color: #334155;
        }

        html, body, [class*="css"] { 
            font-family: 'Plus Jakarta Sans', sans-serif !important; 
            background-color: var(--bg-main) !important;
            color: var(--text-main) !important;
        }

        h1, h2, h3, h4, p, span, label, div { color: var(--text-main); }
        h1, h2 { font-weight: 800 !important; letter-spacing: -1px; }
        .stMarkdown p, .stCaption p { color: var(--text-muted) !important; }

        /* =========================================================
           2. FIX MOBILE & SFONDO SIDEBAR
           ========================================================= */
        [data-testid="stSidebar"] {
            background-color: #0B1120 !important; /* Colore solido e impenetrabile */
            border-right: 1px solid var(--border-color) !important;
            z-index: 999999 !important; /* Forza la sidebar in primissimo piano */
        }
        
        /* Oscuramento sfondo su Mobile (Il "velo" dietro la sidebar aperta) */
        [data-testid="stSidebarOverlay"] {
            background-color: rgba(15, 23, 42, 0.85) !important; 
            backdrop-filter: blur(5px) !important; /* Effetto sfocatura del testo sottostante */
            z-index: 999998 !important;
        }

        /* =========================================================
           3. IL NUOVO MENU DI NAVIGAZIONE "APP-STYLE"
           ========================================================= */
        
        /* Nasconde i classici "pallini" tondi del radio button */
        [data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
            display: none !important;
        }
        
        /* Trasforma le opzioni in pulsanti a tutta larghezza */
        [data-testid="stSidebar"] div[role="radiogroup"] > label {
            background-color: transparent;
            padding: 12px 16px;
            border-radius: 12px;
            margin-bottom: 6px;
            transition: all 0.2s ease-in-out;
            width: 100%;
            cursor: pointer;
            border: 1px solid transparent;
        }
        
        /* Effetto quando passi il mouse sulle voci non selezionate */
        [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
            background-color: rgba(255, 255, 255, 0.05);
            transform: translateX(4px); /* Leggero scorrimento a destra */
        }
        
        /* Effetto della voce ATTUALMENTE SELEZIONATA */
        [data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] {
            background: linear-gradient(90deg, rgba(56,189,248,0.15) 0%, transparent 100%) !important;
            border-left: 4px solid var(--accent) !important;
            border-radius: 4px 12px 12px 4px !important;
        }
        
        /* Colore del testo della voce selezionata */
        [data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] p {
            color: var(--accent) !important;
            font-weight: 700 !important;
            letter-spacing: 0.3px;
        }

        /* Allinea il testo all'interno del nuovo pulsante */
        [data-testid="stSidebar"] div[role="radiogroup"] > label div {
            margin-left: 0 !important; 
            padding-left: 4px !important;
        }

        /* =========================================================
           4. CARD, METRICHE, INPUTS E BOTTONI 
           ========================================================= */
        [data-testid="stForm"], .stExpander {
            background-color: var(--bg-card) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 16px !important;
            padding: 24px !important;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5) !important;
            transition: all 0.3s ease !important;
        }
        [data-testid="stForm"]:hover, .stExpander:hover { border-color: #475569 !important; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.6) !important; }

        [data-testid="stMetric"] {
            background-color: var(--bg-card) !important; padding: 20px !important;
            border-radius: 16px; border: 1px solid var(--border-color);
            border-top: 4px solid var(--accent); box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            transition: all 0.3s ease;
        }
        [data-testid="stMetric"]:hover { transform: translateY(-5px); border-top: 4px solid #7DD3FC; box-shadow: 0 10px 15px rgba(56, 189, 248, 0.1); }
        [data-testid="stMetricValue"] { color: var(--accent) !important; font-weight: 800; font-size: 2.2rem; }
        [data-testid="stMetricLabel"] { color: var(--text-muted) !important; text-transform: uppercase; font-size: 0.85rem; font-weight: 600;}

        .stTextInput input, .stSelectbox div[data-baseweb="select"], .stDateInput input, .stNumberInput input {
            background-color: var(--bg-input) !important; color: var(--text-main) !important;
            border: 1px solid var(--border-color) !important; border-radius: 8px !important; padding: 0.7rem 1rem !important;
        }
        .stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus-within, .stDateInput input:focus, .stNumberInput input:focus {
            border-color: var(--accent) !important; box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.3) !important;
        }
        ul[data-baseweb="menu"] { background-color: var(--bg-card) !important; }
        ul[data-baseweb="menu"] li { color: var(--text-main) !important; }
        ul[data-baseweb="menu"] li:hover { background-color: var(--border-color) !important; color: var(--accent) !important; }

        /* Bottoni */
        div[data-testid="stFormSubmitButton"] > button, .stButton > button[kind="primary"] {
            background-color: var(--accent) !important; color: #000000 !important; border: none !important;
            border-radius: 8px !important; font-weight: 800 !important; padding: 0.6rem 1.5rem !important;
            box-shadow: 0 4px 10px rgba(56, 189, 248, 0.2) !important; transition: all 0.2s ease !important;
        }
        div[data-testid="stFormSubmitButton"] > button *, .stButton > button[kind="primary"] * { color: #000000 !important; }
        div[data-testid="stFormSubmitButton"] > button:hover, .stButton > button[kind="primary"]:hover {
            transform: translateY(-2px) !important; background-color: #7DD3FC !important; color: #000000 !important;
            box-shadow: 0 6px 15px rgba(56, 189, 248, 0.4) !important;
        }

        /* Tabs */
        [data-testid="stTabs"] button { color: var(--text-muted) !important; border-bottom-color: transparent !important; font-weight: 600; }
        [data-testid="stTabs"] button[aria-selected="true"] { color: var(--accent) !important; border-bottom-color: var(--accent) !important; }
        [data-testid="stTabs"] button:hover { color: var(--accent) !important; }
        [data-testid="stTabs"] div[data-baseweb="tab-highlight"] { background-color: var(--accent) !important; }
        
        [data-testid="stDataFrame"] { border: 1px solid var(--border-color); border-radius: 12px; }
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- 2. CONNESSIONE MYSQL (SITEGROUND) ---
@st.cache_resource
def init_connection():
    db = st.secrets["mysql"]
    password_sicura = urllib.parse.quote_plus(db['password'])
    url = f"mysql+pymysql://{db['user']}:{password_sicura}@{db['host']}:{db['port']}/{db['database']}?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800, pool_timeout=30, connect_args={"connect_timeout": 15})

engine = init_connection()

def init_db():
    try:
        with engine.begin() as conn:
            conn.execute(text('''CREATE TABLE IF NOT EXISTS Agenti (ID_Agente VARCHAR(50) PRIMARY KEY, Nome VARCHAR(100), Ruolo VARCHAR(50), ID_Capoarea VARCHAR(50), Mail_Notifica VARCHAR(100), Password VARCHAR(100))'''))
            conn.execute(text('''CREATE TABLE IF NOT EXISTS Negozi (Nome VARCHAR(100) PRIMARY KEY, Partita_IVA VARCHAR(50), Citta VARCHAR(100), Provincia VARCHAR(10), Regione VARCHAR(50))'''))
            conn.execute(text('''CREATE TABLE IF NOT EXISTS Brand (ID_Brand VARCHAR(50) PRIMARY KEY, Nome_Brand VARCHAR(100), Provvigione_Totale_perc VARCHAR(20), Quota_Capoarea_perc VARCHAR(20), Quota_Agente_perc VARCHAR(20))'''))
            conn.execute(text('''CREATE TABLE IF NOT EXISTS Ordini (ID_Ordine VARCHAR(50) PRIMARY KEY, Stagione VARCHAR(50), ID_Agente VARCHAR(50), ID_Negozio VARCHAR(100), Brand VARCHAR(100), `Ordinato_€` DOUBLE, `Consegnato_€` DOUBLE, Stato_Incasso VARCHAR(50), `Incassato_€` DOUBLE, Data_Ordine DATE)'''))
            conn.execute(text('''CREATE TABLE IF NOT EXISTS Log_Consegne (ID_Ordine VARCHAR(50), Data_Consegna DATE, Valore_Consegnato DOUBLE)'''))
            conn.execute(text('''CREATE TABLE IF NOT EXISTS Log_Pagamenti (ID_Ordine VARCHAR(50), Data DATE, Importo_Pagato DOUBLE, Metodo VARCHAR(50))'''))
            conn.execute(text('''CREATE TABLE IF NOT EXISTS Liquidazioni (ID_Liq VARCHAR(50) PRIMARY KEY, Data DATE, Beneficiario VARCHAR(50), Ruolo VARCHAR(50), Importo DOUBLE, Note VARCHAR(200))'''))
            conn.execute(text('''CREATE TABLE IF NOT EXISTS Stagioni (Nome_Stagione VARCHAR(100) PRIMARY KEY, Ordinamento INT)'''))

            res = conn.execute(text("SELECT COUNT(*) FROM Agenti")).scalar()
            if res == 0:
                conn.execute(text("INSERT INTO Agenti VALUES (:id, :n, :r, :c, :m, :p)"), {"id": 'ADMIN-01', "n": 'Admin', "r": 'Superadmin', "c": '', "m": 'tua@email.it', "p": 'admin123'})
            
            res_stag = conn.execute(text("SELECT COUNT(*) FROM Stagioni")).scalar()
            if res_stag == 0:
                default_seasons = [("Autunno/Inverno 24/25 (FW)", 1), ("Primavera/Estate 25 (SS)", 2), ("Autunno/Inverno 25/26 (FW)", 3), ("Primavera/Estate 26 (SS)", 4), ("Autunno/Inverno 26/27 (FW)", 5)]
                for s, o in default_seasons:
                    conn.execute(text("INSERT INTO Stagioni VALUES (:n, :o)"), {"n": s, "o": o})

    except Exception:
        st.error("Errore di connessione. Controlla i secrets e l'IP su SiteGround.")
        st.stop()

def upgrade_db():
    queries = [
        "ALTER TABLE Ordini ADD COLUMN Metodo_Pagamento VARCHAR(50)",
        "ALTER TABLE Ordini ADD COLUMN Data_Scadenza DATE",
        "ALTER TABLE Ordini ADD COLUMN Numero_Fattura VARCHAR(50)"
    ]
    with engine.begin() as conn:
        for q in queries:
            try: conn.execute(text(q))
            except: pass

init_db()
upgrade_db()

# --- 3. MOTORE DATI (SQL) ---
def load_data(table_name):
    df = pd.read_sql_table(table_name, con=engine)
    if table_name == 'Ordini' and not df.empty:
        if 'Data_Ordine' in df.columns: df['Data_Ordine'] = pd.to_datetime(df['Data_Ordine'], errors='coerce')
        if 'Data_Scadenza' in df.columns: df['Data_Scadenza'] = pd.to_datetime(df['Data_Scadenza'], errors='coerce')
    if 'ID_Agente' in df.columns: df['ID_Agente'] = df['ID_Agente'].astype(str)
    if 'ID_Ordine' in df.columns: df['ID_Ordine'] = df['ID_Ordine'].astype(str)
    return df

def execute_query(query, params=None):
    with engine.begin() as conn:
        conn.execute(text(query), params or {})

# --- 4. EMAIL E LOGIN ---
if "auth" not in st.session_state: st.session_state.update({"auth": False, "user": None})

if not st.session_state.auth:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>GESTIONALE<span style='color: #38BDF8;'>DIGITALIMPRESA</span></h1>", unsafe_allow_html=True)
        with st.form("login_form", clear_on_submit=True):
            st.markdown("<p style='text-align: center;'>Versione: Rete Commerciale Abbigliamento ed Accessori</p>", unsafe_allow_html=True)
            u = st.text_input("Username", placeholder="ID Agente o Nome")
            p = st.text_input("Password", type="password", placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("Accedi al Sistema", type="primary", use_container_width=True):
                df_a = load_data("Agenti")
                user = df_a[(df_a['Nome'] == u) & (df_a['Password'] == p)]
                if not user.empty:
                    st.session_state.update({"auth": True, "user": user.iloc[0].to_dict()})
                    st.rerun()
                else: st.error("❌ Credenziali errate.")
    st.stop()

# --- 5. NAVIGAZIONE E NOTIFICHE SCADENZE ---
U = st.session_state.user
ROLE = U['Ruolo']

st.sidebar.markdown(f"<div style='text-align: center; padding: 20px 0;'><h2 style='margin-bottom:0;'>GESTIONALE<br><span style='color:#38BDF8;'>DIGITALIMPRESA</span></h2></div>", unsafe_allow_html=True)
st.sidebar.markdown(f"👤 **{U['Nome']}**<br>🛡️ Livello: `{ROLE}`", unsafe_allow_html=True)
st.sidebar.divider()

df_ordini = load_data("Ordini")
if not df_ordini.empty:
    oggi = pd.to_datetime(date.today())
    scadenze = df_ordini[(df_ordini['Consegnato_€'] > df_ordini['Incassato_€']) & (df_ordini['Data_Scadenza'].notna())]
    scadenze = scadenze[scadenze['Data_Scadenza'] <= oggi + pd.Timedelta(days=7)]
    
    if not scadenze.empty:
        st.sidebar.markdown("<p style='color:#EF4444; font-weight:bold;'>🚨 ALERT SCADENZE</p>", unsafe_allow_html=True)
        for _, row in scadenze.iterrows():
            giorni = (row['Data_Scadenza'] - oggi).days
            msg = f"Scaduta da {abs(giorni)} gg!" if giorni < 0 else "Scade OGGI!" if giorni == 0 else f"Scade tra {giorni} gg"
            st.sidebar.error(f"**{row['Metodo_Pagamento']}**\n\nNegozio: {row['ID_Negozio']}\n\nFattura: {row.get('Numero_Fattura', 'N/D')}\n\n{msg}")
        st.sidebar.divider()

menu_list = ["📊 Dashboard BI", "📝 Nuovo Ordine"]
if ROLE == "Superadmin":
    menu_list += ["🚚 Consegne", "💰 Incassi & Fatture", "💸 Erogazione Provvigioni", "🏪 Negozi", "🏷️ Brand e Stagioni", "👥 Agenti", "🔧 Manutenzione"]

menu = st.sidebar.radio("Seleziona Modulo:", menu_list)

st.sidebar.markdown("<br>", unsafe_allow_html=True)
if st.sidebar.button("🚪 Disconnettiti", type="primary", use_container_width=True):
    st.session_state.auth = False
    st.rerun()

# --- 6. LOGICA DELLE SEZIONI ---
if menu == "📊 Dashboard BI":
    st.markdown("## 📊 Business Intelligence & Cash Flow")
    st.markdown("<p>Monitoraggio in tempo reale delle vendite e delle provvigioni di rete.</p>", unsafe_allow_html=True)
    
    df_o = load_data("Ordini")
    df_n = load_data("Negozi")
    df_b = load_data("Brand")
    df_a = load_data("Agenti")
    df_liq = load_data("Liquidazioni")

    if df_o.empty:
        st.info("💡 Nessun ordine presente nel database.")
    else:
        df = pd.merge(df_o, df_n, left_on='ID_Negozio', right_on='Nome', how='left')
        df = pd.merge(df, df_a[['ID_Agente', 'Nome', 'Ruolo']], on='ID_Agente', suffixes=('', '_Agente'), how='left')
        
        def p2f(x): return float(str(x).replace('%','').replace(',','.')) / 100 if pd.notnull(x) and x != '' else 0.0
        df_b['rate_totale'] = df_b['Provvigione_Totale_perc'].apply(p2f)
        df_b['rate_agente'] = df_b['Quota_Agente_perc'].apply(p2f)
        
        df = pd.merge(df, df_b[['Nome_Brand', 'rate_totale', 'rate_agente']], left_on='Brand', right_on='Nome_Brand', how='left')
        df['Anno'], df['Trimestre'] = df['Data_Ordine'].dt.year, df['Data_Ordine'].dt.quarter
        
        df['Provv_Agente_Maturata'] = df.apply(lambda r: r['Consegnato_€'] * r['rate_agente'] if r['Ruolo'] != 'Superadmin' else 0, axis=1)
        df['Provv_Agente_Esigibile'] = df.apply(lambda r: r['Incassato_€'] * r['rate_agente'] if r['Ruolo'] != 'Superadmin' else 0, axis=1)
        
        df['Provv_Admin_Maturata'] = df.apply(lambda r: r['Consegnato_€'] * r['rate_totale'] if r['Ruolo'] == 'Superadmin' else r['Consegnato_€'] * (r['rate_totale'] - r['rate_agente']), axis=1)
        df['Provv_Admin_Esigibile'] = df.apply(lambda r: r['Incassato_€'] * r['rate_totale'] if r['Ruolo'] == 'Superadmin' else r['Incassato_€'] * (r['rate_totale'] - r['rate_agente']), axis=1)
        
        if ROLE != "Superadmin":
            df = df[df['ID_Agente'] == str(U['ID_Agente'])]
            df['Mio_Maturato'] = df['Provv_Agente_Maturata']
            df['Mio_Esigibile'] = df['Provv_Agente_Esigibile']
            mio_maturato = df['Mio_Maturato'].sum()
            mio_esigibile = df['Mio_Esigibile'].sum()
            liquidato = df_liq[df_liq['Beneficiario'] == U['Nome']]['Importo'].sum() if not df_liq.empty else 0
        else:
            df['Mio_Maturato'] = df['Provv_Admin_Maturata']
            df['Mio_Esigibile'] = df['Provv_Admin_Esigibile']
            mio_maturato = df['Mio_Maturato'].sum()
            mio_esigibile = df['Mio_Esigibile'].sum()
            liquidato = df_liq[df_liq['Beneficiario'] == 'Superadmin']['Importo'].sum() if not df_liq.empty else 0

        saldo_da_ricevere = mio_esigibile - liquidato

        # METRICHE
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 Maturato Lordo", f"€ {mio_maturato:,.2f}")
        c2.metric("💰 Esigibile (Fatturato)", f"€ {mio_esigibile:,.2f}")
        c3.metric("💸 Quota Liquidata", f"€ {liquidato:,.2f}")
        c4.metric("⚖️ Saldo Attivo a Credito", f"€ {saldo_da_ricevere:,.2f}")
        st.markdown("<br>", unsafe_allow_html=True)

        with st.expander("🔎 Motore di Ricerca Avanzato", expanded=True):
            f1, f2, f3, f4 = st.columns(4)
            with f1: date_filter = st.date_input("Periodo Fiscale", [date(2026,1,1), date.today()])
            with f2: anno_filter = st.multiselect("Anno Fiscale", sorted(df['Anno'].dropna().unique().astype(int).tolist()))
            with f3: brand_filter = st.multiselect("Filtro Brand", df['Brand'].dropna().unique())
            with f4: stag_filter = st.multiselect("Filtro Stagione", df['Stagione'].dropna().unique())

        mask = pd.Series(True, index=df.index)
        if len(date_filter) == 2: mask &= (df['Data_Ordine'] >= pd.to_datetime(date_filter[0])) & (df['Data_Ordine'] <= pd.to_datetime(date_filter[1]))
        if anno_filter: mask &= df['Anno'].isin(anno_filter)
        if brand_filter: mask &= df['Brand'].isin(brand_filter)
        if stag_filter: mask &= df['Stagione'].isin(stag_filter)
        
        df_filtered = df[mask]

        st.markdown("<br>", unsafe_allow_html=True)
        tab_geo, tab_produttore, tab_matrice, tab_rete = st.tabs(["🌍 Dati Geografici", "📈 Report Aziende", "🎯 Matrice Clienti", "👥 Performance Rete"])
        
        with tab_geo:
            st.markdown("<br>", unsafe_allow_html=True)
            col_reg, col_prov, col_cit = st.columns(3)
            with col_reg:
                st.markdown("#### Volumi per Regione")
                if 'Regione' in df_filtered.columns: st.dataframe(df_filtered.groupby('Regione').agg({'ID_Ordine':'count', 'Ordinato_€':'sum', 'Mio_Maturato':'sum'}).sort_values('Ordinato_€', ascending=False), use_container_width=True)
            with col_prov:
                st.markdown("#### Volumi per Provincia")
                if 'Provincia' in df_filtered.columns: st.dataframe(df_filtered.groupby('Provincia').agg({'ID_Ordine':'count', 'Ordinato_€':'sum', 'Mio_Maturato':'sum'}).sort_values('Ordinato_€', ascending=False), use_container_width=True)
            with col_cit:
                st.markdown("#### Top 15 Città")
                if 'Citta' in df_filtered.columns: st.dataframe(df_filtered.groupby('Citta').agg({'ID_Ordine':'count', 'Ordinato_€':'sum', 'Mio_Maturato':'sum'}).sort_values('Ordinato_€', ascending=False).head(15), use_container_width=True)

        with tab_produttore:
            st.markdown("<br>#### Ordinato Globale per Casa Mandante", unsafe_allow_html=True)
            if not df_filtered.empty:
                df_prod = df_filtered.groupby(['Brand', 'Stagione']).agg({'ID_Ordine': 'count', 'Ordinato_€': 'sum', 'Consegnato_€': 'sum'}).reset_index().sort_values(['Brand', 'Stagione'])
                df_prod.rename(columns={'ID_Ordine': 'N° Ordini', 'Ordinato_€': 'Ordinato Lordo (€)', 'Consegnato_€': 'Consegnato Netto (€)'}, inplace=True)
                st.dataframe(df_prod.style.format({'Ordinato Lordo (€)': '{:,.2f}', 'Consegnato Netto (€)': '{:,.2f}'}), use_container_width=True)
                
        with tab_matrice:
            st.markdown("<br>#### Matrice Storico Acquisti / Scoperti", unsafe_allow_html=True)
            if not df_filtered.empty:
                matrice = df_filtered.pivot_table(index='ID_Negozio', columns=['Brand', 'Stagione'], values='Ordinato_€', aggfunc='sum').fillna(0)
                # Adattato per il dark mode: Rosso e Verde scuri per non accecare
                def highlight_zeros(val): return 'background-color: #450a0a; color: #fca5a5' if val == 0 else 'background-color: #052e16; color: #86efac'
                st.dataframe(matrice.style.format("{:,.2f} €").applymap(highlight_zeros), use_container_width=True)
            
        with tab_rete:
            st.markdown("<br>", unsafe_allow_html=True)
            if ROLE == "Superadmin":
                st.markdown("#### Classifica Agenti (Leaderboard)")
                st.dataframe(df_filtered.groupby('Nome_Agente').agg({'Ordinato_€':'sum', 'Consegnato_€':'sum', 'Mio_Maturato':'sum'}).sort_values('Ordinato_€', ascending=False), use_container_width=True)
            else: st.info("Le performance globali della rete sono classificate come dati confidenziali direzionali.")

elif menu == "📝 Nuovo Ordine":
    st.markdown("## 📝 Emissione Nuovo Ordine")
    df_n, df_b, df_a = load_data("Negozi"), load_data("Brand"), load_data("Agenti")
    df_s = load_data("Stagioni").sort_values('Ordinamento')
    lista_stagioni = df_s['Nome_Stagione'].tolist() if not df_s.empty else ["Nessuna stagione"]
    
    with st.form("form_ordine", clear_on_submit=True):
        st.markdown("#### 1. Dati Commerciali Base")
        c1, c2, c3 = st.columns(3)
        with c1:
            id_o = st.text_input("Codice Identificativo Ordine")
            neg = st.selectbox("Seleziona Negozio Cliente", df_n['Nome'].tolist() if not df_n.empty else [])
        with c2:
            brand = st.selectbox("Azienda / Brand", df_b['Nome_Brand'].tolist() if not df_b.empty else [])
            stagione = st.selectbox("Collezione Stagionale", lista_stagioni)
        with c3:
            val = st.number_input("Valore Lordo Ordine (€)", min_value=0.0)
            agente_id = st.selectbox("Riferimento Commerciale (Agente)", df_a['ID_Agente'].tolist()) if ROLE == "Superadmin" else U['ID_Agente']
            
        st.markdown("<hr style='border: 1px solid #334155;'>", unsafe_allow_html=True)
        st.markdown("#### 2. Termini e Scadenze")
        c4, c5, c6 = st.columns(3)
        with c4: data_o = st.date_input("Data Emissione Ordine", date.today())
        with c5: metodo = st.selectbox("Metodo Pagamento Richiesto", ["Da Definire", "RiBa 30gg", "RiBa 60gg", "RiBa 90gg", "Bonifico", "Assegno", "Contanti"])
        with c6: scadenza = st.date_input("Scadenza Concordata", date.today() + timedelta(days=30))

        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("Archivia e Salva Ordine Definitivo", type="primary"):
            if id_o and neg and brand:
                try:
                    query = """INSERT INTO Ordini (ID_Ordine, Stagione, ID_Agente, ID_Negozio, Brand, `Ordinato_€`, `Consegnato_€`, Stato_Incasso, `Incassato_€`, Data_Ordine, Metodo_Pagamento, Data_Scadenza, Numero_Fattura) 
                               VALUES (:id, :stag, :ag, :neg, :b, :v, 0.0, 'In Attesa', 0.0, :d, :mp, :ds, '')"""
                    execute_query(query, {"id": id_o, "stag": stagione, "ag": str(agente_id), "neg": neg, "b": brand, "v": val, "d": str(data_o), "mp": metodo, "ds": str(scadenza)})
                    st.success("✅ Ordine archiviato correttamente nel Cloud aziendale.")
                except Exception as e:
                    st.error("⚠️ Attenzione: il Codice Ordine inserito è già presente a sistema.")
            else: st.error("Errore: Compila tutti i campi obbligatori prima di procedere.")

elif menu == "💰 Incassi & Fatture":
    st.markdown("## 💰 Riconciliazione Fatture e Incassi")
    df_o = load_data("Ordini")
    da_inc = df_o[(df_o['Consegnato_€'] > 0) & (df_o['Incassato_€'] < df_o['Consegnato_€'])]
    
    if not da_inc.empty:
        sel = st.selectbox("Cerca Documento Aperto (Digita per cercare):", (da_inc['ID_Ordine'] + " | " + da_inc['ID_Negozio'] + " | Insoluto: € " + (da_inc['Consegnato_€'] - da_inc['Incassato_€']).astype(str)).tolist())
        id_sel = sel.split(" | ")[0]
        r_dati = da_inc[da_inc['ID_Ordine'] == id_sel].iloc[0]
        residuo = r_dati['Consegnato_€'] - r_dati['Incassato_€']
        
        with st.form("form_incasso"):
            st.markdown(f"**Dati Attuali:** Fattura: `{r_dati.get('Numero_Fattura', 'N/D')}` | Metodo: `{r_dati.get('Metodo_Pagamento', 'N/D')}` | Scadenza: `{r_dati.get('Data_Scadenza', 'N/D')}`")
            c1, c2, c3 = st.columns(3)
            with c1: nuovo_nf = st.text_input("Correggi N° Fattura", value=str(r_dati.get('Numero_Fattura', '')))
            with c2: nuovo_mp = st.selectbox("Modifica Metodo", ["RiBa", "Bonifico", "Assegno", "Contanti"], index=0 if r_dati.get('Metodo_Pagamento') and 'RiBa' in r_dati.get('Metodo_Pagamento') else 1)
            with c3: nuova_scadenza = st.date_input("Ricalcola Scadenza", pd.to_datetime(r_dati['Data_Scadenza']) if pd.notnull(r_dati.get('Data_Scadenza')) else date.today())
            
            st.markdown("<hr style='border: 1px dashed #334155;'>", unsafe_allow_html=True)
            val_inc = st.number_input("Immetti Transazione Ricevuta (€)", max_value=residuo, min_value=0.00, value=0.00)
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.form_submit_button("Applica Modifiche ed Esegui Riconciliazione", type="primary"):
                execute_query("UPDATE Ordini SET Numero_Fattura = :nf, Metodo_Pagamento = :mp, Data_Scadenza = :ds WHERE ID_Ordine = :id", {"nf": nuovo_nf, "mp": nuovo_mp, "ds": str(nuova_scadenza), "id": id_sel})
                if val_inc > 0:
                    execute_query("INSERT INTO Log_Pagamenti VALUES (:id, :d, :i, :m)", {"id": id_sel, "d": str(date.today()), "i": val_inc, "m": nuovo_mp})
                    execute_query("UPDATE Ordini SET `Incassato_€` = :i WHERE ID_Ordine = :id", {"i": r_dati['Incassato_€'] + val_inc, "id": id_sel})
                    st.success(f"Pagamento di €{val_inc} validato e registrato a bilancio.")
                else:
                    st.success("Dati fatturazione aggiornati con successo.")
                st.rerun()
    else: st.success("🎉 Bilancio perfetto: non risultano fatture insolute nel sistema.")

elif menu == "💸 Erogazione Provvigioni":
    st.markdown("## 💸 Movimentazione Finanziaria Provvigioni")
    df_a = load_data("Agenti")
    lista_beneficiari = ["Superadmin (Provvigioni Ricevute da Brand)"] + df_a[df_a['Ruolo'] != 'Superadmin']['Nome'].tolist()
    
    with st.form("form_liquidazione"):
        c1, c2 = st.columns(2)
        with c1:
            beneficiario = st.selectbox("Destinatario / Mittente Transazione", lista_beneficiari)
            importo = st.number_input("Ammontare Bonifico/Transazione (€)", min_value=0.01)
        with c2:
            data_liq = st.date_input("Data Effettiva Movimento", date.today())
            note = st.text_input("Oggetto / Note Contabili")
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("Disponi e Salva Transazione", type="primary"):
            ruolo = 'Superadmin' if beneficiario.startswith("Superadmin") else 'Agente'
            nome_db = 'Superadmin' if ruolo == 'Superadmin' else beneficiario
            execute_query("INSERT INTO Liquidazioni VALUES (:id, :d, :b, :r, :i, :n)", {"id": f"LIQ-{int(time.time())}", "d": str(data_liq), "b": nome_db, "r": ruolo, "i": importo, "n": note})
            st.success("Transazione approvata. I contatori della Dashboard sono stati aggiornati.")
            st.rerun()

    st.markdown("<br>#### Registro Libro Giornale Liquidazioni", unsafe_allow_html=True)
    df_liq = load_data("Liquidazioni")
    if not df_liq.empty: st.dataframe(df_liq.sort_values('Data', ascending=False), use_container_width=True)

elif menu == "🚚 Consegne":
    st.markdown("## 🚚 Logistica e Scarico DDT")
    df_o = load_data("Ordini")
    da_consegnare = df_o[df_o['Consegnato_€'] < df_o['Ordinato_€']]
    if not da_consegnare.empty:
        sel = st.selectbox("Ordini in Attesa di Merce:", (da_consegnare['ID_Ordine'] + " | " + da_consegnare['ID_Negozio']).tolist())
        id_sel = sel.split(" | ")[0]
        r_dati = da_consegnare[da_consegnare['ID_Ordine'] == id_sel].iloc[0]
        residuo = r_dati['Ordinato_€'] - r_dati['Consegnato_€']
        val_scarico = st.number_input(f"Valore Bolla/DDT Attuale (€) - Max {residuo:,.2f}", max_value=residuo, min_value=0.01)
        if st.button("Registra Bolla di Consegna", type="primary"):
            nuovo = r_dati['Consegnato_€'] + val_scarico
            execute_query("INSERT INTO Log_Consegne VALUES (:id, :d, :v)", {"id": id_sel, "d": str(date.today()), "v": val_scarico})
            execute_query("UPDATE Ordini SET `Consegnato_€` = :c, Stato_Incasso = :s WHERE ID_Ordine = :id", {"c": nuovo, "s": "Consegnato" if nuovo >= r_dati['Ordinato_€'] else "Parziale", "id": id_sel})
            st.success("DDT Archiviato nel server!"); st.rerun()
    else: st.success("Nessun carico merci pendente.")

elif menu == "🏪 Negozi":
    st.markdown("## 🏪 Gestione Anagrafica Negozi")
    with st.form("f_neg", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1: n, p = st.text_input("Ragione Sociale Completa"), st.text_input("P.IVA / Codice Fiscale")
        with c2: 
            c = st.text_input("Città Sede Operativa")
            c_prov, c_reg = st.columns(2)
            with c_prov: pr = st.text_input("Prov. (Sigla)")
            with c_reg: r = st.text_input("Regione")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("Inserisci Nuova Azienda Cliente", type="primary") and n:
            execute_query("REPLACE INTO Negozi VALUES (:n, :p, :c, :pr, :r)", {"n": n, "p": p, "c": c, "pr": pr, "r": r})
            st.success("Scheda cliente creata o aggiornata."); st.rerun()
    st.dataframe(load_data("Negozi"), use_container_width=True)

elif menu == "🏷️ Brand e Stagioni":
    st.markdown("## 🏷️ Architettura Sistema Commerciale")
    tab_brand, tab_stagioni = st.tabs(["🏢 Impostazioni Brand", "📅 Timeline Stagioni"])
    
    with tab_brand:
        with st.form("f_brand", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: ib, nb = st.text_input("Codice Brand interno"), st.text_input("Ragione Sociale Mandante")
            with c2: qt, qa = st.text_input("Mark-up Globale (%)"), st.text_input("Split Rete Vendita (%)")
            if st.form_submit_button("Aggiungi o Aggiorna Mandante", type="primary") and ib:
                execute_query("REPLACE INTO Brand VALUES (:i, :n, :qt, '0%', :qa)", {"i": ib, "n": nb, "qt": qt, "qa": qa})
                st.success("Parametri commerciali salvati."); st.rerun()
        st.dataframe(load_data("Brand"), use_container_width=True)
        
    with tab_stagioni:
        with st.form("f_stagione", clear_on_submit=True):
            c1, c2 = st.columns([3, 1])
            with c1: n_stag = st.text_input("Etichetta Campagna Vendite (Es. PE 2028)")
            with c2: ord_stag = st.number_input("Priorità Menu", min_value=1, value=10)
            if st.form_submit_button("Inizializza Nuova Stagione", type="primary") and n_stag:
                execute_query("REPLACE INTO Stagioni VALUES (:n, :o)", {"n": n_stag, "o": ord_stag})
                st.success("Stagione integrata nel menu a tendina ordini."); st.rerun()
        df_s = load_data("Stagioni").sort_values('Ordinamento')
        st.dataframe(df_s, use_container_width=True)

elif menu == "👥 Agenti":
    st.markdown("## 👥 Amministrazione Risorse Umane")
    df_a = load_data("Agenti")
    tab1, tab2 = st.tabs(["➕ Onboarding Nuova Risorsa", "❌ Termine Contratto"])
    with tab1:
        with st.form("f_agente", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: aid, anome, arole = st.text_input("Matricola Rete (Es. AG-001)"), st.text_input("Nome Anagrafico"), st.selectbox("Diritti di Sistema", ["Agente", "Superadmin"])
            with c2: amail, apass = st.text_input("Email Aziendale"), st.text_input("Password Iniziale", type="password")
            if st.form_submit_button("Genera Account di Rete", type="primary") and aid:
                execute_query("REPLACE INTO Agenti VALUES (:i, :n, :r, '', :m, :p)", {"i": aid, "n": anome, "r": arole, "m": amail, "p": apass})
                st.success("Profilo di rete creato con successo."); st.rerun()
    with tab2:
        if not df_a.empty:
            agenti_eliminabili = df_a[df_a['ID_Agente'] != U['ID_Agente']]['ID_Agente'].tolist()
            if agenti_eliminabili:
                target_agente = st.selectbox("Seleziona matricola da disabilitare:", agenti_eliminabili)
                if st.button("Revoca Accessi", type="primary"):
                    execute_query("DELETE FROM Agenti WHERE ID_Agente = :id", {"id": target_agente})
                    st.success("Accessi di rete disabilitati."); st.rerun()
    st.dataframe(df_a.drop(columns=['Password']), use_container_width=True)

elif menu == "🔧 Manutenzione":
    st.markdown("## 🔧 Strumenti DB Superadmin")
    df_o = load_data("Ordini")
    if not df_o.empty:
        with st.container(border=True):
            target = st.selectbox("Seleziona riga Ordine per eliminazione forzata:", df_o['ID_Ordine'].tolist())
            conferma = st.checkbox(f"Confermo di aver compreso che l'eliminazione dell'ordine {target} distruggerà irreversibilmente anche le relative fatture, DDT e log di incasso.")
            if st.button("🔥 Esegui Cancellazione a Cascata", type="primary", disabled=not conferma):
                execute_query("DELETE FROM Ordini WHERE ID_Ordine = :id", {"id": target})
                execute_query("DELETE FROM Log_Consegne WHERE ID_Ordine = :id", {"id": target})
                execute_query("DELETE FROM Log_Pagamenti WHERE ID_Ordine = :id", {"id": target})
                st.success("Record vaporizzato dal Database SQL."); st.rerun()




