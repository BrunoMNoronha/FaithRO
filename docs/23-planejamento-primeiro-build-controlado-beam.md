# `docs/23-planejamento-primeiro-build-controlado-beam.md` — Planejamento do Primeiro Build Controlado do Beam Patcher

> **Status:** PLANEJADO / DOCUMENTADO (ETAPA 2O-D1-B8)
> **Data:** 2026-07-25
> **Toolchain Ativa Conservada:** `1.77.2-x86_64-pc-windows-msvc`
> **Toolchain Nomeada para o Build:** `1.85.0-x86_64-pc-windows-msvc`
> **Build Autorizado:** `NÃO` (exige autorização humana explícita em etapa posterior)

> [!CAUTION]
> **Este documento NÃO autoriza o build.**
>
> - Copiar comandos isolados deste documento **não** constitui autorização.
> - O build somente poderá ocorrer **após revisão e integração** deste plano (ETAPA 2O-D1-B9) e **autorização humana explícita** registrada em etapa posterior.
> - A execução deverá acontecer em **workspace temporário fora do repositório FaithRO**.
> - O binário produzido **não** poderá ser executado automaticamente.
> - A **VPS não participa** do build.
> - **Nenhum asset proprietário** (cliente Ragnarok, GRF, DLLs da Gravity) será incorporado.

---

## 1. Objetivo

Produzir um plano técnico, auditável e seguro para uma **futura** execução do primeiro build controlado do Beam Patcher, com a toolchain nomeada `1.85.0-x86_64-pc-windows-msvc`, sem executar o build nesta etapa. O plano define origem, integridade, workspace, toolchain, dependências, rede, overlay, sequência, evidências, critérios de sucesso e falha, riscos, rollback, limpeza e a autorização humana obrigatória.

O artefato versionado que representa este plano de forma validável é
[`client/patcher/beam-audit/first-build-plan.example.json`](../client/patcher/beam-audit/first-build-plan.example.json).

## 2. Escopo

- Inspeção estática das evidências já versionadas (B1–B6).
- Modelagem do plano de execução futura como artefato JSON versionado.
- Validador estático dedicado, schema, testes negativos e workflow de CI.
- Documentação técnica em português brasileiro.

## 3. Fora de escopo

- **Qualquer** compilação, download de dependências, `cargo build/check/test/run/fetch/metadata/update`, `git clone` do Beam ou `rustc` contra o fonte.
- Instalação/alteração de toolchains, componentes, targets, Build Tools ou SDK.
- Alteração da toolchain padrão, criação de override, alteração permanente de PATH.
- Produção, assinatura, empacotamento ou execução de binário.
- Deploy, acesso à VPS e qualquer contato com dados reais de jogadores.
- Modificação de `Cargo.toml`, `Cargo.lock`, código upstream, overlay ou manifest já registrados.

## 4. Pré-condições

- Repositório FaithRO limpo, sem operação Git pendente, sincronizado com `origin/dev`.
- Merge do PR #36 presente em `origin/dev` (commit de governança `58dfbe9b527cb31d8214e960fb27d52be10d07aa`).
- Toolchain padrão `1.77.2-x86_64-pc-windows-msvc` (default) preservada.
- Toolchain `1.85.0-x86_64-pc-windows-msvc` instalada **apenas** como toolchain nomeada (ETAPA 2O-D1-B6).
- Nenhum override; nenhum arquivo `rust-toolchain`/`rust-toolchain.toml` no repositório ou diretórios pais.
- Shell não elevado; Windows Defender ativo.

## 5. Arquivos afetados

| Arquivo | Finalidade |
| --- | --- |
| [`docs/23-planejamento-primeiro-build-controlado-beam.md`](23-planejamento-primeiro-build-controlado-beam.md) | Este documento (planejamento). |
| [`client/patcher/beam-audit/first-build-plan.example.json`](../client/patcher/beam-audit/first-build-plan.example.json) | Plano do primeiro build (autorização de execução), versionado e validável. |
| [`client/patcher/beam-audit/schemas/first-build-plan.schema.json`](../client/patcher/beam-audit/schemas/first-build-plan.schema.json) | JSON Schema do plano. |
| [`scripts/validate-beam-first-build-plan.py`](../scripts/validate-beam-first-build-plan.py) | Validador estático offline (stdlib), com verificação cruzada. |
| [`.github/workflows/validate-beam-first-build-plan.yml`](../.github/workflows/validate-beam-first-build-plan.yml) | Workflow de CI (somente validação estática). |

Índices atualizados: [`docs/README.md`](README.md), [`client/patcher/README.md`](../client/patcher/README.md), [`client/patcher/beam-audit/README.md`](../client/patcher/beam-audit/README.md).

## 6. Arquitetura do build controlado

O build futuro é uma sequência determinística e isolada, executada **fora** do repositório FaithRO, em diretório temporário descartável:

`verificação inicial → clone temporário → checkout destacado → conferência de integridade → overlay de segurança → geração e fixação do lock → fase explícita de download → build offline → inventário e hashes → segundo build offline → verificação final → limpeza`.

Nenhuma etapa altera o repositório FaithRO, a toolchain padrão ou o ambiente global.

## 7. Origem e integridade

- **Origem oficial:** `https://github.com/beamguides/beam-patcher` (sem mirror).
- **Commit fixado:** `feed97887090d121f796bc1b941390e28b7a2da5` (referência `v1.0.1`).
- **Checkout destacado** obrigatório; **branch flutuante proibida**.
- **Integridade:** `sha256` da árvore `4f405c9ecfb2f505d99b00bc77468961e3aa98c72f9ec30faa3939849465b9d5`, reconferida contra
  [`client/patcher/beam-audit/upstream-manifest.example.json`](../client/patcher/beam-audit/upstream-manifest.example.json) via `scripts/audit-beam-upstream.py`. Divergência **interrompe** a execução.
- **Licença:** `MIT OR Apache-2.0`.

## 8. Workspace temporário

- Diretório temporário do sistema, prefixo `faithro-beam-build-`, **fora** do repositório FaithRO.
- Proibido usar o diretório do repositório FaithRO como workspace de compilação.
- Qualquer arquivo criado **fora** do workspace temporário interrompe a execução.
- Removido integralmente ao final (`Remove-Item -Recurse -Force <TEMP>`).

## 9. Seleção explícita da Rust 1.85.0

- Toolchain **nomeada** obrigatória: `1.85.0-x86_64-pc-windows-msvc`.
- Invocação sempre por nome completo (`rustup run 1.85.0-x86_64-pc-windows-msvc cargo ...` ou `cargo +1.85.0-x86_64-pc-windows-msvc ...`).
- Perfil `minimal` (`rustc`, `cargo`, `rust-std`); target `x86_64-pc-windows-msvc`.
- Instalação implícita de componentes ou targets **proibida**.
- Justificativa técnica em [`docs/20-primeiro-build-controlado-beam.md`](20-primeiro-build-controlado-beam.md) (B1/B2): a Rust 1.77.2 é incompatível com o grafo (`zeroize 1.9.0` exige `edition = "2024"`/MSRV `1.85`).

## 10. Preservação da Rust 1.77.2

- `1.77.2-x86_64-pc-windows-msvc` permanece como toolchain **padrão/default** global antes e depois do build.
- **Proibido** `rustup default <toolchain>`, `rustup override set`, e alteração permanente de PATH.
- A verificação final confirma default e ausência de override.

## 11. Política de dependências

- `Cargo.lock` **ausente** no upstream. Será **gerado** no clone temporário e claramente rotulado como **gerado pelo FaithRO** (nunca como arquivo original do upstream).
- Após a geração, o grafo é **fixado** (`--locked`); builds subsequentes usam `--locked`/`--offline`.
- **Proibido** `cargo update` ou alteração de dependências. Mudança inesperada no lockfile **interrompe** a execução.
- Nenhum `Cargo.lock` é versionado no repositório FaithRO.

## 12. Política de rede

- Rede permitida **apenas** nas fases: `prepare_source_clone`, `generate_lockfile`, `fetch_dependencies`.
- Hosts esperados (derivados de [`docs/21`](21-plano-instalacao-toolchain-rust-beam.md) gate 8 e do build-plan): `github.com` (fonte), `static.rust-lang.org`, `crates.io` (registro de dependências).
- Qualquer **download de origem não prevista interrompe** a execução.
- **Nenhuma credencial** é exigida.
- O build principal e o segundo build são **offline** (`--offline`).

## 13. Aplicação do overlay

- Overlay obrigatório: [`client/patcher/beam-audit/overlays/beam-lab-security.patch`](../client/patcher/beam-audit/overlays/beam-lab-security.patch), aplicado **antes** do primeiro build no clone temporário.
- Aplicação **integral** obrigatória (`git apply --check` antes) e validação via `scripts/validate-beam-security-overlay.py`.
- Overlay que não aplica integralmente **interrompe** a execução.
- O overlay endurece a superfície Tauri/rede/processos (updater off, CSP definida, HTTP restrito a loopback, `shell.open` off, lançamento de cliente/SSO bloqueado, `bundle` off).

## 14. Sequência planejada

1. Verificação inicial da toolchain e do repositório.
2. Clone temporário externo (sem checkout).
3. Checkout destacado no commit fixado.
4. Conferência de integridade contra o manifesto.
5. Aplicação do overlay de segurança.
6. Validação do overlay.
7. Geração do `Cargo.lock` (rotulado como gerado pelo FaithRO).
8. Resolução com `--locked` (`cargo metadata --locked`).
9. Fase explícita de download das dependências (rede permitida).
10. Inventário do cache de dependências.
11. **Primeiro build** (`--release --locked --offline`).
12. Inventário dos artefatos produzidos.
13. Registro de SHA-256 dos artefatos (sem executar).
14. Segundo build offline para comparação.
15. Verificação final (default preservada, sem override).
16. Limpeza do workspace temporário.

## 15. Comandos planejados (NÃO AUTORIZADOS PARA EXECUÇÃO)

> [!WARNING]
> Os comandos abaixo são **dados de planejamento**, representados também em
> [`first-build-plan.example.json`](../client/patcher/beam-audit/first-build-plan.example.json)
> (`planned_commands.executable_now = false`). **Nenhum** está autorizado nesta etapa.
> `<TEMP>` é o workspace temporário externo; `<PATCH>` é o overlay versionado.

```text
# verificação inicial (somente leitura)
rustup show active-toolchain; rustup toolchain list; rustup override list

# origem e integridade
git clone --filter=blob:none --no-checkout https://github.com/beamguides/beam-patcher.git <TEMP>
git -C <TEMP> checkout --detach feed97887090d121f796bc1b941390e28b7a2da5
python scripts/audit-beam-upstream.py --source <TEMP> --output <TEMP>/beam-audit.json

# overlay de segurança
git -C <TEMP> apply --check <PATCH>; git -C <TEMP> apply <PATCH>
python scripts/validate-beam-security-overlay.py --source <TEMP> --patch <PATCH>

# lock, download e build (toolchain nomeada 1.85.0)
rustup run 1.85.0-x86_64-pc-windows-msvc cargo generate-lockfile
rustup run 1.85.0-x86_64-pc-windows-msvc cargo metadata --locked --format-version 1
rustup run 1.85.0-x86_64-pc-windows-msvc cargo fetch --locked
rustup run 1.85.0-x86_64-pc-windows-msvc cargo build --release --locked --offline

# inventário, hashes e verificação (sem executar o binário)
Get-ChildItem -Recurse <TEMP>/target/release
Get-FileHash -Algorithm SHA256 <TEMP>/target/release/*
rustup show active-toolchain; rustup show; rustup override list

# limpeza
Remove-Item -Recurse -Force <TEMP>
```

## 16. Evidências futuras a coletar

Timestamps; host/SO sem dados sensíveis; SHA do FaithRO; origem e SHA do Beam; hashes dos arquivos baixados; versões de `rustup`/`rustc`/`cargo`; default e toolchain ativa antes/depois; overrides antes/depois; componentes e targets antes/depois; comandos executados e códigos de saída; arquivos produzidos e seus hashes; inventário do workspace; confirmação de que o binário não foi executado; de que não houve deploy; de que a VPS não foi acessada; e de que o Windows Defender permaneceu ativo. **Sem** nome de usuário, token ou caminho pessoal.

## 17. Critérios de sucesso

Fonte corresponde ao commit fixado; integridade validada; toolchain nomeada confirmada; default 1.77.2 preservada; overlay aplicado integralmente; build encerra com código zero; artefatos esperados apenas no workspace temporário; nenhum artefato inesperado; nenhum binário executado; hashes registrados; workspace removível; FaithRO permanece limpo; nenhuma conexão com a VPS.

## 18. Critérios de falha e interrupção

Toolchain divergente; mudança da default; override detectado; `rust-toolchain*` inesperado; componente/target não autorizado; versão upstream divergente; falha de integridade; overlay que não aplica; download de origem não prevista; modificação de dependência; alteração inesperada de `Cargo.lock`; pedido de privilégio administrativo; pedido para desabilitar proteção; arquivos fora do workspace; tentativa de execução do binário; acesso à VPS; alteração no FaithRO; build não determinístico ou não explicado.

## 19. Riscos

1. O plano pode ficar desatualizado se o upstream mudar.
2. Um comando correto ainda pode falhar por linker ou dependência nativa.
3. Usar `cargo` sem toolchain nomeada selecionará a Rust padrão (1.77.2) e falhará por MSRV.
4. Dependências podem exigir rede na execução futura.
5. O overlay pode deixar de aplicar após mudança upstream.
6. O build pode produzir arquivos inesperados.
7. O binário ainda precisará de inspeção antes de qualquer execução.
8. Um build bem-sucedido não autoriza distribuição.
9. O patcher não autoriza distribuição de cliente ou assets proprietários.
10. A execução futura exigirá autorização humana separada.

## 20. Rollback

Exclusivamente Git nesta etapa: abandonar a branch antes do merge caso reprovada; fechar o PR sem merge; remover o worktree dedicado, se criado; após eventual integração futura, usar `git revert` em nova branch. **Nunca** reescrever o histórico de `dev` nem usar force push em branches protegidas. Como nenhum build ocorre nesta etapa, **não** há rollback de binário, dependências ou workspace de compilação.

## 21. Limpeza

Nesta etapa não há workspace de build. Na execução futura, remover integralmente o diretório temporário (`Remove-Item -Recurse -Force <TEMP>`) e confirmar que o repositório FaithRO permanece intocado pelo build.

## 22. Autorização humana

A execução do primeiro build controlado é **bloqueada** por padrão
(`execution_state.build_authorized = false`, `next_human_authorization_required = true`,
`human_authorization.granted = false`). Só poderá ocorrer após revisão e integração deste plano e **autorização humana explícita** registrada em etapa posterior.

## 23. Próxima etapa permitida

**ETAPA 2O-D1-B9 — Revisar e integrar o plano do primeiro build controlado do Beam Patcher.** A B9 revisará o plano, o schema, o validador, os testes negativos e o PR. O build real **não** é a próxima ação imediata.
