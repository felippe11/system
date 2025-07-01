"""Rotas relacionadas ao processo seletivo de revisores (avaliadores).

Este blueprint permite que clientes configurem o processo, que candidatos
submetam formulários, acompanhem o andamento e que administradores aprovem
candidaturas. Também expõe endpoints para listar eventos elegíveis a partir
da perspectiva de participantes.
"""
from __future__ import annotations

import os
import uuid
from datetime import date, datetime
from typing import Any, Dict, List

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import or_
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from extensions import db
from models import (
    Assignment,
    CampoFormulario,
    Cliente,
    ConfiguracaoCliente,
    Evento,
    Formulario,
    RevisorCandidatura,
    RevisorCandidaturaEtapa,
    RevisorEtapa,
    RevisorProcess,
    Submission,
    Usuario,
)

# -----------------------------------------------------------------------------
# Blueprint
# -----------------------------------------------------------------------------
revisor_routes = Blueprint("revisor_routes", __name__, template_folder="../templates/revisor")


@revisor_routes.record_once
def _ensure_secret_key(setup_state):  # pragma: no cover
    """Garante que a aplicação tenha uma *secret_key* mesmo em dev."""
    app = setup_state.app
    if not app.secret_key:
        app.secret_key = "dev-secret-key"


# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DO PROCESSO PELO CLIENTE
# -----------------------------------------------------------------------------
@revisor_routes.route("/config_revisor", methods=["GET", "POST"])
@login_required
def config_revisor():
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    # Um cliente pode ter no máximo 1 processo configurado.
    processo: RevisorProcess | None = RevisorProcess.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).first()
    formularios: List[Formulario] = Formulario.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).all()

    if request.method == "POST":
        # --- coleta de dados do formulário -----------------------------------
        formulario_id = request.form.get("formulario_id", type=int)
        num_etapas = request.form.get("num_etapas", type=int, default=1)
        stage_names: List[str] = request.form.getlist("stage_name")
        start_raw = request.form.get("availability_start")
        end_raw = request.form.get("availability_end")
        exibir_val = request.form.get("exibir_participantes")
        exibir_para_participantes = exibir_val in {"on", "1", "true"}

        # --- parse de datas ---------------------------------------------------
        def _parse_dt(raw: str | None) -> datetime | None:
            try:
                return datetime.strptime(raw, "%Y-%m-%d") if raw else None
            except ValueError:
                return None

        start_dt = _parse_dt(start_raw)
        end_dt = _parse_dt(end_raw)

        # --- cria ou atualiza processo ---------------------------------------
        if not processo:
            processo = RevisorProcess(cliente_id=current_user.id)  # type: ignore[attr-defined]
            db.session.add(processo)

        processo.formulario_id = formulario_id
        processo.num_etapas = num_etapas
        processo.availability_start = start_dt
        processo.availability_end = end_dt
        processo.exibir_para_participantes = exibir_para_participantes
        db.session.commit()

        # --- (re)cria etapas --------------------------------------------------
        RevisorEtapa.query.filter_by(process_id=processo.id).delete()
        for idx, nome in enumerate(stage_names, start=1):
            if nome:
                db.session.add(RevisorEtapa(process_id=processo.id, numero=idx, nome=nome))
        db.session.commit()

        flash("Processo atualizado", "success")
        return redirect(url_for("revisor_routes.config_revisor"))

    etapas: List[RevisorEtapa] = processo.etapas if processo else []  # type: ignore[index]
    return render_template(
        "revisor/config.html", processo=processo, formularios=formularios, etapas=etapas
    )


# -----------------------------------------------------------------------------
# INSCRIÇÃO/CANDIDATURA PÚBLICA
# -----------------------------------------------------------------------------
@revisor_routes.route("/revisor/apply/<int:process_id>", methods=["GET", "POST"])
def submit_application(process_id: int):
    processo: RevisorProcess = RevisorProcess.query.get_or_404(process_id)
    formulario: Formulario | None = processo.formulario

    if not formulario:
        flash("Formulário não configurado.", "danger")
        return redirect(url_for("evento_routes.home"))

    if request.method == "POST":
        respostas: Dict[str, Any] = {}
        nome: str | None = None
        email: str | None = None

        for campo in formulario.campos:  # type: ignore[attr-defined]
            raw_val = request.form.get(str(campo.id))
            valor: Any = raw_val
            if campo.tipo == "file" and f"file_{campo.id}" in request.files:
                arquivo = request.files[f"file_{campo.id}"]
                if arquivo.filename:
                    filename = secure_filename(arquivo.filename)
                    path = os.path.join("uploads", "candidaturas", filename)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    arquivo.save(path)
                    valor = path
            respostas[campo.nome] = valor

            low = campo.nome.lower()
            if low == "nome":
                nome = valor  # type: ignore[assignment]
            elif low == "email":
                email = valor  # type: ignore[assignment]

        candidatura = RevisorCandidatura(
            process_id=process_id,
            respostas=respostas,
            nome=nome,
            email=email,
        )
        db.session.add(candidatura)
        db.session.commit()

        flash(f"Seu código: {candidatura.codigo}", "success")
        return redirect(url_for("revisor_routes.progress", codigo=candidatura.codigo))

    return render_template("revisor/candidatura_form.html", formulario=formulario)


@revisor_routes.route("/revisor/progress/<codigo>")
def progress(codigo: str):
    cand: RevisorCandidatura = RevisorCandidatura.query.filter_by(codigo=codigo).first_or_404()
    return render_template("revisor/progress.html", candidatura=cand)


@revisor_routes.route("/revisor/progress")
def progress_query():
    codigo = request.args.get("codigo")
    if codigo:
        return redirect(url_for("revisor_routes.progress", codigo=codigo))
    return redirect(url_for("evento_routes.home"))


# -----------------------------------------------------------------------------
# LISTAGEM DE EVENTOS COM PROCESSO ABERTO (VISÃO CANDIDATO)
# -----------------------------------------------------------------------------
@revisor_routes.route("/processo_seletivo")
def select_event():
    now = datetime.utcnow()

    eventos_proc = (
        db.session.query(Evento, RevisorProcess)
        .join(Cliente, Cliente.id == Evento.cliente_id)
        .join(ConfiguracaoCliente, ConfiguracaoCliente.cliente_id == Cliente.id)
        .join(RevisorProcess, RevisorProcess.cliente_id == Cliente.id)
        .filter(
            Evento.status == "ativo",
            Evento.publico.is_(True),
            ConfiguracaoCliente.habilitar_submissao_trabalhos.is_(True),
            or_(RevisorProcess.availability_start.is_(None), RevisorProcess.availability_start <= now),
            or_(RevisorProcess.availability_end.is_(None), RevisorProcess.availability_end >= now),
        )
        .all()
    )

    registros = [
        {"evento": ev, "processo": proc, "status": "Aberto" if proc.is_available() else "Encerrado"}
        for ev, proc in eventos_proc
    ]

    return render_template("revisor/select_event.html", eventos=registros)


# -----------------------------------------------------------------------------
# APROVAÇÃO DE CANDIDATURA (CLIENTE/ADMIN)
# -----------------------------------------------------------------------------
@revisor_routes.route("/revisor/approve/<int:cand_id>", methods=["POST"])
@login_required
def approve(cand_id: int):
    if current_user.tipo not in {"cliente", "admin", "superadmin"}:  # type: ignore[attr-defined]
        return jsonify({"success": False}), 403

    cand: RevisorCandidatura = RevisorCandidatura.query.get_or_404(cand_id)
    cand.status = "aprovado"
    cand.etapa_atual = cand.process.num_etapas  # type: ignore[attr-defined]

    # Cria (ou atualiza) usuário revisor
    reviewer: Usuario | None = Usuario.query.filter_by(email=cand.email).first()
    if not reviewer:
        reviewer = Usuario(
            nome=cand.nome or cand.email,
            cpf=str(uuid.uuid4()),
            email=cand.email,
            senha=generate_password_hash("temp123"),
            formacao="",
            tipo="revisor",
        )
        db.session.add(reviewer)
        db.session.flush()
    else:
        reviewer.tipo = "revisor"  # garante a role

    # Se informado, cria assignment imediato
    submission_id: int | None = (
        request.json.get("submission_id") if request.is_json else request.form.get("submission_id", type=int)
    )
    if submission_id:
        db.session.add(Assignment(submission_id=submission_id, reviewer_id=reviewer.id))

    db.session.commit()
    return jsonify({"success": True, "reviewer_id": reviewer.id})


# -----------------------------------------------------------------------------
# EVENTOS ELEGÍVEIS PARA PARTICIPANTES
# -----------------------------------------------------------------------------
@revisor_routes.route("/revisor/eligible_events")
def eligible_events():
    """Endpoint JSON que lista eventos com processo visível a participantes."""
    hoje = date.today()

    eventos = (
        Evento.query
        .join(RevisorProcess, Evento.cliente_id == RevisorProcess.cliente_id)
        .filter(
            Evento.status == "ativo",
            Evento.publico.is_(True),
            RevisorProcess.exibir_para_participantes.is_(True),
            or_(RevisorProcess.availability_start.is_(None), RevisorProcess.availability_start <= hoje),
            or_(RevisorProcess.availability_end.is_(None), RevisorProcess.availability_end >= hoje),
        )
        .distinct()
        .all()
    )

    return jsonify([{"id": e.id, "nome": e.nome} for e in eventos])
