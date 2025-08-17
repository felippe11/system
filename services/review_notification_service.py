"""Utilities for sending review notifications and logging failures."""

import logging
from flask import url_for
from mailjet_rest.client import ApiError

from extensions import db
from services.mailjet_service import send_via_mailjet

logger = logging.getLogger(__name__)


def _log_review_email_error(review, exc):
    """Persist a failed review notification for later auditing."""
    from models import ReviewEmailLog  # imported here to avoid circular imports

    db.session.add(
        ReviewEmailLog(
            review_id=review.id,
            recipient=review.reviewer.email,
            error=str(exc),
        )
    )


def notify_reviewer(review):
    """Send access details to the assigned reviewer via e-mail.

    If sending fails, a ``ReviewEmailLog`` entry is created so failures can be
    audited later.
    """
    if not review.reviewer or not review.reviewer.email:
        return

    link = url_for(
        "peer_review_routes.review_form", locator=review.locator, _external=True
    )
    text = (
        "Você foi designado para avaliar um trabalho.\n"
        f"Acesse: {link}\nCódigo: {review.access_code}"
    )

    try:
        send_via_mailjet(
            to_email=review.reviewer.email,
            subject="Novo parecer disponível",
            text=text,
        )
    except Exception as exc:  # pragma: no cover - network errors are rare
        if isinstance(exc, ApiError):
            logger.exception(
                "Erro ao enviar e-mail de revisão para %s",
                review.reviewer.email,
            )
        else:
            logger.exception(
                "Erro inesperado ao enviar e-mail de revisão para %s",
                review.reviewer.email,
            )
        _log_review_email_error(review, exc)
