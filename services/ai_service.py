"""
Serviço de Inteligência Artificial para Geração de Texto
Usando Hugging Face Text Generation Inference API
"""

import requests
import json
import logging
from typing import Dict, List, Optional, Any
from flask import current_app
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.hf_api_key = os.getenv('HUGGINGFACE_API_KEY')
        self.hf_model_id = os.getenv('HUGGINGFACE_MODEL_ID', 'microsoft/DialoGPT-medium')
        self.hf_api_url = os.getenv('HUGGINGFACE_API_URL', 'https://api-inference.huggingface.co/models')
        self.tgi_endpoint = os.getenv('TGI_ENDPOINT', 'http://localhost:3000')
        self.use_tgi = os.getenv('USE_TGI', 'false').lower() == 'true'
        
        # Configurações de fallback
        self.fallback_templates = self._load_fallback_templates()
        
    def _load_fallback_templates(self) -> Dict[str, Any]:
        """Carrega templates de fallback para quando a IA não estiver disponível"""
        return {
            'certificate_templates': {
                'workshop': {
                    'title': 'Certificado de Participação',
                    'text': 'Certificamos que {NOME_PARTICIPANTE} participou do workshop "{NOME_EVENTO}", desenvolvendo competências práticas e teóricas na área abordada, com carga horária de {CARGA_HORARIA} horas.',
                    'variables': ['NOME_PARTICIPANTE', 'NOME_EVENTO', 'CARGA_HORARIA']
                },
                'curso': {
                    'title': 'Certificado de Conclusão',
                    'text': 'Certificamos que {NOME_PARTICIPANTE} concluiu com êxito o curso "{NOME_EVENTO}", demonstrando dedicação e aproveitamento nas atividades propostas, totalizando {CARGA_HORARIA} horas de estudo.',
                    'variables': ['NOME_PARTICIPANTE', 'NOME_EVENTO', 'CARGA_HORARIA']
                },
                'palestra': {
                    'title': 'Certificado de Participação',
                    'text': 'Certificamos que {NOME_PARTICIPANTE} participou da palestra "{NOME_EVENTO}", ampliando seus conhecimentos sobre o tema apresentado.',
                    'variables': ['NOME_PARTICIPANTE', 'NOME_EVENTO']
                },
                'seminario': {
                    'title': 'Certificado de Seminário',
                    'text': 'Certificamos que {NOME_PARTICIPANTE} participou do seminário "{NOME_EVENTO}", contribuindo para o debate e troca de conhecimentos na área.',
                    'variables': ['NOME_PARTICIPANTE', 'NOME_EVENTO', 'CARGA_HORARIA']
                }
            },
            'declaration_templates': {
                'attendance': {
                    'title': 'Declaração de Comparecimento',
                    'text': 'Declaramos que {NOME_PARTICIPANTE} compareceu ao evento "{NOME_EVENTO}" realizado em {DATA_EVENTO}, com duração de {CARGA_HORARIA} horas.',
                    'variables': ['NOME_PARTICIPANTE', 'NOME_EVENTO', 'DATA_EVENTO', 'CARGA_HORARIA']
                }
            }
        }

    def _make_tgi_request(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Faz requisição para TGI (Text Generation Inference)"""
        try:
            url = f"{self.tgi_endpoint}/v1/chat/completions"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.hf_api_key}' if self.hf_api_key else 'Bearer -'
            }
            
            payload = {
                'model': 'tgi',
                'messages': messages,
                'max_tokens': kwargs.get('max_tokens', 500),
                'temperature': kwargs.get('temperature', 0.7),
                'stream': kwargs.get('stream', False)
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Erro na requisição TGI: {str(e)}")
            raise

    def _make_hf_request(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Faz requisição para Hugging Face Inference API"""
        try:
            url = f"{self.hf_api_url}/{self.hf_model_id}"
            headers = {
                'Authorization': f'Bearer {self.hf_api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'inputs': prompt,
                'parameters': {
                    'max_new_tokens': kwargs.get('max_tokens', 200),
                    'temperature': kwargs.get('temperature', 0.7),
                    'return_full_text': False,
                    'do_sample': True
                }
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Erro na requisição Hugging Face: {str(e)}")
            raise

    def gerar_texto_certificado(self, tipo_evento: str, nome_evento: str, contexto: str = "") -> Dict[str, Any]:
        """
        Gera texto para certificados usando IA
        
        Args:
            tipo_evento: Tipo do evento (workshop, curso, palestra, etc.)
            nome_evento: Nome do evento
            contexto: Contexto adicional para personalização
            
        Returns:
            Dict com o texto gerado e metadados
        """
        try:
            if self.use_tgi and self.tgi_endpoint:
                return self._gerar_com_tgi(tipo_evento, nome_evento, contexto)
            elif self.hf_api_key:
                return self._gerar_com_hf(tipo_evento, nome_evento, contexto)
            else:
                return self._gerar_fallback(tipo_evento, nome_evento, contexto)
                
        except Exception as e:
            logger.error(f"Erro ao gerar texto de certificado: {str(e)}")
            return self._gerar_fallback(tipo_evento, nome_evento, contexto)

    def _gerar_com_tgi(self, tipo_evento: str, nome_evento: str, contexto: str) -> Dict[str, Any]:
        """Gera texto usando TGI"""
        messages = [
            {
                "role": "system",
                "content": "Você é um assistente especializado em criar textos para certificados e declarações acadêmicas. Seja formal, claro e profissional."
            },
            {
                "role": "user",
                "content": f"Crie um texto para um certificado de {tipo_evento} chamado '{nome_evento}'. {contexto}. Use variáveis como {{NOME_PARTICIPANTE}}, {{NOME_EVENTO}}, {{CARGA_HORARIA}} quando apropriado."
            }
        ]
        
        response = self._make_tgi_request(messages, max_tokens=300, temperature=0.7)
        
        if 'choices' in response and len(response['choices']) > 0:
            texto_gerado = response['choices'][0]['message']['content']
            return {
                'success': True,
                'texto': texto_gerado,
                'modelo': 'TGI',
                'timestamp': datetime.now().isoformat()
            }
        else:
            raise Exception("Resposta inválida da API TGI")

    def _gerar_com_hf(self, tipo_evento: str, nome_evento: str, contexto: str) -> Dict[str, Any]:
        """Gera texto usando Hugging Face Inference API"""
        prompt = f"Gere um texto para certificado de {tipo_evento} '{nome_evento}'. {contexto}. Use variáveis como {{NOME_PARTICIPANTE}}, {{NOME_EVENTO}}, {{CARGA_HORARIA}}."
        
        response = self._make_hf_request(prompt, max_tokens=200, temperature=0.7)
        
        if isinstance(response, list) and len(response) > 0:
            texto_gerado = response[0].get('generated_text', '')
            return {
                'success': True,
                'texto': texto_gerado,
                'modelo': 'Hugging Face',
                'timestamp': datetime.now().isoformat()
            }
        else:
            raise Exception("Resposta inválida da API Hugging Face")

    def _gerar_fallback(self, tipo_evento: str, nome_evento: str, contexto: str) -> Dict[str, Any]:
        """Gera texto usando templates de fallback"""
        templates = self.fallback_templates['certificate_templates']
        
        if tipo_evento.lower() in templates:
            template = templates[tipo_evento.lower()]
            texto = template['text'].replace('{NOME_EVENTO}', nome_evento)
        else:
            # Template genérico
            texto = f"Certificamos que {{NOME_PARTICIPANTE}} participou do {tipo_evento} '{nome_evento}', demonstrando interesse e dedicação nas atividades propostas."
        
        return {
            'success': True,
            'texto': texto,
            'modelo': 'Template Local',
            'timestamp': datetime.now().isoformat(),
            'fallback': True
        }

    def melhorar_texto(self, texto_original: str, objetivo: str = 'melhorar') -> Dict[str, Any]:
        """
        Melhora um texto existente usando IA
        
        Args:
            texto_original: Texto a ser melhorado
            objetivo: Objetivo da melhoria (melhorar, formalizar, simplificar)
            
        Returns:
            Dict com o texto melhorado
        """
        try:
            if self.use_tgi and self.tgi_endpoint:
                return self._melhorar_com_tgi(texto_original, objetivo)
            elif self.hf_api_key:
                return self._melhorar_com_hf(texto_original, objetivo)
            else:
                return self._melhorar_fallback(texto_original, objetivo)
                
        except Exception as e:
            logger.error(f"Erro ao melhorar texto: {str(e)}")
            return self._melhorar_fallback(texto_original, objetivo)

    def _melhorar_com_tgi(self, texto_original: str, objetivo: str) -> Dict[str, Any]:
        """Melhora texto usando TGI"""
        objetivos = {
            'melhorar': 'melhore a qualidade e clareza do texto',
            'formalizar': 'torne o texto mais formal e acadêmico',
            'simplificar': 'simplifique o texto mantendo o significado'
        }
        
        instrucao = objetivos.get(objetivo, 'melhore o texto')
        
        messages = [
            {
                "role": "system",
                "content": "Você é um especialista em redação acadêmica e textos formais. Melhore textos mantendo o tom apropriado para documentos oficiais."
            },
            {
                "role": "user",
                "content": f"{instrucao} do seguinte texto: '{texto_original}'"
            }
        ]
        
        response = self._make_tgi_request(messages, max_tokens=400, temperature=0.5)
        
        if 'choices' in response and len(response['choices']) > 0:
            texto_melhorado = response['choices'][0]['message']['content']
            return {
                'success': True,
                'texto_original': texto_original,
                'texto_melhorado': texto_melhorado,
                'objetivo': objetivo,
                'modelo': 'TGI',
                'timestamp': datetime.now().isoformat()
            }
        else:
            raise Exception("Resposta inválida da API TGI")

    def _melhorar_com_hf(self, texto_original: str, objetivo: str) -> Dict[str, Any]:
        """Melhora texto usando Hugging Face"""
        prompt = f"Melhore o seguinte texto para certificado: '{texto_original}'. Torne-o mais {objetivo}."
        
        response = self._make_hf_request(prompt, max_tokens=300, temperature=0.5)
        
        if isinstance(response, list) and len(response) > 0:
            texto_melhorado = response[0].get('generated_text', '')
            return {
                'success': True,
                'texto_original': texto_original,
                'texto_melhorado': texto_melhorado,
                'objetivo': objetivo,
                'modelo': 'Hugging Face',
                'timestamp': datetime.now().isoformat()
            }
        else:
            raise Exception("Resposta inválida da API Hugging Face")

    def _melhorar_fallback(self, texto_original: str, objetivo: str) -> Dict[str, Any]:
        """Melhora texto usando regras simples"""
        # Melhorias básicas baseadas em regras
        texto_melhorado = texto_original
        
        if objetivo == 'formalizar':
            texto_melhorado = texto_melhorado.replace('participou', 'compareceu')
            texto_melhorado = texto_melhorado.replace('fez', 'realizou')
            texto_melhorado = texto_melhorado.replace('teve', 'obteve')
        elif objetivo == 'simplificar':
            texto_melhorado = texto_melhorado.replace('demonstrando', 'mostrando')
            texto_melhorado = texto_melhorado.replace('desenvolvendo', 'aprendendo')
        
        return {
            'success': True,
            'texto_original': texto_original,
            'texto_melhorado': texto_melhorado,
            'objetivo': objetivo,
            'modelo': 'Template Local',
            'timestamp': datetime.now().isoformat(),
            'fallback': True
        }

    def gerar_sugestoes_variaveis(self, contexto: str) -> Dict[str, Any]:
        """
        Gera sugestões de variáveis dinâmicas baseadas no contexto
        
        Args:
            contexto: Contexto do certificado ou declaração
            
        Returns:
            Dict com sugestões de variáveis
        """
        try:
            if self.use_tgi and self.tgi_endpoint:
                return self._sugestoes_com_tgi(contexto)
            elif self.hf_api_key:
                return self._sugestoes_com_hf(contexto)
            else:
                return self._sugestoes_fallback(contexto)
                
        except Exception as e:
            logger.error(f"Erro ao gerar sugestões: {str(e)}")
            return self._sugestoes_fallback(contexto)

    def _sugestoes_com_tgi(self, contexto: str) -> Dict[str, Any]:
        """Gera sugestões usando TGI"""
        messages = [
            {
                "role": "system",
                "content": "Você é um especialista em sistemas de certificação. Sugira variáveis dinâmicas apropriadas para o contexto fornecido."
            },
            {
                "role": "user",
                "content": f"Para o contexto: '{contexto}', sugira variáveis dinâmicas úteis para certificados. Formato: NOME_VARIAVEL - Descrição"
            }
        ]
        
        response = self._make_tgi_request(messages, max_tokens=300, temperature=0.6)
        
        if 'choices' in response and len(response['choices']) > 0:
            sugestoes_texto = response['choices'][0]['message']['content']
            sugestoes = self._parse_sugestoes(sugestoes_texto)
            return {
                'success': True,
                'sugestoes': sugestoes,
                'modelo': 'TGI',
                'timestamp': datetime.now().isoformat()
            }
        else:
            raise Exception("Resposta inválida da API TGI")

    def _sugestoes_com_hf(self, contexto: str) -> Dict[str, Any]:
        """Gera sugestões usando Hugging Face"""
        prompt = f"Sugira variáveis dinâmicas para certificados baseadas no contexto: '{contexto}'. Formato: NOME_VARIAVEL - Descrição"
        
        response = self._make_hf_request(prompt, max_tokens=200, temperature=0.6)
        
        if isinstance(response, list) and len(response) > 0:
            sugestoes_texto = response[0].get('generated_text', '')
            sugestoes = self._parse_sugestoes(sugestoes_texto)
            return {
                'success': True,
                'sugestoes': sugestoes,
                'modelo': 'Hugging Face',
                'timestamp': datetime.now().isoformat()
            }
        else:
            raise Exception("Resposta inválida da API Hugging Face")

    def _sugestoes_fallback(self, contexto: str) -> Dict[str, Any]:
        """Gera sugestões usando templates padrão"""
        sugestoes_padrao = [
            {'nome': 'NOME_PARTICIPANTE', 'descricao': 'Nome completo do participante'},
            {'nome': 'NOME_EVENTO', 'descricao': 'Nome do evento ou atividade'},
            {'nome': 'CARGA_HORARIA', 'descricao': 'Carga horária total do evento'},
            {'nome': 'DATA_EVENTO', 'descricao': 'Data de realização do evento'},
            {'nome': 'DATA_EMISSAO', 'descricao': 'Data de emissão do certificado'},
            {'nome': 'NOME_INSTITUICAO', 'descricao': 'Nome da instituição organizadora'},
            {'nome': 'COORDENADOR', 'descricao': 'Nome do coordenador do evento'},
            {'nome': 'LOCAL_EVENTO', 'descricao': 'Local onde o evento foi realizado'}
        ]
        
        return {
            'success': True,
            'sugestoes': sugestoes_padrao,
            'modelo': 'Template Local',
            'timestamp': datetime.now().isoformat(),
            'fallback': True
        }

    def _parse_sugestoes(self, texto: str) -> List[Dict[str, str]]:
        """Parseia o texto de sugestões em formato estruturado"""
        sugestoes = []
        linhas = texto.split('\n')
        
        for linha in linhas:
            if ' - ' in linha or ':' in linha:
                partes = linha.split(' - ' if ' - ' in linha else ':')
                if len(partes) >= 2:
                    nome = partes[0].strip().replace('{', '').replace('}', '')
                    descricao = partes[1].strip()
                    if nome and descricao:
                        sugestoes.append({
                            'nome': nome,
                            'descricao': descricao
                        })
        
        return sugestoes if sugestoes else self._sugestoes_fallback('')['sugestoes']

    def verificar_qualidade_texto(self, texto: str) -> Dict[str, Any]:
        """
        Verifica a qualidade de um texto e sugere melhorias
        
        Args:
            texto: Texto a ser analisado
            
        Returns:
            Dict com análise de qualidade
        """
        try:
            if self.use_tgi and self.tgi_endpoint:
                return self._verificar_com_tgi(texto)
            elif self.hf_api_key:
                return self._verificar_com_hf(texto)
            else:
                return self._verificar_fallback(texto)
                
        except Exception as e:
            logger.error(f"Erro ao verificar qualidade: {str(e)}")
            return self._verificar_fallback(texto)

    def _verificar_com_tgi(self, texto: str) -> Dict[str, Any]:
        """Verifica qualidade usando TGI"""
        messages = [
            {
                "role": "system",
                "content": "Você é um especialista em redação acadêmica. Analise a qualidade do texto e sugira melhorias específicas."
            },
            {
                "role": "user",
                "content": f"Analise a qualidade deste texto para certificado: '{texto}'. Identifique problemas e sugira melhorias."
            }
        ]
        
        response = self._make_tgi_request(messages, max_tokens=400, temperature=0.3)
        
        if 'choices' in response and len(response['choices']) > 0:
            analise = response['choices'][0]['message']['content']
            return {
                'success': True,
                'texto': texto,
                'analise': analise,
                'modelo': 'TGI',
                'timestamp': datetime.now().isoformat()
            }
        else:
            raise Exception("Resposta inválida da API TGI")

    def _verificar_com_hf(self, texto: str) -> Dict[str, Any]:
        """Verifica qualidade usando Hugging Face"""
        prompt = f"Analise a qualidade deste texto para certificado: '{texto}'. Identifique problemas e sugira melhorias."
        
        response = self._make_hf_request(prompt, max_tokens=300, temperature=0.3)
        
        if isinstance(response, list) and len(response) > 0:
            analise = response[0].get('generated_text', '')
            return {
                'success': True,
                'texto': texto,
                'analise': analise,
                'modelo': 'Hugging Face',
                'timestamp': datetime.now().isoformat()
            }
        else:
            raise Exception("Resposta inválida da API Hugging Face")

    def _verificar_fallback(self, texto: str) -> Dict[str, Any]:
        """Verifica qualidade usando regras simples"""
        problemas = []
        sugestoes = []
        
        # Verificações básicas
        if len(texto) < 50:
            problemas.append("Texto muito curto")
            sugestoes.append("Adicione mais detalhes sobre o evento")
        
        if '{' not in texto and '}' not in texto:
            problemas.append("Nenhuma variável dinâmica encontrada")
            sugestoes.append("Considere adicionar variáveis como {NOME_PARTICIPANTE}")
        
        if texto.count('.') < 2:
            problemas.append("Poucos pontos finais")
            sugestoes.append("Estruture melhor as frases")
        
        analise = f"Problemas encontrados: {', '.join(problemas) if problemas else 'Nenhum'}. Sugestões: {'; '.join(sugestoes) if sugestoes else 'Texto adequado'}."
        
        return {
            'success': True,
            'texto': texto,
            'analise': analise,
            'modelo': 'Template Local',
            'timestamp': datetime.now().isoformat(),
            'fallback': True
        }

    def get_status(self) -> Dict[str, Any]:
        """Retorna o status dos serviços de IA"""
        status = {
            'tgi': {
                'disponivel': False,
                'endpoint': self.tgi_endpoint,
                'configurado': bool(self.tgi_endpoint and self.tgi_endpoint != 'http://localhost:3000')
            },
            'huggingface': {
                'disponivel': False,
                'api_key': bool(self.hf_api_key),
                'modelo': self.hf_model_id,
                'configurado': bool(self.hf_api_key)
            },
            'fallback': {
                'disponivel': True,
                'descricao': 'Templates locais e regras básicas'
            }
        }
        
        # Testar conectividade
        try:
            if self.use_tgi and self.tgi_endpoint:
                test_response = self._make_tgi_request([
                    {"role": "user", "content": "test"}
                ], max_tokens=10)
                status['tgi']['disponivel'] = True
        except:
            pass
        
        try:
            if self.hf_api_key:
                test_response = self._make_hf_request("test", max_tokens=10)
                status['huggingface']['disponivel'] = True
        except:
            pass
        
        return status

# Instância global do serviço
ai_service = AIService()