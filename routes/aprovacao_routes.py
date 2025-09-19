from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from datetime import datetime
from extensions import db
from models.compra import NivelAprovacao, AprovacaoCompra, Compra
from models.user import Usuario
from services.aprovacao_service import AprovacaoService
from utils.auth import cliente_required, role_required
from functools import wraps

aprovacao_routes = Blueprint('aprovacao', __name__, url_prefix='/aprovacao')

def aprovador_required(f):
    """Decorator para verificar se o usuário tem permissão para aprovar compras."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        is_json_request = (
            request.is_json
            or request.path.startswith('/aprovacao/api')
            or 'application/json' in request.headers.get('Accept', '')
        )

        if not current_user.is_authenticated:
            if is_json_request:
                return jsonify({'success': False, 'message': 'Autenticação necessária'}), 401
            abort(401)
        
        # Verificar se o usuário é admin ou tem permissão de aprovação
        if not (current_user.is_admin or 
                hasattr(current_user, 'pode_aprovar_compras') and current_user.pode_aprovar_compras):
            if is_json_request:
                return jsonify({'success': False, 'message': 'Acesso negado'}), 403
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

@aprovacao_routes.route('/api/aprovacoes/pendentes')
@login_required
@aprovador_required
def listar_aprovacoes_pendentes():
    """Lista aprovações pendentes para o usuário atual."""
    try:
        aprovacoes = AprovacaoService.obter_aprovacoes_pendentes(current_user.id)
        return jsonify({
            'success': True,
            'aprovacoes': [aprovacao.to_dict() for aprovacao in aprovacoes]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@aprovacao_routes.route('/api/aprovacoes/<int:aprovacao_id>/aprovar', methods=['POST'])
@login_required
@aprovador_required
def aprovar_compra(aprovacao_id):
    """Aprova uma compra específica."""
    try:
        data = request.get_json()
        comentario = data.get('comentario', '')
        
        resultado = AprovacaoService.aprovar_compra(
            aprovacao_id=aprovacao_id,
            aprovador_id=current_user.id,
            comentario=comentario
        )
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@aprovacao_routes.route('/api/aprovacoes/<int:aprovacao_id>/rejeitar', methods=['POST'])
@login_required
@aprovador_required
def rejeitar_compra(aprovacao_id):
    """Rejeita uma compra específica."""
    try:
        data = request.get_json()
        comentario = data.get('comentario', '')
        
        if not comentario:
            return jsonify({
                'success': False, 
                'message': 'Comentário é obrigatório para rejeição'
            }), 400
        
        resultado = AprovacaoService.rejeitar_compra(
            aprovacao_id=aprovacao_id,
            aprovador_id=current_user.id,
            comentario=comentario
        )
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@aprovacao_routes.route('/api/compras/<int:compra_id>/historico-aprovacoes')
@login_required
def obter_historico_aprovacoes(compra_id):
    """Obtém o histórico de aprovações de uma compra."""
    try:
        historico = AprovacaoService.obter_historico_aprovacoes(compra_id)
        return jsonify({
            'success': True,
            'historico': [aprovacao.to_dict() for aprovacao in historico]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@aprovacao_routes.route('/aprovacoes')
@login_required
def pagina_aprovacoes():
    """Página principal de aprovações."""
    try:
        # Obter aprovações pendentes
        aprovacoes_pendentes = AprovacaoService.obter_aprovacoes_pendentes(current_user.id)
        
        # Obter estatísticas
        total_pendentes = len(aprovacoes_pendentes)
        
        return render_template('compra/aprovacoes.html',
                             aprovacoes_pendentes=aprovacoes_pendentes,
                             total_pendentes=total_pendentes)
    except Exception as e:
        flash(f'Erro ao carregar aprovações: {str(e)}', 'error')
        return redirect(url_for('compra.gerenciar_compras'))

@aprovacao_routes.route('/niveis-aprovacao')
@login_required
@cliente_required
def gerenciar_niveis():
    """Página para gerenciar níveis de aprovação."""
    try:
        niveis = NivelAprovacao.query.filter_by(
            cliente_id=current_user.cliente_id,
            ativo=True
        ).order_by(NivelAprovacao.ordem).all()
        
        return render_template('compra/niveis_aprovacao.html', niveis=niveis)
    except Exception as e:
        flash(f'Erro ao carregar níveis de aprovação: {str(e)}', 'error')
        return redirect(url_for('compra_routes.gerenciar_compras'))

@aprovacao_routes.route('/api/niveis-aprovacao', methods=['POST'])
@login_required
@cliente_required
def criar_nivel_aprovacao():
    """Cria um novo nível de aprovação."""
    try:
        data = request.get_json()
        
        nivel = NivelAprovacao(
            nome=data['nome'],
            descricao=data.get('descricao'),
            ordem=data['ordem'],
            valor_minimo=data['valor_minimo'],
            valor_maximo=data.get('valor_maximo'),
            obrigatorio=data.get('obrigatorio', True),
            cliente_id=current_user.cliente_id
        )
        
        db.session.add(nivel)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Nível de aprovação criado com sucesso',
            'nivel': nivel.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@aprovacao_routes.route('/api/niveis-aprovacao/<int:nivel_id>', methods=['PUT'])
@login_required
@cliente_required
def atualizar_nivel_aprovacao(nivel_id):
    """Atualiza um nível de aprovação."""
    try:
        nivel = NivelAprovacao.query.filter_by(
            id=nivel_id,
            cliente_id=current_user.cliente_id
        ).first()
        
        if not nivel:
            return jsonify({'success': False, 'message': 'Nível não encontrado'}), 404
        
        data = request.get_json()
        
        nivel.nome = data.get('nome', nivel.nome)
        nivel.descricao = data.get('descricao', nivel.descricao)
        nivel.ordem = data.get('ordem', nivel.ordem)
        nivel.valor_minimo = data.get('valor_minimo', nivel.valor_minimo)
        nivel.valor_maximo = data.get('valor_maximo', nivel.valor_maximo)
        nivel.obrigatorio = data.get('obrigatorio', nivel.obrigatorio)
        nivel.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Nível de aprovação atualizado com sucesso',
            'nivel': nivel.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@aprovacao_routes.route('/api/niveis-aprovacao/<int:nivel_id>', methods=['DELETE'])
@login_required
@cliente_required
def excluir_nivel_aprovacao(nivel_id):
    """Exclui (desativa) um nível de aprovação."""
    try:
        nivel = NivelAprovacao.query.filter_by(
            id=nivel_id,
            cliente_id=current_user.cliente_id
        ).first()
        
        if not nivel:
            return jsonify({'success': False, 'message': 'Nível não encontrado'}), 404
        
        # Verificar se há aprovações pendentes para este nível
        aprovacoes_pendentes = AprovacaoCompra.query.filter_by(
            nivel_aprovacao_id=nivel_id,
            status='pendente'
        ).count()
        
        if aprovacoes_pendentes > 0:
            return jsonify({
                'success': False,
                'message': f'Não é possível excluir. Há {aprovacoes_pendentes} aprovações pendentes para este nível.'
            }), 400
        
        nivel.ativo = False
        nivel.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Nível de aprovação excluído com sucesso'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500