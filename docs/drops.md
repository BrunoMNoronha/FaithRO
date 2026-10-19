# Drops do FaithRO

Referência das decisões sobre taxas de drop (2026-10-18, segunda rodada de balanceamento; a
primeira está em `docs/balanceamento.md`). Pre-renewal, 300x de EXP, nível 255. Dados: base do
site (`faithro_web`: 1.004 monstros, 5.019 drops, 1.907 spawns, montada por
`web/tools/build_gamedb.py` do rAthena commit d4b8e7b) e o código de `src/map/mob.cpp`.
O estudo original não encontrou jogadores. Em 19/10 apareceu uma conta comum com personagem
nível 16; ainda não há amostra de farm que valide os cenários. Números por hora continuam
sendo estimativas; a revisão atual está em `docs/balanceamento.md`.

## Como o rAthena calcula a chance

Na carga do `mob_db`, para cada drop: `chance = oficial x item_rate_<categoria> / 100`, limitada
por `item_drop_<categoria>_min/max`. A categoria vem do tipo do item (cura, usável, equipamento,
carta, demais = "common"); monstros `Class: Boss` usam a variante `_boss`, MVPs a `_mvp`; o slot de
prêmio de MVP usa `item_rate_mvp`; baús de WoE usam `item_rate_treasure`. Se o item estiver em
`db/import/mob_item_ratio.yml`, o `Ratio` **substitui** o multiplicador da categoria para aquele
item (100 = oficial), e os tetos continuam valendo depois.

Dois pontos que enganam:

- `drop_rate_cap: 9000` (90%) só limita bônus do jogador (cartas, chiclete, modo PK). Não limita os
  multiplicadores do servidor: com 100x, qualquer drop oficial de 1% ou mais caía garantido.
- Jogadores não têm `@autoloot` (grupo 0 do `groups.yml`) e `item_auto_get: no`. O zeny por
  limpeza abaixo é teto teórico; na prática quem farma pega só o que vale a pena.

## Diagnóstico (rates de 13/10: comum/cura/usável 100x, equipamento 50x, MVP 10x, baús 10x)

| Categoria | Drops | A 100% | A 50% ou mais |
|---|---|---|---|
| Materiais (common) | 2.175 | 1.735 | 1.856 |
| Equipamento | 1.072 | 228 | 326 |
| Cura | 496 | 435 | 460 |
| Usável | 224 | 89 | 118 |
| Prêmio de MVP | 153 | 144 | 151 |
| Baús de WoE | 395 | 174 | 290 |
| Cartas | 504 | 0 | 0 |

Consequências:

- 180 drops de itens com venda de 10 mil ou mais caíam em metade ou mais dos abates; 105 deles
  tinham menos de 10% no oficial. Exemplos: Holy Avenger (225 mil, Baphomet, 4,8% para 100%),
  Treasure Box (150 mil, Memória de Thanatos 10% para 100%, Savage Dourado 1% para 100%), Gold
  (100 mil, Maya Púrpura 1% para 100%), Full Plate (40 mil, 1% para 50%).
- Todo prêmio de MVP (Old Purple Box, Old Blue Box, diamantes) caía a 100%: 10x sobre chances
  oficiais de 10 a 60%.
- Equipamento de fim de jogo garantido: Kathryne, Memória de Thanatos, Baphomet e Kiel davam 4 a 5
  equipamentos caros por abate.
- Zeny por abate (venda ao NPC, só drops normais): média de 7.262 entre todos os monstros normais;
  Hydrolancer 200 mil, Valquíria 120 mil, Maya Púrpura 101 mil, baú de WoE 81 mil.
- Zeny por limpeza de mapa (spawn oficial): bio3 3,7 M, bio2 2,2 M, Juperos 1,6 a 1,7 M; com o
  x10 de `mobs_x10.txt`, Juperos 2 chegava a 17 M por limpeza e Izlude 2 (mapa de iniciante) a 5,9 M.
  As torres de Thanatos (tha_t07 a t12) davam 30 a 40 mil por abate porque só têm mini-boss.

## Decisões

### Rates globais (`server/conf/import/battle_conf.txt`)

| Categoria | Antes | Agora | Teto novo | Por quê |
|---|---|---|---|---|
| Materiais (common) | 100x | 100x | 50% | Mantém o farm de materiais fácil, mas nada cai garantido; Gold, Treasure Box e diamantes param em 50% |
| Cura | 100x | 100x | 70% | Barato, sem efeito em zeny; teto só para não ser garantido |
| Usável | 100x | 100x | 70% | Idem; Stone of Sage tratado à parte |
| Equipamento | 50x | **30x** | **30%** | 228 equipamentos caíam a 100%; agora nenhum passa de 30%, equipamento continua sendo "sorte" |
| Cartas | 10x (MVP 1x) | igual | sem teto | Decisão da rodada de 13/10 |
| Prêmio de MVP | 10x | **3x** | 50% | Prêmio volta a ser prêmio: 134 dos 153 ficam entre 30 e 50% |
| Baús de WoE | 10x | **5x** | 50% | Baú rendia 81 mil em venda; Oridecon/Elunium continuam a 48 a 50% |

### Itens específicos (`server/db/import/mob_item_ratio.yml`)

| Item | Venda | Ratio | Resultado |
|---|---|---|---|
| Gold | 100 mil | 3x | Besouro-Ladrão Dourado 30%, Savage Dourado 15%, Maya Púrpura 3%, comuns 0,03 a 0,3% |
| Treasure Box | 150 mil | 1x (oficial) | MVPs 50%, Memória de Thanatos 10%, Savage Dourado 1% |
| Valhalla's Flower | 100 mil | 2x | Valquíria Randgris 50% (teto), Valquíria mini-boss 10% |
| Dark Red Scale | 100 mil | 1x | Sombra de Nidhoggr 50% |
| Stone of Sage | 50 mil (usável) | 10x | Gemini-S58 30%, Dama da Sentinela 10%, bio3 5% |

O arquivo entra pelo `cp db/import/*.yml` do `deploy/vps/setup.sh`, sem mudança no deploy. O
`mob_db.yml` do import (gerado por `tools/gen_mob_ptbr.py`) não foi tocado.

### Resultado simulado

| Indicador | Antes | Agora |
|---|---|---|
| Drops a 100% | 2.933 | 0 |
| Equipamentos a 50% ou mais | 326 | 0 |
| Drops de venda >= 10 mil a 50% ou mais | 180 | 62 (só materiais e consumíveis de MVP/mini-boss) |
| Zeny médio por abate (monstros normais) | 7.262 | 3.460 |
| Zeny por limpeza: bio3 / Juperos 2 x10 / Izlude 2 x10 | 3,7 M / 17,2 M / 5,9 M | 2,0 M / 9,5 M / 5,1 M |
| Zeny por abate: Hydrolancer / Valquíria / Maya Púrpura | 200 mil / 120 mil / 102 mil | 110 mil / 58 mil / 51 mil |
| Equipamentos caros por 100 abates de Kathryne | 500 | 150 |

O que **não** mudou e fica anotado: comidas +10 (50 mil, cura) ficam a 70% em MVPs e nos
Hydrolancer/Detardeurus mini-boss de Abyss; as torres de Thanatos continuam o melhor zeny por
abate (mini-boss a 25 a 30 mil); o mob de evento `PORING_V` ("Vem que tem!", 1 por cidade) dropa
armaduras elementais a 30%. Zeny ainda não tem ralo, isso é outra rodada (`docs/balanceamento.md`).

## Plano original de medição (histórico; configurações já revistas)

Na coleta original, `log_conf.txt` desligava o loot de monstros e usava `log_zeny: 100000`.
Desde a rodada 4 estão ativos `enable_logs: 0xFFFFFF7F`, `log_filter: 1` e `log_zeny: 1000`.
As consultas abaixo são exemplos históricos sem os filtros de equipe/bot; para decisões,
aplicar os filtros da revisão atual e usar cronômetro e contador de abates independentes.
Contagens de `picklog` são registros de itens, nunca contagem de monstros mortos.

1. `enable_logs: 0xFFFFFF7F` (liga 0x08) mantendo `log_filter: 4080` e definindo
   `price_items_log: 10000` (hoje 1000, padrão): só entram no `picklog` tipo `M` equipamentos,
   cartas e itens de venda >= 10 mil. Cura, materiais baratos e flechas ficam fora.
2. `log_zeny: 1000` para capturar a venda ao NPC (`zenylog.type = 'S'`).
3. Queries (`ragnarok_log`):

   ```sql
   -- zeny vendido ao NPC por personagem por dia
   SELECT char_id, DATE(time), SUM(amount) FROM zenylog WHERE type='S' GROUP BY 1,2;
   -- itens caros dropados por mapa
   SELECT map, nameid, COUNT(*) FROM picklog WHERE type='M' GROUP BY 1,2 ORDER BY 3 DESC;
   -- MVPs por monstro
   SELECT monster_id, COUNT(*) FROM mvplog GROUP BY 1;
   ```

4. Metas: nenhum personagem acima de 20 M de venda ao NPC por dia nas primeiras semanas; nenhum
   equipamento de venda >= 50 mil aparecendo mais de 3 vezes por dia por mapa. Se estourar, abaixar
   `item_drop_common_max` para 3000 ou pôr os monstros em questão no `List` de um `Ratio` menor no
   `mob_item_ratio.yml`.

## Database do site — corrigida em 19/10/2026

- O builder aplica `mob_item_ratio.yml`, incluindo imports, listas de monstros e remoções
  de uma lista. O multiplicador do item substitui o da categoria antes dos tetos; Ratio 0
  desliga a chance. Prêmios de MVP e a categoria própria dos baús de WoE são considerados.
- `mob_spawns` segue os includes ativos de NPCs, incluindo `mobs_x10.txt`, sem duplicar
  arquivos referenciados mais de uma vez. São spawns estáticos; invocações em tempo de
  execução por scripts de eventos não são estimadas como população fixa.
- `setup-web.sh` usa `build_gamedb.py <raiz-rathena> --fingerprint`: o hash inclui os YAML
  importados, configurações de drops, includes e arquivos de spawn, além do builder.
- Publicação conferida: 335 chances corrigidas (overrides por item e baús), 5.019 drops e
  1.912 pares monstro/mapa. Os serviços do jogo e do site mantiveram os mesmos PIDs.
  Backup das cinco tabelas derivadas e fontes em
  `/var/backups/faithro-web/gamedb-20261019T041320Z`.

## Apêndice: como reproduzir

Dump (somente leitura, na VPS):

```sql
SELECT d.mob_id, m.aegis, m.name, m.level, m.hp, m.is_mvp, m.class, m.base_exp, d.idx, d.item_id,
       i.aegis, i.name, i.type, i.sell, i.slots, d.rate, d.rate_final, d.mvp
FROM mob_drops d JOIN items i ON i.id=d.item_id JOIN mobs m ON m.id=d.mob_id;
SELECT mob_id, map, amount FROM mob_spawns;
```

O cálculo atual reaplica `mob_drop_ratio_adjust` (multiplicador por categoria, `Ratio`,
tetos) sobre a chance oficial, soma `chance x venda` por monstro e pondera pelo spawn de cada
mapa. Baús usam `RaceGroups.Treasure`, conforme o código instalado; identificar somente pelo
nome `TREASURE_BOX*` era uma simplificação do estudo original.
