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
