# Auditoria de prontidão do primeiro acesso (registro consolidado)

> **Escopo:** registro consolidado e datado de auditoria **somente leitura**.
> Nenhuma alteração de código, banco, configuração, `PACKETVER`, progressão,
> firewall, serviço ou binário foi executada. Nenhum cliente foi obtido,
> preparado, modificado ou executado. Nenhuma conta foi criada. Nenhum segredo,
> IP, endpoint ou dado de jogador é registrado aqui.
>
> Este documento **não** substitui e **não** reescreve os registros canônicos —
> ele os **referencia** e registra apenas evidências novas ou reconfirmadas em
> **2026-08-03**, além de reconciliar o estado dos bloqueadores. Documentos
> canônicos: [09](09-cliente-baseline-protocolo.md),
> [12](12-configuracao-packetver.md), [15](15-cliente-primeiro-acesso.md),
> [16](16-politica-distribuicao-cliente.md),
> [28](28-decisao-ferramenta-preparacao-cliente.md),
> [29](29-compatibilidade-cliente-2021-11-05-packetver.md); infraestrutura em
> [04](04-operacao-vps.md), [11](11-servicos-systemd-rathena.md),
> [13](13-credenciais-sql-rathena.md); cadeia WARP em
> [30](30-auditoria-estatica-warp.md)–[37](37-resultado-gate-2-materializacao-integridade-warp.md).

## 1. Objetivo

Consolidar, em um único registro rastreável, o resultado da auditoria de
compatibilidade cliente-servidor e de prontidão do primeiro acesso do FaithRO -
Laus Deo, **reconfirmando por evidência de runtime** o estado do servidor e
**registrando as lacunas** que ainda impedem uma homologação controlada do
primeiro login. O documento evita repetir integralmente as matrizes e
procedimentos já documentados; onde a informação já existe, aponta para a fonte
canônica.

## 2. Estado canônico do projeto (reafirmado, não alterado)

| Item | Valor canônico | Fonte |
| --- | --- | --- |
| Base Level máximo | **255** (planejado, sujeito a balanceamento) | [00](00-base-conhecimento.md), [09 §1](09-cliente-baseline-protocolo.md) |
| Atributo/status natural máximo individual | **185** (planejado) | [00](00-base-conhecimento.md), [09 §1](09-cliente-baseline-protocolo.md) |
| ASPD máxima | **197** (planejada) | [00](00-base-conhecimento.md), [09 §1](09-cliente-baseline-protocolo.md) |
| Terceiras classes | **desabilitadas** por decisão de conteúdo | [09 §4](09-cliente-baseline-protocolo.md) |

> **Nenhuma progressão foi alterada por esta auditoria.** Os overrides de
> progressão (Base 255 / atributos 185 / ASPD 197) permanecem **versionados e
> não implantados**, conforme [14](14-progressao-base-255-overrides.md); este
> documento não os toca.
>
> **Inconsistência herdada registrada:** enunciados anteriores de etapa que
> mencionam "Level máximo 185" referem-se ao **atributo** máximo (185), **não**
> ao Base Level (255). O valor não deve ser interpretado como Base Level nem usado
> para alterar progressão.

## 3. Evidências reconfirmadas por runtime (VPS, somente leitura — 2026-08-03)

Acesso exclusivamente por `ssh faithro-vps`, apenas comandos de leitura. Dados
sensíveis (IP, endpoint, portas de peer) sanitizados. Não houve reinício de
serviço, escrita em banco, alteração de firewall ou de configuração.

| Item | Observado | Como foi observado |
| --- | --- | --- |
| Host / usuário remoto | `faithro-vps` / `faithro` | `hostname`, `whoami` |
| Diretório do rAthena | `/opt/faithro/rathena` | listagem |
| Commit implantado | `7f080871c8b3bbe7a79027194633201c63422ee1` | `git rev-parse HEAD` |
| Working tree do checkout | limpo (0 alterações) | `git status --porcelain` |
| Serviços login/char/map | `ActiveState=active`, `SubState=running`, `NRestarts=0`, `MainPID` válidos | `systemctl show -p ActiveState,SubState,MainPID,NRestarts` |
| Portas de jogo em escuta | `6900`, `6121`, `5121` | `ss -lnt` (endereços sanitizados) |
| MariaDB | porta `3306` presente (localhost + `ufw`, conforme [04](04-operacao-vps.md)) | `ss -lnt` |

Esses valores **reconfirmam** — não contradizem — o estado já registrado em
[09 §13](09-cliente-baseline-protocolo.md), [04](04-operacao-vps.md) e
[11](11-servicos-systemd-rathena.md). Não há conflito documental a reportar.

## 4. `PACKETVER` — determinação e formulação precisa

Evidências coletadas no checkout da VPS (somente leitura):

- **Fonte padrão:** `#define PACKETVER 20211103` em `src/config/packets.hpp`.
- **Ausência de override conhecida:** `src/custom/defines_pre.hpp` **não** define
  `PACKETVER` (nenhuma ocorrência).
- **Ausência de argumento de compilação que o substitua:** nenhum
  `--enable-packetver=` localizado em `config.log`/`CMakeCache.txt`.
- **Checkout da VPS limpo** no commit auditado `7f080871c`.

Formulação precisa (evitando afirmar extração empírica do protocolo do binário):

```text
PACKETVER efetivo fortemente determinado pela configuração de fonte e build,
sem override identificado; compatibilidade do cliente permanece provável até
o teste de login controlado.
```

> O `PACKETVER` **não** foi extraído diretamente do executável compilado; esta
> evidência é de **fonte + configuração de build**, não "confirmação empírica do
> protocolo do binário". A classificação de compatibilidade do cliente 2021-11-05
> permanece **PROVÁVEL** (ver [29](29-compatibilidade-cliente-2021-11-05-packetver.md))
> e só poderá mudar para **COMPROVADA** após uma conexão real **sem erros de
> pacote** (teste de login controlado).

## 5. Criação de conta — `new_account: no` como decisão de segurança

Evidência (somente leitura): `new_account: no` em `conf/login_athena.conf` e no
override `conf/import/login_conf.txt`. Ou seja, o **auto-registro `_M/_F`** do
rAthena está **desabilitado**.

Isto é uma **decisão de segurança**, **não** uma incompatibilidade nem uma
falha: impede a criação automática de contas por qualquer cliente que se conecte.
O primeiro acesso de homologação exige, portanto, **provisionamento controlado**
de uma conta de teste dedicada — e **não** a reativação do auto-registro nem a
exigência do web server (que **não** é requisito comprovado para o login básico;
ver [09 §7](09-cliente-baseline-protocolo.md)).

Não foi localizado, no estado atual, um procedimento versionado de criação de
conta de jogo dedicada — o [13](13-credenciais-sql-rathena.md) cobre apenas a
**rotação da senha do usuário SQL** `faithro_app` e menciona o login
interserver `faithro_srv`, **não** a criação de conta de jogador. Registra-se
abaixo, portanto, um **procedimento planejado** (nada executado nesta etapa;
nenhuma conta criada; nenhuma escrita no banco), reaproveitando os padrões
seguros do [13](13-credenciais-sql-rathena.md):

### 5.1 Procedimento planejado — conta de homologação dedicada

1. **Conta dedicada e não-GM.** Criar **uma** conta exclusiva de homologação na
   tabela `login`, com nível de grupo sem privilégios de GM (não administrativa).
2. **Sem reutilização.** **Não** reutilizar conta administrativa, conta do
   usuário SQL `faithro_app`, nem o login interserver `faithro_srv`.
3. **Senha interativa.** A senha é informada **interativamente na VPS**, lida de
   entrada protegida (`stdin`/arquivo `600`), **nunca** em `argv`, log, journal,
   histórico de shell ou Git (mesma disciplina de segredos do
   [13](13-credenciais-sql-rathena.md)).
4. **Transação SQL controlada.** Criação por transação SQL única e revisável
   (via `sudo mariadb`, socket local), com o mínimo necessário; o esquema exato
   (`userid`, coluna/algoritmo de senha conforme a configuração de login) deve
   ser **confirmado na execução autorizada**, não presumido aqui.
5. **`new_account: no` mantido.** A diretiva permanece `no`; o provisionamento é
   controlado e explícito, sem reabrir o auto-registro.
6. **Rollback.** Reverter por **desativação** (bloqueio/`state`) ou **remoção**
   da conta de homologação, sem afetar outras contas; registrar o resultado sem
   expor segredos.

> **Nesta etapa nada disso é executado.** É um plano; a execução real depende de
> etapa autorizada e do cliente de laboratório preparado.

## 6. Reconciliação da cadeia WARP (estado atual em `origin/dev`)

Correção de uma imprecisão de auditoria anterior: para o **prebuilt WARP.exe**, a
materialização **já ocorreu** de forma controlada.

- **Auditoria binária offline** do prebuilt WARP.exe: plano de 17 gates (0..16)
  em [33](33-plano-auditoria-binaria-offline-warp.md). Estado atual:
  - **GATE 0** (proveniência por metadados): `COMPLETED_PASS`
    ([35](35-resultado-gate-0-proveniencia-warp.md));
  - **GATE 1** (autorização de materialização): integrado
    ([36](36-registro-autorizacao-gate-1-materializacao-warp.md));
  - **GATE 2** (materialização + integridade local): **CONCLUÍDO**,
    `COMPLETED_PASS` em 2026-08-01
    ([37](37-resultado-gate-2-materializacao-integridade-warp.md)) — blob obtido
    por OID Git fixado, tamanho e Git OID conferidos, arquivo **removido**,
    **não versionado**, **não executado**, **não inspecionado**, **não integrado**;
  - **GATE 3 não autorizado** (exige nova decisão humana).
- **Consequência para a preparação do cliente:** o avanço da auditoria binária do
  WARP **não** significa que o WARP tenha sido **executado**, nem que o `Ragexe`
  tenha sido **preparado**. A decisão de ferramenta ([28](28-decisao-ferramenta-preparacao-cliente.md))
  permanece **APROVAR COM RESTRIÇÕES**, com autorização humana **pendente** para
  qualquer modificação do executável. Materializar/verificar o binário do WARP é
  um **pré-requisito de confiança** da ferramenta, distinto de usá-la.

> Reconciliação: onde relatórios anteriores diziam "materialização não ocorreu",
> leia-se: o **blob do WARP.exe foi materializado e verificado no GATE 2 e
> removido**; o **WARP não foi executado** e o **`Ragexe` não foi preparado**.
> Nenhum binário foi materializado, executado, compilado, modificado ou
> distribuído nesta etapa.

## 7. Onde estão as regras de allowlist/denylist do cliente

Para evitar **duas fontes independentes** das mesmas regras, o projeto mantém a
**allowlist/denylist como código canônico** no validador, e este documento apenas
aponta onde elas estão — **não** há arquivos `files-allowlist.txt`/
`files-denylist.txt` duplicando as regras.

- **Fonte canônica:** [`scripts/validate-client-assets.py`](../scripts/validate-client-assets.py):
  - `ALLOWED_SUFFIXES` — sufixos textuais versionáveis em `client/`;
  - `FORBIDDEN_EXTS` — extensões binárias/proprietárias rejeitadas;
  - `MAX_BYTES` — limite de 1 MiB por arquivo; rejeição de symlinks; validação de
    JSON/XML.
- **Bloqueio complementar de commit:** [`.gitignore`](../.gitignore) (padrões
  `*.exe`, `*.dll`, `*.grf`, `RAG_SETUP_*`, `Ragexe*`, `data.grf`, etc.).
- **Execução no CI:** [`validate-client-assets.yml`](../.github/workflows/validate-client-assets.yml).

> A validação final de distribuição **não** depende apenas de extensão: origem e
> licença de cada componente são decididas em
> [16](16-politica-distribuicao-cliente.md).

## 8. Estado dos bloqueadores e decisão de prontidão

**Servidor:** pronto (serviços ativos, portas em escuta, commit alinhado,
`PACKETVER` fortemente determinado como `20211103`). **Cliente / primeiro
acesso:** bloqueado. A decisão permanece:

```text
BLOQUEADO PARA HOMOLOGAÇÃO
```

enquanto **qualquer** um destes bloqueadores persistir:

1. **Executável de laboratório ainda não preparado** por processo autorizado
   (WARP não executado; `Ragexe` não modificado; autorização humana pendente —
   [28 §16](28-decisao-ferramenta-preparacao-cliente.md)).
2. **Mecanismo `clientinfo.xml`/`sclientinfo.xml` não confirmado** no executável
   real ([09 §8](09-cliente-baseline-protocolo.md)).
3. **Endpoint do FaithRO ainda não aplicado** ao cliente de laboratório.
4. **Compatibilidade de protocolo ainda não comprovada por login** (permanece
   **PROVÁVEL**; só um teste de login controlado a eleva a **COMPROVADA** —
   [29 §9](29-compatibilidade-cliente-2021-11-05-packetver.md)).
5. **Conta dedicada de teste ainda não criada** por procedimento controlado
   (§5.1; nenhuma conta criada nesta etapa).

> `new_account: no`, **isoladamente**, **não** é uma incompatibilidade: é uma
> decisão de segurança que apenas exige o **provisionamento controlado** da conta
> de teste (§5).

## 9. Arquivos afetados

| Arquivo | Tipo | Motivo |
| --- | --- | --- |
| `docs/38-auditoria-prontidao-primeiro-acesso.md` | novo | registro consolidado desta auditoria |
| `docs/README.md` | edição pontual | adicionar a entrada do documento 38 ao índice |

Nenhum documento maduro (09, 12, 15, 16, 28, 29) foi reescrito. Nenhum arquivo
fora de `docs/` foi alterado. Nenhum binário, GRF, DLL, asset, arquivo de
`conf/import`, override de progressão ou core foi tocado.

## 10. Passos executados nesta auditoria

1. Gate de repositório na base `origin/dev` (fetch, verificação de
   fast-forward, criação de branch a partir do `origin/dev` atual).
2. Reconstrução da cadeia documental (leitura dos documentos canônicos).
3. Auditoria de `PACKETVER` (fonte + build) — sem checkout do rAthena no repo de
   documentação; confirmação por runtime na VPS.
4. Auditoria remota da VPS **somente leitura** (host, commit, serviços, portas,
   modo de conta).
5. Reconciliação da cadeia WARP contra os registros mais recentes.
6. Redação deste registro consolidado, sem duplicar conteúdo maduro.

## 11. Testes

- `git diff --check` (sem conflitos/whitespace ruim).
- Validador de assets do cliente ([`scripts/validate-client-assets.py`](../scripts/validate-client-assets.py)).
- Verificação de links internos alterados.
- Confirmação de ausência de binários e de segredos no diff.

## 12. Riscos

- **Incompatibilidade de `PACKETVER`:** mitigada pela análise estrutural do lado
  do servidor ([29](29-compatibilidade-cliente-2021-11-05-packetver.md)); prova
  final é o teste de login.
- **Executável incorreto / preparação sem reconhecimento:** mitigado pela
  disciplina de [28](28-decisao-ferramenta-preparacao-cliente.md) (reconhecer o
  `Ragexe` antes de qualquer patch; parar se não reconhecer).
- **Redistribuição não autorizada:** mitigada por
  [16](16-politica-distribuicao-cliente.md), `.gitignore` e
  `validate-client-assets.py`.
- **Antivírus / dependências ausentes:** analisar origem, hash e assinatura; não
  desativar proteções ([15](15-cliente-primeiro-acesso.md)).
- **Endpoint incorreto:** endpoint real nunca versionado; usar template
  [`client/templates/clientinfo.xml.example`](../client/templates/clientinfo.xml.example).
- **Cliente funcionar só na máquina de montagem / divergência VPS × repositório:**
  mitigado por auditoria de runtime e teste em pasta limpa.
- **Base 255 sem 3ª classe exigir balanceamento posterior:** registrado; fora do
  escopo desta etapa; nenhuma progressão alterada.

## 13. Rollback

- Documento de auditoria: o rollback é reverter o commit desta branch (antes do
  merge, fechar o PR sem merge; após squash, `git revert` do commit squash em
  `dev`).
- **Nenhuma** mudança operacional foi feita: não há `PACKETVER`, build, serviço,
  firewall, conta, banco ou binário a reverter.
- A branch `audit/2p-e-c2-gate-2` foi **preservada**; a VPS permanece inalterada.

## 14. Estado de verificação

- **Fato (reconfirmado por runtime, 2026-08-03):** host/commit/working tree da
  VPS; serviços `active/running`; portas `6900/6121/5121`; `PACKETVER` de fonte
  `20211103` sem override; `new_account: no`.
- **Fato (registros canônicos):** cadeia WARP no GATE 2 concluído; GATE 3 não
  autorizado.
- **Inferência:** compatibilidade do cliente 2021-11-05 **PROVÁVEL**.
- **Pendência:** preparação autorizada do executável, `clientinfo` real, endpoint
  aplicado, teste de login controlado e conta de homologação provisionada.
- **Nota:** decisão técnica e de conformidade do projeto, **não** parecer
  jurídico.

## Referências

- [04](04-operacao-vps.md), [09](09-cliente-baseline-protocolo.md),
  [11](11-servicos-systemd-rathena.md), [12](12-configuracao-packetver.md),
  [13](13-credenciais-sql-rathena.md), [14](14-progressao-base-255-overrides.md).
- [15](15-cliente-primeiro-acesso.md), [16](16-politica-distribuicao-cliente.md),
  [28](28-decisao-ferramenta-preparacao-cliente.md),
  [29](29-compatibilidade-cliente-2021-11-05-packetver.md).
- Cadeia WARP: [30](30-auditoria-estatica-warp.md),
  [33](33-plano-auditoria-binaria-offline-warp.md),
  [35](35-resultado-gate-0-proveniencia-warp.md),
  [37](37-resultado-gate-2-materializacao-integridade-warp.md).
- Validador e política de arquivos:
  [`scripts/validate-client-assets.py`](../scripts/validate-client-assets.py),
  [`.gitignore`](../.gitignore).
