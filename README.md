# Análise de Impacto de Refatoração de CNPJ

## 1. O Projeto

Este projeto foi desenvolvido para analisar e mitigar os riscos associados à refatoração de um sistema legado, onde o campo de CNPJ, originalmente numérico, precisava ser atualizado para suportar valores alfanuméricos.

## 2. O Desafio

A base de código é extensa e complexa, com mais de 180.000 linhas de código relevante. A análise manual para identificar todos os pontos de uso do CNPJ seria demorada, cara e com alta probabilidade de erro humano. O principal desafio era garantir que nenhuma funcionalidade fosse quebrada ou se comportasse de maneira inesperada após a mudança, o que poderia levar a bugs críticos em produção.

## 3. A Solução

Para enfrentar o desafio, foi implementada uma solução automatizada em duas partes, que permite uma análise rápida, precisa e iterativa de todo o código-fonte.

### 3.1. Script de Análise Inteligente (`main.py`)

O coração do projeto é um script Python que automatiza a análise de código. Ele opera da seguinte forma:

- **Entrada de Dados:** Utiliza um arquivo de log pré-gerado (`CNPJresults_findStudio 3.txt`) que contém todas as linhas de código onde as variáveis de CNPJ (`CNPJ 1.csv`) são mencionadas.
- **Motor de Regras:** Aplica um conjunto sofisticado e personalizável de regras de expressão regular (regex) para classificar cada ocorrência de código.
- **Sistema de Classificação:** Cada linha de código é categorizada em um dos três grupos:
    - 🔴 **Pontos de Impacto:** Código que será diretamente afetado pela mudança. É subdividido por nível de risco (Alto, Médio, Baixo) para priorização.
    - 🟢 **Itens Descartados:** Código onde a variável de CNPJ aparece, mas de forma segura (comentários, textos, atribuições simples), que pode ser ignorado.
    - 🟡 **Sem Classificação:** Ocorrências que não se encaixam em nenhuma regra e que podem exigir análise manual.
- **Geração de Relatórios:** Ao final, o script gera três relatórios detalhados em formato Excel (`.xlsx`), um para cada categoria, que servem como a base para a estimativa de esforço e o plano de ação.

### 3.2. Painel Gerencial Interativo (`dashboard.py`)

Para traduzir os dados técnicos em uma visão gerencial clara e acionável, foi desenvolvido um painel interativo com a biblioteca Streamlit.

- **Visualização de Dados:** O painel lê os relatórios `.xlsx` gerados pelo script de análise e os apresenta em um formato visualmente atraente e fácil de entender.
- **Métricas e Gráficos:** Exibe as métricas totais, gráficos de distribuição de risco, análise de impacto por tipo de módulo e os padrões de risco mais comuns.
- **Atualização Dinâmica:** O painel reflete automaticamente quaisquer atualizações nos arquivos de dados. Basta rodar o script de análise novamente para que a visualização seja atualizada.
- **Exploração Detalhada:** Permite que os gestores e desenvolvedores explorem os dados brutos de cada categoria diretamente na interface.

## 4. Como Utilizar

Siga os passos abaixo para executar a análise e visualizar o painel.

### Pré-requisitos
- Python 3.x instalado.

### Configuração
1.  **Variáveis:** Certifique-se de que o arquivo `CNPJ 1.csv` contém as variáveis de CNPJ a serem analisadas.
2.  **Código-Fonte:** O arquivo `CNPJresults_findStudio 3.txt` deve conter os resultados da busca (grep/find) no código-fonte.

### Passos de Execução

1.  **Instalar Dependências:**
    Abra um terminal na pasta do projeto e execute:
    ```bash
    python -m pip install -r requirements.txt
    ```

2.  **Executar a Análise de Código:**
    Este comando irá processar os dados e gerar os três relatórios `.xlsx`.
    ```bash
    python main.py
    ```

3.  **Visualizar o Painel Gerencial:**
    Após a análise ser concluída, inicie o servidor do painel.
    ```bash
    python -m streamlit run dashboard.py
    ```
    O painel será aberto automaticamente no seu navegador. 