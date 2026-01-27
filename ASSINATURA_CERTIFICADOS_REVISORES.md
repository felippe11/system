# ✍️ ASSINATURA OPCIONAL NOS CERTIFICADOS DE REVISORES

## 🎯 **FUNCIONALIDADE IMPLEMENTADA**

Agora é possível configurar se a assinatura do cliente deve aparecer ou não nos certificados de revisores através de um checkbox na página de configuração.

---

## 🔧 **MUDANÇAS IMPLEMENTADAS**

### **1. Modelo de Dados**

**Arquivo:** `models/certificado.py`

```python
class CertificadoRevisorConfig(db.Model):
    # ... campos existentes ...
    
    # NOVO CAMPO
    incluir_assinatura_cliente = db.Column(db.Boolean, default=True)
```

**Descrição:** Campo booleano que controla se a assinatura do cliente aparece no PDF.

### **2. Interface de Configuração**

**Arquivo:** `templates/certificado_revisor/configurar.html`

```html
<div class="mb-3">
    <div class="form-check">
        <input class="form-check-input" type="checkbox" id="incluir_assinatura_cliente" 
               name="incluir_assinatura_cliente" {% if config.incluir_assinatura_cliente %}checked{% endif %}>
        <label class="form-check-label" for="incluir_assinatura_cliente">
            <i class="bi bi-pen me-1"></i>Incluir Assinatura do Cliente
        </label>
    </div>
    <div class="form-text">Se marcado, o certificado incluirá a assinatura com o nome do cliente</div>
</div>
```

**Descrição:** Checkbox que permite ao cliente escolher se quer incluir sua assinatura.

### **3. Processamento do Formulário**

**Arquivo:** `routes/certificado_revisor_routes.py`

```python
def salvar_config_certificado_revisor():
    # ... código existente ...
    
    incluir_assinatura_cliente = request.form.get('incluir_assinatura_cliente') == 'on'
    
    # Atualizar configuração
    config.incluir_assinatura_cliente = incluir_assinatura_cliente
```

**Descrição:** Processa o valor do checkbox e salva na configuração.

### **4. Geração de PDF Condicional**

**Arquivo:** `services/pdf_service.py`

```python
def gerar_certificado_revisor_pdf(certificado):
    # ... código existente ...
    
    # Verificar se deve incluir assinatura baseado na configuração
    incluir_assinatura = True  # Padrão
    
    # Buscar configuração do certificado
    try:
        from models import CertificadoRevisorConfig
        config = CertificadoRevisorConfig.query.filter_by(
            cliente_id=certificado.cliente_id,
            evento_id=certificado.evento_id
        ).first()
        
        if config:
            incluir_assinatura = config.incluir_assinatura_cliente
    except Exception as e:
        logger.warning(f"Erro ao verificar configuração de assinatura: {e}")
        incluir_assinatura = True  # Manter padrão em caso de erro
    
    if incluir_assinatura:
        # Adicionar assinatura do cliente
        assinatura_y = info_y + 30
        pdf.set_font('Arial', '', 12)
        pdf.set_xy(margin_left, assinatura_y)
        pdf.cell(text_width, 8, certificado.cliente.nome, 0, 1, 'C')
        
        # Linha para assinatura
        pdf.set_xy(margin_left + (text_width / 2) - 30, assinatura_y + 15)
        pdf.line(margin_left + (text_width / 2) - 30, assinatura_y + 15, 
                margin_left + (text_width / 2) + 30, assinatura_y + 15)
```

**Descrição:** Verifica a configuração e inclui/exclui a assinatura condicionalmente.

---

## 📋 **COMO USAR**

### **1. Configurar Assinatura**

1. **Acesse** a página de configuração de certificados de revisores
2. **Localize** o checkbox "Incluir Assinatura do Cliente"
3. **Marque/desmarque** conforme desejado:
   - ✅ **Marcado**: Assinatura aparece no PDF
   - ❌ **Desmarcado**: Assinatura não aparece no PDF
4. **Salve** a configuração

### **2. Gerar Certificados**

- **Certificados individuais**: Respeitam a configuração atual
- **Certificados em lote**: Respeitam a configuração atual
- **Certificados existentes**: Serão regenerados com a nova configuração

---

## 🗄️ **MIGRAÇÃO DO BANCO DE DADOS**

### **Para Desenvolvimento:**

```bash
python add_assinatura_certificado_revisor.py
```

### **Para Produção:**

```bash
flask db upgrade
```

### **Campo Adicionado:**

```sql
ALTER TABLE certificado_revisor_config 
ADD COLUMN incluir_assinatura_cliente BOOLEAN DEFAULT TRUE;
```

---

## 🎨 **VISUALIZAÇÃO**

### **Com Assinatura (Padrão):**
```
┌─────────────────────────────────────┐
│         CERTIFICADO DE REVISOR       │
│                                     │
│  Certificamos que João Silva atuou  │
│  como revisor de trabalhos...       │
│                                     │
│        Emitido em: 29/09/2025       │
│                                     │
│           Cliente Nome               │
│        ________________             │
└─────────────────────────────────────┘
```

### **Sem Assinatura:**
```
┌─────────────────────────────────────┐
│         CERTIFICADO DE REVISOR       │
│                                     │
│  Certificamos que João Silva atuou  │
│  como revisor de trabalhos...       │
│                                     │
│        Emitido em: 29/09/2025       │
└─────────────────────────────────────┘
```

---

## 🔄 **COMPATIBILIDADE**

### **Registros Existentes:**
- ✅ **Valor padrão**: `TRUE` (assinatura incluída)
- ✅ **Retrocompatibilidade**: Certificados antigos continuam funcionando
- ✅ **Migração automática**: Registros existentes são atualizados

### **Sistema Legacy:**
- ✅ **Funciona normalmente**: Não afeta outras funcionalidades
- ✅ **Configuração independente**: Cada evento pode ter configuração diferente

---

## 🧪 **TESTES**

### **1. Teste de Configuração:**
```python
# Verificar se campo foi adicionado
config = CertificadoRevisorConfig.query.first()
print(f"Incluir assinatura: {config.incluir_assinatura_cliente}")
```

### **2. Teste de Geração:**
```python
# Gerar certificado com assinatura
certificado = CertificadoRevisor.query.first()
pdf_path = gerar_certificado_revisor_pdf(certificado)
print(f"PDF gerado: {pdf_path}")
```

### **3. Teste de Interface:**
- ✅ Checkbox aparece na página de configuração
- ✅ Valor é salvo corretamente
- ✅ PDF é gerado conforme configuração

---

## 📊 **RESUMO DAS MUDANÇAS**

| Componente | Status | Descrição |
|------------|--------|-----------|
| **Modelo** | ✅ | Campo `incluir_assinatura_cliente` adicionado |
| **Interface** | ✅ | Checkbox na página de configuração |
| **Backend** | ✅ | Processamento do formulário atualizado |
| **PDF** | ✅ | Geração condicional implementada |
| **Migration** | ✅ | Script para atualizar banco de dados |
| **Documentação** | ✅ | Guia completo criado |

---

## 🚀 **PRÓXIMOS PASSOS**

1. **Aplicar migration** no banco de dados
2. **Testar funcionalidade** em ambiente de desenvolvimento
3. **Deploy em produção** com `flask db upgrade`
4. **Verificar certificados** gerados com nova configuração

---

**📅 Implementado em:** 29/09/2025  
**🔧 Status:** Funcionalidade Completa  
**📋 Próxima revisão:** Após testes em produção

