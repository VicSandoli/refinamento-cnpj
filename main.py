import re
import csv
import os
import pandas as pd

# --- CONFIGURAÇÃO ---

# 1. Coloque aqui o caminho do seu arquivo de entrada
ARQUIVO_ENTRADA = 'CNPJresults_findStudio 3.txt'

# 2. Nomes dos arquivos de saída que serão gerados
ARQUIVO_SAIDA_AJUSTES = 'analise_ajustes_criticos.xlsx'
ARQUIVO_SAIDA_DESCARTES = 'analise_descartes.xlsx'
ARQUIVO_SAIDA_DESCARTES_OFICIAIS = 'analise_descartes_oficiais.xlsx'
ARQUIVO_SAIDA_PRECIFICACAO = 'analise_precificacao_proposta.xlsx'

# 3. Arquivo com as variáveis a serem analisadas
ARQUIVO_VARIAVEIS = 'CNPJ 1.csv'

# --- CATEGORIAS PARA PRECIFICAÇÃO REALISTA ---
# Mantidas para gerar a estimativa de esforço final.
CATEGORIAS_AJUSTE = {
    "VALIDACAO_ENTRADA": {
        "nome": "Validação e Entrada de Dados",
        "descricao": "Pontos que validam entrada de CNPJ - serão ajustados para usar função central",
        "esforco_base": 56, "esforco_testes": 22,
        "observacao": "Implementação de função central + ajustes pontuais"
    },
    "FORMATACAO_EXIBICAO": {
        "nome": "Formatação e Exibição",
        "descricao": "Pontos que formatam CNPJ para exibição - usarão função central",
        "esforco_base": 30, "esforco_testes": 10,
        "observacao": "Substituição por chamadas à função central"
    },
    "LOGICA_NEGOCIO": {
        "nome": "Lógica de Negócio Específica",
        "descricao": "Pontos com lógica específica que precisam revisão manual",
        "esforco_base": 120, "esforco_testes": 48,
        "observacao": "Análise caso a caso, reengenharia e testes específicos"
    },
    "INTEGRACAO_EXTERNA": {
        "nome": "Integrações Externas",
        "descricao": "Interfaces com sistemas externos - análise de compatibilidade",
        "esforco_base": 50, "esforco_testes": 40,
        "observacao": "Verificação de compatibilidade, adaptação e testes de integração"
    },
    "ESTRUTURA_DADOS": {
        "nome": "Estrutura de Dados",
        "descricao": "Ajustes em banco de dados, índices e consultas",
        "esforco_base": 24, "esforco_testes": 12,
        "observacao": "Revisão de tipos de dados, índices, performance e migração"
    },
    "REVISAO_MANUAL": {
        "nome": "Revisão Manual Necessária",
        "descricao": "Linhas que não se encaixam em padrões conhecidos e exigem análise",
        "esforco_base": 2, "esforco_testes": 1, # Custo por ponto
        "observacao": "Análise manual para determinar a categoria correta e o impacto"
    }
}

# --- REGRAS DE DESCARTE DE ALTA CONFIANÇA ---
# Se uma linha corresponder a qualquer uma destas regras, será descartada.
REGRAS_DESCARTE_CONFIANCA = [
    ("Comentário", r"^\s*(;.*|//.*|#;.*|rem\s)"),
    ("String Literal", r'".*\bVARIAVEL\b.*"'),
    # Regra aprimorada para ser mais específica e evitar descartar atribuições que usam a variável
    ("Atribuição Simples (de variável)", r"^\s*(S|Set)\s+\w+\s*=\s*\bVARIAVEL\b\s*($|;|,|!)"),
    # Regra aprimorada para permitir propriedades de objeto (ponto) e variáveis com '%'
    ("Atribuição Simples (para variável)", r"^\s*(S|Set)\s+\bVARIAVEL\b\s*=\s*[%.\w]+\s*($|;|,|!)"),
    # Regra expandida para cobrir atribuições em lista, como S ALT=0,CCLI=""
    ("Set para Vazio", r'^\s*(S|Set)\s+.*\bVARIAVEL\b\s*=\s*""|,\s*\bVARIAVEL\b\s*=\s*""'),
    # Nova regra, focada apenas na comparação
    ("Comparação com Vazio", r"if\s+'?\bVARIAVEL\b'?\s*=\s*"""),
    # Nova regra para comparação com strings fixas
    ("Comparação com String Fixa", r"^\s*(I|If)\s+'?\bVARIAVEL\b'?\s*=\s*"".*"""),
    ("Uso como Parâmetro Simples", r"(\(|,)\s*\bVARIAVEL\b\s*(\)|,)"),
    ("Parâmetro em Chamada de Método/Função", r"(##class\(|##super\(|\$\$\w+\^)\([^)]*\bVARIAVEL\b[^)]*\)"),
    ("Chamada de Rotina (Do)", r"^\s*Do\s+.*\^.*\bVARIAVEL\b"),
    ("Uso em $ORDER", r"\$O\s*\(.*\bVARIAVEL\b"),
    # Nova regra para o comando Kill
    ("Comando Kill", r"^\s*(K|Kill)\s+.*?\bVARIAVEL\b"),
    # Regra aprimorada para incluir a abreviação 'N' e ser mais precisa
    ("Declaração New", r"^\s*(N|New)\s+.*?\bVARIAVEL\b"),
    ("Verificação de Existência ($D, $G)", r"(if\s+\$G|\$D)\(.*\bVARIAVEL\b"),
]

# --- REGRAS PARA IDENTIFICAR AJUSTES CRÍTICOS ---
# Todas as linhas não descartadas serão testadas contra estas regras.
REGRAS_AJUSTE_CRITICO = [
    # --- VALIDAÇÃO E ENTRADA ---
    (
        "Máscara Numérica Explícita", r"\?\d*N", "VALIDACAO_ENTRADA",
        "Máscara que força entrada numérica - precisa aceitar alfanumérico."
    ),
    (
        "Validação de Comprimento", r"\$L(ENGTH)?\s*\(\s*\bVARIAVEL\b.*\)\s*[=<>]\s*(11|14)", "VALIDACAO_ENTRADA",
        "Validação de tamanho fixo - precisa ser flexibilizada."
    ),
    (
        "Conversão/Operação Numérica", r"(\$NUMBER|\$ZSTRIP)\s*\(\s*\bVARIAVEL\b|\bVARIAVEL\b\s*[\+\-\*\/]\s*\d+|\d+\s*[\+\-\*\/]\s*\bVARIAVEL\b", "VALIDACAO_ENTRADA",
        "Conversão para número ou operação aritmética - falhará com alfanumérico."
    ),
    # --- LÓGICA DE NEGÓCIO ---
    (
        "Padding com Soma", r"(1000000\d{6,}\s*\+\s*\bVARIAVEL\b|\bVARIAVEL\b\s*\+\s*1000000\d{6,})", "LOGICA_NEGOCIO",
        "Técnica de padding com soma para ordenação/comparação - incompatível com alfanumérico."
    ),
    (
        "Extração de Substring ($E, $EXTRACT)", r"(\$E|\$EXTRACT)\s*\(\s*\bVARIAVEL\b", "LOGICA_NEGOCIO",
        "Extração de partes do CNPJ (raiz, filial) - a lógica pode precisar de revisão."
    ),
    (
        "Parsing com $PIECE", r"\$P(IECE)?\s*\(\s*\bVARIAVEL\b", "LOGICA_NEGOCIO",
        "Parsing da variável - pode ser afetado se o delimitador for um número."
    ),
    # --- FORMATAÇÃO E EXIBIÇÃO ---
    (
        "Formatação Manual para Exibição", r"(\bVARIAVEL\b\s*_\s*""[\.\/\-]"")|W(RITE)?\s+.*\bVARIAVEL\b", "FORMATACAO_EXIBICAO",
        "Formatação manual para exibição - deve ser substituída por função central."
    ),
    # --- INTEGRAÇÃO EXTERNA ---
    (
        "Uso em Contexto de Integração", r"(HTTP|REST|SOAP|XML|JSON|EXPORT|IMPORT|FTP|FILE).*\bVARIAVEL\b", "INTEGRACAO_EXTERNA",
        "Interface externa - verificar se o sistema destino suporta CNPJ alfanumérico."
    ),
    # --- ESTRUTURA DE DADOS ---
    (
        "Uso em Operação de Banco", r"&(SQL|sql)\(.*\bVARIAVEL\b.*\)|(SELECT|INSERT|UPDATE|DELETE|WHERE|ORDER\s+BY).*\bVARIAVEL\b", "ESTRUTURA_DADOS",
        "Operação de banco - verificar tipos de dados, índices e performance da consulta."
    ),
]


def carregar_variaveis_alvo(caminho_csv):
    """Carrega as variáveis de um arquivo CSV, filtrando nomes válidos."""
    if not os.path.exists(caminho_csv):
        print(f"ERRO: Arquivo de variáveis '{caminho_csv}' não encontrado.")
        return []
    try:
        df = pd.read_csv(caminho_csv, sep=';', usecols=['codigo'], encoding='utf-8', on_bad_lines='skip')
        df.dropna(subset=['codigo'], inplace=True)
        variaveis = df['codigo'].str.strip().unique()
        # Filtro para garantir que são nomes de variáveis válidos em Mumps
        filtro_regex = r'^[a-zA-Z%][a-zA-Z0-9]*$'
        variaveis_validas = {var for var in variaveis if isinstance(var, str) and re.match(filtro_regex, var)}
        print(f"{len(variaveis_validas)} variáveis únicas e válidas carregadas de {caminho_csv}")
        return list(variaveis_validas)
    except Exception as e:
        print(f"ERRO ao ler o arquivo de variáveis '{caminho_csv}': {e}")
        return []


def extrair_info_linha(linha):
    """Extrai o nome do arquivo, número da linha e o código da linha de entrada."""
    match = re.match(r"^(.*?)\((\d+)\):\s*(.*)", linha)
    if match:
        return match.groups()
    return None, None, None


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


def checar_descarte(codigo, var_alvo):
    """Verifica se a linha deve ser ignorada com base nas regras de descarte de alta confiança."""
    for motivo, regex in REGRAS_DESCARTE_CONFIANCA:
        regex_var = regex.replace('VARIAVEL', re.escape(var_alvo))
        if re.search(regex_var, codigo, re.IGNORECASE):
            return motivo
    return None


def analisar_ponto_critico(codigo, var_alvo):
    """Aplica as regras de ajuste crítico e retorna a primeira correspondência."""
    # Primeiro, verifica regras que não dependem da variável (globais)
    for nome, regex, categoria, just in REGRAS_AJUSTE_CRITICO:
        if 'VARIAVEL' not in regex:
            if re.search(regex, codigo, re.IGNORECASE):
                return nome, categoria, just, regex

    # Depois, verifica regras vinculadas à variável
    for nome, regex, categoria, just in REGRAS_AJUSTE_CRITICO:
        if 'VARIAVEL' in regex:
            regex_var = regex.replace('VARIAVEL', re.escape(var_alvo))
            if re.search(regex_var, codigo, re.IGNORECASE):
                return nome, categoria, just, regex_var

    # Se nenhuma regra crítica corresponder, classifica para revisão manual
    return "Revisão Manual Necessária", "REVISAO_MANUAL", "Não corresponde a nenhum padrão de ajuste ou descarte conhecido.", "N/A"


def gerar_relatorio_precificacao_realista(df_ajustes):
    """Gera relatório de precificação baseado nas categorias de ajuste."""
    if df_ajustes.empty:
        print("\nNenhum dado para gerar o relatório de precificação.")
        return

    # Focar análise apenas em rotinas oficiais
    df_oficiais = df_ajustes[df_ajustes['Classificação'] == 'Oficiais'].copy()
    print(f"\n📊 Análise de Esforço focada em ROTINAS OFICIAIS: {len(df_oficiais)} pontos de {len(df_ajustes)} totais.")
    if df_oficiais.empty:
        print("Nenhuma rotina oficial encontrada para estimativa de esforço.")
        return

    summary_categorias = []
    total_dev = 0
    total_testes = 0

    # Agrupar por categoria para calcular o esforço
    contagem_categorias = df_oficiais['Categoria'].value_counts()

    for categoria_id, config in CATEGORIAS_AJUSTE.items():
        pontos = contagem_categorias.get(categoria_id, 0)
        if pontos > 0:
            if categoria_id == "REVISAO_MANUAL":
                # Custo por ponto para revisão manual
                esforco_dev = config["esforco_base"] * pontos
                esforco_testes = config["esforco_testes"] * pontos
            else:
                # Custo base da categoria + fator por pontos
                fator_pontos = 1 + (pontos - 1) * 0.05 # Adicional de 5% por ponto extra
                esforco_dev = round(config["esforco_base"] * fator_pontos)
                esforco_testes = round(config["esforco_testes"] * fator_pontos)

            total_dev += esforco_dev
            total_testes += esforco_testes
            summary_categorias.append({
                "Categoria": config["nome"], "Pontos Identificados": pontos,
                "Esforço Dev (h)": esforco_dev, "Esforço Testes (h)": esforco_testes,
                "Total (h)": esforco_dev + esforco_testes, "Observação": config["observacao"],
            })

    # Adicionar o esforço da solução central (base)
    esforco_central = {
        "Categoria": "Solução Central - Funções Base", "Pontos Identificados": "N/A",
        "Esforço Dev (h)": 120, "Esforço Testes (h)": 40, "Total (h)": 160,
        "Observação": "Desenvolvimento de funções centrais de validação e formatação.",
    }
    summary_categorias.insert(0, esforco_central)
    total_dev += 120
    total_testes += 40
    total_geral = total_dev + total_testes

    summary_executivo = [
        {"Métrica": "Esforço Desenvolvimento", "Valor": f"{total_dev}h"},
        {"Métrica": "Esforço Testes QA", "Valor": f"{total_testes}h"},
        {"Métrica": "Total Estimado", "Valor": f"{total_geral}h"},
        {"Métrica": "Estimativa com Buffer (20%)", "Valor": f"{round(total_geral * 1.2)}h"},
        {"Métrica": "Pontos Críticos (Oficiais)", "Valor": len(df_oficiais)},
    ]

    try:
        with pd.ExcelWriter(ARQUIVO_SAIDA_PRECIFICACAO, engine='openpyxl') as writer:
            pd.DataFrame(summary_executivo).to_excel(writer, sheet_name='1_Summary_Executivo', index=False)
            pd.DataFrame(summary_categorias).to_excel(writer, sheet_name='2_Estimativa_Por_Categoria', index=False)
            # Adicionar aba com detalhamento dos pontos oficiais
            df_oficiais_detalhe = df_oficiais[['Arquivo', 'Linha', 'Categoria', 'Padrão', 'Justificativa', 'Código']]
            df_oficiais_detalhe.to_excel(writer, sheet_name='3_Detalhe_Pontos_Oficiais', index=False)
        print(f"Relatório de precificação salvo em: {ARQUIVO_SAIDA_PRECIFICACAO}")
        print(f"   -> Total Estimado: {total_geral}h | Com Buffer (20%): {round(total_geral * 1.2)}h")
    except Exception as e:
        print(f"ERRO ao salvar relatório de precificação: {e}")


def salvar_excel(df, nome_arquivo, colunas_ordem):
    """Função auxiliar para salvar DataFrames em Excel com formatação."""
    if df.empty:
        print(f"\nNenhum item para salvar em '{nome_arquivo}'.")
        return

    df_copy = df.copy()
    df_copy['Prefixo'] = df_copy['Arquivo'].str[:3].str.upper()
    df_copy['Classificação'] = df_copy['Arquivo'].apply(classificar_arquivo)
    df_copy['LinhaInt'] = pd.to_numeric(df_copy['Linha'])

    # Ordenar para melhor visualização
    if "Categoria" in df_copy.columns:
        df_copy = df_copy.sort_values(by=['Classificação', 'Arquivo', 'LinhaInt'])
    else:
        df_copy = df_copy.sort_values(by=['Arquivo', 'LinhaInt'])

    colunas_presentes = df_copy.columns.tolist()
    colunas_finais = [col for col in colunas_ordem if col in colunas_presentes]
    df_final = df_copy[colunas_finais]

    try:
        df_final.to_excel(nome_arquivo, index=False, engine='openpyxl')
        print(f"Relatório salvo em: {nome_arquivo}")
    except Exception as e:
        print(f"ERRO ao salvar o arquivo '{nome_arquivo}': {e}")


def main():
    print("--- INICIANDO ANÁLISE DE IMPACTO DE CNPJ ALFANUMÉRICO (v4 - com deduplicação) ---")

    VARIAVEIS_ALVO = carregar_variaveis_alvo(ARQUIVO_VARIAVEIS)
    
    # IBSRIC é especial e não uma variável comum
    is_ibsric_special = 'IBSRIC' in VARIAVEIS_ALVO
    if is_ibsric_special:
        VARIAVEIS_ALVO.remove('IBSRIC')
        print("Info: 'IBSRIC' será tratado como uma chamada de sub-rotina especial.")

    print(f"Analisando o arquivo: {ARQUIVO_ENTRADA}")
    if not os.path.exists(ARQUIVO_ENTRADA):
        print(f"ERRO: Arquivo de entrada não encontrado em '{ARQUIVO_ENTRADA}'")
        return

    # Etapa 1: Ler o arquivo de entrada e agrupar por linha de código única
    linhas_unicas = {}
    variaveis_regex = r"\b(" + "|".join(re.escape(var) for var in VARIAVEIS_ALVO) + r")\b" if VARIAVEIS_ALVO else None

    print("Etapa 1: Lendo e agrupando linhas de código únicas...")
    with open(ARQUIVO_ENTRADA, 'r', encoding='utf-8', errors='ignore') as f_in:
        for linha_bruta in f_in:
            if "Searching for" in linha_bruta or not linha_bruta.strip():
                continue

            arquivo, num_linha, codigo_original = extrair_info_linha(linha_bruta.strip())
            if not arquivo:
                continue

            codigo_para_analise = re.split(r'\s*//', codigo_original)[0].strip()
            
            vars_encontradas_na_linha = set()
            if variaveis_regex:
                vars_encontradas_na_linha.update(re.findall(variaveis_regex, codigo_para_analise, re.IGNORECASE))
            
            if is_ibsric_special and re.search(r'\bIBSRIC\b', codigo_para_analise, re.IGNORECASE):
                vars_encontradas_na_linha.add('IBSRIC')
            
            if not vars_encontradas_na_linha:
                continue

            chave = (arquivo, num_linha)
            if chave not in linhas_unicas:
                linhas_unicas[chave] = {'code': codigo_original, 'vars': set()}
            
            linhas_unicas[chave]['vars'].update(vars_encontradas_na_linha)

    print(f"  - {len(linhas_unicas)} linhas de código únicas encontradas para análise.")

    # Etapa 2: Classificar cada linha de código única
    print("Etapa 2: Classificando cada linha...")
    resultados_ajustes = []
    resultados_descartados = []

    for (arquivo, num_linha), data in linhas_unicas.items():
        codigo_original = data['code']
        variaveis_encontradas = data['vars']
        codigo_para_analise = re.split(r'\s*//', codigo_original)[0].strip()
        variaveis_str = ", ".join(sorted(list(variaveis_encontradas)))
        foi_classificada = False

        # 2.1. Descarte por tipo de arquivo
        classificacao = classificar_arquivo(arquivo)
        if classificacao in ['Não Oficiais', 'Scripts']:
            motivo = "Rotina de Script" if classificacao == 'Scripts' else "Rotina Não Oficial"
            resultados_descartados.append({
                "Arquivo": arquivo, "Linha": num_linha, "Variável": variaveis_str,
                "Regra de Descarte": motivo, "Código": codigo_original
            })
            continue

        # 2.2. Caso Especial: IBSRIC
        if is_ibsric_special and 'IBSRIC' in variaveis_encontradas:
            is_comment_or_literal = re.search(r'^\s*(;.*|//.*|#;.*|rem\s)|".*\bIBSRIC\b.*"', codigo_para_analise, re.IGNORECASE)
            if not is_comment_or_literal:
                resultados_ajustes.append({
                    "Arquivo": arquivo, "Linha": num_linha, "Variável": variaveis_str,
                    "Categoria": "CHAMADA_IBSRIC", "Padrão": "Chamada de Sub-rotina IBSRIC",
                    "Justificativa": "Chamada à sub-rotina para escopo de teste.", "Código": codigo_original
                })
                continue

        # 2.3. Regras de Ajuste Crítico
        vars_sem_ibsric = [v for v in variaveis_encontradas if v != 'IBSRIC']
        if vars_sem_ibsric:
            vars_regex_linha = r'\b(' + '|'.join(re.escape(v) for v in vars_sem_ibsric) + r')\b'
            for nome, regex, categoria, just in REGRAS_AJUSTE_CRITICO:
                regex_com_vars = regex.replace('VARIAVEL', vars_regex_linha)
                if re.search(regex_com_vars, codigo_para_analise, re.IGNORECASE):
                    resultados_ajustes.append({
                        "Arquivo": arquivo, "Linha": num_linha, "Variável": variaveis_str,
                        "Categoria": categoria, "Padrão": nome, "Justificativa": just, "Código": codigo_original
                    })
                    foi_classificada = True
                    break
        if foi_classificada: continue

        # 2.4. Regras de Descarte de Alta Confiança
        if vars_sem_ibsric:
            vars_regex_linha = r'\b(' + '|'.join(re.escape(v) for v in vars_sem_ibsric) + r')\b'
            for motivo, regex in REGRAS_DESCARTE_CONFIANCA:
                regex_com_vars = regex.replace('VARIAVEL', vars_regex_linha)
                if re.search(regex_com_vars, codigo_para_analise, re.IGNORECASE):
                    resultados_descartados.append({
                        "Arquivo": arquivo, "Linha": num_linha, "Variável": variaveis_str,
                        "Regra de Descarte": motivo, "Código": codigo_original
                    })
                    foi_classificada = True
                    break
        if foi_classificada: continue

        # 2.5. Padrão: Se chegou aqui e não é só IBSRIC, é revisão manual
        if vars_sem_ibsric:
            resultados_ajustes.append({
                "Arquivo": arquivo, "Linha": num_linha, "Variável": variaveis_str,
                "Categoria": "REVISAO_MANUAL", "Padrão": "Revisão Manual Necessária", 
                "Justificativa": "Não corresponde a nenhum padrão de ajuste ou descarte conhecido.",
                "Código": codigo_original
            })

    print(f"\nAnálise concluída.")
    print(f"  - Total de linhas únicas analisadas: {len(linhas_unicas)}")
    print(f"  - Pontos de ajuste crítico identificados: {len(resultados_ajustes)}")
    print(f"  - Itens descartados: {len(resultados_descartados)}")

    # Gerar Relatório de Ajustes Críticos
    if resultados_ajustes:
        df_ajustes = pd.DataFrame(resultados_ajustes)
        df_ajustes['Prefixo'] = df_ajustes['Arquivo'].str[:3].str.upper()
        df_ajustes['Classificação'] = df_ajustes['Arquivo'].apply(classificar_arquivo)
        colunas_ajustes = [
            "Arquivo", "Prefixo", "Classificação", "Linha", "Variável",
            "Categoria", "Padrão", "Justificativa", "Código"
        ]
        salvar_excel(df_ajustes, ARQUIVO_SAIDA_AJUSTES, colunas_ajustes)
        gerar_relatorio_precificacao_realista(df_ajustes)

    # Gerar Relatório de Descartes
    if resultados_descartados:
        df_descartados = pd.DataFrame(resultados_descartados)
        df_descartados['Prefixo'] = df_descartados['Arquivo'].str[:3].str.upper()
        df_descartados['Classificação'] = df_descartados['Arquivo'].apply(classificar_arquivo)
        colunas_descartes = [
            "Arquivo", "Prefixo", "Classificação", "Linha",
            "Variável", "Regra de Descarte", "Código"
        ]
        salvar_excel(df_descartados, ARQUIVO_SAIDA_DESCARTES, colunas_descartes)
        df_descartes_oficiais = df_descartados[df_descartados['Classificação'] == 'Oficiais'].copy()
        salvar_excel(df_descartes_oficiais, ARQUIVO_SAIDA_DESCARTES_OFICIAIS, colunas_descartes)

if __name__ == "__main__":
    main()