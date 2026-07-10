# Serviços systemd do rAthena — FaithRO

> **Escopo:** documento de auditoria e operação. A inspeção que originou este
> documento foi **somente leitura** na VPS: nenhum serviço foi iniciado,
> parado, reiniciado, habilitado, desabilitado ou reconfigurado. Nenhum
> arquivo de unidade, firewall, banco de dados ou binário foi alterado.

## Objetivo

Documentar o estado real dos serviços systemd do rAthena usados pelo FaithRO -
Laos Deos, confirmado por inspeção direta na VPS, permitindo que qualquer
operador identifique as unidades corretas, os binários executados, o usuário
e diretório de trabalho, consulte estado e logs com segurança, e execute
start/stop/restart na ordem correta — sem depender do histórico do chat.

## Estado verificado

- **Data da auditoria:** 2026-07-10.
- **Ambiente:** VPS de produção/testes do FaithRO, Ubuntu 22.04.5 LTS
  (kernel `6.8.0-124-generic`), acessada via `<HOST-VPS>` como
  `<USUARIO-OPERACIONAL>` na porta `<PORTA-SSH>` (SSH já documentado como
  `22022/tcp` em [04-operacao-vps.md](04-operacao-vps.md)).
- **Commit do rAthena instalado:** `7f080871c8b3bbe7a79027194633201c63422ee1`
  (abreviado `7f080871c`) — **idêntico** ao commit upstream de referência já
  registrado em [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md)
  e [10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md).
  Isso resolve a pendência "commit instalado na VPS — não verificado" citada
  naqueles documentos: **confirmado nesta auditoria**.
- **Working tree do checkout `/opt/faithro/rathena`:** limpo, branch `master`,
  sincronizado com `origin/master` (`git status --short --branch` sem
  alterações pendentes). Nenhuma modificação local foi encontrada.
- **Unidades encontradas:** `faithro-login.service`, `faithro-char.service`,
  `faithro-map.service` — os três nomes já citados como observação histórica
  em [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md) estão
  **confirmados formalmente** por esta auditoria.
- **Binários presentes em `/opt/faithro/rathena`:** `login-server`,
  `char-server`, `map-server` e **também `web-server`** (os quatro existem,
  são arquivos regulares, permissão `775`, proprietário `faithro:faithro`).
- **Estados:** as três unidades de jogo estão `enabled` e `active (running)`,
  sem falhas (`is-failed` não reporta `failed`).
- **Portas confirmadas:** login `6900/tcp`, char `6121/tcp`, map `5121/tcp`,
  todas vinculadas a todas as interfaces (`0.0.0.0`) no nível do processo, mas
  restringidas por firewall a um único IP autorizado (ver
  [Firewall](#firewall)).
- **Web server:** binário presente e executável, código com
  `WEB_SERVER_ENABLE` verdadeiro para o baseline, **porém sem unidade systemd
  implantada, sem processo em execução e sem porta em escuta**. Configuração
  de override (`conf/import/web_conf.txt`) existe mas está vazia. Ver detalhes
  na seção [Web server](#web-server).

## Arquivos e componentes afetados

Esta tarefa é **read-only** na VPS: nenhum componente operacional foi
alterado. Os seguintes componentes foram apenas **inspecionados**:

- Checkout git em `/opt/faithro/rathena` (estado, commit, branch).
- Binários `login-server`, `char-server`, `map-server`, `web-server`
  (existência e metadados, sem execução).
- Unidades systemd `faithro-login.service`, `faithro-char.service`,
  `faithro-map.service` (arquivo, propriedades, estado, logs recentes).
- Firewall (`ufw status verbose`, somente leitura).
- Portas em escuta (`ss -lntp`, somente leitura).
- Arquivos de configuração do web server (apenas `stat`, sem leitura de
  conteúdo sensível).

No repositório, somente arquivos Markdown foram criados ou atualizados.

## Mapa de serviços

| Função | Unidade confirmada | Binário | Usuário | Diretório | Enabled | Active | Porta |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Login | `faithro-login.service` | `/opt/faithro/rathena/login-server` | `faithro` | `/opt/faithro/rathena` | enabled | active (running) | `6900/tcp` |
| Char | `faithro-char.service` | `/opt/faithro/rathena/char-server` | `faithro` | `/opt/faithro/rathena` | enabled | active (running) | `6121/tcp` |
| Map | `faithro-map.service` | `/opt/faithro/rathena/map-server` | `faithro` | `/opt/faithro/rathena` | enabled | active (running) | `5121/tcp` |
| Web | não implantada (ver [Web server](#web-server)) | `/opt/faithro/rathena/web-server` (presente, não executado) | — | — | — | inactive (sem processo) | não escutando |

## Dependências e ordem

Ordem confirmada diretamente no conteúdo das unidades (`systemctl cat`), não
inferida:

- **Dependência declarada** (`Requires=` / `After=`):
  - `faithro-char.service` declara `Requires=faithro-login.service` e
    `After=faithro-login.service`.
  - `faithro-map.service` declara `Requires=faithro-char.service` e
    `After=faithro-char.service`.
  - `faithro-login.service` declara apenas `Wants=network-online.target` e
    `After=network-online.target mariadb.service` (sem depender das outras
    duas unidades).
- **Ordem operacional recomendada, consistente com as dependências
  declaradas:** login → char → map (start); map → char → login (stop).
- **Comportamento observado:** as três unidades foram iniciadas no mesmo
  evento de boot, com PIDs sequenciais (806, 811, 812), compatível com a
  ordem declarada.

Nenhuma relação `Requires=`/`After=` foi inventada; todas as citadas acima
constam literalmente no `systemctl cat` de cada unidade.

## Conteúdo confirmado das unidades

Revisado previamente: nenhuma das três unidades contém `Environment=`,
credenciais, tokens ou parâmetros sensíveis. As diretivas abaixo foram
copiadas com segurança.

### `faithro-login.service`

```ini
[Unit]
Description=FaithRO rAthena Login Server
Documentation=https://github.com/rathena/rathena
Wants=network-online.target
After=network-online.target mariadb.service

[Service]
Type=simple
User=faithro
Group=faithro
WorkingDirectory=/opt/faithro/rathena
ExecStart=/opt/faithro/rathena/login-server
Restart=on-failure
RestartSec=5
TimeoutStopSec=30
KillSignal=SIGTERM
LimitNOFILE=65535
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### `faithro-char.service`

```ini
[Unit]
Description=FaithRO rAthena Character Server
Documentation=https://github.com/rathena/rathena
Requires=faithro-login.service
After=faithro-login.service

[Service]
Type=simple
User=faithro
Group=faithro
WorkingDirectory=/opt/faithro/rathena
ExecStart=/opt/faithro/rathena/char-server
Restart=on-failure
RestartSec=5
TimeoutStopSec=30
KillSignal=SIGTERM
LimitNOFILE=65535
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### `faithro-map.service`

```ini
[Unit]
Description=FaithRO rAthena Map Server
Documentation=https://github.com/rathena/rathena
Requires=faithro-char.service
After=faithro-char.service

[Service]
Type=simple
User=faithro
Group=faithro
WorkingDirectory=/opt/faithro/rathena
ExecStart=/opt/faithro/rathena/map-server
Restart=on-failure
RestartSec=5
TimeoutStopSec=60
KillSignal=SIGTERM
LimitNOFILE=65535
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

## Comandos de descoberta

Use estes comandos antes de qualquer operação, para confirmar que os nomes
das unidades continuam válidos no ambiente (podem mudar em reinstalações
futuras):

```bash
systemctl list-unit-files --type=service --no-pager |
  grep -Ei 'faithro|rathena|login|char|map|web'

systemctl list-units --type=service --all --no-pager |
  grep -Ei 'faithro|rathena|login|char|map|web'

find /etc/systemd/system /lib/systemd/system \
  -maxdepth 2 -type f \
  \( -iname '*faithro*.service' -o -iname '*rathena*.service' \) \
  -print 2>/dev/null
```

## Consulta de estado

```bash
systemctl is-enabled faithro-login.service faithro-char.service faithro-map.service
systemctl is-active  faithro-login.service faithro-char.service faithro-map.service
systemctl is-failed  faithro-login.service faithro-char.service faithro-map.service
systemctl status faithro-login.service --no-pager --lines=10
systemctl status faithro-char.service  --no-pager --lines=10
systemctl status faithro-map.service   --no-pager --lines=10
```

## Consulta de logs

Use sempre uma janela curta e revise o conteúdo antes de compartilhar —
nunca cole saída bruta de log em issues, PRs ou chats públicos:

```bash
sudo journalctl -u faithro-login.service --since '-10 minutes' --no-pager --lines=50
sudo journalctl -u faithro-char.service  --since '-10 minutes' --no-pager --lines=50
sudo journalctl -u faithro-map.service   --since '-10 minutes' --no-pager --lines=50
```

Na auditoria de 2026-07-10, a janela de 10 minutos não apresentou nenhuma
entrada nova para as três unidades (serviços estáveis, sem reinício recente,
sem mensagem de erro).

## Validação das unidades

Executado com `systemd-analyze verify <caminho-da-unidade>` para as três
unidades, somente para validação sintática (nenhuma correção foi aplicada):

- Nenhum erro ou warning foi reportado especificamente para
  `faithro-login.service`, `faithro-char.service` ou `faithro-map.service`.
- O comando emitiu duas mensagens genéricas do sistema, não relacionadas ao
  FaithRO: permissão negada ao ler `netplan-ovs-cleanup.service` (unidade de
  rede do sistema) e uma chave desconhecida (`RestartMode`) em
  `snapd.service` — ambas unidades de terceiros presentes no SO, fora do
  escopo desta auditoria.
- Conclusão: as três unidades do FaithRO passaram na validação sem
  achados próprios.

## Inicialização planejada

Os comandos abaixo **não foram executados nesta auditoria** (as três unidades
já estavam ativas). Documentados para uso planejado futuro, respeitando a
ordem de dependência declarada:

```bash
sudo systemctl start faithro-login.service
sudo systemctl start faithro-char.service
sudo systemctl start faithro-map.service
```

## Parada planejada

Ordem inversa, para respeitar as dependências declaradas (`map` depende de
`char`, que depende de `login`):

```bash
sudo systemctl stop faithro-map.service
sudo systemctl stop faithro-char.service
sudo systemctl stop faithro-login.service
```

## Reinício planejado

Evite reiniciar as três unidades simultaneamente sem necessidade — prefira
reiniciar apenas a unidade afetada, na ordem de dependência quando mais de
uma precisar ser reiniciada:

```bash
sudo systemctl restart faithro-login.service
sudo systemctl restart faithro-char.service
sudo systemctl restart faithro-map.service
```

Como `char` requer `login` e `map` requer `char`, reiniciar `login` pode
interromper `char` e `map` momentaneamente por dependência declarada; avalie
o impacto antes de reiniciar unidades upstream na cadeia de dependência.

## Web server

Camadas verificadas separadamente, nesta auditoria:

| Camada | Estado confirmado |
| --- | --- |
| Habilitado no código | Sim — `#define WEB_SERVER_ENABLE PACKETVER > 20200300` em `src/config/packets.hpp`, verdadeiro para `PACKETVER=20211103` (já registrado em [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md)). |
| Binário compilado | Sim — `/opt/faithro/rathena/web-server` presente, arquivo regular, permissão `775`, proprietário `faithro:faithro`, executável. |
| Unidade systemd implantada | **Não** — nenhuma unidade relacionada a `web` foi encontrada em `systemctl list-unit-files`/`list-units` nem em `/etc/systemd/system` ou `/lib/systemd/system`. |
| Processo ativo | **Não** — nenhum processo `web-server` em execução no momento da auditoria. |
| Porta escutando | **Não** — nenhuma porta associada a `web-server` em `ss -lntp` (nem `8888/tcp` nem outra). |
| Configuração validada | Parcial — `conf/web_athena.conf` existe (arquivo padrão upstream, `2380 bytes`); `conf/import/web_conf.txt` existe mas está **vazio** (0 bytes), ou seja, nenhum override foi configurado. Conteúdo não foi lido além de metadados (`stat`), para evitar exposição de eventuais segredos. |

**Conclusão desta auditoria:** o web server do rAthena está **compilado, mas
não implantado como serviço** no FaithRO. A pendência registrada em
[09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md) seção 7.2
("confirmar se o binário foi compilado" e "confirmar se existe unidade
systemd") é **parcialmente resolvida**: o binário existe; a unidade **não**
existe. Implantação da unidade, configuração de `web_conf.txt`, porta efetiva,
bind, firewall e testes de endpoint continuam **pendentes** e devem ser
tratados em tarefa própria — não nesta auditoria read-only.

## Firewall

```text
sudo ufw status verbose
```

Confirmado na auditoria:

- Firewall `active`, política padrão `deny (incoming)`.
- `22022/tcp` (SSH) liberado para `Anywhere` — já documentado em
  [04-operacao-vps.md](04-operacao-vps.md).
- `6900/tcp`, `6121/tcp` e `5121/tcp` liberados **apenas** para
  `<IP-AUTORIZADO>` (um único endereço IPv4, não publicado neste documento).
- Nenhuma regra para porta de web server foi encontrada (consistente com a
  ausência de unidade/processo).
- Nenhuma alteração de firewall foi realizada nesta auditoria.

## Testes

Testes seguros, sem expor segredos, para validar este documento em uma nova
auditoria:

- Repetir os comandos de [Comandos de descoberta](#comandos-de-descoberta) e
  confirmar que os três nomes de unidade permanecem os mesmos.
- Repetir `systemctl is-enabled` / `is-active` / `is-failed` para as três
  unidades e comparar com o [Mapa de serviços](#mapa-de-serviços).
- Repetir `sudo ss -lntp` filtrando pelas portas `6900`, `6121`, `5121`,
  `8888` e confirmar que apenas as três primeiras estão em escuta.
- Repetir `sudo ufw status verbose` e confirmar que a política e as regras
  não mudaram sem registro em changelog.
- Repetir `git -C /opt/faithro/rathena status --short --branch` e
  `git -C /opt/faithro/rathena rev-parse HEAD` e confirmar working tree limpo
  e commit esperado.

## Riscos

- As portas do jogo estão vinculadas a `0.0.0.0` (todas as interfaces) no
  nível do processo; a proteção efetiva depende inteiramente do `ufw`. Uma
  alteração futura de firewall sem revisão pode expor as portas publicamente.
- `faithro-char` e `faithro-map` dependem (`Requires=`) das unidades
  anteriores na cadeia; reiniciar uma unidade upstream pode interromper as
  demais.
- O binário `web-server` já está compilado e presente; uma tentativa manual
  de executá-lo fora de uma unidade systemd gerenciada, sem revisão de
  configuração e firewall, poderia expor um serviço não planejado.
- O SSH (`22022/tcp`) está liberado para `Anywhere`; isso é uma decisão de
  hardening já registrada em [04-operacao-vps.md](04-operacao-vps.md) e não
  foi alterada nem reavaliada nesta auditoria.

## Rollback

Esta tarefa é documental e read-only:

- **Rollback documental:** reverter o commit desta branch, caso o conteúdo
  precise ser removido ou corrigido.
- **Nenhuma reversão operacional é necessária** — nenhum serviço, unidade,
  firewall, banco de dados ou binário foi alterado na VPS durante esta
  auditoria.

## Referências

- Unidades reais (caminho, sem conteúdo sensível):
  `/etc/systemd/system/faithro-login.service`,
  `/etc/systemd/system/faithro-char.service`,
  `/etc/systemd/system/faithro-map.service`.
- [Documentação oficial do systemd — `systemd.service`](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [Documentação oficial do systemd — `systemctl`](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html)
- [Documentação oficial do systemd — `journalctl`](https://www.freedesktop.org/software/systemd/man/latest/journalctl.html)
- [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md) — baseline
  `PACKETVER`, `WEB_SERVER_ENABLE` confirmado no código, pendências de
  implantação do web server.
- [10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md) —
  política de fontes e commit de referência `7f080871c`.
- [04-operacao-vps.md](04-operacao-vps.md) — hardware, hardening e portas.
- Evidência sanitizada: coletada em 2026-07-10 via `systemctl show`,
  `systemctl cat`, `systemctl is-enabled/is-active/is-failed`,
  `systemd-analyze verify`, `ss -lntp`, `ufw status verbose`, `journalctl`
  (janela de 10 minutos) e `git status`/`git rev-parse` no checkout
  `/opt/faithro/rathena`. Nenhuma saída bruta contendo IP real, credenciais ou
  dados de jogadores foi versionada.
