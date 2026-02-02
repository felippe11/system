# Setup das tabelas de feedback

Execute este SQL no banco `iafap_database`.

```sql
-- criar tabelas
CREATE TABLE IF NOT EXISTS public.feedback_templates (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL,
    nome VARCHAR(120) NOT NULL,
    descricao TEXT,
    is_default BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT fk_feedback_templates_cliente_id_cliente
        FOREIGN KEY (cliente_id) REFERENCES public.cliente(id)
);

CREATE TABLE IF NOT EXISTS public.feedback_template_oficina (
    id SERIAL PRIMARY KEY,
    template_id INTEGER NOT NULL,
    oficina_id INTEGER NOT NULL,
    created_at TIMESTAMP,
    CONSTRAINT fk_feedback_template_oficina_template_id_feedback_templates
        FOREIGN KEY (template_id) REFERENCES public.feedback_templates(id),
    CONSTRAINT fk_feedback_template_oficina_oficina_id_oficina
        FOREIGN KEY (oficina_id) REFERENCES public.oficina(id)
);

-- coluna template_id
ALTER TABLE public.perguntas_feedback
    ADD COLUMN IF NOT EXISTS template_id INTEGER;

-- FK só se a tabela existir
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'feedback_templates'
    ) THEN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'fk_perguntas_feedback_template_id_feedback_templates'
        ) THEN
            ALTER TABLE public.perguntas_feedback
                ADD CONSTRAINT fk_perguntas_feedback_template_id_feedback_templates
                FOREIGN KEY (template_id) REFERENCES public.feedback_templates(id);
        END IF;
    END IF;
END $$;

-- usuario_id nullable
ALTER TABLE public.respostas_feedback
    ALTER COLUMN usuario_id DROP NOT NULL;
```
