from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from models import AgendamentoVisita
from models.review import Review

dashboard_professor_routes = Blueprint("dashboard_professor", __name__)

@dashboard_professor_routes.route("/dashboard_professor")
@login_required
def dashboard_professor():
    if current_user.tipo != 'professor':
        return redirect(url_for('dashboard_routes.dashboard'))

    # Buscando os agendamentos do professor logado
    agendamentos_professor = AgendamentoVisita.query.filter_by(
        professor_id=current_user.id
    ).all()
    reviews = Review.query.filter_by(reviewer_id=current_user.id).all()

    return render_template(
        'dashboard_professor.html',
        agendamentos=agendamentos_professor,
        reviews=reviews,
    )


