import os
import re
import PyPDF2
from io import BytesIO
from langchain.chains import ConversationChain
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from src.backend.utils.maps import summary_page, process_sentences, update_all_pages_data, limitar_tokens, remove_patterns_from_sentences
from src.backend.llm.azure_open_ai import create_azure_chat_llm
from src.backend.storage.storage import AzureDataLake
from src.backend.utils.logger_config import logger
from unidecode import unidecode
import json

endpoint = os.getenv("AZURE_DOCUMENT_ENDPOINT")
key = os.getenv("AZURE_DOCUMENT_KEY")



def summarization(folder_name):
    """
    Processa PDFs de uma pasta no Azure Data Lake, gera resumos jurídicos e os salva no Data Lake.
    """
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
    
    document_analysis_client = DocumentAnalysisClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )

    for file_name in user_files:
        # Inicializar armazenamento de resumos
        all_pages_summary = {"Resumo": []}

        # Baixar o arquivo do Data Lake
        file_stream = BytesIO()
        datalake.download_file(file_name, file_stream)
        file_stream.seek(0)

        # Analisar o documento com o Azure Document Intelligence
        poller = document_analysis_client.begin_analyze_document(
            "prebuilt-layout", document=file_stream
        )
        result = poller.result()

        # Extrair e processar texto das páginas
        sentences = []
        for page in result.pages:
            lines = [unidecode(line.content).strip().lower() for line in page.lines]
            sentences.append(" ".join(lines))

        sentences_cleaned = remove_patterns_from_sentences(sentences[:30])

        # Gerar resumo para cada página
        for text in sentences_cleaned:
            page_summary = summary_page(conversation, text)
            update_all_pages_data(all_pages_summary, page_summary)
            conversation.memory.clear()

        # Consolidar os resumos das páginas
        consolidated_summary = consolidate_summaries(conversation, all_pages_summary["Resumo"])

        # Extrair metadados e preparar o conteúdo do resumo
        dict_extract = process_sentences(sentences)
        summary_content = create_summary_content(dict_extract, consolidated_summary)

        # Criar o nome do arquivo de saída
        base_name = os.path.splitext(os.path.basename(file_name))[0]
        summary_file_name = f"{folder_name}/{base_name}_summary.txt"

        # Salvar o resumo no Azure Data Lake
        save_summary_to_datalake(datalake, summary_content, summary_file_name)

        logger.info(f"Summary generated and uploaded for file {file_name}")

    return f"Summaries generated successfully for folder {folder_name}."


def consolidate_summaries(conversation, summaries):
    """
    Consolida os resumos das páginas em um único texto coeso.
    """
    # consolidated_prompt = (
    #     f"""
    #     Você é um agente de inteligência artificial especializado em redigir resumos jurídicos de maneira precisa e objetiva. 
    #     Sua tarefa é consolidar os resumos de cada página de uma reclamação trabalhista em um único texto coeso, claro e direto, representando o resumo da reclamação trabalhista como um todo.

    #     ### Formato de saída obrigatório ###
    #     Retorne exclusivamente uma resposta em JSON, sem nenhum texto adicional ou explicação. O formato exato é:

    #     {{
    #         "resumo": "A reclamação trabalhista diz <Resumo objetivo do conteúdo>"
    #     }}

    #     ### Regras ###
    #     - Não inclua frases como "a página diz/trata/menciona" ou referências às origens das informações.
    #     - Construa o texto de forma fluida, combinando os resumos em um único parágrafo objetivo.
    #     - Seja técnico e formal.

    #     ***STRING: {' '.join(summaries)}***

    #     Resposta:
    #     """
    # )

    consolidated_prompt = (
        f"""
        Você é um agente de inteligência artificial especializado em redigir resumos jurídicos de maneira precisa e objetiva. 
        Sua tarefa é consolidar os resumos de cada página de uma reclamação trabalhista em um único texto coeso, claro e direto, representando o resumo da reclamação trabalhista como um todo.

        ### Formato de saída obrigatório ###
        Retorne exclusivamente uma resposta em JSON, sem nenhum texto adicional ou explicação. O formato exato é:

        {{
            "resumo": "ADMITIDO EM [data de admissão] PARA EXERCER A FUNÇÃO DE [função], SENDO DESLIGADO EM [data de desligamento]. 
                       ALEGA QUE [detalhes dos pedidos de forma agrupada e organizada, como verbas rescisórias, jornadas extraordinárias, condições de trabalho, assédio moral, entre outros]."
        }}

        ### Diretrizes ###
        1. Inicie mencionando a data de admissão, a função exercida e a data de desligamento (se aplicável).
        2. Construa o resumo agrupando os pedidos de forma lógica e direta, com foco nos principais tópicos da reclamação trabalhista.
        3. Use uma linguagem técnica, formal e objetiva.
        4. Não inclua expressões como "a página menciona" ou outras referências à origem da informação.
        5. Evite redundâncias e foque em apresentar as informações de maneira concisa e fluida.
        6. Se não tiver certeza de alguma informação, apenas nào mencione.

        ### STRING FORNECIDA ###
        Abaixo está a string consolidada de resumos das páginas da petição inicial. Use-a para criar um resumo conforme os exemplos e as diretrizes:

        ***STRING: {' '.join(summaries)}***

        Resposta:
        """
    )


    consolidated_prompt = limitar_tokens(consolidated_prompt)
    response = conversation.run(consolidated_prompt)

    try:
        # Extração e validação do JSON retornado
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            response = response[json_start:json_end]
        return json.loads(response).get("resumo", "Erro: resumo não encontrado no JSON.")
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON: {e}")
        return "Erro ao resumir: falha ao decodificar JSON"


def create_summary_content(dict_extract, resumo):
    """
    Gera o conteúdo do resumo consolidado com os metadados extraídos.
    """
    return (
        f"Informações extraídas:\n"
        f"Valor da causa: {dict_extract['ValorCausa']}\n"
        f"Reclamante: {dict_extract['Reclamante']}\n"
        f"Aviso Prévio: {dict_extract['AvisoPrevio']}\n"
        f"Danos morais: {dict_extract['DanosMorais']}\n"
        f"Honorários: {dict_extract['Honorarios']}\n"
        f"Salário: {dict_extract['Salario']}\n"
        f"Data de início: {dict_extract['DataInicio']}\n"
        f"Data de demissão: {dict_extract['DataFim']}\n\n"
        f"Resumo consolidado:\n"
        f"{resumo.upper()}"
    )


def save_summary_to_datalake(datalake, summary_content, file_name):
    """
    Salva o resumo consolidado no Azure Data Lake.
    """
    summary_stream = BytesIO(summary_content.encode('utf-8'))
    datalake.upload_file_obj(summary_stream, file_name)

