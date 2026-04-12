# Plano de Deploy: OpenClaw + WhatsApp + API Oficial

## 1. Backend Flask

### Variaveis obrigatorias

- `SECRET_KEY`
- `DATABASE_URL` ou `DB_*`
- `APP_BASE_URL`
- `OPENCLAW_API_TOKEN`
- `OPENCLAW_API_ENABLED=1`
- `MERCADOPAGO_ACCESS_TOKEN` quando houver eventos pagos

### Passos

1. Publicar a aplicacao Flask com HTTPS.
2. Definir `APP_BASE_URL` para o dominio publico final.
3. Aplicar migracoes pendentes com `flask db upgrade`.
4. Validar os endpoints `/api/eventos` e `/api/inscricoes` com um token real.
5. Confirmar escrita em `static/comprovantes/openclaw`.

## 2. Plugin OpenClaw

1. Entrar em `integrations/openclaw`.
2. Rodar `npm install`.
3. Rodar `npm run check`.
4. Rodar `npm test`.
5. Adicionar o caminho do plugin em `plugins.load.paths`.
6. Configurar `plugins.entries.whatsapp-inscricoes.config`.
7. Reiniciar o gateway do OpenClaw.

## 3. WhatsApp / Canal

1. Garantir que o canal do WhatsApp no OpenClaw encaminhe um identificador estavel
   do usuario, por exemplo telefone ou JID, para o campo `userKey` nas chamadas.
2. Associar a skill `whatsapp-inscricoes` ao agente responsavel pelo atendimento.
3. Permitir apenas as oito tools desta integracao para o agente de inscricoes.

## 4. Observabilidade

- Logar todas as chamadas da API com request id e CPF mascarado.
- Monitorar status HTTP 4xx e 5xx dos endpoints `/api/*`.
- Monitorar falhas do Mercado Pago separadamente.
- Rotacionar o `OPENCLAW_API_TOKEN` periodicamente.

## 5. Checklist de go-live

- `pytest tests/test_openclaw_api_routes.py -q`
- `npm run check`
- `npm test`
- teste manual de inscricao gratuita
- teste manual de inscricao paga
- teste manual de comprovante
- teste manual de duplicidade
