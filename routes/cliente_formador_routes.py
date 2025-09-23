# -*- coding: utf-8 -*-
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from extensions import db
from models.user import Ministrante, Cliente
from models.formador import (
    TrilhaFormativa, CampoTrilhaFormativa, ConfiguracaoRelatorioFormador,
    RespostaTrilhaFormativa, ArquivoFormador
)
from models.relatorio_config import RelatorioFormador
from utils.auth import cliente_required
from utils import endpoints

cliente_formador_routes = Blueprint('cliente_formador_routes', __name__)


# Gestão de Trilhas Formativas
@cliente_formador_routes.route('/trilhas_formativas')
@login_required
@cliente_required
def listar_trilhas_formativas():
    """Lista trilhas formativas do cliente"""
    trilhas = TrilhaFormativa.query.filter_by(cliente_id=current_user.id).all()
    return render_template('cliente/trilhas_formativas.html', trilhas=trilhas)


@cliente_formador_routes.route('/trilha_formativa/nova', methods=['GET', 'POST'])
@login_required
@cliente_required
def nova_trilha_formativa():
    """Criar nova trilha formativa"""
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        
        trilha = TrilhaFormativa(
            nome=nome,
            descricao=descricao,
            cliente_id=current_user.id
        )
        
        db.session.add(trilha)
        db.session.flush()  # Para obter o ID
        
        # Adicionar campos
        campos_nomes = request.form.getlist('campo_nome[]')
        campos_tipos = request.form.getlist('campo_tipo[]')
        campos_obrigatorios = request.form.getlist('campo_obrigatorio[]')
        campos_opcoes = request.form.getlist('campo_opcoes[]')
        
        for i, nome_campo in enumerate(campos_nomes):
            if nome_campo.strip():
                campo = CampoTrilhaFormativa(
                    trilha_id=trilha.id,
                    nome=nome_campo,
                    tipo=campos_tipos[i],
                    obrigatorio=str(i) in campos_obrigatorios,
                    opcoes=campos_opcoes[i] if i < len(campos_opcoes) else None,
                    ordem=i
                )
                db.session.add(campo)
        
        db.session.commit()
        flash('Trilha formativa criada com sucesso!', 'success')
        return redirect(url_for('cliente_formador_routes.listar_trilhas_formativas'))
    
    return render_template('cliente/nova_trilha_formativa.html')


@cliente_formador_routes.route('/trilha_formativa/<int:trilha_id>/editar', methods=['GET', 'POST'])
@login_required
@cliente_required
def editar_trilha_formativa(trilha_id):
    """Editar trilha formativa"""
    trilha = TrilhaFormativa.query.get_or_404(trilha_id)
    
    if trilha.cliente_id != current_user.id:
        flash('Acesso negado!', 'danger')
        return redirect(url_for('cliente_formador_routes.listar_trilhas_formativas'))
    
    if request.method == 'POST':
        trilha.nome = request.form.get('nome')
        trilha.descricao = request.form.get('descricao')
        
        # Remover campos existentes
        CampoTrilhaFormativa.query.filter_by(trilha_id=trilha.id).delete()
        
        # Adicionar novos campos
        campos_nomes = request.form.getlist('campo_nome[]')
        campos_tipos = request.form.getlist('campo_tipo[]')
        campos_obrigatorios = request.form.getlist('campo_obrigatorio[]')
        campos_opcoes = request.form.getlist('campo_opcoes[]')
        
        for i, nome_campo in enumerate(campos_nomes):
            if nome_campo.strip():
                campo = CampoTrilhaFormativa(
                    trilha_id=trilha.id,
                    nome=nome_campo,
                    tipo=campos_tipos[i],
                    obrigatorio=str(i) in campos_obrigatorios,
                    opcoes=campos_opcoes[i] if i < len(campos_opcoes) else None,
                    ordem=i
                )
                db.session.add(campo)
        
        db.session.commit()
        flash('Trilha formativa atualizada com sucesso!', 'success')
        return redirect(url_for('cliente_formador_routes.listar_trilhas_formativas'))
    
    return render_template('cliente/editar_trilha_formativa.html', trilha=trilha)


@cliente_formador_routes.route('/trilha_formativa/<int:trilha_id>/respostas')
@login_required
@cliente_required
def ver_respostas_trilha(trilha_id):
    """Ver respostas da trilha formativa"""
    trilha = TrilhaFormativa.query.get_or_404(trilha_id)
    
    if trilha.cliente_id != current_user.id:
        flash('Acesso negado!', 'danger')
        return redirect(url_for('cliente_formador_routes.listar_trilhas_formativas'))
    
    respostas = RespostaTrilhaFormativa.query.filter_by(trilha_id=trilha_id).all()
    
    return render_template(
        'cliente/respostas_trilha_formativa.html',
        trilha=trilha,
        respostas=respostas
    )


# Gestão de Configurações de Relatório
@cliente_formador_routes.route('/configuracoes_relatorio')
@login_required
@cliente_required
def listar_configuracoes_relatorio():
    """Lista configurações de relatório do cliente"""
    configuracoes = ConfiguracaoRelatorioFormador.query.filter_by(
        cliente_id=current_user.id
    ).all()
    return render_template('cliente/configuracoes_relatorio.html', configuracoes=configuracoes)


@cliente_formador_routes.route('/configuracao_relatorio/nova', methods=['GET', 'POST'])
@login_required
@cliente_required
def nova_configuracao_relatorio():
    """Criar nova configuração de relatório"""
    if request.method == 'POST':
        nome = request.form.get('nome')
        tipo_periodo = request.form.get('tipo_periodo')
        
        # Montar campos do relatório
        campos_nomes = request.form.getlist('campo_nome[]')
        campos_tipos = request.form.getlist('campo_tipo[]')
        campos_obrigatorios = request.form.getlist('campo_obrigatorio[]')
        
        campos_relatorio = []
        for i, nome_campo in enumerate(campos_nomes):
            if nome_campo.strip():
                campos_relatorio.append({
                    'id': f'campo_{i}',
                    'nome': nome_campo,
                    'tipo': campos_tipos[i],
                    'obrigatorio': str(i) in campos_obrigatorios
                })
        
        configuracao = ConfiguracaoRelatorioFormador(
            cliente_id=current_user.id,
            nome=nome,
            tipo_periodo=tipo_periodo,
            campos_relatorio=campos_relatorio
        )
        
        db.session.add(configuracao)
        db.session.commit()
        
        flash('Configuração de relatório criada com sucesso!', 'success')
        return redirect(url_for('cliente_formador_routes.listar_configuracoes_relatorio'))
    
    return render_template('cliente/nova_configuracao_relatorio.html')


@cliente_formador_routes.route('/relatorios_formadores')
@login_required
@cliente_required
def ver_relatorios_formadores():
    """Ver relatórios enviados pelos formadores"""
    relatorios = RelatorioFormador.query.join(
        ConfiguracaoRelatorioFormador
    ).filter(
        ConfiguracaoRelatorioFormador.cliente_id == current_user.id
    ).order_by(RelatorioFormador.data_envio.desc()).all()
    
    return render_template('cliente/relatorios_formadores.html', relatorios=relatorios)


# Gestão de Links de Inscrição para Formadores
@cliente_formador_routes.route('/links_inscricao_formador')
@login_required
@cliente_required
def listar_links_inscricao_formador():
    """Lista links de inscrição para formadores"""
    from models.user import FormadorCadastroLink
    
    # Buscar todos os links do cliente atual
    links = FormadorCadastroLink.query.filter_by(cliente_id=current_user.id).order_by(FormadorCadastroLink.created_at.desc()).all()
    
    return render_template('cliente/links_inscricao_formador.html', links=links)


@cliente_formador_routes.route('/gerar_link_inscricao_formador', methods=['GET', 'POST'])
@login_required
@cliente_required
def gerar_link_inscricao_formador():
    """Gerar link de inscrição para formadores"""
    if request.method == 'GET':
        # Redirecionar para a página de links quando acessado via GET
        return redirect(url_for('cliente_formador_routes.listar_links_inscricao_formador'))
    
    from models.user import FormadorCadastroLink
    from datetime import datetime, timedelta
    from extensions import db
    
    # Obter dados do formulário
    descricao = request.form.get('descricao', 'Link de inscrição para formadores')
    validade_dias = int(request.form.get('validade', 30))
    
    # Calcular data de expiração
    expires_at = datetime.utcnow() + timedelta(days=validade_dias)
    
    # Criar novo link no banco de dados
    novo_link = FormadorCadastroLink(
        cliente_id=current_user.id,
        descricao=descricao,
        expires_at=expires_at
    )
    
    try:
        db.session.add(novo_link)
        db.session.commit()
        
        # Gerar URL do link
        base_url = request.host_url.rstrip('/')
        link_url = f"{base_url}/formador/inscricao/{novo_link.token}"
        
        flash(f'Link de inscrição gerado com sucesso: {link_url}', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao gerar link de inscrição. Tente novamente.', 'error')
    
    return redirect(url_for('cliente_formador_routes.listar_links_inscricao_formador'))


# Página de inscrição pública para formadores
@cliente_formador_routes.route('/inscricao_formador/<token>', methods=['GET', 'POST'])
def inscricao_formador(token):
    """Página de inscrição para formadores via link"""
    # Implementar validação do token
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        cpf = request.form.get('cpf')
        telefone = request.form.get('telefone')
        cidade = request.form.get('cidade')
        estado = request.form.get('estado')
        endereco = request.form.get('endereco')
        formacao = request.form.get('formacao')
        areas_atuacao = request.form.get('areas_atuacao')
        
        # Dados bancários
        banco = request.form.get('banco')
        agencia = request.form.get('agencia')
        conta = request.form.get('conta')
        tipo_conta = request.form.get('tipo_conta')
        chave_pix = request.form.get('chave_pix')
        
        # Verificar se email/CPF já existem
        if Ministrante.query.filter_by(email=email).first():
            flash('Email já cadastrado!', 'danger')
            return render_template('formador/inscricao.html')
        
        if Ministrante.query.filter_by(cpf=cpf).first():
            flash('CPF já cadastrado!', 'danger')
            return render_template('formador/inscricao.html')
        
        # Gerar senha temporária
        senha_temporaria = str(uuid.uuid4())[:8]
        
        # Criar formador
        formador = Ministrante(
            nome=nome,
            email=email,
            cpf=cpf,
            telefone=telefone,
            cidade=cidade,
            estado=estado,
            endereco=endereco,
            formacao=formacao,
            areas_atuacao=areas_atuacao,
            banco=banco,
            agencia=agencia,
            conta=conta,
            tipo_conta=tipo_conta,
            chave_pix=chave_pix,
            senha=generate_password_hash(senha_temporaria),
            # cliente_id será definido baseado no token
        )
        
        db.session.add(formador)
        db.session.commit()
        
        flash(f'Cadastro realizado com sucesso! Sua senha temporária é: {senha_temporaria}', 'success')
        return redirect(url_for('auth_routes.login'))
    
    return render_template('formador/inscricao.html')


# Gestão de Arquivos dos Formadores
@cliente_formador_routes.route('/arquivos_formadores')
@login_required
@cliente_required
def listar_arquivos_formadores():
    """Lista arquivos enviados pelos formadores"""
    arquivos = ArquivoFormador.query.filter_by(cliente_id=current_user.id).all()
    return render_template('cliente/arquivos_formadores.html', arquivos=arquivos)


@cliente_formador_routes.route('/configurar_arquivo_formador', methods=['GET', 'POST'])
@login_required
@cliente_required
def configurar_arquivo_formador():
    """Configurar tipos de arquivo que formadores podem enviar"""
    if request.method == 'POST':
        # Implementar configuração de tipos de arquivo permitidos
        flash('Configuração salva com sucesso!', 'success')
        return redirect(url_for('cliente_formador_routes.listar_arquivos_formadores'))
    
    return render_template('cliente/configurar_arquivo_formador.html')