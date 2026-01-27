# Sistema de Votação - AppFiber

## Visão Geral

O Sistema de Votação do AppFiber permite que organizadores de eventos criem votações para trabalhos submetidos, com categorias personalizáveis, perguntas específicas e resultados em tempo real. O sistema integra-se completamente com o sistema existente de submissão e avaliação de trabalhos.

## Funcionalidades Principais

### 1. Cadastro e Configuração

#### Evento de Votação
- **Criação**: Clientes podem criar eventos de votação para seus eventos
- **Configurações**: 
  - Nome e descrição da votação
  - Período de votação (data início/fim)
  - Modo de revelação (imediato ou progressivo)
  - Exibição de resultados em tempo real
  - Permissões de votação (login obrigatório, voto anônimo)

#### Categorias de Votação
- **Categorias personalizáveis**: Ex: "Melhor Apresentação", "Inovação", "Impacto Social"
- **Configurações por categoria**:
  - Nome e descrição
  - Faixa de pontuação (mínima e máxima)
  - Tipo de pontuação (numérica, escala, escolha única)
  - Ordem de exibição

#### Perguntas/Questões
- **Tipos de pergunta**:
  - Numérica (com faixa de valores)
  - Texto livre
  - Escolha única
  - Múltipla escolha
- **Configurações**:
  - Texto da pergunta
  - Observação explicativa
  - Obrigatoriedade
  - Ordem de exibição

### 2. Gerenciamento de Trabalhos

#### Importação de Trabalhos
- **Automática**: Importa todos os trabalhos do evento
- **Manual**: Seleção individual de trabalhos
- **Em lote**: Importação via arquivo
- **Integração**: Conecta com sistema de submissão existente

#### Configurações de Trabalhos
- Título e resumo
- Lista de autores
- Categoria original
- Ordem de exibição
- Status ativo/inativo

### 3. Sistema de Votação

#### Atribuição de Revisores
- **Manual**: Atribuição individual de trabalhos para revisores
- **Automática**: Atribuição em massa
- **Configurações**:
  - Prazo de votação
  - Controle de conclusão
  - Histórico de atribuições

#### Interface de Votação
- **Painel do revisor**: Lista trabalhos atribuídos
- **Formulário de votação**: Interface intuitiva por categoria
- **Validação**: Verificação de campos obrigatórios
- **Salvamento**: Votos salvos automaticamente
- **Finalização**: Controle de conclusão da votação

### 4. Resultados e Rankings

#### Cálculo Automático
- Soma e média das pontuações
- Rankings por categoria
- Posicionamento automático (1º, 2º, 3º lugar)

#### Exibição de Resultados
- **Tempo real**: Atualização automática
- **Modo revelação**: Progressivo (3º → 2º → 1º lugar)
- **Pódio visual**: Representação gráfica dos vencedores
- **Tabelas detalhadas**: Informações completas

#### Exportação
- **PDF**: Relatórios formatados
- **Excel**: Planilhas com dados detalhados
- **Filtros**: Por categoria, período, etc.

## Arquitetura Técnica

### Modelos de Dados

#### VotingEvent
```python
- id: Identificador único
- cliente_id: Cliente proprietário
- evento_id: Evento associado
- nome: Nome da votação
- descricao: Descrição detalhada
- status: configuracao/ativo/finalizado
- data_inicio_votacao: Data de início
- data_fim_votacao: Data de fim
- configurações de exibição e segurança
```

#### VotingCategory
```python
- id: Identificador único
- voting_event_id: Evento de votação
- nome: Nome da categoria
- descricao: Descrição
- pontuacao_minima/maxima: Faixa de valores
- tipo_pontuacao: Tipo de pontuação
- ordem: Ordem de exibição
```

#### VotingQuestion
```python
- id: Identificador único
- category_id: Categoria associada
- texto_pergunta: Texto da pergunta
- observacao_explicativa: Observações
- tipo_resposta: Tipo de resposta
- valor_minimo/maximo: Limites
- obrigatoria: Campo obrigatório
```

#### VotingWork
```python
- id: Identificador único
- voting_event_id: Evento de votação
- submission_id: Trabalho original
- titulo: Título do trabalho
- resumo: Resumo
- autores: Lista de autores
- categoria_original: Categoria original
```

#### VotingAssignment
```python
- id: Identificador único
- voting_event_id: Evento de votação
- revisor_id: Revisor atribuído
- work_id: Trabalho atribuído
- prazo_votacao: Prazo para votação
- concluida: Status de conclusão
```

#### VotingVote
```python
- id: Identificador único
- voting_event_id: Evento de votação
- category_id: Categoria votada
- work_id: Trabalho votado
- revisor_id: Revisor que votou
- pontuacao_final: Pontuação final
- observacoes: Observações do revisor
```

#### VotingResponse
```python
- id: Identificador único
- vote_id: Voto associado
- question_id: Pergunta respondida
- valor_numerico: Valor numérico
- texto_resposta: Resposta em texto
- opcoes_selecionadas: Opções selecionadas
```

#### VotingResult
```python
- id: Identificador único
- voting_event_id: Evento de votação
- category_id: Categoria
- work_id: Trabalho
- pontuacao_total: Pontuação total
- pontuacao_media: Pontuação média
- numero_votos: Número de votos
- posicao_ranking: Posição no ranking
```

### Rotas da API

#### Configuração (Cliente)
- `GET /voting/configurar/<evento_id>`: Página de configuração
- `POST /voting/criar_evento_votacao`: Criar evento de votação
- `GET/POST /voting/categoria/<voting_event_id>`: Gerenciar categorias
- `GET/POST /voting/perguntas/<categoria_id>`: Gerenciar perguntas
- `GET/POST /voting/trabalhos/<voting_event_id>`: Gerenciar trabalhos
- `GET/POST /voting/atribuir_revisores/<voting_event_id>`: Atribuir revisores

#### Votação (Revisores)
- `GET /voting/painel_revisor`: Painel do revisor
- `GET /voting/votar/<assignment_id>`: Interface de votação
- `POST /voting/salvar_voto`: Salvar voto
- `POST /voting/finalizar_votacao/<assignment_id>`: Finalizar votação

#### Resultados
- `GET /voting/resultados/<voting_event_id>`: Exibir resultados
- `GET /voting/resultados_tempo_real/<voting_event_id>`: API tempo real
- `GET /voting/exportar_resultados/<voting_event_id>/<formato>`: Exportar

### Serviços

#### VotingService
- `create_voting_event()`: Criar evento de votação
- `import_works_from_submissions()`: Importar trabalhos
- `assign_works_to_reviewers()`: Atribuir revisores
- `save_vote()`: Salvar voto
- `calculate_results()`: Calcular resultados
- `get_reviewer_assignments()`: Buscar atribuições
- `get_voting_statistics()`: Estatísticas

#### VotingWorkService
- `add_work_to_voting()`: Adicionar trabalho

#### VotingCategoryService
- `create_category()`: Criar categoria
- `add_question_to_category()`: Adicionar pergunta

## Integração com Sistema Existente

### Conexão com Submissões
- Utiliza modelo `Submission` existente
- Importa trabalhos automaticamente
- Mantém referência ao trabalho original

### Conexão com Revisores
- Utiliza modelo `Usuario` com tipo 'revisor'
- Integra com sistema de login existente
- Mantém histórico de atividades

### Conexão com Eventos
- Vincula ao modelo `Evento` existente
- Herda configurações do evento
- Mantém isolamento por cliente

## Segurança e Auditoria

### Logs de Auditoria
- Registro de todas as ações importantes
- Rastreamento de IP e User-Agent
- Histórico completo de modificações

### Controle de Acesso
- Verificação de permissões por tipo de usuário
- Isolamento por cliente
- Validação de atribuições

### Validação de Dados
- Verificação de campos obrigatórios
- Validação de faixas de valores
- Sanitização de entradas

## Interface do Usuário

### Templates Criados
- `configurar_votacao.html`: Configuração inicial
- `gerenciar_categorias.html`: Gerenciamento de categorias
- `gerenciar_perguntas.html`: Gerenciamento de perguntas
- `gerenciar_trabalhos.html`: Gerenciamento de trabalhos
- `atribuir_revisores.html`: Atribuição de revisores
- `painel_revisor.html`: Painel do revisor
- `votar.html`: Interface de votação
- `resultados.html`: Exibição de resultados

### Recursos de UX
- Interface responsiva
- Validação em tempo real
- Feedback visual
- Navegação intuitiva
- Modais para ações rápidas

## Instalação e Configuração

### 1. Criar Tabelas
```bash
python create_voting_migration.py
```

### 2. Registrar Rotas
As rotas já estão registradas em `routes/__init__.py`

### 3. Configurar Permissões
- Clientes podem configurar votações
- Revisores podem votar
- Admins têm acesso total

### 4. Testar Funcionalidades
- Criar evento de votação
- Configurar categorias e perguntas
- Importar trabalhos
- Atribuir revisores
- Realizar votação
- Verificar resultados

## Exemplos de Uso

### Cenário 1: Congresso Científico
1. Cliente cria evento de votação para congresso
2. Define categorias: "Melhor Apresentação", "Inovação", "Impacto Social"
3. Cria perguntas específicas para cada categoria
4. Importa todos os trabalhos submetidos
5. Atribui trabalhos para revisores especializados
6. Revisores votam usando interface intuitiva
7. Resultados são exibidos em tempo real
8. Exporta relatórios finais

### Cenário 2: Feira de Ciências
1. Cliente configura votação para feira
2. Define categoria única: "Melhor Projeto"
3. Cria perguntas numéricas (1-10)
4. Importa trabalhos selecionados
5. Atribui todos os trabalhos para todos os revisores
6. Votação acontece durante o evento
7. Resultados são revelados progressivamente
8. Pódio é exibido em telão

## Manutenção e Suporte

### Monitoramento
- Logs de auditoria para rastreamento
- Estatísticas de uso
- Relatórios de erro

### Backup
- Dados críticos em banco de dados
- Logs de auditoria preservados
- Configurações versionadas

### Atualizações
- Migrações de banco de dados
- Versionamento de funcionalidades
- Compatibilidade com sistema existente

## Limitações e Considerações

### Performance
- Cálculo de resultados pode ser custoso com muitos votos
- Atualização em tempo real requer otimização
- Exportação de grandes volumes pode ser lenta

### Escalabilidade
- Sistema suporta múltiplos eventos simultâneos
- Isolamento por cliente garante segurança
- Cálculos são otimizados para grandes volumes

### Segurança
- Validação rigorosa de entradas
- Controle de acesso por tipo de usuário
- Logs de auditoria para rastreamento

## Roadmap Futuro

### Funcionalidades Planejadas
- Votação por pares (peer review)
- Integração com sistema de certificados
- Notificações automáticas
- API REST completa
- Aplicativo mobile

### Melhorias Técnicas
- Cache de resultados
- Otimização de consultas
- Interface mais responsiva
- Testes automatizados

### Integrações
- Sistema de pagamentos
- Plataformas de streaming
- Redes sociais
- Analytics avançados

