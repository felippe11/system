from datetime import datetime
from extensions import db
from sqlalchemy import func


class Orcamento(db.Model):
    """Modelo para controle orçamentário por polo."""
    __tablename__ = "orcamento"
    
    id = db.Column(db.Integer, primary_key=True)
    polo_id = db.Column(db.Integer, db.ForeignKey("polo.id"), nullable=False)
    
    # Valores orçamentários
    valor_total = db.Column(db.Float, nullable=False, default=0.0)
    valor_custeio = db.Column(db.Float, nullable=False, default=0.0)
    valor_capital = db.Column(db.Float, nullable=False, default=0.0)
    
    # Período do orçamento
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    ano_orcamento = db.Column(db.Integer, nullable=False)
    
    # Controle
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    observacoes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    polo = db.relationship("Polo", backref=db.backref("orcamentos", lazy=True))
    historico_alteracoes = db.relationship("HistoricoOrcamento", backref="orcamento", lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Orcamento {self.polo_id} - {self.ano_orcamento}>"
    
    @property
    def valor_gasto_total(self):
        """Calcula o valor total gasto no período."""
        from models.compra import Compra
        
        total = db.session.query(func.sum(Compra.valor_total)).filter(
            Compra.polo_id == self.polo_id,
            Compra.data_compra >= self.data_inicio,
            Compra.data_compra <= self.data_fim,
            Compra.status != 'Cancelada'
        ).scalar()
        
        return float(total or 0)
    
    @property
    def percentual_gasto(self):
        """Calcula o percentual gasto do orçamento."""
        if self.valor_total <= 0:
            return 0
        return (self.valor_gasto_total / self.valor_total) * 100
    
    @property
    def valor_disponivel(self):
        """Calcula o valor disponível no orçamento."""
        return self.valor_total - self.valor_gasto_total
    
    def to_dict(self):
        """Converte o orçamento para dicionário."""
        return {
            'id': self.id,
            'polo_id': self.polo_id,
            'polo_nome': self.polo.nome if self.polo else None,
            'valor_total': float(self.valor_total),
            'valor_custeio': float(self.valor_custeio),
            'valor_capital': float(self.valor_capital),
            'valor_gasto_total': self.valor_gasto_total,
            'percentual_gasto': self.percentual_gasto,
            'valor_disponivel': self.valor_disponivel,
            'data_inicio': self.data_inicio.isoformat() if self.data_inicio else None,
            'data_fim': self.data_fim.isoformat() if self.data_fim else None,
            'ano_orcamento': self.ano_orcamento,
            'ativo': self.ativo,
            'observacoes': self.observacoes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class HistoricoOrcamento(db.Model):
    """Modelo para histórico de alterações orçamentárias."""
    __tablename__ = "historico_orcamento"
    
    id = db.Column(db.Integer, primary_key=True)
    orcamento_id = db.Column(db.Integer, db.ForeignKey("orcamento.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    
    # Tipo de alteração
    tipo_alteracao = db.Column(db.String(50), nullable=False)  # 'criacao', 'edicao', 'ativacao', 'desativacao'
    
    # Valores anteriores
    valor_total_anterior = db.Column(db.Float)
    valor_custeio_anterior = db.Column(db.Float)
    valor_capital_anterior = db.Column(db.Float)
    
    # Valores novos
    valor_total_novo = db.Column(db.Float)
    valor_custeio_novo = db.Column(db.Float)
    valor_capital_novo = db.Column(db.Float)
    
    # Detalhes da alteração
    motivo = db.Column(db.Text)
    observacoes = db.Column(db.Text)
    data_alteracao = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    usuario = db.relationship("Usuario", backref=db.backref("alteracoes_orcamento", lazy=True))
    
    def __repr__(self):
        return f"<HistoricoOrcamento {self.orcamento_id} - {self.tipo_alteracao}>"
    
    @property
    def variacao_total(self):
        """Calcula a variação no valor total."""
        if self.valor_total_anterior is None or self.valor_total_novo is None:
            return 0
        return self.valor_total_novo - self.valor_total_anterior
    
    @property
    def variacao_percentual_total(self):
        """Calcula a variação percentual no valor total."""
        if not self.valor_total_anterior or self.valor_total_anterior == 0:
            return 0
        return (self.variacao_total / self.valor_total_anterior) * 100
    
    def to_dict(self):
        """Converte o histórico para dicionário."""
        return {
            'id': self.id,
            'orcamento_id': self.orcamento_id,
            'usuario_id': self.usuario_id,
            'usuario_nome': self.usuario.nome if self.usuario else None,
            'tipo_alteracao': self.tipo_alteracao,
            'valor_total_anterior': float(self.valor_total_anterior or 0),
            'valor_custeio_anterior': float(self.valor_custeio_anterior or 0),
            'valor_capital_anterior': float(self.valor_capital_anterior or 0),
            'valor_total_novo': float(self.valor_total_novo or 0),
            'valor_custeio_novo': float(self.valor_custeio_novo or 0),
            'valor_capital_novo': float(self.valor_capital_novo or 0),
            'variacao_total': self.variacao_total,
            'variacao_percentual_total': self.variacao_percentual_total,
            'motivo': self.motivo,
            'observacoes': self.observacoes,
            'data_alteracao': self.data_alteracao.isoformat() if self.data_alteracao else None
        }