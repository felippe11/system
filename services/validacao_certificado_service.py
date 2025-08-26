from models import Evento
from models.user import Usuario
from models.certificado import CertificadoParticipante
from extensions import db
from datetime import datetime
import hashlib
import qrcode
import io
import base64
from flask import current_app, url_for
import logging
import secrets
import string

logger = logging.getLogger(__name__)


def gerar_codigo_verificacao(certificado_id):
    """Gera código único de verificação para o certificado."""
    try:
        certificado = CertificadoParticipante.query.get(certificado_id)
        if not certificado:
            return None
            
        # Gerar código alfanumérico único
        codigo = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12))
        
        # Garantir que o código é único
        while CertificadoParticipante.query.filter_by(codigo_verificacao=codigo).first():
            codigo = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12))
            
        # Atualizar certificado com código
        certificado.codigo_verificacao = codigo
        certificado.data_verificacao_gerada = datetime.utcnow()
        
        db.session.commit()
        
        return codigo
        
    except Exception as e:
        logger.error(f"Erro ao gerar código de verificação: {str(e)}")
        db.session.rollback()
        return None


def gerar_qr_code_certificado(certificado_id):
    """Gera QR code para validação do certificado."""
    try:
        certificado = CertificadoParticipante.query.get(certificado_id)
        if not certificado:
            return None
            
        # Gerar código de verificação se não existir
        if not certificado.codigo_verificacao:
            codigo = gerar_codigo_verificacao(certificado_id)
            if not codigo:
                return None
        else:
            codigo = certificado.codigo_verificacao
            
        # URL de verificação
        url_verificacao = url_for('validacao.verificar_certificado', 
                                 codigo=codigo, _external=True)
        
        # Gerar QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url_verificacao)
        qr.make(fit=True)
        
        # Criar imagem
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Converter para base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            'qr_code': qr_code_base64,
            'codigo_verificacao': codigo,
            'url_verificacao': url_verificacao
        }
        
    except Exception as e:
        logger.error(f"Erro ao gerar QR code: {str(e)}")
        return None


def validar_certificado(codigo_verificacao):
    """Valida certificado pelo código de verificação."""
    try:
        certificado = CertificadoParticipante.query.filter_by(
            codigo_verificacao=codigo_verificacao
        ).first()
        
        if not certificado:
            return {
                'valido': False,
                'erro': 'Código de verificação não encontrado'
            }
            
        if not certificado.liberado:
            return {
                'valido': False,
                'erro': 'Certificado não foi liberado'
            }
            
        # Buscar dados relacionados
        usuario = Usuario.query.get(certificado.usuario_id)
        evento = Evento.query.get(certificado.evento_id)
        
        if not usuario or not evento:
            return {
                'valido': False,
                'erro': 'Dados do certificado não encontrados'
            }
            
        # Registrar acesso de validação
        _registrar_acesso_validacao(certificado.id)
        
        return {
            'valido': True,
            'certificado': {
                'id': certificado.id,
                'titulo': certificado.titulo,
                'tipo': certificado.tipo,
                'carga_horaria': certificado.carga_horaria,
                'data_emissao': certificado.data_emissao,
                'data_liberacao': certificado.data_liberacao,
                'hash_verificacao': certificado.hash_verificacao
            },
            'participante': {
                'nome': usuario.nome,
                'cpf': usuario.cpf,
                'email': usuario.email
            },
            'evento': {
                'nome': evento.nome,
                'data_inicio': evento.data_inicio,
                'data_fim': evento.data_fim,
                'cidade': evento.cidade,
                'organizador': evento.cliente.nome if evento.cliente else 'N/A'
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao validar certificado: {str(e)}")
        return {
            'valido': False,
            'erro': 'Erro interno do servidor'
        }


def validar_hash_certificado(certificado_id, hash_fornecido):
    """Valida integridade do certificado pelo hash."""
    try:
        certificado = CertificadoParticipante.query.get(certificado_id)
        if not certificado:
            return False
            
        return certificado.hash_verificacao == hash_fornecido
        
    except Exception as e:
        logger.error(f"Erro ao validar hash: {str(e)}")
        return False


def _registrar_acesso_validacao(certificado_id):
    """Registra acesso de validação do certificado."""
    try:
        from models.certificado import AcessoValidacaoCertificado
        
        acesso = AcessoValidacaoCertificado(
            certificado_id=certificado_id,
            data_acesso=datetime.utcnow(),
            ip_acesso=None  # Pode ser implementado para capturar IP
        )
        
        db.session.add(acesso)
        db.session.commit()
        
    except Exception as e:
        logger.error(f"Erro ao registrar acesso: {str(e)}")
        db.session.rollback()


def gerar_relatorio_validacoes(cliente_id, data_inicio=None, data_fim=None):
    """Gera relatório de validações de certificados."""
    try:
        from models.certificado import AcessoValidacaoCertificado
        
        query = db.session.query(
            AcessoValidacaoCertificado,
            CertificadoParticipante,
            Usuario,
            Evento
        ).join(
            CertificadoParticipante, 
            AcessoValidacaoCertificado.certificado_id == CertificadoParticipante.id
        ).join(
            Usuario, 
            CertificadoParticipante.usuario_id == Usuario.id
        ).join(
            Evento, 
            CertificadoParticipante.evento_id == Evento.id
        ).filter(
            Evento.cliente_id == cliente_id
        )
        
        if data_inicio:
            query = query.filter(AcessoValidacaoCertificado.data_acesso >= data_inicio)
            
        if data_fim:
            query = query.filter(AcessoValidacaoCertificado.data_acesso <= data_fim)
            
        resultados = query.order_by(AcessoValidacaoCertificado.data_acesso.desc()).all()
        
        validacoes = []
        for acesso, certificado, usuario, evento in resultados:
            validacoes.append({
                'data_acesso': acesso.data_acesso,
                'ip_acesso': acesso.ip_acesso,
                'certificado_titulo': certificado.titulo,
                'participante_nome': usuario.nome,
                'participante_email': usuario.email,
                'evento_nome': evento.nome,
                'codigo_verificacao': certificado.codigo_verificacao
            })
            
        return validacoes
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório: {str(e)}")
        return []


def verificar_integridade_certificados(cliente_id):
    """Verifica integridade de todos os certificados do cliente."""
    try:
        certificados = db.session.query(CertificadoParticipante).join(
            Evento, CertificadoParticipante.evento_id == Evento.id
        ).filter(
            Evento.cliente_id == cliente_id,
            CertificadoParticipante.arquivo_path.isnot(None)
        ).all()
        
        resultados = []
        
        for certificado in certificados:
            try:
                import os
                arquivo_path = os.path.join(
                    current_app.static_folder, 
                    certificado.arquivo_path
                )
                
                if os.path.exists(arquivo_path):
                    # Calcular hash atual do arquivo
                    with open(arquivo_path, 'rb') as f:
                        hash_atual = hashlib.sha256(f.read()).hexdigest()
                        
                    integro = hash_atual == certificado.hash_verificacao
                else:
                    integro = False
                    hash_atual = None
                    
                resultados.append({
                    'certificado_id': certificado.id,
                    'titulo': certificado.titulo,
                    'arquivo_path': certificado.arquivo_path,
                    'hash_original': certificado.hash_verificacao,
                    'hash_atual': hash_atual,
                    'integro': integro,
                    'arquivo_existe': os.path.exists(arquivo_path) if certificado.arquivo_path else False
                })
                
            except Exception as e:
                logger.error(f"Erro ao verificar certificado {certificado.id}: {str(e)}")
                resultados.append({
                    'certificado_id': certificado.id,
                    'titulo': certificado.titulo,
                    'erro': str(e),
                    'integro': False
                })
                
        return resultados
        
    except Exception as e:
        logger.error(f"Erro ao verificar integridade: {str(e)}")
        return []


def buscar_certificados_por_participante(cpf_ou_email):
    """Busca certificados de um participante por CPF ou email."""
    try:
        usuario = Usuario.query.filter(
            (Usuario.cpf == cpf_ou_email) | (Usuario.email == cpf_ou_email)
        ).first()
        
        if not usuario:
            return []
            
        certificados = CertificadoParticipante.query.filter_by(
            usuario_id=usuario.id,
            liberado=True
        ).all()
        
        resultado = []
        for certificado in certificados:
            evento = Evento.query.get(certificado.evento_id)
            
            resultado.append({
                'certificado': certificado,
                'evento': evento,
                'codigo_verificacao': certificado.codigo_verificacao,
                'url_verificacao': url_for('validacao.verificar_certificado', 
                                         codigo=certificado.codigo_verificacao, 
                                         _external=True) if certificado.codigo_verificacao else None
            })
            
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao buscar certificados: {str(e)}")
        return []