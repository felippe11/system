#!/usr/bin/env python3
"""
Script para inicializar o sistema de Business Intelligence
Cria métricas padrão, dashboards de exemplo e configurações iniciais
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.relatorio_bi import MetricaBI, DashboardBI, WidgetBI
from config.relatorio_bi_config import init_bi_metrics, create_sample_dashboard, get_bi_config
from models import Cliente, Usuario

def main():
    """Função principal de inicialização"""
    print("🚀 Inicializando sistema de Business Intelligence...")
    
    # Criar aplicação Flask
    app = create_app()
    
    with app.app_context():
        try:
            # 1. Inicializar métricas padrão
            print("📊 Criando métricas padrão...")
            init_bi_metrics()
            
            # 2. Criar dashboards de exemplo para clientes existentes
            print("📈 Criando dashboards de exemplo...")
            clientes = Cliente.query.all()
            
            for cliente in clientes:
                # Buscar usuário admin do cliente
                usuario_admin = Usuario.query.filter_by(
                    cliente_id=cliente.id,
                    tipo='admin'
                ).first()
                
                if usuario_admin:
                    dashboard = create_sample_dashboard(cliente.id, usuario_admin.id)
                    if dashboard:
                        print(f"   ✅ Dashboard criado para cliente: {cliente.nome}")
                else:
                    print(f"   ⚠️  Nenhum usuário admin encontrado para cliente: {cliente.nome}")
            
            # 3. Criar widgets padrão
            print("🎛️  Criando widgets padrão...")
            criar_widgets_padrao()
            
            # 4. Configurar alertas padrão
            print("🔔 Configurando alertas padrão...")
            configurar_alertas_padrao()
            
            print("✅ Sistema de BI inicializado com sucesso!")
            print("\n📋 Próximos passos:")
            print("   1. Acesse /bi/dashboard para ver o dashboard principal")
            print("   2. Crie relatórios personalizados em /bi/relatorios")
            print("   3. Configure dashboards personalizados em /bi/dashboards")
            print("   4. Explore as análises específicas em /bi/analises")
            
        except Exception as e:
            print(f"❌ Erro ao inicializar sistema de BI: {str(e)}")
            db.session.rollback()
            return False
    
    return True

def criar_widgets_padrao():
    """Cria widgets padrão do sistema"""
    widgets_padrao = [
        {
            'nome': 'KPI Card - Inscrições',
            'tipo_widget': 'kpi_card',
            'configuracao': {
                'titulo': 'Inscrições Totais',
                'metrica': 'inscricoes_totais',
                'cor': '#007bff',
                'icone': 'fas fa-users'
            },
            'largura': 3,
            'altura': 200
        },
        {
            'nome': 'Gráfico de Linha - Tendências',
            'tipo_widget': 'grafico_linha',
            'configuracao': {
                'titulo': 'Tendências Mensais',
                'dados': 'tendencias_mensais',
                'cor': '#28a745'
            },
            'largura': 6,
            'altura': 300
        },
        {
            'nome': 'Gráfico de Pizza - Distribuição',
            'tipo_widget': 'grafico_pizza',
            'configuracao': {
                'titulo': 'Distribuição por Categoria',
                'dados': 'distribuicao_categoria',
                'cores': ['#007bff', '#28a745', '#ffc107', '#dc3545']
            },
            'largura': 4,
            'altura': 300
        },
        {
            'nome': 'Tabela - Top Oficinas',
            'tipo_widget': 'tabela',
            'configuracao': {
                'titulo': 'Top 10 Oficinas',
                'dados': 'top_oficinas',
                'colunas': ['Nome', 'Inscrições', 'Presenças', 'Satisfação']
            },
            'largura': 8,
            'altura': 400
        },
        {
            'nome': 'Gauge - Taxa de Conversão',
            'tipo_widget': 'gauge',
            'configuracao': {
                'titulo': 'Taxa de Conversão',
                'metrica': 'taxa_conversao',
                'min': 0,
                'max': 100,
                'cor': '#28a745'
            },
            'largura': 4,
            'altura': 250
        }
    ]
    
    for widget_data in widgets_padrao:
        # Verificar se widget já existe
        existing = WidgetBI.query.filter_by(nome=widget_data['nome']).first()
        if not existing:
            widget = WidgetBI(
                nome=widget_data['nome'],
                tipo_widget=widget_data['tipo_widget'],
                configuracao=json.dumps(widget_data['configuracao']),
                largura=widget_data['largura'],
                altura=widget_data['altura'],
                ativo=True
            )
            db.session.add(widget)
    
    try:
        db.session.commit()
        print("   ✅ Widgets padrão criados com sucesso!")
    except Exception as e:
        print(f"   ❌ Erro ao criar widgets: {str(e)}")
        db.session.rollback()

def configurar_alertas_padrao():
    """Configura alertas padrão do sistema"""
    from models.relatorio_bi import AlertasBI
    
    alertas_padrao = [
        {
            'nome': 'Taxa de Conversão Baixa',
            'descricao': 'Alerta quando a taxa de conversão estiver abaixo de 50%',
            'tipo_alerta': 'limite',
            'metrica_nome': 'Taxa de Conversão',
            'condicao': 'menor',
            'valor_limite': 50.0,
            'periodo_verificacao': 24
        },
        {
            'nome': 'Satisfação Crítica',
            'descricao': 'Alerta quando a satisfação média estiver abaixo de 3.0',
            'tipo_alerta': 'limite',
            'metrica_nome': 'Satisfação Média',
            'condicao': 'menor',
            'valor_limite': 3.0,
            'periodo_verificacao': 12
        },
        {
            'nome': 'Receita Alta',
            'descricao': 'Alerta quando a receita ultrapassar R$ 100.000',
            'tipo_alerta': 'limite',
            'metrica_nome': 'Receita Total',
            'condicao': 'maior',
            'valor_limite': 100000.0,
            'periodo_verificacao': 24
        }
    ]
    
    for alerta_data in alertas_padrao:
        # Buscar métrica correspondente
        metrica = MetricaBI.query.filter_by(nome=alerta_data['metrica_nome']).first()
        if metrica:
            # Verificar se alerta já existe
            existing = AlertasBI.query.filter_by(nome=alerta_data['nome']).first()
            if not existing:
                alerta = AlertasBI(
                    nome=alerta_data['nome'],
                    descricao=alerta_data['descricao'],
                    tipo_alerta=alerta_data['tipo_alerta'],
                    metrica_id=metrica.id,
                    condicao=alerta_data['condicao'],
                    valor_limite=alerta_data['valor_limite'],
                    periodo_verificacao=alerta_data['periodo_verificacao'],
                    ativo=True
                )
                db.session.add(alerta)
    
    try:
        db.session.commit()
        print("   ✅ Alertas padrão configurados com sucesso!")
    except Exception as e:
        print(f"   ❌ Erro ao configurar alertas: {str(e)}")
        db.session.rollback()

def verificar_dependencias():
    """Verifica se todas as dependências estão instaladas"""
    print("🔍 Verificando dependências...")
    
    dependencias = [
        'reportlab',
        'openpyxl',
        'pandas',
        'chart.js',
        'leaflet',
        'fullcalendar',
        'datatables',
        'select2'
    ]
    
    dependencias_ok = True
    
    for dep in dependencias:
        try:
            if dep in ['reportlab', 'openpyxl', 'pandas']:
                __import__(dep)
            print(f"   ✅ {dep}")
        except ImportError:
            print(f"   ❌ {dep} - NÃO INSTALADO")
            dependencias_ok = False
    
    if not dependencias_ok:
        print("\n⚠️  Algumas dependências não estão instaladas.")
        print("   Execute: pip install reportlab openpyxl pandas")
        return False
    
    print("   ✅ Todas as dependências estão instaladas!")
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("🎯 INICIALIZADOR DO SISTEMA DE BUSINESS INTELLIGENCE")
    print("=" * 60)
    
    # Verificar dependências
    if not verificar_dependencias():
        sys.exit(1)
    
    # Inicializar sistema
    if main():
        print("\n🎉 Inicialização concluída com sucesso!")
        sys.exit(0)
    else:
        print("\n💥 Falha na inicialização!")
        sys.exit(1)
