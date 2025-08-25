from flask import Blueprint
participante_routes = Blueprint("participante_routes", __name__)

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models.user import Usuario, PasswordResetToken
from models.certificado import CertificadoConfig, CertificadoParticipante, NotificacaoCertificado, SolicitacaoCertificado
from models.event import Evento
from models.event import Oficina
from extensions import db
from datetime import datetime



@participante_routes.route('/gerenciar_participantes', methods=['GET'])
@login_required
def gerenciar_participantes():
    # Verifique se é admin
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))

    # Busca todos os usuários cujo tipo é 'participante'
    participantes = Usuario.query.filter_by(tipo='participante').all()

    # Renderiza um template parcial (ou completo). Você pode renderizar
    # a página inteira ou só retornar JSON. Aqui vamos supor que renderiza a modal.
    return render_template('gerenciar_participantes.html', participantes=participantes)

@participante_routes.route('/excluir_participante/<int:participante_id>', methods=['POST'])
@login_required
def excluir_participante(participante_id):
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    participante = Usuario.query.get_or_404(participante_id)
    if participante.tipo != 'participante':
        flash('Esse usuário não é um participante.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))

    PasswordResetToken.query.filter_by(usuario_id=participante.id).delete()
    db.session.delete(participante)
    db.session.commit()
    flash('Participante excluído com sucesso!', 'success')
    return redirect(url_for('dashboard_routes.dashboard'))

@participante_routes.route('/editar_participante_admin/<int:participante_id>', methods=['POST'])
@login_required
def editar_participante_admin(participante_id):
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    participante = Usuario.query.get_or_404(participante_id)
    if participante.tipo != 'participante':
        flash('Esse usuário não é um participante.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))

    # Captura os dados do form
    nome = request.form.get('nome')
    cpf = request.form.get('cpf')
    email = request.form.get('email')
    formacao = request.form.get('formacao')
    nova_senha = request.form.get('senha')

    # Atualiza
    participante.nome = nome
    participante.cpf = cpf
    participante.email = email
    participante.formacao = formacao
    if nova_senha:
        participante.senha = generate_password_hash(nova_senha, method="pbkdf2:sha256")

    db.session.commit()
    flash('Participante atualizado com sucesso!', 'success')
    return redirect(url_for('dashboard_routes.dashboard'))



# ===== ROTAS PARA CERTIFICADOS DO PARTICIPANTE =====

@participante_routes.route('/meus_certificados')
@login_required
def meus_certificados():
    """Página principal de certificados do participante."""
    if current_user.tipo != 'participante':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    # Buscar certificados liberados
    certificados_disponiveis = CertificadoParticipante.query.filter_by(
        usuario_id=current_user.id,
        liberado=True
    ).all()
    
    # Buscar solicitações pendentes
    certificados_pendentes = SolicitacaoCertificado.query.filter_by(
        usuario_id=current_user.id,
        status='pendente'
    ).all()
    
    # Buscar notificações
    notificacoes = NotificacaoCertificado.query.filter_by(
        usuario_id=current_user.id
    ).order_by(NotificacaoCertificado.data_criacao.desc()).limit(10).all()
    
    notificacoes_nao_lidas = NotificacaoCertificado.query.filter_by(
        usuario_id=current_user.id,
        lida=False
    ).count()
    
    # Calcular estatísticas
    from routes.certificado_routes import calcular_atividades_participadas
    
    estatisticas = {
        'liberados': len(certificados_disponiveis),
        'pendentes': len(certificados_pendentes),
        'checkins': 0,
        'carga_horaria': 0
    }
    
    # Calcular estatísticas de participação
    eventos_participante = Evento.query.join(
        'participantes'
    ).filter_by(usuario_id=current_user.id).all()
    
    for evento in eventos_participante:
        dados = calcular_atividades_participadas(current_user.id, evento.id)
        estatisticas['checkins'] += dados.get('total_checkins', 0)
        estatisticas['carga_horaria'] += dados.get('total_horas', 0)
    
    # Verificar se pode solicitar certificados
    pode_solicitar = True  # Implementar lógica específica
    
    # Buscar configurações de eventos
    configs = {}
    for evento in eventos_participante:
        config = CertificadoConfig.query.filter_by(evento_id=evento.id).first()
        if config:
            configs[evento.id] = config
    
    # Buscar oficinas disponíveis para certificados individuais
    oficinas_disponiveis = []
    for evento in eventos_participante:
        oficinas = Oficina.query.filter_by(evento_id=evento.id).all()
        oficinas_disponiveis.extend(oficinas)
    
    return render_template('participante/certificados_participante.html',
                         certificados_disponiveis=certificados_disponiveis,
                         certificados_pendentes=certificados_pendentes,
                         notificacoes=notificacoes,
                         notificacoes_nao_lidas=notificacoes_nao_lidas,
                         estatisticas=estatisticas,
                         pode_solicitar=pode_solicitar,
                         configs=configs,
                         oficinas_disponiveis=oficinas_disponiveis,
                         evento=eventos_participante[0] if eventos_participante else None)


@participante_routes.route('/meus_certificados/<int:evento_id>')
@login_required
def meus_certificados_evento(evento_id):
    """Certificados específicos de um evento."""
    if current_user.tipo != 'participante':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    evento = Evento.query.get_or_404(evento_id)
    
    # Verificar se o participante está inscrito no evento
    from models.event import ParticipanteEvento
    participacao = ParticipanteEvento.query.filter_by(
        usuario_id=current_user.id,
        evento_id=evento_id
    ).first()
    
    if not participacao:
        flash('Você não está inscrito neste evento', 'warning')
        return redirect(url_for('participante_routes.meus_certificados'))
    
    # Buscar certificados do evento
    certificados_disponiveis = CertificadoParticipante.query.filter_by(
        usuario_id=current_user.id,
        evento_id=evento_id,
        liberado=True
    ).all()
    
    certificados_pendentes = SolicitacaoCertificado.query.filter_by(
        usuario_id=current_user.id,
        evento_id=evento_id,
        status='pendente'
    ).all()
    
    # Buscar configuração do evento
    config = CertificadoConfig.query.filter_by(evento_id=evento_id).first()
    
    # Calcular progresso
    from routes.certificado_routes import calcular_atividades_participadas
    from services.certificado_service import verificar_criterios_certificado
    
    dados_participacao = calcular_atividades_participadas(current_user.id, evento_id)
    criterios_ok, pendencias = verificar_criterios_certificado(current_user.id, evento_id)
    
    progresso = {
        'carga_horaria': dados_participacao.get('total_horas', 0),
        'carga_horaria_necessaria': config.carga_horaria_minima if config else 0,
        'percentual_presenca': dados_participacao.get('percentual_presenca', 0),
        'checkins_realizados': dados_participacao.get('total_checkins', 0),
        'checkins_necessarios': config.checkins_minimos if config else 0
    }
    
    # Verificar se tem certificado geral
    tem_certificado_geral = CertificadoParticipante.query.filter_by(
        usuario_id=current_user.id,
        evento_id=evento_id,
        tipo='geral',
        liberado=True
    ).first() is not None
    
    # Buscar oficinas do evento
    oficinas_disponiveis = Oficina.query.filter_by(evento_id=evento_id).all()
    
    return render_template('participante/certificados_participante.html',
                         evento=evento,
                         certificados_disponiveis=certificados_disponiveis,
                         certificados_pendentes=certificados_pendentes,
                         config=config,
                         progresso=progresso,
                         tem_certificado_geral=tem_certificado_geral,
                         oficinas_disponiveis=oficinas_disponiveis,
                         pode_solicitar=config and config.permitir_solicitacao_manual if config else False)


@participante_routes.route('/minha_participacao/<int:evento_id>')
@login_required
def minha_participacao(evento_id):
    """Detalhes da participação do usuário em um evento."""
    if current_user.tipo != 'participante':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    evento = Evento.query.get_or_404(evento_id)
    
    # Verificar participação
    from models.event import ParticipanteEvento
    participacao = ParticipanteEvento.query.filter_by(
        usuario_id=current_user.id,
        evento_id=evento_id
    ).first()
    
    if not participacao:
        flash('Você não está inscrito neste evento', 'warning')
        return redirect(url_for('participante_routes.meus_certificados'))
    
    # Calcular dados de participação
    from routes.certificado_routes import calcular_atividades_participadas
    from services.certificado_service import verificar_criterios_certificado
    
    dados_participacao = calcular_atividades_participadas(current_user.id, evento_id)
    criterios_ok, pendencias = verificar_criterios_certificado(current_user.id, evento_id)
    
    # Buscar configuração
    config = CertificadoConfig.query.filter_by(evento_id=evento_id).first()
    
    return render_template('participante/minha_participacao.html',
                         evento=evento,
                         dados_participacao=dados_participacao,
                         criterios_ok=criterios_ok,
                         pendencias=pendencias,
                         config=config)


@participante_routes.route('/solicitar_certificado_participante', methods=['POST'])
@login_required
def solicitar_certificado_participante():
    """Solicitar certificado como participante."""
    if current_user.tipo != 'participante':
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        evento_id = request.form.get('evento_id')
        tipo = request.form.get('tipo')
        oficina_id = request.form.get('oficina_id')
        justificativa = request.form.get('justificativa', '')
        
        # Verificar se já existe solicitação pendente
        solicitacao_existente = SolicitacaoCertificado.query.filter_by(
            usuario_id=current_user.id,
            evento_id=evento_id,
            oficina_id=oficina_id,
            tipo_certificado=tipo,
            status='pendente'
        ).first()
        
        if solicitacao_existente:
            return jsonify({
                'success': False, 
                'message': 'Já existe uma solicitação pendente para este certificado'
            })
        
        # Verificar se o evento permite solicitações manuais
        config = CertificadoConfig.query.filter_by(evento_id=evento_id).first()
        if not config or not config.permitir_solicitacao_manual:
            return jsonify({
                'success': False,
                'message': 'Este evento não permite solicitações manuais de certificados'
            })
        
        # Coletar dados de participação
        from routes.certificado_routes import calcular_atividades_participadas
        dados_participacao = calcular_atividades_participadas(current_user.id, evento_id)
        
        # Criar solicitação
        solicitacao = SolicitacaoCertificado(
            usuario_id=current_user.id,
            evento_id=evento_id,
            oficina_id=oficina_id if oficina_id else None,
            tipo_certificado=tipo,
            justificativa=justificativa,
            dados_participacao=dados_participacao
        )
        
        db.session.add(solicitacao)
        db.session.commit()
        
        # Criar notificação para administradores
        from routes.certificado_routes import criar_notificacao_solicitacao
        criar_notificacao_solicitacao(solicitacao)
        
        return jsonify({
            'success': True,
            'message': 'Solicitação enviada com sucesso! Você será notificado quando for analisada.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro ao enviar solicitação: {str(e)}'
        })


@participante_routes.route('/marcar_notificacao_lida_participante/<int:notificacao_id>', methods=['POST'])
@login_required
def marcar_notificacao_lida_participante(notificacao_id):
    """Marcar notificação como lida."""
    if current_user.tipo != 'participante':
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    notificacao = NotificacaoCertificado.query.filter_by(
        id=notificacao_id,
        usuario_id=current_user.id
    ).first()
    
    if not notificacao:
        return jsonify({'success': False, 'message': 'Notificação não encontrada'})
    
    notificacao.lida = True
    notificacao.data_leitura = datetime.now()
    
    db.session.commit()
    
    return jsonify({'success': True})
