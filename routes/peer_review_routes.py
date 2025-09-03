from flask import (
    Blueprint,
    request,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from werkzeug.security import generate_password_hash
from flask_login import login_required, current_user
from extensions import db

from models import (
    Usuario,
    Review,
    RevisaoConfig,
    Submission,
    Assignment,
    ConfiguracaoCliente,
    AuditLog,
    Evento,
    ReviewerApplication,
    RevisorCandidatura,
    RevisorProcess,
    WorkMetadata,
    Formulario,
)

import uuid
from datetime import datetime, timedelta
import random
from typing import Dict


peer_review_routes = Blueprint(
    "peer_review_routes", __name__, template_folder="../templates/peer_review"
)


@peer_review_routes.app_context_processor
def inject_reviewer_registration_flag():
    """Determina se o link de inscrição de revisores deve ser exibido."""
    return {"show_reviewer_registration": True}


# ---------------------------------------------------------------------------
# Submissões – Painel de Controle
# ---------------------------------------------------------------------------
@peer_review_routes.route("/submissoes/controle")
@login_required
def submission_control():
    """Render the submission control panel.

    Returns:
        Response: Page listing submissions and available reviewers.
    """
    if current_user.tipo not in ("cliente", "admin", "superadmin"):
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))
    
    # Get current client ID
    cliente_id = getattr(current_user, "id", None)
    
    # Get events associated with the logged-in client first
    eventos = Evento.query.filter_by(cliente_id=cliente_id).all()
    evento_ids = [e.id for e in eventos]
    
    # Get reviewer selection processes for this client
    processos_seletivos = (
        db.session.query(RevisorProcess, Formulario)
        .join(Formulario, RevisorProcess.formulario_id == Formulario.id)
        .filter(RevisorProcess.cliente_id == cliente_id)
        .all()
    )
    
    # Get submissions for client's events with metadata
    submissions = (
        db.session.query(Submission, WorkMetadata)
        .outerjoin(WorkMetadata, 
                  (Submission.evento_id == WorkMetadata.evento_id) & 
                  (Submission.title == WorkMetadata.titulo))
        .filter(Submission.evento_id.in_(evento_ids) if evento_ids else False)
        .all()
    )
    
    # Group by submission to avoid duplicates
    submission_dict = {}
    for sub, work_meta in submissions:
        if sub.id not in submission_dict:
            submission_dict[sub.id] = (sub, work_meta)
    
    submissions = list(submission_dict.values())
    
    # Get reviewers with their form responses
    reviewers_query = (
        db.session.query(Usuario, RevisorCandidatura)
        .join(RevisorCandidatura, Usuario.email == RevisorCandidatura.email)
        .filter(
            Usuario.tipo == "revisor",
            RevisorCandidatura.status == "aprovado",
        )
        .all()
    )
    
    # Process reviewers to extract form data
    reviewers = []
    for usuario, candidatura in reviewers_query:
        reviewer_data = {
            'id': usuario.id,
            'nome': usuario.nome,
            'email': usuario.email,
            'process_id': candidatura.process_id,
            'formacao': '',
            'instituicao': '',
            'area_atuacao': '',
            'titulacao': '',
            'experiencia': '',
            'respostas': candidatura.respostas or {}  # Include full responses for dynamic filtering
        }
        
        # Extract information from form responses (JSON field)
        if candidatura.respostas:
            respostas = candidatura.respostas
            
            # Map common form field names to reviewer data
            # Adjust these mappings based on your actual form structure
            if 'formacao' in respostas:
                reviewer_data['formacao'] = respostas['formacao']
            elif 'formação' in respostas:
                reviewer_data['formacao'] = respostas['formação']
            elif 'graduacao' in respostas:
                reviewer_data['formacao'] = respostas['graduacao']
            elif 'graduação' in respostas:
                reviewer_data['formacao'] = respostas['graduação']
                
            if 'instituicao' in respostas:
                reviewer_data['instituicao'] = respostas['instituicao']
            elif 'instituição' in respostas:
                reviewer_data['instituicao'] = respostas['instituição']
            elif 'universidade' in respostas:
                reviewer_data['instituicao'] = respostas['universidade']
                
            if 'area_atuacao' in respostas:
                reviewer_data['area_atuacao'] = respostas['area_atuacao']
            elif 'área_atuação' in respostas:
                reviewer_data['area_atuacao'] = respostas['área_atuação']
            elif 'area' in respostas:
                reviewer_data['area_atuacao'] = respostas['area']
                
            if 'titulacao' in respostas:
                reviewer_data['titulacao'] = respostas['titulacao']
            elif 'titulação' in respostas:
                reviewer_data['titulacao'] = respostas['titulação']
            elif 'titulo' in respostas:
                reviewer_data['titulacao'] = respostas['titulo']
                
            if 'experiencia' in respostas:
                reviewer_data['experiencia'] = respostas['experiencia']
            elif 'experiência' in respostas:
                reviewer_data['experiencia'] = respostas['experiência']
        
        # Create a simple object to maintain compatibility with template
        class ReviewerInfo:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        reviewers.append(ReviewerInfo(reviewer_data))
    
    
    # Get form fields for dynamic filtering
    form_fields = {}
    field_options = {}
    
    print(f"DEBUG: Processando {len(processos_seletivos)} processos seletivos para form_fields")
    
    for revisor_process, formulario in processos_seletivos:
        print(f"DEBUG: Processo {revisor_process.id}, Formulário ID: {revisor_process.formulario_id}")
        if revisor_process.formulario_id and formulario:
            # Get fields for this form
            campos = formulario.campos
            form_fields[revisor_process.id] = []
            field_options[revisor_process.id] = {}
            
            print(f"DEBUG: Formulário {formulario.id} tem {len(campos)} campos")
            
            for campo in campos:
                print(f"DEBUG: Verificando campo: {campo.nome} (protegido: {campo.protegido}, tipo: {campo.tipo})")
                # Skip protected fields (nome, email)
                if not campo.protegido:
                    form_fields[revisor_process.id].append({
                        'nome': campo.nome,
                        'tipo': campo.tipo,
                        'id': campo.id
                    })
                    print(f"DEBUG: Campo adicionado: {campo.nome} (tipo: {campo.tipo})")
                    
                    # Get unique values for this field from reviewer responses
                    if campo.tipo in ['dropdown', 'text', 'textarea']:
                        valores_unicos = set()
                        
                        # Get all responses for this process
                        candidaturas = RevisorCandidatura.query.filter_by(
                            process_id=revisor_process.id,
                            status='aprovado'
                        ).all()
                        
                        print(f"DEBUG: Encontradas {len(candidaturas)} candidaturas aprovadas para processo {revisor_process.id}")
                        
                        for candidatura in candidaturas:
                            if candidatura.respostas and campo.nome in candidatura.respostas:
                                valor = candidatura.respostas[campo.nome]
                                if valor and str(valor).strip():
                                    valores_unicos.add(str(valor).strip())
                        
                        # For dropdown fields, also include predefined options
                        if campo.tipo == 'dropdown' and campo.opcoes:
                            opcoes_predefinidas = [opt.strip() for opt in campo.opcoes.split(',') if opt.strip()]
                            valores_unicos.update(opcoes_predefinidas)
                        
                        field_options[revisor_process.id][campo.nome] = sorted(list(valores_unicos))
                        print(f"DEBUG: Campo {campo.nome} tem {len(valores_unicos)} valores únicos: {list(valores_unicos)[:5]}...")
                else:
                    print(f"DEBUG: Campo {campo.nome} foi ignorado por ser protegido")
    
    print(f"DEBUG: form_fields final: {form_fields}")
    print(f"DEBUG: field_options final: {field_options}")
    
    # eventos already retrieved above
    
    config = ConfiguracaoCliente.query.filter_by(
        cliente_id=cliente_id
    ).first()
    
    return render_template(
        "peer_review/submission_control.html",
        submissions=submissions,
        reviewers=reviewers,
        config=config,
        eventos=eventos,
        processos_seletivos=processos_seletivos,
        form_fields=form_fields,
        field_options=field_options,
    )


# ---------------------------------------------------------------------------
# Exclusão de todos os trabalhos do evento atual
# ---------------------------------------------------------------------------
@peer_review_routes.route("/submissoes/descartar_todos", methods=["POST"])
@login_required
def discard_all_submissions():
    """Exclui todos os trabalhos submetidos do evento atual.
    
    Returns:
        dict: JSON response with success flag and message.
    """
    # Obter dados do formulário
    print(f"DEBUG: Dados do formulário recebidos: {request.form}")
    print(f"DEBUG: Headers da requisição: {dict(request.headers)}")
    print(f"DEBUG: CSRF token no formulário: {request.form.get('csrf_token')}")
    print(f"DEBUG: Content-Type: {request.content_type}")
    
    print("\n=== INÍCIO discard_all_submissions ===")
    print(f"Método da requisição: {request.method}")
    print(f"Usuário atual: {current_user}")
    print(f"Tipo do usuário: {getattr(current_user, 'tipo', 'N/A')}")
    
    if current_user.tipo not in ("cliente", "admin", "superadmin"):
        print(f"ERRO: Acesso negado para tipo de usuário: {current_user.tipo}")
        return {"success": False, "message": "Acesso negado!"}, 403
    
    print("Verificação de acesso passou, iniciando processo...")
    
    try:
        # Obter o cliente_id do usuário atual
        cliente_id = getattr(current_user, "id", None)
        print(f"Cliente ID obtido: {cliente_id}")
        
        if not cliente_id:
            print("ERRO: Cliente ID não encontrado")
            return {"success": False, "message": "Usuário não identificado"}, 400
        
        # Buscar todas as submissões (incluindo as sem evento_id)
        print(f"Buscando todas as submissões no sistema...")
        submissions = Submission.query.all()
        print(f"Total de submissões encontradas: {len(submissions)}")
        
        # Filtrar submissões por eventos do cliente (se tiverem evento_id)
        # ou incluir submissões sem evento_id para clientes específicos
        eventos_cliente = Evento.query.filter_by(cliente_id=cliente_id).all()
        evento_ids_cliente = [e.id for e in eventos_cliente]
        print(f"Eventos do cliente {cliente_id}: {evento_ids_cliente}")
        
        # Filtrar submissões relevantes:
        # 1. Submissões vinculadas a eventos do cliente
        # 2. Submissões sem evento_id (assumindo que pertencem ao contexto atual)
        submissions_relevantes = []
        for s in submissions:
            if s.evento_id is None or s.evento_id in evento_ids_cliente:
                submissions_relevantes.append(s)
        
        print(f"Submissões relevantes para exclusão: {len(submissions_relevantes)}")
        
        if not submissions_relevantes:
            print("AVISO: Nenhuma submissão encontrada para excluir")
            return {"success": False, "message": "Nenhum trabalho encontrado para excluir"}, 404
        
        submissions = submissions_relevantes
        
        submission_ids = [s.id for s in submissions]
        print(f"IDs das submissões: {submission_ids}")
        
        print("Iniciando exclusão de registros relacionados...")
        
        # Excluir registros relacionados primeiro (para evitar violação de chave estrangeira)
        # 1. Excluir Reviews
        print("Excluindo Reviews...")
        reviews_deleted = Review.query.filter(Review.submission_id.in_(submission_ids)).delete(synchronize_session=False)
        print(f"Reviews excluídas: {reviews_deleted}")
        
        # 2. Excluir Assignments
        print("Excluindo Assignments...")
        # Buscar assignments através de RespostaFormulario
        assignments_to_delete = (
            Assignment.query
            .join(RespostaFormulario, Assignment.resposta_formulario_id == RespostaFormulario.id)
            .filter(RespostaFormulario.trabalho_id.in_(submission_ids))
            .all()
        )
        assignments_deleted = len(assignments_to_delete)
        for assignment in assignments_to_delete:
            db.session.delete(assignment)
        print(f"Assignments excluídas: {assignments_deleted}")
        
        # 3. Excluir AuditLogs relacionados
        print("Excluindo AuditLogs...")
        audits_deleted = AuditLog.query.filter(AuditLog.submission_id.in_(submission_ids)).delete(synchronize_session=False)
        print(f"AuditLogs excluídos: {audits_deleted}")
        
        # 4. Excluir WorkMetadata relacionados (apenas se houver eventos do cliente)
        if evento_ids_cliente:
            print("Excluindo WorkMetadata...")
            metadata_deleted = WorkMetadata.query.filter(WorkMetadata.evento_id.in_(evento_ids_cliente)).delete(synchronize_session=False)
            print(f"WorkMetadata excluídos: {metadata_deleted}")
        
        # 5. Finalmente, excluir as Submissions
        print("Excluindo Submissions...")
        submissions_deleted = Submission.query.filter(Submission.id.in_(submission_ids)).delete(synchronize_session=False)
        print(f"Submissions excluídas: {submissions_deleted}")
        
        # Commit das alterações
        print("Fazendo commit das alterações...")
        db.session.commit()
        print("Commit realizado com sucesso!")
        
        # Log da ação
        print("Criando log de auditoria...")
        usuario = Usuario.query.get(cliente_id)
        uid = usuario.id if usuario else None
        print(f"UID para log: {uid}")
        
        db.session.add(
            AuditLog(
                user_id=uid,
                event_type="bulk_deletion"
            )
        )
        db.session.commit()
        print("Log de auditoria criado com sucesso!")
        
        success_message = f"Todos os {len(submissions)} trabalhos foram excluídos com sucesso!"
        print(f"SUCESSO: {success_message}")
        
        response = {
            "success": True, 
            "message": success_message
        }
        print(f"Resposta a ser enviada: {response}")
        print("=== FIM discard_all_submissions ===\n")
        
        return response
        
    except Exception as e:
        print(f"ERRO CAPTURADO: {str(e)}")
        print(f"Tipo do erro: {type(e).__name__}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        
        print("Fazendo rollback...")
        db.session.rollback()
        
        error_response = {
            "success": False, 
            "message": f"Erro ao excluir trabalhos: {str(e)}"
        }
        print(f"Resposta de erro: {error_response}")
        print("=== FIM discard_all_submissions (COM ERRO) ===\n")
        
        return error_response, 500


# ---------------------------------------------------------------------------
# Atribuição manual de revisores (via AJAX)
# ---------------------------------------------------------------------------
@peer_review_routes.route("/assign_reviews", methods=["POST"])
@login_required
def assign_reviews():
    """Assign reviewers to submissions via JSON.

    Only users of type ``revisor`` with an approved ``RevisorCandidatura``
    are eligible. The request body must map submission IDs to lists of
    reviewer IDs.

    Returns:
        dict: JSON object with success flag or error message.
    """
    if current_user.tipo not in ("cliente", "admin", "superadmin"):
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    usuario = Usuario.query.get(getattr(current_user, "id", None))
    uid = usuario.id if usuario else None  # salva log mesmo sem usuário

    data = request.get_json()
    if not data:
        return {"success": False}, 400

    invalid_reviewers: list[int] = []

    for submission_id, reviewers in data.items():
        submission = Submission.query.get(submission_id)
        if not submission:
            continue

        evento = Evento.query.get(submission.evento_id)
        cliente_id = evento.cliente_id if evento else None

        for reviewer_id in reviewers:
            reviewer = Usuario.query.get(reviewer_id)
            if not reviewer or reviewer.tipo != "revisor":
                invalid_reviewers.append(reviewer_id)
                continue

            candidatura = (
                RevisorCandidatura.query.join(
                    RevisorProcess,
                    RevisorCandidatura.process_id == RevisorProcess.id,
                )
                .filter(
                    RevisorProcess.cliente_id == cliente_id,
                    RevisorCandidatura.status == "aprovado",
                    RevisorCandidatura.email == reviewer.email,
                )
                .first()
            )
            if not candidatura:
                invalid_reviewers.append(reviewer_id)
                continue

            # Cria Review + Assignment ----------------------------------
            rev = Review(
                submission_id=submission.id,
                reviewer_id=reviewer_id,
                access_code=str(uuid.uuid4())[:8],
            )
            db.session.add(rev)

            config = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
            prazo_dias = config.prazo_parecer_dias if config else 14

            # Busca ou cria RespostaFormulario para o trabalho
            resposta_formulario = RespostaFormulario.query.filter_by(trabalho_id=submission.id).first()
            if not resposta_formulario:
                # Cria uma resposta de formulário básica se não existir
                resposta_formulario = RespostaFormulario(
                    trabalho_id=submission.id,
                    formulario_id=None,  # Pode ser None para assignments manuais
                    respostas={},
                    data_submissao=datetime.utcnow()
                )
                db.session.add(resposta_formulario)
                db.session.flush()  # Para obter o ID

            assignment = Assignment(
                resposta_formulario_id=resposta_formulario.id,
                reviewer_id=reviewer_id,
                deadline=datetime.utcnow() + timedelta(days=prazo_dias),
            )
            db.session.add(assignment)

            # Log -------------------------------------------------------
            db.session.add(
                AuditLog(
                    user_id=uid,
                    submission_id=submission.id,
                    event_type="assignment",
                )
            )

    db.session.commit()

    if invalid_reviewers:
        return {
            "success": False,
            "message": f"Revisores não aprovados: {invalid_reviewers}",
        }, 400

    return {"success": True}


# ---------------------------------------------------------------------------
# Atribuição por filtros para revisores aprovados
# ---------------------------------------------------------------------------
@peer_review_routes.route("/revisores/sortear", methods=["POST"])
@peer_review_routes.route("/assign_by_filters", methods=["POST"])
@login_required
def assign_by_filters():
    """Distribui submissões a revisores aprovados com base em filtros."""
    if current_user.tipo not in ("cliente", "admin", "superadmin"):
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    data = request.get_json() or {}
    filtros: dict = data.get("filters", {})
    limite = data.get("limit")
    max_per_submission = data.get("max_per_submission")

    usuario = Usuario.query.get(getattr(current_user, "id", None))
    uid = usuario.id if usuario else None
    cliente_id = getattr(current_user, "id", None)

    config = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
    if limite is None and config:
        limite = config.max_trabalhos_por_revisor
    if limite is None:
        limite = 1

    max_por_sub = config.num_revisores_max if config else 1
    if max_per_submission is not None:
        max_por_sub = int(max_per_submission)
    prazo_dias = config.prazo_parecer_dias if config else 14

    candidaturas = (
        RevisorCandidatura.query.join(
            RevisorProcess, RevisorCandidatura.process_id == RevisorProcess.id
        )
        .filter(
            RevisorProcess.cliente_id == cliente_id,
            RevisorCandidatura.status == "aprovado",
        )
        .all()
    )

    reviewers: list[Usuario] = []
    evento_ids: set[int] = set()
    for cand in candidaturas:
        respostas = cand.respostas or {}
        if all(respostas.get(c) == v for c, v in filtros.items()):
            reviewer = Usuario.query.filter_by(email=cand.email).first()
            if reviewer:
                reviewers.append(reviewer)
                processo = cand.process
                if processo.evento_id:
                    evento_ids.add(processo.evento_id)
                evento_ids.update(e.id for e in processo.eventos)

    if not reviewers:
        return {"success": False, "message": "Nenhum revisor encontrado"}, 400

    submissions = Submission.query.filter(Submission.evento_id.in_(evento_ids)).all()
    elegiveis = [s for s in submissions if len(s.assignments) < max_por_sub]
    if not elegiveis:
        return {"success": False, "message": "Nenhuma submissão elegível"}, 400

    random.shuffle(reviewers)
    random.shuffle(elegiveis)

    contagem_revisor = {
        r.id: Assignment.query.filter_by(reviewer_id=r.id).count() for r in reviewers
    }
    contagem_sub = {s.id: len(s.assignments) for s in elegiveis}

    criados = 0
    for reviewer in reviewers:
        while contagem_revisor[reviewer.id] < limite and elegiveis:
            random.shuffle(elegiveis)
            atribuido = False
            for sub in list(elegiveis):
                existente = Assignment.query.filter_by(
                    submission_id=sub.id, reviewer_id=reviewer.id
                ).first()
                if existente:
                    continue
                assignment = Assignment(
                    submission_id=sub.id,
                    reviewer_id=reviewer.id,
                    deadline=datetime.utcnow() + timedelta(days=prazo_dias),
                )
                db.session.add(assignment)
                db.session.add(
                    AuditLog(
                        user_id=uid,
                        submission_id=sub.id,
                        event_type="assignment",
                    )
                )
                criados += 1
                contagem_revisor[reviewer.id] += 1
                contagem_sub[sub.id] += 1
                if contagem_sub[sub.id] >= max_por_sub:
                    elegiveis.remove(sub)
                atribuido = True
                break
            if not atribuido:
                break

    db.session.commit()
    return {"success": True, "assignments": criados}


# ---------------------------------------------------------------------------
# Atribuição automática de revisores com base na área
# ---------------------------------------------------------------------------
@peer_review_routes.route("/auto_assign/<int:evento_id>", methods=["POST"])
@login_required
def auto_assign(evento_id):
    """Automatically assign reviewers to submissions by area.

    Args:
        evento_id (int): Event identifier.

    Returns:
        dict: JSON response with success flag.
    """
    if current_user.tipo not in ("cliente", "admin", "superadmin"):
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    usuario = Usuario.query.get(getattr(current_user, "id", None))
    uid = usuario.id if usuario else None  # salva log mesmo sem usuário

    config = RevisaoConfig.query.filter_by(evento_id=evento_id).first()
    if not config:
        return {"success": False, "message": "Configuração não encontrada"}, 400

    trabalhos = Submission.query.filter_by(evento_id=evento_id).all()
    revisores = (
        Usuario.query.join(
            RevisorCandidatura, Usuario.email == RevisorCandidatura.email
        )
        .filter(
            Usuario.tipo == "revisor", RevisorCandidatura.status == "aprovado"
        )
        .all()
    )

    # Agrupa revisores por formação/área -----------------------------------
    area_map: dict[str, list[Usuario]] = {}
    for r in revisores:
        area_map.setdefault(r.formacao, []).append(r)

    for t in trabalhos:
        area = t.attributes.get("area_tematica") if t.attributes else None
        revisores_area = area_map.get(area, revisores)
        selecionados = revisores_area[: config.numero_revisores]

        for reviewer in selecionados:
            rev = Review(
                submission_id=t.id,
                reviewer_id=reviewer.id,
                access_code=str(uuid.uuid4())[:8],
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
                    user_id=uid,
                    submission_id=t.id,
                    event_type="assignment",
                )
            )

    db.session.commit()
    return {"success": True}


# ---------------------------------------------------------------------------
# Criação pontual de Review
# ---------------------------------------------------------------------------
@peer_review_routes.route("/create_review", methods=["POST"])
@login_required
def create_review():
    """Cria uma revisão única para uma submissão e um revisor."""
    if current_user.tipo not in ("cliente", "admin", "superadmin"):
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    data = request.get_json(silent=True) or {}
    submission_id = request.form.get("submission_id") or data.get("submission_id")
    reviewer_id = request.form.get("reviewer_id") or data.get("reviewer_id")

    if not submission_id or not reviewer_id:
        return {"success": False, "message": "dados insuficientes"}, 400

    submission = Submission.query.get(int(submission_id))
    rev = Review(
        submission_id=submission.id,
        reviewer_id=int(reviewer_id),
        locator=str(uuid.uuid4()),
        access_code=str(uuid.uuid4())[:8],
    )
    db.session.add(rev)
    db.session.flush()
    notify_reviewer(rev)
    db.session.commit()

    if request.is_json:
        return {
            "success": True,
            "locator": rev.locator,
            "access_code": rev.access_code,
        }

    flash(f"Código do revisor: {rev.access_code}", "success")
    return redirect(
        request.referrer
        or url_for("peer_review_routes.editor_reviews", evento_id=submission.evento_id)
    )


# ---------------------------------------------------------------------------
# Formulário de revisão (público via locator)
# ---------------------------------------------------------------------------
@peer_review_routes.route("/review/<locator>", methods=["GET", "POST"])
def review_form(locator):
    """Handle display and submission of a review form.

    Args:
        locator (str): Public identifier for the review.

    Returns:
        Response: Rendered form or redirect after submission.
    """
    review = Review.query.filter_by(locator=locator).first_or_404()
    barema = EventoBarema.query.filter_by(evento_id=review.submission.evento_id).first()

    if request.method == "GET" and review.started_at is None:
        review.started_at = datetime.utcnow()
        db.session.commit()

    if request.method == "POST":
        codigo = request.form.get("codigo")
        if codigo != review.access_code:
            flash("Código incorreto!", "danger")

            return render_template(
                "peer_review/review_form.html", review=review, barema=barema
            )

        scores: Dict[str, float] = {}

        total = 0.0
        if barema and barema.requisitos:
            for requisito, faixa in barema.requisitos.items():
                nota_raw = request.form.get(requisito)
                if nota_raw is None:
                    continue
                try:
                    nota = float(nota_raw)
                except (TypeError, ValueError):
                    continue
                min_val = faixa.get("min", 0)
                max_val = faixa.get("max")
                if max_val is not None and (nota < min_val or nota > max_val):
                    flash(
                        f"Nota para {requisito} deve estar entre {min_val} e {max_val}",
                        "danger",
                    )
                    return render_template(
                        "peer_review/review_form.html", review=review, barema=barema
                    )
                scores[requisito] = nota
                total += nota
        else:
            try:
                total = float(request.form.get("nota", 0))
            except (TypeError, ValueError):
                flash("Nota inválida (use 1–5).", "danger")
                return render_template(
                    "peer_review/review_form.html", review=review, barema=barema
                )

        review.scores = scores or None
        review.note = total
        review.comments = request.form.get("comentarios")
        review.blind_type = (
            "nome" if request.form.get("mostrar_nome") == "on" else "anonimo"
        )
        review.finished_at = datetime.utcnow()
        if review.started_at:
            review.duration_seconds = int(
                (review.finished_at - review.started_at).total_seconds()
            )
        review.submitted_at = review.finished_at

        assignment = Assignment.query.filter_by(
            submission_id=review.submission_id, reviewer_id=review.reviewer_id
        ).first()
        if assignment:
            assignment.completed = True

        db.session.commit()

        flash(f"Revisão enviada! Total: {total}", "success")

        return redirect(url_for("peer_review_routes.review_form", locator=locator))

    return render_template("peer_review/review_form.html", review=review, barema=barema)


# ---------------------------------------------------------------------------
# Dashboards (autor | revisor | editor)
# ---------------------------------------------------------------------------


@peer_review_routes.route("/dashboard/author_reviews")
@login_required
def author_reviews():
    """Show review status for submissions by the current user.

    Returns:
        Response: Author dashboard page.
    """
    trabalhos = Submission.query.filter_by(author_id=current_user.id).all()
    return render_template("peer_review/dashboard_author.html", trabalhos=trabalhos)


@peer_review_routes.route("/dashboard/reviewer_reviews")
@login_required
def reviewer_reviews():
    """Show assignments for the logged-in reviewer.

    Returns:
        Response: Reviewer dashboard page.
    """
    assignments = Assignment.query.filter_by(reviewer_id=current_user.id).all()
    config = RevisaoConfig.query.first()
    return render_template(
        "peer_review/dashboard_reviewer.html", assignments=assignments, config=config
    )


@peer_review_routes.route("/dashboard/editor_reviews/<int:evento_id>")
@login_required
def editor_reviews(evento_id):
    """List reviews for an event to privileged users.

    Args:
        evento_id (int): Event identifier.

    Returns:
        Response: Editor dashboard page.
    """
    if current_user.tipo not in ("cliente", "admin", "superadmin"):
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    trabalhos = Submission.query.filter_by(evento_id=evento_id).all()
    return render_template("peer_review/dashboard_editor.html", trabalhos=trabalhos)


@peer_review_routes.route("/dashboard/client_reviews")
@login_required
def client_reviews_panel():
    """Painel para clientes acompanharem o progresso das revisões."""
    if current_user.tipo not in ("cliente", "admin", "superadmin"):
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    submissions = (
        Submission.query.join(Evento)
        .filter(Evento.cliente_id == getattr(current_user, "id", None))
        .all()
    )

    items = []
    for sub in submissions:
        assignments = sub.assignments
        total = len(assignments)
        completed = sum(1 for a in assignments if a.completed)
        notes = [r.note for r in sub.reviews if r.note is not None]
        grade = sum(notes) / len(notes) if notes else None
        reviewers = [
            a.reviewer.nome
            for a in assignments
            if a.completed and a.reviewer and a.reviewer.nome
        ]
        items.append(
            {
                "submission": sub,
                "completed": completed,
                "total": total,
                "grade": grade,
                "reviewers": reviewers,
            }
        )

    return render_template("peer_review/dashboard_client.html", items=items)


@peer_review_routes.route("/assign_by_category", methods=["POST"])
@login_required
def assign_by_category():
    """Distribui trabalhos para revisores baseado na categoria dos trabalhos.
    
    Agrupa trabalhos por categoria e revisores por área de especialização,
    fazendo correspondência automática entre categoria do trabalho e área do revisor.
    
    Returns:
        JSON: Resultado da operação com estatísticas de atribuição.
    """
    try:
        # Verificar se usuário tem permissão
        if current_user.tipo not in ("cliente", "admin", "superadmin"):
            return jsonify({"success": False, "message": "Acesso negado!"}), 403
        
        # Obter evento_id da sessão ou parâmetro
        evento_id = session.get("evento_id")
        if not evento_id:
            return jsonify({"success": False, "message": "Evento não identificado!"}), 400
        
        # Buscar trabalhos importados que ainda não foram atribuídos
        trabalhos = Submission.query.filter_by(
            evento_id=evento_id,
            status="imported"
        ).all()
        
        if not trabalhos:
            return jsonify({
                "success": False, 
                "message": "Nenhum trabalho disponível para atribuição!"
            }), 400
        
        # Buscar revisores ativos
        revisores = Usuario.query.filter_by(tipo="revisor", ativo=True).all()
        
        if not revisores:
            return jsonify({
                "success": False, 
                "message": "Nenhum revisor disponível!"
            }), 400
        
        # Agrupar trabalhos por categoria
        trabalhos_por_categoria = {}
        for trabalho in trabalhos:
            categoria = getattr(trabalho.work_metadata, 'categoria', None) if trabalho.work_metadata else None
            if categoria:
                if categoria not in trabalhos_por_categoria:
                    trabalhos_por_categoria[categoria] = []
                trabalhos_por_categoria[categoria].append(trabalho)
        
        # Agrupar revisores por área de formação
        revisores_por_area = {}
        for revisor in revisores:
            area = getattr(revisor, 'formacao', None)
            if area:
                if area not in revisores_por_area:
                    revisores_por_area[area] = []
                revisores_por_area[area].append(revisor)
        
        atribuicoes_criadas = 0
        categorias_processadas = 0
        
        # Fazer correspondência entre categorias e áreas
        for categoria, trabalhos_categoria in trabalhos_por_categoria.items():
            # Buscar revisores com área compatível (correspondência exata ou similar)
            revisores_compativeis = []
            
            # Primeiro, busca correspondência exata
            if categoria in revisores_por_area:
                revisores_compativeis.extend(revisores_por_area[categoria])
            
            # Se não encontrou correspondência exata, busca por similaridade
            if not revisores_compativeis:
                categoria_lower = categoria.lower()
                for area, revisores_area in revisores_por_area.items():
                    area_lower = area.lower()
                    if (categoria_lower in area_lower or 
                        area_lower in categoria_lower or
                        any(palavra in area_lower for palavra in categoria_lower.split()) or
                        any(palavra in categoria_lower for palavra in area_lower.split())):
                        revisores_compativeis.extend(revisores_area)
            
            # Se ainda não encontrou, usa todos os revisores disponíveis
            if not revisores_compativeis:
                revisores_compativeis = revisores
            
            # Atribuir revisores aos trabalhos desta categoria
            if revisores_compativeis:
                categorias_processadas += 1
                revisor_index = 0
                
                for trabalho in trabalhos_categoria:
                    # Selecionar revisor de forma circular
                    revisor = revisores_compativeis[revisor_index % len(revisores_compativeis)]
                    
                    # Verificar se já existe atribuição
                    existing_assignment = Assignment.query.filter_by(
                        submission_id=trabalho.id,
                        reviewer_id=revisor.id
                    ).first()
                    
                    if not existing_assignment:
                        # Criar nova atribuição
                        assignment = Assignment(
                            submission_id=trabalho.id,
                            reviewer_id=revisor.id,
                            assigned_at=datetime.utcnow()
                        )
                        db.session.add(assignment)
                        
                        # Criar review associada
                        review = Review(
                            submission_id=trabalho.id,
                            reviewer_id=revisor.id,
                            locator=str(uuid.uuid4()),
                            access_code=str(uuid.uuid4())[:8]
                        )
                        db.session.add(review)
                        
                        atribuicoes_criadas += 1
                    
                    revisor_index += 1
        
        # Salvar todas as alterações
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Distribuição concluída! {atribuicoes_criadas} atribuições criadas para {categorias_processadas} categorias.",
            "stats": {
                "atribuicoes_criadas": atribuicoes_criadas,
                "categorias_processadas": categorias_processadas,
                "total_trabalhos": len(trabalhos),
                "total_revisores": len(revisores)
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False, 
            "message": f"Erro interno: {str(e)}"
        }), 500


# ------------------------- ROTAS FLAT PARA SPAS ---------------------------
@peer_review_routes.route("/peer-review/author")
def author_dashboard():
    """Serve base page for the author dashboard SPA.

    Returns:
        Response: Rendered HTML template.
    """
    # SPA / Vue / React etc. – serve apenas o HTML base
    return render_template("peer_review/author/dashboard.html", submissions=[])


@peer_review_routes.route("/peer-review/reviewer", methods=["GET", "POST"])
def reviewer_dashboard():
    """Dashboard de revisão com acesso autenticado ou via código."""

    # 1) Se veio POST → redireciona para GET com parâmetros -----------------
    if request.method == "POST":
        locator = request.form.get("locator")
        code = request.form.get("code")
        return redirect(
            url_for("peer_review_routes.reviewer_dashboard", locator=locator, code=code)
        )

    # 2) Usuário autenticado ------------------------------------------------
    if current_user.is_authenticated:
        tasks = Assignment.query.filter_by(reviewer_id=current_user.id).all()
        return render_template("peer_review/reviewer/dashboard.html", tasks=tasks)

    # 3) Tentativa de acesso via locator + code -----------------------------
    locator = request.args.get("locator") or session.get("reviewer_locator")
    code = request.args.get("code") or session.get("reviewer_code")

    if locator and code:
        # 3a) Valida como Review -------------------------------------------
        review = Review.query.filter_by(locator=locator).first()
        if review and review.access_code == code:
            session["reviewer_locator"] = locator
            session["reviewer_code"] = code
            tasks = Assignment.query.filter_by(reviewer_id=review.reviewer_id).all()
            return render_template("peer_review/reviewer/dashboard.html", tasks=tasks)

        # 3b) Valida como Submission ---------------------------------------
        submission = Submission.query.filter_by(locator=locator).first()
        if submission and submission.check_code(code):
            session["reviewer_locator"] = locator
            session["reviewer_code"] = code
            return render_template("peer_review/reviewer/dashboard.html", tasks=[])

        flash("Localizador ou código inválido.", "danger")
    elif locator or code:
        flash("Informe **ambos**: localizador e código.", "danger")

    # Falha de autenticação --------------------------------------------------
    flash("Credenciais inválidas para acesso de revisor.", "danger")
    return redirect(url_for("evento_routes.home") + "#revisorModal")


@peer_review_routes.route("/peer-review/editor")
def editor_dashboard_page():
    """Serve base page for the editor dashboard SPA.

    Returns:
        Response: Rendered HTML template.
    """
    return render_template("peer_review/editor/dashboard.html", decisions=[])


@peer_review_routes.route("/peer-review/register", methods=["GET", "POST"])
def reviewer_registration():
    """Registro simples de novos revisores."""
    if request.method == "POST":
        nome = request.form.get("nome")
        cpf = request.form.get("cpf")
        email = request.form.get("email")
        senha = request.form.get("senha")
        formacao = request.form.get("formacao")

        if not all([nome, cpf, email, senha, formacao]):
            flash("Preencha todos os campos obrigatórios.", "danger")
            return render_template("peer_review/reviewer_registration.html")

        usuario = Usuario.query.filter(
            (Usuario.email == email) | (Usuario.cpf == cpf)
        ).first()
        if usuario is None:
            usuario = Usuario(
                nome=nome,
                cpf=cpf,
                email=email,
                senha=generate_password_hash(senha, method="pbkdf2:sha256"),
                formacao=formacao,
                tipo="revisor",
            )
            db.session.add(usuario)
            db.session.flush()

        db.session.add(ReviewerApplication(usuario_id=usuario.id))
        db.session.commit()
        flash("Candidatura registrada!", "success")
        return redirect(url_for("auth_routes.login"))

    return render_template("peer_review/reviewer_registration.html")
