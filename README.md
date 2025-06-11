# systemiafaptwo

A Flask-based management system.

## Configuracao

Defina as variaveis de ambiente abaixo antes de iniciar a aplicacao:

```bash
export MAIL_USERNAME="seu_email@gmail.com"
export MAIL_PASSWORD="sua_senha"
export GOOGLE_CLIENT_ID="<cliente_id_do_google>"
export GOOGLE_CLIENT_SECRET="<cliente_secret_do_google>"
```

Essas variaveis substituem o antigo arquivo `credentials.json` utilizado para a
autenticacao com a API do Gmail. O arquivo `token.json` sera gerado apos a
primeira autenticacao.
