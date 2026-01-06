import streamlit as st
import pandas as pd
import os
from datetime import datetime
import time
import uuid
from github import Github
from io import StringIO
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="ProTrack Logística", layout="wide", page_icon="🚛")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stButton>button { border-radius: 8px; background-color: #0054a6; color: white; border: none; height: 40px; font-weight: bold; }
    .stButton>button:hover { background-color: #003d7a; }
    .metric-card { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    h1, h2, h3 { color: #0054a6; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURAÇÕES GLOBAIS ---
ATIVIDADES_POR_CARRO = ["AMARRAÇÃO", "DESCARREGAMENTO DE VAN"]
ATIVIDADES_POR_DIA = ["MÁQUINA LIMPEZA", "5S MARIA MOLE", "5S PICKING/ABASTECIMENTO"]
SUPERVISORES_PERMITIDOS = ['99849441', '99813623', '99797465']
LIMITE_RV_OPERADOR = 380.00
PLANILHA_DRIVE_NOME = "ProTrack_DB" # Nome exato da planilha criada no Passo 2

# Regras Fixas
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

def format_currency(value):
    try: return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "R$ 0,00"

# --- CONEXÕES (GITHUB E DRIVE) ---

@st.cache_resource
def get_github_repo():
    """Conecta ao GitHub"""
    try:
        # Verifica se as chaves existem
        if "github" not in st.secrets:
            st.error("Segredos do GitHub não configurados.")
            return None
            
        token = st.secrets["github"]["token"]
        repo_name = st.secrets["github"]["repo_name"]
        g = Github(token)
        return g.get_repo(repo_name)
    except Exception as e:
        st.error(f"Erro GitHub: {e}")
        return None

@st.cache_resource
def get_google_sheet():
    """Conecta ao Google Drive/Sheets"""
    try:
        if "gcp_service_account" in st.secrets:
            # Converte o objeto de secrets para dicionário normal
            creds_dict = dict(st.secrets["gcp_service_account"])
            
            # Define o escopo de acesso
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            
            # Autentica
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            
            # Abre a planilha
            return client.open(PLANILHA_DRIVE_NOME)
        else:
            print("Segredos do Google não encontrados.")
            return None
    except Exception as e:
        # Não para o app se o Drive falhar, apenas avisa no console
        print(f"Aviso Drive: {e}") 
        return None

# --- LEITURA E ESCRITA ---

def get_data(filename):
    """Lê APENAS do GitHub (Mais rápido e estável para leitura)"""
    repo = get_github_repo()
    if not repo: return init_empty_df(filename)
    
    file_path = f"data/{filename}.csv"
    try:
        file_content = repo.get_contents(file_path)
        csv_data = file_content.decoded_content.decode('utf-8')
        df = pd.read_csv(StringIO(csv_data), sep=';', dtype=str)
        
        # Conversão de tipos
        if filename == 'tasks':
            df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
            df['tempo_total_min'] = pd.to_numeric(df['tempo_total_min'], errors='coerce').fillna(0.0)
            df['qtd_produzida'] = pd.to_numeric(df['qtd_produzida'], errors='coerce').fillna(0.0)
        elif filename == 'users':
             if 'rv_acumulada' in df.columns:
                df['rv_acumulada'] = pd.to_numeric(df['rv_acumulada'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
        elif filename == 'rules':
            df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
            
        return df
    except Exception as e:
        if "404" in str(e): return init_empty_df(filename)
        return init_empty_df(filename)

def init_empty_df(filename):
    if filename == 'tasks':
        cols = ['id_task', 'colaborador_id', 'conferente_id', 'atividade', 'area', 'descricao', 
                'sku_produto', 'prioridade', 'status', 'valor', 'data_criacao', 'inicio_execucao', 
                'fim_execucao', 'tempo_total_min', 'obs_rejeicao', 'qtd_lata', 'qtd_pet', 
                'qtd_oneway', 'qtd_longneck', 'qtd_produzida', 'evidencia_img']
        return pd.DataFrame(columns=cols)
    elif filename == 'users': return pd.DataFrame(columns=['nome', 'id_login', 'tipo', 'rv_acumulada'])
    elif filename == 'rules': return pd.DataFrame(NOVAS_REGRAS)
    elif filename == 'sku': return pd.DataFrame(columns=['codigo', 'descricao'])
    return pd.DataFrame()

def save_data(df, filename):
    """SALVA NO GITHUB E DEPOIS ESPELHA NO DRIVE"""
    
    # 1. Salva no GitHub (Prioridade)
    repo = get_github_repo()
    if repo:
        file_path = f"data/{filename}.csv"
        csv_content = df.to_csv(index=False, sep=';')
        try:
            contents = repo.get_contents(file_path)
            repo.update_file(file_path, f"Update {filename}", csv_content, contents.sha)
        except:
            try: repo.create_file(file_path, f"Create {filename}", csv_content)
            except: pass

    # 2. Salva no Google Drive (Backup Visual)
    # Isso roda em 'segundo plano' (se falhar, não trava o app)
    try:
        sheet = get_google_sheet()
        if sheet:
            # Tenta pegar a aba, se não existir, cria
            try: ws = sheet.worksheet(filename)
            except: ws = sheet.add_worksheet(title=filename, rows="1000", cols="20")
            
            ws.clear() # Limpa a aba antes de escrever
            
            # Prepara dados para o Sheets (sem NaN)
            df_drive = df.fillna('')
            df_drive = df_drive.astype(str)
            
            # Escreve (Cabeçalho + Dados)
            ws.update([df_drive.columns.values.tolist()] + df_drive.values.tolist())
    except Exception as e:
        print(f"Erro ao salvar backup no Drive: {e}")

# --- FUNÇÕES DE NEGÓCIO ---

def add_task_safe(task_dict):
    df = get_data("tasks")
    new_row = pd.DataFrame([task_dict])
    new_row = new_row.astype(str)
    df = pd.concat([df, new_row], ignore_index=True)
    save_data(df, "tasks")

def update_task_safe(task_id, updates):
    df = get_data("tasks")
    if df.empty: return
    idx = df[df['id_task'].astype(str) == str(task_id)].index
    if not idx.empty:
        for col, val in updates.items():
            df.at[idx[0], col] = str(val)
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

def buscar_sku_interface():
    df_sku = get_data("sku")
    codigo = st.text_input("Digite o Código do Produto:")
    nome = "-"
    if codigo and not df_sku.empty:
        try:
            col_cod = df_sku.columns[0]
            col_nome = df_sku.columns[1]
            res = df_sku[df_sku[col_cod].astype(str).str.strip() == codigo.strip()]
            if not res.empty: nome = res.iloc[0][col_nome]
            else: nome = "❌ Não encontrado"
        except: pass
    st.text_input("Material", value=nome, disabled=True)
    return f"{codigo} - {nome}" if nome != "-" else "-"

# --- TELAS (INTERFACE) ---
def login_screen():
    st.markdown("<h1 style='text-align: center; color: #0054a6;'>ProTrack Logística 🚛</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.info("Insira seu ID ou Matrícula")
        lid = st.text_input("ID").strip()
        if st.button("ENTRAR"):
            users = get_data("users")
            if users.empty:
                st.warning("Criando Admin inicial...")
                users = pd.DataFrame([{'nome': 'Admin', 'id_login': 'admin', 'tipo': 'Supervisor', 'rv_acumulada': 0}])
                save_data(users, 'users')

            user = users[users['id_login'].astype(str) == lid]
            if not user.empty:
                st.session_state['user_id'] = str(user.iloc[0]['id_login'])
                st.session_state['user_name'] = user.iloc[0]['nome']
                tipo = str(user.iloc[0]['tipo']).upper()
                
                if st.session_state['user_id'] in SUPERVISORES_PERMITIDOS: st.session_state['role'] = 'Supervisor'
                elif 'OPERADOR' in tipo: st.session_state['role'] = 'Operador'
                elif 'CONFERENTE' in tipo: st.session_state['role'] = 'Conferente'
                else: st.session_state['role'] = 'Colaborador'
                st.rerun()
            else: st.error("Usuário não cadastrado.")

def interface_supervisor():
    st.sidebar.header(f"👮 {st.session_state.get('user_name', 'Sup')}")
    menu = st.sidebar.radio("Menu", ["Validar KPIs", "Ajustes Financeiros", "Ranking", "Cadastrar Usuário", "Sair"])
    
    if menu == "Sair": st.session_state.clear(); st.rerun()
    
    users = get_data("users")
    tasks = get_data("tasks")
    rules = get_data("rules")

    if menu == "Validar KPIs":
        st.title("🛡️ Validar Metas (KPIs)")
        if tasks.empty: st.info("Nada pendente.")
        else:
            pendentes = tasks[(tasks['status'] == 'Aguardando Validação') & (tasks['atividade'].isin(['EFC', 'TMA', 'FEFO']))]
            if pendentes.empty: st.info("Tudo validado!")
            else:
                for i, row in pendentes.iterrows():
                    cname = users[users['id_login'].astype(str) == str(row['colaborador_id'])]['nome'].values
                    nome_colab = cname[0] if len(cname) > 0 else row['colaborador_id']
                    
                    with st.container():
                        c1, c2, c3 = st.columns([3,1,1])
                        val = float(row['valor'])
                        c1.markdown(f"**{nome_colab}** - {row['atividade']} ({'OK' if val>0 else 'NOK'})")
                        if c2.button("✅ Confirmar", key=f"ok{i}"):
                            if update_rv_safe(row['colaborador_id'], val):
                                update_task_safe(row['id_task'], {'status': 'Executada'})
                                st.rerun()
                        if c3.button("✏️ Alterar", key=f"nok{i}"):
                            n_val = 0.0
                            if val == 0:
                                try: n_val = float(rules[rules['atividade']==row['atividade']]['valor'].values[0])
                                except: n_val = 0.0
                            if update_rv_safe(row['colaborador_id'], n_val):
                                update_task_safe(row['id_task'], {'status': 'Executada', 'valor': n_val})
                                st.rerun()
                        st.divider()

    elif menu == "Ajustes Financeiros":
        st.title("💰 Ajustes")
        with st.form("ajuste"):
            ops = users['nome'].tolist()
            sel = st.selectbox("Colaborador", ops)
            tipo = st.radio("Tipo", ["Crédito (+)", "Débito (-)"], horizontal=True)
            val = st.number_input("Valor", min_value=0.0, step=1.0)
            mot = st.text_input("Motivo")
            if st.form_submit_button("PROCESSAR"):
                if val > 0 and mot:
                    cid = users[users['nome']==sel].iloc[0]['id_login']
                    vf = val if tipo == "Crédito (+)" else -val
                    if update_rv_safe(cid, vf):
                        add_task_safe({
                            'id_task': str(uuid.uuid4()), 'colaborador_id': str(cid), 'conferente_id': st.session_state['user_id'],
                            'atividade': "AJUSTE MANUAL", 'area': "ADM", 'descricao': f"{tipo}: {mot}", 'sku_produto': "-",
                            'prioridade': "Alta", 'status': "Executada", 'valor': vf, 'data_criacao': datetime.now().strftime("%d/%m %H:%M"),
                            'qtd_produzida': 0
                        })
                        st.success("Feito!")
                        st.rerun()

    elif menu == "Ranking":
        st.title("🏆 Ranking")
        df = users[['nome', 'rv_acumulada']].sort_values('rv_acumulada', ascending=False)
        df['rv_acumulada'] = df['rv_acumulada'].apply(format_currency)
        st.table(df)

    elif menu == "Cadastrar Usuário":
        st.title("➕ Novo Usuário")
        with st.form("nu"):
            nm = st.text_input("Nome")
            lid = st.text_input("ID")
            tp = st.selectbox("Tipo", ["Operador", "Conferente", "Colaborador", "Supervisor"])
            if st.form_submit_button("SALVAR"):
                if nm and lid:
                    nu = pd.DataFrame([{'nome': nm, 'id_login': lid, 'tipo': tp, 'rv_acumulada': 0.0}])
                    nu = nu.astype(str)
                    users = pd.concat([users, nu], ignore_index=True)
                    save_data(users, 'users')
                    st.success("Cadastrado!")

def interface_operador():
    st.sidebar.header(f"👷 {st.session_state['user_name']}")
    opts = ["Tarefas", "Auto-Cadastro", "Dashboard", "Sair"]
    if st.session_state['role'] == 'Operador': opts.insert(0, "🚀 KPIs Diários")
    menu = st.sidebar.radio("Menu", opts)
    uid = st.session_state['user_id']
    
    if menu == "Sair": st.session_state.clear(); st.rerun()

    if menu == "🚀 KPIs Diários":
        st.title("Metas do Dia")
        rules = get_data("rules")
        tasks = get_data("tasks")
        hoje = datetime.now().strftime("%d/%m")
        
        ja_fez = False
        if not tasks.empty:
            tasks['colaborador_id'] = tasks['colaborador_id'].astype(str)
            ja_fez = not tasks[(tasks['colaborador_id']==uid) & (tasks['data_criacao'].str.contains(hoje)) & (tasks['atividade'].isin(['EFC']))].empty
            
        if ja_fez: st.info("Já enviado.")
        else:
            def gv(n): 
                try: return float(rules[rules['atividade']==n]['valor'].values[0])
                except: return 0.0
            with st.form("kpi"):
                c1 = st.checkbox(f"EFC ({format_currency(gv('EFC'))})")
                c2 = st.checkbox(f"TMA ({format_currency(gv('TMA'))})")
                c3 = st.checkbox(f"FEFO ({format_currency(gv('FEFO'))})")
                if st.form_submit_button("ENVIAR"):
                    lst = [('EFC',c1), ('TMA',c2), ('FEFO',c3)]
                    for n, ch in lst:
                        v = gv(n) if ch else 0.0
                        add_task_safe({
                            'id_task': str(uuid.uuid4()), 'colaborador_id': uid, 'conferente_id': 'SIS',
                            'atividade': n, 'area': 'OP', 'descricao': 'Auto', 'sku_produto': '-',
                            'prioridade': 'Alta', 'status': 'Aguardando Validação', 'valor': v,
                            'data_criacao': datetime.now().strftime("%d/%m %H:%M"), 'qtd_produzida': 0
                        })
                    st.success("Enviado!")
                    st.rerun()

    elif menu == "Tarefas":
        interface_colaborador_tarefas(uid)
    elif menu == "Auto-Cadastro":
        interface_colaborador_auto(uid)
    elif menu == "Dashboard":
        st.title("📊 Painel")
        users = get_data("users")
        s = users[users['id_login'].astype(str)==uid]['rv_acumulada'].values
        saldo = float(s[0]) if len(s)>0 else 0.0
        c1, c2 = st.columns(2)
        c1.metric("Saldo", format_currency(saldo))
        if saldo > LIMITE_RV_OPERADOR: st.warning("Teto atingido.")

def interface_conferente():
    st.sidebar.header(f"👤 {st.session_state.get('user_name', 'Conf')}")
    menu = st.sidebar.radio("Menu", ["Criar Tarefa", "Aprovar Tarefas", "Sair"])
    if menu == "Sair": st.session_state.clear(); st.rerun()
    
    users = get_data("users")
    tasks = get_data("tasks")
    rules = get_data("rules")

    if menu == "Criar Tarefa":
        st.title("📋 Nova Tarefa")
        sku = buscar_sku_interface()
        with st.form("nt"):
            c = st.selectbox("Colaborador", users[~users['tipo'].str.contains("Conferente")]['nome'].tolist())
            a = st.selectbox("Atividade", rules['atividade'].tolist())
            l = st.text_input("Local")
            o = st.text_area("Obs")
            if st.form_submit_button("CRIAR"):
                cid = users[users['nome']==c].iloc[0]['id_login']
                val = rules.loc[rules['atividade']==a, 'valor'].values[0]
                add_task_safe({
                    'id_task': str(uuid.uuid4()), 'colaborador_id': str(cid), 'conferente_id': st.session_state['user_id'],
                    'atividade': a, 'area': l, 'descricao': o, 'sku_produto': sku,
                    'prioridade': 'Media', 'status': 'Pendente', 'valor': float(val),
                    'data_criacao': datetime.now().strftime("%d/%m %H:%M"), 'qtd_produzida': 0
                })
                st.success("Criado!")

    elif menu == "Aprovar Tarefas":
        st.title("✅ Aprovação")
        if not tasks.empty:
            pend = tasks[(tasks['status']=='Aguardando Aprovação') & (~tasks['atividade'].isin(['EFC']))]
            if pend.empty: st.info("Nada.")
            for i, r in pend.iterrows():
                with st.expander(f"{r['atividade']} - {r['colaborador_id']}"):
                    st.write(f"Valor: {format_currency(r['valor'])}")
                    if st.button("Aprovar", key=f"ap{i}"):
                        if update_rv_safe(r['colaborador_id'], r['valor']):
                            update_task_safe(r['id_task'], {'status': 'Executada'})
                            st.rerun()
                    if st.button("Rejeitar", key=f"rj{i}"):
                        update_task_safe(r['id_task'], {'status': 'Rejeitada', 'obs_rejeicao': 'Conf recusou'})
                        st.rerun()

# --- MODULOS COMPARTILHADOS ---
def interface_colaborador_tarefas(uid):
    tasks = get_data("tasks")
    st.title("Tarefas")
    if tasks.empty: 
        st.info("Sem tarefas.")
        return
    tasks['colaborador_id'] = tasks['colaborador_id'].astype(str)
    minhas = tasks[(tasks['colaborador_id']==str(uid)) & (tasks['status'].isin(['Pendente', 'Em Execução', 'Rejeitada'])) & (~tasks['atividade'].isin(['EFC']))]
    
    if minhas.empty: st.info("Sem pendências.")
    for i, r in minhas.iterrows():
        with st.expander(f"{r['atividade']} ({r['status']})"):
            st.write(f"Local: {r['area']} | Obs: {r['descricao']}")
            if r['status'] == 'Rejeitada': st.error(r['obs_rejeicao'])
            
            if r['status'] != 'Em Execução':
                if st.button("INICIAR", key=f"i{i}"):
                    update_task_safe(r['id_task'], {'status': 'Em Execução'})
                    st.rerun()
            else:
                with st.form(f"f{i}"):
                    q = st.number_input("Qtd", 1.0)
                    if st.form_submit_button("ENTREGAR"):
                        v = float(r['valor']) * (q if r['atividade'] not in ATIVIDADES_POR_DIA else 1)
                        update_task_safe(r['id_task'], {'status': 'Aguardando Aprovação', 'qtd_produzida': q, 'valor': v})
                        st.rerun()

def interface_colaborador_auto(uid):
    st.title("Auto-Lançamento")
    rules = get_data("rules")
    users = get_data("users")
    confs = users[users['tipo'].str.contains('CONFERENTE', case=False)]['nome'].tolist()
    with st.form("al"):
        c = st.selectbox("Aprovador", confs)
        a = st.selectbox("Atividade", rules['atividade'].tolist())
        l = st.text_input("Local")
        if st.form_submit_button("LANÇAR"):
            cid = users[users['nome']==c].iloc[0]['id_login']
            val = rules.loc[rules['atividade']==a, 'valor'].values[0]
            add_task_safe({
                'id_task': str(uuid.uuid4()), 'colaborador_id': uid, 'conferente_id': str(cid),
                'atividade': a, 'area': l, 'descricao': 'Auto', 'sku_produto': '-',
                'prioridade': 'Media', 'status': 'Pendente', 'valor': float(val),
                'data_criacao': datetime.now().strftime("%d/%m %H:%M"), 'qtd_produzida': 0
            })
            st.success("Lançado!")

# --- ROTEAMENTO ---
if 'user_id' not in st.session_state:
    login_screen()
else:
    r = st.session_state.get('role', 'Colaborador')
    if r == 'Supervisor': interface_supervisor()
    elif r == 'Operador': interface_operador()
    elif r == 'Conferente': interface_conferente()
    else: interface_operador()
