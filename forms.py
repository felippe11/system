from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, IntegerField, SelectMultipleField
from wtforms.validators import DataRequired, Optional

class TipoInscricaoEventoForm(FlaskForm):
    nome = StringField('Nome do Tipo de Inscrição', validators=[DataRequired()])
    preco = FloatField('Preço', validators=[DataRequired()])

class RegraInscricaoEventoForm(FlaskForm):
    tipo_inscricao_id = IntegerField('Tipo de Inscrição', validators=[DataRequired()])
    limite_oficinas = IntegerField('Limite de Oficinas', validators=[Optional()])
    oficinas_permitidas = SelectMultipleField('Oficinas Permitidas', coerce=int)
