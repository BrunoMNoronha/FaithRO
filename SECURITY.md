# Segurança

## Dados sensíveis

Nunca envie para o repositório:

- `.env`
- senhas
- tokens
- chaves SSH
- dumps reais
- backups
- dados pessoais de jogadores
- logs com IPs ou credenciais

## Reporte de vulnerabilidades

Abra uma issue privada ou comunique diretamente o mantenedor do projeto.

## Produção

Antes de qualquer deploy:

- backup do banco
- backup das configs
- teste em ambiente dev/staging
- plano de rollback
