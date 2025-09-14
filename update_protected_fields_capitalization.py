#!/usr/bin/env python3
"""
Script para atualizar a capitalização dos campos protegidos 'nome' e 'email'
para 'Nome' e 'Email' diretamente no banco de dados.
"""

from app import create_app
from extensions import db
from models.event import CampoFormulario

def update_protected_fields_capitalization():
    """Atualiza a capitalização dos campos protegidos nome e email."""
    app = create_app()
    
    with app.app_context():
        try:
            # Buscar todos os campos protegidos com nome 'nome' ou 'email'
            campos_nome = CampoFormulario.query.filter_by(nome='nome', protegido=True).all()
            campos_email = CampoFormulario.query.filter_by(nome='email', protegido=True).all()
            
            updated_count = 0
            
            # Atualizar campos 'nome' para 'Nome'
            for campo in campos_nome:
                campo.nome = 'Nome'
                updated_count += 1
                print(f"Atualizando campo ID {campo.id}: 'nome' -> 'Nome'")
            
            # Atualizar campos 'email' para 'Email'
            for campo in campos_email:
                campo.nome = 'Email'
                updated_count += 1
                print(f"Atualizando campo ID {campo.id}: 'email' -> 'Email'")
            
            # Confirmar as alterações
            db.session.commit()
            
            print(f"\nSucesso! {updated_count} campos foram atualizados.")
            
            # Verificar os resultados
            print("\nVerificando os campos atualizados:")
            campos_nome_updated = CampoFormulario.query.filter_by(nome='Nome', protegido=True).all()
            campos_email_updated = CampoFormulario.query.filter_by(nome='Email', protegido=True).all()
            
            print(f"Campos 'Nome' encontrados: {len(campos_nome_updated)}")
            print(f"Campos 'Email' encontrados: {len(campos_email_updated)}")
            
        except Exception as e:
            print(f"Erro ao atualizar campos: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    update_protected_fields_capitalization()