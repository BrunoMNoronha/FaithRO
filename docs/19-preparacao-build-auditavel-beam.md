# Preparação de build auditável do Beam Patcher (ETAPA 2O-D1)

> **Escopo:** preparação de um processo **auditável e reproduzível** para uma
> **futura** construção do Beam Patcher no Windows. **Nada** foi instalado,
> construído, executado, empacotado, assinado ou implantado nesta etapa. A VPS
> **não** foi acessada. Nenhum cliente, executável ou asset proprietário foi
> utilizado. Complementa
> [17-decisao-patcher-launcher.md](17-decisao-patcher-launcher.md) e
> [18-homologacao-patch-sintetico-beam.md](18-homologacao-patch-sintetico-beam.md).
>
> **Classificação final:** **PRONTO PARA INSTALAÇÃO CONTROLADA DA TOOLCHAIN.**

## 1. Objetivo

Fixar e auditar a origem upstream do Beam Patcher, inspecionar suas dependências
e capacidades, preparar um overlay de segurança exclusivo para laboratório,
criar validadores e CI e documentar o procedimento exato de instalação e build
**futuro**, definindo os gates que autorizarão a ETAPA 2O-D1-B — **sem** instalar
toolchain, construir, executar, empacotar, assinar ou implantar.

## 2. Escopo

Auditoria **estática pré-build** do commit fixado; manifesto determinístico da
origem; inventário dos arquivos críticos; relatório de dependências e capacidades
Tauri; overlay de segurança para laboratório; validadores; plano de instalação;
plano de build; plano de auditoria do binário futuro; workflow de CI sem acesso
ao upstream; PR **draft** para `dev`. **Sem merge.**

## 3. Estado anterior

- PR #31 integrado em `dev` por squash merge; `dev` em `575ec9c`.
- Laboratório sintético do Beam homologado como **APROVADO COM RESTRIÇÕES**
  (docs/18); execução dinâmica do Beam bloqueada por ausência de toolchain.
- Beam ainda **não** construído, executado ou integrado; formato `.beam` não
  homologado dinamicamente.

## 4. Premissas

- A toolchain já instalada é a única utilizável; **nada** é instalado nesta etapa.
- O fonte upstream é clonado apenas em pasta **temporária externa** e descartado.
- Integridade por SHA-256 e digest determinístico da árvore como evidência.
- O patch server do laboratório é **loopback-only**.

## 5. Exclusões

Sem: instalação de Rust/Build Tools/Windows SDK/WebView2/WiX/NSIS/Tauri CLI;
`rustup-init`; `cargo build`/`run`/`tauri`; execução de binário ou script upstream
(`.bat`/`.cmd`/`.ps1`/`.sh`); construção de instalador ou `.exe`/`.msi`/`-setup.exe`;
cópia do fonte upstream para o FaithRO; alteração do commit upstream; acesso à VPS;
deploy; modificação do core do rAthena; uso de cliente/GRF/asset proprietário;
liberação de rede ampla; alteração de Defender/PATH/config global; merge.

## 6. Ambiente inspecionado

Somente leitura. Campos pessoais redigidos.

| Item | Valor |
| ---- | ----- |
| SO | Windows 10 Home Single Language, versão 2009, build 26200, x64 (AMD64) |
| PowerShell | 5.1 (Desktop) — shell **não elevado** |
| Git | 2.55.0 |
| Python | 3.14.6 |
| Node.js / npm | 24.18.0 / 11.16.0 (não utilizados) |
| winget | presente |
| rustup / rustc / cargo | **ausentes** |
| MSVC (`cl`/`link`/`msbuild`) | **ausentes** |
| Visual Studio Build Tools (`vswhere`) | **ausente** |
| WebView2 Runtime | **presente** (150.0.4078.83) |

Pasta temporária de auditoria: `<TEMP_REDIGIDO>/faithro-beam-upstream-audit-XXXX`
(fora do FaithRO, vazia na criação, sem symlink/reparse point).

## 7. Origem upstream

- Repositório oficial: `https://github.com/beamguides/beam-patcher` (sem mirror).
- Clone `--filter=blob:none --no-checkout` + `git checkout --detach` no commit
  fixado; remote oficial; working tree limpo; detached HEAD.

## 8. Commit fixado

- Commit: `feed97887090d121f796bc1b941390e28b7a2da5` (prefixo `feed978870`).
- Data do commit: 2026-06-06 (UTC).
- Referência de versão: **v1.0.1** (tag `v1.0.1` = `e09a0551…`; o commit fixado é
  **descendente legítimo** da tag, confirmado por `git merge-base --is-ancestor`).
- Digest determinístico da árvore (sha256):
  `4f405c9ecfb2f505d99b00bc77468961e3aa98c72f9ec30faa3939849465b9d5`
  (68 arquivos inventariados).

## 9. Licenciamento

`MIT OR Apache-2.0`, confirmado em `LICENSE-MIT`, `LICENSE-APACHE` e no
`Cargo.toml` do workspace (`license = "MIT OR Apache-2.0"`). Permite
redistribuição, modificação e self-host. Nenhum arquivo de licença foi tocado
pelo overlay.

## 10. Estrutura do workspace

Workspace Cargo (`resolver = "2"`, `edition = "2021"`) com 4 membros:

| Crate | Papel |
| ----- | ----- |
| `beam-core` | download, verificação, patcher, updater, SSO, config |
| `beam-formats` | formatos `.beam`/`.thor`/`.rgz`/`.gpf` e GRF |
| `beam-patcher` | binário CLI (`main.rs`) |
| `beam-ui` | app Tauri 1.5 (WebView) + comandos |

Dependências de path são internas ao workspace; **sem** dependências Git;
**sem** submódulos; único build script é `beam-ui/build.rs` (`tauri_build::build()`).

## 11. Requisitos oficiais

Para a D1-B (documentados, **não** instalados): Visual Studio Build Tools 2022
(workload C++ / MSVC), Windows SDK, WebView2 Runtime (já presente), rustup e a
toolchain MSVC exata. Fontes oficiais e gates em
[`build-plan.example.json`](../client/patcher/beam-audit/build-plan.example.json).

## 12. Estado da toolchain

`rustc`/`cargo`/`rustup` **ausentes**; MSVC e Build Tools **ausentes**. Não há
`rust-toolchain`/`rust-toolchain.toml` no upstream.

```text
RISCO — VERSÃO EXATA DO COMPILADOR NÃO FIXADA PELO UPSTREAM
```

**Mitigação (D1-B):** versão exata **proposta** Rust **1.77.2** (≥ 1.75,
compatível com Tauri 1.5), host triple `x86_64-pc-windows-msvc`, target MSVC,
componentes `rustc`/`cargo`/`rust-std`; registrar a versão efetiva ao instalar.
Não usar apenas o canal mutável `stable`.

## 13. Estado do lockfile

`Cargo.lock` **ausente** no commit fixado.

```text
RISCO — UPSTREAM NÃO FIXA A RESOLUÇÃO COMPLETA DAS DEPENDÊNCIAS
```

**Mitigação (D1-B):** gerar `Cargo.lock` em clone temporário, **rotulado como
gerado pelo FaithRO** (não como arquivo original), revisar o diff, `cargo
metadata --locked` e builds com `--locked`; segundo build `--offline`. Nenhum
lockfile foi inventado nesta etapa.

## 14. Reprodutibilidade

Auditoria estática reproduzível por `scripts/audit-beam-upstream.py` (digest
determinístico). A reprodutibilidade **bit-for-bit** do binário **não** é
prometida antes de ser testada na D1-B (comparação entre dois builds prevista).

## 15. Dependências

`workspace.dependencies`: `tokio` 1.35 (full), `serde` 1.0, `serde_yaml` 0.9,
`serde_json` 1.0, `anyhow` 1.0, `thiserror` 1.0, `tracing` 0.1,
`tracing-subscriber` 0.3, `reqwest` 0.11 (`stream`, **`native-tls`**), `flate2`
1.0, `sha2` 0.10, `md5` 0.7, `futures` 0.3, `async-trait` 0.1, `bytes` 1.5.
Auditoria transitiva (crates descontinuados, licenças, build scripts nativos,
conexões de rede) planejada para a D1-B com `cargo metadata`/`tree`/`audit`.

## 16. Build scripts

Único build script direto: `beam-ui/build.rs` → `tauri_build::build()` (padrão do
Tauri). Build scripts **transitivos** (via crates de dependência) serão isolados
na D1-B: download separado do build, build em diretório descartável, monitoração
de processos e rede.

## 17. Capacidades Tauri

`beam-ui/tauri.conf.json` (commit fixado) e classificação para o laboratório:

| Capacidade | Valor upstream | Classificação | Ação do overlay |
| ---------- | -------------- | ------------- | --------------- |
| `allowlist.all` | `false` | MANTER | — |
| `http.all` + scope | `true`; `https://goatmmo.com/**`, `https://**`, curinga http | RESTRINGIR | loopback-only; remove feature `http-all` |
| `shell.open` | `true` | DESABILITAR NO LABORATÓRIO | `false`; remove feature `shell-open` |
| `dialog.open/save` | `true`/`true` | RESTRINGIR | `false` no allowlist (JS) |
| `fs.readFile` | `true`; `$RESOURCE` | MANTER | — |
| `protocol.asset` | `true`; `$RESOURCE` | MANTER | — |
| `updater.active` | `true`; endpoint externo; pubkey placeholder | DESABILITAR NO LABORATÓRIO | `false`; endpoints `[]`; remove feature `updater` |
| `security.csp` | `null` | BLOQUEAR | CSP definida (self/loopback/asset) |
| `bundle.active`/`targets` | `true`/`all` | DESABILITAR NO LABORATÓRIO | `false`/`[]` |

## 18. Rede

`reqwest` com `native-tls`; **sem** `danger_accept_invalid_certs`. URLs no fonte
são placeholders (`patch.example.com`, `auth.example.com`, `yourserver.com`),
exceto o domínio externo `goatmmo.com` no escopo HTTP do Tauri — **removido** pelo
overlay. No laboratório, apenas `127.0.0.1`/`localhost`; sem DNS externo na
primeira execução.

## 19. Processos

`Command::new` sem shell/interpolação (sem `sh -c`/`cmd /c`):

- `beam-ui/src/commands.rs:195` lança `client_exe`; `:431` lança `setup_exe_path`.
- `beam-core/src/sso.rs:83` lança o jogo via SSO (env `BEAM_SSO_TOKEN`).
- Ocorrências em `beam-formats/*` são apenas nomes de arquivos de teste
  (`std::process::id()`), não execução.

Os três pontos de lançamento são **bloqueados** pelo overlay no laboratório.

## 20. Updater

Updater do Tauri ativo com endpoint externo e pubkey placeholder. O overlay o
desabilita (`active:false`, endpoints `[]`, remove feature `updater`). O updater
do `beam_core` é controlado por config e fica desabilitado na config de
laboratório. `auto_update` mantido `false`.

## 21. Shell

`shell.open` habilitado no upstream; **desabilitado** pelo overlay
(`shell.open:false` + remoção da feature `shell-open`). Não há uso de
`shell::open`/`open::that` no Rust.

## 22. Filesystem

`fs.readFile` e `protocol.asset` limitados a `$RESOURCE` — **mantidos** (escopo
já restrito a recursos empacotados). O seletor de pasta usa a API Rust
`FileDialogBuilder` (não lança processo externo).

## 23. CSP

Upstream: `security.csp: null`. Overlay define CSP mínima:
`default-src 'self'`; `connect-src 'self' http://127.0.0.1 http://localhost`;
`img-src/media-src` com `asset:`/`https://asset.localhost`; `script-src 'self'`.

## 24. Overlay de laboratório

[`overlays/beam-lab-security.patch`](../client/patcher/beam-audit/overlays/beam-lab-security.patch),
textual, gerado por `git diff` sobre uma **cópia temporária** (o clone canônico,
usado como evidência, permanece intacto). Toca **apenas** 4 arquivos:
`beam-ui/tauri.conf.json`, `beam-ui/Cargo.toml`, `beam-ui/src/commands.rs`,
`beam-core/src/sso.rs`. Não toca licenças, não cria arquivos novos, não contém
bloco binário. Aplicável ao commit fixado (`git apply --check` OK). Validado por
`scripts/validate-beam-security-overlay.py`.

## 25. Plano de instalação

Ver [`build-plan.example.json`](../client/patcher/beam-audit/build-plan.example.json)
(seção `prerequisites`/`install_rules`): cada pré-requisito com origem oficial,
versão, arquitetura, verificação, impacto, elevação, caminho, rollback e gate.
Regras: sem `curl | sh`/`irm | iex`, sem instalador de terceiros, sem package
manager comunitário, sem `latest` sem registrar a versão efetiva, sem alteração
manual de PATH global, sem componentes extras do Visual Studio, sem IDE completa,
**sem** execução como administrador.

## 26. Plano de build

Ver `build-plan.example.json` (seção `build`): clone novo → checkout destacado →
inventário pré-build → overlay → validação do overlay → geração/revisão do
lockfile → `cargo metadata --locked` → download em fase explícita → inventário do
cache → segundo build com rede bloqueada → `cargo build --release --locked
--offline` → **sem** bundle/installer → SHA-256 do executável → captura dos
arquivos escritos → assinatura Authenticode **ausente** registrada → **sem
execução** nessa fase → comparação entre dois builds → destruição do ambiente
temporário.

## 27. Plano de auditoria do binário

SHA-256 do executável; captura dos arquivos escritos; monitoração de processos e
rede na fase dinâmica (D1-B); nenhuma execução na fase de build; ausência de
assinatura registrada. Nenhuma promessa de reprodutibilidade bit-for-bit antes do
teste.

## 28. Gates da D1-B

Autorizam a D1-B **somente** com todos verdes: (1) origem oficial e commit
fixado confirmados; (2) licença confirmada; (3) inventário determinístico; (4)
toolchain exata definida; (5) lockfile tratado (gerar/rotular/`--locked`); (6)
dependências identificadas; (7) capacidades Tauri auditadas; (8) overlay válido
(updater/shell/HTTP/CSP/bundle/lançamentos); (9) plano de instalação e build
completos; (10) validadores e CI verdes; (11) nenhuma instalação/build/execução
nesta etapa.

## 29. Testes executados

| Teste | Resultado |
| ----- | --------- |
| `git diff --check` | limpo |
| `validate-client-assets.py` | OK |
| `validate-patcher-config.py` | OK |
| `validate-progression-overrides.py` | OK |
| `validate-synthetic-patch-lab.py --self-test` | OK |
| `--help` dos 3 novos scripts | OK |
| `audit-beam-upstream.py` (clone temporário) | OK (68 arquivos, digest fixado) |
| `validate-beam-build-plan.py` (manifesto+plano) | OK |
| `validate-beam-security-overlay.py` (clone temporário) | OK |
| `git apply --check` do overlay no commit fixado | OK |

## 30. Testes não executados

Instalação de toolchain, `cargo build/run/tauri`, execução do Beam,
empacotamento, code signing, teste dinâmico do formato `.beam`, teste no Windows
Defender, comparação bit-for-bit — **todos** pertencem à D1-B.

## 31. Achados

| ID | Severidade | Evidência | Risco | Mitigação | Estado |
| -- | ---------- | --------- | ----- | --------- | ------ |
| F1 | CRÍTICO | `tauri.conf.json`: `http.all=true`, `https://**` + curinga http + `goatmmo.com` | HTTP amplo a partir do WebView | Overlay: loopback-only, remove `http-all` | MITIGADO PELO OVERLAY |
| F2 | ALTO | `security.csp=null` | Sem restrição de origem no WebView | Overlay: CSP mínima | MITIGADO PELO OVERLAY |
| F3 | ALTO | `updater.active=true`, endpoint externo, pubkey placeholder | Auto-update externo | Overlay: `active:false`, endpoints `[]`, remove feature | MITIGADO PELO OVERLAY |
| F4 | MÉDIO | `shell.open=true` | Abrir URL/arquivo externo | Overlay: `false`, remove feature | MITIGADO PELO OVERLAY |
| F5 | MÉDIO | `commands.rs:195/431`, `sso.rs:83` `Command::new(...).spawn()` | Lançar cliente/setup/SSO | Overlay: bloqueio de lançamento no lab | MITIGADO PELO OVERLAY |
| F6 | MÉDIO | Sem `Cargo.lock` no upstream | Resolução variável | D1-B: gerar/revisar/`--locked`/`--offline` | ACEITO PARA LABORATÓRIO |
| F7 | BAIXO | Sem `rust-toolchain` | Compilador não fixado | D1-B: versão exata (1.77.2) | ACEITO PARA LABORATÓRIO |
| F8 | BAIXO | `dialog.open/save=true` | Superfície de diálogo JS | Overlay: `false` no allowlist | MITIGADO PELO OVERLAY |
| F9 | INFORMATIVO | 12 binários rastreados no upstream (assets) | Nenhum p/ FaithRO | Não copiados; gate FASE W | ACEITO PARA LABORATÓRIO |

## 32. Riscos

- **Ausência de `Cargo.lock`** → resolução variável; mitigado na D1-B (§13).
- **Versão mutável do Rust** → fixar versão exata e registrar host/componentes.
- **Capacidades Tauri amplas** → overlay obrigatório antes do primeiro build.
- **Build scripts transitivos** → isolar download/build, monitorar na D1-B.
- **Instalação global** → instalar o mínimo, versões fixas, rollback documentado.

## 33. Critério de aprovação

Enquadra-se em **PRONTO PARA INSTALAÇÃO CONTROLADA DA TOOLCHAIN**: origem e commit
fixados, licença confirmada, inventário determinístico, toolchain exata definida,
lockfile tratado, capacidades auditadas, overlay válido (updater/shell/HTTP/CSP/
bundle/lançamentos), planos completos, validadores e CI verdes e **nenhuma**
instalação/build/execução.

## 34. Rollback

- Arquivos do FaithRO antes do commit: remover apenas os listados por
  `git status` (sem `git clean -fd`/`git reset --hard`).
- Depois do commit: `git revert` em novo commit na própria branch.
- PR: fechar sem merge; não apagar a branch sem autorização.
- Clone temporário: remover apenas `BEAM_AUDIT_ROOT`.
- SO: nenhum rollback de ferramenta necessário (nada instalado).

## 35. Próxima etapa

```text
ETAPA 2O-D1-B — Instalar a toolchain mínima fixada e produzir o primeiro build
não executado do Beam Patcher em ambiente descartável.
```

## 36. Referências

- [17-decisao-patcher-launcher.md](17-decisao-patcher-launcher.md) — seleção do patcher.
- [18-homologacao-patch-sintetico-beam.md](18-homologacao-patch-sintetico-beam.md) — lab sintético.
- [`client/patcher/beam-audit/`](../client/patcher/beam-audit/) — manifesto, achados, plano, schemas, overlay.
- `scripts/audit-beam-upstream.py`, `scripts/validate-beam-build-plan.py`,
  `scripts/validate-beam-security-overlay.py`.
- [16-politica-distribuicao-cliente.md](16-politica-distribuicao-cliente.md) — o que pode/não pode ser distribuído.
