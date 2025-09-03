"""Routes for material management.

Unauthorized AJAX requests receive a JSON 401 from the global handler.
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from datetime import datetime
import json

from extensions import db, csrf
from models.user import Cliente, Monitor
from models.material import Polo, Material, MovimentacaoMaterial, MonitorPolo
from utils import endpoints

material_routes = Blueprint('material_routes', __name__)


def verificar_acesso_cliente():
    """Verifica se o usuário atual é um cliente."""
    return hasattr(current_user, 'tipo') and current_user.tipo == 'cliente'


def verificar_acesso_monitor():
    """Verifica se o usuário atual é um monitor."""
    return hasattr(current_user, 'tipo') and current_user.tipo == 'monitor'


def verificar_acesso_admin():
    """Verifica se o usuário atual é um admin."""
    return hasattr(current_user, 'tipo') and current_user.tipo == 'admin'


# ==================== ROTAS DO CLIENTE ====================

@material_routes.route('/gerenciar-materiais')
@login_required
def gerenciar_materiais():
    """Página principal de gerenciamento de materiais para clientes."""
    if not verificar_acesso_cliente():
        flash('Acesso negado', 'error')
        return redirect(url_for('main.index'))
    
    try:
        # Buscar polos do cliente
        polos = Polo.query.filter_by(cliente_id=current_user.id, ativo=True).all()
        
        # Estatísticas gerais
        total_materiais = Material.query.filter_by(cliente_id=current_user.id, ativo=True).count()
        materiais_baixo_estoque = Material.query.filter_by(cliente_id=current_user.id, ativo=True).filter(
            Material.quantidade_atual <= Material.quantidade_minima
        ).count()
        materiais_esgotados = Material.query.filter_by(cliente_id=current_user.id, ativo=True).filter(
            Material.quantidade_atual <= 0
        ).count()
        
        # Estatísticas por polo
        estatisticas_polos = []
        for polo in polos:
            materiais_polo = Material.query.filter_by(polo_id=polo.id, ativo=True).all()
            total_polo = len(materiais_polo)
            baixo_estoque_polo = sum(1 for m in materiais_polo if m.quantidade_atual <= m.quantidade_minima)
            esgotados_polo = sum(1 for m in materiais_polo if m.quantidade_atual <= 0)
            
            estatisticas_polos.append({
                'polo': polo,
                'total_materiais': total_polo,
                'baixo_estoque': baixo_estoque_polo,
                'esgotados': esgotados_polo
            })
        
        return render_template('material/gerenciar_materiais.html',
                             polos=polos,
                             total_materiais=total_materiais,
                             materiais_baixo_estoque=materiais_baixo_estoque,
                             materiais_esgotados=materiais_esgotados,
                             estatisticas_polos=estatisticas_polos)
    
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar página de materiais: {str(e)}")
        flash('Erro ao carregar dados', 'error')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))


@material_routes.route('/api/polos', methods=['GET'])
@csrf.exempt
@login_required
def listar_polos():
    """API para listar polos acessíveis ao usuário atual.

    - Cliente: lista todos os polos do cliente.
    - Monitor: lista apenas polos atribuídos ao monitor.
    - Admin: lista todos os polos ativos.
    """
    
    try:
        if verificar_acesso_cliente():
            polos = Polo.query.filter_by(cliente_id=current_user.id, ativo=True).all()
        elif verificar_acesso_monitor():
            polos = (
                db.session.query(Polo)
                .join(MonitorPolo, MonitorPolo.polo_id == Polo.id)
                .filter(
                    MonitorPolo.monitor_id == current_user.id,
                    MonitorPolo.ativo == True,
                    Polo.ativo == True
                )
                .all()
            )
            if not polos:
                return jsonify({
                    'success': True,
                    'polos': [],
                    'message': 'Nenhum polo associado ao monitor'
                })
        elif verificar_acesso_admin():
            polos = Polo.query.filter_by(ativo=True).all()
        else:
            return jsonify({'success': False, 'message': 'Acesso negado'}), 403
        return jsonify({
            'success': True,
            'polos': [polo.to_dict() for polo in polos]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== ROTAS DE ESTATÍSTICAS E RELATÓRIOS ====================

@material_routes.route('/api/estatisticas/polos', methods=['GET'])
@csrf.exempt
@login_required
def estatisticas_polos():
    """API para obter estatísticas de materiais por polo."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        # Buscar todos os polos do cliente
        polos = Polo.query.filter_by(cliente_id=current_user.id, ativo=True).all()
        
        estatisticas = []
        
        for polo in polos:
            materiais = Material.query.filter_by(polo_id=polo.id, ativo=True).all()
            
            total_materiais = len(materiais)
            em_estoque = len([m for m in materiais if m.quantidade_atual > m.quantidade_minima])
            estoque_baixo = len([m for m in materiais if 0 < m.quantidade_atual <= m.quantidade_minima])
            sem_estoque = len([m for m in materiais if m.quantidade_atual == 0])
            
            # Calcular valor total (se houver preço unitário)
            valor_total = sum([m.quantidade_atual * (getattr(m, 'preco_unitario', 0) or 0) for m in materiais])
            
            estatisticas.append({
                'polo': polo.to_dict(),
                'total_materiais': total_materiais,
                'em_estoque': em_estoque,
                'estoque_baixo': estoque_baixo,
                'sem_estoque': sem_estoque,
                'valor_total_estoque': valor_total,
                'percentual_ok': round((em_estoque / total_materiais * 100) if total_materiais > 0 else 0, 1),
                'materiais_criticos': [m.to_dict() for m in materiais if m.quantidade_atual <= m.quantidade_minima]
            })
        
        # Estatísticas gerais
        total_geral = sum([e['total_materiais'] for e in estatisticas])
        em_estoque_geral = sum([e['em_estoque'] for e in estatisticas])
        estoque_baixo_geral = sum([e['estoque_baixo'] for e in estatisticas])
        sem_estoque_geral = sum([e['sem_estoque'] for e in estatisticas])
        valor_total_geral = sum([e['valor_total_estoque'] for e in estatisticas])
        
        return jsonify({
            'success': True,
            'estatisticas_por_polo': estatisticas,
            'estatisticas_gerais': {
                'total_materiais': total_geral,
                'em_estoque': em_estoque_geral,
                'estoque_baixo': estoque_baixo_geral,
                'sem_estoque': sem_estoque_geral,
                'valor_total_estoque': valor_total_geral,
                'total_polos': len(polos),
                'percentual_ok': round((em_estoque_geral / total_geral * 100) if total_geral > 0 else 0, 1)
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@material_routes.route('/relatorios/materiais/excel', methods=['GET'])
@login_required
def gerar_relatorio_excel():
    """Gerar relatório de materiais em Excel."""
    if not verificar_acesso_cliente() and not verificar_acesso_monitor():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        import pandas as pd
        from flask import make_response
        import io
        
        polo_id = request.args.get('polo_id')
        tipo_relatorio = request.args.get('tipo', 'geral')
        
        # Determinar cliente_id baseado no tipo de usuário
        if verificar_acesso_cliente():
            cliente_id = current_user.id
        else:  # Monitor
            # Buscar polos atribuídos ao monitor
            polos_monitor = db.session.query(Polo).join(MonitorPolo).filter(
                MonitorPolo.monitor_id == current_user.id,
                MonitorPolo.ativo == True
            ).all()
            if not polos_monitor:
                return jsonify({'success': False, 'message': 'Nenhum polo atribuído'}), 403
            cliente_id = polos_monitor[0].cliente_id
        
        # Construir query
        query = Material.query.filter_by(cliente_id=cliente_id, ativo=True)
        
        if polo_id:
            query = query.filter_by(polo_id=polo_id)
        
        if tipo_relatorio == 'baixo_estoque':
            query = query.filter(Material.quantidade_atual <= Material.quantidade_minima)
        elif tipo_relatorio == 'sem_estoque':
            query = query.filter(Material.quantidade_atual == 0)
        elif tipo_relatorio == 'compras':
            query = query.filter(Material.quantidade_atual < Material.quantidade_minima)
        
        materiais = query.all()
        
        # Preparar dados para Excel
        dados = []
        for material in materiais:
            polo = Polo.query.get(material.polo_id) if material.polo_id else None
            
            # Calcular status
            if material.quantidade_atual == 0:
                status = 'Sem Estoque'
            elif material.quantidade_atual <= material.quantidade_minima:
                status = 'Estoque Baixo'
            else:
                status = 'Em Estoque'
            
            # Calcular quantidade necessária para compra
            if material.quantidade_atual < material.quantidade_minima:
                qtd_necessaria = material.quantidade_minima - material.quantidade_atual + (material.quantidade_minima * 0.5)
            else:
                qtd_necessaria = 0
            
            dados.append({
                'Material': material.nome,
                'Descrição': material.descricao or '',
                'Polo': polo.nome if polo else 'N/A',
                'Quantidade Atual': material.quantidade_atual,
                'Quantidade Mínima': material.quantidade_minima,
                'Unidade': material.unidade,
                'Status': status,
                'Quantidade para Compra': qtd_necessaria,
                'Preço Unitário': getattr(material, 'preco_unitario', 0) or 0,
                'Valor Total Estoque': material.quantidade_atual * (getattr(material, 'preco_unitario', 0) or 0),
                'Última Atualização': (
                    getattr(material, 'data_atualizacao', None).strftime('%d/%m/%Y %H:%M')
                    if getattr(material, 'data_atualizacao', None)
                    else ''
                )
            })
        
        # Criar DataFrame
        df = pd.DataFrame(dados)
        
        # Criar arquivo Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Materiais', index=False)
            
            # Adicionar planilha de resumo
            if len(dados) > 0:
                resumo_dados = {
                    'Métrica': [
                        'Total de Materiais',
                        'Em Estoque',
                        'Estoque Baixo',
                        'Sem Estoque',
                        'Valor Total do Estoque'
                    ],
                    'Valor': [
                        len(dados),
                        len([d for d in dados if d['Status'] == 'Em Estoque']),
                        len([d for d in dados if d['Status'] == 'Estoque Baixo']),
                        len([d for d in dados if d['Status'] == 'Sem Estoque']),
                        sum([d['Valor Total Estoque'] for d in dados])
                    ]
                }
                df_resumo = pd.DataFrame(resumo_dados)
                df_resumo.to_excel(writer, sheet_name='Resumo', index=False)
        
        output.seek(0)
        
        # Preparar resposta
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=relatorio_materiais_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return response
    
    except ImportError:
        return jsonify({'success': False, 'message': 'Biblioteca pandas não instalada'}), 500
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar relatório Excel: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@material_routes.route('/api/movimentacoes', methods=['POST'])
@csrf.exempt
@login_required
def registrar_movimentacao_api():
    """API para registrar movimentação de material (para monitores)."""
    if not verificar_acesso_monitor():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        data = request.get_json()
        material_id = data['material_id']
        tipo = data['tipo']  # entrada, saida, ajuste
        quantidade = int(data['quantidade'])
        observacao = data.get('observacoes') or data.get('observacao') or ''
        
        # Verificar se o material existe e se o monitor tem acesso
        material = Material.query.get(material_id)
        if not material:
            return jsonify({'success': False, 'message': 'Material não encontrado'}), 404
        
        # Verificar se o monitor tem acesso ao polo do material
        acesso_polo = MonitorPolo.query.filter_by(
            monitor_id=current_user.id,
            polo_id=material.polo_id,
            ativo=True
        ).first()
        
        if not acesso_polo:
            return jsonify({'success': False, 'message': 'Acesso negado ao polo deste material'}), 403
        
        # Calcular nova quantidade
        if tipo == 'entrada':
            nova_quantidade = material.quantidade_atual + quantidade
        elif tipo == 'saida':
            nova_quantidade = material.quantidade_atual - quantidade
            if nova_quantidade < 0:
                return jsonify({'success': False, 'message': 'Quantidade insuficiente em estoque'}), 400
        elif tipo == 'ajuste':
            nova_quantidade = quantidade
        else:
            return jsonify({'success': False, 'message': 'Tipo de movimentação inválido'}), 400
        
        # Registrar movimentação
        movimentacao = MovimentacaoMaterial(
            material_id=material_id,
            usuario_id=None,
            monitor_id=current_user.id,
            tipo=tipo,
            quantidade=quantidade,
            observacao=observacao
        )
        
        # Atualizar quantidade do material
        material.quantidade_atual = nova_quantidade
        material.updated_at = datetime.utcnow()
        
        db.session.add(movimentacao)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Movimentação registrada com sucesso',
            'material': material.to_dict(),
            'movimentacao': movimentacao.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@material_routes.route('/api/polos', methods=['POST'])
@csrf.exempt
@login_required
def criar_polo():
    """API para criar novo polo."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        data = request.get_json()
        current_app.logger.info(f"Dados recebidos para criar polo: {data}")
        
        # Validar dados obrigatórios
        if not data or not data.get('nome'):
            return jsonify({'success': False, 'message': 'Nome do polo é obrigatório'}), 400
        
        polo = Polo(
            nome=data['nome'],
            descricao=data.get('descricao'),
            endereco=data.get('endereco'),
            responsavel=data.get('responsavel'),
            telefone=data.get('telefone'),
            email=data.get('email'),
            cliente_id=current_user.id
        )
        
        current_app.logger.info(f"Criando polo: {polo.nome} para cliente {current_user.id}")
        
        db.session.add(polo)
        db.session.commit()
        
        current_app.logger.info(f"Polo criado com sucesso: ID {polo.id}")
        
        return jsonify({
            'success': True,
            'message': 'Polo criado com sucesso',
            'polo': polo.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao criar polo: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'}), 500


@material_routes.route('/api/polos/<int:polo_id>', methods=['PUT'])
@csrf.exempt
@login_required
def atualizar_polo(polo_id):
    """API para atualizar polo."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        polo = Polo.query.filter_by(id=polo_id, cliente_id=current_user.id).first()
        if not polo:
            return jsonify({'success': False, 'message': 'Polo não encontrado'}), 404
        
        data = request.get_json()
        
        polo.nome = data.get('nome', polo.nome)
        polo.descricao = data.get('descricao', polo.descricao)
        polo.endereco = data.get('endereco', polo.endereco)
        polo.responsavel = data.get('responsavel', polo.responsavel)
        polo.telefone = data.get('telefone', polo.telefone)
        polo.email = data.get('email', polo.email)
        polo.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Polo atualizado com sucesso',
            'polo': polo.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@material_routes.route('/api/polos/<int:polo_id>', methods=['DELETE'])
@csrf.exempt
@login_required
def deletar_polo(polo_id):
    """API para deletar polo (desativar)."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        polo = Polo.query.filter_by(id=polo_id, cliente_id=current_user.id).first()
        if not polo:
            return jsonify({'success': False, 'message': 'Polo não encontrado'}), 404
        
        # Verificar se há materiais ativos no polo
        materiais_ativos = Material.query.filter_by(polo_id=polo_id, ativo=True).count()
        if materiais_ativos > 0:
            return jsonify({
                'success': False, 
                'message': f'Não é possível deletar o polo. Há {materiais_ativos} materiais ativos associados.'
            }), 400
        
        polo.ativo = False
        polo.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Polo deletado com sucesso'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@material_routes.route('/api/materiais', methods=['GET'])
@csrf.exempt
@login_required
def listar_materiais():
    """API para listar materiais."""
    if not (verificar_acesso_cliente() or verificar_acesso_monitor()):
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        polo_id = request.args.get('polo_id')
        
        if verificar_acesso_cliente():
            query = Material.query.filter_by(cliente_id=current_user.id, ativo=True)
        else:  # Monitor
            # Buscar polos atribuídos ao monitor
            polos_monitor = db.session.query(MonitorPolo.polo_id).filter_by(
                monitor_id=current_user.id, ativo=True
            ).subquery()
            query = Material.query.filter(
                Material.polo_id.in_(polos_monitor),
                Material.ativo == True
            )
        
        if polo_id:
            query = query.filter_by(polo_id=polo_id)
        
        materiais = query.all()
        
        return jsonify({
            'success': True,
            'materiais': [material.to_dict() for material in materiais]
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@material_routes.route('/api/materiais', methods=['POST'])
@csrf.exempt
@login_required
def criar_material():
    """API para criar novo material."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        data = request.get_json()
        
        # Verificar se o polo pertence ao cliente
        polo = Polo.query.filter_by(id=data['polo_id'], cliente_id=current_user.id).first()
        if not polo:
            return jsonify({'success': False, 'message': 'Polo não encontrado'}), 404

        material = Material(
            nome=data['nome'],
            descricao=data.get('descricao'),
            unidade=data.get('unidade', 'unidade'),
            categoria=data.get('categoria'),
            preco_unitario=data.get('preco_unitario'),
            quantidade_inicial=data.get('quantidade_inicial', 0),
            quantidade_atual=data.get('quantidade_inicial', 0),
            quantidade_minima=data.get('quantidade_minima', 0),
            polo_id=data['polo_id'],
            cliente_id=current_user.id
        )
        
        db.session.add(material)
        db.session.flush()  # Para obter o ID
        
        # Registrar movimentação inicial se houver quantidade
        if material.quantidade_inicial > 0:
            movimentacao = MovimentacaoMaterial(
                tipo='entrada',
                quantidade=material.quantidade_inicial,
                observacao='Estoque inicial',
                material_id=material.id,
                usuario_id=None,
                monitor_id=None
            )
            db.session.add(movimentacao)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Material criado com sucesso',
            'material': material.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@material_routes.route('/api/materiais/<int:material_id>', methods=['PUT'])
@csrf.exempt
@login_required
def atualizar_material(material_id):
    """API para atualizar material."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        material = Material.query.filter_by(id=material_id, cliente_id=current_user.id).first()
        if not material:
            return jsonify({'success': False, 'message': 'Material não encontrado'}), 404
        
        data = request.get_json()

        material.nome = data.get('nome', material.nome)
        material.descricao = data.get('descricao', material.descricao)
        material.unidade = data.get('unidade', material.unidade)
        material.categoria = data.get('categoria', material.categoria)
        material.preco_unitario = data.get('preco_unitario', material.preco_unitario)
        material.quantidade_minima = data.get(
            'quantidade_minima', material.quantidade_minima
        )
        material.updated_at = datetime.utcnow()
        material.data_atualizacao = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Material atualizado com sucesso',
            'material': material.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@material_routes.route('/api/materiais/<int:material_id>', methods=['DELETE'])
@csrf.exempt
@login_required
def deletar_material(material_id):
    """API para deletar material (desativar)."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        material = Material.query.filter_by(id=material_id, cliente_id=current_user.id).first()
        if not material:
            return jsonify({'success': False, 'message': 'Material não encontrado'}), 404
        
        material.ativo = False
        material.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Material deletado com sucesso'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== ROTAS DO MONITOR ====================

@material_routes.route('/monitor/materiais')
@login_required
def monitor_materiais():
    """Dashboard de materiais para monitores."""
    if not verificar_acesso_monitor():
        flash('Acesso negado', 'error')
        return redirect(url_for('main.index'))
    
    try:
        # Buscar polos atribuídos ao monitor
        polos_atribuidos = db.session.query(Polo).join(MonitorPolo).filter(
            MonitorPolo.monitor_id == current_user.id,
            MonitorPolo.ativo == True,
            Polo.ativo == True
        ).all()
        
        return render_template('material/monitor_materiais.html',
                             polos=polos_atribuidos)
    
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar dashboard do monitor: {str(e)}")
        flash('Erro ao carregar dados', 'error')
        return redirect(url_for('main.index'))


@material_routes.route('/api/materiais/<int:material_id>/movimentacao', methods=['POST'])
@csrf.exempt
@login_required
def registrar_movimentacao(material_id):
    """API para registrar movimentação de material."""
    if not (verificar_acesso_cliente() or verificar_acesso_monitor()):
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        data = request.get_json()
        
        # Verificar acesso ao material
        if verificar_acesso_cliente():
            material = Material.query.filter_by(id=material_id, cliente_id=current_user.id).first()
        else:  # Monitor
            # Verificar se o monitor tem acesso ao polo do material
            material = db.session.query(Material).join(MonitorPolo).filter(
                Material.id == material_id,
                MonitorPolo.monitor_id == current_user.id,
                MonitorPolo.polo_id == Material.polo_id,
                MonitorPolo.ativo == True
            ).first()
        
        if not material:
            return jsonify({'success': False, 'message': 'Material não encontrado'}), 404
        
        tipo = data['tipo']  # entrada, saida, ajuste
        quantidade = int(data['quantidade'])
        observacao = data.get('observacao', '')
        
        # Validar quantidade para saída
        if tipo == 'saida' and quantidade > material.quantidade_atual:
            return jsonify({
                'success': False, 
                'message': f'Quantidade insuficiente. Disponível: {material.quantidade_atual}'
            }), 400
        
        # Registrar movimentação
        movimentacao = MovimentacaoMaterial(
            tipo=tipo,
            quantidade=quantidade,
            observacao=observacao,
            material_id=material_id,
            usuario_id=current_user.id if verificar_acesso_cliente() else None,
            monitor_id=current_user.id if verificar_acesso_monitor() else None
        )
        
        # Atualizar quantidade do material
        if tipo == 'entrada':
            material.quantidade_atual += quantidade
        elif tipo == 'saida':
            material.quantidade_atual -= quantidade
            material.quantidade_consumida += quantidade
        elif tipo == 'ajuste':
            # Para ajuste, a quantidade é o novo valor total
            diferenca = quantidade - material.quantidade_atual
            material.quantidade_atual = quantidade
            if diferenca < 0:
                material.quantidade_consumida += abs(diferenca)
        
        material.updated_at = datetime.utcnow()
        
        db.session.add(movimentacao)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Movimentação registrada com sucesso',
            'material': material.to_dict(),
            'movimentacao': movimentacao.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@material_routes.route('/api/materiais/<int:material_id>/movimentacoes', methods=['GET'])
@csrf.exempt
@login_required
def listar_movimentacoes(material_id):
    """API para listar movimentações de um material."""
    if not (verificar_acesso_cliente() or verificar_acesso_monitor()):
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        # Verificar acesso ao material
        if verificar_acesso_cliente():
            material = Material.query.filter_by(id=material_id, cliente_id=current_user.id).first()
        else:  # Monitor
            material = db.session.query(Material).join(MonitorPolo).filter(
                Material.id == material_id,
                MonitorPolo.monitor_id == current_user.id,
                MonitorPolo.polo_id == Material.polo_id,
                MonitorPolo.ativo == True
            ).first()
        
        if not material:
            return jsonify({'success': False, 'message': 'Material não encontrado'}), 404
        
        movimentacoes = MovimentacaoMaterial.query.filter_by(
            material_id=material_id
        ).order_by(MovimentacaoMaterial.data_movimentacao.desc()).all()
        
        return jsonify({
            'success': True,
            'movimentacoes': [mov.to_dict() for mov in movimentacoes]
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== ROTAS DE RELATÓRIOS E EXPORTAÇÃO ====================

@material_routes.route('/api/materiais/relatorio', methods=['GET'])
@csrf.exempt
@login_required
def gerar_relatorio():
    """API para gerar relatório de materiais."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        polo_id = request.args.get('polo_id')
        tipo_relatorio = request.args.get('tipo', 'geral')  # geral, baixo_estoque, compras
        
        query = Material.query.filter_by(cliente_id=current_user.id, ativo=True)
        
        if polo_id:
            query = query.filter_by(polo_id=polo_id)
        
        if tipo_relatorio == 'baixo_estoque':
            query = query.filter(Material.quantidade_atual <= Material.quantidade_minima)
        elif tipo_relatorio == 'compras':
            query = query.filter(Material.quantidade_atual < Material.quantidade_minima)
        
        materiais = query.all()
        
        # Gerar texto para WhatsApp
        if tipo_relatorio == 'compras':
            texto_whatsapp = "📋 *LISTA DE COMPRAS*\n\n"
            for material in materiais:
                if material.quantidade_necessaria > 0:
                    texto_whatsapp += f"• {material.nome}: {material.quantidade_necessaria} {material.unidade}\n"
                    if material.polo:
                        texto_whatsapp += f"  📍 {material.polo.nome}\n"
            
            if not any(m.quantidade_necessaria > 0 for m in materiais):
                texto_whatsapp += "✅ Nenhum material precisa ser comprado no momento."
        else:
            texto_whatsapp = "📊 *RELATÓRIO DE MATERIAIS*\n\n"
            for material in materiais:
                status_emoji = "🔴" if material.status_estoque == "esgotado" else "🟡" if material.status_estoque == "baixo" else "🟢"
                texto_whatsapp += f"{status_emoji} *{material.nome}*\n"
                texto_whatsapp += f"   Estoque: {material.quantidade_atual} {material.unidade}\n"
                if material.polo:
                    texto_whatsapp += f"   📍 {material.polo.nome}\n"
                texto_whatsapp += "\n"
        
        return jsonify({
            'success': True,
            'materiais': [material.to_dict() for material in materiais],
            'texto_whatsapp': texto_whatsapp
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== ROTAS DE ATRIBUIÇÃO DE MONITORES ====================

@material_routes.route('/api/monitores/atribuir-polo', methods=['POST'])
@csrf.exempt
@login_required
def atribuir_monitor_polo():
    """API para atribuir monitor a um polo."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        data = request.get_json()
        monitor_id = data['monitor_id']
        polo_id = data['polo_id']
        
        # Verificar se o monitor e polo pertencem ao cliente
        monitor = Monitor.query.filter_by(id=monitor_id, cliente_id=current_user.id).first()
        polo = Polo.query.filter_by(id=polo_id, cliente_id=current_user.id).first()
        
        if not monitor or not polo:
            return jsonify({'success': False, 'message': 'Monitor ou polo não encontrado'}), 404
        
        # Verificar se já existe atribuição ativa
        atribuicao_existente = MonitorPolo.query.filter_by(
            monitor_id=monitor_id, polo_id=polo_id, ativo=True
        ).first()
        
        if atribuicao_existente:
            return jsonify({'success': False, 'message': 'Monitor já está atribuído a este polo'}), 400
        
        # Criar nova atribuição
        atribuicao = MonitorPolo(
            monitor_id=monitor_id,
            polo_id=polo_id
        )
        
        db.session.add(atribuicao)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Monitor atribuído ao polo com sucesso',
            'atribuicao': atribuicao.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@material_routes.route('/api/monitores/remover-polo', methods=['POST'])
@csrf.exempt
@login_required
def remover_monitor_polo():
    """API para remover monitor de um polo."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        data = request.get_json()
        monitor_id = data['monitor_id']
        polo_id = data['polo_id']
        
        # Buscar atribuição ativa
        atribuicao = MonitorPolo.query.filter_by(
            monitor_id=monitor_id, polo_id=polo_id, ativo=True
        ).first()
        
        if not atribuicao:
            return jsonify({'success': False, 'message': 'Atribuição não encontrada'}), 404
        
        # Verificar se o polo pertence ao cliente
        polo = Polo.query.filter_by(id=polo_id, cliente_id=current_user.id).first()
        if not polo:
            return jsonify({'success': False, 'message': 'Polo não encontrado'}), 404
        
        atribuicao.ativo = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Monitor removido do polo com sucesso'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@material_routes.route('/api/monitores/polos', methods=['GET'])
@csrf.exempt
@login_required
def listar_monitores_polos():
    """API para listar atribuições de monitores a polos."""
    if not verificar_acesso_cliente():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        # Buscar todas as atribuições ativas dos polos do cliente
        atribuicoes = db.session.query(MonitorPolo).join(Polo).filter(
            Polo.cliente_id == current_user.id,
            MonitorPolo.ativo == True
        ).all()
        
        return jsonify({
            'success': True,
            'atribuicoes': [atribuicao.to_dict() for atribuicao in atribuicoes]
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== ROTAS PARA PÁGINAS DE CADASTRO ====================

@material_routes.route('/novo-polo')
@login_required
def novo_polo():
    """Página para cadastro de novo polo."""
    if not verificar_acesso_cliente():
        flash('Acesso negado', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('material/novo_polo.html')


@material_routes.route('/novo-material')
@login_required
def novo_material():
    """Página para cadastro de novo material."""
    if not verificar_acesso_cliente():
        flash('Acesso negado', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('material/novo_material.html')
