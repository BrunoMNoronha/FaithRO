# Cliente, protocolo e baseline de compatibilidade

> **Escopo:** documento de referência e planejamento. Nenhuma alteração de
> código, banco ou configuração operacional é executada por este documento.
> Todos os comandos de compilação e teste são **planejados para execução
> futura** por um operador humano, fora desta tarefa.

## Objetivo

Registrar, de forma rastreável, o cliente-alvo e o protocolo adotados pelo
FaithRO - Laus Deo, deixando explícita a diferença entre conceitos que são
frequentemente confundidos na comunidade (`Ragexe`, `PACKETVER_RE`, Renewal e
Pre-Renewal) e definindo o processo de validação de compatibilidade
cliente-servidor.

## Contexto e premissas

- Emulador: rAthena.
- Sistema: Ubuntu Server 22.04, MariaDB.
- **Commit upstream de referência:** `7f080871c8b3bbe7a79027194633201c63422ee1`
  (abreviado `7f080871c`). As afirmações "confirmado no código" deste documento
  foram verificadas **neste commit fixado** no GitHub (acesso em 2026-07-10).
- Este repositório é de **documentação/planejamento** e **não** contém um
  checkout do rAthena. Diferencie sempre três estados distintos:
  - **commit upstream consultado** (`7f080871c`, verificável no GitHub);
  - **commit efetivamente instalado na VPS** (`/opt/faithro/rathena`) — **não
    verificado nesta tarefa**;
  - **configuração efetivamente compilada na VPS** — **não verificada nesta
    tarefa**.
- Terceiras classes: desabilitadas por decisão de conteúdo do FaithRO.
- Base level máximo planejado: 255, com atributo/status natural máximo
  individual planejado em 185 e ASPD máxima planejada em 197, todos sujeitos
  a balanceamento próprio e ainda não implantados (ver
  [00-base-conhecimento.md](00-base-conhecimento.md); o antigo base level
  máximo 185 foi substituído em 2026-07-10, e o atributo máximo 187 foi
  posteriormente corrigido para 185).

## 1. Baseline do projeto

| Item | Valor |
| --- | --- |
| `PACKETVER` | `20211103` |
| Cliente-alvo | `2021-11-03_Ragexe` |
| Família do executável | `Ragexe` |
| Modo de jogo do servidor | decisão independente do cliente (ver seção 4) |
| Terceiras classes | desabilitadas por decisão do FaithRO |
| Base level máximo | 255 (planejado), sujeito a balanceamento próprio |
| Atributo natural máximo individual | 185 (planejado), sujeito a balanceamento próprio |
| ASPD máxima | 197 (planejada), sujeita a balanceamento próprio |

`2021-11-03_Ragexe` **não** é "o cliente mais novo". Ele é o **cliente de
referência / baseline conservador** adotado pelo projeto, escolhido por
alinhamento com o valor padrão do rAthena e com a matriz de CI oficial. Clientes
posteriores podem ter suporte parcial ou comunitário, mas **não** substituem o
baseline sem análise de compatibilidade, testes, decisão técnica, documentação e
plano de rollback.

## 2. Compatibilidade não é determinada só pelo nome

Deixe explícito no projeto:

- o nome do executável **não** garante compatibilidade;
- a data no nome do arquivo **não** garante compatibilidade;
- renomear o executável **não** altera o protocolo dele;
- um cliente mais novo **não** é automaticamente melhor nem compatível;
- o `PACKETVER` do servidor precisa corresponder à data e à estrutura de pacotes
  do cliente;
- a variante do executável (`Ragexe` vs `RagexeRE` etc.) precisa ser confirmada;
- a obfuscação de pacotes precisa estar alinhada entre cliente e servidor;
- os patches aplicados ao cliente precisam ser conhecidos e documentados;
- após qualquer mudança de protocolo, o servidor deve ser **recompilado de forma
  limpa** e reiniciado de forma controlada;
- dados, Lua, XML e configurações externas ao executável também podem causar
  falhas, mesmo com `PACKETVER` correto.

## 3. `Ragexe` versus `PACKETVER_RE`

Estes conceitos **não** são equivalentes:

- **`PACKETVER`** — data do protocolo de comunicação entre cliente e servidor.
  Para o baseline: `PACKETVER=20211103`.
- **`Ragexe`** — família do executável cliente adotado para 3 de novembro de
  2021. Identificação: `2021-11-03_Ragexe`.
- **`PACKETVER_RE`** — macro **interna** do código do rAthena, definida
  automaticamente para certas faixas de datas.

Fato confirmado no código do rAthena no commit `7f080871c`
([`src/config/packets.hpp`](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/config/packets.hpp)):

```c
#ifndef PACKETVER_RE
	#if ( PACKETVER > 20151104 && PACKETVER < 20180704 ) || ( PACKETVER >= 20200902 && PACKETVER <= 20211118 )
		#define PACKETVER_RE
	#endif
#endif
```

Como `20211103` está no intervalo `>= 20200902 && <= 20211118`, o rAthena
**define `PACKETVER_RE` automaticamente** para o baseline. Consequências:

- isso é uma **decisão interna da implementação** do rAthena;
- **não** transforma o executável em `RagexeRE`;
- o cliente-alvo continua sendo `2021-11-03_Ragexe` (família `Ragexe`);
- **não** se deve editar nem forçar manualmente `PACKETVER_RE` apenas para "fazer
  o nome parecer consistente".

> Não documente o cliente-alvo como `2021-11-03_RagexeRE`. Não há evidência
> técnica para isso; a variante adotada é `Ragexe`.

## 4. Renewal, Pre-Renewal e classes

- `PACKETVER` trata do **protocolo**.
- Renewal e Pre-Renewal tratam das **regras do servidor** (mecânicas, fórmulas).
- O mesmo `PACKETVER=20211103` pode ser compilado pelo rAthena em modo
  Pre-Renewal **ou** Renewal — a CI oficial compila ambos (ver
  [10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md)).
- Um cliente de 2021 **não** habilita, por si só, terceiras ou quartas classes.
- A ausência de terceiras classes é controlada **no servidor** (conteúdo e
  balanceamento), não pelo cliente.
- A presença de sprites, interfaces ou dados de 3ª classe no cliente **não**
  significa que o conteúdo esteja habilitado no servidor.
- O base level 255 com atributos naturais até 185, ASPD máxima 197 e sem
  terceiras classes é uma customização do FaithRO e exige balanceamento
  próprio; a exibição de level, atributos e ASPD nesses valores também
  precisa ser validada na interface do cliente.

## 5. Configuração do `PACKETVER` (planejado)

Existem dois mecanismos oficiais. **Nenhum é executado nesta tarefa.**

### 5.1 Pelo processo de compilação

```bash
./configure --enable-packetver=20211103
```

### 5.2 Pelo mecanismo de customização

Arquivo esperado: `src/custom/defines_pre.hpp`

```cpp
#define PACKETVER 20211103
```

> Não editar diretamente o valor padrão em `src/config/packets.hpp`. Prefira o
> mecanismo de customização (`src/custom/defines_pre.hpp`) ou o argumento oficial
> de compilação.

Após qualquer mudança futura no `PACKETVER`: recompilação **limpa** e reinício
controlado dos serviços de login, char e map (`<UNIDADE-LOGIN>`,
`<UNIDADE-CHAR>`, `<UNIDADE-MAP>` — confirmar os nomes reais no ambiente com
`systemctl`, ver [seção de logs](#logs-sem-publicar-dados-reais)).

## 6. Packet obfuscation

Para `PACKETVER=20211103`, o comportamento **não** é simplesmente "obfuscação
ativa". É preciso distinguir a macro geral da atribuição efetiva de chaves.

**Suporte geral compilado.** Em
[`src/config/packets.hpp`](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/config/packets.hpp)
(commit `7f080871c`), a macro `PACKET_OBFUSCATION` é definida para
`PACKETVER >= 20110817`:

```c
#if PACKETVER >= 20110817
	#ifndef PACKET_OBFUSCATION
		#define PACKET_OBFUSCATION
```

**Chaves efetivas para o baseline.** Em
[`src/map/clif_obfuscation.hpp`](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/map/clif_obfuscation.hpp)
(commit `7f080871c`), a atribuição de chaves para clientes posteriores a
`20180307` é **zero**:

```c
#elif PACKETVER > 20180307 // Clients after 2018-03-07bRagexeRE do not obfuscate packets anymore
    packet_keys(0x00000000,0x00000000,0x00000000);
```

Como `20211103 > 20180307`, para o baseline do FaithRO:

- a macro geral `PACKET_OBFUSCATION` permanece **definida** (suporte compilado);
- as **chaves efetivas são zero**;
- **não existe obfuscação efetiva** no comportamento padrão do rAthena para esse
  `PACKETVER`;
- portanto, **não** se deve afirmar que a criptografia/obfuscação está "ativa por
  padrão" para o baseline;
- patches equivalentes a `Disable Packet Encryption` **não** devem ser
  apresentados como obrigatórios sem verificar o executável real;
- chaves customizadas só devem ser consideradas se houver customização
  **explícita e documentada**.

> **Resumo:** para `PACKETVER=20211103`, o suporte geral à packet obfuscation
> permanece compilado via macro `PACKET_OBFUSCATION`. Entretanto,
> `clif_obfuscation.hpp` atribui chaves zero para clientes posteriores a
> `20180307`, indicando ausência de obfuscação efetiva no comportamento padrão do
> baseline. O executável real e seus patches ainda devem ser verificados para
> confirmar que não houve alteração comunitária ou customizada desse
> comportamento.

Itens a verificar na implantação:

- se o executável real do FaithRO mantém o comportamento padrão (chaves zero);
- se algum patch alterou esse comportamento;
- se existe qualquer customização explícita de chaves (nunca registrar chaves
  reais neste repositório);
- que cliente e servidor permaneçam alinhados após qualquer mudança
  (recompilação limpa + teste).

## 7. Web server do rAthena

**Habilitado pelo código para o baseline.** Em
[`src/config/packets.hpp`](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/config/packets.hpp)
(commit `7f080871c`):

```c
#define WEB_SERVER_ENABLE PACKETVER > 20200300
```

Como o baseline é `PACKETVER=20211103` e `20211103 > 20200300`, o resultado é:

```text
WEB_SERVER_ENABLE: habilitado pelo código para o baseline.
```

### 7.1 Confirmado no código (commit `7f080871c`)

- `WEB_SERVER_ENABLE` é verdadeiro para `PACKETVER=20211103`.
- O rAthena possui um componente web dedicado
  ([`src/web/web.cpp`](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/web/web.cpp)).
- Há controladores para recursos como emblemas de guilda
  ([`src/web/emblem_controller.cpp`](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/web/emblem_controller.cpp)),
  com uso de tabelas como `guild_emblems`.
- O arquivo de configuração
  [`conf/web_athena.conf`](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/conf/web_athena.conf)
  define `web_port: 8888` como valor **padrão upstream** e mantém `bind_ip`
  comentado (exemplo `127.0.0.1`).
- Overrides devem ir para `conf/import/web_conf.txt` (modelo em
  [`conf/import-tmpl/web_conf.txt`](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/conf/import-tmpl/web_conf.txt)).

### 7.2 Pendente na implantação do FaithRO

- confirmar se o binário `web-server` foi compilado na VPS;
- confirmar se existe serviço systemd correspondente (`<UNIDADE-WEB>` —
  `Pendente de definição durante a implantação do web server`);
- configurar `conf/import/web_conf.txt`;
- confirmar a porta efetivamente implantada;
- definir bind, firewall e exposição;
- confirmar as tabelas SQL necessárias;
- testar endpoints e recursos;
- testar emblemas de guilda;
- verificar a configuração esperada pelo cliente.

```text
Porta padrão upstream: 8888/tcp.
Porta efetivamente implantada no FaithRO: pendente de validação.
```

> Não afirmar que a porta efetiva do FaithRO já é `8888`. Não recomendar
> exposição pública automática dessa porta. Não configurar nem expor o web server
> nesta tarefa. Não tratar o web server como requisito comprovado para o login
> básico sem teste.

## 8. XML, Lua e configurações externas

Não assumir automaticamente qual arquivo o cliente lê (`clientinfo.xml`,
`sclientinfo.xml`, caminho em GRF ou Lua específico). Documentar somente o que
for **confirmado no cliente legalmente obtido pelo responsável**.

Verificar e documentar, quando o cliente estiver disponível:

- arquivo realmente lido pelo cliente;
- codificação;
- `servicetype`;
- `servertype`;
- endereço;
- porta;
- `langtype`;
- configurações externas e dependências Lua.

Não publicar o IP real do servidor. Usar sempre placeholders:

```text
<IP-VPS>
<IP-CLIENTE>
<USUARIO>
<BANCO>
<PORTA>
<ARQUIVO>
```

## 9. Patches do cliente

Registrar cada patch por nome e finalidade. **Não** apresentar uma lista genérica
de patches como universalmente correta.

| Patch | Obrigatório | Motivo | Risco | Resultado do teste |
| ----- | ----------- | ------ | ----- | ------------------ |
| _(a preencher com o cliente real)_ | Pendente | Pendente | Pendente | Pendente de validação |

Atenção especial a patches relacionados a:

- leitura de pasta `data`;
- leitura de arquivos XML;
- endereço de conexão;
- packet encryption;
- execução sem parâmetros oficiais;
- configurações externas;
- idioma;
- proteção contra erro por arquivos ausentes.

Ferramentas comunitárias devem ser obtidas do repositório ou página oficial do
autor, quando disponível. **Não** armazenar executáveis já modificados.

## 10. Arquivos que podem ser documentados

O projeto **pode** documentar, sobre um cliente que o responsável possua
legalmente:

- nome esperado do executável;
- data de compilação;
- tamanho;
- metadados;
- hash SHA-256 do arquivo (para identificação, não para redistribuição);
- ferramentas abertas utilizadas;
- patches aplicados;
- estrutura de diretórios;
- arquivos próprios do FaithRO e suas configurações;
- processo de validação.

> Um hash identifica um arquivo já possuído legalmente. Um hash **não** concede
> licença de redistribuição.

## 11. Arquivos que NÃO podem ser fornecidos nem versionados

- cliente completo;
- instalador completo;
- GRF oficial;
- executável oficial;
- executável modificado;
- DLL proprietária;
- asset oficial (sprite, mapa, música);
- pacote de tradução com conteúdo não autorizado;
- arquivo obtido de anexo não confiável.

**Não** incluir links diretos para pacotes completos em Mega, Google Drive,
MediaFire ou serviços equivalentes. Links do fórum devem apontar para a
**discussão**, não para anexos.

## 12. Alertas de segurança do cliente

- Não instruir o usuário a ignorar alertas de antivírus.
- Não tratar falso positivo como fato sem análise.
- Não executar arquivos comunitários na VPS.
- Não usar a VPS de produção para modificar o cliente.
- Não aceitar executáveis prontos como fonte confiável.
- Registrar origem, hash e resultado da análise de qualquer ferramenta utilizada.
- Separar ferramentas abertas de binários proprietários.

## 13. Matriz de compatibilidade do cliente

Estados: `Confirmado no código` · `Confirmado em CI oficial` · `Confirmado
externamente` · `Decisão do projeto` · `Pendente de validação`.

| Componente | Valor encontrado | Estado | Evidência |
| --- | --- | --- | --- |
| Commit upstream de referência | `7f080871c` confirmado no GitHub | Confirmado externamente | commit fixado (seção Contexto) |
| Commit instalado na VPS | `7f080871c` — idêntico ao commit upstream de referência | Confirmado em auditoria read-only (2026-07-10) | `/opt/faithro/rathena`, ver [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md) |
| Configuração compilada na VPS | binários `login-server`, `char-server`, `map-server` e `web-server` presentes; flags de compilação (obfuscação, `PACKETVER_RE`) não re-testadas em binário | Parcialmente confirmado | ver [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md) |
| `PACKETVER` | `20211103` | Confirmado no código | `src/config/packets.hpp` @ `7f080871c` |
| `PACKETVER_RE` | definido automaticamente para `20211103` | Confirmado no código | condição em `src/config/packets.hpp` (seção 3) |
| Família do cliente | `2021-11-03_Ragexe` | Decisão do projeto, requer teste real | baseline FaithRO (seção 1) |
| Modo servidor | Pre-Renewal e Renewal ambos suportados; escolha do FaithRO a definir | Confirmado em CI oficial | matriz `mode: ['PRE','RE']` |
| Packet obfuscation | macro definida, mas chaves zero para versões posteriores a `20180307` | Confirmado no código | `clif_obfuscation.hpp` @ `7f080871c` (seção 6) |
| `WEB_SERVER_ENABLE` | verdadeiro para `20211103` | Confirmado no código | `src/config/packets.hpp` @ `7f080871c` (seção 7) |
| Web server implantado | binário compilado, mas sem unidade systemd nem processo ativo | Confirmado em auditoria read-only (2026-07-10) — não implantado | ver [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md) |
| Porta web efetiva | nenhuma porta em escuta (não implantado) | Confirmado em auditoria read-only (2026-07-10) | ver [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md) |
| Arquivo XML do cliente | requer teste com cliente real | Pendente de validação | requer cliente real |
| Login | requer teste com cliente real | Pendente de validação | requer implantação |
| Seleção de personagem | requer teste com cliente real | Pendente de validação | requer implantação |
| Entrada no mapa | requer teste com cliente real | Pendente de validação | requer implantação |
| Movimento | requer teste com cliente real | Pendente de validação | requer implantação |
| NPCs | requer teste com cliente real | Pendente de validação | requer implantação |
| Inventário | requer teste com cliente real | Pendente de validação | requer implantação |
| Guilda/emblema | depende do web server implantado | Pendente de validação | seção 7 |

> Não preencher como funcional aquilo que não foi testado.

## 14. Plano mínimo de testes do cliente (planejado)

Portas de referência do projeto (padrão rAthena; confirmar na implantação):
login `6900/tcp`, char `6121/tcp`, map `5121/tcp`; web server (upstream)
`8888/tcp`, com porta efetiva **pendente de validação**. Durante testes, as
portas do jogo devem permanecer **restritas ao IP autorizado** e **não** ser
abertas para `Anywhere` sem decisão formal documentada. Ver
[04-operacao-vps.md](04-operacao-vps.md).

### Inicialização

- executável inicia sem erro;
- ausência de DLL não localizada;
- ausência de falha imediata;
- janela e resolução carregam.

### Conexão

- cliente alcança `<IP-VPS>:6900`;
- login-server registra tentativa válida;
- não ocorre `Unknown packet`;
- não ocorre encerramento anormal por divergência de pacotes;
- comportamento de packet obfuscation do cliente compatível com o servidor
  (para o baseline, o padrão do rAthena é sem obfuscação efetiva — seção 6).

### Personagem

- lista de personagens abre;
- personagem pode ser criado, quando permitido;
- personagem pode ser selecionado;
- map-server recebe a conexão.

### Mapa

- personagem entra no mapa;
- movimento funciona;
- NPCs aparecem e a interação funciona;
- inventário abre e itens aparecem corretamente;
- mensagens de chat funcionam.

### Recursos adicionais

- grupo, guilda, emblema (depende do web server), armazém, comércio, atalhos,
  interface, tradução, reconexão.

### Logs (sem publicar dados reais)

Os nomes efetivos das unidades systemd foram **confirmados por auditoria
read-only** em 2026-07-10: `faithro-login.service`, `faithro-char.service` e
`faithro-map.service` (detalhes, propriedades e runbook completo em
[11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md)). Mesmo assim,
antes de operar, **redescubra** as unidades no ambiente — reinstalações
futuras podem alterar os nomes:

```bash
systemctl list-unit-files --type=service |
  grep -Ei 'faithro|rathena|login|char|map|web'
# alternativa, incluindo unidades inativas:
systemctl list-units --type=service --all |
  grep -Ei 'faithro|rathena|login|char|map|web'
```

Depois de confirmar as unidades corretas, consulte os logs substituindo os
placeholders pelos nomes reais:

```bash
journalctl -u <UNIDADE-LOGIN> --since "-10min" -n 200
journalctl -u <UNIDADE-CHAR>  --since "-10min" -n 200
journalctl -u <UNIDADE-MAP>   --since "-10min" -n 200
# web server, quando implantado:
journalctl -u <UNIDADE-WEB>   --since "-10min" -n 200
```

Observações importantes:

- revise os resultados da descoberta antes de usar qualquer nome;
- termos genéricos como `login`, `char`, `map` e `web` podem encontrar serviços
  **não relacionados** ao FaithRO — confirme a unidade correta antes de consultar
  logs ou reiniciar serviços;
- **não** crie uma unidade apenas para fazer a documentação coincidir;
- registre os nomes efetivos, posteriormente, no documento de implantação
  systemd (a criar);
- os nomes `faithro-login.service`, `faithro-char.service` e
  `faithro-map.service` estão formalmente documentados em
  [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md); ainda
  assim, confirme os nomes no ambiente com `systemctl` antes de executar os
  comandos, pois o ambiente pode mudar em reinstalações futuras.

> Não copiar nomes de contas, IPs reais ou dados de jogadores para a
> documentação. Usar limites de linhas e de tempo.

## Riscos

- Divergência cliente-servidor por `PACKETVER` incorreto → `Unknown packet` /
  desconexão.
- Assumir obfuscação "ativa" quando o padrão do baseline é sem obfuscação efetiva
  → configuração e diagnóstico errados.
- Web server habilitado pelo código, mas não implantado/configurado → emblema de
  guilda indisponível.
- Documentar como "compatível" ou "funcional" algo não testado → decisão errada
  de baseline.
- Assumir arquivo XML/Lua sem confirmar no cliente real → configuração inválida.
- Confundir commit upstream de referência com o commit efetivamente instalado na
  VPS.

## Rollback

- Este documento não altera ambiente; o rollback documental é reverter o commit
  desta branch.
- Para mudanças futuras de `PACKETVER`/obfuscação/web server (em tarefa própria):
  manter backup do binário anterior e das configs, recompilar limpo, e reverter
  para o binário/config anteriores em caso de falha, sempre com backup
  previamente criado.

## Estado de verificação

- **Confirmado no código do rAthena no commit `7f080871c` (referência externa,
  acesso em 2026-07-10):**
  - default `PACKETVER=20211103`;
  - definição automática de `PACKETVER_RE` para `20211103`;
  - `PACKET_OBFUSCATION` definida para `PACKETVER >= 20110817`, porém com chaves
    efetivas **zero** para clientes posteriores a `20180307`
    (`clif_obfuscation.hpp`);
  - `WEB_SERVER_ENABLE` verdadeiro para `20211103`
    (`#define WEB_SERVER_ENABLE PACKETVER > 20200300`);
  - porta padrão upstream do web server `8888/tcp` (`conf/web_athena.conf`).
- **Confirmado em CI oficial:** `20211103` na matriz de build, em modos `PRE` e
  `RE`.
- **Confirmado por auditoria read-only na VPS em 2026-07-10** (ver
  [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md)): commit
  instalado (`7f080871c`, idêntico ao de referência); working tree limpo;
  unidades systemd `faithro-login`, `faithro-char`, `faithro-map` (enabled,
  active); portas `6900`, `6121`, `5121`; binário `web-server` compilado, mas
  sem unidade/processo/porta.
- **Pendente de verificação em implantação/checkout local:** flags efetivas de
  compilação do binário (obfuscação, `PACKETVER_RE`) não re-testadas fora do
  código-fonte; comportamento real do executável do cliente; todos os testes
  de jogo; implantação completa do web server (unidade, configuração, porta,
  firewall, testes de endpoint).

## Referências

Ver a tabela completa e classificada por confiança em
[10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md).
</content>
