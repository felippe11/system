
from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import (
    TrabalhoCientifico,
    Usuario,
    Review,
    RevisaoConfig,
    Assignment,
    ConfiguracaoCliente,
    AuditLog,
)
import uuid
from datetime import datetime, timedelta

peer_review_routes = Blueprint('peer_review_routes', __name__, template_folder="../templates/peer_review")

@peer_review_routes.route('/assign_reviews', methods=['POST'])
@login_required
def assign_reviews():
    if current_user.tipo not in ('cliente', 'admin', 'superadmin'):
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    data = request.get_json()
    if not data:
        return {'success': False}, 400
    for trabalho_id, reviewers in data.items():
        trabalho = TrabalhoCientifico.query.get(trabalho_id)
        if not trabalho:
            continue
        for reviewer_id in reviewers:
            rev = Review(
                submission_id=trabalho.id,
                reviewer_id=reviewer_id,
                access_code=str(uuid.uuid4())[:8]
            )
            db.session.add(rev)

            config = ConfiguracaoCliente.query.filter_by(
                cliente_id=trabalho.evento.cliente_id
            ).first()
            prazo_dias = config.prazo_parecer_dias if config else 14
            assignment = Assignment(
                submission_id=trabalho.id,
                reviewer_id=reviewer_id,
                deadline=datetime.utcnow() + timedelta(days=prazo_dias),
            )
            db.session.add(assignment)

            db.session.add(
                AuditLog(
                    user_id=current_user.id,
                    submission_id=trabalho.id,
                    event_type="assignment",
                )
            )
    db.session.commit()
    return {'success': True}

@peer_review_routes.route('/auto_assign/<int:evento_id>', methods=['POST'])
@login_required
def auto_assign(evento_id):
    if current_user.tipo not in ('cliente', 'admin', 'superadmin'):
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    config = RevisaoConfig.query.filter_by(evento_id=evento_id).first()
    if not config:
        return {'success': False, 'message': 'Configuração não encontrada'}, 400
    trabalhos = TrabalhoCientifico.query.filter_by(evento_id=evento_id).all()
    revisores = Usuario.query.filter_by(tipo='professor').all()
    area_map = {}
    for r in revisores:
        area_map.setdefault(r.formacao, []).append(r)
    for t in trabalhos:
        revisores_area = area_map.get(t.area_tematica, revisores)
        selecionados = revisores_area[:config.numero_revisores]
        for reviewer in selecionados:
            rev = Review(
                submission_id=t.id,
                reviewer_id=reviewer.id,
                access_code=str(uuid.uuid4())[:8]
            )
            db.session.add(rev)

            config_cli = ConfiguracaoCliente.query.filter_by(
                cliente_id=t.evento.cliente_id
            ).first()
            prazo_dias = config_cli.prazo_parecer_dias if config_cli else 14
            assignment = Assignment(
                submission_id=t.id,
                reviewer_id=reviewer.id,
                deadline=datetime.utcnow() + timedelta(days=prazo_dias),
            )
            db.session.add(assignment)

            db.session.add(
                AuditLog(
                    user_id=current_user.id,
                    submission_id=t.id,
                    event_type="assignment",
                )
            )
    db.session.commit()
    return {'success': True}

@peer_review_routes.route('/review/<locator>', methods=['GET', 'POST'])
def review_form(locator):
    review = Review.query.filter_by(locator=locator).first_or_404()
    if request.method == 'GET':
        if review.started_at is None:
            review.started_at = datetime.utcnow()
            db.session.commit()
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        if codigo != review.access_code:
            flash('Código incorreto!', 'danger')
            return render_template('peer_review/review_form.html', review=review)
        review.note = request.form.get('nota')
        review.comments = request.form.get('comentarios')
        review.blind_type = 'nome' if request.form.get('mostrar_nome') == 'on' else 'anonimo'
        review.finished_at = datetime.utcnow()
        if review.started_at:
            review.duration_seconds = int((review.finished_at - review.started_at).total_seconds())
        review.submitted_at = review.finished_at
        db.session.commit()
        flash('Revisão enviada!', 'success')
        return redirect(url_for('peer_review_routes.review_form', locator=locator))
    return render_template('peer_review/review_form.html', review=review)

@peer_review_routes.route('/dashboard/author_reviews')
@login_required
def author_reviews():
    trabalhos = TrabalhoCientifico.query.filter_by(usuario_id=current_user.id).all()
    return render_template('peer_review/dashboard_author.html', trabalhos=trabalhos)

@peer_review_routes.route('/dashboard/reviewer_reviews')
@login_required
def reviewer_reviews():
    assignments = Assignment.query.filter_by(reviewer_id=current_user.id).all()
    config = RevisaoConfig.query.first()
    return render_template('peer_review/dashboard_reviewer.html', assignments=assignments, config=config)

@peer_review_routes.route('/dashboard/editor_reviews/<int:evento_id>')
@login_required
def editor_reviews(evento_id):
    if current_user.tipo not in ('cliente', 'admin', 'superadmin'):
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    trabalhos = TrabalhoCientifico.query.filter_by(evento_id=evento_id).all()
    return render_template('peer_review/dashboard_editor.html', trabalhos=trabalhos)

@peer_review_routes.route('/peer-review/author')
def author_dashboard():
    return render_template('peer_review/author/dashboard.html', submissions=[])

@peer_review_routes.route('/peer-review/reviewer')
def reviewer_dashboard():
    assignments = Assignment.query.filter_by(reviewer_id=current_user.id).all() if current_user.is_authenticated else []
    return render_template('peer_review/reviewer/dashboard.html', tasks=assignments)

@peer_review_routes.route('/peer-review/editor')
def editor_dashboard_page():
    return render_template('peer_review/editor/dashboard.html', decisions=[])


