-- Script para criar formulário de trabalhos no sistema
-- Este script deve ser executado no banco de dados PostgreSQL

-- Inserir o formulário de trabalhos
INSERT INTO formularios (nome, descricao, permitir_multiplas_respostas, is_submission_form)
VALUES (
    'Formulário de Trabalhos',
    'Formulário para cadastro de trabalhos acadêmicos pelos clientes',
    true,
    false
);

-- Obter o ID do formulário recém-criado
-- (Este valor será usado nas próximas inserções)
SELECT id FROM formularios WHERE nome = 'Formulário de Trabalhos' ORDER BY id DESC LIMIT 1;

-- Inserir os campos do formulário
-- Campo: Título
INSERT INTO campos_formulario (formulario_id, nome, tipo, obrigatorio, descricao)
SELECT 
    f.id,
    'Título',
    'text',
    true,
    'Título do trabalho acadêmico'
FROM formularios f 
WHERE f.nome = 'Formulário de Trabalhos' 
ORDER BY f.id DESC LIMIT 1;

-- Campo: Categoria (select)
INSERT INTO campos_formulario (formulario_id, nome, tipo, opcoes, obrigatorio, descricao)
SELECT 
    f.id,
    'Categoria',
    'select',
    'Prática Educacional,Pesquisa Inovadora,Produto Inovador',
    true,
    'Categoria do trabalho acadêmico'
FROM formularios f 
WHERE f.nome = 'Formulário de Trabalhos' 
ORDER BY f.id DESC LIMIT 1;

-- Campo: Rede de Ensino
INSERT INTO campos_formulario (formulario_id, nome, tipo, obrigatorio, descricao)
SELECT 
    f.id,
    'Rede de Ensino',
    'text',
    true,
    'Rede de ensino onde o trabalho foi desenvolvido'
FROM formularios f 
WHERE f.nome = 'Formulário de Trabalhos' 
ORDER BY f.id DESC LIMIT 1;

-- Campo: Etapa de Ensino
INSERT INTO campos_formulario (formulario_id, nome, tipo, obrigatorio, descricao)
SELECT 
    f.id,
    'Etapa de Ensino',
    'text',
    true,
    'Etapa de ensino relacionada ao trabalho'
FROM formularios f 
WHERE f.nome = 'Formulário de Trabalhos' 
ORDER BY f.id DESC LIMIT 1;

-- Campo: URL do PDF
INSERT INTO campos_formulario (formulario_id, nome, tipo, obrigatorio, descricao)
SELECT 
    f.id,
    'URL do PDF',
    'url',
    true,
    'URL do arquivo PDF do trabalho'
FROM formularios f 
WHERE f.nome = 'Formulário de Trabalhos' 
ORDER BY f.id DESC LIMIT 1;

-- Verificar se os campos foram criados corretamente
SELECT 
    f.nome as formulario,
    cf.nome as campo,
    cf.tipo,
    cf.obrigatorio,
    cf.opcoes,
    cf.descricao
FROM formularios f
JOIN campos_formulario cf ON f.id = cf.formulario_id
WHERE f.nome = 'Formulário de Trabalhos'
ORDER BY cf.id;

-- Criar índices para otimização
CREATE INDEX IF NOT EXISTS idx_respostas_formulario_trabalhos 
ON respostas_formulario(formulario_id) 
WHERE formulario_id = (SELECT id FROM formularios WHERE nome = 'Formulário de Trabalhos' LIMIT 1);

CREATE INDEX IF NOT EXISTS idx_respostas_formulario_data_trabalhos 
ON respostas_formulario(data_submissao DESC) 
WHERE formulario_id = (SELECT id FROM formularios WHERE nome = 'Formulário de Trabalhos' LIMIT 1);

CREATE INDEX IF NOT EXISTS idx_respostas_campo_trabalhos 
ON respostas_campo(campo_id, valor) 
WHERE campo_id IN (
    SELECT cf.id 
    FROM campos_formulario cf 
    JOIN formularios f ON cf.formulario_id = f.id 
    WHERE f.nome = 'Formulário de Trabalhos'
);