# Balanceamento do FaithRO

Documento de referência das decisões de equilíbrio (2026-10-18). Pre-renewal, 300x de EXP,
nível 255, atributo 185, sem 3ª classe. Dados usados: database do site (1.004 monstros,
5.019 drops, 1.907 spawns) e a tabela de EXP gerada por `tools/gen_progression.py`.

## Metas

| Faixa | Meta de tempo | EXP necessária | Referência de farm |
|---|---|---|---|
| 1 → 99 | ~1 h | 1,2 bilhão (tabela oficial × 300) | qualquer mapa da faixa; ~1 abate por nível |
| 99 → 150 | ~10 h | 8,7 bilhões | monstros de 3 M de EXP por abate (ex.: Anubis, Sleeper, Juperos) |
| 150 → 200 | ~10 h | 31 bilhões | 10 M por abate (ex.: Skogul, Abbey, Thanatos) |
| 200 → 255 | ~23 h | 205 bilhões | 30 M por abate (bio3, Thor, Morroc) |

Total ≈ 44 h solo a 300 abates/hora. Party e mapas lotados encurtam, mas o 255 continua
sendo meta de 2 a 3 semanas para quem joga 2 a 3 horas por dia.

## Curva de EXP pós-99

- Gerada por `tools/gen_progression.py` (parâmetros `TIERS` e `POST99_START`).
- 99→100 custa 100 M (0,3× os 343 M oficiais do 98→99: o reborn já cobrou esse preço).
- Crescimento por nível: 2% até 149, 3% até 199, 3,5% até 254.
- Muralhas: 150 (×1,5), 200 (×1,5), 254 (×2). O 254→255 custa 15,7 bilhões.
- Antes desta rodada, 99→255 custava 1,0 trilhão (86% entre 200 e 255), cerca de 160 h.

## Densidade de monstros

`tools/gen_mob_boost.py` gera `npc/custom/faithro/mobs_x10.txt` no deploy. Critério: 3 mapas
por faixa de nível, sem mini-boss nem MVP no mapa (para não multiplicar cartas raras), e fora
dos melhores mapas de EXP do jogo, que ficam com o spawn oficial.

| Faixa | Mapas | Fator |
|---|---|---|
| 1–30 | prt_sewb2, prt_sewb3, iz_dun02 | ×10 |
| 31–60 | hu_fild04, hu_fild07, alde_dun03 | ×10 |
| 61–90 | juperos_01, juperos_02, abbey01 | ×10 |
| 91+ | man_fild02, spl_fild01 | ×5 (mapas pequenos) |

Ficam oficiais de propósito: `lhz_dun03` (bio3), `moc_fild21/22` (Morroc), `thor_v01..03`.
Com ×10 em bio3, uma limpeza rendia 92 bilhões de EXP e 37 milhões de zeny, e concentrava
3.120 monstros agressivos num mapa, em um servidor de 1 vCPU.

## Cartas

- Só por drop. Comum e mini-boss: 10x (0,01% → 0,1%, ~1.000 abates por carta). MVP: 1x.
- A loja de cartas por 1 milhão foi removida: vendia 406 cartas, 41 delas de mini-boss
  (Ghostring, Angeling, Maya Purple, Hydrolancer...), e 1 milhão eram 25 abates nos
  melhores mapas.

## Combate

- Nenhum monstro normal passa de 16 mil de ataque; um Sniper 255 tem 105 mil de HP.
  O risco real vem dos MVPs (até 49 mil por golpe).
- No 255 uma classe trans tem 7.237 pontos de status, o que maximiza 3,6 atributos em 185.
  Dá variação de build sem fechar tudo.
- HP, ASPD (197) e atributos não mudaram nesta rodada.

## Riscos deixados para depois

- **Zeny vindo de drops.** Tratado em `docs/drops.md` (tetos por categoria, equipamento 30x,
  prêmio de MVP 3x, baús 5x e `db/import/mob_item_ratio.yml` para Gold, Treasure Box etc.).
  Continua faltando ralo: refino, Kafra e NPCs de apostas são os únicos. Candidatos: warper pago,
  taxa de MVP room, loja de consumíveis premium por zeny.
- **Healer com buff grátis** (Agi/Bless, 3 s de espera) torna o Priest de suporte opcional
  fora de MVP e WoE. Opção: buff só até o nível 150.
- **MVP room** permite invocar MVPs por zeny: drops de MVP a 10x sem risco de disputa.
- **Pouco conteúdo acima do 100.** Só 7 monstros normais passam do nível 100. A progressão
  200→255 repete os mesmos mapas; conteúdo novo (instâncias, mapas custom) é a saída real.

## Como medir

Depois de uma semana com jogadores: `picklog`/`mvplog` em `ragnarok_log` dão abates por
hora reais por mapa; comparar com a tabela de metas. Se 99→150 ficar abaixo de 5 h ou acima
de 20 h, ajustar `POST99_START`; se uma faixa específica fugir, ajustar o fator dela em
`TIERS`. Mapas lotados demais ou vazios: ajustar `BOOST` em `gen_mob_boost.py`.
Estudo complementar da rodada 2: [estudo-balanceamento.md](estudo-balanceamento.md).
