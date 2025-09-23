from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, desc
from datetime import datetime, timedelta
import json
import os
from werkzeug.utils import secure_filename

from models.user import db
from models.formador import ConfiguracaoRelatorioFormador as ConfiguracaoRelatorio
from models.relatorio_config import RelatorioFormador
from utils.auth import cliente_required, ministrante_required, monitor_required

formador_relatorio_routes = Blueprint('formador_relatorio_routes', __name__, url_prefix='/formador-relatorios')

# ==================== ROTAS DO CLIENTE ====================

@formador_relatorio_routes.route('/configuracoes')
@login_required
@cliente_required
def configuracoes():
    """Lista configurações de relatórios do cliente"""
    configuracoes = ConfiguracaoRelatorio.query.filter_by(
        cliente_id=current_user.id
    ).order_by(desc(ConfiguracaoRelatorio.created_at)).all()
    
    return render_template('cliente/relatorio_configuracoes.html', 
                         configuracoes=configuracoes)

@formador_relatorio_routes.route('/configuracoes/nova', methods=['GET', 'POST'])
@login_required
@cliente_required
def nova_configuracao():
    """Criar nova configuração de relatório"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # Criar configuração
            config = ConfiguracaoRelatorio(
                nome=data['nome'],
                descricao=data.get('descricao'),
                tipo=TipoRelatorio(data['tipo']),
                obrigatorio=data.get('obrigatorio', False),
                frequencia_dias=data.get('frequencia_dias'),
                cliente_id=current_user.id
            )
            
            db.session.add(config)
            db.session.flush()  # Para obter o ID
            
            # Criar campos
            for campo_data in data.get('campos', []):
                campo = CampoRelatorio(
                    nome=campo_data['nome'],
                    label=campo_data['label'],
                    tipo=TipoCampo(campo_data['tipo']),
                    obrigatorio=campo_data.get('obrigatorio', False),
                    ordem=campo_data.get('ordem', 0),
                    opcoes=json.dumps(campo_data.get('opcoes', [])),
                    placeholder=campo_data.get('placeholder'),
                    validacao=json.dumps(campo_data.get('validacao', {})),
                    configuracao_id=config.id
                )
                db.session.add(campo)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Configuração criada com sucesso!',
                'config_id': config.id
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Erro ao criar configuração: {str(e)}'
            }), 400
    
    return render_template('cliente/nova_configuracao_relatorio.html')

@formador_relatorio_routes.route('/configuracoes/<int:config_id>/editar', methods=['GET', 'POST'])
@login_required
@cliente_required
def editar_configuracao(config_id):
    """Editar configuração de relatório"""
    config = ConfiguracaoRelatorio.query.filter_by(
        id=config_id, cliente_id=current_user.id
    ).first_or_404()
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # Atualizar configuração
            config.nome = data['nome']
            config.descricao = data.get('descricao')
            config.tipo = TipoRelatorio(data['tipo'])
            config.obrigatorio = data.get('obrigatorio', False)
            config.frequencia_dias = data.get('frequencia_dias')
            config.updated_at = datetime.utcnow()
            
            # Remover campos existentes
            CampoRelatorio.query.filter_by(configuracao_id=config.id).delete()
            
            # Criar novos campos
            for campo_data in data.get('campos', []):
                campo = CampoRelatorio(
                    nome=campo_data['nome'],
                    label=campo_data['label'],
                    tipo=TipoCampo(campo_data['tipo']),
                    obrigatorio=campo_data.get('obrigatorio', False),
                    ordem=campo_data.get('ordem', 0),
                    opcoes=json.dumps(campo_data.get('opcoes', [])),
                    placeholder=campo_data.get('placeholder'),
                    validacao=json.dumps(campo_data.get('validacao', {})),
                    configuracao_id=config.id
                )
                db.session.add(campo)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Configuração atualizada com sucesso!'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Erro ao atualizar configuração: {str(e)}'
            }), 400
    
    return render_template('cliente/editar_configuracao_relatorio.html', config=config)

@formador_relatorio_routes.route('/relatorios-recebidos')
@login_required
@cliente_required
def relatorios_recebidos():
    """Lista relatórios recebidos dos formadores"""
    status_filter = request.args.get('status', '')
    tipo_filter = request.args.get('tipo', '')
    formador_filter = request.args.get('formador', '')
    
    query = RelatorioFormador.query.join(ConfiguracaoRelatorio).filter(
        ConfiguracaoRelatorio.cliente_id == current_user.id
    )
    
    if status_filter:
        query = query.filter(RelatorioFormador.status == status_filter)
    
    if tipo_filter:
        query = query.filter(ConfiguracaoRelatorio.tipo == tipo_filter)
    
    if formador_filter:
        query = query.filter(RelatorioFormador.formador_id == formador_filter)
    
    relatorios = query.order_by(desc(RelatorioFormador.created_at)).all()
    
    return render_template('cliente/relatorios_recebidos.html', 
                         relatorios=relatorios)

# ==================== ROTAS DO FORMADOR ====================

@formador_relatorio_routes.route('/meus-relatorios')
@login_required
@ministrante_required
def meus_relatorios():
    """Lista relatórios do formador"""
    relatorios = RelatorioFormador.query.filter_by(
        formador_id=current_user.id
    ).order_by(desc(RelatorioFormador.created_at)).all()
    
    # Buscar configurações disponíveis
    configuracoes = ConfiguracaoRelatorio.query.filter_by(
        cliente_id=current_user.cliente_id,
        ativo=True
    ).all()
    
    return render_template('formador/meus_relatorios.html', 
                         relatorios=relatorios, 
                         configuracoes=configuracoes)

@formador_relatorio_routes.route('/novo/<int:config_id>', methods=['GET', 'POST'])
@login_required
@ministrante_required
def novo_relatorio(config_id):
    """Criar novo relatório"""
    config = ConfiguracaoRelatorio.query.filter_by(
        id=config_id,
        cliente_id=current_user.cliente_id,
        ativo=True
    ).first_or_404()
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # Criar relatório
            relatorio = RelatorioFormador(
                formador_id=current_user.id,
                configuracao_id=config.id,
                atividade_id=data.get('atividade_id'),
                periodo_inicio=datetime.fromisoformat(data['periodo_inicio']) if data.get('periodo_inicio') else None,
                periodo_fim=datetime.fromisoformat(data['periodo_fim']) if data.get('periodo_fim') else None,
                status='rascunho'
            )
            
            db.session.add(relatorio)
            db.session.flush()
            
            # Salvar respostas
            for campo_id, valor in data.get('respostas', {}).items():
                resposta = RespostaCampo(
                    relatorio_id=relatorio.id,
                    campo_id=int(campo_id),
                    valor=valor
                )
                db.session.add(resposta)
            
            # Registrar histórico
            historico = HistoricoRelatorio(
                relatorio_id=relatorio.id,
                usuario_id=current_user.id,
                usuario_tipo='formador',
                acao='criado',
                detalhes='Relatório criado como rascunho'
            )
            db.session.add(historico)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Relatório salvo como rascunho!',
                'relatorio_id': relatorio.id
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Erro ao salvar relatório: {str(e)}'
            }), 400
    
    return render_template('formador/novo_relatorio.html', config=config)

@formador_relatorio_routes.route('/editar/<int:relatorio_id>', methods=['GET', 'POST'])
@login_required
@ministrante_required
def editar_relatorio(relatorio_id):
    """Editar relatório do formador"""
    relatorio = RelatorioFormador.query.filter_by(
        id=relatorio_id,
        formador_id=current_user.id
    ).first_or_404()
    
    if relatorio.status == 'enviado':
        flash('Relatório já foi enviado e não pode ser editado.', 'warning')
        return redirect(url_for('formador_relatorio_routes.meus_relatorios'))
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # Atualizar relatório
            if data.get('atividade_id'):
                relatorio.atividade_id = data['atividade_id']
            if data.get('periodo_inicio'):
                relatorio.periodo_inicio = datetime.fromisoformat(data['periodo_inicio'])
            if data.get('periodo_fim'):
                relatorio.periodo_fim = datetime.fromisoformat(data['periodo_fim'])
            
            relatorio.updated_at = datetime.utcnow()
            
            # Atualizar respostas
            RespostaCampo.query.filter_by(relatorio_id=relatorio.id).delete()
            
            for campo_id, valor in data.get('respostas', {}).items():
                resposta = RespostaCampo(
                    relatorio_id=relatorio.id,
                    campo_id=int(campo_id),
                    valor=valor
                )
                db.session.add(resposta)
            
            # Registrar histórico
            historico = HistoricoRelatorio(
                relatorio_id=relatorio.id,
                usuario_id=current_user.id,
                usuario_tipo='formador',
                acao='editado',
                detalhes='Relatório atualizado'
            )
            db.session.add(historico)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Relatório atualizado com sucesso!'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Erro ao atualizar relatório: {str(e)}'
            }), 400
    
    return render_template('formador/editar_relatorio.html', relatorio=relatorio)

@formador_relatorio_routes.route('/enviar/<int:relatorio_id>', methods=['POST'])
@login_required
@ministrante_required
def enviar_relatorio(relatorio_id):
    """Enviar relatório para o cliente"""
    relatorio = RelatorioFormador.query.filter_by(
        id=relatorio_id,
        formador_id=current_user.id
    ).first_or_404()
    
    if relatorio.status == 'enviado':
        return jsonify({
            'success': False,
            'message': 'Relatório já foi enviado.'
        }), 400
    
    try:
        # Validar campos obrigatórios
        campos_obrigatorios = CampoRelatorio.query.filter_by(
            configuracao_id=relatorio.configuracao_id,
            obrigatorio=True
        ).all()
        
        respostas_existentes = {r.campo_id: r.valor for r in relatorio.respostas}
        
        for campo in campos_obrigatorios:
            if campo.id not in respostas_existentes or not respostas_existentes[campo.id]:
                return jsonify({
                    'success': False,
                    'message': f'Campo obrigatório não preenchido: {campo.label}'
                }), 400
        
        # Enviar relatório
        relatorio.status = 'enviado'
        relatorio.data_envio = datetime.utcnow()
        relatorio.updated_at = datetime.utcnow()
        
        # Registrar histórico
        historico = HistoricoRelatorio(
            relatorio_id=relatorio.id,
            usuario_id=current_user.id,
            usuario_tipo='formador',
            acao='enviado',
            detalhes='Relatório enviado para análise do cliente'
        )
        db.session.add(historico)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Relatório enviado com sucesso!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro ao enviar relatório: {str(e)}'
        }), 400

# ==================== ROTAS AUXILIARES ====================

@formador_relatorio_routes.route('/upload-arquivo', methods=['POST'])
@login_required
def upload_arquivo():
    """Upload de arquivo para campos de relatório"""
    if 'arquivo' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'}), 400
    
    arquivo = request.files['arquivo']
    if arquivo.filename == '':
        return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'}), 400
    
    try:
        filename = secure_filename(arquivo.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        
        upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'relatorios')
        os.makedirs(upload_dir, exist_ok=True)
        
        filepath = os.path.join(upload_dir, filename)
        arquivo.save(filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': filepath
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao fazer upload: {str(e)}'
        }), 400