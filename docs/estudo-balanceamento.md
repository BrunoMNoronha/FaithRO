# Estudo de balanceamento do FaithRO, rodada 2

Data: 18/10/2026. Estudo estático e simulado, sem alterações no servidor ou deploy.
Complementa [balanceamento.md](balanceamento.md), preservando as decisões da primeira rodada.

## Resumo executivo

A prioridade é fechar caminhos que entregam MVPs e cartas sem a progressão pretendida, depois
medir a economia e o combate. Não há evidência de inflação já ocorrida nem de desempenho real
de classes. A consulta encontrou duas contas humanas, ambas `group_id=99`, uma conta de serviço
`sex='S'`, dois personagens, `mvplog` vazio e um lançamento `A` de +1.000.000 no `zenylog`.
Contar a conta de serviço explica as três linhas em `login`; não apareceu uma terceira conta
de jogador. Fontes: Q01 e coleta de 18/10.

Gravidade G: 5, quebra uma regra central ou permite emissão evitável; 4, forte distorção;
3, atrito relevante. Facilidade F: 5, retirar um include ou ajustar constante; 4, pequeno ajuste
de script; 3, ajuste com validação de combate. Ordenação por G × F, com desempate pelo alcance.
Os números sugeridos são hipóteses para uma próxima rodada, não decisões aplicadas.

| # | Problema confirmado | G | F | G×F | Ação proposta e evidência |
|---|---|---|---|---|---|
| 1 | Arena gratuita mantém 209 MVPs em 32 salas, com cura e sem gate | 5 | 5 | 25 | Retirar `etc/mvp_arena.txt` de `optional.conf`. Entrada L20–27; spawns L123–249. Respawn real 60–126 s, média 93 s, não 60–66 s |
| 2 | Rotas custom de cartas contradizem a regra de drop | 5 | 5 | 25 | Desligar `quests/berzebub.txt`, retirar cartas de `THQS_TTShop.txt` e álbum de `rpsroulette.txt`. Carta MVP 4145 é entregue em `berzebub.txt:54`, uma vez por personagem |
| 3 | Bolsa cria lucro previsível sem consumir recursos de combate | 5 | 5 | 25 | Desligar `etc/stock_market.txt`. Sete atualizações/dia, taxa 1.500; simulação de 1.000 dias produz 4,55–5,40 M/dia na estratégia descrita, dependendo do início e do alvo |
| 4 | Sala privada vende 46 MVPs por 100 k cada, sem cooldown | 5 | 4 | 20 | Suspender `etc/mvp_room.txt`; eventual reabertura por tier, limite e nível. Mais 100 k de aluguel/60 min; `nopenalty` L394–401 |
| 5 | Roleta gratuita produz álbuns, caixas e zeny de revenda | 5 | 4 | 20 | Desligar `etc/rpsroulette.txt`; política de jogar pedra dá 50% de vitória e 5% de álbum por partida concluída; L82–122 |
| 6 | Loja e quests pulam a obtenção de equipamento e itens divinos | 4 | 5 | 20 | Retirar Kaho e armas de fim de jogo de `itemmall.txt`; suspender Kaho/Balmung e revisar `valhallen.txt`/Mjolnir por tokens. Kaho custa 700 k na loja, 1 M ou 5 M nas quests |
| 7 | Juros por conta emitem até 100 k por contato diário | 4 | 5 | 20 | Em `etc/bank_kafra.txt:31`, rendimento zero; preservar depósitos. É 0,1%/dia, não 0,01%; datas usam mês× 31 sem ano |
| 8 | Cura, buffs e transporte gratuitos apagam custos recorrentes | 4 | 4 | 16 | Buffs gratuitos só até 99; warper por faixa, com a mesma política em todos os transportes. `healer.txt:18–38`; warper sem gate |
| 9 | Blackjack liquida a aposta só no resultado | 3 | 5 | 15 | Suspender até débito antecipado e validação de abandono. Apostas 2–100 z, até 200 ao dobrar: bug confirmado pelo fluxo, impacto econômico pequeno; L133–149,224,239–249 |
| 10 | Saturação de ASPD/cast, concentração de EXP e pouca observabilidade | 4 | 3 | 12 | Testar ASPD 193 e Asura -50% apenas em PvP/WoE; conservar HP inicialmente. Instrumentar antes de mexer na curva. `status.cpp`, `skill.cpp`, `battle.cpp` e Q02–Q08 |

Outros achados que alteram o pedido inicial: a taxa de vending já é 5%, mas só a partir de
100 M; a caça depende de uma tabela SQL ausente e sua EXP calculada é bônus de 20%; não há
equipamento com drop garantido e `sell > 100k` em mobs de spawn oficial; são 11 mobs normais com EXP acima
do nível 100, dos quais nove têm spawn oficial estático, sob a definição da seção 3.3.

## 0. Fontes, definições e limites

Snapshot rAthena na VPS: `d4b8e7b8f16061cc2496d377ac8f777ce72a4f39`. `config.status` confirma
compilação com `-DPRERE`; `src/config/core.hpp:49` habilita `HP_SP_TABLES`. Foram copiados por
`scp` os YAML pre-re, fontes de cálculo, configurações e spawns efetivamente referenciados.
O snapshot tem 6.169 itens, 1.004 mobs, 5.019 linhas de drop e 1.907 pares mob/mapa. Não executar
`build_gamedb.py`: seu `main` recria tabelas; aqui somente se leu o código e se fez `SELECT`.

Durante a redação apareceram alterações paralelas em `docs/drops.md` (documento da cópia local), na configuração
local de drops e em `mob_item_ratio.yml`. A VPS ainda mantinha equipamento 50 x, prêmio MVP10 x
e treasure 10 x na checagem final. Este estudo conserva essa fotografia em produção, não trata
a proposta local de 30 x/tetos como já implantada e não modifica nem avaliza o patch paralelo.
Recalcular a economia após qualquer implantação; a análise de acessos/NPCs continua pertinente.

Fontes locais: `server/conf/import`, `tools/gen_progression.py`, `tools/gen_mob_boost.py`,
`docs/progressao.csv`, os dois includes custom e todos os scripts neles declarados. Nas tabelas
de NPC, caminhos sem prefixo são relativos a `server/npc/custom/faithro/ptbr/custom/`.
Linhas referem-se às cópias locais de 18/10; fontes C++ referem-se ao commit acima na VPS.

Há quatro tipos de número: **observado** em SELECT/arquivo; **derivado** por fórmula;
**simulado** com hipóteses explícitas; **meta proposta** para validar com jogadores.
Nenhuma estimativa de abates/h ou prazo foi medida em produção. M = milhão, G = bilhão.
Preço `sell` é revenda ao NPC; não é preço de mercado entre jogadores. Ignoram-se Overcharge,
Steal, conversão de pedras elementais, competição, lag, peso, tempo de venda, buffs, cartas
e grupos, salvo quando expressamente indicados. Overcharge 10 acrescenta aproximadamente 24%
à parcela vendável; não multiplicar por isso a EXP nem o zeny pago diretamente por scripts.

O builder do site perde o respawn e não expande `Ai` em `modes`. Por isso se recuperou o
respawn nos arquivos carregados e a agressividade em `mob.hpp:150–177`, bit 0 x 4 dos tipos de
AI, mais overrides de `Modes`. Os 3.375 registros de spawn agregam exatamente os mesmos
1.907 pares de `mob_spawns`, sem divergência de quantidade. O gerador de boost considera
`monster`, não `boss_monster`; ser `Class: Boss` no YAML não basta para excluir um spawn do
gerador. O fator foi aplicado pelo tipo da linha, pelo evento e pelo nome do arquivo.

## 1. Economia de zeny

### 1.1 Oferta dos mapas e rendimento de uma pessoa

Para cada mob, `V = SUM(rate_final / 10000 × sell)` dos drops normais (`mvp=0`). Para cada
linha de spawn, `T = max(1, (delay1 + (delay2 - 1)/2)/1000)` quando `delay2>0`; sem variância,
usar `max(1,delay1/1000)`. `mob.cpp:1071–1092` soma a variância e impõe piso de um segundo.
As três configurações `*_spawn_delay` permanecem 100. Somar `amount × V × 3600/T` dá a
**capacidade de reposição se todos os mobs morrerem imediatamente ao reaparecer**.

Essa capacidade pode dar bilhões/h por mapa. Não é renda de jogador, e nem uma previsão
executável para uma VPS de 1 vCPU. Uma limpeza é estoque, zeny/h é fluxo. Nos mapas de respawn
de um segundo, dividir apenas pelo respawn ignora quase todo o tempo de matar e encontrar.
MVPs ficam fora dos rankings abaixo; mobs regulares com `Class: Boss` e mini-bosses entram.
Prêmio exclusivo de MVP não foi somado como drop comum. Preços são os da Q02.

| Mapa | spawn oficial/final | z/limpeza of./final | M z/h of. | M z/h final |
|---|---|---|---|---|
| juperos_02 | 315/3.150 | 1.716.758/17.167.582 | 6180,33 | 61803,29 |
| hu_fild 07 | 220/2.200 | 690.504/6.905.045 | 2370,57 | 23705,68 |
| iz_dun 02 | 196/1.960 | 591.903/5.919.033 | 2077,11 | 20771,12 |
| hu_fild 04 | 223/2.230 | 550.098/5.500.978 | 1741,00 | 17410,04 |
| abbey 01 | 258/2.580 | 338.388/3.383.876 | 1218,20 | 12181,95 |
| gefenia 03 | 154/154 | 1.432.631/1.432.631 | 5033,74 | 5033,74 |
| gefenia 02 | 144/144 | 1.352.914/1.352.914 | 4746,76 | 4746,76 |
| alde_dun 03 | 196/1.960 | 427.884/4.278.845 | 457,41 | 4574,06 |
| prt_sewb 3 | 210/2.100 | 126.121/1.261.208 | 454,04 | 4540,35 |
| jupe_core | 275/275 | 1.182.523/1.182.523 | 4257,08 | 4257,08 |
| tha_t 02 | 174/174 | 1.181.607/1.181.607 | 3807,93 | 3807,93 |
| in_sphinx 5 | 117/117 | 1.027.411/1.027.411 | 3624,88 | 3624,88 |
| gefenia 01 | 144/144 | 1.001.991/1.001.991 | 3483,44 | 3483,44 |
| prt_sewb 2 | 220/2.200 | 86.697/866.967 | 312,11 | 3121,08 |
| lhz_dun 02 | 331/331 | 2.175.048/2.175.048 | 2951,02 | 2951,02 |
| juperos_01 | 285/2.850 | 1.590.730/15.907.304 | 291,18 | 2911,78 |
| gef_fild 05 | 135/135 | 763.151/763.151 | 2736,37 | 2736,37 |
| tha_t 08 | 57/57 | 1.571.786/1.571.786 | 2479,31 | 2479,31 |
| tha_t 05 | 242/242 | 1.006.727/1.006.727 | 2454,12 | 2454,12 |
| tha_t 06 | 222/222 | 980.233/980.233 | 2453,68 | 2453,68 |

Ranking independente com spawn oficial, sem boost:

| Mapa | M z/h |
|---|---|
| juperos_02 | 6180,33 |
| gefenia 03 | 5033,74 |
| gefenia 02 | 4746,76 |
| jupe_core | 4257,08 |
| tha_t 02 | 3807,93 |
| in_sphinx 5 | 3624,88 |
| gefenia 01 | 3483,44 |
| lhz_dun 02 | 2951,02 |
| gef_fild 05 | 2736,37 |
| tha_t 08 | 2479,31 |
| tha_t 05 | 2454,12 |
| tha_t 06 | 2453,68 |
| tha_t 03 | 2394,49 |
| hu_fild 07 | 2370,57 |
| yuno_fild 08 | 2181,6 |
| iz_dun 02 | 2077,11 |
| gl_dun 02 | 1910,58 |
| tha_t 04 | 1867,01 |
| man_fild 01 | 1759,11 |
| hu_fild 04 | 1741,0 |

Para uma pessoa, o modelo é `kills/h = min(oferta de respawn, 3600/(HP_médio/DPS + 8))`.
Oito segundos por alvo representam deslocamento, seleção, coleta e recuperação, não medição.
DPS significa dano efetivo já depois da defesa. A ponderação por quantidade de spawn é um
cenário de limpeza de mapa, não a distribuição exata de abates no estado estacionário.
Respawns longos podem reduzir a presença de mini-bosses no farm sustentado. Não extrapolar
esse mix como uma renda garantida. O cenário AoE × 3 mantém custo de busca de um encontro
com três alvos e precisa de validação; não é um bônus automático de densidade × 10.

| Mapa | Valor médio/abate | Solo a 300 abates/h | Modelo com DPS 30 k e 8 s | AoE × 3, sensibilidade |
|---|---|---|---|---|
| juperos_02 | 5.450 z | 1,64 M/h | 2,33 M/h | 6,99 M/h |
| gefenia 03 | 9.303 z | 2,79 M/h | 3,83 M/h | 11,50 M/h |
| lhz_dun 03 | 11.834 z | 3,55 M/h | 4,16 M/h | 12,47 M/h |
| abyss_03 | 10.669 z | 3,20 M/h | 4,08 M/h | 12,24 M/h |
| tha_t 09 | 41.115 z | 12,33 M/h | 16,17 M/h | 48,51 M/h |

Fonte: scripts A02/A05, V e mix de spawn. A última linha é especialmente sensível ao tempo
de respawn dos Thanatos e ao percurso, não autoriza anunciar 48,51 M/h como resultado real.
O boost amplia disponibilidade e favorece AoE, mas não aumenta o valor de cada abate.

Para comparar com 44 h, um percurso hipotético de 1 h inicial a 0,5 M/h, 10 h de Juperos 02
a 1,862 M/h, 10 h de Abbey 03 a 0,260 M/h e 23 h de bio 3 a 4,157 M/h acumula **117,33 M**
brutos. Essas durações são a meta, não o tempo que os mapas entregam na seção 3. Esse caixa
corresponde a 5,6% do teto aproximado de 2,1 G. Não se confirma a ideia de que todo 255
natural já necessariamente encosta no teto. A 50 M/h, cenário de farm muito eficiente,
2,1 G são 42 h; a 4,16 M/h, 505 h. Com duas horas/dia: 21 ou 252,4 dias, sem gastos.
Com Overcharge e a mesma coleta, a parcela de 117,33 M subiria para aproximadamente 145,49 M.

### 1.2 NPCs que emitem moeda ou itens liquidáveis

| Fonte | Diagnóstico numérico e abrangência | Recomendação concreta |
|---|---|---|
| Bolsa | `stock_market.txt:36–44,47–80,177–178`; sete ticks/dia. Compra máxima 1 M de ações por operação, carteira `#S1..#S10` por conta sem cap total equivalente. Taxa 1.500 na compra e na venda | Desligar o include. Aumentar taxa sozinha não corrige emissão escalável por tamanho de posição |
| Juros Kafra | `bank_kafra.txt:28–38`; floor(saldo/1000)×dias, cap 100 k por interação elegível. 100 M depositados já dão 100 k/dia, 700 k/semana/conta | Rendimento zero na fórmula L31, preservando principal. Cap 10 k ainda é emissão por conta e perde para a alternativa zero |
| Caça | `hunting_missions.txt:90,164–177,312–329`; quatro mobs distintos, 40–70 de cada, espera 12 h após conclusão, `#` por conta. Falha de dependência: SELECT real retorna erro 1146, tabela `ragnarok.mob_db` ausente | Manter desabilitado até portar a seleção à base realmente existente; só depois avaliar zeny ÷ 10. Não aplicar EXP ÷ 5 com base na premissa de 11× |
| THQS | Inscrição 25 k/personagem; cooldown de uma hora por conta, cancelamento 2.500 e 2–3 h. Tokens por missões, de 1 a 5 nas 40 tarefas; `TTShop:54–72` troca 1 token por 1.000 z | Manter tarefas e token; retirar cartas e itens divinos da loja, e conservar o preço em zeny inicialmente |
| Monster arena | Inicial 1.000 z; `monster_arena.txt:324–332` paga 100 z/ponto. Premiações de abate vão de 1 a 512 pontos, até 51.200 z por abate elegível | Desligar venda de pontos até validar tempo de evolução, cura por cliques, invocações e isolamento; pontos não são EXP do personagem |
| Roleta | `rpsroulette.txt:26–55,79–88,108–122`; jogar sempre pedra resolve cada duelo com 50% de vitória, e a câmara que dispara escolhe o vencedor da partida. Esperança de revenda 21.737,50 z/partida, sem considerar abrir caixas | Desligar. A 60 partidas/h, hipótese de um minuto por partida, são 1,304 M/h mais 3 álbuns/h esperados; não há limite diário |
| Loteria | Bilhete 4.750, prêmio 5 M para seis números e 1 M para quatro ou cinco; retorno teórico 2.246,78 z, 47,30%, perda média 2.503,22 z/bilhete | Manter após corrigir trava `#L1` para o campo efetivo `#LW1`; limitar uma compra por conta/sorteio. Atualmente a condição L115 consulta a variável errada |
| Blackjack | Apostas de 2/10/20/100 z, até 200 ao dobrar; crédito na vitória L238, débito na derrota L243. O `next` L237 precede o crédito, e a interação após mostrar as cartas permite abandonar resultados desfavoráveis antes da liquidação | Desligar até reservar a aposta na entrada e validar saldo no double. Não contar como ralo enquanto o abandono evita perdas |

**Bolsa, simulação de 1.000 dias.** Semente 20261018; dez séries independentes; sete ticks/dia;
`rand(-6,6)` inclusivo; correções sequenciais +3 abaixo de 25, +2 abaixo de 50, -2 acima de
150, -3 acima de 175 e piso 1. Isso é reversão nas bordas, não retorno determinístico à
média 100. `$S_Avg=100` está depois de `end` no OnInit e não inicializa as séries. Os valores
persistidos observados eram 7, 6, 1, 2, 10, 15, 16, 7, 7, 18, com soma positiva, abrindo a
interface sem GM. Mesmo partindo de zero, o relógio acaba produzindo preços positivos, sem uma abertura obrigatória por GM.

Uma posição fixa de 1 M de ações por ticker, sem reinvestir nem empilhar compras, compra
a ≤50 e vende a ≥100 ou ≥150. Supõe capital de até 1 G reservado para as dez posições e
comparecimento a todos os ticks; isso cabe em uma carteira de 2,1 G, mas não é renda de
novato sem capital. Lucro realizado líquido por dia, 1.000 dias divididos pelo total:

| inicio | compra<= | vende>= | z/d realizado | z/d marcado | trades | posicoes abertas | preco max final |
|---|---|---|---|---|---|---|---|
| 0 | 50 | 100 | 5340714 | 5428714 | 191 | 3 | 134 |
| 0 | 50 | 150 | 5402846 | 5606846 | 103 | 5 | 134 |
| 0 | 100 | 101 | 5230967 | 5139967 | 2022 | 6 | 134 |
| 100 | 50 | 100 | 4788720 | 4876720 | 187 | 3 | 133 |
| 100 | 50 | 150 | 4552858 | 4757858 | 95 | 5 | 133 |
| 100 | 100 | 101 | 4367928 | 4276928 | 2048 | 6 | 133 |

Marcação a mercado inclui posições abertas e não equivale a zeny sacado. Uma trajetória
com semente fixa não é a esperança matemática exata nem um intervalo de confiança. Ela
refuta o uso do aviso de “40 M/dia” como valor universal. Carteiras maiores e compras repetidas
podem aumentar a emissão; não se simulou exploração no servidor.

**Caça, cenário condicionado à restauração da base SQL.** Seja N a quantidade de cada mob,
e L a soma de seus quatro níveis: `zeny=N×4×L×60`. No proxy de 360 candidatos extraídos dos
YAML com os filtros do script e cartas entre os drops 3 a 10, 100.000 missões uniformes,
semente 20261018, resultam em média **2.296.997 z**, P5 **1.218.240**, P95 **3.574.080**,
extremos combinatórios **67.200–7.207.200 z**. Não são pagamentos observados nem distribuição
da tabela SQL ausente. Duas conclusões/dia dariam em média 4,594 M/dia/conta, antes do tempo
de caça. Com zeny ÷ 10, 459,4 k/dia. Multi-conta multiplica tudo que usa `#`.

`getmonsterinfo(MOB_BASEEXP)` já devolve a EXP com rate, pois `mob.cpp:5077` aplica 300 x ao
carregar o mob. A divisão por 300 e multiplicação por `.Modifier[0]=300` se cancelam.
`BaseExp += N×SUM(EXP_rateada)/5` passa por `pc.cpp:10466–10472`, sem aplicar novamente 300 x.
Logo o prêmio é **20%** da EXP dos N abates de cada alvo; com os abates, total 1,2×, antes
de bônus individuais, perdas por limite de level-up e efeitos de grupo. “11×” não se confirma.

**Tokens e multi-conta.** O maior prêmio de THQS é 5 tokens, portanto até 5 k por conclusão;
24 conclusões máximas por dia dariam limite de 120 k/conta, hipótese extrema sem duração das
quests. Trocar por equipamentos pode ter valor de revenda maior que 1 k/token, então registrar
a rota escolhida. Bolsa, Kafra, caça, THQS e bilhetes usam variáveis de conta; não são limites
por pessoa. A quest da carta Berzebub usa flag de personagem e permite repetir em alts.

### 1.3 Ralos existentes e um orçamento semanal

Depósito bancário, compra de ações e transferência entre jogadores não destroem riqueza
por si. Juros criam moeda; taxas bancárias destroem moeda. Conversão de zeny em ações só é
imobilização temporária. Computar patrimônio requer somar bancos custom e avaliar posições.

| Ralo | Valor observado | Exemplo semanal, hipótese por jogador |
|---|---|---|
| Sala MVP | 100 k por 60 min + 100 k/MVP; mini-chefe 50 k | Duas sessões e 20 MVPs: 2,2 M; receita de loot fica do outro lado do orçamento |
| Card remover | 200 k +25 k por carta, uma gema amarela e fragmento | Duas remoções de quatro cartas: 600 k |
| Item signer | 3 Gift Boxes +5 k por refino, base zero | Uma assinatura +7: 35 k, além dos itens |
| Bank simples | 500 por depósito/saque | 20 operações: 10 k; principal não é ralo |
| Reset | 5 k status ou skills, 9 k ambos | Quatro resets completos: 36 k |
| Devil Square | 20 k/entrada, base 70 | Sete entradas: 140 k, mas com dez baús por conclusão |
| MVP ladder | 100 k por inscrição do líder, grupo exatamente de dois | Duas inscrições: 200 k; não cobrar ficticiamente de ambos |
| Refino | Weapon 1/2/3/4: 50/200/5 k/20 k por tentativa; Armor: 2 k | 50 tentativas W4 e 50 Armor: 1,1 M, fora minérios |
| Vending | 5%, mínimo 100 M por compra | 0 se só houver compras menores; 5 M numa compra elegível de 100 M |
| Casamento | 1,3 M +1,2 M; divórcio 50 k | 2,5 M por casal uma vez, não receita recorrente semanal |
| Healer/warper custom | 0 | 0 |

Fonte: tabelas de NPC e `db/pre-re/refine.yml`, `conf/battle/items.conf:21–29`.
Sucesso normal até +10: armadura/W4 100/100/100/100/60/40/40/20/20/10%; W3
100/100/100/100/100/60/50/20/20/20%; W2 100/100/100/100/100/100/60/40/20/20%;
W1 100/100/100/100/100/100/100/60/40/20%. Falhas destroem itens acima da segurança;
isso é ralo de itens, não transforma o preço de mercado do item destruído em zeny removido.

O orçamento exemplificado, sem casamento/vending, soma **4,321 M/semana**. Com 14 h/semana
de farm a 4,16 M/h entram 58,24 M; com bolsa no cenário 50→150/início 100, mais 31,87 M;
juros no teto acrescentam 0,7 M. Saldo bruto após esses gastos: **86,49 M/semana**.
Se a caça fosse restaurada sem reequilibrar, acrescentaria cerca de 32,16 M/semana/conta.
Ralos atuais cobrem 4,8% dos 90,81 M de entradas do exemplo sem caça. O prazo aproximado
até 2,1 G seria 24,3 semanas partindo de zero, depois de viabilizar o capital da bolsa.
Esse orçamento não pretende combinar a fase sem capital e a fase de investidor como se
fossem o mesmo dia de jogo.

### 1.4 Recomendação econômica e o que preservar

Primeiro remover emissões sem esforço e rotas de cartas. Depois testar, sem alterar rates
gerais de drop nesta rodada, `vending_tax: 500` com `vending_tax_min: 1000000` em
`server/conf/import/battle_conf.txt`. A unidade 500 significa 5%, não 500% nem 0,5%.
Não é imposto na venda de loot ao NPC e não resolve sozinho a fonte dominante.

Em `warper.txt`, propor cidade/treino até 99 grátis; mapas intermediários 25 k; mapas finais
100 k; acessos de MVP 250 k, com nível 150 no último grupo. Em `healer.txt`, manter cura e
recuperação de SP acessíveis nas cidades, limitar buffs a 99 e não cobrar cura cara de
iniciante. Não contar como ralo eficaz enquanto `quest_warper`, avião, `@warp` ou permissões
de comandos ofereçam caminho equivalente grátis. Auditar permissões é próxima rodada.
Vinte warps finais/dia a 100 k retirariam 2 M/dia, mas a frequência é hipótese e depende dos
atalhos disponíveis. Não financiar o ralo tornando suporte obrigatório para toda ação básica.

Se a sala MVP voltar, começar com aluguel 1 M/h e invocação 1 M para MVPs de entrada,
5 M intermediários, 20 M avançados, cooldown 10 min por conta e base 150. A lista de tiers
deve ser explícita por ID, com cartas raras avançadas fora da sala inicialmente. Com quatro
invocações intermediárias e aluguel, são 21 M retirados por sessão, contra loot a auditar.
Preço sozinho não limita a emissão de cartas nem impede financiar o boss com seu próprio
loot. Não sugerir só subir `rentcost` mantendo a arena gratuita concorrente.

Remover Kaho 5013, Executioner 1169 e itens equivalentes do itemmall é preferível a tabelar
todo o endgame. Alternativa de laboratório: Kaho ≥30 M e Executioner ≥20 M, avaliando
tempo de obtenção e quests paralelas; esses preços não são derivados de mercado existente.
Poison Bottle 678 custa 5 k e amplifica o acesso ao EDP: avaliar 50 k e produção por jogadores
depois do teste de combate. Não banir todos os consumíveis da loja.

O aviso de compra/revenda abaixo do preço pedido **não foi encontrado** em `map.log` nem
`map.log.1.gz` disponíveis. A checagem estática de todas as entradas de `itemmall.txt`, com
Discount de 24% e Overcharge de 24%, encontrou **zero arbitragem positiva** na base atual.
`npc.cpp:4154–4157` usa teste conservador de compra× 0,75 contra venda× 1,24. Não transformar
um aviso preliminar em exploit confirmado. A loja continua problemática pelo acesso barato
e por uma entrada malformada `2247:30000:5206:10000` na L36, a revisar separadamente.

Não mudar inicialmente o teto de zeny, as rates globais 100 x/50 x, os bancos sem juros,
o preço de todo item comum nem o comércio entre jogadores por uma estimativa de emissão.
Não fazer wipe ou correção retroativa: não há população real afetada demonstrada.

## 2. Classes e combate

### 2.1 Pontos e builds comparáveis

No 255: 7.185 pontos normais e 7.237 trans; custo 1→185 = 1.970, custo 1→150 = 1.334.
São 3,67 atributos de 185, não seis. Um trans pode ter três em 185, um em 149, outro em 5
e um em 1, custo 7.236. Um baby pode ter cinco em 150 e um em 88, custo 7.180. Ter cap menor
permite distribuir mais, mas perde patamares quadráticos, HP/SP trans e skills exclusivas.
Os pares `Lord_Knight2`/`Paladin2` e suas versões baby são formas montadas, não quatro novas
classes independentes. Foram mantidos nas 30 entradas para conferir o gerador.

As 90 alocações abaixo são pontos naturais no 255, sem job, equipamento ou buff. Ordem dos
atributos: **STR/AGI/VIT/INT/DEX/LUK**. São referências de custo para PvM, MVP e PvP/WoE,
não builds ótimas nem demonstração de que todas as skills de classes diferentes são iguais.
O preenchimento guloso favorece os atributos em cada papel; ele evidencia o sacrifício,
e não inclui consumíveis, cartas MVP, itens divinos ou homunculus. Diferenças táticas entre
duas colunas podem existir mesmo com os mesmos atributos. Nenhuma build excede o orçamento.

| Classe | PvM | MVP | PvP/WoE | custo |
|---|---|---|---|---|
| Lord_Knight | 185/185/185/5/149/1 | 185/5/185/149/185/1 | 185/185/185/5/149/1 | 7236/7236/7236 |
| High_Priest | 149/5/185/185/185/1 | 5/185/185/185/149/1 | 185/5/185/185/149/1 | 7236/7236/7236 |
| High_Wizard | 149/5/185/185/185/1 | 5/185/185/185/149/1 | 149/5/185/185/185/1 | 7236/7236/7236 |
| Whitesmith | 185/185/185/5/149/1 | 185/149/185/5/185/1 | 185/5/185/149/185/1 | 7236/7236/7236 |
| Sniper | 5/185/185/149/185/1 | 5/185/185/1/185/149 | 5/149/185/1/185/185 | 7236/7236/7236 |
| Assassin_Cross | 185/185/185/5/149/1 | 185/5/185/149/185/1 | 185/185/5/1/149/185 | 7236/7236/7236 |
| Lord_Knight 2 | 185/185/185/5/149/1 | 185/5/185/149/185/1 | 185/185/185/5/149/1 | 7236/7236/7236 |
| Paladin | 185/149/185/5/185/1 | 185/149/185/5/185/1 | 149/5/185/185/185/1 | 7236/7236/7236 |
| Champion | 185/5/149/185/185/1 | 185/149/185/5/185/1 | 185/185/185/5/149/1 | 7236/7236/7236 |
| Professor | 149/5/185/185/185/1 | 5/185/185/185/149/1 | 149/5/185/185/185/1 | 7236/7236/7236 |
| Stalker | 5/185/185/149/185/1 | 185/185/185/5/149/1 | 5/149/185/185/185/1 | 7236/7236/7236 |
| Creator | 149/5/185/185/185/1 | 185/185/185/5/149/1 | 5/1/149/185/185/185 | 7236/7236/7236 |
| Clown | 5/149/185/185/185/1 | 5/185/185/149/185/1 | 5/149/185/185/185/1 | 7236/7236/7236 |
| Gypsy | 5/149/185/185/185/1 | 5/185/185/149/185/1 | 5/185/185/149/185/1 | 7236/7236/7236 |
| Paladin 2 | 185/149/185/5/185/1 | 185/149/185/5/185/1 | 149/5/185/185/185/1 | 7236/7236/7236 |
| Baby_Knight | 150/150/150/88/150/150 | 150/88/150/150/150/150 | 150/150/150/150/150/88 | 7180/7180/7180 |
| Baby_Priest | 88/150/150/150/150/150 | 150/88/150/150/150/150 | 150/150/150/150/150/88 | 7180/7180/7180 |
| Baby_Wizard | 88/150/150/150/150/150 | 150/88/150/150/150/150 | 150/150/150/150/150/88 | 7180/7180/7180 |
| Baby_Blacksmith | 150/150/150/88/150/150 | 150/88/150/150/150/150 | 150/150/150/150/150/88 | 7180/7180/7180 |
| Baby_Hunter | 88/150/150/150/150/150 | 150/88/150/150/150/150 | 150/150/150/150/150/88 | 7180/7180/7180 |
| Baby_Assassin | 150/150/150/88/150/150 | 150/88/150/150/150/150 | 150/150/150/150/150/88 | 7180/7180/7180 |
| Baby_Knight 2 | 150/150/150/88/150/150 | 150/88/150/150/150/150 | 150/150/150/150/150/88 | 7180/7180/7180 |
| Baby_Crusader | 150/150/150/88/150/150 | 150/88/150/150/150/150 | 150/150/150/150/150/88 | 7180/7180/7180 |
| Baby_Monk | 150/150/150/88/150/150 | 150/88/150/150/150/150 | 150/150/150/150/150/88 | 7180/7180/7180 |
| Baby_Sage | 88/150/150/150/150/150 | 150/88/150/150/150/150 | 150/150/150/150/150/88 | 7180/7180/7180 |
| Baby_Rogue | 150/150/150/88/150/150 | 150/88/150/150/150/150 | 150/150/150/150/150/88 | 7180/7180/7180 |
| Baby_Alchemist | 88/150/150/150/150/150 | 150/88/150/150/150/150 | 150/150/150/150/150/88 | 7180/7180/7180 |
| Baby_Bard | 88/150/150/150/150/150 | 150/88/150/150/150/150 | 150/150/150/150/150/88 | 7180/7180/7180 |
| Baby_Dancer | 88/150/150/150/150/150 | 150/88/150/150/150/150 | 150/150/150/150/150/88 | 7180/7180/7180 |
| Baby_Crusader 2 | 150/150/150/88/150/150 | 150/88/150/150/150/150 | 150/150/150/150/150/88 | 7180/7180/7180 |

### 2.2 HP/SP no 99, 150 e 255

Modelo sem equipamento, passivas ou buffs: usar `BaseHp/BaseSp` oficiais onde existam,
pois `HP_SP_TABLES` está ativo. Para níveis sem tabela explícita, o fallback de
`pc.cpp:13710–13783` é:

```text
H0(L) = 35 + floor(L×HpIncrease/100) + SUM(i=2..L, floor(HpFactor×i/100 + 0,5))
S0(L) = 10 + floor(L×SpIncrease/100) + SUM(i=2..L, floor(SpFactor×i/100 + 0,5))
HP = floor(H0×(1+VIT_total/100)×1,25) para trans; baby sem ×1,25
SP = floor(S0×(1+INT_total/100)×1,25) para trans; baby sem ×1,25
```

`status.cpp:3509–3608,4352–4371` aplica atributos, fator trans e caps. Na tabela,
VIT/INT **totais** fixos em 185 para trans e 150 para baby isolam a classe. VIT 185 no 99
é uma sensibilidade teórica e não uma alocação legal com o orçamento de pontos do nível 99;
não usar a tabela como build iniciante. SP com INT 185 também não é o SP de toda build física.

| Classe | Hf/Hi/Si | HP 99 | HP 150 | HP 255 | SP 99/150/255 |
|---|---|---|---|---|---|
| Lord_Knight | (150, 500, 300) | 28.421 | 63.441 | 179.307 | 1.093/1.638/2.760 |
| High_Priest | (75, 500, 800) | 15.154 | 33.120 | 91.987 | 2.857/4.310/7.303 |
| High_Wizard | (55, 500, 900) | 11.592 | 24.998 | 68.642 | 3.209/4.845/8.211 |
| Whitesmith | (90, 500, 400) | 17.773 | 39.130 | 109.365 | 1.446/2.173/3.669 |
| Sniper | (85, 500, 400) | 16.882 | 37.103 | 103.526 | 1.446/2.173/3.669 |
| Assassin_Cross | (110, 500, 400) | 21.300 | 47.199 | 132.614 | 1.446/2.173/3.669 |
| Lord_Knight 2 | (150, 500, 300) | 28.421 | 63.441 | 179.307 | 1.093/1.638/2.760 |
| Paladin | (110, 700, 470) | 22.005 | 48.268 | 134.430 | 1.692/2.547/4.303 |
| Champion | (90, 650, 470) | 18.300 | 39.932 | 110.726 | 1.692/2.547/4.303 |
| Professor | (75, 500, 700) | 15.154 | 33.120 | 91.987 | 2.504/3.776/6.394 |
| Stalker | (85, 500, 500) | 16.882 | 37.103 | 103.526 | 1.799/2.707/4.577 |
| Creator | (90, 500, 400) | 17.773 | 39.130 | 109.365 | 1.446/2.173/3.669 |
| Clown | (75, 300, 600) | 14.449 | 32.051 | 90.170 | 2.151/3.241/5.486 |
| Gypsy | (75, 300, 600) | 14.449 | 32.051 | 90.170 | 2.151/3.241/5.486 |
| Paladin 2 | (110, 700, 470) | 22.005 | 48.268 | 134.430 | 1.692/2.547/4.303 |
| Baby_Knight | (150, 500, 300) | 19.945 | 44.520 | 125.830 | 767/1.150/1.937 |
| Baby_Priest | (75, 500, 800) | 10.635 | 23.242 | 64.552 | 2.005/3.025/5.125 |
| Baby_Wizard | (55, 500, 900) | 8.135 | 17.542 | 48.170 | 2.252/3.400/5.762 |
| Baby_Blacksmith | (90, 500, 400) | 12.472 | 27.460 | 76.747 | 1.015/1.525/2.575 |
| Baby_Hunter | (85, 500, 400) | 11.847 | 26.037 | 72.650 | 1.015/1.525/2.575 |
| Baby_Assassin | (110, 500, 400) | 14.947 | 33.122 | 93.062 | 1.015/1.525/2.575 |
| Baby_Knight 2 | (150, 500, 300) | 19.945 | 44.520 | 125.830 | 767/1.150/1.937 |
| Baby_Crusader | (110, 700, 470) | 15.442 | 33.872 | 94.337 | 1.187/1.787/3.020 |
| Baby_Monk | (90, 650, 470) | 12.842 | 28.022 | 77.702 | 1.187/1.787/3.020 |
| Baby_Sage | (75, 500, 700) | 10.635 | 23.242 | 64.552 | 1.757/2.650/4.487 |
| Baby_Rogue | (85, 500, 500) | 11.847 | 26.037 | 72.650 | 1.262/1.900/3.212 |
| Baby_Alchemist | (90, 500, 400) | 12.472 | 27.460 | 76.747 | 1.015/1.525/2.575 |
| Baby_Bard | (75, 300, 600) | 10.140 | 22.492 | 63.277 | 1.510/2.275/3.850 |
| Baby_Dancer | (75, 300, 600) | 10.140 | 22.492 | 63.277 | 1.510/2.275/3.850 |
| Baby_Crusader 2 | (110, 700, 470) | 15.442 | 33.872 | 94.337 | 1.187/1.787/3.020 |

Caps atuais de HP: 330 k até 99, 660 k até 150, 1,1 M acima de 150. **Nenhum morde o modelo
sem equipamento.** O LK 255 precisa de aproximadamente 6,13× o HP tabulado para chegar a
1,1 M; Sniper, 10,63×. Com VIT natural 185 e job 70, LK tem VIT total 193 e HP **184.340**;
Sniper tem VIT total 188 e HP **104.616**, explicando o “105 k” anterior. Champion com INT
natural 185 +7 de job tem SP **4.409**, sem equipamento. Trust, Berserk, Tao Gunka,
cartas/combos e itens divinos podem alterar bastante os resultados; não foram ocultados em
um suposto valor universal de HP. Preservar caps inicialmente evita nerfar tanques sem evidência.

### 2.3 ASPD e conjuração

Pre-re em `status.cpp:2404–2414`: `amotion = delay - floor(delay×(4×AGI+DEX)/1000)`;
`ASPD = 200 - amotion/10`, com truncamentos intermediários. Intervalo de ataque é
`2×amotion` ms; 197 permite **16,67 ataques/s**, 193 permite **7,14**, 190 permite **5**.
Ir de 197 para 193 reduz o teto de ataques em 57,14%, não em 2%. Não extrapolar esse fator
para toda skill, porque aftercast, cooldown, animação, acerto e recursos também limitam.

Com AGI/DEX **totais** 185, arco Sniper fica em 195,5, katar em 196,2, espada de duas mãos
LK em 195,8 e machado WS em 195,1, sem buffs. Entretanto o pedido usa atributos **naturais**
185: somar bônus de job 70 muda a conclusão. Todas as combinações abaixo batem o cap 197
sem pot, equipamento ou buff. Não se adicionou sequer Owl's Eye do arqueiro nem Bless/Agi.

| Classe | arma | AGI/DEX com job 70 | amotion sem cap | ASPD final sem buff |
|---|---|---|---|---|
| Lord_Knight | 2hSword | 193/194 | 19 | 197,0 |
| Lord_Knight | 1hSpear | 193/194 | 21 | 197,0 |
| Lord_Knight | 2hAxe | 193/194 | 24 | 197,0 |
| High_Priest | Staff | 193/194 | 21 | 197,0 |
| High_Priest | Book | 193/194 | 21 | 197,0 |
| High_Wizard | Staff | 193/194 | 22 | 197,0 |
| Whitesmith | 2hAxe | 192/197 | 23 | 197,0 |
| Sniper | Bow | 196/199 | 11 | 197,0 |
| Assassin_Cross | Katar | 200/195 | 3 | 197,0 |
| Lord_Knight 2 | 2hSword | 193/194 | 19 | 197,0 |
| Lord_Knight 2 | 1hSpear | 193/194 | 21 | 197,0 |
| Lord_Knight 2 | 2hAxe | 193/194 | 24 | 197,0 |
| Paladin | 2hSword | 193/193 | 20 | 197,0 |
| Paladin | 1hSpear | 193/193 | 21 | 197,0 |
| Paladin | 2hAxe | 193/193 | 25 | 197,0 |
| Champion | Staff | 194/195 | 17 | 197,0 |
| Champion | Knuckle | 194/195 | 14 | 197,0 |
| Professor | Staff | 194/196 | 18 | 197,0 |
| Professor | Book | 194/196 | 16 | 197,0 |
| Stalker | Bow | 196/197 | 13 | 197,0 |
| Creator | 2hAxe | 191/199 | 26 | 197,0 |
| Clown | Bow | 197/199 | 9 | 197,0 |
| Clown | Musical | 197/199 | 8 | 197,0 |
| Gypsy | Bow | 199/201 | 2 | 197,0 |
| Gypsy | Whip | 199/201 | 2 | 197,0 |
| Paladin 2 | 2hSword | 193/193 | 20 | 197,0 |
| Paladin 2 | 1hSpear | 193/193 | 21 | 197,0 |
| Paladin 2 | 2hAxe | 193/193 | 25 | 197,0 |

Isso exige maximizar AGI e DEX, disputando o orçamento com STR, VIT e INT. As builds da seção
2.1 mostram a troca. Sniper pode manter DEX/AGI/VIT; SinX físico precisa escolher entre DEX
alta e o quarto atributo. Com healer e Kaho, chegar ao teto fica ainda mais barato. Baby a
AGI/DEX totais 150 deixa 25% do delay: arco com delay 600 resulta em ASPD 185, antes de job,
equipamento e buffs; portanto os dois grupos não saturam igualmente sem ajuda.

`conf/battle/skill.conf:51` fixa `castrate_dex_scale: 150`. Pre-re em `skill.cpp:10136–10141`
zera o cast afetado por DEX quando DEX total ≥150. Com 185, não é “quase instantâneo”:
é zero nessa parcela. Casts que ignoram DEX, delays, cooldowns, SP, gemas e posicionamento
continuam existindo. Bragi, Safety Wall, Pneuma, Lex e Dispel mantêm valor; o healer não
substitui o Priest em combate móvel nem o Professor em controle.

### 2.4 Dano de referência, PvP e ameaça dos mobs

Físico básico pre-re: `STR + floor(STR/10)^2 + floor(DEX/5) + floor(LUK/5)`; para arco,
DEX ocupa a posição do atributo de ataque. Acrescentar arma e modificadores. Em atributos
totais 185, com secundário 149 e LUK 1, dá 538 de status ATK; arma de ATK 200 dá aproximação
de **738**, antes de variação, tamanho, refino e passivas. MATK em INT total 185 é
**861–1.554**; uma hipótese explícita de bônus MATK +15% gera **990–1.787**, não ATK da arma
somado à magia. Fonte: `status.cpp:2424–2516` e scripts dos itens na tabela `items`.

Para o quadro seguinte, usar ATK arredondado de 800, MATK médio 1.388, acerto 100%, elemento
neutro e tamanho 100%. Físico contra mob: `(800×(100-DEF)/100) - softDEF`; softDEF esperado
é VIT + metade do intervalo aleatório de `(VIT/20)^2`, conforme `battle.cpp:4824–4835`.
Magia é `MATK×(100-MDEF)/100 - INT_mob` como aproximação. Não se simularam cada skill e
ordem de todas as bonificações do emulador; as faixas são suficientes para comparar escalas.

| Mob | DEF/MDEF | VIT | INT | Físico básico aprox. | Magia 1× aprox. |
|---|---|---|---|---|---|
| PORING | 0/5 | 1 | 0 | 799 | 1319 |
| SLEEPER | 49/35 | 100 | 57 | 296 | 845 |
| ANUBIS | 25/31 | 10 | 82 | 590 | 876 |
| SKOGUL | 20/15 | 70 | 50 | 566 | 1130 |
| NECROMANCER | 0/40 | 1 | 190 | 799 | 643 |
| SEYREN | 63/12 | 72 | 20 | 220 | 1201 |
| KASA | 23/70 | 31 | 200 | 585 | 216 |
| SALAMANDER | 65/50 | 44 | 45 | 234 | 649 |
| CENTIPEDE | 40/25 | 30 | 5 | 450 | 1036 |
| BRADIUM_GOLEM | 78/22 | 82 | 25 | 86 | 1058 |

| Skill | Modelo pre-re e dano aproximado no alvo jogador | Implicação |
|---|---|---|
| Asura 5 | `(800×(8+4409/10)+1000)×0,504 = 181.500` | Ultrapassa Sniper de 104.616 HP em um uso no cenário; a redução WoE de skill física 60% leva a ~108.900, ainda limítrofe |
| Sonic Blow 10 + Sonic Accel | 880% total, oito golpes visuais; ATK 800, DEF 40 e softDEF médio 233 dá ~1,1 k–2,1 k conforme a aproximação da ordem de defesa. EDP5 multiplica a parcela elegível por 4 | Sozinho está muito abaixo de 105 k nesse equipamento; cards/elemento/Lex e itens divinos precisam de ensaio antes de concluir one-shot |
| Double Strafe 10 | 190% por golpe × 2, total 380%; com ATK 800 e as mesmas defesas, ordem de grandeza 0,7 k–0,9 k | Alta frequência é relevante; não demonstra matar 105 k em um uso |
| Storm Gust 10 | 500% por onda; MATK médio 1.388, MDEF 30, softMDEF aproximada 150; ~4,1 k antes de redução racial, ~2,6 k após 30% Thara e 10% beret, por onda | Não somar várias ondas como golpe único; congelamento e elemento alteram as seguintes |
| Acid Demonstration 10 | `floor(7×185×185²/(10×(185+185)))/2`, por hit, × 10 = ~59,9 k contra jogador antes de reduções adicionais | VIT alta aumenta o dano recebido. É candidato a ensaio junto de Asura, sem presumir 105 k num uso |

O fator 0,504 para dano físico neutro é Thara 30% × beret 10% × Raydric 20%, isto é,
0,7× 0,9× 0,8. Raydric não deve reduzir automaticamente Storm Gust de água nem todo ataque
elemental. DEF física 40, VIT total 185: softDEF médio é aproximadamente 233, intervalo
147–319; arredondamentos não mudam a conclusão de escala. MATK e habilidades de múltiplos
hits usam suas próprias divisões. Asura ignora DEF, mas sofre reduções e contramedidas como
Ghostring, Devotion, Safety Wall conforme o contexto e flags. Não é chance de vitória medida.

Fontes específicas: `skills/acolyte/asurastrike.cpp:57–64`,
`skills/thief/sonicblow.cpp:15–27`, `skills/archer/doublestrafe.cpp:9–11`,
`skills/mage/stormgust.cpp:24–32`, `battle.cpp:6463–6470`, `skill_db.yml` nos IDs 46, 89,
136, 271 e 490. O estudo não promete fidelidade de um emulador completo de combate Python.

| id/nome | HP | ATK 2 | DEF/MDEF | TTK a 10 k/30 k DPS |
|---|---|---|---|---|
| 1039/BAPHOMET | 668.000 | 4.040 | 35/45 | 66,8/22,3 |
| 1086/GOLDEN_BUG | 126.000 | 1.145 | 60/45 | 12,6/4,2 |
| 1157/PHARAOH | 445.997 | 3.015 | 67/70 | 44,6/14,9 |
| 1272/DARK_LORD | 720.000 | 3.320 | 30/70 | 72,0/24,0 |
| 1373/LORD_OF_DEATH | 603.383 | 4.232 | 77/73 | 60,3/20,1 |
| 1583/TAO_GUNKA | 193.000 | 1.770 | 20/20 | 19,3/6,4 |
| 1751/RANDGRIS | 3.567.200 | 9.980 | 25/42 | 356,7/118,9 |
| 1832/IFRIT | 7.700.000 | 17.000 | 40/50 | 770,0/256,7 |
| 1874/BEELZEBUB_ | 6.666.666 | 13.410 | 40/40 | 666,7/222,2 |

TTK = HP/DPS **efetivo**, sem tempo de andar, ativar habilidades ou tratar mecânicas. Os
MVPs de entrada podem cair em segundos/dezenas de segundos; Ifrit, Beelzebub e Randgris
não são honestamente classificados como “todos caem em segundos”. S_NYDHOG 2022 chega a
49.000 de ATK 2; contra HP 104.616, são só 2,14 golpes máximos brutos, antes de defesa ou
skills. O maior ATK 2 normal com spawn oficial e EXP é Duneyrr, **19.000**, não 16.000.
WOOMAWANG_ chega a 20 k na base completa, mas não é uma referência de spawn oficial comum.

`mob_skill_db.txt:186–207` dá a Baphomet Earthquake 5, Power Up, Hell Judgement e quebra de
armadura; `1268–1282` dá a Dark Lord Dark Blessing, Meteor e quebra de elmo;
`3936–3970` inclui Power Up/Assumptio/Dispel de Randgris. Logo ATK 2 isolado não mede risco.
Bio 3 também possui Spiral Pierce/Power Up (`2827–2841`). Não enfraquecer mobs por comparar
somente o ataque básico contra HP máximo. Earthquake em solo e múltiplos alvos exige teste.

### 2.5 Papel por classe e recomendação sem alterar src

| Grupo | PvM/MVP provável | PvP/WoE provável | Limite da conclusão |
|---|---|---|---|
| LK/Paladin | HP alto, mobbing, dano físico e proteção; Paladin ganha com Devotion | Tanque e proteção; Sacrifice exige teste com HP ampliado | HP alto não prova DPS alto; ranged/elementos/mecânicas importam |
| Sniper/SinX | Fortes candidatos a farm/solo pelo teto de ataques; EDP barato reforça SinX | Sniper pressão sustentada; SinX burst/posicionamento | FLEE/HIT, distância e equipamentos podem inverter o resultado |
| WS/Creator | WS auto/cart e gasto por dano; Creator ganha contra VIT alta | AD e proteção química relevantes | Consumo, homunculus e acesso a garrafas precisam ser medidos |
| HW/Professor | Área, controle e elementos; cast por DEX facilmente zerado | Land Protector, Dispel e controle preservam função | Aftercast, MDEF e imunidades impedem equiparar cast zero a DPS infinito |
| HP/Champion | HP oferece suporte em grupo e sustento; Champion grande burst de SP | HP protege; Asura é principal risco de uso único | Healer reduz demanda fora de combate, não elimina todas as funções de HP |
| Stalker/Clown/Gypsy | Versatilidade, cópia e buffs; menos explosão solo em alguns cenários | Strip, Bragi e controle são relevantes | Não chamar de inviáveis por uma tabela de autoattack |
| Babies | Cinco atributos em 150, HP/SP ~70,2% do trans na comparação controlada | Menos skills exclusivas trans e patamares de atributos; opção de desafio | Algumas funções de suporte continuam úteis, sem promessa de paridade |

Proposta de ensaio: `max_aspd: 193`, com `max_third_aspd` e `max_extended_aspd` coerentes em
`server/conf/import/battle_conf.txt`; manter HP e `pk_mode: 0`. No 197 todo ataque de 1 k
efetivo dá 16,67 k DPS; no 193 dá 7,14 k. Não aprovar esse nerf de 57% sem medir autoattack e
tempo por faixa. O modo PK global não é requisito de PvP/WoE; não ligá-lo como balanceamento.

O arquivo suportado neste commit é **`db/import/skill_damage_db.txt`**, não
`skill_damage_db.yml`. A base de import atual só tem comentários; parser em
`skill.cpp:16173–16274`. O ajuste é percentual aditivo: -50 reduz à metade; 50 aumenta 50%.
Proposta inicial isolada para laboratório:

```text
MO_EXTREMITYFIST,BL_PC,6,-50,0,0,0
```

Máscara 6 = PvP + GvG, redução contra jogadores; não alterar o dano de MVP/PvM. BG é bit 8,
portanto usar 14 apenas se a decisão incluir battleground. Na referência, Asura passaria
a ~90,8 k PvP e ~54,5 k WoE. AD e Sacrifice são os outros dois candidatos a medir; não escrever
três nerfs arbitrários antes de verificar dano por uso, consumo e sobrevida. Manter Sonic
Blow, Double Strafe e Storm Gust inicialmente. Não alterar `src`, caps de atributos, cast
global ou todas as skills de uma classe ao mesmo tempo.

## 3. Progressão e mapas

### 3.1 Validar a meta e o caminho que a sustenta

Valores exatos de `docs/progressao.csv` e `extended_curve`, sem rerodar o gerador no repo:

| faixa | EXP | h 300/h alvo |
|---|---|---|
| 1->99 | 1.212.492.555 | 1,01 |
| 99->150 | 8.729.000.000 | 9.699 |
| 150->200 | 31.414.000.000 | 10.471 |
| 200->255 | 205.020.000.000 | 22,78 |
| 254->255 | 15.700.000.000 | 1.744 |

No total, 99→255 custa **245.163.000.000**, e o caminho trans 1→255 soma
**246.375.492.555** por passagem, sem incluir a primeira vida até rebornar. As 44 h assumem
referências de EXP/abate diferentes por faixa e ignoram o tempo de reborn/quest de classe.
O argumento “a 300 abates/h” só fecha se a rota entregar os valores escolhidos.

| mapa | n oficial/final | hp medio | M exp/kill | z/kill | DPS | kills/h | G exp/h | M z/h |
|---|---|---|---|---|---|---|---|---|
| prt_sewb 2 | 220/2.200 | 231 | 0,01 | 394 | 500 | 425 | 0.004 | 0.168 |
| prt_sewb 3 | 210/2.100 | 330 | 0.031 | 601 | 500 | 416 | 0.013 | 0,25 |
| iz_dun 02 | 196/1.960 | 2.541 | 0.108 | 3.020 | 500 | 275 | 0,03 | 0.831 |
| hu_fild 04 | 223/2.230 | 5.367 | 0.477 | 2.467 | 1500 | 311 | 0.148 | 0.767 |
| hu_fild 07 | 220/2.200 | 5.989 | 0.502 | 3.139 | 1500 | 300 | 0.151 | 0.942 |
| alde_dun 03 | 196/1.960 | 4.821 | 0.607 | 2.183 | 1500 | 321 | 0.195 | 0.701 |
| juperos_01 | 285/2.850 | 10.535 | 1.303 | 5.582 | 5000 | 356 | 0.464 | 1.988 |
| juperos_02 | 315/3.150 | 12.691 | 1,4 | 5.450 | 5000 | 342 | 0.478 | 1.862 |
| abbey 01 | 258/2.580 | 23.723 | 2.844 | 1.312 | 5000 | 282 | 0.803 | 0,37 |
| man_fild 02 | 110/550 | 44.052 | 6,14 | 821 | 5000 | 214 | 1.315 | 0.176 |
| spl_fild 01 | 110/550 | 30.448 | 5.934 | 879 | 5000 | 256 | 1.516 | 0.225 |
| in_sphinx 4 | 89/89 | 12.717 | 2.157 | 4.055 | 5000 | 341 | 0.736 | 1.385 |
| in_sphinx 5 | 117/117 | 9.637 | 1.582 | 8.781 | 5000 | 363 | 0.574 | 3.184 |
| ve_fild 06 | 4/4 | 504 | 0.075 | 906 | 15000 | 30 | 0.002 | 0.027 |
| odin_tem 03 | 102/102 | 140.274 | 9.711 | 7.769 | 15000 | 207 | 2.015 | 1.612 |
| abbey 03 | 116/116 | 119.414 | 8.496 | 1.155 | 15000 | 226 | 1.916 | 0,26 |
| tha_t 09 | 44/44 | 34.593 | 6.745 | 41.115 | 15000 | 349 | 2.356 | 14.362 |
| lhz_dun 03 | 312/312 | 67.425 | 29.527 | 11.834 | 30000 | 351 | 10.373 | 4.157 |
| thor_v 01 | 96/96 | 67.949 | 13.315 | 3.515 | 30000 | 351 | 4,67 | 1.233 |
| thor_v 03 | 125/125 | 92.889 | 20.224 | 3.882 | 30000 | 324 | 6.561 | 1.259 |
| moc_fild 21 | 325/325 | 96.538 | 9.621 | 2.448 | 30000 | 321 | 3.088 | 0.786 |
| moc_fild 22 | 205/205 | 171.366 | 17,32 | 2.531 | 30000 | 263 | 4.547 | 0.664 |
| abyss_03 | 123/123 | 42.372 | 5.668 | 10.669 | 30000 | 382 | 2.168 | 4.081 |

As três primeiras rotas modelam DPS 500, seguintes três DPS 1.500, Juperos/Abbey 01/Manuk/
Splendide/Sphinx DPS 5.000, Odin/Abbey 03/Thanatos DPS 15.000 e destinos finais DPS 30.000.
`ve_fild06` na tabela é um controle negativo: não é um destino de Sleeper. Manter a linha
expõe a importância de verificar o mapa pelo ID, em vez de associar nome e rota por memória.
Spawn total inclui mini-bosses e regulares boss-class, exclui MVP; no bio 3 são 312, não 306.

| Faixa | Mobs de referência, exp 300/hp | Horas no modelo | Leitura da meta |
|---|---|---|---|
| 1→99 | Rotas iniciais de 0,01 a 0,607 M/abate, e depois Juperos/Anubis | O total de 1,212 G levaria 6,2 h se toda a EXP viesse do mix de alde_dun 03; Anubis direcionado a ~231/h e 8,4 M daria 0,63 h só de orçamento de EXP | A meta 1 h exige trocar de mapa cedo; não vem de ficar nos mapas 1–60 |
| 99→150 | Anubis 8,4 M/38 k HP; Sleeper 1,0809 M/8.237; Venatu 1,2 M/8.900 | Juperos 02:18,3 h; Abbey 01:10,9 h; Anubis direcionado a DPS 5 k+8 s:4,50 h | “Anubis/Sleeper/Juperos =3 M” não representa os três; seleção do alvo muda a faixa em 4× |
| 150→200 | Skogul 8,286 M/87.544; Necromancer 13,5 M/98 k; Skeggiold 27,33 M/295.200 | Mix Odin 03:15,6 h; Abbey 03:16,4 h; Thanatos 09:13,3 h | A meta 10 h precisa de foco nos mobs valiosos, AoE, mais DPS ou grupo |
| 200→255 | Bio 3 regulares 30 M; Kasa 14,7 M; Salamander 21,6 M; encarnações de Morroc conforme Q02 | Bio 3:19,8 h; Thor 03:31,2 h; Morroc 22:45,1 h; Abyss 03:94,6 h | “Thor/Morroc =30 M por abate” superestima o mix. Bio 3 concentra a rota eficiente |

Tempos calculados por EXP da faixa / EXP/h da tabela. Não chamar essas horas de “reais”.
Não se simulou acurácia de cada classe em todos os mapas nem mortes, que ampliam os tempos.
Party e AoE podem reduzi-los. O modelo tem limite de 450 abates/h quando o DPS tende ao
infinito e se mantêm 8 s de busca por alvo, mostrando que o deslocamento também manda.

Monstros principais, valores e agressividade recuperada do YAML/AI:

| id/nome | lv | HP | EXP 300 | ATK 2 | DEF/MDEF | agressivo | z/kill |
|---|---|---|---|---|---|---|---|
| 1098/ANUBIS | 75 | 38.000 | 8.400.000 | 1.697 | 25/31 | sim | 1.232 |
| 1386/SLEEPER | 67 | 8.237 | 1.080.900 | 789 | 49/35 | sim | 2.944 |
| 1634/SEYREN | 91 | 88.402 | 30.000.000 | 2.530 | 63/12 | sim | 40.382 |
| 1635/EREMES | 87 | 60.199 | 30.000.000 | 2.320 | 23/12 | sim | 3.292 |
| 1637/MAGALETA | 90 | 61.282 | 30.000.000 | 2.053 | 35/60 | sim | 3.071 |
| 1638/SHECIL | 82 | 58.900 | 30.000.000 | 1.854 | 25/15 | sim | 8.889 |
| 1639/KATRINN | 92 | 47.280 | 30.000.000 | 1.697 | 10/74 | sim | 4.137 |
| 1676/VENATU_1 | 72 | 8.900 | 1.200.000 | 1.400 | 30/20 | sim | 5.994 |
| 1752/SKOGUL | 70 | 87.544 | 8.286.000 | 1.930 | 20/15 | sim | 9.761 |
| 1754/SKEGGIOLD | 81 | 295.200 | 27.330.000 | 2.020 | 12/24 | sim | 12.167 |
| 1831/SALAMANDER | 91 | 97.934 | 21.600.000 | 10.860 | 65/50 | sim | 1.291 |
| 1833/KASA | 85 | 80.375 | 14.700.000 | 3.500 | 23/70 | sim | 4.800 |
| 1870/NECROMANCER | 88 | 98.000 | 13.500.000 | 4.000 | 0/40 | sim | 1.459 |
| 1986/TATACHO | 106 | 39.500 | 7.110.000 | 11.000 | 20/17 | não | 702 |
| 1987/CENTIPEDE | 110 | 45.662 | 8.219.100 | 16.000 | 40/25 | sim | 706 |
| 1989/HILLSRION | 105 | 34.600 | 6.228.000 | 5.500 | 28/15 | sim | 1.117 |
| 1992/CORNUS | 108 | 41.220 | 9.256.200 | 13.000 | 35/80 | não | 935 |
| 1993/NAGA | 111 | 46.708 | 9.108.000 | 8.800 | 38/15 | sim | 681 |
| 1994/LUCIOLA_VESPA | 104 | 32.600 | 4.890.000 | 9.900 | 29/5 | sim | 4.516 |
| 2017/RATA | 107 | 216.600 | 21.003.600 | 15.000 | 32/52 | sim | 3.049 |
| 2018/DUNEYRR | 107 | 265.100 | 24.909.000 | 19.000 | 39/35 | sim | 3.609 |
| 2019/ANCIENT_TREE | 102 | 30.030 | 3.306.000 | 17.400 | 39/43 | sim | 682 |
| 2023/DARK_SHADOW | 114 | 42.900 | 6.300.000 | 15.000 | 35/44 | sim | 5.764 |
| 2024/BRADIUM_GOLEM | 101 | 45.200 | 4.200.000 | 13.000 | 78/22 | sim | 962 |

### 3.2 Muralha 254, multi-level e job

254→255 custa **15,7 G**. Um bio 3 regular de 30 M exige `ceil(15.700/30)=524` abates,
ou 1,747 h a 300/h; divisão contínua dá 1,744 h. É 7,66% de toda a faixa 200→255 num nível.
O nível 253 custa 7,56 G e o 254 é o dobro da base sem muralha de aproximadamente 7,85 G.
Isso é uma parede perceptível, mas não dias inteiros de bio 3 no modelo. Com mortes de 1%
da EXP exigida, cada morte no 254 apaga 157 M, aproximadamente 5,23 abates de 30 M.
`death_penalty_type:1`, `death_penalty_base/job:100` usam centésimos de porcento; não 100%.

`multi_level_up_base:99` é limiar de nível, não quantidade de níveis. `pc.cpp:8255` limita
o excedente quando o personagem já chegou ao limiar; uma recompensa grande pode perder EXP
que atravessaria níveis. Não resolve a falta de conteúdo nem acelera a muralha. Proposta:
preservar o limiar e os fatores de TIERS; se o tempo 254→255 P50 ultrapassar 2 h de atividade
com a rota final aprovada, avaliar `MILESTONES[254]:2.0→1.5`, reduzindo 3,925 G, cerca de 131
abates de 30 M. Não cortar toda a curva por um único degrau.

Job trans 1→70 exige **1.084.674.396** de EXP, baby segunda classe 1→50 exige **16.488.271**.
A300 x, com 30 k de EXP job original/abate, são 121 e 2 abates respectivamente; a 300/h são
24,2 min e 24 s. Com mais job EXP/abate ou AoE, trans pode terminar antes. Não é literal
que todas as classes tenham job 70 nem que qualquer mapa dê job 70 em poucos segundos.
`multi_level_up_job:0` não impõe limiar. Dado `skill_tree.yml`, ter pontos cedo abre as
skills dessa classe, sem conceder skills de outra classe ou ignorar pré-requisitos.

Não reduzir `job_exp_rate` por princípio: trans levaria 121 min a 60 x no mesmo cenário, e
baby continuaria muito rápido. Proposta opcional de teste 30–60 x só se a meta escolhida for
1–2 h para o job trans; preservar 300 x enquanto a promessa do servidor for aprender a classe
cedo. Registrar base/job na entrada e saída de sessões para decidir.

### 3.3 Conteúdo 100+, babies e equipamentos

Definição auditável: `level>100`, `class='Normal'`, `is_mvp=0`, `base_exp>0`. São **11**
entradas no site, **nove** com spawn no conjunto oficial estático carregado. Sem o filtro
de EXP, clones de invocação e mobs sem recompensa inflam a contagem. A alegação de sete
corresponde a subconjuntos antigos e não se confirma como total atual.

| Mob | Nível | HP | EXP 300 | Destinos oficiais nesta coleta |
|---|---|---|---|---|
| Tatacho | 106 |39.500 |7.110.000 | man_fild 02/03 |
| Centipede |110 |45.662 |8.219.100 | man_fild 01/02/03 |
| Hillsrion |105 |34.600 |6.228.000 | man_fild 01/03 |
| Cornus |108 |41.220 |9.256.200 | spl_fild 01/03 |
| Naga |111 |46.708 |9.108.000 | spl_fild 01/03 |
| Luciola Vespa |104 |32.600 |4.890.000 | spl_fild 02/03 |
| Rata |107 |216.600 |21.003.600 | nyd_dun 01 |
| Duneyrr |107 |265.100 |24.909.000 | nyd_dun 01 |
| Ancient Tree |102 |30.030 |3.306.000 | Sem spawn estático neste conjunto; pode depender de conteúdo por script |
| Dark Shadow |114 |42.900 |6.300.000 | Sem spawn estático neste conjunto; pode depender de conteúdo por script |
| Bradium Golem |101 |45.200 |4.200.000 | man_fild 02 |

Não há penalidade renewal de nível habilitada no build pre-re, então o 200+ pode continuar
matando monstros de nível 75–99. O problema é variedade/recompensa, não uma proibição por
level. Thor, bio 3, Abyss e Odin são destinos existentes; Manuk, Splendide, Nydhogg e Thanatos
também existem. O custo/EXP por HP e deslocamento concentra a rota eficiente em poucos
deles. Arena e sala MVP oferecem atalho e loot de chefe, reduzindo ainda mais o incentivo
a explorar os mapas, mesmo quando sua EXP/h não for a melhor.

Baby não precisa rebornar, mas seu job de segunda classe termina em 50 e não ganha as skills
trans. Em 255 usa 7.185 pontos e cap 150: cinco atributos fechados contra três trans. Compara-se
HP/SP controlado: `2,5/(2,85×1,25)=70,18%`; o dano de status com atributo principal 150 é
150+225 antes de secundários, contra 185+324 em 185, aproximadamente 73,67%. Equipamentos,
bônus de job e distribuição modificam esses quocientes. Preservar baby como opção distinta;
não igualar cap a 185 silenciosamente nem prometer equivalência em MVP solo.

Q04 retorna **zero** drops garantidos de Weapon/Armor com `sell>100k` em mobs com spawn
oficial. No catálogo completo há um par, EVENT_BAPHO1399 → Holy Avenger 1145, venda 225 k,
sem spawn nesse conjunto oficial. Isso não significa
que equipamentos finais sejam raros. Há 115 pares mob/equipamento garantido em mobs com
spawn oficial, incluindo MVPs. Seyren entrega Claymore de 37 k garantida: a 300 Seyren/h,
300 armas e 11,1 M de revenda somente desse item. A300 abates/h do mix inteiro de bio 3,
a quantidade é menor conforme a participação de Seyren, não 300 para cada espécie.
O item de maior sell nesse conjunto é Counter Dagger de 60 k em Kiel; não 100 k.

Consultar slots, equip_level e scripts junto do preço: Kaho tem `sell=10` e grande bônus;
Executioner `sell=10`, ATK 155, nível 48, ignora DEF de humano e dá+20% contra humano;
Mjolnir `sell=10` dá STR+15, DEX+40 e ASPD rate+10. Revenda baixa não prova baixo poder.
Não reduzir rates de equipamento para resolver exclusivamente emissões de zeny; primeiro
medir oferta de itens desejados, descarte e preço entre jogadores.

### 3.4 Recomendação e o que não mudar

Preservar por enquanto `BOOST`, rate base 300 x, caps 255/185/150 e as muralhas 150/200.
Os 11 mapas já aumentados não precisam de outro × 10 porque o modelo simples quase sempre
é limitado por matar/buscar. Não multiplicar bio 3, Thor ou Morroc antes de medir CPU, mapas
concorridos e mortes. Corrigir a orientação de rotas para separar Anubis 8,4 M de Sleeper 1,08 M
e para incluir opções de custo/risco. Ajustes de `POST99_START` ou TIERS dependem dos tempos
observados por faixa; não utilizar prêmio NPC bloqueado como se já estivesse acelerando
todo mundo. Conteúdo novo e instâncias ficam para próxima rodada, fora desta entrega.

## 4. NPCs custom

### 4.1 Cobertura e critério

`scripts_faithro.conf` declara nove arquivos, incluindo `mobs_x10.txt` gerado; `optional.conf`
declara 56. Inventário total: **65 arquivos declarados**, não 65 personagens NPC, pois há
duplicatas, funções, shops e controladores. O gerado não existe na cópia local, mas o fator
foi reconstruído do gerador conforme pedido; não se criou o arquivo. A classificação trata
o efeito econômico/progressivo; “ok” não equivale a teste completo de bugs. Ausência de gate
significa sem gate explícito de BaseLevel; requisitos de classe/item/quest continuam valendo.
`cd=0` significa ausência de cooldown temporal explícito no caminho descrito.

| Arquivo e evidência | O que dá | Custo | Cooldown | Gate | Gravidade | Recomendação |
|---|---|---|---|---|---|---|
| `npc/custom/faithro/guia.txt` L5–53 | Informação de rates e progressão | 0 | 0 | nenhum | ok | Manter; atualizar texto só após decisões |
| `npc/custom/faithro/ptbr/custom/healer.txt` L18–38 | HP/SP 100%, Agi 10 e Bless 10 por 240 s | 0 | 3 s por sessão | nenhum | alto | Buffs só até 99; preservar cura urbana |
| `npc/custom/faithro/ptbr/custom/warper.txt` L18–80; menus seguintes | Transporte a cidades, dungeons e campos | 0 | 0 | sem BaseLevel | alto | Unificar preço/gate por destino; conferir atalhos |
| `npc/custom/faithro/ptbr/custom/jobmaster.txt` L18–68; 99–171; 381–542 | Mudança de classe, reborn e caminho baby | sem débito Zeny no script | pré-requisitos de classe | nível/job conforme classe | médio | Manter classes permitidas e conferir reborn/baby |
| `npc/custom/faithro/ptbr/custom/resetnpc.txt` L16–40 | Reset de status, skills ou ambos | 5 k/5 k/9 k | 0 | nenhum | médio | Manter; preço por faixa só após medir frequência |
| `npc/custom/faithro/ptbr/custom/stylist.txt` L17–51 | Visual de cabelo/cor/roupa | 0 | 0 | nenhum | ok | Manter cosmético grátis |
| `npc/custom/faithro/selfcheck.txt` L7–18 | Log de configuração no OnInit | 0 | inicialização | controlador sem interação | ok | Manter; não é emissão |
| `npc/custom/faithro/webcmd.txt` L13–51 | Fila administrativa com whitelist | 0 | poll 5 s | acesso administrativo do site | ok | Manter; revisão de permissões em outra rodada |
| `mobs_x10.txt` (gerado por tools/gen_mob_boost.py:29–44) | Boost em 11 mapas | 0 | respawn da origem | gerado no deploy | médio | Manter fator; medir CPU/AoE, não aumentar novamente |
| `npc/custom/faithro/ptbr/custom/platinum_skills.txt` L20–34 | F_GetPlatinumSkills para a classe | 0 | 0 | classe da função oficial | ok | Manter conveniência high rate |
| `npc/custom/faithro/ptbr/custom/breeder.txt` L13–39 | Carrinho/falcão/peco conforme skill | 0 | 0 | skills de classe | ok | Manter; ramos 3rd não tornam classe disponível |
| `npc/custom/faithro/ptbr/custom/itemmall.txt` L13–44 | Equipamento, munição e consumíveis; Kaho 5013 | Kaho 700 k; Executioner 500 k; Poison 5 k | 0 | requisito do item ao equipar | alto | Retirar equipamentos finais; revisar preço de Poison |
| `npc/custom/faithro/ptbr/custom/card_remover.txt` L18–22;62–90 | Retira cartas com risco | 200 k+25 k/carta+itens | 0 | equipamento com carta | ok | Manter e medir gasto; não confundir destruição de item com moeda |
| `npc/custom/faithro/ptbr/custom/item_signer.txt` L18–19;95–131 | Assinatura em item elegível | 3 Gift Boxes+5 k/refino | 0 | restrições de item | ok | Manter cosmético e consumo de itens |
| `npc/custom/faithro/ptbr/custom/woe_controller.txt` L18–91; OnInit e agendas | Controle de castelos e evento | sem prêmio econômico automático do menu | agenda configurada | comandos de GM | médio | Manter; agenda WoE fora de escopo |
| `npc/custom/faithro/ptbr/custom/etc/mvp_room.txt` L20–23;128–131;229–293;394–401 | 46 MVPs e 29 mini-chefes, cura | 100 k/h+100 k/MVP;50 k/mini | sem cd de invocação após kill | sem BaseLevel | crítico | Suspender; reabrir só com tiers, limite e gate 150 |
| `npc/custom/faithro/ptbr/custom/etc/mvp_arena.txt` L20–27;52–84;123–249 | 209 MVPs permanentes,32 salas, cura | 0 | respawn 60–126 s | sem BaseLevel;20 por sala | crítico | Desligar include |
| `npc/custom/faithro/ptbr/custom/etc/penal_servitude.txt` L28–31;43–76;85–190 | Saída da prisão por multa ou trabalho | 1–100 M conforme PRISON | estado de prisão | acesso ao mapa de prisão | médio | Manter só sob política disciplinar; não contar como ralo de farm |
| `npc/custom/faithro/ptbr/custom/etc/bank_kafra.txt` L28–38;50–81 | Depósito por conta e juros | juros 0,1%/dia,cap 100 k/contato elegível | data por conta | saldo depositado | alto | Rendimento zero, preservar saldo; corrigir calendário |
| `npc/custom/faithro/ptbr/custom/etc/bank.txt` L19;26–50;56–101 | Banco por conta sem juros | 500/operação | 0 | saldo e limite da operação | ok | Manter; principal não é ralo |
| `npc/custom/faithro/ptbr/custom/etc/lottery.txt` L20–23;115;287–327 | Sorteio 6 de 40; prêmio 5 M ou 1 M | 4.750/bilhete | sorteio diário 20:45 no script | trava por conta com variável errada | médio | Manter após corrigir #L1; retorno 47,30% |
| `npc/custom/faithro/ptbr/custom/etc/stock_market.txt` L36–44;47–80;177–178;282–398;447–570 | Compra/venda de ações | 1.500/negociação | 7ticks/dia | capital; menu comum abre se soma>0 | crítico | Desligar; não usar aviso 40 M como medição |
| `npc/custom/faithro/ptbr/custom/etc/rpsroulette.txt` L26–55;79–88;108–122 | Minérios, caixas, álbum, Gold | 0; risco de morte | 0 | nenhum | crítico | Desligar fonte repetível de álbum |
| `npc/custom/faithro/ptbr/custom/etc/blackjack.txt` L133–149;224;239–249 | Ganho/perda de aposta | 2/10/20/100;double até 200 | 0 | saldo na escolha inicial | médio | Desligar até reservar aposta e tratar abandono; impacto monetário pequeno |
| `npc/custom/faithro/ptbr/custom/etc/shifty_assassin.txt` L17;44–110;173–185 | Serviço de assassinos contra outro personagem | 250 k/unidade | estoque por relógio | alvo; bloqueio durante WoE | alto | Desligar até política de PvP fora das arenas |
| `npc/custom/faithro/ptbr/custom/etc/monster_arena.txt` L292–332;575–714;735–746 | Treina invocação; vende pontos por 100 z | 1 k inicial; evolução em pontos | cura por cliques | monstro treinado | alto | Retirar conversão de pontos em zeny; testar isolamento |
| `npc/custom/faithro/ptbr/custom/etc/morroc_raceway.txt` L62–110;118–194 | Corrida em mapa dedicado | sem crédito Zeny/getitem no script | estado global da corrida | percurso/checkpoints | ok | Manter como lazer; não inventar payout |
| `npc/custom/faithro/ptbr/custom/etc/marriage.txt` L20–28; registro e anéis | Casamento e divórcio | 1,3 M+1,2 M;divórcio 50 k | estado civil | parceiros e itens | ok | Manter; custo não é recorrente semanal |
| `npc/custom/faithro/ptbr/custom/etc/quest_warper.txt` L326–333;363–371; OnInit | Transporte desbloqueável, cura e storage | config global; devoluções pós-warp | desbloqueios por conta | visitar destinos; sem gate universal | alto | Unificar transporte e corrigir refunds/índices antes de cobrar |
| `npc/custom/faithro/ptbr/custom/etc/autopot.txt` L11–15;60–79;178–201 | Consome poções automaticamente | poções do inventário | 100–1000 ms | nível mínimo do item | alto | Testar mínimo 250 ms e restrição PvP/WoE |
| `npc/custom/faithro/ptbr/custom/quests/hunting_missions.txt` L90;164–177;201–212;312–329 | Quatro caçadas; EXP+zeny+pontos | abates 40–70 de cada | 12 h/conta após conclusão | SQL mob_db ausente; sem BaseLevel | alto | Não restaurar sem adaptação; depois avaliar zeny÷ 10, preservar EXP 20% |
| `npc/custom/faithro/ptbr/custom/quests/quest_shop.txt` L57–99;133–170 | Chapéus/armas e sucos por receita | itens; sucos 3 z+fruta+garrafa | 0 | ingredientes | médio | Manter receitas comuns; revisar sobreposição de equipamentos finais |
| `npc/custom/faithro/ptbr/custom/quests/questboard.txt` L303–330 | Framework de coleta/caça, sem missões cadastradas | nenhum enquanto vazio | quest_delay 0 | faixas definidas por futura missão | ok | Manter inerte ou retirar menu vazio; não contabilizar prêmio inexistente |
| `npc/custom/faithro/ptbr/custom/quests/thq/THQS_ChattingNPC.txt` L20–95 | Diálogo/rede de introdução THQS | 0 | estado da quest | registro THQS | ok | Manter com THQS |
| `npc/custom/faithro/ptbr/custom/quests/thq/THQS_GuildNPC.txt` L21–34;56–71 | Registro de caçador de tesouro | 25 k/personagem | registro | Event_THQS | ok | Manter taxa e progressão |
| `npc/custom/faithro/ptbr/custom/quests/thq/THQS_QuestNPC.txt` L25–78;110–554 | Distribui missões e cancelamento | 2.500 para cancelar | 1 h/conta;cancelar 2–3 h | registro THQS | médio | Manter com validação de repetição e itens de entrega |
| `npc/custom/faithro/ptbr/custom/quests/thq/THQS_Quests.txt` L29–1044 | Conclusões e 1–5 tokens | itens/entregas da missão | controlado pelo QuestNPC | estado de missão | médio | Manter; medir duração, não dar token/h fictício |
| `npc/custom/faithro/ptbr/custom/quests/thq/THQS_TTShop.txt` L54–72;369–374;433–516 | 1 k/token, armas e 13 cartas selecionadas; Mjolnir | 2–540T cartas;1.000T Mjolnir | 0 | tokens por conta | crítico | Retirar cartas e Mjolnir; manter conversão 1 k/token inicialmente |
| `npc/custom/faithro/ptbr/custom/quests/elvenear.txt` L26–33 | Elven Ears 2286 | 2213+20 de 1040+20 de 919 | 0 | itens | ok | Manter receita |
| `npc/custom/faithro/ptbr/custom/quests/sunglasses.txt` L56–62;92–106 | Óculos 2202 com slot | 100 k+400 k+itens | etapas da quest | SG_QUEST1 | médio | Manter; retirar duplicata 2202 da loja a 45 k se valorizar quest |
| `npc/custom/faithro/ptbr/custom/quests/bandit_beard.txt` L76–90;124–235 | Barba 2237, cadeia e monstros | ingredientes | flag final por personagem | etapas BEARD_QUEST | ok | Manter; validar estado global do combate em outra rodada |
| `npc/custom/faithro/ptbr/custom/quests/event_6_new_hats.txt` L44–55;104–113;158–283 | Seis chapéus por receitas | itens | 0 nas trocas | ingredientes | ok | Manter receitas; sem emissão direta de zeny |
| `npc/custom/faithro/ptbr/custom/quests/may_hats.txt` L41–45;68–73;97–164 | Cinco receitas de equipamento | itens | 0 | ingredientes | ok | Manter; preços de mercado ainda desconhecidos |
| `npc/custom/faithro/ptbr/custom/quests/kings_items.txt` L29–30;45–55 | Coroa 5007 ou espada 1137 | receitas em .@Items 1/2 | 0 | itens | médio | Manter sob política de itens; não equivale a carta MVP |
| `npc/custom/faithro/ptbr/custom/quests/dead_branch.txt` L82–97 | Galho 604; chance 1/1000 de Bloody Branch 12103 | 3logs+heart+5trunks+gnarl | 0 | ingredientes | alto | Suspender prêmio Bloody Branch se proteger disponibilidade de MVP |
| `npc/custom/faithro/ptbr/custom/quests/berzebub.txt` L18;22;44–55 | Carta 4145,cast rate-30% | ingredientes;sem zeny | 1/char | BerzQuest | crítico | Desligar; bypass explícito de carta MVP |
| `npc/custom/faithro/ptbr/custom/quests/jewel_case.txt` L18–27;40–57 | Jewel Case 12106 após reborn | estado de base 99 eEXP≥1 M | ciclo de reborn | Upper 0,base 99 para iniciar | médio | Manter; inspecionar conteúdo da caixa antes de anunciar drop-only estrito |
| `npc/custom/faithro/ptbr/custom/quests/valhallen.txt` L31–81;88–128 | Itens divinos, Gleipnir e receitas adicionais | materiais de boss e equipamentos | 0 | ingredientes | alto | Suspender e definir política de god items/pre-re |
| `npc/custom/faithro/ptbr/custom/quests/kaho_balmung.txt` L18–19;38–49 | Balmung 1161 ou Kaho 5013 | 1 M+itens | 0 | ingredientes | alto | Desligar com a revisão da loja |
| `npc/custom/faithro/ptbr/custom/quests/kahohorn.txt` L17–18;57–66 | Kaho 5013 | 5 M+itens,3 Emperium | 0 | ingredientes | alto | Suspender até unificar política/preço Kaho |
| `npc/custom/faithro/ptbr/custom/events/cluckers.txt` L24–59;113–115 | Prêmio padrão 1 Apple 512; GM pode mudar | 0 | rodada manual,encerra ao prêmio | GM80 para controlar | ok | Manter prêmio modesto; registrar mudanças de GM |
| `npc/custom/faithro/ptbr/custom/events/devil_square.txt` L34–43;94–105;128–201 | 203 mobs,2 Moonlight e 10 baús WoE | 20 k | cada 2 h,janela 5 min | base 70 | alto | Rever baús 10 x e MVPs antes de manter como evento recorrente |
| `npc/custom/faithro/ptbr/custom/events/disguise.txt` L127–139;150–165;235 | 10rodadas,Apple 512× 1 por acerto | 0 | cada 2 h;GM pode iniciar | sem BaseLevel;GM60 configura | ok | Manter prêmio atual; evitar cartas/álbuns como prêmio |
| `npc/custom/faithro/ptbr/custom/events/mushroom_event.txt` L41–63 | 1–10 cogumelos,10 Apples por kill | 0 | minuto 10 de cada hora | nenhum;GM60 controla | ok | Manter baixo valor; não é fonte de zeny significativa |
| `npc/custom/faithro/ptbr/custom/events/mvp_ladder.txt` L82–103;222–303 | 39 MVPs em sequência,loots habilitados | 100 k por inscrição do líder | 60 min de timeout;5 s entre rounds | grupo exatamente 2;sem BaseLevel | alto | Gate 150 e limite por conta; testar farm de 39 bosses/entrada |
| `npc/custom/faithro/ptbr/custom/events/holiday/xmas_rings_event.txt` L69–98;119–125;171–185 | Troca de presentes/anéis; reescreve 3 scripts de item | Gift Boxes e presentes | flags da quest;sem gate de mês | estado Q_XMSRINGS | médio | Sazonal; não carregar globalmente sem revisar setitemscript |
| `npc/custom/faithro/ptbr/custom/events/holiday/valentinesdayexp.txt` L62–72;104–111;165–174;209–260 | +50% EXP por raça via chocolate/anel;global no OnInit | 15 k preto;13,5 k+3milks branco | até mudança de hora,parceiro online | casamento/anel/chocolate | alto | Desligar fora da temporada; não tratar comentário de data como gate |
| `npc/custom/faithro/ptbr/custom/events/holiday/hallow06.txt` L18–23;46–47;92–101 | Chapéu 5134 eEXP BaseLevel× 1.000 | itens | flags por personagem | não Novice | médio | Sazonal, sem EXP permanente fora da data |
| `npc/custom/faithro/ptbr/custom/events/holiday/uneasy_cemetery.txt` L26–60;87–114 | 65 mortos-vivos na cidade; prêmio Blue Potion e 50/100EXP | Holy Water para adiar | calendário diário | doação/combate | médio | Suspender invasão urbana fora de evento anunciado |
| `npc/custom/faithro/ptbr/custom/battleground/bg_emp.txt` L14–17;20–24;55–59 | 10 Red Potions por vencedor | 0 | partida até 20 min | 1 por time | ok | Manter prêmio modesto; observar combinação entre contas |
| `npc/custom/faithro/ptbr/custom/battleground/bg_pvp.txt` L19–22;25–30;63 | 10 Red Potions por vencedor | 0 | partida até 20 min | 2 por time | ok | Manter e testar regras próprias de BG |
| `npc/custom/faithro/ptbr/custom/etc/airplane.txt` L19–80; itinerário e embarques | Transporte cíclico para 24 pontos | sem débito Zeny | itinerário por relógio | embarque/local | médio | Manter lazer; harmonizar se virar atalho à tarifa de warper |
| `npc/custom/faithro/ptbr/custom/quests/tha_statues.txt` L34–245;246–256 | Sequência de estátuas,warp thana_step | quatro pedras 7426–7429 | estado TSQ_CHK | etapas e pedras | médio | Manter quest; verificar se warper a torna irrelevante |
| `npc/custom/faithro/ptbr/custom/quests/sphinx_mask.txt` L18–32;42–50 | Máscara 7114 | negocia 1 M/750 k/500 k | flag sphmask_q | event_umbala≥2 | ok | Manter ralo opcional e quest |
| `npc/custom/faithro/ptbr/custom/quests/umbalian_language.txt` L77–78;139–144;159–191 | Idioma/event_umbala e cadeia de itens | Poring Egg,Incubator,livros/scroll | flags de etapas | quest/itens | ok | Manter; não cria recurso monetário repetível |

### 4.2 Pontos de implementação para a próxima rodada

A oferta máxima dos 209 postos da arena, ignorando tempo de combate e percurso, é
`209×3600/92,9995 ≈ 8.090 MVPs/h`, e cerca de 0,809 cartas MVP/h a 0,01% por abate se todos
os postos fossem limpos continuamente. É exposição coletiva potencial, não uma previsão de
farm individual. Ter a chance de carta 1 x não protege a raridade quando a quantidade de
tentativas cresce dessa forma.

Não religar todo `optional.conf` como um pacote indivisível. Grupo imediato proposto de
suspensão: arena MVP, sala MVP, bolsa, blackjack, roleta, quest de carta Berzebub, Kaho/Balmung,
Valhallen e módulos sazonais que reescrevem scripts. No THQS, pode-se preservar tarefas e
remover apenas cartas/Mjolnir da loja. Em Hunting, registrar a dependência ausente em vez
de cadastrar uma tabela SQL antiga sem revisão do contrato de dados.

`quest_warper.txt:331–333,367–371` debita, faz warp, `close2` e depois devolve a taxa. A devolução
da rota dungeon ainda usa array de town e índice diferente do preço debitado. Isso torna
incorreto contar a taxa como ralo confiável, com risco de crédito indevido conforme estado
temporário de menu. Remover devoluções somente após definir como detectar falha de warp;
não copiar a cobrança para o warper principal sem tratar os caminhos de erro.

Devil Square custa 20 k, abre 12 vezes por dia, tem 203 mobs nas três ondas (75+70+58),
incluindo dois Moonlight, e depois dez baús IDs 1324,1328,...,1360. A rate de treasure é 10 x;
não dizer que “dez baús” por si é ralo. Valhallen ainda tem receitas para Gleipnir e itens
de era posterior: conferir disponibilidade dos ingredientes no pre-re e bloquear as receitas
sem uma política. Essa revisão não exige criar conteúdo novo.

O NPC de quests platinum chama `F_GetPlatinumSkills`; dar skills de quest é uma conveniência
coerente com high rate. Preservá-lo, evitando transformá-lo em fonte de skills de classes
desabilitadas. `autopot` tem tick mínimo 100 ms, até 10 verificações/s por jogador, consome os
itens; não cria poções, mas muda sustain e custo de CPU. Propor 250 ms e restrição em PvP/WoE
como teste separado do cap de ASPD. Não atribuir a um único número toda a diferença de classe.

## 5. Como medir

### 5.1 Instrumentação mínima proposta

Nada desta seção foi aplicado. Em `server/conf/import/log_conf.txt`, reduzir `log_zeny`
de 100000 para 1000 no acompanhamento de uma semana e, em janelas controladas de 15–30 min,
usar 1 para capturar inclusive taxas de 500, resets pequenos e revendas. Valor 1 significa
todas as mudanças; não é “mínimo 1” no mesmo sentido dos demais valores. Guardar duração
das janelas e não comparar agregados de limiares diferentes como se cobrissem o mesmo fluxo.

Para itens, ligar bit 0 x 08: `enable_logs: 0xFFFFFF7F`, mantendo 0 x 80 desligado para consumos;
usar `log_filter: 1` durante a amostra. Só ligar 0 x 08 com filtro 4080 ainda perde itens baratos
comuns e gera amostra tendenciosa. `log_mvpdrop: yes` já está ativo e deve ser mantido.
`log_athena.conf` não oferece whitelist por mapa nem amostragem probabilística por item.
Portanto sem mudar src a coleta é global em janelas curtas, filtrando mapas no SELECT;
um filtro SQL depois da escrita não reduz I/O já ocorrido. Usar mapas-chave como roteiro
da sessão: Juperos 02, Abbey 01/03, bio 3, Thor 03, Thanatos 09 e Manuk 02.

No commit analisado, `M` é drop criado pelo monstro, com amount negativo e `char_id` igual
ao ID do mob; `L` é loot carregado/recolhido por monstros, não “todos os abates de jogador”.
Fonte `log.cpp:65–79,269–273`, `mob.cpp:2587`. Não juntar `M` a `char.char_id`. `P` positivo
pode ser coleta pelo jogador, mas também recebe outras origens/caminhos. Autoloot altera
onde os registros aparecem; validar um teste de dez abates antes da janela. Contar linhas
de picklog não conta mortes: um mob gera zero, um ou vários drops, e mob sem drop some.

Sem src, sessões de teste devem registrar externamente começo/fim, conta, classe, nível,
build, mapa, kills pelo contador de quest/evento validado, zeny antes/depois e itens vendidos.
Um item garantido específico pode servir de proxy de mortes daquele ID/mapa com validação,
mas não substitui o contador global. `mvplog` conta MVPs com ID/mapa, sem informar duração
do combate. Medir tempo ativo, não `MAX(time)-MIN(time)` de logs de movimentação, que inclui
AFK ou omite silêncios. Logs SQL existentes não fornecem playtime por mapa, dano, DPS, mortes
de jogadores ou hora de cada level-up. Esses campos exigem um logger futuro por script/evento.

### 5.2 Queries prontas, somente leitura

Os exemplos usam nomes reais de colunas conferidos em `information_schema.COLUMNS`.
Substituir datas e IDs por sessão. Não rodar `CREATE`, `INSERT`, `UPDATE`, `DELETE`, `SET`
ou importação de schema para executar esta análise. Os SELECT abaixo são também o apêndice
de consultas de medição; uma lista vazia hoje é resultado esperado, não defeito da query.

**Q01, população e exposição atual.** Exclui conta de serviço ao contar pessoas cadastradas;
não deduz “jogador” só de uma linha em `login`.

```sql
SELECT sex, group_id, COUNT(*) AS contas
FROM ragnarok.login GROUP BY sex, group_id;
SELECT c.char_id,c.class,c.base_level,c.job_level,c.zeny,l.group_id
FROM ragnarok.`char` c JOIN ragnarok.login l USING(account_id);
SELECT COUNT(*) AS mvps FROM ragnarok_log.mvplog;
SELECT type,COUNT(*) AS eventos,SUM(amount) AS saldo
FROM ragnarok_log.zenylog GROUP BY type;
```

**Q05, entradas/saídas por sistema e dia.** Agrupa movimentações, não identifica automaticamente
o NPC responsável. `N` inclui depósito/saque de bancos custom e negociação da bolsa; reconciliar
com Q08 antes de chamar todo débito de ralo. `T/V/E/I/B/K` são transferências/estoques ou taxas
misturadas e não devem ser somadas como fontes novas por lado. Não contar o lançamento `A` da equipe.

```sql
SELECT DATE(z.time) AS dia,z.type,
       SUM(CASE WHEN z.amount>0 THEN z.amount ELSE 0 END) AS entradas,
       -SUM(CASE WHEN z.amount<0 THEN z.amount ELSE 0 END) AS saidas,
       SUM(z.amount) AS saldo,COUNT(*) AS eventos
FROM ragnarok_log.zenylog z
JOIN ragnarok.`char` c ON c.char_id=z.char_id
JOIN ragnarok.login l ON l.account_id=c.account_id
WHERE z.time>='2026-10-18 00:00:00' AND z.time<'2026-10-25 00:00:00'
  AND l.sex<>'S' AND l.group_id=0 AND z.type<>'A'
GROUP BY DATE(z.time),z.type ORDER BY dia,z.type;

SELECT z.char_id,c.class,c.base_level,z.map,z.type,
       SUM(z.amount) AS saldo,COUNT(*) AS eventos
FROM ragnarok_log.zenylog z
JOIN ragnarok.`char` c ON c.char_id=z.char_id
JOIN ragnarok.login l ON l.account_id=c.account_id
WHERE z.time>='2026-10-18 00:00:00' AND z.time<'2026-10-25 00:00:00'
  AND l.group_id=0 AND l.sex<>'S' AND z.type IN ('S','N','M','C')
GROUP BY z.char_id,c.class,c.base_level,z.map,z.type
ORDER BY saldo DESC;
```

`z.map` é o mapa da operação: a revenda na cidade não revela onde o loot foi farmado.
Para zeny/h de uma sessão, usar duração anotada externamente. A consulta abaixo é exemplo
de uma janela conhecida de 30 min de um personagem; substituir o ID fictício123456 pelo personagem do teste.
Não interpretar seu resultado atual como renda de jogador.

```sql
SELECT char_id,SUM(amount) AS saldo,
       SUM(amount)/0.5 AS saldo_por_hora_janela_conhecida
FROM ragnarok_log.zenylog
WHERE char_id=123456 AND time>='2026-10-18 18:00:00'
  AND time<'2026-10-18 18:30:00' AND type IN ('S','N','M','C')
GROUP BY char_id;
```

**Q06, oferta de itens e valor criado por mapa na janela.** `M` negativo tem ID do mob;
o valor representa geração bruta de loot, não venda realizada nem recebimento por um player.
Excluir mapas de equipe/teste no roteiro, pois o esquema não liga esse registro ao matador.
Cards e prêmios MVP podem ser reportados à parte, evitando duplicação.

```sql
SELECT p.map,DATE_FORMAT(p.time,'%Y-%m-%d %H:00:00') AS hora,
       SUM(-p.amount*i.sell) AS valor_nominal_gerado,
       COUNT(*) AS linhas_de_drop,SUM(-p.amount) AS unidades
FROM ragnarok_log.picklog p
JOIN faithro_web.items i ON i.id=p.nameid
JOIN faithro_web.mobs m ON m.id=p.char_id
WHERE p.type='M' AND p.amount<0 AND m.is_mvp=0
  AND p.time>='2026-10-18 18:00:00' AND p.time<'2026-10-18 18:30:00'
  AND p.map IN ('juperos_02','abbey01','abbey03','lhz_dun03',
                'thor_v03','tha_t09','man_fild02')
GROUP BY p.map,DATE_FORMAT(p.time,'%Y-%m-%d %H:00:00');

SELECT p.type,p.nameid,i.name,SUM(p.amount) AS unidades_liquidas,
       COUNT(*) AS lancamentos
FROM ragnarok_log.picklog p JOIN faithro_web.items i ON i.id=p.nameid
WHERE i.type='Card' AND p.time>='2026-10-18 00:00:00'
GROUP BY p.type,p.nameid,i.name ORDER BY lancamentos DESC;
```

Como teste restrito de abates: Claymore é garantida em Seyren no snapshot. Apenas se o teste
de dez kills confirmar uma linha `M` de amount=-1 por morte, contar esse proxy para Seyren
no bio 3, sem estender a outros mobs nem a toda a sessão.

```sql
SELECT p.map,p.char_id AS mob_id,COUNT(*) AS proxy_kills_seyren
FROM ragnarok_log.picklog p JOIN faithro_web.items i ON i.id=p.nameid
WHERE p.type='M' AND p.amount=-1 AND p.char_id=1634
  AND i.aegis='Claymore' AND p.map='lhz_dun03'
  AND p.time>='2026-10-18 18:00:00' AND p.time<'2026-10-18 18:30:00'
GROUP BY p.map,p.char_id;
```

**Q07, MVPs por hora civil e por fonte.** Contagem é verdadeira para lançamentos MVP, não
tempo de combate. Distinguir mapa oficial, arena, sala e ladder pelo campo `map`.

```sql
SELECT DATE_FORMAT(v.mvp_date,'%Y-%m-%d %H:00:00') AS hora,v.map,
       v.monster_id,m.name,COUNT(*) AS abates,
       COUNT(DISTINCT v.kill_char_id) AS vencedores
FROM ragnarok_log.mvplog v
JOIN ragnarok.`char` c ON c.char_id=v.kill_char_id
JOIN ragnarok.login l ON l.account_id=c.account_id
LEFT JOIN faithro_web.mobs m ON m.id=v.monster_id
WHERE v.mvp_date>='2026-10-18 00:00:00' AND l.group_id=0 AND l.sex<>'S'
GROUP BY DATE_FORMAT(v.mvp_date,'%Y-%m-%d %H:00:00'),v.map,v.monster_id,m.name;
```

**Q08, patrimônio por conta e saldos custom.** Tirar dois snapshots em cliente/arquivo
externo com data conhecida. `char` sozinho não inclui depósitos; não chamar uma retirada
do banco de criação de zeny. A consulta de ações informa quantidades, a avaliação em zeny
depende de casar preços `$S1..$S10` de `mapreg` no mesmo instante.

```sql
WITH dinheiro AS (
  SELECT c.account_id,SUM(c.zeny) AS carteira
  FROM ragnarok.`char` c GROUP BY c.account_id
), bancos AS (
  SELECT account_id,SUM(value) AS depositos
  FROM ragnarok.acc_reg_num
  WHERE `key` IN ('#bankstorage','#kafrabank') GROUP BY account_id
)
SELECT l.account_id,COALESCE(d.carteira,0) AS carteira,
       COALESCE(b.depositos,0) AS bancos,
       COALESCE(d.carteira,0)+COALESCE(b.depositos,0) AS moeda_custom_e_carteira
FROM ragnarok.login l LEFT JOIN dinheiro d USING(account_id)
LEFT JOIN bancos b USING(account_id)
WHERE l.group_id=0 AND l.sex<>'S' ORDER BY moeda_custom_e_carteira DESC;

SELECT account_id,`key`,`index`,value FROM ragnarok.acc_reg_num
WHERE `key` IN ('#bankstorage','#kafrabank','#Treasure_Token',
               '#S1','#S2','#S3','#S4','#S5','#S6','#S7','#S8','#S9','#S10');
SELECT varname,`index`,value FROM ragnarok.mapreg
WHERE varname IN ('$S1','$S2','$S3','$S4','$S5','$S6','$S7','$S8','$S9','$S10');

SELECT c.class,c.base_level,COUNT(*) AS personagens,MIN(c.zeny) AS menor,
       AVG(c.zeny) AS media,MAX(c.zeny) AS maior,
       SUM(c.zeny>=1500000000) AS acima_1_5_bi
FROM ragnarok.`char` c JOIN ragnarok.login l USING(account_id)
WHERE l.group_id=0 AND l.sex<>'S'
GROUP BY c.class,c.base_level;
```

Q08 não soma estoque de itens, native bank se configurado depois, preço entre jogadores
nem ouro guardado; também não identifica a mesma pessoa com várias contas. P50/P90 precisam
ser calculados sobre as linhas por conta exportadas, sem confundir média com mediana.

### 5.3 Metas numéricas e decisões

| Medida | Meta inicial proposta | Alarme e ação |
|---|---|---|
| Sessões reproduzidas | ≥10 por faixa e ≥3 classes, duração 30 min; ideal≥30 contas não staff antes de generalizar | Com menos dados, reportar casos e faixa, não ranking estatístico |
| Base 1→99 /99→150 /150→200 /200→255 | P50 próximo de 1/10/10/23 h ativas; tolerância±30% | Fora de 0,7–1,3 /7–13 /7–13 /16,1–29,9 h, rever rota e emissões NPC antes da curva |
| 254→255 | P50 entre 1 e 2 h ativas em rota final | P90>3 h sugere revisar muralha, risco e disputa |
| Farm líquido pós-serviços | Faixa exploratória de 2–8 M/h solo; reportar mapa/classe e Overcharge | >15 M/h sustentados 30 min: auditar loot e conversões; não nerfar todas as rates pela média |
| Fontes sem combate | Bolsa 0 e juros 0 após decisão; caça restaurada≤500 k/dia/conta em média | Qualquer emissão das fontes suspensas é falha de implantação; multi-conta continua fora da proteção por conta |
| Cobertura dos ralos | 20–40% das entradas sistêmicas em semana madura, separar coortes iniciantes | <10% e saldo mediano subindo>50 M/semana: rever serviços; >50% e pouca adesão: aliviar custo |
| Zeny acumulado | P50 dos 255 naturais de 50–250 M, hipótese inicial; contas/bancos separados | >10% das contas chegando a 1,5 G em 30 dias: revisar fonte dominante; não elevar teto como primeira resposta |
| Cartas MVP | Nenhuma rota custom alternativa; acompanhar kills e drops por fonte | Frequência de carta segue binomial; 10.000 kills a 0,01% dão média 1, não prova de chance errada por zero ou duas |
| Combate de referência | Cada trans deve ter pelo menos um papel funcional; TTK alvo PvP equipado 3–10 s em trocas sustentadas | Mediana<2 s ou Asura letal em>50% do painel com a defesa comum: testar ajuste isolado. Não extrapolar para todos os PvPs |
| Teste de mapa final | 30 min por combinação build/mapa, reportar mortes e tempo recuperando | TTK de MVP<15 s reiterado e sem mecânica: rever acesso/recompensa antes de HP global |
| Custo da coleta | CPU de mapa p 95<80%, sem aumento persistente de latência>20%; volume medido por janela | Interromper janela de log integral se exceder; guardar contagem e duração, não apagar evidência como correção |

Os intervalos são metas de operação a pactuar; não vieram de uma população inexistente.
Para cartas raras, divulgar exposição em abates e intervalo de confiança, não só zeny/h.
Para PvP, painel mínimo proposto:10 duelos por combinação, build/equipamento iguais,
com e sem consumíveis, cenário atual e uma única alteração por vez; WoE tem reduções próprias.

## 6. Próximas rodadas, para escolha

1. Revisar includes, acesso a MVP, cartas alternativas, juros, bolsa e jogos; fazer patch separado.
2. Implementar coleta curta e painel por sessão, sem depender de picklog como contador universal.
3. Ensaiar 193 ASPD, Asura PvP/WoE e autopot, preservando baseline para comparar.
4. Unificar preços e gates de transportes, serviços e permissões de atcommands.
5. Reavaliar rotas, job rate e muralha 254 com tempos ativos; só então alterar geradores.
6. Definir política de itens divinos, quests sazonais e cartas por álbum; criar conteúdo novo,
   instâncias ou mapas 100+ somente em um escopo aprovado à parte.

Nenhuma opção acima foi aplicada. Schedule de WoE, código C++, servidor e deploy ficaram fora.

## Apêndice A. Reprodutibilidade e consultas estáticas

Scratchpad da sessão: `%TEMP%/faithro-estudo-20261018`. Dependência local de leitura YAML:
PyYAML 6.0.3, Python 3.12.14; coleta SSH também compatível com Python 3.15. Não se instalou pacote
na VPS. Arquivos JSON contêm somente catálogo público, schema de colunas e agregados mínimos
da equipe, sem credenciais. A pasta `remote/` guarda os arquivos lidos por scp.

Para repetir: coletar SELECT Q01/Q02/Q09, copiar arquivos do commit indicado, executar A01
para exportação, A02 para números, A03 para diagnósticos complementares, A04 para builds e
A05 para ASPD com job. Os scripts completos usados estão abaixo; seus caminhos de workspace
e scratch são locais desta sessão e devem ser ajustados na reprodução. O relatório em si
não exige que o scratch continue existindo: fórmulas, consultas e fontes estão preservadas.

**Q02, catálogo e valor esperado.** Exportação JSON do A01 preserva scripts de item com
newlines sem quebrar TSV. `rate_final` já incorpora as rates: não multiplicar novamente por 100.

```sql
SELECT * FROM faithro_web.items;
SELECT * FROM faithro_web.mobs;
SELECT * FROM faithro_web.mob_drops;
SELECT * FROM faithro_web.mob_spawns;

SELECT m.id,m.aegis,m.level,m.hp,m.attack,m.attack2,m.defense,
       m.magic_defense,m.vit,m.`int`,m.modes,m.class,m.is_mvp,
       m.base_exp*300 AS exp_final,
       SUM(CASE WHEN d.mvp=0 THEN d.rate_final*i.sell/10000.0 ELSE 0 END) AS z_por_abate
FROM faithro_web.mobs m
LEFT JOIN faithro_web.mob_drops d ON d.mob_id=m.id
LEFT JOIN faithro_web.items i ON i.id=d.item_id
GROUP BY m.id,m.aegis,m.level,m.hp,m.attack,m.attack2,m.defense,
         m.magic_defense,m.vit,m.`int`,m.modes,m.class,m.is_mvp,m.base_exp;
```

**Q03, conteúdo e picos de ataque.** A presença de AI agressiva não é inferível apenas do
`modes` do site. Ler `Ai` no YAML e converter com o enum de `src/map/mob.hpp`.

```sql
SELECT m.id,m.aegis,m.level,m.hp,m.base_exp*300 AS exp_final,
       m.class,m.attack2,COUNT(DISTINCT s.map) AS mapas_estaticos
FROM faithro_web.mobs m LEFT JOIN faithro_web.mob_spawns s ON s.mob_id=m.id
WHERE m.level>100 AND m.class='Normal' AND m.is_mvp=0 AND m.base_exp>0
GROUP BY m.id,m.aegis,m.level,m.hp,m.base_exp,m.class,m.attack2;
SELECT id,aegis,class,is_mvp,attack2 FROM faithro_web.mobs
WHERE base_exp>0 ORDER BY attack2 DESC LIMIT 20;
```

**Q04, drops garantidos e equipamento.** A primeira consulta retorna zero linhas; a segunda
mostra que drops de bom equipamento continuam numerosos apesar desse corte de revenda.

```sql
SELECT m.id,m.aegis AS mob,i.id AS item_id,i.aegis,i.sell,i.slots,
       i.equip_level_min,d.rate_final
FROM faithro_web.mob_drops d JOIN faithro_web.items i ON i.id=d.item_id
JOIN faithro_web.mobs m ON m.id=d.mob_id
WHERE d.mvp=0 AND d.rate_final=10000 AND i.type IN ('Weapon','Armor')
  AND i.sell>100000
  AND EXISTS(SELECT 1 FROM faithro_web.mob_spawns s WHERE s.mob_id=m.id);

SELECT m.id,m.aegis AS mob,i.id AS item_id,i.aegis,i.sell,i.slots,
       i.equip_level_min,d.rate_final
FROM faithro_web.mob_drops d JOIN faithro_web.items i ON i.id=d.item_id
JOIN faithro_web.mobs m ON m.id=d.mob_id
WHERE d.mvp=0 AND d.rate_final=10000 AND i.type IN ('Weapon','Armor')
  AND EXISTS(SELECT 1 FROM faithro_web.mob_spawns s WHERE s.mob_id=m.id)
ORDER BY i.sell DESC;
```

**Q09, contrato das tabelas e dependência de caça.** SELECT de metadados foi usado em vez
de comandos que alterem schema. A existência de `faithro_web.mobs` não satisfaz a query do
NPC para `ragnarok.mob_db`, cujo schema é outro.

```sql
SELECT TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME,COLUMN_TYPE
FROM information_schema.COLUMNS
WHERE (TABLE_SCHEMA='ragnarok_log' AND TABLE_NAME IN ('zenylog','picklog','mvplog','npclog'))
   OR (TABLE_SCHEMA='ragnarok' AND TABLE_NAME IN ('char','login','acc_reg_num','mapreg'))
ORDER BY TABLE_SCHEMA,TABLE_NAME,ORDINAL_POSITION;
SELECT TABLE_SCHEMA,TABLE_NAME FROM information_schema.TABLES
WHERE TABLE_SCHEMA='ragnarok' AND TABLE_NAME IN ('mob_db','mob_db_re');
SELECT varname,value FROM ragnarok.mapreg
WHERE varname IN ('$S1','$S2','$S3','$S4','$S5','$S6','$S7','$S8','$S9','$S10');
```

O SELECT exato da seleção de missões, reproduzido no `extra.py`, gerou erro 1146 de tabela
ausente. Não foi feita tentativa de aceitar ou concluir missão no jogo.

Leitura de arquivos, sem comandos de escrita remotos:

```powershell
$studyScratch = Join-Path $env:TEMP 'faithro-estudo-20261018'
New-Item -ItemType Directory -Force -Path "$studyScratch/remote/db", `
  "$studyScratch/remote/conf", "$studyScratch/remote/src/map", `
  "$studyScratch/remote/npc/pre-re", `
  "$studyScratch/remote/npc/custom/faithro/ptbr" | Out-Null
ssh faithro 'git -C /home/rathena/rathena rev-parse HEAD'
scp -r faithro:/home/rathena/rathena/db/pre-re "$studyScratch/remote/db/"
scp -r faithro:/home/rathena/rathena/conf/battle "$studyScratch/remote/conf/"
scp -r faithro:/home/rathena/rathena/conf/import "$studyScratch/remote/conf/"
scp faithro:/home/rathena/rathena/npc/pre-re/scripts_monsters.conf "$studyScratch/remote/npc/pre-re/"
scp -r faithro:/home/rathena/rathena/npc/custom/faithro/ptbr/mobs "$studyScratch/remote/npc/custom/faithro/ptbr/"
foreach ($studySource in @('status','battle','pc','skill','log','mob')) {
  scp "faithro:/home/rathena/rathena/src/map/$studySource.cpp" "$studyScratch/remote/src/map/"
}
ssh faithro 'zgrep -Ein "discounted buying|overcharged selling" /var/log/rathena/map.log /var/log/rathena/map.log.1.gz'
```

Última busca sem correspondência nesta coleta. O parser e os dados foram usados para checar
arbitragem, sem depender da presença/ausência desse aviso para concluir que um item é forte.
Salvar os seis scripts do apêndice C no scratchpad e ajustar `ROOT`/`R` para o workspace.
Executar A01 e A06 para coleta complementar. Se necessário, instalar PyYAML somente localmente
com Python 3.12, `python -m pip install --target <scratch>/lib312 PyYAML==6.0.3`; executar A02,
A03, A04 e A05 com o mesmo Python 3.12. A04/A05 reutilizam A02; não precisam ser executados
em paralelo. O arquivo gerado `builds.md` contém as 90 alocações com seus custos. Igualdade
bit a bit exige conservar os catálogos/imports desta fotografia; consultas futuras podem
retornar outro estado legítimo. Nenhum desses comandos implanta alterações.

## Apêndice B. Cinco conferências independentes

1. **Juperos 02, zeny/h de oferta:** o snapshot tem 315 mobs e valor total de uma limpeza
   1.716.758,15 z. Todos esses spawns têm piso 1 s; `1.716.758,15×3600=6.180.329.340 z/h`.
   Com fator 10,3150 mobs e 61.803,2934 M/h. No modelo humano,5.450,03 z/abate× 341,62/h
   dá aproximadamente 1,862 M/h; usar o valor integral do script para o fechamento, não
   o arredondamento do quadro.
2. **LK255, HP:** `HpFactor=150`, `HpIncrease=500`. `SUM(i=2..255,i)=32.639`;
   somar 1,5i com arredondamento half-up acrescenta 63,5 ao total 48.958,5, resultando 49.022.
   Base `35+1275+49022=50.332`; `floor(50.332×2,85×1,25)=179.307`.
   VIT natural 185+8 de job: `floor(50.332×2,93×1,25)=184.340`.
3. **254→255:** CSV registra 15.700.000.000; `15.700.000.000/30.000.000=523,333...`;
   arredondar para 524 abates,524/300=1,7467 h. A entrada 255 da tabela não cobra outro nível.
4. **Bolsa por ciclo:** comprar 1.000.000 a 50 custa 50.001.500; vender a 150 retorna 149.998.500;
   lucro 99.997.000. Não é lucro diário: depende de completar a travessia aleatória. A taxa
   absorve 3.000, isto é 0,003% do spread de 100 M.
5. **Loteria:** `C(40,6)=3.838.380`; quatro acertos `C(6,4)×C(34,2)=8.415`;
   cinco acertos 204; seis 1. `(8619×1.000.000+5.000.000)/3.838.380=2246,781194`;
   dividir por 4750 dá 47,300657%. A trava de compra incorreta é achado separado da esperança.

## Apêndice C. Scripts efetivamente usados

Os blocos abaixo são análise de leitura e simulação. Não colar saídas SQL do builder no
MySQL; não usar os geradores em modo de escrita para reproduzir este estudo.

### A01, coleta e baseline

Arquivo `collect.py`, SHA256 `b68a3e83f810e611df46d79b8e3b2fd19c71848b893b03248b39a09b925c2dbb`.

```python
import json, subprocess, pathlib, hashlib, shlex
ROOT=pathlib.Path(r'C:\Development\Workspace\VPS OCI NVMe 2')
SCR=pathlib.Path(__file__).parent
def ssh(cmd):
    return subprocess.run(['ssh','-o','BatchMode=yes','faithro',cmd],capture_output=True,check=True).stdout.decode('utf-8')
def sql(q):
    return ssh('mysql -uroot --default-character-set=utf8mb4 -N -B --raw -e '+shlex.quote(q))
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for d in ['docs','server','tools','web'] for p in (ROOT/d).rglob('*') if p.is_file()}
(SCR/'baseline.json').write_text(json.dumps(manifest),encoding='utf-8')
for table in ['items','mobs','mob_drops','mob_spawns']:
    cols=sql(f"SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='faithro_web' AND TABLE_NAME='{table}' ORDER BY ORDINAL_POSITION").splitlines()
    pairs=','.join("'%s',`%s`"%(c,c) for c in cols)
    data=sql(f'SELECT JSON_OBJECT({pairs}) FROM faithro_web.`{table}`')
    (SCR/(table+'.json')).write_text(json.dumps([json.loads(x) for x in data.splitlines()],ensure_ascii=False),encoding='utf-8')
q="SELECT TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME,COLUMN_TYPE FROM information_schema.COLUMNS WHERE (TABLE_SCHEMA='ragnarok_log' AND TABLE_NAME IN ('zenylog','picklog','mvplog','npclog')) OR (TABLE_SCHEMA='ragnarok' AND TABLE_NAME IN ('char','login','acc_reg_num')) ORDER BY TABLE_SCHEMA,TABLE_NAME,ORDINAL_POSITION"
(SCR/'schema.tsv').write_text(sql(q),encoding='utf-8')
q="SELECT 'accounts',COUNT(*) FROM ragnarok.login UNION ALL SELECT 'chars',COUNT(*) FROM ragnarok.char UNION ALL SELECT 'mvplog',COUNT(*) FROM ragnarok_log.mvplog UNION ALL SELECT 'zenylog',COUNT(*) FROM ragnarok_log.zenylog; SELECT char_id,base_level,job_level,class,zeny FROM ragnarok.char; SELECT type,amount FROM ragnarok_log.zenylog; SELECT varname,value FROM ragnarok.mapreg WHERE varname REGEXP '^\\\\$S[0-9]+$';"
(SCR/'population.tsv').write_text(sql(q),encoding='utf-8')
print('Baseline files:',len(manifest),'data collected')
```

### A02, mapas, curva, HP, ASPD e bolsa

Arquivo `analyze.py`, SHA256 `6c4a3877edc4fd2c621fc9c9dfefb749c151eca29c0816e94d21893a1f172a05`.

```python
import sys,pathlib,json,re,math,random,csv,importlib.util,collections,statistics
S=pathlib.Path(__file__).parent; sys.path.insert(0,str(S/'lib312'))
sys.dont_write_bytecode=True
import yaml
R=pathlib.Path(r'C:\Development\Workspace\VPS OCI NVMe 2'); D=S/'remote'
def load(n): return json.loads((S/(n+'.json')).read_text(encoding='utf-8'))
M={r['id']:r for r in load('mobs')}; I={r['id']:r for r in load('items')}; drops=load('mob_drops'); sp=load('mob_spawns')
mobraw={e['Id']:e for e in yaml.safe_load((D/'db/pre-re/mob_db.yml').read_text(encoding='utf-8'))['Body']}
for mid,m in M.items():
    raw=mobraw.get(mid,{})
    # MD_AGGRESSIVE=0x4, enum e_aegis_monstertype in mob.hpp.
    ai=int(str(raw.get('Ai','6')),10)
    if ai in [4,5,8,9,10,11,12,13,19,20,21,26,27] and raw.get('Modes',{}).get('Aggressive',True): m['modes']+=' Aggressive'
spec=importlib.util.spec_from_file_location('prog',R/'tools/gen_progression.py'); prog=importlib.util.module_from_spec(spec); spec.loader.exec_module(prog)
spec=importlib.util.spec_from_file_location('boost',R/'tools/gen_mob_boost.py'); boost=importlib.util.module_from_spec(spec); spec.loader.exec_module(boost)
def f(n): return f'{n:,.0f}'.replace(',','.')
def tab(headers,rows): return '\n'.join(['| '+' | '.join(headers)+' |','|'+'---|'*len(headers)]+['| '+' | '.join(map(str,r))+' |' for r in rows])+'\n'
out=[]
def put(t): out.append(t)
z=collections.defaultdict(float)
for d in drops:
    if not d['mvp']: z[d['mob_id']]+=d['rate_final']/10000*I[d['item_id']]['sell']
records=[]
for line in (D/'npc/pre-re/scripts_monsters.conf').read_text().splitlines():
    mt=re.match(r'^\s*npc:\s*(\S+)',line)
    if not mt: continue
    p=D/mt[1]
    if not p.exists(): continue
    for ln,raw in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines(),1):
        m=re.match(r'^(\w+),\d+,\d+(?:,\d+,\d+)?\t+(boss_)?monster\t+[^\t]*\t+(\d+),(\d+)(.*)',raw)
        if not m: continue
        mp,boss,mid,n,tail=m.groups(); mid=int(mid); n=int(n)
        if mid not in M: continue
        parts=tail.split(','); delays=[]
        for x in parts[1:3]:
            try: delays.append(int(x))
            except ValueError: delays.append(0)
        delays=(delays+[0,0])[:2]; seconds=max(1,(delays[0]+max(0,delays[1]-1)/2)/1000)
        factor=boost.BOOST.get(mp,1) if not boss and '::' not in tail and 'cleaner' not in p.name.lower() else 1
        records.append(dict(map=mp,id=mid,n=n,t=seconds,factor=factor,boss=bool(boss),file=mt[1],line=ln))
(S/'spawn_records.json').write_text(json.dumps(records),encoding='utf-8')
maps=collections.defaultdict(lambda:collections.defaultdict(float))
for r in records:
    mob=M[r['id']]
    if mob['is_mvp']: continue
    a=maps[r['map']]; a['n']+=r['n']; a['boostn']+=r['n']*r['factor']; a['wave']+=r['n']*z[r['id']]; a['boostwave']+=r['n']*r['factor']*z[r['id']]
    a['h']+=r['n']*z[r['id']]*3600/r['t']; a['boosth']+=r['n']*r['factor']*z[r['id']]*3600/r['t']
    a['exp']+=r['n']*mob['base_exp']*300; a['hp']+=r['n']*mob['hp']
put('## Top 20 por oferta de respawn, sem MVP\n'+tab(['Mapa','spawn oficial/final','z/limpeza of./final','M z/h of.','M z/h final'],[(k,f(a['n'])+'/'+f(a['boostn']),f(a['wave'])+'/'+f(a['boostwave']),f"{a['h']/1e6:.2f}",f"{a['boosth']/1e6:.2f}") for k,a in sorted(maps.items(),key=lambda x:-x[1]['boosth'])[:20]]))
put('## Top20 sem boost\n'+tab(['Mapa','M z/h'],[(k,round(a['h']/1e6,2)) for k,a in sorted(maps.items(),key=lambda x:-x[1]['h'])[:20]]))
route=['prt_sewb2','prt_sewb3','iz_dun02','hu_fild04','hu_fild07','alde_dun03','juperos_01','juperos_02','abbey01','man_fild02','spl_fild01','in_sphinx4','in_sphinx5','ve_fild06','odin_tem03','abbey03','tha_t09','lhz_dun03','thor_v01','thor_v03','moc_fild21','moc_fild22','abyss_03']
rows=[]
for k in route:
    a=maps.get(k)
    if not a: continue
    avgexp=a['exp']/a['n']; avghp=a['hp']/a['n']; avgz=a['wave']/a['n']
    dps=500 if k in route[:3] else 1500 if k in route[3:6] else 5000 if k in route[6:13] else 15000 if k in route[13:17] else 30000
    kills=min(3600/(avghp/dps+8),sum(r['n']*r['factor']*3600/r['t'] for r in records if r['map']==k and not M[r['id']]['is_mvp']))
    rows.append((k,f(a['n'])+'/'+f(a['boostn']),f(avghp),round(avgexp/1e6,3),f(avgz),dps,round(kills),round(kills*avgexp/1e9,3),round(kills*avgz/1e6,3)))
put('## Rotas modelo\n'+tab(['mapa','n oficial/final','hp medio','M exp/kill','z/kill','DPS','kills/h','G exp/h','M z/h'],rows))
put('## Mobs selecionados\n'+tab(['id/nome','lv','HP','EXP300','ATK2','DEF/MDEF','agressivo','z/kill'],[(str(m['id'])+'/'+m['aegis'],m['level'],f(m['hp']),f(m['base_exp']*300),f(m['attack2']),str(m['defense'])+'/'+str(m['magic_defense']),'sim' if 'Aggressive' in m['modes'] else 'não',f(z[m['id']])) for m in M.values() if m['aegis'] in ['ANUBIS','SLEEPER','SKOGUL','SKEGGIOLD','KASA','SALAMANDER','SEYREN','EREMES','HOWARD','MAGALETA','SHECIL','KATRINN','NECROMANCER','GOLD_ACIDUS','VENATU_1','TATACHO','CORNUS','DOLLOMEDES'] or (m['level']>100 and m['class']=='Normal' and not m['is_mvp'])]))
put('## MVPs\n'+tab(['id/nome','HP','ATK2','DEF/MDEF','TTK a 10k/30k DPS'],[(str(m['id'])+'/'+m['aegis'],f(m['hp']),f(m['attack2']),str(m['defense'])+'/'+str(m['magic_defense']),str(round(m['hp']/10000,1))+'/'+str(round(m['hp']/30000,1))) for m in M.values() if m['is_mvp'] and m['aegis'] in ['BAPHOMET','DARK_LORD','LORD_OF_DEATH','PHARAOH','IFRIT','RANDGRIS','SATAN_MOROCC','MOROCC','BEELZEBUB','BEELZEBUB_','GOLDEN_BUG','TAO_GUNKA']]))
put('## Pontos e EXP\n'+str({'c185':prog.cost_to(185),'c150':prog.cost_to(150),'pts255':prog.stat_points()[255],'pts99':prog.stat_points()[99],'total99':sum(prog.extended_curve(100000000)[l] for l in range(99,255))}))
curve=list(csv.DictReader((R/'docs/progressao.csv').open(encoding='utf-8')))
put(tab(['faixa','EXP','h 300/h alvo'],[(f'{lo}->{hi}',f(sum(int(r['exp_trans_para_proximo']) for r in curve if lo<=int(r['nivel'])<hi)),round(sum(int(r['exp_trans_para_proximo']) for r in curve if lo<=int(r['nivel'])<hi)/(300*e),3)) for lo,hi,e in [(1,99,4e6),(99,150,3e6),(150,200,10e6),(200,255,30e6),(254,255,30e6)]]))
jobs={}
for fn in ['job_stats.yml','job_aspd.yml','job_basepoints.yml','job_exp.yml']:
    for e in yaml.safe_load((D/'db/pre-re'/fn).read_text(encoding='utf-8'))['Body']:
        for j in e['Jobs']: jobs.setdefault(j,{}).update({k:v for k,v in e.items() if k!='Jobs'})
(S/'jobs.json').write_text(json.dumps(jobs),encoding='utf-8')
def hp(j,L,vit,trans=True):
    e=jobs[j]; base={p['Level']:p['Hp'] for p in e.get('BaseHp',[])}.get(L)
    if base is None: base=35+math.floor(L*e.get('HpIncrease',500)/100)+sum(math.floor(e.get('HpFactor',0)/100*i+0.5) for i in range(2,L+1))
    return int(base*(1+vit/100)*(1.25 if trans else 1))
def spcalc(j,L,int_,trans=True):
    e=jobs[j]; base={p['Level']:p['Sp'] for p in e.get('BaseSp',[])}.get(L)
    if base is None: base=10+math.floor(L*e.get('SpIncrease',100)/100)+sum(math.floor(e.get('SpFactor',0)/100*i+0.5) for i in range(2,L+1))
    return int(base*(1+int_/100)*(1.25 if trans else 1))
put('## HP/SP VIT/INT total 185 trans e 150 baby\n'+tab(['Classe','Hf/Hi/Si','HP99','HP150','HP255','SP99/150/255'],[(j,str((jobs[j].get('HpFactor',0),jobs[j].get('HpIncrease',500),jobs[j].get('SpIncrease',100))),*[f(hp(j,L,150 if j.startswith('Baby_') else 185,not j.startswith('Baby_'))) for L in [99,150,255]],'/'.join(f(spcalc(j,L,150 if j.startswith('Baby_') else 185,not j.startswith('Baby_'))) for L in [99,150,255])) for j in prog.TRANS_JOBS+prog.EXPANDED_JOBS]))
put('## ASPD AGI/DEX total 185 (sem passivas/buffs)\n'+tab(['Classe','arma','delay','ASPD'],[(j,w,b,round(200-(b-b*925//1000)/10,1)) for j in prog.TRANS_JOBS for w,b in jobs[j].get('BaseASPD',{}).items() if w in ['Bow','Katar','2hSword','2hAxe','Staff','Book','Knuckle','Musical','Whip','1hSpear']]))
put('## Job\n'+tab(['classe','cap','EXP job total','kills @30k job base x300'],[(j,jobs[j].get('MaxJobLevel'),f(sum(p['Exp'] for p in jobs[j].get('JobExp',[]) if p['Level']<jobs[j].get('MaxJobLevel',70))),math.ceil(sum(p['Exp'] for p in jobs[j].get('JobExp',[]) if p['Level']<jobs[j].get('MaxJobLevel',70))/(30000*300))) for j in ['Lord_Knight','High_Priest','Baby_Knight']]))
gear=sorted([dict(d,**{k:I[d['item_id']][k] for k in ['aegis','sell']}) for d in drops if not d['mvp'] and d['rate_final']==10000 and I[d['item_id']]['type'] in ['Weapon','Armor'] and I[d['item_id']]['sell']>100000 and M[d['mob_id']]['class']=='Normal' and not M[d['mob_id']]['is_mvp']],key=lambda d:-d['sell'])
put('## Equip garantido >100k '+str(len(gear))+'\n'+tab(['mob','item','sell','un/h 300 kills'],[(M[d['mob_id']]['aegis'],d['aegis'],f(d['sell']),300) for d in gear[:15]]))
# Stock: 1000 days, 7 ticks/day, 10 series, 1M shares/ticker, adequate capital held outside strategy.
def stock(start,lo,hi):
    rng=random.Random(20261018); prices=[start]*10; held=[False]*10; profit=0; cost=[0]*10; vals=[]; trades=0
    for day in range(1000):
        for tick in range(7):
            for i,p in enumerate(prices):
                p+=rng.randint(-6,6)
                if p<25:p+=3
                if p<50:p+=2
                if p>150:p-=2
                if p>175:p-=3
                p=max(1,p); prices[i]=p
                if not held[i] and p<=lo: cost[i]=p; held[i]=True;profit-=1500;trades+=1
                elif held[i] and p>=hi: profit+=(p-cost[i])*1000000-1500; held[i]=False;trades+=1
        vals.append(profit+sum((p-cost[i])*1000000 for i,p in enumerate(prices) if held[i]))
    return [start,lo,hi,round(profit/1000),round(vals[-1]/1000),trades,sum(held),max(prices)]
put('## Stock 1000 dias\n'+tab(['inicio','compra<=','vende>=','z/d realizado','z/d marcado','trades','posicoes abertas','preco max final'],[stock(st,l,h) for st in [0,100] for l,h in [(50,100),(50,150),(100,101)]]))
ev=(math.comb(6,4)*math.comb(34,2)+math.comb(6,5)*34)*1000000/math.comb(40,6)+5000000/math.comb(40,6)
put('Lottery EV '+str(ev)+' payout '+str(ev/4750))
print('\n'.join(out))
(S/'results.md').write_text('\n'.join(out),encoding='utf-8')
```

### A03, contagens, quests e refino

Arquivo `metrics.py`, SHA256 `4264980e83f6e942abfcdb7f78fa55faa4eea167995053ca2504601a765c1397`.

```python
import pathlib,json,re,random,statistics,collections,sys,math
S=pathlib.Path(__file__).parent;sys.path.insert(0,str(S/'lib312'));import yaml
R=pathlib.Path(r'C:\Development\Workspace\VPS OCI NVMe 2');D=S/'remote'
M={e['id']:e for e in json.loads((S/'mobs.json').read_text())};I={e['id']:e for e in json.loads((S/'items.json').read_text())};dr=json.loads((S/'mob_drops.json').read_text());sp=json.loads((S/'spawn_records.json').read_text());jobs=json.loads((S/'jobs.json').read_text())
raw={e['Id']:e for e in yaml.safe_load((D/'db/pre-re/mob_db.yml').read_text(encoding='utf-8'))['Body']}
print('COUNTS',len(I),len(M),len(dr),len(json.loads((S/'mob_spawns.json').read_text())),'parsed records',len(sp))
agg=collections.Counter()
for r in sp:agg[(r['id'],r['map'])]+=r['n']
db={(r['mob_id'],r['map']):r['amount'] for r in json.loads((S/'mob_spawns.json').read_text())}
print('SPAWN match',len(agg),len(db),'mismatches',sum(agg[k]!=v for k,v in db.items()))
normal=[m for m in M.values() if m['class']=='Normal' and not m['is_mvp'] and m['base_exp']>0 and m['level']>100]; spawned={r['id'] for r in sp}
print('NORMAL >100',[(m['id'],m['aegis'],m['attack2'],m['id'] in spawned) for m in normal]);print('MAX NORMAL',max((m['attack2'],m['aegis']) for m in M.values() if m['class']=='Normal' and not m['is_mvp'] and m['base_exp']>0));print('MAX MVP',max((m['attack2'],m['aegis'],m['id']) for m in M.values() if m['is_mvp']))
ar=(R/'server/npc/custom/faithro/ptbr/custom/etc/mvp_arena.txt').read_text(encoding='utf-8'); arrows=[]
for ln,line in enumerate(ar.splitlines(),1):
    mt=re.search(r'\bmonster\t[^\t]+\t(\d+),(\d+),(\d+),(\d+)',line)
    if mt:
        mid,n,d1,d2=map(int,mt.groups());arrows.append((mid,n,d1,d2))
print('ARENA',len(arrows),sum(x[1] for x in arrows),sum(x[1] for x in arrows if M[x[0]]['is_mvp']),collections.Counter((x[2],x[3]) for x in arrows))
print('ARENA kills/h upper',sum(n*3600000/(d1+(d2-1)/2) for mid,n,d1,d2 in arrows))
print('ARENA MVP card/h upper',sum(n*3600000/(d1+(d2-1)/2)*d['rate_final']/10000 for mid,n,d1,d2 in arrows for d in dr if d['mob_id']==mid and I[d['item_id']]['type']=='Card' and not d['mvp']))
room=(R/'server/npc/custom/faithro/ptbr/custom/etc/mvp_room.txt').read_text(encoding='utf-8');print('ROOM entries',len(re.findall(r'^\s*\d+[,;]',room[room.index('setarray .mvpid'):room.index('setarray .bossid')],re.M)))
rows=[]
for ln,l in enumerate((R/'server/npc/custom/faithro/ptbr/custom/itemmall.txt').read_text(encoding='utf-8').splitlines(),1):
    if '\tshop\t' not in l:continue
    for mid,p in re.findall(r'(\d+):(-?\d+)',l):
        mid,p=int(mid),int(p)
        if mid not in I:continue
        it=I[mid];p=it['buy'] if p<0 else p
        if it['sell']*1.24>p*.76:rows.append((mid,it['aegis'],ln,p,it['sell'],math.floor(it['sell']*1.24)-math.floor(p*.76)))
print('ARBITRAGE',len(rows),sorted(rows,key=lambda x:-x[-1])[:15])
for mid in [4145,5013,1169,678,616,603,617,969,984,985,1530,7058,2630,2629]:print('ITEM',mid,I.get(mid))
black='1062,1088,1183,1186,1200,1212,1220,1221,1234,1235,1244,1245,1250,1268,1290,1293,1294,1296,1298,1299,1300,1301,1303,1304,1305,1306,1308,1309,1311,1313,1515,1588,1618,1676,1677,1678,1679,1796,1797,1974,1975,1976,1977,1978,1979'
c=[]
for m in M.values():
    e=raw[m['id']]
    if m['id']<2000 and m['base_exp']>0 and m['job_exp']>0 and m['class']!='Boss' and str(m['id']) not in black and not e['AegisName'].startswith(('meta','E_')) and any('_Card' in d['Item'] or '_card' in d['Item'] for d in e.get('Drops',[])[2:10]):c.append(m)
rng=random.Random(20261018); vals=[]
for _ in range(100000):
    choices=rng.sample(c,4);n=rng.randint(40,70);vals.append(n*4*sum(m['level'] for m in choices)*60)
vals.sort();print('HUNT projected candidates',len(c),'zeny min/theory',40*4*sum(sorted(m['level'] for m in c)[:4])*60,'max',70*4*sum(sorted((m['level'] for m in c),reverse=True)[:4])*60,'sim p05 mean p95',vals[4999],statistics.mean(vals),vals[94999])
print('BONUS',[(j,{s:sum(p.get(s,0) for p in jobs[j].get('BonusStats',[]) if p['Level']<=70) for s in ['Str','Agi','Vit','Int','Dex','Luk']}) for j in ['Lord_Knight','Sniper','Champion']])
for g in yaml.safe_load((D/'db/pre-re/refine.yml').read_text())['Body']:
    for lev in g['Levels']:
        print('REFINE',g['Group'],lev['Level'],[(a['Level'],[(b['Price'],b['Rate']) for b in a.get('Chances',[]) if b['Type']=='Normal']) for a in lev['RefineLevels'][:10]])
```

### A04,90 alocações

Arquivo `builds.py`, SHA256 `8de33b869c07695ca266ec7a924e45eb6777a86ef858d2e81dc0bcad74c806ac`.

```python
exec(compile(open(__file__.replace('builds.py','analyze.py'),encoding='utf-8').read(), 'analyze.py','exec'))
stat=['S','A','V','I','D','L']
profiles={
'Lord_Knight':['SAVDIL','SVDIAL','SVADIL'],
'High_Priest':['IVDSAL','IAVDSL','VSIDAL'],
'High_Wizard':['IDVSAL','IAVDSL','IVDSAL'],
'Whitesmith':['SAVDIL','SVDAIL','SVDIAL'],
'Sniper':['DAVISL','DAVLSI','DVLASI'],
'Assassin_Cross':['SAVDIL','SVDIAL','SALDVI'],
'Paladin':['VSDAIL','SVDAIL','IVDSAL'],
'Champion':['SIDVAL','SVDAIL','SAVDIL'],
'Professor':['IDVSAL','IAVDSL','VIDSAL'],
'Stalker':['DAVISL','SAVDIL','VDIASL'],
'Creator':['IVDSAL','SAVDIL','DILVSA'],
'Clown':['DIVASL','DAVISL','VDIASL'],
'Gypsy':['DIVASL','DAVISL','VADISL']}
pair=dict(zip(prog.EXPANDED_JOBS,prog.TRANS_JOBS)); pair.update({'Lord_Knight2':'Lord_Knight','Paladin2':'Paladin'})
def alloc(order,cap,budget):
    a={k:1 for k in stat}
    for s in order:
        for n in range(2,cap+1):
            if sum(prog.cost_to(v) for v in a.values())-prog.cost_to(a[s])+prog.cost_to(n)<=budget:a[s]=n
            else:break
    return '/'.join(str(a[k]) for k in stat),sum(prog.cost_to(v) for v in a.values())
rows=[]
for j in prog.TRANS_JOBS+prog.EXPANDED_JOBS:
    p=pair.get(j,j);p=pair.get(p,p);cap=150 if j.startswith('Baby') else 185;budget=7185 if cap==150 else 7237
    orders=profiles[p]
    if cap==150:
        lows=['I','A','L'] if p in ['Lord_Knight','Whitesmith','Assassin_Cross','Paladin','Champion','Stalker'] else ['S','A','L']
        orders=[''.join(k for k in orders[i] if k!=low)+low for i,low in enumerate(lows)]
    v=[alloc(o,cap,budget) for o in orders];rows.append((j,*[x[0] for x in v],'/'.join(str(x[1]) for x in v)))
(S/'builds.md').write_text(tab(['Classe','PvM','MVP','PvP/WoE','custo'],rows),encoding='utf-8')
print('BUILDS',rows[:2]); print('BABY',rows[-1])
```

### A05,ASPD com bônus de job e cenários

Arquivo `final_metrics.py`, SHA256 `404223f0282e5e9444013fb0414b21331adfb285c83e6ad7c38ddb6fc35e3c25`.

```python
exec(compile(open(__file__.replace('final_metrics.py','analyze.py'),encoding='utf-8').read(),'analyze.py','exec'))
rows=[]
for j in prog.TRANS_JOBS:
    b={s:sum(e.get(s,0) for e in jobs[j].get('BonusStats',[]) if e['Level']<=70) for s in ['Agi','Dex']}
    for w,d in jobs[j].get('BaseASPD',{}).items():
        if w not in ['Bow','Katar','2hSword','2hAxe','Staff','Book','Knuckle','Musical','Whip','1hSpear']:continue
        agi=185+b['Agi']; dex=185+b['Dex'];motion=d-d*(4*agi+dex)//1000
        rows.append((j,w,f"{agi}/{dex}",max(0,motion),f'{min(197,200-motion/10):.1f}'))
(S/'aspd-job.md').write_text(tab(['Classe','arma','AGI/DEX com job70','amotion sem cap','ASPD final sem buff'],rows),encoding='utf-8')
print('ASPD JOB',rows)
rew=[(984,10),(985,10),(601,100),(603,8),(617,4),(616,1),(604,10),(969,3),(985,10),(505,20)]
print('RPS EV',sum(I[mid]['sell']*n for mid,n in rew)/20)
for j in ['Lord_Knight','Sniper','Champion']:
    b={s:sum(e.get(s,0) for e in jobs[j].get('BonusStats',[]) if e['Level']<=70) for s in ['Vit','Int']};print('NAT185',j,hp(j,255,185+b['Vit']),spcalc(j,255,185+b['Int']))
for k in ['gefenia03','tha_t09','lhz_dun03','juperos_02','abyss_03']:
    a=maps[k];h=a['hp']/a['n'];avgz=a['wave']/a['n'];print('FARM',k,avgz,'at300',avgz*300,'dps30k',3600/(h/30000+8)*avgz,'aoe3',3600/(h/30000+8)*avgz*3)
spawned={r['id'] for r in records}; elite=[m for m in M.values() if m['class']=='Normal' and not m['is_mvp'] and m['base_exp']>0 and m['id'] in spawned]; print('MAX active normal',max((m['attack2'],m['aegis']) for m in elite))
eq=sorted([d for d in drops if not d['mvp'] and d['rate_final']==10000 and I[d['item_id']]['type'] in ['Armor','Weapon'] and d['mob_id'] in spawned],key=lambda d:-I[d['item_id']]['sell']);print('GEAR guaranteed',len(eq),[(M[d['mob_id']]['aegis'],I[d['item_id']]['aegis'],I[d['item_id']]['sell']) for d in eq[:10]])
for id in [1986,1987,1989,1992,1993,1994,2017,2018,2024]: print('HIGHMAP',id,sorted({r['map'] for r in records if r['id']==id}))
```

### A06,dependência SQL e fontes adicionais

Arquivo `extra.py`, SHA256 `8f809bdb56f27e453027c9d1ab1035fa8e8ad2f30ac84fa984e376051aa5ea6e`.

```python
import pathlib,re,subprocess,shlex,json
S=pathlib.Path(__file__).parent; R=pathlib.Path(r'C:\Development\Workspace\VPS OCI NVMe 2')
def ssh(c):
    p=subprocess.run(['ssh','faithro',c],capture_output=True)
    if p.returncode: raise RuntimeError(p.stderr.decode('utf-8'))
    return p.stdout.decode('utf-8')
def sql(q):return ssh('mysql -uroot -N -B --raw --default-character-set=utf8mb4 -e '+shlex.quote(q))
p=R/'server/npc/custom/faithro/ptbr/custom/quests/hunting_missions.txt'; t=p.read_text(encoding='utf-8')
black=''.join(re.findall(r'"([\d,]+)"',t[t.index('.Blacklist$ ='):]))
q="SELECT JSON_OBJECT('id',ID,'name',name_aegis,'level',level,'exp',base_exp,'job',job_exp) FROM ragnarok.mob_db WHERE left(name_aegis,4) != 'meta' AND left(name_aegis,2) != 'E_' AND base_exp>0 AND job_exp>0 AND (class != 'boss' OR class is null) AND (drop3_item like '%_card' OR drop4_item like '%_card' OR drop5_item like '%_card' OR drop6_item like '%_card' OR drop7_item like '%_card' OR drop8_item like '%_card' OR drop9_item like '%_card' OR drop10_item like '%_card') AND ID<2000 AND instr('"+black+"',ID)=0 ORDER BY ID"
(S/'hunting.sql').write_text(q,encoding='utf-8')
try:(S/'hunting.json').write_text(json.dumps([json.loads(x) for x in sql(q).splitlines()]),encoding='utf-8')
except RuntimeError as e:print('Hunting SQL:',e);(S/'hunting.json').write_text('[]')
for rel in ['src/map/mob.hpp','src/map/npc.cpp','src/map/skills/acolyte/asurastrike.cpp','src/map/skills/archer/doublestrafe.cpp','src/map/skills/thief/sonicblow.cpp','src/map/skills/mage/stormgust.cpp','db/skill_damage_db.yml','db/pre-re/refine.yml','db/pre-re/skill_tree.yml','db/import/skill_damage_db.yml','conf/battle_athena.conf','db/job_stats.yml','db/mob_avail.yml']:
    dst=S/'remote'/rel; dst.parent.mkdir(parents=True,exist_ok=True)
    a=subprocess.run(['scp','-q','faithro:/home/rathena/rathena/'+rel,str(dst)],capture_output=True)
    if a.returncode:print('unavailable',rel)
log=ssh("zgrep -Ein 'NPC.*[Pp]rice|[Ss]ell.*[Bb]uy|[Bb]uy.*[Ss]ell|[Pp]rice.*[Ll]ower|[Pp]rice.*[Hh]igher|[Pp]rice.*[Cc]heap|[Ss]hop.*[Ww]arn|exploit' /var/log/rathena/map.log /var/log/rathena/map.log.1.gz || true")
(S/'shoplog.txt').write_text(log,encoding='utf-8');print('hunting',len(json.loads((S/'hunting.json').read_text())), 'shop log',len(log))
files=[]
for fn in ['scripts_faithro.conf','optional.conf']:
    files+=re.findall(r'^npc:\s*(\S+)',(R/'server/npc/custom/faithro'/fn).read_text(encoding='utf-8'),re.M)
outs=[]
for rel in files:
    p=R/'server'/rel
    if not p.exists():continue
    lines=p.read_text(encoding='utf-8').splitlines();outs.append('\n## '+rel+f' ({len(lines)} linhas)')
    for i,l in enumerate(lines,1):
        if l.lstrip().startswith('//') or l.lstrip().startswith('mes '):continue
        if re.search(r'\b(getitem\w*|delitem\w*|Zeny|zeny|BaseLevel|JobLevel|BaseExp|JobExp|setarray|OnClock\w*|[\w.]*[Dd]elay[\w.]*|[\w.]*[Cc]ost[\w.]*|[\w.]*[Pp]rice[\w.]*|[\w.]*[Tt]imeout[\w.]*)\b|Treasure_Token|^\s*(if|set |\.[A-Za-z_]+\s*=)|\bshop\b',l):
            outs.append(f'{i}: {l.strip()}')
(S/'npc-audit.txt').write_text('\n'.join(outs),encoding='utf-8');print('audit files',len(files))
```

## Apêndice D. Verificação da entrega

A baseline SHA256 abrange 293 arquivos preexistentes em `docs/`, `server/`, `tools/` e `web/`. Esta sessão escreveu somente o estudo e a linha de link em `docs/balanceamento.md`; removeu os dois caches Python que suas importações haviam criado em `tools/__pycache__`. Scripts e resultados ficaram no scratchpad. O texto anterior de balanceamento foi mantido, com normalização de quebras de linha pelo editor e acréscimo do link, sem reescrever decisões.

A comparação final também detectou trabalho paralelo: criação de `docs/drops.md` e `server/db/import/mob_item_ratio.yml`, alteração de `server/conf/import/battle_conf.txt` e do cache de testes de `web/`. Esses arquivos não foram editados nem revertidos por esta sessão. Por isso não seria correto afirmar que a pasta inteira mudou apenas nos dois documentos.

Esta pasta de trabalho não tem metadados Git, e `git status --short` retornou “not a git repository”. Não se pode certificar status Git limpo aqui; registrou-se a comparação SHA256, sem inicializar repositório. As consultas remotas foram de leitura, cópias scp tiveram destino local, e nenhum script foi enviado à VPS para execução. As 27 consultas SELECT/CTE documentadas foram validadas contra o schema real, sem erro; resultados vazios por ausência de jogadores foram preservados. A checagem final da configuração na VPS ainda mostrou as rates da fotografia usada no estudo.

## Publicação deste registro

Esta análise foi produzida na cópia operacional local e em consultas de leitura à VPS.
Os caminhos `server/`, `web/`, `tools/` e `docs/drops.md` citados descrevem aquela fotografia;
eles não correspondem necessariamente à árvore do GitHub usada para publicar o estudo.
Por isso as referências a arquivos do overlay são caminhos textuais, não links para arquivos
que este PR não inclui. O PR acrescenta somente este estudo e o documento anterior de
balanceamento, que ainda não estava versionado nesse remoto; localmente, o documento anterior
recebeu apenas o apontamento para o estudo, além da normalização de quebras de linha.

Impacto operacional desta publicação: nenhum ajuste de gameplay ou implantação. Para testar
a documentação, conferir UTF-8, ausência de travessões, os 65 arquivos no inventário, as 90
alocações, os blocos de análise e os links documentais. Os resultados de consultas e simulações
são a fotografia de 18/10/2026, não evidência nova produzida pelo CI. Rollback: reverter o
commit desta publicação por um novo PR, sem editar histórico nem executar deploy.
