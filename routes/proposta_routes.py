from flask import Blueprint
proposta_routes = Blueprint("proposta_routes", __name__)

from flask import render_template, request, redirect, url_for, flash
from models import Proposta
from extensions import db


@proposta_routes.route('/enviar_proposta', methods=['POST'])
def enviar_proposta():
    nome = request.form.get('nome')
    email = request.form.get('email')
    tipo_evento = request.form.get('tipo_evento')
    descricao = request.form.get('descricao')

    if not all([nome, email, tipo_evento, descricao]):
        flash('Por favor, preencha todos os campos.', 'danger')
        return redirect(url_for('routes.home'))

    nova_proposta = Proposta(
        nome=nome,
        email=email,
        tipo_evento=tipo_evento,
        descricao=descricao
    )

    try:
        db.session.add(nova_proposta)
        db.session.commit()
        flash('Proposta enviada com sucesso! Entraremos em contato em breve.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao enviar proposta. Por favor, tente novamente.', 'danger')

    return render_template(
        'index.html',
        nome=nome,
        email=email,
        tipo_evento=tipo_evento,
        descricao=descricao
    )

