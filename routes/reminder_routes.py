from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from models import (
    LembreteOficina, 
    LembreteEnvio, 
    TipoLembrete, 
    StatusLembrete,
    Oficina,
    Usuario,
    Cliente,
    db
)
from services.email_service import EmailService
import json
import logging

logger = logging.getLogger(__name__)

reminder_routes = Blueprint('reminder_routes', __name__)


@reminder_routes.route('/lembretes')
@login_required
def listar_lembretes():
    """Lista todos os lembretes do cliente."""
    cliente_id = current_user.cliente_id
    
    # Buscar lembretes do cliente
    lembretes = LembreteOficina.query.filter_by(cliente_id=cliente_id).order_by(
        LembreteOficina.data_criacao.desc()
    ).all()
    
    return render_template('lembretes/listar.html', lembretes=lembretes)


@reminder_routes.route('/lembretes/criar', methods=['GET', 'POST'])
@login_required
def criar_lembrete():
    """Cria um novo lembrete."""
    if request.method == 'GET':
        cliente_id = current_user.cliente_id
        
        # Buscar oficinas do cliente
        oficinas = Oficina.query.filter_by(cliente_id=cliente_id).order_by(
            Oficina.titulo.asc()
        ).all()
        
        # Buscar usuários do cliente
        usuarios = Usuario.query.filter_by(cliente_id=cliente_id).order_by(
            Usuario.nome.asc()
        ).all()
        
        return render_template('lembretes/criar.html', oficinas=oficinas, usuarios=usuarios)
    
    # POST - Criar lembrete
    try:
        data = request.get_json()
        
        lembrete = LembreteOficina(
            cliente_id=current_user.cliente_id,
            titulo=data['titulo'],
            mensagem=data['mensagem'],
            tipo=TipoLembrete(data['tipo']),
            enviar_todas_oficinas=data.get('enviar_todas_oficinas', False),
            oficina_ids=json.dumps(data.get('oficina_ids', [])),
            usuario_ids=json.dumps(data.get('usuario_ids', []))
        )
        
        # Configurações para lembretes automáticos
        if lembrete.tipo == TipoLembrete.AUTOMATICO:
            lembrete.dias_antecedencia = data.get('dias_antecedencia')
            
            # Calcular data de envio baseada na data da oficina
            if data.get('data_envio_agendada'):
                lembrete.data_envio_agendada = datetime.fromisoformat(data['data_envio_agendada'])
        
        db.session.add(lembrete)
        db.session.commit()
        
        # Se for manual, processar envio imediatamente
        if lembrete.tipo == TipoLembrete.MANUAL:
            processar_lembrete_manual(lembrete.id)
        else:
            # Se for automático, agendar
            from services.reminder_scheduler import agendar_lembrete_especifico
            agendar_lembrete_especifico(lembrete)
        
        return jsonify({
            'success': True,
            'message': 'Lembrete criado com sucesso!',
            'lembrete_id': lembrete.id
        })
        
    except Exception as e:
        logger.error(f"Erro ao criar lembrete: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro ao criar lembrete: {str(e)}'
        }), 500


@reminder_routes.route('/lembretes/<int:lembrete_id>')
@login_required
def visualizar_lembrete(lembrete_id):
    """Visualiza detalhes de um lembrete."""
    lembrete = LembreteOficina.query.get_or_404(lembrete_id)
    
    # Verificar permissão
    if lembrete.cliente_id != current_user.cliente_id:
        flash("Você não tem permissão para visualizar este lembrete.", "error")
        return redirect(url_for('reminder_routes.listar_lembretes'))
    
    # Buscar envios do lembrete
    envios = LembreteEnvio.query.filter_by(lembrete_id=lembrete_id).all()
    
    return render_template('lembretes/visualizar.html', lembrete=lembrete, envios=envios)


@reminder_routes.route('/lembretes/<int:lembrete_id>/enviar', methods=['POST'])
@login_required
def enviar_lembrete(lembrete_id):
    """Envia um lembrete manualmente."""
    lembrete = LembreteOficina.query.get_or_404(lembrete_id)
    
    # Verificar permissão
    if lembrete.cliente_id != current_user.cliente_id:
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        processar_lembrete_manual(lembrete_id)
        return jsonify({'success': True, 'message': 'Lembrete enviado com sucesso!'})
    except Exception as e:
        logger.error(f"Erro ao enviar lembrete {lembrete_id}: {e}")
        return jsonify({'success': False, 'message': f'Erro ao enviar: {str(e)}'}), 500


@reminder_routes.route('/lembretes/<int:lembrete_id>/cancelar', methods=['POST'])
@login_required
def cancelar_lembrete(lembrete_id):
    """Cancela um lembrete."""
    lembrete = LembreteOficina.query.get_or_404(lembrete_id)
    
    # Verificar permissão
    if lembrete.cliente_id != current_user.cliente_id:
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        lembrete.status = StatusLembrete.CANCELADO
        db.session.commit()
        
        # Cancelar jobs agendados
        from services.reminder_scheduler import cancelar_lembrete_agendado
        cancelar_lembrete_agendado(lembrete_id)
        
        return jsonify({'success': True, 'message': 'Lembrete cancelado com sucesso!'})
    except Exception as e:
        logger.error(f"Erro ao cancelar lembrete {lembrete_id}: {e}")
        return jsonify({'success': False, 'message': f'Erro ao cancelar: {str(e)}'}), 500


@reminder_routes.route('/lembretes/<int:lembrete_id>/deletar', methods=['POST'])
@login_required
def deletar_lembrete(lembrete_id):
    """Deleta um lembrete."""
    lembrete = LembreteOficina.query.get_or_404(lembrete_id)
    
    # Verificar permissão
    if lembrete.cliente_id != current_user.cliente_id:
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        db.session.delete(lembrete)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Lembrete deletado com sucesso!'})
    except Exception as e:
        logger.error(f"Erro ao deletar lembrete {lembrete_id}: {e}")
        return jsonify({'success': False, 'message': f'Erro ao deletar: {str(e)}'}), 500


@reminder_routes.route('/api/oficinas-para-lembrete')
@login_required
def api_oficinas_para_lembrete():
    """API para buscar oficinas do cliente para lembretes."""
    cliente_id = current_user.cliente_id
    
    oficinas = Oficina.query.filter_by(cliente_id=cliente_id).order_by(
        Oficina.titulo.asc()
    ).all()
    
    oficinas_data = []
    for oficina in oficinas:
        oficinas_data.append({
            'id': oficina.id,
            'titulo': oficina.titulo,
            'data_inicio': oficina.data_inicio.isoformat() if oficina.data_inicio else None,
            'local': oficina.local,
            'total_inscritos': len(oficina.inscritos) if hasattr(oficina, 'inscritos') else 0
        })
    
    return jsonify({'oficinas': oficinas_data})


@reminder_routes.route('/api/usuarios-para-lembrete')
@login_required
def api_usuarios_para_lembrete():
    """API para buscar usuários do cliente para lembretes."""
    cliente_id = current_user.cliente_id
    
    usuarios = Usuario.query.filter_by(cliente_id=cliente_id).order_by(
        Usuario.nome.asc()
    ).all()
    
    usuarios_data = []
    for usuario in usuarios:
        usuarios_data.append({
            'id': usuario.id,
            'nome': usuario.nome,
            'email': usuario.email,
            'total_inscricoes': len(usuario.inscricoes) if hasattr(usuario, 'inscricoes') else 0
        })
    
    return jsonify({'usuarios': usuarios_data})


@reminder_routes.route('/api/scheduler-status')
@login_required
def api_scheduler_status():
    """API para verificar status do scheduler de lembretes."""
    from services.reminder_scheduler import get_scheduler_status
    return jsonify(get_scheduler_status())


def processar_lembrete_manual(lembrete_id):
    """Processa o envio de um lembrete manual."""
    lembrete = LembreteOficina.query.get(lembrete_id)
    if not lembrete:
        raise Exception("Lembrete não encontrado")
    
    # Buscar destinatários
    destinatarios = obter_destinatarios_lembrete(lembrete)
    
    # Atualizar contadores
    lembrete.total_destinatarios = len(destinatarios)
    lembrete.status = StatusLembrete.ENVIADO
    lembrete.data_envio = datetime.utcnow()
    
    # Criar registros de envio
    envios_criados = 0
    envios_falhas = 0
    
    for destinatario in destinatarios:
        try:
            # Criar registro de envio
            envio = LembreteEnvio(
                lembrete_id=lembrete.id,
                usuario_id=destinatario['usuario_id'],
                oficina_id=destinatario['oficina_id'],
                status=StatusLembrete.PENDENTE
            )
            db.session.add(envio)
            
            # Enviar email
            EmailService.enviar_lembrete_oficina(
                destinatario=destinatario['usuario_email'],
                nome=destinatario['usuario_nome'],
                oficina_titulo=destinatario['oficina_titulo'],
                titulo_lembrete=lembrete.titulo,
                mensagem=lembrete.mensagem
            )
            
            # Marcar como enviado
            envio.status = StatusLembrete.ENVIADO
            envio.data_envio = datetime.utcnow()
            envios_criados += 1
            
        except Exception as e:
            logger.error(f"Erro ao enviar lembrete para {destinatario['usuario_email']}: {e}")
            envio.status = StatusLembrete.FALHOU
            envio.erro_mensagem = str(e)
            envios_falhas += 1
    
    # Atualizar contadores finais
    lembrete.total_enviados = envios_criados
    lembrete.total_falhas = envios_falhas
    
    db.session.commit()


def obter_destinatarios_lembrete(lembrete):
    """Obtém lista de destinatários para um lembrete."""
    destinatarios = []
    
    if lembrete.enviar_todas_oficinas:
        # Buscar todos os usuários inscritos em todas as oficinas do cliente
        oficinas = Oficina.query.filter_by(cliente_id=lembrete.cliente_id).all()
        for oficina in oficinas:
            if hasattr(oficina, 'inscritos'):
                for inscrito in oficina.inscritos:
                    destinatarios.append({
                        'usuario_id': inscrito.id,
                        'usuario_nome': inscrito.nome,
                        'usuario_email': inscrito.email,
                        'oficina_id': oficina.id,
                        'oficina_titulo': oficina.titulo
                    })
    else:
        # Buscar usuários específicos ou oficinas específicas
        oficina_ids = json.loads(lembrete.oficina_ids) if lembrete.oficina_ids else []
        usuario_ids = json.loads(lembrete.usuario_ids) if lembrete.usuario_ids else []
        
        # Por oficinas específicas
        for oficina_id in oficina_ids:
            oficina = Oficina.query.get(oficina_id)
            if oficina and hasattr(oficina, 'inscritos'):
                for inscrito in oficina.inscritos:
                    destinatarios.append({
                        'usuario_id': inscrito.id,
                        'usuario_nome': inscrito.nome,
                        'usuario_email': inscrito.email,
                        'oficina_id': oficina.id,
                        'oficina_titulo': oficina.titulo
                    })
        
        # Por usuários específicos
        for usuario_id in usuario_ids:
            usuario = Usuario.query.get(usuario_id)
            if usuario and hasattr(usuario, 'inscricoes'):
                for inscricao in usuario.inscricoes:
                    destinatarios.append({
                        'usuario_id': usuario.id,
                        'usuario_nome': usuario.nome,
                        'usuario_email': usuario.email,
                        'oficina_id': inscricao.id,
                        'oficina_titulo': inscricao.titulo
                    })
    
    # Remover duplicatas
    destinatarios_unicos = []
    emails_vistos = set()
    
    for dest in destinatarios:
        chave = f"{dest['usuario_id']}_{dest['oficina_id']}"
        if chave not in emails_vistos:
            destinatarios_unicos.append(dest)
            emails_vistos.add(chave)
    
    return destinatarios_unicos


