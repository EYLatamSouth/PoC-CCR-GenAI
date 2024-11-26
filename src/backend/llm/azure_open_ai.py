import os
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('AZURE_OPENAI_API_KEY')
azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
api_version = os.getenv('AZURE_OPENAI_API_VERSION')
api_type = os.getenv('AZURE_OPENAI_API_TYPE')


def create_azure_chat_llm(temperature=0.5, deployment_name = "gpt-35-turbo"):
  """
    Cria um modelo de linguagem de chat utilizando as bibliotecas da Azure OpenAI.

    Args:
        temperature (float, opcional): Controla a aleatoriedade da resposta gerada. O padrão é 0.5.

    Returns:
        AzureChatOpenAI: Um modelo de linguagem de chat da Azure OpenAI.
    """
  llm = AzureChatOpenAI(
    deployment_name=deployment_name,
    azure_endpoint=azure_endpoint,
    openai_api_key=api_key,
    openai_api_version=api_version,
    temperature=temperature
  )

  return llm