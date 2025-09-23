from datetime import datetime
from extensions import db
import uuid


class SubmissionCategory(db.Model):
    """Categorias de submissão para classificação de trabalhos."""
    
    __tablename__ = "submission_category"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    normalized_name = db.Column(db.String(100), nullable=False)  # Nome normalizado para matching
    description = db.Column(db.Text, nullable=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    active = db.Column(db.Boolean, default=True)
    
    # Relacionamentos
    evento = db.relationship("Evento", backref=db.backref("submission_categories", lazy=True))
    
    def __repr__(self):
        return f"<SubmissionCategory {self.name}>"


class ReviewerProfile(db.Model):
    """Perfil estendido do revisor com capacidades e preferências."""
    
    __tablename__ = "reviewer_profile"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False, unique=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    
    # Capacidades
    max_assignments = db.Column(db.Integer, default=15)  # Máximo de trabalhos
    current_load = db.Column(db.Integer, default=0)  # Carga atual
    available = db.Column(db.Boolean, default=True)
    
    # Informações adicionais
    institution = db.Column(db.String(255), nullable=True)
    expertise_areas = db.Column(db.Text, nullable=True)  # Áreas de especialização
    
    # Controle de conflitos
    excluded_institutions = db.Column(db.JSON, default=list)  # Instituições a evitar
    excluded_authors = db.Column(db.JSON, default=list)  # Autores a evitar
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    usuario = db.relationship("Usuario", backref=db.backref("reviewer_profile", uselist=False))
    evento = db.relationship("Evento", backref=db.backref("reviewer_profiles", lazy=True))
    
    def __repr__(self):
        return f"<ReviewerProfile usuario={self.usuario_id} load={self.current_load}/{self.max_assignments}>"
    
    @property
    def availability_percentage(self):
        """Retorna a porcentagem de disponibilidade do revisor."""
        if self.max_assignments == 0:
            return 0
        return max(0, (self.max_assignments - self.current_load) / self.max_assignments * 100)
    
    @property
    def can_accept_assignment(self):
        """Verifica se o revisor pode aceitar mais atribuições."""
        return self.available and self.current_load < self.max_assignments


class ReviewerPreference(db.Model):
    """Preferências do revisor por categoria de submissão."""
    
    __tablename__ = "reviewer_preference"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    reviewer_profile_id = db.Column(db.Integer, db.ForeignKey("reviewer_profile.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("submission_category.id"), nullable=False)
    affinity_level = db.Column(db.Integer, nullable=False, default=1)  # 0-3 (0=evitar, 1=baixa, 2=média, 3=alta)
    
    # Relacionamentos
    reviewer_profile = db.relationship("ReviewerProfile", backref=db.backref("preferences", lazy=True))
    category = db.relationship("SubmissionCategory", backref=db.backref("reviewer_preferences", lazy=True))
    
    # Constraint única
    __table_args__ = (
        db.UniqueConstraint('reviewer_profile_id', 'category_id', name='unique_reviewer_category_preference'),
        {"extend_existing": True}
    )
    
    def __repr__(self):
        return f"<ReviewerPreference reviewer={self.reviewer_profile_id} category={self.category_id} affinity={self.affinity_level}>"


class DistributionConfig(db.Model):
    """Configuração de distribuição automática para um evento."""
    
    __tablename__ = "distribution_config"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False, unique=True)
    
    # Configurações básicas
    reviewers_per_submission = db.Column(db.Integer, default=2)
    distribution_mode = db.Column(db.String(50), default="balanced")  # balanced | stratified | random
    blind_type = db.Column(db.String(20), default="single")  # single | double | open
    
    # Configurações avançadas
    enable_conflict_detection = db.Column(db.Boolean, default=True)
    enable_load_balancing = db.Column(db.Boolean, default=True)
    enable_affinity_matching = db.Column(db.Boolean, default=True)
    
    # Limites e cotas
    max_submissions_per_reviewer = db.Column(db.Integer, default=15)
    min_affinity_level = db.Column(db.Integer, default=1)  # Nível mínimo de afinidade
    
    # Configurações de fallback
    allow_overload_on_shortage = db.Column(db.Boolean, default=False)
    fallback_to_random = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    evento = db.relationship("Evento", backref=db.backref("distribution_config", uselist=False))
    
    def __repr__(self):
        return f"<DistributionConfig evento={self.evento_id} mode={self.distribution_mode}>"


class AutoDistributionLog(db.Model):
    """Log de auditoria das distribuições automáticas."""

    __tablename__ = "auto_distribution_log"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    
    # Informações da distribuição
    total_submissions = db.Column(db.Integer, nullable=False)
    total_assignments = db.Column(db.Integer, nullable=False)
    distribution_seed = db.Column(db.String(50), nullable=True)  # Seed para reproduzibilidade
    
    # Estatísticas
    conflicts_detected = db.Column(db.Integer, default=0)
    fallback_assignments = db.Column(db.Integer, default=0)
    failed_assignments = db.Column(db.Integer, default=0)
    
    # Detalhes em JSON
    distribution_details = db.Column(db.JSON, default=dict)  # Detalhes da distribuição
    error_log = db.Column(db.JSON, default=list)  # Erros encontrados
    
    # Timestamps
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    
    # Relacionamentos
    evento = db.relationship(
        "Evento", backref=db.backref("auto_distribution_logs", lazy=True)
    )

    def __repr__(self):
        return (
            f"<AutoDistributionLog evento={self.evento_id} "
            f"submissions={self.total_submissions}>"
        )
    
    def mark_completed(self):
        """Marca a distribuição como concluída e calcula a duração."""
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())


class ImportedSubmission(db.Model):
    """Submissões importadas de planilhas com mapeamento dinâmico."""
    
    __tablename__ = "imported_submission"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    
    # Dados básicos
    title = db.Column(db.String(500), nullable=False)
    authors = db.Column(db.Text, nullable=True)  # Lista de autores
    author_email = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(100), nullable=True)
    modality = db.Column(db.String(100), nullable=True)
    submission_type = db.Column(db.String(100), nullable=True)
    keywords = db.Column(db.Text, nullable=True)
    abstract = db.Column(db.Text, nullable=True)
    
    # Dados da importação
    import_batch_id = db.Column(db.String(36), default=lambda: str(uuid.uuid4()))
    original_row_data = db.Column(db.JSON, default=dict)  # Dados originais da linha
    mapping_config = db.Column(db.JSON, default=dict)  # Configuração de mapeamento usada
    
    # Status de processamento
    processed = db.Column(db.Boolean, default=False)
    submission_id = db.Column(db.Integer, db.ForeignKey("submission.id"), nullable=True)  # Link para submission criada
    processing_errors = db.Column(db.JSON, default=list)
    
    # Timestamps
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    
    # Relacionamentos
    evento = db.relationship("Evento", backref=db.backref("imported_submissions", lazy=True))
    submission = db.relationship("Submission", backref=db.backref("imported_from", uselist=False))
    
    def __repr__(self):
        return f"<ImportedSubmission {self.title[:50]}... processed={self.processed}>"
    
    def mark_processed(self, submission_id=None, errors=None):
        """Marca a submissão como processada."""
        self.processed = True
        self.processed_at = datetime.utcnow()
        if submission_id:
            self.submission_id = submission_id
        if errors:
            self.processing_errors = errors


class SpreadsheetMapping(db.Model):
    """Configurações de mapeamento de colunas de planilhas."""
    
    __tablename__ = "spreadsheet_mapping"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # Nome da configuração
    
    # Mapeamento de colunas
    column_mappings = db.Column(db.JSON, nullable=False)  # {"title": "A", "authors": "B", ...}
    normalization_rules = db.Column(db.JSON, default=dict)  # Regras de normalização
    
    # Configurações
    is_default = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    
    # Relacionamentos
    evento = db.relationship("Evento", backref=db.backref("spreadsheet_mappings", lazy=True))
    creator = db.relationship("Usuario", backref=db.backref("created_mappings", lazy=True))
    
    def __repr__(self):
        return f"<SpreadsheetMapping {self.name} evento={self.evento_id}>"