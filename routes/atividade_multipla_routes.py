"""
Rotas para gerenciar atividades com múltiplas datas
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import and_, or_
from datetime import datetime, date, time
from extensions import db
from models.atividade_multipla_data import AtividadeMultiplaData, AtividadeData, FrequenciaAtividade, CheckinAtividade
from models.event import Evento, Checkin
from models.user import Usuario
from models.cliente import Cliente
from decorators import admin_required, cliente_required
from utils.endpoints import DASHBOARD
import logging

logger = logging.getLogger(__name__)

atividade_multipla_routes = Blueprint('atividade_multipla_routes', __name__)


@atividade_multipla_routes.route('/atividades_multiplas')
@login_required
@cliente_required
def listar_atividades():
    """Lista todas as atividades com múltiplas datas do cliente"""
    atividades = AtividadeMultiplaData.query.filter_by(
        cliente_id=current_user.id,
        ativa=True
    ).order_by(AtividadeMultiplaData.created_at.desc()).all()
    
    return render_template('atividade_multipla/lista_atividades.html', atividades=atividades)


@atividade_multipla_routes.route('/atividades_multiplas/nova', methods=['GET', 'POST'])
@login_required
@cliente_required
def nova_atividade():
    """Cria uma nova atividade com múltiplas datas"""
    if request.method == 'POST':
        try:
            # Dados básicos da atividade
            titulo = request.form.get('titulo')
            descricao = request.form.get('descricao')
            carga_horaria_total = request.form.get('carga_horaria_total')
            tipo_atividade = request.form.get('tipo_atividade')
            categoria = request.form.get('categoria')
            estado = request.form.get('estado')
            cidade = request.form.get('cidade')
            evento_id = request.form.get('evento_id') or None
            
            # Configurações
            permitir_checkin_multiplas_datas = 'permitir_checkin_multiplas_datas' in request.form
            gerar_lista_frequencia = 'gerar_lista_frequencia' in request.form
            exigir_presenca_todas_datas = 'exigir_presenca_todas_datas' in request.form
            
            # Criar atividade
            atividade = AtividadeMultiplaData(
                titulo=titulo,
                descricao=descricao,
                carga_horaria_total=carga_horaria_total,
                tipo_atividade=tipo_atividade,
                categoria=categoria,
                estado=estado,
                cidade=cidade,
                cliente_id=current_user.id,
                evento_id=evento_id,
                permitir_checkin_multiplas_datas=permitir_checkin_multiplas_datas,
                gerar_lista_frequencia=gerar_lista_frequencia,
                exigir_presenca_todas_datas=exigir_presenca_todas_datas
            )
            
            db.session.add(atividade)
            db.session.flush()  # Para obter o ID
            
            # Adicionar datas da atividade
            datas_form = request.form.getlist('datas[]')
            horarios_inicio = request.form.getlist('horarios_inicio[]')
            horarios_fim = request.form.getlist('horarios_fim[]')
            palavras_manha = request.form.getlist('palavras_manha[]')
            palavras_tarde = request.form.getlist('palavras_tarde[]')
            cargas_horarias = request.form.getlist('cargas_horarias[]')
            
            for i, data_str in enumerate(datas_form):
                if data_str:
                    data_atividade = AtividadeData(
                        atividade_id=atividade.id,
                        data=datetime.strptime(data_str, '%Y-%m-%d').date(),
                        horario_inicio=datetime.strptime(horarios_inicio[i], '%H:%M').time(),
                        horario_fim=datetime.strptime(horarios_fim[i], '%H:%M').time(),
                        palavra_chave_manha=palavras_manha[i] if palavras_manha[i] else None,
                        palavra_chave_tarde=palavras_tarde[i] if palavras_tarde[i] else None,
                        carga_horaria_data=cargas_horarias[i] if cargas_horarias[i] else None
                    )
                    db.session.add(data_atividade)
            
            db.session.commit()
            flash('Atividade criada com sucesso!', 'success')
            return redirect(url_for('atividade_multipla_routes.visualizar_atividade', id=atividade.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar atividade: {str(e)}")
            flash('Erro ao criar atividade. Tente novamente.', 'danger')
    
    # Buscar eventos do cliente para o select
    eventos = Evento.query.filter_by(cliente_id=current_user.id).all()
    return render_template('atividade_multipla/nova_atividade.html', eventos=eventos)


@atividade_multipla_routes.route('/atividades_multiplas/<int:id>')
@login_required
@cliente_required
def visualizar_atividade(id):
    """Visualiza uma atividade específica"""
    atividade = AtividadeMultiplaData.query.filter_by(
        id=id,
        cliente_id=current_user.id
    ).first_or_404()
    
    # Buscar frequências por data
    frequencias_por_data = {}
    for data_atividade in atividade.datas:
        frequencias = FrequenciaAtividade.query.filter_by(
            atividade_id=atividade.id,
            data_atividade_id=data_atividade.id
        ).all()
        frequencias_por_data[data_atividade.id] = frequencias
    
    return render_template('atividade_multipla/visualizar_atividade.html', 
                         atividade=atividade, 
                         frequencias_por_data=frequencias_por_data)


@atividade_multipla_routes.route('/atividades_multiplas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@cliente_required
def editar_atividade(id):
    """Edita uma atividade existente"""
    atividade = AtividadeMultiplaData.query.filter_by(
        id=id,
        cliente_id=current_user.id
    ).first_or_404()
    
    if request.method == 'POST':
        try:
            # Atualizar dados básicos
            atividade.titulo = request.form.get('titulo')
            atividade.descricao = request.form.get('descricao')
            atividade.carga_horaria_total = request.form.get('carga_horaria_total')
            atividade.tipo_atividade = request.form.get('tipo_atividade')
            atividade.categoria = request.form.get('categoria')
            atividade.estado = request.form.get('estado')
            atividade.cidade = request.form.get('cidade')
            atividade.evento_id = request.form.get('evento_id') or None
            
            # Configurações
            atividade.permitir_checkin_multiplas_datas = 'permitir_checkin_multiplas_datas' in request.form
            atividade.gerar_lista_frequencia = 'gerar_lista_frequencia' in request.form
            atividade.exigir_presenca_todas_datas = 'exigir_presenca_todas_datas' in request.form
            
            # Remover datas existentes
            AtividadeData.query.filter_by(atividade_id=atividade.id).delete()
            
            # Adicionar novas datas
            datas_form = request.form.getlist('datas[]')
            horarios_inicio = request.form.getlist('horarios_inicio[]')
            horarios_fim = request.form.getlist('horarios_fim[]')
            palavras_manha = request.form.getlist('palavras_manha[]')
            palavras_tarde = request.form.getlist('palavras_tarde[]')
            cargas_horarias = request.form.getlist('cargas_horarias[]')
            
            for i, data_str in enumerate(datas_form):
                if data_str:
                    data_atividade = AtividadeData(
                        atividade_id=atividade.id,
                        data=datetime.strptime(data_str, '%Y-%m-%d').date(),
                        horario_inicio=datetime.strptime(horarios_inicio[i], '%H:%M').time(),
                        horario_fim=datetime.strptime(horarios_fim[i], '%H:%M').time(),
                        palavra_chave_manha=palavras_manha[i] if palavras_manha[i] else None,
                        palavra_chave_tarde=palavras_tarde[i] if palavras_tarde[i] else None,
                        carga_horaria_data=cargas_horarias[i] if cargas_horarias[i] else None
                    )
                    db.session.add(data_atividade)
            
            db.session.commit()
            flash('Atividade atualizada com sucesso!', 'success')
            return redirect(url_for('atividade_multipla_routes.visualizar_atividade', id=atividade.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar atividade: {str(e)}")
            flash('Erro ao editar atividade. Tente novamente.', 'danger')
    
    # Buscar eventos do cliente para o select
    eventos = Evento.query.filter_by(cliente_id=current_user.id).all()
    return render_template('atividade_multipla/editar_atividade.html', atividade=atividade, eventos=eventos)


@atividade_multipla_routes.route('/atividades_multiplas/<int:id>/excluir', methods=['POST'])
@login_required
@cliente_required
def excluir_atividade(id):
    """Exclui uma atividade (soft delete)"""
    atividade = AtividadeMultiplaData.query.filter_by(
        id=id,
        cliente_id=current_user.id
    ).first_or_404()
    
    try:
        atividade.ativa = False
        db.session.commit()
        flash('Atividade excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir atividade: {str(e)}")
        flash('Erro ao excluir atividade. Tente novamente.', 'danger')
    
    return redirect(url_for('atividade_multipla_routes.listar_atividades'))


@atividade_multipla_routes.route('/atividades_multiplas/<int:id>/checkin', methods=['GET', 'POST'])
@login_required
@cliente_required
def checkin_atividade(id):
    """Realiza checkin em uma atividade com múltiplas datas"""
    atividade = AtividadeMultiplaData.query.filter_by(
        id=id,
        cliente_id=current_user.id
    ).first_or_404()
    
    if not atividade.permitir_checkin_multiplas_datas:
        flash('Check-in não permitido para esta atividade.', 'danger')
        return redirect(url_for('atividade_multipla_routes.visualizar_atividade', id=id))
    
    if request.method == 'POST':
        try:
            data_atividade_id = request.form.get('data_atividade_id')
            palavra_chave = request.form.get('palavra_chave')
            turno = request.form.get('turno')
            
            data_atividade = AtividadeData.query.filter_by(
                id=data_atividade_id,
                atividade_id=atividade.id
            ).first()
            
            if not data_atividade:
                flash('Data da atividade não encontrada.', 'danger')
                return redirect(url_for('atividade_multipla_routes.checkin_atividade', id=id))
            
            # Verificar palavra-chave
            palavra_correta = None
            if turno == 'manha' and data_atividade.palavra_chave_manha:
                palavra_correta = data_atividade.palavra_chave_manha
            elif turno == 'tarde' and data_atividade.palavra_chave_tarde:
                palavra_correta = data_atividade.palavra_chave_tarde
            
            if palavra_correta and palavra_chave != palavra_correta:
                flash('Palavra-chave incorreta.', 'danger')
                return redirect(url_for('atividade_multipla_routes.checkin_atividade', id=id))
            
            # Verificar se já existe checkin para esta data e turno
            checkin_existente = CheckinAtividade.query.filter_by(
                atividade_id=atividade.id,
                data_atividade_id=data_atividade_id,
                usuario_id=current_user.id,
                turno=turno
            ).first()
            
            if checkin_existente:
                flash('Check-in já realizado para este turno.', 'warning')
                return redirect(url_for('atividade_multipla_routes.checkin_atividade', id=id))
            
            # Criar checkin
            checkin = CheckinAtividade(
                atividade_id=atividade.id,
                data_atividade_id=data_atividade_id,
                usuario_id=current_user.id,
                palavra_chave=palavra_chave,
                turno=turno,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            db.session.add(checkin)
            
            # Atualizar frequência
            frequencia = FrequenciaAtividade.query.filter_by(
                atividade_id=atividade.id,
                data_atividade_id=data_atividade_id,
                usuario_id=current_user.id
            ).first()
            
            if not frequencia:
                frequencia = FrequenciaAtividade(
                    atividade_id=atividade.id,
                    data_atividade_id=data_atividade_id,
                    usuario_id=current_user.id
                )
                db.session.add(frequencia)
            
            # Atualizar presença baseada no turno
            if turno == 'manha':
                frequencia.presente_manha = True
                frequencia.data_checkin_manha = datetime.utcnow()
                frequencia.palavra_chave_usada_manha = palavra_chave
            elif turno == 'tarde':
                frequencia.presente_tarde = True
                frequencia.data_checkin_tarde = datetime.utcnow()
                frequencia.palavra_chave_usada_tarde = palavra_chave
            elif turno == 'dia_inteiro':
                frequencia.presente_dia_inteiro = True
                frequencia.presente_manha = True
                frequencia.presente_tarde = True
                frequencia.data_checkin_manha = datetime.utcnow()
                frequencia.data_checkin_tarde = datetime.utcnow()
                frequencia.palavra_chave_usada_manha = palavra_chave
                frequencia.palavra_chave_usada_tarde = palavra_chave
            
            db.session.commit()
            flash('Check-in realizado com sucesso!', 'success')
            return redirect(url_for('atividade_multipla_routes.visualizar_atividade', id=id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao realizar check-in: {str(e)}")
            flash('Erro ao realizar check-in. Tente novamente.', 'danger')
    
    return render_template('atividade_multipla/checkin_atividade.html', atividade=atividade)


@atividade_multipla_routes.route('/atividades_multiplas/<int:id>/frequencia')
@login_required
@cliente_required
def lista_frequencia(id):
    """Lista de frequência de uma atividade"""
    atividade = AtividadeMultiplaData.query.filter_by(
        id=id,
        cliente_id=current_user.id
    ).first_or_404()
    
    # Buscar todas as frequências da atividade
    frequencias = FrequenciaAtividade.query.filter_by(
        atividade_id=atividade.id
    ).join(Usuario).order_by(Usuario.nome).all()
    
    return render_template('atividade_multipla/lista_frequencia.html', 
                         atividade=atividade, 
                         frequencias=frequencias)


@atividade_multipla_routes.route('/atividades_multiplas/<int:id>/frequencia/pdf')
@login_required
@cliente_required
def gerar_pdf_frequencia(id):
    """Gera PDF da lista de frequência"""
    from services.pdf_frequencia_service import gerar_pdf_frequencia_atividade
    from flask import send_file
    
    atividade = AtividadeMultiplaData.query.filter_by(
        id=id,
        cliente_id=current_user.id
    ).first_or_404()
    
    try:
        pdf_path = gerar_pdf_frequencia_atividade(atividade.id)
        return send_file(pdf_path, as_attachment=True, 
                        download_name=f'frequencia_{atividade.titulo}_{datetime.now().strftime("%Y%m%d")}.pdf')
    except Exception as e:
        logger.error(f"Erro ao gerar PDF de frequência: {str(e)}")
        flash('Erro ao gerar PDF. Tente novamente.', 'danger')
        return redirect(url_for('atividade_multipla_routes.lista_frequencia', id=id))


@atividade_multipla_routes.route('/atividades_multiplas/<int:id>/inscricoes')
@login_required
@cliente_required
def gerenciar_inscricoes(id):
    """Gerencia inscrições em uma atividade"""
    atividade = AtividadeMultiplaData.query.filter_by(
        id=id,
        cliente_id=current_user.id
    ).first_or_404()
    
    # Buscar usuários inscritos (através de checkins)
    usuarios_inscritos = db.session.query(Usuario).join(CheckinAtividade).filter(
        CheckinAtividade.atividade_id == atividade.id
    ).distinct().all()
    
    return render_template('atividade_multipla/gerenciar_inscricoes.html', 
                         atividade=atividade, 
                         usuarios_inscritos=usuarios_inscritos)


@atividade_multipla_routes.route('/atividades_multiplas/<int:id>/inscricoes/inscrever', methods=['POST'])
@login_required
@cliente_required
def inscrever_usuario(id):
    """Inscreve um usuário em uma atividade"""
    atividade = AtividadeMultiplaData.query.filter_by(
        id=id,
        cliente_id=current_user.id
    ).first_or_404()
    
    try:
        usuario_id = request.form.get('usuario_id')
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            flash('Usuário não encontrado.', 'danger')
            return redirect(url_for('atividade_multipla_routes.gerenciar_inscricoes', id=id))
        
        # Verificar se já está inscrito
        checkin_existente = CheckinAtividade.query.filter_by(
            atividade_id=atividade.id,
            usuario_id=usuario_id
        ).first()
        
        if checkin_existente:
            flash('Usuário já está inscrito nesta atividade.', 'warning')
            return redirect(url_for('atividade_multipla_routes.gerenciar_inscricoes', id=id))
        
        # Criar inscrição (através de um checkin inicial)
        # Nota: Em um sistema real, você pode querer ter uma tabela separada para inscrições
        flash('Usuário inscrito com sucesso!', 'success')
        
    except Exception as e:
        logger.error(f"Erro ao inscrever usuário: {str(e)}")
        flash('Erro ao inscrever usuário. Tente novamente.', 'danger')
    
    return redirect(url_for('atividade_multipla_routes.gerenciar_inscricoes', id=id))


# API endpoints para AJAX
@atividade_multipla_routes.route('/api/atividades_multiplas/<int:id>/datas')
@login_required
@cliente_required
def api_datas_atividade(id):
    """API para buscar datas de uma atividade"""
    atividade = AtividadeMultiplaData.query.filter_by(
        id=id,
        cliente_id=current_user.id
    ).first_or_404()
    
    datas = []
    for data_atividade in atividade.datas_ordenadas():
        datas.append({
            'id': data_atividade.id,
            'data': data_atividade.data.strftime('%Y-%m-%d'),
            'horario_inicio': data_atividade.horario_inicio.strftime('%H:%M'),
            'horario_fim': data_atividade.horario_fim.strftime('%H:%M'),
            'palavra_chave_manha': data_atividade.palavra_chave_manha,
            'palavra_chave_tarde': data_atividade.palavra_chave_tarde,
            'carga_horaria': data_atividade.get_carga_horaria()
        })
    
    return jsonify(datas)


@atividade_multipla_routes.route('/api/atividades_multiplas/<int:id>/frequencia/<int:data_id>')
@login_required
@cliente_required
def api_frequencia_data(id, data_id):
    """API para buscar frequência de uma data específica"""
    atividade = AtividadeMultiplaData.query.filter_by(
        id=id,
        cliente_id=current_user.id
    ).first_or_404()
    
    data_atividade = AtividadeData.query.filter_by(
        id=data_id,
        atividade_id=atividade.id
    ).first_or_404()
    
    frequencias = FrequenciaAtividade.query.filter_by(
        atividade_id=atividade.id,
        data_atividade_id=data_id
    ).join(Usuario).order_by(Usuario.nome).all()
    
    dados = []
    for freq in frequencias:
        dados.append({
            'usuario_id': freq.usuario_id,
            'nome': freq.usuario.nome,
            'email': freq.usuario.email,
            'presente_manha': freq.presente_manha,
            'presente_tarde': freq.presente_tarde,
            'presente_dia_inteiro': freq.presente_dia_inteiro,
            'status_presenca': freq.get_status_presenca(),
            'carga_horaria_presenca': freq.get_carga_horaria_presenca()
        })
    
    return jsonify(dados)
