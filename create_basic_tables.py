#!/usr/bin/env python3
"""Script para criar tabelas básicas necessárias"""

import sqlite3
import os

# Conectar ao banco de dados SQLite
db_path = os.path.join('instance', 'database.db')
os.makedirs('instance', exist_ok=True)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Tabela cliente já existe, não precisa criar

# Criar tabela formularios
cursor.execute('''
CREATE TABLE IF NOT EXISTS formularios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    data_inicio DATETIME,
    data_fim DATETIME,
    permitir_multiplas_respostas BOOLEAN DEFAULT 1,
    is_submission_form BOOLEAN DEFAULT 0,
    cliente_id INTEGER,
    FOREIGN KEY (cliente_id) REFERENCES cliente (id)
)
''')

# Criar tabela configuracao_relatorio_formador
cursor.execute('''
CREATE TABLE IF NOT EXISTS configuracao_relatorio_formador (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    nome VARCHAR(255) NOT NULL,
    tipo_periodo VARCHAR(20) NOT NULL,
    campos_relatorio TEXT NOT NULL,
    ativo BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES cliente (id)
)
''')

# Criar tabela ministrante
cursor.execute('''
CREATE TABLE IF NOT EXISTS ministrante (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(255) NOT NULL,
    formacao VARCHAR(255) NOT NULL,
    areas_atuacao VARCHAR(255) NOT NULL,
    cpf VARCHAR(20) UNIQUE NOT NULL,
    pix VARCHAR(255) NOT NULL,
    cidade VARCHAR(255) NOT NULL,
    estado VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    senha VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    cliente_id INTEGER,
    FOREIGN KEY (cliente_id) REFERENCES cliente (id)
)
''')

# Criar tabela oficina
cursor.execute('''
CREATE TABLE IF NOT EXISTS oficina (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

# Criar tabela relatorio_formador
cursor.execute('''
CREATE TABLE IF NOT EXISTS relatorio_formador (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    configuracao_id INTEGER NOT NULL,
    formador_id INTEGER NOT NULL,
    atividade_id INTEGER,
    periodo_inicio DATE,
    periodo_fim DATE,
    dados_relatorio TEXT NOT NULL,
    data_envio DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (configuracao_id) REFERENCES configuracao_relatorio_formador (id),
    FOREIGN KEY (formador_id) REFERENCES ministrante (id),
    FOREIGN KEY (atividade_id) REFERENCES oficina (id)
)
''')

# Inserir registros padrão (ajustado para estrutura existente)
cursor.execute('''
INSERT OR IGNORE INTO cliente (id, nome, email, ativo)
VALUES (1, 'Cliente Teste', 'cliente@teste.com', 1)
''')

cursor.execute('''
INSERT OR IGNORE INTO formularios (id, nome, descricao, permitir_multiplas_respostas, is_submission_form)
VALUES (1, 'Formulário de Trabalhos', 'Formulário para cadastro de trabalhos acadêmicos pelos clientes', 1, 0)
''')

cursor.execute('''
INSERT OR IGNORE INTO configuracao_relatorio_formador (id, cliente_id, nome, tipo_periodo, campos_relatorio, ativo)
VALUES (1, 1, 'Relatório Mensal', 'mensal', '[]', 1)
''')

conn.commit()
conn.close()

print("Tabelas básicas criadas com sucesso!")