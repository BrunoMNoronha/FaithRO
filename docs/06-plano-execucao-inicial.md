# Plano de execução inicial

## Objetivo da fase atual

Organizar o fluxo de desenvolvimento do repositório após o primeiro commit, criando a branch `dev`, estruturando o backlog técnico inicial e preparando o terreno para a abertura de issues no GitHub, antes de qualquer instalação de ambiente local ou VPS.

## Estado atual do projeto

> Atualizado em 2026-07-11 após auditoria read-only da VPS. A fase de organização
> de branches/backlog descrita neste documento está concluída; a infraestrutura
> base foi implantada **na VPS**. A implantação na VPS não substitui o ambiente
> local/dev (Fase 1), que permanece pendente. Os itens abaixo refletem o estado
> real confirmado.

- Repositório criado no GitHub: https://github.com/BrunoMNoronha/FaithRO
- Pacote inicial de documentação já versionado na branch `main` (commit `docs: adiciona base inicial do projeto FaithRO`).
- Branch `dev` em uso como base de desenvolvimento integrado; branches de tarefa derivam dela.
- Backlog técnico aberto no GitHub (issues #2–#16).
- Infraestrutura base **implantada e auditada** na VPS Ubuntu 22.04: usuário
  não-root, SSH endurecido, `ufw`, fail2ban, MariaDB, usuário SQL dedicado,
  rAthena compilado (commit `7f080871c`) e serviços systemd `login/char/map`
  ativos. Backups protegidos existem, mas a rotina automática está pendente.
- Ambiente **local/dev separado** (clonagem, compilação, MariaDB local, banco de
  teste isolado e execução local de login/char/map) **ainda não comprovado** — a
  implantação atual está na VPS (issue #5, critério de ambiente local). Os
  testes de bloqueio do fail2ban (#12) e de conectividade do firewall (#11)
  também permanecem sem evidência.
- Configuração de gameplay (rates, level 255/atributo 185/ASPD 197, bloqueio de
  3ª classes, drops, EXP) ainda **não** implantada — permanece estado-alvo das
  issues #7/#8/#9.

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

Status abaixo atualizado em 2026-07-11 pela auditoria. Legenda: ✅ concluído
(confirmado por evidência) · ⚠️ parcial · ⬜ pendente. As issues **não** foram
alteradas nem fechadas neste alinhamento; a atualização do backlog no GitHub
ocorrerá após a revisão e o merge deste PR.

- ✅ [Infra] Preparar VPS Ubuntu 22.04 *(issue #2)*
- ✅ [Infra] Instalar dependências do rAthena *(issue #3; build compilado)*
- ✅ [Banco] Instalar e configurar MariaDB *(issue #4; ativo, usuário dedicado)*
- ⚠️ [Emulador] Clonar e compilar rAthena *(issue #5; compilado e em execução na
  VPS — commit `7f080871c` —, mas o critério exige ambiente local/dev:
  clonagem, compilação e subida de login/char/map **localmente** ainda não
  comprovadas)*
- ✅ [Config] Definir episódio/referência mecânica *(issue #6 — Pre-Renewal, já fechada)*
- ⬜ [Config] Definir rates iniciais *(issue #7)*
- ⬜ [Config] Definir base level 255, atributos 185 e ASPD 197 (escopo original
  citava base level máximo 185, substituído em 2026-07-10; o atributo máximo
  187 foi posteriormente corrigido para 185 — issue #8)
- ⬜ [Config] Bloquear 3ª classes *(issue #9)*
- ✅ [Segurança] Configurar usuário não-root *(issue #10)*
- ⚠️ [Segurança] Configurar firewall *(issue #11; `ufw` ativo com regras
  aplicadas; teste de conectividade/bloqueio ainda não comprovado)*
- ⚠️ [Segurança] Configurar fail2ban *(issue #12; serviço e jail `sshd` ativos;
  teste de bloqueio ainda não comprovado)*
- ⚠️ [Backup] Definir rotina de backup *(issue #13; backups protegidos existem, rotina automática pendente)*
- ⬜ [Docs] Criar guia de instalação local *(issue #14)*
- ✅ [Docs] Criar guia de operação da VPS *(issue #15, já fechada)*
- ⬜ [Governança] Definir regras do alpha fechado *(issue #16)*

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

A infraestrutura principal da VPS está implantada. Permanecem pendentes o
ambiente local/dev isolado, a automação de backups e os critérios operacionais
ainda sem evidência completa (teste de bloqueio do fail2ban, teste de
conectividade/bloqueio do firewall). A configuração de gameplay deve avançar
somente com esses estados explicitamente separados.

O foco seguinte é a **Fase 2 – Configuração de gameplay** do
[roadmap](02-roadmap.md): rates (issue #7), base level 255 / atributo 185 /
ASPD 197 (issue #8) e bloqueio de 3ª classes (issue #9). Em paralelo, tratar o
ambiente local/dev (issue #5), o backup automático (issue #13), o guia de
instalação local (issue #14) e as regras do alpha fechado (issue #16). A
atualização e o fechamento das issues no GitHub devem ocorrer somente após a
revisão e o merge deste alinhamento documental.
