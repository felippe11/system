"""Backward-compatible wrapper around the unified email service.

This module existed historically to talk directly to the Mailjet API. It is kept
as a thin wrapper so legacy imports continue to function while all logic lives in
:mod:`services.email_service`.
"""

from __future__ import annotations

import warnings
from typing import Iterable, Optional

from services.email_service import send_email


def send_via_mailjet(
    *,
    to_email: str | Iterable[str],
    subject: str,
    text: Optional[str] = None,
    html: Optional[str] = None,
    attachments: Optional[Iterable[str]] = None,
):
    """Send email using the new unified service.

    Parameters mirror the legacy implementation so existing callers keep
    working. The function now delegates to :func:`services.email_service.send_email`
    and therefore supports both Mailjet and SMTP backends transparently.
    """
    warnings.warn(
        "send_via_mailjet is deprecated; use services.email_service.send_email",
        DeprecationWarning,
        stacklevel=2,
    )

    recipients = to_email if isinstance(to_email, (list, tuple, set)) else [to_email]
    return send_email(
        subject=subject,
        to=recipients,
        text=text,
        html=html,
        attachments=attachments,
    )


__all__ = ["send_via_mailjet"]
