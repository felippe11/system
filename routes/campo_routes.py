from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import CampoPersonalizadoCadastro

campo_routes = Blueprint('campo_routes', __name__)

@campo_routes.route('/adicionar_campo_personalizado', methods=['POST'])
@login_required
def adicionar_campo_personalizado():
    nome_campo = request.form.get('nome_campo')
    tipo_campo = request.form.get('tipo_campo')
    obrigatorio = bool(request.form.get('obrigatorio'))

    novo_campo = CampoPersonalizadoCadastro(
        cliente_id=current_user.id,
        nome=nome_campo,
        tipo=tipo_campo,
        obrigatorio=obrigatorio
    )
    db.session.add(novo_campo)
    db.session.commit()

    flash('Campo personalizado adicionado com sucesso!', 'success')
    return redirect(url_for('routes.dashboard_cliente'))

@campo_routes.route('/remover_campo_personalizado/<int:campo_id>', methods=['POST'])
@login_required
def remover_campo_personalizado(campo_id):
    campo = CampoPersonalizadoCadastro.query.get_or_404(campo_id)

    if campo.cliente_id != current_user.id:
        flash('Você não tem permissão para remover este campo.', 'danger')
        return redirect(url_for('routes.dashboard_cliente'))

    db.session.delete(campo)
    db.session.commit()

    flash('Campo personalizado removido com sucesso!', 'success')
    return redirect(url_for('routes.dashboard_cliente'))





