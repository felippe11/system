# SQL - Adicionar senha de acesso aos resultados do feedback aberto

Observacao: esta alteracao adiciona uma **coluna** na tabela existente `configuracao` (nao cria uma nova tabela).

## PostgreSQL
```sql
ALTER TABLE configuracao
ADD COLUMN IF NOT EXISTS senha_feedback_aberto_hash VARCHAR(255);
```

## MySQL
```sql
ALTER TABLE configuracao
ADD COLUMN senha_feedback_aberto_hash VARCHAR(255);
```
