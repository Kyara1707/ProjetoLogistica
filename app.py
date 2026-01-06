import streamlit as st
import sys

st.title("🕵️‍♂️ Diagnóstico de Secrets")

# 1. Verifica se a seção [github] existe
if "github" not in st.secrets:
    st.error("❌ ERRO: O sistema não encontrou a seção '[github]'. Verifique se você escreveu '[github]' no topo da caixa de Secrets.")
    st.stop()

# 2. Lê as credenciais
token = st.secrets["github"].get("token", "")
repo_name = st.secrets["github"].get("repo_name", "")

st.write("---")
st.subheader("🔍 O que o App está lendo:")

# 3. Analisa o TOKEN (sem revelar o segredo todo)
if token:
    st.info(f"🔑 **Token Lido:** `{token}`") # Mostra o token para você conferir se é o novo
    st.write(f"📏 **Tamanho:** {len(token)} caracteres")
    
    if " " in token:
        st.error("🚨 **ALERTA:** Existem ESPAÇOS EM BRANCO no seu token! Apague os espaços na caixa de Secrets.")
    elif len(token) < 30:
        st.error("🚨 **ALERTA:** O token parece curto demais. Um token do GitHub geralmente é bem longo.")
    else:
        st.success("✅ O formato do token parece correto (sem espaços).")
else:
    st.error("❌ O Token está VAZIO. O app não leu nada.")

# 4. Analisa o NOME DO REPO
st.info(f"📂 **Repo Alvo:** `{repo_name}`")

st.write("---")
st.warning("⚠️ **ATENÇÃO:** Após verificar se este é o token correto, APAGUE este código e restaure seu sistema. Não deixe seu token exposto na tela por muito tempo.")
