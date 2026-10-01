# Overrides versionados de progressão — Base 255, atributos 185, ASPD 197

> **Escopo:** implementação **versionada** dos overrides de progressão
> (ETAPA 2N-C, issue #8). Este documento e os arquivos associados **não** foram
> implantados na VPS. Estado: `implementação versionada` ·
> `pendente de implantação controlada` · `pendente de validação no cliente`.

## Objetivo

Registrar a fonte versionada dos limites de progressão aprovados na ETAPA 2N-B
e o mapeamento exato para o rAthena, sem implantar nada:

- Base Level máximo: **255** (core inalterado; `MAX_LEVEL = 275`).
- Atributo natural máximo (normal e trans): **185**.
- ASPD máxima: **197** (teto global, não garantia por classe).
- Base EXP: **Curva B — Intermediária**, níveis 99–255.
- Pontos de status: **Modelo B — continuação natural**, níveis 201–255,
  com `Points(255) = 7185`.
- Job level: **modelo clássico** — nenhum `MaxJobLevel` alterado.
- **Nenhuma** 3ª/4ª classe habilitada; classes expandidas/baby não ativadas.

## Contexto e premissas

- Commit auditado do rAthena: `7f080871c8b3bbe7a79027194633201c63422ee1`
  (Pre-Renewal, `MAX_LEVEL = 275`, `MAX_EXP = INT64_MAX` para `PACKETVER ≥ 20170830`).
- `Points` em `statpoint.yml` é o **total acumulado** de BaseLevel 1 até o nível.
- Base EXP: `Level L` = EXP para avançar de `L` para `L+1`; `Level 255` é a
  **sentinela do cap** (`99999999`), pois no nível máximo o motor retorna
  `MAX_LEVEL_BASE_EXP` independentemente do valor tabelado.
- Custo de atributo (Pre-Renewal): `1 + (low + 9) / 10` (inteiro).

### Correção técnica sobre o arquivo de override de Base EXP

O override de Base EXP e `MaxBaseLevel` usa **`db/import/job_stats.yml`**
(Type `JOB_STATS`), **não** `db/import/job_exp.yml`. A cadeia real de importação
no commit auditado é:

```text
db/job_stats.yml  ->  db/pre-re/job_exp.yml  ->  db/import/job_stats.yml (por último, sobrescreve)
```

`db/import/job_exp.yml` **não** pertence à cadeia de importação e não deve ser
criado. Os pontos de status usam `db/import/statpoint.yml`, que também é
carregado por último na cadeia de `db/statpoint.yml`.

## Arquivos afetados (fonte versionada → destino)

| Fonte versionada (overlay) | Destino na VPS |
|---|---|
| `deploy/rathena-overlay/conf/import/battle_conf.txt` | `/opt/faithro/rathena/conf/import/battle_conf.txt` |
| `deploy/rathena-overlay/db/import/job_stats.yml` | `/opt/faithro/rathena/db/import/job_stats.yml` |
| `deploy/rathena-overlay/db/import/statpoint.yml` | `/opt/faithro/rathena/db/import/statpoint.yml` |

Validador: `scripts/validate-progression-overrides.py` (biblioteca padrão do
Python; **não** inicia o map-server). Os arquivos de override usam final de
linha **LF** (fixado em `.gitattributes`), obrigatório para o host Linux.

## Estrutura implementada

- `battle_conf.txt`: adiciona `max_parameter: 185`, `max_trans_parameter: 185`,
  `max_aspd: 197`. Não altera `max_third_aspd`, `max_extended_aspd`,
  `max_summoner_aspd`, nem `conf/battle/player.conf`.
- `job_stats.yml`: dois grupos de Base EXP (não-trans e trans, extraídos
  verbatim de `db/pre-re/job_exp.yml`). Em cada grupo, na ordem obrigatória
  `Jobs` → `MaxBaseLevel: 255` → `BaseExp` (99–255, 157 entradas). Só
  `MaxBaseLevel` e `BaseExp` são sobrescritos; `MaxJobLevel`, `JobExp`, HP/SP e
  demais campos são preservados pelo merge por classe.
- `statpoint.yml`: reescreve apenas níveis 201–255 (55 entradas). Níveis 1–200
  permanecem herdados de `db/pre-re/statpoint.yml`.

## Testes (estáticos — nenhum serviço iniciado)

- `python scripts/validate-progression-overrides.py` → contagens (157 Base EXP
  por grupo, 55 stat points), continuidade 99–255 e 201–255, monotonicidade,
  marcos, sentinela 255, ausência de `MaxJobLevel`/`JobExp`, ausência de
  classes de 3ª/4ª geração e ausência de `db/import/job_exp.yml`.
- `git diff --check`, verificação de UTF-8, ausência de tabs de indentação em
  YAML e ausência de segredos.

## Riscos

- Erro de estrutura `JOB_STATS` ou de ordem `MaxBaseLevel`/`BaseExp`.
- Grupo de jobs omitido ou classe não autorizada incluída.
- Nível faltante/duplicado ou curva incorreta.
- Pontos de status excessivos; aceleração dupla se a curva for combinada com
  rates altos (issue #7) — a tabela é bruta e o multiplicador é ortogonal.
- Divergência entre o ambiente versionado e o rAthena real; incompatibilidade
  após atualização upstream.
- Exibição no cliente para level 255 / atributos 185 / ASPD 197 (validar).
- ASPD 197 inviável ou trivial por classe; impacto em CPU e em PvM/MVP/PvP/WoE.
- **Dados persistidos:** após um eventual rollback, personagens que já
  ultrapassaram os limites anteriores e pontos/skill points já distribuídos
  **não** revertem apenas restaurando arquivos — exige saneamento no banco.

## Rollback (desta etapa)

Esta etapa é somente versionada. O rollback limita-se ao Git: reverter os
arquivos da branch antes do push; após o push e antes do merge, fechar o PR sem
merge (exclusão da branch remota apenas com autorização). Sem force push, sem
alterar `dev`, sem tocar na VPS. A implantação futura (ETAPA 2N-D) terá backup,
janela de manutenção e rollback próprios (arquivos e dados).

## Dependências

- **Issue #7 (rates):** pendente. A curva é bruta; o multiplicador global é
  aplicado depois e não exige redesenho.
- **Issue #9 (classes):** pendente. A alteração de dados de progressão **não**
  ativa nenhuma classe; a política de ativação de expandidas/baby e o bloqueio
  de 3ª classe pertencem à issue #9.

## Referências

- [03-configuracao-alvo.md](03-configuracao-alvo.md) — decisão de gameplay e
  terminologia (base level × job level × atributo natural × pontos × ASPD).
- [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md) — serviços e
  pré-check do MariaDB para a futura implantação (restart do map-server).
- `deploy/rathena-overlay/README.md` — mapeamento e cadeia de importação.
- Issue #8 — base level 255, atributos 185 e ASPD 197.
