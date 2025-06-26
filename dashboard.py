import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# Configuração da página
st.set_page_config(
    page_title="Dashboard - Análise CNPJ Alfanumérico",
    page_icon="📊",
    layout="wide"
)

# Título principal
st.title("📊 Dashboard - Análise de Impacto CNPJ Alfanumérico")
st.markdown("### Visão Estratégica para Precificação da Proposta")

# Configuração de arquivos
ARQUIVO_IMPACTO = 'analise_impacto_cnpj_refinada.xlsx'
ARQUIVO_PRECIFICACAO = 'analise_precificacao_proposta.xlsx'
ARQUIVO_DESCARTES = 'analise_descartes.xlsx'
ARQUIVO_NAO_CLASSIFICADOS = 'analise_sem_classificacao.xlsx'

# Mapeamento de categorias para cores (atualizado)
CORES_CATEGORIAS = {
    'VALIDACAO_ENTRADA': '#FF4B4B',
    'FORMATACAO_EXIBICAO': '#32CD32',
    'LOGICA_NEGOCIO': '#FF8C00',
    'INTEGRACAO_EXTERNA': '#9370DB',
    'ESTRUTURA_DADOS': '#4682B4'
}

# Função para carregar dados
@st.cache_data
def carregar_dados():
    dados = {}
    
    # Carregar dados de impacto
    if os.path.exists(ARQUIVO_IMPACTO):
        dados['impacto'] = pd.read_excel(ARQUIVO_IMPACTO)
    
    # Carregar dados de precificação
    if os.path.exists(ARQUIVO_PRECIFICACAO):
        dados['precificacao'] = {}
        try:
            xls = pd.ExcelFile(ARQUIVO_PRECIFICACAO)
            for sheet in xls.sheet_names:
                dados['precificacao'][sheet] = pd.read_excel(ARQUIVO_PRECIFICACAO, sheet_name=sheet)
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
pagina = st.sidebar.selectbox(
    "Escolha a visualização:",
    [
        "📈 Visão Executiva", 
        "💰 Precificação Detalhada",
        "🎯 Análise por Categoria RF", 
        "🏗️ Análise por Módulo",
        "⚠️ Pontos Críticos",
        "🔍 Explorador Interativo",
        "📋 Dados Brutos"
    ]
)

# === PÁGINA: VISÃO EXECUTIVA ===
if pagina == "📈 Visão Executiva":
    
    if 'precificacao' in dados and '1_Summary_Executivo' in dados['precificacao']:
        summary = dados['precificacao']['1_Summary_Executivo']
        
        st.markdown("## 🎯 Resumo Executivo - Abordagem Realista")
        
        # Extrair métricas do summary
        metrics = {}
        for _, row in summary.iterrows():
            metrics[row['Métrica']] = row['Valor']
        
        # Métricas principais em colunas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Esforço Total", 
                metrics.get('Total Estimado', 'N/A'),
                help="Desenvolvimento + Testes QA"
            )
            
        with col2:
            st.metric(
                "Desenvolvimento", 
                metrics.get('Esforço Desenvolvimento', 'N/A'),
                help="Codificação + adaptações pontuais"
            )
            
        with col3:
            st.metric(
                "Testes QA", 
                metrics.get('Esforço Testes QA', 'N/A'),
                help="Testes unitários + integração + regressão"
            )
            
        with col4:
            st.metric(
                "Com Buffer 20%", 
                metrics.get('Estimativa com Buffer 20%', 'N/A'),
                help="Margem para imprevistos"
            )
        
        # Destacar a abordagem realista
        st.success("""
        🎯 **Estimativa Realista Considerando:**
        - ✅ Solução centralizada (funções de validação/formatação)
        - ✅ Apenas rotinas oficiais
        - ✅ Esforço por categoria de ajuste (não por ponto)
        - ✅ Premissa de reutilização máxima
        """)
        
        # Gráfico de distribuição por categoria de ajuste
        if '2_Por_Categoria_Ajuste' in dados['precificacao']:
            st.markdown("## 📊 Distribuição de Esforço por Categoria de Ajuste")
            
            df_cat = dados['precificacao']['2_Por_Categoria_Ajuste']
            
            # Gráfico de barras horizontais
            fig_bar = px.bar(
                df_cat, 
                x='Total (h)', 
                y='Categoria',
                title="Esforço por Categoria de Ajuste (Dev + Testes)",
                orientation='h',
                text='Total (h)'
            )
            fig_bar.update_traces(texttemplate='%{text}h', textposition='outside')
            fig_bar.update_layout(height=500)
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # Tabela com detalhes
            st.markdown("### 📋 Detalhamento por Categoria")
            df_display = df_cat[['Categoria', 'Pontos Identificados', 'Esforço Dev (h)', 'Esforço Testes (h)', 'Total (h)', 'Observação']].copy()
            st.dataframe(df_display, use_container_width=True)
    
    else:
        st.warning("⚠️ Dados de precificação não encontrados. Execute primeiro o script main.py.")

# === PÁGINA: PRECIFICAÇÃO DETALHADA ===
elif pagina == "💰 Precificação Detalhada":
    
    if 'precificacao' in dados:
        st.markdown("## 💰 Análise Detalhada para Precificação")
        
        # Summary por categoria de ajuste
        if '2_Por_Categoria_Ajuste' in dados['precificacao']:
            df_cat = dados['precificacao']['2_Por_Categoria_Ajuste']
            
            st.markdown("### 🔧 Estratégia de Implementação")
            
            # Gráfico comparativo Dev vs Testes
            fig_comp = go.Figure()
            fig_comp.add_trace(go.Bar(
                name='Desenvolvimento',
                x=df_cat['Categoria'],
                y=df_cat['Esforço Dev (h)'],
                marker_color='lightblue'
            ))
            fig_comp.add_trace(go.Bar(
                name='Testes QA',
                x=df_cat['Categoria'],
                y=df_cat['Esforço Testes (h)'],
                marker_color='lightcoral'
            ))
            
            fig_comp.update_layout(
                title="Distribuição de Esforço: Desenvolvimento vs Testes",
                barmode='stack',
                height=500
            )
            st.plotly_chart(fig_comp, use_container_width=True)
            
            # Cards expandíveis por categoria
            st.markdown("### 🎯 Detalhamento por Categoria")
            for _, row in df_cat.iterrows():
                with st.expander(f"📋 {row['Categoria']} - {row['Total (h)']}h"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        pontos_str = str(row['Pontos Identificados']) if pd.notna(row['Pontos Identificados']) else 'Base'
                        st.metric("Pontos", pontos_str)
                    with col2:
                        st.metric("Dev", f"{row['Esforço Dev (h)']}h")
                    with col3:
                        st.metric("Testes", f"{row['Esforço Testes (h)']}h")
                    
                    st.markdown(f"**Estratégia:** {row['Observação']}")
                    st.markdown(f"**Descrição:** {row['Descrição']}")
        
        # Summary por módulo oficial
        if '3_Por_Modulo_Oficiais' in dados['precificacao']:
            st.markdown("### 🏗️ Distribuição por Módulo (Apenas Oficiais)")
            df_mod = dados['precificacao']['3_Por_Modulo_Oficiais']
            
            # Gráfico de pizza dos top módulos
            top_modulos = df_mod.nlargest(10, 'Pontos Totais')
            
            fig_pizza = px.pie(
                top_modulos,
                values='Pontos Totais',
                names='Prefixo Módulo',
                title="Top 10 Módulos por Quantidade de Pontos"
            )
            st.plotly_chart(fig_pizza, use_container_width=True)
            
            # Tabela detalhada
            st.dataframe(df_mod, use_container_width=True)
    
    else:
        st.warning("⚠️ Dados de precificação não encontrados.")

# === PÁGINA: ANÁLISE POR CATEGORIA ===
elif pagina == "🎯 Análise por Categoria RF":
    
    if 'impacto' in dados:
        df = dados['impacto']
        
        st.markdown("## 🎯 Análise por Categoria de Ajuste")
        
        # Adicionar classificação
        df['Classificação'] = df['Arquivo'].apply(lambda x: 'Oficiais' if any(x.lower().startswith(p) for p in [
            'dd', 'gap', 'i', 'audit', 'autobasi', 'basico', 'br', 'cbpi', 'csp',
            'estoque', 'faturamento', 'fiscal', 'frete', 'gem', 'ipi', 'ipp',
            'mnemonic', 'precos', 'sistema', 'supervisao', 'tropical', 'tti'
        ]) else 'Scripts' if x.lower().startswith('aba') else 'Não Oficiais')
        
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            categorias_selecionadas = st.multiselect(
                "Filtrar Categorias:",
                df['Categoria'].unique() if 'Categoria' in df.columns else [],
                default=df['Categoria'].unique() if 'Categoria' in df.columns else []
            )
        
        with col2:
            classificacoes_selecionadas = st.multiselect(
                "Filtrar Classificação:",
                df['Classificação'].unique(),
                default=['Oficiais']  # Foco em oficiais por padrão
            )
        
        # Aplicar filtros
        if 'Categoria' in df.columns and categorias_selecionadas:
            df_filtrado = df[
                (df['Categoria'].isin(categorias_selecionadas)) &
                (df['Classificação'].isin(classificacoes_selecionadas))
            ]
            
            if not df_filtrado.empty:
                # Distribuição por categoria
                st.markdown("### 📊 Distribuição de Pontos")
                
                cat_counts = df_filtrado['Categoria'].value_counts()
                fig_cat = px.bar(
                    x=cat_counts.index,
                    y=cat_counts.values,
                    title="Quantidade de Pontos por Categoria",
                    color=cat_counts.index,
                    color_discrete_map=CORES_CATEGORIAS
                )
                st.plotly_chart(fig_cat, use_container_width=True)
                
                # Detalhamento por categoria selecionada
                st.markdown("### 🔍 Detalhamento por Categoria")
                categoria_analise = st.selectbox(
                    "Selecione uma categoria para análise detalhada:",
                    categorias_selecionadas
                )
                
                if categoria_analise:
                    df_categoria = df_filtrado[df_filtrado['Categoria'] == categoria_analise]
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total de Pontos", len(df_categoria))
                    with col2:
                        st.metric("Arquivos Únicos", df_categoria['Arquivo'].nunique())
                    with col3:
                        st.metric("% do Total", f"{round((len(df_categoria) / len(df_filtrado)) * 100, 1)}%")
                    
                    # Tabela de pontos desta categoria
                    st.markdown("#### 📋 Amostras desta Categoria")
                    top_pontos = df_categoria.head(10)[
                        ['Arquivo', 'Linha', 'Padrão', 'Justificativa']
                    ]
                    st.dataframe(top_pontos, use_container_width=True)
            
            else:
                st.warning("Nenhum dado encontrado com os filtros aplicados.")
        else:
            st.info("Dados de categoria não disponíveis ou filtros vazios.")
    
    else:
        st.warning("⚠️ Dados de impacto não encontrados.")

# === PÁGINA: ANÁLISE POR MÓDULO ===
elif pagina == "🏗️ Análise por Módulo":
    
    if 'impacto' in dados:
        df = dados['impacto']
        
        # Adicionar classificação e prefixo
        df['Classificação'] = df['Arquivo'].apply(lambda x: 'Oficiais' if any(x.lower().startswith(p) for p in [
            'dd', 'gap', 'i', 'audit', 'autobasi', 'basico', 'br', 'cbpi', 'csp',
            'estoque', 'faturamento', 'fiscal', 'frete', 'gem', 'ipi', 'ipp',
            'mnemonic', 'precos', 'sistema', 'supervisao', 'tropical', 'tti'
        ]) else 'Scripts' if x.lower().startswith('aba') else 'Não Oficiais')
        
        df['Prefixo'] = df['Arquivo'].str[:3].str.upper()
        
        # Filtrar apenas oficiais por padrão
        df_oficiais = df[df['Classificação'] == 'Oficiais']
        
        st.markdown("## 🏗️ Análise por Módulo (Rotinas Oficiais)")
        
        if not df_oficiais.empty:
            # Seleção de módulo
            modulos = sorted(df_oficiais['Prefixo'].unique())
            modulo_selecionado = st.selectbox("Selecione um módulo:", modulos)
            
            if modulo_selecionado:
                df_modulo = df_oficiais[df_oficiais['Prefixo'] == modulo_selecionado]
                
                # Métricas do módulo
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Pontos", len(df_modulo))
                with col2:
                    st.metric("Arquivos Únicos", df_modulo['Arquivo'].nunique())
                with col3:
                    st.metric("% dos Oficiais", f"{round((len(df_modulo) / len(df_oficiais)) * 100, 1)}%")
                with col4:
                    st.metric("Classificação", "Oficial")
                
                # Distribuição por categoria neste módulo
                if 'Categoria' in df_modulo.columns:
                    st.markdown("### 📊 Distribuição por Categoria de Ajuste")
                    cat_dist = df_modulo['Categoria'].value_counts()
                    
                    fig_mod_cat = px.pie(
                        values=cat_dist.values,
                        names=cat_dist.index,
                        title=f"Categorias no Módulo {modulo_selecionado}",
                        color=cat_dist.index,
                        color_discrete_map=CORES_CATEGORIAS
                    )
                    st.plotly_chart(fig_mod_cat, use_container_width=True)
                
                # Lista de arquivos mais impactados
                st.markdown("### 📁 Arquivos Mais Impactados")
                arquivos_impacto = df_modulo.groupby('Arquivo').agg({
                    'Linha': 'count',
                    'Categoria': lambda x: ', '.join(x.unique()) if 'Categoria' in df_modulo.columns else 'N/A'
                }).rename(columns={'Linha': 'Qtd Pontos'}).sort_values('Qtd Pontos', ascending=False)
                
                st.dataframe(arquivos_impacto, use_container_width=True)
        else:
            st.warning("Nenhum módulo oficial encontrado.")
    
    else:
        st.warning("⚠️ Dados de impacto não encontrados.")

# === PÁGINA: PONTOS CRÍTICOS ===
elif pagina == "⚠️ Pontos Críticos":
    
    if 'precificacao' in dados and '4_Pontos_Criticos' in dados['precificacao']:
        st.markdown("## ⚠️ Pontos Críticos (Rotinas Oficiais)")
        
        df_criticos = dados['precificacao']['4_Pontos_Criticos']
        
        if not df_criticos.empty:
            # Distribuição por categoria dos pontos críticos
            if 'Categoria' in df_criticos.columns:
                st.markdown("### 📊 Distribuição por Categoria")
                
                cat_criticos = df_criticos['Categoria'].value_counts()
                fig_criticos = px.bar(
                    x=cat_criticos.values,
                    y=cat_criticos.index,
                    title="Pontos Críticos por Categoria",
                    orientation='h',
                    color=cat_criticos.index,
                    color_discrete_map=CORES_CATEGORIAS
                )
                st.plotly_chart(fig_criticos, use_container_width=True)
            
            # Tabela detalhada
            st.markdown("### 📋 Detalhamento dos Pontos Críticos")
            st.dataframe(df_criticos, use_container_width=True)
            
            # Análise por módulo dos críticos
            if len(df_criticos) > 0:
                df_criticos['Prefixo'] = df_criticos['Arquivo'].str[:3].str.upper()
                st.markdown("### 🏗️ Módulos Mais Críticos")
                
                modulos_criticos = df_criticos['Prefixo'].value_counts().head(10)
                fig_mod_crit = px.bar(
                    x=modulos_criticos.index,
                    y=modulos_criticos.values,
                    title="Top 10 Módulos com Mais Pontos Críticos"
                )
                st.plotly_chart(fig_mod_crit, use_container_width=True)
        else:
            st.info("Nenhum ponto crítico identificado.")
    
    else:
        st.warning("⚠️ Dados de pontos críticos não encontrados.")

# === PÁGINA: EXPLORADOR INTERATIVO ===
elif pagina == "🔍 Explorador Interativo":
    
    if 'impacto' in dados:
        st.markdown("## 🔍 Explorador Interativo - Filtros e Agrupamentos")
        
        df = dados['impacto'].copy()
        
        # Adicionar colunas auxiliares
        df['Classificação'] = df['Arquivo'].apply(lambda x: 'Oficiais' if any(x.lower().startswith(p) for p in [
            'dd', 'gap', 'i', 'audit', 'autobasi', 'basico', 'br', 'cbpi', 'csp',
            'estoque', 'faturamento', 'fiscal', 'frete', 'gem', 'ipi', 'ipp',
            'mnemonic', 'precos', 'sistema', 'supervisao', 'tropical', 'tti'
        ]) else 'Scripts' if x.lower().startswith('aba') else 'Não Oficiais')
        
        df['Prefixo'] = df['Arquivo'].str[:3].str.upper()
        df['Nome_Arquivo'] = df['Arquivo'].str.split('/').str[-1]  # Apenas o nome do arquivo
        
        # === SEÇÃO DE FILTROS ===
        st.markdown("### 🎛️ Painel de Filtros")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Filtro por classificação
            classificacoes_disponiveis = df['Classificação'].unique()
            classificacoes_selecionadas = st.multiselect(
                "🏷️ Classificação:",
                classificacoes_disponiveis,
                default=['Oficiais']
            )
        
        with col2:
            # Filtro por categoria
            if 'Categoria' in df.columns:
                categorias_disponiveis = df['Categoria'].unique()
                categorias_selecionadas = st.multiselect(
                    "📂 Categoria:",
                    categorias_disponiveis,
                    default=categorias_disponiveis
                )
            else:
                categorias_selecionadas = []
        
        with col3:
            # Filtro por prefixo
            prefixos_disponiveis = sorted(df['Prefixo'].unique())
            prefixos_selecionados = st.multiselect(
                "🏗️ Módulo (Prefixo):",
                prefixos_disponiveis,
                default=prefixos_disponiveis[:10]  # Primeiros 10 por padrão
            )
        
        with col4:
            # Filtro por padrão
            if 'Padrão' in df.columns:
                padroes_disponiveis = df['Padrão'].unique()
                padrao_selecionado = st.selectbox(
                    "🔍 Padrão Específico:",
                    ['Todos'] + list(padroes_disponiveis)
                )
            else:
                padrao_selecionado = 'Todos'
        
        # Aplicar filtros
        df_filtrado = df.copy()
        
        if classificacoes_selecionadas:
            df_filtrado = df_filtrado[df_filtrado['Classificação'].isin(classificacoes_selecionadas)]
        
        if categorias_selecionadas and 'Categoria' in df.columns:
            df_filtrado = df_filtrado[df_filtrado['Categoria'].isin(categorias_selecionadas)]
        
        if prefixos_selecionados:
            df_filtrado = df_filtrado[df_filtrado['Prefixo'].isin(prefixos_selecionados)]
        
        if padrao_selecionado != 'Todos' and 'Padrão' in df.columns:
            df_filtrado = df_filtrado[df_filtrado['Padrão'] == padrao_selecionado]
        
        # === SEÇÃO DE AGRUPAMENTOS ===
        st.markdown("### 📊 Análise e Agrupamentos Dinâmicos")
        
        if not df_filtrado.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                # Opções de agrupamento
                opcoes_agrupamento = ['Prefixo', 'Classificação']
                if 'Categoria' in df_filtrado.columns:
                    opcoes_agrupamento.append('Categoria')
                if 'Padrão' in df_filtrado.columns:
                    opcoes_agrupamento.append('Padrão')
                
                agrupamento_por = st.selectbox(
                    "📈 Agrupar dados por:",
                    opcoes_agrupamento
                )
            
            with col2:
                # Opções de métrica
                metrica_opcoes = ['Quantidade de Pontos', 'Quantidade de Arquivos']
                metrica_selecionada = st.selectbox(
                    "📊 Métrica para exibir:",
                    metrica_opcoes
                )
            
            # Gerar agrupamento
            if agrupamento_por and metrica_selecionada:
                if metrica_selecionada == 'Quantidade de Pontos':
                    df_agrupado = df_filtrado.groupby(agrupamento_por).size().reset_index(name='Quantidade')
                else:  # Quantidade de Arquivos
                    df_agrupado = df_filtrado.groupby(agrupamento_por)['Arquivo'].nunique().reset_index(name='Quantidade')
                
                df_agrupado = df_agrupado.sort_values('Quantidade', ascending=False)
                
                # Gráfico do agrupamento
                fig_agrup = px.bar(
                    df_agrupado,
                    x=agrupamento_por,
                    y='Quantidade',
                    title=f"{metrica_selecionada} por {agrupamento_por}",
                    color='Quantidade',
                    color_continuous_scale='Blues'
                )
                fig_agrup.update_layout(height=400)
                st.plotly_chart(fig_agrup, use_container_width=True)
                
                # Tabela do agrupamento
                st.markdown(f"#### 📋 Detalhamento: {metrica_selecionada} por {agrupamento_por}")
                
                # Adicionar percentuais
                df_agrupado['Percentual'] = round((df_agrupado['Quantidade'] / df_agrupado['Quantidade'].sum()) * 100, 1)
                df_agrupado['Percentual_Str'] = df_agrupado['Percentual'].astype(str) + '%'
                
                # Converter para string para evitar erros de serialização
                df_display = df_agrupado[[agrupamento_por, 'Quantidade', 'Percentual_Str']].copy()
                df_display = df_display.astype(str)
                
                # Exibir tabela com filtros por coluna
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True
                )
        
        # === SEÇÃO DE TABELA PRINCIPAL FILTRADA ===
        st.markdown("### 📋 Dados Filtrados")
        
        if not df_filtrado.empty:
            # Estatísticas rápidas
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total de Pontos", len(df_filtrado))
            with col2:
                st.metric("Arquivos Únicos", df_filtrado['Arquivo'].nunique())
            with col3:
                st.metric("Módulos Únicos", df_filtrado['Prefixo'].nunique())
            with col4:
                if 'Categoria' in df_filtrado.columns:
                    st.metric("Categorias", df_filtrado['Categoria'].nunique())
                else:
                    st.metric("Classificações", df_filtrado['Classificação'].nunique())
            
            # Opções de exibição da tabela
            col1, col2 = st.columns(2)
            
            with col1:
                # Colunas para exibir
                colunas_disponiveis = df_filtrado.columns.tolist()
                colunas_padrao = ['Arquivo', 'Linha', 'Prefixo', 'Classificação']
                if 'Categoria' in colunas_disponiveis:
                    colunas_padrao.append('Categoria')
                if 'Padrão' in colunas_disponiveis:
                    colunas_padrao.append('Padrão')
                
                colunas_selecionadas = st.multiselect(
                    "Selecione as colunas para exibir:",
                    colunas_disponiveis,
                    default=colunas_padrao
                )
            
            with col2:
                # Limite de linhas
                limite_linhas = st.select_slider(
                    "Limite de linhas para exibição:",
                    options=[50, 100, 250, 500, 1000, 'Todas'],
                    value=250
                )
            
            # Exibir tabela filtrada
            if colunas_selecionadas:
                df_exibir = df_filtrado[colunas_selecionadas].copy()
                
                if limite_linhas != 'Todas':
                    df_exibir = df_exibir.head(limite_linhas)
                
                st.markdown(f"#### 📊 Mostrando {len(df_exibir)} de {len(df_filtrado)} registros")
                
                # Tabela com opção de download
                st.dataframe(df_exibir, use_container_width=True, hide_index=True)
                
                # Botão de download
                if st.button("💾 Baixar dados filtrados como CSV"):
                    csv = df_filtrado.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"dados_filtrados_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
        else:
            st.warning("⚠️ Nenhum dado encontrado com os filtros aplicados.")
    
    else:
        st.warning("⚠️ Dados de impacto não encontrados.")

# === PÁGINA: DADOS BRUTOS ===
elif pagina == "📋 Dados Brutos":
    
    st.markdown("## 📋 Dados Brutos - Exploração Avançada")
    
    # Tabs para diferentes conjuntos de dados com filtros
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Impactos", "💰 Precificação", "🗑️ Descartes", "❓ Não Classificados"])
    
    with tab1:
        if 'impacto' in dados:
            st.markdown("### 🎯 Pontos de Impacto - Com Filtros Avançados")
            
            df_imp = dados['impacto'].copy()
            
            # Adicionar colunas auxiliares
            df_imp['Classificação'] = df_imp['Arquivo'].apply(lambda x: 'Oficiais' if any(x.lower().startswith(p) for p in [
                'dd', 'gap', 'i', 'audit', 'autobasi', 'basico', 'br', 'cbpi', 'csp',
                'estoque', 'faturamento', 'fiscal', 'frete', 'gem', 'ipi', 'ipp',
                'mnemonic', 'precos', 'sistema', 'supervisao', 'tropical', 'tti'
            ]) else 'Scripts' if x.lower().startswith('aba') else 'Não Oficiais')
            
            df_imp['Prefixo'] = df_imp['Arquivo'].str[:3].str.upper()
            
            # === FILTROS ===
            st.markdown("#### 🔍 Filtros")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                classificacoes_imp = st.multiselect(
                    "🏷️ Classificação:",
                    df_imp['Classificação'].unique(),
                    default=['Oficiais']
                )
            
            with col2:
                if 'Categoria' in df_imp.columns:
                    categorias_imp = st.multiselect(
                        "📂 Categoria:",
                        df_imp['Categoria'].unique(),
                        default=df_imp['Categoria'].unique()
                    )
                else:
                    categorias_imp = []
            
            with col3:
                prefixos_imp = st.multiselect(
                    "🏗️ Módulo (Prefixo):",
                    sorted(df_imp['Prefixo'].unique()),
                    default=sorted(df_imp['Prefixo'].unique())[:15]
                )
            
            with col4:
                # Filtro por faixa de horas
                if 'Estimativa (Horas)' in df_imp.columns:
                    min_horas = st.number_input("Min Horas:", 0.0, step=0.1, value=0.0)
                    max_horas = st.number_input("Max Horas:", 0.0, step=0.1, value=float(df_imp['Estimativa (Horas)'].max()))
                else:
                    min_horas = max_horas = 0
            
            # Aplicar filtros
            df_imp_filtrado = df_imp.copy()
            
            if classificacoes_imp:
                df_imp_filtrado = df_imp_filtrado[df_imp_filtrado['Classificação'].isin(classificacoes_imp)]
            
            if categorias_imp and 'Categoria' in df_imp.columns:
                df_imp_filtrado = df_imp_filtrado[df_imp_filtrado['Categoria'].isin(categorias_imp)]
            
            if prefixos_imp:
                df_imp_filtrado = df_imp_filtrado[df_imp_filtrado['Prefixo'].isin(prefixos_imp)]
            
            if 'Estimativa (Horas)' in df_imp.columns and max_horas > 0:
                df_imp_filtrado = df_imp_filtrado[
                    (df_imp_filtrado['Estimativa (Horas)'] >= min_horas) & 
                    (df_imp_filtrado['Estimativa (Horas)'] <= max_horas)
                ]
            
            # === ESTATÍSTICAS ===
            st.markdown("#### 📊 Estatísticas dos Dados Filtrados")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Registros", len(df_imp_filtrado))
            with col2:
                st.metric("Arquivos Únicos", df_imp_filtrado['Arquivo'].nunique())
            with col3:
                st.metric("Módulos", df_imp_filtrado['Prefixo'].nunique())
            with col4:
                if 'Estimativa (Horas)' in df_imp_filtrado.columns:
                    st.metric("Total Horas", f"{df_imp_filtrado['Estimativa (Horas)'].sum():.1f}h")
            
            # === GRÁFICOS ===
            if not df_imp_filtrado.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Gráfico por categoria
                    if 'Categoria' in df_imp_filtrado.columns:
                        cat_count = df_imp_filtrado['Categoria'].value_counts()
                        fig_cat = px.pie(
                            values=cat_count.values,
                            names=cat_count.index,
                            title="Distribuição por Categoria"
                        )
                        fig_cat.update_layout(height=300)
                        st.plotly_chart(fig_cat, use_container_width=True)
                
                with col2:
                    # Top 10 módulos
                    mod_count = df_imp_filtrado['Prefixo'].value_counts().head(10)
                    fig_mod = px.bar(
                        x=mod_count.values,
                        y=mod_count.index,
                        orientation='h',
                        title="Top 10 Módulos"
                    )
                    fig_mod.update_layout(height=300)
                    st.plotly_chart(fig_mod, use_container_width=True)
            
            # === TABELA ===
            st.markdown("#### 📋 Dados Filtrados")
            
            # Opções de exibição
            col1, col2 = st.columns(2)
            with col1:
                limite_imp = st.selectbox("Registros por página:", [100, 500, 1000, "Todos"], index=1)
            with col2:
                ordenar_imp = st.selectbox("Ordenar por:", df_imp_filtrado.columns.tolist())
            
            # Aplicar ordenação e limite
            if ordenar_imp:
                df_imp_filtrado = df_imp_filtrado.sort_values(ordenar_imp, ascending=False)
            
            if limite_imp != "Todos":
                df_exibir_imp = df_imp_filtrado.head(limite_imp)
            else:
                df_exibir_imp = df_imp_filtrado
            
            # Exibir tabela
            st.dataframe(df_exibir_imp, use_container_width=True, hide_index=True)
            
            # Download
            csv = df_imp_filtrado.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Download Impactos Filtrados",
                data=csv,
                file_name=f"impactos_filtrados_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
        else:
            st.warning("Dados de impacto não encontrados.")
    
    with tab2:
        if 'precificacao' in dados:
            st.markdown("### 💰 Dados de Precificação - Com Filtros")
            
            # Seleção de planilha
            sheet_selecionada = st.selectbox(
                "Selecione a planilha:",
                list(dados['precificacao'].keys())
            )
            
            if sheet_selecionada:
                df_prec = dados['precificacao'][sheet_selecionada].copy()
                
                # Estatísticas básicas
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Registros", len(df_prec))
                with col2:
                    st.metric("Colunas", len(df_prec.columns))
                with col3:
                    st.metric("Planilha", sheet_selecionada)
                
                # Filtros
                st.markdown("#### 🔍 Filtros")
                
                # Filtro por coluna
                colunas_texto = [col for col in df_prec.columns if df_prec[col].dtype == 'object']
                if colunas_texto:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        coluna_filtro = st.selectbox("Filtrar por coluna:", ['Nenhum'] + colunas_texto)
                    
                    with col2:
                        if coluna_filtro != 'Nenhum':
                            valores_unicos = df_prec[coluna_filtro].dropna().unique()
                            if len(valores_unicos) <= 20:
                                valores_filtro = st.multiselect(
                                    f"Valores de {coluna_filtro}:",
                                    valores_unicos,
                                    default=valores_unicos
                                )
                            else:
                                texto_filtro = st.text_input(f"Buscar em {coluna_filtro}:")
                                valores_filtro = None
                        else:
                            valores_filtro = None
                            texto_filtro = ""
                
                # Aplicar filtros
                df_prec_filtrado = df_prec.copy()
                if 'coluna_filtro' in locals() and coluna_filtro != 'Nenhum':
                    if valores_filtro is not None:
                        df_prec_filtrado = df_prec_filtrado[df_prec_filtrado[coluna_filtro].isin(valores_filtro)]
                    elif 'texto_filtro' in locals() and texto_filtro:
                        df_prec_filtrado = df_prec_filtrado[
                            df_prec_filtrado[coluna_filtro].str.contains(texto_filtro, case=False, na=False)
                        ]
                
                # Tabela
                st.dataframe(df_prec_filtrado, use_container_width=True, hide_index=True)
                
                # Download
                csv = df_prec_filtrado.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label=f"📥 Download {sheet_selecionada}",
                    data=csv,
                    file_name=f"{sheet_selecionada}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        else:
            st.warning("Dados de precificação não encontrados.")
    
    with tab3:
        if 'descartes' in dados:
            st.markdown("### 🗑️ Itens Descartados - Com Filtros")
            
            df_desc = dados['descartes'].copy()
            
            # Adicionar colunas auxiliares
            df_desc['Classificação'] = df_desc['Arquivo'].apply(lambda x: 'Oficiais' if any(x.lower().startswith(p) for p in [
                'dd', 'gap', 'i', 'audit', 'autobasi', 'basico', 'br', 'cbpi', 'csp',
                'estoque', 'faturamento', 'fiscal', 'frete', 'gem', 'ipi', 'ipp',
                'mnemonic', 'precos', 'sistema', 'supervisao', 'tropical', 'tti'
            ]) else 'Scripts' if x.lower().startswith('aba') else 'Não Oficiais')
            
            df_desc['Prefixo'] = df_desc['Arquivo'].str[:3].str.upper()
            
            # === FILTROS ===
            st.markdown("#### 🔍 Filtros")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                classificacoes_desc = st.multiselect(
                    "🏷️ Classificação:",
                    df_desc['Classificação'].unique(),
                    default=['Oficiais']
                )
            
            with col2:
                if 'Regra de Descarte' in df_desc.columns:
                    regras_desc = st.multiselect(
                        "📋 Regra de Descarte:",
                        df_desc['Regra de Descarte'].unique(),
                        default=df_desc['Regra de Descarte'].unique()[:5]
                    )
                else:
                    regras_desc = []
            
            with col3:
                prefixos_desc = st.multiselect(
                    "🏗️ Módulo (Prefixo):",
                    sorted(df_desc['Prefixo'].unique()),
                    default=sorted(df_desc['Prefixo'].unique())[:10]
                )
            
            # Aplicar filtros
            df_desc_filtrado = df_desc.copy()
            
            if classificacoes_desc:
                df_desc_filtrado = df_desc_filtrado[df_desc_filtrado['Classificação'].isin(classificacoes_desc)]
            
            if regras_desc and 'Regra de Descarte' in df_desc.columns:
                df_desc_filtrado = df_desc_filtrado[df_desc_filtrado['Regra de Descarte'].isin(regras_desc)]
            
            if prefixos_desc:
                df_desc_filtrado = df_desc_filtrado[df_desc_filtrado['Prefixo'].isin(prefixos_desc)]
            
            # === ESTATÍSTICAS ===
            st.markdown("#### 📊 Estatísticas dos Descartes")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Descartados", len(df_desc_filtrado))
            with col2:
                st.metric("Arquivos Únicos", df_desc_filtrado['Arquivo'].nunique())
            with col3:
                if 'Regra de Descarte' in df_desc_filtrado.columns:
                    st.metric("Regras Diferentes", df_desc_filtrado['Regra de Descarte'].nunique())
            with col4:
                st.metric("Módulos", df_desc_filtrado['Prefixo'].nunique())
            
            # === GRÁFICO DE REGRAS ===
            if 'Regra de Descarte' in df_desc_filtrado.columns and not df_desc_filtrado.empty:
                regras_count = df_desc_filtrado['Regra de Descarte'].value_counts()
                fig_regras = px.bar(
                    x=regras_count.values,
                    y=regras_count.index,
                    orientation='h',
                    title="Distribuição por Regra de Descarte"
                )
                fig_regras.update_layout(height=400)
                st.plotly_chart(fig_regras, use_container_width=True)
            
            # === TABELA ===
            st.markdown("#### 📋 Dados Filtrados")
            
            # Opções de exibição
            col1, col2 = st.columns(2)
            with col1:
                limite_desc = st.selectbox("Registros por página:", [100, 500, 1000, "Todos"], index=1, key="desc_limite")
            with col2:
                ordenar_desc = st.selectbox("Ordenar por:", df_desc_filtrado.columns.tolist(), key="desc_ordem")
            
            # Aplicar ordenação e limite
            if ordenar_desc:
                df_desc_filtrado = df_desc_filtrado.sort_values(ordenar_desc)
            
            if limite_desc != "Todos":
                df_exibir_desc = df_desc_filtrado.head(limite_desc)
            else:
                df_exibir_desc = df_desc_filtrado
            
            # Exibir tabela
            st.dataframe(df_exibir_desc, use_container_width=True, hide_index=True)
            
            # Download
            csv = df_desc_filtrado.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Download Descartes Filtrados",
                data=csv,
                file_name=f"descartes_filtrados_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
        else:
            st.warning("Dados de descartes não encontrados.")
    
    with tab4:
        if 'nao_classificados' in dados:
            st.markdown("### ❓ Itens Não Classificados - Com Filtros")
            st.info("⚠️ Estes itens podem precisar de análise manual adicional.")
            
            df_nc = dados['nao_classificados'].copy()
            
            # Adicionar colunas auxiliares
            df_nc['Classificação'] = df_nc['Arquivo'].apply(lambda x: 'Oficiais' if any(x.lower().startswith(p) for p in [
                'dd', 'gap', 'i', 'audit', 'autobasi', 'basico', 'br', 'cbpi', 'csp',
                'estoque', 'faturamento', 'fiscal', 'frete', 'gem', 'ipi', 'ipp',
                'mnemonic', 'precos', 'sistema', 'supervisao', 'tropical', 'tti'
            ]) else 'Scripts' if x.lower().startswith('aba') else 'Não Oficiais')
            
            df_nc['Prefixo'] = df_nc['Arquivo'].str[:3].str.upper()
            
            # === FILTROS ===
            st.markdown("#### 🔍 Filtros")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                classificacoes_nc = st.multiselect(
                    "🏷️ Classificação:",
                    df_nc['Classificação'].unique(),
                    default=['Oficiais']
                )
            
            with col2:
                if 'Variável Encontrada' in df_nc.columns:
                    variaveis_nc = st.multiselect(
                        "🔍 Variáveis:",
                        sorted(df_nc['Variável Encontrada'].unique()),
                        default=sorted(df_nc['Variável Encontrada'].unique())[:10]
                    )
                else:
                    variaveis_nc = []
            
            with col3:
                prefixos_nc = st.multiselect(
                    "🏗️ Módulo (Prefixo):",
                    sorted(df_nc['Prefixo'].unique()),
                    default=sorted(df_nc['Prefixo'].unique())[:10]
                )
            
            # Aplicar filtros
            df_nc_filtrado = df_nc.copy()
            
            if classificacoes_nc:
                df_nc_filtrado = df_nc_filtrado[df_nc_filtrado['Classificação'].isin(classificacoes_nc)]
            
            if variaveis_nc and 'Variável Encontrada' in df_nc.columns:
                df_nc_filtrado = df_nc_filtrado[df_nc_filtrado['Variável Encontrada'].isin(variaveis_nc)]
            
            if prefixos_nc:
                df_nc_filtrado = df_nc_filtrado[df_nc_filtrado['Prefixo'].isin(prefixos_nc)]
            
            # === ESTATÍSTICAS ===
            st.markdown("#### 📊 Estatísticas dos Não Classificados")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Não Classificados", len(df_nc_filtrado))
            with col2:
                st.metric("Arquivos Únicos", df_nc_filtrado['Arquivo'].nunique())
            with col3:
                if 'Variável Encontrada' in df_nc_filtrado.columns:
                    st.metric("Variáveis Diferentes", df_nc_filtrado['Variável Encontrada'].nunique())
            with col4:
                st.metric("Módulos", df_nc_filtrado['Prefixo'].nunique())
            
            # === GRÁFICO DE VARIÁVEIS ===
            if 'Variável Encontrada' in df_nc_filtrado.columns and not df_nc_filtrado.empty:
                var_count = df_nc_filtrado['Variável Encontrada'].value_counts().head(15)
                fig_var = px.bar(
                    x=var_count.values,
                    y=var_count.index,
                    orientation='h',
                    title="Top 15 Variáveis Não Classificadas"
                )
                fig_var.update_layout(height=400)
                st.plotly_chart(fig_var, use_container_width=True)
            
            # === TABELA ===
            st.markdown("#### 📋 Dados Filtrados")
            
            # Opções de exibição
            col1, col2 = st.columns(2)
            with col1:
                limite_nc = st.selectbox("Registros por página:", [100, 500, 1000, "Todos"], index=1, key="nc_limite")
            with col2:
                ordenar_nc = st.selectbox("Ordenar por:", df_nc_filtrado.columns.tolist(), key="nc_ordem")
            
            # Aplicar ordenação e limite
            if ordenar_nc:
                df_nc_filtrado = df_nc_filtrado.sort_values(ordenar_nc)
            
            if limite_nc != "Todos":
                df_exibir_nc = df_nc_filtrado.head(limite_nc)
            else:
                df_exibir_nc = df_nc_filtrado
            
            # Exibir tabela
            st.dataframe(df_exibir_nc, use_container_width=True, hide_index=True)
            
            # Download
            csv = df_nc_filtrado.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Download Não Classificados Filtrados",
                data=csv,
                file_name=f"nao_classificados_filtrados_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
        else:
            st.warning("Dados de não classificados não encontrados.")

# Rodapé
st.markdown("---")
st.markdown("📊 **Dashboard de Análise CNPJ Alfanumérico** | Desenvolvido para suporte à precificação da proposta")

# Instruções de uso na sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("### 📖 Como usar:")
st.sidebar.markdown("""
1. **Execute primeiro:** `python main.py`
2. **Inicie o dashboard:** `streamlit run dashboard.py`
3. **Navegue pelas abas** para diferentes visões
4. **Use os filtros** para análises específicas
5. **Baixe os dados** conforme necessário
""")

# Informações técnicas na sidebar
if 'impacto' in dados:
    st.sidebar.markdown("### 📈 Estatísticas:")
    df = dados['impacto']
    st.sidebar.metric("Total de Pontos", len(df))
    if 'Estimativa (Horas)' in df.columns:
        st.sidebar.metric("Total Estimado", f"{df['Estimativa (Horas)'].sum():.1f}h")
    st.sidebar.metric("Arquivos Únicos", df['Arquivo'].nunique()) 