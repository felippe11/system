from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    abort,
    request,
)
from flask_login import login_required, current_user

dashboard_routes = Blueprint(
    'dashboard_routes',
    __name__,
    template_folder="../templates/dashboard"
)
# ────────────────────────────────────────
# DASHBOARD GERAL (admin, cliente, participante, professor)
# ────────────────────────────────────────
@dashboard_routes.route('/dashboard')
@login_required
def dashboard():
    tipo = getattr(current_user, "tipo", None)

    if tipo == "admin":
        return redirect(url_for("dashboard_routes.dashboard_admin"))

    elif tipo == "cliente":
        return redirect(url_for("dashboard_routes.dashboard_cliente"))

    elif tipo == "participante":
        return redirect(
            url_for("dashboard_participante_routes.dashboard_participante")
        )

    elif tipo == "ministrante":
        return redirect(
            url_for("dashboard_ministrante_routes.dashboard_ministrante")
        )

    elif tipo == "professor":
        return redirect(url_for("dashboard_professor.dashboard_professor"))

    abort(403)

@dashboard_routes.route("/dashboard_admin")
@login_required
def dashboard_admin():
    """Renderiza o dashboard do administrador com estatísticas do sistema."""
    if current_user.tipo != "admin":
        abort(403)

    from models import Evento, Oficina, Inscricao, Cliente, Configuracao, Proposta
    from extensions import db

    total_eventos = Evento.query.count()
    total_oficinas = Oficina.query.count()
    total_inscricoes = Inscricao.query.count()

    # Calculo de vagas oferecidas considerando o tipo de inscrição
    oficinas = Oficina.query.options(db.joinedload(Oficina.inscritos)).all()
    total_vagas = 0
    for of in oficinas:
        if of.tipo_inscricao == "com_inscricao_com_limite":
            total_vagas += of.vagas
        elif of.tipo_inscricao == "com_inscricao_sem_limite":
            total_vagas += len(of.inscritos)

    percentual_adesao = (total_inscricoes / total_vagas) * 100 if total_vagas > 0 else 0

    clientes = Cliente.query.all()
    propostas = Proposta.query.order_by(Proposta.data_criacao.desc()).all()
    configuracao = Configuracao.query.first()

    estado_filter = request.args.get("estado")
    cidade_filter = request.args.get("cidade")

    return render_template(
        "dashboard/dashboard_admin.html",
        total_eventos=total_eventos,
        total_oficinas=total_oficinas,
        total_inscricoes=total_inscricoes,
        percentual_adesao=percentual_adesao,
        clientes=clientes,
        propostas=propostas,
        configuracao=configuracao,
        estado_filter=estado_filter,
        cidade_filter=cidade_filter,
    )


