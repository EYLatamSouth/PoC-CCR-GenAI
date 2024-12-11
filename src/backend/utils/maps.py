import re
import tiktoken
import json
from src.backend.utils.logger_config import logger

# Função para contar tokens de um prompt
def contar_tokens(prompt: str, modelo="cl100k_base"):
    # Usando a codificação padrão "cl100k_base" para o GPT-3.5 / GPT-4
    enc = tiktoken.get_encoding(modelo)
    tokens = enc.encode(prompt)
    return len(tokens)

# Função para limitar o número de tokens
def limitar_tokens(prompt: str, max_tokens=8000, modelo="cl100k_base"):
    tokens = contar_tokens(prompt, modelo)
    if tokens > max_tokens:
        print(f"Prompt contém {tokens} tokens, que é maior que o limite de {max_tokens} tokens.")
        # Truncar o prompt para o limite de tokens
        enc = tiktoken.get_encoding(modelo)
        tokens = enc.encode(prompt)
        truncated_prompt = enc.decode(tokens[:max_tokens])  # Trunca o prompt para o limite
        print(f"Prompt truncado para {max_tokens} tokens.")
        return truncated_prompt
    return prompt

# Função principal para extrair informações
def extract_information_from_page(conversation, page_text):
    # Criação do prompt

    prompt_string = (
    f"""
    Você é um agente de inteligência artificial especializado em extrair informaçÕes e redigir resumos jurídicos de maneira precisa e objetiva.  
    Você recebeu um texto referente à uma página de uma reclamação trabalhista.
    O texto da página está abaixo entre ***.
    Extraia as informações abaixo do texto fornecido.
    Seja direto, objetivo e responda apenas com os dados solicitados e no formato especificado. 
    Se alguma informação não for encontrada, responda "Não identificado".

    ### Formato da Resposta ###
    Retorne exclusivamente uma resposta em JSON no seguinte formato:

    {{
    "Processo" :  "<Número da reclamação trabalhista (ex.: "0010005-64.2021.5.03.0187")>",
    "Autor" : "<Nome do autor do processo (também chamado de adverso, reclamante ou ex-empregado)>",
    "Salário" : "<Valor do salário ou remuneração do autor (ex.: "R$ 2.500,00")>",
    "Tempo" : "<Tempo de serviço do autor na empresa (ex.: "5 anos e 3 meses")>",
    "Resumo" : "<Resumo objetivo do conteúdo da página. Comece sempre com "O documento diz...">",
    "Valor" : "<Valor da causa informado no processo, costuma ser o maior valor escrito no documento (ex.: "R$ 500.000,00")>",
    "Objetos" : "<Objetos da reclamação e seus valores, no formato "<Objeto>" - "<Valor>" (ex.: "Hora extra" - "R$ 2.000,00", "Férias" - "R$ 3.500,00", "FGTS" - "Não identificado")>"
    }}

    ### Regras Adicionais ###
    - Não inclua frases desnecessárias que indiquem a origem das informações.
    - Para o resumo, construa o texto de forma fluida e seja objetivo e mantenha um tom formal e técnico.
    
    Texto da página ***. {page_text} ***.

    Resposta em JSON:        
    """
    )
    
    # Limitar o prompt para não ultrapassar o número máximo de tokens
    prompt_string_limited = limitar_tokens(prompt_string)

    # Chamada para o modelo de conversa
    response = conversation.run(prompt_string_limited)  # Use .run() para strings diretas
    print("response: ",response)
    try:
        # Limpar espaços e quebras de linha
        response_cleaned = response.strip()

        response_cleaned = response_cleaned.replace('\\"', "'")

        # Verificar se é JSON válido
        if response_cleaned.startswith('{') and response_cleaned.endswith('}'):
            response_json = json.loads(response_cleaned)
        else:
            logger.error("Formato inválido, o texto não é JSON.")

            response_json =  {
                "Processo" : "Não identificado",
                "Autor" : "Não identificado",
                "Salário" : "Não identificado",
                "Tempo" : "Não identificado",
                "Resumo" : "",
                "Valor" : "Não identificado",
                "Objetos" : "Não identificado"
            }
            return response_json
        
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON: {e}")
        return {"resumo": "Erro ao resumir: falha ao decodificar JSON"}
            
    return response_json  # Retorna a resposta do modelo

# Função para atualizar o dicionário consolidado, sem duplicar informações
def update_all_pages_data(data_dict, extracted_dict):
    """
    Atualiza o dicionário consolidado com os dados extraídos de uma página usando regex.
    """
    
    data_dict["Processo"].add(extracted_dict["Processo"])
    
    data_dict["Autor"].add(extracted_dict["Autor"])

    data_dict["Salário"].add(extracted_dict["Salário"])

    data_dict["Tempo"].add(extracted_dict["Tempo"])

    data_dict["Valor"].add(extracted_dict["Valor"])

    data_dict["Objetos"].add(extracted_dict["Objetos"])
    
    data_dict["Resumo"].append(extracted_dict["Resumo"])


def padronizar_telefone(telefone):
    telefone = ''.join(filter(str.isdigit, str(telefone)))
    
    if len(telefone) == 10:
        return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
    
    elif len(telefone) == 8:
        return f"{telefone[:4]}-{telefone[4:]}"
    
    else:
        return telefone
    
def validar_grupo(conversation,grupo,textos):
    try:
        itens_texto = ', '.join(f"- {texto}" for texto in textos)

        prompt = f"""
            Você é um agente de inteligência artificial trabalhando no setor de compras da CCR.
            Sua tarefa é analisar uma lista de materiais agrupados em categorias e determinar se todos os materiais estão coerentes com o nome do grupo.

            ### Instruções ###
            - Considere que o nome do grupo representa uma categoria ampla que pode incluir sinônimos ou itens relacionados.
            - Analise cuidadosamente se cada material pertence à categoria representada pelo grupo.
            - Use bom senso para identificar associações plausíveis entre o nome do grupo e os materiais listados. Exemplo:
            - Grupo: "Ferramentas". Materiais: "Martelo", "Alicate" — **Coerente**.
            - Grupo: "Ferramentas". Materiais: "Notebook", "Cadeira" — **Incoerente**.
            - Se o material não parecer pertencer ao grupo, mas for ambíguo, dê o benefício da dúvida e considere como coerente.

            ### Formato da Resposta ###
            Retorne exclusivamente uma resposta em JSON no seguinte formato:
            {{
            "status": "Ok" ou "Incoerente",
            "materiais_incoerentes": ["Material 1", "Material 2", ...]
            }}
            - Se todos os materiais forem coerentes com o grupo, retorne:
            {{
                "status": "Ok",
                "materiais_incoerentes": []
            }}
            - Se houver materiais incoerentes, liste apenas os nomes dos materiais incoerentes no campo `materiais_incoerentes`.

            ### Regras Adicionais ###
            - Não inclua explicações, saudações, despedidas ou informações adicionais.
            - Não faça suposições desnecessárias. Seja objetivo ao determinar a coerência.

            Grupo: {grupo}
            Materiais:
            {itens_texto}

            Resposta em JSON:
            """

        # prompt_limited = limitar_tokens(prompt)
        validacao = conversation.run(prompt)
        conversation.memory.clear()

        # Processa o JSON retornado
        validacao_json = json.loads(validacao)
        return validacao_json
    except json.JSONDecodeError:
        logger.error(f"Erro ao decodificar JSON para o grupo {grupo}: {validacao}")
        return {"status": "Erro", "materiais_incoerentes": []}
    except Exception as e:
        logger.error(f"Erro ao validar grupo {grupo}: {str(e)}")
        return {"status": "Erro", "materiais_incoerentes": []}