from models import Checkin, Oficina, Evento, CertificadoTemplate
from models.user import Cliente, Usuario
from models.review import ConfiguracaoCertificadoEvento
from models.certificado import (
    CertificadoConfig, CertificadoParticipante, NotificacaoCertificado,
    SolicitacaoCertificado, CertificadoTemplateAvancado
)
from models.event import ConfiguracaoCertificadoAvancada
from extensions import db
from sqlalchemy import func
from datetime import datetime
import hashlib
import os
from services.pdf_service import gerar_certificado_personalizado
from flask import current_app
import logging

logger = logging.getLogger(__name__)


def verificar_criterios_certificado(usuario_id, evento_id):
    """Verifica se o participante atende aos critérios de certificado."""
    config = ConfiguracaoCertificadoEvento.query.filter_by(evento_id=evento_id).first()
    if not config:
        return True, []

    pendencias = []

    total_checkins = Checkin.query.filter_by(usuario_id=usuario_id, evento_id=evento_id).count()
    if config.checkins_minimos and total_checkins < config.checkins_minimos:
        pendencias.append(f"Mínimo de {config.checkins_minimos} check-ins (atual {total_checkins})")

    for oficina_id in config.get_oficinas_obrigatorias_list():
        tem = Checkin.query.filter_by(usuario_id=usuario_id, oficina_id=oficina_id).first()
        if not tem:
            ofi = Oficina.query.get(oficina_id)
            pendencias.append(f"Participar da oficina '{ofi.titulo if ofi else oficina_id}'")

    if config.percentual_minimo:
        total_oficinas = Oficina.query.filter_by(evento_id=evento_id).count()
        if total_oficinas:
            presentes = (
                Checkin.query.join(Oficina, Checkin.oficina_id == Oficina.id)
                .filter(Checkin.usuario_id == usuario_id, Oficina.evento_id == evento_id)
                .with_entities(Checkin.oficina_id).distinct().count()
            )
            percentual = (presentes / total_oficinas) * 100
            if percentual < config.percentual_minimo:
                pendencias.append(f"Participação mínima de {config.percentual_minimo}% (atual {int(percentual)}%)")

    return len(pendencias) == 0, pendencias


def gerar_certificados_automaticos(evento_id):
    """Gera certificados automaticamente para participantes elegíveis."""
    try:
        config = CertificadoConfig.query.filter_by(evento_id=evento_id).first()
        if not config or not config.liberacao_automatica:
            logger.info(f"Geração automática desabilitada para evento {evento_id}")
            return []

        evento = Evento.query.get(evento_id)
        if not evento:
            logger.error(f"Evento {evento_id} não encontrado")
            return []

        # Buscar participantes elegíveis
        participantes_elegíveis = _buscar_participantes_elegiveis(evento_id, config)
        certificados_gerados = []

        for usuario_id in participantes_elegíveis:
            try:
                certificado = _gerar_certificado_participante(usuario_id, evento_id, config)
                if certificado:
                    certificados_gerados.append(certificado)
                    
                    # Enviar notificação se configurado
                    if config.notificar_participantes:
                        _criar_notificacao_certificado(usuario_id, evento_id, 'liberacao')
                        
            except Exception as e:
                logger.error(f"Erro ao gerar certificado para usuário {usuario_id}: {str(e)}")
                continue

        logger.info(f"Gerados {len(certificados_gerados)} certificados para evento {evento_id}")
        return certificados_gerados
        
    except Exception as e:
        logger.error(f"Erro na geração automática de certificados: {str(e)}")
        return []


def _buscar_participantes_elegiveis(evento_id, config):
    """Busca participantes que atendem aos critérios para certificado."""
    # Buscar todos os usuários que participaram do evento
    participantes = db.session.query(Checkin.usuario_id).filter(
        Checkin.evento_id == evento_id
    ).distinct().all()
    
    elegíveis = []
    for (usuario_id,) in participantes:
        # Verificar se já tem certificado
        certificado_existente = CertificadoParticipante.query.filter_by(
            usuario_id=usuario_id,
            evento_id=evento_id,
            tipo='geral'
        ).first()
        
        if certificado_existente:
            continue
            
        # Verificar critérios
        criterios_ok, _ = verificar_criterios_certificado(usuario_id, evento_id)
        if criterios_ok:
            elegíveis.append(usuario_id)
            
    return elegíveis


def _gerar_certificado_participante(usuario_id, evento_id, config):
    """Gera certificado individual para um participante."""
    try:
        usuario = Usuario.query.get(usuario_id)
        evento = Evento.query.get(evento_id)
        
        if not usuario or not evento:
            return None
            
        # Calcular carga horária
        carga_horaria = _calcular_carga_horaria_participante(usuario_id, evento_id)
        
        # Buscar template
        template = _buscar_template_certificado(evento.cliente_id)
        if not template:
            logger.warning(f"Nenhum template encontrado para cliente {evento.cliente_id}")
            return None
            
        # Gerar arquivo PDF
        arquivo_path = _gerar_arquivo_certificado(usuario, evento, carga_horaria, template)
        
        # Criar registro no banco
        certificado = CertificadoParticipante(
            usuario_id=usuario_id,
            evento_id=evento_id,
            tipo='geral',
            titulo=f"Certificado de Participação - {evento.nome}",
            carga_horaria=carga_horaria,
            liberado=True,
            data_liberacao=datetime.utcnow(),
            arquivo_path=arquivo_path,
            hash_verificacao=_gerar_hash_certificado(arquivo_path)
        )
        
        db.session.add(certificado)
        db.session.commit()
        
        return certificado
        
    except Exception as e:
        logger.error(f"Erro ao gerar certificado individual: {str(e)}")
        db.session.rollback()
        return None


def _calcular_carga_horaria_participante(usuario_id, evento_id):
    """Calcula a carga horária total do participante no evento."""
    oficinas_participadas = db.session.query(Oficina).join(
        Checkin, Oficina.id == Checkin.oficina_id
    ).filter(
        Checkin.usuario_id == usuario_id,
        Oficina.evento_id == evento_id
    ).all()

    return sum(oficina.carga_horaria or 0 for oficina in oficinas_participadas)


def calcular_atividades_participadas(usuario_id, evento_id, config=None):
    """Calcula todas as atividades que o usuário participou no evento."""
    oficinas_participadas = (
        db.session.query(Oficina.id, Oficina.titulo, Oficina.carga_horaria)
        .join(Checkin, Checkin.oficina_id == Oficina.id)
        .filter(
            Checkin.usuario_id == usuario_id,
            Oficina.evento_id == evento_id,
        )
        .all()
    )

    atividades = {
        "oficinas": [],
        "atividades_sem_inscricao": [],
        "total_horas": 0,
        "total_atividades": 0,
    }

    for oficina in oficinas_participadas:
        atividades["oficinas"].append(
            {
                "id": oficina.id,
                "titulo": oficina.titulo,
                "carga_horaria": int(oficina.carga_horaria),
                "tipo": "oficina",
            }
        )
        atividades["total_horas"] += int(oficina.carga_horaria)

    if config and getattr(config, "incluir_atividades_sem_inscricao", False):
        checkins_extras = (
            db.session.query(Checkin)
            .filter(
                Checkin.usuario_id == usuario_id,
                Checkin.evento_id == evento_id,
                Checkin.oficina_id.is_(None),
            )
            .all()
        )

        for checkin in checkins_extras:
            if checkin.palavra_chave and "ATIVIDADE" in checkin.palavra_chave:
                atividades["atividades_sem_inscricao"].append(
                    {
                        "titulo": checkin.palavra_chave.replace("ATIVIDADE-", ""),
                        "carga_horaria": 2,
                        "tipo": "atividade_extra",
                    }
                )
                atividades["total_horas"] += 2

    atividades["total_atividades"] = len(atividades["oficinas"]) + len(
        atividades["atividades_sem_inscricao"]
    )

    return atividades


def _buscar_template_certificado(cliente_id):
    """Busca template ativo para certificados."""
    # Primeiro tenta template avançado
    template_avancado = CertificadoTemplateAvancado.query.filter_by(
        cliente_id=cliente_id,
        ativo=True,
        tipo='geral'
    ).first()
    
    if template_avancado:
        return template_avancado
        
    # Fallback para template simples
    template_simples = CertificadoTemplate.query.filter_by(
        cliente_id=cliente_id,
        ativo=True
    ).first()
    
    return template_simples


def _gerar_arquivo_certificado(usuario, evento, carga_horaria, template):
    """Gera o arquivo PDF do certificado."""
    try:
        # Criar diretório se não existir
        certificados_dir = os.path.join(current_app.static_folder, 'certificados')
        os.makedirs(certificados_dir, exist_ok=True)
        
        # Nome do arquivo
        filename = f"certificado_{usuario.id}_{evento.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        arquivo_path = os.path.join(certificados_dir, filename)
        
        # Gerar PDF usando o serviço existente
        if hasattr(template, 'conteudo_html'):
            # Template avançado
            conteudo = template.conteudo_html
        else:
            # Template simples
            conteudo = template.conteudo
            
        # Buscar oficinas participadas
        oficinas = db.session.query(Oficina).join(
            Checkin, Oficina.id == Checkin.oficina_id
        ).filter(
            Checkin.usuario_id == usuario.id,
            Oficina.evento_id == evento.id
        ).all()
        
        # Gerar certificado personalizado
        pdf_path = gerar_certificado_personalizado(
            usuario, oficinas, carga_horaria, '', conteudo, evento.cliente
        )
        
        # Mover para local definitivo
        if pdf_path != arquivo_path:
            os.rename(pdf_path, arquivo_path)
            
        return f"certificados/{filename}"
        
    except Exception as e:
        logger.error(f"Erro ao gerar arquivo de certificado: {str(e)}")
        return None


def _gerar_hash_certificado(arquivo_path):
    """Gera hash para validação do certificado."""
    try:
        if not arquivo_path or not os.path.exists(arquivo_path):
            return None
            
        with open(arquivo_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return None


def _criar_notificacao_certificado(usuario_id, evento_id, tipo):
    """Cria notificação sobre certificado."""
    try:
        evento = Evento.query.get(evento_id)
        
        mensagens = {
            'liberacao': f"Seu certificado do evento '{evento.nome}' está disponível para download!",
            'aprovacao': f"Sua solicitação de certificado para '{evento.nome}' foi aprovada!",
            'rejeicao': f"Sua solicitação de certificado para '{evento.nome}' foi rejeitada."
        }
        
        notificacao = NotificacaoCertificado(
            usuario_id=usuario_id,
            evento_id=evento_id,
            tipo=tipo,
            titulo=f"Certificado - {evento.nome}",
            mensagem=mensagens.get(tipo, "Atualização sobre seu certificado")
        )
        
        db.session.add(notificacao)
        db.session.commit()
        
    except Exception as e:
        logger.error(f"Erro ao criar notificação: {str(e)}")
        db.session.rollback()


def processar_solicitacoes_pendentes():
    """Processa solicitações de certificados pendentes."""
    try:
        solicitacoes = SolicitacaoCertificado.query.filter_by(status='pendente').all()
        processadas = 0
        
        for solicitacao in solicitacoes:
            try:
                # Verificar se atende aos critérios
                criterios_ok, pendencias = verificar_criterios_certificado(
                    solicitacao.usuario_id, solicitacao.evento_id
                )
                
                if criterios_ok:
                    # Aprovar automaticamente se configurado
                    config = CertificadoConfig.query.filter_by(
                        evento_id=solicitacao.evento_id
                    ).first()
                    
                    if config and config.aprovacao_automatica_se_criterios:
                        solicitacao.status = 'aprovada'
                        solicitacao.data_resposta = datetime.utcnow()
                        
                        # Gerar certificado
                        _gerar_certificado_participante(
                            solicitacao.usuario_id, 
                            solicitacao.evento_id, 
                            config
                        )
                        
                        # Notificar
                        _criar_notificacao_certificado(
                            solicitacao.usuario_id, 
                            solicitacao.evento_id, 
                            'aprovacao'
                        )
                        
                        processadas += 1
                        
            except Exception as e:
                logger.error(f"Erro ao processar solicitação {solicitacao.id}: {str(e)}")
                continue
                
        db.session.commit()
        logger.info(f"Processadas {processadas} solicitações de certificados")
        return processadas
        
    except Exception as e:
        logger.error(f"Erro ao processar solicitações: {str(e)}")
        db.session.rollback()
        return 0
