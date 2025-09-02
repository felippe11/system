from flask import Blueprint
from utils import endpoints
patrocinador_routes = Blueprint("patrocinador_routes", __name__)

from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import Evento, Patrocinador
from extensions import db
import os
from flask import jsonify

# Mapeamento de categorias para usar acentuação correta
categoria_map = {
    "realizacao": "Realização",
    "patrocinio": "Patrocínio",
    "organizacao": "Organização",
    "apoio": "Apoio",
}


@patrocinador_routes.route('/adicionar_patrocinadores_categorizados', methods=['POST'])
@login_required
def adicionar_patrocinadores_categorizados():
    if current_user.tipo not in ['admin', 'cliente']:
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))

    evento_id = request.form.get('evento_id')
    if not evento_id:
        flash("Evento não selecionado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))

    qtd_realizacao = int(request.form.get('qtd_realizacao', 0))
    qtd_patrocinio = int(request.form.get('qtd_patrocinio', 0))
    qtd_organizacao = int(request.form.get('qtd_organizacao', 0))
    qtd_apoio = int(request.form.get('qtd_apoio', 0))

    def salvar_uploads(categoria_label, qtd):
        imported_count = 0
        for i in range(qtd):
            key = f'{categoria_label.lower()}_{i}'
            if key in request.files:
                file = request.files[key]
                if file and file.filename.strip():
                    filename = secure_filename(file.filename)
                    upload_folder = os.path.join('static', 'uploads', 'patrocinadores')
                    os.makedirs(upload_folder, exist_ok=True)
                    file.save(os.path.join(upload_folder, filename))

                    logo_path = os.path.join('uploads', 'patrocinadores', filename)

                    # Categoria com acentuação correta
                    categoria = categoria_map.get(categoria_label.lower())
                    novo_pat = Patrocinador(
                        evento_id=evento_id,
                        logo_path=logo_path,
                        categoria=categoria
                    )
                    db.session.add(novo_pat)
                    imported_count += 1
        return imported_count

    total_importados = 0
    total_importados += salvar_uploads('realizacao', qtd_realizacao)
    total_importados += salvar_uploads('patrocinio', qtd_patrocinio)
    total_importados += salvar_uploads('organizacao', qtd_organizacao)
    total_importados += salvar_uploads('apoio', qtd_apoio)

    db.session.commit()

    flash(f"Patrocinadores adicionados com sucesso! Total: {total_importados}", "success")
    return redirect(url_for(endpoints.DASHBOARD_CLIENTE))


@patrocinador_routes.route('/remover_patrocinador/<int:patrocinador_id>', methods=['POST'])
@login_required
def remover_patrocinador(patrocinador_id):
    if current_user.tipo not in ['admin', 'cliente']:
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))

    patrocinador = Patrocinador.query.get_or_404(patrocinador_id)

    # Se for cliente, verifica se realmente é dele
    if current_user.tipo == 'cliente':
        # Busca o evento do patrocinador e verifica se pertence ao cliente
        if not patrocinador.evento or patrocinador.evento.cliente_id != current_user.id:
            flash("Você não tem permissão para remover esse patrocinador.", "danger")
            return redirect(url_for('patrocinador_routes.listar_patrocinadores'))

    try:
        db.session.delete(patrocinador)
        db.session.commit()
        flash("Patrocinador removido com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao remover patrocinador: {e}", "danger")

    return redirect(url_for('patrocinador_routes.listar_patrocinadores'))


@patrocinador_routes.route('/patrocinadores', methods=['GET'])
@login_required
def listar_patrocinadores():
    # Verifica se é admin ou cliente
    if current_user.tipo not in ['admin', 'cliente']:
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))
    
    # Se for admin, traz todos; se for cliente, traz só do cliente
    if current_user.tipo == 'admin':
        patrocinadores = Patrocinador.query.all()
    else:
        # Busca os eventos do cliente
        eventos_cliente = Evento.query.filter_by(cliente_id=current_user.id).all()
        evento_ids = [ev.id for ev in eventos_cliente]
        # Traz patrocinadores apenas dos eventos do cliente
        patrocinadores = Patrocinador.query.filter(Patrocinador.evento_id.in_(evento_ids)).all()

    return render_template(
        'listar_patrocinadores.html', 
        patrocinadores=patrocinadores
    )

@patrocinador_routes.route('/gerenciar_patrocinadores')
@login_required
def gerenciar_patrocinadores():
    """Lista todos os patrocinadores, de todas as categorias."""
    if current_user.tipo not in ['admin','cliente']:
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))

    # Se for admin, traz todos. Se for cliente, filtra pelos eventos do cliente
    if current_user.tipo == 'admin':
        patrocinadores = Patrocinador.query.all()
    else:
        # Buscar eventos do cliente e extrair seus IDs
        eventos_cliente = Evento.query.filter_by(cliente_id=current_user.id).all()
        eventos_ids = [ev.id for ev in eventos_cliente]
        patrocinadores = Patrocinador.query.filter(Patrocinador.evento_id.in_(eventos_ids)).all()

    return render_template('patrocinador/gerenciar_patrocinadores.html', patrocinadores=patrocinadores)

@patrocinador_routes.route('/remover_foto_patrocinador/<int:patrocinador_id>', methods=['POST'])
@login_required
def remover_foto_patrocinador(patrocinador_id):
    """Remove a foto de patrocinador (categoria: Realização, Organização, Apoio, Patrocínio)."""
    if current_user.tipo not in ['admin','cliente']:
        flash("Acesso negado!", "danger")
        return redirect(url_for(endpoints.DASHBOARD))

    pat = Patrocinador.query.get_or_404(patrocinador_id)

    # Se for cliente, verifica se esse patrocinador é dele
    if current_user.tipo == 'cliente':
        if not pat.evento or pat.evento.cliente_id != current_user.id:
            flash("Você não tem permissão para remover este registro.", "danger")
            return redirect(url_for('patrocinador_routes.gerenciar_patrocinadores'))

    try:
        db.session.delete(pat)
        db.session.commit()
        flash("Logo removida com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao remover: {e}", "danger")

    return redirect(url_for('patrocinador_routes.gerenciar_patrocinadores'))

@patrocinador_routes.route('/remover_fotos_selecionadas', methods=['POST'])
def remover_fotos_selecionadas():
    # Recupera a lista de IDs selecionados no checkbox
    ids_selecionados = request.form.getlist('fotos_selecionadas')

    if not ids_selecionados:
        flash('Nenhuma imagem foi selecionada para remoção.', 'warning')
        return redirect(url_for('patrocinador_routes.gerenciar_patrocinadores'))
    
    # Converte cada id para inteiro
    ids_selecionados = [int(x) for x in ids_selecionados]

    # Busca cada patrocinador correspondente e remove do DB
    for pat_id in ids_selecionados:
        pat = Patrocinador.query.get(pat_id)
        if pat:
            # Se quiser, remova também o arquivo de imagem físico, se armazenar localmente
            # Exemplo: os.remove(os.path.join(current_app.static_folder, pat.logo_path))

            db.session.delete(pat)
    
    db.session.commit()
    flash('Fotos removidas com sucesso!', 'success')
    return redirect(url_for('patrocinador_routes.gerenciar_patrocinadores'))
    # Se não houver fotos selecionadas, redireciona para a página de gerenciamento



