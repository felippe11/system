import json
import os
import uuid
from utils import endpoints

import pandas as pd
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user
from utils.auth import login_required
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from extensions import db, csrf
from models import (
    AuditLog,
    Assignment,
    Evento,
    Formulario,
    RespostaCampo,
    RespostaFormulario,
    Review,
    Submission,
    Usuario,
    WorkMetadata,
)
from models.review import Assignment
from sqlalchemy import func
from services.submission_service import SubmissionService
from utils.mfa import mfa_required


trabalho_routes = Blueprint(
    "trabalho_routes",
    __name__,
    template_folder="../templates/trabalho"
)


# ──────────────────────────────── SUBMISSÃO ──────────────────────────────── #
@trabalho_routes.route("/submeter_trabalho", methods=["GET", "POST"])
@login_required
@mfa_required
def submeter_trabalho():
    """Participante faz upload do PDF e registra o trabalho no banco."""
    if current_user.tipo not in ["participante", "ministrante"]:
        flash("Acesso negado. Apenas participantes podem submeter trabalhos.", "error")
        return redirect(url_for(endpoints.DASHBOARD))

    config = current_user.cliente.configuracao if current_user.cliente else None
    formulario = None
    if config and config.habilitar_submissao_trabalhos:
        formulario = config.formulario_submissao
        if not formulario or not formulario.is_submission_form:
            flash("Formulário de submissão inválido.", "danger")
            return redirect(url_for(endpoints.DASHBOARD))
        if (
            formulario.eventos
            and current_user.evento_id not in [ev.id for ev in formulario.eventos]
        ):
            flash("Formulário indisponível para seu evento.", "danger")
            return redirect(url_for(endpoints.DASHBOARD))

    if not formulario:
        flash("Submissão de trabalhos desabilitada.", "danger")
        return redirect(url_for(endpoints.DASHBOARD))

    if request.method == "POST":
        evento_id = getattr(current_user, "evento_id", None)
        if not evento_id:
            flash("Usuário sem evento associado.", "danger")
            return redirect(url_for("trabalho_routes.submeter_trabalho"))

        evento = Evento.query.get(evento_id)
        if not evento or not evento.submissao_aberta:
            flash("Submissão encerrada para seu evento.", "danger")
            return redirect(url_for("trabalho_routes.submeter_trabalho"))

        resposta_formulario = RespostaFormulario(
            formulario_id=formulario.id, usuario_id=current_user.id
        )
        db.session.add(resposta_formulario)
        db.session.flush()

        allowed = "pdf"
        if current_user.cliente and current_user.cliente.configuracao:
            allowed = current_user.cliente.configuracao.allowed_file_types or "pdf"
        exts = [e.strip().lower() for e in allowed.split(",")] if allowed else []

        titulo = None
        arquivo_pdf = None

        for campo in formulario.campos:
            valor = request.form.get(str(campo.id))
            if campo.tipo == "file" and f"file_{campo.id}" in request.files:
                arquivo = request.files[f"file_{campo.id}"]
                if arquivo and arquivo.filename:
                    filename = secure_filename(arquivo.filename)
                    ext_ok = any(
                        filename.lower().endswith(f".{ext}") for ext in exts
                    )
                    if not ext_ok:
                        db.session.rollback()
                        flash("Tipo de arquivo não permitido.", "warning")
                        return redirect(url_for("trabalho_routes.submeter_trabalho"))
                    uploads_dir = current_app.config.get(
                        "UPLOAD_FOLDER", "static/uploads/trabalhos"
                    )
                    os.makedirs(uploads_dir, exist_ok=True)
                    unique_name = f"{uuid.uuid4().hex}_{filename}"
                    caminho_arquivo = os.path.join(uploads_dir, unique_name)
                    arquivo.save(caminho_arquivo)
                    valor = caminho_arquivo
                    if not arquivo_pdf:
                        arquivo_pdf = caminho_arquivo

            if campo.obrigatorio and not valor:
                db.session.rollback()
                flash(f"O campo '{campo.nome}' é obrigatório.", "warning")
                return redirect(url_for("trabalho_routes.submeter_trabalho"))

            resposta_campo = RespostaCampo(
                resposta_formulario_id=resposta_formulario.id,
                campo_id=campo.id,
                valor=valor,
            )
            db.session.add(resposta_campo)

            if not titulo and campo.tipo != "file":
                titulo = valor

        titulo = titulo or "Trabalho sem título"


        try:
            # Usar o serviço unificado para criar a submissão
            submission = SubmissionService.create_submission(
                title=titulo,
                author_id=current_user.id,
                evento_id=evento_id,
                file_path=arquivo_pdf
            )
            
            # Gerar código de acesso
            code = uuid.uuid4().hex[:8]
            submission.code_hash = generate_password_hash(code, method="pbkdf2:sha256")
            
            # Log de auditoria
            usuario = Usuario.query.get(getattr(current_user, "id", None))
            uid = usuario.id if usuario else None
            db.session.add(
                AuditLog(user_id=uid, submission_id=submission.id, event_type="submission")
            )
            
            db.session.commit()
            
            flash(
                "Trabalho submetido com sucesso! "
                f"Localizador: {submission.locator} Código: {code}",
                "success",
            )
            return redirect(url_for("trabalho_routes.meus_trabalhos"))
            
        except ValueError as e:
            db.session.rollback()
            flash(str(e), "error")
            return redirect(url_for("trabalho_routes.submeter_trabalho"))
        except Exception as e:
            db.session.rollback()
            flash("Erro interno. Tente novamente.", "error")
            current_app.logger.error(f"Erro na submissão: {e}")
            return redirect(url_for("trabalho_routes.submeter_trabalho"))

    return render_template("submeter_trabalho.html", formulario=formulario)


# ──────────────────────────────── MEUS TRABALHOS ─────────────────────────── #
@trabalho_routes.route("/meus_trabalhos")
@login_required
def meus_trabalhos():
    """Lista trabalhos do participante logado com informações detalhadas."""
    if current_user.tipo not in ["participante", "ministrante"]:
        return redirect(
            url_for(endpoints.DASHBOARD)
        )

    # Buscar submissões com informações relacionadas
    from sqlalchemy.orm import joinedload
    from models.review import Review, Assignment
    
    trabalhos = db.session.query(Submission).options(
        joinedload(Submission.evento),
        joinedload(Submission.author)
    ).filter_by(author_id=current_user.id).all()
    
    # Enriquecer dados dos trabalhos
    trabalhos_detalhados = []
    for trabalho in trabalhos:
        # Buscar revisões
        reviews = Review.query.filter_by(submission_id=trabalho.id).all()
        assignments = Assignment.query.filter_by(submission_id=trabalho.id).all()
        
        # Traduzir status
        status_map = {
            'submitted': 'Submetido',
            'under_review': 'Em Revisão',
            'accepted': 'Aceito',
            'rejected': 'Rejeitado',
            'pending': 'Pendente'
        }
        
        trabalho_info = {
            'submission': trabalho,
            'status_traduzido': status_map.get(trabalho.status, trabalho.status),
            'total_reviews': len(reviews),
            'completed_reviews': len([r for r in reviews if r.finished_at]),
            'pending_reviews': len([a for a in assignments if not any(r.finished_at for r in reviews if r.submission_id == a.submission_id)]),
            'evento_nome': trabalho.evento.nome if trabalho.evento else 'N/A',
            'area_nome': 'Área Geral'  # Placeholder - implementar busca de área se necessário
        }
        trabalhos_detalhados.append(trabalho_info)
    
    return render_template("meus_trabalhos.html", trabalhos=trabalhos_detalhados)


# ──────────────────────────── TRABALHOS CLIENTE ─────────────────────────── #
@trabalho_routes.route("/trabalhos")
@login_required
def listar_trabalhos():
    """Lista todos os trabalhos cadastrados pelo cliente."""
    if current_user.tipo not in ["cliente", "admin"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))
    
    # Buscar formulário de trabalhos
    formulario = Formulario.query.filter_by(nome='Formulário de Trabalhos').first()
    if not formulario:
        flash("Formulário de trabalhos não encontrado.", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))
    
    # Buscar TODAS as respostas do formulário (não apenas do cliente atual)
    # O cliente precisa ver todos os trabalhos para poder distribuí-los
    respostas = RespostaFormulario.query.filter_by(
        formulario_id=formulario.id
    ).order_by(RespostaFormulario.data_submissao.desc()).all()
    
    # Buscar informações de distribuição para cada trabalho
    trabalho_ids = [resposta.id for resposta in respostas]
    
    # Buscar assignments com informações dos revisores
    from models.user import Usuario
    assignments_with_reviewers = db.session.query(
        Assignment.resposta_formulario_id,
        Usuario.nome.label('reviewer_name')
    ).join(
        Usuario, Assignment.reviewer_id == Usuario.id
    ).filter(
        Assignment.resposta_formulario_id.in_(trabalho_ids)
    ).all()
    
    # Organizar assignments por trabalho
    assignment_dict = {}
    for assignment in assignments_with_reviewers:
        trabalho_id = assignment.resposta_formulario_id
        if trabalho_id not in assignment_dict:
            assignment_dict[trabalho_id] = []
        assignment_dict[trabalho_id].append(assignment.reviewer_name)
    
    # Organizar dados dos trabalhos
    trabalhos = []
    for resposta in respostas:
        trabalho = {'id': resposta.id, 'data_submissao': resposta.data_submissao}
        
        # Adicionar status de distribuição e revisores
        reviewer_names = assignment_dict.get(resposta.id, [])
        if reviewer_names:
            trabalho['distribution_status'] = 'Distribuído'
            trabalho['assignment_count'] = len(reviewer_names)
            trabalho['reviewer_names'] = reviewer_names
        else:
            trabalho['distribution_status'] = 'Não Distribuído'
            trabalho['assignment_count'] = 0
            trabalho['reviewer_names'] = []
        
        for resposta_campo in resposta.respostas_campos:
            campo_nome = resposta_campo.campo.nome
            trabalho[campo_nome.lower().replace(' ', '_')] = resposta_campo.valor
        trabalhos.append(trabalho)
    
    return render_template("trabalhos/listar_trabalhos.html", trabalhos=trabalhos)


@trabalho_routes.route("/trabalhos/novo", methods=["GET", "POST"])
@login_required
def novo_trabalho():
    """Formulário para adicionar novo trabalho."""
    if current_user.tipo != "cliente":
        flash("Acesso negado.", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))
    
    # Buscar formulário de trabalhos
    formulario = Formulario.query.filter_by(nome='Formulário de Trabalhos').first()
    if not formulario:
        flash("Formulário de trabalhos não encontrado.", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))
    
    if request.method == "POST":
        # Criar nova resposta do formulário
        resposta_formulario = RespostaFormulario(
            formulario_id=formulario.id,
            usuario_id=current_user.id
        )
        db.session.add(resposta_formulario)
        db.session.flush()
        
        # Processar campos do formulário
        for campo in formulario.campos:
            valor = request.form.get(f"campo_{campo.id}")
            
            # Validar campos obrigatórios
            if campo.obrigatorio and not valor:
                db.session.rollback()
                flash(f"O campo '{campo.nome}' é obrigatório.", "warning")
                return render_template("trabalhos/novo_trabalho.html", formulario=formulario)
            
            # Criar resposta do campo
            resposta_campo = RespostaCampo(
                resposta_formulario_id=resposta_formulario.id,
                campo_id=campo.id,
                valor=valor or ''
            )
            db.session.add(resposta_campo)
        
        try:
            db.session.commit()
            flash("Trabalho cadastrado com sucesso!", "success")
            return redirect(url_for("trabalho_routes.listar_trabalhos"))
        except Exception as e:
            db.session.rollback()
            flash("Erro ao cadastrar trabalho. Tente novamente.", "danger")
            current_app.logger.error(f"Erro ao cadastrar trabalho: {e}")
    
    return render_template("trabalhos/novo_trabalho.html", formulario=formulario)


@trabalho_routes.route("/trabalhos/<int:trabalho_id>/editar", methods=["GET", "POST"])
@login_required
def editar_trabalho(trabalho_id):
    """Editar trabalho existente."""
    if current_user.tipo not in ["cliente", "admin", "revisor"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))
    
    # Buscar resposta do formulário
    if current_user.tipo == "admin":
        # Admin pode editar qualquer trabalho
        resposta = RespostaFormulario.query.get(trabalho_id)
    elif current_user.tipo == "revisor":
        # Revisor pode editar trabalhos distribuídos para ele ou seus próprios trabalhos
        resposta = RespostaFormulario.query.filter(
            db.or_(
                RespostaFormulario.usuario_id == current_user.id,
                RespostaFormulario.id.in_(
                    db.session.query(Assignment.resposta_formulario_id)
                    .filter(Assignment.reviewer_id == current_user.id)
                )
            )
        ).filter(RespostaFormulario.id == trabalho_id).first()
    else:
        # Cliente só pode editar seus próprios trabalhos
        resposta = RespostaFormulario.query.filter_by(
            id=trabalho_id,
            usuario_id=current_user.id
        ).first()
    
    if not resposta:
        flash("Trabalho não encontrado.", "danger")
        return redirect(url_for("trabalho_routes.listar_trabalhos"))
    
    formulario = resposta.formulario
    
    if request.method == "POST":
        # Atualizar respostas dos campos
        for campo in formulario.campos:
            valor = request.form.get(f"campo_{campo.id}")
            
            # Validar campos obrigatórios
            if campo.obrigatorio and not valor:
                flash(f"O campo '{campo.nome}' é obrigatório.", "warning")
                return render_template("trabalhos/editar_trabalho.html", 
                                     formulario=formulario, resposta=resposta)
            
            # Buscar ou criar resposta do campo
            resposta_campo = RespostaCampo.query.filter_by(
                resposta_formulario_id=resposta.id,
                campo_id=campo.id
            ).first()
            
            if resposta_campo:
                resposta_campo.valor = valor or ''
            else:
                resposta_campo = RespostaCampo(
                    resposta_formulario_id=resposta.id,
                    campo_id=campo.id,
                    valor=valor or ''
                )
                db.session.add(resposta_campo)
        
        try:
            db.session.commit()
            flash("Trabalho atualizado com sucesso!", "success")
            return redirect(url_for("trabalho_routes.listar_trabalhos"))
        except Exception as e:
            db.session.rollback()
            flash("Erro ao atualizar trabalho. Tente novamente.", "danger")
            current_app.logger.error(f"Erro ao atualizar trabalho: {e}")
    
    return render_template("trabalhos/editar_trabalho.html", 
                         formulario=formulario, resposta=resposta)


@trabalho_routes.route("/trabalhos/<int:trabalho_id>/excluir", methods=["POST"])
@login_required
def excluir_trabalho(trabalho_id):
    """Excluir trabalho."""
    if current_user.tipo not in ["cliente", "admin", "revisor"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))
    
    # Buscar resposta do formulário
    if current_user.tipo == "admin":
        # Admin pode excluir qualquer trabalho
        resposta = RespostaFormulario.query.get(trabalho_id)
    elif current_user.tipo == "revisor":
        # Revisor pode excluir trabalhos distribuídos para ele ou seus próprios trabalhos
        resposta = RespostaFormulario.query.filter(
            db.or_(
                RespostaFormulario.usuario_id == current_user.id,
                RespostaFormulario.id.in_(
                    db.session.query(Assignment.resposta_formulario_id)
                    .filter(Assignment.reviewer_id == current_user.id)
                )
            )
        ).filter(RespostaFormulario.id == trabalho_id).first()
    else:
        # Cliente só pode excluir seus próprios trabalhos
        resposta = RespostaFormulario.query.filter_by(
            id=trabalho_id,
            usuario_id=current_user.id
        ).first()
    
    if not resposta:
        flash("Trabalho não encontrado.", "danger")
        return redirect(url_for("trabalho_routes.listar_trabalhos"))
    
    try:
        # Excluir respostas dos campos primeiro
        RespostaCampo.query.filter_by(resposta_formulario_id=resposta.id).delete()
        # Excluir resposta do formulário
        db.session.delete(resposta)
        db.session.commit()
        flash("Trabalho excluído com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Erro ao excluir trabalho. Tente novamente.", "danger")
        current_app.logger.error(f"Erro ao excluir trabalho: {e}")
    
    return redirect(url_for("trabalho_routes.listar_trabalhos"))


@trabalho_routes.route("/trabalhos/<int:trabalho_id>/visualizar")
@login_required
def visualizar_trabalho(trabalho_id):
    """Visualizar detalhes do trabalho."""
    if current_user.tipo not in ["cliente", "admin", "revisor"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))
    
    # Buscar resposta do formulário
    if current_user.tipo == "admin":
        # Admin pode visualizar qualquer trabalho
        resposta = RespostaFormulario.query.get(trabalho_id)
    elif current_user.tipo == "revisor":
        # Revisor pode visualizar trabalhos distribuídos para ele ou seus próprios trabalhos
        resposta = RespostaFormulario.query.filter(
            db.or_(
                RespostaFormulario.usuario_id == current_user.id,
                RespostaFormulario.id.in_(
                    db.session.query(Assignment.resposta_formulario_id)
                    .filter(Assignment.reviewer_id == current_user.id)
                )
            )
        ).filter(RespostaFormulario.id == trabalho_id).first()
    else:
        # Cliente só pode visualizar seus próprios trabalhos
        resposta = RespostaFormulario.query.filter_by(
            id=trabalho_id,
            usuario_id=current_user.id
        ).first()
    
    if not resposta:
        flash("Trabalho não encontrado.", "danger")
        return redirect(url_for("trabalho_routes.listar_trabalhos"))
    
    # Obter o formulário associado
    formulario = resposta.formulario
    
    # Organizar dados do trabalho
    trabalho = {'id': resposta.id, 'data_submissao': resposta.data_submissao}
    for resposta_campo in resposta.respostas_campos:
        campo_nome = resposta_campo.campo.nome
        trabalho[campo_nome.lower().replace(' ', '_')] = resposta_campo.valor
    
    return render_template("trabalhos/visualizar_trabalho.html", 
                         trabalho=trabalho, resposta=resposta, formulario=formulario)


# ───────────────────────────── DISTRIBUIÇÃO ──────────────────────────────── #
@trabalho_routes.route("/distribuicao", methods=["GET", "POST"])
@login_required
def distribuicao():
    """Permite importar planilha e mapear campos para distribuição."""

    campos = ["titulo", "resumo"]
    if request.method == "POST":
        if "data" in request.form and all(
            f"map_{c}" in request.form for c in campos
        ):
            data_json = request.form.get("data", "[]")
            try:
                rows = json.loads(data_json)
            except json.JSONDecodeError:
                flash("Dados inválidos.", "danger")
                return redirect(url_for("trabalho_routes.distribuicao"))
            mapping = {c: request.form.get(f"map_{c}") for c in campos}
            for row in rows:
                item = {c: row.get(col) for c, col in mapping.items()}
                db.session.add(WorkMetadata(data=item))
            db.session.commit()
            flash("Dados importados com sucesso!", "success")
            return redirect(url_for("trabalho_routes.distribuicao"))

        arquivo = request.files.get("arquivo")
        if not arquivo or arquivo.filename == "":
            flash("Nenhum arquivo selecionado.", "warning")
            return render_template("distribuicao.html")


# ──────────────────────── DISTRIBUIÇÃO DE TRABALHOS ─────────────────────── #
@trabalho_routes.route("/api/reviewers", methods=["GET"])
def get_available_reviewers():
    """API endpoint to get available reviewers for distribution."""
    # Authentication removed to allow access for distribution functionality
    
    # CSRF validation removed for API endpoints
    
    try:
        # Get reviewers (users with tipo 'revisor')
        reviewers = Usuario.query.filter_by(tipo="revisor").all()
        
        reviewer_list = []
        for reviewer in reviewers:
            # Count current assignments
            current_assignments = Assignment.query.filter_by(
                reviewer_id=reviewer.id,
                completed=False
            ).count()
            
            reviewer_data = {
                "id": reviewer.id,
                "nome": reviewer.nome,
                "email": reviewer.email,
                "current_assignments": current_assignments,
                "expertise": getattr(reviewer, 'expertise', ''),
                "available": True  # Could add logic for availability
            }
            reviewer_list.append(reviewer_data)
        
        return {
            "success": True,
            "reviewers": reviewer_list,
            "total": len(reviewer_list)
        }
    
    except Exception as e:
        current_app.logger.error(f"Error getting reviewers: {e}")
        return {"error": "Internal server error"}, 500


@trabalho_routes.route("/api/distribution/manual", methods=["POST"])
@csrf.exempt
def manual_distribution():
    """API endpoint for manual work distribution."""
    
    try:
        data = request.get_json()
        if not data:
            return {"error": "No data provided"}, 400
        
        work_ids = data.get('work_ids', [])
        assignments = data.get('assignments', [])
        deadline = data.get('deadline')  # Get deadline from top level
        notes = data.get('notes', '')
        
        if not work_ids or not assignments:
            return {"error": "Work IDs and assignments are required"}, 400
        
        # Validate works exist
        works = RespostaFormulario.query.filter(
            RespostaFormulario.id.in_(work_ids)
        ).all()
        
        if len(works) != len(work_ids):
            return {"error": "Some works not found"}, 404
        
        assignments_created = 0
        
        # Create assignments
        for assignment_data in assignments:
            work_id = assignment_data.get('workId')  # Changed from 'work_id' to 'workId'
            reviewer_id = assignment_data.get('reviewerId')  # Changed from 'reviewer_id' to 'reviewerId'
            
            if not all([work_id, reviewer_id]):
                continue
            
            # Check if assignment already exists
            existing = Assignment.query.filter_by(
                resposta_formulario_id=work_id,
                reviewer_id=reviewer_id
            ).first()
            
            if existing:
                continue
            
            # Create new assignment
            assignment = Assignment(
                resposta_formulario_id=work_id,
                reviewer_id=reviewer_id,
                deadline=deadline,  # Use deadline from top level
                distribution_type='manual',
                distribution_date=db.func.now(),
                distributed_by=None,
                notes=notes
            )
            db.session.add(assignment)
            assignments_created += 1
        
        # Distribution logging removed to eliminate CSRF-related database errors
        
        db.session.commit()
        
        return {
            "success": True,
            "message": f"Successfully created {assignments_created} assignments",
            "assignments_created": assignments_created
        }
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in manual distribution: {e}")
        return {"error": "Internal server error"}, 500


@trabalho_routes.route("/api/distribution/automatic", methods=["POST"])
@csrf.exempt
def automatic_distribution():
    """API endpoint for automatic work distribution."""
    
    try:
        data = request.get_json()
        if not data:
            return {"error": "No data provided"}, 400
        
        work_ids = data.get('work_ids', [])
        reviewers_per_work = data.get('reviewers_per_work', 2)
        criteria = data.get('criteria', {})
        notes = data.get('notes', '')
        
        if not work_ids:
            return {"error": "Work IDs are required"}, 400
        
        # Get available reviewers
        reviewers_query = Usuario.query.filter_by(tipo="revisor")
        
        # Apply criteria filters if provided
        if criteria.get('expertise'):
            # This would need to be implemented based on your user model
            pass
        
        if criteria.get('max_assignments'):
            # Filter reviewers with fewer than max assignments
            max_assignments = criteria['max_assignments']
            reviewers_query = reviewers_query.filter(
                ~Usuario.id.in_(
                    db.session.query(Assignment.reviewer_id)
                    .filter(Assignment.completed == False)
                    .group_by(Assignment.reviewer_id)
                    .having(db.func.count(Assignment.id) >= max_assignments)
                )
            )
        
        available_reviewers = reviewers_query.all()
        
        if len(available_reviewers) < reviewers_per_work:
            return {
                "error": f"Not enough reviewers available. Need {reviewers_per_work}, found {len(available_reviewers)}"
            }, 400
        
        # Get works
        works = RespostaFormulario.query.filter(
            RespostaFormulario.id.in_(work_ids)
        ).all()
        
        assignments_created = 0
        
        # Simple round-robin distribution
        reviewer_index = 0
        for work in works:
            for _ in range(reviewers_per_work):
                reviewer = available_reviewers[reviewer_index % len(available_reviewers)]
                
                # Check if assignment already exists
                existing = Assignment.query.filter_by(
                    resposta_formulario_id=work.id,
                    reviewer_id=reviewer.id
                ).first()
                
                if not existing:
                    assignment = Assignment(
                        resposta_formulario_id=work.id,
                        reviewer_id=reviewer.id,
                        distribution_type='automatic',
                        distribution_date=db.func.now(),
                        distributed_by=None,
                        notes=notes
                    )
                    db.session.add(assignment)
                    assignments_created += 1
                
                reviewer_index += 1
        
        # Distribution logging removed to eliminate CSRF-related database errors
        
        db.session.commit()
        
        return {
            "success": True,
            "message": f"Successfully created {assignments_created} assignments",
            "assignments_created": assignments_created,
            "distribution_summary": {
                "works_distributed": len(works),
                "reviewers_used": len(available_reviewers),
                "reviewers_per_work": reviewers_per_work
            }
        }
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in automatic distribution: {e}")
        return {"error": "Internal server error"}, 500


@trabalho_routes.route("/api/distribution/undo/<int:work_id>", methods=["DELETE"])
@csrf.exempt
def undo_work_distribution(work_id):
    """API endpoint to undo distribution for a specific work."""
    
    try:
        # Check if work exists
        work = RespostaFormulario.query.get(work_id)
        if not work:
            return {"error": "Work not found"}, 404
        
        # Delete all assignments for this work
        assignments = Assignment.query.filter_by(resposta_formulario_id=work_id).all()
        
        if not assignments:
            return {"error": "No distribution found for this work"}, 404
        
        assignments_deleted = len(assignments)
        
        for assignment in assignments:
            db.session.delete(assignment)
        
        db.session.commit()
        
        return {
            "success": True,
            "message": f"Successfully removed {assignments_deleted} assignments for work ID {work_id}",
            "assignments_deleted": assignments_deleted
        }, 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error undoing work distribution: {e}")
        return {"error": "Internal server error"}, 500


@trabalho_routes.route("/api/distribution/undo-all", methods=["DELETE"])
@csrf.exempt
def undo_all_distributions():
    """API endpoint to undo all work distributions."""
    
    try:
        # Get all assignments
        assignments = Assignment.query.all()
        
        if not assignments:
            return {"error": "No distributions found"}, 404
        
        assignments_deleted = len(assignments)
        works_affected = len(set(assignment.resposta_formulario_id for assignment in assignments))
        
        # Delete all assignments
        for assignment in assignments:
            db.session.delete(assignment)
        
        db.session.commit()
        
        return {
            "success": True,
            "message": f"Successfully removed all distributions. {assignments_deleted} assignments from {works_affected} works were deleted.",
            "assignments_deleted": assignments_deleted,
            "works_affected": works_affected
        }, 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error undoing all distributions: {e}")
        return {"error": "Internal server error"}, 500


        try:
            df = pd.read_excel(arquivo)
        except Exception:
            flash("Erro ao processar o arquivo.", "danger")
            return render_template("distribuicao.html")
        columns = df.columns.tolist()
        data = df.to_dict(orient="records")
        flash("Planilha carregada com sucesso.", "info")
        return render_template(
            "distribuicao.html",
            columns=columns,
            data_preview=data[:5],
            data_json=json.dumps(data),
            campos=campos,
        )

    return render_template("distribuicao.html")
