"""
Configurações de Inteligência Artificial
"""

import os
from typing import Dict, Any

class AIConfig:
    """Configurações para serviços de IA"""
    
    # Hugging Face
    HF_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
    HF_MODEL_ID = os.getenv('HUGGINGFACE_MODEL_ID', 'microsoft/DialoGPT-medium')
    HF_API_URL = os.getenv('HUGGINGFACE_API_URL', 'https://api-inference.huggingface.co/models')
    
    # Text Generation Inference (TGI)
    USE_TGI = os.getenv('USE_TGI', 'false').lower() == 'true'
    TGI_ENDPOINT = os.getenv('TGI_ENDPOINT', 'http://localhost:3000')
    
    # Configurações de Fallback
    ENABLE_FALLBACK = True
    FALLBACK_TEMPLATES_PATH = 'templates/ai/fallback_templates.json'
    
    # Configurações de Rate Limiting
    RATE_LIMIT_REQUESTS = 100
    RATE_LIMIT_WINDOW = 3600  # 1 hora
    
    # Configurações de Timeout
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
    
    # Modelos Recomendados
    RECOMMENDED_MODELS = {
        'portuguese': [
            'neuralmind/bert-base-portuguese-cased',
            'pierreguillou/bert-base-cased-pt-lenerbr',
            'microsoft/DialoGPT-medium'
        ],
        'multilingual': [
            'microsoft/DialoGPT-medium',
            'microsoft/DialoGPT-large',
            'facebook/blenderbot-400M-distill'
        ],
        'specialized': [
            'microsoft/DialoGPT-medium',  # Para conversas
            'gpt2',  # Para geração de texto
            'distilgpt2'  # Versão menor do GPT-2
        ]
    }
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Retorna configurações atuais"""
        return {
            'huggingface': {
                'api_key': bool(cls.HF_API_KEY),
                'model_id': cls.HF_MODEL_ID,
                'api_url': cls.HF_API_URL
            },
            'tgi': {
                'enabled': cls.USE_TGI,
                'endpoint': cls.TGI_ENDPOINT
            },
            'fallback': {
                'enabled': cls.ENABLE_FALLBACK,
                'templates_path': cls.FALLBACK_TEMPLATES_PATH
            },
            'rate_limiting': {
                'requests': cls.RATE_LIMIT_REQUESTS,
                'window': cls.RATE_LIMIT_WINDOW
            },
            'timeout': {
                'request': cls.REQUEST_TIMEOUT,
                'max_retries': cls.MAX_RETRIES
            }
        }
    
    @classmethod
    def is_configured(cls) -> bool:
        """Verifica se pelo menos um serviço de IA está configurado"""
        return bool(cls.HF_API_KEY) or (cls.USE_TGI and cls.TGI_ENDPOINT)
    
    @classmethod
    def get_available_services(cls) -> list:
        """Retorna lista de serviços disponíveis"""
        services = []
        
        if cls.HF_API_KEY:
            services.append('huggingface')
        
        if cls.USE_TGI and cls.TGI_ENDPOINT:
            services.append('tgi')
        
        if cls.ENABLE_FALLBACK:
            services.append('fallback')
        
        return services
