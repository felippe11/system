"""Modelos para o sistema de feedback aberto diario (isolado)."""

from datetime import datetime
import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Date,
    Enum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from extensions import db


class TipoPerguntaFeedbackAberto(enum.Enum):
    """Tipos de perguntas disponiveis para feedback aberto."""

    TEXTO_LIVRE = "texto_livre"
    MULTIPLA_ESCOLHA = "multipla_escolha"
    MULTIPLA_ESCOLHA_MULTIPLA = "multipla_escolha_multipla"
    ESCALA_NUMERICA = "escala_numerica"
    SIM_NAO = "sim_nao"
    EMAIL = "email"
    TELEFONE = "telefone"
    DATA = "data"
    NUMERO = "numero"


class FeedbackAbertoPergunta(db.Model):
    """Perguntas configuraveis para o feedback aberto diario."""

    __tablename__ = "feedback_aberto_perguntas"

    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=False)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    tipo = Column(Enum(TipoPerguntaFeedbackAberto), nullable=False)
    opcoes = Column(Text, nullable=True)  # JSON string
    obrigatoria = Column(Boolean, default=True)
    ordem = Column(Integer, default=0)
    ativa = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cliente = relationship("Cliente", backref="feedback_aberto_perguntas")

    def __repr__(self):
        return f"<FeedbackAbertoPergunta {self.titulo}>"


class FeedbackAbertoDia(db.Model):
    """Link diario de feedback aberto."""

    __tablename__ = "feedback_aberto_dias"
    __table_args__ = (
        UniqueConstraint("cliente_id", "data", name="uq_feedback_aberto_cliente_data"),
    )

    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=False)
    data = Column(Date, nullable=False)
    titulo = Column(String(255), nullable=True)
    token = Column(String(64), unique=True, nullable=False)
    ativa = Column(Boolean, default=True)
    exigir_nome = Column(Boolean, default=False)
    exigir_email = Column(Boolean, default=False)
    exigir_telefone = Column(Boolean, default=False)
    exigir_identificador = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cliente = relationship("Cliente", backref="feedback_aberto_dias")
    perguntas = relationship(
        "FeedbackAbertoDiaPergunta",
        back_populates="dia",
        cascade="all, delete-orphan",
    )
    envios = relationship(
        "FeedbackAbertoEnvio",
        back_populates="dia",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<FeedbackAbertoDia {self.data.isoformat()}>"


class FeedbackAbertoDiaPergunta(db.Model):
    """Vinculo entre o dia e as perguntas do feedback aberto."""

    __tablename__ = "feedback_aberto_dia_perguntas"
    __table_args__ = (
        UniqueConstraint(
            "dia_id",
            "pergunta_id",
            name="uq_feedback_aberto_dia_pergunta",
        ),
    )

    id = Column(Integer, primary_key=True)
    dia_id = Column(Integer, ForeignKey("feedback_aberto_dias.id"), nullable=False)
    pergunta_id = Column(
        Integer,
        ForeignKey("feedback_aberto_perguntas.id"),
        nullable=False,
    )
    ordem = Column(Integer, default=0)

    dia = relationship("FeedbackAbertoDia", back_populates="perguntas")
    pergunta = relationship("FeedbackAbertoPergunta", backref="dias_vinculados")


class FeedbackAbertoEnvio(db.Model):
    """Registro de cada envio do formulario aberto."""

    __tablename__ = "feedback_aberto_envios"

    id = Column(Integer, primary_key=True)
    dia_id = Column(Integer, ForeignKey("feedback_aberto_dias.id"), nullable=False)
    nome = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    telefone = Column(String(64), nullable=True)
    identificador = Column(String(120), nullable=True)
    ip_origem = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    dia = relationship("FeedbackAbertoDia", back_populates="envios")
    respostas = relationship(
        "FeedbackAbertoResposta",
        back_populates="envio",
        cascade="all, delete-orphan",
    )


class FeedbackAbertoResposta(db.Model):
    """Respostas do feedback aberto diario."""

    __tablename__ = "feedback_aberto_respostas"

    id = Column(Integer, primary_key=True)
    envio_id = Column(
        Integer,
        ForeignKey("feedback_aberto_envios.id"),
        nullable=False,
    )
    pergunta_id = Column(
        Integer,
        ForeignKey("feedback_aberto_perguntas.id"),
        nullable=False,
    )
    resposta_texto = Column(Text, nullable=True)
    resposta_numerica = Column(Integer, nullable=True)
    resposta_escolha = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    envio = relationship("FeedbackAbertoEnvio", back_populates="respostas")
    pergunta = relationship("FeedbackAbertoPergunta", backref="respostas_abertas")
