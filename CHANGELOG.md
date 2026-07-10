# Changelog

Todas as mudanças relevantes do FaithRO devem ser registradas aqui.

## [Não lançado]

- Decisão de gameplay alterada de base level 185 para base level 255, com
  status/atributo máximo individual planejado em 187 e job level máximo a
  definir por classe. Configuração, EXP, pontos de status e balanceamento
  permanecem pendentes da issue #8. Nenhuma alteração operacional foi
  realizada. (As menções a "level 185" em entradas anteriores deste changelog
  são registros históricos da decisão substituída.)
- Refinamento das evidências da decisão Pre-Renewal (`docs/03-configuracao-alvo.md`,
  `docs/10-fontes-comunitarias-rathena.md`, `docs/README.md`): tabelas
  reformuladas para distinguir decisão/estado-alvo de estado operacional;
  configuração de build Pre-Renewal (`config.log`, `-DPRERE`) tratada como
  "configuração registrada", sem atestar a proveniência dos binários
  atualmente em execução; removida a afirmação "Renewal nativa para níveis
  maiores" da comparação de mecânicas; level 185 mantido como customização
  pendente das issues #7/#8/#9 em ambos os modos. Nenhuma alteração
  operacional realizada.
- `docs/03-configuracao-alvo.md` reorganizado para registrar Pre-Renewal como
  referência mecânica oficial do FaithRO (issue #6), separando modo mecânico,
  conteúdo, episódio histórico, protocolo, classes permitidas e level máximo
  como conceitos independentes. Decisão apoiada em auditoria read-only do
  build instalado em `/opt/faithro/rathena`: `config.log` confirma
  `./configure --enable-prere=yes` com `-DPRERE` efetivamente presente nas
  `CPPFLAGS` de compilação, classificando o build como "Pre-Renewal
  confirmado no build". Episódio histórico permanece não fixado; conteúdo
  segue como curadoria pendente; level 185 e rates permanecem dependentes das
  issues #8 e #7; bloqueio de 3ª classes permanece dependente da issue #9.
  Nenhuma mudança operacional foi realizada (nenhum serviço reiniciado,
  nenhum binário recompilado). `docs/10-fontes-comunitarias-rathena.md`
  atualizado com a fonte `src/config/renewal.hpp` e a evidência de
  compilação (`config.log`).
- Correção do runbook de serviços systemd
  (`docs/11-servicos-systemd-rathena.md`): documentada a propagação de
  `Requires=` em parada/reinício explícitos, diferenciada de falha ou
  encerramento espontâneo (`Restart=on-failure` não propaga); adicionado
  pré-check obrigatório do MariaDB (`After=mariadb.service` não é dependência
  de ativação); removida a sequência redundante de restart das três unidades
  em favor de três cenários separados (map / char+map / cadeia completa via
  login); removida a evidência baseada em PIDs transitórios; adicionada seção
  "Falhas e recuperação da cadeia"; reformulada a descrição do ambiente para
  "VPS atual do projeto FaithRO". Adicionado resumo operacional em
  `docs/04-operacao-vps.md` ("Operação dos serviços rAthena"), atendendo aos
  critérios da issue #15.
- Documento de serviços systemd do rAthena adicionado
  (`docs/11-servicos-systemd-rathena.md`), com base em auditoria read-only na
  VPS em 2026-07-10: unidades `faithro-login.service`, `faithro-char.service`
  e `faithro-map.service` confirmadas (enabled, active, portas `6900`,
  `6121`, `5121`); commit instalado (`7f080871c`) confirmado idêntico ao
  commit upstream de referência; binário `web-server` confirmado compilado,
  porém sem unidade systemd, processo ou porta implantados. Nenhum serviço
  foi alterado durante a auditoria.
- `docs/04-operacao-vps.md`, `docs/09-cliente-baseline-protocolo.md` e
  `docs/10-fontes-comunitarias-rathena.md` atualizados para refletir os itens
  confirmados pela auditoria (nomes de unidades, commit instalado, estado do
  web server), substituindo pendências que já foram verificadas.
- Índice central da documentação criado (`docs/README.md`).
- Documento de cliente e protocolo adicionado (`docs/09-cliente-baseline-protocolo.md`):
  baseline `2021-11-03_Ragexe` / `PACKETVER=20211103`, distinção `Ragexe` × `PACKETVER_RE`,
  protocolo × Renewal/Pre-Renewal, packet obfuscation, web server,
  matriz de compatibilidade e plano de testes.
- Documento de fontes comunitárias adicionado (`docs/10-fontes-comunitarias-rathena.md`)
  com política e classificação de confiança das fontes.
- Tabela de portas em `docs/04-operacao-vps.md` atualizada com os padrões do rAthena.
- Correção do baseline de cliente e web server (referências fixadas no commit
  `7f080871c`): packet obfuscation descrita como macro definida, porém com chaves
  efetivas zero para clientes posteriores a `20180307` (sem obfuscação efetiva no
  baseline); `WEB_SERVER_ENABLE` confirmado como verdadeiro para `20211103`, com
  implantação e porta efetiva do web server ainda pendentes; índice passa a
  separar estado documental de estado de implantação.
- Comandos de consulta de logs em `docs/09-cliente-baseline-protocolo.md` passam a
  usar placeholders (`<UNIDADE-LOGIN>`, `<UNIDADE-CHAR>`, `<UNIDADE-MAP>`,
  `<UNIDADE-WEB>`) com etapa de descoberta via `systemctl`, em vez de presumir
  nomes de unidades systemd não documentadas no repositório.

## [0.1.0] - Planejamento inicial

- Documentação inicial criada.
- Instruções de agentes adicionadas.
- Roadmap inicial definido.
- Emulador recomendado: rAthena.
