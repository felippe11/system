# -*- coding: utf-8 -*-
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.user import Monitor, Ministrante
from models.formador import MaterialAprovado, SolicitacaoMaterial, FormadorMonitor
from utils.auth import monitor_required

monitor_formador_routes = Blueprint('monitor_formador_routes', __name__)


@monitor_formador_routes.route('/dashboard_monitor')
@login_required
@monitor_required
def dashboard_monitor():
    """Dashboard do monitor para gerenciar materiais dos formadores"""
    monitor = current_user
    
    # Buscar materiais aprovados para entrega
    materiais_pendentes = MaterialAprovado.query.filter_by(
        monitor_id=monitor.id,
        entregue=False
    ).join(SolicitacaoMaterial).all()
    
    # Buscar formadores associados
    formadores_associados = FormadorMonitor.query.filter_by(
        monitor_id=monitor.id,
        ativo=True
    ).all()
    
    # Buscar materiais já entregues (últimos 30 dias)
    materiais_entregues = MaterialAprovado.query.filter_by(
        monitor_id=monitor.id,
        entregue=True
    ).filter(
        MaterialAprovado.data_entrega >= datetime.utcnow().replace(day=1)
    ).join(SolicitacaoMaterial).all()
    
    return render_template(
        'monitor/dashboard.html',
        monitor=monitor,
        materiais_pendentes=materiais_pendentes,
        formadores_associados=formadores_associados,
        materiais_entregues=materiais_entregues
    )


@monitor_formador_routes.route('/entregar_material/<int:material_id>', methods=['POST'])
@login_required
@monitor_required
def entregar_material(material_id):
    """Marcar material como entregue"""
    material = MaterialAprovado.query.get_or_404(material_id)
    
    if material.monitor_id != current_user.id:
        flash('Acesso negado!', 'danger')
        return redirect(url_for('monitor_formador_routes.dashboard_monitor'))
    
    observacoes = request.form.get('observacoes_entrega', '')
    
    material.entregue = True
    material.data_entrega = datetime.utcnow()
    material.observacoes_entrega = observacoes
    
    db.session.commit()
    
    flash('Material marcado como entregue!', 'success')
    return redirect(url_for('monitor_formador_routes.dashboard_monitor'))


@monitor_formador_routes.route('/meus_formadores')
@login_required
@monitor_required
def meus_formadores():
    """Lista de formadores associados ao monitor"""
    formadores_associados = FormadorMonitor.query.filter_by(
        monitor_id=current_user.id,
        ativo=True
    ).all()
    
    return render_template(
        'monitor/meus_formadores.html',
        formadores_associados=formadores_associados
    )


@monitor_formador_routes.route('/historico_entregas')
@login_required
@monitor_required
def historico_entregas():
    """Histórico de entregas do monitor"""
    materiais_entregues = MaterialAprovado.query.filter_by(
        monitor_id=current_user.id,
        entregue=True
    ).join(SolicitacaoMaterial).order_by(
        MaterialAprovado.data_entrega.desc()
    ).all()
    
    return render_template(
        'monitor/historico_entregas.html',
        materiais_entregues=materiais_entregues
    )