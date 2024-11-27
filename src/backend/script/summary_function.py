import logging
import os
from azure.functions import HttpRequest, HttpResponse
from io import BytesIO
from zipfile import ZipFile
from backend.script.summary import summarization
from src.backend.storage.storage import AzureDataLake

def main(req: HttpRequest) -> HttpResponse:
    logging.info("Azure Function triggered to process PDF files.")
    
    try:
        # Ler arquivos do request
        files = req.files.values()
        if not files:
            return HttpResponse("No files provided", status_code=400)

        # Criar nome único para a pasta do usuário
        user_email = req.headers.get("x-user-email", "unknown_user")
        folder_name = f"Summ_{user_email.split('@')[0].lower().replace('.', '_')}"

        # Inicializar o Data Lake
        datalake = AzureDataLake()

        # Upload de arquivos
        uploaded_files = []
        for file in files:
            file_name = file.filename
            object_name = f"{folder_name}/{file_name}"
            datalake.upload_file_obj(file.stream, object_name)
            uploaded_files.append(object_name)

        # Realizar a sumarização
        summarization(folder_name)

        # Listar e baixar arquivos resumidos
        all_files = datalake.get_files_names_from_adls()
        summary_files = [
            f for f in all_files if f.startswith(folder_name) and f.endswith(".txt")
        ]
        pdf_files = [
            f for f in all_files if f.startswith(folder_name) and f.endswith(".pdf")
        ]

        if not summary_files:
            return HttpResponse("No summaries were generated.", status_code=500)

        # Criar ZIP dos arquivos resumidos
        zip_stream = BytesIO()
        with ZipFile(zip_stream, "w") as zip_file:
            for file_name in summary_files:
                file_stream = BytesIO()
                datalake.download_file(file_name, file_stream)
                file_stream.seek(0)
                zip_file.writestr(os.path.basename(file_name), file_stream.read())

        zip_stream.seek(0)

        # Excluir arquivos resumidos após o download
        for file_name in summary_files:
            datalake.delete_file(file_name)

        # Excluir arquivos PDF enviados após o processamento
        for file_name in pdf_files:
            datalake.delete_file(file_name)
        logging.info(f"Deleted all processed PDF files in folder '{folder_name}'.")

        # Retornar o arquivo ZIP
        return HttpResponse(
            zip_stream.read(),
            status_code=200,
            mimetype="application/zip",
            headers={"Content-Disposition": "attachment; filename=summaries.zip"},
        )
    except Exception as e:
        logging.error(f"Error processing files: {e}")
        return HttpResponse(f"Internal Server Error: {e}", status_code=500)
