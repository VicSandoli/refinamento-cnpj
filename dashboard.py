import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import re
import subprocess
import threading
import sys

# Configuração da página
st.set_page_config(
    page_title="Dashboard - Análise CNPJ Alfanumérico",
    page_icon="📊",
    layout="wide"
)

# Título principal
st.title("📊 Dashboard - Análise de Impacto CNPJ Alfanumérico")
st.markdown("### Visão Estratégica para Precificação da Proposta")

# --- CONTROLE DE EXECUÇÃO NA SIDEBAR ---
st.sidebar.title("⚙️ Controles")

if st.sidebar.button("Executar Nova Análise", type="primary"):
    st.session_state.run_analysis = True
    st.session_state.analysis_output = ""
    st.session_state.analysis_done = False

if 'run_analysis' in st.session_state and st.session_state.run_analysis:
    st.sidebar.info("Análise em andamento...")
    output_placeholder = st.sidebar.empty()
    
    # Usando st.spinner para uma melhor UX
    with st.spinner('Executando main.py... Por favor, aguarde.'):
        try:
            # Garante que o processo filho use UTF-8 para I/O, resolvendo problemas de encoding no Windows.
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'UTF-8'

            # Comando para executar o script. '-u' para unbuffered output.
            # Usar sys.executable garante que o subprocesso use o mesmo ambiente Python que o Streamlit.
            process = subprocess.Popen(
                [sys.executable, '-u', 'main.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',
                text=True,
                env=env
            )

            log_output = ""
            for line in iter(process.stdout.readline, ''):
                log_output += line
                output_placeholder.code(log_output, language='log')
            
            process.stdout.close()
            return_code = process.wait()

            if return_code == 0:
                st.session_state.analysis_output = log_output + "\n\n✅ Análise concluída com sucesso!"
                st.toast("Análise finalizada! Os dados foram atualizados.", icon="🎉")
            else:
                st.session_state.analysis_output = log_output + f"\n\n❌ ERRO: A análise falhou com código de saída {return_code}."
                st.toast("Ocorreu um erro durante a análise.", icon="🔥")

        except Exception as e:
            st.session_state.analysis_output = f"❌ FALHA CRÍTICA ao executar o script: {e}"
            st.toast("Falha crítica ao tentar executar o script.", icon="🚨")

    st.session_state.run_analysis = False
    st.session_state.analysis_done = True
    st.cache_data.clear() # Limpa o cache para forçar o recarregamento dos dados
    st.rerun() # Força o rerun do script do dashboard

if 'analysis_done' in st.session_state and st.session_state.analysis_done:
    st.sidebar.code(st.session_state.analysis_output, language='log')
    if st.sidebar.button("Limpar Log"):
        st.session_state.analysis_done = False
        st.session_state.analysis_output = ""
        st.rerun()

# Configuração de arquivos
ARQUIVO_AJUSTES = 'analise_ajustes_criticos.xlsx'
ARQUIVO_PRECIFICACAO = 'analise_precificacao_proposta.xlsx'
ARQUIVO_DESCARTES = 'analise_descartes.xlsx'
ARQUIVO_NAO_CLASSIFICADOS = 'analise_sem_classificacao.xlsx'

# Mapeamento de categorias para cores (atualizado)
CORES_FRENTES = {
    'Análise e Planejamento': '#4682B4',
    'Desenvolvimento': '#FF8C00',
    'Refatoração': '#32CD32',
    'Testes e Implantação': '#FF4B4B',
    'Outros': '#9370DB'
}

# Função para carregar dados
@st.cache_data
def carregar_dados():
    dados = {}
    
    # Carregar dados de ajustes (pontos críticos)
    if os.path.exists(ARQUIVO_AJUSTES):
        dados['ajustes'] = pd.read_excel(ARQUIVO_AJUSTES)
    
    # Carregar dados de precificação
    if os.path.exists(ARQUIVO_PRECIFICACAO):
        dados['precificacao'] = {}
        try:
            xls = pd.ExcelFile(ARQUIVO_PRECIFICACAO)
            sheet_map = {
                'sumario': '1_Summary_Executivo',
                'detalhes': '2_Estimativa_Detalhada',
                'pontos': '3_Detalhe_Pontos_Oficiais' # Mantido para consistência
            }
            for key, sheet_name in sheet_map.items():
                if sheet_name in xls.sheet_names:
                    dados['precificacao'][key] = pd.read_excel(ARQUIVO_PRECIFICACAO, sheet_name=sheet_name)
        except Exception as e:
            st.error(f"Erro ao carregar precificação: {e}")
    
    # Carregar outros dados
    for nome, arquivo in [('descartes', ARQUIVO_DESCARTES), ('nao_classificados', ARQUIVO_NAO_CLASSIFICADOS)]:
        if os.path.exists(arquivo):
            try:
                dados[nome] = pd.read_excel(arquivo)
            except Exception as e:
                st.warning(f"Erro ao carregar {nome}: {e}")
    
    return dados

# Carregar dados
dados = carregar_dados()

# Sidebar para navegação
st.sidebar.title("🔍 Navegação")
pagina = st.sidebar.radio(
    "Escolha a visualização:",
    [
        "📈 Visão Executiva", 
        "💰 Precificação Detalhada",
        "🏗️ Análise por Prefixo/Grupo",
        "🔍 Explorador de Pontos Críticos"
    ]
)

# === PÁGINA: VISÃO EXECUTIVA ===
if pagina == "📈 Visão Executiva":
    
    if 'precificacao' in dados and 'sumario' in dados['precificacao']:
        summary = dados['precificacao']['sumario']
        
        st.markdown("## 🎯 Resumo Executivo - Abordagem Realista")
        
        # Extrair métricas do summary
        metrics = {}
        for _, row in summary.iterrows():
            metrics[row['Métrica']] = row['Valor']
        
        # Garantir que todos os valores de métricas sejam strings para evitar erro de tipo
        for k, v in metrics.items():
            metrics[k] = str(v)
        
        # Métricas principais em colunas
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Esforço Total", 
                metrics.get('Total Estimado', 'N/A'),
                help="Soma de todas as frentes: Desenvolvimento + Testes QA"
            )
            
        with col2:
            st.metric(
                "Com Buffer 20%", 
                metrics.get('Estimativa com Buffer 20%', 'N/A'),
                help="Margem para imprevistos e atividades não planejadas"
            )

        with col3:
            st.metric(
                "Desenvolvimento", 
                metrics.get('Esforço Desenvolvimento', 'N/A'),
                help="Codificação, arquitetura e atividades de desenvolvimento"
            )
            
        with col4:
            st.metric(
                "Testes QA", 
                metrics.get('Esforço Testes QA', 'N/A'),
                help="Testes unitários, integração, regressão e homologação"
            )
            
        with col5:
            st.metric(
                "Rotinas Impactadas",
                str(metrics.get('Rotinas Oficiais Impactadas', 'N/A')),
                help="Número de programas/rotinas oficiais únicos que sofrerão alterações."
            )

        # Gráfico de distribuição por frente de trabalho
        if 'detalhes' in dados['precificacao']:
            st.markdown("## 📊 Distribuição de Esforço por Frente de Trabalho")
            
            df_cat = dados['precificacao']['detalhes'].copy()

            # Fix para erro de tipo: garantir que colunas potencialmente mistas sejam string
            if 'Pontos Identificados' in df_cat.columns:
                df_cat['Pontos Identificados'] = df_cat['Pontos Identificados'].astype(str)
            
            # Gráfico de barras horizontais
            fig_bar = px.bar(
                df_cat, 
                x='Total (h)', 
                y='Frente de Trabalho',
                title="Esforço por Frente de Trabalho (Dev + Testes)",
                orientation='h',
                text='Total (h)',
                color='Tipo',
                color_discrete_map={
                    'Atividade Base': '#4682B4',
                    'Ajuste de Código': '#FF8C00'
                }
            )
            fig_bar.update_traces(texttemplate='%{text}h', textposition='outside')
            fig_bar.update_layout(height=500, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # Tabela com detalhes
            st.markdown("### 📋 Detalhamento por Frente")
            df_display = df_cat[['Frente de Trabalho', 'Tipo', 'Esforço Dev (h)', 'Esforço Testes (h)', 'Total (h)', 'Observação']].copy()
            st.dataframe(df_display, use_container_width=True)

            # Texto para escopo da proposta
            st.markdown("## 📝 Texto Sugerido para Proposta (Escopo)")
            escopo_proposta = """
O escopo desta proposta contempla o projeto completo de adequação do sistema ao novo padrão de CNPJ alfanumérico, compreendendo as seguintes frentes de trabalho:

1.  **Análise e Planejamento:** Levantamento de todos os pontos de impacto no código-fonte, planejamento de atividades, definição de arquitetura e coordenação do projeto.
2.  **Desenvolvimento da Solução Central:** Criação de funções e componentes centralizados para validar, formatar, armazenar e calcular o dígito verificador (DV) do novo CNPJ alfanumérico.
3.  **Refatoração do Código-Fonte:** Substituição de todas as manipulações de CNPJ (validações, formatações, lógicas de negócio) por chamadas à nova solução central. Inclui a análise e ajuste de sub-rotinas e queries de banco de dados impactadas.
4.  **Ajustes de Infraestrutura e Integrações:** Migração do padrão de código de barras da DANFE para o formato CODE-128A.
5.  **Testes e Homologação:** Ciclo completo de testes, incluindo testes unitários, testes integrados e suporte à homologação pelo cliente (UAT) para garantir a conformidade e a ausência de regressões.
6.  **Pós-Implantação:** Operação assistida para acompanhamento em produção e resolução de ajustes remanescentes.

**Fora do Escopo:**
*   Quaisquer alterações de funcionalidade não relacionadas diretamente à adequação do CNPJ.
*   Migração de dados históricos (a ser avaliada em projeto específico, se necessário).
"""
            st.text_area("Edite e copie o texto abaixo:", escopo_proposta, height=400)
    
    else:
        st.warning("⚠️ Dados de precificação não encontrados. Execute primeiro o script main.py.")

# === PÁGINA: PRECIFICAÇÃO DETALHADA ===
elif pagina == "💰 Precificação Detalhada":
    
    if 'precificacao' in dados and 'detalhes' in dados['precificacao']:
        st.markdown("## 💰 Análise Detalhada por Frente de Trabalho")
        
        df_detalhes = dados['precificacao']['detalhes']
        
        # Gráfico comparativo Dev vs Testes
        st.markdown("### Esforço: Desenvolvimento vs. Testes")
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(
            name='Desenvolvimento',
            x=df_detalhes['Frente de Trabalho'],
            y=df_detalhes['Esforço Dev (h)'],
            marker_color='#4682B4',
            text=df_detalhes['Esforço Dev (h)'],
            textposition='inside'
        ))
        fig_comp.add_trace(go.Bar(
            name='Testes QA',
            x=df_detalhes['Frente de Trabalho'],
            y=df_detalhes['Esforço Testes (h)'],
            marker_color='#FF4B4B',
            text=df_detalhes['Esforço Testes (h)'],
            textposition='inside'
        ))
        
        fig_comp.update_layout(
            title_text="Distribuição de Esforço: Desenvolvimento vs. Testes",
            barmode='stack',
            height=600,
            xaxis={'categoryorder':'total descending'},
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_comp, use_container_width=True)
        
        # Cards expandíveis com detalhes
        st.markdown("### 🎯 Detalhamento das Frentes")
        for _, row in df_detalhes.iterrows():
            with st.expander(f"**{row['Frente de Trabalho']}** - {row['Total (h)']}h"):
                st.markdown(f"*{row['Observação']}*")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total", f"{row['Total (h)']}h")
                with col2:
                    st.metric("Desenvolvimento", f"{row['Esforço Dev (h)']}h")
                with col3:
                    st.metric("Testes QA", f"{row['Esforço Testes (h)']}h")

    else:
        st.warning("⚠️ Dados de precificação não encontrados. Execute o script principal primeiro.")

# === PÁGINA: ANÁLISE POR MÓDULO ===
elif pagina == "🏗️ Análise por Prefixo/Grupo":
    
    if 'ajustes' in dados:
        st.markdown("## 🏗️ Análise de Impacto por Prefixo/Grupo de Programas")
        df_ajustes = dados['ajustes']
        
        # Contagem de pontos por módulo (prefixo do arquivo)
        df_modulos = df_ajustes['Prefixo'].value_counts().reset_index()
        df_modulos.columns = ['Prefixo/Grupo', 'Pontos Críticos']
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.metric("Total de Grupos Impactados", df_modulos['Prefixo/Grupo'].nunique())
            st.markdown("#### Top 10 Grupos Críticos")
            st.dataframe(df_modulos.head(10), use_container_width=True)

        with col2:
            st.markdown("#### Distribuição de Pontos Críticos por Grupo")
            fig = px.bar(
                df_modulos.head(20).sort_values(by='Pontos Críticos', ascending=True),
                x='Pontos Críticos',
                y='Prefixo/Grupo',
                orientation='h',
                title='Top 20 Grupos com Mais Pontos de Ajuste'
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
            
    else:
        st.warning("⚠️ Dados de ajustes críticos não encontrados. Execute o script principal e recarregue a página.")

# === PÁGINA: EXPLORADOR DE PONTOS CRÍTICOS ===
elif pagina == "🔍 Explorador de Pontos Críticos":

    if 'ajustes' in dados:
        st.markdown("## 🔍 Explorador Interativo de Pontos Críticos")
        df_ajustes = dados['ajustes'].copy()
        
        # Filtros
        st.sidebar.header("Filtros do Explorador")
        
        # Filtro por Módulo (Prefixo)
        modulos_unicos = sorted(df_ajustes['Prefixo'].unique())
        modulos_selecionados = st.sidebar.multiselect("Prefixo/Grupo", modulos_unicos, default=modulos_unicos[:5])
        
        # Filtro por Arquivo
        arquivos_unicos = sorted(df_ajustes[df_ajustes['Prefixo'].isin(modulos_selecionados)]['Arquivo'].unique())
        arquivo_selecionado = st.sidebar.multiselect("Arquivo Específico", arquivos_unicos)

        # Aplicar filtros
        if modulos_selecionados:
            df_filtrado = df_ajustes[df_ajustes['Prefixo'].isin(modulos_selecionados)]
            if arquivo_selecionado:
                df_filtrado = df_filtrado[df_filtrado['Arquivo'].isin(arquivo_selecionado)]
        else:
            df_filtrado = df_ajustes

        # Função para destacar variáveis no código
        def destacar_variaveis(row):
            codigo = str(row['Código'])
            variaveis = str(row['Variável']).split(', ')
            for var in variaveis:
                # Usar re.escape para tratar caracteres especiais nas variáveis
                codigo = re.sub(f'({re.escape(var)})', r'**:red[\\1]**', codigo, flags=re.IGNORECASE)
            return codigo

        # Aplicar o destaque
        if not df_filtrado.empty:
            # Criar uma cópia explícita aqui para evitar o SettingWithCopyWarning
            df_filtrado = df_filtrado.copy()
            df_filtrado.loc[:, 'Código'] = df_filtrado.apply(destacar_variaveis, axis=1)
        
        st.dataframe(df_filtrado, use_container_width=True)
        st.info(f"Exibindo {len(df_filtrado)} de {len(df_ajustes)} pontos críticos.")

    else:
        st.warning("⚠️ Dados de ajustes críticos não encontrados. Execute o script principal e recarregue a página.")

# Rodapé
st.markdown("---")
st.markdown("📊 **Dashboard de Análise CNPJ Alfanumérico** | Desenvolvido para suporte à precificação da proposta")

# Instruções de uso na sidebar
st.sidebar.markdown("---")
st.sidebar.title("📖 Como usar")
st.sidebar.markdown("""
1.  **Clique em 'Executar Nova Análise'** para gerar os dados mais recentes a partir do código-fonte.
2.  **Aguarde a execução terminar.** O log aparecerá na barra lateral.
3.  **Navegue pelas abas** para explorar os resultados.
4.  **Use os filtros no Explorador** para análises detalhadas.
""")

# Informações técnicas na sidebar
if 'ajustes' in dados:
    st.sidebar.markdown("### 📈 Estatísticas:")
    df = dados['ajustes']
    st.sidebar.metric("Total de Pontos", len(df))
    if 'Estimativa (Horas)' in df.columns:
        st.sidebar.metric("Total Estimado", f"{df['Estimativa (Horas)'].sum():.1f}h")
    st.sidebar.metric("Arquivos Únicos", df['Arquivo'].nunique()) 