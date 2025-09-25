#!/usr/bin/env python3
"""
Utilitários para gerenciamento de fontes no FPDF.
Solução para evitar problemas de caminhos absolutos em produção.
"""

import os
import tempfile
import shutil
from fpdf import FPDF

def setup_fonts_safe(pdf, fallback_to_arial=True):
    """
    Configura fontes de forma segura, sempre usando Arial.
    
    Args:
        pdf: Instância do FPDF
        fallback_to_arial: Parâmetro mantido para compatibilidade (sempre True)
        
    Returns:
        str: Nome da fonte configurada (sempre 'Arial')
    """
    # Sempre retorna Arial para máxima compatibilidade
    return 'Arial'

def set_font_safe(pdf, font_name, style='', size=12):
    """
    Define fonte de forma segura, sempre usando Arial.
    
    Args:
        pdf: Instância do FPDF
        font_name: Nome da fonte (ignorado, sempre usa Arial)
        style: Estilo da fonte ('', 'B', 'I', 'BI')
        size: Tamanho da fonte
    """
    try:
        pdf.set_font('Arial', style, size)
    except Exception:
        try:
            pdf.set_font('Helvetica', style, size)
        except Exception:
            pdf.set_font('Times', style, size)

def create_pdf_with_safe_fonts():
    """
    Cria uma instância de PDF com fontes configuradas de forma segura.
    
    Returns:
        tuple: (pdf_instance, font_name)
    """
    pdf = FPDF()
    font_name = 'Arial'  # Sempre usa Arial
    return pdf, font_name