# OpenClaw WhatsApp Inscricoes

Plugin nativo do OpenClaw para usar o WhatsApp como interface conversacional
das inscricoes, com o backend Flask deste repositorio como autoridade oficial.

## O que este pacote entrega

- tools tipadas para consultar e criar inscricoes
- cliente HTTP tipado para a API oficial
- maquina de estados por usuario
- persistencia local do estado conversacional para retomada
- prompts internos e skill em pt-BR
- testes e checagem de tipo

## Tools registradas

- `listar_eventos`
- `detalhar_evento`
- `buscar_participante_por_cpf`
- `criar_inscricao`
- `consultar_inscricao_por_cpf`
- `consultar_status_inscricao`
- `consultar_comprovante`
- `gerar_link_pagamento`

## Estrutura

```text
integrations/openclaw
├── openclaw.plugin.json
├── package.json
├── tsconfig.json
├── src
│   ├── config.ts
│   ├── index.ts
│   ├── types.ts
│   ├── http/api-client.ts
│   ├── intents
│   │   ├── flows-ptbr.ts
│   │   └── state-machine.ts
│   ├── prompts/safe-tool-prompts.ts
│   └── services
│       ├── registration-service.ts
│       └── state-store.ts
├── skills
│   └── whatsapp-inscricoes
│       └── SKILL.md
└── test
    ├── state-machine.test.ts
    └── state-store.test.ts
```

## Configuracao do plugin

### 1. Instalar dependencias

```bash
cd integrations/openclaw
npm install
npm run check
npm test
```

### 2. Habilitar no OpenClaw

Exemplo de configuracao:

```json
{
  "plugins": {
    "enabled": true,
    "load": {
      "paths": [
        "C:/Users/Felipe Cabral/system/integrations/openclaw"
      ]
    },
    "entries": {
      "whatsapp-inscricoes": {
        "enabled": true,
        "config": {
          "apiBaseUrl": "https://seu-backend.example.com",
          "apiToken": "troque-por-um-token-forte",
          "defaultClienteId": 1,
          "publicOnly": true,
          "requestTimeoutMs": 15000
        }
      }
    }
  },
  "tools": {
    "allow": [
      "whatsapp-inscricoes"
    ]
  }
}
```

Depois reinicie o gateway:

```bash
openclaw gateway restart
```

## Estado conversacional

O estado por usuario fica em um arquivo JSON no diretório de estado do OpenClaw.
Os principais estados sao:

- `awaiting_event_selection`
- `awaiting_cpf`
- `awaiting_name`
- `awaiting_email`
- `awaiting_formacao`
- `ready_to_create`
- `registration_created`
- `awaiting_payment_link`
- `completed`
- `error`

## Fluxo recomendado

1. `listar_eventos`
2. `detalhar_evento`
3. `buscar_participante_por_cpf`
4. `criar_inscricao`
5. `gerar_link_pagamento` quando `payment_required=true`
6. `consultar_status_inscricao`
7. `consultar_comprovante`

## Garantias

- o agente nao inventa sucesso
- toda consulta vem da API oficial
- duplicidade e tratada pelo backend e refletida como `duplicate_registration`
- comprovante e link de pagamento so aparecem quando a API oficial devolve os dados
