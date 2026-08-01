# Registro da autorização humana do GATE 1 (autorização para materialização)

> **Estado atual:** `GATE 1 CONCLUÍDO — MATERIALIZAÇÃO FUTURA AUTORIZADA; GATE 2 NÃO
> AUTORIZADO` (ETAPA 2P-E-C1-A).
> **Data:** 2026-08-01.
> **Escopo:** registrar, de forma auditável, a decisão humana que **autoriza
> exclusivamente uma materialização futura** do blob fixado, a ser executada em um
> **GATE 2 separado**. O GATE 1 é **decisão humana apenas**: esta etapa **não**
> materializa, **não** baixa, **não** acessa o conteúdo do blob, **não** calcula
> SHA-256, **não** inspeciona e **não** executa nada. O merge deste registro **não**
> inicia o GATE 2.
> Continua [35](35-resultado-gate-0-proveniencia-warp.md); observa
> [33](33-plano-auditoria-binaria-offline-warp.md),
> [34](34-registro-autorizacao-gate-0-proveniencia-warp.md),
> [30](30-auditoria-estatica-warp.md) e [16](16-politica-distribuicao-cliente.md).

## 1. Objetivo

Registrar a autorização humana **exclusiva** do `GATE 1 — MATERIALIZATION_AUTHORIZATION`
do plano da auditoria binária offline do WARP
([docs/33](33-plano-auditoria-binaria-offline-warp.md)), delimitando — **sem
executar** — o escopo fechado de uma materialização futura do blob fixado.

## 2. Precedência: o GATE 1 canônico é decisão-humana-apenas

O plano canônico ([docs/33 §11](33-plano-auditoria-binaria-offline-warp.md) e
[`binary-audit-plan.example.json`](../client/warp-audit/binary-audit-plan.example.json),
`gate_id:1`) define o GATE 1 como **"Autorização para materialização"**, com
`does_not_materialize_binary: true` e opções de saída `AUTHORIZE_MATERIALIZATION` ou
`STOP_PATH`. A **materialização e a integridade local** (obtenção do blob + cálculo de
SHA-256) são o **GATE 2**; **identidade/assinatura** é o **GATE 3**; **inventário PE**
é o **GATE 4** — cada um com **decisão humana independente** e **sem autorização
transitiva**. Portanto, esta etapa executa **apenas** o GATE 1 canônico: registra a
decisão e o escopo fechado; **nada é materializado, baixado, acessado, hasheado,
inspecionado ou executado**.

## 3. Decisão humana

`AUTHORIZE_MATERIALIZATION` — autoriza **somente** uma materialização **futura** do
blob fixado, no escopo fechado, mediante execução posterior do GATE 2. Registro real:
[`client/warp-audit/decisions/binary-audit-gate-01-decision-record-2026-08-01.json`](../client/warp-audit/decisions/binary-audit-gate-01-decision-record-2026-08-01.json).

A decisão sucede o estado integrado pelo **PR #48** (`GATE 0 CONCLUÍDO — APROVADO POR
METADADOS`), cujo squash é `219b96b0688d9e5b71ae555b23e4166ef136424d` (base `dev`).

## 4. Decisor e autoridade

Decisor `BrunoMNoronha`; função/autoridade "Responsável técnico e mantenedor do
projeto FaithRO - Laos Deos". Canal "Claude Code — conversa do projeto FaithRO".

## 5. Pré-condição (GATE 0)

O GATE 0 foi **executado e concluído** com `COMPLETED_PASS`
([docs/35](35-resultado-gate-0-proveniencia-warp.md); evidência
[`binary-audit-gate-00-provenance-evidence-2026-08-01.json`](../client/warp-audit/evidence/binary-audit-gate-00-provenance-evidence-2026-08-01.json)):
proveniência declarada **consistente** com os metadados oficiais. `COMPLETED_PASS`
**não** significa confiança, segurança ou aprovação do binário.

## 6. Escopo fechado da materialização futura

Exatamente **um** objeto Git (blob), no GitHub oficial, preso ao objeto imutável:

| Campo | Valor canônico |
| --- | --- |
| Repositório | `Neo-Mind/WARP` (PUBLIC) |
| Branch | `rock_win32` |
| Commit | `9b1173e9e4e135c68e150704f01186ab5e763acd` |
| Árvore | `1aebae06d5c71a145afc35cc72fcf5c210a08758` |
| Caminho | `win32/WARP.exe` |
| Git blob OID | `c853da42d18dfe090b4e941b435d989311faf3dc` |
| Algoritmo do OID | `GIT_OBJECT_ID` (**não** é SHA-256) |
| Tamanho (metadados) | `1137152` bytes |
| Máximo de arquivos | `1` |
| Escopo de rede | `GITHUB_OFFICIAL_ONLY` |

Sem clone, fetch, pull, archive, release asset, mirror ou fonte de terceiros; sem
materializar qualquer outro arquivo.

## 7. Matriz de autorizações

Apenas **cinco** flags `true` (decisão humana + pré-condição + o **grant** deste gate);
todas as demais `false`:

```text
human_decision_required=true    human_decision_received=true
gate_selected=true              gate_0_completed=true
materialization_authorized=true            <-- único grant do GATE 1

hashing_authorized=false                static_inspection_authorized=false
local_security_scan_authorized=false    external_reputation_upload_authorized=false
sandbox_creation_authorized=false       execution_without_client_authorized=false
client_copy_provision_authorized=false  execution_with_client_copy_authorized=false
patch_review_authorized=false           patch_application_authorized=false
client_preparation_authorized=false     vps_access_authorized=false
test_account_authorized=false           first_login_authorized=false
distribution_authorized=false           gate_2_authorized=false
```

`materialization_authorized=true` refere-se à autorização para uma **etapa futura**
(GATE 2), **não** a uma ação executada aqui. `gate_2_authorized=false`: o GATE 2 **não**
é iniciado automaticamente e exigirá **nova decisão humana**.

## 8. Confirmação de ausência de materialização

`binary_materialized=false`, `blob_content_accessed=false`,
`binary_sha256_computed=false`, `binary_sha256=null`, `no_download_performed=true`,
`no_upstream_query_this_stage=true`, `no_static_inspection_performed=true`,
`no_execution_performed=true`, `no_sandbox_created=true`, `no_vps_access=true`,
`binary_versioned=false`. **Nenhuma** consulta ao upstream foi realizada nesta etapa;
**nenhum** binário foi baixado, acessado, materializado, hasheado ou executado.

## 9. Ações não autorizadas

Materializar/baixar/acessar/hashear **nesta etapa**; iniciar o GATE 2
automaticamente; clone/fetch/pull; archive; release asset; mirror; fonte de
terceiros; materializar outro arquivo; inspeção estática ou dinâmica; execução;
sandbox/Wine/VM; envio a serviço externo; cliente; patches; login; VPS; distribuição;
alteração do servidor, `PACKETVER` ou core do rAthena.

## 10. Separação entre registro e execução

Esta etapa **registra** a autorização e **completa** o GATE 1 como decisão. A
materialização será uma etapa **futura e separada** (GATE 2), sob **nova decisão
humana**, com integridade calculada localmente e sem envio externo. O merge deste
registro **não** inicia o GATE 2.

## 11. Propriedade intelectual

Distinga expressamente, sem presumir equivalência:

- **licença declarada do repositório** (`GPL-3.0`, metadado);
- **licença do código-fonte**;
- **licença aplicável ao binário materializado**;
- **autorização para análise**;
- **autorização para redistribuição**.

WARP é GPL-3.0 (uso local; binário **não** versionado). `Ragexe`, GRF, DLLs e assets
Gravity são proprietários — proibido versionar, hospedar, empacotar, enviar à VPS ou
distribuir (ver [16](16-politica-distribuicao-cliente.md)). **Nenhuma** autorização de
redistribuição do binário é concedida; a licença do repositório **não** equivale a
autorização para redistribuir o binário.

## 12. Segurança e privacidade

O registro não contém IP, senha, token, chave, caminho pessoal, URL direta de
binário, comando de download, hash de binário real (SHA-256) nem resultado de
análise. O validador reprova esses conteúdos e reporta apenas arquivo, campo e
categoria (sem ecoar o valor).

## 13. Validação, schema e testes

- Schema: [`binary-audit-gate-01-decision-record-real.schema.json`](../client/warp-audit/schemas/binary-audit-gate-01-decision-record-real.schema.json)
  (draft-07, subconjunto; `const` nos identificadores canônicos).
- Validador: [`scripts/validate-warp-audit.py`](../scripts/validate-warp-audit.py)
  (offline; `validate_gate1_record`/`validate_gate1`; cross-checks com o plano, a
  decisão e a evidência do GATE 0 e com o squash do PR #48).
- Testes: [`scripts/test-warp-audit-gate-01.py`](../scripts/test-warp-audit-gate-01.py)
  (1 positivo + testes negativos; ambos executados no CI
  [`validate-warp-audit.yml`](../.github/workflows/validate-warp-audit.yml)).

## 14. Riscos

R1 registro interpretado como materialização; R2 autorização transitiva
(GATE 1 → GATE 2/3/4); R3 `materialization_authorized=true` lido como ação executada;
R4 `COMPLETED_PASS` do GATE 0 lido como confiança/segurança; R5 Git blob OID
confundido com SHA-256; R6 licença do repositório lida como autorização de
redistribuição. Mitigações: `does_not_materialize_binary` do plano, `security_assertions`
confirmando ausência de ação, `gate_2_authorized=false`, escopo fechado por `const`,
distinção explícita OID × SHA-256, seção de PI e testes negativos.

## 15. Rollback

Antes do merge: corrigir por novo commit; manter draft; fechar o PR; sem force; sem
reescrever `dev`. Após integração: branch de `dev`, reverter o squash, validar, abrir
PR de reversão. A reversão Git **não** apaga a decisão humana histórica; **não**
autoriza nova obtenção, execução, distribuição ou qualquer gate posterior; e **não**
invalida automaticamente a proveniência já observada. A revogação exige novo registro
humano explícito.

## 16. Estado atual

```text
GATE 1 CONCLUÍDO — MATERIALIZAÇÃO FUTURA AUTORIZADA; GATE 2 NÃO AUTORIZADO
```

## 17. Próxima decisão humana

Somente após revisão e integração deste registro poderá ser solicitada uma nova
decisão humana sobre o **GATE 2** (materialização e integridade local):

```text
AUTHORIZE_GATE_2
STOP_PATH
```

Nenhuma dessas opções está selecionada. A autorização do GATE 1 **não** seleciona
`AUTHORIZE_GATE_2` automaticamente.

## Estado de verificação

- **Fato:** decisão humana recebida (`AUTHORIZE_MATERIALIZATION`); GATE 1 registrado
  como decisão; escopo fechado ao blob fixado; nenhuma consulta upstream nesta etapa;
  todas as flags operacionais `false`, exceto `materialization_authorized=true`
  (grant do gate).
- **Inferência/decisão:** apenas a materialização **futura** (GATE 2) fica autorizada;
  sem autorização transitiva; GATE 2 não iniciado.
- **Pendência:** revisão/integração e, depois, decisão humana sobre o GATE 2.
- **Nota:** decisão técnica e de conformidade do projeto, **não** parecer jurídico.
