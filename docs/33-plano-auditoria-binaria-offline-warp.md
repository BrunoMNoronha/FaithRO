# Plano da auditoria binária offline do WARP

> **Estado atual:** `PLANO CRIADO — NENHUMA MATERIALIZAÇÃO AUTORIZADA` (ETAPA
> 2P-E-B-PREBUILT).
> **Data:** 2026-07-31.
> **Escopo:** **exclusivamente planejamento**. Nada é baixado, materializado,
> extraído, hasheado (do binário real), inspecionado, executado nem enviado a
> qualquer serviço. Nenhuma sandbox é criada. **Nenhuma** autorização operacional
> é concedida; **cada gate exige decisão humana independente**; o merge do PR desta
> etapa **não** autoriza o GATE 1.
> Continua [32](32-registro-decisao-caminho-nucleo-warp.md); observa
> [30](30-auditoria-estatica-warp.md), [31](31-decisao-caminho-nucleo-warp.md) e
> [16](16-politica-distribuicao-cliente.md).

## 1. Objetivo

Elaborar um plano técnico, documental e auditável para uma **futura** auditoria
binária **offline** do núcleo prebuilt do WARP, executável em etapas pequenas,
reproduzíveis e bloqueadas por decisões humanas independentes.

## 2. Contexto

A ETAPA 2P-D concluiu que, no commit fixado, o núcleo do WARP existe **apenas** como
binário prebuilt (achado W1). A ETAPA 2P-E-A submeteu o caminho do núcleo à decisão
humana e a ETAPA 2P-E-A2 **registrou** a decisão: `PREBUILT_PATH` **selecionado
apenas para planejamento**. Esta etapa produz esse plano.

## 3. Decisão de origem

Registro real:
[`client/warp-audit/decisions/core-path-decision-record-2026-07-31.json`](../client/warp-audit/decisions/core-path-decision-record-2026-07-31.json)
— `decision.option=PREBUILT_PATH`; `prebuilt_path_authorized=false`;
`materialization_authorized=false`; `execution_authorized=false`;
`client_provision_authorized=false`; `client_modification_authorized=false`;
`first_login_authorized=false`; 15 condições; patches sensíveis bloqueados;
candidatos apenas revisados; `STOP_PATH` disponível.

## 4. O que esta etapa autoriza

- Somente a **produção deste plano** e dos dois templates
  ([plano](../client/warp-audit/binary-audit-plan.example.json),
  [registro por gate](../client/warp-audit/binary-audit-gate-record.example.json)).
- Registra apenas `plan_creation_authorized=true` e `plan_created=true`.

## 5. O que esta etapa NÃO autoriza

Download, materialização, extração, cópia do binário para o repositório, cálculo de
hash do binário real, inspeção PE do binário real, verificação Authenticode do
binário real, envio a antivírus/serviço externo, execução do WARP, criação ou
início de sandbox, fornecimento do `Ragexe`, modificação do cliente, aplicação de
patch, primeiro login, acesso à VPS, alteração de rAthena/`PACKETVER`/MariaDB/
firewall/serviços e distribuição de executáveis, GRFs, DLLs ou assets proprietários.
**Todas** as autorizações operacionais permanecem `false`.

## 6. Princípios da auditoria

Offline por padrão; mínimo privilégio; máquina/sandbox descartável; rede bloqueada;
evidência antes de decisão; hashes calculados localmente; preservação do artefato
original; cópias de trabalho descartáveis; nenhuma alteração do executável original;
nenhum arquivo proprietário no Git; decisões humanas independentes; interrupção
automática em comportamento inesperado; `STOP_PATH` válido em qualquer fase; nenhuma
adaptação do servidor por tentativa; ausência de confiança implícita no prebuilt.

## 7. Modelo de ameaça

O binário prebuilt é tratado como **binário de terceiros de proveniência parcial**
(custody FRACA — ver [31 §6](31-decisao-caminho-nucleo-warp.md)): sem fonte, sem
receita, sem hash publicado, sem assinatura verificada, sem reprodutibilidade. As
ameaças consideradas incluem cadeia de suprimentos, injeção/persistência,
comportamento de rede não documentado, empacotamento/anti-análise e corrupção do
executável do cliente. Nenhuma conclusão automática de "seguro" ou "malicioso" é
admitida.

## 8. Ativos protegidos

Estação/host do operador; o executável original do cliente (`Ragexe`) legalmente
possuído; credenciais e contas; a VPS e seus serviços; a integridade do servidor
(rAthena, MariaDB, firewall); a propriedade intelectual de terceiros.

## 9. Limites de propriedade intelectual

WARP é GPL-3.0 (uso local; binário **não** versionado no FaithRO). `Ragexe`, GRF,
DLLs e assets da Gravity são **proprietários**: proibido versionar, hospedar,
empacotar, enviar à VPS ou distribuir (ver
[16](16-politica-distribuicao-cliente.md)). Nenhum hash de binário real, resultado
de análise real, URL de download ou comando operacional pronto é incluído aqui.

## 10. Arquitetura futura do ambiente

Ambiente **descartável** e **isolado**, sem dados pessoais, credenciais, acesso à
VPS, rede local, clipboard/pastas compartilhadas, sincronização em nuvem ou mounts
do host; com snapshot inicial, documentação de sistema/ferramentas e bloqueio de
rede em mais de uma camada quando tecnicamente possível. **Não** é criado nesta
etapa (ver GATE 6).

## 11. Fases e gates

O plano define **17 gates** (0 a 16), cada um uma unidade separada com objetivo,
ações planejadas, evidências, opções de saída (sempre incluindo `STOP_PATH`) e o que
**não** autoriza. Detalhes em
[`binary-audit-plan.example.json`](../client/warp-audit/binary-audit-plan.example.json).

| Gate | Nome | Natureza |
| :-: | --- | --- |
| 0 | Reconfirmação de proveniência | Metadados; sem materialização |
| 1 | Autorização para materialização | Decisão humana |
| 2 | Materialização e integridade local | Sem execução |
| 3 | Identidade e assinatura | Estático offline |
| 4 | Inventário PE estático | Estático offline |
| 5 | Verificações locais de segurança | Somente mecanismos locais |
| 6 | Preparação da sandbox | Sem criar/iniciar |
| 7 | Baseline dinâmico | Pré-execução |
| 8 | Autorização para execução sem cliente | Decisão humana |
| 9 | Análise dinâmica sem cliente | Rede bloqueada |
| 10 | Avaliação dos resultados sem cliente | Critérios |
| 11 | Autorização para cópia descartável do executável | Decisão humana |
| 12 | Análise com cópia descartável | Rede bloqueada; original preservado |
| 13 | Revisão individual de patches | Uma decisão por patch |
| 14 | Autorização para aplicar patches selecionados | Lista fechada |
| 15 | Preparação controlada do cliente | Sem login |
| 16 | Autorização para primeiro login | Decisão humana final |

## 12. Decisões humanas independentes

Cada gate operacional exige um **registro de decisão próprio** (template
[`binary-audit-gate-record.example.json`](../client/warp-audit/binary-audit-gate-record.example.json)),
com escopo `single-gate`. **Não há autorização transitiva**: a decisão de um gate
não autoriza qualquer outro. O futuro registro real será criado em diretório
separado, com schema próprio/estritamente validado.

## 13. Matriz de autorização

Todas `false` nesta etapa (exceto as duas documentais):

```text
plan_creation_authorized=true          plan_created=true

provenance_reconfirmation_authorized=false  materialization_authorized=false
hashing_authorized=false               static_inspection_authorized=false
local_security_scan_authorized=false   external_reputation_upload_authorized=false
sandbox_creation_authorized=false      execution_without_client_authorized=false
client_copy_provision_authorized=false execution_with_client_copy_authorized=false
patch_review_authorized=false          patch_application_authorized=false
client_preparation_authorized=false    vps_access_authorized=false
test_account_authorized=false          first_login_authorized=false
distribution_authorized=false
```

## 14. Evidências

Cada gate futuro exigirá evidências mínimas (identificador, gate, data, operador,
decisão humana associada, ambiente, ferramentas e versões, resumos de integridade,
entradas, comandos efetivamente executados no futuro, códigos de saída, resultados,
arquivos de evidência e seus resumos, achados, limitações, riscos, decisão,
rollback executado e descarte confirmado). **Nenhuma** evidência real é preenchida
nesta etapa.

## 15. Critérios de aprovação

Um gate só avança com evidência suficiente e decisão humana explícita. Aprovar um
gate **não** implica aprovar o seguinte; aprovação sem cliente **não** autoriza
fornecer o cliente; nenhum resultado isolado aprova o binário.

## 16. Critérios de interrupção

Resultam automaticamente em `STOPPED` ou retorno à decisão humana: divergência do
commit, hash instável, assinatura inválida/enganosa, dependência inesperada,
privilégio elevado não explicado, persistência, tentativa de rede, injeção, driver,
alteração fora do diretório previsto, acesso a credenciais, anti-análise,
empacotamento não explicado, resultado de segurança grave, falha no bloqueio de
rede, sandbox contaminada, evidência incompleta, modificação do original, tentativa
de acessar a VPS, tentativa de distribuir/versionar artefatos e necessidade de
patch sensível não autorizado.

## 17. Tratamento de tentativas de rede

Qualquer tentativa de rede durante análise dinâmica **interrompe** o teste,
**preserva** a evidência e **retorna** à decisão humana. A sandbox deve bloquear
rede em mais de uma camada quando tecnicamente possível.

## 18. Preservação do original

O `Ragexe` original permanece **preservado fora do diretório operacional**. Qualquer
teste futuro usa **somente cópia isolada e descartável**. O executável alterado
**não** pode ser versionado, publicado, enviado à VPS ou distribuído.

## 19. Análise estática

Identidade/assinatura (GATE 3) e inventário PE (GATE 4): cabeçalhos, seções,
entropia, overlay, imports/exports, recursos, manifest, TLS callbacks, relocations,
debug directory, certificados, indicadores de empacotamento, dependências, strings e
possíveis URLs/domínios/caminhos embutidos, privilégios e persistência aparentes.
Nenhuma conclusão depende de uma métrica isolada.

## 20. Análise dinâmica

Somente após GATE 8 (autorização humana): uma execução controlada, **sem** cliente,
**sem** rede, **sem** credenciais, em sandbox descartável, com baseline antes/depois
(GATE 7/9). A observação com cópia descartável do executável (GATE 12) exige rede
bloqueada, baseline limpo e descarte posterior.

## 21. Patches

Cada patch é tratado por decisão separada (GATE 13). Permanecem **bloqueados**
`CustomDLL`, `DisableProtect`, `DisableEncr`, `EnableProxy`; permanecem **apenas
candidatos revisados** `DataFolderFirst`, `CallKoreaClientInfo`. A autorização para
aplicar (GATE 14) registra uma **lista fechada** (vazia = nenhum autorizado); é
proibida autorização genérica.

## 22. Preparação do cliente

Somente futura (GATE 15): cópia operacional separada, inventário, hashes,
permissões, configuração própria/licenciada, reversibilidade; **sem** conteúdo
proprietário no Git, **sem** envio à VPS e **sem** login.

## 23. Primeiro login

Gate humano separado e final (GATE 16), condicionado à conclusão satisfatória dos
gates anteriores, cliente preparado, servidor estável, conta descartável aprovada,
janela de teste, logs, rollback, autorização de acesso à VPS (se necessária) e
validação de PI. **Não** é concedido nesta etapa.

## 24. Segurança e privacidade

Nenhum IP, senha, token, chave, caminho pessoal, nome de máquina, usuário local,
dado de jogador, hash de binário real, resultado real, URL de download ou comando
operacional pronto é incluído. O validador
[`scripts/validate-warp-audit.py`](../scripts/validate-warp-audit.py) reprova esses
conteúdos.

## 25. Riscos

R1 plano interpretado como autorização; R2 autorização transitiva entre gates; R3
confusão entre estático e execução; R4 vazamento de artefato proprietário; R5
sandbox insuficientemente isolada; R6 falso senso de segurança; R7 patch sensível
aprovado por associação. Mitigações: flags operacionais `false`, linguagem
explícita, schemas restritivos, testes negativos, PR draft, um registro por gate,
conjuntos fechados de patches e `STOP_PATH`.

## 26. Rollback

Antes do merge: corrigir por novo commit; manter draft; fechar o PR se necessário;
sem force; sem reescrever `dev`. Após eventual integração: branch a partir de `dev`,
reverter o squash, validar, abrir PR de reversão. A reversão do plano **não** revoga
automaticamente a decisão humana histórica da ETAPA 2P-E-A2; substituí-la exige novo
registro humano explícito.

## 27. Descarte

Ambiente e cópias de trabalho são descartáveis, com política de descarte por gate e
confirmação registrada nas evidências futuras. Nada é preservado além do necessário.

## 28. Limitações

O plano é abstrato: descreve categorias de ferramentas e comandos futuros, **não**
comandos prontos para baixar ou executar o prebuilt. A eficácia real dependerá da
execução futura, autorizada gate a gate, e de evidências que ainda não existem.

## 29. Estado atual

```text
PLANO CRIADO — NENHUMA MATERIALIZAÇÃO AUTORIZADA
```

## 30. Próxima decisão humana necessária

A próxima decisão humana possível — **somente após** revisão e eventual integração
deste plano — será **exclusivamente**:

```text
Decidir se o GATE 0 — reconfirmação de proveniência por metadados — poderá ser iniciado.
```

Essa decisão ainda **não** autoriza materialização, download nem execução do
prebuilt. Este documento **não** a solicita como se já estivesse concedida.

## Estado de verificação

- **Fato:** decisão 2P-E-A2 registrada; plano e templates criados; todas as
  autorizações operacionais `false`.
- **Inferência/decisão:** auditoria binária offline planejada em 17 gates
  independentes, cada um com decisão humana própria e `STOP_PATH`.
- **Pendência:** decisão humana para iniciar (ou não) o GATE 0.
- **Nota:** decisão técnica e de conformidade do projeto, **não** parecer jurídico.
