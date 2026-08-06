# Preparação operacional do GATE 5 — ferramenta, contratos e testes sintéticos

> **Estado atual:** `GATE 5 — TOOLING PREPARADO E TESTADO (SOMENTE FIXTURES
> SINTÉTICAS); EXECUÇÃO NÃO AUTORIZADA` (ETAPA 2P-E-C5-TOOLING-PREP).
> **Data:** 2026-08-05.
> **Escopo:** **exclusivamente preparatório**. Cria e testa a ferramenta, os
> schemas de entrada/evidência e os testes que **poderão** ser usados numa futura
> execução controlada do GATE 5. **Não** executa o GATE 5, **não** usa o WARP real,
> **não** materializa nem executa qualquer PE, **não** executa Defender/antivírus/
> YARA/scanner sobre o artefato real, **não** faz upload externo, **não** prepara o
> cliente e **não** acessa a VPS.
> Continua [44](44-gate-5-decisao-e-plano.md); observa
> [33](33-plano-auditoria-binaria-offline-warp.md) e
> [40](40-preparacao-gate-4-inventario-pe-estatico-warp.md).

```text
gate_5_authorized=false
execution_authorized=false
local_security_scan_authorized=false
external_reputation_upload_authorized=false
client_preparation_authorized=false
```

## 1. Objetivo

Preparar, de forma **auditável e separada da execução**, o mecanismo do GATE 5 —
**verificações locais de segurança** — para evitar improviso na futura execução: a
ferramenta nasce **versionada, revisável e testada apenas com fixtures sintéticas**,
com contratos fechados de entrada e evidência, antes de qualquer varredura real. A
decisão da etapa 2P-E-C5-PREP (doc 44) foi **Opção B** — aprovar apenas a definição e
o plano de controle. Esta etapa materializa **somente** o tooling desse plano.

## 2. Estado anterior (cadeia)

- **GATE 4 = `COMPLETED_PASS`** (doc 43), integrado por squash `76d6b46` (PR #58) na
  branch `dev`. Resultado **procedural**; **não** aprova o binário.
- Output imutável do GATE 4 com SHA-256
  `84c3c49a770b475fdf25c43467498e014b2f8950ef172384bb8ea48bbe17f584` — **inalterado**
  e **fora do diff** desta etapa.
- Pacote de decisão do GATE 5 (doc 44) em `state=PENDING_HUMAN_DECISION`.

## 3. Ainda não existe autorização operacional real

O merge desta preparação **não** autoriza executar o GATE 5. Não há decisão,
evidência nem saída **real** do GATE 5. A execução real exigirá **nova decisão
humana explícita em PR separado**, referenciando o squash integrado desta preparação
e os Git blob OIDs exatos da ferramenta e dos testes.

## 4. Arquivos afetados

**Criados:**

- [`scripts/warp-audit-gate-05.py`](../scripts/warp-audit-gate-05.py) — orquestrador
  estático (stdlib, fail-closed, sem rede, sem execução do artefato).
- [`scripts/test-warp-audit-gate-05.py`](../scripts/test-warp-audit-gate-05.py) —
  testes (positivos, negativos, segurança, portabilidade) com fixtures sintéticas.
- [`client/warp-audit/schemas/binary-audit-gate-05-input.schema.json`](../client/warp-audit/schemas/binary-audit-gate-05-input.schema.json)
  e [`binary-audit-gate-05-input.example.json`](../client/warp-audit/binary-audit-gate-05-input.example.json).
- [`client/warp-audit/schemas/binary-audit-gate-05-evidence.schema.json`](../client/warp-audit/schemas/binary-audit-gate-05-evidence.schema.json)
  e [`binary-audit-gate-05-evidence.example.json`](../client/warp-audit/binary-audit-gate-05-evidence.example.json)
  (gerada por fixture sintética; `FIXTURE_VALIDATION_PASS`).

**Alterados:**

- [`scripts/validate-warp-audit.py`](../scripts/validate-warp-audit.py) — registra os
  dois contratos em `ARTIFACTS` (validação genérica: schema fechado + security scan +
  flags).
- [`scripts/test-warp-audit-eol.py`](../scripts/test-warp-audit-eol.py) e
  [`.gitattributes`](../.gitattributes) — `eol=lf` para a ferramenta e os testes.
- [`.github/workflows/validate-warp-audit.yml`](../.github/workflows/validate-warp-audit.yml)
  — executa o novo teste (checkout normal e regressão `core.autocrlf=true`).
- Índices: `docs/README.md`, `client/warp-audit/README.md`.

## 5. Arquitetura

```text
configuração declarativa (input schema)
        ↓
orquestrador Python (warp-audit-gate-05.py)
        ↓
adapters locais explicitamente permitidos
        ↓
normalização dos resultados (estados fechados)
        ↓
evidência JSON fechada
        ↓
validação por schema
```

- **Orquestrador:** recebe caminhos explícitos; valida identidade da entrada
  (SHA-256, tamanho); opera **fail-closed**; **impede execução do arquivo**; chama
  apenas adapters permitidos; captura stdout/stderr/exit code com timeout; normaliza;
  gera evidência sanitizada; nunca faz rede; nunca modifica a entrada; nunca escreve
  fora do diretório de output autorizado.
- **Modos:** `--validate-only` (valida contrato/ambiente, sem scanners);
  `--fixture-mode` (apenas fixtures sintéticas, adapter sintético puro, sem
  subprocess); **modo real BLOQUEADO** — falha com
  `GATE 5 REAL EXECUTION IS NOT AUTHORIZED`. Não há opção escondida para contornar.
- **Adapters:** `synthetic-local` (puro Python, sem executável externo; habilitado em
  fixture); `windows-defender-local` e `yara-local` (**apenas contrato**: detecção de
  disponibilidade, builder de comando com o arquivo como **argumento** — nunca como
  executável — e parser; **não** executados nesta etapa; exigem autorização futura;
  testados por respostas simuladas).
- **Estados fechados por adapter:** `NOT_RUN`, `PASS`, `FINDING`, `ERROR`, `TIMEOUT`,
  `STOP_PATH`. **Não** são usados `SAFE`/`BENIGN`/`TRUSTED`/`MALICIOUS` como conclusão
  do FaithRO.
- **Outcome da etapa:** `FIXTURE_VALIDATION_PASS` (fixture) ou
  `CONFIG_VALIDATION_PASS` (validate-only). **Nunca** `GATE_PASSED` para o artefato
  real.
- **Rede:** sem bibliotecas de rede (`requests`/`urllib.request`/`http.client`/
  `socket`/`ftplib`/`smtplib`/`paramiko`); imports mínimos da biblioteca padrão.

## 6. Ações permitidas nesta etapa (lista fechada)

Definir contratos; criar schemas fechados; implementar o orquestrador; criar testes
estáticos; criar fixtures sintéticas em runtime; documentar; integrar ao CI; preparar
a validação por schema. Nada além disto.

## 7. Ações proibidas

Usar o WARP real como entrada; materializar/executar/carregar qualquer PE; executar
Defender/antivírus/YARA/scanner sobre o artefato real; upload externo; iniciar/
concluir o GATE 5; preparar o cliente; acessar a VPS; alterar qualquer flag
operacional para `true`.

## 8. Testes

Fixtures **sintéticas** geradas em runtime (bytes inertes, sem formato executável
válido). Cobrem casos válidos (schemas, fixture-mode, adapter sintético
PASS/FINDING/ERROR/TIMEOUT, determinismo, sanitização, output em diretório
permitido); casos negativos (flags em `true`, campo desconhecido/ausente, hash
inválido/divergente, input inexistente, symlink, output fora do diretório, modo real,
adapter desconhecido, timeout, overwrite, excesso de stdout/stderr, import de rede);
segurança da ferramenta (entrada não executada, conteúdo/permissões byte-idênticos,
sem sockets/import de rede, `shell=False`, argumentos como lista); e portabilidade (CI
Linux, sem Windows/Defender/YARA/VPS/internet/cliente/WARP).

## 9. Riscos

- **R1** Ferramenta executar a entrada acidentalmente.
- **R2** Comando injetável (concatenação de string / `shell=True`).
- **R3** Rede não intencional.
- **R4** Interpretar resultado como aprovação de segurança.
- **R5** Falso positivo.
- **R6** Falso negativo.
- **R7** Parser incompatível com a versão real do scanner.
- **R8** Vazamento em logs (caminhos, IPs, segredos).
- **R9** Overwrite de evidência.
- **R10** Uso de ferramenta diferente da revisada.
- **R11** Divergência de hash da entrada.
- **R12** Execução sem autorização.

## 10. Mitigações

- **R1/R12** Sem `open`/exec do artefato; modo real bloqueado; scanners recebem o
  arquivo como argumento; testes confirmam entrada byte-idêntica e não executada.
- **R2** `shell=False`, argumentos sempre como lista, sem `os.system`; testes.
- **R3** Sem imports de rede; teste que reprova import proibido; `network_policy=blocked`.
- **R4** Estados fochados procedurais; `outcome` nunca `GATE_PASSED`; limitações
  explícitas; nenhuma conclusão por métrica isolada.
- **R5/R6/R7** Achados exigem interpretação humana; parser isolado e testado por
  respostas simuladas.
- **R8** Sanitização de caminhos/usuários/IPs/URLs/segredos e limites de tamanho.
- **R9** Recusa de sobrescrever evidência existente.
- **R10/R11** `eol=lf` para reprodutibilidade de blob OID; reconfirmação de identidade
  (SHA-256) e `expected_sha256` com falha em divergência.

## 11. Rollback

Antes do merge: corrigir por commit normal, manter draft ou fechar o PR sem merge.
Após eventual integração: reverter o squash por PR separado, sem reescrever histórico;
nunca usar `reset --hard`, `git clean -fd` ou force push. A reversão **não** executa o
GATE 5 nem altera o output do GATE 4.

## 12. Próxima decisão humana

A **execução real** do GATE 5 exige **nova decisão humana explícita** em **PR
separado**, definindo a lista fechada de ferramentas locais e as pré-condições do doc
44 §10. Esta etapa **não** a solicita e **não** a concede.

## Estado de verificação

- **Fato:** GATE 4 integrado (`76d6b46`); output SHA-256 `84c3c49a…` inalterado; doc
  44 em `PENDING_HUMAN_DECISION`.
- **Inferência/decisão:** tooling estático do GATE 5 preparado, testado só com
  fixtures sintéticas, fail-closed, sem rede e sem execução.
- **Pendência:** decisão humana para autorizar (ou não) a execução real do GATE 5.
- **Nota:** decisão técnica e de conformidade do projeto, **não** parecer jurídico nem
  atestado de segurança.
