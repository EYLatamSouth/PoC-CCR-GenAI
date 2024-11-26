import os
import boto3
from flask import Blueprint, request, flash, redirect, url_for, render_template, session, jsonify
from src.backend.utils.utils import folders
from src.backend.scripts.main_rag_amparo import rag
from dotenv import load_dotenv
from botocore.exceptions import ClientError
import datetime
from src.backend.utils.logger_config import logger

load_dotenv()

bp = Blueprint("upload_s3", __name__, template_folder=folders.TEMPLATES,
               static_folder=folders.STATIC)

@bp.route('/UploadS3', methods=['GET', 'POST'])
def upload_to_s3():

    user = session.get('name')

    if not user:
        logger.info("User is not connected, redirecting to logout...")
        return redirect(url_for("auth.logout"))
    
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
            # Definir o nome do bucket S3 e objeto no S3
            bucket_name = os.getenv('AWS_S3_BUCKET_NAME')
            object_name = f'Amparo/{nome_base}_{data}{extensao}'

            # Fazer upload do arquivo para o S3 diretamente da memória
            try:
                s3_client = boto3.client('s3')
                s3_client.upload_fileobj(file, bucket_name, object_name)

                flash(f'Upload do {file.filename} feito com sucesso.', 'success')
                logger.info('File successfully uploaded to S3')
            except ClientError as e:
                logger.error(e)
                flash(f'Falha ao fazer upload do {file.filename}.', 'error')

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                flash('Ocorreu um erro inesperado ao tentar fazer o upload. Tente novamente.', 'error')
            
            return redirect(url_for('upload_s3.upload_to_s3'))
    
    return render_template('upload/upload_s3.html')

@bp.route('/generate_index', methods=['POST'])
def generate_index_amparo():
    try:
        rag()
        logger.info('Index generated successfully for the agent Amparo.')

        return jsonify({'message': 'Index generated successfully!'}), 200

    except Exception as e:
        logger.error(f"Error generating the index: {e}")
        return jsonify({'message': 'Error generating the index'}), 500