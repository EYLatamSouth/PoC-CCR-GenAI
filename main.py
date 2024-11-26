import PyPDF2
from langchain.chains import ConversationChain
from maps import create_azure_chat_llm, extract_information_from_page, update_all_pages_data, limitar_tokens
import re

# Abrir o arquivo PDF
pdf_file_path = "C:/Users/HN573EG/OneDrive - EY/Desktop/Projetos/Carrefour/docs/Caso 4 - Decisao.pdf"
pdf_file = open(pdf_file_path, "rb")
pdf_reader = PyPDF2.PdfReader(pdf_file)

# Configuração do LLM e da conversação
llm = create_azure_chat_llm()

# Configurar o ConversationChain
conversation = ConversationChain(llm=llm, verbose=True)

# Dicionário para armazenar informações de todas as páginas
all_pages_data = {
    "Processo": "Não identificado",
    "Autor": "Não identificado",
    "Réu": "Não identificado",
    "Resumo": [],
    "Pedidos": [],
    "Decisões": [],
}

# Processar cada página do PDF
for page_num in range(len(pdf_reader.pages)):
    page_text = pdf_reader.pages[page_num].extract_text()
    extracted_data = extract_information_from_page(conversation, page_text)
    update_all_pages_data(all_pages_data, extracted_data)
    conversation.memory.clear()

# Consolidar apenas os resumos em um único texto
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

# Limitar o prompt para não ultrapassar o número máximo de tokens
final_prompt_limited = limitar_tokens(final_prompt)

# Consolidar o resumo final
final_summary = conversation.run(final_prompt_limited)

match = re.search(r'###RESPOSTA###(.*)', final_summary, re.DOTALL)
    
if match:
    resumo = match.group(1).strip()

else:
    resumo = "Erro: A resposta não contém os delimitadores esperados."

# Criar saída final com apenas as informações desejadas
output_file_path = "resumo_pdf_final.txt"
with open(output_file_path, "w", encoding="utf-8") as output_file:
    output_file.write("Informações extraídas:\n")
    # Apenas adiciona as chaves desejadas e evita duplicados
    output_file.write(f"Processo: {all_pages_data['Processo']}\n")
    output_file.write(f"Autor: {all_pages_data['Autor']}\n")
    output_file.write(f"Réu: {all_pages_data['Réu']}\n")
    output_file.write(f"Pedidos: {'; '.join(all_pages_data['Pedidos'])}\n")
    output_file.write(f"Decisões: {'; '.join(all_pages_data['Decisões'])}\n\n")
    output_file.write("Resumo consolidado:\n")
    output_file.write(resumo)

print(f"Resumo final salvo em {output_file_path}")