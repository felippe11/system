# 🎓 Sistema de Certificados para Revisores

## 📋 Visão Geral

Esta funcionalidade permite que clientes configurem e liberem certificados para revisores que participaram da avaliação de trabalhos científicos. Os revisores podem visualizar e baixar seus certificados através do dashboard.

## ✨ Funcionalidades Implementadas

### 🏢 Para Clientes (Dashboard Cliente)

#### 1. **Configuração de Certificados**
- **Localização**: Dashboard Cliente → Aba "Revisores" → Seção "Certificados de Revisores"
- **Funcionalidades**:
  - Configurar título do certificado
  - Personalizar texto com variáveis dinâmicas
  - Upload de imagem de fundo
  - Definir critérios de liberação automática
  - Configurar número mínimo de trabalhos revisados

#### 2. **Liberação de Certificados**
- **Liberação Individual**: Liberar certificado para um revisor específico
- **Liberação em Massa**: Liberar certificados para todos os revisores aprovados
- **Geração de PDF**: Gerar PDF do certificado automaticamente
- **Envio por Email**: Enviar certificados por email para revisores

#### 3. **Gestão de Revisores**
- Lista de revisores aprovados
- Estatísticas de trabalhos revisados
- Status dos certificados (liberado/pendente)
- Ações rápidas por revisor

### 👨‍🏫 Para Revisores (Dashboard Revisor)

#### 1. **Visualização de Certificados**
- **Localização**: Dashboard Revisor → Seção "Meus Certificados de Revisor"
- **Funcionalidades**:
  - Lista de certificados liberados
  - Informações detalhadas (cliente, evento, trabalhos revisados)
  - Data de liberação
  - Status do certificado

#### 2. **Download de Certificados**
- Download direto do PDF
- Nome do arquivo personalizado
- Verificação de integridade

## 🔧 Variáveis Dinâmicas Disponíveis

No texto do certificado, você pode usar as seguintes variáveis:

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `{nome_revisor}` | Nome completo do revisor | João Silva |
| `{evento_nome}` | Nome do evento | Congresso de Ciência 2024 |
| `{cliente_nome}` | Nome do cliente | Universidade ABC |
| `{trabalhos_revisados}` | Quantidade de trabalhos revisados | 15 |
| `{data_liberacao}` | Data de liberação do certificado | 15/12/2024 |

### Exemplo de Texto:
```
Certificamos que {nome_revisor} atuou como revisor de trabalhos no evento '{evento_nome}', 
contribuindo para a avaliação de {trabalhos_revisados} trabalhos científicos. 
Este certificado foi emitido em {data_liberacao} pela {cliente_nome}.
```

## 🗃️ Estrutura do Banco de Dados

### Tabela: `certificado_revisor_config`
Configurações de certificados por cliente/evento.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | Integer | Chave primária |
| `cliente_id` | Integer | ID do cliente |
| `evento_id` | Integer | ID do evento (opcional) |
| `titulo_certificado` | String | Título do certificado |
| `texto_certificado` | Text | Texto com variáveis |
| `fundo_certificado` | String | Caminho da imagem de fundo |
| `liberacao_automatica` | Boolean | Liberação automática |
| `criterio_trabalhos_minimos` | Integer | Mínimo de trabalhos |

### Tabela: `certificado_revisor`
Certificados emitidos para revisores.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | Integer | Chave primária |
| `revisor_id` | Integer | ID do revisor |
| `cliente_id` | Integer | ID do cliente |
| `evento_id` | Integer | ID do evento |
| `liberado` | Boolean | Status de liberação |
| `data_liberacao` | DateTime | Data de liberação |
| `liberado_por` | Integer | ID do usuário que liberou |
| `titulo` | String | Título do certificado |
| `texto_personalizado` | Text | Texto personalizado |
| `fundo_personalizado` | String | Fundo personalizado |
| `trabalhos_revisados` | Integer | Quantidade de trabalhos |
| `arquivo_path` | String | Caminho do PDF gerado |

## 🚀 Como Usar

### 1. **Configurar Certificado (Cliente)**

1. Acesse o Dashboard Cliente
2. Vá para a aba "Revisores"
3. Na seção "Certificados de Revisores":
   - Selecione um evento
   - Clique em "Configurar Certificados"
4. Configure:
   - Título do certificado
   - Texto com variáveis
   - Imagem de fundo (opcional)
   - Critérios de liberação
5. Salve a configuração

### 2. **Liberar Certificados (Cliente)**

1. Na página de configuração, visualize a lista de revisores
2. Para liberação individual:
   - Clique no botão "Liberar" ao lado do revisor
3. Para liberação em massa:
   - Clique em "Liberar Todos"
4. Para enviar por email:
   - Clique em "Enviar Todos por Email"

### 3. **Visualizar Certificados (Revisor)**

1. Acesse o Dashboard Revisor
2. Na seção "Meus Certificados de Revisor":
   - Clique em "Ver Meus Certificados"
3. Visualize a lista de certificados liberados
4. Clique em "Baixar Certificado" para download

## 📁 Arquivos Criados/Modificados

### Novos Arquivos:
- `routes/certificado_revisor_routes.py` - Rotas da funcionalidade
- `templates/certificado_revisor/configurar.html` - Página de configuração
- `templates/certificado_revisor/meus_certificados.html` - Página do revisor
- `templates/email/certificado_revisor.html` - Template de email
- `create_certificado_revisor_tables.py` - Script de migração

### Arquivos Modificados:
- `models/certificado.py` - Novos modelos
- `models/__init__.py` - Importações dos novos modelos
- `services/pdf_service.py` - Função de geração de PDF
- `services/email_service.py` - Função de envio de email
- `templates/dashboard/dashboard_cliente.html` - Seção na aba revisores
- `templates/peer_review/reviewer/dashboard.html` - Seção de certificados
- `routes/__init__.py` - Registro do blueprint

## 🔧 Instalação

### 🏭 **Para Produção (Recomendado)**

1. **Aplique a migração usando Flask-Migrate**:
   ```bash
   # Definir variável de ambiente
   export FLASK_APP=app.py
   
   # Aplicar migração
   flask db upgrade
   ```

2. **Verifique se as tabelas foram criadas**:
   ```sql
   -- Verificar tabelas criadas
   SELECT table_name FROM information_schema.tables 
   WHERE table_name IN ('certificado_revisor_config', 'certificado_revisor');
   ```

### 🧪 **Para Desenvolvimento/Teste Local**

1. **Execute o script de migração**:
   ```bash
   python create_certificado_revisor_tables.py
   ```

2. **Verifique se as tabelas foram criadas**:
   - `certificado_revisor_config`
   - `certificado_revisor`

### ✅ **Teste a Funcionalidade**

1. Configure um certificado no dashboard do cliente
2. Libere certificados para revisores
3. Verifique se os revisores conseguem baixar

## 🎨 Personalização

### Imagens de Fundo
- Formatos suportados: PNG, JPG, JPEG, PDF
- Recomendado: 297x210mm (A4 landscape)
- Armazenamento: `static/uploads/certificados_revisor/`

### PDFs Gerados
- Formato: A4 landscape
- Fonte: DejaVu Sans (suporte a acentos)
- Armazenamento: `static/certificados/revisores/`

## 🔒 Segurança

- Apenas clientes podem configurar e liberar certificados
- Revisores só visualizam seus próprios certificados
- Verificação de permissões em todas as rotas
- Validação de arquivos de upload

## 🐛 Solução de Problemas

### Erro: "Tabela não encontrada"
- Execute o script de migração: `python create_certificado_revisor_tables.py`

### Erro: "Fonte não encontrada"
- Verifique se os arquivos de fonte estão em `fonts/`:
  - `DejaVuSans.ttf`
  - `DejaVuSans-Bold.ttf`

### Erro: "Diretório não encontrado"
- Crie os diretórios necessários:
  - `static/uploads/certificados_revisor/`
  - `static/certificados/revisores/`

### Certificado não aparece para o revisor
- Verifique se o certificado foi liberado
- Confirme se o revisor tem candidatura aprovada
- Verifique se o evento está correto

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique os logs da aplicação
2. Confirme se todas as tabelas foram criadas
3. Teste com dados de exemplo
4. Verifique permissões de usuário

---

**Desenvolvido com ❤️ para o Sistema IAFAP**
