# routes/auth_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
import pyotp

from models import Usuario, Ministrante, Cliente
from extensions import login_manager, db
from forms import PublicClienteForm

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
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        # Tenta localizar o usuário por email nas três tabelas
        usuario = Usuario.query.filter_by(email=email).first() or \
                  Ministrante.query.filter_by(email=email).first() or \
                  Cliente.query.filter_by(email=email).first()

        if not usuario:
            flash('E-mail ou senha incorretos!', 'danger')
            return render_template("login.html")

        if isinstance(usuario, Cliente) and not usuario.ativo:
            logout_user()
            flash('Sua conta está desativada. Contate o administrador.', 'danger')
            return render_template("login.html")

        if isinstance(usuario, Usuario) and not getattr(usuario, 'ativo', True):
            logout_user()
            msg = 'Sua conta está bloqueada. Contate a administração do evento.'
            flash(msg, 'danger')
            return msg

        if not check_password_hash(usuario.senha, senha):
            flash('E-mail ou senha incorretos!', 'danger')
            return render_template("login.html")

        if getattr(usuario, 'mfa_enabled', False):
            session['pre_mfa_user_id'] = usuario.id
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
            return redirect(url_for(destino))
        except Exception:
            return 'login ok'

    return render_template("login.html")


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
            return redirect(url_for(destino))
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
        usuario = Usuario.query.filter_by(cpf=cpf).first()
        if usuario:
            session['reset_user_id'] = usuario.id
            return redirect(url_for('auth_routes.reset_senha_cpf'))
        else:
            flash('CPF não encontrado!', 'danger')
            return redirect(url_for('auth_routes.esqueci_senha_cpf'))
    return render_template("esqueci_senha_cpf.html")

@auth_routes.route('/reset_senha_cpf', methods=['GET', 'POST'])
def reset_senha_cpf():
    user_id = session.get('reset_user_id')
    if not user_id:
        flash('Nenhum usuário selecionado para redefinição!', 'danger')
        return redirect(url_for('auth_routes.esqueci_senha_cpf'))
    usuario = db.session.get(Usuario, user_id)
    if not usuario:
        flash('Usuário não encontrado no banco de dados!', 'danger')
        return redirect(url_for('auth_routes.esqueci_senha_cpf'))
    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')
        if not nova_senha or nova_senha != confirmar_senha:
            flash('As senhas não coincidem ou são inválidas.', 'danger')
            return redirect(url_for('auth_routes.reset_senha_cpf'))
        usuario.senha = generate_password_hash(nova_senha)
        db.session.commit()
        session.pop('reset_user_id', None)
        flash('Senha redefinida com sucesso! Faça login novamente.', 'success')
        return redirect(url_for('auth_routes.login'))
    return render_template('reset_senha_cpf.html', usuario=usuario)

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
    if form.validate_on_submit():
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

    if request.method == 'POST':
        flash('Falha na validação do CAPTCHA, tente novamente.', 'danger')

    return render_template('auth/cadastrar_cliente_publico.html', form=form)
