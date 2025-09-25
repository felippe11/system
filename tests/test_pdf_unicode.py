"""Testes para garantir suporte a caracteres unicode nos PDFs."""

from font_utils import create_pdf_with_safe_fonts, set_font_safe


def test_pdf_generation_with_unicode(tmp_path):
    pdf, default_font = create_pdf_with_safe_fonts()
    pdf.add_page()
    set_font_safe(pdf, default_font, size=14)
    pdf.cell(0, 10, "Total arrecadado: € 1.234,56")

    output_path = tmp_path / "unicode.pdf"
    pdf.output(str(output_path))

    assert output_path.exists()
    assert output_path.stat().st_size > 0
