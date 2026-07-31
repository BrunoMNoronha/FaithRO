# Decisão do caminho do núcleo do WARP

> **Status:** PACOTE DE DECISÃO HUMANA PREPARADO / NENHUMA OPÇÃO SELECIONADA (ETAPA 2P-E-A).
> **Data:** 2026-07-31.
> **Classificação da investigação:** **PREBUILT COM PROVENIÊNCIA PARCIAL**
> (fonte não localizada; prebuilt de origem oficial, sem hash/assinatura/receita/
> reprodutibilidade — custody FRACA). Esta classificação **não** é uma decisão
> humana.
> **Escopo:** investigação documental e preparação de um pacote de decisão humana.
> **Nada** foi materializado, compilado ou executado; nenhuma opção foi
> selecionada; nenhuma autorização operacional foi concedida.
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

| Verificação | Resultado |
| --- | --- |
| Fonte C++/Qt do núcleo em **alguma** branch | **Não** (`src/build = 0` em todas as 10 branches) |
| Receita de build (`.pro/.pri/CMake/.sln/Makefile`) | **Não** (nenhuma branch) |
| Tags / Releases | **0 / 0** |
| Wiki documenta build a partir do fonte | **Não** |
| Repositório de fonte separado do mantenedor | **Não** (`sfui` em C++ é lib de 2015 do Google Code, `NOASSERTION`, não relacionada) |
| Issues sobre "build from source" | **0** |

**Correspondência fonte-binário: `FONTE NÃO LOCALIZADA`.** O código-fonte C++/Qt
do núcleo do WARP não é publicado oficialmente (repositório descrito como "Win App
Revamp Package", linguagem GitHub = JavaScript).

## 6. Proveniência do prebuilt

Por **metadados oficiais** (sem materializar o binário):

| Item | Resultado |
| --- | --- |
| PREBUILT TEM ORIGEM OFICIAL | **SIM** (commit direto do mantenedor no repo oficial) |
| COMMIT DE INTRODUÇÃO IDENTIFICADO | **SIM** (`b5f4b6a1f8d3`, 2020-11-26, "Added the Binaries & DLL") |
| Commits que tocam `win32/WARP.exe` | 21 (todos por Neo / Neo Mind; sem CI/automação) |
| `win32/WARP.exe` (blob / tamanho) | `c853da42d18dfe090b4e941b435d989311faf3dc` / 1.137.152 bytes |
| FONTE CORRESPONDENTE IDENTIFICADA | **NÃO** |
| RECEITA DE BUILD CORRESPONDENTE | **NÃO** |
| HASH OFICIAL PUBLICADO | **NÃO** (sem releases/tags) |
| ASSINATURA DOCUMENTADA | **NÃO** (Authenticode eventual no PE não materializada nem verificada) |
| REPRODUTIBILIDADE DEMONSTRADA | **NÃO** |
| CADEIA DE CUSTÓDIA | **FRACA** |

Não se conclui que o prebuilt é seguro nem malicioso.

## 7. Lacunas

- Ausência de fonte do núcleo e de receita de build.
- Ausência de hash oficial publicado e de assinatura documentada.
- Ausência de reprodutibilidade.
- Única âncora de proveniência: autoria dos commits no repositório oficial.

## 8. Alternativas

- **Fonte oficial (SOURCE_PATH):** `NÃO DISPONÍVEL`.
- **Prebuilt oficial (PREBUILT_PATH):** `ADEQUADO COM RESTRIÇÕES` — só sob
  auditoria binária offline futura e autorização humana específica.
- **Outra ferramenta (ALTERNATIVE_TOOL):** `INCONCLUSIVO` — NEMO atual (4144)
  permanece **rejeitado** (licença ausente + binários versionados, [28](28-decisao-ferramenta-preparacao-cliente.md));
  nenhuma outra ferramenta com fonte completa + receita foi localizada nesta etapa.
- **Interromper (STOP_PATH):** `ADEQUADO` — manter o servidor em homologação de
  infraestrutura e aguardar cadeia de confiança melhor.

## 9. Matriz de decisão

| Alternativa | Fonte completa | Build reproduzível | Licença | Proveniência | Risco supply chain | Risco de PI | Esforço | Permite avançar? |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| Fonte oficial do WARP localizada | Não | Não | GPL-3.0 | — | — | — | — | **Não** (`NÃO DISPONÍVEL`) |
| Prebuilt oficial do WARP | Não | Não | GPL-3.0 | Parcial (oficial, custody FRACA) | Alto | Baixo (uso local) | Alto (auditoria binária) | **Com restrições** |
| Outra ferramenta aberta | ? | ? | ? | ? | ? | ? | Alto | **Inconclusivo** |
| Cliente-base alternativo legal | — | — | — | — | Médio | Alto (proprietário) | Alto | **Inconclusivo** |
| Interromper o fluxo | — | — | — | — | Nenhum | Nenhum | Nenhum | **Sim** |

Estados: `ADEQUADO`, `ADEQUADO COM RESTRIÇÕES`, `INCONCLUSIVO`, `INADEQUADO`,
`NÃO DISPONÍVEL`.

## 10. Recomendação técnica

**`SUBMETER CAMINHO DO PREBUILT À DECISÃO HUMANA EXCEPCIONAL`** — como **opção**,
nunca como autorização. Justificativa: `SOURCE_PATH` está indisponível; nenhuma
ferramenta alternativa superior foi localizada; restam `PREBUILT_PATH` (apenas sob
auditoria binária offline futura + autorização específica) e `STOP_PATH`. Dada a
**custody FRACA**, **rejeitar** ou **interromper** permanecem opções igualmente
válidas para o decisor humano. **Nenhuma opção é selecionada aqui.**

## 11. Decisão humana necessária

O decisor deve, no registro
[`core-path-decision-record.example.json`](../client/warp-audit/core-path-decision-record.example.json),
selecionar **uma** opção e definir condições. Enquanto `status = PENDING`, o fluxo
permanece bloqueado. O registro **não** concede autorização a si mesmo.

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
  PROVENIÊNCIA PARCIAL; recomendação técnica = submeter o prebuilt à decisão humana
  excepcional (não é autorização).
- **Pendência:** decisão humana do caminho do núcleo; auditoria binária offline se
  o prebuilt for escolhido.
- **Nota:** decisão técnica e de conformidade do projeto, **não** parecer jurídico.
