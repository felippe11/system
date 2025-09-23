#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar se o nome do revisor está sendo salvo corretamente
na tabela avaliacao_barema após as modificações implementadas.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models.avaliacao import AvaliacaoBarema
from models.user import Usuario
from models.review import RevisorCandidatura

def testar_nome_revisor():
    """Testa se o campo nome_revisor foi adicionado e está funcionando."""
    app = create_app()
    
    with app.app_context():
        print("=== TESTE: Campo nome_revisor na tabela avaliacao_barema ===")
        print()
        
        # 1. Verificar se o campo nome_revisor existe na tabela
        try:
            # Tentar acessar o campo nome_revisor através do modelo
            avaliacao_teste = AvaliacaoBarema.query.first()
            if avaliacao_teste and hasattr(avaliacao_teste, 'nome_revisor'):
                print("✅ Campo 'nome_revisor' existe na tabela avaliacao_barema")
            else:
                print("❌ Campo 'nome_revisor' NÃO existe na tabela avaliacao_barema")
                return
        except Exception as e:
            print(f"❌ Erro ao verificar campo: {e}")
            return
        
        # 2. Verificar se há avaliações existentes
        avaliacoes = AvaliacaoBarema.query.limit(5).all()
        print(f"\n📊 Total de avaliações encontradas: {len(avaliacoes)}")
        
        if avaliacoes:
            print("\n=== AVALIAÇÕES EXISTENTES ===")
            for i, avaliacao in enumerate(avaliacoes, 1):
                print(f"\nAvaliação {i}:")
                print(f"  ID: {avaliacao.id}")
                print(f"  Revisor ID: {avaliacao.revisor_id}")
                print(f"  Nome Revisor: {getattr(avaliacao, 'nome_revisor', 'CAMPO NÃO EXISTE')}")
                print(f"  Categoria: {avaliacao.categoria}")
                print(f"  Data: {avaliacao.data_avaliacao}")
                
                # Verificar o nome do revisor através do relacionamento
                if avaliacao.revisor:
                    print(f"  Nome do Usuário (relacionamento): {avaliacao.revisor.nome}")
        
        # 3. Verificar candidaturas de revisores
        print("\n=== CANDIDATURAS DE REVISORES ===")
        candidaturas = RevisorCandidatura.query.limit(3).all()
        for candidatura in candidaturas:
            print(f"\nCandidatura:")
            print(f"  Nome: {candidatura.nome}")
            print(f"  Email: {candidatura.email}")
            print(f"  Status: {candidatura.status}")
            print(f"  Código: {candidatura.codigo}")
            
            # Verificar se há usuário correspondente
            usuario = Usuario.query.filter_by(email=candidatura.email).first()
            if usuario:
                print(f"  Usuário correspondente: {usuario.nome} (ID: {usuario.id})")
        
        # 4. Simular a lógica de determinação do nome do revisor
        print("\n=== TESTE DA LÓGICA DE NOME DO REVISOR ===")
        
        # Buscar uma candidatura aprovada para teste
        candidatura_teste = RevisorCandidatura.query.filter_by(status='aprovado').first()
        if candidatura_teste:
            print(f"\nTestando com candidatura: {candidatura_teste.nome}")
            
            # Aplicar a mesma lógica da rota
            nome_revisor = candidatura_teste.nome
            if candidatura_teste.status == 'aprovado':
                revisor_user = Usuario.query.filter_by(email=candidatura_teste.email).first()
                if revisor_user and revisor_user.nome:
                    nome_revisor = revisor_user.nome
            
            print(f"Nome final determinado: {nome_revisor}")
        else:
            print("Nenhuma candidatura aprovada encontrada para teste")
        
        print("\n=== TESTE CONCLUÍDO ===")

if __name__ == "__main__":
    testar_nome_revisor()