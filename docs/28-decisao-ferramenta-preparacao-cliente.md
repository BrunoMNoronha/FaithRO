# Decisão da ferramenta de preparação do executável do cliente

> **Status:** DECISÃO PREPARADA / NÃO EXECUTADA (ETAPA 2P-C).
> **Data:** 2026-07-27.
> **Escopo:** documento de decisão técnica. **Nenhuma** ferramenta foi baixada,
> compilada, executada ou aplicada. **Nenhum** cliente foi modificado. **Nenhum**
> executável preparado foi produzido. **Nenhum** binário de release foi obtido.
> Apenas metadados e código-fonte de repositórios oficiais foram inspecionados de
> forma estática. Esta decisão **não** autoriza execução.
> Complementa [17-decisao-patcher-launcher.md](17-decisao-patcher-launcher.md)
> (patchers de **GRF**, que não tocam o executável),
> [16-politica-distribuicao-cliente.md](16-politica-distribuicao-cliente.md) e
> [29-compatibilidade-cliente-2021-11-05-packetver.md](29-compatibilidade-cliente-2021-11-05-packetver.md).

## 1. Objetivo

Selecionar, por evidência de fontes oficiais, a ferramenta adequada para
**preparar (hex/diff) — exclusivamente em laboratório local** — o executável
`Ragexe` legalmente possuído pelo responsável, habilitando conexão a um servidor
configurado pelo operador (leitura de pasta `data`, `clientinfo` de FaithRO,
`langtype`, e — se comprovadamente necessário — tratamento de proteção/encriptação),
**sem** redistribuir qualquer conteúdo proprietário da Gravity.

Esta lacuna é real: [17](17-decisao-patcher-launcher.md) decidiu apenas o patcher
de **GRF** (Beam/RPatchur), que por design **nunca** modifica o `Ragexe`. Não
havia ferramenta aprovada para preparar o executável.

## 2. Contexto

- Cliente-alvo: `Ragexe` com build (PE link) **2021-11-05**, SHA-256
  `8990A9A9CD6623E173BCC8B406A311AF32773EB881E539082126B768C14E95A0`, x86,
  assinatura Gravity válida, com `GameGuard.des`/`v3hunt.dll` presentes no
  diretório (presença ≠ execução comprovada), **sem** `data\clientinfo.xml` de
  FaithRO (aponta para servidores oficiais).
- Compatibilidade de protocolo com o servidor (`PACKETVER=20211103`): **PROVÁVEL**
  (ver [29](29-compatibilidade-cliente-2021-11-05-packetver.md)); **não** requer
  mudança de servidor.
- O Beam Patcher ([17](17-decisao-patcher-launcher.md), [23](23-planejamento-primeiro-build-controlado-beam.md))
  atualiza **GRF**, não o `Ragexe`; **não** é a ferramenta desta decisão.

## 3. Candidatos

| # | Alternativa | Origem oficial | Tipo | Licença | Estado |
| - | --- | --- | --- | --- | --- |
| 1 | **WARP** | `github.com/Neo-Mind/WARP` | Open source (C++/Qt + scripts JS ECMA-262) | **GPL-3.0** (arquivo `LICENSE`) | **Ativo** (commit 2026-05-07) |
| 2 | **NEMO (atual, 4144)** | `gitlab.com/4144/Nemo` | Open source (Qt Script) + binários versionados | **Não declarada** (sem `LICENSE`) | **Ativo** (atividade 2026-06-13) |
| 3 | NEMO (histórico) | `github.com/Neo-Mind/NEMO` | Qt Script | Não declarada | **Arquivado** (aponta para o item 2) |
| 4 | Edição hex manual | — | Manual | — | — |
| 5 | "Cliente alternativo legal" | — | — | — | apenas avaliação conceitual |

> Datas/metadados consultados em **2026-07-27** via GitHub API e GitLab API
> oficiais. Nenhum binário foi baixado.

## 4. Fontes

Hierarquia conforme [10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md):
repositório oficial → arquivos de licença → estrutura do código → documentação do
autor.

- **WARP:** repositório oficial `Neo-Mind/WARP` (branch `rock_win32`, HEAD
  `9b1173e9e4e135c68e150704f01186ab5e763acd` — abreviação `9b1173e9e4e1` —,
  2026-05-07). `LICENSE` = GNU GPL v3. Submódulos: apenas o **Wiki**
  (documentação), sem submódulo de código.
- **NEMO atual:** o `README` do repositório histórico `Neo-Mind/NEMO` declara
  literalmente que o repositório está obsoleto e aponta para
  `gitlab.com/4144/Nemo` como a versão atual (mantenedor **4144**). Projeto
  público, ativo (atividade 2026-06-13), `default_branch` `master`.

## 5. Licença

> Esta seção é uma decisão **técnica e de conformidade do projeto**, não um
> parecer jurídico. As afirmações abaixo são de **política e risco**; qualquer
> obrigação de licença deve ser reavaliada antes de qualquer execução.

- **WARP:** identificada como **GPL-3.0** (arquivo `LICENSE` = GNU GPL v3). Como
  **política do FaithRO**, o projeto **não** distribuirá o WARP (original ou
  modificado), o `Ragexe` (original ou preparado), nem qualquer asset
  proprietário; qualquer eventual obrigação da GPL para uso local seria
  reavaliada antes da execução.
- **NEMO atual:** **sem licença declarada** (nenhum `LICENSE`/`COPYING` na raiz;
  SPDX nulo na API do GitLab). A **ausência de concessão explícita de direitos**
  impede o projeto de considerar o NEMO adequado para adoção ou redistribuição —
  bloqueio de **conformidade**, análogo ao tratamento do Thor em
  [17 §6](17-decisao-patcher-launcher.md).
- O `Ragexe` (original ou preparado) e os assets da Gravity são **proprietários**;
  como política, **nunca** serão redistribuídos, versionados ou compartilhados
  ([16](16-politica-distribuicao-cliente.md)).

## 6. Análise de segurança (inspeção estática — sem executar)

### 6.1 WARP

| Item | Resultado | Evidência |
| --- | --- | --- |
| Núcleo | C++/Qt, app Windows 32-bit; patches em JS (ECMA-262) | README |
| Submódulos | apenas `Wiki` (docs), sem código externo | `.gitmodules` |
| Rede / auto-update / telemetria | **Não foram encontrados** no conjunto inspecionado (únicos `http` são URLs da licença GPL) | `Scripts/Init/*`, `Scripts/Support/*` |
| Execução de shell / ActiveX / WScript | **Não foram encontrados** no conjunto inspecionado | idem |
| Reconhecimento do executável | por tabelas (`Tables/Input.yml`, `NemoMap.yml`, `Patch.yml`) | estrutura |
| Separação entrada/saída | `Inputs/` e `Outputs/` distintos; `LastSession.yml` | README |
| Catálogo de patches | `Patches.yml` + 159 scripts em `Scripts/Patches/` | estrutura |
| Operação offline (aparente) | patch é local, sobre o executável | design |

> **Escopo da conclusão de segurança.** Não foram encontrados mecanismos de rede,
> auto-update, telemetria ou execução de shell no **conjunto de arquivos e
> scripts efetivamente inspecionado nesta etapa**. A conclusão **não** abrange
> componentes, dependências, binários pré-compilados ou scripts ainda não
> auditados.
>
> - **Inspecionado nesta etapa:** `README.md`, `LICENSE`, `.gitmodules`,
>   `Patches.yml`/`Extensions.yml` (catálogo), listagem de `Scripts/Patches`,
>   `Scripts/Init/*` e `Scripts/Support/*` (grep de rede/exec/update), listagem
>   de `Tables/`.
> - **Não inspecionado nesta etapa:** os 159 scripts de patch individuais, o
>   binário/núcleo Qt (se o pré-compilado for usado), `path traversal`/escrita
>   fora do diretório, tratamento de arquivo parcialmente alterado, carregamento
>   de DLL (`CustomDLL`), reprodutibilidade do build e superfície completa.
> - **Transferido para a ETAPA 2P-D:** auditoria integral dos itens acima antes
>   de qualquer uso real. Preferir **compilar do fonte**.

### 6.2 NEMO atual (`4144/Nemo`)

| Item | Resultado | Evidência |
| --- | --- | --- |
| Licença | **ausente** | sem `LICENSE`/`COPYING`; SPDX nulo |
| Binários versionados na raiz | **Sim** — `NEMO.exe`, `CORE.dll`, `Plugin.dll`, `QtCore4.dll`, `QtGui4.dll`, **`QtNetwork4.dll`**, `QtScript4.dll`, `libgcc_s_dw2-1.dll`, `mingwm10.dll` | árvore do repo |
| Build reproduzível | **não evidente** — o motor (`CORE.dll`/`Plugin.dll`) é distribuído como binário versionado | árvore do repo |
| Rede | módulo Qt de rede (`QtNetwork4.dll`) presente (capacidade; uso real exigiria auditoria não permitida nesta etapa) | árvore do repo |
| Fonte de patches | `Patches/`, `Tables/`, `Support/` (scripts) | árvore do repo |
| Manutenção | ativa (2026-06-13) | GitLab API |

**Conclusão:** a **ausência de licença** somada a **binários versionados sem
build reproduzível claro** (risco de cadeia de suprimentos e de conformidade)
inviabiliza a adoção, mesmo o projeto estando ativo.

## 7. Comparação

| Critério | WARP | NEMO atual (4144) | Hex manual | Cliente alternativo legal |
| --- | :-: | :-: | :-: | :-: |
| Origem oficial | Sim | Sim | — | conceitual |
| Licença clara | **GPL-3.0** | **Ausente** | — | — |
| Código-fonte completo | Sim | Parcial (motor em `.dll` versionada) | — | — |
| Commit fixável | Sim | Sim | Não | — |
| Manutenção | Ativa | Ativa | — | — |
| Compatibilidade comprovada | a validar (2P-D) | a validar | frágil | — |
| Execução offline | Sim | provável (a auditar) | Sim | — |
| Dependências | Qt (compilável) | Qt4 (DLLs versionadas) | nenhuma | — |
| Reprodutibilidade | Alta (fonte) | Baixa (binários versionados) | Baixa | — |
| Auditoria possível | Sim (fonte) | Parcial | Baixa | — |
| Backup automático | Inputs/Outputs (a confirmar) | a auditar | Não | — |
| Rollback | excluir cópia de lab | excluir cópia de lab | difícil | — |
| Risco de corrupção | baixo (patches estruturados) | médio | **alto** | — |
| Risco de cadeia de suprimentos | baixo (fonte; binário opcional) | **alto** (binários versionados) | baixo | — |
| Restrições de PI | GPL para o WARP; `Ragexe` proprietário | licença ausente; `Ragexe` proprietário | `Ragexe` proprietário | proprietário |

> "Cliente alternativo legal" foi avaliado apenas conceitualmente: não elimina a
> necessidade de uma ferramenta de preparação, exigiria novo cliente obtido de
> fonte oficial e **não** autoriza distribuir qualquer pacote proprietário. Não
> foi localizado nem distribuído nada.

## 8. Decisão por candidato

| Candidato | Decisão | Motivo |
| --- | --- | --- |
| **WARP** | **APROVAR COM RESTRIÇÕES** | Licença clara (GPL-3.0), fonte auditável, versão fixável, manutenção ativa, sem rede/auto-update **no conjunto inspecionado**, patches de capacidade presentes. Restrições: auditoria aprofundada + autorização humana antes de qualquer uso. |
| **NEMO atual (4144)** | **REJEITADO** | Licença **ausente** + binários versionados sem build reproduzível (risco de PI e de cadeia de suprimentos). **Não** rejeitado por arquivamento (o projeto atual está ativo). Reavaliável se receber licença clara e build reproduzível. |
| NEMO histórico | **REJEITADO** | Arquivado e superado pelo próprio autor; sem licença. |
| Hex manual | **REJEITADO** | Sem perfil reconhecível, não reprodutível, alto risco de corrupção. |
| Cliente alternativo legal | **INCONCLUSIVO** | Apenas conceitual; não avaliado como substituto real nesta etapa. |

### Recomendação principal — **WARP** (APROVAR COM RESTRIÇÕES)

- **Qual ferramenta:** WARP (`github.com/Neo-Mind/WARP`), sem mirror.
- **Commit a fixar:** `9b1173e9e4e135c68e150704f01186ab5e763acd` (abreviação
  `9b1173e9e4e1`; branch `rock_win32`, 2026-05-07) — reconfirmar e registrar
  SHA-256 da árvore no início da 2P-D.
- **Compilar internamente:** **sim, preferencialmente** — compilar o núcleo Qt do
  fonte para máxima auditabilidade.
- **Binário oficial:** aceitável **apenas** após auditoria estática do fonte,
  verificação de integridade e varredura com as proteções locais; execução
  **local**, **não** elevada; **nunca** na VPS. Preferir o build próprio.
- **Patches — apenas candidatos por capacidade, nada obrigatório.** Nenhum patch
  é obrigatório antes de: reconhecimento real do executável, auditoria
  aprofundada, teste em cópia isolada e autorização humana. Candidatos a
  **avaliar** (confirmar cada um contra o comportamento real do cliente):
  `DataFolderFirst` (ler pasta `data`), `CallKoreaClientInfo`/`RestoreClientInfo`
  (ler `clientinfo.xml`), `EnableDnsSupport` (host por nome, se aplicável),
  `LangType` (idioma).
- **Patches sensíveis — jamais selecionados automaticamente:** `DisableProtect`
  (proteção/GameGuard), `DisableEncr` (encriptação), `CustomDLL` (carregamento de
  DLL) e `EnableProxy` (proxy). Cada um exige justificativa comprovada, auditoria
  específica e **autorização humana**; **nenhum** pode ser aplicado por padrão na
  futura execução.
- **Patches proibidos/desnecessários:** todos os cosméticos e de gameplay
  (`Custom*` visuais, `CashShop`, auras, etc.) e qualquer patch não essencial à
  conexão básica.
- **Verificar reconhecimento do executável:** carregar o `Ragexe` no WARP e
  confirmar que ele casa com um perfil conhecido para a data/família; conferir o
  SHA-256 `8990A9A9…`. Se **não** reconhecer com segurança, **interromper**.
- **Preservar o original:** WARP lê de `Inputs/` e grava em `Outputs/` (arquivo
  novo); manter o `Ragexe` original intacto; trabalhar sobre **cópia de
  laboratório** isolada (fora do repositório e de pastas sincronizadas).
- **Validar o resultado:** registrar hash antes/depois e os patches aplicados;
  abrir o cliente localmente e confirmar que aparece **somente** o FaithRO; depois
  (etapa autorizada) executar o teste de login controlado.
- **Rollback:** excluir a cópia de laboratório; original preservado; **não**
  tentar reconstruir o original a partir do modificado.
- **Aprovações humanas ainda exigidas:** auditoria aprofundada (2P-D) **e**
  autorização humana explícita antes de modificar o `Ragexe` (modelo de *gate*
  análogo ao do Beam).

## 9. Condições de aprovação (WARP)

1. Fixar commit e **auditar o fonte integralmente** antes de usar; registrar
   SHA-256 da árvore.
2. Obter **somente** do repositório oficial, sem mirror; preferir build do fonte.
3. Reconhecer o `Ragexe` específico antes de qualquer patch; caso contrário,
   parar.
4. Aplicar **apenas** os patches mínimos necessários; nada cosmético/gameplay.
5. Trabalhar **só** na cópia de laboratório; preservar o original; hash antes/depois.
6. **Nunca** redistribuir o WARP modificado nem o `Ragexe` preparado; nenhum
   arquivo do cliente entra no Git nem vai à VPS.
7. Execução real sujeita a **autorização humana** explícita (2P-D+).

## 10. Arquivos futuros (não criados nesta etapa)

- Cópia de laboratório do cliente (fora do repositório; nunca versionada).
- `Ragexe` preparado (apenas local; nunca versionado nem redistribuído).
- `data\clientinfo.xml` real (a partir do template
  [`client/templates/clientinfo.xml.example`](../client/templates/clientinfo.xml.example);
  nunca versionar o real com IP/porta).

## 11. Passos futuros

1. **ETAPA 2P-D** — auditoria estática aprofundada do WARP (fonte fixado) e
   preparação do laboratório da ferramenta. **Não** modifica o `Ragexe` sem
   autorização humana específica.
2. Autorização humana explícita → preparação do executável em laboratório.
3. Configuração do `clientinfo` de FaithRO e teste de login controlado
   (ver [29 §10](29-compatibilidade-cliente-2021-11-05-packetver.md)).

## 12. Testes

- **Nesta etapa (documental):** inspeção estática de licença, estrutura, submódulos
  e superfície de rede/execução do WARP; auditoria de licença/binários do NEMO
  atual; validações de [FASE J](#) do PR (Markdown, links, ausência de binários,
  segredos, IPs, caminhos pessoais).
- **Futuros (2P-D+):** auditoria dos scripts de patch, reconhecimento do
  executável, integridade, teste de abertura local e teste de login controlado.

## 13. Riscos

- **Segurança/cadeia de suprimentos:** executar ferramenta de terceiros; mitigado
  por auditoria do fonte, build próprio, execução local não elevada e varredura.
- **Corrupção do executável:** mitigada por cópia de laboratório + hash + rollback
  por exclusão.
- **Legal/PI:** `Ragexe` e assets da Gravity são proprietários; **nunca**
  redistribuir; WARP é GPL, usado apenas localmente.
- **Reconhecimento do cliente:** se o WARP não reconhecer o `Ragexe`, não patchear
  às cegas.

## 14. Rollback

Etapa documental: o rollback é reverter o commit desta branch. **Nenhuma**
ferramenta foi obtida/executada; **nenhum** executável foi modificado; **nada**
foi implantado. Para a preparação futura: rollback por exclusão da cópia de
laboratório, com o original preservado.

## 15. Propriedade intelectual

- WARP: **GPL-3.0**; uso local não obriga redistribuição; **não** versionar o
  binário do WARP no FaithRO.
- NEMO atual: **sem licença** → não adotar.
- `Ragexe`, `data.grf`, DLLs e assets da Gravity: **proprietários** — **proibido**
  redistribuir, versionar, hospedar ou empacotar ([16](16-politica-distribuicao-cliente.md)).

## 16. Estado da implantação

```text
Ferramenta obtida:        NÃO
Ferramenta executada:     NÃO
Executável modificado:    NÃO
clientinfo de FaithRO:    NÃO configurado
Teste de login:           NÃO realizado
Autorização humana:       PENDENTE (exigida antes de qualquer preparação real)
```

## Estado de verificação

- **Fato:** metadados de WARP (licença GPL-3.0 declarada, ativo, submódulo só de
  Wiki, sem rede/auto-update **no conjunto inspecionado**) e de NEMO atual (sem
  licença declarada, binários versionados, ativo); estrutura de patches do WARP.
- **Inferência/decisão:** adequação do WARP como ferramenta mínima (APROVAR COM
  RESTRIÇÕES); rejeição do NEMO atual por licença ausente/cadeia de suprimentos.
- **Pendência:** auditoria aprofundada (2P-D) e autorização humana antes de
  qualquer preparação do `Ragexe`; teste de login controlado para compatibilidade.
- **Nota:** decisão técnica e de conformidade do projeto, **não** parecer
  jurídico.
