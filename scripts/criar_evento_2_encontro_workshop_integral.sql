DO $$
DECLARE
    v_cliente_id INTEGER;
    v_evento_id INTEGER;

    v_tipo_prof_id INTEGER;
    v_tipo_tecnico_id INTEGER;

    v_sala1_id INTEGER;
    v_sala2_id INTEGER;
    v_sala3_id INTEGER;
    v_sala4_id INTEGER;

    v_inscritos_sala1 INTEGER;
    v_inscritos_sala2 INTEGER;
    v_inscritos_sala3 INTEGER;
    v_inscritos_sala4 INTEGER;
BEGIN
    SELECT id
      INTO v_cliente_id
      FROM cliente
     WHERE lower(email) = lower('iafap@appfiber.com')
     LIMIT 1;

    IF v_cliente_id IS NULL THEN
        RAISE EXCEPTION 'Cliente nao encontrado para o email iafap@appfiber.com';
    END IF;

    SELECT id
      INTO v_evento_id
      FROM evento
     WHERE cliente_id = v_cliente_id
       AND nome = '2o Encontro do Workshop de Educacao Integral | Senador Rui Palmeira'
     LIMIT 1;

    IF v_evento_id IS NULL THEN
        INSERT INTO evento (
            cliente_id,
            nome,
            descricao,
            banner_url,
            programacao,
            localizacao,
            link_mapa,
            inscricao_gratuita,
            data_inicio,
            data_fim,
            hora_inicio,
            hora_fim,
            status,
            capacidade_padrao,
            requer_aprovacao,
            publico,
            habilitar_lotes,
            submissao_aberta
        )
        VALUES (
            v_cliente_id,
            '2o Encontro do Workshop de Educacao Integral | Senador Rui Palmeira',
            'Segundo encontro do Workshop de Educacao Integral, com 4 turmas simultaneas e limite de 25 participantes por sala.',
            NULL,
            'Data: 25 de abril | Horario: 08h as 17h | Local: mesma escola do encontro anterior.',
            'Mesma escola do encontro anterior',
            NULL,
            TRUE,
            TIMESTAMP '2026-04-25 08:00:00',
            TIMESTAMP '2026-04-25 17:00:00',
            TIME '08:00:00',
            TIME '17:00:00',
            'ativo',
            25,
            FALSE,
            TRUE,
            FALSE,
            FALSE
        )
        RETURNING id INTO v_evento_id;
    ELSE
        UPDATE evento
           SET descricao = 'Segundo encontro do Workshop de Educacao Integral, com 4 turmas simultaneas e limite de 25 participantes por sala.',
               programacao = 'Data: 25 de abril | Horario: 08h as 17h | Local: mesma escola do encontro anterior.',
               localizacao = 'Mesma escola do encontro anterior',
               link_mapa = NULL,
               banner_url = NULL,
               inscricao_gratuita = TRUE,
               data_inicio = TIMESTAMP '2026-04-25 08:00:00',
               data_fim = TIMESTAMP '2026-04-25 17:00:00',
               hora_inicio = TIME '08:00:00',
               hora_fim = TIME '17:00:00',
               status = 'ativo',
               capacidade_padrao = 25,
               requer_aprovacao = FALSE,
               publico = TRUE,
               habilitar_lotes = FALSE,
               submissao_aberta = FALSE
         WHERE id = v_evento_id;
    END IF;

    SELECT id
      INTO v_tipo_prof_id
      FROM evento_inscricao_tipo
     WHERE evento_id = v_evento_id
       AND nome = 'Profissionais da Educacao Integral'
     LIMIT 1;

    IF v_tipo_prof_id IS NULL THEN
        INSERT INTO evento_inscricao_tipo (evento_id, nome, preco, submission_only)
        VALUES (v_evento_id, 'Profissionais da Educacao Integral', 0, FALSE)
        RETURNING id INTO v_tipo_prof_id;
    ELSE
        UPDATE evento_inscricao_tipo
           SET preco = 0,
               submission_only = FALSE
         WHERE id = v_tipo_prof_id;
    END IF;

    SELECT id
      INTO v_tipo_tecnico_id
      FROM evento_inscricao_tipo
     WHERE evento_id = v_evento_id
       AND nome = 'Tecnicos, Diretores e Coordenadores'
     LIMIT 1;

    IF v_tipo_tecnico_id IS NULL THEN
        INSERT INTO evento_inscricao_tipo (evento_id, nome, preco, submission_only)
        VALUES (v_evento_id, 'Tecnicos, Diretores e Coordenadores', 0, FALSE)
        RETURNING id INTO v_tipo_tecnico_id;
    ELSE
        UPDATE evento_inscricao_tipo
           SET preco = 0,
               submission_only = FALSE
         WHERE id = v_tipo_tecnico_id;
    END IF;

    SELECT id INTO v_sala1_id
      FROM oficina
     WHERE evento_id = v_evento_id
       AND titulo = 'Turma 1 - Profissionais'
     LIMIT 1;

    IF v_sala1_id IS NULL THEN
        INSERT INTO oficina (
            titulo, descricao, ministrante_id, vagas, carga_horaria, estado, cidade,
            cliente_id, evento_id, tipo_inscricao, tipo_oficina, tipo_oficina_outro,
            inscricao_gratuita, tipos_inscricao_permitidos
        )
        VALUES (
            'Turma 1 - Profissionais',
            'Turma voltada para profissionais da Educacao Integral.',
            NULL, 25, '8', 'AL', 'Senador Rui Palmeira',
            v_cliente_id, v_evento_id, 'com_inscricao_com_limite', 'Workshop', NULL,
            TRUE, v_tipo_prof_id::text
        )
        RETURNING id INTO v_sala1_id;
    ELSE
        SELECT COUNT(*) INTO v_inscritos_sala1 FROM inscricao WHERE oficina_id = v_sala1_id;
        UPDATE oficina
           SET descricao = 'Turma voltada para profissionais da Educacao Integral.',
               carga_horaria = '8',
               estado = 'AL',
               cidade = 'Senador Rui Palmeira',
               cliente_id = v_cliente_id,
               evento_id = v_evento_id,
               tipo_inscricao = 'com_inscricao_com_limite',
               tipo_oficina = 'Workshop',
               tipo_oficina_outro = NULL,
               inscricao_gratuita = TRUE,
               tipos_inscricao_permitidos = v_tipo_prof_id::text,
               vagas = CASE WHEN v_inscritos_sala1 = 0 THEN 25 ELSE vagas END
         WHERE id = v_sala1_id;
    END IF;

    SELECT id INTO v_sala2_id
      FROM oficina
     WHERE evento_id = v_evento_id
       AND titulo = 'Turma 2 - Profissionais'
     LIMIT 1;

    IF v_sala2_id IS NULL THEN
        INSERT INTO oficina (
            titulo, descricao, ministrante_id, vagas, carga_horaria, estado, cidade,
            cliente_id, evento_id, tipo_inscricao, tipo_oficina, tipo_oficina_outro,
            inscricao_gratuita, tipos_inscricao_permitidos
        )
        VALUES (
            'Turma 2 - Profissionais',
            'Turma voltada para profissionais da Educacao Integral.',
            NULL, 25, '8', 'AL', 'Senador Rui Palmeira',
            v_cliente_id, v_evento_id, 'com_inscricao_com_limite', 'Workshop', NULL,
            TRUE, v_tipo_prof_id::text
        )
        RETURNING id INTO v_sala2_id;
    ELSE
        SELECT COUNT(*) INTO v_inscritos_sala2 FROM inscricao WHERE oficina_id = v_sala2_id;
        UPDATE oficina
           SET descricao = 'Turma voltada para profissionais da Educacao Integral.',
               carga_horaria = '8',
               estado = 'AL',
               cidade = 'Senador Rui Palmeira',
               cliente_id = v_cliente_id,
               evento_id = v_evento_id,
               tipo_inscricao = 'com_inscricao_com_limite',
               tipo_oficina = 'Workshop',
               tipo_oficina_outro = NULL,
               inscricao_gratuita = TRUE,
               tipos_inscricao_permitidos = v_tipo_prof_id::text,
               vagas = CASE WHEN v_inscritos_sala2 = 0 THEN 25 ELSE vagas END
         WHERE id = v_sala2_id;
    END IF;

    SELECT id INTO v_sala3_id
      FROM oficina
     WHERE evento_id = v_evento_id
       AND titulo = 'Turma 3 - Profissionais'
     LIMIT 1;

    IF v_sala3_id IS NULL THEN
        INSERT INTO oficina (
            titulo, descricao, ministrante_id, vagas, carga_horaria, estado, cidade,
            cliente_id, evento_id, tipo_inscricao, tipo_oficina, tipo_oficina_outro,
            inscricao_gratuita, tipos_inscricao_permitidos
        )
        VALUES (
            'Turma 3 - Profissionais',
            'Turma voltada para profissionais da Educacao Integral.',
            NULL, 25, '8', 'AL', 'Senador Rui Palmeira',
            v_cliente_id, v_evento_id, 'com_inscricao_com_limite', 'Workshop', NULL,
            TRUE, v_tipo_prof_id::text
        )
        RETURNING id INTO v_sala3_id;
    ELSE
        SELECT COUNT(*) INTO v_inscritos_sala3 FROM inscricao WHERE oficina_id = v_sala3_id;
        UPDATE oficina
           SET descricao = 'Turma voltada para profissionais da Educacao Integral.',
               carga_horaria = '8',
               estado = 'AL',
               cidade = 'Senador Rui Palmeira',
               cliente_id = v_cliente_id,
               evento_id = v_evento_id,
               tipo_inscricao = 'com_inscricao_com_limite',
               tipo_oficina = 'Workshop',
               tipo_oficina_outro = NULL,
               inscricao_gratuita = TRUE,
               tipos_inscricao_permitidos = v_tipo_prof_id::text,
               vagas = CASE WHEN v_inscritos_sala3 = 0 THEN 25 ELSE vagas END
         WHERE id = v_sala3_id;
    END IF;

    SELECT id INTO v_sala4_id
      FROM oficina
     WHERE evento_id = v_evento_id
       AND titulo = 'Turma 4 - Tecnicos, Diretores e Coordenadores'
     LIMIT 1;

    IF v_sala4_id IS NULL THEN
        INSERT INTO oficina (
            titulo, descricao, ministrante_id, vagas, carga_horaria, estado, cidade,
            cliente_id, evento_id, tipo_inscricao, tipo_oficina, tipo_oficina_outro,
            inscricao_gratuita, tipos_inscricao_permitidos
        )
        VALUES (
            'Turma 4 - Tecnicos, Diretores e Coordenadores',
            'Turma especifica para tecnicos, diretores e coordenadores.',
            NULL, 25, '8', 'AL', 'Senador Rui Palmeira',
            v_cliente_id, v_evento_id, 'com_inscricao_com_limite', 'Workshop', NULL,
            TRUE, v_tipo_tecnico_id::text
        )
        RETURNING id INTO v_sala4_id;
    ELSE
        SELECT COUNT(*) INTO v_inscritos_sala4 FROM inscricao WHERE oficina_id = v_sala4_id;
        UPDATE oficina
           SET descricao = 'Turma especifica para tecnicos, diretores e coordenadores.',
               carga_horaria = '8',
               estado = 'AL',
               cidade = 'Senador Rui Palmeira',
               cliente_id = v_cliente_id,
               evento_id = v_evento_id,
               tipo_inscricao = 'com_inscricao_com_limite',
               tipo_oficina = 'Workshop',
               tipo_oficina_outro = NULL,
               inscricao_gratuita = TRUE,
               tipos_inscricao_permitidos = v_tipo_tecnico_id::text,
               vagas = CASE WHEN v_inscritos_sala4 = 0 THEN 25 ELSE vagas END
         WHERE id = v_sala4_id;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM oficinadia WHERE oficina_id = v_sala1_id AND data = DATE '2026-04-25'
    ) THEN
        INSERT INTO oficinadia (oficina_id, data, horario_inicio, horario_fim, ordem_exibicao)
        VALUES (v_sala1_id, DATE '2026-04-25', '08:00', '17:00', 1);
    ELSE
        UPDATE oficinadia
           SET horario_inicio = '08:00',
               horario_fim = '17:00',
               ordem_exibicao = 1
         WHERE oficina_id = v_sala1_id
           AND data = DATE '2026-04-25';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM oficinadia WHERE oficina_id = v_sala2_id AND data = DATE '2026-04-25'
    ) THEN
        INSERT INTO oficinadia (oficina_id, data, horario_inicio, horario_fim, ordem_exibicao)
        VALUES (v_sala2_id, DATE '2026-04-25', '08:00', '17:00', 1);
    ELSE
        UPDATE oficinadia
           SET horario_inicio = '08:00',
               horario_fim = '17:00',
               ordem_exibicao = 1
         WHERE oficina_id = v_sala2_id
           AND data = DATE '2026-04-25';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM oficinadia WHERE oficina_id = v_sala3_id AND data = DATE '2026-04-25'
    ) THEN
        INSERT INTO oficinadia (oficina_id, data, horario_inicio, horario_fim, ordem_exibicao)
        VALUES (v_sala3_id, DATE '2026-04-25', '08:00', '17:00', 1);
    ELSE
        UPDATE oficinadia
           SET horario_inicio = '08:00',
               horario_fim = '17:00',
               ordem_exibicao = 1
         WHERE oficina_id = v_sala3_id
           AND data = DATE '2026-04-25';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM oficinadia WHERE oficina_id = v_sala4_id AND data = DATE '2026-04-25'
    ) THEN
        INSERT INTO oficinadia (oficina_id, data, horario_inicio, horario_fim, ordem_exibicao)
        VALUES (v_sala4_id, DATE '2026-04-25', '08:00', '17:00', 1);
    ELSE
        UPDATE oficinadia
           SET horario_inicio = '08:00',
               horario_fim = '17:00',
               ordem_exibicao = 1
         WHERE oficina_id = v_sala4_id
           AND data = DATE '2026-04-25';
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM regra_inscricao_evento
         WHERE evento_id = v_evento_id
           AND tipo_inscricao_id = v_tipo_prof_id
    ) THEN
        INSERT INTO regra_inscricao_evento (
            evento_id,
            tipo_inscricao_id,
            limite_oficinas,
            oficinas_permitidas
        )
        VALUES (
            v_evento_id,
            v_tipo_prof_id,
            1,
            concat_ws(',', v_sala1_id, v_sala2_id, v_sala3_id)
        );
    ELSE
        UPDATE regra_inscricao_evento
           SET limite_oficinas = 1,
               oficinas_permitidas = concat_ws(',', v_sala1_id, v_sala2_id, v_sala3_id)
         WHERE evento_id = v_evento_id
           AND tipo_inscricao_id = v_tipo_prof_id;
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM regra_inscricao_evento
         WHERE evento_id = v_evento_id
           AND tipo_inscricao_id = v_tipo_tecnico_id
    ) THEN
        INSERT INTO regra_inscricao_evento (
            evento_id,
            tipo_inscricao_id,
            limite_oficinas,
            oficinas_permitidas
        )
        VALUES (
            v_evento_id,
            v_tipo_tecnico_id,
            1,
            v_sala4_id::text
        );
    ELSE
        UPDATE regra_inscricao_evento
           SET limite_oficinas = 1,
               oficinas_permitidas = v_sala4_id::text
         WHERE evento_id = v_evento_id
           AND tipo_inscricao_id = v_tipo_tecnico_id;
    END IF;

    RAISE NOTICE 'Evento criado/atualizado com sucesso. Evento ID: %', v_evento_id;
END $$;

