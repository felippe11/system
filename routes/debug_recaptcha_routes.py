
from flask import Blueprint, render_template, request, jsonify, current_app
import requests

debug_recaptcha_routes = Blueprint('debug_recaptcha_routes', __name__)

@debug_recaptcha_routes.route('/debug/recaptcha-test')
def recaptcha_test():
    """Página de diagnóstico para o reCAPTCHA v3"""
    return render_template('recaptcha_test.html')
    
@debug_recaptcha_routes.route('/debug/recaptcha-simples')
def teste_recaptcha_simples():
    """Página de diagnóstico simples para o reCAPTCHA v3"""
    return render_template('teste_recaptcha_simples.html')
    
@debug_recaptcha_routes.route('/debug/recaptcha-ultra-simples')
def teste_recaptcha_ultra_simples():
    """Página de diagnóstico ultra simples para o reCAPTCHA v3 (sem framework)"""
    return render_template('teste_recaptcha_ultra_simples.html')
    
@debug_recaptcha_routes.route('/debug/config-recaptcha')
def config_recaptcha():
    """Exibe informações de configuração do reCAPTCHA"""
    import sys
    import platform
    import flask
    
    # Verificar se as chaves do reCAPTCHA estão presentes nas variáveis de ambiente
    import os
    env_public_key = os.environ.get('RECAPTCHA_PUBLIC_KEY', 'Não definida no ambiente')
    env_private_key = os.environ.get('RECAPTCHA_PRIVATE_KEY', 'Não definida no ambiente')
    
    # Verificar a configuração atual do aplicativo
    config_public_key = current_app.config.get('RECAPTCHA_PUBLIC_KEY', 'Não definida na configuração')
    config_private_key = current_app.config.get('RECAPTCHA_PRIVATE_KEY', 'Não definida na configuração')
    
    # Coletar informações do sistema
    system_info = {
        'Sistema Operacional': platform.system() + ' ' + platform.release(),
        'Python': sys.version,
        'Flask': flask.__version__,
        'Ambiente': os.environ.get('FLASK_ENV', 'não definido')
    }
    
    # Verificar se o reCAPTCHA pode ser acessado
    import requests
    recaptcha_accessible = False
    try:
        r = requests.get('https://www.google.com/recaptcha/api.js', timeout=5)
        recaptcha_accessible = r.status_code == 200
    except:
        pass
    
    return render_template(
        'recaptcha_config.html',
        system_info=system_info,
        env_public_key=env_public_key[:8] + '...' if len(env_public_key) > 8 and env_public_key != 'Não definida no ambiente' else env_public_key,
        env_private_key=env_private_key[:8] + '...' if len(env_private_key) > 8 and env_private_key != 'Não definida no ambiente' else env_private_key,
        config_public_key=config_public_key[:8] + '...' if len(config_public_key) > 8 and config_public_key != 'Não definida na configuração' else config_public_key,
        config_private_key=config_private_key[:8] + '...' if len(config_private_key) > 8 and config_private_key != 'Não definida na configuração' else config_private_key,
        recaptcha_accessible=recaptcha_accessible
    )

@debug_recaptcha_routes.route('/debug/teste-recaptcha', methods=['POST'])
def processar_teste_recaptcha():
    """Processa o formulário de teste do reCAPTCHA v3"""
    token = request.form.get('g-recaptcha-response', '')
    
    current_app.logger.info(f"Token de teste recebido: {token[:20] if token else ''}... (Tamanho: {len(token)})")
    
    if not token:
        return jsonify({
            'success': False,
            'error': 'Token não encontrado na requisição',
            'details': {
                'form_data': {k: v for k, v in request.form.items() if k != 'csrf_token'}
            }
        })
    
    # Mostrar todos os campos do formulário para diagnóstico
    form_data = {k: v for k, v in request.form.items() if k not in ['g-recaptcha-response', 'csrf_token']}
    current_app.logger.debug(f"Outros campos do formulário: {form_data}")
    
    return jsonify({
        'success': True,
        'message': 'Token do reCAPTCHA recebido com sucesso',
        'tokenLength': len(token)
    })

@debug_recaptcha_routes.route('/debug/verificar-recaptcha', methods=['POST'])
def verificar_recaptcha():
    """API para verificar um token do reCAPTCHA v3"""
    data = request.json
    token = data.get('token', '')
    client_info = data.get('clientInfo', {})
    
    # Registrar informações do cliente para diagnóstico
    current_app.logger.info(f"Teste de reCAPTCHA solicitado por: {client_info}")
    
    if not token:
        return jsonify({
            'success': False,
            'error': 'Token não fornecido',
            'details': {
                'tokenReceived': False,
                'clientInfo': client_info
            }
        })
    
    # Verificação do token com a API do Google
    recaptcha_secret = current_app.config.get('RECAPTCHA_PRIVATE_KEY', '')
    verify_url = 'https://www.google.com/recaptcha/api/siteverify'
    
    if not recaptcha_secret:
        return jsonify({
            'success': False,
            'error': 'Chave privada do reCAPTCHA não configurada no servidor',
            'details': {
                'serverConfig': {
                    'privateKeyConfigured': False,
                    'publicKeyConfigured': bool(current_app.config.get('RECAPTCHA_PUBLIC_KEY', ''))
                }
            }
        })
        
    try:
        # Realizar a solicitação para o Google
        verify_data = {
            'secret': recaptcha_secret,
            'response': token,
            'remoteip': request.remote_addr
        }
        
        r = requests.post(verify_url, data=verify_data)
        
        # Verificar resposta HTTP
        if r.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'Erro na API do Google reCAPTCHA (HTTP {r.status_code})',
                'details': {
                    'httpStatus': r.status_code,
                    'responseText': r.text
                }
            })
        
        # Analisar resultado
        result = r.json()
        current_app.logger.debug(f"Resposta da API do reCAPTCHA: {result}")
        
        if result.get('success'):
            score = result.get('score', 0.0)
            action = result.get('action', '')
            
            return jsonify({
                'success': True,
                'score': score,
                'action': action,
                'details': {
                    'googleResponse': result,
                    'tokenLength': len(token),
                    'clientInfo': client_info
                }
            })
        else:
            error_codes = result.get('error-codes', [])
            return jsonify({
                'success': False,
                'error': f'Erro na validação: {", ".join(error_codes)}',
                'details': {
                    'googleResponse': result,
                    'errorCodes': error_codes,
                    'tokenLength': len(token)
                }
            })
    
    except Exception as e:
        current_app.logger.exception(f"Exceção ao verificar reCAPTCHA: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erro no servidor: {str(e)}',
            'details': {
                'exceptionType': type(e).__name__,
                'exceptionMessage': str(e)
            }
        })

