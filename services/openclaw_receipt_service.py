from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from flask import current_app
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from models import Inscricao
from utils.openclaw_validators import format_cpf


def generate_receipt_pdf(inscricao: Inscricao) -> str:
    """Generate a lightweight official receipt PDF for an enrollment."""
    output_dir = Path(_resolve_output_dir())
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"openclaw_comprovante_{inscricao.id}_{inscricao.qr_code_token[:8]}.pdf"
    pdf_path = output_dir / filename
    evento = inscricao.evento
    usuario = inscricao.usuario

    doc = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4

    doc.setTitle(f"Comprovante de Inscricao - {evento.nome if evento else inscricao.id}")
    doc.setFont("Helvetica-Bold", 20)
    doc.drawString(2 * cm, height - 3 * cm, "Comprovante de Inscricao")

    doc.setFont("Helvetica", 11)
    doc.drawString(2 * cm, height - 4.3 * cm, f"Inscricao ID: {inscricao.id}")
    doc.drawString(2 * cm, height - 5.0 * cm, f"Protocolo: {inscricao.qr_code_token}")
    doc.drawString(
        2 * cm,
        height - 5.7 * cm,
        f"Status do pagamento: {inscricao.status_pagamento}",
    )

    y = height - 7.2 * cm
    doc.setFont("Helvetica-Bold", 13)
    doc.drawString(2 * cm, y, "Participante")
    y -= 0.8 * cm
    doc.setFont("Helvetica", 11)
    doc.drawString(2 * cm, y, f"Nome: {usuario.nome}")
    y -= 0.6 * cm
    doc.drawString(2 * cm, y, f"CPF: {format_cpf(usuario.cpf) or usuario.cpf}")
    y -= 0.6 * cm
    doc.drawString(2 * cm, y, f"Email: {usuario.email}")
    y -= 0.6 * cm
    doc.drawString(2 * cm, y, f"Formacao: {usuario.formacao}")

    y -= 1.2 * cm
    doc.setFont("Helvetica-Bold", 13)
    doc.drawString(2 * cm, y, "Evento")
    y -= 0.8 * cm
    doc.setFont("Helvetica", 11)
    doc.drawString(2 * cm, y, f"Nome: {evento.nome if evento else 'Nao informado'}")
    y -= 0.6 * cm
    doc.drawString(
        2 * cm,
        y,
        f"Local: {evento.localizacao if evento and evento.localizacao else 'Nao informado'}",
    )
    y -= 0.6 * cm
    data_evento = (
        evento.get_data_formatada()
        if evento and hasattr(evento, "get_data_formatada")
        else "Nao informado"
    )
    doc.drawString(2 * cm, y, f"Periodo: {data_evento}")

    y -= 1.2 * cm
    doc.setFont("Helvetica-Oblique", 10)
    generated_at = datetime.now(UTC).strftime("%d/%m/%Y %H:%M UTC")
    doc.drawString(2 * cm, y, f"Gerado em {generated_at} pela API oficial.")

    y -= 0.8 * cm
    footer = (
        "A inscricao esta confirmada."
        if inscricao.status_pagamento == "approved"
        else "A inscricao existe, mas ainda depende da confirmacao do pagamento."
    )
    doc.drawString(2 * cm, y, footer)

    doc.showPage()
    doc.save()
    return str(pdf_path.resolve())


def _resolve_output_dir() -> str:
    static_root = current_app.config.get("STATIC_ROOT") or current_app.static_folder
    return os.path.join(static_root, "comprovantes", "openclaw")
