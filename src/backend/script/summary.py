import os
import re
import PyPDF2
from io import BytesIO
from langchain.chains import ConversationChain
from src.backend.utils.maps import extract_information_from_page, update_all_pages_data, limitar_tokens
from src.backend.llm.azure_open_ai import create_azure_chat_llm
from src.backend.storage.storage import AzureDataLake
from src.backend.utils.logger_config import logger
import json

def summarization(folder_name):
    # Inicializar Azure Data Lake
    datalake = AzureDataLake()

    # Listar arquivos do usuário no Data Lake
    files = datalake.get_files_names_from_adls()
    user_files = [f for f in files if f.startswith(folder_name) and f.endswith('.pdf')]

    if not user_files:
        raise FileNotFoundError("No PDF files found in the specified folder.")

    # Configurar o modelo de LLM
    llm = create_azure_chat_llm(temperature=0)
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
            "Processo": set(),
            "Autor": set(),
            "Salário": set(),
            "Tempo": set(),
            "Valor": set(),
            "Objetos": set(),
            "Resumo": []
        }

        for page_num in range(len(pdf_reader.pages)):
            page_text = pdf_reader.pages[page_num].extract_text()
            extracted_data = extract_information_from_page(conversation, page_text)
            update_all_pages_data(all_pages_data, extracted_data)
            conversation.memory.clear()

        final_prompt = (
            f"""
            Você é um agente de inteligência artificial especializado em redigir resumos jurídicos de maneira precisa e objetiva. 
            Você recebeu uma string contendo os resumos de cada página de uma reclamação trabalhista. 
            Sua tarefa é consolidar essas informações em um único texto coeso, claro e direto, representando o resumo da reclamação trabalhista como um todo.
            O texto final deve refletir o conteúdo integral da reclamação, sem conter termos como "a página diz/trata/menciona" ou indicar que as informações vêm de páginas específicas.

            ### Formato da Resposta ###
            Retorne exclusivamente uma resposta em JSON no seguinte formato:
            {{
            "resumo": "A reclamação trabalhista diz..."
            }}
            
            ### Regras Adicionais ###
            - Não inclua frases desnecessárias que indiquem a origem das informações.
            - Construa o texto de forma fluida, combinando os resumos em um único parágrafo que capture a essência da reclamação trabalhista.
            - Seja objetivo e mantenha um tom formal e técnico.
            
            ***STRING: {' '.join(all_pages_data["Resumo"])}***

            Resposta em JSON:
            """
        )

        final_prompt_limited = limitar_tokens(final_prompt)
        final_summary = conversation.run(final_prompt_limited)
        print("final_summary: ", final_summary)
        try:
            # Limpar espaços e quebras de linha
            final_summary_cleaned = final_summary.strip()
            print("final_summary_cleaned: ", final_summary_cleaned)
            # Verificar se é JSON válido
            if final_summary_cleaned.startswith('{') and final_summary_cleaned.endswith('}'):
                final_summary_json = json.loads(final_summary_cleaned)
                print("final_summary_json: ", final_summary_json)
            else:
                logger.error("Formato inválido, o texto não é JSON.")
                return {"resumo": "Erro ao resumir: formato inválido"}
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON: {e}")
            return {"resumo": "Erro ao resumir: falha ao decodificar JSON"}
        
        resumo = final_summary_json['resumo']
        # Criar o nome do arquivo de resumo
        base_name = os.path.splitext(os.path.basename(file_name))[0]
        summary_file_name = f"{folder_name}/{base_name}_summary.txt"

        # Criar o conteúdo do arquivo .txt
        summary_content = (
            f"Informações extraídas:\n"
            f"Processo: {all_pages_data['Processo']}\n"
            f"Autor: {all_pages_data['Autor']}\n"
            f"Salário: {all_pages_data['Salário']}\n"
            f"Tempo: {all_pages_data['Tempo']}\n"
            f"Valor: {all_pages_data['Valor']}\n"
            f"Objetos: {all_pages_data['Objetos']}\n\n"
            f"Resumo consolidado:\n"
            f"{resumo}"
        )

        # Salvar o resumo como arquivo no Azure Data Lake
        summary_stream = BytesIO(summary_content.encode('utf-8'))
        datalake.upload_file_obj(summary_stream, summary_file_name)

        logger.info(f"Summary generated and uploaded for file {file_name}")


    return f"Summaries generated successfully for folder {folder_name}."
