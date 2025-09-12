# -*- coding: utf-8 -*-
from datetime import datetime
from extensions import db


class TrilhaFormativa(db.Model):
    """Modelo para trilhas formativas configuráveis pelo cliente"""
    __tablename__ = "trilha_formativa"
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relacionamentos
    cliente = db.relationship("Cliente", backref="trilhas_formativas")
    campos = db.relationship("CampoTrilhaFormativa", backref="trilha", cascade="all, delete-orphan")
    respostas = db.relationship("RespostaTrilhaFormativa", backref="trilha", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TrilhaFormativa {self.nome}>"


class CampoTrilhaFormativa(db.Model):
    """Campos configuráveis para as trilhas formativas"""
    __tablename__ = "campo_trilha_formativa"
    
    id = db.Column(db.Integer, primary_key=True)
    trilha_id = db.Column(db.Integer, db.ForeignKey("trilha_formativa.id"), nullable=False)
    nome = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # texto, numero, data, select, checkbox, textarea
    obrigatorio = db.Column(db.Boolean, default=False)
    opcoes = db.Column(db.Text, nullable=True)  # Para campos select (JSON)
    ordem = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f"<CampoTrilhaFormativa {self.nome}>"


class RespostaTrilhaFormativa(db.Model):
    """Respostas dos formadores às trilhas formativas"""
    __tablename__ = "resposta_trilha_formativa"
    
    id = db.Column(db.Integer, primary_key=True)
    trilha_id = db.Column(db.Integer, db.ForeignKey("trilha_formativa.id"), nullable=False)
    formador_id = db.Column(db.Integer, db.ForeignKey("ministrante.id"), nullable=False)
    respostas = db.Column(db.JSON, nullable=False)  # Armazena as respostas em formato JSON
    data_envio = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relacionamentos
    formador = db.relationship("Ministrante", backref="respostas_trilhas")
    
    def __repr__(self):
        return f"<RespostaTrilhaFormativa {self.formador.nome} - {self.trilha.nome}>"


class SolicitacaoMaterial(db.Model):
    """Solicitações de material pelos formadores"""
    __tablename__ = "solicitacao_material"
    
    id = db.Column(db.Integer, primary_key=True)
    formador_id = db.Column(db.Integer, db.ForeignKey("ministrante.id"), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    atividade_id = db.Column(db.Integer, db.ForeignKey("oficina.id"), nullable=True)  # Pode ser geral
    
    tipo_solicitacao = db.Column(db.String(20), nullable=False)  # 'atividade' ou 'geral'
    tipo_material = db.Column(db.String(255), nullable=False)
    unidade_medida = db.Column(db.String(50), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    justificativa = db.Column(db.Text, nullable=False)
    
    status = db.Column(db.String(20), default='pendente')  # pendente, aprovado, rejeitado, parcial
    observacoes_cliente = db.Column(db.Text, nullable=True)
    quantidade_aprovada = db.Column(db.Integer, nullable=True)
    
    data_solicitacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_resposta = db.Column(db.DateTime, nullable=True)
    
    # Relacionamentos
    formador = db.relationship("Ministrante", backref="solicitacoes_material")
    cliente = db.relationship("Cliente", backref="solicitacoes_material")
    atividade = db.relationship("Oficina", backref="solicitacoes_material")
    
    def __repr__(self):
        return f"<SolicitacaoMaterial {self.tipo_material} - {self.formador.nome}>"


class MaterialAprovado(db.Model):
    """Materiais aprovados pelo cliente para entrega pelo monitor"""
    __tablename__ = "material_aprovado"
    
    id = db.Column(db.Integer, primary_key=True)
    solicitacao_id = db.Column(db.Integer, db.ForeignKey("solicitacao_material.id"), nullable=False)
    monitor_id = db.Column(db.Integer, db.ForeignKey("monitor.id"), nullable=True)
    
    quantidade_para_entrega = db.Column(db.Integer, nullable=False)
    entregue = db.Column(db.Boolean, default=False)
    data_entrega = db.Column(db.DateTime, nullable=True)
    observacoes_entrega = db.Column(db.Text, nullable=True)
    
    # Relacionamentos
    solicitacao = db.relationship("SolicitacaoMaterial", backref="materiais_aprovados")
    monitor = db.relationship("Monitor", backref="materiais_para_entrega")
    
    def __repr__(self):
        return f"<MaterialAprovado {self.solicitacao.tipo_material}>"


class ConfiguracaoRelatorioFormador(db.Model):
    """Configuração de relatórios para formadores"""
    __tablename__ = "configuracao_relatorio_formador"
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    nome = db.Column(db.String(255), nullable=False)
    tipo_periodo = db.Column(db.String(20), nullable=False)  # atividade, mensal, trimestral, anual
    campos_relatorio = db.Column(db.JSON, nullable=False)  # Campos configuráveis
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relacionamentos
    cliente = db.relationship("Cliente", backref="configuracoes_relatorio_formador")
    
    def __repr__(self):
        return f"<ConfiguracaoRelatorioFormador {self.nome}>"


class RelatorioFormador(db.Model):
    """Relatórios enviados pelos formadores"""
    __tablename__ = "relatorio_formador"
    
    id = db.Column(db.Integer, primary_key=True)
    configuracao_id = db.Column(db.Integer, db.ForeignKey("configuracao_relatorio_formador.id"), nullable=False)
    formador_id = db.Column(db.Integer, db.ForeignKey("ministrante.id"), nullable=False)
    atividade_id = db.Column(db.Integer, db.ForeignKey("oficina.id"), nullable=True)  # Para relatórios por atividade
    
    periodo_inicio = db.Column(db.Date, nullable=True)
    periodo_fim = db.Column(db.Date, nullable=True)
    dados_relatorio = db.Column(db.JSON, nullable=False)
    
    data_envio = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relacionamentos
    configuracao = db.relationship("ConfiguracaoRelatorioFormador", backref="relatorios")
    formador = db.relationship("Ministrante", backref="relatorios")
    atividade = db.relationship("Oficina", backref="relatorios_formador")
    
    def __repr__(self):
        return f"<RelatorioFormador {self.formador.nome} - {self.configuracao.nome}>"


class ArquivoFormador(db.Model):
    """Arquivos que o formador pode fazer upload"""
    __tablename__ = "arquivo_formador"
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    formador_id = db.Column(db.Integer, db.ForeignKey("ministrante.id"), nullable=False)
    
    nome_arquivo = db.Column(db.String(255), nullable=False)
    nome_original = db.Column(db.String(255), nullable=False)
    caminho_arquivo = db.Column(db.String(500), nullable=False)
    frequencia_reenvio = db.Column(db.String(50), nullable=True)  # semanal, mensal, trimestral, etc.
    
    data_upload = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    proximo_reenvio = db.Column(db.DateTime, nullable=True)
    
    # Relacionamentos
    cliente = db.relationship("Cliente", backref="arquivos_formador")
    formador = db.relationship("Ministrante", backref="arquivos_enviados")
    
    def __repr__(self):
        return f"<ArquivoFormador {self.nome_arquivo}>"


class FormadorMonitor(db.Model):
    """Associação entre formador e monitor"""
    __tablename__ = "formador_monitor"
    
    id = db.Column(db.Integer, primary_key=True)
    formador_id = db.Column(db.Integer, db.ForeignKey("ministrante.id"), nullable=False)
    monitor_id = db.Column(db.Integer, db.ForeignKey("monitor.id"), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    
    data_associacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)
    
    # Relacionamentos
    formador = db.relationship("Ministrante", backref="monitor_associado")
    monitor = db.relationship("Monitor", backref="formadores_associados")
    cliente = db.relationship("Cliente", backref="associacoes_formador_monitor")
    
    def __repr__(self):
        return f"<FormadorMonitor {self.formador.nome} - {self.monitor.nome_completo}>"