# FaithRO - Laos Deos

Servidor sem fins lucrativos inspirado em Ragnarok Online, com proposta **old school**, **high rate**, sem 3ª classes e com progressão customizada até o nível base 255 (atributo/status natural máximo individual planejado: 185; ASPD máxima planejada: 197).

> Status: infraestrutura base implantada e auditada (VPS, MariaDB, rAthena
> compilado e serviços em execução); configuração de gameplay e alpha ainda
> pendentes.
> Emulador em uso na primeira fase: **rAthena**.

## Objetivo do projeto

Criar um servidor estável, simples de manter, com foco em nostalgia, comunidade pequena/média e regras transparentes. O projeto deve evitar pay-to-win e priorizar operação responsável, backups, versionamento e documentação desde o início.

## Escopo inicial

- Mecânica base: old school / pré-renewal como referência.
- Classes: até transclasses; sem 3ª classes.
- Rates: high rate, valores finais a definir.
- Base level máximo planejado: 255, sujeito a balanceamento (antigo base level máximo 185 substituído em 2026-07-10).
- Atributo/status natural máximo individual planejado: 185 (corrige a decisão anterior de 187; não confundir com o antigo base level 185).
- ASPD máxima planejada: 197.
- Job level máximo: a definir por classe.
- Hospedagem inicial: VPS Ubuntu 22.04, 1 vCPU, 2 GB RAM, 50 GB.
- Banco de dados: MariaDB.
- Versionamento: GitHub.
- Ferramentas de IA: ChatGPT, Claude e GitHub Copilot.

## Decisões iniciais

| Tema | Decisão |
|---|---|
| Emulador | rAthena na fase inicial |
| Alternativa | Hercules se o projeto exigir arquitetura mais modular/plugin-based |
| Produção | Não rodar diretamente da branch upstream sem testes |
| Customizações | Manter em `import`, `npc/custom`, patches pequenos e documentados |
| Dados sensíveis | Nunca versionar `.env`, senhas, dumps reais, chaves SSH ou backups |
| Cliente/assets | Não versionar nem distribuir material proprietário ou sem licença |

## Estrutura sugerida

```text
faithro/
├─ .github/
│  ├─ copilot-instructions.md
│  ├─ instructions/
│  └─ ISSUE_TEMPLATE/
├─ docs/
├─ prompts/
├─ scripts/
├─ AGENTS.md
├─ CLAUDE.md
├─ README.md
├─ SECURITY.md
└─ CONTRIBUTING.md
```

## Próximos passos

1. ~~Criar repositório no GitHub.~~ ✅ Concluído.
2. ~~Adicionar pacote inicial de documentação ao repositório.~~ ✅ Concluído (commit inicial na branch `main`).
3. ~~Organizar a branch `dev` para desenvolvimento integrado e branches de tarefa específicas.~~ ✅ Concluído.
4. ~~Estruturar o backlog técnico inicial e abrir as issues correspondentes no GitHub.~~ ✅ Concluído (issues #2–#16).
5. ~~Preparar ambiente do emulador (compilação, banco de dados e serviços).~~ ✅ Concluído na VPS: rAthena compilado (commit `7f080871c`), MariaDB e serviços `login/char/map` ativos (auditoria read-only em 2026-07-11).
6. ~~Configurar VPS com usuário não-root, firewall, fail2ban e backups.~~ ⚠️ Parcial: usuário não-root, SSH endurecido, `ufw` e fail2ban concluídos; backups existem e estão protegidos, mas a **rotina automática** ainda está pendente (issue #13).
7. Definir configuração de gameplay: rates (issue #7), base level 255 / atributo 185 / ASPD 197 (issue #8), jobs permitidos e bloqueio de 3ª classes (issue #9), drops, EXP table e economia. Episódio/referência mecânica (Pre-Renewal) já definido (issue #6).
8. Escrever o guia de instalação local (issue #14) e definir as regras do alpha fechado (issue #16).
9. Só depois abrir alpha fechado.

Ver [docs/06-plano-execucao-inicial.md](docs/06-plano-execucao-inicial.md) para o detalhamento e [docs/02-roadmap.md](docs/02-roadmap.md) para o roadmap por fases.

## Documentação

O índice central da base de conhecimento está em
[docs/README.md](docs/README.md). Para cliente e protocolo, ver
[docs/09-cliente-baseline-protocolo.md](docs/09-cliente-baseline-protocolo.md);
para a política de fontes, ver
[docs/10-fontes-comunitarias-rathena.md](docs/10-fontes-comunitarias-rathena.md).
