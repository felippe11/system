"""
Serviço para gerenciamento de aprovações de compras em múltiplos níveis
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import and_, or_, desc
from extensions import db
from models.compra import Compra, AprovacaoCompra, NivelAprovacao
from models.user import Usuario
from services.compra_notification_service import CompraNotificationService
from services.aprovacao_notification_service import AprovacaoNotificationService


class AprovacaoService:
    """Serviço para gerenciar aprovações de compras"""
    
    @staticmethod
    def criar_niveis_aprovacao_padrao():
        """Cria os níveis de aprovação padrão do sistema"""
        niveis_padrao = [
            {
                'nome': 'Supervisor',
                'ordem': 1,
                'valor_minimo': 0.00,
                'valor_maximo': 1000.00,
                'obrigatorio': True,
                'descricao': 'Aprovação de supervisor para compras até R$ 1.000'
            },
            {
                'nome': 'Gerente',
                'ordem': 2,
                'valor_minimo': 1000.01,
                'valor_maximo': 5000.00,
                'obrigatorio': True,
                'descricao': 'Aprovação de gerente para compras de R$ 1.000 a R$ 5.000'
            },
            {
                'nome': 'Diretor',
                'ordem': 3,
                'valor_minimo': 5000.01,
                'valor_maximo': 999999999.99,
                'obrigatorio': True,
                'descricao': 'Aprovação de diretor para compras acima de R$ 5.000'
            }
        ]
        
        for nivel_data in niveis_padrao:
            nivel_existente = NivelAprovacao.query.filter_by(
                nome=nivel_data['nome'],
                ordem=nivel_data['ordem']
            ).first()
            
            if not nivel_existente:
                nivel = NivelAprovacao(**nivel_data)
                db.session.add(nivel)
        
        db.session.commit()
    
    @staticmethod
    def obter_niveis_necessarios(valor_compra: float) -> List[NivelAprovacao]:
        """Obtém os níveis de aprovação necessários para uma compra"""
        return NivelAprovacao.query.filter(
            and_(
                NivelAprovacao.ativo == True,
                NivelAprovacao.valor_minimo <= valor_compra,
                NivelAprovacao.valor_maximo >= valor_compra
            )
        ).order_by(NivelAprovacao.ordem).all()
    
    @staticmethod
    def iniciar_processo_aprovacao(compra_id: int) -> bool:
        """Inicia o processo de aprovação para uma compra"""
        try:
            compra = Compra.query.get(compra_id)
            if not compra:
                return False
            
            # Obter níveis necessários
            niveis = AprovacaoService.obter_niveis_necessarios(compra.valor_total)
            
            if not niveis:
                # Se não há níveis configurados, aprovar automaticamente
                compra.status = 'aprovada'
                compra.data_aprovacao = datetime.utcnow()
                db.session.commit()
                return True
            
            # Criar registros de aprovação
            for nivel in niveis:
                aprovacao = AprovacaoCompra(
                    compra_id=compra.id,
                    nivel_aprovacao_id=nivel.id,
                    status='pendente',
                    data_solicitacao=datetime.utcnow()
                )
                db.session.add(aprovacao)
            
            # Atualizar status da compra
            compra.status = 'aguardando_aprovacao'
            
            # Notificar primeiro nível
            primeiro_nivel = niveis[0]
            AprovacaoService._notificar_aprovadores(compra, primeiro_nivel)
            
            db.session.commit()
            
            # Enviar notificações para o primeiro nível de aprovação
            if niveis:
                try:
                    AprovacaoNotificationService.enviar_notificacao_aprovacao_pendente(
                        compra_id, niveis[0].id
                    )
                except Exception as e:
                    # Log error but don't fail the approval process
                    pass
            
            return True
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def aprovar_nivel(aprovacao_id: int, usuario_id: int, observacoes: str = None) -> Dict[str, Any]:
        """Aprova um nível específico"""
        try:
            aprovacao = AprovacaoCompra.query.get(aprovacao_id)
            if not aprovacao:
                return {'success': False, 'message': 'Aprovação não encontrada'}
            
            if aprovacao.status != 'pendente':
                return {'success': False, 'message': 'Esta aprovação já foi processada'}
            
            # Verificar se o usuário tem permissão para aprovar este nível
            usuario = Usuario.query.get(usuario_id)
            if not AprovacaoService._usuario_pode_aprovar(usuario, aprovacao.nivel_aprovacao):
                return {'success': False, 'message': 'Usuário não tem permissão para esta aprovação'}
            
            # Aprovar o nível
            aprovacao.status = 'aprovada'
            aprovacao.usuario_aprovador_id = usuario_id
            aprovacao.data_aprovacao = datetime.utcnow()
            aprovacao.observacoes = observacoes
            
            # Verificar se todos os níveis foram aprovados
            compra = aprovacao.compra
            aprovacoes_pendentes = AprovacaoCompra.query.filter_by(
                compra_id=compra.id,
                status='pendente'
            ).count()
            
            if aprovacoes_pendentes == 0:
                # Todas as aprovações foram concluídas
                compra.status = 'aprovada'
                compra.data_aprovacao = datetime.utcnow()
                
                # Notificar solicitante
                CompraNotificationService.notificar_aprovacao_final(compra)
            else:
                # Notificar próximo nível
                proximo_nivel = AprovacaoService._obter_proximo_nivel_pendente(compra.id)
                if proximo_nivel:
                    AprovacaoService._notificar_aprovadores(compra, proximo_nivel.nivel_aprovacao)
            
            db.session.commit()
            
            # Enviar notificação de conclusão
            try:
                AprovacaoNotificationService.enviar_notificacao_aprovacao_concluida(
                    aprovacao.compra_id, 'aprovada', observacoes
                )
            except Exception as e:
                # Log error but don't fail the approval process
                pass
            
            return {'success': True, 'message': 'Aprovação realizada com sucesso'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Erro ao aprovar: {str(e)}'}
    
    @staticmethod
    def rejeitar_nivel(aprovacao_id: int, usuario_id: int, motivo: str) -> Dict[str, Any]:
        """Rejeita um nível específico"""
        try:
            aprovacao = AprovacaoCompra.query.get(aprovacao_id)
            if not aprovacao:
                return {'success': False, 'message': 'Aprovação não encontrada'}
            
            if aprovacao.status != 'pendente':
                return {'success': False, 'message': 'Esta aprovação já foi processada'}
            
            # Verificar permissão
            usuario = Usuario.query.get(usuario_id)
            if not AprovacaoService._usuario_pode_aprovar(usuario, aprovacao.nivel_aprovacao):
                return {'success': False, 'message': 'Usuário não tem permissão para esta aprovação'}
            
            # Rejeitar o nível
            aprovacao.status = 'rejeitada'
            aprovacao.usuario_aprovador_id = usuario_id
            aprovacao.data_aprovacao = datetime.utcnow()
            aprovacao.observacoes = motivo
            
            # Rejeitar a compra
            compra = aprovacao.compra
            compra.status = 'rejeitada'
            compra.motivo_rejeicao = motivo
            
            # Rejeitar todas as outras aprovações pendentes
            AprovacaoCompra.query.filter_by(
                compra_id=compra.id,
                status='pendente'
            ).update({'status': 'cancelada'})
            
            # Notificar solicitante
            CompraNotificationService.notificar_rejeicao(compra, motivo)
            
            db.session.commit()
            return {'success': True, 'message': 'Compra rejeitada com sucesso'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Erro ao rejeitar: {str(e)}'}
    
    @staticmethod
    def obter_aprovacoes_pendentes(usuario_id: int) -> List[AprovacaoCompra]:
        """Obtém aprovações pendentes para um usuário"""
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            return []
        
        # Obter níveis que o usuário pode aprovar
        niveis_usuario = AprovacaoService._obter_niveis_usuario(usuario)
        
        if not niveis_usuario:
            return []
        
        return AprovacaoCompra.query.filter(
            and_(
                AprovacaoCompra.status == 'pendente',
                AprovacaoCompra.nivel_aprovacao_id.in_([n.id for n in niveis_usuario])
            )
        ).join(Compra).order_by(desc(Compra.data_criacao)).all()
    
    @staticmethod
    def obter_historico_aprovacoes(compra_id: int) -> List[AprovacaoCompra]:
        """Obtém o histórico de aprovações de uma compra"""
        return AprovacaoCompra.query.filter_by(
            compra_id=compra_id
        ).join(NivelAprovacao).order_by(NivelAprovacao.ordem).all()
    
    @staticmethod
    def _usuario_pode_aprovar(usuario: Usuario, nivel: NivelAprovacao) -> bool:
        """Verifica se um usuário pode aprovar um nível específico"""
        # Lógica baseada no tipo de usuário e configurações
        if usuario.tipo == 'admin':
            return True
        
        if nivel.nome == 'Supervisor' and usuario.tipo in ['monitor', 'admin']:
            return True
        
        if nivel.nome == 'Gerente' and usuario.tipo in ['admin']:
            return True
        
        if nivel.nome == 'Diretor' and usuario.tipo == 'admin':
            return True
        
        return False
    
    @staticmethod
    def _obter_niveis_usuario(usuario: Usuario) -> List[NivelAprovacao]:
        """Obtém os níveis que um usuário pode aprovar"""
        niveis = []
        
        if usuario.tipo == 'admin':
            niveis = NivelAprovacao.query.filter_by(ativo=True).all()
        elif usuario.tipo == 'monitor':
            niveis = NivelAprovacao.query.filter_by(
                ativo=True,
                nome='Supervisor'
            ).all()
        
        return niveis
    
    @staticmethod
    def _obter_proximo_nivel_pendente(compra_id: int) -> Optional[AprovacaoCompra]:
        """Obtém o próximo nível pendente de aprovação"""
        return AprovacaoCompra.query.filter_by(
            compra_id=compra_id,
            status='pendente'
        ).join(NivelAprovacao).order_by(NivelAprovacao.ordem).first()
    
    @staticmethod
    def _notificar_aprovadores(compra: Compra, nivel: NivelAprovacao):
        """Notifica os aprovadores de um nível específico"""
        # Obter usuários que podem aprovar este nível
        if nivel.nome == 'Supervisor':
            usuarios = Usuario.query.filter(Usuario.tipo.in_(['monitor', 'admin'])).all()
        elif nivel.nome == 'Gerente':
            usuarios = Usuario.query.filter_by(tipo='admin').all()
        elif nivel.nome == 'Diretor':
            usuarios = Usuario.query.filter_by(tipo='admin').all()
        else:
            usuarios = []
        
        # Enviar notificações
        for usuario in usuarios:
            CompraNotificationService.notificar_aprovacao_pendente(compra, usuario, nivel)