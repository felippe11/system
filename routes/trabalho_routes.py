import json
import os
import uuid

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
from flask_login import current_user, login_required
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from extensions import db
from models import (
    AuditLog,
    Evento,
    Formulario,
    RespostaCampo,
    RespostaFormulario,
    Submission,
    Usuario,
    WorkMetadata,
)
from models.review import Assignment
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
        return redirect(url_for("dashboard_routes.dashboard"))

    config = current_user.cliente.configuracao if current_user.cliente else None
    formulario = None
    if config and config.habilitar_submissao_trabalhos:
        formulario = config.formulario_submissao
        if not formulario or not formulario.is_submission_form:
            flash("Formulário de submissão inválido.", "danger")
            return redirect(url_for("dashboard_routes.dashboard"))
        if (
            formulario.eventos
            and current_user.evento_id not in [ev.id for ev in formulario.eventos]
        ):
            flash("Formulário indisponível para seu evento.", "danger")
            return redirect(url_for("dashboard_routes.dashboard"))

    if not formulario:
        flash("Submissão de trabalhos desabilitada.", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

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
            url_for("dashboard_routes.dashboard")
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
