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
from sqlalchemy import func, desc
from sqlalchemy.orm import selectinload

from models import (

    Assignment,
    CampoFormulario,
    Cliente,
    ConfiguracaoCliente,

    Evento,
    Formulario,


    EventoBarema,

    RevisorCandidatura,
    RevisorCandidaturaEtapa,
    RevisorEtapa,
    RevisorProcess,
    revisor_process_evento_association,
    Submission,
    Review,
    Usuario,
)
from tasks import send_email_task
from services.pdf_service import gerar_revisor_details_pdf
import utils.revisor_helpers as rh

parse_revisor_form = rh.parse_revisor_form
recreate_stages = rh.recreate_stages
update_process_eventos = rh.update_process_eventos
update_revisor_process = rh.update_revisor_process
recreate_criterios = getattr(rh, "recreate_criterios", lambda *a, **k: None)


# Extensões permitidas para upload de arquivos
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx"}

# -----------------------------------------------------------------------------
# Blueprint
# -----------------------------------------------------------------------------
revisor_routes = Blueprint(
    "revisor_routes", __name__, template_folder="../templates/revisor"
)


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
    eventos: List[Evento] = Evento.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).all()
    selected_event_ids: List[int] = [e.id for e in processo.eventos] if processo else []


    if request.method == "POST":
        dados = parse_revisor_form(request)
        if not processo:
            processo = RevisorProcess(cliente_id=current_user.id)  # type: ignore[attr-defined]
            db.session.add(processo)
        update_revisor_process(processo, dados)
        update_process_eventos(processo, dados["eventos_ids"])
        recreate_stages(processo, dados["stage_names"])
        recreate_criterios(processo, dados["criterios"])
        flash("Processo atualizado", "success")
        return redirect(url_for("revisor_routes.config_revisor"))

    etapas: List[RevisorEtapa] = processo.etapas if processo else []  # type: ignore[index]
    criterios = processo.criterios if processo else []  # type: ignore[attr-defined]
    return render_template(
        "revisor/config.html",
        processo=processo,
        formularios=formularios,
        etapas=etapas,
        criterios=criterios,
        eventos=eventos,
        selected_event_ids=selected_event_ids,
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
            key = str(campo.id)
            valor: Any = None
            is_required = getattr(campo, "obrigatorio", False)

            if campo.tipo == "file":
                file_key = f"file_{campo.id}"
                arquivo = request.files.get(file_key)
                if is_required and (not arquivo or not arquivo.filename):
                    flash(f"O campo {campo.nome} é obrigatório.", "danger")
                    return redirect(request.url)
                if arquivo and arquivo.filename:
                    filename = secure_filename(arquivo.filename)
                    ext = os.path.splitext(filename)[1].lower()
                    if ext not in ALLOWED_EXTENSIONS:
                        flash("Extensão de arquivo não permitida.", "danger")
                        return redirect(request.url)
                    unique_name = (
                        f"{uuid.uuid4().hex}_"
                        f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{ext}"
                    )
                    dir_path = os.path.join("uploads", "candidaturas", str(process_id))
                    os.makedirs(dir_path, exist_ok=True)
                    path = os.path.join(dir_path, unique_name)
                    arquivo.save(path)
                    valor = path
            else:
                raw_val = request.form.get(key)
                if is_required and not raw_val:
                    flash(f"O campo {campo.nome} é obrigatório.", "danger")
                    return redirect(request.url)
                valor = raw_val

            respostas[campo.nome] = valor

            low = campo.nome.lower()
            if low == "nome":
                nome = valor  # type: ignore[assignment]
            elif low == "email":
                email = valor  # type: ignore[assignment]

        if email and RevisorCandidatura.query.filter_by(
            process_id=process_id, email=email
        ).first():
            flash(
                "Já existe uma candidatura com este e-mail para este processo.",
                "danger",
            )
            return redirect(request.url)

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
    cand: RevisorCandidatura = RevisorCandidatura.query.filter_by(
        codigo=codigo
    ).first_or_404()
    pdf_url = url_for("revisor_routes.progress_pdf", codigo=codigo)
    return render_template("revisor/progress.html", candidatura=cand, pdf_url=pdf_url)


@revisor_routes.route("/revisor/progress/<codigo>/pdf")
def progress_pdf(codigo: str):
    cand: RevisorCandidatura = RevisorCandidatura.query.filter_by(
        codigo=codigo
    ).first_or_404()
    return gerar_revisor_details_pdf(cand)


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
    """Lista eventos com processo seletivo visível a participantes."""
    now = datetime.utcnow()

    processos = (
        RevisorProcess.query.options(selectinload(RevisorProcess.eventos))
        .filter(
            RevisorProcess.exibir_para_participantes.is_(True),
            or_(
                RevisorProcess.availability_start.is_(None),
                RevisorProcess.availability_start <= now,
            ),
            or_(
                RevisorProcess.availability_end.is_(None),
                RevisorProcess.availability_end >= now,
            ),
        )
        .all()
    )

    registros: list[dict[str, object]] = []
    for proc in processos:
        eventos = list(proc.eventos)
        if not eventos and proc.evento_id:
            ev = Evento.query.get(proc.evento_id)
            if ev:
                eventos.append(ev)

        if not eventos:
            registros.append(
                {
                    "evento": None,
                    "processo": proc,
                    "status": "Aberto" if proc.is_available() else "Encerrado",
                }
            )
            continue

        for ev in eventos:
            if ev.status == "ativo" and ev.publico:
                registros.append(
                    {
                        "evento": ev,
                        "processo": proc,
                        "status": "Aberto" if proc.is_available() else "Encerrado",
                    }
                )

    if not registros:
        flash(
            "Nenhum processo seletivo de revisores disponível no momento.",
            "info",
        )

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

    config_cli = ConfiguracaoCliente.query.filter_by(
        cliente_id=cand.process.cliente_id
    ).first()
    if config_cli:
        aprovados = (
            RevisorCandidatura.query.join(
                RevisorProcess, RevisorCandidatura.process_id == RevisorProcess.id
            )
            .filter(
                RevisorProcess.cliente_id == cand.process.cliente_id,
                RevisorCandidatura.status == "aprovado",
            )
            .count()
        )
        if (
            config_cli.limite_revisores is not None
            and aprovados >= config_cli.limite_revisores
        ):
            flash("Limite de revisores atingido.", "danger")
            return redirect(url_for("dashboard_routes.dashboard_cliente"))
    cand.status = "aprovado"
    cand.etapa_atual = cand.process.num_etapas  # type: ignore[attr-defined]

    reviewer: Usuario | None = None
    if cand.email:
        # Cria (ou atualiza) usuário revisor
        reviewer = Usuario.query.filter_by(email=cand.email).first()
        if not reviewer:
            reviewer = Usuario(
                nome=cand.nome or cand.email,
                cpf=str(uuid.uuid4().int)[:11],
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
        request.json.get("submission_id")
        if request.is_json
        else request.form.get("submission_id", type=int)
    )
    if submission_id and reviewer:
        db.session.add(Assignment(submission_id=submission_id, reviewer_id=reviewer.id))

    db.session.commit()
    if cand.email:
        send_email_task.delay(
            cand.email,
            cand.nome or "",
            "Processo Seletivo de Revisores",
            "Atualização de status da candidatura",
            "",
            template_path="emails/revisor_status_change.html",
            template_context={"status": cand.status, "codigo": cand.codigo},
        )
    msg = "Candidatura aprovada"
    if request.is_json:
        resp = {"success": True}
        if reviewer:
            resp["reviewer_id"] = reviewer.id
        resp["message"] = msg
        return jsonify(resp)
    flash(msg, "success")
    return redirect(url_for("dashboard_routes.dashboard_cliente"))


@revisor_routes.route("/revisor/reject/<int:cand_id>", methods=["POST"])
@login_required
def reject(cand_id: int):
    """Marca a candidatura como rejeitada."""
    if current_user.tipo not in {"cliente", "admin", "superadmin"}:  # type: ignore[attr-defined]
        return jsonify({"success": False}), 403

    cand: RevisorCandidatura = RevisorCandidatura.query.get_or_404(cand_id)
    cand.status = "rejeitado"
    db.session.commit()
    if cand.email:
        send_email_task.delay(
            cand.email,
            cand.nome or "",
            "Processo Seletivo de Revisores",
            "Atualização de status da candidatura",
            "",
            template_path="emails/revisor_status_change.html",
            template_context={"status": cand.status, "codigo": cand.codigo},
        )
    if request.is_json:
        return jsonify({"success": True})
    return redirect(url_for("dashboard_routes.dashboard_cliente"))


@revisor_routes.route("/revisor/advance/<int:cand_id>", methods=["POST"])
@login_required
def advance(cand_id: int):
    """Avança a candidatura para a próxima etapa."""
    if current_user.tipo not in {"cliente", "admin", "superadmin"}:  # type: ignore[attr-defined]
        return jsonify({"success": False}), 403

    cand: RevisorCandidatura = RevisorCandidatura.query.get_or_404(cand_id)

    current_num = cand.etapa_atual
    curr_etapa = RevisorEtapa.query.filter_by(
        process_id=cand.process_id, numero=current_num
    ).first()
    if curr_etapa:
        curr_status = RevisorCandidaturaEtapa.query.filter_by(
            candidatura_id=cand.id, etapa_id=curr_etapa.id
        ).first()
        if not curr_status:
            curr_status = RevisorCandidaturaEtapa(
                candidatura_id=cand.id, etapa_id=curr_etapa.id
            )
            db.session.add(curr_status)
        curr_status.status = "concluída"

    if current_num < cand.process.num_etapas:
        cand.etapa_atual = current_num + 1
        next_etapa = RevisorEtapa.query.filter_by(
            process_id=cand.process_id, numero=cand.etapa_atual
        ).first()
        if next_etapa:
            next_status = RevisorCandidaturaEtapa.query.filter_by(
                candidatura_id=cand.id, etapa_id=next_etapa.id
            ).first()
            if not next_status:
                next_status = RevisorCandidaturaEtapa(
                    candidatura_id=cand.id, etapa_id=next_etapa.id
                )
                db.session.add(next_status)
            next_status.status = "em_andamento"

    db.session.commit()
    if cand.email:
        send_email_task.delay(
            cand.email,
            cand.nome or "",
            "Processo Seletivo de Revisores",
            "Atualização de status da candidatura",
            "",
            template_path="emails/revisor_status_change.html",
            template_context={"status": cand.status, "codigo": cand.codigo},
        )
    if request.is_json:
        return jsonify({"success": True, "etapa_atual": cand.etapa_atual})
    return redirect(url_for("dashboard_routes.dashboard_cliente"))


@revisor_routes.route("/revisor/view/<int:cand_id>")
@login_required
def view_candidatura(cand_id: int):
    """Exibe os detalhes e respostas de uma candidatura."""
    if current_user.tipo not in {"cliente", "admin", "superadmin"}:  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    cand: RevisorCandidatura = RevisorCandidatura.query.get_or_404(cand_id)
    return render_template("revisor/candidatura_detail.html", candidatura=cand)


# -----------------------------------------------------------------------------
# AVALIAÇÃO DE TRABALHOS
# -----------------------------------------------------------------------------
@revisor_routes.route("/revisor/avaliar/<int:submission_id>", methods=["GET", "POST"])
@login_required
def avaliar(submission_id: int):
    """Permite ao revisor atribuir notas a uma submissão com base no barema."""
    submission = Submission.query.get_or_404(submission_id)
    barema = EventoBarema.query.filter_by(evento_id=submission.evento_id).first()
    review = Review.query.filter_by(
        submission_id=submission.id, reviewer_id=current_user.id
    ).first()

    if request.method == "POST" and barema:
        scores: Dict[str, int] = {}
        for requisito, _max in barema.requisitos.items():
            nota_raw = request.form.get(requisito)
            if nota_raw:
                scores[requisito] = int(nota_raw)

        if review is None:
            review = Review(
                submission_id=submission.id, reviewer_id=current_user.id
            )
        review.scores = scores
        db.session.add(review)
        db.session.commit()
        flash("Avaliação registrada", "success")
        return redirect(url_for("revisor_routes.avaliar", submission_id=submission.id))

    return render_template(
        "revisor/avaliacao.html", submission=submission, barema=barema, review=review
    )


# -----------------------------------------------------------------------------
# EVENTOS ELEGÍVEIS PARA PARTICIPANTES
# -----------------------------------------------------------------------------
@revisor_routes.route("/revisor/eligible_events")
def eligible_events():
    """Endpoint JSON que lista eventos com processo visível a participantes."""
    hoje = date.today()

    eventos = (
        Evento.query.join(
            RevisorProcess, Evento.cliente_id == RevisorProcess.cliente_id
        )
        .filter(
            Evento.status == "ativo",
            Evento.publico.is_(True),
            RevisorProcess.exibir_para_participantes.is_(True),
            or_(
                RevisorProcess.availability_start.is_(None),
                RevisorProcess.availability_start <= hoje,
            ),
            or_(
                RevisorProcess.availability_end.is_(None),
                RevisorProcess.availability_end >= hoje,
            ),
        )
        .distinct()
        .all()
    )

    return jsonify([{"id": e.id, "nome": e.nome} for e in eventos])


@revisor_routes.route("/ranking_trabalhos")
@login_required
def ranking_trabalhos():
    """Lista trabalhos com a soma das notas recebidas.

    Permite ordenar por qualquer campo de ``Submission`` através do
    parâmetro de query ``ordenar_por``. Quando não informado, ordena pelo
    total de notas (``total_nota``) de forma decrescente.
    """

    if current_user.tipo not in ("cliente", "admin", "superadmin"):
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    ordenar_por = request.args.get("ordenar_por", "total_nota")

    notas_sub = (
        db.session.query(
            Review.submission_id.label("sub_id"),
            func.coalesce(func.sum(Review.note), 0).label("total_nota"),
        )
        .group_by(Review.submission_id)
        .subquery()
    )

    query = (
        db.session.query(Submission, notas_sub.c.total_nota)
        .outerjoin(notas_sub, Submission.id == notas_sub.c.sub_id)
    )

    if ordenar_por != "total_nota" and hasattr(Submission, ordenar_por):
        query = query.order_by(getattr(Submission, ordenar_por))
    else:
        ordenar_por = "total_nota"
        query = query.order_by(desc(notas_sub.c.total_nota))

    resultados = [
        {"submission": sub, "total_nota": nota or 0} for sub, nota in query.all()
    ]

    return render_template(
        "revisor/ranking.html",
        resultados=resultados,
        ordenar_por=ordenar_por,
    )
