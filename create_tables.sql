-- Script SQL para criar as tabelas MaterialDisponivel e SolicitacaoMaterialFormador

-- Verificar se a tabela material_disponivel já existe
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'material_disponivel') THEN
        -- Criar tabela material_disponivel
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
        );
        
        -- Criar índices para material_disponivel
        CREATE INDEX ix_material_disponivel_cliente_id ON material_disponivel (cliente_id);
        CREATE INDEX ix_material_disponivel_material_id ON material_disponivel (material_id);
        
        RAISE NOTICE 'Tabela material_disponivel criada com sucesso!';
    ELSE
        RAISE NOTICE 'Tabela material_disponivel já existe.';
    END IF;
END
$$;

-- Verificar se a tabela solicitacao_material_formador já existe
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'solicitacao_material_formador') THEN
        -- Criar tabela solicitacao_material_formador
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
        );
        
        -- Criar índices para solicitacao_material_formador
        CREATE INDEX ix_solicitacao_material_formador_formador_id ON solicitacao_material_formador (formador_id);
        CREATE INDEX ix_solicitacao_material_formador_cliente_id ON solicitacao_material_formador (cliente_id);
        CREATE INDEX ix_solicitacao_material_formador_status ON solicitacao_material_formador (status);
        CREATE INDEX ix_solicitacao_material_formador_data_solicitacao ON solicitacao_material_formador (data_solicitacao);
        
        RAISE NOTICE 'Tabela solicitacao_material_formador criada com sucesso!';
    ELSE
        RAISE NOTICE 'Tabela solicitacao_material_formador já existe.';
    END IF;
END
$$;

-- Atualizar a versão da migração no Alembic
INSERT INTO alembic_version (version_num) VALUES ('d8e9f1a2b3c4') 
ON CONFLICT (version_num) DO NOTHING;

SELECT 'Migração aplicada com sucesso!' as resultado;