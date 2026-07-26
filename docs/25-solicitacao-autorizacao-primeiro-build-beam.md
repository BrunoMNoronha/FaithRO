# `docs/25-solicitacao-autorizacao-primeiro-build-beam.md` — Solicitação Formal de Autorização do Primeiro Build Controlado do Beam Patcher

> **Status:** SOLICITAÇÃO PREPARADA / AUTORIZAÇÃO NÃO CONCEDIDA (ETAPA 2O-D1-B12)
> **Data:** 2026-07-26
> **Decisão humana:** `PENDENTE` (`request_status = PENDING_HUMAN_DECISION`)
> **Build Autorizado:** `NÃO` (a decisão será registrada em etapa e artefato posteriores)

> [!CAUTION]
> **Avisos obrigatórios — leia antes de tudo:**
>
> - **Esta solicitação NÃO concede autorização e NÃO pode conceder a si mesma.** Ela apenas submete o runbook e o vínculo técnico a uma decisão humana futura.
> - **Merge, aprovação deste PR ou revisão técnica NÃO equivalem à autorização operacional** para executar o build.
> - A **decisão humana** (aprovar/negar, responsável, janela, assinatura) será registrada em **artefato separado** — o modelo de autorização [`first-build-authorization.example.json`](../client/patcher/beam-audit/first-build-authorization.example.json) —, **nunca** neste documento de solicitação.
> - Enquanto `request_status = PENDING_HUMAN_DECISION`, permanecem proibidos build, download do Beam, resolução de dependências, `Cargo.lock`, `target`, produção ou execução de binário.
> - A **futura autorização** deverá ser vinculada a **SHAs exatos**, ter **janela com expiração obrigatória** e ser de **uso único**.
> - A **VPS não participa**. **Nenhum cliente ou asset proprietário** é incorporado.

---

## 1. Objetivo

Preparar, documentar e submeter — por Pull Request e como artefato versionado — uma **solicitação formal de autorização humana** para uma **futura** execução controlada do primeiro build do Beam Patcher. Esta etapa é **exclusivamente documental e declarativa**: ela reúne os artefatos integrados pela ETAPA 2O-D1-B11, identifica exatamente o commit do FaithRO e a versão do runbook submetidos à autorização, registra o escopo técnico solicitado e mantém a autorização **não concedida**.

## 2. Escopo desta etapa

- Documento formal de solicitação (este arquivo).
- Modelo declarativo versionado da solicitação ([`first-build-authorization-request.example.json`](../client/patcher/beam-audit/first-build-authorization-request.example.json)).
- Schema restritivo ([`schemas/first-build-authorization-request.schema.json`](../client/patcher/beam-audit/schemas/first-build-authorization-request.schema.json)).
- Validador estático offline dedicado ([`scripts/validate-beam-first-build-authorization-request.py`](../scripts/validate-beam-first-build-authorization-request.py)).
- Workflow de CI somente leitura ([`.github/workflows/validate-beam-first-build-authorization-request.yml`](../.github/workflows/validate-beam-first-build-authorization-request.yml)).
- Atualização mínima dos índices.

## 3. Fora de escopo

- **Qualquer** build, download, clone do Beam, `cargo build/check/test/run/fetch/metadata/update`, `rustc`, `cargo install` ou resolução de dependências.
- Criação de `Cargo.lock` ou `target`; produção, assinatura, empacotamento ou execução de binário; deploy; acesso à VPS.
- **Concessão** de autorização humana; preenchimento de identidade, cargo, decisão, assinatura, timestamps ou janela do autorizador.
- Alteração da toolchain padrão, criação de override ou mudança permanente de `PATH`.

## 4. Arquitetura da autorização (quatro artefatos + solicitação)

A responsabilidade permanece separada para que **nenhum documento autorize a si mesmo**:

| Artefato | Papel |
| --- | --- |
| [`first-build-plan.example.json`](../client/patcher/beam-audit/first-build-plan.example.json) (B8) | **Plano** — intenção e regras gerais. |
| [`first-build-runbook.example.json`](../client/patcher/beam-audit/first-build-runbook.example.json) (B10) | **Runbook** — sequência operacional, go/no-go, procedimentos. |
| [`first-build-authorization.example.json`](../client/patcher/beam-audit/first-build-authorization.example.json) (B10) | **Autorização** — decisão humana futura (template, não concedida). |
| [`first-build-execution-evidence.example.json`](../client/patcher/beam-audit/first-build-execution-evidence.example.json) (B10) | **Evidência** — registro da execução futura (template, não executado). |
| [`first-build-authorization-request.example.json`](../client/patcher/beam-audit/first-build-authorization-request.example.json) (B12) | **Solicitação** — este pedido formal de decisão humana; **não concede**. |

A **solicitação** distingue explicitamente três momentos: **solicitar** (esta etapa), **decidir** (etapa futura, no artefato de autorização) e **executar** (etapa futura, sob o runbook e com evidência). A solicitação aponta para o artefato de autorização como **alvo separado** onde a decisão será registrada.

## 5. Origem (ETAPA 2O-D1-B11)

A ETAPA 2O-D1-B11 integrou o **PR #38** por squash merge em `dev`. O commit de referência do FaithRO usado nesta solicitação é o commit que integrou o runbook:

- **Commit de referência do FaithRO:** `0c7e3c78a15605e44d4618c26ecf0e169d36e475` (`origin/dev`, merge do PR #38).
- **Runbook submetido:** [`first-build-runbook.example.json`](../client/patcher/beam-audit/first-build-runbook.example.json), versão `1.0.0`.

O commit de referência é o ponto de integração do runbook; o vínculo forte é o **hash SHA-256 do arquivo** do runbook, que permanece estável independentemente de commits documentais posteriores.

## 6. Identificação técnica

- **Projeto:** FaithRO — Laos Deos.
- **Operação solicitada:** primeiro build controlado do Beam Patcher.
- **SHA de referência do FaithRO:** `0c7e3c78a15605e44d4618c26ecf0e169d36e475`.
- **Runbook submetido:** `client/patcher/beam-audit/first-build-runbook.example.json`
  - **SHA-256:** `83c701e1e79644f86e5581c8062abacd5e8f2bdf763422ad584807bc5e6c83ed`
- **Modelo de autorização vinculado:** `client/patcher/beam-audit/first-build-authorization.example.json`
  - **SHA-256:** `d057434d3aa1d59f32aa80f360f08aa144c5f58559f699e939fe84edb3705f5b`
- **Toolchain requerida:** `1.85.0-x86_64-pc-windows-msvc` (invocação sempre por nome completo).
- **Toolchain padrão preservada:** `1.77.2-x86_64-pc-windows-msvc`.
- **Target:** `x86_64-pc-windows-msvc`.
- **Ambiente previsto do build futuro:** Windows 11 x86_64, estação de laboratório, shell não elevado, Windows Defender ativo.
- **Confirmação:** o Rust padrão **não** será alterado; **não** haverá override nem mudança permanente de `PATH`.

> Os hashes acima foram calculados **sobre arquivos já existentes no repositório**. O validador desta etapa recomputa esses hashes e **rejeita** qualquer divergência.

## 7. Escopo permitido solicitado

Uma autorização **futura** poderá permitir estritamente (esta solicitação **não** concede nada disto):

1. Obter o código-fonte do Beam a partir da origem oficial previamente aprovada.
2. Verificar origem e integridade contra o manifesto versionado.
3. Preparar workspace temporário efêmero externo ao repositório FaithRO.
4. Usar explicitamente a toolchain nomeada `1.85.0-x86_64-pc-windows-msvc`.
5. Executar um **único** build controlado, offline, com lock fixo.
6. Coletar evidências **sem** executar o binário.
7. Remover integralmente o workspace temporário conforme o runbook.

## 8. Ações que permanecem proibidas

Mesmo após um eventual build autorizado, permanecem **fora do escopo**:

- Executar o binário produzido; realizar deploy; publicar ou distribuir o resultado; entregar a jogadores.
- Empacotar com cliente ou asset proprietário; assinar ou alterar executáveis.
- Desabilitar o Windows Defender; realizar mudança permanente na estação.
- Reutilizar a mesma autorização; acessar a VPS; usar o resultado em produção.

## 9. Estado inicial obrigatório

O modelo mantém explicitamente:

| Campo | Valor |
| --- | --- |
| `request_status` | `PENDING_HUMAN_DECISION` |
| `authorization_granted` | `false` |
| `execution_permitted` | `false` |
| `authorization_used` | `false` |
| `authorization_revoked` | `false` |
| `build_started` | `false` |
| `beam_downloaded` | `false` |
| `binary_produced` | `false` |

O schema trava cada um desses valores por `const`, tornando **estruturalmente impossível** representar uma autorização concedida ou uma execução iniciada neste artefato.

## 10. Decisão humana futura (dados exigidos)

A solicitação **descreve** — sem oferecer campos preenchíveis de concessão — os dados que só poderão ser preenchidos pela pessoa autorizadora, **em etapa posterior e no artefato de autorização separado**:

- Identificador organizacional e função/responsabilidade da pessoa autorizadora.
- Decisão explícita: aprovar ou negar; data e hora UTC da decisão.
- Início e **expiração obrigatória** da janela (máx. 24 h).
- Justificativa; confirmação do SHA do FaithRO e do hash do runbook.
- Confirmação de **uso único**; assinatura, aprovação registrada ou referência auditável.
- Condições adicionais e revogação, se aplicáveis.

Esses dados **não** são inventados aqui. No template de autorização eles permanecem como placeholders inequívocos (`<PREENCHER-...>`) ou nulos.

## 11. Validação estática

Validação offline dedicada (stdlib; não clona, não instala, não constrói, não executa, não concede autorização; recomputa e confere os hashes do runbook e da autorização):

```bash
python scripts/validate-beam-first-build-authorization-request.py
```

O validador confirma o vínculo entre solicitação ↔ runbook ↔ autorização ↔ SHA do FaithRO, rejeita estados que representem autorização/execução já ocorridas, e verifica que o runbook e a autorização referenciados **permanecem bloqueados**.

## 12. Riscos

1. Solicitação associada ao SHA errado do FaithRO.
2. Runbook alterado depois da solicitação (o hash versionado detecta divergência).
3. Hash incorreto registrado (o validador recomputa e rejeita).
4. Pessoa não autorizada registrar a decisão.
5. Confusão entre aprovação do PR e autorização operacional.
6. Autorização expirada ou reutilizada.
7. Escopo interpretado de forma ampla; build executado fora da janela.
8. Evidência incompleta; artefato produzido ser executado ou distribuído indevidamente.
9. Modelo desatualizado após mudança no upstream ou na toolchain.

## 13. Rollback

Etapa documental. **Não** reescrever histórico nem usar force push. Antes do merge, o rollback é **fechar o PR e excluir a branch**. Após eventual merge futuro, o rollback é `git revert` do commit de merge, em branch separada e por novo PR. Não há binário, workspace, dependência, deploy ou alteração de VPS a reverter.

## 14. Próxima etapa permitida

Após revisão e integração deste PR, uma **etapa separada** deverá: apresentar a solicitação a uma pessoa autorizada; registrar uma **decisão humana verificável** no artefato de autorização; validar identidade, escopo, SHAs, hashes e janela; e **manter o build bloqueado** até a concessão formal ser revisada e integrada.

## 15. Declarações

- **Nenhuma autorização foi concedida.** A execução continua proibida.
- **Nenhum build foi executado**, nenhum download do Beam realizado, nenhum binário produzido ou executado.
- **Nenhuma dependência** foi instalada ou alterada; nenhum `Cargo.lock` ou `target` foi criado.
- Rust `1.77.2` continua padrão; Rust `1.85.0` continua apenas nomeada.
- **Nenhum override** ou `PATH` permanente foi criado; nenhuma VPS ou deploy envolvido; nenhum cliente ou asset proprietário manipulado.
- **Aprovação ou merge deste PR não equivalem à autorização operacional.**
