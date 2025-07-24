# routes/auth_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
import pyotp

from models import Usuario, Ministrante, Cliente, PasswordResetToken
from extensions import login_manager, db, mail
from forms import PublicClienteForm
from utils.security import password_is_strong

auth_routes = Blueprint(
    'auth_routes',
    __name__,
    template_folder="../templates/auth"
)

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
        cpf = request.form.get('cpf')
        print(f"CPF recebido: {cpf}")
        usuario = Usuario.query.filter_by(cpf=cpf).first()

        if usuario:
            print(f"Usuário encontrado: ID {usuario.id}, Email {usuario.email}")
            token = PasswordResetToken(
                usuario_id=usuario.id,
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            db.session.add(token)
            db.session.commit()
            link = url_for('auth_routes.reset_senha_cpf', token=token.token, _external=True)
            msg = Message(
                subject='Redefini\u00e7\u00e3o de Senha',
                recipients=[usuario.email],
                body=f'Acesse o link para redefinir sua senha: {link}'
            )
            try:
                print("Tentando enviar email de redefinição de senha")
                mail.send(msg)
                print("Email enviado com sucesso")
            except Exception as e:
                print(f"Erro ao enviar email: {e}")
        else:
            print("Nenhum usuário encontrado com o CPF informado")
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

        usuario.senha = generate_password_hash(nova_senha)
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
    
    if request.method == 'POST':
        if not form.validate():
            # Verificar especificamente erros do reCAPTCHA
            if form.recaptcha.errors:
                erro_captcha = form.recaptcha.errors[0] if form.recaptcha.errors else "Falha na validação do CAPTCHA"
                flash(f'Erro no CAPTCHA: {erro_captcha}', 'danger')
            else:
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
                senha=generate_password_hash(senha),
                habilita_pagamento=True,
            )

            db.session.add(novo_cliente)
            db.session.commit()

            flash('Cliente cadastrado com sucesso!', 'success')
            return redirect(url_for('auth_routes.login'))

    return render_template('auth/cadastrar_cliente_publico.html', form=form)
