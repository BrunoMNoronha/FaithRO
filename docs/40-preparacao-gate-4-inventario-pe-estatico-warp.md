# Preparação do GATE 4 — inventário PE estático offline do WARP

> **Estado atual:** `GATE 4 — FERRAMENTA PREPARADA E TESTADA (SOMENTE FIXTURES
> SINTÉTICAS); EXECUÇÃO NÃO AUTORIZADA` (ETAPA 2P-E-C4-PREP).
> **Data:** 2026-08-04.
> **Escopo:** **exclusivamente preparatório**. Cria, revisa, testa e documenta a
> ferramenta que **poderá** ser usada no futuro GATE 4. **Não** executa o GATE 4,
> **não** materializa nem inspeciona o `WARP.exe`, **não** acessa o blob upstream,
> **não** cria decisão/evidência/saída real do GATE 4 e **não** autoriza execução,
> análise dinâmica, GATE 5 ou uso no cliente/distribuição.
> Continua [39](39-resultado-gate-3-identidade-assinatura-warp.md); observa
> [33](33-plano-auditoria-binaria-offline-warp.md) e
> [16](16-politica-distribuicao-cliente.md).

## 1. Objetivo

Preparar, de forma **auditável e separada da execução**, a ferramenta do GATE 4 —
inventário PE **estático offline** — para evitar a repetição do problema do GATE 3,
no qual a medição inicial foi produzida por um parser **não versionado** (achado D3
da revisão 2P-E-C3-R1). Aqui, o analisador nasce **versionado, revisável e testado
apenas com fixtures sintéticas**, antes de qualquer medição real.

## 2. Contexto e cadeia dos GATEs 2 e 3

- **GATE 2 (2P-E-C2-A):** materialização única e integridade local do blob fixado
  (`c853da42…`, `1137152` bytes, SHA-256 `345f3464…`); binário removido, não
  versionado. `COMPLETED_PASS`.
- **GATE 3 (2P-E-C3 + R1…R4.1 + REPEAT):** identidade e assinatura estática offline.
  A repetição corretiva (`AUTHORIZE_CORRECTIVE_REPEAT_GATE_3`) concluiu
  `COMPLETED_PASS` com o **inspetor de identidade versionado**
  [`scripts/inspect-warp-pe-identity.py`](../scripts/inspect-warp-pe-identity.py):
  `PE32`, 5 seções, `SizeOfOptionalHeader=224`, magic `0x010b`, Certificate Table
  `present=false` (assinatura ausente ≠ malware). A evidência histórica invalidada é
  **preservada**.

O GATE 3 estabeleceu a **identidade** e o **estado da assinatura**. O GATE 4 é o passo
seguinte: **inventário PE estático** (seções, imports/exports, recursos, etc.).

## 3. Decisão estratégica de avançar

A decisão estratégica do mantenedor é **prosseguir no caminho do GATE 4**. Esta etapa
materializa **apenas a preparação**: a autorização operacional real do GATE 4 ocorrerá
em **PR separado**, depois desta preparação integrada, referenciando o **squash
integrado** e os **Git blob OIDs exatos** do analisador e dos testes revisados.

## 4. Ainda não existe autorização operacional real

Esta etapa **não** concede autorização operacional. O merge desta preparação **não**
autoriza executar o GATE 4. Não há decisão, evidência nem saída real do GATE 4. As
confirmações negativas estão no §14 e são verificadas pelo validador
([`scripts/validate-warp-audit.py`](../scripts/validate-warp-audit.py), etapa
`gate-04-prep`), que exige `gate_4_real_decision_count=0`,
`gate_4_real_evidence_count=0`, `gate_4_real_output_count=0`, `gate_4_authorized=false`,
`gate_4_execution_authorized=false` e `gate_5_authorized=false`.

## 5. Contrato do GATE 4 (escopo do inventário estático)

O GATE 4 limita-se a **inventário PE estático offline**, incluindo, quando
estruturalmente presentes: cabeçalhos e seções; características e permissões das seções;
tamanhos raw e virtual; **entropia** por seção e total; **overlay**; **imports** (por
nome e ordinal) e **exports**; **recursos** e **manifest** (incluindo o **nível de
execução solicitado**: `asInvoker`/`highestAvailable`/`requireAdministrator`); **TLS
callbacks**; **relocations**; **debug directory**; **Certificate Table apenas como
estrutura**; dependências declaradas; **indicadores estruturais de empacotamento**;
strings relevantes; **URLs, domínios e caminhos** embutidos; e **APIs** potencialmente
relacionadas a rede, processos, serviços, registro, memória remota, injeção ou
persistência aparente.

O contrato afirma **explicitamente**:

- uma API importada **não** prova que a funcionalidade é utilizada;
- uma string **não** prova comportamento;
- entropia alta isoladamente **não** prova empacotamento ou malware;
- ausência de indicador **não** prova segurança;
- achados estáticos exigem **interpretação contextual**;
- **nenhuma** conclusão depende de uma única métrica;
- o GATE 4 **não** executa, carrega, emula ou descompacta dinamicamente o PE;
- o GATE 4 **não** autoriza o GATE 5;
- o GATE 4 **não** autoriza uso no cliente ou distribuição.

## 6. Arquivos afetados

| Arquivo | Tipo | Motivo |
| --- | --- | --- |
| [`scripts/inspect-warp-pe-static.py`](../scripts/inspect-warp-pe-static.py) | novo | analisador PE estático offline (stdlib, bounds checking, fail-closed) |
| [`scripts/test-warp-pe-static.py`](../scripts/test-warp-pe-static.py) | novo | testes do analisador com **fixtures sintéticas** removidas ao final |
| `client/warp-audit/schemas/binary-audit-gate-04-static-inventory-output.schema.json` | novo | schema fechado da **saída** determinística do analisador |
| `client/warp-audit/schemas/binary-audit-gate-04-decision-record-real.schema.json` | novo | schema da **futura** decisão humana `AUTHORIZE_GATE_4_EXECUTION` |
| `client/warp-audit/schemas/binary-audit-gate-04-{pass,fail,stopped}-evidence.schema.json` | novos | schemas da **futura** evidência PASS/FAIL/STOPPED |
| [`scripts/validate-warp-audit.py`](../scripts/validate-warp-audit.py) | edição | validação `gate-04-prep`: convenção, máquina de estados atômica, flags negativas |
| [`scripts/test-warp-audit-gate-04.py`](../scripts/test-warp-audit-gate-04.py) | novo | testes positivos/negativos do validador do GATE 4 |
| [`scripts/test-warp-audit-eol.py`](../scripts/test-warp-audit-eol.py) | edição | atributos LF + bytes dos novos scripts (sem exigir saída inexistente) |
| [`.gitattributes`](../.gitattributes) | edição | 3 padrões mínimos `text eol=lf` para os novos byte-sensíveis |
| [`.github/workflows/validate-warp-audit.yml`](../.github/workflows/validate-warp-audit.yml) | edição | novos passos e regressão `core.autocrlf=true` |
| `docs/40-*.md`, `docs/README.md`, `client/warp-audit/README.md` | novo/edição | este registro e índices |

Nada em `conf/import`, `db/import`, `npc/custom`, `src/`, core, VPS, MariaDB, firewall,
serviços, cliente, `Ragexe` ou progressão foi tocado. **Nenhum binário adicionado.** Os
três artefatos byte-fixados do GATE 3 (`scripts/inspect-warp-pe-identity.py`,
`scripts/test-warp-pe-identity.py` e a saída do parser do GATE 3) permanecem
**idênticos** em blob e worktree.

## 7. Arquitetura do analisador

[`scripts/inspect-warp-pe-static.py`](../scripts/inspect-warp-pe-static.py):

- **Somente biblioteca padrão** do Python; **sem** `pefile`/LIEF/YARA/antivírus; **sem**
  rede; **sem** `ctypes`/`LoadLibrary`/`ShellExecute`/Wine/VM; **sem** subprocesso sobre
  o binário; abre a entrada **somente em leitura binária** e **nunca** modifica o arquivo.
- **Bounds checking** antes de toda leitura derivada de offset/tamanho; **fail-closed**
  (`PEError`, exit ≠ 0) diante de estruturas truncadas, inconsistentes ou sobrepostas;
  mapeamento **RVA→offset** validado pela Section Table.
- É **deliberadamente separado** do inspetor de identidade do GATE 3 (sem código
  compartilhado importado), para **não** alterar os Git blob OIDs protegidos do GATE 3.
- **Não** copia lógica divergente do parser do GATE 3; reimplementa o parsing de forma
  dedicada ao inventário.

## 8. Modelo de saída

JSON **determinístico**: UTF-8 sem BOM, LF, `indent=2`, `sort_keys=True`, **exatamente
um** newline final, sem chaves duplicadas e sem dados após o newline. A saída **separa**:

- `structural_facts` — cabeçalhos, seções (permissões, tamanhos, entropia), overlay,
  imports, exports, recursos/manifest, TLS, relocations, debug, Certificate Table
  (estrutura), dependências declaradas;
- `heuristics` — indicadores **estruturais** de empacotamento (W+X, alta entropia,
  seção executável sem raw, overlay), cada um com nota de que **não** é veredito;
- `import_classification` — tabela **fechada** de APIs por categoria;
- `string_indicators` — indicadores textuais **sanitizados e limitados**;
- `limitations` — as ressalvas do contrato (§5).

A saída **nunca** emite bytes brutos de seções, conteúdo de `bCertificate`, base64,
hexdumps, dump integral de recursos/strings, segredos, caminhos pessoais nem nome de
máquina/usuário. Cada lista tem **limite** de tamanho/quantidade e registra
**truncamento** explícito. O schema fechado é
[`binary-audit-gate-04-static-inventory-output.schema.json`](../client/warp-audit/schemas/binary-audit-gate-04-static-inventory-output.schema.json)
(`additionalProperties=false` em todos os níveis).

## 9. Sanitização

A coleta de strings é **conservadora** e **classificada** (nunca uma lista completa e
irrestrita): possíveis URLs, possíveis domínios, caminhos embutidos, mutex/serviço/
registro **por regra explícita** e indicadores textuais de depuração/empacotamento.
Regras: **limite** de ocorrências por categoria e de caracteres por item; **dedup** e
**ordenação** determinísticos; **rejeição/redação** de caminhos pessoais (drive/home),
**IPs literais**, tokens, chaves e credenciais; proibição de conteúdo arbitrário sem
classificação; e registro de que os valores são **indicadores textuais**, não
comportamento confirmado (`redacted_count` contabiliza o que foi descartado).

A **classificação de imports** é uma tabela **fechada** no código, *case-insensitive*
determinística, que preserva o nome importado sanitizado, **não** classifica DLL/API
desconhecida por suposição, **não** converte presença em veredito e é coberta por testes
positivos e negativos.

## 10. Fixtures e testes

- [`scripts/test-warp-pe-static.py`](../scripts/test-warp-pe-static.py) usa
  **exclusivamente fixtures sintéticas** criadas durante os testes e **removidas ao
  final, inclusive após falha**. Cobre: PE32/PE32+; uma e várias seções; W+X e nomes
  atípicos; entropia conhecida (0.0, 1.0, 8.0); overlay ausente/presente; imports por
  nome e ordinal; exports; manifest `asInvoker`/`highestAvailable`/`requireAdministrator`;
  TLS/relocations/debug ausentes e presentes; Certificate Table ausente e estruturalmente
  presente; classificação (rede/serviço/registro/memória remota/desconhecido);
  strings ASCII e UTF-16LE; URL e domínio; caminho pessoal redigido; token/segredo
  ausente da saída; limites/truncamento; offsets fora do arquivo; overflow/soma fora de
  bounds; diretórios sobrepostos; RVA não mapeável; Section Table truncada; Optional
  Header inconsistente; número excessivo de seções; JSON determinístico sem BOM/CR,
  newline único, sem base64/bytes brutos; e conformidade com o **schema fechado**.
- [`scripts/test-warp-audit-gate-04.py`](../scripts/test-warp-audit-gate-04.py) exercita
  o validador com decisão/evidência **sintéticas** válidas e mutações inválidas
  (gate_5 autorizado, gate_4_execution ausente, OID divergente, PASS sem saída
  determinística, STOPPED com saída, FAIL em estado impossível, saída com BOM/CRLF/base64).
- **Nenhum** teste acessa o WARP real, cliente, `Ragexe`, rede ou VPS.

## 11. Limitações

O analisador ainda **não** foi executado sobre o `WARP.exe` (execução é o GATE 4, não
autorizado). A eficácia real dependerá da execução futura, autorizada em PR separado.
Heurísticas estruturais **não** são veredito; a interpretação é contextual e humana.
O mini-validador de schema suporta um subconjunto de JSON Schema (sem `oneOf`/`if-then-
else`); as relações condicionais (PASS/FAIL/STOPPED) são aplicadas em Python.

## 12. Riscos

R1 parser incorreto produzindo falso achado; R2 offsets/RVAs mal validados; R3 import
lido como comportamento; R4 string lida como comportamento; R5 entropia tratada como
veredito; R6 vazamento de conteúdo binário; R7 vazamento de caminhos/segredos; R8 lista
de strings excessiva; R9 saída não determinística; R10 CRLF alterando OIDs; R11
alteração acidental dos artefatos do GATE 3; R12 criação prematura de decisão/evidência
real; R13 autorização transitiva do GATE 5; R14 ferramenta carregando/executando o PE;
R15 arquivo temporário não removido; R16 binário entrando no Git; R17 inspeção real
durante testes. **Mitigações:** bounds checking + fail-closed + fixtures; separação de
fatos/heurísticas/limitações; sanitização + `redacted_count`; limites e truncamento;
JSON determinístico (indent/sort/LF/newline único, sem base64); `.gitattributes eol=lf`
+ teste de EOL + regressão `autocrlf=true`; analisador **separado** do GATE 3 (OIDs
preservados); validador `gate-04-prep` reprova prematuridade/órfãos/estado impossível e
exige `gate_5_authorized=false`; asserções `executed/loaded/emulated/unpacked=false` e
`run_on_warp_exe`; fixtures removidas inclusive após falha; nenhum binário versionado.

## 13. Rollback

Antes do merge: corrigir por commits adicionais; manter o PR **draft**; fechar o PR se a
arquitetura for inválida; preservar a branch para auditoria; **sem** force push; **sem**
reset destrutivo; **sem** alterar outros worktrees. Após eventual merge: criar branch de
`dev`, `git revert` do squash, validar todas as suítes, abrir PR de reversão, **sem**
reescrever histórico. O rollback desta preparação **não** altera os fatos históricos dos
GATEs 2 e 3 e **não** autoriza execução, materialização ou distribuição.

## 14. Confirmações negativas

```text
gate_4_preparation_completed=true   gate_4_authorized=false
gate_4_execution_authorized=false   gate_5_authorized=false
gate_4_real_decision_count=0        gate_4_real_evidence_count=0
gate_4_real_output_count=0
warp_exe_materialized=false         warp_exe_inspected=false
upstream_blob_accessed=false        binary_versioned=false
dynamic_analysis_authorized=false   client_accessed=false
ragexe_accessed=false               vps_accessed=false
gate_3_byte_pinned_artifacts_unchanged=true
```

## 15. Próxima decisão humana (proposta)

Após a **revisão independente e eventual integração** desta preparação, a próxima
decisão humana possível — em **PR separado** — será, como **proposta** (nomes ainda a
serem confirmados como canônicos; **nenhuma** opção selecionada):

```text
AUTHORIZE_GATE_4_EXECUTION
STOP_PATH
```

```text
GATE 4 NÃO AUTORIZADO OPERACIONALMENTE
```

A integração desta preparação **não** seleciona nenhuma dessas opções nem autoriza a
execução do GATE 4, análise dinâmica, GATE 5, uso no cliente ou distribuição.

## Estado de verificação

- **Fato:** ferramenta do GATE 4 versionada e testada **somente com fixtures
  sintéticas**; schemas fechados; validador estendido; artefatos byte-fixados do GATE 3
  **inalterados**.
- **Inferência/decisão:** avançar no caminho do GATE 4 **apenas** na camada de
  preparação; execução exige nova decisão humana em PR separado.
- **Pendência:** decisão humana `AUTHORIZE_GATE_4_EXECUTION` / `STOP_PATH`.
- **Nota:** decisão técnica e de conformidade do projeto, **não** parecer jurídico.
