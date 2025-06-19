from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required
from werkzeug.utils import secure_filename
from io import BytesIO

from extensions import db
from models import ArquivoBinario

binary_routes = Blueprint('binary_routes', __name__)


@binary_routes.route('/api/binarios', methods=['POST'])
@login_required
def upload_binario():
    """Endpoint para upload de arquivos binários."""
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    novo = ArquivoBinario(
        nome=secure_filename(file.filename),
        conteudo=file.read(),
        mimetype=file.mimetype or 'application/octet-stream'
    )
    db.session.add(novo)
    db.session.commit()
    return jsonify({'id': novo.id, 'nome': novo.nome}), 201


@binary_routes.route('/api/binarios/<int:arquivo_id>', methods=['GET'])
@login_required
def download_binario(arquivo_id):
    """Baixa um arquivo binário armazenado no banco."""
    arq = ArquivoBinario.query.get_or_404(arquivo_id)
    return send_file(
        BytesIO(arq.conteudo),
        mimetype=arq.mimetype,
        as_attachment=True,
        download_name=arq.nome
    )
