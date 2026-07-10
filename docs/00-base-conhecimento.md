# Base de conhecimento inicial

## Visão

FaithRO - Laos Deos será um servidor old school/high rate, sem fins lucrativos, com foco em nostalgia e comunidade.

## Definição de old school no projeto

Para este projeto, “old school” significa:

- Sem 3ª classes.
- Progressão centrada em classes 1, 2, expanded e transclasses, a confirmar.
- Economia simples.
- MVP com NPCs essenciais, sem excesso de custom.
- Mecânicas inspiradas em pré-renewal, mesmo que o level máximo seja customizado.

## Ponto de atenção: level 185 sem 3ª classe

Level 185 com ausência de 3ª classe é uma decisão custom. Isso não é “pré-renewal puro”. Exige balanceamento de:

- HP/SP por classe.
- Tabelas de EXP.
- Dano de skills.
- Cast/ASPD.
- Equipamentos.
- MVPs.
- Economia.
- PvP/WoE, se forem habilitados.

## Política sem fins lucrativos

Recomendado:

- Sem venda de poder.
- Doações opcionais e transparentes, apenas para custo de hospedagem.
- Prestação de contas simples.
- Nenhum item exclusivo quebrando economia.

## Glossário

- Emulador: software servidor compatível com lógica de MMORPG.
- rAthena: emulador open-source em C++.
- Hercules: emulador open-source em C, com foco modular.
- NPC script: script de comportamento de NPCs.
- Rates: multiplicadores de experiência e drop.
- Pre-renewal: conjunto de mecânicas clássicas anteriores ao Renewal.

## Índice de documentos

| Documento | Finalidade | Público-alvo | Estado | Dependências | Última revisão |
| --------- | ---------- | ------------ | ------ | ------------ | -------------- |
| [00-base-conhecimento.md](00-base-conhecimento.md) | Centralizar visão, glossário e índice de toda a documentação. | Todos | validado | Nenhuma | 2026-07-10 |
| [01-decisao-tecnica.md](01-decisao-tecnica.md) | Registrar as decisões fundamentais do projeto. | Técnicos | pendente de validação | Nenhuma | 2026-07-10 |
| [02-roadmap.md](02-roadmap.md) | Guiar as etapas de desenvolvimento. | Todos | pendente de validação | 01 | 2026-07-10 |
| [03-configuracao-alvo.md](03-configuracao-alvo.md) | Registrar configurações desejadas do servidor. | Técnicos | pendente de validação | 01, 02 | 2026-07-10 |
| [04-operacao-vps.md](04-operacao-vps.md) | Guiar acesso, segurança e operação básica da VPS. | Infra/DevOps | pendente de validação | Nenhuma | 2026-07-10 |
| [05-governanca.md](05-governanca.md) | Definir fluxos, papéis e regras do repositório. | Todos | pendente de validação | Nenhuma | 2026-07-10 |
| [06-plano-execucao-inicial.md](06-plano-execucao-inicial.md) | Descrever a primeira fase de setup do ambiente. | Técnicos | pendente de validação | 02, 04 | 2026-07-10 |
| [07-fluxo-pull-request.md](07-fluxo-pull-request.md) | Padronizar como commits e PRs devem ser feitos. | Desenvolvedores | pendente de validação | 05 | 2026-07-10 |
| [08-preparar-vps-ubuntu-2204.md](08-preparar-vps-ubuntu-2204.md) | Procedimento de instalação das dependências. | Infra/DevOps | pendente de validação | 04 | 2026-07-10 |
| [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md) | Documentar baseline de cliente, protocolo e matriz de testes. | Técnicos | validado | 01, 12 | 2026-07-10 |
| [10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md) | Registrar e classificar fontes de pesquisa usadas no projeto. | Todos | validado | Nenhuma | 2026-07-10 |
| [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md) | Descrever os serviços systemd criados na implantação. | Infra/DevOps | pendente de validação | 08 | 2026-07-10 |
| [12-configuracao-packetver.md](12-configuracao-packetver.md) | Procedimento técnico (planejado) para alteração de PACKETVER e obfuscação. | Técnicos | validado | 09 | 2026-07-10 |
| [99-checklists.md](99-checklists.md) | Listas de verificação para deploy, rollback e manutenção. | Técnicos | pendente de validação | Nenhuma | 2026-07-10 |
