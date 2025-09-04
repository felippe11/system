from extensions import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON


class CertificadoConfig(db.Model):
    """Configurações de certificados para eventos."""
    __tablename__ = "certificado_config"
    
    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    
    # Configurações básicas
    liberacao_automatica = db.Column(db.Boolean, default=True)
    permitir_solicitacao_manual = db.Column(db.Boolean, default=False)
    notificar_participantes = db.Column(db.Boolean, default=True)
    
    # Critérios de liberação
    carga_horaria_minima = db.Column(db.Integer, default=0)
    percentual_presenca_minimo = db.Column(db.Float, default=0.0)
    checkins_minimos = db.Column(db.Integer, default=0)
    validar_oficinas_obrigatorias = db.Column(db.Boolean, default=False)
    oficinas_participadas_minimas = db.Column(db.Integer, default=0)
    exigir_atividades_obrigatorias = db.Column(db.Boolean, default=False)
    
    # Configurações de aprovação
    exigir_aprovacao_manual = db.Column(db.Boolean, default=False)
    aprovacao_automatica_se_criterios = db.Column(db.Boolean, default=True)
    
    # Prazos
    prazo_liberacao_automatica = db.Column(db.DateTime, nullable=True)
    prazo_solicitacao_manual = db.Column(db.DateTime, nullable=True)
    
    # Relacionamentos
    evento = db.relationship("Evento", backref="certificado_config")
    cliente = db.relationship("Cliente", backref="certificado_configs")
    
    def __repr__(self):
        return f'<CertificadoConfig {self.evento_id}>'


class CertificadoParticipante(db.Model):
    """Certificados emitidos para participantes."""
    __tablename__ = "certificado_participante"
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    oficina_id = db.Column(db.Integer, db.ForeignKey("oficina.id"), nullable=True)
    
    # Tipo e status
    tipo = db.Column(db.String(20), nullable=False)  # 'geral', 'individual'
    liberado = db.Column(db.Boolean, default=False)
    
    # Dados do certificado
    titulo = db.Column(db.String(200), nullable=False)
    carga_horaria = db.Column(db.Integer, nullable=False)
    data_emissao = db.Column(db.DateTime, default=datetime.utcnow)
    data_liberacao = db.Column(db.DateTime, nullable=True)
    
    # Arquivo e validação
    arquivo_path = db.Column(db.String(500), nullable=True)
    hash_verificacao = db.Column(db.String(64), nullable=True)
    
    # Relacionamentos
    usuario = db.relationship("Usuario", backref="certificados")
    evento = db.relationship("Evento", backref="certificados_participantes")
    oficina = db.relationship("Oficina", backref="certificados_oficina")
    
    def __repr__(self):
        return f'<CertificadoParticipante {self.usuario_id}-{self.evento_id}>'


class NotificacaoCertificado(db.Model):
    """Notificações relacionadas a certificados."""
    __tablename__ = "notificacao_certificado"
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    
    # Conteúdo da notificação
    tipo = db.Column(db.String(50), nullable=False)  # 'liberacao', 'aprovacao', 'rejeicao'
    titulo = db.Column(db.String(200), nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    
    # Status
    lida = db.Column(db.Boolean, default=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_leitura = db.Column(db.DateTime, nullable=True)
    
    # Relacionamentos
    usuario = db.relationship("Usuario", backref="notificacoes_certificado")
    evento = db.relationship("Evento", backref="notificacoes_certificado")
    
    def __repr__(self):
        return f'<NotificacaoCertificado {self.tipo}-{self.usuario_id}>'


class SolicitacaoCertificado(db.Model):
    """Solicitações de certificados para aprovação manual."""
    __tablename__ = "solicitacao_certificado"
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    oficina_id = db.Column(db.Integer, db.ForeignKey("oficina.id"), nullable=True)
    
    # Dados da solicitação
    tipo_certificado = db.Column(db.String(20), nullable=False)  # 'geral', 'individual'
    justificativa = db.Column(db.Text, nullable=True)
    dados_participacao = db.Column(JSON, nullable=True)
    
    # Status e datas
    status = db.Column(db.String(20), default='pendente')  # 'pendente', 'aprovada', 'rejeitada'
    data_solicitacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_resposta = db.Column(db.DateTime, nullable=True)
    
    # Aprovação
    aprovado_por = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    observacoes_aprovacao = db.Column(db.Text, nullable=True)
    
    # Relacionamentos
    usuario = db.relationship("Usuario", foreign_keys=[usuario_id], backref="solicitacoes_certificado")
    evento = db.relationship("Evento", backref="solicitacoes_certificado")
    oficina = db.relationship("Oficina", backref="solicitacoes_certificado")
    aprovador = db.relationship("Usuario", foreign_keys=[aprovado_por])
    
    def __repr__(self):
        return f'<SolicitacaoCertificado {self.usuario_id}-{self.evento_id}-{self.status}>'


class RegraCertificado(db.Model):
    """Regras avançadas para liberação de certificados."""
    __tablename__ = "regra_certificado"
    
    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    
    # Identificação da regra
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    ativa = db.Column(db.Boolean, default=True)
    prioridade = db.Column(db.Integer, default=0)
    
    # Condições
    condicoes = db.Column(JSON, nullable=False)  # Estrutura JSON com as condições
    
    # Ações
    acoes = db.Column(JSON, nullable=False)  # Estrutura JSON com as ações
    
    # Datas
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    evento = db.relationship("Evento", backref="regras_certificado")
    cliente = db.relationship("Cliente", backref="regras_certificado")
    
    def __repr__(self):
        return f'<RegraCertificado {self.nome}-{self.evento_id}>'


class CertificadoTemplateAvancado(db.Model):
    """Templates avançados para certificados."""
    __tablename__ = "certificado_template_avancado"
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    
    # Identificação
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    tipo = db.Column(db.String(20), nullable=False)  # 'geral', 'individual'
    
    # Template
    conteudo_html = db.Column(db.Text, nullable=False)
    variaveis_disponiveis = db.Column(JSON, nullable=True)
    
    # Status
    ativo = db.Column(db.Boolean, default=True)
    padrao = db.Column(db.Boolean, default=False)
    
    # Datas
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    cliente = db.relationship("Cliente", backref="templates_certificado_avancado")
    
    def __repr__(self):
        return f'<CertificadoTemplateAvancado {self.nome}>'


class DeclaracaoTemplate(db.Model):
    """Templates para declarações de comparecimento."""
    __tablename__ = "declaracao_template"
    __table_args__ = (
        db.UniqueConstraint(
            "cliente_id",
            "nome",
            name="uq_declaracao_template_cliente_nome",
        ),
        {"extend_existing": True},
    )
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    
    # Identificação
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'individual', 'coletiva'
    
    # Conteúdo
    conteudo = db.Column(db.Text, nullable=False)
    
    # Status
    ativo = db.Column(db.Boolean, default=True)
    
    # Datas
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    cliente = db.relationship("Cliente", backref="templates_declaracao")
    
    def __repr__(self):
        return f'<DeclaracaoTemplate {self.nome}>'


class VariavelDinamica(db.Model):
    """Variáveis dinâmicas para templates de certificados e declarações."""
    __tablename__ = "variavel_dinamica"
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    
    # Identificação
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    tipo = db.Column(db.String(20), nullable=False)  # 'texto', 'numero', 'data', 'booleano'
    
    # Configurações
    valor_padrao = db.Column(db.Text, nullable=True)
    obrigatoria = db.Column(db.Boolean, default=False)
    formato = db.Column(db.String(100), nullable=True)  # Para datas, números, etc.
    
    # Status
    ativa = db.Column(db.Boolean, default=True)
    
    # Datas
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    cliente = db.relationship("Cliente", backref="variaveis_dinamicas")
    
    def __repr__(self):
        return f'<VariavelDinamica {self.nome}>'


class AcessoValidacaoCertificado(db.Model):
    """Registros de acessos para validação de certificados."""
    __tablename__ = "acesso_validacao_certificado"
    
    id = db.Column(db.Integer, primary_key=True)
    certificado_id = db.Column(db.Integer, db.ForeignKey("certificado_participante.id"), nullable=False)
    
    # Dados do acesso
    data_acesso = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ip_acesso = db.Column(db.String(45))  # IPv4 ou IPv6
    user_agent = db.Column(db.Text)
    
    # Relacionamentos
    certificado = db.relationship("CertificadoParticipante", backref="acessos_validacao")
    
    def __repr__(self):
        return f'<AcessoValidacaoCertificado {self.certificado_id}-{self.data_acesso}>'