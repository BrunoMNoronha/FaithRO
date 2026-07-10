# Fontes comunitárias e política de fontes rAthena

> **Escopo:** documento de referência. Não altera código, banco ou configuração.
> Registra a política de fontes do projeto e o conhecimento comunitário
> consultado, sempre distinguindo o que é oficial do que é recomendação
> comunitária.

## Objetivo

Estabelecer uma hierarquia clara de fontes para decisões técnicas do FaithRO,
registrar as fontes efetivamente consultadas e evitar que recomendações de fórum
sejam tratadas como documentação oficial.

## Critérios de seleção

- Priorizar código, testes e documentação **oficiais** do rAthena.
- Dar preferência a conteúdo em **português** (comunidade lusófona).
- Considerar data de publicação, data de atualização, versão do rAthena, data do
  cliente, modo Renewal/Pre-Renewal, patches e estado da obfuscação.
- Não confiar apenas na primeira postagem de um tópico: ler respostas
  posteriores, correções e relatos de falha.
- Nunca inventar fonte, autor, data, versão, hash, URL ou resultado de teste.
- Não usar anexos executáveis como fonte confiável; não baixar clientes
  completos, GRFs ou executáveis modificados; preferir links para a **discussão**.

## Hierarquia de fontes (prioridade)

1. Código oficial do rAthena.
2. Workflows e testes oficiais do rAthena (CI).
3. Documentação e wiki oficial do rAthena.
4. Issues e pull requests do repositório oficial.
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

## Tabela de fontes consultadas

| Tema | Fonte | Idioma | Tipo | Data de acesso | Confiança | Uso no FaithRO |
| --- | --- | --- | --- | --- | --- | --- |
| Default de `PACKETVER` | [`src/config/packets.hpp` (rAthena `master`)](https://github.com/rathena/rathena/blob/master/src/config/packets.hpp) | EN | Código oficial | 2026-07-10 | Confirmado no código | Baseline `PACKETVER=20211103` |
| Definição de `PACKETVER_RE` | [`src/config/packets.hpp` (rAthena `master`)](https://github.com/rathena/rathena/blob/master/src/config/packets.hpp) | EN | Código oficial | 2026-07-10 | Confirmado no código | Explica macro interna para `20211103` |
| Packet obfuscation padrão | [`src/config/packets.hpp` (rAthena `master`)](https://github.com/rathena/rathena/blob/master/src/config/packets.hpp) | EN | Código oficial | 2026-07-10 | Confirmado no código | Obfuscação ativa por padrão (`>= 20110817`) |
| Matriz de packet versions da CI | [`.github/workflows/build_servers_packetversions.yml`](https://github.com/rathena/rathena/blob/master/.github/workflows/build_servers_packetversions.yml) | EN | CI oficial | 2026-07-10 | Confirmado em CI oficial | `20211103` compilado em `PRE` e `RE` |
| Configuração de `PACKETVER` / Configure | [Wiki oficial do rAthena](https://github.com/rathena/rathena/wiki) | EN | Wiki oficial | 2026-07-10 | Oficial | Mecanismos `--enable-packetver` e `defines_pre.hpp` |
| Web server / emblema de guilda | [Issue #5114 — Can't set guild emblem](https://github.com/rathena/rathena/issues/5114) | EN | Issue oficial | 2026-07-10 | Comunidade — alta confiança | Emblema depende do web server e das tabelas SQL |
| Web server (suporte) | [Guild emblem not work (athena-web-service)](https://rathena.org/board/topic/127275-guild-emblem-not-workathena-web-service/) | EN | Fórum internacional | 2026-07-10 | Comunidade — requer validação | Contexto de configuração do web service |
| Compilação após definir `PACKETVER` | [Issue #6803 — Not able to compile after defining PACKETVER](https://github.com/rathena/rathena/issues/6803) | EN | Issue oficial | 2026-07-10 | Comunidade — alta confiança | Alerta sobre onde definir `PACKETVER` |

> Fontes internacionais foram usadas por ausência de equivalente lusófono
> confirmado para estes pontos específicos. A busca priorizou conteúdo em
> português; quando não localizado, registrou-se a fonte oficial/internacional.

## Tópicos do fórum a revisar (pendente de validação)

Os tópicos abaixo foram indicados como relevantes, mas **ainda não** tiveram seu
conteúdo integral validado nesta tarefa. Ao usá-los, ler respostas posteriores e
confirmar compatibilidade com o commit e o `PACKETVER` do FaithRO. Não usar o
título como prova suficiente.

- "Most Stable Client for Renewal now?" — `Pendente de validação`.
- "Renewal Client data & Hexed 2021-11-03_Ragexe compatible with rAthena" —
  `Pendente de validação`.
- "Stable Combo For PACKETVER, packet_db_ver and Client" — `Pendente de
  validação`.
- Discussões recentes sobre incompatibilidade de pacotes e packet obfuscation —
  `Pendente de validação`.

> Prioridade de busca futura: tópicos em português e contribuições de membros
> brasileiros/lusófonos. Registrar título, idioma, tipo, autor/comunidade, datas
> de publicação/atualização/acesso, URL da discussão, informação obtida, nível de
> confiança, limitações e relação com o commit e o `PACKETVER` do FaithRO.

## Itens pendentes

- Validação integral dos tópicos de fórum listados acima.
- Confirmação do gating de compilação do web server no código.
- Verificação do commit `7f080871c` em um checkout real do rAthena.
- Levantamento de fontes lusófonas equivalentes para os temas hoje cobertos
  apenas por fontes internacionais.

## Referências cruzadas

- [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md) — baseline
  do cliente, protocolo, obfuscação e matriz de compatibilidade.
- [01-decisao-tecnica.md](01-decisao-tecnica.md) — decisão pelo rAthena.
</content>
