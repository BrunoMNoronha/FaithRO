# Decisão do caminho do núcleo do WARP

> **Status:** PACOTE DE DECISÃO HUMANA PREPARADO / NENHUMA OPÇÃO SELECIONADA (ETAPA 2P-E-A).
> **Data:** 2026-07-31.
> **Classificação da investigação:** **PREBUILT COM PROVENIÊNCIA PARCIAL** —
> retrato pontual de 2026-07-31 (fonte não localizada **no escopo pesquisado**;
> blob do prebuilt presente no repositório oficial, mas sem hash publicado,
> assinatura verificada, receita ou reprodutibilidade — custody FRACA por
> critérios objetivos, ver [§6](#6-proveniência-do-prebuilt)). Esta classificação
> **não** é uma decisão humana e **não** valida o binário.
> **Escopo:** investigação documental e preparação de um pacote de decisão humana.
> **Nada** foi materializado, baixado, compilado ou executado; **nenhuma** opção
> foi selecionada; o registro de decisão permanece **em branco**; **nenhuma**
> autorização operacional foi concedida; o merge do PR **não** constitui decisão
> humana.
> Continua [30](30-auditoria-estatica-warp.md); observa
> [16](16-politica-distribuicao-cliente.md) e [28](28-decisao-ferramenta-preparacao-cliente.md).

## 1. Objetivo

Preparar uma **decisão humana formal** sobre o caminho técnico do núcleo do WARP
após o achado **W1** (ETAPA 2P-D/D1), comparando — **sem selecionar
automaticamente** — quatro caminhos: (1) localizar fonte oficial completa +
receita de build; (2) considerar excepcionalmente o prebuilt sob auditoria
binária futura; (3) rejeitar o WARP e escolher outra ferramenta; (4) interromper a
preparação do cliente.

## 2. Contexto

- PR #43 (2P-D/D1) integrado em `dev` (squash `5789310a72fe0cfaa28307d06e983db6404a9fc6`).
- Build do núcleo **bloqueado**; uso do prebuilt **não autorizado**; patches
  sensíveis **bloqueados**; nenhum merge equivale a autorização operacional.
- PR #41 (fluxo do Beam) permanece aberto, draft e **fora** deste fluxo.

## 3. Achado W1 (recapitulação)

No commit fixado `9b1173e9e4e135c68e150704f01186ab5e763acd` (branch `rock_win32`),
a **camada textual** (scripts `.qjs/.mjs`, YAML, tabelas, docs) é auditável, mas o
**núcleo C++/Qt não está presente como fonte** e **não há receita de build**. O
núcleo é fornecido **apenas como binário prebuilt** em `win32/`.

## 4. Fontes pesquisadas

Somente fontes oficiais, via API/páginas oficiais, **sem baixar binários**:

- as **10 branches** do repositório oficial (`base`, `deb32`, `deb64`, `docs`,
  `gh-pages`, `rock`, `rock_deb32`, `rock_deb64`, `rock_win32`, `win32`);
- **tags** e **releases** do repositório;
- o submódulo **Wiki** (`WARP.wiki.git`);
- `README.md` e `CHANGELOG.md`;
- **issues**;
- os **repositórios do mantenedor** `Neo-Mind`.

## 5. Resultado da busca por fonte

Retrato pontual da consulta de **2026-07-31** (API oficial, com paginação); os
números são o resultado dessa consulta, não uma verdade permanente.

| Verificação | Resultado observado |
| --- | --- |
| Fonte C++/Qt do núcleo em **alguma** branch | Não localizada (`src/build = 0` nas 10 branches observadas) |
| Receita de build (`.pro/.pri/CMake/.sln/Makefile`) | Não localizada (nenhuma branch observada) |
| Tags / Releases | 0 / 0 (observados) |
| Wiki documenta build a partir do fonte | Não |
| Repositório de fonte separado do mantenedor | Não localizado (`sfui` em C++ é lib de 2015 do Google Code, `NOASSERTION`, sem relação demonstrada) |
| Issues sobre "build from source" | 0 (observadas) |

**Correspondência fonte-binário: `FONTE NÃO LOCALIZADA NO ESCOPO PESQUISADO`.** A
fonte C++/Qt do núcleo e uma receita de build correspondente **não foram
localizadas** no conjunto de branches, tags, releases, Wiki, issues, documentação e
repositórios oficiais pesquisados nesta etapa (repositório descrito como "Win App
Revamp Package", linguagem GitHub = JavaScript). **Ausência de evidência no escopo
pesquisado não é prova de inexistência.**

## 6. Proveniência do prebuilt

Por **metadados oficiais** (sem materializar o binário):

| Item | Resultado observado |
| --- | --- |
| Blob presente no repositório **oficial** | **SIM** — o blob está versionado no repo oficial; introdução/atualizações são rastreáveis no histórico Git. **Não** significa binário autenticado nem validado. |
| Commit de introdução (SHA completo) | `b5f4b6a1f8d326fd2e1d882c5ffaf107f2a6dea0` (abrev. `b5f4b6a1f8d3`), 2020-11-26, "Added the Binaries & DLL" |
| Commits que tocam `win32/WARP.exe` (observados) | 21 |
| Autoria (metadados Git) | atribuída à identidade **Neo / Neo Mind** do repo oficial; **não** comprova ambiente de build, identidade civil, integridade do binário nem custódia |
| `win32/WARP.exe` (blob / tamanho) | `c853da42d18dfe090b4e941b435d989311faf3dc` / 1.137.152 bytes |
| Fonte correspondente identificada | **NÃO** |
| Receita de build correspondente | **NÃO** |
| Hash oficial publicado | **NÃO** (sem releases/tags) |
| Assinatura verificada | **NÃO** (Authenticode eventual no PE não materializada nem verificada) |
| Reprodutibilidade demonstrada | **NÃO** |
| Binário materializado / comportamento analisado | **NÃO / NÃO** |

**Cadeia de custódia: `FRACA`** — derivada objetivamente destes critérios (não é
juízo subjetivo): blob no repo oficial *(positivo)*; histórico rastreável
*(positivo)*; fonte correspondente, receita de build, hash externo publicado,
assinatura verificada, release/tag, CI/build provenance e reprodutibilidade
*(todos ausentes)*. **Não se conclui que o prebuilt é seguro nem malicioso.**

## 7. Lacunas

- Ausência de fonte do núcleo e de receita de build.
- Ausência de hash oficial publicado e de assinatura documentada.
- Ausência de reprodutibilidade.
- Única âncora de proveniência: autoria dos commits no repositório oficial.

## 8. Alternativas

Cada opção é apenas **elegível para consideração humana** (`selected=false`).

- **Fonte oficial (SOURCE_PATH):** `NÃO DISPONÍVEL` — não elegível (fonte não
  localizada no escopo pesquisado).
- **Prebuilt oficial (PREBUILT_PATH):** `ELEGÍVEL PARA CONSIDERAÇÃO EXCEPCIONAL` —
  único caminho WARP tecnicamente identificado, porém **insuficiente** para
  execução sem **auditoria binária offline futura** e **decisão humana
  excepcional**; sem materialização/download/execução nesta etapa; **sujeito a
  rejeição**.
- **Outra ferramenta (ALTERNATIVE_TOOL):** `INCONCLUSIVO` — **nenhuma alternativa
  materialmente superior foi localizada nesta etapa**; NEMO atual (4144) permanece
  rejeitado pela política do projeto ([28](28-decisao-ferramenta-preparacao-cliente.md));
  uma pesquisa dedicada futura pode encontrar outro candidato; nenhuma foi aprovada.
- **Interromper (STOP_PATH):** `ADEQUADO` — **opção de primeira classe**, não é
  falha do projeto: preserva segurança e propriedade intelectual, mantém o servidor
  disponível para homologação de infraestrutura, é reversível se surgir ferramenta
  melhor e não exige rollback.

## 9. Matriz de decisão

| Alternativa | Fonte completa | Build reproduzível | Licença | Proveniência | Risco supply chain | Risco de PI | Esforço | Permite avançar? |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| Fonte oficial do WARP localizada | Não | Não | GPL-3.0 | — | — | — | — | **Não** (`NÃO DISPONÍVEL`) |
| Prebuilt oficial do WARP | Não | Não | GPL-3.0 | Parcial (blob oficial, custody FRACA) | Alto | Baixo (uso local) | Alto (auditoria binária) | **Elegível p/ consideração excepcional** |
| Outra ferramenta aberta | ? | ? | ? | ? | ? | ? | Alto | **Inconclusivo** |
| Cliente-base alternativo legal | — | — | — | — | Médio | Alto (proprietário) | Alto | **Inconclusivo** |
| Interromper o fluxo | — | — | — | — | Nenhum | Nenhum | Nenhum | **Adequado (1ª classe)** |

Estados: `ADEQUADO`, `ELEGÍVEL PARA CONSIDERAÇÃO EXCEPCIONAL`, `INCONCLUSIVO`,
`INADEQUADO`, `NÃO DISPONÍVEL`. "Elegível" significa que a opção **pode ser
discutida** pelo decisor, **não** que possa ser executada.

## 10. Recomendação técnica

**`SUBMETER PREBUILT_PATH E STOP_PATH AO DECISOR, SEM PREFERÊNCIA AUTOMÁTICA`.** O
caminho do prebuilt é tecnicamente o **único** caminho WARP identificado, mas
possui **cadeia de confiança insuficiente** para execução sem auditoria binária e
decisão humana excepcional. `SOURCE_PATH` está indisponível; `ALTERNATIVE_TOOL` é
inconclusivo. A recomendação desta etapa é **submeter conjuntamente**
`PREBUILT_PATH` e `STOP_PATH` ao decisor humano, **sem preferência operacional
automática** e sem induzir aprovação. **Nenhuma opção é selecionada aqui**, e esta
recomendação **não** é uma autorização.

## 11. Decisão humana necessária

O arquivo
[`core-path-decision-record.example.json`](../client/warp-audit/core-path-decision-record.example.json)
é **somente template** e deve permanecer **em branco** (`status = PENDING`, campos
`null`, flags `false`). A decisão real futura deve ser registrada em um **artefato
separado, fora do template**, com identidade, autoridade, canal e data vindos de
**entrada humana** — o agente **não** pode inventá-los. O merge deste PR **não**
preenche o registro nem seleciona opção; o registro **não** concede autorização a
si mesmo. Enquanto não houver decisão humana explícita, o fluxo permanece bloqueado.

## 12. Autorizações separadas (todas negadas nesta etapa)

Mesmo que o caminho do prebuilt seja futuramente escolhido, cada item exige
autorização própria: materializar o blob, calcular SHA-256, validar Authenticode,
inventariar PE, listar imports, extrair strings/recursos, análise estática
offline, antivírus locais, sandbox descartável sem cliente, bloqueio de rede,
monitoramento de processos/arquivos/registro, comparação antes/depois, descarte do
ambiente, fornecer cópia do `Ragexe` e produzir saída modificada. Ver
[`core-path-decision-package.example.json`](../client/warp-audit/core-path-decision-package.example.json)
(`future_binary_audit_requirements`, todos `authorized=false`).

## 13. Arquivos afetados

Criados/atualizados (apenas texto): `docs/31` (este documento),
`client/warp-audit/core-path-decision-package.example.json`,
`client/warp-audit/core-path-decision-record.example.json`, schemas
correspondentes, `scripts/validate-warp-audit.py` (estendido), e atualizações em
`docs/README.md`, `client/warp-audit/README.md`, `client/README.md`. Não alterados:
`client/patcher/`, documentos do Beam, PR #41.

Os SHA-256 das referências no pacote usam a estratégia canônica **SHA-256 do
conteúdo do blob Git (normalizado a LF)**, reproduzível por
`git show <rev>:<caminho> | sha256sum` — **não** o working tree (que pode ter CRLF
no Windows).

## 14. Passos futuros

Somente após decisão humana explícita e revisada: se **fonte** (indisponível hoje),
2P-E-B-FONTE; se **prebuilt**, 2P-E-B-PREBUILT (auditoria binária offline); se
**outra ferramenta**, nova auditoria dedicada; se **interrupção**, encerrar a
preparação do cliente.

## 15. Testes futuros

Auditoria binária offline do prebuilt (se autorizada), reconhecimento real do
`Ragexe` (se autorizado) e teste de login controlado (se autorizado) — todos em
etapas separadas.

## 16. Riscos

- **Cadeia de suprimentos:** usar binário de terceiros sem fonte nem integridade
  publicada — mitigável apenas por auditoria binária offline rigorosa.
- **PI:** WARP é GPL (uso local); `Ragexe`/assets Gravity proprietários, nunca
  redistribuídos.
- **Decisão precipitada:** mitigada por manter tudo bloqueado até decisão humana.

## 17. Rollback

Documental: reverter o commit desta branch. Nada foi materializado, compilado ou
executado. Nenhuma reversão de VPS, MariaDB, firewall ou cliente é necessária.

## 18. Propriedade intelectual

Registrados apenas metadados (caminho relativo upstream, tamanho, blob SHA). Nenhum
binário, DLL, `.asi`, `Ragexe`, GRF, dump ou assinatura de bytes proprietários foi
versionado, publicado ou compartilhado.

## 19. Limitações

- A conclusão "fonte não localizada" abrange as fontes oficiais pesquisadas nesta
  etapa; não prova impossibilidade absoluta de existir fonte privada.
- A proveniência do prebuilt baseia-se em metadados do repositório oficial; a
  integridade do binário só poderá ser avaliada em auditoria binária futura
  autorizada.

## 20. Próxima etapa permitida

Somente após **decisão humana explícita e revisada** registrada em
`core-path-decision-record`: a etapa correspondente ao caminho escolhido
(2P-E-B-FONTE / 2P-E-B-PREBUILT / nova auditoria de ferramenta / encerramento).
**Nenhuma** é iniciada automaticamente.

## Estado de verificação

- **Fato:** ausência de fonte/receita em todas as branches; 0 tags/releases; Wiki
  sem build-from-source; proveniência do prebuilt (commit introdutor, autoria,
  blob/tamanho) por metadados.
- **Inferência/decisão:** classificação da investigação = PREBUILT COM
  PROVENIÊNCIA PARCIAL (retrato pontual); recomendação técnica = submeter
  `PREBUILT_PATH` **e** `STOP_PATH` ao decisor **sem preferência automática** (não é
  autorização); nenhuma opção selecionada.
- **Pendência:** decisão humana do caminho do núcleo; auditoria binária offline se
  o prebuilt for escolhido.
- **Nota:** decisão técnica e de conformidade do projeto, **não** parecer jurídico.
