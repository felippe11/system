import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from flask import current_app
from models import LembreteOficina, StatusLembrete, TipoLembrete, db
from services.email_service import EmailService

logger = logging.getLogger(__name__)

# Scheduler global
scheduler = None


def init_scheduler(app):
    """Inicializa o scheduler de lembretes."""
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler já foi inicializado")
        return scheduler
    
    scheduler = BackgroundScheduler()
    scheduler.start()
    
    # Adicionar job para verificar lembretes automáticos a cada hora
    scheduler.add_job(
        verificar_lembretes_automaticos,
        'cron',
        minute=0,  # Executar no início de cada hora
        args=[app],
        id='verificar_lembretes_automaticos',
        replace_existing=True
    )
    
    logger.info("Scheduler de lembretes inicializado")
    return scheduler


def verificar_lembretes_automaticos(app):
    """Verifica e processa lembretes automáticos pendentes."""
    with app.app_context():
        try:
            logger.info("Verificando lembretes automáticos...")
            
            # Buscar lembretes automáticos pendentes
            lembretes_pendentes = LembreteOficina.query.filter(
                LembreteOficina.tipo == TipoLembrete.AUTOMATICO,
                LembreteOficina.status == StatusLembrete.PENDENTE
            ).all()
            
            logger.info(f"Encontrados {len(lembretes_pendentes)} lembretes automáticos pendentes")
            
            for lembrete in lembretes_pendentes:
                try:
                    processar_lembrete_automatico(lembrete)
                except Exception as e:
                    logger.error(f"Erro ao processar lembrete {lembrete.id}: {e}")
                    lembrete.status = StatusLembrete.FALHOU
                    db.session.commit()
            
            logger.info("Verificação de lembretes automáticos concluída")
            
        except Exception as e:
            logger.error(f"Erro na verificação de lembretes automáticos: {e}")


def processar_lembrete_automatico(lembrete):
    """Processa um lembrete automático específico."""
    logger.info(f"Processando lembrete automático {lembrete.id}: {lembrete.titulo}")
    
    # Verificar se deve ser enviado agora
    if not deve_enviar_agora(lembrete):
        logger.info(f"Lembrete {lembrete.id} ainda não deve ser enviado")
        return
    
    # Processar envio
    from routes.reminder_routes import processar_lembrete_manual
    processar_lembrete_manual(lembrete.id)
    
    logger.info(f"Lembrete automático {lembrete.id} processado com sucesso")


def deve_enviar_agora(lembrete):
    """Verifica se um lembrete automático deve ser enviado agora."""
    agora = datetime.utcnow()
    
    # Se tem data específica agendada
    if lembrete.data_envio_agendada:
        return agora >= lembrete.data_envio_agendada
    
    # Se tem dias de antecedência definidos
    if lembrete.dias_antecedencia:
        # Buscar oficinas do lembrete
        oficinas = obter_oficinas_lembrete(lembrete)
        
        for oficina in oficinas:
            if oficina.data_inicio:
                data_limite = oficina.data_inicio - timedelta(days=lembrete.dias_antecedencia)
                if agora >= data_limite:
                    return True
    
    return False


def obter_oficinas_lembrete(lembrete):
    """Obtém as oficinas relacionadas a um lembrete."""
    from models import Oficina
    import json
    
    if lembrete.enviar_todas_oficinas:
        # Todas as oficinas do cliente
        return Oficina.query.filter_by(cliente_id=lembrete.cliente_id).all()
    else:
        # Oficinas específicas
        oficina_ids = json.loads(lembrete.oficina_ids) if lembrete.oficina_ids else []
        return Oficina.query.filter(Oficina.id.in_(oficina_ids)).all()


def agendar_lembrete_especifico(lembrete):
    """Agenda um lembrete para uma data específica."""
    global scheduler
    
    if scheduler is None:
        logger.error("Scheduler não foi inicializado")
        return False
    
    try:
        # Se tem data específica, agendar para essa data
        if lembrete.data_envio_agendada:
            scheduler.add_job(
                processar_lembrete_automatico,
                DateTrigger(run_date=lembrete.data_envio_agendada),
                args=[lembrete],
                id=f'lembrete_especifico_{lembrete.id}',
                replace_existing=True
            )
            logger.info(f"Lembrete {lembrete.id} agendado para {lembrete.data_envio_agendada}")
            return True
        
        # Se tem dias de antecedência, calcular data baseada nas oficinas
        if lembrete.dias_antecedencia:
            oficinas = obter_oficinas_lembrete(lembrete)
            
            for oficina in oficinas:
                if oficina.data_inicio:
                    data_envio = oficina.data_inicio - timedelta(days=lembrete.dias_antecedencia)
                    
                    # Só agendar se a data for no futuro
                    if data_envio > datetime.utcnow():
                        scheduler.add_job(
                            processar_lembrete_automatico,
                            DateTrigger(run_date=data_envio),
                            args=[lembrete],
                            id=f'lembrete_oficina_{lembrete.id}_{oficina.id}',
                            replace_existing=True
                        )
                        logger.info(f"Lembrete {lembrete.id} agendado para oficina {oficina.id} em {data_envio}")
            
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Erro ao agendar lembrete {lembrete.id}: {e}")
        return False


def cancelar_lembrete_agendado(lembrete_id):
    """Cancela jobs agendados para um lembrete."""
    global scheduler
    
    if scheduler is None:
        return
    
    try:
        # Remover jobs relacionados ao lembrete
        jobs_removidos = 0
        
        # Job específico do lembrete
        job_id = f'lembrete_especifico_{lembrete_id}'
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            jobs_removidos += 1
        
        # Jobs de oficinas específicas
        for job in scheduler.get_jobs():
            if f'lembrete_oficina_{lembrete_id}_' in job.id:
                scheduler.remove_job(job.id)
                jobs_removidos += 1
        
        logger.info(f"Removidos {jobs_removidos} jobs agendados para lembrete {lembrete_id}")
        
    except Exception as e:
        logger.error(f"Erro ao cancelar jobs do lembrete {lembrete_id}: {e}")


def get_scheduler_status():
    """Retorna status do scheduler."""
    global scheduler
    
    if scheduler is None:
        return {'status': 'not_initialized', 'jobs': 0}
    
    try:
        jobs = scheduler.get_jobs()
        return {
            'status': 'running',
            'jobs': len(jobs),
            'job_details': [
                {
                    'id': job.id,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                }
                for job in jobs
            ]
        }
    except Exception as e:
        logger.error(f"Erro ao obter status do scheduler: {e}")
        return {'status': 'error', 'error': str(e)}


def shutdown_scheduler():
    """Para o scheduler."""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler de lembretes finalizado")
