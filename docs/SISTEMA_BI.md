# Sistema de Business Intelligence (BI)

## Visão Geral

O Sistema de Business Intelligence foi desenvolvido para fornecer análises avançadas e dashboards interativos para o sistema de eventos. Ele permite criar relatórios personalizados, dashboards com widgets arrastáveis e exportação em múltiplos formatos.

## Funcionalidades Principais

### 1. Dashboard Principal
- **Localização**: `/bi/dashboard`
- **Funcionalidade**: Visão geral com KPIs executivos e navegação rápida
- **Recursos**:
  - KPIs principais (inscrições, presença, receita, satisfação)
  - 9 visões analíticas diferentes
  - Filtros globais por período e evento
  - Exportação em PDF, Excel, CSV

### 2. Relatórios Avançados
- **Localização**: `/bi/relatorios`
- **Funcionalidade**: Criação e gerenciamento de relatórios personalizados
- **Tipos de Relatório**:
  - **Executivo**: Visão estratégica com KPIs principais
  - **Operacional**: Análise de processos e eficiência
  - **Financeiro**: Análise de receita, custos e indicadores
  - **Qualidade**: Satisfação, feedback e NPS

### 3. Dashboards Interativos
- **Localização**: `/bi/dashboards`
- **Funcionalidade**: Criação de dashboards com widgets arrastáveis
- **Widgets Disponíveis**:
  - **KPI Cards**: Valores únicos com comparação
  - **Gráficos**: Linha, barras, pizza, donut
  - **Tabelas**: Dados tabulares com filtros
  - **Gauges**: Indicadores visuais

### 4. Sistema de Cache
- **Funcionalidade**: Cache inteligente para performance
- **Configuração**: Expiração automática em 60 minutos
- **Benefícios**: Redução de carga no banco de dados

### 5. Alertas Inteligentes
- **Funcionalidade**: Notificações baseadas em métricas
- **Canais**: Email, Slack (configurável)
- **Frequências**: Diário, semanal, mensal

## Estrutura de Arquivos

```
models/
├── relatorio_bi.py          # Modelos do BI
services/
├── bi_analytics_service.py  # Lógica de análise
├── relatorio_export_service.py # Exportação
routes/
├── relatorio_bi_routes.py  # Rotas da API
templates/relatorio_bi/
├── base.html               # Template base
├── dashboard_principal.html # Dashboard principal
├── visualizar_relatorio.html # Visualização de relatórios
├── criar_relatorio.html    # Criação de relatórios
├── criar_dashboard.html    # Criação de dashboards
├── visualizar_dashboard.html # Visualização de dashboards
├── lista_relatorios.html  # Lista de relatórios
├── lista_dashboards.html  # Lista de dashboards
├── editar_relatorio.html   # Edição de relatórios
└── editar_dashboard.html   # Edição de dashboards
```

## Instalação e Configuração

### 1. Executar Migração
```bash
flask db migrate -m "Add BI tables"
flask db upgrade
```

### 2. Popular Métricas Padrão
```bash
python scripts/popular_metricas_bi.py
```

### 3. Configurar Rotas
As rotas já estão registradas em `routes/__init__.py`:
```python
from .relatorio_bi_routes import relatorio_bi_routes
app.register_blueprint(relatorio_bi_routes)
```

## Uso do Sistema

### Acessando o BI
1. No dashboard do cliente, aba "Criar Novo"
2. Clique no card "Business Intelligence"
3. Escolha entre:
   - **Dashboard BI**: Visão geral
   - **Relatórios**: Criação de relatórios
   - **Dashboards**: Criação de dashboards

### Criando um Relatório
1. Acesse `/bi/relatorios/criar`
2. Preencha as informações básicas
3. Configure filtros avançados
4. Use o preview para validar
5. Salve o relatório

### Criando um Dashboard
1. Acesse `/bi/dashboards/criar`
2. Arraste widgets da paleta
3. Configure cada widget
4. Teste o layout
5. Salve o dashboard

## Métricas Disponíveis

### Métricas Executivas
- `inscricoes_totais`: Total de inscrições
- `usuarios_unicos`: Usuários únicos
- `checkins_total`: Total de check-ins
- `taxa_presenca`: Taxa de presença
- `receita_total`: Receita total
- `ticket_medio`: Valor médio por inscrição

### Métricas de Qualidade
- `satisfacao_media`: Nota média de satisfação
- `nps_score`: Net Promoter Score
- `certificados_gerados`: Certificados emitidos

### Métricas Operacionais
- `taxa_conversao`: Conversão de visitantes
- `ocupacao_media`: Taxa de ocupação
- `tempo_medio_checkin`: Tempo médio de check-in

## Visões Analíticas

### 1. Visão Executiva
- KPIs principais
- Tendências mensais
- Alertas importantes
- Satisfação média

### 2. Visão Funil
- Conversão por etapa
- Taxa de abandono
- Pontos de melhoria

### 3. Visão Ocupação
- Capacidade por atividade
- Gargalos identificados
- Agenda otimizada

### 4. Visão Presença
- Taxa de presença por atividade
- Análise de faltas
- Retenção de participantes

### 5. Visão Qualidade
- Distribuição de avaliações
- NPS Score
- Feedback qualitativo

### 6. Visão Financeiro
- Receita por período
- Ticket médio
- Crescimento mensal

### 7. Visão Certificados
- Emissão automática
- Taxa de download
- Tempo de processamento

### 8. Visão Operação
- Eficiência de processos
- Segurança do sistema
- Logs de auditoria

### 9. Visão Diversidade
- Inclusão e acessibilidade
- Distribuição demográfica
- ODS relacionados

### 10. Visão Geografia
- Análise por localização
- Ranking de cidades
- Satisfação regional

## Exportação

### Formatos Suportados
- **PDF**: Relatórios formatados com gráficos
- **Excel (XLSX)**: Dados tabulares com formatação
- **CSV**: Dados brutos para análise
- **JSON**: Dados estruturados para APIs

### Configurações de Exportação
- Incluir/excluir gráficos
- Período personalizado
- Filtros aplicados
- Formatação profissional

## Performance e Cache

### Sistema de Cache
- **Chave**: Hash dos filtros + tipo de relatório
- **Expiração**: 60 minutos (configurável)
- **Armazenamento**: Banco de dados
- **Limpeza**: Automática por expiração

### Otimizações
- Queries otimizadas com índices
- Agregações pré-calculadas
- Paginação de resultados
- Lazy loading de widgets

## Segurança

### Controle de Acesso
- Autenticação obrigatória
- Autorização por cliente
- Dashboards públicos/privados
- Links de compartilhamento com expiração

### Proteção de Dados
- Sanitização de inputs
- Validação de filtros
- Logs de auditoria
- Backup automático

## Troubleshooting

### Problemas Comuns

#### 1. Erro de Importação
```
ImportError: No module named 'relatorio_bi_routes'
```
**Solução**: Verificar se o arquivo existe e está no path correto

#### 2. Erro de Banco de Dados
```
Table 'relatorio_bi' doesn't exist
```
**Solução**: Executar migração do banco de dados

#### 3. Cache Não Funcionando
**Solução**: Verificar configuração de cache e limpar cache manualmente

#### 4. Widgets Não Carregam
**Solução**: Verificar JavaScript e console do navegador

### Logs e Debug
- Logs em `logs/bi_system.log`
- Debug mode: `DEBUG=True`
- Console do navegador para erros JS

## Roadmap Futuro

### Próximas Funcionalidades
- [ ] Machine Learning para previsões
- [ ] Integração com APIs externas
- [ ] Relatórios agendados
- [ ] Notificações push
- [ ] Análise de sentimento
- [ ] Comparação entre eventos
- [ ] Benchmarking de mercado

### Melhorias Técnicas
- [ ] Cache Redis
- [ ] Processamento assíncrono
- [ ] API GraphQL
- [ ] Microserviços
- [ ] Containerização

## Suporte

Para suporte técnico ou dúvidas sobre o sistema de BI:
- Documentação: `/docs/SISTEMA_BI.md`
- Logs: `logs/bi_system.log`
- Issues: GitHub Issues
- Email: suporte@empresa.com