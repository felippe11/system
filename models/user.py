import uuid
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash

from extensions import db


usuario_clientes = db.Table(
    "usuario_clientes",
    db.Column("usuario_id", db.Integer, db.ForeignKey("usuario.id")),
    db.Column("cliente_id", db.Integer, db.ForeignKey("cliente.id")),
)


class Usuario(db.Model, UserMixin):
    __tablename__ = "usuario"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    formacao = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default="participante")
    cliente_id = db.Column(
        db.Integer, db.ForeignKey("cliente.id"), nullable=True
    )  # ✅ Alterado para permitir NULL
    evento_id = db.Column(
        db.Integer, db.ForeignKey("evento.id"), nullable=True
    )  # Novo campo para associar usuário ao evento
    tipo_inscricao_id = db.Column(
        db.Integer, db.ForeignKey("evento_inscricao_tipo.id"), nullable=True
    )

    tipo_inscricao = db.relationship(
        "EventoInscricaoTipo", backref=db.backref("usuarios", lazy=True)
    )
    cliente = db.relationship(
        "Cliente", backref=db.backref("usuarios_legacy", lazy=True)
    )
    clientes = db.relationship(
        "Cliente", secondary="usuario_clientes", back_populates="usuarios"
    )
    evento = db.relationship("Evento", backref=db.backref("usuarios", lazy=True))
    password_reset_tokens = db.relationship(
        "PasswordResetToken",
        cascade="all, delete-orphan",
        passive_deletes=True,
        back_populates="usuario",
    )
    # NOVOS CAMPOS PARA LOCAIS DE ATUAÇÃO:
    estados = db.Column(db.String(255), nullable=True)  # Ex.: "SP,RJ,MG"
    cidades = db.Column(
        db.String(255), nullable=True
    )  # Ex.: "São Paulo,Rio de Janeiro,Belo Horizonte"

    # MFA
    mfa_enabled = db.Column(db.Boolean, default=False)
    mfa_secret = db.Column(db.String(32), nullable=True)
    ativo = db.Column(db.Boolean, default=True)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha, senha)

    def __repr__(self):
        return f"<Usuario {self.nome}>"

    def is_superuser(self):
        return self.tipo == "superadmin"

    def is_cliente(self):
        return self.tipo == "cliente"

    @property
    def is_admin(self):
        return self.tipo == "admin"

    def is_active(self):
        return self.ativo

    def is_professor(self):
        return self.tipo == "professor"

    def is_revisor(self):
        return self.tipo == "revisor"

    def tem_pagamento_pendente(self):
        from .event import Inscricao

        pendente = Inscricao.query.filter_by(
            usuario_id=self.id, status_pagamento="pending"
        ).count()
        return pendente > 0


class Cliente(db.Model, UserMixin):
    __tablename__ = "cliente"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, default=True)  # Habilitação pelo superusuário
    tipo = db.Column(db.String(20), default="cliente")  # Define o tipo do usuário
    cliente_id = db.Column(
        db.Integer, db.ForeignKey("cliente.id"), nullable=True
    )  # ✅ Adicionando relação com Cliente

    # Campo novo para pagamento:
    habilita_pagamento = db.Column(db.Boolean, default=True)

    # Relacionamento com Oficina
    oficinas = db.relationship(
        "Oficina", back_populates="cliente"
    )  # ✅ Agora usa `back_populates`

    configuracao = db.relationship(
        "ConfiguracaoCliente", back_populates="cliente", uselist=False
    )
    usuarios = db.relationship(
        "Usuario", secondary="usuario_clientes", back_populates="clientes"
    )

    # Novos campos (caminho das imagens):
    logo_certificado = db.Column(db.String(255), nullable=True)  # Logo
    fundo_certificado = db.Column(db.String(255), nullable=True)  # Fundo do certificado
    assinatura_certificado = db.Column(db.String(255), nullable=True)  # Assinatura
    texto_personalizado = db.Column(db.Text)

    def is_active(self):
        """Retorna True se o cliente está ativo."""
        return self.ativo

    def get_id(self):
        """Retorna o ID do cliente como string, necessário para Flask-Login."""
        return str(self.id)

    def is_cliente(self):
        return self.tipo == "cliente"

    @property
    def is_admin(self):
        return self.tipo == "admin"

    def is_professor(self):
        """Indica se o cliente é um professor."""
        return False


class LinkCadastro(db.Model):
    __tablename__ = "link_cadastro"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=True)
    slug_customizado = db.Column(db.String(50), unique=True, nullable=True)
    token = db.Column(
        db.String(36), unique=True, nullable=False, default=str(uuid.uuid4())
    )
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    cliente = db.relationship(
        "Cliente", backref=db.backref("links_cadastro", lazy=True)
    )
    evento = db.relationship("Evento", backref=db.backref("links_cadastro", lazy=True))

    def __repr__(self):
        return (
            f"<LinkCadastro cliente_id={self.cliente_id}, evento_id={self.evento_id}, "
            f"token={self.token}, slug={self.slug_customizado}>"
        )


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_token"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    token = db.Column(
        db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    usuario = db.relationship("Usuario", back_populates="password_reset_tokens")

    def __repr__(self):
        return f"<PasswordResetToken usuario_id={self.usuario_id} token={self.token}>"


class MonitorCadastroLink(db.Model):
    """Link para autoinscrição de monitores."""

    __tablename__ = "monitor_cadastro_link"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    token = db.Column(
        db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    cliente = db.relationship(
        "Cliente", backref=db.backref("monitor_cadastro_links", lazy=True)
    )

    def is_valid(self):
        """Retorna True se o link não foi usado e ainda não expirou."""
        return (not self.used) and datetime.utcnow() < self.expires_at


class Monitor(db.Model, UserMixin):
    __tablename__ = "monitor"
    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(255), nullable=False)
    curso = db.Column(db.String(255), nullable=False)
    carga_horaria_disponibilidade = db.Column(db.Integer, nullable=False)  # Horas por semana
    dias_disponibilidade = db.Column(db.String(255), nullable=False)  # Ex: "segunda,terça,quarta"
    turnos_disponibilidade = db.Column(db.String(255), nullable=False)  # Ex: "manhã,tarde"
    email = db.Column(db.String(255), unique=True, nullable=False)
    telefone_whatsapp = db.Column(db.String(20), nullable=False)
    codigo_acesso = db.Column(db.String(10), unique=True, nullable=False)  # Código único para login
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=True)
    
    # Relacionamentos
    cliente = db.relationship("Cliente", backref="monitores")
    
    @property
    def tipo(self):
        return "monitor"
    
    def get_dias_lista(self):
        """Retorna lista dos dias de disponibilidade"""
        return self.dias_disponibilidade.split(',') if self.dias_disponibilidade else []
    
    def get_turnos_lista(self):
        """Retorna lista dos turnos de disponibilidade"""
        return self.turnos_disponibilidade.split(',') if self.turnos_disponibilidade else []
    
    def get_dias_disponibilidade(self):
        """Retorna lista dos dias de disponibilidade (alias para get_dias_lista)"""
        return self.get_dias_lista()
    
    def get_turnos_disponibilidade(self):
        """Retorna lista dos turnos de disponibilidade (alias para get_turnos_lista)"""
        return self.get_turnos_lista()
    
    def is_active(self):
        return self.ativo
    
    def __repr__(self):
        return f"<Monitor {self.nome_completo}>"


class Ministrante(db.Model, UserMixin):
    __tablename__ = "ministrante"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    formacao = db.Column(db.String(255), nullable=False)
    categorias_formacao = db.Column(
        db.String(512), nullable=True
    )  # Nova coluna para múltiplas categorias
    foto = db.Column(
        db.String(255), nullable=True
    )  # Nova coluna para armazenar caminho da foto
    areas_atuacao = db.Column(db.String(255), nullable=False)
    cpf = db.Column(db.String(20), unique=True, nullable=False)
    pix = db.Column(db.String(255), nullable=False)
    cidade = db.Column(db.String(255), nullable=False)
    estado = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=True)
    
    # Novos campos para Formador
    telefone = db.Column(db.String(20), nullable=True)
    endereco = db.Column(db.String(500), nullable=True)
    banco = db.Column(db.String(100), nullable=True)
    agencia = db.Column(db.String(20), nullable=True)
    conta = db.Column(db.String(30), nullable=True)
    tipo_conta = db.Column(db.String(20), nullable=True)  # corrente, poupança
    chave_pix = db.Column(db.String(255), nullable=True)  # diferente do campo pix existente
    ativo = db.Column(db.Boolean, default=True)
    
    cliente = db.relationship("Cliente", backref="ministrantes")

    @property
    def tipo(self):
        return "ministrante"

    def __repr__(self):
        return f"<Ministrante {self.nome}>"


class FormadorCadastroLink(db.Model):
    """Link para autoinscrição de formadores."""

    __tablename__ = "formador_cadastro_link"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    token = db.Column(
        db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    descricao = db.Column(db.String(255), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    cliente = db.relationship(
        "Cliente", backref=db.backref("formador_cadastro_links", lazy=True)
    )

    def is_valid(self):
        """Retorna True se o link não foi usado e ainda não expirou."""
        return (not self.used) and datetime.utcnow() < self.expires_at

    def __repr__(self):
        return f"<FormadorCadastroLink {self.token}>"
