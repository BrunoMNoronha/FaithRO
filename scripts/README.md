# Scripts

Este diretório deve conter scripts auxiliares do projeto.

## Regras

- Use `set -euo pipefail`.
- Não colocar senhas no script.
- Carregar variáveis de ambiente por `.env` local não versionado.
- Registrar logs.
- Documentar uso.
- Testar em ambiente dev antes de produção.

## Exemplos futuros

- `backup-db.sh`
- `deploy-config.sh`
- `healthcheck.sh`
- `restore-db.sh`
