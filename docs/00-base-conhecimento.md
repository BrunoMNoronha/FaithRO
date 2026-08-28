# Base de conhecimento inicial

## Visão

FaithRO - Laus Deo será um servidor old school/high rate, sem fins lucrativos, com foco em nostalgia e comunidade.

## Definição de old school no projeto

Para este projeto, “old school” significa:

- Sem 3ª classes.
- Progressão centrada em classes 1, 2, expanded e transclasses, a confirmar.
- Economia simples.
- MVP com NPCs essenciais, sem excesso de custom.
- Mecânicas inspiradas em pré-renewal, mesmo que o level máximo seja customizado.

## Ponto de atenção: base level 255, atributos máximos 185 e ASPD máxima 197 sem 3ª classe

Decisão vigente (estado-alvo, ainda não implantado):

- Base level máximo planejado: 255.
- Atributo/status natural máximo individual planejado: 185.
- ASPD máxima planejada: 197.
- Job level máximo: pendente de definição por classe.

Decisão histórica: o antigo base level máximo 185 foi substituído em
2026-07-10 por base level máximo 255. Decisão posterior: o atributo máximo
inicialmente registrado como 187 foi corrigido para 185, e a ASPD máxima
planejada foi definida em 197. Não confundir o antigo base level 185
(histórico revogado) com o atributo natural máximo vigente 185.

Base level 255, atributos naturais até 185 e ASPD máxima 197, com ausência de
3ª classe, são customizações de **impacto extremo**. Isso não é “pré-renewal
puro”, e os valores ainda não foram implantados ou validados operacionalmente
(issue #8). Exige balanceamento de:

- HP/SP por classe.
- Tabelas de EXP até 255.
- Pontos totais de status e custo dos atributos até 185.
- Dano de skills.
- Cast/ASPD (incluindo a ASPD máxima 197, por classe, arma e buffs).
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
| [15-cliente-primeiro-acesso.md](15-cliente-primeiro-acesso.md) | Fluxo planejado de primeiro acesso do jogador ao cliente. | Todos | pendente de validação | 09, 12, 16 | 2026-07-24 |
| [16-politica-distribuicao-cliente.md](16-politica-distribuicao-cliente.md) | Política de distribuição e auditoria dos downloads do cliente. | Todos | validado | 09, 10 | 2026-07-24 |
| [17-decisao-patcher-launcher.md](17-decisao-patcher-launcher.md) | Seleção do patcher/launcher (Beam Patcher principal, RPatchur reserva); protótipo local, sem produção. | Técnicos | validado | 15, 16, 10 | 2026-07-24 |
| [18-homologacao-patch-sintetico-beam.md](18-homologacao-patch-sintetico-beam.md) | Homologação sintética do fluxo do Beam (gerador determinístico, loopback, SHA-256, testes negativos); APROVADO COM RESTRIÇÕES. | Técnicos | validado | 17, 16 | 2026-07-25 |
| [19-preparacao-build-auditavel-beam.md](19-preparacao-build-auditavel-beam.md) | Preparação de build auditável do Beam (auditoria estática do commit fixado, manifesto, overlay de segurança de laboratório, plano de installation/build, validadores/CI). | Técnicos | validado | 18, 17 | 2026-07-25 |
| [20-primeiro-build-controlado-beam.md](20-primeiro-build-controlado-beam.md) | Reprodução, documentação do bloqueio da toolchain Rust 1.77.2 e seleção estática da candidata mínima Rust 1.85.0. | Técnicos | candidata selecionada | 19, 18, 17 | 2026-07-25 |
| [21-plano-instalacao-toolchain-rust-beam.md](21-plano-instalacao-toolchain-rust-beam.md) | Plano técnico de coexistência e futura instalação isolada da Rust 1.85.0-x86_64-pc-windows-msvc sem alterar default. | Técnicos | plano documentado | 20, 19 | 2026-07-25 |
| [22-instalacao-isolada-toolchain-rust-beam.md](22-instalacao-isolada-toolchain-rust-beam.md) | Registro e validação empírica da instalação isolada da Rust 1.85.0-x86_64-pc-windows-msvc sem build. | Técnicos | instalado e validado | 21, 20 | 2026-07-25 |
| [99-checklists.md](99-checklists.md) | Listas de verificação para deploy, rollback e manutenção. | Técnicos | pendente de validação | Nenhuma | 2026-07-10 |
