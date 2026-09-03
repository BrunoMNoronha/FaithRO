# Primeiro acesso do cliente e reconciliação de runtime (Etapa 2P-G)

> **Escopo:** registro técnico de reconciliação de drift de runtime (Base Level 185 e Packet Obfuscation) e prontidão para o handshake de login do cliente no FaithRO - Laos Deos. Nenhum binário proprietário, GRF, chave privada, segredo ou dado de jogador é registrado ou distribuído.

## 1. Objetivo

Conduzir o processo de reconciliação de drift do servidor rAthena (`7f080871c`), reconfirmar empiricamente o comportamento de PACKETVER e de Packet Obfuscation, alinhar o limite de Base Level para 185 sem 3ª classe, e validar a prontidão server-side para o primeiro acesso do cliente autorizado.

## 2. Estado inicial

- **VPS:** Ubuntu 22.04.5 LTS (`faithro-vps`), 1 vCPU, 2 GB RAM, 50 GB disco.
- **MariaDB:** Ativo em `127.0.0.1:3306` com databases `faithro` e `faithro_log`.
- **Serviços de jogo:** `faithro-login.service` (6900/tcp), `faithro-char.service` (6121/tcp) e `faithro-map.service` (5121/tcp) ativos e integrados.
- **Uptime dos serviços:** Estável (> 20 dias).

## 3. Reconciliação de drift

### 3.1 Base Level 255 × Requisito FaithRO 185

- **Diagnóstico:** A configuração versionada em `deploy/rathena-overlay/db/import/job_stats.yml` e na VPS continha `MaxBaseLevel: 255` herdada de proposta preliminar de expansão. O requisito oficial do FaithRO estabelece Base Level máximo de 185 para todas as classes sem 3ª classe.
- **Ação executada:**
  - Alteração de `MaxBaseLevel: 255` para `MaxBaseLevel: 185` nos dois grupos de classes (classes não-trans e classes trans) em `deploy/rathena-overlay/db/import/job_stats.yml` e em `/opt/faithro/rathena/db/import/job_stats.yml` na VPS.
  - Atualização do validador determinístico [`scripts/validate-progression-overrides.py`](../scripts/validate-progression-overrides.py) para exigir estritamente `MaxBaseLevel == 185` em todos os blocos de classes.
  - Reinício controlado do `faithro-map.service` na VPS com recarga limpa das tabelas de EXP e confirmação de inicialização normal.

### 3.2 Packet Obfuscation

- **Diagnóstico:** O startup do map-server emite `Packet Obfuscation: Enabled. Keys: 0x00000000, 0x00000000, 0x00000000`.
- **Análise do código-fonte (`7f080871c`):**
  - Em `src/config/packets.hpp`: `#define PACKET_OBFUSCATION` é ativado para `PACKETVER >= 20110817`.
  - Em `src/map/clif_obfuscation.hpp`: Para `PACKETVER > 20180307`, as chaves oficiais são `#define packet_keys(0x00000000, 0x00000000, 0x00000000)`.
  - Em `src/map/clif.cpp`: A operação de decodificação `cmd = (cmd ^ ((((0 * 0) + 0) >> 16) & 0x7FFF))` resulta em `cmd ^ 0 == cmd` (transformação identidade / no-op).
- **Classificação técnica:** **`ZERO_KEY_NO_EFFECT`** (macro de compilação ativada no código, mas operação matemática nula devido às chaves zero, transmitindo pacotes em formato plano/não-obfustado, compatível com o cliente pós-2018).

## 4. PACKETVER comprovado

- **PACKETVER do servidor:** `20211103`
- **Macro interna:** `PACKETVER_RE` ativada automaticamente pelo rAthena no intervalo `[20200902, 20211118]`.
- **Compatibilidade do cliente 2021-11-05:** `PROVÁVEL` (conforme documentado em `docs/29`, toda a janela `[20211103, 20211118]` compartilha as mesmas estruturas de pacotes e shuffle de pacotes no commit `7f080871c`).

## 5. Perfil de conexão do cliente

```text
CLIENT_CONNECTION_PROFILE
server_name: FaithRO
login_host: 129.121.46.11
login_port: 6900
char_port: 6121
map_port: 5121
packetver: 20211103
expected_client_date: 2021-11-03 / 2021-11-05 (Ragexe)
packet_obfuscation: ZERO_KEY_NO_EFFECT (chaves zero, pacotes planos)
mode: Pre-Renewal (sem 3ª classes)
level_cap_base: 185
level_cap_stat: 185
max_aspd: 197
new_account: no (contas gerenciadas via MariaDB)
```

## 6. Estado do cliente no workspace

- Em estrito cumprimento à política de não versionar nem distribuir executáveis proprietários ou assets com copyright Gravity (AGENTS.md Regra 4 e Docs 16/29), o repositório contém apenas modelos de configuração (`client/templates/clientinfo.xml.example`) e documentação.
- Nenhum cliente proprietário modificado/hexado foi baixado ou executado neste ambiente automatizado.

## 7. Testes executados

- `python scripts/validate-progression-overrides.py`: `PASS` (Base EXP: 157, Stat points: 55, Cap Base: 185, Stat: 185, ASPD: 197).
- `python scripts/validate-warp-audit.py`: `PASS`.
- `git diff --check`: `PASS`.
- `systemctl is-active mariadb faithro-login faithro-char faithro-map`: `PASS` (todos `active`).
- `ss -lntp`: `PASS` (portas 6900, 6121, 5121 escutando).
- Map server reload: `PASS` (1265 mapas, 13036 NPCs, conexão com char-server restabelecida com sucesso).

## 8. Rollback

- Reverter `deploy/rathena-overlay/db/import/job_stats.yml` e `scripts/validate-progression-overrides.py` via Git (`git revert`).
- Na VPS, restaurar o arquivo `job_stats.yml` anterior e executar `sudo systemctl restart faithro-map.service`.
