#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnóstico para investigar discrepância entre revisor esperado e exibido
"""

import psycopg2
import psycopg2.extras
import os
from datetime import datetime
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

def conectar_banco():
    """Conecta ao banco de dados PostgreSQL"""
    try:
        # Tenta usar DATABASE_URL primeiro
        database_url = os.getenv("DB_ONLINE") or os.getenv("DATABASE_URL")
        
        if database_url:
            # psycopg2 aceita postgresql:// diretamente
            conn = psycopg2.connect(database_url)
        else:
            # Usa parâmetros individuais
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                database=os.getenv("DB_NAME", "iafap_database"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASS", "postgres")
            )
        
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")
        return None

def verificar_usuarios():
    """Verifica todos os usuários cadastrados"""
    conn = conectar_banco()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nome, email, tipo_usuario 
            FROM usuario 
            ORDER BY id
        """)
        
        usuarios = cursor.fetchall()
        
        print("\n=== USUÁRIOS CADASTRADOS ===")
        print(f"Total de usuários: {len(usuarios)}")
        print("-" * 60)
        
        for usuario in usuarios:
            print(f"ID: {usuario['id']} | Nome: {usuario['nome']} | Email: {usuario['email']} | Tipo: {usuario['tipo_usuario']}")
        
        # Procurar especificamente por Xerosvaldo
        cursor.execute("""
            SELECT id, nome, email, tipo_usuario 
            FROM usuario 
            WHERE nome ILIKE %s OR nome ILIKE %s
        """, ('%Xerosvaldo%', '%xerosvaldo%'))
        
        xerosvaldo = cursor.fetchall()
        
        print("\n=== BUSCA POR XEROSVALDO ===")
        if xerosvaldo:
            for user in xerosvaldo:
                print(f"ENCONTRADO - ID: {user['id']} | Nome: {user['nome']} | Email: {user['email']}")
        else:
            print("NENHUM usuário com nome 'Xerosvaldo' encontrado")
        
    except Exception as e:
        print(f"Erro ao verificar usuários: {e}")
    finally:
        conn.close()

def verificar_avaliacoes_barema():
    """Verifica todas as avaliações de barema"""
    conn = conectar_banco()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ab.id, ab.revisor_id, ab.submission_id, ab.data_avaliacao,
                   u.nome as revisor_nome, u.email as revisor_email,
                   s.title as trabalho_titulo
            FROM avaliacao_barema ab
            LEFT JOIN usuario u ON ab.revisor_id = u.id
            LEFT JOIN submission s ON ab.submission_id = s.id
            ORDER BY ab.id
        """)
        
        avaliacoes = cursor.fetchall()
        
        print("\n=== AVALIAÇÕES DE BAREMA ===")
        print(f"Total de avaliações: {len(avaliacoes)}")
        print("-" * 80)
        
        for avaliacao in avaliacoes:
            data_formatada = avaliacao['data_avaliacao'] if avaliacao['data_avaliacao'] else 'N/A'
            print(f"ID: {avaliacao['id']} | Revisor ID: {avaliacao['revisor_id']} | Nome: {avaliacao['revisor_nome']} | Email: {avaliacao['revisor_email']}")
            print(f"  Trabalho: {avaliacao['trabalho_titulo']} | Data: {data_formatada}")
            print("-" * 80)
        
    except Exception as e:
        print(f"Erro ao verificar avaliações: {e}")
    finally:
        conn.close()

def verificar_associacao_revisor_trabalho():
    """Verifica a associação entre revisores e trabalhos"""
    conn = conectar_banco()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # Verificar se existe alguma avaliação com Xerosvaldo
        cursor.execute("""
            SELECT ab.id, ab.revisor_id, u.nome as revisor_nome, s.title as trabalho_titulo
            FROM avaliacao_barema ab
            LEFT JOIN usuario u ON ab.revisor_id = u.id
            LEFT JOIN submission s ON ab.submission_id = s.id
            WHERE u.nome ILIKE %s OR u.nome ILIKE %s
        """, ('%Xerosvaldo%', '%xerosvaldo%'))
        
        avaliacoes_xerosvaldo = cursor.fetchall()
        
        print("\n=== AVALIAÇÕES DE XEROSVALDO ===")
        if avaliacoes_xerosvaldo:
            for avaliacao in avaliacoes_xerosvaldo:
                print(f"Avaliação ID: {avaliacao['id']} | Revisor ID: {avaliacao['revisor_id']} | Nome: {avaliacao['revisor_nome']}")
                print(f"  Trabalho: {avaliacao['trabalho_titulo']}")
        else:
            print("NENHUMA avaliação encontrada para Xerosvaldo")
        
        # Verificar se existe alguma avaliação com Andre Teste
        cursor.execute("""
            SELECT ab.id, ab.revisor_id, u.nome as revisor_nome, s.title as trabalho_titulo
            FROM avaliacao_barema ab
            LEFT JOIN usuario u ON ab.revisor_id = u.id
            LEFT JOIN submission s ON ab.submission_id = s.id
            WHERE u.nome ILIKE %s OR u.nome ILIKE %s
        """, ('%Andre%', '%andre%'))
        
        avaliacoes_andre = cursor.fetchall()
        
        print("\n=== AVALIAÇÕES DE ANDRE ===")
        if avaliacoes_andre:
            for avaliacao in avaliacoes_andre:
                print(f"Avaliação ID: {avaliacao['id']} | Revisor ID: {avaliacao['revisor_id']} | Nome: {avaliacao['revisor_nome']}")
                print(f"  Trabalho: {avaliacao['trabalho_titulo']}")
        else:
            print("NENHUMA avaliação encontrada para Andre")
        
    except Exception as e:
        print(f"Erro ao verificar associações: {e}")
    finally:
        conn.close()

def main():
    """Função principal do diagnóstico"""
    print("=" * 80)
    print("DIAGNÓSTICO DE DISCREPÂNCIA DE REVISOR")
    print(f"Executado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Executar todas as verificações
    verificar_usuarios()
    verificar_avaliacoes_barema()
    verificar_associacao_revisor_trabalho()
    
    print("\n=" * 80)
    print("DIAGNÓSTICO CONCLUÍDO")
    print("=" * 80)

if __name__ == "__main__":
    main()