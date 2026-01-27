from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from extensions import db
import enum


class TipoLembrete(enum.Enum):
    MANUAL = "manual"
    AUTOMATICO = "automatico"


class StatusLembrete(enum.Enum):
    PENDENTE = "pendente"
    ENVIADO = "enviado"
    FALHOU = "falhou"
    CANCELADO = "cancelado"


class LembreteOficina(db.Model):
    """Modelo para lembretes de oficinas."""
    __tablename__ = "lembrete_oficina"
    
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=False)
    titulo = Column(String(200), nullable=False)
    mensagem = Column(Text, nullable=False)
    tipo = Column(Enum(TipoLembrete), nullable=False, default=TipoLembrete.MANUAL)
    status = Column(Enum(StatusLembrete), nullable=False, default=StatusLembrete.PENDENTE)
    
    # Configurações para lembretes automáticos
    dias_antecedencia = Column(Integer, nullable=True)  # Dias antes da oficina
    data_envio_agendada = Column(DateTime, nullable=True)  # Data/hora específica para envio
    
    # Filtros de destinatários
    enviar_todas_oficinas = Column(Boolean, default=False)
    oficina_ids = Column(Text, nullable=True)  # JSON com IDs das oficinas selecionadas
    usuario_ids = Column(Text, nullable=True)  # JSON com IDs dos usuários específicos
    
    # Controle de envio
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_envio = Column(DateTime, nullable=True)
    total_destinatarios = Column(Integer, default=0)
    total_enviados = Column(Integer, default=0)
    total_falhas = Column(Integer, default=0)
    
    # Relacionamentos
    cliente = relationship("Cliente", back_populates="lembretes_oficinas")
    envios = relationship("LembreteEnvio", back_populates="lembrete", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<LembreteOficina {self.titulo}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'titulo': self.titulo,
            'mensagem': self.mensagem,
            'tipo': self.tipo.value,
            'status': self.status.value,
            'dias_antecedencia': self.dias_antecedencia,
            'data_envio_agendada': self.data_envio_agendada.isoformat() if self.data_envio_agendada else None,
            'enviar_todas_oficinas': self.enviar_todas_oficinas,
            'oficina_ids': self.oficina_ids,
            'usuario_ids': self.usuario_ids,
            'data_criacao': self.data_criacao.isoformat(),
            'data_envio': self.data_envio.isoformat() if self.data_envio else None,
            'total_destinatarios': self.total_destinatarios,
            'total_enviados': self.total_enviados,
            'total_falhas': self.total_falhas
        }


class LembreteEnvio(db.Model):
    """Modelo para controle de envios individuais de lembretes."""
    __tablename__ = "lembrete_envio"
    
    id = Column(Integer, primary_key=True)
    lembrete_id = Column(Integer, ForeignKey("lembrete_oficina.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    oficina_id = Column(Integer, ForeignKey("oficina.id"), nullable=False)
    
    status = Column(Enum(StatusLembrete), nullable=False, default=StatusLembrete.PENDENTE)
    data_envio = Column(DateTime, nullable=True)
    erro_mensagem = Column(Text, nullable=True)
    
    # Relacionamentos
    lembrete = relationship("LembreteOficina", back_populates="envios")
    usuario = relationship("Usuario")
    oficina = relationship("Oficina")
    
    def __repr__(self):
        return f"<LembreteEnvio {self.usuario.email} - {self.oficina.titulo}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'lembrete_id': self.lembrete_id,
            'usuario_id': self.usuario_id,
            'oficina_id': self.oficina_id,
            'status': self.status.value,
            'data_envio': self.data_envio.isoformat() if self.data_envio else None,
            'erro_mensagem': self.erro_mensagem,
            'usuario_nome': self.usuario.nome if self.usuario else None,
            'usuario_email': self.usuario.email if self.usuario else None,
            'oficina_titulo': self.oficina.titulo if self.oficina else None
        }
