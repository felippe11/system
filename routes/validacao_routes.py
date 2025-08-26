from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from models.certificado import CertificadoParticipante, AcessoValidacaoCertificado
from services.validacao_certificado_service import (
    validar_certificado_por_codigo,
    verificar_integridade_certificado,
    registrar_acesso_validacao,
    gerar_relatorio_validacoes,
    verificar_integridade_certificados_cliente,
    buscar_certificados_por_participante
)
from extensions import db
from datetime import datetime, timedelta
from flask_login import login_required, current_user
from decorators import cliente_required

validacao_bp = Blueprint('validacao', __name__, url_prefix='/validacao')

@validacao_bp.route('/certificado/<codigo>')
def validar_certificado(codigo):
    """Página pública para validação de certificados."""
    try:
        resultado = validar_certificado_por_codigo(codigo)
        
        if resultado['valido']:
            certificado = resultado['certificado']
            
            # Registrar acesso
            ip_acesso = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
            user_agent = request.headers.get('User-Agent')
            
            registrar_acesso_validacao(
                certificado_id=certificado.id,
                ip_acesso=ip_acesso,
                user_agent=user_agent
            )
            
            return render_template('validacao/certificado_valido.html', 
                                 certificado=certificado,
                                 resultado=resultado)
        else:
            return render_template('validacao/certificado_invalido.html', 
                                 erro=resultado['erro'])
                                 
    except Exception as e:
        return render_template('validacao/certificado_invalido.html', 
                             erro='Erro interno do sistema')

@validacao_bp.route('/api/certificado/<codigo>')
def api_validar_certificado(codigo):
    """API para validação de certificados."""
    try:
        resultado = validar_certificado_por_codigo(codigo)
        
        if resultado['valido']:
            certificado = resultado['certificado']
            
            # Registrar acesso
            ip_acesso = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
            user_agent = request.headers.get('User-Agent')
            
            registrar_acesso_validacao(
                certificado_id=certificado.id,
                ip_acesso=ip_acesso,
                user_agent=user_agent
            )
            
            return jsonify({
                'valido': True,
                'participante': certificado.participante.nome,
                'evento': certificado.evento.nome,
                'data_emissao': certificado.data_emissao.strftime('%d/%m/%Y'),
                'carga_horaria': certificado.carga_horaria_total,
                'hash_verificacao': certificado.hash_verificacao
            })
        else:
            return jsonify({
                'valido': False,
                'erro': resultado['erro']
            })
            
    except Exception as e:
        return jsonify({
            'valido': False,
            'erro': 'Erro interno do sistema'
        }), 500

@validacao_bp.route('/buscar')
def buscar_certificados():
    """Página para buscar certificados por CPF ou email."""
    return render_template('validacao/buscar_certificados.html')

@validacao_bp.route('/api/buscar')
def api_buscar_certificados():
    """API para buscar certificados por CPF ou email."""
    cpf = request.args.get('cpf')
    email = request.args.get('email')
    
    if not cpf and not email:
        return jsonify({
            'erro': 'CPF ou email deve ser informado'
        }), 400
    
    try:
        certificados = buscar_certificados_por_participante(cpf=cpf, email=email)
        
        resultado = []
        for cert in certificados:
            resultado.append({
                'codigo_verificacao': cert.codigo_verificacao,
                'evento': cert.evento.nome,
                'data_emissao': cert.data_emissao.strftime('%d/%m/%Y'),
                'carga_horaria': cert.carga_horaria_total,
                'url_validacao': url_for('validacao.validar_certificado', 
                                        codigo=cert.codigo_verificacao, _external=True)
            })
        
        return jsonify({
            'certificados': resultado,
            'total': len(resultado)
        })
        
    except Exception as e:
        return jsonify({
            'erro': 'Erro interno do sistema'
        }), 500

@validacao_bp.route('/admin/relatorio')
@login_required
@cliente_required
def relatorio_validacoes():
    """Relatório de validações para administradores."""
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    # Definir período padrão (últimos 30 dias)
    if not data_inicio:
        data_inicio = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not data_fim:
        data_fim = datetime.now().strftime('%Y-%m-%d')
    
    try:
        relatorio = gerar_relatorio_validacoes(
            cliente_id=current_user.id,
            data_inicio=datetime.strptime(data_inicio, '%Y-%m-%d'),
            data_fim=datetime.strptime(data_fim, '%Y-%m-%d')
        )
        
        return render_template('validacao/relatorio_validacoes.html',
                             relatorio=relatorio,
                             data_inicio=data_inicio,
                             data_fim=data_fim)
                             
    except Exception as e:
        flash('Erro ao gerar relatório de validações', 'error')
        return redirect(url_for('dashboard.dashboard_cliente'))

@validacao_bp.route('/admin/integridade')
@login_required
@cliente_required
def verificar_integridade():
    """Verificar integridade dos certificados do cliente."""
    try:
        resultado = verificar_integridade_certificados_cliente(current_user.id)
        
        return render_template('validacao/integridade_certificados.html',
                             resultado=resultado)
                             
    except Exception as e:
        flash('Erro ao verificar integridade dos certificados', 'error')
        return redirect(url_for('dashboard.dashboard_cliente'))

@validacao_bp.route('/admin/api/integridade')
@login_required
@cliente_required
def api_verificar_integridade():
    """API para verificar integridade dos certificados."""
    try:
        resultado = verificar_integridade_certificados_cliente(current_user.id)
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({
            'erro': 'Erro interno do sistema'
        }), 500