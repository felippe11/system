from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from datetime import datetime
import random
from models import Sorteio, Inscricao, Evento, Oficina
from models.user import Usuario
from extensions import db
from utils import endpoints

# Criação do blueprint
sorteio_routes = Blueprint('sorteio_routes', __name__, template_folder="../templates/sorteio")

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

# ===========================
#   SORTEIOS
# ===========================

@sorteio_routes.route('/criar_sorteio', methods=['GET', 'POST'])
@login_required
def criar_sorteio():
    """
    Rota para criar um novo sorteio.
    GET: Exibe o formulário de criação
    POST: Processa o formulário e cria o sorteio
    """
    # Verificar se o usuário é um cliente
    if current_user.tipo != 'cliente':
        flash('Acesso negado. Apenas clientes podem gerenciar sorteios.', 'danger')
        return redirect(url_for(endpoints.DASHBOARD))
    
    # Listar eventos do cliente para o formulário
    eventos = Evento.query.filter_by(cliente_id=current_user.id).all()
    
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        premio = request.form.get('premio')
        descricao = request.form.get('descricao')
        tipo_sorteio = request.form.get('tipo_sorteio')
        evento_id = request.form.get('evento_id')
        oficina_id = request.form.get('oficina_id') if tipo_sorteio == 'oficina' else None
        
        # Validações básicas
        if not titulo or not premio or not evento_id:
            flash('Por favor, preencha todos os campos obrigatórios.', 'danger')
            return render_template('criar_sorteio.html', eventos=eventos)
          # Obter número de vencedores
        num_vencedores = request.form.get('num_vencedores', '1')
        # Converter para inteiro e garantir valor mínimo de 1
        try:
            num_vencedores = max(1, int(num_vencedores))
        except ValueError:
            num_vencedores = 1
            
        # Criar novo sorteio
        sorteio = Sorteio(
            titulo=titulo,
            premio=premio,
            descricao=descricao,
            cliente_id=current_user.id,
            evento_id=evento_id,
            oficina_id=oficina_id,
            num_vencedores=num_vencedores,
            status='pendente'
        )
        
        try:
            db.session.add(sorteio)
            db.session.commit()
            flash('Sorteio criado com sucesso!', 'success')
            return redirect(url_for('sorteio_routes.gerenciar_sorteios'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar sorteio: {str(e)}', 'danger')
    
    return render_template('criar_sorteio.html', eventos=eventos)

@sorteio_routes.route('/gerenciar_sorteios')
@login_required
def gerenciar_sorteios():
    """
    Rota para listar e gerenciar os sorteios existentes.
    """
    # Verificar se o usuário é um cliente
    if current_user.tipo != 'cliente':
        flash('Acesso negado. Apenas clientes podem gerenciar sorteios.', 'danger')
        return redirect(url_for(endpoints.DASHBOARD))
    
    # Filtros da URL
    evento_id = request.args.get('evento_id', type=int)
    status = request.args.get('status')
    
    # Consulta base
    query = Sorteio.query.filter_by(cliente_id=current_user.id)
    
    # Aplicar filtros
    if evento_id:
        query = query.filter_by(evento_id=evento_id)
    if status:
        query = query.filter_by(status=status)
    
    # Ordenar por data, mais recentes primeiro
    sorteios = query.order_by(Sorteio.data_sorteio.desc()).all()
    
    # Listar eventos do cliente para o filtro
    eventos = Evento.query.filter_by(cliente_id=current_user.id).all()
    
    return render_template('gerenciar_sorteios.html', 
                           sorteios=sorteios, 
                           eventos=eventos)


@sorteio_routes.route('/api/oficinas_evento/<int:evento_id>')
@login_required
def get_oficinas_evento(evento_id):
    """
    API para obter as oficinas de um evento específico.
    """
    try:
        oficinas = Oficina.query.filter_by(evento_id=evento_id).all()
        return jsonify({
            'success': True,
            'oficinas': [{'id': o.id, 'titulo': o.titulo} for o in oficinas]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@sorteio_routes.route('/api/participantes_contagem')
@login_required
def get_participantes_contagem():
    """
    API para contar o número de participantes elegíveis para um sorteio.
    """
    tipo = request.args.get('tipo')
    id_param = request.args.get('id', type=int)
    
    
    if not tipo or not id_param:
        return jsonify({'success': False, 'message': 'Parâmetros inválidos'})
    
    try:
        if tipo == 'evento':
            # Contar participantes de um evento - filtrar diretamente pelo evento_id na tabela Usuario
            total = Usuario.query.filter_by(evento_id=id_param).count()
        elif tipo == 'oficina':
            # Contar participantes de uma oficina
            total = Usuario.query.join(
                Inscricao, Usuario.id == Inscricao.usuario_id
            ).filter(
                Inscricao.oficina_id == id_param
            ).count()
        else:
            return jsonify({'success': False, 'message': 'Tipo inválido'})
        
        return jsonify({'success': True, 'total': total})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    """
    API para contar o número de participantes elegíveis para um sorteio.
    """
    tipo = request.args.get('tipo')
    id_param = request.args.get('id', type=int)
    
    if not tipo or not id_param:
        return jsonify({'success': False, 'message': 'Parâmetros inválidos'})
    
    try:
        if tipo == 'evento':
            # Contar participantes de um evento
            total = Inscricao.query.filter_by(evento_id=id_param).count()
        elif tipo == 'oficina':
            # Contar participantes de uma oficina
            total = Inscricao.query.filter_by(oficina_id=id_param).count()
        else:
            return jsonify({'success': False, 'message': 'Tipo inválido'})
        
        return jsonify({'success': True, 'total': total})
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
        if sorteio.status != 'realizado' or not sorteio.ganhadores:
            return jsonify({'success': False, 'message': 'Este sorteio ainda não foi realizado'})
        
        # Buscar os ganhadores do sorteio
        ganhadores_data = []
        for ganhador in sorteio.ganhadores:
            ganhadores_data.append({
                'id': ganhador.id,
                'nome': ganhador.nome,
                'email': ganhador.email
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
    Rota para realizar um sorteio, selecionando um ganhador aleatório.
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
        
        # Selecionar um participante aleatoriamente
        ganhador = random.choice(participantes)
        
        # Atualizar o sorteio com o ganhador
        sorteio.ganhador_id = ganhador.id
        sorteio.status = 'realizado'
        sorteio.data_sorteio = datetime.utcnow()
        
        db.session.commit()
        
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
                'ganhador': {
                    'id': ganhador.id,
                    'nome': ganhador.nome,
                    'email': ganhador.email
                }
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
    """
    Rota para realizar um sorteio, selecionando um ganhador aleatório.
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
        participantes = []
        if sorteio.oficina_id:
            # Sorteio para uma oficina específica - buscar usuários diretamente
            participantes = Usuario.query.filter_by(oficina_id=sorteio.oficina_id).all()
        else:
            # Sorteio para todo o evento - buscar usuários diretamente
            participantes = Usuario.query.filter_by(evento_id=sorteio.evento_id).all()
        
        if not participantes:
            return jsonify({'success': False, 'message': 'Não há participantes elegíveis para este sorteio'})
        
        # Selecionar um participante aleatoriamente
        ganhador = random.choice(participantes)
        
        # Atualizar o sorteio com o ganhador
        sorteio.ganhador_id = ganhador.id
        sorteio.status = 'realizado'
        sorteio.data_sorteio = datetime.utcnow()
        
        db.session.commit()
        
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
                'ganhador': {
                    'id': ganhador.id,
                    'nome': ganhador.nome,
                    'email': ganhador.email
                }
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
    """
    Rota para realizar um sorteio, selecionando um ganhador aleatório.
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
            # Sorteio para uma oficina específica
            participantes = Inscricao.query.filter_by(oficina_id=sorteio.oficina_id).all()
        else:
            # Sorteio para todo o evento
            participantes = Inscricao.query.filter_by(evento_id=sorteio.evento_id).all()
        
        if not participantes:
            return jsonify({'success': False, 'message': 'Não há participantes elegíveis para este sorteio'})
        
        # Selecionar um participante aleatoriamente
        inscricao_sorteada = random.choice(participantes)
        
        # Atualizar o sorteio com o ganhador
        sorteio.ganhador_id = inscricao_sorteada.usuario_id
        sorteio.status = 'realizado'
        sorteio.data_sorteio = datetime.utcnow()
        
        db.session.commit()
        
        # Buscar dados completos do ganhador
        ganhador = Usuario.query.get(inscricao_sorteada.usuario_id)
        
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
                'ganhador': {
                    'id': ganhador.id,
                    'nome': ganhador.nome,
                    'email': ganhador.email
                }
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@sorteio_routes.route('/cancelar_sorteio/<int:sorteio_id>', methods=['POST'])
@login_required
def cancelar_sorteio(sorteio_id):
    """
    Rota para cancelar um sorteio.
    """
    try:
        sorteio = Sorteio.query.get_or_404(sorteio_id)
        
        # Verificar se o usuário atual é o dono do sorteio
        if sorteio.cliente_id != current_user.id:
            return jsonify({'success': False, 'message': 'Acesso negado'})
        
        # Verificar se o sorteio já foi realizado ou cancelado
        if sorteio.status != 'pendente':
            return jsonify({'success': False, 'message': f'O sorteio não pode ser cancelado porque está com status: {sorteio.status}'})
        
        # Cancelar o sorteio
        sorteio.status = 'cancelado'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Sorteio cancelado com sucesso!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
