# Revisão de economia e combate, 19/10/2026

Esta publicação continua o estudo do PR #93. A árvore operacional usada na VPS e
na cópia de trabalho ainda difere deste repositório: caminhos `server/`, `web/` e
`deploy/vps/` citados nos relatórios são referências operacionais. Este PR não
substitui `deploy/rathena-overlay/`, não publica a aplicação web e não executa deploy.

## Objetivo e evidência

- [Relatório atualizado](../docs/balanceamento.md): economia, mapas, atributos,
  combate, limitações e validações funcionais dos NPCs.
- [Estudo anterior revisado](../docs/estudo-balanceamento.md): corrige interpretações
  de logs, orçamentos e números históricos.
- [Drops](../docs/drops.md): regras de chance usadas na cópia operacional.
- `balance-review-20261019/`: coletor de leitura e snapshot público dos dados do
  jogo/cálculos. Campos de métricas de jogadores foram retirados da cópia publicada;
  não há contas, personagens reais, inventários de jogadores ou dumps SQL.
- `balance-session-kit/`: equipamentos, habilidades, plano e 16 fichas pendentes.
  Nenhuma ficha representa combate executado. `prepare.py` nunca sobrescreve dados.
- `game-lab/`, `npc-runtime/`, `service-runtime/`: resultados sintéticos dos
  laboratórios descartáveis e propostas de correção.
- `candidate-runtime/`: comparação posterior dos NPCs instalados com os dois patches,
  nove builds de cura, 40 combinações de tarifa e cinco recusas por saldo insuficiente.
  Os patches foram aplicados somente a cópias privadas temporárias.

A referência continua EXP 300x, nível 255, atributos 185 e ASPD 197. Cenários de
150/300/600 abates por hora são cálculos condicionais. Linhas de drops não são
abates, intervalos de logs não são horas jogadas e o piloto real está em 0/3 sessões.

## Arquivos e impacto

`tools/analyze_balance_session.py` e `tools/analyze_balance_pilot.py` validam arquivos
locais, sem rede ou banco. Os executores `tools/isolated_*` e o mini-cliente Python
`tools/bot/` são ferramentas de QA manual. Não são iniciados por CI, serviço ou
deploy deste PR. O workflow novo executa somente os 83 testes locais e análise de
sintaxe. Nenhum executável ou asset proprietário é publicado.

Os hashes `local_tool_sha256` e `tested_tool_sha256` identificam a versão usada em
cada coleta, inclusive versões anteriores dos executores. Não significam que todos
os ensaios foram feitos com a última versão. Os `.gitattributes` locais preservam
os bytes de ferramentas, curva e evidências para evitar conversão CRLF/LF.

## Como testar

Na raiz do repositório, com Python 3.12 e pytest:

```sh
python -m pytest tools/tests/test_balance_session.py tools/tests/test_balance_pilot.py tools/tests/test_bot_protocol.py -q
```

As fichas `pending` devem ser recusadas, sem produzir métricas. Copiar uma ficha
antes de preenchê-la; registrar tempo explícito, contador calibrado, build,
equipamentos, consumíveis, mortes, EXP e fluxos de moeda. Os analisadores não
autorizam mudanças de balanceamento.

Os laboratórios Linux exigem ferramentas já instaladas, root para namespaces e o
layout operacional indicado nos executores. O modo `--npc-checks` também depende do
builder instalado em `/root/faithro/deploy/web/tools/build_gamedb.py`; ele não está
incluído neste PR. Não executar os laboratórios no checkout Windows nem no CI.
Uma repetição manual cria banco novo e servidores próprios em namespaces privados,
com limites de recursos, fontes somente de leitura e remoção do ambiente ao sair.
O mini-cliente usa `PACKETVER 20260219`, conforme a instalação analisada.

O modo manual `--candidate-checks` exige `git` já instalado, o helper
`isolated_candidate_checks.py`, o pacote `bot` e os dois patches de `service-runtime/`
ao lado do executor no pacote temporário enviado ao Linux. Compara duas instâncias
sequenciais de map-server, encerrando a primeira antes de conferir/aplicar os patches
nas cópias privadas. Limites: CPU 25%, 512 MiB e 600 s. Não instala ferramentas,
não executa combate e não escreve nos NPCs instalados.

## Riscos e rollback

Os patches candidatos de Curandeira e Warpra são arquivos de referência validados no
laboratório, sem aplicação no overlay operacional ou na produção. O registro original
de propostas permanece em `service-runtime/recommendations.json`; os resultados e
critérios atualizados estão em `candidate-runtime/recommendations.json`. Não habilitar
calabouços da Warpra em produção a partir desta publicação.

Risco deste PR: interpretar resultados funcionais sintéticos como farm real ou
aplicar procedimentos específicos da instalação em outro layout. O relatório
explicita essas limitações. Para desfazer a publicação, reverter seus commits por
novo PR; não há migração ou mudança de produção para reverter.
