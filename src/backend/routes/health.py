from flask import Blueprint
from src.backend.utils.utils import folders


bp = Blueprint("health", __name__, template_folder=folders.TEMPLATES,
                static_folder=folders.STATIC)

@bp.route("/health")
def health():
    """
    Verifica a saúde do serviço.

    Método HTTP:
        GET

    Respostas:
        200: Retorna "OK" indicando que o serviço está funcionando.
    """

    return "OK", 200