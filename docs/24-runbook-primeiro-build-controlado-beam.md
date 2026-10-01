# `docs/24-runbook-primeiro-build-controlado-beam.md` — Runbook do Primeiro Build Controlado do Beam Patcher

> **Status:** RUNBOOK PREPARADO / AUTORIZAÇÃO NÃO CONCEDIDA (ETAPA 2O-D1-B10)
> **Data:** 2026-07-25
> **Toolchain Ativa Conservada:** `1.77.2-x86_64-pc-windows-msvc`
> **Toolchain Nomeada para o Build:** `1.85.0-x86_64-pc-windows-msvc`
> **Build Autorizado:** `NÃO` (exige autorização humana explícita em etapa posterior)

> [!CAUTION]
> **Avisos obrigatórios — leia antes de tudo:**
>
> - **Este runbook NÃO autoriza o build.** Criar, revisar ou integrar o runbook não concede autorização.
> - **O modelo de autorização está propositalmente NÃO concedido** (`authorization_granted=false`, `execution_permitted=false`).
> - **Nenhum comando de build deve ser copiado e executado nesta etapa.** Comandos bloqueados são dados de planejamento.
> - **O merge do runbook NÃO equivale a autorização.**
> - A **futura autorização** deverá estar vinculada a **SHAs exatos** e a uma **janela com expiração**, e ser **de uso único** (consumida ou revogada após o uso).
> - A **futura execução** deverá usar **workspace temporário externo** ao repositório FaithRO.
> - O **binário futuro NÃO será executado automaticamente**.
> - A **VPS não participa**.
> - **Nenhum cliente ou asset proprietário** (Ragnarok, GRF, DLLs da Gravity) será incorporado.

---

## 1. Objetivo

Transformar o plano integrado do primeiro build controlado do Beam Patcher ([`docs/23`](23-planejamento-primeiro-build-controlado-beam.md) / [`first-build-plan.example.json`](../client/patcher/beam-audit/first-build-plan.example.json)) em um **runbook operacional revisável**, com **checkpoint explícito de autorização humana**, **critérios objetivos de go/no-go** e **modelo de evidência** — **sem executar o build**.

## 2. Escopo

- Runbook operacional versionado e validável (sequência ordenada com IDs estáveis).
- Modelo declarativo de autorização humana (template, não concedido).
- Template de evidência da execução futura (execução não iniciada).
- Schemas, validador estático offline, testes negativos e workflow de CI.
- Documentação técnica em português brasileiro.

## 3. Fora de escopo

- **Qualquer** build, download, clone do Beam, `cargo build/check/test/run/fetch/metadata/update`, `rustc` contra o fonte ou resolução de dependências.
- Instalação/alteração de toolchains, componentes, targets; alteração da default; override; alteração de PATH.
- Produção, assinatura, empacotamento ou execução de binário; deploy; acesso à VPS.
- Concessão de autorização humana; alteração do plano B8 já aprovado.

## 4. Arquitetura

A responsabilidade é **separada em quatro artefatos distintos**, para que autorização não se confunda com evidência e o runbook não sirva de autorização de si mesmo:

| Artefato | Papel |
| --- | --- |
| [`first-build-plan.example.json`](../client/patcher/beam-audit/first-build-plan.example.json) (B8) | **Plano** — intenção e regras gerais (imutável nesta etapa). |
| [`first-build-runbook.example.json`](../client/patcher/beam-audit/first-build-runbook.example.json) | **Runbook** — sequência operacional ordenada, go/no-go, procedimentos. |
| [`first-build-authorization.example.json`](../client/patcher/beam-audit/first-build-authorization.example.json) | **Autorização** — decisão humana futura (template, não concedida). |
| [`first-build-execution-evidence.example.json`](../client/patcher/beam-audit/first-build-execution-evidence.example.json) | **Evidência** — registro da execução futura (template, não executado). |

Justificativa: o plano permanece estável; o runbook descreve **como** executar sem **quando**; a autorização define **quando/quem/por quanto tempo**; a evidência registra **o que de fato ocorreu**. Nenhum documento autoriza a si mesmo.

## 5. Relação com o plano B8/B9

O runbook **não** substitui nem muta o plano B8. Ele o referencia (`plan_reference`) e reusa os invariantes já aprovados: origem, commit fixado, digest, overlay, toolchain nomeada, política de rede e limpeza. O validador faz verificação cruzada com o plano, o manifesto e o overlay.

## 6. Arquivos afetados

| Arquivo | Finalidade |
| --- | --- |
| [`docs/24-runbook-primeiro-build-controlado-beam.md`](24-runbook-primeiro-build-controlado-beam.md) | Este documento. |
| [`client/patcher/beam-audit/first-build-runbook.example.json`](../client/patcher/beam-audit/first-build-runbook.example.json) | Runbook operacional (25 passos, go/no-go, procedimentos). |
| [`client/patcher/beam-audit/first-build-authorization.example.json`](../client/patcher/beam-audit/first-build-authorization.example.json) | Modelo de autorização humana (não concedido). |
| [`client/patcher/beam-audit/first-build-execution-evidence.example.json`](../client/patcher/beam-audit/first-build-execution-evidence.example.json) | Template de evidência futura (não executado). |
| [`client/patcher/beam-audit/schemas/first-build-runbook.schema.json`](../client/patcher/beam-audit/schemas/first-build-runbook.schema.json) | JSON Schema do runbook. |
| [`client/patcher/beam-audit/schemas/first-build-authorization.schema.json`](../client/patcher/beam-audit/schemas/first-build-authorization.schema.json) | JSON Schema da autorização. |
| [`client/patcher/beam-audit/schemas/first-build-execution-evidence.schema.json`](../client/patcher/beam-audit/schemas/first-build-execution-evidence.schema.json) | JSON Schema da evidência. |
| [`scripts/validate-beam-first-build-runbook.py`](../scripts/validate-beam-first-build-runbook.py) | Validador estático offline (stdlib), com verificação cruzada. |
| [`.github/workflows/validate-beam-first-build-runbook.yml`](../.github/workflows/validate-beam-first-build-runbook.yml) | Workflow de CI (somente validação estática). |

## 7. Pré-condições

- Repositório FaithRO limpo, sem operação Git pendente, sincronizado com `origin/dev` (commit de governança `4c6a908e09cad84d7ad275267c9b4f912c56b76e`).
- Rust `1.77.2-x86_64-pc-windows-msvc` como default; `1.85.0-x86_64-pc-windows-msvc` apenas como toolchain nomeada.
- Nenhum override; nenhum `rust-toolchain*`; nenhum `Cargo.lock`; nenhum `target`.
- Shell não elevado; Windows Defender ativo.

## 8. Estados do processo

1. **Planejado** — runbook criado, comandos documentados, evidência definida; nenhuma autorização; nenhuma execução (estado atual).
2. **Autorizado** — só em etapa futura, mediante declaração humana explícita vinculada a SHAs, digest, toolchain, host, janela, escopo, critérios e responsável.
3. **Executado** — só após execução real, com evidências completas.

Nesta etapa (B10): `human_authorization_required=true`, `human_authorization_granted=false`, `execution_authorized=false`, e todos os marcadores de build/binário/deploy/VPS em `false`. Nenhum campo ausente, nulo ou ambíguo equivale a autorização.

## 9. Checkpoint de autorização

O passo `RB-02 (authorization_check)` é o **gate** que confere a autorização antes de qualquer ação com efeito colateral. Sem autorização válida, vinculada e não consumida, o resultado é **NO-GO**.

## 10. Modelo de autorização

O template ([`first-build-authorization.example.json`](../client/patcher/beam-audit/first-build-authorization.example.json)) contém vínculo técnico já fixado (commit e digest do Beam, hash do overlay, toolchain, target) e **placeholders** `<PREENCHER-...>` para a decisão humana futura (commit do FaithRO, SHA do runbook, responsável, janela, host). O validador **rejeita** qualquer autorização que apareça concedida, usada, revogada-mas-aceita, sem expiração, reutilizável, sem responsável ou com placeholder tratado como aprovação.

## 11. Validade e revogação

A autorização futura será de **uso único** (`single_use=true`), com janela **limitada** (`max_duration_hours` de 1 a 24) e **expiração obrigatória**. É **revogável** e deverá ser **consumida ou revogada** após o uso.

## 12. Go/No-Go

O runbook define listas objetivas de condições de **GO** e **NO-GO**. **Não** existe "prosseguir com ressalvas" (`proceed_with_reservations_allowed=false`); resultado incerto é **NO-GO** (`ambiguous_result_is="NO-GO"`).

## 13. Runbook

Sequência de 25 passos (`RB-01`..`RB-25`) com identificadores estáveis, dependências, execução (`allowed_read_only` ou `blocked_pending_authorization`), rede, evidência, critérios de sucesso/falha, ação em falha e rollback local. Fases:

`host_gate → authorization_check → prepare_workspace → capture_baseline → acquire_source → verify_integrity → initial_inventory → prepare_overlay → apply_overlay → validate_overlay → verify_toolchain → verify_components_targets → prepare_dependencies → offline_transition → primary_build → capture_exit_code → inventory_artifacts → hash_artifacts → static_inspection → confirm_no_execution → cleanup → capture_final_state → reconciliation → closure → generate_evidence`.

## 14. Comandos planejados (NÃO AUTORIZADOS PARA EXECUÇÃO)

> [!WARNING]
> Os comandos do runbook são **dados de planejamento**. Passos de download, resolução, patch, build ou execução permanecem `blocked_pending_authorization`. Somente passos `allowed_read_only` (gate do host, conferência de autorização, baseline, conferência de toolchain/componentes) podem ser executados para **validar o ambiente**. `<TEMP>` é o workspace temporário externo; `<PATCH>` é o overlay versionado.

Todos os comandos usam a **toolchain nomeada** `1.85.0-x86_64-pc-windows-msvc`. O build é `cargo build --release --locked --offline`.

## 15. Coleta de baseline

Toolchain default/ativa, overrides, componentes, targets, arquivos seletores, PATH permanente, estado do repositório, inventário inicial e estado do Windows Defender — **sem** usuário, caminho pessoal, token ou IP.

## 16. Integridade

Reconferência do `tree_digest` `sha256` `4f405c9ecfb2f505d99b00bc77468961e3aa98c72f9ec30faa3939849465b9d5` contra o manifesto. Divergência interrompe (NO-GO).

## 17. Overlay

Overlay [`beam-lab-security.patch`](../client/patcher/beam-audit/overlays/beam-lab-security.patch) (`sha256` `945dbd2f354f9738f77fced4dd3a70923227ede042bbd3819dcadb44ca5c37fe`) aplicado **integralmente** antes do build e validado. O hash é vinculado na autorização.

## 18. Toolchain

Invocação sempre por nome completo; default 1.77.2 preservada; sem override; sem alteração de PATH; sem instalação implícita de componente ou target.

## 19. Dependências e rede

`Cargo.lock` ausente no upstream é **gerado** no clone temporário (rotulado como gerado pelo FaithRO) e **fixado** (`--locked`). Rede permitida apenas em `acquire_source`, `prepare_dependencies` e `offline_transition`, restrita a `github.com`, `static.rust-lang.org` e `crates.io`. Build e comparação são **offline**.

## 20. Build futuro

Um build controlado, offline, na toolchain nomeada, com lock fixo, produzindo artefatos apenas no workspace temporário.

## 21. Artefatos futuros

Inventariados e com `SHA-256` registrado **sem execução**.

## 22. Inspeção

Inspeção estática dos artefatos; confirmação explícita de que **nenhum binário foi executado**.

## 23. Evidências

Template ([`first-build-execution-evidence.example.json`](../client/patcher/beam-audit/first-build-execution-evidence.example.json)) com identidade, baseline, execução e estado final. Nesta etapa: execução **não iniciada**, listas de comandos/artefatos **vazias**, nenhum hash ou timestamp de execução preenchido, sem dados pessoais/segredos.

## 24. Interrupção

Interromper na primeira condição de NO-GO; não prosseguir com ressalvas; registrar passo, comando e saída; remover o workspace; confirmar FaithRO limpo.

## 25. Limpeza

Remover integralmente o workspace temporário; confirmar ausência de arquivos fora dele; confirmar FaithRO intocado pelo build.

## 26. Rollback

Nesta etapa não há binário, dependência, workspace de compilação ou deploy a reverter. Para os artefatos versionados: abandonar a branch antes do merge, ou `git revert` do merge em nova branch após integração futura. **Nunca** reescrever `dev` nem usar force push.

## 27. Riscos

1. Runbook pode desatualizar após mudança upstream.
2. Autorização pode ser concedida para SHA errado.
3. Janela de autorização pode expirar durante a preparação.
4. Verificação textual de comandos não é exaustiva.
5. Build pode falhar por linker ou exigir dependência nativa.
6. Rede pode produzir resultado diferente; overlay pode deixar de aplicar.
7. Workspace pode produzir arquivos inesperados; evidência pode ficar incompleta.
8. Build bem-sucedido **não** autoriza execução nem distribuição.
9. O patcher **não** autoriza cliente ou assets proprietários.
10. O merge do runbook **não** autoriza o build; a execução exige autorização humana específica, revogável e de uso único; qualquer divergência produz **NO-GO**.

## 28. Segurança

Nenhum build, download, resolução, binário, execução, deploy ou VPS nesta etapa. Windows Defender permanece ativo. Sem privilégio administrativo. Sem alteração de default, override ou PATH.

## 29. Propriedade intelectual

O Beam Patcher é `MIT OR Apache-2.0`. Nenhum asset proprietário (cliente, GRF, DLLs da Gravity) é incorporado, empacotado ou distribuído.

## 30. Próxima etapa permitida

**ETAPA 2O-D1-B11 — Revisar e integrar o runbook e os modelos de autorização do primeiro build controlado.** A B11 deverá continuar **sem executar o build**.
