from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from utils.mfa import mfa_required
from extensions import db
from models import (
    Submission,
    AvaliacaoTrabalho,
    AuditLog,
    Evento,
    Usuario,
    Formulario,
    RespostaFormulario,
    RespostaCampo,
)
import uuid
import os
import secrets

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
    if current_user.tipo != "participante":
        flash("Apenas participantes podem submeter trabalhos.", "danger")
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

        raw_code = secrets.token_urlsafe(8)[:8]
        code_hash = generate_password_hash(raw_code)
        submission = Submission(
            title=titulo,
            abstract=None,
            content=None,
            file_path=arquivo_pdf,
            author_id=current_user.id,
            evento_id=evento_id,
            locator=str(uuid.uuid4()),
            code_hash=code_hash,
        )
        db.session.add(submission)
        db.session.flush()

        usuario = Usuario.query.get(getattr(current_user, "id", None))
        uid = usuario.id if usuario else None
        db.session.add(
            AuditLog(user_id=uid, submission_id=submission.id, event_type="submission")
        )

        db.session.commit()

        flash(
            f"Trabalho submetido com sucesso! Localizador: {submission.locator} - Código: {raw_code}",
            "success",
        )
        return redirect(url_for("trabalho_routes.meus_trabalhos"))

    return render_template("submeter_trabalho.html", formulario=formulario)


# ──────────────────────────────── AVALIAÇÃO ──────────────────────────────── #
@trabalho_routes.route("/avaliar_trabalhos")
@login_required
@mfa_required
def avaliar_trabalhos():
    """Lista trabalhos pendentes para avaliação."""
    if current_user.tipo != "cliente" and not current_user.is_superuser():
        flash("Apenas administradores ou avaliadores têm acesso.", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    trabalhos = Submission.query.filter(
        Submission.status != "aceito"
    ).all()
    return render_template("avaliar_trabalhos.html", trabalhos=trabalhos)


@trabalho_routes.route("/avaliar_trabalho/<int:trabalho_id>", methods=["GET", "POST"])
@login_required
@mfa_required
def avaliar_trabalho(trabalho_id):
    """Tela de avaliação individual de um trabalho."""

    if current_user.tipo != "cliente" and not current_user.is_superuser():
        flash("Apenas administradores ou avaliadores têm acesso.", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    trabalho = Submission.query.get_or_404(trabalho_id)

    if request.method == "POST":
        estrelas = request.form.get("estrelas")
        nota = request.form.get("nota")
        conceito = request.form.get("conceito")
        comentario = request.form.get("comentario")

        # Validações
        try:
            estrelas_val = int(estrelas)
        except (TypeError, ValueError):
            flash("Número de estrelas inválido.", "danger")
            return redirect(url_for("trabalho_routes.avaliar_trabalho", trabalho_id=trabalho_id))
        if not 1 <= estrelas_val <= 5:
            flash("Número de estrelas deve estar entre 1 e 5.", "danger")
            return redirect(url_for("trabalho_routes.avaliar_trabalho", trabalho_id=trabalho_id))

        try:
            nota_val = float(nota)
        except (TypeError, ValueError):
            flash("Nota inválida.", "danger")
            return redirect(url_for("trabalho_routes.avaliar_trabalho", trabalho_id=trabalho_id))
        if not 0 <= nota_val <= 10:
            flash("Nota deve estar entre 0 e 10.", "danger")
            return redirect(url_for("trabalho_routes.avaliar_trabalho", trabalho_id=trabalho_id))

        avaliacao = AvaliacaoTrabalho(
            trabalho_id=trabalho.id,
            avaliador_id=current_user.id,
            estrelas=estrelas_val,
            nota=nota_val,
            conceito=conceito,
            comentario=comentario,
        )
        db.session.add(avaliacao)

        trabalho.status = "avaliado"
        db.session.commit()

        # Audit log
        usuario = Usuario.query.get(getattr(current_user, "id", None))
        uid = usuario.id if usuario else None  # salva log mesmo sem usuário
        db.session.add(
            AuditLog(
                user_id=uid,
                submission_id=trabalho.id,
                event_type="decision",
            )
        )
        db.session.commit()

        flash("Avaliação registrada!", "success")
        return redirect(url_for("trabalho_routes.avaliar_trabalhos"))

    return render_template("avaliar_trabalho.html", trabalho=trabalho)


# ──────────────────────────────── MEUS TRABALHOS ─────────────────────────── #
@trabalho_routes.route("/meus_trabalhos")
@login_required
def meus_trabalhos():
    """Lista trabalhos do participante logado."""
    if current_user.tipo != "participante":
        return redirect(url_for("dashboard_participante_routes.dashboard_participante"))

    trabalhos = Submission.query.filter_by(author_id=current_user.id).all()
    return render_template("meus_trabalhos.html", trabalhos=trabalhos)
