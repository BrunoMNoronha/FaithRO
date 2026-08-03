# Resultado do GATE 3 — identidade e assinatura estática offline do WARP

> **Estado atual:** `GATE 3 CONCLUÍDO — IDENTIDADE CONFIRMADA E ASSINATURA
> DETERMINADA (AUSENTE)` (ETAPA 2P-E-C3).
> **Data da execução:** 2026-08-03.
> **Escopo:** rematerialização temporária de **exatamente um** blob Git fixado, em
> área isolada **fora** do repositório; reconfirmação de identidade (tamanho, Git
> object ID e SHA-256 **iguais** aos do GATE 2); inspeção estática offline limitada
> à **identidade do PE** e à **assinatura Authenticode**; e **remoção** do arquivo.
> **Nenhuma** execução, carga, análise dinâmica, sandbox, inspeção ampla (seções,
> imports, exports, strings, entropia — GATE 4), acesso ao cliente/`Ragexe`/VPS,
> patch ou distribuição. **GATE 4 não autorizado.**
> Continua [37](37-resultado-gate-2-materializacao-integridade-warp.md); observa
> [33](33-plano-auditoria-binaria-offline-warp.md),
> [35](35-resultado-gate-0-proveniencia-warp.md) e
> [16](16-politica-distribuicao-cliente.md).

## 1. Objetivo

Executar exclusivamente o `GATE 3 — IDENTITY_AND_SIGNATURE` do plano da auditoria
binária offline: **reconfirmar a identidade** do artefato e **determinar o estado da
assinatura Authenticode** por inspeção estática, **sem executar** nem carregar o
conteúdo e **sem** inventário amplo (reservado ao GATE 4).

## 2. Decisão e autorização de origem

Decisão humana `AUTHORIZE_GATE_3`
([`binary-audit-gate-03-decision-record-2026-08-03.json`](../client/warp-audit/decisions/binary-audit-gate-03-decision-record-2026-08-03.json)):
`gate_3_authorized=true`, `temporary_materialization_authorized=true`,
`local_hashing_authorized=true`, `static_identity_inspection_authorized=true`,
`authenticode_inspection_authorized=true`; `gate_4_authorized=false` e demais
autorizações operacionais `false`. Sucede o **PR #50** (squash
`6ab37b2a7ae65fd6b4fdf184759b345cf9ce4bd6`, base `dev`), que integrou a
decisão/evidência do GATE 2 (`COMPLETED_PASS`).

## 3. Escopo exato

Rematerializar e inspecionar estaticamente **um** objeto: o blob Git fixado no
caminho `win32/WARP.exe`. A inspeção limita-se a: assinaturas `MZ`/`PE`, formato PE,
arquitetura, PE32/PE32+, subsystem, timestamp de cabeçalho (metadado **não
confiável**), checksum declarado, informação de versão/`OriginalFilename`; e à
existência/estado da Certificate Table e da assinatura Authenticode. **Fora do
escopo** (GATE 4): seções, imports, exports, strings, entropia, TLS callbacks,
relocations, recursos não relacionados à identidade, empacotamento e comportamento.

## 4. Identificadores do artefato

| Item | Valor |
| --- | --- |
| Repositório oficial | `Neo-Mind/WARP` (branch `rock_win32`) |
| Commit fixado | `9b1173e9e4e135c68e150704f01186ab5e763acd` |
| Árvore | `1aebae06d5c71a145afc35cc72fcf5c210a08758` |
| Caminho | `win32/WARP.exe` (entrada **blob**) |
| Git blob OID | `c853da42d18dfe090b4e941b435d989311faf3dc` |
| Tamanho | `1137152` bytes |
| SHA-256 (conteúdo) | `345f3464ee72a60afc97bde0773410f47348a00d8629182fe52741c5f1a42874` |

## 5. Método de materialização

GitHub oficial, **Git Data API — objeto blob por OID**
(`network_scope=GITHUB_OFFICIAL_ONLY`). A obtenção ficou **presa ao objeto Git
imutável** (blob OID), não ao topo da branch. **Sem** clone, fetch, pull, archive,
release asset, mirror ou fonte de terceiros; **sem** materializar qualquer outro
arquivo; **sem** acesso de rede **após** a obtenção.

## 6. Isolamento

Arquivo materializado em **área temporária isolada fora do repositório FaithRO**
(caminho lógico redigido: `<scratchpad>/warp-gate3/WARP.exe`), validado
programaticamente como fora da worktree, com destino inicialmente vazio e
`materialized_file_count=1`.

## 7. Ferramentas e versões

| Ferramenta | Versão | Uso (comando sanitizado) | Saída | Limitação |
| --- | --- | --- | --- | --- |
| `gh` | 2.96.0 | Git Data API: objeto blob por OID → `.content` | blob obtido e decodificado (1137152 B) | só o objeto fixado; não valida segurança |
| `git` | 2.55.0 | `git hash-object` do arquivo | Git OID `c853da42…` (igual) | é identidade do objeto Git, não SHA-256 |
| `python` | 3.14.6 | stdlib: parse de cabeçalho PE + SHA-256 + `VS_VERSION_INFO`/`OriginalFilename` | PE32 x86; sem Certificate Table | só identidade do PE; não inventaria seções (GATE 4) |
| `openssl` | 3.5.7 | `pkcs7 -inform DER -print_certs -noout` (**não executado**) | não aplicável (sem assinatura) | sem assinatura embutida, não há PKCS#7 a parsear |

Nenhuma ferramenta **executou** ou **carregou** o binário.

## 8. Identidade PE observada

- Assinaturas **`MZ`** e **`PE`** presentes; formato **PE32** (magic `0x010b`).
- Arquitetura/machine: **`0x014c`** (`IMAGE_FILE_MACHINE_I386`, x86).
- Subsystem: **`WINDOWS_GUI`** (`2`); número de seções: **5**;
  `NumberOfRvaAndSizes`: `16`.
- **Timestamp de cabeçalho:** `0` (`1970-01-01T00:00:00Z`) — **metadado NÃO
  confiável**, provavelmente zerado na geração; **não** tratado como data confiável.
- **Checksum declarado:** `0x00000000` (metadado; não recalculado nem usado como
  juízo).
- **Informações de versão:** `VS_VERSION_INFO` presente; **`OriginalFilename` =
  `WARP.exe`**, consistente com a identidade esperada.
- **PE válido/parseável:** sim.

## 9. Assinatura Authenticode observada

- **Certificate Table (data directory 4):** **AUSENTE**.
- **Assinatura Authenticode:** **AUSENTE** (não há PKCS#7 embutido).
- Estruturalmente parseável: **não aplicável** (nada a parsear).
- Algoritmo de digest / subject / issuer / serial: **não aplicável** (ausência).
- Timestamp/countersignature: **ausente**.
- Verificação criptográfica: `NOT_APPLICABLE_NO_SIGNATURE`.
- Estado da cadeia de confiança: `NOT_APPLICABLE_NO_SIGNATURE`.

> A ausência de assinatura é um **achado material** registrado — **não** é, por si só,
> veredito de arquivo malicioso.

## 10. Separação entre presença, validade, confiança e segurança

Distinga expressamente:

- **assinatura presente** ≠ **assinatura criptograficamente válida**;
- **assinatura válida** ≠ **cadeia confiável**;
- **cadeia confiável** ≠ **certificado vigente**;
- **timestamp presente** ≠ **timestamp confiável**;
- qualquer um dos acima ≠ **arquivo seguro**;
- **assinatura ausente** ≠ **arquivo malicioso**.

Neste artefato a assinatura está **ausente**: não há o que validar; a ausência
**não** classifica o arquivo como inseguro nem como malicioso. Da mesma forma, uma
assinatura presente **não** significaria arquivo seguro.

## 11. Limitações

- Sem Certificate Table, **não há assinatura** a validar; a ausência **não** implica
  malware, insegurança nem confiança.
- **Nenhuma** verificação criptográfica de cadeia, **OCSP**, **CRL** ou **timestamp**
  foi feita: inspeção **offline**, sem trust store adequado e **sem rede** após a
  obtenção do blob.
- A inspeção limitou-se à **identidade do PE** e à **assinatura**; seções, imports,
  exports, strings, entropia e comportamento **não** foram inspecionados (GATE 4).
- **Git object ID** e **SHA-256** têm finalidades diferentes; a correspondência de
  identidade prova **apenas** identidade do conteúdo, **não** segurança, benignidade,
  licença de redistribuição nem adequação ao cliente.
- Timestamp e checksum de cabeçalho são **metadados**; `0` não é data/estado confiável.
- Retrato pontual de **2026-08-03**.

## 12. Resultado

```text
COMPLETED_PASS
```

Significa **apenas**:

```text
A identidade do conteúdo é igual à do GATE 2, o PE é válido/parseável e o estado da
assinatura Authenticode foi determinado com precisão (AUSENTE).
```

**Não** significa segurança, benignidade, confiança, licença de redistribuição nem
adequação ao cliente.

## 13. Limpeza

O arquivo materializado e o diretório temporário foram **removidos**; nenhum
`WARP.exe` permanece no disco de trabalho; **nenhum** binário na worktree ou no Git.
`temporary_file_removed=true`, `temporary_dir_removed=true`; confirmação:
`target_exists=false`, `workdir_exists=false`. Horários reais: início
`2026-08-03T15:16:14.406Z`, fim `2026-08-03T15:16:15.244Z`, limpeza
`2026-08-03T15:16:15.290Z` (não representativos).

## 14. Confirmações negativas

`no_execution_performed=true`, `no_dynamic_analysis_performed=true`,
`no_sandbox_created=true`, `no_wine_or_vm_load=true`, `no_network_after_fetch=true`,
`no_external_service_upload=true`, `no_additional_file_materialized=true`,
`no_gate4_inspection_performed=true`, `no_client_access=true`, `no_ragexe_access=true`,
`no_patch_selected_or_applied=true`, `no_clientinfo_modified=true`,
`no_vps_access=true`, `binary_versioned=false`, `raw_signature_versioned=false`,
`gate_4_authorized=false`.

## 15. Arquivos afetados

| Arquivo | Tipo | Motivo |
| --- | --- | --- |
| `client/warp-audit/decisions/binary-audit-gate-03-decision-record-2026-08-03.json` | novo | registro real da decisão `AUTHORIZE_GATE_3` |
| `client/warp-audit/evidence/binary-audit-gate-03-identity-signature-evidence-2026-08-03.json` | novo | evidência real de identidade e assinatura |
| `client/warp-audit/schemas/binary-audit-gate-03-decision-record-real.schema.json` | novo | schema da decisão do GATE 3 |
| `client/warp-audit/schemas/binary-audit-gate-03-identity-signature-evidence.schema.json` | novo | schema da evidência do GATE 3 |
| `scripts/validate-warp-audit.py` | edição | validação do GATE 3 (decisão + evidência) |
| `scripts/test-warp-audit-gate-03.py` | novo | testes positivos e negativos do GATE 3 |
| `docs/39-resultado-gate-3-identidade-assinatura-warp.md` | novo | este registro |
| `docs/README.md` | edição pontual | índice do documento 39 |
| `client/warp-audit/README.md` | edição pontual | entradas do GATE 3 |
| `.github/workflows/validate-warp-audit.yml` | edição pontual | executar o teste do GATE 3 |

Nenhum binário, GRF, DLL ou asset foi adicionado. Nada em `conf/import`, `db/import`,
`npc/custom`, core, VPS ou cliente foi tocado.

## 16. Testes

- `git diff --check` (sem conflito/whitespace ruim).
- Validador: [`scripts/validate-warp-audit.py`](../scripts/validate-warp-audit.py)
  (`validate_gate3_decision`/`validate_gate3_evidence`; offline; cross-checks com o
  plano, a decisão e a evidência do GATE 2 e com o squash do PR #50).
- Testes: [`scripts/test-warp-audit-gate-03.py`](../scripts/test-warp-audit-gate-03.py)
  (positivos + 15 negativos obrigatórios; executados no CI
  [`validate-warp-audit.yml`](../.github/workflows/validate-warp-audit.yml)).
- Testes anteriores (GATE 1 e GATE 2) continuam verdes; validações existentes **não**
  foram enfraquecidas.

## 17. Riscos

R1 confusão entre identidade e segurança; R2 assinatura ausente lida como malware; R3
assinatura presente lida como confiança; R4 cadeia não validável offline; R5 timestamp
PE tratado como data confiável; R6 parsing parcial tratado como validação completa; R7
ferramenta carregando/executando o PE; R8 tentativa de consulta de rede; R9 avanço
indevido ao GATE 4; R10 binário permanecer em disco; R11 executável no Git; R12
exposição de certificado/caminho/dado pessoal; R13 alteração de schemas anteriores;
R14 falso `COMPLETED_PASS`. **Mitigações:** separação explícita presença × validade ×
confiança × segurança; ausência registrada como achado sem veredito; timestamp
rotulado como metadado não confiável; parse apenas de cabeçalho + detecção estrutural;
nenhuma ferramenta que carregue o PE; `network_scope=GITHUB_OFFICIAL_ONLY` e
`no_network_after_fetch=true`; `gate_4_authorized=false`; remoção obrigatória +
verificação; `.gitignore`/validador de assets; caminho lógico redigido e sem
certificado completo; schemas anteriores intocados; `COMPLETED_PASS` exige identidade
igual ao GATE 2 + PE válido + assinatura determinada.

## 18. Rollback

Antes do merge: corrigir por novo commit; manter draft; fechar o PR; sem force; sem
reescrever `dev`. Após integração: branch de `dev`, reverter o squash, validar, abrir
PR de reversão. O revert **não** apaga a identidade/assinatura já observadas, **não**
autoriza nova materialização/execução/inspeção ampla/distribuição, **não** inicia o
GATE 4 e **não** substitui nova decisão humana. Nenhum binário foi versionado; o
arquivo temporário foi removido.

## 19. Estado atual

```text
GATE 3 CONCLUÍDO — IDENTIDADE CONFIRMADA E ASSINATURA DETERMINADA (AUSENTE)
```

## 20. Próxima decisão humana

```text
GATE 4 NÃO AUTORIZADO
```

Somente após revisão e integração deste resultado poderá ser solicitada uma nova
decisão humana sobre o **GATE 4** (inventário PE estático):

```text
AUTHORIZE_GATE_4
STOP_PATH
```

Nenhuma dessas opções está selecionada. Um `COMPLETED_PASS` no GATE 3 **não**
seleciona `AUTHORIZE_GATE_4` automaticamente.

## Estado de verificação

- **Fato:** um blob rematerializado fora do repo; tamanho, Git blob OID e SHA-256
  **iguais** aos do GATE 2; PE32 x86 válido; `OriginalFilename` `WARP.exe`;
  Certificate Table **ausente**; arquivo removido.
- **Inferência/decisão:** `COMPLETED_PASS` — identidade confirmada e assinatura
  **ausente** determinada; **não** é juízo de segurança.
- **Pendência:** revisão/integração e, depois, decisão humana sobre o GATE 4.
- **Nota:** decisão técnica e de conformidade do projeto, **não** parecer jurídico.
