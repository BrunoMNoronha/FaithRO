# Índice da documentação — FaithRO - Laos Deos

Índice central da base de conhecimento técnica do projeto. Toda a documentação
está em português brasileiro. Este índice não renumera os documentos existentes;
apenas os organiza por categoria e registra estado e dependências.

## Como usar

- Comece por [00-base-conhecimento.md](00-base-conhecimento.md) para a visão do
  projeto.
- Para cliente/protocolo, veja [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md).
- Para a política de fontes, veja [10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md).

## Estados possíveis

- **Estado documental** — maturidade do texto: `planejado` · `em elaboração` ·
  `validado` · `desatualizado`.
- **Estado de implantação** — o procedimento descrito já foi executado no
  ambiente real: `não aplicável` (documento conceitual) · `não iniciado` ·
  `em andamento` · `implantado` · `pendente de validação`.

> Um documento pode ter texto `validado` e implantação `não iniciado`. Não marque
> o texto como pendente apenas porque o cliente ou serviço ainda não foi testado.

## Índice por documento

| Documento | Finalidade | Público-alvo | Estado documental | Estado de implantação | Dependências | Última revisão |
| --- | --- | --- | --- | --- | --- | --- |
| [00-base-conhecimento.md](00-base-conhecimento.md) | Visão geral, definição de old school, level 185 | Todos | validado | não aplicável | — | 2026-07-10 |
| [01-decisao-tecnica.md](01-decisao-tecnica.md) | Escolha do emulador (rAthena) | Técnico | validado | não aplicável | 00 | 2026-07-10 |
| [02-roadmap.md](02-roadmap.md) | Fases do projeto | Todos | em elaboração | não aplicável | 00, 01 | 2026-07-10 |
| [03-configuracao-alvo.md](03-configuracao-alvo.md) | Referência mecânica Pre-Renewal e planejamento de rates, classes, level e conteúdo | Config/gameplay | validado | parcialmente implantado[^1] | 00, 09, 10, 11 | 2026-07-10 |
| [04-operacao-vps.md](04-operacao-vps.md) | Hardware, hardening, portas, backups | Infra/operação | em elaboração | não iniciado | 08 | 2026-07-10 |
| [05-governanca.md](05-governanca.md) | Princípios, regras de mudança, ADRs | Todos | validado | não aplicável | — | 2026-07-10 |
| [06-plano-execucao-inicial.md](06-plano-execucao-inicial.md) | Fluxo de branches e backlog inicial | Técnico | validado | não aplicável | 07 | 2026-07-10 |
| [07-fluxo-pull-request.md](07-fluxo-pull-request.md) | Processo de PR | Colaboradores | validado | não aplicável | 06 | 2026-07-10 |
| [08-preparar-vps-ubuntu-2204.md](08-preparar-vps-ubuntu-2204.md) | Preparação da VPS (issue #2) | Infra | validado | não iniciado | 04 | 2026-07-10 |
| [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md) | Cliente, `PACKETVER`, obfuscação, web server, matriz e testes | Cliente/protocolo | validado | não iniciado | 01, 10 | 2026-07-10 |
| [10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md) | Política e tabela de fontes | Técnico/documental | validado | não aplicável | — | 2026-07-10 |
| [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md) | Unidades systemd do rAthena, binários, portas e web server | Infra/operação | validado | implantado (login/char/map); web server não implantado | 04, 09 | 2026-07-10 |
| [99-checklists.md](99-checklists.md) | Checklists de PR, deploy, balanceamento | Todos | validado | não aplicável | — | 2026-07-10 |

[^1]: No documento 03, "parcialmente implantado" significa apenas que a
    configuração de build auditada está alinhada com Pre-Renewal. Level 185,
    rates, bloqueio de classes e curadoria de conteúdo continuam pendentes.

## Índice por categoria

- **Visão geral e decisões:** [00](00-base-conhecimento.md),
  [01](01-decisao-tecnica.md), [05](05-governanca.md).
- **Planejamento e processo:** [02](02-roadmap.md),
  [06](06-plano-execucao-inicial.md), [07](07-fluxo-pull-request.md),
  [99](99-checklists.md).
- **Infraestrutura e operação:** [04](04-operacao-vps.md),
  [08-preparar-vps-ubuntu-2204.md](08-preparar-vps-ubuntu-2204.md),
  [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md).
- **Gameplay e balanceamento:** [03](03-configuracao-alvo.md) (mecânica
  Pre-Renewal, level 185 e rates, ver também [00](00-base-conhecimento.md)).
- **Cliente e protocolo:** [09](09-cliente-baseline-protocolo.md).
- **Fontes comunitárias:** [10](10-fontes-comunitarias-rathena.md).
- **Templates:** [templates/ADR.md](templates/ADR.md),
  [templates/PULL_REQUEST_TEMPLATE.md](templates/PULL_REQUEST_TEMPLATE.md).

## Convenções

- Numeração `NN-nome.md`; próximos documentos usam o próximo número livre (a
  partir de `11`), sem renumerar os existentes.
- Documentos de procedimento técnico devem conter: Objetivo, Contexto e
  premissas, Arquivos afetados, Passos, Testes, Riscos, Rollback, Referências.
- Distinguir sempre: fato oficial, fato confirmado no código, decisão do projeto,
  recomendação comunitária, hipótese e pendência.
- Não versionar segredos nem material proprietário (ver
  [../SECURITY.md](../SECURITY.md) e [05-governanca.md](05-governanca.md)).
</content>
