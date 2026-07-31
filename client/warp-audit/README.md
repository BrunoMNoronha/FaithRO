# `client/warp-audit/` — auditoria estática do WARP (ETAPA 2P-D)

> Esta pasta contém **apenas artefatos textuais** da auditoria estática do WARP
> (manifesto, achados de segurança, seleção de patches e seus schemas). **Nenhum**
> arquivo do WARP, do `Ragexe`, GRF, DLL, `.asi` ou asset proprietário é — ou pode
> ser — versionado aqui. O código-fonte do WARP **não** é copiado para o FaithRO.

## Contexto

A decisão de ferramenta ([docs/28](../../docs/28-decisao-ferramenta-preparacao-cliente.md))
aprovou o **WARP com restrições** e transferiu para a ETAPA 2P-D a auditoria
estática aprofundada do commit fixado. Esta pasta é o resultado versionado dessa
auditoria. O relatório completo está em
[docs/30-auditoria-estatica-warp.md](../../docs/30-auditoria-estatica-warp.md).

- **Origem oficial:** `https://github.com/Neo-Mind/WARP.git` (sem mirror).
- **Branch:** `rock_win32`.
- **Commit fixado:** `9b1173e9e4e135c68e150704f01186ab5e763acd`.
- **Licença:** GNU GPL v3 (arquivo `LICENSE`; a presença da GPL **não** prova que
  a fonte completa correspondente ao binário esteja neste commit).
- **Classificação:** `BLOQUEADO PARA BUILD DO FONTE` (núcleo só prebuilt no
  commit — W1) e `APROVADO COM RESTRIÇÕES` apenas para **decidir o caminho do
  núcleo** (ETAPA 2P-E-A). Só a camada textual é fonte auditável; o núcleo C++/Qt
  **não** está presente como fonte.

## Arquivos

| Arquivo | Conteúdo |
| --- | --- |
| [`upstream-manifest.example.json`](upstream-manifest.example.json) | Origem, integridade (tree digest, SHA-256 de arquivos críticos), inventário, binários rastreados, submódulos, toolchain. |
| [`security-findings.example.json`](security-findings.example.json) | Achados W1–W10 (severidade, evidência, impacto, mitigação, pendência humana). |
| [`patch-selection.example.json`](patch-selection.example.json) | Patches candidatos mínimos, sensíveis e rejeitados; flags de autorização. |
| [`core-path-decision-package.example.json`](core-path-decision-package.example.json) | (2P-E-A) Investigação do caminho do núcleo: fonte não localizada, proveniência do prebuilt, opções, matriz, requisitos de auditoria binária; `PENDING_HUMAN_DECISION`. |
| [`core-path-decision-record.example.json`](core-path-decision-record.example.json) | (2P-E-A) Registro de decisão humana **em branco** — template (`status=PENDING`, campos `null`, flags `false`). Permanece intocado. |
| [`decisions/core-path-decision-record-2026-07-31.json`](decisions/core-path-decision-record-2026-07-31.json) | (2P-E-A2) Registro **real** da decisão humana: `PREBUILT_PATH` **selecionado apenas para planejamento**; flags operacionais `false`. |
| [`binary-audit-plan.example.json`](binary-audit-plan.example.json) | (2P-E-B-PREBUILT) **Template** do plano da auditoria binária offline em 17 gates independentes; `PLANNED_NOT_AUTHORIZED`; nenhuma autorização operacional; nenhum binário materializado. |
| [`binary-audit-gate-record.example.json`](binary-audit-gate-record.example.json) | (2P-E-B-PREBUILT) **Template em branco** do registro de decisão por gate (`status=PENDING`, campos `null`, autoriza no máximo um gate; sem autorização transitiva). |
| [`decisions/binary-audit-gate-00-decision-record-2026-07-31.json`](decisions/binary-audit-gate-00-decision-record-2026-07-31.json) | (2P-E-C0-A) Registro **real** da autorização humana **exclusiva do GATE 0** (reconfirmação de proveniência por metadados): `AUTHORIZED_FOR_SINGLE_GATE`; GATE 0 autorizado, **não iniciado**; GATE 1 proibido. |
| [`schemas/`](schemas/) | JSON Schemas (draft-07) dos artefatos, incluindo `core-path-decision-record-real.schema.json`, `binary-audit-plan.schema.json`, `binary-audit-gate-record.schema.json` e `binary-audit-gate-00-decision-record-real.schema.json`. |

## Garantias desta etapa

O WARP **não** foi compilado nem executado. **Nenhum** executável do cliente foi
copiado ou modificado. **Nenhum** asset proprietário foi manipulado. As flags nos
artefatos permanecem:

```text
source_executed=false  source_built=false  binary_created=false  client_modified=false
core_cpp_source_present_at_commit=false  build_recipe_present=false
core_build_possible_with_pinned_commit=false  prebuilt_use_authorized=false
execution_allowed=false  final_selection_allowed=false  human_authorization_required=true
```

## Principais achados (resumo)

- **W1 (ALTO):** o commit fixado em `rock_win32` **não** contém fonte C++/Qt nem
  receita de build; o núcleo é distribuído **apenas** como binário prebuilt em
  `win32/`. "Compilar do fonte" **não** é satisfeito por esta branch → build do
  fonte **bloqueado**; caminho do núcleo é decisão humana separada (2P-E-A).
- **W2/W3 (ALTO):** patches sensíveis presentes (`CustomDLL` injeta DLL arbitrária;
  `DisableProtect`, `DisableEncr`, `EnableProxy`). Nenhum é necessário ao primeiro
  acesso; todos exigem decisão separada.
- **W8 (INFORMATIVO):** nenhuma superfície de rede, auto-update ou telemetria foi
  encontrada no conjunto de **scripts** inspecionado (o binário do núcleo não foi
  auditado estaticamente).

## Validação

O script [`scripts/validate-warp-audit.py`](../../scripts/validate-warp-audit.py)
valida os cinco JSONs de auditoria contra os schemas e contra regras de segurança
(SHA de 40/64 caracteres, flags de build/execução/uso-do-prebuilt/modificação e de
decisão proibidas em `true`, template de decisão em branco, referências existentes,
consistência pacote/registro, ausência de IP, senha, token e caminho pessoal) e —
desde a ETAPA 2P-E-A2 — cada **registro real** em [`decisions/`](decisions/): que o
template continua vazio, que o registro real contém a decisão, que a opção é
`PREBUILT_PATH`, que nenhuma autorização operacional está `true`, que
identidade/autoridade não são placeholders, que a data é válida, que justificativa e
condições não estão vazias, que pacote e registro usam o mesmo commit fixado e que
propriedades extras são rejeitadas. Desde a ETAPA 2P-E-B-PREBUILT também valida os
**templates de planejamento** ([`binary-audit-plan.example.json`](binary-audit-plan.example.json)
e [`binary-audit-gate-record.example.json`](binary-audit-gate-record.example.json)):
gates com IDs únicos e ordenados, `STOP_PATH` previsto, critérios de interrupção não
vazios, conjuntos exatos de patches bloqueados/candidatos, commit consistente com o
registro 2P-E-A2, template de gate em branco, ausência de comando de download, de URL
direta para binário, de comando de execução do WARP/cliente, de hash de binário como
evidência e de texto que sugira aprovação implícita do prebuilt; e confirma que as
palavras-chave dos schemas são implementadas pelo validador. Usa **apenas a
biblioteca padrão** do Python e não acessa a rede.

## Decisão do caminho do núcleo (2P-E-A)

A investigação do caminho do núcleo e o pacote de decisão humana estão em
[`core-path-decision-package.example.json`](core-path-decision-package.example.json)
/ [`core-path-decision-record.example.json`](core-path-decision-record.example.json)
e em [docs/31](../../docs/31-decisao-caminho-nucleo-warp.md): fonte C++/Qt
**não localizada**; prebuilt de origem oficial com **proveniência parcial** (custody
FRACA); **nenhuma opção selecionada**, **nenhuma autorização** concedida.

A decisão humana (2P-E-A2) está registrada em
[`decisions/core-path-decision-record-2026-07-31.json`](decisions/core-path-decision-record-2026-07-31.json)
e em [docs/32](../../docs/32-registro-decisao-caminho-nucleo-warp.md):
`PREBUILT_PATH` foi **selecionado apenas para planejamento** da auditoria binária
offline. O prebuilt **não** foi materializado nem executado; **todas** as flags
operacionais permanecem `false`; o template continua **em branco**; o merge do PR
**não** autoriza a próxima ação; **cada gate futuro exige decisão humana separada**.

## Plano da auditoria binária offline (2P-E-B-PREBUILT)

O **plano** da futura auditoria binária offline está em
[`binary-audit-plan.example.json`](binary-audit-plan.example.json) e em
[docs/33](../../docs/33-plano-auditoria-binaria-offline-warp.md): **17 gates
independentes** (0–16), cada um com decisão humana própria e `STOP_PATH`. Estes são
**artefatos de planejamento** — templates. **Nenhum** binário foi baixado,
materializado, extraído ou executado; **nenhum** gate operacional está autorizado;
todas as autorizações operacionais permanecem `false`; o merge do PR **não** autoriza
o GATE 1. O template de decisão por gate
([`binary-audit-gate-record.example.json`](binary-audit-gate-record.example.json))
permanece em branco; o **futuro registro real** de cada gate deverá ser criado em
diretório separado, autorizando **no máximo um gate**, sem autorização transitiva.

## Autorização do GATE 0 (2P-E-C0-A)

A autorização humana **exclusiva do GATE 0** (reconfirmação de proveniência por
metadados) está registrada em
[`decisions/binary-audit-gate-00-decision-record-2026-07-31.json`](decisions/binary-audit-gate-00-decision-record-2026-07-31.json)
e em [docs/34](../../docs/34-registro-autorizacao-gate-0-proveniencia-warp.md):
`GATE 0 AUTORIZADO — AINDA NÃO INICIADO`. Apenas
`provenance_reconfirmation_authorized` (mais as flags de decisão) está `true`; todas
as demais permanecem `false`. **Nenhuma** consulta upstream foi realizada nesta
etapa; **nenhuma** evidência coletada; o **GATE 1 continua proibido**; o merge do
registro **não** executa o GATE 0. A execução ocorrerá em etapa futura e separada
(2P-E-C0-B), somente por metadados oficiais.

## Propriedade intelectual

WARP é **GPL-3.0** (uso apenas local; binário não versionado no FaithRO). `Ragexe`,
GRF, DLLs e assets da Gravity são **proprietários** — proibido versionar, hospedar,
empacotar ou compartilhar (ver [docs/16](../../docs/16-politica-distribuicao-cliente.md)).

## Referências

- [docs/28](../../docs/28-decisao-ferramenta-preparacao-cliente.md) — decisão da ferramenta.
- [docs/29](../../docs/29-compatibilidade-cliente-2021-11-05-packetver.md) — compatibilidade do cliente.
- [docs/30](../../docs/30-auditoria-estatica-warp.md) — relatório desta auditoria.
- [docs/31](../../docs/31-decisao-caminho-nucleo-warp.md) — decisão do caminho do núcleo.
- [docs/32](../../docs/32-registro-decisao-caminho-nucleo-warp.md) — registro da decisão humana.
- [docs/33](../../docs/33-plano-auditoria-binaria-offline-warp.md) — plano da auditoria binária offline.
- [docs/34](../../docs/34-registro-autorizacao-gate-0-proveniencia-warp.md) — autorização do GATE 0.
- [docs/16](../../docs/16-politica-distribuicao-cliente.md) — política de distribuição.
