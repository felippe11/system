#!/usr/bin/env python3
"""Utilitários para gerenciamento de fontes com suporte a Unicode no FPDF."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fpdf import FPDF

logger = logging.getLogger(__name__)

DEFAULT_FONT_FAMILY = "DejaVuSans"
_FONT_FILES = {
    "": "DejaVuSans.ttf",
    "B": "DejaVuSans-Bold.ttf",
    "I": "DejaVuSans-Oblique.ttf",
}


def _fonts_directory() -> Path:
    """Return the absolute path to the bundled fonts directory."""

    return Path(__file__).resolve().parent / "fonts"


def _register_unicode_fonts(pdf: FPDF, family: str = DEFAULT_FONT_FAMILY) -> Optional[str]:
    """Register bundled DejaVu fonts with unicode support.

    If the TrueType font cache contains outdated absolute paths (common when the
    metrics file was generated on another OS), we normalise the internal FPDF
    references so that the current runtime path is always used.
    """

    font_dir = _fonts_directory()
    registered = False

    for style, filename in _FONT_FILES.items():
        font_path = font_dir / filename
        if not font_path.exists():
            logger.warning("Fonte %s não encontrada em %s", filename, font_path)
            continue

        try:
            pdf.add_font(family, style, str(font_path), uni=True)
        except RuntimeError as exc:
            logger.exception(
                "Falha ao registrar fonte %s (%s): %s",
                filename,
                style,
                exc,
            )
            continue

        fontkey = family.lower() + style.upper()
        if fontkey in pdf.fonts:
            pdf.fonts[fontkey]["ttffile"] = str(font_path)
        if fontkey in pdf.font_files:
            pdf.font_files[fontkey]["ttffile"] = str(font_path)
        registered = True

    if registered:
        pdf._isunicode = True  # pyfpdf usa este sinalizador para UTF-16
        return family

    return None


def setup_fonts_safe(pdf: FPDF, fallback_to_arial: bool = True) -> str:
    """Configura fontes com suporte a Unicode retornando o nome da família usada."""

    unicode_family = _register_unicode_fonts(pdf)
    if unicode_family:
        return unicode_family

    logger.warning(
        "Fontes DejaVu indisponíveis; usando fontes padrão do FPDF."
    )
    return "Arial" if fallback_to_arial else "Helvetica"


def set_font_safe(pdf: FPDF, font_name: str, style: str = "", size: int = 12) -> None:
    """Define uma fonte tentando manter unicode e aplicando fallbacks."""

    style = style.upper()

    # pyfpdf não fornece variante BI por padrão; usar combinações conhecidas
    primary_style = style
    fallback_style = ""
    if style == "BI" and font_name != "Arial":
        # Preferir negrito ao combinar, pois transmite melhor o destaque
        fallback_style = "I"
        primary_style = "B"

    for candidate in (primary_style, fallback_style, ""):
        if candidate is None:
            continue
        try:
            pdf.set_font(font_name, candidate, size)
            return
        except Exception:  # noqa: BLE001 - qualquer falha cai no fallback
            continue

    # Último recurso: fontes core do FPDF
    for fallback_family in ("Arial", "Helvetica", "Times"):
        try:
            pdf.set_font(fallback_family, style, size)
            return
        except Exception:
            continue

    # Se nada funcionar, deixamos o FPDF levantar o erro padrão
    pdf.set_font(font_name, style, size)


def create_pdf_with_safe_fonts() -> tuple[FPDF, str]:
    """Cria uma instância de PDF preparada para textos Unicode."""

    pdf = FPDF()
    font_name = setup_fonts_safe(pdf)
    return pdf, font_name
