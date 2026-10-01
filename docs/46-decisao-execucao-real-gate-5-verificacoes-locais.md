# Decisão: execução real condicionada do GATE 5 — verificações locais de segurança

> **Etapa:** 2P-E-C5-REAL-AUTH-DECISION
> **Predecessor:** 2P-E-C5-GATE-REVIEW (tooling revisado, 84/84 PASS)
> **Decisor:** BrunoMNoronha
> **Data da decisão:** 2026-08-28
> **Estado:** CONDITIONAL_APPROVAL_FOR_SEPARATE_EXECUTION

## 0. Princípio

**Tooling pronto ≠ decisão aprovada ≠ pré-condições satisfeitas ≠ execução
realizada ≠ cliente autorizado.**

O merge deste PR registra a decisão humana e o contrato fechado. Ele **não**
executa o GATE 5, **não** materializa o PE, **não** executa scanners reais,
**não** prepara o cliente e **não** promove nenhuma flag operacional que
habilitaria execução automática.

A execução real ocorrerá em **outra etapa, outro branch e outro PR**, após
revisão e integração desta decisão em `dev`.

## 1. Decisão humana

**Opção D selecionada condicionalmente:** autorizar uma futura execução real e
local do GATE 5, limitada a verificações de segurança com ferramentas locais,
desde que **todas** as pré-condições técnicas documentadas sejam satisfeitas no
início da etapa de execução.

A aprovação **não** autoriza:

- preparação de cliente;
- distribuição de artefatos;
- upload externo ou reputação externa;
- acesso à VPS;
- qualquer operação fora do GATE 5 local.

## 2. Semântica exata da Opção D (reconstruída)

Conforme doc 44 §16:

> **Opção D — Autorizar futura execução limitada**
> Permanece desmarcada. Depende de decisão humana explícita posterior, registrada
> em PR separado ou mecanismo canônico equivalente, após resolver as lacunas de
> §10.

Significado: uma execução real, local e limitada do GATE 5, operando
exclusivamente sobre o blob WARP fixado (`c853da42...`, 1137152 bytes), usando
apenas ferramentas da lista fechada, em ambiente isolado, sem rede, sem upload
externo, sem execução do PE, sem preparação de cliente.

Este documento é o "PR separado" referido. A decisão foi recebida e as lacunas
de §10 são fechadas abaixo.

## 3. Predecessor e cadeia de evidências

| Elemento | Valor |
|----------|-------|
| GATE 4 outcome | `COMPLETED_PASS` |
| GATE 4 squash integrado | `03348d7` (PR #57) |
| GATE 4 output SHA-256 | `84c3c49a770b475fdf25c43467498e014b2f8950ef172384bb8ea48bbe17f584` |
| GATE 4 output path | `client/warp-audit/evidence/binary-audit-gate-04-static-inventory-output-2026-08-05.json` |
| GATE 4 pass evidence path | `client/warp-audit/evidence/binary-audit-gate-04-pass-evidence-2026-08-05.json` |
| GATE 4 decision record path | `client/warp-audit/decisions/binary-audit-gate-04-decision-record-2026-08-05.json` |
| GATE 5 tooling squash | `80f6f7a` (PR #59) |
| GATE 5 tooling review | 84/84 PASS (2P-E-C5-GATE-REVIEW) |
| GATE 5 tool blob OID | `952df939d2ca2db656dd8c5ccd787916f5ea3ba0` |
| GATE 5 test blob OID | `0af398724a63c8aad3123c08f3b6f860de88c370` |

## 4. Fechamento das lacunas do doc 44 §10

### 4.1 Entradas — materialização (antes: ambíguo)

**Resolução:** a futura execução real poderá materializar temporariamente o blob
WARP fixado, seguindo exatamente o procedimento do GATE 4:

- **Único blob:** `c853da42d18dfe090b4e941b435d989311faf3dc` (1137152 bytes)
- **Origem:** GitHub oficial, API de Git Data (blob por OID)
- **Local:** diretório temporário fora do repositório FaithRO
- **Permissões:** restritas (umask 077 quando suportado)
- **Reconfirmação obrigatória:** tamanho + Git blob OID + SHA-256 antes de
  qualquer scan
- **Remoção obrigatória:** em PASS, FINDING, ERROR, TIMEOUT ou STOPPED
- **Proibições:** nunca commitar, nunca versionar, nunca anexar ao PR, nunca
  copiar para VPS, nunca distribuir

**Status:** definido ✅

### 4.2 Lista fechada de ferramentas locais (antes: ambíguo)

A lista é **fechada**. Nenhuma ferramenta pode ser adicionada durante a execução
sem nova decisão humana.

#### 4.2.1 Microsoft Defender Antivirus (MpCmdRun.exe)

| Atributo | Requisito |
|----------|-----------|
| Função | scan local antivírus |
| Invocação | `MpCmdRun.exe -Scan -ScanType 3 -File <path>` |
| Caminho | absoluto, canonicalizado; **não** via `PATH`/`shutil.which()` |
| Localização esperada | `C:\Program Files\Windows Defender\MpCmdRun.exe` ou `C:\ProgramData\Microsoft\Windows Defender\Platform\<version>\MpCmdRun.exe` |
| Verificação pré-scan | SHA-256 do executável coletado e registrado |
| Versão | produto/plataforma e security intelligence coletados e registrados |
| Comportamento de rede | **não depender** de cloud protection; isolamento fornecido pelo ambiente (§5) |
| Arquivo como argumento | `-File <path>` — **nunca** como executável |
| Exit code | 0=clean, 2=threat found; qualquer outro=ERROR |

#### 4.2.2 YARA (yara/yara64)

| Atributo | Requisito |
|----------|-----------|
| Função | scan local com regras estáticas |
| Caminho | absoluto, canonicalizado; **não** via `PATH`/`shutil.which()` |
| Verificação pré-scan | SHA-256 do executável coletado e registrado |
| Versão | `yara --version` coletado e registrado |
| Rulesets | SHA-256 de cada arquivo de regras coletado e registrado |
| Origem das regras | documentada e verificável; regras imutáveis durante execução |
| Download durante execução | **proibido** |
| Arquivo como argumento | argumento posicional — **nunca** como executável |

#### 4.2.3 Adapter sintético (synthetic-local)

| Atributo | Requisito |
|----------|-----------|
| Função | validação de fixtures sintéticas (já existente) |
| Uso | apenas em `--fixture-mode`; puro Python, sem subprocess |
| Escopo | testes e validação do tooling; não opera sobre o WARP real |

#### 4.2.4 Proibição de ferramentas adicionais

Qualquer ferramenta não listada acima é **proibida**. Adição requer nova decisão
humana, com: nome, função, versão, caminho, identidade/hash, razão técnica e
comportamento de rede.

**Status:** definido ✅

### 4.3 Ambiente exigido (antes: ambíguo)

A futura execução real deve ocorrer em um ambiente que satisfaça **todos** os
seguintes requisitos:

| Requisito | Descrição |
|-----------|-----------|
| Tipo | VM Windows descartável/snapshotada **ou** ambiente equivalente com isolamento verificável |
| Separação | separado do ambiente operacional do servidor FaithRO |
| Snapshot | estado inicial registrado; restaurável em caso de problema |
| Rede (egress) | bloqueada por mecanismo **externo ao guest** (hypervisor, firewall do host, regra de rede) |
| Rede (ingress) | apenas o necessário para obter o blob via GitHub oficial; bloqueada antes do scan |
| VPS | acesso proibido |
| Credenciais FaithRO | ausentes no ambiente |
| Tokens/SSH | ausentes no ambiente |
| Dados de jogadores | ausentes no ambiente |
| Compartilhamentos | nenhum desnecessário |
| Defender cloud | **não** depender de serviços cloud; a barreira de rede é externa ao scanner |
| Alterações permanentes | **proibidas** no host do desenvolvedor; usar ambiente descartável |

A evidência da futura execução deve registrar:

- tipo de ambiente;
- mecanismo de isolamento de rede;
- estado de rede antes da execução do scan;
- estado de rede após a execução do scan;
- tentativas bloqueadas observáveis, se aplicável;
- confirmação de que nenhum upload/reputação externa foi autorizado.

**Status:** definido ✅

### 4.4 Critério de aprovação específico do GATE 5 (antes: ambíguo)

Ver §7 (critérios fechados de resultado).

**Status:** definido ✅

### 4.5 Artefatos de preparação (antes: ausente)

| Artefato | Status |
|----------|--------|
| Orquestrador `scripts/warp-audit-gate-05.py` | versionado (PR #59) |
| Testes `scripts/test-warp-audit-gate-05.py` | versionados (PR #59) |
| Schema de entrada `binary-audit-gate-05-input.schema.json` | versionado (PR #59) |
| Schema de evidência `binary-audit-gate-05-evidence.schema.json` | versionado (PR #59) |
| Pacote de decisão (preparação) | versionado (PR #59) |
| Registro de decisão real (este documento) | **este PR** |
| Schema do registro de decisão real | **este PR** |

**Status:** definido ✅

## 5. Isolamento de rede — contrato fechado (R3/R5)

`network_policy=blocked` é uma declaração de intenção. **Não** é barreira técnica.

### 5.1 Requisito obrigatório

O scan real somente pode começar **depois** de haver evidência suficiente de
isolamento técnico:

1. Egress de rede bloqueado por mecanismo independente do scanner/processo.
2. O mecanismo deve ser verificável e registrável (ex.: regra de firewall,
   configuração de hypervisor, air-gap documentado).
3. Configuração interna do Defender (ex.: desativar cloud protection) **não** é
   prova suficiente de isolamento.
4. A barreira de rede deve ser **externa ao scanner**.

### 5.2 Defender e cloud

O Microsoft Defender possui funcionalidades de proteção cloud (MAPS, sample
submission). Durante o GATE 5:

- **Não** depender de cloud protection para resultados.
- **Não** fazer mudanças permanentes na política de segurança do host do
  desenvolvedor.
- O isolamento deve ser fornecido pelo ambiente descartável/firewall externo.
- Se o Defender em modo offline não produzir resultados suficientes, registrar
  como limitação — **nunca** habilitar rede para compensar.

### 5.3 Registro obrigatório na futura evidência

A futura evidência deve registrar o estado de rede antes e depois do scan, o
mecanismo de isolamento e a confirmação de que `network_access=false` e
`external_reputation_upload_authorized=false`.

## 6. Identidade das ferramentas — fechamento do R13

`shutil.which()` sozinho **não** atende o requisito de identidade.

### 6.1 Procedimento obrigatório antes de cada scan

```text
1. Resolver caminho do scanner
2. Canonicalizar caminho (resolve symlinks)
3. Rejeitar localização inesperada (fora dos diretórios permitidos)
4. Calcular SHA-256 do executável
5. Coletar versão do produto
6. Registrar caminho + SHA-256 + versão na evidência
7. Comparar contra expectativas do contrato (localização permitida)
8. Somente então permitir execução do scan
```

### 6.2 Comportamento em caso de divergência

Qualquer divergência inesperada (caminho fora da allowlist, hash desconhecido,
versão incompatível) deve resultar em:

```text
FAIL-CLOSED — nenhum scan ocorre
```

### 6.3 Política para mudanças legítimas de versão

Atualizações de security intelligence do Defender são legítimas e esperadas. O
hash do `MpCmdRun.exe` e a versão da plataforma devem ser registrados, mas não
fixados rigidamente. O que importa é:

- Localização no diretório esperado;
- Executável assinado pela Microsoft (se verificável);
- Versão registrada na evidência.

Para YARA, o hash do executável e dos rulesets devem ser fixados e documentados
antes da execução.

## 7. Critérios fechados de resultado do futuro GATE 5

### 7.1 PASS

Somente quando **todos** forem verdadeiros:

- ambiente isolado validado;
- identidade do alvo validada (SHA-256, tamanho, blob OID);
- identidade de cada scanner validada (caminho, hash, versão);
- nenhuma ferramenta fora da allowlist;
- todos os scans terminam normalmente (dentro do timeout);
- nenhum finding classificado como ameaça;
- nenhum timeout;
- nenhum parser error;
- nenhuma ferramenta retorna estado desconhecido;
- nenhuma tentativa de operação proibida;
- evidência final válida contra schema;
- predecessor (GATE 4 output SHA-256) íntegro;
- binário e diretório temporário removidos;
- confirmação de limpeza registrada.

### 7.2 FINDING

Qualquer scanner indicar possível ameaça, detecção ou resultado conservador
equivalente. **Não** converter FINDING em PASS automaticamente.

FINDING exige interpretação humana e contextual. Um resultado individual **não**
prova que o binário é malicioso — mas **não** pode ser descartado sem análise.

### 7.3 ERROR

Incluindo, mas não limitado a:

- scanner indisponível ou com hash divergente;
- target com identidade divergente;
- parser failure;
- output inesperado ou fora do schema;
- erro de acesso ao arquivo;
- ambiente incompleto ou não verificável;
- cleanup incompleto.

### 7.4 TIMEOUT

Timeout é resultado independente e **não** é PASS. Se um scanner exceder o
timeout configurado, o resultado é TIMEOUT e o gate **não** pode concluir PASS.

### 7.5 BLOCKED

Utilizado quando pré-condições de segurança não permitirem começar o scan:

- ambiente não isolado;
- identidade do alvo não confirmada;
- identidade do scanner não confirmada;
- predecessor não íntegro;
- flag obrigatória com valor indevido;
- qualquer pré-condição do contrato violada.

O sistema é **fail-closed** em todos os caminhos.

## 8. Identidade do alvo

### 8.1 Artefato único

| Atributo | Valor |
|----------|-------|
| Repositório | `Neo-Mind/WARP` |
| Branch | `rock_win32` |
| Commit | `9b1173e9e4e135c68e150704f01186ab5e763acd` |
| Caminho | `win32/WARP.exe` |
| Git blob OID | `c853da42d18dfe090b4e941b435d989311faf3dc` |
| Tamanho | 1137152 bytes |
| SHA-256 | `345f3464ee72a60afc97bde0773410f47348a00d8629182fe52741c5f1a42874` |

### 8.2 Verificação obrigatória antes do scan

1. Materializar via GitHub oficial (Git Data API, blob por OID)
2. Calcular SHA-256 localmente
3. Comparar com valor esperado (`345f3464...`)
4. Comparar tamanho com valor esperado (1137152)
5. Verificar Git blob OID com valor esperado (`c853da42...`)
6. Se qualquer divergência: FAIL-CLOSED, remover imediatamente

### 8.3 Proibições

O binário **não** pode ser: commitado, versionado, anexado ao PR, publicado,
copiado para VPS, distribuído pelo projeto. A evidência pode conter somente
metadados e hashes — nunca bytes do binário.

## 9. Flags desta decisão

| Flag | Valor | Justificativa |
|------|-------|---------------|
| `human_decision_required` | `true` | decisão humana necessária por contrato |
| `human_decision_received` | `true` | decisão recebida nesta etapa |
| `option_selected` | `true` | Opção D selecionada condicionalmente |
| `gate_5_authorized` | `true` | GATE 5 autorizado para futura execução controlada |
| `local_security_scan_authorized` | `true` | scan local autorizado com ferramentas da lista fechada |
| `temporary_materialization_authorized` | `true` | materialização temporária do blob autorizada |
| `execution_authorized` | `false` | execução do PE permanece proibida |
| `client_preparation_authorized` | `false` | **proibido** |
| `external_reputation_upload_authorized` | `false` | **proibido** |
| `vps_access_authorized` | `false` | **proibido** |
| `distribution_authorized` | `false` | **proibido** |
| `dynamic_analysis_authorized` | `false` | fora do escopo do GATE 5 |

> [!IMPORTANT]
> `gate_5_authorized=true` e `local_security_scan_authorized=true` neste
> registro de decisão **não** habilitam o tooling a executar automaticamente.
> O orquestrador (`warp-audit-gate-05.py`) possui bloqueio no modo `real` que
> exige remoção explícita em PR separado de execução. A evidência de input
> schema (`binary-audit-gate-05-input.schema.json`) mantém `mode` como
> `enum: ["validate-only", "fixture"]` — sem `real`. A separação
> decisão/execução é preservada arquiteturalmente.

> [!CAUTION]
> `client_preparation_authorized` permanece **false**. A preparação efetiva do
> cliente exige etapa posterior, explícita, independente e revisável.

## 10. Abort conditions (mantidas do doc 44 §11)

Interrompem imediatamente e retornam à decisão humana:

- hash/identidade divergente do blob fixado;
- artefato inesperado ou saída fora do schema;
- qualquer tentativa de rede não prevista;
- persistência ou alteração fora do diretório temporário autorizado;
- acesso a credenciais ou dados reais;
- falha de isolamento ou do embargo de rede;
- falha de logging;
- escopo divergente do plano;
- qualquer comportamento não coberto pelo contrato.

## 11. Riscos residuais

### R13 — Identidade do scanner

Fechado por este contrato (§6). A execução real deve seguir o procedimento de
verificação obrigatório. `shutil.which()` sozinho é insuficiente.

### Rede

`network_policy=blocked` não é garantia técnica. O contrato (§5) exige
isolamento verificável por mecanismo externo ao scanner.

### Defender cloud

Defender pode depender de serviços cloud. O contrato (§5.2) proíbe dependência
e exige barreira externa.

### YARA/rules

Executável e rulesets devem ter identidade verificável. Download durante
execução é proibido (§4.2.2).

### Assets proprietários

O projeto não autoriza redistribuição do WARP, cliente, GRF ou assets
proprietários. Apenas análise local é permitida (§8.3).

### Cliente

Esta decisão **não** autoriza preparação nem distribuição do cliente.

## 12. Rollback

### Antes do merge

Corrigir por commit normal, manter draft ou fechar o PR sem merge.

### Depois do merge

Revogar por novo registro e novo PR sem reescrever evidência histórica. Nunca
usar reset destrutivo ou force push. A revogação **não** pode executar o PE,
autorizar uma segunda execução, restaurar ou introduzir binário no Git,
preparar o cliente ou acessar a VPS.

## 13. Próxima etapa

Após revisão e integração deste PR em `dev`, a próxima etapa será:

**ETAPA 2P-E-C5-REAL-EXEC** — executar uma única execução real e controlada do
GATE 5, sob o contrato aqui aprovado, em branch e PR separados.

Esta etapa **não** antecipa essa execução.

## Estado de verificação

- **Fato:** GATE 4 integrado (`03348d7`); output SHA-256 `84c3c49a…`
  recomputado; tooling do GATE 5 revisado (84/84 PASS, PR #59 `80f6f7a`);
  Opção D reconstruída do doc 44 §16.
- **Decisão:** Opção D selecionada condicionalmente; lacunas de §10 fechadas;
  contrato de execução definido com ferramentas, ambiente, critérios e
  identidade.
- **Pendência:** execução real em etapa separada (2P-E-C5-REAL-EXEC).
- **Nota:** decisão técnica e de conformidade do projeto, **não** parecer
  jurídico nem atestado de segurança.
