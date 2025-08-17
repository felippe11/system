"""Utilities for sending review notifications and logging failures."""

import logging
from flask import url_for
from mailjet_rest.client import ApiError

from extensions import db
from models import ReviewEmailLog
from services.mailjet_service import send_via_mailjet

logger = logging.getLogger(__name__)


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
    except ApiError as exc:  # pragma: no cover - network errors are rare
        logger.exception(
            "Erro ao enviar e-mail de revisão para %s", review.reviewer.email
        )
        db.session.add(
            ReviewEmailLog(
                review_id=review.id,
                recipient=review.reviewer.email,
                error=str(exc),
            )
        )
    except Exception as exc:  # pragma: no cover
        logger.exception(
            "Erro inesperado ao enviar e-mail de revisão para %s",
            review.reviewer.email,
        )
        db.session.add(
            ReviewEmailLog(
                review_id=review.id,
                recipient=review.reviewer.email,
                error=str(exc),
            )
        )
