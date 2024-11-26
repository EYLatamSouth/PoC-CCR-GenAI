import os
from loguru import logger
from opencensus.ext.azure.log_exporter import AzureLogHandler
import logging

# Carregar a variável de ambiente para Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

# Configurar Loguru
logger.remove()  # Remove o handler padrão do Loguru
# logger.add("app.log", rotation="10 MB", retention="7 days", level="INFO")  # Salvar em arquivo

if APPLICATIONINSIGHTS_CONNECTION_STRING:
    # Criar o AzureLogHandler para o Application Insights
    azure_handler = AzureLogHandler(connection_string=APPLICATIONINSIGHTS_CONNECTION_STRING)

    # Criar um interceptor para direcionar logs do Loguru para o Application Insights
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            # Repassa os logs do Loguru para o AzureLogHandler
            azure_handler.emit(record)

    # Adicionar o InterceptHandler ao Loguru
    logger.add(InterceptHandler(), level="INFO")

# Configuração para usar o logger em todos os módulos
logger.info("Logger configurado com sucesso!")

# Exemplo de como adicionar um log adicional no console (opcional):
logger.add(lambda msg: print(msg, flush=True), level="DEBUG")
