"""
Rotas para Business Intelligence e Relatórios Avançados
Fornece endpoints para dashboards, relatórios personalizados e exportações
"""

from flask import Blueprint, render_template, request, jsonify, send_file, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Any

from extensions import db
from models.relatorio_bi import (
    RelatorioBI, MetricaBI, DashboardBI, WidgetBI, 
    ExportacaoRelatorio, CacheRelatorio, AlertasBI
)
from services.bi_analytics_service import BIAnalyticsService
from services.relatorio_export_service import RelatorioExportService
from utils.auth import dashboard_access_required

relatorio_bi_routes = Blueprint("relatorio_bi_routes", __name__)

# Inicializar serviços
bi_service = BIAnalyticsService()
export_service = RelatorioExportService()

@relatorio_bi_routes.route('/bi/dashboard')
@login_required
@dashboard_access_required
def dashboard_bi():
    """Dashboard principal de Business Intelligence"""
    try:
        # Verificar se usuário é admin ou cliente
        is_admin = current_user.tipo == 'admin'
        cliente_id = current_user.id if not is_admin else None
        
        # Obter KPIs executivos
        kpis = bi_service.calcular_kpis_executivos(
            cliente_id or 1,  # Admin vê todos os dados
            request.args.to_dict()
        )
        
        # Obter dashboards personalizados do usuário
        dashboards = DashboardBI.query.filter_by(
            cliente_id=current_user.id if not is_admin else 1,
            ativo=True
        ).all()
        
        # Obter alertas ativos
        alertas = AlertasBI.query.filter_by(ativo=True).all()
        
        # Obter métricas disponíveis
        metricas = MetricaBI.query.filter_by(ativo=True).all()
        
        return render_template(
            'relatorio_bi/dashboard_principal.html',
            kpis=kpis,
            dashboards=dashboards,
            alertas=alertas,
            metricas=metricas,
            is_admin=is_admin
        )
        
    except Exception as e:
        flash(f'Erro ao carregar dashboard: {str(e)}', 'error')
        return redirect(url_for('relatorio_routes.gerar_relatorio_evento'))

@relatorio_bi_routes.route('/bi/relatorios')
@login_required
@dashboard_access_required
def lista_relatorios():
    """Lista todos os relatórios de BI"""
    try:
        is_admin = current_user.tipo == 'admin'
        cliente_id = current_user.id if not is_admin else None
        
        # Obter relatórios
        query = RelatorioBI.query
        if not is_admin:
            query = query.filter_by(cliente_id=cliente_id)
        
        relatorios = query.order_by(desc(RelatorioBI.data_criacao)).all()
        
        # Obter tipos de relatório disponíveis
        tipos_relatorio = ['executivo', 'operacional', 'financeiro', 'qualidade']
        
        return render_template(
            'relatorio_bi/lista_relatorios.html',
            relatorios=relatorios,
            tipos_relatorio=tipos_relatorio,
            is_admin=is_admin
        )
        
    except Exception as e:
        flash(f'Erro ao carregar relatórios: {str(e)}', 'error')
        return redirect(url_for('relatorio_bi_routes.dashboard_bi'))

@relatorio_bi_routes.route('/bi/relatorios/novo', methods=['GET', 'POST'])
@login_required
@dashboard_access_required
def criar_relatorio():
    """Cria novo relatório de BI"""
    if request.method == 'POST':
        try:
            # Obter dados do formulário
            nome = request.form.get('nome')
            descricao = request.form.get('descricao')
            tipo_relatorio = request.form.get('tipo_relatorio')
            periodo_inicio = request.form.get('periodo_inicio')
            periodo_fim = request.form.get('periodo_fim')
            
            # Criar relatório
            relatorio = RelatorioBI(
                nome=nome,
                descricao=descricao,
                tipo_relatorio=tipo_relatorio,
                cliente_id=current_user.id,
                usuario_criador_id=current_user.id,
                periodo_inicio=datetime.strptime(periodo_inicio, '%Y-%m-%d').date() if periodo_inicio else None,
                periodo_fim=datetime.strptime(periodo_fim, '%Y-%m-%d').date() if periodo_fim else None
            )
            
            # Aplicar filtros
            filtros = {
                'data_inicio': periodo_inicio,
                'data_fim': periodo_fim,
                'evento_id': request.form.get('evento_id'),
                'oficina_id': request.form.get('oficina_id'),
                'estado': request.form.get('estado'),
                'cidade': request.form.get('cidade')
            }
            
            # Remover valores vazios
            filtros = {k: v for k, v in filtros.items() if v}
            relatorio.set_filtros_dict(filtros)
            
            db.session.add(relatorio)
            db.session.commit()
            
            flash('Relatório criado com sucesso!', 'success')
            return redirect(url_for('relatorio_bi_routes.visualizar_relatorio', id=relatorio.id))
            
        except Exception as e:
            flash(f'Erro ao criar relatório: {str(e)}', 'error')
            db.session.rollback()
    
    # Obter dados para formulário
    from models import Evento, Oficina
    eventos = Evento.query.filter_by(cliente_id=current_user.id).all()
    oficinas = Oficina.query.filter_by(cliente_id=current_user.id).all()
    
    return render_template(
        'relatorio_bi/criar_relatorio.html',
        eventos=eventos,
        oficinas=oficinas
    )

@relatorio_bi_routes.route('/bi/relatorios/<int:id>')
@login_required
@dashboard_access_required
def visualizar_relatorio(id):
    """Visualiza relatório específico"""
    try:
        relatorio = RelatorioBI.query.get_or_404(id)
        
        # Verificar permissão
        if current_user.tipo != 'admin' and relatorio.cliente_id != current_user.id:
            flash('Acesso negado', 'error')
            return redirect(url_for('relatorio_bi_routes.lista_relatorios'))
        
        # Gerar dados do relatório
        dados = bi_service.gerar_relatorio_personalizado(id)
        
        # Obter histórico de exportações
        historico_exportacoes = export_service.obter_historico_exportacoes(relatorio_id=id)
        
        return render_template(
            'relatorio_bi/visualizar_relatorio.html',
            relatorio=relatorio,
            dados=dados,
            historico_exportacoes=historico_exportacoes
        )
        
    except Exception as e:
        flash(f'Erro ao visualizar relatório: {str(e)}', 'error')
        return redirect(url_for('relatorio_bi_routes.lista_relatorios'))

@relatorio_bi_routes.route('/bi/relatorios/<int:id>/exportar', methods=['POST'])
@login_required
@dashboard_access_required
def exportar_relatorio(id):
    """Exporta relatório em formato específico"""
    try:
        relatorio = RelatorioBI.query.get_or_404(id)
        
        # Verificar permissão
        if current_user.tipo != 'admin' and relatorio.cliente_id != current_user.id:
            return jsonify({'error': 'Acesso negado'}), 403
        
        formato = request.json.get('formato', 'pdf')
        configuracao = request.json.get('configuracao', {})
        
        # Exportar relatório
        if formato == 'pdf':
            filepath = export_service.exportar_relatorio_pdf(id, configuracao)
        elif formato == 'xlsx':
            filepath = export_service.exportar_relatorio_xlsx(id, configuracao)
        elif formato == 'csv':
            filepath = export_service.exportar_relatorio_csv(id, configuracao)
        elif formato == 'json':
            filepath = export_service.exportar_relatorio_json(id, configuracao)
        else:
            return jsonify({'error': 'Formato não suportado'}), 400
        
        return jsonify({
            'success': True,
            'filepath': filepath,
            'filename': os.path.basename(filepath)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@relatorio_bi_routes.route('/bi/relatorios/<int:id>/download/<path:filename>')
@login_required
@dashboard_access_required
def download_relatorio(id, filename):
    """Download de arquivo de relatório exportado"""
    try:
        relatorio = RelatorioBI.query.get_or_404(id)
        
        # Verificar permissão
        if current_user.tipo != 'admin' and relatorio.cliente_id != current_user.id:
            flash('Acesso negado', 'error')
            return redirect(url_for('relatorio_bi_routes.lista_relatorios'))
        
        # Buscar exportação
        exportacao = ExportacaoRelatorio.query.filter_by(
            relatorio_id=id,
            arquivo_path=os.path.join('uploads/relatorios', filename)
        ).first()
        
        if not exportacao or not os.path.exists(exportacao.arquivo_path):
            flash('Arquivo não encontrado', 'error')
            return redirect(url_for('relatorio_bi_routes.visualizar_relatorio', id=id))
        
        return send_file(
            exportacao.arquivo_path,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Erro ao fazer download: {str(e)}', 'error')
        return redirect(url_for('relatorio_bi_routes.visualizar_relatorio', id=id))

@relatorio_bi_routes.route('/bi/analises/tendencias')
@login_required
@dashboard_access_required
def analise_tendencias():
    """Análise de tendências temporais"""
    try:
        periodo_dias = request.args.get('periodo', 30, type=int)
        cliente_id = current_user.id if current_user.tipo != 'admin' else 1
        
        # Gerar análise de tendências
        dados = bi_service.gerar_analise_tendencias(cliente_id, periodo_dias)
        
        return render_template(
            'relatorio_bi/analise_tendencias.html',
            dados=dados,
            periodo_dias=periodo_dias
        )
        
    except Exception as e:
        flash(f'Erro ao gerar análise de tendências: {str(e)}', 'error')
        return redirect(url_for('relatorio_bi_routes.dashboard_bi'))

@relatorio_bi_routes.route('/bi/analises/geografia')
@login_required
@dashboard_access_required
def analise_geografica():
    """Análise geográfica detalhada"""
    try:
        cliente_id = current_user.id if current_user.tipo != 'admin' else 1
        filtros = request.args.to_dict()
        
        # Gerar análise geográfica
        dados = bi_service.gerar_analise_geografica(cliente_id, filtros)
        
        return render_template(
            'relatorio_bi/analise_geografica.html',
            dados=dados
        )
        
    except Exception as e:
        flash(f'Erro ao gerar análise geográfica: {str(e)}', 'error')
        return redirect(url_for('relatorio_bi_routes.dashboard_bi'))

@relatorio_bi_routes.route('/bi/analises/qualidade')
@login_required
@dashboard_access_required
def analise_qualidade():
    """Análise de qualidade e satisfação"""
    try:
        cliente_id = current_user.id if current_user.tipo != 'admin' else 1
        filtros = request.args.to_dict()
        
        # Gerar análise de qualidade
        dados = bi_service.gerar_analise_qualidade(cliente_id, filtros)
        
        return render_template(
            'relatorio_bi/analise_qualidade.html',
            dados=dados
        )
        
    except Exception as e:
        flash(f'Erro ao gerar análise de qualidade: {str(e)}', 'error')
        return redirect(url_for('relatorio_bi_routes.dashboard_bi'))

@relatorio_bi_routes.route('/bi/analises/financeira')
@login_required
@dashboard_access_required
def analise_financeira():
    """Análise financeira detalhada"""
    try:
        cliente_id = current_user.id if current_user.tipo != 'admin' else 1
        filtros = request.args.to_dict()
        
        # Gerar análise financeira
        dados = bi_service.gerar_analise_financeira(cliente_id, filtros)
        
        return render_template(
            'relatorio_bi/analise_financeira.html',
            dados=dados
        )
        
    except Exception as e:
        flash(f'Erro ao gerar análise financeira: {str(e)}', 'error')
        return redirect(url_for('relatorio_bi_routes.dashboard_bi'))

@relatorio_bi_routes.route('/bi/dashboards')
@login_required
@dashboard_access_required
def lista_dashboards():
    """Lista dashboards personalizados"""
    try:
        is_admin = current_user.tipo == 'admin'
        cliente_id = current_user.id if not is_admin else None
        
        # Obter dashboards
        query = DashboardBI.query
        if not is_admin:
            query = query.filter_by(cliente_id=cliente_id)
        
        dashboards = query.filter_by(ativo=True).order_by(desc(DashboardBI.data_criacao)).all()
        
        return render_template(
            'relatorio_bi/lista_dashboards.html',
            dashboards=dashboards,
            is_admin=is_admin
        )
        
    except Exception as e:
        flash(f'Erro ao carregar dashboards: {str(e)}', 'error')
        return redirect(url_for('relatorio_bi_routes.dashboard_bi'))

@relatorio_bi_routes.route('/bi/dashboards/novo', methods=['GET', 'POST'])
@login_required
@dashboard_access_required
def criar_dashboard():
    """Cria novo dashboard personalizado"""
    if request.method == 'POST':
        try:
            # Obter dados do formulário
            nome = request.form.get('nome')
            descricao = request.form.get('descricao')
            widgets_json = request.form.get('widgets')
            layout_json = request.form.get('layout')
            
            # Criar dashboard
            dashboard = DashboardBI(
                nome=nome,
                descricao=descricao,
                cliente_id=current_user.id,
                usuario_criador_id=current_user.id
            )
            
            # Configurar widgets e layout
            if widgets_json:
                dashboard.set_widgets_dict(json.loads(widgets_json))
            if layout_json:
                dashboard.set_layout_dict(json.loads(layout_json))
            
            db.session.add(dashboard)
            db.session.commit()
            
            flash('Dashboard criado com sucesso!', 'success')
            return redirect(url_for('relatorio_bi_routes.visualizar_dashboard', id=dashboard.id))
            
        except Exception as e:
            flash(f'Erro ao criar dashboard: {str(e)}', 'error')
            db.session.rollback()
    
    # Obter widgets disponíveis
    widgets = WidgetBI.query.filter_by(ativo=True).all()
    metricas = MetricaBI.query.filter_by(ativo=True).all()
    
    return render_template(
        'relatorio_bi/criar_dashboard.html',
        widgets=widgets,
        metricas=metricas
    )

@relatorio_bi_routes.route('/bi/dashboards/<int:id>')
@login_required
@dashboard_access_required
def visualizar_dashboard(id):
    """Visualiza dashboard específico"""
    try:
        dashboard = DashboardBI.query.get_or_404(id)
        
        # Verificar permissão
        if current_user.tipo != 'admin' and dashboard.cliente_id != current_user.id:
            flash('Acesso negado', 'error')
            return redirect(url_for('relatorio_bi_routes.lista_dashboards'))
        
        # Obter widgets do dashboard
        widgets_config = dashboard.get_widgets_dict()
        layout_config = dashboard.get_layout_dict()
        
        return render_template(
            'relatorio_bi/visualizar_dashboard.html',
            dashboard=dashboard,
            widgets_config=widgets_config,
            layout_config=layout_config
        )
        
    except Exception as e:
        flash(f'Erro ao visualizar dashboard: {str(e)}', 'error')
        return redirect(url_for('relatorio_bi_routes.lista_dashboards'))

@relatorio_bi_routes.route('/bi/dashboards/<int:id>/exportar', methods=['POST'])
@login_required
@dashboard_access_required
def exportar_dashboard(id):
    """Exporta dashboard para PDF"""
    try:
        dashboard = DashboardBI.query.get_or_404(id)
        
        # Verificar permissão
        if current_user.tipo != 'admin' and dashboard.cliente_id != current_user.id:
            return jsonify({'error': 'Acesso negado'}), 403
        
        # Exportar dashboard
        filepath = export_service.exportar_dashboard_pdf(id, request.json)
        
        return jsonify({
            'success': True,
            'filepath': filepath,
            'filename': os.path.basename(filepath)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# APIs para dados dinâmicos

@relatorio_bi_routes.route('/api/bi/kpis')
@login_required
@dashboard_access_required
def api_kpis():
    """API para obter KPIs em tempo real"""
    try:
        cliente_id = current_user.id if current_user.tipo != 'admin' else 1
        filtros = request.args.to_dict()
        
        kpis = bi_service.calcular_kpis_executivos(cliente_id, filtros)
        
        return jsonify({
            'success': True,
            'kpis': kpis,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@relatorio_bi_routes.route('/api/bi/tendencias')
@login_required
@dashboard_access_required
def api_tendencias():
    """API para obter dados de tendências"""
    try:
        cliente_id = current_user.id if current_user.tipo != 'admin' else 1
        periodo_dias = request.args.get('periodo', 30, type=int)
        
        dados = bi_service.gerar_analise_tendencias(cliente_id, periodo_dias)
        
        return jsonify({
            'success': True,
            'dados': dados,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@relatorio_bi_routes.route('/api/bi/alertas')
@login_required
@dashboard_access_required
def api_alertas():
    """API para obter alertas ativos"""
    try:
        # Executar verificação de alertas
        alertas_disparados = bi_service.executar_alertas_bi()
        
        return jsonify({
            'success': True,
            'alertas': alertas_disparados,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@relatorio_bi_routes.route('/api/bi/metricas')
@login_required
@dashboard_access_required
def api_metricas():
    """API para obter métricas disponíveis"""
    try:
        metricas = MetricaBI.query.filter_by(ativo=True).all()
        
        return jsonify({
            'success': True,
            'metricas': [{
                'id': m.id,
                'nome': m.nome,
                'descricao': m.descricao,
                'categoria': m.categoria,
                'tipo': m.tipo_metrica,
                'cor': m.cor,
                'icone': m.icone,
                'unidade': m.unidade
            } for m in metricas]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@relatorio_bi_routes.route('/api/bi/widgets')
@login_required
@dashboard_access_required
def api_widgets():
    """API para obter widgets disponíveis"""
    try:
        widgets = WidgetBI.query.filter_by(ativo=True).all()
        
        return jsonify({
            'success': True,
            'widgets': [{
                'id': w.id,
                'nome': w.nome,
                'tipo': w.tipo_widget,
                'configuracao': w.get_config_dict(),
                'largura': w.largura,
                'altura': w.altura
            } for w in widgets]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Rotas de manutenção

@relatorio_bi_routes.route('/bi/manutencao/limpar-cache')
@login_required
@dashboard_access_required
def limpar_cache():
    """Limpa cache de relatórios"""
    try:
        # Remover cache expirado
        cache_expirado = CacheRelatorio.query.filter(
            CacheRelatorio.data_expiracao < datetime.utcnow()
        ).delete()
        
        db.session.commit()
        
        flash(f'Cache limpo: {cache_expirado} registros removidos', 'success')
        return redirect(url_for('relatorio_bi_routes.dashboard_bi'))
        
    except Exception as e:
        flash(f'Erro ao limpar cache: {str(e)}', 'error')
        return redirect(url_for('relatorio_bi_routes.dashboard_bi'))

@relatorio_bi_routes.route('/bi/manutencao/limpar-arquivos')
@login_required
@dashboard_access_required
def limpar_arquivos():
    """Limpa arquivos de exportação antigos"""
    try:
        export_service.limpar_arquivos_antigos()
        flash('Arquivos antigos removidos com sucesso', 'success')
        return redirect(url_for('relatorio_bi_routes.dashboard_bi'))
        
    except Exception as e:
        flash(f'Erro ao limpar arquivos: {str(e)}', 'error')
        return redirect(url_for('relatorio_bi_routes.dashboard_bi'))
