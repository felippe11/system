import pandas as pd
import numpy as np
import uuid
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from io import BytesIO

from extensions import db
from models.submission_system import (
    ImportedSubmission, SpreadsheetMapping, SubmissionCategory
)
from models.review import Submission
from models.user import Usuario
from werkzeug.security import generate_password_hash


class SpreadsheetService:
    """Serviço para importação e processamento de planilhas de submissões."""
    
    def __init__(self, evento_id: int):
        self.evento_id = evento_id
        self.normalization_rules = self._load_normalization_rules()
    
    def _load_normalization_rules(self) -> Dict[str, Dict[str, str]]:
        """Carrega regras de normalização padrão."""
        return {
            "category": {
                "matematica": "Matemática",
                "mat": "Matemática",
                "matematicas": "Matemática",
                "portugues": "Português",
                "port": "Português",
                "lingua portuguesa": "Português",
                "ciencias": "Ciências",
                "ciencia": "Ciências",
                "historia": "História",
                "hist": "História",
                "geografia": "Geografia",
                "geo": "Geografia",
                "fisica": "Física",
                "fis": "Física",
                "quimica": "Química",
                "qui": "Química",
                "biologia": "Biologia",
                "bio": "Biologia"
            },
            "modality": {
                "presencial": "Presencial",
                "online": "Online",
                "hibrido": "Híbrido",
                "ead": "Online",
                "remoto": "Online"
            },
            "type": {
                "artigo": "Artigo",
                "resumo": "Resumo",
                "poster": "Pôster",
                "comunicacao": "Comunicação",
                "relato": "Relato de Experiência"
            }
        }
    
    def analyze_spreadsheet(self, file_content: bytes, filename: str) -> Dict:
        """Analisa a estrutura da planilha e sugere mapeamentos."""
        try:
            # Detectar formato do arquivo
            if filename.endswith('.csv'):
                df = pd.read_csv(BytesIO(file_content), encoding='utf-8', nrows=100)
            else:
                df = pd.read_excel(BytesIO(file_content), nrows=100)
            
            # Analisar colunas
            columns_analysis = self._analyze_columns(df)
            
            # Sugerir mapeamentos
            suggested_mapping = self._suggest_column_mapping(columns_analysis)
            
            # Detectar valores únicos para normalização
            unique_values = self._extract_unique_values(df, suggested_mapping)
            
            return {
                "success": True,
                "total_rows": len(df),
                "columns": list(df.columns),
                "columns_analysis": columns_analysis,
                "suggested_mapping": suggested_mapping,
                "unique_values": unique_values,
                "sample_data": df.head(5).to_dict('records')
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _analyze_columns(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """Analisa cada coluna da planilha."""
        analysis = {}
        
        for column in df.columns:
            col_data = df[column].dropna()
            
            analysis[column] = {
                "data_type": str(col_data.dtype),
                "non_null_count": len(col_data),
                "null_count": df[column].isnull().sum(),
                "unique_count": col_data.nunique(),
                "sample_values": col_data.head(3).tolist(),
                "avg_length": col_data.astype(str).str.len().mean() if len(col_data) > 0 else 0,
                "confidence_scores": self._calculate_field_confidence(column, col_data)
            }
        
        return analysis
    
    def _calculate_field_confidence(self, column_name: str, data: pd.Series) -> Dict[str, float]:
        """Calcula confiança de que a coluna corresponde a cada campo."""
        column_lower = column_name.lower()
        scores = {}
        
        # Padrões para identificação de campos
        patterns = {
            "title": ["titulo", "title", "nome", "trabalho", "artigo"],
            "authors": ["autor", "autores", "author", "authors", "pesquisador"],
            "email": ["email", "e-mail", "mail", "contato"],
            "category": ["categoria", "area", "disciplina", "materia", "category"],
            "modality": ["modalidade", "tipo", "formato", "modality"],
            "keywords": ["palavra", "chave", "keyword", "tag"],
            "abstract": ["resumo", "abstract", "sinopse", "descricao"],
            "institution": ["instituicao", "escola", "universidade", "institution"]
        }
        
        for field, keywords in patterns.items():
            score = 0.0
            
            # Score por nome da coluna
            for keyword in keywords:
                if keyword in column_lower:
                    score += 0.8
                    break
            
            # Score por conteúdo (para alguns campos específicos)
            if field == "email" and len(data) > 0:
                email_pattern = r'^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$'
                email_matches = data.astype(str).str.match(email_pattern).sum()
                if email_matches > 0:
                    score += (email_matches / len(data)) * 0.9
            
            elif field == "title" and len(data) > 0:
                avg_length = data.astype(str).str.len().mean()
                if 20 <= avg_length <= 200:  # Títulos típicos
                    score += 0.3
            
            elif field == "authors" and len(data) > 0:
                # Verificar se contém nomes (múltiplas palavras)
                multi_word = data.astype(str).str.contains(r'\s+').sum()
                if multi_word > len(data) * 0.5:
                    score += 0.4
            
            scores[field] = min(1.0, score)
        
        return scores
    
    def _suggest_column_mapping(self, columns_analysis: Dict) -> Dict[str, str]:
        """Sugere mapeamento automático de colunas."""
        mapping = {}
        used_columns = set()
        
        # Campos obrigatórios primeiro
        required_fields = ["title", "authors", "email", "category"]
        
        for field in required_fields:
            best_column = None
            best_score = 0.0
            
            for column, analysis in columns_analysis.items():
                if column in used_columns:
                    continue
                
                score = analysis["confidence_scores"].get(field, 0.0)
                if score > best_score and score > 0.3:  # Threshold mínimo
                    best_score = score
                    best_column = column
            
            if best_column:
                mapping[field] = best_column
                used_columns.add(best_column)
        
        # Campos opcionais
        optional_fields = ["modality", "keywords", "abstract", "institution"]
        
        for field in optional_fields:
            best_column = None
            best_score = 0.0
            
            for column, analysis in columns_analysis.items():
                if column in used_columns:
                    continue
                
                score = analysis["confidence_scores"].get(field, 0.0)
                if score > best_score and score > 0.2:
                    best_score = score
                    best_column = column
            
            if best_column:
                mapping[field] = best_column
                used_columns.add(best_column)
        
        return mapping
    
    def _extract_unique_values(self, df: pd.DataFrame, mapping: Dict[str, str]) -> Dict[str, List[str]]:
        """Extrai valores únicos das colunas mapeadas para normalização."""
        unique_values = {}
        
        for field, column in mapping.items():
            if column in df.columns:
                values = df[column].dropna().astype(str).str.strip()
                unique_vals = sorted(values.unique().tolist())
                unique_values[field] = unique_vals[:50]  # Limitar para performance
        
        return unique_values
    
    def import_spreadsheet(self, file_content: bytes, filename: str, 
                           column_mapping: Dict[str, str], 
                           normalization_config: Dict[str, Dict[str, str]] = None) -> Dict:
        """Importa planilha completa com mapeamento configurado."""
        try:
            # Carregar planilha completa
            if filename.endswith('.csv'):
                df = pd.read_csv(BytesIO(file_content), encoding='utf-8')
            else:
                df = pd.read_excel(BytesIO(file_content))

            # Normalizar mapeamento: aceitar índices numéricos (ou strings numéricas) e nomes
            normalized_mapping: Dict[str, str] = {}
            for field, value in (column_mapping or {}).items():
                try:
                    if isinstance(value, int) or (isinstance(value, str) and str(value).isdigit()):
                        idx = int(value)
                        if 0 <= idx < len(df.columns):
                            normalized_mapping[field] = str(df.columns[idx])
                    else:
                        normalized_mapping[field] = str(value)
                except Exception:
                    continue

            # Gerar ID do lote
            batch_id = str(uuid.uuid4())
            
            # Processar em chunks para otimização
            chunk_size = 1000
            total_imported = 0
            errors = []
            
            for i in range(0, len(df), chunk_size):
                chunk = df.iloc[i:i+chunk_size]
                chunk_result = self._process_chunk(
                    chunk, normalized_mapping, batch_id, 
                    normalization_config or self.normalization_rules
                )
                total_imported += chunk_result["imported"]
                errors.extend(chunk_result["errors"])
            
            # Salvar configuração de mapeamento
            self._save_mapping_config(normalized_mapping, normalization_config)
            
            # Retornar chaves compatíveis com o frontend atual
            return {
                "success": True,
                "batch_id": batch_id,
                "total_rows": len(df),
                # chaves antigas usadas pelo template
                "imported_rows": total_imported,
                "warning_rows": 0,
                "error_rows": len(errors),
                # chaves mais descritivas (retrocompatibilidade)
                "imported_count": total_imported,
                "error_count": len(errors),
                "errors": errors[:10],  # Primeiros 10 erros
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _process_chunk(self, chunk: pd.DataFrame, mapping: Dict[str, str], 
                      batch_id: str, normalization_rules: Dict) -> Dict:
        """Processa um chunk da planilha."""
        imported = 0
        errors = []
        
        submissions_to_add = []
        
        for index, row in chunk.iterrows():
            try:
                # Extrair dados mapeados
                submission_data = self._extract_submission_data(row, mapping, normalization_rules)
                
                # Validar dados obrigatórios
                if not submission_data.get("title"):
                    errors.append(f"Linha {index + 1}: Título obrigatório")
                    continue
                
                # Criar objeto ImportedSubmission
                imported_submission = ImportedSubmission(
                    evento_id=self.evento_id,
                    title=submission_data["title"],
                    authors=submission_data.get("authors") or submission_data.get("author"),
                    author_email=submission_data.get("email"),
                    category=submission_data.get("category"),
                    modality=submission_data.get("modality"),
                    submission_type=submission_data.get("type"),
                    keywords=submission_data.get("keywords"),
                    abstract=submission_data.get("abstract"),
                    import_batch_id=batch_id,
                    original_row_data=row.to_dict(),
                    mapping_config=mapping
                )
                
                submissions_to_add.append(imported_submission)
                imported += 1
                
            except Exception as e:
                errors.append(f"Linha {index + 1}: {str(e)}")
        
        # Inserção em lote para performance
        if submissions_to_add:
            db.session.bulk_save_objects(submissions_to_add)
            db.session.commit()
        
        return {"imported": imported, "errors": errors}
    
    def _extract_submission_data(self, row: pd.Series, mapping: Dict[str, str], 
                               normalization_rules: Dict) -> Dict[str, str]:
        """Extrai e normaliza dados de uma linha da planilha."""
        data = {}
        
        for field, column in mapping.items():
            if column in row.index and pd.notna(row[column]):
                value = str(row[column]).strip()
                
                # Aplicar normalização
                if field in normalization_rules:
                    value = self._normalize_value(value, normalization_rules[field])
                
                data[field] = value
        
        return data
    
    def _normalize_value(self, value: str, rules: Dict[str, str]) -> str:
        """Normaliza um valor usando as regras fornecidas."""
        value_lower = value.lower().strip()
        
        # Busca exata primeiro
        if value_lower in rules:
            return rules[value_lower]
        
        # Busca por similaridade
        for pattern, normalized in rules.items():
            if pattern in value_lower or value_lower in pattern:
                return normalized
        
        # Retorna valor original se não encontrar regra
        return value.title()  # Capitalizar primeira letra
    
    def _save_mapping_config(self, column_mapping: Dict[str, str], 
                           normalization_config: Dict = None):
        """Salva configuração de mapeamento para reutilização."""
        mapping = SpreadsheetMapping(
            evento_id=self.evento_id,
            name=f"Importação {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            column_mappings=column_mapping,
            normalization_rules=normalization_config or {},
            created_by=1  # TODO: Obter usuário atual
        )
        
        db.session.add(mapping)
        db.session.commit()
    
    def process_imported_submissions(self, batch_id: str = None) -> Dict:
        """Processa submissões importadas criando objetos Submission."""
        try:
            query = ImportedSubmission.query.filter_by(
                evento_id=self.evento_id,
                processed=False
            )
            
            if batch_id:
                query = query.filter_by(import_batch_id=batch_id)
            
            imported_submissions = query.all()
            
            processed = 0
            errors = []
            
            for imported in imported_submissions:
                try:
                    # Criar submissão real
                    submission = self._create_submission_from_imported(imported)
                    
                    if submission:
                        imported.mark_processed(submission.id)
                        processed += 1
                    
                except Exception as e:
                    imported.mark_processed(errors=[str(e)])
                    errors.append(f"Submissão {imported.id}: {str(e)}")
            
            db.session.commit()
            
            return {
                "success": True,
                "processed_count": processed,
                "created_submissions": processed,
                "error_count": len(errors),
                "errors": errors[:10],
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_submission_from_imported(self, imported: ImportedSubmission) -> Optional[Submission]:
        """Cria objeto Submission a partir de ImportedSubmission."""
        # Gerar código de acesso
        access_code = str(uuid.uuid4())[:8].upper()
        
        # Criar submissão
        submission = Submission(
            title=imported.title,
            abstract=imported.abstract,
            evento_id=imported.evento_id,
            status="submitted",
            code_hash=generate_password_hash(access_code),
            attributes={
                "authors": imported.authors,
                "author_email": imported.author_email,
                "category": imported.category,
                "modality": imported.modality,
                "submission_type": imported.submission_type,
                "keywords": imported.keywords,
                "imported_from_batch": imported.import_batch_id
            }
        )
        
        db.session.add(submission)
        db.session.flush()  # Para obter o ID
        
        return submission
    
    def get_import_stats(self, batch_id: str = None) -> Dict:
        """Retorna estatísticas de importação."""
        query = ImportedSubmission.query.filter_by(evento_id=self.evento_id)
        
        if batch_id:
            query = query.filter_by(import_batch_id=batch_id)
        
        total = query.count()
        processed = query.filter_by(processed=True).count()
        pending = total - processed
        
        # Erros
        with_errors = query.filter(
            ImportedSubmission.processing_errors != None,
            ImportedSubmission.processing_errors != []
        ).count()
        
        return {
            "total_imported": total,
            "processed": processed,
            "pending": pending,
            "with_errors": with_errors,
            "success_rate": round((processed / total * 100) if total > 0 else 0, 2)
        }
    
    def get_saved_mappings(self) -> List[Dict]:
        """Retorna mapeamentos salvos para o evento."""
        mappings = SpreadsheetMapping.query.filter_by(
            evento_id=self.evento_id,
            active=True
        ).order_by(SpreadsheetMapping.created_at.desc()).all()
        
        return [{
            "id": m.id,
            "name": m.name,
            "column_mappings": m.column_mappings,
            "normalization_rules": m.normalization_rules,
            "is_default": m.is_default,
            "created_at": m.created_at.isoformat()
        } for m in mappings]
    
    def generate_template(self, mapping_id: int = None) -> bytes:
        """Gera template de planilha baseado em mapeamento salvo."""
        if mapping_id:
            mapping = SpreadsheetMapping.query.get(mapping_id)
            if mapping:
                columns = list(mapping.column_mappings.values())
            else:
                columns = self._get_default_columns()
        else:
            columns = self._get_default_columns()
        
        # Criar DataFrame com colunas e exemplos
        examples = {
            "Título": "Exemplo de Título do Trabalho",
            "Autores": "João Silva, Maria Santos",
            "Email": "autor@exemplo.com",
            "Categoria": "Matemática",
            "Modalidade": "Presencial",
            "Palavras-chave": "educação, matemática, ensino",
            "Resumo": "Este é um exemplo de resumo do trabalho..."
        }
        
        data = {col: [examples.get(col, "")] for col in columns}
        df = pd.DataFrame(data)
        
        # Converter para Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Submissões')
        
        return output.getvalue()
    
    def _get_default_columns(self) -> List[str]:
        """Retorna colunas padrão para template."""
        return [
            "Título", "Autores", "Email", "Categoria", 
            "Modalidade", "Palavras-chave", "Resumo"
        ]



