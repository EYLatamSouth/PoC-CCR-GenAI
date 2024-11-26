import os
import uuid
from flask import Blueprint, request, render_template, make_response, redirect, url_for, session
import identity.web
from dotenv import load_dotenv
from src.backend.utils.utils import folders

load_dotenv()

bp = Blueprint("auth", __name__, template_folder=folders.TEMPLATES,
                static_folder=folders.STATIC)

AUTHORITY = os.getenv("AUTHORITY")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

auth = identity.web.Auth(
    session=session,
    authority=AUTHORITY,
    client_id=CLIENT_ID,
    client_credential=CLIENT_SECRET,
)

@bp.route("/")
def index():

    user_id = session.get('user_id')

    if user_id:
        return redirect(url_for("auth.show_chat")) 
    else:
        return redirect(url_for("auth.login"))

@bp.route('/chat', methods=['GET'])
def show_chat():
    return render_template('select/index.html')

@bp.route("/login")
def login():
    return render_template("auth/login_sso.html", **auth.log_in(
        scopes=["User.Read"],
        redirect_uri=url_for("auth.auth_response", _external=True),
        prompt="select_account",
        ))

@bp.route("/getAToken")
def auth_response():
    result = auth.complete_log_in(request.args)

    if "error" in result:
        return make_response(result.get("error"))

    # Extraia informações do ID Token
    user_id = session.get('user_id')

    if not user_id:
        session['user_id'] = str(uuid.uuid4())
        session['messages'] = {
            "ai": [],
            "user": []
        }

    # Configurando as novas variáveis na sessão com base no ID Token
    session['login'] = result.get("preferred_username")  # Email ou login do usuário
    session['name'] = result.get("name")  # Nome do usuário
    session['token'] = result.get("sub")  # Usando o "sub" como identificador único do token
    session.permanent = True  # Torna a sessão permanente (expira conforme configurado)

    return redirect(url_for("auth.show_chat"))


@bp.route("/logout")
def logout():

    user_id = session.get('user_id')

    if user_id:
        session.pop(user_id, None)
        session.pop('messages')
    
    session.clear()

    return redirect(auth.log_out(url_for("auth.login", _external=True)))