# Sistema de Notificações de Compras

## Visão Geral

O sistema de notificações de compras monitora automaticamente situações críticas e envia alertas por email para administradores e monitores responsáveis.

## Tipos de Alertas

### 1. Orçamento Excedido 🚨
- **Quando**: Orçamento de um polo excede 100% do valor planejado
- **Destinatários**: Administradores e monitores do polo + administradores globais
- **Frequência**: Imediata quando detectado

### 2. Orçamento Próximo ao Limite ⚠️
- **Quando**: Orçamento de um polo atinge 90% do valor planejado
- **Destinatários**: Administradores e monitores do polo + administradores globais
- **Frequência**: Imediata quando detectado

### 3. Compras Pendentes 📋
- **Quando**: Compras permanecem com status "pendente" por mais de 7 dias
- **Destinatários**: Administradores e monitores do polo
- **Frequência**: Diária

### 4. Prestações de Contas Atrasadas 📄
- **Quando**: Compras aprovadas há mais de 30 dias sem prestação de contas
- **Destinatários**: Administradores e monitores do polo
- **Frequência**: Semanal

## Configuração

### Acesso à Configuração
1. Faça login como administrador
2. Acesse "Gerenciar Compras"
3. Clique no botão "Notificações"

### Funcionalidades Disponíveis
- **Verificação Manual**: Execute verificação imediata de todos os alertas
- **Teste de Notificações**: Envie emails de teste para validar configuração
- **Status em Tempo Real**: Visualize alertas ativos no dashboard
- **Histórico de Orçamentos**: Monitore status de todos os orçamentos

## Configuração Técnica

### Pré-requisitos
- Serviço Mailjet configurado (variáveis MAILJET_API_KEY e MAILJET_SECRET_KEY)
- Usuários com emails válidos cadastrados
- Orçamentos configurados para os polos

### Verificação Automática

#### Execução Manual
```bash
python scripts/verificar_alertas_compras.py
```

#### Agendamento Automático (Windows)
```bash
# Execute como administrador
scripts/agendar_verificacoes.bat
```

#### Agendamento Automático (Linux/Mac)
```bash
# Adicione ao crontab
# Verificação diária às 08:00
0 8 * * * /path/to/python /path/to/scripts/verificar_alertas_compras.py

# Verificação semanal às segundas-feiras às 09:00
0 9 * * 1 /path/to/python /path/to/scripts/verificar_alertas_compras.py
```

## API Endpoints

### Status das Notificações
```
GET /compras/api/notificacoes/status
```
Retorna status atual de todos os alertas.

### Teste de Notificações
```
POST /compras/notificacoes/testar
Content-Type: application/json

{
    "tipo_teste": "orcamento_excedido" | "orcamento_proximo_limite" | "compras_pendentes" | "prestacoes_atrasadas"
}
```

## Templates de Email

Os emails são enviados em formato HTML responsivo com as seguintes informações:

### Orçamento Excedido
- Nome do polo
- Valor do orçamento vs valor gasto
- Percentual utilizado
- Período do orçamento
- Ações recomendadas

### Orçamento Próximo ao Limite
- Nome do polo
- Valor restante
- Percentual utilizado
- Recomendações preventivas

### Compras Pendentes
- Lista de compras pendentes
- Número de dias pendente
- Informações da compra (fornecedor, valor, data)

### Prestações Atrasadas
- Lista de prestações em atraso
- Número de dias de atraso
- Informações da compra

## Logs e Monitoramento

### Arquivos de Log
- `logs/alertas_compras.log`: Log das verificações automáticas
- Log da aplicação principal: Erros e informações gerais

### Monitoramento
- Dashboard em tempo real na interface web
- Métricas de alertas ativos
- Status detalhado por polo

## Solução de Problemas

### Emails não estão sendo enviados
1. Verifique as credenciais do Mailjet
2. Confirme que os usuários têm emails válidos
3. Verifique os logs para erros específicos

### Alertas não estão sendo detectados
1. Verifique se os orçamentos estão configurados corretamente
2. Confirme que as compras estão associadas aos polos corretos
3. Verifique as datas dos orçamentos

### Verificação automática não está funcionando
1. Confirme que as tarefas agendadas estão ativas
2. Verifique permissões de execução dos scripts
3. Confirme que o ambiente Python está configurado corretamente

## Segurança

- Apenas administradores podem configurar notificações
- Emails contêm apenas informações necessárias (sem dados sensíveis)
- Logs não registram informações pessoais
- Credenciais de email são armazenadas como variáveis de ambiente

## Personalização

### Modificar Templates de Email
Edite os métodos `_get_template_*` em `services/compra_notification_service.py`

### Alterar Critérios de Alerta
Modifique as constantes nos métodos de verificação:
- Dias para compras pendentes: linha ~75
- Dias para prestações atrasadas: linha ~95
- Percentual para orçamento próximo ao limite: linha ~60

### Adicionar Novos Tipos de Alerta
1. Crie novo método de verificação em `CompraNotificationService`
2. Adicione template de email correspondente
3. Inclua na verificação principal (`verificar_alertas_criticos`)
4. Adicione opção de teste na interface web