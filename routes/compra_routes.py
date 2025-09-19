"""Routes for purchase management and fiscal documentation.

Unauthorized AJAX requests receive a JSON 401 from the global handler.
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app, send_file
from flask_login import login_required, current_user
from utils.auth import cliente_required
from datetime import datetime, timedelta
import json
import os
import uuid
from werkzeug.utils import secure_filename
from sqlalchemy import and_, or_, desc, asc, func
from sqlalchemy.orm import joinedload

from extensions import db, csrf
from models.user import Cliente, Monitor, Usuario
from models.compra import Compra, ItemCompra, DocumentoFiscal, PrestacaoContas, RelatorioCompra, prestacao_compra
from models.material import Material
from services.compra_notification_service import CompraNotificationService
from services.export_service import ExportService
from models.material import Polo, Material
from utils import endpoints
from services.compra_service import CompraService
from services.integracao_service import IntegracaoComprasMateriais
from services.aprovacao_service import AprovacaoService

compra_routes = Blueprint('compra_routes', __name__)

# Configurações de upload
UPLOAD_FOLDER = 'static/documentos_fiscais'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'xml', 'zip', 'rar'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB


def verificar_acesso_cliente():
    """Verifica se o usuário atual é um cliente."""
    return hasattr(current_user, 'tipo') and current_user.tipo == 'cliente'


def verificar_acesso_monitor():
    """Verifica se o usuário atual é um monitor."""
    return hasattr(current_user, 'tipo') and current_user.tipo == 'monitor'


def verificar_acesso_admin():
    """Verifica se o usuário atual é um admin."""
    return hasattr(current_user, 'tipo') and current_user.tipo == 'admin'


def allowed_file(filename):
    """Verifica se o arquivo tem uma extensão permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def gerar_numero_compra():
    """Gera um número único para a compra."""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"COMP-{timestamp}"


def gerar_numero_prestacao():
    """Gera um número único para a prestação de contas."""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"PREST-{timestamp}"


def aplicar_filtros_relatorio():
    """Aplica filtros avançados ao relatório de compras."""
    from collections import defaultdict
    
    # Query base
    query = Compra.query.filter(
        Compra.cliente_id == current_user.id,
        Compra.ativo.isnot(False)
    )
    
    # Filtros de período
    periodo = request.args.get('periodo')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    if periodo and periodo != 'personalizado':
        hoje = datetime.now()
        if periodo == 'hoje':
            data_inicio_dt = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
            data_fim_dt = hoje.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif periodo == 'semana':
            data_inicio_dt = hoje - timedelta(days=hoje.weekday())
            data_fim_dt = data_inicio_dt + timedelta(days=6)
        elif periodo == 'mes':
            data_inicio_dt = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            data_fim_dt = (data_inicio_dt + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        elif periodo == 'trimestre':
            mes_inicio = ((hoje.month - 1) // 3) * 3 + 1
            data_inicio_dt = hoje.replace(month=mes_inicio, day=1, hour=0, minute=0, second=0, microsecond=0)
            data_fim_dt = (data_inicio_dt + timedelta(days=93)).replace(day=1) - timedelta(days=1)
        elif periodo == 'ano':
            data_inicio_dt = hoje.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            data_fim_dt = hoje.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
        
        query = query.filter(Compra.data_compra >= data_inicio_dt, Compra.data_compra <= data_fim_dt)
    
    elif data_inicio and data_fim:
        data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
        data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
        query = query.filter(Compra.data_compra >= data_inicio_dt, Compra.data_compra <= data_fim_dt)
    
    # Filtros básicos
    polo_id = request.args.get('polo_id')
    if polo_id:
        query = query.filter(Compra.polo_id == polo_id)
    
    status = request.args.get('status')
    if status:
        query = query.filter(Compra.status == status)
    
    fornecedor = request.args.get('fornecedor')
    if fornecedor:
        query = query.filter(Compra.fornecedor.ilike(f'%{fornecedor}%'))
    
    # Filtros avançados
    tipo_gasto = request.args.get('tipo_gasto')
    if tipo_gasto:
        query = query.filter(Compra.tipo_gasto == tipo_gasto)
    
    categoria_material = request.args.get('categoria_material')
    if categoria_material:
        # Filtrar compras que tenham itens com materiais da categoria especificada
        query = query.join(ItemCompra).join(Material).filter(Material.categoria == categoria_material)
    
    tipo_documento = request.args.get('tipo_documento')
    if tipo_documento:
        # Filtrar compras que tenham documentos do tipo especificado
        query = query.join(DocumentoFiscal).filter(DocumentoFiscal.tipo_documento == tipo_documento)
    
    numero_documento = request.args.get('numero_documento')
    if numero_documento:
        # Filtrar compras que tenham documentos com o número especificado
        query = query.join(DocumentoFiscal).filter(DocumentoFiscal.numero_documento.ilike(f'%{numero_documento}%'))
    
    # Filtros de valor
    valor_min = request.args.get('valor_min')
    if valor_min:
        query = query.filter(Compra.valor_total >= float(valor_min))
    
    valor_max = request.args.get('valor_max')
    if valor_max:
        query = query.filter(Compra.valor_total <= float(valor_max))
    
    # Ordenação
    ordenacao = request.args.get('ordenacao', 'data_desc')
    if ordenacao == 'data_asc':
        query = query.order_by(Compra.data_compra.asc())
    elif ordenacao == 'valor_desc':
        query = query.order_by(Compra.valor_total.desc())
    elif ordenacao == 'valor_asc':
        query = query.order_by(Compra.valor_total.asc())
    elif ordenacao == 'fornecedor':
        query = query.order_by(Compra.fornecedor.asc())
    elif ordenacao == 'polo':
        query = query.join(Polo).order_by(Polo.nome.asc())
    else:  # data_desc (padrão)
        query = query.order_by(Compra.data_compra.desc())
    
    # Executar query
    compras = query.distinct().all()
    
    # Calcular estatísticas
    total_compras = len(compras)
    valor_total = sum(compra.valor_total for compra in compras)
    valor_medio = valor_total / total_compras if total_compras > 0 else 0
    fornecedores_unicos = len(set(compra.fornecedor for compra in compras))
    
    estatisticas = {
        'total_compras': total_compras,
        'valor_total': valor_total,
        'valor_medio': valor_medio,
        'total_fornecedores': fornecedores_unicos
    }
    
    # Dados para gráficos
    # Compras por mês
    compras_por_mes = defaultdict(float)
    for compra in compras:
        mes_ano = compra.data_compra.strftime('%Y-%m')
        compras_por_mes[mes_ano] += compra.valor_total
    
    meses = sorted(compras_por_mes.keys())
    valores_mes = [compras_por_mes[mes] for mes in meses]
    meses_formatados = [datetime.strptime(mes, '%Y-%m').strftime('%m/%Y') for mes in meses]
    
    # Compras por polo
    compras_por_polo = defaultdict(float)
    for compra in compras:
        polo_nome = compra.polo.nome if compra.polo else 'Sem Polo'
        compras_por_polo[polo_nome] += compra.valor_total
    
    polos = list(compras_por_polo.keys())
    valores_polo = list(compras_por_polo.values())
    
    graficos = {
        'meses': meses_formatados,
        'valores_mes': valores_mes,
        'polos': polos,
        'valores_polo': valores_polo
    }
    
    return {
        'compras': compras,
        'estatisticas': estatisticas,
        'graficos': graficos
    }


# ==================== ROTAS PRINCIPAIS ====================

@compra_routes.route('/gerenciar-compras')
@login_required
def gerenciar_compras():
    """Página principal de gerenciamento de compras."""
    if not verificar_acesso_cliente():
        flash('Acesso negado', 'error')
        return redirect(url_for('evento_routes.home'))
    
    try:
        # Estatísticas gerais
        total_compras = Compra.query.filter(
            Compra.cliente_id == current_user.id,
            Compra.ativo.isnot(False)
        ).count()
        
        compras_pendentes = Compra.query.filter(
            Compra.cliente_id == current_user.id,
            Compra.ativo.isnot(False),
            Compra.status == 'pendente'
        ).count()
        
        compras_mes = Compra.query.filter(
            Compra.cliente_id == current_user.id,
            Compra.ativo.isnot(False),
            Compra.data_compra >= datetime.now().replace(day=1)
        ).count()
        
        # Valor total das compras do mês
        valor_mes = db.session.query(func.sum(Compra.valor_total)).filter(
            Compra.cliente_id == current_user.id,
            Compra.ativo.isnot(False),
            Compra.data_compra >= datetime.now().replace(day=1)
        ).scalar() or 0
        
        # Buscar polos do cliente
        polos = Polo.query.filter_by(cliente_id=current_user.id, ativo=True).all()
        
        estatisticas = {
            'total_compras': total_compras,
            'compras_pendentes': compras_pendentes,
            'compras_mes': compras_mes,
            'valor_mes': valor_mes
        }
        
        return render_template('compra/gerenciar_compras.html',
                             estatisticas=estatisticas,
                             polos=polos)
    
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar página de compras: {e}")
        flash('Erro ao carregar dados', 'error')
        return redirect(url_for('evento_routes.home'))


@compra_routes.route('/nova-compra')
@login_required
def nova_compra():
    """Página para cadastro de nova compra."""
    if not verificar_acesso_cliente():
        flash('Acesso negado', 'error')
        return redirect(url_for('evento_routes.home'))
    
    try:
        polos = Polo.query.filter_by(cliente_id=current_user.id, ativo=True).all()
        materiais = Material.query.filter_by(cliente_id=current_user.id, ativo=True).all()
        
        return render_template('compra/nova_compra.html', polos=polos, materiais=materiais)
    
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar página de nova compra: {e}")
        flash('Erro ao carregar dados', 'error')
        return redirect(url_for('compra_routes.gerenciar_compras'))


@compra_routes.route('/prestacao-contas')
@login_required
def prestacao_contas():
    """Página de prestação de contas."""
    if not verificar_acesso_cliente():
        flash('Acesso negado', 'error')
        return redirect(url_for('evento_routes.home'))
    
    try:
        # Estatísticas de prestação de contas
        total_prestacoes = PrestacaoContas.query.filter(
            PrestacaoContas.cliente_id == current_user.id,
            PrestacaoContas.ativo.isnot(False)
        ).count()
        
        prestacoes_pendentes = PrestacaoContas.query.filter(
            PrestacaoContas.cliente_id == current_user.id,
            PrestacaoContas.ativo.isnot(False),
            PrestacaoContas.status == 'rascunho'
        ).count()
        
        prestacoes_enviadas = PrestacaoContas.query.filter(
            PrestacaoContas.cliente_id == current_user.id,
            PrestacaoContas.ativo.isnot(False),
            PrestacaoContas.status == 'enviada'
        ).count()
        
        estatisticas = {
            'total_prestacoes': total_prestacoes,
            'prestacoes_pendentes': prestacoes_pendentes,
            'prestacoes_enviadas': prestacoes_enviadas
        }
        
        return render_template('compra/prestacao_contas.html', estatisticas=estatisticas)
    
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar prestação de contas: {e}")
        flash('Erro ao carregar dados', 'error')
        return redirect(url_for('compra_routes.gerenciar_compras'))


@compra_routes.route('/relatorios-compras')
@login_required
def relatorios_compras():
    """Página de relatórios de compras."""
    if not verificar_acesso_cliente():
        flash('Acesso negado', 'error')
        return redirect(url_for('evento_routes.home'))
    
    try:
        # Buscar relatórios salvos
        relatorios_salvos = RelatorioCompra.query.filter(
            or_(
                RelatorioCompra.cliente_id == current_user.id,
                RelatorioCompra.publico == True
            ),
            RelatorioCompra.ativo.isnot(False)
        ).all()
        
        polos = Polo.query.filter_by(cliente_id=current_user.id, ativo=True).all()
        
        # Buscar categorias de materiais únicas para o filtro
        categorias_materiais = db.session.query(Material.categoria).filter(
            Material.cliente_id == current_user.id,
            Material.categoria.isnot(None),
            Material.categoria != '',
            Material.ativo == True
        ).distinct().order_by(Material.categoria).all()
        categorias_materiais = [cat[0] for cat in categorias_materiais if cat[0]]
        
        # Aplicar filtros se fornecidos
        compras = []
        estatisticas = {}
        graficos = {}
        
        # Verificar se há parâmetros de filtro
        if any(request.args.get(param) for param in ['periodo', 'data_inicio', 'data_fim', 'polo_id', 'status', 'tipo_gasto', 'categoria_material', 'tipo_documento', 'fornecedor', 'valor_min', 'valor_max', 'numero_documento']):
            # Aplicar filtros e gerar relatório
            resultado_filtros = aplicar_filtros_relatorio()
            compras = resultado_filtros['compras']
            estatisticas = resultado_filtros['estatisticas']
            graficos = resultado_filtros['graficos']
        
        return render_template('compra/relatorios_compras.html', 
                             relatorios_salvos=relatorios_salvos,
                             polos=polos,
                             categorias_materiais=categorias_materiais,
                             compras=compras,
                             estatisticas=estatisticas,
                             graficos=graficos)
    
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar relatórios: {e}")
        flash('Erro ao carregar dados', 'error')
        return redirect(url_for('compra_routes.gerenciar_compras'))


@compra_routes.route('/dashboard-cronologico')
@login_required
def dashboard_cronologico():
    """Página do dashboard cronológico de compras."""
    if not verificar_acesso_cliente():
        flash('Acesso negado', 'error')
        return redirect(url_for('evento_routes.home'))
    
    try:
        polos = Polo.query.filter_by(cliente_id=current_user.id, ativo=True).all()
        return render_template('compra/dashboard_cronologico.html', polos=polos)
    
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar dashboard cronológico: {e}")
        flash('Erro ao carregar dados', 'error')
        return redirect(url_for('compra_routes.gerenciar_compras'))


# ==================== API ENDPOINTS ====================

@compra_routes.route('/api/compras', methods=['GET'])
@login_required
def api_listar_compras():
    """API para listar compras com filtros."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        # Parâmetros de filtro
        polo_id = request.args.get('polo_id', type=int)
        status = request.args.get('status')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        fornecedor = request.args.get('fornecedor')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Query base
        query = Compra.query.filter(
            Compra.cliente_id == current_user.id,
            Compra.ativo.isnot(False)
        )
        
        # Aplicar filtros
        if polo_id:
            query = query.filter(Compra.polo_id == polo_id)
        
        if status:
            query = query.filter(Compra.status == status)
        
        if fornecedor:
            query = query.filter(Compra.fornecedor.ilike(f'%{fornecedor}%'))
        
        if data_inicio:
            data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(Compra.data_compra >= data_inicio_dt)
        
        if data_fim:
            data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
            query = query.filter(Compra.data_compra <= data_fim_dt)
        
        # Ordenação
        query = query.order_by(desc(Compra.data_compra))
        
        # Paginação
        compras = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'compras': [compra.to_dict() for compra in compras.items],
            'total': compras.total,
            'pages': compras.pages,
            'current_page': page
        })
    
    except Exception as e:
        current_app.logger.error(f"Erro ao listar compras: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@compra_routes.route('/api/compras', methods=['POST'])
@login_required
def api_criar_compra():
    """API para criar nova compra."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        data = request.get_json()
        
        # Validações básicas
        if not data.get('fornecedor'):
            return jsonify({'success': False, 'message': 'Fornecedor é obrigatório'}), 400
        
        if not data.get('itens') or len(data.get('itens', [])) == 0:
            return jsonify({'success': False, 'message': 'Pelo menos um item é obrigatório'}), 400
        
        # Validar polo se fornecido
        polo_id = data.get('polo_id')
        if polo_id:
            polo = Polo.query.filter_by(id=polo_id, cliente_id=current_user.id, ativo=True).first()
            if not polo:
                return jsonify({'success': False, 'message': 'Polo inválido ou não pertence ao cliente'}), 400
        
        # Criar compra
        compra = Compra(
            numero_compra=gerar_numero_compra(),
            descricao=data.get('descricao'),
            fornecedor=data.get('fornecedor'),
            cnpj_fornecedor=data.get('cnpj_fornecedor'),
            endereco_fornecedor=data.get('endereco_fornecedor'),
            telefone_fornecedor=data.get('telefone_fornecedor'),
            email_fornecedor=data.get('email_fornecedor'),
            valor_total=float(data.get('valor_total', 0)),
            valor_frete=float(data.get('valor_frete', 0)),
            valor_desconto=float(data.get('valor_desconto', 0)),
            valor_impostos=float(data.get('valor_impostos', 0)),
            data_compra=datetime.strptime(data.get('data_compra'), '%Y-%m-%d') if data.get('data_compra') else datetime.utcnow(),
            data_entrega_prevista=datetime.strptime(data.get('data_entrega_prevista'), '%Y-%m-%d') if data.get('data_entrega_prevista') else None,
            status=data.get('status', 'pendente'),
            observacoes=data.get('observacoes'),
            justificativa=data.get('justificativa'),
            tipo_gasto=data.get('tipo_gasto', 'custeio'),  # Novo campo com valor padrão
            polo_id=polo_id,  # Agora opcional
            cliente_id=current_user.id,
            usuario_id=current_user.id
        )
        
        db.session.add(compra)
        db.session.flush()  # Para obter o ID da compra
        
        # Criar itens da compra
        for item_data in data.get('itens', []):
            item = ItemCompra(
                descricao=item_data.get('descricao'),
                quantidade=float(item_data.get('quantidade')),
                unidade=item_data.get('unidade', 'unidade'),
                preco_unitario=float(item_data.get('preco_unitario')),
                valor_total=float(item_data.get('valor_total')),
                observacoes=item_data.get('observacoes'),
                material_id=item_data.get('material_id'),
                compra_id=compra.id
            )
            db.session.add(item)
        
        db.session.commit()
        
        # Iniciar processo de aprovação
        try:
            from services.aprovacao_service import AprovacaoService
            AprovacaoService.iniciar_processo_aprovacao(compra.id)
        except Exception as e:
            current_app.logger.warning(f"Erro ao iniciar processo de aprovação para compra {compra.id}: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Compra criada com sucesso',
            'compra': compra.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao criar compra: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@compra_routes.route('/api/compras/<int:compra_id>', methods=['GET'])
@login_required
def api_obter_compra(compra_id):
    """API para obter detalhes de uma compra."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        compra = Compra.query.filter_by(
            id=compra_id, 
            cliente_id=current_user.id,
            ativo=True
        ).first()
        
        if not compra:
            return jsonify({'success': False, 'message': 'Compra não encontrada'}), 404
        
        # Incluir itens e documentos
        compra_dict = compra.to_dict()
        compra_dict['itens'] = [item.to_dict() for item in compra.itens]
        compra_dict['documentos'] = [doc.to_dict() for doc in compra.documentos if doc.ativo]
        
        return jsonify({
            'success': True,
            'compra': compra_dict
        })
    
    except Exception as e:
        current_app.logger.error(f"Erro ao obter compra {compra_id}: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@compra_routes.route('/api/compras/<int:compra_id>', methods=['PUT'])
@login_required
def api_atualizar_compra(compra_id):
    """API para atualizar uma compra."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        compra = Compra.query.filter_by(
            id=compra_id, 
            cliente_id=current_user.id,
            ativo=True
        ).first()
        
        if not compra:
            return jsonify({'success': False, 'message': 'Compra não encontrada'}), 404
        
        data = request.get_json()
        
        # Atualizar campos da compra
        compra.descricao = data.get('descricao', compra.descricao)
        compra.fornecedor = data.get('fornecedor', compra.fornecedor)
        compra.cnpj_fornecedor = data.get('cnpj_fornecedor', compra.cnpj_fornecedor)
        compra.endereco_fornecedor = data.get('endereco_fornecedor', compra.endereco_fornecedor)
        compra.telefone_fornecedor = data.get('telefone_fornecedor', compra.telefone_fornecedor)
        compra.email_fornecedor = data.get('email_fornecedor', compra.email_fornecedor)
        compra.valor_total = float(data.get('valor_total', compra.valor_total))
        compra.valor_frete = float(data.get('valor_frete', compra.valor_frete or 0))
        compra.valor_desconto = float(data.get('valor_desconto', compra.valor_desconto or 0))
        compra.valor_impostos = float(data.get('valor_impostos', compra.valor_impostos or 0))
        compra.status = data.get('status', compra.status)
        compra.observacoes = data.get('observacoes', compra.observacoes)
        compra.justificativa = data.get('justificativa', compra.justificativa)
        compra.polo_id = data.get('polo_id', compra.polo_id)
        
        if data.get('data_entrega_prevista'):
            compra.data_entrega_prevista = datetime.strptime(data.get('data_entrega_prevista'), '%Y-%m-%d')
        
        if data.get('data_entrega_realizada'):
            compra.data_entrega_realizada = datetime.strptime(data.get('data_entrega_realizada'), '%Y-%m-%d')
        
        compra.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Compra atualizada com sucesso',
            'compra': compra.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao atualizar compra {compra_id}: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@compra_routes.route('/api/compras/<int:compra_id>', methods=['DELETE'])
@login_required
def api_deletar_compra(compra_id):
    """API para deletar (desativar) uma compra."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        compra = Compra.query.filter_by(
            id=compra_id, 
            cliente_id=current_user.id,
            ativo=True
        ).first()
        
        if not compra:
            return jsonify({'success': False, 'message': 'Compra não encontrada'}), 404
        
        compra.ativo = False
        compra.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Compra deletada com sucesso'
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao deletar compra {compra_id}: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


# ==================== UPLOAD DE DOCUMENTOS ====================

@compra_routes.route('/api/compras/<int:compra_id>/documentos', methods=['POST'])
@login_required
def api_upload_documento(compra_id):
    """API para upload de documentos fiscais."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        compra = Compra.query.filter_by(
            id=compra_id, 
            cliente_id=current_user.id,
            ativo=True
        ).first()
        
        if not compra:
            return jsonify({'success': False, 'message': 'Compra não encontrada'}), 404
        
        arquivo = request.files.get('arquivo')
        if not arquivo:
            return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'}), 400
        
        if arquivo.filename == '':
            return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'}), 400
        
        # Usar o novo serviço de validação
        tipo_documento = request.form.get('tipo_documento', 'outros')
        validation_result = CompraService.validate_fiscal_document(arquivo, tipo_documento)
        
        if not validation_result['valid']:
            errors = validation_result['errors']
            return jsonify({
                'success': False, 
                'message': 'Arquivo inválido: ' + '; '.join(errors),
                'errors': errors
            }), 400
        
        # Verificar limite total de upload para a compra
        file_size = validation_result['file_info']['size']
        if not CompraService.validate_total_upload_size(compra_id, file_size):
            return jsonify({
                'success': False, 
                'message': f'Limite total de arquivos excedido (máximo {CompraService.MAX_TOTAL_SIZE_MB}MB por compra)'
            }), 400
        
        # Gerar nome seguro para o arquivo
        secure_filename_generated = CompraService.generate_secure_filename(arquivo.filename, compra_id)
        
        # Criar diretório seguro
        upload_path = CompraService.create_upload_directory(compra_id)
        
        # Salvar arquivo
        filepath = os.path.join(upload_path, secure_filename_generated)
        arquivo.save(filepath)
        
        # Calcular hash do arquivo para integridade
        file_hash = CompraService.calculate_file_hash(arquivo)
        
        # Escaneamento básico de segurança
        scan_result = CompraService.scan_for_malware(filepath)
        if not scan_result['safe']:
            # Remover arquivo se não for seguro
            try:
                os.remove(filepath)
            except:
                pass
            return jsonify({
                'success': False,
                'message': 'Arquivo rejeitado por questões de segurança: ' + '; '.join(scan_result['threats'])
            }), 400
        
        # Criar registro no banco
        documento = DocumentoFiscal(
            tipo_documento=tipo_documento,
            numero_documento=request.form.get('numero_documento'),
            serie_documento=request.form.get('serie_documento'),
            chave_acesso=request.form.get('chave_acesso'),
            nome_arquivo=validation_result['file_info']['original_name'],
            nome_arquivo_seguro=secure_filename_generated,
            caminho_arquivo=filepath,
            tamanho_arquivo=file_size,
            tipo_mime=arquivo.content_type,
            hash_arquivo=file_hash,
            data_emissao=datetime.strptime(request.form.get('data_emissao'), '%Y-%m-%d') if request.form.get('data_emissao') else None,
            valor_documento=float(request.form.get('valor_documento')) if request.form.get('valor_documento') else None,
            observacoes=request.form.get('observacoes'),
            compra_id=compra_id,
            usuario_upload_id=current_user.id,
            validacao_resultado=json.dumps(validation_result),
            scan_seguranca=json.dumps(scan_result)
        )
        
        db.session.add(documento)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Documento enviado com sucesso',
            'documento': documento.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao fazer upload de documento: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@compra_routes.route('/api/documentos/<int:documento_id>/download')
@login_required
def api_download_documento(documento_id):
    """API para download de documentos fiscais."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        documento = DocumentoFiscal.query.join(Compra).filter(
            DocumentoFiscal.id == documento_id,
            Compra.cliente_id == current_user.id,
            DocumentoFiscal.ativo == True
        ).first()
        
        if not documento:
            return jsonify({'success': False, 'message': 'Documento não encontrado'}), 404
        
        if not os.path.exists(documento.caminho_arquivo):
            return jsonify({'success': False, 'message': 'Arquivo não encontrado no servidor'}), 404
        
        return send_file(
            documento.caminho_arquivo,
            as_attachment=True,
            download_name=documento.nome_arquivo
        )
    
    except Exception as e:
        current_app.logger.error(f"Erro ao fazer download do documento {documento_id}: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


# ==================== PRESTAÇÃO DE CONTAS ====================

@compra_routes.route('/api/prestacoes', methods=['GET'])
@login_required
def api_listar_prestacoes():
    """API para listar prestações de contas."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        
        query = PrestacaoContas.query.filter(
            PrestacaoContas.cliente_id == current_user.id,
            PrestacaoContas.ativo.isnot(False)
        )
        
        if status:
            query = query.filter(PrestacaoContas.status == status)
        
        query = query.order_by(desc(PrestacaoContas.created_at))
        
        prestacoes = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'prestacoes': [prestacao.to_dict() for prestacao in prestacoes.items],
            'total': prestacoes.total,
            'pages': prestacoes.pages,
            'current_page': page
        })
    
    except Exception as e:
        current_app.logger.error(f"Erro ao listar prestações: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@compra_routes.route('/api/prestacoes', methods=['POST'])
@login_required
def api_criar_prestacao():
    """API para criar nova prestação de contas."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        data = request.get_json()
        
        # Validações
        if not data.get('titulo'):
            return jsonify({'success': False, 'message': 'Título é obrigatório'}), 400
        
        if not data.get('data_inicio') or not data.get('data_fim'):
            return jsonify({'success': False, 'message': 'Período é obrigatório'}), 400
        
        # Criar prestação
        prestacao = PrestacaoContas(
            numero_prestacao=gerar_numero_prestacao(),
            titulo=data.get('titulo'),
            descricao=data.get('descricao'),
            data_inicio=datetime.strptime(data.get('data_inicio'), '%Y-%m-%d'),
            data_fim=datetime.strptime(data.get('data_fim'), '%Y-%m-%d'),
            observacoes=data.get('observacoes'),
            cliente_id=current_user.id,
            usuario_id=current_user.id
        )
        
        db.session.add(prestacao)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Prestação de contas criada com sucesso',
            'prestacao': prestacao.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao criar prestação: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


# ==================== RELATÓRIOS ====================

@compra_routes.route('/api/relatorios/compras', methods=['GET'])
@login_required
def api_relatorio_compras():
    """API para gerar relatório de compras com filtros personalizáveis."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        # Parâmetros de filtro
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        polo_id = request.args.get('polo_id', type=int)
        status = request.args.get('status')
        fornecedor = request.args.get('fornecedor')
        ordenacao = request.args.get('ordenacao', 'data_compra')
        ordem = request.args.get('ordem', 'desc')
        
        # Query base
        query = Compra.query.filter(
            Compra.cliente_id == current_user.id,
            Compra.ativo.isnot(False)
        )
        
        # Aplicar filtros
        if data_inicio:
            query = query.filter(Compra.data_compra >= datetime.strptime(data_inicio, '%Y-%m-%d'))
        
        if data_fim:
            query = query.filter(Compra.data_compra <= datetime.strptime(data_fim, '%Y-%m-%d'))
        
        if polo_id:
            query = query.filter(Compra.polo_id == polo_id)
        
        if status:
            query = query.filter(Compra.status == status)
        
        if fornecedor:
            query = query.filter(Compra.fornecedor.ilike(f'%{fornecedor}%'))
        
        # Ordenação
        if hasattr(Compra, ordenacao):
            campo_ordenacao = getattr(Compra, ordenacao)
            if ordem == 'asc':
                query = query.order_by(asc(campo_ordenacao))
            else:
                query = query.order_by(desc(campo_ordenacao))
        
        compras = query.all()
        
        # Calcular totais
        valor_total = sum(compra.valor_total or 0 for compra in compras)
        valor_liquido = sum(compra.valor_liquido for compra in compras)
        
        return jsonify({
            'success': True,
            'compras': [compra.to_dict() for compra in compras],
            'resumo': {
                'total_compras': len(compras),
                'valor_total': valor_total,
                'valor_liquido': valor_liquido
            }
        })
    
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar relatório: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@compra_routes.route('/api/relatorios/cronologico', methods=['GET'])
@login_required
def api_relatorio_cronologico():
    """API para relatório cronológico com análise temporal de compras."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        # Parâmetros
        periodo = request.args.get('periodo', 'mensal')  # diario, semanal, mensal, trimestral, anual
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        polo_id = request.args.get('polo_id', type=int)
        comparar_periodo_anterior = request.args.get('comparar_anterior', 'false').lower() == 'true'
        
        # Definir datas padrão se não fornecidas
        if not data_fim:
            data_fim = datetime.now()
        else:
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d')
            
        if not data_inicio:
            if periodo == 'diario':
                data_inicio = data_fim - timedelta(days=30)
            elif periodo == 'semanal':
                data_inicio = data_fim - timedelta(weeks=12)
            elif periodo == 'mensal':
                data_inicio = data_fim - timedelta(days=365)
            elif periodo == 'trimestral':
                data_inicio = data_fim - timedelta(days=730)
            else:  # anual
                data_inicio = data_fim - timedelta(days=1095)
        else:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
        
        # Query base
        query = Compra.query.filter(
            Compra.cliente_id == current_user.id,
            Compra.ativo.isnot(False),
            Compra.data_compra >= data_inicio,
            Compra.data_compra <= data_fim
        )
        
        if polo_id:
            query = query.filter(Compra.polo_id == polo_id)
        
        compras = query.all()
        
        # Agrupar dados por período
        dados_cronologicos = {}
        for compra in compras:
            if periodo == 'diario':
                chave = compra.data_compra.strftime('%Y-%m-%d')
            elif periodo == 'semanal':
                # Primeira data da semana
                inicio_semana = compra.data_compra - timedelta(days=compra.data_compra.weekday())
                chave = inicio_semana.strftime('%Y-%m-%d')
            elif periodo == 'mensal':
                chave = compra.data_compra.strftime('%Y-%m')
            elif periodo == 'trimestral':
                trimestre = (compra.data_compra.month - 1) // 3 + 1
                chave = f"{compra.data_compra.year}-T{trimestre}"
            else:  # anual
                chave = compra.data_compra.strftime('%Y')
            
            if chave not in dados_cronologicos:
                dados_cronologicos[chave] = {
                    'periodo': chave,
                    'total_compras': 0,
                    'valor_total': 0,
                    'valor_liquido': 0,
                    'compras': []
                }
            
            dados_cronologicos[chave]['total_compras'] += 1
            dados_cronologicos[chave]['valor_total'] += compra.valor_total or 0
            dados_cronologicos[chave]['valor_liquido'] += compra.valor_liquido or 0
            dados_cronologicos[chave]['compras'].append(compra.to_dict())
        
        # Ordenar por período
        dados_ordenados = sorted(dados_cronologicos.values(), key=lambda x: x['periodo'])
        
        # Calcular estatísticas
        total_geral = sum(item['valor_total'] for item in dados_ordenados)
        media_periodo = total_geral / len(dados_ordenados) if dados_ordenados else 0
        
        # Comparação com período anterior se solicitado
        comparacao = None
        if comparar_periodo_anterior and dados_ordenados:
            duracao = data_fim - data_inicio
            data_inicio_anterior = data_inicio - duracao
            data_fim_anterior = data_inicio
            
            query_anterior = Compra.query.filter(
                Compra.cliente_id == current_user.id,
                Compra.ativo.isnot(False),
                Compra.data_compra >= data_inicio_anterior,
                Compra.data_compra < data_fim_anterior
            )
            
            if polo_id:
                query_anterior = query_anterior.filter(Compra.polo_id == polo_id)
            
            compras_anterior = query_anterior.all()
            valor_anterior = sum(c.valor_total or 0 for c in compras_anterior)
            
            if valor_anterior > 0:
                variacao_percentual = ((total_geral - valor_anterior) / valor_anterior) * 100
            else:
                variacao_percentual = 100 if total_geral > 0 else 0
            
            comparacao = {
                'periodo_anterior': {
                    'inicio': data_inicio_anterior.strftime('%Y-%m-%d'),
                    'fim': data_fim_anterior.strftime('%Y-%m-%d'),
                    'total_compras': len(compras_anterior),
                    'valor_total': valor_anterior
                },
                'variacao_percentual': round(variacao_percentual, 2),
                'tendencia': 'alta' if variacao_percentual > 0 else 'baixa' if variacao_percentual < 0 else 'estavel'
            }
        
        return jsonify({
            'success': True,
            'periodo': periodo,
            'data_inicio': data_inicio.strftime('%Y-%m-%d'),
            'data_fim': data_fim.strftime('%Y-%m-%d'),
            'dados_cronologicos': dados_ordenados,
            'estatisticas': {
                'total_geral': total_geral,
                'total_compras': len(compras),
                'media_por_periodo': round(media_periodo, 2),
                'periodos_analisados': len(dados_ordenados)
            },
            'comparacao': comparacao
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar relatório cronológico: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@compra_routes.route('/api/relatorios/dashboard', methods=['GET'])
@login_required
def api_dashboard_compras():
    """API para dashboard com métricas e KPIs de compras."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        polo_id = request.args.get('polo_id', type=int)
        
        # Período atual (últimos 30 dias)
        data_fim = datetime.now()
        data_inicio = data_fim - timedelta(days=30)
        
        # Query base
        query_base = Compra.query.filter(
            Compra.cliente_id == current_user.id,
            Compra.ativo.isnot(False)
        )
        
        if polo_id:
            query_base = query_base.filter(Compra.polo_id == polo_id)
        
        # Compras do período atual
        compras_periodo = query_base.filter(
            Compra.data_compra >= data_inicio,
            Compra.data_compra <= data_fim
        ).all()
        
        # Compras do período anterior (para comparação)
        data_inicio_anterior = data_inicio - timedelta(days=30)
        compras_anterior = query_base.filter(
            Compra.data_compra >= data_inicio_anterior,
            Compra.data_compra < data_inicio
        ).all()
        
        # Métricas principais
        valor_atual = sum(c.valor_total or 0 for c in compras_periodo)
        valor_anterior = sum(c.valor_total or 0 for c in compras_anterior)
        
        # Calcular variações
        def calcular_variacao(atual, anterior):
            if anterior > 0:
                return round(((atual - anterior) / anterior) * 100, 2)
            return 100 if atual > 0 else 0
        
        # Status das compras
        status_count = {}
        for compra in compras_periodo:
            status = compra.status or 'pendente'
            status_count[status] = status_count.get(status, 0) + 1
        
        # Top fornecedores
        fornecedores = {}
        for compra in compras_periodo:
            fornecedor = compra.fornecedor or 'Não informado'
            if fornecedor not in fornecedores:
                fornecedores[fornecedor] = {'total': 0, 'compras': 0}
            fornecedores[fornecedor]['total'] += compra.valor_total or 0
            fornecedores[fornecedor]['compras'] += 1
        
        top_fornecedores = sorted(
            [{'nome': k, **v} for k, v in fornecedores.items()],
            key=lambda x: x['total'],
            reverse=True
        )[:5]
        
        # Compras por polo (se não filtrado)
        compras_por_polo = []
        if not polo_id:
            from sqlalchemy import func
            resultado_polos = db.session.query(
                Polo.nome,
                func.count(Compra.id).label('total_compras'),
                func.sum(Compra.valor_total).label('valor_total')
            ).join(Compra).filter(
                Compra.cliente_id == current_user.id,
                Compra.ativo.isnot(False),
                Compra.data_compra >= data_inicio,
                Compra.data_compra <= data_fim
            ).group_by(Polo.id, Polo.nome).all()
            
            compras_por_polo = [
                {
                    'polo': resultado.nome,
                    'total_compras': resultado.total_compras,
                    'valor_total': float(resultado.valor_total or 0)
                }
                for resultado in resultado_polos
            ]
        
        return jsonify({
            'success': True,
            'metricas': {
                'valor_total': {
                    'atual': valor_atual,
                    'anterior': valor_anterior,
                    'variacao': calcular_variacao(valor_atual, valor_anterior)
                },
                'total_compras': {
                    'atual': len(compras_periodo),
                    'anterior': len(compras_anterior),
                    'variacao': calcular_variacao(len(compras_periodo), len(compras_anterior))
                },
                'ticket_medio': {
                    'atual': round(valor_atual / len(compras_periodo), 2) if compras_periodo else 0,
                    'anterior': round(valor_anterior / len(compras_anterior), 2) if compras_anterior else 0
                }
            },
            'distribuicoes': {
                'status': status_count,
                'top_fornecedores': top_fornecedores,
                'compras_por_polo': compras_por_polo
            },
            'periodo': {
                'inicio': data_inicio.strftime('%Y-%m-%d'),
                'fim': data_fim.strftime('%Y-%m-%d')
            }
        })
        
    except Exception as e:
         current_app.logger.error(f"Erro ao gerar dashboard: {e}")
         return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@compra_routes.route('/api/relatorios/exportar', methods=['GET'])
@login_required
def exportar_relatorio():
    """Exportar relatório cronológico em Excel."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        import pandas as pd
        from io import BytesIO
        
        # Parâmetros
        periodo = request.args.get('periodo', 'mensal')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        polo_id = request.args.get('polo_id', type=int)
        formato = request.args.get('formato', 'excel')
        
        # Buscar dados cronológicos
        if not data_fim:
            data_fim = datetime.now()
        else:
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d')
            
        if not data_inicio:
            if periodo == 'diario':
                data_inicio = data_fim - timedelta(days=30)
            elif periodo == 'semanal':
                data_inicio = data_fim - timedelta(weeks=12)
            elif periodo == 'mensal':
                data_inicio = data_fim - timedelta(days=365)
            elif periodo == 'trimestral':
                data_inicio = data_fim - timedelta(days=730)
            else:  # anual
                data_inicio = data_fim - timedelta(days=1095)
        else:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
        
        # Query base
        query = Compra.query.filter(
            Compra.cliente_id == current_user.id,
            Compra.ativo.isnot(False),
            Compra.data_compra >= data_inicio,
            Compra.data_compra <= data_fim
        )
        
        if polo_id:
            query = query.filter(Compra.polo_id == polo_id)
        
        compras = query.all()
        
        # Preparar dados para exportação
        dados_exportacao = []
        for compra in compras:
            dados_exportacao.append({
                'ID': compra.id,
                'Data': compra.data_compra.strftime('%d/%m/%Y'),
                'Polo': compra.polo.nome if compra.polo else 'N/A',
                'Fornecedor': compra.fornecedor or 'N/A',
                'CNPJ': compra.cnpj_fornecedor or 'N/A',
                'Valor Total': compra.valor_total or 0,
                'Valor Líquido': compra.valor_liquido or 0,
                'Status': compra.status or 'Pendente',
                'Observações': compra.observacoes or '',
                'Total de Itens': len(compra.itens) if compra.itens else 0,
                'Total de Documentos': len(compra.documentos) if compra.documentos else 0
            })
        
        if formato == 'excel':
            # Criar arquivo Excel
            output = BytesIO()
            
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Aba principal com dados das compras
                df_compras = pd.DataFrame(dados_exportacao)
                df_compras.to_excel(writer, sheet_name='Compras', index=False)
                
                # Aba com resumo por período
                dados_cronologicos = {}
                for compra in compras:
                    if periodo == 'diario':
                        chave = compra.data_compra.strftime('%Y-%m-%d')
                    elif periodo == 'semanal':
                        inicio_semana = compra.data_compra - timedelta(days=compra.data_compra.weekday())
                        chave = inicio_semana.strftime('%Y-%m-%d')
                    elif periodo == 'mensal':
                        chave = compra.data_compra.strftime('%Y-%m')
                    elif periodo == 'trimestral':
                        trimestre = (compra.data_compra.month - 1) // 3 + 1
                        chave = f"{compra.data_compra.year}-T{trimestre}"
                    else:  # anual
                        chave = compra.data_compra.strftime('%Y')
                    
                    if chave not in dados_cronologicos:
                        dados_cronologicos[chave] = {
                            'Período': chave,
                            'Total de Compras': 0,
                            'Valor Total': 0,
                            'Valor Líquido': 0
                        }
                    
                    dados_cronologicos[chave]['Total de Compras'] += 1
                    dados_cronologicos[chave]['Valor Total'] += compra.valor_total or 0
                    dados_cronologicos[chave]['Valor Líquido'] += compra.valor_liquido or 0
                
                df_resumo = pd.DataFrame(list(dados_cronologicos.values()))
                df_resumo.to_excel(writer, sheet_name='Resumo por Período', index=False)
                
                # Aba com estatísticas
                estatisticas = {
                    'Métrica': [
                        'Total de Compras',
                        'Valor Total',
                        'Valor Líquido',
                        'Ticket Médio',
                        'Período Analisado'
                    ],
                    'Valor': [
                        len(compras),
                        sum(c.valor_total or 0 for c in compras),
                        sum(c.valor_liquido or 0 for c in compras),
                        (sum(c.valor_total or 0 for c in compras) / len(compras)) if compras else 0,
                        f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
                    ]
                }
                
                df_estatisticas = pd.DataFrame(estatisticas)
                df_estatisticas.to_excel(writer, sheet_name='Estatísticas', index=False)
            
            output.seek(0)
            
            # Nome do arquivo
            nome_arquivo = f"relatorio_compras_{periodo}_{data_inicio.strftime('%Y%m%d')}_{data_fim.strftime('%Y%m%d')}.xlsx"
            
            return send_file(
                output,
                as_attachment=True,
                download_name=nome_arquivo,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        
        else:
            return jsonify({'success': False, 'message': 'Formato não suportado'}), 400
            
    except ImportError:
        return jsonify({'success': False, 'message': 'Biblioteca pandas não disponível'}), 500
    except Exception as e:
        current_app.logger.error(f"Erro ao exportar relatório: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


# ==================== PÁGINA DE UPLOAD ====================

@compra_routes.route('/upload-documento')
@login_required
def upload_documento():
    """Página para upload de documentos fiscais."""
    if not verificar_acesso_cliente():
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard_routes.dashboard_cliente'))
    
    try:
        # Buscar compras ativas do cliente para seleção
        compras = Compra.query.filter_by(
            cliente_id=current_user.id,
            ativo=True
        ).order_by(desc(Compra.created_at)).all()
        
        return render_template('compra/upload_documento.html', compras=compras)
        
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar página de upload: {e}")
        flash('Erro ao carregar página de upload.', 'error')


# ==================== INTEGRAÇÃO COM MATERIAIS ====================

@compra_routes.route('/api/processar-entrega/<int:compra_id>', methods=['POST'])
@login_required
def processar_entrega_compra(compra_id):
    """Processa entrega de compra e atualiza estoque de materiais."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        # Verificar se a compra pertence ao cliente
        compra = Compra.query.filter_by(id=compra_id, cliente_id=current_user.id).first()
        if not compra:
            return jsonify({'success': False, 'message': 'Compra não encontrada'}), 404
        
        # Processar entrega
        resultado = IntegracaoComprasMateriais.processar_entrega_compra(
            compra_id=compra_id,
            usuario_id=current_user.id
        )
        
        if resultado['success']:
            return jsonify({
                'success': True,
                'message': f'Entrega processada com sucesso! {resultado["materiais_atualizados"]} materiais atualizados.',
                'detalhes': resultado['detalhes']
            })
        else:
            return jsonify({'success': False, 'message': resultado['error']}), 400
            
    except Exception as e:
        current_app.logger.error(f"Erro ao processar entrega: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@compra_routes.route('/api/gerar-compra-necessidades', methods=['POST'])
@login_required
def gerar_compra_necessidades():
    """Gera compra baseada em necessidades de estoque."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        data = request.get_json()
        polo_id = data.get('polo_id')
        fornecedor = data.get('fornecedor')
        tipo_gasto = data.get('tipo_gasto', 'custeio')
        
        # Gerar compra sugerida
        resultado = IntegracaoComprasMateriais.gerar_compra_por_necessidades(
            cliente_id=current_user.id,
            polo_id=polo_id,
            fornecedor=fornecedor,
            tipo_gasto=tipo_gasto
        )
        
        if resultado['success']:
            return jsonify({
                'success': True,
                'compra_sugerida': resultado['compra_sugerida'],
                'total_itens': resultado['total_itens'],
                'valor_total_estimado': resultado['valor_total_estimado']
            })
        else:
            return jsonify({'success': False, 'message': resultado.get('message', resultado.get('error'))}), 400
            
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar compra por necessidades: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@compra_routes.route('/api/sincronizar-precos/<int:compra_id>', methods=['POST'])
@login_required
def sincronizar_precos_materiais(compra_id):
    """Sincroniza preços dos materiais baseado na compra."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        # Verificar se a compra pertence ao cliente
        compra = Compra.query.filter_by(id=compra_id, cliente_id=current_user.id).first()
        if not compra:
            return jsonify({'success': False, 'message': 'Compra não encontrada'}), 404
        
        # Sincronizar preços
        resultado = IntegracaoComprasMateriais.sincronizar_precos_materiais(compra_id)
        
        if resultado['success']:
            return jsonify({
                'success': True,
                'message': f'Preços sincronizados! {resultado["materiais_atualizados"]} materiais atualizados.',
                'detalhes': resultado['detalhes']
            })
        else:
            return jsonify({'success': False, 'message': resultado['error']}), 400
            
    except Exception as e:
        current_app.logger.error(f"Erro ao sincronizar preços: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@compra_routes.route('/api/relatorio-necessidades')
@login_required
def relatorio_necessidades():
    """Gera relatório de necessidades de materiais."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        polo_id = request.args.get('polo_id', type=int)
        
        # Gerar relatório
        resultado = IntegracaoComprasMateriais.obter_relatorio_necessidades(
            cliente_id=current_user.id,
            polo_id=polo_id
        )
        
        if resultado['success']:
            return jsonify({
                'success': True,
                'relatorio': resultado['relatorio']
            })
        else:
            return jsonify({'success': False, 'message': resultado['error']}), 400
            
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar relatório de necessidades: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@compra_routes.route('/api/verificar-orcamento', methods=['POST'])
@login_required
def verificar_disponibilidade_orcamento():
    """Verifica disponibilidade orçamentária para compra."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        data = request.get_json()
        valor_compra = float(data.get('valor_compra', 0))
        tipo_gasto = data.get('tipo_gasto', 'custeio')
        
        # Verificar disponibilidade
        resultado = IntegracaoComprasMateriais.verificar_disponibilidade_orcamento(
            cliente_id=current_user.id,
            valor_compra=valor_compra,
            tipo_gasto=tipo_gasto
        )
        
        return jsonify(resultado)
        
    except Exception as e:
        current_app.logger.error(f"Erro ao verificar orçamento: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500


@compra_routes.route('/necessidades-estoque')
@login_required
def necessidades_estoque():
    """Página para visualizar necessidades de estoque e gerar compras."""
    if not verificar_acesso_cliente():
        flash('Acesso negado', 'error')
        return redirect(url_for('evento_routes.home'))
    
    try:
        # Buscar polos do cliente
        polos = Polo.query.filter_by(cliente_id=current_user.id, ativo=True).all()
        
        return render_template('compra/necessidades_estoque.html', polos=polos)
    
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar página de necessidades: {e}")
        flash('Erro ao carregar dados', 'error')
        return redirect(url_for('compra_routes.gerenciar_compras'))


@compra_routes.route('/api/documentos/validar', methods=['POST'])
@login_required
def validar_documento():
    """API para validar documento fiscal"""
    try:
        from services.documento_fiscal_service import DocumentoFiscalService
        
        if 'arquivo' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'})
        
        arquivo = request.files['arquivo']
        tipo_documento = request.form.get('tipo_documento')
        
        if arquivo.filename == '':
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'})
        
        if not tipo_documento:
            return jsonify({'success': False, 'error': 'Tipo de documento não informado'})
        
        # Processar validação
        service = DocumentoFiscalService()
        resultado = service.validar_arquivo(arquivo, tipo_documento)
        
        if resultado['valido']:
            # Extrair dados do documento
            dados_extraidos = service.extrair_dados_documento(arquivo, tipo_documento)
            
            return jsonify({
                'success': True,
                'validacao': resultado,
                'dados_extraidos': dados_extraidos
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Documento inválido',
                'validacao': resultado
            })
    
    except Exception as e:
        current_app.logger.error(f"Erro ao validar documento: {str(e)}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'})


@compra_routes.route('/api/compras/<int:compra_id>/documentos', methods=['POST'])
@login_required
def upload_documento_api(compra_id):
    """API para upload de documento fiscal"""
    try:
        from services.documento_fiscal_service import DocumentoFiscalService
        
        # Verificar se a compra existe e o usuário tem acesso
        compra = Compra.query.get_or_404(compra_id)
        
        if not current_user.is_admin and not current_user.is_gestor and compra.usuario_id != current_user.id:
            return jsonify({'success': False, 'error': 'Acesso negado'})
        
        if 'arquivo' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'})
        
        arquivo = request.files['arquivo']
        tipo_documento = request.form.get('tipo_documento')
        observacoes = request.form.get('observacoes', '')
        numero_documento = request.form.get('numero_documento', '')
        valor_documento = request.form.get('valor_documento')
        data_emissao = request.form.get('data_emissao')
        chave_acesso = request.form.get('chave_acesso', '')
        
        if arquivo.filename == '':
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'})
        
        # Processar upload
        service = DocumentoFiscalService()
        resultado = service.processar_upload(
            arquivo=arquivo,
            compra_id=compra_id,
            tipo_documento=tipo_documento,
            observacoes=observacoes,
            numero_documento=numero_documento,
            valor_documento=float(valor_documento) if valor_documento else None,
            data_emissao=datetime.strptime(data_emissao, '%Y-%m-%d').date() if data_emissao else None,
            chave_acesso=chave_acesso,
            usuario_id=current_user.id
        )
        
        if resultado['success']:
            return jsonify({
                'success': True,
                'message': 'Documento enviado com sucesso',
                'documento_id': resultado['documento_id'],
                'warnings': resultado.get('warnings', [])
            })
        else:
            return jsonify({
                'success': False,
                'error': resultado['error']
            })
    
    except Exception as e:
        current_app.logger.error(f"Erro ao fazer upload de documento: {str(e)}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'})


@compra_routes.route('/notificacoes/configurar', methods=['GET', 'POST'])
@login_required
def configurar_notificacoes():
    """Configurar sistema de notificações de compras."""
    if not verificar_acesso_admin():
        flash('Acesso negado. Apenas administradores podem configurar notificações.', 'error')
        return redirect(url_for('compra_routes.gerenciar_compras'))
    
    if request.method == 'POST':
        try:
            # Executar verificação manual de alertas
            CompraNotificationService.verificar_alertas_criticos()
            flash('Verificação de alertas executada com sucesso!', 'success')
            
        except Exception as e:
            current_app.logger.error(f"Erro ao executar verificação de alertas: {str(e)}")
            flash('Erro ao executar verificação de alertas.', 'error')
    
    return render_template('compra/configurar_notificacoes.html')


@compra_routes.route('/notificacoes/testar', methods=['POST'])
@login_required
def testar_notificacoes():
    """Testar envio de notificações."""
    if not verificar_acesso_admin():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        tipo_teste = request.json.get('tipo_teste')
        
        if tipo_teste == 'orcamento_excedido':
            # Simular teste de orçamento excedido
            from models.orcamento import Orcamento
            orcamento = Orcamento.query.first()
            if orcamento:
                CompraNotificationService.enviar_alerta_orcamento_excedido(
                    orcamento, orcamento.valor_total * 1.1, 110
                )
                return jsonify({'success': True, 'message': 'Teste de orçamento excedido enviado'})
            else:
                return jsonify({'success': False, 'message': 'Nenhum orçamento encontrado para teste'})
        
        elif tipo_teste == 'orcamento_proximo_limite':
            from models.orcamento import Orcamento
            orcamento = Orcamento.query.first()
            if orcamento:
                CompraNotificationService.enviar_alerta_orcamento_proximo_limite(
                    orcamento, orcamento.valor_total * 0.95, 95
                )
                return jsonify({'success': True, 'message': 'Teste de orçamento próximo ao limite enviado'})
            else:
                return jsonify({'success': False, 'message': 'Nenhum orçamento encontrado para teste'})
        
        elif tipo_teste == 'compras_pendentes':
            compras_pendentes = Compra.query.filter_by(status='pendente').limit(3).all()
            if compras_pendentes:
                CompraNotificationService.enviar_alerta_compras_pendentes(compras_pendentes)
                return jsonify({'success': True, 'message': 'Teste de compras pendentes enviado'})
            else:
                return jsonify({'success': False, 'message': 'Nenhuma compra pendente encontrada para teste'})
        
        elif tipo_teste == 'prestacoes_atrasadas':
            prestacoes_atrasadas = Compra.query.filter(
                Compra.status == 'aprovada',
                Compra.prestacao_contas == False
            ).limit(3).all()
            if prestacoes_atrasadas:
                CompraNotificationService.enviar_alerta_prestacoes_atrasadas(prestacoes_atrasadas)
                return jsonify({'success': True, 'message': 'Teste de prestações atrasadas enviado'})
            else:
                return jsonify({'success': False, 'message': 'Nenhuma prestação atrasada encontrada para teste'})
        
        else:
            return jsonify({'success': False, 'message': 'Tipo de teste inválido'})
    
    except Exception as e:
        current_app.logger.error(f"Erro ao testar notificações: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})


@compra_routes.route('/api/notificacoes/status', methods=['GET'])
@login_required
def status_notificacoes():
    """Verificar status das notificações e alertas."""
    if not verificar_acesso_admin():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        from models.orcamento import Orcamento
        
        # Verificar orçamentos próximos ao limite
        orcamentos_criticos = []
        orcamentos = Orcamento.query.filter_by(ativo=True).all()
        
        for orcamento in orcamentos:
            total_gasto = db.session.query(
                db.func.sum(Compra.valor_total)
            ).filter(
                Compra.polo_id == orcamento.polo_id,
                Compra.data_compra >= orcamento.data_inicio,
                Compra.data_compra <= orcamento.data_fim,
                Compra.status.in_(['aprovada', 'finalizada'])
            ).scalar() or 0
            
            percentual_usado = (total_gasto / orcamento.valor_total) * 100 if orcamento.valor_total > 0 else 0
            
            if percentual_usado >= 90:
                orcamentos_criticos.append({
                    'polo_nome': orcamento.polo.nome,
                    'percentual_usado': round(percentual_usado, 2),
                    'valor_total': float(orcamento.valor_total),
                    'total_gasto': float(total_gasto),
                    'status': 'excedido' if percentual_usado >= 100 else 'proximo_limite'
                })
        
        # Verificar compras pendentes há mais de 7 dias
        data_limite = datetime.now() - timedelta(days=7)
        compras_pendentes = Compra.query.filter(
            Compra.status == 'pendente',
            Compra.data_compra <= data_limite
        ).count()
        
        # Verificar prestações atrasadas
        data_limite_prestacao = datetime.now() - timedelta(days=30)
        prestacoes_atrasadas = Compra.query.filter(
            Compra.status == 'aprovada',
            Compra.data_compra <= data_limite_prestacao,
            Compra.prestacao_contas == False
        ).count()
        
        return jsonify({
            'success': True,
            'status': {
                'orcamentos_criticos': orcamentos_criticos,
                'compras_pendentes': compras_pendentes,
                'prestacoes_atrasadas': prestacoes_atrasadas,
                'total_alertas': len(orcamentos_criticos) + (1 if compras_pendentes > 0 else 0) + (1 if prestacoes_atrasadas > 0 else 0)
            }
        })
    
    except Exception as e:
        current_app.logger.error(f"Erro ao verificar status das notificações: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})


# Rotas do Dashboard de Análise
@compra_routes.route('/dashboard-analise')
@login_required
def dashboard_analise():
    """Página do dashboard de análise de gastos"""
    if not current_user.is_admin:
        flash('Acesso negado. Apenas administradores podem acessar o dashboard.', 'error')
        return redirect(url_for('compra_routes.gerenciar_compras'))
    
    return render_template('compra/dashboard_analise.html')

@compra_routes.route('/api/polos')
@login_required
def api_polos():
    """API para obter lista de polos"""
    try:
        polos = Polo.query.filter_by(ativo=True).all()
        return jsonify({
            'success': True,
            'polos': [{'id': p.id, 'nome': p.nome} for p in polos]
        })
    except Exception as e:
        logger.error(f"Erro ao carregar polos: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@compra_routes.route('/api/categorias')
@login_required
def api_categorias():
    """API para obter lista de categorias"""
    try:
        # Obter categorias únicas das compras
        categorias = db.session.query(Compra.categoria).distinct().filter(
            Compra.categoria.isnot(None),
            Compra.categoria != ''
        ).all()
        
        categorias_list = [{'id': cat[0], 'nome': cat[0]} for cat in categorias if cat[0]]
        
        return jsonify({
            'success': True,
            'categorias': categorias_list
        })
    except Exception as e:
        logger.error(f"Erro ao carregar categorias: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@compra_routes.route('/api/dashboard/metricas')
@login_required
def api_dashboard_metricas():
    """API para métricas principais do dashboard"""
    try:
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        polo_id = request.args.get('polo_id')
        categoria_id = request.args.get('categoria_id')
        
        # Query base
        query = Compra.query
        
        # Aplicar filtros
        if data_inicio:
            query = query.filter(Compra.data_compra >= datetime.strptime(data_inicio, '%Y-%m-%d'))
        if data_fim:
            query = query.filter(Compra.data_compra <= datetime.strptime(data_fim, '%Y-%m-%d'))
        if polo_id:
            query = query.filter(Compra.polo_id == polo_id)
        if categoria_id:
            query = query.filter(Compra.categoria == categoria_id)
        
        compras = query.all()
        
        # Calcular métricas
        total_gastos = sum(c.valor_total or 0 for c in compras)
        total_compras = len(compras)
        ticket_medio = total_gastos / total_compras if total_compras > 0 else 0
        economia_gerada = sum(c.economia_gerada or 0 for c in compras)
        
        # Calcular variações (período anterior)
        if data_inicio and data_fim:
            data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
            data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
            periodo_dias = (data_fim_dt - data_inicio_dt).days
            
            data_inicio_anterior = data_inicio_dt - timedelta(days=periodo_dias)
            data_fim_anterior = data_inicio_dt
            
            query_anterior = Compra.query.filter(
                Compra.data_compra >= data_inicio_anterior,
                Compra.data_compra < data_fim_anterior
            )
            
            if polo_id:
                query_anterior = query_anterior.filter(Compra.polo_id == polo_id)
            if categoria_id:
                query_anterior = query_anterior.filter(Compra.categoria == categoria_id)
            
            compras_anterior = query_anterior.all()
            
            total_gastos_anterior = sum(c.valor_total or 0 for c in compras_anterior)
            total_compras_anterior = len(compras_anterior)
            ticket_medio_anterior = total_gastos_anterior / total_compras_anterior if total_compras_anterior > 0 else 0
            economia_anterior = sum(c.economia_gerada or 0 for c in compras_anterior)
            
            # Calcular variações percentuais
            variacao_gastos = ((total_gastos - total_gastos_anterior) / total_gastos_anterior * 100) if total_gastos_anterior > 0 else 0
            variacao_compras = ((total_compras - total_compras_anterior) / total_compras_anterior * 100) if total_compras_anterior > 0 else 0
            variacao_ticket = ((ticket_medio - ticket_medio_anterior) / ticket_medio_anterior * 100) if ticket_medio_anterior > 0 else 0
            variacao_economia = ((economia_gerada - economia_anterior) / economia_anterior * 100) if economia_anterior > 0 else 0
        else:
            variacao_gastos = variacao_compras = variacao_ticket = variacao_economia = 0
        
        return jsonify({
            'success': True,
            'metricas': {
                'total_gastos': total_gastos,
                'total_compras': total_compras,
                'ticket_medio': ticket_medio,
                'economia_gerada': economia_gerada,
                'variacao_gastos': variacao_gastos,
                'variacao_compras': variacao_compras,
                'variacao_ticket': variacao_ticket,
                'variacao_economia': variacao_economia
            }
        })
    except Exception as e:
        logger.error(f"Erro ao carregar métricas do dashboard: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@compra_routes.route('/api/dashboard/evolucao')
@login_required
def api_dashboard_evolucao():
    """API para gráfico de evolução temporal"""
    try:
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        polo_id = request.args.get('polo_id')
        categoria_id = request.args.get('categoria_id')
        
        # Query base
        query = db.session.query(
            func.date(Compra.data_compra).label('data'),
            func.sum(Compra.valor_total).label('total')
        )
        
        # Aplicar filtros
        if data_inicio:
            query = query.filter(Compra.data_compra >= datetime.strptime(data_inicio, '%Y-%m-%d'))
        if data_fim:
            query = query.filter(Compra.data_compra <= datetime.strptime(data_fim, '%Y-%m-%d'))
        if polo_id:
            query = query.filter(Compra.polo_id == polo_id)
        if categoria_id:
            query = query.filter(Compra.categoria == categoria_id)
        
        resultados = query.group_by(func.date(Compra.data_compra)).order_by('data').all()
        
        labels = [r.data.strftime('%d/%m') for r in resultados]
        valores = [float(r.total or 0) for r in resultados]
        
        return jsonify({
            'success': True,
            'labels': labels,
            'valores': valores
        })
    except Exception as e:
        logger.error(f"Erro ao carregar evolução temporal: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@compra_routes.route('/api/dashboard/status')
@login_required
def api_dashboard_status():
    """API para gráfico de distribuição por status"""
    try:
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        polo_id = request.args.get('polo_id')
        categoria_id = request.args.get('categoria_id')
        
        # Query base
        query = db.session.query(
            Compra.status,
            func.count(Compra.id).label('quantidade')
        )
        
        # Aplicar filtros
        if data_inicio:
            query = query.filter(Compra.data_compra >= datetime.strptime(data_inicio, '%Y-%m-%d'))
        if data_fim:
            query = query.filter(Compra.data_compra <= datetime.strptime(data_fim, '%Y-%m-%d'))
        if polo_id:
            query = query.filter(Compra.polo_id == polo_id)
        if categoria_id:
            query = query.filter(Compra.categoria == categoria_id)
        
        resultados = query.group_by(Compra.status).all()
        
        labels = [r.status or 'Sem Status' for r in resultados]
        valores = [r.quantidade for r in resultados]
        
        return jsonify({
            'success': True,
            'labels': labels,
            'valores': valores
        })
    except Exception as e:
        logger.error(f"Erro ao carregar distribuição por status: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@compra_routes.route('/api/dashboard/categorias')
@login_required
def api_dashboard_categorias():
    """API para gráfico de gastos por categoria"""
    try:
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        polo_id = request.args.get('polo_id')
        categoria_id = request.args.get('categoria_id')
        
        # Query base
        query = db.session.query(
            Compra.categoria,
            func.sum(Compra.valor_total).label('total')
        )
        
        # Aplicar filtros
        if data_inicio:
            query = query.filter(Compra.data_compra >= datetime.strptime(data_inicio, '%Y-%m-%d'))
        if data_fim:
            query = query.filter(Compra.data_compra <= datetime.strptime(data_fim, '%Y-%m-%d'))
        if polo_id:
            query = query.filter(Compra.polo_id == polo_id)
        if categoria_id:
            query = query.filter(Compra.categoria == categoria_id)
        
        resultados = query.filter(Compra.categoria.isnot(None)).group_by(Compra.categoria).order_by(func.sum(Compra.valor_total).desc()).limit(10).all()
        
        labels = [r.categoria or 'Sem Categoria' for r in resultados]
        valores = [float(r.total or 0) for r in resultados]
        
        return jsonify({
            'success': True,
            'labels': labels,
            'valores': valores
        })
    except Exception as e:
        logger.error(f"Erro ao carregar gastos por categoria: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@compra_routes.route('/api/dashboard/polos')
@login_required
def api_dashboard_polos():
    """API para gráfico de gastos por polo"""
    try:
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        polo_id = request.args.get('polo_id')
        categoria_id = request.args.get('categoria_id')
        
        # Query base
        query = db.session.query(
            Polo.nome,
            func.sum(Compra.valor_total).label('total')
        ).join(Compra, Compra.polo_id == Polo.id)
        
        # Aplicar filtros
        if data_inicio:
            query = query.filter(Compra.data_compra >= datetime.strptime(data_inicio, '%Y-%m-%d'))
        if data_fim:
            query = query.filter(Compra.data_compra <= datetime.strptime(data_fim, '%Y-%m-%d'))
        if polo_id:
            query = query.filter(Compra.polo_id == polo_id)
        if categoria_id:
            query = query.filter(Compra.categoria == categoria_id)
        
        resultados = query.group_by(Polo.nome).order_by(func.sum(Compra.valor_total).desc()).all()
        
        labels = [r.nome for r in resultados]
        valores = [float(r.total or 0) for r in resultados]
        
        return jsonify({
            'success': True,
            'labels': labels,
            'valores': valores
        })
    except Exception as e:
        logger.error(f"Erro ao carregar gastos por polo: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@compra_routes.route('/api/dashboard/fornecedores')
@login_required
def api_dashboard_fornecedores():
    """API para top fornecedores"""
    try:
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        polo_id = request.args.get('polo_id')
        categoria_id = request.args.get('categoria_id')
        
        # Query base
        query = db.session.query(
            Compra.fornecedor,
            func.sum(Compra.valor_total).label('valor_total'),
            func.count(Compra.id).label('total_compras')
        )
        
        # Aplicar filtros
        if data_inicio:
            query = query.filter(Compra.data_compra >= datetime.strptime(data_inicio, '%Y-%m-%d'))
        if data_fim:
            query = query.filter(Compra.data_compra <= datetime.strptime(data_fim, '%Y-%m-%d'))
        if polo_id:
            query = query.filter(Compra.polo_id == polo_id)
        if categoria_id:
            query = query.filter(Compra.categoria == categoria_id)
        
        resultados = query.filter(Compra.fornecedor.isnot(None)).group_by(Compra.fornecedor).order_by(func.sum(Compra.valor_total).desc()).limit(10).all()
        
        fornecedores = []
        for r in resultados:
            fornecedores.append({
                'nome': r.fornecedor or 'Fornecedor não informado',
                'valor_total': float(r.valor_total or 0),
                'total_compras': r.total_compras
            })
        
        return jsonify({
            'success': True,
            'fornecedores': fornecedores
        })
    except Exception as e:
        logger.error(f"Erro ao carregar top fornecedores: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@compra_routes.route('/api/dashboard/analise-polos')
@login_required
def api_dashboard_analise_polos():
    """API para análise orçamentária por polo"""
    try:
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        categoria_id = request.args.get('categoria_id')
        
        # Query para gastos por polo
        query_gastos = db.session.query(
            Polo.id,
            Polo.nome,
            func.sum(Compra.valor_total).label('valor_gasto')
        ).join(Compra, Compra.polo_id == Polo.id)
        
        # Aplicar filtros
        if data_inicio:
            query_gastos = query_gastos.filter(Compra.data_compra >= datetime.strptime(data_inicio, '%Y-%m-%d'))
        if data_fim:
            query_gastos = query_gastos.filter(Compra.data_compra <= datetime.strptime(data_fim, '%Y-%m-%d'))
        if categoria_id:
            query_gastos = query_gastos.filter(Compra.categoria == categoria_id)
        
        gastos_por_polo = query_gastos.group_by(Polo.id, Polo.nome).all()
        
        # Query para orçamentos por polo
        orcamentos_por_polo = db.session.query(
            Polo.id,
            func.sum(Orcamento.valor_total).label('orcamento_total')
        ).join(Orcamento, Orcamento.polo_id == Polo.id).group_by(Polo.id).all()
        
        # Combinar dados
        orcamentos_dict = {o.id: float(o.orcamento_total or 0) for o in orcamentos_por_polo}
        
        polos_analise = []
        for gasto in gastos_por_polo:
            orcamento_total = orcamentos_dict.get(gasto.id, 0)
            polos_analise.append({
                'nome': gasto.nome,
                'valor_gasto': float(gasto.valor_gasto or 0),
                'orcamento_total': orcamento_total
            })
        
        return jsonify({
            'success': True,
            'polos': polos_analise
        })
    except Exception as e:
        logger.error(f"Erro ao carregar análise de polos: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@compra_routes.route('/api/dashboard/insights')
@login_required
def api_dashboard_insights():
    """API para insights e tendências"""
    try:
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        polo_id = request.args.get('polo_id')
        categoria_id = request.args.get('categoria_id')
        
        insights = []
        
        # Insight 1: Orçamentos excedidos
        query_orcamentos = db.session.query(
            Polo.nome,
            func.sum(Compra.valor_total).label('gasto'),
            func.sum(Orcamento.valor_total).label('orcamento')
        ).join(Compra, Compra.polo_id == Polo.id).join(Orcamento, Orcamento.polo_id == Polo.id)
        
        if data_inicio:
            query_orcamentos = query_orcamentos.filter(Compra.data_compra >= datetime.strptime(data_inicio, '%Y-%m-%d'))
        if data_fim:
            query_orcamentos = query_orcamentos.filter(Compra.data_compra <= datetime.strptime(data_fim, '%Y-%m-%d'))
        
        orcamentos_excedidos = query_orcamentos.group_by(Polo.nome).having(
            func.sum(Compra.valor_total) > func.sum(Orcamento.valor_total)
        ).all()
        
        if orcamentos_excedidos:
            insights.append({
                'tipo': 'warning',
                'icone': 'fa-exclamation-triangle',
                'titulo': 'Orçamentos Excedidos',
                'descricao': f'{len(orcamentos_excedidos)} polo(s) excederam seus orçamentos no período analisado.'
            })
        
        # Insight 2: Compras pendentes
        compras_pendentes = Compra.query.filter(
            Compra.status.in_(['Pendente', 'Em Análise', 'Aguardando Aprovação'])
        ).count()
        
        if compras_pendentes > 0:
            insights.append({
                'tipo': 'info',
                'icone': 'fa-clock',
                'titulo': 'Compras Pendentes',
                'descricao': f'{compras_pendentes} compra(s) aguardando processamento ou aprovação.'
            })
        
        # Insight 3: Economia gerada
        query_economia = Compra.query
        if data_inicio:
            query_economia = query_economia.filter(Compra.data_compra >= datetime.strptime(data_inicio, '%Y-%m-%d'))
        if data_fim:
            query_economia = query_economia.filter(Compra.data_compra <= datetime.strptime(data_fim, '%Y-%m-%d'))
        
        economia_total = sum(c.economia_gerada or 0 for c in query_economia.all())
        
        if economia_total > 0:
            insights.append({
                'tipo': 'success',
                'icone': 'fa-piggy-bank',
                'titulo': 'Economia Gerada',
                'descricao': f'R$ {economia_total:,.2f} economizados através de negociações e processos otimizados.'
            })
        
        # Insight 4: Fornecedor mais utilizado
        fornecedor_top = db.session.query(
            Compra.fornecedor,
            func.count(Compra.id).label('total')
        ).filter(Compra.fornecedor.isnot(None)).group_by(Compra.fornecedor).order_by(func.count(Compra.id).desc()).first()
        
        if fornecedor_top:
            insights.append({
                'tipo': 'primary',
                'icone': 'fa-handshake',
                'titulo': 'Fornecedor Principal',
                'descricao': f'{fornecedor_top.fornecedor} é o fornecedor mais utilizado com {fornecedor_top.total} compras.'
            })
        
        return jsonify({
            'success': True,
            'insights': insights
        })
    except Exception as e:
        logger.error(f"Erro ao carregar insights: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500


@compra_routes.route('/exportar/excel')
@login_required
def exportar_compras_excel():
    """Exporta relatório de compras em Excel"""
    try:
        # Verificar permissões
        if not (verificar_acesso_admin() or verificar_acesso_monitor()):
            flash('Acesso negado.', 'error')
            return redirect(url_for('compra_routes.gerenciar_compras'))
        
        # Obter filtros da query string
        status = request.args.get('status')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        fornecedor = request.args.get('fornecedor')
        
        # Construir query
        query = Compra.query
        
        if status:
            query = query.filter(Compra.status == status)
        
        if data_inicio:
            try:
                data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d')
                query = query.filter(Compra.data_criacao >= data_inicio_obj)
            except ValueError:
                pass
        
        if data_fim:
            try:
                data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d')
                query = query.filter(Compra.data_criacao <= data_fim_obj)
            except ValueError:
                pass
        
        if fornecedor:
            query = query.filter(Compra.fornecedor.ilike(f'%{fornecedor}%'))
        
        # Executar query
        compras = query.order_by(desc(Compra.data_criacao)).all()
        
        # Exportar para Excel
        filepath = ExportService.export_compras_excel(compras)
        
        return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath))
        
    except Exception as e:
        current_app.logger.error(f"Erro ao exportar compras para Excel: {str(e)}")
        flash('Erro ao exportar relatório.', 'error')
        return redirect(url_for('compra_routes.gerenciar_compras'))


@compra_routes.route('/exportar/pdf')
@login_required
def exportar_compras_pdf():
    """Exporta relatório de compras em PDF"""
    try:
        # Verificar permissões
        if not (verificar_acesso_admin() or verificar_acesso_monitor()):
            flash('Acesso negado.', 'error')
            return redirect(url_for('compra_routes.gerenciar_compras'))
        
        # Obter filtros da query string
        status = request.args.get('status')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        fornecedor = request.args.get('fornecedor')
        
        # Construir query
        query = Compra.query
        
        if status:
            query = query.filter(Compra.status == status)
        
        if data_inicio:
            try:
                data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d')
                query = query.filter(Compra.data_criacao >= data_inicio_obj)
            except ValueError:
                pass
        
        if data_fim:
            try:
                data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d')
                query = query.filter(Compra.data_criacao <= data_fim_obj)
            except ValueError:
                pass
        
        if fornecedor:
            query = query.filter(Compra.fornecedor.ilike(f'%{fornecedor}%'))
        
        # Executar query
        compras = query.order_by(desc(Compra.data_criacao)).all()
        
        # Exportar para PDF
        filepath = ExportService.export_compras_pdf(compras)
        
        return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath))
        
    except Exception as e:
        current_app.logger.error(f"Erro ao exportar compras para PDF: {str(e)}")
        flash('Erro ao exportar relatório.', 'error')
        return redirect(url_for('compra_routes.gerenciar_compras'))