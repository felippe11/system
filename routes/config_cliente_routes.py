from flask import (
    Blueprint,
    jsonify,
    request,
    redirect,
    url_for,
    flash,
    render_template,
    current_app,
)
from flask_login import login_required, current_user
from extensions import db
from utils import endpoints

from models import (
    ConfiguracaoCliente,
    Configuracao,
    Cliente,
    RevisaoConfig,
    Evento,
    ConfiguracaoEvento,
    Formulario,
)

from datetime import datetime
import logging
import uuid
import secrets
import pandas as pd
from werkzeug.security import generate_password_hash

config_cliente_routes = Blueprint("config_cliente_routes", __name__)


def _get_evento_config(evento_id: int):
    """Retorna a configuracao do evento, criando caso nao exista."""
    config = ConfiguracaoEvento.query.filter_by(evento_id=evento_id).first()
    if not config:
        config = ConfiguracaoEvento(evento_id=evento_id)
        db.session.add(config)
        db.session.commit()
    return config


@config_cliente_routes.route("/toggle_checkin_global_cliente", methods=["POST"])
@login_required
def toggle_checkin_global_cliente():
    data = request.get_json(silent=True) or {}
    evento_id = (
        data.get("evento_id")
        or request.form.get("evento_id", type=int)
        or request.args.get("evento_id", type=int)
    )

    if evento_id:
        evento = Evento.query.get_or_404(evento_id)
        if current_user.tipo == "cliente" and evento.cliente_id != current_user.id:
            return jsonify({"success": False, "message": "Acesso negado!"}), 403

        config_evento = ConfiguracaoEvento.query.filter_by(evento_id=evento_id).first()
        if not config_evento:
            config_evento = ConfiguracaoEvento(evento_id=evento_id)
            db.session.add(config_evento)

        config_evento.permitir_checkin_global = (
            not config_evento.permitir_checkin_global
        )
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "value": config_evento.permitir_checkin_global,
                "message": "Check-in Global do evento atualizado com sucesso!",
            }
        )

    # Caso não tenha evento_id, alterna a configuração do cliente
    cliente_id = current_user.id
    config_cliente = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(
            cliente_id=cliente_id,
            permitir_checkin_global=False,
            habilitar_feedback=False,
            habilitar_certificado_individual=False,
            habilitar_submissao_trabalhos=False,
        )
        db.session.add(config_cliente)
        db.session.commit()

    config_cliente.permitir_checkin_global = not config_cliente.permitir_checkin_global
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "value": config_cliente.permitir_checkin_global,
            "message": "Check-in Global do cliente atualizado com sucesso!",
        }
    )


@config_cliente_routes.route("/toggle_feedback_cliente", methods=["POST"])
@login_required
def toggle_feedback_cliente():
    data = request.get_json(silent=True) or {}
    evento_id = (
        data.get("evento_id")
        or request.form.get("evento_id", type=int)
        or request.args.get("evento_id", type=int)
    )

    if evento_id:
        evento = Evento.query.get_or_404(evento_id)
        if current_user.tipo == "cliente" and evento.cliente_id != current_user.id:
            return jsonify({"success": False, "message": "Acesso negado!"}), 403

        config_evento = ConfiguracaoEvento.query.filter_by(evento_id=evento_id).first()
        if not config_evento:
            config_evento = ConfiguracaoEvento(evento_id=evento_id)
            db.session.add(config_evento)

        config_evento.habilitar_feedback = not config_evento.habilitar_feedback
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "value": config_evento.habilitar_feedback,
                "message": "Feedback do evento atualizado com sucesso!",
            }
        )

    # Se não houver evento_id, alterna a configuração do cliente
    cliente_id = current_user.id
    config_cliente = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(
            cliente_id=cliente_id,
            permitir_checkin_global=False,
            habilitar_feedback=False,
            habilitar_certificado_individual=False,
            habilitar_qrcode_evento_credenciamento=False,
            habilitar_submissao_trabalhos=False,
        )
        db.session.add(config_cliente)
        db.session.commit()

    config_cliente.habilitar_feedback = not config_cliente.habilitar_feedback
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "value": config_cliente.habilitar_feedback,
            "message": "Feedback do cliente atualizado com sucesso!",
        }
    )


@config_cliente_routes.route("/toggle_certificado_cliente", methods=["POST"])
@login_required
def toggle_certificado_cliente():
    data = request.get_json(silent=True) or {}
    evento_id = (
        data.get("evento_id")
        or request.form.get("evento_id", type=int)
        or request.args.get("evento_id", type=int)
    )

    if evento_id:
        evento = Evento.query.get_or_404(evento_id)
        if current_user.tipo == "cliente" and evento.cliente_id != current_user.id:
            return jsonify({"success": False, "message": "Acesso negado!"}), 403

        config_evento = ConfiguracaoEvento.query.filter_by(evento_id=evento_id).first()
        if not config_evento:
            config_evento = ConfiguracaoEvento(evento_id=evento_id)
            db.session.add(config_evento)

        config_evento.habilitar_certificado_individual = (
            not config_evento.habilitar_certificado_individual
        )
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "value": config_evento.habilitar_certificado_individual,
                "message": "Certificado individual do evento atualizado com sucesso!",
            }
        )

    # Caso não haja evento_id, atualiza configuração do cliente
    cliente_id = current_user.id
    config_cliente = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(
            cliente_id=cliente_id,
            permitir_checkin_global=False,
            habilitar_feedback=False,
            habilitar_certificado_individual=False,
            habilitar_submissao_trabalhos=False,
        )
        db.session.add(config_cliente)
        db.session.commit()

    config_cliente.habilitar_certificado_individual = (
        not config_cliente.habilitar_certificado_individual
    )
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "value": config_cliente.habilitar_certificado_individual,
            "message": "Certificado individual do cliente atualizado com sucesso!",
        }
    )


@config_cliente_routes.route("/toggle_certificado_individual", methods=["POST"])
@login_required
def toggle_certificado_individual():
    # Permite apenas clientes (já que esta rota altera uma
    # configuração global de certificado)
    # if current_user.tipo != "cliente":
    # flash("Acesso Autorizado!", "danger")

    config = Configuracao.query.first()
    if not config:
        config = Configuracao(
            permitir_checkin_global=False,
            habilitar_feedback=False,
            habilitar_certificado_individual=False,
        )
        db.session.add(config)
    config.habilitar_certificado_individual = (
        not config.habilitar_certificado_individual
    )
    db.session.commit()

    status = "ativado" if config.habilitar_certificado_individual else "desativado"
    flash(f"Certificado individual {status} com sucesso!", "success")
    return redirect(url_for(endpoints.DASHBOARD_CLIENTE))


@config_cliente_routes.route("/toggle_feedback", methods=["POST"])
@login_required
def toggle_feedback():
    if current_user.tipo != "admin":
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_participante_routes.dashboard_participante"))
    config = Configuracao.query.first()
    if not config:
        config = Configuracao(permitir_checkin_global=False, habilitar_feedback=False)
        db.session.add(config)
    config.habilitar_feedback = not config.habilitar_feedback
    db.session.commit()
    status = "ativado" if config.habilitar_feedback else "desativado"
    flash(f"Feedback global {status} com sucesso!", "success")
    return redirect(url_for(endpoints.DASHBOARD))


@config_cliente_routes.route("/toggle_cliente/<int:cliente_id>")
@login_required
def toggle_cliente(cliente_id):
    if current_user.tipo != "admin":
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))

    cliente = Cliente.query.get_or_404(cliente_id)
    logging.debug("Antes: %s", cliente.ativo)
    cliente.ativo = not cliente.ativo
    logging.debug("Depois: %s", cliente.ativo)

    db.session.commit()
    flash(
        f"Cliente {'ativado' if cliente.ativo else 'desativado'} com sucesso", "success"
    )
    return redirect(url_for(endpoints.DASHBOARD))


@config_cliente_routes.route("/toggle_submissao_trabalhos", methods=["POST"])
@login_required
def toggle_submissao_trabalhos_cliente():
    if current_user.tipo != "cliente":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403

    evento_id = request.args.get("evento_id", type=int) or request.form.get(
        "evento_id", type=int
    )

    if evento_id:
        cfg = ConfiguracaoEvento.query.filter_by(evento_id=evento_id).first()
        if not cfg:
            cfg = ConfiguracaoEvento(evento_id=evento_id)
            db.session.add(cfg)
        cfg.habilitar_submissao_trabalhos = not cfg.habilitar_submissao_trabalhos
        db.session.commit()
        return jsonify({"success": True, "value": cfg.habilitar_submissao_trabalhos})

    config = current_user.configuracao
    if not config:
        config = ConfiguracaoCliente(
            cliente_id=current_user.id, habilitar_submissao_trabalhos=False
        )
        db.session.add(config)
        db.session.commit()

    if not config.habilitar_submissao_trabalhos:
        if not config.formulario_submissao_id:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Defina um formulário de submissão.",
                    }
                ),
                400,
            )
        form = Formulario.query.get(config.formulario_submissao_id)
        if not form or not form.is_submission_form:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Formulário de submissão inválido.",
                    }
                ),
                400,
            )

    config.habilitar_submissao_trabalhos = not config.habilitar_submissao_trabalhos
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "value": config.habilitar_submissao_trabalhos,
            "message": "Configuração de submissão de trabalhos atualizada!",
        }
    )


@config_cliente_routes.route("/toggle_mostrar_taxa", methods=["POST"])
@login_required
def toggle_mostrar_taxa():
    if current_user.tipo != "cliente":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403

    evento_id = request.args.get("evento_id", type=int) or request.form.get(
        "evento_id", type=int
    )

    if evento_id:
        cfg = ConfiguracaoEvento.query.filter_by(evento_id=evento_id).first()
        if not cfg:
            cfg = ConfiguracaoEvento(evento_id=evento_id)
            db.session.add(cfg)
        cfg.mostrar_taxa = not cfg.mostrar_taxa
        db.session.commit()
        return jsonify(
            {
                "success": True,
                "value": cfg.mostrar_taxa,
                "message": "Exibição da taxa atualizada!",
            }
        )

    config = current_user.configuracao
    if not config:
        config = ConfiguracaoCliente(
            cliente_id=current_user.id, habilitar_submissao_trabalhos=False
        )
        db.session.add(config)
        db.session.commit()

    config.mostrar_taxa = not config.mostrar_taxa
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "value": config.mostrar_taxa,
            "message": "Exibição da taxa atualizada!",
        }
    )


@config_cliente_routes.route("/toggle_obrigatorio_nome", methods=["POST"])
@login_required
def toggle_obrigatorio_nome():
    if current_user.tipo != "cliente":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403
    data = request.get_json(silent=True) or {}
    evento_id = data.get("evento_id") or request.form.get("evento_id", type=int)
    if not evento_id:
        return jsonify({"success": False, "message": "Evento não informado"}), 400

    evento = Evento.query.get_or_404(evento_id)
    if evento.cliente_id != current_user.id:
        return jsonify({"success": False, "message": "Acesso negado!"}), 403

    config = _get_evento_config(evento_id)
    config.obrigatorio_nome = not config.obrigatorio_nome
    db.session.commit()
    return jsonify({"success": True, "value": config.obrigatorio_nome})


@config_cliente_routes.route("/toggle_obrigatorio_cpf", methods=["POST"])
@login_required
def toggle_obrigatorio_cpf():
    if current_user.tipo != "cliente":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403
    data = request.get_json(silent=True) or {}
    evento_id = data.get("evento_id") or request.form.get("evento_id", type=int)
    if not evento_id:
        return jsonify({"success": False, "message": "Evento não informado"}), 400

    evento = Evento.query.get_or_404(evento_id)
    if evento.cliente_id != current_user.id:
        return jsonify({"success": False, "message": "Acesso negado!"}), 403

    config = _get_evento_config(evento_id)
    config.obrigatorio_cpf = not config.obrigatorio_cpf
    db.session.commit()
    return jsonify({"success": True, "value": config.obrigatorio_cpf})


@config_cliente_routes.route("/toggle_obrigatorio_email", methods=["POST"])
@login_required
def toggle_obrigatorio_email():
    if current_user.tipo != "cliente":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403
    data = request.get_json(silent=True) or {}
    evento_id = data.get("evento_id") or request.form.get("evento_id", type=int)
    if not evento_id:
        return jsonify({"success": False, "message": "Evento não informado"}), 400

    evento = Evento.query.get_or_404(evento_id)
    if evento.cliente_id != current_user.id:
        return jsonify({"success": False, "message": "Acesso negado!"}), 403

    config = _get_evento_config(evento_id)
    config.obrigatorio_email = not config.obrigatorio_email
    db.session.commit()
    return jsonify({"success": True, "value": config.obrigatorio_email})


@config_cliente_routes.route("/toggle_obrigatorio_senha", methods=["POST"])
@login_required
def toggle_obrigatorio_senha():
    if current_user.tipo != "cliente":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403
    data = request.get_json(silent=True) or {}
    evento_id = data.get("evento_id") or request.form.get("evento_id", type=int)
    if not evento_id:
        return jsonify({"success": False, "message": "Evento não informado"}), 400

    evento = Evento.query.get_or_404(evento_id)
    if evento.cliente_id != current_user.id:
        return jsonify({"success": False, "message": "Acesso negado!"}), 403

    config = _get_evento_config(evento_id)
    config.obrigatorio_senha = not config.obrigatorio_senha
    db.session.commit()
    return jsonify({"success": True, "value": config.obrigatorio_senha})


@config_cliente_routes.route("/toggle_obrigatorio_formacao", methods=["POST"])
@login_required
def toggle_obrigatorio_formacao():
    if current_user.tipo != "cliente":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403
    data = request.get_json(silent=True) or {}
    evento_id = data.get("evento_id") or request.form.get("evento_id", type=int)
    if not evento_id:
        return jsonify({"success": False, "message": "Evento não informado"}), 400

    evento = Evento.query.get_or_404(evento_id)
    if evento.cliente_id != current_user.id:
        return jsonify({"success": False, "message": "Acesso negado!"}), 403

    config = _get_evento_config(evento_id)
    config.obrigatorio_formacao = not config.obrigatorio_formacao
    db.session.commit()
    return jsonify({"success": True, "value": config.obrigatorio_formacao})


@config_cliente_routes.route("/api/configuracao_cliente_atual", methods=["GET"])
@login_required
def configuracao_cliente_atual():
    """Retorna o estado atual das configurações do cliente logado em JSON."""
    cliente_id = current_user.id
    config_cliente = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(
            cliente_id=cliente_id,
            permitir_checkin_global=False,
            habilitar_feedback=False,
            habilitar_certificado_individual=False,
            habilitar_submissao_trabalhos=False,
        )
        db.session.add(config_cliente)
        db.session.commit()

    return jsonify(
        {
            "success": True,
            "permitir_checkin_global": config_cliente.permitir_checkin_global,
            "habilitar_feedback": config_cliente.habilitar_feedback,
            "habilitar_certificado_individual": (
                config_cliente.habilitar_certificado_individual
            ),
            "habilitar_qrcode_evento_credenciamento": (
                config_cliente.habilitar_qrcode_evento_credenciamento
            ),
            "mostrar_taxa": config_cliente.mostrar_taxa,
            "review_model": config_cliente.review_model,
            "num_revisores_min": config_cliente.num_revisores_min,
            "num_revisores_max": config_cliente.num_revisores_max,
            "prazo_parecer_dias": config_cliente.prazo_parecer_dias,
            "habilitar_submissao_trabalhos": (
                config_cliente.habilitar_submissao_trabalhos
            ),
            "obrigatorio_nome": config_cliente.obrigatorio_nome,
            "obrigatorio_cpf": config_cliente.obrigatorio_cpf,
            "obrigatorio_email": config_cliente.obrigatorio_email,
            "obrigatorio_senha": config_cliente.obrigatorio_senha,
            "obrigatorio_formacao": config_cliente.obrigatorio_formacao,
            "allowed_file_types": config_cliente.allowed_file_types,
        }
    )


@config_cliente_routes.route("/toggle_qrcode_evento_credenciamento", methods=["POST"])
@login_required
def toggle_qrcode_evento_credenciamento():
    # Garante que apenas clientes possam alterar
    if current_user.tipo != "cliente":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403

    data = request.get_json(silent=True) or {}
    evento_id = (
        data.get("evento_id")
        or request.form.get("evento_id", type=int)
        or request.args.get("evento_id", type=int)
    )

    if evento_id:
        evento = Evento.query.get_or_404(evento_id)
        if evento.cliente_id != current_user.id:
            return jsonify({"success": False, "message": "Acesso negado!"}), 403

        config_evento = ConfiguracaoEvento.query.filter_by(evento_id=evento_id).first()
        if not config_evento:
            config_evento = ConfiguracaoEvento(evento_id=evento_id)
            db.session.add(config_evento)

        config_evento.habilitar_qrcode_evento_credenciamento = (
            not config_evento.habilitar_qrcode_evento_credenciamento
        )
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "value": config_evento.habilitar_qrcode_evento_credenciamento,
                "message": (
                    "Habilitação de QRCode de credenciamento do evento atualizada!"
                ),
            }
        )

    # Caso não tenha evento_id, aplica configuração global do cliente
    config_cliente = ConfiguracaoCliente.query.filter_by(
        cliente_id=current_user.id
    ).first()
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(
            cliente_id=current_user.id,
            permitir_checkin_global=False,
            habilitar_feedback=False,
            habilitar_certificado_individual=False,
            habilitar_qrcode_evento_credenciamento=False,
            habilitar_submissao_trabalhos=False,
        )
        db.session.add(config_cliente)
        db.session.commit()

    config_cliente.habilitar_qrcode_evento_credenciamento = (
        not config_cliente.habilitar_qrcode_evento_credenciamento
    )
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "value": config_cliente.habilitar_qrcode_evento_credenciamento,
            "message": "Habilitação de QRCode de credenciamento do cliente atualizada!",
        }
    )


@config_cliente_routes.route("/set_review_model", methods=["POST"])
@login_required
def set_review_model():
    if current_user.tipo != "cliente":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403

    data = request.get_json() or {}
    review_model = data.get("review_model")
    if review_model not in ["single", "double"]:
        return jsonify({"success": False, "message": "Modelo inválido"}), 400

    config_cliente = ConfiguracaoCliente.query.filter_by(
        cliente_id=current_user.id
    ).first()
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(cliente_id=current_user.id)
        db.session.add(config_cliente)

    config_cliente.review_model = review_model
    db.session.commit()

    return jsonify({"success": True, "value": config_cliente.review_model})


@config_cliente_routes.route("/set_num_revisores_min", methods=["POST"])
@login_required
def set_num_revisores_min():
    if current_user.tipo != "cliente":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403

    data = request.get_json() or {}
    try:
        value = int(data.get("value"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Valor inválido"}), 400

    config_cliente = ConfiguracaoCliente.query.filter_by(
        cliente_id=current_user.id
    ).first()
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(cliente_id=current_user.id)
        db.session.add(config_cliente)

    config_cliente.num_revisores_min = value
    db.session.commit()

    return jsonify({"success": True, "value": config_cliente.num_revisores_min})


@config_cliente_routes.route("/set_num_revisores_max", methods=["POST"])
@login_required
def set_num_revisores_max():
    if current_user.tipo != "cliente":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403

    data = request.get_json() or {}
    try:
        value = int(data.get("value"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Valor inválido"}), 400

    config_cliente = ConfiguracaoCliente.query.filter_by(
        cliente_id=current_user.id
    ).first()
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(cliente_id=current_user.id)
        db.session.add(config_cliente)

    config_cliente.num_revisores_max = value
    db.session.commit()

    return jsonify({"success": True, "value": config_cliente.num_revisores_max})


@config_cliente_routes.route("/set_prazo_parecer_dias", methods=["POST"])
@login_required
def set_prazo_parecer_dias():
    if current_user.tipo != "cliente":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403

    data = request.get_json() or {}
    try:
        value = int(data.get("value"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Valor inválido"}), 400

    config_cliente = ConfiguracaoCliente.query.filter_by(
        cliente_id=current_user.id
    ).first()
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(cliente_id=current_user.id)
        db.session.add(config_cliente)

    config_cliente.prazo_parecer_dias = value
    db.session.commit()

    return jsonify({"success": True, "value": config_cliente.prazo_parecer_dias})


@config_cliente_routes.route("/set_max_trabalhos_revisor", methods=["POST"])
@login_required
def set_max_trabalhos_revisor():
    """Define o número máximo de trabalhos por revisor."""
    if current_user.tipo != "cliente":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403

    data = request.get_json() or {}
    try:
        value = int(data.get("value"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Valor inválido"}), 400

    config_cliente = ConfiguracaoCliente.query.filter_by(
        cliente_id=current_user.id
    ).first()
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(cliente_id=current_user.id)
        db.session.add(config_cliente)

    config_cliente.max_trabalhos_por_revisor = value
    db.session.commit()

    return jsonify({"success": True, "value": config_cliente.max_trabalhos_por_revisor})


@config_cliente_routes.route("/set_allowed_file_types", methods=["POST"])
@login_required
def set_allowed_file_types():
    if current_user.tipo != "cliente":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403

    data = request.get_json() or {}
    value = data.get("value", "pdf")

    config_cliente = ConfiguracaoCliente.query.filter_by(
        cliente_id=current_user.id
    ).first()
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(cliente_id=current_user.id)
        db.session.add(config_cliente)

    config_cliente.allowed_file_types = value
    db.session.commit()

    return jsonify({"success": True, "value": config_cliente.allowed_file_types})


@config_cliente_routes.route("/set_formulario_submissao", methods=["POST"])
@login_required
def set_formulario_submissao():
    """Define o formulário de submissão para o cliente atual."""
    if current_user.tipo != "cliente":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403

    data = request.get_json() or {}
    formulario_id = data.get("formulario_id")

    config_cliente = ConfiguracaoCliente.query.filter_by(
        cliente_id=current_user.id
    ).first()
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(cliente_id=current_user.id)
        db.session.add(config_cliente)

    config_cliente.formulario_submissao_id = formulario_id
    db.session.commit()

    return jsonify({"success": True, "value": config_cliente.formulario_submissao_id})


@config_cliente_routes.route("/set_limite_eventos/<int:cliente_id>", methods=["POST"])
@login_required
def set_limite_eventos(cliente_id):
    if current_user.tipo != "admin":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403
    value = request.form.get("value") or request.json.get("value")
    try:
        value_int = int(value)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Valor inválido"}), 400
    config = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
    if not config:
        config = ConfiguracaoCliente(cliente_id=cliente_id)
        db.session.add(config)
    config.limite_eventos = value_int
    db.session.commit()
    return jsonify({"success": True, "value": config.limite_eventos})


@config_cliente_routes.route("/set_limite_inscritos/<int:cliente_id>", methods=["POST"])
@login_required
def set_limite_inscritos(cliente_id):
    if current_user.tipo != "admin":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403
    value = request.form.get("value") or request.json.get("value")
    try:
        value_int = int(value)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Valor inválido"}), 400
    config = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
    if not config:
        config = ConfiguracaoCliente(cliente_id=cliente_id)
        db.session.add(config)
    config.limite_inscritos = value_int
    db.session.commit()
    return jsonify({"success": True, "value": config.limite_inscritos})


@config_cliente_routes.route(
    "/set_limite_formularios/<int:cliente_id>", methods=["POST"]
)
@login_required
def set_limite_formularios(cliente_id):
    if current_user.tipo != "admin":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403
    value = request.form.get("value") or request.json.get("value")
    try:
        value_int = int(value)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Valor inválido"}), 400
    config = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
    if not config:
        config = ConfiguracaoCliente(cliente_id=cliente_id)
        db.session.add(config)
    config.limite_formularios = value_int
    db.session.commit()
    return jsonify({"success": True, "value": config.limite_formularios})


@config_cliente_routes.route("/set_limite_revisores/<int:cliente_id>", methods=["POST"])
@login_required
def set_limite_revisores(cliente_id):
    if current_user.tipo != "admin":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403
    value = request.form.get("value") or request.json.get("value")
    try:
        value_int = int(value)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Valor inválido"}), 400
    config = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
    if not config:
        config = ConfiguracaoCliente(cliente_id=cliente_id)
        db.session.add(config)
    config.limite_revisores = value_int
    db.session.commit()
    return jsonify({"success": True, "value": config.limite_revisores})


@config_cliente_routes.route("/set_limite_total_revisores", methods=["POST"])
@login_required
def set_limite_total_revisores():
    """Define o limite total de revisores para o cliente."""
    if current_user.tipo != "cliente":
        return jsonify({"success": False, "message": "Acesso negado!"}), 403
    
    value = request.form.get("value") or request.json.get("value")
    try:
        value_int = int(value)
        if value_int < 0:
            return jsonify({"success": False, "message": "Valor deve ser positivo"}), 400
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Valor inválido"}), 400
    
    config = ConfiguracaoCliente.query.filter_by(cliente_id=current_user.id).first()
    if not config:
        config = ConfiguracaoCliente(cliente_id=current_user.id)
        db.session.add(config)
    
    config.limite_total_revisores = value_int
    db.session.commit()
    
    return jsonify({"success": True, "value": config.limite_total_revisores})


@config_cliente_routes.route("/revisao_config/<int:evento_id>", methods=["POST"])
@login_required
def atualizar_revisao_config(evento_id):
    if current_user.tipo != "cliente":
        return jsonify({"success": False, "message": "Acesso negado"}), 403
    data = request.get_json() or {}
    config = RevisaoConfig.query.filter_by(evento_id=evento_id).first()
    if not config:
        config = RevisaoConfig(evento_id=evento_id)
        db.session.add(config)
    numero = data.get("numero_revisores")
    if numero is not None:
        config.numero_revisores = int(numero)
    prazo = data.get("prazo_revisao")
    if prazo:
        config.prazo_revisao = datetime.fromisoformat(prazo)
    modelo = data.get("modelo_blind")
    if modelo:
        config.modelo_blind = modelo
    db.session.commit()
    return jsonify({"success": True})





@config_cliente_routes.route(
    "/api/configuracao_evento/<int:evento_id>", methods=["GET"]
)
@login_required
def configuracao_evento(evento_id):
    evento = Evento.query.get_or_404(evento_id)
    if evento.cliente_id != current_user.id:
        return jsonify({"success": False, "message": "Acesso negado"}), 403
    config = ConfiguracaoEvento.query.filter_by(evento_id=evento_id).first()
    if not config:
        config = ConfiguracaoEvento(evento_id=evento_id, cliente_id=current_user.id)
        db.session.add(config)
        db.session.commit()
    data = config.to_dict()
    data["success"] = True
    return jsonify(data)


@config_cliente_routes.route(
    "/api/configuracao_evento/<int:evento_id>/<campo>", methods=["POST"]
)
@login_required
def toggle_configuracao_evento(evento_id, campo):
    evento = Evento.query.get_or_404(evento_id)
    if evento.cliente_id != current_user.id:
        return jsonify({"success": False, "message": "Acesso negado"}), 403
    valid = {
        "permitir_checkin_global",
        "habilitar_qrcode_evento_credenciamento",
        "habilitar_feedback",
        "habilitar_certificado_individual",
        "mostrar_taxa",
        "obrigatorio_nome",
        "obrigatorio_cpf",
        "obrigatorio_email",
        "obrigatorio_senha",
        "obrigatorio_formacao",
    }
    if campo not in valid:
        return jsonify({"success": False, "message": "Campo inválido"}), 400
    config = ConfiguracaoEvento.query.filter_by(evento_id=evento_id).first()
    if not config:
        config = ConfiguracaoEvento(evento_id=evento_id, cliente_id=current_user.id)
        db.session.add(config)
    setattr(config, campo, not getattr(config, campo))
    db.session.commit()
    return jsonify({"success": True, "value": getattr(config, campo)})




@config_cliente_routes.route("/config_submissao")
@login_required
def config_submissao():
    """Página de configuração das opções de submissão e revisão"""
    if current_user.tipo != "cliente":
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))

    config_cliente = ConfiguracaoCliente.query.filter_by(
        cliente_id=current_user.id
    ).first()
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(cliente_id=current_user.id)
        db.session.add(config_cliente)
        db.session.commit()

    eventos = Evento.query.filter_by(cliente_id=current_user.id).all()
    formularios = Formulario.query.filter_by(
        cliente_id=current_user.id, is_submission_form=True
    ).all()
    revisao_configs = {
        cfg.evento_id: {
            "numero_revisores": cfg.numero_revisores,
            "prazo_revisao": (
                cfg.prazo_revisao.isoformat() if cfg.prazo_revisao else None
            ),
            "modelo_blind": cfg.modelo_blind,
        }
        for cfg in RevisaoConfig.query.filter(
            RevisaoConfig.evento_id.in_([e.id for e in eventos])
        ).all()
    }

    # Verificar se há um arquivo template para processar automaticamente
    arquivo_template = request.args.get('arquivo')
    evento_id = request.args.get('evento_id')
    auto_import_data = None
    
    if arquivo_template == 'template_trabalhos.xlsx' and evento_id:
        try:
            import os
            template_path = os.path.join(current_app.static_folder, 'templates', 'template_trabalhos.xlsx')
            if os.path.exists(template_path):
                auto_import_data = {
                    'template_file': arquivo_template,
                    'evento_id': evento_id,
                    'template_path': template_path
                }
        except Exception as e:
            flash(f"Erro ao carregar template: {str(e)}", "warning")

    return render_template(
        "config/config_submissao.html",
        config_cliente=config_cliente,
        eventos=eventos,
        formularios=formularios,
        revisao_configs=revisao_configs,
        auto_import_data=auto_import_data,
    )


@config_cliente_routes.route("/get_eventos_cliente", methods=["GET"])
@login_required
def get_eventos_cliente():
    """Buscar eventos para seleção na importação. Admin vê todos, cliente vê apenas os seus."""
    print(f"[DEBUG] get_eventos_cliente chamada - current_user: {current_user}")
    print(f"[DEBUG] current_user.id: {current_user.id}")
    print(f"[DEBUG] current_user.tipo: {current_user.tipo}")
    print(f"[DEBUG] current_user.email: {current_user.email}")
    
    # Permitir acesso para admin e cliente
    if current_user.tipo not in ["cliente", "admin"]:
        print(f"[DEBUG] Acesso negado - tipo de usuário: {current_user.tipo}")
        return jsonify({"success": False, "message": "Acesso negado"}), 403
    
    # Admin vê todos os eventos, cliente vê apenas os seus
    if current_user.tipo == "admin":
        eventos = Evento.query.all()
        print(f"[DEBUG] Admin - Todos os eventos encontrados: {len(eventos)}")
    else:
        # Usar diretamente current_user.id já que current_user é um Cliente
        eventos = Evento.query.filter_by(cliente_id=current_user.id).all()
        print(f"[DEBUG] Cliente - Eventos encontrados: {len(eventos)}")
    
    for evento in eventos:
        print(f"[DEBUG] Evento: ID={evento.id}, Nome={evento.nome}, Cliente_ID={evento.cliente_id}")
    
    eventos_data = [{
        "id": evento.id,
        "nome": evento.nome,
        "descricao": evento.descricao
    } for evento in eventos]
    
    print(f"[DEBUG] Retornando dados: {eventos_data}")
    return jsonify({"success": True, "eventos": eventos_data})


@config_cliente_routes.route("/importar_trabalhos", methods=["POST"])
@login_required
def importar_trabalhos():
    """Proxy endpoint to reuse the generic import logic. Admin pode importar para qualquer evento."""
    if current_user.tipo not in ["cliente", "admin"]:
        return jsonify({"success": False, "message": "Acesso negado"}), 403
    
    # Validar se o evento_id foi fornecido
    evento_id = request.form.get("evento_id", type=int)
    if not evento_id:
        return jsonify({"success": False, "message": "Evento deve ser selecionado"}), 400
    
    # Admin pode acessar qualquer evento, cliente apenas os seus
    if current_user.tipo == "admin":
        evento = Evento.query.filter_by(id=evento_id).first()
    else:
        evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first()
    
    if not evento:
        return jsonify({"success": False, "message": "Evento não encontrado ou acesso negado"}), 403
    
    from .importar_trabalhos_routes import importar_trabalhos as handler
    return handler()

