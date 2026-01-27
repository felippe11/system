# Atividades com Múltiplas Datas

Este documento descreve a funcionalidade de atividades com múltiplas datas implementada no sistema.

## Visão Geral

A funcionalidade de atividades com múltiplas datas permite que organizadores criem atividades que ocorrem em várias datas diferentes, com controle de frequência e check-in para cada data específica.

## Funcionalidades Principais

### 1. Criação de Atividades
- **Título e Descrição**: Informações básicas da atividade
- **Tipo de Atividade**: Oficina, Palestra, Workshop, Curso, Seminário, etc.
- **Carga Horária Total**: Horas totais da atividade
- **Localização**: Estado e cidade
- **Múltiplas Datas**: Adicionar várias datas com horários específicos
- **Palavras-chave**: Para check-in em cada turno (manhã/tarde)
- **Configurações**: Check-in múltiplo, lista de frequência, presença obrigatória

### 2. Gestão de Datas
- **Datas Específicas**: Cada atividade pode ter várias datas
- **Horários**: Início e fim para cada data
- **Carga Horária por Data**: Distribuição automática ou manual
- **Palavras-chave**: Diferentes para manhã e tarde
- **Observações**: Notas específicas para cada data

### 3. Sistema de Check-in
- **Check-in por Data**: Participantes fazem check-in em cada data
- **Turnos**: Manhã, tarde ou dia inteiro
- **Validação**: Palavras-chave para confirmar presença
- **Controle de Duplicidade**: Evita check-ins repetidos no mesmo turno
- **Dados Adicionais**: IP, User-Agent, timestamp

### 4. Lista de Frequência
- **Controle por Data**: Frequência registrada para cada data
- **Status de Presença**: Presente, ausente, parcial
- **Carga Horária Presenciada**: Cálculo automático baseado na presença
- **Relatórios**: Visualização e exportação em PDF
- **Estatísticas**: Resumos por data e geral

### 5. Certificados
- **Integração**: Atividades incluídas no cálculo de certificados
- **Carga Horária**: Considera apenas horas presenciadas
- **Critérios**: Configurável para presença obrigatória em todas as datas

## Modelos de Dados

### AtividadeMultiplaData
- `id`: Identificador único
- `titulo`: Nome da atividade
- `descricao`: Descrição detalhada
- `carga_horaria_total`: Horas totais da atividade
- `tipo_atividade`: Tipo (oficina, palestra, etc.)
- `permitir_checkin_multiplas_datas`: Se permite check-in
- `gerar_lista_frequencia`: Se gera lista de frequência
- `exigir_presenca_todas_datas`: Se exige presença em todas as datas
- `estado`, `cidade`: Localização
- `cliente_id`, `evento_id`: Relacionamentos

### AtividadeData
- `id`: Identificador único
- `atividade_id`: Referência à atividade
- `data`: Data específica
- `horario_inicio`, `horario_fim`: Horários
- `palavra_chave_manha`, `palavra_chave_tarde`: Palavras para check-in
- `carga_horaria_data`: Horas desta data específica
- `observacoes`: Notas adicionais

### FrequenciaAtividade
- `id`: Identificador único
- `atividade_id`, `data_atividade_id`, `usuario_id`: Relacionamentos
- `presente_manha`, `presente_tarde`, `presente_dia_inteiro`: Status de presença
- `data_checkin_manha`, `data_checkin_tarde`: Timestamps dos check-ins
- `palavra_chave_usada_manha`, `palavra_chave_usada_tarde`: Palavras utilizadas

### CheckinAtividade
- `id`: Identificador único
- `atividade_id`, `data_atividade_id`, `usuario_id`: Relacionamentos
- `data_hora`: Timestamp do check-in
- `palavra_chave`: Palavra utilizada
- `turno`: Manhã, tarde ou dia inteiro
- `ip_address`, `user_agent`: Dados adicionais

## Rotas da API

### Gestão de Atividades
- `GET /atividades_multiplas` - Lista atividades
- `GET /atividades_multiplas/nova` - Formulário de nova atividade
- `POST /atividades_multiplas/nova` - Cria nova atividade
- `GET /atividades_multiplas/<id>` - Visualiza atividade
- `GET /atividades_multiplas/<id>/editar` - Formulário de edição
- `POST /atividades_multiplas/<id>/editar` - Atualiza atividade
- `POST /atividades_multiplas/<id>/excluir` - Exclui atividade

### Check-in
- `GET /atividades_multiplas/<id>/checkin` - Formulário de check-in
- `POST /atividades_multiplas/<id>/checkin` - Processa check-in

### Frequência
- `GET /atividades_multiplas/<id>/frequencia` - Lista de frequência
- `GET /atividades_multiplas/<id>/frequencia/pdf` - PDF da frequência

### API Endpoints
- `GET /api/atividades_multiplas/<id>/datas` - Datas da atividade
- `GET /api/atividades_multiplas/<id>/frequencia/<data_id>` - Frequência por data

## Templates

### Estrutura de Templates
```
templates/atividade_multipla/
├── base.html                    # Template base
├── lista_atividades.html        # Lista de atividades
├── nova_atividade.html          # Formulário de criação
├── visualizar_atividade.html    # Detalhes da atividade
├── editar_atividade.html        # Formulário de edição
├── checkin_atividade.html       # Formulário de check-in
└── lista_frequencia.html        # Lista de frequência
```

### Características dos Templates
- **Design Responsivo**: Adaptável a diferentes tamanhos de tela
- **Interface Intuitiva**: Fácil navegação e uso
- **Validação Client-side**: JavaScript para validações
- **Feedback Visual**: Mensagens de sucesso/erro
- **Componentes Reutilizáveis**: Cards, badges, tabelas

## Serviços

### PDFFrequenciaService
- Geração de PDFs de listas de frequência
- Estilos personalizados
- Estatísticas por data
- Resumo geral da atividade

### Integração com Certificados
- Cálculo de carga horária incluindo atividades múltiplas
- Verificação de critérios de presença
- Geração automática de certificados

## Configuração

### Registro de Rotas
```python
from config.atividade_multipla_config import register_atividade_multipla_routes
register_atividade_multipla_routes(app)
```

### Menu de Navegação
```python
from config.atividade_multipla_config import get_atividade_multipla_menu_items
menu_items = get_atividade_multipla_menu_items()
```

## Migração do Banco de Dados

Execute a migração para criar as novas tabelas:
```bash
flask db upgrade
```

## Permissões

- **Cliente**: Acesso completo às suas atividades
- **Admin**: Acesso a todas as atividades
- **Participante**: Apenas check-in em atividades permitidas

## Exemplos de Uso

### 1. Criar uma Oficina de 3 Dias
1. Acesse "Atividades com Múltiplas Datas"
2. Clique em "Nova Atividade"
3. Preencha título: "Oficina de Programação Web"
4. Selecione tipo: "Oficina"
5. Carga horária: "24"
6. Adicione 3 datas com horários
7. Configure palavras-chave para cada turno
8. Salve a atividade

### 2. Realizar Check-in
1. Acesse a atividade
2. Clique em "Check-in"
3. Selecione a data
4. Escolha o turno
5. Digite a palavra-chave
6. Confirme o check-in

### 3. Gerar Lista de Frequência
1. Acesse a atividade
2. Clique em "Frequência"
3. Visualize a lista por data
4. Clique em "Baixar PDF" para exportar

## Considerações Técnicas

### Performance
- Índices criados para consultas frequentes
- Lazy loading para relacionamentos
- Paginação em listas grandes

### Segurança
- Validação de permissões em todas as rotas
- Sanitização de dados de entrada
- Proteção contra CSRF

### Escalabilidade
- Estrutura modular
- Separação de responsabilidades
- Fácil extensão para novas funcionalidades

## Troubleshooting

### Problemas Comuns
1. **Erro de permissão**: Verifique se o usuário tem acesso de cliente
2. **Check-in duplicado**: Sistema impede check-ins repetidos no mesmo turno
3. **PDF não gera**: Verifique se há dados de frequência registrados
4. **Certificado não inclui atividade**: Verifique se a atividade está vinculada ao evento

### Logs
- Logs de check-in em `checkin_atividade`
- Logs de erro em `services/pdf_frequencia_service.py`
- Logs de certificado em `services/certificado_service.py`
