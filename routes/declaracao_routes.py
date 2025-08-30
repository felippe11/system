from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for, make_response
from flask_login import login_required, current_user
from models import Evento
from models.user import Usuario
from models.certificado import DeclaracaoTemplate, VariavelDinamica
import json
from services.declaracao_service import (
    gerar_declaracao_participacao, gerar_declaracao_coletiva,
    listar_participantes_evento, validar_participacao
)
from extensions import db
from decorators import cliente_required
import os
from flask import current_app
import logging
from datetime import datetime

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


@declaracao_bp.route('/editor-avancado')
@login_required
def editor_avancado():
    """Exibe o editor avançado de declarações"""
    try:
        return render_template('declaracao/editor_avancado.html')
    except Exception as e:
        logger.error(f"Erro ao carregar editor avançado: {str(e)}")
        flash('Erro ao carregar editor avançado.', 'error')
        return redirect(url_for('declaracao.listar_templates'))


@declaracao_bp.route('/editor-avancado/<int:template_id>')
@login_required
def editar_template_avancado(template_id):
    """Edita um template existente no editor avançado"""
    try:
        template = DeclaracaoTemplate.query.get_or_404(template_id)
        
        # Verificar se o usuário tem permissão para editar este template
        if not current_user.is_admin and template.cliente_id != current_user.cliente_id:
            flash('Você não tem permissão para editar este template.', 'error')
            return redirect(url_for('declaracao.listar_templates'))
        
        return render_template('declaracao/editor_avancado.html', template=template)
    except Exception as e:
        logger.error(f"Erro ao carregar template para edição: {str(e)}")
        flash('Erro ao carregar template.', 'error')
        return redirect(url_for('declaracao.listar_templates'))







@declaracao_bp.route('/configuracoes_avancadas/<int:template_id>')
@login_required
def configuracoes_avancadas(template_id):
    """Exibe as configurações avançadas de um template"""
    try:
        template = DeclaracaoTemplate.query.get_or_404(template_id)
        
        # Verificar permissões
        if not current_user.is_admin and template.cliente_id != current_user.cliente_id:
            flash('Você não tem permissão para acessar este template.', 'error')
            return redirect(url_for('declaracao.listar_templates'))
        
        # Carregar configurações existentes
        configuracoes = {}
        if template.configuracoes:
            try:
                configuracoes = json.loads(template.configuracoes)
            except:
                configuracoes = {}
        
        return render_template('declaracao/configuracoes_avancadas.html', 
                             template=template, 
                             configuracoes=configuracoes)
        
    except Exception as e:
        logger.error(f"Erro ao carregar configurações: {str(e)}")
        flash('Erro ao carregar configurações.', 'error')
        return redirect(url_for('declaracao.listar_templates'))


@declaracao_bp.route('/salvar_configuracoes/<int:template_id>', methods=['POST'])
@login_required
def salvar_configuracoes(template_id):
    """Salva as configurações avançadas de um template"""
    try:
        template = DeclaracaoTemplate.query.get_or_404(template_id)
        
        # Verificar permissões
        if not current_user.is_admin and template.cliente_id != current_user.cliente_id:
            return jsonify({'success': False, 'message': 'Sem permissão para editar este template'})
        
        data = request.get_json()
        configuracoes = data.get('configuracoes', {})
        
        template.configuracoes = json.dumps(configuracoes)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Configurações salvas com sucesso!'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao salvar configurações: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})



def editar_template_avancado(template_id):
    """Edita template existente no editor avançado."""
    try:
        template = DeclaracaoTemplate.query.filter_by(
            id=template_id, 
            cliente_id=current_user.id
        ).first()
        
        if not template:
            flash('Template não encontrado.', 'error')
            return redirect(url_for('declaracao.listar_templates'))
            
        return render_template('declaracao/editor_avancado.html', template=template)
        
    except Exception as e:
        logger.error(f"Erro ao carregar template para edição: {str(e)}")
        flash('Erro ao carregar template.', 'error')
        return redirect(url_for('declaracao.listar_templates'))


@declaracao_bp.route('/salvar_template_avancado', methods=['POST'])
@login_required
@cliente_required
def salvar_template_avancado():
    """Salva template criado no editor avançado."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Dados não fornecidos'})
            
        nome = data.get('nome')
        tipo = data.get('tipo')
        orientacao = data.get('orientacao', 'portrait')
        elementos = data.get('elementos', [])
        configuracoes = data.get('configuracoes', {})
        conteudo = data.get('conteudo', '')
        
        if not all([nome, tipo]):
            return jsonify({'success': False, 'message': 'Nome e tipo são obrigatórios'})
            
        # Verificar se é edição ou criação
        template_id = data.get('template_id')
        
        if template_id:
            # Editar template existente
            template = DeclaracaoTemplate.query.filter_by(
                id=template_id,
                cliente_id=current_user.id
            ).first()
            
            if not template:
                return jsonify({'success': False, 'message': 'Template não encontrado'})
                
        else:
            # Criar novo template
            template = DeclaracaoTemplate(cliente_id=current_user.id)
            db.session.add(template)
            
        # Atualizar dados do template
        template.nome = nome
        template.tipo = tipo
        template.conteudo = conteudo
        template.configuracoes = {
            'elementos': elementos,
            'orientacao': orientacao,
            'versao': '2.0',
            **configuracoes
        }
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Template salvo com sucesso!',
            'template_id': template.id
        })
        
    except Exception as e:
        logger.error(f"Erro ao salvar template avançado: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})


@declaracao_bp.route('/salvar_variavel', methods=['POST'])
@login_required
@cliente_required
def salvar_variavel():
    """Salva nova variável dinâmica."""
    try:
        from models.certificado import VariavelDinamica
        
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Dados não fornecidos'})
            
        nome = data.get('nome')
        descricao = data.get('descricao')
        valor_padrao = data.get('valor_padrao', '')
        tipo = data.get('tipo', 'text')
        
        if not all([nome, descricao]):
            return jsonify({'success': False, 'message': 'Nome e descrição são obrigatórios'})
            
        # Verificar se variável já existe
        variavel_existente = VariavelDinamica.query.filter_by(
            cliente_id=current_user.id,
            nome=nome
        ).first()
        
        if variavel_existente:
            return jsonify({'success': False, 'message': 'Variável com este nome já existe'})
            
        # Criar nova variável
        variavel = VariavelDinamica(
            cliente_id=current_user.id,
            nome=nome,
            descricao=descricao,
            valor_padrao=valor_padrao,
            tipo=tipo
        )
        
        db.session.add(variavel)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Variável criada com sucesso!',
            'variavel': {
                'id': variavel.id,
                'nome': variavel.nome,
                'descricao': variavel.descricao,
                'valor_padrao': variavel.valor_padrao,
                'tipo': variavel.tipo
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao salvar variável: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})


@declaracao_bp.route('/variaveis_dinamicas')
@login_required
@cliente_required
def listar_variaveis_dinamicas():
    """Lista variáveis dinâmicas do cliente."""
    try:
        from models.certificado import VariavelDinamica
        
        variaveis = VariavelDinamica.query.filter_by(
            cliente_id=current_user.id
        ).all()
        
        dados_variaveis = []
        for variavel in variaveis:
            dados_variaveis.append({
                'id': variavel.id,
                'nome': variavel.nome,
                'descricao': variavel.descricao,
                'valor_padrao': variavel.valor_padrao,
                'tipo': variavel.tipo
            })
            
        return jsonify({
            'success': True,
            'variaveis': dados_variaveis
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar variáveis dinâmicas: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})


@declaracao_bp.route('/exportar-importar')
@login_required
@cliente_required
def exportar_importar():
    """Página para exportar e importar templates."""
    try:
        templates = DeclaracaoTemplate.query.filter_by(
            cliente_id=current_user.id
        ).all()
        
        return render_template('declaracao/exportar_importar.html', templates=templates)
        
    except Exception as e:
        logger.error(f"Erro ao carregar página de exportar/importar: {str(e)}")
        flash('Erro ao carregar página.', 'error')
        return redirect(url_for('declaracao.listar_templates'))


@declaracao_bp.route('/exportar', methods=['POST'])
@login_required
@cliente_required
def exportar_templates():
    """Exporta templates selecionados."""
    try:
        data = request.get_json()
        template_ids = data.get('template_ids', [])
        formato = data.get('formato', 'json')
        incluir_metadados = data.get('incluir_metadados', True)
        
        if not template_ids:
            return jsonify({'success': False, 'message': 'Nenhum template selecionado'})
        
        # Buscar templates do cliente
        templates = DeclaracaoTemplate.query.filter(
            DeclaracaoTemplate.id.in_(template_ids),
            DeclaracaoTemplate.cliente_id == current_user.id
        ).all()
        
        if not templates:
            return jsonify({'success': False, 'message': 'Templates não encontrados'})
        
        # Preparar dados para exportação
        export_data = {
            'version': '1.0',
            'export_date': datetime.now().isoformat(),
            'format': formato,
            'include_metadata': incluir_metadados,
            'templates': []
        }
        
        for template in templates:
            template_data = {
                'nome': template.nome,
                'tipo': template.tipo,
                'conteudo_html': template.conteudo_html,
                'ativo': template.ativo
            }
            
            if incluir_metadados:
                template_data.update({
                    'data_criacao': template.data_criacao.isoformat() if template.data_criacao else None,
                    'data_atualizacao': template.data_atualizacao.isoformat() if template.data_atualizacao else None
                })
            
            export_data['templates'].append(template_data)
        
        # Criar resposta com arquivo
        from io import BytesIO
        import zipfile
        
        if formato == 'zip':
            # Criar arquivo ZIP
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr('templates.json', json.dumps(export_data, indent=2, ensure_ascii=False))
            
            zip_buffer.seek(0)
            
            return send_file(
                zip_buffer,
                as_attachment=True,
                download_name=f'templates_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip',
                mimetype='application/zip'
            )
        else:
            # Retornar JSON
            response = make_response(json.dumps(export_data, indent=2, ensure_ascii=False))
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename=templates_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            return response
            
    except Exception as e:
        logger.error(f"Erro ao exportar templates: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})


@declaracao_bp.route('/importar', methods=['POST'])
@login_required
@cliente_required
def importar_templates():
    """Importa templates de arquivo."""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'})
        
        file = request.files['file']
        sobrescrever = request.form.get('sobrescrever', 'false').lower() == 'true'
        validar = request.form.get('validar', 'true').lower() == 'true'
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'})
        
        # Verificar extensão do arquivo
        if not (file.filename.endswith('.json') or file.filename.endswith('.zip')):
            return jsonify({'success': False, 'message': 'Formato de arquivo não suportado'})
        
        # Ler conteúdo do arquivo
        import_data = None
        
        if file.filename.endswith('.zip'):
            import zipfile
            with zipfile.ZipFile(file, 'r') as zip_file:
                # Procurar arquivo templates.json no ZIP
                if 'templates.json' in zip_file.namelist():
                    with zip_file.open('templates.json') as json_file:
                        import_data = json.loads(json_file.read().decode('utf-8'))
                else:
                    return jsonify({'success': False, 'message': 'Arquivo templates.json não encontrado no ZIP'})
        else:
            import_data = json.loads(file.read().decode('utf-8'))
        
        # Validar estrutura do arquivo
        if validar:
            if not isinstance(import_data, dict) or 'templates' not in import_data:
                return jsonify({'success': False, 'message': 'Estrutura do arquivo inválida'})
            
            if not isinstance(import_data['templates'], list):
                return jsonify({'success': False, 'message': 'Lista de templates inválida'})
        
        # Importar templates
        templates_importados = 0
        templates_ignorados = 0
        erros = []
        
        for template_data in import_data['templates']:
            try:
                # Verificar se template já existe
                template_existente = DeclaracaoTemplate.query.filter_by(
                    cliente_id=current_user.id,
                    nome=template_data['nome']
                ).first()
                
                if template_existente and not sobrescrever:
                    templates_ignorados += 1
                    continue
                
                if template_existente and sobrescrever:
                    # Atualizar template existente
                    template_existente.tipo = template_data.get('tipo', template_existente.tipo)
                    template_existente.conteudo_html = template_data.get('conteudo_html', template_existente.conteudo_html)
                    template_existente.ativo = template_data.get('ativo', template_existente.ativo)
                    template_existente.data_atualizacao = datetime.now()
                else:
                    # Criar novo template
                    novo_template = DeclaracaoTemplate(
                        cliente_id=current_user.id,
                        nome=template_data['nome'],
                        tipo=template_data.get('tipo', 'individual'),
                        conteudo_html=template_data.get('conteudo_html', ''),
                        ativo=template_data.get('ativo', True)
                    )
                    db.session.add(novo_template)
                
                templates_importados += 1
                
            except Exception as e:
                erros.append(f"Erro ao importar template '{template_data.get('nome', 'Desconhecido')}': {str(e)}")
        
        db.session.commit()
        
        # Preparar resposta
        resultado = {
            'success': True,
            'message': f'Importação concluída! {templates_importados} template(s) importado(s), {templates_ignorados} ignorado(s).',
            'templates_importados': templates_importados,
            'templates_ignorados': templates_ignorados,
            'erros': erros
        }
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Erro ao importar templates: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})