import os
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
# ATENÇÃO: Escolha de onde vai importar o db e mantenha um único import!
from extensions import db  # Se você inicializa o SQLAlchemy em 'extensions.py'


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

    def verificar_senha(self, senha):
        return check_password_hash(self.senha, senha)

    def __repr__(self):
        return f"<Usuario {self.nome}>"


# =================================
#           CONFIGURAÇÃO
# =================================
class Configuracao(db.Model):
    __tablename__ = 'configuracao'

    id = db.Column(db.Integer, primary_key=True)
    permitir_checkin_global = db.Column(db.Boolean, default=False)
    # Se precisar manter habilitar_feedback
    habilitar_feedback = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Configuracao permitir_checkin_global={self.permitir_checkin_global}>"


# =================================
#             OFICINA
# =================================
class Oficina(db.Model):
    __tablename__ = 'oficina'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    ministrante = db.Column(db.String(100), nullable=False)
    vagas = db.Column(db.Integer, nullable=False)
    carga_horaria = db.Column(db.String(10), nullable=False)
    estado = db.Column(db.String(2), nullable=False)  # Ex.: 'PA', 'SP'...
    cidade = db.Column(db.String(100), nullable=False)
    qr_code = db.Column(db.String(255), nullable=True)

    def __init__(self, titulo, descricao, ministrante, vagas, carga_horaria, estado, cidade, qr_code=None):
        self.titulo = titulo
        self.descricao = descricao
        self.ministrante = ministrante
        self.vagas = vagas
        self.carga_horaria = carga_horaria
        self.estado = estado.upper()  # Garante que a sigla fique maiúscula
        self.cidade = cidade
        self.qr_code = qr_code

    def __repr__(self):
        return f"<Oficina {self.titulo}>"

    def delete_qr_code(self):
        """Deleta o arquivo de QR Code (se existir) e limpa o campo no banco."""
        if self.qr_code and os.path.exists(self.qr_code):
            os.remove(self.qr_code)
            print(f"QR Code removido: {self.qr_code}")
            self.qr_code = None


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

    oficina = db.relationship('Oficina', backref=db.backref('dias', lazy=True))

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

    usuario = db.relationship('Usuario', backref='inscricoes')
    oficina = db.relationship('Oficina', backref='inscritos')

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
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    oficina_id = db.Column(db.Integer, db.ForeignKey('oficina.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)   # Nota de 1 a 5
    comentario = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship('Usuario', backref='feedbacks')
    oficina = db.relationship('Oficina', backref='feedbacks')

    def __repr__(self):
        return f"<Feedback id={self.id} Usuario={self.usuario_id} Oficina={self.oficina_id}>"


# =================================
#          MINISTRANTE
# =================================
class Ministrante(db.Model):
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

    def __repr__(self):
        return f"<Ministrante {self.nome}>"
