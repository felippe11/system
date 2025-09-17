"""
Editor Routes - Rotas para o editor visual similar ao Canva
"""

from flask import Blueprint, render_template, request, jsonify, session
from flask_login import login_required, current_user
import json
import os
from datetime import datetime

editor_bp = Blueprint('editor', __name__, url_prefix='/editor')

@editor_bp.route('/')
@login_required
def index():
    """Página principal do editor visual"""
    return render_template('editor/canva_editor.html')

@editor_bp.route('/new')
@login_required
def new_project():
    """Criar novo projeto"""
    return render_template('editor/canva_editor.html', project_type='new')

@editor_bp.route('/templates')
@login_required
def templates():
    """Listar templates disponíveis"""
    templates_data = {
        'presentation': {
            'name': 'Apresentação',
            'description': 'Template para apresentações profissionais',
            'thumbnail': '/static/img/templates/presentation.jpg',
            'category': 'business'
        },
        'poster': {
            'name': 'Poster',
            'description': 'Template para cartazes e eventos',
            'thumbnail': '/static/img/templates/poster.jpg',
            'category': 'marketing'
        },
        'social': {
            'name': 'Redes Sociais',
            'description': 'Template para posts em redes sociais',
            'thumbnail': '/static/img/templates/social.jpg',
            'category': 'social'
        },
        'certificate': {
            'name': 'Certificado',
            'description': 'Template para certificados e diplomas',
            'thumbnail': '/static/img/templates/certificate.jpg',
            'category': 'education'
        },
        'flyer': {
            'name': 'Panfleto',
            'description': 'Template para panfletos promocionais',
            'thumbnail': '/static/img/templates/flyer.jpg',
            'category': 'marketing'
        },
        'business_card': {
            'name': 'Cartão de Visita',
            'description': 'Template para cartões de visita',
            'thumbnail': '/static/img/templates/business_card.jpg',
            'category': 'business'
        }
    }
    
    return jsonify(templates_data)

@editor_bp.route('/elements')
@login_required
def elements():
    """Listar elementos disponíveis"""
    elements_data = {
        'shapes': {
            'name': 'Formas',
            'items': [
                {'id': 'rectangle', 'name': 'Retângulo', 'icon': 'square'},
                {'id': 'circle', 'name': 'Círculo', 'icon': 'circle'},
                {'id': 'triangle', 'name': 'Triângulo', 'icon': 'play'},
                {'id': 'line', 'name': 'Linha', 'icon': 'minus'},
                {'id': 'arrow', 'name': 'Seta', 'icon': 'arrow-right'},
                {'id': 'star', 'name': 'Estrela', 'icon': 'star'},
                {'id': 'heart', 'name': 'Coração', 'icon': 'heart'},
                {'id': 'diamond', 'name': 'Losango', 'icon': 'gem'}
            ]
        },
        'text': {
            'name': 'Texto',
            'items': [
                {'id': 'heading', 'name': 'Título', 'preview': 'Título Principal'},
                {'id': 'subtitle', 'name': 'Subtítulo', 'preview': 'Subtítulo'},
                {'id': 'body', 'name': 'Corpo', 'preview': 'Texto do corpo'},
                {'id': 'caption', 'name': 'Legenda', 'preview': 'Legenda pequena'}
            ]
        },
        'icons': {
            'name': 'Ícones',
            'categories': [
                {
                    'name': 'Básicos',
                    'items': [
                        {'id': 'fas fa-home', 'name': 'Casa'},
                        {'id': 'fas fa-user', 'name': 'Usuário'},
                        {'id': 'fas fa-heart', 'name': 'Coração'},
                        {'id': 'fas fa-star', 'name': 'Estrela'},
                        {'id': 'fas fa-phone', 'name': 'Telefone'},
                        {'id': 'fas fa-envelope', 'name': 'Email'},
                        {'id': 'fas fa-location-dot', 'name': 'Localização'},
                        {'id': 'fas fa-calendar', 'name': 'Calendário'}
                    ]
                },
                {
                    'name': 'Negócios',
                    'items': [
                        {'id': 'fas fa-briefcase', 'name': 'Maleta'},
                        {'id': 'fas fa-chart-bar', 'name': 'Gráfico'},
                        {'id': 'fas fa-handshake', 'name': 'Aperto de mão'},
                        {'id': 'fas fa-target', 'name': 'Alvo'},
                        {'id': 'fas fa-lightbulb', 'name': 'Lâmpada'},
                        {'id': 'fas fa-cog', 'name': 'Engrenagem'},
                        {'id': 'fas fa-trophy', 'name': 'Troféu'},
                        {'id': 'fas fa-rocket', 'name': 'Foguete'}
                    ]
                },
                {
                    'name': 'Redes Sociais',
                    'items': [
                        {'id': 'fab fa-facebook', 'name': 'Facebook'},
                        {'id': 'fab fa-instagram', 'name': 'Instagram'},
                        {'id': 'fab fa-twitter', 'name': 'Twitter'},
                        {'id': 'fab fa-linkedin', 'name': 'LinkedIn'},
                        {'id': 'fab fa-youtube', 'name': 'YouTube'},
                        {'id': 'fab fa-whatsapp', 'name': 'WhatsApp'},
                        {'id': 'fab fa-telegram', 'name': 'Telegram'},
                        {'id': 'fab fa-tiktok', 'name': 'TikTok'}
                    ]
                }
            ]
        },
        'graphics': {
            'name': 'Gráficos',
            'items': [
                {'id': 'chart_bar', 'name': 'Gráfico de Barras', 'type': 'chart'},
                {'id': 'chart_pie', 'name': 'Gráfico de Pizza', 'type': 'chart'},
                {'id': 'chart_line', 'name': 'Gráfico de Linha', 'type': 'chart'},
                {'id': 'progress_bar', 'name': 'Barra de Progresso', 'type': 'widget'},
                {'id': 'timeline', 'name': 'Linha do Tempo', 'type': 'widget'},
                {'id': 'infographic', 'name': 'Infográfico', 'type': 'widget'}
            ]
        }
    }
    
    return jsonify(elements_data)

@editor_bp.route('/save', methods=['POST'])
@login_required
def save_project():
    """Salvar projeto do usuário"""
    try:
        data = request.get_json()
        
        project_data = {
            'id': data.get('id'),
            'name': data.get('name', 'Projeto sem título'),
            'canvas_data': data.get('canvas_data'),
            'thumbnail': data.get('thumbnail'),
            'user_id': current_user.id,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Aqui você salvaria no banco de dados
        # Por enquanto, vamos simular salvando em sessão
        if 'user_projects' not in session:
            session['user_projects'] = []
        
        # Verificar se é um projeto existente ou novo
        existing_project = None
        for i, project in enumerate(session['user_projects']):
            if project.get('id') == project_data['id']:
                existing_project = i
                break
        
        if existing_project is not None:
            session['user_projects'][existing_project] = project_data
        else:
            project_data['id'] = f"project_{len(session['user_projects']) + 1}"
            session['user_projects'].append(project_data)
        
        session.modified = True
        
        return jsonify({
            'success': True,
            'message': 'Projeto salvo com sucesso!',
            'project_id': project_data['id']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao salvar projeto: {str(e)}'
        }), 500

@editor_bp.route('/load/<project_id>')
@login_required
def load_project(project_id):
    """Carregar projeto específico"""
    try:
        user_projects = session.get('user_projects', [])
        
        for project in user_projects:
            if project.get('id') == project_id:
                return jsonify({
                    'success': True,
                    'project': project
                })
        
        return jsonify({
            'success': False,
            'message': 'Projeto não encontrado'
        }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao carregar projeto: {str(e)}'
        }), 500

@editor_bp.route('/projects')
@login_required
def list_projects():
    """Listar projetos do usuário"""
    try:
        user_projects = session.get('user_projects', [])
        
        # Filtrar apenas projetos do usuário atual
        user_projects = [p for p in user_projects if p.get('user_id') == current_user.id]
        
        return jsonify({
            'success': True,
            'projects': user_projects
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao listar projetos: {str(e)}'
        }), 500

@editor_bp.route('/export/<project_id>')
@login_required
def export_project(project_id):
    """Exportar projeto em diferentes formatos"""
    try:
        format_type = request.args.get('format', 'png')
        
        user_projects = session.get('user_projects', [])
        project = None
        
        for p in user_projects:
            if p.get('id') == project_id:
                project = p
                break
        
        if not project:
            return jsonify({
                'success': False,
                'message': 'Projeto não encontrado'
            }), 404
        
        # Aqui você implementaria a lógica de exportação
        # Por enquanto, retornamos os dados do projeto
        return jsonify({
            'success': True,
            'project': project,
            'export_format': format_type
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao exportar projeto: {str(e)}'
        }), 500

@editor_bp.route('/fonts')
@login_required
def get_fonts():
    """Listar fontes disponíveis"""
    fonts_data = {
        'google_fonts': [
            {'name': 'Inter', 'family': 'Inter, sans-serif', 'category': 'sans-serif'},
            {'name': 'Roboto', 'family': 'Roboto, sans-serif', 'category': 'sans-serif'},
            {'name': 'Open Sans', 'family': 'Open Sans, sans-serif', 'category': 'sans-serif'},
            {'name': 'Lato', 'family': 'Lato, sans-serif', 'category': 'sans-serif'},
            {'name': 'Montserrat', 'family': 'Montserrat, sans-serif', 'category': 'sans-serif'},
            {'name': 'Poppins', 'family': 'Poppins, sans-serif', 'category': 'sans-serif'},
            {'name': 'Playfair Display', 'family': 'Playfair Display, serif', 'category': 'serif'},
            {'name': 'Merriweather', 'family': 'Merriweather, serif', 'category': 'serif'},
            {'name': 'Dancing Script', 'family': 'Dancing Script, cursive', 'category': 'handwriting'},
            {'name': 'Pacifico', 'family': 'Pacifico, cursive', 'category': 'handwriting'}
        ],
        'system_fonts': [
            {'name': 'Arial', 'family': 'Arial, sans-serif', 'category': 'sans-serif'},
            {'name': 'Helvetica', 'family': 'Helvetica, sans-serif', 'category': 'sans-serif'},
            {'name': 'Times New Roman', 'family': 'Times New Roman, serif', 'category': 'serif'},
            {'name': 'Georgia', 'family': 'Georgia, serif', 'category': 'serif'},
            {'name': 'Courier New', 'family': 'Courier New, monospace', 'category': 'monospace'}
        ]
    }
    
    return jsonify(fonts_data)

@editor_bp.route('/colors')
@login_required
def get_color_palettes():
    """Obter paletas de cores predefinidas"""
    color_palettes = {
        'trending': [
            {'name': 'Sunset', 'colors': ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']},
            {'name': 'Ocean', 'colors': ['#0984e3', '#74b9ff', '#00b894', '#00cec9', '#6c5ce7']},
            {'name': 'Forest', 'colors': ['#00b894', '#55a3ff', '#fd79a8', '#fdcb6e', '#6c5ce7']},
            {'name': 'Sunset', 'colors': ['#fd79a8', '#fdcb6e', '#e17055', '#74b9ff', '#a29bfe']}
        ],
        'business': [
            {'name': 'Professional', 'colors': ['#2d3436', '#636e72', '#74b9ff', '#0984e3', '#00b894']},
            {'name': 'Corporate', 'colors': ['#2c3e50', '#34495e', '#3498db', '#2980b9', '#27ae60']},
            {'name': 'Modern', 'colors': ['#1e3a8a', '#3b82f6', '#06b6d4', '#10b981', '#f59e0b']}
        ],
        'creative': [
            {'name': 'Vibrant', 'colors': ['#e74c3c', '#f39c12', '#f1c40f', '#2ecc71', '#9b59b6']},
            {'name': 'Pastel', 'colors': ['#fab1a0', '#fd79a8', '#fdcb6e', '#55efc4', '#74b9ff']},
            {'name': 'Neon', 'colors': ['#ff006e', '#8338ec', '#3a86ff', '#06ffa5', '#ffbe0b']}
        ]
    }
    
    return jsonify(color_palettes)