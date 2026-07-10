# Configuração alvo de gameplay

> **Escopo:** documento de decisão técnica e documentação. Nenhuma alteração de
> código, banco de dados, rates, tabela de EXP, level máximo, NPCs, classes,
> configuração da VPS ou firewall é executada por este documento. Nenhum
> serviço foi reiniciado e nenhum binário foi recompilado para produzir este
> texto.

## Objetivo

Definir formalmente a **referência mecânica** (Pre-Renewal ou Renewal) que
servirá de base para as próximas configurações do FaithRO - Laos Deos,
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

- Nome: FaithRO - Laos Deos
- Estilo: old school/high rate
- 3ª classes: desabilitadas (política de conteúdo, ver seção
  [Classes](#classes))
- Level máximo: 185 (customização, ver seção [Level 185](#level-185))
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

| Conceito           | Decisão                 |
| ------------------ | ------------------------ |
| Protocolo          | `PACKETVER=20211103`    |
| Cliente            | `2021-11-03_Ragexe`     |
| Mecânica           | Pre-Renewal             |
| Conteúdo           | curado                  |
| Episódio histórico | ainda não fixado        |
| Classes            | até transclasses        |
| 3ª classes         | bloqueadas por política |
| Level máximo       | 185 custom              |
| Rates              | pendentes                |

Nenhuma linha desta tabela decorre automaticamente de outra. Em particular:

- `PACKETVER=20211103` **não** obriga o servidor a operar em Renewal (o mesmo
  `PACKETVER` é compilado pela CI oficial em ambos os modos, `PRE` e `RE` —
  ver [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md));
- Pre-Renewal **não** bloqueia sozinho as 3ª classes — isso é política de
  conteúdo tratada na issue #9 (ver [Classes](#classes));
- Pre-Renewal **não** define sozinho o level máximo 185 — isso é
  customização tratada na issue #8 (ver [Level 185](#level-185));
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
| Compatibilidade conceitual com level 185  | custom e de alto risco         | nativa para níveis maiores, mas foge da proposta   |
| Bloqueio de 3ª classes                    | ainda precisa ser configurado  | ainda precisa ser configurado                      |
| Conteúdo disponível                       | precisa ser curado             | precisa ser curado                                 |
| Complexidade de balanceamento             | alta por causa do level 185    | alta por remoção das 3ª classes                    |

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
no commit `7f080871c`, quando `PRERE` está definido, o bloco `#ifndef PRERE`
que define `RENEWAL`, `RENEWAL_CAST`, `RENEWAL_DROP`, `RENEWAL_EXP`,
`RENEWAL_LVDMG`, `RENEWAL_ASPD` e `RENEWAL_STAT` **não é executado** — nenhuma
dessas macros Renewal é definida para esta compilação.

**Classificação final:** `Pre-Renewal confirmado no build`.

Esta classificação é a mais forte das quatro categorias possíveis
(`Pre-Renewal confirmado no build` · `Renewal confirmado no build` ·
`Fonte padrão Renewal, mas build efetivo inconclusivo` ·
`Pendente de validação`), porque a evidência não vem apenas da leitura de
`renewal.hpp` (que descreve o padrão quando `PRERE` **não** está definido),
mas da flag de compilação efetivamente registrada em `config.log` e
propagada para `CPPFLAGS`.

**Limitações:** esta auditoria não reexecutou os binários nem inspecionou
símbolos/strings do executável compilado para reconfirmar a macro em tempo de
execução; a evidência se apoia no log de configuração (`config.log`) do
próprio processo de build, que é a fonte mais forte disponível sem recompilar
nada. Não recompile para "confirmar ainda mais" — isso seria uma mudança
operacional fora do escopo desta tarefa.

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

## Level 185

Level 185 é tratado como **customização de alto impacto**, independente da
mecânica-base escolhida. Riscos documentados, a serem endereçados na issue
#8:

- fórmulas Pre-Renewal não foram originalmente balanceadas para essa
  progressão;
- excesso de pontos de atributo;
- crescimento de HP/SP;
- precisão e esquiva;
- ASPD;
- dano físico e mágico;
- cast instantâneo;
- defesa;
- resistência a status;
- balanceamento PvP;
- balanceamento WoE;
- trivialização de MVPs;
- progressão de EXP;
- diferença entre classes;
- equipamentos pensados para faixas de level menores.

A issue #8 deverá incluir: tabela de EXP customizada, curva de progressão,
limite de atributos, pontos de status, HP/SP, testes por faixa de level,
benchmarks de classes e plano de rollback. Nenhum desses itens é configurado
nesta tarefa.

## Rates

As rates da issue #7 só devem ser fechadas **depois** da definição da
mecânica registrada aqui. Em Pre-Renewal:

- não devem ser consideradas ativas as fórmulas `RENEWAL_EXP`;
- não devem ser consideradas ativas as fórmulas `RENEWAL_DROP`;
- rates brutas ainda precisam ser equilibradas;
- drop de cartas e MVP deve ser tratado separadamente;
- level 185 altera o tempo total de progressão, afetando o cálculo de rates.

Os valores abaixo permanecem **propostas pendentes**, não decisão final, até
o fechamento da issue #7:

| Item | Valor inicial sugerido | Observação |
|---|---:|---|
| Base EXP | 100x | ajustar após teste |
| Job EXP | 100x | ajustar após teste |
| Drop comum | 50x | cuidado com inflação |
| Drop card normal | 10x | evitar saturação |
| Drop MVP card | 1x a 3x | recomendado manter baixo |
| Level máximo | 185 | custom (issue #8) |
| Job máximo | a definir | depende das classes permitidas (issue #9) |
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
| #8 — Definir level máximo 185 | Curva de EXP, atributos, HP/SP, testes por faixa | Deve tratar level 185 como customização de alto risco sobre fórmulas Pre-Renewal |
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
- Level 185 está marcado como customização de alto risco, pendente da issue
  #8.
- Rates permanecem pendentes da issue #7.
- Expanded classes permanecem pendentes.
- Nenhum conteúdo foi marcado como disponível sem auditoria.
- Estado atual do build e estado-alvo do projeto estão separados (ver seção
  seguinte).
- Fontes usam o commit fixado `7f080871c`.

## Estado atual versus estado-alvo

| Item               | Estado atual               | Estado-alvo         | Ação futura                                  |
| ------------------- | --------------------------- | --------------------- | ---------------------------------------------- |
| Mecânica compilada  | Pre-Renewal confirmado no build (`-DPRERE` em `config.log`) | Pre-Renewal          | nenhuma — já alinhado, sem necessidade de recompilar |
| 3ª classes          | não validado integralmente  | bloqueadas             | issue #9                                        |
| Level máximo        | não validado                 | 185                    | issue #8                                        |
| Rates               | não validadas                | high rate a definir    | issue #7                                        |
| Conteúdo            | banco atual do rAthena       | curado                 | tarefa futura de curadoria de conteúdo          |

Como o build atual já é Pre-Renewal, esta seção documenta o alinhamento —
**nenhuma recompilação e nenhum reinício de serviço são necessários ou foram
executados** em decorrência desta tarefa.

## Riscos

- Escolher Renewal apenas por causa do cliente de 2021 (mitigado: decisão
  documentada como independente do protocolo).
- Tratar Pre-Renewal como bloqueio automático de 3ª classes (mitigado:
  seção [Classes](#classes) explícita).
- Fixar episódio sem auditar conteúdo (mitigado: seção
  [Conteúdo e episódio](#conteúdo-e-episódio) deixa o episódio em aberto).
- Subestimar o impacto do level 185 sobre fórmulas Pre-Renewal (mitigado:
  seção [Level 185](#level-185) lista riscos e remete à issue #8).
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
- [00-base-conhecimento.md](00-base-conhecimento.md) — definição de old school e ponto de atenção sobre level 185.
- Auditoria read-only desta tarefa: `config.log`, `git status`/`git rev-parse` em `/opt/faithro/rathena`, acesso em 2026-07-10.
