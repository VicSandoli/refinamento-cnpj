import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Análise de Impacto de Refatoração",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- ESTILO CSS CUSTOMIZADO (Opcional, para refinar o visual) ---
st.markdown("""
<style>
    /* Melhora a aparência dos containers de métricas */
    .stMetric {
        border-radius: 10px;
        padding: 15px;
        background-color: #262730;
        border: 1px solid #4A4A4A;
    }
    /* Estilo para os títulos das seções */
    h2 {
        border-bottom: 2px solid #4A90E2;
        padding-bottom: 5px;
        color: #FFFFFF;
    }
    /* Estilo para expanders */
    .st-expander {
        border: 1px solid #4A4A4A !important;
        border-radius: 10px !important;
    }
</style>
""", unsafe_allow_html=True)


# --- FUNÇÃO DE CARREGAMENTO DE DADOS (com cache) ---
# O cache do Streamlit garante que os dados só sejam recarregados se os arquivos mudarem.
@st.cache_data
def carregar_dados():
    """Carrega os dados dos três arquivos Excel gerados pelo script de análise."""
    caminhos = {
        "impacto": 'analise_impacto_cnpj_refinada.xlsx',
        "descartes": 'analise_descartes.xlsx',
        "sem_classificacao": 'analise_sem_classificacao.xlsx'
    }
    dados = {}
    erros = {}

    for nome, caminho in caminhos.items():
        if os.path.exists(caminho):
            try:
                dados[nome] = pd.read_excel(caminho)
            except Exception as e:
                erros[nome] = f"Erro ao ler '{caminho}': {e}"
        else:
            erros[nome] = f"Arquivo '{caminho}' não encontrado. Execute o script 'main.py' primeiro."
    
    return dados, erros

# --- TÍTULO PRINCIPAL ---
st.title("📊 Painel de Análise de Impacto - Refatoração de CNPJ")
st.markdown("Visão gerencial dos resultados da análise de código para a migração de CNPJ numérico para alfanumérico.")


# --- CARREGAMENTO E VALIDAÇÃO DOS DADOS ---
dados, erros = carregar_dados()

if erros:
    for nome, msg in erros.items():
        st.error(msg)
    st.warning("Alguns ou todos os relatórios não puderam ser carregados. Os dados exibidos podem estar incompletos.")

# --- DADOS DE IMPACTO (O FOCO PRINCIPAL) ---
df_impacto = dados.get("impacto")
df_descartes = dados.get("descartes")
df_nao_classificados = dados.get("sem_classificacao")

# --- MÉTRICAS GERAIS ---
st.header("Resumo Geral da Análise")

total_impacto = len(df_impacto) if df_impacto is not None else 0
total_descartado = len(df_descartes) if df_descartes is not None else 0
total_sem_class = len(df_nao_classificados) if df_nao_classificados is not None else 0
total_analisado = total_impacto + total_descartado + total_sem_class

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="🔴 Pontos de Impacto", value=f"{total_impacto:,}".replace(",", "."))
with col2:
    st.metric(label="🟢 Itens Descartados", value=f"{total_descartado:,}".replace(",", "."))
with col3:
    st.metric(label="🟡 Sem Classificação", value=f"{total_sem_class:,}".replace(",", "."))
with col4:
    st.metric(label="Total de Linhas Relevantes", value=f"{total_analisado:,}".replace(",", "."))


# --- SEÇÃO DE ANÁLISE VISUAL DO IMPACTO ---
if df_impacto is not None and not df_impacto.empty:
    st.header("Análise Detalhada dos Pontos de Impacto")

    # Gráficos em colunas
    c1, c2 = st.columns(2)

    with c1:
        # Gráfico 1: Impacto por Nível de Risco
        st.subheader("Impacto por Nível de Risco")
        contagem_risco = df_impacto['Nível de Risco'].value_counts().reset_index()
        contagem_risco.columns = ['Nível de Risco', 'Contagem']
        fig_risco = px.bar(
            contagem_risco,
            x='Nível de Risco',
            y='Contagem',
            title="Distribuição de Ocorrências por Risco",
            color='Nível de Risco',
            color_discrete_map={'Alto': '#FF4B4B', 'Médio': '#FFD700', 'Baixo': '#4CAF50'},
            text_auto=True
        )
        fig_risco.update_layout(showlegend=False)
        st.plotly_chart(fig_risco, use_container_width=True)

    with c2:
        # Gráfico 2: Impacto por Classificação de Arquivo
        st.subheader("Impacto por Classificação de Arquivo")
        contagem_classificacao = df_impacto['Classificação'].value_counts().reset_index()
        contagem_classificacao.columns = ['Classificação', 'Contagem']
        fig_classificacao = px.pie(
            contagem_classificacao,
            names='Classificação',
            values='Contagem',
            title="Proporção de Impacto por Tipo de Módulo",
            hole=0.4
        )
        st.plotly_chart(fig_classificacao, use_container_width=True)

    # Gráfico 3: Padrões de Risco Mais Comuns
    st.subheader("Padrões de Risco Mais Frequentes")
    contagem_padrao = df_impacto['Padrão de Risco'].value_counts().nlargest(10).reset_index()
    contagem_padrao.columns = ['Padrão de Risco', 'Contagem']
    fig_padrao = px.bar(
        contagem_padrao,
        y='Padrão de Risco',
        x='Contagem',
        orientation='h',
        title="Top 10 Padrões de Risco Encontrados",
        text_auto=True
    )
    fig_padrao.update_yaxes(categoryorder="total ascending")
    st.plotly_chart(fig_padrao, use_container_width=True)

# --- SEÇÃO DE DETALHAMENTO DOS DADOS (EXPANDERS) ---
st.header("Detalhamento dos Dados")

if df_impacto is not None:
    with st.expander("🔴 Visualizar Dados de Impacto"):
        st.dataframe(df_impacto)

if df_descartes is not None:
    with st.expander("🟢 Visualizar Itens Descartados"):
        st.dataframe(df_descartes)
        
if df_nao_classificados is not None:
    with st.expander("🟡 Visualizar Itens Sem Classificação"):
        st.dataframe(df_nao_classificados) 