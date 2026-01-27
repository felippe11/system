"""
Configuração para atividades com múltiplas datas
"""
from flask import Blueprint
from routes.atividade_multipla_routes import atividade_multipla_routes

def register_atividade_multipla_routes(app):
    """Registra as rotas de atividades com múltiplas datas no app Flask"""
    app.register_blueprint(atividade_multipla_routes, url_prefix='/atividades_multiplas')

def get_atividade_multipla_menu_items():
    """Retorna itens de menu para atividades com múltiplas datas"""
    return [
        {
            'title': 'Atividades com Múltiplas Datas',
            'url': 'atividade_multipla_routes.listar_atividades',
            'icon': 'fas fa-calendar-alt',
            'permissions': ['cliente']
        }
    ]
