"""
Script para depurar problemas com o reCAPTCHA.
Execute com: python debug_recaptcha.py
"""
import logging
import os

from flask import Flask, render_template_string, request
from flask_wtf import FlaskForm, RecaptchaField
from wtforms import SubmitField
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Carrega as variáveis de ambiente
load_dotenv()

app = Flask(__name__)

# Configuração básica
app.config["SECRET_KEY"] = "chave-secreta-para-teste"
app.config["RECAPTCHA_PUBLIC_KEY"] = os.getenv("RECAPTCHA_PUBLIC_KEY")
app.config["RECAPTCHA_PRIVATE_KEY"] = os.getenv("RECAPTCHA_PRIVATE_KEY")
app.config["RECAPTCHA_DATA_ATTRS"] = {"theme": "light", "size": "normal"}
# Configurações adicionais que podem ajudar
app.config["RECAPTCHA_OPTIONS"] = {"hl": "pt-BR"}
# Use isso se você estiver usando reCAPTCHA v2 Invisible
# app.config["RECAPTCHA_USE_SSL"] = False

# Informações de debug
logger.info("DEBUG: RECAPTCHA_PUBLIC_KEY = %s", app.config["RECAPTCHA_PUBLIC_KEY"])
logger.info(
    "DEBUG: RECAPTCHA_PRIVATE_KEY = %s",
    "*" * len(app.config["RECAPTCHA_PRIVATE_KEY"])
    if app.config["RECAPTCHA_PRIVATE_KEY"]
    else "Não definida",
)
logger.info(
    "DEBUG: Chave pública parece ser v3? %s",
    app.config["RECAPTCHA_PUBLIC_KEY"].startswith("6Lf")
    if app.config["RECAPTCHA_PUBLIC_KEY"]
    else "N/A",
)
logger.info(
    "DEBUG: Comprimento da chave pública: %s",
    len(app.config["RECAPTCHA_PUBLIC_KEY"])
    if app.config["RECAPTCHA_PUBLIC_KEY"]
    else 0,
)
logger.info(
    "DEBUG: Comprimento da chave privada: %s",
    len(app.config["RECAPTCHA_PRIVATE_KEY"])
    if app.config["RECAPTCHA_PRIVATE_KEY"]
    else 0,
)

# Formulário de teste simples
class TestForm(FlaskForm):
    recaptcha = RecaptchaField()
    submit = SubmitField("Enviar")

# Template simples para testar
test_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Teste de reCAPTCHA</title>
</head>
<body>
    <h1>Teste de reCAPTCHA</h1>
    
    <form method="POST">
        {{ form.csrf_token }}
        <div>
            {{ form.recaptcha }}
            {% if form.recaptcha.errors %}
                <div style="color: red;">
                    {% for error in form.recaptcha.errors %}
                        {{ error }}
                    {% endfor %}
                </div>
            {% endif %}
        </div>
        <br>
        {{ form.submit }}
    </form>
    
    {% if resultado %}
        <div style="margin-top: 20px; padding: 10px; background-color: {% if success %}#d4edda{% else %}#f8d7da{% endif %};">
            {{ resultado }}
        </div>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def test_recaptcha():
    form = TestForm()
    resultado = None
    success = False
    
    if request.method == "POST":
        if form.validate_on_submit():
            resultado = "reCAPTCHA validado com sucesso!"
            success = True
        else:
            resultado = f"Erro na validação do reCAPTCHA: {form.errors}"
            logger.info("DEBUG: Erros do formulário: %s", form.errors)
    
    return render_template_string(
        test_template, 
        form=form, 
        resultado=resultado,
        success=success
    )

if __name__ == "__main__":
    # Usar porta diferente para evitar conflito
    app.run(debug=True, port=5050)
