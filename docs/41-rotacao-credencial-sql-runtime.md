# Rotação da credencial SQL do runtime FaithRO

> **Escopo:** operação de segurança **com escrita controlada** na VPS (rotação de
> credencial) e documentação sanitizada no repositório. Nenhum segredo é
> versionado. Nenhum dado de jogador foi lido ou alterado. Nenhuma conta foi
> criada. Complementa [13-credenciais-sql-rathena.md](13-credenciais-sql-rathena.md)
> e [38-auditoria-prontidao-primeiro-acesso.md](38-auditoria-prontidao-primeiro-acesso.md).

## 1. Objetivo

Rotacionar com segurança a senha do usuário MariaDB operacional do runtime do
rAthena (`faithro_app`), validar integralmente os três serviços após a troca e
registrar o procedimento de forma sanitizada.

## 2. Motivação

Durante a ETAPA 2O-A (auditoria somente leitura) a credencial SQL apareceu em
claro em uma saída de terminal. Sem evidência de exposição pública, mas por
princípio de contenção, a credencial passou a ser tratada como **potencialmente
comprometida** e foi rotacionada.

## 3. Data e ambiente

- **Data:** 2026-08-05 (UTC).
- **VPS:** Ubuntu 22.04.5 LTS (host `faithro-vps`), timezone America/Sao_Paulo.
- **Runtime:** `/opt/faithro/rathena` (checkout upstream do rAthena, branch `master`).
- **Banco:** MariaDB 10.6, escutando somente em `127.0.0.1:3306` (não exposto).
- **Usuário SQL rotacionado:** `faithro_app@localhost` (plugin `mysql_native_password`).
- **Bancos:** `faithro` e `faithro_log`.

## 4. Referências de commit

| Item | Valor |
| --- | --- |
| Base do worktree/branch | `origin/dev` @ `f9f84feeceaf01577e1978b98f0ea04753c9e1e3` |
| SHA do deploy (runtime) | `7f080871c8b3bbe7a79027194633201c63422ee1` |
| Branch de trabalho | `security/rotate-faithro-app-credential` (worktree isolado) |

## 5. Arquivos operacionais afetados (sem conteúdo sensível)

- **Único arquivo de runtime alterado:** `conf/import/inter_conf.txt` — campos de
  senha SQL das seis conexões que usam `faithro_app`:
  `login_server_pw`, `ipban_db_pw`, `char_server_pw`, `map_server_pw`,
  `web_server_pw`, `log_db_pw`. As chaves `*_id` (usuário) permaneceram
  inalteradas. Permissões preservadas: `faithro:faithro`, modo `600`.
- **MariaDB:** senha do usuário `faithro_app@localhost` (via `ALTER USER ...
  IDENTIFIED BY ...`, plugin `mysql_native_password` preservado). Grants
  inalterados.

Arquivos deliberadamente **não** alterados: base `conf/inter_athena.conf` (usa
outro usuário, valores default), `passwd` inter-servidor de char/map (não é SQL),
`channels.conf` (senha de canal de chat), repositório clonado
`/opt/faithro/faithro-repo` (`.env.example`/docs — não lidos pelo runtime),
backups históricos.

## 6. Estado anterior (baseline)

- Três serviços `active/running`, `NRestarts=0`, iniciados em 2026-07-27.
- Todas as seis conexões SQL compartilhavam o **mesmo** usuário e a **mesma**
  senha (usuário único `faithro_app`).
- `PACKETVER=20211103`, Pré-Renewal, obfuscação com chaves efetivas zero, 1265
  mapas, portas 6900/6121/5121, MariaDB local.

## 7. Procedimento executado (alto nível)

1. **Gate local:** worktree isolado criado a partir de `origin/dev`, sem tocar o
   worktree/branch do WARP.
2. **Gate operacional (leitura):** confirmada estabilidade dos serviços, MariaDB
   local e ausência de mudança desde a 2O-A.
3. **Descoberta:** mapeadas todas as referências à credencial; produzida lista
   fechada (um único arquivo de runtime + o usuário no banco).
4. **Backup + rollback:** backup do arquivo alterado com checksum SHA-256, modo
   `600`, em diretório protegido `700` sob `/opt/faithro/backups/config/`;
   script de rollback preparado e validado **antes** da escrita.
5. **Geração da credencial:** nova senha criptograficamente aleatória (48
   caracteres alfanuméricos) gerada **na VPS**, em arquivo protegido em `/run`
   (`root:600`), nunca impressa, nunca transmitida, nunca copiada para fora.
6. **Rotação coordenada:** atualização das seis referências no config, seguida
   de `ALTER USER` no MariaDB, com **saída totalmente suprimida**.
7. **Reinício ordenado:** `login → char → map`, com validação a cada passo.
8. **Validação e observação:** testes de autenticação e janela de observação de
   60 segundos.
9. **Limpeza:** todos os temporários secretos triturados (`shred`) e removidos;
   backup de rollback preservado.

A senha foi gerada com classe **alfanumérica** por decisão de compatibilidade:
garante interpretação correta pelo parser de linha do rAthena e pelo literal SQL,
sem caracteres de escape/aspas.

## 8. Testes e resultados

| Teste | Resultado |
| --- | --- |
| Nova credencial autentica em `faithro` e `faithro_log` | **PASS** |
| Credencial antiga rejeitada após a troca | **PASS** (captura sem imprimir valor) |
| Grants do usuário equivalentes ao baseline (USAGE + ALL em ambos os bancos) | **PASS** |
| `login-server` `active/running`, listening 6900 | **PASS** |
| `char-server` conecta ao login, anuncia IP público, listening 6121 | **PASS** |
| `map-server` conecta ao char, 1265 mapas, listening 5121 | **PASS** |
| `NRestarts` sem crescimento (sem ciclo de restart) | **PASS** (permaneceu 0) |
| Sem `Access denied` / erro SQL / crash nos três serviços | **PASS** (0 ocorrências) |
| `PACKETVER=20211103` e Pré-Renewal inalterados | **PASS** |
| Portas inalteradas; MariaDB permanece local | **PASS** |
| Janela de 60s: PIDs e `NRestarts` estáveis; leitura SQL início=fim | **PASS** |
| Nenhum registro do jogo alterado (contagem de contas constante) | **PASS** |

**Resultado geral: APROVADA.**

## 9. Evidências sanitizadas

- Config pós-rotação: seis linhas `*_pw` presentes com valores mascarados
  (`[REDACTED]`), `*_id: faithro_app`, permissões `600`.
- Runtime: `login-server is ready ... port 6900`; `char-server is ready ...
  port 6121`; `Map-Server 0 connected: 1265 maps ... port 5121`;
  `Using packet version: 20211103`; `Packet Obfuscation: Enabled. Keys:
  0x00000000, 0x00000000, 0x00000000`.
- Backup: `inter_conf.txt.bak` + `.sha256`, modo `600` em diretório `700`.
- Endereços IP exibidos apenas de forma sanitizada.

## 10. Nota de incidente (contido)

Na primeira tentativa de `ALTER USER` foi usada sintaxe do MySQL
(`IDENTIFIED WITH ... BY`) inválida no MariaDB; o cliente ecoou a instrução com
erro e uma senha **candidata** apareceu transitoriamente. Contenção: essa
tentativa **falhou** (a senha candidata **nunca** se tornou credencial ativa no
banco), a candidata foi **descartada**, e uma senha nova foi gerada e aplicada
com a sintaxe correta e **saída suprimida**. Nenhum valor secreto foi
persistido no servidor (config reescrito, arquivos temporários triturados) nem
versionado.

## 11. Riscos remanescentes

- **Usuário SQL único** compartilhado pelas seis conexões (sem segregação por
  serviço) — fora do escopo desta etapa; segregação continua como melhoria futura.
- **Histórico de shell** (`~/.bash_history`) pode conter credenciais de rotações
  manuais anteriores; após esta rotação, qualquer senha antiga ali é inválida.
  Recomenda-se revisão em etapa futura.
- **`.env.example`** no repositório clonado da VPS referencia a chave de senha
  (placeholder); revisar para garantir ausência de valor real, em etapa futura.
- **Divergência de build** (fonte com `RENEWAL` ativo × binário Pré-Renewal)
  permanece **pendente**; não faz parte desta etapa.

## 12. Rollback disponível

Script `rollback.sh` preservado no diretório de backup protegido restaura o
arquivo de config (verificando checksum), restabelece a senha anterior no
MariaDB (derivada do backup, sem impressão), reinicia os serviços na ordem
segura e valida `login → char → map`. O backup **não** foi removido nesta etapa.

## 13. Registros explícitos

- `new_account: no` **não** foi alterado.
- **Nenhuma conta** (jogador ou GM) foi criada.
- **UFW** não foi alterado.
- **PACKETVER** não foi alterado.
- **Binários não** foram recompilados.
- Divergência fonte Renewal × binário Pré-Renewal **continua pendente**.
- **Nenhum segredo** (senha antiga, nova, hash, comando SQL com senha, dump ou
  dado de jogador) foi versionado.

## 14. Pendências

- Segregação de usuários SQL por serviço (etapa futura, fora deste escopo).
- Reconciliação da divergência de build (Renewal × Pré-Renewal).
- Revisão de `~/.bash_history` e `.env.example` do repositório clonado na VPS.
- Próximo marco funcional: preparação do cliente e teste de login controlado
  (não faz parte desta etapa).
