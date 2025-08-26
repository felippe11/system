from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from models import Evento
from models.user import Usuario
from models.certificado import DeclaracaoTemplate
from services.declaracao_service import (
    gerar_declaracao_participacao, gerar_declaracao_coletiva,
    listar_participantes_evento, validar_participacao
)
from extensions import db
from decorators import cliente_required
import os
from flask import current_app
import logging

logger = logging.getLogger(__name__)
declaracao_bp = Blueprint('declaracao', __name__, url_prefix='/declaracao')


@declaracao_bp.route('/gerar/<int:evento_id>/<int:usuario_id>')
@login_required
@cliente_required
def gerar_declaracao_individual(evento_id, usuario_id):
    """Gera declaração individual de participação."""
    try:
        # Verificar se o evento pertence ao cliente
        evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first()
        if not evento:
            flash('Evento não encontrado.', 'error')
            return redirect(url_for('evento.listar'))
            
        # Verificar se o usuário participou
        if not validar_participacao(usuario_id, evento_id):
            flash('Usuário não participou deste evento.', 'error')
            return redirect(url_for('evento.detalhes', id=evento_id))
            
        # Gerar declaração
        arquivo_path = gerar_declaracao_participacao(usuario_id, evento_id)
        
        if arquivo_path:
            arquivo_completo = os.path.join(current_app.static_folder, arquivo_path)
            if os.path.exists(arquivo_completo):
                usuario = Usuario.query.get(usuario_id)
                filename = f"declaracao_{usuario.nome.replace(' ', '_')}_{evento.nome.replace(' ', '_')}.pdf"
                return send_file(arquivo_completo, as_attachment=True, download_name=filename)
                
        flash('Erro ao gerar declaração.', 'error')
        return redirect(url_for('evento.detalhes', id=evento_id))
        
    except Exception as e:
        logger.error(f"Erro ao gerar declaração individual: {str(e)}")
        flash('Erro interno do servidor.', 'error')
        return redirect(url_for('evento.detalhes', id=evento_id))


@declaracao_bp.route('/gerar-coletiva/<int:evento_id>', methods=['GET', 'POST'])
@login_required
@cliente_required
def gerar_declaracao_coletiva_route(evento_id):
    """Gera declaração coletiva de participação."""
    try:
        # Verificar se o evento pertence ao cliente
        evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first()
        if not evento:
            flash('Evento não encontrado.', 'error')
            return redirect(url_for('evento.listar'))
            
        if request.method == 'GET':
            # Listar participantes para seleção
            participantes = listar_participantes_evento(evento_id)
            return render_template('declaracao/selecionar_participantes.html', 
                                 evento=evento, participantes=participantes)
                                 
        elif request.method == 'POST':
            # Processar seleção
            usuarios_selecionados = request.form.getlist('usuarios_selecionados')
            
            if not usuarios_selecionados:
                flash('Selecione pelo menos um participante.', 'error')
                return redirect(url_for('declaracao.gerar_declaracao_coletiva_route', evento_id=evento_id))
                
            usuarios_ids = [int(uid) for uid in usuarios_selecionados]
            
            # Gerar declaração coletiva
            arquivo_path = gerar_declaracao_coletiva(evento_id, usuarios_ids)
            
            if arquivo_path:
                arquivo_completo = os.path.join(current_app.static_folder, arquivo_path)
                if os.path.exists(arquivo_completo):
                    filename = f"declaracao_coletiva_{evento.nome.replace(' ', '_')}.pdf"
                    return send_file(arquivo_completo, as_attachment=True, download_name=filename)
                    
            flash('Erro ao gerar declaração coletiva.', 'error')
            return redirect(url_for('declaracao.gerar_declaracao_coletiva_route', evento_id=evento_id))
            
    except Exception as e:
        logger.error(f"Erro ao gerar declaração coletiva: {str(e)}")
        flash('Erro interno do servidor.', 'error')
        return redirect(url_for('evento.detalhes', id=evento_id))


@declaracao_bp.route('/templates')
@login_required
@cliente_required
def listar_templates():
    """Lista templates de declaração do cliente."""
    try:
        templates = DeclaracaoTemplate.query.filter_by(cliente_id=current_user.id).all()
        return render_template('declaracao/templates.html', templates=templates)
        
    except Exception as e:
        logger.error(f"Erro ao listar templates: {str(e)}")
        flash('Erro ao carregar templates.', 'error')
        return redirect(url_for('dashboard.cliente'))


@declaracao_bp.route('/template/criar', methods=['GET', 'POST'])
@login_required
@cliente_required
def criar_template():
    """Cria novo template de declaração."""
    try:
        if request.method == 'GET':
            return render_template('declaracao/criar_template.html')
            
        elif request.method == 'POST':
            nome = request.form.get('nome')
            tipo = request.form.get('tipo')
            conteudo = request.form.get('conteudo')
            
            if not all([nome, tipo, conteudo]):
                flash('Todos os campos são obrigatórios.', 'error')
                return render_template('declaracao/criar_template.html')
                
            # Verificar se já existe template ativo do mesmo tipo
            template_existente = DeclaracaoTemplate.query.filter_by(
                cliente_id=current_user.id,
                tipo=tipo,
                ativo=True
            ).first()
            
            # Desativar template existente se necessário
            if template_existente and request.form.get('definir_ativo'):
                template_existente.ativo = False
                
            # Criar novo template
            template = DeclaracaoTemplate(
                cliente_id=current_user.id,
                nome=nome,
                tipo=tipo,
                conteudo=conteudo,
                ativo=bool(request.form.get('definir_ativo'))
            )
            
            db.session.add(template)
            db.session.commit()
            
            flash('Template criado com sucesso!', 'success')
            return redirect(url_for('declaracao.listar_templates'))
            
    except Exception as e:
        logger.error(f"Erro ao criar template: {str(e)}")
        db.session.rollback()
        flash('Erro ao criar template.', 'error')
        return render_template('declaracao/criar_template.html')


@declaracao_bp.route('/template/editar/<int:template_id>', methods=['GET', 'POST'])
@login_required
@cliente_required
def editar_template(template_id):
    """Edita template de declaração."""
    try:
        template = DeclaracaoTemplate.query.filter_by(
            id=template_id, 
            cliente_id=current_user.id
        ).first()
        
        if not template:
            flash('Template não encontrado.', 'error')
            return redirect(url_for('declaracao.listar_templates'))
            
        if request.method == 'GET':
            return render_template('declaracao/editar_template.html', template=template)
            
        elif request.method == 'POST':
            template.nome = request.form.get('nome')
            template.conteudo = request.form.get('conteudo')
            
            # Gerenciar status ativo
            if request.form.get('definir_ativo'):
                # Desativar outros templates do mesmo tipo
                DeclaracaoTemplate.query.filter_by(
                    cliente_id=current_user.id,
                    tipo=template.tipo
                ).update({'ativo': False})
                
                template.ativo = True
            else:
                template.ativo = False
                
            db.session.commit()
            
            flash('Template atualizado com sucesso!', 'success')
            return redirect(url_for('declaracao.listar_templates'))
            
    except Exception as e:
        logger.error(f"Erro ao editar template: {str(e)}")
        db.session.rollback()
        flash('Erro ao editar template.', 'error')
        return redirect(url_for('declaracao.listar_templates'))


@declaracao_bp.route('/template/excluir/<int:template_id>', methods=['POST'])
@login_required
@cliente_required
def excluir_template(template_id):
    """Exclui template de declaração."""
    try:
        template = DeclaracaoTemplate.query.filter_by(
            id=template_id, 
            cliente_id=current_user.id
        ).first()
        
        if not template:
            flash('Template não encontrado.', 'error')
            return redirect(url_for('declaracao.listar_templates'))
            
        db.session.delete(template)
        db.session.commit()
        
        flash('Template excluído com sucesso!', 'success')
        return redirect(url_for('declaracao.listar_templates'))
        
    except Exception as e:
        logger.error(f"Erro ao excluir template: {str(e)}")
        db.session.rollback()
        flash('Erro ao excluir template.', 'error')
        return redirect(url_for('declaracao.listar_templates'))


@declaracao_bp.route('/template/ativar/<int:template_id>', methods=['POST'])
@login_required
@cliente_required
def ativar_template(template_id):
    """Ativa template de declaração."""
    try:
        template = DeclaracaoTemplate.query.filter_by(
            id=template_id, 
            cliente_id=current_user.id
        ).first()
        
        if not template:
            return jsonify({'success': False, 'message': 'Template não encontrado'})
            
        # Desativar outros templates do mesmo tipo
        DeclaracaoTemplate.query.filter_by(
            cliente_id=current_user.id,
            tipo=template.tipo
        ).update({'ativo': False})
        
        # Ativar template selecionado
        template.ativo = True
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Template ativado com sucesso'})
        
    except Exception as e:
        logger.error(f"Erro ao ativar template: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})


@declaracao_bp.route('/participantes/<int:evento_id>')
@login_required
@cliente_required
def listar_participantes(evento_id):
    """Lista participantes do evento para geração de declarações."""
    try:
        # Verificar se o evento pertence ao cliente
        evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first()
        if not evento:
            return jsonify({'error': 'Evento não encontrado'}), 404
            
        participantes = listar_participantes_evento(evento_id)
        
        dados_participantes = []
        for dados in participantes:
            dados_participantes.append({
                'id': dados['usuario'].id,
                'nome': dados['usuario'].nome,
                'email': dados['usuario'].email,
                'cpf': dados['usuario'].cpf,
                'total_checkins': dados['total_checkins'],
                'carga_horaria': dados['carga_horaria']
            })
            
        return jsonify({
            'participantes': dados_participantes,
            'total': len(dados_participantes)
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar participantes: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500


@declaracao_bp.route('/preview/<int:template_id>')
@login_required
@cliente_required
def preview_template(template_id):
    """Visualiza preview do template de declaração."""
    try:
        template = DeclaracaoTemplate.query.filter_by(
            id=template_id, 
            cliente_id=current_user.id
        ).first()
        
        if not template:
            flash('Template não encontrado.', 'error')
            return redirect(url_for('declaracao.listar_templates'))
            
        # Dados fictícios para preview
        from datetime import datetime
        dados_preview = {
            'usuario': {
                'nome': 'João da Silva',
                'cpf': '123.456.789-00',
                'email': 'joao@exemplo.com'
            },
            'evento': {
                'nome': 'Evento de Exemplo',
                'data_inicio': datetime(2024, 1, 15),
                'data_fim': datetime(2024, 1, 17),
                'cidade': 'São Paulo'
            },
            'dados': {
                'total_checkins': 3,
                'carga_horaria': 20
            },
            'data_atual': datetime.now()
        }
        
        if template.tipo == 'coletiva':
            dados_preview['dados_usuarios'] = [
                {
                    'usuario': {'nome': 'João da Silva', 'cpf': '123.456.789-00'},
                    'total_checkins': 3,
                    'carga_horaria': 20
                },
                {
                    'usuario': {'nome': 'Maria Santos', 'cpf': '987.654.321-00'},
                    'total_checkins': 2,
                    'carga_horaria': 15
                }
            ]
            
        return render_template('declaracao/preview.html', 
                             template=template, dados=dados_preview)
        
    except Exception as e:
        logger.error(f"Erro ao gerar preview: {str(e)}")
        flash('Erro ao gerar preview.', 'error')
        return redirect(url_for('declaracao.listar_templates'))