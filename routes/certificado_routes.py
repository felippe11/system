from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
    after_this_request,
    jsonify,
)
from utils import endpoints

from flask_login import login_required, current_user

from werkzeug.utils import secure_filename
from extensions import db
from models import (
    Oficina,
    CertificadoTemplate,
    Evento,
    Checkin,
    DeclaracaoComparecimento,
)
from models.user import Cliente

from models.certificado import (
    CertificadoTemplateAvancado,
    RegraCertificado,
    SolicitacaoCertificado,
    NotificacaoCertificado,
    DeclaracaoTemplate,
    CertificadoConfig,
    CertificadoParticipante,
    VariavelDinamica,
)
from models.event import ConfiguracaoCertificadoAvancada
from services.pdf_service import gerar_certificado_personalizado  # ajuste conforme a localização

from services.declaracao_service import gerar_declaracao_personalizada

from utils.auth import (
    login_required,
    require_permission,
    require_resource_access,
    role_required,
    cliente_required,
    admin_required,
)



import os
from datetime import datetime
import logging

import json
from sqlalchemy import func


certificado_routes = Blueprint(
    'certificado_routes',
    __name__,
    template_folder="../templates/certificado"
)

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.pdf'}
ALLOWED_MIME_TYPES = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.pdf': 'application/pdf',
}


@certificado_routes.route(
    '/admin/processar_certificados_pendentes',
    methods=['POST'],
)
@login_required
@admin_required
def processar_certificados_pendentes():
    """Processa solicitações de certificados com status pendente."""
    processadas = certificado_service.processar_solicitacoes_pendentes()
    logger.info(
        "Usuário %s processou %d solicitações de certificados",
        current_user.id,
        processadas,
    )
    return jsonify({'processadas': processadas})


@certificado_routes.route('/templates_certificado', methods=['GET', 'POST'])
@login_required

@require_permission('templates.view')

def templates_certificado():
    if request.method == 'POST':
        titulo = request.form['titulo']
        conteudo = request.form['conteudo']
        novo_template = CertificadoTemplate(cliente_id=current_user.id, titulo=titulo, conteudo=conteudo)
        db.session.add(novo_template)
        db.session.commit()
        flash('Template cadastrado com sucesso!', 'success')

    templates = CertificadoTemplate.query.filter_by(cliente_id=current_user.id).all()
    return render_template('certificado/templates_certificado.html', templates=templates)

@certificado_routes.route('/set_template_ativo/<int:template_id>', methods=['POST'])
@login_required

@require_permission('templates.activate')
@require_resource_access('template', 'template_id', 'edit')

def set_template_ativo(template_id):
    CertificadoTemplate.query.filter_by(cliente_id=current_user.id).update({'ativo': False})
    template = CertificadoTemplate.query.get(template_id)
    template.ativo = True
    db.session.commit()
    flash('Template definido como ativo com sucesso!', 'success')
    return redirect(url_for('certificado_routes.templates_certificado'))

@certificado_routes.route('/gerar_certificado_evento', methods=['POST'])
@login_required

@require_permission('certificados.generate')

def gerar_certificado_evento():
    texto_personalizado = request.form.get('texto_personalizado', '')
    oficinas_ids = request.form.getlist('oficinas_selecionadas')

    oficinas = Oficina.query.filter(Oficina.id.in_(oficinas_ids)).all()
    total_horas = sum(int(of.carga_horaria) for of in oficinas)

    # Capturar template ativo
    template = CertificadoTemplate.query.filter_by(cliente_id=current_user.id, ativo=True).first()
    if not template:
        flash('Nenhum template ativo encontrado!', 'danger')
        return redirect(url_for('certificado_routes.dashboard_cliente'))

    pdf_path = gerar_certificado_personalizado(current_user, oficinas, total_horas, texto_personalizado, template.conteudo)
    return send_file(pdf_path, as_attachment=True)

@certificado_routes.route('/salvar_personalizacao_certificado', methods=['POST'])
@login_required

@require_permission('certificados.edit')

def salvar_personalizacao_certificado():
    """Salva personalização do certificado após validar os arquivos enviados."""
    cliente = Cliente.query.get(current_user.id)

    upload_dir = os.path.join('static', 'uploads', 'certificados')
    os.makedirs(upload_dir, exist_ok=True)

    for campo in ['logo_certificado', 'assinatura_certificado', 'fundo_certificado']:
        arquivo = request.files.get(campo)
        if not arquivo or not arquivo.filename:
            continue

        filename = secure_filename(arquivo.filename)
        ext = os.path.splitext(filename)[1].lower()
        mimetype = arquivo.mimetype

        if ext not in ALLOWED_MIME_TYPES or ALLOWED_MIME_TYPES[ext] != mimetype:
            flash(
                'Arquivo inválido para {}. Permitidos: {}'.format(
                    campo.replace('_', ' '), ', '.join(sorted(ALLOWED_EXTENSIONS))
                ),
                'danger',
            )
            return redirect(
                url_for('certificado_routes.upload_personalizacao_certificado')
            )

        path = os.path.join(upload_dir, filename)
        arquivo.save(path)
        setattr(cliente, campo, path)

    cliente.texto_personalizado = request.form.get('texto_personalizado')
    db.session.commit()

    flash('Personalizações salvas com sucesso!', 'success')
    return redirect(url_for('certificado_routes.upload_personalizacao_certificado'))

@certificado_routes.route('/ativar_template_certificado/<int:template_id>', methods=['POST'])
@login_required

@require_permission('templates.activate')
@require_resource_access('template', 'template_id', 'edit')

def ativar_template_certificado(template_id):
    CertificadoTemplate.query.filter_by(cliente_id=current_user.id).update({'ativo': False})
    template = CertificadoTemplate.query.get_or_404(template_id)
    template.ativo = True
    db.session.commit()

    flash('Template ativado com sucesso!', 'success')
    return redirect(url_for('certificado_routes.upload_personalizacao_certificado'))


@certificado_routes.route('/editar_template_certificado/<int:template_id>', methods=['POST'])
@login_required

@require_permission('templates.edit')
@require_resource_access('template', 'template_id', 'edit')

def editar_template_certificado(template_id):
    template = CertificadoTemplate.query.get_or_404(template_id)

    if template.cliente_id != current_user.id:
        flash('Você não tem permissão para editar este template.', 'danger')
        return redirect(url_for('certificado_routes.upload_personalizacao_certificado'))

    novo_titulo = request.form.get('titulo')
    novo_conteudo = request.form.get('conteudo')

    if not novo_titulo or not novo_conteudo:
        flash('Todos os campos são obrigatórios.', 'warning')
        return redirect(url_for('certificado_routes.upload_personalizacao_certificado'))

    template.titulo = novo_titulo
    template.conteudo = novo_conteudo

    db.session.commit()
    flash('Template atualizado com sucesso!', 'success')
    return redirect(url_for('certificado_routes.upload_personalizacao_certificado'))

@certificado_routes.route('/desativar_template_certificado/<int:template_id>', methods=['POST'])
@login_required

@require_permission('templates.deactivate')
@require_resource_access('template', 'template_id', 'edit')

def desativar_template_certificado(template_id):
    template = CertificadoTemplate.query.get_or_404(template_id)

    if template.cliente_id != current_user.id:
        flash('Você não tem permissão para alterar esse template.', 'danger')
        return redirect(url_for('certificado_routes.upload_personalizacao_certificado'))

    template.ativo = False
    db.session.commit()
    flash('Template desativado com sucesso!', 'info')
    return redirect(url_for('certificado_routes.upload_personalizacao_certificado'))

@certificado_routes.route('/upload_personalizacao_certificado', methods=['GET', 'POST'])
@login_required

@require_permission('certificados.create')

def upload_personalizacao_certificado():
    
    cliente = Cliente.query.get(current_user.id)
    templates = CertificadoTemplate.query.filter_by(cliente_id=current_user.id).all()

    if request.method == 'POST':
        logo_file = request.files.get('logo_certificado')
        fundo_file = request.files.get('fundo_certificado')
        ass_file = request.files.get('assinatura_certificado')

        # Exemplo de pasta
        pasta_uploads = os.path.join('uploads', 'personalizacao')
        os.makedirs(pasta_uploads, exist_ok=True)

        # Se o cliente enviar algo, salvamos e atualizamos o path
        if logo_file and logo_file.filename:
            filename_logo = secure_filename(logo_file.filename)
            caminho_logo = os.path.join(pasta_uploads, filename_logo)
            logo_file.save(caminho_logo)
            current_user.logo_certificado = caminho_logo  # Salva no banco

        if fundo_file and fundo_file.filename:
            filename_fundo = secure_filename(fundo_file.filename)
            caminho_fundo = os.path.join(pasta_uploads, filename_fundo)
            fundo_file.save(caminho_fundo)
            current_user.fundo_certificado = caminho_fundo

        if ass_file and ass_file.filename:
            filename_ass = secure_filename(ass_file.filename)
            caminho_ass = os.path.join(pasta_uploads, filename_ass)
            ass_file.save(caminho_ass)
            current_user.assinatura_certificado = caminho_ass

        db.session.commit()
        flash("Personalização salva com sucesso!", "success")
        return redirect(url_for('certificado_routes.dashboard_cliente'))

    return render_template('upload_personalizacao_cert.html', templates=templates, cliente=cliente)


@certificado_routes.route('/preview_certificado', methods=['GET', 'POST'])
@login_required

@require_permission('certificados.view')

def preview_certificado():
    """Gera um PDF de exemplo para visualizar o certificado."""

    class UsuarioExemplo:
        id = 0
        nome = "Participante Exemplo"

    class OficinaExemplo:
        titulo = "Oficina Exemplo"
        carga_horaria = "4"
        datas = [datetime.now()]

    cliente = Cliente.query.get(current_user.id)
    template = CertificadoTemplate.query.filter_by(cliente_id=current_user.id, ativo=True).first()
    template_conteudo = template.conteudo if template else None

    temp_files = []

    if request.method == "POST":
        import tempfile
        from types import SimpleNamespace

        texto_personalizado = request.form.get("texto_personalizado", "")

        caminhos = {}
        for campo in ["logo_certificado", "assinatura_certificado", "fundo_certificado"]:
            arquivo = request.files.get(campo)
            if arquivo and arquivo.filename:
                extensao = os.path.splitext(arquivo.filename)[1]
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=extensao)
                arquivo.save(tmp.name)
                caminhos[campo] = tmp.name
                temp_files.append(tmp.name)
            else:
                caminhos[campo] = getattr(cliente, campo)

        temp_cliente = SimpleNamespace(
            logo_certificado=caminhos.get("logo_certificado"),
            assinatura_certificado=caminhos.get("assinatura_certificado"),
            fundo_certificado=caminhos.get("fundo_certificado"),
            texto_personalizado=texto_personalizado,
        )
    else:
        texto_personalizado = ""
        temp_cliente = cliente

    pdf_path = gerar_certificado_personalizado(
        UsuarioExemplo(),
        [OficinaExemplo()],
        4,
        texto_personalizado,
        template_conteudo,
        temp_cliente,
    )

    @after_this_request
    def cleanup(response):
        # Testes lidam com remoção do arquivo gerado
        for f in temp_files:
            try:
                os.remove(f)
            except OSError as exc:
                logger.exception("Erro ao remover arquivo temporário %s", f)
        return response
    
    if pdf_path:
        return send_file(pdf_path, as_attachment=True, download_name="preview_certificado.pdf")
    else:
        flash('Erro ao gerar preview do certificado', 'error')
        return redirect(url_for('certificado_routes.templates_certificado'))


# Rotas para Editor Avançado de Certificados

@certificado_routes.route('/editor_avancado')
@login_required
@require_permission('templates.create')
def editor_avancado():
    """Página do editor avançado de certificados."""
    template_id = request.args.get('template_id')
    template = None
    
    if template_id:
        template = CertificadoTemplateAvancado.query.filter_by(
            id=template_id, cliente_id=current_user.id
        ).first()
    
    return render_template('certificado/editor_avancado.html', template=template)


@certificado_routes.route('/salvar_template_avancado', methods=['POST'])
@login_required
@require_permission('templates.create')
def salvar_template_avancado():
    """Salvar template avançado criado no editor."""
    try:
        data = request.get_json()
        
        titulo = data.get('titulo')
        orientacao = data.get('orientacao', 'landscape')
        elements = data.get('elements', [])
        html = data.get('html', '')
        
        if not titulo:
            return {'success': False, 'message': 'Título é obrigatório'}
        
        # Criar ou atualizar template
        template_id = data.get('template_id')
        if template_id:
            template = CertificadoTemplateAvancado.query.filter_by(
                id=template_id, cliente_id=current_user.id
            ).first()
            if not template:
                return {'success': False, 'message': 'Template não encontrado'}
        else:
            template = CertificadoTemplateAvancado(cliente_id=current_user.id)
        
        template.titulo = titulo
        template.orientacao = orientacao
        template.conteudo = html
        template.layout_config = {
            'elements': elements,
            'canvas_html': html
        }
        
        if not template_id:
            db.session.add(template)
        
        db.session.commit()
        
        return {'success': True, 'template_id': template.id}
        
    except Exception as e:
        logger.exception("Erro ao salvar template avançado")
        return {'success': False, 'message': str(e)}


@certificado_routes.route('/salvar_variavel', methods=['POST'])
@login_required
@require_permission('templates.edit')
def salvar_variavel():
    """Salvar nova variável dinâmica."""
    try:
        data = request.get_json()
        
        nome = data.get('nome', '').upper().strip()
        descricao = data.get('descricao', '')
        valor_padrao = data.get('valor_padrao', '')
        tipo = data.get('tipo', 'texto')
        
        if not nome:
            return {'success': False, 'message': 'Nome da variável é obrigatório'}
        
        # Verificar se já existe
        existing = VariavelDinamica.query.filter_by(
            cliente_id=current_user.id, nome=nome
        ).first()
        
        if existing:
            return {'success': False, 'message': 'Variável já existe'}
        
        variavel = VariavelDinamica(
            cliente_id=current_user.id,
            nome=nome,
            descricao=descricao,
            valor_padrao=valor_padrao,
            tipo=tipo
        )
        
        db.session.add(variavel)
        db.session.commit()
        
        return {'success': True, 'variavel_id': variavel.id}
        
    except Exception as e:
        logger.exception("Erro ao salvar variável")
        return {'success': False, 'message': str(e)}


@certificado_routes.route('/variaveis_dinamicas', methods=['GET', 'POST'])
@login_required
@require_permission('templates.view')
def variaveis_dinamicas():
    """Gerenciar variáveis dinâmicas do cliente."""
    if request.method == 'POST':
        # Criar nova variável
        try:
            data = request.get_json() if request.is_json else request.form
            
            nome = data.get('nome', '').upper().strip()
            descricao = data.get('descricao', '')
            valor_padrao = data.get('valor_padrao', '')
            tipo = data.get('tipo', 'texto')
            opcoes = data.get('opcoes', [])
            
            if not nome:
                return {'success': False, 'message': 'Nome da variável é obrigatório'}
            
            # Verificar se já existe
            existing = VariavelDinamica.query.filter_by(
                cliente_id=current_user.id, nome=nome
            ).first()
            
            if existing:
                return {'success': False, 'message': 'Variável já existe'}
            
            variavel = VariavelDinamica(
                cliente_id=current_user.id,
                nome=nome,
                descricao=descricao,
                valor_padrao=valor_padrao,
                tipo=tipo,
                opcoes=opcoes if tipo == 'lista' else None
            )
            
            db.session.add(variavel)
            db.session.commit()
            
            if request.is_json:
                return {'success': True, 'variavel_id': variavel.id}
            else:
                flash('Variável criada com sucesso!', 'success')
                return redirect(url_for('certificado_routes.variaveis_dinamicas'))
                
        except Exception as e:
            logger.exception("Erro ao criar variável")
            if request.is_json:
                return {'success': False, 'message': str(e)}
            else:
                flash(f'Erro ao criar variável: {str(e)}', 'error')
                return redirect(url_for('certificado_routes.variaveis_dinamicas'))
    
    # GET - Listar variáveis
    variaveis = VariavelDinamica.query.filter_by(
        cliente_id=current_user.id, ativo=True
    ).order_by(VariavelDinamica.data_criacao.desc()).all()
    
    if request.headers.get('Accept') == 'application/json':
        return {
            'variaveis': [{
                'id': v.id,
                'nome': v.nome,
                'descricao': v.descricao,
                'valor_padrao': v.valor_padrao,
                'tipo': v.tipo,
                'opcoes': v.opcoes
            } for v in variaveis]
        }
    
    return render_template('certificado/variaveis_dinamicas.html', variaveis=variaveis)


@certificado_routes.route('/importar_variaveis_dinamicas', methods=['POST'])
@login_required
@require_permission('templates.edit')
def importar_variaveis_dinamicas():
    """Importar variáveis dinâmicas de um arquivo JSON."""
    try:
        data = request.get_json()
        
        if not data or 'variaveis' not in data:
            return jsonify({'success': False, 'message': 'Dados inválidos'}), 400
        
        variaveis_importadas = 0
        variaveis_ignoradas = 0
        erros = []
        
        for variavel_data in data['variaveis']:
            try:
                # Verificar se já existe uma variável com o mesmo nome
                nome = variavel_data.get('nome', '').upper().strip()
                if not nome:
                    erros.append('Nome da variável é obrigatório')
                    continue
                
                variavel_existente = VariavelDinamica.query.filter_by(
                    nome=nome,
                    cliente_id=current_user.id
                ).first()
                
                if variavel_existente:
                    variaveis_ignoradas += 1
                    continue
                
                # Criar nova variável
                nova_variavel = VariavelDinamica(
                    nome=nome,
                    descricao=variavel_data.get('descricao', ''),
                    valor_padrao=variavel_data.get('valor_padrao', ''),
                    tipo=variavel_data.get('tipo', 'texto'),
                    opcoes=variavel_data.get('opcoes') if variavel_data.get('tipo') == 'lista' else None,
                    cliente_id=current_user.id
                )
                
                db.session.add(nova_variavel)
                variaveis_importadas += 1
                
            except Exception as e:
                erros.append(f"Erro ao importar variável '{variavel_data.get('nome', 'sem nome')}': {str(e)}")
        
        db.session.commit()
        
        mensagem = f'{variaveis_importadas} variáveis importadas com sucesso'
        if variaveis_ignoradas > 0:
            mensagem += f', {variaveis_ignoradas} ignoradas (já existem)'
        if erros:
            mensagem += f', {len(erros)} erros'
        
        return jsonify({
            'success': True,
            'message': mensagem,
            'importadas': variaveis_importadas,
            'ignoradas': variaveis_ignoradas,
            'erros': erros
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao importar variáveis dinâmicas: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro interno do sistema'}), 500


@certificado_routes.route('/variaveis_dinamicas/<int:variavel_id>', methods=['PUT', 'DELETE'])
@login_required
@require_permission('templates.edit')
@require_resource_access('variavel', 'variavel_id', 'edit')
def gerenciar_variavel_dinamica(variavel_id):
    """Editar ou excluir variável dinâmica."""
    variavel = VariavelDinamica.query.filter_by(
        id=variavel_id, cliente_id=current_user.id
    ).first_or_404()
    
    if request.method == 'PUT':
        try:
            data = request.get_json()
            
            variavel.nome = data.get('nome', variavel.nome).upper().strip()
            variavel.descricao = data.get('descricao', variavel.descricao)
            variavel.valor_padrao = data.get('valor_padrao', variavel.valor_padrao)
            variavel.tipo = data.get('tipo', variavel.tipo)
            variavel.opcoes = data.get('opcoes') if data.get('tipo') == 'lista' else None
            
            db.session.commit()
            
            return {'success': True, 'message': 'Variável atualizada com sucesso'}
            
        except Exception as e:
            logger.exception("Erro ao atualizar variável")
            return {'success': False, 'message': str(e)}
    
    elif request.method == 'DELETE':
        try:
            variavel.ativo = False
            db.session.commit()
            
            return {'success': True, 'message': 'Variável excluída com sucesso'}
            
        except Exception as e:
            logger.exception("Erro ao excluir variável")
            return {'success': False, 'message': str(e)}


@certificado_routes.route('/templates_simples')
@login_required
@cliente_required
def templates_simples():
    """Listar templates simples de certificados."""
    templates = CertificadoTemplate.query.filter_by(
        cliente_id=current_user.id
    ).order_by(CertificadoTemplate.data_criacao.desc()).all()
    
    return render_template('certificado/templates_certificado.html', templates=templates)

@certificado_routes.route('/templates_avancados')
@login_required
@cliente_required
def templates_avancados():
    """Listar templates avançados de certificados."""
    templates = CertificadoTemplateAvancado.query.filter_by(
        cliente_id=current_user.id
    ).order_by(CertificadoTemplateAvancado.data_criacao.desc()).all()
    
    return render_template('certificado/templates_avancados.html', templates=templates)

@certificado_routes.route('/config_criterios')
@login_required
@cliente_required
def config_criterios():
    """Configurar critérios de certificados."""
    eventos = Evento.query.filter_by(cliente_id=current_user.id).all()
    return render_template('certificado/config_criterios.html', eventos=eventos)


@certificado_routes.route('/config_geral')
@login_required
@cliente_required
def config_geral():
    """Configuração geral de certificados."""
    try:
        templates = CertificadoTemplate.query.filter_by(cliente_id=current_user.cliente_id).all()
        templates_avancados = CertificadoTemplateAvancado.query.filter_by(cliente_id=current_user.cliente_id).all()
        eventos = Evento.query.filter_by(cliente_id=current_user.cliente_id).all()
        
        return render_template('certificado/config_geral.html', 
                             templates=templates, 
                             templates_avancados=templates_avancados,
                             eventos=eventos)
    except Exception as e:
        flash(f'Erro ao carregar configurações: {str(e)}', 'error')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))

@certificado_routes.route('/templates_personalizaveis')
@login_required
@require_permission('templates.view')
def templates_personalizaveis():
    """Lista todos os templates personalizáveis com suas variáveis dinâmicas"""
    templates = CertificadoTemplateAvancado.query.filter_by(
        cliente_id=current_user.id,
        ativo=True
    ).all()
    
    variaveis = VariavelDinamica.query.filter_by(
        cliente_id=current_user.id,
        ativo=True
    ).all()
    
    return render_template('certificado/templates_personalizaveis.html', 
                         templates=templates, variaveis=variaveis)

@certificado_routes.route('/criar_template_personalizado', methods=['GET', 'POST'])
@login_required
@require_permission('templates.create')
def criar_template_personalizado():
    """Cria um novo template personalizado com variáveis dinâmicas"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form.to_dict()
            
            # Validação básica
            if not data.get('titulo') or not data.get('conteudo'):
                return {'success': False, 'message': 'Título e conteúdo são obrigatórios'}, 400
            
            # Criar novo template
            template = CertificadoTemplateAvancado(
                cliente_id=current_user.id,
                nome=data['titulo'],
                descricao=data.get('descricao', ''),
                tipo=data.get('categoria', 'certificado'),
                conteudo_html=data['conteudo'],
                variaveis_disponiveis=json.dumps(data.get('variaveis_selecionadas', [])),
                ativo=True
            )
            
            db.session.add(template)
            db.session.commit()
            
            if request.is_json:
                return {'success': True, 'message': 'Template criado com sucesso!', 'template_id': template.id}
            else:
                flash('Template personalizado criado com sucesso!', 'success')
                return redirect(url_for('certificado_routes.templates_personalizaveis'))
                
        except Exception as e:
            logger.error(f"Erro ao criar template personalizado: {str(e)}")
            db.session.rollback()
            if request.is_json:
                return {'success': False, 'message': 'Erro interno do servidor'}, 500
            else:
                flash('Erro ao criar template personalizado', 'error')
                return redirect(url_for('certificado_routes.templates_personalizaveis'))
    
    # GET - Mostrar formulário
    variaveis = VariavelDinamica.query.filter_by(
        cliente_id=current_user.id,
        ativo=True
    ).all()
    
    return render_template('certificado/criar_template_personalizado.html', variaveis=variaveis)

@certificado_routes.route('/editar_template_personalizado/<int:template_id>', methods=['GET', 'POST'])
@login_required
@require_permission('templates.edit')
@require_resource_access('template', 'template_id', 'edit')
def editar_template_personalizado(template_id):
    """Edita um template personalizado existente"""
    template = CertificadoTemplateAvancado.query.filter_by(
        id=template_id,
        cliente_id=current_user.id
    ).first_or_404()
    
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form.to_dict()
            
            # Atualizar template
            template.nome = data.get('titulo', template.nome)
            template.descricao = data.get('descricao', template.descricao)
            template.tipo = data.get('categoria', template.tipo)
            template.conteudo_html = data.get('conteudo', template.conteudo_html)
            template.variaveis_disponiveis = json.dumps(data.get('variaveis_selecionadas', json.loads(template.variaveis_disponiveis or '[]')))
            template.data_atualizacao = datetime.utcnow()
            
            db.session.commit()
            
            if request.is_json:
                return {'success': True, 'message': 'Template atualizado com sucesso!'}
            else:
                flash('Template personalizado atualizado com sucesso!', 'success')
                return redirect(url_for('certificado_routes.templates_personalizaveis'))
                
        except Exception as e:
            logger.error(f"Erro ao editar template personalizado: {str(e)}")
            db.session.rollback()
            if request.is_json:
                return {'success': False, 'message': 'Erro interno do servidor'}, 500
            else:
                flash('Erro ao editar template personalizado', 'error')
                return redirect(url_for('certificado_routes.templates_personalizaveis'))
    
    # GET - Mostrar formulário de edição
    variaveis = VariavelDinamica.query.filter_by(
        cliente_id=current_user.id,
        ativo=True
    ).all()
    
    # Converter JSON strings para objetos Python
    template_data = {
        'id': template.id,
        'titulo': template.titulo,
        'conteudo': template.conteudo,
        'layout_config': json.loads(template.layout_config or '{}'),
        'elementos_visuais': json.loads(template.elementos_visuais or '{}'),
        'variaveis_selecionadas': json.loads(template.variaveis_dinamicas or '[]'),
        'orientacao': template.orientacao,
        'tamanho_pagina': template.tamanho_pagina,
        'margem_config': json.loads(template.margem_config or '{}')
    }
    
    return render_template('certificado/editar_template_personalizado.html', 
                         template=template_data, variaveis=variaveis)

@certificado_routes.route('/aplicar_variaveis_template', methods=['POST'])
@login_required
@require_permission('templates.edit')
def aplicar_variaveis_template():
    """Aplica variáveis dinâmicas a um template e retorna o conteúdo processado"""
    try:
        data = request.get_json()
        template_id = data.get('template_id')
        valores_variaveis = data.get('valores_variaveis', {})
        
        if not template_id:
            return {'success': False, 'message': 'ID do template é obrigatório'}, 400
        
        template = CertificadoTemplateAvancado.query.filter_by(
            id=template_id,
            cliente_id=current_user.id
        ).first_or_404()
        
        # Processar conteúdo com variáveis
        conteudo_processado = template.conteudo
        
        # Substituir variáveis no conteúdo
        for nome_variavel, valor in valores_variaveis.items():
            placeholder = f"{{{nome_variavel}}}"
            conteudo_processado = conteudo_processado.replace(placeholder, str(valor))
        
        # Buscar variáveis não preenchidas
        variaveis_template = json.loads(template.variaveis_dinamicas or '[]')
        variaveis_nao_preenchidas = []
        
        for var_id in variaveis_template:
            variavel = VariavelDinamica.query.get(var_id)
            if variavel and f"{{{variavel.nome}}}" in conteudo_processado:
                if variavel.nome not in valores_variaveis:
                    # Usar valor padrão se disponível
                    if variavel.valor_padrao:
                        conteudo_processado = conteudo_processado.replace(
                            f"{{{variavel.nome}}}", 
                            str(variavel.valor_padrao)
                        )
                    else:
                        variaveis_nao_preenchidas.append(variavel.nome)
        
        return {
            'success': True,
            'conteudo_processado': conteudo_processado,
            'variaveis_nao_preenchidas': variaveis_nao_preenchidas
        }
        
    except Exception as e:
        logger.error(f"Erro ao aplicar variáveis ao template: {str(e)}")
        return {'success': False, 'message': 'Erro interno do servidor'}, 500


@certificado_routes.route('/excluir_template_avancado/<int:template_id>', methods=['POST'])
@login_required
@require_permission('templates.delete')
@require_resource_access('template', 'template_id', 'delete')
def excluir_template_avancado(template_id):
    """Excluir template avançado."""
    template = CertificadoTemplateAvancado.query.filter_by(
        id=template_id, cliente_id=current_user.id
    ).first()
    
    if not template:
        flash('Template não encontrado', 'error')
        return redirect(url_for('certificado_routes.templates_avancados'))
    
    db.session.delete(template)
    db.session.commit()
    
    flash('Template excluído com sucesso', 'success')
    return redirect(url_for('certificado_routes.templates_avancados'))


@certificado_routes.route('/ativar_template_avancado/<int:template_id>', methods=['POST'])
@login_required
@require_permission('templates.activate')
@require_resource_access('template', 'template_id', 'edit')
def ativar_template_avancado(template_id):
    """Ativar template avançado."""
    # Desativar todos os templates
    CertificadoTemplateAvancado.query.filter_by(
        cliente_id=current_user.id
    ).update({'ativo': False})
    
    # Ativar o selecionado
    template = CertificadoTemplateAvancado.query.filter_by(
        id=template_id, cliente_id=current_user.id
    ).first()
    
    if template:
        template.ativo = True
        db.session.commit()
        flash('Template ativado com sucesso', 'success')
    else:
        flash('Template não encontrado', 'error')
    
    return redirect(url_for('certificado_routes.templates_avancados'))


@certificado_routes.route('/configurar_certificados/<int:evento_id>')
@login_required
@require_permission('configuracoes.view')
@require_resource_access('evento', 'evento_id', 'view')
def configurar_certificados(evento_id):
    """Configurar opções avançadas de certificados para um evento."""
    from models.event import Evento
    
    evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first()
    if not evento:
        flash('Evento não encontrado', 'error')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))
    
    config = ConfiguracaoCertificadoAvancada.query.filter_by(
        evento_id=evento_id, cliente_id=current_user.id
    ).first()
    
    templates = CertificadoTemplateAvancado.query.filter_by(
        cliente_id=current_user.id
    ).all()
    
    return render_template('certificado/configurar_certificados.html', 
                         evento=evento, config=config, templates=templates)


@certificado_routes.route('/salvar_configuracao_certificados', methods=['POST'])
@login_required
@require_permission('configuracoes.edit')
def salvar_configuracao_certificados():
    """Salvar configurações avançadas de certificados."""
    try:
        evento_id = request.form.get('evento_id')
        
        config = ConfiguracaoCertificadoAvancada.query.filter_by(
            evento_id=evento_id, cliente_id=current_user.id
        ).first()
        
        if not config:
            config = ConfiguracaoCertificadoAvancada(
                evento_id=evento_id, cliente_id=current_user.id
            )
            db.session.add(config)
        
        # Atualizar configurações básicas
        config.liberacao_individual = 'liberacao_individual' in request.form
        config.liberacao_geral = 'liberacao_geral' in request.form
        config.liberacao_simultanea = 'liberacao_simultanea' in request.form
        config.incluir_atividades_sem_inscricao = 'incluir_atividades_sem_inscricao' in request.form
        config.carga_horaria_minima = int(request.form.get('carga_horaria_minima', 0))
        config.percentual_presenca_minimo = int(request.form.get('percentual_presenca_minimo', 0))
        config.acesso_participante = 'acesso_participante' in request.form
        config.acesso_admin = 'acesso_admin' in request.form
        config.acesso_cliente = 'acesso_cliente' in request.form
        
        # Novas configurações do sistema flexível
        config.liberacao_automatica = 'liberacao_automatica' in request.form
        config.permitir_solicitacao_manual = 'permitir_solicitacao_manual' in request.form
        config.notificar_liberacao = 'notificar_liberacao' in request.form
        config.exigir_checkin_minimo = 'exigir_checkin_minimo' in request.form
        config.validar_oficinas_obrigatorias = 'validar_oficinas_obrigatorias' in request.form
        config.min_checkins = int(request.form.get('min_checkins', 1))
        config.min_oficinas_participadas = int(request.form.get('min_oficinas_participadas', 0))
        config.exigir_atividades_obrigatorias = 'exigir_atividades_obrigatorias' in request.form
        config.requer_aprovacao_manual = 'requer_aprovacao_manual' in request.form
        config.aprovacao_automatica_criterios = 'aprovacao_automatica_criterios' in request.form
        
        # Prazos
        prazo_liberacao_automatica = request.form.get('prazo_liberacao_automatica')
        prazo_solicitacao_manual = request.form.get('prazo_solicitacao_manual')
        
        if prazo_liberacao_automatica:
            config.prazo_liberacao_automatica = datetime.strptime(prazo_liberacao_automatica, '%Y-%m-%dT%H:%M')
        else:
            config.prazo_liberacao_automatica = None
            
        if prazo_solicitacao_manual:
            config.prazo_solicitacao_manual = datetime.strptime(prazo_solicitacao_manual, '%Y-%m-%dT%H:%M')
        else:
            config.prazo_solicitacao_manual = None
        
        # Templates
        template_individual_id = request.form.get('template_individual_id')
        template_geral_id = request.form.get('template_geral_id')
        
        config.template_individual_id = template_individual_id if template_individual_id else None
        config.template_geral_id = template_geral_id if template_geral_id else None
        
        db.session.commit()
        
        flash('Configurações salvas com sucesso', 'success')
        return redirect(url_for('certificado_routes.configurar_certificados', evento_id=evento_id))
        
    except Exception as e:
        logger.exception("Erro ao salvar configurações")
        flash('Erro ao salvar configurações', 'error')
        return redirect(url_for('certificado_routes.configurar_certificados', evento_id=evento_id))

    return send_file(pdf_path, mimetype="application/pdf")


@certificado_routes.route('/gerar_certificado_geral_evento/<int:evento_id>', methods=['GET'])
@login_required
@require_permission('certificados.generate')
@require_resource_access('evento', 'evento_id', 'view')
def gerar_certificado_geral_evento(evento_id):
    """Gera certificado geral do evento com cálculo automático de carga horária."""
    from models.event import Evento
    from models import Checkin
    from services.certificado_service import verificar_criterios_certificado
    
    evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first()
    if not evento:
        flash('Evento não encontrado', 'error')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))
    
    # Verificar se há configuração específica para este evento
    config = ConfiguracaoCertificadoAvancada.query.filter_by(
        evento_id=evento_id, cliente_id=current_user.id
    ).first()
    
    if not config or not config.liberacao_geral:
        flash('Certificado geral não está habilitado para este evento', 'warning')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))
    
    # Buscar participantes que fizeram check-in no evento
    participantes_query = db.session.query(
        Checkin.usuario_id
    ).filter(
        Checkin.evento_id == evento_id
    ).distinct()
    
    participantes_ids = [p.usuario_id for p in participantes_query.all()]
    
    if not participantes_ids:
        flash('Nenhum participante encontrado para este evento', 'warning')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))
    
    # Gerar certificados para todos os participantes elegíveis
    certificados_gerados = []
    
    for usuario_id in participantes_ids:
        # Verificar critérios de certificado
        ok, pendencias = verificar_criterios_certificado(usuario_id, evento_id)
        
        if ok:
            # Calcular atividades participadas
            atividades_participadas = certificado_service.calcular_atividades_participadas(
                usuario_id, evento_id, config
            )
            
            if atividades_participadas['total_horas'] >= (config.carga_horaria_minima or 0):
                # Gerar certificado
                from models.user import Usuario
                usuario = Usuario.query.get(usuario_id)
                
                template = None
                if config.template_geral_id:
                    template = CertificadoTemplateAvancado.query.get(config.template_geral_id)
                
                if not template:
                    template = CertificadoTemplate.query.filter_by(
                        cliente_id=current_user.id, ativo=True
                    ).first()
                
                if template:
                    pdf_path = gerar_certificado_geral_personalizado(
                        usuario, evento, atividades_participadas, template, current_user
                    )
                    certificados_gerados.append({
                        'usuario': usuario.nome,
                        'path': pdf_path
                    })
    
    if certificados_gerados:
        # Criar ZIP com todos os certificados
        import zipfile
        import tempfile
        
        zip_path = os.path.join(tempfile.gettempdir(), f'certificados_evento_{evento_id}.zip')
        
        with zipfile.ZipFile(zip_path, 'w') as zip_file:
            for cert in certificados_gerados:
                if os.path.exists(cert['path']):
                    zip_file.write(cert['path'], f"certificado_{cert['usuario']}.pdf")
        
        flash(f'{len(certificados_gerados)} certificados gerados com sucesso', 'success')
        return send_file(zip_path, as_attachment=True, download_name=f'certificados_{evento.nome}.zip')
    else:
        flash('Nenhum participante atende aos critérios para certificado', 'warning')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))


@certificado_routes.route('/preview_certificado_geral/<int:evento_id>')
@login_required
@require_permission('certificados.view')
@require_resource_access('evento', 'evento_id', 'view')
def preview_certificado_geral(evento_id):
    """Visualizar preview do certificado geral do evento."""
    from models.event import Evento
    
    evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first()
    if not evento:
        flash('Evento não encontrado', 'error')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))
    
    config = ConfiguracaoCertificadoAvancada.query.filter_by(
        evento_id=evento_id, cliente_id=current_user.id
    ).first()
    
    # Criar dados de exemplo
    class UsuarioExemplo:
        id = 0
        nome = "Participante Exemplo"
    
    atividades_exemplo = {
        'oficinas': [
            {'titulo': 'Oficina Exemplo 1', 'carga_horaria': 4, 'datas': ['01/01/2024']},
            {'titulo': 'Oficina Exemplo 2', 'carga_horaria': 6, 'datas': ['02/01/2024']}
        ],
        'atividades_sem_inscricao': [
            {'titulo': 'Palestra Exemplo', 'carga_horaria': 2, 'datas': ['03/01/2024']}
        ],
        'total_horas': 12,
        'total_atividades': 3
    }
    
    template = None
    if config and config.template_geral_id:
        template = CertificadoTemplateAvancado.query.get(config.template_geral_id)
    
    if not template:
        template = CertificadoTemplate.query.filter_by(
            cliente_id=current_user.id, ativo=True
        ).first()
    
    if template:
        pdf_path = gerar_certificado_geral_personalizado(
            UsuarioExemplo(), evento, atividades_exemplo, template, current_user
        )
        return send_file(pdf_path, mimetype="application/pdf")
    else:
        flash('Nenhum template encontrado', 'error')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))


@certificado_routes.route('/configuracoes_evento/<int:evento_id>')
@login_required
@require_permission('configuracoes.view')
@require_resource_access('evento', 'evento_id', 'view')
def configuracoes_evento(evento_id):
    """Retorna as configurações de certificado para um evento específico."""
    from models.event import Evento
    
    evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first()
    if not evento:
        return {'success': False, 'message': 'Evento não encontrado'}
    
    config = ConfiguracaoCertificadoAvancada.query.filter_by(
        evento_id=evento_id, cliente_id=current_user.id
    ).first()
    
    # Gerar HTML das configurações
    liberacao_html = render_template('certificado/config_liberacao.html', config=config)
    criterios_html = render_template('certificado/config_criterios.html', config=config)
    geral_html = render_template('certificado/config_geral.html', config=config, evento=evento)
    
    return {
        'success': True,
        'liberacao_html': liberacao_html,
        'criterios_html': criterios_html,
        'geral_html': geral_html
    }


@certificado_routes.route('/historico_emissoes', methods=['GET', 'POST'])
@login_required
@require_permission('relatorios.view')
def historico_emissoes():
    """Retorna o histórico de emissões de certificados e declarações."""
    if request.method == 'GET':
        # Renderizar página de histórico
        return render_template('certificado/historico_emissoes.html')
    
    # POST - retornar dados filtrados
    filtros = request.get_json()
    
    # Implementar consulta do histórico baseado nos filtros
    # Por enquanto, retornar dados de exemplo
    historico_html = render_template('certificado/historico_table.html', historico=[])
    
    return {
        'success': True,
        'html': historico_html
    }


def gerar_certificado_geral_personalizado(usuario, evento, atividades, template, cliente):
    """Gera certificado geral personalizado com todas as atividades do evento."""
    import os
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import Paragraph, Frame
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    
    # Configuração do arquivo de saída
    pdf_filename = f"certificado_geral_{usuario.id}_{evento.id}.pdf"
    pdf_path = os.path.join("static/certificados", pdf_filename)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    
    # Criação do canvas
    c = canvas.Canvas(pdf_path, pagesize=landscape(A4))
    width, height = landscape(A4)
    
    # Determinar conteúdo do certificado
    if hasattr(template, 'conteudo') and template.conteudo:
        conteudo_final = template.conteudo
    elif hasattr(template, 'design_json') and template.design_json:
        # Template avançado - usar design JSON
        conteudo_final = gerar_conteudo_template_avancado(template.design_json, usuario, evento, atividades)
    else:
        conteudo_final = (
            "Certificamos que {NOME_PARTICIPANTE} participou do evento {NOME_EVENTO}, "
            "realizando {TOTAL_ATIVIDADES} atividades com carga horária total de {CARGA_HORARIA} horas. "
            "Atividades realizadas: {LISTA_ATIVIDADES}."
        )
    
    # Substituir variáveis
    lista_atividades = ', '.join([
        ativ['titulo'] for ativ in atividades['oficinas'] + atividades['atividades_sem_inscricao']
    ])
    
    conteudo_final = conteudo_final.replace("{NOME_PARTICIPANTE}", usuario.nome)\
                                   .replace("{NOME_EVENTO}", evento.nome)\
                                   .replace("{CARGA_HORARIA}", str(atividades['total_horas']))\
                                   .replace("{TOTAL_ATIVIDADES}", str(atividades['total_atividades']))\
                                   .replace("{LISTA_ATIVIDADES}", lista_atividades)\
                                   .replace("{DATA_EVENTO}", evento.data_inicio.strftime('%d/%m/%Y') if evento.data_inicio else '')
    
    # Renderizar certificado
    # 1. Fundo
    if hasattr(cliente, 'fundo_certificado') and cliente.fundo_certificado:
        fundo_path = os.path.join('static', cliente.fundo_certificado)
        if os.path.exists(fundo_path):
            fundo = ImageReader(fundo_path)
            c.drawImage(fundo, 0, 0, width=width, height=height)
    
    # 2. Título
    c.setFont("Helvetica-Bold", 24)
    titulo = "CERTIFICADO DE PARTICIPAÇÃO"
    titulo_largura = c.stringWidth(titulo, "Helvetica-Bold", 24)
    c.drawString((width - titulo_largura) / 2, height * 0.75, titulo)
    
    # 3. Conteúdo
    styles = getSampleStyleSheet()
    style = ParagraphStyle(
        'CertificadoStyle',
        parent=styles['Normal'],
        fontSize=14,
        leading=20,
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    # Criar frame para o texto
    frame = Frame(width * 0.1, height * 0.3, width * 0.8, height * 0.3, 
                  leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0)
    
    # Criar parágrafo
    para = Paragraph(conteudo_final, style)
    frame.addFromList([para], c)
    
    # 4. Logo (se disponível)
    if hasattr(cliente, 'logo_certificado') and cliente.logo_certificado:
        logo_path = os.path.join('static', cliente.logo_certificado)
        if os.path.exists(logo_path):
            logo = ImageReader(logo_path)
            c.drawImage(logo, width * 0.05, height * 0.05, width=100, height=100, preserveAspectRatio=True)
    
    # 5. Data de emissão
    c.setFont("Helvetica", 10)
    data_emissao = f"Emitido em: {datetime.now().strftime('%d/%m/%Y')}"
    c.drawString(width * 0.7, height * 0.1, data_emissao)
    
    c.save()
    return pdf_path


@certificado_routes.route('/exportar_importar')
@login_required
@require_permission('templates.export_import')
def exportar_importar():
    """Página para exportar e importar templates de certificados"""
    templates = CertificadoTemplateAvancado.query.filter_by(cliente_id=current_user.id).all()
    return render_template('certificado/exportar_importar.html', templates=templates)


@certificado_routes.route('/exportar', methods=['POST'])
@login_required
@require_permission('templates.export')
def exportar_templates():
    """Exportar templates de certificados selecionados"""
    try:
        data = request.get_json()
        template_ids = data.get('template_ids', [])
        formato = data.get('formato', 'json')
        incluir_metadados = data.get('incluir_metadados', True)
        incluir_variaveis = data.get('incluir_variaveis', True)
        
        if not template_ids:
            return {'success': False, 'message': 'Nenhum template selecionado'}, 400
        
        # Buscar templates
        templates = CertificadoTemplateAvancado.query.filter(
            CertificadoTemplateAvancado.id.in_(template_ids),
            CertificadoTemplateAvancado.cliente_id == current_user.id
        ).all()
        
        if not templates:
            return {'success': False, 'message': 'Nenhum template encontrado'}, 404
        
        # Preparar dados para exportação
        export_data = {
            'tipo': 'certificados',
            'versao': '1.0',
            'data_exportacao': datetime.now().isoformat(),
            'templates': []
        }
        
        if incluir_metadados:
            export_data['metadados'] = {
                'cliente_id': current_user.id,
                'total_templates': len(templates)
            }
        
        for template in templates:
            template_data = {
                'nome': template.nome,
                'tipo': template.tipo,
                'conteudo_html': template.conteudo_html,
                'conteudo_css': template.conteudo_css,
                'ativo': template.ativo,
                'padrao': template.padrao,
                'descricao': template.descricao,
                'orientacao': template.orientacao,
                'tamanho_papel': template.tamanho_papel
            }
            
            if incluir_variaveis:
                variaveis = VariavelDinamica.query.filter_by(
                    template_id=template.id,
                    tipo_template='certificado'
                ).all()
                template_data['variaveis'] = [{
                    'nome': var.nome,
                    'tipo': var.tipo,
                    'valor_padrao': var.valor_padrao,
                    'obrigatoria': var.obrigatoria,
                    'descricao': var.descricao
                } for var in variaveis]
            
            export_data['templates'].append(template_data)
        
        if formato == 'zip':
            # Criar arquivo ZIP
            import zipfile
            import tempfile
            
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, f'certificados_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip')
            
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                # Adicionar JSON principal
                json_content = json.dumps(export_data, indent=2, ensure_ascii=False)
                zipf.writestr('templates.json', json_content)
                
                # Adicionar README
                readme_content = f"""# Exportação de Templates de Certificados

Data da exportação: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
Total de templates: {len(templates)}
Formato: ZIP

## Conteúdo
- templates.json: Dados dos templates

## Como importar
1. Acesse a página de Exportar/Importar Templates
2. Selecione este arquivo ZIP
3. Configure as opções de importação
4. Clique em "Importar Templates"
"""
                zipf.writestr('README.txt', readme_content)
            
            @after_this_request
            def remove_temp_file(response):
                try:
                    os.remove(zip_path)
                    os.rmdir(temp_dir)
                except:
                    pass
                return response
            
            return send_file(zip_path, as_attachment=True, download_name=f'certificados_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip')
        
        else:
            # Retornar JSON
            @after_this_request
            def set_download_headers(response):
                response.headers['Content-Disposition'] = f'attachment; filename=certificados_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                return response
            
            return export_data
    
    except Exception as e:
        logger.error(f"Erro ao exportar templates: {str(e)}")
        return {'success': False, 'message': 'Erro interno do servidor'}, 500


@certificado_routes.route('/importar', methods=['POST'])
@login_required
@require_permission('templates.import')
def importar_templates():
    """Importar templates de certificados"""
    try:
        sobrescrever = request.form.get('sobrescrever') == 'true'
        validar = request.form.get('validar') == 'true'
        importar_variaveis = request.form.get('importar_variaveis') == 'true'
        
        files = request.files.getlist('files')
        if not files:
            return {'success': False, 'message': 'Nenhum arquivo enviado'}, 400
        
        templates_importados = 0
        templates_ignorados = 0
        erros = []
        
        for file in files:
            if not file.filename:
                continue
            
            try:
                if file.filename.endswith('.zip'):
                    # Processar arquivo ZIP
                    import zipfile
                    import tempfile
                    
                    temp_dir = tempfile.mkdtemp()
                    zip_path = os.path.join(temp_dir, secure_filename(file.filename))
                    file.save(zip_path)
                    
                    with zipfile.ZipFile(zip_path, 'r') as zipf:
                        # Procurar arquivo JSON principal
                        json_files = [f for f in zipf.namelist() if f.endswith('.json')]
                        if not json_files:
                            erros.append(f"Nenhum arquivo JSON encontrado em {file.filename}")
                            continue
                        
                        # Usar o primeiro JSON encontrado (ou templates.json se existir)
                        json_file = 'templates.json' if 'templates.json' in json_files else json_files[0]
                        
                        with zipf.open(json_file) as f:
                            data = json.load(f)
                    
                    # Limpar arquivos temporários
                    os.remove(zip_path)
                    os.rmdir(temp_dir)
                
                elif file.filename.endswith('.json'):
                    # Processar arquivo JSON
                    data = json.load(file)
                
                else:
                    erros.append(f"Formato de arquivo não suportado: {file.filename}")
                    continue
                
                # Validar estrutura do arquivo
                if validar:
                    if 'templates' not in data:
                        erros.append(f"Estrutura inválida em {file.filename}: campo 'templates' não encontrado")
                        continue
                    
                    if data.get('tipo') != 'certificados':
                        erros.append(f"Tipo de arquivo incorreto em {file.filename}: esperado 'certificados'")
                        continue
                
                # Processar templates
                for template_data in data.get('templates', []):
                    try:
                        nome = template_data.get('nome')
                        if not nome:
                            erros.append("Template sem nome encontrado")
                            continue
                        
                        # Verificar se template já existe
                        existing_template = CertificadoTemplateAvancado.query.filter_by(
                            nome=nome,
                            cliente_id=current_user.id
                        ).first()
                        
                        if existing_template and not sobrescrever:
                            templates_ignorados += 1
                            continue
                        
                        # Criar ou atualizar template
                        if existing_template:
                            template = existing_template
                        else:
                            template = CertificadoTemplateAvancado(cliente_id=current_user.id)
                        
                        # Atualizar dados do template
                        template.nome = nome
                        template.tipo = template_data.get('tipo', 'geral')
                        template.conteudo_html = template_data.get('conteudo_html', '')
                        template.conteudo_css = template_data.get('conteudo_css', '')
                        template.ativo = template_data.get('ativo', False)
                        template.padrao = template_data.get('padrao', False)
                        template.descricao = template_data.get('descricao', '')
                        template.orientacao = template_data.get('orientacao', 'portrait')
                        template.tamanho_papel = template_data.get('tamanho_papel', 'A4')
                        
                        if not existing_template:
                            db.session.add(template)
                        
                        db.session.flush()  # Para obter o ID do template
                        
                        # Importar variáveis se solicitado
                        if importar_variaveis and 'variaveis' in template_data:
                            # Remover variáveis existentes se sobrescrever
                            if existing_template:
                                VariavelDinamica.query.filter_by(
                                    template_id=template.id,
                                    tipo_template='certificado'
                                ).delete()
                            
                            # Adicionar novas variáveis
                            for var_data in template_data['variaveis']:
                                variavel = VariavelDinamica(
                                    template_id=template.id,
                                    tipo_template='certificado',
                                    nome=var_data.get('nome'),
                                    tipo=var_data.get('tipo', 'texto'),
                                    valor_padrao=var_data.get('valor_padrao'),
                                    obrigatoria=var_data.get('obrigatoria', False),
                                    descricao=var_data.get('descricao')
                                )
                                db.session.add(variavel)
                        
                        templates_importados += 1
                    
                    except Exception as e:
                        erros.append(f"Erro ao processar template '{template_data.get('nome', 'sem nome')}': {str(e)}")
            
            except Exception as e:
                erros.append(f"Erro ao processar arquivo {file.filename}: {str(e)}")
        
        # Salvar alterações
        db.session.commit()
        
        return {
            'success': True,
            'templates_importados': templates_importados,
            'templates_ignorados': templates_ignorados,
            'erros': erros
        }
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao importar templates: {str(e)}")
        return {'success': False, 'message': 'Erro interno do servidor'}, 500


# ===== SISTEMA FLEXÍVEL DE LIBERAÇÃO DE CERTIFICADOS =====

@certificado_routes.route('/regras_certificado/<int:evento_id>')
@login_required
@require_permission('configuracoes.view')
@require_resource_access('evento', 'evento_id', 'view')
def gerenciar_regras_certificado(evento_id):
    """Gerenciar regras de liberação de certificados."""
    from models.event import Evento
    
    evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first()
    if not evento:
        flash('Evento não encontrado', 'error')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))
    
    regras = RegraCertificado.query.filter_by(
        evento_id=evento_id, cliente_id=current_user.id
    ).order_by(RegraCertificado.prioridade.asc()).all()
    
    templates = CertificadoTemplateAvancado.query.filter_by(
        cliente_id=current_user.id, ativo=True
    ).all()
    
    return render_template('regras_certificado.html', 
                         evento=evento, regras=regras, templates=templates)


@certificado_routes.route('/criar_regra_certificado', methods=['POST'])
@login_required
@require_permission('configuracoes.edit')
def criar_regra_certificado():
    """Criar nova regra de certificado."""
    try:
        data = request.get_json()
        
        regra = RegraCertificado(
            cliente_id=current_user.id,
            evento_id=data['evento_id'],
            nome=data['nome'],
            descricao=data.get('descricao', ''),
            condicoes=data['condicoes'],
            operador_logico=data.get('operador_logico', 'AND'),
            acao=data['acao'],
            template_especifico_id=data.get('template_especifico_id'),
            prioridade=data.get('prioridade', 0)
        )
        
        db.session.add(regra)
        db.session.commit()
        
        return {
            'success': True,
            'message': 'Regra criada com sucesso',
            'regra_id': regra.id
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar regra: {str(e)}")
        return {'success': False, 'message': 'Erro ao criar regra'}, 500


@certificado_routes.route('/editar_regra_certificado/<int:regra_id>', methods=['PUT'])
@login_required
@require_permission('configuracoes.edit')
@require_resource_access('regra', 'regra_id', 'edit')
def editar_regra_certificado(regra_id):
    """Editar regra de certificado."""
    try:
        regra = RegraCertificado.query.filter_by(
            id=regra_id, cliente_id=current_user.id
        ).first()
        
        if not regra:
            return {'success': False, 'message': 'Regra não encontrada'}, 404
        
        data = request.get_json()
        
        regra.nome = data.get('nome', regra.nome)
        regra.descricao = data.get('descricao', regra.descricao)
        regra.condicoes = data.get('condicoes', regra.condicoes)
        regra.operador_logico = data.get('operador_logico', regra.operador_logico)
        regra.acao = data.get('acao', regra.acao)
        regra.template_especifico_id = data.get('template_especifico_id', regra.template_especifico_id)
        regra.prioridade = data.get('prioridade', regra.prioridade)
        regra.ativo = data.get('ativo', regra.ativo)
        
        db.session.commit()
        
        return {
            'success': True,
            'message': 'Regra atualizada com sucesso'
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao editar regra: {str(e)}")
        return {'success': False, 'message': 'Erro ao editar regra'}, 500


@certificado_routes.route('/excluir_regra_certificado/<int:regra_id>', methods=['DELETE'])
@login_required
@require_permission('configuracoes.delete')
@require_resource_access('regra', 'regra_id', 'delete')
def excluir_regra_certificado(regra_id):
    """Excluir regra de certificado."""
    try:
        regra = RegraCertificado.query.filter_by(
            id=regra_id, cliente_id=current_user.id
        ).first()
        
        if not regra:
            return {'success': False, 'message': 'Regra não encontrada'}, 404
        
        db.session.delete(regra)
        db.session.commit()
        
        return {
            'success': True,
            'message': 'Regra excluída com sucesso'
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir regra: {str(e)}")
        return {'success': False, 'message': 'Erro ao excluir regra'}, 500


@certificado_routes.route('/obter_regra_certificado/<int:regra_id>', methods=['GET'])
@login_required
@require_permission('configuracoes.view')
@require_resource_access('regra', 'regra_id', 'view')
def obter_regra_certificado(regra_id):
    """Obter dados de uma regra específica."""
    try:
        regra = RegraCertificado.query.filter_by(
            id=regra_id, cliente_id=current_user.id
        ).first()
        
        if not regra:
            return {'success': False, 'message': 'Regra não encontrada'}, 404
        
        return {
            'success': True,
            'regra': {
                'id': regra.id,
                'nome': regra.nome,
                'descricao': regra.descricao,
                'prioridade': regra.prioridade,
                'condicoes': regra.condicoes,
                'acoes': regra.acoes,
                'ativa': regra.ativa
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter regra: {str(e)}")
        return {'success': False, 'message': 'Erro ao obter regra'}, 500


@certificado_routes.route('/solicitar_declaracao', methods=['POST'])
@login_required
def solicitar_declaracao():
    """Solicitar declaração de participação."""
    try:
        data = request.get_json(silent=True) or request.form

        solicitacao_existente = SolicitacaoCertificado.query.filter_by(
            usuario_id=current_user.id,
            evento_id=data['evento_id'],
            tipo_certificado='declaracao',
            status='pendente'
        ).first()

        if solicitacao_existente:
            mensagem = (
                'Já existe uma solicitação pendente para esta declaração'
            )
            if request.is_json:
                return {'success': False, 'message': mensagem}, 400
            flash(mensagem, 'warning')
            return redirect(
                request.referrer
                or url_for(
                    'dashboard_participante_routes.dashboard_participante'
                )
            )

        dados_participacao = certificado_service.calcular_atividades_participadas(
            current_user.id, data['evento_id']
        )

        solicitacao = SolicitacaoCertificado(
            usuario_id=current_user.id,
            evento_id=data['evento_id'],
            tipo_certificado='declaracao',
            justificativa=data.get('justificativa', ''),
            dados_participacao=dados_participacao
        )

        db.session.add(solicitacao)
        db.session.commit()

        criar_notificacao_solicitacao(solicitacao)

        mensagem = 'Solicitação enviada com sucesso'
        if request.is_json:
            return {
                'success': True,
                'message': mensagem,
                'solicitacao_id': solicitacao.id,
            }
        flash(mensagem, 'success')
        return redirect(
            request.referrer
            or url_for('dashboard_participante_routes.dashboard_participante')
        )

    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        logger.error(f"Erro ao solicitar declaração: {str(e)}")
        mensagem = 'Erro ao enviar solicitação'
        if request.is_json:
            return {'success': False, 'message': mensagem}, 500
        flash(mensagem, 'danger')
        return redirect(
            request.referrer
            or url_for('dashboard_participante_routes.dashboard_participante')
        )


@certificado_routes.route('/solicitar_certificado', methods=['POST'])
@login_required
def solicitar_certificado():
    """Solicitar certificado para aprovação manual."""
    try:
        data = request.get_json()
        
        # Verificar se já existe solicitação pendente
        solicitacao_existente = SolicitacaoCertificado.query.filter_by(
            usuario_id=current_user.id,
            evento_id=data['evento_id'],
            oficina_id=data.get('oficina_id'),
            tipo_certificado=data['tipo_certificado'],
            status='pendente'
        ).first()
        
        if solicitacao_existente:
            return {
                'success': False, 
                'message': 'Já existe uma solicitação pendente para este certificado'
            }
        
        # Coletar dados de participação
        dados_participacao = certificado_service.calcular_atividades_participadas(
            current_user.id, data['evento_id']
        )
        
        solicitacao = SolicitacaoCertificado(
            usuario_id=current_user.id,
            evento_id=data['evento_id'],
            oficina_id=data.get('oficina_id'),
            tipo_certificado=data['tipo_certificado'],
            justificativa=data.get('justificativa', ''),
            dados_participacao=dados_participacao
        )
        
        db.session.add(solicitacao)
        db.session.commit()
        
        # Criar notificação para administradores
        criar_notificacao_solicitacao(solicitacao)
        
        return {
            'success': True,
            'message': 'Solicitação enviada com sucesso',
            'solicitacao_id': solicitacao.id
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao solicitar certificado: {str(e)}")
        return {'success': False, 'message': 'Erro ao enviar solicitação'}, 500


@certificado_routes.route('/aprovar_solicitacao/<int:solicitacao_id>', methods=['POST'])
@login_required
@require_permission('certificados.approve')
def aprovar_solicitacao(solicitacao_id):
    """Aprovar solicitação de certificado."""
    try:
        solicitacao = SolicitacaoCertificado.query.get(solicitacao_id)
        
        if not solicitacao:
            return {'success': False, 'message': 'Solicitação não encontrada'}, 404
        
        data = request.get_json()
        
        solicitacao.status = 'aprovada'
        solicitacao.aprovado_por = current_user.id
        solicitacao.data_aprovacao = datetime.utcnow()
        solicitacao.observacoes_aprovacao = data.get('observacoes', '')
        
        db.session.commit()
        
        # Gerar certificado automaticamente
        if data.get('gerar_automaticamente', True):
            gerar_certificado_aprovado(solicitacao)
        
        # Criar notificação para o usuário
        criar_notificacao_aprovacao(solicitacao)
        
        return {
            'success': True,
            'message': 'Solicitação aprovada com sucesso'
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao aprovar solicitação: {str(e)}")
        return {'success': False, 'message': 'Erro ao aprovar solicitação'}, 500


@certificado_routes.route('/rejeitar_solicitacao/<int:solicitacao_id>', methods=['POST'])
@login_required
@require_permission('certificados.approve')
def rejeitar_solicitacao(solicitacao_id):
    """Rejeitar solicitação de certificado."""
    try:
        solicitacao = SolicitacaoCertificado.query.get(solicitacao_id)
        
        if not solicitacao:
            return {'success': False, 'message': 'Solicitação não encontrada'}, 404
        
        data = request.get_json()
        
        solicitacao.status = 'rejeitada'
        solicitacao.aprovado_por = current_user.id
        solicitacao.data_aprovacao = datetime.utcnow()
        solicitacao.observacoes_aprovacao = data.get('motivo', '')
        
        db.session.commit()
        
        # Criar notificação para o usuário
        criar_notificacao_rejeicao(solicitacao)
        
        return {
            'success': True,
            'message': 'Solicitação rejeitada'
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao rejeitar solicitação: {str(e)}")
        return {'success': False, 'message': 'Erro ao rejeitar solicitação'}, 500


@certificado_routes.route('/solicitacoes_pendentes')
@login_required
@require_permission('certificados.approve')
def listar_solicitacoes_pendentes():
    """Listar solicitações pendentes de aprovação."""
    from models.event import Evento
    
    solicitacoes = SolicitacaoCertificado.query.filter_by(
        status='pendente'
    ).join(SolicitacaoCertificado.evento).filter(
        Evento.cliente_id == current_user.id
    ).order_by(SolicitacaoCertificado.data_solicitacao.desc()).all()
    
    return render_template('solicitacoes_pendentes.html', solicitacoes=solicitacoes)


@certificado_routes.route('/detalhes_solicitacao/<int:solicitacao_id>')
@login_required
@require_permission('certificados.approve')
def detalhes_solicitacao(solicitacao_id):
    """Obter detalhes de uma solicitação de certificado."""
    try:
        from models.event import Evento
        
        solicitacao = SolicitacaoCertificado.query.filter_by(
            id=solicitacao_id
        ).join(SolicitacaoCertificado.evento).filter(
            Evento.cliente_id == current_user.id
        ).first()
        
        if not solicitacao:
            return jsonify({'erro': 'Solicitação não encontrada'}), 404
        
        # Obter informações detalhadas
        detalhes = {
            'id': solicitacao.id,
            'status': solicitacao.status,
            'data_solicitacao': solicitacao.data_solicitacao.strftime('%d/%m/%Y %H:%M'),
            'data_processamento': solicitacao.data_processamento.strftime('%d/%m/%Y %H:%M') if solicitacao.data_processamento else None,
            'motivo_rejeicao': solicitacao.motivo_rejeicao,
            'usuario': {
                'id': solicitacao.usuario.id,
                'nome': solicitacao.usuario.nome,
                'email': solicitacao.usuario.email,
                'cpf': solicitacao.usuario.cpf
            },
            'evento': {
                'id': solicitacao.evento.id,
                'nome': solicitacao.evento.nome,
                'data_inicio': solicitacao.evento.data_inicio.strftime('%d/%m/%Y'),
                'data_fim': solicitacao.evento.data_fim.strftime('%d/%m/%Y'),
                'carga_horaria': solicitacao.evento.carga_horaria
            },
            'tipo_certificado': solicitacao.tipo_certificado,
            'observacoes': solicitacao.observacoes
        }
        
        # Verificar participação do usuário
        from models.event import Participacao, Atividade, ParticipacaoAtividade
        
        participacao = Participacao.query.filter_by(
            usuario_id=solicitacao.usuario_id,
            evento_id=solicitacao.evento_id
        ).first()
        
        if participacao:
            detalhes['participacao'] = {
                'data_inscricao': participacao.data_inscricao.strftime('%d/%m/%Y %H:%M'),
                'presente': participacao.presente,
                'horas_participacao': participacao.horas_participacao or 0
            }
            
            # Obter atividades participadas
            atividades_participadas = ParticipacaoAtividade.query.filter_by(
                participacao_id=participacao.id,
                presente=True
            ).join(Atividade).all()
            
            detalhes['atividades'] = [{
                'nome': pa.atividade.nome,
                'data': pa.atividade.data.strftime('%d/%m/%Y'),
                'carga_horaria': pa.atividade.carga_horaria
            } for pa in atividades_participadas]
        
        return jsonify(detalhes)
        
    except Exception as e:
        logger.error(f"Erro ao obter detalhes da solicitação {solicitacao_id}: {str(e)}")
        return jsonify({'erro': 'Erro interno do sistema'}), 500


@certificado_routes.route('/notificacoes_certificado')
@login_required
def listar_notificacoes():
    """Listar notificações de certificados do usuário."""
    notificacoes = NotificacaoCertificado.query.filter_by(
        usuario_id=current_user.id
    ).order_by(NotificacaoCertificado.data_criacao.desc()).limit(50).all()
    
    return render_template('notificacoes_certificado.html', notificacoes=notificacoes)


@certificado_routes.route('/marcar_notificacao_lida/<int:notificacao_id>', methods=['POST'])
@login_required
def marcar_notificacao_lida(notificacao_id):
    """Marcar notificação como lida."""
    try:
        notificacao = NotificacaoCertificado.query.filter_by(
            id=notificacao_id, usuario_id=current_user.id
        ).first()
        
        if not notificacao:
            return {'success': False, 'message': 'Notificação não encontrada'}, 404
        
        notificacao.lida = True
        db.session.commit()
        
        return {'success': True, 'message': 'Notificação marcada como lida'}
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao marcar notificação: {str(e)}")
        return {'success': False, 'message': 'Erro ao marcar notificação'}, 500


# ===== FUNÇÕES AUXILIARES =====

def avaliar_regras_certificado(usuario_id, evento_id, tipo_certificado='geral'):
    """Avaliar regras de liberação de certificados para um usuário."""
    regras = RegraCertificado.query.filter_by(
        evento_id=evento_id, ativo=True
    ).order_by(RegraCertificado.prioridade.asc()).all()
    
    dados_participacao = certificado_service.calcular_atividades_participadas(
        usuario_id, evento_id
    )
    
    for regra in regras:
        if avaliar_condicoes_regra(regra, dados_participacao):
            return {
                'acao': regra.acao,
                'template_id': regra.template_especifico_id,
                'regra': regra.nome
            }
    
    return {'acao': 'liberar', 'template_id': None, 'regra': 'Padrão'}


def avaliar_condicoes_regra(regra, dados_participacao):
    """Avaliar se as condições de uma regra são atendidas."""
    condicoes = regra.condicoes
    resultados = []
    
    for condicao in condicoes:
        campo = condicao['campo']
        operador = condicao['operador']
        valor = condicao['valor']
        
        valor_atual = dados_participacao.get(campo, 0)
        
        if operador == 'maior_que':
            resultado = valor_atual > valor
        elif operador == 'menor_que':
            resultado = valor_atual < valor
        elif operador == 'igual':
            resultado = valor_atual == valor
        elif operador == 'maior_igual':
            resultado = valor_atual >= valor
        elif operador == 'menor_igual':
            resultado = valor_atual <= valor
        else:
            resultado = False
        
        resultados.append(resultado)
    
    if regra.operador_logico == 'AND':
        return all(resultados)
    else:  # OR
        return any(resultados)


def criar_notificacao_solicitacao(solicitacao):
    """Criar notificação para administradores sobre nova solicitação."""
    from models.user import Usuario
    
    # Buscar administradores do cliente
    admins = Usuario.query.filter_by(
        cliente_id=solicitacao.evento.cliente_id,
        role='admin'
    ).all()
    
    for admin in admins:
        notificacao = NotificacaoCertificado(
            usuario_id=admin.id,
            evento_id=solicitacao.evento_id,
            tipo='pendente',
            titulo='Nova Solicitação de Certificado',
            mensagem=f'Nova solicitação de certificado {solicitacao.tipo_certificado} de {solicitacao.usuario.nome}',
            solicitacao_id=solicitacao.id
        )
        db.session.add(notificacao)
    
    db.session.commit()


def criar_notificacao_aprovacao(solicitacao):
    """Criar notificação de aprovação para o usuário."""
    notificacao = NotificacaoCertificado(
        usuario_id=solicitacao.usuario_id,
        evento_id=solicitacao.evento_id,
        tipo='liberado',
        titulo='Certificado Aprovado',
        mensagem=f'Sua solicitação de certificado {solicitacao.tipo_certificado} foi aprovada',
        solicitacao_id=solicitacao.id
    )
    db.session.add(notificacao)
    db.session.commit()


def criar_notificacao_rejeicao(solicitacao):
    """Criar notificação de rejeição para o usuário."""
    notificacao = NotificacaoCertificado(
        usuario_id=solicitacao.usuario_id,
        evento_id=solicitacao.evento_id,
        tipo='rejeitado',
        titulo='Certificado Rejeitado',
        mensagem=f'Sua solicitação de certificado {solicitacao.tipo_certificado} foi rejeitada: {solicitacao.observacoes_aprovacao}',
        solicitacao_id=solicitacao.id
    )
    db.session.add(notificacao)
    db.session.commit()


def gerar_certificado_aprovado(solicitacao):
    """Gerar certificado após aprovação."""
    try:
        if solicitacao.tipo_certificado == 'geral':
            # Gerar certificado geral
            atividades = certificado_service.calcular_atividades_participadas(
                solicitacao.usuario_id, solicitacao.evento_id
            )
            
            config = ConfiguracaoCertificadoAvancada.query.filter_by(
                evento_id=solicitacao.evento_id
            ).first()
            
            template = None
            if config and config.template_geral_id:
                template = CertificadoTemplateAvancado.query.get(config.template_geral_id)
            
            if template:
                pdf_path = gerar_certificado_geral_personalizado(
                    solicitacao.usuario, solicitacao.evento, atividades, template, solicitacao.evento.cliente
                )
                
                # Registrar no histórico
                from models.event import HistoricoCertificado
                historico = HistoricoCertificado(
                    usuario_id=solicitacao.usuario_id,
                    evento_id=solicitacao.evento_id,
                    tipo_certificado='geral',
                    template_usado=template.nome,
                    caminho_arquivo=pdf_path,
                    data_emissao=datetime.utcnow()
                )
                db.session.add(historico)
                db.session.commit()
        
    except Exception as e:
        logger.error(f"Erro ao gerar certificado aprovado: {str(e)}")
        raise


def gerar_conteudo_template_avancado(design_json, usuario, evento, atividades):
    """Gera conteúdo baseado no design JSON do template avançado."""
    try:
        design = json.loads(design_json)
        conteudo_parts = []
        
        for elemento in design.get('elementos', []):
            if elemento.get('tipo') == 'texto':
                texto = elemento.get('conteudo', '')
                # Substituir variáveis no texto
                texto = texto.replace("{NOME_PARTICIPANTE}", usuario.nome)\
                            .replace("{NOME_EVENTO}", evento.nome)\
                            .replace("{CARGA_HORARIA}", str(atividades['total_horas']))\
                            .replace("{TOTAL_ATIVIDADES}", str(atividades['total_atividades']))
                conteudo_parts.append(texto)
        
        return ' '.join(conteudo_parts)
    except:
        return (
            "Certificamos que {NOME_PARTICIPANTE} participou do evento {NOME_EVENTO}, "
            "realizando {TOTAL_ATIVIDADES} atividades com carga horária total de {CARGA_HORARIA} horas."
         )


# ==================== ROTAS PARA DECLARAÇÕES DE COMPARECIMENTO ====================

@certificado_routes.route('/declaracoes')
@login_required
@require_permission('declaracoes.view')
def gerenciar_declaracoes():
    """Página para gerenciar templates de declarações de comparecimento."""
    templates = DeclaracaoTemplate.query.filter_by(cliente_id=current_user.id).all()
    return render_template('certificado/declaracoes.html', templates=templates)


@certificado_routes.route('/declaracoes/criar', methods=['GET', 'POST'])
@login_required
@require_permission('declaracoes.create')
def criar_declaracao_template():
    """Criar novo template de declaração de comparecimento."""
    if request.method == 'POST':
        data = request.get_json()
        existente = DeclaracaoTemplate.query.filter_by(
            cliente_id=current_user.id, nome=data.get('nome')
        ).first()
        if existente:
            return {
                'success': False,
                'message': 'Template com este nome já existe'
            }, 400

        template = DeclaracaoTemplate(
            nome=data['nome'],
            conteudo=data['conteudo'],
            tipo=data.get('tipo', 'comparecimento'),
            ativo=data.get('ativo', True),
            cliente_id=current_user.id
        )

        db.session.add(template)
        db.session.commit()

        return {'success': True, 'message': 'Template de declaração criado com sucesso'}
    
    return render_template('certificado/criar_declaracao.html')


@certificado_routes.route('/declaracoes/editar/<int:template_id>', methods=['GET', 'POST'])
@login_required
@require_permission('declaracoes.edit')
@require_resource_access('template', 'template_id', 'edit')
def editar_declaracao_template(template_id):
    """Editar template de declaração existente."""
    template = DeclaracaoTemplate.query.filter_by(
        id=template_id, cliente_id=current_user.id
    ).first_or_404()
    
    if request.method == 'GET':
        return {
            'template': {
                'id': template.id,
                'nome': template.nome,
                'conteudo': template.conteudo,
                'tipo': template.tipo,
                'ativo': template.ativo,
            }
        }

    data = request.get_json()

    existente = (
        DeclaracaoTemplate.query.filter_by(
            cliente_id=current_user.id, nome=data.get('nome')
        )
        .filter(DeclaracaoTemplate.id != template.id)
        .first()
    )
    if existente:
        return {
            'success': False,
            'message': 'Template com este nome já existe'
        }, 400

    template.nome = data['nome']
    template.conteudo = data['conteudo']
    template.tipo = data.get('tipo', template.tipo)
    template.ativo = data.get('ativo', template.ativo)

    db.session.commit()

    return {'success': True, 'message': 'Template atualizado com sucesso'}


@certificado_routes.route('/declaracoes/deletar/<int:template_id>', methods=['DELETE'])
@login_required
@require_permission('declaracoes.delete')
@require_resource_access('template', 'template_id', 'delete')
def deletar_declaracao_template(template_id):
    """Deletar template de declaração."""
    template = DeclaracaoTemplate.query.filter_by(
        id=template_id, cliente_id=current_user.id
    ).first_or_404()
    
    db.session.delete(template)
    db.session.commit()

    return {'success': True, 'message': 'Template deletado com sucesso'}

@certificado_routes.route('/declaracoes/duplicar/<int:template_id>', methods=['POST'])
@login_required
@require_permission('declaracoes.create')
@require_resource_access('template', 'template_id', 'view')
def duplicar_declaracao_template(template_id):
    """Duplicar template de declaração existente."""
    template = DeclaracaoTemplate.query.filter_by(
        id=template_id,
        cliente_id=current_user.id
    ).first()

    if not template:
        return {'success': False, 'message': 'Template não encontrado'}, 404

    novo_template = DeclaracaoTemplate(
        nome=f"{template.nome} (Cópia)",
        conteudo=template.conteudo,
        tipo=template.tipo,
        ativo=False,
        cliente_id=current_user.id,
    )

    db.session.add(novo_template)
    db.session.commit()

    return {'success': True, 'message': 'Template duplicado com sucesso'}


@certificado_routes.route('/declaracoes/toggle-ativo/<int:template_id>', methods=['POST'])
@login_required
@require_permission('declaracoes.edit')
@require_resource_access('template', 'template_id', 'edit')
def toggle_declaracao_ativo(template_id):
    """Alternar status ativo de um template."""
    template = DeclaracaoTemplate.query.filter_by(
        id=template_id,
        cliente_id=current_user.id
    ).first()

    if not template:
        return {'success': False, 'message': 'Template não encontrado'}, 404

    if template.ativo:
        template.ativo = False
        status = 'desativado'
    else:
        DeclaracaoTemplate.query.filter_by(cliente_id=current_user.id).update(
            {'ativo': False}
        )
        template.ativo = True
        status = 'ativado'

    db.session.commit()

    return {
        'success': True,
        'message': f'Template {status} com sucesso',
        'ativo': template.ativo,
    }


@certificado_routes.route('/declaracoes/importar', methods=['POST'])
@login_required
@require_permission('declaracoes.create')
def importar_declaracao_template():
    """Importar template de declaração a partir de JSON."""
    data = request.get_json()

    if not data:
        return {'success': False, 'message': 'Nenhum dado enviado'}, 400

    nome = data.get('nome')
    conteudo = data.get('conteudo')
    tipo = data.get('tipo', 'comparecimento')
    ativo = data.get('ativo', False)

    if not nome or not conteudo:
        return {'success': False, 'message': 'Nome e conteúdo são obrigatórios'}, 400

    existente = DeclaracaoTemplate.query.filter_by(
        cliente_id=current_user.id, nome=nome
    ).first()
    if existente:
        return {'success': False, 'message': 'Template com este nome já existe'}, 400

    if ativo:
        DeclaracaoTemplate.query.filter_by(cliente_id=current_user.id).update(
            {'ativo': False}
        )

    template = DeclaracaoTemplate(
        nome=nome,
        conteudo=conteudo,
        tipo=tipo,
        ativo=ativo,
        cliente_id=current_user.id,
    )

    db.session.add(template)
    db.session.commit()

    return {'success': True, 'message': 'Template importado com sucesso'}



@certificado_routes.route('/declaracoes/gerar_individual/<int:evento_id>/<int:usuario_id>')
@login_required
@require_permission('declaracoes.generate')
@require_resource_access('evento', 'evento_id', 'view')
def gerar_declaracao_individual(evento_id, usuario_id):
    """Gerar declaração individual de comparecimento."""
    from models.event import Evento
    from models.user import Usuario
    
    evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first_or_404()
    usuario = Usuario.query.get_or_404(usuario_id)
    
    # Verificar se o usuário participou do evento
    participacao = verificar_participacao_evento(usuario_id, evento_id)
    
    if not participacao['participou']:
        flash('Usuário não participou deste evento', 'error')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))
    
    # Buscar template individual ativo
    template = DeclaracaoTemplate.query.filter_by(
        cliente_id=current_user.id, ativo=True, tipo='individual'
    ).first()

    if not template:
        flash('Nenhum template de declaração individual encontrado', 'error')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))
    
    # Gerar declaração
    pdf_path = gerar_declaracao_personalizada(usuario, evento, participacao, template, current_user)
    
    return send_file(pdf_path, mimetype="application/pdf")



@certificado_routes.route('/declaracoes/gerar_lote/<int:evento_id>')
@login_required
@require_permission('declaracoes.bulk_generate')
@require_resource_access('evento', 'evento_id', 'view')
def gerar_declaracoes_lote(evento_id):
    """Gerar declarações em lote para um evento."""
    from models.event import Evento
    from models import Checkin
    
    evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first_or_404()
    
    # Buscar todos os participantes do evento
    participantes_query = db.session.query(
        Checkin.usuario_id
    ).filter(
        Checkin.evento_id == evento_id
    ).distinct()
    
    participantes_ids = [p.usuario_id for p in participantes_query.all()]
    
    if not participantes_ids:
        flash('Nenhum participante encontrado para este evento', 'warning')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))
    
    # Buscar template coletivo ativo
    template = DeclaracaoTemplate.query.filter_by(
        cliente_id=current_user.id, ativo=True, tipo='coletiva'
    ).first()

    if not template:
        flash('Nenhum template de declaração coletiva encontrado', 'error')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))
    
    # Gerar declarações
    declaracoes_geradas = []
    
    for usuario_id in participantes_ids:
        from models.user import Usuario
        usuario = Usuario.query.get(usuario_id)
        
        if usuario:
            participacao = verificar_participacao_evento(usuario_id, evento_id)
            
            if participacao['participou']:
                pdf_path = gerar_declaracao_personalizada(
                    usuario, evento, participacao, template, current_user
                )
                declaracoes_geradas.append({
                    'usuario': usuario.nome,
                    'path': pdf_path
                })
    
    if declaracoes_geradas:
        # Criar ZIP com todas as declarações
        import zipfile
        import tempfile
        
        zip_path = os.path.join(tempfile.gettempdir(), f'declaracoes_evento_{evento_id}.zip')
        
        with zipfile.ZipFile(zip_path, 'w') as zip_file:
            for decl in declaracoes_geradas:
                if os.path.exists(decl['path']):
                    zip_file.write(decl['path'], f"declaracao_{decl['usuario']}.pdf")
        
        flash(f'{len(declaracoes_geradas)} declarações geradas com sucesso', 'success')
        return send_file(zip_path, as_attachment=True, download_name=f'declaracoes_{evento.nome}.zip')
    else:
        flash('Nenhuma declaração pôde ser gerada', 'warning')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))


@certificado_routes.route('/declaracoes/preview-participantes/<int:evento_id>')
@login_required
@require_permission('declaracoes.view')
@require_resource_access('evento', 'evento_id', 'view')
def preview_participantes(evento_id):
    """Retorna lista resumida de participantes do evento."""
    from models.event import Evento, Checkin
    from models.user import Usuario

    Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first_or_404()

    participantes = (
        db.session.query(Usuario.id, Usuario.nome)
        .join(Checkin, Checkin.usuario_id == Usuario.id)
        .filter(Checkin.evento_id == evento_id)
        .distinct()
        .all()
    )

    dados = [{'id': p.id, 'nome': p.nome} for p in participantes]
    return jsonify({'participantes': dados})


@certificado_routes.route('/declaracoes/preview/<int:template_id>/<int:evento_id>')
@login_required
@require_permission('declaracoes.view')
@require_resource_access('template', 'template_id', 'view')
def preview_declaracao(template_id, evento_id):
    """Visualizar preview de declaração."""
    from models.event import Evento
    
    template = DeclaracaoTemplate.query.filter_by(
        id=template_id, cliente_id=current_user.id
    ).first_or_404()
    
    evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first_or_404()
    
    # Criar dados de exemplo
    class UsuarioExemplo:
        id = 0
        nome = "Participante Exemplo"
        email = "exemplo@email.com"
    
    participacao_exemplo = {
        'participou': True,
        'total_checkins': 5,
        'atividades': [
            {'nome': 'Oficina Exemplo 1', 'data': '01/01/2024'},
            {'nome': 'Oficina Exemplo 2', 'data': '02/01/2024'}
        ],
        'carga_horaria_total': 10
    }
    
    pdf_path = gerar_declaracao_personalizada(
        UsuarioExemplo(), evento, participacao_exemplo, template, current_user
    )

    return send_file(pdf_path, mimetype="application/pdf")


@certificado_routes.route('/declaracoes/estatisticas/<int:evento_id>')
@login_required
@require_permission('declaracoes.view')
@require_resource_access('evento', 'evento_id', 'view')
def estatisticas_declaracoes(evento_id):
    """Retorna estatísticas de emissão de declarações."""
    total_participantes = (
        db.session.query(Checkin.usuario_id)
        .filter_by(evento_id=evento_id)
        .distinct()
        .count()
    )

    declaracoes_emitidas = (
        DeclaracaoComparecimento.query.filter_by(
            evento_id=evento_id, status='emitida'
        ).count()
    )

    participantes_elegiveis = total_participantes
    novas_declaracoes = max(participantes_elegiveis - declaracoes_emitidas, 0)

    return jsonify(
        {
            'estatisticas': {
                'total_participantes': total_participantes,
                'participantes_elegiveis': participantes_elegiveis,
                'declaracoes_ja_emitidas': declaracoes_emitidas,
                'novas_declaracoes': novas_declaracoes,
            }
        }
    )


@certificado_routes.route('/declaracoes/status-liberacao/<int:evento_id>')
@login_required
@require_permission('declaracoes.view')
@require_resource_access('evento', 'evento_id', 'view')
def status_liberacao_declaracoes(evento_id):
    """Retorna status da liberação de declarações."""
    participantes_elegiveis = (
        db.session.query(Checkin.usuario_id)
        .filter_by(evento_id=evento_id)
        .distinct()
        .count()
    )

    declaracoes_disponiveis = (
        DeclaracaoComparecimento.query.filter(
            DeclaracaoComparecimento.evento_id == evento_id,
            DeclaracaoComparecimento.status.in_(['liberada', 'emitida'])
        ).count()
    )

    data_liberacao = (
        db.session.query(func.min(DeclaracaoComparecimento.data_liberacao))
        .filter(DeclaracaoComparecimento.evento_id == evento_id)
        .scalar()
    )

    status = {
        'liberado': declaracoes_disponiveis > 0,
        'participantes_elegiveis': participantes_elegiveis,
        'declaracoes_disponiveis': declaracoes_disponiveis,
        'data_liberacao': data_liberacao.isoformat() if data_liberacao else None,
    }

    return jsonify({'status': status})


@certificado_routes.route('/declaracoes/habilitar-liberacao', methods=['POST'])
@login_required
@require_permission('declaracoes.release')
def habilitar_liberacao_declaracoes():
    """Habilita a liberação de declarações para um evento."""
    dados = request.get_json() or {}
    evento_id = dados.get('evento_id')
    template_id = dados.get('template_id')
    Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first_or_404()
    try:
        liberar_declaracoes_evento(evento_id, template_id)
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    return jsonify({'success': True})


@certificado_routes.route(
    '/declaracoes/desabilitar-liberacao/<int:evento_id>', methods=['POST']
)
@login_required
@require_permission('declaracoes.release')
@require_resource_access('evento', 'evento_id', 'edit')
def desabilitar_liberacao_declaracoes(evento_id):
    """Desabilita a liberação de declarações de um evento."""
    DeclaracaoComparecimento.query.filter_by(evento_id=evento_id).update(
        {'status': 'pendente', 'data_liberacao': None}
    )
    db.session.commit()
    return jsonify({'success': True})


def verificar_participacao_evento(usuario_id, evento_id):
    """Verifica a participação de um usuário em um evento."""
    from models import Checkin
    
    # Buscar check-ins do usuário no evento
    checkins = db.session.query(Checkin).filter(
        Checkin.usuario_id == usuario_id,
        Checkin.evento_id == evento_id
    ).all()
    
    if not checkins:
        return {
            'participou': False,
            'total_checkins': 0,
            'atividades': [],
            'carga_horaria_total': 0
        }
    
    # Calcular atividades participadas
    atividades = []
    carga_horaria_total = 0
    
    for checkin in checkins:
        if checkin.oficina:
            atividades.append({
                'nome': checkin.oficina.titulo,
                'data': checkin.data_checkin.strftime('%d/%m/%Y') if checkin.data_checkin else '',
                'carga_horaria': checkin.oficina.carga_horaria
            })
            carga_horaria_total += int(checkin.oficina.carga_horaria or 0)
    
    return {
        'participou': True,
        'total_checkins': len(checkins),
        'atividades': atividades,
        'carga_horaria_total': carga_horaria_total
    }


@certificado_routes.route('/testar_template/<int:template_id>', methods=['POST'])
@login_required
@require_permission('templates.test')
def testar_template(template_id):
    """Testa um template personalizado com dados de exemplo."""
    try:
        template = CertificadoTemplateAvancado.query.filter_by(
            id=template_id,
            cliente_id=current_user.id
        ).first_or_404()
        
        # Dados de exemplo para teste
        dados_exemplo = {
            'nome_participante': 'João da Silva',
            'nome_evento': 'Evento de Teste',
            'data_evento': datetime.now().strftime('%d/%m/%Y'),
            'carga_horaria': '8 horas',
            'organizador': current_user.nome or 'Organizador Teste'
        }
        
        # Processar template com dados de exemplo
        conteudo_teste = template.conteudo
        for chave, valor in dados_exemplo.items():
            placeholder = f"{{{chave}}}"
            conteudo_teste = conteudo_teste.replace(placeholder, str(valor))
        
        return jsonify({
            'success': True,
            'conteudo_teste': conteudo_teste,
            'dados_exemplo': dados_exemplo
        })
        
    except Exception as e:
        logger.error(f"Erro ao testar template: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao testar template'}), 500


@certificado_routes.route('/duplicar_template_personalizado/<int:template_id>', methods=['POST'])
@login_required
@require_permission('templates.create')
def duplicar_template_personalizado(template_id):
    """Duplica um template personalizado."""
    try:
        template_original = CertificadoTemplateAvancado.query.filter_by(
            id=template_id,
            cliente_id=current_user.id
        ).first_or_404()
        
        # Criar cópia do template
        novo_template = CertificadoTemplateAvancado(
            titulo=f"{template_original.titulo} (Cópia)",
            conteudo=template_original.conteudo,
            layout_config=template_original.layout_config,
            elementos_visuais=template_original.elementos_visuais,
            variaveis_dinamicas=template_original.variaveis_dinamicas,
            orientacao=template_original.orientacao,
            tamanho_pagina=template_original.tamanho_pagina,
            margem_config=template_original.margem_config,
            cliente_id=current_user.id,
            ativo=False,  # Cópia inicia inativa
            data_criacao=datetime.now()
        )
        
        db.session.add(novo_template)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Template duplicado com sucesso',
            'novo_template_id': novo_template.id
        })
        
    except Exception as e:
        logger.error(f"Erro ao duplicar template: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao duplicar template'}), 500


@certificado_routes.route('/toggle_template_personalizado/<int:template_id>', methods=['POST'])
@login_required
@require_permission('templates.activate')
def toggle_template_personalizado(template_id):
    """Ativa ou desativa um template personalizado."""
    try:
        data = request.get_json()
        ativar = data.get('ativar', False)
        
        template = CertificadoTemplateAvancado.query.filter_by(
            id=template_id,
            cliente_id=current_user.id
        ).first_or_404()
        
        template.ativo = ativar
        db.session.commit()
        
        acao = 'ativado' if ativar else 'desativado'
        return jsonify({
            'success': True,
            'message': f'Template {acao} com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao alterar status do template: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao alterar status do template'}), 500


@certificado_routes.route('/excluir_template_personalizado/<int:template_id>', methods=['POST'])
@login_required
@require_permission('templates.delete')
def excluir_template_personalizado(template_id):
    """Exclui um template personalizado."""
    try:
        template = CertificadoTemplateAvancado.query.filter_by(
            id=template_id,
            cliente_id=current_user.id
        ).first_or_404()
        
        db.session.delete(template)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Template excluído com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao excluir template: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao excluir template'}), 500
