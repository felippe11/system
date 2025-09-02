from datetime import datetime
from extensions import db


class Polo(db.Model):
    """Modelo para representar polos formativos."""
    __tablename__ = "polo"
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    endereco = db.Column(db.String(500), nullable=True)
    responsavel = db.Column(db.String(255), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com cliente
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    cliente = db.relationship("Cliente", backref=db.backref("polos", lazy=True))
    
    # Relacionamento com materiais
    materiais = db.relationship("Material", back_populates="polo", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Polo {self.nome}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'endereco': self.endereco,
            'responsavel': self.responsavel,
            'telefone': self.telefone,
            'email': self.email,
            'ativo': self.ativo,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Material(db.Model):
    """Modelo para representar materiais de um polo."""
    __tablename__ = "material"
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    unidade = db.Column(db.String(50), nullable=False, default="unidade")  # unidade, kg, litro, etc.
    categoria = db.Column(db.String(100), nullable=True)  # categoria do material
    
    # Quantidades
    quantidade_inicial = db.Column(db.Integer, nullable=False, default=0)
    quantidade_atual = db.Column(db.Integer, nullable=False, default=0)
    quantidade_consumida = db.Column(db.Integer, nullable=False, default=0)
    quantidade_minima = db.Column(db.Integer, nullable=False, default=0)  # estoque mínimo
    
    # Controle
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    polo_id = db.Column(db.Integer, db.ForeignKey("polo.id"), nullable=False)
    polo = db.relationship("Polo", back_populates="materiais")
    
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    cliente = db.relationship("Cliente", backref=db.backref("materiais", lazy=True))
    
    # Relacionamento com movimentações
    movimentacoes = db.relationship("MovimentacaoMaterial", back_populates="material", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Material {self.nome} - {self.polo.nome}>"
    
    @property
    def quantidade_necessaria(self):
        """Calcula a quantidade necessária para compra."""
        if self.quantidade_atual < self.quantidade_minima:
            return self.quantidade_minima - self.quantidade_atual
        return 0
    
    @property
    def status_estoque(self):
        """Retorna o status do estoque."""
        if self.quantidade_atual <= 0:
            return "esgotado"
        elif self.quantidade_atual <= self.quantidade_minima:
            return "baixo"
        else:
            return "normal"
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'unidade': self.unidade,
            'categoria': self.categoria,
            'quantidade_inicial': self.quantidade_inicial,
            'quantidade_atual': self.quantidade_atual,
            'quantidade_consumida': self.quantidade_consumida,
            'quantidade_minima': self.quantidade_minima,
            'quantidade_necessaria': self.quantidade_necessaria,
            'status_estoque': self.status_estoque,
            'ativo': self.ativo,
            'polo_id': self.polo_id,
            'polo_nome': self.polo.nome if self.polo else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class MovimentacaoMaterial(db.Model):
    """Modelo para registrar movimentações de materiais."""
    __tablename__ = "movimentacao_material"
    
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)  # entrada, saida, ajuste
    quantidade = db.Column(db.Integer, nullable=False)
    observacao = db.Column(db.Text, nullable=True)
    data_movimentacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    material_id = db.Column(db.Integer, db.ForeignKey("material.id"), nullable=False)
    material = db.relationship("Material", back_populates="movimentacoes")
    
    # Usuário responsável pela movimentação
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    usuario = db.relationship("Usuario", backref=db.backref("movimentacoes_material", lazy=True))
    
    # Monitor responsável (se aplicável)
    monitor_id = db.Column(db.Integer, db.ForeignKey("monitor.id"), nullable=True)
    monitor = db.relationship("Monitor", backref=db.backref("movimentacoes_material", lazy=True))
    
    def __repr__(self):
        return f"<MovimentacaoMaterial {self.tipo} - {self.quantidade} {self.material.nome}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'tipo': self.tipo,
            'quantidade': self.quantidade,
            'observacao': self.observacao,
            'data_movimentacao': self.data_movimentacao.isoformat() if self.data_movimentacao else None,
            'material_id': self.material_id,
            'material_nome': self.material.nome if self.material else None,
            'usuario_id': self.usuario_id,
            'usuario_nome': self.usuario.nome if self.usuario else None,
            'monitor_id': self.monitor_id,
            'monitor_nome': self.monitor.nome_completo if self.monitor else None
        }


class MonitorPolo(db.Model):
    """Modelo para associar monitores a polos específicos."""
    __tablename__ = "monitor_polo"
    
    id = db.Column(db.Integer, primary_key=True)
    monitor_id = db.Column(db.Integer, db.ForeignKey("monitor.id"), nullable=False)
    polo_id = db.Column(db.Integer, db.ForeignKey("polo.id"), nullable=False)
    data_atribuicao = db.Column(db.DateTime, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)
    
    # Relacionamentos
    monitor = db.relationship("Monitor", backref=db.backref("polos_atribuidos", lazy=True))
    polo = db.relationship("Polo", backref=db.backref("monitores_atribuidos", lazy=True))
    
    def __repr__(self):
        return f"<MonitorPolo {self.monitor.nome_completo} - {self.polo.nome}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'monitor_id': self.monitor_id,
            'monitor_nome': self.monitor.nome_completo if self.monitor else None,
            'polo_id': self.polo_id,
            'polo_nome': self.polo.nome if self.polo else None,
            'data_atribuicao': self.data_atribuicao.isoformat() if self.data_atribuicao else None,
            'ativo': self.ativo
        }