-- Comando SQL para restaurar vagas de agendamentos cancelados
-- Este comando identifica agendamentos cancelados e restaura suas vagas nos horários correspondentes

-- Primeiro, vamos verificar a situação atual
SELECT 
    av.id as agendamento_id,
    av.status,
    av.quantidade_alunos,
    hv.id as horario_id,
    hv.vagas_disponiveis,
    hv.capacidade_total,
    av.data_cancelamento
FROM agendamento_visita av
JOIN horario_visitacao hv ON av.horario_id = hv.id
WHERE av.status IN ('cancelado', 'recusado')
ORDER BY av.data_cancelamento DESC;

-- Comando para restaurar as vagas dos agendamentos cancelados
-- ATENÇÃO: Execute este comando apenas após verificar os dados acima

UPDATE horario_visitacao 
SET vagas_disponiveis = LEAST(
    vagas_disponiveis + (
        SELECT COALESCE(SUM(av.quantidade_alunos), 0)
        FROM agendamento_visita av 
        WHERE av.horario_id = horario_visitacao.id 
        AND av.status IN ('cancelado', 'recusado')
    ),
    capacidade_total
)
WHERE id IN (
    SELECT DISTINCT av.horario_id
    FROM agendamento_visita av
    WHERE av.status IN ('cancelado', 'recusado')
);

-- Verificação após a execução
SELECT 
    av.id as agendamento_id,
    av.status,
    av.quantidade_alunos,
    hv.id as horario_id,
    hv.vagas_disponiveis,
    hv.capacidade_total,
    av.data_cancelamento
FROM agendamento_visita av
JOIN horario_visitacao hv ON av.horario_id = hv.id
WHERE av.status IN ('cancelado', 'recusado')
ORDER BY av.data_cancelamento DESC;

-- Comando alternativo mais seguro (executa um horário por vez)
-- Use este se preferir uma abordagem mais cautelosa:
/*
UPDATE horario_visitacao hv
SET vagas_disponiveis = (
    SELECT LEAST(
        hv.vagas_disponiveis + COALESCE(SUM(av.quantidade_alunos), 0),
        hv.capacidade_total
    )
    FROM agendamento_visita av
    WHERE av.horario_id = hv.id
    AND av.status IN ('cancelado', 'recusado')
    GROUP BY av.horario_id
)
WHERE EXISTS (
    SELECT 1
    FROM agendamento_visita av
    WHERE av.horario_id = hv.id
    AND av.status IN ('cancelado', 'recusado')
);
*/