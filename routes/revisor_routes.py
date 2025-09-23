<<<<<<< HEAD
"""Rotas relacionadas ao processo seletivo de revisores (avaliadores).

Este blueprint permite que clientes configurem o processo, que candidatos
submetam formulários, acompanhem o andamento e que administradores aprovem
candidaturas. Também expõe endpoints para listar eventos elegíveis a partir
da perspectiva de participantes.
"""

from __future__ import annotations
from utils import endpoints
from utils.barema import normalize_barema_requisitos

import json
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
from sqlalchemy.exc import ProgrammingError

from models import (
    Assignment,
    Cliente,
    ConfiguracaoCliente,
    Evento,
    Formulario,
    EventoBarema,
    ProcessoBarema,
    ProcessoBaremaRequisito,
    RevisorCandidatura,
    RevisorCandidaturaEtapa,
    RevisorEtapa,
    RevisorProcess,
    revisor_process_evento_association,
    Submission,
    Review,
    Usuario,
)
from models.event import CampoFormulario, RespostaCampoFormulario, RespostaFormulario
from models.review import CategoriaBarema
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
# PROCESSOS DO REVISOR
# -----------------------------------------------------------------------------



@revisor_routes.route("/revisor/processos", methods=["GET"])
@login_required
def list_processes() -> Any:
    """List all review processes for the logged client."""

    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))

    processos = RevisorProcess.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).all()
    
    return render_template("revisor/process_list.html", processos=processos)


@revisor_routes.route("/revisor/processos/novo", methods=["GET"])
@login_required
def new_process():
    """Render form to create a new review process."""
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    
    formularios: List[Formulario] = Formulario.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).all()
    eventos: List[Evento] = Evento.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).all()
    
    # Create empty process for form rendering
    processo = RevisorProcess(cliente_id=current_user.id, num_etapas=1)  # type: ignore[attr-defined]
    
    return render_template(
        "revisor/config.html",
        processo=processo,
        formularios=formularios,
        etapas=[],
        criterios=[],
        eventos=eventos,
        selected_event_ids=[],
        is_new=True
    )


@revisor_routes.route("/revisor/processos", methods=["POST"])
@login_required
def create_process() -> Any:
    """Create a new review process for the current client."""
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    try:
        dados = parse_revisor_form(request)
    except ValueError as exc:
        flash(str(exc), "danger")
        return jsonify({"error": str(exc)}), 400

    created_form: Formulario | None = None
    if not dados.get("formulario_id"):
        created_form = Formulario(
            nome="Formulário de Candidatura",
            cliente_id=current_user.id,  # type: ignore[attr-defined]
        )
        db.session.add(created_form)
        db.session.flush()
        rh.ensure_reviewer_required_fields(created_form)
        dados["formulario_id"] = created_form.id

    processo = RevisorProcess(
        cliente_id=current_user.id,  # type: ignore[attr-defined]
        nome=dados["nome"],
    )
    db.session.add(processo)
    update_revisor_process(processo, dados)
    db.session.flush()
    update_process_eventos(processo, dados.get("eventos_ids", []))
    recreate_stages(processo, dados.get("stage_names", []))
    recreate_criterios(processo, dados.get("criterios", []))
    if created_form is None and processo.formulario_id:
        formulario = Formulario.query.get(processo.formulario_id)
        if formulario:
            rh.ensure_reviewer_required_fields(formulario)
    

    
    db.session.commit()
    flash("Processo criado com sucesso!", "success")
    return redirect(url_for("revisor_routes.edit_process", process_id=processo.id))


@revisor_routes.route("/revisor/processos/<int:process_id>", methods=["GET", "POST"])
@login_required
def edit_process(process_id: int):
    """Render or update a specific review process."""
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    
    # Check if process exists
    processo = RevisorProcess.query.filter_by(
        id=process_id, 
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).first()
    
    if not processo:
        flash("Processo não encontrado. Crie um novo processo ou edite um existente.", "warning")
        return redirect(url_for("revisor_routes.list_processes"))
    
    if processo.cliente_id != current_user.id:  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))


    formularios: List[Formulario] = Formulario.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).all()
    eventos: List[Evento] = Evento.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).all()

    selected_event_ids: List[int] = [e.id for e in processo.eventos]


    if request.method == "POST":
        try:
            dados = parse_revisor_form(request)
        except ValueError as exc:
            flash(str(exc), "danger")

            return redirect(
                url_for("revisor_routes.edit_process", process_id=processo.id)

            )
        update_revisor_process(processo, dados)

        update_process_eventos(processo, dados.get("eventos_ids", []))
        recreate_criterios(processo, dados.get("criterios", []))
        if processo.formulario_id:

            formulario = Formulario.query.get(processo.formulario_id)
            if formulario:
                rh.ensure_reviewer_required_fields(formulario)
        

        
        db.session.commit()
        flash("Processo atualizado", "success")

        return redirect(
            url_for("revisor_routes.edit_process", process_id=processo.id)
        )


    try:
        criterios = processo.criterios  # type: ignore[attr-defined]
    except ProgrammingError as exc:  # pragma: no cover - depends on db state
        current_app.logger.error("Erro ao acessar criterios: %s", exc)
        flash(
            "Banco de dados desatualizado. Administradores: executem as migrações.",
            "warning",
        )
        criterios = []
    # Determinar se é um novo processo
    is_new = processo.id is None
    
    return render_template(
        "revisor/config.html",
        processo=processo,
        formularios=formularios,
        criterios=criterios,
        eventos=eventos,
        selected_event_ids=selected_event_ids,
        is_new=is_new,
    )



# Compat: rota antiga que redireciona para o fluxo atual
@revisor_routes.route("/config_revisor", methods=["GET", "POST"])
@login_required
def config_revisor():
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))

    processo = RevisorProcess.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).first()

    if processo is None:
        processo = RevisorProcess(cliente_id=current_user.id)  # type: ignore[attr-defined]
        db.session.add(processo)
        db.session.commit()

    return redirect(url_for("revisor_routes.edit_process", process_id=processo.id))


@revisor_routes.route("/revisor/config", methods=["GET"])
@login_required
def config_overview():
    """Main configuration page for reviewer processes.
    
    Lists all existing reviewer processes for the current client
    and provides options to create new ones or edit existing ones.
    """
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    
    # Get all reviewer processes for the current client
    processos = RevisorProcess.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).all()
    
    # Get all forms for the current client
    formularios = Formulario.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).all()
    
    # Get all events for the current client
    eventos = Evento.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).all()
    
    return render_template(
        "revisor/config_overview.html",
        processos=processos,
        formularios=formularios,
        eventos=eventos,
    )


@revisor_routes.route("/revisor/processes/<int:process_id>/delete", methods=["POST"])
@revisor_routes.route("/revisor/<int:process_id>/delete", methods=["POST"])
@login_required
def delete_process(process_id: int):
    """Remove a review process owned by the current client."""
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    processo = RevisorProcess.query.get_or_404(process_id)
    if processo.cliente_id != current_user.id:  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    db.session.delete(processo)
    db.session.commit()
    if request.method == "DELETE":
        return "", 204
    flash("Processo removido", "success")
    return redirect(url_for("revisor_routes.list_processes"))


# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DE BAREMAS
# -----------------------------------------------------------------------------
@revisor_routes.route("/revisor/<int:process_id>/barema")
@login_required
def manage_barema(process_id: int):
    """Display and ensure a barema exists for the given process.

    Args:
        process_id: Identifier of the review process.

    Returns:
        Response rendering the barema management page.
    """
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    processo = RevisorProcess.query.get_or_404(process_id)
    barema = ProcessoBarema.query.filter_by(process_id=process_id).first()
    if barema is None:
        barema = ProcessoBarema(process_id=process_id)
        db.session.add(barema)
        db.session.commit()
    requisitos = barema.requisitos
    return render_template(
        "revisor/barema_form.html",
        processo=processo,
        barema=barema,
        requisitos=requisitos,
    )


@revisor_routes.route(
    "/revisor/barema/<int:barema_id>/requisito/new", methods=["GET", "POST"]
)
@login_required
def add_requisito(barema_id: int):
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    barema = ProcessoBarema.query.get_or_404(barema_id)

    if request.method == "POST":
        requisito = ProcessoBaremaRequisito(
            barema_id=barema_id,
            nome=request.form.get("nome") or "",
            descricao=request.form.get("descricao"),
            pontuacao_min=request.form.get("pontuacao_min", type=float) or 0,
            pontuacao_max=request.form.get("pontuacao_max", type=float) or 0,
        )
        if requisito.pontuacao_min > requisito.pontuacao_max:
            error = "Pontuação mínima não pode ser maior que a máxima."
            flash(error, "danger")
            return render_template(
                "revisor/requisito_form.html",
                barema=barema,
                requisito=requisito,
                error=error,
            )
        db.session.add(requisito)
        db.session.commit()
        flash("Requisito adicionado", "success")
        return redirect(
            url_for("revisor_routes.manage_barema", process_id=barema.process_id)
        )
    return render_template(
        "revisor/requisito_form.html", barema=barema, requisito=None
    )


@revisor_routes.route(
    "/revisor/requisito/<int:req_id>/edit", methods=["GET", "POST"]
)
@login_required
def edit_requisito(req_id: int):
    requisito = ProcessoBaremaRequisito.query.get_or_404(req_id)
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")


        return redirect(url_for(endpoints.DASHBOARD))
    if request.method == "POST":
        requisito.nome = request.form.get("nome") or requisito.nome
        requisito.descricao = request.form.get("descricao")
        requisito.pontuacao_min = (
            request.form.get("pontuacao_min", type=float) or 0
        )
        requisito.pontuacao_max = (
            request.form.get("pontuacao_max", type=float) or 0
        )
        if requisito.pontuacao_min > requisito.pontuacao_max:
            error = "Pontuação mínima não pode ser maior que a máxima."
            flash(error, "danger")
            return render_template(
                "revisor/requisito_form.html",
                barema=requisito.barema,
                requisito=requisito,
                error=error,
            )
        db.session.commit()
        flash("Requisito atualizado", "success")
        return redirect(
            url_for(
                "revisor_routes.manage_barema",
                process_id=requisito.barema.process_id,
            )
        )
    return render_template(
        "revisor/requisito_form.html",
        barema=requisito.barema,
        requisito=requisito,
    )


@revisor_routes.route(
    "/revisor/requisito/<int:req_id>/delete", methods=["POST"]

)
@login_required
def delete_requisito(req_id: int):
    requisito = ProcessoBaremaRequisito.query.get_or_404(req_id)
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")

        return redirect(url_for(endpoints.DASHBOARD))
    process_id = requisito.barema.process_id
    db.session.delete(requisito)
    db.session.commit()
    flash("Requisito removido", "success")
    return redirect(url_for("revisor_routes.manage_barema", process_id=process_id))


@revisor_routes.route(
    "/revisor/<int:process_id>/barema/delete", methods=["POST"]

)
@login_required
def delete_barema(process_id: int):
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    barema = ProcessoBarema.query.filter_by(process_id=process_id).first_or_404()

    db.session.delete(barema)
    db.session.commit()
    flash("Barema removido", "success")
    return redirect(url_for("revisor_routes.manage_barema", process_id=process_id))


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
            elif campo.tipo == "checkbox":
                valores = request.form.getlist(key)
                if is_required and not valores:
                    flash(f"O campo {campo.nome} é obrigatório.", "danger")
                    return redirect(request.url)
                valor = valores
            elif campo.tipo == "radio":
                raw_val = request.form.get(key)
                if is_required and not raw_val:
                    flash(f"O campo {campo.nome} é obrigatório.", "danger")
                    return redirect(request.url)
                if raw_val and campo.opcoes:
                    opcoes_validas = [o.strip() for o in campo.opcoes.split(",")]
                    if raw_val not in opcoes_validas:
                        flash("Opção inválida.", "danger")
                        return redirect(request.url)
                valor = raw_val
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

        # Validação obrigatória para nome e email
        if not nome:
            flash("O campo Nome é obrigatório.", "danger")
            return redirect(request.url)
        
        if not email:
            flash("O campo E-mail é obrigatório.", "danger")
            return redirect(request.url)

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

    # Ordenar todos os campos pela ordem
    campos_ordenados = sorted(formulario.campos, key=lambda c: getattr(c, 'ordem', 0) or 0)
    
    return render_template(
        "revisor/candidatura_form.html", 
        formulario=formulario, 
        processo=processo,
        campos=campos_ordenados
    )


@revisor_routes.route("/revisor/progress/<codigo>")
def progress(codigo: str):
    cand: RevisorCandidatura = RevisorCandidatura.query.filter_by(
        codigo=codigo
    ).first_or_404()

    trabalhos_designados = []
    if cand.status == 'aprovado':
        revisor_user = Usuario.query.filter_by(email=cand.email).first()
        if revisor_user:
            # Determinar o evento associado à candidatura
            processo = cand.process
            evento_id = None
            
            if processo.evento_id:
                evento_id = processo.evento_id
            elif processo.eventos:
                evento_id = processo.eventos[0].id  # Usar o primeiro evento associado
            
            # Buscar assignments do revisor filtrados por evento (se disponível)
            query = (
                Assignment.query
                .options(
                    db.joinedload(Assignment.resposta_formulario),
                    db.joinedload(Assignment.reviewer)
                )
                .filter_by(reviewer_id=revisor_user.id)
                # Garantir que apenas assignments distribuídos sejam mostrados
                .filter(Assignment.distribution_date.isnot(None))
            )
            
            # Filtrar por evento se disponível
            if evento_id:
                from models.event import RespostaFormulario

                query = (
                    query.join(
                        RespostaFormulario,
                        Assignment.resposta_formulario_id == RespostaFormulario.id,
                    ).filter(RespostaFormulario.evento_id == evento_id)
                )

            assignments = query.all()

            for assignment in assignments:
                resposta = assignment.resposta_formulario
                if not resposta:
                    continue
                campos = {
                    rc.campo.nome: rc.valor
                    for rc in resposta.respostas_campos
                    if rc.campo and rc.campo.nome
                }
                
                # Calcular dias restantes para o prazo
                days_left = None
                if assignment.deadline:
                    from datetime import date
                    today = date.today()
                    deadline_date = assignment.deadline.date() if hasattr(assignment.deadline, 'date') else assignment.deadline
                    days_left = (deadline_date - today).days
                
                # Buscar a submission real pelo trabalho_id
                from models.review import Submission
                submission = Submission.query.get(resposta.trabalho_id)
                
                trabalho = {
                    "titulo": campos.get("Título"),
                    "categoria": campos.get("Categoria"),
                    "pdf_url": campos.get("URL do PDF"),
                    "data_submissao": resposta.data_submissao,
                    "assignment_deadline": assignment.deadline,
                    "assignment_completed": assignment.completed,
                    "distribution_date": assignment.distribution_date,
                    "days_left": days_left,
                    "id": assignment.id,
                    "submission_id": submission.id if submission else None,
                }
                trabalhos_designados.append(trabalho)

    # Determinar o nome do revisor
    nome_revisor = cand.nome
    if cand.status == 'aprovado':
        revisor_user = Usuario.query.filter_by(email=cand.email).first()
        if revisor_user and revisor_user.nome:
            nome_revisor = revisor_user.nome
    
    pdf_url = url_for("revisor_routes.progress_pdf", codigo=codigo)
    return render_template(
        "revisor/progress.html",
        candidatura=cand,
        pdf_url=pdf_url,
        trabalhos_designados=trabalhos_designados,
        nome_revisor=nome_revisor
    )


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
    today = date.today()

    processos = (
        RevisorProcess.query.options(selectinload(RevisorProcess.eventos))
        .filter(
            RevisorProcess.status.in_(["aberto", "pendente", "encerrado"]),
            or_(
                RevisorProcess.availability_start.is_(None),
                func.date(RevisorProcess.availability_start) <= today,
            ),
            or_(
                RevisorProcess.availability_end.is_(None),
                func.date(RevisorProcess.availability_end) >= today,
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

        # Mapear status do banco para exibição no template
        db_status = getattr(proc, "status", None)
        if db_status == "aberto":
            status = "Aberto"
        elif db_status == "pendente":
            status = "Pendente"
        elif db_status == "encerrado":
            status = "Encerrado"
        else:
            status = "Aberto" if proc.is_available() else "Encerrado"
        if not eventos:
            registros.append({"evento": None, "processo": proc, "status": status})
            continue

        validos = [ev for ev in eventos if ev.status == "ativo" and ev.publico]
        if validos:
            for ev in validos:
                registros.append({"evento": ev, "processo": proc, "status": status})
        elif proc.is_available():
            registros.append({"evento": None, "processo": proc, "status": status})

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
            config_cli.limite_total_revisores is not None
            and aprovados >= config_cli.limite_total_revisores
        ):
            flash("Limite de revisores atingido.", "danger")
            return redirect(url_for(endpoints.DASHBOARD_CLIENTE))
    cand.status = "aprovado"
    cand.etapa_atual = cand.process.num_etapas  # type: ignore[attr-defined]

    reviewer: Usuario | None = None
    if cand.email:
        # Cria (ou atualiza) usuário revisor
        reviewer = Usuario.query.filter_by(email=cand.email).first()
        if not reviewer:
            reviewer = Usuario(
                nome=cand.nome or cand.email,
                email=cand.email,
                senha=generate_password_hash("temp123", method="pbkdf2:sha256"),
                formacao="",
                tipo="revisor",
            )
            for _ in range(5):
                novo_cpf = str(uuid.uuid4().int)[:11]
                if not Usuario.query.filter_by(cpf=novo_cpf).first():
                    reviewer.cpf = novo_cpf
                    break
            else:  # pragma: no cover - defensive branch
                current_app.logger.error(
                    "Falha ao gerar CPF único para revisor %s", cand.email
                )
                err_msg = (
                    "Erro ao gerar CPF único. "
                    "Tente novamente ou contate o suporte."
                )
                if request.is_json:
                    return jsonify({"success": False, "error": err_msg}), 500
                flash(err_msg, "danger")
                return redirect(url_for(endpoints.DASHBOARD_CLIENTE))
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
    
    # Atribuição automática de trabalhos disponíveis para o revisor aprovado
    if reviewer:
        from datetime import timedelta
        
        # Busca trabalhos disponíveis do mesmo cliente que ainda precisam de revisores
        from models.event import RespostaFormulario
        
        # Buscar IDs de trabalhos já atribuídos ao revisor
        trabalhos_atribuidos_ids = (
            db.session.query(RespostaFormulario.trabalho_id)
            .join(Assignment, Assignment.resposta_formulario_id == RespostaFormulario.id)
            .filter(Assignment.reviewer_id == reviewer.id)
            .filter(RespostaFormulario.trabalho_id.isnot(None))
        )
        
        trabalhos_disponiveis = (
            Submission.query
            .join(Evento, Submission.evento_id == Evento.id)
            .filter(
                Evento.cliente_id == cand.process.cliente_id,
                ~Submission.id.in_(trabalhos_atribuidos_ids)
            )
            .limit(5)  # Limita a 5 trabalhos iniciais
            .all()
        )
        
        # Cria assignments para os trabalhos disponíveis
        config = ConfiguracaoCliente.query.filter_by(
            cliente_id=cand.process.cliente_id
        ).first()
        prazo_dias = config.prazo_parecer_dias if config else 14
        
        for trabalho in trabalhos_disponiveis:
            # Cria Review
            review = Review(
                submission_id=trabalho.id,
                reviewer_id=reviewer.id,
                access_code=str(uuid.uuid4())[:8],
            )
            db.session.add(review)
            
            # Busca ou cria RespostaFormulario para o trabalho
            resposta_formulario = RespostaFormulario.query.filter_by(trabalho_id=trabalho.id).first()
            if not resposta_formulario:
                # Cria uma resposta de formulário básica se não existir
                resposta_formulario = RespostaFormulario(
                    trabalho_id=trabalho.id,
                    formulario_id=None,  # Pode ser None para assignments automáticos
                    data_submissao=datetime.utcnow()
                )
                db.session.add(resposta_formulario)
                db.session.flush()  # Para obter o ID
            
            # Cria Assignment
            assignment = Assignment(
                resposta_formulario_id=resposta_formulario.id,
                reviewer_id=reviewer.id,
                deadline=datetime.utcnow() + timedelta(days=prazo_dias),
            )
            db.session.add(assignment)

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
    return redirect(url_for(endpoints.DASHBOARD_CLIENTE))


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
    return redirect(url_for(endpoints.DASHBOARD_CLIENTE))


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
    return redirect(url_for(endpoints.DASHBOARD_CLIENTE))


@revisor_routes.route("/revisor/view/<int:cand_id>")
@login_required
def view_candidatura(cand_id: int):
    """Exibe os detalhes e respostas de uma candidatura."""
    if current_user.tipo not in {"cliente", "admin", "superadmin"}:  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))

    cand: RevisorCandidatura = RevisorCandidatura.query.get_or_404(cand_id)
    return render_template("revisor/candidatura_detail.html", candidatura=cand)


# -----------------------------------------------------------------------------
# AVALIAÇÃO DE TRABALHOS
# -----------------------------------------------------------------------------
def _extract_categoria_valor(raw_valor):
    """Normalize raw category values coming from form answers."""

    if raw_valor is None:
        return None

    if isinstance(raw_valor, str):
        valor = raw_valor.strip()
        if not valor:
            return None

        if valor.startswith("[") and valor.endswith("]"):
            try:
                parsed = json.loads(valor)
            except (TypeError, ValueError):
                parsed = None
            if isinstance(parsed, list):
                for item in parsed:
                    item_valor = str(item).strip()
                    if item_valor:
                        return item_valor
                return None

        return valor

    if isinstance(raw_valor, list):
        for item in raw_valor:
            item_valor = str(item).strip()
            if item_valor:
                return item_valor
        return None

    valor = str(raw_valor).strip()
    return valor or None


def get_categoria_trabalho(resposta_formulario):
    """Obtém a categoria do trabalho a partir das respostas dos campos."""
    if not resposta_formulario:
        return None

    for resposta_campo in resposta_formulario.respostas_campos:
        campo_nome = (getattr(resposta_campo.campo, "nome", "") or "").strip().lower()
        if "categoria" not in campo_nome:
            continue

        valor = _extract_categoria_valor(resposta_campo.valor)
        if valor:
            return valor

    return None


def resolve_categoria_trabalho(submission, assignment=None):
    """Resolve a categoria do trabalho reutilizando a resposta do assignment.

    Primeiro tenta extrair a categoria da resposta vinculada ao assignment.
    Caso não encontre, faz uma busca abrangente em todas as respostas do
    trabalho procurando campos cujo nome contenha "categoria".
    """

    resposta_formulario = None
    if assignment is not None:
        resposta_formulario = getattr(assignment, "resposta_formulario", None)
        if (
            resposta_formulario is None
            and getattr(assignment, "resposta_formulario_id", None)
        ):
            resposta_formulario = RespostaFormulario.query.get(
                assignment.resposta_formulario_id
            )

    categoria = None
    if resposta_formulario:
        categoria = get_categoria_trabalho(resposta_formulario)
        if categoria:
            return categoria

    respostas_categoria = (
        RespostaFormulario.query
        .join(
            RespostaCampoFormulario,
        RespostaCampoFormulario.resposta_formulario_id == RespostaFormulario.id,
    )
    .join(CampoFormulario, RespostaCampoFormulario.campo_id == CampoFormulario.id)
        .filter(
            RespostaFormulario.trabalho_id == submission.id,
            RespostaFormulario.evento_id == submission.evento_id,
            CampoFormulario.nome.ilike("%categoria%"),
        )
        .order_by(RespostaFormulario.id)
        .all()
    )

    vistos: set[int] = set()
    for resposta in respostas_categoria:
        if resposta.id in vistos:
            continue
        vistos.add(resposta.id)
        categoria = get_categoria_trabalho(resposta)
        if categoria:
            return categoria

    return None

@revisor_routes.route("/revisor/avaliar/<int:submission_id>", methods=["GET", "POST"])
def avaliar(submission_id: int):
    """Permite ao revisor atribuir notas a uma submissão com base no barema."""
    submission = Submission.query.get_or_404(submission_id)
    
    # Se o usuário não estiver autenticado, permitir acesso apenas para visualização
    if not current_user.is_authenticated:
        # Buscar assignment através da resposta de formulário (sem filtro de reviewer_id)
        assignment = (
            Assignment.query
            .join(RespostaFormulario, Assignment.resposta_formulario_id == RespostaFormulario.id)
            .filter(RespostaFormulario.trabalho_id == submission.id)
            .first()
        )
        if not assignment:
            flash("Nenhum revisor atribuído para este trabalho!", "warning")
            return redirect(url_for("evento_routes.home"))
    else:
        # Buscar assignment através da resposta de formulário
        assignment = (
            Assignment.query
            .join(RespostaFormulario, Assignment.resposta_formulario_id == RespostaFormulario.id)
            .filter(
                RespostaFormulario.trabalho_id == submission.id,
                Assignment.reviewer_id == current_user.id
            )
            .first()
        )
        if not assignment:
            flash("Acesso negado!", "danger")
            return redirect(url_for(endpoints.DASHBOARD))

    categoria_trabalho = resolve_categoria_trabalho(submission, assignment)
    
    # Buscar barema específico da categoria primeiro
    barema_categoria = None
    if categoria_trabalho:
        barema_categoria = CategoriaBarema.query.filter_by(
            evento_id=submission.evento_id,
            categoria=categoria_trabalho
        ).first()
    
    # Fallback para barema geral do evento se não houver barema específico
    barema_geral = EventoBarema.query.filter_by(evento_id=submission.evento_id).first()
    
    if not barema_categoria and not barema_geral:
        flash("Barema não encontrado para este evento.", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    
    # Usar barema específico se disponível, senão usar o geral
=======
"""Rotas relacionadas ao processo seletivo de revisores (avaliadores).

Este blueprint permite que clientes configurem o processo, que candidatos
submetam formulários, acompanhem o andamento e que administradores aprovem
candidaturas. Também expõe endpoints para listar eventos elegíveis a partir
da perspectiva de participantes.
"""

from __future__ import annotations
from utils import endpoints
from utils.barema import normalize_barema_requisitos

import json
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
from sqlalchemy.exc import ProgrammingError

from models import (
    Assignment,
    Cliente,
    ConfiguracaoCliente,
    Evento,
    Formulario,
    EventoBarema,
    ProcessoBarema,
    ProcessoBaremaRequisito,
    RevisorCandidatura,
    RevisorCandidaturaEtapa,
    RevisorEtapa,
    RevisorProcess,
    revisor_process_evento_association,
    Submission,
    Review,
    Usuario,
)
from models.event import CampoFormulario, RespostaCampoFormulario, RespostaFormulario
from models.review import CategoriaBarema
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
# PROCESSOS DO REVISOR
# -----------------------------------------------------------------------------



@revisor_routes.route("/revisor/processos", methods=["GET"])
@login_required
def list_processes() -> Any:
    """List all review processes for the logged client."""

    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))

    processos = RevisorProcess.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).all()
    
    return render_template("revisor/process_list.html", processos=processos)


@revisor_routes.route("/revisor/processos/novo", methods=["GET"])
@login_required
def new_process():
    """Render form to create a new review process."""
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    
    formularios: List[Formulario] = Formulario.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).all()
    eventos: List[Evento] = Evento.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).all()
    
    # Create empty process for form rendering
    processo = RevisorProcess(cliente_id=current_user.id, num_etapas=1)  # type: ignore[attr-defined]
    
    return render_template(
        "revisor/config.html",
        processo=processo,
        formularios=formularios,
        etapas=[],
        criterios=[],
        eventos=eventos,
        selected_event_ids=[],
        is_new=True
    )


@revisor_routes.route("/revisor/processos", methods=["POST"])
@login_required
def create_process() -> Any:
    """Create a new review process for the current client."""
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    try:
        dados = parse_revisor_form(request)
    except ValueError as exc:
        flash(str(exc), "danger")
        return jsonify({"error": str(exc)}), 400

    created_form: Formulario | None = None
    if not dados.get("formulario_id"):
        created_form = Formulario(
            nome="Formulário de Candidatura",
            cliente_id=current_user.id,  # type: ignore[attr-defined]
        )
        db.session.add(created_form)
        db.session.flush()
        rh.ensure_reviewer_required_fields(created_form)
        dados["formulario_id"] = created_form.id

    processo = RevisorProcess(
        cliente_id=current_user.id,  # type: ignore[attr-defined]
        nome=dados["nome"],
    )
    db.session.add(processo)
    update_revisor_process(processo, dados)
    db.session.flush()
    update_process_eventos(processo, dados.get("eventos_ids", []))
    recreate_stages(processo, dados.get("stage_names", []))
    recreate_criterios(processo, dados.get("criterios", []))
    if created_form is None and processo.formulario_id:
        formulario = Formulario.query.get(processo.formulario_id)
        if formulario:
            rh.ensure_reviewer_required_fields(formulario)
    

    
    db.session.commit()
    flash("Processo criado com sucesso!", "success")
    return redirect(url_for("revisor_routes.edit_process", process_id=processo.id))


@revisor_routes.route("/revisor/processos/<int:process_id>", methods=["GET", "POST"])
@login_required
def edit_process(process_id: int):
    """Render or update a specific review process."""
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    
    # Check if process exists
    processo = RevisorProcess.query.filter_by(
        id=process_id, 
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).first()
    
    if not processo:
        flash("Processo não encontrado. Crie um novo processo ou edite um existente.", "warning")
        return redirect(url_for("revisor_routes.list_processes"))
    
    if processo.cliente_id != current_user.id:  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))


    formularios: List[Formulario] = Formulario.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).all()
    eventos: List[Evento] = Evento.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).all()

    selected_event_ids: List[int] = [e.id for e in processo.eventos]


    if request.method == "POST":
        try:
            dados = parse_revisor_form(request)
        except ValueError as exc:
            flash(str(exc), "danger")

            return redirect(
                url_for("revisor_routes.edit_process", process_id=processo.id)

            )
        update_revisor_process(processo, dados)

        update_process_eventos(processo, dados.get("eventos_ids", []))
        recreate_criterios(processo, dados.get("criterios", []))
        if processo.formulario_id:

            formulario = Formulario.query.get(processo.formulario_id)
            if formulario:
                rh.ensure_reviewer_required_fields(formulario)
        

        
        db.session.commit()
        flash("Processo atualizado", "success")

        return redirect(
            url_for("revisor_routes.edit_process", process_id=processo.id)
        )


    try:
        criterios = processo.criterios  # type: ignore[attr-defined]
    except ProgrammingError as exc:  # pragma: no cover - depends on db state
        current_app.logger.error("Erro ao acessar criterios: %s", exc)
        flash(
            "Banco de dados desatualizado. Administradores: executem as migrações.",
            "warning",
        )
        criterios = []
    # Determinar se é um novo processo
    is_new = processo.id is None
    
    return render_template(
        "revisor/config.html",
        processo=processo,
        formularios=formularios,
        criterios=criterios,
        eventos=eventos,
        selected_event_ids=selected_event_ids,
        is_new=is_new,
    )



# Compat: rota antiga que redireciona para o fluxo atual
@revisor_routes.route("/config_revisor", methods=["GET", "POST"])
@login_required
def config_revisor():
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))

    processo = RevisorProcess.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).first()

    if processo is None:
        processo = RevisorProcess(cliente_id=current_user.id)  # type: ignore[attr-defined]
        db.session.add(processo)
        db.session.commit()

    return redirect(url_for("revisor_routes.edit_process", process_id=processo.id))


@revisor_routes.route("/revisor/config", methods=["GET"])
@login_required
def config_overview():
    """Main configuration page for reviewer processes.
    
    Lists all existing reviewer processes for the current client
    and provides options to create new ones or edit existing ones.
    """
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    
    # Get all reviewer processes for the current client
    processos = RevisorProcess.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).all()
    
    # Get all forms for the current client
    formularios = Formulario.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).all()
    
    # Get all events for the current client
    eventos = Evento.query.filter_by(
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).all()
    
    return render_template(
        "revisor/config_overview.html",
        processos=processos,
        formularios=formularios,
        eventos=eventos,
    )


@revisor_routes.route("/revisor/processes/<int:process_id>/delete", methods=["POST"])
@revisor_routes.route("/revisor/<int:process_id>/delete", methods=["POST"])
@login_required
def delete_process(process_id: int):
    """Remove a review process owned by the current client."""
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    processo = RevisorProcess.query.get_or_404(process_id)
    if processo.cliente_id != current_user.id:  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    db.session.delete(processo)
    db.session.commit()
    if request.method == "DELETE":
        return "", 204
    flash("Processo removido", "success")
    return redirect(url_for("revisor_routes.list_processes"))


# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DE BAREMAS
# -----------------------------------------------------------------------------
@revisor_routes.route("/revisor/<int:process_id>/barema")
@login_required
def manage_barema(process_id: int):
    """Display and ensure a barema exists for the given process.

    Args:
        process_id: Identifier of the review process.

    Returns:
        Response rendering the barema management page.
    """
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    processo = RevisorProcess.query.get_or_404(process_id)
    barema = ProcessoBarema.query.filter_by(process_id=process_id).first()
    if barema is None:
        barema = ProcessoBarema(process_id=process_id)
        db.session.add(barema)
        db.session.commit()
    requisitos = barema.requisitos
    return render_template(
        "revisor/barema_form.html",
        processo=processo,
        barema=barema,
        requisitos=requisitos,
    )


@revisor_routes.route(
    "/revisor/barema/<int:barema_id>/requisito/new", methods=["GET", "POST"]
)
@login_required
def add_requisito(barema_id: int):
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    barema = ProcessoBarema.query.get_or_404(barema_id)

    if request.method == "POST":
        requisito = ProcessoBaremaRequisito(
            barema_id=barema_id,
            nome=request.form.get("nome") or "",
            descricao=request.form.get("descricao"),
            pontuacao_min=request.form.get("pontuacao_min", type=float) or 0,
            pontuacao_max=request.form.get("pontuacao_max", type=float) or 0,
        )
        if requisito.pontuacao_min > requisito.pontuacao_max:
            error = "Pontuação mínima não pode ser maior que a máxima."
            flash(error, "danger")
            return render_template(
                "revisor/requisito_form.html",
                barema=barema,
                requisito=requisito,
                error=error,
            )
        db.session.add(requisito)
        db.session.commit()
        flash("Requisito adicionado", "success")
        return redirect(
            url_for("revisor_routes.manage_barema", process_id=barema.process_id)
        )
    return render_template(
        "revisor/requisito_form.html", barema=barema, requisito=None
    )


@revisor_routes.route(
    "/revisor/requisito/<int:req_id>/edit", methods=["GET", "POST"]
)
@login_required
def edit_requisito(req_id: int):
    requisito = ProcessoBaremaRequisito.query.get_or_404(req_id)
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")


        return redirect(url_for(endpoints.DASHBOARD))
    if request.method == "POST":
        requisito.nome = request.form.get("nome") or requisito.nome
        requisito.descricao = request.form.get("descricao")
        requisito.pontuacao_min = (
            request.form.get("pontuacao_min", type=float) or 0
        )
        requisito.pontuacao_max = (
            request.form.get("pontuacao_max", type=float) or 0
        )
        if requisito.pontuacao_min > requisito.pontuacao_max:
            error = "Pontuação mínima não pode ser maior que a máxima."
            flash(error, "danger")
            return render_template(
                "revisor/requisito_form.html",
                barema=requisito.barema,
                requisito=requisito,
                error=error,
            )
        db.session.commit()
        flash("Requisito atualizado", "success")
        return redirect(
            url_for(
                "revisor_routes.manage_barema",
                process_id=requisito.barema.process_id,
            )
        )
    return render_template(
        "revisor/requisito_form.html",
        barema=requisito.barema,
        requisito=requisito,
    )


@revisor_routes.route(
    "/revisor/requisito/<int:req_id>/delete", methods=["POST"]

)
@login_required
def delete_requisito(req_id: int):
    requisito = ProcessoBaremaRequisito.query.get_or_404(req_id)
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")

        return redirect(url_for(endpoints.DASHBOARD))
    process_id = requisito.barema.process_id
    db.session.delete(requisito)
    db.session.commit()
    flash("Requisito removido", "success")
    return redirect(url_for("revisor_routes.manage_barema", process_id=process_id))


@revisor_routes.route(
    "/revisor/<int:process_id>/barema/delete", methods=["POST"]

)
@login_required
def delete_barema(process_id: int):
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    barema = ProcessoBarema.query.filter_by(process_id=process_id).first_or_404()

    db.session.delete(barema)
    db.session.commit()
    flash("Barema removido", "success")
    return redirect(url_for("revisor_routes.manage_barema", process_id=process_id))


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
            elif campo.tipo == "checkbox":
                valores = request.form.getlist(key)
                if is_required and not valores:
                    flash(f"O campo {campo.nome} é obrigatório.", "danger")
                    return redirect(request.url)
                valor = valores
            elif campo.tipo == "radio":
                raw_val = request.form.get(key)
                if is_required and not raw_val:
                    flash(f"O campo {campo.nome} é obrigatório.", "danger")
                    return redirect(request.url)
                if raw_val and campo.opcoes:
                    opcoes_validas = [o.strip() for o in campo.opcoes.split(",")]
                    if raw_val not in opcoes_validas:
                        flash("Opção inválida.", "danger")
                        return redirect(request.url)
                valor = raw_val
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

        # Validação obrigatória para nome e email
        if not nome:
            flash("O campo Nome é obrigatório.", "danger")
            return redirect(request.url)
        
        if not email:
            flash("O campo E-mail é obrigatório.", "danger")
            return redirect(request.url)

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

    # Ordenar todos os campos pela ordem
    campos_ordenados = sorted(formulario.campos, key=lambda c: getattr(c, 'ordem', 0) or 0)
    
    return render_template(
        "revisor/candidatura_form.html", 
        formulario=formulario, 
        processo=processo,
        campos=campos_ordenados
    )


@revisor_routes.route("/revisor/progress/<codigo>")
def progress(codigo: str):
    cand: RevisorCandidatura = RevisorCandidatura.query.filter_by(
        codigo=codigo
    ).first_or_404()

    trabalhos_designados = []
    if cand.status == 'aprovado':
        revisor_user = Usuario.query.filter_by(email=cand.email).first()
        if revisor_user:
            # Determinar o evento associado à candidatura
            processo = cand.process
            evento_id = None
            
            if processo.evento_id:
                evento_id = processo.evento_id
            elif processo.eventos:
                evento_id = processo.eventos[0].id  # Usar o primeiro evento associado
            
            # Buscar assignments do revisor filtrados por evento (se disponível)
            query = (
                Assignment.query
                .options(
                    db.joinedload(Assignment.resposta_formulario),
                    db.joinedload(Assignment.reviewer)
                )
                .filter_by(reviewer_id=revisor_user.id)
            )
            
            # Filtrar por evento se disponível e se há respostas com evento_id válido
            if evento_id:
                from models.event import RespostaFormulario
                
                # Verificar se existem respostas com este evento_id
                respostas_com_evento = (
                    RespostaFormulario.query
                    .join(Assignment, Assignment.resposta_formulario_id == RespostaFormulario.id)
                    .filter(
                        Assignment.reviewer_id == revisor_user.id,
                        RespostaFormulario.evento_id == evento_id
                    ).count()
                )
                
                # Só filtrar por evento se existirem respostas com evento_id válido
                if respostas_com_evento > 0:
                    query = (
                        query.join(
                            RespostaFormulario,
                            Assignment.resposta_formulario_id == RespostaFormulario.id,
                        ).filter(RespostaFormulario.evento_id == evento_id)
                    )

            assignments = query.all()

            for assignment in assignments:
                resposta = assignment.resposta_formulario
                if not resposta:
                    continue
                campos = {
                    rc.campo.nome: rc.valor
                    for rc in resposta.respostas_campos
                    if rc.campo and rc.campo.nome
                }
                
                # Calcular dias restantes para o prazo
                days_left = None
                if assignment.deadline:
                    from datetime import date
                    today = date.today()
                    deadline_date = assignment.deadline.date() if hasattr(assignment.deadline, 'date') else assignment.deadline
                    days_left = (deadline_date - today).days
                
                # Buscar a submission real pelo trabalho_id
                from models.review import Submission
                submission = Submission.query.get(resposta.trabalho_id)
                
                trabalho = {
                    "titulo": campos.get("Título"),
                    "categoria": campos.get("Categoria"),
                    "pdf_url": campos.get("URL do PDF"),
                    "data_submissao": resposta.data_submissao,
                    "assignment_deadline": assignment.deadline,
                    "assignment_completed": assignment.completed,
                    "distribution_date": assignment.distribution_date,
                    "days_left": days_left,
                    "id": assignment.id,
                    "submission_id": submission.id if submission else None,
                }
                trabalhos_designados.append(trabalho)

    # Determinar o nome do revisor
    nome_revisor = cand.nome
    if cand.status == 'aprovado':
        revisor_user = Usuario.query.filter_by(email=cand.email).first()
        if revisor_user and revisor_user.nome:
            nome_revisor = revisor_user.nome
    
    pdf_url = url_for("revisor_routes.progress_pdf", codigo=codigo)
    return render_template(
        "revisor/progress.html",
        candidatura=cand,
        pdf_url=pdf_url,
        trabalhos_designados=trabalhos_designados,
        nome_revisor=nome_revisor
    )


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
    today = date.today()

    processos = (
        RevisorProcess.query.options(selectinload(RevisorProcess.eventos))
        .filter(
            RevisorProcess.status.in_(["aberto", "pendente", "encerrado"]),
            or_(
                RevisorProcess.availability_start.is_(None),
                func.date(RevisorProcess.availability_start) <= today,
            ),
            or_(
                RevisorProcess.availability_end.is_(None),
                func.date(RevisorProcess.availability_end) >= today,
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

        # Mapear status do banco para exibição no template
        db_status = getattr(proc, "status", None)
        if db_status == "aberto":
            status = "Aberto"
        elif db_status == "pendente":
            status = "Pendente"
        elif db_status == "encerrado":
            status = "Encerrado"
        else:
            status = "Aberto" if proc.is_available() else "Encerrado"
        if not eventos:
            registros.append({"evento": None, "processo": proc, "status": status})
            continue

        validos = [ev for ev in eventos if ev.status == "ativo" and ev.publico]
        if validos:
            for ev in validos:
                registros.append({"evento": ev, "processo": proc, "status": status})
        elif proc.is_available():
            registros.append({"evento": None, "processo": proc, "status": status})

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
            config_cli.limite_total_revisores is not None
            and aprovados >= config_cli.limite_total_revisores
        ):
            flash("Limite de revisores atingido.", "danger")
            return redirect(url_for(endpoints.DASHBOARD_CLIENTE))
    cand.status = "aprovado"
    cand.etapa_atual = cand.process.num_etapas  # type: ignore[attr-defined]

    reviewer: Usuario | None = None
    if cand.email:
        # Cria (ou atualiza) usuário revisor
        reviewer = Usuario.query.filter_by(email=cand.email).first()
        if not reviewer:
            reviewer = Usuario(
                nome=cand.nome or cand.email,
                email=cand.email,
                senha=generate_password_hash("temp123", method="pbkdf2:sha256"),
                formacao="",
                tipo="revisor",
            )
            for _ in range(5):
                novo_cpf = str(uuid.uuid4().int)[:11]
                if not Usuario.query.filter_by(cpf=novo_cpf).first():
                    reviewer.cpf = novo_cpf
                    break
            else:  # pragma: no cover - defensive branch
                current_app.logger.error(
                    "Falha ao gerar CPF único para revisor %s", cand.email
                )
                err_msg = (
                    "Erro ao gerar CPF único. "
                    "Tente novamente ou contate o suporte."
                )
                if request.is_json:
                    return jsonify({"success": False, "error": err_msg}), 500
                flash(err_msg, "danger")
                return redirect(url_for(endpoints.DASHBOARD_CLIENTE))
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
    
    # Atribuição automática de trabalhos disponíveis para o revisor aprovado
    if reviewer:
        from datetime import timedelta
        
        # Busca trabalhos disponíveis do mesmo cliente que ainda precisam de revisores
        from models.event import RespostaFormulario
        
        # Buscar IDs de trabalhos já atribuídos ao revisor
        trabalhos_atribuidos_ids = (
            db.session.query(RespostaFormulario.trabalho_id)
            .join(Assignment, Assignment.resposta_formulario_id == RespostaFormulario.id)
            .filter(Assignment.reviewer_id == reviewer.id)
            .filter(RespostaFormulario.trabalho_id.isnot(None))
        )
        
        trabalhos_disponiveis = (
            Submission.query
            .join(Evento, Submission.evento_id == Evento.id)
            .filter(
                Evento.cliente_id == cand.process.cliente_id,
                ~Submission.id.in_(trabalhos_atribuidos_ids)
            )
            .limit(5)  # Limita a 5 trabalhos iniciais
            .all()
        )
        
        # Cria assignments para os trabalhos disponíveis
        config = ConfiguracaoCliente.query.filter_by(
            cliente_id=cand.process.cliente_id
        ).first()
        prazo_dias = config.prazo_parecer_dias if config else 14
        
        for trabalho in trabalhos_disponiveis:
            # Cria Review
            review = Review(
                submission_id=trabalho.id,
                reviewer_id=reviewer.id,
                access_code=str(uuid.uuid4())[:8],
            )
            db.session.add(review)
            
            # Busca ou cria RespostaFormulario para o trabalho
            resposta_formulario = RespostaFormulario.query.filter_by(trabalho_id=trabalho.id).first()
            if not resposta_formulario:
                # Cria uma resposta de formulário básica se não existir
                resposta_formulario = RespostaFormulario(
                    trabalho_id=trabalho.id,
                    formulario_id=None,  # Pode ser None para assignments automáticos
                    data_submissao=datetime.utcnow()
                )
                db.session.add(resposta_formulario)
                db.session.flush()  # Para obter o ID
            
            # Cria Assignment
            assignment = Assignment(
                resposta_formulario_id=resposta_formulario.id,
                reviewer_id=reviewer.id,
                deadline=datetime.utcnow() + timedelta(days=prazo_dias),
            )
            db.session.add(assignment)

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
    return redirect(url_for(endpoints.DASHBOARD_CLIENTE))


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
    return redirect(url_for(endpoints.DASHBOARD_CLIENTE))


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
    return redirect(url_for(endpoints.DASHBOARD_CLIENTE))


@revisor_routes.route("/revisor/view/<int:cand_id>")
@login_required
def view_candidatura(cand_id: int):
    """Exibe os detalhes e respostas de uma candidatura."""
    if current_user.tipo not in {"cliente", "admin", "superadmin"}:  # type: ignore[attr-defined]
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))

    cand: RevisorCandidatura = RevisorCandidatura.query.get_or_404(cand_id)
    return render_template("revisor/candidatura_detail.html", candidatura=cand)


# -----------------------------------------------------------------------------
# AVALIAÇÃO DE TRABALHOS
# -----------------------------------------------------------------------------
def _extract_categoria_valor(raw_valor):
    """Normalize raw category values coming from form answers."""

    if raw_valor is None:
        return None

    if isinstance(raw_valor, str):
        valor = raw_valor.strip()
        if not valor:
            return None

        if valor.startswith("[") and valor.endswith("]"):
            try:
                parsed = json.loads(valor)
            except (TypeError, ValueError):
                parsed = None
            if isinstance(parsed, list):
                for item in parsed:
                    item_valor = str(item).strip()
                    if item_valor:
                        return item_valor
                return None

        return valor

    if isinstance(raw_valor, list):
        for item in raw_valor:
            item_valor = str(item).strip()
            if item_valor:
                return item_valor
        return None

    valor = str(raw_valor).strip()
    return valor or None


def get_categoria_trabalho(resposta_formulario):
    """Obtém a categoria do trabalho a partir das respostas dos campos."""
    if not resposta_formulario:
        return None

    for resposta_campo in resposta_formulario.respostas_campos:
        campo_nome = (getattr(resposta_campo.campo, "nome", "") or "").strip().lower()
        if "categoria" not in campo_nome:
            continue

        valor = _extract_categoria_valor(resposta_campo.valor)
        if valor:
            return valor

    return None


def resolve_categoria_trabalho(submission, assignment=None):
    """Resolve a categoria do trabalho reutilizando a resposta do assignment.

    Primeiro tenta extrair a categoria da resposta vinculada ao assignment.
    Caso não encontre, faz uma busca abrangente em todas as respostas do
    trabalho procurando campos cujo nome contenha "categoria".
    """

    resposta_formulario = None
    if assignment is not None:
        resposta_formulario = getattr(assignment, "resposta_formulario", None)
        if (
            resposta_formulario is None
            and getattr(assignment, "resposta_formulario_id", None)
        ):
            resposta_formulario = RespostaFormulario.query.get(
                assignment.resposta_formulario_id
            )

    categoria = None
    if resposta_formulario:
        categoria = get_categoria_trabalho(resposta_formulario)
        if categoria:
            return categoria

    respostas_categoria = (
        RespostaFormulario.query
        .join(
            RespostaCampoFormulario,
        RespostaCampoFormulario.resposta_formulario_id == RespostaFormulario.id,
    )
    .join(CampoFormulario, RespostaCampoFormulario.campo_id == CampoFormulario.id)
        .filter(
            RespostaFormulario.trabalho_id == submission.id,
            RespostaFormulario.evento_id == submission.evento_id,
            CampoFormulario.nome.ilike("%categoria%"),
        )
        .order_by(RespostaFormulario.id)
        .all()
    )

    vistos: set[int] = set()
    for resposta in respostas_categoria:
        if resposta.id in vistos:
            continue
        vistos.add(resposta.id)
        categoria = get_categoria_trabalho(resposta)
        if categoria:
            return categoria

    return None

@revisor_routes.route("/revisor/avaliar/<int:submission_id>", methods=["GET", "POST"])
def avaliar(submission_id: int):
    """Permite ao revisor atribuir notas a uma submissão com base no barema."""
    submission = Submission.query.get_or_404(submission_id)
    
    # Se o usuário não estiver autenticado, permitir acesso apenas para visualização
    if not current_user.is_authenticated:
        # Buscar assignment através da resposta de formulário (sem filtro de reviewer_id)
        assignment = (
            Assignment.query
            .join(RespostaFormulario, Assignment.resposta_formulario_id == RespostaFormulario.id)
            .filter(RespostaFormulario.trabalho_id == submission.id)
            .first()
        )
        if not assignment:
            flash("Nenhum revisor atribuído para este trabalho!", "warning")
            return redirect(url_for("evento_routes.home"))
    else:
        # Buscar assignment através da resposta de formulário
        assignment = (
            Assignment.query
            .join(RespostaFormulario, Assignment.resposta_formulario_id == RespostaFormulario.id)
            .filter(
                RespostaFormulario.trabalho_id == submission.id,
                Assignment.reviewer_id == current_user.id
            )
            .first()
        )
        if not assignment:
            flash("Acesso negado!", "danger")
            return redirect(url_for(endpoints.DASHBOARD))

    categoria_trabalho = resolve_categoria_trabalho(submission, assignment)
    
    # Buscar barema específico da categoria primeiro
    barema_categoria = None
    if categoria_trabalho:
        barema_categoria = CategoriaBarema.query.filter_by(
            evento_id=submission.evento_id,
            categoria=categoria_trabalho
        ).first()
    
    # Fallback para barema geral do evento se não houver barema específico
    barema_geral = EventoBarema.query.filter_by(evento_id=submission.evento_id).first()
    
    if not barema_categoria and not barema_geral:
        flash("Barema não encontrado para este evento.", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    
    # Usar barema específico se disponível, senão usar o geral
>>>>>>> c593328b09b311b97c969034b12baa1c351a90bd
    barema = barema_categoria if barema_categoria else barema_geral
    requisitos = normalize_barema_requisitos(barema)
    usando_barema_categoria = bool(barema_categoria and barema is barema_categoria)
    barema_label = getattr(barema, "nome", None)
    if not barema_label:
        barema_label = "Barema da categoria" if usando_barema_categoria else "Barema geral do evento"
    barema_descricao = getattr(barema, "descricao", None)
    
    # Buscar review apenas se o usuário estiver autenticado
    review = None
    if current_user.is_authenticated:
        review = Review.query.filter_by(
            submission_id=submission.id, reviewer_id=current_user.id
        ).first()


    if request.method == "POST" and barema:
        # Apenas usuários autenticados podem submeter avaliações
        if not current_user.is_authenticated:
            flash("Você precisa estar logado para submeter uma avaliação!", "warning")
            return redirect(url_for("auth_routes.login"))

        scores: Dict[str, float] = {}

        for requisito, faixa in requisitos.items():
            nota_raw = request.form.get(requisito)
            if nota_raw:
                try:
                    nota = float(nota_raw)
                except ValueError:
                    flash(f"Nota inválida informada para {requisito}.", "danger")
                    return render_template(
                        "revisor/avaliacao.html",
                        submission=submission,
                        barema=barema,
                        requisitos=requisitos,
                        review=review,
                        categoria_trabalho=categoria_trabalho,
                        usando_barema_categoria=usando_barema_categoria,
                        barema_label=barema_label,
                        barema_descricao=barema_descricao,
                    )
                min_val = faixa.get("min", 0)
                max_val = faixa.get("max")
                if max_val is not None and (nota < min_val or nota > max_val):
                    flash(
                        f"Nota para {requisito} deve estar entre {min_val} e {max_val}",
                        "danger",
                    )
                    return render_template(
                        "revisor/avaliacao.html",
                        submission=submission,
                        barema=barema,
                        requisitos=requisitos,
                        review=review,
                        categoria_trabalho=categoria_trabalho,
                        usando_barema_categoria=usando_barema_categoria,
                        barema_label=barema_label,
                        barema_descricao=barema_descricao,
                    )
                scores[requisito] = nota


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
        "revisor/avaliacao.html",
        submission=submission,
        barema=barema,
        review=review,
        requisitos=requisitos,
        categoria_trabalho=categoria_trabalho,
        usando_barema_categoria=usando_barema_categoria,
        barema_label=barema_label,
        barema_descricao=barema_descricao,
    )
<<<<<<< HEAD


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
            RevisorProcess.status == "ativo",
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
        return redirect(url_for(endpoints.DASHBOARD))

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


@revisor_routes.route(
    "/revisor/api/formulario/<int:formulario_id>/campos", methods=["GET"]
)
def get_public_formulario_campos(formulario_id: int) -> Any:
    """Return public fields for a form used in reviewer applications.

    This endpoint does not require authentication but ensures the form
    belongs to an available reviewer process that is visible to
    participants. Only non-protected fields are returned.
    """

    processo = RevisorProcess.query.filter_by(formulario_id=formulario_id).first()
    if (
        not processo
        or processo.status != "aberto"
        or not processo.exibir_para_participantes
        or not processo.is_available()
    ):
        return jsonify({"error": "Formulário não disponível"}), 404

    formulario = processo.formulario
    if not formulario:
        return jsonify({"error": "Formulário não encontrado"}), 404

    from models.event import CampoFormulario

    campos_qs = (
        CampoFormulario.query.filter_by(
            formulario_id=formulario.id, protegido=False
        )
        .order_by(CampoFormulario.id.asc())
        .all()
    )

    def _safe_int(value, default=1):
        try:
            return int(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    campos = [
        {
            "id": campo.id,
            "nome": campo.nome,
            "tipo": campo.tipo,
            "obrigatorio": bool(getattr(campo, "obrigatorio", False)),
            "etapa": _safe_int(getattr(campo, "etapa", 1), 1),
        }
        for campo in campos_qs
    ]

    return jsonify(campos)


@revisor_routes.route("/api/formulario/<int:formulario_id>/campos", methods=["GET"])
@login_required
def get_formulario_campos(formulario_id: int) -> Any:
    """API endpoint para buscar campos de um formulário específico."""
    
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        return jsonify({"success": False, "error": "Acesso negado"}), 403
    
    formulario = Formulario.query.filter_by(
        id=formulario_id,
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).first()
    
    if not formulario:
        return jsonify({"success": False, "error": "Formulário não encontrado"}), 404
    
    campos = [{
        "id": campo.id,
        "nome": campo.nome,
        "tipo": campo.tipo,
        "obrigatorio": campo.obrigatorio,
        "etapa": campo.etapa or 1
    } for campo in formulario.campos]
    
    return jsonify({"success": True, "campos": campos})


@revisor_routes.route("/revisor/iniciar_revisao/<int:trabalho_id>", methods=["GET"])
def iniciar_revisao(trabalho_id: int):
    """Inicia a revisão de um trabalho redirecionando para o barema apropriado."""
    import logging
    from models.event import RespostaFormulario
    from models.review import RevisorCandidatura
    
    logging.info(f"[DEBUG] Rota iniciar_revisao chamada para trabalho_id: {trabalho_id}")
    logging.info(f"[DEBUG] Usuário atual: {'Autenticado' if current_user.is_authenticated else 'Não autenticado'}")
    
    # Buscar o trabalho
    submission = Submission.query.get_or_404(trabalho_id)
    logging.info(f"[DEBUG] Trabalho encontrado: {submission.id}")
    
    # Verificar se existe um assignment para este trabalho
    assignment = (
        Assignment.query
        .join(RespostaFormulario, Assignment.resposta_formulario_id == RespostaFormulario.id)
        .filter(RespostaFormulario.trabalho_id == submission.id)
        .first()
    )
    
    if not assignment:
        flash("Nenhum revisor atribuído para este trabalho!", "warning")
        return redirect(url_for("evento_routes.home"))
    
    categoria = resolve_categoria_trabalho(submission, assignment)
    
    # Buscar barema específico da categoria primeiro
    barema_categoria = None
    if categoria:
        barema_categoria = CategoriaBarema.query.filter_by(
            evento_id=submission.evento_id,
            categoria=categoria
        ).first()
    
    # Fallback para barema geral do evento se não houver barema específico
    barema_geral = EventoBarema.query.filter_by(evento_id=submission.evento_id).first()
    
    if not barema_categoria and not barema_geral:
        flash("Barema não encontrado para este evento.", "danger")
        return redirect(url_for("evento_routes.home"))
    
    # Redirecionar para a avaliação
    return redirect(url_for("revisor_routes.avaliar", submission_id=submission.id))


@revisor_routes.route("/revisor/selecionar_categoria_barema/<int:trabalho_id>", methods=["GET"])
def selecionar_categoria_barema(trabalho_id):
    """Permite ao revisor selecionar a categoria do barema para avaliação."""
    import logging
    logging.info(f"[DEBUG] Rota selecionar_categoria_barema chamada para trabalho_id: {trabalho_id}")
    
    from models.review import Submission
    from models.event import RespostaFormulario
    
    # Verificar se o usuário é um revisor (comentado para permitir acesso via código)
    # if current_user.tipo not in ("revisor", "admin", "superadmin"):
    #     flash("Acesso negado!", "danger")
    #     return redirect(url_for("evento_routes.home"))
    
    # Buscar o trabalho
    logging.info(f"[DEBUG] Buscando trabalho com ID: {trabalho_id}")
    try:
        trabalho = Submission.query.get_or_404(trabalho_id)
        logging.info(f"[DEBUG] Trabalho encontrado: {trabalho.title if trabalho else 'None'}")
        
        # Buscar o assignment para obter o código da candidatura
        assignment = (
            Assignment.query
            .join(RespostaFormulario, Assignment.resposta_formulario_id == RespostaFormulario.id)
            .filter(RespostaFormulario.trabalho_id == trabalho_id)
            .first()
        )
        
        codigo_candidatura = None
        if assignment and assignment.reviewer:
            # Buscar a candidatura do revisor
            candidatura = RevisorCandidatura.query.filter_by(
                email=assignment.reviewer.email
            ).first()
            if candidatura:
                codigo_candidatura = candidatura.codigo
        
        # Categorias disponíveis
        categorias = [
            "Prática Educacional",
            "Pesquisa Inovadora", 
            "Produto Inovador"
        ]
        
        logging.info(f"[DEBUG] Renderizando template com {len(categorias)} categorias")
        return render_template(
            "revisor/selecionar_categoria_barema.html",
            trabalho=trabalho,
            categorias=categorias,
            codigo_candidatura=codigo_candidatura
        )
    except Exception as e:
        logging.error(f"[DEBUG] Erro na rota selecionar_categoria_barema: {str(e)}")
        logging.error(f"[DEBUG] Tipo do erro: {type(e).__name__}")
        import traceback
        logging.error(f"[DEBUG] Traceback: {traceback.format_exc()}")
        raise


@revisor_routes.route("/revisor/avaliar_barema/<int:trabalho_id>/<categoria>", methods=["GET", "POST"])
def avaliar_barema(trabalho_id, categoria):
    """Interface de avaliação baseada nos critérios do barema da categoria selecionada."""
    from models.review import Submission, CategoriaBarema, EventoBarema
    from models.avaliacao import AvaliacaoBarema, AvaliacaoCriterio
    
    # Verificar se o usuário é um revisor (comentado para permitir acesso via código)
    # if current_user.tipo not in ("revisor", "admin", "superadmin"):
    #     flash("Acesso negado!", "danger")
    #     return redirect(url_for("evento_routes.home"))
    
    # Buscar o trabalho
    trabalho = Submission.query.get_or_404(trabalho_id)
    
    # Buscar o barema da categoria
    barema = CategoriaBarema.query.filter_by(
        evento_id=trabalho.evento_id,
        categoria=categoria
    ).first()
    
    # Se não houver barema específico, buscar barema geral
    if not barema:
        barema_geral = EventoBarema.query.filter_by(evento_id=trabalho.evento_id).first()
        if barema_geral:
            # Criar um objeto mock para compatibilidade
            class BaremaMock:
                def __init__(self, evento_barema):
                    self.id = evento_barema.id
                    self.nome = f"Barema Geral - {categoria}"
                    self.criterios = evento_barema.requisitos or {}
            barema = BaremaMock(barema_geral)
    
    if not barema:
        flash(f"Barema não encontrado para a categoria '{categoria}'.", "danger")
        return redirect(url_for("revisor_routes.selecionar_categoria_barema", trabalho_id=trabalho_id))
    
    # Processar critérios do barema (JSON)
    criterios_dict = barema.criterios if hasattr(barema, 'criterios') else {}
    criterios = []
    for nome, detalhes in criterios_dict.items():
        criterio = {
            'id': nome,
            'nome': detalhes.get('nome', nome) if isinstance(detalhes, dict) else nome,
            'descricao': detalhes.get('descricao', '') if isinstance(detalhes, dict) else '',
            'nota_maxima': detalhes.get('pontuacao_max', detalhes.get('max', 10)) if isinstance(detalhes, dict) else 10,
            'peso': detalhes.get('peso', 1) if isinstance(detalhes, dict) else 1
        }
        criterios.append(criterio)
    
    if request.method == "POST":
        # Processar avaliação
        # Criar ou atualizar avaliação
        # Usar ID genérico para revisor quando não logado
        revisor_id = current_user.id if current_user.is_authenticated else 1
        
        avaliacao = AvaliacaoBarema.query.filter_by(
            trabalho_id=trabalho_id,
            revisor_id=revisor_id,
            barema_id=barema.id
        ).first()
        
        if not avaliacao:
            avaliacao = AvaliacaoBarema(
                trabalho_id=trabalho_id,
                revisor_id=revisor_id,
                barema_id=barema.id,
                categoria=categoria
            )
            db.session.add(avaliacao)
            db.session.flush()  # Para obter o ID
        
        # Salvar avaliações dos critérios
        for criterio in criterios:
            nota = request.form.get(f"criterio_{criterio['id']}")
            observacao = request.form.get(f"observacao_{criterio['id']}", "")
            
            if nota:
                # Verificar se já existe avaliação para este critério
                avaliacao_criterio = AvaliacaoCriterio.query.filter_by(
                    avaliacao_id=avaliacao.id,
                    criterio_id=criterio['id']
                ).first()
                
                if avaliacao_criterio:
                    avaliacao_criterio.nota = float(nota)
                    avaliacao_criterio.observacao = observacao
                else:
                    avaliacao_criterio = AvaliacaoCriterio(
                        avaliacao_id=avaliacao.id,
                        criterio_id=criterio['id'],
                        nota=float(nota),
                        observacao=observacao
                    )
                    db.session.add(avaliacao_criterio)
        
        # Calcular nota final
        nota_final = sum(float(request.form.get(f"criterio_{c['id']}", 0)) for c in criterios)
        avaliacao.nota_final = nota_final
        avaliacao.data_avaliacao = datetime.now()
        
        db.session.commit()
        
        flash("Avaliação salva com sucesso!", "success")
        return redirect(url_for("revisor_routes.progress"))
    
    return render_template(
        "revisor/avaliar_barema.html",
        trabalho=trabalho,
        barema=barema,
        criterios=criterios,
        categoria=categoria
    )
=======


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
            RevisorProcess.status == "ativo",
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
        return redirect(url_for(endpoints.DASHBOARD))

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


@revisor_routes.route(
    "/revisor/api/formulario/<int:formulario_id>/campos", methods=["GET"]
)
def get_public_formulario_campos(formulario_id: int) -> Any:
    """Return public fields for a form used in reviewer applications.

    This endpoint does not require authentication but ensures the form
    belongs to an available reviewer process that is visible to
    participants. Only non-protected fields are returned.
    """

    processo = RevisorProcess.query.filter_by(formulario_id=formulario_id).first()
    if (
        not processo
        or processo.status != "aberto"
        or not processo.exibir_para_participantes
        or not processo.is_available()
    ):
        return jsonify({"error": "Formulário não disponível"}), 404

    formulario = processo.formulario
    if not formulario:
        return jsonify({"error": "Formulário não encontrado"}), 404

    from models.event import CampoFormulario

    campos_qs = (
        CampoFormulario.query.filter_by(
            formulario_id=formulario.id, protegido=False
        )
        .order_by(CampoFormulario.id.asc())
        .all()
    )

    def _safe_int(value, default=1):
        try:
            return int(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    campos = [
        {
            "id": campo.id,
            "nome": campo.nome,
            "tipo": campo.tipo,
            "obrigatorio": bool(getattr(campo, "obrigatorio", False)),
            "etapa": _safe_int(getattr(campo, "etapa", 1), 1),
        }
        for campo in campos_qs
    ]

    return jsonify(campos)


@revisor_routes.route("/api/formulario/<int:formulario_id>/campos", methods=["GET"])
@login_required
def get_formulario_campos(formulario_id: int) -> Any:
    """API endpoint para buscar campos de um formulário específico."""
    
    if current_user.tipo != "cliente":  # type: ignore[attr-defined]
        return jsonify({"success": False, "error": "Acesso negado"}), 403
    
    formulario = Formulario.query.filter_by(
        id=formulario_id,
        cliente_id=current_user.id  # type: ignore[attr-defined]
    ).first()
    
    if not formulario:
        return jsonify({"success": False, "error": "Formulário não encontrado"}), 404
    
    campos = [{
        "id": campo.id,
        "nome": campo.nome,
        "tipo": campo.tipo,
        "obrigatorio": campo.obrigatorio,
        "etapa": campo.etapa or 1
    } for campo in formulario.campos]
    
    return jsonify({"success": True, "campos": campos})


@revisor_routes.route("/revisor/iniciar_revisao/<int:trabalho_id>", methods=["GET"])
def iniciar_revisao(trabalho_id: int):
    """Inicia a revisão de um trabalho redirecionando para o barema apropriado."""
    import logging
    from models.event import RespostaFormulario
    from models.review import RevisorCandidatura
    
    logging.info(f"[DEBUG] Rota iniciar_revisao chamada para trabalho_id: {trabalho_id}")
    logging.info(f"[DEBUG] Usuário atual: {'Autenticado' if current_user.is_authenticated else 'Não autenticado'}")
    
    # Buscar o trabalho
    submission = Submission.query.get_or_404(trabalho_id)
    logging.info(f"[DEBUG] Trabalho encontrado: {submission.id}")
    
    # Verificar se existe um assignment para este trabalho
    assignment = (
        Assignment.query
        .join(RespostaFormulario, Assignment.resposta_formulario_id == RespostaFormulario.id)
        .filter(RespostaFormulario.trabalho_id == submission.id)
        .first()
    )
    
    if not assignment:
        flash("Nenhum revisor atribuído para este trabalho!", "warning")
        return redirect(url_for("evento_routes.home"))
    
    categoria = resolve_categoria_trabalho(submission, assignment)
    
    # Buscar barema específico da categoria primeiro
    barema_categoria = None
    if categoria:
        barema_categoria = CategoriaBarema.query.filter_by(
            evento_id=submission.evento_id,
            categoria=categoria
        ).first()
    
    # Fallback para barema geral do evento se não houver barema específico
    barema_geral = EventoBarema.query.filter_by(evento_id=submission.evento_id).first()
    
    if not barema_categoria and not barema_geral:
        flash("Barema não encontrado para este evento.", "danger")
        return redirect(url_for("evento_routes.home"))
    
    # Redirecionar para a avaliação
    return redirect(url_for("revisor_routes.avaliar", submission_id=submission.id))


@revisor_routes.route("/revisor/selecionar_categoria_barema/<int:trabalho_id>", methods=["GET"])
def selecionar_categoria_barema(trabalho_id):
    """Permite ao revisor selecionar a categoria do barema para avaliação."""
    import logging
    logging.info(f"[DEBUG] Rota selecionar_categoria_barema chamada para trabalho_id: {trabalho_id}")
    
    from models.review import Submission
    from models.event import RespostaFormulario
    
    # Verificar se o usuário é um revisor (comentado para permitir acesso via código)
    # if current_user.tipo not in ("revisor", "admin", "superadmin"):
    #     flash("Acesso negado!", "danger")
    #     return redirect(url_for("evento_routes.home"))
    
    # Buscar o trabalho
    logging.info(f"[DEBUG] Buscando trabalho com ID: {trabalho_id}")
    try:
        trabalho = Submission.query.get_or_404(trabalho_id)
        logging.info(f"[DEBUG] Trabalho encontrado: {trabalho.title if trabalho else 'None'}")
        
        # Buscar o assignment para obter o código da candidatura
        assignment = (
            Assignment.query
            .join(RespostaFormulario, Assignment.resposta_formulario_id == RespostaFormulario.id)
            .filter(RespostaFormulario.trabalho_id == trabalho_id)
            .first()
        )
        
        codigo_candidatura = None
        if assignment and assignment.reviewer:
            # Buscar a candidatura do revisor
            candidatura = RevisorCandidatura.query.filter_by(
                email=assignment.reviewer.email
            ).first()
            if candidatura:
                codigo_candidatura = candidatura.codigo
        
        # Obter a categoria do trabalho usando a função existente
        categoria_trabalho = resolve_categoria_trabalho(trabalho, assignment)
        
        # Categorias disponíveis
        categorias = [
            "Prática Educacional",
            "Pesquisa Inovadora", 
            "Produto Inovador"
        ]
        
        logging.info(f"[DEBUG] Renderizando template com {len(categorias)} categorias")
        logging.info(f"[DEBUG] Categoria do trabalho: {categoria_trabalho}")
        return render_template(
            "revisor/selecionar_categoria_barema.html",
            trabalho=trabalho,
            categorias=categorias,
            categoria=categoria_trabalho,
            codigo_candidatura=codigo_candidatura
        )
    except Exception as e:
        logging.error(f"[DEBUG] Erro na rota selecionar_categoria_barema: {str(e)}")
        logging.error(f"[DEBUG] Tipo do erro: {type(e).__name__}")
        import traceback
        logging.error(f"[DEBUG] Traceback: {traceback.format_exc()}")
        raise


@revisor_routes.route("/revisor/avaliar_barema/<int:trabalho_id>/<categoria>", methods=["GET", "POST"])
def avaliar_barema(trabalho_id, categoria):
    """Interface de avaliação baseada nos critérios do barema da categoria selecionada."""
    from models.review import Submission, CategoriaBarema, EventoBarema
    from models.avaliacao import AvaliacaoBarema, AvaliacaoCriterio
    from models.event import RespostaFormulario
    
    # Verificar se o usuário é um revisor (comentado para permitir acesso via código)
    # if current_user.tipo not in ("revisor", "admin", "superadmin"):
    #     flash("Acesso negado!", "danger")
    #     return redirect(url_for("evento_routes.home"))
    
    # Buscar o trabalho
    trabalho = Submission.query.get_or_404(trabalho_id)
    
    # Buscar o assignment para obter o código da candidatura (definir no início)
    assignment = (
        Assignment.query
        .join(RespostaFormulario, Assignment.resposta_formulario_id == RespostaFormulario.id)
        .filter(RespostaFormulario.trabalho_id == trabalho_id)
        .first()
    )
    
    codigo_candidatura = None
    if assignment and assignment.reviewer:
        # Buscar a candidatura do revisor
        candidatura = RevisorCandidatura.query.filter_by(
            email=assignment.reviewer.email
        ).first()
        if candidatura:
            codigo_candidatura = candidatura.codigo
    
    # Resolver a categoria real do trabalho usando a função existente
    categoria_real = resolve_categoria_trabalho(trabalho, assignment)
    if not categoria_real:
        categoria_real = categoria  # Fallback para o parâmetro da URL
    
    # Buscar o barema da categoria
    barema = CategoriaBarema.query.filter_by(
        evento_id=trabalho.evento_id,
        categoria=categoria
    ).first()
    
    # Se não houver barema específico, buscar barema geral
    if not barema:
        barema_geral = EventoBarema.query.filter_by(evento_id=trabalho.evento_id).first()
        if barema_geral:
            # Criar um objeto mock para compatibilidade
            class BaremaMock:
                def __init__(self, evento_barema):
                    self.id = evento_barema.id
                    self.nome = f"Barema Geral - {categoria}"
                    self.criterios = evento_barema.requisitos or {}
            barema = BaremaMock(barema_geral)
    
    if not barema:
        flash(f"Barema não encontrado para a categoria '{categoria}'.", "danger")
        return redirect(url_for("revisor_routes.selecionar_categoria_barema", trabalho_id=trabalho_id))
    
    # Processar critérios do barema (JSON)
    criterios_dict = barema.criterios if hasattr(barema, 'criterios') else {}
    criterios = []
    for nome, detalhes in criterios_dict.items():
        criterio = {
            'id': nome,
            'nome': detalhes.get('nome', nome) if isinstance(detalhes, dict) else nome,
            'descricao': detalhes.get('descricao', '') if isinstance(detalhes, dict) else '',
            'nota_maxima': detalhes.get('pontuacao_max', detalhes.get('max', 10)) if isinstance(detalhes, dict) else 10,
            'peso': detalhes.get('peso', 1) if isinstance(detalhes, dict) else 1
        }
        criterios.append(criterio)
    
    if request.method == "POST":
        # Processar avaliação
        # Criar ou atualizar avaliação
        # Usar ID genérico para revisor quando não logado
        revisor_id = current_user.id if current_user.is_authenticated else 1
        
        # Determinar o nome do revisor usando a mesma lógica da rota progress
        nome_revisor = None
        if assignment and assignment.reviewer:
            candidatura = RevisorCandidatura.query.filter_by(
                email=assignment.reviewer.email
            ).first()
            if candidatura:
                nome_revisor = candidatura.nome
                if candidatura.status == 'aprovado':
                    revisor_user = Usuario.query.filter_by(email=candidatura.email).first()
                    if revisor_user and revisor_user.nome:
                        nome_revisor = revisor_user.nome
        
        avaliacao = AvaliacaoBarema.query.filter_by(
            trabalho_id=trabalho_id,
            revisor_id=revisor_id,
            barema_id=barema.id
        ).first()
        
        if not avaliacao:
            avaliacao = AvaliacaoBarema(
                trabalho_id=trabalho_id,
                revisor_id=revisor_id,
                nome_revisor=nome_revisor,
                barema_id=barema.id,
                categoria=categoria_real
            )
            db.session.add(avaliacao)
            db.session.flush()  # Para obter o ID
        else:
            # Atualizar o nome do revisor se a avaliação já existe
            avaliacao.nome_revisor = nome_revisor
        
        # Salvar avaliações dos critérios
        for criterio in criterios:
            nota = request.form.get(f"criterio_{criterio['id']}")
            observacao = request.form.get(f"observacao_{criterio['id']}", "")
            
            if nota:
                # Verificar se já existe avaliação para este critério
                avaliacao_criterio = AvaliacaoCriterio.query.filter_by(
                    avaliacao_id=avaliacao.id,
                    criterio_id=criterio['id']
                ).first()
                
                if avaliacao_criterio:
                    avaliacao_criterio.nota = float(nota)
                    avaliacao_criterio.observacao = observacao
                else:
                    avaliacao_criterio = AvaliacaoCriterio(
                        avaliacao_id=avaliacao.id,
                        criterio_id=criterio['id'],
                        nota=float(nota),
                        observacao=observacao
                    )
                    db.session.add(avaliacao_criterio)
        
        # Calcular nota final
        nota_final = sum(float(request.form.get(f"criterio_{c['id']}", 0)) for c in criterios)
        avaliacao.nota_final = nota_final
        avaliacao.data_avaliacao = datetime.now()
        
        # Atualizar o status do assignment para completed
        if assignment:
            assignment.completed = True
        
        db.session.commit()
        
        flash("Avaliação salva com sucesso!", "success")
        return redirect(url_for("revisor_routes.progress", codigo=codigo_candidatura))
    
    # Buscar o pdf_url através da RespostaFormulario
    pdf_url = None
    
    if assignment and assignment.resposta_formulario:
        resposta = assignment.resposta_formulario
        for resposta_campo in resposta.respostas_campos:
            if resposta_campo.campo.tipo == 'url' and 'pdf' in resposta_campo.campo.nome.lower():
                pdf_url = resposta_campo.valor
                break
    
    # Adicionar pdf_url ao objeto trabalho para compatibilidade com o template
    trabalho.pdf_url = pdf_url
    
    return render_template(
        "revisor/avaliar_barema.html",
        trabalho=trabalho,
        barema=barema,
        criterios=criterios,
        categoria=categoria_real,
        codigo_candidatura=codigo_candidatura
    )
>>>>>>> c593328b09b311b97c969034b12baa1c351a90bd
