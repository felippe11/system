<<<<<<< HEAD
from datetime import datetime
from extensions import db


class AvaliacaoBarema(db.Model):
    """Avaliação de um trabalho usando critérios de barema."""
    
    __tablename__ = "avaliacao_barema"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    trabalho_id = db.Column(db.Integer, db.ForeignKey("submission.id"), nullable=False)
    revisor_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    barema_id = db.Column(db.Integer, nullable=False)  # Pode referenciar CategoriaBarema ou EventoBarema
    categoria = db.Column(db.String(255), nullable=False)
    nota_final = db.Column(db.Float, nullable=True)
    data_avaliacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    trabalho = db.relationship("Submission", backref="avaliacoes_barema")
    revisor = db.relationship("Usuario", backref="avaliacoes_realizadas")
    criterios_avaliacao = db.relationship("AvaliacaoCriterio", backref="avaliacao", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AvaliacaoBarema {self.id}: Trabalho {self.trabalho_id} - Categoria {self.categoria}>"


class AvaliacaoCriterio(db.Model):
    """Avaliação individual de um critério específico."""
    
    __tablename__ = "avaliacao_criterio"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    avaliacao_id = db.Column(db.Integer, db.ForeignKey("avaliacao_barema.id"), nullable=False)
    criterio_id = db.Column(db.String(255), nullable=False)  # ID ou nome do critério no JSON do barema
    nota = db.Column(db.Float, nullable=False)
    observacao = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
=======
from datetime import datetime
from extensions import db


class AvaliacaoBarema(db.Model):
    """Avaliação de um trabalho usando critérios de barema."""
    
    __tablename__ = "avaliacao_barema"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    trabalho_id = db.Column(db.Integer, db.ForeignKey("submission.id"), nullable=False)
    revisor_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    nome_revisor = db.Column(db.String(255), nullable=True)  # Nome do revisor exibido na página
    barema_id = db.Column(db.Integer, nullable=False)  # Pode referenciar CategoriaBarema ou EventoBarema
    categoria = db.Column(db.String(255), nullable=False)
    nota_final = db.Column(db.Float, nullable=True)
    data_avaliacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    trabalho = db.relationship("Submission", backref="avaliacoes_barema")
    revisor = db.relationship("Usuario", backref="avaliacoes_realizadas")
    criterios_avaliacao = db.relationship("AvaliacaoCriterio", backref="avaliacao", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AvaliacaoBarema {self.id}: Trabalho {self.trabalho_id} - Categoria {self.categoria}>"


class AvaliacaoCriterio(db.Model):
    """Avaliação individual de um critério específico."""
    
    __tablename__ = "avaliacao_criterio"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    avaliacao_id = db.Column(db.Integer, db.ForeignKey("avaliacao_barema.id"), nullable=False)
    criterio_id = db.Column(db.String(255), nullable=False)  # ID ou nome do critério no JSON do barema
    nota = db.Column(db.Float, nullable=False)
    observacao = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
>>>>>>> c593328b09b311b97c969034b12baa1c351a90bd
        return f"<AvaliacaoCriterio {self.id}: Critério {self.criterio_id} - Nota {self.nota}>"