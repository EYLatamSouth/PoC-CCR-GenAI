import os
from datetime import datetime
from dotenv import load_dotenv
from src.backend.utils.logger_config import logger
from azure.storage.blob import BlobServiceClient
import pandas as pd
from io import BytesIO

load_dotenv()

class AzureDataLake:
    """
    Implementação de armazenamento no Azure Data Lake.
    """

    def __init__(self):
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.container_name = os.getenv("AZURE_STORAGE_CONTAINER")
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    def get_files_names_from_adls(self):
        """
        Obtém os nomes de todos os arquivos no container do Azure Data Lake.

        Returns:
            list: Lista com os nomes dos arquivos.
        """
        files = []
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            blobs = container_client.list_blobs()
            for blob in blobs:
                files.append(blob.name)
        except Exception as e:
            logger.error(f"Error listing files: {e}")
        return files

    def upload_file_obj(self, file_obj, object_name):
        """
        Faz upload de um objeto de arquivo para o Azure Data Lake.

        Args:
            file_obj (file-like object): Objeto de arquivo a ser enviado.
            object_name (str): Nome do arquivo no armazenamento.
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=object_name)
            blob_client.upload_blob(file_obj, overwrite=True)
            logger.info("File successfully uploaded to Azure Data Lake.")
        except Exception as e:
            logger.error(f"Error uploading file: {e}")

    def upload_file(self, file, object_name):
        """
        Faz upload de um arquivo local para o Azure Data Lake.

        Args:
            file (str): Caminho para o arquivo local.
            object_name (str): Nome do arquivo no armazenamento.
        """
        try:
            with open(file, "rb") as file_data:
                self.upload_file_obj(file_data, object_name)
        except Exception as e:
            logger.error(f"Error uploading file: {e}")

    def download_file(self, object_name, file_stream):
        """
        Faz o download de um arquivo do Azure Data Lake para um objeto de arquivo em memória.

        Args:
            object_name (str): Nome do arquivo no armazenamento.
            file_stream (BytesIO): O objeto de arquivo em memória onde o conteúdo será armazenado.
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=object_name)
            download_stream = blob_client.download_blob()
            
            # Copiar o conteúdo do download para o objeto BytesIO
            download_stream.readinto(file_stream)
            file_stream.seek(0)  # Reinicia o cursor do BytesIO para o início

            logger.info(f"File {object_name} successfully downloaded into memory.")
        except Exception as e:
            logger.error(f"Error downloading file: {e}")


    def delete_file(self, object_name):
        """
        Exclui um arquivo do Azure Data Lake.

        Args:
            object_name (str): Nome do arquivo no armazenamento.
        """
        try:
            # Obtém o cliente do blob
            blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=object_name)
            # Exclui o arquivo
            blob_client.delete_blob()
            logger.info(f"File {object_name} successfully deleted from Azure Data Lake.")
        except Exception as e:
            logger.error(f"Error deleting file {object_name}: {e}")

    def read_excel(self, object_name, sheet_name=None):
        """
        Lê um arquivo Excel diretamente do Azure Data Lake.

        Args:
            object_name (str): Nome do arquivo no armazenamento.
            sheet_name (str): Nome da planilha no arquivo Excel (opcional).

        Returns:
            pd.DataFrame: DataFrame com os dados do arquivo Excel.
        """
        try:
            file_stream = BytesIO()
            self.download_file(object_name, file_stream)
            logger.info(f"Reading Excel file: {object_name}")
            return pd.read_excel(file_stream, sheet_name=sheet_name, engine='openpyxl')
        except Exception as e:
            logger.error(f"Error reading Excel file {object_name}: {e}")
            return pd.DataFrame()

    def extract_date_from_file_name(self, file_name):
        """
        Extrai a data do nome do arquivo baseado no padrão de nomeação.

        Args:
            file_name (str): O nome do arquivo.

        Returns:
            datetime: Um objeto datetime representando a data extraída do nome do arquivo.
        """
        aux = os.path.splitext('-'.join(file_name.split('_')[-3:]))[0]
        return datetime.strptime(aux, "%Y-%m-%d")

    def find_latest_file(self, file_list, item):
        """
        Encontra o arquivo mais recente em uma lista, filtrando pelo nome do item.

        Args:
            file_list (list): Lista de nomes de arquivos.
            item (str): O item a ser filtrado no nome dos arquivos.

        Returns:
            str: O nome do arquivo mais recente que contém o item especificado.
        """
        filtered_files = [file_name for file_name in file_list if item in file_name]
        sorted_files = sorted(filtered_files, key=lambda x: self.extract_date_from_file_name(x), reverse=True)

        if sorted_files:
            return sorted_files[0]
        else:
            return None