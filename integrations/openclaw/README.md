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

## Limitacao atual

Este pacote, no estado atual, registra apenas tools no gateway OpenClaw.
Ele nao implementa um plugin de canal do WhatsApp por conta propria.

Na pratica, isso significa:

- ele nao "escuta" mensagens recebidas no WhatsApp sozinho
- ele nao responde automaticamente so por estar carregado como plugin
- ele precisa ser conectado a um agente/canal do OpenClaw que use essas tools

Se o numero recebe a mensagem mas nao responde, o problema mais provavel e:

- nao existe um canal/agente OpenClaw ligado a esse numero, ou
- o plugin foi carregado apenas como plugin comum de tools, sem wiring de canal

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

Arquivo pronto para copiar:

- `integrations/openclaw/openclaw.gateway.example.json`

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

Campos que voce precisa ajustar no exemplo:

- `apiBaseUrl`: URL publica do Flask, por exemplo o dominio/ngrok que responde as rotas `/api/...`
  No arquivo de exemplo atual, ele ja vem preenchido com `https://a9d8-2804-29b8-513c-2e78-7002-24b0-5b1c-ac9b.ngrok-free.app`.
- `apiToken`: mesmo valor definido em `OPENCLAW_API_TOKEN` no backend Flask
- `defaultClienteId`: cliente padrao para listar eventos, se fizer sentido no seu fluxo

Observacao:

- esse arquivo configura o plugin e a comunicacao com a API oficial
- a conexao do numero/canal do WhatsApp com o gateway OpenClaw ainda depende da configuracao do proprio gateway/provedor

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
