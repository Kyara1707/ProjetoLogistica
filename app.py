import streamlit as st
import pandas as pd
import os
from datetime import datetime
import time

# --- LISTAS DE CATEGORIAS ---
ATIVIDADES_POR_CARRO = [
    "AMARRAÇÃO", 
    "DESCARREGAMENTO DE VAN"
]

ATIVIDADES_POR_DIA = [
    "MÁQUINA LIMPEZA", 
    "5S MARIA MOLE", 
    "5S PICKING/ABASTECIMENTO"
]

# --- LISTA DE SUPERVISORES ---
SUPERVISORES_PERMITIDOS = ['99849441', '99813623', '99797465']

# --- CONFIGURAÇÃO DE PREÇOS DO REPACK ---
PRECOS_REPACK = {
    'Lata': 0.10,
    'PET': 0.15,
    'OneWay': 0.20,
    'LongNeck': 0.20
}

# --- REGRAS ATUALIZADAS (Conforme sua lista) ---
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
    # --- NOVOS KPIS ---
    {"atividade": "EFC", "valor": 3.85},
    {"atividade": "TMA", "valor": 7.70},
    {"atividade": "FEFO", "valor": 3.85}
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
    # Atualiza o arquivo rules.csv com a lista correta
    try:
        df_regras = pd.DataFrame(NOVAS_REGRAS)
        df_regras.to_csv(f"{FILES_PATH}/rules.csv", index=False, sep=';', encoding='latin1')
    except PermissionError:
        pass 

    if not os.path.exists(f"{FILES_PATH}/users.csv"):
        # Cria users.csv se não existir
        pd.DataFrame(columns=['nome', 'id_login', 'tipo', 'rv_acumulada']).to_csv(f"{FILES_PATH}/users.csv", sep=';', index=False)

init_data()

# --- LEITURA DE DADOS ---
def get_data(filename):
    path = f"{FILES_PATH}/{filename}.csv"
    if not os.path.exists(path):
        if filename == 'tasks':
             cols = ['id_task', 'colaborador_id', 'conferente_id', 'atividade', 'area', 'descricao', 'sku_produto', 'prioridade', 'status', 'valor', 'data_criacao', 'inicio_execucao', 'fim_execucao', 'tempo_total_min', 'obs_rejeicao', 'qtd_lata', 'qtd_pet', 'qtd_oneway', 'qtd_longneck', 'qtd_produzida', 'evidencia_img']
             return pd.DataFrame(columns=cols)
        return pd.DataFrame()

    try:
        df = pd.read_csv(path, sep=';', encoding='latin1', dtype=str)
        if len(df.columns) == 1:
             df = pd.read_csv(path, sep=None, engine='python', encoding='latin1', dtype=str)

        if filename != 'sku':
            df.columns = df.columns.str.strip().str.lower()

        if filename == 'rules':
            if 'valor' in df.columns:
                df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
            # Normalizar nomes das atividades para garantir match
            if 'atividade' in df.columns:
                df['atividade'] = df['atividade'].astype(str).str.strip()

        elif filename == 'users':
            if 'nome' not in df.columns:
                df = pd.read_csv(path, sep=';', encoding='latin1', header=None, dtype=str)
                if len(df.columns) >= 3:
                    df.columns = ['nome', 'id_login', 'tipo'] + list(df.columns[3:])
                if not df.empty and str(df.iloc[0,0]).lower() == 'nome': df = df[1:]
            
            if 'id_login' in df.columns: 
                df['id_login'] = df['id_login'].astype(str).str.strip()
            
            if 'rv_acumulada' in df.columns:
                df['rv_acumulada'] = df['rv_acumulada'].astype(str).str.replace(',', '.')
                df['rv_acumulada'] = pd.to_numeric(df['rv_acumulada'], errors='coerce').fillna(0.0)
            else:
                df['rv_acumulada'] = 0.0

        elif filename == 'tasks':
            if 'colaborador_id' in df.columns: 
                df['colaborador_id'] = df['colaborador_id'].astype(str).str.strip()
            if 'valor' in df.columns:
                 df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
            if 'tempo_total_min' in df.columns:
                 df['tempo_total_min'] = pd.to_numeric(df['tempo_total_min'], errors='coerce').fillna(0.0)
            if 'qtd_produzida' in df.columns:
                 df['qtd_produzida'] = pd.to_numeric(df['qtd_produzida'], errors='coerce').fillna(0.0)

        elif filename == 'sku':
            df = df.dropna(how='all')
            df.columns = df.columns.str.strip()

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

def update_rv_safe(user_id, amount):
    df = get_data("users")
    user_id = str(user_id).strip()
    df['id_login'] = df['id_login'].astype(str).str.strip()
    idx = df[df['id_login'] == user_id].index
    if not idx.empty:
        atual = df.at[idx[0], 'rv_acumulada']
        novo_saldo = float(atual) + float(amount)
        df.at[idx[0], 'rv_acumulada'] = novo_saldo
        save_data(df, "users")
        return True
    return False

def buscar_sku_interface():
    df_sku = get_data("sku")
    codigo_input = st.text_input("Digite o Código do Produto:")
    material_encontrado = ""
    if codigo_input and not df_sku.empty:
        try:
            resultado = df_sku[df_sku['Código Promax'].astype(str).str.strip() == codigo_input.strip()]
            if not resultado.empty:
                material_encontrado = resultado.iloc[0]['Material']
            else:
                material_encontrado = "❌ PRODUTO NÃO ENCONTRADO"
        except:
            material_encontrado = "⚠️ Erro na leitura do arquivo SKU"
    st.text_input("Material (Busca Automática)", value=material_encontrado, disabled=True)
    if material_encontrado and "❌" not in material_encontrado:
        return f"{codigo_input} - {material_encontrado}"
    return "-"

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
                st.error("Erro users.csv. Verifique se existe.")
                return
            
            user = users[users['id_login'] == login_id]
            if not user.empty:
                st.session_state['user_id'] = str(user.iloc[0]['id_login'])
                st.session_state['user_name'] = user.iloc[0]['nome']
                
                # Normaliza o tipo para evitar erro de caixa alta/baixa
                tipo_user = str(user.iloc[0]['tipo']).strip().upper()

                if str(user.iloc[0]['id_login']) in SUPERVISORES_PERMITIDOS:
                    st.session_state['user_role'] = 'Supervisor'
                elif 'OPERADOR' in tipo_user:
                    st.session_state['user_role'] = 'Operador'
                elif 'CONFERENTE' in tipo_user:
                    st.session_state['user_role'] = 'Conferente'
                else:
                    st.session_state['user_role'] = 'Colaborador'
                
                st.rerun()
            else:
                st.error("Usuário não encontrado.")

# --- SUPERVISOR ---
def interface_supervisor():
    st.sidebar.header(f"👮 {st.session_state['user_name']}")
    st.sidebar.badge("Supervisor")
    menu = st.sidebar.radio("Menu", ["Validar KPIs", "Lançar Bônus", "Ranking", "Sair"])
    users = get_data("users")
    rules = get_data("rules")

    if menu == "Sair":
        st.session_state.clear()
        st.rerun()

    elif menu == "Validar KPIs":
        st.title("🛡️ Validação de KPIs (Operadores)")
        tasks = get_data("tasks")
        
        # Filtra tarefas de KPI (EFC, TMA, FEFO) que estão esperando validação
        if not tasks.empty:
            kpi_names = ["EFC", "TMA", "FEFO"]
            kpi_tasks = tasks[
                (tasks['status'] == 'Aguardando Validação') & 
                (tasks['atividade'].isin(kpi_names))
            ]

            if kpi_tasks.empty:
                st.info("Nenhum KPI pendente de validação hoje.")
            else:
                for i, row in kpi_tasks.iterrows():
                    colab_nome = users[users['id_login'] == str(row['colaborador_id'])]['nome'].values
                    nome_show = colab_nome[0] if len(colab_nome) > 0 else row['colaborador_id']
                    
                    with st.container():
                        st.markdown(f"**{nome_show}** - {row['atividade']}")
                        st.caption(f"Data: {row['data_criacao']}")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        valor_declarado = float(row['valor'])
                        status_declarado = "OK" if valor_declarado > 0 else "NOK"
                        cor_status = "green" if valor_declarado > 0 else "red"

                        col1.markdown(f"Operador declarou: **:{cor_status}[{status_declarado}]**")
                        col1.write(f"Valor: {format_currency(valor_declarado)}")

                        if col2.button("✅ Confirmar", key=f"kpi_ok_{row['id_task']}"):
                            if update_rv_safe(row['colaborador_id'], valor_declarado):
                                update_task_safe(row['id_task'], {'status': 'Executada'})
                                st.success("Confirmado!")
                                time.sleep(0.5)
                                st.rerun()

                        if col3.button("✏️ Alterar/Corrigir", key=f"kpi_nok_{row['id_task']}"):
                            # Logica de inversão
                            if valor_declarado > 0:
                                # Era OK, vira NOK (0 reais)
                                update_task_safe(row['id_task'], {'status': 'Não Atingido', 'valor': 0.0, 'obs_rejeicao': 'Supervisor alterou para NOK'})
                                st.warning("Alterado para NOK (R$ 0,00).")
                            else:
                                # Era NOK, vira OK. Busca valor na tabela de regras
                                val_cheio = 0.0
                                if not rules.empty:
                                    try:
                                        val_cheio = rules.loc[rules['atividade'] == row['atividade'], 'valor'].values[0]
                                    except: pass
                                
                                if update_rv_safe(row['colaborador_id'], val_cheio):
                                    update_task_safe(row['id_task'], {'status': 'Executada', 'valor': val_cheio, 'obs_rejeicao': 'Supervisor alterou para OK'})
                                    st.success(f"Alterado para OK ({format_currency(val_cheio)}).")
                            
                            time.sleep(1)
                            st.rerun()
                        st.divider()
        else:
            st.info("Sem dados.")

    elif menu == "Lançar Bônus":
        # ... (Mantém igual)
        st.title("💰 Lançar Bônus / Extra")
        st.markdown("---")
        with st.form("bonus_form"):
            ops = users[~users['id_login'].isin(SUPERVISORES_PERMITIDOS)]['nome'].tolist()
            colab_bonus = st.selectbox("Colaborador", ops)
            valor_bonus = st.number_input("Valor (R$)", min_value=0.0, step=1.0)
            motivo_bonus = st.text_input("Motivo")
            
            if st.form_submit_button("CONFIRMAR"):
                if valor_bonus > 0 and motivo_bonus:
                    cid = users[users['nome'] == colab_bonus].iloc[0]['id_login']
                    if update_rv_safe(cid, valor_bonus):
                        task_log = {
                            'id_task': int(time.time()), 'colaborador_id': str(cid), 'conferente_id': st.session_state['user_id'],
                            'atividade': "BÔNUS SUPERVISOR", 'area': "ADM", 'descricao': motivo_bonus, 'sku_produto': "-", 'prioridade': 'Alta',
                            'status': 'Executada', 'valor': float(valor_bonus), 'data_criacao': datetime.now().strftime("%d/%m %H:%M"),
                            'inicio_execucao': "-", 'fim_execucao': "-", 'tempo_total_min': 0, 'obs_rejeicao': "",
                            'qtd_lata': 0, 'qtd_pet': 0, 'qtd_oneway': 0, 'qtd_longneck': 0, 'evidencia_img': ""
                        }
                        add_task_safe(task_log)
                        st.success(f"Adicionado {format_currency(valor_bonus)} para {colab_bonus}.")
                    else: st.error("Erro.")
                else: st.warning("Preencha tudo.")

    elif menu == "Ranking":
        st.title("🏆 Ranking Geral")
        st.dataframe(users[['nome', 'rv_acumulada']].sort_values('rv_acumulada', ascending=False), use_container_width=True)

# --- CONFERENTE ---
def interface_conferente():
    # ... (Mantém a lógica do conferente original)
    st.sidebar.header(f"👤 {st.session_state['user_name']}")
    st.sidebar.badge("Conferente")
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
                try:
                    cid = users[users['nome'] == colab].iloc[0]['id_login']
                    val = 0.0
                    if not rules.empty:
                        val = rules.loc[rules['atividade'] == atv, 'valor'].values[0]

                    task = {
                        'id_task': int(time.time()), 'colaborador_id': str(cid), 'conferente_id': st.session_state['user_id'],
                        'atividade': atv, 'area': area, 'descricao': obs, 
                        'sku_produto': sku_resultado, 
                        'prioridade': prio, 'status': 'Pendente',
                        'valor': float(val), 'data_criacao': datetime.now().strftime("%d/%m %H:%M"),
                        'inicio_execucao': None, 'fim_execucao': None, 'tempo_total_min': 0, 'obs_rejeicao': '',
                        'qtd_lata': 0, 'qtd_pet': 0, 'qtd_oneway': 0, 'qtd_longneck': 0, 'qtd_produzida': 0, 'evidencia_img': ''
                    }
                    add_task_safe(task)
                    st.success(f"Criada! SKU: {sku_resultado}")
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
                    
                    sku_info = row['sku_produto'] if 'sku_produto' in row and pd.notna(row['sku_produto']) else "-"
                    st.caption(f"📦 Material: {sku_info}")

                    c1, c2 = st.columns(2)
                    c1.write(f"⏱️ {row['tempo_total_min']}m")
                    
                    if row['atividade'] in ['REPACK', 'Repack']:
                        c1.info(f"🥫L:{row['qtd_lata']} 🍾P:{row['qtd_pet']} 🧊OW:{row['qtd_oneway']} 🍺LN:{row['qtd_longneck']}")
                    elif row['atividade'] in ATIVIDADES_POR_CARRO:
                        c1.info(f"🚛 {row['qtd_produzida']} Carro(s)")
                    elif row['atividade'] in ATIVIDADES_POR_DIA:
                        c1.info(f"📅 1 Diária") 
                    else:
                        c1.info(f"📦 {row['qtd_produzida']} Palete(s)")
                    
                    c1.metric("A Pagar", format_currency(row['valor']))
                    
                    if pd.notna(row['evidencia_img']) and row['evidencia_img']:
                        if os.path.exists(row['evidencia_img']):
                            try: c2.image(row['evidencia_img'], width=150)
                            except: pass
                    
                    b1, b2 = st.columns(2)
                    if b1.button("✅ Aprovar", key=f"ok{row['id_task']}"):
                        if update_rv_safe(row['colaborador_id'], row['valor']):
                            update_task_safe(row['id_task'], {'status': 'Executada'})
                            st.success("Pago!")
                            time.sleep(0.5)
                            st.rerun()
                    
                    with b2:
                        with st.expander("❌ Rejeitar"):
                            motivo = st.text_input("Motivo:", key=f"rs{row['id_task']}")
                            if st.button("Confirmar", key=f"cr{row['id_task']}"):
                                update_task_safe(row['id_task'], {'status': 'Rejeitada', 'obs_rejeicao': motivo})
                                st.rerun()
                    st.divider()
        else: st.info("Sem tarefas.")

# --- OPERADOR (PERFIL CORRIGIDO) ---
def interface_operador():
    st.sidebar.header(f"👷 {st.session_state['user_name']}")
    st.sidebar.badge("Operador")
    menu = st.sidebar.radio("Menu", ["🚀 KPIs Diários", "Tarefas", "Auto-Cadastro", "Dashboard", "Sair"])
    my_id = str(st.session_state['user_id'])
    
    if menu == "Sair":
        st.session_state.clear()
        st.rerun()
        
    elif menu == "KPIs Diários":
        st.title("🚀 Metas Diárias (KPIs)")
        st.markdown("Valide suas metas do dia.")
        
        # Buscar valores reais do CSV rules
        rules = get_data("rules")
        val_efc = 0.0
        val_tma = 0.0
        val_fefo = 0.0
        
        if not rules.empty:
            try: val_efc = float(rules.loc[rules['atividade'] == 'EFC', 'valor'].values[0])
            except: pass
            try: val_tma = float(rules.loc[rules['atividade'] == 'TMA', 'valor'].values[0])
            except: pass
            try: val_fefo = float(rules.loc[rules['atividade'] == 'FEFO', 'valor'].values[0])
            except: pass
        
        tasks = get_data("tasks")
        hoje_str = datetime.now().strftime("%d/%m")
        
        # Filtra tarefas deste usuário, com data de hoje e que sejam KPIs
        ja_lancou = False
        kpi_names = ["EFC", "TMA", "FEFO"]
        
        if not tasks.empty:
            kpis_hoje = tasks[
                (tasks['colaborador_id'] == my_id) & 
                (tasks['data_criacao'].str.contains(hoje_str)) &
                (tasks['atividade'].isin(kpi_names))
            ]
            if not kpis_hoje.empty:
                ja_lancou = True
                st.info("✅ Você já enviou seus KPIs de hoje. Aguarde validação do supervisor.")
                st.dataframe(kpis_hoje[['atividade', 'status', 'valor']])
        
        if not ja_lancou:
            with st.form("form_kpi"):
                st.write("Marque 'OK' se a meta foi batida.")
                
                check_efc = st.checkbox(f"EFC ({format_currency(val_efc)})")
                check_tma = st.checkbox(f"TMA ({format_currency(val_tma)})")
                check_fefo = st.checkbox(f"FEFO ({format_currency(val_fefo)})")
                
                if st.form_submit_button("ENVIAR KPIs"):
                    kpi_list = [
                        ("EFC", check_efc, val_efc),
                        ("TMA", check_tma, val_tma),
                        ("FEFO", check_fefo, val_fefo)
                    ]
                    
                    for nome_kpi, bateu_meta, valor_kpi in kpi_list:
                        val_final = valor_kpi if bateu_meta else 0.0
                        task = {
                            'id_task': int(time.time()) + int(valor_kpi*100), 
                            'colaborador_id': my_id, 
                            'conferente_id': 'SISTEMA',
                            'atividade': nome_kpi, 
                            'area': 'OPERAÇÃO', 
                            'descricao': f"Auto-avaliação: {'OK' if bateu_meta else 'NOK'}", 
                            'sku_produto': "-",
                            'prioridade': 'Alta',
                            'status': 'Aguardando Validação', 
                            'valor': float(val_final), 
                            'data_criacao': datetime.now().strftime("%d/%m %H:%M"),
                            'inicio_execucao': "-", 'fim_execucao': "-", 
                            'tempo_total_min': 0, 'obs_rejeicao': "",
                            'qtd_lata': 0, 'qtd_pet': 0, 'qtd_oneway': 0, 'qtd_longneck': 0, 'evidencia_img': ""
                        }
                        add_task_safe(task)
                        time.sleep(0.1)
                        
                    st.success("KPIs enviados para o supervisor!")
                    st.rerun()

    elif menu == "Tarefas":
        interface_colaborador_tarefas(my_id)
    elif menu == "Auto-Cadastro":
        interface_colaborador_auto(my_id)
    elif menu == "Dashboard":
        interface_colaborador_dash(my_id)

# --- REUTILIZAVEIS ---
def interface_colaborador_dash(my_id):
    users = get_data("users")
    tasks = get_data("tasks")
    st.title("📊 Dashboard")
    
    user_row = users[users['id_login'] == my_id]
    if not user_row.empty:
        udata = user_row.iloc[0]
        hrs = 0
        if not tasks.empty:
            done = tasks[(tasks['colaborador_id'] == my_id) & (tasks['status'] == 'Executada')]
            hrs = pd.to_numeric(done['tempo_total_min'], errors='coerce').sum() / 60
        
        c1, c2 = st.columns(2)
        c1.metric("RV (R$)", format_currency(udata['rv_acumulada']))
        c2.metric("Horas", f"{hrs:.1f}")
    else:
        st.error("Erro ao carregar dados.")

def interface_colaborador_tarefas(my_id):
    tasks = get_data("tasks")
    st.title("🗂️ Tarefas")
    t1, t2 = st.tabs(["A Fazer", "Feitas"])
    with t1:
        if not tasks.empty:
            # Filtra KPIs para nao aparecer aqui
            kpis = ["EFC", "TMA", "FEFO"]
            todo = tasks[(tasks['colaborador_id'] == my_id) & (tasks['status'].isin(['Pendente', 'Rejeitada', 'Em Execução'])) & (~tasks['atividade'].isin(kpis))]
            if todo.empty: st.info("Nada pendente.")
            for i, row in todo.iterrows():
                with st.expander(f"{row['atividade']} ({row['status']})", expanded=True):
                    st.write(f"Local: {row['area']}")
                    sku_show = row['sku_produto'] if 'sku_produto' in row and pd.notna(row['sku_produto']) else "-"
                    st.write(f"📦 **Material:** {sku_show}")
                    st.write(f"Obs: {row['descricao']}")

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
                            
                            if row['atividade'] in ['REPACK', 'Repack']:
                                st.subheader("Produção Repack")
                                c1,c2,c3,c4 = st.columns(4)
                                lata = c1.number_input("Lata", 0)
                                pet = c2.number_input("PET", 0)
                                ow = c3.number_input("OneWay", 0)
                                ln = c4.number_input("LongNeck", 0)
                                valor_final = (lata*PRECOS_REPACK['Lata']) + (pet*PRECOS_REPACK['PET']) + (ow*PRECOS_REPACK['OneWay']) + (ln*PRECOS_REPACK['LongNeck'])
                            
                            elif row['atividade'] in ATIVIDADES_POR_CARRO:
                                st.info(f"Valor por Carro: {format_currency(valor_base)}")
                                qtd_prod = st.number_input("Qtd Carros:", min_value=1.0, value=1.0, step=1.0)
                                valor_final = valor_base * qtd_prod
                            
                            elif row['atividade'] in ATIVIDADES_POR_DIA:
                                st.info(f"Valor da Diária: {format_currency(valor_base)}")
                                st.success("✅ Registrando 1 diária.")
                                qtd_prod = 1.0
                                valor_final = valor_base
                            
                            else:
                                st.info(f"Valor por Palete: {format_currency(valor_base)}")
                                qtd_prod = st.number_input("Qtd Paletes:", min_value=1.0, value=1.0, step=1.0)
                                valor_final = valor_base * qtd_prod
                            
                            st.write(f"Total: {format_currency(valor_final)}")
                            foto = st.file_uploader("Foto")
                            if st.form_submit_button("Enviar"):
                                pth = f"images/{row['id_task']}_{foto.name}" if foto else ""
                                if foto:
                                    with open(pth, "wb") as f: f.write(foto.getbuffer())
                                
                                update_task_safe(row['id_task'], {
                                    'status': 'Aguardando Aprovação', 'tempo_total_min': st.session_state['fdur'],
                                    'evidencia_img': pth, 'qtd_lata': lata, 'qtd_pet': pet, 'qtd_oneway': ow, 'qtd_longneck': ln,
                                    'qtd_produzida': qtd_prod, 'valor': valor_final
                                })
                                del st.session_state['fid']
                                st.success("Enviado!")
                                st.rerun()
    with t2:
        tasks = get_data("tasks")
        if not tasks.empty:
            done = tasks[(tasks['colaborador_id'] == my_id) & (tasks['status'] == 'Executada')]
            st.dataframe(done[['atividade', 'valor', 'data_criacao']])

def interface_colaborador_auto(my_id):
    users = get_data("users")
    rules = get_data("rules")
    st.title("🙋 Auto-Cadastro")
    
    sku_resultado = buscar_sku_interface()

    confs = users[users['tipo'].str.lower().str.contains('conferente', na=False)]['nome'].tolist()
    
    with st.form("auto"):
        quem = st.selectbox("Aprovador", confs)
        atvs = rules['atividade'].tolist() if not rules.empty else []
        oq = st.selectbox("Atividade", atvs)
        loc = st.text_input("Local")
        obs_user = st.text_area("Obs")
        
        if st.form_submit_button("Cadastrar"):
            cid = users[users['nome'] == quem].iloc[0]['id_login']
            val = rules.loc[rules['atividade'] == oq, 'valor'].values[0] if not rules.empty else 0.0
            desc_final = obs_user if obs_user else "Auto"
            task = {
                'id_task': int(time.time()), 'colaborador_id': my_id, 'conferente_id': str(cid),
                'atividade': oq, 'area': loc, 'descricao': desc_final, 
                'sku_produto': sku_resultado,
                'prioridade': 'Média',
                'status': 'Pendente', 'valor': float(val), 'data_criacao': datetime.now().strftime("%d/%m %H:%M"),
                'inicio_execucao': "", 'fim_execucao': "", 'tempo_total_min': 0, 'obs_rejeicao': "",
                'qtd_lata': 0, 'qtd_pet': 0, 'qtd_oneway': 0, 'qtd_longneck': 0, 'evidencia_img': ""
            }
            add_task_safe(task)
            st.success("Salvo!")

def interface_colaborador():
    st.sidebar.header(f"👷 {st.session_state['user_name']}")
    st.sidebar.badge("Colaborador")
    menu = st.sidebar.radio("Menu", ["Dashboard", "Tarefas", "Auto-Cadastro", "Regras", "Sair"])
    my_id = str(st.session_state['user_id'])

    if menu == "Sair":
        st.session_state.clear()
        st.rerun()
    elif menu == "Dashboard":
        interface_colaborador_dash(my_id)
    elif menu == "Tarefas":
        interface_colaborador_tarefas(my_id)
    elif menu == "Auto-Cadastro":
        interface_colaborador_auto(my_id)
    elif menu == "Regras":
        rules = get_data("rules")
        if not rules.empty:
            rules['fmt'] = rules['valor'].apply(format_currency)
            st.table(rules[['atividade', 'fmt']])

# --- RUN ---
if 'user_id' not in st.session_state:
    login_screen()
else:
    if st.session_state['user_role'] == 'Supervisor':
        interface_supervisor()
    elif st.session_state['user_role'] == 'Conferente':
        interface_conferente()
    elif st.session_state['user_role'] == 'Operador':
        interface_operador()
    else:
        interface_colaborador()
