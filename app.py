import streamlit as st
import pandas as pd
import os
from datetime import datetime
import time

# --- CONFIGURAÇÃO DE PREÇOS DO REPACK ---
PRECOS_REPACK = {
    'Lata': 0.10,
    'PET': 0.15,
    'OneWay': 0.20,
    'LongNeck': 0.20
}

# --- REGRAS OFICIAIS ---
NOVAS_REGRAS = [
    {"atividade": "SELO VERMELHO (T/M)", "valor": 1.25},
    {"atividade": "SELO VERMELHO (B/V)", "valor": 1.50},
    {"atividade": "AMARRAÇÃO", "valor": 3.00},
    {"atividade": "REFUGO", "valor": 0.90},
    {"atividade": "BLITZ (EMPURRADA/CARREG/RETORNO)", "valor": 1.50},
    {"atividade": "REPACK", "valor": 0.00},
    {"atividade": "DEVOLUÇÃO", "valor": 1.25},
    {"atividade": "TRANSBORDO", "valor": 1.50},
    {"atividade": "TRIAGEM AVARIAS ARMAZÉM D", "valor": 1.25},
    {"atividade": "PRÉ PICKING MKT PLACE (DESTILADOS)", "valor": 2.00},
    {"atividade": "PRÉ PICKING MKT PLACE (REDBULL)", "valor": 1.50},
    {"atividade": "CÂMARA FRIA", "valor": 3.00},
    {"atividade": "MÁQUINA LIMPEZA", "valor": 5.00},
    {"atividade": "5S MARIA MOLE", "valor": 14.50},
    {"atividade": "5S PICKING/ABASTECIMENTO", "valor": 14.50},
    {"atividade": "DESCARREGAMENTO DE VAN", "valor": 2.00}
]

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="ProTrack Logística", layout="wide", page_icon="🚛")

st.markdown("""
    <style>
    .stButton>button {
        border-radius: 20px;
        background-color: #0054a6;
        color: white;
        border: none;
        padding: 10px 24px;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #003d7a;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #0054a6;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    h1, h2, h3 { color: #0054a6; }
    </style>
    """, unsafe_allow_html=True)

# --- ARQUIVOS ---
FILES_PATH = "data"
IMGS_PATH = "images"
os.makedirs(FILES_PATH, exist_ok=True)
os.makedirs(IMGS_PATH, exist_ok=True)

def format_currency(value):
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

# --- INIT DATA ---
def init_data():
    try:
        df_regras = pd.DataFrame(NOVAS_REGRAS)
        df_regras.to_csv(f"{FILES_PATH}/rules.csv", index=False, sep=';', encoding='latin1')
    except PermissionError:
        st.error("ERRO: Feche o Excel!")

    if not os.path.exists(f"{FILES_PATH}/users.csv"):
        pd.DataFrame(columns=['nome', 'id_login', 'tipo', 'rv_acumulada']).to_csv(f"{FILES_PATH}/users.csv", sep=';', index=False)

init_data()

# --- LEITURA DE DADOS ---
def get_data(filename):
    path = f"{FILES_PATH}/{filename}.csv"
    if not os.path.exists(path):
        if filename == 'tasks':
             cols = ['id_task', 'colaborador_id', 'conferente_id', 'atividade', 'area', 'descricao', 'prioridade', 'status', 'valor', 'data_criacao', 'inicio_execucao', 'fim_execucao', 'tempo_total_min', 'obs_rejeicao', 'qtd_lata', 'qtd_pet', 'qtd_oneway', 'qtd_longneck', 'evidencia_img']
             return pd.DataFrame(columns=cols)
        return pd.DataFrame()

    try:
        df = pd.read_csv(path, sep=';', encoding='latin1')
        if len(df.columns) == 1:
             df = pd.read_csv(path, sep=None, engine='python', encoding='latin1')

        df.columns = df.columns.str.strip().str.lower()

        if filename == 'rules':
            if 'valor' in df.columns:
                df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)

        elif filename == 'users':
            if 'nome' not in df.columns:
                df = pd.read_csv(path, sep=';', encoding='latin1', header=None)
                if len(df.columns) >= 3:
                    df.columns = ['nome', 'id_login', 'tipo'] + list(df.columns[3:])
                if not df.empty and str(df.iloc[0,0]).lower() == 'nome': df = df[1:]
            
            if 'id_login' in df.columns: 
                df['id_login'] = df['id_login'].astype(str).str.strip()
            
            # TRATAMENTO CRÍTICO DA RV PARA GARANTIR SOMA
            if 'rv_acumulada' in df.columns:
                df['rv_acumulada'] = df['rv_acumulada'].astype(str).str.replace(',', '.')
                df['rv_acumulada'] = pd.to_numeric(df['rv_acumulada'], errors='coerce').fillna(0.0)
            else:
                df['rv_acumulada'] = 0.0

        elif filename == 'tasks':
            if 'colaborador_id' in df.columns: 
                df['colaborador_id'] = df['colaborador_id'].astype(str).str.strip()

        return df
    except Exception:
        return pd.DataFrame()

def save_data(df, filename):
    try:
        df.to_csv(f"{FILES_PATH}/{filename}.csv", index=False, sep=';', encoding='latin1')
    except PermissionError:
        st.error(f"Feche o arquivo {filename}!")

def add_task_safe(task_dict):
    df = get_data("tasks")
    new_row = pd.DataFrame([task_dict])
    if df.empty: df = new_row
    else: df = pd.concat([df, new_row], ignore_index=True)
    save_data(df, "tasks")

def update_task_safe(task_id, updates):
    df = get_data("tasks")
    if df.empty: return
    df['id_task'] = df['id_task'].astype(str)
    idx = df[df['id_task'] == str(task_id)].index
    if not idx.empty:
        for col, val in updates.items():
            df.at[idx[0], col] = val
        save_data(df, "tasks")

# --- CORREÇÃO DA SOMA DA RV ---
def update_rv_safe(user_id, amount):
    df = get_data("users")
    
    # Garante que os IDs sejam strings limpas para bater
    user_id = str(user_id).strip()
    df['id_login'] = df['id_login'].astype(str).str.strip()
    
    idx = df[df['id_login'] == user_id].index
    
    if not idx.empty:
        # Pega valor atual garantindo que é numero
        atual = df.at[idx[0], 'rv_acumulada']
        novo_saldo = float(atual) + float(amount)
        
        df.at[idx[0], 'rv_acumulada'] = novo_saldo
        save_data(df, "users")
        return True
    else:
        st.error(f"Erro ao pagar: Usuário ID {user_id} não encontrado no cadastro.")
        return False

# --- LOGIN ---
def login_screen():
    st.markdown("<h1 style='text-align: center;'>ProTrack Logística 🚛</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.info("Login (ID ou Matrícula)")
        login_id = st.text_input("ID").strip()
        if st.button("ENTRAR"):
            users = get_data("users")
            if users.empty: 
                st.error("Erro users.csv")
                return
            
            user = users[users['id_login'] == login_id]
            if not user.empty:
                st.session_state['user_id'] = str(user.iloc[0]['id_login'])
                st.session_state['user_name'] = user.iloc[0]['nome']
                role = str(user.iloc[0]['tipo']).lower()
                st.session_state['user_role'] = 'Conferente' if 'conferente' in role else 'Colaborador'
                st.rerun()
            else:
                st.error("Usuário não encontrado.")

# --- CONFERENTE ---
def interface_conferente():
    st.sidebar.header(f"👤 {st.session_state['user_name']}")
    st.sidebar.badge("Conferente")
    menu = st.sidebar.radio("Menu", ["Criar Tarefa", "Aprovar Tarefas", "Ranking", "Sair"])
    users = get_data("users")
    tasks = get_data("tasks")
    rules = get_data("rules")

    if menu == "Sair":
        st.session_state.clear()
        st.rerun()

    elif menu == "Criar Tarefa":
        st.title("📋 Nova Atividade")
        with st.form("task_form"):
            ops = users[~users['tipo'].str.lower().str.contains('conferente', na=False)]['nome'].tolist()
            atvs = rules['atividade'].tolist() if not rules.empty else []
            
            colab = st.selectbox("Colaborador", ops)
            atv = st.selectbox("Atividade", atvs)
            area = st.text_input("Local")
            obs = st.text_area("Obs")
            prio = st.select_slider("Prioridade", ["Baixa", "Média", "Alta"])
            
            if st.form_submit_button("Enviar"):
                try:
                    cid = users[users['nome'] == colab].iloc[0]['id_login']
                    val = 0.0
                    if not rules.empty:
                        val_row = rules.loc[rules['atividade'] == atv, 'valor']
                        if not val_row.empty: val = val_row.values[0]

                    task = {
                        'id_task': int(time.time()), 'colaborador_id': str(cid), 'conferente_id': st.session_state['user_id'],
                        'atividade': atv, 'area': area, 'descricao': obs, 'prioridade': prio, 'status': 'Pendente',
                        'valor': float(val), 'data_criacao': datetime.now().strftime("%d/%m %H:%M"),
                        'inicio_execucao': None, 'fim_execucao': None, 'tempo_total_min': 0, 'obs_rejeicao': '',
                        'qtd_lata': 0, 'qtd_pet': 0, 'qtd_oneway': 0, 'qtd_longneck': 0, 'evidencia_img': ''
                    }
                    add_task_safe(task)
                    st.success(f"Criada! Valor Unitário: {format_currency(val)}")
                except Exception as e: st.error(f"Erro: {e}")

    elif menu == "Aprovar Tarefas":
        st.title("✅ Aprovação")
        if not tasks.empty:
            pends = tasks[tasks['status'] == 'Aguardando Aprovação']
            if pends.empty: st.info("Tudo ok.")
            for i, row in pends.iterrows():
                cname = users[users['id_login'] == str(row['colaborador_id'])]['nome'].values
                name = cname[0] if len(cname)>0 else "Desc"
                with st.container():
                    st.markdown(f"**{name}** - {row['atividade']}")
                    c1, c2 = st.columns(2)
                    c1.write(f"⏱️ Tempo: {row['tempo_total_min']}m")
                    
                    if row['atividade'] == 'REPACK' or row['atividade'] == 'Repack':
                        c1.info(f"🥫 Lata:{row['qtd_lata']} | 🍾 PET:{row['qtd_pet']} | 🧊 OW:{row['qtd_oneway']} | 🍺 LN:{row['qtd_longneck']}")
                    
                    c1.metric("💰 Valor Total a Pagar", format_currency(row['valor']))

                    if pd.notna(row['evidencia_img']) and row['evidencia_img']:
                        if os.path.exists(row['evidencia_img']):
                            try: c2.image(row['evidencia_img'], width=150)
                            except: c2.warning("Img erro")
                    
                    b1, b2 = st.columns(2)
                    if b1.button("✅ Aprovar", key=f"ok{row['id_task']}"):
                        # ATUALIZA O SALDO
                        pago = update_rv_safe(row['colaborador_id'], row['valor'])
                        
                        if pago:
                            update_task_safe(row['id_task'], {'status': 'Executada'})
                            st.success(f"Pago R$ {row['valor']} para {name}!")
                            time.sleep(1)
                            st.rerun()
                    
                    with b2:
                        with st.expander("❌ Rejeitar"):
                            motivo = st.text_input("Motivo:", key=f"rs{row['id_task']}")
                            if st.button("Confirmar", key=f"cr{row['id_task']}"):
                                update_task_safe(row['id_task'], {'status': 'Rejeitada', 'obs_rejeicao': motivo})
                                st.rerun()
                    st.divider()
        else: st.info("Sem tarefas.")

    elif menu == "Ranking":
        st.dataframe(users[['nome', 'rv_acumulada']].sort_values('rv_acumulada', ascending=False), use_container_width=True)

# --- COLABORADOR ---
def interface_colaborador():
    st.sidebar.header(f"👷 {st.session_state['user_name']}")
    st.sidebar.badge("Colaborador")
    menu = st.sidebar.radio("Menu", ["Dashboard", "Tarefas", "Auto-Cadastro", "Regras", "Sair"])
    
    my_id = str(st.session_state['user_id'])

    if menu == "Sair":
        st.session_state.clear()
        st.rerun()

    elif menu == "Dashboard":
        # RECARREGA DADOS PARA GARANTIR SALDO ATUALIZADO
        users = get_data("users")
        tasks = get_data("tasks")
        
        st.title("📊 Dashboard")
        udata = users[users['id_login'] == my_id].iloc[0]
        hrs = 0
        if not tasks.empty:
            done = tasks[(tasks['colaborador_id'] == my_id) & (tasks['status'] == 'Executada')]
            hrs = done['tempo_total_min'].sum() / 60
        
        c1, c2 = st.columns(2)
        c1.metric("RV (R$)", format_currency(udata['rv_acumulada']))
        c2.metric("Horas", f"{hrs:.1f}")

    elif menu == "Tarefas":
        tasks = get_data("tasks")
        st.title("🗂️ Tarefas")
        t1, t2 = st.tabs(["A Fazer", "Feitas"])
        with t1:
            if not tasks.empty:
                todo = tasks[(tasks['colaborador_id'] == my_id) & (tasks['status'].isin(['Pendente', 'Rejeitada', 'Em Execução']))]
                if todo.empty: st.info("Nada pendente.")
                for i, row in todo.iterrows():
                    with st.expander(f"{row['atividade']} ({row['status']})", expanded=True):
                        st.write(f"Local: {row['area']} | Obs: {row['descricao']}")
                        if row['status'] == 'Rejeitada': st.error(f"Motivo: {row['obs_rejeicao']}")
                        
                        if row['status'] != 'Em Execução':
                            if st.button("▶️ INICIAR", key=f"go{row['id_task']}"):
                                update_task_safe(row['id_task'], {'status': 'Em Execução', 'inicio_execucao': datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                                st.rerun()
                        else:
                            if st.button("⏹️ FINALIZAR", key=f"end{row['id_task']}"):
                                ini = pd.to_datetime(row['inicio_execucao'])
                                dur = (datetime.now() - ini).total_seconds() / 60
                                st.session_state['fid'] = row['id_task']
                                st.session_state['fdur'] = round(dur, 2)
                                st.rerun()
                        
                        if st.session_state.get('fid') == row['id_task']:
                            st.markdown("---")
                            st.write(f"Tempo: {st.session_state['fdur']} min")
                            
                            with st.form(f"f{row['id_task']}"):
                                lata, pet, ow, ln = 0, 0, 0, 0
                                qtd_prod = 1.0
                                valor_base = row['valor']
                                valor_final = 0.0
                                
                                if row['atividade'] == 'REPACK' or row['atividade'] == 'Repack':
                                    st.subheader("Produção Repack")
                                    c1, c2, c3, c4 = st.columns(4)
                                    lata = c1.number_input("Lata", 0)
                                    pet = c2.number_input("PET", 0)
                                    ow = c3.number_input("OneWay", 0)
                                    ln = c4.number_input("LongNeck", 0)
                                    valor_final = (lata * PRECOS_REPACK['Lata']) + (pet * PRECOS_REPACK['PET']) + (ow * PRECOS_REPACK['OneWay']) + (ln * PRECOS_REPACK['LongNeck'])
                                else:
                                    st.info(f"Valor Unitário/Base: {format_currency(valor_base)}")
                                    qtd_prod = st.number_input("Quantidade Realizada:", min_value=1.0, value=1.0, step=1.0)
                                    valor_final = valor_base * qtd_prod

                                st.caption(f"💰 Valor Total: {format_currency(valor_final)}")
                                foto = st.file_uploader("Foto")
                                
                                if st.form_submit_button("Entregar"):
                                    p = f"{IMGS_PATH}/{row['id_task']}_{foto.name}" if foto else ""
                                    if foto:
                                        with open(p, "wb") as f: f.write(foto.getbuffer())
                                    
                                    update_task_safe(row['id_task'], {
                                        'status': 'Aguardando Aprovação',
                                        'tempo_total_min': st.session_state['fdur'],
                                        'evidencia_img': p,
                                        'qtd_lata': lata, 'qtd_pet': pet, 'qtd_oneway': ow, 'qtd_longneck': ln,
                                        'valor': valor_final
                                    })
                                    del st.session_state['fid']
                                    st.success("Entregue!")
                                    st.rerun()
        with t2:
            tasks = get_data("tasks")
            if not tasks.empty:
                done = tasks[(tasks['colaborador_id'] == my_id) & (tasks['status'] == 'Executada')]
                if 'valor' in done.columns:
                    st.dataframe(done[['atividade', 'valor', 'data_criacao']])

    elif menu == "Auto-Cadastro":
        users = get_data("users")
        rules = get_data("rules")
        st.title("🙋 Auto-Cadastro")
        confs_df = users[users['tipo'].str.lower().str.contains('conferente', na=False)]
        if confs_df.empty:
            st.warning("⚠️ Conferente não identificado. Usando lista geral.")
            confs = users['nome'].tolist()
        else:
            confs = confs_df['nome'].tolist()
            
        with st.form("auto"):
            quem = st.selectbox("Aprovador", confs)
            atvs = rules['atividade'].tolist() if not rules.empty else []
            oq = st.selectbox("Atividade", atvs)
            loc = st.text_input("Local")
            # CAMPO DE OBSERVAÇÃO NOVO
            obs_user = st.text_area("Observação / Detalhes")
            
            if st.form_submit_button("Cadastrar"):
                try:
                    cid = users[users['nome'] == quem].iloc[0]['id_login']
                    val = 0.0
                    if not rules.empty:
                        val_row = rules.loc[rules['atividade'] == oq, 'valor']
                        if not val_row.empty: val = val_row.values[0]
                    
                    desc_final = obs_user if obs_user else "Auto-Cadastro"

                    task = {
                        'id_task': int(time.time()), 'colaborador_id': my_id, 'conferente_id': str(cid),
                        'atividade': oq, 'area': loc, 'descricao': desc_final, 'prioridade': 'Média',
                        'status': 'Pendente', 'valor': float(val), 'data_criacao': datetime.now().strftime("%d/%m %H:%M"),
                        'inicio_execucao': None, 'fim_execucao': None, 'tempo_total_min': 0, 'obs_rejeicao': '',
                        'qtd_lata': 0, 'qtd_pet': 0, 'qtd_oneway': 0, 'qtd_longneck': 0, 'evidencia_img': ''
                    }
                    add_task_safe(task)
                    st.success("Sucesso!")
                except Exception as e: st.error(f"Erro: {e}")

    elif menu == "Regras":
        rules = get_data("rules")
        st.title("💰 Valores")
        if not rules.empty and 'valor' in rules.columns:
            rules_view = rules.copy()
            rules_view['valor'] = rules_view['valor'].apply(format_currency)
            st.table(rules_view[['atividade', 'valor']])
        else:
            st.warning("Sem regras.")

# --- RUN ---
if 'user_id' not in st.session_state:
    login_screen()
else:
    if st.session_state['user_role'] == 'Conferente':
        interface_conferente()
    else:
        interface_colaborador()