# -*- coding: utf-8 -*-
import sys
sys.path.append('.')

try:
    from flask import Flask
    from extensions import db
    from config import Config
    
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    
    with app.app_context():
        # Importar modelos após inicializar o contexto
        from models.review import RevisorProcess
        from models.event import Formulario
        
        processo = RevisorProcess.query.get(6)
        print('=== DEBUG PROCESSO 6 ===')
        print('Processo encontrado:', processo is not None)
        
        if processo:
            print('ID:', processo.id)
            print('Nome:', processo.nome)
            print('Status:', processo.status)
            print('Formulario ID:', processo.formulario_id)
            print('Formulario objeto:', processo.formulario is not None)
            
            if processo.formulario:
                print('Formulario nome:', processo.formulario.nome)
                print('Numero de campos:', len(processo.formulario.campos))
                
                if len(processo.formulario.campos) == 0:
                    print('PROBLEMA: Formulario sem campos!')
                else:
                    print('Campos encontrados:')
                    for i, campo in enumerate(processo.formulario.campos):
                        print('  ' + str(i+1) + '. ' + campo.nome + ' (' + campo.tipo + ')')
            else:
                print('PROBLEMA: Processo sem formulario associado!')
        else:
            print('PROBLEMA: Processo 6 nao encontrado!')
            
except Exception as e:
    print('ERRO:', str(e))
    import traceback
    traceback.print_exc()