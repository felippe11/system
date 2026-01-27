"""
Configuração para o sistema de Business Intelligence
Registra as rotas e configurações do módulo de BI
"""

from flask import Flask
from routes.relatorio_bi_routes import relatorio_bi_routes

def register_bi_routes(app: Flask):
    """Registra as rotas de Business Intelligence no Flask"""
    app.register_blueprint(relatorio_bi_routes, url_prefix='/bi')

def get_bi_config():
    """Retorna configurações específicas do módulo de BI"""
    return {
        'cache_duration': 3600,  # 1 hora em segundos
        'max_export_size': 50 * 1024 * 1024,  # 50MB
        'supported_formats': ['pdf', 'xlsx', 'csv', 'json'],
        'auto_refresh_interval': 30000,  # 30 segundos
        'max_dashboards_per_user': 10,
        'max_reports_per_user': 50,
        'default_metrics': [
            {
                'nome': 'Inscrições Totais',
                'categoria': 'participacao',
                'tipo_metrica': 'contador',
                'cor': '#007bff',
                'icone': 'fas fa-users',
                'unidade': 'unidades'
            },
            {
                'nome': 'Taxa de Conversão',
                'categoria': 'participacao',
                'tipo_metrica': 'percentual',
                'cor': '#28a745',
                'icone': 'fas fa-percentage',
                'unidade': '%'
            },
            {
                'nome': 'Receita Total',
                'categoria': 'financeiro',
                'tipo_metrica': 'monetario',
                'cor': '#ffc107',
                'icone': 'fas fa-dollar-sign',
                'unidade': 'R$'
            },
            {
                'nome': 'Satisfação Média',
                'categoria': 'qualidade',
                'tipo_metrica': 'decimal',
                'cor': '#17a2b8',
                'icone': 'fas fa-star',
                'unidade': '/5.0'
            }
        ],
        'chart_colors': [
            '#007bff', '#28a745', '#ffc107', '#dc3545', '#17a2b8',
            '#6f42c1', '#fd7e14', '#20c997', '#e83e8c', '#6c757d'
        ],
        'widget_types': [
            'grafico_linha',
            'grafico_barras',
            'grafico_pizza',
            'grafico_donut',
            'kpi_card',
            'tabela',
            'mapa',
            'calendario',
            'gauge',
            'treemap'
        ],
        'report_types': [
            {
                'id': 'executivo',
                'nome': 'Executivo',
                'descricao': 'Relatório para tomada de decisão estratégica',
                'icon': 'fas fa-chart-line'
            },
            {
                'id': 'operacional',
                'nome': 'Operacional',
                'descricao': 'Relatório para análise operacional',
                'icon': 'fas fa-cogs'
            },
            {
                'id': 'financeiro',
                'nome': 'Financeiro',
                'descricao': 'Relatório para análise financeira',
                'icon': 'fas fa-dollar-sign'
            },
            {
                'id': 'qualidade',
                'nome': 'Qualidade',
                'descricao': 'Relatório para análise de qualidade',
                'icon': 'fas fa-star'
            }
        ]
    }

def init_bi_metrics():
    """Inicializa métricas padrão do sistema de BI"""
    from models.relatorio_bi import MetricaBI
    from extensions import db
    
    config = get_bi_config()
    
    for metrica_data in config['default_metrics']:
        # Verificar se a métrica já existe
        existing = MetricaBI.query.filter_by(nome=metrica_data['nome']).first()
        if not existing:
            metrica = MetricaBI(
                nome=metrica_data['nome'],
                categoria=metrica_data['categoria'],
                tipo_metrica=metrica_data['tipo_metrica'],
                cor=metrica_data['cor'],
                icone=metrica_data['icone'],
                unidade=metrica_data['unidade'],
                ativo=True
            )
            db.session.add(metrica)
    
    try:
        db.session.commit()
        print("Métricas de BI inicializadas com sucesso!")
    except Exception as e:
        print(f"Erro ao inicializar métricas de BI: {str(e)}")
        db.session.rollback()

def create_sample_dashboard(cliente_id: int, usuario_id: int):
    """Cria um dashboard de exemplo para demonstração"""
    from models.relatorio_bi import DashboardBI, WidgetBI
    from extensions import db
    import json
    
    # Criar dashboard
    dashboard = DashboardBI(
        nome="Dashboard Executivo",
        descricao="Dashboard com os principais indicadores executivos",
        cliente_id=cliente_id,
        usuario_criador_id=usuario_id,
        publico=False
    )
    
    # Configurar layout
    layout_config = {
        'rows': [
            {
                'id': 'row1',
                'columns': [
                    {'id': 'col1', 'width': 3, 'widgets': ['kpi1', 'kpi2']},
                    {'id': 'col2', 'width': 3, 'widgets': ['kpi3', 'kpi4']},
                    {'id': 'col3', 'width': 6, 'widgets': ['chart1']}
                ]
            },
            {
                'id': 'row2',
                'columns': [
                    {'id': 'col4', 'width': 8, 'widgets': ['chart2']},
                    {'id': 'col5', 'width': 4, 'widgets': ['table1']}
                ]
            }
        ]
    }
    
    # Configurar widgets
    widgets_config = {
        'kpi1': {
            'tipo': 'kpi_card',
            'titulo': 'Inscrições Totais',
            'metrica': 'inscricoes_totais',
            'cor': '#007bff'
        },
        'kpi2': {
            'tipo': 'kpi_card',
            'titulo': 'Taxa de Conversão',
            'metrica': 'taxa_conversao',
            'cor': '#28a745'
        },
        'kpi3': {
            'tipo': 'kpi_card',
            'titulo': 'Receita Total',
            'metrica': 'receita_total',
            'cor': '#ffc107'
        },
        'kpi4': {
            'tipo': 'kpi_card',
            'titulo': 'Satisfação Média',
            'metrica': 'satisfacao_media',
            'cor': '#17a2b8'
        },
        'chart1': {
            'tipo': 'grafico_linha',
            'titulo': 'Tendências Mensais',
            'dados': 'tendencias_mensais'
        },
        'chart2': {
            'tipo': 'grafico_barras',
            'titulo': 'Comparação por Categoria',
            'dados': 'comparacao_categoria'
        },
        'table1': {
            'tipo': 'tabela',
            'titulo': 'Top 5 Oficinas',
            'dados': 'top_oficinas'
        }
    }
    
    dashboard.set_layout_dict(layout_config)
    dashboard.set_widgets_dict(widgets_config)
    
    db.session.add(dashboard)
    
    try:
        db.session.commit()
        print(f"Dashboard de exemplo criado para cliente {cliente_id}")
        return dashboard
    except Exception as e:
        print(f"Erro ao criar dashboard de exemplo: {str(e)}")
        db.session.rollback()
        return None

def get_bi_menu_items():
    """Retorna itens de menu para o sistema de BI"""
    return [
        {
            'title': 'Dashboard BI',
            'url': '/bi/dashboard',
            'icon': 'fas fa-chart-line',
            'description': 'Visão geral e indicadores principais'
        },
        {
            'title': 'Relatórios',
            'url': '/bi/relatorios',
            'icon': 'fas fa-file-alt',
            'description': 'Relatórios personalizados e exportações'
        },
        {
            'title': 'Dashboards',
            'url': '/bi/dashboards',
            'icon': 'fas fa-th-large',
            'description': 'Dashboards personalizados'
        },
        {
            'title': 'Análise de Tendências',
            'url': '/bi/analises/tendencias',
            'icon': 'fas fa-chart-line',
            'description': 'Análise temporal de dados'
        },
        {
            'title': 'Análise Geográfica',
            'url': '/bi/analises/geografia',
            'icon': 'fas fa-map-marked-alt',
            'description': 'Análise por localização'
        },
        {
            'title': 'Análise de Qualidade',
            'url': '/bi/analises/qualidade',
            'icon': 'fas fa-star',
            'description': 'Análise de satisfação e qualidade'
        },
        {
            'title': 'Análise Financeira',
            'url': '/bi/analises/financeira',
            'icon': 'fas fa-dollar-sign',
            'description': 'Análise financeira detalhada'
        }
    ]
