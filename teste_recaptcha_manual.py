"""
Script para testar diferentes tipos de reCAPTCHA.
Este script cria uma página que testa tanto reCAPTCHA v2 Checkbox quanto v2 Invisible.
"""
from flask import Flask, render_template_string, request, jsonify
import os
import requests
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = "chave-secreta-para-teste"

# Template para teste manual sem Flask-WTF
test_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Teste Manual de reCAPTCHA</title>
    <script src="https://www.google.com/recaptcha/api.js" async defer></script>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .section { border: 1px solid #ddd; padding: 20px; margin-bottom: 20px; border-radius: 5px; }
        .error { color: red; }
        .success { color: green; }
        h2 { color: #333; }
        button { padding: 10px 15px; background: #4CAF50; color: white; border: none; cursor: pointer; border-radius: 4px; }
        input[type="text"] { padding: 8px; width: 100%; margin-bottom: 10px; }
        textarea { width: 100%; height: 100px; padding: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Teste de reCAPTCHA</h1>
        
        <div class="section">
            <h2>Informações das chaves</h2>
            <p><strong>Chave pública:</strong> {{ public_key }}</p>
            <p><strong>Comprimento chave pública:</strong> {{ public_key_len }} caracteres</p>
            <p><strong>Chave privada:</strong> {{ private_key_masked }}</p>
            <p><strong>Comprimento chave privada:</strong> {{ private_key_len }} caracteres</p>
        </div>

        <div class="section">
            <h2>1. Teste de reCAPTCHA v2 "Checkbox"</h2>
            <form id="form1" action="/verify" method="post">
                <input type="hidden" name="recaptcha_type" value="checkbox">
                <div class="g-recaptcha" data-sitekey="{{ public_key }}"></div>
                <br/>
                <button type="submit">Verificar</button>
            </form>
        </div>
        
        <div class="section">
            <h2>2. Teste de reCAPTCHA v2 "Invisible"</h2>
            <form id="form2" action="/verify" method="post">
                <input type="hidden" name="recaptcha_type" value="invisible">
                <button class="g-recaptcha" 
                        data-sitekey="{{ public_key }}" 
                        data-callback="onSubmitInvisible"
                        data-size="invisible">
                    Verificar (Invisível)
                </button>
            </form>
            <script>
                function onSubmitInvisible(token) {
                    document.getElementById("form2").submit();
                }
            </script>
        </div>
        
        <div class="section">
            <h2>3. Verificação manual</h2>
            <p>Cole o token do reCAPTCHA para verificação direta:</p>
            <textarea id="manualToken" placeholder="Cole o token do reCAPTCHA aqui"></textarea>
            <br/>
            <button onclick="verifyManually()">Verificar Token</button>
            <div id="manualResult" style="margin-top: 10px;"></div>
            
            <script>
                function verifyManually() {
                    const token = document.getElementById('manualToken').value.trim();
                    if (!token) {
                        document.getElementById('manualResult').innerHTML = 
                            '<span class="error">Insira um token válido</span>';
                        return;
                    }
                    
                    fetch('/verify-manual', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ token: token })
                    })
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('manualResult').innerHTML = 
                            `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                    });
                }
            </script>
        </div>
        
        {% if result %}
        <div class="section" style="background-color: {{ 'rgba(200, 255, 200, 0.3)' if success else 'rgba(255, 200, 200, 0.3)' }};">
            <h2>Resultado da verificação</h2>
            <p><strong>Status:</strong> <span class="{{ 'success' if success else 'error' }}">{{ 'Sucesso' if success else 'Falha' }}</span></p>
            <p><strong>Detalhes:</strong></p>
            <pre>{{ result }}</pre>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    public_key = os.getenv("RECAPTCHA_PUBLIC_KEY", "")
    private_key = os.getenv("RECAPTCHA_PRIVATE_KEY", "")
    
    return render_template_string(
        test_template,
        public_key=public_key,
        public_key_len=len(public_key),
        private_key_masked="*" * len(private_key) if private_key else "Não definida",
        private_key_len=len(private_key),
        result=None,
        success=False
    )

@app.route('/verify', methods=['POST'])
def verify():
    recaptcha_type = request.form.get('recaptcha_type', '')
    token = request.form.get('g-recaptcha-response', '')
    
    if not token:
        return render_template_string(
            test_template,
            public_key=os.getenv("RECAPTCHA_PUBLIC_KEY", ""),
            public_key_len=len(os.getenv("RECAPTCHA_PUBLIC_KEY", "")),
            private_key_masked="*" * len(os.getenv("RECAPTCHA_PRIVATE_KEY", "")),
            private_key_len=len(os.getenv("RECAPTCHA_PRIVATE_KEY", "")),
            result="Token não fornecido!",
            success=False
        )
    
    # Verificar com a API do Google
    result, success = verify_recaptcha(token)
    
    return render_template_string(
        test_template,
        public_key=os.getenv("RECAPTCHA_PUBLIC_KEY", ""),
        public_key_len=len(os.getenv("RECAPTCHA_PUBLIC_KEY", "")),
        private_key_masked="*" * len(os.getenv("RECAPTCHA_PRIVATE_KEY", "")),
        private_key_len=len(os.getenv("RECAPTCHA_PRIVATE_KEY", "")),
        result=result,
        success=success
    )

@app.route('/verify-manual', methods=['POST'])
def verify_manual():
    data = request.json
    token = data.get('token', '')
    
    if not token:
        return jsonify({'error': 'Token não fornecido!'})
    
    result, success = verify_recaptcha(token)
    return jsonify({'result': result, 'success': success})

def verify_recaptcha(token):
    """Verifica o token do reCAPTCHA diretamente com a API do Google"""
    try:
        private_key = os.getenv("RECAPTCHA_PRIVATE_KEY", "")
        
        if not private_key:
            return "Chave privada não configurada!", False
        
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={
                'secret': private_key,
                'response': token
            }
        )
        
        result = response.json()
        return str(result), result.get('success', False)
        
    except Exception as e:
        return f"Erro ao verificar: {str(e)}", False

if __name__ == "__main__":
    # Usar porta 5051 para evitar conflitos
    app.run(debug=True, port=5051)
