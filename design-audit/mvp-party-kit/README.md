# Rodada: Loteria implantada e validação conjunta de MVP

## Estado da produção

A primeira consulta ainda encontrou um personagem conectado. Depois das tarefas
locais, a nova conferência encontrou zero; o executor voltou a exigir zero em dois
checkpoints antes da parada. A alteração textual ensaiada foi implantada em
19/10/2026 às 04:11:44 de São Paulo (07:11:44 UTC), em janela de 3,75 s.
Somente `rathena-map` foi reiniciado. O texto agora anuncia **20h45 (horário de
São Paulo)**; o evento `OnClock2045`, preço e premiação não foram alterados.

Backup: `/var/backups/faithro/npc-lottery-time-20261019T071144Z.tar.gz`.
SHA-256: `ce66f9809cd5ab7846b42de49f6db2566f502f6cbc854bb867515d0ecd0e4470`.
Contém os originais instalado/espelho e manifesto, verificados antes da parada.
Backup e payload permanecem fora do Git. O overlay operacional local foi atualizado
para o mesmo conteúdo UTF-8 do espelho da VPS. O arquivo instalado continua CP1252.

`lottery-deployment.json` registra o deploy; `vps-preflight.json` é o estado anterior.
Os registros de rodadas anteriores que dizem “não implantado” continuam históricos.
O caminho de sucesso desta variante foi executado; não foi necessário rollback.
Uma reversão usa as duas cópias do backup com mapa parado em nova janela sem jogadores,
preservando atributos dos arquivos, seguida das mesmas verificações de prontidão.

## Verificação nativa posterior

`onboarding-post-lottery-deploy.json` usa a cópia **inalterada** do hash candidato
instalado. O helper agora aceita somente dois hashes conhecidos: o antigo, com patch
aplicado apenas na cópia privada, ou o candidato exato já implantado, sem reaplicar
o patch. Outros conteúdos são recusados. O arquivo de patch também tem hash fixo.

No laboratório descartável, com rede/PID/mount privados, banco novo e nenhuma conta
copiada da produção, o cliente recebeu o anúncio correto e pagou 4.750 zeny. A segunda
compra, no mesmo personagem e em outro da mesma conta, não debitou. Cada personagem
começou com 100 Red Potions e terminou com 99 após uso nativo, HP 1→40/40 e inventário
persistido. Faca e camisa permaneceram equipadas. Não houve combate, sorteio real ou
resgate de prêmio. Os PIDs de produção e char_conf não mudaram durante esse laboratório.

## O que o novo protocolo confere

`tools/analyze_balance_mvp.py` trabalha somente com JSON local. Cada tentativa tem
identificador próprio, alvo, resultado, cronômetro de combate e fichas de atacante/
suporte. Usa os controles Sniper e High Priest/Professor já preparados. Exige builds
exatas, dez slots, munição Arrow (1750) do atacante, painel observado e ausência de
mudanças de equipamento/atributos ou ajuda fora da party. O ambiente aceito é isolado,
com testadores group 0, sem bot ou operações administrativas durante a sessão.

As duas fichas usam a mesma janela operacional e o mesmo contador compartilhado de
chefe+invocações, calibrado previamente com dez abates conhecidos. O resultado agrega
esses abates uma única vez. O contador compartilhado nunca habilita métrica individual
de jogador no analisador de sessão. No resultado de morte da dupla, basta que ao menos
um participante tenha morrido; o suporte sobrevivente registra zero, sem inventar morte.
Vitória exige um abate do chefe, e falha exige zero abates do chefe.

Cada ledger continua fechando saldo, compras, vendas, recompensas e inventário.
Transferências internas de zeny e itens precisam aparecer nos dois lados e na lista
de transferências da tentativa; são canceladas na soma da party. Entrada ou saída
externa não declarada é recusada. Custos de compra e valor de estoque consumido são
resultados separados: não somar as duas medidas para produzir um “lucro líquido”.

O protocolo exige listas de habilidades usadas, buffs próprios e buffs recebidos.
Origem, nível e quantidade de aplicações recebidas precisam caber nas conjurações
declaradas pelo outro participante. Isso confere coerência entre fichas; não autentica
o efeito no servidor. Também não deduz consumo de reagentes pelo nome da skill,
não reconstrói SP a partir de cast/regen e não mede uptime ou DPS individual.
O observador deve declarar todos os consumíveis; revisão nativa continua necessária.

Combate tem até 600 s, dentro da sessão operacional completa. Timeout exige atingir
o limite com tolerância de cinco segundos; deslocamento, compras e recuperação não
são apagados dos custos ou do tempo operacional. Tentativas do painel são sequenciais.

## Matriz e uso

`matrix.json` tem **36 posições pendentes**: quatro chefes × solo/High Priest/
Professor × três repetições. Selecionar apenas uma classe de suporte mantém 24
tentativas. As classes de suporte ficam em condições separadas. Alvos e níveis
iniciais continuam GTB 99, Baphomet 150, Randgris/Ifrit 255. Os controles abaixo do
cap medem progressão; não representam DPS em nível constante se subirem de nível.

Os três `pending-gtb-*.json` são exemplos para preenchimento, sem resultados. Para
criar uma nova ficha, na raiz do repositório:

```sh
python tools/prepare_mvp_party.py --target 1086 --support High_Priest --output gtb-duo-1.json
python tools/analyze_balance_mvp.py gtb-duo-1.json
```

A segunda chamada deve recusar a ficha enquanto estiver pendente e não imprimir
métricas. O gerador usa criação exclusiva e não sobrescreve medições. Depois de
preencher observações reais, analisar uma tentativa pelo mesmo comando. Para o painel,
usar `--panel` seguido somente dos 24 ou 36 arquivos de tentativas preenchidas;
não incluir o manifesto, exemplos pendentes ou arquivos de verificação.

O painel exige três tentativas por alvo/condição, IDs únicos de tentativa e sessão,
ausência de sobreposição e observações declaradas reais. Dados `synthetic` só servem
ao teste individual do software e são recusados no painel. Falhas e timeouts entram
nos custos totais e no custo por vitória; quando não há vitória, esse quociente fica
desconhecido (`null`), sem divisão por zero ou falsa gratuidade.

## Aceite, confiança e limites

Confiança alta na alteração textual implantada e na consistência das regras cobertas
pelos **128 testes locais** e pelo laboratório nativo. A coleta não fornece confiança
em desempenho de combate: o piloto PvM continua 0/3 e as posições de MVP continuam
pendentes. Os testes de software incluem dados fictícios marcados como observados
apenas dentro das fixtures; isso não constitui sessão real nem foi publicado como tal.

Adotar o protocolo para revisar dados quando as fontes/builds de referência ainda
conferirem e cada participante tiver registros completos. Recusar comparações com
drift, financiamento externo, inventário incompleto, suporte diferente agrupado ou
falhas omitidas. Três repetições não demonstram superioridade nem autorizam nerfs.
Nenhum resultado deste pacote promove automaticamente balanceamento ou autentica
observação. Preservados EXP 300x, nível 255, atributos 185 e ASPD 197.

Impacto local: analisadores, gerador, exemplos, matriz, helper de QA, CI e documentação.
Reverter esses arquivos remove o protocolo novo; fichas individuais antigas mantêm
o escopo individual por padrão. Rollback do texto de produção é independente e usa
o backup indicado acima.
