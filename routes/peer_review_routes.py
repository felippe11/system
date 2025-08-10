from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from flask_login import login_required, current_user
from extensions import db

from models import (
    TrabalhoCientifico,
    Usuario,
    Review,
    RevisaoConfig,
    Submission,
    Assignment,
    ConfiguracaoCliente,
    AuditLog,
    Evento,
    ReviewerApplication,
)

import uuid
from datetime import datetime, timedelta


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
    if current_user.tipo not in ("cliente", "admin", "superadmin"):
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))
    submissions = Submission.query.all()
    return render_template(
        "peer_review/submission_control.html", submissions=submissions
    )


# ---------------------------------------------------------------------------
# Atribuição manual de revisores (via AJAX)
# ---------------------------------------------------------------------------
@peer_review_routes.route("/assign_reviews", methods=["POST"])
@login_required
def assign_reviews():
    if current_user.tipo not in ("cliente", "admin", "superadmin"):
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    data = request.get_json()
    if not data:
        return {"success": False}, 400

    for trabalho_id, reviewers in data.items():
        trabalho = TrabalhoCientifico.query.get(trabalho_id)
        if not trabalho:
            continue

        for reviewer_id in reviewers:
            # Cria Review + Assignment --------------------------------------
            rev = Review(
                submission_id=trabalho.id,
                reviewer_id=reviewer_id,
                access_code=str(uuid.uuid4())[:8],
            )
            db.session.add(rev)

            evento = Evento.query.get(trabalho.evento_id)
            cliente_id = evento.cliente_id if evento else None
            config = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
            prazo_dias = config.prazo_parecer_dias if config else 14

            assignment = Assignment(
                submission_id=trabalho.id,
                reviewer_id=reviewer_id,
                deadline=datetime.utcnow() + timedelta(days=prazo_dias),
            )
            db.session.add(assignment)

            # Log -----------------------------------------------------------
            db.session.add(
                AuditLog(
                    user_id=current_user.id,
                    submission_id=trabalho.id,
                    event_type="assignment",
                )
            )

    db.session.commit()
    return {"success": True}


# ---------------------------------------------------------------------------
# Atribuição automática de revisores com base na área
# ---------------------------------------------------------------------------
@peer_review_routes.route("/auto_assign/<int:evento_id>", methods=["POST"])
@login_required
def auto_assign(evento_id):
    if current_user.tipo not in ("cliente", "admin", "superadmin"):
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    config = RevisaoConfig.query.filter_by(evento_id=evento_id).first()
    if not config:
        return {"success": False, "message": "Configuração não encontrada"}, 400

    trabalhos = TrabalhoCientifico.query.filter_by(evento_id=evento_id).all()
    revisores = Usuario.query.filter_by(tipo="professor").all()

    # Agrupa revisores por formação/área -----------------------------------
    area_map = {}
    for r in revisores:
        area_map.setdefault(r.formacao, []).append(r)

    for t in trabalhos:
        revisores_area = area_map.get(t.area_tematica, revisores)
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
                    user_id=current_user.id,
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
    """Cria uma revisão única para um trabalho e um revisor."""
    if current_user.tipo not in ("cliente", "admin", "superadmin"):
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    data = request.get_json(silent=True) or {}
    trabalho_id = request.form.get("trabalho_id") or data.get("trabalho_id")
    reviewer_id = request.form.get("reviewer_id") or data.get("reviewer_id")

    if not trabalho_id or not reviewer_id:
        return {"success": False, "message": "dados insuficientes"}, 400

    rev = Review(
        submission_id=int(trabalho_id),
        reviewer_id=int(reviewer_id),
        locator=str(uuid.uuid4()),
        access_code=str(uuid.uuid4())[:8],
    )
    db.session.add(rev)
    db.session.commit()

    if request.is_json:
        return {"success": True, "locator": rev.locator, "access_code": rev.access_code}

    flash(f"Código do revisor: {rev.access_code}", "success")
    return redirect(
        request.referrer or url_for("peer_review_routes.editor_reviews", evento_id=trabalho_id)
    )


# ---------------------------------------------------------------------------
# Formulário de revisão (público via locator)
# ---------------------------------------------------------------------------
@peer_review_routes.route("/review/<locator>", methods=["GET", "POST"])
def review_form(locator):
    review = Review.query.filter_by(locator=locator).first_or_404()

    if request.method == "GET" and review.started_at is None:
        review.started_at = datetime.utcnow()
        db.session.commit()

    if request.method == "POST":
        codigo = request.form.get("codigo")
        if codigo != review.access_code:
            flash("Código incorreto!", "danger")
            return render_template("peer_review/review_form.html", review=review)

        try:
            nota = int(request.form.get("nota"))
            if nota not in range(1, 6):
                raise ValueError
        except (TypeError, ValueError):
            flash("Nota inválida (use 1–5).", "danger")
            return render_template("peer_review/review_form.html", review=review)
        review.note = nota
        review.comments = request.form.get("comentarios")
        review.blind_type = "nome" if request.form.get("mostrar_nome") == "on" else "anonimo"
        review.finished_at = datetime.utcnow()
        if review.started_at:
            review.duration_seconds = int(
                (review.finished_at - review.started_at).total_seconds()
            )
        review.submitted_at = review.finished_at
        db.session.commit()

        flash("Revisão enviada!", "success")
        return redirect(url_for("peer_review_routes.review_form", locator=locator))

    return render_template("peer_review/review_form.html", review=review)


# ---------------------------------------------------------------------------
# Dashboards (autor | revisor | editor)
# ---------------------------------------------------------------------------
@peer_review_routes.route("/dashboard/author_reviews")
@login_required
def author_reviews():
    trabalhos = TrabalhoCientifico.query.filter_by(usuario_id=current_user.id).all()
    return render_template("peer_review/dashboard_author.html", trabalhos=trabalhos)


@peer_review_routes.route("/dashboard/reviewer_reviews")
@login_required
def reviewer_reviews():
    assignments = Assignment.query.filter_by(reviewer_id=current_user.id).all()
    config = RevisaoConfig.query.first()
    return render_template(
        "peer_review/dashboard_reviewer.html", assignments=assignments, config=config
    )


@peer_review_routes.route("/dashboard/editor_reviews/<int:evento_id>")
@login_required
def editor_reviews(evento_id):
    if current_user.tipo not in ("cliente", "admin", "superadmin"):
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    trabalhos = TrabalhoCientifico.query.filter_by(evento_id=evento_id).all()
    return render_template("peer_review/dashboard_editor.html", trabalhos=trabalhos)


# ------------------------- ROTAS FLAT PARA SPAS ---------------------------
@peer_review_routes.route("/peer-review/author")
def author_dashboard():
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
            url_for(
                "peer_review_routes.reviewer_dashboard", locator=locator, code=code
            )
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
                senha=generate_password_hash(senha),
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
