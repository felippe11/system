# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import and_

from extensions import db
from models.user import Ministrante, Cliente, Monitor
from models.formador import (
    TrilhaFormativa, CampoTrilhaFormativa, RespostaTrilhaFormativa,
    SolicitacaoMaterial, MaterialAprovado, ConfiguracaoRelatorioFormador,
    RelatorioFormador, ArquivoFormador, FormadorMonitor
)
from models import Oficina
from utils.auth import ministrante_required
from utils import endpoints

formador_routes = Blueprint('formador_routes', __name__)


@formador_routes.route('/dashboard_formador')
@login_required
@ministrante_required
def dashboard_formador():
    """Dashboard principal do formador"""
    formador = current_user
    
    # Buscar oficinas/atividades do formador
    oficinas = Oficina.query.filter_by(ministrante_id=formador.id).all()
    
    # Buscar solicitações de material pendentes
    solicitacoes_pendentes = SolicitacaoMaterial.query.filter_by(
        formador_id=formador.id,
        status='pendente'
    ).count()
    
    # Buscar trilhas formativas disponíveis
    trilhas_disponiveis = TrilhaFormativa.query.filter_by(
        cliente_id=formador.cliente_id,
        ativo=True
    ).all()
    
    # Buscar relatórios pendentes
    configuracoes_relatorio = ConfiguracaoRelatorioFormador.query.filter_by(
        cliente_id=formador.cliente_id,
        ativo=True
    ).all()
    
    return render_template(
        'formador/dashboard.html',
        formador=formador,
        oficinas=oficinas,
        solicitacoes_pendentes=solicitacoes_pendentes,
        trilhas_disponiveis=trilhas_disponiveis,
        configuracoes_relatorio=configuracoes_relatorio
    )


@formador_routes.route('/solicitar_material', methods=['GET', 'POST'])
@login_required
@ministrante_required
def solicitar_material():
    """Página para solicitação de materiais"""
    if request.method == 'POST':
        tipo_solicitacao = request.form.get('tipo_solicitacao')
        atividade_id = request.form.get('atividade_id') if tipo_solicitacao == 'atividade' else None
        tipo_material = request.form.get('tipo_material')
        unidade_medida = request.form.get('unidade_medida')
        quantidade = int(request.form.get('quantidade'))
        justificativa = request.form.get('justificativa')
        
        solicitacao = SolicitacaoMaterial(
            formador_id=current_user.id,
            cliente_id=current_user.cliente_id,
            atividade_id=atividade_id,
            tipo_solicitacao=tipo_solicitacao,
            tipo_material=tipo_material,
            unidade_medida=unidade_medida,
            quantidade=quantidade,
            justificativa=justificativa
        )
        
        db.session.add(solicitacao)
        db.session.commit()
        
        flash('Solicitação de material enviada com sucesso!', 'success')
        return redirect(url_for('formador_routes.minhas_solicitacoes'))
    
    # Buscar atividades do formador para o select
    oficinas = Oficina.query.filter_by(ministrante_id=current_user.id).all()
    
    return render_template('formador/solicitar_material.html', oficinas=oficinas)


@formador_routes.route('/minhas_solicitacoes')
@login_required
@ministrante_required
def minhas_solicitacoes():
    """Lista de solicitações de material do formador"""
    solicitacoes = SolicitacaoMaterial.query.filter_by(
        formador_id=current_user.id
    ).order_by(SolicitacaoMaterial.data_solicitacao.desc()).all()
    
    return render_template('formador/minhas_solicitacoes.html', solicitacoes=solicitacoes)


@formador_routes.route('/trilha_formativa/<int:trilha_id>', methods=['GET', 'POST'])
@login_required
@ministrante_required
def responder_trilha_formativa(trilha_id):
    """Responder trilha formativa"""
    trilha = TrilhaFormativa.query.get_or_404(trilha_id)
    
    # Verificar se o formador já respondeu esta trilha
    resposta_existente = RespostaTrilhaFormativa.query.filter_by(
        trilha_id=trilha_id,
        formador_id=current_user.id
    ).first()
    
    if request.method == 'POST':
        respostas = {}
        for campo in trilha.campos:
            valor = request.form.get(f'campo_{campo.id}')
            if campo.tipo == 'checkbox':
                valor = request.form.getlist(f'campo_{campo.id}')
            respostas[str(campo.id)] = valor
        
        if resposta_existente:
            resposta_existente.respostas = respostas
            resposta_existente.data_envio = datetime.utcnow()
        else:
            nova_resposta = RespostaTrilhaFormativa(
                trilha_id=trilha_id,
                formador_id=current_user.id,
                respostas=respostas
            )
            db.session.add(nova_resposta)
        
        db.session.commit()
        flash('Trilha formativa enviada com sucesso!', 'success')
        return redirect(url_for('formador_routes.dashboard_formador'))
    
    return render_template(
        'formador/trilha_formativa.html',
        trilha=trilha,
        resposta_existente=resposta_existente
    )


@formador_routes.route('/relatorio/<int:config_id>', methods=['GET', 'POST'])
@login_required
@ministrante_required
def enviar_relatorio(config_id):
    """Enviar relatório do formador"""
    configuracao = ConfiguracaoRelatorioFormador.query.get_or_404(config_id)
    
    if request.method == 'POST':
        dados_relatorio = {}
        for campo in configuracao.campos_relatorio:
            valor = request.form.get(f'campo_{campo["id"]}')
            dados_relatorio[campo['id']] = valor
        
        atividade_id = request.form.get('atividade_id') if configuracao.tipo_periodo == 'atividade' else None
        periodo_inicio = request.form.get('periodo_inicio')
        periodo_fim = request.form.get('periodo_fim')
        
        relatorio = RelatorioFormador(
            configuracao_id=config_id,
            formador_id=current_user.id,
            atividade_id=atividade_id,
            periodo_inicio=datetime.strptime(periodo_inicio, '%Y-%m-%d').date() if periodo_inicio else None,
            periodo_fim=datetime.strptime(periodo_fim, '%Y-%m-%d').date() if periodo_fim else None,
            dados_relatorio=dados_relatorio
        )
        
        db.session.add(relatorio)
        db.session.commit()
        
        flash('Relatório enviado com sucesso!', 'success')
        return redirect(url_for('formador_routes.dashboard_formador'))
    
    # Buscar atividades se for relatório por atividade
    oficinas = None
    if configuracao.tipo_periodo == 'atividade':
        oficinas = Oficina.query.filter_by(ministrante_id=current_user.id).all()
    
    return render_template(
        'formador/relatorio.html',
        configuracao=configuracao,
        oficinas=oficinas
    )


@formador_routes.route('/upload_arquivo', methods=['GET', 'POST'])
@login_required
@ministrante_required
def upload_arquivo():
    """Upload de arquivos pelo formador"""
    if request.method == 'POST':
        if 'arquivo' not in request.files:
            flash('Nenhum arquivo selecionado!', 'error')
            return redirect(request.url)
        
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado!', 'error')
            return redirect(request.url)
        
        nome_arquivo = request.form.get('nome_arquivo')
        frequencia_reenvio = request.form.get('frequencia_reenvio')
        
        if arquivo:
            filename = secure_filename(arquivo.filename)
            # Criar diretório se não existir
            upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'static/uploads'), 'formadores')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Salvar arquivo
            filepath = os.path.join(upload_dir, filename)
            arquivo.save(filepath)
            
            # Calcular próximo reenvio
            proximo_reenvio = None
            if frequencia_reenvio:
                if frequencia_reenvio == 'semanal':
                    proximo_reenvio = datetime.utcnow() + timedelta(weeks=1)
                elif frequencia_reenvio == 'mensal':
                    proximo_reenvio = datetime.utcnow() + timedelta(days=30)
                elif frequencia_reenvio == 'trimestral':
                    proximo_reenvio = datetime.utcnow() + timedelta(days=90)
            
            # Salvar no banco
            arquivo_formador = ArquivoFormador(
                cliente_id=current_user.cliente_id,
                formador_id=current_user.id,
                nome_arquivo=nome_arquivo or filename,
                nome_original=filename,
                caminho_arquivo=filepath,
                frequencia_reenvio=frequencia_reenvio,
                proximo_reenvio=proximo_reenvio
            )
            
            db.session.add(arquivo_formador)
            db.session.commit()
            
            flash('Arquivo enviado com sucesso!', 'success')
            return redirect(url_for('formador_routes.meus_arquivos'))
    
    return render_template('formador/upload_arquivo.html')


@formador_routes.route('/meus_arquivos')
@login_required
@ministrante_required
def meus_arquivos():
    """Lista de arquivos enviados pelo formador"""
    arquivos = ArquivoFormador.query.filter_by(
        formador_id=current_user.id
    ).order_by(ArquivoFormador.data_upload.desc()).all()
    
    return render_template('formador/meus_arquivos.html', arquivos=arquivos)


@formador_routes.route('/feedbacks')
@login_required
@ministrante_required
def ver_feedbacks():
    """Ver feedbacks das atividades do formador"""
    # Buscar oficinas do formador
    oficinas = Oficina.query.filter_by(ministrante_id=current_user.id).all()
    
    # Aqui você pode implementar a lógica para buscar feedbacks
    # dependendo de como está estruturado no seu sistema
    
    return render_template('formador/feedbacks.html', oficinas=oficinas)


# Rotas para o cliente gerenciar formadores
@formador_routes.route('/gerenciar_formadores')
@login_required
def gerenciar_formadores():
    """Tela de gerenciamento de formadores para o cliente"""
    if current_user.tipo != 'cliente':
        flash('Acesso negado!', 'danger')
        return redirect(url_for(endpoints.DASHBOARD))
    
    formadores = Ministrante.query.filter_by(cliente_id=current_user.id).all()
    monitores = Monitor.query.filter_by(cliente_id=current_user.id).all()
    
    return render_template(
        'cliente/gerenciar_formadores.html',
        formadores=formadores,
        monitores=monitores
    )


@formador_routes.route('/aprovar_solicitacao/<int:solicitacao_id>', methods=['POST'])
@login_required
def aprovar_solicitacao(solicitacao_id):
    """Aprovar solicitação de material"""
    if current_user.tipo != 'cliente':
        return jsonify({'error': 'Acesso negado'}), 403
    
    solicitacao = SolicitacaoMaterial.query.get_or_404(solicitacao_id)
    
    if solicitacao.cliente_id != current_user.id:
        return jsonify({'error': 'Acesso negado'}), 403
    
    acao = request.form.get('acao')  # aprovar, rejeitar, parcial
    quantidade_aprovada = request.form.get('quantidade_aprovada')
    observacoes = request.form.get('observacoes')
    monitor_id = request.form.get('monitor_id')
    
    solicitacao.status = acao
    solicitacao.observacoes_cliente = observacoes
    solicitacao.data_resposta = datetime.utcnow()
    
    if acao in ['aprovar', 'parcial']:
        solicitacao.quantidade_aprovada = int(quantidade_aprovada or solicitacao.quantidade)
        
        # Criar material aprovado para entrega
        material_aprovado = MaterialAprovado(
            solicitacao_id=solicitacao_id,
            monitor_id=int(monitor_id) if monitor_id else None,
            quantidade_para_entrega=solicitacao.quantidade_aprovada
        )
        db.session.add(material_aprovado)
    
    db.session.commit()
    
    flash('Solicitação processada com sucesso!', 'success')
    return redirect(url_for('formador_routes.gerenciar_formadores'))


@formador_routes.route('/associar_monitor', methods=['POST'])
@login_required
def associar_monitor():
    """Associar formador a monitor"""
    if current_user.tipo != 'cliente':
        return jsonify({'error': 'Acesso negado'}), 403
    
    formador_id = request.form.get('formador_id')
    monitor_id = request.form.get('monitor_id')
    
    # Verificar se já existe associação
    associacao_existente = FormadorMonitor.query.filter_by(
        formador_id=formador_id,
        monitor_id=monitor_id,
        ativo=True
    ).first()
    
    if associacao_existente:
        flash('Formador já está associado a este monitor!', 'warning')
    else:
        associacao = FormadorMonitor(
            formador_id=formador_id,
            monitor_id=monitor_id,
            cliente_id=current_user.id
        )
        db.session.add(associacao)
        db.session.commit()
        flash('Formador associado ao monitor com sucesso!', 'success')
    
    return redirect(url_for('formador_routes.gerenciar_formadores'))