# 📧 CONFIGURAÇÃO DE EMAIL - GUIA COMPLETO

## 🔧 **CONFIGURAÇÃO NECESSÁRIA**

### **1. Variáveis de Ambiente**

Crie um arquivo `.env` na raiz do projeto com as seguintes configurações:

```bash
# ============================================
# CONFIGURAÇÃO DE EMAIL - MAILJET (RECOMENDADO)
# ============================================

# Credenciais do Mailjet
MAILJET_API_KEY=sua_api_key_aqui
MAILJET_SECRET_KEY=seu_secret_key_aqui

# Email padrão para envio
MAIL_DEFAULT_SENDER=seu_email@dominio.com

# ============================================
# CONFIGURAÇÃO DE EMAIL - SMTP (FALLBACK)
# ============================================

# Configurações SMTP (usadas como fallback)
MAIL_SERVER=in-v3.mailjet.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=sua_api_key_aqui
MAIL_PASSWORD=seu_secret_key_aqui
```

### **2. Configuração no Mailjet**

1. **Acesse**: [https://app.mailjet.com/](https://app.mailjet.com/)
2. **Crie uma conta** ou faça login
3. **Vá para**: Account Settings → API Key Management
4. **Copie**:
   - **API Key** → `MAILJET_API_KEY`
   - **Secret Key** → `MAILJET_SECRET_KEY`
5. **Configure** o domínio de envio se necessário

### **3. Configuração Alternativa (SMTP)**

Se preferir usar SMTP diretamente:

```bash
# Para Gmail
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=seu_email@gmail.com
MAIL_PASSWORD=sua_senha_de_app

# Para Outlook
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=seu_email@outlook.com
MAIL_PASSWORD=sua_senha

# Para outros provedores
MAIL_SERVER=seu_servidor_smtp.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=seu_email@dominio.com
MAIL_PASSWORD=sua_senha
```

---

## 🧪 **TESTANDO A CONFIGURAÇÃO**

### **1. Teste Rápido**

```bash
python test_email_system.py
```

### **2. Teste Manual**

```python
from services.email_service import email_service

# Teste simples
resultado = email_service.send_email(
    subject="Teste de Configuração",
    to="seu_email@teste.com",
    text="Este é um teste do sistema de emails."
)

print(f"Resultado: {resultado}")
```

### **3. Verificar Logs**

Os logs detalhados aparecerão no console:

```
INFO: Iniciando envio de email - Assunto: Teste de Configuração
INFO: Destinatários: ['seu_email@teste.com']
INFO: Remetente: seu_email@dominio.com
INFO: Anexos: 0
INFO: Usando Mailjet para envio
INFO: Email enviado via Mailjet com sucesso
```

---

## 📋 **TEMPLATES DE EMAIL DISPONÍVEIS**

### **Templates Existentes:**

1. **`templates/email/certificado_revisor.html`**
   - Para certificados de revisores
   - Moderno e responsivo

2. **`templates/emails/revisor_status_change.html`**
   - Para notificações de revisores
   - Com código de acesso

3. **`templates/emails/confirmacao_inscricao_oficina.html`**
   - Para confirmação de inscrições

4. **`templates/emails/confirmacao_agendamento.html`**
   - Para confirmação de agendamentos

### **Criando Novos Templates:**

```html
<!-- templates/emails/meu_template.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Meu Template</title>
    <style>
        body { font-family: Arial, sans-serif; }
        .container { max-width: 600px; margin: auto; }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ titulo }}</h1>
        <p>Olá {{ nome }}!</p>
        <p>{{ mensagem }}</p>
    </div>
</body>
</html>
```

---

## 🚨 **SOLUÇÃO DE PROBLEMAS**

### **Problema: "Template não encontrado"**

**Solução:**
```python
# Verificar se o template existe
from services.email_service import email_service

template_path = "emails/meu_template.html"
if email_service._validate_template(template_path):
    print("Template válido")
else:
    print("Template não encontrado ou inválido")
```

### **Problema: "MAIL_DEFAULT_SENDER não configurado"**

**Solução:**
```bash
# Adicionar ao .env
MAIL_DEFAULT_SENDER=seu_email@dominio.com
```

### **Problema: "Nenhum provedor de email configurado"**

**Solução:**
```bash
# Configurar pelo menos um:
MAILJET_API_KEY=sua_key
MAILJET_SECRET_KEY=seu_secret

# OU

MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=seu_email@gmail.com
MAIL_PASSWORD=sua_senha
```

### **Problema: Emails não chegam**

**Verificações:**
1. ✅ Verificar spam/lixo eletrônico
2. ✅ Confirmar credenciais do Mailjet/SMTP
3. ✅ Verificar logs de erro
4. ✅ Testar com email diferente
5. ✅ Verificar limites de envio

---

## 📊 **MONITORAMENTO E LOGS**

### **Logs Disponíveis:**

```python
import logging

# Configurar nível de log
logging.basicConfig(level=logging.INFO)

# Ver logs do EmailService
logger = logging.getLogger('services.email_service')
logger.info("Teste de log")
```

### **Métricas Importantes:**

- ✅ **Taxa de sucesso**: % de emails enviados com sucesso
- ✅ **Tempo de envio**: Duração média do envio
- ✅ **Erros por tipo**: Categorização de falhas
- ✅ **Templates usados**: Frequência de uso

---

## 🔄 **MIGRAÇÃO DO SISTEMA LEGACY**

### **Antes (Sistema Legacy):**
```python
from utils import enviar_email

enviar_email(
    destinatario="usuario@email.com",
    nome_participante="João",
    nome_oficina="Oficina Teste",
    assunto="Confirmação",
    corpo_texto="Texto do email"
)
```

### **Depois (Sistema Unificado):**
```python
from services.email_service import email_service

resultado = email_service.send_email(
    subject="Confirmação",
    to="usuario@email.com",
    template="emails/confirmacao.html",
    template_context={
        "nome": "João",
        "oficina": "Oficina Teste"
    }
)
```

### **Compatibilidade:**
O sistema legacy ainda funciona, mas agora usa internamente o EmailService unificado.

---

## ✅ **CHECKLIST DE CONFIGURAÇÃO**

- [ ] Variáveis de ambiente configuradas
- [ ] Credenciais do Mailjet válidas
- [ ] Email padrão configurado
- [ ] Templates validados
- [ ] Teste de envio realizado
- [ ] Logs funcionando
- [ ] Sistema legacy migrado

---

**📅 Última atualização:** 29/09/2025  
**🔧 Sistema:** EmailService Unificado  
**📋 Status:** Configuração Completa

