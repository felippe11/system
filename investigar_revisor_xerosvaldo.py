#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from sqlalchemy import text

def investigar_revisor_problema():
    """Investiga por que Xerosvaldo não aparece como revisor"""
    app = create_app()
    
    with app.app_context():
        try:
            print("=== INVESTIGAÇÃO DO PROBLEMA DO REVISOR ===")
            
            # 1. Verificar dados dos usuários relevantes
            print("\n1. DADOS DOS USUÁRIOS RELEVANTES:")
            result = db.session.execute(text("""
                SELECT id, nome, email, tipo, ativo
                FROM usuario 
                WHERE id IN (7, 417)
                ORDER BY id
            """))
            
            for row in result.fetchall():
                print(f"   ID: {row[0]}, Nome: {row[1]}, Email: {row[2]}, Tipo: {row[3]}, Ativo: {row[4]}")
            
            # 2. Verificar todas as avaliações de barema
            print("\n2. TODAS AS AVALIAÇÕES DE BAREMA:")
            result = db.session.execute(text("""
                SELECT ab.id, ab.trabalho_id, ab.revisor_id, u.nome as revisor_nome, 
                       ab.categoria, ab.nota_final, ab.data_avaliacao, ab.created_at
                FROM avaliacao_barema ab
                LEFT JOIN usuario u ON ab.revisor_id = u.id
                ORDER BY ab.created_at DESC
            """))
            
            avaliacoes = result.fetchall()
            if avaliacoes:
                for av in avaliacoes:
                    print(f"   ID: {av[0]}, Trabalho: {av[1]}, Revisor ID: {av[2]}, Nome: {av[3]}")
                    print(f"      Categoria: {av[4]}, Nota: {av[5]}, Data Avaliação: {av[6]}, Criado: {av[7]}")
                    print()
            else:
                print("   Nenhuma avaliação encontrada")
            
            # 3. Verificar se existe tabela de trabalhos
            print("\n3. VERIFICANDO TABELA DE TRABALHOS:")
            result = db.session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name LIKE '%trabalho%'
            """))
            
            tabelas_trabalho = [row[0] for row in result.fetchall()]
            print(f"   Tabelas relacionadas a trabalho: {tabelas_trabalho}")
            
            # 4. Se existe tabela trabalho, verificar dados
            if 'trabalho' in tabelas_trabalho:
                print("\n4. DADOS DA TABELA TRABALHO:")
                result = db.session.execute(text("""
                    SELECT id, titulo, autor_id, revisor_id, status
                    FROM trabalho
                    ORDER BY id DESC
                    LIMIT 10
                """))
                
                trabalhos = result.fetchall()
                if trabalhos:
                    for trabalho in trabalhos:
                        print(f"   ID: {trabalho[0]}, Título: {trabalho[1][:50]}..., Autor: {trabalho[2]}, Revisor: {trabalho[3]}, Status: {trabalho[4]}")
                else:
                    print("   Nenhum trabalho encontrado")
            
            # 5. Verificar se existe tabela submission (pode ser usada em vez de trabalho)
            if 'submission' in tabelas_trabalho:
                print("\n5. DADOS DA TABELA SUBMISSION:")
                result = db.session.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'submission' AND table_schema = 'public'
                    ORDER BY ordinal_position
                """))
                
                print("   Colunas da tabela submission:")
                for row in result.fetchall():
                    print(f"   - {row[0]} ({row[1]})")
                
                # Verificar dados da submission
                result = db.session.execute(text("""
                    SELECT id, title, author_id, reviewer_id, status
                    FROM submission
                    ORDER BY id DESC
                    LIMIT 10
                """))
                
                submissions = result.fetchall()
                if submissions:
                    print("\n   Dados das submissions:")
                    for sub in submissions:
                        print(f"   ID: {sub[0]}, Título: {sub[1][:50] if sub[1] else 'N/A'}..., Autor: {sub[2]}, Revisor: {sub[3]}, Status: {sub[4]}")
                else:
                    print("   Nenhuma submission encontrada")
            
            # 6. Verificar qual trabalho está sendo avaliado por Xerosvaldo
            print("\n6. TRABALHOS AVALIADOS POR XEROSVALDO (ID 417):")
            result = db.session.execute(text("""
                SELECT