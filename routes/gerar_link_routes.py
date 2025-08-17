from flask import Blueprint, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import Evento
from models.user import LinkCadastro
import uuid

gerar_link_routes = Blueprint('gerar_link_routes', __name__)


@gerar_link_routes.route('/gerar_link', methods=['GET', 'POST'])
@login_required
def gerar_link():
    if current_user.tipo not in ['cliente', 'admin']:
        return "Forbidden", 403

    cliente_id = current_user.id

    if request.method == 'POST':
        # Obtém os dados JSON da requisição
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Nenhum dado enviado'}), 400

        evento_id = data.get('evento_id')
        slug_customizado = data.get('slug_customizado')

        if not evento_id:
            return jsonify({'success': False, 'message': 'Evento não especificado'}), 400
            
        # Garantir que evento_id seja um inteiro
        try:
            evento_id = int(evento_id)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'ID do evento inválido'}), 400

        # Verifica se o evento pertence ao cliente
        evento = Evento.query.filter_by(id=evento_id, cliente_id=cliente_id).first()
        if not evento and current_user.tipo != 'admin':
            return jsonify({'success': False, 'message': 'Evento inválido ou não autorizado'}), 403

        # Gera um token único
        novo_token = str(uuid.uuid4())

        # Valida e limpa o slug personalizado
        if slug_customizado:
            slug_customizado = slug_customizado.strip().lower().replace(' ', '-')
            if LinkCadastro.query.filter_by(slug_customizado=slug_customizado).first():
                return jsonify({'success': False, 'message': 'Slug já está em uso'}), 400
        else:
            slug_customizado = None

        # Cria o link de cadastro no banco
        novo_link = LinkCadastro(
            cliente_id=cliente_id,
            evento_id=evento_id,
            token=novo_token,
            slug_customizado=slug_customizado
        )
        db.session.add(novo_link)
        db.session.commit()

        # Define a URL base dependendo do ambiente
        if request.host.startswith("127.0.0.1") or "localhost" in request.host:
            base_url = "http://127.0.0.1:5000"  # URL local
        else:
            base_url = "https://appfiber.com.br"  # URL de produção

        # Gera o link final
        if slug_customizado:
            link_gerado = f"{base_url}/inscricao/{slug_customizado}"
        else:
            link_gerado = f"{base_url}{url_for('inscricao_routes.cadastro_participante', identifier=novo_token)}"
        return jsonify({'success': True, 'link': link_gerado})

    # Para GET, verificamos se é uma solicitação para listar links de um evento específico
    evento_id = request.args.get('evento_id')
    if evento_id:
        # Converter para inteiro, pois o ID do evento é um inteiro no banco de dados
        try:
            evento_id = int(evento_id)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'ID do evento inválido'}), 400
            
        # Verificar se o evento pertence ao cliente atual
        evento = Evento.query.filter_by(id=evento_id, cliente_id=cliente_id).first()
        if not evento and current_user.tipo != 'admin':
            return jsonify({'success': False, 'links': [], 'message': 'Evento não autorizado'}), 403
        
        # Buscar todos os links para este evento
        links = LinkCadastro.query.filter_by(evento_id=evento_id, cliente_id=cliente_id).all()
        
        # Montar a lista de links com URLs completas
        links_list = []
        for link in links:
            if request.host.startswith("127.0.0.1") or "localhost" in request.host:
                base_url = "http://127.0.0.1:5000"
            else:
                base_url = "https://appfiber.com.br"
                
            if link.slug_customizado:
                url = f"{base_url}/inscricao/{link.slug_customizado}"
            else:
                url = f"{base_url}{url_for('inscricao_routes.cadastro_participante', identifier=link.token)}"                
            links_list.append({
                'id': link.id,
                'token': link.token,
                'slug': link.slug_customizado,
                'url': url,
                'criado_em': link.criado_em.isoformat()
            })
            
        return jsonify({'success': True, 'links': links_list})
        
    # Para GET sem evento_id, apenas retorna os eventos disponíveis
    eventos = Evento.query.filter_by(cliente_id=cliente_id).all()
    return jsonify({'eventos': [{'id': e.id, 'nome': e.nome} for e in eventos]})

@gerar_link_routes.route('/excluir_link', methods=['POST'])
@login_required
def excluir_link():
    if current_user.tipo not in ['cliente', 'admin']:
        return jsonify({'success': False, 'message': 'Não autorizado'}), 403
        
    data = request.get_json()
    if not data or 'link_id' not in data:
        return jsonify({'success': False, 'message': 'ID do link não fornecido'}), 400
        
    link_id = data['link_id']
    link = LinkCadastro.query.get(link_id)
    
    if not link:
        return jsonify({'success': False, 'message': 'Link não encontrado'}), 404
        
    if link.cliente_id != current_user.id and current_user.tipo != 'admin':
        return jsonify({'success': False, 'message': 'Não autorizado a excluir este link'}), 403
        
    db.session.delete(link)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Link excluído com sucesso'})
