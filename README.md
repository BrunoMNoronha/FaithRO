# FaithRO - Laos Deos

Servidor sem fins lucrativos inspirado em Ragnarok Online, com proposta **old school**, **high rate**, sem 3ª classes e com progressão customizada até o nível base 185.

> Status: documentação inicial / planejamento técnico.
> Emulador recomendado para a primeira fase: **rAthena**.

## Objetivo do projeto

Criar um servidor estável, simples de manter, com foco em nostalgia, comunidade pequena/média e regras transparentes. O projeto deve evitar pay-to-win e priorizar operação responsável, backups, versionamento e documentação desde o início.

## Escopo inicial

- Mecânica base: old school / pré-renewal como referência.
- Classes: até transclasses; sem 3ª classes.
- Rates: high rate, valores finais a definir.
- Level máximo: 185, sujeito a balanceamento.
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
3. Organizar a branch `dev` para desenvolvimento integrado e branches de tarefa específicas.
4. Estruturar o backlog técnico inicial e abrir as issues correspondentes no GitHub.
5. Preparar ambiente local/dev antes de produção (fork/submodule do emulador, compilação, banco de teste).
6. Definir rates, episódio-alvo, jobs permitidos, drops e economia.
7. Configurar VPS com usuário não-root, firewall, fail2ban e backups.
8. Só depois abrir alpha fechado.

Ver [docs/06-plano-execucao-inicial.md](docs/06-plano-execucao-inicial.md) para o detalhamento desta fase.

## Documentação

O índice central da base de conhecimento está em
[docs/README.md](docs/README.md). Para cliente e protocolo, ver
[docs/09-cliente-baseline-protocolo.md](docs/09-cliente-baseline-protocolo.md);
para a política de fontes, ver
[docs/10-fontes-comunitarias-rathena.md](docs/10-fontes-comunitarias-rathena.md).
