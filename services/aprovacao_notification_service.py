#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Serviço de notificações para o sistema de aprovação de compras.
"""

from flask import current_app, render_template_string
from services.email_service import send_email
from models.user import Usuario
from models.compra import Compra, AprovacaoCompra, NivelAprovacao
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AprovacaoNotificationService:
    """Serviço para envio de notificações de aprovação por email."""
    
    @staticmethod
    def enviar_notificacao_aprovacao_pendente(compra_id, nivel_aprovacao_id):
        """
        Envia notificação para aprovadores quando uma compra precisa de aprovação.
        
        Args:
            compra_id (int): ID da compra
            nivel_aprovacao_id (int): ID do nível de aprovação
        """
        try:
            compra = Compra.query.get(compra_id)
            nivel = NivelAprovacao.query.get(nivel_aprovacao_id)
            
            if not compra or not nivel:
                logger.error(f"Compra {compra_id} ou nível {nivel_aprovacao_id} não encontrados")
                return False
            
            # Buscar aprovadores para este nível (usuários admin ou com permissão específica)
            aprovadores = Usuario.query.filter(
                (Usuario.is_admin == True) | 
                (Usuario.pode_aprovar_compras == True)
            ).filter_by(cliente_id=compra.cliente_id, ativo=True).all()
            
            if not aprovadores:
                logger.warning(f"Nenhum aprovador encontrado para cliente {compra.cliente_id}")
                return False
            
            # Template do email
            template_html = """
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center;">
                    <h1 style="margin: 0;">Nova Aprovação Pendente</h1>
                </div>
                
                <div style="padding: 30px; background: #f8f9fa;">
                    <h2 style="color: #495057;">Compra #{{ compra.numero_compra }}</h2>
                    
                    <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="color: #667eea; margin-top: 0;">Detalhes da Compra</h3>
                        <p><strong>Fornecedor:</strong> {{ compra.fornecedor }}</p>
                        <p><strong>Valor Total:</strong> R$ {{ "%.2f"|format(compra.valor_total) }}</p>
                        <p><strong>Data de Criação:</strong> {{ compra.data_criacao.strftime('%d/%m/%Y %H:%M') }}</p>
                        <p><strong>Tipo de Gasto:</strong> {{ compra.tipo_gasto }}</p>
                        {% if compra.observacoes %}
                        <p><strong>Observações:</strong> {{ compra.observacoes }}</p>
                        {% endif %}
                    </div>
                    
                    <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="color: #667eea; margin-top: 0;">Nível de Aprovação</h3>
                        <p><strong>{{ nivel.nome }}</strong></p>
                        <p>{{ nivel.descricao }}</p>
                        <p><strong>Faixa de Valor:</strong> R$ {{ "%.2f"|format(nivel.valor_minimo) }} 
                        {% if nivel.valor_maximo %}até R$ {{ "%.2f"|format(nivel.valor_maximo) }}{% else %}ou mais{% endif %}</p>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{{ url_aprovacao }}" 
                           style="background: linear-gradient(135deg, #28a745, #20c997); 
                                  color: white; 
                                  padding: 15px 30px; 
                                  text-decoration: none; 
                                  border-radius: 8px; 
                                  font-weight: bold;
                                  display: inline-block;">
                            Acessar Sistema de Aprovação
                        </a>
                    </div>
                    
                    <div style="background: #e9ecef; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <p style="margin: 0; font-size: 14px; color: #6c757d;">
                            <strong>Importante:</strong> Esta aprovação é obrigatória para prosseguir com a compra. 
                            Por favor, analise os detalhes e tome uma decisão o mais breve possível.
                        </p>
                    </div>
                </div>
                
                <div style="background: #495057; color: white; padding: 15px; text-align: center; font-size: 12px;">
                    <p style="margin: 0;">Sistema de Gestão IAFAP - Notificação Automática</p>
                    <p style="margin: 5px 0 0 0;">Este é um email automático, não responda.</p>
                </div>
            </div>
            """
            
            # URL para acessar o sistema de aprovação
            url_aprovacao = current_app.config.get('BASE_URL', 'http://localhost:5000') + '/aprovacao'
            
            # Enviar email para cada aprovador
            emails_enviados = 0
            for aprovador in aprovadores:
                if not aprovador.email:
                    continue

                try:
                    html_content = render_template_string(
                        template_html,
                        compra=compra,
                        nivel=nivel,
                        aprovador=aprovador,
                        url_aprovacao=url_aprovacao,
                    )

                    send_email(
                        to=aprovador.email,
                        subject=f'Nova Aprovação Pendente - Compra #{compra.numero_compra}',
                        html=html_content,
                    )
                    emails_enviados += 1
                    logger.info("Email de aprovação enviado para %s", aprovador.email)

                except Exception as e:
                    logger.error("Erro ao enviar email para %s: %s", aprovador.email, e)
            
            logger.info(f"Enviados {emails_enviados} emails de notificação para compra {compra_id}")
            return emails_enviados > 0
            
        except Exception as e:
            logger.error(f"Erro ao enviar notificações de aprovação: {e}")
            return False
    
    @staticmethod
    def enviar_notificacao_aprovacao_concluida(compra_id, status, comentario=None):
        """
        Envia notificação quando uma aprovação é concluída (aprovada ou rejeitada).
        
        Args:
            compra_id (int): ID da compra
            status (str): 'aprovado' ou 'rejeitado'
            comentario (str): Comentário do aprovador
        """
        try:
            compra = Compra.query.get(compra_id)
            if not compra:
                logger.error(f"Compra {compra_id} não encontrada")
                return False
            
            # Buscar o solicitante da compra
            solicitante = Usuario.query.get(compra.usuario_id)
            if not solicitante or not solicitante.email:
                logger.warning(f"Solicitante da compra {compra_id} não encontrado ou sem email")
                return False
            
            # Template do email
            template_html = """
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: {% if status == 'aprovado' %}linear-gradient(135deg, #28a745, #20c997){% else %}linear-gradient(135deg, #dc3545, #e74c3c){% endif %}; color: white; padding: 20px; text-align: center;">
                    <h1 style="margin: 0;">Compra {{ status|title }}</h1>
                </div>
                
                <div style="padding: 30px; background: #f8f9fa;">
                    <h2 style="color: #495057;">Compra #{{ compra.numero_compra }}</h2>
                    
                    <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="color: {% if status == 'aprovado' %}#28a745{% else %}#dc3545{% endif %}; margin-top: 0;">
                            Status: {{ status|title }}
                        </h3>
                        <p><strong>Fornecedor:</strong> {{ compra.fornecedor }}</p>
                        <p><strong>Valor Total:</strong> R$ {{ "%.2f"|format(compra.valor_total) }}</p>
                        <p><strong>Data de Criação:</strong> {{ compra.data_criacao.strftime('%d/%m/%Y %H:%M') }}</p>
                        
                        {% if comentario %}
                        <div style="background: #e9ecef; padding: 15px; border-radius: 8px; margin: 15px 0;">
                            <p style="margin: 0;"><strong>Comentário do Aprovador:</strong></p>
                            <p style="margin: 10px 0 0 0; font-style: italic;">{{ comentario }}</p>
                        </div>
                        {% endif %}
                    </div>
                    
                    {% if status == 'aprovado' %}
                    <div style="background: #d4edda; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745;">
                        <p style="margin: 0; color: #155724;">
                            <strong>Próximos Passos:</strong> Sua compra foi aprovada e você pode prosseguir com o processo de aquisição.
                        </p>
                    </div>
                    {% else %}
                    <div style="background: #f8d7da; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #dc3545;">
                        <p style="margin: 0; color: #721c24;">
                            <strong>Ação Necessária:</strong> Sua compra foi rejeitada. Revise os detalhes e faça uma nova solicitação se necessário.
                        </p>
                    </div>
                    {% endif %}
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{{ url_compras }}" 
                           style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                  color: white; 
                                  padding: 15px 30px; 
                                  text-decoration: none; 
                                  border-radius: 8px; 
                                  font-weight: bold;
                                  display: inline-block;">
                            Acessar Sistema de Compras
                        </a>
                    </div>
                </div>
                
                <div style="background: #495057; color: white; padding: 15px; text-align: center; font-size: 12px;">
                    <p style="margin: 0;">Sistema de Gestão IAFAP - Notificação Automática</p>
                    <p style="margin: 5px 0 0 0;">Este é um email automático, não responda.</p>
                </div>
            </div>
            """
            
            # URL para acessar o sistema de compras
            url_compras = current_app.config.get('BASE_URL', 'http://localhost:5000') + '/compra'
            
            html_content = render_template_string(
                template_html,
                compra=compra,
                status=status,
                comentario=comentario,
                solicitante=solicitante,
                url_compras=url_compras,
            )

            send_email(
                to=solicitante.email,
                subject=f'Compra #{compra.numero_compra} - {status.title()}',
                html=html_content,
            )
            logger.info("Email de conclusão de aprovação enviado para %s", solicitante.email)
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar notificação de conclusão: {e}")
            return False
    
    @staticmethod
    def enviar_lembrete_aprovacao_pendente():
        """
        Envia lembretes para aprovações pendentes há mais de 24 horas.
        Esta função pode ser chamada por um job agendado.
        """
        try:
            from datetime import timedelta
            
            # Buscar aprovações pendentes há mais de 24 horas
            limite_tempo = datetime.utcnow() - timedelta(hours=24)
            
            aprovacoes_pendentes = AprovacaoCompra.query.filter(
                AprovacaoCompra.status == 'pendente',
                AprovacaoCompra.created_at < limite_tempo
            ).all()
            
            lembretes_enviados = 0
            
            for aprovacao in aprovacoes_pendentes:
                # Enviar lembrete (reutilizar a função de notificação pendente)
                if AprovacaoNotificationService.enviar_notificacao_aprovacao_pendente(
                    aprovacao.compra_id, 
                    aprovacao.nivel_aprovacao_id
                ):
                    lembretes_enviados += 1
            
            logger.info(f"Enviados {lembretes_enviados} lembretes de aprovação")
            return lembretes_enviados
            
        except Exception as e:
            logger.error(f"Erro ao enviar lembretes de aprovação: {e}")
            return 0
