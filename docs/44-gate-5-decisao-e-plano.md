# Preparação da decisão humana do GATE 5 — definição e plano de controle

> **Estado atual:** `GATE 5 — PREPARAÇÃO DA DECISÃO HUMANA; NÃO AUTORIZADO`
> (ETAPA 2P-E-C5-PREP).
> **Data:** 2026-08-05.
> **Escopo:** **exclusivamente documental e preparatório**. Inspeciona o estado
> integrado do GATE 4, identifica a definição canônica do GATE 5, analisa lacunas e
> riscos e elabora um plano de controle e uma matriz de decisão humana. **Não**
> autoriza, **não** inicia e **não** executa o GATE 5; **não** repete o GATE 4;
> **não** altera a saída/evidência do GATE 4; **não** materializa nem executa
> qualquer PE; **não** prepara o cliente; **não** acessa a VPS.
> Continua [43](43-resultado-gate-4-inventario-pe-estatico-warp.md); observa
> [33](33-plano-auditoria-binaria-offline-warp.md),
> [40](40-preparacao-gate-4-inventario-pe-estatico-warp.md) e
> [16](16-politica-distribuicao-cliente.md).

```text
decision_status=PENDING_HUMAN_DECISION
gate_5_authorized=false
execution_authorized=false
client_preparation_authorized=false
```

## Classificação da próxima etapa

**D2 — o GATE 5 está nomeado e definido em alto nível na cadeia canônica, mas sua
definição pronta para execução é incompleta.** O gate existe como uma fatia do plano
de 17 gates (doc 33 §11 e `binary-audit-plan.example.json`, `gate_id=5`), com
objetivo, ações planejadas, ações que não autoriza, `must_remain_false` e exigência
de decisão humana. Porém a preparação operacional que a cadeia exigiu **antes de cada
execução** (ferramenta versionada, testes com fixtures, schemas fechados de
decisão/evidência/saída — como o GATE 4 recebeu em 2P-E-C4-PREP, doc 40) **ainda não
existe** para o GATE 5.

Portanto, a decisão humana desta etapa é **sobre a definição e o plano de controle**,
não sobre execução. Recomendação padrão desta etapa:

```text
NÃO AUTORIZAR EXECUÇÃO DO GATE 5 NESTE PR.
APROVAR, NO MÁXIMO, A DEFINIÇÃO DOCUMENTAL E O PLANO DE CONTROLE.
```

## 1. Objetivo

O GATE 5 — **verificações locais de segurança** — pretende, conforme a cadeia
canônica (doc 33 §11; plano `gate_id=5`), **planejar e, futuramente, aplicar apenas
mecanismos locais e autorizados** de verificação de segurança sobre o único blob WARP
fixado (por exemplo, antivírus local, Defender ou equivalente disponível, ferramentas
estáticas locais e regras YARA locais aprovadas), **sem** enviar o binário a qualquer
serviço externo automaticamente. Qualquer análise de reputação externa exige um gate
humano separado.

Este documento **não** executa o GATE 5. Ele prepara a decisão humana que poderá, no
máximo, **aprovar a definição e o plano de controle**. Onde este documento vai além do
que a cadeia já fixa, o conteúdo é marcado explicitamente como **proposta**.

## 2. Estado anterior (GATE 4)

- **GATE 4 = `COMPLETED_PASS`** (doc 43, ETAPA 2P-E-C4-EXEC), integrado por squash
  `03348d7` na branch `dev` (PR #57, `MERGED`).
- Resultado **procedural**: o inventário PE estático foi executado conforme o contrato
  e a saída é válida e sanitizada. **Não** constitui aprovação de segurança do binário.
- Output imutável:
  [`binary-audit-gate-04-static-inventory-output-2026-08-05.json`](../client/warp-audit/evidence/binary-audit-gate-04-static-inventory-output-2026-08-05.json).
- **SHA-256 do output:**
  `84c3c49a770b475fdf25c43467498e014b2f8950ef172384bb8ea48bbe17f584`
  (preso na evidência PASS; UTF-8/LF, sem BOM/CR).
- Identidade reconfirmada igual aos GATES 2/3: blob `c853da42…`, 1137152 bytes,
  SHA-256 `345f3464…`. PE32 x86, 5 seções (nenhuma W+X), não assinado (Certificate
  Table ausente ≠ malware), manifest `asInvoker`; nenhum import classificado como rede
  ou injeção. Estes são **achados**, não veredito.
- `gate_5_authorized=false`.
- **Proibido repetir o GATE 4** sem nova decisão humana; proibido reexecutar o
  analisador sobre o blob; proibido reintroduzir o binário no Git.

## 3. Escopo proposto

**Incluído (proposta a decidir):**

- Definição normativa do GATE 5 (objetivo, entradas, ações permitidas/proibidas,
  ambiente, critérios, abort, evidências) a partir do que a cadeia já fixa, com as
  lacunas marcadas.
- Plano de controle (ambiente isolado, embargo de rede, descarte) para uma futura
  execução, **sem criá-lo**.
- Matriz de decisão humana (§16).

**Excluído (não faz parte desta etapa):**

- Execução, materialização, hashing ou inspeção do WARP.exe.
- Criação de ferramenta, schemas de evidência, sandbox ou ambiente.
- Repetição do GATE 4; alteração da saída/evidência do GATE 4.
- Preparação/publicação do cliente; acesso à VPS.

**Dependências:**

- Integração prévia (já ocorrida) do GATE 4 (`03348d7`).
- Se a Opção B for escolhida: uma etapa **2P-E-C5-PREP-TOOL** (proposta) para criar,
  de forma versionada e testada só com fixtures, os artefatos do GATE 5, análoga ao
  2P-E-C4-PREP.

**Itens que exigem decisão humana adicional:**

- A lista fechada de ferramentas locais e regras YARA aprovadas.
- Se o GATE 5 exigirá materialização temporária do blob (ver §6 e as lacunas em §10).
- Qualquer análise de reputação externa (gate humano separado; permanece proibida).

## 4. Arquivos potencialmente afetados numa futura execução

Apenas caminhos/categorias permitidos. **Fora de escopo:** `src/`, `pre-re/`,
`conf/battle/` e todo o core do rAthena — o GATE 5 é sobre o binário WARP, não sobre
o servidor.

Categorias permitidas numa futura execução (proposta):

- `client/warp-audit/decisions/` — registro real da futura decisão do GATE 5.
- `client/warp-audit/evidence/` — futura evidência do GATE 5 (resultado das
  verificações locais + lista de ferramentas), sanitizada.
- `client/warp-audit/schemas/` — schemas fechados do GATE 5 (se a preparação da
  ferramenta for aprovada).
- `scripts/` — eventuais scripts **isolados de validação** (não executam o PE).
- `docs/` — documento de resultado.
- `docs/README.md`, `client/warp-audit/README.md` — índices.

Nenhum binário, GRF, executável ou asset proprietário é versionado.

## 5. Ambiente (descrição; não criado nesta etapa)

Para uma **futura** execução (proposta, alinhada aos princípios do doc 33 §6/§10):

- **Isolamento:** host do operador em modo controlado; sem dados pessoais; sem
  credenciais reais; sem clipboard/pastas compartilhadas ou mounts sensíveis.
- **Rede:** bloqueada ou estritamente controlada; **nenhum** upload do binário a
  serviço externo, sandbox pública, nuvem, LLM, repositório, issue ou chat
  (`external_reputation_upload_authorized=false`). As verificações são **locais**.
- **Snapshot/descarte:** cópia de trabalho descartável; binário materializado
  temporariamente **fora do repositório** e removido ao fim (como no GATE 4);
  diretório temporário removido; sem lixeira.
- **Logs e limites:** logging da invocação e dos códigos de saída; janela de tempo
  limitada; embargo de rede documentado do início ao fim.
- **Proibições:** proibida conexão com a VPS de produção; proibido uso do cliente
  real até autorização específica.

Detalhes não sustentados pela cadeia estão marcados como proposta e **não** substituem
uma futura especificação formal (ver lacuna em §10).

## 6. Entradas permitidas (numa futura execução)

- O **único blob WARP fixado** `c853da42d18dfe090b4e941b435d989311faf3dc`
  (1137152 bytes), obtido **apenas** do GitHub oficial por object ID, como nos
  GATES 2/3/4.
- A lista fechada de **ferramentas locais aprovadas** (a definir por decisão humana).

**Nenhum** artefato é incorporado nesta etapa. Se a materialização for necessária para
verificações locais, seu modo e limites precisam de decisão humana explícita (ver
§10 — o plano marca `does_not_materialize_binary=true` no nível do plano).

## 7. Ações permitidas (lista fechada, numa futura execução)

Somente após decisão humana explícita e específica. Toda ação **não listada** é
proibida.

1. Materializar temporariamente o blob fixado por object ID (se e somente se a decisão
   humana o autorizar), fora do repositório.
2. Reconfirmar a identidade (tamanho, Git blob OID, SHA-256) antes de qualquer
   verificação.
3. Executar **apenas** ferramentas de segurança **locais e autorizadas** da lista
   fechada.
4. Registrar resultados sanitizados e a lista de ferramentas usadas.
5. Remover o binário e o diretório temporário e confirmar a limpeza.
6. Registrar evidência e decisão em PR separado.

## 8. Ações proibidas

- Distribuir ou versionar o WARP, GRF, executáveis ou assets proprietários.
- Executar, carregar, emular, desassemblar ou depurar o PE (o GATE 5 é local/estático;
  execução dinâmica é GATE 8/9, sob decisão humana própria).
- Enviar o binário a serviço externo, sandbox pública, nuvem, LLM, repositório, issue,
  chat ou storage externo (`external_reputation_upload_authorized=false`).
- Acessar a produção/VPS; usar o alias `ssh faithro-vps`.
- Acessar dados de jogadores ou usar credenciais reais.
- Comunicação externa não autorizada; persistência fora do ambiente.
- Alterar a saída ou a evidência do GATE 4.
- Reexecutar/repetir o GATE 4.
- Preparar ou publicar o cliente.

## 9. Critérios de entrada (pré-condições para uma futura autorização)

- GATE 4 integrado e íntegro; SHA-256 do output confere
  (`84c3c49a…`); `gate_5_authorized=false` na cadeia.
- Definição do GATE 5 aprovada (esta etapa) ou refinada, com lacunas de §10 resolvidas.
- Lista fechada de ferramentas locais e regras aprovadas.
- Ambiente isolado especificado; embargo de rede definido; política de descarte
  definida.
- Registro de decisão humana real (PR separado), sem autorização transitiva.

## 10. Critérios de sucesso e lacunas

**Sucesso procedural (proposta):** as verificações locais aprovadas foram executadas
conforme o contrato; a saída é válida e sanitizada; a identidade foi reconfirmada; o
binário e o diretório temporário foram removidos; o embargo de rede foi respeitado.

**Observações técnicas:** os resultados das ferramentas locais são **achados** que
exigem interpretação humana e contextual.

**Limitações:** um resultado local (positivo ou negativo) **não** prova que o binário
é seguro, benigno ou malicioso; ausência de detecção **não** prova segurança;
verificação local **não** substitui análise dinâmica (GATE 8+) nem confere aprovação
de uso no cliente. Nenhuma conclusão depende de uma única métrica.

**Conclusões que não podem ser feitas:** o GATE 5, por si, **não** aprova o binário,
**não** autoriza o GATE 6+ e **não** autoriza uso no cliente ou distribuição.

**Lacunas na cadeia canônica atual** (a resolver antes de qualquer execução):

| Elemento | Situação | Observação |
| --- | --- | --- |
| Nome do GATE 5 | definido | doc 33 §11; plano `gate_id=5` = "Verificações locais de segurança". |
| Objetivo | definido | plano `gate_id=5.objective`. |
| Ações permitidas | definido | plano `gate_id=5.planned_actions`. |
| Ações proibidas | definido | plano `gate_id=5.does_not_authorize` + §16 do doc 33. |
| Entradas (materialização) | ambíguo | `does_not_materialize_binary=true` no nível do plano; a execução real precisaria do blob temporário. **Modo/limites NÃO DEFINIDOS NA CADEIA CANÔNICA ATUAL.** |
| Lista de ferramentas locais | ambíguo | categorias citadas; lista fechada/versões/regras **NÃO DEFINIDAS NA CADEIA CANÔNICA ATUAL**. |
| Ambiente exigido | ambíguo | princípios gerais (doc 33 §6/§10); detalhe por gate **NÃO DEFINIDO NA CADEIA CANÔNICA ATUAL**. |
| Critério de aprovação | ambíguo | exit options `GATE_PASSED/GATE_FAILED/STOP_PATH` + doc 33 §15; critério específico do GATE 5 **NÃO DEFINIDO NA CADEIA CANÔNICA ATUAL**. |
| Abort conditions | definido (geral) | doc 33 §16 (21 critérios) aplicáveis; ver §11. |
| Rollback | definido (geral) | doc 33 §26; ver §15. |
| Decisor humano | definido | `BrunoMNoronha` (convenção dos registros reais dos GATES 0–4). |
| Artefatos de preparação (ferramenta/schemas/evidência) | ausente | **NÃO DEFINIDO NA CADEIA CANÔNICA ATUAL** (o GATE 4 os teve na 2P-E-C4-PREP). |

## 11. Abort conditions (numa futura execução)

Interrompem imediatamente e retornam à decisão humana (doc 33 §16, aplicáveis):

- hash/identidade divergente do blob fixado;
- artefato inesperado ou saída fora do schema;
- qualquer tentativa de rede não prevista (upload/reputação/DNS/VPS);
- persistência ou alteração fora do diretório temporário autorizado;
- acesso a credenciais ou dados reais;
- falha de isolamento ou do embargo de rede;
- falha de logging;
- escopo divergente do plano;
- qualquer comportamento não coberto pelo plano.

## 12. Evidências esperadas (numa futura execução)

- Registro de decisão humana real do GATE 5 (PR separado).
- Evidência com: identificador, data, operador, ambiente, ferramentas e versões,
  reconfirmação de identidade (tamanho/OID/SHA-256), resultados sanitizados das
  verificações locais, lista de ferramentas usadas, códigos de saída, achados,
  limitações, riscos, confirmação de limpeza e embargo de rede.
- Se produzir saída determinística, seu SHA-256 preso na evidência (UTF-8/LF).

## 13. Riscos

- **R1** Confundir resultado procedural do GATE 4 (`COMPLETED_PASS`) com aprovação de
  segurança.
- **R2** Interpretar este pacote (ou seu merge) como autorização do GATE 5.
- **R3** Falsos positivos/negativos de ferramentas locais tratados como veredito.
- **R4** Comportamento dependente de runtime não observável estaticamente.
- **R5** Risco de rede (upload/reputação inadvertidos).
- **R6** Persistência ou contaminação do ambiente.
- **R7** Incorporar componente sem licença adequada / vazar artefato proprietário.
- **R8** Expansão de escopo (deslizar para análise dinâmica ou cliente).
- **R9** Documentação interpretar inferências/achados como fatos.

## 14. Mitigações

- **R1/R2** Linguagem explícita; flags `false` (`gate_5_authorized`,
  `execution_authorized`, `client_preparation_authorized`); estado
  `PENDING_HUMAN_DECISION`; PR em draft; merge não autoriza.
- **R3/R4/R9** Achados exigem interpretação humana; nenhuma conclusão por métrica
  isolada; separar fato de inferência.
- **R5** Rede bloqueada/embargo em mais de uma camada; `external_reputation_upload_authorized=false`.
- **R6** Ambiente isolado e descartável; limpeza confirmada; sem persistência.
- **R7** WARP GPL-3.0 usado localmente, **não** versionado; assets proprietários
  proibidos (doc 16).
- **R8** Lista fechada de ações; abort conditions; um registro por gate; sem
  autorização transitiva.

## 15. Rollback e descarte

- **Desta etapa (documental):** `reverter o commit ou fechar o PR draft sem merge`.
- **De uma futura execução:** interromper, limpar a área temporária, registrar
  `STOPPED`/`COMPLETED_FAIL` conforme o estado; corrigir/revogar por novo PR sem
  reescrever evidência histórica; nunca reexecutar o analisador sobre o blob, nunca
  autorizar segunda execução ou o GATE 5 por reversão, nunca reintroduzir o binário.
  Nunca usar `reset --hard`, `git clean -fd` ou force push.

## 16. Matriz de decisão humana

Nenhuma opção está pré-selecionada. A autorização de execução (Opção D) permanece
**desmarcada** e depende de decisão humana explícita posterior, em PR separado.

### Opção A — Não avançar
Manter o GATE 5 não autorizado; encerrar o caminho aqui (ou por `STOP_PATH`).

### Opção B — Aprovar apenas a definição e o plano
Permitir refinamento documental e a preparação de controles/ferramenta (etapa PREP
análoga ao 2P-E-C4-PREP), **sem** materialização ou execução.

### Opção C — Solicitar correções
Retornar este pacote para ajustes.

### Opção D — Autorizar futura execução limitada
**Permanece desmarcada.** Depende de decisão humana explícita posterior, registrada em
PR separado ou mecanismo canônico equivalente, após resolver as lacunas de §10.

## 17. Estado da decisão

```text
decision_status=PENDING_HUMAN_DECISION
gate_5_authorized=false
execution_authorized=false
client_preparation_authorized=false
```

Registro estruturado correspondente:
[`binary-audit-gate-05-decision-package.example.json`](../client/warp-audit/binary-audit-gate-05-decision-package.example.json)
(convenção do pacote de decisão; `state=PENDING_HUMAN_DECISION`; nenhuma flag de
autorização em `true`).

## Estado de verificação

- **Fato:** GATE 4 integrado (`03348d7`, PR #57 `MERGED`); output SHA-256
  `84c3c49a…` recomputado e conferido; `gate_5_authorized=false` em toda a cadeia; o
  GATE 5 está nomeado no plano (doc 33 §11; `gate_id=5`).
- **Inferência/decisão:** classificação **D2**; a decisão humana desta etapa é sobre a
  definição e o plano de controle, não sobre execução.
- **Proposta:** ambiente, entradas, ações, critérios e evidências futuros marcados como
  proposta; lacunas de §10 pendentes.
- **Pendência:** decisão humana explícita (§16). Nenhuma execução autorizada.
- **Nota:** decisão técnica e de conformidade do projeto, **não** parecer jurídico nem
  atestado de segurança.
