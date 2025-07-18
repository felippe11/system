from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from extensions import db, socketio
from werkzeug.utils import secure_filename
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
from models import (
    Checkin, Inscricao, Oficina, ConfiguracaoCliente,
    AgendamentoVisita, Evento, Usuario
)
from utils import formatar_brasilia, determinar_turno
from .agendamento_routes import agendamento_routes  # Needed for URL generation

checkin_routes = Blueprint('checkin_routes', __name__)


@checkin_routes.route('/leitor_checkin', methods=['GET'])
@login_required
def leitor_checkin():
    logger.debug("Entrou em /leitor_checkin")

    token = request.args.get('token')
    logger.debug("Token recebido: %s", token)

    if not token:
        mensagem = "Token não fornecido ou inválido."
        logger.error(mensagem)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'erro', 'mensagem': mensagem}), 400
        flash(mensagem, "danger")
        return redirect(url_for('dashboard_routes.dashboard'))

    inscricao = Inscricao.query.filter_by(qr_code_token=token).first()
    logger.debug("Inscricao encontrada: %s (ID: %s)", inscricao, inscricao.id if inscricao else 'None')

    if not inscricao:
        mensagem = "Inscrição não encontrada para este token."
        logger.error(mensagem)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'erro', 'mensagem': mensagem}), 404
        flash(mensagem, "danger")
        return redirect(url_for('dashboard_routes.dashboard'))

    # Verifica se é check-in de evento ou oficina
    if inscricao.evento_id:
        logger.debug("Inscrição pertence a EVENTO (ID=%s)", inscricao.evento_id)
        checkin_existente = Checkin.query.filter_by(
            usuario_id=inscricao.usuario_id,
            evento_id=inscricao.evento_id
        ).first()
        if checkin_existente:
            mensagem = "Check-in de evento já foi realizado!"
            logger.warning(mensagem)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'status': 'repetido', 'mensagem': mensagem}), 200
            flash(mensagem, "warning")
            return redirect(url_for('dashboard_routes.dashboard'))

        novo_checkin = Checkin(
            usuario_id=inscricao.usuario_id,
            evento_id=inscricao.evento_id,
            palavra_chave="QR-EVENTO"
        )
        dados_checkin = {
            'participante': inscricao.usuario.nome,
            'evento': inscricao.evento.nome,
            'data_hora': novo_checkin.data_hora.strftime('%d/%m/%Y %H:%M:%S')
        }
        logger.info("Check-in de EVENTO criado. Usuario=%s, Evento=%s", inscricao.usuario_id, inscricao.evento_id)

    elif inscricao.oficina_id:
        logger.debug("Inscrição pertence a OFICINA (ID=%s)", inscricao.oficina_id)
        checkin_existente = Checkin.query.filter_by(
            usuario_id=inscricao.usuario_id,
            oficina_id=inscricao.oficina_id
        ).first()
        if checkin_existente:
            mensagem = "Check-in da oficina já foi realizado!"
            logger.warning(mensagem)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'status': 'repetido', 'mensagem': mensagem}), 200
            flash(mensagem, "warning")
            return redirect(url_for('dashboard_routes.dashboard'))

        novo_checkin = Checkin(
            usuario_id=inscricao.usuario_id,
            oficina_id=inscricao.oficina_id,
            palavra_chave="QR-OFICINA"
        )
        dados_checkin = {
            'participante': inscricao.usuario.nome,
            'oficina': inscricao.oficina.titulo,
            'data_hora': novo_checkin.data_hora.strftime('%d/%m/%Y %H:%M:%S')
        }
        logger.info("Check-in de OFICINA criado. Usuario=%s, Oficina=%s", inscricao.usuario_id, inscricao.oficina_id)

    else:
        mensagem = "Inscrição sem evento ou oficina vinculada."
        logger.error(mensagem)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'erro', 'mensagem': mensagem}), 400
        flash(mensagem, "danger")
        return redirect(url_for('dashboard_routes.dashboard'))

    db.session.add(novo_checkin)
    db.session.commit()
    logger.info("Check-in salvo no banco: ID=%s", novo_checkin.id)

    # Emitir via Socket.IO (se você usa Socket.IO)
    socketio.emit('novo_checkin', dados_checkin, broadcast=True)
    logger.debug("Socket.IO emit -> %s", dados_checkin)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        logger.debug("Retornando JSON para AJAX")
        return jsonify({'status': 'ok', **dados_checkin})

    flash("Check-in realizado com sucesso!", "success")
    logger.info("Check-in concluído e flash exibido, redirecionando para dashboard.")
    return redirect(url_for('dashboard_routes.dashboard'))

@checkin_routes.route('/cliente/checkin_manual/<int:usuario_id>/<int:oficina_id>', methods=['POST'])
@login_required
def checkin_manual(usuario_id, oficina_id):
    checkin_existente = Checkin.query.filter_by(usuario_id=usuario_id, oficina_id=oficina_id).first()
    if checkin_existente:
        flash('Participante já realizou check-in.', 'warning')
        return redirect(request.referrer or url_for('inscricao_routes.gerenciar_inscricoes'))

    oficina = Oficina.query.get_or_404(oficina_id)
    
    checkin = Checkin(
        usuario_id=usuario_id,
        oficina_id=oficina_id,
        palavra_chave="manual",
        cliente_id=oficina.cliente_id,
        evento_id=oficina.evento_id
    )
    db.session.add(checkin)
    db.session.commit()

    flash('Check-in manual registrado com sucesso!', 'success')
    return redirect(request.referrer or url_for('inscricao_routes.gerenciar_inscricoes'))

@checkin_routes.route('/checkin/<int:oficina_id>', methods=['GET', 'POST'])
@login_required
def checkin(oficina_id):
    oficina = Oficina.query.get_or_404(oficina_id)
    cliente_id_oficina = oficina.cliente_id

    config_cliente = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id_oficina).first()
    if not config_cliente or not config_cliente.permitir_checkin_global:
        flash("Check-in indisponível para esta oficina!", "danger")
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

    if request.method == 'POST':
        palavra_escolhida = request.form.get('palavra_escolhida')
        if not palavra_escolhida:
            flash("Selecione uma opção de check-in.", "danger")
            return redirect(url_for('checkin_routes.checkin', oficina_id=oficina_id))

        inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, oficina_id=oficina.id).first()
        if not inscricao:
            flash("Você não está inscrito nesta oficina!", "danger")
            return redirect(url_for('checkin_routes.checkin', oficina_id=oficina_id))

        if inscricao.checkin_attempts >= 2:
            flash("Você excedeu o número de tentativas de check-in.", "danger")
            return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

        # ❗Verificar se já existe check-in anterior
        checkin_existente = Checkin.query.filter_by(usuario_id=current_user.id, oficina_id=oficina.id).first()
        if checkin_existente:
            flash("Você já realizou o check-in!", "warning")
            return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

        if palavra_escolhida.strip() != oficina.palavra_correta.strip():
            inscricao.checkin_attempts += 1
            db.session.commit()
            flash("Palavra-chave incorreta!", "danger")
            return redirect(url_for('checkin_routes.checkin', oficina_id=oficina_id))

        checkin = Checkin(
            usuario_id=current_user.id,
            oficina_id=oficina.id,
            palavra_chave=palavra_escolhida,
            cliente_id=oficina.cliente_id,
            evento_id=oficina.evento_id
        )
        db.session.add(checkin)
        db.session.commit()
        flash("Check-in realizado com sucesso!", "success")
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

    opcoes = oficina.opcoes_checkin.split(',') if oficina.opcoes_checkin else []
    return render_template('checkin/checkin.html', oficina=oficina, opcoes=opcoes)




@checkin_routes.route('/oficina/<int:oficina_id>/checkins', methods=['GET'])
@login_required
def lista_checkins(oficina_id):
    if current_user.tipo not in ['admin', 'cliente']:
        flash("Acesso Autorizado!", "danger")

    oficina = Oficina.query.get_or_404(oficina_id)
    checkins = Checkin.query.filter_by(oficina_id=oficina_id).all()

    usuarios_checkin = [{
        'nome': checkin.usuario.nome,
        'cpf': checkin.usuario.cpf,
        'email': checkin.usuario.email,
        'data_hora': checkin.data_hora
    } for checkin in checkins]

    # Coleta todos os ministrantes associados à oficina
    ministrantes = [m.nome for m in oficina.ministrantes_associados] if oficina.ministrantes_associados else []

    return render_template(
        'checkin/lista_checkins.html',
        oficina=oficina,
        usuarios_checkin=usuarios_checkin,
        ministrantes=ministrantes
    )

@checkin_routes.route('/checkin')
def checkin_token():
    """
    Endpoint para processamento de check-in via QR Code
    """
    token = request.args.get('token')
    
    if not token:
        flash('Token inválido ou não fornecido', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    # Se não estiver logado, redirecionar para login
    if not current_user.is_authenticated:
        # Salvar token na sessão para usar após o login
        session['checkin_token'] = token
        flash('Faça login para processar o check-in', 'info')
        return redirect(url_for('auth.login', next=request.url))
    
    # Verificar se é um cliente (organizador)
    if current_user.tipo != 'cliente':
        flash('Apenas organizadores podem realizar check-in', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    # Buscar o agendamento pelo token
    agendamento = AgendamentoVisita.query.filter_by(qr_code_token=token).first()
    
    if not agendamento:
        flash('Agendamento não encontrado', 'danger')
        return redirect(url_for('dashboard_routes.dashboard_cliente'))
    
    # Verificar se o agendamento pertence a um evento do cliente
    evento_id = agendamento.horario.evento_id
    evento = Evento.query.get(evento_id)
    
    if evento.cliente_id != current_user.id:
        flash('Este agendamento não pertence a um evento seu', 'danger')
        return redirect(url_for('dashboard_routes.dashboard_cliente'))
    
    # Verificar se já foi realizado check-in
    if agendamento.checkin_realizado:
        flash('Check-in já realizado para este agendamento', 'warning')
    else:
        # Realizar check-in
        return redirect(url_for(
            'agendamento_routes.checkin_agendamento',
            qr_code_token=token
        ))
    
    # Redirecionar para detalhes do agendamento
    return redirect(url_for('agendamento_routes.detalhes_agendamento', agendamento_id=agendamento.id))


@checkin_routes.route('/leitor_checkin_json', methods=['POST'])
@login_required
def leitor_checkin_json():
    """
    Recebe o token do QR‑Code, grava o check‑in
    (evento ou oficina) e avisa via Socket.IO.
    Sempre grava o cliente_id para que apareça
    na lista filtrada por cliente.
    """
    from datetime import datetime      # ← agora importado
    import sys

    data = request.get_json(silent=True) or {}
    token = (data.get('token') or '').strip()

    if not token:
        return jsonify(status='error',
                       message='Token não fornecido!'), 400

    # procura a inscrição pelo token
    inscricao = Inscricao.query.filter_by(qr_code_token=token).first()
    if not inscricao:
        return jsonify(status='error',
                       message='Inscrição não encontrada.'), 404

    if inscricao.cliente_id != current_user.id:
        return jsonify(status='error',
                       message='Esta inscrição não pertence a um evento ou atividade sua!'), 403

    cliente_id   = inscricao.cliente_id
    sala_cliente = f"cliente_{cliente_id}"     # sala usada no Socket.IO

    # ---------- EVENTO ----------
    if inscricao.evento_id:
        # evita duplicidade
        if Checkin.query.filter_by(usuario_id=inscricao.usuario_id,
                                   evento_id=inscricao.evento_id).first():
            return jsonify(status='warning',
                           message='Check‑in do evento já foi realizado!')

        novo = Checkin(usuario_id = inscricao.usuario_id,
                       evento_id  = inscricao.evento_id,
                       cliente_id = cliente_id,          # ★ grava aqui
                       palavra_chave = "QR-EVENTO")
    # ---------- OFICINA ----------
    elif inscricao.oficina_id:
        if Checkin.query.filter_by(usuario_id=inscricao.usuario_id,
                                   oficina_id=inscricao.oficina_id).first():
            return jsonify(status='warning',
                           message='Check‑in da oficina já foi realizado!')

        novo = Checkin(usuario_id = inscricao.usuario_id,
                       oficina_id = inscricao.oficina_id,
                       cliente_id = cliente_id,          # ★ grava aqui
                       palavra_chave = "QR-OFICINA")
    else:
        return jsonify(status='error',
                       message='Inscrição sem evento ou oficina.'), 400

    db.session.add(novo)
    db.session.commit()

    # prepara carga para front‑end
    payload = {
        'participante': inscricao.usuario.nome,
        'data_hora'   : novo.data_hora.strftime('%d/%m/%Y %H:%M:%S'),
        'turno'       : determinar_turno(novo.data_hora)
    }
    if novo.evento_id:
        payload['evento'] = inscricao.evento.nome
    else:
        payload['oficina'] = inscricao.oficina.titulo

    # emite apenas para quem estiver na sala do cliente
    socketio.emit('novo_checkin', payload,
                  namespace='/checkins', room=sala_cliente)

    return jsonify(status='success',
                   message='Check‑in realizado com sucesso!',
                   **payload)



@checkin_routes.route('/lista_checkins_qr')
@login_required
def lista_checkins_qr():
    """
    Rota para exibir os check-ins feitos via QR Code em uma página dedicada,
    substituindo o modal que era usado anteriormente.
    """
    if current_user.tipo not in ['admin', 'cliente']:
        flash("Acesso não autorizado!", "danger")
        return redirect(url_for('dashboard_routes.dashboard'))
        
    # Busca apenas check-ins via QR dos usuários do cliente
    from sqlalchemy import or_
    from models import Usuario

    checkins_via_qr = (
        Checkin.query
        .outerjoin(Checkin.oficina)
        .outerjoin(Checkin.usuario)
        .filter(
            Checkin.palavra_chave.in_([
                'QR-AUTO',
                'QR-EVENTO',
                'QR-OFICINA'
            ]),
            or_(
                Usuario.cliente_id == current_user.id,
                Oficina.cliente_id == current_user.id,
                Checkin.cliente_id == current_user.id
            )
        )
        .order_by(Checkin.data_hora.desc())
        .all()
    )
    
    # Obtém as atividades (oficinas) do cliente para o filtro
    oficinas = Oficina.query.filter_by(cliente_id=current_user.id).all()
    
    return render_template(
        'checkin/lista_checkins_qr.html',
        checkins_via_qr=checkins_via_qr,
        oficinas=oficinas,
        active_tab=None
    )

@checkin_routes.route('/lista_checkins_json')
@login_required
def lista_checkins_json():
    """
    Retorna os últimos check‑ins do cliente logado em formato JSON.
    Identifica se o check‑in é de evento ou de oficina.
    """
    from sqlalchemy import or_

    base_query = Checkin.query.outerjoin(Checkin.oficina).outerjoin(Checkin.usuario)

    if current_user.is_cliente():
        base_query = base_query.filter(
            or_(
                Usuario.cliente_id == current_user.id,
                Oficina.cliente_id == current_user.id,
                Checkin.cliente_id == current_user.id,
            )
        )

    checkins = (
        base_query
        .order_by(Checkin.data_hora.desc())
        .limit(50)
        .all()
    )

    resultado = []
    for c in checkins:
        data_formatada = formatar_brasilia(c.data_hora)
        turno = determinar_turno(c.data_hora)

        if c.evento_id:
            resultado.append({
                'participante': c.usuario.nome,
                'evento'      : c.evento.nome if c.evento else "Evento Desconhecido",
                'data_hora'   : data_formatada,
                'turno'       : turno,
                'tipo_checkin': 'evento'
            })
        elif c.oficina_id:
            resultado.append({
                'participante': c.usuario.nome,
                'oficina'     : c.oficina.titulo if c.oficina else "Oficina Desconhecida",
                'data_hora'   : data_formatada,
                'turno'       : turno,
                'tipo_checkin': 'oficina'
            })
        else:
            resultado.append({
                'participante': c.usuario.nome,
                'atividade'   : "N/A",
                'data_hora'   : data_formatada,
                'turno'       : turno,
                'tipo_checkin': 'nenhum'
            })

    return jsonify(status='success', checkins=resultado)


@checkin_routes.route('/fazer_checkin/<int:agendamento_id>')
@login_required
def fazer_checkin(agendamento_id):
    """Redireciona para a página de confirmação de check-in."""
    return redirect(url_for('checkin_routes.confirmar_checkin', agendamento_id=agendamento_id))


@checkin_routes.route('/confirmar_checkin/<int:agendamento_id>', methods=['GET', 'POST'])
@login_required
def confirmar_checkin(agendamento_id):
    """
    Página de confirmação de check-in com detalhes do agendamento e lista de alunos.
    """
    # Verificar se é um cliente
    if current_user.tipo != 'cliente':
        flash('Acesso negado! Esta área é exclusiva para organizadores.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    agendamento = AgendamentoVisita.query.get_or_404(agendamento_id)
    
    # Verificar se o agendamento pertence a um evento do cliente
    evento = agendamento.horario.evento
    if evento.cliente_id != current_user.id:
        flash('Este agendamento não pertence a um evento seu!', 'danger')
        return redirect(url_for('agendamento_routes.checkin_qr_agendamento'))
    
    # Verificar se já foi feito check-in
    if agendamento.checkin_realizado:
        flash('Check-in já foi realizado para este agendamento!', 'warning')
        return redirect(url_for('agendamento_routes.detalhes_agendamento', agendamento_id=agendamento.id))
    
    if request.method == 'POST':
        # Realizar check-in
        agendamento.checkin_realizado = True
        agendamento.data_checkin = datetime.utcnow()
        agendamento.status = 'realizado'
        
        # Verificar se há alunos marcados como presentes
        alunos_presentes = request.form.getlist('alunos_presentes')
        
        # Marcar alunos como presentes
        for aluno in agendamento.alunos:
            aluno.presente = str(aluno.id) in alunos_presentes
        
        try:
            db.session.commit()
            flash('Check-in realizado com sucesso!', 'success')
            return redirect(url_for('agendamento_routes.detalhes_agendamento', agendamento_id=agendamento.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao realizar check-in: {str(e)}', 'danger')
    
    return render_template(
        'checkin/confirmar_checkin.html',
        agendamento=agendamento,
        horario=agendamento.horario,
        evento=evento
    )

@checkin_routes.route('/processar_qrcode', methods=['POST'])
@login_required
def processar_qrcode():
    """
    Endpoint AJAX para processar dados do QR Code escaneado.
    """
    # Verificar se é um cliente
    if current_user.tipo != 'cliente':
        return jsonify({'success': False, 'message': 'Acesso negado!'})
    
    # Obter dados do request
    data = request.json
    token = data.get('token')
    
    if not token:
        return jsonify({'success': False, 'message': 'Token não fornecido!'})
    
    # Buscar agendamento pelo token
    agendamento = AgendamentoVisita.query.filter_by(qr_code_token=token).first()
    
    if not agendamento:
        return jsonify({'success': False, 'message': 'Agendamento não encontrado!'})
    
    # Verificar se o agendamento pertence a um evento do cliente
    evento = agendamento.horario.evento
    if evento.cliente_id != current_user.id:
        return jsonify({'success': False, 'message': 'Este agendamento não pertence a um evento seu!'})
    
    # Verificar se já foi feito check-in
    if agendamento.checkin_realizado:
        return jsonify({
            'success': False, 
            'message': 'Check-in já realizado!',
            'redirect': url_for('agendamento_routes.detalhes_agendamento', agendamento_id=agendamento.id)
        })
    
    # Retornar sucesso e URL para confirmação
    return jsonify({
        'success': True,
        'message': 'Agendamento encontrado!',
        'redirect': url_for('checkin_routes.confirmar_checkin', agendamento_id=agendamento.id)
    })

@checkin_routes.route('/admin_scan')
@login_required
def admin_scan():
    if current_user.tipo not in ('admin', 'cliente'):
        flash("Acesso Autorizado!", "danger")
        
    return render_template("checkin/scan_qr.html")
