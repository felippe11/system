from flask import Blueprint, send_file, abort, current_app
from flask_login import login_required, current_user
import os
from models.review import Submission
from models import Usuario, AuditLog
from extensions import db
from utils.auth import admin_required
from datetime import datetime

secure_file_routes = Blueprint('secure_file_routes', __name__)


@secure_file_routes.route('/secure/submission/<int:submission_id>/file')
@login_required
def download_submission_file(submission_id):
    """Download seguro de arquivo de submissão com controle de acesso."""
    
    submission = Submission.query.get_or_404(submission_id)
    
    # Verificar permissões de acesso
    if not _can_access_submission(submission):
        abort(403)
    
    # Verificar se o arquivo existe
    if not submission.file_path or not os.path.exists(submission.file_path):
        abort(404)
    
    # Log de acesso
    _log_file_access(submission_id)
    
    # Enviar arquivo
    return send_file(
        submission.file_path,
        as_attachment=True,
        download_name=f"submission_{submission_id}_{os.path.basename(submission.file_path)}"
    )


@secure_file_routes.route('/secure/submission/<locator>/file')
def download_submission_file_by_locator(locator):
    """Download por locator com código de acesso."""
    from flask import request
    
    code = request.args.get('code')
    if not code:
        abort(401)
    
    submission = Submission.query.filter_by(locator=locator).first_or_404()
    
    # Verificar código de acesso
    if not submission.check_code(code):
        abort(401)
    
    # Verificar se o arquivo existe
    if not submission.file_path or not os.path.exists(submission.file_path):
        abort(404)
    
    # Log de acesso anônimo
    _log_anonymous_access(submission.id, locator)
    
    # Enviar arquivo
    return send_file(
        submission.file_path,
        as_attachment=True,
        download_name=f"submission_{submission.id}_{os.path.basename(submission.file_path)}"
    )


def _can_access_submission(submission):
    """Verifica se o usuário atual pode acessar a submissão."""
    
    # Administradores e superadmins podem acessar tudo
    if current_user.tipo in ['admin', 'superadmin']:
        return True
    
    # Autor pode acessar sua própria submissão
    if submission.author_id == current_user.id:
        return True
    
    # Revisores designados podem acessar
    from models.review import Assignment
    assignment = Assignment.query.filter_by(
        submission_id=submission.id,
        reviewer_id=current_user.id
    ).first()
    if assignment:
        return True
    
    # Organizadores do evento podem acessar
    if (submission.evento_id and 
        current_user.tipo in ['ministrante', 'professor'] and
        current_user.evento_id == submission.evento_id):
        return True
    
    return False


def _log_file_access(submission_id):
    """Registra acesso ao arquivo no log de auditoria."""
    try:
        audit_log = AuditLog(
            user_id=current_user.id,
            submission_id=submission_id,
            event_type='file_access',
            timestamp=datetime.utcnow()
        )
        db.session.add(audit_log)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Erro ao registrar acesso ao arquivo: {e}")


def _log_anonymous_access(submission_id, locator):
    """Registra acesso anônimo ao arquivo."""
    try:
        audit_log = AuditLog(
            user_id=None,
            submission_id=submission_id,
            event_type='anonymous_file_access',
            details=f'locator: {locator}',
            timestamp=datetime.utcnow()
        )
        db.session.add(audit_log)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Erro ao registrar acesso anônimo: {e}")