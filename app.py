import streamlit as st
import pandas as pd
import os
from datetime import datetime
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
LIMITE_RV_OPERADOR = 380.00  # <--- NOVO LIMITE CONFIGURADO AQUI

# Tabela de preços fixa para garantir funcionamento se CSV falhar
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

# --- GERENCIAMENTO DE DADOS (CORRIGIDO PARA EVITAR KEYERROR) ---
def init_data():
    # Garante que rules existe
    if not os.path.exists(f"{FILES_PATH}/rules.csv"):
        df_regras = pd.DataFrame(NOVAS_REGRAS)
        df_regras.to_csv(f"{FILES_PATH}/rules.csv", index=False, sep=';', encoding='latin1')
    
    # Garante que users existe
    if not os.path.exists(f"{FILES_PATH}/users.csv"):
        pd.DataFrame(columns=['nome', 'id_login', 'tipo', 'rv_acumulada']).to_csv(f"{FILES_PATH}/users.csv", sep=';', index=False)
    
    # Garante que tasks existe
    if not os.path.exists(f"{FILES_PATH}/tasks.csv"):
        cols = ['id_task', 'colaborador_id', 'conferente_id', 'atividade', 'area', 'descricao', 
                'sku_produto', 'prioridade', 'status', 'valor', 'data_criacao', 'inicio_execucao', 
                'fim_execucao', 'tempo_total_min', 'obs_rejeicao', 'qtd_lata', 'qtd_pet', 
                'qtd_oneway', 'qtd_longneck', 'qtd_produzida', 'evidencia_img']
        pd.DataFrame(columns=cols).to_csv(f"{FILES_PATH}/tasks.csv", sep=';', index=False)

init_data()

def get_data(filename):
    path = f"{FILES_PATH}/{filename}.csv"
    if not os.path.exists(path):
        init_data() # Tenta recriar se não existir
        
    try:
        df = pd.read_csv(path, sep=';', encoding='latin1', dtype=str)
        
        # CORREÇÃO CRÍTICA: Se o arquivo existir mas estiver vazio ou sem colunas
        if filename == 'tasks':
            required_cols = ['id_task', 'colaborador_id', 'status', 'valor', 'atividade']
            if df.empty or not all(col in df.columns for col in required_cols):
                 cols = ['id_task', 'colaborador_id', 'conferente_id', 'atividade', 'area', 'descricao', 
                        'sku_produto', 'prioridade', 'status', 'valor', 'data_criacao', 'inicio_execucao', 
                        'fim_execucao', 'tempo_total_min', 'obs_rejeicao', 'qtd_lata', 'qtd_pet', 
                        'qtd_oneway', 'qtd_longneck', 'qtd_produzida', 'evidencia_img']
                 return pd.DataFrame(columns=cols)
            
            # Conversão de tipos para evitar erros matemáticos
            df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
            df['tempo_total_min'] = pd.to_numeric(df['tempo_total_min'], errors='coerce').fillna(0.0)
            
        elif filename == 'users':
            if 'rv_acumulada' not in df.columns:
                df['rv_acumulada'] = 0.0
            df['rv_acumulada'] = pd.to_numeric(df['rv_acumulada'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
            
        elif filename == 'rules':
            df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
            
        return df
    except Exception as e:
        st.error(f"Erro ao ler {filename}: {e}")
        return pd.DataFrame()

def save_data(df, filename):
    try: df.to_csv(f"{FILES_PATH}/{filename}.csv", index=False, sep=';', encoding='latin1')
    except: st.error(f"Erro ao salvar. Feche o arquivo {filename}.csv se estiver aberto!")

def add_task_safe(task_dict):
    df = get_data("tasks")
    new_row = pd.DataFrame([task_dict])
    df = pd.concat([df, new_row], ignore_index=True)
    save_data(df, "tasks")

def update_task_safe(task_id, updates):
    df = get_data("tasks")
    if df.empty: return
    # Garante comparação string x string
    idx = df[df['id_task'].astype(str) == str(task_id)].index
    if not idx.empty:
        for col, val in updates.items():
            df.at[idx[0], col] = val
        save_data(df, "tasks")

def update_rv_safe(user_id, amount):
    df = get_data("users")
    # Limpa espaços em branco nos IDs
    idx = df[df['id_login'].astype(str).str.strip() == str(user_id).strip()].index
    if not idx.empty:
        atual = float(df.at[idx[0], 'rv_acumulada'])
        df.at[idx[0], 'rv_acumulada'] = atual + float(amount)
        save_data(df, "users")
        return True
    return False

def buscar_sku_interface():
    df_sku = get_data("sku") # Requer arquivo sku.csv na pasta data se quiser usar
    codigo = st.text_input("Digite o Código do Produto:")
    nome = "-"
    if codigo and not df_sku.empty:
        try:
            # Tenta encontrar código na coluna (ajuste o nome da coluna conforme seu CSV)
            col_cod = df_sku.columns[0] # Assume primeira coluna como código
            col_nome = df_sku.columns[1] # Assume segunda como nome
            res = df_sku[df_sku[col_cod].astype(str).str.strip() == codigo.strip()]
            if not res.empty: nome = res.iloc[0][col_nome]
            else: nome = "❌ Não encontrado"
        except: pass
    st.text_input("Material", value=nome, disabled=True)
    return f"{codigo} - {nome}" if nome != "-" else "-"

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
                
                if st.session_state['user_id'] in SUPERVISORES_PERMITIDOS: st.session_state['role'] = 'Supervisor'
                elif 'OPERADOR' in tipo: st.session_state['role'] = 'Operador'
                elif 'CONFERENTE' in tipo: st.session_state['role'] = 'Conferente'
                else: st.session_state['role'] = 'Colaborador'
                st.rerun()
            else: st.error("Usuário não cadastrado.")

def interface_supervisor():
    st.sidebar.header(f"👮 {st.session_state['user_name']}")
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
                    # Chaves ÚNICAS para evitar DuplicateWidgetID
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
                            
                            if val == 0: # Era NOK, virou OK
                                try: novo_valor = float(rules.loc[rules['atividade'] == row['atividade'], 'valor'].values[0])
                                except: novo_valor = 0.0
                                obs = "Supervisor alterou para OK"

                            if update_rv_safe(row['colaborador_id'], novo_valor):
                                update_task_safe(row['id_task'], {'status': novo_status, 'valor': novo_valor, 'obs_rejeicao': obs})
                                st.rerun()
                        st.divider()

    elif menu == "Ajustes Financeiros":
        st.title("💰 Ajuste de Saldo (Crédito/Débito)")
        st.info("Utilize para pagar bônus ou realizar descontos manuais.")
        
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
                            'data_criacao': datetime.now().strftime("%d/%m %H:%M"),
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
    st.sidebar.header(f"👷 {st.session_state['user_name']}")
    menu = st.sidebar.radio("Menu", ["🚀 KPIs Diários", "Tarefas", "Auto-Cadastro", "Dashboard", "Sair"])
    uid = st.session_state['user_id']
    
    if menu == "Sair": 
        st.session_state.clear()
        st.rerun()

    if menu == "🚀 KPIs Diários":
        st.title("🚀 Metas do Dia")
        rules = get_data("rules")
        
        # Recupera valores das regras
        def get_val(name):
            try: return float(rules[rules['atividade']==name]['valor'].values[0])
            except: return 0.0
            
        v_efc = get_val('EFC')
        v_tma = get_val('TMA')
        v_fefo = get_val('FEFO')
        
        hoje = datetime.now().strftime("%d/%m")
        tasks = get_data("tasks")
        
        # Verifica se já enviou hoje
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
                            'data_criacao': datetime.now().strftime("%d/%m %H:%M"),
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
        
        # --- LÓGICA DO TETO ---
        saldo_exibido = min(saldo_real, LIMITE_RV_OPERADOR)
        # ---------------------
        
        tasks = get_data("tasks")
        if not tasks.empty:
            minhas = tasks[(tasks['colaborador_id'].astype(str) == uid) & (tasks['status'] == 'Executada')]
            total_tarefas = len(minhas)
            soma_kpis = minhas[minhas['atividade'].isin(['EFC', 'TMA', 'FEFO'])]['valor'].sum()
            soma_prod = minhas[~minhas['atividade'].isin(['EFC', 'TMA', 'FEFO'])]['valor'].sum()
        else:
            total_tarefas, soma_kpis, soma_prod = 0, 0.0, 0.0

        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Saldo Total (RV)", format_currency(saldo_exibido))
        c2.metric("📦 Tarefas Executadas", total_tarefas)
        c3.metric("🎯 Ganho com KPIs", format_currency(soma_kpis))

        if saldo_real > LIMITE_RV_OPERADOR:
            st.warning(f"🔒 Teto de RV atingido! Seu acumulado real é {format_currency(saldo_real)}, mas o pagamento é limitado a {format_currency(LIMITE_RV_OPERADOR)}.")

        st.subheader("Histórico Recente")
        if not tasks.empty:
            hist = tasks[(tasks['colaborador_id'].astype(str) == uid)].sort_values('data_criacao', ascending=False).head(10)
            st.dataframe(hist[['data_criacao', 'atividade', 'status', 'valor']], use_container_width=True)

def interface_conferente():
    st.sidebar.header(f"👤 {st.session_state['user_name']}")
    menu = st.sidebar.radio("Menu", ["Criar Tarefa", "Aprovar Tarefas", "Sair"])
    users = get_data("users")
    tasks = get_data("tasks")
    rules = get_data("rules")

    if menu == "Sair":
        st.session_state.clear()
        st.rerun()

    elif menu == "Criar Tarefa":
        st.title("📋 Nova Atividade")
        sku_resultado = buscar_sku_interface()

        with st.form("task_form"):
            ops = users[~users['tipo'].str.lower().str.contains('conferente', na=False)]['nome'].tolist()
            atvs = rules['atividade'].tolist() if not rules.empty else []
            
            colab = st.selectbox("Colaborador", ops)
            atv = st.selectbox("Atividade", atvs)
            area = st.text_input("Local")
            obs = st.text_area("Obs")
            prio = st.select_slider("Prioridade", ["Baixa", "Média", "Alta"])
            
            if st.form_submit_button("Enviar"):
                if colab and atv:
                    cid = users[users['nome'] == colab].iloc[0]['id_login']
                    val = 0.0
                    if not rules.empty:
                        val_lookup = rules.loc[rules['atividade'] == atv, 'valor']
                        if not val_lookup.empty: val = val_lookup.values[0]

                    task = {
                        'id_task': str(uuid.uuid4()),
                        'colaborador_id': str(cid), 
                        'conferente_id': st.session_state['user_id'],
                        'atividade': atv, 'area': area, 'descricao': obs, 
                        'sku_produto': sku_resultado, 'prioridade': prio, 'status': 'Pendente',
                        'valor': float(val), 'data_criacao': datetime.now().strftime("%d/%m %H:%M"),
                        'inicio_execucao': None, 'fim_execucao': None, 
                        'tempo_total_min': 0, 'obs_rejeicao': '',
                        'qtd_lata': 0, 'qtd_pet': 0, 'qtd_oneway': 0, 'qtd_longneck': 0, 
                        'qtd_produzida': 0, 'evidencia_img': ''
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
                # CHAVES ÚNICAS
                k_approve = f"ok_{row['id_task']}_{i}"
                k_reject_exp = f"rej_exp_{row['id_task']}_{i}"
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
                            try: c2.image(row['evidencia_img'], width=150)
                            except: pass
                    
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

    # Filtro Seguro
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
            if row['status'] == 'Rejeitada': st.error(f"Motivo: {row['obs_rejeicao']}")
            
            if row['status'] != 'Em Execução':
                if st.button("▶️ INICIAR", key=k_init):
                    update_task_safe(row['id_task'], {'status': 'Em Execução', 'inicio_execucao': datetime.now().strftime("%Y-%m-%d %H:%M")})
                    st.rerun()
            else:
                if st.button("⏹️ FINALIZAR", key=k_end):
                    st.session_state['f_id'] = row['id_task']
                    st.rerun()

            # Formulário de Finalização
            if st.session_state.get('f_id') == row['id_task']:
                st.markdown("---")
                st.write("📝 Detalhes da Execução")
                with st.form(f"form_fim_{row['id_task']}"):
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
                        qtd = st.number_input("Qtd Paletes/Unid", 1.0)
                        val_calc = float(row['valor']) * qtd
                    
                    st.write(f"**Valor Final:** {format_currency(val_calc)}")
                    foto = st.file_uploader("Foto Evidência")
                    
                    if st.form_submit_button("CONCLUIR"):
                        pth = ""
                        if foto:
                            pth = f"images/{row['id_task']}_{foto.name}"
                            with open(pth, "wb") as f: f.write(foto.getbuffer())
                            
                        update_task_safe(row['id_task'], {
                            'status': 'Aguardando Aprovação',
                            'qtd_produzida': qtd,
                            'valor': val_calc,
                            'evidencia_img': pth,
                            'qtd_lata': lata, 'qtd_pet': pet, 'qtd_oneway': ow, 'qtd_longneck': ln,
                            'fim_execucao': datetime.now().strftime("%Y-%m-%d %H:%M"),
                            'tempo_total_min': 10 
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
    
    with st.form("auto_c"):
        conf = st.selectbox("Quem aprova?", confs)
        atv = st.selectbox("Atividade", rules['atividade'].tolist())
        loc = st.text_input("Local")
        sku = buscar_sku_interface()
        
        if st.form_submit_button("CADASTRAR"):
            if conf and atv:
                cid = users[users['nome']==conf].iloc[0]['id_login']
                val = rules.loc[rules['atividade']==atv, 'valor'].values[0]
                task = {
                    'id_task': str(uuid.uuid4()),
                    'colaborador_id': uid, 'conferente_id': str(cid),
                    'atividade': atv, 'area': loc, 'descricao': 'Auto-lancamento',
                    'sku_produto': sku, 'prioridade': 'Média', 'status': 'Pendente',
                    'valor': float(val), 'data_criacao': datetime.now().strftime("%d/%m %H:%M"),
                    'inicio_execucao': "-", 'fim_execucao': "-", 'tempo_total_min': 0, 'obs_rejeicao': "", 
                    'qtd_lata': 0, 'qtd_pet': 0, 'qtd_oneway': 0, 'qtd_longneck': 0, 
                    'qtd_produzida': 0, 'evidencia_img': ""
                }
                add_task_safe(task)
                st.success("Criado!")
            else: st.error("Preencha tudo")

# --- ROTEAMENTO ---
if 'user_id' not in st.session_state:
    login_screen()
else:
    r = st.session_state.get('role')
    if r == 'Supervisor': interface_supervisor()
    elif r == 'Operador': interface_operador()
    elif r == 'Conferente': interface_conferente()
    else: st.warning("Perfil não identificado")
