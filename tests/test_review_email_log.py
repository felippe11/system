import importlib

import pytest
from flask import Flask

from extensions import db
from models import Usuario, Submission, Review, ReviewEmailLog

review_service = importlib.import_module("services.review_notification_service")


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _create_review():
    reviewer = Usuario(
        nome="Rev",
        cpf="00000000000",
        email="rev@test",
        senha="x",
        formacao="x",
        tipo="revisor",
    )
    submission = Submission(title="T", code_hash="h")
    db.session.add_all([reviewer, submission])
    db.session.commit()
    review = Review(
        submission_id=submission.id,
        reviewer_id=reviewer.id,
        access_code="123",
    )
    db.session.add(review)
    db.session.commit()
    return review


def test_logs_failure(app, monkeypatch):
    with app.app_context():
        review = _create_review()
        monkeypatch.setattr(review_service, "url_for", lambda *a, **k: "http://link")

        def boom(**_):
            raise Exception("boom")

        monkeypatch.setattr(review_service, "send_via_mailjet", boom)
        review_service.notify_reviewer(review)
        db.session.commit()
        log = ReviewEmailLog.query.one()
        assert log.review_id == review.id
        assert log.recipient == review.reviewer.email
        assert "boom" in log.error


def test_success_no_log(app, monkeypatch):
    with app.app_context():
        review = _create_review()
        monkeypatch.setattr(review_service, "url_for", lambda *a, **k: "http://link")
        monkeypatch.setattr(review_service, "send_via_mailjet", lambda **_: None)
        review_service.notify_reviewer(review)
        db.session.commit()
        assert ReviewEmailLog.query.count() == 0
