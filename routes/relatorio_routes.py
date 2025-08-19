from flask import Blueprint

relatorio_routes = Blueprint("relatorio_routes", __name__)

from flask import render_template, request, redirect, url_for, flash, send_from_directory, send_file, abort
from flask_login import login_required, current_user
from io import BytesIO
from openpyxl import Workbook
from extensions import db
from models import (
    Evento,
    Oficina,
    Inscricao,
    LoteTipoInscricao,
    EventoInscricaoTipo,
    Ministrante,
    Checkin,
    Sorteio,
)
from datetime import datetime
import os

from services.ia_service import gerar_texto_relatorio


def montar_relatorio_mensagem(incluir_financeiro=False):
    from sqlalchemy import func
    
    # Se quiser só as oficinas do cliente, verifique se current_user é admin ou cliente:
    is_admin = (current_user.tipo == 'admin')
    if is_admin:
        total_oficinas = Oficina.query.count()
        # Buscar todas as oficinas para calcular o total de vagas considerando o tipo_inscricao
        oficinas = Oficina.query.options(db.joinedload(Oficina.inscritos)).all()
        total_inscricoes = Inscricao.query.count()
        eventos = Evento.query.all()
    else:
        total_oficinas = Oficina.query.filter_by(cliente_id=current_user.id).count()
        # Buscar oficinas do cliente para calcular o total de vagas considerando o tipo_inscricao
        oficinas = Oficina.query.filter_by(cliente_id=current_user.id).options(db.joinedload(Oficina.inscritos)).all()
        total_inscricoes = Inscricao.query.join(Oficina).filter(Oficina.cliente_id == current_user.id).count()
        eventos = Evento.query.filter_by(cliente_id=current_user.id).all()

    financeiro_por_evento = {}
    if incluir_financeiro:
        inscricoes_q = (
            Inscricao.query.join(Evento)
            .filter(Inscricao.status_pagamento == 'approved')
        )
        if not is_admin:
            inscricoes_q = inscricoes_q.filter(Evento.cliente_id == current_user.id)
        inscricoes = inscricoes_q.options(db.joinedload(Inscricao.evento)).all()

        for ins in inscricoes:
            evento = ins.evento
            if not evento:
                continue
            valor = 0.0
            if ins.lote_id and evento.habilitar_lotes:
                lti = LoteTipoInscricao.query.filter_by(
                    lote_id=ins.lote_id,
                    tipo_inscricao_id=ins.tipo_inscricao_id,
                ).first()
                if lti:
                    valor = float(lti.preco)
            else:
                eit = EventoInscricaoTipo.query.get(ins.tipo_inscricao_id)
                if eit:
                    valor = float(eit.preco)

            financeiro_por_evento[evento.id] = financeiro_por_evento.get(evento.id, 0.0) + valor
    
    # Novo cálculo do total_vagas conforme solicitado:
    # 1. Soma as vagas das oficinas com tipo_inscricao 'com_inscricao_com_limite'
    # 2. Soma o número de inscritos nas oficinas com tipo_inscricao 'com_inscricao_sem_limite'
    total_vagas = 0
    for of in oficinas:
        if of.tipo_inscricao == 'com_inscricao_com_limite':
            total_vagas += of.vagas
        elif of.tipo_inscricao == 'com_inscricao_sem_limite':
            total_vagas += len(of.inscritos)
    
    # Cálculo de adesão
    percentual_adesao = (total_inscricoes / total_vagas) * 100 if total_vagas > 0 else 0

    # Monta a mensagem com emojis e loop
    total_eventos = len(eventos)
    mensagem = (
        "📊 *Relatório do Sistema*\n\n"
        f"✅ *Total de Eventos:* {total_eventos}\n"
        f"✅ *Total de Oficinas:* {total_oficinas}\n"
        f"✅ *Vagas Ofertadas:* {total_vagas}\n"
        f"✅ *Vagas Preenchidas:* {total_inscricoes}\n"
        f"✅ *% de Adesão:* {percentual_adesao:.2f}%\n\n"
        "----------------------------------------\n"
    )
    
    # Agrupar oficinas por evento
    for evento in eventos:
        # Buscar oficinas deste evento
        if is_admin:
            oficinas_evento = Oficina.query.filter_by(evento_id=evento.id).all()
        else:
            oficinas_evento = Oficina.query.filter_by(evento_id=evento.id, cliente_id=current_user.id).all()
        
        # Se não houver oficinas neste evento, pular
        if not oficinas_evento:
            continue
            
        # Adicionar cabeçalho do evento
        mensagem += f"\n🎪 *EVENTO: {evento.nome}*\n"
        mensagem += f"📌 *Total de Oficinas no Evento:* {len(oficinas_evento)}\n"
        if incluir_financeiro:
            receita = financeiro_por_evento.get(evento.id, 0.0)
            mensagem += f"💰 *Receita:* R$ {receita:.2f}\n"
        
        # Adicionar dados de cada oficina do evento
        for oficina in oficinas_evento:
            # Conta inscritos
            num_inscritos = Inscricao.query.filter_by(oficina_id=oficina.id).count()
            
            # Calcula ocupação considerando o tipo de inscrição
            if oficina.tipo_inscricao == 'sem_inscricao':
                ocupacao = 0  # Não é relevante calcular ocupação
                vagas_texto = "N/A (sem inscrição)"
            elif oficina.tipo_inscricao == 'com_inscricao_sem_limite':
                ocupacao = 100  # Sempre 100% pois aceita qualquer número de inscritos
                vagas_texto = "Ilimitadas"
            else:  # com_inscricao_com_limite
                ocupacao = (num_inscritos / oficina.vagas)*100 if oficina.vagas else 0
                vagas_texto = str(oficina.vagas)
            
            # Determina o texto amigável para o tipo de inscrição
            tipo_inscricao_texto = "Sem inscrição"
            if oficina.tipo_inscricao == "com_inscricao_sem_limite":
                tipo_inscricao_texto = "Inscrição sem limite de vagas"
            elif oficina.tipo_inscricao == "com_inscricao_com_limite":
                tipo_inscricao_texto = "Inscrição com vagas limitadas"

            mensagem += (
                f"\n🎓 *Oficina:* {oficina.titulo}\n"
                f"🔹 *Tipo de Inscrição:* {tipo_inscricao_texto}\n"
                f"🔹 *Vagas:* {vagas_texto}\n"
                f"🔹 *Inscritos:* {num_inscritos}\n"
                f"🔹 *Ocupação:* {ocupacao:.2f}%\n"
            )

            mensagem += "----------------------------------------\n"

    return mensagem


@relatorio_routes.route('/relatorio_mensagem')
@login_required
def relatorio_mensagem():
    incluir = request.args.get('financeiro') == '1'
    texto = montar_relatorio_mensagem(incluir)
    return render_template(
        'relatorio/relatorio_mensagem.html',
        texto_relatorio=texto,
        incluir_financeiro=incluir
    )


@relatorio_routes.route('/gerar_relatorio_evento', methods=['GET', 'POST'])
@login_required
def gerar_relatorio_evento():
    """Gera relatório de um evento com opção de download em Word/PDF."""
    # Carrega eventos do usuário atual
    is_admin = current_user.tipo == 'admin'
    if is_admin:
        eventos = Evento.query.all()
    else:
        eventos = Evento.query.filter_by(cliente_id=current_user.id).all()

    preview = None
    contexto_export = None
    selected_event = None

    if request.method == 'POST':
        evento_id = request.form.get('evento_id', type=int)
        selected_event = Evento.query.get(evento_id) if evento_id else None
        cabecalho = request.form.get('cabecalho', '')
        rodape = request.form.get('rodape', '')

        incluir_atividades = 'atividades' in request.form
        incluir_ministrantes = 'ministrantes' in request.form
        incluir_datas = 'datas' in request.form
        incluir_sorteio = 'sorteio' in request.form
        incluir_num_inscritos = 'num_inscritos' in request.form
        incluir_lista_nominal = 'lista_nominal' in request.form
        incluir_checkins = 'checkins' in request.form

        dados = {}
        if selected_event:
            dados['evento'] = selected_event

            if incluir_atividades or incluir_ministrantes or incluir_datas:
                oficinas = Oficina.query.filter_by(evento_id=selected_event.id).all()
                if incluir_atividades:
                    dados['atividades'] = oficinas
                if incluir_ministrantes:
                    ministrantes = [
                        of.ministrante_obj for of in oficinas if of.ministrante_obj
                    ]
                    dados['ministrantes'] = ministrantes
                if incluir_datas:
                    datas = []
                    for of in oficinas:
                        for dia in of.dias:
                            datas.append(
                                {
                                    'oficina': of.titulo,
                                    'data': dia.data,
                                    'inicio': dia.horario_inicio,
                                    'fim': dia.horario_fim,
                                }
                            )
                    dados['datas'] = datas

            if incluir_sorteio:
                dados['sorteios'] = Sorteio.query.filter_by(evento_id=selected_event.id).all()

            if incluir_num_inscritos or incluir_lista_nominal or incluir_checkins:
                inscricoes = Inscricao.query.filter_by(evento_id=selected_event.id).all()
                if incluir_num_inscritos:
                    dados['num_inscritos'] = len(inscricoes)
                if incluir_lista_nominal:
                    dados['lista_nominal'] = [ins.usuario.nome for ins in inscricoes]
                if incluir_checkins:
                    dados['checkins'] = Checkin.query.filter_by(evento_id=selected_event.id).all()

        texto_base = gerar_texto_relatorio(dados)

        preview = f"{cabecalho}\n{texto_base}\n{rodape}".strip()
        contexto_export = {
            'cabecalho': cabecalho,
            'rodape': rodape,
            'texto': texto_base,
            'dados': dados,
        }

        download = request.form.get('download')
        if download in {'pdf', 'word'} and selected_event:
            conteudo = f"{cabecalho}\n\n{texto_base}\n\n{rodape}".strip()
            buffer = BytesIO()
            if download == 'pdf':
                from reportlab.pdfgen import canvas

                c = canvas.Canvas(buffer)
                y = 800
                for linha in conteudo.split('\n'):
                    c.drawString(40, y, linha)
                    y -= 15
                c.save()
                buffer.seek(0)
                nome = 'relatorio_evento.pdf'
                return send_file(buffer, as_attachment=True, download_name=nome, mimetype='application/pdf')
            else:  # word via RTF simples
                conteudo_rtf = '{\\rtf1\n' + conteudo.replace('\n', '\\par\n') + '\n}'
                buffer.write(conteudo_rtf.encode('utf-8'))
                buffer.seek(0)
                nome = 'relatorio_evento.rtf'
                return send_file(buffer, as_attachment=True, download_name=nome, mimetype='application/rtf')

    return render_template(
        'relatorio/gerar_relatorio.html',
        eventos=eventos,
        preview=preview,
        contexto_export=contexto_export,
        selected_event=selected_event,
    )


@relatorio_routes.route('/relatorios/<path:filename>')
@login_required
def get_relatorio_file(filename):
    # Ajuste o caminho para a pasta de relatórios
    pasta_uploads = os.path.join('uploads', 'relatorios')
    return send_from_directory(pasta_uploads, filename)

@relatorio_routes.route('/gerar_modelo/<string:tipo>', methods=['GET'])
@login_required
def gerar_modelo(tipo):
    """
    Gera um arquivo Excel (XLSX) em memória com colunas obrigatórias
    para importação de Usuários ou Oficinas. Retorna o arquivo para download.
    
    Use:
      /gerar_modelo/usuarios  -> para Modelo de Usuários
      /gerar_modelo/oficinas  -> para Modelo de Oficinas
    """
    # 1. Cria o Workbook em memória
    wb = Workbook()
    ws = wb.active

    if tipo.lower() == 'usuarios':
        ws.title = "ModeloUsuarios"

        # Exemplo de colunas do model Usuario:
        #   nome, cpf, email, senha, formacao, tipo
        colunas = [
            "nome", "cpf", "email", "senha", "formacao", "tipo"
        ]
        ws.append(colunas)

        # Exemplo de linha de demonstração
        ws.append([
            "Fulano de Tal",     # nome
            "123.456.789-00",    # cpf
            "fulano@email.com",  # email
            "senha123",          # senha
            "Graduado em X",     # formacao
            "participante"       # tipo: pode ser admin, cliente, participante, etc.
        ])

        # Nome do arquivo para download
        nome_arquivo = "modelo_usuarios.xlsx"

    elif tipo.lower() == 'oficinas':
        ws.title = "ModeloOficinas"

        # Exemplo de colunas do model Oficina (e OficinaDia):
        #   titulo, descricao, ministrante_id, vagas, carga_horaria,
        #   estado, cidade, datas, horarios_inicio, horarios_fim
        colunas = [
            "titulo", "descricao", "ministrante_id",
            "vagas", "carga_horaria", "estado", "cidade",
            "datas", "horarios_inicio", "horarios_fim"
        ]
        ws.append(colunas)

        # Exemplo de linha de demonstração
        ws.append([
            "Oficina Exemplo",              # titulo
            "Descricao da oficina",         # descricao
            1,                              # ministrante_id
            30,                             # vagas
            "4h",                           # carga_horaria
            "SP",                           # estado
            "São Paulo",                    # cidade
            "01/09/2025,02/09/2025",        # datas (separado por vírgula)
            "08:00,08:00",                  # horarios_inicio (mesma quantidade de itens de datas)
            "12:00,12:00"                   # horarios_fim
        ])

        nome_arquivo = "modelo_oficinas.xlsx"

    else:
        # Se não for "usuarios" nem "oficinas", retorna 400 (Bad Request)
        abort(400, "Tipo inválido. Use 'usuarios' ou 'oficinas'.")

    # 2. Salva o Workbook em um buffer de memória
    output = BytesIO()
    wb.save(output)
    output.seek(0)  # Volta para o início do buffer

    # 3. Retorna o arquivo
    return send_file(
        output,
        as_attachment=True,
        download_name=nome_arquivo,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


