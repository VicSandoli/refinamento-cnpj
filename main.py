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
ARQUIVO_SAIDA_DESCARTES_EXTRACAO = 'analise_descartes_extracao_simples.xlsx'
ARQUIVO_SAIDA_RESUMO = 'analise_resumo_criticos_oficiais.xlsx'

# 3. Arquivo com os termos de busca a serem analisados
ARQUIVO_TERMOS = 'CNPJ 1.csv'

# --- ATIVIDADES BASE DO PROJETO ---
# Esforços fixos para atividades que independem da contagem de pontos de código,
# refletindo o escopo completo do projeto de adequação ao CNPJ alfanumérico.
ATIVIDADES_BASE_PROJETO = {
    "GERENCIAMENTO_PROJETO": {
        "nome": "Gerenciamento e Planejamento",
        "esforco_dev": 120, "esforco_testes": 0,
        "descricao": "Coordenação, planejamento e acompanhamento das entregas do projeto."
    },
    "ANALISE_ARQUITETURA": {
        "nome": "Análise e Arquitetura da Solução (Especificação funcional)",
        "esforco_dev": 160, "esforco_testes": 0,
        "descricao": "Definição da arquitetura da solução, especificação funcional e detalhamento das regras de negócio para o CNPJ alfanumérico."
    },
    "ANALISE_PONTOS_CRITICOS": {
        "nome": "Análise preliminar para identificação de pontos a serem ajustados",
        "esforco_dev": 210, "esforco_testes": 0,
        "descricao": "Análise em bloco de todos os pontos de código impactados para categorização e definição das estratégias de refatoração."
    },
    "SOLUCAO_CENTRAL": {
        "nome": "Desenvolvimento da Solução Central para tratamento de código",
        "esforco_dev": 80, "esforco_testes": 40,
        "descricao": "Criação e testes unitários das funções centrais de validação, formatação e cálculo de DV."
    },
    "REFATORACAO_ROTINAS": {
        "nome": "Refatoração e ajustes de rotinas identificadas",
        "esforco_dev": 560, "esforco_testes": 240,
        "descricao": "Refatoração de todas as rotinas e pontos de código impactados, aplicando a solução central."
    },
    "AJUSTE_SUBROTINA_IBSRIC": {
        "nome": "Ajustes de subrotinas de validação (IBSRIC)",
        "esforco_dev": 40, "esforco_testes": 20,
        "descricao": "Refatoração específica do conjunto de sub-rotinas de validação (IBSRIC) para utilizar a nova solução central."
    },
    "AJUSTE_CODIGO_BARRAS": {
        "nome": "Ajustes de código de barras do DANFE",
        "esforco_dev": 60, "esforco_testes": 20,
        "descricao": "Implementação da migração do padrão de código de barras de CODE-128C para CODE-128A."
    },
    "AJUSTE_CHAVE_NFE": {
        "nome": "Ajustes de chave de acesso NFe",
        "esforco_dev": 100, "esforco_testes": 40,
        "descricao": "Ajuste na lógica de geração e validação da chave de acesso de Documentos Fiscais Eletrônicos."
    },
    "TESTES_IMPLANTACAO": {
        "nome": "Testes Finais e Implantação (Homologação e Go-Live)",
        "esforco_dev": 80, "esforco_testes": 100,
        "descricao": "Ciclo completo de testes integrados, suporte à homologação (UAT), apoio ao go-live e atividades de implantação em produção."
    }
}

# --- CATEGORIAS PARA AJUSTE DE CÓDIGO ---
# Custo marginal por ponto de código, representando o esforço mecânico de substituição.
# Esta seção é mantida para a classificação dos pontos no relatório de detalhamento, mas não é mais usada para o cálculo do esforço.
CATEGORIAS_AJUSTE_CODIGO = {
    "REFATORACAO_PONTUAL": {
        "nome": "Refatoração e ajustes de rotinas identificadas",
        "descricao": "Substituição do código legado por chamadas à nova solução central.",
        "esforco_dev_por_ponto": 0.0,  # Não utilizado para cálculo
        "esforco_testes_por_ponto": 0.0, # Não utilizado para cálculo
        "observacao": "Custo agora definido como um bloco fixo em ATIVIDADES_BASE_PROJETO."
    }
}

# --- REGRAS DE DESCARTE DE ALTA CONFIANÇA ---
# Se uma linha corresponder a qualquer uma destas regras, será descartada.
REGRAS_DESCARTE_CONFIANCA = [
    # Regra unificada para comentários que será verificada com uma exceção
    ("Comentário", r"^\s*(;+|//)"),
    # Novas regras para descartar definições de classes (.cls) que não são código executável
    ("Definição de Classe (Property, Parameter, etc.)", r"^\s*(Property|Parameter|Index|Method|Class|Relationship|Query|Trigger|ForeignKey)\s+"),
    ("Definição de Mapeamento XML/Storage", r"^\s*<(Sql|Data|Storage|Index|Stream|Map|Routine)"),
    ("Definição de Bloco XData", r"^\s*(XData|Import|Include)\s+"),
    # Movida para cima para ter prioridade sobre regras mais genéricas
    ("Extração Simples de Substring", r"(\$E|\$EXTRACT)\s*\(\s*\bVARIAVEL\b"),
    ("String Literal", r'".*\bVARIAVEL\b.*"'),
    # Novas regras para descartar usos simples em SQL que não representam risco
    ("Uso como Alias em SQL", r"\bAS\s+'?\bVARIAVEL\b'?,?"),
    ("Comparação Simples em SQL", r"(WHERE|ON)\s+.*\s*\bVARIAVEL\b\s*(=|LIKE)\s*.*|SET\s+.*\s*\bVARIAVEL\b\s*="),
    # Regra aprimorada para ser mais específica e evitar descartar atribuições que usam a variável
    ("Atribuição Simples (de variável)", r"^\s*(S|Set)\s+\w+\s*=\s*\bVARIAVEL\b\s*($|;|,|!)"),
    # Regra aprimorada para permitir atribuições complexas (com funções, métodos, etc.)
    ("Atribuição Simples (para variável)", r"^\s*(S|Set)\s+\bVARIAVEL\b\s*=\s*.*($|;|,|!)"),
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
        "Máscara Numérica Explícita", r"\?\d*N", "REFATORACAO_PONTUAL",
        "Máscara que força entrada numérica - precisa aceitar alfanumérico."
    ),
    (
        "Validação de Comprimento", r"\$L(ENGTH)?\s*\(\s*\bVARIAVEL\b.*\)\s*[=<>]\s*(11|14)", "REFATORACAO_PONTUAL",
        "Validação de tamanho fixo - precisa ser flexibilizada."
    ),
    (
        "Conversão/Operação Numérica", r"(\$NUMBER|\$ZSTRIP)\s*\(\s*\bVARIAVEL\b|\bVARIAVEL\b\s*[\+\-\*\/]\s*\d+|\d+\s*[\+\-\*\/]\s*\bVARIAVEL\b", "REFATORACAO_PONTUAL",
        "Conversão para número ou operação aritmética - falhará com alfanumérico."
    ),
    # --- LÓGICA DE NEGÓCIO ---
    (
        "Padding com Soma", r"(1000000\d{6,}\s*\+\s*\bVARIAVEL\b|\bVARIAVEL\b\s*\+\s*1000000\d{6,})", "REFATORACAO_PONTUAL",
        "Técnica de padding com soma para ordenação/comparação - incompatível com alfanumérico."
    ),
    (
        "Extração com Lógica Numérica ($E, $EXTRACT)", r"(\$E|\$EXTRACT)\s*\((?=[^)]*\+)[^)]*\bVARIAVEL\b[^)]*\)", "REFATORACAO_PONTUAL",
        "Extração de substring combinada com soma, indicando manipulação numérica."
    ),
    (
        "Parsing com $PIECE", r"\$P(IECE)?\s*\(\s*\bVARIAVEL\b", "REFATORACAO_PONTUAL",
        "Parsing da variável - pode ser afetado se o delimitador for um número."
    ),
    # --- FORMATAÇÃO E EXIBIÇÃO ---
    (
        "Formatação Manual para Exibição", r"(\bVARIAVEL\b\s*_\s*""[\.\/\-]"")|W(RITE)?\s+.*\bVARIAVEL\b", "REFATORACAO_PONTUAL",
        "Formatação manual para exibição - deve ser substituída por função central."
    ),
    # --- INTEGRAÇÃO E REVISÃO MANUAL ---
    (
        "Uso em Contexto de Integração", r"(HTTP|REST|SOAP|XML|JSON|EXPORT|IMPORT|FTP|FILE).*\bVARIAVEL\b", "REFATORACAO_PONTUAL",
        "Uso em contexto de integração. Requer análise manual da compatibilidade."
    ),
    # --- ESTRUTURA DE DADOS ---
    (
        "Uso em Operação de Banco", r"&(SQL|sql)\(.*\bVARIAVEL\b.*\)|(SELECT|INSERT|UPDATE|DELETE|WHERE|ORDER\s+BY).*\bVARIAVEL\b", "REFATORACAO_PONTUAL",
        "Operação de banco - verificar tipos de dados, índices e performance da consulta."
    ),
]


def carregar_termos_busca(caminho_csv):
    """Carrega os termos de busca e seus tipos de um arquivo CSV."""
    if not os.path.exists(caminho_csv):
        print(f"ERRO: Arquivo de termos '{caminho_csv}' não encontrado.")
        return {}
    try:
        df = pd.read_csv(caminho_csv, sep=';', usecols=['termo', 'tipo'], encoding='utf-8', on_bad_lines='skip')
        df.dropna(inplace=True)
        df['termo'] = df['termo'].astype(str).str.strip()
        df['tipo'] = df['tipo'].astype(str).str.strip()
        termos_dict = dict(zip(df['termo'], df['tipo']))
        print(f"{len(termos_dict)} termos de busca únicos carregados de {caminho_csv}")
        return termos_dict
    except Exception as e:
        print(f"ERRO ao ler o arquivo de termos '{caminho_csv}': {e}")
        return {}


def extrair_info_linha(linha):
    """Extrai o nome do arquivo, localizador e o código da linha de entrada."""
    # Regex aprimorada para lidar com formatos como:
    # arquivo(loc1): codigo
    # arquivo(loc1)[loc2]: codigo
    match = re.match(r"^(.*?)\((.*?)\)(.*?):\s*(.*)", linha)
    if match:
        arquivo, loc_parens, loc_brackets, codigo = match.groups()
        # Combina as partes do localizador para criar um identificador único
        localizador = loc_parens.strip() + loc_brackets.strip()
        return arquivo.strip(), localizador, codigo.strip()
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
    return "Revisão Manual Necessária", "REFATORACAO_PONTUAL", "Não corresponde a nenhum padrão de ajuste ou descarte conhecido.", "N/A"


def gerar_relatorio_precificacao_realista(df_ajustes):
    """Gera relatório de precificação realista baseado em blocos de trabalho com esforço fixo."""

    # --- INÍCIO DA LÓGICA DE CÁLCULO ---
    total_dev = 0
    total_testes = 0
    summary_atividades = []

    # 1. Adicionar Atividades Base do Projeto
    for _, config in ATIVIDADES_BASE_PROJETO.items():
        esforco_dev = config["esforco_dev"]
        esforco_testes = config["esforco_testes"]
        total_dev += esforco_dev
        total_testes += esforco_testes
        summary_atividades.append({
            "Frente de Trabalho": config["nome"],
            "Tipo": "Frente de Trabalho",
            "Pontos Identificados": "N/A",
            "Esforço Dev (h)": esforco_dev,
            "Esforço Testes (h)": esforco_testes,
            "Total (h)": esforco_dev + esforco_testes,
            "Observação": config["descricao"],
        })

    # Apenas para fins de relatório, contamos os pontos oficiais
    df_oficiais = pd.DataFrame()
    if not df_ajustes.empty:
        df_oficiais = df_ajustes[df_ajustes['Classificação'] == 'Oficiais'].copy()
    
    # 3. Gerar Sumário Executivo
    total_geral = total_dev + total_testes
    summary_executivo = [
        {"Métrica": "Esforço Desenvolvimento", "Valor": f"{total_dev}h"},
        {"Métrica": "Esforço Testes QA", "Valor": f"{total_testes}h"},
        {"Métrica": "Total Estimado", "Valor": f"{total_geral}h"},
        {"Métrica": "Estimativa com Buffer (15%)", "Valor": f"{round(total_geral * 1.15)}h"},
        {"Métrica": "Pontos Críticos (Oficiais)", "Valor": len(df_oficiais)},
        {"Métrica": "Rotinas Oficiais Impactadas", "Valor": df_oficiais['Arquivo'].nunique() if not df_oficiais.empty else 0},
    ]

    # 4. Salvar o relatório em Excel com múltiplas abas
    try:
        df_summary = pd.DataFrame(summary_atividades)
        with pd.ExcelWriter(ARQUIVO_SAIDA_PRECIFICACAO, engine='openpyxl') as writer:
            pd.DataFrame(summary_executivo).to_excel(writer, sheet_name='1_Summary_Executivo', index=False)
            df_summary.to_excel(writer, sheet_name='2_Estimativa_Detalhada', index=False)
            if not df_oficiais.empty:
                df_oficiais_detalhe = df_oficiais[['Arquivo', 'Localizador', 'Categoria', 'Padrão', 'Justificativa', 'Código']]
                df_oficiais_detalhe.to_excel(writer, sheet_name='3_Detalhe_Pontos_Oficiais', index=False)
        print(f"Relatório de precificação salvo em: {ARQUIVO_SAIDA_PRECIFICACAO}")
        print(f"   -> Total Estimado: {round(total_geral)}h | Com Buffer (15%): {round(total_geral * 1.15)}h")
    except Exception as e:
        print(f"ERRO ao salvar relatório de precificação: {e}")


def gerar_relatorio_resumo(df_ajustes, nome_arquivo):
    """Gera um relatório de resumo de pontos críticos por programa oficial."""
    if df_ajustes.empty:
        print("\nNenhum dado para gerar o relatório de resumo.")
        return

    df_oficiais = df_ajustes[df_ajustes['Classificação'] == 'Oficiais'].copy()
    if df_oficiais.empty:
        print("\nNenhuma rotina oficial encontrada para o resumo de pontos críticos.")
        return

    # Agrupar por arquivo e tipo, contar os pontos
    df_resumo = df_oficiais.groupby(['Arquivo', 'Tipo Programa']).size().reset_index(name='Pontos Críticos')
    
    # Ordenar por quantidade de pontos críticos
    df_resumo = df_resumo.sort_values(by='Pontos Críticos', ascending=False)
    
    try:
        df_resumo.to_excel(nome_arquivo, index=False, engine='openpyxl')
        print(f"Relatório de resumo salvo em: {nome_arquivo}")
    except Exception as e:
        print(f"ERRO ao salvar o arquivo de resumo '{nome_arquivo}': {e}")


def salvar_excel(df, nome_arquivo, colunas_ordem):
    """Função auxiliar para salvar DataFrames em Excel com formatação."""
    if df.empty:
        print(f"\nNenhum item para salvar em '{nome_arquivo}'.")
        return

    df_copy = df.copy()
    df_copy['Prefixo'] = df_copy['Arquivo'].str[:3].str.upper()
    df_copy['Classificação'] = df_copy['Arquivo'].apply(classificar_arquivo)
    
    # Ordenar para melhor visualização (sem conversão numérica)
    if "Categoria" in df_copy.columns:
        df_copy = df_copy.sort_values(by=['Classificação', 'Arquivo', 'Localizador'])
    else:
        df_copy = df_copy.sort_values(by=['Arquivo', 'Localizador'])

    colunas_presentes = df_copy.columns.tolist()
    colunas_finais = [col for col in colunas_ordem if col in colunas_presentes]
    df_final = df_copy[colunas_finais]

    try:
        df_final.to_excel(nome_arquivo, index=False, engine='openpyxl')
        print(f"Relatório salvo em: {nome_arquivo}")
    except Exception as e:
        print(f"ERRO ao salvar o arquivo '{nome_arquivo}': {e}")


def main():
    print("--- INICIANDO ANÁLISE DE IMPACTO DE CNPJ ALFANUMÉRICO (v5 - com tipo de termo) ---")

    termos_busca = carregar_termos_busca(ARQUIVO_TERMOS)
    if not termos_busca:
        return

    print(f"Analisando o arquivo: {ARQUIVO_ENTRADA}")
    if not os.path.exists(ARQUIVO_ENTRADA):
        print(f"ERRO: Arquivo de entrada não encontrado em '{ARQUIVO_ENTRADA}'")
        return

    # Etapa 1: Ler o arquivo de entrada e agrupar por linha de código única
    linhas_unicas = {}
    linhas_ignoradas = []
    print("Etapa 1: Lendo, buscando termos e agrupando linhas de código únicas...")
    with open(ARQUIVO_ENTRADA, 'r', encoding='utf-8', errors='ignore') as f_in:
        for linha_bruta in f_in:
            linha_strip = linha_bruta.strip()
            if "Searching for" in linha_strip or not linha_strip:
                continue

            arquivo, num_linha, codigo_original = extrair_info_linha(linha_strip)
            if not arquivo:
                linhas_ignoradas.append(f"Formato Inválido: {linha_strip}")
                continue

            codigo_para_analise = codigo_original # Analisar a linha inteira
            
            termos_encontrados_na_linha = {} # {termo: tipo}
            for termo, tipo in termos_busca.items():
                regex = ''
                # Sub-rotinas são buscadas como palavras completas para evitar falsos positivos
                if tipo == 'sub-rotina':
                    regex = r'\b' + re.escape(termo) + r'\b'
                # Variáveis e texto-livre podem ser parte de outra string
                elif tipo in ['variavel', 'texto-livre']:
                    regex = re.escape(termo)
                
                if regex and re.search(regex, codigo_para_analise, re.IGNORECASE):
                    termos_encontrados_na_linha[termo] = tipo
            
            if not termos_encontrados_na_linha:
                linhas_ignoradas.append(f"Nenhum Termo Encontrado: {linha_strip}")
                continue

            chave = (arquivo, num_linha)
            if chave not in linhas_unicas:
                linhas_unicas[chave] = {'code': codigo_original, 'terms': {}}
            
            linhas_unicas[chave]['terms'].update(termos_encontrados_na_linha)

    print(f"  - {len(linhas_unicas)} linhas de código únicas encontradas para análise.")
    print(f"  - {len(linhas_ignoradas)} linhas ignoradas (formato inválido ou sem termos).")

    # Salvar o relatório de linhas ignoradas
    if linhas_ignoradas:
        try:
            with open('analise_linhas_ignoradas.txt', 'w', encoding='utf-8') as f:
                for linha in sorted(linhas_ignoradas):
                    f.write(f"{linha}\n")
            print("Arquivo com linhas ignoradas salvo em: analise_linhas_ignoradas.txt")
        except Exception as e:
            print(f"ERRO ao salvar o arquivo de linhas ignoradas: {e}")

    # Etapa 2: Classificar cada linha de código única
    print("Etapa 2: Classificando cada linha...")
    resultados_ajustes = []
    resultados_descartados = []

    for (arquivo, num_linha), data in linhas_unicas.items():
        codigo_original = data['code']
        termos_encontrados = data['terms'] # É um dict {termo: tipo}
        codigo_para_analise = codigo_original # Usar a linha inteira para análise
        
        # Constrói a string de variáveis para o relatório
        variaveis_str = ", ".join(sorted(termos_encontrados.keys()))
        foi_classificada = False

        # --- LÓGICA DE CLASSIFICAÇÃO REESTRUTURADA ---
        
        # Etapa 1: Descartar comentários (prioridade máxima e sem exceções)
        if re.match(r"^\s*(;+|//)", codigo_para_analise):
            resultados_descartados.append({
                "Arquivo": arquivo, "Linha": num_linha, "Variável": variaveis_str,
                "Regra de Descarte": "Comentário", "Código": codigo_original
            })
            continue

        # Etapa 2: Descartar rotinas não oficiais ou scripts
        classificacao_arquivo = classificar_arquivo(arquivo)
        if classificacao_arquivo in ['Não Oficiais', 'Scripts']:
            motivo = "Rotina de Script" if classificacao_arquivo == 'Scripts' else "Rotina Não Oficial"
            resultados_descartados.append({
                "Arquivo": arquivo, "Linha": num_linha, "Variável": variaveis_str,
                "Regra de Descarte": motivo, "Código": codigo_original
            })
            continue
            
        # Etapa 3: Se não foi descartada, aplicar outras regras e classificações
        
        # Separa os termos encontrados por tipo para aplicar lógicas distintas
        vars_na_linha = [t for t, tipo in termos_encontrados.items() if tipo == 'variavel']
        subs_na_linha = [t for t, tipo in termos_encontrados.items() if tipo == 'sub-rotina']

        # 3.1: Lógica para Sub-rotinas
        if subs_na_linha:
            resultados_ajustes.append({
                "Arquivo": arquivo, "Linha": num_linha, "Variável": variaveis_str,
                "Categoria": "CHAMADA_SUBROTINA", "Padrão": "Chamada de Sub-rotina",
                "Justificativa": f"Chamada à(s) sub-rotina(s): {', '.join(sorted(subs_na_linha))}.", 
                "Código": codigo_original
            })
            foi_classificada = True
        
        # 3.2: Lógica para Variáveis (se houver e não tiver sido classificada como sub-rotina)
        if vars_na_linha and not foi_classificada:
            vars_regex_linha = r'\b(' + '|'.join(re.escape(v) for v in vars_na_linha) + r')\b'
            
            # Aplicar regras de DESCARTE restantes
            for motivo, regex in REGRAS_DESCARTE_CONFIANCA:
                if motivo == "Comentário": continue # Já foi tratado
                
                regex_com_vars = regex.replace('VARIAVEL', vars_regex_linha)
                if re.search(regex_com_vars, codigo_para_analise, re.IGNORECASE):
                    resultados_descartados.append({
                        "Arquivo": arquivo, "Linha": num_linha, "Variável": variaveis_str,
                        "Regra de Descarte": motivo, "Código": codigo_original
                    })
                    foi_classificada = True
                    break
            if foi_classificada: continue

            # Aplicar regras de AJUSTE CRÍTICO
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

        # Etapa 4: Padrão final -> Revisão Manual
        if not foi_classificada:
            justificativa = "Termo de texto-livre encontrado." if not vars_na_linha else "Não corresponde a nenhum padrão de ajuste ou descarte conhecido."
            resultados_ajustes.append({
                "Arquivo": arquivo, "Linha": num_linha, "Variável": variaveis_str,
                "Categoria": "REFATORACAO_PONTUAL", "Padrão": "Revisão Manual Necessária", 
                "Justificativa": justificativa,
                "Código": codigo_original
            })

    print(f"\nAnálise concluída.")
    print(f"  - Total de linhas únicas analisadas: {len(linhas_unicas)}")
    print(f"  - Pontos de ajuste crítico identificados: {len(resultados_ajustes)}")
    print(f"  - Itens descartados: {len(resultados_descartados)}")

    # Gerar Relatório de Ajustes Críticos
    if resultados_ajustes:
        df_ajustes = pd.DataFrame(resultados_ajustes)
        df_ajustes['Tipo Programa'] = df_ajustes['Arquivo'].str.split('.').str[-1]
        df_ajustes['Prefixo'] = df_ajustes['Arquivo'].str[:3].str.upper()
        df_ajustes['Classificação'] = df_ajustes['Arquivo'].apply(classificar_arquivo)
        colunas_ajustes = [
            "Arquivo", "Tipo Programa", "Prefixo", "Classificação", "Linha", "Variável",
            "Categoria", "Padrão", "Justificativa", "Código"
        ]
        df_ajustes.rename(columns={'Linha': 'Localizador'}, inplace=True)
        colunas_ajustes[4] = 'Localizador'
        salvar_excel(df_ajustes, ARQUIVO_SAIDA_AJUSTES, colunas_ajustes)
        gerar_relatorio_precificacao_realista(df_ajustes)
        gerar_relatorio_resumo(df_ajustes, ARQUIVO_SAIDA_RESUMO)

    # Gerar Relatório de Descartes
    if resultados_descartados:
        df_descartados = pd.DataFrame(resultados_descartados)
        df_descartados['Tipo Programa'] = df_descartados['Arquivo'].str.split('.').str[-1]
        df_descartados['Prefixo'] = df_descartados['Arquivo'].str[:3].str.upper()
        df_descartados['Classificação'] = df_descartados['Arquivo'].apply(classificar_arquivo)
        colunas_descartes = [
            "Arquivo", "Tipo Programa", "Prefixo", "Classificação", "Linha",
            "Variável", "Regra de Descarte", "Código"
        ]
        df_descartados.rename(columns={'Linha': 'Localizador'}, inplace=True)
        colunas_descartes[4] = 'Localizador'
        salvar_excel(df_descartados, ARQUIVO_SAIDA_DESCARTES, colunas_descartes)
        df_descartes_oficiais = df_descartados[df_descartados['Classificação'] == 'Oficiais'].copy()
        salvar_excel(df_descartes_oficiais, ARQUIVO_SAIDA_DESCARTES_OFICIAIS, colunas_descartes)

        # Salvar o relatório específico de descarte por extração simples
        df_extracao_simples = df_descartados[df_descartados['Regra de Descarte'] == 'Extração Simples de Substring'].copy()
        salvar_excel(df_extracao_simples, ARQUIVO_SAIDA_DESCARTES_EXTRACAO, colunas_descartes)

if __name__ == "__main__":
    main()