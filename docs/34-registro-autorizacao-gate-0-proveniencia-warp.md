# Registro da autorização humana do GATE 0 (reconfirmação de proveniência)

> **Estado atual:** `GATE 0 AUTORIZADO — AINDA NÃO INICIADO` (ETAPA 2P-E-C0-A).
> **Data:** 2026-07-31.
> **Escopo:** registrar, de forma auditável, a decisão humana que **autoriza
> exclusivamente o GATE 0** (reconfirmação de proveniência por metadados). Esta
> etapa **não** executa o GATE 0, **não** consulta o upstream, **não** coleta
> evidências e **não** autoriza o GATE 1. O merge deste registro **não** executa o
> GATE 0.
> Continua [33](33-plano-auditoria-binaria-offline-warp.md); observa
> [30](30-auditoria-estatica-warp.md), [31](31-decisao-caminho-nucleo-warp.md),
> [32](32-registro-decisao-caminho-nucleo-warp.md) e
> [16](16-politica-distribuicao-cliente.md).

## 1. Objetivo

Registrar a autorização humana **exclusiva** do GATE 0 do plano da auditoria binária
offline do WARP ([docs/33](33-plano-auditoria-binaria-offline-warp.md)), preparando —
sem executar — uma etapa futura e separada de reconfirmação de proveniência por
metadados.

## 2. Contexto

O plano (ETAPA 2P-E-B, PR #46) definiu 17 gates independentes; o GATE 0 é a
reconfirmação de proveniência por metadados, anterior ao GATE 1. O merge do plano
**não** autorizou nenhum gate. Esta etapa registra a primeira autorização humana de
gate.

## 3. Decisão humana

`APPROVE_GATE_0` — autoriza exclusivamente o GATE 0 (reconfirmação de proveniência
por metadados), a ser executado em etapa futura e separada. Registro real:
[`client/warp-audit/decisions/binary-audit-gate-00-decision-record-2026-07-31.json`](../client/warp-audit/decisions/binary-audit-gate-00-decision-record-2026-07-31.json).

## 4. Decisor e autoridade

Decisor `BrunoMNoronha`; função/autoridade "Responsável técnico e mantenedor do
projeto FaithRO - Laos Deos".

## 5. Data e canal

2026-07-31; canal "ChatGPT — conversa do projeto FaithRO".

## 6. Gate autorizado

`GATE 0` — `PROVENANCE_RECONFIRMATION` (id 0), conforme
[binary-audit-plan.example.json](../client/warp-audit/binary-audit-plan.example.json).

## 7. Justificativa

O GATE 0 é a primeira verificação do plano e **não** materializa, baixa nem executa
o binário. A reconfirmação por metadados públicos e oficiais confirma a consistência
entre o plano FaithRO e o upstream oficial antes de qualquer decisão posterior. A
autorização vale **somente** para o GATE 0.

## 8. Escopo permitido

Consultar **somente** metadados públicos e oficiais para reconfirmar: identidade do
repositório upstream; existência do commit fixado; referências, árvore e caminho
declarado do artefato; identificadores Git de commit, árvore e blob; tamanho do blob
quando exposto diretamente pela API de metadados; tags e releases relacionadas apenas
por metadados; licença e informações textuais de proveniência; consistência entre o
plano FaithRO e o upstream oficial. **Nenhum** conteúdo binário é acessado.

## 9. Métodos permitidos

Conjunto fechado, apenas metadados: GitHub API de metadados; GitHub web metadata;
GitHub connector; `git ls-remote`; endpoints de commit, árvore e refs; metadados de
tags e releases; licença e documentação textual. **Sem** comandos operacionais e
**sem** URLs diretas.

## 10. Ações proibidas

Clone; fetch/pull upstream; archive; release asset; blob binário; conteúdo do
prebuilt; materialização; extração; hashing do binário real; inspeção PE;
Authenticode; antivírus; execução; sandbox; cliente; patches; login; VPS;
distribuição; alteração do servidor.

## 11. Condições

As 17 condições estão registradas no artefato real (numeradas 1–17), incluindo:
autorização apenas para o GATE 0; execução em etapa posterior separada; apenas
metadados públicos/oficiais; clone e fetch upstream proibidos; conteúdo do blob
inacessível; nenhuma URL direta do binário; nenhuma materialização; nenhuma análise;
nenhuma sandbox/cliente/VPS; inconsistência interrompe o fluxo; `STOP_PATH`
disponível; aprovação do GATE 0 **não** autoriza o GATE 1; o merge **não** executa o
GATE 0.

## 12. Matriz de autorizações

Apenas **quatro** flags `true`; todas as demais `false`:

```text
human_decision_required=true   human_decision_received=true
gate_selected=true             provenance_reconfirmation_authorized=true

gate_0_started=false           gate_0_completed=false
gate_1_authorized=false        materialization_authorized=false
hashing_authorized=false       static_inspection_authorized=false
local_security_scan_authorized=false    external_reputation_upload_authorized=false
sandbox_creation_authorized=false       execution_without_client_authorized=false
client_copy_provision_authorized=false  execution_with_client_copy_authorized=false
patch_review_authorized=false           patch_application_authorized=false
client_preparation_authorized=false     vps_access_authorized=false
test_account_authorized=false           first_login_authorized=false
distribution_authorized=false
```

## 13. Estado de execução

`AUTHORIZED_NOT_STARTED` — o GATE 0 está **autorizado**, mas **não iniciado**;
nenhuma evidência foi coletada; nenhuma consulta upstream foi realizada nesta etapa.

## 14. Separação entre registro e execução

Esta etapa **registra** a autorização; **não** a executa. A execução do GATE 0 será
uma etapa futura e separada (2P-E-C0-B). O merge deste registro **não** inicia o
GATE 0.

## 15. Critérios de interrupção

Qualquer inconsistência de proveniência (identidade do repositório, existência do
commit, árvore/refs, licença, ou divergência entre o plano e o upstream) deve
**interromper** o fluxo e retornar à decisão humana. `STOP_PATH` permanece
disponível.

## 16. Propriedade intelectual

WARP é GPL-3.0 (uso local; binário **não** versionado). `Ragexe`, GRF, DLLs e assets
Gravity são proprietários — proibido versionar, hospedar, empacotar, enviar à VPS ou
distribuir (ver [16](16-politica-distribuicao-cliente.md)). Nenhum conteúdo binário é
acessado no GATE 0.

## 17. Segurança e privacidade

O registro não contém IP, senha, token, chave, caminho pessoal, URL direta de
binário, comando operacional, hash de binário real nem resultado de análise. O
validador reprova esses conteúdos e reporta apenas arquivo, campo e categoria (sem
ecoar o valor).

## 18. Riscos

R1 registro interpretado como execução; R2 GATE 0 interpretado como autorização de
materialização; R3 método de metadados baixar conteúdo; R4 URL direta induzir
download; R5 autorização transitiva; R6 mensagem de erro expor valor. Mitigações:
`gate_0_started/completed=false`, apenas `provenance_reconfirmation_authorized=true`,
métodos como conjunto fechado, proibição de URLs/clone/fetch, escopo single-gate e
mensagens redigidas.

## 19. Rollback

Antes do merge: corrigir por novo commit; manter draft; fechar o PR; sem force; sem
reescrever `dev`. Após integração: branch de `dev`, reverter o squash, validar, abrir
PR de reversão. A reversão Git **não** apaga a decisão humana histórica; a revogação
exige novo registro humano explícito.

## 20. Estado atual

```text
GATE 0 AUTORIZADO — AINDA NÃO INICIADO
```

## 21. Próxima etapa possível

```text
ETAPA 2P-E-C0-B — executar exclusivamente o GATE 0 por metadados oficiais.
```

Essa próxima etapa **não** pode materializar o binário, **não** pode baixar blob ou
release, **não** pode iniciar o GATE 1 e deverá terminar em **relatório e nova
decisão humana**.

## Estado de verificação

- **Fato:** decisão humana recebida (`APPROVE_GATE_0`); GATE 0 autorizado; não
  iniciado; nenhuma consulta upstream nesta etapa; todas as flags operacionais
  `false`.
- **Inferência/decisão:** apenas o GATE 0 (metadados) fica autorizado; sem
  autorização transitiva; GATE 1 proibido.
- **Pendência:** execução futura e separada do GATE 0 (2P-E-C0-B), com relatório e
  nova decisão humana.
- **Nota:** decisão técnica e de conformidade do projeto, **não** parecer jurídico.
