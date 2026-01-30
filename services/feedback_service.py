"""
Serviço para gerenciar perguntas e respostas de feedback personalizadas.
"""

from models import (
    PerguntaFeedback,
    RespostaFeedback,
    FeedbackSession,
    Oficina,
    Usuario,
    Inscricao,
    FeedbackTemplate,
    FeedbackTemplateOficina,
)
from extensions import db
from datetime import datetime, timedelta
import json
import secrets
import string


class FeedbackService:
    """Serviço para gerenciar feedback personalizado."""
    
    @staticmethod
    def criar_pergunta(cliente_id, titulo, descricao, tipo, oficina_id=None, atividade_id=None, opcoes=None, obrigatoria=True, ordem=0):
        """
        Cria uma nova pergunta de feedback.

        Args:
            cliente_id: ID do cliente
            titulo: Título da pergunta
            descricao: Descrição da pergunta
            tipo: Tipo da pergunta (TipoPergunta)
            oficina_id: ID da oficina (None para aplicar a todas)
            atividade_id: ID da atividade (None para aplicar a todas)
            opcoes: Lista de opções para múltipla escolha
            obrigatoria: Se a pergunta é obrigatória
            ordem: Ordem de exibição
            
        Returns:
            PerguntaFeedback: Objeto da pergunta criada
        """
        pergunta = PerguntaFeedback(
            cliente_id=cliente_id,
            oficina_id=oficina_id,
            atividade_id=atividade_id,
            titulo=titulo,
            descricao=descricao,
            tipo=tipo,
            opcoes=json.dumps(opcoes) if opcoes else None,
            obrigatoria=obrigatoria,
            ordem=ordem
        )
        
        db.session.add(pergunta)
        db.session.commit()
        return pergunta

    @staticmethod
    def criar_pergunta_template(template_id, cliente_id, titulo, descricao, tipo, opcoes=None, obrigatoria=True, ordem=0):
        pergunta = PerguntaFeedback(
            cliente_id=cliente_id,
            template_id=template_id,
            titulo=titulo,
            descricao=descricao,
            tipo=tipo,
            opcoes=json.dumps(opcoes) if opcoes else None,
            obrigatoria=obrigatoria,
            ordem=ordem,
        )
        db.session.add(pergunta)
        db.session.commit()
        return pergunta

    @staticmethod
    def criar_template(cliente_id, nome, descricao=None, is_default=False):
        if is_default:
            FeedbackTemplate.query.filter_by(cliente_id=cliente_id, is_default=True).update(
                {"is_default": False}
            )
        template = FeedbackTemplate(
            cliente_id=cliente_id,
            nome=nome,
            descricao=descricao,
            is_default=is_default,
        )
        db.session.add(template)
        db.session.commit()
        return template

    @staticmethod
    def definir_template_padrao(cliente_id, template_id):
        FeedbackTemplate.query.filter_by(cliente_id=cliente_id, is_default=True).update(
            {"is_default": False}
        )
        template = FeedbackTemplate.query.get_or_404(template_id)
        template.is_default = True
        db.session.commit()
        return template

    @staticmethod
    def aplicar_template(template_id, oficina_ids):
        template = FeedbackTemplate.query.get_or_404(template_id)
        for oficina_id in oficina_ids:
            # Desativa perguntas personalizadas da oficina (mantém histórico)
            PerguntaFeedback.query.filter_by(
                oficina_id=oficina_id, ativa=True
            ).update({"ativa": False})
            vinculo = FeedbackTemplateOficina.query.filter_by(oficina_id=oficina_id).first()
            if vinculo:
                vinculo.template_id = template.id
            else:
                vinculo = FeedbackTemplateOficina(
                    template_id=template.id,
                    oficina_id=oficina_id,
                )
                db.session.add(vinculo)
        db.session.commit()
        return template

    @staticmethod
    def desvincular_oficina(oficina_id):
        vinculo = FeedbackTemplateOficina.query.filter_by(oficina_id=oficina_id).first()
        if not vinculo:
            return None
        template = vinculo.template
        perguntas_template = PerguntaFeedback.query.filter_by(
            template_id=template.id, ativa=True
        ).order_by(PerguntaFeedback.ordem, PerguntaFeedback.id).all()
        for pergunta in perguntas_template:
            clone = PerguntaFeedback(
                cliente_id=template.cliente_id,
                oficina_id=oficina_id,
                titulo=pergunta.titulo,
                descricao=pergunta.descricao,
                tipo=pergunta.tipo,
                opcoes=pergunta.opcoes,
                obrigatoria=pergunta.obrigatoria,
                ordem=pergunta.ordem,
                ativa=True,
            )
            db.session.add(clone)
        db.session.delete(vinculo)
        db.session.commit()
        return template
    
    @staticmethod
    def listar_perguntas(cliente_id, oficina_id=None, atividade_id=None):
        """
        Lista perguntas de feedback para um cliente, oficina e/ou atividade.
        
        Args:
            cliente_id: ID do cliente
            oficina_id: ID da oficina (None para todas)
            atividade_id: ID da atividade (None para todas)
            
        Returns:
            List[PerguntaFeedback]: Lista de perguntas
        """
        query = PerguntaFeedback.query.filter_by(cliente_id=cliente_id, ativa=True)
        
        if oficina_id and atividade_id:
            # Perguntas específicas da atividade OU globais da oficina OU globais do cliente
            query = query.filter(
                db.or_(
                    PerguntaFeedback.atividade_id == atividade_id,
                    db.and_(
                        PerguntaFeedback.oficina_id == oficina_id,
                        PerguntaFeedback.atividade_id.is_(None)
                    ),
                    db.and_(
                        PerguntaFeedback.oficina_id.is_(None),
                        PerguntaFeedback.atividade_id.is_(None)
                    )
                )
            )
        elif oficina_id:
            # Se houver perguntas customizadas da oficina, usa apenas elas
            perguntas_custom = PerguntaFeedback.query.filter_by(
                cliente_id=cliente_id,
                oficina_id=oficina_id,
                ativa=True,
            ).order_by(PerguntaFeedback.ordem, PerguntaFeedback.id).all()
            if perguntas_custom:
                return perguntas_custom

            # Se houver template vinculado, usa perguntas do template
            vinculo = FeedbackTemplateOficina.query.filter_by(oficina_id=oficina_id).first()
            if vinculo:
                return PerguntaFeedback.query.filter_by(
                    cliente_id=cliente_id,
                    template_id=vinculo.template_id,
                    ativa=True,
                ).order_by(PerguntaFeedback.ordem, PerguntaFeedback.id).all()

            # Se houver template padrão, usa perguntas do template padrão
            template_padrao = FeedbackTemplate.query.filter_by(
                cliente_id=cliente_id, is_default=True
            ).first()
            if template_padrao:
                return PerguntaFeedback.query.filter_by(
                    cliente_id=cliente_id,
                    template_id=template_padrao.id,
                    ativa=True,
                ).order_by(PerguntaFeedback.ordem, PerguntaFeedback.id).all()

            # Fallback: perguntas globais legadas
            query = query.filter(
                db.and_(
                    PerguntaFeedback.oficina_id.is_(None),
                    PerguntaFeedback.template_id.is_(None),
                )
            )
        elif atividade_id:
            # Perguntas específicas da atividade OU globais do cliente
            query = query.filter(
                db.or_(
                    PerguntaFeedback.atividade_id == atividade_id,
                    PerguntaFeedback.atividade_id.is_(None)
                )
            )
        else:
            # Apenas perguntas globais
            query = query.filter(
                db.and_(
                    PerguntaFeedback.oficina_id.is_(None),
                    PerguntaFeedback.template_id.is_(None),
                    PerguntaFeedback.atividade_id.is_(None)
                )
            )
        
        return query.order_by(PerguntaFeedback.ordem, PerguntaFeedback.id).all()
    
    @staticmethod
    def atualizar_pergunta(pergunta_id, **kwargs):
        """
        Atualiza uma pergunta de feedback.
        
        Args:
            pergunta_id: ID da pergunta
            **kwargs: Campos para atualizar
            
        Returns:
            PerguntaFeedback: Objeto da pergunta atualizada
        """
        pergunta = PerguntaFeedback.query.get_or_404(pergunta_id)
        
        for key, value in kwargs.items():
            if hasattr(pergunta, key):
                if key == 'opcoes' and value:
                    setattr(pergunta, key, json.dumps(value))
                else:
                    setattr(pergunta, key, value)
        
        pergunta.updated_at = datetime.utcnow()
        db.session.commit()
        return pergunta
    
    @staticmethod
    def deletar_pergunta(pergunta_id):
        """
        Deleta uma pergunta de feedback (soft delete).
        
        Args:
            pergunta_id: ID da pergunta
        """
        pergunta = PerguntaFeedback.query.get_or_404(pergunta_id)
        pergunta.ativa = False
        pergunta.updated_at = datetime.utcnow()
        db.session.commit()
    
    @staticmethod
    def reordenar_perguntas(pergunta_ids):
        """
        Reordena perguntas de feedback.
        
        Args:
            pergunta_ids: Lista de IDs na nova ordem
        """
        for i, pergunta_id in enumerate(pergunta_ids):
            pergunta = PerguntaFeedback.query.get(pergunta_id)
            if pergunta:
                pergunta.ordem = i
                pergunta.updated_at = datetime.utcnow()
        
        db.session.commit()
    
    @staticmethod
    def criar_sessao_feedback(usuario_id, oficina_id, expires_hours=24):
        """
        Cria uma sessão de feedback para um usuário.
        
        Args:
            usuario_id: ID do usuário
            oficina_id: ID da oficina
            expires_hours: Horas até expirar
            
        Returns:
            FeedbackSession: Objeto da sessão criada
        """
        # Verificar se o usuário está inscrito na oficina
        inscricao = Inscricao.query.filter_by(
            usuario_id=usuario_id,
            oficina_id=oficina_id
        ).first()
        
        if not inscricao:
            raise ValueError("Usuário não está inscrito nesta oficina")
        
        # Gerar token único
        token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        
        # Verificar se já existe sessão ativa
        sessao_existente = FeedbackSession.query.filter_by(
            usuario_id=usuario_id,
            oficina_id=oficina_id,
            ativa=True
        ).first()
        
        if sessao_existente:
            sessao_existente.ativa = False
            sessao_existente.updated_at = datetime.utcnow()
        
        # Criar nova sessão
        sessao = FeedbackSession(
            token=token,
            usuario_id=usuario_id,
            oficina_id=oficina_id,
            expires_at=datetime.utcnow() + timedelta(hours=expires_hours)
        )
        
        db.session.add(sessao)
        db.session.commit()
        return sessao
    
    @staticmethod
    def validar_sessao_feedback(token):
        """
        Valida uma sessão de feedback.
        
        Args:
            token: Token da sessão
            
        Returns:
            FeedbackSession: Objeto da sessão se válida, None caso contrário
        """
        sessao = FeedbackSession.query.filter_by(token=token).first()
        
        if sessao and sessao.is_valid():
            return sessao
        
        return None
    
    @staticmethod
    def salvar_respostas(token, respostas):
        """
        Salva respostas de feedback.
        
        Args:
            token: Token da sessão
            respostas: Dicionário com pergunta_id: resposta
            
        Returns:
            List[RespostaFeedback]: Lista de respostas salvas
        """
        sessao = FeedbackSession.query.filter_by(token=token).first()
        
        if not sessao or not sessao.is_valid():
            raise ValueError("Sessão inválida ou expirada")
        
        if sessao.respondida:
            raise ValueError("Feedback já foi respondido")
        
        respostas_salvas = []
        
        for pergunta_id, resposta in respostas.items():
            pergunta = PerguntaFeedback.query.get(pergunta_id)
            
            if not pergunta or not pergunta.ativa:
                continue
            
            # Verificar se já existe resposta
            resposta_existente = RespostaFeedback.query.filter_by(
                pergunta_id=pergunta_id,
                usuario_id=sessao.usuario_id,
                oficina_id=sessao.oficina_id
            ).first()
            
            if resposta_existente:
                # Atualizar resposta existente
                resposta_obj = resposta_existente
            else:
                # Criar nova resposta
                resposta_obj = RespostaFeedback(
                    pergunta_id=pergunta_id,
                    usuario_id=sessao.usuario_id,
                    oficina_id=sessao.oficina_id
                )
                db.session.add(resposta_obj)
            
            # Salvar resposta baseada no tipo
            if pergunta.tipo.value == 'texto_livre':
                resposta_obj.resposta_texto = resposta
            elif pergunta.tipo.value == 'escala_numerica':
                resposta_obj.resposta_numerica = int(resposta)
            elif pergunta.tipo.value in ['multipla_escolha', 'sim_nao']:
                resposta_obj.resposta_escolha = resposta
            
            resposta_obj.updated_at = datetime.utcnow()
            respostas_salvas.append(resposta_obj)
        
        # Marcar sessão como respondida
        sessao.respondida = True
        sessao.updated_at = datetime.utcnow()
        
        db.session.commit()
        return respostas_salvas

    @staticmethod
    def salvar_respostas_publico(oficina_id, respostas):
        respostas_salvas = []

        for pergunta_id, resposta in respostas.items():
            pergunta = PerguntaFeedback.query.get(pergunta_id)
            if not pergunta or not pergunta.ativa:
                continue

            resposta_obj = RespostaFeedback(
                pergunta_id=pergunta_id,
                usuario_id=None,
                oficina_id=oficina_id,
            )
            db.session.add(resposta_obj)

            if pergunta.tipo.value == 'texto_livre':
                resposta_obj.resposta_texto = resposta
            elif pergunta.tipo.value == 'escala_numerica':
                resposta_obj.resposta_numerica = int(resposta)
            elif pergunta.tipo.value in ['multipla_escolha', 'sim_nao']:
                resposta_obj.resposta_escolha = resposta

            resposta_obj.updated_at = datetime.utcnow()
            respostas_salvas.append(resposta_obj)

        db.session.commit()
        return respostas_salvas
    
    @staticmethod
    def obter_respostas_oficina(oficina_id):
        """
        Obtém todas as respostas de feedback de uma oficina.
        
        Args:
            oficina_id: ID da oficina
            
        Returns:
            List[RespostaFeedback]: Lista de respostas
        """
        return RespostaFeedback.query.filter_by(oficina_id=oficina_id).all()
    
    @staticmethod
    def obter_estatisticas_feedback(oficina_id):
        """
        Obtém estatísticas de feedback de uma oficina.
        
        Args:
            oficina_id: ID da oficina
            
        Returns:
            dict: Estatísticas do feedback
        """
        respostas = RespostaFeedback.query.filter_by(oficina_id=oficina_id).all()
        
        if not respostas:
            return {
                'total_respostas': 0,
                'perguntas_respondidas': 0,
                'taxa_resposta': 0
            }
        
        # Contar respostas por pergunta
        perguntas_respondidas = {}
        for resposta in respostas:
            if resposta.pergunta_id not in perguntas_respondidas:
                perguntas_respondidas[resposta.pergunta_id] = 0
            perguntas_respondidas[resposta.pergunta_id] += 1
        
        # Obter total de inscritos
        total_inscritos = Inscricao.query.filter_by(oficina_id=oficina_id).count()
        
        return {
            'total_respostas': len(respostas),
            'perguntas_respondidas': len(perguntas_respondidas),
            'taxa_resposta': (len(respostas) / max(total_inscritos, 1)) * 100,
            'respostas_por_pergunta': perguntas_respondidas
        }
