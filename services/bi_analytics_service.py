"""
Serviço de Business Intelligence e Análise de Dados
Fornece funcionalidades avançadas de análise, métricas e relatórios
"""

from extensions import db
from models import (
    Usuario, Evento, Oficina, Inscricao, Checkin, Cliente, 
    Pagamento, Feedback, AtividadeMultiplaData, FrequenciaAtividade
)
from models.relatorio_bi import (
    RelatorioBI, MetricaBI, DashboardBI, WidgetBI, 
    ExportacaoRelatorio, CacheRelatorio, AlertasBI
)
from sqlalchemy import func, text, and_, or_, desc, asc
from datetime import datetime, timedelta, date
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class BIAnalyticsService:
    """Serviço principal para análises de Business Intelligence"""
    
    def __init__(self):
        self.cache_duration = 3600  # 1 hora em segundos
    
    def calcular_kpis_executivos(self, cliente_id: int, filtros: Dict = None) -> Dict[str, Any]:
        """Calcula KPIs executivos principais"""
        try:
            # Verificar cache primeiro
            cache_key = f"kpis_executivos_{cliente_id}_{hashlib.md5(str(filtros).encode()).hexdigest()}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            # Aplicar filtros base
            query_base = self._aplicar_filtros_base(cliente_id, filtros)
            
            # KPIs principais
            kpis = {
                'inscricoes_totais': self._calcular_inscricoes_totais(query_base),
                'usuarios_unicos': self._calcular_usuarios_unicos(query_base),
                'taxa_conversao': self._calcular_taxa_conversao(query_base),
                'receita_total': self._calcular_receita_total(query_base),
                'ticket_medio': self._calcular_ticket_medio(query_base),
                'taxa_presenca': self._calcular_taxa_presenca(query_base),
                'satisfacao_media': self._calcular_satisfacao_media(query_base),
                'nps': self._calcular_nps(query_base),
                'crescimento_mensal': self._calcular_crescimento_mensal(query_base),
                'retencao_participantes': self._calcular_retencao_participantes(query_base)
            }
            
            # Salvar no cache
            self._set_cached_data(cache_key, kpis, 'kpis')
            
            return kpis
            
        except Exception as e:
            logger.error(f"Erro ao calcular KPIs executivos: {str(e)}")
            return {}
    
    def gerar_analise_tendencias(self, cliente_id: int, periodo_dias: int = 30) -> Dict[str, Any]:
        """Gera análise de tendências temporais"""
        try:
            data_fim = datetime.now()
            data_inicio = data_fim - timedelta(days=periodo_dias)
            
            # Dados por dia
            dados_diarios = self._obter_dados_diarios(cliente_id, data_inicio, data_fim)
            
            # Análise de tendências
            tendencias = {
                'inscricoes': self._analisar_tendencia(dados_diarios, 'inscricoes'),
                'presencas': self._analisar_tendencia(dados_diarios, 'presencas'),
                'receita': self._analisar_tendencia(dados_diarios, 'receita'),
                'satisfacao': self._analisar_tendencia(dados_diarios, 'satisfacao')
            }
            
            # Padrões identificados
            padroes = self._identificar_padroes(dados_diarios)
            
            return {
                'periodo': {
                    'inicio': data_inicio.isoformat(),
                    'fim': data_fim.isoformat(),
                    'dias': periodo_dias
                },
                'dados_diarios': dados_diarios,
                'tendencias': tendencias,
                'padroes': padroes,
                'resumo': self._gerar_resumo_tendencias(tendencias)
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar análise de tendências: {str(e)}")
            return {}
    
    def gerar_analise_geografica(self, cliente_id: int, filtros: Dict = None) -> Dict[str, Any]:
        """Gera análise geográfica detalhada"""
        try:
            # Dados por estado
            dados_estados = db.session.query(
                Oficina.estado,
                func.count(Inscricao.id).label('inscricoes'),
                func.count(Checkin.id).label('presencas'),
                func.sum(Pagamento.valor).label('receita')
            ).join(Inscricao, Oficina.id == Inscricao.oficina_id)\
             .outerjoin(Checkin, Checkin.inscricao_id == Inscricao.id)\
             .outerjoin(Pagamento, Pagamento.inscricao_id == Inscricao.id)\
             .filter(Oficina.cliente_id == cliente_id)\
             .group_by(Oficina.estado).all()
            
            # Dados por cidade
            dados_cidades = db.session.query(
                Oficina.cidade,
                Oficina.estado,
                func.count(Inscricao.id).label('inscricoes'),
                func.count(Checkin.id).label('presencas'),
                func.avg(Feedback.nota).label('satisfacao_media')
            ).join(Inscricao, Oficina.id == Inscricao.oficina_id)\
             .outerjoin(Checkin, Checkin.inscricao_id == Inscricao.id)\
             .outerjoin(Feedback, Feedback.oficina_id == Oficina.id)\
             .filter(Oficina.cliente_id == cliente_id)\
             .group_by(Oficina.cidade, Oficina.estado).all()
            
            # Rankings
            ranking_estados = sorted(dados_estados, key=lambda x: x.inscricoes, reverse=True)
            ranking_cidades = sorted(dados_cidades, key=lambda x: x.inscricoes, reverse=True)
            
            return {
                'estados': [{
                    'estado': item.estado,
                    'inscricoes': item.inscricoes,
                    'presencas': item.presencas,
                    'receita': float(item.receita or 0),
                    'taxa_presenca': (item.presencas / item.inscricoes * 100) if item.inscricoes > 0 else 0
                } for item in dados_estados],
                'cidades': [{
                    'cidade': item.cidade,
                    'estado': item.estado,
                    'inscricoes': item.inscricoes,
                    'presencas': item.presencas,
                    'satisfacao_media': float(item.satisfacao_media or 0),
                    'taxa_presenca': (item.presencas / item.inscricoes * 100) if item.inscricoes > 0 else 0
                } for item in dados_cidades],
                'rankings': {
                    'estados': ranking_estados[:10],
                    'cidades': ranking_cidades[:20]
                },
                'metricas_gerais': self._calcular_metricas_geograficas(dados_estados, dados_cidades)
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar análise geográfica: {str(e)}")
            return {}
    
    def gerar_analise_qualidade(self, cliente_id: int, filtros: Dict = None) -> Dict[str, Any]:
        """Gera análise de qualidade e satisfação"""
        try:
            # Dados de feedback
            feedbacks = db.session.query(
                Feedback.oficina_id,
                Oficina.titulo.label('oficina_titulo'),
                func.avg(Feedback.nota).label('nota_media'),
                func.count(Feedback.id).label('total_avaliacoes'),
                func.sum(case([(Feedback.nota >= 4, 1)], else_=0)).label('avaliacoes_positivas'),
                func.sum(case([(Feedback.nota <= 2, 1)], else_=0)).label('avaliacoes_negativas')
            ).join(Oficina, Feedback.oficina_id == Oficina.id)\
             .filter(Oficina.cliente_id == cliente_id)\
             .group_by(Feedback.oficina_id, Oficina.titulo).all()
            
            # Análise por categoria
            categorias = ['conteudo', 'logistica', 'estrutura', 'material', 'instrutor']
            feedback_por_categoria = {}
            
            for categoria in categorias:
                feedback_cat = db.session.query(
                    func.avg(getattr(Feedback, f'nota_{categoria}')).label('nota_media')
                ).join(Oficina, Feedback.oficina_id == Oficina.id)\
                 .filter(Oficina.cliente_id == cliente_id)\
                 .filter(getattr(Feedback, f'nota_{categoria}').isnot(None)).first()
                
                feedback_por_categoria[categoria] = float(feedback_cat.nota_media or 0)
            
            # NPS
            nps_data = self._calcular_nps_detalhado(cliente_id)
            
            # Comentários
            comentarios_positivos = db.session.query(Feedback.comentario)\
                .join(Oficina, Feedback.oficina_id == Oficina.id)\
                .filter(Oficina.cliente_id == cliente_id)\
                .filter(Feedback.nota >= 4)\
                .filter(Feedback.comentario.isnot(None))\
                .limit(50).all()
            
            comentarios_negativos = db.session.query(Feedback.comentario)\
                .join(Oficina, Feedback.oficina_id == Oficina.id)\
                .filter(Oficina.cliente_id == cliente_id)\
                .filter(Feedback.nota <= 2)\
                .filter(Feedback.comentario.isnot(None))\
                .limit(50).all()
            
            return {
                'resumo_geral': {
                    'nota_media_geral': sum([f.nota_media for f in feedbacks]) / len(feedbacks) if feedbacks else 0,
                    'total_avaliacoes': sum([f.total_avaliacoes for f in feedbacks]),
                    'nps': nps_data['nps'],
                    'promotores': nps_data['promotores'],
                    'neutros': nps_data['neutros'],
                    'detratores': nps_data['detratores']
                },
                'por_oficina': [{
                    'oficina_id': f.oficina_id,
                    'oficina_titulo': f.oficina_titulo,
                    'nota_media': float(f.nota_media or 0),
                    'total_avaliacoes': f.total_avaliacoes,
                    'avaliacoes_positivas': f.avaliacoes_positivas,
                    'avaliacoes_negativas': f.avaliacoes_negativas,
                    'taxa_positivas': (f.avaliacoes_positivas / f.total_avaliacoes * 100) if f.total_avaliacoes > 0 else 0
                } for f in feedbacks],
                'por_categoria': feedback_por_categoria,
                'comentarios': {
                    'positivos': [c.comentario for c in comentarios_positivos],
                    'negativos': [c.comentario for c in comentarios_negativos]
                },
                'tendencias_qualidade': self._analisar_tendencias_qualidade(cliente_id)
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar análise de qualidade: {str(e)}")
            return {}
    
    def gerar_analise_financeira(self, cliente_id: int, filtros: Dict = None) -> Dict[str, Any]:
        """Gera análise financeira detalhada"""
        try:
            # Receitas por período
            receitas_mensais = db.session.query(
                func.date_trunc('month', Pagamento.data_pagamento).label('mes'),
                func.sum(Pagamento.valor).label('receita'),
                func.count(Pagamento.id).label('transacoes')
            ).join(Inscricao, Pagamento.inscricao_id == Inscricao.id)\
             .join(Oficina, Inscricao.oficina_id == Oficina.id)\
             .filter(Oficina.cliente_id == cliente_id)\
             .filter(Pagamento.status == 'approved')\
             .group_by(func.date_trunc('month', Pagamento.data_pagamento))\
             .order_by(desc('mes')).all()
            
            # Análise de inadimplência
            inadimplencia = self._calcular_inadimplencia(cliente_id)
            
            # Análise de chargebacks
            chargebacks = self._calcular_chargebacks(cliente_id)
            
            # Ticket médio por categoria
            ticket_medio_categoria = db.session.query(
                Oficina.categoria,
                func.avg(Pagamento.valor).label('ticket_medio'),
                func.count(Pagamento.id).label('transacoes')
            ).join(Inscricao, Pagamento.inscricao_id == Inscricao.id)\
             .join(Oficina, Inscricao.oficina_id == Oficina.id)\
             .filter(Oficina.cliente_id == cliente_id)\
             .filter(Pagamento.status == 'approved')\
             .group_by(Oficina.categoria).all()
            
            # Projeções
            projecoes = self._gerar_projecoes_financeiras(receitas_mensais)
            
            return {
                'receitas_mensais': [{
                    'mes': r.mes.strftime('%Y-%m'),
                    'receita': float(r.receita or 0),
                    'transacoes': r.transacoes
                } for r in receitas_mensais],
                'resumo_financeiro': {
                    'receita_total': sum([float(r.receita or 0) for r in receitas_mensais]),
                    'transacoes_totais': sum([r.transacoes for r in receitas_mensais]),
                    'ticket_medio_geral': sum([float(r.receita or 0) for r in receitas_mensais]) / sum([r.transacoes for r in receitas_mensais]) if receitas_mensais else 0,
                    'crescimento_mensal': self._calcular_crescimento_receita(receitas_mensais)
                },
                'inadimplencia': inadimplencia,
                'chargebacks': chargebacks,
                'ticket_medio_categoria': [{
                    'categoria': t.categoria or 'Sem categoria',
                    'ticket_medio': float(t.ticket_medio or 0),
                    'transacoes': t.transacoes
                } for t in ticket_medio_categoria],
                'projecoes': projecoes,
                'metricas_risco': self._calcular_metricas_risco_financeiro(cliente_id)
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar análise financeira: {str(e)}")
            return {}
    
    def gerar_relatorio_personalizado(self, relatorio_id: int) -> Dict[str, Any]:
        """Gera relatório personalizado baseado em configuração"""
        try:
            relatorio = RelatorioBI.query.get_or_404(relatorio_id)
            filtros = relatorio.get_filtros_dict()
            
            # Executar queries baseadas no tipo de relatório
            if relatorio.tipo_relatorio == 'executivo':
                dados = self.calcular_kpis_executivos(relatorio.cliente_id, filtros)
            elif relatorio.tipo_relatorio == 'operacional':
                dados = self._gerar_analise_operacional(relatorio.cliente_id, filtros)
            elif relatorio.tipo_relatorio == 'financeiro':
                dados = self.gerar_analise_financeira(relatorio.cliente_id, filtros)
            elif relatorio.tipo_relatorio == 'qualidade':
                dados = self.gerar_analise_qualidade(relatorio.cliente_id, filtros)
            else:
                dados = {}
            
            # Atualizar relatório
            relatorio.set_dados_dict(dados)
            relatorio.ultima_execucao = datetime.utcnow()
            db.session.commit()
            
            return dados
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório personalizado: {str(e)}")
            return {}
    
    def criar_dashboard_personalizado(self, nome: str, cliente_id: int, usuario_id: int, 
                                    widgets: List[Dict], layout: Dict) -> DashboardBI:
        """Cria dashboard personalizado"""
        try:
            dashboard = DashboardBI(
                nome=nome,
                cliente_id=cliente_id,
                usuario_criador_id=usuario_id
            )
            
            dashboard.set_widgets_dict(widgets)
            dashboard.set_layout_dict(layout)
            
            db.session.add(dashboard)
            db.session.commit()
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Erro ao criar dashboard personalizado: {str(e)}")
            raise
    
    def executar_alertas_bi(self) -> List[Dict[str, Any]]:
        """Executa verificação de alertas de BI"""
        try:
            alertas_disparados = []
            alertas = AlertasBI.query.filter_by(ativo=True).all()
            
            for alerta in alertas:
                if self._verificar_alerta(alerta):
                    alertas_disparados.append({
                        'alerta_id': alerta.id,
                        'nome': alerta.nome,
                        'descricao': alerta.descricao,
                        'tipo': alerta.tipo_alerta,
                        'valor_atual': self._obter_valor_metrica(alerta.metrica_id),
                        'valor_limite': alerta.valor_limite,
                        'usuarios': alerta.get_usuarios_notificar(),
                        'canais': alerta.get_canais_notificacao()
                    })
                    
                    # Atualizar último disparo
                    alerta.ultimo_disparo = datetime.utcnow()
            
            db.session.commit()
            return alertas_disparados
            
        except Exception as e:
            logger.error(f"Erro ao executar alertas BI: {str(e)}")
            return []
    
    # Métodos auxiliares privados
    
    def _aplicar_filtros_base(self, cliente_id: int, filtros: Dict = None) -> Dict[str, Any]:
        """Aplica filtros base nas consultas"""
        if not filtros:
            return {'cliente_id': cliente_id}
        
        filtros['cliente_id'] = cliente_id
        return filtros
    
    def _calcular_inscricoes_totais(self, query_base: Dict) -> int:
        """Calcula total de inscrições"""
        query = Inscricao.query.join(Oficina, Inscricao.oficina_id == Oficina.id)\
            .filter(Oficina.cliente_id == query_base['cliente_id'])
        
        if 'data_inicio' in query_base:
            query = query.filter(Inscricao.created_at >= query_base['data_inicio'])
        if 'data_fim' in query_base:
            query = query.filter(Inscricao.created_at <= query_base['data_fim'])
        
        return query.count()
    
    def _calcular_usuarios_unicos(self, query_base: Dict) -> int:
        """Calcula usuários únicos"""
        query = Inscricao.query.join(Oficina, Inscricao.oficina_id == Oficina.id)\
            .filter(Oficina.cliente_id == query_base['cliente_id'])
        
        if 'data_inicio' in query_base:
            query = query.filter(Inscricao.created_at >= query_base['data_inicio'])
        if 'data_fim' in query_base:
            query = query.filter(Inscricao.created_at <= query_base['data_fim'])
        
        return query.with_entities(Inscricao.usuario_id).distinct().count()
    
    def _calcular_taxa_conversao(self, query_base: Dict) -> float:
        """Calcula taxa de conversão"""
        inscricoes = self._calcular_inscricoes_totais(query_base)
        confirmados = Inscricao.query.join(Oficina, Inscricao.oficina_id == Oficina.id)\
            .filter(Oficina.cliente_id == query_base['cliente_id'])\
            .filter(Inscricao.status_pagamento == 'approved').count()
        
        return (confirmados / inscricoes * 100) if inscricoes > 0 else 0
    
    def _calcular_receita_total(self, query_base: Dict) -> float:
        """Calcula receita total"""
        query = Pagamento.query.join(Inscricao, Pagamento.inscricao_id == Inscricao.id)\
            .join(Oficina, Inscricao.oficina_id == Oficina.id)\
            .filter(Oficina.cliente_id == query_base['cliente_id'])\
            .filter(Pagamento.status == 'approved')
        
        if 'data_inicio' in query_base:
            query = query.filter(Pagamento.data_pagamento >= query_base['data_inicio'])
        if 'data_fim' in query_base:
            query = query.filter(Pagamento.data_pagamento <= query_base['data_fim'])
        
        return float(query.with_entities(func.sum(Pagamento.valor)).scalar() or 0)
    
    def _calcular_ticket_medio(self, query_base: Dict) -> float:
        """Calcula ticket médio"""
        receita = self._calcular_receita_total(query_base)
        transacoes = Pagamento.query.join(Inscricao, Pagamento.inscricao_id == Inscricao.id)\
            .join(Oficina, Inscricao.oficina_id == Oficina.id)\
            .filter(Oficina.cliente_id == query_base['cliente_id'])\
            .filter(Pagamento.status == 'approved').count()
        
        return receita / transacoes if transacoes > 0 else 0
    
    def _calcular_taxa_presenca(self, query_base: Dict) -> float:
        """Calcula taxa de presença"""
        inscricoes = self._calcular_inscricoes_totais(query_base)
        presencas = Checkin.query.join(Inscricao, Checkin.inscricao_id == Inscricao.id)\
            .join(Oficina, Inscricao.oficina_id == Oficina.id)\
            .filter(Oficina.cliente_id == query_base['cliente_id']).count()
        
        return (presencas / inscricoes * 100) if inscricoes > 0 else 0
    
    def _calcular_satisfacao_media(self, query_base: Dict) -> float:
        """Calcula satisfação média"""
        query = Feedback.query.join(Oficina, Feedback.oficina_id == Oficina.id)\
            .filter(Oficina.cliente_id == query_base['cliente_id'])
        
        if 'data_inicio' in query_base:
            query = query.filter(Feedback.created_at >= query_base['data_inicio'])
        if 'data_fim' in query_base:
            query = query.filter(Feedback.created_at <= query_base['data_fim'])
        
        return float(query.with_entities(func.avg(Feedback.nota)).scalar() or 0)
    
    def _calcular_nps(self, query_base: Dict) -> int:
        """Calcula NPS"""
        nps_data = self._calcular_nps_detalhado(query_base['cliente_id'])
        return nps_data['nps']
    
    def _calcular_nps_detalhado(self, cliente_id: int) -> Dict[str, int]:
        """Calcula NPS detalhado"""
        feedbacks = Feedback.query.join(Oficina, Feedback.oficina_id == Oficina.id)\
            .filter(Oficina.cliente_id == cliente_id)\
            .filter(Feedback.nota.isnot(None)).all()
        
        promotores = sum(1 for f in feedbacks if f.nota >= 9)
        neutros = sum(1 for f in feedbacks if 7 <= f.nota <= 8)
        detratores = sum(1 for f in feedbacks if f.nota <= 6)
        total = len(feedbacks)
        
        if total == 0:
            return {'nps': 0, 'promotores': 0, 'neutros': 0, 'detratores': 0}
        
        nps = ((promotores - detratores) / total) * 100
        return {
            'nps': int(nps),
            'promotores': promotores,
            'neutros': neutros,
            'detratores': detratores
        }
    
    def _calcular_crescimento_mensal(self, query_base: Dict) -> float:
        """Calcula crescimento mensal"""
        # Implementar cálculo de crescimento
        return 0.0
    
    def _calcular_retencao_participantes(self, query_base: Dict) -> float:
        """Calcula retenção de participantes"""
        # Implementar cálculo de retenção
        return 0.0
    
    def _obter_dados_diarios(self, cliente_id: int, data_inicio: datetime, data_fim: datetime) -> List[Dict]:
        """Obtém dados diários para análise de tendências"""
        # Implementar consulta de dados diários
        return []
    
    def _analisar_tendencia(self, dados: List[Dict], metrica: str) -> Dict[str, Any]:
        """Analisa tendência de uma métrica"""
        # Implementar análise de tendência
        return {'direcao': 'estavel', 'magnitude': 0, 'confianca': 0}
    
    def _identificar_padroes(self, dados: List[Dict]) -> List[Dict]:
        """Identifica padrões nos dados"""
        # Implementar identificação de padrões
        return []
    
    def _gerar_resumo_tendencias(self, tendencias: Dict) -> Dict[str, Any]:
        """Gera resumo das tendências"""
        return {'resumo': 'Análise de tendências em desenvolvimento'}
    
    def _calcular_metricas_geograficas(self, dados_estados: List, dados_cidades: List) -> Dict[str, Any]:
        """Calcula métricas geográficas gerais"""
        return {'total_estados': len(dados_estados), 'total_cidades': len(dados_cidades)}
    
    def _calcular_inadimplencia(self, cliente_id: int) -> Dict[str, Any]:
        """Calcula métricas de inadimplência"""
        return {'taxa': 0, 'valor': 0, 'transacoes': 0}
    
    def _calcular_chargebacks(self, cliente_id: int) -> Dict[str, Any]:
        """Calcula métricas de chargebacks"""
        return {'taxa': 0, 'valor': 0, 'transacoes': 0}
    
    def _gerar_projecoes_financeiras(self, receitas_mensais: List) -> Dict[str, Any]:
        """Gera projeções financeiras"""
        return {'proximo_mes': 0, 'proximos_3_meses': 0, 'proximos_6_meses': 0}
    
    def _calcular_crescimento_receita(self, receitas_mensais: List) -> float:
        """Calcula crescimento da receita"""
        if len(receitas_mensais) < 2:
            return 0.0
        
        receita_atual = float(receitas_mensais[0].receita or 0)
        receita_anterior = float(receitas_mensais[1].receita or 0)
        
        return ((receita_atual - receita_anterior) / receita_anterior * 100) if receita_anterior > 0 else 0
    
    def _calcular_metricas_risco_financeiro(self, cliente_id: int) -> Dict[str, Any]:
        """Calcula métricas de risco financeiro"""
        return {'risco_baixo': True, 'indicadores': []}
    
    def _gerar_analise_operacional(self, cliente_id: int, filtros: Dict) -> Dict[str, Any]:
        """Gera análise operacional"""
        return {'operacional': 'Análise operacional em desenvolvimento'}
    
    def _analisar_tendencias_qualidade(self, cliente_id: int) -> Dict[str, Any]:
        """Analisa tendências de qualidade"""
        return {'tendencias': 'Análise de tendências de qualidade em desenvolvimento'}
    
    def _verificar_alerta(self, alerta: AlertasBI) -> bool:
        """Verifica se alerta deve ser disparado"""
        valor_atual = self._obter_valor_metrica(alerta.metrica_id)
        
        if alerta.condicao == 'maior':
            return valor_atual > alerta.valor_limite
        elif alerta.condicao == 'menor':
            return valor_atual < alerta.valor_limite
        elif alerta.condicao == 'igual':
            return valor_atual == alerta.valor_limite
        elif alerta.condicao == 'diferente':
            return valor_atual != alerta.valor_limite
        
        return False
    
    def _obter_valor_metrica(self, metrica_id: int) -> float:
        """Obtém valor atual de uma métrica"""
        metrica = MetricaBI.query.get(metrica_id)
        if not metrica or not metrica.formula:
            return 0.0
        
        # Executar query SQL da métrica
        try:
            resultado = db.session.execute(text(metrica.formula)).scalar()
            return float(resultado or 0)
        except Exception:
            return 0.0
    
    def _get_cached_data(self, cache_key: str) -> Optional[Dict]:
        """Obtém dados do cache"""
        cache = CacheRelatorio.query.filter_by(chave_cache=cache_key).first()
        if cache and not cache.is_expired():
            cache.hits += 1
            db.session.commit()
            return cache.get_dados_dict()
        return None
    
    def _set_cached_data(self, cache_key: str, dados: Dict, tipo_dados: str) -> None:
        """Salva dados no cache"""
        try:
            # Remover cache expirado
            CacheRelatorio.query.filter(CacheRelatorio.data_expiracao < datetime.utcnow()).delete()
            
            # Criar novo cache
            cache = CacheRelatorio(
                chave_cache=cache_key,
                dados_cache=json.dumps(dados),
                tipo_dados=tipo_dados,
                filtros_hash=hashlib.md5(cache_key.encode()).hexdigest(),
                data_expiracao=datetime.utcnow() + timedelta(seconds=self.cache_duration)
            )
            
            db.session.add(cache)
            db.session.commit()
        except Exception as e:
            logger.error(f"Erro ao salvar cache: {str(e)}")
            db.session.rollback()
