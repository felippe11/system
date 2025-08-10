from flask_wtf import FlaskForm, RecaptchaField
from wtforms import (
    StringField,
    FloatField,
    IntegerField,
    SelectMultipleField,
    PasswordField,
    SubmitField,
)
from wtforms.validators import DataRequired, Optional, Email, Length, EqualTo

class TipoInscricaoEventoForm(FlaskForm):
    nome = StringField('Nome do Tipo de Inscrição', validators=[DataRequired()])
    preco = FloatField('Preço', validators=[DataRequired()])

class RegraInscricaoEventoForm(FlaskForm):
    tipo_inscricao_id = IntegerField('Tipo de Inscrição', validators=[DataRequired()])
    limite_oficinas = IntegerField('Limite de Oficinas', validators=[Optional()])
    oficinas_permitidas = SelectMultipleField('Oficinas Permitidas', coerce=int)

    def __init__(self, oficinas_choices=None, *args, **kwargs):
        """Permite injetar escolhas para as oficinas permitidas.

        Parameters
        ----------
        oficinas_choices: list[tuple[int, str]] | None
            Lista de pares ``(id, nome)`` das oficinas disponíveis.
        """
        super().__init__(*args, **kwargs)
        self.oficinas_permitidas.choices = oficinas_choices or []


class EditarClienteForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    senha = PasswordField('Nova Senha')
    submit = SubmitField('Salvar Alterações')


class PublicClienteForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired(), Length(min=8)])
    confirmacao_senha = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('senha')])
    # Não utilizamos RecaptchaField para v3, a validação é feita manualmente
