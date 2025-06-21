from flask import session
from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
Config.SQLALCHEMY_ENGINE_OPTIONS = Config.build_engine_options(
    Config.SQLALCHEMY_DATABASE_URI
)

from app import create_app


def add_routes(app):
    @app.route('/set')
    def set_route():
        session['value'] = 'works'
        return 'ok'

    @app.route('/get')
    def get_route():
        return session.get('value', 'missing')


def test_session_persists_between_app_instances(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'session-test')

    app1 = create_app()
    add_routes(app1)
    c1 = app1.test_client()
    c1.get('/set')
    cookie_name = app1.config['SESSION_COOKIE_NAME']
    cookie = c1.get_cookie(cookie_name).value

    app2 = create_app()
    add_routes(app2)
    c2 = app2.test_client()
    c2.set_cookie(cookie_name, cookie, domain='localhost')
    resp = c2.get('/get')
    assert resp.data == b'works'
