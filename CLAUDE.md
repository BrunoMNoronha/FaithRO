# CLAUDE.md - Memória de projeto para Claude Code

## Projeto

FaithRO - Laos Deos é um servidor sem fins lucrativos, old school/high rate, sem 3ª classes, com base level máximo planejado em 255 e status/atributo máximo individual planejado em 187 (job level máximo a definir por classe; decisão anterior de level 185 substituída em 2026-07-10).

## Instruções permanentes

- Trabalhe com cautela. Este projeto envolve emulador, banco de dados e operação Linux.
- Antes de editar arquivos, leia a estrutura do repositório.
- Antes de sugerir comandos destrutivos, explique o impacto.
- Nunca leia, edite ou exponha arquivos sensíveis como `.env`, chaves SSH, dumps reais e backups.
- Não ajude a distribuir cliente, GRF, executáveis ou assets proprietários sem licença.
- Prefira `conf/import`, `db/import` e `npc/custom` em vez de editar o core.
- Use português brasileiro.
- Responda com plano, patch proposto, testes e rollback.

## Convenções

- Branches:
  - `docs/...`
  - `feature/...`
  - `fix/...`
  - `infra/...`
- Commits:
  - `docs: ...`
  - `feat: ...`
  - `fix: ...`
  - `infra: ...`
- PRs devem incluir:
  - resumo
  - checklist de testes
  - riscos
  - rollback

## Checklist antes de finalizar

- [ ] A mudança respeita old school / sem 3ª classes?
- [ ] A mudança não cria pay-to-win?
- [ ] A mudança é segura para produção?
- [ ] Há documentação?
- [ ] Há plano de rollback?
