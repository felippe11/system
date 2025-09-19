import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from decimal import Decimal
from jinja2 import Template

from extensions import db
from models.compra import Compra
from models.user import Usuario
from models.material import Polo
from models.orcamento import Orcamento
from services.mailjet_service import send_via_mailjet

logger = logging.getLogger(__name__)


class CompraNotificationService:
    """Serviço para notificações automáticas do sistema de compras."""
    
    @staticmethod
    def verificar_alertas_criticos():
        """Verifica e envia alertas críticos do sistema de compras."""
        try:
            # Verificar orçamentos excedidos
            CompraNotificationService.verificar_orcamentos_excedidos()
            
            # Verificar compras pendentes há muito tempo
            CompraNotificationService.verificar_compras_pendentes()
            
            # Verificar prestações de contas em atraso
            CompraNotificationService.verificar_prestacoes_atrasadas()
            
            logger.info("Verificação de alertas críticos concluída")
            
        except Exception as e:
            logger.error(f"Erro ao verificar alertas críticos: {str(e)}")
    
    @staticmethod
    def verificar_orcamentos_excedidos():
        """Verifica orçamentos que foram excedidos."""
        try:
            # Buscar todos os orçamentos ativos
            orcamentos = Orcamento.query.filter_by(ativo=True).all()
            
            for orcamento in orcamentos:
                # Calcular total gasto no período
                total_gasto = db.session.query(
                    db.func.sum(Compra.valor_total)
                ).filter(
                    Compra.polo_id == orcamento.polo_id,
                    Compra.data_compra >= orcamento.data_inicio,
                    Compra.data_compra <= orcamento.data_fim,
                    Compra.status.in_(['aprovada', 'finalizada'])
                ).scalar() or Decimal('0')
                
                # Verificar se excedeu o orçamento
                percentual_usado = (total_gasto / orcamento.valor_total) * 100 if orcamento.valor_total > 0 else 0
                
                if percentual_usado >= 100:
                    CompraNotificationService.enviar_alerta_orcamento_excedido(
                        orcamento, total_gasto, percentual_usado
                    )
                elif percentual_usado >= 90:
                    CompraNotificationService.enviar_alerta_orcamento_proximo_limite(
                        orcamento, total_gasto, percentual_usado
                    )
                    
        except Exception as e:
            logger.error(f"Erro ao verificar orçamentos excedidos: {str(e)}")
    
    @staticmethod
    def verificar_compras_pendentes():
        """Verifica compras pendentes há mais de 7 dias."""
        try:
            data_limite = datetime.now() - timedelta(days=7)
            
            compras_pendentes = Compra.query.filter(
                Compra.status == 'pendente',
                Compra.data_compra <= data_limite
            ).all()
            
            if compras_pendentes:
                CompraNotificationService.enviar_alerta_compras_pendentes(compras_pendentes)
                
        except Exception as e:
            logger.error(f"Erro ao verificar compras pendentes: {str(e)}")
    
    @staticmethod
    def verificar_prestacoes_atrasadas():
        """Verifica prestações de contas em atraso."""
        try:
            data_limite = datetime.now() - timedelta(days=30)
            
            prestacoes_atrasadas = Compra.query.filter(
                Compra.status == 'aprovada',
                Compra.data_compra <= data_limite,
                Compra.prestacao_contas == False
            ).all()
            
            if prestacoes_atrasadas:
                CompraNotificationService.enviar_alerta_prestacoes_atrasadas(prestacoes_atrasadas)
                
        except Exception as e:
            logger.error(f"Erro ao verificar prestações atrasadas: {str(e)}")
    
    @staticmethod
    def enviar_alerta_orcamento_excedido(orcamento, total_gasto, percentual_usado):
        """Envia alerta de orçamento excedido."""
        try:
            # Buscar administradores e monitores do polo
            destinatarios = CompraNotificationService._get_polo_managers(orcamento.polo_id)
            
            subject = f"🚨 ALERTA CRÍTICO: Orçamento Excedido - {orcamento.polo.nome}"
            
            template_data = {
                'polo_nome': orcamento.polo.nome,
                'orcamento_valor': orcamento.valor_total,
                'total_gasto': total_gasto,
                'percentual_usado': round(percentual_usado, 2),
                'periodo_inicio': orcamento.data_inicio.strftime('%d/%m/%Y'),
                'periodo_fim': orcamento.data_fim.strftime('%d/%m/%Y'),
                'data_alerta': datetime.now().strftime('%d/%m/%Y %H:%M')
            }
            
            html_content = CompraNotificationService._get_template_orcamento_excedido().render(**template_data)
            
            for destinatario in destinatarios:
                send_via_mailjet(
                    to_email=destinatario.email,
                    subject=subject,
                    html=html_content
                )
                
            logger.info(f"Alerta de orçamento excedido enviado para {len(destinatarios)} destinatários")
            
        except Exception as e:
            logger.error(f"Erro ao enviar alerta de orçamento excedido: {str(e)}")
    
    @staticmethod
    def enviar_alerta_orcamento_proximo_limite(orcamento, total_gasto, percentual_usado):
        """Envia alerta de orçamento próximo ao limite."""
        try:
            destinatarios = CompraNotificationService._get_polo_managers(orcamento.polo_id)
            
            subject = f"⚠️ ATENÇÃO: Orçamento Próximo ao Limite - {orcamento.polo.nome}"
            
            template_data = {
                'polo_nome': orcamento.polo.nome,
                'orcamento_valor': orcamento.valor_total,
                'total_gasto': total_gasto,
                'percentual_usado': round(percentual_usado, 2),
                'valor_restante': orcamento.valor_total - total_gasto,
                'periodo_inicio': orcamento.data_inicio.strftime('%d/%m/%Y'),
                'periodo_fim': orcamento.data_fim.strftime('%d/%m/%Y'),
                'data_alerta': datetime.now().strftime('%d/%m/%Y %H:%M')
            }
            
            html_content = CompraNotificationService._get_template_orcamento_proximo_limite().render(**template_data)
            
            for destinatario in destinatarios:
                send_via_mailjet(
                    to_email=destinatario.email,
                    subject=subject,
                    html=html_content
                )
                
            logger.info(f"Alerta de orçamento próximo ao limite enviado para {len(destinatarios)} destinatários")
            
        except Exception as e:
            logger.error(f"Erro ao enviar alerta de orçamento próximo ao limite: {str(e)}")
    
    @staticmethod
    def enviar_alerta_compras_pendentes(compras_pendentes):
        """Envia alerta de compras pendentes há muito tempo."""
        try:
            # Agrupar por polo
            compras_por_polo = {}
            for compra in compras_pendentes:
                if compra.polo_id not in compras_por_polo:
                    compras_por_polo[compra.polo_id] = []
                compras_por_polo[compra.polo_id].append(compra)
            
            for polo_id, compras in compras_por_polo.items():
                destinatarios = CompraNotificationService._get_polo_managers(polo_id)
                polo_nome = compras[0].polo.nome
                
                subject = f"📋 Compras Pendentes de Aprovação - {polo_nome}"
                
                template_data = {
                    'polo_nome': polo_nome,
                    'total_compras': len(compras),
                    'compras': [
                        {
                            'numero': compra.numero_compra,
                            'fornecedor': compra.fornecedor,
                            'valor': compra.valor_total,
                            'data': compra.data_compra.strftime('%d/%m/%Y'),
                            'dias_pendente': (datetime.now() - compra.data_compra).days
                        }
                        for compra in compras
                    ],
                    'data_alerta': datetime.now().strftime('%d/%m/%Y %H:%M')
                }
                
                html_content = CompraNotificationService._get_template_compras_pendentes().render(**template_data)
                
                for destinatario in destinatarios:
                    send_via_mailjet(
                        to_email=destinatario.email,
                        subject=subject,
                        html=html_content
                    )
                    
                logger.info(f"Alerta de compras pendentes enviado para {polo_nome}")
                
        except Exception as e:
            logger.error(f"Erro ao enviar alerta de compras pendentes: {str(e)}")
    
    @staticmethod
    def enviar_alerta_prestacoes_atrasadas(prestacoes_atrasadas):
        """Envia alerta de prestações de contas atrasadas."""
        try:
            # Agrupar por polo
            prestacoes_por_polo = {}
            for compra in prestacoes_atrasadas:
                if compra.polo_id not in prestacoes_por_polo:
                    prestacoes_por_polo[compra.polo_id] = []
                prestacoes_por_polo[compra.polo_id].append(compra)
            
            for polo_id, compras in prestacoes_por_polo.items():
                destinatarios = CompraNotificationService._get_polo_managers(polo_id)
                polo_nome = compras[0].polo.nome
                
                subject = f"📄 Prestações de Contas em Atraso - {polo_nome}"
                
                template_data = {
                    'polo_nome': polo_nome,
                    'total_prestacoes': len(compras),
                    'prestacoes': [
                        {
                            'numero': compra.numero_compra,
                            'fornecedor': compra.fornecedor,
                            'valor': compra.valor_total,
                            'data_compra': compra.data_compra.strftime('%d/%m/%Y'),
                            'dias_atraso': (datetime.now() - compra.data_compra).days
                        }
                        for compra in compras
                    ],
                    'data_alerta': datetime.now().strftime('%d/%m/%Y %H:%M')
                }
                
                html_content = CompraNotificationService._get_template_prestacoes_atrasadas().render(**template_data)
                
                for destinatario in destinatarios:
                    send_via_mailjet(
                        to_email=destinatario.email,
                        subject=subject,
                        html=html_content
                    )
                    
                logger.info(f"Alerta de prestações atrasadas enviado para {polo_nome}")
                
        except Exception as e:
            logger.error(f"Erro ao enviar alerta de prestações atrasadas: {str(e)}")
    
    @staticmethod
    def _get_polo_managers(polo_id):
        """Busca administradores e monitores do polo."""
        try:
            # Buscar usuários com acesso ao polo (admin e monitor)
            usuarios = Usuario.query.filter(
                Usuario.ativo == True,
                Usuario.email.isnot(None),
                Usuario.tipo_usuario.in_(['admin', 'monitor']),
                Usuario.polo_id == polo_id
            ).all()
            
            # Adicionar administradores globais
            admins_globais = Usuario.query.filter(
                Usuario.ativo == True,
                Usuario.email.isnot(None),
                Usuario.tipo_usuario == 'admin'
            ).all()
            
            # Combinar e remover duplicatas
            todos_usuarios = list(set(usuarios + admins_globais))
            
            return todos_usuarios
            
        except Exception as e:
            logger.error(f"Erro ao buscar gestores do polo: {str(e)}")
            return []
    
    @staticmethod
    def _get_template_orcamento_excedido():
        """Template para alerta de orçamento excedido."""
        template_str = """
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #dc3545; border-radius: 10px; background-color: #f8f9fa;">
                <h2 style="color: #dc3545; text-align: center;">🚨 ALERTA CRÍTICO: Orçamento Excedido</h2>
                
                <div style="padding: 15px; background-color: #f5c6cb; border-left: 5px solid #dc3545; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #721c24;">Polo: {{ polo_nome }}</h3>
                    <p><strong>Orçamento Total:</strong> R$ {{ "%.2f"|format(orcamento_valor) }}</p>
                    <p><strong>Total Gasto:</strong> R$ {{ "%.2f"|format(total_gasto) }}</p>
                    <p><strong>Percentual Usado:</strong> {{ percentual_usado }}%</p>
                    <p><strong>Período:</strong> {{ periodo_inicio }} a {{ periodo_fim }}</p>
                </div>
                
                <div style="padding: 15px; background-color: #fff3cd; border-left: 5px solid #ffc107;">
                    <h4 style="margin-top: 0; color: #856404;">Ação Necessária</h4>
                    <p>O orçamento foi excedido! É necessário:</p>
                    <ul>
                        <li>Revisar as compras aprovadas</li>
                        <li>Avaliar a necessidade de ajuste orçamentário</li>
                        <li>Suspender novas aprovações até regularização</li>
                    </ul>
                </div>
                
                <p style="text-align: center; margin-top: 20px; font-size: 12px; color: #666;">
                    Alerta gerado automaticamente em {{ data_alerta }}
                </p>
            </div>
        </body>
        </html>
        """
        return Template(template_str)
    
    @staticmethod
    def _get_template_orcamento_proximo_limite():
        """Template para alerta de orçamento próximo ao limite."""
        template_str = """
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ffc107; border-radius: 10px; background-color: #f8f9fa;">
                <h2 style="color: #ffc107; text-align: center;">⚠️ ATENÇÃO: Orçamento Próximo ao Limite</h2>
                
                <div style="padding: 15px; background-color: #fff3cd; border-left: 5px solid #ffc107; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #856404;">Polo: {{ polo_nome }}</h3>
                    <p><strong>Orçamento Total:</strong> R$ {{ "%.2f"|format(orcamento_valor) }}</p>
                    <p><strong>Total Gasto:</strong> R$ {{ "%.2f"|format(total_gasto) }}</p>
                    <p><strong>Valor Restante:</strong> R$ {{ "%.2f"|format(valor_restante) }}</p>
                    <p><strong>Percentual Usado:</strong> {{ percentual_usado }}%</p>
                    <p><strong>Período:</strong> {{ periodo_inicio }} a {{ periodo_fim }}</p>
                </div>
                
                <div style="padding: 15px; background-color: #d1ecf1; border-left: 5px solid #17a2b8;">
                    <h4 style="margin-top: 0; color: #0c5460;">Recomendações</h4>
                    <p>O orçamento está próximo ao limite. Recomendamos:</p>
                    <ul>
                        <li>Monitorar de perto as próximas compras</li>
                        <li>Priorizar apenas compras essenciais</li>
                        <li>Considerar remanejamento de recursos se necessário</li>
                    </ul>
                </div>
                
                <p style="text-align: center; margin-top: 20px; font-size: 12px; color: #666;">
                    Alerta gerado automaticamente em {{ data_alerta }}
                </p>
            </div>
        </body>
        </html>
        """
        return Template(template_str)
    
    @staticmethod
    def _get_template_compras_pendentes():
        """Template para alerta de compras pendentes."""
        template_str = """
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #17a2b8; border-radius: 10px; background-color: #f8f9fa;">
                <h2 style="color: #17a2b8; text-align: center;">📋 Compras Pendentes de Aprovação</h2>
                
                <div style="padding: 15px; background-color: #d1ecf1; border-left: 5px solid #17a2b8; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #0c5460;">Polo: {{ polo_nome }}</h3>
                    <p><strong>Total de Compras Pendentes:</strong> {{ total_compras }}</p>
                </div>
                
                <div style="padding: 15px; background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 5px;">
                    <h4 style="margin-top: 0;">Compras Pendentes:</h4>
                    {% for compra in compras %}
                    <div style="padding: 10px; margin: 10px 0; background-color: #f8f9fa; border-left: 3px solid #17a2b8;">
                        <p><strong>Nº:</strong> {{ compra.numero }} | <strong>Fornecedor:</strong> {{ compra.fornecedor }}</p>
                        <p><strong>Valor:</strong> R$ {{ "%.2f"|format(compra.valor) }} | <strong>Data:</strong> {{ compra.data }}</p>
                        <p><strong>Pendente há:</strong> {{ compra.dias_pendente }} dias</p>
                    </div>
                    {% endfor %}
                </div>
                
                <p style="text-align: center; margin-top: 20px; font-size: 12px; color: #666;">
                    Alerta gerado automaticamente em {{ data_alerta }}
                </p>
            </div>
        </body>
        </html>
        """
        return Template(template_str)
    
    @staticmethod
    def _get_template_prestacoes_atrasadas():
        """Template para alerta de prestações atrasadas."""
        template_str = """
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #fd7e14; border-radius: 10px; background-color: #f8f9fa;">
                <h2 style="color: #fd7e14; text-align: center;">📄 Prestações de Contas em Atraso</h2>
                
                <div style="padding: 15px; background-color: #ffeaa7; border-left: 5px solid #fd7e14; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #8b4513;">Polo: {{ polo_nome }}</h3>
                    <p><strong>Total de Prestações em Atraso:</strong> {{ total_prestacoes }}</p>
                </div>
                
                <div style="padding: 15px; background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 5px;">
                    <h4 style="margin-top: 0;">Prestações em Atraso:</h4>
                    {% for prestacao in prestacoes %}
                    <div style="padding: 10px; margin: 10px 0; background-color: #f8f9fa; border-left: 3px solid #fd7e14;">
                        <p><strong>Nº:</strong> {{ prestacao.numero }} | <strong>Fornecedor:</strong> {{ prestacao.fornecedor }}</p>
                        <p><strong>Valor:</strong> R$ {{ "%.2f"|format(prestacao.valor) }} | <strong>Data da Compra:</strong> {{ prestacao.data_compra }}</p>
                        <p><strong>Atraso:</strong> {{ prestacao.dias_atraso }} dias</p>
                    </div>
                    {% endfor %}
                </div>
                
                <p style="text-align: center; margin-top: 20px; font-size: 12px; color: #666;">
                    Alerta gerado automaticamente em {{ data_alerta }}
                </p>
            </div>
        </body>
        </html>
        """
        return Template(template_str)