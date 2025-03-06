import os
import uuid
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from extensions import db  # Se você inicializa o SQLAlchemy em 'extensions.py'
from sqlalchemy.orm import relationship  # Adicione esta linha!
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email


# =================================
#             CLIENTE
# =================================
class EditarClienteForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    senha = PasswordField('Nova Senha')
    submit = SubmitField('Salvar Alterações')
# =================================
#             USUÁRIO
# =================================
class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuario'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    formacao = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default='participante')
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=True)  # ✅ Alterado para permitir NULL

    
    cliente = db.relationship('Cliente', backref=db.backref('usuarios', lazy=True))
    # NOVOS CAMPOS PARA LOCAIS DE ATUAÇÃO:
    estados = db.Column(db.String(255), nullable=True)   # Ex.: "SP,RJ,MG"
    cidades = db.Column(db.String(255), nullable=True)   # Ex.: "São Paulo,Rio de Janeiro,Belo Horizonte"

    def verificar_senha(self, senha):
        return check_password_hash(self.senha, senha)

    def __repr__(self):
        return f"<Usuario {self.nome}>"
    
    def is_superuser(self):
        return self.tipo == "superadmin"

    def is_cliente(self):
        return self.tipo == "cliente"




# =================================
#           CONFIGURAÇÃO
# =================================
class Configuracao(db.Model):
    __tablename__ = 'configuracao'

    id = db.Column(db.Integer, primary_key=True)
    permitir_checkin_global = db.Column(db.Boolean, default=False)
    habilitar_feedback = db.Column(db.Boolean, default=False)
    habilitar_certificado_individual = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Configuracao permitir_checkin_global={self.permitir_checkin_global}>"


# =================================
#          MINISTRANTE
# =================================
class Ministrante(db.Model, UserMixin):
    __tablename__ = 'ministrante'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    formacao = db.Column(db.String(255), nullable=False)
    areas_atuacao = db.Column(db.String(255), nullable=False)
    cpf = db.Column(db.String(20), unique=True, nullable=False)
    pix = db.Column(db.String(255), nullable=False)
    cidade = db.Column(db.String(255), nullable=False)
    estado = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=True)  # ✅ Relacionamento com Cliente
    cliente = db.relationship("Cliente", backref="ministrantes")  # ✅ Relacionamento reverso


    @property
    def tipo(self):
        return 'ministrante'

    def __repr__(self):
        return f"<Ministrante {self.nome}>"


# ... (outras importações permanecem iguais)

# =================================
#             OFICINA
# =================================
class Oficina(db.Model):
    __tablename__ = 'oficina'
    
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    ministrante_id = db.Column(db.Integer, db.ForeignKey('ministrante.id'), nullable=True)
    ministrante_obj = db.relationship("Ministrante", backref="oficinas", lazy=True)
  
    vagas = db.Column(db.Integer, nullable=False)
    carga_horaria = db.Column(db.String(10), nullable=False)
    estado = db.Column(db.String(2), nullable=False)
    cidade = db.Column(db.String(100), nullable=False)
    qr_code = db.Column(db.String(255), nullable=True)

    opcoes_checkin = db.Column(db.String(255), nullable=True)  # Ex: "palavra1,palavra2,palavra3,palavra4,palavra5"
    palavra_correta = db.Column(db.String(50), nullable=True)
    
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=True)  # ✅ Adicionado
    cliente = db.relationship("Cliente", back_populates="oficinas")  # ✅ Corrigido para `back_populates`

    dias = db.relationship('OficinaDia', back_populates="oficina", lazy=True, cascade="all, delete-orphan")

    def __init__(self, titulo, descricao, ministrante_id, vagas, carga_horaria, estado, cidade, cliente_id=None, qr_code=None):
        self.titulo = titulo
        self.descricao = descricao
        self.ministrante_id = ministrante_id
        self.vagas = vagas
        self.carga_horaria = carga_horaria
        self.estado = estado
        self.cidade = cidade
        self.qr_code = qr_code
        self.cliente_id = cliente_id  # ✅ Adicionando o cliente_id corretamente

    def __repr__(self):
        return f"<Oficina {self.titulo}>"


# =================================
#          OFICINA DIA
# =================================
class OficinaDia(db.Model):
    __tablename__ = 'oficinadia'

    id = db.Column(db.Integer, primary_key=True)
    oficina_id = db.Column(db.Integer, db.ForeignKey('oficina.id'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    horario_inicio = db.Column(db.String(5), nullable=False)
    horario_fim = db.Column(db.String(5), nullable=False)
    palavra_chave_manha = db.Column(db.String(50), nullable=True)
    palavra_chave_tarde = db.Column(db.String(50), nullable=True)

    oficina = db.relationship('Oficina', back_populates="dias")

    def __repr__(self):
        return f"<OficinaDia {self.data} {self.horario_inicio}-{self.horario_fim}>"


# =================================
#           INSCRIÇÃO
# =================================
class Inscricao(db.Model):
    __tablename__ = 'inscricao'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    oficina_id = db.Column(db.Integer, db.ForeignKey('oficina.id'))
    
    # Novo campo:
    qr_code_token = db.Column(db.String(100), unique=True, nullable=True)

    checkin_attempts = db.Column(db.Integer, default=0)
    
    usuario = db.relationship('Usuario', backref=db.backref('inscricoes', lazy='joined'))  # Adicionar lazy loading
    oficina = db.relationship('Oficina', backref='inscritos')
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False) 
    
    def __init__(self, usuario_id, oficina_id):
        self.usuario_id = usuario_id
        self.oficina_id = oficina_id
        # Exemplo: usar uuid4
        self.qr_code_token = str(uuid.uuid4())
    
    def __repr__(self):
        return f"<Inscricao Usuario: {self.usuario_id} Oficina: {self.oficina_id}>"
    
    


# =================================
#            CHECKIN
# =================================
class Checkin(db.Model):
    __tablename__ = 'checkin'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    oficina_id = db.Column(db.Integer, db.ForeignKey('oficina.id'), nullable=False)
    data_hora = db.Column(db.DateTime, default=datetime.utcnow)
    palavra_chave = db.Column(db.String(50), nullable=False)

    usuario = db.relationship('Usuario', backref=db.backref('checkins', lazy=True))
    oficina = db.relationship('Oficina', backref=db.backref('checkins', lazy=True))

    def __repr__(self):
        return f"<Checkin Usuario: {self.usuario_id}, Oficina: {self.oficina_id}, Data: {self.data_hora}>"


# =================================
#            FEEDBACK
# =================================
class Feedback(db.Model):
    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    ministrante_id = db.Column(db.Integer, db.ForeignKey('ministrante.id'), nullable=True)
    oficina_id = db.Column(db.Integer, db.ForeignKey('oficina.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # Nota de 1 a 5
    comentario = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship('Usuario', backref='feedbacks')
    ministrante = db.relationship('Ministrante', backref='feedbacks')
    oficina = db.relationship('Oficina', backref='feedbacks')

    def __repr__(self):
        return f"<Feedback id={self.id} " \
               f"Usuario={self.usuario_id if self.usuario_id else 'N/A'} " \
               f"Ministrante={self.ministrante_id if self.ministrante_id else 'N/A'} " \
               f"Oficina={self.oficina_id}>"


# =================================
#       MATERIAL DA OFICINA
# =================================
class MaterialOficina(db.Model):
    __tablename__ = 'material_oficina'

    id = db.Column(db.Integer, primary_key=True)
    oficina_id = db.Column(db.Integer, db.ForeignKey('oficina.id'), nullable=False)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    caminho_arquivo = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    oficina = db.relationship('Oficina', backref='materiais')

    def __repr__(self):
        return f"<MaterialOficina id={self.id}, arquivo={self.nome_arquivo}>"
    


# =================================
#       RELATÓRIO DA OFICINA
# =================================
class RelatorioOficina(db.Model):
    __tablename__ = 'relatorio_oficina'

    id = db.Column(db.Integer, primary_key=True)
    oficina_id = db.Column(db.Integer, db.ForeignKey('oficina.id'), nullable=False)
    ministrante_id = db.Column(db.Integer, db.ForeignKey('ministrante.id'), nullable=False)

    metodologia = db.Column(db.Text, nullable=True)
    resultados = db.Column(db.Text, nullable=True)
    fotos_videos_path = db.Column(db.String(255), nullable=True)
    enviado_em = db.Column(db.DateTime, default=datetime.utcnow)

    oficina = db.relationship(
        'Oficina',
        backref=db.backref('relatorios_oficina', lazy=True)
    )
    ministrante = db.relationship(
        'Ministrante',
        backref=db.backref('relatorios_ministrante', lazy=True)
    )

    def __repr__(self):
        return f"<RelatorioOficina oficina_id={self.oficina_id} ministrante_id={self.ministrante_id}>"

class Cliente(db.Model, UserMixin):
    __tablename__ = 'cliente'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False) 
    ativo = db.Column(db.Boolean, default=True)  # Habilitação pelo superusuário
    tipo = db.Column(db.String(20), default='cliente')  # Define o tipo do usuário
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=True)  # ✅ Adicionando relação com Cliente

     # Relacionamento com Oficina
    oficinas = db.relationship("Oficina", back_populates="cliente")  # ✅ Agora usa `back_populates`
    
    # Novos campos (caminho das imagens):
    logo_certificado = db.Column(db.String(255), nullable=True)       # Logo
    fundo_certificado = db.Column(db.String(255), nullable=True)      # Fundo do certificado
    assinatura_certificado = db.Column(db.String(255), nullable=True) # Assinatura

    
    def is_active(self):
        """Retorna True se o cliente está ativo."""
        return self.ativo
    def get_id(self):
        """Retorna o ID do cliente como string, necessário para Flask-Login."""
        return str(self.id)

class LinkCadastro(db.Model):
    __tablename__ = 'link_cadastro'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    token = db.Column(db.String(36), unique=True, nullable=False, default=str(uuid.uuid4()))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    cliente = db.relationship('Cliente', backref=db.backref('links_cadastro', lazy=True))

    def __repr__(self):
        return f"<LinkCadastro cliente_id={self.cliente_id}, token={self.token}>"
    

from extensions import db

class Formulario(db.Model):
    __tablename__ = 'formularios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=True)  # Se cada cliente puder ter seus próprios formulários
    
    cliente = db.relationship('Cliente', backref=db.backref('formularios', lazy=True))
    campos = db.relationship('CampoFormulario', backref='formulario', lazy=True, cascade="all, delete-orphan")
    respostas = db.relationship("RespostaFormulario", back_populates="formulario", lazy=True)

    def __repr__(self):
        return f"<Formulario {self.nome}>"

class CampoFormulario(db.Model):
    __tablename__ = 'campos_formulario'

    id = db.Column(db.Integer, primary_key=True)
    formulario_id = db.Column(db.Integer, db.ForeignKey('formularios.id'), nullable=False)
    nome = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # Exemplo: texto, número, arquivo, dropdown
    opcoes = db.Column(db.Text, nullable=True)  # Para dropdowns/checklists (valores separados por vírgula)
    obrigatorio = db.Column(db.Boolean, default=False)
    tamanho_max = db.Column(db.Integer, nullable=True)  # Para limitar caracteres
    regex_validacao = db.Column(db.String(255), nullable=True)  # Validação customizada

    def __repr__(self):
        return f"<Campo {self.nome} ({self.tipo})>"

class RespostaFormulario(db.Model):
    __tablename__ = 'respostas_formulario'

    id = db.Column(db.Integer, primary_key=True)
    formulario_id = db.Column(db.Integer, db.ForeignKey('formularios.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    data_submissao = db.Column(db.DateTime, default=datetime.utcnow)
    
    # NOVA COLUNA PARA STATUS
    status_avaliacao = db.Column(db.String(50), nullable=True, default='Não Avaliada')

    formulario = db.relationship("Formulario", back_populates="respostas", lazy=True)
    usuario = db.relationship('Usuario', backref=db.backref('respostas', lazy=True))

    def __repr__(self):
        return f"<RespostaFormulario ID {self.id} - Formulário {self.formulario_id} - Usuário {self.usuario_id}>"

class RespostaCampo(db.Model):
    __tablename__ = 'respostas_campo'

    id = db.Column(db.Integer, primary_key=True)
    resposta_formulario_id = db.Column(db.Integer, db.ForeignKey('respostas_formulario.id'), nullable=False)
    campo_id = db.Column(db.Integer, db.ForeignKey('campos_formulario.id'), nullable=False)
    valor = db.Column(db.Text, nullable=False)

    resposta_formulario = db.relationship('RespostaFormulario', backref=db.backref('respostas_campos', lazy=True))
    campo = db.relationship('CampoFormulario', backref=db.backref('respostas', lazy=True))

    def __repr__(self):
        return f"<RespostaCampo ID {self.id} - Campo {self.campo_id} - Valor {self.valor}>"
    
# models.py
class ConfiguracaoCliente(db.Model):
    __tablename__ = 'configuracao_cliente'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    
    permitir_checkin_global = db.Column(db.Boolean, default=False)
    habilitar_feedback = db.Column(db.Boolean, default=False)
    habilitar_certificado_individual = db.Column(db.Boolean, default=False)
    
    # Relacionamento com o cliente (opcional se quiser acessar .cliente)
    cliente = db.relationship("Cliente", backref=db.backref("configuracao_cliente", uselist=False))
    
class FeedbackCampo(db.Model):
    __tablename__ = 'feedback_campo'

    id = db.Column(db.Integer, primary_key=True)
    resposta_campo_id = db.Column(db.Integer, db.ForeignKey('respostas_campo.id'), nullable=False)
    ministrante_id = db.Column(db.Integer, db.ForeignKey('ministrante.id'), nullable=False)

    texto_feedback = db.Column(db.Text, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    resposta_campo = db.relationship('RespostaCampo', backref=db.backref('feedbacks_campo', lazy=True))
    ministrante = db.relationship('Ministrante', backref=db.backref('feedbacks_campo', lazy=True))

    def __repr__(self):
        return f"<FeedbackCampo id={self.id} resposta_campo={self.resposta_campo_id} ministrante={self.ministrante_id}>"


