import pytest
from werkzeug.security import generate_password_hash
from config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(Config.SQLALCHEMY_DATABASE_URI)

from app import create_app
from extensions import db
from models.review import Submission, Review

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        raw_code = 'secret'
        sub = Submission(title='T', locator='loc1', code_hash=generate_password_hash(raw_code))
        db.session.add(sub)
        db.session.commit()
        rev = Review(submission_id=sub.id, locator='revloc', access_code='revcode')
        db.session.add(rev)
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_review_timing(client, app):
    # access GET sets start
    resp = client.get('/review/revloc')
    assert resp.status_code == 200
    with app.app_context():
        rev = Review.query.filter_by(locator='revloc').first()
        assert rev.started_at is not None
    # submit POST
    resp = client.post('/review/revloc', data={'codigo': 'revcode', 'nota': '5'})
    assert resp.status_code in (200, 302)
    with app.app_context():
        rev = Review.query.filter_by(locator='revloc').first()
        assert rev.finished_at is not None
        assert rev.duration_seconds is not None

    # list codes
    resp = client.get('/submissions/loc1/codes')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['locator'] == 'loc1'
    assert data['reviews'][0]['access_code'] == 'revcode'
    assert 'reviewer_name' in data['reviews'][0]
