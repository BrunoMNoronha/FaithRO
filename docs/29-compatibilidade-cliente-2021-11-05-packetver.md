# Compatibilidade do cliente 2021-11-05 com o `PACKETVER` do servidor

> **Escopo:** documento de reconciliação técnica, **somente leitura**. Nenhuma
> alteração de código, banco, configuração, `PACKETVER` ou build foi executada.
> Nenhum cliente foi executado ou modificado. Nenhum acesso à VPS foi feito nesta
> etapa. Complementa [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md)
> e [12-configuracao-packetver.md](12-configuracao-packetver.md).

## 1. Objetivo

Determinar, por evidência técnica, se o executável do cliente legalmente possuído
pelo responsável — identificado com carimbo PE de **2021-11-05** — é compatível
com o servidor atual do FaithRO, compilado com `PACKETVER=20211103`
(Pre-Renewal), e se alguma mudança futura de `PACKETVER` é necessária. A decisão
segue a regra: **não** alterar o servidor se a compatibilidade for `COMPROVADA`
ou `PROVÁVEL`.

## 2. Identificação do executável (evidência local, read-only)

| Campo | Valor | Classificação |
| --- | --- | --- |
| Família aparente | `Ragexe` (nome `Ragexe.exe`, não `RagexeRE`) | Fato |
| Arquitetura | x86 (PE Machine `0x014C`), 12 seções | Fato |
| **Carimbo PE (link date)** | **2021-11-05 01:31:18 UTC** | Fato |
| Versão PE (FileVersion/ProductVersion) | ausente (vazia) | Fato |
| Nome interno / OriginalFilename | ausentes | Fato |
| Assinatura Authenticode | **Válida** — `GRAVITY Co., Ltd.` (executável oficial, não hexado) | Fato |
| SHA-256 | `8990A9A9CD6623E173BCC8B406A311AF32773EB881E539082126B768C14E95A0` | Fato |
| Origem legal | Instalado a partir do `RAG_SETUP_211105` (instalador oficial Gravity, assinatura válida — ver [16](16-politica-distribuicao-cliente.md)) | Fato |

## 3. Diferença entre timestamp e protocolo

É obrigatório **não** interpretar um único metadado como o `PACKETVER`. Distinção
explícita:

| Conceito | Valor no caso FaithRO | Observação |
| --- | --- | --- |
| Data do instalador | `211105` (nome `RAG_SETUP_211105`) | metadado de empacotamento |
| Data de distribuição | 2021-11 (kRO) | metadado de release |
| **Timestamp PE (link)** | **2021-11-05** | data de *build* do executável (mais confiável que `mtime` de arquivo, mas ainda **não** é o `PACKETVER` por si só) |
| Nome comunitário do cliente | "cliente 2021-11-05" | convenção da comunidade |
| Data do protocolo (`PACKETVER` do cliente) | provavelmente `20211105` | a data de build costuma ser adotada como `PACKETVER`, mas o que importa é a **estrutura de pacotes** que o cliente usa |
| `PACKETVER` do servidor | `20211103` (default do fonte, sem override, sem `--enable-packetver`; ver [12](12-configuracao-packetver.md) e a auditoria 2P-A) | valor efetivo do build |

O carimbo PE prova apenas **quando** o executável foi linkado, não **qual**
estrutura de pacotes ele fala. A compatibilidade é decidida pela estrutura de
pacotes, analisada a seguir.

## 4. Evidências encontradas (fontes primárias — rAthena @ `7f080871c`)

Inspeção do código-fonte do rAthena no commit **instalado na VPS**
(`7f080871c8b3bbe7a79027194633201c63422ee1`), via arquivos oficiais no GitHub:

- [`src/config/packets.hpp`](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/config/packets.hpp):
  - `#define PACKETVER 20211103` (default do fonte);
  - `PACKETVER_RE` é definido automaticamente para o intervalo
    `>= 20200902 && <= 20211118` (portanto **tanto 20211103 quanto 20211105**
    são RE).
- [`src/map/packets_struct.hpp`](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/map/packets_struct.hpp),
  [`src/map/clif_packetdb.hpp`](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/map/clif_packetdb.hpp)
  e [`src/map/clif_shuffle.hpp`](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/map/clif_shuffle.hpp):
  - **todas** as estruturas de pacote e o *shuffle* da era de novembro/2021 no
    ramo RE são chaveados por **`PACKETVER_RE_NUM >= 20211103`**;
  - **não existe** nenhum guard intermediário em `20211104`, `20211105` ou
    qualquer data até `20211118` — a única fronteira RE nessa janela é
    `20211103`, e o intervalo RE encerra em `20211118` (`packets.hpp`).

**Consequência:** o rAthena modela **toda a janela `[20211103, 20211118]`** com
**a mesma** estrutura de pacotes e o mesmo *shuffle*. Um servidor compilado com
`PACKETVER=20211103` satisfaz `>= 20211103` (igualdade inclusa) e portanto produz
o **mesmo layout de pacotes** que produziria para `20211105`. Um cliente
2021-11-05 cai dentro dessa janela.

Obfuscação: conforme [09 §6](09-cliente-baseline-protocolo.md), para
`PACKETVER > 20180307` as chaves efetivas são **zero** (sem obfuscação efetiva);
isso vale igualmente para 20211103 e 20211105.

## 5. `PACKETVER` mais provável do cliente

```text
CLIENTE COMPROVADO:            Ragexe família, build (PE link) 2021-11-05, x86, assinado Gravity
PACKETVER MAIS PROVÁVEL:       20211105 (data de build), pertencente à mesma geração RE de 20211103
NÍVEL DE CONFIANÇA:            MÉDIO-ALTO
EVIDÊNCIA:                     guards RE chaveados em 20211103 sem branch até 20211118
                               (packets_struct.hpp, clif_packetdb.hpp, clif_shuffle.hpp @ 7f080871c)
COMPATIBILIDADE COM 20211103:  PROVÁVEL
```

## 6. Compatibilidade com o servidor

- O servidor está em `PACKETVER=20211103`, Pre-Renewal, com `PACKETVER_RE`
  definido internamente (decisão do rAthena, ver [09 §3](09-cliente-baseline-protocolo.md)).
- Estruturalmente, 20211103 e 20211105 são idênticos para o rAthena neste commit.
- Portanto a compatibilidade é classificada como **PROVÁVEL** — forte evidência
  de fonte primária, sem, ainda, um teste de login controlado que a eleve a
  `COMPROVADA`.

## 7. Lacunas

- Não há, nesta etapa, um **teste de login controlado** (cliente real ↔ servidor)
  que confirme ausência de `Unknown packet`. Essa é a única prova que converte
  `PROVÁVEL` em `COMPROVADA`.
- O executável ainda **não** está preparado para conectar a servidor privado
  (oficial/assinado, GameGuard, sem `clientinfo` de FaithRO — ver
  [28](28-decisao-ferramenta-preparacao-cliente.md)); o teste depende dessa
  preparação futura e autorizada.
- O `PACKETVER` exato do cliente não é lido diretamente do executável nesta
  etapa; é **inferido** pela data de build e confirmado estruturalmente pelo lado
  do servidor.

## 8. Matriz

| Item | Valor | Classificação |
| --- | --- | --- |
| Família do cliente | `Ragexe` 2021-11-05 (x86, assinado) | Fato |
| `PACKETVER` do servidor | `20211103` (default, sem override) | Fato |
| Geração de protocolo RE | `[20211103, 20211118]` sem branch intermediário | Fato |
| `PACKETVER` provável do cliente | `20211105` (mesma geração RE) | Inferência |
| Compatibilidade | **PROVÁVEL** | Inferência (fonte primária) |
| Necessidade de rebuild do servidor | **Não** (regra decisória: PROVÁVEL) | Decisão |
| Prova definitiva | teste de login controlado | Pendência |

## 9. Decisão

- **Não** alterar o `PACKETVER` do servidor e **não** recompilar o rAthena: a
  compatibilidade é **PROVÁVEL** e a regra proíbe mudança do servidor nesse caso.
- Elevar a classificação para `COMPROVADA` **apenas** por um teste de login
  controlado, após a preparação autorizada do executável
  ([28](28-decisao-ferramenta-preparacao-cliente.md)).
- Se, e somente se, um teste controlado revelar `DIVERGENTE` (ex.: `Unknown
  packet`), abrir tarefa **separada** de mudança de `PACKETVER` com build limpo e
  rollback (ver [12](12-configuracao-packetver.md)); nunca por tentativa e erro.

## 10. Testes futuros

1. Preparar o executável em laboratório (etapa autorizada; ver [28](28-decisao-ferramenta-preparacao-cliente.md)).
2. Teste de login controlado a partir do IP autorizado: cliente alcança o
   login-server, autentica, recebe a lista de personagens, entra no mapa —
   **sem** `Unknown packet` nem desconexão por divergência de pacotes.
3. Observar os logs do servidor (sanitizados) em busca de erros de pacote.
4. Registrar o resultado e, se positivo, atualizar a classificação para
   `COMPROVADA`.

## 11. Riscos

- **Divergência inesperada:** se o cliente 2021-11-05 tiver alguma diferença de
  pacote não modelada, ocorreria `Unknown packet`. Mitigação: teste controlado
  antes de qualquer uso amplo; rollback documental; sem rebuild especulativo.
- **Inferência de `PACKETVER`:** a data de build não é prova absoluta do
  protocolo; mitigada pela análise estrutural do lado do servidor.
- **Confusão timestamp × protocolo:** documentada explicitamente na §3 para
  evitar decisões erradas.

## 12. Rollback

Documento read-only: o rollback é reverter o commit desta branch. **Nenhuma**
mudança operacional foi feita; não há `PACKETVER`, build, binário ou serviço a
reverter. Qualquer mudança futura de `PACKETVER` terá seu próprio rollback com
backup de binário e configuração (ver [12](12-configuracao-packetver.md)).

## Estado de verificação

- **Fato (confirmado em fonte primária / evidência local):** identificação do
  executável (PE, assinatura, SHA-256); guards RE do rAthena chaveados em
  `20211103` sem branch até `20211118`.
- **Inferência:** `PACKETVER` provável do cliente `20211105`; compatibilidade
  `PROVÁVEL`.
- **Pendência:** teste de login controlado para elevar a `COMPROVADA`.
