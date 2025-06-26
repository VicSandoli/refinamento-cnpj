# 🔐 Dashboard CNPJ Alfanumérico - Versão com Autenticação
# Para uso corporativo com controle de acesso

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# === CONFIGURAÇÃO DE AUTENTICAÇÃO ===
def check_password():
    """Implementa autenticação simples para GPs"""
    
    def password_entered():
        # Senhas por perfil (em produção, usar banco de dados)
        valid_passwords = {
            "gp_admin": "cnpj_admin_2024",
            "gp_visualizacao": "cnpj_view_2024", 
            "demo": "demo_123"
        }
        
        password = st.session_state["password"]
        username = st.session_state.get("username", "").lower()
        
        if username in valid_passwords and password == valid_passwords[username]:
            st.session_state["password_correct"] = True
            st.session_state["user_profile"] = username
            st.session_state["authenticated_at"] = datetime.now()
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    # Interface de login
    if "password_correct" not in st.session_state:
        st.markdown("## 🔐 Acesso Restrito - Dashboard CNPJ Alfanumérico")
        st.markdown("### 👨‍💼 Login para Gerentes de Projeto")
        
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.text_input(
                "👤 Usuário:", 
                key="username",
                placeholder="gp_admin / gp_visualizacao / demo"
            )
            st.text_input(
                "🔒 Senha:", 
                type="password", 
                on_change=password_entered, 
                key="password",
                placeholder="Digite sua senha"
            )
            
            st.markdown("---")
            st.info("""
            **👥 Perfis de Acesso:**
            - `gp_admin`: Acesso completo + downloads
            - `gp_visualizacao`: Apenas visualização
            - `demo`: Demonstração limitada
            """)
        
        return False
        
    elif not st.session_state["password_correct"]:
        st.error("❌ Usuário ou senha incorretos!")
        st.text_input("👤 Usuário:", key="username")
        st.text_input("🔒 Senha:", type="password", on_change=password_entered, key="password")
        return False
    else:
        return True

# === CONTROLE DE SESSÃO ===
def show_session_info():
    """Mostra informações da sessão na sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 👤 Sessão Ativa")
    st.sidebar.success(f"**Usuário:** {st.session_state.get('user_profile', 'N/A')}")
    
    if 'authenticated_at' in st.session_state:
        auth_time = st.session_state['authenticated_at']
        st.sidebar.info(f"**Login:** {auth_time.strftime('%H:%M:%S')}")
    
    if st.sidebar.button("🔓 Logout"):
        for key in ['password_correct', 'user_profile', 'authenticated_at']:
            if key in st.session_state:
                del st.session_state[key]
        st.experimental_rerun()

def check_permission(action="view"):
    """Verifica permissões baseadas no perfil do usuário"""
    user_profile = st.session_state.get('user_profile', '')
    
    permissions = {
        'gp_admin': ['view', 'download', 'export', 'filter'],
        'gp_visualizacao': ['view', 'filter'],
        'demo': ['view']
    }
    
    return action in permissions.get(user_profile, [])

# === INÍCIO DO DASHBOARD ===
st.set_page_config(
    page_title="Dashboard CNPJ Alfanumérico - Corporativo",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Verificar autenticação
if not check_password():
    st.stop()

# Mostrar informações da sessão
show_session_info()

# A partir daqui, o código do dashboard original continua...
# Importar todas as funções do dashboard.py original

# === CARREGAMENTO DE DADOS (mesmo código do dashboard original) ===
@st.cache_data
def carregar_dados():
    """Carrega todos os datasets gerados pela análise"""
    dados = {}
    
    # ... resto do código de carregamento igual ao dashboard.py
    
    return dados

# === INTERFACE PRINCIPAL ===
st.title("📊 Dashboard CNPJ Alfanumérico - Versão Corporativa")

# Verificar permissões para diferentes seções
user_profile = st.session_state.get('user_profile', '')

if user_profile == 'demo':
    st.warning("🎯 **Modo Demonstração** - Funcionalidades limitadas")
elif user_profile == 'gp_visualizacao':
    st.info("👀 **Modo Visualização** - Sem downloads")
else:
    st.success("🔧 **Modo Administrador** - Acesso completo")

# === MENU DE NAVEGAÇÃO ===
st.sidebar.markdown("## 📋 Navegação")

# Ajustar páginas baseado no perfil
paginas_base = [
    "📈 Visão Executiva",
    "💰 Precificação Detalhada", 
    "🎯 Análise por Categoria",
    "🏗️ Análise por Módulo",
    "⚠️ Pontos Críticos"
]

if check_permission("filter"):
    paginas_base.append("🔍 Explorador Interativo")

if check_permission("view"):
    paginas_base.append("📋 Dados Brutos")

pagina = st.sidebar.selectbox("Selecione a página:", paginas_base)

# === CARREGAMENTO E VALIDAÇÃO DE DADOS ===
dados = carregar_dados()

if not dados:
    st.error("❌ **Erro:** Nenhum dado encontrado!")
    st.markdown("""
    ### 🔧 Para resolver este problema:
    1. Execute primeiro: `python main.py`
    2. Aguarde a geração dos arquivos Excel
    3. Recarregue esta página
    """)
    st.stop()

# === CONTEÚDO DAS PÁGINAS ===
# Aqui você copiaria todo o código das páginas do dashboard.py original
# Mas com verificações de permissão onde necessário

# Exemplo para downloads:
if st.button("📥 Download") and check_permission("download"):
    # Código de download
    pass
elif st.button("📥 Download") and not check_permission("download"):
    st.error("❌ Permissão negada para download")

# === RODAPÉ CORPORATIVO ===
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("📊 **Dashboard CNPJ Alfanumérico**")
    st.markdown("Versão Corporativa com Controle de Acesso")

with col2:
    st.markdown("🏢 **Acesso Corporativo**")
    st.markdown(f"Usuário: {user_profile}")

with col3:
    st.markdown("🔐 **Segurança**")
    st.markdown("Sessão autenticada e monitorada")

# Log de acesso (opcional)
if 'access_logged' not in st.session_state:
    # Aqui você poderia implementar log em arquivo ou banco
    # print(f"Acesso: {user_profile} em {datetime.now()}")
    st.session_state['access_logged'] = True 