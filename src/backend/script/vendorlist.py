import pandas as pd
from unidecode import unidecode
from langchain.chains import ConversationChain
from src.backend.llm.azure_open_ai import create_azure_chat_llm
from src.backend.utils.maps import padronizar_telefone, validar_grupo
from src.backend.utils.logger_config import logger
from src.backend.storage.storage import AzureDataLake
from src.backend.utils.logger_config import logger
from dotenv import load_dotenv
from io import BytesIO
import json

load_dotenv()

# Configurar o modelo de LLM
llm = create_azure_chat_llm(temperature=0)
conversation = ConversationChain(llm=llm, verbose=True)

file = "BaseTeste_2024_12_11.XLSX"
file_mat = "MATERIAIS_SPOT_CURVA_A_B_C_2024_12_11.xlsx"

sheet = "Base Requisições 27.11"
sheet_gm = 'GMs'
sheet_mat = "MATERIAIS"
sheet_hist = "Base Histórico Compras"
sheet_forncedores = "Base Fornecedores"

def vendorlist(folder_name):
    datalake = AzureDataLake()
    files = datalake.get_files_names_from_adls()
    user_files = [f for f in files if f.startswith(folder_name) and f.endswith('.xlsx')]

    if not user_files:
        raise FileNotFoundError("No XLSX files found in the specified folder.")
    
    # Leitura dos arquivos Excel

    df = datalake.read_excel(f"{folder_name}\{file}", sheet_name=sheet)
    df_hist = datalake.read_excel(f"{folder_name}\{file}", sheet_name=sheet_hist)
    df_gm = datalake.read_excel(f"{folder_name}\{file}", sheet_name=sheet_gm)
    df_fornecedores = datalake.read_excel(f"{folder_name}\{file}", sheet_name=sheet_forncedores)
    df_mat = datalake.read_excel(f"{folder_name}\{file_mat}", sheet_name=sheet_mat)

    # Transformações nos dataframes
    df_fornecedores['Nº CNPJ'] = df_fornecedores['Nº CNPJ'].fillna(0).astype("int64").astype(str).str.zfill(14)
    df_fornecedores['Fornecedor'] = df_fornecedores['Fornecedor'].fillna(0).astype('int64')
    df_fornecedores['telefone'] = df_fornecedores['telefone'].apply(padronizar_telefone)
    df_hist[['CodigoFornecedor', 'CentroFornecedor']] = df_hist['Fornecedor/centro fornecedor'].str.split(n=1, expand=True)
    df_hist['CodigoFornecedor'] = df_hist['CodigoFornecedor'].fillna(0).astype('int64')
    df_hist_2 = df_hist[['CodigoFornecedor', 'Material', 'Grupo de mercadorias']].copy()

    df.columns = [unidecode(col).replace(" ", "_").replace(".", "_") for col in df.columns]
    df['Material'] = df['Material'].fillna(0).astype('int64')
    df_mat['MATERIAL'] = df_mat['MATERIAL'].astype('int64')
    df_mat_curva = df_mat[['MATERIAL', 'CURVA']].copy()

    df_merge = df.merge(df_mat_curva, left_on='Material', right_on='MATERIAL', how='left').drop(columns=['MATERIAL'])
    df_merge_b_c = df_merge[(df_merge.CURVA == 'B') | (df_merge.CURVA == 'C')].copy()
    df_merge_b_c_filtered = df_merge_b_c[df_merge_b_c.Urgencia_necessidade < 4].copy()

    df_merge_gm = df_merge_b_c_filtered.merge(df_gm, left_on='Grupo_de_mercadorias', right_on='GM', how='left').drop(columns=['GM'])
    df_merge_gm_filtered = df_merge_gm[df_merge_gm.Grupo.notna()].copy()

    lista_materiais = list(df_merge_gm_filtered.Material.unique())
    df_hist_2_filtered_by_material = df_hist_2[df_hist_2.Material.isin(lista_materiais)].copy()

    vendorlist_gm = {}
    for gm in df_hist_2_filtered_by_material['Grupo de mercadorias'].unique():
        filtered_hist = df_hist_2_filtered_by_material[df_hist_2_filtered_by_material['Grupo de mercadorias'] == gm]
        merged_df = filtered_hist.merge(
            df_fornecedores,
            left_on='CodigoFornecedor',
            right_on='Fornecedor',
            how='inner'
        )
        merged_df_2 = merged_df.rename(columns={
            'Nome 1': 'RAZÃO SOCIAL / NOME FANTASIA',
            'Nº CNPJ': 'CNPJ',
            'Fornecedor': 'CÓDIGO SAP',
            'Bloqueado por compliance': 'STATUS CADASTRO',
            'e-mail': 'E-MAIL',
            'telefone': 'TELEFONE'
        })[['RAZÃO SOCIAL / NOME FANTASIA', 'CNPJ', 'CÓDIGO SAP', 'STATUS CADASTRO', 'E-MAIL', 'TELEFONE']]

        final_df = merged_df_2.drop_duplicates()
        vendorlist_gm[gm] = final_df

    # Upload dos dataframes para o datalake
    for gm, df in vendorlist_gm.items():
        buffer = BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)

        file_name = f"{folder_name}/{gm}_vendorlist.xlsx"
        datalake.upload_file_obj(buffer, file_name)
        logger.info(f"File uploaded: {file_name}")

    return f"Vendorlist generated successfully for folder {folder_name}."

    # Agrupar por grupo e consolidar os textos
    # grupos = df_merge_gm_filtered.groupby('Grupo')['Texto_breve'].apply(list).reset_index()


    # grupos['Validacao'] = grupos.apply(lambda row: validar_grupo(conversation,row['Grupo'], row['Texto_breve']), axis=1)



