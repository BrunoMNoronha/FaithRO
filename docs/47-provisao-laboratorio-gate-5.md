# Especificação, runbook e auditoria de prontidão do laboratório para o GATE 5

> **Etapa:** 2P-E-C5-LAB-PROVISION  
> **Predecessor:** 2P-E-C5-REAL-EXEC-PREFLIGHT (resultado: `PREFLIGHT_BLOCKED — NO EXECUTION`)  
> **Decisão de base:** 2P-E-C5-REAL-AUTH-DECISION ([doc 46](46-decisao-execucao-real-gate-5-verificacoes-locais.md), decisor BrunoMNoronha)  
> **Estado desta etapa:** `LAB_PROVISION_BLOCKED — NO TARGET MATERIALIZATION`  
> **Data:** 2026-08-28  

```text
target_materialized=false
artifact_executed=false
defender_target_scan_executed=false
yara_target_scan_executed=false
network_active_test_performed=false
external_reputation_used=false
vps_accessed=false
client_prepared=false
distribution_performed=false
```

---

## 0. Princípio e garantias de segurança

Esta etapa é estritamente **fail-closed** e tem caráter preparatório, documental e de auditoria de prontidão.

O princípio fundamental da cadeia permanece:

$$\text{Tooling pronto} \neq \text{Decisão aprovada} \neq \text{Lab provisionado} \neq \text{Preflight aprovado} \neq \text{Target materializado} \neq \text{Target escaneado} \neq \text{Execução autorizada}$$

Fica expressamente estabelecido:

```text
LAB_READY != EXECUTION_AUTHORIZED
LAB_READY != CLIENT_PREPARATION_AUTHORIZED
LAB_READY != DISTRIBUTION_AUTHORIZED
```

Nenhum artefato do cliente foi materializado, copiado, escaneado, executado ou distribuído.

---

## 1. Objetivo

1. Especificar a arquitetura técnica, requisitos operacionais e critérios de aceitação do laboratório dedicado para o GATE 5 da auditoria binária offline do WARP.
2. Definir o runbook seguro de provisionamento e congelamento do ambiente pelo operador humano.
3. Auditar o estado corrente do laboratório frente aos quatro bloqueios identificados no preflight anterior (`BLK-01` a `BLK-04`).
4. Fixar os requisitos de versão, proveniência e integridade da engine YARA clássica (4.5.5) e dos rulesets aprovados (`Yara-Rules/rules` sob GPL-2.0).
5. Fornecer os critérios formais para que um futuro rerun do preflight (`ETAPA 2P-E-C5-REAL-EXEC-PREFLIGHT-RERUN`) possa avaliar a transição para `PREFLIGHT_PASS`.

---

## 2. Ameaças mitigadas pelo modelo de laboratório

| ID | Ameaça | Vetor | Mitigação no laboratório |
|---|---|---|---|
| **T1** | Contaminação do host do desenvolvedor | Execução acidental ou exploração de parser de antivírus durante a inspeção do alvo | VM Windows x64 descartável e dedicada, sem persistência fora do snapshot, sem montagem de unidades do host |
| **T2** | Egress acidental / vazamento de telemetria | Scanners locais tentando contactar serviços em nuvem (ex.: MAPS do Defender, telemetry) ou binário acionado | Isolamento de rede imposto **fora do guest** (hypervisor / virtual switch sem uplink / firewall do host) |
| **T3** | Exposição de credenciais e infraestrutura | Sessões ativas de navegador, chaves SSH, tokens Git ou `.env` do FaithRO acessíveis no ambiente | VM limpa sem qualquer credencial, secret, chave SSH, token GitHub ou dump de banco |
| **T4** | Drift ou adulteração de ferramentas de análise | Uso de binários de scanner de origem desconhecida ou mutável | Identidade do YARA (versão 4.5.5, SHA-256) e caminhos absolutos canônicos do Defender verificados antes do uso |
| **T5** | Incompatibilidade ou mutabilidade de regras | Regras YARA sofrendo alterações silenciosas ou falhando em compilação | Ruleset pinado a commit SHA-40 imutável, SHA-256 por arquivo, aggregate SHA-256 e compilação prévia com `compile errors = 0` |
| **T6** | Falsos positivos como veredito absoluto | Regra heurística genérica disparando alarme | Resultados tratados como evidência contextual com schema fechado, nunca como aprovação/reprovação automática |

---

## 3. Arquitetura do laboratório

```text
+-------------------------------------------------------------------------------+
| HOST FÍSICO DO DESENVOLVEDOR (Windows Workstation)                           |
|                                                                               |
|  +-------------------------------------------------------------------------+  |
|  | Hypervisor (Hyper-V / VirtualBox / VMware Workstation)                  |  |
|  |                                                                         |  |
|  |  Barreira de Rede Externa:                                              |  |
|  |  * Virtual Switch "Private / Host-Only" SEM gateway/uplink               |  |
|  |  * Egress para Internet = BLOQUEADO NO HYPERVISOR                      |  |
|  |  * Egress para LAN / VPS = BLOQUEADO NO HYPERVISOR                      |  |
|  |                                                                         |  |
|  |  +-------------------------------------------------------------------+  |  |
|  |  | VM Windows x64 Descartável                                        |  |  |
|  |  |                                                                   |  |  |
|  |  |  [ Snapshot / Checkpoint Baseline Limpo ]                          |  |  |
|  |  |                                                                   |  |  |
|  |  |  * OS: Windows 10 / 11 x64 (Clean Install)                        |  |  |
|  |  |  * Scanners Locais Pré-posicionados:                              |  |  |
|  |  |    - Microsoft Defender Antivirus (MpCmdRun.exe)                  |  |  |
|  |  |    - YARA clássico 4.5.5 oficial (yara.exe / yara64.exe)          |  |  |
|  |  |    - Rulesets pinados (Yara-Rules/rules @ commit fixado)          |  |  |
|  |  |                                                                   |  |  |
|  |  |  * Proibições no Guest:                                           |  |  |
|  |  |    - SEM credenciais FaithRO / `.env` / dumps                     |  |  |
|  |  |    - SEM chaves SSH / tokens GitHub                               |  |  |
|  |  |    - SEM compartilhamento de pastas (Shared Folders)              |  |  |
|  |  |    - SEM clipboard compartilhado / Drag & Drop                    |  |  |
|  |  |    - SEM dados reais de jogadores                                 |  |  |
|  |  +-------------------------------------------------------------------+  |  |
|  +-------------------------------------------------------------------------+  |
+-------------------------------------------------------------------------------+
```

---

## 4. Requisitos obrigatórios da VM e do ambiente

### 4.1 Descartabilidade e snapshots
A VM deve possuir snapshot/checkpoint limpo registrado antes de qualquer introdução de alvos ou testes.
Informações que devem ser registradas na evidência:
- Nome do Hypervisor e versão;
- Nome da máquina virtual;
- Versão e build do sistema operacional guest;
- Arquitetura do guest (x64);
- Nome do snapshot/checkpoint baseline;
- Identificador GUID do snapshot (se suportado pelo hypervisor);
- Timestamp UTC de criação do snapshot.

### 4.2 Credenciais e segredos (Data Gate)
O ambiente guest deve ser auditado passivamente para confirmar a **ausência total** de:
- Chaves privadas SSH (`id_rsa`, `id_ed25519`, etc.);
- Tokens de autenticação (GitHub Personal Access Tokens, Azure, AWS, etc.);
- Credenciais no Windows Credential Manager vinculadas ao ambiente de produção ou repositório;
- Arquivos de configuração `.env` ou dumps MariaDB/SQL do FaithRO;
- Dados de contas ou jogadores reais;
- Sessões ativas em navegadores web.

### 4.3 Integrações Host / Guest
Devem ser desativadas no hypervisor:
- Compartilhamento de área de transferência (Shared Clipboard);
- Arrastar e soltar (Drag and Drop);
- Pastas compartilhadas automáticas (Shared Folders / Host Drive Mounting);
- Passthrough de dispositivos USB não essenciais.

### 4.4 Isolamento de rede
O isolamento deve ser garantido **fora do guest**:
- A interface de rede virtual da VM deve estar associada a um switch privado/isolado sem rota padrão de internet;
- Não é permitida comunicação com a VPS ou com servidores da LAN do desenvolvedor;
- A comprovação de isolamento no preflight deve ser **passiva** (verificação da configuração do virtual switch / adaptador), sendo proibida a execução de comandos de rede ativos contra a internet (ex.: `ping`, `curl`, `Invoke-WebRequest`, consultas DNS públicas).

---

## 5. Especificação das ferramentas locais

### 5.1 Microsoft Defender Antivirus (`MpCmdRun.exe`)
- **Finalidade:** Scanner antivírus local offline.
- **Invocação autorizada:** `MpCmdRun.exe -Scan -ScanType 3 -File <caminho_absoluto>`
- **Localização canônica permitida:**
  - `%ProgramFiles%\Windows Defender\MpCmdRun.exe`
  - `%ProgramData%\Microsoft\Windows Defender\Platform\<versao>\MpCmdRun.exe`
- **Requisitos de conformidade:**
  - O executável deve ser invocado diretamente por caminho absoluto canonicalizado (proibida resolução cega via `PATH`);
  - Coleta de tamanho, SHA-256 e versão da plataforma antes de qualquer uso;
  - Operação com o arquivo como argumento de análise (`-File`), nunca como executável;
  - Exit codes: 0 = limpo (sem ameaças detectadas), 2 = ameaça encontrada; qualquer outro = `ERROR`.

### 5.2 YARA clássico 4.5.5
- **Finalidade:** Mecanismo de varredura estática baseado em assinaturas de regras.
- **Engine autorizada:** YARA clássico `v4.5.5` (proibido migrar para YARA-X nesta etapa para evitar drift de tooling).
- **Origem canônica:** Repositório oficial VirusTotal/yara (Release `v4.5.5`).
- **Requisitos de conformidade do binário:**
  - Nome do ativo: `yara-4.5.5-win64.zip` / `yara64.exe` (ou `yara32.exe`);
  - Versão confirmada via `yara --version`: exatamente `4.5.5`;
  - SHA-256 coletado diretamente sobre o binário pré-posicionado;
  - Execução restrita a argumentos posicionais apontando para o arquivo, sem execução do alvo.

---

## 6. Especificação e política do Ruleset

### 6.1 Baseline aprovado
- **Repositório:** `Yara-Rules/rules`
- **Licença:** GNU General Public License v2.0 (`GPL-2.0`)
- **Política de congelamento:** O operador deve fixar um commit SHA-40 exato no momento da aquisição. É proibido o uso da referência volátil `master`.

### 6.2 Categorias relevantes para executáveis PE Windows
A seleção de regras para o primeiro ciclo do GATE 5 deve focar nas categorias pertinentes a binários PE Windows:
1. `malware` — assinaturas de famílias de malware conhecidas;
2. `packers` — detecção de empacotadores, compressores e obfuscadores PE;
3. `antidebug_antivm` / `anti_analysis` — detecção de rotinas de evasão e técnicas anti-análise;
4. `capabilities` — mapeamento de funcionalidades estruturais;
5. `crypto` — assinaturas de constantes e rotinas criptográficas conhecidas.

### 6.3 Categorias expressamente excluídas
Ficam excluídas do conjunto ativo deste ciclo:
- `email` (regras para análise de cabeçalhos e anexos de e-mail);
- `exploit_kits` e `cve` voltados a documentos (PDF, Office, RTF);
- `webshells` (regras para PHP, ASP, JSP);
- `mobile` / `android` (regras para APK, DEX, Mach-O/iOS).

### 6.4 Tratamento de regras incompatíveis
- **Regra fundamental:** Proibido modificar código de regras upstream de terceiros no repositório FaithRO.
- Se uma regra falhar na compilação (`yarac` ou `yara -w`):
  1. Identificar o arquivo e regra exata;
  2. Documentar o motivo técnico da incompatibilidade;
  3. Excluir o arquivo da lista efetiva do ruleset;
  4. Recalcular o aggregate SHA-256 do conjunto resultante;
  5. Não realizar correções silenciosas.

### 6.5 Cálculo do Aggregate SHA-256 do Ruleset
O hash agregado dos rulesets deve ser calculado de forma determinística:
1. Listar todos os arquivos `.yar` / `.yara` aprovados em ordem alfabética ascendente de seus caminhos relativos (usando separador `/` e codificação UTF-8);
2. Para cada arquivo, calcular o SHA-256 em hexadecimal minúsculo;
3. Concatenar as linhas no formato `<sha256>  <caminho_relativo>\n` (com terminação LF);
4. Calcular o SHA-256 do manifesto concatenado.

---

## 7. Runbook seguro de preparação do operador

O operador humano deve seguir a seguinte ordem de passos para provisionar o laboratório:

```text
Passo 1:  Criar VM Windows x64 limpa no Hypervisor escolhido (Hyper-V / VirtualBox / VMware).
Passo 2:  Atualizar o sistema operacional guest e o Microsoft Defender (com conectividade temporária de instalação).
Passo 3:  Baixar o release oficial do YARA 4.5.5 (VirusTotal/yara v4.5.5) e verificar hash.
Passo 4:  Clonar/baixar o repositório Yara-Rules/rules no commit fixado e filtrar categorias PE.
Passo 5:  Pré-posicionar o binário do YARA e as regras na VM em diretório dedicado (ex.: C:\Tools\YARA).
Passo 6:  Executar validação de sintaxe (compilação) de todas as regras com yarac.exe (0 erros).
Passo 7:  Coletar inventário de arquivos de regras, hashes individuais e aggregate SHA-256.
Passo 8:  Auditar o guest: remover histórico, caches de credenciais, chaves SSH, tokens, navegadores logados.
Passo 9:  Desativar integrações host/guest (Shared Folders, Shared Clipboard, Drag & Drop).
Passo 10: Desligar a VM.
Passo 11: Desconectar o Virtual Switch do guest ou configurar rede "Private/Host-Only" sem rota externa.
Passo 12: Criar o snapshot/checkpoint baseline limpo (ex.: "BASELINE_GATE5_ISOLATED").
Passo 13: Ligar a VM no modo isolado.
Passo 14: Executar preflight passivo e produzir o manifesto do laboratório (SEM o alvo WARP).
```

---

## 8. Auditoria do estado atual (Diagnóstico dos Bloqueios)

Na presente etapa (`2P-E-C5-LAB-PROVISION`), a inspeção passiva do ambiente resultou no seguinte diagnóstico formal:

| Identificador | Pré-condição | Estado Atual | Diagnóstico |
|---|---|---|---|
| `BLK-01` | VM Windows x64 descartável com snapshot baseline | **NÃO DISPONÍVEL** | Nenhuma VM dedicada com checkpoint baseline registrado foi disponibilizada no hypervisor local. |
| `BLK-02` | Isolamento de rede imposto externamente | **NÃO CONFIGURADO** | O ambiente host não possui virtual switch isolado ativo associado a uma VM de análise. |
| `BLK-03` | YARA clássico 4.5.5 pré-posicionado | **NÃO PRÉ-POSICIONADO** | Binário oficial do YARA 4.5.5 não localizado em diretório de laboratório no ambiente de execução. |
| `BLK-04` | Rulesets Yara-Rules pinados e validados | **NÃO CONGELADOS** | Conjunto de regras não adquirido, não filtrado e sem aggregate SHA-256 gerado no ambiente. |

Como consequência direta do princípio fail-closed:

```text
Resultado da auditoria de prontidão:
LAB_PROVISION_BLOCKED — NO TARGET MATERIALIZATION
```

---

## 9. Cadeia de integridade do projeto

Os valores canônicos da cadeia de auditoria do WARP foram verificados diretamente no repositório Git:

- **Alvo canônico fixado:** `win32/WARP.exe` no commit `9b1173e9e4e135c68e150704f01186ab5e763acd` do repositório `Neo-Mind/WARP`
- **Git Blob OID do alvo:** `c853da42d18dfe090b4e941b435d989311faf3dc`
- **Tamanho esperado do alvo:** `1137152` bytes
- **SHA-256 esperado do alvo:** `345f3464ee72a60afc97bde0773410f47348a00d8629182fe52741c5f1a42874`
- **Predecessor GATE 4 Output SHA-256:** `84c3c49a770b475fdf25c43467498e014b2f8950ef172384bb8ea48bbe17f584` (arquivo `client/warp-audit/evidence/binary-audit-gate-04-static-inventory-output-2026-08-05.json`)
- **Squash do Tooling GATE 5:** `80f6f7a0da38ca18edd93e87260529f74c49d5ca` (PR #59)
- **Git Blob OID do Orquestrador (`scripts/warp-audit-gate-05.py`):** `952df939d2ca2db656dd8c5ccd787916f5ea3ba0`
- **Git Blob OID dos Testes (`scripts/test-warp-audit-gate-05.py`):** `0af398724a63c8aad3123c08f3b6f860de88c370`

A cadeia histórica permanece estritamente íntegra e sem qualquer desvio (zero drift).

---

## 10. Riscos e mitigações

- **R1 — Contaminação do host:** Mitigado pelo modelo de VM descartável com reversão a snapshot.
- **R2 — Egress acidental de rede:** Mitigado pela exigência de isolamento em camada de virtual switch / hypervisor externo ao guest.
- **R3 — Drift de versão do YARA:** Mitigado pela fixação estrita da versão 4.5.5 oficial com SHA-256 do executável verificado.
- **R4 — Drift de rulesets:** Mitigado pela fixação de commit SHA-40, filtragem determinística de categorias e aggregate SHA-256.
- **R5 — Falsos positivos em regras:** Mitigado pela interpretação contextual e pelo schema de evidência estruturado (achado $\neq$ veredito de infecção).
- **R6 — Licenciamento GPL-2.0:** Mitigado pelo registro da licença e por não vendorizar o ruleset upstream integralmente no repositório FaithRO.
- **R7 — Migração prematura para YARA-X:** Mitigado pela decisão explícita de manter YARA 4.5.5 clássico.
- **R8 — Materialização prematura do binário:** Mitigado pela proibição absoluta de download, cópia ou extração do WARP nesta etapa.

---

## 11. Plano de Rollback

- **Repositório:** A branch `docs/gate-5-lab-provision` pode ser descartada ou resetada sem afetar a integridade de `dev`. Nenhuma alteração foi realizada na branch principal.
- **Laboratório:** Caso qualquer artefato temporário ou incorreto seja colocado no ambiente da VM, o operador deve desligar a VM e restaurar o estado ao snapshot baseline limpo anterior à alteração.

---

## 12. Próximos passos

1. O operador humano deve executar o provisionamento prático da VM conforme o runbook da Seção 7;
2. Disponibilizar a VM isolada com snapshot, YARA 4.5.5 e rulesets compilados;
3. Executar a etapa dedicada `ETAPA 2P-E-C5-REAL-EXEC-PREFLIGHT-RERUN` para validar os 4 requisitos e produzir o manifesto do laboratório;
4. Somente após `PREFLIGHT_PASS` formal no rerun e aprovação humana separada será avaliada a etapa de varredura estática real.
