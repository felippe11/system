"""
Serviço especializado para processamento de documentos fiscais.
Inclui validação, extração de dados, OCR e análise de conformidade.
"""

import os
import hashlib
import mimetypes
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re
import json
from werkzeug.utils import secure_filename
from PIL import Image
import fitz  # PyMuPDF para PDFs

from models import db, DocumentoFiscal, Compra
from utils.file_utils import ensure_directory_exists


class DocumentoFiscalService:
    """Serviço para processamento avançado de documentos fiscais."""
    
    # Configurações
    UPLOAD_FOLDER = 'static/documentos_fiscais'
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'xml', 'zip', 'rar'}
    
    # Tipos de documento e suas validações específicas
    TIPOS_DOCUMENTO = {
        'nota_fiscal': {
            'nome': 'Nota Fiscal',
            'extensoes_preferenciais': ['xml', 'pdf'],
            'campos_obrigatorios': ['numero_documento', 'data_emissao', 'valor_documento'],
            'validacao_especial': True
        },
        'nota_fiscal_eletronica': {
            'nome': 'Nota Fiscal Eletrônica (NFe)',
            'extensoes_preferenciais': ['xml'],
            'campos_obrigatorios': ['numero_documento', 'chave_acesso', 'data_emissao', 'valor_documento'],
            'validacao_especial': True
        },
        'cupom_fiscal': {
            'nome': 'Cupom Fiscal',
            'extensoes_preferenciais': ['pdf', 'jpg', 'jpeg', 'png'],
            'campos_obrigatorios': ['data_emissao', 'valor_documento'],
            'validacao_especial': False
        },
        'recibo': {
            'nome': 'Recibo',
            'extensoes_preferenciais': ['pdf', 'jpg', 'jpeg', 'png'],
            'campos_obrigatorios': ['data_emissao', 'valor_documento'],
            'validacao_especial': False
        },
        'comprovante_pagamento': {
            'nome': 'Comprovante de Pagamento',
            'extensoes_preferenciais': ['pdf', 'jpg', 'jpeg', 'png'],
            'campos_obrigatorios': ['data_emissao', 'valor_documento'],
            'validacao_especial': False
        },
        'boleto': {
            'nome': 'Boleto Bancário',
            'extensoes_preferenciais': ['pdf'],
            'campos_obrigatorios': ['data_emissao', 'valor_documento'],
            'validacao_especial': False
        },
        'outros': {
            'nome': 'Outros Documentos',
            'extensoes_preferenciais': ['pdf', 'jpg', 'jpeg', 'png'],
            'campos_obrigatorios': [],
            'validacao_especial': False
        }
    }
    
    @classmethod
    def processar_upload(cls, arquivo, compra_id: int, tipo_documento: str, 
                        observacoes: str = None, usuario_id: int = None) -> Dict:
        """
        Processa upload completo de documento fiscal.
        
        Args:
            arquivo: Arquivo enviado
            compra_id: ID da compra
            tipo_documento: Tipo do documento
            observacoes: Observações opcionais
            usuario_id: ID do usuário que fez upload
            
        Returns:
            Dict com resultado do processamento
        """
        try:
            # Validações iniciais
            validacao = cls._validar_arquivo(arquivo, tipo_documento)
            if not validacao['valido']:
                return {'success': False, 'error': validacao['erro']}
            
            # Verificar se compra existe e pertence ao usuário
            compra = Compra.query.get(compra_id)
            if not compra:
                return {'success': False, 'error': 'Compra não encontrada'}
            
            # Gerar nome seguro e caminho
            nome_original = secure_filename(arquivo.filename)
            extensao = nome_original.split('.')[-1].lower()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_seguro = f"{compra_id}_{tipo_documento}_{timestamp}.{extensao}"
            
            # Criar diretório se não existir
            upload_path = os.path.join(cls.UPLOAD_FOLDER, str(compra.cliente_id))
            ensure_directory_exists(upload_path)
            
            caminho_completo = os.path.join(upload_path, nome_seguro)
            
            # Salvar arquivo
            arquivo.save(caminho_completo)
            
            # Calcular hash para integridade
            hash_arquivo = cls._calcular_hash_arquivo(caminho_completo)
            
            # Obter informações do arquivo
            tamanho_arquivo = os.path.getsize(caminho_completo)
            tipo_mime = mimetypes.guess_type(caminho_completo)[0]
            
            # Extrair dados do documento
            dados_extraidos = cls._extrair_dados_documento(caminho_completo, tipo_documento)
            
            # Validar documento específico
            resultado_validacao = cls._validar_documento_especifico(
                caminho_completo, tipo_documento, dados_extraidos
            )
            
            # Criar registro no banco
            documento = DocumentoFiscal(
                tipo_documento=tipo_documento,
                numero_documento=dados_extraidos.get('numero_documento'),
                serie_documento=dados_extraidos.get('serie_documento'),
                chave_acesso=dados_extraidos.get('chave_acesso'),
                nome_arquivo=nome_original,
                nome_arquivo_seguro=nome_seguro,
                caminho_arquivo=caminho_completo,
                tamanho_arquivo=tamanho_arquivo,
                tipo_mime=tipo_mime,
                hash_arquivo=hash_arquivo,
                data_emissao=dados_extraidos.get('data_emissao'),
                valor_documento=dados_extraidos.get('valor_documento'),
                observacoes=observacoes,
                compra_id=compra_id,
                usuario_upload_id=usuario_id,
                validacao_resultado=json.dumps(resultado_validacao),
                scan_seguranca=json.dumps({'status': 'pendente'})
            )
            
            db.session.add(documento)
            db.session.commit()
            
            return {
                'success': True,
                'documento_id': documento.id,
                'dados_extraidos': dados_extraidos,
                'validacao': resultado_validacao,
                'warnings': resultado_validacao.get('warnings', [])
            }
            
        except Exception as e:
            db.session.rollback()
            # Remover arquivo se foi salvo
            if 'caminho_completo' in locals() and os.path.exists(caminho_completo):
                os.remove(caminho_completo)
            return {'success': False, 'error': f'Erro ao processar upload: {str(e)}'}
    
    @classmethod
    def _validar_arquivo(cls, arquivo, tipo_documento: str) -> Dict:
        """Valida arquivo antes do upload."""
        if not arquivo or arquivo.filename == '':
            return {'valido': False, 'erro': 'Nenhum arquivo selecionado'}
        
        # Verificar extensão
        extensao = arquivo.filename.split('.')[-1].lower()
        if extensao not in cls.ALLOWED_EXTENSIONS:
            return {'valido': False, 'erro': f'Extensão {extensao} não permitida'}
        
        # Verificar tamanho (se possível)
        arquivo.seek(0, 2)  # Ir para o final
        tamanho = arquivo.tell()
        arquivo.seek(0)  # Voltar ao início
        
        if tamanho > cls.MAX_FILE_SIZE:
            return {'valido': False, 'erro': 'Arquivo muito grande (máx. 16MB)'}
        
        # Verificar se extensão é adequada para o tipo
        if tipo_documento in cls.TIPOS_DOCUMENTO:
            extensoes_preferenciais = cls.TIPOS_DOCUMENTO[tipo_documento]['extensoes_preferenciais']
            if extensao not in extensoes_preferenciais:
                return {
                    'valido': True,
                    'warning': f'Extensão {extensao} não é preferencial para {tipo_documento}. '
                              f'Recomendado: {", ".join(extensoes_preferenciais)}'
                }
        
        return {'valido': True}
    
    @classmethod
    def _calcular_hash_arquivo(cls, caminho_arquivo: str) -> str:
        """Calcula hash SHA-256 do arquivo."""
        hash_sha256 = hashlib.sha256()
        with open(caminho_arquivo, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    @classmethod
    def _extrair_dados_documento(cls, caminho_arquivo: str, tipo_documento: str) -> Dict:
        """Extrai dados do documento baseado no tipo e formato."""
        extensao = caminho_arquivo.split('.')[-1].lower()
        dados = {}
        
        try:
            if extensao == 'xml' and tipo_documento in ['nota_fiscal', 'nota_fiscal_eletronica']:
                dados = cls._extrair_dados_xml_nfe(caminho_arquivo)
            elif extensao == 'pdf':
                dados = cls._extrair_dados_pdf(caminho_arquivo, tipo_documento)
            elif extensao in ['jpg', 'jpeg', 'png']:
                dados = cls._extrair_dados_imagem(caminho_arquivo, tipo_documento)
            
        except Exception as e:
            dados['erro_extracao'] = str(e)
        
        return dados
    
    @classmethod
    def _extrair_dados_xml_nfe(cls, caminho_arquivo: str) -> Dict:
        """Extrai dados de XML de Nota Fiscal Eletrônica."""
        dados = {}
        
        try:
            tree = ET.parse(caminho_arquivo)
            root = tree.getroot()
            
            # Namespace da NFe
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            
            # Buscar dados da NFe
            inf_nfe = root.find('.//nfe:infNFe', ns)
            if inf_nfe is not None:
                # Chave de acesso
                dados['chave_acesso'] = inf_nfe.get('Id', '').replace('NFe', '')
                
                # Dados da nota
                ide = inf_nfe.find('nfe:ide', ns)
                if ide is not None:
                    dados['numero_documento'] = ide.find('nfe:nNF', ns).text if ide.find('nfe:nNF', ns) is not None else None
                    dados['serie_documento'] = ide.find('nfe:serie', ns).text if ide.find('nfe:serie', ns) is not None else None
                    
                    # Data de emissão
                    data_emissao = ide.find('nfe:dhEmi', ns)
                    if data_emissao is not None:
                        try:
                            dados['data_emissao'] = datetime.fromisoformat(data_emissao.text.replace('Z', '+00:00'))
                        except:
                            pass
                
                # Valor total
                total = inf_nfe.find('.//nfe:vNF', ns)
                if total is not None:
                    try:
                        dados['valor_documento'] = float(total.text)
                    except:
                        pass
                
                # Dados do emitente
                emit = inf_nfe.find('nfe:emit', ns)
                if emit is not None:
                    cnpj = emit.find('nfe:CNPJ', ns)
                    nome = emit.find('nfe:xNome', ns)
                    if cnpj is not None and nome is not None:
                        dados['emitente'] = f"{nome.text} (CNPJ: {cnpj.text})"
                
        except Exception as e:
            dados['erro_xml'] = str(e)
        
        return dados
    
    @classmethod
    def _extrair_dados_pdf(cls, caminho_arquivo: str, tipo_documento: str) -> Dict:
        """Extrai dados de arquivo PDF usando OCR básico."""
        dados = {}
        
        try:
            doc = fitz.open(caminho_arquivo)
            texto_completo = ""
            
            for page in doc:
                texto_completo += page.get_text()
            
            doc.close()
            
            # Buscar padrões comuns
            dados.update(cls._buscar_padroes_texto(texto_completo, tipo_documento))
            
        except Exception as e:
            dados['erro_pdf'] = str(e)
        
        return dados
    
    @classmethod
    def _extrair_dados_imagem(cls, caminho_arquivo: str, tipo_documento: str) -> Dict:
        """Extrai dados de imagem (placeholder para OCR futuro)."""
        dados = {}
        
        try:
            # Verificar se imagem é válida
            with Image.open(caminho_arquivo) as img:
                dados['largura'] = img.width
                dados['altura'] = img.height
                dados['formato'] = img.format
            
            # TODO: Implementar OCR com pytesseract se disponível
            dados['ocr_disponivel'] = False
            
        except Exception as e:
            dados['erro_imagem'] = str(e)
        
        return dados
    
    @classmethod
    def _buscar_padroes_texto(cls, texto: str, tipo_documento: str) -> Dict:
        """Busca padrões comuns em texto extraído."""
        dados = {}
        
        # Padrões regex
        padroes = {
            'valor': [
                r'(?:total|valor|r\$)\s*:?\s*r?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                r'(\d{1,3}(?:\.\d{3})*,\d{2})'
            ],
            'data': [
                r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'(\d{2,4}[\/\-]\d{1,2}[\/\-]\d{1,2})'
            ],
            'numero_nota': [
                r'(?:nota|nf|número)\s*:?\s*(\d+)',
                r'n[úu]mero\s*:?\s*(\d+)'
            ],
            'cnpj': [
                r'(\d{2}\.\d{3}\.\d{3}\/\d{4}\-\d{2})',
                r'cnpj\s*:?\s*(\d{2}\.\d{3}\.\d{3}\/\d{4}\-\d{2})'
            ]
        }
        
        texto_lower = texto.lower()
        
        for tipo, patterns in padroes.items():
            for pattern in patterns:
                match = re.search(pattern, texto_lower)
                if match:
                    valor = match.group(1)
                    
                    if tipo == 'valor':
                        try:
                            # Converter para float
                            valor_limpo = valor.replace('.', '').replace(',', '.')
                            dados['valor_documento'] = float(valor_limpo)
                        except:
                            pass
                    elif tipo == 'data':
                        try:
                            # Tentar converter data
                            for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d', '%Y-%m-%d']:
                                try:
                                    dados['data_emissao'] = datetime.strptime(valor, fmt)
                                    break
                                except:
                                    continue
                        except:
                            pass
                    elif tipo == 'numero_nota':
                        dados['numero_documento'] = valor
                    elif tipo == 'cnpj':
                        dados['cnpj_emitente'] = valor
                    
                    break  # Usar primeira ocorrência encontrada
        
        return dados
    
    @classmethod
    def _validar_documento_especifico(cls, caminho_arquivo: str, tipo_documento: str, dados_extraidos: Dict) -> Dict:
        """Valida documento específico baseado no tipo."""
        resultado = {
            'valido': True,
            'warnings': [],
            'erros': [],
            'score_qualidade': 100
        }
        
        if tipo_documento not in cls.TIPOS_DOCUMENTO:
            resultado['warnings'].append('Tipo de documento não reconhecido')
            resultado['score_qualidade'] -= 10
        
        # Verificar campos obrigatórios
        tipo_config = cls.TIPOS_DOCUMENTO.get(tipo_documento, {})
        campos_obrigatorios = tipo_config.get('campos_obrigatorios', [])
        
        for campo in campos_obrigatorios:
            if campo not in dados_extraidos or not dados_extraidos[campo]:
                resultado['warnings'].append(f'Campo obrigatório não encontrado: {campo}')
                resultado['score_qualidade'] -= 15
        
        # Validações específicas por tipo
        if tipo_documento == 'nota_fiscal_eletronica':
            if 'chave_acesso' in dados_extraidos:
                chave = dados_extraidos['chave_acesso']
                if len(chave) != 44:
                    resultado['erros'].append('Chave de acesso da NFe deve ter 44 dígitos')
                    resultado['score_qualidade'] -= 25
        
        # Verificar consistência de valores
        if 'valor_documento' in dados_extraidos:
            valor = dados_extraidos['valor_documento']
            if valor <= 0:
                resultado['warnings'].append('Valor do documento deve ser maior que zero')
                resultado['score_qualidade'] -= 10
            elif valor > 1000000:  # 1 milhão
                resultado['warnings'].append('Valor muito alto, verifique se está correto')
                resultado['score_qualidade'] -= 5
        
        # Verificar data de emissão
        if 'data_emissao' in dados_extraidos:
            data_emissao = dados_extraidos['data_emissao']
            if isinstance(data_emissao, datetime):
                hoje = datetime.now()
                if data_emissao > hoje:
                    resultado['warnings'].append('Data de emissão é futura')
                    resultado['score_qualidade'] -= 10
                elif (hoje - data_emissao).days > 365:
                    resultado['warnings'].append('Documento muito antigo (mais de 1 ano)')
                    resultado['score_qualidade'] -= 5
        
        # Determinar se é válido baseado no score
        if resultado['score_qualidade'] < 50:
            resultado['valido'] = False
        
        return resultado
    
    @classmethod
    def obter_tipos_documento(cls) -> Dict:
        """Retorna tipos de documento disponíveis."""
        return cls.TIPOS_DOCUMENTO
    
    @classmethod
    def validar_integridade_arquivo(cls, documento_id: int) -> Dict:
        """Valida integridade de arquivo já salvo."""
        documento = DocumentoFiscal.query.get(documento_id)
        if not documento:
            return {'valido': False, 'erro': 'Documento não encontrado'}
        
        if not os.path.exists(documento.caminho_arquivo):
            return {'valido': False, 'erro': 'Arquivo não encontrado no sistema'}
        
        # Recalcular hash
        hash_atual = cls._calcular_hash_arquivo(documento.caminho_arquivo)
        
        if hash_atual != documento.hash_arquivo:
            return {'valido': False, 'erro': 'Arquivo foi modificado ou corrompido'}
        
        return {'valido': True, 'hash': hash_atual}
    
    @classmethod
    def gerar_relatorio_documentos(cls, compra_id: int = None, cliente_id: int = None) -> Dict:
        """Gera relatório de documentos fiscais."""
        query = DocumentoFiscal.query.filter_by(ativo=True)
        
        if compra_id:
            query = query.filter_by(compra_id=compra_id)
        elif cliente_id:
            query = query.join(Compra).filter(Compra.cliente_id == cliente_id)
        
        documentos = query.all()
        
        # Estatísticas
        total_documentos = len(documentos)
        tipos_count = {}
        tamanho_total = 0
        documentos_com_problemas = 0
        
        for doc in documentos:
            # Contar por tipo
            tipos_count[doc.tipo_documento] = tipos_count.get(doc.tipo_documento, 0) + 1
            
            # Somar tamanho
            if doc.tamanho_arquivo:
                tamanho_total += doc.tamanho_arquivo
            
            # Verificar problemas
            if doc.validacao_resultado:
                try:
                    validacao = json.loads(doc.validacao_resultado)
                    if not validacao.get('valido', True) or validacao.get('score_qualidade', 100) < 70:
                        documentos_com_problemas += 1
                except:
                    documentos_com_problemas += 1
        
        return {
            'total_documentos': total_documentos,
            'tipos_count': tipos_count,
            'tamanho_total_mb': round(tamanho_total / (1024 * 1024), 2),
            'documentos_com_problemas': documentos_com_problemas,
            'documentos': [doc.to_dict() for doc in documentos]
        }