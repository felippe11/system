# routes/auth_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
import pyotp
import logging

from models import Inscricao
from models.user import Usuario, Ministrante, Cliente, PasswordResetToken
from extensions import login_manager, db
from utils import enviar_email
from forms import PublicClienteForm
from utils.security import password_is_strong

auth_routes = Blueprint(
    'auth_routes',
    __name__,
    template_folder="../templates/auth"
)

logger = logging.getLogger(__name__)

# =======================================
# Função de carregamento de usuário
# =======================================
@login_manager.user_loader
def load_user(user_id):
    user_type = session.get('user_type')

    if user_type == 'ministrante':
        return db.session.get(Ministrante, int(user_id))
    elif user_type in ['admin', 'participante']:
        return db.session.get(Usuario, int(user_id))
    elif user_type == 'cliente':
        return db.session.get(Cliente, int(user_id))

    # Fallback
    return db.session.get(Usuario, int(user_id)) or db.session.get(Ministrante, int(user_id))


# =======================================
# Login
# =======================================
@auth_routes.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    next_page = request.args.get('next') or request.form.get('next')
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        # Tenta localizar o usuário por email nas três tabelas
        usuario = Usuario.query.filter_by(email=email).first() or \
                  Ministrante.query.filter_by(email=email).first() or \
                  Cliente.query.filter_by(email=email).first()

        if not usuario:
            flash('E-mail ou senha incorretos!', 'danger')
            return render_template("login.html", next=next_page)

        if isinstance(usuario, Cliente) and not usuario.ativo:
            logout_user()
            flash('Sua conta está desativada. Contate o administrador.', 'danger')
            return render_template("login.html", next=next_page)

        if isinstance(usuario, Usuario) and not getattr(usuario, 'ativo', True):
            logout_user()
            msg = 'Sua conta está bloqueada. Contate a administração do evento.'
            flash(msg, 'danger')
            return msg

        if not check_password_hash(usuario.senha, senha):
            flash('E-mail ou senha incorretos!', 'danger')
            return render_template("login.html", next=next_page)

        if isinstance(usuario, Usuario):
            ultima = Inscricao.query.filter_by(usuario_id=usuario.id).order_by(Inscricao.id.desc()).first()
            if ultima and usuario.evento_id != ultima.evento_id:
                usuario.evento_id = ultima.evento_id
                db.session.commit()

        if getattr(usuario, 'mfa_enabled', False):
            session['pre_mfa_user_id'] = usuario.id
            if next_page:
                session['next_page'] = next_page
            if isinstance(usuario, Cliente):
                session['pre_mfa_user_type'] = 'cliente'
            elif isinstance(usuario, Ministrante):
                session['pre_mfa_user_type'] = 'ministrante'
            else:
                session['pre_mfa_user_type'] = usuario.tipo
            return redirect(url_for('auth_routes.mfa'))

        login_user(usuario)
        session['user_type'] = (
            'cliente' if isinstance(usuario, Cliente)
            else 'ministrante' if isinstance(usuario, Ministrante)
            else usuario.tipo
        )
        session['mfa_authenticated'] = True

        flash('Login realizado com sucesso!', 'success')

        destino = {
            'admin':        'dashboard_routes.dashboard',
            'cliente':      'dashboard_routes.dashboard',
            'participante': 'dashboard_participante_routes.dashboard_participante',
            'ministrante':  'dashboard_ministrante_routes.dashboard_ministrante',
            'professor':    'dashboard_professor.dashboard_professor',
            'superadmin':   'dashboard_routes.dashboard_superadmin'
        }.get(session.get('user_type'), 'dashboard_routes.dashboard')

        try:
            return redirect(next_page or url_for(destino))
        except Exception:
            return 'login ok'

    return render_template("login.html", next=next_page)


@auth_routes.route('/mfa', methods=['GET', 'POST'])
def mfa():
    user_id = session.get('pre_mfa_user_id')
    if not user_id:
        return redirect(url_for('auth_routes.login'))

    usuario = db.session.get(Usuario, user_id)
    if not usuario or not usuario.mfa_secret:
        flash('Usuário inválido para MFA', 'danger')
        return redirect(url_for('auth_routes.login'))

    if request.method == 'POST':
        token = request.form.get('token')
        totp = pyotp.TOTP(usuario.mfa_secret)
        if totp.verify(token):
            login_user(usuario)
            session['user_type'] = session.pop('pre_mfa_user_type', usuario.tipo)
            session.pop('pre_mfa_user_id', None)
            next_page = session.pop('next_page', None)
            session['mfa_authenticated'] = True
            flash('Login realizado com sucesso!', 'success')
            destino = {
                'admin':        'dashboard_routes.dashboard',
                'cliente':      'dashboard_routes.dashboard',
                'participante': 'dashboard_participante_routes.dashboard_participante',
                'ministrante':  'dashboard_ministrante_routes.dashboard_ministrante',
                'professor':    'dashboard_professor.dashboard_professor',
                'superadmin':   'dashboard_routes.dashboard_superadmin'
            }.get(session.get('user_type'), 'dashboard_routes.dashboard')
            return redirect(next_page or url_for(destino))
        else:
            flash('Código inválido', 'danger')
    return render_template('auth/mfa.html')

# ===========================
#   RESET DE SENHA VIA CPF
# ===========================
@auth_routes.route('/esqueci_senha_cpf', methods=['GET', 'POST'])
def esqueci_senha_cpf():
    if request.method == 'POST':
        # Verificar reCAPTCHA v3
        recaptcha_response = request.form.get('g-recaptcha-response', '')
        if not recaptcha_response:
            flash('Erro na verificação de segurança. Por favor, tente novamente.', 'danger')
            return render_template("esqueci_senha_cpf.html")
        
        # Verificação manual do reCAPTCHA v3
        import requests
        recaptcha_secret = current_app.config.get('RECAPTCHA_PRIVATE_KEY', '')
        verify_url = 'https://www.google.com/recaptcha/api/siteverify'
        
        try:
            r = requests.post(verify_url, {
                'secret': recaptcha_secret,
                'response': recaptcha_response,
                'remoteip': request.remote_addr
            })
            result = r.json()
            
            if result.get('success'):
                score = result.get('score', 0.0)
                action = result.get('action', '')
                current_app.logger.info(f"reCAPTCHA v3 score: {score}, action: {action}")
                
                if score < 0.5:  # Valor típico para pontuação mínima
                    flash('Verificação de segurança falhou. Por favor, tente novamente.', 'danger')
                    current_app.logger.warning(f"reCAPTCHA v3 score baixo: {score} para IP {request.remote_addr}")
                    return render_template("esqueci_senha_cpf.html")
            else:
                flash('Erro na verificação de segurança. Por favor, tente novamente.', 'danger')
                current_app.logger.error(f"reCAPTCHA v3 falhou: {result.get('error-codes', [])}")
                return render_template("esqueci_senha_cpf.html")
        except Exception as e:
            flash('Erro no servidor. Por favor, tente novamente.', 'danger')
            current_app.logger.error(f"Erro ao verificar reCAPTCHA v3: {str(e)}")
            return render_template("esqueci_senha_cpf.html")
        
        cpf = request.form.get('cpf')
        logger.info("CPF recebido: ***%s", cpf[-4:])
        usuario = Usuario.query.filter_by(cpf=cpf).first()

        if usuario:
            masked_email_parts = usuario.email.split("@")
            masked_email = masked_email_parts[0][:2] + "***@" + masked_email_parts[1]
            logger.info(
                "Usuário encontrado: ID %s, Email %s",
                usuario.id,
                masked_email,
            )
            token = PasswordResetToken(
                usuario_id=usuario.id,
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            db.session.add(token)
            db.session.commit()
            link = url_for('auth_routes.reset_senha_cpf', token=token.token, _external=True)
            assunto = 'Redefini\u00e7\u00e3o de Senha'
            corpo_texto = f'Acesse o link para redefinir sua senha: {link}'
            corpo_html = f"""
            <p>Olá, {usuario.nome}!</p>
            <p>Recebemos uma solicitação para redefinir sua senha. Para prosseguir, acesse o link abaixo:</p>
            <p><a href='{link}'>{link}</a></p>
            <p>Se você não solicitou esta alteração, ignore este e-mail.</p>
            """
            try:
                logger.info("Tentando enviar email de redefinição de senha via OAuth")
                enviar_email(
                    destinatario=usuario.email,
                    nome_participante=usuario.nome,
                    nome_oficina='',
                    assunto=assunto,
                    corpo_texto=corpo_texto,
                    corpo_html=corpo_html,
                )
                logger.info("Email enviado com sucesso")
            except Exception as e:
                logger.exception("Erro ao enviar email: %s", e)
        else:
            logger.warning("Nenhum usuário encontrado com o CPF informado")
        flash('Se o CPF estiver cadastrado, enviamos um link para o e-mail associado.', 'info')
        return redirect(url_for('auth_routes.login'))
    return render_template("esqueci_senha_cpf.html")

@auth_routes.route('/reset_senha_cpf', methods=['GET', 'POST'])
def reset_senha_cpf():
    token_str = request.args.get('token') or request.form.get('token')
    if not token_str:
        flash('Token inválido ou expirado.', 'danger')
        return redirect(url_for('auth_routes.esqueci_senha_cpf'))

    token_obj = PasswordResetToken.query.filter_by(token=token_str, used=False).first()
    if not token_obj or token_obj.expires_at < datetime.utcnow():
        flash('Token inválido ou expirado.', 'danger')
        return redirect(url_for('auth_routes.esqueci_senha_cpf'))

    usuario = token_obj.usuario

    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')
        if not password_is_strong(nova_senha) or nova_senha != confirmar_senha:
            flash('As senhas não coincidem ou não atendem aos requisitos.', 'danger')
            return redirect(url_for('auth_routes.reset_senha_cpf', token=token_str))

        usuario.senha = generate_password_hash(nova_senha, method="pbkdf2:sha256")
        token_obj.used = True
        db.session.commit()
        flash('Senha redefinida com sucesso! Faça login novamente.', 'success')
        return redirect(url_for('auth_routes.login'))

    return render_template('reset_senha_cpf.html', token=token_str)

# =======================================
# Logout
# =======================================
@auth_routes.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso!', 'info')
    return redirect(url_for('evento_routes.home'))


# =======================================
# Cadastro Público de Cliente
# =======================================
@auth_routes.route('/registrar_cliente', methods=['GET', 'POST'])
def cadastrar_cliente_publico():
    form = PublicClienteForm()
    
    # Registrar informações importantes no log para diagnóstico
    current_app.logger.info("========== INÍCIO DIAGNÓSTICO RECAPTCHA ==========")
    current_app.logger.info(f"Método da requisição: {request.method}")
    current_app.logger.info(f"User-Agent: {request.headers.get('User-Agent')}")
    current_app.logger.info(f"Referer: {request.headers.get('Referer')}")
    current_app.logger.info(f"Configuração reCAPTCHA - Chave pública configurada: {bool(current_app.config.get('RECAPTCHA_PUBLIC_KEY'))}")
    current_app.logger.info(f"Configuração reCAPTCHA - Chave privada configurada: {bool(current_app.config.get('RECAPTCHA_PRIVATE_KEY'))}")
    current_app.logger.info("========== FIM DIAGNÓSTICO RECAPTCHA ==========")
    
    if request.method == 'POST':
        # Primeiro, registrar todos os campos do formulário para diagnóstico completo
        current_app.logger.info("========== DIAGNÓSTICO DO FORMULÁRIO ==========")
        form_data = {k: (v[:20] + '...' if k != 'g-recaptcha-response' and isinstance(v, str) and len(v) > 20 else v) 
                     for k, v in request.form.items()}
        current_app.logger.info(f"Campos presentes: {', '.join(form_data.keys())}")
        current_app.logger.info(f"Content-Type: {request.content_type}")
        current_app.logger.info(f"Tamanho do corpo da requisição: {request.content_length} bytes")
        current_app.logger.info("========== FIM DIAGNÓSTICO DO FORMULÁRIO ==========")
        
        # Captura a resposta do reCAPTCHA v3
        recaptcha_response = request.form.get('g-recaptcha-response', '')
        recaptcha_valid = True
        
        # Log das informações recebidas para debug
        current_app.logger.info("========== DIAGNÓSTICO TOKEN RECAPTCHA ==========")
        if recaptcha_response:
            current_app.logger.info(f"Token recaptcha recebido: {recaptcha_response[:20]}... (Tamanho: {len(recaptcha_response)})")
        else:
            current_app.logger.warning("ALERTA: Token recaptcha NÃO encontrado na requisição!")
            # Imprimir headers para diagnóstico
            current_app.logger.info(f"Headers: {dict(request.headers)}")
        current_app.logger.info("========== FIM DIAGNÓSTICO TOKEN RECAPTCHA ==========")
        
        # MODO DIAGNÓSTICO: Se não encontrar o token reCAPTCHA, 
        # prossegue mesmo assim, mas registra o problema
        if not recaptcha_response:
            current_app.logger.warning("MODO DIAGNÓSTICO: Permitindo cadastro sem reCAPTCHA para diagnóstico")
            flash('Aviso: Verificação de segurança (reCAPTCHA) não foi enviada pelo seu navegador. O cadastro será permitido em modo de diagnóstico.', 'warning')
            # Em produção, descomente estas linhas:
            # recaptcha_valid = False
            # flash('Verificação de segurança ausente. Por favor, tente novamente.', 'danger')
            # return render_template('auth/cadastrar_cliente_publico.html', form=form)
        else:
            # Verificação manual do reCAPTCHA v3
            import requests
            recaptcha_secret = current_app.config.get('RECAPTCHA_PRIVATE_KEY', '')
            
            # Verificar se a chave privada está configurada
            if not recaptcha_secret:
                recaptcha_valid = False
                flash('Erro de configuração do servidor. Por favor, contate o suporte.', 'danger')
                current_app.logger.error("ERRO CRÍTICO: RECAPTCHA_PRIVATE_KEY não está configurada")
                return render_template('auth/cadastrar_cliente_publico.html', form=form)
                
            current_app.logger.debug(f"Chave secreta configurada (tamanho: {len(recaptcha_secret)})")
            verify_url = 'https://www.google.com/recaptcha/api/siteverify'
            
            try:
                # Log dos dados que serão enviados
                current_app.logger.debug(f"Enviando verificação para {verify_url}")
                
                # Realizar a solicitação
                verify_data = {
                    'secret': recaptcha_secret,
                    'response': recaptcha_response,
                    'remoteip': request.remote_addr
                }
                
                r = requests.post(verify_url, data=verify_data)
                
                # Verificar resposta HTTP
                if r.status_code != 200:
                    recaptcha_valid = False
                    flash(f'Erro na API do reCAPTCHA (HTTP {r.status_code})', 'danger')
                    current_app.logger.error(f"Erro HTTP na verificação do reCAPTCHA: {r.status_code}, {r.text}")
                    return render_template('auth/cadastrar_cliente_publico.html', form=form)
                
                # Analisar resultado
                result = r.json()
                current_app.logger.debug(f"Resposta da API do reCAPTCHA: {result}")
                
                # Para v3, precisamos verificar a pontuação
                if result.get('success'):
                    score = result.get('score', 0.0)
                    action = result.get('action', '')
                    
                    # Registrar o score para fins de diagnóstico
                    current_app.logger.info(f"reCAPTCHA v3 score: {score}, action: {action}")
                    
                    # Temporariamente, aceite qualquer pontuação para diagnóstico
                    if score < 0.1:  # Valor muito baixo apenas para casos extremos
                        recaptcha_valid = False
                        flash(f'Pontuação de segurança muito baixa ({score}). Por favor, tente novamente.', 'danger')
                        current_app.logger.warning(f"reCAPTCHA v3 score baixo: {score} para IP {request.remote_addr}")
                    else:
                        current_app.logger.info(f"reCAPTCHA v3 validado com sucesso, score: {score}")
                else:
                    recaptcha_valid = False
                    error_codes = result.get('error-codes', [])
                    error_msg = ', '.join(error_codes) if error_codes else 'Erro desconhecido'
                    flash(f'Erro na verificação de segurança: {error_msg}', 'danger')
                    current_app.logger.error(f"reCAPTCHA v3 falhou: {error_codes}")
            except Exception as e:
                recaptcha_valid = False
                current_app.logger.exception(f"Exceção ao verificar reCAPTCHA v3: {str(e)}")
                flash(f'Erro no servidor: {str(e)}', 'danger')
        
        if not recaptcha_valid:
            return render_template('auth/cadastrar_cliente_publico.html', form=form)
        
        # Validar o resto do formulário
        if not form.validate():
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'Erro no campo {field}: {error}', 'danger')
        
        # Caso o formulário seja válido
        elif form.validate_on_submit():
            nome = request.form['nome']
            email = request.form['email']
            senha = request.form['senha']

            cliente_existente = Cliente.query.filter_by(email=email).first()
            if cliente_existente:
                flash('Já existe um cliente com esse e-mail!', 'danger')
                return redirect(url_for('auth_routes.cadastrar_cliente_publico'))

            # Pagamento habilitado por padrão para novos clientes
            novo_cliente = Cliente(
                nome=nome,
                email=email,
                senha=generate_password_hash(senha, method="pbkdf2:sha256"),
                habilita_pagamento=True,
            )

            db.session.add(novo_cliente)
            db.session.commit()

            flash('Cliente cadastrado com sucesso!', 'success')
            return redirect(url_for('auth_routes.login'))

    return render_template('auth/cadastrar_cliente_publico.html', form=form)
