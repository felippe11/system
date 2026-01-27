# 🚀 Deploy - Certificados de Revisores

## 📋 Instruções para Deploy em Produção

### 1. **Preparação do Ambiente**

```bash
# 1. Fazer backup do banco de dados
pg_dump -h localhost -U usuario -d database_name > backup_antes_certificados_revisores.sql

# 2. Verificar versão atual do banco
flask db current

# 3. Verificar se há migrações pendentes
flask db show
```

### 2. **Aplicação da Migração**

```bash
# Definir variável de ambiente
export FLASK_APP=app.py

# Aplicar migração
flask db upgrade

# Verificar se foi aplicada
flask db current
```

### 3. **Verificação das Tabelas**

```sql
-- Conectar ao banco e verificar
\c database_name

-- Verificar se as tabelas foram criadas
SELECT table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_name IN ('certificado_revisor_config', 'certificado_revisor')
ORDER BY table_name, ordinal_position;

-- Verificar índices
SELECT indexname, tablename 
FROM pg_indexes 
WHERE tablename IN ('certificado_revisor_config', 'certificado_revisor');
```

### 4. **Criação de Diretórios**

```bash
# Criar diretórios necessários
mkdir -p static/uploads/certificados_revisor
mkdir -p static/certificados/revisores

# Definir permissões adequadas
chmod 755 static/uploads/certificados_revisor
chmod 755 static/certificados/revisores
```

### 5. **Verificação de Funcionalidade**

1. **Acesse o dashboard do cliente**
2. **Vá para a aba "Revisores"**
3. **Verifique se a seção "Certificados de Revisores" aparece**
4. **Selecione um evento e clique em "Configurar Certificados"**
5. **Teste a configuração básica**

### 6. **Rollback (se necessário)**

```bash
# Se houver problemas, fazer rollback
flask db downgrade

# Verificar versão após rollback
flask db current
```

## 🔍 Checklist de Deploy

- [ ] Backup do banco de dados realizado
- [ ] Migração aplicada com sucesso (`flask db upgrade`)
- [ ] Tabelas criadas no banco
- [ ] Diretórios criados com permissões adequadas
- [ ] Funcionalidade testada no dashboard do cliente
- [ ] Funcionalidade testada no dashboard do revisor
- [ ] Logs verificados (sem erros)

## 🚨 Troubleshooting

### Erro: "Tabela já existe"
```bash
# Verificar se a migração já foi aplicada
flask db current

# Se necessário, marcar como aplicada manualmente
flask db stamp head
```

### Erro: "Permissão negada"
```bash
# Verificar permissões dos diretórios
ls -la static/uploads/
ls -la static/certificados/

# Corrigir permissões
chmod 755 static/uploads/certificados_revisor
chmod 755 static/certificados/revisores
```

### Erro: "Fonte não encontrada"
```bash
# Verificar se as fontes estão presentes
ls -la fonts/DejaVuSans*

# Se não estiverem, copiar do sistema ou baixar
# DejaVuSans.ttf e DejaVuSans-Bold.ttf
```

## 📊 Monitoramento Pós-Deploy

### 1. **Verificar Logs**
```bash
# Verificar logs da aplicação
tail -f logs/app.log | grep -i certificado

# Verificar logs de erro
tail -f logs/error.log
```

### 2. **Monitorar Performance**
```sql
-- Verificar tamanho das tabelas
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE tablename IN ('certificado_revisor_config', 'certificado_revisor');
```

### 3. **Teste de Funcionalidade**
- [ ] Cliente consegue configurar certificados
- [ ] Cliente consegue liberar certificados individuais
- [ ] Cliente consegue liberar certificados em massa
- [ ] Cliente consegue enviar por email
- [ ] Revisor consegue visualizar certificados
- [ ] Revisor consegue baixar PDFs
- [ ] Emails são enviados corretamente

## 🔄 Atualizações Futuras

Para futuras atualizações da funcionalidade:

1. **Criar nova migração**:
   ```bash
   flask db migrate -m "Descrição da mudança"
   ```

2. **Aplicar migração**:
   ```bash
   flask db upgrade
   ```

3. **Verificar aplicação**:
   ```bash
   flask db current
   ```

---

**✅ Deploy concluído com sucesso!**

A funcionalidade de certificados de revisores está agora disponível em produção.

