#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from sqlalchemy import text

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    from extensions import db
    
    # Criar a aplicação
    app = create_app()
    
    with app.app_context():
        print("Conectando ao banco de dados...")
        
        # Ler o arquivo SQL
        with open('fix_canceled_appointments_slots.sql', 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Dividir o conteúdo em comandos individuais
        # Remover comentários e comandos vazios
        commands = []
        current_command = []
        
        for line in sql_content.split('\n'):
            line = line.strip()
            
            # Pular linhas vazias e comentários
            if not line or line.startswith('--'):
                continue
                
            # Pular blocos de comentários /* */
            if line.startswith('/*'):
                continue
                
            current_command.append(line)
            
            # Se a linha termina com ';', é o fim de um comando
            if line.endswith(';'):
                command_text = ' '.join(current_command)
                if command_text.strip():
                    commands.append(command_text)
                current_command = []
        
        # Executar cada comando
        for i, command in enumerate(commands, 1):
            try:
                print(f"\nExecutando comando {i}:")
                print(f"{command[:100]}..." if len(command) > 100 else command)
                
                result = db.session.execute(text(command))
                
                # Se é um SELECT, mostrar os resultados
                if command.strip().upper().startswith('SELECT'):
                    rows = result.fetchall()
                    if rows:
                        print(f"Resultado: {len(rows)} linha(s) encontrada(s)")
                        for row in rows[:5]:  # Mostrar apenas as primeiras 5 linhas
                            print(f"  {dict(row)}")
                        if len(rows) > 5:
                            print(f"  ... e mais {len(rows) - 5} linha(s)")
                    else:
                        print("Nenhuma linha encontrada")
                
                # Se é um UPDATE, mostrar quantas linhas foram afetadas
                elif command.strip().upper().startswith('UPDATE'):
                    print(f"Linhas afetadas: {result.rowcount}")
                
                db.session.commit()
                print("✓ Comando executado com sucesso")
                
            except Exception as e:
                print(f"✗ Erro ao executar comando {i}: {e}")
                db.session.rollback()
                continue
        
        print("\n=== Execução do script SQL concluída ===")
        
except Exception as e:
    print(f"Erro geral: {e}")
    import traceback
    traceback.print_exc()