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
| [00-base-conhecimento.md](00-base-conhecimento.md) | Visão geral, definição de old school, base level 255, atributos máximos 185 e ASPD máxima 197 | Todos | validado | não aplicável | — | 2026-07-10 |
| [01-decisao-tecnica.md](01-decisao-tecnica.md) | Escolha do emulador (rAthena) | Técnico | validado | não aplicável | 00 | 2026-07-10 |
| [02-roadmap.md](02-roadmap.md) | Fases do projeto | Todos | em elaboração | não aplicável | 00, 01 | 2026-07-10 |
| [03-configuracao-alvo.md](03-configuracao-alvo.md) | Referência mecânica Pre-Renewal e planejamento de base level 255, atributos 185, ASPD 197, classes, rates e conteúdo | Config/gameplay | validado | parcialmente implantado[^1] | 00, 09, 10, 11 | 2026-07-10 |
| [04-operacao-vps.md](04-operacao-vps.md) | Hardware, hardening, portas, backups | Infra/operação | em elaboração | não iniciado | 08 | 2026-07-10 |
| [05-governanca.md](05-governanca.md) | Princípios, regras de mudança, ADRs | Todos | validado | não aplicável | — | 2026-07-10 |
| [06-plano-execucao-inicial.md](06-plano-execucao-inicial.md) | Fluxo de branches e backlog inicial | Técnico | validado | não aplicável | 07 | 2026-07-10 |
| [07-fluxo-pull-request.md](07-fluxo-pull-request.md) | Processo de PR | Colaboradores | validado | não aplicável | 06 | 2026-07-10 |
| [08-preparar-vps-ubuntu-2204.md](08-preparar-vps-ubuntu-2204.md) | Preparação da VPS (issue #2) | Infra | validado | não iniciado | 04 | 2026-07-10 |
| [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md) | Cliente, `PACKETVER`, obfuscação, web server, matriz e testes | Cliente/protocolo | validado | não iniciado | 01, 10 | 2026-07-10 |
| [10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md) | Política e tabela de fontes | Técnico/documental | validado | não aplicável | — | 2026-07-10 |
| [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md) | Unidades systemd do rAthena, binários, portas e web server | Infra/operação | validado | implantado (login/char/map); web server não implantado | 04, 09 | 2026-07-10 |
| [12-configuracao-packetver.md](12-configuracao-packetver.md) | Procedimento planejado de configuração de `PACKETVER`, obfuscação e web server | Cliente/protocolo | validado | não iniciado | 09, 10, 11 | 2026-07-10 |
| [13-credenciais-sql-rathena.md](13-credenciais-sql-rathena.md) | Auditoria e rotação segura das credenciais MariaDB do rAthena (usuário único `faithro_app`, seis diretivas `*_pw`) | Infra/operação/segurança | validado | implantado (rotação executada e validada) | 04, 11 | 2026-07-11 |
| [14-progressao-base-255-overrides.md](14-progressao-base-255-overrides.md) | Overrides versionados de progressão (Base 255, atributos 185, ASPD 197, Curva EXP B, stat points Modelo B); mapeamento para `/opt/faithro/rathena` | Config/gameplay | validado | não iniciado (implementação versionada; não implantado) | 03, 11 | 2026-07-11 |
| [23-planejamento-primeiro-build-controlado-beam.md](23-planejamento-primeiro-build-controlado-beam.md) | Plano do primeiro build controlado do Beam Patcher (Rust 1.85.0 nomeada; build bloqueado, exige autorização humana) | Cliente/build/segurança | validado | não iniciado (build não autorizado) | 19, 20, 21, 22 | 2026-07-25 |
| [24-runbook-primeiro-build-controlado-beam.md](24-runbook-primeiro-build-controlado-beam.md) | Runbook operacional, modelo de autorização humana e template de evidência do primeiro build (build bloqueado; autorização não concedida) | Cliente/build/segurança | validado | não iniciado (autorização não concedida) | 19, 20, 21, 22, 23 | 2026-07-25 |
| [99-checklists.md](99-checklists.md) | Checklists de PR, deploy, balanceamento | Todos | validado | não aplicável | — | 2026-07-10 |

[^1]: No documento 03, "parcialmente implantado" significa apenas que a
    configuração registrada do build está alinhada com Pre-Renewal. Base
    level 255, atributos naturais máximos 185, ASPD máxima 197, rates,
    classes e conteúdo continuam pendentes de implantação e validação.

## Índice por categoria

- **Visão geral e decisões:** [00](00-base-conhecimento.md),
  [01](01-decisao-tecnica.md), [05](05-governanca.md).
- **Planejamento e processo:** [02](02-roadmap.md),
  [06](06-plano-execucao-inicial.md), [07](07-fluxo-pull-request.md),
  [99](99-checklists.md).
- **Infraestrutura e operação:** [04](04-operacao-vps.md),
  [08-preparar-vps-ubuntu-2204.md](08-preparar-vps-ubuntu-2204.md),
  [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md),
  [13-credenciais-sql-rathena.md](13-credenciais-sql-rathena.md).
- **Gameplay e balanceamento:** [03](03-configuracao-alvo.md) (mecânica
  Pre-Renewal, base level 255, atributos máximos 185, ASPD máxima 197 e
  rates, ver também [00](00-base-conhecimento.md)),
  [14](14-progressao-base-255-overrides.md) (overrides versionados de
  progressão; ainda não implantados).
- **Cliente e protocolo:** [09](09-cliente-baseline-protocolo.md),
  [12](12-configuracao-packetver.md).
- **Patcher e build auditável do Beam:**
  [23](23-planejamento-primeiro-build-controlado-beam.md) (planejamento do
  primeiro build controlado; build ainda não autorizado),
  [24](24-runbook-primeiro-build-controlado-beam.md) (runbook operacional,
  autorização humana e evidência; autorização não concedida).
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
