from datetime import datetime
from extensions import db
from sqlalchemy import func


class OrcamentoCliente(db.Model):
    """Modelo para controle orçamentário do cliente."""
    __tablename__ = "orcamento_cliente"
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    
    # Valores orçamentários
    valor_total_disponivel = db.Column(db.Float, nullable=False, default=0.0)
    valor_custeio_disponivel = db.Column(db.Float, nullable=False, default=0.0)
    valor_capital_disponivel = db.Column(db.Float, nullable=False, default=0.0)
    
    # Valores de alerta
    valor_alerta_total = db.Column(db.Float, nullable=False, default=0.0)
    valor_alerta_custeio = db.Column(db.Float, nullable=False, default=0.0)
    valor_alerta_capital = db.Column(db.Float, nullable=False, default=0.0)
    
    # Período do orçamento
    ano_orcamento = db.Column(db.Integer, nullable=False)
    mes_inicio = db.Column(db.Integer, nullable=False, default=1)
    mes_fim = db.Column(db.Integer, nullable=False, default=12)
    
    # Controle
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    cliente = db.relationship("Cliente", backref=db.backref("orcamentos", lazy=True))
    
    def __repr__(self):
        return f"<OrcamentoCliente {self.cliente_id} - {self.ano_orcamento}>"
    
    @property
    def valor_gasto_total(self):
        """Calcula o valor total gasto no período."""
        from datetime import date
        inicio_periodo = date(self.ano_orcamento, self.mes_inicio, 1)
        if self.mes_fim == 12:
            fim_periodo = date(self.ano_orcamento + 1, 1, 1)
        else:
            fim_periodo = date(self.ano_orcamento, self.mes_fim + 1, 1)
        
        total = db.session.query(func.sum(Compra.valor_total)).filter(
            Compra.cliente_id == self.cliente_id,
            Compra.data_compra >= inicio_periodo,
            Compra.data_compra < fim_periodo,
            Compra.ativo.is_(True)
        ).scalar() or 0.0
        
        return total
    
    @property
    def valor_gasto_custeio(self):
        """Calcula o valor gasto em custeio no período."""
        from datetime import date
        inicio_periodo = date(self.ano_orcamento, self.mes_inicio, 1)
        if self.mes_fim == 12:
            fim_periodo = date(self.ano_orcamento + 1, 1, 1)
        else:
            fim_periodo = date(self.ano_orcamento, self.mes_fim + 1, 1)
        
        total = db.session.query(func.sum(Compra.valor_total)).filter(
            Compra.cliente_id == self.cliente_id,
            Compra.tipo_gasto == 'custeio',
            Compra.data_compra >= inicio_periodo,
            Compra.data_compra < fim_periodo,
            Compra.ativo.is_(True)
        ).scalar() or 0.0
        
        return total
    
    @property
    def valor_gasto_capital(self):
        """Calcula o valor gasto em capital no período."""
        from datetime import date
        inicio_periodo = date(self.ano_orcamento, self.mes_inicio, 1)
        if self.mes_fim == 12:
            fim_periodo = date(self.ano_orcamento + 1, 1, 1)
        else:
            fim_periodo = date(self.ano_orcamento, self.mes_fim + 1, 1)
        
        total = db.session.query(func.sum(Compra.valor_total)).filter(
            Compra.cliente_id == self.cliente_id,
            Compra.tipo_gasto == 'capital',
            Compra.data_compra >= inicio_periodo,
            Compra.data_compra < fim_periodo,
            Compra.ativo.is_(True)
        ).scalar() or 0.0
        
        return total
    
    @property
    def percentual_gasto_total(self):
        """Calcula o percentual gasto do orçamento total."""
        if self.valor_total_disponivel <= 0:
            return 0
        return (self.valor_gasto_total / self.valor_total_disponivel) * 100
    
    @property
    def percentual_gasto_custeio(self):
        """Calcula o percentual gasto do orçamento de custeio."""
        if self.valor_custeio_disponivel <= 0:
            return 0
        return (self.valor_gasto_custeio / self.valor_custeio_disponivel) * 100
    
    @property
    def percentual_gasto_capital(self):
        """Calcula o percentual gasto do orçamento de capital."""
        if self.valor_capital_disponivel <= 0:
            return 0
        return (self.valor_gasto_capital / self.valor_capital_disponivel) * 100
    
    @property
    def alerta_total(self):
        """Verifica se o gasto total atingiu o valor de alerta."""
        return self.valor_gasto_total >= self.valor_alerta_total
    
    @property
    def alerta_custeio(self):
        """Verifica se o gasto de custeio atingiu o valor de alerta."""
        return self.valor_gasto_custeio >= self.valor_alerta_custeio
    
    @property
    def alerta_capital(self):
        """Verifica se o gasto de capital atingiu o valor de alerta."""
        return self.valor_gasto_capital >= self.valor_alerta_capital
    
    def to_dict(self):
        return {
            'id': self.id,
            'cliente_id': self.cliente_id,
            'valor_total_disponivel': self.valor_total_disponivel,
            'valor_custeio_disponivel': self.valor_custeio_disponivel,
            'valor_capital_disponivel': self.valor_capital_disponivel,
            'valor_alerta_total': self.valor_alerta_total,
            'valor_alerta_custeio': self.valor_alerta_custeio,
            'valor_alerta_capital': self.valor_alerta_capital,
            'ano_orcamento': self.ano_orcamento,
            'mes_inicio': self.mes_inicio,
            'mes_fim': self.mes_fim,
            'valor_gasto_total': self.valor_gasto_total,
            'valor_gasto_custeio': self.valor_gasto_custeio,
            'valor_gasto_capital': self.valor_gasto_capital,
            'percentual_gasto_total': self.percentual_gasto_total,
            'percentual_gasto_custeio': self.percentual_gasto_custeio,
            'percentual_gasto_capital': self.percentual_gasto_capital,
            'alerta_total': self.alerta_total,
            'alerta_custeio': self.alerta_custeio,
            'alerta_capital': self.alerta_capital,
            'ativo': self.ativo,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class NivelAprovacao(db.Model):
    """Modelo para representar níveis de aprovação de compras."""
    __tablename__ = "nivel_aprovacao"
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    ordem = db.Column(db.Integer, nullable=False)  # Ordem do nível (1, 2, 3...)
    valor_minimo = db.Column(db.Float, nullable=False, default=0.0)
    valor_maximo = db.Column(db.Float, nullable=True)  # NULL = sem limite
    obrigatorio = db.Column(db.Boolean, default=True, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relacionamentos
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    cliente = db.relationship("Cliente", backref=db.backref("niveis_aprovacao", lazy=True))
    
    # Controle
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<NivelAprovacao {self.nome}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'ordem': self.ordem,
            'valor_minimo': self.valor_minimo,
            'valor_maximo': self.valor_maximo,
            'obrigatorio': self.obrigatorio,
            'ativo': self.ativo,
            'cliente_id': self.cliente_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class AprovacaoCompra(db.Model):
    """Modelo para representar aprovações de compras."""
    __tablename__ = "aprovacao_compra"
    
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False, default='pendente')  # pendente, aprovada, rejeitada
    comentario = db.Column(db.Text, nullable=True)
    data_aprovacao = db.Column(db.DateTime, nullable=True)
    
    # Relacionamentos
    compra_id = db.Column(db.Integer, db.ForeignKey("compra.id"), nullable=False)
    compra = db.relationship("Compra", backref=db.backref("aprovacoes", lazy=True))
    
    nivel_aprovacao_id = db.Column(db.Integer, db.ForeignKey("nivel_aprovacao.id"), nullable=False)
    nivel_aprovacao = db.relationship("NivelAprovacao", backref=db.backref("aprovacoes", lazy=True))
    
    aprovador_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    aprovador = db.relationship("Usuario", backref=db.backref("aprovacoes_realizadas", lazy=True))
    
    # Controle
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<AprovacaoCompra {self.compra_id} - {self.nivel_aprovacao.nome}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'status': self.status,
            'comentario': self.comentario,
            'data_aprovacao': self.data_aprovacao.isoformat() if self.data_aprovacao else None,
            'compra_id': self.compra_id,
            'nivel_aprovacao_id': self.nivel_aprovacao_id,
            'nivel_aprovacao': self.nivel_aprovacao.to_dict() if self.nivel_aprovacao else None,
            'aprovador_id': self.aprovador_id,
            'aprovador': self.aprovador.nome if self.aprovador else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Compra(db.Model):
    """Modelo para representar compras de materiais."""
    __tablename__ = "compra"
    
    id = db.Column(db.Integer, primary_key=True)
    numero_compra = db.Column(db.String(50), nullable=False, unique=True)
    descricao = db.Column(db.Text, nullable=True)
    fornecedor = db.Column(db.String(255), nullable=False)
    cnpj_fornecedor = db.Column(db.String(18), nullable=True)
    endereco_fornecedor = db.Column(db.Text, nullable=True)
    telefone_fornecedor = db.Column(db.String(20), nullable=True)
    email_fornecedor = db.Column(db.String(255), nullable=True)
    
    # Valores financeiros
    valor_total = db.Column(db.Float, nullable=False, default=0.0)
    valor_frete = db.Column(db.Float, nullable=True, default=0.0)
    valor_desconto = db.Column(db.Float, nullable=True, default=0.0)
    valor_impostos = db.Column(db.Float, nullable=True, default=0.0)
    
    # Datas
    data_compra = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_entrega_prevista = db.Column(db.DateTime, nullable=True)
    data_entrega_realizada = db.Column(db.DateTime, nullable=True)
    
    # Status da compra
    status = db.Column(db.String(50), nullable=False, default='pendente')  # pendente, aprovada, entregue, cancelada
    
    # Tipo de gasto
    tipo_gasto = db.Column(db.String(20), nullable=False, default='custeio')  # custeio, capital
    
    # Observações e justificativas
    observacoes = db.Column(db.Text, nullable=True)
    justificativa = db.Column(db.Text, nullable=True)
    
    # Controle
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    cliente = db.relationship("Cliente", backref=db.backref("compras", lazy=True))
    
    polo_id = db.Column(db.Integer, db.ForeignKey("polo.id"), nullable=True)
    polo = db.relationship("Polo", backref=db.backref("compras", lazy=True))
    
    # Usuário responsável pela compra
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    usuario = db.relationship("Usuario", backref=db.backref("compras_realizadas", lazy=True))
    
    # Relacionamentos com itens e documentos
    itens = db.relationship("ItemCompra", back_populates="compra", cascade="all, delete-orphan")
    documentos = db.relationship("DocumentoFiscal", back_populates="compra", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Compra {self.numero_compra} - {self.fornecedor}>"
    
    @property
    def valor_liquido(self):
        """Calcula o valor líquido da compra (total - desconto + frete + impostos)."""
        return (self.valor_total or 0) - (self.valor_desconto or 0) + (self.valor_frete or 0) + (self.valor_impostos or 0)
    
    @property
    def status_entrega(self):
        """Retorna o status da entrega."""
        if self.data_entrega_realizada:
            return "entregue"
        elif self.data_entrega_prevista and self.data_entrega_prevista < datetime.utcnow():
            return "atrasada"
        elif self.data_entrega_prevista:
            return "prevista"
        else:
            return "sem_previsao"
    
    def to_dict(self):
        return {
            'id': self.id,
            'numero_compra': self.numero_compra,
            'descricao': self.descricao,
            'fornecedor': self.fornecedor,
            'cnpj_fornecedor': self.cnpj_fornecedor,
            'endereco_fornecedor': self.endereco_fornecedor,
            'telefone_fornecedor': self.telefone_fornecedor,
            'email_fornecedor': self.email_fornecedor,
            'valor_total': self.valor_total,
            'valor_frete': self.valor_frete,
            'valor_desconto': self.valor_desconto,
            'valor_impostos': self.valor_impostos,
            'valor_liquido': self.valor_liquido,
            'data_compra': self.data_compra.isoformat() if self.data_compra else None,
            'data_entrega_prevista': self.data_entrega_prevista.isoformat() if self.data_entrega_prevista else None,
            'data_entrega_realizada': self.data_entrega_realizada.isoformat() if self.data_entrega_realizada else None,
            'status': self.status,
            'tipo_gasto': self.tipo_gasto,
            'status_entrega': self.status_entrega,
            'observacoes': self.observacoes,
            'justificativa': self.justificativa,
            'ativo': self.ativo,
            'polo_id': self.polo_id,
            'polo_nome': self.polo.nome if self.polo else None,
            'cliente_id': self.cliente_id,
            'usuario_id': self.usuario_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'total_itens': len(self.itens) if self.itens else 0,
            'total_documentos': len(self.documentos) if self.documentos else 0
        }


class ItemCompra(db.Model):
    """Modelo para representar itens de uma compra."""
    __tablename__ = "item_compra"
    
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(255), nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    unidade = db.Column(db.String(50), nullable=False, default="unidade")
    preco_unitario = db.Column(db.Float, nullable=False)
    valor_total = db.Column(db.Float, nullable=False)
    observacoes = db.Column(db.Text, nullable=True)
    
    # Relacionamento com material (se aplicável)
    material_id = db.Column(db.Integer, db.ForeignKey("material.id"), nullable=True)
    material = db.relationship("Material", backref=db.backref("itens_compra", lazy=True))
    
    # Relacionamento com compra
    compra_id = db.Column(db.Integer, db.ForeignKey("compra.id"), nullable=False)
    compra = db.relationship("Compra", back_populates="itens")
    
    # Controle
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ItemCompra {self.descricao} - {self.quantidade} {self.unidade}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'descricao': self.descricao,
            'quantidade': self.quantidade,
            'unidade': self.unidade,
            'preco_unitario': self.preco_unitario,
            'valor_total': self.valor_total,
            'observacoes': self.observacoes,
            'material_id': self.material_id,
            'material_nome': self.material.nome if self.material else None,
            'compra_id': self.compra_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class DocumentoFiscal(db.Model):
    """Modelo para representar documentos fiscais de uma compra."""
    __tablename__ = "documento_fiscal"
    
    id = db.Column(db.Integer, primary_key=True)
    tipo_documento = db.Column(db.String(50), nullable=False)  # nota_fiscal, cupom_fiscal, recibo, boleto, outros
    numero_documento = db.Column(db.String(100), nullable=True)
    serie_documento = db.Column(db.String(20), nullable=True)
    chave_acesso = db.Column(db.String(44), nullable=True)  # Para NFe
    
    # Arquivo
    nome_arquivo = db.Column(db.String(255), nullable=False)  # Nome original
    nome_arquivo_seguro = db.Column(db.String(255), nullable=True)  # Nome seguro gerado
    caminho_arquivo = db.Column(db.String(500), nullable=False)
    tamanho_arquivo = db.Column(db.Integer, nullable=True)  # em bytes
    tipo_mime = db.Column(db.String(100), nullable=True)
    hash_arquivo = db.Column(db.String(64), nullable=True)  # SHA-256 hash para integridade
    validacao_resultado = db.Column(db.Text, nullable=True)  # JSON com resultado da validação
    scan_seguranca = db.Column(db.Text, nullable=True)  # JSON com resultado do scan de segurança
    
    # Dados do documento
    data_emissao = db.Column(db.DateTime, nullable=True)
    valor_documento = db.Column(db.Float, nullable=True)
    
    # Observações
    observacoes = db.Column(db.Text, nullable=True)
    
    # Controle
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com compra
    compra_id = db.Column(db.Integer, db.ForeignKey("compra.id"), nullable=False)
    compra = db.relationship("Compra", back_populates="documentos")
    
    # Usuário que fez upload
    usuario_upload_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    usuario_upload = db.relationship("Usuario", backref=db.backref("documentos_upload", lazy=True))
    
    def __repr__(self):
        return f"<DocumentoFiscal {self.tipo_documento} - {self.numero_documento}>"
    
    @property
    def extensao_arquivo(self):
        """Retorna a extensão do arquivo."""
        if self.nome_arquivo:
            return self.nome_arquivo.split('.')[-1].lower()
        return None
    
    def to_dict(self):
        return {
            'id': self.id,
            'tipo_documento': self.tipo_documento,
            'numero_documento': self.numero_documento,
            'serie_documento': self.serie_documento,
            'chave_acesso': self.chave_acesso,
            'nome_arquivo': self.nome_arquivo,
            'nome_arquivo_seguro': self.nome_arquivo_seguro,
            'caminho_arquivo': self.caminho_arquivo,
            'tamanho_arquivo': self.tamanho_arquivo,
            'tipo_mime': self.tipo_mime,
            'hash_arquivo': self.hash_arquivo,
            'extensao_arquivo': self.extensao_arquivo,
            'data_emissao': self.data_emissao.isoformat() if self.data_emissao else None,
            'valor_documento': self.valor_documento,
            'observacoes': self.observacoes,
            'ativo': self.ativo,
            'compra_id': self.compra_id,
            'usuario_upload_id': self.usuario_upload_id,
            'validacao_resultado': self.validacao_resultado,
            'scan_seguranca': self.scan_seguranca,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class PrestacaoContas(db.Model):
    """Modelo para representar prestação de contas de compras."""
    __tablename__ = "prestacao_contas"
    
    id = db.Column(db.Integer, primary_key=True)
    numero_prestacao = db.Column(db.String(50), nullable=False, unique=True)
    titulo = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    
    # Período da prestação
    data_inicio = db.Column(db.DateTime, nullable=False)
    data_fim = db.Column(db.DateTime, nullable=False)
    
    # Valores consolidados
    valor_total_compras = db.Column(db.Float, nullable=False, default=0.0)
    valor_total_documentos = db.Column(db.Float, nullable=False, default=0.0)
    
    # Status
    status = db.Column(db.String(50), nullable=False, default='rascunho')  # rascunho, enviada, aprovada, rejeitada
    
    # Observações
    observacoes = db.Column(db.Text, nullable=True)
    observacoes_aprovacao = db.Column(db.Text, nullable=True)
    
    # Controle
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    data_envio = db.Column(db.DateTime, nullable=True)
    data_aprovacao = db.Column(db.DateTime, nullable=True)
    
    # Relacionamentos
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    cliente = db.relationship("Cliente", backref=db.backref("prestacoes_contas", lazy=True))
    
    # Usuário responsável
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    usuario = db.relationship(
        "Usuario",
        foreign_keys=[usuario_id],
        backref=db.backref("prestacoes_contas", lazy=True),
    )
    
    # Usuário que aprovou
    usuario_aprovacao_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    usuario_aprovacao = db.relationship("Usuario", foreign_keys=[usuario_aprovacao_id], backref=db.backref("prestacoes_aprovadas", lazy=True))
    
    # Relacionamento com compras
    compras = db.relationship("Compra", secondary="prestacao_compra", backref=db.backref("prestacoes_contas", lazy=True))
    
    def __repr__(self):
        return f"<PrestacaoContas {self.numero_prestacao} - {self.titulo}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'numero_prestacao': self.numero_prestacao,
            'titulo': self.titulo,
            'descricao': self.descricao,
            'data_inicio': self.data_inicio.isoformat() if self.data_inicio else None,
            'data_fim': self.data_fim.isoformat() if self.data_fim else None,
            'valor_total_compras': self.valor_total_compras,
            'valor_total_documentos': self.valor_total_documentos,
            'status': self.status,
            'observacoes': self.observacoes,
            'observacoes_aprovacao': self.observacoes_aprovacao,
            'ativo': self.ativo,
            'cliente_id': self.cliente_id,
            'usuario_id': self.usuario_id,
            'usuario_aprovacao_id': self.usuario_aprovacao_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'data_envio': self.data_envio.isoformat() if self.data_envio else None,
            'data_aprovacao': self.data_aprovacao.isoformat() if self.data_aprovacao else None,
            'total_compras': len(self.compras) if self.compras else 0
        }


# Tabela de associação para prestação de contas e compras
prestacao_compra = db.Table('prestacao_compra',
    db.Column('prestacao_id', db.Integer, db.ForeignKey('prestacao_contas.id'), primary_key=True),
    db.Column('compra_id', db.Integer, db.ForeignKey('compra.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)


class RelatorioCompra(db.Model):
    """Modelo para representar relatórios de compras personalizados."""
    __tablename__ = "relatorio_compra"
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    
    # Filtros do relatório (JSON)
    filtros = db.Column(db.Text, nullable=True)  # JSON com os filtros aplicados
    
    # Configurações de exibição
    campos_exibir = db.Column(db.Text, nullable=True)  # JSON com campos a exibir
    ordenacao = db.Column(db.String(100), nullable=True)  # campo de ordenação
    ordem_crescente = db.Column(db.Boolean, default=True)
    
    # Controle
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    publico = db.Column(db.Boolean, default=False)  # Se pode ser usado por outros usuários
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    cliente = db.relationship("Cliente", backref=db.backref("relatorios_compra", lazy=True))
    
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    usuario = db.relationship("Usuario", backref=db.backref("relatorios_compra", lazy=True))
    
    def __repr__(self):
        return f"<RelatorioCompra {self.nome}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'filtros': self.filtros,
            'campos_exibir': self.campos_exibir,
            'ordenacao': self.ordenacao,
            'ordem_crescente': self.ordem_crescente,
            'ativo': self.ativo,
            'publico': self.publico,
            'cliente_id': self.cliente_id,
            'usuario_id': self.usuario_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
