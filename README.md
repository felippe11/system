# systemiafaptwo

A Flask-based management system.

## Contribuição

Consulte [AGENTS.md](AGENTS.md) para convenções de código, práticas de commit e requisitos de testes. Siga essas orientações ao colaborar.


## Configuracao

Defina as variaveis de ambiente abaixo antes de iniciar a aplicacao (veja
`\.env.example` para um modelo completo):

```bash
export MAILJET_API_KEY="<sua_api_key>"
export MAILJET_SECRET_KEY="<seu_secret_key>"
export MAIL_DEFAULT_SENDER="seu_email@exemplo.com"
export GOOGLE_CLIENT_ID="<cliente_id_do_google>"
export GOOGLE_CLIENT_SECRET="<cliente_secret_do_google>"
export SECRET_KEY="<sua_chave_secreta>"
export LOG_LEVEL="DEBUG"
export APP_BASE_URL="https://seu-dominio.com"
export RECAPTCHA_PUBLIC_KEY="<sua_chave_publica_recaptcha>"
export RECAPTCHA_PRIVATE_KEY="<sua_chave_privada_recaptcha>"
export DATABASE_URL="postgresql://usuario:senha@host:5432/banco"
export DB_ONLINE="<url_do_banco_online>"
export DB_LOCAL="<url_do_banco_local>"
```

As variáveis `SECRET_KEY`, `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` são **obrigatórias**.
A `SECRET_KEY` deve ser um valor forte e aleatório; a aplicação encerrará a
inicialização caso qualquer uma delas não esteja definida no ambiente. As
chaves do Google são necessárias para a autenticação via Gmail. A variável
`LOG_LEVEL` controla a verbosidade do log e, se não definida, assume `INFO`,
reduzindo o volume de mensagens em produção. Ajuste para `DEBUG` durante o
desenvolvimento para obter logs mais detalhados.

A variável `DATABASE_URL`, quando definida, deve conter a URI completa do
banco de dados e tem precedência sobre as variáveis `DB_USER`, `DB_PASS`,
`DB_HOST`, `DB_PORT` e `DB_NAME`.

## Hash de senhas

As senhas são geradas com `generate_password_hash` utilizando o algoritmo
`pbkdf2:sha256` e 1.000.000 iterações. O valor final tem 103 caracteres e segue
o formato `<algoritmo>:<iterações>$<salt>$<hash>`.

## Banco de Dados

Depois de clonar o repositório ou atualizar o código, instale as dependências
listadas em `requirements.txt` antes de rodar a aplicação ou os testes. Esse
arquivo inclui o `python-dotenv`, usado para carregar automaticamente as
variáveis definidas em `.env`:

```bash
pip install -r requirements.txt
```

Para rodar a suíte de testes ou trabalhar no desenvolvimento, instale também os
pacotes opcionais descritos em `requirements-dev.txt`:

```bash
pip install -r requirements-dev.txt
```

Com o ambiente configurado, gere e aplique as migrações com os comandos abaixo:

```bash
flask db migrate
flask db upgrade
```

Todas as alterações no esquema do banco devem passar por esse fluxo de migrações;
`db.create_all` não é utilizado.

Uma nova revisão `671cbede4123` adiciona os campos `numero_revisores`, `prazo_revisao` e
`modelo_blind` à tabela `reviewer_application`.

`SECRET_KEY` garante que as sessões geradas por uma instância do Flask possam
ser lidas por outra. Em produção, utilize um valor seguro e idêntico em todas as
réplicas do aplicativo.

Essas variáveis substituem o antigo arquivo `credentials.json` utilizado para a
autenticação com a API do Gmail. O envio de e-mails agora é realizado pela
integração com o Mailjet, portanto não é necessário gerar tokens OAuth para o
Gmail.

`APP_BASE_URL` define a URL base para gerar links externos, como o `notification_url` do Mercado Pago. Em desenvolvimento, aponte para um endereço público (ex.: URL do ngrok).

`RECAPTCHA_PUBLIC_KEY` e `RECAPTCHA_PRIVATE_KEY` devem conter as chaves obtidas no [Google reCAPTCHA](https://www.google.com/recaptcha/admin). Sem valores válidos, o CAPTCHA não funcionará em produção.

## Formulários e processo de revisão

Ao criar um formulário ligado ao processo de revisão, utilize o campo
**Evento** para selecionar o evento específico. Quando um processo lida com
múltiplos eventos, essa seleção é obrigatória e define em qual deles o
formulário operará. O vínculo limita o processo ao evento escolhido;
demais eventos não poderão usar esse formulário. Se necessário atender
outros eventos, crie formulários separados para cada um.

## Conflito com pacotes `config`

Alguns ambientes podem ter instalado um pacote externo chamado `config`,
causando importações incorretas. Para verificar qual arquivo está sendo usado no
seu projeto, execute:

```python
import config
print(config.__file__)
```

O caminho exibido deve apontar para o `config.py` deste repositório. Caso seja
outro local, ajuste o `PYTHONPATH` ou remova o pacote conflitante.

## Instalação no Windows/WSL

Siga as etapas abaixo para configurar o projeto no Windows ou dentro do WSL:

1. Instale **Python 3.x** e **Git** a partir dos sites oficiais.
2. Crie e ative um ambiente virtual:

```bash
python -m venv venv
venv\Scripts\activate
```

3. Instale as dependências do projeto:

```bash
pip install -r requirements.txt
```

4. Para executar os testes, instale também as dependências de desenvolvimento:
```bash
pip install -r requirements-dev.txt
```
5. Instale e configure o **PostgreSQL** para Windows ou utilize o serviço Linux pelo WSL.
6. Defina as variáveis de ambiente com `set` ou crie um arquivo `.env` lido pelo `python-dotenv` (pode copiar o arquivo `\.env.example`).
7. Aplique as migrações e inicie o servidor:

```bash
flask db upgrade
python app.py  # ou flask run
```

As instruções para Linux continuam as mesmas dentro do WSL.

## Acessibilidade

Para oferecer acessibilidade em Libras e suporte a pessoas cegas:

- Adicione o plugin [VLibras](https://www.gov.br/governodigital/pt-br/vlibras) antes do fechamento da tag `</body>` em `templates/base.html`:

```html
<div vw class="enabled">
    <div vw-access-button class="active"></div>
    <div vw-plugin-wrapper>
        <div class="vw-plugin-top-wrapper"></div>
    </div>
</div>
<script src="https://vlibras.gov.br/app/vlibras-plugin.js"></script>
<script>new window.VLibras.Widget('https://vlibras.gov.br/app');</script>
```

- Inclua um link "Pular para o conteúdo principal" no início do `<body>` e defina o `id` `main-content` na tag `<main>`:

```html
<a href="#main-content" class="visually-hidden-focusable">Pular para o conteúdo principal</a>
<main id="main-content">
    ...
</main>
```

- Verifique se todas as imagens possuem um texto alternativo significativo (`alt`).

## Formulários

Ao criar um formulário, o campo de seleção de eventos relacionados usa o atributo
`name="eventos[]"` para permitir a seleção múltipla. No back-end, continue
obtendo os IDs selecionados com `request.form.getlist("eventos")`.

## Programacao em PDF

Use a rota `/gerar_folder_evento/<evento_id>` para baixar a programacao do evento no formato de folder. Esta rota gera um PDF em modo paisagem com duas colunas, facilitando a impressao frente e verso.

### Exportar participantes

No dashboard do cliente é possível exportar a lista de inscritos de um evento em dois formatos. Escolha o evento desejado e utilize o botão **Exportar Participantes** para baixar um arquivo XLSX ou PDF contendo os campos padrões e personalizados do cadastro.

### Placas de oficinas

Para sinalizar as atividades de um evento, utilize a rota `/gerar_placas/<evento_id>` ou o botão **Baixar Placas** no dashboard do cliente. Um PDF é gerado com uma página por oficina, contendo título e ministrante.

### Conversão de DOCX para PDF

Relatórios em PDF são gerados a partir de documentos Word usando `docx2pdf`. Caso a conversão falhe, o sistema tenta utilizar `pypandoc` se estiver disponível; do contrário, retorna o arquivo DOCX original. Instale `pypandoc` para habilitar o fallback.

### Impersonação de clientes

Administradores podem acessar o painel de qualquer cliente clicando em **Acessar** na seção de Gestão de Clientes do dashboard. A navegação mostrará um link "Sair do modo cliente" para retornar à conta de administrador.

### Impersonação de usuários

É possível entrar como qualquer usuário vinculado a um cliente. Utilize o botão **Listar usuários** na tabela de clientes e, em seguida, clique em **Acessar** ao lado do participante desejado. Enquanto estiver nesse modo, a barra superior exibirá "Sair do modo usuário" para retornar ao perfil de administrador.

## Database maintenance

`add_taxa_coluna.py` adiciona a coluna `taxa_diferenciada` na tabela `configuracao_cliente` caso ela ainda nao exista.
`check_and_fix_taxa_column.py` verifica se a coluna esta presente e a cria automaticamente se necessario.
Execute um desses scripts antes de rodar `populate_script.py` caso seu banco nao esteja com as migracoes atualizadas.

## Organização de templates

Para mover arquivos de template para suas pastas corretas, utilize:

```bash
python organizar_templates.py
```

Esse script substitui o antigo `organizar_templates.sh`.

## Deployment

Run the application with Gunicorn using the WSGI entry point from `wsgi.py`. Use `eventlet` workers and bind to the `PORT` environment variable expected by most hosting platforms:

```

gunicorn app:app --worker-class eventlet --workers 4 --timeout 120 --bind 0.0.0.0:$PORT

```

The `eventlet` dependency is included in `requirements.txt`.

Ensure all configuration variables described earlier are set before starting the
server.

## Background jobs

Heavy PDF generation and e-mail sending can block a request. Use Celery to run
these tasks asynchronously. Start a worker with:

```bash
celery -A tasks.celery worker --loglevel=info
```

Set `REDIS_URL` to your broker URI and run the worker alongside Gunicorn.


## API

### `GET /visualizar/<agendamento_id>`

Retorna os detalhes de um agendamento existente. Quando o cabeçalho
`Accept` é `application/json` e o agendamento não é localizado, a rota
responde com `404` e um corpo JSON no formato
`{"erro": "Agendamento não encontrado"}`.

### Render deploy hook

To trigger redeploys automatically when new commits are pushed, open your web service settings on Render. Under **Deploy Hooks**, click **Enable deploy hook** to generate the URL. Call this endpoint from your CI workflow or repository settings whenever you want Render to rebuild the service.

