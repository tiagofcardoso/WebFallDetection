from flask import Flask
from .config import *


def create_app():
    app = Flask(__name__)

    # Configurações da aplicação
    app.config.from_object('config')

    # Registrar blueprints
    from app.templates.routes import main
    app.register_blueprint(main)

    return app
