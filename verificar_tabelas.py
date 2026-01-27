#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from sqlalchemy import text

def verificar_estrutura_banco():
    """Verifica a estrutura das tabelas no banco de dados"""
    app = create_app()
    
    with app.app_context():
        try:
            # Verificar tabelas disponíveis
            print("=== TABELAS DISPONÍVEIS ===")
            result = db.session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            
            tabelas = [row[0] for row in result.fetchall()]
            for tabela in tabelas:
                print(f"- {tabela}")
            
            # Verificar colunas da tabela usuario
            if 'usuario' in tabelas:
                print("\n=== COLUNAS DA TABELA USUARIO ===")
                result = db.session.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'usuario' AND table_schema = 'public'
                    ORDER BY ordinal_position
                """))
                
                for row in result.fetchall():
                    print(f"- {row[0]} ({row[1]})")
            
            # Verificar colunas da tabela avaliacao_barema
            if 'avaliacao_barema' in tabelas:
                print("\n=== COLUNAS DA TABELA AVALIACAO_BAREMA ===")
                result = db.session.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'avaliacao_barema' AND table_schema = 'public'
                    ORDER BY ordinal_position
                """))
                
                for row in result.fetchall():
                    print(f"- {row[0]} ({row[1]})")
            
            # Buscar usuários com nome similar a Xerosvaldo
            print("\n=== USUÁRIOS COM NOME SIMILAR A XEROSVALDO ===")
            result = db.session.execute(text("""
                SELECT id, nome, email 
                FROM usuario 
                WHERE nome ILIKE '%xerosvaldo%' OR nome ILIKE '%xerosval%'
                ORDER BY nome
            """))
            
            usuarios = result.fetchall()
            if usuarios:
                for usuario in usuarios:
                    print(f"ID: {usuario[0]}, Nome: {usuario[1]}, Email: {usuario[2]}")
            else:
                print("Nenhum usuário encontrado com nome similar a Xerosvaldo")
            
            # Buscar usuário Andre Teste
            print("\n=== USUÁRIO ANDRE TESTE ===")
            result = db.session.execute(text("""
                SELECT id, nome, email 
                FROM usuario 
                WHERE nome ILIKE '%andre%teste%' OR nome ILIKE '%andre teste%'
                ORDER BY nome
            """))
            
            usuarios = result.fetchall()
            if usuarios:
                for usuario in usuarios:
                    print(f"ID: {usuario[0]}, Nome: {usuario[1]}, Email: {usuario[2]}")
            else:
                print("Nenhum usuário encontrado com nome Andre Teste")
            
            # Verificar avaliações de barema recentes
            if 'avaliacao_barema' in tabelas:
                print("\n=== AVALIAÇÕES DE BAREMA RECENTES ===")
                result = db.session.execute(text("""
                    SELECT ab.id, ab.revisor_id, u.nome as revisor_nome, ab.created_at
                    FROM avaliacao_barema ab
                    LEFT JOIN usuario u ON ab.revisor_id = u.id
                    ORDER BY ab.created_at DESC
                    LIMIT 10
                """))
                
                avaliacoes = result.fetchall()
                if avaliacoes:
                    for avaliacao in avaliacoes:
                        print(f"ID: {avaliacao[0]}, Revisor ID: {avaliacao[1]}, Nome: {avaliacao[2]}, Data: {avaliacao[3]}")
                else:
                    print("Nenhuma avaliação de barema encontrada")
                    
        except Exception as e:
            print(f"Erro ao verificar estrutura do banco: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    verificar_estrutura_banco()