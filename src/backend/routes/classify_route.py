import os
import datetime
from flask import Blueprint, request, session, jsonify, send_file, redirect, url_for, flash, render_template
from src.backend.utils.utils import folders
from src.backend.storage.storage import AzureDataLake
from src.backend.utils.logger_config import logger
from src.backend.script.classify import classification
from io import BytesIO
from zipfile import ZipFile

bp = Blueprint("classify", __name__, template_folder=folders.TEMPLATES)

@bp.route('/upload_classify', methods=['GET', 'POST'])
def upload_classify():
    user = session.get('name')
    if not user:
        logger.info("User is not connected, redirecting to logout...")
        return redirect(url_for("auth.logout"))

    user_name = user.split("@")[0].lower().replace(".", "_")
    folder_name = f'Classify_{user_name}'

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
            
            return redirect(url_for('classify.upload_classify'))
    
    return render_template('agents/classify.html')


@bp.route('/generate_classification', methods=['POST'])
def generate_classification():
    user = session.get('name')
    if not user:
        logger.info("User is not connected, redirecting to logout...")
        return redirect(url_for("auth.logout"))

    user_name = user.split("@")[0].lower().replace(".", "_")
    folder_name = f"Classify_{user_name}"

    try:
        classification(folder_name)
        logger.info(f"Classification completed for folder: {folder_name}")
        return jsonify({'message': 'Classification completed successfully!'}), 200
    except Exception as e:
        logger.error(f"Error during classification: {e}")
        return jsonify({'message': 'Error during classification'}), 500

@bp.route('/download_classifications', methods=['GET'])
def download_classifications():
    user = session.get('name')
    if not user:
        logger.info("User is not connected, redirecting to logout...")
        return redirect(url_for("auth.logout"))

    user_name = user.split("@")[0].lower().replace(".", "_")
    folder_name = f"Classify_{user_name}"

    try:
        datalake = AzureDataLake()
        files = datalake.get_files_names_from_adls()
        class_files = [f for f in files if f.startswith(folder_name) and f.endswith('.txt')]
        pdf_files = [f for f in files if f.startswith(folder_name) and f.endswith(".pdf")]

        if not class_files:
            logger.info(f"No classification files found in folder '{folder_name}'.")
            return jsonify({'message': 'No classifications available for download.'}), 404

        zip_stream = BytesIO()
        with ZipFile(zip_stream, 'w') as zip_file:
            for file_name in class_files:
                file_stream = BytesIO()
                datalake.download_file(file_name, file_stream)
                file_stream.seek(0)
                zip_file.writestr(os.path.basename(file_name), file_stream.read())

        zip_stream.seek(0)

        # Excluir arquivos TXT enviados após o processamento
        for txt_file_name in class_files:
            datalake.delete_file(txt_file_name)
        logger.info(f"Deleted all summary files in folder '{folder_name}'.")

        # Excluir arquivos PDF enviados após o processamento
        for pdf_file_name in pdf_files:
            datalake.delete_file(pdf_file_name)
        logger.info(f"Deleted all processed PDF files in folder '{folder_name}'.")

        return send_file(
            zip_stream,
            as_attachment=True,
            download_name="classifications.zip",
            mimetype="application/zip"
        )
    except Exception as e:
        logger.error(f"Error during download: {e}")
        return jsonify({'message': 'Error occurred during download.'}), 500
