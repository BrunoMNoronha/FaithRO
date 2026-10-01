# 20 — Reprodução, documentação e bloqueio da toolchain Rust 1.77.2 (ETAPA 2O-D1-B1)

> **CLASSIFICAÇÃO OBRIGATÓRIA: BLOQUEADO — TOOLCHAIN RUST 1.77.2 INCOMPATÍVEL COM O GRAFO ATUALMENTE RESOLVIDO DAS DEPENDÊNCIAS DO UPSTREAM**
>
> A toolchain Rust 1.77.2 e o Cargo 1.77.2 foram empiricamente testados contra o grafo de dependências do Beam Patcher (commit upstream `feed97887090d121f796bc1b941390e28b7a2da5`) com o overlay de segurança aplicado.
>
> O `cargo metadata --locked` falhou imediatamente antes de qualquer compilação porque a dependência **`zeroize 1.9.0`** exige `edition = "2024"` e `rust-version = "1.85"`, recurso não suportado pelo Cargo 1.77.2 (exit code 101). Outros crates observados no grafo declaram MSRVs entre 1.82 e 1.83.
>
> **NENHUM BUILD FOI INICIADO. NENHUM BINÁRIO FOI PRODUZIDO OU EXECUTADO. NENHUMA DEPENDÊNCIA FOI ALTERADA. A TOOLCHAIN NÃO FOI ELEVADA.**

---

## 1. Objetivo

Reproduzir deterministicamente e versionar o bloqueio de compatibilidade da toolchain Rust 1.77.2, auditando todos os refs do upstream quanto à existência de `Cargo.lock` oficial e registrando as evidências sem alterar o código upstream nem elevar a toolchain instalada.

---

## 2. Ferramentas instaladas e ambiente

| Ferramenta / Componente | Versão Confirmada | Método de Verificação | Estado no Sistema |
| ----------------------- | ----------------- | --------------------- | ----------------- |
| **Shell** | PowerShell non-elevated | `WindowsPrincipal.IsInRole(Administrator)` -> `False` | Não elevado |
| **Visual Studio Build Tools** | 2022 (17.14.37516.0) | `vswhere.exe` | Instalado |
| **MSVC C/C++ Compiler** | 19.44.35228 (`cl.exe`) | `Launch-VsDevShell.ps1` | Instalado |
| **MSVC Linker** | 14.44.35228.0 (`link.exe`) | `Launch-VsDevShell.ps1` | Instalado |
| **Windows SDK** | 10.0.26100.0 | `vswhere.exe` / Build Tools | Instalado |
| **MSBuild** | 17.14.51 | `Launch-VsDevShell.ps1` | Instalado |
| **Rustup** | 1.29.0 | `rustup.exe --version` | Instalado no perfil do usuário (`~/.cargo/bin`) |
| **Rustc** | 1.77.2 (`25ef9e3d8 2024-04-09`) | `rustup run 1.77.2-... rustc --version` | Toolchain ativa / padrão |
| **Cargo** | 1.77.2 (`e52e36006 2024-03-26`) | `rustup run 1.77.2-... cargo --version` | Toolchain ativa / padrão |
| **WebView2 Evergreen** | 150.0.4078.83 | Registro do Windows (`EdgeUpdate Clients`) | Preexistente (não reinstalado) |

*Nota: Visual Studio Build Tools e Rust 1.77.2 permanecem instalados no ambiente local.*

---

## 3. Origem Upstream e busca por Cargo.lock Oficial

- **Repositório Upstream**: `https://github.com/beamguides/beam-patcher.git`
- **Commit Fixado**: `feed97887090d121f796bc1b941390e28b7a2da5`
- **Tree Digest (SHA-256)**: `4f405c9ecfb2f505d99b00bc77468961e3aa98c72f9ec30faa3939849465b9d5`
- **Contagem de arquivos**: 68 arquivos

### Busca por Cargo.lock em todos os refs e histórico (FASE E):

- **Varredura em `refs/heads`, `refs/remotes`, `refs/tags`**: `0` refs continham `Cargo.lock`.
- **Varredura no histórico do Git (`git log --all --full-history -- Cargo.lock`)**: NENHUM commit histórico registrou `Cargo.lock`.
- **Resultado registrado**: `official_cargo_lock_found = false`.

---

## 4. Overlay de segurança

O overlay de segurança do laboratório (`client/patcher/beam-audit/overlays/beam-lab-security.patch`) foi aplicado no clone temporário e validado semanticamente via `scripts/validate-beam-security-overlay.py` (`Overlay de segurança: OK`).

Os 4 arquivos modificados pelo overlay:
- `beam-core/src/sso.rs`
- `beam-ui/Cargo.toml`
- `beam-ui/src/commands.rs`
- `beam-ui/tauri.conf.json`

---

## 5. Lockfile de teste e erro reproduzido

### Generation do Cargo.lock (FASE G):
- `cargo generate-lockfile` executado com sucesso (exit `0`).
- **Cargo.lock gerado**: 498 packages resolvidos, 494 dependências do `crates.io-index`, `0` dependências git.
- **SHA-256 do Cargo.lock**: `fe0bb3a8f6f1d95084eb96b7a80bb6c17a2fd87b2b5d2f2bc4392c332df39101`.

### Reprodução do Bloqueio:
```text
$ rustup run 1.77.2-x86_64-pc-windows-msvc cargo metadata --locked --format-version 1
Exit code: 101
Stderr:
error: failed to download `zeroize v1.9.0`
Caused by: unable to get packages from source
Caused by: failed to download replaced source registry `crates-io`
Caused by: failed to parse manifest at `.../zeroize-1.9.0/Cargo.toml`
Caused by: feature `edition2024` is required

The package requires the Cargo feature called `edition2024`, but that feature is not stabilized in this version of Cargo (1.77.2).
```

### Incompatibilidades confirmadas no cache local de manifests:
- **`zeroize 1.9.0`** (Bloqueador Primário): declara `edition = "2024"` e `rust-version = "1.85"`.
- **`zerovec 0.11.6`**: declara `rust-version = "1.83"`.
- **`potential_utf 0.1.5`**, **`windows-strings 0.5.1`**, **`writeable 0.6.3`**, **`zerotrie 0.2.4`**: declaram `rust-version = "1.82"`.

---

## 6. Evidências versionadas

- **Manifesto de Evidência**: [`client/patcher/beam-audit/evidence/toolchain-compatibility.json`](../client/patcher/beam-audit/evidence/toolchain-compatibility.json)
- **JSON Schema**: [`client/patcher/beam-audit/schemas/toolchain-compatibility.schema.json`](../client/patcher/beam-audit/schemas/toolchain-compatibility.schema.json)
- **Validador em Python**: [`scripts/validate-beam-toolchain-compatibility.py`](../scripts/validate-beam-toolchain-compatibility.py)
- **Workflow de CI**: [`.github/workflows/validate-beam-toolchain-compatibility.yml`](../.github/workflows/validate-beam-toolchain-compatibility.yml)

Nenhum caminho pessoal, segredo ou token foi incluído nos arquivos versionados.

---

## 7. Garantias de Segurança Mantidas

- **Nenhum `cargo build` executado.**
- **Nenhum `cargo test` executado.**
- **Nenhum `cargo run` executado.**
- **Nenhum binário produzido ou executado.**
- **Nenhum `cargo update` ou `--precise` executado.**
- **Nenhuma dependência ou `Cargo.toml` upstream alterado.**
- **Toolchain Rust não foi elevada.**
- **Build Tools e Rust 1.77.2 permanecem instalados.**
- **O ambiente temporário foi totalmente limpo (`AuditRoot` removido).**
- **Nenhum deploy realizado; VPS não acessada.**

---

## 8. Riscos residuais

- A toolchain 1.77.2 é incapaz de compilar a resolução atual do grafo de dependências do Beam Patcher sem alterar dependências (o que é proibido).
- Uma nova versão mínima da toolchain Rust (mínimo observado: 1.85.0) deverá ser auditada e aprovada na etapa seguinte.

---

## 9. Rollback

- O rollback da etapa é trivial: reverter os commits de documentação e evidência via Git.
- Nenhuma alteração persistente foi feita no código-fonte do upstream ou no repositório `FaithRO`.

---

## 10. Próxima Etapa

**ETAPA 2O-D1-B3 — Revisar e integrar a auditoria da toolchain Rust candidata (Rust 1.85.0).**

---

## 11. Auditoria e Seleção da Toolchain Rust Candidata (ETAPA 2O-D1-B2)

> **CLASSIFICAÇÃO TÉCNICA: CONCLUÍDO — TOOLCHAIN CANDIDATA APROVADA SOMENTE PARA FUTURA INSTALAÇÃO CONTROLADA**
>
> A toolchain Rust **`1.85.0`** (e Cargo **`1.85.0`**) foi selecionada por auditoria 100% estática como a menor versão mínima compatível com todo o grafo de dependências atualmente resolvido do Beam Patcher.
>
> **A INSTALAÇÃO E O BUILD PERMANECEM NÃO AUTORIZADOS (`installation_authorized = false`, `build_authorized = false`). A SELEÇÃO APENAS PROPÕE A VERSÃO PARA UMA ETAPA FUTURA DE INSTALAÇÃO CONTROLADA.**

### 11.1 Resumo da Auditoria Estática do Grafo
- **Total de Pacotes Analisados**: 510 pacotes no lockfile temporário reproduzido (`cargo generate-lockfile` em clone isolado).
- **Deriva Temporal do Grafo Registrada**: O hash do lockfile atualizou para `fc277856dd6bc9b935fe82261fc45e1b26daa05a712a6f41fd758b95656fd448` (comparado ao hash anterior `fe0bb3a8f6f1d95084eb96b7a80bb6c17a2fd87b2b5d2f2bc4392c332df39101`, com 498 pacotes). Ambas as resoluções exigem `zeroize 1.9.0` (`edition = "2024"`, MSRV `1.85`).
- **Editions Observadas**: `2018`, `2021`, `2024`.
- **Maior MSRV Declarado**: `zeroize 1.9.0` (`rust-version = "1.85"`).
- **Outros MSRVs Elevados Confirmados**: `zerovec 0.11.6` (1.83), `potential_utf 0.1.5` (1.82), `windows-strings 0.5.1` (1.82), `writeable 0.6.3` (1.82), `zerotrie 0.2.4` (1.82), `hyper 1.6.0` (1.79), `reqwest 0.12.15` (1.79).
- **Pacotes com MSRV Declarado**: 308 pacotes.
- **Pacotes sem MSRV Declarado**: 202 pacotes (MSRV não especificado no manifesto publicado).
- **Pacotes não verificáveis**: `0` pacotes.
- **Dependências Git**: `0` dependências.

### 11.2 Evidências e Validadores Versionados
- **Manifesto de Seleção**: [`client/patcher/beam-audit/evidence/toolchain-selection.json`](../client/patcher/beam-audit/evidence/toolchain-selection.json)
- **JSON Schema**: [`client/patcher/beam-audit/schemas/toolchain-selection.schema.json`](../client/patcher/beam-audit/schemas/toolchain-selection.schema.json)
- **Validador em Python**: [`scripts/validate-beam-toolchain-selection.py`](../scripts/validate-beam-toolchain-selection.py)
- **Workflow de CI**: [`.github/workflows/validate-beam-toolchain-selection.yml`](../.github/workflows/validate-beam-toolchain-selection.yml)

---

## 12. Declarações Obrigatórias

- Nenhuma ferramenta foi instalada.
- Nenhuma toolchain foi alterada (Rust 1.77.2 permanece ativa).
- Nenhum build foi iniciado.
- Nenhum binário foi produzido ou executado.
- Nenhuma dependência foi modificada.
- Nenhum `Cargo.lock` foi versionado no repositório.
- Nenhum deploy foi realizado.
- VPS não foi acessada.
- Windows Defender não foi desabilitado.
- O PR permanece em rascunho (draft).
