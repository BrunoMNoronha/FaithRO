# 20 — Primeiro build controlado do Beam Patcher (ETAPA 2O-D1-B)

> **ESTADO: PAUSADO ANTES DA INSTALAÇÃO DA TOOLCHAIN.**
> Por decisão do operador, esta execução foi **interrompida deliberadamente**
> após os gates de repositório e de sistema, **antes** de baixar/instalar o
> Visual Studio Build Tools, o Rust ou de produzir qualquer build.
>
> **Nenhum build foi produzido. Nenhum binário foi executado. Nenhum software
> foi instalado. O sistema não foi modificado.**
>
> Classificação técnica de build: **não aplicável (build não realizado)**.

## 1. Objetivo

Instalar a toolchain mínima fixada (VS Build Tools + Rust 1.77.2 MSVC) e produzir
o primeiro build **não executado** e auditável do Beam Patcher, conforme o plano
canônico [`client/patcher/beam-audit/build-plan.example.json`](../client/patcher/beam-audit/build-plan.example.json).

## 2. Escopo desta parcial

Registra apenas o que foi **observado** e **executado com segurança** até o ponto
de pausa: gates de repositório e sistema e a **reconciliação do componente do
Windows SDK** (FASE D). Não cobre instalação, download de dependências, builds,
comparação ou destruição de ambiente — nada disso ocorreu.

## 3. Estado anterior

- Repositório `BrunoMNoronha/FaithRO`, branch base `dev`, commit `78f5bc5`.
- PR #32 integrado; classificação anterior: pronto para instalação controlada.
- Toolchain (Rust, Cargo, MSVC, Build Tools) ausente; WebView2 Evergreen presente.
- Nenhum build realizado; Beam nunca executado.

## 4. Correção do componente Windows SDK (FASE D — executada)

| Item | Valor |
| ---- | ----- |
| ID genérico anterior | `Microsoft.VisualStudio.Component.Windows11SDK` |
| ID versionado confirmado | `Microsoft.VisualStudio.Component.Windows11SDK.26100` |
| Nome no catálogo | Windows 11 SDK (10.0.26100.3916) |
| Fonte do catálogo | Documentação oficial do VS Build Tools 2022 (component directory) |
| Componentes mínimos | `Microsoft.VisualStudio.Workload.VCTools`, `Microsoft.VisualStudio.Component.VC.Tools.x86.x64`, `Microsoft.VisualStudio.Component.Windows11SDK.26100` |

O plano foi atualizado com o ID versionado e **validado contra o schema**
(`scripts/validate-beam-build-plan.py` → OK).

## 5. Ambiente (observado)

| Item | Evidência | Resultado | Limitação |
| ---- | --------- | --------- | --------- |
| Privilégio do shell | `WindowsPrincipal.IsInRole(Administrator)` | `False` (não elevado) | — |
| Espaço livre (unidade de sistema/TEMP em C:) | `Get-PSDrive` | 125,4 GB livres (≥ 20 GB exigidos) | — |
| Git | `Get-Command git` | Presente | — |
| Python | `Get-Command python` | Presente | — |
| Rustup / rustc / cargo | `Get-Command` | **Ausentes** | esperado |
| `cl` (MSVC) / `msbuild` | `Get-Command` | **Ausentes** | esperado |
| `link` | `Get-Command link` | Presente, porém é o `link.exe` do Git (`usr/bin/link`, coreutils), **não** o linker MSVC | falso-positivo registrado |
| WebView2 Evergreen | chave `EdgeUpdate Clients {F3017226-…}` | Presente `150.0.4078.83` | não reinstalar |

## 6. Origem upstream (verificada sem clonar)

`git ls-remote https://github.com/beamguides/beam-patcher.git` retornou:

| Ref | Commit |
| --- | ------ |
| `HEAD` / `refs/heads/main` | `feed97887090d121f796bc1b941390e28b7a2da5` |
| `refs/tags/v1.0.1` | `e09a0551b4d371d304e6da351e5f3e3b5fec2c69` |
| `refs/tags/v1.0.0` | `d56cdeac30a0f243a73f92eee2ab6d37bf2e85b5` |

Confere com o manifesto: commit fixado e tag `v1.0.1` idênticos. Upstream real e
acessível. **Nenhum clone foi feito** nesta parcial.

## 7. Overlay de segurança

Presente e íntegro (não aplicado nesta parcial, pois não houve fonte clonado):
`client/patcher/beam-audit/overlays/beam-lab-security.patch`
SHA-256: `945dbd2f354f9738f77fced4dd3a70923227ede042bbd3819dcadb44ca5c37fe`.

## 8. O que NÃO foi feito (pausado)

- Download/verificação e **instalação do VS Build Tools** (UAC não solicitado).
- Instalação do Rustup e da toolchain `1.77.2-x86_64-pc-windows-msvc`.
- Clone do upstream, `cargo generate-lockfile`, `cargo fetch`, `cargo metadata`.
- **Build A / Build B**, inventário de artefatos, comparação de hashes.
- Criação de `evidence/`, validador de evidências e workflow de CI (pertencem à
  execução com build real; não foram criados para não gerar evidência vazia).

## 9. Classificação

**PAUSADO POR DECISÃO DO OPERADOR — INSTALAÇÃO NÃO INICIADA.**
Não se aplica `BUILD PRODUZIDO` nem `BLOQUEADO` (não houve falha nem build).

## 10. Riscos residuais

- Toolchain ainda não instalada: build permanece não verificado.
- `cargo-audit` não executado; code signing e comportamento dinâmico não avaliados.
- Reprodutibilidade não observada (nenhum build realizado).

## 11. Rollback

Trivial: **nada foi instalado ou modificado no sistema**. As únicas mudanças são
textuais e versionadas nesta branch (`test/build-controlado-beam`), reversíveis
por `git revert` na própria branch. `dev` não foi alterada.

## 12. Próxima etapa

Retomar a partir da **FASE F** do plano com o operador presente para aprovar o
UAC do instalador oficial do VS Build Tools, seguindo as regras de segurança já
homologadas (componentes mínimos, sem PATH global, toolchain exata, dois builds
offline, nenhum binário executado).

## 13. Referências

- [`client/patcher/beam-audit/build-plan.example.json`](../client/patcher/beam-audit/build-plan.example.json)
- [`client/patcher/beam-audit/upstream-manifest.example.json`](../client/patcher/beam-audit/upstream-manifest.example.json)
- [`docs/19-preparacao-build-auditavel-beam.md`](19-preparacao-build-auditavel-beam.md)
