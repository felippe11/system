from datetime import datetime, date
from typing import List, Dict, Any
from models.compra import OrcamentoCliente, Compra
from extensions import db
from sqlalchemy import func


class AlertaOrcamentoService:
    """Serviço para gerenciar alertas de controle orçamentário."""
    
    @staticmethod
    def obter_alertas_cliente(cliente_id: int, ano: int = None) -> Dict[str, Any]:
        """
        Obtém todos os alertas orçamentários para um cliente.
        
        Args:
            cliente_id: ID do cliente
            ano: Ano do orçamento (padrão: ano atual)
            
        Returns:
            Dict com alertas organizados por criticidade
        """
        if ano is None:
            ano = datetime.now().year
            
        orcamento = OrcamentoCliente.query.filter_by(
            cliente_id=cliente_id,
            ano_orcamento=ano,
            ativo=True
        ).first()
        
        if not orcamento:
            return {
                'criticos': [],
                'avisos': [],
                'informativos': [],
                'total_alertas': 0,
                'orcamento_configurado': False
            }
        
        alertas = {
            'criticos': [],
            'avisos': [],
            'informativos': [],
            'total_alertas': 0,
            'orcamento_configurado': True,
            'orcamento': orcamento.to_dict()
        }
        
        # Verificar alertas críticos (>= 90% do orçamento)
        AlertaOrcamentoService._verificar_alertas_criticos(orcamento, alertas)
        
        # Verificar avisos (>= valor de alerta configurado)
        AlertaOrcamentoService._verificar_avisos(orcamento, alertas)
        
        # Verificar informativos (>= 70% do orçamento)
        AlertaOrcamentoService._verificar_informativos(orcamento, alertas)
        
        # Contar total de alertas
        alertas['total_alertas'] = (
            len(alertas['criticos']) + 
            len(alertas['avisos']) + 
            len(alertas['informativos'])
        )
        
        return alertas
    
    @staticmethod
    def _verificar_alertas_criticos(orcamento: OrcamentoCliente, alertas: Dict[str, Any]):
        """Verifica alertas críticos (>= 90% do orçamento)."""
        
        # Alerta crítico - Orçamento total
        if orcamento.percentual_gasto_total >= 90:
            alertas['criticos'].append({
                'tipo': 'orcamento_total_critico',
                'titulo': 'Orçamento Total Crítico',
                'mensagem': f'Orçamento total atingiu {orcamento.percentual_gasto_total:.1f}% do limite',
                'valor_gasto': orcamento.valor_gasto_total,
                'valor_disponivel': orcamento.valor_total_disponivel,
                'percentual': orcamento.percentual_gasto_total,
                'icone': 'exclamation-triangle-fill',
                'cor': 'danger'
            })
        
        # Alerta crítico - Orçamento de custeio
        if orcamento.percentual_gasto_custeio >= 90:
            alertas['criticos'].append({
                'tipo': 'orcamento_custeio_critico',
                'titulo': 'Orçamento de Custeio Crítico',
                'mensagem': f'Orçamento de custeio atingiu {orcamento.percentual_gasto_custeio:.1f}% do limite',
                'valor_gasto': orcamento.valor_gasto_custeio,
                'valor_disponivel': orcamento.valor_custeio_disponivel,
                'percentual': orcamento.percentual_gasto_custeio,
                'icone': 'exclamation-triangle-fill',
                'cor': 'danger'
            })
        
        # Alerta crítico - Orçamento de capital
        if orcamento.percentual_gasto_capital >= 90:
            alertas['criticos'].append({
                'tipo': 'orcamento_capital_critico',
                'titulo': 'Orçamento de Capital Crítico',
                'mensagem': f'Orçamento de capital atingiu {orcamento.percentual_gasto_capital:.1f}% do limite',
                'valor_gasto': orcamento.valor_gasto_capital,
                'valor_disponivel': orcamento.valor_capital_disponivel,
                'percentual': orcamento.percentual_gasto_capital,
                'icone': 'exclamation-triangle-fill',
                'cor': 'danger'
            })
    
    @staticmethod
    def _verificar_avisos(orcamento: OrcamentoCliente, alertas: Dict[str, Any]):
        """Verifica avisos baseados nos valores de alerta configurados."""
        
        # Aviso - Valor de alerta total
        if orcamento.alerta_total and orcamento.percentual_gasto_total < 90:
            alertas['avisos'].append({
                'tipo': 'alerta_total',
                'titulo': 'Alerta de Orçamento Total',
                'mensagem': f'Orçamento total atingiu o valor de alerta configurado ({orcamento.percentual_gasto_total:.1f}%)',
                'valor_gasto': orcamento.valor_gasto_total,
                'valor_alerta': orcamento.valor_alerta_total,
                'percentual': orcamento.percentual_gasto_total,
                'icone': 'exclamation-triangle',
                'cor': 'warning'
            })
        
        # Aviso - Valor de alerta custeio
        if orcamento.alerta_custeio and orcamento.percentual_gasto_custeio < 90:
            alertas['avisos'].append({
                'tipo': 'alerta_custeio',
                'titulo': 'Alerta de Orçamento de Custeio',
                'mensagem': f'Orçamento de custeio atingiu o valor de alerta configurado ({orcamento.percentual_gasto_custeio:.1f}%)',
                'valor_gasto': orcamento.valor_gasto_custeio,
                'valor_alerta': orcamento.valor_alerta_custeio,
                'percentual': orcamento.percentual_gasto_custeio,
                'icone': 'exclamation-triangle',
                'cor': 'warning'
            })
        
        # Aviso - Valor de alerta capital
        if orcamento.alerta_capital and orcamento.percentual_gasto_capital < 90:
            alertas['avisos'].append({
                'tipo': 'alerta_capital',
                'titulo': 'Alerta de Orçamento de Capital',
                'mensagem': f'Orçamento de capital atingiu o valor de alerta configurado ({orcamento.percentual_gasto_capital:.1f}%)',
                'valor_gasto': orcamento.valor_gasto_capital,
                'valor_alerta': orcamento.valor_alerta_capital,
                'percentual': orcamento.percentual_gasto_capital,
                'icone': 'exclamation-triangle',
                'cor': 'warning'
            })
    
    @staticmethod
    def _verificar_informativos(orcamento: OrcamentoCliente, alertas: Dict[str, Any]):
        """Verifica alertas informativos (>= 70% do orçamento)."""
        
        # Informativo - Orçamento total
        if (orcamento.percentual_gasto_total >= 70 and 
            orcamento.percentual_gasto_total < 90 and 
            not orcamento.alerta_total):
            alertas['informativos'].append({
                'tipo': 'info_total',
                'titulo': 'Informativo - Orçamento Total',
                'mensagem': f'Orçamento total atingiu {orcamento.percentual_gasto_total:.1f}% do limite',
                'valor_gasto': orcamento.valor_gasto_total,
                'valor_disponivel': orcamento.valor_total_disponivel,
                'percentual': orcamento.percentual_gasto_total,
                'icone': 'info-circle',
                'cor': 'info'
            })
        
        # Informativo - Orçamento de custeio
        if (orcamento.percentual_gasto_custeio >= 70 and 
            orcamento.percentual_gasto_custeio < 90 and 
            not orcamento.alerta_custeio):
            alertas['informativos'].append({
                'tipo': 'info_custeio',
                'titulo': 'Informativo - Orçamento de Custeio',
                'mensagem': f'Orçamento de custeio atingiu {orcamento.percentual_gasto_custeio:.1f}% do limite',
                'valor_gasto': orcamento.valor_gasto_custeio,
                'valor_disponivel': orcamento.valor_custeio_disponivel,
                'percentual': orcamento.percentual_gasto_custeio,
                'icone': 'info-circle',
                'cor': 'info'
            })
        
        # Informativo - Orçamento de capital
        if (orcamento.percentual_gasto_capital >= 70 and 
            orcamento.percentual_gasto_capital < 90 and 
            not orcamento.alerta_capital):
            alertas['informativos'].append({
                'tipo': 'info_capital',
                'titulo': 'Informativo - Orçamento de Capital',
                'mensagem': f'Orçamento de capital atingiu {orcamento.percentual_gasto_capital:.1f}% do limite',
                'valor_gasto': orcamento.valor_gasto_capital,
                'valor_disponivel': orcamento.valor_capital_disponivel,
                'percentual': orcamento.percentual_gasto_capital,
                'icone': 'info-circle',
                'cor': 'info'
            })
    
    @staticmethod
    def obter_resumo_orcamentario(cliente_id: int, ano: int = None) -> Dict[str, Any]:
        """
        Obtém resumo orçamentário para exibição no dashboard.
        
        Args:
            cliente_id: ID do cliente
            ano: Ano do orçamento (padrão: ano atual)
            
        Returns:
            Dict com resumo orçamentário
        """
        if ano is None:
            ano = datetime.now().year
            
        orcamento = OrcamentoCliente.query.filter_by(
            cliente_id=cliente_id,
            ano_orcamento=ano,
            ativo=True
        ).first()
        
        if not orcamento:
            return {
                'configurado': False,
                'ano': ano,
                'mensagem': 'Orçamento não configurado para este ano'
            }
        
        return {
            'configurado': True,
            'ano': ano,
            'total': {
                'disponivel': orcamento.valor_total_disponivel,
                'gasto': orcamento.valor_gasto_total,
                'percentual': orcamento.percentual_gasto_total,
                'restante': orcamento.valor_total_disponivel - orcamento.valor_gasto_total
            },
            'custeio': {
                'disponivel': orcamento.valor_custeio_disponivel,
                'gasto': orcamento.valor_gasto_custeio,
                'percentual': orcamento.percentual_gasto_custeio,
                'restante': orcamento.valor_custeio_disponivel - orcamento.valor_gasto_custeio
            },
            'capital': {
                'disponivel': orcamento.valor_capital_disponivel,
                'gasto': orcamento.valor_gasto_capital,
                'percentual': orcamento.percentual_gasto_capital,
                'restante': orcamento.valor_capital_disponivel - orcamento.valor_gasto_capital
            }
        }
    
    @staticmethod
    def verificar_disponibilidade_orcamentaria(cliente_id: int, valor: float, tipo_gasto: str = 'total') -> Dict[str, Any]:
        """
        Verifica se há disponibilidade orçamentária para uma compra.
        
        Args:
            cliente_id: ID do cliente
            valor: Valor da compra
            tipo_gasto: Tipo de gasto ('total', 'custeio', 'capital')
            
        Returns:
            Dict com resultado da verificação
        """
        ano = datetime.now().year
        orcamento = OrcamentoCliente.query.filter_by(
            cliente_id=cliente_id,
            ano_orcamento=ano,
            ativo=True
        ).first()
        
        if not orcamento:
            return {
                'disponivel': False,
                'motivo': 'Orçamento não configurado',
                'valor_solicitado': valor,
                'tipo_gasto': tipo_gasto
            }
        
        if tipo_gasto == 'custeio':
            valor_disponivel = orcamento.valor_custeio_disponivel - orcamento.valor_gasto_custeio
            percentual_apos = ((orcamento.valor_gasto_custeio + valor) / orcamento.valor_custeio_disponivel) * 100
        elif tipo_gasto == 'capital':
            valor_disponivel = orcamento.valor_capital_disponivel - orcamento.valor_gasto_capital
            percentual_apos = ((orcamento.valor_gasto_capital + valor) / orcamento.valor_capital_disponivel) * 100
        else:  # total
            valor_disponivel = orcamento.valor_total_disponivel - orcamento.valor_gasto_total
            percentual_apos = ((orcamento.valor_gasto_total + valor) / orcamento.valor_total_disponivel) * 100
        
        disponivel = valor <= valor_disponivel
        
        return {
            'disponivel': disponivel,
            'valor_solicitado': valor,
            'valor_disponivel': valor_disponivel,
            'percentual_apos_compra': percentual_apos,
            'tipo_gasto': tipo_gasto,
            'motivo': 'Valor excede o orçamento disponível' if not disponivel else None,
            'alerta': percentual_apos >= 90 if disponivel else False
        }