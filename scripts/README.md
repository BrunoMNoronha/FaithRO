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

## Criação das issues iniciais

### `criar-issues-iniciais.md`

Guia manual com as 15 issues do backlog técnico inicial (título, descrição e critérios de aceite cada). Serve como fonte de verdade tanto para criação manual pela interface do GitHub quanto como base de conteúdo para o script `criar-issues-iniciais.ps1`.

### `criar-issues-iniciais.ps1`

Script PowerShell que usa o GitHub CLI (`gh issue create`) para criar as mesmas 15 issues no repositório `BrunoMNoronha/FaithRO`. Não contém tokens, senhas ou dados sensíveis.

**Pré-requisitos:**

- GitHub CLI instalado (`gh --version`).
- Autenticação feita com `gh auth login` (verificar com `gh auth status`).
- Permissão de escrita (criar issues) no repositório.
- As labels sugeridas (`infra`, `banco`, `emulador`, `config`, `seguranca`, `backup`, `docs`, `governanca`) podem não existir ainda no repositório — crie-as antes em Settings > Labels (ou via `gh label create`), senão o `gh issue create` falha ao aplicar uma label inexistente.

**Modo simulação (padrão, seguro):**

O script inicia com `$DryRun = $true`. Nesse modo, ele apenas imprime no terminal os comandos `gh issue create` que seriam executados, sem criar nada no GitHub.

```powershell
./scripts/criar-issues-iniciais.ps1
```

**Execução real:**

Só execute de verdade após revisar a saída do modo simulação e confirmar que as labels já existem no repositório.

1. Editar o arquivo e alterar `$DryRun = $true` para `$DryRun = $false`.
2. Rodar novamente:

```powershell
./scripts/criar-issues-iniciais.ps1
```

Isso criará as 15 issues reais em `https://github.com/BrunoMNoronha/FaithRO/issues`.
