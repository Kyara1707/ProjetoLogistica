import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import time
import uuid

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
    h1, h2, h3 { color: #0054a6; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURAÇÕES GLOBAIS ---
ATIVIDADES_POR_CARRO = ["AMARRAÇÃO", "DESCARREGAMENTO DE VAN"]
ATIVIDADES_POR_DIA = ["MÁQUINA LIMPEZA", "5S MARIA MOLE", "5S PICKING/ABASTECIMENTO"]
SUPERVISORES_PERMITIDOS = ['99849441', '99813623', '99797465']
LIMITE_RV_OPERADOR = 380.00  

# Tabela de preços fixa
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
    # Ajuste simples para horário Brasil (UTC-3)
    return datetime.now() - timedelta(hours=3)

# --- GERENCIAMENTO DE DADOS ---
def init_data():
    if not os.path.exists(f"{FILES_PATH}/rules.csv"):
        df_regras = pd.DataFrame(NOVAS_REGRAS)
        df_regras.to_csv(f"{FILES_PATH}/rules.csv", index=False, sep=';', encoding='utf-8-sig')
    
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

init_data()

def get_data(filename):
    path = f"{FILES_PATH}/{filename}.csv"
    if not os.path.exists(path):
        init_data()
        if not os.path.exists(path): return pd.DataFrame()

    try:
        try:
            df = pd.read_csv(path, sep=';', encoding='utf-8-sig', dtype=str)
        except UnicodeDecodeError:
            df = pd.read_csv(path, sep=';', encoding='latin1', dtype=str)
        
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
    except Exception as e:
        return pd.DataFrame()

def save_data(df, filename):
    try: df.to_csv(f"{FILES_PATH}/{filename}.csv", index=False, sep=';', encoding='utf-8-sig')
    except: st.error(f"Erro ao salvar {filename}. Feche o arquivo se estiver aberto.")

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
        for col, val in updates.items():
            df.at[idx[0], col] = val
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

# --- FUNÇÃO DE BUSCA DE SKU ---
def buscar_sku_interface_v2():
    df_sku = get_data("sku")
    
    if df_sku.empty:
        st.warning("Base de SKUs vazia.")
        return "-"

    df_sku['display'] = df_sku.iloc[:, 1].astype(str) + " | Cód: " + df_sku.iloc[:, 0].astype(str)
    opcoes = df_sku['display'].tolist()
    
    st.write("Pesquise o Material:")
    escolha = st.selectbox("Selecione o Produto (Digite para buscar)", [""] + opcoes)
    
    codigo_travado = ""
    nome_produto = "-"
    
    if escolha:
        try:
            parts = escolha.split(" | Cód: ")
            nome_produto = parts[0]
            codigo_travado = parts[1]
        except:
            codigo_travado = "Erro"
            
    st.text_input("Código do SKU (Travado)", value=codigo_travado, disabled=True)
    
    if codigo_travado and codigo_travado != "Erro":
        return f"{codigo_travado} - {nome_produto}"
    return "-"

# --- TELAS DO SISTEMA ---
def login_screen():
    st.markdown("<h1 style='text-align: center; color: #0054a6;'>ProTrack Logística 🚛</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.info("Insira seu ID ou Matrícula")
        lid = st.text_input("ID").strip()
        if st.button("ENTRAR"):
            users = get_data("users")
            if users.empty:
                st.error("Arquivo de usuários vazio ou não encontrado.")
                return

            user = users[users['id_login'].astype(str) == lid]
            if not user.empty:
                st.session_state['user_id'] = str(user.iloc[0]['id_login'])
                st.session_state['user_name'] = user.iloc[0]['nome']
                tipo = str(user.iloc[0]['tipo']).upper()
                
                if st.session_state['user_id'] in SUPERVISORES_PERMITIDOS: 
                    st.session_state['role'] = 'Supervisor'
                elif 'OPERADOR' in tipo: 
                    st.session_state['role'] = 'Operador'
                elif 'CONFERENTE' in tipo: 
                    st.session_state['role'] = 'Conferente'
                else: 
                    st.session_state['role'] = 'Colaborador' 
                st.rerun()
            else: st.error("Usuário não cadastrado.")

def interface_supervisor():
    st.sidebar.header(f"👮 {st.session_state.get('user_name', 'Sup')}")
    menu = st.sidebar.radio("Menu", ["Validar KPIs", "Ajustes Financeiros", "Ranking", "Sair"])
    
    if menu == "Sair": 
        st.session_state.clear()
        st.rerun()
    
    users = get_data("users")
    rules = get_data("rules")
    tasks = get_data("tasks")

    if menu == "Validar KPIs":
        st.title("🛡️ Validar Metas (KPIs)")
        if tasks.empty:
            st.info("Nenhuma tarefa para validar.")
        else:
            pendentes = tasks[(tasks['status'] == 'Aguardando Validação') & (tasks['atividade'].isin(['EFC', 'TMA', 'FEFO']))]
            
            if pendentes.empty: st.info("Tudo validado!")
            else:
                for i, row in pendentes.iterrows():
                    k_ok = f"btn_ok_{row['id_task']}_{i}"
                    k_nok = f"btn_nok_{row['id_task']}_{i}"
                    
                    cname = users[users['id_login'].astype(str) == str(row['colaborador_id'])]['nome'].values
                    nome_colab = cname[0] if len(cname) > 0 else row['colaborador_id']
                    
                    with st.container():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        val = float(row['valor'])
                        status_user = "OK" if val > 0 else "NOK"
                        
                        col1.markdown(f"**{nome_colab}** | {row['atividade']} | Declarado: **{status_user}** ({format_currency(val)})")
                        
                        if col2.button("✅ Confirmar", key=k_ok):
                            if update_rv_safe(row['colaborador_id'], val):
                                update_task_safe(row['id_task'], {'status': 'Executada'})
                                st.rerun()
                                
                        if col3.button("✏️ Alterar", key=k_nok):
                            novo_status = 'Não Atingido' if val > 0 else 'Executada'
                            novo_valor = 0.0
                            obs = "Supervisor alterou para NOK"
                            
                            if val == 0: 
                                try: novo_valor = float(rules.loc[rules['atividade'] == row['atividade'], 'valor'].values[0])
                                except: novo_valor = 0.0
                                obs = "Supervisor alterou para OK"

                            if update_rv_safe(row['colaborador_id'], novo_valor):
                                update_task_safe(row['id_task'], {'status': novo_status, 'valor': novo_valor, 'obs_rejeicao': obs})
                                st.rerun()
                        st.divider()

    elif menu == "Ajustes Financeiros":
        st.title("💰 Ajuste de Saldo (Crédito/Débito)")
        
        with st.form("ajuste_form"):
            ops = users['nome'].tolist()
            colab = st.selectbox("Colaborador", ops)
            tipo = st.radio("Tipo de Ajuste", ["Crédito (+)", "Débito (-)"], horizontal=True)
            valor = st.number_input("Valor (R$)", min_value=0.0, step=0.5)
            motivo = st.text_input("Motivo (Ex: Bônus Meta Semanal, Quebra de Material)")
            
            if st.form_submit_button("PROCESSAR AJUSTE"):
                if valor > 0 and motivo:
                    cid = users[users['nome'] == colab].iloc[0]['id_login']
                    valor_final = valor if tipo == "Crédito (+)" else -valor
                    
                    if update_rv_safe(cid, valor_final):
                        task = {
                            'id_task': str(uuid.uuid4()), 
                            'colaborador_id': str(cid),
                            'conferente_id': st.session_state['user_id'],
                            'atividade': "AJUSTE MANUAL",
                            'area': "ADM",
                            'descricao': f"{tipo}: {motivo}",
                            'sku_produto': "-",
                            'prioridade': 'Alta',
                            'status': 'Executada',
                            'valor': float(valor_final),
                            'data_criacao': get_time_br().strftime("%d/%m %H:%M"),
                            'inicio_execucao': "-", 'fim_execucao': "-", 
                            'tempo_total_min': 0, 'obs_rejeicao': "", 
                            'qtd_lata': 0, 'qtd_pet': 0, 'qtd_oneway': 0, 'qtd_longneck': 0, 
                            'qtd_produzida': 0, 'evidencia_img': ""
                        }
                        add_task_safe(task)
                        st.success(f"Sucesso! Ajuste de {format_currency(valor_final)} realizado.")
                        time.sleep(1)
                        st.rerun()
                    else: st.error("Erro ao atualizar saldo.")
                else:
                    st.warning("Insira valor e motivo.")

    elif menu == "Ranking":
        st.title("🏆 Ranking Geral")
        df_rank = users[['nome', 'rv_acumulada']].copy()
        df_rank = df_rank.sort_values('rv_acumulada', ascending=False).reset_index(drop=True)
        df_rank['rv_acumulada'] = df_rank['rv_acumulada'].apply(format_currency)
        st.table(df_rank)

def interface_operador():
    if 'role' not in st.session_state or 'user_id' not in st.session_state:
        st.session_state.clear()
        st.rerun()

    st.sidebar.header(f"👷 {st.session_state['user_name']}")
    
    opcoes_menu = ["Tarefas", "Auto-Cadastro", "Dashboard", "Sair"]
    
    if st.session_state.get('role') == 'Operador':
        opcoes_menu.insert(0, "🚀 KPIs Diários")
        
    menu = st.sidebar.radio("Menu", opcoes_menu)
    uid = st.session_state['user_id']
    
    if menu == "Sair": 
        st.session_state.clear()
        st.rerun()

    if menu == "🚀 KPIs Diários" and st.session_state.get('role') == 'Operador':
        st.title("🚀 Metas do Dia")
        rules = get_data("rules")
        
        def get_val(name):
            try: return float(rules[rules['atividade']==name]['valor'].values[0])
            except: return 0.0
            
        v_efc = get_val('EFC')
        v_tma = get_val('TMA')
        v_fefo = get_val('FEFO')
        
        hoje = get_time_br().strftime("%d/%m")
        tasks = get_data("tasks")
        
        ja_fez = False
        if not tasks.empty:
            tasks['colaborador_id'] = tasks['colaborador_id'].astype(str)
            ja_fez = not tasks[(tasks['colaborador_id']==uid) & (tasks['data_criacao'].str.contains(hoje)) & (tasks['atividade'].isin(['EFC','TMA']))].empty
        
        if ja_fez:
            st.info("✅ KPIs de hoje já enviados e aguardando validação.")
        else:
            with st.form("kpi_form"):
                st.write("Marque as metas batidas:")
                c_efc = st.checkbox(f"EFC ({format_currency(v_efc)})")
                c_tma = st.checkbox(f"TMA ({format_currency(v_tma)})")
                c_fefo = st.checkbox(f"FEFO ({format_currency(v_fefo)})")
                
                if st.form_submit_button("ENVIAR"):
                    lista = [("EFC", c_efc, v_efc), ("TMA", c_tma, v_tma), ("FEFO", c_fefo, v_fefo)]
                    for nome, check, val in lista:
                        vf = val if check else 0.0
                        task = {
                            'id_task': str(uuid.uuid4()),
                            'colaborador_id': uid,
                            'conferente_id': 'SISTEMA',
                            'atividade': nome,
                            'area': 'OPERAÇÃO',
                            'descricao': 'Auto-Avaliação',
                            'sku_produto': '-', 'prioridade': 'Alta',
                            'status': 'Aguardando Validação',
                            'valor': float(vf),
                            'data_criacao': get_time_br().strftime("%d/%m %H:%M"),
                            'inicio_execucao': "-", 'fim_execucao': "-", 
                            'tempo_total_min': 0, 'obs_rejeicao': "", 
                            'qtd_lata': 0, 'qtd_pet': 0, 'qtd_oneway': 0, 'qtd_longneck': 0, 
                            'qtd_produzida': 0, 'evidencia_img': ""
                        }
                        add_task_safe(task)
                    st.success("Enviado com sucesso!")
                    time.sleep(1)
                    st.rerun()

    elif menu == "Tarefas":
        interface_colaborador_tarefas(uid)
        
    elif menu == "Auto-Cadastro":
        interface_colaborador_auto(uid)
        
    elif menu == "Dashboard":
        st.title("📊 Seu Desempenho")
        users = get_data("users")
        meu_saldo = users[users['id_login'].astype(str) == uid]['rv_acumulada'].values
        saldo_real = float(meu_saldo[0]) if len(meu_saldo) > 0 else 0.0
        
        saldo_exibido = min(saldo_real, LIMITE_RV_OPERADOR)
        
        tasks = get_data("tasks")
        total_tarefas = 0
        soma_kpis = 0.0

        if not tasks.empty:
            minhas = tasks[(tasks['colaborador_id'].astype(str) == uid) & (tasks['status'] == 'Executada')]
            total_tarefas = len(minhas)
            kpi_tasks = minhas[minhas['atividade'].isin(['EFC', 'TMA', 'FEFO'])]
            if not kpi_tasks.empty:
                soma_kpis = kpi_tasks['valor'].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Saldo Total (RV)", format_currency(saldo_exibido))
        c2.metric("📦 Tarefas Executadas", total_tarefas)
        
        if st.session_state.get('role') == 'Operador':
            c3.metric("🎯 Ganho com KPIs", format_currency(soma_kpis))
        else:
            c3.metric("⭐ Status", "Ativo") 

        if saldo_real > LIMITE_RV_OPERADOR:
            st.warning(f"🔒 Teto de RV atingido! Seu acumulado real é {format_currency(saldo_real)}, mas o pagamento é limitado a {format_currency(LIMITE_RV_OPERADOR)}.")

        st.subheader("Histórico Recente")
        if not tasks.empty:
            hist = tasks[(tasks['colaborador_id'].astype(str) == uid)].sort_values('data_criacao', ascending=False).head(10)
            st.dataframe(hist[['data_criacao', 'atividade', 'status', 'valor']], use_container_width=True)

def interface_conferente():
    st.sidebar.header(f"👤 {st.session_state.get('user_name', 'Conf')}")
    menu = st.sidebar.radio("Menu", ["Criar Tarefa", "Aprovar Tarefas", "Sair"])
    users = get_data("users")
    tasks = get_data("tasks")
    rules = get_data("rules")

    if menu == "Sair":
        st.session_state.clear()
        st.rerun()

    elif menu == "Criar Tarefa":
        st.title("📋 Nova Atividade")

        ops = users[~users['tipo'].str.lower().str.contains('conferente', na=False)]['nome'].tolist()
        atvs = rules['atividade'].tolist() if not rules.empty else []
        
        colab = st.selectbox("Colaborador", ops)
        atv = st.selectbox("Atividade", atvs)
        
        sku_resultado = "-"
        if atv and ("REPACK" not in atv) and ("SELO VERMELHO" not in atv):
            st.markdown("---")
            sku_resultado = buscar_sku_interface_v2()
            st.markdown("---")
        else:
            st.info("SKU não obrigatório para esta atividade.")
            sku_resultado = "N/A"

        with st.form("task_form"):
            area = st.text_input("Local")
            obs = st.text_area("Obs")
            prio = st.select_slider("Prioridade", ["Baixa", "Média", "Alta"])

            st.markdown("### 📷 Evidência Inicial (Opcional)")
            foto_upload = st.file_uploader("Carregar Foto ou Vídeo", type=['png', 'jpg', 'jpeg', 'mp4', 'avi'])
            
            if st.form_submit_button("Enviar"):
                if colab and atv:
                    cid = users[users['nome'] == colab].iloc[0]['id_login']
                    val = 0.0
                    if not rules.empty:
                        val_lookup = rules.loc[rules['atividade'] == atv, 'valor']
                        if not val_lookup.empty: val = val_lookup.values[0]

                    path_evidencia = ""
                    task_id_new = str(uuid.uuid4())
                    
                    if foto_upload:
                        ext = foto_upload.name.split('.')[-1].lower()
                        path_evidencia = f"{IMGS_PATH}/{task_id_new}_INICIAL.{ext}"
                        with open(path_evidencia, "wb") as f:
                            f.write(foto_upload.getbuffer())

                    task = {
                        'id_task': task_id_new,
                        'colaborador_id': str(cid), 
                        'conferente_id': st.session_state['user_id'],
                        'atividade': atv, 'area': area, 'descricao': obs, 
                        'sku_produto': sku_resultado, 'prioridade': prio, 'status': 'Pendente',
                        'valor': float(val), 'data_criacao': get_time_br().strftime("%d/%m %H:%M"),
                        'inicio_execucao': None, 'fim_execucao': None, 
                        'tempo_total_min': 0, 'obs_rejeicao': '',
                        'qtd_lata': 0, 'qtd_pet': 0, 'qtd_oneway': 0, 'qtd_longneck': 0, 
                        'qtd_produzida': 0, 'evidencia_img': path_evidencia
                    }
                    add_task_safe(task)
                    st.success(f"Tarefa criada para {colab}!")
                else:
                    st.error("Selecione colaborador e atividade")

    elif menu == "Aprovar Tarefas":
        st.title("✅ Aprovação")
        if not tasks.empty:
            pends = tasks[(tasks['status'] == 'Aguardando Aprovação') & (~tasks['atividade'].isin(['EFC', 'TMA', 'FEFO']))]
            
            if pends.empty: st.info("Nenhuma tarefa pendente.")
            
            for i, row in pends.iterrows():
                k_approve = f"ok_{row['id_task']}_{i}"
                k_reject_btn = f"rej_btn_{row['id_task']}_{i}"
                k_reason = f"reason_{row['id_task']}_{i}"
                
                cname = users[users['id_login'].astype(str) == str(row['colaborador_id'])]['nome'].values
                name = cname[0] if len(cname)>0 else "Desconhecido"
                
                with st.container():
                    st.markdown(f"**{name}** - {row['atividade']}")
                    sku_info = row['sku_produto'] if pd.notna(row['sku_produto']) else "-"
                    st.caption(f"📦 Material: {sku_info}")

                    c1, c2 = st.columns(2)
                    c1.write(f"⏱️ {row['tempo_total_min']} min")
                    
                    if row['atividade'] == 'REPACK':
                        c1.info(f"🥫L:{row['qtd_lata']} 🍾P:{row['qtd_pet']} 🧊OW:{row['qtd_oneway']} 🍺LN:{row['qtd_longneck']}")
                    else:
                        c1.info(f"Qtd: {row['qtd_produzida']}")
                    
                    c1.metric("A Pagar", format_currency(row['valor']))
                    
                    if pd.notna(row['evidencia_img']) and row['evidencia_img']:
                        if os.path.exists(row['evidencia_img']):
                            ext = row['evidencia_img'].split('.')[-1].lower()
                            if ext in ['mp4', 'avi', 'mov', 'mkv']:
                                c2.video(row['evidencia_img'])
                            else:
                                try: c2.image(row['evidencia_img'], width=200, caption="Evidência")
                                except: c2.error("Erro ao carregar imagem")
                        else:
                            c2.warning("Arquivo não encontrado no servidor.")
                    
                    b1, b2 = st.columns(2)
                    if b1.button("✅ Aprovar", key=k_approve):
                        if update_rv_safe(row['colaborador_id'], row['valor']):
                            update_task_safe(row['id_task'], {'status': 'Executada'})
                            st.success("Pago!")
                            time.sleep(0.5)
                            st.rerun()
                    
                    with b2:
                        with st.expander("❌ Rejeitar"):
                            motivo = st.text_input("Motivo:", key=k_reason)
                            if st.button("Confirmar Rejeição", key=k_reject_btn):
                                update_task_safe(row['id_task'], {'status': 'Rejeitada', 'obs_rejeicao': motivo})
                                st.rerun()
                    st.divider()
        else: st.info("Sem tarefas.")

# --- FUNÇÕES REUTILIZÁVEIS ---
def interface_colaborador_tarefas(uid):
    tasks = get_data("tasks")
    st.title("🗂️ Tarefas")
    
    if tasks.empty:
        st.info("Nenhuma tarefa encontrada.")
        return

    tasks['colaborador_id'] = tasks['colaborador_id'].astype(str)
    mask_pend = (tasks['colaborador_id'] == str(uid)) & \
                (tasks['status'].isin(['Pendente', 'Em Execução', 'Rejeitada'])) & \
                (~tasks['atividade'].isin(['EFC', 'TMA', 'FEFO']))
    
    todo = tasks[mask_pend]
    
    if todo.empty: st.info("Nenhuma tarefa pendente.")
    
    for i, row in todo.iterrows():
        k_init = f"init_{row['id_task']}"
        k_end = f"end_{row['id_task']}"
        
        with st.expander(f"{row['atividade']} ({row['status']})", expanded=True):
            st.write(f"**Local:** {row['area']}")
            st.write(f"**Material:** {row['sku_produto']}")
            st.write(f"**Obs:** {row['descricao']}")
            
            # Se houver foto/vídeo inicial (Conferente), mostra aqui
            if pd.notna(row['evidencia_img']) and row['evidencia_img'] and os.path.exists(row['evidencia_img']):
                 ext = row['evidencia_img'].split('.')[-1].lower()
                 if ext in ['mp4', 'avi', 'mov', 'mkv']:
                     st.video(row['evidencia_img'])
                 else:
                     st.image(row['evidencia_img'], width=100, caption="Ref. Inicial")

            if row['status'] == 'Rejeitada': st.error(f"Motivo: {row['obs_rejeicao']}")
            
            if row['status'] != 'Em Execução':
                if st.button("▶️ INICIAR", key=k_init):
                    # Salva horário Brasil
                    now_br = get_time_br().strftime("%Y-%m-%d %H:%M")
                    update_task_safe(row['id_task'], {'status': 'Em Execução', 'inicio_execucao': now_br})
                    st.rerun()
            else:
                if st.button("⏹️ FINALIZAR", key=k_end):
                    st.session_state['f_id'] = row['id_task']
                    st.rerun()

            if st.session_state.get('f_id') == row['id_task']:
                st.markdown("---")
                st.write("📝 Detalhes da Execução")
                
                # --- CÁLCULO DE TEMPO AUTOMÁTICO PRÉVIO ---
                tempo_estimado = 1
                try:
                    fmt = "%Y-%m-%d %H:%M"
                    if row['inicio_execucao'] and row['inicio_execucao'] != "-":
                        start_time = datetime.strptime(row['inicio_execucao'], fmt)
                        end_time = get_time_br()
                        diff = end_time - start_time
                        tempo_estimado = round(diff.total_seconds() / 60)
                except:
                    tempo_estimado = 1
                
                if tempo_estimado < 1: tempo_estimado = 1

                with st.form(f"form_fim_{row['id_task']}"):
                    # Permite editar o tempo caso o colaborador tenha esquecido de dar Start
                    tempo_real = st.number_input("Tempo Total (minutos)", min_value=1, value=int(tempo_estimado), step=1)
                    
                    qtd = 1.0
                    val_calc = float(row['valor'])
                    lata, pet, ow, ln = 0,0,0,0
                    
                    if row['atividade'] == 'REPACK':
                        c1,c2,c3,c4 = st.columns(4)
                        lata = c1.number_input("Lata", 0)
                        pet = c2.number_input("PET", 0)
                        ow = c3.number_input("OW", 0)
                        ln = c4.number_input("LN", 0)
                        val_calc = (lata*0.10)+(pet*0.15)+(ow*0.20)+(ln*0.20)
                    elif row['atividade'] in ATIVIDADES_POR_CARRO:
                        qtd = st.number_input("Qtd Carros", 1.0)
                        val_calc = float(row['valor']) * qtd
                    elif row['atividade'] not in ATIVIDADES_POR_DIA:
                        qtd = st.number_input("Qtd Paletes", 1.0)
                        val_calc = float(row['valor']) * qtd
                    
                    st.write(f"**Valor Final:** {format_currency(val_calc)}")
                    
                    st.markdown("**📸 Foto Obrigatória para concluir**")
                    foto = st.file_uploader("Foto Evidência Final")
                    
                    if st.form_submit_button("CONCLUIR"):
                        if not foto:
                            st.error("⚠️ Você precisa anexar uma foto para finalizar!")
                        else:
                            nome_safe = st.session_state['user_name'].replace(" ", "_")
                            atv_safe = row['atividade'].replace(" ", "_").replace("/", "-")
                            data_safe = datetime.now().strftime("%Y%m%d_%H%M%S")
                            ext = foto.name.split('.')[-1].lower()
                            
                            filename = f"{nome_safe}_{atv_safe}_{data_safe}.{ext}"
                            pth = f"{IMGS_PATH}/{filename}"
                            
                            with open(pth, "wb") as f: f.write(foto.getbuffer())
                            
                            update_task_safe(row['id_task'], {
                                'status': 'Aguardando Aprovação',
                                'qtd_produzida': qtd,
                                'valor': val_calc,
                                'evidencia_img': pth,
                                'qtd_lata': lata, 'qtd_pet': pet, 'qtd_oneway': ow, 'qtd_longneck': ln,
                                'fim_execucao': get_time_br().strftime("%Y-%m-%d %H:%M"),
                                'tempo_total_min': tempo_real # Usa o tempo que o colaborador confirmou/corrigiu
                            })
                            if 'f_id' in st.session_state: del st.session_state['f_id']
                            st.success("Tarefa entregue!")
                            time.sleep(1)
                            st.rerun()

def interface_colaborador_auto(uid):
    st.title("🙋 Auto-Cadastro")
    rules = get_data("rules")
    users = get_data("users")
    confs = users[users['tipo'].str.contains('CONFERENTE', case=False, na=False)]['nome'].tolist()
    
    ops = users[~users['tipo'].str.lower().str.contains('conferente', na=False)]['nome'].tolist()
    
    colab_sel = st.selectbox("Quem aprova?", confs)
    atv = st.selectbox("Atividade", rules['atividade'].tolist())

    sku_resultado = "-"
    if atv and ("REPACK" not in atv) and ("SELO VERMELHO" not in atv):
        st.markdown("---")
        sku_resultado = buscar_sku_interface_v2()
        st.markdown("---")
    else:
        st.info("SKU não obrigatório.")
        sku_resultado = "N/A"
        
    with st.form("auto_c"):
        loc = st.text_input("Local")
        obs = st.text_area("Obs")
        foto_init = st.file_uploader("Foto Inicial (Opcional)")
        
        if st.form_submit_button("CRIAR TAREFA"):
            if colab_sel and atv:
                try:
                    conf_id = users[users['nome'] == colab_sel].iloc[0]['id_login']
                except:
                    st.error("Conferente inválido")
                    return

                val = 0.0
                val_lookup = rules.loc[rules['atividade'] == atv, 'valor']
                if not val_lookup.empty: val = val_lookup.values[0]

                path_init = ""
                task_id = str(uuid.uuid4())
                
                if foto_init:
                    ext = foto_init.name.split('.')[-1].lower()
                    path_init = f"{IMGS_PATH}/{task_id}_INICIAL.{ext}"
                    with open(path_init, "wb") as f:
                        f.write(foto_init.getbuffer())

                task = {
                    'id_task': task_id,
                    'colaborador_id': str(uid),
                    'conferente_id': str(conf_id),
                    'atividade': atv, 'area': loc, 'descricao': obs,
                    'sku_produto': sku_resultado, 'prioridade': 'Média', 'status': 'Pendente',
                    'valor': float(val), 'data_criacao': get_time_br().strftime("%d/%m %H:%M"),
                    'inicio_execucao': None, 'fim_execucao': None,
                    'tempo_total_min': 0, 'obs_rejeicao': '',
                    'qtd_lata': 0, 'qtd_pet': 0, 'qtd_oneway': 0, 'qtd_longneck': 0,
                    'qtd_produzida': 0, 'evidencia_img': path_init
                }
                add_task_safe(task)
                st.success("Auto-cadastro realizado!")
            else:
                st.error("Preencha os campos obrigatórios.")

# --- ROTEAMENTO ---
if 'user_id' not in st.session_state:
    login_screen()
else:
    r = st.session_state.get('role', 'Colaborador')
    
    if r == 'Supervisor': interface_supervisor()
    elif r == 'Operador': interface_operador()
    elif r == 'Conferente': interface_conferente()
    elif r == 'Colaborador': interface_operador()
    else: 
        st.session_state.clear()
        st.rerun()
