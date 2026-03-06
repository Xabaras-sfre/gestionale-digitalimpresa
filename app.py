import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date

# --- 1. CONFIGURAZIONE PAGINA E DESIGN ---
st.set_page_config(page_title="Network 2026", layout="wide", page_icon="👔")

def inject_custom_css():
    st.markdown("""
        <style>
        /* Importa il font moderno 'Inter' */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        
        /* Stile delle Card delle Metriche (KPI) */
        [data-testid="stMetric"] {
            background-color: rgba(175, 175, 175, 0.1);
            padding: 1.2rem;
            border-radius: 12px;
            border-left: 5px solid #0068c9;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            transition: transform 0.2s ease;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
        }
        
        /* Arrotondamento dei bottoni */
        div.stButton > button {
            border-radius: 8px;
            font-weight: 600;
            padding: 0.5rem 1rem;
            transition: all 0.3s ease;
        }
        
        /* Stile Form e Input */
        .stTextInput>div>div>input, .stSelectbox>div>div>div {
            border-radius: 8px;
        }
        
        /* Intestazioni e Testi */
        h1, h2, h3 {
            font-weight: 700 !important;
            letter-spacing: -0.5px;
        }
        
        /* Sidebar più elegante */
        [data-testid="stSidebar"] {
            background-color: rgba(175, 175, 175, 0.03);
            border-right: 1px solid rgba(175, 175, 175, 0.2);
        }
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- 2. CONNESSIONE MYSQL (SITEGROUND) ---
@st.cache_resource
def init_connection():
    db = st.secrets["mysql"]
    password_sicura = urllib.parse.quote_plus(db['password'])
    url = f"mysql+pymysql://{db['user']}:{password_sicura}@{db['host']}:{db['port']}/{db['database']}?charset=utf8mb4"
    
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=30,
        connect_args={"connect_timeout": 15}
    )

engine = init_connection()

def init_db():
    try:
        with engine.begin() as conn:
            conn.execute(text('''CREATE TABLE IF NOT EXISTS Agenti (
                ID_Agente VARCHAR(50) PRIMARY KEY, Nome VARCHAR(100), Ruolo VARCHAR(50), 
                ID_Capoarea VARCHAR(50), Mail_Notifica VARCHAR(100), Password VARCHAR(100))'''))
                            
            conn.execute(text('''CREATE TABLE IF NOT EXISTS Negozi (
                Nome VARCHAR(100) PRIMARY KEY, Partita_IVA VARCHAR(50), Citta VARCHAR(100), 
                Provincia VARCHAR(10), Regione VARCHAR(50))'''))
                            
            conn.execute(text('''CREATE TABLE IF NOT EXISTS Brand (
                ID_Brand VARCHAR(50) PRIMARY KEY, Nome_Brand VARCHAR(100), Provvigione_Totale_perc VARCHAR(20), 
                Quota_Capoarea_perc VARCHAR(20), Quota_Agente_perc VARCHAR(20))'''))
                            
            conn.execute(text('''CREATE TABLE IF NOT EXISTS Ordini (
                ID_Ordine VARCHAR(50) PRIMARY KEY, Stagione VARCHAR(50), ID_Agente VARCHAR(50), 
                ID_Negozio VARCHAR(100), Brand VARCHAR(100), `Ordinato_€` DOUBLE, 
                `Consegnato_€` DOUBLE, Stato_Incasso VARCHAR(50), `Incassato_€` DOUBLE, Data_Ordine DATE)'''))
                            
            conn.execute(text('''CREATE TABLE IF NOT EXISTS Log_Consegne (
                ID_Ordine VARCHAR(50), Data_Consegna DATE, Valore_Consegnato DOUBLE)'''))
                            
            conn.execute(text('''CREATE TABLE IF NOT EXISTS Log_Pagamenti (
                ID_Ordine VARCHAR(50), Data DATE, Importo_Pagato DOUBLE, Metodo VARCHAR(50))'''))

            res = conn.execute(text("SELECT COUNT(*) FROM Agenti")).scalar()
            if res == 0:
                conn.execute(text("INSERT INTO Agenti VALUES (:id, :n, :r, :c, :m, :p)"), 
                             {"id": 'ADMIN-01', "n": 'Admin', "r": 'Superadmin', "c": '', "m": 'tua@email.it', "p": 'admin123'})
    except Exception as e:
        st.error("Errore di connessione. Verifica che l'IP su SiteGround (Accesso Remoto) includa il simbolo %.")
        st.stop()

init_db()

# --- 3. MOTORE DATI (SQL) ---
def load_data(table_name):
    df = pd.read_sql_table(table_name, con=engine)
    if table_name == 'Ordini' and not df.empty and 'Data_Ordine' in df.columns:
        df['Data_Ordine'] = pd.to_datetime(df['Data_Ordine'], errors='coerce')
    if 'ID_Agente' in df.columns: df['ID_Agente'] = df['ID_Agente'].astype(str)
    if 'ID_Ordine' in df.columns: df['ID_Ordine'] = df['ID_Ordine'].astype(str)
    return df

def execute_query(query, params=None):
    with engine.begin() as conn:
        conn.execute(text(query), params or {})

# --- 4. EMAIL ---
def send_email(ordine_id, agente, negozio, brand, valore, email_dest):
    if "email" not in st.secrets: return False
    try:
        e = st.secrets["email"]
        msg = MIMEMultipart()
        msg['From'], msg['To'], msg['Subject'] = e["mittente"], f"{email_dest}, {e['mittente']}", f"📦 Ordine: {ordine_id} - {negozio}"
        corpo = f"Nuovo ordine registrato a sistema.\n\nCodice: {ordine_id}\nAgente: {agente}\nNegozio: {negozio}\nBrand: {brand}\nValore Lordo: € {valore:,.2f}"
        msg.attach(MIMEText(corpo, 'plain'))
        with smtplib.SMTP(e["smtp_server"], e["smtp_port"]) as s:
            s.starttls()
            s.login(e["mittente"], e["password"])
            s.send_message(msg)
        return True
    except: return False

# --- 5. LOGIN MODERNO ---
if "auth" not in st.session_state: st.session_state.update({"auth": False, "user": None})

if not st.session_state.auth:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<h2 style='text-align: center; color: #0068c9;'>Area Riservata Rete Vendita</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Inserisci le tue credenziali per accedere al gestionale 2026</p>", unsafe_allow_html=True)
        with st.form("login_form", clear_on_submit=True):
            u = st.text_input("Nome Utente", placeholder="Es. Mario Rossi")
            p = st.text_input("Password", type="password", placeholder="••••••••")
            # Pulsante 'primary' per farlo spiccare in blu
            submit = st.form_submit_button("Accedi al Sistema", type="primary", use_container_width=True)
            
            if submit:
                df_a = load_data("Agenti")
                user = df_a[(df_a['Nome'] == u) & (df_a['Password'] == p)]
                if not user.empty:
                    st.session_state.update({"auth": True, "user": user.iloc[0].to_dict()})
                    st.rerun()
                else: 
                    st.error("❌ Credenziali non valide. Riprova.")
    st.stop()

# --- 6. NAVIGAZIONE ---
U = st.session_state.user
ROLE = U['Ruolo']

st.sidebar.markdown(f"### 👤 Ciao, **{U['Nome']}**")
st.sidebar.caption(f"🛡️ Livello Accesso: `{ROLE}`")
st.sidebar.divider()

menu_list = ["📊 Dashboard BI", "📝 Nuovo Ordine"]
if ROLE == "Superadmin":
    menu_list += ["🚚 Consegne", "💰 Pagamenti", "🏪 Negozi", "🏷️ Brand", "👥 Agenti", "🔧 Manutenzione"]

menu = st.sidebar.radio("Menu Navigazione", menu_list)

st.sidebar.divider()
if st.sidebar.button("🚪 Disconnettiti", use_container_width=True):
    st.session_state.auth = False
    st.rerun()

# --- 7. LOGICA DELLE SEZIONI ---
if menu == "📊 Dashboard BI":
    st.markdown("## 📊 Business Intelligence & Performance")
    st.caption("Analizza l'andamento delle vendite e le provvigioni maturate in tempo reale.")
    
    df_o = load_data("Ordini")
    df_n = load_data("Negozi")
    df_b = load_data("Brand")
    df_a = load_data("Agenti")

    if df_o.empty:
        st.info("💡 Nessun ordine presente nel Database. Vai su 'Nuovo Ordine' per iniziare.")
    else:
        df = pd.merge(df_o, df_n, left_on='ID_Negozio', right_on='Nome', how='left')
        df = pd.merge(df, df_a[['ID_Agente', 'Nome', 'Ruolo']], on='ID_Agente', suffixes=('', '_Agente'), how='left')
        
        def p2f(x): return float(str(x).replace('%','').replace(',','.')) / 100 if pd.notnull(x) and x != '' else 0.0
        df_b['rate_totale'] = df_b['Provvigione_Totale_perc'].apply(p2f)
        df_b['rate_agente'] = df_b['Quota_Agente_perc'].apply(p2f)
        
        df = pd.merge(df, df_b[['Nome_Brand', 'rate_totale', 'rate_agente']], left_on='Brand', right_on='Nome_Brand', how='left')
        
        df['Anno'] = df['Data_Ordine'].dt.year
        df['Trimestre'] = df['Data_Ordine'].dt.quarter
        
        df['Provv_Agente_Maturata'] = df.apply(lambda r: r['Consegnato_€'] * r['rate_agente'] if r['Ruolo'] != 'Superadmin' else 0, axis=1)
        df['Provv_Agente_Esigibile'] = df.apply(lambda r: r['Incassato_€'] * r['rate_agente'] if r['Ruolo'] != 'Superadmin' else 0, axis=1)
        
        df['Provv_Admin_Maturata'] = df.apply(lambda r: r['Consegnato_€'] * r['rate_totale'] if r['Ruolo'] == 'Superadmin' else r['Consegnato_€'] * (r['rate_totale'] - r['rate_agente']), axis=1)
        df['Provv_Admin_Esigibile'] = df.apply(lambda r: r['Incassato_€'] * r['rate_totale'] if r['Ruolo'] == 'Superadmin' else r['Incassato_€'] * (r['rate_totale'] - r['rate_agente']), axis=1)
        
        if ROLE == "Superadmin":
            df['Mio_Maturato'] = df['Provv_Admin_Maturata']
            df['Mio_Esigibile'] = df['Provv_Admin_Esigibile']
        else:
            df = df[df['ID_Agente'] == str(U['ID_Agente'])]
            df['Mio_Maturato'] = df['Provv_Agente_Maturata']
            df['Mio_Esigibile'] = df['Provv_Agente_Esigibile']

        with st.expander("🔎 Filtri Avanzati di Ricerca", expanded=True):
            f1, f2, f3, f4, f5 = st.columns(5)
            with f1:
                date_valide = df['Data_Ordine'].dropna()
                min_d = date_valide.min().date() if not date_valide.empty else date(2026,1,1)
                max_d = date_valide.max().date() if not date_valide.empty else date.today()
                date_filter = st.date_input("Calendario Specifico", [min_d, max_d])
            with f2:
                anni = sorted(df['Anno'].dropna().unique().astype(int).tolist())
                anno_filter = st.multiselect("Anno Fiscale", anni)
            with f3:
                trimestre_filter = st.multiselect("Trimestre (Q)", [1, 2, 3, 4], format_func=lambda x: f"Q{x}")
            with f4:
                brand_filter = st.multiselect("Seleziona Brand", df['Brand'].dropna().unique())
            with f5:
                if ROLE == "Superadmin":
                    agente_filter = st.multiselect("Seleziona Agente", df['Nome_Agente'].dropna().unique())
                else:
                    agente_filter = []

        mask = pd.Series(True, index=df.index)
        if len(date_filter) == 2:
            mask &= (df['Data_Ordine'] >= pd.to_datetime(date_filter[0])) & (df['Data_Ordine'] <= pd.to_datetime(date_filter[1]))
        if anno_filter: mask &= df['Anno'].isin(anno_filter)
        if trimestre_filter: mask &= df['Trimestre'].isin(trimestre_filter)
        if brand_filter: mask &= df['Brand'].isin(brand_filter)
        if ROLE == "Superadmin" and agente_filter: mask &= df['Nome_Agente'].isin(agente_filter)
        
        df_filtered = df[mask]

        # Stile delle card KPI
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 Ordini Registrati", len(df_filtered))
        c2.metric("💶 Fatturato Lordo", f"{df_filtered['Ordinato_€'].sum():,.2f} €")
        c3.metric("⏳ Maturato (da incassare)", f"{df_filtered['Mio_Maturato'].sum():,.2f} €")
        c4.metric("💰 Esigibile (incassato)", f"{df_filtered['Mio_Esigibile'].sum():,.2f} €")

        st.markdown("<br>", unsafe_allow_html=True)
        
        tab_geo, tab_neg, tab_brand, tab_rete = st.tabs(["🌍 Geografia", "🏪 Negozi", "🏷️ Performance Brand", "👥 Rete Vendita"])
        
        with tab_geo:
            col_reg, col_prov, col_cit = st.columns(3)
            with col_reg:
                st.markdown("#### Spaccato per Regione")
                if 'Regione' in df_filtered.columns:
                    st.dataframe(df_filtered.groupby('Regione').agg({'ID_Ordine':'count', 'Ordinato_€':'sum', 'Mio_Maturato':'sum'}).sort_values('Ordinato_€', ascending=False), use_container_width=True)
            with col_prov:
                st.markdown("#### Spaccato per Provincia")
                if 'Provincia' in df_filtered.columns:
                    st.dataframe(df_filtered.groupby('Provincia').agg({'ID_Ordine':'count', 'Ordinato_€':'sum', 'Mio_Maturato':'sum'}).sort_values('Ordinato_€', ascending=False), use_container_width=True)
            with col_cit:
                st.markdown("#### Top 15 Città")
                if 'Citta' in df_filtered.columns:
                    st.dataframe(df_filtered.groupby('Citta').agg({'ID_Ordine':'count', 'Ordinato_€':'sum', 'Mio_Maturato':'sum'}).sort_values('Ordinato_€', ascending=False).head(15), use_container_width=True)

        with tab_neg:
            st.markdown("#### Performance Dettagliata per Singolo Negozio")
            if 'ID_Negozio' in df_filtered.columns:
                df_negozi_stats = df_filtered.groupby('ID_Negozio').agg({
                    'ID_Ordine':'count', 
                    'Ordinato_€':'sum', 
                    'Consegnato_€':'sum',
                    'Mio_Maturato':'sum',
                    'Mio_Esigibile':'sum'
                }).sort_values('Ordinato_€', ascending=False)
                st.dataframe(df_negozi_stats, use_container_width=True)
                
        with tab_brand:
            st.markdown("#### Incidenza e Margini dei Marchi")
            st.dataframe(df_filtered.groupby('Brand').agg({'ID_Ordine':'count', 'Ordinato_€':'sum', 'Mio_Maturato':'sum'}).sort_values('Ordinato_€', ascending=False), use_container_width=True)
            
        with tab_rete:
            if ROLE == "Superadmin":
                st.markdown("#### Classifica Agenti e Portafoglio")
                st.dataframe(df_filtered.groupby('Nome_Agente').agg({'Ordinato_€':'sum', 'Consegnato_€':'sum', 'Mio_Maturato':'sum'}).sort_values('Ordinato_€', ascending=False), use_container_width=True)
            else:
                st.info("I dati aggregati dell'intera rete commerciale sono visibili solo alla direzione. I tuoi dati personali sono riflessi nelle altre schede.")

elif menu == "📝 Nuovo Ordine":
    st.markdown("## 📝 Registra Nuovo Ordine")
    st.caption("Compila i dettagli per inserire un nuovo ordine nel sistema centrale.")
    df_n, df_b, df_a = load_data("Negozi"), load_data("Brand"), load_data("Agenti")
    
    with st.form("form_ordine", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            id_o = st.text_input("Codice Identificativo Ordine")
            neg = st.selectbox("Seleziona Negozio", df_n['Nome'].tolist() if not df_n.empty else [])
            brand = st.selectbox("Seleziona Brand", df_b['Nome_Brand'].tolist() if not df_b.empty else [])
        with c2:
            val = st.number_input("Valore Lordo Ordine (€)", min_value=0.0)
            agente_id = st.selectbox("Assegnato a:", df_a['ID_Agente'].tolist()) if ROLE == "Superadmin" else U['ID_Agente']
            data_o = st.date_input("Data Sottoscrizione", date.today())
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("Conferma e Salva Ordine", type="primary"):
            if id_o and neg and brand:
                try:
                    execute_query("INSERT INTO Ordini VALUES (:id, 'AI 2026', :ag, :neg, :b, :v, 0.0, 'In Attesa', 0.0, :d)", 
                                 {"id": id_o, "ag": str(agente_id), "neg": neg, "b": brand, "v": val, "d": str(data_o)})
                    
                    mail_dest = df_a[df_a['ID_Agente'] == str(agente_id)].iloc[0].get('Mail_Notifica', '')
                    send_email(id_o, U['Nome'], neg, brand, val, mail_dest)
                    st.success("✅ Ordine registrato con successo nel database in Cloud!")
                except Exception as e:
                    st.error("⚠️ Attenzione: Un ordine con questo Codice Identificativo esiste già nel sistema.")
            else: st.error("Compila tutti i campi obbligatori prima di salvare.")

elif menu == "🚚 Consegne":
    st.markdown("## 🚚 Gestione Scarico Merci (DDT)")
    st.caption("Seleziona un ordine in attesa e registra il valore della merce fisicamente consegnata al negozio.")
    df_o = load_data("Ordini")
    da_consegnare = df_o[df_o['Consegnato_€'] < df_o['Ordinato_€']]
    
    if not da_consegnare.empty:
        sel = st.selectbox("Ordini in Lavorazione:", (da_consegnare['ID_Ordine'] + " | " + da_consegnare['ID_Negozio']).tolist())
        id_sel = sel.split(" | ")[0]
        r_dati = da_consegnare[da_consegnare['ID_Ordine'] == id_sel].iloc[0]
        residuo = r_dati['Ordinato_€'] - r_dati['Consegnato_€']
        
        st.info(f"Valore residuo ancora da consegnare: **€ {residuo:,.2f}**")
        val_scarico = st.number_input("Valore DDT Attuale (€)", max_value=residuo, min_value=0.01)
        if st.button("Registra Consegna Merce", type="primary"):
            nuovo = r_dati['Consegnato_€'] + val_scarico
            stato = "Consegnato" if nuovo >= r_dati['Ordinato_€'] else "Parziale"
            
            execute_query("INSERT INTO Log_Consegne VALUES (:id, :d, :v)", {"id": id_sel, "d": str(date.today()), "v": val_scarico})
            execute_query("UPDATE Ordini SET `Consegnato_€` = :c, Stato_Incasso = :s WHERE ID_Ordine = :id", {"c": nuovo, "s": stato, "id": id_sel})
            st.success("DDT Registrato con successo!"); st.rerun()
    else: st.success("🎉 Eccellente! Tutte le merci ordinate sono state consegnate ai clienti.")

elif menu == "💰 Pagamenti":
    st.markdown("## 💰 Registrazione Incassi e Sblocco Provvigioni")
    st.caption("Registra i pagamenti ricevuti dai clienti per gli ordini consegnati.")
    df_o = load_data("Ordini")
    da_inc = df_o[df_o['Incassato_€'] < df_o['Consegnato_€']]
    
    if not da_inc.empty:
        sel = st.selectbox("Fatture in Attesa di Pagamento:", (da_inc['ID_Ordine'] + " | " + da_inc['ID_Negozio']).tolist())
        id_sel = sel.split(" | ")[0]
        r_dati = da_inc[da_inc['ID_Ordine'] == id_sel].iloc[0]
        residuo = r_dati['Consegnato_€'] - r_dati['Incassato_€']
        
        st.warning(f"Insoluto per questo ordine: **€ {residuo:,.2f}**")
        val_inc = st.number_input("Somma Incassata (€)", max_value=residuo, min_value=0.01)
        metodo = st.selectbox("Metodo di Pagamento", ["Bonifico", "Assegno", "Contanti", "RiBa"])
        if st.button("Registra Pagamento Definitivo", type="primary"):
            nuovo = r_dati['Incassato_€'] + val_inc
            execute_query("INSERT INTO Log_Pagamenti VALUES (:id, :d, :i, :m)", {"id": id_sel, "d": str(date.today()), "i": val_inc, "m": metodo})
            execute_query("UPDATE Ordini SET `Incassato_€` = :i WHERE ID_Ordine = :id", {"i": nuovo, "id": id_sel})
            st.success("Pagamento registrato! Provvigione resa Esigibile."); st.rerun()
    else: st.success("🎉 Nessun insoluto presente a sistema.")

elif menu == "🏪 Negozi":
    st.markdown("## 🏪 Anagrafica Negozi")
    with st.form("f_neg", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            n = st.text_input("Ragione Sociale Negozio")
            p = st.text_input("Partita IVA")
        with c2:
            c = st.text_input("Città")
            c_prov, c_reg = st.columns(2)
            with c_prov: pr = st.text_input("Provincia (Es. MI)")
            with c_reg: r = st.text_input("Regione")
        
        if st.form_submit_button("Aggiungi o Aggiorna Negozio", type="primary") and n:
            execute_query("REPLACE INTO Negozi VALUES (:n, :p, :c, :pr, :r)", {"n": n, "p": p, "c": c, "pr": pr, "r": r})
            st.success(f"Negozio {n} salvato nell'anagrafica!"); st.rerun()
            
    st.markdown("<br>#### Elenco Negozi Attivi", unsafe_allow_html=True)
    st.dataframe(load_data("Negozi"), use_container_width=True)

elif menu == "🏷️ Brand":
    st.markdown("## 🏷️ Gestione Portafoglio Brand")
    with st.form("f_brand", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            ib = st.text_input("ID Brand (Es. BR-01)")
            nb = st.text_input("Nome Commerciale Brand")
        with c2:
            qt = st.text_input("Provvigione Totale Maturata (%)", placeholder="Es. 15%")
            qa = st.text_input("Quota Trattenuta Agente (%)", placeholder="Es. 10%")
            
        if st.form_submit_button("Salva Configurazione Brand", type="primary") and ib:
            execute_query("REPLACE INTO Brand VALUES (:i, :n, :qt, '0%', :qa)", {"i": ib, "n": nb, "qt": qt, "qa": qa})
            st.success(f"Parametri del brand {nb} salvati con successo!"); st.rerun()
            
    st.markdown("<br>#### Elenco Brand e Provvigioni", unsafe_allow_html=True)
    st.dataframe(load_data("Brand"), use_container_width=True)

elif menu == "👥 Agenti":
    st.markdown("## 👥 Gestione Rete Commerciale")
    df_a = load_data("Agenti")
    
    tab1, tab2 = st.tabs(["➕ Crea / Modifica", "❌ Licenzia Agente"])
    
    with tab1:
        st.write("Crea un nuovo profilo o sovrascrivi i dati di un agente esistente digitandone l'ID esatto.")
        with st.form("f_agente", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                aid = st.text_input("ID Agente (Es. AG-01)")
                anome = st.text_input("Nome e Cognome")
                arole = st.selectbox("Ruolo a Sistema", ["Agente", "Superadmin"])
            with c2:
                amail = st.text_input("Email (Per notifiche nuovi ordini)")
                apass = st.text_input("Password di Accesso", type="password")
                
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("Salva Account Agente", type="primary") and aid:
                execute_query("REPLACE INTO Agenti VALUES (:i, :n, :r, '', :m, :p)", {"i": aid, "n": anome, "r": arole, "m": amail, "p": apass})
                st.success(f"Dati di {aid} sincronizzati!"); st.rerun()
                
    with tab2:
        if not df_a.empty:
            agenti_eliminabili = df_a[df_a['ID_Agente'] != U['ID_Agente']]['ID_Agente'].tolist()
            if agenti_eliminabili:
                target_agente = st.selectbox("Seleziona Agente da rimuovere dal sistema:", agenti_eliminabili)
                st.warning("⚠️ L'eliminazione revocherà l'accesso immediato all'agente. I suoi ordini passati rimarranno negli archivi a fini statistici.")
                if st.button("Revoca Accesso ed Elimina", type="primary"):
                    execute_query("DELETE FROM Agenti WHERE ID_Agente = :id", {"id": target_agente})
                    st.success("Profilo Agente rimosso."); st.rerun()
            else:
                st.info("Sei l'unico utente amministratore registrato nel sistema. L'auto-eliminazione è disabilitata.")

    st.markdown("<br>#### Anagrafica Agenti Attivi", unsafe_allow_html=True)
    st.dataframe(df_a.drop(columns=['Password']), use_container_width=True) # Nascondiamo le password dalla tabella!

elif menu == "🔧 Manutenzione":
    st.markdown("## 🔧 Strumenti Amministratore")
    st.error("⚠️ Attenzione: L'eliminazione degli ordini è un'azione distruttiva. Verranno rimossi anche tutti i DDT e le fatture associate (Cascade Delete).")
    
    df_o = load_data("Ordini")
    if not df_o.empty:
        with st.container(border=True):
            target = st.selectbox("Seleziona Ordine da annullare:", df_o['ID_Ordine'].tolist())
            conferma = st.checkbox(f"Sono sicuro di voler eliminare permanentemente l'ordine {target}")
            
            if st.button("🗑️ Elimina Definitivamente", type="primary", disabled=not conferma):
                execute_query("DELETE FROM Ordini WHERE ID_Ordine = :id", {"id": target})
                execute_query("DELETE FROM Log_Consegne WHERE ID_Ordine = :id", {"id": target})
                execute_query("DELETE FROM Log_Pagamenti WHERE ID_Ordine = :id", {"id": target})
                st.success(f"L'ordine {target} e tutti i suoi log sono stati vaporizzati dal server."); st.rerun()
    else:
        st.success("Nessun ordine presente nel database da eliminare.")

