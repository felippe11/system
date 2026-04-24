from utils import endpoints
# routes/auth_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import func
from datetime import datetime, timedelta
import pyotp
import logging

from models import Inscricao
from models.user import Usuario, Ministrante, Cliente, PasswordResetToken
from extensions import login_manager, db
from utils import enviar_email, enviar_email_google
from forms import PublicClienteForm
from utils.security import password_is_strong

auth_routes = Blueprint(
    'auth_routes',
    __name__,
    template_folder="../templates/auth"
)

logger = logging.getLogger(__name__)

# =======================================
# FunÃ§Ã£o de carregamento de usuÃ¡rio
# =======================================
@login_manager.user_loader
def load_user(user_id):
    user_type = session.get('user_type')

    # Tenta carregar baseado no user_type da sessÃ£o primeiro
    if user_type == 'ministrante':
        user = db.session.get(Ministrante, int(user_id))
        if user:
            return user
    elif user_type in ['admin', 'participante']:
        user = db.session.get(Usuario, int(user_id))
        if user:
            return user
    elif user_type == 'cliente':
        user = db.session.get(Cliente, int(user_id))
        if user:
            return user
    elif user_type == 'monitor':
        from models.user import Monitor
        user = db.session.get(Monitor, int(user_id))
        if user:
            return user

    # Fallback robusto: tenta todas as tabelas se user_type nÃ£o estiver disponÃ­vel
    # Isso Ã© importante para casos onde a sessÃ£o pode nÃ£o ter user_type
    user = db.session.get(Cliente, int(user_id))
    if user:
        # Atualiza a sessÃ£o com o tipo correto
        session['user_type'] = 'cliente'
        return user
    
    user = db.session.get(Usuario, int(user_id))
    if user:
        # Atualiza a sessÃ£o com o tipo correto
        session['user_type'] = user.tipo
        return user
    
    user = db.session.get(Ministrante, int(user_id))
    if user:
        # Atualiza a sessÃ£o com o tipo correto
        session['user_type'] = 'ministrante'
        return user
    
    # Se chegou atÃ© aqui, usuÃ¡rio nÃ£o foi encontrado
    return None


# =======================================
# Login
# =======================================
@auth_routes.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    next_page = request.args.get('next') or request.form.get('next')
    if request.method == 'POST':
        email_input = request.form.get('email', '')
        senha = request.form['senha']

        email_normalized = email_input.strip().lower()

        # Tenta localizar o usuÃ¡rio por email nas trÃªs tabelas (ignorando maiÃºsculas/minÃºsculas)
        usuario = None
        for modelo in (Usuario, Ministrante, Cliente):
            resultado = modelo.query.filter(func.lower(modelo.email) == email_normalized).first()
            if resultado:
                usuario = resultado
                break

        if not usuario:
            flash('E-mail ou senha incorretos!', 'danger')
            return render_template("login.html", next=next_page)

        if isinstance(usuario, Cliente) and not usuario.ativo:
            logout_user()
            flash('Sua conta estÃ¡ desativada. Contate o administrador.', 'danger')
            return render_template("login.html", next=next_page)

        if isinstance(usuario, Usuario) and not getattr(usuario, 'ativo', True):
            logout_user()
            msg = 'Sua conta estÃ¡ bloqueada. Contate a administraÃ§Ã£o do evento.'
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
            'admin':        endpoints.DASHBOARD,
            'cliente':      endpoints.DASHBOARD,
            'participante': endpoints.DASHBOARD_PARTICIPANTE,
            'ministrante':  'formador_routes.dashboard_formador',
            'professor':    'dashboard_professor.dashboard_professor',
            'superadmin':   endpoints.DASHBOARD_SUPERADMIN
        }.get(session.get('user_type'), endpoints.DASHBOARD)

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
        flash('UsuÃ¡rio invÃ¡lido para MFA', 'danger')
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
                'admin':        endpoints.DASHBOARD,
                'cliente':      endpoints.DASHBOARD,
                'participante': endpoints.DASHBOARD_PARTICIPANTE,
                'ministrante':  'formador_routes.dashboard_formador',
                'professor':    'dashboard_professor.dashboard_professor',
                'superadmin':   endpoints.DASHBOARD_SUPERADMIN
            }.get(session.get('user_type'), endpoints.DASHBOARD)
            return redirect(next_page or url_for(destino))
        else:
            flash('CÃ³digo invÃ¡lido', 'danger')
    return render_template('auth/mfa.html')

# ===========================
#   RESET DE SENHA VIA CPF
# ===========================
@auth_routes.route('/esqueci_senha_cpf', methods=['GET', 'POST'])
def esqueci_senha_cpf():
    def _normalizar_cpf(cpf: str) -> str:
        return "".join(ch for ch in (cpf or "") if ch.isdigit())

    def _formatar_cpf(cpf: str) -> str:
        cpf_digits = _normalizar_cpf(cpf)
        if len(cpf_digits) != 11:
            return cpf
        return f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"

    def _buscar_usuario_por_cpf(cpf: str):
        cpf_digits = _normalizar_cpf(cpf)
        if not cpf_digits:
            return None
        cpf_formatado = _formatar_cpf(cpf_digits)
        return Usuario.query.filter(
            (Usuario.cpf == cpf_digits) | (Usuario.cpf == cpf_formatado)
        ).first()

    if request.method == 'POST':
        acao = request.form.get('acao', 'validar_cpf')
        cpf = request.form.get('cpf', '').strip()
        usuario = _buscar_usuario_por_cpf(cpf)

        if acao == 'validar_cpf':
            if not usuario:
                flash('CPF não encontrado.', 'danger')
                return render_template("esqueci_senha_cpf.html", cpf=cpf, etapa='cpf')
            return render_template(
                "esqueci_senha_cpf.html",
                cpf=_normalizar_cpf(cpf),
                etapa='nova_senha'
            )

        if acao == 'alterar_senha':
            nova_senha = request.form.get('nova_senha', '')
            confirmar_senha = request.form.get('confirmar_senha', '')

            if not usuario:
                flash('CPF não encontrado.', 'danger')
                return render_template("esqueci_senha_cpf.html", cpf=cpf, etapa='cpf')

            if not password_is_strong(nova_senha):
                flash('A senha não atende aos requisitos mínimos de segurança.', 'danger')
                return render_template(
                    "esqueci_senha_cpf.html",
                    cpf=_normalizar_cpf(cpf),
                    etapa='nova_senha'
                )

            if nova_senha != confirmar_senha:
                flash('As senhas não coincidem.', 'danger')
                return render_template(
                    "esqueci_senha_cpf.html",
                    cpf=_normalizar_cpf(cpf),
                    etapa='nova_senha'
                )

            usuario.senha = generate_password_hash(nova_senha, method="pbkdf2:sha256")
            db.session.commit()
            flash('Senha atualizada com sucesso. Faça login.', 'success')
            return redirect(url_for('auth_routes.login'))

    return render_template("esqueci_senha_cpf.html", etapa='cpf')

@auth_routes.route('/reset_senha_cpf', methods=['GET', 'POST'])
def reset_senha_cpf():
    token_str = request.args.get('token') or request.form.get('token')
    if not token_str:
        flash('Token invÃ¡lido ou expirado.', 'danger')
        return redirect(url_for('auth_routes.esqueci_senha_cpf'))

    token_obj = PasswordResetToken.query.filter_by(token=token_str, used=False).first()
    if not token_obj or token_obj.expires_at < datetime.utcnow():
        flash('Token invÃ¡lido ou expirado.', 'danger')
        return redirect(url_for('auth_routes.esqueci_senha_cpf'))

    usuario = token_obj.usuario

    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')
        if not password_is_strong(nova_senha) or nova_senha != confirmar_senha:
            flash('As senhas nÃ£o coincidem ou nÃ£o atendem aos requisitos.', 'danger')
            return redirect(url_for('auth_routes.reset_senha_cpf', token=token_str))

        usuario.senha = generate_password_hash(nova_senha, method="pbkdf2:sha256")
        token_obj.used = True
        db.session.commit()
        flash('Senha redefinida com sucesso! FaÃ§a login novamente.', 'success')
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
# Cadastro PÃºblico de Cliente
# =======================================
@auth_routes.route('/registrar_cliente', methods=['GET', 'POST'])
def cadastrar_cliente_publico():
    form = PublicClienteForm()
    
    # Registrar informaÃ§Ãµes importantes no log para diagnÃ³stico
    current_app.logger.info("========== INÃCIO DIAGNÃ“STICO RECAPTCHA ==========")
    current_app.logger.info(f"MÃ©todo da requisiÃ§Ã£o: {request.method}")
    current_app.logger.info(f"User-Agent: {request.headers.get('User-Agent')}")
    current_app.logger.info(f"Referer: {request.headers.get('Referer')}")
    current_app.logger.info(f"ConfiguraÃ§Ã£o reCAPTCHA - Chave pÃºblica configurada: {bool(current_app.config.get('RECAPTCHA_PUBLIC_KEY'))}")
    current_app.logger.info(f"ConfiguraÃ§Ã£o reCAPTCHA - Chave privada configurada: {bool(current_app.config.get('RECAPTCHA_PRIVATE_KEY'))}")
    current_app.logger.info("========== FIM DIAGNÃ“STICO RECAPTCHA ==========")
    
    if request.method == 'POST':
        # Primeiro, registrar todos os campos do formulÃ¡rio para diagnÃ³stico completo
        current_app.logger.info("========== DIAGNÃ“STICO DO FORMULÃRIO ==========")
        form_data = {k: (v[:20] + '...' if k != 'g-recaptcha-response' and isinstance(v, str) and len(v) > 20 else v) 
                     for k, v in request.form.items()}
        current_app.logger.info(f"Campos presentes: {', '.join(form_data.keys())}")
        current_app.logger.info(f"Content-Type: {request.content_type}")
        current_app.logger.info(f"Tamanho do corpo da requisiÃ§Ã£o: {request.content_length} bytes")
        current_app.logger.info("========== FIM DIAGNÃ“STICO DO FORMULÃRIO ==========")
        
        # Captura a resposta do reCAPTCHA v3
        recaptcha_response = request.form.get('g-recaptcha-response', '')
        recaptcha_valid = True
        
        # Log das informaÃ§Ãµes recebidas para debug
        current_app.logger.info("========== DIAGNÃ“STICO TOKEN RECAPTCHA ==========")
        if recaptcha_response:
            current_app.logger.info(f"Token recaptcha recebido: {recaptcha_response[:20]}... (Tamanho: {len(recaptcha_response)})")
        else:
            current_app.logger.warning("ALERTA: Token recaptcha NÃƒO encontrado na requisiÃ§Ã£o!")
            # Imprimir headers para diagnÃ³stico
            current_app.logger.info(f"Headers: {dict(request.headers)}")
        current_app.logger.info("========== FIM DIAGNÃ“STICO TOKEN RECAPTCHA ==========")
        
        # MODO DIAGNÃ“STICO: Se nÃ£o encontrar o token reCAPTCHA, 
        # prossegue mesmo assim, mas registra o problema
        if not recaptcha_response:
            current_app.logger.warning("MODO DIAGNÃ“STICO: Permitindo cadastro sem reCAPTCHA para diagnÃ³stico")
            flash('Aviso: VerificaÃ§Ã£o de seguranÃ§a (reCAPTCHA) nÃ£o foi enviada pelo seu navegador. O cadastro serÃ¡ permitido em modo de diagnÃ³stico.', 'warning')
            # Em produÃ§Ã£o, descomente estas linhas:
            # recaptcha_valid = False
            # flash('VerificaÃ§Ã£o de seguranÃ§a ausente. Por favor, tente novamente.', 'danger')
            # return render_template('auth/cadastrar_cliente_publico.html', form=form)
        else:
            # VerificaÃ§Ã£o manual do reCAPTCHA v3
            import requests
            recaptcha_secret = current_app.config.get('RECAPTCHA_PRIVATE_KEY', '')
            
            # Verificar se a chave privada estÃ¡ configurada
            if not recaptcha_secret:
                recaptcha_valid = False
                flash('Erro de configuraÃ§Ã£o do servidor. Por favor, contate o suporte.', 'danger')
                current_app.logger.error("ERRO CRÃTICO: RECAPTCHA_PRIVATE_KEY nÃ£o estÃ¡ configurada")
                return render_template('auth/cadastrar_cliente_publico.html', form=form)
                
            current_app.logger.debug(f"Chave secreta configurada (tamanho: {len(recaptcha_secret)})")
            verify_url = 'https://www.google.com/recaptcha/api/siteverify'
            
            try:
                # Log dos dados que serÃ£o enviados
                current_app.logger.debug(f"Enviando verificaÃ§Ã£o para {verify_url}")
                
                # Realizar a solicitaÃ§Ã£o
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
                    current_app.logger.error(f"Erro HTTP na verificaÃ§Ã£o do reCAPTCHA: {r.status_code}, {r.text}")
                    return render_template('auth/cadastrar_cliente_publico.html', form=form)
                
                # Analisar resultado
                result = r.json()
                current_app.logger.debug(f"Resposta da API do reCAPTCHA: {result}")
                
                # Para v3, precisamos verificar a pontuaÃ§Ã£o
                if result.get('success'):
                    score = result.get('score', 0.0)
                    action = result.get('action', '')
                    
                    # Registrar o score para fins de diagnÃ³stico
                    current_app.logger.info(f"reCAPTCHA v3 score: {score}, action: {action}")
                    
                    # Temporariamente, aceite qualquer pontuaÃ§Ã£o para diagnÃ³stico
                    if score < 0.1:  # Valor muito baixo apenas para casos extremos
                        recaptcha_valid = False
                        flash(f'PontuaÃ§Ã£o de seguranÃ§a muito baixa ({score}). Por favor, tente novamente.', 'danger')
                        current_app.logger.warning(f"reCAPTCHA v3 score baixo: {score} para IP {request.remote_addr}")
                    else:
                        current_app.logger.info(f"reCAPTCHA v3 validado com sucesso, score: {score}")
                else:
                    recaptcha_valid = False
                    error_codes = result.get('error-codes', [])
                    error_msg = ', '.join(error_codes) if error_codes else 'Erro desconhecido'
                    flash(f'Erro na verificaÃ§Ã£o de seguranÃ§a: {error_msg}', 'danger')
                    current_app.logger.error(f"reCAPTCHA v3 falhou: {error_codes}")
            except Exception as e:
                recaptcha_valid = False
                current_app.logger.exception(f"ExceÃ§Ã£o ao verificar reCAPTCHA v3: {str(e)}")
                flash(f'Erro no servidor: {str(e)}', 'danger')
        
        if not recaptcha_valid:
            return render_template('auth/cadastrar_cliente_publico.html', form=form)
        
        # Validar o resto do formulÃ¡rio
        if not form.validate():
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'Erro no campo {field}: {error}', 'danger')
        
        # Caso o formulÃ¡rio seja vÃ¡lido
        elif form.validate_on_submit():
            nome = request.form['nome']
            email = request.form['email']
            senha = request.form['senha']

            cliente_existente = Cliente.query.filter_by(email=email).first()
            if cliente_existente:
                flash('JÃ¡ existe um cliente com esse e-mail!', 'danger')
                return redirect(url_for('auth_routes.cadastrar_cliente_publico'))

            # Pagamento habilitado por padrÃ£o para novos clientes
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


