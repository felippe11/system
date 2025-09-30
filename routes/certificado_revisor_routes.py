"""Rotas para gerenciamento de certificados de revisores.

Este módulo permite que clientes configurem e liberem certificados para revisores,
bem como que revisores visualizem e baixem seus certificados.
"""

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    send_file,
    current_app,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
from sqlalchemy import func, and_, or_

from extensions import db
from models import (
    CertificadoRevisorConfig,
    CertificadoRevisor,
    Usuario,
    Cliente,
    Evento,
    RevisorCandidatura,
    RevisorProcess,
    Assignment,
    RespostaFormulario,
)
from services.pdf_service import gerar_certificado_revisor_pdf
from services.email_service import EmailService
from utils.auth import cliente_required, admin_required
from utils import endpoints

certificado_revisor_routes = Blueprint(
    'certificado_revisor_routes',
    __name__,
    template_folder="../templates/certificado_revisor"
)

ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.pdf'}
ALLOWED_MIME_TYPES = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.pdf': 'application/pdf',
}


@certificado_revisor_routes.route('/certificado_revisor/configurar/<int:evento_id>')
@login_required
@cliente_required
def configurar_certificado_revisor(evento_id):
    """Página de configuração de certificados para revisores."""
    evento = Evento.query.get_or_404(evento_id)
    
    # Verificar se o evento pertence ao cliente
    if evento.cliente_id != current_user.id:
        flash('Acesso negado!', 'danger')
        return redirect(url_for(endpoints.DASHBOARD))
    
    # Buscar ou criar configuração
    config = CertificadoRevisorConfig.query.filter_by(
        cliente_id=current_user.id,
        evento_id=evento_id
    ).first()
    
    if not config:
        config = CertificadoRevisorConfig(
            cliente_id=current_user.id,
            evento_id=evento_id,
            titulo_certificado=f"Certificado de Revisor - {evento.nome}",
            texto_certificado=f"Certificamos que {{nome_revisor}} atuou como revisor de trabalhos no evento '{evento.nome}', contribuindo para a avaliação e seleção de trabalhos científicos.",
        )
        db.session.add(config)
        db.session.commit()
    
    # Buscar revisores aprovados para este evento
    revisores_aprovados = _get_revisores_aprovados(evento_id)
    
    # Debug: Log das informações
    current_app.logger.info(f"Evento: {evento.nome} (ID: {evento.id})")
    current_app.logger.info(f"Cliente: {current_user.nome} (ID: {current_user.id})")
    current_app.logger.info(f"Revisores aprovados encontrados: {len(revisores_aprovados)}")
    
    # Buscar certificados existentes para este evento
    certificados_existentes = CertificadoRevisor.query.filter_by(
        cliente_id=current_user.id,
        evento_id=evento_id
    ).all()
    
    current_app.logger.info(f"Certificados existentes: {len(certificados_existentes)}")
    
    return render_template(
        'certificado_revisor/configurar.html',
        evento=evento,
        config=config,
        revisores_aprovados=revisores_aprovados,
        certificados_existentes=certificados_existentes
    )


@certificado_revisor_routes.route('/certificado_revisor/salvar_config', methods=['POST'])
@login_required
@cliente_required
def salvar_config_certificado_revisor():
    """Salva a configuração do certificado de revisor."""
    evento_id = request.form.get('evento_id')
    titulo = request.form.get('titulo_certificado')
    texto = request.form.get('texto_certificado')
    liberacao_automatica = request.form.get('liberacao_automatica') == 'on'
    trabalhos_minimos = int(request.form.get('trabalhos_minimos', 1))
    incluir_assinatura_cliente = request.form.get('incluir_assinatura_cliente') == 'on'
    
    evento = Evento.query.get_or_404(evento_id)
    
    # Verificar se o evento pertence ao cliente
    if evento.cliente_id != current_user.id:
        flash('Acesso negado!', 'danger')
        return redirect(url_for(endpoints.DASHBOARD))
    
    # Buscar ou criar configuração
    config = CertificadoRevisorConfig.query.filter_by(
        cliente_id=current_user.id,
        evento_id=evento_id
    ).first()
    
    if not config:
        config = CertificadoRevisorConfig(
            cliente_id=current_user.id,
            evento_id=evento_id
        )
        db.session.add(config)
    
    # Atualizar configuração
    config.titulo_certificado = titulo
    config.texto_certificado = texto
    config.liberacao_automatica = liberacao_automatica
    config.criterio_trabalhos_minimos = trabalhos_minimos
    config.incluir_assinatura_cliente = incluir_assinatura_cliente
    
    # Processar upload de fundo
    if 'fundo_certificado' in request.files:
        arquivo = request.files['fundo_certificado']
        if arquivo and arquivo.filename:
            filename = secure_filename(arquivo.filename)
            ext = os.path.splitext(filename)[1].lower()
            
            if ext in ALLOWED_EXTENSIONS:
                unique_name = f"{uuid.uuid4().hex}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{ext}"
                dir_path = os.path.join('static', 'uploads', 'certificados_revisor')
                os.makedirs(dir_path, exist_ok=True)
                path = os.path.join(dir_path, unique_name)
                arquivo.save(path)
                config.fundo_certificado = f"uploads/certificados_revisor/{unique_name}"
    
    db.session.commit()
    flash('Configuração salva com sucesso!', 'success')
    
    return redirect(url_for('certificado_revisor_routes.configurar_certificado_revisor', evento_id=evento_id))


@certificado_revisor_routes.route('/certificado_revisor/liberar_individual/<int:revisor_id>/<int:evento_id>')
@login_required
@cliente_required
def liberar_certificado_individual(revisor_id, evento_id):
    """Libera certificado individual para um revisor."""
    evento = Evento.query.get_or_404(evento_id)
    
    # Verificar se o evento pertence ao cliente
    if evento.cliente_id != current_user.id:
        flash('Acesso negado!', 'danger')
        return redirect(url_for(endpoints.DASHBOARD))
    
    revisor = Usuario.query.get_or_404(revisor_id)
    
    # Verificar se o revisor tem candidatura aprovada
    candidatura = _verificar_candidatura_aprovada(revisor_id, evento_id)
    if not candidatura:
        flash('Revisor não possui candidatura aprovada para este evento.', 'danger')
        return redirect(url_for('certificado_revisor_routes.configurar_certificado_revisor', evento_id=evento_id))
    
    # Buscar configuração
    config = CertificadoRevisorConfig.query.filter_by(
        cliente_id=current_user.id,
        evento_id=evento_id
    ).first()
    
    if not config:
        flash('Configure primeiro o certificado de revisor.', 'danger')
        return redirect(url_for('certificado_revisor_routes.configurar_certificado_revisor', evento_id=evento_id))
    
    # Buscar ou criar certificado
    certificado = CertificadoRevisor.query.filter_by(
        revisor_id=revisor_id,
        cliente_id=current_user.id,
        evento_id=evento_id
    ).first()
    
    if not certificado:
        # Calcular estatísticas do revisor
        trabalhos_revisados = _calcular_trabalhos_revisados(revisor_id, evento_id)
        
        certificado = CertificadoRevisor(
            revisor_id=revisor_id,
            cliente_id=current_user.id,
            evento_id=evento_id,
            titulo=config.titulo_certificado,
            texto_personalizado=config.texto_certificado,
            fundo_personalizado=config.fundo_certificado,
            trabalhos_revisados=trabalhos_revisados,
        )
        db.session.add(certificado)
    
    # Liberar certificado
    certificado.liberado = True
    certificado.data_liberacao = datetime.utcnow()
    certificado.liberado_por = None  # Cliente liberando, não um usuário específico
    
    db.session.commit()
    
    flash(f'Certificado liberado para {revisor.nome}!', 'success')
    return redirect(url_for('certificado_revisor_routes.configurar_certificado_revisor', evento_id=evento_id))


@certificado_revisor_routes.route('/certificado_revisor/liberar_todos/<int:evento_id>')
@login_required
@cliente_required
def liberar_certificados_todos(evento_id):
    """Libera certificados para todos os revisores aprovados."""
    evento = Evento.query.get_or_404(evento_id)
    
    # Verificar se o evento pertence ao cliente
    if evento.cliente_id != current_user.id:
        flash('Acesso negado!', 'danger')
        return redirect(url_for(endpoints.DASHBOARD))
    
    # Buscar configuração
    config = CertificadoRevisorConfig.query.filter_by(
        cliente_id=current_user.id,
        evento_id=evento_id
    ).first()
    
    if not config:
        flash('Configure primeiro o certificado de revisor.', 'danger')
        return redirect(url_for('certificado_revisor_routes.configurar_certificado_revisor', evento_id=evento_id))
    
    # Buscar revisores aprovados
    revisores_aprovados = _get_revisores_aprovados(evento_id)
    
    liberados = 0
    for revisor in revisores_aprovados:
        # Verificar se já tem certificado liberado
        certificado_existente = CertificadoRevisor.query.filter_by(
            revisor_id=revisor.id,
            cliente_id=current_user.id,
            evento_id=evento_id,
            liberado=True
        ).first()
        
        if not certificado_existente:
            # Calcular estatísticas do revisor
            trabalhos_revisados = _calcular_trabalhos_revisados(revisor.id, evento_id)
            
            certificado = CertificadoRevisor(
                revisor_id=revisor.id,
                cliente_id=current_user.id,
                evento_id=evento_id,
                titulo=config.titulo_certificado,
                texto_personalizado=config.texto_certificado,
                fundo_personalizado=config.fundo_certificado,
                trabalhos_revisados=trabalhos_revisados,
                liberado=True,
                data_liberacao=datetime.utcnow(),
                liberado_por=None,  # Cliente liberando, não um usuário específico
            )
            db.session.add(certificado)
            liberados += 1
    
    db.session.commit()
    
    flash(f'Certificados liberados para {liberados} revisores!', 'success')
    return redirect(url_for('certificado_revisor_routes.configurar_certificado_revisor', evento_id=evento_id))


@certificado_revisor_routes.route('/certificado_revisor/download_publico/<codigo_candidatura>')
def download_certificado_publico(codigo_candidatura):
    """Download público de certificado usando código da candidatura (sem login)."""
    from models import RevisorCandidatura, Usuario
    
    # Buscar candidatura pelo código
    candidatura = RevisorCandidatura.query.filter_by(codigo=codigo_candidatura).first()
    if not candidatura:
        flash('Candidatura não encontrada!', 'danger')
        return redirect(url_for('evento_routes.home'))
    
    # Buscar usuário revisor
    revisor_user = Usuario.query.filter_by(email=candidatura.email).first()
    if not revisor_user:
        flash('Revisor não encontrado!', 'danger')
        return redirect(url_for('evento_routes.home'))
    
    # Buscar certificados liberados para este revisor
    certificados = CertificadoRevisor.query.filter_by(
        revisor_id=revisor_user.id,
        liberado=True
    ).order_by(CertificadoRevisor.data_liberacao.desc()).all()
    
    if not certificados:
        flash('Nenhum certificado liberado encontrado para este revisor!', 'warning')
        return redirect(url_for('revisor_routes.progress', codigo=codigo_candidatura))
    
    # Se houver apenas um certificado, baixar diretamente
    if len(certificados) == 1:
        certificado = certificados[0]
        try:
            # Gerar PDF se não existir
            if not certificado.arquivo_path or not os.path.exists(certificado.arquivo_path):
                pdf_path = gerar_certificado_revisor_pdf(certificado)
                certificado.arquivo_path = pdf_path
                db.session.commit()
            
            return send_file(
                certificado.arquivo_path, 
                as_attachment=True, 
                download_name=f"certificado_revisor_{certificado.revisor.nome.replace(' ', '_')}.pdf"
            )
        except Exception as e:
            current_app.logger.error(f"Erro ao gerar PDF do certificado: {e}")
            flash('Erro ao gerar certificado. Tente novamente.', 'danger')
            return redirect(url_for('revisor_routes.progress', codigo=codigo_candidatura))
    
    # Se houver múltiplos certificados, mostrar página de seleção
    return render_template(
        'certificado_revisor/selecionar_certificado.html',
        candidatura=candidatura,
        certificados=certificados,
        codigo_candidatura=codigo_candidatura
    )


@certificado_revisor_routes.route('/certificado_revisor/download_especifico/<int:certificado_id>/<codigo_candidatura>')
def download_certificado_especifico(certificado_id, codigo_candidatura):
    """Download de certificado específico usando código da candidatura (sem login)."""
    from models import RevisorCandidatura, Usuario
    
    # Buscar candidatura pelo código
    candidatura = RevisorCandidatura.query.filter_by(codigo=codigo_candidatura).first()
    if not candidatura:
        flash('Candidatura não encontrada!', 'danger')
        return redirect(url_for('evento_routes.home'))
    
    # Buscar certificado
    certificado = CertificadoRevisor.query.get_or_404(certificado_id)
    
    # Verificar se o certificado pertence ao revisor da candidatura
    revisor_user = Usuario.query.filter_by(email=candidatura.email).first()
    if not revisor_user or certificado.revisor_id != revisor_user.id:
        flash('Acesso negado!', 'danger')
        return redirect(url_for('evento_routes.home'))
    
    # Verificar se está liberado
    if not certificado.liberado:
        flash('Certificado ainda não foi liberado!', 'danger')
        return redirect(url_for('revisor_routes.progress', codigo=codigo_candidatura))
    
    try:
        # Gerar PDF se não existir
        if not certificado.arquivo_path or not os.path.exists(certificado.arquivo_path):
            pdf_path = gerar_certificado_revisor_pdf(certificado)
            certificado.arquivo_path = pdf_path
            db.session.commit()
        
        return send_file(
            certificado.arquivo_path, 
            as_attachment=True, 
            download_name=f"certificado_revisor_{certificado.revisor.nome.replace(' ', '_')}.pdf"
        )
        
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar PDF do certificado: {e}")
        flash('Erro ao gerar certificado. Tente novamente.', 'danger')
        return redirect(url_for('revisor_routes.progress', codigo=codigo_candidatura))


@certificado_revisor_routes.route('/certificado_revisor/gerar_pdf/<int:certificado_id>')
@login_required
def gerar_pdf_certificado_revisor(certificado_id):
    """Gera e retorna o PDF do certificado do revisor."""
    certificado = CertificadoRevisor.query.get_or_404(certificado_id)
    
    # Verificar permissão
    if current_user.tipo == 'cliente':
        if certificado.cliente_id != current_user.id:
            flash('Acesso negado!', 'danger')
            return redirect(url_for(endpoints.DASHBOARD))
    elif current_user.tipo == 'revisor':
        if certificado.revisor_id != current_user.id:
            flash('Acesso negado!', 'danger')
            return redirect(url_for(endpoints.DASHBOARD))
    else:
        flash('Acesso negado!', 'danger')
        return redirect(url_for(endpoints.DASHBOARD))
    
    # Verificar se está liberado
    if not certificado.liberado:
        flash('Certificado ainda não foi liberado!', 'danger')
        return redirect(url_for(endpoints.DASHBOARD))
    
    try:
        # Gerar PDF
        pdf_path = gerar_certificado_revisor_pdf(certificado)
        
        # Atualizar caminho do arquivo
        certificado.arquivo_path = pdf_path
        db.session.commit()
        
        return send_file(pdf_path, as_attachment=True, download_name=f"certificado_revisor_{certificado.revisor.nome.replace(' ', '_')}.pdf")
        
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar PDF do certificado: {e}")
        flash('Erro ao gerar certificado. Tente novamente.', 'danger')
        return redirect(url_for(endpoints.DASHBOARD))


@certificado_revisor_routes.route('/certificado_revisor/enviar_email/<int:certificado_id>')
@login_required
@cliente_required
def enviar_email_certificado_revisor(certificado_id):
    """Envia certificado por email para o revisor."""
    certificado = CertificadoRevisor.query.get_or_404(certificado_id)
    
    # Verificar se o certificado pertence ao cliente
    if certificado.cliente_id != current_user.id:
        flash('Acesso negado!', 'danger')
        return redirect(url_for(endpoints.DASHBOARD))
    
    # Verificar se está liberado
    if not certificado.liberado:
        flash('Certificado ainda não foi liberado!', 'danger')
        return redirect(url_for('certificado_revisor_routes.configurar_certificado_revisor', evento_id=certificado.evento_id))
    
    try:
        # Gerar PDF se não existir
        if not certificado.arquivo_path or not os.path.exists(certificado.arquivo_path):
            pdf_path = gerar_certificado_revisor_pdf(certificado)
            certificado.arquivo_path = pdf_path
            db.session.commit()
        
        # Enviar email
        email_service = EmailService()
        sucesso = email_service.enviar_certificado_revisor(certificado)
        
        if sucesso:
            flash('Certificado enviado por email com sucesso!', 'success')
        else:
            flash('Erro ao enviar email. Tente novamente.', 'danger')
            
    except Exception as e:
        current_app.logger.error(f"Erro ao enviar email do certificado: {e}")
        flash('Erro ao enviar email. Tente novamente.', 'danger')
    
    return redirect(url_for('certificado_revisor_routes.configurar_certificado_revisor', evento_id=certificado.evento_id))


@certificado_revisor_routes.route('/certificado_revisor/enviar_todos_email/<int:evento_id>')
@login_required
@cliente_required
def enviar_todos_certificados_email(evento_id):
    """Envia certificados por email para todos os revisores."""
    evento = Evento.query.get_or_404(evento_id)
    
    # Verificar se o evento pertence ao cliente
    if evento.cliente_id != current_user.id:
        flash('Acesso negado!', 'danger')
        return redirect(url_for(endpoints.DASHBOARD))
    
    # Buscar certificados liberados
    certificados = CertificadoRevisor.query.filter_by(
        cliente_id=current_user.id,
        evento_id=evento_id,
        liberado=True
    ).all()
    
    enviados = 0
    erros = 0
    
    email_service = EmailService()
    
    for certificado in certificados:
        try:
            # Gerar PDF se não existir
            if not certificado.arquivo_path or not os.path.exists(certificado.arquivo_path):
                pdf_path = gerar_certificado_revisor_pdf(certificado)
                certificado.arquivo_path = pdf_path
            
            # Enviar email
            sucesso = email_service.enviar_certificado_revisor(certificado)
            if sucesso:
                enviados += 1
            else:
                erros += 1
                
        except Exception as e:
            current_app.logger.error(f"Erro ao enviar email do certificado {certificado.id}: {e}")
            erros += 1
    
    db.session.commit()
    
    if enviados > 0:
        flash(f'Certificados enviados para {enviados} revisores!', 'success')
    if erros > 0:
        flash(f'Erro ao enviar {erros} certificados.', 'warning')
    
    return redirect(url_for('certificado_revisor_routes.configurar_certificado_revisor', evento_id=evento_id))


@certificado_revisor_routes.route('/certificado_revisor/gerar_todos_pdfs/<int:evento_id>')
@login_required
@cliente_required
def gerar_todos_pdfs(evento_id):
    """Gera PDFs para todos os certificados liberados."""
    evento = Evento.query.get_or_404(evento_id)
    
    # Verificar se o evento pertence ao cliente
    if evento.cliente_id != current_user.id:
        flash('Acesso negado!', 'danger')
        return redirect(url_for(endpoints.DASHBOARD))
    
    # Buscar certificados liberados
    certificados = CertificadoRevisor.query.filter_by(
        cliente_id=current_user.id,
        evento_id=evento_id,
        liberado=True
    ).all()
    
    gerados = 0
    erros = 0
    
    for certificado in certificados:
        try:
            # Gerar PDF se não existir
            if not certificado.arquivo_path or not os.path.exists(certificado.arquivo_path):
                pdf_path = gerar_certificado_revisor_pdf(certificado)
                certificado.arquivo_path = pdf_path
                gerados += 1
                
        except Exception as e:
            current_app.logger.error(f"Erro ao gerar PDF do certificado {certificado.id}: {e}")
            erros += 1
    
    db.session.commit()
    
    if gerados > 0:
        flash(f'PDFs gerados para {gerados} certificados!', 'success')
    if erros > 0:
        flash(f'Erro ao gerar {erros} PDFs.', 'warning')
    
    return redirect(url_for('certificado_revisor_routes.configurar_certificado_revisor', evento_id=evento_id))


@certificado_revisor_routes.route('/certificado_revisor/download_lote/<int:evento_id>')
@login_required
@cliente_required
def download_lote_certificados(evento_id):
    """Faz download em lote de todos os certificados liberados."""
    import zipfile
    import tempfile
    import io
    
    evento = Evento.query.get_or_404(evento_id)
    
    # Verificar se o evento pertence ao cliente
    if evento.cliente_id != current_user.id:
        flash('Acesso negado!', 'danger')
        return redirect(url_for(endpoints.DASHBOARD))
    
    # Buscar certificados liberados
    certificados = CertificadoRevisor.query.filter_by(
        cliente_id=current_user.id,
        evento_id=evento_id,
        liberado=True
    ).all()
    
    if not certificados:
        flash('Nenhum certificado liberado encontrado!', 'warning')
        return redirect(url_for('certificado_revisor_routes.configurar_certificado_revisor', evento_id=evento_id))
    
    # Criar arquivo ZIP em memória
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for certificado in certificados:
            try:
                # Gerar PDF se não existir
                if not certificado.arquivo_path or not os.path.exists(certificado.arquivo_path):
                    pdf_path = gerar_certificado_revisor_pdf(certificado)
                    certificado.arquivo_path = pdf_path
                
                # Ler arquivo PDF
                if os.path.exists(certificado.arquivo_path):
                    with open(certificado.arquivo_path, 'rb') as pdf_file:
                        pdf_content = pdf_file.read()
                        
                    # Nome do arquivo no ZIP
                    nome_arquivo = f"certificado_{certificado.revisor.nome.replace(' ', '_')}.pdf"
                    
                    # Adicionar ao ZIP
                    zip_file.writestr(nome_arquivo, pdf_content)
                    
            except Exception as e:
                current_app.logger.error(f"Erro ao processar certificado {certificado.id}: {e}")
                continue
    
    db.session.commit()
    
    # Preparar resposta
    zip_buffer.seek(0)
    
    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name=f"certificados_revisores_{evento.nome.replace(' ', '_')}.zip",
        mimetype='application/zip'
    )


@certificado_revisor_routes.route('/certificado_revisor/meus_certificados')
@login_required
def meus_certificados_revisor():
    """Página de certificados do revisor."""
    if current_user.tipo != 'revisor':
        flash('Acesso negado!', 'danger')
        return redirect(url_for(endpoints.DASHBOARD))
    
    # Buscar certificados liberados
    certificados = CertificadoRevisor.query.filter_by(
        revisor_id=current_user.id,
        liberado=True
    ).order_by(CertificadoRevisor.data_liberacao.desc()).all()
    
    return render_template(
        'certificado_revisor/meus_certificados.html',
        certificados=certificados
    )


# Funções auxiliares

def _get_revisores_aprovados(evento_id):
    """Busca revisores aprovados para um evento."""
    from models.review import revisor_process_evento_association
    
    # Debug: Verificar se existem processos para este evento
    processos_evento = db.session.query(RevisorProcess).join(
        revisor_process_evento_association,
        RevisorProcess.id == revisor_process_evento_association.c.revisor_process_id
    ).filter(
        revisor_process_evento_association.c.evento_id == evento_id
    ).all()
    
    current_app.logger.info(f"Processos encontrados para evento {evento_id}: {len(processos_evento)}")
    
    # Debug: Verificar candidaturas aprovadas
    candidaturas_aprovadas = RevisorCandidatura.query.join(
        RevisorProcess, RevisorCandidatura.process_id == RevisorProcess.id
    ).join(
        revisor_process_evento_association,
        RevisorProcess.id == revisor_process_evento_association.c.revisor_process_id
    ).filter(
        revisor_process_evento_association.c.evento_id == evento_id,
        RevisorCandidatura.status == 'aprovado'
    ).all()
    
    current_app.logger.info(f"Candidaturas aprovadas encontradas: {len(candidaturas_aprovadas)}")
    
    # Tentar abordagem alternativa: buscar diretamente por candidaturas aprovadas
    if not candidaturas_aprovadas:
        # Buscar candidaturas aprovadas sem join com evento
        candidaturas_gerais = RevisorCandidatura.query.filter(
            RevisorCandidatura.status == 'aprovado'
        ).all()
        
        current_app.logger.info(f"Candidaturas aprovadas gerais: {len(candidaturas_gerais)}")
        
        # Para cada candidatura, verificar se o processo está associado ao evento
        revisores_encontrados = []
        for candidatura in candidaturas_gerais:
            processo = RevisorProcess.query.get(candidatura.process_id)
            if processo and processo.eventos:
                for evento_processo in processo.eventos:
                    if evento_processo.id == evento_id:
                        # Buscar usuário por email
                        usuario = Usuario.query.filter_by(email=candidatura.email).first()
                        if usuario and usuario not in revisores_encontrados:
                            revisores_encontrados.append(usuario)
        
        current_app.logger.info(f"Revisores encontrados (método alternativo): {len(revisores_encontrados)}")
        return revisores_encontrados
    
    # Buscar revisores usando o método original
    revisores = db.session.query(Usuario).join(
        RevisorCandidatura, Usuario.email == RevisorCandidatura.email
    ).join(
        RevisorProcess, RevisorCandidatura.process_id == RevisorProcess.id
    ).join(
        revisor_process_evento_association, 
        RevisorProcess.id == revisor_process_evento_association.c.revisor_process_id
    ).filter(
        revisor_process_evento_association.c.evento_id == evento_id,
        RevisorCandidatura.status == 'aprovado'
    ).all()
    
    current_app.logger.info(f"Revisores encontrados (método original): {len(revisores)}")
    
    return revisores


def _verificar_candidatura_aprovada(revisor_id, evento_id):
    """Verifica se um revisor tem candidatura aprovada para um evento."""
    from models.review import revisor_process_evento_association
    
    revisor = Usuario.query.get(revisor_id)
    if not revisor:
        return None
    
    return RevisorCandidatura.query.join(
        RevisorProcess, RevisorCandidatura.process_id == RevisorProcess.id
    ).join(
        revisor_process_evento_association, 
        RevisorProcess.id == revisor_process_evento_association.c.revisor_process_id
    ).filter(
        RevisorCandidatura.email == revisor.email,
        revisor_process_evento_association.c.evento_id == evento_id,
        RevisorCandidatura.status == 'aprovado'
    ).first()


def _calcular_trabalhos_revisados(revisor_id, evento_id):
    """Calcula quantos trabalhos um revisor revisou em um evento."""
    return db.session.query(Assignment).join(
        RespostaFormulario, Assignment.resposta_formulario_id == RespostaFormulario.id
    ).filter(
        Assignment.reviewer_id == revisor_id,
        RespostaFormulario.evento_id == evento_id,
        Assignment.completed == True
    ).count()
