# Primeiro acesso do cliente e reconciliação de runtime (Etapas 2P-G e 2P-H)

> **Escopo:** registro técnico de reconciliação de drift de runtime (Base Level 185 e Packet Obfuscation), localização do executável autorizado na estação do operador, validação de conectividade de rede e firewall, e diagnóstico do mecanismo de configuração de conexão para o primeiro acesso ao FaithRO - Laos Deos. Nenhum binário proprietário, GRF, chave privada, segredo ou dado de jogador é registrado ou distribuído.

---

## 1. Histórico e contexto inicial (Etapa 2P-G)

Na etapa 2P-G, foi conduzido o processo de reconciliação de drift do servidor rAthena (`7f080871c8b3bbe7a79027194633201c63422ee1`):
1. **Base Level 185:** Reconciliado de 255 para 185 em `deploy/rathena-overlay/db/import/job_stats.yml` e na VPS (`/opt/faithro/rathena/db/import/job_stats.yml`), com validador determinístico [`scripts/validate-progression-overrides.py`](../scripts/validate-progression-overrides.py) aprovado.
2. **Packet Obfuscation:** Classificado como `ZERO_KEY_NO_EFFECT` (chaves zero, pacotes em formato plano sem impacto de criptografia).
3. **PACKETVER do servidor:** `20211103` (Pre-Renewal com macro `PACKETVER_RE` automática no intervalo `[20200902, 20211118]`).
4. **Desfecho 2P-G:** Encerrou com `BLOCKED — AUTHORIZED CLIENT NOT PRESENT` pois a busca havia sido restrita ao repositório git do workspace, onde executáveis proprietários não são versionados por política de segurança.

---

## 2. Validação empírica do primeiro acesso e localização do cliente (Etapa 2P-H)

- **Data de execução:** 2026-09-03
- **Operador / Estação:** Windows Workstation do operador
- **Alvo:** Servidor FaithRO na VPS (`129.121.46.11`)

### 2.1 Localização do cliente autorizado na estação

A busca em diretórios locais na estação do operador localizou a instalação oficial de cliente em:

```text
CLIENT_PRESENT: YES
CLIENT_ROOT: C:\Gravity\Ragnarok
CLIENT_EXECUTABLE_NAME: Ragexe.exe
CLIENT_EXECUTABLE_DATE: 2021-11-05 01:31:18 UTC (PE link timestamp)
CLIENT_ARCH: x86 (IMAGE_FILE_MACHINE_I386 / PE32)
CLIENT_AUTHENTICODE: Válida — "GRAVITY Co., Ltd." (binário oficial limpo, não modificado)
CLIENT_SHA256: 8990A9A9CD6623E173BCC8B406A311AF32773EB881E539082126B768C14E95A0
CLIENT_ORIGIN: Instalador oficial RAG_SETUP_211105 (ver Doc 29 §2)
```

**Resultado do GATE 1:** `PASS` (`CLIENT_PRESENT: YES`).

---

### 2.2 Compatibilidade técnica de protocolo

- **Target do servidor:** `PACKETVER = 20211103`
- **Build do executável:** `2021-11-05 01:31:18 UTC`
- **Análise do rAthena (`7f080871c`):** Conforme demonstrado no [Doc 29](29-compatibilidade-cliente-2021-11-05-packetver.md), todo o intervalo `[20211103, 20211118]` no ramo RE compartilha idênticas estruturas de pacote e o mesmo shuffle de opcodes (guards chaveados em `PACKETVER_RE_NUM >= 20211103`).
- **Classificação de compatibilidade:** `PROBABLY_COMPATIBLE`.

---

### 2.3 Mecanismo de configuração de conexão (Fase E)

A inspeção detalhada da instalação local em `C:\Gravity\Ragnarok` determinou:

```text
CLIENTINFO_SOURCE: NONE_IDENTIFIED
CLIENTINFO_LOAD_PATH: NOT_CONFIGURED
CONNECTION_CURRENT_HOST: ropatch.gnjoy.com / kRO oficial (hardcoded / patch client)
CONNECTION_CURRENT_PORT: oficial kRO
```

- **Diagnóstico:** O executável localizado é o binário original limpo da Gravity com assinatura digital válida. Ele **não lê** arquivos externos `data\clientinfo.xml` nem arquivos de configuração em texto da pasta local; seu fluxo nativo aponta para a infraestrutura coreana da Gravity e depende de GameGuard (`GameGuard.des`, `v3hunt.dll`).
- **Restrição de segurança:** A preparação do executável para aceitar conexão externa (ex.: patches `DataFolderFirst` e `RestoreClientInfo` via WARP) exige modificação de executável proprietário (hex/diff), o que é expressamente **proibido** nesta etapa e depende da trilha de autorização e laboratório do WARP (Docs 28, 46, 47 e 48).
- **Classificação:** Bloqueio em `L2 CLIENT_CONFIGURATION`.

---

### 2.4 IP público do operador e Firewall (Fase F e Gate 2)

- **IP público do operador detectado:** `189.6.11.60`
- **IP anterior nas regras UFW:** `179.255.39.153` (`MISMATCH`)
- **Ação executada no firewall da VPS:**
  - Adicionadas regras específicas para as portas do jogo (`6900/tcp`, `6121/tcp`, `5121/tcp`) a partir do IP `189.6.11.60`.
  - Removidas as regras obsoletas de `179.255.39.153`.
  - Mantidas as políticas `default deny incoming` e restrição estrita do MariaDB a `127.0.0.1:3306`.
  - Status pós-mudança: `MATCH`.

---

### 2.5 Testes de conectividade de rede (Checkpoints H1 a H7)

| Checkpoint | Alvo | Resultado | Evidência empírica |
|---|---|:---:|---|
| **H1 — TCP (Login)** | `129.121.46.11:6900` | **PASS** | `TcpTestSucceeded: True` da estação; VPS log: `login-server: Closed connection from '189.6.11.60'`. |
| **H1 — TCP (Char)** | `129.121.46.11:6121` | **PASS** | `TcpTestSucceeded: True` da estação. |
| **H1 — TCP (Map)** | `129.121.46.11:5121` | **PASS** | `TcpTestSucceeded: True` da estação; VPS log: `map-server: Closed connection from '189.6.11.60'`. |
| **H2 — Packet Handshake** | Login protocol | *NOT REACHED* | Bloqueado pelo mecanismo de configuração do cliente (L2). |
| **H3 — Autenticação** | Credenciais homologação | *NOT REACHED* | Bloqueado pelo mecanismo de configuração do cliente (L2). |
| **H4 — Login → Char** | Seleção de personagem | *NOT REACHED* | Bloqueado pelo mecanismo de configuração do cliente (L2). |
| **H5 — Seleção de Personagem** | Carregamento de char | *NOT REACHED* | Bloqueado pelo mecanismo de configuração do cliente (L2). |
| **H6 — Char → Map** | Handoff de mapa | *NOT REACHED* | Bloqueado pelo mecanismo de configuração do cliente (L2). |
| **H7 — In-Game** | Movimentação / UI | *NOT REACHED* | Bloqueado pelo mecanismo de configuração do cliente (L2). |

---

### 2.6 Saúde do runtime após o teste

```text
mariadb.service:       active (running)
faithro-login.service: active (running)
faithro-char.service:  active (running)
faithro-map.service:   active (running)
Portas em escuta:      6900, 6121, 5121 em 0.0.0.0; 3306 em 127.0.0.1
Erros de servidor:     Nenhum (zero segfaults, zero asserts, zero SQL errors)
```

---

## 3. Matriz de resultado consolidada

```text
CLIENT_PRESENT:           YES (C:\Gravity\Ragnarok\Ragexe.exe)
CLIENT_COMPATIBILITY:     PROBABLY_COMPATIBLE (PACKETVER 20211103)
OPERATOR_PUBLIC_IP_MATCH: MATCH (189.6.11.60 atualizado no UFW)
H1_TCP:                   PASS (6900, 6121, 5121 alcançáveis e respondendo)
H2_PACKET_HANDSHAKE:      NOT_REACHED
H3_AUTH:                  NOT_REACHED
H4_LOGIN_TO_CHAR:         NOT_REACHED
H5_CHARACTER_SELECTION:   NOT_REACHED
H6_CHAR_TO_MAP:           NOT_REACHED
H7_INGAME:                NOT_REACHED
SERVICES_AFTER_TEST:      ACTIVE_HEALTHY
SERVER_ERRORS:            NONE
```

---

## 4. Classificação de falha

- **Camada primária de bloqueio:** **`L2 CLIENT_CONFIGURATION`**
- **Justificativa:** O cliente legítimo e compatível está fisicamente presente na estação do operador (`CLIENT_PRESENT: YES`) e a camada de rede/firewall está comprovadamente operacional (`H1_TCP: PASS`), mas o binário é original da Gravity sem mecanismo local autorizado para receber o apontamento de `address` e `port` do FaithRO sem alteração de executável proprietário por hex patch.

---

## 5. Decisão

```text
BLOCKED — CLIENT CONFIGURATION METHOD NOT AUTHORIZED
```

---

## 6. Próxima ação recomendada

Para avançar com segurança e conformidade para a validação empírica completa dos checkpoints H2 a H7:
1. Concluir a execução do laboratório isolado do WARP (**GATE 5** — já especificado e autoprovisionado no PR #75), sob autorização humana explícita.
2. Gerar a cópia de laboratório preparada do `Ragexe.exe` aplicando estritamente os patches mínimos necessários (`DataFolderFirst`, `RestoreClientInfo`, `LangType`).
3. Executar o handshake de login real (H2 a H7) utilizando o executável de laboratório preparado e as credenciais de homologação já existentes.

---

## 7. Rollback

- **Cliente local:** Nenhum arquivo local foi alterado; executável preservado intacto.
- **Firewall:** Se necessário reverter a regra de IP do operador, restaurar `179.255.39.153` no UFW da VPS.
- **Servidor:** Nenhum arquivo ou configuração do servidor rAthena foi alterado nesta etapa. Base Level 185 mantido como baseline autoritativa.
- **Git:** Reverter o commit desta etapa via `git revert`.
