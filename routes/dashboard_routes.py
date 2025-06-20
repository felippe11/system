from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    abort,
    request,
    current_app,
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
    from flask import current_app, abort

    # Se o login não está desabilitado e o usuário logado não é admin → 403
    if not current_app.config.get("LOGIN_DISABLED") and getattr(current_user, "tipo", None) != "admin":
        abort(403)


    from models import (
        Evento,
        Oficina,
        Inscricao,
        Cliente,
        Configuracao,
        Proposta,
        EventoInscricaoTipo,
        LoteTipoInscricao,
    )
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

    # ------------------------------------------------------------------
    # Dados financeiros gerais
    # ------------------------------------------------------------------
    taxa = float(configuracao.taxa_percentual_inscricao or 0) if configuracao else 0.0

    inscricoes_pagas = (
        Inscricao.query
        .join(Evento)
        .filter(
            Inscricao.status_pagamento == "approved",
            Evento.inscricao_gratuita.is_(False)
        )
        .options(db.joinedload(Inscricao.evento))
        .all()
    )

    financeiro_clientes = {}
    for ins in inscricoes_pagas:
        evento = ins.evento
        if not evento:
            continue
        cliente = evento.cliente
        cinfo = financeiro_clientes.setdefault(
            cliente.id,
            {
                "nome": cliente.nome,
                "receita_total": 0.0,
                "taxas": 0.0,
                "eventos": {},
            },
        )

        preco = 0.0
        if ins.lote_id and evento.habilitar_lotes:
            lti = LoteTipoInscricao.query.filter_by(
                lote_id=ins.lote_id,
                tipo_inscricao_id=ins.tipo_inscricao_id,
            ).first()
            if lti:
                preco = float(lti.preco)
        else:
            eit = EventoInscricaoTipo.query.get(ins.tipo_inscricao_id)
            if eit:
                preco = float(eit.preco)

        einfo = cinfo["eventos"].setdefault(
            evento.id,
            {"nome": evento.nome, "quantidade": 0, "receita": 0.0},
        )
        einfo["quantidade"] += 1
        einfo["receita"] += preco
        cinfo["receita_total"] += preco

    for cinfo in financeiro_clientes.values():
        cinfo["taxas"] = cinfo["receita_total"] * taxa / 100

    total_eventos_receita = sum(len(c["eventos"]) for c in financeiro_clientes.values())
    receita_total = sum(c["receita_total"] for c in financeiro_clientes.values())
    receita_taxas = sum(c["taxas"] for c in financeiro_clientes.values())

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
        finance_clientes=list(financeiro_clientes.values()),
        total_eventos_receita=total_eventos_receita,
        receita_total=receita_total,
        receita_taxas=receita_taxas,
        estado_filter=estado_filter,
        cidade_filter=cidade_filter,
    )


