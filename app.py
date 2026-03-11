import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import time
import uuid
from github import Github

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="ProTrack Logística", layout="wide", page_icon="🚛")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stButton>button {
        border-radius: 8px;
        background-color: #0054a6;
        color: white;
        border: none;
        height: 40px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #003d7a;
    }
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    button[title="View fullscreen"] {
        display: none;
    }
    h1, h2, h3 { color: #0054a6; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURAÇÕES GLOBAIS ---
ATIVIDADES_POR_CARRO = ["AMARRAÇÃO", "DESCARREGAMENTO DE VAN"]
ATIVIDADES_POR_DIA = ["MÁQUINA LIMPEZA", "5S MARIA MOLE", "5S PICKING/ABASTECIMENTO"]
SUPERVISORES_PERMITIDOS = ['99849441', '99813623', '99797465']
LIMITE_RV_OPERADOR = 380.00  

NOVAS_REGRAS = [
    {"atividade": "SELO VERMELHO (T/M)", "valor": 1.25},
    {"atividade": "SELO VERMELHO (B/V)", "valor": 1.50},
    {"atividade": "AMARRAÇÃO", "valor": 3.00},
    {"atividade": "REFUGO", "valor": 0.90},
    {"atividade": "BLITZ (EMPURRADA)", "valor": 1.50},
    {"atividade": "BLITZ (CARREG)", "valor": 1.50},
    {"atividade": "BLITZ (RETORNO)", "valor": 1.50},
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
    {"atividade": "DESCARREGAMENTO DE VAN", "valor": 2.00},
    {"atividade": "EFC", "valor": 3.85},
    {"atividade": "TMA", "valor": 7.70},
    {"atividade": "FEFO", "valor": 3.85}
]

FILES_PATH = "data"
IMGS_PATH = "images"
os.makedirs(FILES_PATH, exist_ok=True)
os.makedirs(IMGS_PATH, exist_ok=True)

def format_currency(value):
    try: return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "R$ 0,00"

def get_time_br():
    return datetime.utcnow() - timedelta(hours=3)

# --- INTEGRAÇÃO DIRETA COM O GITHUB ---

def get_github_repo():
    if "GITHUB_TOKEN" in st.secrets and "GITHUB_REPO" in st.secrets:
        g = Github(st.secrets["GITHUB_TOKEN"])
        return g.get_repo(st.secrets["GITHUB_REPO"])
    return None

def sync_from_github(filename):
    try:
        repo = get_github_repo()
        if repo:
            contents = repo.get_contents(f"{FILES_PATH}/{filename}.csv")
            with open(f"{FILES_PATH}/{filename}.csv", "wb") as f:
                f.write(contents.decoded_content)
    except Exception:
        pass 

def save_to_github(filename):
    try:
        repo = get_github_repo()
        if repo:
            file_path = f"{FILES_PATH}/{filename}.csv"
            with open(file_path, "rb") as f: content = f.read()
            try:
                contents = repo.get_contents(file_path)
                repo.update_file(contents.path, f"Atualizou {filename}", content, contents.sha)
            except Exception:
                repo.create_file(file_path, f"Criou {filename}", content)
    except Exception as e:
        st.error(f"Erro na sincronização CSV com o GitHub: {e}")

def upload_media_to_github(file_path):
    """Nova função exclusiva para salvar as imagens/vídeos no GitHub"""
    try:
        repo = get_github_repo()
        if repo:
            with open(file_path, "rb") as f: content = f.read()
            try:
                contents = repo.get_contents(file_path)
                repo.update_file(contents.path, f"Atualizou Imagem {file_path}", content, contents.sha)
            except Exception:
                repo.create_file(file_path, f"Upload Imagem {file_path}", content)
    except Exception as e:
        st.error(f"Erro ao salvar imagem no GitHub: {e}")

def get_media_url(local_path):
    """Garante que a imagem aparece mesmo se o servidor apagar a pasta local, puxando do GitHub"""
    if not local_path or pd.isna(local_path): return ""
    if os.path.exists(local_path): return local_path
    
    repo_name = st.secrets.get("GITHUB_REPO", "")
    if repo_name:
        return f"https://raw.githubusercontent.com/{repo_name}/main/{local_path}"
    return ""

def generate_media_name(usuario, atividade, sku, sufixo=""):
    """Gera o nome do ficheiro no formato: USUARIO_ATIVIDADE_SKU_DATA_HORA"""
    nome_safe = str(usuario).strip().replace(" ", "_").upper()
    atv_safe = str(atividade).strip().replace(" ", "_").replace("/", "-").upper()
    
    if not sku or sku in ["-", "N/A"]:
        sku_safe = "SEM_SKU"
    else:
        # Pega apenas o código do SKU antes do traço
        sku_safe = str(sku).split(" - ")[0].strip().replace(" ", "_").upper()
        
    data_safe = get_time_br().strftime("%d%m%Y_%H%M%S")
    
    sufixo_str = f"_{sufixo}" if sufixo else ""
    return f"{nome_safe}_{atv_safe}_{sku_safe}_{data_safe}{sufixo_str}"

# --- GERENCIAMENTO DE DADOS ---

def init_data():
    if not os.path.exists(f"{FILES_PATH}/rules.csv"):
        pd.DataFrame(NOVAS_REGRAS).to_csv(f"{FILES_PATH}/rules.csv", index=False, sep=';', encoding='utf-8-sig')
    if not os.path.exists(f"{FILES_PATH}/users.csv"):
        pd.DataFrame(columns=['nome', 'id_login', 'tipo', 'rv_acumulada']).to_csv(f"{FILES_PATH}/users.csv", sep=';', index=False, encoding='utf-8-sig')
    if not os.path.exists(f"{FILES_PATH}/tasks.csv"):
        cols = ['id_task', 'colaborador_id', 'conferente_id', 'atividade', 'area', 'descricao', 
                'sku_produto', 'prioridade', 'status', 'valor', 'data_criacao', 'inicio_execucao', 
                'fim_execucao', 'tempo_total_min', 'obs_rejeicao', 'qtd_lata', 'qtd_pet', 
                'qtd_oneway', 'qtd_longneck', 'qtd_produzida', 'evidencia_img']
        pd.DataFrame(columns=cols).to_csv(f"{FILES_PATH}/tasks.csv", sep=';', index=False, encoding='utf-8-sig')
    if not os.path.exists(f"{FILES_PATH}/sku.csv"):
        pd.DataFrame(columns=['codigo', 'descricao']).to_csv(f"{FILES_PATH}/sku.csv", sep=';', index=False, encoding='utf-8-sig')

def get_data(filename):
    sync_from_github(filename) 
    path = f"{FILES_PATH}/{filename}.csv"
    if not os.path.exists(path):
        init_data()
        if not os.path.exists(path): return pd.DataFrame()
    try:
        try: df = pd.read_csv(path, sep=';', encoding='utf-8-sig', dtype=str)
        except: df = pd.read_csv(path, sep=';', encoding='latin1', dtype=str)
        
        if filename == 'tasks':
            required = ['id_task', 'colaborador_id', 'status', 'valor', 'atividade']
            if df.empty or not all(c in df.columns for c in required):
                 cols = ['id_task', 'colaborador_id', 'conferente_id', 'atividade', 'area', 'descricao', 
                         'sku_produto', 'prioridade', 'status', 'valor', 'data_criacao', 'inicio_execucao', 
                         'fim_execucao', 'tempo_total_min', 'obs_rejeicao', 'qtd_lata', 'qtd_pet', 
                         'qtd_oneway', 'qtd_longneck', 'qtd_produzida', 'evidencia_img']
                 return pd.DataFrame(columns=cols)
            df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
            df['tempo_total_min'] = pd.to_numeric(df['tempo_total_min'], errors='coerce').fillna(0.0)
        elif filename == 'users':
            if 'rv_acumulada' not in df.columns: df['rv_acumulada'] = 0.0
            df['rv_acumulada'] = pd.to_numeric(df['rv_acumulada'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
        elif filename == 'rules':
            df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
        return df
    except: return pd.DataFrame()

def save_data(df, filename):
    try: 
        df.to_csv(f"{FILES_PATH}/{filename}.csv", index=False, sep=';', encoding='utf-8-sig')
        save_to_github(filename)
    except Exception as e: st.error(f"Erro ao guardar {filename}.")

def add_task_safe(task_dict):
    df = get_data("tasks")
    new_row = pd.DataFrame([task_dict])
    df = pd.concat([df, new_row], ignore_index=True)
    save_data(df, "tasks")

def update_task_safe(task_id, updates):
    df = get_data("tasks")
    if df.empty: return
    idx = df[df['id_task'].astype(str) == str(task_id)].index
    if not idx.empty:
        for col, val in updates.items(): df.at[idx[0], col] = val
        save_data(df, "tasks")

def update_rv_safe(user_id, amount):
    df = get_data("users")
    idx = df[df['id_login'].astype(str).str.strip() == str(user_id).strip()].index
    if not idx.empty:
        atual = float(df.at[idx[0], 'rv_acumulada'])
        df.at[idx[0], 'rv_acumulada'] = atual + float(amount)
        save_data(df, "users")
        return True
    return False

def buscar_sku_interface_v2():
    df_sku = get_data("sku")
    if df_sku.empty: return "-"
    df_sku['display'] = df_sku.iloc[:, 1].astype(str) + " | Cód: " + df_sku.iloc[:, 0].astype(str)
    opcoes = df_sku['display'].tolist()
    
    escolha = st.selectbox("Selecione o Produto (Escreva para buscar)", [""] + opcoes)
    codigo_travado = ""
    nome_produto = "-"
    
    if escolha:
        try:
            parts = escolha.split(" | Cód: ")
            nome_produto = parts[0]
            codigo_travado = parts[1]
        except: codigo_travado = "Erro"
            
    st.text_input("Código do SKU (Travado)", value=codigo_travado, disabled=True)
    if codigo_travado and codigo_travado != "Erro": return f"{codigo_travado} - {nome_produto}"
    return "-"

# --- GESTÃO DE SESSÃO ---
def do_logout():
    st.query_params.clear()
    st.session_state.clear()
    st.rerun()

def restore_session():
    qp = st.query_params
    if 'uid' in qp:
        uid = qp['uid']
        users = get_data("users")
        user = users[users['id_login'].astype(str) == uid]
        if not user.empty:
            st.session_state['user_id'] = str(user.iloc[0]['id_login'])
            st.session_state['user_name'] = user.iloc[0]['nome']
            tipo = str(user.iloc[0]['tipo']).upper()
            if st.session_state['user_id'] in SUPERVISORES_PERMITIDOS: st.session_state['role'] = 'Supervisor'
            elif 'OPERADOR' in tipo: st.session_state['role'] = 'Operador'
            elif 'CONFERENTE' in tipo: st.session_state['role'] = 'Conferente'
            else: st.session_state['role'] = 'Colaborador'
            return True
    return False

# --- TELA DE REGRAS ---
def interface_regras():
    st.title("📜 Regras & Valores")
    rules = get_data("rules")
    if not rules.empty:
        df_show = rules.copy()[['atividade', 'valor']]
        df_show.columns = ['Atividade', 'Valor Unitário']
        df_show['Valor Unitário'] = df_show['Valor Unitário'].apply(format_currency)
        st.dataframe(df_show.sort_values('Atividade'), use_container_width=True, hide_index=True)

# --- TELAS DO SISTEMA ---
def login_screen():
    st.markdown("<h1 style='text-align: center; color: #0054a6;'>ProTrack Logística 🚛</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.info("Insira o seu ID ou Matrícula")
        lid = st.text_input("ID").strip()
        if st.button("ENTRAR"):
            users = get_data("users")
            user = users[users['id_login'].astype(str) == lid]
            if not user.empty:
                st.query_params["uid"] = str(user.iloc[0]['id_login'])
                time.sleep(0.1)
                st.rerun()
            else: st.error("Utilizador não cadastrado.")

def interface_supervisor():
    st.sidebar.header(f"👮 {st.session_state.get('user_name', 'Sup')}")
    menu = st.sidebar.radio("Menu", ["Validar KPIs", "Ajustes Financeiros", "Ranking", "Regras & Valores", "Sair"])
    if menu == "Sair": do_logout()
    elif menu == "Regras & Valores": interface_regras()
    
    users, rules, tasks = get_data("users"), get_data("rules"), get_data("tasks")

    if menu == "Validar KPIs":
        st.title("🛡️ Validar Metas (KPIs)")
        pendentes = tasks[(tasks['status'] == 'Aguardando Validação') & (tasks['atividade'].isin(['EFC', 'TMA', 'FEFO']))]
        if pendentes.empty: st.info("Tudo validado!")
        else:
            for i, row in pendentes.iterrows():
                cname = users[users['id_login'].astype(str) == str(row['colaborador_id'])]['nome'].values
                nome_colab = cname[0] if len(cname) > 0 else row['colaborador_id']
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    val = float(row['valor'])
                    col1.markdown(f"**{nome_colab}** | {row['atividade']} | Declarado: **{'OK' if val > 0 else 'NOK'}** ({format_currency(val)})")
                    if col2.button("✅ Confirmar", key=f"ok_{row['id_task']}"):
                        if update_rv_safe(row['colaborador_id'], val):
                            update_task_safe(row['id_task'], {'status': 'Executada'})
                            st.rerun()
                    if col3.button("✏️ Alterar", key=f"nok_{row['id_task']}"):
                        novo_status = 'Não Atingido' if val > 0 else 'Executada'
                        novo_valor = float(rules.loc[rules['atividade'] == row['atividade'], 'valor'].values[0]) if val == 0 else 0.0
                        obs = "Supervisor alterou status"
                        if update_rv_safe(row['colaborador_id'], novo_valor):
                            update_task_safe(row['id_task'], {'status': novo_status, 'valor': novo_valor, 'obs_rejeicao': obs})
                            st.rerun()
                    st.divider()

    elif menu == "Ajustes Financeiros":
        st.title("💰 Ajuste de Saldo")
        with st.form("ajuste_form"):
            colab = st.selectbox("Colaborador", users['nome'].tolist())
            tipo = st.radio("Tipo de Ajuste", ["Crédito (+)", "Débito (-)"], horizontal=True)
            valor = st.number_input("Valor (R$)", min_value=0.0, step=0.5)
            motivo = st.text_input("Motivo")
            if st.form_submit_button("PROCESSAR"):
                if valor > 0 and motivo:
                    cid = users[users['nome'] == colab].iloc[0]['id_login']
                    v_final = valor if tipo == "Crédito (+)" else -valor
                    if update_rv_safe(cid, v_final):
                        add_task_safe({
                            'id_task': str(uuid.uuid4()), 'colaborador_id': str(cid), 'conferente_id': st.session_state['user_id'],
                            'atividade': "AJUSTE MANUAL", 'area': "ADM", 'descricao': f"{tipo}: {motivo}",
                            'sku_produto': "-", 'prioridade': 'Alta', 'status': 'Executada', 'valor': float(v_final),
                            'data_criacao': get_time_br().strftime("%d/%m %H:%M"), 'inicio_execucao': "-", 'fim_execucao': "-", 
                            'tempo_total_min': 0, 'obs_rejeicao': "", 'qtd_lata': 0, 'qtd_pet': 0, 'qtd_oneway': 0, 'qtd_longneck': 0, 
                            'qtd_produzida': 0, 'evidencia_img': ""
                        })
                        st.success("Ajuste efetuado.")
                        time.sleep(1)
                        st.rerun()

    elif menu == "Ranking":
        st.title("🏆 Ranking Geral")
        df_rank = users[['nome', 'rv_acumulada']].sort_values('rv_acumulada', ascending=False).reset_index(drop=True)
        df_rank['rv_acumulada'] = df_rank['rv_acumulada'].apply(format_currency)
        st.table(df_rank)

def interface_operador():
    st.sidebar.header(f"👷 {st.session_state['user_name']}")
    ops_menu = ["Tarefas", "Auto-Cadastro", "Dashboard", "Regras & Valores", "Sair"]
    if st.session_state.get('role') == 'Operador': ops_menu.insert(0, "🚀 KPIs Diários")
    menu = st.sidebar.radio("Menu", ops_menu)
    uid = st.session_state['user_id']
    
    if menu == "Sair": do_logout()
    elif menu == "Regras & Valores": interface_regras()
    elif menu == "🚀 KPIs Diários":
        st.title("🚀 Metas do Dia")
        rules, tasks = get_data("rules"), get_data("tasks")
        def get_v(n): return float(rules[rules['atividade']==n]['valor'].values[0]) if not rules[rules['atividade']==n].empty else 0.0
        v_efc, v_tma, v_fefo = get_v('EFC'), get_v('TMA'), get_v('FEFO')
        ja_fez = not tasks[(tasks['colaborador_id'].astype(str)==uid) & (tasks['data_criacao'].str.contains(get_time_br().strftime("%d/%m"))) & (tasks['atividade'].isin(['EFC','TMA']))].empty if not tasks.empty else False
        
        if ja_fez: st.info("✅ KPIs enviados e aguardam validação.")
        else:
            with st.form("kpi"):
                c_efc, c_tma, c_fefo = st.checkbox(f"EFC ({format_currency(v_efc)})"), st.checkbox(f"TMA ({format_currency(v_tma)})"), st.checkbox(f"FEFO ({format_currency(v_fefo)})")
                if st.form_submit_button("ENVIAR"):
                    for n, c, v in [("EFC", c_efc, v_efc), ("TMA", c_tma, v_tma), ("FEFO", c_fefo, v_fefo)]:
                        add_task_safe({
                            'id_task': str(uuid.uuid4()), 'colaborador_id': uid, 'conferente_id': 'SISTEMA',
                            'atividade': n, 'area': 'OPERAÇÃO', 'descricao': 'Auto-Avaliação', 'sku_produto': '-', 
                            'prioridade': 'Alta', 'status': 'Aguardando Validação', 'valor': float(v if c else 0.0),
                            'data_criacao': get_time_br().strftime("%d/%m %H:%M"), 'inicio_execucao': "-", 'fim_execucao': "-", 
                            'tempo_total_min': 0, 'obs_rejeicao': "", 'qtd_lata': 0, 'qtd_pet': 0, 'qtd_oneway': 0, 
                            'qtd_longneck': 0, 'qtd_produzida': 0, 'evidencia_img': ""
                        })
                    st.success("Enviado!")
                    time.sleep(1); st.rerun()
    elif menu == "Tarefas": interface_colaborador_tarefas(uid)
    elif menu == "Auto-Cadastro": interface_colaborador_auto(uid)
    elif menu == "Dashboard":
        st.title("📊 O Seu Desempenho")
        users, tasks = get_data("users"), get_data("tasks")
        meu_saldo = float(users[users['id_login'].astype(str) == uid]['rv_acumulada'].values[0])
        saldo_exibido = min(meu_saldo, LIMITE_RV_OPERADOR)
        minhas = tasks[(tasks['colaborador_id'].astype(str) == uid) & (tasks['status'] == 'Executada')] if not tasks.empty else pd.DataFrame()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Saldo", format_currency(saldo_exibido))
        c2.metric("📦 Tarefas", len(minhas))
        c3.metric("🎯 Ganho KPIs", format_currency(minhas[minhas['atividade'].isin(['EFC', 'TMA', 'FEFO'])]['valor'].sum() if not minhas.empty else 0))
        
        if meu_saldo > LIMITE_RV_OPERADOR: st.warning(f"🔒 Teto atingido! Real: {format_currency(meu_saldo)}. Pagamento limitado a {format_currency(LIMITE_RV_OPERADOR)}.")

def interface_conferente():
    st.sidebar.header(f"👤 {st.session_state.get('user_name', 'Conf')}")
    menu = st.sidebar.radio("Menu", ["Criar Tarefa", "Aprovar Tarefas", "Regras & Valores", "Sair"])
    users, tasks, rules = get_data("users"), get_data("tasks"), get_data("rules")

    if menu == "Sair": do_logout()
    elif menu == "Regras & Valores": interface_regras()
    elif menu == "Criar Tarefa":
        st.title("📋 Nova Atividade")
        ops = users[~users['tipo'].str.lower().str.contains('conferente', na=False)]['nome'].tolist()
        colab = st.selectbox("Colaborador", ops)
        atv = st.selectbox("Atividade", rules['atividade'].tolist() if not rules.empty else [])
        
        sku_resultado = buscar_sku_interface_v2() if atv and "REPACK" not in atv and "SELO" not in atv else "N/A"

        with st.form("task_form"):
            area = st.text_input("Local")
            obs = st.text_area("Obs")
            prio = st.select_slider("Prioridade", ["Baixa", "Média", "Alta"])
            foto_upload = st.file_uploader("Carregar Foto", type=['png', 'jpg', 'jpeg', 'mp4'])
            
            if st.form_submit_button("Enviar"):
                if colab and atv:
                    cid = users[users['nome'] == colab].iloc[0]['id_login']
                    val = float(rules.loc[rules['atividade'] == atv, 'valor'].values[0]) if not rules.empty and not rules.loc[rules['atividade'] == atv].empty else 0.0
                    
                    path_evidencia = ""
                    if foto_upload:
                        ext = foto_upload.name.split('.')[-1].lower()
                        # Usa a nova função de nomenclatura
                        base_name = generate_media_name(colab, atv, sku_resultado, "INICIAL")
                        path_evidencia = f"{IMGS_PATH}/{base_name}.{ext}"
                        with open(path_evidencia, "wb") as f: f.write(foto_upload.getbuffer())
                        
                        # Salva imagem no GitHub
                        upload_media_to_github(path_evidencia)

                    add_task_safe({
                        'id_task': str(uuid.uuid4()), 'colaborador_id': str(cid), 'conferente_id': st.session_state['user_id'],
                        'atividade': atv, 'area': area, 'descricao': obs, 'sku_produto': sku_resultado, 
                        'prioridade': prio, 'status': 'Pendente', 'valor': val, 'data_criacao': get_time_br().strftime("%d/%m %H:%M"),
                        'inicio_execucao': None, 'fim_execucao': None, 'tempo_total_min': 0, 'obs_rejeicao': '',
                        'qtd_lata': 0, 'qtd_pet': 0, 'qtd_oneway': 0, 'qtd_longneck': 0, 'qtd_produzida': 0, 'evidencia_img': path_evidencia
                    })
                    st.success("Criado!")
                else: st.error("Preencha tudo")

    elif menu == "Aprovar Tarefas":
        st.title("✅ Aprovação")
        pends = tasks[(tasks['status'] == 'Aguardando Aprovação') & (~tasks['atividade'].isin(['EFC', 'TMA', 'FEFO']))] if not tasks.empty else pd.DataFrame()
        if pends.empty: st.info("Nenhuma pendente.")
        for i, row in pends.iterrows():
            cname = users[users['id_login'].astype(str) == str(row['colaborador_id'])]['nome'].values
            with st.container():
                st.markdown(f"**{cname[0] if len(cname)>0 else 'User'}** - {row['atividade']}")
                st.caption(f"📦 Material: {row['sku_produto']}")
                c1, c2 = st.columns(2)
                c1.write(f"⏱️ {row['tempo_total_min']} min")
                c1.metric("A Pagar", format_currency(row['valor']))
                
                # Exibe a imagem, puxando do GitHub se não tiver localmente
                img_url = get_media_url(row['evidencia_img'])
                if img_url: 
                    if 'mp4' in img_url.lower(): c2.video(img_url)
                    else: c2.image(img_url, width=200)
                
                b1, b2 = st.columns(2)
                if b1.button("✅ Aprovar", key=f"ok_{row['id_task']}"):
                    if update_rv_safe(row['colaborador_id'], row['valor']):
                        update_task_safe(row['id_task'], {'status': 'Executada'})
                        st.rerun()
                with b2.expander("❌ Rejeitar"):
                    motivo = st.text_input("Motivo:", key=f"m_{row['id_task']}")
                    if st.button("Rejeitar", key=f"r_{row['id_task']}"):
                        update_task_safe(row['id_task'], {'status': 'Rejeitada', 'obs_rejeicao': motivo})
                        st.rerun()
                st.divider()

def interface_colaborador_tarefas(uid):
    tasks = get_data("tasks")
    st.title("🗂️ Tarefas")
    todo = tasks[(tasks['colaborador_id'].astype(str) == str(uid)) & (tasks['status'].isin(['Pendente', 'Em Execução', 'Rejeitada'])) & (~tasks['atividade'].isin(['EFC', 'TMA', 'FEFO']))] if not tasks.empty else pd.DataFrame()
    if todo.empty: st.info("Sem tarefas.")
    
    for i, row in todo.iterrows():
        with st.expander(f"{row['atividade']} ({row['status']})", expanded=True):
            st.write(f"**Local:** {row['area']}")
            st.write(f"**Material:** {row['sku_produto']}")
            
            img_url = get_media_url(row.get('evidencia_img', ''))
            if img_url:
                if 'mp4' in img_url.lower(): st.video(img_url)
                else: st.image(img_url, width=150)

            if row['status'] != 'Em Execução':
                if st.button("▶️ INICIAR", key=f"in_{row['id_task']}"):
                    update_task_safe(row['id_task'], {'status': 'Em Execução', 'inicio_execucao': get_time_br().strftime("%Y-%m-%d %H:%M:%S")})
                    st.rerun()
            else:
                if st.button("⏹️ FINALIZAR", key=f"en_{row['id_task']}"):
                    st.session_state['f_id'] = row['id_task']
                    st.rerun()

            if st.session_state.get('f_id') == row['id_task']:
                st.write("📝 Detalhes")
                with st.form(f"form_{row['id_task']}"):
                    qtd = st.number_input("Quantidade", 1.0)
                    val_calc = float(row['valor']) * qtd
                    
                    foto = st.file_uploader("Foto Evidência Final")
                    if st.form_submit_button("CONCLUIR"):
                        if not foto: st.error("⚠️ Anexe uma foto!")
                        else:
                            ext = foto.name.split('.')[-1].lower()
                            # Usa a nova função de nomenclatura
                            base_name = generate_media_name(st.session_state['user_name'], row['atividade'], row['sku_produto'], "FINAL")
                            pth = f"{IMGS_PATH}/{base_name}.{ext}"
                            
                            with open(pth, "wb") as f: f.write(foto.getbuffer())
                            
                            # Salva imagem no GitHub
                            upload_media_to_github(pth)
                            
                            update_task_safe(row['id_task'], {
                                'status': 'Aguardando Aprovação', 'qtd_produzida': qtd, 'valor': val_calc,
                                'evidencia_img': pth, 'fim_execucao': get_time_br().strftime("%Y-%m-%d %H:%M:%S"),
                                'tempo_total_min': 5 
                            })
                            del st.session_state['f_id']
                            st.rerun()

def interface_colaborador_auto(uid):
    st.title("🙋 Auto-Cadastro")
    rules, users = get_data("rules"), get_data("users")
    confs = users[users['tipo'].str.contains('CONFERENTE', na=False)]['nome'].tolist()
    colab_sel = st.selectbox("Quem aprova?", confs)
    atv = st.selectbox("Atividade", rules['atividade'].tolist() if not rules.empty else [])
    sku_resultado = buscar_sku_interface_v2() if atv and "REPACK" not in atv and "SELO" not in atv else "N/A"
        
    with st.form("auto_c"):
        loc = st.text_input("Local")
        obs = st.text_area("Obs")
        foto_init = st.file_uploader("Foto Inicial (Opcional)")
        
        if st.form_submit_button("CRIAR"):
            if colab_sel and atv:
                conf_id = users[users['nome'] == colab_sel].iloc[0]['id_login']
                val = float(rules.loc[rules['atividade'] == atv, 'valor'].values[0]) if not rules.empty and not rules.loc[rules['atividade'] == atv].empty else 0.0
                
                path_init = ""
                if foto_init:
                    ext = foto_init.name.split('.')[-1].lower()
                    # Usa a nova função de nomenclatura
                    base_name = generate_media_name(st.session_state['user_name'], atv, sku_resultado, "AUTO_INICIAL")
                    path_init = f"{IMGS_PATH}/{base_name}.{ext}"
                    with open(path_init, "wb") as f: f.write(foto_init.getbuffer())
                    
                    # Salva imagem no GitHub
                    upload_media_to_github(path_init)

                add_task_safe({
                    'id_task': str(uuid.uuid4()), 'colaborador_id': str(uid), 'conferente_id': str(conf_id),
                    'atividade': atv, 'area': loc, 'descricao': obs, 'sku_produto': sku_resultado, 
                    'prioridade': 'Média', 'status': 'Pendente', 'valor': val, 'data_criacao': get_time_br().strftime("%d/%m %H:%M"),
                    'inicio_execucao': None, 'fim_execucao': None, 'tempo_total_min': 0, 'obs_rejeicao': '',
                    'qtd_lata': 0, 'qtd_pet': 0, 'qtd_oneway': 0, 'qtd_longneck': 0, 'qtd_produzida': 0, 'evidencia_img': path_init
                })
                st.success("Criado!")
                time.sleep(1)
                st.rerun()

# --- ROTEAMENTO ---
if 'user_id' not in st.session_state:
    if not restore_session(): login_screen()
    else: st.rerun()
else:
    if 'uid' not in st.query_params: st.query_params['uid'] = st.session_state['user_id']
    r = st.session_state.get('role', 'Colaborador')
    if r == 'Supervisor': interface_supervisor()
    elif r == 'Operador': interface_operador()
    elif r == 'Conferente': interface_conferente()
    else: interface_operador()
