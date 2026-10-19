# Balanceamento do FaithRO

Documento de referência das decisões de equilíbrio, iniciado em 18/10/2026 e revisto em
19/10/2026. Pre-renewal, 300x de EXP, nível 255, atributo 185, ASPD 197, sem 3ª classe.
Snapshot atual: 1.004 monstros, 5.019 drops e 1.912 pares de spawn. As primeiras seções
registram metas e estudos históricos; a revisão de 19/10 abaixo contém os cálculos atuais.

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

## Rodada 2: atalhos dos NPCs custom (18/10/2026, em produção)

Base: itens 1–8 de [estudo-balanceamento.md](estudo-balanceamento.md). Validado com
`map-server --run-once` numa cópia do servidor: 0 erros, 0 avisos, 13.502 NPCs (eram 13.556).

| Atalho | Mudança | Arquivo |
|---|---|---|
| Arena de MVP grátis (209 MVPs) e sala de MVP paga (46 MVPs a 100 k) | desligadas | `server/npc/custom/faithro/optional.conf` |
| Carta de MVP pela quest do Belzebu | quest desligada | idem |
| Cartas e Mjolnir na loja de fichas do THQS | retirados do menu; tarefas, fichas e troca por zeny ficam | `ptbr/custom/quests/thq/THQS_TTShop.txt` |
| Bolsa de valores, roleta e blackjack | desligados | `optional.conf` |
| Juros do banco Kafra (até 100 k/dia por conta) | rendimento zero; depósitos e saques continuam | `ptbr/custom/etc/bank_kafra.txt` |
| Buff grátis do healer (Agi/Bless 10) | só até o nível de base 99; a cura continua para todos | `ptbr/custom/healer.txt` (`.@BuffMaxLevel`) |
| Warper grátis | cidades sempre grátis; outros destinos grátis até o 99, 25 k do 100 ao 199 e 50 k no 200+ (também no "Último Teleporte") | `ptbr/custom/warper.txt` (`function Fee`; desde a rodada 3 os valores ficam em `F_FaithRO_WarpFee`) |
| Loja vendendo armas de MVP/chefe | saíram as 42 armas de nível 4 e o Kaho (5013) | `ptbr/custom/itemmall.txt` |

Ficaram de fora desta rodada (próximas): quests de Kaho/Balmung e Valhallen (itens divinos),
Valkyrie Helm/Helm of Sun e outros chapéus raros no itemmall, preço da Poison Bottle (5 k),
cobrança e devolução da `quest_warper` (o estudo achou devolução com índice errado), avião
grátis e permissões de `@warp`. Enquanto esses caminhos existirem, a taxa do warper não é um
ralo garantido.

## Rodada 3: itens divinos, chapéus raros e transportes (18/10/2026, em produção desde 18/10 20:34)

Fecha os atalhos deixados de fora da rodada 2. Valores e política aprovados pelo dono.
Validado com `map-server --run-once` numa cópia do servidor: 0 erros, 0 avisos, 13.499 NPCs (eram 13.502 na rodada 2; saíram
os três NPCs desligados).

**Política de itens divinos e de GM.** Itens divinos (Mjolnir, Sleipnir, Brisingamen,
Megingjard) só pelas quests oficiais dos selos (`npc/quests/seals/`, já carregadas). Kaho
(5013) e Balmung (1161) são itens de GM e não entram no jogo por NPC.

| Atalho | Mudança | Arquivo |
|---|---|---|
| Valhallen (Lenneth, Prontera): itens divinos com materiais de Baú do Tesouro, sem os selos; também Asprika e Brynhild (de era posterior) e quatro receitas com itens que nem existem no pre-re (Hervor, Jormungand, Muspellium, Essência da Runa) | desligada | `server/npc/custom/faithro/optional.conf` |
| Mensageiro Real: Balmung ou Kaho por 1 M e itens comuns | desligado | idem (`kaho_balmung.txt`) |
| Servo do Lorde Kaho: Kaho por 3 Emperium, 10 drops de MVP, bonecos e 5 M | desligado | idem (`kahohorn.txt`) |
| Chapéus de drop de MVP/chefe/baú no itemmall | saíram Gemmed Sallet 2231, Tiara 2234, Crown 2235, Golden Gear 2246, Majestic Goat 2256, Spiky Band 2258 e 5161, Elven Ears 2286, Binoculars 2296, Dark Blinder 5104 e Hat of the Sun God 5022 | `ptbr/custom/itemmall.txt` |
| Chapéus sem drop com bônus de topo no itemmall | saíram Valkyrie Helm 5171 (1,25 M), Dark Randgris Helm 5373, Gigantic Majestic Goat 5374, Helm of Darkness 5181, Emperor's Laurel Crown 5205, Soul Wing 5297, Champion Wreath 5320, Misstrance Crown 5323 e Red Tailed Ribbon 5801; os chapéus cosméticos e os de bônus pequeno ficam | idem |
| Poison Bottle 678 a 5 k (EDP barato) | 50 k | idem (Street Dealer) |
| Warpra (`quest_warper`) devolvia a taxa depois do warp; na rota de calabouço devolvia pelo índice do menu de cidades | devoluções retiradas; cobra o preço do menu de GM (hoje zero) mais a mesma taxa por faixa do warper principal: cidades grátis, outros destinos grátis até o 99, 25 k do 100 ao 199 e 50 k no 200+ | `ptbr/custom/etc/quest_warper.txt` |
| Balmung (1161) na loja de fichas do THQS por 2.000 fichas | retirado do menu de espadas de duas mãos (mesma política do Kaho) | `ptbr/custom/quests/thq/THQS_TTShop.txt` |
| Taxa por faixa duplicada entre os dois warpers | valores passaram para a função global `F_FaithRO_WarpFee`, no topo de `warper.txt`; a `function Fee` do warper chama essa função | `ptbr/custom/warper.txt` |

Notas:

- Na VPS a Warpra está com o warp para calabouços desligado (`$QW_DW_OFF=1` em `mapreg`) e
  com todos os preços do menu de GM zerados. O teleporte para cidades continua grátis, como
  no warper principal. A taxa vale para os calabouços se um GM religar o menu (ou num banco
  novo, em que `$QW_DW_OFF` começa em 0).
- `quest_warper.txt` depende de `warper.txt` (carregado por `scripts_faithro.conf`) por causa
  de `F_FaithRO_WarpFee`.
- Dois desses chapéus continuam saindo por receita, sem zeny: Hat of the Sun God 5022 em
  `ptbr/custom/quests/quest_shop.txt` (Emblem of the Sun God 7086 e materiais comuns) e Elven
  Ears 2286 em `quests/elvenear.txt`. Ficam: consomem itens, não emitem zeny.
- A loja "Chapéus 01" tinha uma entrada malformada (`2247:30000:5206:10000`); corrigida para
  `2247:30000,5206:10000`, e o 5206 (chapéu comum) passa a ser vendido por 10 k.
- Avião (`etc/airplane.txt`) fica grátis: 12 paradas sorteadas por hora, atracando a cada 5 min;
  é ambientação, não atalho.
- `@warp`/`@go` não são problema: na VPS vale o `conf/groups.yml` padrão (o `import` está vazio);
  o grupo 0 só tem `changedress` e `resurrect`, `@go` é do grupo 1 e `@warp` é de GM.

Nada ficou de fora desta rodada.

## Rodada 4: preparar para medir (18/10/2026, em produção desde 18/10 20:54; anunciada em faithro.site/noticias e no motd)

Sem mexer em combate ou curva: liga a coleta que a seção "Como medir" pede, conserta as
missões de caça (quebradas em produção) e limita o autopot. Validado com `map-server --run-once`
numa cópia do servidor: 0 erros, 0 avisos, 13.499 NPCs.

| O quê | Mudança | Arquivo |
|---|---|---|
| Logs não capturavam drops (bit 0x08 desligado) nem zeny abaixo de 100 k, então a seção "Como medir" não tinha dados | `enable_logs: 0xFFFFFF7F` (loot de monstro ligado; consumo 0x80 continua fora), `log_filter: 1` (todos os itens), `log_zeny: 1000` | `server/conf/import/log_conf.txt` |
| Missões de caça quebradas: o NPC consultava a tabela SQL `mob_db`, que não existe no banco `ragnarok` (erro 1146); ninguém conseguia pegar missão | os alvos saem de uma lista fixa `.Pool` com 348 mobs, sorteados sem repetição; a consulta SQL e `.mob_db$` saíram. O resto (progresso, ranking, loja de pontos) continua em `char_reg_num` | `ptbr/custom/quests/hunting_missions.txt` |
| Autopot com atraso mínimo de 100 ms (10 checagens/s por jogador) | mínimo 250 ms; valores menores informados pelo jogador são elevados a 250 | `ptbr/custom/etc/autopot.txt` (`.MinDelay`) |

Como a lista `.Pool` foi gerada (MariaDB `faithro_web` da VPS, mesmo critério da consulta
original: mobs normais com ID < 2000, com EXP, com carta entre os drops, fora da lista negra do
script):

```sql
SELECT GROUP_CONCAT(m.id ORDER BY m.id) FROM mobs m
WHERE m.id < 2000 AND m.aegis NOT LIKE 'meta%' AND m.aegis NOT LIKE 'E\_%'
  AND m.base_exp > 0 AND m.job_exp > 0 AND m.is_mvp = 0 AND m.class <> 'Boss'
  AND EXISTS (SELECT 1 FROM mob_drops d JOIN items i ON i.id = d.item_id
              WHERE d.mob_id = m.id AND d.mvp = 0 AND i.type = 'Card')
  AND m.id NOT IN (<lista negra do OnInit>);
```

Regerar só se o `mob_db` mudar de forma relevante (novos mobs normais com carta).

Guardas para os logs: se a CPU do map-server passar de 80% ou o `picklog` crescer além do
razoável para o disco (37 GB livres em 18/10), voltar a `0xFFFFFF77` e `log_filter: 4080`. Com o
servidor quase vazio o custo é desprezível; reavaliar quando houver dezenas de jogadores.

Recompensa das missões de caça: `.Modifier` usa `base_exp_rate/100` e `job_exp_rate/100` (com
`base_exp_rate: 30000`, isso é 300x o valor base da fórmula) e zeny ×60; o estudo estimou ~4,6 M/dia/conta
com duas conclusões por dia (cooldown 12 h). Fica como está nesta rodada e entra na medição.

## Rodada 5: retirada de NPCs (19/10/2026, em produção)

- **Escada de MVPs suspensa:** include de `events/mvp_ladder.txt` comentado em
  `server/npc/custom/faithro/optional.conf`. O evento oferecia 39 chefes por entrada,
  sem cooldown e com drops. Script e recordes existentes foram preservados.
- **Time Azul e Time Vermelho retirados de Prontera:** includes de
  `battleground/bg_emp.txt` e `battleground/bg_pvp.txt` comentados. Saíram os quatro
  NPCs visíveis (dois pares) e seus dois controladores; ninguém estava nas arenas.
- **Tine retirado de Prontera:** seu diálogo e posição foram substituídos pelo
  controlador invisível `FaithRO_ValentineBonus` em `events/holiday/valentinesdayexp.txt`.
  Os quatro `setitemscript` e os outros três NPCs do arquivo ficaram iguais.

As duas aplicações reiniciaram somente `rathena-map`; login, char, web do jogo e site
mantiveram os mesmos PIDs. Conferência de inicialização: 13.492 NPCs, zero erros e
zero avisos. Backups das fontes instaladas e do pacote de deploy:
`/var/backups/faithro/npc-suspension-20261019T041945Z.tar.gz` e
`/var/backups/faithro/tine-removal-20261019T042112Z.tar.gz`.

## Rodada 6: recompensa em zeny da caça (19/10/2026, em produção)

O terceiro valor de `.Modifier` em `ptbr/custom/quests/hunting_missions.txt` passou
de 60 para 6: pagamentos em zeny reduzidos em 90%. EXP, pontos, progresso, loja,
348 alvos possíveis, quantidade de abates e cooldown de 12 horas permaneceram iguais.
Missões em andamento usam o novo valor no próximo resgate; nenhum contador foi zerado.

Com a lista atual, a média calculada passa de aproximadamente 2,35 milhões para
235 mil zeny por missão; duas conclusões equivalem a cerca de 470 mil. São estimativas
do sorteio, não renda observada nem promessa de duas conclusões diárias: o cooldown
começa depois de concluir e o tempo de caça também conta.

As cópias local, instalada em Windows-1252 e do pacote de deploy foram conferidas;
a única mudança no script foi a constante e seu comentário. Aplicação sem personagens
online, reiniciando somente `rathena-map`: 13.492 NPCs, zero erros e zero avisos.
Backup: `/var/backups/faithro/hunting-reward-20261019T042314Z.tar.gz`.

## Rodada 7: venda de pontos da Arena de Monstros (19/10/2026, em produção)

A conversão de experiência do monstro em zeny foi suspensa em
`ptbr/custom/etc/monster_arena.txt`: saíram a opção "Vender Experiência" e o bloco
`L_Sell`, que debitava pontos e creditava 100 zeny por ponto. O treinador informa
que a troca está suspensa. Entrada, lutas, cura, evolução e pontos acumulados foram
preservados, incluindo os 22 trechos que concedem pontos por abates.

Conferência das fontes: somente o menu e o bloco de venda mudaram. Publicação sem
personagens online, reiniciando apenas `rathena-map`: 13.492 NPCs, zero erros e
zero avisos. Backup: `/var/backups/faithro/arena-zeny-20261019T042438Z.tar.gz`.

## Rodada 8: trava de bilhete da Loteria (19/10/2026, em produção)

A condição de segunda compra em `ptbr/custom/etc/lottery.txt` passou a consultar
`#LW1`, preenchido na confirmação do bilhete, em vez de `#L1`, que não era preenchido.
O bloqueio é verificado antes de debitar zeny. Preço, prêmios e resgate ficaram iguais.

Conferência lógica: primeira compra permitida, bilhete confirmado bloqueia outra
compra no mesmo sorteio e o próximo sorteio permite nova compra. As fontes diferem
somente pelo nome da variável; não foram comprados bilhetes nem pagos prêmios nos testes.
IDs e números do sorteio em `mapreg` ficaram iguais antes e depois da aplicação.
Somente `rathena-map` reiniciado, sem personagens online: 13.492 NPCs, zero erros e
zero avisos. Backup: `/var/backups/faithro/lottery-ticket-20261019T042557Z.tar.gz`.

## Itens iniciais (19/10/2026, em produção)

Novos personagens recebem 100 Poções Vermelhas (item 501) diretamente na criação,
além da faca e da camisa originais. Configuração em `conf/import/char_conf.txt`:
`start_items_pre: 1201,1,2:2301,1,16:501,100,0`. O último zero mantém as poções
no inventário. Personagens já existentes não recebem itens por essa configuração.

O parser e a rotina de criação foram conferidos no código instalado do rAthena
pré-Renewal. As cópias local, instalada e do pacote de deploy foram sincronizadas.
A aplicação final ocorreu sem jogadores comuns online, reiniciando somente
`rathena-char`; inicialização e reconexão do mapa confirmadas, sem erros no serviço.
Não foi criado personagem de teste. Evidência em
`design-audit/starting-items/verification.json` e backup em
`/var/backups/faithro/starting-red-potions-20261019T043439Z.tar.gz`.

## Revisão de 19/10/2026: cinco frentes concluídas em leitura

Coleta em `design-audit/balance-review-20261019/snapshot.json`; coletor reproduzível em
`collect.py` no mesmo diretório. Execução remota com `python3 -B -`: somente arquivos e SELECT,
sem chamar `builder.main`, sem personagens de teste, reinícios ou combates. A coleta não
pretende comprovar o comportamento de menus por interação; essa validação exige ensaio.

**1. Estado publicado e site.** Os 13 arquivos críticos conferidos coincidem com o overlay
local após normalizar encoding e quebras de linha. Escada e times fora dos includes ativos;
Tine como controlador invisível; caça com fator 6; venda da Arena ausente; trava da Loteria
em `#LW1`; 100 Red Potions nos itens iniciais. Zero diferenças na comparação integral dos
5.019 drops e dos 1.912 pares estáticos de spawn com as tabelas do site.

Conferência aritmética de overrides: Gold de Maya Purple = 1% × 3 = 3%; GTB = 10% × 3 = 30%;
Stone of Sage de Gemini = 3% × 10 = 30%; Treasure Box de Thanatos = 10% × 1 = 10%.
Essas são chances-base, antes de bônus individuais do jogador. Drops dinâmicos de eventos
não são convertidos em spawn fixo. A comparação com o site usa o mesmo builder; os exemplos
aritméticos e a regra de override/tetos foram conferidos também em `src/map/mob.cpp:4832,6775`.

**2. Economia.** Existe uma conta comum com um personagem nível 16. O recorte encontrou zero
registros de zeny, zero vitórias de MVP e três registros de itens tipo P; isso não demonstra
renda, abates nem tempo de jogo. Equipe, bot de grupo 1, conta de serviço e operações A foram
excluídos. Não há evidência de inflação observada.

Revenda de drops e pagamentos de quests criam zeny; comércio entre jogadores e depósitos/
saques transferem saldo; compra ao NPC, refino e transportes pagos retiram moeda. Entrada de
item no inventário não é emissão de zeny até a venda. As 100 Red Potions iniciais valem 2.500
zeny em revenda-base, ou 3.100 com Overcharge 10: emissão potencial por personagem, não por
hora. Não foi inferida exploração por recriação de personagem.

O itemmall tem 372 entradas válidas verificadas e nenhuma arbitragem positiva no cenário
Discount 24% / Overcharge 24%; a conclusão se restringe a essa loja. Poison Bottle custa
50.000 na loja custom (38.000 com desconto), apesar de seu Buy genérico no YAML ser 5.000.
EDP exige uma por ativação. O par Acid Bottle + Bottle Grenade custa 1.000 na loja (760 com
desconto) por Acid Demonstration. Blue Gemstone custa 600; a flecha comum custa 10 no itemmall,
embora o Buy genérico seja 1. Preço genérico do item não substitui preço de loja custom.

Refino normal no YAML pre-re: taxa por tentativa de arma nível 1/2/3/4 = 50/200/5.000/20.000;
armadura = 2.000. Somar materiais e perdas por falha; não chamar apenas a taxa de custo total.
Não foram avaliadas como rotas ativas as tabelas de equipamentos Shadow ou armas nível 5.
Warper: cidade e personagem até 99 grátis; 100–199 paga 25.000, 200+ paga 50.000 por destino
não urbano. O menu de dungeons da Warpra permanece desligado no mapreg (`$QW_DW_OFF=1`).

**3. Mapas.** Cada célula traz os cenários de **150 / 300 / 600 abates por hora**, nesta ordem.
EXP em bilhões; zeny em milhões, venda-base bruta ao NPC, sem Overcharge. A média é ponderada
pela população estática sem MVP; mini-bosses permanecem no mix. É um cenário de composição,
sem garantia de que esse mix, respawn ou ritmo seja sustentável — especialmente em Thanatos.

| Mapa | Spawn sem MVP: original/ativo | EXP G/h: 150/300/600 | Zeny bruto M/h: 150/300/600 |
|---|---|---|---|
| juperos_01 | 285/2850 | 0.195/0.391/0.782 | 0.470/0.940/1.879 |
| juperos_02 | 315/3150 | 0.210/0.420/0.840 | 0.451/0.902/1.804 |
| abbey01 | 258/2580 | 0.427/0.853/1.706 | 0.113/0.226/0.452 |
| abbey03 | 116/116 | 1.274/2.549/5.097 | 0.087/0.175/0.350 |
| lhz_dun03 | 312/312 | 4.429/8.858/17.716 | 0.943/1.886/3.772 |
| thor_v01 | 96/96 | 1.997/3.995/7.989 | 0.324/0.647/1.294 |
| thor_v03 | 125/125 | 3.034/6.067/12.134 | 0.376/0.753/1.505 |
| tha_t09 | 44/44 | 1.012/2.024/4.047 | 1.895/3.790/7.579 |
| man_fild02 | 110/550 | 0.921/1.842/3.684 | 0.063/0.125/0.250 |

A densidade aumenta disponibilidade, não valor por abate nem abates/h automaticamente.
Coleta seletiva, peso, concorrência, deslocamento, mortes, invocações e bônus de grupo não
estão modelados. Overcharge 10 eleva aproximadamente 24% apenas a revenda, com arredondamento
por unidade; o snapshot também traz essa coluna.

Exemplo de sensibilidade, não consumo medido: comprar 100 White Potions ao Buy genérico de
1.200, usar 1.000 flechas da loja e pagar um warp custa 155.000 no nível 150 ou 180.000 no
200+. Não inclui SP, refino ou morte; validar preço no vendedor usado no ensaio. Em Juperos 2
a 300 abates/h, 902 mil brutos menos 180 mil dão cerca de 722 mil. Vinte ativações de EDP
acrescentam 1 milhão sem desconto: esse mesmo cenário fica negativo. Não cobrar simultaneamente
flechas e EDP como se fossem consumidos pela mesma build; o exemplo de EDP substitui a parcela
de munição (custo 1,17 M, saldo aproximadamente -268 mil). Consumíveis dropados e revendidos
não podem ser contados também como usados: ajustar o inventário final no ensaio.

**4. Classes.** Orçamento total trans conferido: 99 = 1.325; 150 = 2.722; 200 = 4.597;
255 = 7.237. Custo de 1 a 185 = 1.970, pelo ramo pre-re de `pc.cpp:8803`. Foram calculadas
104 alocações de exemplo: 13 classes × 4 níveis × PvM/MVP, todas dentro do orçamento. As
formas montadas compartilham a análise da classe original. Não são builds ótimas ou DPS real;
prioridades, pontos gastos e restantes estão no snapshot. Job 70 é premissa de ensaio,
não condição de todo personagem natural ao chegar ao 99.

HP abaixo considera os atributos das builds PvM do snapshot e bônus de job 70, sem equipamento,
passivas ou buffs. Consulta `BaseHp` quando disponível e usa fallback instalado nos demais
níveis (`pc.cpp:13710,14290`); VIT e fator trans em `status.cpp:3509`. Logo a comparação
não isola apenas o efeito do nível: as alocações também mudam.

| Classe | HP99 | HP150 | HP200 | HP255 | ASPD255, só atributos/job/arma |
|---|---|---|---|---|---|
| Lord_Knight | 16853 | 44742 | 90185 | 168612 | 195.6 |
| Paladin | 15133 | 40138 | 80083 | 139147 | 185.6 |
| Sniper | 9714 | 25516 | 51200 | 95534 | 197.0 |
| Assassin_Cross | 12256 | 32460 | 65410 | 122377 | 197.0 |
| High_Wizard | 6752 | 17367 | 34467 | 63825 | 171.6 |
| High_Priest | 9837 | 25218 | 51628 | 94246 | 171.2 |
| Champion | 9118 | 24379 | 49313 | 95962 | 177.4 |
| Professor | 8773 | 22893 | 45780 | 85209 | 175.3 |
| Creator | 11287 | 29244 | 60272 | 110516 | 167.4 |
| Whitesmith | 10414 | 27322 | 54771 | 102074 | 194.8 |
| Stalker | 9774 | 25646 | 51426 | 95898 | 197.0 |
| Clown | 8264 | 21930 | 44251 | 82893 | 188.9 |
| Gypsy | 8264 | 21930 | 44251 | 82893 | 189.4 |

ASPD usa só a categoria de arma indicada no snapshot, sem bônus do equipamento, passivas,
escudo ou buffs. Sniper, SinX e Stalker chegam a 197 nessas alocações; não é verdade que toda
classe/build chega sem investir. O teto de ataques básicos passa de 16,67/s em 197 para
7,14/s em 193: redução de 57,1%, não proporcional a quatro pontos. Aftercast, cooldown,
SP e mecânicas impedem extrapolar essa proporção para habilidades. Storm Gust tem aftercast
base de 5 s, Sharpshooting 1,5 s, Asura 5 tem 1 s; são valores antes de modificadores.

Papéis para comparar em ensaio: LK e Paladin, sobrevivência/mobbing/proteção; Sniper e SinX,
dano sustentado e custo de munição/EDP; HW, área e controle com dependência de elemento;
HP e Professor, sustentação/Assumptio/SP; Champion e Creator, dano concentrado com reposição
de SP/frascos; WS, dano de curta distância e custos; Stalker, versatilidade e limitações de
cópia; Clown/Gypsy, buffs e ganho do grupo. Medir contribuição do suporte por produção total
do grupo e mortes evitadas, sem exigir paridade no farm solo. Nenhuma ordem de DPS foi provada.

Equipamento mínimo reproduzível: Jacket 2304, Muffler 2504, Shoes 2404, sem cartas, +0;
compráveis por 30 mil no total antes de desconto. Armas no snapshot, todas na loja ativa:
LK Two-Handed Sword 1158; Paladin Pike 1408; Sniper/Stalker Great Bow 1708; SinX Katar 1253;
HW/HP Staff 1608; Champion Knuckle Dusters 1804; Professor Book 1550; Creator War Axe 1306;
WS Hammer 1355; Clown Mandolin 1904; Gypsy Whip 1953. Nomes são de referência:
confirmar restrições de classe e nível no cliente antes de começar. Os modelos de HP/ASPD
não incluem os bônus desses itens; no ensaio registrar o painel final. Não usar Kaho, itens
de GM, divinos ou cartas de MVP como equipamento inicial presumido.

**5. Proposta e roteiro.** Não há novo ajuste numérico justificado pela amostra atual.

| Item | Atual → candidato | Efeito esperado / risco | Confiança e critério |
|---|---|---|---|
| Rates/atributos/nível | 300x / 185 / 255 → conservar | Mantém referência de comparação; pode preservar desequilíbrios ainda não medidos | Alta para não alterar sem amostra; revisar com sessões comparáveis |
| ASPD | 197 → 193 somente como hipótese em laboratório | Reduz teto de ataques básicos em 57,1%; alto risco para classes físicas | Alta na conta, baixa no ganho de equilíbrio. Só propor adoção se eliminar vantagem repetida sem inviabilizar custos/função; descartar se apenas piorar físicos enquanto skills dominam |
| Habilidades | valores atuais → sem novo multiplicador | Preserva PvM/MVP; risco desconhecido em PvP/WoE | Baixa para qualquer nerf. Medir TTK, mortes e contramedidas com equipamento igual; não adotar -50% por cálculo isolado |
| Densidade | Juperos/Abbey ×10, Manuk ×5 → conservar | Mantém oferta; risco de concentração e carga | Baixa para alterar. Só propor redução se CPU/latência ou domínio de eficiência se repetirem com o mesmo painel; descartar se causar espera sem resolver o problema |
| Coleta e documentação | deduções por logs → sessões cronometradas e fontes atuais | Permite distinguir custos, abates e horas; exige execução controlada | Alta; abandonar comparação quando build, rota ou inventário não forem reproduzíveis |

Primeira bateria em ambiente de teste: Sniper, SinX e HW nos níveis 99/150/200/255 com as
alocações e equipamentos acima. Uma rota fixa por comparação, 30 minutos corridos, três
repetições, mesmas regras de buffs e coleta. Cobrir Juperos, Abbey, Bio3, Thor, Thanatos e
Manuk; se uma build não sobreviver, registrar a falha em vez de inventar rendimento. Usar
DS/Sharpshooting, ataques/Sonic Blow com e sem EDP e Storm Gust, respectivamente; registrar
níveis e demais habilidades antes da sessão. Contar abates por instrumento validado,
EXP e zeny antes/depois, item por item usado/coletado/vendido, mortes, viagens, peso,
tempo de recuperação, CPU e latência. Apurar saldo líquido sem duplicar itens consumidos.

MVP: GTB e Baphomet como controles iniciais, Randgris e Ifrit como desafios finais. HP de
referência 126.000 / 668.000 / 3.567.200 / 7.700.000. Três tentativas solo e três em dupla com
HP ou Professor, cronômetro desde o primeiro ataque até vitória ou morte, limite de 10 min
por tentativa; declarar falha/timeout e registrar dano, mecânicas, recursos, suporte e
invocações. Não transformar HP dividido por DPS hipotético em resultado de combate.
Depois ampliar às demais classes; PvP/WoE como painel complementar separado, sem aplicar
nerfs globais por resultados desse painel. Esta rodada não executou nenhuma dessas lutas.

## Rodada seguinte: pacote de medição preparado (19/10/2026)

Cinco entregas adicionais, sem mudança no servidor: compatibilidade de equipamentos,
habilidades com pré-requisitos, preços por vendedor, apurador de sessões e fichas de ensaio.
Fontes e plano em `design-audit/balance-session-kit/installed-data.json` e `plan.json`.

- **Equipamentos:** 416 verificações de quatro peças nas 104 combinações anteriores,
  considerando família da classe, sexo, nível e restrições. Todos compatíveis. Armas com
  bônus: Katar 1253 dá DEX +1; Staff 1608 dá INT +2 e MATK +15%; War Axe 1306 dá DEX/LUK +2.
  Esses bônus não estavam incluídos nos modelos sem equipamento e devem aparecer no painel
  real. As fichas também registram slots vazios, cartas e refino.
- **Habilidades piloto:** pré-requisitos expandidos da árvore instalada para Sniper,
  SinX e HW. Gastos de primeira/segunda classe: 40/27, 38/39 e 33/44, respectivamente,
  dentro de 49/69 com primeira classe job 50 e trans job 70; cada uma inclui Basic Skill 9
  no orçamento separado de Aprendiz. A lista completa está nas fichas.
- **Vendedores:** 1.758 entradas literais de lojas normais do grafo pre-re ativo, sem
  include ausente; nenhuma arbitragem positiva encontrada com desconto/sobrepreço de 24%.
  O recorte não cobre lojas programadas por script, barter ou cash shop. Flecha comum
  custa 1 nos vendedores oficiais e 10 no itemmall: usar no ensaio o preço do vendedor
  efetivamente visitado. White Potion = 1.200; Fly Wing = 60; Blue Potion = 5.000;
  Blue/Yellow Gemstone = 600; Poison Bottle = 50.000; frascos de AD = 500 cada, antes de
  descontos. Não houve alteração de preços.
- **Apuração:** `tools/analyze_balance_session.py` lê somente um JSON local, sem acesso
  a rede, jogo ou banco. Exige sessão explicitamente cronometrada, calibração do contador
  com pelo menos dez abates conhecidos, orçamento de atributos válido e reconciliação de
  zeny e consumíveis. Transferências não viram renda de farm; consumo é informado separado
  do saldo de caixa para não descontar compras duas vezes. EXP desconhecida fica desconhecida;
  uma diferença de EXP parcial que atravessa níveis não é aceita como ganho total.
  Vitórias de MVP exigem distinguir alvo e invocações. Dados sintéticos e testadores ficam
  fora de métricas de jogadores. O programa valida consistência declarada, não autentica
  observações no servidor nem substitui a execução dos ensaios.
- **Fichas:** 12 modelos de farm (três classes × quatro níveis), quatro modelos de MVP
  com níveis/alvos definidos e estado inicial `pending`. Não geram desempenho enquanto
  não forem preenchidos. Copiar antes de preencher: o preparador recusa sobrescrever
  arquivos existentes. Registrar painel real, buffs, todos os movimentos de zeny e todos
  os consumíveis; usar zero apenas quando a ausência do movimento tiver sido conferida.

Para apurar uma cópia preenchida, a partir da raiz do projeto:

```powershell
python tools/analyze_balance_session.py caminho/da/sessao-preenchida.json
```

O arquivo sai em JSON no terminal; entrada pendente ou inconsistente retorna código 2 e
não imprime métricas. Não editar `status` para observado sem executar a sessão real.
Usar a curva de EXP para ganho total quando houver subida de nível. Excluir operações
administrativas dentro da janela; preparação de personagens de QA ocorre antes da janela
e apenas no ambiente isolado. Manter estoque, compras e coleta reconciliados: um mesmo
item não pode aparecer simultaneamente como vendido, consumido e remanescente.

Próximo marco de execução: piloto de 90 minutos, com Sniper/SinX/HW 99, 30 minutos cada em
Juperos 2. Validar registros antes de ampliar. O painel completo de farm tem 18 combinações,
três repetições de 30 minutos: 54 sessões, 27 horas, incluindo pilotos válidos. Os seis mapas
são Juperos 2, Abbey 3, Thor 1, Bio3, Manuk 2 e Thanatos 9, nas faixas indicadas no plano.
MVPs: GTB 99, Baphomet 150, Randgris/Ifrit 255; solo e dupla, três tentativas por alvo/modo,
24 tentativas de até dez minutos, até quatro horas de combate além de preparação e resets.
O piloto é a primeira execução proposta; não é necessário realizar todo o painel de uma vez.
As fichas de MVP começam com Sniper; suporte HP/Professor é alternativa a registrar.

O pacote não provisiona um servidor de testes nem cria personagens. Não houve combate,
reinício, instalação ou alteração de arquivos/bancos em produção nesta rodada. Evidência
dos testes de software e verificação das fichas em `design-audit/balance-session-kit/verification.json`.

## Validação isolada e protocolo de progressão (19/10/2026)

Cinco avanços depois do pacote de fichas:

1. **Ambiente temporário validado.** A VPS tem uma CPU e cerca de 1 GiB de RAM disponível
   na sondagem; não havia outro serviço rAthena de testes identificado. Foi executado um
   laboratório curto em namespaces próprios de rede, processos e mounts, com banco vazio,
   apenas loopback, fontes de produção montadas em leitura, credenciais próprias e limite
   de CPU de 25%, RAM de 384 MiB e duração de 180 s. Não instala pacotes. O teste usa cópias
   reais dos executáveis: rAthena muda o diretório de trabalho para o diretório do binário,
   portanto apontar diretamente ao executável instalado não é isolamento suficiente.
   A configuração privada também encobre os imports originais dentro do namespace.
2. **Criação real pelo protocolo do jogo.** Login e char-server isolados receberam pedidos
   de criação de dois personagens QA. Cada inventário teve exatamente 100 itens 501,
   uma faca 1201 equipada na posição 2 e uma camisa 2301 equipada na posição 16, todos
   identificados. Não foram copiadas contas de produção. O map-server não foi iniciado;
   não houve combate. Ao encerrar, processos, banco e diretórios temporários foram removidos.
   Serviços e configuração de personagens da produção permaneceram iguais. Evidência:
   `design-audit/game-lab/character-check.json`; executor: `tools/isolated_char_check.py`.
3. **Nível inicial não significa nível constante.** Com EXP 300x, uma sessão iniciada no 99
   pode atravessar níveis. O piloto v2 compara progressão desde o mesmo nível inicial,
   registra nível final e não distribui pontos nem troca equipamento durante a janela.
   HP/SP podem crescer com o nível; por isso o resultado não será divulgado como comparação
   de DPS fixo no 99. Ensaios em nível fixo precisam declarar e manter o nível; se subir,
   o apurador rejeita essa classificação. Somente fichas ainda pendentes foram migradas.
4. **EXP e perdas pela curva.** Os 254 custos de transição anteriores ao cap do CSV local
   coincidem com o `job_stats.yml` instalado. A ficha pode informar nível/EXP parcial de
   início e fim e o hash da curva. O apurador calcula o progresso líquido entre níveis,
   aceita perdas por morte e recusa EXP parcial incompatível ou curva diferente.
   Progresso líquido não é EXP bruta concedida por monstros. Ao atingir/estar no 255, usar
   EXP desconhecida/não aplicável; um equivalente de EXP 300x por abate é cálculo separado,
   nunca ganho efetivamente acumulado no cap. Evidência: `design-audit/game-lab/curve-verification.json`.
5. **Trava para ampliar o piloto.** `tools/analyze_balance_pilot.py` só libera a consistência
   dos registros após receber três sessões reais e sequenciais do ambiente isolado,
   Sniper/SinX/HW iniciando no 99 em Juperos 2, com 30 minutos cada. Exige fichas de
   referência, IDs únicos, painel real, buffs próprios registrados, ausência de suporte
   externo, contador calibrado, caixa e consumíveis reconciliados. EDP declarado exige
   Poison Bottle consumida. Dados sintéticos, sobreposição de horários, mudanças de
   build e fichas pendentes bloqueiam a passagem. Isso não aplica balanceamento e não
   autentica declarações no servidor. Uma sessão por classe ainda não prova superioridade.

Apuração do piloto, depois de preencher cópias das três fichas:

```powershell
python tools/analyze_balance_pilot.py sessao-sniper.json sessao-sinx.json sessao-hw.json
```

Sessões ausentes ou pendentes retornam código 2, sem métricas. Os testes de software cobrem
64 casos; simulações usadas por esses testes não foram salvas como sessões observadas.
O piloto de combate continua com **zero sessões executadas de três necessárias**.
O laboratório de criação foi removido e não constitui servidor persistente de combate;
seus limites de CPU não servem como medição de desempenho de produção. Esta rodada não
iniciou o map-server nem realizou combates, e não alterou arquivos, personagens ou bancos
de produção. As referências 300x/255/185/197 permanecem iguais.

## Verificação funcional dos NPCs no laboratório (19/10/2026)

Cinco verificações passaram em login, char e map-server isolados, com banco vazio e cliente
QA via protocolo do jogo. Scripts dos NPCs e biblioteca global foram copiados sem alterar
seus bytes; os hashes estão em `design-audit/npc-runtime/verification.json`. Um NPC de
controle separado apenas preparou dados e leu os saldos do laboratório.

1. **Mapa:** inicialização e operações sem erros de script/SQL. Carregados 12 mapas,
   incluindo dependências das conquistas, e zero spawns de monstros. As taxas efetivas
   de base/job foram conferidas em 30.000 (300x), com atributo máximo 185. O ambiente
   usou CPU limitada a 25%, RAM a 512 MiB, rede com loopback apenas, fontes montadas em
   leitura e duração máxima de 300 s; não serve como benchmark de produção.
2. **NPCs retirados:** os includes da Escada e dos dois arquivos de times continuam
   ausentes do grafo ativo. No arquivo de feriado carregado, `getnpcid` retornou zero
   para Tine e ID válido para `FaithRO_ValentineBonus`. A checagem de runtime cobre esse
   arquivo carregado; não é uma carga integral de todos os NPCs da produção.
3. **Loteria:** primeira compra debitou 4.750; outra compra no mesmo sorteio foi
   bloqueada sem novo débito. Depois de executar o evento de sorteio no laboratório,
   a renovação debitou 4.750 e manteve os seis números do bilhete anterior. Os seis
   números eram distintos e estavam no intervalo 1–40. Nenhum prêmio foi resgatado.
4. **Arena:** o treinador exibiu evolução, abandono e cancelamento, sem opção de venda;
   informou a suspensão. Cancelar manteve os 1.234 pontos e 50.000 zeny preparados no
   laboratório. Não foram iniciadas lutas nem gastos pontos em evolução.
5. **Caça:** uma nova missão sorteou quatro IDs distintos da pool ativa e quantidade
   dentro de 40–70 (63 nesta execução). Para testar a entrega sem lutar, o controlador
   preparou quatro alvos — Poring, Fabre, Pupa e Salgueiro — com 40/40 em cada contador.
   O pagamento foi exatamente `40 × 4 × (1+2+2+4) × 6 = 8.640` zeny, com três pontos;
   o diálogo mostrou 28.800 EXP de base e 26.400 de classe, conforme o cálculo a 300x.
   O progresso foi limpo, o total de missões aumentou para um e uma tentativa imediata
   foi bloqueada por cooldown de aproximadamente 43.200 segundos (12 h).

A conclusão da caça foi artificialmente preparada para validar a transação. Não equivale
a completar 160 abates, provar velocidade de farm ou observar emissão por jogadores reais.
Os testes de combate do piloto permanecem em zero de três sessões.

O QA detectou e corrigiu um erro do mini-cliente Python em `tools/bot/protocol.py`: opções
vazias de menu eram contadas como opções visíveis. No rAthena instalado,
`script.cpp:menu_countoptions` converte a posição visível enviada pelo cliente para a
posição original do script. A opção de status da caça, precedida por um campo vazio,
deve ser enviada como primeira opção visível. O decoder agora elimina somente campos
vazios, preservando espaços e cores. A regressão cobre lacunas iniciais, intermediárias
e finais; os 19 testes de protocolo passaram. O cliente corrigido foi usado em cópia
temporária no laboratório; o FaithBot da produção não foi republicado nesta rodada.

Durante a montagem do laboratório foram completados imports/mensagens e mapas exigidos
pelo loader. As configurações públicas de combate são capturadas antes de esconder os
imports da produção; uma leitura posterior do caminho encoberto usaria os defaults do
laboratório. A execução final confirmou as taxas efetivas antes de validar os diálogos.

Pendência textual identificada, sem mudança aplicada: a Loteria anuncia 21h no diálogo,
mas seu evento é `OnClock2045` (20h45 no relógio do servidor). A coleta atual não verificou
o fuso do serviço. Alinhar a mensagem ao horário de execução é candidato de confiança alta,
com baixo risco; validar pelo evento e pelo texto antes de publicar uma correção.

Ao terminar, o laboratório foi removido. Os PIDs dos cinco serviços principais e a
configuração de personagens da produção permaneceram iguais; não houve combate nem
alteração de personagens, bancos ou scripts de produção. Executor:
`tools/isolated_char_check.py --npc-checks`, com `tools/isolated_npc_checks.py` ao lado.

## Verificação de cura, transportes e compras (19/10/2026)

Cinco caminhos adicionais foram exercitados por cliente nativo no laboratório
temporário, sem monstros. Os seis arquivos de NPC/mapflags vieram da instalação e
mantiveram seus hashes. Um observador separado preparou personagens sintéticos e
leu HP, SP, buffs, zeny, inventário, coordenadas e desbloqueios pelo próprio script.
Essas observações funcionais não representam desempenho de jogadores.

1. **Curandeira.** Cura gratuita e buffs de Blessing/Increase AGI nível 10 por
   240 segundos até o nível 99 confirmados. No nível 100, cura sem esses buffs.
   Foi encontrada uma falha: a cura vem antes dos buffs; no Sniper 99 de teste,
   restaurou 512 SP e Blessing elevou o máximo para 563, deixando déficit de 51.
   No nível 100, sem buffs, restaurou 517/517 SP. O déficit não é um valor fixo
   para todas as builds: depende do máximo de SP antes/depois do buff.
2. **Limites de tarifa.** A função instalada e o débito real para Juperos 1
   concordaram: nível 99 grátis; 100 e 199 pagam 25.000; 200 e 255 pagam 50.000.
   O destino foi confirmado como `juperos_01`, coordenadas 53,247.
3. **Destinos e último teleporte.** Repetir o último destino no 255 cobrou mais
   50.000. Com 49.999, não houve débito nem warp e o último destino foi preservado.
   Alberta foi acessível gratuitamente no 255 com saldo zero; a função usa o
   mapflag `town` do destino, carregado do arquivo oficial instalado.
4. **Warpra.** Consulta somente de leitura confirmou `$QW_DW_OFF=1` e
   `$QW_MapUserShow=1`; demais chaves numéricas consultadas, ausentes, valem zero.
   O laboratório reproduziu esse estado: menu de calabouços ausente,
   desbloqueio de Prontera por visita funcional e viagem urbana gratuita.
   Com calabouços habilitados e Juperos desbloqueado **somente no laboratório**,
   houve débito líquido de 25.000 no 100 e 50.000 no 200, sem devolução.
   Há outra pendência: o menu de andar mostra `Nível 1 [0]`, sem a tarifa por
   nível, embora a cobrança ocorra. Esse caminho está desligado em produção.
5. **Compras.** Preço exibido, débito e itens recebidos concordaram: Poison Bottle
   (678) 50.000; Blue Potion (505) 5.000; dez flechas (1750) 100; gemas
   715/716/717 a 600 cada; Acid Bottle (7136) e Bottle Grenade (7135) a 500 cada.
   O lote de três gemas e dois frascos custou 2.800. Comprar Poison Bottle com
   49.999 foi recusado sem alterar dinheiro ou quantidade. Personagem sem Discount;
   esta verificação não mede consumo em combate nem cobre todas as lojas.

Os dois achados geraram propostas concretas, sem aplicação no overlay ou na VPS:

| Achado | Atual → candidato | Efeito esperado e risco | Confiança e aceite/descarte |
|---|---|---|---|
| SP após Blessing | curar antes → curar depois dos buffs | Completar o máximo final de HP/SP. Risco baixo, verificar recálculo e renovação de buffs existentes | Alta no diagnóstico. Ensaiar níveis 1/99/100/255, INT baixa/alta e equipamentos de SP. Adotar apenas com HP/SP completos, gratuidade, duração de 240 s, intervalo de 3 s e buffs somente até 99 preservados; descartar se qualquer condição falhar |
| Preço na Warpra | prévia sem taxa compartilhada → incluir a mesma função na prévia do andar | Informar o total antes da escolha, preservando o débito. Risco baixo de divergência ou duplicação com preços de GM | Alta no diagnóstico. Ensaiar 99/100/199/200/255, exibição de usuários ligada/desligada, profundidades 0/1 e taxas adicionais de GM. Adotar apenas se prévia = débito e saldo insuficiente não cobrar; descartar se houver diferença, cobrança dupla ou alteração da chave desligada em produção |

Os patches `design-audit/service-runtime/healer-sp-candidate.patch` e
`warpra-price-preview-candidate.patch` estão prontos para revisão, mas ainda não
foram aplicados nem ensaiados. Ambos passaram em `git apply --check` contra o
overlay local, sem escrita nos arquivos de NPC. Critérios completos em `recommendations.json`.
O próximo trabalho proposto é o ensaio desses candidatos no laboratório.

Durante a preparação, o observador de QA foi corrigido para se desligar do RID antes
de `end`: o comando instalado envia um pacote de fechamento enquanto há personagem
anexado, interferindo na janela da loja. A correção pertence ao laboratório;
não foi necessário mudar NPCs ou o protocolo do cliente nesta rodada.

Evidências: `design-audit/service-runtime/verification.json`,
`production-warpra-config.json` e `cleanup-verification.json`. Os 83 testes locais
de protocolo, sessão e piloto passaram. Executor Linux:
`tools/isolated_char_check.py --service-checks`, com
`tools/isolated_service_checks.py` e o pacote `bot` ao lado. O executor limita CPU
a 25%, memória a 512 MiB e duração a 420 s, remove o laboratório e confere os PIDs
dos cinco serviços principais e o hash da configuração de personagens.
Não houve combate, alteração de bancos/personagens/NPCs em produção ou adoção de
balanceamento. EXP 300x, nível 255, atributos 185 e ASPD 197 permanecem como referência;
o piloto real continua pendente.

## Ensaio dos candidatos após o PR #94 (19/10/2026)

Esta rodada atualiza o estado dos dois patches de referência: foram ensaiados em
cópias privadas dos NPCs, após uma execução de comparação com os arquivos instalados.
O overlay operacional e a VPS continuam com os NPCs anteriores. As cinco etapas foram:

1. **Branches e worktrees.** Nova busca em `C:/Development`, worktrees do Codex e
   temporários encontrou duas cópias Git do FaithRO, ambas limpas antes desta rodada,
   sem stashes, commits exclusivos nas branches antigas ou worktrees vinculados extras.
   As branches dos PRs #93/#94 já pertencem ao histórico de `main`; nenhuma foi apagada,
   resetada ou trocada na cópia antiga. O ensaio foi preparado na branch local
   `test/candidatos-cura-warpra` do checkout Git.
2. **Comparação da Curandeira.** O arquivo instalado repetiu 512/563 SP no Sniper 99
   com INT 1. Com INT 90 e Anel de Morpheus (2648), ficou em 1.018/1.072. A cópia com
   `percentheal` após os buffs completou 563/563 e 1.072/1.072, respectivamente.
   A matriz candidata teve nove builds: Aprendiz 1 e Sniper 99/100/255, INT natural
   1 ou 90, com/sem anel conforme nível. O anel vendido na loja foi conferido na base
   instalada: nível mínimo 33, INT +1 e SP máximo +5%. Equipamento e atributos foram
   preparados pelo controle de QA; não representam itens obtidos por um jogador.
3. **Limites e repetição da cura.** Nas nove builds, HP/SP finais ficaram completos,
   sem débito. Blessing/Increase AGI nível 10 foram concedidos no 1/99, com duração
   observada próxima de 240 s; no 100/255 não foram concedidos. Após reduzir HP/SP pelo
   controle do laboratório, clicar antes do prazo foi bloqueado; após o prazo configurado
   de 3 s, curou novamente. A renovação dos buffs existentes também deixou SP completo.
4. **Prévia e cobrança da Warpra.** Os arquivos instalados omitiram 25.000/50.000 do
   menu no 100/200 e descontaram esses valores. O candidato passou em 40 combinações:
   níveis 99/100/199/200/255 × usuários no menu ligados/desligados × Juperos andar
   1/2 (profundidade 0/1) × preços de GM zerados/adicionais. O perfil adicional foi
   base de 3.000 e 700 por profundidade. Em todos os casos, a prévia coincidiu com o
   débito líquido, sem taxa compartilhada duplicada. No 200, por exemplo, o andar 2
   mostrou e cobrou 53.700. Cinco tentativas com uma unidade a menos foram recusadas
   sem débito ou warp. Com a chave desligada, o menu de calabouços permaneceu ausente
   nas duas versões; o ensaio não habilitou esse caminho na produção.
5. **Regressão e encerramento.** Os 83 testes locais passaram. O modo candidato recusou
   execução no Windows sem realizar ações. As duas instâncias sequenciais de map-server
   do laboratório carregaram sem erros e com zero spawns. O ambiente temporário foi
   removido; PIDs dos cinco serviços, configuração de personagens e hashes dos NPCs
   instalados permaneceram iguais. Consulta final confirmou `$QW_DW_OFF=1` na produção.

Evidências em `design-audit/candidate-runtime/verification.json`,
`cleanup-verification.json` e `recommendations.json`. O inventário Git com paths locais
fica apenas na cópia operacional, fora da publicação. Executor:
`tools/isolated_char_check.py --candidate-checks`, com o helper
`tools/isolated_candidate_checks.py`, pacote `bot` e os dois arquivos `.patch` ao lado.
O executor exige `git` já instalado, confere os patches antes de aplicá-los e limita
o laboratório a CPU 25%, 512 MiB e 600 s. A aplicação acontece somente após encerrar
a instância de comparação e somente nos arquivos privados temporários.

A confiança é alta no comportamento funcional coberto. Os resultados não cobrem
todas as combinações de buffs/equipamentos, nem todas as restrições de rotas da Warpra.
Os patches estão validados para preparar uma futura aplicação controlada. Adotar apenas
se uma implantação posterior mantiver HP/SP completos, gratuidade, limites/duração de
buffs, intervalo e igualdade entre prévia e débito; descartar ou reverter se houver
divergência, cobrança duplicada, débito com saldo insuficiente ou habilitação inesperada.
A próxima rodada proposta é preparar o pacote de aplicação e rollback dos dois NPCs.
Para desfazer esta rodada de QA, reverter as ferramentas/documentação; o laboratório
já foi descartado e não existe migração ou alteração de produção para reverter.
O piloto real permanece em 0/3 e EXP 300x, nível 255, atributos 185 e ASPD 197 seguem
como referência.

## Aplicação na produção e na VPS (19/10/2026)

As duas correções validadas após o PR #95 foram aplicadas em 19/10, às 03h18 de
São Paulo, em uma janela iniciada com zero personagens online. O map-server foi
parado, os dois arquivos foram substituídos e o serviço reiniciado. A janela até
a confirmação de prontidão e estabilidade durou 4,38 s.

- **Curandeira:** `percentheal` passou para depois dos buffs, preenchendo o máximo
  final de HP/SP conforme os nove casos de laboratório.
- **Warpra:** a prévia do andar inclui a função compartilhada de tarifa, conforme
  os 40 casos de laboratório. A chave `$QW_DW_OFF=1` permanece na produção.
- **Sincronização:** arquivos instalados em `/home/rathena/rathena`, espelho de
  deploy em `/root/faithro/deploy/server` e overlay operacional local foram atualizados.
  A Warpra instalada mantém CP1252; os espelhos UTF-8 têm o mesmo conteúdo lógico.

Antes da mudança foram conferidos os hashes de origem, os hashes dos candidatos
ensaiados e a igualdade lógica dos espelhos. O lock existente de deploy foi usado.
Backup criado e relido para validação:
`/var/backups/faithro/npc-healer-warpra-20261019T061852Z.tar.gz`, com os quatro arquivos
anteriores e manifesto de hashes, donos e permissões. SHA-256 do arquivo:
`0c26e1996fcf97b2f62fc17ef2f55961252875a9186b2a3b739cbb17c3a5bd6f`.
O backup não integra esta publicação.

Apenas `rathena-map` foi reiniciado. Login, char e os dois serviços web mantiveram
seus PIDs. O novo trecho do log não teve erros de script ou SQL, e o autoteste
confirmou EXP 300x/300x, atributos naturais/trans 185, ASPD 197 e aura no 255.
Os hashes de configurações protegidas, incluindo as tabelas de nível/atributos,
permaneceram iguais. O site público com User-Agent de navegador e o `/healthz` local
responderam HTTP 200. A sonda pública com User-Agent padrão do Python recebeu 403;
as sondas de navegador na VPS e fora dela responderam 200.

O comportamento funcional foi ensaiado no laboratório. Na produção foram verificados
arquivos, carga, autoteste, serviços e HTTP; não foram alterados personagens pelo
executor nem iniciados combates. O executor não emitiu SQL de escrita. Os hashes
instalados coincidem com os candidatos ensaiados.

Evidências: `design-audit/production-npc-fixes/deployment.json`, `health.json` e
`local-overlay.json`. O ensaio comparativo `--candidate-checks` da rodada anterior
requer a versão anterior como referência; depois desta aplicação, uma repetição exige
preparar essa referência no laboratório a partir do backup, sem restaurar a produção.
Em falha de inicialização, o procedimento preparado restauraria
automaticamente os quatro arquivos e iniciaria novamente o map-server; não foi
necessário usá-lo. Para reversão posterior, abrir outra janela com zero personagens,
parar apenas o map-server, conferir o SHA-256 acima, restaurar as entradas
`installed/` e `deploy/` nos respectivos diretórios preservando dono/permissão e
reiniciar com a mesma validação de log/autoteste. Restaurar também os dois arquivos
do overlay local a partir da cópia anterior mantida no registro operacional.
Reverter apenas esta documentação no Git não desfaz a aplicação na VPS.

## Cinco verificações após a implantação (19/10/2026)

1. **Estabilidade e recuperação.** Cinco serviços ativos, contadores de reinício
   automático em zero, nenhum erro de mapa/SQL após a última prontidão e HTTP 200
   no site e no healthcheck local. O backup dos dois NPCs foi aberto novamente:
   cinco entradas, modo 600 e SHA-256 igual ao registrado na implantação. Esta leitura
   não equivale a ensaio de restauração em produção.
2. **Fontes e database pública.** Coleta somente de leitura voltou a encontrar 6.171
   itens, 1.004 monstros, 5.019 drops e 1.912 pares de spawn. Nenhuma divergência
   entre drops/spawns esperados e tabelas do site. Quatro páginas públicas também
   foram conferidas: Gold do Golden Thief Bug 30%, Gold da Maya Purple 3%, Stone of
   Sage do Gemini 30% e Treasure Box do Thanatos 10%, incluindo os multiplicadores
   específicos. Rates, densidades, cenários e builds calculados não mudaram.
   Escada, times, Tine, venda de pontos da Arena e regras anteriores continuaram
   no estado esperado. Campos de métricas de jogadores foram retirados do snapshot
   público; consultas operacionais continuaram filtrando equipe, bot e operações
   administrativas. Logs não foram convertidos em abates ou horas jogadas.
3. **Horário da Loteria.** O host usa `America/Sao_Paulo`, o processo do mapa não
   tem override `TZ` e `npc_event_do_clock` usa `localtime()` no código instalado.
   O evento é `OnClock2045`; a produção ainda anuncia 21h na confirmação.
   O candidato `lottery-time-candidate.patch` altera apenas essa mensagem para
   **20h45 (horário de São Paulo)**. Foi aplicado somente à cópia privada e a
   confirmação correta apareceu pelo cliente nativo. A compra continuou em 4.750;
   segunda compra foi bloqueada sem débito tanto no mesmo personagem como em outro
   personagem da mesma conta. Não houve resgate de prêmio ou execução do sorteio
   real em produção. Confiança alta; risco baixo, condicionado à manutenção do fuso
   e do evento. Adotar apenas se mensagem, fuso e evento concordarem; descartar ou
   reverter se horário pretendido for outro ou se preço/regra de bilhetes mudar.
4. **Poções de início.** Dois personagens novos do banco privado receberam 100
   Red Potions (501), faca/camisa equipadas e zero zeny inicial. O controle de QA
   reduziu HP antes do ensaio; cada personagem usou uma poção pelo pacote real
   `CZ_USE_ITEM2` (0x0439). O ACK confirmou sucesso, o inventário passou para 99 e
   o HP de 1 para 40/40, sem cobrança. Equipamentos permaneceram e as quantidades
   99/99 foram salvas no banco privado ao sair. Não foram criados personagens ou
   alterados inventários na produção.
5. **Regressões e prioridades.** Os 83 testes locais passaram. O laboratório foi
   removido, sem unidades ou diretórios de QA restantes, e o hash da Loteria instalada
   permaneceu igual. Não há nova evidência de combate que sustente ajuste de rates,
   EXP, atributos, ASPD ou habilidades. Os orçamentos trans 99/150/200/255 continuam
   1.325/2.722/4.597/7.237; os cenários de farm permanecem cálculos brutos condicionais.
   O piloto real segue 0/3. Próximas prioridades: aplicação controlada do texto da
   Loteria, piloto PvM já especificado para Sniper/SinX/HW e, depois, fichas de MVP
   separando chefe, invocações, falhas e consumíveis. Preservar os valores atuais até
   existir evidência suficiente; validar/descartar hipóteses pelos critérios anteriores.

Evidências em `design-audit/post-deploy-review/`: `stability.json`, `snapshot.json`,
`public-database.json`, `onboarding-verification.json`, `cleanup-verification.json`,
`lottery-review.json` e `priorities.json`. Os horários UTC nos arquivos são metadados;
o horário comunicado ao jogador usa São Paulo.
O modo manual `tools/isolated_char_check.py --onboarding-checks` exige o helper
`isolated_onboarding_checks.py`, o pacote `bot` e o patch de horário ao lado do executor
no pacote temporário. Converte o patch para CP1252 antes de conferir/aplicar na cópia
privada, usa CPU 25%/512 MiB/300 s e não executa combates. Reverter esta rodada remove
ferramentas/documentação/candidato; não existe alteração de produção a restaurar.

## Riscos deixados para depois

- **Zeny vindo de drops.** Tratado em `docs/drops.md` (tetos por categoria, equipamento 30x,
  prêmio de MVP 3x, baús 5x e `db/import/mob_item_ratio.yml` para Gold, Treasure Box etc.).
  Ralos: refino, Kafra e a taxa do warper (rodada 2).
- **Pouco conteúdo acima do 100.** A revisão encontrou 9 monstros de classe Normal,
  sem MVP, com EXP e spawn estático ativo, acima do nível 100. A contagem antiga de 7
  não representa esse critério. A progressão
  200→255 repete os mesmos mapas; conteúdo novo (instâncias, mapas custom) é a saída real.

## Como medir

`picklog` registra movimentações de itens; suas linhas não contam abates. `mvplog` registra
vitórias de MVP, sem medir horas jogadas. Intervalos entre logs também não medem sessões.
Para EXP/h e abates/h, usar contador de abates validado e cronômetro de uma sessão de ensaio,
registrando separadamente combate, deslocamento, venda, recuperação e mortes.
Filtrar contas comuns (`group_id=0`, excluindo serviço/bot), retirar lançamentos administrativos
e separar emissão por NPC, transferência entre jogadores e gastos. A coleta atual não sustenta
alterações na curva. Os limites de tempo das metas são critérios propostos para ensaios, não
gatilhos automáticos para alterar `POST99_START`, `TIERS` ou `BOOST`.
Estudo complementar da rodada 2: [estudo-balanceamento.md](estudo-balanceamento.md).
