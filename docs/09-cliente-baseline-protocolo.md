# Cliente, protocolo e baseline de compatibilidade

> **Escopo:** documento de referência e planejamento. Nenhuma alteração de
> código, banco ou configuração operacional é executada por este documento.
> Todos os comandos de compilação e teste são **planejados para execução
> futura** por um operador humano, fora desta tarefa.

## Objetivo

Registrar, de forma rastreável, o cliente-alvo e o protocolo adotados pelo
FaithRO - Laos Deos, deixando explícita a diferença entre conceitos que são
frequentemente confundidos na comunidade (`Ragexe`, `PACKETVER_RE`, Renewal e
Pre-Renewal) e definindo o processo de validação de compatibilidade
cliente-servidor.

## Contexto e premissas

- Emulador: rAthena.
- Sistema: Ubuntu Server 22.04, MariaDB.
- Commit de referência informado para o rAthena: `7f080871c` (a confirmar no
  checkout real quando o emulador for clonado — ver [Estado de verificação](#estado-de-verificacao)).
- Este repositório é de **documentação/planejamento**. Ele **não** contém um
  checkout do rAthena; portanto, as macros do emulador não podem ser confirmadas
  a partir deste repositório e foram verificadas no código-fonte oficial do
  rAthena (`master`) como referência externa.
- Terceiras classes: desabilitadas por decisão de conteúdo do FaithRO.
- Level máximo: 185, sujeito a balanceamento próprio (ver
  [00-base-conhecimento.md](00-base-conhecimento.md)).

## 1. Baseline do projeto

| Item | Valor |
| --- | --- |
| `PACKETVER` | `20211103` |
| Cliente-alvo | `2021-11-03_Ragexe` |
| Família do executável | `Ragexe` |
| Modo de jogo do servidor | decisão independente do cliente (ver seção 4) |
| Terceiras classes | desabilitadas por decisão do FaithRO |
| Level máximo | 185, sujeito a balanceamento próprio |

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

Fato confirmado no código oficial do rAthena (`src/config/packets.hpp`, `master`):

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
- O level 185 sem terceiras classes é uma customização do FaithRO e exige
  balanceamento próprio.

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
controlado dos serviços `faithro-login`, `faithro-char` e `faithro-map`.

## 6. Packet obfuscation

Fato confirmado no código oficial do rAthena (`src/config/packets.hpp`, `master`):

```c
#if PACKETVER >= 20110817
	#ifndef PACKET_OBFUSCATION
		#define PACKET_OBFUSCATION
```

Ou seja, para `PACKETVER=20211103` a **obfuscação de pacotes está ativa por
padrão** no servidor. As três chaves de obfuscação ficam **indefinidas por
padrão** e, quando usadas, devem ser especificadas em configuração de
customização (nunca registrar chaves reais neste repositório).

Regra obrigatória de alinhamento:

- se o cliente estiver com a criptografia de pacotes **desabilitada** (patch
  equivalente a "Disable Packet Encryption"), o servidor deve estar configurado
  de forma **compatível**;
- se o servidor **mantiver** a obfuscação ativa, o cliente deve usar configuração
  compatível;
- qualquer alteração exige recompilação limpa;
- o estado final deve ser **documentado e testado**.

> Não recomende desabilitar a obfuscação de forma automática. É uma decisão de
> alinhamento que exige teste. Não registre chaves reais na documentação.

Itens a verificar na implantação:

- `PACKET_OBFUSCATION` ativo no servidor (padrão para este `PACKETVER`);
- se o cliente mantém a criptografia de pacotes;
- se foi aplicado patch equivalente a "Disable Packet Encryption";
- se existem chaves customizadas;
- se cliente e servidor estão alinhados.

## 7. Web server do rAthena

O rAthena moderno possui um componente de **web server** (usado, entre outros,
por emblemas de guilda). Estado de verificação:

- **Confirmado (comunidade/issues oficiais):** para clientes/pacotes modernos, o
  emblema de guilda passa a depender do web server; ele exige as tabelas SQL
  próprias (ex.: `guild_emblems`) importadas no banco.
- **Pendente de verificação direta no código:** o gating exato de compilação
  (macro e faixa de `PACKETVER`) não foi confirmado a partir de um checkout local
  nesta tarefa, pois este repositório não contém o código do rAthena.

A documentar na implantação (tarefa própria):

- se o web server foi compilado;
- se existe serviço systemd correspondente;
- qual porta é usada e se é interna ou pública;
- quais recursos dependem dele (ex.: emblema de guilda);
- se as tabelas necessárias foram importadas;
- se o cliente tem configuração externa apontando para o serviço.

Estado atual no FaithRO:

```text
Web server: pendente de validação e implantação em tarefa própria.
```

> Não tratar o web server como requisito comprovado para o login básico sem
> teste. Não configurar nem expor o web server nesta tarefa.

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

Estados: `Confirmado no código` · `Confirmado em CI oficial` · `Decisão do
projeto` · `Pendente de validação`.

| Componente | Valor esperado | Valor encontrado | Estado | Evidência |
| --- | --- | --- | --- | --- |
| Commit rAthena | `7f080871c` | Não verificável neste repositório (sem checkout do rAthena) | Pendente de validação | — |
| `PACKETVER` | `20211103` | `20211103` (default upstream) | Confirmado no código | `src/config/packets.hpp` do rAthena `master` |
| Família do cliente | `Ragexe` | `Ragexe` | Decisão do projeto | Baseline FaithRO (seção 1) |
| Data do cliente | `2021-11-03` | `2021-11-03` | Decisão do projeto | Baseline FaithRO (seção 1) |
| Macro interna | determinada pelo código | `PACKETVER_RE` definida automaticamente para `20211103` | Confirmado no código | condição em `src/config/packets.hpp` (seção 3) |
| Modo servidor | conforme configuração do FaithRO | Pre-Renewal e Renewal ambos suportados pelo upstream; escolha do FaithRO a definir | Confirmado em CI oficial | matriz `mode: ['PRE','RE']` |
| Packet obfuscation | cliente e servidor alinhados | ativa por padrão no servidor (`PACKETVER >= 20110817`) | Confirmado no código | `src/config/packets.hpp` (seção 6) |
| Arquivo XML | confirmado por teste | — | Pendente de validação | requer cliente real |
| Web server | confirmado ou pendente | — | Pendente de validação | ver seção 7 |
| Login | funcional | — | Pendente de validação | requer implantação |
| Seleção de personagem | funcional | — | Pendente de validação | requer implantação |
| Entrada no mapa | funcional | — | Pendente de validação | requer implantação |
| Movimento | funcional | — | Pendente de validação | requer implantação |
| NPCs | funcionais | — | Pendente de validação | requer implantação |
| Inventário | funcional | — | Pendente de validação | requer implantação |
| Guilda/emblema | funcional ou pendente | — | Pendente de validação | depende do web server |

## 14. Plano mínimo de testes do cliente (planejado)

Portas de referência do projeto (padrão rAthena; confirmar na implantação):
login `6900/tcp`, char `6121/tcp`, map `5121/tcp`. Durante testes, as portas do
jogo devem permanecer **restritas ao IP autorizado** e **não** abertas para
`Anywhere` sem decisão formal documentada. Ver
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
- não ocorre encerramento anormal por divergência de pacotes.

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

- grupo, guilda, emblema, armazém, comércio, atalhos, interface, tradução,
  reconexão.

### Logs (sem publicar dados reais)

```bash
journalctl -u faithro-login --since "-10min" -n 200
journalctl -u faithro-char  --since "-10min" -n 200
journalctl -u faithro-map   --since "-10min" -n 200
```

> Não copiar nomes de contas, IPs reais ou dados de jogadores para a
> documentação. Usar limites de linhas e de tempo.

## Riscos

- Divergência cliente-servidor por `PACKETVER` incorreto → `Unknown packet` /
  desconexão.
- Obfuscação desalinhada entre cliente e servidor → falha de login.
- Web server ausente/não configurado → emblema de guilda indisponível.
- Documentar como "compatível" algo não testado → decisão errada de baseline.
- Assumir arquivo XML/Lua sem confirmar no cliente real → configuração inválida.

## Rollback

- Este documento não altera ambiente; o rollback documental é reverter o commit
  desta branch.
- Para mudanças futuras de `PACKETVER`/obfuscação (em tarefa própria): manter
  backup do binário anterior e das configs, recompilar limpo, e reverter para o
  binário/config anteriores em caso de falha, sempre com backup previamente
  criado.

## Estado de verificação

- **Confirmado no código do rAthena `master` (referência externa, acesso em
  2026-07-10):** default `PACKETVER=20211103`; definição automática de
  `PACKETVER_RE` para `20211103`; `PACKET_OBFUSCATION` ativo por padrão para
  `PACKETVER >= 20110817`.
- **Confirmado em CI oficial:** `20211103` na matriz de build, em modos `PRE` e
  `RE`.
- **Pendente de verificação em checkout local:** commit `7f080871c`; gating de
  compilação do web server; qualquer valor efetivamente compilado na VPS.

## Referências

Ver a tabela completa e classificada por confiança em
[10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md).
</content>
</invoke>
