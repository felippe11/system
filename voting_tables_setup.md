# Setup das tabelas de votação (voting_*)

Execute este SQL no banco `iafap_database`.

```sql
CREATE TABLE IF NOT EXISTS public.voting_event (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL,
    evento_id INTEGER NOT NULL,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'configuracao',
    data_inicio_votacao TIMESTAMP,
    data_fim_votacao TIMESTAMP,
    exibir_resultados_tempo_real BOOLEAN NOT NULL DEFAULT TRUE,
    modo_revelacao VARCHAR(20) NOT NULL DEFAULT 'imediato',
    permitir_votacao_multipla BOOLEAN NOT NULL DEFAULT FALSE,
    exigir_login_revisor BOOLEAN NOT NULL DEFAULT TRUE,
    permitir_voto_anonimo BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT fk_voting_event_cliente_id_cliente
        FOREIGN KEY (cliente_id) REFERENCES public.cliente(id),
    CONSTRAINT fk_voting_event_evento_id_evento
        FOREIGN KEY (evento_id) REFERENCES public.evento(id)
);

CREATE TABLE IF NOT EXISTS public.voting_category (
    id SERIAL PRIMARY KEY,
    voting_event_id INTEGER NOT NULL,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    ordem INTEGER NOT NULL DEFAULT 0,
    ativa BOOLEAN NOT NULL DEFAULT TRUE,
    pontuacao_minima DOUBLE PRECISION NOT NULL DEFAULT 0,
    pontuacao_maxima DOUBLE PRECISION NOT NULL DEFAULT 10,
    tipo_pontuacao VARCHAR(20) NOT NULL DEFAULT 'numerica',
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT fk_voting_category_voting_event_id_voting_event
        FOREIGN KEY (voting_event_id) REFERENCES public.voting_event(id)
);

CREATE TABLE IF NOT EXISTS public.voting_question (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL,
    texto_pergunta TEXT NOT NULL,
    observacao_explicativa TEXT,
    ordem INTEGER NOT NULL DEFAULT 0,
    obrigatoria BOOLEAN NOT NULL DEFAULT TRUE,
    tipo_resposta VARCHAR(20) NOT NULL DEFAULT 'numerica',
    opcoes_resposta JSON,
    valor_minimo DOUBLE PRECISION,
    valor_maximo DOUBLE PRECISION,
    casas_decimais INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT fk_voting_question_category_id_voting_category
        FOREIGN KEY (category_id) REFERENCES public.voting_category(id)
);

CREATE TABLE IF NOT EXISTS public.voting_work (
    id SERIAL PRIMARY KEY,
    voting_event_id INTEGER NOT NULL,
    submission_id INTEGER,
    titulo VARCHAR(255) NOT NULL,
    resumo TEXT,
    autores TEXT,
    categoria_original VARCHAR(255),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    ordem_exibicao INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT fk_voting_work_voting_event_id_voting_event
        FOREIGN KEY (voting_event_id) REFERENCES public.voting_event(id),
    CONSTRAINT fk_voting_work_submission_id_submission
        FOREIGN KEY (submission_id) REFERENCES public.submission(id)
);

CREATE TABLE IF NOT EXISTS public.voting_assignment (
    id SERIAL PRIMARY KEY,
    voting_event_id INTEGER NOT NULL,
    revisor_id INTEGER NOT NULL,
    work_id INTEGER NOT NULL,
    prazo_votacao TIMESTAMP,
    concluida BOOLEAN NOT NULL DEFAULT FALSE,
    data_conclusao TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT fk_voting_assignment_voting_event_id_voting_event
        FOREIGN KEY (voting_event_id) REFERENCES public.voting_event(id),
    CONSTRAINT fk_voting_assignment_revisor_id_usuario
        FOREIGN KEY (revisor_id) REFERENCES public.usuario(id),
    CONSTRAINT fk_voting_assignment_work_id_voting_work
        FOREIGN KEY (work_id) REFERENCES public.voting_work(id)
);

CREATE TABLE IF NOT EXISTS public.voting_vote (
    id SERIAL PRIMARY KEY,
    voting_event_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    work_id INTEGER NOT NULL,
    revisor_id INTEGER NOT NULL,
    pontuacao_final DOUBLE PRECISION,
    observacoes TEXT,
    data_voto TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT,
    CONSTRAINT fk_voting_vote_voting_event_id_voting_event
        FOREIGN KEY (voting_event_id) REFERENCES public.voting_event(id),
    CONSTRAINT fk_voting_vote_category_id_voting_category
        FOREIGN KEY (category_id) REFERENCES public.voting_category(id),
    CONSTRAINT fk_voting_vote_work_id_voting_work
        FOREIGN KEY (work_id) REFERENCES public.voting_work(id),
    CONSTRAINT fk_voting_vote_revisor_id_usuario
        FOREIGN KEY (revisor_id) REFERENCES public.usuario(id)
);

CREATE TABLE IF NOT EXISTS public.voting_response (
    id SERIAL PRIMARY KEY,
    vote_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    valor_numerico DOUBLE PRECISION,
    texto_resposta TEXT,
    opcoes_selecionadas JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT fk_voting_response_vote_id_voting_vote
        FOREIGN KEY (vote_id) REFERENCES public.voting_vote(id),
    CONSTRAINT fk_voting_response_question_id_voting_question
        FOREIGN KEY (question_id) REFERENCES public.voting_question(id)
);

CREATE TABLE IF NOT EXISTS public.voting_result (
    id SERIAL PRIMARY KEY,
    voting_event_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    work_id INTEGER NOT NULL,
    pontuacao_total DOUBLE PRECISION NOT NULL,
    pontuacao_media DOUBLE PRECISION NOT NULL,
    numero_votos INTEGER NOT NULL,
    posicao_ranking INTEGER,
    calculado_em TIMESTAMP,
    versao_calculo VARCHAR(20) NOT NULL DEFAULT '1.0',
    CONSTRAINT fk_voting_result_voting_event_id_voting_event
        FOREIGN KEY (voting_event_id) REFERENCES public.voting_event(id),
    CONSTRAINT fk_voting_result_category_id_voting_category
        FOREIGN KEY (category_id) REFERENCES public.voting_category(id),
    CONSTRAINT fk_voting_result_work_id_voting_work
        FOREIGN KEY (work_id) REFERENCES public.voting_work(id)
);

CREATE TABLE IF NOT EXISTS public.voting_audit_log (
    id SERIAL PRIMARY KEY,
    voting_event_id INTEGER NOT NULL,
    usuario_id INTEGER,
    acao VARCHAR(100) NOT NULL,
    detalhes JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    data_acao TIMESTAMP,
    CONSTRAINT fk_voting_audit_log_voting_event_id_voting_event
        FOREIGN KEY (voting_event_id) REFERENCES public.voting_event(id),
    CONSTRAINT fk_voting_audit_log_usuario_id_usuario
        FOREIGN KEY (usuario_id) REFERENCES public.usuario(id)
);
```
