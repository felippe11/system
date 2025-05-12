from flask import Blueprint, jsonify
from flask_login import current_user, login_required
from datetime import datetime
import random
from models import Sorteio, Usuario, Inscricao
from extensions import db

# Criação do blueprint
sorteio_routes = Blueprint('sorteio_routes', __name__)

@sorteio_routes.route('/api/sorteio_info/<int:sorteio_id>')
@login_required
def get_sorteio_info(sorteio_id):
    """
    API para obter informações básicas sobre um sorteio, incluindo número de vencedores.
    """
    try:
        sorteio = Sorteio.query.get_or_404(sorteio_id)
        
        # Verificar se o usuário atual é o dono do sorteio
        if sorteio.cliente_id != current_user.id:
            return jsonify({'success': False, 'message': 'Acesso negado'})
        
        # Retornar informação do número de vencedores
        return jsonify({
            'success': True,
            'num_vencedores': sorteio.num_vencedores if hasattr(sorteio, 'num_vencedores') and sorteio.num_vencedores else 1
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@sorteio_routes.route('/api/sorteio/<int:sorteio_id>')
@login_required
def get_sorteio(sorteio_id):
    """
    API para obter detalhes de um sorteio específico.
    """
    try:
        sorteio = Sorteio.query.get_or_404(sorteio_id)
        
        # Verificar se o usuário atual é o dono do sorteio
        if sorteio.cliente_id != current_user.id:
            return jsonify({'success': False, 'message': 'Acesso negado'})
        
        # Verificar se o sorteio foi realizado
        if sorteio.status != 'realizado':
            return jsonify({'success': False, 'message': 'Este sorteio ainda não foi realizado'})
        
        # Buscar os ganhadores do sorteio (pode ser uma lista vazia)
        ganhadores_data = []
        if hasattr(sorteio, 'ganhadores') and sorteio.ganhadores:
            for ganhador in sorteio.ganhadores:
                ganhadores_data.append({
                    'id': ganhador.id,
                    'nome': ganhador.nome,
                    'email': ganhador.email
                })
        # Compatibilidade com versão antiga se ainda houver campo ganhador_id
        elif hasattr(sorteio, 'ganhador') and sorteio.ganhador:
            ganhadores_data.append({
                'id': sorteio.ganhador.id,
                'nome': sorteio.ganhador.nome,
                'email': sorteio.ganhador.email
            })
        
        # Formatar dados do sorteio
        return jsonify({
            'success': True,
            'sorteio': {
                'id': sorteio.id,
                'titulo': sorteio.titulo,
                'premio': sorteio.premio,
                'descricao': sorteio.descricao,
                'data_sorteio': sorteio.data_sorteio.isoformat(),
                'status': sorteio.status,
                'ganhadores': ganhadores_data
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@sorteio_routes.route('/realizar_sorteio/<int:sorteio_id>', methods=['POST'])
@login_required
def realizar_sorteio(sorteio_id):
    """
    Rota para realizar um sorteio, selecionando ganhadores aleatórios.
    """
    try:
        sorteio = Sorteio.query.get_or_404(sorteio_id)
        
        # Verificar se o usuário atual é o dono do sorteio
        if sorteio.cliente_id != current_user.id:
            return jsonify({'success': False, 'message': 'Acesso negado'})
        
        # Verificar se o sorteio já foi realizado ou cancelado
        if sorteio.status != 'pendente':
            return jsonify({'success': False, 'message': f'O sorteio não pode ser realizado porque está com status: {sorteio.status}'})
        
        # Buscar participantes elegíveis baseado no tipo de sorteio (evento ou oficina)
        if sorteio.oficina_id:
            # Sorteio para uma oficina específica - buscar usuários através da tabela de inscrições
            participantes_ids = db.session.query(Inscricao.usuario_id).filter_by(oficina_id=sorteio.oficina_id).all()
            if not participantes_ids:
                return jsonify({'success': False, 'message': 'Não há participantes elegíveis para este sorteio'})
            
            # Extrair os IDs dos usuários da lista de tuplas
            usuario_ids = [id[0] for id in participantes_ids]
            
            # Buscar os objetos de usuário
            participantes = Usuario.query.filter(Usuario.id.in_(usuario_ids)).all()
        else:
            # Sorteio para todo o evento - buscar usuários diretamente
            participantes = Usuario.query.filter_by(evento_id=sorteio.evento_id).all()
        
        if not participantes:
            return jsonify({'success': False, 'message': 'Não há participantes elegíveis para este sorteio'})
        
        # Selecionar ganhadores aleatoriamente conforme o número definido
        num_vencedores = sorteio.num_vencedores if hasattr(sorteio, 'num_vencedores') and sorteio.num_vencedores else 1
        
        # Limitar o número de vencedores ao total de participantes
        num_vencedores = min(num_vencedores, len(participantes))
        
        # Selecionar ganhadores aleatoriamente
        ganhadores = random.sample(participantes, num_vencedores)
        
        # Atualizar o sorteio com os ganhadores
        sorteio.status = 'realizado'
        sorteio.data_sorteio = datetime.utcnow()
        
        # Limpar ganhadores anteriores e adicionar os novos
        sorteio.ganhadores = ganhadores
        
        db.session.commit()
        
        # Preparar dados de ganhadores para retornar na API
        ganhadores_data = []
        for ganhador in ganhadores:
            ganhadores_data.append({
                'id': ganhador.id,
                'nome': ganhador.nome,
                'email': ganhador.email
            })
        
        # Formatar dados do sorteio realizado
        return jsonify({
            'success': True,
            'message': 'Sorteio realizado com sucesso!',
            'sorteio': {
                'id': sorteio.id,
                'titulo': sorteio.titulo,
                'premio': sorteio.premio,
                'descricao': sorteio.descricao,
                'data_sorteio': sorteio.data_sorteio.isoformat(),
                'status': sorteio.status,
                'ganhadores': ganhadores_data
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@sorteio_routes.route('/excluir_sorteio/<int:sorteio_id>', methods=['POST'])
@login_required
def excluir_sorteio(sorteio_id):
    """
    Rota para excluir um sorteio permanentemente.
    """
    try:
        sorteio = Sorteio.query.get_or_404(sorteio_id)
        
        # Verificar se o usuário atual é o dono do sorteio
        if sorteio.cliente_id != current_user.id:
            return jsonify({'success': False, 'message': 'Acesso negado'})
        
        # Limpar qualquer associação com ganhadores
        if hasattr(sorteio, 'ganhadores'):
            sorteio.ganhadores = []
        
        # Remover o sorteio
        db.session.delete(sorteio)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Sorteio excluído com sucesso!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
