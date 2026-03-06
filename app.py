import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Network 2026 - Cloud DB", layout="wide", page_icon="☁️")

# --- 2. CONNESSIONE MYSQL (SITEGROUND) BLINDATA ---
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
        st.error("Errore di inizializzazione DB. Controlla i Secrets e l'Accesso Remoto su SiteGround.")
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
        corpo = f"Nuovo ordine:\nCodice: {ordine_id}\nAgente: {agente}\nNegozio: {negozio}\nBrand: {brand}\nValore: € {valore:,.2f}"
        msg.attach(MIMEText(corpo, 'plain'))
        with smtplib.SMTP(e["smtp_server"], e["smtp_port"]) as s:
            s.starttls()
            s.login(e["mittente"], e["password"])
            s.send_message(msg)
        return True
    except: return False

# --- 5. LOGIN ---
if "auth" not in st.session_state: st.session_state.update({"auth": False, "user": None})

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>☁️ Gestione Rete Vendita 2026</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        with st.form("login_form"):
            u = st.text_input("Utente")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Accedi"):
                df_a = load_data("Agenti")
                user = df_a[(df_a['Nome'] == u) & (df_a['Password'] == p)]
                if not user.empty:
                    st.session_state.update({"auth": True, "user": user.iloc[0].to_dict()})
                    st.rerun()
                else: st.error("❌ Credenziali errate. Usa 'Admin' / 'admin123' al primo avvio.")
    st.stop()

# --- 6. NAVIGAZIONE ---
U = st.session_state.user
ROLE = U['Ruolo']

st.sidebar.title(f"👤 {U['Nome']}")
st.sidebar.caption(f"Ruolo: {ROLE}")

menu_list = ["📊 Dashboard BI", "📝 Nuovo Ordine"]
if ROLE == "Superadmin":
    menu_list += ["🚚 Consegne", "💰 Pagamenti", "🏪 Negozi", "🏷️ Brand", "👥 Agenti", "🔧 Manutenzione"]

menu = st.sidebar.radio("Menu Principale", menu_list)

if st.sidebar.button("Logout"):
    st.session_state.auth = False
    st.rerun()

# --- 7. LOGICA DELLE SEZIONI ---
if menu == "📊 Dashboard BI":
    st.title("📊 Business Intelligence")
    
    df_o = load_data("Ordini")
    df_n = load_data("Negozi")
    df_b = load_data("Brand")
    df_a = load_data("Agenti")

    if df_o.empty:
        st.info("Nessun ordine nel Database.")
    else:
        df = pd.merge(df_o, df_n, left_on='ID_Negozio', right_on='Nome', how='left')
        df = pd.merge(df, df_a[['ID_Agente', 'Nome', 'Ruolo']], on='ID_Agente', suffixes=('', '_Agente'), how='left')
        
        def p2f(x): return float(str(x).replace('%','').replace(',','.')) / 100 if pd.notnull(x) and x != '' else 0.0
        df_b['rate_totale'] = df_b['Provvigione_Totale_perc'].apply(p2f)
        df_b['rate_agente'] = df_b['Quota_Agente_perc'].apply(p2f)
        
        df = pd.merge(df, df_b[['Nome_Brand', 'rate_totale', 'rate_agente']], left_on='Brand', right_on='Nome_Brand', how='left')
        
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

        st.markdown("### 🔍 Filtri Dinamici")
        f1, f2, f3 = st.columns(3)
        with f1:
            date_valide = df['Data_Ordine'].dropna()
            min_d = date_valide.min().date() if not date_valide.empty else date(2026,1,1)
            max_d = date_valide.max().date() if not date_valide.empty else date.today()
            date_filter = st.date_input("Periodo", [min_d, max_d])
        with f2:
            brand_filter = st.multiselect("Brand", df['Brand'].dropna().unique())
        with f3:
            if ROLE == "Superadmin":
                agente_filter = st.multiselect("Agente", df['Nome_Agente'].dropna().unique())
            else:
                agente_filter = []

        mask = pd.Series(True, index=df.index)
        if len(date_filter) == 2:
            mask &= (df['Data_Ordine'] >= pd.to_datetime(date_filter[0])) & (df['Data_Ordine'] <= pd.to_datetime(date_filter[1]))
        if brand_filter: mask &= df['Brand'].isin(brand_filter)
        if ROLE == "Superadmin" and agente_filter: mask &= df['Nome_Agente'].isin(agente_filter)
        
        df_filtered = df[mask]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ordini (Q.tà)", len(df_filtered))
        c2.metric("Fatturato Lordo (€)", f"{df_filtered['Ordinato_€'].sum():,.2f} €")
        c3.metric("Mio Maturato (€)", f"{df_filtered['Mio_Maturato'].sum():,.2f} €")
        c4.metric("Mio Esigibile (€)", f"{df_filtered['Mio_Esigibile'].sum():,.2f} €")

        st.divider()
        tab1, tab2, tab3 = st.tabs(["Geografia", "Performance Brand", "Rete Vendita"])
        with tab1:
            if 'Regione' in df_filtered.columns: st.bar_chart(df_filtered.groupby('Regione')['Ordinato_€'].sum())
        with tab2:
            st.dataframe(df_filtered.groupby('Brand').agg({'ID_Ordine':'count', 'Ordinato_€':'sum', 'Mio_Maturato':'sum'}).sort_values('Ordinato_€', ascending=False), use_container_width=True)
        with tab3:
            if ROLE == "Superadmin":
                st.dataframe(df_filtered.groupby('Nome_Agente').agg({'Ordinato_€':'sum', 'Consegnato_€':'sum', 'Mio_Maturato':'sum'}).sort_values('Ordinato_€', ascending=False), use_container_width=True)
            else:
                st.info("I dati aggregati della rete sono visibili solo alla direzione.")

elif menu == "📝 Nuovo Ordine":
    st.title("📝 Registra Ordine")
    df_n, df_b, df_a = load_data("Negozi"), load_data("Brand"), load_data("Agenti")
    
    with st.form("form_ordine", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            id_o = st.text_input("ID Ordine")
            neg = st.selectbox("Negozio", df_n['Nome'].tolist() if not df_n.empty else [])
            brand = st.selectbox("Brand", df_b['Nome_Brand'].tolist() if not df_b.empty else [])
        with c2:
            val = st.number_input("Valore (€)", min_value=0.0)
            agente_id = st.selectbox("Agente (Chi chiude il contratto?)", df_a['ID_Agente'].tolist()) if ROLE == "Superadmin" else U['ID_Agente']
            data_o = st.date_input("Data", date.today())
        
        if st.form_submit_button("Salva"):
            if id_o and neg and brand:
                try:
                    execute_query("INSERT INTO Ordini VALUES (:id, 'AI 2026', :ag, :neg, :b, :v, 0.0, 'In Attesa', 0.0, :d)", 
                                 {"id": id_o, "ag": str(agente_id), "neg": neg, "b": brand, "v": val, "d": str(data_o)})
                    
                    mail_dest = df_a[df_a['ID_Agente'] == str(agente_id)].iloc[0].get('Mail_Notifica', '')
                    send_email(id_o, U['Nome'], neg, brand, val, mail_dest)
                    st.success("✅ Ordine salvato e archiviato!")
                except Exception as e:
                    st.error("Errore: ID Ordine già esistente nel database.")
            else: st.error("Compila i campi obbligatori.")

elif menu == "🚚 Consegne":
    st.title("🚚 Scarico Merci")
    df_o = load_data("Ordini")
    da_consegnare = df_o[df_o['Consegnato_€'] < df_o['Ordinato_€']]
    
    if not da_consegnare.empty:
        sel = st.selectbox("Ordine:", (da_consegnare['ID_Ordine'] + " | " + da_consegnare['ID_Negozio']).tolist())
        id_sel = sel.split(" | ")[0]
        r_dati = da_consegnare[da_consegnare['ID_Ordine'] == id_sel].iloc[0]
        residuo = r_dati['Ordinato_€'] - r_dati['Consegnato_€']
        
        val_scarico = st.number_input("Valore DDT (€)", max_value=residuo, min_value=0.01)
        if st.button("Registra Scarico"):
            nuovo = r_dati['Consegnato_€'] + val_scarico
            stato = "Consegnato" if nuovo >= r_dati['Ordinato_€'] else "Parziale"
            
            execute_query("INSERT INTO Log_Consegne VALUES (:id, :d, :v)", {"id": id_sel, "d": str(date.today()), "v": val_scarico})
            execute_query("UPDATE Ordini SET `Consegnato_€` = :c, Stato_Incasso = :s WHERE ID_Ordine = :id", {"c": nuovo, "s": stato, "id": id_sel})
            st.success("Scaricato!"); st.rerun()
    else: st.success("Niente da consegnare.")

elif menu == "💰 Pagamenti":
    st.title("💰 Registra Incassi")
    df_o = load_data("Ordini")
    da_inc = df_o[df_o['Incassato_€'] < df_o['Consegnato_€']]
    
    if not da_inc.empty:
        sel = st.selectbox("Ordine:", (da_inc['ID_Ordine'] + " | " + da_inc['ID_Negozio']).tolist())
        id_sel = sel.split(" | ")[0]
        r_dati = da_inc[da_inc['ID_Ordine'] == id_sel].iloc[0]
        residuo = r_dati['Consegnato_€'] - r_dati['Incassato_€']
        
        val_inc = st.number_input("Incasso Reale (€)", max_value=residuo, min_value=0.01)
        metodo = st.selectbox("Metodo", ["Bonifico", "Assegno", "Contanti", "RiBa"])
        if st.button("Registra Pagamento"):
            nuovo = r_dati['Incassato_€'] + val_inc
            execute_query("INSERT INTO Log_Pagamenti VALUES (:id, :d, :i, :m)", {"id": id_sel, "d": str(date.today()), "i": val_inc, "m": metodo})
            execute_query("UPDATE Ordini SET `Incassato_€` = :i WHERE ID_Ordine = :id", {"i": nuovo, "id": id_sel})
            st.success("Pagato e provvigione sbloccata!"); st.rerun()
    else: st.success("Nessun insoluto.")

elif menu == "🏪 Negozi":
    st.title("🏪 Anagrafica Negozi")
    with st.form("f_neg"):
        n, p, c = st.text_input("Ragione Sociale"), st.text_input("P.IVA"), st.text_input("Città")
        pr, r = st.text_input("Provincia (Es. RM)"), st.text_input("Regione")
        if st.form_submit_button("Aggiungi") and n:
            execute_query("REPLACE INTO Negozi VALUES (:n, :p, :c, :pr, :r)", {"n": n, "p": p, "c": c, "pr": pr, "r": r})
            st.success("Negozio Salvato!"); st.rerun()
    st.dataframe(load_data("Negozi"), use_container_width=True)

elif menu == "🏷️ Brand":
    st.title("🏷️ Gestione Brand")
    with st.form("f_brand"):
        ib, nb = st.text_input("ID Brand"), st.text_input("Nome Brand")
        qt, qa = st.text_input("Provvigione Totale % (Es. 15%)"), st.text_input("Quota Agente % (Es. 10%)")
        if st.form_submit_button("Salva") and ib:
            execute_query("REPLACE INTO Brand VALUES (:i, :n, :qt, '0%', :qa)", {"i": ib, "n": nb, "qt": qt, "qa": qa})
            st.success("Brand Salvato!"); st.rerun()
    st.dataframe(load_data("Brand"), use_container_width=True)

elif menu == "👥 Agenti":
    st.title("👥 Gestione Agenti")
    df_a = load_data("Agenti")
    
    tab1, tab2 = st.tabs(["➕ Crea o Modifica", "❌ Elimina"])
    
    with tab1:
        st.write("Inserisci un nuovo ID per creare un agente, oppure l'ID di un agente esistente per aggiornarne i dati.")
        with st.form("f_agente", clear_on_submit=True):
            aid, anome = st.text_input("ID Agente (Es. AG-01)"), st.text_input("Nome Cognome")
            arole, amail = st.selectbox("Ruolo", ["Agente", "Superadmin"]), st.text_input("Email per Notifiche")
            apass = st.text_input("Password")
            if st.form_submit_button("Salva Agente") and aid:
                execute_query("REPLACE INTO Agenti VALUES (:i, :n, :r, '', :m, :p)", {"i": aid, "n": anome, "r": arole, "m": amail, "p": apass})
                st.success(f"Dati di {aid} salvati correttamente!"); st.rerun()
                
    with tab2:
        if not df_a.empty:
            # Rimuoviamo noi stessi dalla lista per evitare l'auto-cancellazione
            agenti_eliminabili = df_a[df_a['ID_Agente'] != U['ID_Agente']]['ID_Agente'].tolist()
            if agenti_eliminabili:
                target_agente = st.selectbox("Seleziona Agente da licenziare/eliminare:", agenti_eliminabili)
                st.warning("⚠️ L'eliminazione impedirà all'agente di accedere. I suoi ordini passati rimarranno nel database a fini contabili.")
                if st.button("ELIMINA AGENTE DEFINITIVAMENTE", type="primary"):
                    execute_query("DELETE FROM Agenti WHERE ID_Agente = :id", {"id": target_agente})
                    st.success("Agente rimosso dal sistema."); st.rerun()
            else:
                st.info("Sei l'unico utente registrato nel sistema. Non è possibile auto-eliminarsi.")

    st.divider()
    st.subheader("Elenco Rete Vendita")
    st.dataframe(df_a, use_container_width=True)

elif menu == "🔧 Manutenzione":
    st.title("🔧 Database Core")
    df_o = load_data("Ordini")
    if not df_o.empty:
        target = st.selectbox("Elimina Ordine (Cascade):", df_o['ID_Ordine'].tolist())
        if st.button("ELIMINA DEFINITIVAMENTE", type="primary"):
            execute_query("DELETE FROM Ordini WHERE ID_Ordine = :id", {"id": target})
            execute_query("DELETE FROM Log_Consegne WHERE ID_Ordine = :id", {"id": target})
            execute_query("DELETE FROM Log_Pagamenti WHERE ID_Ordine = :id", {"id": target})
            st.success("Eliminato dal database e dai log!"); st.rerun()
