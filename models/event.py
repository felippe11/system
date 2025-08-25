import os
import uuid
from datetime import datetime, date
from extensions import db  # Se você inicializa o SQLAlchemy em 'extensions.py'
from sqlalchemy.orm import relationship, foreign  # Adicione esta linha!


#           CONFIGURAÇÃO
# =================================
class Configuracao(db.Model):
    __tablename__ = "configuracao"

    id = db.Column(db.Integer, primary_key=True)
    permitir_checkin_global = db.Column(db.Boolean, default=False)
    habilitar_feedback = db.Column(db.Boolean, default=False)
    habilitar_certificado_individual = db.Column(db.Boolean, default=False)

    taxa_percentual_inscricao = db.Column(db.Numeric(5, 2), default=0)

    def __repr__(self):
        return f"<Configuracao permitir_checkin_global={self.permitir_checkin_global}>"


# =================================
#       ASSOCIAÇÕES DE EVENTO
# =================================

# Tabela de associação N:N
oficina_ministrantes_association = db.Table(
    "oficina_ministrantes_association",
    db.Column("oficina_id", db.Integer, db.ForeignKey("oficina.id"), primary_key=True),
    db.Column(
        "ministrante_id", db.Integer, db.ForeignKey("ministrante.id"), primary_key=True
    ),
)

# Association table linking formulários to eventos
evento_formulario_association = db.Table(
    "evento_formulario_association",
    db.Column("evento_id", db.Integer, db.ForeignKey("evento.id"), primary_key=True),
    db.Column(
        "formulario_id", db.Integer, db.ForeignKey("formularios.id"), primary_key=True
    ),
)

# =================================
#             OFICINA
# =================================
class Oficina(db.Model):
    __tablename__ = "oficina"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    ministrante_id = db.Column(
        db.Integer, db.ForeignKey("ministrante.id"), nullable=True
    )
    ministrante_obj = db.relationship("Ministrante", backref="oficinas", lazy=True)

    # Tipo de inscrição: 'sem_inscricao', 'com_inscricao_sem_limite', 'com_inscricao_com_limite'
    tipo_inscricao = db.Column(
        db.String(30), nullable=False, default="com_inscricao_com_limite"
    )
    # Tipo de oficina: 'Oficina', 'Palestra', 'Conferência', etc.
    tipo_oficina = db.Column(db.String(50), nullable=True)
    # Campo para quando o tipo_oficina for 'outros'
    tipo_oficina_outro = db.Column(db.String(100), nullable=True)
    vagas = db.Column(db.Integer, nullable=False)
    carga_horaria = db.Column(db.String(10), nullable=False)
    estado = db.Column(db.String(2), nullable=False)
    cidade = db.Column(db.String(100), nullable=False)
    qr_code = db.Column(db.String(255), nullable=True)

    opcoes_checkin = db.Column(
        db.String(255), nullable=True
    )  # Ex: "palavra1,palavra2,palavra3,palavra4,palavra5"
    palavra_correta = db.Column(db.String(50), nullable=True)

    cliente_id = db.Column(
        db.Integer, db.ForeignKey("cliente.id"), nullable=True
    )  # ✅ Adicionado
    cliente = db.relationship(
        "Cliente", back_populates="oficinas"
    )  # ✅ Corrigido para `back_populates`
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=True)
    evento = db.relationship("Evento", backref=db.backref("oficinas", lazy=True))

    ministrantes_associados = db.relationship(
        "Ministrante",
        secondary="oficina_ministrantes_association",  # nome da tabela que criamos
        backref="oficinas_relacionadas",
        lazy="dynamic",  # ou 'select', 'joined', etc. conforme sua preferência
    )

    dias = db.relationship(
        "OficinaDia", back_populates="oficina", lazy=True, cascade="all, delete-orphan"
    )

    # Novo campo: Se True, inscrição gratuita; se False, será necessário realizar pagamento.
    inscricao_gratuita = db.Column(db.Boolean, default=True)

    # 🔥 Corrigido o método __init__
    def __init__(
        self,
        titulo,
        descricao,
        ministrante_id,
        vagas,
        carga_horaria,
        estado,
        cidade,
        cliente_id=None,
        evento_id=None,
        qr_code=None,
        opcoes_checkin=None,
        palavra_correta=None,
        tipo_inscricao="com_inscricao_com_limite",
        tipo_oficina="Oficina",
        tipo_oficina_outro=None,
        inscricao_gratuita=True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.titulo = titulo
        self.descricao = descricao
        self.ministrante_id = ministrante_id
        self.carga_horaria = carga_horaria
        self.estado = estado
        self.cidade = cidade
        self.qr_code = qr_code
        self.cliente_id = cliente_id
        self.evento_id = evento_id
        self.opcoes_checkin = opcoes_checkin
        self.palavra_correta = palavra_correta
        self.tipo_inscricao = tipo_inscricao
        self.tipo_oficina = tipo_oficina
        self.tipo_oficina_outro = tipo_oficina_outro
        self.inscricao_gratuita = inscricao_gratuita

        # Define o valor de vagas com base no tipo de inscrição
        if tipo_inscricao == "sem_inscricao":
            self.vagas = 0  # Não é necessário controlar vagas
        elif tipo_inscricao == "com_inscricao_sem_limite":
            self.vagas = 9999  # Um valor alto para representar "sem limite"
        else:  # com_inscricao_com_limite
            self.vagas = vagas

    def __repr__(self):
        return f"<Oficina {self.titulo}>"


# =================================
#          OFICINA DIA
# =================================
class OficinaDia(db.Model):
    __tablename__ = "oficinadia"

    id = db.Column(db.Integer, primary_key=True)
    oficina_id = db.Column(db.Integer, db.ForeignKey("oficina.id"), nullable=False)
    data = db.Column(db.Date, nullable=False)
    horario_inicio = db.Column(db.String(5), nullable=False)
    horario_fim = db.Column(db.String(5), nullable=False)
    palavra_chave_manha = db.Column(db.String(50), nullable=True)
    palavra_chave_tarde = db.Column(db.String(50), nullable=True)

    oficina = db.relationship("Oficina", back_populates="dias")

    def __repr__(self):
        return f"<OficinaDia {self.data} {self.horario_inicio}-{self.horario_fim}>"


# =================================
#           INSCRIÇÃO
# =================================


class Inscricao(db.Model):
    __tablename__ = "inscricao"

    # 👉 NOVOS CAMPOS
    payment_id = db.Column(
        db.String(64), index=True, nullable=True
    )  # id da transação no MP
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, index=True, nullable=False
    )

    boleto_url = db.Column(db.String(512), nullable=True)  # ← NOVO

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    oficina_id = db.Column(db.Integer, db.ForeignKey("oficina.id"), nullable=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=True)

    qr_code_token = db.Column(db.String(100), unique=True, nullable=True)
    checkin_attempts = db.Column(db.Integer, default=0)

    tipo_inscricao_id = db.Column(
        db.Integer, db.ForeignKey("inscricao_tipo.id"), nullable=True
    )
    lote_id = db.Column(db.Integer, db.ForeignKey("lote_inscricao.id"), nullable=True)

    usuario = db.relationship(
        "Usuario", backref=db.backref("inscricoes", lazy="joined")
    )
    oficina = db.relationship("Oficina", backref="inscritos")
    evento = db.relationship("Evento", backref="inscricoes")
    lote = db.relationship("LoteInscricao", backref=db.backref("inscricoes", lazy=True))
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)

    status_pagamento = db.Column(
        db.String(20), default="pending", index=True  # ➊  (gera índice)
    )

    def __init__(
        self,
        usuario_id,
        cliente_id,
        oficina_id=None,
        evento_id=None,
        status_pagamento="pending",
        lote_id=None,
        tipo_inscricao_id=None,
    ):
        self.usuario_id = usuario_id
        self.cliente_id = cliente_id
        self.oficina_id = oficina_id
        self.evento_id = evento_id
        self.status_pagamento = status_pagamento
        self.lote_id = lote_id
        self.tipo_inscricao_id = tipo_inscricao_id

        # Gera um token único garantido
        while True:
            token = str(uuid.uuid4())
            existing = Inscricao.query.filter_by(qr_code_token=token).first()
            if not existing:
                self.qr_code_token = token
                break

    def __repr__(self):
        return f"<Inscricao Usuario={self.usuario_id}, Oficina={self.oficina_id}, Evento={self.evento_id}>"


# Novo modelo para tipos de inscrição (caso a oficina seja paga)
class InscricaoTipo(db.Model):
    __tablename__ = "inscricao_tipo"

    id = db.Column(db.Integer, primary_key=True)
    oficina_id = db.Column(db.Integer, db.ForeignKey("oficina.id"), nullable=False)
    nome = db.Column(db.String(100), nullable=True)  # Ex: Estudante, Professor
    preco = db.Column(db.Numeric(10, 2), nullable=True)

    oficina = db.relationship(
        "Oficina", backref=db.backref("tipos_inscricao", lazy=True)
    )

    def __repr__(self):
        return f"<InscricaoTipo {self.nome}: R$ {self.preco}>"


# Em models.py ou onde você define seus modelos


class EventoInscricaoTipo(db.Model):
    __tablename__ = "evento_inscricao_tipo"

    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    submission_only = db.Column(db.Boolean, default=False)

    # Relação com Evento - removendo backref para evitar conflito

    def __init__(self, evento_id, nome, preco, submission_only=False):
        self.evento_id = evento_id
        self.nome = nome
        self.preco = preco
        self.submission_only = submission_only

    @property
    def tipo_inscricao(self):
        """Alias to self for template compatibility."""
        return self


class RegraInscricaoEvento(db.Model):
    __tablename__ = "regra_inscricao_evento"

    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    tipo_inscricao_id = db.Column(
        db.Integer, db.ForeignKey("evento_inscricao_tipo.id"), nullable=False
    )
    limite_oficinas = db.Column(db.Integer, nullable=False, default=0)  # 0 = sem limite
    oficinas_permitidas = db.Column(
        db.Text, nullable=True
    )  # IDs das oficinas separados por vírgula

    evento = db.relationship(
        "Evento", backref=db.backref("regras_inscricao", lazy=True)
    )
    tipo_inscricao = db.relationship(
        "EventoInscricaoTipo", backref=db.backref("regras", lazy=True)
    )

    def __init__(
        self, evento_id, tipo_inscricao_id, limite_oficinas=0, oficinas_permitidas=None
    ):
        self.evento_id = evento_id
        self.tipo_inscricao_id = tipo_inscricao_id
        self.limite_oficinas = limite_oficinas
        self.oficinas_permitidas = oficinas_permitidas

    def get_oficinas_permitidas_list(self):
        if not self.oficinas_permitidas:
            return []
        return [int(id) for id in self.oficinas_permitidas.split(",") if id]

    def set_oficinas_permitidas_list(self, oficinas_ids):
        self.oficinas_permitidas = ",".join(str(id) for id in oficinas_ids)


# =================================
#            CHECKIN
# =================================


class Checkin(db.Model):
    __tablename__ = "checkin"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer, db.ForeignKey("usuario.id"), nullable=False, index=True
    )
    oficina_id = db.Column(
        db.Integer, db.ForeignKey("oficina.id"), nullable=True, index=True
    )  # agora pode ser nulo
    evento_id = db.Column(
        db.Integer, db.ForeignKey("evento.id"), nullable=True, index=True
    )  # novo campo
    data_hora = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    palavra_chave = db.Column(db.String(50), nullable=False)

    # NOVO  ▼▼▼
    cliente_id = db.Column(
        db.Integer, db.ForeignKey("cliente.id"), nullable=True, index=True
    )
    cliente = db.relationship("Cliente", backref=db.backref("checkins", lazy=True))

    usuario = db.relationship("Usuario", backref=db.backref("checkins", lazy=True))
    oficina = db.relationship("Oficina", backref=db.backref("checkins", lazy=True))
    evento = db.relationship("Evento", backref=db.backref("checkins_evento", lazy=True))

    def __repr__(self):
        return f"<Checkin (usuario={self.usuario_id}, oficina={self.oficina_id}, evento={self.evento_id}, data={self.data_hora})>"

    @property
    def turno(self) -> str:
        """Retorna o turno baseado no horário do check-in."""
        from utils import determinar_turno

        return determinar_turno(self.data_hora)


# =================================
#            FEEDBACK
# =================================
class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    ministrante_id = db.Column(
        db.Integer, db.ForeignKey("ministrante.id"), nullable=True
    )
    oficina_id = db.Column(db.Integer, db.ForeignKey("oficina.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # Nota de 1 a 5
    comentario = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship("Usuario", backref="feedbacks")
    ministrante = db.relationship("Ministrante", backref="feedbacks")
    oficina = db.relationship("Oficina", backref="feedbacks")

    def __repr__(self):
        return (
            f"<Feedback id={self.id} "
            f"Usuario={self.usuario_id if self.usuario_id else 'N/A'} "
            f"Ministrante={self.ministrante_id if self.ministrante_id else 'N/A'} "
            f"Oficina={self.oficina_id}>"
        )


# =================================
#       MATERIAL DA OFICINA
# =================================
class MaterialOficina(db.Model):
    __tablename__ = "material_oficina"

    id = db.Column(db.Integer, primary_key=True)
    oficina_id = db.Column(db.Integer, db.ForeignKey("oficina.id"), nullable=False)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    caminho_arquivo = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    oficina = db.relationship("Oficina", backref="materiais")

    def __repr__(self):
        return f"<MaterialOficina id={self.id}, arquivo={self.nome_arquivo}>"


# =================================
#       RELATÓRIO DA OFICINA
# =================================
class RelatorioOficina(db.Model):
    __tablename__ = "relatorio_oficina"

    id = db.Column(db.Integer, primary_key=True)
    oficina_id = db.Column(db.Integer, db.ForeignKey("oficina.id"), nullable=False)
    ministrante_id = db.Column(
        db.Integer, db.ForeignKey("ministrante.id"), nullable=False
    )

    metodologia = db.Column(db.Text, nullable=True)
    resultados = db.Column(db.Text, nullable=True)
    fotos_videos_path = db.Column(db.String(255), nullable=True)
    enviado_em = db.Column(db.DateTime, default=datetime.utcnow)

    oficina = db.relationship(
        "Oficina", backref=db.backref("relatorios_oficina", lazy=True)
    )
    ministrante = db.relationship(
        "Ministrante", backref=db.backref("relatorios_ministrante", lazy=True)
    )

    def __repr__(self):
        return f"<RelatorioOficina oficina_id={self.oficina_id} ministrante_id={self.ministrante_id}>"



from extensions import db


class Formulario(db.Model):
    __tablename__ = "formularios"

    id = db.Column(db.Integer, primary_key=True)

    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    data_inicio = db.Column(db.DateTime, nullable=True)
    data_fim = db.Column(db.DateTime, nullable=True)
    permitir_multiplas_respostas = db.Column(db.Boolean, default=True)
    is_submission_form = db.Column(db.Boolean, default=False)

    # Relação com Cliente (opcional por cliente)
    cliente_id = db.Column(
        db.Integer, db.ForeignKey("cliente.id"), nullable=True
    )  # Se cada cliente puder ter seus próprios formulários
    cliente = db.relationship("Cliente", backref=db.backref("formularios", lazy=True))

    # Campos do formulário
    campos = db.relationship(
        "CampoFormulario",
        backref="formulario",
        lazy=True,
        cascade="all, delete-orphan",
    )

    # Respostas do formulário
    respostas = db.relationship(
        "RespostaFormulario",
        back_populates="formulario",
        cascade="all, delete-orphan",
    )

    # Eventos associados a este formulário
    eventos = db.relationship(
        "Evento",
        secondary="evento_formulario_association",
        backref=db.backref("formularios", lazy="dynamic"),
    )

    def __repr__(self):
        return f"<Formulario {self.nome}>"


class CampoFormulario(db.Model):
    __tablename__ = "campos_formulario"

    id = db.Column(db.Integer, primary_key=True)
    formulario_id = db.Column(
        db.Integer, db.ForeignKey("formularios.id"), nullable=True, default=1
    )  # Atualizado: permite NULL e default 1
    nome = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    opcoes = db.Column(db.Text, nullable=True)
    obrigatorio = db.Column(db.Boolean, default=False)
    tamanho_max = db.Column(db.Integer, nullable=True)
    regex_validacao = db.Column(db.String(255), nullable=True)
    descricao = db.Column(db.Text, nullable=True)  # Novo campo conforme banco do Render

    def __repr__(self):
        return f"<Campo {self.nome} ({self.tipo})>"


class RespostaFormulario(db.Model):
    __tablename__ = "respostas_formulario"

    id = db.Column(db.Integer, primary_key=True)
    formulario_id = db.Column(
        db.Integer, db.ForeignKey("formularios.id"), nullable=False
    )
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    data_submissao = db.Column(db.DateTime, default=datetime.utcnow)

    # NOVA COLUNA PARA STATUS
    status_avaliacao = db.Column(db.String(50), nullable=True, default="Não Avaliada")

    respostas_campos = db.relationship(
        "RespostaCampo",
        back_populates="resposta_formulario",
        cascade="all, delete-orphan",
    )

    formulario = db.relationship(
        "Formulario", back_populates="respostas"
    )  # 🔄 Corrigido o back_populates
    usuario = db.relationship("Usuario", backref=db.backref("respostas", lazy=True))

    def __repr__(self):
        return f"<RespostaFormulario ID {self.id} - Formulário {self.formulario_id} - Usuário {self.usuario_id}>"


class RespostaCampo(db.Model):
    __tablename__ = "respostas_campo"

    id = db.Column(db.Integer, primary_key=True)
    resposta_formulario_id = db.Column(
        db.Integer, db.ForeignKey("respostas_formulario.id"), nullable=False
    )
    campo_id = db.Column(
        db.Integer, db.ForeignKey("campos_formulario.id"), nullable=False
    )
    valor = db.Column(db.Text, nullable=False)

    resposta_formulario = db.relationship(
        "RespostaFormulario", back_populates="respostas_campos"
    )
    campo = db.relationship(
        "CampoFormulario", backref=db.backref("respostas", lazy=True)
    )

    def __repr__(self):
        return (
            f"<RespostaCampo ID {self.id} - Campo {self.campo_id} - Valor {self.valor}>"
        )


# models.py
class ConfiguracaoCliente(db.Model):
    __tablename__ = "configuracao_cliente"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)

    permitir_checkin_global = db.Column(db.Boolean, default=False)
    habilitar_feedback = db.Column(db.Boolean, default=False)
    habilitar_certificado_individual = db.Column(db.Boolean, default=False)

    # Campo para habilitar credenciamento via QRCode do evento:
    habilitar_qrcode_evento_credenciamento = db.Column(db.Boolean, default=False)

    # Relacionamento com o cliente (opcional se quiser acessar .cliente)
    cliente = db.relationship("Cliente", back_populates="configuracao")

    habilitar_submissao_trabalhos = db.Column(db.Boolean, default=False)
    # Exibe a taxa de serviço separadamente no preço da inscrição
    mostrar_taxa = db.Column(db.Boolean, default=True)
    # Taxa diferenciada específica para o cliente (se definida, sobrepõe a taxa geral)
    taxa_diferenciada = db.Column(db.Numeric(5, 2), nullable=True)

    allowed_file_types = db.Column(db.String(100), default="pdf")
    formulario_submissao_id = db.Column(
        db.Integer, db.ForeignKey("formularios.id"), nullable=True
    )
    formulario_submissao = db.relationship("Formulario")

    review_model = db.Column(db.String(20), default="single")
    num_revisores_min = db.Column(db.Integer, default=1)

    num_revisores_max = db.Column(db.Integer, default=2)
    prazo_parecer_dias = db.Column(db.Integer, default=14)
    max_trabalhos_por_revisor = db.Column(db.Integer, default=5, nullable=True)

    obrigatorio_nome = db.Column(db.Boolean, default=True)
    obrigatorio_cpf = db.Column(db.Boolean, default=True)

    obrigatorio_email = db.Column(db.Boolean, default=True)
    obrigatorio_senha = db.Column(db.Boolean, default=True)
    obrigatorio_formacao = db.Column(db.Boolean, default=True)

    limite_eventos = db.Column(db.Integer, default=5)
    limite_inscritos = db.Column(db.Integer, default=1000)
    limite_formularios = db.Column(db.Integer, default=3)
    limite_revisores = db.Column(db.Integer, default=2)


class ConfiguracaoEvento(db.Model):
    __tablename__ = "configuracao_evento"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)

    permitir_checkin_global = db.Column(db.Boolean, default=False)
    habilitar_feedback = db.Column(db.Boolean, default=False)
    habilitar_certificado_individual = db.Column(db.Boolean, default=False)
    habilitar_qrcode_evento_credenciamento = db.Column(db.Boolean, default=False)

    cliente = db.relationship(
        "Cliente", backref=db.backref("configuracoes_evento", lazy=True)
    )
    evento = db.relationship(
        "Evento", backref=db.backref("configuracao_evento", uselist=False)
    )

    habilitar_submissao_trabalhos = db.Column(db.Boolean, default=False)
    mostrar_taxa = db.Column(db.Boolean, default=True)
    taxa_diferenciada = db.Column(db.Numeric(5, 2), nullable=True)

    allowed_file_types = db.Column(db.String(100), default="pdf")

    review_model = db.Column(db.String(20), default="single")
    num_revisores_min = db.Column(db.Integer, default=1)
    num_revisores_max = db.Column(db.Integer, default=2)
    prazo_parecer_dias = db.Column(db.Integer, default=14)

    obrigatorio_nome = db.Column(db.Boolean, default=True)
    obrigatorio_cpf = db.Column(db.Boolean, default=True)
    obrigatorio_email = db.Column(db.Boolean, default=True)
    obrigatorio_senha = db.Column(db.Boolean, default=True)
    obrigatorio_formacao = db.Column(db.Boolean, default=True)

    limite_eventos = db.Column(db.Integer, default=5)
    limite_inscritos = db.Column(db.Integer, default=1000)
    limite_formularios = db.Column(db.Integer, default=3)
    limite_revisores = db.Column(db.Integer, default=2)

    def to_dict(self):
        """Return a dictionary representation of configuration flags."""
        fields = [
            "permitir_checkin_global",
            "habilitar_qrcode_evento_credenciamento",
            "habilitar_feedback",
            "habilitar_certificado_individual",
            "mostrar_taxa",
            "habilitar_submissao_trabalhos",
            "review_model",
            "num_revisores_min",
            "num_revisores_max",
            "prazo_parecer_dias",
            "obrigatorio_nome",
            "obrigatorio_cpf",
            "obrigatorio_email",
            "obrigatorio_senha",
            "obrigatorio_formacao",
            "allowed_file_types",
            "taxa_diferenciada",
            "limite_eventos",
            "limite_inscritos",
            "limite_formularios",
            "limite_revisores",
        ]
        return {f: getattr(self, f) for f in fields}


class FeedbackCampo(db.Model):
    __tablename__ = "feedback_campo"

    id = db.Column(db.Integer, primary_key=True)
    resposta_campo_id = db.Column(
        db.Integer, db.ForeignKey("respostas_campo.id"), nullable=False
    )

    ministrante_id = db.Column(
        db.Integer, db.ForeignKey("ministrante.id"), nullable=True
    )
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=True)

    texto_feedback = db.Column(db.Text, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    resposta_campo = db.relationship(
        "RespostaCampo",
        backref=db.backref("feedbacks_campo", lazy=True, cascade="all, delete-orphan"),
    )
    ministrante = db.relationship(
        "Ministrante", backref=db.backref("feedbacks_campo", lazy=True)
    )
    cliente = db.relationship(
        "Cliente", backref=db.backref("feedbacks_campo", lazy=True)
    )

    def __repr__(self):
        return f"<FeedbackCampo id={self.id} resposta_campo={self.resposta_campo_id} ministrante={self.ministrante_id}>"


# =================================
#            PROPOSTA
# =================================
class Proposta(db.Model):
    __tablename__ = "proposta"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    tipo_evento = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Proposta {self.id} de {self.nome}>"


# =================================
#            EVENTO
# =================================


class Evento(db.Model):
    __tablename__ = "evento"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    banner_url = db.Column(db.String(255), nullable=True)
    programacao = db.Column(db.Text, nullable=True)
    localizacao = db.Column(db.String(255), nullable=True)
    link_mapa = db.Column(db.Text, nullable=True)
    inscricao_gratuita = db.Column(
        db.Boolean, default=False, nullable=False
    )  # Novo campo
    # Novos campos de data
    data_inicio = db.Column(db.DateTime, nullable=True)
    data_fim = db.Column(db.DateTime, nullable=True)
    hora_inicio = db.Column(db.Time, nullable=True)
    hora_fim = db.Column(db.Time, nullable=True)

    # Adicione aqui a coluna status
    status = db.Column(db.String(50), default="ativo")

    capacidade_padrao = db.Column(db.Integer, nullable=True, default=0)
    requer_aprovacao = db.Column(db.Boolean, default=False)
    publico = db.Column(db.Boolean, default=True)

    habilitar_lotes = db.Column(db.Boolean, default=False)

    submissao_aberta = db.Column(db.Boolean, default=False)

    cliente = db.relationship("Cliente", backref=db.backref("eventos", lazy=True))
    # Modificando o relacionamento para evitar conflito de backref
    tipos_inscricao = db.relationship(
        "EventoInscricaoTipo", backref="evento", overlaps="evento"
    )

    @property
    def tipos_inscricao_evento(self):
        """Propriedade para compatibilidade com os templates existentes"""
        return self.tipos_inscricao

    def get_regras_inscricao(self, tipo_inscricao_id):
        """Retorna as regras de inscrição para um tipo específico de inscrição"""
        for regra in self.regras_inscricao:
            if regra.tipo_inscricao_id == tipo_inscricao_id:
                return regra
        return None

    def get_data_formatada(self):
        if self.data_inicio:
            if self.data_fim and self.data_fim != self.data_inicio:
                return f"{self.data_inicio.strftime('%d/%m/%Y')} - {self.data_fim.strftime('%d/%m/%Y')}"
            return self.data_inicio.strftime("%d/%m/%Y")
        return "Data a definir"

    def get_preco_base(self):
        if self.tipos_inscricao:
            return min(tipo.preco for tipo in self.tipos_inscricao)
        return 0


class FormularioTemplate(db.Model):
    __tablename__ = "formulario_templates"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=True)
    categoria = db.Column(
        db.String(100), nullable=True
    )  # e.g., "workshop", "event", "course"
    is_default = db.Column(db.Boolean, default=False)

    cliente = db.relationship(
        "Cliente", backref=db.backref("templates_formulario", lazy=True)
    )
    campos = db.relationship(
        "CampoFormularioTemplate",
        backref="template",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<FormularioTemplate {self.nome}>"


class CampoFormularioTemplate(db.Model):
    __tablename__ = "campos_formulario_template"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(
        db.Integer, db.ForeignKey("formulario_templates.id"), nullable=False
    )
    nome = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    opcoes = db.Column(db.Text, nullable=True)
    obrigatorio = db.Column(db.Boolean, default=False)
    ordem = db.Column(db.Integer, default=0)  # For ordering fields

    def __repr__(self):
        return f"<CampoFormularioTemplate {self.nome} ({self.tipo})>"


from datetime import datetime, timedelta
from extensions import db


class ConfiguracaoAgendamento(db.Model):
    """Configuração de regras para agendamentos de visitas por cliente."""

    __tablename__ = "configuracao_agendamento"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)

    # Regras de agendamento
    prazo_cancelamento = db.Column(
        db.Integer, nullable=False, default=24
    )  # Horas antes do evento
    tempo_bloqueio = db.Column(
        db.Integer, nullable=False, default=7
    )  # Dias de bloqueio por violação
    capacidade_padrao = db.Column(
        db.Integer, nullable=False, default=30
    )  # Quantidade padrão de alunos por horário
    intervalo_minutos = db.Column(
        db.Integer, nullable=False, default=60
    )  # Minutos entre agendamentos

    tipos_inscricao_permitidos = db.Column(db.Text, nullable=True)

    # Horários de disponibilidade
    horario_inicio = db.Column(db.Time, nullable=False)
    horario_fim = db.Column(db.Time, nullable=False)
    dias_semana = db.Column(
        db.String(20), nullable=False, default="1,2,3,4,5"
    )  # 0=Dom, 1=Seg, ..., 6=Sáb

    # Relações
    cliente = db.relationship(
        "Cliente", backref=db.backref("configuracoes_agendamento", lazy=True)
    )
    evento = db.relationship(
        "Evento", backref=db.backref("configuracoes_agendamento", lazy=True)
    )

    def get_tipos_inscricao_list(self):
        if not self.tipos_inscricao_permitidos:
            return []
        return [int(t) for t in self.tipos_inscricao_permitidos.split(",") if t]

    def __repr__(self):
        return f"<ConfiguracaoAgendamento {self.id} - Evento {self.evento_id}>"


class SalaVisitacao(db.Model):
    """Salas disponíveis para visitação em um evento."""

    __tablename__ = "sala_visitacao"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    capacidade = db.Column(db.Integer, nullable=False, default=30)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)

    # Relações
    evento = db.relationship("Evento", backref=db.backref("salas_visitacao", lazy=True))

    def __repr__(self):
        return f"<SalaVisitacao {self.nome} - Evento {self.evento_id}>"


class HorarioVisitacao(db.Model):
    """Slots de horários disponíveis para agendamento."""

    __tablename__ = "horario_visitacao"

    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    data = db.Column(db.Date, nullable=False)
    horario_inicio = db.Column(db.Time, nullable=False)
    horario_fim = db.Column(db.Time, nullable=False)
    capacidade_total = db.Column(db.Integer, nullable=False)
    vagas_disponiveis = db.Column(db.Integer, nullable=False)

    # Relações
    evento = db.relationship(
        "Evento", backref=db.backref("horarios_visitacao", lazy=True)
    )

    def __repr__(self):
        return f"<HorarioVisitacao {self.data} {self.horario_inicio}-{self.horario_fim} ({self.vagas_disponiveis} vagas)>"


class AgendamentoVisita(db.Model):
    """Agendamento de visita feito por um professor, opcionalmente vinculado a um cliente."""

    __tablename__ = "agendamento_visita"

    id = db.Column(db.Integer, primary_key=True)
    horario_id = db.Column(
        db.Integer, db.ForeignKey("horario_visitacao.id"), nullable=False
    )

    professor_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)

    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=True)

    # Informações da escola e turma
    escola_nome = db.Column(db.String(200), nullable=False)
    escola_codigo_inep = db.Column(db.String(20), nullable=True)
    turma = db.Column(db.String(50), nullable=False)
    nivel_ensino = db.Column(
        db.String(50), nullable=False
    )  # Anos iniciais, finais, etc.
    quantidade_alunos = db.Column(db.Integer, nullable=False)
    rede_ensino = db.Column(db.String(100), nullable=True)
    municipio = db.Column(db.String(100), nullable=True)
    bairro = db.Column(db.String(100), nullable=True)
    responsavel_nome = db.Column(db.String(150), nullable=True)
    responsavel_cargo = db.Column(db.String(100), nullable=True)
    responsavel_whatsapp = db.Column(db.String(20), nullable=True)
    responsavel_email = db.Column(db.String(120), nullable=True)
    acompanhantes_nomes = db.Column(db.String(255), nullable=True)
    acompanhantes_qtd = db.Column(db.Integer, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    compromisso_1 = db.Column(db.Boolean, default=False)
    compromisso_2 = db.Column(db.Boolean, default=False)
    compromisso_3 = db.Column(db.Boolean, default=False)
    compromisso_4 = db.Column(db.Boolean, default=False)

    # Status do agendamento
    data_agendamento = db.Column(db.DateTime, default=datetime.utcnow)
    data_cancelamento = db.Column(db.DateTime, nullable=True)
    status = db.Column(
        db.String(20), default="pendente"
    )  # pendente, confirmado, cancelado, realizado
    checkin_realizado = db.Column(db.Boolean, default=False)
    data_checkin = db.Column(db.DateTime, nullable=True)

    # QR Code para check-in
    qr_code_token = db.Column(db.String(100), unique=True, nullable=False)

    # Salas selecionadas para visitação
    salas_selecionadas = db.Column(
        db.String(200), nullable=True
    )  # IDs separados por vírgula

    # Relações

    horario = db.relationship(
        "HorarioVisitacao", backref=db.backref("agendamentos", lazy=True)
    )
    professor = db.relationship(
        "Usuario", backref=db.backref("agendamentos_visitas", lazy=True)
    )
    cliente = db.relationship(
        "Cliente", backref=db.backref("agendamentos_visitas", lazy=True)
    )

    def __init__(self, **kwargs):
        super(AgendamentoVisita, self).__init__(**kwargs)
        import uuid

        self.qr_code_token = str(uuid.uuid4())

    def __repr__(self):

        cliente_nome = self.cliente.nome if self.cliente else "sem cliente"
        professor_nome = self.professor.nome if self.professor else "sem professor"
        return (
            f"<AgendamentoVisita {self.id} - Prof. {professor_nome} - "
            f"{self.escola_nome} ({cliente_nome})>"
        )


class AlunoVisitante(db.Model):
    """Alunos participantes de uma visita agendada."""

    __tablename__ = "aluno_visitante"

    id = db.Column(db.Integer, primary_key=True)
    agendamento_id = db.Column(
        db.Integer, db.ForeignKey("agendamento_visita.id"), nullable=False
    )
    nome = db.Column(db.String(150), nullable=False)
    cpf = db.Column(db.String(14), nullable=True)  # Opcional para menores
    presente = db.Column(db.Boolean, default=False)

    # Relações
    agendamento = db.relationship(
        "AgendamentoVisita", backref=db.backref("alunos", lazy=True)
    )
    
    # Relação many-to-many com materiais de apoio
    materiais_apoio = db.relationship(
        "MaterialApoio",
        secondary="aluno_material_apoio_association",
        backref=db.backref("alunos_atendidos", lazy=True),
        lazy="dynamic"
    )

    def __repr__(self):
        return f"<AlunoVisitante {self.nome} - Agendamento {self.agendamento_id}>"


class ProfessorBloqueado(db.Model):
    """Registro de professores bloqueados por violação de regras."""

    __tablename__ = "professor_bloqueado"

    id = db.Column(db.Integer, primary_key=True)
    professor_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    data_inicial = db.Column(db.DateTime, default=datetime.utcnow)
    data_final = db.Column(db.DateTime, nullable=False)
    motivo = db.Column(db.Text, nullable=False)

    # Relações
    professor = db.relationship("Usuario", backref=db.backref("bloqueios", lazy=True))
    evento = db.relationship(
        "Evento", backref=db.backref("professores_bloqueados", lazy=True)
    )

    def __repr__(self):
        return f"<ProfessorBloqueado {self.professor_id} até {self.data_final.strftime('%d/%m/%Y')}>"


class Patrocinador(db.Model):
    __tablename__ = "patrocinador"
    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    logo_path = db.Column(db.String(255), nullable=False)
    categoria = db.Column(
        db.String(50), nullable=False
    )  # Ex: 'Realização', 'Patrocínio', etc.

    evento = db.relationship("Evento", backref=db.backref("patrocinadores", lazy=True))

    def __init__(self, evento_id, logo_path, categoria):
        self.evento_id = evento_id
        self.logo_path = logo_path
        self.categoria = categoria


class CertificadoTemplate(db.Model):
    __tablename__ = "certificado_template"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    titulo = db.Column(db.String(100), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)  # HTML ou texto estruturado
    ativo = db.Column(db.Boolean, default=False)

    cliente = db.relationship("Cliente", backref="certificados_templates")


class CampoPersonalizadoCadastro(db.Model):
    __tablename__ = "campos_personalizados_cadastro"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # texto, número, email, data, etc.
    obrigatorio = db.Column(db.Boolean, default=False)

    cliente = db.relationship(
        "Cliente", backref=db.backref("campos_personalizados", lazy=True)
    )
    evento = db.relationship(
        "Evento", backref=db.backref("campos_personalizados", lazy=True)
    )


class WorkMetadata(db.Model):
    """Stores selected metadata from imported work spreadsheets."""

    __tablename__ = "work_metadata"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.JSON, nullable=False)
    titulo = db.Column(db.String(255), nullable=True)
    categoria = db.Column(db.String(100), nullable=True)
    rede_ensino = db.Column(db.String(100), nullable=True)
    etapa_ensino = db.Column(db.String(100), nullable=True)
    pdf_url = db.Column(db.String(255), nullable=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=True)

    evento = db.relationship("Evento")


class Pagamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    tipo_inscricao_id = db.Column(
        db.Integer, db.ForeignKey("evento_inscricao_tipo.id"), nullable=False
    )
    status = db.Column(db.String(50), default="pendente")
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    mercado_pago_id = db.Column(db.String(255), nullable=True)

    usuario = db.relationship("Usuario")
    evento = db.relationship("Evento")
    tipo_inscricao = db.relationship("EventoInscricaoTipo")


# Tabela de associação para múltiplos ganhadores por sorteio
sorteio_ganhadores = db.Table(
    "sorteio_ganhadores",
    db.Column("sorteio_id", db.Integer, db.ForeignKey("sorteio.id"), primary_key=True),
    db.Column("usuario_id", db.Integer, db.ForeignKey("usuario.id"), primary_key=True),
)


class Sorteio(db.Model):
    __tablename__ = "sorteio"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    premio = db.Column(db.String(255), nullable=False)
    data_sorteio = db.Column(db.DateTime, default=datetime.utcnow)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=True)
    oficina_id = db.Column(db.Integer, db.ForeignKey("oficina.id"), nullable=True)
    ganhador_id = db.Column(
        db.Integer, db.ForeignKey("usuario.id"), nullable=True
    )  # Mantido para compatibilidade
    num_vencedores = db.Column(db.Integer, default=1)  # Número de vencedores do sorteio
    status = db.Column(
        db.String(20), default="pendente"
    )  # pendente, realizado, cancelado

    # Relacionamentos
    cliente = db.relationship("Cliente", backref=db.backref("sorteios", lazy=True))
    evento = db.relationship("Evento", backref=db.backref("sorteios", lazy=True))
    oficina = db.relationship("Oficina", backref=db.backref("sorteios", lazy=True))
    ganhador = db.relationship(
        "Usuario", backref=db.backref("sorteios_ganhos", lazy=True)
    )  # Mantido para compatibilidade

    # Nova relação para múltiplos ganhadores
    ganhadores = db.relationship(
        "Usuario",
        secondary="sorteio_ganhadores",
        lazy="subquery",
        backref=db.backref("sorteios_vencidos", lazy=True),
    )

    def __repr__(self):
        return f"<Sorteio {self.titulo} - Prêmio: {self.premio}>"


class LoteInscricao(db.Model):
    __tablename__ = "lote_inscricao"

    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    data_inicio = db.Column(db.DateTime, nullable=True)
    data_fim = db.Column(db.DateTime, nullable=True)
    qtd_maxima = db.Column(db.Integer, nullable=True)  # Limite de inscrições
    ordem = db.Column(db.Integer, nullable=False, default=0)  # Para ordenar lotes
    ativo = db.Column(db.Boolean, default=True)

    # Relacionamento com o evento
    evento = db.relationship(
        "Evento", backref=db.backref("lotes", lazy=True, order_by="LoteInscricao.ordem")
    )

    def __repr__(self):
        return f"<LoteInscricao {self.nome}>"

    def is_valid(self):
        """Verifica se o lote está válido (dentro da data ou limite de inscritos)"""
        now = datetime.utcnow()

        # Verificar por data
        if self.data_inicio and self.data_fim:
            if now < self.data_inicio or now > self.data_fim:
                return False

        # Verificar por quantidade de inscrições
        if self.qtd_maxima is not None:
            count = Inscricao.query.filter_by(
                evento_id=self.evento_id, lote_id=self.id
            ).count()
            if count >= self.qtd_maxima:
                return False

        return True


class LoteTipoInscricao(db.Model):
    """Associa um *lote* de inscrição a um *tipo* de inscrição com preço."""

    __tablename__ = "lote_tipo_inscricao"

    id = db.Column(db.Integer, primary_key=True)
    lote_id = db.Column(db.Integer, db.ForeignKey("lote_inscricao.id"), nullable=False)
    tipo_inscricao_id = db.Column(
        db.Integer, db.ForeignKey("evento_inscricao_tipo.id"), nullable=False
    )
    preco = db.Column(db.Float, nullable=False)

    # relationships
    lote = db.relationship(
        "LoteInscricao", backref=db.backref("tipos_inscricao", lazy=True)
    )
    tipo_inscricao = db.relationship(
        "EventoInscricaoTipo", backref=db.backref("lotes_precos", lazy=True)
    )

    def __repr__(self):
        return f"<LoteTipoInscricao Lote={self.lote_id}, Tipo={self.tipo_inscricao_id}, Preço={self.preco}>"


# =================================
#            ARQUIVO BINÁRIO
# =================================
class ArquivoBinario(db.Model):
    """Modelo para armazenar arquivos binários no banco de dados."""

    __tablename__ = "arquivo_binario"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    conteudo = db.Column(db.LargeBinary, nullable=False)
    mimetype = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ArquivoBinario id={self.id} nome={self.nome}>"


# =================================
#            AUDIT LOG
# =================================
class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    submission_id = db.Column(
        db.Integer,
        db.ForeignKey("respostas_formulario.id", ondelete="CASCADE"),
        nullable=True,
    )
    event_type = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    usuario = db.relationship("Usuario")
    submission = db.relationship(
        "RespostaFormulario",
        backref=db.backref("audit_logs", passive_deletes=True),
    )

    def __repr__(self):
        return f"<AuditLog {self.user_id} {self.event_type} {self.submission_id}>"


class ParticipanteEvento(db.Model):
    """Modelo para associar participantes (usuários) a eventos."""
    __tablename__ = "participante_evento"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    data_inscricao = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="ativo")  # ativo, inativo, cancelado

    # Relacionamentos
    usuario = db.relationship("Usuario", backref=db.backref("participacoes_eventos", lazy=True))
    evento = db.relationship("Evento", backref=db.backref("participantes", lazy=True))

    def __init__(self, usuario_id, evento_id, status="ativo"):
        self.usuario_id = usuario_id
        self.evento_id = evento_id
        self.status = status

    def __repr__(self):
        return f"<ParticipanteEvento usuario_id={self.usuario_id} evento_id={self.evento_id}>"


class MonitorAgendamento(db.Model):
    """Modelo para associar monitores a agendamentos de visitas."""
    __tablename__ = "monitor_agendamento"

    id = db.Column(db.Integer, primary_key=True)
    monitor_id = db.Column(db.Integer, db.ForeignKey("monitor.id"), nullable=False)
    agendamento_id = db.Column(db.Integer, db.ForeignKey("agendamento_visita.id"), nullable=False)
    data_atribuicao = db.Column(db.DateTime, default=datetime.utcnow)
    tipo_distribuicao = db.Column(db.String(20), default="manual")  # manual, automatica
    status = db.Column(db.String(20), default="ativo")  # ativo, inativo, substituido
    observacoes = db.Column(db.Text, nullable=True)

    # Relacionamentos
    monitor = db.relationship("Monitor", backref=db.backref("agendamentos_atribuidos", lazy=True))
    agendamento = db.relationship("AgendamentoVisita", backref=db.backref("monitores_atribuidos", lazy=True))

    def __init__(self, monitor_id, agendamento_id, tipo_distribuicao="manual", status="ativo"):
        self.monitor_id = monitor_id
        self.agendamento_id = agendamento_id
        self.tipo_distribuicao = tipo_distribuicao
        self.status = status

    def __repr__(self):
        return f"<MonitorAgendamento monitor_id={self.monitor_id} agendamento_id={self.agendamento_id}>"


class PresencaAluno(db.Model):
    """Modelo para registrar presença/ausência de alunos pelos monitores."""
    __tablename__ = "presenca_aluno"

    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey("aluno_visitante.id"), nullable=False)
    monitor_id = db.Column(db.Integer, db.ForeignKey("monitor.id"), nullable=False)
    agendamento_id = db.Column(db.Integer, db.ForeignKey("agendamento_visita.id"), nullable=False)
    presente = db.Column(db.Boolean, default=False)
    data_registro = db.Column(db.DateTime, default=datetime.utcnow)
    metodo_confirmacao = db.Column(db.String(20), default="qr_code")  # qr_code, manual
    observacoes = db.Column(db.Text, nullable=True)

    # Relacionamentos
    aluno = db.relationship("AlunoVisitante", backref=db.backref("registros_presenca", lazy=True))
    monitor = db.relationship("Monitor", backref=db.backref("registros_presenca", lazy=True))
    agendamento = db.relationship("AgendamentoVisita", backref=db.backref("registros_presenca", lazy=True))

    def __init__(self, aluno_id, monitor_id, agendamento_id, presente=False, metodo_confirmacao="qr_code"):
        self.aluno_id = aluno_id
        self.monitor_id = monitor_id
        self.agendamento_id = agendamento_id
        self.presente = presente
        self.metodo_confirmacao = metodo_confirmacao

    def __repr__(self):
        return f"<PresencaAluno aluno_id={self.aluno_id} presente={self.presente}>"


class MaterialApoio(db.Model):
    """Materiais de apoio para alunos com necessidades especiais."""
    
    __tablename__ = "material_apoio"
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relações
    cliente = db.relationship("Cliente", backref=db.backref("materiais_apoio", lazy=True))
    
    def __init__(self, nome, descricao, cliente_id, ativo=True):
        self.nome = nome
        self.descricao = descricao
        self.cliente_id = cliente_id
        self.ativo = ativo
    
    def __repr__(self):
        return f"<MaterialApoio {self.nome} - Cliente {self.cliente_id}>"


# Tabela de associação para materiais de apoio selecionados por aluno
aluno_material_apoio_association = db.Table(
    "aluno_material_apoio_association",
    db.Column("aluno_id", db.Integer, db.ForeignKey("aluno_visitante.id"), primary_key=True),
    db.Column("material_id", db.Integer, db.ForeignKey("material_apoio.id"), primary_key=True),
)


class NecessidadeEspecial(db.Model):
    """Registro de necessidades especiais dos alunos visitantes."""
    
    __tablename__ = "necessidade_especial"
    
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey("aluno_visitante.id"), nullable=False, unique=True)
    tipo = db.Column(db.String(50), nullable=False)  # 'PCD' ou 'Neurodivergente'
    descricao = db.Column(db.Text, nullable=False)
    data_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relações
    aluno = db.relationship("AlunoVisitante", backref=db.backref("necessidade_especial", uselist=False, lazy=True))
    
    def __init__(self, aluno_id, tipo, descricao):
        self.aluno_id = aluno_id
        self.tipo = tipo
        self.descricao = descricao
    
    def get_tipo_display(self):
        """Retorna a descrição legível do tipo de necessidade especial."""
        tipos_display = {
            'pcd_fisica': 'PCD Física',
            'pcd_visual': 'PCD Visual',
            'pcd_auditiva': 'PCD Auditiva',
            'pcd_intelectual': 'PCD Intelectual',
            'neurodivergente_autismo': 'Neurodivergente - Autismo',
            'neurodivergente_tdah': 'Neurodivergente - TDAH',
            'neurodivergente_dislexia': 'Neurodivergente - Dislexia',
            'neurodivergente_outros': 'Neurodivergente - Outros',
            'outros': 'Outros'
        }
        return tipos_display.get(self.tipo, self.tipo.title())
    
    def __repr__(self):
        return f"<NecessidadeEspecial {self.tipo} - Aluno {self.aluno_id}>"






class DeclaracaoComparecimento(db.Model):
    """Modelo para declarações de comparecimento."""
    __tablename__ = "declaracao_comparecimento"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    
    # Configurações da declaração
    titulo = db.Column(db.String(200), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey("declaracao_template.id"), nullable=True)
    
    # Status e controle
    status = db.Column(db.String(20), default="pendente")  # pendente, liberada, emitida
    data_liberacao = db.Column(db.DateTime, nullable=True)
    data_emissao = db.Column(db.DateTime, nullable=True)
    liberado_por = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    
    # Configurações de acesso
    requer_checkin = db.Column(db.Boolean, default=True)
    liberacao_automatica = db.Column(db.Boolean, default=False)
    
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    cliente = db.relationship("Cliente", backref="declaracoes_comparecimento")
    evento = db.relationship("Evento", backref="declaracoes_comparecimento")
    usuario = db.relationship("Usuario", foreign_keys=[usuario_id], backref="declaracoes_recebidas")
    liberador = db.relationship("Usuario", foreign_keys=[liberado_por], backref="declaracoes_liberadas")
    template = db.relationship("DeclaracaoTemplate", backref="declaracoes")

    def __repr__(self):
        return f"<DeclaracaoComparecimento {self.titulo} - {self.usuario_id}>"





class ConfiguracaoCertificadoAvancada(db.Model):
    """Configurações avançadas para emissão de certificados."""
    __tablename__ = "config_certificado_avancada"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    
    # Configurações de liberação
    liberacao_individual = db.Column(db.Boolean, default=True)
    liberacao_geral = db.Column(db.Boolean, default=True)
    liberacao_simultanea = db.Column(db.Boolean, default=False)
    liberacao_automatica = db.Column(db.Boolean, default=False)
    
    # Critérios para certificado geral
    incluir_atividades_sem_inscricao = db.Column(db.Boolean, default=True)
    carga_horaria_minima = db.Column(db.Integer, default=0)
    percentual_presenca_minimo = db.Column(db.Integer, default=0)
    exigir_checkin_minimo = db.Column(db.Boolean, default=True)
    validar_oficinas_obrigatorias = db.Column(db.Boolean, default=False)
    
    # Configurações de acesso
    acesso_participante = db.Column(db.Boolean, default=True)
    acesso_admin = db.Column(db.Boolean, default=True)
    acesso_cliente = db.Column(db.Boolean, default=True)
    
    # Aprovação e notificações
    requer_aprovacao_manual = db.Column(db.Boolean, default=False)
    notificar_participante = db.Column(db.Boolean, default=True)
    notificar_admin = db.Column(db.Boolean, default=False)
    
    # Configurações de prazo
    prazo_liberacao_dias = db.Column(db.Integer, nullable=True)  # Dias após o evento
    data_limite_emissao = db.Column(db.DateTime, nullable=True)
    
    # Templates associados
    template_individual_id = db.Column(db.Integer, db.ForeignKey("certificado_template_avancado.id"), nullable=True)
    template_geral_id = db.Column(db.Integer, db.ForeignKey("certificado_template_avancado.id"), nullable=True)
    
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cliente = db.relationship("Cliente", backref="configs_certificado_avancadas")
    evento = db.relationship("Evento", backref="config_certificado_avancada", uselist=False)
    template_individual = db.relationship("CertificadoTemplateAvancado", foreign_keys=[template_individual_id])
    template_geral = db.relationship("CertificadoTemplateAvancado", foreign_keys=[template_geral_id])

    def __repr__(self):
        return f"<ConfiguracaoCertificadoAvancada Evento {self.evento_id}>"


class HistoricoCertificado(db.Model):
    """Histórico de certificados emitidos."""
    __tablename__ = "historico_certificado"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey("evento.id"), nullable=False)
    oficina_id = db.Column(db.Integer, db.ForeignKey("oficina.id"), nullable=True)
    
    tipo_certificado = db.Column(db.String(20), nullable=False)  # individual, geral
    template_usado_id = db.Column(db.Integer, db.ForeignKey("certificado_template_avancado.id"), nullable=True)
    
    # Dados do certificado
    titulo = db.Column(db.String(200), nullable=False)
    carga_horaria_total = db.Column(db.Integer, nullable=False)
    atividades_participadas = db.Column(db.JSON, nullable=True)  # Lista de atividades
    
    # Controle de emissão
    data_emissao = db.Column(db.DateTime, default=datetime.utcnow)
    emitido_por = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    arquivo_path = db.Column(db.String(500), nullable=True)
    hash_verificacao = db.Column(db.String(64), nullable=True)  # Para validação

    usuario = db.relationship("Usuario", foreign_keys=[usuario_id], backref="certificados_recebidos")
    evento = db.relationship("Evento", backref="certificados_emitidos")
    oficina = db.relationship("Oficina", backref="certificados_emitidos")
    template_usado = db.relationship("CertificadoTemplateAvancado", backref="certificados_gerados")
    emissor = db.relationship("Usuario", foreign_keys=[emitido_por], backref="certificados_emitidos")

    def __repr__(self):
        return f"<HistoricoCertificado {self.tipo_certificado} - {self.usuario_id}>"


class VariavelDinamica(db.Model):
    """Variáveis dinâmicas personalizadas para templates."""
    __tablename__ = "variavel_dinamica"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    nome = db.Column(db.String(50), nullable=False)  # Ex: NOME_INSTITUICAO
    descricao = db.Column(db.String(200), nullable=True)
    valor_padrao = db.Column(db.Text, nullable=True)
    tipo = db.Column(db.String(20), default="texto")  # texto, data, numero, lista
    opcoes = db.Column(db.JSON, nullable=True)  # Para tipo lista
    ativo = db.Column(db.Boolean, default=True)
    
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    cliente = db.relationship("Cliente", backref="variaveis_dinamicas")

    def __repr__(self):
        return f"<VariavelDinamica {self.nome}>"
