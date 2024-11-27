import os
import re
import PyPDF2
from io import BytesIO
from langchain.chains import ConversationChain
from src.backend.utils.maps import extract_information_from_page, update_all_pages_data, limitar_tokens
from src.backend.llm.azure_open_ai import create_azure_chat_llm
from src.backend.storage.storage import AzureDataLake
from src.backend.utils.logger_config import logger

def classification():
    
    logger.info("classification")


    return "classification"
