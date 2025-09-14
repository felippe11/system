from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from extensions import db
from models import Feedback, Oficina
from models.user import Cliente
from utils import endpoints

feedback_routes = Blueprint('feedback_routes', __name__)


@feedback_routes.route('/feedback_ministrante/<int:oficina_id>', methods=['GET', 'POST'])
@login_required
def feedback_ministrante(oficina_id):
    # Verifica se o usuário é um ministrante
    if current_user.tipo != 'ministrante':
        flash('Apenas ministrantes podem enviar feedback por aqui.', 'danger')
        return redirect(url_for('formador_routes.dashboard_formador'))
    
    oficina = Oficina.query.get_or_404(oficina_id)
    
    if request.method == 'POST':
        try:
            rating = int(request.form.get('rating', 0))
        except ValueError:
            rating = 0
        comentario = request.form.get('comentario', '').strip()
        if rating < 1 or rating > 5:
            flash('A avaliação deve ser entre 1 e 5 estrelas.', 'danger')
            return redirect(url_for('feedback_routes.feedback_ministrante', oficina_id=oficina_id))
        
        novo_feedback = Feedback(
            ministrante_id=current_user.id,  # Salva o id do ministrante
            oficina_id=oficina.id,
            rating=rating,
            comentario=comentario
        )
        db.session.add(novo_feedback)
        db.session.commit()
        flash('Feedback enviado com sucesso!', 'success')
        return redirect(url_for('formador_routes.dashboard_formador'))
    
    # Reaproveita o template existente (feedback.html) ou crie um específico se desejar
    return render_template('feedback.html', oficina=oficina)


@feedback_routes.route('/feedback/<int:oficina_id>', methods=['GET', 'POST'])
@login_required
def feedback(oficina_id):
    oficina = Oficina.query.get_or_404(oficina_id)
    if current_user.tipo != 'participante':
        flash('Apenas participantes podem enviar feedback.', 'danger')
        return redirect(url_for(endpoints.DASHBOARD))
    if request.method == 'POST':
        try:
            rating = int(request.form.get('rating', 0))
        except ValueError:
            rating = 0
        comentario = request.form.get('comentario', '').strip()
        if rating < 1 or rating > 5:
            flash('A avaliação deve ser entre 1 e 5 estrelas.', 'danger')
            return redirect(url_for('feedback_routes.feedback', oficina_id=oficina_id))
        novo_feedback = Feedback(
            usuario_id=current_user.id,
            oficina_id=oficina.id,
            rating=rating,
            comentario=comentario
        )
        db.session.add(novo_feedback)
        db.session.commit()
        flash('Feedback enviado com sucesso!', 'success')
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))
    return render_template('feedback.html', oficina=oficina)

@feedback_routes.route('/feedback_oficina/<int:oficina_id>')
@login_required
def feedback_oficina(oficina_id):
    oficina = Oficina.query.get_or_404(oficina_id)  # Primeiro
    if current_user.tipo not in ['admin', 'cliente'] or (current_user.tipo == 'cliente' and oficina.cliente_id != current_user.id and oficina.cliente_id is not None):
        flash('Você não tem permissão para visualizar o feedback desta oficina.', 'danger')
        

    # Obtendo clientes para filtro (somente admin pode visualizar)
    clientes = Cliente.query.all() if current_user.tipo == 'admin' else []

    # Cálculo das estatísticas gerais (sem os filtros da query abaixo)
    total_feedbacks_all = Feedback.query.filter_by(oficina_id=oficina_id).all()
    total_count = len(total_feedbacks_all)
    total_avg = (sum(fb.rating for fb in total_feedbacks_all) / total_count) if total_count > 0 else 0

    feedbacks_usuarios = Feedback.query.filter(
        Feedback.oficina_id == oficina_id,
        Feedback.usuario_id.isnot(None)
    ).all()
    count_usuarios = len(feedbacks_usuarios)
    avg_usuarios = (sum(fb.rating for fb in feedbacks_usuarios) / count_usuarios) if count_usuarios > 0 else 0

    feedbacks_ministrantes = Feedback.query.filter(
        Feedback.oficina_id == oficina_id,
        Feedback.ministrante_id.isnot(None)
    ).all()
    count_ministrantes = len(feedbacks_ministrantes)
    avg_ministrantes = (sum(fb.rating for fb in feedbacks_ministrantes) / count_ministrantes) if count_ministrantes > 0 else 0

    # Filtros
    tipo = request.args.get('tipo')
    estrelas = request.args.get('estrelas')
    cliente_filter = request.args.get('cliente_id')

    query = Feedback.query.join(Oficina).filter(Feedback.oficina_id == oficina_id)

    # Filtra pelo tipo de feedback (usuário ou ministrante)
    if tipo == 'usuario':
        query = query.filter(Feedback.usuario_id.isnot(None))
    elif tipo == 'ministrante':
        query = query.filter(Feedback.ministrante_id.isnot(None))

    # Filtra pelo número de estrelas
    if estrelas and estrelas.isdigit():
        query = query.filter(Feedback.rating == int(estrelas))

    # Filtra pelo cliente selecionado (somente admins)
    if current_user.tipo == 'admin' and cliente_filter and cliente_filter.isdigit():
        query = query.filter(Oficina.cliente_id == int(cliente_filter))

    feedbacks = query.order_by(Feedback.created_at.desc()).all()

    
    return render_template('oficina/feedback_oficina.html', oficina=oficina, feedbacks=feedbacks,
                           total_count=total_count, total_avg=total_avg,
                           count_ministrantes=count_ministrantes, avg_ministrantes=avg_ministrantes,
                           count_usuarios=count_usuarios, avg_usuarios=avg_usuarios,  is_admin=current_user.tipo == 'admin', clientes=clientes, cliente_filter=cliente_filter)
