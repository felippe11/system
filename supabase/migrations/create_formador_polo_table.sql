-- Criação da tabela formador_polo para associar formadores a polos
CREATE TABLE IF NOT EXISTS formador_polo (
    id SERIAL PRIMARY KEY,
    formador_id INTEGER NOT NULL REFERENCES ministrante(id) ON DELETE CASCADE,
    polo_id INTEGER NOT NULL REFERENCES polo(id) ON DELETE CASCADE,
    data_atribuicao TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ativo BOOLEAN DEFAULT TRUE,
    UNIQUE(formador_id, polo_id)
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_formador_polo_formador_id ON formador_polo(formador_id);
CREATE INDEX IF NOT EXISTS idx_formador_polo_polo_id ON formador_polo(polo_id);
CREATE INDEX IF NOT EXISTS idx_formador_polo_ativo ON formador_polo(ativo);

-- Comentários
COMMENT ON TABLE formador_polo IS 'Tabela para associar formadores (ministrantes) a polos específicos';
COMMENT ON COLUMN formador_polo.formador_id IS 'ID do formador (ministrante)';
COMMENT ON COLUMN formador_polo.polo_id IS 'ID do polo';
COMMENT ON COLUMN formador_polo.data_atribuicao IS 'Data e hora da atribuição do formador ao polo';
COMMENT ON COLUMN formador_polo.ativo IS 'Indica se a atribuição está ativa';

-- Permissões para roles anon e authenticated
GRANT SELECT ON formador_polo TO anon;
GRANT ALL PRIVILEGES ON formador_polo TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE formador_polo_id_seq TO authenticated;