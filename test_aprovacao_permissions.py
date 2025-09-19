#!/usr/bin/env python3
"""
Script para testar e configurar permissões de aprovação de compras
"""

import os
import sys
from flask import Flask
from extensions import db
from models.user import Usuario

def create_app():
    """Criar aplicação Flask para teste"""
    app = Flask(__name__)
    
    # Configuração básica
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-key'
    
    # Inicializar extensões
    db.init_app(app)
    
    return app

def test_user_permissions():
    """Testar permissões de usuários"""
    app = create_app()
    
    with app.app_context():
        print("=== Testando Permissões de Aprovação ===\n")
        
        # Buscar usuários
        usuarios = Usuario.query.all()
        
        print(f"Total de usuários encontrados: {len(usuarios)}\n")
        
        for usuario in usuarios[:10]:  # Mostrar apenas os primeiros 10
            print(f"Usuário: {usuario.nome}")
            print(f"  Email: {usuario.email}")
            print(f"  Tipo: {usuario.tipo}")
            print(f"  Admin: {usuario.is_admin}")
            print(f"  Pode aprovar compras: {getattr(usuario, 'pode_aprovar_compras', 'CAMPO NÃO EXISTE')}")
            print(f"  Ativo: {usuario.ativo}")
            print("-" * 50)

def grant_approval_permission(email):
    """Conceder permissão de aprovação para um usuário"""
    app = create_app()
    
    with app.app_context():
        usuario = Usuario.query.filter_by(email=email).first()
        
        if not usuario:
            print(f"Usuário com email {email} não encontrado!")
            return False
        
        # Verificar se o campo existe
        if not hasattr(usuario, 'pode_aprovar_compras'):
            print("ERRO: Campo 'pode_aprovar_compras' não existe no modelo!")
            return False
        
        usuario.pode_aprovar_compras = True
        db.session.commit()
        
        print(f"Permissão de aprovação concedida para {usuario.nome} ({email})")
        return True

def list_admin_users():
    """Listar usuários admin"""
    app = create_app()
    
    with app.app_context():
        admins = Usuario.query.filter_by(tipo='admin').all()
        
        print(f"=== Usuários Admin ({len(admins)}) ===\n")
        
        for admin in admins:
            print(f"Nome: {admin.nome}")
            print(f"Email: {admin.email}")
            print(f"Pode aprovar: {getattr(admin, 'pode_aprovar_compras', 'N/A')}")
            print("-" * 30)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test":
            test_user_permissions()
        elif command == "grant" and len(sys.argv) > 2:
            email = sys.argv[2]
            grant_approval_permission(email)
        elif command == "admins":
            list_admin_users()
        else:
            print("Uso:")
            print("  python test_aprovacao_permissions.py test")
            print("  python test_aprovacao_permissions.py grant <email>")
            print("  python test_aprovacao_permissions.py admins")
    else:
        print("Comandos disponíveis:")
        print("  test - Testar permissões de usuários")
        print("  grant <email> - Conceder permissão de aprovação")
        print("  admins - Listar usuários admin")