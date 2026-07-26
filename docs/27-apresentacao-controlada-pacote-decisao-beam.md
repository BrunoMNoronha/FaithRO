# `docs/27-apresentacao-controlada-pacote-decisao-beam.md` — Apresentação Controlada do Pacote de Decisão do Primeiro Build do Beam Patcher

> **Status:** APRESENTAÇÃO PREPARADA / NÃO APRESENTADA (ETAPA 2O-D1-B16)
> **Data:** 2026-07-26
> **Apresentação:** `NÃO REALIZADA` (`presentation_status = NOT_PRESENTED`)
> **Decisão humana:** `NÃO SOLICITADA / NÃO RECEBIDA`
> **Build Autorizado:** `NÃO`

> [!CAUTION]
> **Avisos obrigatórios — leia antes de tudo:**
>
> - **Este material NÃO apresenta o pacote a ninguém.** Prepara o conteúdo, os canais, os critérios de autoridade e os procedimentos para uma futura apresentação controlada.
> - **Nenhuma pessoa foi selecionada como decisora.** Nenhuma identidade, e-mail, função ou autoridade foi preenchida ou inferida.
> - **Nenhum canal foi selecionado. Nenhuma comunicação foi enviada.**
> - **Merge, aprovação deste PR ou revisão técnica NÃO equivalem à apresentação nem à decisão.**
> - **A apresentação não é autorização. A decisão não é autorização operacional. A decisão não executa o build.**
> - A entrega real e o recebimento serão registrados em etapa posterior (ETAPA 2O-D1-B17), com **entrada humana explícita** e canal auditável.
> - A **VPS não participa**. **Nenhum cliente ou asset proprietário** é incorporado.

---

## 1. Objetivo

Preparar, documentar e validar os artefatos necessários para uma **futura apresentação controlada** do pacote de decisão humana do primeiro build do Beam Patcher: o conteúdo exato a apresentar, o procedimento de identificação e validação da autoridade, os canais auditáveis permitidos, o manifesto de entrega, o comprovante de recebimento ainda em branco, o roteiro, o procedimento de recomputação de SHAs e hashes imediatamente antes da apresentação, o procedimento de devolução e os critérios de aceitação do registro recebido. Esta etapa **não** apresenta o pacote, **não** registra decisão, **não** preenche identidade e **não** autoriza qualquer execução.

## 2. Escopo desta etapa

- Manifesto de apresentação ([`first-build-human-presentation-manifest.example.json`](../client/patcher/beam-audit/first-build-human-presentation-manifest.example.json)), estado `NOT_PRESENTED`.
- Comprovante de entrega/recebimento **em branco** ([`first-build-human-presentation-receipt.example.json`](../client/patcher/beam-audit/first-build-human-presentation-receipt.example.json)).
- Schemas restritivos ([manifesto](../client/patcher/beam-audit/schemas/first-build-human-presentation-manifest.schema.json), [comprovante](../client/patcher/beam-audit/schemas/first-build-human-presentation-receipt.schema.json)).
- Validador estático offline dedicado ([`scripts/validate-beam-first-build-human-presentation.py`](../scripts/validate-beam-first-build-human-presentation.py)).
- Workflow de CI somente leitura ([`.github/workflows/validate-beam-first-build-human-presentation.yml`](../.github/workflows/validate-beam-first-build-human-presentation.yml)).
- Fixação de EOL (`.gitattributes`) e atualização mínima dos índices.

## 3. Fora de escopo

- **Qualquer** build, download, clone do Beam, `cargo`, `rustc` ou resolução de dependências; `Cargo.lock`; `target`; binário; deploy; acesso à VPS.
- **Apresentar** o pacote a uma pessoa; **enviar** e-mail, mensagem, formulário ou convite; **selecionar** ou inventar canal ou decisor; **preencher** identidade, função, autoridade, decisão, recebimento, datas, assinaturas ou referências; criar janela ativa.
- Alteração da toolchain padrão, override ou mudança permanente de `PATH`.

## 4. Separação de responsabilidades

Permanecem rigorosamente separados: (1) preparação técnica; (2) solicitação; (3) pacote de decisão; (4) **preparação da apresentação** (esta etapa); (5) apresentação humana; (6) decisão humana; (7) revisão técnica da decisão; (8) autorização operacional; (9) execução do build; (10) evidência. Os artefatos desta etapa **não** tomam decisão, **não** representam apresentação realizada, **não** confirmam recebimento, **não** preenchem identidade, **não** concedem autorização, **não** liberam execução e **não** acionam a etapa seguinte.

## 5. Origem (ETAPA 2O-D1-B15)

A B15 integrou o **PR #40** por squash merge em `dev`. Âncoras usadas nesta etapa:

- **Commit de referência do FaithRO** (contém o pacote integrado): `c5473a22c4c4fb301e91f35779a83d9bc4bca99a`.
- **Merge do PR #40:** o mesmo commit `c5473a22c4c4fb301e91f35779a83d9bc4bca99a`.

## 6. Conteúdo apresentado e hashes (LF)

O manifesto referencia, por caminho relativo e **SHA-256 (LF)**, os seis artefatos apresentados:

| Papel | SHA-256 (LF) |
| --- | --- |
| pacote de decisão | `e217bd25b592e404cb2fce70520529a92289637a9e2c8e8cd48f13d29eb11a87` |
| registro de decisão | `63f74bc71b0415da6036a71bc02e7db5c4881fce24f56c4c1cdce29c6e5127f4` |
| solicitação | `cc57edff417b6da27f8b1a8b3bf8e833a9906f6a8de0dc0fc7389556fdba4f90` |
| runbook | `83c701e1e79644f86e5581c8062abacd5e8f2bdf763422ad584807bc5e6c83ed` |
| plano | `5b64f9462e238ba450b40fe431f05ef4d9f04bb81b7daaba504dae722e67094c` |
| template de autorização | `d057434d3aa1d59f32aa80f360f08aa144c5f58559f699e939fe84edb3705f5b` |

Os hashes foram calculados **sobre os bytes LF** dos arquivos já existentes. O validador **recomputa** cada hash e **rejeita** divergência ou fim de linha CRLF.

## 7. Estado inicial (manifesto e comprovante)

Manifesto: `presentation_status = NOT_PRESENTED`; `presentation_prepared = true` (apenas material preparado, **não** apresentado); `channel_selected`, `decision_maker_identified`, `authority_verified`, `package_delivered`, `package_received`, `decision_requested`, `decision_received`, `authorization_granted`, `execution_permitted`, `build_started`, `beam_downloaded`, `binary_produced` = `false`. Comprovante: idem, com `channel`, `recipient` e `delivery` inteiramente `null`. Os schemas travam esse estado por `const`/`null` — **impossível** representar apresentação, entrega, identidade ou decisão.

## 8. Canais auditáveis permitidos

O procedimento define **categorias** aceitáveis, **sem selecionar** uma agora: Pull Request ou Issue privada apropriada; documento controlado com histórico de revisão; e-mail corporativo ou pessoal previamente verificado; reunião registrada em ata; sistema formal de aprovação; assinatura eletrônica verificável; ou outro canal com identidade, timestamp e histórico auditável. Todo canal futuro exige: identificação, referência auditável, controle de acesso, preservação do conteúdo, data e hora, confirmação de remetente e destinatário, e impossibilidade de alteração silenciosa. **Nada é enviado** e **nenhum canal** (Gmail, GitHub, etc.) é selecionado automaticamente.

## 9. Identificação e autoridade

Exige **entrada humana externa** para nome/identificador, função, fundamento da autoridade, relação com o projeto, canal de contato, identidade verificável, confirmação explícita de autoridade e referência da designação. Nesta etapa, todos esses campos permanecem `null`; `identity_confirmed = false`; `authority_confirmed = false`. **Nenhum nome é inferido** do proprietário do repositório ou de usuários do GitHub; **nenhuma** busca em contatos ou e-mail.

## 10. Roteiro mínimo da futura apresentação

Confirmar identidade e base da autoridade; explicar que a apresentação **não é** autorização; apresentar solicitação e pacote; recomputar hashes e confirmar SHAs e EOL; explicar escopo limitado, ações permanentemente proibidas e riscos; explicar aprovação, recusa, janela, expiração, uso único e revogação; explicar que falha de build **não** reabre a autorização; explicar que a decisão positiva ainda exige **revisão técnica**; explicar que **nenhuma decisão executa o build automaticamente**; entregar o formulário pendente; indicar a devolução; registrar **apenas** que o pacote foi entregue, **caso** isso realmente ocorra; **não** pressionar por decisão imediata.

## 11. Integridade imediatamente antes da apresentação

A futura apresentação deverá: usar checkout limpo; confirmar o commit exato; recomputar os hashes; comparar com o manifesto; verificar o EOL LF; executar os validadores estáticos; confirmar ausência de decisão, de autorização e de build; e gerar um relatório de integridade **sem dados sensíveis**. Nesta etapa, o procedimento é apenas **documentado e validado** — **não** executado como se a apresentação estivesse ocorrendo.

## 12. Entrega e devolução

**Entrega futura** registrará: identificador do manifesto e do pacote, canal, data/hora, remetente, destinatário, referência auditável, hashes apresentados, versão apresentada, e confirmações de que o registro estava pendente, sem autorização e sem execução — todos `null` nesta etapa. **Devolução da decisão**: no mesmo canal ou canal acordado, com identidade verificável, referência ao pacote e manifesto, SHAs e hashes confirmados, aprovação ou recusa explícita, justificativa, janela **apenas** em caso de aprovação, uso único, referência auditável, **sem** comandos, anexos executáveis, binários ou dados sensíveis desnecessários. O recebimento da decisão **não** libera automaticamente o build.

## 13. Critérios de aceitação da decisão devolvida

Uma decisão recebida só poderá avançar para **revisão técnica** se: identidade e autoridade verificáveis; canal auditável; pacote e manifesto coincidentes; hashes e SHAs coincidentes; decisão explícita; assinatura/referência verificável; campos obrigatórios preenchidos; sem campos extras, comandos, anexos binários ou contradições; registro não alterado além dos campos humanos permitidos; e decisão dentro do formato esperado. **Uma decisão recebida ainda não é autorização operacional** até revisão técnica separada.

## 14. Integridade e fim de linha

Todo arquivo cujo hash é persistido tem EOL canônico **LF** em [`.gitattributes`](../.gitattributes), incluindo o manifesto e o comprovante. O validador confere os **bytes reais** e **rejeita CRLF e EOL misto** — sem normalização silenciosa. Um **checkout novo** produz LF; um checkout preexistente pode precisar de re-normalização única (por exemplo, `git add --renormalize . && git checkout .`).

## 15. Validação estática

```bash
python scripts/validate-beam-first-build-human-presentation.py
```

Offline, apenas stdlib; não apresenta, não decide, não autoriza, não envia comunicação. Recomputa hashes, confere EOL, valida schemas, rejeita apresentação realizada, canal/identidade/decisão/autorização preenchidos, comandos, metacaracteres, travessia, URLs não aprovadas e dados sensíveis, e confirma que pacote, registro, solicitação e autorização permanecem bloqueados.

## 16. Riscos

Decisor incorreto; autoridade não verificável; canal não auditável; pacote entregue a destinatário errado; versão errada apresentada; SHA ou hash errado; arquivo alterado após a apresentação; CRLF/LF; checkout antigo com EOL stale; confirmação de recebimento falsa; apresentação confundida com decisão; decisão confundida com autorização; autorização confundida com execução; decisão fora do canal; registro alterado indevidamente; build iniciado antes da revisão; dados sensíveis expostos; anexos executáveis; artefato executado ou distribuído indevidamente.

## 17. Rollback

Etapa documental. Antes do merge: **fechar o PR e excluir a branch**, mantendo os achados. Após eventual merge: `git revert` do commit de merge em branch separada + PR de reversão. **Nunca** reescrever `dev` nem usar force push. Não há apresentação, decisão, build, binário, dependência, deploy ou VPS a reverter.

## 18. Próxima etapa permitida

**ETAPA 2O-D1-B17** — executar a apresentação humana controlada e registrar **somente a entrega** do pacote, com entrada humana explícita para selecionar o canal, identificar o destinatário, apresentar a base da autoridade, autorizar o envio/apresentação, registrar data/hora reais e confirmar o recebimento. A B17 **não** inventará informações, **não** registrará decisão sem manifestação do decisor, **não** concederá autorização, **não** executará build e **não** liberará automaticamente a execução. **Não executar a B17 agora.**

## 19. Declarações

- **Nenhuma apresentação ocorreu**; **nenhum canal foi selecionado**; **nenhuma comunicação foi enviada**.
- **Nenhuma identidade foi preenchida**; **nenhuma autoridade foi confirmada**; **nenhum pacote foi entregue**; **nenhum recebimento foi confirmado**.
- **Nenhuma decisão foi solicitada ou recebida**; **nenhuma autorização foi concedida**; execução continua proibida; **merge não equivale à apresentação ou decisão**; a decisão futura **não** executa automaticamente o build.
- **Nenhum download/build/binário/dependência**; nenhum `Cargo.lock`/`target`.
- Rust `1.77.2` continua padrão; `1.85.0` apenas nomeada; sem override ou `PATH` permanente.
- Nenhuma VPS ou deploy; nenhum cliente ou asset proprietário manipulado.
