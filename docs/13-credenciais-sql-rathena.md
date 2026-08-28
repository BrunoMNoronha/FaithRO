# Credenciais SQL do rAthena — auditoria e rotação — FaithRO

> **Escopo:** documento de auditoria, operação e rotação das credenciais
> MariaDB usadas pelo rAthena. A operação que originou este documento **alterou
> a senha do usuário SQL do emulador** e reiniciou os serviços de forma
> controlada, com backup e rollback preparados. Nenhum valor secreto (senha,
> hash, token) é registrado aqui — segredos reais **nunca** devem ser
> documentados.

## Objetivo

Registrar a arquitetura das credenciais SQL do rAthena no FaithRO - Laus Deo,
o método seguro de auditoria e rotação da senha do usuário de banco, as
validações obrigatórias, os riscos, o rollback e o troubleshooting — para que
qualquer operador rotacione a credencial sem expor segredos e sem derrubar os
serviços.

## Estado verificado

- **Data da auditoria e rotação:** 2026-07-11.
- **Ambiente:** VPS `faithro-vps`, Ubuntu 22.04.5 LTS
  (kernel `6.8.0-124-generic`), acesso via alias `ssh faithro-vps` como usuário
  `faithro` (grupo `sudo`).
- **Repositório do emulador:** `/opt/faithro/rathena`, branch `master`,
  commit `7f080871c` (git hash `7f080871c8b3bbe7a79027194633201c63422ee1`).
- **MariaDB:** ativo; usuário administrativo local via `sudo mariadb`.
- **Serviços envolvidos:** `faithro-login.service`, `faithro-char.service`,
  `faithro-map.service`, todos `User=faithro` e `active/running`.

## Arquitetura de credenciais

### Usuário SQL

- Conta **única e dedicada** ao rAthena: `faithro_app`@`localhost`.
- Plugin de autenticação: `mysql_native_password`.
- Host restrito a `localhost` (conexão por socket Unix; `host: localhost` no
  rAthena usa o socket e ignora a porta).
- Privilégios **escopados** aos bancos usados, sem privilégios globais:
  - `GRANT ALL PRIVILEGES ON faithro.*`
  - `GRANT ALL PRIVILEGES ON faithro_log.*`
  - `GRANT USAGE ON *.*` (apenas o baseline, sem privilégio efetivo global).
- Não existe usuário `ragnarok` no MariaDB, portanto o default upstream
  `ragnarok/ragnarok` presente no core (ver abaixo) é inofensivo.
- Não há contas anônimas nem conta do rAthena com host `%`.

### Bancos

- `faithro` — dados do jogo (account, char, map).
- `faithro_log` — logs.

### Arquivos de configuração

| Caminho | Papel | Versionado | Permissão |
| --- | --- | --- | --- |
| `conf/inter_athena.conf` | Core do rAthena; mantém o default upstream `ragnarok/ragnarok` como placeholder | Sim (core, não editar) | — |
| `conf/import/inter_conf.txt` | **Override efetivo** com a credencial real; vence sobre o core | **Não** (ignorado) | `600 faithro:faithro` |

O override é ignorado pelo Git via `.gitignore` (`/conf/import`); confirmável com
`git check-ignore -v conf/import/inter_conf.txt`. O diretório `conf/import` tem
permissão `700 faithro:faithro`.

### Ponto crítico — seis conjuntos, um único usuário

O override `conf/import/inter_conf.txt` define **seis** conjuntos de credenciais,
**todos apontando para o mesmo usuário** `faithro_app`:

| Diretiva de senha | Componente que a usa | Banco alvo |
| --- | --- | --- |
| `login_server_pw` | login-server (DB de contas) | `faithro` |
| `ipban_db_pw` | login-server (subsistema IPBan) | `faithro` |
| `char_server_pw` | char-server | `faithro` |
| `map_server_pw` | map-server | `faithro` |
| `web_server_pw` | web-server (não implantado como serviço systemd) | `faithro` |
| `log_db_pw` | login/char/map (DB de logs) | `faithro_log` |

Como o MariaDB tem **um único** usuário `faithro_app`, **todas as seis** linhas
`*_pw` precisam carregar a **mesma** senha e ser rotacionadas **em conjunto**.
Rotacionar apenas parte delas quebra os componentes cujas linhas ficaram com a
senha antiga (ver [Troubleshooting](#troubleshooting)).

> **Confirmado no código** (commit `7f080871c`): as senhas SQL são armazenadas
> como `std::string` em login (`src/login/account.cpp`), char
> (`src/char/inter.cpp`) e map (`src/map/map.cpp`); o parser de linha usa buffer
> `w2[1024]` (`sscanf("%31[^:]: %1023[^\r\n]", ...)`). Não há limite prático de
> comprimento de senha nesses caminhos. O `char passwd[24]` em
> `src/char/char.hpp` é o login **inter-servidor** (conta `faithro_srv`), que
> **não** é usuário MariaDB e **não** faz parte desta rotação.

## Método de rotação

Toda a operação roda **na VPS**, dentro de um script remoto único, com
`umask 077`, `trap` de limpeza e auto-rollback. Regras invioláveis:

- Nunca imprimir senha, hash, token ou o conteúdo integral do override.
- Nunca passar senha em argumento de linha de comando (`ps` a exporia).
- Gerar a senha **na VPS**, sem retorná-la ao terminal local.
- Arquivos temporários com segredo: `600`, em diretório protegido, removidos por
  `trap` em sucesso, erro ou interrupção.
- Não alterar o core do emulador, o usuário SQL, o host, os bancos nem os
  privilégios — apenas a **senha**.

### Passos

1. **Gate e baseline:** confirmar `git status` limpo, MariaDB ativo, os três
   serviços e seus `MainPID`/`NRestarts`.
2. **Backup e rollback:** criar `/opt/faithro/backups/config/<timestamp>/`
   (`700`), copiar o override preservando dono/permissões (`cp -p`), gerar
   `sha256`, capturar o **hash de senha antigo** em arquivo `600` (para rollback
   por hash, sem texto-claro).
3. **Gerar senha** forte na VPS sem exibir. Recomenda-se alfanumérica
   (`[A-Za-z0-9]`) para evitar qualquer ambiguidade em parsing de config,
   arquivo de opções do cliente e SQL. Ex.: 40 caracteres alfanuméricos.
4. **Alterar no MariaDB** por `stdin` (nunca `-e` com segredo):
   `SET PASSWORD FOR 'faithro_app'@'localhost' = PASSWORD('<nova>'); FLUSH PRIVILEGES;`
5. **Validar a nova credencial** conectando como `faithro_app` aos **dois**
   bancos (`faithro` e `faithro_log`), com a senha apenas em
   `--defaults-extra-file` (`600`), nunca em `argv`.
6. **Atualizar as seis linhas `*_pw`** do override, preservando inode, dono e
   permissão (`600 faithro:faithro`), lendo a senha de arquivo (não de `argv`).
7. **Restart controlado** na ordem `login → char → map`.
8. **Validação** de pelo menos 60 s (ver abaixo).
9. **Limpeza** dos temporários com segredo (via `trap`). Manter o backup
   protegido para recuperação administrativa.

## Validações

Durante ≥ 60 s, com checagens objetivas em intervalos (não apenas `sleep 60`):

- Serviços `active/running`, `MainPID` estáveis, `NRestarts` sem crescimento.
- Ausência, no journal da janela da operação, de: `access denied`,
  `denied for user`, `authentication failed`, `can't connect to mysql`,
  `lost connection to mysql`, `unknown database`, `couldn't connect`,
  `segmentation fault`, `core dumped`.
- Marcadores **positivos** de log deste build (calibrados na inicialização):
  - login: `Ipban connection made` (confirma `ipban_db_pw`),
    `The login-server is ready` (confirma `login_server_pw`),
    `Connection of the char-server 'FaithRO' accepted` (char ↔ login).
  - map: `Successfully logged on to Char Server`,
    `Map-server connected to char-server`, `Map Server is now online`
    (confirma `map_server_pw` e a cadeia map ↔ char).

A **ausência de confirmação positiva** deve ser tratada como falha e acionar
rollback — "nenhum erro visível" não é confirmação suficiente.

## Riscos

- **Rotação parcial das seis linhas `*_pw`** — causa mais provável de falha (ver
  Troubleshooting). Sempre rotacionar as seis juntas.
- **Janela entre trocar a senha no MariaDB e reiniciar os serviços** — os
  processos em execução mantêm conexões persistentes com a senha antiga em
  memória; a troca não derruba conexões vivas, mas um reconnect nesse intervalo
  falharia. Mantenha a janela curta (trocar → validar → atualizar override →
  restart).
- **web-server** — a diretiva `web_server_pw` existe no override, mas o
  web-server **não** é um serviço systemd implantado; ele não é reiniciado pela
  rotação. Ainda assim, atualize `web_server_pw` para manter consistência.
- **`~/.bash_history`** — pode conter referências a `faithro_app` de comandos
  antigos. Após a rotação, qualquer senha antiga ali registrada torna-se inútil;
  ainda assim, recomenda-se higienizar o histórico e evitar digitar senhas em
  linha de comando.

## Rollback

Preparado **antes** de qualquer escrita e acionado automaticamente em qualquer
falha após o início das alterações. Restaura, sem exibir segredos:

1. **Senha SQL antiga** pelo hash capturado:
   `SET PASSWORD FOR 'faithro_app'@'localhost' = '<hash-antigo>'; FLUSH PRIVILEGES;`
   (a forma por hash `*...` não requer o texto-claro).
2. **Override antigo** a partir de `inter_conf.txt.bak` (`cp -p`, preservando
   dono/permissões).
3. **Restart** dos três serviços e **revalidação** (`active/running`, banco,
   logs).

Localização do backup: `/opt/faithro/backups/config/<timestamp>/`
(`inter_conf.txt.bak`, `inter_conf.txt.bak.sha256`, `old_auth.hash`,
`baseline.txt`), todos `600 faithro:faithro`, diretório `700`. **Não** versionar
o backup.

## Troubleshooting

- **`Access denied for user 'faithro_app'@'localhost' (using password: YES)` no
  boot do login, mesmo após rotação** — quase sempre significa que **nem todas**
  as seis linhas `*_pw` foram atualizadas. O login-server abre três conexões
  (account, ipban, loginlog); se `ipban_db_pw` (ou outra) ficou com a senha
  antiga enquanto o MariaDB já tem a nova, o login falha com `status=1/FAILURE`.
  Correção: garantir que as **seis** linhas `*_pw` tenham a nova senha.
- **A credencial autentica pelo cliente `mariadb` mas o serviço falha** — indica
  que o valor no arquivo do serviço difere do que o cliente usou (rotação
  parcial, arquivo errado, ou segredo com caractere problemático). Prefira senha
  alfanumérica e confirme qual arquivo é efetivamente carregado
  (`conf/import/inter_conf.txt`).
- **`localhost` vs `127.0.0.1`** — a conta é `@localhost`; o rAthena com
  `host: localhost` conecta por socket Unix. Não altere host e senha ao mesmo
  tempo sem necessidade comprovada.
- **`systemctl is-active` retornando 3** em scripts com `set -e` aborta o fluxo:
  o serviço não está `active`. Trate como falha e investigue o journal do
  processo atual.

## Observações de segurança

- Segredos reais (senha, hash, token) **nunca** entram em documentação, Git,
  logs, journal, `argv` ou temporários desprotegidos. Em relatórios, representar
  como `[REDACTED]`.
- Qualquer credencial **exibida** em terminal, log, journal ou transcript deve
  ser considerada **comprometida** e rotacionada preventivamente, mesmo sem
  evidência de uso indevido por terceiros.
- Não alterar a autenticação do usuário `root` do MariaDB.
- Não conceder privilégios globais; manter o escopo aos bancos `faithro` e
  `faithro_log`.

## Referências

- [04-operacao-vps.md](04-operacao-vps.md) — operação da VPS, backups, portas.
- [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md) — unidades
  systemd, ordem de start/stop, pré-check do MariaDB.
- [../SECURITY.md](../SECURITY.md) e [05-governanca.md](05-governanca.md) —
  política de segredos e governança.
