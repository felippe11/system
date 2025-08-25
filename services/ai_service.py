import requests
import json
from typing import Dict, List, Optional
import os
from flask import current_app

class AIService:
    """
    Serviço de IA para geração e melhoria de textos usando APIs gratuitas.
    Utiliza principalmente Hugging Face Inference API que oferece modelos gratuitos.
    """
    
    def __init__(self):
        self.hf_api_key = os.getenv('HUGGINGFACE_API_KEY', '<REMOVED>')
        self.base_url = "https://api-inference.huggingface.co/models"
        self.headers = {
            "Authorization": f"Bearer {self.hf_api_key}" if self.hf_api_key else "",
            "Content-Type": "application/json"
        }
    
    def gerar_texto_certificado(self, tipo_evento: str, nome_evento: str, contexto: str = "") -> Dict:
        """
        Gera texto para certificados usando IA.
        
        Args:
            tipo_evento: Tipo do evento (workshop, palestra, curso, etc.)
            nome_evento: Nome do evento
            contexto: Contexto adicional sobre o evento
            
        Returns:
            Dict com o texto gerado e sugestões
        """
        try:
            prompt = self._criar_prompt_certificado(tipo_evento, nome_evento, contexto)
            
            # Usar modelo de geração de texto gratuito
            model = "microsoft/DialoGPT-medium"
            response = self._fazer_requisicao_hf(model, prompt)
            
            if response and 'generated_text' in response[0]:
                texto_gerado = response[0]['generated_text']
                return {
                    'success': True,
                    'texto': self._limpar_texto_gerado(texto_gerado),
                    'sugestoes': self._gerar_sugestoes_certificado(tipo_evento)
                }
            else:
                return self._fallback_texto_certificado(tipo_evento, nome_evento)
                
        except Exception as e:
            current_app.logger.error(f"Erro na geração de texto: {str(e)}")
            return self._fallback_texto_certificado(tipo_evento, nome_evento)
    
    def melhorar_texto(self, texto_original: str, objetivo: str = "melhorar") -> Dict:
        """
        Melhora um texto existente usando IA.
        
        Args:
            texto_original: Texto a ser melhorado
            objetivo: Objetivo da melhoria (melhorar, formalizar, simplificar)
            
        Returns:
            Dict com o texto melhorado
        """
        try:
            prompt = self._criar_prompt_melhoria(texto_original, objetivo)
            
            # Usar modelo de paráfrase/melhoria
            model = "tuner007/pegasus_paraphrase"
            response = self._fazer_requisicao_hf(model, texto_original)
            
            if response and len(response) > 0:
                texto_melhorado = response[0].get('generated_text', texto_original)
                return {
                    'success': True,
                    'texto_original': texto_original,
                    'texto_melhorado': self._limpar_texto_gerado(texto_melhorado),
                    'melhorias_aplicadas': self._identificar_melhorias(texto_original, texto_melhorado)
                }
            else:
                return self._fallback_melhoria_texto(texto_original, objetivo)
                
        except Exception as e:
            current_app.logger.error(f"Erro na melhoria de texto: {str(e)}")
            return self._fallback_melhoria_texto(texto_original, objetivo)
    
    def gerar_sugestoes_variaveis(self, contexto: str) -> List[Dict]:
        """
        Gera sugestões de variáveis dinâmicas baseadas no contexto.
        
        Args:
            contexto: Contexto do evento ou certificado
            
        Returns:
            Lista de sugestões de variáveis
        """
        try:
            # Análise básica do contexto para sugerir variáveis
            sugestoes = [
                {
                    'variavel': '{NOME_PARTICIPANTE}',
                    'descricao': 'Nome completo do participante',
                    'exemplo': 'João da Silva',
                    'categoria': 'participante'
                },
                {
                    'variavel': '{NOME_EVENTO}',
                    'descricao': 'Nome do evento',
                    'exemplo': contexto[:50] if contexto else 'Workshop de Tecnologia',
                    'categoria': 'evento'
                },
                {
                    'variavel': '{CARGA_HORARIA_TOTAL}',
                    'descricao': 'Carga horária total participada',
                    'exemplo': '20 horas',
                    'categoria': 'participacao'
                },
                {
                    'variavel': '{DATA_EVENTO}',
                    'descricao': 'Data de realização do evento',
                    'exemplo': '15 de Janeiro de 2024',
                    'categoria': 'evento'
                },
                {
                    'variavel': '{LISTA_ATIVIDADES}',
                    'descricao': 'Lista das atividades participadas',
                    'exemplo': 'Palestra 1, Workshop 2, Mesa Redonda 3',
                    'categoria': 'participacao'
                }
            ]
            
            # Adicionar sugestões específicas baseadas no contexto
            if 'workshop' in contexto.lower():
                sugestoes.append({
                    'variavel': '{HABILIDADES_DESENVOLVIDAS}',
                    'descricao': 'Habilidades desenvolvidas no workshop',
                    'exemplo': 'Programação Python, Análise de Dados',
                    'categoria': 'aprendizado'
                })
            
            if 'curso' in contexto.lower():
                sugestoes.append({
                    'variavel': '{NOTA_FINAL}',
                    'descricao': 'Nota final obtida no curso',
                    'exemplo': '9.5',
                    'categoria': 'avaliacao'
                })
            
            return sugestoes
            
        except Exception as e:
            current_app.logger.error(f"Erro na geração de sugestões: {str(e)}")
            return []
    
    def verificar_qualidade_texto(self, texto: str) -> Dict:
        """
        Verifica a qualidade de um texto e sugere melhorias.
        
        Args:
            texto: Texto a ser analisado
            
        Returns:
            Dict com análise de qualidade
        """
        try:
            analise = {
                'pontuacao_qualidade': 0,
                'problemas_encontrados': [],
                'sugestoes_melhoria': [],
                'metricas': {
                    'palavras': len(texto.split()),
                    'caracteres': len(texto),
                    'frases': texto.count('.') + texto.count('!') + texto.count('?')
                }
            }
            
            # Verificações básicas de qualidade
            if len(texto) < 50:
                analise['problemas_encontrados'].append('Texto muito curto')
                analise['sugestoes_melhoria'].append('Considere adicionar mais detalhes')
            
            if not any(char.isupper() for char in texto):
                analise['problemas_encontrados'].append('Falta de maiúsculas')
                analise['sugestoes_melhoria'].append('Verifique a capitalização')
            
            if texto.count('.') == 0:
                analise['problemas_encontrados'].append('Falta de pontuação')
                analise['sugestoes_melhoria'].append('Adicione pontuação adequada')
            
            # Calcular pontuação de qualidade
            pontuacao = 100
            pontuacao -= len(analise['problemas_encontrados']) * 20
            analise['pontuacao_qualidade'] = max(0, pontuacao)
            
            return analise
            
        except Exception as e:
            current_app.logger.error(f"Erro na verificação de qualidade: {str(e)}")
            return {'pontuacao_qualidade': 0, 'problemas_encontrados': ['Erro na análise']}
    
    def _fazer_requisicao_hf(self, model: str, input_text: str) -> Optional[List[Dict]]:
        """
        Faz requisição para a API do Hugging Face.
        """
        try:
            url = f"{self.base_url}/{model}"
            payload = {"inputs": input_text}
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                current_app.logger.warning(f"API HF retornou status {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Erro na requisição HF: {str(e)}")
            return None
    
    def _criar_prompt_certificado(self, tipo_evento: str, nome_evento: str, contexto: str) -> str:
        """
        Cria prompt para geração de texto de certificado.
        """
        return f"""
        Gere um texto formal e elegante para um certificado de {tipo_evento}.
        Nome do evento: {nome_evento}
        Contexto: {contexto}
        
        O texto deve:
        - Ser formal e respeitoso
        - Reconhecer a participação do indivíduo
        - Mencionar as competências desenvolvidas
        - Ter entre 100-200 palavras
        
        Texto do certificado:
        """
    
    def _criar_prompt_melhoria(self, texto: str, objetivo: str) -> str:
        """
        Cria prompt para melhoria de texto.
        """
        objetivos_map = {
            'melhorar': 'mais claro e elegante',
            'formalizar': 'mais formal e profissional',
            'simplificar': 'mais simples e direto'
        }
        
        objetivo_desc = objetivos_map.get(objetivo, 'melhor')
        
        return f"""
        Reescreva o seguinte texto para torná-lo {objetivo_desc}:
        
        Texto original: {texto}
        
        Texto melhorado:
        """
    
    def _limpar_texto_gerado(self, texto: str) -> str:
        """
        Limpa e formata o texto gerado pela IA.
        """
        # Remover quebras de linha excessivas
        texto = ' '.join(texto.split())
        
        # Capitalizar primeira letra
        if texto:
            texto = texto[0].upper() + texto[1:]
        
        # Garantir que termine com ponto
        if texto and not texto.endswith(('.', '!', '?')):
            texto += '.'
        
        return texto
    
    def _gerar_sugestoes_certificado(self, tipo_evento: str) -> List[str]:
        """
        Gera sugestões específicas para o tipo de evento.
        """
        sugestoes_base = [
            "Considere mencionar as competências específicas desenvolvidas",
            "Adicione informações sobre a carga horária",
            "Inclua o nome da instituição organizadora"
        ]
        
        sugestoes_especificas = {
            'workshop': [
                "Destaque as habilidades práticas adquiridas",
                "Mencione os projetos desenvolvidos"
            ],
            'curso': [
                "Inclua informações sobre avaliação",
                "Mencione os módulos concluídos"
            ],
            'palestra': [
                "Foque no conhecimento adquirido",
                "Destaque a relevância do tema"
            ]
        }
        
        return sugestoes_base + sugestoes_especificas.get(tipo_evento.lower(), [])
    
    def _fallback_texto_certificado(self, tipo_evento: str, nome_evento: str) -> Dict:
        """
        Texto de fallback quando a IA não está disponível.
        """
        templates = {
            'workshop': f"Certificamos que {{NOME_PARTICIPANTE}} participou do workshop '{nome_evento}', desenvolvendo competências práticas e teóricas na área abordada, com carga horária de {{CARGA_HORARIA_TOTAL}} horas.",
            'curso': f"Certificamos que {{NOME_PARTICIPANTE}} concluiu com êxito o curso '{nome_evento}', demonstrando dedicação e aproveitamento nas atividades propostas, totalizando {{CARGA_HORARIA_TOTAL}} horas de estudo.",
            'palestra': f"Certificamos que {{NOME_PARTICIPANTE}} participou da palestra '{nome_evento}', ampliando seus conhecimentos sobre o tema apresentado.",
            'default': f"Certificamos que {{NOME_PARTICIPANTE}} participou do evento '{nome_evento}', demonstrando interesse e dedicação nas atividades propostas."
        }
        
        texto = templates.get(tipo_evento.lower(), templates['default'])
        
        return {
            'success': True,
            'texto': texto,
            'sugestoes': self._gerar_sugestoes_certificado(tipo_evento),
            'fonte': 'template_local'
        }
    
    def _fallback_melhoria_texto(self, texto_original: str, objetivo: str) -> Dict:
        """
        Melhoria de fallback quando a IA não está disponível.
        """
        # Aplicar melhorias básicas baseadas em regras
        texto_melhorado = texto_original
        
        if objetivo == 'formalizar':
            # Substituições para formalizar
            substituicoes = {
                'você': 'Vossa Senhoria',
                'seu': 'vosso',
                'sua': 'vossa',
                'ok': 'adequado',
                'legal': 'apropriado'
            }
            
            for informal, formal in substituicoes.items():
                texto_melhorado = texto_melhorado.replace(informal, formal)
        
        elif objetivo == 'simplificar':
            # Substituições para simplificar
            substituicoes = {
                'outrossim': 'além disso',
                'destarte': 'assim',
                'conquanto': 'embora',
                'porquanto': 'porque'
            }
            
            for complexo, simples in substituicoes.items():
                texto_melhorado = texto_melhorado.replace(complexo, simples)
        
        return {
            'success': True,
            'texto_original': texto_original,
            'texto_melhorado': texto_melhorado,
            'melhorias_aplicadas': ['Melhorias básicas aplicadas'],
            'fonte': 'regras_locais'
        }
    
    def _identificar_melhorias(self, texto_original: str, texto_melhorado: str) -> List[str]:
        """
        Identifica as melhorias aplicadas no texto.
        """
        melhorias = []
        
        if len(texto_melhorado) > len(texto_original):
            melhorias.append('Texto expandido com mais detalhes')
        elif len(texto_melhorado) < len(texto_original):
            melhorias.append('Texto condensado para maior clareza')
        
        if texto_melhorado.count('.') > texto_original.count('.'):
            melhorias.append('Pontuação melhorada')
        
        if texto_melhorado != texto_original:
            melhorias.append('Estrutura e vocabulário aprimorados')
        
        return melhorias if melhorias else ['Texto otimizado']

# Instância global do serviço
ai_service = AIService()