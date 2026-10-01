# Resultado do GATE 2 — materialização e integridade local do WARP

> **Estado atual:** `GATE 2 CONCLUÍDO — MATERIALIZAÇÃO E INTEGRIDADE LOCAL
> CONFIRMADAS` (ETAPA 2P-E-C2-A).
> **Data da execução:** 2026-08-01.
> **Escopo:** obtenção controlada de **exatamente um** blob Git fixado, em área
> temporária isolada **fora** do repositório, com confirmação local de tamanho,
> Git object ID e SHA-256, e **remoção** do arquivo. **Nenhuma** execução, inspeção
> estática/dinâmica, sandbox, integração no cliente ou distribuição. **GATE 3 não
> autorizado.**
> Continua [36](36-registro-autorizacao-gate-1-materializacao-warp.md); observa
> [33](33-plano-auditoria-binaria-offline-warp.md),
> [35](35-resultado-gate-0-proveniencia-warp.md) e
> [16](16-politica-distribuicao-cliente.md).

## 1. Objetivo

Executar exclusivamente o `GATE 2 — MATERIALIZATION_AND_LOCAL_INTEGRITY` do plano da
auditoria binária offline: materializar o blob fixado e **confirmar a integridade
local**, sem executar nem inspecionar o conteúdo.

## 2. Decisão e autorização de origem

Decisão humana `AUTHORIZE_GATE_2`
([`binary-audit-gate-02-decision-record-2026-08-01.json`](../client/warp-audit/decisions/binary-audit-gate-02-decision-record-2026-08-01.json)):
`gate_2_authorized=true`, `hashing_authorized=true`; `gate_3_authorized=false` e demais
autorizações operacionais `false`. Sucede o **PR #49** (squash
`6a078f338bc69307e942ba390b565da4008acc40`, base `dev`), que integrou o GATE 1
(`materialization_authorized=true`).

## 3. Método utilizado

GitHub oficial, **Git Data API — objeto blob por OID** (`network_scope=GITHUB_OFFICIAL_ONLY`).
A obtenção ficou **presa ao objeto Git imutável** (blob OID), não ao topo da branch.
**Sem** clone, fetch, pull, archive, release asset, mirror ou fonte de terceiros;
**sem** materializar qualquer outro arquivo.

## 4. Isolamento

Arquivo materializado em **área temporária isolada fora do repositório FaithRO**
(caminho lógico redigido: `<scratchpad>/warp-gate2/WARP.exe`), validado
programaticamente como fora da worktree, com destino inicialmente vazio.

## 5. Reconfirmação de identidade (metadados)

Commit `9b1173e9…` → árvore `1aebae06…` → `win32/` (árvore `94132cf1…`) →
`WARP.exe` (**blob**), OID `c853da42…`, tamanho `1137152`. **Consistente.**

## 6. Horários reais capturados

- Início da materialização: `2026-08-01T14:00:00.288Z`
- Fim da materialização: `2026-08-01T14:00:01.273Z`
- Limpeza (remoção): `2026-08-01T14:01:09.767Z`

Horários **reais**, capturados no momento das operações — **não** representativos.

## 7. Materialização

- Arquivos de conteúdo materializados: **1** (`WARP.exe`).
- Tamanho observado: **1137152 bytes**.
- Arquivo **não** aberto e **não** executado.

## 8. Integridade local

| Métrica | Esperado | Observado | Resultado |
| --- | --- | --- | :-: |
| Tamanho (bytes) | 1137152 | 1137152 | MATCH |
| Git blob OID | `c853da42d18dfe090b4e941b435d989311faf3dc` | `c853da42d18dfe090b4e941b435d989311faf3dc` | MATCH |

- **Git object ID** (algoritmo `GIT_OBJECT_ID`): SHA-1 sobre a representação Git
  `blob <size>\0<content>`. Recalculado por `git hash-object` **e** por recomputo
  independente — ambos iguais ao esperado.
- **SHA-256 local** (algoritmo `SHA-256`) do conteúdo:
  `345f3464ee72a60afc97bde0773410f47348a00d8629182fe52741c5f1a42874` (64 hex).

> **Importante:** o **Git object ID** e o **SHA-256** têm **finalidades diferentes**.
> O Git object ID é a identidade do objeto Git; o SHA-256 é o hash do conteúdo. O
> SHA-256 **não** é apresentado como Git OID, e **não** representa aprovação de
> segurança.

## 9. Resultado

```text
COMPLETED_PASS
```

Significa **apenas**:

```text
O conteúdo materializado corresponde exatamente ao objeto Git fixado
(tamanho e Git blob OID iguais aos esperados).
```

**Não** significa segurança, benignidade, confiança, licença de redistribuição nem
adequação ao cliente.

## 10. Limpeza

O executável e o helper de decodificação foram **removidos**; o diretório temporário
foi removido; nenhum `WARP.exe` permanece no disco de trabalho; **nenhum** binário na
worktree ou no Git. `temporary_file_removed=true`, `temporary_dir_removed=true`.

## 11. Confirmações negativas

`no_execution_performed=true`, `no_static_inspection_performed=true`,
`no_dynamic_analysis_performed=true`, `no_sandbox_created=true`,
`no_client_integration=true`, `no_distribution=true`, `no_vps_access=true`,
`no_clone_or_archive=true`, `no_release_asset=true`, `no_mirror_or_third_party=true`,
`no_external_service_upload=true`, `binary_versioned=false`, `gate_3_authorized=false`.

## 12. Limitações

- Correspondência de hash prova **identidade** do conteúdo em relação ao objeto Git
  fixado; **não** prova segurança, benignidade, licença de redistribuição nem
  adequação ao cliente.
- Git object ID e SHA-256 são identificadores com finalidades diferentes.
- **Nenhuma** inspeção estática (PE, strings, imports, exports, recursos, assinatura)
  nem análise dinâmica foi realizada; o GATE 2 **não** as substitui.
- Retrato pontual de 2026-08-01.

## 13. Propriedade intelectual

WARP é GPL-3.0 (uso local; binário **não** versionado). `Ragexe`, GRF, DLLs e assets
Gravity são proprietários (ver [16](16-politica-distribuicao-cliente.md)). Distinga
expressamente: **identidade do conteúdo** × **integridade criptográfica** ×
**segurança** × **confiança** × **licença** × **autorização para análise** ×
**autorização para materialização** × **autorização para redistribuição**. **Nenhuma**
autorização de redistribuição é concedida; a licença do repositório **não** equivale a
autorização para redistribuir o binário.

## 14. Validação, schema e testes

- Decisão: [`binary-audit-gate-02-decision-record-2026-08-01.json`](../client/warp-audit/decisions/binary-audit-gate-02-decision-record-2026-08-01.json)
  · schema [`binary-audit-gate-02-decision-record-real.schema.json`](../client/warp-audit/schemas/binary-audit-gate-02-decision-record-real.schema.json).
- Evidência: [`binary-audit-gate-02-integrity-evidence-2026-08-01.json`](../client/warp-audit/evidence/binary-audit-gate-02-integrity-evidence-2026-08-01.json)
  · schema [`binary-audit-gate-02-integrity-evidence.schema.json`](../client/warp-audit/schemas/binary-audit-gate-02-integrity-evidence.schema.json).
- Validador: [`scripts/validate-warp-audit.py`](../scripts/validate-warp-audit.py)
  (`validate_gate2_decision`/`validate_gate2_evidence`; offline; cross-checks com o
  plano, o GATE 1 e a evidência do GATE 0, e com o squash do PR #49).
- Testes: [`scripts/test-warp-audit-gate-02.py`](../scripts/test-warp-audit-gate-02.py)
  (positivos + negativos; executados no CI
  [`validate-warp-audit.yml`](../.github/workflows/validate-warp-audit.yml)).

## 15. Riscos

R1 objeto diferente do aprovado; R2 arquivos adicionais; R3 Git OID confundido com
SHA-256; R4 execução acidental; R5 executável no Git; R6 arquivo permanecer em disco;
R7 fonte alternativa após falha; R8 hash lido como segurança; R9 avanço para inspeção;
R10 propriedade intelectual. Mitigações: obtenção presa ao objeto imutável + recomputo
do Git OID; destino vazio e `materialized_file_count=1`; campos/algoritmos separados;
sem ferramentas que carreguem o PE; destino fora da worktree + busca por binários;
remoção obrigatória e verificação; proibição de fallback (`COMPLETED_FAIL`); limitações
obrigatórias; `gate_3_authorized=false`; sem publicação do arquivo.

## 16. Rollback

Antes do merge: corrigir por novo commit; manter draft; fechar o PR; sem force; sem
reescrever `dev`. Após integração: branch de `dev`, reverter o squash, validar, abrir
PR de reversão. O revert **não** apaga hashes já observados, **não** autoriza nova
materialização/execução/inspeção/distribuição, **não** inicia o GATE 3 e **não**
substitui nova decisão humana.

## 17. Estado atual

```text
GATE 2 CONCLUÍDO — MATERIALIZAÇÃO E INTEGRIDADE LOCAL CONFIRMADAS
```

## 18. Próxima decisão humana

Somente após revisão e integração deste resultado poderá ser solicitada uma nova
decisão humana sobre o **GATE 3** (identidade e assinatura — inspeção estática
offline):

```text
AUTHORIZE_GATE_3
STOP_PATH
```

Nenhuma dessas opções está selecionada. Um `COMPLETED_PASS` no GATE 2 **não**
seleciona `AUTHORIZE_GATE_3` automaticamente.

## Estado de verificação

- **Fato:** um blob materializado fora do repo; tamanho e Git blob OID **iguais** aos
  esperados; SHA-256 local calculado e distinto do Git OID; arquivo removido.
- **Inferência/decisão:** `COMPLETED_PASS` — identidade do conteúdo confirmada em
  relação ao objeto fixado; **não** é juízo de segurança.
- **Pendência:** revisão/integração e, depois, decisão humana sobre o GATE 3.
- **Nota:** decisão técnica e de conformidade do projeto, **não** parecer jurídico.
