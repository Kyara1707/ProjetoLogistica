import streamlit as st
from github import Github
import json
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="ProTrack Logística", page_icon="🚛", layout="centered")

# --- FUNÇÕES DE CONEXÃO (BLINDADAS) ---
def get_github_connection():
    """Conecta ao GitHub usando os segredos validados."""
    try:
        token = st.secrets["github"]["token"]
        g = Github(token)
        return g
    except Exception as e:
        st.error(f"Erro de Token: {e}")
        return None

def get_repo():
    """Pega o repositório correto."""
    try:
        g = get_github_connection()
        if g:
            repo_name = st.secrets["github"]["repo_name"]
            repo = g.get_repo(repo_name)
            return repo
    except Exception as e:
        st.error(f"Erro ao achar repositório: {e}")
        return None

def load_data_from_github(filename="data.json"):
    """Lê o arquivo JSON do GitHub. Se não existir, cria um vazio."""
    repo = get_repo()
    if not repo:
        return {}
    
    try:
        contents = repo.get_contents(filename)
        decoded = contents.decoded_content.decode("utf-8")
        return json.loads(decoded)
    except:
        # Se der erro (arquivo não existe), retorna dicionário vazio
        return {}

def save_data_to_github(data, filename="data.json", message="Atualização de dados"):
    """Salva os dados no GitHub."""
    repo = get_repo()
    if not repo:
        return False
    
    json_data = json.dumps(data, indent=4)
    
    try:
        # Tenta atualizar arquivo existente
        contents = repo.get_contents(filename)
        repo.update_file(contents.path, message, json_data, contents.sha)
        return True
    except:
        try:
            # Se não existe, cria um novo
            repo.create_file(filename, message, json_data)
            return True
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
            return False

# --- LÓGICA DO APP ---

st.title("ProTrack Logística 🚛")

# Carregar dados
db = load_data_from_github()

# Se for a primeira vez, inicializa estrutura básica
if not db:
    db = {"usuarios": {}, "entregas": []}

menu = st.sidebar.selectbox("Menu", ["Login", "Cadastro (Admin)"])

if menu == "Login":
    st.subheader("Acesso ao Sistema")
    id_input = st.text_input("ID ou Matrícula")
    
    if st.button("Entrar"):
        if id_input in db["usuarios"]:
            usuario = db["usuarios"][id_input]
            st.success(f"Bem-vindo(a), {usuario['nome']}!")
            st.info(f"Cargo: {usuario['cargo']}")
            
            # --- ÁREA LOGADA ---
            st.write("---")
            st.write("### Painel de Entregas")
            if db["entregas"]:
                df = pd.DataFrame(db["entregas"])
                st.dataframe(df)
            else:
                st.warning("Nenhuma entrega registrada.")
                
            # Exemplo de registro de entrega
            with st.expander("Registrar Nova Entrega"):
                destino = st.text_input("Destino")
                status = st.selectbox("Status", ["Pendente", "Em Rota", "Entregue"])
                if st.button("Salvar Entrega"):
                    nova_entrega = {
                        "motorista": usuario['nome'],
                        "destino": destino,
                        "status": status,
                        "data": str(datetime.now())
                    }
                    db["entregas"].append(nova_entrega)
                    if save_data_to_github(db):
                        st.success("Entrega salva no GitHub com sucesso!")
                        st.rerun() # Atualiza a tela
                    
        else:
            st.error("ID não encontrado. Cadastre-se ou contate o administrador.")

elif menu == "Cadastro (Admin)":
    st.subheader("Cadastro de Novo Usuário")
    # Senha simples para evitar cadastro de qualquer um
    senha_admin = st.text_input("Senha de Administrador", type="password")
    
    if senha_admin == "admin123": # Pode mudar depois
        new_id = st.text_input("Novo ID/Matrícula")
        new_nome = st.text_input("Nome")
        new_cargo = st.selectbox("Cargo", ["Motorista", "Gerente", "Logística"])
        
        if st.button("Cadastrar Usuário"):
            if new_id and new_nome:
                db["usuarios"][new_id] = {"nome": new_nome, "cargo": new_cargo}
                
                with st.spinner("Salvando no GitHub..."):
                    sucesso = save_data_to_github(db)
                
                if sucesso:
                    st.success(f"Usuário {new_nome} cadastrado com sucesso!")
                else:
                    st.error("Erro ao salvar no banco de dados.")
            else:
                st.warning("Preencha todos os campos.")
    elif senha_admin:
        st.error("Senha incorreta.")
