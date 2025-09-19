from datetime import datetime
from extensions import db
from models.orcamento import Orcamento, HistoricoOrcamento
from models.user import Usuario
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)


class HistoricoOrcamentoService:
    """Serviço para gerenciar histórico de alterações orçamentárias."""
    
    @staticmethod
    def registrar_criacao(orcamento, motivo=None, observacoes=None):
        """Registra a criação de um novo orçamento."""
        try:
            historico = HistoricoOrcamento(
                orcamento_id=orcamento.id,
                usuario_id=current_user.id if current_user.is_authenticated else None,
                tipo_alteracao='criacao',
                valor_total_novo=orcamento.valor_total,
                valor_custeio_novo=orcamento.valor_custeio,
                valor_capital_novo=orcamento.valor_capital,
                motivo=motivo or 'Criação do orçamento',
                observacoes=observacoes
            )
            
            db.session.add(historico)
            db.session.commit()
            
            logger.info(f"Histórico de criação registrado para orçamento {orcamento.id}")
            return historico
            
        except Exception as e:
            logger.error(f"Erro ao registrar criação do orçamento: {str(e)}")
            db.session.rollback()
            raise
    
    @staticmethod
    def registrar_edicao(orcamento, valores_anteriores, motivo=None, observacoes=None):
        """Registra a edição de um orçamento."""
        try:
            historico = HistoricoOrcamento(
                orcamento_id=orcamento.id,
                usuario_id=current_user.id if current_user.is_authenticated else None,
                tipo_alteracao='edicao',
                valor_total_anterior=valores_anteriores.get('valor_total'),
                valor_custeio_anterior=valores_anteriores.get('valor_custeio'),
                valor_capital_anterior=valores_anteriores.get('valor_capital'),
                valor_total_novo=orcamento.valor_total,
                valor_custeio_novo=orcamento.valor_custeio,
                valor_capital_novo=orcamento.valor_capital,
                motivo=motivo or 'Edição do orçamento',
                observacoes=observacoes
            )
            
            db.session.add(historico)
            db.session.commit()
            
            logger.info(f"Histórico de edição registrado para orçamento {orcamento.id}")
            return historico
            
        except Exception as e:
            logger.error(f"Erro ao registrar edição do orçamento: {str(e)}")
            db.session.rollback()
            raise
    
    @staticmethod
    def registrar_ativacao_desativacao(orcamento, ativo, motivo=None, observacoes=None):
        """Registra a ativação ou desativação de um orçamento."""
        try:
            tipo_alteracao = 'ativacao' if ativo else 'desativacao'
            
            historico = HistoricoOrcamento(
                orcamento_id=orcamento.id,
                usuario_id=current_user.id if current_user.is_authenticated else None,
                tipo_alteracao=tipo_alteracao,
                valor_total_novo=orcamento.valor_total,
                valor_custeio_novo=orcamento.valor_custeio,
                valor_capital_novo=orcamento.valor_capital,
                motivo=motivo or f'{"Ativação" if ativo else "Desativação"} do orçamento',
                observacoes=observacoes
            )
            
            db.session.add(historico)
            db.session.commit()
            
            logger.info(f"Histórico de {tipo_alteracao} registrado para orçamento {orcamento.id}")
            return historico
            
        except Exception as e:
            logger.error(f"Erro ao registrar {tipo_alteracao} do orçamento: {str(e)}")
            db.session.rollback()
            raise
    
    @staticmethod
    def obter_historico_orcamento(orcamento_id, limite=50):
        """Obtém o histórico de alterações de um orçamento específico."""
        try:
            historico = HistoricoOrcamento.query.filter_by(
                orcamento_id=orcamento_id
            ).order_by(HistoricoOrcamento.data_alteracao.desc()).limit(limite).all()
            
            return [h.to_dict() for h in historico]
            
        except Exception as e:
            logger.error(f"Erro ao obter histórico do orçamento {orcamento_id}: {str(e)}")
            return []
    
    @staticmethod
    def obter_historico_polo(polo_id, limite=100):
        """Obtém o histórico de alterações de todos os orçamentos de um polo."""
        try:
            historico = db.session.query(HistoricoOrcamento).join(
                Orcamento, HistoricoOrcamento.orcamento_id == Orcamento.id
            ).filter(
                Orcamento.polo_id == polo_id
            ).order_by(HistoricoOrcamento.data_alteracao.desc()).limit(limite).all()
            
            return [h.to_dict() for h in historico]
            
        except Exception as e:
            logger.error(f"Erro ao obter histórico do polo {polo_id}: {str(e)}")
            return []
    
    @staticmethod
    def obter_historico_geral(data_inicio=None, data_fim=None, tipo_alteracao=None, limite=200):
        """Obtém o histórico geral de alterações orçamentárias."""
        try:
            query = HistoricoOrcamento.query
            
            if data_inicio:
                query = query.filter(HistoricoOrcamento.data_alteracao >= data_inicio)
            
            if data_fim:
                query = query.filter(HistoricoOrcamento.data_alteracao <= data_fim)
            
            if tipo_alteracao:
                query = query.filter(HistoricoOrcamento.tipo_alteracao == tipo_alteracao)
            
            historico = query.order_by(
                HistoricoOrcamento.data_alteracao.desc()
            ).limit(limite).all()
            
            return [h.to_dict() for h in historico]
            
        except Exception as e:
            logger.error(f"Erro ao obter histórico geral: {str(e)}")
            return []
    
    @staticmethod
    def obter_estatisticas_alteracoes(data_inicio=None, data_fim=None):
        """Obtém estatísticas sobre as alterações orçamentárias."""
        try:
            query = HistoricoOrcamento.query
            
            if data_inicio:
                query = query.filter(HistoricoOrcamento.data_alteracao >= data_inicio)
            
            if data_fim:
                query = query.filter(HistoricoOrcamento.data_alteracao <= data_fim)
            
            # Contar por tipo de alteração
            tipos_alteracao = db.session.query(
                HistoricoOrcamento.tipo_alteracao,
                db.func.count(HistoricoOrcamento.id).label('total')
            ).filter(
                HistoricoOrcamento.data_alteracao >= data_inicio if data_inicio else True,
                HistoricoOrcamento.data_alteracao <= data_fim if data_fim else True
            ).group_by(HistoricoOrcamento.tipo_alteracao).all()
            
            # Calcular variações totais
            edicoes = query.filter(HistoricoOrcamento.tipo_alteracao == 'edicao').all()
            
            variacao_total_positiva = sum(
                h.variacao_total for h in edicoes if h.variacao_total > 0
            )
            
            variacao_total_negativa = sum(
                h.variacao_total for h in edicoes if h.variacao_total < 0
            )
            
            # Usuários mais ativos
            usuarios_ativos = db.session.query(
                Usuario.nome,
                db.func.count(HistoricoOrcamento.id).label('total_alteracoes')
            ).join(
                HistoricoOrcamento, Usuario.id == HistoricoOrcamento.usuario_id
            ).filter(
                HistoricoOrcamento.data_alteracao >= data_inicio if data_inicio else True,
                HistoricoOrcamento.data_alteracao <= data_fim if data_fim else True
            ).group_by(Usuario.nome).order_by(
                db.func.count(HistoricoOrcamento.id).desc()
            ).limit(10).all()
            
            return {
                'tipos_alteracao': [
                    {'tipo': t.tipo_alteracao, 'total': t.total} 
                    for t in tipos_alteracao
                ],
                'variacao_total_positiva': float(variacao_total_positiva),
                'variacao_total_negativa': float(variacao_total_negativa),
                'usuarios_ativos': [
                    {'nome': u.nome, 'total_alteracoes': u.total_alteracoes}
                    for u in usuarios_ativos
                ],
                'total_alteracoes': query.count()
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de alterações: {str(e)}")
            return {
                'tipos_alteracao': [],
                'variacao_total_positiva': 0,
                'variacao_total_negativa': 0,
                'usuarios_ativos': [],
                'total_alteracoes': 0
            }