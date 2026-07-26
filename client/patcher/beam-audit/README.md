# `client/patcher/beam-audit/` — auditoria estática pré-build do Beam Patcher

> **Escopo:** artefatos de **preparação** para uma futura construção auditável do
> Beam Patcher (ETAPA 2O-D1). **Nenhum** fonte de terceiros, binário, instalador
> ou toolchain é versionado aqui. **Nada foi construído, executado ou implantado.**
> Ver a preparação completa em
> [`docs/19-preparacao-build-auditavel-beam.md`](../../../docs/19-preparacao-build-auditavel-beam.md).

## O que é isto

Esta pasta guarda o resultado **versionável** de uma auditoria **estática**
(pré-build) do commit fixado do Beam Patcher
(`beamguides/beam-patcher`, `feed97887090d121f796bc1b941390e28b7a2da5`,
referência `v1.0.1`, licença `MIT OR Apache-2.0`):

```text
beam-audit/
├── README.md                        # este arquivo
├── upstream-manifest.example.json   # manifesto determinístico da origem (hashes, digest)
├── security-findings.example.json   # achados da auditoria (Tauri/rede/processos)
├── build-plan.example.json          # plano controlled de instalação e build (D1-B2)
├── first-build-plan.example.json    # plano do primeiro build controlado / autorização de execução (D1-B8)
├── first-build-runbook.example.json # runbook operacional do primeiro build (D1-B10)
├── first-build-authorization.example.json    # modelo de autorização humana (template, não concedido) (D1-B10)
├── first-build-authorization-request.example.json # solicitação formal de autorização humana (pendente, não concede) (D1-B12)
├── first-build-human-decision-package.example.json # pacote de decisão humana (leitura, não concede) (D1-B14)
├── first-build-human-decision-record.example.json  # registro de decisão em branco (pendente) (D1-B14)
├── first-build-human-presentation-manifest.example.json # manifesto de apresentação (não apresentado) (D1-B16)
├── first-build-human-presentation-receipt.example.json  # comprovante de entrega em branco (D1-B16)
├── first-build-execution-evidence.example.json # template de evidência da execução futura (não executado) (D1-B10)
├── toolchain-installation-plan.example.json # plano de instalação isolada da Rust 1.85.0 (D1-B4)
├── evidence/
│   ├── toolchain-compatibility.json # evidência de incompatibilidade da Rust 1.77.2 (D1-B1)
│   ├── toolchain-selection.json     # evidência de seleção da candidata Rust 1.85.0 (D1-B2)
│   └── toolchain-installation.json    # evidência de instalação isolada da Rust 1.85.0 (D1-B6)
├── overlays/
│   ├── README.md
│   └── beam-lab-security.patch       # overlay de segurança do laboratório (textual)
└── schemas/
    ├── upstream-manifest.schema.json
    ├── build-plan.schema.json
    ├── first-build-plan.schema.json
    ├── first-build-runbook.schema.json
    ├── first-build-authorization.schema.json
    ├── first-build-authorization-request.schema.json
    ├── first-build-human-decision-package.schema.json
    ├── first-build-human-decision-record.schema.json
    ├── first-build-human-presentation-manifest.schema.json
    ├── first-build-human-presentation-receipt.schema.json
    ├── first-build-execution-evidence.schema.json
    ├── toolchain-compatibility.schema.json
    ├── toolchain-selection.schema.json
    ├── toolchain-installation-plan.schema.json
    └── toolchain-installation.schema.json
```

O fonte do Beam foi clonado apenas em pasta **temporária fora do repositório**,
com `git checkout --detach` no commit fixado, auditado de forma read-only e
**descartado** ao final. Nada do upstream (código, binário, `Cargo.lock`) é
copiado para o FaithRO.

## Como reproduzir a auditoria (fora do repositório)

```bash
# 1) Clonar o fonte oficial em pasta temporária EXTERNA ao FaithRO
git clone --filter=blob:none --no-checkout https://github.com/beamguides/beam-patcher.git /tmp/beam
cd /tmp/beam && git checkout --detach feed97887090d121f796bc1b941390e28b7a2da5

# 2) Inventário determinístico (não constrói, não executa, não copia o fonte)
python scripts/audit-beam-upstream.py --source /tmp/beam --output /tmp/beam-audit.json

# 3) Validar o manifesto e o plano versionados
python scripts/validate-beam-build-plan.py \
  --manifest client/patcher/beam-audit/upstream-manifest.example.json \
  --plan client/patcher/beam-audit/build-plan.example.json

# 4) Auditar MSRVs e edições do grafo (não constrói, não executa)
# Em clone isolado após `cargo generate-lockfile`:
python scripts/audit-beam-rust-msrv.py \
  --lockfile /tmp/beam/Cargo.lock \
  --output /tmp/toolchain-selection.json

# 5) Validar a evidência de seleção de toolchain e compatibilidade
python scripts/validate-beam-toolchain-compatibility.py
python scripts/validate-beam-toolchain-selection.py

# 6) Validar o plano e a evidência de instalação isolada da toolchain Rust 1.85.0
python scripts/validate-beam-toolchain-installation-plan.py
python scripts/validate-beam-toolchain-installation.py

# 7) Validar o overlay de segurança contra o clone temporário
python scripts/validate-beam-security-overlay.py \
  --source /tmp/beam \
  --patch client/patcher/beam-audit/overlays/beam-lab-security.patch

# 8) Remover a pasta temporária
rm -rf /tmp/beam
```

## Achados principais (resumo)

| ID | Severidade | Item | Estado |
| -- | ---------- | ---- | ------ |
| F1 | CRÍTICO | `http.all` amplo + `https://**`/curinga http + domínio externo | MITIGADO PELO OVERLAY |
| F2 | ALTO | CSP nula (`security.csp: null`) | MITIGADO PELO OVERLAY |
| F3 | ALTO | Updater Tauri ativo com endpoint externo | MITIGADO PELO OVERLAY |
| F4 | MÉDIO | `shell.open` habilitado | MITIGADO PELO OVERLAY |
| F5 | MÉDIO | Lançamento de cliente/setup/SSO via `Command::new` | MITIGADO PELO OVERLAY |
| F6 | MÉDIO | `Cargo.lock` ausente no upstream | ACEITO PARA LABORATÓRIO |
| F7 | BAIXO | `rust-toolchain` ausente (versão não fixada) | ACEITO PARA LABORATÓRIO |
| F8 | BAIXO | Diálogos abrir/salvar habilitados | MITIGADO PELO OVERLAY |
| F9 | INFORMATIVO | Binários rastreados no upstream (assets) | ACEITO (não copiados) |

Detalhes completos e evidências em
[`docs/19-preparacao-build-auditavel-beam.md`](../../../docs/19-preparacao-build-auditavel-beam.md).

## Regras

- Os `*.example.json` são **exemplos versionados** e a fonte de verdade dos
  validadores. Não contêm segredo, caminho pessoal, IP real nem URL externa
  não oficial.
- O overlay é **textual** e limitado a mudanças de segurança do laboratório.
  Nunca deve conter bloco binário nem tocar licenças.
- Nada aqui autoriza build, execução, empacotamento, assinatura ou deploy do
  Beam. Esses passos pertencem à ETAPA 2O-D1-B, sob as mesmas restrições.

## Plano do primeiro build controlado (ETAPA 2O-D1-B8)

`first-build-plan.example.json` (schema em `schemas/first-build-plan.schema.json`)
representa, de forma versionada e validável, o **plano do primeiro build
controlado** e a **autorização de execução** — que permanece **bloqueada**
(`build_authorized=false`, `next_human_authorization_required=true`). Documentação
completa em
[`docs/23-planejamento-primeiro-build-controlado-beam.md`](../../../docs/23-planejamento-primeiro-build-controlado-beam.md).
Validação estática offline (não clona, não instala, não constrói):

```bash
python scripts/validate-beam-first-build-plan.py
```

## Runbook, autorização e evidência (ETAPA 2O-D1-B10)

Três artefatos separados por responsabilidade, todos versionados e validáveis,
que **não** autorizam e **não** executam o build:

- `first-build-runbook.example.json` — **runbook** operacional (25 passos com IDs
  estáveis, go/no-go, interrupção, limpeza e rollback).
- `first-build-authorization.example.json` — **modelo de autorização humana**,
  propositalmente **não concedido** (`authorization_granted=false`,
  `execution_permitted=false`), vinculado a SHAs, digest, hash do overlay,
  toolchain e a uma janela com expiração; de uso único e revogável.
- `first-build-execution-evidence.example.json` — **template de evidência** da
  execução futura, com execução **não iniciada** e listas vazias.

Documentação completa em
[`docs/24-runbook-primeiro-build-controlado-beam.md`](../../../docs/24-runbook-primeiro-build-controlado-beam.md).
Validação estática offline (não clona, não instala, não constrói, não executa;
confirma que a autorização continua não concedida):

```bash
python scripts/validate-beam-first-build-runbook.py
```

## Solicitação formal de autorização (ETAPA 2O-D1-B12)

`first-build-authorization-request.example.json` (schema em
`schemas/first-build-authorization-request.schema.json`) registra a
**solicitação formal** de autorização humana do primeiro build, vinculada ao
commit de referência do FaithRO e ao **SHA-256 do runbook e do modelo de
autorização** já existentes no repositório. A solicitação **não** concede e
**não** pode conceder autorização a si mesma (`request_status=PENDING_HUMAN_DECISION`,
`authorization_granted=false`, `execution_permitted=false`); a decisão pertence
ao artefato de autorização separado, em etapa posterior. Documentação completa em
[`docs/25-solicitacao-autorizacao-primeiro-build-beam.md`](../../../docs/25-solicitacao-autorizacao-primeiro-build-beam.md).
Validação estática offline (não clona, não instala, não constrói, não executa,
não concede autorização; recomputa e confere os hashes):

```bash
python scripts/validate-beam-first-build-authorization-request.py
```

## Pacote de decisão humana e registro de decisão (ETAPA 2O-D1-B14)

`first-build-human-decision-package.example.json` (schema em
`schemas/first-build-human-decision-package.schema.json`) reúne, por
**referência e hash**, a solicitação, o runbook, o modelo de autorização e o
plano de build, ancorados ao commit de integração do PR #39
(`4251c373a8bcdbb9e49369668711d64d8140aad3`), para que uma pessoa com autoridade
decida em etapa posterior. `first-build-human-decision-record.example.json`
(schema em `schemas/first-build-human-decision-record.schema.json`) é o
**formulário de registro em branco** (`decision_status=PENDING`, `decision=null`,
todos os flags `false`). Nenhum dos dois **concede autorização**, **permite
execução** ou **representa uma decisão**; a decisão real será registrada em
instância separada na ETAPA 2O-D1-B15, após revisão técnica. Documentação
completa em
[`docs/26-pacote-decisao-humana-primeiro-build-beam.md`](../../../docs/26-pacote-decisao-humana-primeiro-build-beam.md).
Validação estática offline (não clona, não instala, não constrói, não executa,
não decide, não autoriza; recomputa hashes e confere EOL LF):

```bash
python scripts/validate-beam-first-build-human-decision.py
```

## Apresentação controlada do pacote ao decisor (ETAPA 2O-D1-B16)

`first-build-human-presentation-manifest.example.json` (schema em
`schemas/first-build-human-presentation-manifest.schema.json`) registra, em
estado `NOT_PRESENTED`, o **conteúdo exato**, os **canais permitidos**, os
**critérios de autoridade** e os **procedimentos** de integridade, entrega,
devolução e aceitação para uma futura apresentação do pacote a uma pessoa com
autoridade, referenciando os seis artefatos por **caminho relativo + SHA-256
(LF)**, ancorados ao merge do PR #40
(`c5473a22c4c4fb301e91f35779a83d9bc4bca99a`).
`first-build-human-presentation-receipt.example.json` (schema em
`schemas/first-build-human-presentation-receipt.schema.json`) é o
**comprovante de entrega/recebimento em branco** (`NOT_PRESENTED`, entrega e
recebimento `false`, canal/identidade/decisão `null`). Nenhum dos dois
**apresenta**, **seleciona canal**, **identifica decisor**, **confirma
recebimento**, **registra decisão** ou **concede autorização**; a entrega real
será registrada na ETAPA 2O-D1-B17, com entrada humana explícita. Documentação
completa em
[`docs/27-apresentacao-controlada-pacote-decisao-beam.md`](../../../docs/27-apresentacao-controlada-pacote-decisao-beam.md).
Validação estática offline (não apresenta, não decide, não autoriza, não envia
comunicação; recomputa hashes e confere EOL LF):

```bash
python scripts/validate-beam-first-build-human-presentation.py
```
