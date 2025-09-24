# Sistema de Business Intelligence (BI)

## Visão Geral

O Sistema de Business Intelligence foi desenvolvido para fornecer análises avançadas, relatórios personalizados e dashboards interativos para o sistema de eventos e oficinas. Ele oferece insights estratégicos baseados em dados reais para tomada de decisão.

## Funcionalidades Principais

### 📊 Dashboard Principal
- **KPIs em Tempo Real**: Indicadores atualizados automaticamente
- **Alertas Inteligentes**: Notificações baseadas em métricas configuráveis
- **Dashboards Personalizados**: Criação de visões customizadas
- **Análises Rápidas**: Acesso direto a análises específicas

### 📈 Relatórios Avançados
- **Relatórios Executivos**: Visão estratégica para tomada de decisão
- **Relatórios Operacionais**: Análise detalhada de processos
- **Relatórios Financeiros**: Insights sobre receita e custos
- **Relatórios de Qualidade**: Análise de satisfação e feedback

### 🎛️ Dashboards Personalizados
- **Widgets Interativos**: Gráficos, tabelas, KPIs e mapas
- **Layout Flexível**: Arrastar e soltar para organizar widgets
- **Filtros Dinâmicos**: Aplicar filtros em tempo real
- **Exportação**: Salvar dashboards em PDF, Excel, CSV ou JSON

### 📊 Análises Especializadas
- **Análise de Tendências**: Evolução temporal dos dados
- **Análise Geográfica**: Distribuição por localização
- **Análise de Qualidade**: Satisfação e feedback dos participantes
- **Análise Financeira**: Receita, custos e projeções

## Estrutura Técnica

### Modelos de Dados

#### RelatorioBI
```python
- id: Identificador único
- nome: Nome do relatório
- descricao: Descrição detalhada
- tipo_relatorio: 'executivo', 'operacional', 'financeiro', 'qualidade'
- cliente_id: Cliente proprietário
- usuario_criador_id: Usuário que criou
- filtros_aplicados: JSON com filtros
- periodo_inicio/fim: Período de análise
- dados_relatorio: JSON com dados
- metricas_calculadas: JSON com métricas
- status: 'ativo', 'arquivado', 'excluido'
```

#### MetricaBI
```python
- id: Identificador único
- nome: Nome da métrica
- descricao: Descrição da métrica
- categoria: 'vendas', 'participacao', 'qualidade', 'financeiro'
- tipo_metrica: 'contador', 'percentual', 'monetario', 'tempo'
- formula: SQL ou descrição da fórmula
- cor: Cor hexadecimal para exibição
- icone: Ícone FontAwesome
- unidade: Unidade de medida
```

#### DashboardBI
```python
- id: Identificador único
- nome: Nome do dashboard
- descricao: Descrição do dashboard
- cliente_id: Cliente proprietário
- usuario_criador_id: Usuário que criou
- layout_config: JSON com configuração do layout
- widgets_config: JSON com configuração dos widgets
- filtros_padrao: JSON com filtros padrão
- publico: Se é público ou privado
- usuarios_permitidos: JSON com IDs de usuários permitidos
```

### Serviços

#### BIAnalyticsService
- **calcular_kpis_executivos()**: Calcula KPIs principais
- **gerar_analise_tendencias()**: Análise de tendências temporais
- **gerar_analise_geografica()**: Análise por localização
- **gerar_analise_qualidade()**: Análise de satisfação
- **gerar_analise_financeira()**: Análise financeira
- **gerar_relatorio_personalizado()**: Gera relatório customizado
- **executar_alertas_bi()**: Executa verificação de alertas

#### RelatorioExportService
- **exportar_relatorio_pdf()**: Exporta para PDF
- **exportar_relatorio_xlsx()**: Exporta para Excel
- **exportar_relatorio_csv()**: Exporta para CSV
- **exportar_relatorio_json()**: Exporta para JSON
- **exportar_dashboard_pdf()**: Exporta dashboard para PDF

### Rotas

#### Dashboard e Relatórios
- `GET /bi/dashboard` - Dashboard principal
- `GET /bi/relatorios` - Lista de relatórios
- `GET /bi/relatorios/novo` - Criar novo relatório
- `GET /bi/relatorios/<id>` - Visualizar relatório
- `POST /bi/relatorios/<id>/exportar` - Exportar relatório

#### Dashboards Personalizados
- `GET /bi/dashboards` - Lista de dashboards
- `GET /bi/dashboards/novo` - Criar novo dashboard
- `GET /bi/dashboards/<id>` - Visualizar dashboard
- `POST /bi/dashboards/<id>/exportar` - Exportar dashboard

#### Análises Especializadas
- `GET /bi/analises/tendencias` - Análise de tendências
- `GET /bi/analises/geografia` - Análise geográfica
- `GET /bi/analises/qualidade` - Análise de qualidade
- `GET /bi/analises/financeira` - Análise financeira

#### APIs
- `GET /api/bi/kpis` - KPIs em tempo real
- `GET /api/bi/tendencias` - Dados de tendências
- `GET /api/bi/alertas` - Alertas ativos
- `GET /api/bi/metricas` - Métricas disponíveis
- `GET /api/bi/widgets` - Widgets disponíveis

## Configuração e Instalação

### 1. Dependências
```bash
pip install reportlab openpyxl pandas
```

### 2. Migração do Banco
```bash
flask db upgrade
```

### 3. Inicialização do Sistema
```bash
python scripts/init_bi_system.py
```

### 4. Registro das Rotas
```python
from config.relatorio_bi_config import register_bi_routes
register_bi_routes(app)
```

## Uso do Sistema

### Criando um Relatório

1. **Acesse** `/bi/relatorios/novo`
2. **Preencha** os dados básicos:
   - Nome do relatório
   - Descrição
   - Tipo (executivo, operacional, financeiro, qualidade)
   - Período de análise
3. **Configure** os filtros desejados
4. **Salve** o relatório

### Criando um Dashboard

1. **Acesse** `/bi/dashboards/novo`
2. **Configure** o layout arrastando widgets
3. **Selecione** as métricas para cada widget
4. **Personalize** cores e configurações
5. **Salve** o dashboard

### Configurando Alertas

1. **Acesse** as configurações de métricas
2. **Defina** condições de alerta:
   - Tipo: limite, tendência, anomalia, meta
   - Condição: maior, menor, igual, diferente
   - Valor limite
   - Período de verificação
3. **Configure** usuários e canais de notificação
4. **Ative** o alerta

## Métricas Disponíveis

### Participação
- **Inscrições Totais**: Número total de inscrições
- **Usuários Únicos**: Número de usuários únicos
- **Taxa de Conversão**: Percentual de conversão
- **Taxa de Presença**: Percentual de presença

### Financeiro
- **Receita Total**: Valor total arrecadado
- **Ticket Médio**: Valor médio por participante
- **Taxa de Inadimplência**: Percentual de inadimplência
- **Crescimento de Receita**: Variação percentual

### Qualidade
- **Satisfação Média**: Nota média de satisfação
- **NPS**: Net Promoter Score
- **Taxa de Recomendação**: Percentual que recomendaria
- **Feedback Positivo**: Percentual de feedback positivo

## Widgets Disponíveis

### Gráficos
- **Linha**: Tendências temporais
- **Barras**: Comparações categóricas
- **Pizza**: Distribuições percentuais
- **Donut**: Distribuições com centro vazio
- **Gauge**: Indicadores de performance

### Tabelas
- **Tabela Simples**: Dados tabulares
- **Tabela com Filtros**: Dados filtráveis
- **Tabela Pivot**: Dados agrupados

### KPIs
- **Card Simples**: Valor único
- **Card com Comparação**: Valor com variação
- **Card com Gráfico**: Valor com mini-gráfico

### Mapas
- **Mapa de Calor**: Densidade geográfica
- **Mapa de Pontos**: Localizações específicas
- **Mapa de Regiões**: Dados por região

## Exportação

### Formatos Suportados
- **PDF**: Relatórios profissionais
- **Excel (XLSX)**: Dados tabulares editáveis
- **CSV**: Dados para importação
- **JSON**: Dados estruturados

### Configurações de Exportação
- **Filtros**: Aplicar filtros específicos
- **Período**: Definir período de exportação
- **Formato**: Personalizar layout e cores
- **Dados**: Selecionar métricas específicas

## Performance e Cache

### Sistema de Cache
- **Duração**: 1 hora por padrão
- **Tipos**: KPIs, gráficos, tabelas
- **Invalidação**: Automática por tempo
- **Limpeza**: Automática de registros expirados

### Otimizações
- **Índices**: Criados para consultas frequentes
- **Agregações**: Cálculos pré-computados
- **Paginação**: Dados paginados para grandes volumes
- **Lazy Loading**: Carregamento sob demanda

## Segurança

### Controle de Acesso
- **Permissões**: Baseadas em tipo de usuário
- **Isolamento**: Dados por cliente
- **Auditoria**: Log de todas as ações
- **Validação**: Validação de entrada rigorosa

### Proteção de Dados
- **Criptografia**: Dados sensíveis criptografados
- **Backup**: Backup automático de configurações
- **Versionamento**: Controle de versões de relatórios
- **Retenção**: Política de retenção de dados

## Monitoramento

### Alertas do Sistema
- **Performance**: Tempo de resposta
- **Erros**: Falhas de processamento
- **Capacidade**: Uso de recursos
- **Segurança**: Tentativas de acesso

### Métricas de Uso
- **Relatórios**: Mais acessados
- **Dashboards**: Mais utilizados
- **Exportações**: Frequência de exportação
- **Usuários**: Atividade por usuário

## Troubleshooting

### Problemas Comuns

#### Relatórios não carregam
1. Verificar permissões do usuário
2. Verificar se o cliente tem dados
3. Verificar logs de erro
4. Limpar cache do sistema

#### Gráficos não aparecem
1. Verificar se Chart.js está carregado
2. Verificar dados da métrica
3. Verificar configuração do widget
4. Verificar console do navegador

#### Exportação falha
1. Verificar espaço em disco
2. Verificar permissões de escrita
3. Verificar tamanho dos dados
4. Verificar logs de exportação

### Logs Importantes
- **Aplicação**: `logs/app.log`
- **Erros**: `logs/error.log`
- **BI**: `logs/bi.log`
- **Exportação**: `logs/export.log`

## Roadmap

### Próximas Funcionalidades
- **Machine Learning**: Análises preditivas
- **Real-time**: Atualizações em tempo real
- **Mobile**: App móvel para dashboards
- **Integração**: APIs externas

### Melhorias Planejadas
- **Performance**: Otimizações de consulta
- **UX**: Interface mais intuitiva
- **Relatórios**: Mais tipos de relatório
- **Alertas**: Mais tipos de alerta

## Suporte

### Documentação
- **API**: Documentação completa da API
- **Guia do Usuário**: Manual passo a passo
- **FAQ**: Perguntas frequentes
- **Tutoriais**: Vídeos e exemplos

### Contato
- **Email**: suporte@empresa.com
- **Chat**: Sistema de chat integrado
- **Ticket**: Sistema de tickets
- **Telefone**: (11) 99999-9999

---

**Versão**: 1.0.0  
**Última Atualização**: Janeiro 2024  
**Autor**: Sistema de BI Team
