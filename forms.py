from flask_wtf import FlaskForm, RecaptchaField
from wtforms import (
    StringField,
    FloatField,
    IntegerField,
    SelectMultipleField,
    PasswordField,
    SubmitField,
)
from wtforms.validators import DataRequired, Optional, Email

class TipoInscricaoEventoForm(FlaskForm):
    nome = StringField('Nome do Tipo de Inscrição', validators=[DataRequired()])
    preco = FloatField('Preço', validators=[DataRequired()])

class RegraInscricaoEventoForm(FlaskForm):
    tipo_inscricao_id = IntegerField('Tipo de Inscrição', validators=[DataRequired()])
    limite_oficinas = IntegerField('Limite de Oficinas', validators=[Optional()])
    oficinas_permitidas = SelectMultipleField('Oficinas Permitidas', coerce=int)


class EditarClienteForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    senha = PasswordField('Nova Senha')
    submit = SubmitField('Salvar Alterações')


class PublicClienteForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired()])
    # Não utilizamos RecaptchaField para v3, a validação é feita manualmente
