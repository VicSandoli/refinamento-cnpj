"""
Script para corrigir problemas de serialização de DataFrames no Streamlit
Executar antes do deploy para evitar erros do PyArrow
"""

import pandas as pd
import os

def fix_dataframe_types(df):
    """Converte colunas problemáticas para tipos compatíveis com Arrow"""
    df_fixed = df.copy()
    
    # Converter colunas object mistas para string
    for col in df_fixed.columns:
        if df_fixed[col].dtype == 'object':
            # Verificar se há mistura de tipos
            types_in_col = df_fixed[col].apply(type).unique()
            if len(types_in_col) > 1:
                df_fixed[col] = df_fixed[col].astype(str)
    
    # Converter float64 para float32 se possível
    for col in df_fixed.select_dtypes(include=['float64']).columns:
        df_fixed[col] = pd.to_numeric(df_fixed[col], downcast='float')
    
    # Converter int64 para int32 se possível  
    for col in df_fixed.select_dtypes(include=['int64']).columns:
        df_fixed[col] = pd.to_numeric(df_fixed[col], downcast='integer')
        
    return df_fixed

def main():
    """Corrige os arquivos Excel existentes"""
    arquivos_excel = [
        'analise_impacto_cnpj_refinada.xlsx',
        'analise_precificacao_proposta.xlsx', 
        'analise_descartes.xlsx',
        'analise_sem_classificacao.xlsx'
    ]
    
    for arquivo in arquivos_excel:
        if os.path.exists(arquivo):
            print(f"Corrigindo {arquivo}...")
            
            # Ler todas as planilhas
            try:
                xl_file = pd.ExcelFile(arquivo)
                with pd.ExcelWriter(arquivo, engine='openpyxl') as writer:
                    for sheet_name in xl_file.sheet_names:
                        df = pd.read_excel(arquivo, sheet_name=sheet_name)
                        df_fixed = fix_dataframe_types(df)
                        df_fixed.to_excel(writer, sheet_name=sheet_name, index=False)
                        
                print(f"✅ {arquivo} corrigido!")
                        
            except Exception as e:
                print(f"❌ Erro ao corrigir {arquivo}: {e}")
        else:
            print(f"⚠️ {arquivo} não encontrado")

if __name__ == "__main__":
    main() 