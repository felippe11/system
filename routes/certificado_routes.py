from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, after_this_request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
from models import Cliente, Oficina, CertificadoTemplate
from services.pdf_service import gerar_certificado_personalizado  # ajuste conforme a localização

import os
from datetime import datetime
import logging

certificado_routes = Blueprint(
    'certificado_routes',
    __name__,
    template_folder="../templates/certificado"
)

logger = logging.getLogger(__name__)


@certificado_routes.route('/templates_certificado', methods=['GET', 'POST'])
@login_required
def templates_certificado():
    if request.method == 'POST':
        titulo = request.form['titulo']
        conteudo = request.form['conteudo']
        novo_template = CertificadoTemplate(cliente_id=current_user.id, titulo=titulo, conteudo=conteudo)
        db.session.add(novo_template)
        db.session.commit()
        flash('Template cadastrado com sucesso!', 'success')

    templates = CertificadoTemplate.query.filter_by(cliente_id=current_user.id).all()
    return render_template('certificado/templates_certificado.html', templates=templates)

@certificado_routes.route('/set_template_ativo/<int:template_id>', methods=['POST'])
@login_required
def set_template_ativo(template_id):
    CertificadoTemplate.query.filter_by(cliente_id=current_user.id).update({'ativo': False})
    template = CertificadoTemplate.query.get(template_id)
    template.ativo = True
    db.session.commit()
    flash('Template definido como ativo com sucesso!', 'success')
    return redirect(url_for('certificado_routes.templates_certificado'))

@certificado_routes.route('/gerar_certificado_evento', methods=['POST'])
@login_required
def gerar_certificado_evento():
    texto_personalizado = request.form.get('texto_personalizado', '')
    oficinas_ids = request.form.getlist('oficinas_selecionadas')

    oficinas = Oficina.query.filter(Oficina.id.in_(oficinas_ids)).all()
    total_horas = sum(int(of.carga_horaria) for of in oficinas)

    # Capturar template ativo
    template = CertificadoTemplate.query.filter_by(cliente_id=current_user.id, ativo=True).first()
    if not template:
        flash('Nenhum template ativo encontrado!', 'danger')
        return redirect(url_for('certificado_routes.dashboard_cliente'))

    pdf_path = gerar_certificado_personalizado(current_user, oficinas, total_horas, texto_personalizado, template.conteudo)
    return send_file(pdf_path, as_attachment=True)

@certificado_routes.route('/salvar_personalizacao_certificado', methods=['POST'])
@login_required
def salvar_personalizacao_certificado():
    cliente = Cliente.query.get(current_user.id)

    for campo in ['logo_certificado', 'assinatura_certificado', 'fundo_certificado']:
        arquivo = request.files.get(campo)
        if arquivo:
            filename = secure_filename(arquivo.filename)
            path = os.path.join('static/uploads/certificados', filename)
            arquivo.save(path)
            setattr(cliente, campo, path)

    cliente.texto_personalizado = request.form.get('texto_personalizado')
    db.session.commit()

    flash('Personalizações salvas com sucesso!', 'success')
    return redirect(url_for('certificado_routes.upload_personalizacao_certificado'))

@certificado_routes.route('/ativar_template_certificado/<int:template_id>', methods=['POST'])
@login_required
def ativar_template_certificado(template_id):
    CertificadoTemplate.query.filter_by(cliente_id=current_user.id).update({'ativo': False})
    template = CertificadoTemplate.query.get_or_404(template_id)
    template.ativo = True
    db.session.commit()

    flash('Template ativado com sucesso!', 'success')
    return redirect(url_for('certificado_routes.upload_personalizacao_certificado'))


@certificado_routes.route('/editar_template_certificado/<int:template_id>', methods=['POST'])
@login_required
def editar_template_certificado(template_id):
    template = CertificadoTemplate.query.get_or_404(template_id)

    if template.cliente_id != current_user.id:
        flash('Você não tem permissão para editar este template.', 'danger')
        return redirect(url_for('certificado_routes.upload_personalizacao_certificado'))

    novo_titulo = request.form.get('titulo')
    novo_conteudo = request.form.get('conteudo')

    if not novo_titulo or not novo_conteudo:
        flash('Todos os campos são obrigatórios.', 'warning')
        return redirect(url_for('certificado_routes.upload_personalizacao_certificado'))

    template.titulo = novo_titulo
    template.conteudo = novo_conteudo

    db.session.commit()
    flash('Template atualizado com sucesso!', 'success')
    return redirect(url_for('certificado_routes.upload_personalizacao_certificado'))

@certificado_routes.route('/desativar_template_certificado/<int:template_id>', methods=['POST'])
@login_required
def desativar_template_certificado(template_id):
    template = CertificadoTemplate.query.get_or_404(template_id)

    if template.cliente_id != current_user.id:
        flash('Você não tem permissão para alterar esse template.', 'danger')
        return redirect(url_for('certificado_routes.upload_personalizacao_certificado'))

    template.ativo = False
    db.session.commit()
    flash('Template desativado com sucesso!', 'info')
    return redirect(url_for('certificado_routes.upload_personalizacao_certificado'))

@certificado_routes.route('/upload_personalizacao_certificado', methods=['GET', 'POST'])
@login_required
def upload_personalizacao_certificado():
    
    cliente = Cliente.query.get(current_user.id)
    templates = CertificadoTemplate.query.filter_by(cliente_id=current_user.id).all()

    if request.method == 'POST':
        logo_file = request.files.get('logo_certificado')
        fundo_file = request.files.get('fundo_certificado')
        ass_file = request.files.get('assinatura_certificado')

        # Exemplo de pasta
        pasta_uploads = os.path.join('uploads', 'personalizacao')
        os.makedirs(pasta_uploads, exist_ok=True)

        # Se o cliente enviar algo, salvamos e atualizamos o path
        if logo_file and logo_file.filename:
            filename_logo = secure_filename(logo_file.filename)
            caminho_logo = os.path.join(pasta_uploads, filename_logo)
            logo_file.save(caminho_logo)
            current_user.logo_certificado = caminho_logo  # Salva no banco

        if fundo_file and fundo_file.filename:
            filename_fundo = secure_filename(fundo_file.filename)
            caminho_fundo = os.path.join(pasta_uploads, filename_fundo)
            fundo_file.save(caminho_fundo)
            current_user.fundo_certificado = caminho_fundo

        if ass_file and ass_file.filename:
            filename_ass = secure_filename(ass_file.filename)
            caminho_ass = os.path.join(pasta_uploads, filename_ass)
            ass_file.save(caminho_ass)
            current_user.assinatura_certificado = caminho_ass

        db.session.commit()
        flash("Personalização salva com sucesso!", "success")
        return redirect(url_for('certificado_routes.dashboard_cliente'))

    return render_template('upload_personalizacao_cert.html', templates=templates, cliente=cliente)


@certificado_routes.route('/preview_certificado', methods=['GET', 'POST'])
@login_required
def preview_certificado():
    """Gera um PDF de exemplo para visualizar o certificado."""

    class UsuarioExemplo:
        id = 0
        nome = "Participante Exemplo"

    class OficinaExemplo:
        titulo = "Oficina Exemplo"
        carga_horaria = "4"
        datas = [datetime.now()]

    cliente = Cliente.query.get(current_user.id)
    template = CertificadoTemplate.query.filter_by(cliente_id=current_user.id, ativo=True).first()
    template_conteudo = template.conteudo if template else None

    temp_files = []

    if request.method == "POST":
        import tempfile
        from types import SimpleNamespace

        texto_personalizado = request.form.get("texto_personalizado", "")

        caminhos = {}
        for campo in ["logo_certificado", "assinatura_certificado", "fundo_certificado"]:
            arquivo = request.files.get(campo)
            if arquivo and arquivo.filename:
                extensao = os.path.splitext(arquivo.filename)[1]
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=extensao)
                arquivo.save(tmp.name)
                caminhos[campo] = tmp.name
                temp_files.append(tmp.name)
            else:
                caminhos[campo] = getattr(cliente, campo)

        temp_cliente = SimpleNamespace(
            logo_certificado=caminhos.get("logo_certificado"),
            assinatura_certificado=caminhos.get("assinatura_certificado"),
            fundo_certificado=caminhos.get("fundo_certificado"),
            texto_personalizado=texto_personalizado,
        )
    else:
        texto_personalizado = ""
        temp_cliente = cliente

    pdf_path = gerar_certificado_personalizado(
        UsuarioExemplo(),
        [OficinaExemplo()],
        4,
        texto_personalizado,
        template_conteudo,
        temp_cliente,
    )

    @after_this_request
    def cleanup(response):
        # Testes lidam com remoção do arquivo gerado
        for f in temp_files:
            try:
                os.remove(f)
            except OSError as exc:
                logger.exception("Erro ao remover arquivo temporário %s", f)
        return response

    return send_file(pdf_path, mimetype="application/pdf")

