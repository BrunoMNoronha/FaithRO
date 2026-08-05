# Autorização da execução do GATE 4 — inventário PE estático do WARP

> **Escopo:** registro de **decisão humana** (governança), somente documental.
> **DECISÃO AUTORIZADA — EXECUÇÃO AINDA NÃO INICIADA.** Esta etapa **não** executa
> o GATE 4, **não** materializa `WARP.exe`, **não** baixa blob, **não** acessa o
> upstream `Neo-Mind/WARP`, **não** roda o analisador sobre PE real e **não** cria
> saída/evidência real. Complementa
> [40-preparacao-gate-4-inventario-pe-estatico-warp.md](40-preparacao-gate-4-inventario-pe-estatico-warp.md)
> (preparação, onde a execução ainda **não** estava autorizada).

## 1. Objetivo

Registrar, em JSON canônico e documentação versionada, a autorização humana real
`AUTHORIZE_GATE_4_EXECUTION` para executar **uma única** instância do GATE 4 — o
inventário PE **estático e offline** do WARP. A execução operacional ocorrerá em
**outra branch e outro PR**, somente após esta decisão ser revisada e integrada.

## 2. Decisão humana

| Campo | Valor |
| --- | --- |
| Decisão | `AUTHORIZE_GATE_4_EXECUTION` |
| Decisor | `BrunoMNoronha` |
| Papel/Autoridade | Responsável técnico e mantenedor do projeto FaithRO — Laos Deos |
| Canal | Decisão humana delegada ao consultor técnico FaithRO nesta conversa |
| Data | 2026-08-05 |
| `status` | `AUTHORIZED_FOR_SINGLE_GATE` |
| `execution_state` | `AUTHORIZED_NOT_STARTED` |

Registro: [`client/warp-audit/decisions/binary-audit-gate-04-decision-record-2026-08-05.json`](../client/warp-audit/decisions/binary-audit-gate-04-decision-record-2026-08-05.json),
validado contra `binary-audit-gate-04-decision-record-real.schema.json`.

## 3. Justificativa

O GATE 3 terminou `COMPLETED_PASS`. A ferramenta do GATE 4 foi preparada em PR
separado (#54) e revisada de forma independente (2P-E-C4-REVIEW): o analisador é
**estritamente estático** (só leitura de bytes; sem `subprocess`/`ctypes`/rede/shell)
e **fail-closed**; os testes usam **exclusivamente fixtures sintéticas**; a saída é
**determinística, sanitizada e fechada por schema**. A materialização futura fica
limitada a **um blob Git imutável**. A inspeção estática é necessária para avançar
na avaliação do WARP. **A autorização não é aprovação de segurança do executável
nem conclusão da avaliação**; imports, strings, APIs e entropia **não** são
vereditos isolados; `STOPPED` e `COMPLETED_FAIL` permanecem disponíveis; **nenhuma
autorização transitiva** é concedida.

## 4. Pré-condições

- GATE 3 concluído `COMPLETED_PASS`
  ([decisão](../client/warp-audit/decisions/binary-audit-gate-03-corrective-repeat-decision-record-2026-08-03.json),
  [evidência](../client/warp-audit/evidence/binary-audit-gate-03-corrective-repeat-evidence-2026-08-03.json)).
- Preparação do GATE 4 **integrada** em `dev` (PR #54, squash abaixo).
- Analisador e testes revisados presentes em `dev` com os blob OIDs canônicos.

## 5. Squash e blobs revisados (presos)

| Item | Valor |
| --- | --- |
| Squash integrado (PR #54) | `a5843c306288fb27d8e1bd1741f6ca75d810defa` (base `dev`) |
| Analisador | `scripts/inspect-warp-pe-static.py` — blob `f223ae7b50048aa493a47dcb95ead9ad5716e3cc` |
| Testes | `scripts/test-warp-pe-static.py` — blob `fdc79947a8f7c151dcee240e6317f87e36d80961` |

A decisão fica presa ao **squash integrado** e aos **blob OIDs**, não ao head
histórico da branch do PR #54.

## 6. Escopo autorizado

Executar, **uma vez**, o procedimento de **inventário PE estático offline** do
WARP, produzindo apenas JSON determinístico e sanitizado conforme o schema de
saída. `gate_4_execution_authorized=true` significa autorizar o **procedimento de
auditoria estática**, **não** executar o binário.

## 7. Ações expressamente proibidas

Executar/carregar/emular/descompactar o PE; Wine/Proton/VM/sandbox/análise
dinâmica; modificar o binário; reputação externa; rede após obter o blob;
versionar/distribuir binário; acessar cliente/Ragexe/RAG_SETUP/opensetup-lua;
acessar a VPS; criar conta/primeiro login; preparar/mod. clientinfo ou patch;
autorizar o **GATE 5**. Estas permanecem `false` no registro
(`execution_authorized=false`, `gate_5_authorized=false`, etc.).

## 8. Materialização fixada (futura, não executada aqui)

| Campo | Valor |
| --- | --- |
| Repositório | `Neo-Mind/WARP` |
| commit / tree | `9b1173e9…` / `1aebae06…` |
| artefato | `win32/WARP.exe` |
| blob OID (Git) | `c853da42d18dfe090b4e941b435d989311faf3dc` |
| tamanho | `1137152` bytes |
| max_files / rede | `1` / `GITHUB_OFFICIAL_ONLY` |

A autorização fica presa ao **blob**, não à branch upstream.

## 9. Condições

O registro fixa **35 condições** numeradas (1..35), incluindo: uma única
execução; squash e blobs exatos; um único blob materializado fora do repositório;
`umask 077`; reconfirmação de tamanho/OID/SHA-256 antes do analisador; limpeza e
`COMPLETED_FAIL` em divergência; sem rede após obter o blob; somente leitura
estática; proibição de execução/emulação/unpacking/sandbox; saída sem bytes
brutos/certificado/base64/dumps/segredos/caminhos pessoais; achados como
indicadores (não veredito); remoção do binário temporário; sem binário no Git/CI;
sem acesso a cliente/Ragexe/VPS/conta; GATE 5 e distribuição não autorizados;
decisão e execução em PRs separados; este PR não cria saída/evidência real.

## 10. Arquivos afetados

- `client/warp-audit/decisions/binary-audit-gate-04-decision-record-2026-08-05.json` (novo)
- `docs/42-autorizacao-execucao-gate-4-inventario-pe-warp.md` (novo)
- `docs/README.md`, `client/warp-audit/README.md` (índices, se necessário)

Nenhum script, schema, workflow, `.gitattributes`, evidência, output ou binário é
alterado nesta etapa.

## 11. Testes

`validate-warp-audit` (aceita a decisão; `gate_4_real_decision_count=1`,
evidence/output=0), `test-warp-audit-gate-04`, `test-warp-pe-static`,
`test-warp-audit-eol`, `validate-client-assets`, `git diff --check`, além de
`gate-01/02/03` e `pe-identity`.

## 12. Riscos

R1 confundir autorização com execução (mitigado: `execution_state=AUTHORIZED_NOT_STARTED`,
`execution_authorized=false`); R2 autorização transitiva do GATE 5 (mitigado:
`gate_5_authorized=false` e demais `false`); R3 drift do squash/blobs (mitigado:
condições 2–4 e recomputo de OID pelo validador); R4 materialização de artefato
errado (mitigado: `materialization_scope` const + condição 6); R5 vazamento na
saída futura (mitigado: schema fechado + sanitização do analisador revisado).

## 13. Rollback

Antes do merge: corrigir por novo commit normal ou fechar o PR. Depois do merge:
revogar por **novo registro e novo PR** (a reversão Git não apaga a decisão
histórica). Nenhuma reversão pode executar o PE, autorizar uma segunda execução,
autorizar o GATE 5 ou reintroduzir binário no Git. Se a execução futura já tiver
começado, interromper, limpar e registrar `STOPPED`/`COMPLETED_FAIL`. Nunca usar
reset destrutivo nem force push.

## 14. Estado atual

```text
GATE 4 AUTORIZADO — EXECUÇÃO NÃO INICIADA

gate_4_authorized = true
gate_4_execution_authorized = true
gate_5_authorized = false
execution_state = AUTHORIZED_NOT_STARTED

gate_4_real_decision_count = 1
gate_4_real_evidence_count = 0
gate_4_real_output_count = 0
```

Nenhuma decisão, saída ou evidência de execução foi fabricada.

## 15. Próxima etapa

Revisar e integrar este PR de decisão. **Em PR separado** (outra branch),
executar a instância única do GATE 4 conforme o escopo fixado, produzindo a
evidência (`PASS`/`FAIL`/`STOPPED`) e a saída determinística do inventário — sem
executar o binário e sem autorizar o GATE 5.
