# Roadmap inicial

> Estado atualizado em 2026-07-11 por auditoria read-only da VPS. Itens marcados
> foram confirmados por evidência (serviços ativos, portas em escuta,
> configuração efetiva). Itens em gameplay permanecem estado-alvo, pendentes das
> issues #7/#8/#9.

## Fase 0 - Preparação

- [x] Criar repositório no GitHub.
- [x] Adicionar instruções de agentes.
- [ ] Definir licença do repositório próprio. *(pendente: `LICENSE_PENDING.txt`)*
- [x] Definir política legal e de assets. *(`SECURITY.md`, `CLAUDE.md`, docs/10)*
- [x] Criar quadro de issues. *(issues #2–#16)*

## Fase 1 - Ambiente de desenvolvimento

- [x] Subir ambiente local/dev. *(implantado diretamente na VPS)*
- [x] Compilar emulador. *(rAthena, commit `7f080871c`; binários login/char/map/web)*
- [x] Configurar MariaDB local. *(MariaDB 10.6.23 ativo, apenas `127.0.0.1:3306`)*
- [x] Criar banco de teste. *(bancos `faithro` e `faithro_log`)*
- [x] Validar login, char-server e map-server. *(unidades ativas, portas 6900/6121/5121 em escuta)*

## Fase 2 - Configuração de gameplay

- [ ] Definir rates (calculadas para base level 255).
- [ ] Configurar base level máximo 255 (decisão registrada; implantação pendente).
- [ ] Configurar atributo/status natural máximo individual 185 (decisão registrada; implantação pendente).
- [ ] Configurar ASPD máxima 197 (decisão registrada; implantação e validação pendentes).
- [ ] Definir job máximo por classe.
- [ ] Bloquear 3ª classes.
- [ ] Ajustar EXP table até 255 e curva de pontos de status.
- [ ] Ajustar drops.
- [ ] Definir NPCs essenciais.

## Fase 3 - VPS

- [x] Criar usuário não-root. *(`faithro`, grupo `sudo`)*
- [x] Configurar SSH por chave. *(porta 22022, `PubkeyAuthentication yes`)*
- [x] Desabilitar login root por senha. *(efetivo via `sshd_config.d/00-faithro-hardening.conf`: `PermitRootLogin no`, `PasswordAuthentication no`)*
- [x] Configurar firewall. *(`ufw` ativo, `deny (incoming)`; SSH liberado, portas de jogo restritas a IP autorizado)*
- [x] Configurar fail2ban. *(ativo/enabled, jail `sshd` entre outras)*
- [ ] Configurar backups. ⚠️ *Parcial: backups manuais existem e estão protegidos (`drwx------`, `config` + `mariadb`); rotina automática ainda pendente (issue #13).*
- [x] Configurar serviço systemd. *(unidades `faithro-login/char/map`, ativas/enabled)*

## Fase 4 - Alpha fechado

- [ ] Criar contas de teste.
- [ ] Testar progressão 1-255, atributos naturais até 185 e ASPD máxima 197.
- [ ] Testar troca de classe.
- [ ] Testar drops.
- [ ] Testar MVPs.
- [ ] Testar reinício do servidor.
- [ ] Coletar bugs.

## Fase 5 - Beta aberto

- [ ] Publicar regras.
- [ ] Publicar changelog.
- [ ] Monitorar CPU/RAM.
- [ ] Ajustar balanceamento.
