from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime

from extensions import db
from models.submission_system import (
    ReviewerProfile, ReviewerPreference, DistributionConfig, 
    SubmissionCategory, SpreadsheetMapping, ImportedSubmission
)
from models.review import Submission, Assignment
from models.event import Evento
from models.user import Usuario
from services.distribution_service import DistributionService
from services.spreadsheet_service import SpreadsheetService
from utils.auth import admin_required

submission_distribution_routes = Blueprint('submission_distribution', __name__, url_prefix='/submission-distribution')

# ============================================================================
# CONFIGURAÇÃO DE DISTRIBUIÇÃO
# ============================================================================

@submission_distribution_routes.route('/config/<int:evento_id>')
@login_required
@admin_required
def distribution_config(evento_id):
    """Página de configuração de distribuição."""
    evento = Evento.query.get_or_404(evento_id)
    
    # Carregar ou criar configuração
    config = DistributionConfig.query.filter_by(evento_id=evento_id).first()
    if not config:
        config = DistributionConfig(evento_id=evento_id)
        db.session.add(config)
        db.session.commit()
    
    # Carregar categorias
    categories = SubmissionCategory.query.filter_by(evento_id=evento_id).all()
    
    # Carregar revisores
    reviewers = ReviewerProfile.query.filter_by(evento_id=evento_id).all()
    
    return render_template('submission_distribution/config.html', 
                         evento=evento, config=config, 
                         categories=categories, reviewers=reviewers)

@submission_distribution_routes.route('/config/<int:evento_id>/save', methods=['POST'])
@login_required
@admin_required
def save_distribution_config(evento_id):
    """Salva configuração de distribuição."""
    try:
        config = DistributionConfig.query.filter_by(evento_id=evento_id).first()
        if not config:
            config = DistributionConfig(evento_id=evento_id)
            db.session.add(config)
        
        # Atualizar configurações
        config.reviewers_per_submission = int(request.form.get('reviewers_per_submission', 2))
        config.distribution_mode = request.form.get('distribution_mode', 'balanced')
        config.blind_type = request.form.get('blind_type', 'single')
        config.enable_conflict_detection = 'enable_conflict_detection' in request.form
        config.enable_load_balancing = 'enable_load_balancing' in request.form
        config.enable_affinity_matching = 'enable_affinity_matching' in request.form
        config.max_submissions_per_reviewer = int(request.form.get('max_submissions_per_reviewer', 15))
        config.min_affinity_level = int(request.form.get('min_affinity_level', 1))
        config.allow_overload_on_shortage = 'allow_overload_on_shortage' in request.form
        config.fallback_to_random = 'fallback_to_random' in request.form
        
        db.session.commit()
        flash('Configuração salva com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao salvar configuração: {str(e)}', 'error')
    
    return redirect(url_for('submission_distribution.distribution_config', evento_id=evento_id))

# ============================================================================
# GESTÃO DE REVISORES
# ============================================================================

@submission_distribution_routes.route('/reviewers/<int:evento_id>')
@login_required
@admin_required
def manage_reviewers(evento_id):
    """Página de gestão de revisores."""
    evento = Evento.query.get_or_404(evento_id)
    reviewers = ReviewerProfile.query.filter_by(evento_id=evento_id).all()
    categories = SubmissionCategory.query.filter_by(evento_id=evento_id).all()
    
    return render_template('submission_distribution/reviewers.html',
                         evento=evento, reviewers=reviewers, categories=categories)

@submission_distribution_routes.route('/reviewers/<int:evento_id>/add', methods=['POST'])
@login_required
@admin_required
def add_reviewer(evento_id):
    """Adiciona novo revisor."""
    try:
        usuario_id = request.form.get('usuario_id')
        max_assignments = int(request.form.get('max_assignments', 15))
        institution = request.form.get('institution', '')
        expertise_areas = request.form.get('expertise_areas', '')
        
        # Verificar se usuário existe
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            flash('Usuário não encontrado!', 'error')
            return redirect(url_for('submission_distribution.manage_reviewers', evento_id=evento_id))
        
        # Verificar se já é revisor do evento
        existing = ReviewerProfile.query.filter_by(
            usuario_id=usuario_id, evento_id=evento_id
        ).first()
        
        if existing:
            flash('Usuário já é revisor deste evento!', 'warning')
            return redirect(url_for('submission_distribution.manage_reviewers', evento_id=evento_id))
        
        # Criar perfil de revisor
        reviewer = ReviewerProfile(
            usuario_id=usuario_id,
            evento_id=evento_id,
            max_assignments=max_assignments,
            institution=institution,
            expertise_areas=expertise_areas
        )
        
        db.session.add(reviewer)
        db.session.commit()
        
        flash('Revisor adicionado com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar revisor: {str(e)}', 'error')
    
    return redirect(url_for('submission_distribution.manage_reviewers', evento_id=evento_id))

@submission_distribution_routes.route('/reviewers/<int:reviewer_id>/preferences', methods=['POST'])
@login_required
@admin_required
def update_reviewer_preferences(reviewer_id):
    """Atualiza preferências do revisor."""
    try:
        reviewer = ReviewerProfile.query.get_or_404(reviewer_id)
        
        # Limpar preferências existentes
        ReviewerPreference.query.filter_by(reviewer_profile_id=reviewer_id).delete()
        
        # Adicionar novas preferências
        preferences_data = request.get_json()
        for category_id, affinity_level in preferences_data.items():
            if int(affinity_level) > 0:  # Apenas preferências positivas
                preference = ReviewerPreference(
                    reviewer_profile_id=reviewer_id,
                    category_id=int(category_id),
                    affinity_level=int(affinity_level)
                )
                db.session.add(preference)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Preferências atualizadas!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

# ============================================================================
# IMPORTAÇÃO DE PLANILHAS
# ============================================================================

@submission_distribution_routes.route('/import/<int:evento_id>')
@login_required
@admin_required
def import_spreadsheet(evento_id):
    """Página de importação de planilhas."""
    evento = Evento.query.get_or_404(evento_id)
    
    # Carregar mapeamentos salvos
    service = SpreadsheetService(evento_id)
    saved_mappings = service.get_saved_mappings()
    
    return render_template('submission_distribution/import.html',
                         evento=evento, saved_mappings=saved_mappings)

@submission_distribution_routes.route('/import/<int:evento_id>/analyze', methods=['POST'])
@login_required
@admin_required
def analyze_spreadsheet(evento_id):
    """Analisa planilha enviada e sugere mapeamentos."""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'})
        
        # Validar tipo de arquivo
        allowed_extensions = {'.xlsx', '.xls', '.csv'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'success': False, 'error': 'Tipo de arquivo não suportado'})
        
        # Analisar planilha
        service = SpreadsheetService(evento_id)
        result = service.analyze_spreadsheet(file.read(), file.filename)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@submission_distribution_routes.route('/import/<int:evento_id>/execute', methods=['POST'])
@login_required
@admin_required
def execute_import(evento_id):
    """Executa importação com mapeamento configurado."""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'})
        
        file = request.files['file']
        column_mapping = request.form.get('column_mapping')
        normalization_config = request.form.get('normalization_config')
        
        if not column_mapping:
            return jsonify({'success': False, 'error': 'Mapeamento de colunas obrigatório'})
        
        # Parse JSON
        column_mapping = json.loads(column_mapping)
        normalization_config = json.loads(normalization_config) if normalization_config else None
        
        # Executar importação
        service = SpreadsheetService(evento_id)
        result = service.import_spreadsheet(
            file.read(), file.filename, column_mapping, normalization_config
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@submission_distribution_routes.route('/import/<int:evento_id>/process', methods=['POST'])
@login_required
@admin_required
def process_imported(evento_id):
    """Processa submissões importadas criando objetos Submission."""
    try:
        batch_id = request.form.get('batch_id')
        
        service = SpreadsheetService(evento_id)
        result = service.process_imported_submissions(batch_id)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@submission_distribution_routes.route('/import/<int:evento_id>/stats')
@login_required
@admin_required
def import_stats(evento_id):
    """Retorna estatísticas de importação."""
    try:
        batch_id = request.args.get('batch_id')
        
        service = SpreadsheetService(evento_id)
        stats = service.get_import_stats(batch_id)
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@submission_distribution_routes.route('/import/<int:evento_id>/template')
@login_required
@admin_required
def download_template(evento_id):
    """Download de template de planilha."""
    try:
        mapping_id = request.args.get('mapping_id', type=int)
        
        service = SpreadsheetService(evento_id)
        template_data = service.generate_template(mapping_id)
        
        from flask import Response
        return Response(
            template_data,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': 'attachment; filename=template_submissoes.xlsx'}
        )
        
    except Exception as e:
        flash(f'Erro ao gerar template: {str(e)}', 'error')
        return redirect(url_for('submission_distribution.import_spreadsheet', evento_id=evento_id))

# ============================================================================
# DISTRIBUIÇÃO AUTOMÁTICA
# ============================================================================

@submission_distribution_routes.route('/distribute/<int:evento_id>')
@login_required
@admin_required
def distribution_dashboard(evento_id):
    """Dashboard de distribuição automática."""
    evento = Evento.query.get_or_404(evento_id)
    
    # Carregar estatísticas
    service = DistributionService(evento_id)
    stats = service.get_distribution_stats()
    
    # Carregar submissões pendentes
    pending_submissions = Submission.query.filter_by(evento_id=evento_id).outerjoin(Assignment).filter(
        Assignment.id.is_(None)
    ).all()
    
    return render_template('submission_distribution/dashboard.html',
                         evento=evento, stats=stats, 
                         pending_submissions=pending_submissions)

@submission_distribution_routes.route('/distribute/<int:evento_id>/execute', methods=['POST'])
@login_required
@admin_required
def execute_distribution(evento_id):
    """Executa distribuição automática."""
    try:
        submission_ids = request.form.getlist('submission_ids')
        seed = request.form.get('seed')
        
        # Converter IDs para inteiros
        if submission_ids:
            submission_ids = [int(id) for id in submission_ids]
        else:
            submission_ids = None
        
        # Executar distribuição
        service = DistributionService(evento_id)
        result = service.distribute_submissions(submission_ids, seed)
        
        if result['success']:
            flash(f"Distribuição concluída! {result['total_assignments']} atribuições criadas.", 'success')
        else:
            flash('Erro na distribuição. Verifique os logs.', 'error')
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@submission_distribution_routes.route('/distribute/<int:evento_id>/stats')
@login_required
@admin_required
def distribution_stats(evento_id):
    """Retorna estatísticas de distribuição."""
    try:
        service = DistributionService(evento_id)
        stats = service.get_distribution_stats()
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@submission_distribution_routes.route('/distribute/<int:evento_id>/rebalance', methods=['POST'])
@login_required
@admin_required
def rebalance_assignments(evento_id):
    """Rebalanceia atribuições existentes."""
    try:
        service = DistributionService(evento_id)
        result = service.rebalance_assignments()
        
        flash('Rebalanceamento concluído!', 'success')
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================================================
# GESTÃO DE CATEGORIAS
# ============================================================================

@submission_distribution_routes.route('/categories/<int:evento_id>')
@login_required
@admin_required
def manage_categories(evento_id):
    """Página de gestão de categorias."""
    evento = Evento.query.get_or_404(evento_id)
    categories = SubmissionCategory.query.filter_by(evento_id=evento_id).all()
    
    return render_template('submission_distribution/categories.html',
                         evento=evento, categories=categories)

@submission_distribution_routes.route('/categories/<int:evento_id>/add', methods=['POST'])
@login_required
@admin_required
def add_category(evento_id):
    """Adiciona nova categoria."""
    try:
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        if not name:
            flash('Nome da categoria é obrigatório!', 'error')
            return redirect(url_for('submission_distribution.manage_categories', evento_id=evento_id))
        
        # Normalizar nome
        normalized_name = name.lower().strip()
        
        # Verificar se já existe
        existing = SubmissionCategory.query.filter_by(
            evento_id=evento_id, normalized_name=normalized_name
        ).first()
        
        if existing:
            flash('Categoria já existe!', 'warning')
            return redirect(url_for('submission_distribution.manage_categories', evento_id=evento_id))
        
        # Criar categoria
        category = SubmissionCategory(
            name=name,
            normalized_name=normalized_name,
            description=description,
            evento_id=evento_id
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash('Categoria adicionada com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar categoria: {str(e)}', 'error')
    
    return redirect(url_for('submission_distribution.manage_categories', evento_id=evento_id))

# ============================================================================
# API ENDPOINTS
# ============================================================================

@submission_distribution_routes.route('/api/reviewers/<int:evento_id>')
@login_required
@admin_required
def api_reviewers(evento_id):
    """API para listar revisores."""
    reviewers = ReviewerProfile.query.filter_by(evento_id=evento_id).all()
    
    return jsonify([{
        'id': r.id,
        'usuario_id': r.usuario_id,
        'nome': r.usuario.nome if r.usuario else 'N/A',
        'email': r.usuario.email if r.usuario else 'N/A',
        'max_assignments': r.max_assignments,
        'current_load': r.current_load,
        'availability_percentage': r.availability_percentage,
        'available': r.available,
        'institution': r.institution
    } for r in reviewers])

@submission_distribution_routes.route('/api/submissions/<int:evento_id>')
@login_required
@admin_required
def api_submissions(evento_id):
    """API para listar submissões."""
    submissions = Submission.query.filter_by(evento_id=evento_id).all()
    
    return jsonify([{
        'id': s.id,
        'title': s.title,
        'author': s.author.nome if s.author else 'N/A',
        'status': s.status,
        'category': s.attributes.get('category', 'N/A') if s.attributes else 'N/A',
        'assignments_count': len(s.assignments),
        'created_at': s.created_at.isoformat()
    } for s in submissions])

# ============================================================================
# DASHBOARD DE MÉTRICAS
# ============================================================================

@submission_distribution_routes.route('/metrics/<int:evento_id>')
@login_required
@admin_required
def metrics_dashboard(evento_id):
    """Dashboard de métricas e acompanhamento."""
    evento = Evento.query.get_or_404(evento_id)
    return render_template('submission_distribution/metrics.html', evento=evento)

@submission_distribution_routes.route('/api/metrics/<int:evento_id>')
@login_required
@admin_required
def get_metrics(evento_id):
    """API para obter métricas do sistema de distribuição."""
    try:
        from services.audit_service import AuditService
        
        # Parâmetros de filtro
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        metric_type = request.args.get('metric_type', 'all')
        
        audit_service = AuditService(evento_id)
        
        # Dados de resumo
        summary = {
            'total_distributions': audit_service._count_distributions(start_date, end_date),
            'total_assignments': audit_service._count_assignments(start_date, end_date),
            'total_conflicts': audit_service._count_conflicts(start_date, end_date),
            'avg_success_rate': audit_service._calculate_avg_success_rate(start_date, end_date)
        }
        
        # Timeline de distribuições
        distribution_timeline = audit_service._get_distribution_timeline(start_date, end_date)
        
        # Distribuição por modo
        mode_distribution = audit_service._get_mode_distribution(start_date, end_date)
        
        # Performance dos revisores
        reviewer_performance = audit_service._get_reviewer_performance(start_date, end_date)
        
        # Histórico de distribuições
        distribution_history = audit_service._get_distribution_history(start_date, end_date)
        
        # Timeline de conflitos
        conflict_timeline = audit_service._get_conflict_timeline(start_date, end_date)
        
        # Timeline de importações
        import_timeline = audit_service._get_import_timeline(start_date, end_date)
        
        # Histórico de importações
        import_history = audit_service._get_import_history(start_date, end_date)
        
        return jsonify({
            'success': True,
            'summary': summary,
            'distribution_timeline': distribution_timeline,
            'mode_distribution': mode_distribution,
            'reviewer_performance': reviewer_performance,
            'distribution_history': distribution_history,
            'conflict_timeline': conflict_timeline,
            'import_timeline': import_timeline,
            'import_history': import_history
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao obter métricas: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@submission_distribution_routes.route('/api/distribution-details/<int:evento_id>/<int:distribution_id>')
@login_required
@admin_required
def get_distribution_details(evento_id, distribution_id):
    """API para obter detalhes de uma distribuição específica."""
    try:
        from services.audit_service import AuditService
        
        audit_service = AuditService(evento_id)
        distribution = audit_service._get_distribution_details(distribution_id)
        
        if not distribution:
            return jsonify({
                'success': False,
                'error': 'Distribuição não encontrada'
            }), 404
        
        return jsonify({
            'success': True,
            'distribution': distribution
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao obter detalhes da distribuição: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@submission_distribution_routes.route('/api/export/<int:evento_id>')
@login_required
@admin_required
def export_data(evento_id):
    """API para exportar dados em CSV."""
    try:
        from services.audit_service import AuditService
        from flask import Response
        
        export_type = request.args.get('type', 'distribution')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        audit_service = AuditService(evento_id)
        
        if export_type == 'reviewer_performance':
            csv_data = audit_service.export_audit_data_csv('reviewer_performance', start_date, end_date)
            filename = f'reviewer_performance_{evento_id}.csv'
        elif export_type == 'distribution':
            csv_data = audit_service.export_audit_data_csv('distribution', start_date, end_date)
            filename = f'distribution_audit_{evento_id}.csv'
        elif export_type == 'conflicts':
            csv_data = audit_service.export_audit_data_csv('conflicts', start_date, end_date)
            filename = f'conflicts_audit_{evento_id}.csv'
        elif export_type == 'imports':
            csv_data = audit_service.export_audit_data_csv('imports', start_date, end_date)
            filename = f'imports_audit_{evento_id}.csv'
        else:
            return jsonify({
                'success': False,
                'error': 'Tipo de exportação inválido'
            }), 400
        
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        current_app.logger.error(f"Erro ao exportar dados: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500