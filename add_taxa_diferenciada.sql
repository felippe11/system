-- Adicionar a coluna taxa_diferenciada à tabela configuracao_cliente
ALTER TABLE configuracao_cliente ADD COLUMN IF NOT EXISTS taxa_diferenciada NUMERIC(5,2);
