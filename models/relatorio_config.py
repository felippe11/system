from datetime import datetime
import enum
from extensions import db

class TipoRelatorio(enum.Enum):
    ATIVIDADE = "atividade"
    MENSAL = "mensal"
    TRIMESTRAL = "trimestral"
    ANUAL = "anual"

class TipoCampo(enum.Enum):
    TEXTO = "texto"
    NUMERO = "numero"
    DATA = "data"
    SELECAO = "selecao"
    MULTIPLA_ESCOLHA = "multipla_escolha"
    ARQUIVO = "arquivo"
    TEXTO_LONGO = "texto_longo"

class ConfiguracaoRelatorio(db.Model):
    """Configuração de relatórios definida pelo cliente"""
    __tablename__ = 'configuracao_relatorio'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    tipo = db.Column(db.Enum(TipoRelatorio), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    obrigatorio = db.Column(db.Boolean, default=False)
    frequencia_dias = db.Column(db.Integer)  # Para relatórios periódicos
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    cliente = db.relationship("Cliente", backref="configuracoes_relatorio")
    campos = db.relationship("CampoRelatorio", back_populates="configuracao", cascade="all, delete-orphan")
    relatorios = db.relationship("RelatorioFormador", back_populates="configuracao")
    
    def __repr__(self):
        return f'<ConfiguracaoRelatorio {self.nome}>'

class CampoRelatorio(db.Model):
    """Campos configuráveis para relatórios"""
    __tablename__ = 'campo_relatorio'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    label = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.Enum(TipoCampo), nullable=False)
    obrigatorio = db.Column(db.Boolean, default=False)
    ordem = db.Column(db.Integer, default=0)
    opcoes = db.Column(db.Text)  # JSON para opções de seleção
    placeholder = db.Column(db.String(200))
    validacao = db.Column(db.Text)  # Regras de validação em JSON
    configuracao_id = db.Column(db.Integer, db.ForeignKey('configuracao_relatorio.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    configuracao = db.relationship("ConfiguracaoRelatorio", back_populates="campos")
    respostas = db.relationship("RespostaCampo", back_populates="campo")
    
    def __repr__(self):
        return f'<CampoRelatorio {self.label}>'

class RelatorioFormador(db.Model):
    """Relatórios preenchidos pelos formadores"""
    __tablename__ = 'relatorio_formador'
    
    id = db.Column(db.Integer, primary_key=True)
    formador_id = db.Column(db.Integer, db.ForeignKey('ministrante.id'), nullable=False)
    configuracao_id = db.Column(db.Integer, db.ForeignKey('configuracao_relatorio.id'), nullable=False)
    oficina_id = db.Column(db.Integer, db.ForeignKey('oficina.id'), nullable=True)  # Para relatórios por oficina
    periodo_inicio = db.Column(db.DateTime)  # Para relatórios periódicos
    periodo_fim = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='rascunho')  # rascunho, enviado, aprovado
    observacoes_cliente = db.Column(db.Text)
    data_envio = db.Column(db.DateTime)
    data_aprovacao = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    formador = db.relationship("Ministrante", backref="relatorios")
    configuracao = db.relationship("ConfiguracaoRelatorio", back_populates="relatorios")
    oficina = db.relationship("Oficina", backref="relatorios_formador")
    respostas = db.relationship("RespostaCampo", back_populates="relatorio", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<RelatorioFormador {self.id} - {self.configuracao.nome}>'

class RespostaCampo(db.Model):
    """Respostas dos formadores para cada campo do relatório"""
    __tablename__ = 'resposta_campo'
    
    id = db.Column(db.Integer, primary_key=True)
    relatorio_id = db.Column(db.Integer, db.ForeignKey('relatorio_formador.id'), nullable=False)
    campo_id = db.Column(db.Integer, db.ForeignKey('campo_relatorio.id'), nullable=False)
    valor = db.Column(db.Text)  # Valor da resposta
    arquivo_path = db.Column(db.String(500))  # Para campos de arquivo
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    relatorio = db.relationship("RelatorioFormador", back_populates="respostas")
    campo = db.relationship("CampoRelatorio", back_populates="respostas")
    
    def __repr__(self):
        return f'<RespostaCampo {self.campo.label}: {self.valor[:50]}>'

class HistoricoRelatorio(db.Model):
    """Histórico de alterações nos relatórios"""
    __tablename__ = 'historico_relatorio'
    
    id = db.Column(db.Integer, primary_key=True)
    relatorio_id = db.Column(db.Integer, db.ForeignKey('relatorio_formador.id'), nullable=False)
    usuario_id = db.Column(db.Integer, nullable=False)  # ID do usuário que fez a alteração
    usuario_tipo = db.Column(db.String(20), nullable=False)  # formador, cliente, monitor
    acao = db.Column(db.String(50), nullable=False)  # criado, editado, enviado, aprovado, rejeitado
    detalhes = db.Column(db.Text)  # Detalhes da alteração
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    relatorio = db.relationship("RelatorioFormador")
    
    def __repr__(self):
        return f'<HistoricoRelatorio {self.acao} - {self.created_at}>'