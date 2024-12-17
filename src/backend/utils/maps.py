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



# Função para remover as strings com base nos padrões
def remove_patterns_from_sentences(sentences):
    cleaned_sentences = []

    patterns = [
    r"fls .: \d{1,3}",  
    r"okuyama & alves advogados",  
    r"\(19\) 99416-2590",  
    r"\(11\) 94390-6888",  
    r"\(11\) 99160-5858",  
    r"www.okuyamaealvesadvogados.com.br",  
    r"okuyamaealvesadvogados@aasp.org.br", 
    r"pje assinado eletronicamente por:",  
    r"erick keiti okuyama",
    r"juntado em: 05/06/2024 14:38:38",
    r"4d07594",
    r"ab61ae7",
    r"av. narciso yague guimaraes",
    r"no 1145, " ,
    r"sala 501, ",
    r"5a andar, " ,
    r"jardim armenia, ",
    r"mogi das cruzes, ",
    r"cep: 08780-500"
    ]   

    for sentence in sentences:
        for pattern in patterns:
            sentence = re.sub(pattern, "", sentence)
        cleaned_sentences.append(sentence.replace('. r$',' r$').strip())
    return cleaned_sentences

# Função principal para extrair informações

def extract_valor_causa(sentences):
    pattern = r"valor da causa:\s*r\$\s?\d{1,3}(?:\.\d{3})*(?:,\s?\d{2})?"
    matches = [re.search(r"r\$\s?\d{1,3}(?:\.\d{3})*(?:,\s?\d{2})", m, re.IGNORECASE).group().upper() for m in sentences if re.search(pattern, m, re.IGNORECASE)]
    return matches

def extract_reclamante(sentences):
    pattern = r"reclamante:\s*([\w\s]+?)\s*advogado:"
    matches = [m.title() for s in sentences for m in re.findall(pattern, s, re.IGNORECASE)]
    return matches

def extract_aviso_previo(sentences):
    pattern = r"aviso previo(?:\s+de\s*)?[\d\s]+dias[\s\.\,]*r\$\s?\d{1,3}(?:\.\d{3})*(?:,\d{2})"
    values = []
    for sentence in sentences:
        match = re.search(pattern, sentence, re.IGNORECASE)
        if match:
            # Extrair o valor monetário (R$) encontrado na frase
            value = re.search(r"r\$\s?\d{1,3}(?:\.\d{3})*(?:,\d{2})", match.group(), re.IGNORECASE)
            if value:
                values.append(value.group().upper())
    return values

def extract_danos_morais(sentences):
    pattern = r"indenizar moralmente.*?r\$\s?\d{1,3}(?:\.\d{3})*(?:,\d{2})"
    values = []
    for sentence in sentences:
        # Buscar o trecho relevante a partir de "indenizar moralmente"
        match = re.search(pattern, sentence, re.IGNORECASE | re.DOTALL)
        if match:
            # Extrair apenas o valor monetário presente após "indenizar moralmente"
            value = re.search(r"r\$\s?\d{1,3}(?:\.\d{3})*(?:,\d{2})", match.group(), re.IGNORECASE)
            if value:
                values.append(value.group().upper())
    return values


def extract_insalubridade(sentences):
    pattern = r"[a-z]\)\s.*?reclamante no pagamento do adicional de insalubridade.*?r\$\s?\d{1,3}(?:\.\d{3})*(?:,\s?\d{2})"
    matches = [re.search(r"r\$\s?\d{1,3}(?:\.\d{3})*(?:,\s?\d{2})", m, re.IGNORECASE).group().upper() for m in sentences if re.search(pattern, m, re.IGNORECASE)]
    return matches

def extract_honorarios(sentences):
    pattern = r"honorarios.*?\b(\d{1,3}%)"
    matches = [m.upper() for s in sentences for m in re.findall(pattern, s, re.IGNORECASE)]
    return matches

def extract_salario(sentences):
    pattern = r"percebendo como salario a quantia de r\$\s?\d{1,3}(?:\.\d{3})*(?:,\s?\d{2})\s*\("
    matches = [re.search(r"r\$\s?\d{1,3}(?:\.\d{3})*(?:,\s?\d{2})", m, re.IGNORECASE).group().upper() for m in sentences if re.search(pattern, m, re.IGNORECASE)]
    return matches

def extract_data_inicio(sentences):
    pattern = r"admitida.*?(\d{2}/\d{2}/\d{4})"
    matches = [m for s in sentences for m in re.findall(pattern, s, re.IGNORECASE)]
    return matches

def extract_data_fim(sentences):
    pattern = r"encerrar.*?(\d{2}/\d{2}/\d{4})|pedido de demissao.*?(\d{2}/\d{2}/\d{4})"
    matches = [m for s in sentences for m in re.findall(pattern, s, re.IGNORECASE) if m]
    matches = [m[0] if m[0] else m[1] for m in matches]  # Handle multiple groups
    return matches

def process_sentences(sentences):
    dict_extract = {
        "ValorCausa": ", ".join(extract_valor_causa(sentences)).upper(),
        "Reclamante": ", ".join(extract_reclamante(sentences)).title(),
        "AvisoPrevio": ", ".join(extract_aviso_previo(sentences)).upper(),
        "DanosMorais": ", ".join(extract_danos_morais(sentences)).upper(),
        "Insalubridade": ", ".join(extract_insalubridade(sentences)).upper(),
        "Honorarios": ", ".join(extract_honorarios(sentences)).upper(),
        "Salario": ", ".join(extract_salario(sentences)).upper(),
        "DataInicio": ", ".join(extract_data_inicio(sentences)),
        "DataFim": ", ".join(extract_data_fim(sentences))
    }
    return dict_extract

def summary_page(conversation, page_text):
    # Criação do prompt

    prompt_string = (
    f"""
    Você é um agente de inteligência artificial especializado em redigir resumos jurídicos de maneira precisa, objetiva e técnica.  
    Você recebeu um texto referente à uma página de um processo trabalhista.
    O texto da página está abaixo entre ***.
    Se atente bem ao texto e traga o resumo com as informações mais relevantes.
    Seja direto, objetivo e responda apenas com os dados solicitados e no formato especificado. 
    Se alguma informação não for encontrada, responda "Não identificado".

    ### Formato da Resposta ###
    Retorne exclusivamente uma resposta em JSON no seguinte formato:

    {{
    "Resumo" : "<Resumo objetivo do conteúdo da página. Comece sempre com "O documento diz...">"
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
                "Resumo" : ""
            }
            return response_json
        
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON: {e}")
        return {"Resumo": "Erro ao resumir: falha ao decodificar JSON"}
            
    return response_json  # Retorna a resposta do modelo

# Função para atualizar o dicionário consolidado, sem duplicar informações
def update_all_pages_data(data_dict, extracted_dict):
    """
    Atualiza o dicionário consolidado com os dados extraídos de uma página usando regex.
    """
    
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