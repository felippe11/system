# Este arquivo permite que o diretório routes seja tratado como um pacote Python

def register_routes(app):
    # Primeiro, registrar as rotas de sorteio
    from routes.sorteio_routes import sorteio_routes
    app.register_blueprint(sorteio_routes)
    
    # Depois, importar o módulo routes diretamente do diretório pai
    # para evitar conflitos de nome com o pacote routes
    import sys
    import os
    import importlib.util
    
    # Caminho para o arquivo routes.py no diretório raiz
    routes_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'routes.py')
    
    # Carregar o módulo routes.py como um módulo separado
    spec = importlib.util.spec_from_file_location('main_routes', routes_path)
    main_routes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main_routes)
    
    # Registrar o blueprint de rotas principais
    app.register_blueprint(main_routes.routes)
