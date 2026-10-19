# Custos-base, recuperação de NPC e próximo ensaio

## Resultado desta rodada

Cinco frentes: catálogo de recursos instalado; cálculo de custos-base; recuperação
nativa dos arquivos da Loteria; roteiro de EDP/piloto; regressões e leitura da VPS.
Não houve alteração de produção nem combate. EXP 300x, nível 255, atributos 185 e
ASPD 197 permanecem. Os registros anteriores de implantação continuam válidos.

## Requisitos e preços conferidos

`collect_resource_costs.py` leu 15 habilidades selecionadas, imports, requisitos e
ofertas literais de lojas ativas. Não executa SQL nem clientes. O catálogo inclui
hashes de `skill.cpp`, `battle.cpp`, databases e configurações relevantes.
`arrow_decrement=1` foi encontrado em `conf/battle/battle.conf:169`.

No banco instalado, Double Strafe tem dois acertos e exige uma flecha; Focused Arrow
Strike também exige uma. `battle_consume_ammo` usa a quantidade de munição da skill,
com mínimo de uma quando essa quantidade é zero, sob a flag de consumo. Não multiplicar
munição por acertos, inimigos atingidos ou linhas de dano. Os dois casos selecionados
têm `AmmoAmount=1`, explicitamente.

`skill_consume_requirement` distingue consumo anterior à execução (`type&1`) e
itens depois (`type&2`). `skill_get_requirement` aplica condições de itens/status;
há dispensas no código. Por isso, os eventos de cobrança de SP, itens e munição são
entradas separadas do calculador. Não são deduzidos do número de casts ou hits.

Preços mínimos literais antes de desconto: Red Potion 50, White Potion 1.200,
Blue Potion 5.000, Poison Bottle 50.000, Yellow/Blue Gemstone 600, Cobweb 200,
Arrow 1. Os fornecedores e linhas estão no catálogo. Declaração ativa de loja não
substitui verificar acesso e preço efetivo do comprador durante o ensaio.

## Cálculos independentes de exemplo

Cada linha usa a quantidade indicada de eventos de cobrança para os recursos
relevantes. Não constitui uma build, uma sessão ou uma taxa de farm.

| Habilidade / nível | Eventos supostos | SP-base | Itens | Valor de reposição |
| --- | ---: | ---: | --- | ---: |
| Double Strafe 10 | 100 | 1.200 | 100 Arrow | 100 |
| Focused Arrow Strike 5 | 100 | 3.000 | 100 Arrow | 100 |
| Safety Wall 10 | 10 | 400 | 10 Blue Gemstone | 6.000 |
| Land Protector 5 | 10 | 500 | 10 Blue + 10 Yellow | 12.000 |
| Resurrection 4 | 5 | 300 | 5 Blue Gemstone | 3.000 |
| Spider Web 1 | 10 | 500 | 10 Cobweb | 2.000 |
| EDP 5 | 10 | 1.000 | 10 Poison Bottle | 500.000 |

`analyze_resource_costs.py` confere o hash do catálogo, nível da habilidade, tabelas
de custo por nível e tipos/contagens. Preço ausente fica desconhecido, sem valor zero
inventado. O resultado é sempre cálculo de custo-base. SP-base não é variação líquida
de SP: regeneração, Soul Change, bônus, falhas e dispensas precisam de registro próprio.
Valor de estoque consumido continua separado do caixa de compras, evitando dupla cobrança.

```sh
python tools/analyze_resource_costs.py design-audit/resource-recovery-review/example-double-strafe.json
```

O exemplo contém somente contagens hipotéticas. `declared_charge_counts` identifica
contagens fornecidas pelo observador, sem autenticação automática. Este calculador
complementa a revisão manual; o gate de MVP não passou a inferir consumo por skill.

## Hipótese econômica de EDP

`Duration1` nominal de EDP 5 é 60 s. Um modelo de uma hora contínua, sem intervalos
ou perdas antecipadas, usa 60 frascos: **3.000.000 zeny de reposição**. O modelo
anterior de Juperos 2 usa 3.006,21 zeny de venda NPC esperada por abate, ponderada
pela composição estática do mapa. A 300 abates supostos, a venda bruta seria 901.863.
Seriam aproximadamente **998 abates/h**, nessa mesma composição, só para cobrir
frascos no valor esperado, antes dos demais custos e sem Overcharge.

Essa comparação não mede o ganho de EDP, os abates possíveis ou o lucro real.
Loot tem variação e composição de alvos real pode diferir. Não reduzir preço do
frasco ou habilidade apenas por esse cenário. A recomendação de confiança alta é
medir custo e benefício juntos; a rentabilidade permanece hipótese sem confiança
de desempenho. Adotar uso contínuo em uma rota apenas se repetições reais mostrarem
resultado econômico/sobrevivência favorável com custos completos. Descartar essa
hipótese de uso contínuo se a reposição superar repetidamente o benefício medido.

`edp-trial-protocol.json` especifica um estudo separado: SinX 255, mesmo equipamento
base a +0, Juperos 2, três pares de 30 min com EDP desligado/ligado em ordem alternada.
No cap não se inventa EXP efetiva. Registrar uptime real, perdas do buff, frascos,
recuperação, mortes, inventário e caixa. Não assumir 100% de cobertura ao analisar.
São seis sessões/180 min mais preparação, ainda não executadas.

## Recuperação nativa do backup

O modo manual `isolated_char_check.py --lottery-recovery-checks` restaurou as duas
cópias do backup revisado de 07:11:44 UTC dentro do laboratório privado: hashes,
UID/GID e modo recuperados. Verificou manifesto, lista exata de membros e o hash
fixo do arquivo `.tar.gz`. O destino é limitado à pasta temporária privada; o
mapa leu o arquivo antigo restaurado. O cliente confirmou anúncio antigo de 21h,
compra de 4.750 e bloqueio da segunda compra em dois personagens da mesma conta.
As poções também passaram, com 100→99 e cura 1→40/40.

A produção continuou no hash novo, anunciando 20h45, e seus cinco PIDs não mudaram.
O ensaio cobre restauração e carregamento dos arquivos NPC. Não foi uma restauração
de banco nem execução do rollback automático disparado por falha do deploy.
Os dados do ensaio são sintéticos em banco novo; não houve cópia de contas, combate,
prêmio ou sorteio real. CPU 25%, memória 512 MiB e limite 300 s foram preservados.

## Prontidão e próximos dados necessários

`pilot-readiness.json` confirma que os três controles do piloto PvM permanecem
pendentes: Sniper, SinX e HW, início 99, Juperos 2, 30 min cada. Nenhuma observação
real foi fornecida a este pacote. O laboratório automatizado dura no máximo cinco
minutos; ele não comporta uma sessão de 30 minutos ou substitui o ambiente persistente
de ensaio com acesso normal do testador. Esse ambiente e as três medições reais são
os próximos requisitos para um relatório de desempenho. A preparação não autoriza
combates em produção nem transforma testes de software em métricas de jogadores.

## Validação, confiança e reversão

Passaram **143 testes locais**, além do ensaio nativo de recuperação. A conferência
final encontrou cinco serviços ativos, nenhum erro novo de mapa, HTTP 200 e 13 fontes/
configurações com hashes esperados. A Loteria de produção e seu espelho permaneceram
na versão implantada; nenhuma unidade ou pasta de QA restou.

Confiança alta nos custos-base, integridade do backup e recuperação dos arquivos
ensaiados. Para usar o catálogo, conferir novamente seus hashes e a flag de munição;
se mudarem, recolher e rever os cálculos. Eficiência de classes e rentabilidade real
continuam sem medição. Nenhum resultado promove ajuste numérico automaticamente.

Arquivos: coletor de leitura e calculador local em `tools/`, extensão explícita do helper
de QA, testes/CI, catálogo, exemplos, hipóteses e registros nesta pasta. Reverter esta
rodada remove essas ferramentas/evidências e restaura o helper anterior. Não há
alteração desta rodada em produção a restaurar. O backup permanece na VPS, fora do Git.
