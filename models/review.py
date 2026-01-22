import uuid
from datetime import datetime, date

from werkzeug.security import check_password_hash

from extensions import db


# Association table linking RevisorProcess and Evento
revisor_process_evento_association = db.Table(
    "revisor_process_evento_association",
    db.Column(
        "revisor_process_id",
        db.Integer,
        db.ForeignKey("revisor_process.id"),
        primary_key=True,
    ),
    db.Column("evento_id", db.Integer, db.ForeignKey("evento.id"), primary_key=True),
    extend_existing=True,
)
class RevisaoConfig(db.Model):
    """Define regras globais de revisão para um evento (nº revisores, blind etc.)."""

    __tablename__ = "revisao_config"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(
        db.Integer, db.ForeignKey("evento.id"), nullable=False, unique=True
    )
    permitir_checkin_global = db.Column(db.Boolean, default=False)
    habilitar_feedback = db.Column(db.Boolean, default=False)
    habilitar_certificado_individual = db.Column(db.Boolean, default=False)
    habilitar_qrcode_evento_credenciamento = db.Column(db.Boolean, default=False)
    habilitar_submissao_trabalhos = db.Column(db.Boolean, default=False)
    mostrar_taxa = db.Column(db.Boolean, default=True)
    numero_revisores = db.Column(db.Integer, default=2)
    prazo_revisao = db.Column(db.DateTime, nullable=True)
    modelo_blind = db.Column(db.String(20), default="single")  # single | double | open

    evento = db.relationship(
        "Evento", backref=db.backref("revisao_config", uselist=False)
    )


class EventoBarema(db.Model):
    """Define os critérios de avaliação para um evento.

    ``requisitos`` armazena um dicionário onde cada chave é o nome do
    requisito e o valor é um objeto com os limites ``min`` e ``max``.
    Ex.: {"Critério": {"min": 1, "max": 5}}
    """

    __tablename__ = "evento_barema"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    requisitos = db.Column(db.JSON, nullable=False)

    evento = db.relationship(
        "Evento", backref=db.backref("evento_barema", uselist=False)
    )


class ConfiguracaoCertificadoEvento(db.Model):
    """Regras personalizadas para emissão de certificados em eventos."""

    __tablename__ = "config_certificado_evento"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)

    checkins_minimos = db.Column(db.Integer, default=0)
    percentual_minimo = db.Column(db.Integer, default=0)
    oficinas_obrigatorias = db.Column(db.Text, nullable=True)

    cliente = db.relationship(
        "Cliente", backref=db.backref("configs_certificado_evento", lazy=True)
    )
    evento = db.relationship(
        "Evento", backref=db.backref("config_certificado", uselist=False)
    )

    def get_oficinas_obrigatorias_list(self):
        if not self.oficinas_obrigatorias:
            return []
        return [int(o) for o in self.oficinas_obrigatorias.split(",") if o]


class RevisorEtapa(db.Model):
    __tablename__ = "revisor_etapa"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    process_id = db.Column(
        db.Integer, db.ForeignKey("revisor_process.id"), nullable=False
    )
    numero = db.Column(db.Integer, nullable=False)
    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)

    process = db.relationship(
        "RevisorProcess",
        backref=db.backref("etapas", cascade="all, delete-orphan", lazy=True),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RevisorEtapa process={self.process_id} numero={self.numero}>"


class RevisorCriterio(db.Model):
    __tablename__ = "revisor_criterio"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    process_id = db.Column(db.Integer, db.ForeignKey("revisor_process.id"), nullable=False)
    nome = db.Column(db.String(255), nullable=False)

    process = db.relationship(
        "RevisorProcess",
        backref=db.backref("criterios", cascade="all, delete-orphan", lazy=True),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RevisorCriterio process={self.process_id} nome={self.nome}>"


class RevisorRequisito(db.Model):
    __tablename__ = "revisor_requisito"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    criterio_id = db.Column(
        db.Integer,
        db.ForeignKey("revisor_criterio.id", ondelete="CASCADE"),
        nullable=False,
    )
    descricao = db.Column(db.String(255), nullable=False)

    criterio = db.relationship(
        "RevisorCriterio", backref=db.backref("requisitos", lazy=True)
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RevisorRequisito criterio={self.criterio_id}>"


class RevisorCandidatura(db.Model):
    __tablename__ = "revisor_candidatura"
    __table_args__ = {"extend_existing": True}


    id = db.Column(db.Integer, primary_key=True)
    process_id = db.Column(
        db.Integer, db.ForeignKey("revisor_process.id"), nullable=False
    )
    respostas = db.Column(db.JSON, nullable=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    codigo = db.Column(db.String(8), unique=True, default=lambda: str(uuid.uuid4())[:8])
    etapa_atual = db.Column(db.Integer, default=1)
    status = db.Column(db.String(50), default="pendente")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    process = db.relationship(
        "RevisorProcess",
        backref=db.backref("candidaturas", cascade="all, delete-orphan", lazy=True),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RevisorCandidatura process={self.process_id} status={self.status}>"


class RevisorCandidaturaEtapa(db.Model):
    __tablename__ = "revisor_candidatura_etapa"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    candidatura_id = db.Column(
        db.Integer, db.ForeignKey("revisor_candidatura.id"), nullable=False
    )
    etapa_id = db.Column(db.Integer, db.ForeignKey("revisor_etapa.id"), nullable=False)
    status = db.Column(db.String(50), default="pendente")
    observacoes = db.Column(db.Text, nullable=True)

    candidatura = db.relationship(
        "RevisorCandidatura",
        backref=db.backref(
            "etapas_status", cascade="all, delete-orphan", lazy=True
        ),
    )
    etapa = db.relationship("RevisorEtapa")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<RevisorCandidaturaEtapa candidatura={self.candidatura_id} "
            f"etapa={self.etapa_id} status={self.status}>"
        )


# -----------------------------------------------------------------------------
# REVIEWER APPLICATION (para usuários internos do sistema)
# -----------------------------------------------------------------------------
class ReviewerApplication(db.Model):
    """Candidatura de usuário para atuar como revisor."""

    __tablename__ = "reviewer_application"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    stage = db.Column(db.String(50), default="novo")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=True)

    usuario = db.relationship(
        "Usuario", backref=db.backref("reviewer_applications", lazy=True)
    )
    evento = db.relationship(
        "Evento", backref=db.backref("reviewer_applications", lazy=True)
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ReviewerApplication usuario={self.usuario_id} stage={self.stage}>"


# -----------------------------------------------------------------------------
# SUBMISSION (trabalhos científicos, resumos, etc.)
# -----------------------------------------------------------------------------
class Submission(db.Model):
    """Representa um trabalho submetido para avaliação em um evento."""

    __tablename__ = "submission"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)

    # textual fields
    abstract = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=True)

    # file upload (caminho para o arquivo no sistema de arquivos ou S3 etc.)
    file_path = db.Column(db.String(255), nullable=True)

    # locator & code (para acesso do autor e revisores externos)
    locator = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    code_hash = db.Column(db.String(256), nullable=False)

    # metadata
    status = db.Column(db.String(50), nullable=True)
    area_id = db.Column(db.Integer, nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    attributes = db.Column(db.JSON, default=dict)  # metadados importados

    # relationships
    author = db.relationship("Usuario", backref=db.backref("submissions", lazy=True))
    evento = db.relationship("Evento", backref=db.backref("submissions", lazy=True))

    # ------------------------------------------------------------------
    # utility
    # ------------------------------------------------------------------
    def __repr__(self):
        return f"<Submission {self.title}>"

    def check_code(self, code: str) -> bool:
        """Valida o código de acesso enviado pelo usuário."""
        if not code:
            return False
        return check_password_hash(self.code_hash, code)


# -----------------------------------------------------------------------------
# REVIEW (parecer da submissão)
# -----------------------------------------------------------------------------
class Review(db.Model):
    """Armazena o parecer de um revisor sobre uma submissão."""

    __tablename__ = "review"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(
        db.Integer, db.ForeignKey("submission.id"), nullable=False
    )

    # revisor (identificado ou anônimo)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    reviewer_name = db.Column(db.String(255), nullable=True)

    # segurança/acesso externo
    locator = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    access_code = db.Column(db.String(50), nullable=True)

    # detalhes
    blind_type = db.Column(
        db.String(20), nullable=True
    )  # single | double | open | anonimo
    scores = db.Column(db.JSON, nullable=True)  # ex.: {"originalidade": 4}
    note = db.Column(db.Integer, nullable=True)  # nota geral (0‑10) opcional
    comments = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(255), nullable=True)  # PDF anotado etc.
    decision = db.Column(
        db.String(50), nullable=True
    )  # accept | minor | major | reject
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    submission = db.relationship("Submission", backref=db.backref("reviews", lazy=True))
    reviewer = db.relationship("Usuario", backref=db.backref("reviews", lazy=True))

    def __repr__(self):
        return f"<Review {self.id} submission={self.submission_id}>"

    @property
    def duration(self):
        if self.started_at and self.finished_at:
            return int((self.finished_at - self.started_at).total_seconds())
        return None


# -----------------------------------------------------------------------------

# ASSIGNMENT (vincula revisor ↔ submissão)
# -----------------------------------------------------------------------------
class Assignment(db.Model):
    """Liga um revisor a uma submissão de trabalho (RespostaFormulario), controlando prazo e conclusão."""

    __tablename__ = "assignment"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    resposta_formulario_id = db.Column(
        db.Integer, db.ForeignKey("respostas_formulario.id"), nullable=False
    )
    reviewer_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    deadline = db.Column(db.DateTime, nullable=True)
    completed = db.Column(db.Boolean, default=False)
    
    # New fields for distribution tracking
    distribution_type = db.Column(db.String(20), nullable=True)  # 'manual' or 'automatic'
    distribution_date = db.Column(db.DateTime, nullable=True)
    distributed_by = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_reevaluation = db.Column(db.Boolean, nullable=False, default=False)

    resposta_formulario = db.relationship(
        "RespostaFormulario", backref=db.backref("assignments", lazy=True)
    )
    reviewer = db.relationship("Usuario", foreign_keys=[reviewer_id], backref=db.backref("assignments", lazy=True))
    distributor = db.relationship("Usuario", foreign_keys=[distributed_by], backref=db.backref("distributed_assignments", lazy=True))

    @property
    def submission(self):
        """Retorna a submissão associada através da resposta do formulário."""
        if self.resposta_formulario and self.resposta_formulario.trabalho_id:
            return Submission.query.get(self.resposta_formulario.trabalho_id)
        return None


# -----------------------------------------------------------------------------
# DISTRIBUTION LOG (log de distribuições de trabalhos)
# -----------------------------------------------------------------------------
class DistributionLog(db.Model):
    """Registra histórico de distribuições de trabalhos para revisores."""

    __tablename__ = "distribution_log"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=True)
    distribution_type = db.Column(db.String(20), nullable=False)  # 'manual' or 'automatic'
    total_works = db.Column(db.Integer, nullable=False)
    total_reviewers = db.Column(db.Integer, nullable=False)
    assignments_created = db.Column(db.Integer, nullable=False)
    distribution_date = db.Column(db.DateTime, nullable=False)
    distributed_by = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    filters_applied = db.Column(db.JSON, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    evento = db.relationship("Evento", backref=db.backref("distribution_logs", lazy=True))
    distributor = db.relationship("Usuario", backref=db.backref("distribution_logs", lazy=True))

    def __repr__(self):
        return f"<DistributionLog {self.id} evento={self.evento_id} type={self.distribution_type}>"


# Associação N:N entre processos de revisor e eventos (removida - usando a definição do topo do arquivo)

class RevisorProcess(db.Model):
    """Configura um processo seletivo de revisores."""

    __tablename__ = "revisor_process"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    formulario_id = db.Column(
        db.Integer,
        db.ForeignKey("formularios.id", ondelete="SET NULL"),
        nullable=True,
    )
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=True)
    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default="aberto")
    num_etapas = db.Column(db.Integer, default=1)

    # Controle de disponibilidade do processo
    availability_start = db.Column(db.DateTime, nullable=True)
    availability_end = db.Column(db.DateTime, nullable=True)
    exibir_para_participantes = db.Column(db.Boolean, default=False)

    cliente = db.relationship(
        "Cliente", backref=db.backref("revisor_processes", lazy=True)
    )
    formulario = db.relationship(
        "Formulario",
        backref=db.backref("revisor_processes", passive_deletes=True),
    )
    eventos = db.relationship(
        "Evento", secondary=revisor_process_evento_association, lazy="selectin"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RevisorProcess id={self.id} cliente={self.cliente_id}>"

    def is_available(self) -> bool:
        """Return True if the process is currently available."""
        today = date.today()
        if self.availability_start and today < self.availability_start.date():
            return False
        if self.availability_end and today > self.availability_end.date():
            return False
        return True


class ProcessoBarema(db.Model):
    """Conjunto de critérios de avaliação para um processo de revisores."""

    __tablename__ = "processo_barema"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    process_id = db.Column(
        db.Integer, db.ForeignKey("revisor_process.id"), nullable=False, unique=True
    )

    process = db.relationship(
        "RevisorProcess",
        backref=db.backref(
            "processo_barema", uselist=False, cascade="all, delete-orphan"
        ),
    )
    requisitos = db.relationship(
        "ProcessoBaremaRequisito",
        backref="barema",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ProcessoBarema id={self.id} process={self.process_id}>"


class ProcessoBaremaRequisito(db.Model):
    """Requisito avaliativo pertencente a um barema de processo."""

    __tablename__ = "processo_barema_requisito"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    barema_id = db.Column(
        db.Integer, db.ForeignKey("processo_barema.id"), nullable=False
    )
    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    pontuacao_min = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    pontuacao_max = db.Column(db.Numeric(5, 2), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ProcessoBaremaRequisito id={self.id} barema={self.barema_id}>"


class CategoriaBarema(db.Model):
    """Barema personalizado por categoria de trabalho."""

    __tablename__ = "categoria_barema"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    categoria = db.Column(db.String(255), nullable=False)
    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    criterios = db.Column(db.JSON, nullable=False)  # {"criterio1": {"nome": "...", "descricao": "...", "pontuacao_max": 10}, ...}
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    evento = db.relationship("Evento", backref=db.backref("categoria_baremas", lazy=True))

    def __repr__(self) -> str:
        return f"<CategoriaBarema id={self.id} evento={self.evento_id} categoria={self.categoria}>"

    def get_total_pontuacao_maxima(self):
        """Retorna a pontuação máxima total do barema."""
        if not self.criterios:
            return 0
        return sum(criterio.get('pontuacao_max', 0) for criterio in self.criterios.values())

    @classmethod
    def get_barema_por_categoria(cls, evento_id, categoria):
        """Busca barema específico para uma categoria em um evento."""
        return cls.query.filter_by(
            evento_id=evento_id,
            categoria=categoria,
            ativo=True
        ).first()


class TesteBarema(db.Model):
    """Armazena resultados de testes de baremas."""

    __tablename__ = "teste_barema"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    barema_id = db.Column(db.Integer, db.ForeignKey("categoria_barema.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    pontuacoes = db.Column(db.JSON, nullable=False)  # {"criterio1": 8.5, "criterio2": 9.0, ...}
    total_pontos = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # relationships
    barema = db.relationship("CategoriaBarema", backref=db.backref("testes", lazy=True))
    usuario = db.relationship("Usuario", backref=db.backref("testes_barema", lazy=True))

    def __repr__(self) -> str:
        return f"<TesteBarema id={self.id} barema={self.barema_id} usuario={self.usuario_id}>"
