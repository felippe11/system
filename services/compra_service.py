"""
Serviço para gerenciamento de compras e validação de documentos fiscais.
"""

import hashlib
import mimetypes
import os
import time
import uuid
import xml.etree.ElementTree as ET
from typing import Dict, List

from flask import current_app
from PIL import Image
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

try:
    import magic
except ImportError:  # pragma: no cover - depends on optional system library
    magic = None


class CompraService:
    """Serviço para operações relacionadas a compras e documentos fiscais."""
    
    # Extensões permitidas para documentos fiscais
    ALLOWED_EXTENSIONS = {
        'pdf': ['application/pdf'],
        'jpg': ['image/jpeg'],
        'jpeg': ['image/jpeg'],
        'png': ['image/png'],
        'xml': ['application/xml', 'text/xml'],
        'zip': ['application/zip'],
        'rar': ['application/x-rar-compressed'],
        'doc': ['application/msword'],
        'docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    }
    
    # Tamanho máximo por arquivo (em MB)
    MAX_FILE_SIZE_MB = 10
    
    # Tamanho máximo total por compra (em MB)
    MAX_TOTAL_SIZE_MB = 50
    
    @staticmethod
    def validate_fiscal_document(file: FileStorage, document_type: str = None) -> Dict[str, any]:
        """
        Valida um documento fiscal antes do upload.
        
        Args:
            file: Arquivo a ser validado
            document_type: Tipo do documento (nota_fiscal, cupom_fiscal, etc.)
            
        Returns:
            Dict com resultado da validação
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'file_info': {}
        }
        
        try:
            # Verificar se arquivo existe
            if not file or not file.filename:
                result['errors'].append('Nenhum arquivo foi selecionado.')
                return result
            
            # Obter informações básicas do arquivo
            filename = secure_filename(file.filename)
            file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            
            result['file_info'] = {
                'original_name': file.filename,
                'secure_name': filename,
                'extension': file_ext,
                'size': 0
            }
            
            # Verificar extensão
            if file_ext not in CompraService.ALLOWED_EXTENSIONS:
                result['errors'].append(
                    f'Tipo de arquivo não permitido. '
                    f'Extensões aceitas: {", ".join(CompraService.ALLOWED_EXTENSIONS.keys())}'
                )
                return result
            
            # Verificar tamanho do arquivo
            file.seek(0, 2)  # Ir para o final
            file_size = file.tell()
            file.seek(0)  # Voltar ao início
            
            result['file_info']['size'] = file_size
            
            if file_size > CompraService.MAX_FILE_SIZE_MB * 1024 * 1024:
                result['errors'].append(
                    f'Arquivo muito grande. Tamanho máximo: {CompraService.MAX_FILE_SIZE_MB}MB'
                )
                return result
            
            if file_size == 0:
                result['errors'].append('Arquivo está vazio.')
                return result
            
            # Verificar MIME type
            file_content = file.read(1024)  # Ler apenas os primeiros 1024 bytes
            file.seek(0)  # Voltar ao início
            
            detected_mime = None
            expected_mimes = CompraService.ALLOWED_EXTENSIONS.get(file_ext, [])

            if magic:
                try:
                    detected_mime = magic.from_buffer(file_content, mime=True)
                except Exception:
                    result['warnings'].append(
                        'Não foi possível verificar o tipo do arquivo com magic.'
                    )
            else:
                guessed_mime, _ = mimetypes.guess_type(filename)
                detected_mime = guessed_mime
                if not guessed_mime:
                    result['warnings'].append(
                        'Verificação do tipo de arquivo limitada: biblioteca magic não disponível.'
                    )

            if detected_mime and expected_mimes and detected_mime not in expected_mimes:
                result['warnings'].append(
                    f'Tipo de arquivo detectado ({detected_mime}) não corresponde à extensão ({file_ext})'
                )
            elif not detected_mime:
                result['warnings'].append('Não foi possível verificar o tipo do arquivo.')
            
            # Validações específicas por tipo de documento
            if document_type:
                validation_result = CompraService._validate_document_type(file, document_type, file_ext)
                result['errors'].extend(validation_result.get('errors', []))
                result['warnings'].extend(validation_result.get('warnings', []))
            
            # Verificar se é uma imagem válida (para JPG, PNG)
            if file_ext in ['jpg', 'jpeg', 'png']:
                try:
                    file.seek(0)
                    img = Image.open(file)
                    img.verify()
                    file.seek(0)
                    
                    # Verificar dimensões mínimas
                    width, height = img.size
                    if width < 100 or height < 100:
                        result['warnings'].append('Imagem com resolução muito baixa.')
                    
                    result['file_info']['dimensions'] = f'{width}x{height}'
                    
                except Exception as e:
                    result['errors'].append('Arquivo de imagem corrompido ou inválido.')
                    return result
            
            # Se chegou até aqui, arquivo é válido
            result['valid'] = True
            
        except Exception as e:
            result['errors'].append(f'Erro na validação: {str(e)}')
        
        return result
    
    @staticmethod
    def _validate_document_type(file: FileStorage, document_type: str, file_ext: str) -> Dict[str, List[str]]:
        """Validações específicas por tipo de documento."""
        result = {'errors': [], 'warnings': []}
        
        try:
            if document_type == 'nota_fiscal' and file_ext == 'xml':
                # Validar XML de nota fiscal
                file.seek(0)
                content = file.read()
                file.seek(0)
                
                try:
                    root = ET.fromstring(content)
                    # Verificar se é um XML de NFe válido
                    if 'NFe' not in root.tag and 'nfeProc' not in root.tag:
                        result['warnings'].append('XML pode não ser uma Nota Fiscal Eletrônica válida.')
                except ET.ParseError:
                    result['errors'].append('XML inválido ou corrompido.')
            
            elif document_type == 'cupom_fiscal':
                # Cupons fiscais geralmente são PDFs ou imagens
                if file_ext not in ['pdf', 'jpg', 'jpeg', 'png']:
                    result['warnings'].append('Cupons fiscais são geralmente em formato PDF ou imagem.')
            
            elif document_type == 'recibo':
                # Recibos podem ser PDFs, imagens ou documentos
                if file_ext not in ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx']:
                    result['warnings'].append('Recibos são geralmente em formato PDF, imagem ou documento.')
            
        except Exception as e:
            result['warnings'].append(f'Não foi possível validar especificamente o tipo de documento: {str(e)}')
        
        return result
    
    @staticmethod
    def generate_secure_filename(original_filename: str, compra_id: int) -> str:
        """Gera um nome de arquivo seguro e único."""
        # Obter extensão
        ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        
        # Gerar nome único
        unique_id = str(uuid.uuid4())
        timestamp = str(int(time.time()))
        
        # Criar hash do nome original para referência
        original_hash = hashlib.md5(original_filename.encode()).hexdigest()[:8]
        
        return f"compra_{compra_id}_{timestamp}_{original_hash}_{unique_id}.{ext}"
    
    @staticmethod
    def calculate_file_hash(file: FileStorage) -> str:
        """Calcula hash SHA-256 do arquivo para verificação de integridade."""
        file.seek(0)
        hash_sha256 = hashlib.sha256()
        
        for chunk in iter(lambda: file.read(4096), b""):
            hash_sha256.update(chunk)
        
        file.seek(0)
        return hash_sha256.hexdigest()
    
    @staticmethod
    def validate_total_upload_size(compra_id: int, new_file_size: int) -> bool:
        """Verifica se o tamanho total dos arquivos não excede o limite."""
        from models.compra import Compra
        
        compra = Compra.query.get(compra_id)
        if not compra:
            return False
        
        # Calcular tamanho total atual
        total_size = sum(doc.tamanho_arquivo or 0 for doc in compra.documentos)
        
        # Verificar se novo arquivo excede limite
        if (total_size + new_file_size) > CompraService.MAX_TOTAL_SIZE_MB * 1024 * 1024:
            return False
        
        return True
    
    @staticmethod
    def scan_for_malware(file_path: str) -> Dict[str, any]:
        """
        Simula escaneamento de malware (implementação básica).
        Em produção, integrar com antivírus real.
        """
        result = {
            'safe': True,
            'threats': [],
            'scan_time': time.time()
        }
        
        try:
            # Verificações básicas de segurança
            file_size = os.path.getsize(file_path)
            
            # Arquivo muito pequeno pode ser suspeito
            if file_size < 10:
                result['threats'].append('Arquivo suspeito: tamanho muito pequeno')
                result['safe'] = False
            
            # Verificar se arquivo tem conteúdo executável (básico)
            with open(file_path, 'rb') as f:
                header = f.read(4)
                
                # Headers de executáveis conhecidos
                executable_headers = [
                    b'MZ\x90\x00',  # PE executável
                    b'\x7fELF',     # ELF executável
                    b'\xca\xfe\xba\xbe',  # Mach-O
                ]
                
                for exe_header in executable_headers:
                    if header.startswith(exe_header):
                        result['threats'].append('Arquivo contém código executável')
                        result['safe'] = False
                        break
            
        except Exception as e:
            result['threats'].append(f'Erro no escaneamento: {str(e)}')
            result['safe'] = False
        
        return result
    
    @staticmethod
    def create_upload_directory(compra_id: int) -> str:
        """Cria diretório de upload para uma compra específica."""
        base_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        compra_dir = os.path.join(base_dir, 'compras', str(compra_id))
        
        os.makedirs(compra_dir, exist_ok=True)
        
        # Criar arquivo .htaccess para segurança (se Apache)
        htaccess_path = os.path.join(compra_dir, '.htaccess')
        if not os.path.exists(htaccess_path):
            with open(htaccess_path, 'w') as f:
                f.write('Options -Indexes\n')
                f.write('Options -ExecCGI\n')
                f.write('<Files "*.php">\n')
                f.write('    Deny from all\n')
                f.write('</Files>\n')
        
        return compra_dir
    
    @staticmethod
    def cleanup_temp_files(directory: str, max_age_hours: int = 24):
        """Remove arquivos temporários antigos."""
        import time
        
        if not os.path.exists(directory):
            return
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for filename in os.listdir(directory):
            if filename.startswith('temp_'):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getctime(file_path)
                    if file_age > max_age_seconds:
                        try:
                            os.remove(file_path)
                        except:
                            pass  # Ignorar erros de remoção
