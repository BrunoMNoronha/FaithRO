# Changelog

Todas as mudanças relevantes do FaithRO devem ser registradas aqui.

## [Não lançado]

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

## [0.1.0] - Planejamento inicial

- Documentação inicial criada.
- Instruções de agentes adicionadas.
- Roadmap inicial definido.
- Emulador recomendado: rAthena.
