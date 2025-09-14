# -*- coding: utf-8 -*-

import os
import sys
from datetime import datetime

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app
    from extensions import db
    from sqlalchemy import text
    
    with app.app_context():
        print("Conectando ao banco de dados...")
        
        # Verificar se as tabelas já existem
        result = db.engine.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('material_disponivel', 'solicitacao_material_formador')
        """))
        
        existing_tables = [row[0] for row in result]
        print("Tabelas existentes: {}".format(existing_tables))
        
        if 'material_disponivel' not in existing_tables:
            print("Criando tabela material_disponivel...")
            db.engine.execute(text("""
                CREATE TABLE material_disponivel (
                    id SERIAL PRIMARY KEY,
                    material_id INTEGER NOT NULL,
                    cliente_id INTEGER NOT NULL,
                    quantidade_minima INTEGER NOT NULL DEFAULT 1,
                    quantidade_maxima INTEGER NOT NULL DEFAULT 100,
                    controle_estoque BOOLEAN NOT NULL DEFAULT true,
                    ativo BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (cliente_id) REFERENCES "user" (id) ON DELETE CASCADE,
                    FOREIGN KEY (material_id) REFERENCES material (id) ON DELETE CASCADE
                )
            """))
            
            # Criar índices
            db.engine.execute(text("CREATE INDEX ix_material_disponivel_cliente_id ON material_disponivel (cliente_id)"))
            db.engine.execute(text("CREATE INDEX ix_material_disponivel_material_id ON material_disponivel (material_id)"))
            print("Tabela material_disponivel criada com sucesso!")
        else:
            print("Tabela material_disponivel já existe.")
        
        if 'solicitacao_material_formador' not in existing_tables:
            print("Criando tabela solicitacao_material_formador...")
            db.engine.execute(text("""
                CREATE TABLE solicitacao_material_formador (
                    id SERIAL PRIMARY KEY,
                    formador_id INTEGER NOT NULL,
                    cliente_id INTEGER NOT NULL,
                    tipo_solicitacao VARCHAR(20) NOT NULL DEFAULT 'existente',
                    material_disponivel_id INTEGER,
                    nome_material VARCHAR(200),
                    descricao_material TEXT,
                    unidade_medida VARCHAR(50),
                    quantidade_solicitada INTEGER NOT NULL,
                    justificativa TEXT,
                    status VARCHAR(20) NOT NULL DEFAULT 'pendente',
                    quantidade_aprovada INTEGER,
                    observacoes_cliente TEXT,
                    entregue BOOLEAN NOT NULL DEFAULT false,
                    data_entrega TIMESTAMP,
                    observacoes_entrega TEXT,
                    data_solicitacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    data_resposta TIMESTAMP,
                    FOREIGN KEY (cliente_id) REFERENCES "user" (id) ON DELETE CASCADE,
                    FOREIGN KEY (formador_id) REFERENCES ministrante (id) ON DELETE CASCADE,
                    FOREIGN KEY (material_disponivel_id) REFERENCES material_disponivel (id) ON DELETE SET NULL
                )
            """))
            
            # Criar índices
            db.engine.execute(text("CREATE INDEX ix_solicitacao_material_formador_formador_id ON solicitacao_material_formador (formador_id)"))
            db.engine.execute(text("CREATE INDEX ix_solicitacao_material_formador_cliente_id ON solicitacao_material_formador (cliente_id)"))
            db.engine.execute(text("CREATE INDEX ix_solicitacao_material_formador_status ON solicitacao_material_formador (status)"))
            db.engine.execute(text("CREATE INDEX ix_solicitacao_material_formador_data_solicitacao ON solicitacao_material_formador (data_solicitacao)"))
            print("Tabela solicitacao_material_formador criada com sucesso!")
        else:
            print("Tabela solicitacao_material_formador já existe.")
        
        # Atualizar a tabela alembic_version
        print("Atualizando versão da migração...")
        db.engine.execute(text("INSERT INTO alembic_version (version_num) VALUES ('d8e9f1a2b3c4') ON CONFLICT (version_num) DO NOTHING"))
        
        print("Migração aplicada com sucesso!")
        
except Exception as e:
    print("Erro ao aplicar migração: {}".format(e))
    import traceback
    traceback.print_exc()