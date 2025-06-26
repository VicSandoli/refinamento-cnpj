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

# 3. Arquivo com as variáveis a serem analisadas
ARQUIVO_VARIAVEIS = 'CNPJ 1.csv'

# --- REGRAS DE ANÁLISE (O CÉREBRO DO SCRIPT) ---

# REGRAS GLOBAIS: Verificadas em TODAS as linhas. A primeira que corresponder, classifica a linha.
REGRAS_GLOBAIS_RISCO = [
    (
        "Máscara Numérica Explícita",
        r"\?\d*N",
        "Alto", 4,
        "Uso do operador de padrão 'N' (?N, ?14N), que valida estritamente caracteres numéricos."
    ),
]

# REGRAS VINCULADAS: Verificadas apenas em linhas que contêm uma variável alvo.
REGRAS_VINCULADAS_RISCO = [
    # --- RISCO ALTO ---
    (
        "Operação Aritmética",
        r"\bVARIAVEL\b\s*\+\s*|\s*\+\s*\bVARIAVEL\b|\bVARIAVEL\b\s*\*\s*|\s*\*\s*\bVARIAVEL\b|\bVARIAVEL\b\s*\/|\/\s*\bVARIAVEL\b",
        "Alto", 5,
        "Tentativa de usar a variável em uma operação matemática. Quebra de sintaxe garantida com valor alfanumérico."
    ),
    (
        "Função Numérica ($NUMBER)",
        r"\$NUMBER\s*\(\s*\bVARIAVEL\b",
        "Alto", 4,
        "Conversão explícita para número. Falhará com valor alfanumérico."
    ),
    # --- RISCO MÉDIO ---
    (
        "Manipulação de Estrutura Fixa ($E, $EXTRACT)",
        r"(\$E|\$EXTRACT)\s*\(\s*\bVARIAVEL\b",
        "Médio", 3,
        "Extração de substring. A lógica pode estar incorreta para o novo formato de CNPJ (ex: raiz não tem mais 8 ou 12 caracteres)."
    ),
    (
        "Uso em $ORDER",
        r"\$O\s*\(\s*\^[A-Z0-9\.]+.*\bVARIAVEL\b",
        "Médio", 2,
        "Uso como subscrito em um laço $ORDER. A ordem de processamento será alterada de numérica para alfanumérica, impactando relatórios e processos."
    ),
    (
        "Comparação com Número",
        r"if\s+\bVARIAVEL\b\s*[=<>]\s*\d+",
        "Médio", 3,
        "Comparação direta com um número. Pode levar a comportamento incorreto, pois um CNPJ alfanumérico será avaliado como 0."
    ),
    # --- RISCO BAIXO ---
    (
        "Formatação Manual para Exibição",
        r'\bVARIAVEL\b\s*_\s*"[\./-]"',  # CORRIGIDO: usando aspas simples para delimitar
        "Baixo", 1,
        "Concatenação manual de '.', '/' ou '-'. Código deve ser refatorado para usar uma função de formatação central."
    ),
]

# REGRAS DE DESCARTE: Também são vinculadas a uma variável.
REGRAS_VINCULADAS_DESCARTE = [
    (r"^\s*;", "Comentário"),
    (r"\brem\b", "Comentário 'rem'"),
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
    (r"if\s+\$E\(\bVARIAVEL\b", "Uso em $E/$EXTRACT (ignorado se já tratado como risco)"),
    (r"if\s+\$EXTRACT\(\bVARIAVEL\b", "Uso em $E/$EXTRACT (ignorado se já tratado como risco)"),
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
    """Aplica as regras de risco globais ao código."""
    for nome, regex, risco, pontos, just in REGRAS_GLOBAIS_RISCO:
        if re.search(regex, codigo, re.IGNORECASE):
            return nome, risco, pontos, just, regex
    return None

def analisar_regras_vinculadas(codigo, var_alvo):
    """Aplica as regras de risco vinculadas a uma variável específica."""
    for nome, regex, risco, pontos, just in REGRAS_VINCULADAS_RISCO:
        regex_var = regex.replace('VARIAVEL', var_alvo)
        if re.search(regex_var, codigo, re.IGNORECASE):
            return nome, risco, pontos, just
    return None

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

            arquivo, num_linha, codigo = extrair_info_linha(linha_bruta.strip())
            if not arquivo:
                continue

            foi_classificada = False

            # 1. Análise de Regras Globais (maior prioridade)
            resultado_global = analisar_regras_globais(codigo)
            if resultado_global:
                regra, risco, pontos, just, padrao = resultado_global
                resultados_impacto.append({
                    "Arquivo": arquivo, "Linha": num_linha, "Variável": f"Padrão Global: {padrao}",
                    "Nível de Risco": risco, "Complexidade (1-5)": pontos,
                    "Padrão de Risco": regra, "Justificativa / Ação Recomendada": just,
                    "Código": codigo
                })
                foi_classificada = True

            # 2. Análise Vinculada a Variável (se não classificada globalmente)
            if not foi_classificada:
                match_var = re.search(variaveis_regex, codigo, re.IGNORECASE)
                if match_var:
                    var_encontrada = match_var.group(0)

                    # 2a. Checar Descarte
                    motivo_descarte = checar_descarte_vinculado(codigo, var_encontrada)
                    if motivo_descarte:
                        resultados_descartados.append({
                            "Arquivo": arquivo, "Linha": num_linha, "Variável": var_encontrada.upper(),
                            "Regra de Descarte": motivo_descarte, "Código": codigo
                        })
                        foi_classificada = True
                    else:
                        # 2b. Checar Risco Vinculado
                        resultado_risco = analisar_regras_vinculadas(codigo, var_encontrada)
                        if resultado_risco:
                            regra, risco, pontos, just = resultado_risco
                            resultados_impacto.append({
                                "Arquivo": arquivo, "Linha": num_linha, "Variável": var_encontrada.upper(),
                                "Nível de Risco": risco, "Complexidade (1-5)": pontos,
                                "Padrão de Risco": regra, "Justificativa / Ação Recomendada": just,
                                "Código": codigo
                            })
                            foi_classificada = True

            # 3. Coletar itens não classificados que contêm variáveis
            if not foi_classificada:
                match_var = re.search(variaveis_regex, codigo, re.IGNORECASE)
                if match_var:
                    resultados_sem_classificacao.append({
                        "Arquivo": arquivo, "Linha": num_linha,
                        "Variável Encontrada": match_var.group(0).upper(),
                        "Código": codigo
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
        if "Nível de Risco" in df_copy.columns:
            ordem_risco = {"Alto": 0, "Médio": 1, "Baixo": 2}
            df_copy['OrdemRisco'] = df_copy['Nível de Risco'].map(ordem_risco)
            df_copy = df_copy.sort_values(by=['OrdemRisco', 'Complexidade (1-5)', 'Arquivo', 'LinhaInt'], ascending=[True, False, True, True])
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
            "Nível de Risco", "Complexidade (1-5)", "Padrão de Risco",
            "Justificativa / Ação Recomendada", "Código"
        ]
        salvar_excel(df_impacto, ARQUIVO_SAIDA_IMPACTO, colunas_impacto)

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