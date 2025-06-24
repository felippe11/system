from flask import Blueprint, request, jsonify, abort
import uuid
import secrets
import bcrypt
from models import Submission, Review
from extensions import db, mail
from flask_mail import Message

submission_routes = Blueprint('submission_routes', __name__)


@submission_routes.route('/submissions', methods=['POST'])
def create_submission():
    title = request.form.get('title')
    content = request.form.get('content')
    email = request.form.get('email')

    if not title or not email:
        return jsonify({'error': 'title and email required'}), 400

    locator = str(uuid.uuid4())
    raw_code = secrets.token_urlsafe(8)[:8]
    code_hash = bcrypt.hashpw(raw_code.encode(), bcrypt.gensalt()).decode()

    submission = Submission(title=title, content=content,
                            locator=locator, code_hash=code_hash)
    db.session.add(submission)
    db.session.commit()

    try:
        msg = Message('Submission Access Code', recipients=[email])
        msg.body = f'Locator: {locator}\nAccess code: {raw_code}'
        mail.send(msg)
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
    review = Review(submission=submission, reviewer=reviewer, comment=comment)
    db.session.add(review)
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
