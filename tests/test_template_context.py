from datetime import datetime
import os

os.environ.setdefault("GOOGLE_CLIENT_ID", "x")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "x")

from utils import template_context


def test_now_available_in_template_context(monkeypatch):
    class DummyUser:
        is_authenticated = False

    monkeypatch.setattr(template_context, "current_user", DummyUser())
    context = template_context.inject_auth_context()

    assert "now" in context
    assert isinstance(context["now"](), datetime)
