import re
import tiktoken

# Função para contar tokens de um prompt
def contar_tokens(prompt: str, modelo="cl100k_base"):
    # Usando a codificação padrão "cl100k_base" para o GPT-3.5 / GPT-4
    enc = tiktoken.get_encoding(modelo)
    tokens = enc.encode(prompt)
    return len(tokens)

# Função para limitar o número de tokens
def limitar_tokens(prompt: str, max_tokens=8192, modelo="cl100k_base"):
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
        Extraia as seguintes informações do texto fornecido, se disponíveis:

        1. **Processo:** Apenas o número.
        2. **Autor:** Apenas o autor
        3. **Réu:** Apenas o réu
        4. **Resumo:** Resumo objetivo do que tem na página. 
        5. **Pedidos:** O que o autor busca.
        6. **Decisões:** Andamento atual e movimentações importantes.

        Se algo não estiver claro ou ausente, indique "Não identificado". Seja objetivo e direto.

        Texto da página: {page_text}
        """
    )
    
    # Limitar o prompt para não ultrapassar o número máximo de tokens
    prompt_string_limited = limitar_tokens(prompt_string)

    # Chamada para o modelo de conversa
    response = conversation.run(prompt_string_limited)  # Use .run() para strings diretas
    return response  # Retorna a resposta do modelo

# Função para atualizar o dicionário consolidado, sem duplicar informações
def update_all_pages_data(data_dict, extracted_text):
    """
    Atualiza o dicionário consolidado com os dados extraídos de uma página usando regex.
    """
    # Limpar os espaços em branco no começo e final do texto
    extracted_text = extracted_text.strip()

    # Definindo os padrões regex para cada seção, agora considerando o formato que você forneceu
    processo_pattern = r"1\.\sProcesso\:\s*(.*?)(?=\n2\.|$)"
    autor_pattern = r"2\.\sAutor\:\s*(.*?)(?=\n3\.|$)"
    reu_pattern = r"3\.\sRéu\:\s*(.*?)(?=\n4\.|$)"
    resumo_pattern = r"4\.\sResumo\:\s*(.*?)(?=\n5\.|$)"
    pedidos_pattern = r"5\.\sPedidos\:\s*(.*?)(?=\n6\.|$)"
    decisoes_pattern = r"6\.\sDecisões\:\s*(.*?)(?=\n|$)"

    # Usar regex para encontrar os dados de cada seção
    processo_match = re.search(processo_pattern, extracted_text, re.DOTALL)
    autor_match = re.search(autor_pattern, extracted_text, re.DOTALL)
    reu_match = re.search(reu_pattern, extracted_text, re.DOTALL)
    resumo_match = re.search(resumo_pattern, extracted_text, re.DOTALL)
    pedidos_match = re.search(pedidos_pattern, extracted_text, re.DOTALL)
    decisoes_match = re.search(decisoes_pattern, extracted_text, re.DOTALL)

    # Atualizar o dicionário com os dados extraídos, mas apenas se não estiverem já definidos
    if processo_match and data_dict["Processo"] == "Não identificado":
        data_dict["Processo"] = processo_match.group(1).strip()
        
    if autor_match and data_dict["Autor"] == "Não identificado":
        data_dict["Autor"] = autor_match.group(1).strip()
        
    if reu_match and data_dict["Réu"] == "Não identificado":
        data_dict["Réu"] = reu_match.group(1).strip()

    if resumo_match:
        data_dict["Resumo"].append(resumo_match.group(1).strip())

    if pedidos_match:
        data_dict["Pedidos"].append(pedidos_match.group(1).strip())

    if decisoes_match:
        data_dict["Decisões"].append(decisoes_match.group(1).strip())