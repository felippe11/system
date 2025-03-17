from flask import Flask
from config import Config
from extensions import db, login_manager, migrate, mail
from datetime import datetime
import os
import logging

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.jinja_env.add_extension('jinja2.ext.do')
    
    app.debug = True
    # Configuração de logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    # Inicializar extensões
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)  # Já inicializa o migrate importado de extensions
    mail.init_app(app)
    
    # REMOVA ESTA LINHA - você já está inicializando o migrate acima
    # migrate = Migrate(app, db)  <- Este é o problema

    login_manager.login_view = "routes.login"
    login_manager.session_protection = "strong"

    # Definição do filtro para formatação de datas
    @app.template_filter('string_to_date')
    def string_to_date(value):
        try:
            return datetime.strptime(value, '%Y-%m-%d').strftime('%d/%m/%Y')
        except (ValueError, TypeError):
            return value  # Retorna a string original se não puder converter

    # Importar e registrar as rotas **após** a criação do app
    from routes import register_routes
    register_routes(app)

    # Criar o banco dentro do contexto da aplicação
    with app.app_context():
        db.create_all()

    return app

# Criar a aplicação
app = create_app()

# Executar apenas se rodar diretamente
if __name__ == '__main__':
    app.run(debug=True)