# Sistema de Lembretes de Oficinas

## Visão Geral

O sistema de lembretes permite que clientes enviem notificações automáticas ou manuais para participantes inscritos em oficinas. Os lembretes podem ser configurados para envio imediato ou agendado com base em critérios específicos.

## Funcionalidades

### 1. Tipos de Lembrete

#### Manual
- Envio imediato após criação
- Controle total pelo usuário
- Ideal para comunicações urgentes

#### Automático
- Agendamento baseado em dias de antecedência
- Agendamento para data/hora específica
- Execução automática pelo sistema

### 2. Destinatários

#### Todas as Oficinas
- Envia para todos os participantes de todas as oficinas do cliente
- Opção mais ampla de alcance

#### Oficinas Específicas
- Seleção de oficinas específicas
- Controle granular sobre destinatários

#### Usuários Específicos
- Seleção individual de usuários
- Máximo controle sobre quem recebe

### 3. Configurações Automáticas

#### Dias de Antecedência
- Define quantos dias antes da oficina enviar o lembrete
- Exemplo: 3 dias antes = lembrete enviado 3 dias antes da data da oficina

#### Data/Hora Específica
- Agendamento para momento exato
- Sobrescreve configuração de dias de antecedência
- Formato: YYYY-MM-DD HH:MM

## Estrutura do Banco de Dados

### Tabela: lembrete_oficina
```sql
- id: Chave primária
- cliente_id: ID do cliente proprietário
- titulo: Título do lembrete
- mensagem: Conteúdo da mensagem
- tipo: 'manual' ou 'automatico'
- status: 'pendente', 'enviado', 'falhou', 'cancelado'
- dias_antecedencia: Dias antes da oficina (automático)
- data_envio_agendada: Data/hora específica (automático)
- enviar_todas_oficinas: Boolean para todas as oficinas
- oficina_ids: JSON com IDs das oficinas selecionadas
- usuario_ids: JSON com IDs dos usuários selecionados
- data_criacao: Data de criação
- data_envio: Data de envio efetivo
- total_destinatarios: Total de destinatários
- total_enviados: Total de emails enviados
- total_falhas: Total de falhas no envio
```

### Tabela: lembrete_envio
```sql
- id: Chave primária
- lembrete_id: ID do lembrete pai
- usuario_id: ID do usuário destinatário
- oficina_id: ID da oficina relacionada
- status: Status do envio individual
- data_envio: Data do envio individual
- erro_mensagem: Mensagem de erro (se houver)
```

## Arquivos do Sistema

### Modelos
- `models/reminder.py`: Definição dos modelos de dados

### Rotas
- `routes/reminder_routes.py`: Endpoints da API REST

### Templates
- `templates/lembretes/listar.html`: Lista de lembretes
- `templates/lembretes/criar.html`: Formulário de criação
- `templates/lembretes/visualizar.html`: Detalhes do lembrete

### Serviços
- `services/email_service.py`: Serviço de envio de emails
- `services/reminder_scheduler.py`: Sistema de agendamento automático

### Migração
- `migrations/add_reminder_tables.py`: Script para criar tabelas

## Como Usar

### 1. Acesso
- Navegue para o dashboard do cliente
- Clique na aba "Gerenciar"
- Clique no card "Lembretes"

### 2. Criar Lembrete
1. Clique em "Novo Lembrete"
2. Preencha título e mensagem
3. Escolha tipo (Manual ou Automático)
4. Configure destinatários
5. Para automático: defina dias de antecedência ou data específica
6. Clique em "Criar Lembrete"

### 3. Gerenciar Lembretes
- **Listar**: Visualize todos os lembretes
- **Visualizar**: Veja detalhes e estatísticas
- **Enviar**: Envie lembretes manuais pendentes
- **Cancelar**: Cancele lembretes automáticos
- **Deletar**: Remova lembretes permanentemente

## Configuração de Email

O sistema utiliza as configurações de email do Flask:
```python
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USERNAME = 'seu-email@gmail.com'
MAIL_PASSWORD = 'sua-senha'
MAIL_USE_TLS = True
```

## Sistema de Agendamento

### Scheduler Automático
- Executa a cada hora (minuto 0)
- Verifica lembretes automáticos pendentes
- Processa envios baseados em critérios

### Jobs Agendados
- Lembretes com data específica: job único
- Lembretes com dias de antecedência: job por oficina
- Cancelamento automático ao cancelar lembrete

## Monitoramento

### Status do Scheduler
- Endpoint: `/api/scheduler-status`
- Retorna status e jobs agendados
- Útil para diagnóstico

### Logs
- Todas as operações são logadas
- Nível INFO para operações normais
- Nível ERROR para falhas

## Segurança

### Controle de Acesso
- Apenas clientes podem gerenciar seus lembretes
- Verificação de permissão em todas as operações
- Isolamento por cliente_id

### Validação
- Validação de dados de entrada
- Sanitização de mensagens HTML
- Verificação de limites (dias de antecedência: 1-30)

## Troubleshooting

### Problemas Comuns

1. **Emails não enviados**
   - Verificar configurações SMTP
   - Verificar logs de erro
   - Testar conectividade

2. **Lembretes automáticos não executam**
   - Verificar status do scheduler
   - Verificar logs do sistema
   - Verificar configurações de data

3. **Tabelas não existem**
   - Executar script de migração
   - Verificar permissões do banco
   - Verificar logs de criação

### Comandos Úteis

```bash
# Executar migração
python migrations/add_reminder_tables.py

# Verificar status do scheduler
curl http://localhost:5000/api/scheduler-status

# Ver logs do sistema
tail -f logs/app.log
```

## Desenvolvimento

### Adicionar Novos Tipos de Lembrete
1. Atualizar enum `TipoLembrete`
2. Modificar lógica de processamento
3. Atualizar templates

### Personalizar Templates de Email
1. Editar `EmailService.enviar_lembrete_oficina`
2. Modificar HTML e CSS
3. Testar em diferentes clientes de email

### Adicionar Novos Destinatários
1. Estender `obter_destinatarios_lembrete`
2. Adicionar campos de filtro
3. Atualizar interface de seleção
