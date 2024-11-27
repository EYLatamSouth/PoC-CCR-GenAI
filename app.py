import os
from datetime import timedelta
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask, session
from flask_session import Session
from src.backend.utils.utils import folders
from src.backend.routes import auth, health, upload
from dotenv import load_dotenv
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.ext.flask.flask_middleware import FlaskMiddleware
from opencensus.trace.samplers import ProbabilitySampler

load_dotenv()

# Carregar a variável de ambiente para Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

def create_app():
    """
    Cria e configura uma instância dos ChatBots dos agentes.
    """
    app = Flask(__name__, template_folder=folders.TEMPLATES,
                static_folder=folders.STATIC)

    # Enable HTTPS
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Configurar a sessão
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = "flask_session"
    app.config["SESSION_PERMANENT"] = False
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=10)

    Session(app)

    # Configurar FlaskMiddleware para Application Insights
    if APPLICATIONINSIGHTS_CONNECTION_STRING:
        FlaskMiddleware(
            app=app,  # Aqui você passa a instância do Flask
            exporter=AzureExporter(connection_string=APPLICATIONINSIGHTS_CONNECTION_STRING),
            sampler=ProbabilitySampler(rate=1.0)  # Rastrear 100% das requisições
        )
    
    # Registrar blueprints
    app.register_blueprint(auth.bp)
    app.register_blueprint(health.bp)
    app.register_blueprint(upload.bp)
    
    return app

# Expor o `app` globalmente para Gunicorn
app = create_app()

if __name__ == "__main__":
    app.run()