import streamlit as st
from github import Github

st.title("🕵️‍♂️ Detetive de Conexão GitHub")

# 1. Verifica se existe a seção [github]
if "github" not in st.secrets:
    st.error("❌ ERRO GRAVE: Não encontrei a seção [github] nos Secrets.")
    st.stop()

token = st.secrets["github"].get("token", "")
repo_name = st.secrets["github"].get("repo_name", "")

# 2. Analisa o Token (Sem mostrar ele todo)
st.write(f"**Repositório alvo:** `{repo_name}`")
if not token:
    st.error("❌ O Token está vazio!")
else:
    # Mostra apenas o início e o fim para conferência
    st.info(f"🔑 **Token lido:** `{token[:4]}...{token[-4:]}` (Tamanho: {len(token)} caracteres)")
    
    if " " in token:
        st.error("🚨 PERIGO: Detectei um ESPAÇO EM BRANCO no meio do seu token! Remova os espaços.")

# 3. Tenta conectar no GitHub (Login Geral)
try:
    g = Github(token)
    user = g.get_user()
    login = user.login
    st.success(f"✅ **Autenticação SUCESSO!** Logado como: **{login}**")
except Exception as e:
    st.error(f"❌ **Falha no Login:** O token está inválido ou vencido.\nErro: {e}")
    st.stop()

# 4. Tenta acessar o Repositório Específico
try:
    repo = g.get_repo(repo_name)
    st.success(f"✅ **Repositório Encontrado:** {repo.full_name}")
    
    # Tenta listar arquivos
    contents = repo.get_contents("")
    st.write("📂 **Arquivos na raiz:**")
    for content_file in contents:
        st.write(f"- {content_file.name}")
        
except Exception as e:
    st.error(f"❌ **Falha ao acessar o Repositório:** Eu loguei, mas não consegui ver o repo `{repo_name}`.")
    st.warning("Dicas:\n1. O nome do repo está exato? (Ex: 'seuUsuario/seuRepo')\n2. O Token tem a caixinha 'repo' marcada?\n3. O repositório existe mesmo?")
