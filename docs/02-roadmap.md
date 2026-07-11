# Roadmap inicial

> Estado atualizado em 2026-07-11 por auditoria read-only da VPS. Itens marcados
> foram confirmados por evidência **na VPS** (serviços ativos, portas em escuta,
> configuração efetiva). A implantação na VPS **não** satisfaz os critérios de
> ambiente local/dev (Fase 1), que permanecem pendentes. Itens de gameplay
> permanecem estado-alvo, pendentes das issues #7/#8/#9.

## Fase 0 - Preparação

- [x] Criar repositório no GitHub.
- [x] Adicionar instruções de agentes.
- [ ] Definir licença do repositório próprio. *(pendente: `LICENSE_PENDING.txt`)*
- [x] Definir política legal e de assets. *(`SECURITY.md`, `CLAUDE.md`, docs/10)*
- [x] Criar quadro de issues. *(issues #2–#16)*

## Fase 1 - Ambiente de desenvolvimento

- [ ] Subir ambiente local/dev. *(pendente; a implantação atual está na VPS)*
- [ ] Compilar o emulador no ambiente local/dev. *(compilação na VPS validada
  (rAthena `7f080871c`), mas ambiente local ainda não comprovado)*
- [ ] Configurar MariaDB local. *(MariaDB implantado na VPS; instância local
  ainda não comprovada)*
- [ ] Criar banco de teste separado. *(`faithro` e `faithro_log` são bancos
  operacionais da VPS, não um banco de teste isolado)*
- [ ] Validar login, char-server e map-server localmente. *(validado na VPS;
  execução local ainda não comprovada)*

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
- [ ] Configurar e validar firewall. ⚠️ *Parcial: `ufw` ativo com `deny
  (incoming)` e regras aplicadas (SSH liberado, portas de jogo restritas a IP
  autorizado); teste explícito de conectividade/bloqueio ainda não comprovado
  (issue #11).*
- [ ] Configurar e validar fail2ban. ⚠️ *Parcial: serviço e jail `sshd` ativos;
  teste de bloqueio ainda não comprovado (issue #12).*
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
