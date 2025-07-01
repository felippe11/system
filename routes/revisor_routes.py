from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from extensions import db
from datetime import datetime
from models import (Formulario, CampoFormulario, RevisorProcess, RevisorEtapa,
                    RevisorCandidatura, RevisorCandidaturaEtapa, Usuario, Assignment, Submission)
import os
import uuid

revisor_routes = Blueprint('revisor_routes', __name__, template_folder="../templates/revisor")


@revisor_routes.record_once
def ensure_secret_key(setup_state):
    app = setup_state.app
    if not app.secret_key:
        app.secret_key = 'dev-secret-key'


@revisor_routes.route('/config_revisor', methods=['GET', 'POST'])
@login_required
def config_revisor():
    if current_user.tipo != 'cliente':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))

    processo = RevisorProcess.query.filter_by(cliente_id=current_user.id).first()
    formularios = Formulario.query.filter_by(cliente_id=current_user.id).all()

    if request.method == 'POST':
        formulario_id = request.form.get('formulario_id', type=int)
        num_etapas = request.form.get('num_etapas', type=int, default=1)
        stage_names = request.form.getlist('stage_name')
        titulo = request.form.get('titulo')
        data_inicio_raw = request.form.get('data_inicio')
        data_fim_raw = request.form.get('data_fim')
        exibir_val = request.form.get('exibir_participantes')
        exibir_participantes = exibir_val in ['on', '1', 'true']

        data_inicio = None
        if data_inicio_raw:
            try:
                data_inicio = datetime.strptime(data_inicio_raw, '%Y-%m-%d')
            except ValueError:
                data_inicio = None

        data_fim = None
        if data_fim_raw:
            try:
                data_fim = datetime.strptime(data_fim_raw, '%Y-%m-%d')
            except ValueError:
                data_fim = None
        if not processo:
            processo = RevisorProcess(cliente_id=current_user.id)
            db.session.add(processo)
        processo.formulario_id = formulario_id
        processo.num_etapas = num_etapas
        processo.titulo = titulo
        processo.data_inicio = data_inicio
        processo.data_fim = data_fim
        processo.exibir_participantes = exibir_participantes
        db.session.commit()
        RevisorEtapa.query.filter_by(process_id=processo.id).delete()
        for idx, nome in enumerate(stage_names, start=1):
            if nome:
                db.session.add(RevisorEtapa(process_id=processo.id, numero=idx, nome=nome))
        db.session.commit()
        flash('Processo atualizado', 'success')
        return redirect(url_for('revisor_routes.config_revisor'))

    etapas = processo.etapas if processo else []
    return render_template('revisor/config.html', processo=processo, formularios=formularios, etapas=etapas)


@revisor_routes.route('/revisor/apply/<int:process_id>', methods=['GET', 'POST'])
def submit_application(process_id):
    processo = RevisorProcess.query.get_or_404(process_id)
    formulario = processo.formulario
    if not formulario:
        flash('Formulário não configurado.', 'danger')
        return redirect(url_for('evento_routes.home'))

    if request.method == 'POST':
        respostas = {}
        nome = None
        email = None
        for campo in formulario.campos:
            valor = request.form.get(str(campo.id))
            if campo.tipo == 'file' and 'file_' + str(campo.id) in request.files:
                arquivo = request.files['file_' + str(campo.id)]
                if arquivo.filename:
                    filename = secure_filename(arquivo.filename)
                    path = os.path.join('uploads', 'candidaturas', filename)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    arquivo.save(path)
                    valor = path
            respostas[campo.nome] = valor
            low = campo.nome.lower()
            if low == 'nome':
                nome = valor
            if low == 'email':
                email = valor
        candidatura = RevisorCandidatura(
            process_id=process_id,
            respostas=respostas,
            nome=nome,
            email=email,
        )
        db.session.add(candidatura)
        db.session.commit()
        if current_app.secret_key:
            flash(f'Seu código: {candidatura.codigo}', 'success')
        return redirect(url_for('revisor_routes.progress', codigo=candidatura.codigo))

    return render_template('revisor/candidatura_form.html', formulario=formulario)


@revisor_routes.route('/revisor/progress/<codigo>')
def progress(codigo):
    cand = RevisorCandidatura.query.filter_by(codigo=codigo).first_or_404()
    try:
        return render_template('revisor/progress.html', candidatura=cand)
    except Exception:
        return f"Status: {cand.status}", 200


@revisor_routes.route('/revisor/progress')
def progress_query():
    codigo = request.args.get('codigo')
    if codigo:
        return redirect(url_for('revisor_routes.progress', codigo=codigo))
    return redirect(url_for('evento_routes.home'))


@revisor_routes.route('/revisor/approve/<int:cand_id>', methods=['POST'])
@login_required
def approve(cand_id):
    if current_user.tipo not in ('cliente', 'admin', 'superadmin'):
        return jsonify({'success': False}), 403
    cand = RevisorCandidatura.query.get_or_404(cand_id)
    cand.status = 'aprovado'
    cand.etapa_atual = cand.process.num_etapas
    reviewer = Usuario.query.filter_by(email=cand.email).first()
    if not reviewer:
        reviewer = Usuario(
            nome=cand.nome or cand.email,
            cpf=str(uuid.uuid4()),
            email=cand.email,
            senha=generate_password_hash('temp123'),
            formacao='',
            tipo='revisor'
        )
        db.session.add(reviewer)
        db.session.flush()
    else:
        reviewer.tipo = 'revisor'
    submission_id = None
    if request.is_json:
        submission_id = request.json.get('submission_id')
    else:
        submission_id = request.form.get('submission_id', type=int)
    if submission_id:
        db.session.add(Assignment(submission_id=submission_id, reviewer_id=reviewer.id))
    db.session.commit()
    return jsonify({'success': True, 'reviewer_id': reviewer.id})
