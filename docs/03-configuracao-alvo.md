# Configuração alvo de gameplay

> **Escopo:** documento de decisão técnica e documentação. Nenhuma alteração de
> código, banco de dados, rates, tabela de EXP, level máximo, NPCs, classes,
> configuração da VPS ou firewall é executada por este documento. Nenhum
> serviço foi reiniciado e nenhum binário foi recompilado para produzir este
> texto.

## Objetivo

Definir formalmente a **referência mecânica** (Pre-Renewal ou Renewal) que
servirá de base para as próximas configurações do FaithRO - Laus Deo,
separando explicitamente seis conceitos que a comunidade costuma tratar como
equivalentes:

1. modo mecânico;
2. conteúdo disponível;
3. episódio histórico;
4. protocolo do cliente;
5. classes permitidas;
6. level máximo customizado.

Referências: issue `#6 — [Config] Definir episódio/referência mecânica`;
commit upstream de referência `7f080871c8b3bbe7a79027194633201c63422ee1`
(`7f080871c`); baseline de protocolo `PACKETVER=20211103`; cliente
`2021-11-03_Ragexe` (ver
[09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md)).

## Identidade

- Nome: FaithRO - Laus Deo
- Estilo: old school/high rate
- Estado-alvo de 3ª classes: bloqueadas por política; validação operacional
  na issue #9 (ver seção [Classes](#classes))
- Base level máximo planejado: 255; implantação e balanceamento na issue #8
  (ver seção [Base level 255, atributos máximos 185 e ASPD 197](#base-level-255-atributos-máximos-185-e-aspd-197))
- Atributo/status natural máximo individual planejado: 185; implantação e
  validação na issue #8
- ASPD máxima planejada: 197; implantação e validação na issue #8
- Job level máximo: pendente de definição para cada classe permitida
- Decisão histórica: o antigo base level máximo 185 foi substituído em
  2026-07-10 por base level máximo 255.
- Decisão posterior: o atributo máximo inicialmente registrado como 187 foi
  corrigido para 185, e a ASPD máxima planejada foi definida em 197.
- Público: comunidade pequena/média
- Sem fins lucrativos

## Decisão de mecânica

```text
O FaithRO adotará Pre-Renewal como referência mecânica inicial.
```

Esta decisão é registrada nesta tarefa como **decisão técnica documentada**,
confirmada pela auditoria de build descrita em
[Estado atual do build](#estado-atual-do-build). Nenhuma mudança operacional
foi realizada para produzir esta decisão.

## Conceitos independentes

| Conceito           | Decisão / estado-alvo       | Estado operacional                                |
| ------------------ | ---------------------------- | -------------------------------------------------- |
| Protocolo          | `PACKETVER=20211103`        | confirmado no código e checkout                    |
| Cliente            | `2021-11-03_Ragexe`         | requer validação real com cliente                  |
| Mecânica           | Pre-Renewal                 | configuração registrada do build alinhada          |
| Conteúdo           | curado                       | não inventariado integralmente                     |
| Episódio histórico | ainda não fixado             | não aplicável                                      |
| Classes            | até transclasses             | validação operacional pendente                     |
| 3ª classes         | bloqueadas por política      | pendente da issue #9                               |
| Base level máximo  | 255                          | ainda não configurado ou validado (issue #8)       |
| Atributo natural máximo | 185 por atributo        | ainda não configurado ou validado (issue #8)       |
| ASPD máxima        | 197                          | ainda não configurada ou validada (issue #8)       |
| Job level          | definir por classe           | pendente das issues #8 e #9                        |
| Rates              | high rate a definir           | pendente da issue #7                               |

Nenhuma linha desta tabela decorre automaticamente de outra. Em particular:

- `PACKETVER=20211103` **não** obriga o servidor a operar em Renewal (o mesmo
  `PACKETVER` é compilado pela CI oficial em ambos os modos, `PRE` e `RE` —
  ver [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md));
- Pre-Renewal **não** bloqueia sozinho as 3ª classes — isso é política de
  conteúdo tratada na issue #9 (ver [Classes](#classes));
- Pre-Renewal **não** define sozinho o base level máximo 255, o atributo
  natural máximo 185 nem a ASPD máxima 197 — isso é customização tratada na
  issue #8 (ver
  [Base level 255, atributos máximos 185 e ASPD 197](#base-level-255-atributos-máximos-185-e-aspd-197));
- Pre-Renewal **não** define sozinho o conteúdo (mapas, quests, itens) — isso
  é curadoria pendente (ver [Conteúdo e episódio](#conteúdo-e-episódio)).

## Comparação Pre-Renewal × Renewal

| Critério                                 | Pre-Renewal                   | Renewal sem 3ª classes                           |
| ----------------------------------------- | ------------------------------ | -------------------------------------------------- |
| Alinhamento com proposta old school       | alto                           | parcial                                            |
| Fórmulas de atributos                     | clássicas                      | Renewal                                            |
| Cast                                      | clássico                       | VCT/FCT Renewal                                    |
| EXP por diferença de level                | sem algoritmo Renewal          | algoritmo Renewal                                  |
| Drop por diferença de level               | sem algoritmo Renewal          | algoritmo Renewal                                  |
| ASPD                                      | clássica                       | Renewal                                            |
| Dano modificado por base level            | sem `RENEWAL_LVDMG`            | com `RENEWAL_LVDMG`                                |
| Base level 255                            | customização extrema; exige revisão das fórmulas clássicas | também exige validação própria; Renewal não garante balanceamento nesse limite sem 3ª classes |
| Atributos naturais até 185                | exige revisão de fórmulas e custos clássicos | também não possui balanceamento garantido          |
| ASPD máxima 197                           | exige validação por classe, arma e buffs | também exige validação própria                     |
| Bloqueio de 3ª classes                    | ainda precisa ser configurado  | ainda precisa ser configurado                      |
| Conteúdo disponível                       | precisa ser curado             | precisa ser curado                                 |
| Complexidade de balanceamento             | alta por combinar base level 255, atributos naturais 185, ASPD 197 e ausência de 3ª classes | alta por combinar fórmulas Renewal, progressão customizada e remoção das 3ª classes |

Nenhuma das duas colunas elimina a necessidade de balanceamento próprio: a
diferença está em **qual** conjunto de fórmulas e ajustes precisa ser
revisado, não em ausência de trabalho.

## Justificativa

A escolha por Pre-Renewal se apoia em:

- melhor alinhamento com a proposta old school já registrada em
  [00-base-conhecimento.md](00-base-conhecimento.md) e no
  [README.md](../README.md);
- melhor alinhamento com progressão até transclasses;
- evita adotar fórmulas Renewal apenas porque o cliente de referência é de
  2021 — protocolo e mecânica são decisões independentes (ver
  [Conceitos independentes](#conceitos-independentes));
- mantém protocolo e mecânica como decisões independentes, documentadas
  separadamente;
- facilita comunicar a identidade do servidor à comunidade;
- permite curadoria posterior de conteúdo sem amarrar o projeto a um episódio
  histórico incorreto.

Registros explícitos:

```text
O cliente 2021-11-03_Ragexe e o PACKETVER=20211103 não obrigam o servidor a
operar em Renewal.
```

```text
A ausência de 3ª classes é uma política de conteúdo e progressão, não uma
consequência automática de PRERE.
```

## Estado atual do build

Auditoria **read-only** executada em `/opt/faithro/rathena` via acesso SSH já
configurado (alias local, sem publicação de host, usuário ou porta reais).
Nenhum arquivo foi alterado, nenhum serviço foi iniciado, parado ou
reiniciado, nenhum binário foi recompilado.

Evidência coletada:

```text
git status --short --branch  → ## master...origin/master (working tree limpo)
git rev-parse HEAD            → 7f080871c8b3bbe7a79027194633201c63422ee1
git log -1 --oneline          → 7f080871c Fix compiler errors after skill split (#10043)
```

O commit instalado é **idêntico** ao commit upstream de referência já
registrado em [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md)
e [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md).

Evidência de compilação (`config.log`):

```text
config.log:7:   $ ./configure --enable-prere=yes --enable-epoll=yes
config.log:878: configure:7128: CPPFLAGS= ... -DSOCKET_EPOLL -DPRERE ... -DHAVE_MONOTONIC_CLOCK
config.log:997: CPPFLAGS=' ... -DSOCKET_EPOLL -DPRERE ... -DHAVE_MONOTONIC_CLOCK'
```

`src/custom/defines_pre.hpp` existe no checkout, mas está **vazio** (apenas o
guard de inclusão do template padrão) — ou seja, a macro `PRERE` **não** vem
de um override manual nesse arquivo, e sim da flag `--enable-prere=yes`
passada ao `./configure`, que o processo de build propagou efetivamente para
`CPPFLAGS` (`-DPRERE`) na compilação registrada em `config.log`.

Conforme [src/config/renewal.hpp](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/config/renewal.hpp)
no commit `7f080871c`, com `PRERE` definido, o bloco `#ifndef PRERE` desse
arquivo — que define `RENEWAL`, `RENEWAL_CAST`, `RENEWAL_DROP`,
`RENEWAL_EXP`, `RENEWAL_LVDMG`, `RENEWAL_ASPD` e `RENEWAL_STAT` — não define
essas macros Renewal gerais listadas naquele arquivo. Esta conclusão está
limitada ao arquivo e ao mecanismo analisados: pode haver configurações
específicas em outros arquivos, conteúdo Renewal no banco, comportamentos
independentes dessas macros ou customizações futuras.

**Classificação final:** `Pre-Renewal confirmado na configuração registrada do build`.

Esta classificação é a mais forte das quatro categorias possíveis
(`Pre-Renewal confirmado na configuração registrada do build` ·
`Renewal confirmado na configuração registrada do build` ·
`Fonte padrão Renewal, mas build efetivo inconclusivo` ·
`Pendente de validação`), porque a evidência não vem apenas da leitura de
`renewal.hpp` (que descreve o padrão quando `PRERE` **não** está definido),
mas da flag de compilação efetivamente registrada em `config.log` e
propagada para `CPPFLAGS`. `config.log` sozinho, porém, não comprova de forma
independente a proveniência dos binários atualmente em execução (ver tabela
abaixo).

| Camada                                       | Estado                                                            |
| --------------------------------------------- | ------------------------------------------------------------------ |
| Código-fonte                                  | `PRERE` desabilita o bloco de macros Renewal em `renewal.hpp`      |
| Configuração registrada                       | `--enable-prere=yes` e `-DPRERE` confirmados em `config.log`       |
| Binários presentes                            | confirmados em auditoria anterior                                  |
| Vínculo entre `config.log` e binários atuais  | não atestado por hash, metadata de build ou inspeção equivalente   |
| Comportamento em gameplay                     | ainda requer testes funcionais                                     |

**Limitações:** esta auditoria não reexecutou os binários nem inspecionou
símbolos/strings do executável compilado para reconfirmar a macro em tempo de
execução; a evidência se apoia no log de configuração (`config.log`) do
próprio processo de build, que é a fonte mais forte disponível sem recompilar
nada. `config.log` não comprova, de forma independente, que os binários
atualmente em execução foram gerados exatamente por esse build, que não
foram substituídos depois, ou que não houve cópia de binários de outro
ambiente. Não recompile para "confirmar ainda mais" — isso seria uma mudança
operacional fora do escopo desta tarefa; a limitação de proveniência não
bloqueia a decisão documental registrada nesta tarefa.

## Conteúdo e episódio

Não foi fixado, nesta tarefa, um número de episódio histórico. Antes de fixar
um episódio, seria necessário validar mapas, cidades, quests, instâncias,
monstros, itens, equipamentos, NPCs, classes expandidas, eventual conteúdo
Renewal misturado no banco do rAthena, compatibilidade com transclasses e
impacto econômico — nenhum desses itens foi auditado aqui.

```text
Referência de conteúdo inicial:
conteúdo curado compatível com a era de transclasses, sem compromisso com uma
reprodução integral de episódio oficial específico.
```

```text
Decisão futura:
a lista exata de mapas, quests, instâncias, equipamentos e classes expandidas
será definida em tarefa própria de curadoria de conteúdo.
```

"Pre-Renewal" é a referência **mecânica** (fórmulas e comportamento do
servidor), não uma reprodução histórica integral de um episódio numerado.

## Classes

Permitidas inicialmente:

- 1st classes;
- 2nd classes;
- Transclasses.

Bloqueadas por política de conteúdo (não por consequência automática de
`PRERE`):

- 3ª classes;
- evoluções posteriores que quebrem a proposta old school.

Pre-Renewal **não** é garantia de bloqueio completo de 3ª classes, evoluções
posteriores, NPCs de troca de classe, comandos administrativos, job changers
customizados ou itens/quests de mudança de job. A issue #9 permanece
necessária e deverá validar:

- job changer;
- NPCs oficiais;
- comandos administrativos;
- scripts customizados;
- permissões de GM;
- criação direta de personagens para teste;
- classes expandidas;
- tentativa de troca acima de transclasse;
- regressão após atualizações.

### Expanded classes

Nenhuma decisão definitiva é tomada nesta tarefa. Opções registradas:

```text
Opção A — bloquear todas inicialmente.
Opção B — permitir apenas classes expandidas compatíveis com a proposta.
Opção C — liberar progressivamente após testes.
```

Recomendação inicial (não substitui tarefa própria de conteúdo e
balanceamento):

```text
Bloquear ou manter indisponíveis até decisão específica de conteúdo e
balanceamento.
```

## Base level 255, atributos máximos 185 e ASPD 197

Decisão oficial atual:

```text
Base level máximo planejado: 255.
Atributo/status natural máximo individual planejado: 185.
ASPD máxima planejada: 197.
Job level máximo: pendente de definição por classe.
```

```text
Decisão histórica: o antigo base level máximo 185 foi substituído em
2026-07-10 por base level máximo 255.
Decisão posterior: o atributo máximo inicialmente registrado como 187 foi
corrigido para 185, e a ASPD máxima planejada foi definida em 197.
```

O número 185 tem, portanto, dois significados distintos que nunca devem ser
tratados como equivalentes: o **antigo base level máximo 185** (histórico
revogado) e o **atributo natural máximo individual 185** (decisão vigente).

Pre-Renewal não garante balanceamento para base level 255, atributos naturais
até 185 ou ASPD máxima 197. Os valores 255, 185 e 197 são decisões de
projeto. Eles ainda não foram implantados ou validados operacionalmente.

### Terminologia

Estes conceitos são independentes e não devem ser confundidos:

- **base level** — nível base do personagem; alvo: máximo 255;
- **job level** — nível de classe; máximo ainda pendente de definição por
  classe permitida;
- **limite natural individual de atributo (atributo/status máximo)** — valor
  natural máximo que um único atributo (STR, AGI, VIT, DEX, INT, LUK) pode
  atingir por investimento do jogador; alvo: 185;
- **pontos totais de status** — soma de pontos distribuíveis acumulados ao
  longo da progressão; **não** é o mesmo que o limite individual de 185;
- **pontos concedidos por level** — quantos pontos de status cada base level
  concede; a curva ainda precisa ser definida;
- **custo para elevar cada atributo** — pontos necessários para subir um
  atributo em 1; cresce com o valor do atributo e precisa ser validado até
  185;
- **atributos naturais** — valor investido pelo jogador, sujeito ao limite
  individual;
- **atributos finais** — valor com equipamentos, cartas, refinos e buffs;
  podem exceder o valor natural e exigem validação própria;
- **ASPD máxima** — limite de velocidade de ataque do personagem; alvo: 197;
- **AGI** — atributo que influencia a ASPD, mas **não** é a ASPD;
- **velocidade de movimento** — deslocamento do personagem; independente da
  ASPD;
- **delay de ataque** — intervalo entre ataques básicos, derivado da ASPD;
- **delay de skills** — atrasos próprios de cada skill; não são eliminados
  pela ASPD;
- **pós-conjuração (after-cast delay)** — atraso após conjurar skills; não é
  removido automaticamente pela ASPD máxima.

```text
“Atributo máximo 185” significa limite natural individual de STR, AGI, VIT,
INT, DEX e LUK, não quantidade total de pontos.
“ASPD máxima 197” significa limite de velocidade de ataque, não AGI 197,
velocidade de movimento ou remoção de delays de skills.
```

“Level 255” refere-se ao base level, **não** ao job level.

### Riscos e itens de validação (issue #8)

Pre-Renewal com base level 255, atributo natural máximo individual 185, ASPD
máxima 197 e sem 3ª classes é uma **customização de impacto extremo**: as
fórmulas clássicas não foram concebidas para esses limites. Nenhuma falha é
declarada sem teste; os itens abaixo são riscos ou itens de validação
obrigatórios:

- curva de EXP até 255;
- quantidade total de pontos de status;
- concessão de pontos por level;
- custo de atributos até 185;
- STR e dano físico;
- AGI e ASPD (incluindo ASPD máxima);
- VIT, HP, defesa e resistência;
- INT, SP e dano mágico;
- DEX, HIT e cast (incluindo instant cast);
- LUK, crítico e resistências;
- HIT e FLEE nas faixas altas de level;
- resistência a status negativos;
- HP/SP por classe;
- classes normais e transclasses (diferença de poder entre elas);
- equipamentos pensados para faixas de level menores;
- cartas;
- refinos;
- buffs acumuláveis;
- MVPs (trivialização);
- PvM;
- PvP;
- WoE;
- economia;
- consumíveis;
- resetador;
- job changer;
- comandos administrativos;
- scripts que presumam limites menores de level ou atributo;
- interface do cliente (exibição de level e de atributos em valores altos);
- tipos numéricos e limites internos do emulador.

### Riscos e itens de validação da ASPD máxima 197

ASPD máxima 197 é uma **customização de alto impacto** sobre o combate
Pre-Renewal. Não se deve declarar que o servidor já suporta ou limita
corretamente a ASPD em 197 sem teste. Riscos e itens de validação
obrigatórios:

- diferença de ASPD alcançável por classe;
- armas de uma e de duas mãos;
- escudos;
- classes corpo a corpo;
- classes de ataque à distância;
- arcos;
- armas de fogo, caso classes expandidas sejam futuramente permitidas;
- bônus fixos de ASPD;
- bônus percentuais de ASPD;
- AGI;
- DEX, quando aplicável às fórmulas;
- poções de velocidade;
- buffs;
- equipamentos;
- cartas;
- refinos;
- penalidades de ASPD;
- animação do cliente;
- sincronização cliente-servidor;
- ataque automático;
- consumo de munição;
- spam de efeitos visuais;
- carga do map-server;
- PvM;
- MVP;
- PvP;
- WoE;
- interação com skills que usam ASPD;
- interação com delays próprios de skills;
- verificação de que a ASPD **não** elimina a pós-conjuração;
- comportamento ao remover equipamentos e buffs;
- clamp correto em 197;
- tentativa de exceder 197.

### Relação entre AGI 185 e ASPD 197

```text
AGI natural 185 não garante, isoladamente, ASPD 197.
ASPD depende das fórmulas Pre-Renewal, classe, arma, escudo, buffs,
equipamentos e demais modificadores.
O balanceamento deverá impedir que ASPD 197 seja trivial para todas as classes
ou impossível para classes que deveriam alcançá-la.
```

Não estão fixados nesta tarefa quais classes devem alcançar ASPD 197 nem
quais equipamentos serão necessários; isso será validado na issue #8 ou em
issue própria de balanceamento.

A issue #8 deverá incluir: tabela de EXP customizada até 255, curva de
progressão, limite natural individual de atributos (185), pontos totais de
status, curva de concessão de pontos, custo de atributos, HP/SP, validação da
ASPD máxima 197 por classe e tipo de arma, testes por faixa de level,
benchmarks de classes e plano de rollback. Nenhum desses itens é configurado
nesta tarefa.

## Rates

As rates da issue #7 só devem ser fechadas **depois** da definição da
mecânica registrada aqui. Em Pre-Renewal:

- não devem ser consideradas ativas as fórmulas `RENEWAL_EXP`;
- não devem ser consideradas ativas as fórmulas `RENEWAL_DROP`;
- rates brutas ainda precisam ser equilibradas;
- drop de cartas e MVP deve ser tratado separadamente;
- base level 255 altera o tempo total de progressão, afetando o cálculo de
  rates.

```text
A progressão high rate deverá ser calculada para base level 255, e não para o
antigo base level máximo 185 (decisão histórica revogada).
```

A issue #7 deverá avaliar o tempo de progressão nas faixas:

- 1–99;
- 100–150;
- 151–200;
- 201–230;
- 231–255.

Considerando: rebirth, transclasse, jogo solo, grupos, bônus de EXP, eventos,
equipamentos de EXP e o tempo para atingir atributos naturais altos (próximos
do limite individual de 185).

Estado dos itens de progressão:

| Item                    | Estado                     |
| ----------------------- | -------------------------- |
| Base level máximo       | 255 — pendente da issue #8 |
| Atributo natural máximo | 185 — pendente da issue #8 |
| ASPD máxima             | 197 — pendente da issue #8 |
| Job level máximo        | a definir por classe       |
| Base EXP                | proposta pendente          |
| Job EXP                 | proposta pendente          |

Registros adicionais:

- o atributo natural máximo 185 altera o custo e a quantidade total de pontos
  de status necessários;
- a ASPD máxima 197 afeta o balanceamento de equipamentos, buffs e classes;
- nenhuma rate está automaticamente aprovada.

Os valores abaixo permanecem **propostas pendentes**, não decisão final, até
o fechamento da issue #7 — nenhuma rate (incluindo `100x`) está aprovada:

| Item | Valor inicial sugerido | Observação |
|---|---:|---|
| Base EXP | 100x | ajustar após teste |
| Job EXP | 100x | ajustar após teste |
| Drop comum | 50x | cuidado com inflação |
| Drop card normal | 10x | evitar saturação |
| Drop MVP card | 1x a 3x | recomendado manter baixo |
| Base level máximo | 255 | custom (issue #8); ainda não implantado |
| Atributo natural máximo individual | 185 | custom (issue #8); ainda não implantado |
| ASPD máxima | 197 | custom (issue #8); ainda não implantada |
| Job máximo | a definir | depende das classes permitidas (issues #8 e #9) |
| Instant cast | a definir | impacto alto em PvP/MVP |

## NPCs iniciais

- Warper limitado.
- Healer.
- Job changer até transclasse.
- Resetador com custo.
- Loja utilitária básica.
- NPC de informações do servidor.
- NPC de regras.

## Decisões pendentes

- WoE terá ou não?
- PvP será aberto?
- Haverá autoloot?
- Haverá comandos `@go`, `@storage`, `@warp`?
- Haverá cash shop? Recomendação: não ter pay-to-win.
- Episódio histórico numerado (ver [Conteúdo e episódio](#conteúdo-e-episódio)).
- Expanded classes (ver [Classes](#classes)).

## Dependências

| Issue | Escopo | Relação com esta decisão |
| --- | --- | --- |
| #7 — Definir rates iniciais | Rates de EXP e drop | Só deve ser fechada após esta decisão de mecânica; fórmulas `RENEWAL_EXP`/`RENEWAL_DROP` não se aplicam em Pre-Renewal |
| #8 — Definir base level 255, atributos 185 e ASPD 197 | Curva de EXP até 255, pontos de status, atributos naturais até 185, ASPD máxima 197, HP/SP, testes por faixa | Deve tratar base level 255, atributos naturais 185 e ASPD 197 como customização de impacto extremo sobre fórmulas Pre-Renewal |
| #9 — Bloquear 3ª classes | Job changer, NPCs, comandos, scripts, GM | Deve validar que o bloqueio é efetivo; Pre-Renewal não garante isso sozinho |

## Testes

Este documento é documental; "testes" aqui significam verificações de
consistência textual e de rastreabilidade, não execução em ambiente real:

- Pre-Renewal não foi confundido com episódio histórico.
- Pre-Renewal não foi confundido com cliente ou `PACKETVER`.
- Pre-Renewal não foi confundido com `PACKETVER_RE`.
- O cliente de 2021 não foi tratado como obrigação de Renewal.
- 3ª classes continuam registradas como política independente, pendente de
  validação pela issue #9.
- Base level 255, atributo natural máximo individual 185 e ASPD máxima 197
  estão marcados como customização de impacto extremo, pendente da issue #8;
  o antigo base level máximo 185 está registrado apenas como histórico
  substituído, e o atributo máximo 187 como decisão corrigida para 185.
- Base level, job level, limite natural individual de atributo, pontos totais
  de status, ASPD, AGI, velocidade de movimento e delays de skills estão
  diferenciados (ver [Terminologia](#terminologia)).
- AGI 185 e ASPD 197 estão registradas como grandezas distintas (ver
  [Relação entre AGI 185 e ASPD 197](#relação-entre-agi-185-e-aspd-197)).
- Rates permanecem pendentes da issue #7.
- Expanded classes permanecem pendentes.
- Nenhum conteúdo foi marcado como disponível sem auditoria.
- Estado atual do build e estado-alvo do projeto estão separados (ver seção
  seguinte).
- Fontes usam o commit fixado `7f080871c`.

## Estado atual versus estado-alvo

| Item               | Estado atual               | Estado-alvo         | Ação futura                                  |
| ------------------- | --------------------------- | --------------------- | ---------------------------------------------- |
| Mecânica compilada  | Pre-Renewal confirmado na configuração registrada do build (`-DPRERE` em `config.log`); proveniência dos binários atuais não atestada nesta auditoria | Pre-Renewal          | nenhuma ação de recompilação motivada por esta tarefa; testes funcionais permanecem necessários |
| Base level          | não validado nesta tarefa    | 255                    | issue #8                                        |
| Atributo máximo     | não validado nesta tarefa    | 185 natural            | issue #8                                        |
| ASPD máxima         | não validada nesta tarefa    | 197                    | issue #8                                        |
| Job level           | não definido                 | definir por classe     | issues #8 e #9                                  |
| 3ª classes          | bloqueio não validado integralmente | bloqueadas      | issue #9                                        |
| Rates               | não validadas                | high rate até 255      | issue #7                                        |
| Conteúdo            | não auditado nesta tarefa    | curado                 | tarefa futura de curadoria de conteúdo          |

A configuração registrada em `config.log` está alinhada com a decisão
Pre-Renewal. Não foi identificada nesta tarefa razão documental para
recompilar. A proveniência exata dos binários atuais e o comportamento
funcional deverão ser confirmados em testes futuros, sem que isso impeça a
aprovação da referência mecânica. Nenhuma recompilação e nenhum reinício de
serviço foram executados em decorrência desta tarefa.

## Riscos

- Escolher Renewal apenas por causa do cliente de 2021 (mitigado: decisão
  documentada como independente do protocolo).
- Tratar Pre-Renewal como bloqueio automático de 3ª classes (mitigado:
  seção [Classes](#classes) explícita).
- Fixar episódio sem auditar conteúdo (mitigado: seção
  [Conteúdo e episódio](#conteúdo-e-episódio) deixa o episódio em aberto).
- Subestimar o impacto do base level 255, dos atributos naturais até 185 e da
  ASPD máxima 197 sobre fórmulas Pre-Renewal (mitigado: seção
  [Base level 255, atributos máximos 185 e ASPD 197](#base-level-255-atributos-máximos-185-e-aspd-197)
  lista riscos e remete à issue #8).
- Confundir o limite natural individual de atributo (185) com pontos totais
  de status, ou base level 255 com job level (mitigado: seção
  [Terminologia](#terminologia)).
- Confundir o antigo base level máximo 185 (histórico revogado) com o
  atributo natural máximo vigente 185 (mitigado: registro explícito dos dois
  significados na seção
  [Base level 255, atributos máximos 185 e ASPD 197](#base-level-255-atributos-máximos-185-e-aspd-197)).
- Confundir AGI 185 com ASPD 197, tratar ASPD como velocidade de movimento ou
  como redução de delay/pós-conjuração de skills (mitigado: seções
  [Terminologia](#terminologia) e
  [Relação entre AGI 185 e ASPD 197](#relação-entre-agi-185-e-aspd-197)).
- Presumir que todas as classes devem alcançar ASPD 197, ou declarar os
  limites 255/185/197 como já implantados (mitigado: seções de riscos e
  [Estado atual versus estado-alvo](#estado-atual-versus-estado-alvo)).
- Subestimar a carga do map-server com ASPD alta (mitigado: item de validação
  na issue #8).
- Aplicar rates antes da definição mecânica (mitigado: seção
  [Rates](#rates) mantém valores como propostas pendentes).
- Confundir `PACKETVER_RE` com modo Renewal (ver
  [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md), seção
  3).
- Documentar o estado-alvo como se já estivesse implantado — mitigado pela
  separação explícita em
  [Estado atual versus estado-alvo](#estado-atual-versus-estado-alvo).
- Alterar o servidor durante uma tarefa documental — não ocorreu; auditoria
  foi read-only.

## Rollback

Esta tarefa é documental e read-only:

1. reverter o commit desta branch, caso o conteúdo precise ser removido ou
   corrigido;
2. não alterar `dev` diretamente — reverter apenas na branch de tarefa antes
   do merge, ou por um novo commit de reversão após o merge;
3. nenhum rollback operacional é necessário, pois nenhuma mudança operacional
   ocorreu (nenhum serviço reiniciado, nenhum binário recompilado, nenhuma
   configuração de VPS alterada);
4. se o PR for incorporado e a decisão mudar no futuro, criar um novo
   ADR/PR (ver [templates/ADR.md](templates/ADR.md)) documentando a
   substituição da decisão, em vez de editar silenciosamente esta decisão já
   incorporada.

## Referências

- [src/config/renewal.hpp @ 7f080871c](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/config/renewal.hpp) — fonte oficial fixada da macro `PRERE` e das macros Renewal dependentes.
- [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md) — protocolo, `PACKETVER_RE`, distinção protocolo × mecânica.
- [10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md) — política de fontes e tabela classificada por confiança.
- [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md) — auditoria read-only anterior do commit instalado e dos serviços.
- [00-base-conhecimento.md](00-base-conhecimento.md) — definição de old school e ponto de atenção sobre base level 255, atributos máximos 185 e ASPD máxima 197.
- Auditoria read-only desta tarefa: `config.log`, `git status`/`git rev-parse` em `/opt/faithro/rathena`, acesso em 2026-07-10.
