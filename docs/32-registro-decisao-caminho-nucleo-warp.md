# Registro da decisão humana do caminho do núcleo do WARP

> **Status:** DECISÃO HUMANA REGISTRADA — `PREBUILT_PATH` **selecionado apenas
> para planejamento** (ETAPA 2P-E-A2).
> **Data:** 2026-07-31.
> **Escopo:** registro documental e auditável da decisão humana e preparação da
> trilha para o **planejamento** da auditoria binária offline (2P-E-B-PREBUILT).
> **Nada** foi materializado, baixado, extraído, compilado ou executado; **nenhuma**
> autorização operacional foi concedida; o merge do futuro PR **não** autoriza a
> próxima ação; **cada gate futuro exige decisão humana separada**.
> Continua [31](31-decisao-caminho-nucleo-warp.md); observa
> [30](30-auditoria-estatica-warp.md), [28](28-decisao-ferramenta-preparacao-cliente.md)
> e [16](16-politica-distribuicao-cliente.md).

## 1. O que esta etapa é (e o que não é)

Esta etapa **registra** — de forma fiel e auditável — a decisão humana recebida
sobre o caminho do núcleo do WARP e **prepara o plano** da futura auditoria
binária offline. Ela **não** solicita nova escolha, **não** amplia autorizações e
**não** inicia a auditoria binária.

Deixa-se explícito, sem ambiguidade:

- `PREBUILT_PATH` foi **selecionado apenas para planejamento**;
- o prebuilt **não** foi materializado;
- o prebuilt **não** foi executado;
- **nenhuma** autorização operacional foi concedida;
- o **merge** do futuro PR **não** autoriza a próxima ação;
- **cada gate futuro exige decisão humana separada**.

A palavra "selecionado" significa apenas que **este** será o caminho submetido ao
planejamento da auditoria. Ela **não** significa que o binário está autorizado
para materialização, execução ou uso.

## 2. Decisão registrada

| Campo | Valor |
| --- | --- |
| Decisor | `BrunoMNoronha` |
| Função / autoridade | Responsável técnico e mantenedor do projeto FaithRO - Laos Deos |
| Canal | ChatGPT — conversa do projeto FaithRO |
| Data | 2026-07-31 |
| Opção selecionada | **`PREBUILT_PATH`** (registrada em `decision.option`) |
| Commit fixado | `9b1173e9e4e135c68e150704f01186ab5e763acd` |

A seleção é registrada **exclusivamente** em `decision.option = PREBUILT_PATH`.
**Não** se usa `prebuilt_path_authorized=true`: a flag de autorização do prebuilt
permanece `false`, como todas as demais flags operacionais.

## 3. Justificativa (registrada)

O WARP é atualmente o único caminho técnico identificado para preparar o
executável legalmente possuído pelo responsável pelo FaithRO, mas seu núcleo é
distribuído apenas como binário prebuilt, sem fonte C++/Qt correspondente, receita
de build, hash externo publicado ou reprodutibilidade demonstrada.

`PREBUILT_PATH` é selecionado **somente** para permitir o planejamento de uma
auditoria binária offline, gradual, reproduzível e sujeita a autorizações humanas
separadas.

Esta seleção **não** significa confiança no binário, aprovação de seu uso ou
autorização para materializá-lo ou executá-lo. O caminho poderá ser interrompido e
substituído por `STOP_PATH` a qualquer momento se a análise futura identificar
risco incompatível com as políticas de segurança, manutenção ou propriedade
intelectual do FaithRO.

## 4. Condições obrigatórias da decisão

1. Autoriza somente o **registro documental** de `PREBUILT_PATH` e a preparação do
   **plano** da futura auditoria binária offline.
2. O binário prebuilt **não** pode ser baixado, materializado, extraído, executado
   ou enviado a qualquer serviço nesta etapa.
3. Uma futura materialização dependerá de **autorização humana específica** e
   deverá ocorrer somente a partir do blob do commit oficial fixado
   `9b1173e9e4e135c68e150704f01186ab5e763acd`.
4. Antes de qualquer execução futura, deverão existir **gates separados** para:
   cálculo local de SHA-256; verificação Authenticode; inventário PE; análise de
   imports, recursos e dependências; análise estática offline; verificação por
   mecanismos locais de segurança; preparação de sandbox descartável; bloqueio de
   rede; baseline de processos, arquivos e registro; plano de descarte e rollback.
5. A autorização para **materializar** o prebuilt **não** autorizará sua execução.
6. A autorização para **executar** o prebuilt sem cliente **não** autorizará
   fornecer o `Ragexe`.
7. O `Ragexe` original deverá permanecer **preservado fora** do diretório
   operacional. Qualquer teste futuro utilizará somente cópia **isolada e
   descartável**.
8. **Nenhum** arquivo do cliente, executável modificado, GRF, DLL, `.asi` ou asset
   proprietário poderá ser versionado, publicado, enviado à VPS ou distribuído.
9. Os patches `CustomDLL`, `DisableProtect`, `DisableEncr` e `EnableProxy`
   permanecem **bloqueados** e exigirão decisão humana individual.
10. Os patches `DataFolderFirst` e `CallKoreaClientInfo` permanecem **somente
    candidatos revisados estaticamente**: não aprovados, não aplicados e não
    suficientes para o primeiro acesso.
11. **Não** alterar `PACKETVER`, **não** recompilar o rAthena e **não** adaptar o
    servidor por tentativa. A compatibilidade atual permanece `PROVÁVEL` até teste
    controlado.
12. **Não** acessar a VPS, **não** criar conta de teste e **não** alterar firewall,
    MariaDB ou serviços nesta etapa.
13. **Não** executar o Beam Patcher. O Beam pertence ao fluxo de atualização de
    conteúdo próprio/licenciado e não resolve a preparação do executável.
14. Qualquer comportamento inesperado, alerta de segurança, dependência não
    explicada, tentativa de rede ou inconsistência de proveniência deve
    **interromper automaticamente** o fluxo e retornar a decisão para revisão
    humana.
15. `STOP_PATH` permanece disponível a qualquer momento e **não** deve ser tratado
    como falha do projeto.

## 5. Autorizações e proibições desta etapa

Verdadeiras **apenas** as três flags de decisão; **todas** as operacionais `false`:

```text
HUMAN_DECISION_REQUIRED=true    HUMAN_DECISION_RECEIVED=true    OPTION_SELECTED=true

SOURCE_PATH_AUTHORIZED=false    PREBUILT_PATH_AUTHORIZED=false  ALTERNATIVE_TOOL_AUTHORIZED=false
STOP_PATH_SELECTED=false        MATERIALIZATION_AUTHORIZED=false BUILD_AUTHORIZED=false
EXECUTION_AUTHORIZED=false      CLIENT_PROVISION_AUTHORIZED=false CLIENT_MODIFICATION_AUTHORIZED=false
FIRST_LOGIN_AUTHORIZED=false
```

`SOURCE_PATH_AUTHORIZED`, `ALTERNATIVE_TOOL_AUTHORIZED` e `STOP_PATH_SELECTED`
permanecem `false`: a seleção de `PREBUILT_PATH` não seleciona nem autoriza os
demais caminhos.

## 6. Registro real e template preservado

- **Registro real** (preenchido, fiel à decisão):
  [`client/warp-audit/decisions/core-path-decision-record-2026-07-31.json`](../client/warp-audit/decisions/core-path-decision-record-2026-07-31.json).
- **Template** — permanece **em branco**, intocado:
  [`client/warp-audit/core-path-decision-record.example.json`](../client/warp-audit/core-path-decision-record.example.json)
  (`status=PENDING`, campos `null`, flags `false`).

O registro real é um **artefato separado** do template. O merge do PR **não**
preenche o template nem seleciona opção; o registro **não** concede autorização a
si mesmo.

## 7. Schema e validação

- **Schema do registro real:**
  [`client/warp-audit/schemas/core-path-decision-record-real.schema.json`](../client/warp-audit/schemas/core-path-decision-record-real.schema.json)
  (draft-07, `additionalProperties:false` — rejeita propriedades extras).
- **Validador:** [`scripts/validate-warp-audit.py`](../scripts/validate-warp-audit.py)
  (apenas biblioteca padrão; sem rede, sem subprocessos, sem escrita). Comprova
  que:

  - o template `.example.json` continua vazio;
  - o registro real contém a decisão;
  - a opção é `PREBUILT_PATH`;
  - nenhuma autorização operacional está `true`;
  - identidade e autoridade não são placeholders;
  - a data é válida;
  - justificativa e condições não estão vazias;
  - pacote e registro usam o mesmo commit fixado;
  - propriedades extras são rejeitadas;
  - entrada inválida **não** produz traceback (código de saída ≠ 0).

Testes negativos cobrem: cada autorização proibida em `true`, opção inválida,
placeholder, IP, senha, token, path traversal, propriedade extra e JSON inválido.

## 8. Próxima etapa permitida

**Somente planejamento:**
`ETAPA 2P-E-B-PREBUILT — planejamento da auditoria binária offline`. Essa etapa
**não** poderá materializar, baixar, extrair nem executar o binário; cada gate
técnico (materialização, SHA-256, Authenticode, PE, imports, análise estática,
antivírus, sandbox, rede bloqueada, baseline, descarte) exigirá **decisão humana
separada**.

## 9. Riscos e mitigação

O principal risco é o **registro da seleção ser interpretado como autorização**
para utilizar o prebuilt. Mitigação: flags operacionais obrigatoriamente `false`;
terminologia explícita ("selecionado apenas para planejamento"); schema com
`additionalProperties:false`; validador com testes negativos; PR **draft**;
ausência de qualquer materialização; **gates humanos separados**.

## 10. Rollback

**Antes do merge:** corrigir ou fechar o PR; **não** usar `--force`; **não**
reescrever `dev`.

**Após eventual integração documental:** criar branch a partir de `dev`, reverter o
squash, validar e abrir PR de reversão.

O rollback do registro Git **não** apaga a decisão humana histórica. Qualquer
alteração posterior deve ser feita por um **novo** registro de decisão,
preservando a trilha de auditoria.

## 11. Estado de verificação

- **Fato:** decisão humana recebida (decisor, função/autoridade, canal, data);
  opção `PREBUILT_PATH` registrada em `decision.option`; template preservado em
  branco; todas as flags operacionais `false`.
- **Inferência/decisão:** `PREBUILT_PATH` submetido **apenas** ao planejamento da
  auditoria binária offline; nenhuma autorização operacional concedida.
- **Pendência:** planejamento da auditoria (2P-E-B-PREBUILT) e, depois, gates
  humanos individuais para qualquer materialização/execução.
- **Nota:** decisão técnica e de conformidade do projeto, **não** parecer jurídico.
