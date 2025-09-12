from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

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

class ConfiguracaoRelatorio(Base):
    """Configuração de relatórios definida pelo cliente"""
    __tablename__ = 'configuracao_relatorio'
    
    id = Column(Integer, primary_key=True)
    nome = Column(String(200), nullable=False)
    descricao = Column(Text)
    tipo = Column(Enum(TipoRelatorio), nullable=False)
    ativo = Column(Boolean, default=True)
    obrigatorio = Column(Boolean, default=False)
    frequencia_dias = Column(Integer)  # Para relatórios periódicos
    cliente_id = Column(Integer, ForeignKey('cliente.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    cliente = relationship("Cliente", back_populates="configuracoes_relatorio")
    campos = relationship("CampoRelatorio", back_populates="configuracao", cascade="all, delete-orphan")
    relatorios = relationship("RelatorioFormador", back_populates="configuracao")
    
    def __repr__(self):
        return f'<ConfiguracaoRelatorio {self.nome}>'

class CampoRelatorio(Base):
    """Campos configuráveis para relatórios"""
    __tablename__ = 'campo_relatorio'
    
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    label = Column(String(200), nullable=False)
    tipo = Column(Enum(TipoCampo), nullable=False)
    obrigatorio = Column(Boolean, default=False)
    ordem = Column(Integer, default=0)
    opcoes = Column(Text)  # JSON para opções de seleção
    placeholder = Column(String(200))
    validacao = Column(Text)  # Regras de validação em JSON
    configuracao_id = Column(Integer, ForeignKey('configuracao_relatorio.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    configuracao = relationship("ConfiguracaoRelatorio", back_populates="campos")
    respostas = relationship("RespostaCampo", back_populates="campo")
    
    def __repr__(self):
        return f'<CampoRelatorio {self.label}>'

class RelatorioFormador(Base):
    """Relatórios preenchidos pelos formadores"""
    __tablename__ = 'relatorio_formador'
    
    id = Column(Integer, primary_key=True)
    formador_id = Column(Integer, ForeignKey('ministrante.id'), nullable=False)
    configuracao_id = Column(Integer, ForeignKey('configuracao_relatorio.id'), nullable=False)
    atividade_id = Column(Integer, ForeignKey('atividade.id'), nullable=True)  # Para relatórios por atividade
    periodo_inicio = Column(DateTime)  # Para relatórios periódicos
    periodo_fim = Column(DateTime)
    status = Column(String(20), default='rascunho')  # rascunho, enviado, aprovado
    observacoes_cliente = Column(Text)
    data_envio = Column(DateTime)
    data_aprovacao = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    formador = relationship("Ministrante", back_populates="relatorios")
    configuracao = relationship("ConfiguracaoRelatorio", back_populates="relatorios")
    atividade = relationship("Atividade", back_populates="relatorios_formador")
    respostas = relationship("RespostaCampo", back_populates="relatorio", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<RelatorioFormador {self.id} - {self.configuracao.nome}>'

class RespostaCampo(Base):
    """Respostas dos formadores para cada campo do relatório"""
    __tablename__ = 'resposta_campo'
    
    id = Column(Integer, primary_key=True)
    relatorio_id = Column(Integer, ForeignKey('relatorio_formador.id'), nullable=False)
    campo_id = Column(Integer, ForeignKey('campo_relatorio.id'), nullable=False)
    valor = Column(Text)  # Valor da resposta
    arquivo_path = Column(String(500))  # Para campos de arquivo
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    relatorio = relationship("RelatorioFormador", back_populates="respostas")
    campo = relationship("CampoRelatorio", back_populates="respostas")
    
    def __repr__(self):
        return f'<RespostaCampo {self.campo.label}: {self.valor[:50]}>'

class HistoricoRelatorio(Base):
    """Histórico de alterações nos relatórios"""
    __tablename__ = 'historico_relatorio'
    
    id = Column(Integer, primary_key=True)
    relatorio_id = Column(Integer, ForeignKey('relatorio_formador.id'), nullable=False)
    usuario_id = Column(Integer, nullable=False)  # ID do usuário que fez a alteração
    usuario_tipo = Column(String(20), nullable=False)  # formador, cliente, monitor
    acao = Column(String(50), nullable=False)  # criado, editado, enviado, aprovado, rejeitado
    detalhes = Column(Text)  # Detalhes da alteração
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    relatorio = relationship("RelatorioFormador")
    
    def __repr__(self):
        return f'<HistoricoRelatorio {self.acao} - {self.created_at}>'