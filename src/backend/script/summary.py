import os
import re
import PyPDF2
from io import BytesIO
from langchain.chains import ConversationChain
from src.backend.utils.maps import extract_information_from_page, update_all_pages_data, limitar_tokens
from src.backend.llm.azure_open_ai import create_azure_chat_llm
from src.backend.storage.storage import AzureDataLake
from src.backend.utils.logger_config import logger

def summarization(folder_name):
    # Inicializar Azure Data Lake
    datalake = AzureDataLake()

    # Listar arquivos do usuário no Data Lake
    files = datalake.get_files_names_from_adls()
    user_files = [f for f in files if f.startswith(folder_name) and f.endswith('.pdf')]

    if not user_files:
        raise FileNotFoundError("No PDF files found in the specified folder.")

    # Configurar o modelo de LLM
    llm = create_azure_chat_llm()
    conversation = ConversationChain(llm=llm, verbose=True)

    for file_name in user_files:
        # Baixar o arquivo do Data Lake
        file_stream = BytesIO()
        datalake.download_file(file_name, file_stream)
        file_stream.seek(0)

        # Processar o arquivo PDF
        pdf_reader = PyPDF2.PdfReader(file_stream)

        # Dicionário para armazenar informações do arquivo atual
        all_pages_data = {
            "Processo": "Não identificado",
            "Autor": "Não identificado",
            "Réu": "Não identificado",
            "Resumo": [],
            "Pedidos": [],
            "Decisões": [],
        }

        for page_num in range(len(pdf_reader.pages)):
            page_text = pdf_reader.pages[page_num].extract_text()
            extracted_data = extract_information_from_page(conversation, page_text)
            update_all_pages_data(all_pages_data, extracted_data)
            conversation.memory.clear()

        # Consolidar o resumo final
        final_prompt = (
            f"""
            Você é um agente de inteligência artificial e capacitado para atuar no setor jurídico. 
            Você recebeu uma string com os resumos de cada página de um arquivo PDF, a string está abaixo entre ***.
            Nessa string tem os resumos de todas as páginas do documento PDF.
            Seu objetivo é ler essa string de resumos e consolidá-los em um único texto coeso e direto.
            Esse texto consolidado tem que ser o resumo do PDF inteiro.
            Você tem todas as informações necessárias para executar essa tarefa de forma precisa. 
            A sua resposta precisa ter sempre a seção RESPOSTA, e deve ser sempre apresentada exclusivamente no seguinte formato:

            "
            ###RESPOSTA###

            <Resumo do PDF>

            "

            Traga as respostas sempre no formato demonstrado acima, com RESPOSTA sinalizado por ###.        

            ***STRING: {' '.join(all_pages_data["Resumo"])}***
            """
        )
        final_prompt_limited = limitar_tokens(final_prompt)
        final_summary = conversation.run(final_prompt_limited)

        match = re.search(r'###RESPOSTA###(.*)', final_summary, re.DOTALL)
        
        resumo = match.group(1).strip() if match else "Erro: A resposta não contém os delimitadores esperados."

        # Criar o nome do arquivo de resumo
        base_name = os.path.splitext(os.path.basename(file_name))[0]
        summary_file_name = f"{folder_name}/{base_name}_summary.txt"

        # Criar o conteúdo do arquivo .txt
        summary_content = (
            f"Informações extraídas:\n"
            f"Processo: {all_pages_data['Processo']}\n"
            f"Autor: {all_pages_data['Autor']}\n"
            f"Réu: {all_pages_data['Réu']}\n"
            f"Pedidos: {'; '.join(all_pages_data['Pedidos'])}\n"
            f"Decisões: {'; '.join(all_pages_data['Decisões'])}\n\n"
            f"Resumo consolidado:\n"
            f"{resumo}"
        )

        # Salvar o resumo como arquivo no Azure Data Lake
        summary_stream = BytesIO(summary_content.encode('utf-8'))
        datalake.upload_file_obj(summary_stream, summary_file_name)

        logger.info(f"Summary generated and uploaded for file {file_name}")


    return f"Summaries generated successfully for folder {folder_name}."
