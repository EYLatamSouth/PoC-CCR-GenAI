import os
import datetime
from flask import Blueprint, request, session, jsonify, send_file, redirect, url_for, flash, render_template
from src.backend.utils.utils import folders
from src.backend.storage.storage import AzureDataLake
from src.backend.utils.logger_config import logger
from src.backend.script.vendorlist import vendorlist
from io import BytesIO
from zipfile import ZipFile

bp = Blueprint("vendorlist", __name__, template_folder=folders.TEMPLATES)

@bp.route('/upload_vendorlist', methods=['GET', 'POST'])
def upload_vendorlist():
    user = session.get('name')
    if not user:
        logger.info("User is not connected, redirecting to logout...")
        return redirect(url_for("auth.logout"))

    user_name = user.split("@")[0].lower().replace(".", "_")
    folder_name = f'Vendorlist_{user_name}'

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
            
            return redirect(url_for('vendorlist.upload_vendorlist'))
    
    return render_template('agents/vendorlist.html')

@bp.route('/generate_vendorlist', methods=['POST'])
def generate_vendorlist():
    user = session.get('name')
    if not user:
        logger.info("User is not connected, redirecting to logout...")
        return redirect(url_for("auth.logout"))

    user_name = user.split("@")[0].lower().replace(".", "_")
    folder_name = f"Vendorlist_{user_name}"

    try:
        vendorlist(folder_name)
        logger.info(f"vendorlist completed for folder: {folder_name}")
        return jsonify({'message': 'vendorlist completed successfully!'}), 200
    except Exception as e:
        logger.error(f"Error during vendorlist: {e}")
        return jsonify({'message': 'Error during vendorlist'}), 500

@bp.route('/download_vendorlist', methods=['GET'])
def download_vendorlist():
    user = session.get('name')
    if not user:
        logger.info("User is not connected, redirecting to logout...")
        return redirect(url_for("auth.logout"))

    user_name = user.split("@")[0].lower().replace(".", "_")
    folder_name = f"Vendorlist_{user_name}"

    try:
        datalake = AzureDataLake()
        files = datalake.get_files_names_from_adls()
        vendor_files = [f for f in files if f.startswith(folder_name) and f.endswith('vendorlist.xlsx')]

        if not vendor_files:
            logger.info(f"No vendorlist files found in folder '{folder_name}'.")
            return jsonify({'message': 'No vendorlist available for download.'}), 404

        zip_stream = BytesIO()
        with ZipFile(zip_stream, 'w') as zip_file:
            for file_name in vendor_files:
                file_stream = BytesIO()
                datalake.download_file(file_name, file_stream)
                file_stream.seek(0)
                zip_file.writestr(os.path.basename(file_name), file_stream.read())

        zip_stream.seek(0)

        # Excluir arquivos vendorlist enviados após o processamento
        for xlsx_file_name in vendor_files:
            datalake.delete_file(xlsx_file_name)
        logger.info(f"Deleted all summary files in folder '{folder_name}'.")

        return send_file(
            zip_stream,
            as_attachment=True,
            download_name="vendorlist.zip",
            mimetype="application/zip"
        )
    except Exception as e:
        logger.error(f"Error during download: {e}")
        return jsonify({'message': 'Error occurred during download.'}), 500
