# MVPs: ameaças instaladas e suporte para ensaio

Esta rodada lê as fontes instaladas e prepara fichas. Nenhum combate foi executado,
nenhum resultado de jogador foi produzido e nenhum número de balanceamento mudou.
As evidências são `installed-threats.json`, `support-installed-data.json` e oito
cartões `support-*.json`, todos pendentes de medição.

## Quatro alvos e um limite comum

O painel anterior mantém três tentativas por alvo/modo e até 600 segundos de combate
por tentativa. A divisão HP/600 abaixo é um cálculo mínimo de dano entregue ao chefe
por segundo, depois das mitigações, supondo ausência de cura. Não estima DPS de classe,
não inclui invocações e não prova que uma build sobreviva.

| Alvo | HP instalado | Elemento | HP/600 | Spawn estático declarado |
| --- | ---: | --- | ---: | --- |
| GTB | 126.000 | Fogo 2 | 210,000 | prt_sewb4, 1 |
| Baphomet | 668.000 | Sombrio 3 | 1.113,333 | prt_maze03, 1 |
| Randgris | 3.567.200 | Sagrado 4 | 5.945,333 | odin_tem03, 1 |
| Ifrit | 7.700.000 | Fogo 4 | 12.833,333 | thor_v03, 1 |

Os spawns são declarações de arquivos ativos, sem afirmar que o chefe esteja vivo.
O ensaio usa uma cópia isolada com as mesmas definições; não disputar esses spawns
na produção. Cura do chefe eleva o dano bruto necessário. Reposicionamento, controle
de invocações e perda de uptime também elevam a exigência sobre os intervalos de ataque.

## Gatilhos que precisam aparecer na ficha

- **GTB:** Assumptio, Reflect Shield, ocultação, cura e invocações. Registrar tipo de
  ataque e interrupções; não atribuir uma diferença automaticamente à ASPD.
- **Baphomet:** Earthquake tem condição de HP 80, cast de 2 s e atraso de recast de
  30 s nas declarações attack/chase. Power Up tem condição de HP 30. Marcar a fase
  e o momento da morte ou abandono; as duas linhas de estado não são duas conjurações
  simultâneas.
- **Randgris:** Dispell tem atraso de 30 s, Earthquake usa condição de HP 30 e cast
  de 1 s. Thunderstorm tem `attackpcge,2`, cast de 1,5 s e atraso de 5 s. No código,
  essa condição compara `unit_counttargeted(md)` com 2; `unit.cpp` retorna
  `ud->target_count`. Registrar se o suporte também mantém o chefe como alvo.
  Tamanho da party ou simples presença perto do chefe não comprovam esse gatilho.
- **Ifrit:** Pneuma está declarado no estado idle, condicionado a `longrangeattacked`.
  Registrar o estado e a execução observados; não afirmar bloqueio permanente de
  Sniper a partir dessa linha. Full Strip, Land Protector, Dragon Fear e invocações
  entram no registro. Earthquake tem condição de HP 40, cast de 0,5 s e atraso de
  20 s; Power Up usa condição de HP 20.

`mob_skill_rate=100`, `mob_skill_delay=100` e `mob_max_skilllvl=100` foram conferidos
seguindo imports de configuração. Chance 10000 significa 100% em uma verificação
elegível; não significa frequência garantida. IA, estado, condições, prioridades e
habilidades em execução continuam relevantes. Fontes e hashes acompanham os dados;
leitura de fonte não autentica o binário em execução nem substitui observação nativa.

## Suporte com pontos e compra verificáveis

| Classe | Primeira classe | Segunda classe | Equipamento base, sem desconto |
| --- | ---: | ---: | ---: |
| High Priest | 44/49 | 22/69 | 50.000 zeny |
| Professor | 25/49 | 47/69 | 60.000 zeny |

Ambas usam 9/9 pontos de Noviço e assumem primeira classe no job 50 e segunda no
job 70. Os oito cartões cobrem 99, 150, 200 e 255, com os mesmos orçamentos naturais
1.325/2.722/4.597/7.237 já verificados. Jacket, Hood, Sandals e Staff/Book estão a +0,
sem cartas; todos os dez slots estão declarados. Compatibilidade, preço e origem
de loja foram conferidos. Este é um controle acessível para medir suporte; não é
uma recomendação de equipamento final para sobreviver a Ifrit ou Randgris.

High Priest inclui Heal, Blessing, Increase Agility, Pneuma, Magnificat, Assumptio
e Resurrection, com pré-requisitos. Professor inclui Safety Wall, Land Protector,
Dispell, Soul Change, Spider Web e Wall of Fog. Uma habilidade estar legalmente
disponível não prova que funcione contra o MVP; registrar tentativa e efeito real.

As fontes instaladas exigem Blue Gemstone para Safety Wall e Resurrection; Blue e
Yellow para Land Protector; Yellow para Dispell; Cobweb para Spider Web. Foram
encontradas ofertas literais ativas de gemas a 600 e Cobweb a 200, antes de desconto.
As habilidades de pré-requisito também estão alocadas: se forem usadas, registrar
seus custos. SP, tempo de cast e custos por habilidade estão em `skill_details`.
Não cobrar item de skill que não foi usada nem ignorar estoque inicial consumido.

## Roteiro da próxima medição

1. Executar primeiro o piloto PvM existente: Sniper, SinX e HW, início 99, Juperos 2,
   30 minutos corridos por classe. Ele continua em **0/3**; esta rodada não o substitui.
2. Para MVP, copiar a ficha do alvo já existente em `balance-session-kit/`. GTB inicia
   em 99, Baphomet em 150 e os dois finais em 255. Registrar nível final e progressão;
   não tratar os controles abaixo do cap como DPS em nível constante.
3. Selecionar **uma** alternativa de suporte para o painel inicial: solo e duo,
   quatro alvos, três repetições, total 24 tentativas. Testar High Priest e Professor
   separadamente cria três condições e **36 tentativas**, até seis horas de combate,
   além de preparação. Não agrupar as duas classes como se fossem o mesmo tratamento.
4. Calibrar o contador com dez abates conhecidos antes do lote. Em cada tentativa,
   registrar chefe e invocações separadamente, horário com fuso, tempo total da sessão
   e tempo específico de combate. Aplicar o limite de 600 s ao combate; deslocamento,
   compra e recuperação continuam no custo/tempo operacional completo.
5. Para cada participante: copiar o cartão de build, preencher painel real, buffs
   recebidos/perdidos, habilidades usadas, mortes, inventário e fluxo de zeny.
   Registrar transferências internas em ambas as fichas e eliminá-las ao somar a
   party. O analisador de sessão existente confere o ledger de uma ficha; **não**
   valida automaticamente todos os custos/buffs da dupla. Exigir revisão conjunta.
   A rodada posterior em `../mvp-party-kit/` acrescenta um protocolo e analisador
   conjunto para transferências, custos e coerência dos buffs declarados. As fichas
   v2 desta preparação não são automaticamente convertidas nem tratadas como observações.
6. Registrar vitória, morte, timeout e abandono. Não apagar falhas nem transformar
   invocações mortas em vitória do chefe. Comparar custo total por tentativa e por
   vitória, sobrevivência e uptime do atacante; não chamar efeito da dupla de ganho
   individual de DPS. Repetir antes de propor balanceamento.

## Confiança, aceite e reversão

Confiança alta nas declarações, preços literais e orçamentos desta coleta; a eficácia
das builds e do suporte ainda é desconhecida. Adotar os cartões como controle se o
laboratório preservar os hashes relevantes, a compra/equipamento funcionar e os
registros dos dois participantes fecharem. Descartar a comparação se houver ajuda
externa não declarada, mudança de equipamento/atributo dentro da tentativa ou ledger
incompleto. Falta de sobrevivência é um resultado válido do controle, não prova isolada
de necessidade de nerf. Registrar eventual próxima faixa de equipamento separadamente.

Esta rodada não sustenta ASPD 193 ou redução de habilidades. Remover os novos cartões,
coletores e documentos reverte a preparação; não há alteração do jogo a restaurar.
`prepare_support_cards.py` usa criação exclusiva e recusa sobrescrever cartões existentes.
