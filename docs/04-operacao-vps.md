# Operação inicial da VPS

## Hardware atual

- 1 vCPU
- 2 GB RAM
- 50 GB armazenamento
- Ubuntu 22.04
- Localização: São Paulo, Brasil

Essa configuração é suficiente para desenvolvimento, alpha fechado e comunidade pequena. Para crescimento, observar CPU, RAM, uso de disco e latência.

## Hardening básico

Checklist recomendado:

- [ ] Criar usuário administrativo não-root.
- [ ] Configurar SSH por chave.
- [ ] Desabilitar login root por senha.
- [ ] Trocar senha inicial.
- [ ] Ativar firewall.
- [ ] Liberar apenas portas necessárias.
- [ ] Instalar fail2ban.
- [ ] Atualizar pacotes.
- [ ] Configurar backups automáticos.
- [ ] Configurar logs e rotação.

## Portas

As portas exatas dependem da configuração do emulador. Documente aqui:

| Serviço | Porta | Público? |
|---|---:|---|
| SSH | 22022 | restrito |
| Login server | 6900/tcp (confirmado em auditoria) | restrito ao IP autorizado (`ufw`) |
| Char server | 6121/tcp (confirmado em auditoria) | restrito ao IP autorizado (`ufw`) |
| Map server | 5121/tcp (confirmado em auditoria) | restrito ao IP autorizado (`ufw`) |
| Web server | 8888/tcp (padrão upstream); não implantado — sem unidade, processo ou porta em escuta | não implantado nesta auditoria |
| MariaDB | 3306 | não, apenas localhost |

> As portas de login, char e map foram **confirmadas por auditoria read-only**
> em 2026-07-10 (ver [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md)):
> processos vinculados a todas as interfaces, mas acesso externo restrito pelo
> `ufw` a um único IP autorizado, com política padrão `deny (incoming)`. O web
> server é **habilitado pelo código** para o baseline (`PACKETVER=20211103`) e
> seu binário está compilado na VPS, mas **não há unidade systemd, processo
> ativo nem porta em escuta** — implantação continua pendente. Detalhes de
> cliente, protocolo, obfuscação e web server em
> [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md).
> Unidades systemd, binários, dependências e runbook completo em
> [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md).

## Backups

Backups mínimos:

- Banco de dados.
- Configurações custom.
- NPCs custom.
- Scripts.
- Logs relevantes.

Retenção inicial:

- Diário por 7 dias.
- Semanal por 4 semanas.
- Mensal por 3 meses, se houver espaço.

## Deploy seguro

1. Abrir janela de manutenção.
2. Fazer backup.
3. Aplicar mudança em staging/dev.
4. Validar login/char/map.
5. Aplicar em produção.
6. Validar novamente.
7. Registrar changelog.
