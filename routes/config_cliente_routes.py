from flask import Blueprint, jsonify, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import ConfiguracaoCliente, Configuracao, Cliente

config_cliente_routes = Blueprint('config_cliente_routes', __name__)

@config_cliente_routes.route("/toggle_checkin_global_cliente", methods=["POST"])
@login_required
def toggle_checkin_global_cliente():
    # Permite apenas clientes acessarem esta rota
    #if current_user.tipo != "cliente":
        #flash("Acesso Autorizado!", "danger")
        
        
    
    # Para clientes, já utiliza o próprio ID
    cliente_id = current_user.id

    from models import ConfiguracaoCliente
    config_cliente = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
    if not config_cliente:
        # Cria uma nova configuração para esse cliente, se não existir
        config_cliente = ConfiguracaoCliente(
            cliente_id=cliente_id,
            permitir_checkin_global=False,
            habilitar_feedback=False,
            habilitar_certificado_individual=False
        )
        db.session.add(config_cliente)
        db.session.commit()

    # Inverte o valor de permitir_checkin_global e persiste
    config_cliente.permitir_checkin_global = not config_cliente.permitir_checkin_global
    db.session.commit()

    return jsonify({
        "success": True,
        "value": config_cliente.permitir_checkin_global,  # True ou False
        "message": "Check-in Global atualizado com sucesso!"
    })


@config_cliente_routes.route("/toggle_feedback_cliente", methods=["POST"])
@login_required
def toggle_feedback_cliente():
    # Permite apenas clientes
    #if current_user.tipo != "cliente":
        #flash("Acesso Autorizado!", "danger")
        
    
    cliente_id = current_user.id
    config_cliente = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(
            cliente_id=cliente_id,
            permitir_checkin_global=False,
            habilitar_feedback=False,
            habilitar_certificado_individual=False,
            habilitar_qrcode_evento_credenciamento=False
        )
        db.session.add(config_cliente)
        db.session.commit()

    config_cliente.habilitar_feedback = not config_cliente.habilitar_feedback
    db.session.commit()

    return jsonify({
        "success": True,
        "value": config_cliente.habilitar_feedback,
        "message": "Feedback atualizado com sucesso!"
    })


@config_cliente_routes.route("/toggle_certificado_cliente", methods=["POST"])
@login_required
def toggle_certificado_cliente():
    # Permite apenas clientes
    #if current_user.tipo != "cliente":
        #flash("Acesso Autorizado!", "danger")
        
    
    cliente_id = current_user.id
    config_cliente = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(
            cliente_id=cliente_id,
            permitir_checkin_global=False,
            habilitar_feedback=False,
            habilitar_certificado_individual=False
        )
        db.session.add(config_cliente)
        db.session.commit()

    config_cliente.habilitar_certificado_individual = not config_cliente.habilitar_certificado_individual
    db.session.commit()

    return jsonify({
        "success": True,
        "value": config_cliente.habilitar_certificado_individual,
        "message": "Certificado Individual atualizado com sucesso!"
    })


@config_cliente_routes.route("/toggle_certificado_individual", methods=["POST"])
@login_required
def toggle_certificado_individual():
    # Permite apenas clientes (já que esta rota altera uma configuração global de certificado)
    #if current_user.tipo != "cliente":
        #flash("Acesso Autorizado!", "danger")
        
    
    config = Configuracao.query.first()
    if not config:
        config = Configuracao(
            permitir_checkin_global=False,
            habilitar_feedback=False,
            habilitar_certificado_individual=False
        )
        db.session.add(config)
    config.habilitar_certificado_individual = not config.habilitar_certificado_individual
    db.session.commit()

    status = "ativado" if config.habilitar_certificado_individual else "desativado"
    flash(f"Certificado individual {status} com sucesso!", "success")
    return redirect(url_for('dashboard_routes.dashboard_cliente'))

@config_cliente_routes.route("/toggle_feedback", methods=["POST"])
@login_required
def toggle_feedback():
    if current_user.tipo != "admin":
        flash("Acesso negado!", "danger")
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))
    config = Configuracao.query.first()
    if not config:
        config = Configuracao(permitir_checkin_global=False, habilitar_feedback=False)
        db.session.add(config)
    config.habilitar_feedback = not config.habilitar_feedback
    db.session.commit()
    flash(f"Feedback global {'ativado' if config.habilitar_feedback else 'desativado'} com sucesso!", "success")
    return redirect(url_for('dashboard_routes.dashboard'))

@config_cliente_routes.route('/toggle_cliente/<int:cliente_id>')
@login_required
def toggle_cliente(cliente_id):
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    cliente = Cliente.query.get_or_404(cliente_id)
    print(f"Antes: {cliente.ativo}")
    cliente.ativo = not cliente.ativo  
    print(f"Depois: {cliente.ativo}")
    

    db.session.commit()
    flash(f"Cliente {'ativado' if cliente.ativo else 'desativado'} com sucesso", "success")
    return redirect(url_for('dashboard_routes.dashboard'))

@config_cliente_routes.route('/toggle_submissao_trabalhos')
@login_required
def toggle_submissao_trabalhos_cliente():
    if current_user.tipo != 'cliente':
        flash("Apenas clientes podem alterar essa configuração.", "warning")
        return redirect(url_for('dashboard_routes.dashboard'))

    config = current_user.configuracao

    if not config:
        flash("Cliente sem configuração associada.", "danger")
        return redirect(url_for('dashboard_routes.dashboard'))

    config.habilitar_submissao_trabalhos = not config.habilitar_submissao_trabalhos
    db.session.commit()
    flash("Configuração de submissão de trabalhos atualizada!", "success")
    return redirect(url_for('dashboard_routes.dashboard'))

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
            habilitar_certificado_individual=False
        )
        db.session.add(config_cliente)
        db.session.commit()

    return jsonify({
        "success": True,
        "permitir_checkin_global": config_cliente.permitir_checkin_global,
        "habilitar_feedback": config_cliente.habilitar_feedback,
        "habilitar_certificado_individual": config_cliente.habilitar_certificado_individual,
        "habilitar_qrcode_evento_credenciamento": config_cliente.habilitar_qrcode_evento_credenciamento
    })

@config_cliente_routes.route("/toggle_qrcode_evento_credenciamento", methods=["POST"])
@login_required
def toggle_qrcode_evento_credenciamento():
    # Garante que apenas o cliente (dono) possa mudar
    if current_user.tipo != 'cliente':
        return jsonify({"success": False, "message": "Acesso negado!"}), 403

    # Busca (ou cria) a configuração desse cliente
    config_cliente = ConfiguracaoCliente.query.filter_by(cliente_id=current_user.id).first()
    if not config_cliente:
        config_cliente = ConfiguracaoCliente(
            cliente_id=current_user.id,
            permitir_checkin_global=False,
            habilitar_feedback=False,
            habilitar_certificado_individual=False,
            habilitar_qrcode_evento_credenciamento=False
        )
        db.session.add(config_cliente)
        db.session.commit()

    # Inverte o valor atual
    config_cliente.habilitar_qrcode_evento_credenciamento = not config_cliente.habilitar_qrcode_evento_credenciamento
    db.session.commit()

    return jsonify({
        "success": True,
        "value": config_cliente.habilitar_qrcode_evento_credenciamento,
        "message": "Habilitação de QRCode de Evento atualizada!"
    })

