import os
import json
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from io import BytesIO
from src.backend.storage.storage import AzureDataLake
from src.backend.utils.logger_config import logger
from dotenv import load_dotenv

load_dotenv()

# Recupera as variáveis de ambiente
endpoint = os.getenv("AZURE_DOCUMENT_ENDPOINT")
key = os.getenv("AZURE_DOCUMENT_KEY")

# ID do classificador personalizado
classifier_id = "classify-ccr"

def classification(folder_name):
    
    if not endpoint or not key:
        raise logger.error("Certifique-se de que AZURE_DOCUMENT_ENDPOINT e AZURE_DOCUMENT_KEY estão configuradas corretamente.")

    # Inicializar Azure Data Lake
    datalake = AzureDataLake()

    # Listar arquivos do usuário no Data Lake
    files = datalake.get_files_names_from_adls()
    user_files = [f for f in files if f.startswith(folder_name) and f.endswith('.pdf')]

    if not user_files:
        raise FileNotFoundError("No PDF files found in the specified folder.")

    # Cria o cliente do Document Analysis
    client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    classification_content = ""
    for file_name in user_files:
        # Baixar o arquivo do Data Lake
        file_stream = BytesIO()
        datalake.download_file(file_name, file_stream)
        file_stream.seek(0)

        # Classificar o documento
        poller = client.begin_classify_document(classifier_id=classifier_id, document=file_stream)
        result = poller.result()

        # Construir o conteúdo do arquivo de classificação
        classification_content += f"Resultados da classificação para o arquivo: {file_name}\n"
        for analyzed_document in result.documents:
            classification_content += f"Tipo de Documento: {analyzed_document.doc_type}, Confiança: {analyzed_document.confidence:.2f}\n"

    classification_file_name = f"{folder_name}/classifications.txt"

    # Salvar o arquivo de classificação no Azure Data Lake
    classification_stream = BytesIO(classification_content.encode('utf-8'))
    datalake.upload_file_obj(classification_stream, classification_file_name)

    logger.info(f"Classification results generated and uploaded for file {file_name}")

    return f"Classifications generated successfully for folder {folder_name}."