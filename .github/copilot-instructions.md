# GitHub Copilot - Instruções do repositório FaithRO

Este repositório documenta e customiza o projeto FaithRO - Laos Deos.

## Contexto

Servidor Ragnarok-like sem fins lucrativos, old school/high rate, sem 3ª classes, base level máximo planejado 255 e status máximo individual planejado 187 (decisão anterior de level 185 substituída em 2026-07-10), usando rAthena como emulador inicial e MariaDB como banco.

## Como gerar código

- Não inclua segredos.
- Não gere dumps reais, credenciais ou chaves.
- Não recomende distribuir cliente/assets proprietários.
- Prefira configurações em `conf/import`, `db/import`, `npc/custom`.
- Evite mudanças no core quando um override/config resolver.
- Use português brasileiro em documentação.
- Para scripts shell, use `set -euo pipefail`.
- Para SQL, prefira migrations pequenas, idempotentes quando possível, com comentários.
- Para NPC/scripts, mantenha comentários curtos e objetivos.
- Para qualquer alteração operacional, inclua teste e rollback.

## Estilo

- Código simples e explícito.
- Commits pequenos.
- Nomes claros.
- Nada de “magic numbers” sem comentário.

## Segurança

- Nunca sugerir versionar:
  - `.env`
  - `*.sql` de dump real
  - backups
  - chaves privadas
  - senhas
  - tokens
  - dados pessoais de jogadores
