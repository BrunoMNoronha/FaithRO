# `docs/26-pacote-decisao-humana-primeiro-build-beam.md` — Pacote de Decisão Humana do Primeiro Build Controlado do Beam Patcher

> **Status:** PACOTE PREPARADO / DECISÃO NÃO TOMADA (ETAPA 2O-D1-B14)
> **Data:** 2026-07-26
> **Decisão humana:** `PENDENTE` (`decision_status = PENDING`)
> **Build Autorizado:** `NÃO` (a decisão será registrada e revisada em etapas posteriores)

> [!CAUTION]
> **Avisos obrigatórios — leia antes de tudo:**
>
> - **Este pacote NÃO concede autorização e NÃO permite execução.** Ele apenas reúne, por referência e hash, o que uma pessoa com autoridade precisa para decidir depois.
> - **Este pacote NÃO representa uma decisão.** O registro de decisão versionado é um **formulário em branco** (`decision_status = PENDING`).
> - **Merge, aprovação deste PR ou revisão técnica NÃO equivalem à decisão humana nem à autorização operacional.**
> - **A decisão humana NÃO executa o build automaticamente.** Mesmo aprovada, a execução exige revisão técnica separada e permanece bloqueada nesta etapa.
> - A **decisão real** será registrada em etapa posterior (ETAPA 2O-D1-B15), como instância separada submetida a revisão técnica — **nunca** editando os exemplos versionados.
> - A **VPS não participa**. **Nenhum cliente ou asset proprietário** é incorporado.

---

## 1. Objetivo

Preparar, documentar e validar um **pacote formal** para que uma pessoa com autoridade possa, em uma etapa humana posterior: revisar a solicitação do primeiro build controlado do Beam Patcher; confirmar o escopo, os SHAs, os hashes, os riscos e as restrições; e registrar uma decisão de **aprovação ou recusa**, estabelecendo — somente em caso de aprovação — uma janela limitada e de uso único. Esta etapa **prepara o processo**; ela **não** toma a decisão, **não** preenche aprovação real e **não** autoriza o build.

## 2. Escopo desta etapa

- Pacote de decisão legível ([`first-build-human-decision-package.example.json`](../client/patcher/beam-audit/first-build-human-decision-package.example.json)), com checklist incorporado.
- Registro de decisão **não preenchido** ([`first-build-human-decision-record.example.json`](../client/patcher/beam-audit/first-build-human-decision-record.example.json)).
- Schemas restritivos ([pacote](../client/patcher/beam-audit/schemas/first-build-human-decision-package.schema.json), [registro](../client/patcher/beam-audit/schemas/first-build-human-decision-record.schema.json)).
- Validador estático offline dedicado ([`scripts/validate-beam-first-build-human-decision.py`](../scripts/validate-beam-first-build-human-decision.py)).
- Workflow de CI somente leitura ([`.github/workflows/validate-beam-first-build-human-decision.yml`](../.github/workflows/validate-beam-first-build-human-decision.yml)).
- Fixação de EOL (`.gitattributes`) e atualização mínima dos índices.

## 3. Fora de escopo

- **Qualquer** build, download, clone do Beam, `cargo build/run/install/fetch`, `rustc` ou resolução de dependências.
- Criação de `Cargo.lock` ou `target`; produção, assinatura, empacotamento ou execução de binário; deploy; acesso à VPS.
- **Tomar** a decisão; preencher aprovação/recusa; inventar identidade, cargo, e-mail, assinatura, autoridade ou timestamps do decisor; criar janela ativa.
- Alteração da toolchain padrão, override ou mudança permanente de `PATH`.

## 4. Separação de responsabilidades

Devem permanecer rigorosamente separados: (1) preparação técnica; (2) solicitação de autorização; (3) **pacote apresentado ao decisor** (esta etapa); (4) **decisão humana**; (5) revisão técnica da decisão preenchida; (6) autorização operacional; (7) execução do build; (8) evidência. Nenhum artefato desta etapa autoriza a si mesmo, registra aprovação fictícia, permite execução ou inicia automaticamente a etapa seguinte.

| Artefato | Papel |
| --- | --- |
| [`first-build-plan.example.json`](../client/patcher/beam-audit/first-build-plan.example.json) (B8) | Plano de build. |
| [`first-build-runbook.example.json`](../client/patcher/beam-audit/first-build-runbook.example.json) (B10) | Runbook operacional. |
| [`first-build-authorization.example.json`](../client/patcher/beam-audit/first-build-authorization.example.json) (B10) | Template de autorização (não concedido). |
| [`first-build-authorization-request.example.json`](../client/patcher/beam-audit/first-build-authorization-request.example.json) (B12) | Solicitação formal (pendente). |
| [`first-build-human-decision-package.example.json`](../client/patcher/beam-audit/first-build-human-decision-package.example.json) (B14) | **Pacote** apresentado ao decisor. |
| [`first-build-human-decision-record.example.json`](../client/patcher/beam-audit/first-build-human-decision-record.example.json) (B14) | **Registro** de decisão (formulário em branco). |

## 5. Origem (ETAPA 2O-D1-B13)

A B13 integrou o **PR #39** por squash merge em `dev`. Âncoras usadas nesta etapa:

- **Commit de referência do FaithRO** (contém a solicitação integrada): `4251c373a8bcdbb9e49369668711d64d8140aad3`.
- **Merge do PR #39:** o mesmo commit `4251c373a8bcdbb9e49369668711d64d8140aad3`.

## 6. Estrutura do pacote

O pacote registra, sem duplicar integralmente os arquivos: identificação (projeto, finalidade, versão do formato, SHA do FaithRO, merge do PR #39, identificadores estáveis do pacote e da solicitação); artefatos referenciados por **caminho relativo + SHA-256 + EOL**; o escopo apresentado ao decisor; as proibições permanentes; os riscos; os critérios de autoridade; as regras de aprovação e recusa; as regras de janela, expiração, revogação e uso único; o checklist de decisão; e os procedimentos de entrega e devolução. A data do pacote permanece `null` (depende da entrega humana; **não** se inventa data real).

### 6.1 Artefatos referenciados e hashes (LF)

| Papel | Caminho | SHA-256 (LF) |
| --- | --- | --- |
| solicitação | `client/patcher/beam-audit/first-build-authorization-request.example.json` | `cc57edff417b6da27f8b1a8b3bf8e833a9906f6a8de0dc0fc7389556fdba4f90` |
| runbook | `client/patcher/beam-audit/first-build-runbook.example.json` | `83c701e1e79644f86e5581c8062abacd5e8f2bdf763422ad584807bc5e6c83ed` |
| autorização | `client/patcher/beam-audit/first-build-authorization.example.json` | `d057434d3aa1d59f32aa80f360f08aa144c5f58559f699e939fe84edb3705f5b` |
| plano | `client/patcher/beam-audit/first-build-plan.example.json` | `5b64f9462e238ba450b40fe431f05ef4d9f04bb81b7daaba504dae722e67094c` |

Os hashes foram calculados **sobre os bytes LF** dos arquivos já existentes. O validador **recomputa** cada hash e **rejeita** divergência ou fim de linha CRLF.

## 7. Registro de decisão (formulário em branco)

O registro representa **somente** o estado pendente: `decision_status = PENDING`; `decision = null`; `authorization_granted`, `execution_permitted`, `authorization_used`, `authorization_revoked`, `decision_recorded`, `build_started`, `beam_downloaded`, `binary_produced` = `false`. Os campos de identidade, janela, justificativa e revogação permanecem `null`. O schema trava esse estado por `const`/`null`, tornando **estruturalmente impossível** o exemplo representar uma decisão tomada. Uma decisão real será registrada em instância separada na B15.

## 8. Critérios de autoridade

O procedimento **não** inventa uma pessoa. Define critérios objetivos: mantenedor responsável pelo projeto; pessoa formalmente designada pelo proprietário do repositório; pessoa com responsabilidade explícita pela segurança e operação do build; identidade verificável no canal de decisão adotado; e, quando possível, ausência de conflito com quem executará o build. O formulário prevê identificador, função, base da autoridade, canal verificável, referência auditável, data/hora e confirmação de identidade — todos `null` nesta etapa. Dados pessoais **não** são extraídos automaticamente do GitHub.

## 9. Regras de aprovação e recusa

**Aprovação futura** só será válida se: todos os artefatos forem encontrados; todos os hashes recomputados coincidirem; os SHAs forem confirmados; a origem do Beam estiver explicitamente aprovada; o escopo estiver integralmente compreendido; o uso for único; houver início e expiração dentro do limite; a autorização não tiver sido usada; não houver revogação nem mudança posterior nos artefatos; o registro estiver associado à solicitação e ao pacote; a decisão for feita por autoridade verificável; a aprovação **não** autorizar execução nem distribuição do binário; e **uma revisão técnica separada** aprovar o registro preenchido antes do build.

**Recusa** registra decisão de negar, justificativa, condições não satisfeitas, identidade, autoridade, data/hora e referência auditável, mantendo autorização não concedida, execução proibida, ausência de janela e build bloqueado. A recusa **não** exige campos exclusivos de aprovação.

## 10. Janela, expiração, revogação e uso único

**Janela:** início e expiração absolutos, timezone `UTC`, duração máxima limitada, sem janela retroativa, sem expiração anterior ao início, sem janela indefinida. **Uso único:** uma autorização corresponde a uma única tentativa; qualquer início de execução a consome; falha de build **não** a reabre; nova tentativa exige nova decisão. **Revogação:** pode ocorrer antes da execução, registra identidade/data/razão/referência, prevalece sobre aprovação anterior, impede a execução e **não** pode ser revertida silenciosamente. O modelo **não** representa janela ativa nem revogação real nesta etapa.

## 11. Integridade e fim de linha

Como a B13 identificou risco real de CRLF/LF, todo arquivo cujo hash é persistido tem EOL canônico **LF** explícito em [`.gitattributes`](../.gitattributes). O validador confere os **bytes reais** e **sinaliza CRLF como erro** — sem normalização silenciosa. Um **checkout novo** produz LF; um checkout preexistente pode precisar de re-normalização única (por exemplo, `git add --renormalize . && git checkout .`). Recompute os hashes em checkout novo (por exemplo com `Get-FileHash SHA256`) antes de confiar neles.

## 12. Validação estática

```bash
python scripts/validate-beam-first-build-human-decision.py
```

Offline, apenas stdlib; não clona, não instala, não constrói, não executa, não decide, não autoriza. Recomputa hashes, confere EOL, valida schemas, rejeita estado decidido/autorizado/janela ativa, rejeita comandos, metacaracteres, travessia, URLs não aprovadas e dados sensíveis, e confirma que a solicitação, o runbook e a autorização referenciados permanecem bloqueados.

## 13. Riscos

Decisor sem autoridade; identidade não verificável; decisão fora do canal esperado; SHA errado; hash errado; arquivo alterado depois da decisão; CRLF/LF; solicitação obsoleta; runbook alterado; origem upstream alterada; janela inválida; autorização reutilizada; revogação ignorada; build iniciado antes da revisão da decisão; aprovação de PR confundida com decisão; decisão confundida com execução automática; evidência insuficiente; dados sensíveis em logs; artefato produzido executado ou distribuído indevidamente.

## 14. Rollback

Etapa documental. Antes do merge: **fechar o PR e excluir a branch**, mantendo os achados. Após eventual merge futuro: criar branch a partir de `dev`, `git revert` do commit de merge, validar e abrir PR de reversão. **Nunca** reescrever `dev` nem usar force push. Não há build, binário, dependência, workspace, deploy ou VPS a reverter.

## 15. Próxima etapa permitida

**ETAPA 2O-D1-B15** — apresentar o pacote ao decisor humano e registrar a decisão verificável, com identidade e autoridade fornecidas externamente, canal auditável confirmado, SHAs e hashes recomputados, escopo e riscos apresentados, aprovação ou recusa registrada sem inventar informações, **sem executar o build** e **sem permitir automaticamente a execução**, submetendo o registro preenchido a revisão técnica posterior. **Não executar a B15 agora.**

## 16. Declarações

- **Nenhuma decisão humana foi tomada**; nenhuma identidade foi inventada.
- **Nenhuma autorização foi concedida**; a execução continua proibida; **merge não equivale à decisão**; a decisão futura não executará automaticamente o build.
- **Nenhum download**, **nenhum build**, **nenhum binário** produzido ou executado; **nenhuma dependência** instalada; **nenhum `Cargo.lock` ou `target`** criado.
- Rust `1.77.2` continua padrão; `1.85.0` continua apenas nomeada; sem override ou `PATH` permanente.
- Nenhuma VPS ou deploy; nenhum cliente ou asset proprietário manipulado.
