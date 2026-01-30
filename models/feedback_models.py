"""
Modelos para sistema de feedback personalizado com perguntas definidas pelo cliente.
"""

from extensions import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum


class TipoPergunta(enum.Enum):
    """Tipos de perguntas disponíveis para feedback."""
    TEXTO_LIVRE = "texto_livre"
    MULTIPLA_ESCOLHA = "multipla_escolha"
    ESCALA_NUMERICA = "escala_numerica"
    SIM_NAO = "sim_nao"


class FeedbackTemplate(db.Model):
    """Modelo para templates de feedback."""
    __tablename__ = "feedback_templates"

    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=False)
    nome = Column(String(120), nullable=False)
    descricao = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cliente = relationship("Cliente", backref="feedback_templates")
    perguntas = relationship(
        "PerguntaFeedback",
        backref="template",
        primaryjoin="FeedbackTemplate.id==PerguntaFeedback.template_id",
    )

    def __repr__(self):
        return f"<FeedbackTemplate {self.nome}>"


class FeedbackTemplateOficina(db.Model):
    """Vincula um template a uma oficina."""
    __tablename__ = "feedback_template_oficina"

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("feedback_templates.id"), nullable=False)
    oficina_id = Column(Integer, ForeignKey("oficina.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    template = relationship("FeedbackTemplate", backref="oficinas_vinculadas")
    oficina = relationship("Oficina", backref="feedback_template_vinculo")

    def __repr__(self):
        return f"<FeedbackTemplateOficina template={self.template_id} oficina={self.oficina_id}>"


class PerguntaFeedback(db.Model):
    """Modelo para perguntas personalizadas de feedback definidas pelo cliente."""
    __tablename__ = 'perguntas_feedback'
    
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('cliente.id'), nullable=False)
    oficina_id = Column(Integer, ForeignKey('oficina.id'), nullable=True)  # Se None, aplica a todas as oficinas
    template_id = Column(Integer, ForeignKey("feedback_templates.id"), nullable=True)
    atividade_id = Column(Integer, nullable=True)  # ID opcional para vincular a uma atividade específica
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    tipo = Column(Enum(TipoPergunta), nullable=False, default=TipoPergunta.TEXTO_LIVRE)
    opcoes = Column(Text, nullable=True)  # JSON string para opções de múltipla escolha
    obrigatoria = Column(Boolean, default=True)
    ordem = Column(Integer, default=0)
    ativa = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    cliente = relationship("Cliente", backref="perguntas_feedback")
    oficina = relationship("Oficina", backref="perguntas_feedback")
    respostas = relationship("RespostaFeedback", back_populates="pergunta")
    
    def __repr__(self):
        return f'<PerguntaFeedback {self.titulo}>'
    
    def to_dict(self):
        """Converte o objeto para dicionário."""
        return {
            'id': self.id,
            'template_id': self.template_id,
            'titulo': self.titulo,
            'descricao': self.descricao,
            'tipo': self.tipo.value,
            'opcoes': self.opcoes,
            'obrigatoria': self.obrigatoria,
            'ordem': self.ordem,
            'ativa': self.ativa
        }


class RespostaFeedback(db.Model):
    """Modelo para respostas de feedback dos usuários."""
    __tablename__ = 'respostas_feedback'
    
    id = Column(Integer, primary_key=True)
    pergunta_id = Column(Integer, ForeignKey('perguntas_feedback.id'), nullable=False)
    usuario_id = Column(Integer, ForeignKey('usuario.id'), nullable=True)
    oficina_id = Column(Integer, ForeignKey('oficina.id'), nullable=False)
    resposta_texto = Column(Text, nullable=True)
    resposta_numerica = Column(Integer, nullable=True)
    resposta_escolha = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    pergunta = relationship("PerguntaFeedback", back_populates="respostas")
    usuario = relationship("Usuario", backref="respostas_feedback")
    oficina = relationship("Oficina", backref="respostas_feedback")
    
    def __repr__(self):
        return f'<RespostaFeedback {self.pergunta.titulo}: {self.resposta_texto or self.resposta_numerica or self.resposta_escolha}>'
    
    def to_dict(self):
        """Converte o objeto para dicionário."""
        return {
            'id': self.id,
            'pergunta_id': self.pergunta_id,
            'usuario_id': self.usuario_id,
            'oficina_id': self.oficina_id,
            'resposta_texto': self.resposta_texto,
            'resposta_numerica': self.resposta_numerica,
            'resposta_escolha': self.resposta_escolha,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class FeedbackSession(db.Model):
    """Modelo para controlar sessões de feedback via QR Code."""
    __tablename__ = 'feedback_sessions'
    
    id = Column(Integer, primary_key=True)
    token = Column(String(255), unique=True, nullable=False)
    usuario_id = Column(Integer, ForeignKey('usuario.id'), nullable=False)
    oficina_id = Column(Integer, ForeignKey('oficina.id'), nullable=False)
    ativa = Column(Boolean, default=True)
    respondida = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Relacionamentos
    usuario = relationship("Usuario", backref="feedback_sessions")
    oficina = relationship("Oficina", backref="feedback_sessions")
    
    def __repr__(self):
        return f'<FeedbackSession {self.token}>'
    
    def is_valid(self):
        """Verifica se a sessão ainda é válida."""
        if not self.ativa or self.respondida:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
