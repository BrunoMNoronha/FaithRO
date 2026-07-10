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

## Tabela de fontes consultadas

### Fontes oficiais

| Tema | Fonte | Idioma | Tipo | Data | Confiança | Uso no FaithRO |
| ---- | ----- | ------ | ---- | ---- | --------- | -------------- |
| Configuração de `PACKETVER` / Configure | [Wiki oficial do rAthena](https://github.com/rathena/rathena/wiki) | EN | Wiki oficial | 2026-07-10 | Oficial | Mecanismos `--enable-packetver` e `defines_pre.hpp` |

### Código e CI

| Tema | Fonte | Idioma | Tipo | Data | Confiança | Uso no FaithRO |
| ---- | ----- | ------ | ---- | ---- | --------- | -------------- |
| Default de `PACKETVER` e `PACKETVER_RE` | [`src/config/packets.hpp` @ 7f080871c](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/config/packets.hpp) | EN | Código oficial | 2026-07-10 | Confirmado no código | Base do baseline (20211103) |
| Packet obfuscation (macro) | [`src/config/packets.hpp` @ 7f080871c](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/config/packets.hpp) | EN | Código oficial | 2026-07-10 | Confirmado no código | Aplica-se a 20211103 |
| Packet obfuscation | [`src/map/clif_obfuscation.hpp` @ 7f080871c](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/map/clif_obfuscation.hpp) | EN | Código oficial | 2026-07-10 | Confirmado no código | Suporte e regras identificados no upstream |
| `WEB_SERVER_ENABLE` | [`src/config/packets.hpp` @ 7f080871c](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/config/packets.hpp) | EN | Código oficial | 2026-07-10 | Confirmado no código | Habilitado pelo código |
| Componente web e emblema | [`src/web/web.cpp` @ 7f080871c](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/web/web.cpp) | EN | Código oficial | 2026-07-10 | Confirmado no código | Requer web server para emblema |
| Matriz de packet versions | [`.github/workflows/build_servers_packetversions.yml` @ 7f080871c](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/.github/workflows/build_servers_packetversions.yml) | EN | CI oficial | 2026-07-10 | Confirmado em CI oficial | 20211103 consta na matriz |

### Fórum em português

*(Nenhum tópico referenciado nesta documentação até o momento).*

### Fórum internacional

*(Os tópicos discutindo clientes estáveis não sustentam decisões neste momento e foram removidos desta lista por não terem sido integralmente validados).*

### Outras fontes comunitárias

| Tema | Fonte | Idioma | Tipo | Data | Confiança | Uso no FaithRO |
| ---- | ----- | ------ | ---- | ---- | --------- | -------------- |
| Patchers NEMO | Forks em repositórios da comunidade | EN | Repo Comunitário | 2026-07-10 | Comunidade — requer validação | Uso externo pendente |

### Fontes históricas

| Tema | Fonte | Idioma | Tipo | Data | Confiança | Uso no FaithRO |
| ---- | ----- | ------ | ---- | ---- | --------- | -------------- |
| nemo.herc.ws original | indisponível/descontinuado | EN | Site/Ferramenta | N/A | Histórico/desatualizado | Substituído por forks |

### Fontes não recomendadas

| Tema | Fonte | Idioma | Tipo | Data | Confiança | Uso no FaithRO |
| ---- | ----- | ------ | ---- | ---- | --------- | -------------- |
| Links diretos de executáveis | Hospedagens (Mega, MediaFire, GDrive) | Vários | Downloads | N/A | Não recomendado | Proibido no projeto |

### Itens pendentes

- Identificação de discussões lusófonas atualizadas e confiáveis.
- Verificação do commit e configuração efetivamente compilados na VPS.

## Referências cruzadas

- [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md) — baseline
  do cliente, protocolo, obfuscação, web server e matriz de compatibilidade.
- [01-decisao-tecnica.md](01-decisao-tecnica.md) — decisão pelo rAthena.
