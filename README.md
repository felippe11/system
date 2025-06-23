# systemiafaptwo

A Flask-based management system.

## Configuracao

Defina as variaveis de ambiente abaixo antes de iniciar a aplicacao:

```bash
export MAIL_USERNAME="seu_email@gmail.com"
export MAIL_PASSWORD="sua_senha"
export GOOGLE_CLIENT_ID="<cliente_id_do_google>"
export GOOGLE_CLIENT_SECRET="<cliente_secret_do_google>"
export SECRET_KEY="<sua_chave_secreta>"
export APP_BASE_URL="https://seu-dominio.com"
export RECAPTCHA_PUBLIC_KEY="<sua_chave_publica_recaptcha>"
export RECAPTCHA_PRIVATE_KEY="<sua_chave_privada_recaptcha>"
export DB_ONLINE="<url_do_banco_online>"
export DB_LOCAL="<url_do_banco_local>"
```

## Banco de Dados

Depois de clonar o repositório ou atualizar o código, aplique as migrações executando:

```bash
flask db upgrade
```

`SECRET_KEY` garante que as sessões geradas por uma instância do Flask possam
ser lidas por outra. Em produção, utilize um valor seguro e idêntico em todas as
réplicas do aplicativo.

Essas variaveis substituem o antigo arquivo `credentials.json` utilizado para a
autenticacao com a API do Gmail. O arquivo `token.json` sera gerado apos a
primeira autenticacao.

`APP_BASE_URL` define a URL base para gerar links externos, como o `notification_url` do Mercado Pago. Em desenvolvimento, aponte para um endereço público (ex.: URL do ngrok).

`RECAPTCHA_PUBLIC_KEY` e `RECAPTCHA_PRIVATE_KEY` devem conter as chaves obtidas no [Google reCAPTCHA](https://www.google.com/recaptcha/admin). Sem valores válidos, o CAPTCHA não funcionará em produção.

## Execucao

O arquivo `Procfile` usa `gunicorn app:app` para iniciar o servidor. O
`gunicorn` é recomendado apenas para ambientes Linux ou WSL. No Windows,
execute `python app.py` ou instale o pacote `waitress` para ter um servidor
mais apropriado para produção.

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

## Programacao em PDF

Use a rota `/gerar_folder_evento/<evento_id>` para baixar a programacao do evento no formato de folder. Esta rota gera um PDF em modo paisagem com duas colunas, facilitando a impressao frente e verso.

### Exportar participantes

No dashboard do cliente é possível exportar a lista de inscritos de um evento em dois formatos. Escolha o evento desejado e utilize o botão **Exportar Participantes** para baixar um arquivo XLSX ou PDF contendo os campos padrões e personalizados do cadastro.

### Placas de oficinas

Para sinalizar as atividades de um evento, utilize a rota `/gerar_placas/<evento_id>` ou o botão **Baixar Placas** no dashboard do cliente. Um PDF é gerado com uma página por oficina, contendo título e ministrante.

### Impersonação de clientes

Administradores podem acessar o painel de qualquer cliente clicando em **Acessar** na seção de Gestão de Clientes do dashboard. A navegação mostrará um link "Sair do modo cliente" para retornar à conta de administrador.

## Database maintenance

`add_taxa_coluna.py` adiciona a coluna `taxa_diferenciada` na tabela `configuracao_cliente` caso ela ainda nao exista.
`check_and_fix_taxa_column.py` verifica se a coluna esta presente e a cria automaticamente se necessario.
Execute um desses scripts antes de rodar `populate_script.py` caso seu banco nao esteja com as migracoes atualizadas.

