from datetime import datetime
import logging
import os
from typing import TYPE_CHECKING

from flask import current_app, render_template_string

from extensions import db
from models import Checkin, Oficina, Evento, DeclaracaoComparecimento
from models.user import Usuario  # Cliente não é usado aqui
from models.certificado import DeclaracaoTemplate

if TYPE_CHECKING:
    # Apenas para type checkers/IDE — não executa em runtime
    from weasyprint import HTML, CSS  # noqa: F401

logger = logging.getLogger(__name__)


# ------------------------------- #
# Helpers
# ------------------------------- #
def _import_weasyprint():
    """
    Importa o WeasyPrint apenas quando necessário.
    Evita quebrar a inicialização do app (db upgrade, etc.)
    caso as DLLs não estejam presentes no Windows.
    """
    try:
        from weasyprint import HTML, CSS  # type: ignore
        return HTML, CSS
    except Exception as e:
        raise RuntimeError(
            "WeasyPrint não está disponível no ambiente. "
            "No Windows, prefira instalar: pip install \"weasyprint[binary]==66.0\" "
            "ou configure as dependências do GTK/Pango no PATH. "
            "Alternativamente, gere o PDF em um ambiente Linux/WSL."
        ) from e


# ------------------------------- #
# API pública
# ------------------------------- #
def gerar_declaracao_participacao(usuario_id, evento_id, tipo='individual'):
    """Gera declaração de participação para um usuário."""
    try:
        usuario = Usuario.query.get(usuario_id)
        evento = Evento.query.get(evento_id)

        if not usuario or not evento:
            logger.error(f"Usuário {usuario_id} ou evento {evento_id} não encontrado")
            return None

        # Buscar template
        template = _buscar_template_declaracao(evento.cliente_id, tipo)
        if not template:
            logger.warning(f"Template de declaração não encontrado para cliente {evento.cliente_id}")
            template = _criar_template_padrao(evento.cliente_id, tipo)

        # Calcular dados de participação
        dados_participacao = _calcular_dados_participacao(usuario_id, evento_id)

        # Gerar arquivo PDF
        arquivo_path = _gerar_arquivo_declaracao(usuario, evento, dados_participacao, template)

        return arquivo_path

    except Exception as e:
        logger.error(f"Erro ao gerar declaração: {str(e)}")
        return None


def gerar_declaracao_coletiva(evento_id, usuarios_ids=None):
    """Gera declaração coletiva para múltiplos participantes."""
    try:
        evento = Evento.query.get(evento_id)
        if not evento:
            logger.error(f"Evento {evento_id} não encontrado")
            return None

        # Se não especificado, buscar todos os participantes
        if not usuarios_ids:
            usuarios_ids = db.session.query(Checkin.usuario_id)\
                .filter(Checkin.evento_id == evento_id)\
                .distinct().all()
            usuarios_ids = [uid[0] for uid in usuarios_ids]

        # Buscar dados dos usuários
        usuarios = Usuario.query.filter(Usuario.id.in_(usuarios_ids)).all()

        # Buscar template coletivo
        template = _buscar_template_declaracao(evento.cliente_id, 'coletiva')
        if not template:
            template = _criar_template_padrao(evento.cliente_id, 'coletiva')

        # Calcular dados de participação para cada usuário
        dados_usuarios = []
        for usuario in usuarios:
            dados = _calcular_dados_participacao(usuario.id, evento_id)
            dados['usuario'] = usuario
            dados_usuarios.append(dados)

        # Gerar arquivo PDF
        arquivo_path = _gerar_arquivo_declaracao_coletiva(evento, dados_usuarios, template)

        return arquivo_path

    except Exception as e:
        logger.error(f"Erro ao gerar declaração coletiva: {str(e)}")
        return None


def liberar_declaracoes_evento(evento_id, template_id=None):
    """Libera declarações de comparecimento para todos os participantes."""
    evento = Evento.query.get(evento_id)
    if not evento:
        raise ValueError("Evento não encontrado")

    template = None
    if template_id:
        template = DeclaracaoTemplate.query.filter_by(
            id=template_id, cliente_id=evento.cliente_id
        ).first()
    if not template:
        template = DeclaracaoTemplate.query.filter_by(
            cliente_id=evento.cliente_id, ativo=True
        ).first()
    if not template:
        raise ValueError("Template não encontrado")

    participantes = (
        db.session.query(Checkin.usuario_id)
        .filter_by(evento_id=evento_id)
        .distinct()
        .all()
    )

    for (usuario_id,) in participantes:
        declaracao = DeclaracaoComparecimento.query.filter_by(
            evento_id=evento_id, usuario_id=usuario_id
        ).first()
        if not declaracao:
            declaracao = DeclaracaoComparecimento(
                cliente_id=evento.cliente_id,
                evento_id=evento_id,
                usuario_id=usuario_id,
                titulo=template.nome,
                conteudo=template.conteudo,
                template_id=template.id,
            )
            db.session.add(declaracao)

        declaracao.status = "liberada"
        declaracao.data_liberacao = datetime.utcnow()
        declaracao.template_id = template.id
        declaracao.titulo = template.nome
        declaracao.conteudo = template.conteudo

    db.session.commit()
    return len(participantes)


# ------------------------------- #
# Templates
# ------------------------------- #
def _buscar_template_declaracao(cliente_id, tipo):
    """Busca template de declaração ativo."""
    return DeclaracaoTemplate.query.filter_by(
        cliente_id=cliente_id,
        tipo=tipo,
        ativo=True
    ).first()


def _criar_template_padrao(cliente_id, tipo):
    """Cria template padrão se não existir."""
    try:
        if tipo == 'individual':
            conteudo = """
            <div style="text-align: center; font-family: Arial, sans-serif; padding: 50px;">
                <h1 style="color: #2c3e50; margin-bottom: 30px;">DECLARAÇÃO DE PARTICIPAÇÃO</h1>

                <p style="font-size: 16px; line-height: 1.6; margin: 30px 0;">
                    Declaramos que <strong>{{ usuario.nome }}</strong>,
                    portador(a) do CPF {{ usuario.cpf }},
                    participou do evento <strong>"{{ evento.nome }}"</strong>,
                    realizado no período de {{ evento.data_inicio.strftime('%d/%m/%Y') }}
                    {% if evento.data_fim %}a {{ evento.data_fim.strftime('%d/%m/%Y') }}{% endif %}.
                </p>

                <p style="font-size: 16px; line-height: 1.6; margin: 30px 0;">
                    O participante esteve presente em {{ dados.total_checkins }} atividade(s),
                    totalizando {{ dados.carga_horaria }} hora(s) de participação.
                </p>

                <div style="margin-top: 80px;">
                    <p>{{ evento.cidade }}, {{ data_atual.strftime('%d de %B de %Y') }}</p>
                </div>

                <div style="margin-top: 100px; border-top: 1px solid #000; width: 300px; margin-left: auto; margin-right: auto; padding-top: 10px;">
                    <p><strong>Coordenação do Evento</strong></p>
                </div>
            </div>
            """
        else:  # coletiva
            conteudo = """
            <div style="font-family: Arial, sans-serif; padding: 50px;">
                <h1 style="text-align: center; color: #2c3e50; margin-bottom: 30px;">DECLARAÇÃO COLETIVA DE PARTICIPAÇÃO</h1>

                <p style="font-size: 16px; line-height: 1.6; margin: 30px 0;">
                    Declaramos que os participantes relacionados abaixo estiveram presentes no evento
                    <strong>"{{ evento.nome }}"</strong>, realizado no período de
                    {{ evento.data_inicio.strftime('%d/%m/%Y') }}
                    {% if evento.data_fim %}a {{ evento.data_fim.strftime('%d/%m/%Y') }}{% endif %}.
                </p>

                <table style="width: 100%; border-collapse: collapse; margin: 30px 0;">
                    <thead>
                        <tr style="background-color: #f8f9fa;">
                            <th style="border: 1px solid #ddd; padding: 12px; text-align: left;">Nome</th>
                            <th style="border: 1px solid #ddd; padding: 12px; text-align: left;">CPF</th>
                            <th style="border: 1px solid #ddd; padding: 12px; text-align: center;">Atividades</th>
                            <th style="border: 1px solid #ddd; padding: 12px; text-align: center;">Carga Horária</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for dados in dados_usuarios %}
                        <tr>
                            <td style="border: 1px solid #ddd; padding: 12px;">{{ dados.usuario.nome }}</td>
                            <td style="border: 1px solid #ddd; padding: 12px;">{{ dados.usuario.cpf }}</td>
                            <td style="border: 1px solid #ddd; padding: 12px; text-align: center;">{{ dados.total_checkins }}</td>
                            <td style="border: 1px solid #ddd; padding: 12px; text-align: center;">{{ dados.carga_horaria }}h</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>

                <div style="margin-top: 80px; text-align: center;">
                    <p>{{ evento.cidade }}, {{ data_atual.strftime('%d de %B de %Y') }}</p>
                </div>

                <div style="margin-top: 100px; text-align: center;">
                    <div style="border-top: 1px solid #000; width: 300px; margin: 0 auto; padding-top: 10px;">
                        <p><strong>Coordenação do Evento</strong></p>
                    </div>
                </div>
            </div>
            """

        template = DeclaracaoTemplate(
            cliente_id=cliente_id,
            nome=f"Template Padrão - {tipo.title()}",
            tipo=tipo,
            conteudo=conteudo,
            ativo=True
        )

        db.session.add(template)
        db.session.commit()

        return template

    except Exception as e:
        logger.error(f"Erro ao criar template padrão: {str(e)}")
        db.session.rollback()
        return None


# ------------------------------- #
# Cálculo de participação
# ------------------------------- #
def _calcular_dados_participacao(usuario_id, evento_id):
    """Calcula dados de participação do usuário no evento."""
    # Buscar checkins
    checkins = Checkin.query.filter_by(
        usuario_id=usuario_id,
        evento_id=evento_id
    ).all()

    # Buscar oficinas participadas
    oficinas_ids = [c.oficina_id for c in checkins if c.oficina_id]
    oficinas = Oficina.query.filter(Oficina.id.in_(oficinas_ids)).all() if oficinas_ids else []

    # Calcular carga horária
    carga_horaria = sum(oficina.carga_horaria or 0 for oficina in oficinas)

    return {
        'total_checkins': len(checkins),
        'oficinas_participadas': oficinas,
        'carga_horaria': carga_horaria,
        'datas_participacao': [c.data_checkin for c in checkins if c.data_checkin]
    }


# ------------------------------- #
# Geração de arquivos (PDF)
# ------------------------------- #
def _gerar_arquivo_declaracao(usuario, evento, dados_participacao, template):
    """Gera arquivo PDF da declaração individual."""
    try:
        # Criar diretório se não existir
        declaracoes_dir = os.path.join(current_app.static_folder, 'declaracoes')
        os.makedirs(declaracoes_dir, exist_ok=True)

        # Nome do arquivo
        filename = f"declaracao_{usuario.id}_{evento.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        arquivo_path = os.path.join(declaracoes_dir, filename)

        # Renderizar template
        html_content = render_template_string(
            template.conteudo,
            usuario=usuario,
            evento=evento,
            dados=dados_participacao,
            data_atual=datetime.now()
        )

        # Importar e gerar PDF
        HTML, CSS = _import_weasyprint()
        HTML(string=html_content).write_pdf(arquivo_path)

        return f"declaracoes/{filename}"

    except Exception as e:
        logger.error(f"Erro ao gerar arquivo de declaração: {str(e)}")
        return None


def _gerar_arquivo_declaracao_coletiva(evento, dados_usuarios, template):
    """Gera arquivo PDF da declaração coletiva."""
    try:
        # Criar diretório se não existir
        declaracoes_dir = os.path.join(current_app.static_folder, 'declaracoes')
        os.makedirs(declaracoes_dir, exist_ok=True)

        # Nome do arquivo
        filename = f"declaracao_coletiva_{evento.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        arquivo_path = os.path.join(declaracoes_dir, filename)

        # Renderizar template
        html_content = render_template_string(
            template.conteudo,
            evento=evento,
            dados_usuarios=dados_usuarios,
            data_atual=datetime.now()
        )

        # Importar e gerar PDF
        HTML, CSS = _import_weasyprint()
        HTML(string=html_content).write_pdf(arquivo_path)

        return f"declaracoes/{filename}"

    except Exception as e:
        logger.error(f"Erro ao gerar arquivo de declaração coletiva: {str(e)}")
        return None


# ------------------------------- #
# Consultas auxiliares
# ------------------------------- #
def listar_participantes_evento(evento_id):
    """Lista todos os participantes de um evento com dados de participação."""
    try:
        participantes = db.session.query(Usuario).join(
            Checkin, Usuario.id == Checkin.usuario_id
        ).filter(
            Checkin.evento_id == evento_id
        ).distinct().all()

        dados_participantes = []
        for participante in participantes:
            dados = _calcular_dados_participacao(participante.id, evento_id)
            dados['usuario'] = participante
            dados_participantes.append(dados)

        return dados_participantes

    except Exception as e:
        logger.error(f"Erro ao listar participantes: {str(e)}")
        return []


def validar_participacao(usuario_id, evento_id):
    """Valida se o usuário realmente participou do evento."""
    try:
        checkins = Checkin.query.filter_by(
            usuario_id=usuario_id,
            evento_id=evento_id
        ).count()

        return checkins > 0

    except Exception as e:
        logger.error(f"Erro ao validar participação: {str(e)}")
        return False
