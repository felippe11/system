from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
from utils.mfa import mfa_required
from werkzeug.utils import secure_filename
from io import BytesIO

from extensions import db
from models import ArquivoBinario, AuditLog
from models.user import Usuario

binary_routes = Blueprint('binary_routes', __name__)

# Tamanho máximo de arquivo (5 MB)
MAX_FILE_SIZE = 5 * 1024 * 1024


@binary_routes.route('/api/binarios', methods=['POST'])
@login_required
@mfa_required
def upload_binario():
    """Endpoint para upload de arquivos binários."""
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400

    usuario = Usuario.query.get(getattr(current_user, 'id', None))
    uid = usuario.id if usuario else None  # salva log mesmo se usuário não existir

    content_length = file.content_length or request.content_length
    if content_length and content_length > MAX_FILE_SIZE:
        log = AuditLog(user_id=uid, submission_id=None, event_type='upload_too_large')
        db.session.add(log)
        db.session.commit()
        return jsonify({'error': 'Arquivo excede o tamanho máximo de 5MB'}), 400

    novo = ArquivoBinario(
        nome=secure_filename(file.filename),
        conteudo=file.read(),
        mimetype=file.mimetype or 'application/octet-stream'
    )
    db.session.add(novo)
    db.session.commit()
    log = AuditLog(user_id=uid, submission_id=novo.id, event_type='upload')
    db.session.add(log)
    db.session.commit()
    return jsonify({'id': novo.id, 'nome': novo.nome}), 201


@binary_routes.route('/api/binarios/<int:arquivo_id>', methods=['GET'])
@login_required
@mfa_required
def download_binario(arquivo_id):
    """Baixa um arquivo binário armazenado no banco."""
    arq = ArquivoBinario.query.get_or_404(arquivo_id)
    usuario = Usuario.query.get(getattr(current_user, 'id', None))
    uid = usuario.id if usuario else None  # salva log mesmo sem usuário
    log = AuditLog(user_id=uid, submission_id=arquivo_id, event_type='download')
    db.session.add(log)
    db.session.commit()
    return send_file(
        BytesIO(arq.conteudo),
        mimetype=arq.mimetype,
        as_attachment=True,
        download_name=arq.nome
    )
