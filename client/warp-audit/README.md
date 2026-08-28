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
| [`evidence/binary-audit-gate-00-provenance-evidence-2026-08-01.json`](evidence/binary-audit-gate-00-provenance-evidence-2026-08-01.json) | (2P-E-C0-B) Evidência **real** da execução do GATE 0 por metadados oficiais: `COMPLETED_PASS`; proveniência consistente; **nenhum** conteúdo de blob acessado; Git object ID ≠ SHA-256 local; GATE 1 ainda proibido. |
| [`decisions/binary-audit-gate-01-decision-record-2026-08-01.json`](decisions/binary-audit-gate-01-decision-record-2026-08-01.json) | (2P-E-C1-A) Registro **real** da autorização humana **exclusiva do GATE 1** (autorização para materialização): `AUTHORIZE_MATERIALIZATION`; **decisão-humana-apenas** (nada materializado/baixado/hasheado/executado); escopo fechado ao blob fixado; `materialization_authorized=true`; **GATE 2 não autorizado**. |
| [`decisions/binary-audit-gate-02-decision-record-2026-08-01.json`](decisions/binary-audit-gate-02-decision-record-2026-08-01.json) | (2P-E-C2-A) Registro **real** da autorização humana **exclusiva do GATE 2** (materialização e integridade local): `AUTHORIZE_GATE_2`; `gate_2_authorized=true`, `hashing_authorized=true`; **GATE 3 não autorizado**. |
| [`evidence/binary-audit-gate-02-integrity-evidence-2026-08-01.json`](evidence/binary-audit-gate-02-integrity-evidence-2026-08-01.json) | (2P-E-C2-A) Evidência **real** do GATE 2: `COMPLETED_PASS`; **1** blob materializado fora do repo, tamanho `1137152` e Git blob OID **iguais** aos esperados; SHA-256 local registrado (≠ Git OID); arquivo **removido**; nenhuma execução/inspeção/sandbox/distribuição; **binário não versionado**. |
| [`decisions/binary-audit-gate-03-decision-record-2026-08-03.json`](decisions/binary-audit-gate-03-decision-record-2026-08-03.json) | (2P-E-C3) Registro **real** da autorização humana **exclusiva do GATE 3** (identidade e assinatura estática offline): `AUTHORIZE_GATE_3`; `gate_3_authorized=true`, materialização temporária + hashing + inspeção de identidade/Authenticode `true`; **GATE 4 não autorizado**. |
| [`evidence/binary-audit-gate-03-identity-signature-evidence-2026-08-03.json`](evidence/binary-audit-gate-03-identity-signature-evidence-2026-08-03.json) | (2P-E-C3 / **revisão 2P-E-C3-R1**) Evidência **real** do GATE 3, agora `EVIDENCE_INVALIDATED_PENDING_REPEAT`: o `COMPLETED_PASS` foi **suspenso** (D1-D4). Fatos do GATE 2 (blob OID/tamanho/SHA-256) **preservados**; identidade PE (`size_of_optional_header=267` == magic PE32) e assinatura **pendentes de reconfirmação**; leitura estática explícita (sem `opened` ambíguo); OpenSSL `invoked=false`/`exit_code=null`; **nenhuma nova materialização**; **binário não versionado**. |
| [`decisions/binary-audit-gate-04-decision-record-2026-08-05.json`](decisions/binary-audit-gate-04-decision-record-2026-08-05.json) | (2P-E-C4-AUTH) Registro **real** da autorização humana **exclusiva do GATE 4** (inventário PE estático offline): `AUTHORIZE_GATE_4_EXECUTION` (decisor `BrunoMNoronha`); `gate_4_authorized=true`, `gate_4_execution_authorized=true`, `static_inventory_authorized=true`; **DECISÃO AUTORIZADA — EXECUÇÃO NÃO INICIADA** (`execution_state=AUTHORIZED_NOT_STARTED`); presa ao squash `a5843c3` (PR #54) e aos blobs `f223ae7b`/`fdc79947`; `execution_authorized=false`, `gate_5_authorized=false`; **GATE 5 não autorizado**. Execução em PR separado. |
| [`evidence/binary-audit-gate-04-pass-evidence-2026-08-05.json`](evidence/binary-audit-gate-04-pass-evidence-2026-08-05.json) | (2P-E-C4-EXEC) Evidência **real** da execução do GATE 4: **`COMPLETED_PASS`**. Identidade reconfirmada igual ao GATE 2/3 (blob `c853da42…`, 1137152 bytes, SHA-256 `345f3464…`); analisador revisado (`f223ae7b`) invocado **uma vez** (só-leitura; `executed/loaded=false`); saída presa por SHA-256 `84c3c49a…`; binário/diretório removidos; `binary_versioned=false`, `gate_5_authorized=false`. `COMPLETED_PASS` **não** aprova o binário. |
| [`evidence/binary-audit-gate-04-static-inventory-output-2026-08-05.json`](evidence/binary-audit-gate-04-static-inventory-output-2026-08-05.json) | (2P-E-C4-EXEC) Saída **byte-fixada** (UTF-8/LF, SHA-256 `84c3c49a…`) do inventário PE estático do WARP produzida pelo analisador revisado: fatos estruturais, heurísticas e indicadores textuais **sanitizados** (sem bytes brutos, `bCertificate`, base64, segredo, IP ou caminho pessoal). Achados **não** são veredito. |
| [`binary-audit-gate-05-decision-package.example.json`](binary-audit-gate-05-decision-package.example.json) | (2P-E-C5-PREP) Pacote de **preparação** da futura decisão humana do **GATE 5** (verificações locais de segurança): referencia o GATE 4 integrado (squash `03348d7`, output SHA-256 `84c3c49a…`), a definição canônica do GATE 5, as lacunas e as opções A–D. `state=PENDING_HUMAN_DECISION`; **não** concede autorização (`gate_5_authorized=false`, `execution_authorized=false`, `client_preparation_authorized=false`). Ver [docs/44](../../docs/44-gate-5-decisao-e-plano.md). |
| [`binary-audit-gate-05-input.example.json`](binary-audit-gate-05-input.example.json) | (2P-E-C5-TOOLING-PREP) Exemplo do **contrato de entrada** do orquestrador estático do GATE 5 ([`scripts/warp-audit-gate-05.py`](../../scripts/warp-audit-gate-05.py)): aponta para **fixture sintética** (nunca o WARP real); `network_policy=blocked`, `execution_policy=artifact_never_executed`; flags `false`. |
| [`binary-audit-gate-05-evidence.example.json`](binary-audit-gate-05-evidence.example.json) | (2P-E-C5-TOOLING-PREP) Exemplo de **evidência** gerada por **fixture sintética**: `outcome=FIXTURE_VALIDATION_PASS` (nunca `GATE_PASSED`); `artifact_executed=false`, `network_access=false`; resultados sanitizados; flags `false`. Ver [docs/45](../../docs/45-gate-5-preparacao-operacional.md). |
| [`decisions/binary-audit-gate-05-decision-record-2026-08-28.json`](decisions/binary-audit-gate-05-decision-record-2026-08-28.json) | (2P-E-C5-REAL-AUTH-DECISION) Registro **real** da autorização humana condicional da execução real do **GATE 5** (verificações locais de segurança): `AUTHORIZE_GATE_5_LOCAL_EXECUTION` (decisor `BrunoMNoronha`); fecha lacunas do doc 44 §10; `gate_5_authorized=true`, `local_security_scan_authorized=true`, `temporary_materialization_authorized=true`; **DECISÃO AUTORIZADA — EXECUÇÃO NÃO INICIADA** (`execution_state=AUTHORIZED_NOT_STARTED`); presa ao squash `80f6f7a` (PR #59) e aos blobs `952df939`/`0af39872`; `execution_authorized=false`, `client_preparation_authorized=false`. Execução em PR separado. Ver [docs/46](../../docs/46-decisao-execucao-real-gate-5-verificacoes-locais.md). |
| [`schemas/`](schemas/) | JSON Schemas (draft-07) dos artefatos, incluindo `core-path-decision-record-real.schema.json`, `binary-audit-plan.schema.json`, `binary-audit-gate-record.schema.json`, `binary-audit-gate-00-decision-record-real.schema.json`, `binary-audit-gate-00-provenance-evidence.schema.json`, `binary-audit-gate-01-decision-record-real.schema.json`, `binary-audit-gate-02-decision-record-real.schema.json`, `binary-audit-gate-02-integrity-evidence.schema.json`, `binary-audit-gate-03-decision-record-real.schema.json`, `binary-audit-gate-03-identity-signature-evidence.schema.json` e (convenção da repetição corretiva, sem registros reais) `binary-audit-gate-03-corrective-repeat-decision-record-real.schema.json`, `binary-audit-gate-03-corrective-repeat-pass-evidence.schema.json`, `binary-audit-gate-03-corrective-repeat-fail-evidence.schema.json`, `binary-audit-gate-03-corrective-repeat-stopped-evidence.schema.json` e `binary-audit-gate-03-corrective-repeat-parser-output.schema.json`; (convenção da **preparação do GATE 4**, sem registros reais) `binary-audit-gate-04-decision-record-real.schema.json`, `binary-audit-gate-04-pass-evidence.schema.json`, `binary-audit-gate-04-fail-evidence.schema.json`, `binary-audit-gate-04-stopped-evidence.schema.json` e `binary-audit-gate-04-static-inventory-output.schema.json`; (convenção da **preparação da decisão do GATE 5**, sem registros reais) `binary-audit-gate-05-decision-package.schema.json`; (convenção do **tooling do GATE 5**, sem registros reais) `binary-audit-gate-05-input.schema.json` e `binary-audit-gate-05-evidence.schema.json`; e (registro real do **GATE 5**) `binary-audit-gate-05-decision-record-real.schema.json`. |

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
palavras-chave dos schemas são implementadas pelo validador. Desde a ETAPA
2P-E-C0-B valida a **evidência real do GATE 0** e, desde a ETAPA 2P-E-C1-A, o
**registro real do GATE 1** ([`decisions/binary-audit-gate-01-decision-record-2026-08-01.json`](decisions/binary-audit-gate-01-decision-record-2026-08-01.json)):
decisão `AUTHORIZE_MATERIALIZATION`, escopo fechado ao blob fixado por `const`,
`materialization_authorized=true` como único grant, todos os demais pontos críticos
`false` (sem autorização transitiva), `binary_sha256=null` e demais invariantes de
não-materialização, e cross-checks com o plano, a decisão e a evidência do GATE 0 e
com o squash do PR #48. Os testes positivos e negativos estão em
[`scripts/test-warp-audit-gate-01.py`](../../scripts/test-warp-audit-gate-01.py).
Desde a ETAPA 2P-E-C2-A valida a **decisão e a evidência do GATE 2**
([`decisions/binary-audit-gate-02-decision-record-2026-08-01.json`](decisions/binary-audit-gate-02-decision-record-2026-08-01.json)
e [`evidence/binary-audit-gate-02-integrity-evidence-2026-08-01.json`](evidence/binary-audit-gate-02-integrity-evidence-2026-08-01.json)):
decisão `AUTHORIZE_GATE_2` com escopo fechado, evidência `COMPLETED_PASS` com
`materialized_file_count=1`, tamanho e Git blob OID iguais aos esperados, SHA-256 local
válido (64 hex) e **distinto** do Git OID, `temporary_file_removed=true`,
`gate_3_authorized=false`, e cross-checks com o plano, o GATE 1 e a evidência do
GATE 0 e com o squash do PR #49 (testes em
[`scripts/test-warp-audit-gate-02.py`](../../scripts/test-warp-audit-gate-02.py)). Usa
**apenas a biblioteca padrão** do Python e não acessa a rede.

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

## Resultado do GATE 0 (2P-E-C0-B)

O GATE 0 foi **executado por metadados oficiais** — evidência em
[`evidence/binary-audit-gate-00-provenance-evidence-2026-08-01.json`](evidence/binary-audit-gate-00-provenance-evidence-2026-08-01.json)
e em [docs/35](../../docs/35-resultado-gate-0-proveniencia-warp.md): resultado
`COMPLETED_PASS` (`GATE 0 CONCLUÍDO — APROVADO POR METADADOS`). Repositório, commit,
árvore, caminho, tipo de objeto, **Git blob object ID** e tamanho **coincidem** com os
registros internos; licença GPL-3.0 consistente. **Nenhum** conteúdo de blob foi
acessado; **nenhum** binário foi baixado, materializado, hasheado, inspecionado ou
executado. O `git_blob_oid` é o identificador do objeto Git informado pelo upstream —
**não** é um SHA-256 calculado localmente sobre o binário. A aprovação por metadados
**não** significa confiança/segurança do binário e **não** autoriza o GATE 1: qualquer
avanço exige **nova decisão humana** (`AUTHORIZE_GATE_1` / `REPEAT_GATE_0` /
`STOP_PATH`).

## Resultado do GATE 3 (2P-E-C3) e revisões corretivas (2P-E-C3-R1 … R4.1)

O GATE 3 foi executado por inspeção estática offline — decisão em
[`decisions/binary-audit-gate-03-decision-record-2026-08-03.json`](decisions/binary-audit-gate-03-decision-record-2026-08-03.json),
evidência em
[`evidence/binary-audit-gate-03-identity-signature-evidence-2026-08-03.json`](evidence/binary-audit-gate-03-identity-signature-evidence-2026-08-03.json)
e em [docs/39](../../docs/39-resultado-gate-3-identidade-assinatura-warp.md).

Uma **revisão corretiva independente (2P-E-C3-R1)** **suspendeu** o `COMPLETED_PASS`
original e o estado da evidência passou a `EVIDENCE_INVALIDATED_PENDING_REPEAT`:

- **D1** — `opened=false` era ambíguo (o conteúdo foi lido para inspeção estática);
  substituído por `file_read_for_static_inspection=true` + `launched`/`executed`/
  `loaded_as_executable=false`.
- **D2** — `size_of_optional_header=267` (== magic PE32 `0x010B`): forte indício de
  leitura de campo no offset incorreto; marcado `MEASUREMENT_REQUIRES_RECONFIRMATION`
  (não alterado por suposição).
- **D3** — o parser era de scratchpad, não versionado; foi versionado o inspetor
  revisável [`scripts/inspect-warp-pe-identity.py`](../../scripts/inspect-warp-pe-identity.py)
  (offline, _bounds checking_) com fixtures sintéticas em
  [`scripts/test-warp-pe-identity.py`](../../scripts/test-warp-pe-identity.py).
- **D4** — OpenSSL registrava `exit_code=-1` sem ter sido invocado; corrigido para
  `invoked=false` / `exit_code=null`.

Os **fatos do GATE 2** (blob OID `c853da42…`, tamanho `1137152`, SHA-256 `345f3464…`,
materialização e limpeza anteriores, ausência de execução, binário não versionado)
são **preservados**. A identidade PE e o estado da assinatura ficam **pendentes de
reconfirmação** por **repetição controlada**. **Nenhuma nova materialização** ocorreu;
o inspetor revisável **não** foi executado sobre o `WARP.exe`. O **GATE 4 permanece
não autorizado**; a repetição corretiva do GATE 3 exige **nova decisão humana**
(proposta: `AUTHORIZE_CORRECTIVE_REPEAT_GATE_3` / `STOP_PATH`). Os testes positivos e
negativos estão em [`scripts/test-warp-audit-gate-03.py`](../../scripts/test-warp-audit-gate-03.py).

**Endurecimento 2P-E-C3-R2:** o inspetor [`scripts/inspect-warp-pe-identity.py`](../../scripts/inspect-warp-pe-identity.py)
**removeu** a falsa regra universal `SizeOfOptionalHeader == Magic` (a igualdade não
viola o PE; `soh=267` é legítimo) e passou a fazer **parsing estrutural da Certificate
Table** (`WIN_CERTIFICATE`: bounds, alinhamento a 8 bytes, `dwLength`, progressão sem
loop, soma coincidente), emitindo **apenas metadados** — nunca o `bCertificate`. As
fixtures em [`scripts/test-warp-pe-identity.py`](../../scripts/test-warp-pe-identity.py)
foram ampliadas (soh=267 válido + 17 cenários da tabela). A **cadeia da repetição
corretiva** foi preparada como **convenção** (schemas
`binary-audit-gate-03-corrective-repeat-*`), **sem** criar decisão ou evidência reais:
a futura decisão referenciará a decisão original, a evidência invalidada, a revisão R1,
o commit exato e os Git blob OIDs do parser e dos testes, o blob imutável do WARP e o
escopo de **exatamente uma** repetição; a evidência invalidada **nunca** volta a
`COMPLETED_PASS`.

**Endurecimento 2P-E-C3-R3:** o inspetor passou a validar a **Section Table**
(`NumberOfSections` 1–96 + flag `IMAGE_FILE_EXECUTABLE_IMAGE`; offset/tamanho/fim;
`within_file`), `SizeOfHeaders` (coerente com o fim da tabela, o arquivo e o
`FileAlignment`) e `SectionAlignment`/`FileAlignment`, sem inspecionar o conteúdo das
seções; `pe_valid` foi substituído por `pe_headers_structurally_parseable` (sem
overclaim). A Certificate Table exige `offset >= SizeOfHeaders` (nunca sobreposta aos
cabeçalhos) e registra `declared_dw_length`/`aligned_span`/`padding_length`/
`padding_zero_filled` (padding só-zero), reconhecendo `0x0009` (`WIN_CERT_TYPE_PKCS1_SIGN`).
As fixtures foram reconstruídas com Section Table válida. O modelo de resultado da
repetição virou **três schemas** (`...-{pass,fail,stopped}-evidence`) — FAIL não exige
`identity_matches_gate_2`, STOPPED não exige conclusão. A **proveniência** é amarrada ao
conteúdo real: o validador recalcula o Git blob OID do parser e dos testes
(`SHA-1("blob <size>\0"+content)`, offline) e a saída exata do parser é um artefato
textual separado (`...-parser-output-*.json`) referenciado por SHA-256. O orquestrador
reprova duplicações (≤1 decisão, ≤1 evidência, ≤1 saída) e segunda repetição. **Nenhum
registro real** existe nesta etapa.

**Atomicidade 2P-E-C3-R4:** o orquestrador trata `decisão → evidência → saída do
parser` como unidade transacional e **reprova órfãos** (evidência/saída sem decisão;
saída sem evidência). A saída do parser é presa aos **bytes exatos** (SHA-256 sobre os
bytes reais; sem BOM/CRLF; newline final único; sem chaves duplicadas; `raw == forma
determinística`) e o seu schema é **fechado** (`additionalProperties=false` em todos os
níveis, com `security_scan` e proibição de `bCertificate`/base64). As referências de
saída/decisão exigem **igualdade exata** de caminho. A **proveniência** do parser **e
dos testes** é recalculada offline (`git_blob_oid_for_bytes`) e conferida contra a
decisão **e** a evidência, exigindo o mesmo commit; `None` é erro. Os campos duplicados
na evidência PASS devem ser **idênticos** à saída real (fonte primária). PASS/FAIL/
STOPPED têm schemas distintos e o parser emite `certificate_table.within_file` sempre,
permitindo fechar o schema da saída.

**Referência do FAIL e invariantes 2P-E-C3-R4.1:** o caminho `COMPLETED_FAIL` passou a
prender a saída com a **mesma igualdade exata** do PASS — quando
`parser_output_produced=true`, exige `parser_output_raw`/`present_output_name`/
`parser_output_path` não nulos, `reviewed_parser_output_ref.path` **igual** ao caminho
canônico do único arquivo (não basta `endswith`) e SHA-256 dos bytes reais. Uma função
comum (`validate_parser_execution_state`) aplica em Python os invariantes de
`parser_invoked`/`parser_completed`/`parser_output_produced` para PASS/FAIL/STOPPED:
FAIL admite **apenas** `PRE_PARSER_FAIL` (`false/false/false`),
`PARSER_ERROR_WITHOUT_OUTPUT` (`true/false/false`) e `POST_OUTPUT_FAIL`
(`true/true/true`) — qualquer outra combinação é reprovada. STOPPED não modela
`parser_completed` (limitação documentada); o campo não foi inventado. O **parser e os
testes do parser não mudaram** (blob OIDs inalterados) e **nada** foi materializado,
executado ou registrado como repetição real; a evidência histórica permanece
`EVIDENCE_INVALIDATED_PENDING_REPEAT` e o **GATE 4 continua não autorizado**.

**Repetição corretiva executada (2P-E-C3-REPEAT) — COMPLETED_PASS:** sob a decisão
humana real `AUTHORIZE_CORRECTIVE_REPEAT_GATE_3`
([registro](decisions/binary-audit-gate-03-corrective-repeat-decision-record-2026-08-03.json)),
executou-se **uma** repetição controlada: materialização única do blob `c853da42…` pela
API oficial Git Data do GitHub (por object ID) em diretório temporário fora do repo,
identidade reconfirmada **igual** ao GATE 2 (`1137152` / `c853da42…` / `sha256 345f3464…`),
e **apenas** o parser revisado executado para leitura estática. Resultado: `PE32`,
5 seções, **`SizeOfOptionalHeader=224`** e magic `0x010b` separados (reconfirmando o
achado D2 da R1), Certificate Table `present=false` (assinatura ausente ≠ malware). A
[saída do parser](evidence/binary-audit-gate-03-corrective-repeat-parser-output-2026-08-03.json)
foi versionada e presa por bytes/referência à
[evidência `COMPLETED_PASS`](evidence/binary-audit-gate-03-corrective-repeat-evidence-2026-08-03.json).
Binário temporário removido; **não** executado/carregado; sem cliente/`Ragexe`/VPS; GATE 4
e segunda repetição **não** autorizados; evidência histórica invalidada **preservada**.
PASS significa **apenas** que a repetição controlada do GATE 3 foi concluída.

## Preparação do GATE 4 (2P-E-C4-PREP)

A **ferramenta** do futuro GATE 4 (inventário PE **estático offline**) foi preparada,
testada e documentada — **sem** executar o GATE 4 e **sem** materializar/inspecionar o
`WARP.exe` (ver [docs/40](../../docs/40-preparacao-gate-4-inventario-pe-estatico-warp.md)):

- **Analisador** [`scripts/inspect-warp-pe-static.py`](../../scripts/inspect-warp-pe-static.py):
  stdlib apenas, leitura binária, _bounds checking_, **fail-closed**, saída JSON
  determinística (UTF-8 sem BOM, LF, `indent=2`, `sort_keys`, newline único) que **separa**
  fatos estruturais, heurísticas e limitações; **nunca** emite bytes brutos, `bCertificate`,
  base64, dump integral, segredos ou caminhos pessoais; strings **sanitizadas e limitadas**;
  classificação de imports por **tabela fechada**. É **separado** do inspetor do GATE 3
  (OIDs `3442ddfc…`/`6d7cab1b…` **inalterados**).
- **Testes com fixtures sintéticas** [`scripts/test-warp-pe-static.py`](../../scripts/test-warp-pe-static.py)
  (removidas ao final, inclusive após falha) e testes do validador
  [`scripts/test-warp-audit-gate-04.py`](../../scripts/test-warp-audit-gate-04.py).
- **Schemas fechados** (`additionalProperties=false`): saída do inventário, decisão real
  (`AUTHORIZE_GATE_4_EXECUTION`) e evidência **PASS/FAIL/STOPPED** — todos com
  `gate_5_authorized const:false`. **Nenhum** registro real do GATE 4 existe nesta etapa.
- **Validador** (`gate-04-prep` em [`scripts/validate-warp-audit.py`](../../scripts/validate-warp-audit.py)):
  confirma a convenção e a máquina de estados atômica (reprova decisão/evidência/saída
  prematura, órfãos, duplicação, autorização transitiva do GATE 5, saída com
  BOM/CRLF/base64/bytes brutos e estados impossíveis do analisador); exige
  `gate_4_real_decision_count=0`, `gate_4_real_evidence_count=0`,
  `gate_4_real_output_count=0`, `gate_4_authorized=false`, `gate_4_execution_authorized=false`.

A execução operacional do GATE 4 exige **nova decisão humana** em **PR separado**
(proposta: `AUTHORIZE_GATE_4_EXECUTION` / `STOP_PATH`), referenciando o squash integrado
desta preparação e os Git blob OIDs exatos do analisador e dos testes. O **GATE 5
permanece não autorizado**.

## Preparação da decisão do GATE 5 (2P-E-C5-PREP)

O GATE 4 foi executado e integrado (`COMPLETED_PASS`, squash `03348d7`, PR #57). Esta
etapa **apenas prepara** a futura decisão humana do **GATE 5** (verificações locais de
segurança) — ver [docs/44](../../docs/44-gate-5-decisao-e-plano.md). Classificação
**D2**: o GATE 5 está nomeado/definido em alto nível na cadeia (doc 33 §11; plano
`gate_id=5`), mas a preparação operacional (ferramenta/schemas/evidência) **ainda não
existe**. O pacote estruturado correspondente é
[`binary-audit-gate-05-decision-package.example.json`](binary-audit-gate-05-decision-package.example.json)
(`state=PENDING_HUMAN_DECISION`), validado pelas regras genéricas do validador
(schema fechado + `security_scan` + `forbidden_flags`).

Esta etapa **não** executa o GATE 5, **não** repete o GATE 4, **não** altera a
saída/evidência do GATE 4, **não** materializa nem executa qualquer PE, **não** prepara
o cliente e **não** acessa a VPS. `gate_5_authorized=false`,
`execution_authorized=false`, `client_preparation_authorized=false`. Qualquer avanço
exige **nova decisão humana** em **PR separado**.

## Tooling do GATE 5 (2P-E-C5-TOOLING-PREP)

Após a decisão **Opção B** (doc 44), esta etapa prepara — **sem executar** — o
mecanismo do GATE 5: o orquestrador estático
[`scripts/warp-audit-gate-05.py`](../../scripts/warp-audit-gate-05.py) (stdlib,
fail-closed, sem rede, sem execução do artefato; `--validate-only`/`--fixture-mode`;
**modo real bloqueado** com `GATE 5 REAL EXECUTION IS NOT AUTHORIZED`), os contratos
fechados de entrada e evidência (`binary-audit-gate-05-input`/`-evidence`) e os testes
[`scripts/test-warp-audit-gate-05.py`](../../scripts/test-warp-audit-gate-05.py) **só
com fixtures sintéticas**. Adapters: `synthetic-local` (puro Python, habilitado em
fixture) e `windows-defender-local`/`yara-local` (**apenas contrato**, não executados,
exigem autorização futura). A evidência de exemplo é `FIXTURE_VALIDATION_PASS` —
**nunca** `GATE_PASSED`.

**Ferramenta preparada; testes somente sintéticos; GATE 5 não executado; scanner real
não utilizado; autorização continua falsa.** A execução real do GATE 5 exige **nova
decisão humana explícita** em **PR separado** (ver [docs/45](../../docs/45-gate-5-preparacao-operacional.md)).

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
- [docs/35](../../docs/35-resultado-gate-0-proveniencia-warp.md) — resultado do GATE 0 (metadados).
- [docs/39](../../docs/39-resultado-gate-3-identidade-assinatura-warp.md) — resultado do GATE 3 (identidade e assinatura).
- [docs/40](../../docs/40-preparacao-gate-4-inventario-pe-estatico-warp.md) — preparação do GATE 4 (inventário PE estático).
- [docs/42](../../docs/42-autorizacao-execucao-gate-4-inventario-pe-warp.md) — autorização do GATE 4 (inventário PE estático).
- [docs/43](../../docs/43-resultado-gate-4-inventario-pe-estatico-warp.md) — resultado do GATE 4 (inventário PE estático).
- [docs/44](../../docs/44-gate-5-decisao-e-plano.md) — preparação da decisão do GATE 5 (verificações locais).
- [docs/45](../../docs/45-gate-5-preparacao-operacional.md) — preparação operacional do GATE 5 (verificações locais).
- [docs/46](../../docs/46-decisao-execucao-real-gate-5-verificacoes-locais.md) — autorização condicional da execução real do GATE 5 (verificações locais).
- [docs/47](../../docs/47-provisao-laboratorio-gate-5.md) — especificação e auditoria de prontidão do laboratório para o GATE 5.
- [docs/16](../../docs/16-politica-distribuicao-cliente.md) — política de distribuição.
