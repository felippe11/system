from flask import Blueprint, request, redirect, url_for, flash, session, abort
from flask_login import login_user, login_required, current_user
from extensions import db
from models import Inscricao, Configuracao, ConfiguracaoCliente
from models.user import Cliente
import os
from utils import endpoints

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
    # Permitir tanto superadmin quanto cliente
    if current_user.tipo not in ["cliente", "superadmin", "admin"]:
        abort(403)
        
    valor = request.form.get("taxa_percentual", "0").replace(",", ".")
    cliente_id = request.form.get("cliente_id")
    taxa_diferenciada = request.form.get("taxa_diferenciada", "").replace(",", ".")
    remover_taxa = request.form.get("remover_taxa") == "1"
    
    try:
        perc = round(Decimal(valor), 2)          # 0–100
        assert 0 <= perc <= 100
    except:
        flash("Percentual da taxa geral inválido", "danger")
        return redirect(request.referrer or url_for(endpoints.DASHBOARD_ADMIN))

    cfg = Configuracao.query.first()
    if not cfg:
        cfg = Configuracao()
        db.session.add(cfg)

    # Atualiza a taxa geral do sistema
    cfg.taxa_percentual_inscricao = perc
    
    # Se um cliente foi selecionado
    if cliente_id:
        cliente_id = int(cliente_id)
        config_cliente = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
          # Verifica se é para remover a taxa diferenciada
        if remover_taxa:
            if config_cliente:
                config_cliente.taxa_diferenciada = None
                flash(f"Taxa diferenciada removida. O cliente agora usa a taxa geral do sistema.", "success")
            else:
                flash(f"Este cliente já está usando a taxa geral do sistema.", "info")
                
        # Caso contrário, se uma taxa diferenciada foi informada
        elif taxa_diferenciada:
            try:
                perc_cliente = round(Decimal(taxa_diferenciada), 2)
                assert 0 <= perc_cliente <= 100
                
                # Verifica se a taxa diferenciada é menor que a taxa geral
                if perc_cliente >= perc:
                    flash("A taxa diferenciada deve ser menor que a taxa geral do sistema", "danger")
                    return redirect(request.referrer or url_for(endpoints.DASHBOARD_ADMIN))
                    
                # Busca a configuração do cliente ou cria uma nova
                if not config_cliente:
                    config_cliente = ConfiguracaoCliente(cliente_id=cliente_id)
                    db.session.add(config_cliente)
                    
                # Atualiza a taxa diferenciada do cliente
                config_cliente.taxa_diferenciada = perc_cliente
                flash(f"Taxa diferenciada para cliente ID {cliente_id} salva com sucesso!", "success")
            except:
                flash("Erro ao salvar a taxa diferenciada. Verifique os valores informados.", "danger")
                return redirect(request.referrer or url_for(endpoints.DASHBOARD_ADMIN))
    
    db.session.commit()
    flash("Percentual geral salvo!", "success")
    return redirect(request.referrer or url_for(endpoints.DASHBOARD_ADMIN))
