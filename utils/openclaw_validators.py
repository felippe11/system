from __future__ import annotations

import re
from typing import Any

from email_validator import EmailNotValidError, validate_email


class OpenClawValidationError(ValueError):
    """Raised when an OpenClaw payload fails validation."""


_NON_DIGIT_RE = re.compile(r"\D+")


def normalize_cpf(raw_cpf: str | None) -> str:
    """Return CPF with digits only after validating checksum."""
    digits = _NON_DIGIT_RE.sub("", raw_cpf or "")
    if len(digits) != 11:
        raise OpenClawValidationError("CPF deve conter 11 digitos.")
    if digits == digits[0] * 11:
        raise OpenClawValidationError("CPF invalido.")

    first_digit = _calculate_cpf_digit(digits[:9], start=10)
    second_digit = _calculate_cpf_digit(digits[:10], start=11)
    if digits[-2:] != f"{first_digit}{second_digit}":
        raise OpenClawValidationError("CPF invalido.")
    return digits


def format_cpf(cpf: str | None) -> str | None:
    """Return CPF in 000.000.000-00 format when possible."""
    if not cpf:
        return None
    digits = _NON_DIGIT_RE.sub("", cpf)
    if len(digits) != 11:
        return cpf
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def normalize_email(raw_email: str | None) -> str:
    """Return a normalized email address."""
    try:
        result = validate_email((raw_email or "").strip(), check_deliverability=False)
    except EmailNotValidError as exc:
        raise OpenClawValidationError("Email invalido.") from exc
    return result.normalized


def require_text(
    data: dict[str, Any],
    field_name: str,
    *,
    label: str | None = None,
) -> str:
    """Return a stripped text field or raise a validation error."""
    value = data.get(field_name)
    if value is None:
        raise OpenClawValidationError(f"{label or field_name} e obrigatorio.")
    text = str(value).strip()
    if not text:
        raise OpenClawValidationError(f"{label or field_name} e obrigatorio.")
    return text


def optional_int(data: dict[str, Any], field_name: str) -> int | None:
    """Parse an optional integer field."""
    value = data.get(field_name)
    if value in (None, "", "null"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise OpenClawValidationError(
            f"{field_name} deve ser um numero inteiro."
        ) from exc


def parse_bool(value: Any, *, default: bool = False) -> bool:
    """Parse a boolean query flag."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "t", "sim", "yes", "y"}:
        return True
    if normalized in {"0", "false", "f", "nao", "não", "no", "n"}:
        return False
    return default


def _calculate_cpf_digit(base_digits: str, *, start: int) -> int:
    total = 0
    for multiplier, digit in zip(range(start, 1, -1), base_digits):
        total += multiplier * int(digit)
    remainder = (total * 10) % 11
    return 0 if remainder == 10 else remainder
