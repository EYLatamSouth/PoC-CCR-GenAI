import os
from flask import Blueprint, request, flash, redirect, url_for, render_template, session, jsonify, send_file
from src.backend.utils.utils import folders
from dotenv import load_dotenv
import datetime
from src.backend.storage.storage import AzureDataLake
from src.backend.utils.logger_config import logger
from src.backend.script.main import summarization
from io import BytesIO
from zipfile import ZipFile


load_dotenv()

bp = Blueprint("upload", __name__, template_folder=folders.TEMPLATES,
               static_folder=folders.STATIC)

@bp.route('/Upload', methods=['GET', 'POST'])
def upload():
    user = session.get('name')

    if not user:
        logger.info("User is not connected, redirecting to logout...")
        return redirect(url_for("auth.logout"))
    
    # Gerar o nome da pasta com base no usuário
    user_name = user.split("@")[0].lower().replace(".", "_")
    folder_name = f'Summ_{user_name}'

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file:
            data = datetime.datetime.now().strftime("%Y_%m_%d")
            nome_base, extensao = os.path.splitext(file.filename)
            # Definir o nome do objeto no Azure Data Lake (incluindo a "pasta")
            object_name = f'{folder_name}/{nome_base}_{data}{extensao}'

            # Fazer upload do arquivo para o Azure Data Lake diretamente da memória
            try:
                datalake = AzureDataLake()
                datalake.upload_file_obj(file, object_name)

                flash(f'Upload do {file.filename} feito com sucesso.', 'success')
                logger.info(f'File successfully uploaded to Azure Data Lake at {object_name}')
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                flash('Ocorreu um erro inesperado ao tentar fazer o upload. Tente novamente.', 'error')
            
            return redirect(url_for('upload.upload'))
    
    return render_template('upload/upload.html')


@bp.route('/generate_summary', methods=['POST'])
def generate_summary():
    user = session.get('name')
    if not user:
        logger.info("User is not connected, redirecting to logout...")
        return redirect(url_for("auth.logout"))
    
    user_name = user.split("@")[0].lower().replace(".", "_")
    folder_name = f"Summ_{user_name}"

    try:
        # Executar o processo de sumarização
        summarization(folder_name)
        logger.info(f"Summarization completed for folder: {folder_name}")

        return jsonify({'message': 'Summarization completed successfully!'}), 200
    except Exception as e:
        logger.error(f"Error during summarization: {e}")
        return jsonify({'message': 'Error during summarization'}), 500

    
@bp.route('/download_summaries', methods=['GET'])
def download_summaries():
    user = session.get('name')
    if not user:
        logger.info("User is not connected, redirecting to logout...")
        return redirect(url_for("auth.logout"))
    
    user_name = user.split("@")[0].lower().replace(".", "_")
    folder_name = f"Summ_{user_name}"

    try:
        # Inicializar o Azure Data Lake
        datalake = AzureDataLake()

        # Listar todos os arquivos de resumo (.txt) na pasta do usuário
        files = datalake.get_files_names_from_adls()
        summary_files = [f for f in files if f.startswith(folder_name) and f.endswith('.txt')]

        if not summary_files:
            logger.info(f"No summary files found in folder '{folder_name}'.")
            return jsonify({'message': 'No summaries available for download.'}), 404

        # Criar um arquivo ZIP contendo os arquivos .txt
        zip_stream = BytesIO()
        with ZipFile(zip_stream, 'w') as zip_file:
            for file_name in summary_files:
                file_stream = BytesIO()
                datalake.download_file(file_name, file_stream)
                file_stream.seek(0)
                zip_file.writestr(os.path.basename(file_name), file_stream.read())

        zip_stream.seek(0)

        # Excluir todos os arquivos da pasta e a pasta em si
        for file_name in summary_files:
            datalake.delete_file(file_name)
        logger.info(f"Deleted all summary files in folder '{folder_name}'.")

        return send_file(
            zip_stream,
            as_attachment=True,
            download_name="summaries.zip",
            mimetype="application/zip"
        )
    except Exception as e:
        logger.error(f"Error during download or deletion: {e}")
        return jsonify({'message': 'Error occurred during download or deletion.'}), 500

