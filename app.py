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



# --- GERENCIAMENTO DE DADOS (CORRIGIDO) ---

def init_data():

    # Cria rules.csv

    if not os.path.exists(f"{FILES_PATH}/rules.csv"):

        df_regras = pd.DataFrame(NOVAS_REGRAS)

        df_regras.to_csv(f"{FILES_PATH}/rules.csv", index=False, sep=';', encoding='utf-8-sig')

    

    # Cria users.csv

    if not os.path.exists(f"{FILES_PATH}/users.csv"):

        pd.DataFrame(columns=['nome', 'id_login', 'tipo', 'rv_acumulada']).to_csv(f"{FILES_PATH}/users.csv", sep=';', index=False, encoding='utf-8-sig')

    

    # Cria tasks.csv

    if not os.path.exists(f"{FILES_PATH}/tasks.csv"):

        cols = ['id_task', 'colaborador_id', 'conferente_id', 'atividade', 'area', 'descricao', 

                'sku_produto', 'prioridade', 'status', 'valor', 'data_criacao', 'inicio_execucao', 

                'fim_execucao', 'tempo_total_min', 'obs_rejeicao', 'qtd_lata', 'qtd_pet', 

                'qtd_oneway', 'qtd_longneck', 'qtd_produzida', 'evidencia_img']

        pd.DataFrame(columns=cols).to_csv(f"{FILES_PATH}/tasks.csv", sep=';', index=False, encoding='utf-8-sig')



    # Cria sku.csv (PARA EVITAR O ERRO DE BUSCA)

    if not os.path.exists(f"{FILES_PATH}/sku.csv"):

        pd.DataFrame(columns=['codigo', 'descricao']).to_csv(f"{FILES_PATH}/sku.csv", sep=';', index=False, encoding='utf-8-sig')



init_data()



def get_data(filename):

    path = f"{FILES_PATH}/{filename}.csv"

    # Se o arquivo não existir mesmo após init, retorna vazio para não quebrar

    if not os.path.exists(path):

        init_data() # Tenta criar de novo

        if not os.path.exists(path): return pd.DataFrame() # Desiste e retorna vazio



    try:

        try:

            df = pd.read_csv(path, sep=';', encoding='utf-8-sig', dtype=str)

        except UnicodeDecodeError:

            df = pd.read_csv(path, sep=';', encoding='latin1', dtype=str)

        

        # Tratamentos específicos

        if filename == 'tasks':

            # Garante que as colunas existam

            required = ['id_task', 'colaborador_id', 'status', 'valor', 'atividade']

            if df.empty or not all(c in df.columns for c in required):

                 # Retorna estrutura vazia se estiver corrompido

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

        # Em caso de erro grave, retorna vazio em vez de tela vermelha

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

                

                # Definição rigorosa de papeis

                if st.session_state['user_id'] in SUPERVISORES_PERMITIDOS: 

                    st.session_state['role'] = 'Supervisor'

                elif 'OPERADOR' in tipo: 

                    st.session_state['role'] = 'Operador'

                elif 'CONFERENTE' in tipo: 

                    st.session_state['role'] = 'Conferente'

                else: 

                    # Qualquer outro (Ajudante, Auxiliar) cai aqui

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

                    

                    cname = users[users['id_login'].astype(str) == str(row['colaborador_id'])]['nome'].value
