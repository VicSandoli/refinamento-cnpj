import re
import csv
import os
import pandas as pd

# --- CONFIGURAÇÃO ---

# 1. Coloque aqui o caminho do seu arquivo de entrada
ARQUIVO_ENTRADA = 'CNPJresults_findStudio 3.txt'

# 2. Nomes dos arquivos de saída que serão gerados
ARQUIVO_SAIDA_IMPACTO = 'analise_impacto_cnpj_refinada.xlsx'
ARQUIVO_SAIDA_DESCARTES = 'analise_descartes.xlsx'
ARQUIVO_SAIDA_NAO_CLASSIFICADOS = 'analise_sem_classificacao.xlsx'
ARQUIVO_SAIDA_PRECIFICACAO = 'analise_precificacao_proposta.xlsx'

# 3. Arquivo com as variáveis a serem analisadas
ARQUIVO_VARIAVEIS = 'CNPJ 1.csv'

# --- CATEGORIAS PARA PRECIFICAÇÃO REALISTA ---

# Premissa: Solução centralizada será implementada para tratar CNPJ alfanumérico
# Estimativas por CATEGORIA (não por ponto individual)
CATEGORIAS_AJUSTE = {
    "VALIDACAO_ENTRADA": {
        "nome": "Validação e Entrada de Dados",
        "descricao": "Pontos que validam entrada de CNPJ - serão ajustados para usar função central",
        "esforco_base": 56,  # horas totais para a categoria (+40%)
        "esforco_testes": 22,  # horas de testes QA (+40%)
        "observacao": "Implementação de função central + ajustes pontuais + validações específicas"
    },
    "FORMATACAO_EXIBICAO": {
        "nome": "Formatação e Exibição",
        "descricao": "Pontos que formatam CNPJ para exibição - usarão função central de formatação",
        "esforco_base": 30,  # horas totais (+25%)
        "esforco_testes": 10,  # horas de testes QA (+25%)
        "observacao": "Substituição por chamadas à função central + ajustes de layout"
    },
    "LOGICA_NEGOCIO": {
        "nome": "Lógica de Negócio Específica",
        "descricao": "Pontos com lógica específica que precisam revisão manual",
        "esforco_base": 120, # horas totais (+50%)
        "esforco_testes": 48,  # horas de testes QA (+50%)
        "observacao": "Análise caso a caso + reengenharia + adaptação + testes específicos"
    },
    "INTEGRACAO_EXTERNA": {
        "nome": "Integrações Externas",
        "descricao": "Interfaces com sistemas externos - análise de compatibilidade",
        "esforco_base": 50,  # horas totais (+56%)
        "esforco_testes": 40,  # horas de testes QA (+67% - mais testes por ser integração)
        "observacao": "Verificação de compatibilidade + adaptação + testes de integração"
    },
    "ESTRUTURA_DADOS": {
        "nome": "Estrutura de Dados",
        "descricao": "Ajustes em banco de dados, índices e consultas",
        "esforco_base": 24,  # horas totais (+50%)
        "esforco_testes": 12,  # horas de testes QA (+50%)
        "observacao": "Revisão de tipos de dados + índices + performance + migração"
    }
}

# --- REGRAS SIMPLIFICADAS PARA CATEGORIZAÇÃO ---

# REGRAS GLOBAIS: Verificadas em TODAS as linhas
REGRAS_GLOBAIS_CATEGORIAS = [
    (
        "Máscara Numérica Explícita",
        r"\?\d*N",
        "VALIDACAO_ENTRADA",
        "Máscara que força entrada numérica - precisa aceitar alfanumérico."
    ),
]

# REGRAS VINCULADAS: Verificadas apenas em linhas que contêm uma variável alvo
REGRAS_VINCULADAS_CATEGORIAS = [
    # --- VALIDAÇÃO E ENTRADA ---
    (
        "Validação de Entrada",
        r"(if.*\bVARIAVEL\b.*[=<>]\s*\d+|\$L\(.*\bVARIAVEL\b.*\)\s*[=<>]\s*1[14])",
        "VALIDACAO_ENTRADA",
        "Validação que assume formato/comprimento específico - usar função central."
    ),
    (
        "Conversão Numérica",
        r"(\$NUMBER\s*\(\s*\bVARIAVEL\b|if.*\bVARIAVEL\b.*[+\-*/])",
        "VALIDACAO_ENTRADA",
        "Conversão para número ou operação aritmética - usar função central."
    ),
    
    # --- FORMATAÇÃO E EXIBIÇÃO ---
    (
        "Formatação Manual",
        r'(\bVARIAVEL\b\s*_\s*"[\./-]"|Write.*\bVARIAVEL\b)',
        "FORMATACAO_EXIBICAO",
        "Formatação manual para exibição - usar função central de formatação."
    ),
    
    # --- LÓGICA DE NEGÓCIO ---
    (
        "Extração de CNPJ Raiz",
        r"(\$E|\$EXTRACT)\s*\(\s*\bVARIAVEL\b\s*,\s*1\s*,\s*(8|12)\s*\)",
        "LOGICA_NEGOCIO",
        "Extração de raiz com comprimento fixo - revisar lógica para alfanumérico."
    ),
    (
        "Manipulação Específica",
        r"(\$E|\$EXTRACT)\s*\(\s*\bVARIAVEL\b",
        "LOGICA_NEGOCIO",
        "Manipulação específica de substring - verificar se permanece válida."
    ),
    
    # --- INTEGRAÇÃO EXTERNA ---
    (
        "Interface Externa",
        r"(HTTP|REST|SOAP|XML|JSON|EXPORT|IMPORT|FILE).*\bVARIAVEL\b|\bVARIAVEL\b.*(HTTP|REST|SOAP|XML|JSON|EXPORT|IMPORT|FILE)",
        "INTEGRACAO_EXTERNA",
        "Interface externa - verificar se destino suporta CNPJ alfanumérico."
    ),
    
    # --- ESTRUTURA DE DADOS ---
    (
        "Operação de Banco",
        r"(SELECT|INSERT|UPDATE|DELETE|ORDER\s+BY|GROUP\s+BY|WHERE).*\bVARIAVEL\b",
        "ESTRUTURA_DADOS",
        "Operação de banco - verificar tipos de dados e performance."
    ),
]

def carregar_variaveis_alvo(caminho_csv):
    """
    Carrega dinamicamente as variáveis de um arquivo CSV.
    Assume que o delimitador é ';' e as variáveis estão na 5ª coluna (índice 4).
    Filtra para manter apenas nomes de variáveis válidos.
    """
    if not os.path.exists(caminho_csv):
        print(f"ERRO: Arquivo de variáveis '{caminho_csv}' não encontrado.")
        return []

    variaveis = set()
    with open(caminho_csv, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f, delimiter=';')
        next(reader, None)  # Pula o cabeçalho
        for row in reader:
            if len(row) > 4 and row[4].strip():
                var = row[4].strip()
                # Filtro simples para nomes de variáveis (começa com letra, pode ter números/underline)
                if re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', var):
                    variaveis.add(var)
    
    print(f"{len(variaveis)} variáveis carregadas de {caminho_csv}")
    return list(variaveis)


def extrair_info_linha(linha):
    """Extrai o nome do arquivo, número da linha e o código da linha de entrada."""
    match = re.match(r"^(.*?)\((\d+)\):\s*(.*)", linha)
    if match:
        return match.groups()
    return None, None, None

# --- FUNÇÕES DE ANÁLISE REESTRUTURADAS ---

def analisar_regras_globais(codigo):
    """Aplica as regras globais de categorização ao código."""
    for nome, regex, categoria, just in REGRAS_GLOBAIS_CATEGORIAS:
        if re.search(regex, codigo, re.IGNORECASE):
            return nome, categoria, just, regex
    return None

def analisar_regras_vinculadas(codigo, var_alvo):
    """Aplica as regras vinculadas de categorização a uma variável específica."""
    for nome, regex, categoria, just in REGRAS_VINCULADAS_CATEGORIAS:
        regex_var = regex.replace('VARIAVEL', var_alvo)
        if re.search(regex_var, codigo, re.IGNORECASE):
            return nome, categoria, just
    return None

def gerar_relatorio_precificacao_realista(df_impacto):
    """Gera relatório de precificação baseado em categorias de ajuste (não por ponto)."""
    if df_impacto.empty:
        print("\nNenhum dado para relatório de precificação.")
        return
    
    # Adicionar colunas auxiliares
    df_impacto['Classificação'] = df_impacto['Arquivo'].apply(classificar_arquivo)
    
    # Filtrar apenas rotinas oficiais
    df_oficiais = df_impacto[df_impacto['Classificação'] == 'Oficiais'].copy()
    
    print(f"📊 Análise focada em ROTINAS OFICIAIS: {len(df_oficiais)} pontos de {len(df_impacto)} totais")
    
    if df_oficiais.empty:
        print("Nenhuma rotina oficial encontrada.")
        return
    
    # Contar pontos por categoria
    contagem_categorias = df_oficiais['Categoria'].value_counts()
    
    # 1. Summary por Categoria de Ajuste
    summary_categorias = []
    total_dev = 0
    total_testes = 0
    
    for categoria, config in CATEGORIAS_AJUSTE.items():
        pontos_categoria = contagem_categorias.get(categoria, 0)
        
        if pontos_categoria > 0:
            # Esforço base + proporcional ao número de pontos (máximo 50% extra)
            fator_pontos = min(1 + (pontos_categoria - 1) * 0.1, 1.5)  # Max 50% extra
            esforco_dev = round(config["esforco_base"] * fator_pontos)
            esforco_testes = round(config["esforco_testes"] * fator_pontos)
            
            total_dev += esforco_dev
            total_testes += esforco_testes
            
            summary_categorias.append({
                "Categoria": config["nome"],
                "Pontos Identificados": str(pontos_categoria),  # Converter para string
                "Esforço Dev (h)": esforco_dev,
                "Esforço Testes (h)": esforco_testes,
                "Total (h)": esforco_dev + esforco_testes,
                "Observação": config["observacao"],
                "Descrição": config["descricao"]
            })
    
    # 2. Esforço da Solução Central
    esforco_central = {
        "Categoria": "Solução Central - Funções Base",
        "Pontos Identificados": "Base",  # String consistente
        "Esforço Dev (h)": 120,  # Desenvolvimento das funções centrais
        "Esforço Testes (h)": 40,   # Testes unitários das funções centrais
        "Total (h)": 160,
        "Observação": "Funções de validação, formatação e utilitários CNPJ alfanumérico",
        "Descrição": "Desenvolvimento das funções centralizadas que serão usadas em todo o sistema"
    }
    
    # Adicionar solução central no início
    summary_categorias.insert(0, esforco_central)
    total_dev += 120
    total_testes += 40
    
    # 3. Summary Executivo
    total_geral = total_dev + total_testes
    
    summary_executivo = [{
        "Métrica": "Esforço Desenvolvimento",
        "Valor": f"{total_dev}h",
        "Observação": "Desenvolvimento + adaptações pontuais"
    }, {
        "Métrica": "Esforço Testes QA", 
        "Valor": f"{total_testes}h",
        "Observação": "Testes unitários + integração + regressão"
    }, {
        "Métrica": "Total Estimado",
        "Valor": f"{total_geral}h",
        "Observação": "Estimativa realista considerando solução centralizada"
    }, {
        "Métrica": "Pontos Oficiais Analisados",
        "Valor": str(len(df_oficiais)),  # Converter para string
        "Observação": "Apenas rotinas oficiais consideradas"
    }, {
        "Métrica": "Estimativa com Buffer 20%",
        "Valor": f"{round(total_geral * 1.2)}h",
        "Observação": "Margem para imprevistos (mais conservadora)"
    }]
    
    # 4. Distribuição por Módulo (apenas oficiais)
    df_oficiais['Prefixo'] = df_oficiais['Arquivo'].str[:3].str.upper()
    summary_modulos = []
    
    for prefixo in sorted(df_oficiais['Prefixo'].unique()):
        dados_modulo = df_oficiais[df_oficiais['Prefixo'] == prefixo]
        categorias_modulo = dados_modulo['Categoria'].value_counts()
        
        summary_modulos.append({
            "Prefixo Módulo": prefixo,
            "Pontos Totais": str(len(dados_modulo)),  # Converter para string
            "Categorias": ', '.join([f"{cat}({qtd})" for cat, qtd in categorias_modulo.items()]),
            "% dos Pontos": round((len(dados_modulo) / len(df_oficiais)) * 100, 1)
        })
    
    # Salvar relatórios
    try:
        with pd.ExcelWriter(ARQUIVO_SAIDA_PRECIFICACAO, engine='openpyxl') as writer:
            # Aba 1: Summary Executivo
            pd.DataFrame(summary_executivo).to_excel(
                writer, sheet_name='1_Summary_Executivo', index=False
            )
            
            # Aba 2: Por Categoria de Ajuste
            pd.DataFrame(summary_categorias).to_excel(
                writer, sheet_name='2_Por_Categoria_Ajuste', index=False
            )
            
            # Aba 3: Por Módulo
            pd.DataFrame(summary_modulos).to_excel(
                writer, sheet_name='3_Por_Modulo_Oficiais', index=False
            )
            
            # Aba 4: Detalhamento de pontos críticos  
            if len(df_oficiais) > 0:
                pontos_criticos = df_oficiais.head(20)[
                    ['Arquivo', 'Linha', 'Categoria', 'Padrão', 'Justificativa', 'Código']
                ]
            else:
                pontos_criticos = pd.DataFrame()
            pontos_criticos.to_excel(
                writer, sheet_name='4_Pontos_Criticos', index=False
            )
            
        print(f"Relatório de precificação realista salvo em: {ARQUIVO_SAIDA_PRECIFICACAO}")
        print(f"📊 RESUMO EXECUTIVO:")
        print(f"   • Pontos oficiais analisados: {len(df_oficiais)}")
        print(f"   • Desenvolvimento: {total_dev}h")
        print(f"   • Testes QA: {total_testes}h") 
        print(f"   • Total: {total_geral}h")
        print(f"   • Com buffer 20%: {round(total_geral * 1.2)}h")
        
    except Exception as e:
        print(f"ERRO ao salvar relatório de precificação: {e}")

# REGRAS DE DESCARTE: mantidas do código original
REGRAS_VINCULADAS_DESCARTE = [
    # Descarte de strings literais (maior prioridade)
    (r'^\s*(S|Set)\s+\w+\s*=\s*".*\bVARIAVEL\b.*"', "Atribuição de String Literal"),
    (r'^\s*W(rite)?\s*!?,?\s*".*\bVARIAVEL\b.*"', "Escrita de String Literal"),
    # Comentários
    (r"^\s*;", "Comentário"),
    (r"\brem\b", "Comentário 'rem'"),
    (r"^\s*//", "Comentário '//'"),
    (r"^\s*#;", "Comentário '#;'"),
    # Outras regras de descarte
    (r",\s*\w+\s*=\s*\bVARIAVEL\b", "Atribuição Simples (Múltiplos Comandos)"),
    (r"^\s*Do\s+.*\^.*\bVARIAVEL\b", "Chamada de Rotina (Do)"),
    (r"\$O\s*\(.*\bVARIAVEL\b", "Uso em $ORDER"),
    (r"^\s*Write\s+.*\bVARIAVEL\b", "Escrita simples (Write)"),
    (r"^\s*(S|Set)\s+\w+\s*=\s*\bVARIAVEL\b\s*($|;)", "Atribuição Simples"),
    (r"\$\$\$PARAMETROS\s*\(.*\bVARIAVEL\b", "Uso em macro $$$PARAMETROS"),
    (r"'\$D\(.*\bVARIAVEL\b.*\)", "Verificação de existência em Global ($D)"),
    (r"New\s+.*\bVARIAVEL\b", "Declaração New"),
    (r'S\s*\(?.*\bVARIAVEL\b.*\)?\s*=\s*""', "Inicialização para vazio"),
    (r'Set\s+\bVARIAVEL\b\s*=\s*""', "Set para vazio"),
    (r'if\s+\bVARIAVEL\b\s*=\s*""', "Comparação com vazio"),
    (r'if\s+\bVARIAVEL\b\s*\'\s*=\s*""', "Comparação com vazio"),
    (r"if\s+\$G\(\bVARIAVEL\b", "Verificação com $GET"),
    (r'G:\bVARIAVEL\b\?1""', "GOTO se nulo"),
    (r"Write\s+.*/CAMPO\s*\(" , "Escrita em campo de tela"),
    (r"Set\s+.*\s*=\s*##class\(", "Chamada de método de classe"),
    (r"\.cpfcnpj\s*=", "Atribuição a propriedade de objeto"),
]



def checar_descarte_vinculado(codigo, var_alvo):
    """Verifica se a linha deve ser ignorada com base nas regras de descarte vinculadas."""
    for regex, motivo in REGRAS_VINCULADAS_DESCARTE:
        regex_var = regex.replace('VARIAVEL', var_alvo)
        if re.search(regex_var, codigo, re.IGNORECASE):
            return motivo
    return None

def classificar_arquivo(nome_arquivo):
    """Adiciona classificação 'Oficiais', 'Scripts' ou 'Não Oficiais'."""
    prefixos_oficiais = [
        'dd', 'gap', 'i', 'audit', 'autobasi', 'basico', 'br', 'cbpi', 'csp',
        'estoque', 'faturamento', 'fiscal', 'frete', 'gem', 'ipi', 'ipp',
        'mnemonic', 'precos', 'sistema', 'supervisao', 'tropical', 'tti'
    ]
    nome_arquivo_lower = nome_arquivo.lower()
    if nome_arquivo_lower.startswith('aba'):
        return 'Scripts'
    if any(nome_arquivo_lower.startswith(p) for p in prefixos_oficiais):
        return 'Oficiais'
    return 'Não Oficiais'

def main():
    print("--- INICIANDO ANÁLISE DE IMPACTO DE CNPJ ALFANUMÉRICO (v2) ---")
    
    VARIAVEIS_ALVO = carregar_variaveis_alvo(ARQUIVO_VARIAVEIS)
    if not VARIAVEIS_ALVO:
        print("Nenhuma variável alvo para analisar. Encerrando.")
        return
        
    print(f"Analisando o arquivo: {ARQUIVO_ENTRADA}")
    if not os.path.exists(ARQUIVO_ENTRADA):
        print(f"ERRO: Arquivo de entrada não encontrado em '{ARQUIVO_ENTRADA}'")
        return

    variaveis_regex = r"\b(" + "|".join(re.escape(var) for var in VARIAVEIS_ALVO) + r")\b"

    resultados_impacto = []
    resultados_descartados = []
    resultados_sem_classificacao = []
    
    linhas_analisadas = 0
    with open(ARQUIVO_ENTRADA, 'r', encoding='utf-8', errors='ignore') as f_in:
        for linha_bruta in f_in:
            linhas_analisadas += 1
            if "Searching for" in linha_bruta or not linha_bruta.strip():
                continue

            arquivo, num_linha, codigo_original = extrair_info_linha(linha_bruta.strip())
            if not arquivo:
                continue

            # PRE-PROCESSAMENTO: remove comentários inline para análise mais precisa
            codigo_para_analise = re.split(r'\s*//', codigo_original)[0].strip()

            # Otimização: Descartar rotinas não oficiais no início
            if classificar_arquivo(arquivo) == 'Não Oficiais':
                match_var_descarte = re.search(variaveis_regex, codigo_para_analise, re.IGNORECASE)
                var_encontrada_descarte = match_var_descarte.group(0) if match_var_descarte else "N/A"
                resultados_descartados.append({
                    "Arquivo": arquivo, "Linha": num_linha, "Variável": var_encontrada_descarte.upper(),
                    "Regra de Descarte": "Rotina Não Oficial", "Código": codigo_original
                })
                continue

            foi_classificada = False

            # 1. Análise de Regras Globais (maior prioridade)
            resultado_global = analisar_regras_globais(codigo_para_analise)
            if resultado_global:
                regra, categoria, just, padrao = resultado_global
                resultados_impacto.append({
                    "Arquivo": arquivo, "Linha": num_linha, "Variável": f"Padrão Global: {padrao}",
                    "Categoria": categoria, "Padrão": regra, "Justificativa": just,
                    "Código": codigo_original
                })
                foi_classificada = True

            # 2. Análise Vinculada a Variável (se não classificada globalmente)
            if not foi_classificada:
                match_var = re.search(variaveis_regex, codigo_para_analise, re.IGNORECASE)
                if match_var:
                    var_encontrada = match_var.group(0)

                    # 2a. Checar Categorização Vinculada
                    resultado_categoria = analisar_regras_vinculadas(codigo_para_analise, var_encontrada)
                    if resultado_categoria:
                        regra, categoria, just = resultado_categoria
                        resultados_impacto.append({
                            "Arquivo": arquivo, "Linha": num_linha, "Variável": var_encontrada.upper(),
                            "Categoria": categoria, "Padrão": regra, "Justificativa": just,
                            "Código": codigo_original
                        })
                        foi_classificada = True
                    else:
                        # 2b. Checar Descarte (apenas se não houver categorização)
                        motivo_descarte = checar_descarte_vinculado(codigo_para_analise, var_encontrada)
                        if motivo_descarte:
                            resultados_descartados.append({
                                "Arquivo": arquivo, "Linha": num_linha, "Variável": var_encontrada.upper(),
                                "Regra de Descarte": motivo_descarte, "Código": codigo_original
                            })
                            foi_classificada = True


            # 3. Coletar itens não classificados que contêm variáveis
            if not foi_classificada:
                 match_var = re.search(variaveis_regex, codigo_para_analise, re.IGNORECASE)
                 if match_var:
                    resultados_sem_classificacao.append({
                        "Arquivo": arquivo, "Linha": num_linha,
                        "Variável Encontrada": match_var.group(0).upper(),
                        "Código": codigo_original
                    })


    print(f"\nAnálise concluída.")
    print(f"Total de linhas lidas: {linhas_analisadas}")
    print(f"Pontos de impacto identificados: {len(resultados_impacto)}")
    print(f"Itens descartados: {len(resultados_descartados)}")
    print(f"Itens sem classificação: {len(resultados_sem_classificacao)}")

    # Função auxiliar para salvar DataFrames
    def salvar_excel(df, nome_arquivo, colunas_ordem):
        if df.empty:
            print(f"\nNenhum item para salvar em '{nome_arquivo}'.")
            return
        
        df_copy = df.copy()
        df_copy['Prefixo'] = df_copy['Arquivo'].str[:3].str.upper()
        df_copy['Classificação'] = df_copy['Arquivo'].apply(classificar_arquivo)
        df_copy['LinhaInt'] = pd.to_numeric(df_copy['Linha'])
        
        # Ordenação especial para o DataFrame de impacto
        if "Categoria" in df_copy.columns:
            # Ordenação por prioridade de categoria
            ordem_categoria = {
                "VALIDACAO_ENTRADA": 0,
                "LOGICA_NEGOCIO": 1, 
                "INTEGRACAO_EXTERNA": 2,
                "ESTRUTURA_DADOS": 3,
                "FORMATACAO_EXIBICAO": 4
            }
            df_copy['OrdemCategoria'] = df_copy['Categoria'].map(ordem_categoria).fillna(99)
            df_copy = df_copy.sort_values(by=['OrdemCategoria', 'Arquivo', 'LinhaInt'], ascending=[True, True, True])
        else:
            df_copy = df_copy.sort_values(by=['Arquivo', 'LinhaInt'])

        # Garante que todas as colunas esperadas existam antes de reordenar
        colunas_presentes = df_copy.columns.tolist()
        colunas_finais = [col for col in colunas_ordem if col in colunas_presentes]
        
        df_final = df_copy[colunas_finais]

        try:
            df_final.to_excel(nome_arquivo, index=False, engine='openpyxl')
            print(f"Relatório salvo em: {nome_arquivo}")
        except Exception as e:
            print(f"ERRO ao salvar o arquivo '{nome_arquivo}': {e}")

    # Gerar Relatório de Impacto
    if resultados_impacto:
        df_impacto = pd.DataFrame(resultados_impacto)
        colunas_impacto = [
            "Arquivo", "Prefixo", "Classificação", "Linha", "Variável",
            "Categoria", "Padrão", "Justificativa", "Código"
        ]
        salvar_excel(df_impacto, ARQUIVO_SAIDA_IMPACTO, colunas_impacto)
        
        # Gerar Relatório de Precificação REALISTA (foco em rotinas oficiais)
        gerar_relatorio_precificacao_realista(df_impacto)

    # Gerar Relatório de Descartes
    if resultados_descartados:
        df_descartados = pd.DataFrame(resultados_descartados)
        colunas_descartes = [
            "Arquivo", "Prefixo", "Classificação", "Linha",
            "Variável", "Regra de Descarte", "Código"
        ]
        salvar_excel(df_descartados, ARQUIVO_SAIDA_DESCARTES, colunas_descartes)

    # Gerar Relatório de Não Classificados
    if resultados_sem_classificacao:
        df_nao_classificados = pd.DataFrame(resultados_sem_classificacao)
        colunas_nao_classificados = [
            "Arquivo", "Prefixo", "Classificação", "Linha",
            "Variável Encontrada", "Código"
        ]
        salvar_excel(df_nao_classificados, ARQUIVO_SAIDA_NAO_CLASSIFICADOS, colunas_nao_classificados)

if __name__ == "__main__":
    main()