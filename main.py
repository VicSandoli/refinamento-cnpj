import re
import csv
import os
import pandas as pd

# --- CONFIGURAÇÃO ---

# 1. Coloque aqui o caminho do seu arquivo de entrada
ARQUIVO_ENTRADA = 'CNPJresults_findStudio 3.txt'

# 2. Nome do arquivo de saída que será gerado
ARQUIVO_SAIDA = 'analise_impacto_cnpj_refinada.xlsx'

# 3. Arquivo com as variáveis a serem analisadas
ARQUIVO_VARIAVEIS = 'CNPJ 1.csv'

# --- REGRAS DE ANÁLISE (O CÉREBRO DO SCRIPT) ---

# Regras são aplicadas em ordem. A primeira que corresponder, classifica a linha.
# A estrutura é: (Nome da Regra, Padrão Regex, Nível de Risco, Pontos de Complexidade, Justificativa)

REGRAS_DE_RISCO = [
    # --- RISCO ALTO ---
    (
        "Operação Aritmética",
        r"\bVARIAVEL\b\s*\+|\+\s*\bVARIAVEL\b|\bVARIAVEL\b\s*\*|\*\s*\bVARIAVEL\b|\bVARIAVEL\b\s*\/|\/\s*\bVARIAVEL\b",
        "Alto", 5,
        "Tentativa de usar a variável em uma operação matemática. Quebra de sintaxe garantida com valor alfanumérico."
    ),
    (
        "Máscara Numérica Explícita",
        r"\?\d*N",
        "Alto", 4,
        "Uso do operador de padrão 'N' (?N, ?14N), que valida estritamente caracteres numéricos."
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
        r"\$O\s*\(\s*\^[A-Z0-9.]+.*\bVARIAVEL\b",
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
        r"\bVARIAVEL\b\s*_\s*""[\./-]""",
        "Baixo", 1,
        "Concatenação manual de '.', '/' ou '-'. Código deve ser refatorado para usar uma função de formatação central."
    ),
]

# Regras para descartar linhas (ruído) antes de aplicar as regras de risco.
REGRAS_DE_DESCARTE = [
    r"^\s*;",  # Linha é um comentário
    r"\brem\b", # Linha contém 'rem' (provavelmente comentário ou mensagem)
    r"New\s+.*\bVARIAVEL\b", # Declaração New
    r"S\s*\(?.*\bVARIAVEL\b.*\)?\s*=\s*""""", # Inicialização para vazio/nulo
    r"Set\s+\bVARIAVEL\b\s*=\s*""""", # Set para vazio/nulo
    r"if\s+\bVARIAVEL\b\s*=\s*""""", # Comparação com vazio/nulo
    r"if\s+\bVARIAVEL\b\s*'\s*=\s*""""", # Comparação com vazio/nulo
    r"if\s+\$G\(\bVARIAVEL\b", # Verificação com $GET
    r"G:\bVARIAVEL\b\?1""""", # GOTO se a variável for nula
    r"Write\s+.*/CAMPO\s*\(", # Escrita em campo de tela (geralmente não requer lógica de validação)
    r"Set\s+.*\s*=\s*##class\(", # Chamadas de método de classe (a lógica está na classe, não aqui)
    r"\.cpfcnpj\s*=", # Atribuição a uma propriedade de objeto (a lógica está no setter do objeto)
    r"\$E\s*\(\s*\bVARIAVEL\b", # Extração de substring
    r"\$EXTRACT\s*\(\s*\bVARIAVEL\b", # Extração de substring
    r"\$O\s*\(\s*\^[A-Z0-9.]+.*\bVARIAVEL\b", # Uso como subscrito em um laço $ORDER
    r"if\s+\bVARIAVEL\b\s*[=<>]\s*\d+", # Comparação direta com um número
    r"\bVARIAVEL\b\s*_\s*""[\./-]""", # Concatenação manual de '.', '/' ou '-'
]


def carregar_variaveis_alvo(caminho_csv):
    """
    Carrega dinamicamente as variáveis de um arquivo CSV.
    Assume que o delimitador é ';' e as variáveis estão na 5ª coluna (índice 4).
    Filtra para manter apenas nomes de variáveis válidos (ignora números, etc.).
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

def analisar_codigo(codigo, var_alvo):
    """Aplica as regras de risco ao código e retorna a primeira correspondência."""
    for nome, regex, risco, pontos, just in REGRAS_DE_RISCO:
        # Substitui o placeholder 'VARIAVEL' pela variável real
        regex_var = regex.replace('VARIAVEL', var_alvo)
        if re.search(regex_var, codigo, re.IGNORECASE):
            return nome, risco, pontos, just
    return None

def deve_descartar(codigo, var_alvo):
    """
    Verifica se a linha deve ser ignorada com base nas regras de descarte.
    Retorna a regra que causou o descarte, ou None se nenhuma regra corresponder.
    """
    for regex in REGRAS_DE_DESCARTE:
        regex_var = regex.replace('VARIAVEL', var_alvo)
        if re.search(regex_var, codigo, re.IGNORECASE):
            return regex  # Retorna a regra que deu match
    return None

def main():
    print("--- INICIANDO ANÁLISE DE IMPACTO DE CNPJ ALFANUMÉRICO ---")
    
    # Carrega as variáveis alvo dinamicamente
    VARIAVEIS_ALVO = carregar_variaveis_alvo(ARQUIVO_VARIAVEIS)
    if not VARIAVEIS_ALVO:
        print("Nenhuma variável alvo para analisar. Encerrando.")
        return
        
    print(f"Iniciando análise do arquivo de código: {ARQUIVO_ENTRADA}")
    
    if not os.path.exists(ARQUIVO_ENTRADA):
        print(f"ERRO: Arquivo de entrada não encontrado em '{ARQUIVO_ENTRADA}'")
        return

    # Compila um regex para encontrar qualquer uma das variáveis alvo
    variaveis_regex = r"\b(" + "|".join(re.escape(var) for var in VARIAVEIS_ALVO) + r")\b"
    
    linhas_analisadas = 0
    linhas_relevantes = 0
    
    # Usamos um dicionário para evitar duplicatas (mesma linha/arquivo/código)
    resultados_unicos = {}
    # Lista para armazenar os itens descartados para revisão
    resultados_descartados = []

    with open(ARQUIVO_ENTRADA, 'r', encoding='utf-8', errors='ignore') as f_in:
        for linha_bruta in f_in:
            linhas_analisadas += 1
            
            # Pula linhas de cabeçalho ou vazias
            if "Searching for" in linha_bruta or not linha_bruta.strip():
                continue

            arquivo, num_linha, codigo = extrair_info_linha(linha_bruta.strip())
            
            if not arquivo:
                continue
            
            # Encontra qual variável alvo está na linha
            match_var = re.search(variaveis_regex, codigo, re.IGNORECASE)
            if not match_var:
                continue
                
            var_encontrada = match_var.group(0)

            # 1. Aplicar filtro de descarte
            regra_descarte_aplicada = deve_descartar(codigo, var_encontrada)
            if regra_descarte_aplicada:
                resultados_descartados.append({
                    "Arquivo": arquivo,
                    "Linha": num_linha,
                    "Variável": var_encontrada.upper(),
                    "Regra de Descarte": regra_descarte_aplicada,
                    "Código": codigo.strip()
                })
                continue
            
            # 2. Aplicar regras de risco
            resultado_analise = analisar_codigo(codigo, var_encontrada)
            
            if resultado_analise:
                linhas_relevantes += 1
                regra, risco, pontos, just = resultado_analise
                
                # Chave única para evitar duplicatas
                chave = (arquivo, num_linha, codigo)
                if chave not in resultados_unicos:
                    resultados_unicos[chave] = {
                        "Arquivo": arquivo,
                        "Linha": num_linha,
                        "Variável": var_encontrada.upper(),
                        "Nível de Risco": risco,
                        "Complexidade (1-5)": pontos,
                        "Padrão de Risco": regra,
                        "Justificativa / Ação Recomendada": just,
                        "Código": codigo.strip()
                    }

    print(f"\nAnálise concluída.")
    print(f"Total de linhas lidas: {linhas_analisadas}")
    print(f"Total de pontos de atenção identificados: {len(resultados_unicos)}")

    # 3. Gravar resultados no Excel
    if resultados_unicos:
        # Converte o dicionário de resultados em uma lista de dicionários
        lista_resultados = list(resultados_unicos.values())
        
        # Cria um DataFrame do Pandas
        df = pd.DataFrame(lista_resultados)

        # --- Adicionar novas colunas de classificação ---
        prefixos_oficiais = [
            'dd', 'gap', 'i', 'audit', 'autobasi', 'basico', 'br', 'cbpi', 'csp',
            'estoque', 'faturamento', 'fiscal', 'frete', 'gem', 'ipi', 'ipp',
            'mnemonic', 'precos', 'sistema', 'supervisao', 'tropical', 'tti'
        ]

        def classificar_arquivo(nome_arquivo):
            nome_arquivo_lower = nome_arquivo.lower()
            # 1. 'ABA' é o mais específico, checar primeiro
            if nome_arquivo_lower.startswith('aba'):
                return 'Scripts'
            
            # 2. Checar a lista de prefixos oficiais
            for prefixo in prefixos_oficiais:
                if nome_arquivo_lower.startswith(prefixo):
                    return 'Oficiais'
            
            # 3. Se não for nenhum dos anteriores, é Não Oficial
            return 'Não Oficiais'
        
        df['Prefixo'] = df['Arquivo'].str[:3].str.upper()
        df['Classificação'] = df['Arquivo'].apply(classificar_arquivo)


        # --- Ordenação ---
        # Adiciona colunas temporárias para ordenação complexa
        ordem_risco = {"Alto": 0, "Médio": 1, "Baixo": 2}
        df['OrdemRisco'] = df['Nível de Risco'].map(ordem_risco)
        # Converte a coluna 'Linha' para numérico para ordenar corretamente
        df['LinhaInt'] = pd.to_numeric(df['Linha'])
        
        # Ordena o DataFrame
        df_ordenado = df.sort_values(
            by=['OrdemRisco', 'Complexidade (1-5)', 'Arquivo', 'LinhaInt'],
            ascending=[True, False, True, True]
        )
        
        # --- Organiza a ordem final das colunas ---
        colunas_finais = [
            "Arquivo", "Prefixo", "Classificação", "Linha", "Variável", 
            "Nível de Risco", "Complexidade (1-5)", "Padrão de Risco", 
            "Justificativa / Ação Recomendada", "Código"
        ]
        df_final = df_ordenado[colunas_finais]


        # Salva o DataFrame em um arquivo Excel
        try:
            df_final.to_excel(ARQUIVO_SAIDA, index=False, engine='openpyxl')
            print(f"Relatório refinado e com classificação salvo em: {ARQUIVO_SAIDA}")
        except Exception as e:
            print(f"ERRO ao salvar o arquivo Excel: {e}")
            print("Por favor, certifique-se de que a biblioteca 'openpyxl' está instalada.")
            print("Você pode instalá-la com: pip install pandas openpyxl")
    else:
        print("Nenhuma linha relevante encontrada com base nas regras.")

    # 4. Gravar resultados dos itens descartados
    if resultados_descartados:
        ARQUIVO_SAIDA_DESCARTES = 'analise_descartes.xlsx'
        print(f"\nEncontrados {len(resultados_descartados)} itens descartados. Gerando relatório de descarte...")

        df_descartados = pd.DataFrame(resultados_descartados)
        
        # Reutiliza a lógica de classificação de arquivos
        df_descartados['Prefixo'] = df_descartados['Arquivo'].str[:3].str.upper()
        df_descartados['Classificação'] = df_descartados['Arquivo'].apply(classificar_arquivo)

        # Ordena por arquivo e linha
        df_descartados['LinhaInt'] = pd.to_numeric(df_descartados['Linha'])
        df_descartados = df_descartados.sort_values(by=['Arquivo', 'LinhaInt']).drop(columns=['LinhaInt'])

        # Organiza a ordem das colunas
        colunas_descartes = [
            "Arquivo", "Prefixo", "Classificação", "Linha", 
            "Variável", "Regra de Descarte", "Código"
        ]
        df_descartados_final = df_descartados[colunas_descartes]

        try:
            df_descartados_final.to_excel(ARQUIVO_SAIDA_DESCARTES, index=False, engine='openpyxl')
            print(f"Relatório de itens descartados salvo em: {ARQUIVO_SAIDA_DESCARTES}")
        except Exception as e:
            print(f"ERRO ao salvar o arquivo de descartes: {e}")
    else:
        print("\nNenhum item foi descartado pelas regras de filtro.")

if __name__ == "__main__":
    main()