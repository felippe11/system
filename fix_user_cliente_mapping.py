#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corrigir o mapeamento entre Usuario e Cliente
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.user import Usuario, Cliente
from extensions import db

def fix_user_cliente_mapping():
    app = create_app()
    
    with app.app_context():
        print("=== Corrigindo mapeamento Usuario-Cliente ===")
        
        # 1. Verificar Usuario ID 7
        usuario = Usuario.query.get(7)
        if usuario:
            print(f"\n1. Usuario encontrado:")
            print(f"  - ID: {usuario.id}")
            print(f"  - Nome: {usuario.nome}")
            print(f"  - Email: {usuario.email}")
            print(f"  - Tipo: {usuario.tipo}")
        else:
            print("\n1. Usuario ID 7 não encontrado!")
            return
        
        # 2. Verificar Cliente com mesmo email
        cliente = Cliente.query.filter_by(email=usuario.email).first()
        if cliente:
            print(f"\n2. Cliente encontrado por email:")
            print(f"  - ID: {cliente.id}")
            print(f"  - Nome: {cliente.nome}")
            print(f"  - Email: {cliente.email}")
        else:
            print(f"\n2. Cliente não encontrado por email: {usuario.email}")
            return
        
        # 3. Verificar se existe Cliente com ID 7
        cliente_id_7 = Cliente.query.get(7)
        if cliente_id_7:
            print(f"\n3. Cliente ID 7 já existe:")
            print(f"  - Nome: {cliente_id_7.nome}")
            print(f"  - Email: {cliente_id_7.email}")
        else:
            print(f"\n3. Cliente ID 7 não existe - este é o problema!")
            
            # Criar Cliente com ID 7 baseado no Usuario
            print(f"\n4. Criando Cliente ID 7 baseado no Usuario...")
            try:
                # Primeiro, vamos verificar se podemos inserir com ID específico
                novo_cliente = Cliente(
                    nome=usuario.nome,
                    email=usuario.email,
                    senha=usuario.senha,
                    ativo=True,
                    tipo='cliente'
                )
                db.session.add(novo_cliente)
                db.session.flush()  # Para obter o ID
                
                print(f"  - Cliente criado com ID: {novo_cliente.id}")
                
                # Se o ID não for 7, precisamos ajustar
                if novo_cliente.id != 7:
                    print(f"  - ID gerado ({novo_cliente.id}) != 7, ajustando...")
                    
                    # Rollback e tentar forçar ID 7
                    db.session.rollback()
                    
                    # Inserir diretamente com ID 7
                    db.session.execute(
                        "INSERT INTO cliente (id, nome, email, senha, ativo, tipo) VALUES (:id, :nome, :email, :senha, :ativo, :tipo)",
                        {
                            'id': 7,
                            'nome': usuario.nome,
                            'email': usuario.email,
                            'senha': usuario.senha,
                            'ativo': True,
                            'tipo': 'cliente'
                        }
                    )
                    db.session.commit()
                    print(f"  - Cliente ID 7 criado com sucesso!")
                else:
                    db.session.commit()
                    print(f"  - Cliente ID 7 criado com sucesso!")
                
            except Exception as e:
                db.session.rollback()
                print(f"  - Erro ao criar Cliente: {e}")
                return
        
        # 5. Verificar eventos
        from models.event import Evento
        eventos = Evento.query.all()
        print(f"\n5. Eventos existentes:")
        for evento in eventos:
            print(f"  - ID: {evento.id}, Nome: {evento.nome}, Cliente ID: {evento.cliente_id}")
        
        # 6. Atualizar eventos do cliente ID 4 para ID 7 se necessário
        eventos_cliente_4 = Evento.query.filter_by(cliente_id=4).all()
        if eventos_cliente_4:
            print(f"\n6. Atualizando eventos do cliente ID 4 para ID 7...")
            for evento in eventos_cliente_4:
                evento.cliente_id = 7
                print(f"  - Evento '{evento.nome}' atualizado")
            db.session.commit()
            print(f"  - {len(eventos_cliente_4)} eventos atualizados!")
        
        print(f"\n=== Correção concluída ===")

if __name__ == '__main__':
    fix_user_cliente_mapping()