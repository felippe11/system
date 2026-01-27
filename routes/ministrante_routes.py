from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import Oficina, RelatorioOficina, MaterialOficina
from models.user import Ministrante, Cliente
from extensions import db
from werkzeug.security import generate_password_hash
import os
import uuid
from utils import endpoints

ministrante_routes = Blueprint(
    "ministrante_routes",
    __name__,
    template_folder="../templates/ministrante"
)


@ministrante_routes.route('/cadastro_ministrante', methods=['GET', 'POST'])
@login_required
def cadastro_ministrante():
    if current_user.tipo not in ['admin', 'cliente']:
        flash('Apenas administradores e clientes podem cadastrar ministrantes!', 'danger')
        return redirect(url_for(endpoints.DASHBOARD))

    clientes = Cliente.query.all() if current_user.tipo == 'admin' else []

    if request.method == 'POST':
        nome = request.form.get('nome')
        formacao = request.form.get('formacao')
        categorias_formacao = request.form.getlist('categorias_formacao')
        categorias_str = ','.join(categorias_formacao)  # Transforma lista em string
        foto = request.files.get('foto')
        areas = request.form.get('areas')
        cpf = request.form.get('cpf')
        pix = request.form.get('pix')
        cidade = request.form.get('cidade')
        estado = request.form.get('estado')
        email = request.form.get('email')
        senha = generate_password_hash(request.form.get('senha'), method="pbkdf2:sha256")

        # Se for admin, pega o cliente_id do form
        # Se for cliente, assume o id do current_user
        cliente_id = request.form.get('cliente_id') if current_user.tipo == 'admin' else current_user.id

        # Gera caminho único para foto
        foto_path = None
        if foto and foto.filename:
            original_filename = secure_filename(foto.filename)   # ex.: foto.jpg
            ext = original_filename.rsplit('.', 1)[1].lower()    # pega a extensão ex.: jpg
            unique_name = f"{uuid.uuid4()}.{ext}"                # ex.: 123e4567-e89b-12d3-a456-426614174000.jpg
            uploads_root = current_app.config.get(
                "UPLOADS_ROOT",
                os.path.join(current_app.root_path, "static", "uploads"),
            )
            caminho_foto = os.path.join(uploads_root, "ministrantes", unique_name)
            os.makedirs(os.path.dirname(caminho_foto), exist_ok=True)
            foto.save(caminho_foto) 
            foto_path = f'uploads/ministrantes/{unique_name}'    # caminho relativo à pasta static

        # Agora criamos o objeto Ministrante, passando foto_path
        novo_ministrante = Ministrante(
            nome=nome,
            formacao=formacao,
            categorias_formacao=categorias_str,
            foto=foto_path,  # Passamos o caminho aqui (ou None se não houve upload)
            areas_atuacao=areas,
            cpf=cpf,
            pix=pix,
            cidade=cidade,
            estado=estado,
            email=email,
            senha=senha,
            cliente_id=cliente_id
        )

        try:
            db.session.add(novo_ministrante)
            db.session.commit()
            flash('Cadastro realizado com sucesso!', 'success')
            # Redireciona para o dashboard adequado (admin / cliente)
            return redirect(url_for(endpoints.DASHBOARD_CLIENTE if current_user.tipo == 'cliente' else endpoints.DASHBOARD))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar ministrante: {str(e)}', 'danger')

    return render_template('cadastro_ministrante.html', clientes=clientes)

@ministrante_routes.route('/editar_ministrante/<int:ministrante_id>', methods=['GET', 'POST'])
@login_required
def editar_ministrante(ministrante_id):
    ministrante = Ministrante.query.get_or_404(ministrante_id)

    if current_user.tipo == 'cliente' and ministrante.cliente_id != current_user.id:
        flash('Acesso negado!', 'danger')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))

    clientes = Cliente.query.all() if current_user.tipo == 'admin' else None
    ids_extras = request.form.getlist('ministrantes_ids[]')
    
    for mid in ids_extras:
        m = Ministrante.query.get(int(mid))
        if m:
            oficina.ministrantes_associados.append(m)

    if request.method == 'POST':
        ministrante.nome = request.form.get('nome')
        ministrante.formacao = request.form.get('formacao')
        categorias_formacao = request.form.getlist('categorias_formacao')
        ministrante.categorias_formacao = ','.join(categorias_formacao)

        ministrante.areas_atuacao = request.form.get('areas')
        ministrante.cpf = request.form.get('cpf')
        ministrante.pix = request.form.get('pix')
        ministrante.cidade = request.form.get('cidade')
        ministrante.estado = request.form.get('estado')
        ministrante.email = request.form.get('email')

        if current_user.tipo == 'admin':
            novo_cliente_id = request.form.get('cliente_id')
            ministrante.cliente_id = novo_cliente_id if novo_cliente_id else None

        nova_senha = request.form.get('senha')
        if nova_senha:
            ministrante.senha = generate_password_hash(nova_senha, method="pbkdf2:sha256")

        foto = request.files.get('foto')
        if foto and foto.filename:
            filename = secure_filename(foto.filename)
            uploads_root = current_app.config.get(
                "UPLOADS_ROOT",
                os.path.join(current_app.root_path, "static", "uploads"),
            )
            caminho_foto = os.path.join(uploads_root, "ministrantes", filename)
            os.makedirs(os.path.dirname(caminho_foto), exist_ok=True)
            foto.save(caminho_foto)
            ministrante.foto = f'uploads/ministrantes/{filename}'

        db.session.commit()
        flash('Ministrante atualizado com sucesso!', 'success')
        return redirect(url_for('ministrante_routes.gerenciar_ministrantes'))

    return render_template('editar_ministrante.html', ministrante=ministrante, clientes=clientes)

@ministrante_routes.route('/excluir_ministrante/<int:ministrante_id>', methods=['POST'])
@login_required
def excluir_ministrante(ministrante_id):
    ministrante = Ministrante.query.get_or_404(ministrante_id)

    if current_user.tipo == 'cliente' and ministrante.cliente_id != current_user.id:
        flash('Acesso negado!', 'danger')
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))

    db.session.delete(ministrante)
    db.session.commit()
    flash('Ministrante excluído com sucesso!', 'success')
    return redirect(url_for('ministrante_routes.gerenciar_ministrantes'))


@ministrante_routes.route('/gerenciar_ministrantes', methods=['GET'])
@login_required
def gerenciar_ministrantes():
    if current_user.tipo not in ['admin', 'cliente']:
        flash('Acesso negado!', 'danger')
        return redirect(url_for(endpoints.DASHBOARD))

    ministrantes = Ministrante.query.filter_by(cliente_id=current_user.id).all() if current_user.tipo == 'cliente' else Ministrante.query.all()

    return render_template('gerenciar_ministrantes.html', ministrantes=ministrantes)


@ministrante_routes.route('/enviar_relatorio/<int:oficina_id>', methods=['GET', 'POST'])
@login_required
def enviar_relatorio(oficina_id):
    if current_user.tipo != 'ministrante':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('evento_routes.home'))

    oficina = Oficina.query.get_or_404(oficina_id)
    ministrante_logado = Ministrante.query.filter_by(email=current_user.email).first()

    if oficina.ministrante_id != ministrante_logado.id:
        flash('Você não é responsável por esta oficina!', 'danger')
        return redirect(url_for('formador_routes.dashboard_formador'))

    if request.method == 'POST':
        metodologia = request.form.get('metodologia')
        resultados = request.form.get('resultados')

        # Upload de fotos/vídeos se desejado
        arquivo_midia = request.files.get('arquivo_midia')
        midia_path = None
        if arquivo_midia:
            filename = secure_filename(arquivo_midia.filename)
            pasta_uploads = os.path.join('uploads', 'relatorios')
            os.makedirs(pasta_uploads, exist_ok=True)
            caminho_arquivo = os.path.join(pasta_uploads, filename)
            arquivo_midia.save(caminho_arquivo)
            midia_path = caminho_arquivo

        novo_relatorio = RelatorioOficina(
            oficina_id=oficina.id,
            ministrante_id=ministrante_logado.id,
            metodologia=metodologia,
            resultados=resultados,
            fotos_videos_path=midia_path
        )
        db.session.add(novo_relatorio)
        db.session.commit()

        flash("Relatório enviado com sucesso!", "success")
        return redirect(url_for('formador_routes.dashboard_formador'))

    return render_template('enviar_relatorio.html', oficina=oficina)

@ministrante_routes.route('/upload_material/<int:oficina_id>', methods=['GET', 'POST'])
@login_required
def upload_material(oficina_id):
    # Verifica se o usuário é um ministrante
    from models import Ministrante  # Certifique-se de importar se necessário
    if not hasattr(current_user, 'tipo') or current_user.tipo != 'ministrante':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('evento_routes.home'))
    
    # Buscar a oficina e verificar se o ministrante logado é responsável por ela
    oficina = Oficina.query.get_or_404(oficina_id)
    ministrante_logado = Ministrante.query.filter_by(email=current_user.email).first()
    if not ministrante_logado or oficina.ministrante_id != ministrante_logado.id:
        flash('Você não é responsável por esta oficina!', 'danger')
        return redirect(url_for('dashboard_ministrante_routes.dashboard_ministrante'))
    
    if request.method == 'POST':
        arquivo = request.files.get('arquivo')
        if arquivo:
            filename = secure_filename(arquivo.filename)
            pasta_uploads = os.path.join('uploads', 'materiais')
            os.makedirs(pasta_uploads, exist_ok=True)
            caminho_arquivo = os.path.join(pasta_uploads, filename)
            arquivo.save(caminho_arquivo)
            
            novo_material = MaterialOficina(
                oficina_id=oficina.id,
                nome_arquivo=filename,
                caminho_arquivo=caminho_arquivo
            )
            db.session.add(novo_material)
            db.session.commit()
            
            flash('Material anexado com sucesso!', 'success')
            return redirect(url_for('formador_routes.dashboard_formador'))
        else:
            flash('Nenhum arquivo foi enviado.', 'danger')
    
    return render_template('upload_material.html', oficina=oficina)
