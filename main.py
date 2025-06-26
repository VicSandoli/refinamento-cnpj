import re
import csv
import os

# --- CONFIGURAÇÃO ---

# 1. Coloque aqui o caminho do seu arquivo de entrada
ARQUIVO_ENTRADA = 'CNPJresults_findStudio 3.txt'

# 2. Nome do arquivo de saída que será gerado
ARQUIVO_SAIDA = 'analise_impacto_cnpj_refinada.csv'

# 3. Lista de variáveis a serem analisadas. Adicione todas as variáveis relevantes aqui.
# A busca não diferencia maiúsculas de minúsculas.
VARIAVEIS_ALVO = [
    'CGCC', 'CGCF', 'CCLI', 'CCSU', 'CGCS', 'CCLIP',
    'CNFO', 'CLIENTE', 'XCCLI', 'CodCliente', 'codigoCliente'
    # Adicione mais variáveis conforme a sua lista completa...
]

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
    """Verifica se a linha deve ser ignorada com base nas regras de descarte."""
    for regex in REGRAS_DE_DESCARTE:
        regex_var = regex.replace('VARIAVEL', var_alvo)
        if re.search(regex_var, codigo, re.IGNORECASE):
            return True
    return False

def main():
    print(f"Iniciando análise do arquivo: {ARQUIVO_ENTRADA}")
    
    if not os.path.exists(ARQUIVO_ENTRADA):
        print(f"ERRO: Arquivo de entrada não encontrado em '{ARQUIVO_ENTRADA}'")
        return

    # Compila um regex para encontrar qualquer uma das variáveis alvo
    variaveis_regex = r"\b(" + "|".join(VARIAVEIS_ALVO) + r")\b"
    
    linhas_analisadas = 0
    linhas_relevantes = 0
    
    # Usamos um dicionário para evitar duplicatas (mesma linha/arquivo/código)
    resultados_unicos = {}

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
            if deve_descartar(codigo, var_encontrada):
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

    # 3. Gravar resultados no CSV
    if resultados_unicos:
        with open(ARQUIVO_SAIDA, 'w', newline='', encoding='utf-8') as f_out:
            # Pega o cabeçalho do primeiro item do dicionário
            primeiro_item = next(iter(resultados_unicos.values()))
            writer = csv.DictWriter(f_out, fieldnames=primeiro_item.keys())
            
            writer.writeheader()
            
            # Ordena os resultados para um relatório mais limpo
            # Ordena por Risco (Alto->Médio->Baixo), depois por Complexidade (desc), depois por Arquivo e Linha
            ordem_risco = {"Alto": 0, "Médio": 1, "Baixo": 2}
            resultados_ordenados = sorted(
                resultados_unicos.values(), 
                key=lambda item: (
                    ordem_risco[item["Nível de Risco"]], 
                    -item["Complexidade (1-5)"], 
                    item["Arquivo"], 
                    int(item["Linha"])
                )
            )
            
            writer.writerows(resultados_ordenados)
        print(f"Relatório refinado salvo em: {ARQUIVO_SAIDA}")
    else:
        print("Nenhuma linha relevante encontrada com base nas regras.")

if __name__ == "__main__":
    main()