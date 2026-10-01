# rAthena overlay — fonte versionada dos overrides

Este diretório é a **fonte versionada** dos arquivos de *override* do rAthena do
FaithRO. Ele **não** é o rAthena e **não** deve conter o repositório do emulador.
Cada arquivo aqui espelha exatamente o caminho de destino no rAthena instalado.

## Mapeamento de destino

| Arquivo versionado (overlay) | Destino na VPS |
|---|---|
| `conf/import/battle_conf.txt` | `/opt/faithro/rathena/conf/import/battle_conf.txt` |
| `db/import/job_stats.yml` | `/opt/faithro/rathena/db/import/job_stats.yml` |
| `db/import/statpoint.yml` | `/opt/faithro/rathena/db/import/statpoint.yml` |

A implantação (ETAPA 2N-D, ainda **não** executada) copiará o conteúdo destes
arquivos para os caminhos equivalentes, com backup e janela de manutenção.

## Cadeia de importação confirmada (commit auditado `7f080871c`)

- **Base EXP / `MaxBaseLevel`:** `db/job_stats.yml` → `db/pre-re/job_exp.yml` →
  **`db/import/job_stats.yml`** (carregado por último, sobrescreve).
  **Não** existe `db/import/job_exp.yml` na cadeia — não criar esse arquivo.
- **Pontos de status:** `db/statpoint.yml` → `db/pre-re/statpoint.yml` →
  **`db/import/statpoint.yml`** (carregado por último, sobrescreve).
- **Configuração de batalha:** `conf/battle/*.conf` → `conf/import/battle_conf.txt`.

## Pacote implementado (aprovado na ETAPA 2N-B, issue #8)

- Base Level máximo: **255** (core inalterado; `MAX_LEVEL = 275`).
- Atributo natural máximo (normal e trans): **185**.
- ASPD máxima: **197** (teto global).
- Base EXP: **Curva B — Intermediária**, níveis 99–255 (157 entradas;
  `Level 255` = sentinela do cap).
- Pontos de status: **Modelo B — continuação natural**, níveis 201–255
  (55 entradas; `Points(255) = 7185`).
- Job level: **modelo clássico** (nenhum `MaxJobLevel` alterado).
- **Nenhuma** 3ª/4ª classe habilitada; classes expandidas/baby não ativadas
  (política pertence à issue #9).

## Estado

`implementação versionada` · `pendente de implantação controlada` ·
`pendente de validação no cliente`. Nada foi implantado na VPS por esta etapa.

## Validação

`python scripts/validate-progression-overrides.py` (biblioteca padrão; não
inicia o map-server).
