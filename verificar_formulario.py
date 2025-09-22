from app import create_app
from models import Formulario, CampoFormulario, Evento, Usuario
from extensions import db

app = create_app()

with app.app_context():
    print("=== VERIFICAÇÃO DO FORMULÁRIO DE TRABALHOS ===")
    
    # Buscar formulário de trabalhos pelo ID 9
    formulario = Formulario.query.get(9)
    if not formulario:
        print("❌ Formulário ID 9 não encontrado!")
    else:
        print(f"✅ Formulário encontrado - ID: {formulario.id}, Nome: {formulario.nome}")
        
        # Verificar campos do formulário
        campos = formulario.campos
        print(f"\nCampos do formulário ({len(campos)}):")
        
        campos_obrigatorios = []
        for campo in campos:
            print(f"  - ID: {campo.id}, Nome: {campo.nome}, Tipo: {campo.tipo}, Obrigatório: {campo.obrigatorio}")
            if campo.opcoes:
                print(f"    Opções: {campo.opcoes}")
            if campo.obrigatorio:
                campos_obrigatorios.append(campo.nome)
        
        print(f"\nCampos obrigatórios: {campos_obrigatorios}")
    
    print("\n=== VERIFICAÇÃO DE EVENTOS COM FORMULÁRIO DE TRABALHOS ===")
    
    # Buscar eventos que têm o formulário de trabalhos associado
    eventos_com_formulario = []
    todos_eventos = Evento.query.all()
    
    for evento in todos_eventos:
        formularios_evento = list(evento.formularios)
        for form in formularios_evento:
            if form.id == 9:  # Formulário de Trabalhos
                eventos_com_formulario.append(evento)
                break
    
    print(f"Eventos com formulário de trabalhos ({len(eventos_com_formulario)}):")
    for evento in eventos_com_formulario:
        print(f"  - ID: {evento.id}, Nome: {evento.nome}, Status: {evento.status}")
    
    print("\n=== VERIFICAÇÃO DO USUÁRIO ANDRE ===")
    
    # Buscar usuário andre@teste.com
    usuario = Usuario.query.filter_by(email='andre@teste.com').first()
    if usuario:
        print(f"✅ Usuário encontrado - ID: {usuario.id}, Email: {usuario.email}")
        print(f"   Evento associado diretamente: {usuario.evento_id}")
        
        # Verificar evento associado diretamente
        if usuario.evento_id:
            evento = Evento.query.get(usuario.evento_id)
            if evento:
                print(f"\nEvento do usuário: ID {evento.id}, Nome: {evento.nome}, Status: {evento.status}")
                
                # Verificar formulários do evento
                formularios = list(evento.formularios)
                print(f"Formulários associados ({len(formularios)}):")
                for form in formularios:
                    print(f"  - ID: {form.id}, Nome: {form.nome}")
                    if form.id == 9:
                        print(f"    ✅ Este evento tem o formulário de trabalhos!")
        else:
            print("   Usuário não tem evento associado diretamente.")
    else:
        print("❌ Usuário andre@teste.com não encontrado!")
    
    print("\n=== VERIFICAÇÃO ESPECÍFICA DO EVENTO 12 ===")
    
    evento = Evento.query.get(12)
    if evento:
        print(f"Evento ID 12: {evento.nome}")
        formularios = list(evento.formularios)
        print(f"Formulários associados:")
        for form in formularios:
            print(f"  - ID: {form.id}, Nome: {form.nome}")
        
        # Verificar se precisa associar o formulário de trabalhos
        tem_formulario_trabalhos = any(f.id == 9 for f in formularios)
        if not tem_formulario_trabalhos:
            print("\n⚠️ PROBLEMA IDENTIFICADO: Evento 12 não tem o formulário de trabalhos associado!")
            print("   Isso explica por que o cadastro de trabalhos falha.")
            print("   Solução: Associar o formulário ID 9 ao evento ID 12.")
    
    print("\n=== TODOS OS EVENTOS E SEUS FORMULÁRIOS ===")
    
    todos_eventos = Evento.query.all()
    for evento in todos_eventos:
        formularios = list(evento.formularios)
        print(f"Evento ID {evento.id} ({evento.nome}):")
        if formularios:
            for form in formularios:
                print(f"  - Formulário ID {form.id}: {form.nome}")
        else:
            print(f"  - Nenhum formulário associado")
    
    print("\n=== DIAGNÓSTICO FINAL ===")
    
    # Verificar se o usuário andre está no evento 12
    usuario_andre = Usuario.query.filter_by(email='andre@teste.com').first()
    if usuario_andre and usuario_andre.evento_id == 12:
        print("✅ Usuário andre está associado ao evento 12")
        
        # Verificar se evento 12 tem formulário de trabalhos
        evento_12 = Evento.query.get(12)
        if evento_12:
            formularios_12 = list(evento_12.formularios)
            tem_form_trabalhos = any(f.id == 9 for f in formularios_12)
            
            if not tem_form_trabalhos:
                print("❌ CAUSA DO ERRO: Evento 12 não tem o formulário de trabalhos (ID 9) associado!")
                print("   O usuário está tentando cadastrar trabalho em um evento que não suporta isso.")
                print("\n🔧 SOLUÇÃO NECESSÁRIA:")
                print("   1. Associar o formulário de trabalhos (ID 9) ao evento 12")
                print("   2. OU associar o usuário a um evento que já tenha o formulário de trabalhos")
            else:
                print("✅ Evento 12 tem o formulário de trabalhos associado")
    else:
        print("ℹ️ Usuário andre não está associado ao evento 12 ou não foi encontrado")