# -*- coding: utf-8 -*-
"""
Serviço para exportação de relatórios em PDF e Excel
"""

import io
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

import pandas as pd
from flask import current_app
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfgen import canvas

from extensions import db
from models.compra import Compra
from models.orcamento import Orcamento, HistoricoOrcamento


class ExportService:
    """Serviço para exportação de dados em diferentes formatos"""
    
    @staticmethod
    def export_compras_excel(compras: List[Compra], filename: Optional[str] = None) -> str:
        """
        Exporta lista de compras para Excel
        
        Args:
            compras: Lista de compras para exportar
            filename: Nome do arquivo (opcional)
            
        Returns:
            Caminho do arquivo gerado
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"relatorio_compras_{timestamp}.xlsx"
        
        # Preparar dados
        data = []
        for compra in compras:
            data.append({
                'ID': compra.id,
                'Descrição': compra.descricao,
                'Valor': compra.valor,
                'Status': compra.status,
                'Data Criação': compra.data_criacao.strftime("%d/%m/%Y %H:%M") if compra.data_criacao else '',
                'Data Aprovação': compra.data_aprovacao.strftime("%d/%m/%Y %H:%M") if compra.data_aprovacao else '',
                'Fornecedor': compra.fornecedor,
                'Categoria': compra.categoria,
                'Observações': compra.observacoes or ''
            })
        
        # Criar DataFrame
        df = pd.DataFrame(data)
        
        # Salvar arquivo
        filepath = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'static/tmp'), filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Compras', index=False)
            
            # Ajustar largura das colunas
            worksheet = writer.sheets['Compras']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        return filepath
    
    @staticmethod
    def export_orcamentos_excel(orcamentos: List[Orcamento], filename: Optional[str] = None) -> str:
        """
        Exporta lista de orçamentos para Excel
        
        Args:
            orcamentos: Lista de orçamentos para exportar
            filename: Nome do arquivo (opcional)
            
        Returns:
            Caminho do arquivo gerado
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"relatorio_orcamentos_{timestamp}.xlsx"
        
        # Preparar dados dos orçamentos
        data_orcamentos = []
        for orcamento in orcamentos:
            data_orcamentos.append({
                'ID': orcamento.id,
                'Título': orcamento.titulo,
                'Valor Total': orcamento.valor_total,
                'Valor Aprovado': orcamento.valor_aprovado,
                'Status': orcamento.status,
                'Data Criação': orcamento.data_criacao.strftime("%d/%m/%Y %H:%M") if orcamento.data_criacao else '',
                'Data Aprovação': orcamento.data_aprovacao.strftime("%d/%m/%Y %H:%M") if orcamento.data_aprovacao else '',
                'Responsável': orcamento.responsavel,
                'Departamento': orcamento.departamento,
                'Observações': orcamento.observacoes or ''
            })
        
        # Criar DataFrame
        df_orcamentos = pd.DataFrame(data_orcamentos)
        
        # Salvar arquivo
        filepath = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'static/tmp'), filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df_orcamentos.to_excel(writer, sheet_name='Orçamentos', index=False)
            
            # Ajustar largura das colunas
            worksheet = writer.sheets['Orçamentos']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        return filepath
    
    @staticmethod
    def export_compras_pdf(compras: List[Compra], filename: Optional[str] = None) -> str:
        """
        Exporta lista de compras para PDF
        
        Args:
            compras: Lista de compras para exportar
            filename: Nome do arquivo (opcional)
            
        Returns:
            Caminho do arquivo gerado
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"relatorio_compras_{timestamp}.pdf"
        
        filepath = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'static/tmp'), filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Criar documento PDF
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        story = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Centralizado
        )
        
        # Título
        title = Paragraph("Relatório de Compras", title_style)
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Data de geração
        date_text = f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
        date_para = Paragraph(date_text, styles['Normal'])
        story.append(date_para)
        story.append(Spacer(1, 20))
        
        # Preparar dados da tabela
        data = [['ID', 'Descrição', 'Valor', 'Status', 'Fornecedor', 'Data Criação']]
        
        for compra in compras:
            data.append([
                str(compra.id),
                compra.descricao[:30] + '...' if len(compra.descricao) > 30 else compra.descricao,
                f"R$ {compra.valor:,.2f}",
                compra.status,
                compra.fornecedor[:20] + '...' if compra.fornecedor and len(compra.fornecedor) > 20 else (compra.fornecedor or ''),
                compra.data_criacao.strftime("%d/%m/%Y") if compra.data_criacao else ''
            ])
        
        # Criar tabela
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        
        # Construir PDF
        doc.build(story)
        
        return filepath
    
    @staticmethod
    def export_orcamentos_pdf(orcamentos: List[Orcamento], filename: Optional[str] = None) -> str:
        """
        Exporta lista de orçamentos para PDF
        
        Args:
            orcamentos: Lista de orçamentos para exportar
            filename: Nome do arquivo (opcional)
            
        Returns:
            Caminho do arquivo gerado
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"relatorio_orcamentos_{timestamp}.pdf"
        
        filepath = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'static/tmp'), filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Criar documento PDF
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        story = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Centralizado
        )
        
        # Título
        title = Paragraph("Relatório de Orçamentos", title_style)
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Data de geração
        date_text = f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
        date_para = Paragraph(date_text, styles['Normal'])
        story.append(date_para)
        story.append(Spacer(1, 20))
        
        # Preparar dados da tabela
        data = [['ID', 'Título', 'Valor Total', 'Status', 'Responsável', 'Data Criação']]
        
        for orcamento in orcamentos:
            data.append([
                str(orcamento.id),
                orcamento.titulo[:30] + '...' if len(orcamento.titulo) > 30 else orcamento.titulo,
                f"R$ {orcamento.valor_total:,.2f}",
                orcamento.status,
                orcamento.responsavel[:20] + '...' if orcamento.responsavel and len(orcamento.responsavel) > 20 else (orcamento.responsavel or ''),
                orcamento.data_criacao.strftime("%d/%m/%Y") if orcamento.data_criacao else ''
            ])
        
        # Criar tabela
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        
        # Construir PDF
        doc.build(story)
        
        return filepath
    
    @staticmethod
    def export_historico_orcamento_excel(historicos: List[HistoricoOrcamento], filename: Optional[str] = None) -> str:
        """
        Exporta histórico de alterações orçamentárias para Excel
        
        Args:
            historicos: Lista de históricos para exportar
            filename: Nome do arquivo (opcional)
            
        Returns:
            Caminho do arquivo gerado
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"historico_orcamentos_{timestamp}.xlsx"
        
        # Preparar dados
        data = []
        for historico in historicos:
            data.append({
                'ID': historico.id,
                'Orçamento ID': historico.orcamento_id,
                'Ação': historico.acao,
                'Valor Anterior': historico.valor_anterior,
                'Valor Novo': historico.valor_novo,
                'Status Anterior': historico.status_anterior,
                'Status Novo': historico.status_novo,
                'Usuário': historico.usuario,
                'Data': historico.data_alteracao.strftime("%d/%m/%Y %H:%M") if historico.data_alteracao else '',
                'Observações': historico.observacoes or ''
            })
        
        # Criar DataFrame
        df = pd.DataFrame(data)
        
        # Salvar arquivo
        filepath = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'static/tmp'), filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Histórico', index=False)
            
            # Ajustar largura das colunas
            worksheet = writer.sheets['Histórico']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        return filepath