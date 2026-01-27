"""
Modelos para atividades com múltiplas datas e listas de frequência
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Time, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from extensions import db


class AtividadeMultiplaData(db.Model):
    """Modelo para atividades que ocorrem em múltiplas datas"""
    __tablename__ = 'atividade_multipla_data'
    
    id = Column(Integer, primary_key=True)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    carga_horaria_total = Column(String(10), nullable=False)  # Carga horária total da atividade
    tipo_atividade = Column(String(50), nullable=False, default='oficina')  # oficina, palestra, workshop, etc.
    
    # Relacionamentos
    cliente_id = Column(Integer, ForeignKey('cliente.id'), nullable=False)
    evento_id = Column(Integer, ForeignKey('evento.id'), nullable=True)
    
    # Configurações
    permitir_checkin_multiplas_datas = Column(Boolean, default=True)
    gerar_lista_frequencia = Column(Boolean, default=True)
    exigir_presenca_todas_datas = Column(Boolean, default=False)  # Se True, deve estar presente em todas as datas para receber certificado
    
    # Campos de localização
    estado = Column(String(2), nullable=False)
    cidade = Column(String(100), nullable=False)
    
    # Status
    ativa = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    cliente = relationship("Cliente", backref="atividades_multiplas_data")
    evento = relationship("Evento", backref="atividades_multiplas_data")
    datas = relationship("AtividadeData", back_populates="atividade", cascade="all, delete-orphan")
    frequencias = relationship("FrequenciaAtividade", back_populates="atividade", cascade="all, delete-orphan")
    checkins = relationship("CheckinAtividade", back_populates="atividade", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<AtividadeMultiplaData {self.titulo}>'
    
    def get_total_datas(self):
        """Retorna o número total de datas da atividade"""
        return len(self.datas)
    
    def get_datas_ordenadas(self):
        """Retorna as datas ordenadas cronologicamente"""
        return sorted(self.datas, key=lambda x: x.data)
    
    def get_carga_horaria_por_data(self):
        """Retorna a carga horária por data (total dividido pelo número de datas)"""
        if not self.datas:
            return 0
        try:
            carga_total = float(self.carga_horaria_total)
            return carga_total / len(self.datas)
        except (ValueError, ZeroDivisionError):
            return 0


class AtividadeData(db.Model):
    """Modelo para datas específicas de uma atividade"""
    __tablename__ = 'atividade_data'
    
    id = Column(Integer, primary_key=True)
    atividade_id = Column(Integer, ForeignKey('atividade_multipla_data.id'), nullable=False)
    data = Column(Date, nullable=False)
    horario_inicio = Column(Time, nullable=False)
    horario_fim = Column(Time, nullable=False)
    
    # Palavras-chave para checkin (manhã e tarde)
    palavra_chave_manha = Column(String(50), nullable=True)
    palavra_chave_tarde = Column(String(50), nullable=True)
    
    # Configurações específicas da data
    carga_horaria_data = Column(String(10), nullable=True)  # Se não especificado, usa a divisão automática
    observacoes = Column(Text, nullable=True)
    
    # Status
    ativa = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    atividade = relationship("AtividadeMultiplaData", back_populates="datas")
    frequencias = relationship("FrequenciaAtividade", back_populates="data_atividade", cascade="all, delete-orphan")
    checkins = relationship("CheckinAtividade", back_populates="data_atividade", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<AtividadeData {self.data} {self.horario_inicio}-{self.horario_fim}>'
    
    def get_carga_horaria(self):
        """Retorna a carga horária desta data específica"""
        if self.carga_horaria_data:
            try:
                return float(self.carga_horaria_data)
            except ValueError:
                pass
        
        # Se não especificado, usa a divisão automática da atividade
        return self.atividade.get_carga_horaria_por_data()
    
    def get_turno_manha(self):
        """Retorna se esta data tem turno da manhã"""
        return self.palavra_chave_manha is not None
    
    def get_turno_tarde(self):
        """Retorna se esta data tem turno da tarde"""
        return self.palavra_chave_tarde is not None


class FrequenciaAtividade(db.Model):
    """Modelo para listas de frequência de atividades"""
    __tablename__ = 'frequencia_atividade'
    
    id = Column(Integer, primary_key=True)
    atividade_id = Column(Integer, ForeignKey('atividade_multipla_data.id'), nullable=False)
    data_atividade_id = Column(Integer, ForeignKey('atividade_data.id'), nullable=False)
    usuario_id = Column(Integer, ForeignKey('usuario.id'), nullable=False)
    
    # Status de presença
    presente_manha = Column(Boolean, default=False)
    presente_tarde = Column(Boolean, default=False)
    presente_dia_inteiro = Column(Boolean, default=False)  # Para atividades de dia inteiro
    
    # Dados do checkin
    data_checkin_manha = Column(DateTime, nullable=True)
    data_checkin_tarde = Column(DateTime, nullable=True)
    palavra_chave_usada_manha = Column(String(50), nullable=True)
    palavra_chave_usada_tarde = Column(String(50), nullable=True)
    
    # Observações
    observacoes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    atividade = relationship("AtividadeMultiplaData", back_populates="frequencias")
    data_atividade = relationship("AtividadeData", back_populates="frequencias")
    usuario = relationship("Usuario", backref="frequencias_atividades")
    
    def __repr__(self):
        return f'<FrequenciaAtividade {self.usuario.nome} - {self.data_atividade.data}>'
    
    def get_status_presenca(self):
        """Retorna o status de presença do usuário"""
        if self.presente_dia_inteiro:
            return "Dia Inteiro"
        elif self.presente_manha and self.presente_tarde:
            return "Manhã e Tarde"
        elif self.presente_manha:
            return "Manhã"
        elif self.presente_tarde:
            return "Tarde"
        else:
            return "Ausente"
    
    def get_carga_horaria_presenca(self):
        """Retorna a carga horária baseada na presença"""
        if self.presente_dia_inteiro:
            return self.data_atividade.get_carga_horaria()
        elif self.presente_manha and self.presente_tarde:
            return self.data_atividade.get_carga_horaria()
        elif self.presente_manha or self.presente_tarde:
            return self.data_atividade.get_carga_horaria() / 2
        else:
            return 0


class CheckinAtividade(db.Model):
    """Modelo para checkins específicos de atividades com múltiplas datas"""
    __tablename__ = 'checkin_atividade'
    
    id = Column(Integer, primary_key=True)
    atividade_id = Column(Integer, ForeignKey('atividade_multipla_data.id'), nullable=False)
    data_atividade_id = Column(Integer, ForeignKey('atividade_data.id'), nullable=False)
    usuario_id = Column(Integer, ForeignKey('usuario.id'), nullable=False)
    
    # Dados do checkin
    data_hora = Column(DateTime, default=datetime.utcnow)
    palavra_chave = Column(String(50), nullable=False)
    turno = Column(String(10), nullable=False)  # 'manha', 'tarde', 'dia_inteiro'
    
    # Dados adicionais
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Relacionamentos
    atividade = relationship("AtividadeMultiplaData", back_populates="checkins")
    data_atividade = relationship("AtividadeData", back_populates="checkins")
    usuario = relationship("Usuario", backref="checkins_atividades")
    
    def __repr__(self):
        return f'<CheckinAtividade {self.usuario.nome} - {self.data_atividade.data} - {self.turno}>'
    
    def get_turno_display(self):
        """Retorna o turno formatado para exibição"""
        turnos = {
            'manha': 'Manhã',
            'tarde': 'Tarde',
            'dia_inteiro': 'Dia Inteiro'
        }
        return turnos.get(self.turno, self.turno)


# Tabela de associação para ministrantes de atividades
atividade_ministrantes_association = Table(
    'atividade_ministrantes_association',
    db.metadata,
    Column('atividade_id', Integer, ForeignKey('atividade_multipla_data.id'), primary_key=True),
    Column('ministrante_id', Integer, ForeignKey('ministrante.id'), primary_key=True)
)
