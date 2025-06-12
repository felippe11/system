# routes/auth_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash

from models import Usuario, Ministrante, Cliente
from extensions import login_manager, db

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

        if not check_password_hash(usuario.senha, senha):
            flash('E-mail ou senha incorretos!', 'danger')
            return render_template("login.html")

        # Autenticar e guardar o tipo de usuário
        login_user(usuario)

        if isinstance(usuario, Cliente):
            session['user_type'] = 'cliente'
        elif isinstance(usuario, Ministrante):
            session['user_type'] = 'ministrante'
        else:
            session['user_type'] = usuario.tipo

        flash('Login realizado com sucesso!', 'success')

        # Redirecionamento baseado no tipo
        destino = {
            'admin':        'dashboard_routes.dashboard',
            'cliente':      'dashboard_routes.dashboard',
            'participante': 'dashboard_participante_routes.dashboard_participante',
            'ministrante':  'dashboard_ministrante_routes.dashboard_ministrante',
            'professor':    'dashboard_professor.dashboard_professor'
        }.get(session.get('user_type'), 'dashboard_routes.dashboard')

        return redirect(url_for(destino))

    return render_template("login.html")

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
