from flask import Blueprint, request, jsonify, abort, current_app
import os
import uuid
import secrets
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from models import Submission, Review, Assignment, ConfiguracaoCliente, AuditLog
from extensions import db
from services.mailjet_service import send_via_mailjet

submission_routes = Blueprint('submission_routes', __name__)


@submission_routes.route('/submissions', methods=['POST'])
def create_submission():
    title = request.form.get('title')
    content = request.form.get('content')
    email = request.form.get('email')
    author_id = request.form.get('author_id', type=int)
    evento_id = request.form.get('evento_id', type=int)
    uploaded_file = request.files.get('file')

    if not title or not email:
        return jsonify({'error': 'title and email required'}), 400

    locator = str(uuid.uuid4())
    raw_code = secrets.token_urlsafe(8)[:8]
    code_hash = generate_password_hash(raw_code)

    file_path = None
    if uploaded_file and uploaded_file.filename:
        filename = secure_filename(uploaded_file.filename)
        uploads_dir = current_app.config.get(
            'UPLOAD_FOLDER', 'static/uploads/submissions'
        )
        os.makedirs(uploads_dir, exist_ok=True)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(uploads_dir, unique_name)
        uploaded_file.save(file_path)

    submission = Submission(
        title=title,
        content=content,
        locator=locator,
        code_hash=code_hash,
        file_path=file_path,
        author_id=author_id,
        evento_id=evento_id,
    )
    db.session.add(submission)
    db.session.commit()

    db.session.add(
        AuditLog(
            user_id=author_id,
            submission_id=submission.id,
            event_type="submission",
        )
    )
    db.session.commit()

    try:
        send_via_mailjet(
            to_email=email,
            subject='Submission Access Code',
            text=f'Locator: {locator}\nAccess code: {raw_code}'
        )
    except Exception:
        pass

    return jsonify({'locator': locator, 'code': raw_code}), 201


@submission_routes.route('/submissions/<locator>')
def get_submission(locator):
    code = request.args.get('code')
    submission = Submission.query.filter_by(locator=locator).first_or_404()
    if not submission.check_code(code):
        abort(401)

    return jsonify({
        'id': submission.id,
        'title': submission.title,
        'content': submission.content
    })


@submission_routes.route('/submissions/<locator>/reviews', methods=['POST'])
def add_review(locator):
    code = request.form.get('code')
    submission = Submission.query.filter_by(locator=locator).first_or_404()
    if not submission.check_code(code):
        abort(401)

    reviewer = request.form.get('reviewer')
    comment = request.form.get('comment')

    review = Review(
        submission_id=submission.id,
        reviewer_name=reviewer,
        comments=comment,
    )
    db.session.add(review)

    cliente_id = submission.author.cliente_id if submission.author else None
    config = None
    if cliente_id:
        config = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
    prazo_dias = config.prazo_parecer_dias if config else 14

    assignment = Assignment(
        submission_id=submission.id,
        reviewer_id=int(reviewer) if reviewer and str(reviewer).isdigit() else None,
        deadline=datetime.utcnow() + timedelta(days=prazo_dias),
    )
    db.session.add(assignment)

    db.session.add(
        AuditLog(
            user_id=None,
            submission_id=submission.id,
            event_type="assignment",
        )
    )

    db.session.commit()
    return jsonify({'message': 'Review submitted'})


@submission_routes.route('/submissions/<locator>/codes')
def list_review_codes(locator):
    submission = Submission.query.filter_by(locator=locator).first_or_404()
    reviews = Review.query.filter_by(submission_id=submission.id).all()
    return jsonify({
        'locator': locator,
        'reviews': [
            {
                'locator': r.locator,
                'access_code': r.access_code,
                'started_at': r.started_at.isoformat() if r.started_at else None,
                'finished_at': r.finished_at.isoformat() if r.finished_at else None,
                'duration_seconds': r.duration_seconds
            }
            for r in reviews
        ]
    })
