import os
from src.backend.storage.storage import AzureDataLake
from src.backend.utils.logger_config import logger
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from dotenv import load_dotenv
from io import BytesIO
from unidecode import unidecode
import re
import pandas as pd

load_dotenv()

endpoint = os.getenv("AZURE_DOCUMENT_ENDPOINT")
key = os.getenv("AZURE_DOCUMENT_KEY")

def ranking(folder_name):

    quantidade_map = {
        2104622: 144,
        2104623: 144,
        2104624: 60,
        2104625: 60,
        2104626: 922,
    }

    # Inicializar Azure Data Lake
    datalake = AzureDataLake()

    # Listar arquivos do usuário no Data Lake
    
    file_excelite = f'{folder_name}/excelite_.pdf'
    file_bold = f'{folder_name}/bold_.pdf'
     

    if (not file_excelite) or (not file_bold):
        raise FileNotFoundError("No PDF files found in the specified folder.")
    
    document_analysis_client = DocumentAnalysisClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )

    # Baixar o arquivo do Data Lake
    file_stream_excelite = BytesIO()
    datalake.download_file(file_excelite, file_stream_excelite)
    file_stream_excelite.seek(0)

    # Analisar o documento com o Azure Document Intelligence
    poller_excelite = document_analysis_client.begin_analyze_document(
        "prebuilt-layout", document=file_stream_excelite
    )
    result_excelite = poller_excelite.result()

    # List to hold table data
    tables_data_excelite = []

    for table_idx, table in enumerate(result_excelite.tables):
        print(
            "Table # {} has {} rows and {} columns".format(
            table_idx, table.row_count, table.column_count
            )
        )
        
        # Initialize a list for the current table
        table_data_excelite = [["" for _ in range(table.column_count)] for _ in range(table.row_count)]
        
        for cell in table.cells:
            table_data_excelite[cell.row_index][cell.column_index] = cell.content
        
        # Append the current table data to tables_data
        tables_data_excelite.append(table_data_excelite)

    # Convert the first table to a pandas DataFrame (assuming there's at least one table)
    if tables_data_excelite:
        df_excelite = pd.DataFrame(tables_data_excelite[0])
    else:
        print("No tables found in the document.")


    sentences_excelite = []
    for page in result_excelite.pages:
        lines = [unidecode(line.content).strip().lower() for line in page.lines]
        sentences_excelite.append(" ".join(lines))

    # Dicionário para armazenar os resultados
    dict_extract_excelite = {}

    # Regex para capturar os campos desejados
    pattern_excelite = r"delivery time\s*:\s*([\w\s\-.,]+)\.\s*2\. payment:\s*([\w\s\-.,%']+)"

    for sentence in sentences_excelite:
        # Procura os campos na string
        match = re.search(pattern_excelite, sentence, re.IGNORECASE)
        if match:
            prazo = match.group(1).strip()
            condicao = match.group(2).strip()
            frete = "Não informado"  # Frete não mencionado na string
            
            dict_extract_excelite = {
                "prazo": prazo,
                "condicao": condicao,
                "frete": frete
            }

    df_excelite = df_excelite.T.set_index(0).T

    # Deletar a primeira e a segunda linha
    df_excelite = df_excelite.iloc[2:].reset_index(drop=True)

    # Renomear as colunas "Unit Price" com as respectivas regras de negócio
    # Renomeando as três últimas colunas do DataFrame
    df_excelite.columns = list(df_excelite.columns[:-3]) + ['Price < 1000kg', 'Price 1000kg-3000kg', 'Price > 3000kg']

    last_three_cols = df_excelite.columns[-3:]

    # Alterar as colunas
    for col in last_three_cols:
        df_excelite[col] = df_excelite[col].apply(lambda x: x.replace('$', '')).astype(float) * 5.65

    df_excelite['Net Weight'] = df_excelite['Net Weight'].astype(float)
    df_excelite[['CodigoProduto', 'Material']] = df_excelite['Description'].str.split('/',n=1, expand=True)

    # Garantindo que a coluna "Material" seja do tipo inteiro
    df_excelite["Material"] = pd.to_numeric(df_excelite["Material"], errors="coerce").astype("Int64")

    df_excelite["Quantidade"] = df_excelite["Material"].map(quantidade_map)

    df_excelite['PesoTotal'] = df_excelite['Net Weight'] * df_excelite['Quantidade'] 

    df_excelite["ValorTotal"] = df_excelite.apply(calcular_valor_total, axis=1)
    df_excelite["ValorUnitario"] = df_excelite.apply(calcular_valor_unitario, axis=1)

    df_excelite["ValorTotalComImpostos"] = df_excelite["ValorTotal"]*1.8

    df_excelite = df_excelite.rename(columns={"Material":"MATERIAL"
                                   ,"ValorUnitario":"VALOR UNITÁRIO"
                                   ,"ValorTotalComImpostos":"VALOR TOTAL"})
    
    df_excelite_final = df_excelite[['MATERIAL','VALOR UNITÁRIO','VALOR TOTAL']].iloc[:-1].copy()

    df_excelite_final["PRAZO DE ENTREGA"] = dict_extract_excelite['prazo']
    df_excelite_final["Condição de Pagamento"] = dict_extract_excelite['condicao']
    df_excelite_final["Condição de Entrega"] = dict_extract_excelite['frete']
    df_excelite_final["FORNECEDOR"] = 'EXCELITE'

    # Baixar o arquivo do Data Lake
    file_stream_bold = BytesIO()
    datalake.download_file(file_bold, file_stream_bold)
    file_stream_bold.seek(0)

    # Analisar o documento com o Azure Document Intelligence
    poller_bold = document_analysis_client.begin_analyze_document(
        "prebuilt-layout", document=file_stream_bold
    )
    result_bold = poller_bold.result()

    # List to hold table data
    tables_data_bold = []

    for table_idx, table in enumerate(result_bold.tables):
        print(
            "Table # {} has {} rows and {} columns".format(
            table_idx, table.row_count, table.column_count
            )
        )
        
        # Initialize a list for the current table
        table_data_bold = [["" for _ in range(table.column_count)] for _ in range(table.row_count)]
        
        for cell in table.cells:
            table_data_bold[cell.row_index][cell.column_index] = cell.content
        
        # Append the current table data to tables_data
        tables_data_bold.append(table_data_bold)

    # Convert the first table to a pandas DataFrame (assuming there's at least one table)
    if tables_data_bold:
        df_bold = pd.DataFrame(tables_data_bold[0])
    else:
        print("No tables found in the document.")


    sentences_bold = []
    for page in result_bold.pages:
        lines = [unidecode(line.content).strip().lower() for line in page.lines]
        sentences_bold.append(" ".join(lines))

    # Dicionário para armazenar os resultados
    dict_extract_bold = {}

    # Regex para capturar os campos desejados
    pattern_bold = r"prazo entrega:\s*([\w\s]+)\s*cond\. pagamento:\s*([\w\s]+)\s*tipo de frete:\s*([\w\s]+)"

    for sentence in sentences_bold:
        match = re.search(pattern_bold, sentence, re.IGNORECASE)
        if match:
            prazo = match.group(1).strip().title()  # Formata para "A Combinar"
            condicao = match.group(2).strip().replace("dd", "dias").title()  # Substitui "dd" por "dias"
            frete = match.group(3).strip().upper()  # Coloca o frete em maiúsculas
            dict_extract_bold = {
                "prazo": prazo,
                "condicao": condicao,
                "frete": frete
            }
            break  # Para no primeiro match, caso haja várias strings
    
    df_bold = df_bold.T.set_index(0).T

    # Deletar a primeira e a segunda linha
    df_bold = df_bold.reset_index(drop=True)

    df_bold = df_bold[df_bold.Item.isin(['1','2','3','4','5'])]

    df_bold['Qtde'] = df_bold['Qtde'].apply(lambda x: x.replace('nas\n', '')).astype(float)
    df_bold['Preço Unitário'] = df_bold['Preço Unitário'].apply(lambda x: x.replace('.', '').replace(',', '.').replace(' ', '')).astype(float)
    df_bold['Valor Total'] = df_bold['Valor Total'].apply(lambda x: x.replace('.', '').replace(',', '.').replace(' ', '')).astype(float)

    df_bold["Código"] = pd.to_numeric(df_bold["Código"], errors="coerce").astype("Int64")

    df_bold = df_bold.rename(columns={"Código":"MATERIAL"
                          ,"Preço Unitário":"VALOR UNITÁRIO"
                          ,"Valor Total":"VALOR TOTAL"})

    df_bold_final = df_bold[['MATERIAL','VALOR UNITÁRIO','VALOR TOTAL']].copy()

    df_bold_final["PRAZO DE ENTREGA"] = dict_extract_bold['prazo']
    df_bold_final["Condição de Pagamento"] = dict_extract_bold['condicao']
    df_bold_final["Condição de Entrega"] = dict_extract_bold['frete']
    df_bold_final["FORNECEDOR"] = 'BOLD'

    # Supondo que df_final e df_final_2 já estão carregados
    # Concatene os dois dataframes
    df_concatenado = pd.concat([df_excelite_final, df_bold_final])

    # Remova duplicados mantendo o menor VALOR TOTAL
    df_resultante = df_concatenado.sort_values(by="VALOR TOTAL").drop_duplicates(subset="MATERIAL", keep="first")

    # Resete o índice para melhor visualização (opcional)
    df_resultante = df_resultante.reset_index(drop=True)

    buffer = BytesIO()
    df_resultante.to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)

    file_name = f"{folder_name}/rank.xlsx"
    datalake.upload_file_obj(buffer, file_name)
    logger.info(f"File uploaded: {file_name}")

    return f"Rank generated successfully for folder {folder_name}."

# Criando a coluna ValorTotal com base na regra fornecida
def calcular_valor_total(row):
    if row["PesoTotal"] < 1000:
        return round(row["Price < 1000kg"] * row["Quantidade"],2)
    elif 1000 <= row["PesoTotal"] <= 3000:
        return round(row["Price 1000kg-3000kg"] * row["Quantidade"],2)
    else:
        return round(row["Price > 3000kg"] * row["Quantidade"],2)
    
def calcular_valor_unitario(row):
    if row["PesoTotal"] < 1000:
        return round(row["Price < 1000kg"],2) 
    elif 1000 <= row["PesoTotal"] <= 3000:
        return round(row["Price 1000kg-3000kg"],2) 
    else:
        return round(row["Price > 3000kg"],2) 