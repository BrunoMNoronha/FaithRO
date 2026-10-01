# Preparação controlada do cliente e auditoria de laboratório GATE 5 (Etapa 2P-I)

> **Escopo:** registro técnico da auditoria do ecossistema WARP/GATE 5, reconciliação de integridade do executável oficial da Gravity, diagnóstico de prontidão do laboratório isolado de preparação de cliente, validação do perfil mínimo de patches e comprovação de conectividade de rede para o servidor FaithRO - Laos Deos. Nenhum binário proprietário, GRF, chave privada, segredo ou dado de jogador é registrado ou versionado.

---

## 1. Decisão humana e autorização formal

Em conformidade com a governança do projeto, foi registrada formalmente a seguinte decisão humana para esta etapa:

```text
HUMAN_DECISION:
APPROVED — GATE 5 CONTROLLED CLIENT PREPARATION

SCOPE:
LOCAL TESTING ONLY

DISTRIBUTION:
PROHIBITED

PROPRIETARY_ARTIFACTS_IN_GIT:
PROHIBITED
```

### Limites estritos da autorização:
- **Autorizado:** Produção e teste local e controlado de um executável derivado exclusivamente para testes do operador na estação de desenvolvimento.
- **Proibido expressamente:**
  - Distribuição pública ou privada;
  - Publicação em sites ou mídias;
  - Upload para o GitHub ou inclusão em Pull Requests;
  - Inclusão do executável em Releases do repositório;
  - Armazenamento de arquivos GRF ou assets proprietários da Gravity no Git;
  - Download de clientes ou patches binários de terceiros não auditados;
  - Modificação arbitrária do servidor ou quebra da integridade de baseline.

---

## 2. Cliente fonte autorizado (Preservação do original)

O executável oficial já existente na estação do operador foi inspecionado antes de qualquer manipulação e tratado como fonte imutável (read-only):

```text
SOURCE_CLIENT:          C:\Gravity\Ragnarok\Ragexe.exe
SOURCE_SIZE:            7.696.896 bytes
SOURCE_PE_OFFSET:       336 (0x150)
SOURCE_RAW_TIMESTAMP:   1636075878
SOURCE_PE_TIMESTAMP:    2021-11-05 01:31:18 UTC
SOURCE_ARCH:            x86 (IMAGE_FILE_MACHINE_I386 / PE32)
SOURCE_AUTHENTICODE:    Valid
SOURCE_SIGNER:          CN="GRAVITY Co., Ltd.", O="GRAVITY Co., Ltd.", L=Mapo-gu, S=Seoul, C=KR
SOURCE_SHA256:          8990A9A9CD6623E173BCC8B406A311AF32773EB881E539082126B768C14E95A0
SOURCE_INTEGRITY:       PASS
```

O hash SHA-256 e os metadados PE conferem perfeitamente com a evidência consolidada na etapa 2P-H ([Doc 50](50-primeiro-acesso-cliente.md)). Nenhuma ferramenta ou processo aplicou modificações sobre este binário.

---

## 3. Auditoria do ecossistema WARP / GATE 5 existente

A inspeção dos artefatos normativos e scripts do projeto identificou:

| Dimensão | Especificação canônica | Estado auditado nesta etapa |
|---|---|---|
| **GATE5_TOOLCHAIN** | Toolchain baseada no WARP (`Neo-Mind/WARP`, GPL-3.0, commit `9b1173e9e4e1`) conforme [Doc 28](28-decisao-ferramenta-preparacao-cliente.md). | A ferramenta `WARP.exe` ainda não foi materializada nem compilada na VM isolada. O orquestrador estático [`scripts/warp-audit-gate-05.py`](../scripts/warp-audit-gate-05.py) opera somente em modo fixture/validação com bloqueio fail-closed ativo (`REAL_EXECUTION_BLOCK_MESSAGE`). |
| **GATE5_ENTRYPOINT** | `scripts/lab/gate5-provision.ps1` (provisionamento da VM) e `scripts/lab/gate5-verify-baseline.ps1` (validação de baseline). | Automação testada com 178 PASS / 0 FAIL em fixtures sintéticas ([scripts/lab/test-gate5-lab-automation.ps1](../scripts/lab/test-gate5-lab-automation.ps1)), mas pendente de execução real final no guest. |
| **GATE5_INPUT_POLICY** | O cliente fonte `Ragexe.exe` original é estritamente imutável. Entradas no laboratório ocorrem via cópia descartável controlada. | Atendida: o cliente original permaneceu intocado. |
| **GATE5_OUTPUT_POLICY** | Binários derivados residem unicamente em diretórios locais não versionados na estação do operador (`.local/`). | Atendida: proibição absoluta de versionamento de PE/GRF no Git. |
| **GATE5_AUTHORIZATION_MODEL** | Decisão humana explícita prévia por etapa. | Atendida para a etapa 2P-I. |
| **GATE5_PATCH_PROFILE_MODEL** | Perfil estritamente mínimo e allowlisted para alcançar `LOGIN -> CHAR -> MAP`. | Especificado e catalogado (ver §4). |
| **GATE5_EVIDENCE_MODEL** | Registro em JSON estruturado com hashes SHA-256, timestamps UTC e saída sanitizada. | Atendido pelo pipeline do laboratório. |

---

## 4. Perfil de patches mínimo avaliado

Conforme a Regra de Minimalidade e a análise estática documentada em [`client/warp-audit/patch-selection.example.json`](../client/warp-audit/patch-selection.example.json) e no [Doc 28](28-decisao-ferramenta-preparacao-cliente.md), os patches candidatos foram avaliados:

| Patch Candidate | Finalidade | Requisito 1º Login | Risco / Impacto | Decisão |
|---|---|:---:|---|:---:|
| **`DataFolderFirst`** | Permite que o executável leia a pasta local `data\` antes de consultar o GRF. | **Sim** | Baixo (NOPs e ajustes de saltos condicionais em `g_readFolderFirst`). | **ENABLE** |
| **`CallKoreaClientInfo`** | Corrige `InitClientInfo` para chamar a rotina de leitura de `clientinfo.xml`. | **Sim** | Baixo (ajuste de switch/jmp para kRO). | **ENABLE** |
| **`RestoreClientInfo`** | Força a leitura do arquivo de configuração de rede customizado. | **Candidato** | Médio (avaliação de template). Deferido até validação do patch anterior. | **DEFER** |
| **`MultiGRFs`** | Suporte a múltiplos arquivos GRF externos. | Não | Baixo/Médio (reescreve rotina de carregamento via `GetProcAddress`). Desnecessário para teste mínimo. | **REJECT** |
| **`EnableDnsSupport`** | Resolução de nomes via DNS. | Não | Baixo/Médio (carrega `ws2_32.dll`). Desnecessário pois a conexão é por IP numérico. | **REJECT** |
| **`DisableProtect`** *(NoHShield/GameGuard)* | Desativa checagens de anticheat do cliente. | Não | Alto (desativação preventiva de segurança). Não autorizado por padrão. | **REJECT** |
| **`DisableEncr`** *(NoLoginEncr)* | Envio de credenciais em texto claro. | Não | Crítico (inseguro). Servidor rAthena homologado processa protocolo padrão. | **REJECT** |
| **`CustomDLL`** | Injeção de DLL externa na import table. | Não | Crítico (risco de cadeia de suprimentos). Expressamente proibido. | **REJECT** |
| **Patches cosméticos / QoL** | Custom window title, zoom, fontes, UI, cash shop. | Não | Risco de conflito e poluição de baseline. | **REJECT** |

### Política GameGuard:
```text
DISABLE_GAMEGUARD: NOT_AUTHORIZED_BY_DEFAULT
```
Nenhum bypass preventivo foi aplicado. Apenas se comprovado empiricamente que o GameGuard impede o startup do executável em ambiente local será aberto gate específico para classificação.

---

## 5. Reconciliação do laboratório GATE 5 (`FaithRO-GATE5-LAB`)

A inspeção física da máquina virtual em `C:\VMs\FaithRO-GATE5-LAB` e do estado em `.local\gate5-lab` revelou:

```text
LAB_DIRECTORY:          C:\VMs\FaithRO-GATE5-LAB
VM_VMX_PRESENT:         TRUE
VM_VMDK_PRESENT:        TRUE (38.815.793.152 bytes)
VM_POWER_STATE:         POWERED_OFF (0 VMs em execução no VMware Workstation)
VM_ENCRYPTION_STATE:    ENCRYPTED (exigência do vTPM 2.0; chave sob posse exclusiva do operador)
LAB_STATE:              PROVISIONAMENTO_INCOMPLETO
PROVISIONING_RUN:       run-02-clean-install (selada em .local\gate5-lab\evidence\run-02-clean-install\sealed.json)
FASES_CONCLUIDAS:       HOST_PREFLIGHT_OK, VMWARE_INSTALLED, ISO_VALIDATED, VM_CREATED, VCRUNTIME_READY, YARA_READY, RULESET_READY
FASES_AUSENTES:         GUEST_INSTALLED, GUEST_UPDATED, DEFENDER_READY, SANITIZED, ISOLATED, SNAPSHOT_CREATED, BASELINE_VERIFIED
SNAPSHOT_BASELINE:      AUSENTE (BASELINE_GATE5_ISOLATED não existe)
TOOLCHAIN_STATE:        NOT_MATERIALIZED (WARP.exe não compilado/materializado na VM)
INPUT_CHANNEL:          ISO virtual SATA (gate5-unattend.iso)
OUTPUT_CHANNEL:         Sink serial desacoplado por boot (boot-NNNN.txt)
```

### Diagnóstico de bloqueio:
A máquina virtual do laboratório não concluiu o ciclo completo de instalação limpa e isolamento até a geração do snapshot imutável `BASELINE_GATE5_ISOLATED`. Conforme a **Regra Central** do projeto:
1. É estritamente proibido realizar patch manual de bytes;
2. É estritamente proibido usar editores hexadecimais arbitrários;
3. É estritamente proibido baixar patchers binários externos da internet.

Como a ferramenta autorizada (`WARP`) depende do laboratório aprovado e este encontra-se pendente de conclusão do provisionamento, a etapa falha de forma segura e determinística (*fail-closed*).

---

## 6. Configuração ClientInfo FaithRO (Referência de rede)

Arquivo preparado conforme o template [`client/templates/clientinfo.xml.example`](../client/templates/clientinfo.xml.example) para ser consumido na pasta `data\`:

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

---

## 7. Testes empíricos de rede e baseline server-side

### 7.1 Firewall e Conectividade TCP (H1)
- **IP público do operador:** `189.6.11.60` (conferido via API externa).
- **Regras UFW na VPS (`129.121.46.11`):** Regras 2, 3 e 4 ativas liberando especificamente `189.6.11.60` nas portas TCP `6900`, `6121` e `5121`. Porta `3306` (MariaDB) mantida isolada a `127.0.0.1`.
- **Validação TCP local:**
  - `6900/tcp` (Login): `TcpTestSucceeded: True`
  - `6121/tcp` (Char): `TcpTestSucceeded: True`
  - `5121/tcp` (Map): `TcpTestSucceeded: True`
  - **Resultado H1_TCP:** `PASS`.

### 7.2 Saúde do servidor (VPS)
```text
mariadb.service:       active (running)
faithro-login.service: active (running)
faithro-char.service:  active (running)
faithro-map.service:   active (running)
Erros nos logs:        Zero segfaults, zero asserts, zero SQL errors, zero desconexões anômalas
```

---

## 8. Matriz obrigatória de resultados

```text
GATE5_LAB:                INCOMPLETE (run-02 selada em GUEST_PHASE_FAILED_INSTALLWAIT)
SOURCE_INTEGRITY:         PASS (C:\Gravity\Ragnarok\Ragexe.exe inalterado)
PATCH_TOOL:               NOT_MATERIALIZED (WARP.exe não disponível em runtime)
PATCH_PROFILE:            EVALUATED_MINIMAL (DataFolderFirst, CallKoreaClientInfo)
PATCH_PROFILE_MINIMAL:    CONFIRMED_MINIMAL (Patches sensíveis e cosméticos rejeitados)
OUTPUT_VALIDATION:        NOT_APPLICABLE (nenhum executável derivado gerado sem ferramenta auditada)
CLIENT_START:             NOT_REACHED

H1_TCP:                   PASS (6900, 6121, 5121 acessíveis a partir de 189.6.11.60)
H2_PACKET_HANDSHAKE:      NOT_REACHED (bloqueado pela ausência de executável preparado)
H3_AUTH:                  NOT_REACHED
H4_LOGIN_TO_CHAR:         NOT_REACHED
H5_CHARACTER_SELECTION:   NOT_REACHED
H6_CHAR_TO_MAP:           NOT_REACHED
H7_INGAME:                NOT_REACHED

SERVICES_AFTER_TEST:      ACTIVE_HEALTHY
SERVER_ERRORS:            NONE
```

---

## 9. Classificação de falhas

- **Camadas primárias de bloqueio:**
  - **`L1 LAB`** — O laboratório isolado `FaithRO-GATE5-LAB` não atingiu o estado `BASELINE_GATE5_ISOLATED`.
  - **`L2 PATCH_TOOL`** — Não há binário ou automação do patcher WARP homologada e pronta para execução segura fora da sandbox do laboratório.

---

## 10. Riscos e mitigações

| Risco | Severidade | Mitigação aplicada |
|---|:---:|---|
| **R1 — Alteração do cliente original** | Crítica | O arquivo `C:\Gravity\Ragnarok\Ragexe.exe` foi auditado e tratado como read-only. `SOURCE_INTEGRITY: PASS`. |
| **R2 — Patch overreach / contorno manual** | Alta | Aplicação estrita da Regra Central: proibição de editores hexadecimais manuais e rejeição de patches não essenciais. |
| **R3 — Artefato proprietário no Git** | Crítica | Nenhuma cópia binária ou modificada foi introduzida no repositório. O diff contém exclusivamente documentação markdown. |
| **R4 — Mascaramento de mismatch de protocolo** | Média | O PACKETVER do servidor permanece fixo em `20211103` e o cliente em `2021-11-05`. Nenhuma mutação server-side foi realizada. |
| **R5 — Bypass inadvertido de segurança do cliente** | Alta | GameGuard mantido sob status `NOT_AUTHORIZED_BY_DEFAULT`. |

---

## 11. Rollback

- **Cliente:** Nenhum derivado foi gerado. O executável fonte permanece intacto.
- **Laboratório:** Mantido no estado selado atual sem intervenções destrutivas.
- **Servidor e Firewall:** Nenhuma alteração de configuração na VPS ou no UFW; integridade de baseline preservada.
- **Git:** Reversão padrão via `git revert` do commit desta etapa, se necessário.

---

## 12. Decisão final

```text
BLOCKED — GATE 5 LAB NOT READY
```

---

## 13. Próxima ação recomendada

1. Concluir o autoprovisionamento do laboratório GATE 5 (`scripts/lab/gate5-provision.ps1`) através da intervenção humana na interface do VMware Workstation (desbloqueio da VM criptografada pelo operador), avançando pelas fases `GUEST_INSTALLED` até `BASELINE_GATE5_ISOLATED`.
2. Validar o laboratório isolado com `scripts/lab/gate5-verify-baseline.ps1`.
3. Materializar e auditar a ferramenta WARP dentro do laboratório aprovado conforme a trilha do WARP audit.
4. Retomar a etapa de preparação controlada do cliente para execução dos testes H2 a H7.
