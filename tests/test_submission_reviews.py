import os
import pytest
from werkzeug.security import generate_password_hash

os.environ["SECRET_KEY"] = "test"
os.environ["GOOGLE_CLIENT_ID"] = "dummy"
os.environ["GOOGLE_CLIENT_SECRET"] = "dummy"
from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models.user import Usuario
from models.review import Submission, Review, Assignment


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        reviewer = Usuario(
            nome='Reviewer',
            cpf='1',
            email='rev@test',
            senha=generate_password_hash('123', method="pbkdf2:sha256"),
            formacao='X',
            tipo='professor',
        )
        sub = Submission(
            title='T',
            locator='loc1',
            code_hash=generate_password_hash('code', method="pbkdf2:sha256"),
        )
        db.session.add_all([reviewer, sub])
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_add_review_separate_fields(client, app):
    resp = client.post(
        '/submissions/loc1/reviews',
        data={
            'code': 'code',
            'reviewer_id': 1,
            'reviewer_name': 'Prof',
            'comment': 'Good',
        },
    )
    assert resp.status_code == 200
    with app.app_context():
        review = Review.query.first()
        assignment = Assignment.query.first()
        assert review.reviewer_name == 'Prof'
        assert review.reviewer_id == 1
        assert assignment.reviewer_id == 1
