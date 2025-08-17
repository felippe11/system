from flask import Blueprint
participante_routes = Blueprint("participante_routes", __name__)
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models.user import Usuario, PasswordResetToken
from extensions import db


@participante_routes.route('/gerenciar_participantes', methods=['GET'])
@login_required
def gerenciar_participantes():
    # Verifique se é admin
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))

    # Busca todos os usuários cujo tipo é 'participante'
    participantes = Usuario.query.filter_by(tipo='participante').all()

    # Renderiza um template parcial (ou completo). Você pode renderizar
    # a página inteira ou só retornar JSON. Aqui vamos supor que renderiza a modal.
    return render_template('gerenciar_participantes.html', participantes=participantes)

@participante_routes.route('/excluir_participante/<int:participante_id>', methods=['POST'])
@login_required
def excluir_participante(participante_id):
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    participante = Usuario.query.get_or_404(participante_id)
    if participante.tipo != 'participante':
        flash('Esse usuário não é um participante.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))

    PasswordResetToken.query.filter_by(usuario_id=participante.id).delete()
    db.session.delete(participante)
    db.session.commit()
    flash('Participante excluído com sucesso!', 'success')
    return redirect(url_for('dashboard_routes.dashboard'))

@participante_routes.route('/editar_participante_admin/<int:participante_id>', methods=['POST'])
@login_required
def editar_participante_admin(participante_id):
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    participante = Usuario.query.get_or_404(participante_id)
    if participante.tipo != 'participante':
        flash('Esse usuário não é um participante.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))

    # Captura os dados do form
    nome = request.form.get('nome')
    cpf = request.form.get('cpf')
    email = request.form.get('email')
    formacao = request.form.get('formacao')
    nova_senha = request.form.get('senha')

    # Atualiza
    participante.nome = nome
    participante.cpf = cpf
    participante.email = email
    participante.formacao = formacao
    if nova_senha:
        participante.senha = generate_password_hash(nova_senha)

    db.session.commit()
    flash('Participante atualizado com sucesso!', 'success')
    return redirect(url_for('dashboard_routes.dashboard'))
