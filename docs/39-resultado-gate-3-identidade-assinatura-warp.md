# Resultado do GATE 3 — identidade e assinatura estática offline do WARP

> **Estado atual:** `GATE 3 — REPETIÇÃO CORRETIVA EXECUTADA: COMPLETED_PASS`
> (decisão humana `AUTHORIZE_CORRECTIVE_REPEAT_GATE_3`, 2P-E-C3-REPEAT). A evidência
> histórica **permanece** `EVIDENCE_INVALIDATED_PENDING_REPEAT` e é preservada; o PASS
> vale para a **nova** evidência da repetição. Revisões prévias: **2P-E-C3-R1 … R4.1**.
> **Data da execução original:** 2026-08-03 · **Data da revisão corretiva:** 2026-08-03.
> **Escopo desta correção:** revisar os artefatos já versionados, corrigir schemas,
> validador, testes, documentação e semântica dos registros, e **versionar um parser
> PE offline revisável e testável** — **sem** repetir a materialização do `WARP.exe`.
> **Nenhuma nova materialização** ocorreu; **WARP não executado**; **`Ragexe`
> intocado**; **GATE 4 não autorizado**.
> Continua [37](37-resultado-gate-2-materializacao-integridade-warp.md); observa
> [33](33-plano-auditoria-binaria-offline-warp.md),
> [35](35-resultado-gate-0-proveniencia-warp.md) e
> [16](16-politica-distribuicao-cliente.md).

## 0. Revisão corretiva independente (2P-E-C3-R1)

Uma revisão independente do PR #52 encontrou problemas de **auditabilidade** na
evidência inicial e o resultado `COMPLETED_PASS` foi **suspenso**:

- **D1 — semântica ambígua de abertura.** A evidência registrava `opened=false`,
  embora o conteúdo **tenha sido lido** para SHA-256, Git object ID, parse do PE,
  busca de versão e inspeção da Certificate Table. Substituído por campos
  inequívocos: `file_read_for_static_inspection=true`, `launched=false`,
  `executed=false`, `loaded_as_executable=false`.
- **D2 — `size_of_optional_header=267`.** O valor `267` equivale a `0x010B`, que é o
  **magic de PE32**. Isso é **forte indício** de leitura do **campo no offset
  incorreto** (o parser de scratchpad lia `coff+20`, o início do Optional Header /
  Magic, em vez de `coff+16`). **Não** é conclusão definitiva; a medição foi marcada
  como `MEASUREMENT_REQUIRES_RECONFIRMATION` e **não** foi alterada por suposição
  (não vira `224`/`0xE0`).
- **D3 — parser não versionado.** O parser que produziu a evidência rodou em
  scratchpad e não estava disponível para revisão. Foi **versionado** um inspetor PE
  offline revisável, com _bounds checking_
  ([`scripts/inspect-warp-pe-identity.py`](../scripts/inspect-warp-pe-identity.py)),
  coberto por testes de **fixtures sintéticas**
  ([`scripts/test-warp-pe-identity.py`](../scripts/test-warp-pe-identity.py)).
- **D4 — OpenSSL não invocado.** A evidência registrava OpenSSL com `exit_code=-1`
  mesmo **sem** ter sido invocado. Corrigido: `available`/`invoked`/`completed`
  distintos e `exit_code=null` quando `invoked=false`.

Como o `WARP.exe` foi removido e **uma nova materialização não está autorizada**
nesta etapa, os campos produzidos pelo parser não versionado (identidade PE e estado
da assinatura) foram marcados como **pendentes de reconfirmação**; **não** foram
remedidos nem estimados.

## 0.1 Endurecimento e cadeia da repetição (2P-E-C3-R2)

Uma segunda revisão endureceu o inspetor e preparou a cadeia da repetição corretiva —
**sem** repetir a materialização e **sem** executar o parser sobre o `WARP.exe`:

- **Regra falsa removida.** O inspetor **não** rejeita mais um PE apenas porque
  `SizeOfOptionalHeader == Magic`. Essa igualdade numérica **não** viola o formato PE
  (`soh = 267` é um valor legítimo). A garantia contra o bug de offset (R1) é ler
  `SizeOfOptionalHeader` de `coff+16` e `Magic` do início do Optional Header — campos
  **separados** — exercitado por testes de regressão. Uma fixture sintética **válida**
  com `Magic=0x010b` e `SizeOfOptionalHeader=267` é aceita; a fixture `0xE0`→`224`
  continua provando que os offsets não se confundem. No validador, a exigência de
  reconfirmação do valor `267` passou a depender da **proveniência**
  (`produced_by=UNVERSIONED_SCRATCHPAD_PARSER`), **não** de uma regra geral.
- **Certificate Table estrutural.** O inspetor agora percorre a Certificate Table
  (`WIN_CERTIFICATE`) validando: índice só quando `NumberOfRvaAndSizes > 4`; primeiro
  campo é **file offset** (não RVA); par offset/tamanho ambos zero ou ambos não-zero
  (parcial → rejeitado); presença exige bounds, alinhamento a 8 bytes, tamanho ≥ 8 e
  ao menos um cabeçalho; percorre entradas por `align8(dwLength)` com `dwLength ≥ 8`,
  sem loop, com soma final coincidente. Emite **apenas metadados estruturais**
  (`dwLength`, `revision`, `certificate_type`); **nunca** o conteúdo `bCertificate`.
- **Fixtures ampliadas.** 17 novos cenários de Certificate Table (ausente, par parcial,
  desalinhado, `size<8`, `dwLength<8`, além da tabela, truncada, uma/duas entradas
  válidas, progressão alinhada, padding, soma incompatível, ausência de conteúdo no
  JSON, sem execução, fixtures removidas).
- **Cadeia da repetição preparada** (convenção, **sem** registros reais): schemas
  `binary-audit-gate-03-corrective-repeat-decision-record-real.schema.json` e
  `binary-audit-gate-03-corrective-repeat-evidence.schema.json`. A futura decisão
  referenciará a decisão original, a **evidência invalidada** (que permanece
  histórica), a revisão R1, o **commit exato** e os **Git blob OIDs** do parser e dos
  testes, o blob imutável do WARP e o escopo de **exatamente uma** repetição. A futura
  evidência preservará `original_invalidated_evidence_ref`,
  `corrective_repeat_decision_ref`, `reviewed_parser_ref`,
  `reviewed_parser_git_blob_oid` e `reviewed_parser_test_ref`. O validador impede que a
  evidência histórica invalidada volte a `COMPLETED_PASS`.

**Nenhuma materialização** ocorreu; o parser revisado **ainda não foi executado sobre
o WARP.exe**; a evidência invalidada **permanece histórica**; a repetição produzirá
**decisão e evidência separadas**; o **GATE 4 permanece não autorizado**.

## 0.2 Section Table, fixtures e estados de falha (2P-E-C3-R3)

Uma terceira revisão finalizou o inspetor e o modelo da repetição — ainda **sem**
materializar nem executar o parser sobre o `WARP.exe`:

- **Section Table validada.** O inspetor passou a validar `NumberOfSections`
  (`>=1` e `<=96`, com a flag `IMAGE_FILE_EXECUTABLE_IMAGE` presente antes de tratar a
  estrutura como imagem executável — a flag **não** prova segurança nem
  executabilidade operacional) e a **Section Table**
  (`section_table_offset = pe_sig + 4 + COFF + SizeOfOptionalHeader`,
  `entry_size = 40`, `end_offset`, `within_file`, `contents_inspected=false`), além de
  `SizeOfHeaders` (`>= section_table_end`, `<= file_size`, alinhado a `FileAlignment`)
  e dos metadados `SectionAlignment`/`FileAlignment`. **Sem** interpretar o conteúdo
  das seções (isso é GATE 4).
- **Sem overclaim.** `pe_valid` foi substituído por
  `pe_headers_structurally_parseable` (+ `full_pe_validation_performed=false`,
  `section_contents_validated=false`, `security_evaluation_performed=false`): os
  cabeçalhos examinados são coerentes e a Section Table declarada cabe no arquivo — **não**
  houve validação integral das seções, execução ou avaliação de segurança.
- **Fixtures reconstruídas.** Cada fixture válida contém DOS + PE + COFF + Optional
  Header + `N` cabeçalhos de seção (40 bytes) + padding até `SizeOfHeaders`, e a
  Certificate Table (quando presente) **somente após `SizeOfHeaders`** — nunca
  sobreposta à Section Table/aos cabeçalhos. Cobertura: 1 e 5 seções; `NumberOfSections`
  0 e 97; Section Table truncada; headers incompletos; `section_table_end > file_size`;
  `SizeOfHeaders` menor que o fim da tabela, maior que o arquivo e desalinhado; flag
  executável ausente; cert sobreposta à Section Table e aos headers (rejeitadas); cert
  após `SizeOfHeaders` (aceita); PE32/PE32+; `soh=267` e regressão `0xE0→224`.
- **WIN_CERTIFICATE.** Registra `declared_dw_length`, `aligned_span`, `padding_length`
  e `padding_zero_filled`; avança por `align8(dwLength)` (aceitando `dwLength` não
  múltiplo de 8), confirma que o padding físico cabe na tabela e contém **apenas
  zeros**, reconhece o tipo `0x0009` (`WIN_CERT_TYPE_PKCS1_SIGN`) e **não** declara
  validade criptográfica.
- **Estados PASS/FAIL/STOPPED separados.** O modelo de resultado deixou de exigir os
  mesmos campos completos para todos os outcomes. São **três schemas** distintos:
  `...-pass-evidence` (identidade igual ao GATE 2, cabeçalhos parseáveis, saída do
  parser amarrada por SHA-256, limpeza), `...-fail-evidence` (motivo de falha; **não**
  exige `identity_matches_gate_2`) e `...-stopped-evidence` (motivo de interrupção;
  **não** exige conclusão nem campos completos). A lógica condicional é implementada
  em Python (o mini-validador não suporta `oneOf`/`if-then-else`).
- **Proveniência amarrada ao conteúdo.** O validador **recalcula localmente** o Git
  blob OID do parser e dos testes (`SHA-1("blob <size>\0"+content)`, sem subprocess/rede)
  e confere contra os valores registrados; o commit é confirmado pelo **gate Git
  externo** e os blobs pelo **validador offline**. A saída exata do parser é um
  artefato textual separado (`...-parser-output-*.json`, só metadados) referenciado por
  `reviewed_parser_output_ref` + `reviewed_parser_output_sha256`, com cruzamento de
  campos.
- **Sem duplicação.** O orquestrador exige **no máximo** 1 decisão, 1 evidência e 1
  saída do parser de repetição, com referências casadas, e reprova segunda repetição.
  Enquanto não houver autorização: **0** de cada.

## 0.3 Atomicidade, bytes exatos e proveniência (2P-E-C3-R4)

A quarta revisão fechou a máquina de estados e a proveniência da repetição — ainda
**sem** materializar nem executar o parser sobre o `WARP.exe`:

- **Artefatos como unidade transacional.** O orquestrador trata `DECISÃO → EVIDÊNCIA →
  SAÍDA DO PARSER` como uma unidade e **reprova órfãos**: evidência ou saída **sem
  decisão**; saída **sem evidência** (mesmo com decisão presente). Sem autorização, o
  estado exigido é **0/0/0**; autorizado-mas-não-executado permite **1 decisão / 0 / 0**.
- **PASS/FAIL/STOPPED honestos.** PASS exige `parser_execution` (`invoked`/`completed`/
  `output_produced=true`) e a **saída real obrigatória**. FAIL declara
  `parser_invoked`/`parser_completed`/`parser_output_produced`: falha antes do parser
  (sem saída), falha do parser sem JSON válido (sem fabricar saída) ou falha após uma
  saída válida (com referência+hash). STOPPED registra `stage_when_stopped`,
  `materialization_started`, `parser_invoked`, `parser_output_produced=false`,
  `cleanup_required`/`cleanup_attempted`/`cleanup_completed`; **não** pode ter saída.
- **Saída presa aos bytes exatos.** O validador lê o arquivo em modo **binário**,
  calcula o **SHA-256 diretamente sobre esses bytes** e o compara ao registrado;
  rejeita **BOM**, **CRLF**, ausência/duplicação de newline final e dados após o
  newline; carrega o JSON rejeitando **chaves duplicadas** (`object_pairs_hook`); e
  exige `raw_bytes == forma determinística` (`indent=2`, `sort_keys`). Assim ficam
  protegidos conteúdo, ordenação, indentação, encoding e newline.
- **Schema da saída fechado.** `additionalProperties=false` em **todos** os níveis,
  modelando exatamente os campos emitidos pelo inspetor; a saída passa por
  `security_scan`, checagem de caminhos pessoais/segredos/endpoints/comandos e
  **proibição de conteúdo `bCertificate`/base64**. Sem campos livres de notas.
- **Referências exatas.** `reviewed_parser_output_ref.path` deve apontar **exatamente**
  para o único arquivo de saída presente; `corrective_repeat_decision_ref` para a
  decisão presente. FAIL/STOPPED sem saída **não** podem ter `reviewed_parser_output_*`.
- **Proveniência completa.** O validador **recalcula** o Git blob OID do parser **e dos
  testes** a partir dos bytes da worktree (`SHA-1("blob <size>\0"+content)`) e os
  compara à decisão **e** à evidência (quando o parser foi usado), exigindo o **mesmo
  commit** em ambos; `_git_blob_oid_of_repo_file()==None` é **erro**, nunca validação
  omitida. O commit é confirmado pelo **gate Git externo**; o validador offline confirma
  apenas os **bytes** (não a relação commit→árvore).
- **Cross-check integral.** Todos os campos que a evidência PASS duplica da saída
  (`file_size`, `pe_format`, `machine`, `subsystem`, `section_table`,
  `certificate_table`, flags de escopo, semântica de leitura, etc.) devem ser
  **idênticos** à saída real; a saída do parser é a **fonte primária**.

## 0.4 Referência do FAIL e invariantes de estado (2P-E-C3-R4.1)

A revisão **2P-E-C3-R4.1** fechou o caminho `COMPLETED_FAIL` — **sem** materializar,
**sem** acessar o blob upstream e **sem** executar o parser sobre o `WARP.exe`:

- **Referência presa no FAIL (R4.1-D1).** Quando `parser_output_produced=true` no
  `COMPLETED_FAIL`, o validador passou a exigir a **mesma ligação exata** já aplicada no
  PASS: `parser_output_raw`, `present_output_name` e `parser_output_path` não podem ser
  `None`; `reviewed_parser_output_ref.path` deve ser **igual** ao caminho canônico do
  único arquivo de saída (`client/warp-audit/evidence/<arquivo>`), **não** bastando
  `endswith`; e o **SHA-256 dos bytes reais** deve conferir. Reprova: saída sem
  referência, referência sem saída, referência para arquivo diferente, referência para
  o **mesmo nome em diretório diferente**, hash de um arquivo com referência para outro,
  e mais de uma saída.
- **Invariantes de `parser_execution` (R4.1-D2).** Uma função comum
  (`validate_parser_execution_state`) é usada por PASS, FAIL e STOPPED. Invariantes
  gerais: `completed⇒invoked`; `output_produced⇒invoked ∧ completed`;
  `¬invoked⇒¬completed ∧ ¬output_produced`; `¬completed⇒¬output_produced`. Por outcome:
  **PASS** exige exatamente `true/true/true`; **COMPLETED_FAIL** admite **apenas** três
  estados fechados — `PRE_PARSER_FAIL` (`false/false/false`),
  `PARSER_ERROR_WITHOUT_OUTPUT` (`true/false/false`) e `POST_OUTPUT_FAIL`
  (`true/true/true`); qualquer outra combinação (por exemplo `false/true/false`,
  `false/false/true`, `false/true/true`, `true/false/true`) é **reprovada**.
- **STOPPED e a limitação documentada.** O modelo STOPPED não possui `parser_completed`;
  o campo **não foi inventado**. Validam-se os campos equivalentes existentes
  (`parser_invoked`, `parser_output_produced=false`) e mantém-se `output_produced⇒invoked`.
  A limitação (`¬invoked⇒¬completed` não verificável sem o campo) está registrada no
  código e no schema.
- **Schema FAIL.** Como o mini-validador não implementa `if/then/else`, os três booleanos
  permanecem no schema e as relações condicionais são aplicadas em Python; a **descrição**
  do schema FAIL passou a registrar explicitamente os três estados válidos.
- **Parser e testes do parser inalterados.** Esta revisão **não** tocou
  `scripts/inspect-warp-pe-identity.py` nem `scripts/test-warp-pe-identity.py`
  (Git blob OIDs `3442ddfc…` e `6d7cab1b…` confirmados antes e depois).
- **Nada materializado ou executado.** Nenhuma nova materialização ocorreu; o parser não
  foi executado sobre o `WARP.exe`; **não** existe registro/evidência/saída reais da
  repetição; o **GATE 4 permanece não autorizado**; a evidência histórica permanece
  `EVIDENCE_INVALIDATED_PENDING_REPEAT`.

## 0.5 Repetição corretiva executada (2P-E-C3-REPEAT) — COMPLETED_PASS

Sob a decisão humana real `AUTHORIZE_CORRECTIVE_REPEAT_GATE_3`
([registro](../client/warp-audit/decisions/binary-audit-gate-03-corrective-repeat-decision-record-2026-08-03.json)),
executou-se **exatamente uma** repetição corretiva controlada — **sem** executar nem
carregar o binário:

- **Decisão presa aos objetos autorizados.** `reviewed_parser_commit`
  `bebe4fe9843e52b45b4d244a0f49f338ec3452d4`; Git blob OIDs do parser
  `3442ddfc…` e dos testes `6d7cab1b…` (recalculados antes e depois, **inalterados**);
  blob WARP `c853da42…`, tamanho `1137152`. Nenhuma autorização transitiva concedida.
- **Materialização única.** Exatamente um arquivo binário, obtido **somente** pela API
  oficial Git Data do GitHub pelo object ID (`GITHUB_OFFICIAL_GIT_DATA_API_BLOB_BY_OID`),
  decodificado direto para diretório temporário **fora do repositório**; a resposta não
  foi persistida; base64/bytes não impressos; rede encerrada após a obtenção.
- **Identidade reconfirmada IGUAL ao GATE 2.** `size=1137152`,
  `git_blob_oid=c853da42d18dfe090b4e941b435d989311faf3dc`,
  `sha256=345f3464…74` (Git OID ≠ SHA-256, ambos conferidos).
- **Parser revisado (somente leitura estática).** `exit_code=0`,
  `parser_invoked/parser_completed/parser_output_produced=true`. A saída exata e
  sanitizada foi versionada em
  [`…-parser-output-2026-08-03.json`](../client/warp-audit/evidence/binary-audit-gate-03-corrective-repeat-parser-output-2026-08-03.json)
  (SHA-256 `93296824…`), presa por bytes e por referência exata à evidência.
- **Resultado estrutural do PE.** `PE32`, machine `0x014c` (x86), subsystem
  `WINDOWS_GUI`, **5 seções**, `SizeOfHeaders=1024`, `FileAlignment=512`,
  `SectionAlignment=4096`. **`SizeOfOptionalHeader=224`** e magic **`0x010b`**
  separados — o achado **D2 da R1** (267 == magic, indício de offset incorreto) fica
  **definitivamente reconfirmado** como leitura correta (224 ≠ 0x010b).
- **Certificate Table.** `present=false`, `structurally_parseable=true` — **assinatura
  Authenticode ausente**. Achado material, **não** malware; sem validação de cadeia,
  OCSP/CRL, extração de `bCertificate` nem OpenSSL sobre conteúdo não extraído.
- **Cleanup confirmado.** Arquivo e diretório temporários removidos em qualquer desfecho
  (`temporary_file_removed`/`temporary_dir_removed=true`); binário **nunca** versionado.
- **Sem acesso a cliente, `Ragexe` ou VPS; GATE 4 não autorizado; segunda repetição não
  autorizada.** A evidência histórica invalidada é **preservada**.

> `COMPLETED_PASS` significa **apenas** que a repetição controlada do GATE 3 foi
> concluída — **não** segurança, confiança, validade de assinatura, nem autorização de
> uso no cliente, distribuição ou GATE 4.

## 0.6 Hardening cross-platform (LF) pós-integração (2P-E-C3-LF)

- **PR #52 integrado por squash** `7e4478845ea9c9cdd1a9f1732aca3caf119a664a` em `dev`.
- O **conteúdo Git integrado estava correto e em LF** (o blob da saída do parser tem
  SHA-256 `932968…f816` e Git OID `c1e66885…`; parser/testes com OIDs `3442ddfc…` /
  `6d7cab1b…`).
- Um checkout **Windows com `core.autocrlf=true`** convertia os arquivos da **worktree**
  de LF para CRLF. Isso fazia o validador local **rejeitar corretamente** os bytes
  divergentes (SHA-256 e Git blob OIDs recalculados diferentes; CRLF proibido) — ou
  seja, o problema era do **checkout**, **não** corrupção do blob Git nem das medições.
- O `.gitattributes` passou a **proteger somente os três artefatos byte-sensíveis** com
  `text eol=lf`: a saída do parser (`…-corrective-repeat-parser-output-*.json`),
  `scripts/inspect-warp-pe-identity.py` e `scripts/test-warp-pe-identity.py`. Nenhuma
  regra genérica (`* text=…` ou `client/**`) foi aplicada.
- Adicionou-se [`scripts/test-warp-audit-eol.py`](../scripts/test-warp-audit-eol.py)
  (consulta `git check-attr` **e** lê os bytes da worktree, recalculando SHA-256/OIDs) e
  uma **etapa de regressão** no workflow que clona localmente com `core.autocrlf=true` e
  prova que `eol=lf` prevalece.
- **Não houve alteração** de bytes, hashes, medições, evidências, parser ou testes do
  parser. **Nenhuma nova materialização** e **nenhuma segunda repetição** ocorreram; o
  **GATE 4 continua não autorizado**. O resultado técnico do GATE 3 permanece intacto.

## 1. Objetivo

Executar exclusivamente o `GATE 3 — IDENTITY_AND_SIGNATURE`: reconfirmar a identidade
do artefato e determinar o estado da assinatura Authenticode por inspeção estática,
sem executar nem carregar o conteúdo. Esta revisão **corrige a auditabilidade** do
registro sem repetir a materialização.

## 2. Decisão e autorização de origem

Decisão humana `AUTHORIZE_GATE_3`
([`binary-audit-gate-03-decision-record-2026-08-03.json`](../client/warp-audit/decisions/binary-audit-gate-03-decision-record-2026-08-03.json)):
`gate_3_authorized=true`; `gate_4_authorized=false`. Sucede o **PR #50** (squash
`6ab37b2a7ae65fd6b4fdf184759b345cf9ce4bd6`, base `dev`). Esta correção (2P-E-C3-R1)
**não** cria um novo registro humano de autorização para repetição.

## 3. Escopo exato

Reconfirmar a identidade (tamanho, Git OID, SHA-256) — **fatos preservados do GATE 2**
— e determinar o estado da assinatura. A inspeção limita-se à identidade do PE e à
assinatura Authenticode; seções, imports, exports, strings, entropia e comportamento
pertencem ao **GATE 4** e não estão autorizados.

## 4. Identificadores do artefato (preservados do GATE 2)

| Item | Valor |
| --- | --- |
| Repositório oficial | `Neo-Mind/WARP` (branch `rock_win32`) |
| Commit fixado | `9b1173e9e4e135c68e150704f01186ab5e763acd` |
| Árvore | `1aebae06d5c71a145afc35cc72fcf5c210a08758` |
| Caminho | `win32/WARP.exe` (entrada **blob**) |
| Git blob OID | `c853da42d18dfe090b4e941b435d989311faf3dc` |
| Tamanho | `1137152` bytes |
| SHA-256 (conteúdo) | `345f3464ee72a60afc97bde0773410f47348a00d8629182fe52741c5f1a42874` |

Estes valores foram confirmados por `git hash-object`/`hashlib` (não pelo parser PE) e
**batem** com o GATE 2. Permanecem **válidos**.

## 5. Método de materialização (execução original)

GitHub oficial, **Git Data API — objeto blob por OID** (`GITHUB_OFFICIAL_ONLY`),
preso ao objeto imutável; sem clone/fetch/archive/mirror/terceiros; sem rede após a
obtenção. **Esta correção não executou nova materialização.**

## 6. Isolamento

Arquivo materializado (na execução original) em **área temporária fora do
repositório** (`<scratchpad>/warp-gate3/WARP.exe`), `materialized_file_count=1`, e
**removido**.

## 7. Ferramentas e versões

| Ferramenta | Versão | Disponível | Invocada | Exit | Observação |
| --- | --- | :-: | :-: | :-: | --- |
| `gh` | 2.96.0 | sim | sim | 0 | obtenção do blob (execução original) |
| `git` | 2.55.0 | sim | sim | 0 | Git OID = `c853da42…` (fato do GATE 2) |
| parser de scratchpad | 3.14.6 (**não versionado**) | sim | sim | 0 | produziu `soh=267` (== magic); **substituído** |
| `openssl` | 3.5.7 | sim | **não** | `null` | não havia assinatura a parsear (D4 corrigido) |
| `inspect-warp-pe-identity.py` | stdlib | sim | **não** sobre o WARP.exe | — | inspetor revisável versionado (D3) |

## 8. Identidade PE observada (pendente de reconfirmação)

Valores **observados pelo parser não versionado**, registrados como observações
históricas — **não** como medições confirmadas (`reconfirmation_required=true`,
`pe_valid_status=PENDING_RECONFIRMATION`):

- `MZ`/`PE` observados presentes; magic observado `0x010b` (PE32).
- machine observado `0x014c` (x86); subsystem observado `WINDOWS_GUI`.
- **`size_of_optional_header` observado `267` → `MEASUREMENT_REQUIRES_RECONFIRMATION`**
  (coincide com o magic `0x010B`; forte indício de offset incorreto — ver D2).
- timestamp de cabeçalho observado `0` (metadado **não confiável**); checksum
  observado `0x00000000`.
- **Informações de versão / `OriginalFilename`:** `NOT_DETERMINED_BY_REVIEWED_PARSER`
  (o método original foi busca textual UTF-16 não reproduzível; **não** preservado
  como fato).

## 9. Assinatura Authenticode observada (pendente de reconfirmação)

- Certificate Table observada como **ausente** pelo parser não versionado
  (`determination_status=PENDING_RECONFIRMATION`).
- A ausência observada **não** é veredito de malware; uma eventual presença **não**
  seria prova de segurança. A determinação será reconfirmada pelo inspetor revisável
  numa repetição controlada, se autorizada.

## 10. Separação entre presença, validade, confiança e segurança

**assinatura presente** ≠ **válida** ≠ **cadeia confiável** ≠ **certificado vigente**;
**timestamp presente** ≠ **confiável**; nada disso ≠ **arquivo seguro**; **assinatura
ausente** ≠ **arquivo malicioso**. Estas asserções semânticas permanecem válidas.

## 11. Limitações

- Como o `WARP.exe` foi removido e **nova materialização não está autorizada**, os
  campos de identidade PE/assinatura **não** foram remedidos; permanecem pendentes.
- Os valores do parser não versionado são **observações históricas**, não medições
  confirmadas.
- Nenhuma verificação de cadeia/OCSP/CRL/timestamp; a determinação de assinatura fica
  pendente.
- Git OID e SHA-256 têm finalidades diferentes; identidade (preservada do GATE 2)
  **não** prova segurança.

## 12. Resultado

```text
EVIDENCE_INVALIDATED_PENDING_REPEAT
```

O `COMPLETED_PASS` original foi **suspenso**. Motivo: a evidência de identidade PE e do
estado da assinatura foi produzida por parser **não versionado** com **indício de
offset incorreto** (D2) e semântica ambígua (D1); nenhuma nova medição pôde ser feita
sem repetir a materialização (não autorizada).

## 13. Limpeza

Na execução original o arquivo temporário e o diretório foram **removidos**
(`temporary_file_removed=true`, `temporary_dir_removed=true`). Os fixtures sintéticos
dos testes do parser são criados e **removidos** durante o teste. Nenhum `WARP.exe` ou
binário permanece na worktree ou no Git.

## 14. Confirmações negativas

`no_new_materialization_performed=true`, `no_new_execution_performed=true`,
`no_execution_performed=true`, `no_dynamic_analysis_performed=true`,
`no_sandbox_created=true`, `no_wine_or_vm_load=true`, `no_network_after_fetch=true`,
`no_ragexe_access=true`, `no_client_access=true`, `no_gate4_inspection_performed=true`,
`binary_versioned=false`, `raw_signature_versioned=false`, `gate_4_authorized=false`.
O inspetor revisável **não** foi executado sobre o `WARP.exe` (`run_on_warp_exe=false`).

## 15. Arquivos afetados

| Arquivo | Tipo | Motivo |
| --- | --- | --- |
| `scripts/inspect-warp-pe-identity.py` | novo/edição | inspetor PE offline revisável (D3); R2: regra `soh==magic` removida + Certificate Table estrutural |
| `scripts/test-warp-pe-identity.py` | novo/edição | fixtures sintéticas (D2/D3); R2: `soh=267` válido + 17 cenários da Certificate Table |
| `client/warp-audit/schemas/binary-audit-gate-03-corrective-repeat-decision-record-real.schema.json` | novo | R2: schema da futura decisão da repetição |
| `client/warp-audit/schemas/binary-audit-gate-03-corrective-repeat-{pass,fail,stopped}-evidence.schema.json` | novos | R3: schemas PASS/FAIL/STOPPED da futura evidência |
| `client/warp-audit/schemas/binary-audit-gate-03-corrective-repeat-parser-output.schema.json` | novo | R3: schema da saída textual do parser (metadados) |
| `client/warp-audit/evidence/binary-audit-gate-03-identity-signature-evidence-2026-08-03.json` | edição | invalidação + D1/D2/D4 |
| `client/warp-audit/schemas/binary-audit-gate-03-identity-signature-evidence.schema.json` | edição | novo estado e semântica |
| `client/warp-audit/schemas/binary-audit-gate-03-corrective-repeat-fail-evidence.schema.json` | edição | R4.1: descrição registra os três estados fechados do FAIL |
| `client/warp-audit/decisions/binary-audit-gate-03-corrective-repeat-decision-record-2026-08-03.json` | novo | 2P-E-C3-REPEAT: registro real da decisão humana `AUTHORIZE_CORRECTIVE_REPEAT_GATE_3` |
| `client/warp-audit/evidence/binary-audit-gate-03-corrective-repeat-evidence-2026-08-03.json` | novo | 2P-E-C3-REPEAT: evidência real `COMPLETED_PASS` da repetição executada |
| `client/warp-audit/evidence/binary-audit-gate-03-corrective-repeat-parser-output-2026-08-03.json` | novo | 2P-E-C3-REPEAT: saída exata e sanitizada do parser revisado (metadados PE) |
| `scripts/validate-warp-audit.py` | edição | validação da evidência invalidada; R4: bytes/atomicidade; R4.1: ligação exata no FAIL + `validate_parser_execution_state` |
| `scripts/test-warp-audit-gate-03.py` | edição | negativos D1-D4; R4.1: estados FAIL válidos/inválidos, ligação da saída e cadeia FAIL pelo orquestrador |
| `docs/39-*.md` | edição | este registro |
| `docs/README.md`, `client/warp-audit/README.md` | edição pontual | estado atualizado |
| `.github/workflows/validate-warp-audit.yml` | edição pontual | executar o teste do parser |

Nada em `conf/import`, `db/import`, `npc/custom`, `src/`, core, VPS, MariaDB, firewall,
serviços, cliente, `Ragexe` ou progressão foi tocado. Nenhum binário adicionado.

## 16. Testes

- `git diff --check`; `validate-warp-audit.py`; `test-warp-audit-gate-01/02/03.py`
  (gate-03 com **133** casos após R4.1, incluindo estados FAIL válidos/inválidos e a
  ligação exata da saída pelo orquestrador real); `test-warp-pe-identity.py` (32 casos,
  inclui a regressão D2: `soh` de `0xE0` **não** vira `267`); `validate-client-assets.py`.
  Testes dos GATEs anteriores **não** foram enfraquecidos. Git blob OIDs do parser e dos
  testes do parser (`3442ddfc…`, `6d7cab1b…`) **inalterados** antes e depois de R4.1.

## 17. Riscos

Confusão identidade × segurança; assinatura ausente lida como malware; assinatura
presente lida como confiança; cadeia não validável offline; timestamp PE tratado como
data confiável; **parsing parcial/offset incorreto tratado como medição válida**;
ferramenta carregando/executando o PE; tentativa de rede; avanço indevido ao GATE 4;
binário permanecer em disco/entrar no Git; exposição de certificado/caminho/dado
pessoal; **falso `COMPLETED_PASS`** (mitigado por esta invalidação). Mitigações:
inspetor revisável com _bounds checking_ + fixtures; `MEASUREMENT_REQUIRES_RECONFIRMATION`;
distinção disponível/invocada; `run_on_warp_exe=false`; `gate_4_authorized=false`.

## 18. Rollback

Antes do merge: corrigir por commits; manter draft; fechar o PR se inválido; preservar
a branch/evidências. Após merge futuro: branch de `dev`, `git revert` do squash,
validação completa, PR de reversão. O revert **não** apaga os fatos preservados do
GATE 2 nem autoriza repetir a materialização. Sem `reset --hard`, sem `git clean`, sem
force push.

## 19. Estado atual

```text
GATE 3 — REPETIÇÃO CORRETIVA EXECUTADA: COMPLETED_PASS
(evidência histórica EVIDENCE_INVALIDATED_PENDING_REPEAT preservada)
```

## 20. Próxima decisão humana (proposta)

A repetição corretiva do GATE 3 foi **executada** e concluiu `COMPLETED_PASS`; a
identidade PE foi remedida (`SizeOfOptionalHeader=224`, magic `0x010b`) e a Certificate
Table determinada (`present=false`). A próxima decisão humana é sobre **avançar ou
parar** — como **proposta** (nomes ainda não canônicos; **nenhuma** opção selecionada):

```text
AUTHORIZE_GATE_4
STOP_PATH
```

```text
GATE 4 NÃO AUTORIZADO
```

O `COMPLETED_PASS` da repetição **não** seleciona o GATE 4 automaticamente nem autoriza
uso no cliente ou distribuição; uma segunda repetição **não** está autorizada.

## Estado de verificação

- **Fato (preservado do GATE 2):** blob OID, tamanho e SHA-256; materialização e
  limpeza anteriores; ausência de execução; binário não versionado.
- **Invalidado/pendente:** identidade PE (incl. `size_of_optional_header=267`) e
  estado da assinatura — produzidos por parser não versionado; aguardam reconfirmação.
- **Correção:** semântica de leitura (D1), medição (D2), parser versionado (D3),
  ferramenta invocada (D4); `COMPLETED_PASS` suspenso.
- **Pendência:** decisão humana sobre repetição corretiva do GATE 3.
- **Nota:** decisão técnica e de conformidade do projeto, **não** parecer jurídico.
