from app import create_app
from models import Formulario, Evento, Usuario
from extensions import db

app = create_app()

with app.app_context():
    print("=== CORREÇÃO DA ASSOCIAÇÃO FORMULÁRIO-EVENTO ===")
    
    # Buscar formulário de trabalhos (ID 9)
    formulario = Formulario.query.get(9)
    if not formulario:
        print("❌ Formulário ID 9 não encontrado!")
        exit(1)
    
    # Buscar evento 12
    evento = Evento.query.get(12)
    if not evento:
        print("❌ Evento ID 12 não encontrado!")
        exit(1)
    
    print(f"✅ Formulário encontrado: {formulario.nome} (ID: {formulario.id})")
    print(f"✅ Evento encontrado: {evento.nome} (ID: {evento.id})")
    
    # Verificar se já está associado
    formularios_evento = list(evento.formularios)
    ja_associado = any(f.id == 9 for f in formularios_evento)
    
    if ja_associado:
        print("ℹ️ Formulário já está associado ao evento.")
    else:
        print("\n🔧 Associando formulário ao evento...")
        
        # Associar formulário ao evento
        evento.formularios.append(formulario)
        
        try:
            db.session.commit()
            print("✅ Formulário associado com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao associar formulário: {e}")
            exit(1)
    
    print("\n=== VERIFICAÇÃO DA ASSOCIAÇÃO DO USUÁRIO ===")
    
    # Buscar usuário andre
    usuario = Usuario.query.filter_by(email='andre@teste.com').first()
    if not usuario:
        print("❌ Usuário andre@teste.com não encontrado!")
        exit(1)
    
    print(f"✅ Usuário encontrado: {usuario.email} (ID: {usuario.id})")
    print(f"   Evento atual: {usuario.evento_id}")
    
    # Verificar se usuário está associado ao evento 12
    if usuario.evento_id != 12:
        print("\n🔧 Associando usuário ao evento 12...")
        
        usuario.evento_id = 12
        
        try:
            db.session.commit()
            print("✅ Usuário associado ao evento 12 com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao associar usuário: {e}")
            exit(1)
    else:
        print("ℹ️ Usuário já está associado ao evento 12.")
    
    print("\n=== VERIFICAÇÃO FINAL ===")
    
    # Recarregar dados
    evento = Evento.query.get(12)
    usuario = Usuario.query.filter_by(email='andre@teste.com').first()
    
    formularios_evento = list(evento.formularios)
    tem_formulario_trabalhos = any(f.id == 9 for f in formularios_evento)
    
    print(f"Evento 12 ({evento.nome}):")
    print(f"  - Formulários associados: {len(formularios_evento)}")
    for form in formularios_evento:
        print(f"    - {form.nome} (ID: {form.id})")
    
    print(f"\nUsuário {usuario.email}:")
    print(f"  - Evento associado: {usuario.evento_id}")
    
    if tem_formulario_trabalhos and usuario.evento_id == 12:
        print("\n🎉 CORREÇÃO CONCLUÍDA COM SUCESSO!")
        print("   O usuário agora pode cadastrar trabalhos no evento 12.")
    else:
        print("\n❌ Ainda há problemas na configuração.")
        if not tem_formulario_trabalhos:
            print("   - Formulário de trabalhos não está associado ao evento")
        if usuario.evento_id != 12:
            print("   - Usuário não está associado ao evento 12")