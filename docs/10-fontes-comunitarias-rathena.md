# Fontes comunitárias e política de fontes rAthena

> **Escopo:** documento de referência. Não altera código, banco ou configuração.
> Registra a política de fontes do projeto e o conhecimento comunitário
> consultado, sempre distinguindo o que é oficial do que é recomendação
> comunitária.

## Objetivo

Estabelecer uma hierarquia clara de fontes para decisões técnicas do FaithRO,
registrar as fontes efetivamente consultadas e evitar que recomendações de fórum
— ou comentários em issues — sejam tratados como documentação oficial.

## Critérios de seleção

- Priorizar código, testes e documentação **oficiais** do rAthena.
- Dar preferência a conteúdo em **português** (comunidade lusófona).
- Avaliar a informação pelo **conteúdo e pela confirmação no código**, não pela
  hospedagem. Uma issue no repositório oficial **não é** automaticamente
  documentação oficial nem "alta confiança" só por estar no GitHub oficial.
- Considerar data de publicação, data de atualização, versão do rAthena, data do
  cliente, modo Renewal/Pre-Renewal, patches e estado da obfuscação.
- Não confiar apenas na primeira postagem de um tópico: ler respostas
  posteriores, correções e relatos de falha.
- Nunca inventar fonte, autor, data, versão, hash, URL ou resultado de teste.
- Não usar anexos executáveis como fonte confiável; não incluir links para
  clientes completos, executáveis modificados ou pacotes hospedados em
  Mega/Drive/MediaFire; preferir links para a **página da discussão**.

## Hierarquia de fontes (prioridade)

1. Código oficial do rAthena (preferencialmente fixado em commit).
2. Workflows e testes oficiais do rAthena (CI).
3. Documentação e wiki oficial do rAthena.
4. Issues e pull requests do repositório oficial (como discussão, não como
   documentação oficial).
5. Fórum rAthena em português.
6. Publicações de membros brasileiros/lusófonos.
7. Tópicos internacionais do fórum rAthena.
8. Documentação oficial das ferramentas utilizadas.
9. Repositórios oficiais dos autores das ferramentas.
10. Outras fontes comunitárias, apenas quando necessário e com ressalvas.

## Níveis de confiança

- `Oficial`
- `Confirmado no código`
- `Confirmado em CI oficial`
- `Comunidade — alta confiança`
- `Comunidade — requer validação`
- `Histórico/desatualizado`
- `Não recomendado`
- `Confirmado na configuração de build auditada`

## Commit de referência

Todas as evidências de código abaixo estão fixadas no commit
`7f080871c8b3bbe7a79027194633201c63422ee1` (abreviado `7f080871c`). O `master`
pode aparecer apenas como referência adicional sobre o estado atual do upstream,
nunca como única evidência de uma decisão vinculada a esse commit. A confirmação
de que a VPS realmente usa esse commit foi **verificada por auditoria
read-only em 2026-07-10**: `/opt/faithro/rathena` está no mesmo commit
`7f080871c`, working tree limpo (ver
[11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md)).

## Tabela de fontes consultadas

| Tema | Título/fonte | Idioma | Tipo | Autor/comunidade | Publicação | Última atualização | Acesso | Informação obtida | Confiança | Limitações | Relação com commit/PACKETVER |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Default de `PACKETVER` e `PACKETVER_RE` | [`src/config/packets.hpp` @ 7f080871c](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/config/packets.hpp) | EN | Código oficial (commit fixado) | rAthena | N/A (arquivo de código) | commit `7f080871c` | 2026-07-10 | `PACKETVER 20211103` padrão; `PACKETVER_RE` definido automaticamente para `20211103` | Confirmado no código | Reflete o commit fixado, não a VPS | Base do baseline; commit `7f080871c` |
| Packet obfuscation (macro) | [`src/config/packets.hpp` @ 7f080871c](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/config/packets.hpp) | EN | Código oficial (commit fixado) | rAthena | N/A | commit `7f080871c` | 2026-07-10 | `PACKET_OBFUSCATION` definida para `PACKETVER >= 20110817` | Confirmado no código | Macro geral; não é a atribuição de chaves | Aplica-se a `20211103` |
| Packet obfuscation (chaves efetivas) | [`src/map/clif_obfuscation.hpp` @ 7f080871c](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/map/clif_obfuscation.hpp) | EN | Código oficial (commit fixado) | rAthena | N/A | commit `7f080871c` | 2026-07-10 | Chaves zero para `PACKETVER > 20180307` (sem obfuscação efetiva no baseline) | Confirmado no código | Comportamento padrão; executável real ainda a verificar | Aplica-se a `20211103` |
| `WEB_SERVER_ENABLE` | [`src/config/packets.hpp` @ 7f080871c](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/config/packets.hpp) | EN | Código oficial (commit fixado) | rAthena | N/A | commit `7f080871c` | 2026-07-10 | `#define WEB_SERVER_ENABLE PACKETVER > 20200300` → verdadeiro para `20211103` | Confirmado no código | Gating de compilação; não confirma implantação | Aplica-se a `20211103` |
| Componente web e emblema | [`src/web/web.cpp` @ 7f080871c](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/web/web.cpp) · [`src/web/emblem_controller.cpp` @ 7f080871c](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/web/emblem_controller.cpp) | EN | Código oficial (commit fixado) | rAthena | N/A | commit `7f080871c` | 2026-07-10 | Existe web server dedicado e controlador de emblema (tabela `guild_emblems`) | Confirmado no código | Não confirma que está compilado/implantado na VPS | Requer web server para emblema |
| Porta padrão do web server | [`conf/web_athena.conf` @ 7f080871c](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/conf/web_athena.conf) | EN | Config oficial (commit fixado) | rAthena | N/A | commit `7f080871c` | 2026-07-10 | `web_port: 8888` padrão; `bind_ip` comentado (`127.0.0.1`) | Confirmado no código | Padrão upstream; porta efetiva do FaithRO pendente | Override via `conf/import/web_conf.txt` |
| Matriz de packet versions da CI | [`.github/workflows/build_servers_packetversions.yml` @ 7f080871c](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/.github/workflows/build_servers_packetversions.yml) | EN | CI oficial (commit fixado) | rAthena | N/A | commit `7f080871c` | 2026-07-10 | `20211103` compilado em modos `PRE` e `RE` | Confirmado em CI oficial | Cobertura de build, não de gameplay | `20211103` na matriz |
| Configuração de `PACKETVER` / Configure | [Wiki oficial do rAthena](https://github.com/rathena/rathena/wiki) | EN | Wiki oficial | rAthena | Pendente de validação | Pendente de validação | 2026-07-10 | Mecanismos `--enable-packetver` e `defines_pre.hpp` | Oficial | Wiki vive no `master`; confirmar contra o commit | Aplica-se ao baseline |
| Macro `PRERE` e macros Renewal dependentes | [`src/config/renewal.hpp` @ 7f080871c](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/config/renewal.hpp) | EN | Código oficial (commit fixado) | rAthena | N/A (arquivo de código) | commit `7f080871c` | 2026-07-10 | `#ifndef PRERE` define `RENEWAL`, `RENEWAL_CAST`, `RENEWAL_DROP`, `RENEWAL_EXP`, `RENEWAL_LVDMG`, `RENEWAL_ASPD`, `RENEWAL_STAT`; `PRERE` desabilita o bloco inteiro | Confirmado no código | Descreve o padrão quando `PRERE` não está definido; não confirma, por si só, o build efetivo (ver auditoria de `config.log` abaixo) | Base da decisão de mecânica em [03-configuracao-alvo.md](03-configuracao-alvo.md) |
| Evidência da configuração de build (`config.log`) | `config.log` do checkout `/opt/faithro/rathena` | N/A (log de build) | Auditoria read-only própria (não é fonte comunitária externa, não versionada) | Equipe FaithRO | N/A | build instalado, commit `7f080871c` | 2026-07-10 | `./configure --enable-prere=yes`; `CPPFLAGS` efetivas contêm `-DPRERE`; `src/custom/defines_pre.hpp` vazio (sem override manual) | Confirmado na configuração de build auditada | Não reexecuta nem inspeciona símbolos do binário; não é evidência independente da proveniência dos binários atuais; não confirma comportamento de gameplay | Resolve a classificação de mecânica em [03-configuracao-alvo.md](03-configuracao-alvo.md) como "Pre-Renewal confirmado na configuração registrada do build" |

## Fórum rAthena e issues (não validados integralmente)

Os tópicos e issues abaixo foram **indicados** como relevantes, mas **não**
tiveram seu conteúdo integral validado nesta tarefa. Para eles: não usar o título
como evidência; registrar URL apenas se confirmada; marcar informação obtida como
`Pendente de validação` e confiança como `Comunidade — requer validação`; não
afirmar leitura integral que não ocorreu.

| Tema | Título/fonte | Idioma | Tipo | Confiança | Situação |
| --- | --- | --- | --- | --- | --- |
| Cliente estável Renewal | "Most Stable Client for Renewal now?" | EN | Fórum internacional | Comunidade — requer validação | Pendente de validação |
| Cliente `2021-11-03_Ragexe` | "Renewal Client data & Hexed 2021-11-03_Ragexe compatible with rAthena" | EN | Fórum internacional | Comunidade — requer validação | Pendente de validação |
| Combo estável de `PACKETVER` | "Stable Combo For PACKETVER, packet_db_ver and Client" | EN | Fórum internacional | Comunidade — requer validação | Pendente de validação |
| Web server / emblema | Discussões sobre web server, emblemas e incompatibilidade de pacotes | EN | Fórum/issue | Comunidade — requer validação | Pendente de validação |

> Estes itens não têm URL registrada porque não foram abertos e validados
> integralmente nesta tarefa. Ao validá-los futuramente, registrar título,
> idioma, tipo, autor/comunidade, datas de publicação/atualização/acesso, URL da
> **discussão**, informação obtida, nível de confiança, limitações e relação com
> o commit e o `PACKETVER` do FaithRO.

## Ausência de fonte lusófona

Para os pontos técnicos hoje cobertos (protocolo, obfuscação, web server), a
evidência principal veio do **código oficial** do rAthena. Não foi localizada,
nesta tarefa, uma fonte lusófona equivalente e confirmada para esses pontos
específicos. Registro honesto: **fonte lusófona equivalente pendente de
localização**.

## Itens pendentes

- Validação integral dos tópicos de fórum/issues listados (com URL confirmada).
- ~~Verificação do commit efetivamente instalado na VPS~~ — confirmado em
  auditoria read-only de 2026-07-10: `7f080871c`, idêntico ao commit upstream
  de referência (ver
  [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md)).
- Verificação da configuração efetivamente compilada na VPS quanto a
  obfuscação e `PACKETVER_RE` (comportamento do binário, não apenas do
  código-fonte); implantação completa do web server (unidade, porta,
  firewall) — ver [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md).
- Configuração de build Pre-Renewal: confirmada no `config.log` em auditoria
  read-only de 2026-07-10 (`--enable-prere=yes`, `CPPFLAGS` efetivas com
  `-DPRERE`; ver [03-configuracao-alvo.md](03-configuracao-alvo.md), seção
  "Estado atual do build").
- Proveniência dos binários atuais em relação ao `config.log`: não atestada
  nesta auditoria.
- Comportamento funcional Pre-Renewal: validar em testes de gameplay.
- Levantamento de fontes lusófonas equivalentes.

## Referências cruzadas

- [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md) — baseline
  do cliente, protocolo, obfuscação, web server e matriz de compatibilidade.
- [01-decisao-tecnica.md](01-decisao-tecnica.md) — decisão pelo rAthena.
</content>
