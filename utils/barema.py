"""Utility helpers for working with barema configurations."""

from __future__ import annotations

from typing import Any, Dict


def _coerce_number(value: Any, default: float | int | None) -> float | int | None:
    """Convert values stored in baremas to numeric types.

    Args:
        value: Raw value that may be numeric, string or ``None``.
        default: Value returned when conversion is not possible.

    Returns:
        A float or int when conversion succeeds, otherwise ``default``.
    """
    if value in (None, ""):
        return default
    if isinstance(value, (int, float)):
        return value
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return int(number) if number.is_integer() else number


def normalize_barema_requisitos(barema: Any) -> Dict[str, Dict[str, Any]]:
    """Return a normalized ``requisitos`` mapping for any barema instance.

    For ``EventoBarema`` objects the structure is already stored in the
    ``requisitos`` attribute, but values may be strings. ``CategoriaBarema``
    stores the configuration under ``criterios`` using another schema. This
    helper converts both representations into the same dictionary format used by
    the templates and validation logic.

    Args:
        barema: ``EventoBarema`` or ``CategoriaBarema`` instance (or ``None``).

    Returns:
        A dictionary mapping criterion names to dicts containing ``min`` and
        ``max`` keys plus optional metadata such as ``descricao``.
    """
    if barema is None:
        return {}

    raw_requisitos = getattr(barema, "requisitos", None)
    if isinstance(raw_requisitos, dict) and raw_requisitos:
        normalized: Dict[str, Dict[str, Any]] = {}
        for key, faixa in raw_requisitos.items():
            label = str(key)
            if isinstance(faixa, dict):
                min_val = _coerce_number(faixa.get("min"), 0) or 0
                max_val = _coerce_number(faixa.get("max"), None)
                if max_val is None:
                    continue
                entry: Dict[str, Any] = {"min": min_val, "max": max_val}
                descricao = faixa.get("descricao")
                if descricao:
                    entry["descricao"] = descricao
                normalized[label] = entry
            else:
                max_val = _coerce_number(faixa, None)
                if max_val is None:
                    continue
                normalized[label] = {"min": 0, "max": max_val}
        if normalized:
            return normalized

    criterios = getattr(barema, "criterios", None)
    if isinstance(criterios, dict) and criterios:
        normalized: Dict[str, Dict[str, Any]] = {}
        for key, data in criterios.items():
            label = str(key)
            min_val = 0
            max_val = None
            descricao = None
            if isinstance(data, dict):
                label = data.get("nome") or label
                descricao = data.get("descricao")
                max_source = data.get("pontuacao_max")
                if max_source is None:
                    max_source = data.get("pontuacaoMax")
                if max_source is None:
                    max_source = data.get("max")
                max_val = _coerce_number(max_source, None)

                min_source = data.get("pontuacao_min")
                if min_source is None:
                    min_source = data.get("pontuacaoMin")
                if min_source is None:
                    min_source = data.get("min")
                min_val = _coerce_number(min_source, 0) or 0
            else:
                max_val = _coerce_number(data, None)
            if max_val is None:
                continue
            entry: Dict[str, Any] = {"min": min_val, "max": max_val}
            if descricao:
                entry["descricao"] = descricao
            normalized[str(label)] = entry
        return normalized

    return {}
