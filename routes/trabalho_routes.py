from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from utils.mfa import mfa_required
from extensions import db
from sqlalchemy import or_
from models import TrabalhoCientifico, AvaliacaoTrabalho, AuditLog, Evento
import uuid
import os

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

    # Eventos disponíveis (cliente ou globais) para seleção no formulário
    eventos = Evento.query.filter(
        or_(Evento.cliente_id == current_user.cliente_id, Evento.cliente_id == None)
    ).all()

    if request.method == "POST":
        titulo = request.form.get("titulo")
        resumo = request.form.get("resumo")
        area_tematica = request.form.get("area_tematica")
        arquivo = request.files.get("arquivo_pdf")
        evento_id = request.form.get("evento_id") or getattr(current_user, "evento_id", None)

        # Se nenhum evento foi informado ou está associado ao usuário
        if not evento_id:
            flash("Escolha um evento antes de submeter o trabalho", "danger")
            return redirect(url_for("trabalho_routes.submeter_trabalho"))

        # Validação básica
        if not all([titulo, resumo, area_tematica, arquivo]):
            flash("Todos os campos são obrigatórios!", "warning")
            return redirect(url_for("trabalho_routes.submeter_trabalho"))

        allowed = "pdf"
        if current_user.cliente and current_user.cliente.configuracao:
            allowed = current_user.cliente.configuracao.allowed_file_types or "pdf"
        ext_ok = False
        if allowed:
            exts = [e.strip().lower() for e in allowed.split(',')]
            ext_ok = any(arquivo.filename.lower().endswith(f".{ext}") for ext in exts)
        if not ext_ok:
            flash("Tipo de arquivo não permitido.", "warning")
            return redirect(url_for("trabalho_routes.submeter_trabalho"))

        # Salva o arquivo
        filename = secure_filename(arquivo.filename)
        uploads_dir = current_app.config.get("UPLOAD_FOLDER", "static/uploads/trabalhos")
        os.makedirs(uploads_dir, exist_ok=True)
        caminho_pdf = os.path.join(uploads_dir, filename)
        arquivo.save(caminho_pdf)

        # Registra no banco
        trabalho = TrabalhoCientifico(
            titulo=titulo,
            resumo=resumo,
            area_tematica=area_tematica,
            arquivo_pdf=caminho_pdf,
            usuario_id=current_user.id,
            evento_id=evento_id,
            locator=str(uuid.uuid4()),
        )
        db.session.add(trabalho)
        db.session.commit()
        locator = trabalho.locator

        # Audit log
        db.session.add(
            AuditLog(
                user_id=current_user.id,
                submission_id=trabalho.id,
                event_type="submission",
            )
        )
        db.session.commit()

        flash(
            f"Trabalho submetido com sucesso! Localizador: {locator}",
            "success",
        )
        return redirect(url_for("trabalho_routes.meus_trabalhos"))

    return render_template("submeter_trabalho.html", eventos=eventos)


# ──────────────────────────────── AVALIAÇÃO ──────────────────────────────── #
@trabalho_routes.route("/avaliar_trabalhos")
@login_required
@mfa_required
def avaliar_trabalhos():
    """Lista trabalhos pendentes para avaliação."""
    if current_user.tipo != "cliente" and not current_user.is_superuser():
        flash("Apenas administradores ou avaliadores têm acesso.", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    trabalhos = TrabalhoCientifico.query.filter(
        TrabalhoCientifico.status != "aceito"
    ).all()
    return render_template("avaliar_trabalhos.html", trabalhos=trabalhos)


@trabalho_routes.route("/avaliar_trabalho/<int:trabalho_id>", methods=["GET", "POST"])
@login_required
@mfa_required
def avaliar_trabalho(trabalho_id):
    """Tela de avaliação individual de um trabalho."""
    trabalho = TrabalhoCientifico.query.get_or_404(trabalho_id)

    if request.method == "POST":
        estrelas = request.form.get("estrelas")
        nota = request.form.get("nota")
        conceito = request.form.get("conceito")
        comentario = request.form.get("comentario")

        avaliacao = AvaliacaoTrabalho(
            trabalho_id=trabalho.id,
            avaliador_id=current_user.id,
            estrelas=int(estrelas) if estrelas else None,
            nota=float(nota) if nota else None,
            conceito=conceito,
            comentario=comentario,
        )
        db.session.add(avaliacao)

        trabalho.status = "avaliado"
        db.session.commit()

        # Audit log
        db.session.add(
            AuditLog(
                user_id=current_user.id,
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

    trabalhos = TrabalhoCientifico.query.filter_by(usuario_id=current_user.id).all()
    return render_template("meus_trabalhos.html", trabalhos=trabalhos)
