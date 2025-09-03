from typing import Dict, List, Any, Tuple, Optional
import re
import pandas as pd
from datetime import datetime
import logging
from email_validator import validate_email, EmailNotValidError
from models import Evento, Categoria, Modalidade
from sqlalchemy import and_
from database import db

class ValidationService:
    """Serviço para validação avançada de dados de importação"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Padrões de validação
        self.patterns = {
            'cpf': re.compile(r'^\d{3}\.\d{3}\.\d{3}-\d{2}$|^\d{11}$'),
            'phone': re.compile(r'^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$'),
            'cep': re.compile(r'^\d{5}-?\d{3}$'),
            'url': re.compile(r'^https?://[\w\.-]+\.[a-zA-Z]{2,}'),
            'orcid': re.compile(r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$')
        }
        
        # Configurações de validação
        self.validation_config = {
            'max_title_length': 500,
            'max_abstract_length': 5000,
            'max_keywords_count': 10,
            'max_authors_count': 20,
            'required_fields': ['titulo', 'resumo', 'autores'],
            'email_domains_whitelist': None,  # None = aceitar todos
            'forbidden_words': ['teste', 'example', 'dummy']
        }
    
    def validate_submission_data(self, data: Dict[str, Any], evento_id: int) -> Dict[str, Any]:
        """Valida dados de uma submissão"""
        errors = []
        warnings = []
        normalized_data = data.copy()
        
        try:
            # Validações básicas
            errors.extend(self._validate_required_fields(data))
            errors.extend(self._validate_field_lengths(data))
            errors.extend(self._validate_field_formats(data))
            
            # Validações de negócio
            business_errors, business_warnings = self._validate_business_rules(data, evento_id)
            errors.extend(business_errors)
            warnings.extend(business_warnings)
            
            # Normalização de dados
            normalized_data = self._normalize_submission_data(data)
            
            # Validações de integridade
            integrity_errors = self._validate_data_integrity(normalized_data, evento_id)
            errors.extend(integrity_errors)
            
            # Validações de consistência
            consistency_warnings = self._validate_data_consistency(normalized_data)
            warnings.extend(consistency_warnings)
            
        except Exception as e:
            self.logger.error(f"Erro durante validação: {str(e)}")
            errors.append(f"Erro interno de validação: {str(e)}")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'normalized_data': normalized_data,
            'validation_score': self._calculate_validation_score(errors, warnings)
        }
    
    def validate_reviewer_data(self, data: Dict[str, Any], evento_id: int) -> Dict[str, Any]:
        """Valida dados de um revisor"""
        errors = []
        warnings = []
        normalized_data = data.copy()
        
        try:
            # Validações específicas para revisores
            errors.extend(self._validate_reviewer_required_fields(data))
            errors.extend(self._validate_reviewer_email(data))
            errors.extend(self._validate_reviewer_preferences(data, evento_id))
            
            # Normalização
            normalized_data = self._normalize_reviewer_data(data)
            
            # Validações de duplicação
            duplication_warnings = self._check_reviewer_duplication(normalized_data, evento_id)
            warnings.extend(duplication_warnings)
            
        except Exception as e:
            self.logger.error(f"Erro durante validação de revisor: {str(e)}")
            errors.append(f"Erro interno de validação: {str(e)}")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'normalized_data': normalized_data,
            'validation_score': self._calculate_validation_score(errors, warnings)
        }
    
    def validate_batch_import(self, df: pd.DataFrame, data_type: str, evento_id: int) -> Dict[str, Any]:
        """Valida importação em lote"""
        results = {
            'total_records': len(df),
            'valid_records': 0,
            'invalid_records': 0,
            'records_with_warnings': 0,
            'validation_details': [],
            'summary_errors': [],
            'summary_warnings': [],
            'processing_time': 0
        }
        
        start_time = datetime.now()
        
        try:
            # Validação estrutural do DataFrame
            structural_errors = self._validate_dataframe_structure(df, data_type)
            if structural_errors:
                results['summary_errors'].extend(structural_errors)
                return results
            
            # Validação linha por linha
            for index, row in df.iterrows():
                row_data = row.to_dict()
                
                if data_type == 'submission':
                    validation_result = self.validate_submission_data(row_data, evento_id)
                elif data_type == 'reviewer':
                    validation_result = self.validate_reviewer_data(row_data, evento_id)
                else:
                    raise ValueError(f"Tipo de dados não suportado: {data_type}")
                
                # Adicionar número da linha aos erros e warnings
                for error in validation_result['errors']:
                    validation_result['errors'] = [f"Linha {index + 2}: {error}" for error in validation_result['errors']]
                
                for warning in validation_result['warnings']:
                    validation_result['warnings'] = [f"Linha {index + 2}: {warning}" for warning in validation_result['warnings']]
                
                # Contabilizar resultados
                if validation_result['is_valid']:
                    results['valid_records'] += 1
                else:
                    results['invalid_records'] += 1
                
                if validation_result['warnings']:
                    results['records_with_warnings'] += 1
                
                # Armazenar detalhes
                results['validation_details'].append({
                    'row': index + 2,
                    'is_valid': validation_result['is_valid'],
                    'errors': validation_result['errors'],
                    'warnings': validation_result['warnings'],
                    'validation_score': validation_result['validation_score']
                })
            
            # Validações globais do lote
            batch_warnings = self._validate_batch_consistency(df, data_type, evento_id)
            results['summary_warnings'].extend(batch_warnings)
            
        except Exception as e:
            self.logger.error(f"Erro durante validação em lote: {str(e)}")
            results['summary_errors'].append(f"Erro interno: {str(e)}")
        
        finally:
            results['processing_time'] = (datetime.now() - start_time).total_seconds()
        
        return results
    
    def _validate_required_fields(self, data: Dict[str, Any]) -> List[str]:
        """Valida campos obrigatórios"""
        errors = []
        
        for field in self.validation_config['required_fields']:
            if field not in data or not data[field] or str(data[field]).strip() == '':
                errors.append(f"Campo obrigatório '{field}' está vazio ou ausente")
        
        return errors
    
    def _validate_field_lengths(self, data: Dict[str, Any]) -> List[str]:
        """Valida comprimento dos campos"""
        errors = []
        
        # Título
        if 'titulo' in data and len(str(data['titulo'])) > self.validation_config['max_title_length']:
            errors.append(f"Título excede {self.validation_config['max_title_length']} caracteres")
        
        # Resumo
        if 'resumo' in data and len(str(data['resumo'])) > self.validation_config['max_abstract_length']:
            errors.append(f"Resumo excede {self.validation_config['max_abstract_length']} caracteres")
        
        return errors
    
    def _validate_field_formats(self, data: Dict[str, Any]) -> List[str]:
        """Valida formatos dos campos"""
        errors = []
        
        # Email dos autores
        if 'autores' in data:
            authors = self._parse_authors(data['autores'])
            for i, author in enumerate(authors):
                if 'email' in author and author['email']:
                    try:
                        validate_email(author['email'])
                    except EmailNotValidError:
                        errors.append(f"Email inválido para autor {i + 1}: {author['email']}")
        
        # CPF (se presente)
        if 'cpf' in data and data['cpf']:
            if not self.patterns['cpf'].match(str(data['cpf'])):
                errors.append("Formato de CPF inválido")
        
        # Telefone (se presente)
        if 'telefone' in data and data['telefone']:
            if not self.patterns['phone'].match(str(data['telefone'])):
                errors.append("Formato de telefone inválido")
        
        # ORCID (se presente)
        if 'orcid' in data and data['orcid']:
            if not self.patterns['orcid'].match(str(data['orcid'])):
                errors.append("Formato de ORCID inválido")
        
        return errors
    
    def _validate_business_rules(self, data: Dict[str, Any], evento_id: int) -> Tuple[List[str], List[str]]:
        """Valida regras de negócio"""
        errors = []
        warnings = []
        
        try:
            # Verificar se categoria existe
            if 'categoria' in data and data['categoria']:
                categoria = db.session.query(Categoria).filter(
                    and_(Categoria.nome == data['categoria'], Categoria.evento_id == evento_id)
                ).first()
                
                if not categoria:
                    errors.append(f"Categoria '{data['categoria']}' não encontrada para este evento")
            
            # Verificar se modalidade existe
            if 'modalidade' in data and data['modalidade']:
                modalidade = db.session.query(Modalidade).filter(
                    and_(Modalidade.nome == data['modalidade'], Modalidade.evento_id == evento_id)
                ).first()
                
                if not modalidade:
                    errors.append(f"Modalidade '{data['modalidade']}' não encontrada para este evento")
            
            # Verificar palavras proibidas
            forbidden_found = []
            for field in ['titulo', 'resumo']:
                if field in data and data[field]:
                    text = str(data[field]).lower()
                    for word in self.validation_config['forbidden_words']:
                        if word in text:
                            forbidden_found.append(f"'{word}' em {field}")
            
            if forbidden_found:
                warnings.append(f"Palavras suspeitas encontradas: {', '.join(forbidden_found)}")
            
            # Verificar número de autores
            if 'autores' in data:
                authors = self._parse_authors(data['autores'])
                if len(authors) > self.validation_config['max_authors_count']:
                    errors.append(f"Número de autores ({len(authors)}) excede o máximo permitido ({self.validation_config['max_authors_count']})")
                elif len(authors) == 0:
                    errors.append("Pelo menos um autor deve ser informado")
            
            # Verificar número de palavras-chave
            if 'palavras_chave' in data and data['palavras_chave']:
                keywords = [k.strip() for k in str(data['palavras_chave']).split(',')]
                if len(keywords) > self.validation_config['max_keywords_count']:
                    warnings.append(f"Número de palavras-chave ({len(keywords)}) é alto. Recomendado: até {self.validation_config['max_keywords_count']}")
        
        except Exception as e:
            self.logger.error(f"Erro em validação de regras de negócio: {str(e)}")
            errors.append(f"Erro na validação de regras de negócio: {str(e)}")
        
        return errors, warnings
    
    def _validate_data_integrity(self, data: Dict[str, Any], evento_id: int) -> List[str]:
        """Valida integridade dos dados"""
        errors = []
        
        try:
            # Verificar se evento existe
            evento = db.session.query(Evento).filter(Evento.id == evento_id).first()
            if not evento:
                errors.append(f"Evento com ID {evento_id} não encontrado")
                return errors
            
            # Verificar datas (se aplicável)
            if hasattr(evento, 'data_limite_submissao') and evento.data_limite_submissao:
                if datetime.now() > evento.data_limite_submissao:
                    errors.append("Prazo de submissão já expirou")
            
            # Verificar consistência entre campos relacionados
            if 'categoria' in data and 'modalidade' in data:
                # Verificar se a modalidade é válida para a categoria
                # (implementar lógica específica se necessário)
                pass
        
        except Exception as e:
            self.logger.error(f"Erro em validação de integridade: {str(e)}")
            errors.append(f"Erro na validação de integridade: {str(e)}")
        
        return errors
    
    def _validate_data_consistency(self, data: Dict[str, Any]) -> List[str]:
        """Valida consistência dos dados"""
        warnings = []
        
        # Verificar consistência entre título e resumo
        if 'titulo' in data and 'resumo' in data:
            titulo_words = set(str(data['titulo']).lower().split())
            resumo_words = set(str(data['resumo']).lower().split())
            
            # Verificar se há palavras do título no resumo
            common_words = titulo_words.intersection(resumo_words)
            if len(common_words) < 2:
                warnings.append("Título e resumo parecem inconsistentes (poucas palavras em comum)")
        
        # Verificar consistência entre palavras-chave e conteúdo
        if 'palavras_chave' in data and ('titulo' in data or 'resumo' in data):
            keywords = [k.strip().lower() for k in str(data['palavras_chave']).split(',')]
            content = f"{data.get('titulo', '')} {data.get('resumo', '')}".lower()
            
            missing_keywords = [kw for kw in keywords if kw not in content]
            if len(missing_keywords) > len(keywords) / 2:
                warnings.append("Muitas palavras-chave não aparecem no título ou resumo")
        
        return warnings
    
    def _normalize_submission_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza dados de submissão"""
        normalized = data.copy()
        
        # Normalizar texto
        for field in ['titulo', 'resumo']:
            if field in normalized and normalized[field]:
                # Remover espaços extras
                normalized[field] = ' '.join(str(normalized[field]).split())
                # Capitalizar primeira letra
                normalized[field] = normalized[field].strip().capitalize()
        
        # Normalizar categoria e modalidade
        for field in ['categoria', 'modalidade']:
            if field in normalized and normalized[field]:
                normalized[field] = str(normalized[field]).strip().title()
        
        # Normalizar palavras-chave
        if 'palavras_chave' in normalized and normalized['palavras_chave']:
            keywords = [k.strip().lower() for k in str(normalized['palavras_chave']).split(',')]
            normalized['palavras_chave'] = ', '.join(keywords)
        
        # Normalizar autores
        if 'autores' in normalized:
            normalized['autores'] = self._normalize_authors(normalized['autores'])
        
        return normalized
    
    def _normalize_reviewer_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza dados de revisor"""
        normalized = data.copy()
        
        # Normalizar nome
        if 'nome' in normalized and normalized['nome']:
            normalized['nome'] = str(normalized['nome']).strip().title()
        
        # Normalizar email
        if 'email' in normalized and normalized['email']:
            normalized['email'] = str(normalized['email']).strip().lower()
        
        # Normalizar áreas de interesse
        if 'areas_interesse' in normalized and normalized['areas_interesse']:
            areas = [a.strip().title() for a in str(normalized['areas_interesse']).split(',')]
            normalized['areas_interesse'] = ', '.join(areas)
        
        return normalized
    
    def _parse_authors(self, authors_data: Any) -> List[Dict[str, str]]:
        """Parseia dados de autores"""
        if isinstance(authors_data, list):
            return authors_data
        
        if isinstance(authors_data, str):
            # Tentar parsear string de autores
            authors = []
            for author_str in authors_data.split(';'):
                if ',' in author_str:
                    parts = author_str.split(',')
                    authors.append({
                        'nome': parts[0].strip(),
                        'email': parts[1].strip() if len(parts) > 1 else ''
                    })
                else:
                    authors.append({'nome': author_str.strip(), 'email': ''})
            return authors
        
        return []
    
    def _normalize_authors(self, authors_data: Any) -> List[Dict[str, str]]:
        """Normaliza dados de autores"""
        authors = self._parse_authors(authors_data)
        
        for author in authors:
            if 'nome' in author:
                author['nome'] = str(author['nome']).strip().title()
            if 'email' in author and author['email']:
                author['email'] = str(author['email']).strip().lower()
        
        return authors
    
    def _validate_reviewer_required_fields(self, data: Dict[str, Any]) -> List[str]:
        """Valida campos obrigatórios para revisor"""
        errors = []
        required_fields = ['nome', 'email']
        
        for field in required_fields:
            if field not in data or not data[field] or str(data[field]).strip() == '':
                errors.append(f"Campo obrigatório '{field}' está vazio ou ausente")
        
        return errors
    
    def _validate_reviewer_email(self, data: Dict[str, Any]) -> List[str]:
        """Valida email do revisor"""
        errors = []
        
        if 'email' in data and data['email']:
            try:
                validate_email(data['email'])
            except EmailNotValidError:
                errors.append(f"Email inválido: {data['email']}")
        
        return errors
    
    def _validate_reviewer_preferences(self, data: Dict[str, Any], evento_id: int) -> List[str]:
        """Valida preferências do revisor"""
        errors = []
        
        # Validar áreas de interesse
        if 'areas_interesse' in data and data['areas_interesse']:
            areas = [a.strip() for a in str(data['areas_interesse']).split(',')]
            
            # Verificar se as áreas existem no evento
            categorias_evento = db.session.query(Categoria).filter(
                Categoria.evento_id == evento_id
            ).all()
            
            categorias_nomes = [c.nome for c in categorias_evento]
            
            for area in areas:
                if area not in categorias_nomes:
                    errors.append(f"Área de interesse '{area}' não encontrada nas categorias do evento")
        
        return errors
    
    def _check_reviewer_duplication(self, data: Dict[str, Any], evento_id: int) -> List[str]:
        """Verifica duplicação de revisor"""
        warnings = []
        
        if 'email' in data and data['email']:
            # Verificar se já existe revisor com mesmo email
            from models import Revisor
            existing = db.session.query(Revisor).filter(
                and_(Revisor.email == data['email'], Revisor.evento_id == evento_id)
            ).first()
            
            if existing:
                warnings.append(f"Já existe revisor cadastrado com email {data['email']}")
        
        return warnings
    
    def _validate_dataframe_structure(self, df: pd.DataFrame, data_type: str) -> List[str]:
        """Valida estrutura do DataFrame"""
        errors = []
        
        if df.empty:
            errors.append("Planilha está vazia")
            return errors
        
        # Verificar colunas obrigatórias baseadas no tipo
        if data_type == 'submission':
            required_columns = ['titulo', 'resumo']
        elif data_type == 'reviewer':
            required_columns = ['nome', 'email']
        else:
            errors.append(f"Tipo de dados não reconhecido: {data_type}")
            return errors
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"Colunas obrigatórias ausentes: {', '.join(missing_columns)}")
        
        return errors
    
    def _validate_batch_consistency(self, df: pd.DataFrame, data_type: str, evento_id: int) -> List[str]:
        """Valida consistência do lote"""
        warnings = []
        
        # Verificar duplicatas
        if data_type == 'submission':
            duplicates = df[df.duplicated(subset=['titulo'], keep=False)]
            if not duplicates.empty:
                warnings.append(f"Encontradas {len(duplicates)} submissões com títulos duplicados")
        
        elif data_type == 'reviewer':
            duplicates = df[df.duplicated(subset=['email'], keep=False)]
            if not duplicates.empty:
                warnings.append(f"Encontrados {len(duplicates)} revisores com emails duplicados")
        
        return warnings
    
    def _calculate_validation_score(self, errors: List[str], warnings: List[str]) -> float:
        """Calcula score de validação (0-100)"""
        if errors:
            return 0.0
        
        # Score baseado no número de warnings
        warning_penalty = min(len(warnings) * 10, 50)  # Máximo 50% de penalidade
        return max(100 - warning_penalty, 50)  # Mínimo 50% se não há erros
    
    def get_validation_statistics(self, validation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Gera estatísticas de validação"""
        total = len(validation_results)
        valid = sum(1 for r in validation_results if r['is_valid'])
        with_warnings = sum(1 for r in validation_results if r['warnings'])
        
        avg_score = sum(r['validation_score'] for r in validation_results) / total if total > 0 else 0
        
        return {
            'total_records': total,
            'valid_records': valid,
            'invalid_records': total - valid,
            'records_with_warnings': with_warnings,
            'success_rate': (valid / total * 100) if total > 0 else 0,
            'average_score': avg_score,
            'quality_grade': self._get_quality_grade(avg_score)
        }
    
    def _get_quality_grade(self, score: float) -> str:
        """Retorna nota de qualidade baseada no score"""
        if score >= 90:
            return 'Excelente'
        elif score >= 80:
            return 'Bom'
        elif score >= 70:
            return 'Regular'
        elif score >= 60:
            return 'Ruim'
        else:
            return 'Muito Ruim'