# Rotação da credencial SQL do runtime FaithRO

> **Escopo:** operação de segurança **com escrita controlada** na VPS (rotação de
> credencial) e documentação sanitizada no repositório. Nenhum segredo é
> versionado. Nenhum dado individual, pessoal ou conteúdo de jogador foi lido ou
> alterado; somente contagens agregadas foram consultadas para validação. Nenhuma
> conta foi criada. Complementa [13-credenciais-sql-rathena.md](13-credenciais-sql-rathena.md)
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

Arquivos deliberadamente **não** alterados **durante a 2O-B1 original**: base
`conf/inter_athena.conf` (usa outro usuário, valores default), `passwd`
inter-servidor de char/map (não é SQL), `channels.conf` (senha de canal de chat),
repositório clonado `/opt/faithro/faithro-repo` (`.env.example`/docs — não lidos
pelo runtime). Os **backups históricos** de rotações anteriores não foram
alterados na 2O-B1 original, mas foram **posteriormente aposentados** na
2O-B1-R1 (ver §15) — portanto **não** permaneceram intocados ao longo de toda a
cadeia.

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
   script de rollback preparado e validado **antes** da escrita (esse rollback e
   o backup em texto claro foram **posteriormente aposentados** na 2O-B1-R1 — §15).
5. **Geração da credencial:** a credencial **definitiva** (48 caracteres
   alfanuméricos, criptograficamente aleatória) foi gerada **na VPS**, em arquivo
   protegido em `/run` (`root:600`), e **não foi impressa, transmitida nem
   copiada para fora**. Uma tentativa **anterior** gerou uma senha **candidata**
   que foi exibida por um erro de sintaxe e imediatamente descartada — ver §10;
   essa candidata **nunca** se tornou credencial ativa.
6. **Rotação coordenada:** atualização das seis referências no config, seguida do
   `ALTER USER` no MariaDB. A **primeira** tentativa de `ALTER USER` usou sintaxe
   incompatível com o MariaDB, falhou e exibiu a senha candidata (§10); o
   `ALTER USER` **definitivo e bem-sucedido** foi executado com **saída
   suprimida**.
7. **Reinício ordenado:** `login → char → map`, com validação a cada passo.
8. **Validação e observação:** testes de autenticação e janela de observação de
   60 segundos.
9. **Limpeza:** todos os temporários secretos triturados (`shred`) e removidos.
   **Ao final da 2O-B1 original**, o backup de rollback havia sido **preservado**;
   a revisão 2O-B1-R1 identificou que ele continha a credencial anterior em texto
   claro e o **aposentou** (§15) — o backup sensível **não** existe mais.

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
- Backup original: `inter_conf.txt.bak` + `.sha256` em diretório `700`. **Este
  backup continha a credencial anterior em texto claro** e foi **aposentado** na
  ETAPA 2O-B1-R1 (ver §15).
- Endereços IP exibidos apenas de forma sanitizada.

## 10. Nota de incidente (contido)

Na primeira tentativa de `ALTER USER` foi usada sintaxe do MySQL
(`IDENTIFIED WITH ... BY`) inválida no MariaDB; o cliente ecoou a instrução com
erro e uma senha **candidata** apareceu transitoriamente. Contenção: essa
tentativa **falhou** (a senha candidata **nunca** se tornou credencial ativa no
banco), a candidata foi **descartada**, e uma senha nova foi gerada e aplicada
com a sintaxe correta e **saída suprimida**.

> **Correção (2O-B1-R1).** A versão inicial deste documento afirmava que "nenhum
> valor secreto permaneceu persistido no servidor". Isso estava **incorreto**: o
> backup de rollback preservava a credencial **anterior** em texto claro, e um
> script era capaz de reativá-la. A afirmação absoluta foi removida; a
> retenção foi tratada na §15. Nenhum segredo foi **versionado** no Git — isso
> permanece verdadeiro e distinto da retenção no servidor.

## 11. Riscos remanescentes

- **Usuário SQL único** compartilhado pelas seis conexões (sem segregação por
  serviço) — fora do escopo desta etapa; segregação continua como melhoria futura.
- **Histórico de shell** (`~/.bash_history` de `faithro`): 6 linhas sensíveis de
  rotações manuais anteriores foram **removidas** na 2O-B1-R1 (§15); histórico do
  `root` não continha linhas sensíveis.
- **`.env.example`** no repositório clonado da VPS: revisado na 2O-B1-R1 e
  classificado como **placeholder** (≠ credencial ativa e ≠ antiga); não alterado.
- **Remoção é melhor esforço:** `shred` atua apenas no filesystem visível; **não
  há garantia** sobre snapshots, camadas copy-on-write, backups do provedor,
  journald externo ou o transcript do agente.
- **Divergência de build** (fonte com `RENEWAL` ativo × binário Pré-Renewal)
  permanece **pendente**; não faz parte desta etapa.

## 12. Modelo de recuperação (substitui o rollback inseguro)

> O `rollback.sh` original e o backup em texto claro foram **aposentados** na
> ETAPA 2O-B1-R1 (§15). A credencial anterior é considerada **comprometida** e
> **não deve ser restaurada** em hipótese alguma.

**Falha de autenticação futura** — recuperar por **nova rotação com credencial
fresca**, nunca restaurando a senha antiga:

1. gerar uma nova credencial aleatória **na VPS** (em `/run`, `root:600`, nunca
   impressa);
2. atualizar o arquivo de import e o MariaDB de forma coordenada, com saída de
   comandos SQL suprimida;
3. testar a nova autenticação (nos dois bancos) **antes** do restart;
4. reiniciar `login → char → map`;
5. validar por pelo menos 60 segundos;
6. remover os temporários (`shred`, melhor esforço);
7. **não** restaurar credenciais antigas.

**Falha apenas de configuração não sensível** — usar Git, a configuração-base
conhecida ou um registro sanitizado. **Nenhum backup persistente em texto claro**
deve ser usado como caminho de rollback de credencial.

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
- Próximo marco funcional: preparação do cliente e teste de login controlado
  (não faz parte desta etapa).

## 15. Correção pós-rotação (ETAPA 2O-B1-R1)

**Data:** 2026-08-05 (UTC). **Motivação:** revisão independente identificou que o
rollback preparado na rotação preservava a **credencial anterior em texto claro**
(`inter_conf.txt.bak`) e um `rollback.sh` capaz de **reativá-la** — o que
deixaria de ser um rollback seguro, já que a credencial anterior é tratada como
**comprometida**. A documentação original também afirmava, de forma incorreta,
que nenhum segredo permanecera no servidor.

**Decisão de segurança:** a credencial anterior **não** pode voltar a ser ativada;
o caminho de recuperação passa a ser **nova rotação com credencial fresca** (§12).

**Ações executadas (escrita controlada na VPS, sem expor segredos):**

- Confirmado que a **credencial ativa autentica** em `faithro` e `faithro_log`
  antes de qualquer remoção; a credencial antiga **não** foi lida nem testada.
- **Aposentados** (remoção de melhor esforço via `shred` no filesystem visível):
  - no diretório desta rotação: o backup de config em texto claro, seu checksum
    e o script restaurador;
  - em diretórios de rotações anteriores (`rotacao-2pb-20260727`,
    `rotacao-sql-20260711`) e no backup avulso de `20260710`: backups de config
    em texto claro, checksums e artefatos de autenticação antigos.
- **Higienização de histórico:** 6 linhas sensíveis removidas do
  `~/.bash_history` de `faithro` (dono/permissões `600` preservados; sem sessão
  interativa concorrente); histórico do `root` já estava livre.
- **`.env.example`:** revisado em memória e classificado como **placeholder**
  (≠ ativa, ≠ antiga); **não** alterado.
- **`/run`, `/tmp`, journald e checkouts da VPS:** sem temporários da etapa; sem
  padrões sensíveis na janela da rotação; working trees limpos.
- **Registro sanitizado** `RETIREMENT.txt` (modo `600`, sem segredo) criado no
  diretório da rotação; `baseline.txt` (sem conteúdo sensível) preservado.

**Limitações declaradas honestamente:** a remoção é de **melhor esforço** e não
garante eliminação em snapshots, camadas copy-on-write, backups do provedor,
journald externo ou no transcript do agente. O transcript do agente **não** pode
ser apagado por comandos na VPS.

**Validação pós-higienização:** credencial ativa autentica; três serviços
`active/running` com `NRestarts` estável e sem `Access denied`; `login → char →
map` funcional; 1265 mapas; `PACKETVER=20211103` e Pré-Renewal inalterados;
portas inalteradas; MariaDB local; contagem agregada inalterada; janela de 60s
estável; nenhum backup em texto claro, rollback inseguro ou temporário
remanescente.
