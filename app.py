import streamlit as st
from github import Github

st.title("Teste de Conexão GitHub")

try:
    # 1. Pega os segredos
    token = st.secrets["github"]["token"]
    repo_name = st.secrets["github"]["repo_name"]
    
    st.write(f"Tentando conectar em: `{repo_name}`")
    st.write(f"Usando token que começa com: `{token[:6]}...`")

    # 2. Tenta logar
    g = Github(token)
    user = g.get_user().login
    st.success(f"✅ Login SUCESSO! Você é: {user}")

    # 3. Tenta acessar o repo
    repo = g.get_repo(repo_name)
    st.success(f"✅ Repositório ENCONTRADO! Descrição: {repo.description}")

except Exception as e:
    st.error(f"❌ FALHA: {e}")
