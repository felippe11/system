#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para criar níveis de aprovação iniciais no sistema.
"""

import os
import sys
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.compra import NivelAprovacao
from models.user import Cliente

def criar_niveis_aprovacao_iniciais():
    """Cria níveis de aprovação iniciais para demonstração."""
    app = create_app()
    
    with app.app_context():
        try:
            # Buscar todos os clientes para criar níveis para cada um
            clientes = Cliente.query.all()
            
            if not clientes:
                print("Nenhum cliente encontrado. Criando níveis para cliente padrão (ID=1)")
                cliente_ids = [1]
            else:
                cliente_ids = [cliente.id for cliente in clientes]
            
            niveis_criados = 0
            
            for cliente_id in cliente_ids:
                # Verificar se já existem níveis para este cliente
                niveis_existentes = NivelAprovacao.query.filter_by(cliente_id=cliente_id).count()
                
                if niveis_existentes > 0:
                    print(f"Cliente {cliente_id} já possui {niveis_existentes} níveis de aprovação")
                    continue
                
                # Criar níveis de aprovação padrão
                niveis_padrao = [
                    {
                        'nome': 'Supervisor Direto',
                        'descricao': 'Aprovação do supervisor direto para compras até R$ 5.000',
                        'ordem': 1,
                        'valor_minimo': 0.0,
                        'valor_maximo': 5000.0,
                        'obrigatorio': True,
                        'ativo': True,
                        'cliente_id': cliente_id
                    },
                    {
                        'nome': 'Gerente de Área',
                        'descricao': 'Aprovação do gerente para compras de R$ 5.001 até R$ 20.000',
                        'ordem': 2,
                        'valor_minimo': 5001.0,
                        'valor_maximo': 20000.0,
                        'obrigatorio': True,
                        'ativo': True,
                        'cliente_id': cliente_id
                    },
                    {
                        'nome': 'Diretor Financeiro',
                        'descricao': 'Aprovação do diretor financeiro para compras de R$ 20.001 até R$ 50.000',
                        'ordem': 3,
                        'valor_minimo': 20001.0,
                        'valor_maximo': 50000.0,
                        'obrigatorio': True,
                        'ativo': True,
                        'cliente_id': cliente_id
                    },
                    {
                        'nome': 'Diretoria Executiva',
                        'descricao': 'Aprovação da diretoria executiva para compras acima de R$ 50.000',
                        'ordem': 4,
                        'valor_minimo': 50001.0,
                        'valor_maximo': None,  # Sem limite máximo
                        'obrigatorio': True,
                        'ativo': True,
                        'cliente_id': cliente_id
                    }
                ]
                
                for nivel_data in niveis_padrao:
                    nivel = NivelAprovacao(**nivel_data)
                    db.session.add(nivel)
                    niveis_criados += 1
                
                print(f"Criados 4 níveis de aprovação para cliente {cliente_id}")
            
            # Commit das alterações
            db.session.commit()
            print(f"\n✓ Total de {niveis_criados} níveis de aprovação criados com sucesso!")
            
            # Listar níveis criados
            print("\nNíveis de aprovação criados:")
            niveis = NivelAprovacao.query.order_by(NivelAprovacao.cliente_id, NivelAprovacao.ordem).all()
            for nivel in niveis:
                valor_max = f"R$ {nivel.valor_maximo:,.2f}" if nivel.valor_maximo else "Sem limite"
                print(f"  Cliente {nivel.cliente_id} - {nivel.nome}: R$ {nivel.valor_minimo:,.2f} até {valor_max}")
                
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao criar níveis de aprovação: {e}")
            return False
            
    return True

if __name__ == '__main__':
    print("Criando níveis de aprovação iniciais...")
    criar_niveis_aprovacao_iniciais()