"""
Serviço para geração de PDFs de listas de frequência
"""
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
import tempfile

from models.atividade_multipla_data import AtividadeMultiplaData, FrequenciaAtividade
from models.user import Usuario
from extensions import db
from flask import send_file


class PDFFrequenciaService:
    """Serviço para geração de PDFs de listas de frequência"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Configura estilos personalizados para o PDF"""
        # Estilo para título principal
        self.styles.add(ParagraphStyle(
            name='TituloPrincipal',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        ))
        
        # Estilo para subtítulo
        self.styles.add(ParagraphStyle(
            name='Subtitulo',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=15,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        ))
        
        # Estilo para cabeçalho da tabela
        self.styles.add(ParagraphStyle(
            name='CabecalhoTabela',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.white,
            fontName='Helvetica-Bold'
        ))
        
        # Estilo para dados da tabela
        self.styles.add(ParagraphStyle(
            name='DadosTabela',
            parent=self.styles['Normal'],
            fontSize=9,
            alignment=TA_LEFT,
            textColor=colors.black
        ))
        
        # Estilo para informações da atividade
        self.styles.add(ParagraphStyle(
            name='InfoAtividade',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=5,
            textColor=colors.black
        ))
    
    def gerar_pdf_frequencia_atividade(self, atividade_id):
        """Gera PDF da lista de frequência de uma atividade"""
        atividade = AtividadeMultiplaData.query.get(atividade_id)
        if not atividade:
            raise ValueError("Atividade não encontrada")
        
        # Criar arquivo temporário
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_path = temp_file.name
        temp_file.close()
        
        # Criar documento PDF
        doc = SimpleDocTemplate(
            temp_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Construir conteúdo
        story = []
        
        # Cabeçalho
        story.extend(self._criar_cabecalho(atividade))
        
        # Informações da atividade
        story.extend(self._criar_info_atividade(atividade))
        
        # Lista de frequência por data
        for data_atividade in atividade.get_datas_ordenadas():
            story.extend(self._criar_tabela_frequencia_data(atividade, data_atividade))
            story.append(Spacer(1, 20))
        
        # Resumo geral
        story.extend(self._criar_resumo_geral(atividade))
        
        # Gerar PDF
        doc.build(story)
        
        return temp_path
    
    def _criar_cabecalho(self, atividade):
        """Cria o cabeçalho do PDF"""
        story = []
        
        # Título principal
        story.append(Paragraph("LISTA DE FREQUÊNCIA", self.styles['TituloPrincipal']))
        
        # Nome da atividade
        story.append(Paragraph(atividade.titulo, self.styles['Subtitulo']))
        
        # Data de geração
        data_geracao = datetime.now().strftime("%d/%m/%Y às %H:%M")
        story.append(Paragraph(f"Gerado em: {data_geracao}", self.styles['InfoAtividade']))
        
        story.append(Spacer(1, 20))
        
        return story
    
    def _criar_info_atividade(self, atividade):
        """Cria seção com informações da atividade"""
        story = []
        
        # Informações básicas
        info_data = [
            ["<b>Tipo de Atividade:</b>", atividade.tipo_atividade.title()],
            ["<b>Carga Horária Total:</b>", f"{atividade.carga_horaria_total} horas"],
            ["<b>Local:</b>", f"{atividade.cidade}, {atividade.estado}"],
            ["<b>Número de Datas:</b>", str(atividade.get_total_datas())],
        ]
        
        if atividade.evento:
            info_data.append(["<b>Evento:</b>", atividade.evento.nome])
        
        # Criar tabela de informações
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        return story
    
    def _criar_tabela_frequencia_data(self, atividade, data_atividade):
        """Cria tabela de frequência para uma data específica"""
        story = []
        
        # Título da data
        data_str = data_atividade.data.strftime("%d/%m/%Y")
        horario_str = f"{data_atividade.horario_inicio.strftime('%H:%M')} - {data_atividade.horario_fim.strftime('%H:%M')}"
        story.append(Paragraph(f"<b>Data: {data_str} - Horário: {horario_str}</b>", self.styles['Subtitulo']))
        
        # Buscar frequências para esta data
        frequencias = FrequenciaAtividade.query.filter_by(
            atividade_id=atividade.id,
            data_atividade_id=data_atividade.id
        ).join(Usuario).order_by(Usuario.nome).all()
        
        if not frequencias:
            story.append(Paragraph("Nenhuma frequência registrada para esta data.", self.styles['InfoAtividade']))
            return story
        
        # Cabeçalho da tabela
        headers = ["Nome", "Email", "Manhã", "Tarde", "Dia Inteiro", "Status", "Carga Horária"]
        
        # Dados da tabela
        data = []
        for freq in frequencias:
            # Status de presença
            status_manha = "✓" if freq.presente_manha else "✗"
            status_tarde = "✓" if freq.presente_tarde else "✗"
            status_dia = "✓" if freq.presente_dia_inteiro else "✗"
            
            data.append([
                freq.usuario.nome,
                freq.usuario.email,
                status_manha,
                status_tarde,
                status_dia,
                freq.get_status_presenca(),
                f"{freq.get_carga_horaria_presenca():.1f}h"
            ])
        
        # Criar tabela
        table_data = [headers] + data
        table = Table(table_data, colWidths=[2*inch, 2*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1.2*inch, 1*inch])
        
        # Estilo da tabela
        table_style = [
            # Cabeçalho
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Dados
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),  # Nome
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),  # Email
            ('ALIGN', (2, 1), (-1, -1), 'CENTER'),  # Demais colunas
            
            # Bordas
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Alternância de cores
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]
        
        table.setStyle(TableStyle(table_style))
        story.append(table)
        
        # Estatísticas da data
        total_participantes = len(frequencias)
        presentes_manha = sum(1 for f in frequencias if f.presente_manha)
        presentes_tarde = sum(1 for f in frequencias if f.presente_tarde)
        presentes_dia = sum(1 for f in frequencias if f.presente_dia_inteiro)
        
        stats_text = f"Total de participantes: {total_participantes} | "
        stats_text += f"Presentes manhã: {presentes_manha} | "
        stats_text += f"Presentes tarde: {presentes_tarde} | "
        stats_text += f"Presentes dia inteiro: {presentes_dia}"
        
        story.append(Paragraph(stats_text, self.styles['InfoAtividade']))
        
        return story
    
    def _criar_resumo_geral(self, atividade):
        """Cria resumo geral da atividade"""
        story = []
        
        story.append(Spacer(1, 20))
        story.append(Paragraph("RESUMO GERAL", self.styles['Subtitulo']))
        
        # Calcular estatísticas gerais
        total_datas = atividade.get_total_datas()
        total_frequencias = FrequenciaAtividade.query.filter_by(atividade_id=atividade.id).count()
        
        # Buscar todos os usuários únicos que participaram
        usuarios_unicos = db.session.query(Usuario).join(FrequenciaAtividade).filter(
            FrequenciaAtividade.atividade_id == atividade.id
        ).distinct().count()
        
        # Calcular carga horária total presenciada
        carga_horaria_total = 0
        for data_atividade in atividade.datas:
            frequencias_data = FrequenciaAtividade.query.filter_by(
                atividade_id=atividade.id,
                data_atividade_id=data_atividade.id
            ).all()
            
            for freq in frequencias_data:
                carga_horaria_total += freq.get_carga_horaria_presenca()
        
        # Dados do resumo
        resumo_data = [
            ["<b>Total de Datas:</b>", str(total_datas)],
            ["<b>Total de Participantes:</b>", str(usuarios_unicos)],
            ["<b>Total de Frequências Registradas:</b>", str(total_frequencias)],
            ["<b>Carga Horária Total Presenciada:</b>", f"{carga_horaria_total:.1f} horas"],
            ["<b>Carga Horária da Atividade:</b>", f"{atividade.carga_horaria_total} horas"],
        ]
        
        resumo_table = Table(resumo_data, colWidths=[2.5*inch, 3.5*inch])
        resumo_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        story.append(resumo_table)
        
        return story


def gerar_pdf_frequencia_atividade(atividade_id):
    """Função auxiliar para gerar PDF de frequência"""
    service = PDFFrequenciaService()
    return service.gerar_pdf_frequencia_atividade(atividade_id)
