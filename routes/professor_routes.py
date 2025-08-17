# -*- coding: utf-8 -*-

from flask import render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import os
import io
import qrcode
from fpdf import FPDF
from PIL import Image

from extensions import db

    Evento, ProfessorBloqueado, SalaVisitacao, HorarioVisitacao,
    AgendamentoVisita, AlunoVisitante, ConfiguracaoAgendamento, Oficina,
    Inscricao,

)
from services.pdf_service import gerar_pdf_comprovante_agendamento
from . import routes

# Rotas para gerenciamento de agendamentos (para professores/participantes)
@routes.route('/professor/eventos_disponiveis')
@login_required
def eventos_disponiveis_professor():
    # Apenas participantes (professores) podem acessar
    if current_user.tipo != 'professor':
        flash('Acesso negado! Esta área é exclusiva para professores.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    # Buscar eventos disponíveis para agendamento
    eventos = Evento.query.filter(
        Evento.data_inicio <= datetime.utcnow(),
        Evento.data_fim >= datetime.utcnow(),
        Evento.status == 'ativo'
    ).all()
    
    return render_template(
        'professor/eventos_disponiveis.html',
        eventos=eventos
    )


@routes.route('/professor/evento/<int:evento_id>')
@login_required
def detalhes_evento_professor(evento_id):
    # Apenas participantes (professores) podem acessar
    if current_user.tipo != 'professor':
        flash('Acesso negado! Esta área é exclusiva para professores.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    evento = Evento.query.get_or_404(evento_id)
    
    # Verificar se o professor está bloqueado
    bloqueio = ProfessorBloqueado.query.filter_by(
        professor_id=current_user.id,
        evento_id=evento_id
    ).filter(ProfessorBloqueado.data_final >= datetime.utcnow()).first()
    
    # Buscar salas do evento
    salas = SalaVisitacao.query.filter_by(evento_id=evento_id).all()
    
    return render_template(
        'professor/detalhes_evento.html',
        evento=evento,
        bloqueio=bloqueio,
        salas=salas
    )


@routes.route('/professor/horarios_disponiveis/<int:evento_id>')
@login_required
def horarios_disponiveis_professor(evento_id):
    # Apenas participantes (professores) podem acessar
    if current_user.tipo != 'professor':
        flash('Acesso negado! Esta área é exclusiva para professores.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    # Verificar se o professor está bloqueado
    bloqueio = ProfessorBloqueado.query.filter_by(
        professor_id=current_user.id,
        evento_id=evento_id
    ).filter(ProfessorBloqueado.data_final >= datetime.utcnow()).first()
    
    if bloqueio:
        flash(f'Você está temporariamente bloqueado até {bloqueio.data_final.strftime("%d/%m/%Y")}. Motivo: {bloqueio.motivo}', 'danger')
        return redirect(url_for('routes.eventos_disponiveis_professor'))
    
    evento = Evento.query.get_or_404(evento_id)
    
    # Filtrar por data
    data_filtro = request.args.get('data')
    
    # Base da consulta - horários com vagas disponíveis
    query = HorarioVisitacao.query.filter_by(
        evento_id=evento_id
    ).filter(HorarioVisitacao.vagas_disponiveis > 0)
    
    # Filtrar apenas datas futuras (a partir de amanhã)
    amanha = datetime.now().date() + timedelta(days=1)
    query = query.filter(HorarioVisitacao.data >= amanha)
    
    # Aplicar filtro por data específica
    if data_filtro:
        data_filtrada = datetime.strptime(data_filtro, '%Y-%m-%d').date()
        query = query.filter(HorarioVisitacao.data == data_filtrada)
    
    # Ordenar por data e horário
    horarios = query.order_by(
        HorarioVisitacao.data,
        HorarioVisitacao.horario_inicio
    ).all()
    
    # Agrupar horários por data para facilitar a visualização
    horarios_por_data = {}
    for horario in horarios:
        data_str = horario.data.strftime('%Y-%m-%d')
        if data_str not in horarios_por_data:
            horarios_por_data[data_str] = []
        horarios_por_data[data_str].append(horario)
    
    return render_template(
        'professor/horarios_disponiveis.html',
        evento=evento,
        horarios_por_data=horarios_por_data,
        data_filtro=data_filtro
    )


@routes.route('/professor/criar_agendamento/<int:horario_id>', methods=['GET', 'POST'])
@login_required
def criar_agendamento_professor(horario_id):
    """Permite que professores ou participantes criem um agendamento."""
    # Apenas professores ou participantes podem acessar
    if current_user.tipo not in ('professor', 'participante'):
        msg = 'Acesso negado! Esta área é exclusiva para professores e participantes.'
        flash(msg, 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    horario = HorarioVisitacao.query.get_or_404(horario_id)
    evento = horario.evento

    config = ConfiguracaoAgendamento.query.filter_by(evento_id=evento.id).first()
    if config:
        permitidos = config.get_tipos_inscricao_list()
        if permitidos and current_user.tipo_inscricao_id not in permitidos:
            flash('Seu tipo de inscrição não permite agendar visitas neste evento.', 'danger')
            return redirect(url_for('routes.horarios_disponiveis_professor', evento_id=evento.id))
    
    # Verificar se o professor está bloqueado
    bloqueio = ProfessorBloqueado.query.filter_by(
        professor_id=current_user.id,
        evento_id=evento.id
    ).filter(ProfessorBloqueado.data_final >= datetime.utcnow()).first()
    
    if bloqueio:
        flash(f'Você está temporariamente bloqueado até {bloqueio.data_final.strftime("%d/%m/%Y")}. Motivo: {bloqueio.motivo}', 'danger')
        return redirect(url_for('routes.eventos_disponiveis_professor'))
    
    # Verificar se ainda há vagas
    if horario.vagas_disponiveis <= 0:
        flash('Não há mais vagas disponíveis para este horário!', 'warning')
        return redirect(url_for('routes.horarios_disponiveis_professor', evento_id=evento.id))
    
    # Buscar salas para seleção
    salas = SalaVisitacao.query.filter_by(evento_id=evento.id).all()
    
    if request.method == 'POST':
        # Validar campos obrigatórios
        escola_nome = request.form.get('escola_nome')
        escola_codigo_inep = request.form.get('escola_codigo_inep')
        turma = request.form.get('turma')
        nivel_ensino = request.form.get('nivel_ensino')
        quantidade_alunos = request.form.get('quantidade_alunos', type=int)
        salas_selecionadas = request.form.getlist('salas_selecionadas')
        
        if not escola_nome or not turma or not nivel_ensino or not quantidade_alunos:
            flash('Preencha todos os campos obrigatórios!', 'danger')
        elif quantidade_alunos <= 0:
            flash('A quantidade de alunos deve ser maior que zero!', 'danger')
        elif quantidade_alunos > horario.vagas_disponiveis:
            flash(f'Não há vagas suficientes! Disponíveis: {horario.vagas_disponiveis}', 'danger')
        else:
            # Criar o agendamento
            agendamento = AgendamentoVisita(
                horario_id=horario.id,
                professor_id=current_user.id,
                cliente_id=current_user.cliente_id,
                escola_nome=escola_nome,
                escola_codigo_inep=escola_codigo_inep,
                turma=turma,
                nivel_ensino=nivel_ensino,
                quantidade_alunos=quantidade_alunos,
                salas_selecionadas=','.join(salas_selecionadas) if salas_selecionadas else None
            )
            
            # Atualizar vagas disponíveis
            horario.vagas_disponiveis -= quantidade_alunos
            
            db.session.add(agendamento)
            
            try:
                db.session.commit()
                flash('Agendamento realizado com sucesso!', 'success')
                
                # Redirecionar para a página de adicionar alunos
                return redirect(url_for('routes.adicionar_alunos_agendamento', agendamento_id=agendamento.id))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao realizar agendamento: {str(e)}', 'danger')
    
    return render_template(
        'professor/criar_agendamento.html',
        horario=horario,
        evento=evento,
        salas=salas
    )


@routes.route('/professor/adicionar_alunos/<int:agendamento_id>', methods=['GET', 'POST'])
@routes.route(
    '/participante/adicionar_alunos/<int:agendamento_id>', methods=['GET', 'POST']
)
@login_required
def adicionar_alunos_agendamento(agendamento_id):
    """Permite adicionar alunos a um agendamento."""
    # Professores, clientes e participantes podem acessar
    tipos_permitidos = {'professor', 'cliente', 'participante'}
    if current_user.tipo not in tipos_permitidos:
        msg = 'Acesso negado! Esta área é exclusiva para professores, clientes e participantes.'
        flash(msg, 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))

    agendamento = AgendamentoVisita.query.get_or_404(agendamento_id)

    # Verificar se o agendamento pertence ao usuário
    if current_user.tipo == 'professor':
        pertence = agendamento.professor_id == current_user.id
        redirect_dest = url_for('agendamento_routes.meus_agendamentos')
    elif current_user.tipo == 'participante':
        pertence = agendamento.professor_id == current_user.id
        redirect_dest = url_for('agendamento_routes.meus_agendamentos_participante')
    else:  # cliente
        pertence = agendamento.cliente_id == current_user.id
        redirect_dest = url_for('agendamento_routes.meus_agendamentos_cliente')

    if not pertence:
        flash('Acesso negado! Este agendamento não pertence a você.', 'danger')
        return redirect(redirect_dest)
    
    # Lista de alunos já adicionados
    alunos = AlunoVisitante.query.filter_by(agendamento_id=agendamento.id).all()
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        cpf = request.form.get('cpf')
        
        if nome:
            # Validar CPF se fornecido
            if cpf and len(cpf.replace('.', '').replace('-', '')) != 11:
                flash('CPF inválido. Digite apenas os números ou deixe em branco.', 'danger')
            else:
                aluno = AlunoVisitante(
                    agendamento_id=agendamento.id,
                    nome=nome,
                    cpf=cpf
                )
                db.session.add(aluno)

                try:
                    db.session.commit()
                    flash('Aluno adicionado com sucesso!', 'success')
                    total = AlunoVisitante.query.filter_by(agendamento_id=agendamento.id).count()
                    if total >= agendamento.quantidade_alunos:
                        return redirect(url_for('routes.confirmacao_agendamento_professor', agendamento_id=agendamento.id))
                    # Recarregar a página para mostrar o aluno adicionado
                    return redirect(url_for('routes.adicionar_alunos_agendamento', agendamento_id=agendamento.id))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erro ao adicionar aluno: {str(e)}', 'danger')
        else:
            flash('Nome do aluno é obrigatório!', 'danger')
    
    return render_template(
        'professor/adicionar_alunos.html',
        agendamento=agendamento,
        alunos=alunos,
        total_adicionados=len(alunos),
        quantidade_esperada=agendamento.quantidade_alunos
    )


@routes.route('/professor/remover_aluno/<int:aluno_id>', methods=['POST'])
@routes.route('/participante/remover_aluno/<int:aluno_id>', methods=['POST'])
@login_required
def remover_aluno_agendamento(aluno_id):
    """Remove um aluno de um agendamento."""
    # Professores e participantes podem acessar
    if current_user.tipo not in ('professor', 'participante'):
        msg = 'Acesso negado! Esta área é exclusiva para professores e participantes.'
        flash(msg, 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))

    aluno = AlunoVisitante.query.get_or_404(aluno_id)
    agendamento = aluno.agendamento

    # Verificar se o agendamento pertence ao usuário
    pertence = agendamento.professor_id == current_user.id
    if current_user.tipo == 'professor':
        redirect_dest = url_for('agendamento_routes.meus_agendamentos')
    else:
        redirect_dest = url_for('agendamento_routes.meus_agendamentos_participante')
    if not pertence:
        flash('Acesso negado! Este aluno não pertence a um agendamento seu.', 'danger')
        return redirect(redirect_dest)
    
    try:
        db.session.delete(aluno)
        db.session.commit()
        flash('Aluno removido com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao remover aluno: {str(e)}', 'danger')
    
    return redirect(url_for('routes.adicionar_alunos_agendamento', agendamento_id=agendamento.id))


@routes.route('/professor/importar_alunos/<int:agendamento_id>', methods=['GET', 'POST'])
@login_required
def importar_alunos_agendamento(agendamento_id):
    # Apenas participantes (professores) podem acessar
    if current_user.tipo != 'professor':
        flash('Acesso negado! Esta área é exclusiva para professores.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    agendamento = AgendamentoVisita.query.get_or_404(agendamento_id)
    
    # Verificar se o agendamento pertence ao professor
    if agendamento.professor_id != current_user.id:
        flash('Acesso negado! Este agendamento não pertence a você.', 'danger')
        return redirect(url_for('agendamento_routes.meus_agendamentos'))
    
    if request.method == 'POST':
        # Verificar se foi enviado um arquivo
        if 'arquivo_csv' not in request.files:
            flash('Nenhum arquivo selecionado!', 'danger')
            return redirect(request.url)
        
        arquivo = request.files['arquivo_csv']
        
        # Verificar se o arquivo tem nome
        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado!', 'danger')
            return redirect(request.url)
        
        # Verificar se o arquivo é CSV
        if arquivo and arquivo.filename.endswith('.csv'):
            try:
                # Ler o conteúdo do arquivo
                conteudo = arquivo.read().decode('utf-8')
                linhas = conteudo.splitlines()
                
                # Contar alunos adicionados
                alunos_adicionados = 0
                
                # Processar cada linha do CSV
                for linha in linhas:
                    if ',' in linha:
                        # Formato esperado: Nome,CPF (opcional)
                        partes = linha.split(',')
                        nome = partes[0].strip()
                        cpf = partes[1].strip() if len(partes) > 1 else None
                        
                        if nome:
                            aluno = AlunoVisitante(
                                agendamento_id=agendamento.id,
                                nome=nome,
                                cpf=cpf
                            )
                            db.session.add(aluno)
                            alunos_adicionados += 1
                
                if alunos_adicionados > 0:
                    db.session.commit()
                    flash(f'{alunos_adicionados} alunos importados com sucesso!', 'success')
                    total = AlunoVisitante.query.filter_by(agendamento_id=agendamento.id).count()
                    if total >= agendamento.quantidade_alunos:
                        return redirect(url_for('routes.confirmacao_agendamento_professor', agendamento_id=agendamento.id))
                else:
                    flash('Nenhum aluno encontrado no arquivo!', 'warning')

                return redirect(url_for('routes.adicionar_alunos_agendamento', agendamento_id=agendamento.id))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao processar arquivo: {str(e)}', 'danger')
        else:
            flash('Arquivo deve estar no formato CSV!', 'danger')
    
    return render_template(
        'professor/importar_alunos.html',
        agendamento=agendamento
    )


@routes.route('/professor/confirmacao_agendamento/<int:agendamento_id>')
@login_required
def confirmacao_agendamento_professor(agendamento_id):
    if current_user.tipo != 'professor':
        flash('Acesso negado! Esta área é exclusiva para professores.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))

    agendamento = AgendamentoVisita.query.get_or_404(agendamento_id)

    if agendamento.professor_id != current_user.id:
        flash('Acesso negado! Este agendamento não pertence a você.', 'danger')
        return redirect(url_for('agendamento_routes.meus_agendamentos'))

    alunos = AlunoVisitante.query.filter_by(agendamento_id=agendamento.id).all()
    if not alunos:
        flash('Nenhum aluno cadastrado neste agendamento.', 'warning')
        return redirect(url_for('routes.adicionar_alunos_agendamento', agendamento_id=agendamento.id))

    return render_template(
        'professor/confirmacao_agendamento.html',
        agendamento=agendamento,
        alunos=alunos
    )

@routes.route('/professor/imprimir_agendamento/<int:agendamento_id>')
@login_required
def imprimir_agendamento_professor(agendamento_id):
    """Gera o comprovante de um agendamento."""

    # Permitir acesso a professores, participantes, clientes e usuários
    tipos_permitidos = {'professor', 'participante', 'cliente', 'usuario'}
    if current_user.tipo not in tipos_permitidos:
        flash(
            'Acesso negado! Esta área é exclusiva para professores, '
            'participantes, clientes e usuários.',
            'danger',
        )
        return redirect(url_for('dashboard_routes.dashboard'))

    agendamento = AgendamentoVisita.query.get_or_404(agendamento_id)

    # Validar propriedade conforme o tipo do usuário
    if current_user.tipo == 'professor' and agendamento.professor_id != current_user.id:
        flash('Acesso negado! Este agendamento não pertence a você.', 'danger')
        return redirect(url_for('agendamento_routes.meus_agendamentos'))
    if (
        current_user.tipo == 'cliente'
        and agendamento.horario.evento.cliente_id != current_user.id
    ):
        flash(
            'Acesso negado! Este agendamento não pertence ao seu evento.',
            'danger',
        )
        return redirect(url_for('agendamento_routes.meus_agendamentos'))

    if agendamento.status != 'confirmado':
        flash('Agendamento ainda não confirmado.', 'warning')
        return redirect(url_for('agendamento_routes.meus_agendamentos'))

    horario = agendamento.horario
    evento = horario.evento
    
    # Buscar salas selecionadas para visitação
    salas_ids = agendamento.salas_selecionadas.split(',') if agendamento.salas_selecionadas else []
    salas = SalaVisitacao.query.filter(SalaVisitacao.id.in_(salas_ids)).all() if salas_ids else []

    # Buscar alunos participantes
    alunos = AlunoVisitante.query.filter_by(agendamento_id=agendamento.id).all()

    if not alunos:
        flash('Adicione alunos antes de imprimir o comprovante.', 'warning')
        return redirect(url_for('routes.adicionar_alunos_agendamento', agendamento_id=agendamento.id))

    # Gerar PDF para impressão
    pdf_filename = f"agendamento_{agendamento_id}.pdf"
    pdf_path = os.path.join("static", "agendamentos", pdf_filename)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    
    # Chamar função para gerar PDF
    gerar_pdf_comprovante_agendamento(agendamento, horario, evento, salas, alunos, pdf_path)
    
    return send_file(pdf_path, as_attachment=True)


@routes.route('/professor/qrcode_agendamento/<int:agendamento_id>')
@login_required
def qrcode_agendamento_professor(agendamento_id):
    """Exibe o QR Code de um agendamento."""

    # Permitir acesso a professores, participantes, clientes e usuários
    tipos_permitidos = {'professor', 'participante', 'cliente', 'usuario'}
    if current_user.tipo not in tipos_permitidos:
        flash(
            'Acesso negado! Esta área é exclusiva para professores, '
            'participantes, clientes e usuários.',
            'danger',
        )
        return redirect(url_for('dashboard_routes.dashboard'))

    agendamento = AgendamentoVisita.query.get_or_404(agendamento_id)

    # Validar propriedade conforme o tipo do usuário
    if current_user.tipo == 'professor' and agendamento.professor_id != current_user.id:
        flash('Acesso negado! Este agendamento não pertence a você.', 'danger')
        return redirect(url_for('agendamento_routes.meus_agendamentos'))
    if (
        current_user.tipo == 'cliente'
        and agendamento.horario.evento.cliente_id != current_user.id
    ):
        flash(
            'Acesso negado! Este agendamento não pertence ao seu evento.',
            'danger',
        )
        return redirect(url_for('agendamento_routes.meus_agendamentos'))

    if agendamento.status != 'confirmado':
        flash('Agendamento ainda não confirmado.', 'warning')
        return redirect(url_for('agendamento_routes.meus_agendamentos'))

    # Página que exibe o QR Code para check-in
    return render_template(
        'professor/qrcode_agendamento.html',
        agendamento=agendamento,
        token=agendamento.qr_code_token
    )


@routes.route('/participante/horarios_disponiveis/<int:evento_id>')
@login_required
def horarios_disponiveis_participante(evento_id):
    """Lista horários disponíveis para participantes."""
    if current_user.tipo != 'participante':
        flash('Acesso negado! Esta área é exclusiva para participantes.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))

    evento = Evento.query.get_or_404(evento_id)

    # Verificar se o participante está inscrito no evento (diretamente ou por oficina)
    inscrito = Inscricao.query.filter_by(usuario_id=current_user.id, evento_id=evento_id).first()
    if not inscrito:
        inscrito = Inscricao.query.join(Oficina).filter(
            Inscricao.usuario_id == current_user.id,
            Oficina.evento_id == evento_id
        ).first()

    if not inscrito:
        flash('Você não está inscrito neste evento.', 'warning')
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

    data_filtro = request.args.get('data')

    query = HorarioVisitacao.query.filter_by(evento_id=evento_id).filter(
        HorarioVisitacao.vagas_disponiveis > 0,
        HorarioVisitacao.data >= datetime.now().date() + timedelta(days=1)
    )

    if data_filtro:
        data_filtrada = datetime.strptime(data_filtro, '%Y-%m-%d').date()
        query = query.filter(HorarioVisitacao.data == data_filtrada)

    horarios = query.order_by(HorarioVisitacao.data, HorarioVisitacao.horario_inicio).all()

    horarios_por_data = {}
    for h in horarios:
        data_str = h.data.strftime('%Y-%m-%d')
        horarios_por_data.setdefault(data_str, []).append(h)

    return render_template(
        'participante/horarios_disponiveis.html',
        evento=evento,
        horarios_por_data=horarios_por_data,
        data_filtro=data_filtro
    )


@routes.route('/participante/criar_agendamento/<int:horario_id>', methods=['GET', 'POST'])
@login_required
def criar_agendamento_participante(horario_id):
    """Permite que o participante faça um agendamento de visita em grupo."""
    if current_user.tipo != 'participante':
        flash('Acesso negado! Esta área é exclusiva para participantes.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))

    horario = HorarioVisitacao.query.get_or_404(horario_id)
    evento = horario.evento

    # Verificar se o usuário está inscrito no evento (diretamente ou por oficina)
    inscrito = Inscricao.query.filter_by(usuario_id=current_user.id, evento_id=evento.id).first()
    if not inscrito:
        inscrito = Inscricao.query.join(Oficina).filter(
            Inscricao.usuario_id == current_user.id,
            Oficina.evento_id == evento.id
        ).first()

    if not inscrito:
        flash('Você não está inscrito neste evento.', 'warning')
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

    # Verificar vagas disponíveis
    if horario.vagas_disponiveis <= 0:
        flash('Não há mais vagas disponíveis para este horário!', 'warning')
        return redirect(url_for('routes.horarios_disponiveis_participante', evento_id=evento.id))

    # Salas disponíveis para seleção
    salas = SalaVisitacao.query.filter_by(evento_id=evento.id).all()

    if request.method == 'POST':
        # Obter dados do formulário
        escola_nome = request.form.get('escola_nome')
        escola_codigo_inep = request.form.get('escola_codigo_inep')
        turma = request.form.get('turma')
        nivel_ensino = request.form.get('nivel_ensino')
        quantidade_alunos = request.form.get('quantidade_alunos', type=int)
        salas_selecionadas = request.form.getlist('salas_selecionadas')

        # Validações básicas
        if not escola_nome or not turma or not nivel_ensino or not quantidade_alunos:
            flash('Preencha todos os campos obrigatórios!', 'danger')
        elif quantidade_alunos <= 0:
            flash('A quantidade de alunos deve ser maior que zero!', 'danger')
        elif quantidade_alunos > horario.vagas_disponiveis:
            flash(f'Não há vagas suficientes! Disponíveis: {horario.vagas_disponiveis}', 'danger')
        else:
            agendamento = AgendamentoVisita(
                horario_id=horario.id,
                professor_id=current_user.id,
                cliente_id=current_user.cliente_id,
                escola_nome=escola_nome,
                escola_codigo_inep=escola_codigo_inep,
                turma=turma,
                nivel_ensino=nivel_ensino,
                quantidade_alunos=quantidade_alunos,
                salas_selecionadas=','.join(salas_selecionadas) if salas_selecionadas else None
            )

            horario.vagas_disponiveis -= quantidade_alunos
            db.session.add(agendamento)
            try:
                db.session.commit()
                flash('Agendamento realizado com sucesso!', 'success')
                return redirect(url_for('agendamento_routes.meus_agendamentos_participante'))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao realizar agendamento: {str(e)}', 'danger')

    return render_template(
        'participante/criar_agendamento.html',
        horario=horario,
        evento=evento,
        salas=salas
    )
    
