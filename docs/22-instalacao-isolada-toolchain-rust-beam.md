# `docs/22-instalacao-isolada-toolchain-rust-beam.md` — Instalação Isolada e Validação da Toolchain Rust 1.85.0

> **Status:** INSTALADO E VALIDADO / SEM BUILD (ETAPA 2O-D1-B6)
> **Data:** 2026-07-25
> **Toolchain Ativa Conservada:** `1.77.2-x86_64-pc-windows-msvc`
> **Toolchain Adicionada Isoladamente:** `1.85.0-x86_64-pc-windows-msvc`
> **Perfil de Instalação:** `minimal` (`rustc`, `cargo`, `rust-std`)
> **Instalação Autorizada:** `SIM` (prompt formal de autorização recebido)
> **Build Autorizado:** `NÃO` (exige autorização humana prévia para etapa posterior)

---

## 1. Objetivo

Registrar a execução autorizada da instalação local e isolada da toolchain `1.85.0-x86_64-pc-windows-msvc` no ambiente de desenvolvimento do projeto **FaithRO - Laus Deo**, preservando integralmente a toolchain ativa `1.77.2-x86_64-pc-windows-msvc` como padrão global.

A instalação foi efetuada **sem autorização de compilação**, **sem execução do Beam Patcher**, **sem alteração de dependências**, **sem acesso à VPS** e **sem deploy**.

---

## 2. Inventário Empírico Pré e Pós-Instalação

### 2.1. Estado Pré-Instalação (Baseline)
- **Rustup**: `1.29.0`
- **Toolchain Padrão / Ativa**: `1.77.2-x86_64-pc-windows-msvc`
- **Toolchain Candidata 1.85.0**: Ausente
- **Overrides Locais**: `no overrides`
- **Espaço em Disco Livre**: `116.17 GB`

### 2.2. Comando Autorizado Executado
```powershell
rustup toolchain install 1.85.0-x86_64-pc-windows-msvc --profile minimal
```
- **Início UTC**: `2026-07-25T22:00:52Z`
- **Término UTC**: `2026-07-25T22:01:37Z`
- **Exit Code**: `0`
- **Delta em Disco**: `~447 MB` (`116.17 GB` -> `115.76 GB`)

### 2.3. Estado Pós-Instalação Confirmado
- **Toolchain Padrão Global Intacta**: `1.77.2-x86_64-pc-windows-msvc` (`rustup default`)
- **Toolchains Instaladas**:
  - `1.77.2-x86_64-pc-windows-msvc` (active, default)
  - `1.85.0-x86_64-pc-windows-msvc`
- **Invocação Nomeada Exclusiva**:
  ```powershell
  rustup run 1.85.0-x86_64-pc-windows-msvc rustc --version --verbose
  # Out: rustc 1.85.0 (4d91de4e4 2025-02-17)

  rustup run 1.85.0-x86_64-pc-windows-msvc cargo --version --verbose
  # Out: cargo 1.85.0 (d73d2caf9 2024-12-31)
  ```
- **Preservação Registrada**:
  ```powershell
  rustup run 1.77.2-x86_64-pc-windows-msvc rustc --version --verbose
  # Out: rustc 1.77.2 (25ef9e3d8 2024-04-09)
  ```

---

## 3. Arquivos Afetados Nesta Etapa

- `.github/workflows/validate-beam-toolchain-installation.yml` *(NEW)*
- `client/patcher/README.md`
- `client/patcher/beam-audit/README.md`
- `client/patcher/beam-audit/evidence/toolchain-installation.json` *(NEW)*
- `client/patcher/beam-audit/schemas/toolchain-installation.schema.json` *(NEW)*
- `docs/00-base-conhecimento.md`
- `docs/21-plano-instalacao-toolchain-rust-beam.md`
- `docs/22-instalacao-isolada-toolchain-rust-beam.md` *(NEW)*
- `scripts/validate-beam-toolchain-installation.py` *(NEW)*

---

## 4. Evidência e Validação Estática

A evidência empírica está versionada em [`client/patcher/beam-audit/evidence/toolchain-installation.json`](../client/patcher/beam-audit/evidence/toolchain-installation.json) e validada estaticamente pelo schema [`client/patcher/beam-audit/schemas/toolchain-installation.schema.json`](../client/patcher/beam-audit/schemas/toolchain-installation.schema.json) através do validador [`scripts/validate-beam-toolchain-installation.py`](../scripts/validate-beam-toolchain-installation.py).

O validador foi submetido a uma suíte de **30 casos de testes negativos** (100% rejeitados), garantindo estaticamente que nenhuma violação de governança ou autorização indevida possa ser registrada.

---

## 5. Exceção de Governança Registrada

Na FASE A, identificou-se que o commit `d1b8a1ea7c30205ef8603081bfe412bd40625236` foi efetuado diretamente na branch `dev` após o merge do PR #35.

- **Auditoria de Diff**: `git diff 07460386102794b604d47ae6f326e0646ec758be..d1b8a1e`
- **Constatação**: O commit alterou exclusivamente `docs/21-plano-instalacao-toolchain-rust-beam.md` para remoção de 5 espaços em branco ao final de linhas (trailing whitespace do Markdown). Nenhuma alteração semântica ou em outros arquivos foi realizada.
- **Registro**: A ocorrência foi formalmente registrada na evidência JSON no campo `governance_exception`.

---

## 6. Riscos Residuais

> [!WARNING]
> 1. **Execução Manual sem Toolchain Nomeada**: Qualquer desenvolvedor que invoque `cargo build` diretamente no PowerShell sem a flag `+1.85.0-x86_64-pc-windows-msvc` executará a Rust 1.77.2, resultando em erro de compilação devido ao MSRV das dependências.
> 2. **Compilação Não Testada**: A presença da toolchain 1.85.0 no sistema não garante que o build do Beam Patcher compilará sem erros. A compilação permanece pendente de autorização explícita.

---

## 7. Plano de Rollback

Em caso de necessidade de remoção isolada da Rust 1.85.0 do ambiente local:

```powershell
rustup toolchain uninstall 1.85.0-x86_64-pc-windows-msvc
```

Este comando remove estritamente a toolchain 1.85.0 e seus componentes (`rustc`, `cargo`, `rust-std`), mantendo a Rust 1.77.2 intacta e funcional como padrão.
