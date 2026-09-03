# Validação pós-snapshot `GATE5-Baseline` e preparação controlada do cliente (Etapa 2P-M-R2)

> **Escopo:** registro técnico da validação física e lógica do snapshot baseline `GATE5-Baseline` no laboratório isolado `FaithRO-GATE5-LAB`, inventário exaustivo de integridade do cliente oficial autorizado em `C:\Gravity\Ragnarok`, reconciliação da suíte de automação do laboratório (181 PASS / 0 FAIL) e validadores do repositório, preparação controlada do arquivo de configuração próprio `clientinfo.xml` e definição do runbook de sanidade e rollback. Nenhum binário proprietário, GRF, chave privada, segredo ou dado de jogador é registrado ou versionado.

---

## 1. Resumo executivo

Na etapa anterior (2P-I / [Doc 51](51-gate5-preparacao-controlada-cliente.md)), a preparação controlada foi bloqueada em `L1 LAB` e `L2 PATCH_TOOL` porque o laboratório isolado ainda não possuía um snapshot baseline formalizado e a VM não havia concluído o isolamento de rede e mídias.

Em 2026-09-03, o operador humano executou com sucesso a criação manual do snapshot de baseline no VMware Workstation, nomeado exatamente:

```text
GATE5-Baseline
```

A presente etapa (**2P-M-R2**) consolida a validação empírica e auditável deste baseline:
1. **Snapshot validado:** Presença física e lógica do snapshot `GATE5-Baseline` comprovada via inspeção read-only do `.vmsd`, `.vmsn`, delta VMDK ativo (`FaithRO-GATE5-LAB-000001.vmdk`) e preservação do disco base (`FaithRO-GATE5-LAB.vmdk`). A árvore de snapshots não sofreu mutações indevidas (`SNAPSHOT_TREE_MUTATED: NO`).
2. **Cliente autorizado inventariado:** Localizado na estação do operador em `C:\Gravity\Ragnarok`, com integridade de `Ragexe.exe` (SHA-256 `8990A9A9...`) e `data.grf` (SHA-256 `6DCAE744...`) integralmente conferida.
3. **Automação do laboratório:** Executada com **181 PASS / 0 FAIL** em `scripts/lab/test-gate5-lab-automation.ps1`, e 100% de aprovação nos validadores do projeto (`validate-progression-overrides.py`, `validate-warp-audit.py`, `validate-client-assets.py`, `validate-patcher-config.py`).
4. **Preparação controlada:** Configuração textual `clientinfo.xml` gerada em pasta isolada de evidências (`.local/gate5-lab/evidence/run-05-client-preparation/`), apontando para `129.121.46.11:6900`.
5. **Preservação de binários:** Nenhuma alteração em executáveis proprietários, DLLs ou arquivos GRF foi realizada nesta etapa.

---

## 2. Estado inicial reconciliado

- **Repositório Git:**
  - Branch base: `dev` sincronizado com `origin/dev` no commit `92432b8d73482d23aa56a73161949ddeaa43161e`.
  - Branch de trabalho: `ops/gate5-baseline-validation-client-prep`.
  - Working tree limpa antes de qualquer alteração.
- **Processos do host:**
  - Processo `vmware-vmx.exe` inativo (VM desligada).
  - Processo `vmware.exe` finalizado de forma limpa antes dos testes para desocupação de locks e eliminação de caching em disco.
- **Laboratório físico (`C:\VMs\FaithRO-GATE5-LAB`):**
  - Diretório íntegro, sem arquivos corrompidos ou locks residuais.
  - vTPM 2.0 ativo com criptografia parcial do VMX (chave sob custódia exclusiva do operador).

---

## 3. Evidência e validação do snapshot `GATE5-Baseline`

A inspeção em modo estritamente *read-only* dos artefatos da VM em `C:\VMs\FaithRO-GATE5-LAB` revelou:

### 3.1 Metadados no arquivo `.vmsd` (`FaithRO-GATE5-LAB.vmsd`)
```ini
.encoding = "UTF-8"
snapshot.lastUID = "1"
snapshot.current = "1"
snapshot0.uid = "1"
snapshot0.filename = "FaithRO-GATE5-LAB-Snapshot1.vmsn"
snapshot0.displayName = "GATE5-Baseline"
snapshot0.description = "Baseline Windows 11 operacional antes das alterações controladas do cliente FaithRO."
snapshot0.createTimeHigh = "416404"
snapshot0.createTimeLow = "1361996416"
snapshot0.numDisks = "1"
snapshot0.disk0.fileName = "FaithRO-GATE5-LAB.vmdk"
snapshot0.disk0.node = "nvme0:0"
snapshot.numSnapshots = "1"
snapshot.mru0.uid = "1"
```

- **Hash SHA-256 do `.vmsd`:** `C28B2B702E9E80C0DAAA3CA2035BF519FCA1D87B5A8926E47355B875B85D9354`

### 3.2 Arquivo de estado da VM (`FaithRO-GATE5-LAB-Snapshot1.vmsn`)
- **Tamanho:** 339.968 bytes
- **Data de gravação:** 2026-09-03 10:42:03
- **Hash SHA-256:** `ED7D7C49BF2AB894992B4F21C25B793C6F6C95EBDCCB3595BD2D7741D48B3679`

### 3.3 Estrutura de discos no arquivo `.vmx`
- **Disco base preservado (read-only pelo hypervisor):** `FaithRO-GATE5-LAB.vmdk` (40.618.885.120 bytes)
- **Disco delta ativo:** `FaithRO-GATE5-LAB-000001.vmdk` (9.240.576 bytes)
- **Entrada no VMX:**
  ```ini
  nvme0:0.present = "TRUE"
  nvme0:0.fileName = "FaithRO-GATE5-LAB-000001.vmdk"
  ```

### 3.4 Resultado da validação do snapshot
```text
GATE5_BASELINE_SNAPSHOT_PRESENT: PASS
GATE5_BASELINE_SNAPSHOT_NAME: GATE5-Baseline
SNAPSHOT_TREE_MUTATED: NO
BASE_DISK_FROZEN: PASS
DELTA_DISK_ACTIVE: PASS
```

---

## 4. Auditoria e inventário do cliente autorizado

A busca local na estação de trabalho localizou e catalogou o cliente oficial em `C:\Gravity\Ragnarok`:

```text
CLIENT_FOUND: PASS
CLIENT_ROOT: C:\Gravity\Ragnarok
CLIENT_EXECUTABLE_PRESENT: YES
DATA_ARCHIVE_PRESENT: YES
CLIENT_CONFIGURATION_IDENTIFIED: YES
```

### 4.1 Componentes e hashes críticos
| Arquivo | Tamanho (bytes) | Hash SHA-256 | Função / Descrição |
|---|---|---|---|
| **`Ragexe.exe`** | 7.696.896 | `8990A9A9CD6623E173BCC8B406A311AF32773EB881E539082126B768C14E95A0` | Executável principal (kRO 2021-11-05; assinatura digital oficial da Gravity válida) |
| **`data.grf`** | 3.167.729.595 | `6DCAE744FB8E5FC1FCAFBE8CFB3F5392E9D89B431E56811C3618462D5DE2D53A` | Arquivo principal de assets/recursos do jogo |
| **`Ragnarok.exe`** | 465.296 | `43A18F51CD7FE60EDC5B34E8016AACC6E84C64BF7BEA6CE196A2516A87383E50` | Launcher/patcher oficial |
| **`Setup.exe`** | 1.623.952 | `05C67B70EA48DC43E086C11AE5B09A428C6E5E6330F1B77D1A0D78AF7D235FEF` | Utilitário de configuração gráfica/áudio |
| **`Init.exe`** | 15.016 | `F6D6EFEACCF1FE1AF7C673C5960E96E1B3809FF7220BA5528E0C7325BDDC7083` | Inicializador de ambiente do cliente |
| **`RagnarokKR.ini`** | 1.157 | `39596D14B349DC86C44D8B131A0243212524B8D7AB070373BD3266644BD1DFCB` | Configuração proprietária ofuscada do patcher kRO |
| **`Patch.inf`** | 4 | `6531852ACC5B9D256BEDF48254722B5826D4928C61A4A0F046C082C6ABB6FDCB` | Arquivo de controle de versão do patcher |
| **`GameGuard.des`** | 537.040 | `34BD5706904B3412F7CFDE30FD23FFE4BF7DDDB3C8814A6003CEC0ACF9775FB0` | Módulo de proteção GameGuard |
| **`v3hunt.dll`** | 131.201 | `F4AFE407BEA443ADBB18387DE30BF139E8FF8CD6028464F200EFC55D1348CCE9` | Módulo de anticheat AhnLab V3 |

### 4.2 Diretórios identificados
- `AI`, `BGM`, `NavigationData`, `PatchClient`, `Skin`, `System`.
- O diretório customizado `data\` ainda não existe na instalação raiz (será materializado de forma controlada na etapa seguinte).

---

## 5. Reconciliação e execução de testes automatizados

### 5.1 Suíte de automação do laboratório GATE 5
- **Arquivo:** [`scripts/lab/test-gate5-lab-automation.ps1`](../scripts/lab/test-gate5-lab-automation.ps1)
- **Diagnóstico prévio:** O teste sintético apontou bloqueio por `Test-Gate5VmwareUiRunning` enquanto a interface do VMware Workstation estava aberta. Com o encerramento gracioso do processo `vmware.exe`, a suíte foi executada:
  ```text
  RESULTADO: 181 PASS / 0 FAIL
  LAB_AUTOMATION_TESTS: PASS
  ```

### 5.2 Validadores do repositório
Todos os validadores executados com sucesso:
- `python scripts/validate-progression-overrides.py` -> **OK** (Base EXP 157, Stat points 55, Cap 185, ASPD 197)
- `python scripts/validate-warp-audit.py` -> **OK** (8 artefatos, schemas, regras de segurança, cross-checks e decisão do GATE 5)
- `python scripts/validate-client-assets.py` -> **OK** (110 arquivos em `client/`)
- `python scripts/validate-patcher-config.py` -> **OK** (50 arquivos em `client/patcher/`)
- **Critério:** `PROJECT_VALIDATORS: PASS`.

---

## 6. Preparação controlada executada

1. **Reconciliação da constante de snapshot:**
   - Em [`scripts/lab/gate5-common.ps1`](../scripts/lab/gate5-common.ps1), a variável `$script:Gate5SnapshotName` foi atualizada de `'BASELINE_GATE5_ISOLATED'` para `'GATE5-Baseline'`, alinhando a automação ao nome oficial escolhido pelo operador.
2. **Preparação do `clientinfo.xml` FaithRO:**
   - Criado em `.local/gate5-lab/evidence/run-05-client-preparation/clientinfo.xml` com hash SHA-256 `F0517B52B734C1528E11C4DEE2926255794781D2ABB0C4728C8BED3B667C7CE3`:
     ```xml
     <?xml version="1.0" encoding="utf-8" ?>
     <clientinfo>
         <connection>
             <display>FaithRO - Laos Deos</display>
             <address>129.121.46.11</address>
             <port>6900</port>
             <version>20211103</version>
             <langtype>1</langtype>
         </connection>
     </clientinfo>
     ```
3. **Pasta de evidências da etapa:**
   - Criada em `.local/gate5-lab/evidence/run-05-client-preparation/`.

---

## 7. Ações deliberadamente NÃO executadas

Em conformidade estrita com a política de governança e segurança:
- **Nenhum patching binário:** `Ragexe.exe` não foi modificado por hex edit, Nemo ou scripts.
- **Nenhuma alteração de GRF:** `data.grf` permaneceu intocado.
- **Nenhuma injeção de DLL:** Nenhuma DLL externa (`dinput.dll`, wrappers etc.) foi inserida.
- **Nenhum arquivo proprietário no Git:** Nenhum executável, DLL, GRF ou backup local foi adicionado ao versionamento.
- **Nenhum login no servidor:** O handshake de login permanece bloqueado até a etapa de execução controlada.
- **Nenhuma restauração do snapshot:** `GATE5-Baseline` foi preservado como ponto de rollback inicial.

---

## 8. Teste de sanidade da VM (Runbook de verificação)

Para validar o estado operacional da máquina virtual sem corromper o baseline:

1. Abrir o **VMware Workstation**.
2. Selecionar a máquina virtual **`FaithRO-GATE5-LAB`**.
3. Informar a senha de criptografia da VM para desbloquear o vTPM.
4. Acionar **`Power On`**.
5. Verificar se o Windows 11 inicializa normalmente até a tela de login / desktop.
6. Confirmar ausência de erros de integridade de disco ou do Windows Boot Manager.
7. Executar **`Shut Down`** limpo do sistema operacional guest.
8. **ATENÇÃO:** Não selecionar *Revert to Snapshot* a menos que haja intenção explícita de descarte de alterações.

---

## 9. Matriz obrigatória de gates

```text
GATE5_BASELINE_SNAPSHOT_PRESENT: PASS
GATE5_BASELINE_SNAPSHOT_NAME: PASS
GATE5_BASELINE_UNCHANGED: PASS
VM_STATE_RECONCILED: PASS
LAB_AUTOMATION_TESTS: PASS
PROJECT_VALIDATORS: PASS
CLIENT_FOUND: PASS
CLIENT_INVENTORIED: PASS
PROPRIETARY_ASSETS_COPIED_TO_REPO: NO
BINARY_PATCHING_PERFORMED: NO
GRF_MODIFICATION_PERFORMED: NO
ROLLBACK_AVAILABLE: PASS
EVIDENCE_CAPTURED: PASS
DOCUMENTATION_UPDATED: PASS
```

---

## 10. Riscos e mitigações

| Risco | Severidade | Mitigação aplicada |
|---|:---:|---|
| **R1 — Descarte acidental do snapshot baseline** | Crítica | Snapshot `GATE5-Baseline` validado fisicamente em `.vmsd` e `.vmsn`. Procedimento operacional proíbe expressamente reversão durante a preparação. |
| **R2 — Alteração concorrente do `.vmx` com VMware aberto** | Média | Encerramento gracioso prévio do processo `vmware.exe` e validação de desocupação de locks (`.lck`). |
| **R3 — Modificação não auditada de binários proprietários** | Crítica | Hashes de todos os arquivos em `C:\Gravity\Ragnarok` catalogados. Nenhuma ferramenta de patch executada nesta etapa. |
| **R4 — Vazamento de assets proprietários para o Git** | Crítica | `.local/` mantido no `.gitignore`. Auditoria `git status` e `git diff --check` sem assets binários ou segredos. |

---

## 11. Plano de rollback

### Nível 1 — Configuração textual
- Excluir a pasta `.local/gate5-lab/evidence/run-05-client-preparation/`.
- Reverter o commit de atualização do `gate5-common.ps1` via `git restore scripts/lab/gate5-common.ps1`.

### Nível 2 — Laboratório / Máquina Virtual
- Caso ocorra qualquer inconsistência ou corrupção no guest Windows 11 durante a preparação futura:
  - No VMware Workstation, selecionar a VM `FaithRO-GATE5-LAB`.
  - Acessar `Snapshot Manager`.
  - Selecionar `GATE5-Baseline` e clicar em **`Go To`** (Reverter).
  - O estado do laboratório retornará exatamente ao ponto imediatamente anterior a qualquer customização.

---

## 12. Próxima etapa recomendada

Avançar para a **ETAPA 2P-M-R3 — Preparação e Aplicação do Perfil Mínimo de Patches no Laboratório Isolado**:
1. Ativar o diretório `data\` no cliente e copiar o `clientinfo.xml` homologado.
2. Executar dentro da sandbox do laboratório a aplicação estrita do perfil mínimo homologado (`DataFolderFirst`, `CallKoreaClientInfo`, `LangType`).
3. Validar a inicialização do executável preparado e o handshake de rede com o login server (`129.121.46.11:6900`).
