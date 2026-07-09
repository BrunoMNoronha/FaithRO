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
| Login server | a definir | sim |
| Char server | a definir | sim |
| Map server | a definir | sim |
| MariaDB | 3306 | não, apenas localhost |

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
