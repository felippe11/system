
from flask import Blueprint, render_template, request, jsonify, current_app
import requests
import json

teste_recaptcha_routes = Blueprint('teste_recaptcha_routes', __name__)

@teste_recaptcha_routes.route('/debug/recaptcha-simples')
def teste_recaptcha_simples():
    """Página de diagnóstico simples para o reCAPTCHA v3"""
    return render_template('teste_recaptcha_simples.html')

@teste_recaptcha_routes.route('/debug/teste-recaptcha', methods=['POST'])
def processar_teste_recaptcha():
    """Processa o formulário de teste do reCAPTCHA v3"""
    token = request.form.get('g-recaptcha-response', '')
    
    current_app.logger.debug(f"Token de teste recebido: {token[:20]}... (Tamanho: {len(token)})")
    
    if not token:
        return jsonify({
            'success': False,
            'error': 'Token não encontrado na requisição'
        })
    
    # Mostrar todos os campos do formulário para diagnóstico
    form_data = {k: v for k, v in request.form.items() if k != 'g-recaptcha-response'}
    current_app.logger.debug(f"Outros campos do formulário: {form_data}")
    
    return jsonify({
        'success': True,
        'message': 'Token do reCAPTCHA recebido com sucesso',
        'tokenLength': len(token)
    })

@teste_recaptcha_routes.route('/debug/verificar-token', methods=['POST'])
def verificar_token():
    """Verifica um token do reCAPTCHA v3"""
    data = request.json
    token = data.get('token', '')
    
    current_app.logger.debug(f"Verificando token: {token[:20]}... (Tamanho: {len(token)})")
    
    if not token:
        return jsonify({
            'success': False,
            'error': 'Token não encontrado na requisição'
        })
    
    # Verificação do token com a API do Google
    recaptcha_secret = current_app.config.get('RECAPTCHA_PRIVATE_KEY', '')
    
    if not recaptcha_secret:
        return jsonify({
            'success': False,
            'error': 'Chave privada do reCAPTCHA não configurada no servidor'
        })
    
    verify_url = 'https://www.google.com/recaptcha/api/siteverify'
    
    try:
        r = requests.post(verify_url, data={
            'secret': recaptcha_secret,
            'response': token,
            'remoteip': request.remote_addr
        })
        
        if r.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'Erro na API do Google (HTTP {r.status_code})'
            })
        
        result = r.json()
        current_app.logger.debug(f"Resposta da API: {result}")
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'score': result.get('score', 0),
                'action': result.get('action', ''),
                'details': result
            })
        else:
            error_codes = result.get('error-codes', [])
            return jsonify({
                'success': False,
                'error': f'Erro na validação: {", ".join(error_codes)}',
                'details': result
            })
            
    except Exception as e:
        current_app.logger.exception(f"Exceção ao verificar token: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erro no servidor: {str(e)}'
        })

