import importlib
import pathlib
import sys

# Ensure repository root is on sys.path
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import sitecustomize to preload real utils before tests possibly monkeypatch it
try:
    import sitecustomize  # noqa: F401
except Exception:  # pragma: no cover - optional
    pass

from datetime import datetime
from extensions import db
import models


class ReviewEmailLog(db.Model):
    __tablename__ = "review_email_log"

    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, nullable=False)
    recipient = db.Column(db.String(255), nullable=False)
    error = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


if not hasattr(models, "ReviewEmailLog"):
    models.ReviewEmailLog = ReviewEmailLog
