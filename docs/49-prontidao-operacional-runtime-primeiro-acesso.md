# Prontidão operacional do runtime para o primeiro acesso (Etapa 2P-F)

> **Escopo:** registro técnico de homologação e validação da prontidão de runtime do servidor FaithRO - Laos Deos para o primeiro acesso real. Reconciliação completa entre repositório local, repositório remoto, VPS de produção e serviços de banco e emulador rAthena. Nenhum segredo ou credencial é exposto neste documento.

## 1. Objetivo

Atestar o estado operacional do runtime na VPS (`faithro-vps`), garantindo que MariaDB, login-server, char-server e map-server estejam íntegros, em execução contínua, comunicando-se corretamente entre si e prontos para receber a primeira conexão do cliente sem bloqueios ou falhas de configuração.

## 2. Estado de infraestrutura e serviços (VPS)

- **Ambiente:** Ubuntu 22.04.5 LTS (kernel `6.8.0-136-generic`)
- **Recursos:** 1 vCPU, 1.9 GiB RAM, 2.0 GiB Swap, disco 49 GB (37 GB livres)
- **IP público:** `129.121.46.11`
- **Diretório da instalação:** `/opt/faithro/rathena`
- **Commit rAthena instalado:** `7f080871c8b3bbe7a79027194633201c63422ee1`
- **Uptime dos serviços:** contínuo e estável (> 20 dias ininterruptos)

### Matriz de serviços

| Serviço | Unidade systemd | Binário | Estado | Porta | Escuta | Integração |
|---|---|---|---|---:|---|---|
| **MariaDB** | `mariadb.service` | `/usr/sbin/mariadbd` | `active (running)` | 3306/tcp | `127.0.0.1:3306` (local) | Operacional; autenticação de `faithro_app` OK |
| **Login Server** | `faithro-login.service` | `/opt/faithro/rathena/login-server` | `active (running)` | 6900/tcp | `0.0.0.0:6900` | Operacional; conectado ao MariaDB |
| **Char Server** | `faithro-char.service` | `/opt/faithro/rathena/char-server` | `active (running)` | 6121/tcp | `0.0.0.0:6121` | Operacional; autenticado no login-server (`faithro_srv`) e MariaDB |
| **Map Server** | `faithro-map.service` | `/opt/faithro/rathena/map-server` | `active (running)` | 5121/tcp | `0.0.0.0:5121` | Operacional; 1265 mapas carregados; conectado ao char-server |

## 3. Configurações de jogo e mecânica

- **Modo:** Pre-Renewal (sem 3ª classes).
- **Base Level Cap:** 255 (`db/import/job_stats.yml`).
- **Atributo natural individual máximo:** 185 (`conf/import/battle_conf.txt`).
- **ASPD máxima:** 197 (`conf/import/battle_conf.txt`).
- **PACKETVER:** 20211103 (Pre-Renewal com macro `PACKETVER_RE` automática).
- **Obfuscação de pacotes:** chaves zero (`0x0, 0x0, 0x0`), desabilitada por padrão para `PACKETVER > 20180307`.
- **Criação de conta:** `new_account: no` (auto-criação via sufixos `_M/_F` desabilitada por política de segurança).

## 4. Segurança e firewall

- O MariaDB está restrito estritamente a `127.0.0.1:3306`, não acessível externamente.
- O firewall `ufw` está ativo (`deny incoming` por padrão):
  - `22022/tcp` (SSH): liberado `Anywhere` (autenticação estrita por chave SSH).
  - `6900/tcp` (Login): liberado para IP autorizado.
  - `6121/tcp` (Char): liberado para IP autorizado.
  - `5121/tcp` (Map): liberado para IP autorizado.

## 5. Perfil canônico de conexão do cliente

```text
CLIENT_CONNECTION_PROFILE
server_name: FaithRO
login_host: 129.121.46.11
login_port: 6900
char_port: 6121
map_port: 5121
packetver: 20211103
expected_client_date: 2021-11-03 / 2021-11-05 (Ragexe)
packet_obfuscation: disabled (zero keys)
mode: Pre-Renewal (sem 3ª classes)
level_cap_base: 255
level_cap_stat: 185
max_aspd: 197
new_account: no (gerenciada via banco)
notes: Servidor em baseline operacional pronta para teste de login.
```

## 6. Procedimento operacional (Lifecycle)

- **Iniciar stack:** `sudo systemctl start faithro-login faithro-char faithro-map`
- **Parar stack:** `sudo systemctl stop faithro-map faithro-char faithro-login`
- **Reiniciar stack:** `sudo systemctl restart faithro-login` (o restart se propaga para char e map pelas diretivas `Requires=`)
- **Verificar status:** `sudo systemctl status faithro-login faithro-char faithro-map mariadb`
- **Verificar logs:**
  - Login: `sudo journalctl -u faithro-login.service -n 50 --no-pager`
  - Char: `sudo journalctl -u faithro-char.service -n 50 --no-pager`
  - Map: `sudo journalctl -u faithro-map.service -n 50 --no-pager`
