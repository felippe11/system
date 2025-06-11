from flask import Blueprint, request, redirect, url_for, flash, session, abort
from flask_login import login_user, login_required, current_user
from extensions import db
from models import Inscricao, Configuracao
import os

from services.mp_service import get_sdk
from decimal import Decimal

mercadopago_routes = Blueprint('mercadopago_routes', __name__)


@mercadopago_routes.route("/pagamento_sucesso")
def pagamento_sucesso():
    payment_id        = request.args.get("payment_id")
    external_ref      = request.args.get("external_reference")  # id da inscrição
    inscricao         = Inscricao.query.get_or_404(external_ref)

    # 1) marca como aprovado, se ainda não estiver
    if inscricao.status_pagamento != "approved":
        inscricao.status_pagamento = "approved"
        db.session.commit()

    # 2) faz login do usuário automaticamente
    login_user(inscricao.usuario)
    session['user_type'] = 'participante'

    flash("Pagamento aprovado! Bem‑vindo(a) 😉", "success")
    return redirect(url_for('dashboard_participante_routes.dashboard_participante'))



@mercadopago_routes.route("/pagamento_pendente")
def pagamento_pendente():
    flash("Pagamento pendente. Você poderá concluir mais tarde.", "warning")
    return redirect(url_for("auth_routes.login"))


@mercadopago_routes.route("/pagamento_falha")
def pagamento_falha():
    flash("Pagamento não foi concluído. Tente novamente.", "danger")
    return redirect(url_for("auth_routes.login"))


@mercadopago_routes.route("/webhook_mp", methods=["POST"])
def webhook_mp():
    data = request.get_json(silent=True) or {}
    if data.get("type") == "payment":
        sdk = get_sdk()
        if not sdk:
            return "", 200
        pay = sdk.payment().get(data["data"]["id"])["response"]

        if pay["status"] == "approved":
            ref = pay["external_reference"]
            insc = Inscricao.query.get(int(ref))
            if insc and insc.status_pagamento != "approved":
                insc.status_pagamento = "approved"
                db.session.commit()
    return "", 200  

@mercadopago_routes.route("/atualizar_taxa", methods=["POST"])
@login_required
def atualizar_taxa():
    if current_user.tipo != "cliente":
        abort(403)

    valor = request.form.get("taxa_percentual", "0").replace(",", ".")
    try:
        perc = round(Decimal(valor), 2)          # 0–100
        assert 0 <= perc <= 100
    except:
        flash("Percentual inválido", "danger")
        return redirect(request.referrer or url_for('dashboard_routes.dashboard_admin'))

    cfg = Configuracao.query.first()
    if not cfg:
        cfg = Configuracao()
        db.session.add(cfg)

    cfg.taxa_percentual_inscricao = perc
    db.session.commit()
    flash("Percentual salvo!", "success")
    return redirect(request.referrer or url_for('dashboard_routes.dashboard_admin'))
