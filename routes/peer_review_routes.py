
from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from flask_login import login_required, current_user
from extensions import db
from models import TrabalhoCientifico, Usuario, Review, RevisaoConfig, Submission
import uuid
from datetime import datetime

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
    reviews = Review.query.filter_by(reviewer_id=current_user.id).all()
    config = RevisaoConfig.query.first()
    return render_template('peer_review/dashboard_reviewer.html', reviews=reviews, config=config)

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
    locator = request.args.get('locator') or session.get('reviewer_locator')
    code = request.args.get('code') or session.get('reviewer_code')

    if locator and code:
        review = Review.query.filter_by(locator=locator).first()
        if review and review.access_code == code:
            session['reviewer_locator'] = locator
            session['reviewer_code'] = code
            tasks = Review.query.filter_by(reviewer_id=review.reviewer_id).all()
            return render_template('peer_review/reviewer/dashboard.html', tasks=tasks)

        submission = Submission.query.filter_by(locator=locator).first()
        if submission and submission.check_code(code):
            session['reviewer_locator'] = locator
            session['reviewer_code'] = code
            return render_template('peer_review/reviewer/dashboard.html', tasks=[])

    flash('Credenciais inválidas para acesso de revisor.', 'danger')
    return redirect(url_for('evento_routes.home') + '#revisorModal')

@peer_review_routes.route('/peer-review/editor')
def editor_dashboard_page():
    return render_template('peer_review/editor/dashboard.html', decisions=[])


