# Horário da Loteria: implantação preparada, pendente de janela

**Atualização posterior:** implantado em 19/10/2026 às 04:11 de São Paulo, quando
não havia personagens conectados. Registro, backup e verificação nativa em
[`../mvp-party-kit/README.md`](../mvp-party-kit/README.md). O restante desta seção
preserva o estado histórico da preparação.

A Loteria ainda anuncia **21h**, enquanto `OnClock2045` e o fuso
`America/Sao_Paulo`, sem override TZ no map-server, determinam 20h45. O candidato
textual já passou pelo laboratório nativo na rodada anterior. Preço, prêmio e
horário do evento permanecem iguais.

Nesta rodada, a consulta encontrou **um personagem conectado**. A condição para a
janela não foi satisfeita: não houve reinício de serviço, escrita nos NPCs, backup
novo ou implantação parcial. `preflight.json` e `health.json` registram a conferência.
Os cinco serviços continuam ativos, sem reinícios automáticos ou novos erros de
mapa após a prontidão. Site e healthcheck retornaram HTTP 200.

## Candidato e procedimento preparado

- Atual: `O sorteio ao vivo acontece às 21h.`
- Candidato: `O sorteio ao vivo acontece às 20h45 (horário de São Paulo).`
- Confiança: alta; uma mudança de fuso/evento exige rever a mensagem.
- Efeito esperado: anúncio coerente com o evento instalado.
- Risco: baixo para o texto, com interrupção do mapa exigida para carregamento.
- Adotar se os hashes ensaiados, evento e fuso ainda concordarem e não houver
  personagens conectados. Recusar se houver drift ou resultado funcional diferente.

`tools/deploy_lottery_text.py` é um executor manual específico para esse arquivo.
Não é iniciado por CI ou serviço. Recebe JSON por stdin com chave exata
`npc/custom/faithro/ptbr/custom/etc/lottery.txt` e campos `installed_base64`,
`before_sha256` e `after_sha256`. O payload contém a cópia CP1252 do candidato.
O hash fixo impede ampliar o conteúdo autorizado pelo payload.

Hash instalado esperado:
`4e1114ff73ca4add082087420ba7dbbba7dd9970b7adab9f30260c34d2eff819`.
Hash candidato esperado:
`9dbbb64a8e449fb6765ff246312b5e9491c688e96d4bd1848ca00e9b887b4119`.
Patch ensaiado: `post-deploy-review/lottery-time-candidate.patch`, SHA-256
`2173300a3b2204c4d09ef78d0c7713f01fbee3a1ff77239814ed2c12ba047cf8`.

Antes de parar o mapa, o executor confere serviços, dois checkpoints de zero online,
fuso, TZ, hash instalado, alteração textual exclusiva e equivalência do espelho.
O backup `/var/backups/faithro/npc-lottery-time-<UTC>.tar.gz` deve conter os dois
originais, seus atributos de arquivo e o manifesto; é aberto e conferido antes da
parada. A escrita preserva encoding, proprietário e permissões. Apenas rathena-map
é reiniciado; prontidão, logs e as referências 300x/255/185/197 são exigidas.

Em falha depois da parada, o próprio executor restaura as duas cópias originais e
inicia o mapa com nova verificação de prontidão. Uma reversão manual posterior deve
usar os dois arquivos desse backup, com mapa parado em nova janela sem jogadores;
repetir as mesmas verificações de saúde. Backups e payload ficam fora do Git.

Os testes desta preparação exercitaram recusas locais, com processos/banco/arquivos da VPS
substituídos por mocks. Não demonstram uma implantação ou restauração real desta
Loteria. Naquele momento, sucesso e rollback desta variante permaneciam sem execução;
a atualização acima registra a execução posterior do caminho de sucesso.
