import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, timedelta
import time

# --- 1. CONFIGURAZIONE PAGINA E DESIGN ---
st.set_page_config(page_title="Network 2026", layout="wide", page_icon="👔")

def inject_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        [data-testid="stMetric"] {
            background-color: rgba(175, 175, 175, 0.1); padding: 1.2rem;
            border-radius: 12px; border-left: 5px solid #0068c9;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); transition: transform 0.2s ease;
        }
        [data-testid="stMetric"]:hover { transform: translateY(-3px); box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1); }
        div.stButton > button { border-radius: 8px; font-weight: 600; transition: all 0.3s ease; }
        .stTextInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input { border-radius: 8px; }
        h1, h2, h3 { font-weight: 700 !important; letter-spacing: -0.5px; }
        [data-testid="stSidebar"] { background-color: rgba(175, 175, 175, 0.03); border-right: 1px solid rgba(175, 175, 175, 0.2); }
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

            res = conn.execute(text("SELECT COUNT(*) FROM Agenti")).scalar()
            if res == 0:
                conn.execute(text("INSERT INTO Agenti VALUES (:id, :n, :r, :c, :m, :p)"), {"id": 'ADMIN-01', "n": 'Admin', "r": 'Superadmin', "c": '', "m": 'tua@email.it', "p": 'admin123'})
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
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<h2 style='text-align: center; color: #0068c9;'>Area Riservata Rete Vendita</h2>", unsafe_allow_html=True)
        with st.form("login_form", clear_on_submit=True):
            u = st.text_input("Nome Utente", placeholder="Es. Mario Rossi")
            p = st.text_input("Password", type="password", placeholder="••••••••")
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

st.sidebar.markdown(f"### 👤 Ciao, **{U['Nome']}**")
st.sidebar.caption(f"🛡️ Livello Accesso: `{ROLE}`")
st.sidebar.divider()

df_ordini = load_data("Ordini")
if not df_ordini.empty:
    oggi = pd.to_datetime(date.today())
    scadenze = df_ordini[(df_ordini['Consegnato_€'] > df_ordini['Incassato_€']) & (df_ordini['Data_Scadenza'].notna())]
    scadenze = scadenze[scadenze['Data_Scadenza'] <= oggi + pd.Timedelta(days=7)]
    
    if not scadenze.empty:
        st.sidebar.markdown("🚨 **ATTENZIONE SCADENZE**")
        for _, row in scadenze.iterrows():
            giorni = (row['Data_Scadenza'] - oggi).days
            msg = f"Scaduta da {abs(giorni)} gg!" if giorni < 0 else "Scade OGGI!" if giorni == 0 else f"Scade tra {giorni} gg"
            st.sidebar.error(f"**{row['Metodo_Pagamento']}** - {row['ID_Negozio']}\n\nFattura: {row.get('Numero_Fattura', 'N/D')}\n\n{msg}")
        st.sidebar.divider()

menu_list = ["📊 Dashboard BI", "📝 Nuovo Ordine"]
if ROLE == "Superadmin":
    menu_list += ["🚚 Consegne", "💰 Incassi & Fatture", "💸 Erogazione Provvigioni", "🏪 Negozi", "🏷️ Brand", "👥 Agenti", "🔧 Manutenzione"]

menu = st.sidebar.radio("Menu Navigazione", menu_list)

if st.sidebar.button("🚪 Disconnettiti", use_container_width=True):
    st.session_state.auth = False
    st.rerun()

# --- 6. LOGICA DELLE SEZIONI ---
if menu == "📊 Dashboard BI":
    st.markdown("## 📊 Business Intelligence & Cash Flow")
    
    df_o = load_data("Ordini")
    df_n = load_data("Negozi")
    df_b = load_data("Brand")
    df_a = load_data("Agenti")
    df_liq = load_data("Liquidazioni")

    if df_o.empty:
        st.info("💡 Nessun ordine presente.")
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
        
        # FIX: Riapplicate le colonne al dataframe per permettere i calcoli nei grafici
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
        st.markdown("### 🏦 Stato Finanziario Provvigioni")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("⏳ Maturato (Merci Consegnate)", f"€ {mio_maturato:,.2f}")
        c2.metric("💰 Esigibile (Fatture Incassate)", f"€ {mio_esigibile:,.2f}")
        c3.metric("💸 Già Liquidato (Pagato)", f"€ {liquidato:,.2f}")
        c4.metric("⚖️ Saldo Netto da Ricevere", f"€ {saldo_da_ricevere:,.2f}")

        st.divider()

        with st.expander("🔎 Filtri Avanzati di Ricerca", expanded=True):
            f1, f2, f3, f4 = st.columns(4)
            with f1: date_filter = st.date_input("Calendario", [date(2026,1,1), date.today()])
            with f2: anno_filter = st.multiselect("Anno Fiscale", sorted(df['Anno'].dropna().unique().astype(int).tolist()))
            with f3: brand_filter = st.multiselect("Seleziona Brand", df['Brand'].dropna().unique())
            with f4: stag_filter = st.multiselect("Stagione", df['Stagione'].dropna().unique())

        mask = pd.Series(True, index=df.index)
        if len(date_filter) == 2: mask &= (df['Data_Ordine'] >= pd.to_datetime(date_filter[0])) & (df['Data_Ordine'] <= pd.to_datetime(date_filter[1]))
        if anno_filter: mask &= df['Anno'].isin(anno_filter)
        if brand_filter: mask &= df['Brand'].isin(brand_filter)
        if stag_filter: mask &= df['Stagione'].isin(stag_filter)
        
        df_filtered = df[mask]

        tab_geo, tab_produttore, tab_matrice, tab_rete = st.tabs(["🌍 Geografia", "📈 Report Produttori", "🎯 Matrice Clienti", "👥 Rete Vendita"])
        
        with tab_geo:
            col_reg, col_prov, col_cit = st.columns(3)
            with col_reg:
                if 'Regione' in df_filtered.columns:
                    st.dataframe(df_filtered.groupby('Regione').agg({'ID_Ordine':'count', 'Ordinato_€':'sum', 'Mio_Maturato':'sum'}).sort_values('Ordinato_€', ascending=False), use_container_width=True)
            with col_prov:
                if 'Provincia' in df_filtered.columns:
                    st.dataframe(df_filtered.groupby('Provincia').agg({'ID_Ordine':'count', 'Ordinato_€':'sum', 'Mio_Maturato':'sum'}).sort_values('Ordinato_€', ascending=False), use_container_width=True)
            with col_cit:
                if 'Citta' in df_filtered.columns:
                    st.dataframe(df_filtered.groupby('Citta').agg({'ID_Ordine':'count', 'Ordinato_€':'sum', 'Mio_Maturato':'sum'}).sort_values('Ordinato_€', ascending=False).head(15), use_container_width=True)

        with tab_produttore:
            st.markdown("#### Ordinato per Produttore / Azienda")
            st.caption("Visualizza i totali raccolti divisi per Brand e Stagione (Replica del Report Azienda PDF)")
            if not df_filtered.empty:
                df_prod = df_filtered.groupby(['Brand', 'Stagione']).agg({
                    'ID_Ordine': 'count',
                    'Ordinato_€': 'sum',
                    'Consegnato_€': 'sum'
                }).reset_index().sort_values(['Brand', 'Stagione'])
                df_prod.rename(columns={'ID_Ordine': 'Q.tà Ordini', 'Ordinato_€': 'Totale Ordinato (€)', 'Consegnato_€': 'Totale Consegnato (€)'}, inplace=True)
                
                st.dataframe(df_prod.style.format({'Totale Ordinato (€)': '{:,.2f}', 'Totale Consegnato (€)': '{:,.2f}'}), use_container_width=True)
                
        with tab_matrice:
            st.markdown("#### Matrice di Copertura per Cliente (Storico Acquisti / Vuoti)")
            st.caption("Verifica quali clienti hanno confermato o saltato l'acquisto di una determinata collezione stagionale.")
            if not df_filtered.empty:
                matrice = df_filtered.pivot_table(
                    index='ID_Negozio', 
                    columns=['Brand', 'Stagione'], 
                    values='Ordinato_€', 
                    aggfunc='sum'
                ).fillna(0)
                
                def highlight_zeros(val):
                    color = '#ffcccc' if val == 0 else '#ccffcc'
                    return f'background-color: {color}'
                
                st.dataframe(matrice.style.format("{:,.2f} €").applymap(highlight_zeros), use_container_width=True)
            
        with tab_rete:
            if ROLE == "Superadmin":
                st.markdown("#### Classifica Agenti e Portafoglio")
                st.dataframe(df_filtered.groupby('Nome_Agente').agg({'Ordinato_€':'sum', 'Consegnato_€':'sum', 'Mio_Maturato':'sum'}).sort_values('Ordinato_€', ascending=False), use_container_width=True)
            else:
                st.info("I dati aggregati della rete sono visibili solo alla direzione.")

elif menu == "📝 Nuovo Ordine":
    st.markdown("## 📝 Registra Nuovo Ordine")
    df_n, df_b, df_a = load_data("Negozi"), load_data("Brand"), load_data("Agenti")
    
    with st.form("form_ordine", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            id_o = st.text_input("Codice Identificativo Ordine")
            neg = st.selectbox("Seleziona Negozio", df_n['Nome'].tolist() if not df_n.empty else [])
        with c2:
            brand = st.selectbox("Seleziona Brand", df_b['Nome_Brand'].tolist() if not df_b.empty else [])
            stagione = st.selectbox("Seleziona Stagione", ["Autunno/Inverno 24/25 (FW)", "Primavera/Estate 25 (SS)", "Autunno/Inverno 25/26 (FW)", "Primavera/Estate 26 (SS)", "Autunno/Inverno 26/27 (FW)"])
        with c3:
            val = st.number_input("Valore Lordo Ordine (€)", min_value=0.0)
            agente_id = st.selectbox("Assegnato a:", df_a['ID_Agente'].tolist()) if ROLE == "Superadmin" else U['ID_Agente']
            
        st.markdown("#### 💳 Condizioni di Pagamento Concordate")
        c4, c5, c6 = st.columns(3)
        with c4: data_o = st.date_input("Data Sottoscrizione", date.today())
        with c5: metodo = st.selectbox("Metodo Previsto", ["Da Definire", "RiBa 30gg", "RiBa 60gg", "RiBa 90gg", "Bonifico", "Assegno", "Contanti"])
        with c6: scadenza = st.date_input("Data Scadenza Prevista", date.today() + timedelta(days=30))

        if st.form_submit_button("Conferma e Salva Ordine", type="primary"):
            if id_o and neg and brand:
                try:
                    query = """INSERT INTO Ordini (ID_Ordine, Stagione, ID_Agente, ID_Negozio, Brand, `Ordinato_€`, `Consegnato_€`, Stato_Incasso, `Incassato_€`, Data_Ordine, Metodo_Pagamento, Data_Scadenza, Numero_Fattura) 
                               VALUES (:id, :stag, :ag, :neg, :b, :v, 0.0, 'In Attesa', 0.0, :d, :mp, :ds, '')"""
                    params = {"id": id_o, "stag": stagione, "ag": str(agente_id), "neg": neg, "b": brand, "v": val, "d": str(data_o), "mp": metodo, "ds": str(scadenza)}
                    execute_query(query, params)
                    st.success("✅ Ordine registrato con successo!")
                except Exception as e:
                    st.error("⚠️ Errore: Codice Identificativo Ordine già esistente.")
            else: st.error("Compila i campi obbligatori.")

elif menu == "💰 Incassi & Fatture":
    st.markdown("## 💰 Gestione Fatture, Scadenze e Incassi")
    df_o = load_data("Ordini")
    da_inc = df_o[(df_o['Consegnato_€'] > 0) & (df_o['Incassato_€'] < df_o['Consegnato_€'])]
    
    if not da_inc.empty:
        sel = st.selectbox("Seleziona Ordine/DDT da Incassare o Modificare:", (da_inc['ID_Ordine'] + " | " + da_inc['ID_Negozio'] + " | Rimanenza: € " + (da_inc['Consegnato_€'] - da_inc['Incassato_€']).astype(str)).tolist())
        id_sel = sel.split(" | ")[0]
        r_dati = da_inc[da_inc['ID_Ordine'] == id_sel].iloc[0]
        residuo = r_dati['Consegnato_€'] - r_dati['Incassato_€']
        
        with st.form("form_incasso"):
            st.markdown(f"**Dettagli Attuali:** Fattura: `{r_dati.get('Numero_Fattura', 'N/D')}` | Metodo: `{r_dati.get('Metodo_Pagamento', 'N/D')}` | Scadenza: `{r_dati.get('Data_Scadenza', 'N/D')}`")
            c1, c2, c3 = st.columns(3)
            with c1: nuovo_nf = st.text_input("Aggiorna N° Fattura", value=str(r_dati.get('Numero_Fattura', '')))
            with c2: nuovo_mp = st.selectbox("Modifica Metodo", ["RiBa", "Bonifico", "Assegno", "Contanti"], index=0 if r_dati.get('Metodo_Pagamento') and 'RiBa' in r_dati.get('Metodo_Pagamento') else 1)
            with c3: nuova_scadenza = st.date_input("Modifica Scadenza", pd.to_datetime(r_dati['Data_Scadenza']) if pd.notnull(r_dati.get('Data_Scadenza')) else date.today())
            
            st.divider()
            val_inc = st.number_input("Registra Nuovo Incasso Reale (€)", max_value=residuo, min_value=0.00, value=0.00)
            
            if st.form_submit_button("Salva Modifiche / Registra Pagamento", type="primary"):
                execute_query("UPDATE Ordini SET Numero_Fattura = :nf, Metodo_Pagamento = :mp, Data_Scadenza = :ds WHERE ID_Ordine = :id", {"nf": nuovo_nf, "mp": nuovo_mp, "ds": str(nuova_scadenza), "id": id_sel})
                if val_inc > 0:
                    nuovo_tot = r_dati['Incassato_€'] + val_inc
                    execute_query("INSERT INTO Log_Pagamenti VALUES (:id, :d, :i, :m)", {"id": id_sel, "d": str(date.today()), "i": val_inc, "m": nuovo_mp})
                    execute_query("UPDATE Ordini SET `Incassato_€` = :i WHERE ID_Ordine = :id", {"i": nuovo_tot, "id": id_sel})
                    st.success(f"Aggiornato! Incasso di €{val_inc} registrato.")
                else:
                    st.success("Dati fattura e scadenza aggiornati correttamente.")
                st.rerun()
    else: st.success("🎉 Non ci sono fatture pendenti o insoluti!")

elif menu == "💸 Erogazione Provvigioni":
    st.markdown("## 💸 Registro Liquidazione Provvigioni")
    df_a = load_data("Agenti")
    lista_beneficiari = ["Superadmin (Provvigioni Ricevute)"] + df_a[df_a['Ruolo'] != 'Superadmin']['Nome'].tolist()
    
    with st.form("form_liquidazione"):
        c1, c2 = st.columns(2)
        with c1:
            beneficiario = st.selectbox("Verso chi è la transazione?", lista_beneficiari)
            importo = st.number_input("Importo Liquidato (€)", min_value=0.01)
        with c2:
            data_liq = st.date_input("Data Transazione", date.today())
            note = st.text_input("Note (Es. Saldo Provvigioni Trimestre 1)")
            
        if st.form_submit_button("Registra Pagamento Provvigioni", type="primary"):
            id_liq = f"LIQ-{int(time.time())}"
            ruolo = 'Superadmin' if beneficiario == "Superadmin (Provvigioni Ricevute)" else 'Agente'
            nome_db = 'Superadmin' if ruolo == 'Superadmin' else beneficiario
            execute_query("INSERT INTO Liquidazioni VALUES (:id, :d, :b, :r, :i, :n)", {"id": id_liq, "d": str(data_liq), "b": nome_db, "r": ruolo, "i": importo, "n": note})
            st.success("Transazione contabile registrata!")
            st.rerun()

    df_liq = load_data("Liquidazioni")
    if not df_liq.empty: st.dataframe(df_liq.sort_values('Data', ascending=False), use_container_width=True)

elif menu == "🚚 Consegne":
    st.markdown("## 🚚 Gestione Scarico Merci (DDT)")
    df_o = load_data("Ordini")
    da_consegnare = df_o[df_o['Consegnato_€'] < df_o['Ordinato_€']]
    if not da_consegnare.empty:
        sel = st.selectbox("Ordini in Lavorazione:", (da_consegnare['ID_Ordine'] + " | " + da_consegnare['ID_Negozio']).tolist())
        id_sel = sel.split(" | ")[0]
        r_dati = da_consegnare[da_consegnare['ID_Ordine'] == id_sel].iloc[0]
        residuo = r_dati['Ordinato_€'] - r_dati['Consegnato_€']
        val_scarico = st.number_input("Valore DDT Attuale (€)", max_value=residuo, min_value=0.01)
        if st.button("Registra Consegna Merce", type="primary"):
            nuovo = r_dati['Consegnato_€'] + val_scarico
            stato = "Consegnato" if nuovo >= r_dati['Ordinato_€'] else "Parziale"
            execute_query("INSERT INTO Log_Consegne VALUES (:id, :d, :v)", {"id": id_sel, "d": str(date.today()), "v": val_scarico})
            execute_query("UPDATE Ordini SET `Consegnato_€` = :c, Stato_Incasso = :s WHERE ID_Ordine = :id", {"c": nuovo, "s": stato, "id": id_sel})
            st.success("DDT Registrato!"); st.rerun()
    else: st.success("🎉 Tutte le merci ordinate sono state consegnate.")

elif menu == "🏪 Negozi":
    st.markdown("## 🏪 Anagrafica Negozi")
    with st.form("f_neg", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1: n, p = st.text_input("Ragione Sociale"), st.text_input("Partita IVA")
        with c2: 
            c = st.text_input("Città")
            c_prov, c_reg = st.columns(2)
            with c_prov: pr = st.text_input("Provincia (Es. MI)")
            with c_reg: r = st.text_input("Regione")
        if st.form_submit_button("Aggiungi o Aggiorna", type="primary") and n:
            execute_query("REPLACE INTO Negozi VALUES (:n, :p, :c, :pr, :r)", {"n": n, "p": p, "c": c, "pr": pr, "r": r})
            st.success("Salvato!"); st.rerun()
    st.dataframe(load_data("Negozi"), use_container_width=True)

elif menu == "🏷️ Brand":
    st.markdown("## 🏷️ Gestione Brand")
    with st.form("f_brand", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1: ib, nb = st.text_input("ID Brand"), st.text_input("Nome Commerciale")
        with c2: qt, qa = st.text_input("Provvigione Totale %"), st.text_input("Quota Agente %")
        if st.form_submit_button("Salva Configurazione", type="primary") and ib:
            execute_query("REPLACE INTO Brand VALUES (:i, :n, :qt, '0%', :qa)", {"i": ib, "n": nb, "qt": qt, "qa": qa})
            st.success("Salvato!"); st.rerun()
    st.dataframe(load_data("Brand"), use_container_width=True)

elif menu == "👥 Agenti":
    st.markdown("## 👥 Gestione Rete Commerciale")
    df_a = load_data("Agenti")
    tab1, tab2 = st.tabs(["➕ Crea / Modifica", "❌ Licenzia"])
    with tab1:
        with st.form("f_agente", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: aid, anome, arole = st.text_input("ID Agente"), st.text_input("Nome"), st.selectbox("Ruolo", ["Agente", "Superadmin"])
            with c2: amail, apass = st.text_input("Email"), st.text_input("Password", type="password")
            if st.form_submit_button("Salva Account", type="primary") and aid:
                execute_query("REPLACE INTO Agenti VALUES (:i, :n, :r, '', :m, :p)", {"i": aid, "n": anome, "r": arole, "m": amail, "p": apass})
                st.success("Salvato!"); st.rerun()
    with tab2:
        if not df_a.empty:
            agenti_eliminabili = df_a[df_a['ID_Agente'] != U['ID_Agente']]['ID_Agente'].tolist()
            if agenti_eliminabili:
                target_agente = st.selectbox("Seleziona Agente da rimuovere:", agenti_eliminabili)
                if st.button("Elimina", type="primary"):
                    execute_query("DELETE FROM Agenti WHERE ID_Agente = :id", {"id": target_agente})
                    st.success("Rimosso."); st.rerun()
    st.dataframe(df_a.drop(columns=['Password']), use_container_width=True)

elif menu == "🔧 Manutenzione":
    st.markdown("## 🔧 Strumenti Amministratore")
    df_o = load_data("Ordini")
    if not df_o.empty:
        with st.container(border=True):
            target = st.selectbox("Seleziona Ordine da annullare:", df_o['ID_Ordine'].tolist())
            conferma = st.checkbox(f"Sono sicuro di voler eliminare l'ordine {target}")
            if st.button("🗑️ Elimina Definitivamente", type="primary", disabled=not conferma):
                execute_query("DELETE FROM Ordini WHERE ID_Ordine = :id", {"id": target})
                execute_query("DELETE FROM Log_Consegne WHERE ID_Ordine = :id", {"id": target})
                execute_query("DELETE FROM Log_Pagamenti WHERE ID_Ordine = :id", {"id": target})
                st.success("Eliminato!"); st.rerun()
