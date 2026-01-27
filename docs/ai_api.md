# API de Inteligência Artificial

## Visão Geral

A API de IA do sistema permite geração e melhoria de textos para certificados e declarações usando diferentes provedores de IA, incluindo Hugging Face e Text Generation Inference (TGI).

## Configuração

### Variáveis de Ambiente

```bash
# Hugging Face
HUGGINGFACE_API_KEY=your-huggingface-api-key
HUGGINGFACE_MODEL_ID=microsoft/DialoGPT-medium
HUGGINGFACE_API_URL=https://api-inference.huggingface.co/models

# Text Generation Inference (TGI)
USE_TGI=false
TGI_ENDPOINT=http://localhost:3000
```

### Modelos Recomendados

#### Para Português:
- `neuralmind/bert-base-portuguese-cased`
- `pierreguillou/bert-base-cased-pt-lenerbr`

#### Para Multilíngue:
- `microsoft/DialoGPT-medium`
- `microsoft/DialoGPT-large`
- `facebook/blenderbot-400M-distill`

#### Para Geração de Texto:
- `gpt2`
- `distilgpt2`

## Endpoints

### 1. Gerar Texto para Certificado

**POST** `/ai/gerar-texto-certificado`

Gera texto para certificados usando IA.

**Request Body:**
```json
{
  "tipo_evento": "workshop",
  "nome_evento": "Workshop de Python",
  "contexto": "Focado em desenvolvimento web, 40 horas"
}
```

**Response:**
```json
{
  "success": true,
  "texto": "Certificamos que {NOME_PARTICIPANTE} participou do workshop 'Workshop de Python', desenvolvendo competências práticas e teóricas na área de desenvolvimento web, com carga horária de 40 horas.",
  "modelo": "TGI",
  "timestamp": "2024-01-15T10:30:00"
}
```

### 2. Melhorar Texto

**POST** `/ai/melhorar-texto`

Melhora um texto existente.

**Request Body:**
```json
{
  "texto_original": "João participou do curso",
  "objetivo": "formalizar"
}
```

**Response:**
```json
{
  "success": true,
  "texto_original": "João participou do curso",
  "texto_melhorado": "João compareceu ao curso",
  "objetivo": "formalizar",
  "modelo": "TGI",
  "timestamp": "2024-01-15T10:30:00"
}
```

### 3. Sugestões de Variáveis

**POST** `/ai/sugestoes-variaveis`

Gera sugestões de variáveis dinâmicas.

**Request Body:**
```json
{
  "contexto": "Certificado de workshop de programação"
}
```

**Response:**
```json
{
  "success": true,
  "sugestoes": [
    {
      "nome": "NOME_PARTICIPANTE",
      "descricao": "Nome completo do participante"
    },
    {
      "nome": "NOME_EVENTO",
      "descricao": "Nome do evento"
    }
  ],
  "modelo": "TGI",
  "timestamp": "2024-01-15T10:30:00"
}
```

### 4. Verificar Qualidade

**POST** `/ai/verificar-qualidade`

Verifica a qualidade de um texto.

**Request Body:**
```json
{
  "texto": "Certificamos que João participou do curso"
}
```

**Response:**
```json
{
  "success": true,
  "texto": "Certificamos que João participou do curso",
  "analise": "Texto adequado. Sugestões: Adicionar variáveis dinâmicas como {NOME_PARTICIPANTE}.",
  "modelo": "TGI",
  "timestamp": "2024-01-15T10:30:00"
}
```

### 5. Status dos Serviços

**GET** `/ai/status`

Verifica o status dos serviços de IA.

**Response:**
```json
{
  "success": true,
  "status": {
    "tgi": {
      "disponivel": true,
      "endpoint": "http://localhost:3000",
      "configurado": true
    },
    "huggingface": {
      "disponivel": true,
      "api_key": true,
      "modelo": "microsoft/DialoGPT-medium",
      "configurado": true
    },
    "fallback": {
      "disponivel": true,
      "descricao": "Templates locais e regras básicas"
    }
  }
}
```

### 6. Testar Conectividade

**POST** `/ai/testar-huggingface`
**POST** `/ai/testar-tgi`

Testa a conectividade com os serviços.

**Response:**
```json
{
  "success": true,
  "message": "Conexão com Hugging Face funcionando",
  "resultado": {
    "success": true,
    "texto": "Texto de teste gerado",
    "modelo": "Hugging Face",
    "timestamp": "2024-01-15T10:30:00"
  }
}
```

## Fallback e Tratamento de Erros

O sistema possui um sistema robusto de fallback:

1. **TGI** (se configurado e disponível)
2. **Hugging Face** (se configurado e disponível)
3. **Templates Locais** (sempre disponível)

### Templates de Fallback

O sistema inclui templates pré-definidos para diferentes tipos de eventos:

- **Workshop**: Foco em competências práticas
- **Curso**: Ênfase em conclusão e aproveitamento
- **Palestra**: Participação e ampliação de conhecimentos
- **Seminário**: Debate e troca de conhecimentos

## Uso com Text Generation Inference (TGI)

### Instalação do TGI

```bash
# Instalar TGI
pip install text-generation-inference

# Executar servidor
text-generation-inference --model-id microsoft/DialoGPT-medium --port 3000
```

### Configuração

```bash
USE_TGI=true
TGI_ENDPOINT=http://localhost:3000
```

### Vantagens do TGI

- **Performance**: Mais rápido que API do Hugging Face
- **Controle**: Execução local
- **Custo**: Sem custos de API
- **Privacidade**: Dados não saem do servidor

## Exemplos de Uso

### Python

```python
import requests

# Gerar texto para certificado
response = requests.post('http://localhost:5000/ai/gerar-texto-certificado', 
    json={
        'tipo_evento': 'workshop',
        'nome_evento': 'Workshop de Python',
        'contexto': 'Focado em desenvolvimento web'
    }
)

data = response.json()
print(data['texto'])
```

### JavaScript

```javascript
// Gerar texto para certificado
const response = await fetch('/ai/gerar-texto-certificado', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        tipo_evento: 'workshop',
        nome_evento: 'Workshop de Python',
        contexto: 'Focado em desenvolvimento web'
    })
});

const data = await response.json();
console.log(data.texto);
```

## Monitoramento e Logs

O sistema registra todas as operações de IA:

- **Sucessos**: Textos gerados, melhorias aplicadas
- **Erros**: Falhas de conectividade, timeouts
- **Fallbacks**: Uso de templates locais
- **Performance**: Tempo de resposta, uso de recursos

## Limitações e Considerações

### Rate Limiting
- **Hugging Face**: 1000 requests/hora (gratuito)
- **TGI**: Sem limitações (local)

### Timeouts
- **Padrão**: 30 segundos
- **Configurável**: Via variáveis de ambiente

### Qualidade
- **IA**: Alta qualidade, contexto específico
- **Fallback**: Boa qualidade, genérico

## Suporte

Para problemas ou dúvidas:

1. Verificar logs do sistema
2. Testar conectividade com `/ai/status`
3. Usar templates de fallback como alternativa
4. Consultar documentação do Hugging Face/TGI
