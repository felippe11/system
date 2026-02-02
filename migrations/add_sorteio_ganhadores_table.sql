-- Migração para adicionar a tabela de associação sorteio_ganhadores
-- Esta tabela permite que um sorteio tenha múltiplos ganhadores

CREATE TABLE IF NOT EXISTS sorteio_ganhadores (
    sorteio_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    PRIMARY KEY (sorteio_id, usuario_id),
    FOREIGN KEY (sorteio_id) REFERENCES sorteio(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuario(id) ON DELETE CASCADE
);

-- Criar índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_sorteio_ganhadores_sorteio ON sorteio_ganhadores(sorteio_id);
CREATE INDEX IF NOT EXISTS idx_sorteio_ganhadores_usuario ON sorteio_ganhadores(usuario_id);
