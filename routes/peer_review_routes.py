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
    RevisorCandidatura,
    RevisorProcess,
)
from services.review_notification_service import notify_reviewer


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
    if current_user.tipo not in ("cliente", "admin", "superadmin"):
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))
    submissions = Submission.query.all()
    reviewers = Usuario.query.filter_by(tipo="professor").all()
    config = ConfiguracaoCliente.query.filter_by(
        cliente_id=getattr(current_user, "id", None)
    ).first()
    return render_template(
        "peer_review/submission_control.html",
        submissions=submissions,
        reviewers=reviewers,
        config=config,
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

    usuario = Usuario.query.get(getattr(current_user, "id", None))
    uid = usuario.id if usuario else None  # salva log mesmo sem usuário

    data = request.get_json()
    if not data:
        return {"success": False}, 400

    for submission_id, reviewers in data.items():
        sub = Submission.query.get(submission_id)
        if not sub:
            continue


        for reviewer_id in reviewers:
            # Cria Review + Assignment --------------------------------------
            rev = Review(
                submission_id=trabalho.id,
                reviewer_id=reviewer_id,
                access_code=str(uuid.uuid4())[:8],
            )
            db.session.add(rev)
            db.session.flush()
            notify_reviewer(rev)


            evento = Evento.query.get(sub.evento_id)
            cliente_id = evento.cliente_id if evento else None
            config = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
            prazo_dias = config.prazo_parecer_dias if config else 14

            assignment = Assignment(
                submission_id=sub.id,
                reviewer_id=reviewer_id,
                deadline=datetime.utcnow() + timedelta(days=prazo_dias),
            )
            db.session.add(assignment)

            # Log -----------------------------------------------------------
            db.session.add(
                AuditLog(
                    user_id=uid,
                    submission_id=sub.id,
                    event_type="assignment",
                )
            )

    db.session.commit()
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

    submissions = Submission.query.filter(
        Submission.evento_id.in_(evento_ids)
    ).all()
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
    if current_user.tipo not in ("cliente", "admin", "superadmin"):
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    usuario = Usuario.query.get(getattr(current_user, "id", None))
    uid = usuario.id if usuario else None  # salva log mesmo sem usuário

    config = RevisaoConfig.query.filter_by(evento_id=evento_id).first()
    if not config:
        return {"success": False, "message": "Configuração não encontrada"}, 400

    trabalhos = Submission.query.filter_by(evento_id=evento_id).all()
    revisores = Usuario.query.filter_by(tipo="professor").all()

    # Agrupa revisores por formação/área -----------------------------------
    area_map = {}
    for r in revisores:
        area_map.setdefault(r.formacao, []).append(r)

    for t in trabalhos:
        revisores_area = area_map.get(getattr(t, "area_tematica", None), revisores)
        selecionados = revisores_area[: config.numero_revisores]

        for reviewer in selecionados:
            rev = Review(
                submission_id=t.id,
                reviewer_id=reviewer.id,
                access_code=str(uuid.uuid4())[:8],
            )
            db.session.add(rev)
            db.session.flush()
            notify_reviewer(rev)

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
    db.session.flush()
    notify_reviewer(rev)
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
    barema = EventoBarema.query.filter_by(
        evento_id=review.submission.evento_id
    ).first()


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

    return render_template(
        "peer_review/review_form.html", review=review, barema=barema
    )



# ---------------------------------------------------------------------------
# Dashboards (autor | revisor | editor)
# ---------------------------------------------------------------------------
@peer_review_routes.route("/dashboard/author_reviews")
@login_required
def author_reviews():
    trabalhos = Submission.query.filter_by(author_id=current_user.id).all()
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
        Submission.query.join(Evento).filter(
            Evento.cliente_id == getattr(current_user, "id", None)
        ).all()
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
