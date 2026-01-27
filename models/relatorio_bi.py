from extensions import db
from datetime import datetime, date
from sqlalchemy.orm import relationship
from sqlalchemy import func, text
import json

class RelatorioBI(db.Model):
    """Modelo para armazenar relatórios de BI gerados"""
    __tablename__ = 'relatorio_bi'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    tipo_relatorio = db.Column(db.String(50), nullable=False)  # 'executivo', 'operacional', 'financeiro', 'qualidade'
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    usuario_criador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
    # Configurações do relatório
    filtros_aplicados = db.Column(db.Text, nullable=True)  # JSON com filtros
    periodo_inicio = db.Column(db.Date, nullable=True)
    periodo_fim = db.Column(db.Date, nullable=True)
    
    # Dados do relatório
    dados_relatorio = db.Column(db.Text, nullable=True)  # JSON com dados
    metricas_calculadas = db.Column(db.Text, nullable=True)  # JSON com métricas
    
    # Metadados
    status = db.Column(db.String(20), default='ativo')  # 'ativo', 'arquivado', 'excluido'
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ultima_execucao = db.Column(db.DateTime, nullable=True)
    
    # Relacionamentos
    cliente = relationship("Cliente", backref="relatorios_bi")
    usuario_criador = relationship("Usuario", backref="relatorios_criados")
    
    def __repr__(self):
        return f"<RelatorioBI {self.nome}>"
    
    def get_filtros_dict(self):
        """Retorna filtros como dicionário Python"""
        if self.filtros_aplicados:
            return json.loads(self.filtros_aplicados)
        return {}
    
    def set_filtros_dict(self, filtros):
        """Define filtros a partir de dicionário Python"""
        self.filtros_aplicados = json.dumps(filtros)
    
    def get_dados_dict(self):
        """Retorna dados como dicionário Python"""
        if self.dados_relatorio:
            return json.loads(self.dados_relatorio)
        return {}
    
    def set_dados_dict(self, dados):
        """Define dados a partir de dicionário Python"""
        self.dados_relatorio = json.dumps(dados)
    
    def get_metricas_dict(self):
        """Retorna métricas como dicionário Python"""
        if self.metricas_calculadas:
            return json.loads(self.metricas_calculadas)
        return {}
    
    def set_metricas_dict(self, metricas):
        """Define métricas a partir de dicionário Python"""
        self.metricas_calculadas = json.dumps(metricas)

class MetricaBI(db.Model):
    """Modelo para métricas de BI calculadas"""
    __tablename__ = 'metrica_bi'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    categoria = db.Column(db.String(50), nullable=False)  # 'vendas', 'participacao', 'qualidade', 'financeiro'
    tipo_metrica = db.Column(db.String(30), nullable=False)  # 'contador', 'percentual', 'monetario', 'tempo'
    formula = db.Column(db.Text, nullable=True)  # SQL ou descrição da fórmula
    
    # Configurações de exibição
    cor = db.Column(db.String(7), default='#3498db')  # Cor hex
    icone = db.Column(db.String(50), default='fas fa-chart-line')
    unidade = db.Column(db.String(20), nullable=True)  # '%', 'R$', 'pessoas', etc.
    
    # Metadados
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<MetricaBI {self.nome}>"

class DashboardBI(db.Model):
    """Modelo para dashboards de BI personalizados"""
    __tablename__ = 'dashboard_bi'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    usuario_criador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
    # Configuração do dashboard
    layout_config = db.Column(db.Text, nullable=True)  # JSON com layout
    widgets_config = db.Column(db.Text, nullable=True)  # JSON com widgets
    filtros_padrao = db.Column(db.Text, nullable=True)  # JSON com filtros padrão
    
    # Configurações de acesso
    publico = db.Column(db.Boolean, default=False)
    usuarios_permitidos = db.Column(db.Text, nullable=True)  # JSON com IDs de usuários
    
    # Metadados
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    cliente = relationship("Cliente", backref="dashboards_bi")
    usuario_criador = relationship("Usuario", backref="dashboards_criados")
    
    def __repr__(self):
        return f"<DashboardBI {self.nome}>"
    
    def get_layout_dict(self):
        """Retorna layout como dicionário Python"""
        if self.layout_config:
            return json.loads(self.layout_config)
        return {}
    
    def set_layout_dict(self, layout):
        """Define layout a partir de dicionário Python"""
        self.layout_config = json.dumps(layout)
    
    def get_widgets_dict(self):
        """Retorna widgets como dicionário Python"""
        if self.widgets_config:
            return json.loads(self.widgets_config)
        return {}
    
    def set_widgets_dict(self, widgets):
        """Define widgets a partir de dicionário Python"""
        self.widgets_config = json.dumps(widgets)

class WidgetBI(db.Model):
    """Modelo para widgets de BI"""
    __tablename__ = 'widget_bi'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    tipo_widget = db.Column(db.String(50), nullable=False)  # 'grafico', 'tabela', 'kpi', 'mapa', 'calendario'
    configuracao = db.Column(db.Text, nullable=True)  # JSON com configuração
    
    # Dados do widget
    query_sql = db.Column(db.Text, nullable=True)
    metrica_id = db.Column(db.Integer, db.ForeignKey('metrica_bi.id'), nullable=True)
    
    # Configurações de exibição
    largura = db.Column(db.Integer, default=4)  # Colunas (1-12)
    altura = db.Column(db.Integer, default=300)  # Pixels
    posicao_x = db.Column(db.Integer, default=0)
    posicao_y = db.Column(db.Integer, default=0)
    
    # Metadados
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    metrica = relationship("MetricaBI", backref="widgets")
    
    def __repr__(self):
        return f"<WidgetBI {self.nome}>"
    
    def get_config_dict(self):
        """Retorna configuração como dicionário Python"""
        if self.configuracao:
            return json.loads(self.configuracao)
        return {}
    
    def set_config_dict(self, config):
        """Define configuração a partir de dicionário Python"""
        self.configuracao = json.dumps(config)

class ExportacaoRelatorio(db.Model):
    """Modelo para controle de exportações de relatórios"""
    __tablename__ = 'exportacao_relatorio'

    id = db.Column(db.Integer, primary_key=True)
    relatorio_id = db.Column(db.Integer, db.ForeignKey('relatorio_bi.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
    # Configurações da exportação
    formato = db.Column(db.String(10), nullable=False)  # 'pdf', 'xlsx', 'csv', 'json'
    filtros_aplicados = db.Column(db.Text, nullable=True)  # JSON com filtros
    configuracao_export = db.Column(db.Text, nullable=True)  # JSON com configurações
    
    # Status da exportação
    status = db.Column(db.String(20), default='processando')  # 'processando', 'concluido', 'erro'
    arquivo_path = db.Column(db.String(500), nullable=True)
    tamanho_arquivo = db.Column(db.Integer, nullable=True)
    mensagem_erro = db.Column(db.Text, nullable=True)
    
    # Metadados
    data_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    data_conclusao = db.Column(db.DateTime, nullable=True)
    tempo_processamento = db.Column(db.Integer, nullable=True)  # Segundos
    
    # Relacionamentos
    relatorio = relationship("RelatorioBI", backref="exportacoes")
    usuario = relationship("Usuario", backref="exportacoes_relatorios")
    
    def __repr__(self):
        return f"<ExportacaoRelatorio {self.formato} - {self.status}>"
    
    def get_filtros_dict(self):
        """Retorna filtros como dicionário Python"""
        if self.filtros_aplicados:
            return json.loads(self.filtros_aplicados)
        return {}
    
    def set_filtros_dict(self, filtros):
        """Define filtros a partir de dicionário Python"""
        self.filtros_aplicados = json.dumps(filtros)

class CacheRelatorio(db.Model):
    """Modelo para cache de dados de relatórios"""
    __tablename__ = 'cache_relatorio'

    id = db.Column(db.Integer, primary_key=True)
    chave_cache = db.Column(db.String(255), unique=True, nullable=False)
    dados_cache = db.Column(db.Text, nullable=False)  # JSON com dados em cache
    
    # Metadados do cache
    tipo_dados = db.Column(db.String(50), nullable=False)  # 'kpis', 'graficos', 'tabelas'
    filtros_hash = db.Column(db.String(64), nullable=False)  # Hash dos filtros aplicados
    
    # Controle de expiração
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_expiracao = db.Column(db.DateTime, nullable=False)
    hits = db.Column(db.Integer, default=0)  # Quantas vezes foi acessado
    
    def __repr__(self):
        return f"<CacheRelatorio {self.chave_cache}>"
    
    def is_expired(self):
        """Verifica se o cache expirou"""
        return datetime.utcnow() > self.data_expiracao
    
    def get_dados_dict(self):
        """Retorna dados como dicionário Python"""
        return json.loads(self.dados_cache)
    
    def set_dados_dict(self, dados):
        """Define dados a partir de dicionário Python"""
        self.dados_cache = json.dumps(dados)

class AlertasBI(db.Model):
    """Modelo para alertas e notificações de BI"""
    __tablename__ = 'alertas_bi'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    tipo_alerta = db.Column(db.String(50), nullable=False)  # 'limite', 'tendencia', 'anomalia', 'meta'
    
    # Configuração do alerta
    metrica_id = db.Column(db.Integer, db.ForeignKey('metrica_bi.id'), nullable=False)
    condicao = db.Column(db.String(20), nullable=False)  # 'maior', 'menor', 'igual', 'diferente'
    valor_limite = db.Column(db.Float, nullable=False)
    periodo_verificacao = db.Column(db.Integer, default=24)  # Horas
    
    # Configurações de notificação
    usuarios_notificar = db.Column(db.Text, nullable=True)  # JSON com IDs de usuários
    canais_notificacao = db.Column(db.Text, nullable=True)  # JSON com canais: 'email', 'dashboard', 'webhook'
    
    # Status
    ativo = db.Column(db.Boolean, default=True)
    ultima_verificacao = db.Column(db.DateTime, nullable=True)
    ultimo_disparo = db.Column(db.DateTime, nullable=True)
    
    # Metadados
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    metrica = relationship("MetricaBI", backref="alertas")
    
    def __repr__(self):
        return f"<AlertasBI {self.nome}>"
    
    def get_usuarios_notificar(self):
        """Retorna usuários como lista Python"""
        if self.usuarios_notificar:
            return json.loads(self.usuarios_notificar)
        return []
    
    def set_usuarios_notificar(self, usuarios):
        """Define usuários a partir de lista Python"""
        self.usuarios_notificar = json.dumps(usuarios)
    
    def get_canais_notificacao(self):
        """Retorna canais como lista Python"""
        if self.canais_notificacao:
            return json.loads(self.canais_notificacao)
        return []
    
    def set_canais_notificacao(self, canais):
        """Define canais a partir de lista Python"""
        self.canais_notificacao = json.dumps(canais)
