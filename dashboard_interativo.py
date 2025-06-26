# 📤 Dashboard CNPJ Alfanumérico - Versão Interativa
# Upload de arquivos + processamento em tempo real

import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime
from typing import Dict, List, Any

# === CONFIGURAÇÃO ===
st.set_page_config(
    page_title="Dashboard CNPJ Interativo",
    page_icon="📤",
    layout="wide"
)

# === FUNÇÕES DE PROCESSAMENTO ===
def processar_codigo(conteudo: str) -> tuple:
    """Processa código e identifica pontos CNPJ"""
    
    padroes_cnpj = [
        r'\bcnpj\b', r'\bCNPJ\b', r'\bCgc\b', r'\bcgc\b', r'\bCGC\b',
        r'\bCadNacPesJur\b', r'\bcadNacPesJur\b', r'\bCADNACPESJUR\b'
    ]
    
    regras_descarte = [
        r'^\s*\*', r'^\s*//', r'^\s*REM\s', r'STRING\s*\(', 
        r'WRITE\s*\(', r'DISPLAY\s', r'EXHIBIT\s'
    ]
    
    pontos = []
    descartados = []
    nao_classificados = []
    
    linhas = conteudo.split('\n')
    
    for i, linha in enumerate(linhas, 1):
        linha_limpa = linha.strip()
        
        if not linha_limpa:
            continue
        
        # Verificar descarte
        deve_descartar = False
        regra_descarte = None
        
        for regra in regras_descarte:
            if re.search(regra, linha_limpa, re.IGNORECASE):
                deve_descartar = True
                regra_descarte = regra.replace('\\', '').replace('s*', '').replace('b', '')
                break
        
        if deve_descartar:
            descartados.append({
                'Linha': i,
                'Código': linha_limpa[:80] + '...' if len(linha_limpa) > 80 else linha_limpa,
                'Motivo': regra_descarte
            })
            continue
        
        # Procurar CNPJ
        for padrao in padroes_cnpj:
            if re.search(padrao, linha_limpa):
                categoria = categorizar_linha(linha_limpa)
                
                if categoria:
                    estimativa = {
                        'Validação/Entrada': 0.8,
                        'Formatação/Exibição': 0.5,
                        'Lógica de Negócio': 1.8,
                        'Integrações Externas': 2.8,
                        'Estrutura de Dados': 0.9
                    }.get(categoria, 1.0)
                    
                    pontos.append({
                        'Linha': i,
                        'Código': linha_limpa[:80] + '...' if len(linha_limpa) > 80 else linha_limpa,
                        'Variável': padrao.replace('\\', '').replace('b', ''),
                        'Categoria': categoria,
                        'Estimativa (h)': estimativa
                    })
                else:
                    nao_classificados.append({
                        'Linha': i,
                        'Código': linha_limpa[:80] + '...' if len(linha_limpa) > 80 else linha_limpa,
                        'Variável': padrao.replace('\\', '').replace('b', '')
                    })
                break
    
    return pontos, nao_classificados, descartados

def categorizar_linha(linha: str) -> str:
    """Categoriza linha de código"""
    linha_upper = linha.upper()
    
    if any(palavra in linha_upper for palavra in ['VALIDATE', 'CHECK', 'IF', 'WHEN', 'PERFORM']):
        return 'Validação/Entrada'
    elif any(palavra in linha_upper for palavra in ['DISPLAY', 'WRITE', 'MOVE', 'STRING']):
        return 'Formatação/Exibição'
    elif any(palavra in linha_upper for palavra in ['COMPUTE', 'ADD', 'EVALUATE', 'SEARCH']):
        return 'Lógica de Negócio'
    elif any(palavra in linha_upper for palavra in ['EXEC', 'SQL', 'SELECT', 'CICS', 'DB2']):
        return 'Integrações Externas'
    elif any(palavra in linha_upper for palavra in ['REDEFINES', 'OCCURS', 'PIC', 'VALUE']):
        return 'Estrutura de Dados'
    
    return None

# === INTERFACE ===
st.title("📤 Dashboard CNPJ - Análise Interativa")

# === UPLOAD DE ARQUIVOS ===
st.markdown("## 📁 Upload de Arquivos")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📄 Arquivo CSV (Variáveis)")
    arquivo_csv = st.file_uploader(
        "Upload do CSV com variáveis CNPJ:",
        type=['csv'],
        help="Arquivo com colunas: Variável, Tipo, Descrição"
    )

with col2:
    st.markdown("### 📝 Arquivo TXT (Código)")
    arquivo_txt = st.file_uploader(
        "Upload do TXT com código-fonte:",
        type=['txt'],
        help="Arquivo de texto com código para análise"
    )

# === PROCESSAMENTO ===
if arquivo_csv and arquivo_txt:
    
    col1, col2, col3 = st.columns([1,1,1])
    
    with col2:
        processar = st.button(
            "🚀 ANALISAR ARQUIVOS",
            type="primary",
            use_container_width=True
        )
    
    if processar:
        
        with st.spinner("🔄 Processando arquivos..."):
            
            # Ler CSV
            try:
                df_variaveis = pd.read_csv(arquivo_csv)
                st.success(f"✅ CSV carregado: {len(df_variaveis)} variáveis")
            except Exception as e:
                st.error(f"❌ Erro no CSV: {e}")
                st.stop()
            
            # Ler TXT
            try:
                conteudo = arquivo_txt.read().decode('utf-8', errors='ignore')
                total_linhas = len(conteudo.split('\n'))
                st.success(f"✅ TXT carregado: {total_linhas} linhas")
            except Exception as e:
                st.error(f"❌ Erro no TXT: {e}")
                st.stop()
            
            # Processar
            pontos, nao_class, descartes = processar_codigo(conteudo)
            
            # Salvar resultados
            st.session_state['resultados'] = {
                'pontos': pd.DataFrame(pontos),
                'nao_classificados': pd.DataFrame(nao_class),
                'descartados': pd.DataFrame(descartes),
                'variaveis': df_variaveis,
                'stats': {
                    'total_linhas': total_linhas,
                    'arquivo_nome': arquivo_txt.name,
                    'processado_em': datetime.now()
                }
            }
        
        st.success("🎉 Processamento concluído!")

# === RESULTADOS ===
if 'resultados' in st.session_state:
    
    dados = st.session_state['resultados']
    
    st.markdown("---")
    st.markdown("## 📊 Resultados da Análise")
    
    # === MÉTRICAS ===
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📝 Linhas Analisadas", f"{dados['stats']['total_linhas']:,}")
    
    with col2:
        st.metric("🎯 Pontos Encontrados", len(dados['pontos']))
    
    with col3:
        st.metric("❓ Não Classificados", len(dados['nao_classificados']))
    
    with col4:
        st.metric("🗑️ Descartados", len(dados['descartados']))
    
    # === ABAS DE RESULTADOS ===
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 Pontos de Impacto",
        "📊 Análise por Categoria", 
        "❓ Não Classificados",
        "🗑️ Descartados",
        "📋 Dados Brutos"
    ])
    
    with tab1:
        st.markdown("### 🎯 Pontos de Impacto Identificados")
        
        if not dados['pontos'].empty:
            df_pontos = dados['pontos']
            
            # Estimativa total
            total_horas = df_pontos['Estimativa (h)'].sum()
            st.info(f"⏱️ **Estimativa Total:** {total_horas:.1f} horas ({total_horas/8:.1f} dias úteis)")
            
            # Filtros simples
            col1, col2 = st.columns(2)
            
            with col1:
                if 'Categoria' in df_pontos.columns:
                    cats_selecionadas = st.multiselect(
                        "🏷️ Filtrar por Categoria:",
                        df_pontos['Categoria'].unique(),
                        default=df_pontos['Categoria'].unique()
                    )
                else:
                    cats_selecionadas = []
            
            with col2:
                vars_selecionadas = st.multiselect(
                    "🔍 Filtrar por Variável:",
                    df_pontos['Variável'].unique(),
                    default=df_pontos['Variável'].unique()
                )
            
            # Aplicar filtros
            df_filtrado = df_pontos.copy()
            if cats_selecionadas:
                df_filtrado = df_filtrado[df_filtrado['Categoria'].isin(cats_selecionadas)]
            if vars_selecionadas:
                df_filtrado = df_filtrado[df_filtrado['Variável'].isin(vars_selecionadas)]
            
            # Mostrar dados filtrados
            st.markdown(f"**{len(df_filtrado)} pontos** ({df_filtrado['Estimativa (h)'].sum():.1f}h)")
            st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
            
            # Download
            csv = df_filtrado.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                "📥 Download Pontos de Impacto",
                csv,
                file_name=f"pontos_impacto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("⚠️ Nenhum ponto de impacto encontrado")
    
    with tab2:
        st.markdown("### 📊 Análise por Categoria")
        
        if not dados['pontos'].empty and 'Categoria' in dados['pontos'].columns:
            df_pontos = dados['pontos']
            
            # Agrupamento
            cat_stats = df_pontos.groupby('Categoria').agg({
                'Estimativa (h)': ['sum', 'mean', 'count']
            }).round(2)
            
            cat_stats.columns = ['Total Horas', 'Média Horas', 'Quantidade']
            cat_stats = cat_stats.reset_index()
            
            # Gráficos
            col1, col2 = st.columns(2)
            
            with col1:
                fig1 = px.pie(
                    cat_stats,
                    values='Total Horas',
                    names='Categoria',
                    title="Distribuição de Horas por Categoria"
                )
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                fig2 = px.bar(
                    cat_stats,
                    x='Categoria',
                    y='Quantidade',
                    title="Quantidade de Pontos por Categoria"
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            # Tabela
            st.dataframe(cat_stats, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ Dados insuficientes para análise por categoria")
    
    with tab3:
        st.markdown("### ❓ Itens Não Classificados")
        
        if not dados['nao_classificados'].empty:
            st.info("💡 Estes itens podem precisar de análise manual")
            st.dataframe(dados['nao_classificados'], use_container_width=True, hide_index=True)
        else:
            st.success("✅ Todos os pontos foram classificados!")
    
    with tab4:
        st.markdown("### 🗑️ Itens Descartados")
        
        if not dados['descartados'].empty:
            st.info("ℹ️ Linhas ignoradas (comentários, strings, etc.)")
            
            # Análise de motivos
            if 'Motivo' in dados['descartados'].columns:
                motivo_count = dados['descartados']['Motivo'].value_counts()
                
                fig = px.bar(
                    x=motivo_count.values,
                    y=motivo_count.index,
                    orientation='h',
                    title="Motivos de Descarte"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(dados['descartados'], use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ Nenhum item foi descartado")
    
    with tab5:
        st.markdown("### 📋 Todos os Dados")
        
        sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
            "🎯 Impactos", "❓ Não Class.", "🗑️ Descartes", "📄 Variáveis"
        ])
        
        with sub_tab1:
            st.dataframe(dados['pontos'], use_container_width=True, hide_index=True)
        
        with sub_tab2:
            st.dataframe(dados['nao_classificados'], use_container_width=True, hide_index=True)
        
        with sub_tab3:
            st.dataframe(dados['descartados'], use_container_width=True, hide_index=True)
        
        with sub_tab4:
            st.dataframe(dados['variaveis'], use_container_width=True, hide_index=True)
    
    # === AÇÕES ===
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Nova Análise"):
            del st.session_state['resultados']
            st.experimental_rerun()
    
    with col2:
        # Download completo
        if st.button("📦 Download Completo"):
            import zipfile
            import io
            
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                # Adicionar CSVs ao ZIP
                for nome, df in dados.items():
                    if isinstance(df, pd.DataFrame):
                        csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                        zip_file.writestr(f"{nome}.csv", csv_data)
            
            st.download_button(
                "📥 Baixar ZIP Completo",
                zip_buffer.getvalue(),
                file_name=f"analise_cnpj_completa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                mime="application/zip"
            )
    
    with col3:
        st.info(f"📅 Processado: {dados['stats']['processado_em'].strftime('%H:%M:%S')}")

else:
    # === INSTRUÇÕES ===
    st.markdown("---")
    st.markdown("## 📖 Instruções de Uso")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 1️⃣ Arquivo CSV de Variáveis
        
        Faça upload de um arquivo CSV com:
        - **Variável:** Nome da variável CNPJ
        - **Tipo:** Tipo de dado
        - **Descrição:** Descrição da variável
        
        **Exemplo:**
        ```
        Variável,Tipo,Descrição
        CNPJ,String,Número do CNPJ
        CGC,String,Cadastro Geral
        ```
        """)
    
    with col2:
        st.markdown("""
        ### 2️⃣ Arquivo TXT de Código
        
        Faça upload do código-fonte contendo:
        - Código COBOL, Natural, JCL
        - Rotinas de mainframe
        - Scripts de banco de dados
        
        **O sistema irá:**
        - 🔍 Identificar variáveis CNPJ
        - 📊 Categorizar por tipo de uso
        - ⏱️ Estimar esforço de alteração
        """)
    
    st.markdown("""
    ### 3️⃣ Resultados
    
    Após o processamento, você terá:
    - **📊 Resumo executivo** com métricas principais
    - **🎯 Lista de pontos** que precisam alteração
    - **📈 Análises gráficas** por categoria
    - **📥 Download** dos resultados em CSV/ZIP
    """)

# === RODAPÉ ===
st.markdown("---")
st.markdown("📤 **Dashboard CNPJ Interativo** | Desenvolvido para análise de impacto em tempo real") 