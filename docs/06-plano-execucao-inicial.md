# Plano de execução inicial

## Objetivo da fase atual

Organizar o fluxo de desenvolvimento do repositório após o primeiro commit, criando a branch `dev`, estruturando o backlog técnico inicial e preparando o terreno para a abertura de issues no GitHub, antes de qualquer instalação de ambiente local ou VPS.

## Estado atual do projeto

- Repositório criado no GitHub: https://github.com/BrunoMNoronha/FaithRO
- Pacote inicial de documentação já versionado na branch `main` (commit `docs: adiciona base inicial do projeto FaithRO`).
- Nenhuma instalação de emulador, banco de dados ou VPS foi realizada até o momento.
- Branch `dev` criada para concentrar o desenvolvimento integrado.

## Fluxo de branches recomendado

- `main`: base estável, apenas conteúdo revisado e testado.
- `dev`: desenvolvimento integrado, ponto de partida para branches de tarefa.
- Branches de tarefa (a partir de `dev`), por exemplo:
  - `docs/backlog-inicial`
  - `infra/setup-vps`
  - `config/rates-iniciais`
  - `emulador/setup-rathena`

Fluxo sugerido: tarefa → PR para `dev` → validação → PR de `dev` para `main` em pontos estáveis (releases de documentação/configuração).

## Backlog inicial

- [Infra] Preparar VPS Ubuntu 22.04
- [Infra] Instalar dependências do rAthena
- [Banco] Instalar e configurar MariaDB
- [Emulador] Clonar e compilar rAthena
- [Config] Definir episódio/referência mecânica
- [Config] Definir rates iniciais
- [Config] Definir base level 255 e status máximo 187 (escopo original citava
  level máximo 185; decisão substituída em 2026-07-10 — ver issue #8)
- [Config] Bloquear 3ª classes
- [Segurança] Configurar usuário não-root
- [Segurança] Configurar firewall
- [Segurança] Configurar fail2ban
- [Backup] Definir rotina de backup
- [Docs] Criar guia de instalação local
- [Docs] Criar guia de operação da VPS
- [Governança] Definir regras do alpha fechado

## Critérios de pronto para a fase inicial

- Branch `dev` criada e disponível (local e, após confirmação, remota).
- README atualizado refletindo o estado real do projeto.
- Backlog técnico documentado e compreensível para qualquer colaborador.
- Issues iniciais com título, descrição e critérios de aceite prontos para criação manual no GitHub.
- Nenhum arquivo sensível, proprietário ou de instalação real foi adicionado.

## Riscos

- Baixo risco técnico: fase é apenas documentação e organização de branches, sem alteração de sistemas em produção.
- Risco de divergência entre `main` e `dev` se branches de tarefa não forem revisadas antes do merge.
- Risco de esquecimento de itens do backlog se as issues não forem criadas a partir deste documento.

## Rollback

- Caso a branch `dev` precise ser descartada: `git branch -D dev` localmente (e `git push origin --delete dev` remotamente, apenas mediante confirmação).
- Caso as alterações de documentação precisem ser revertidas: `git checkout main -- README.md` ou reverter o commit específico com `git revert <hash>`.
- Nenhuma dessas ações afeta banco de dados, VPS ou emulador, pois nada disso foi instalado ainda.

## Próximo passo recomendado

Criar as issues iniciais no GitHub a partir de [scripts/criar-issues-iniciais.md](../scripts/criar-issues-iniciais.md) e, em seguida, iniciar a fase de preparação de ambiente local (Fase 1 do [roadmap](02-roadmap.md)).
