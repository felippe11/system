from datetime import datetime
from extensions import db
from sqlalchemy.dialects.postgresql import JSON


class VotingEvent(db.Model):
    """Configuração de um evento de votação para trabalhos."""
    
    __tablename__ = "voting_event"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    
    # Configurações básicas
    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="configuracao")  # configuracao, ativo, finalizado
    
    # Período de votação
    data_inicio_votacao = db.Column(db.DateTime, nullable=True)
    data_fim_votacao = db.Column(db.DateTime, nullable=True)
    
    # Configurações de exibição
    exibir_resultados_tempo_real = db.Column(db.Boolean, default=True)
    modo_revelacao = db.Column(db.String(20), default="imediato")  # imediato, progressivo
    permitir_votacao_multipla = db.Column(db.Boolean, default=False)
    
    # Configurações de segurança
    exigir_login_revisor = db.Column(db.Boolean, default=True)
    permitir_voto_anonimo = db.Column(db.Boolean, default=False)
    
    # Metadados
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    cliente = db.relationship("Cliente", backref="voting_events")
    evento = db.relationship("Evento", backref="voting_events")
    categorias = db.relationship("VotingCategory", backref="voting_event", cascade="all, delete-orphan")
    trabalhos = db.relationship("VotingWork", backref="voting_event", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<VotingEvent {self.nome} - {self.evento_id}>"
    
    @property
    def is_active(self):
        """Verifica se o evento de votação está ativo."""
        now = datetime.utcnow()
        if self.status != "ativo":
            return False
        if self.data_inicio_votacao and now < self.data_inicio_votacao:
            return False
        if self.data_fim_votacao and now > self.data_fim_votacao:
            return False
        return True


class VotingCategory(db.Model):
    """Categoria de votação (ex: melhor apresentação, inovação, impacto social)."""
    
    __tablename__ = "voting_category"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    voting_event_id = db.Column(db.Integer, db.ForeignKey("voting_event.id"), nullable=False)
    
    # Configurações da categoria
    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    ordem = db.Column(db.Integer, default=0)
    ativa = db.Column(db.Boolean, default=True)
    
    # Configurações de pontuação
    pontuacao_minima = db.Column(db.Float, default=0.0)
    pontuacao_maxima = db.Column(db.Float, default=10.0)
    tipo_pontuacao = db.Column(db.String(20), default="numerica")  # numerica, escala, escolha_unica
    
    # Metadados
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    perguntas = db.relationship("VotingQuestion", backref="category", cascade="all, delete-orphan")
    votos = db.relationship("VotingVote", backref="category", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<VotingCategory {self.nome} - {self.voting_event_id}>"


class VotingQuestion(db.Model):
    """Pergunta/quesito de avaliação dentro de uma categoria."""
    
    __tablename__ = "voting_question"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("voting_category.id"), nullable=False)
    
    # Configurações da pergunta
    texto_pergunta = db.Column(db.Text, nullable=False)
    observacao_explicativa = db.Column(db.Text, nullable=True)
    ordem = db.Column(db.Integer, default=0)
    obrigatoria = db.Column(db.Boolean, default=True)
    
    # Configurações de resposta
    tipo_resposta = db.Column(db.String(20), default="numerica")  # numerica, texto, escolha_unica, multipla_escolha
    opcoes_resposta = db.Column(JSON, nullable=True)  # Para escolha única/múltipla
    valor_minimo = db.Column(db.Float, nullable=True)
    valor_maximo = db.Column(db.Float, nullable=True)
    casas_decimais = db.Column(db.Integer, default=1)
    
    # Metadados
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    respostas = db.relationship("VotingResponse", backref="question", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<VotingQuestion {self.id} - {self.texto_pergunta[:50]}...>"


class VotingWork(db.Model):
    """Trabalho participante de um evento de votação."""
    
    __tablename__ = "voting_work"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    voting_event_id = db.Column(db.Integer, db.ForeignKey("voting_event.id"), nullable=False)
    submission_id = db.Column(db.Integer, db.ForeignKey("submission.id"), nullable=True)
    
    # Dados do trabalho
    titulo = db.Column(db.String(255), nullable=False)
    resumo = db.Column(db.Text, nullable=True)
    autores = db.Column(db.Text, nullable=True)  # Lista de autores
    categoria_original = db.Column(db.String(255), nullable=True)  # Categoria do trabalho original
    
    # Configurações de participação
    ativo = db.Column(db.Boolean, default=True)
    ordem_exibicao = db.Column(db.Integer, default=0)
    
    # Metadados
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    submission = db.relationship("Submission", backref="voting_works")
    votos = db.relationship("VotingVote", backref="work", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<VotingWork {self.titulo} - {self.voting_event_id}>"


class VotingAssignment(db.Model):
    """Atribuição de trabalhos para revisores votarem."""
    
    __tablename__ = "voting_assignment"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    voting_event_id = db.Column(db.Integer, db.ForeignKey("voting_event.id"), nullable=False)
    revisor_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    work_id = db.Column(db.Integer, db.ForeignKey("voting_work.id"), nullable=False)
    
    # Configurações da atribuição
    prazo_votacao = db.Column(db.DateTime, nullable=True)
    concluida = db.Column(db.Boolean, default=False)
    data_conclusao = db.Column(db.DateTime, nullable=True)
    
    # Metadados
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    voting_event = db.relationship("VotingEvent", backref="assignments")
    revisor = db.relationship("Usuario", backref="voting_assignments")
    work = db.relationship("VotingWork", backref="assignments")
    
    def __repr__(self):
        return f"<VotingAssignment {self.revisor_id} - {self.work_id}>"


class VotingVote(db.Model):
    """Voto de um revisor em uma categoria específica."""
    
    __tablename__ = "voting_vote"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    voting_event_id = db.Column(db.Integer, db.ForeignKey("voting_event.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("voting_category.id"), nullable=False)
    work_id = db.Column(db.Integer, db.ForeignKey("voting_work.id"), nullable=False)
    revisor_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    
    # Dados do voto
    pontuacao_final = db.Column(db.Float, nullable=True)  # Pontuação final calculada
    observacoes = db.Column(db.Text, nullable=True)
    
    # Metadados
    data_voto = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)  # Para auditoria
    user_agent = db.Column(db.Text, nullable=True)
    
    # Relacionamentos
    voting_event = db.relationship("VotingEvent", backref="votes")
    revisor = db.relationship("Usuario", backref="voting_votes")
    respostas = db.relationship("VotingResponse", backref="vote", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<VotingVote {self.revisor_id} - {self.work_id} - {self.category_id}>"


class VotingResponse(db.Model):
    """Resposta individual a uma pergunta específica."""
    
    __tablename__ = "voting_response"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    vote_id = db.Column(db.Integer, db.ForeignKey("voting_vote.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("voting_question.id"), nullable=False)
    
    # Dados da resposta
    valor_numerico = db.Column(db.Float, nullable=True)
    texto_resposta = db.Column(db.Text, nullable=True)
    opcoes_selecionadas = db.Column(JSON, nullable=True)  # Para múltipla escolha
    
    # Metadados
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<VotingResponse {self.id} - Question {self.question_id}>"


class VotingResult(db.Model):
    """Resultados calculados de uma votação."""
    
    __tablename__ = "voting_result"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    voting_event_id = db.Column(db.Integer, db.ForeignKey("voting_event.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("voting_category.id"), nullable=False)
    work_id = db.Column(db.Integer, db.ForeignKey("voting_work.id"), nullable=False)
    
    # Resultados calculados
    pontuacao_total = db.Column(db.Float, nullable=False)
    pontuacao_media = db.Column(db.Float, nullable=False)
    numero_votos = db.Column(db.Integer, nullable=False)
    posicao_ranking = db.Column(db.Integer, nullable=True)
    
    # Metadados
    calculado_em = db.Column(db.DateTime, default=datetime.utcnow)
    versao_calculo = db.Column(db.String(20), default="1.0")
    
    # Relacionamentos
    voting_event = db.relationship("VotingEvent", backref="results")
    category = db.relationship("VotingCategory", backref="results")
    work = db.relationship("VotingWork", backref="results")
    
    def __repr__(self):
        return f"<VotingResult {self.work_id} - {self.category_id} - Posição {self.posicao_ranking}>"


class VotingAuditLog(db.Model):
    """Log de auditoria para ações na votação."""
    
    __tablename__ = "voting_audit_log"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    voting_event_id = db.Column(db.Integer, db.ForeignKey("voting_event.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    
    # Dados da ação
    acao = db.Column(db.String(100), nullable=False)  # votar, configurar, finalizar, etc.
    detalhes = db.Column(JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    
    # Metadados
    data_acao = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    voting_event = db.relationship("VotingEvent", backref="audit_logs")
    usuario = db.relationship("Usuario", backref="voting_audit_logs")
    
    def __repr__(self):
        return f"<VotingAuditLog {self.acao} - {self.data_acao}>"

