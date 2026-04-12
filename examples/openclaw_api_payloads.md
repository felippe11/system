# Exemplos de Payload: OpenClaw API

## GET /api/eventos

```http
GET /api/eventos?cliente_id=1&somente_publicos=true
Authorization: Bearer <OPENCLAW_API_TOKEN>
```

## GET /api/eventos/:id

```http
GET /api/eventos/12
Authorization: Bearer <OPENCLAW_API_TOKEN>
```

## GET /api/participantes/cpf/:cpf

```http
GET /api/participantes/cpf/52998224725
Authorization: Bearer <OPENCLAW_API_TOKEN>
```

## POST /api/inscricoes

```json
{
  "evento_id": 12,
  "cpf": "52998224725",
  "nome": "Ana da Silva",
  "email": "ana@example.com",
  "formacao": "Graduacao",
  "senha": "SenhaTemporaria123!",
  "tipo_inscricao_id": 3,
  "lote_id": 7
}
```

## GET /api/inscricoes

```http
GET /api/inscricoes?cpf=52998224725&evento_id=12
Authorization: Bearer <OPENCLAW_API_TOKEN>
```

## GET /api/inscricoes/protocolo/:protocolo

```http
GET /api/inscricoes/protocolo/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <OPENCLAW_API_TOKEN>
```

## GET /api/inscricoes/status/:inscricao_id

```http
GET /api/inscricoes/status/981
Authorization: Bearer <OPENCLAW_API_TOKEN>
```

## GET /api/comprovantes/:inscricao_id

```http
GET /api/comprovantes/981
Authorization: Bearer <OPENCLAW_API_TOKEN>
```

Resposta resumida:

```json
{
  "success": true,
  "data": {
    "inscricao_id": 981,
    "protocolo": "550e8400-e29b-41d4-a716-446655440000",
    "download_url": "https://api.example.com/api/comprovantes/981/arquivo?token=550e8400-e29b-41d4-a716-446655440000",
    "arquivo_nome": "openclaw_comprovante_981_550e8400.pdf"
  }
}
```

## POST /api/pagamentos/gerar-link

```json
{
  "inscricao_id": 981
}
```

Resposta resumida:

```json
{
  "success": true,
  "data": {
    "payment_required": true,
    "status_pagamento": "pending",
    "payment_url": "https://www.mercadopago.com.br/checkout/v1/redirect?pref_id=..."
  }
}
```
