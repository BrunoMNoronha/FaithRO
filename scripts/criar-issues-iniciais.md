# Como criar as issues iniciais no GitHub

Este guia contém instruções manuais para criar as issues iniciais do backlog técnico no repositório https://github.com/BrunoMNoronha/FaithRO. As issues devem ser criadas manualmente pela interface do GitHub (Issues > New issue), sem uso de GitHub CLI ou automação neste momento.

Para cada issue, use o template abaixo e ajuste os campos "Título", "Descrição" e "Critérios de aceite".

---

## 1. [Infra] Preparar VPS Ubuntu 22.04

**Descrição:** Preparar a VPS Ubuntu 22.04 (1 vCPU, 2 GB RAM, 50 GB) que servirá de base para o servidor, incluindo atualização do sistema e pacotes essenciais.

**Critérios de aceite:**
- [ ] Sistema atualizado (`apt update && apt upgrade`).
- [ ] Pacotes básicos instalados (git, curl, build-essential, etc.).
- [ ] Acesso SSH validado.

## 2. [Infra] Instalar dependências do rAthena

**Descrição:** Instalar as dependências necessárias para compilar e rodar o rAthena na VPS ou ambiente local.

**Critérios de aceite:**
- [ ] Lista de dependências documentada em `docs/`.
- [ ] Dependências instaladas e validadas em ambiente de teste.

## 3. [Banco] Instalar e configurar MariaDB

**Descrição:** Instalar o MariaDB e realizar configuração inicial de segurança (usuário, senha, acesso restrito).

**Critérios de aceite:**
- [ ] MariaDB instalado.
- [ ] `mysql_secure_installation` (ou equivalente) executado.
- [ ] Usuário de banco dedicado ao rAthena criado, sem usar root.

## 4. [Emulador] Clonar e compilar rAthena

**Descrição:** Clonar o rAthena em ambiente de desenvolvimento e compilar com sucesso, sem alterar o core.

**Critérios de aceite:**
- [ ] Repositório clonado em ambiente local/dev.
- [ ] Compilação concluída sem erros.
- [ ] login-server, char-server e map-server sobem localmente.

## 5. [Config] Definir episódio/referência mecânica

**Descrição:** Definir formalmente o episódio ou referência de mecânica old school/pré-renewal que servirá de base para configurações futuras.

**Critérios de aceite:**
- [ ] Episódio/referência documentado em `docs/03-configuracao-alvo.md`.
- [ ] Justificativa registrada.

## 6. [Config] Definir rates iniciais

**Descrição:** Definir rates iniciais de EXP, drop e demais parâmetros de economia para o modelo high rate.

**Critérios de aceite:**
- [ ] Rates definidos e documentados.
- [ ] Revisão para evitar desbalanceamento severo.

## 7. [Config] Definir level máximo 185

**Descrição:** Confirmar e documentar a configuração de level base máximo em 185, incluindo ajustes de EXP table necessários.

**Critérios de aceite:**
- [ ] Configuração documentada.
- [ ] Plano de ajuste de EXP table descrito.

## 8. [Config] Bloquear 3ª classes

**Descrição:** Garantir que classes de 3ª (terceira) não estejam disponíveis, mantendo o escopo old school do projeto.

**Critérios de aceite:**
- [ ] Job restrictions documentadas.
- [ ] Plano de validação (teste de troca de classe) descrito.

## 9. [Segurança] Configurar usuário não-root

**Descrição:** Criar usuário não-root dedicado para operação do servidor na VPS.

**Critérios de aceite:**
- [ ] Usuário criado com permissões mínimas necessárias.
- [ ] Acesso root direto via senha desabilitado.

## 10. [Segurança] Configurar firewall

**Descrição:** Configurar firewall (ex.: ufw) liberando apenas as portas necessárias para SSH e serviços do emulador.

**Critérios de aceite:**
- [ ] Regras de firewall documentadas.
- [ ] Firewall ativo e testado.

## 11. [Segurança] Configurar fail2ban

**Descrição:** Configurar fail2ban para proteger o acesso SSH contra tentativas de força bruta.

**Critérios de aceite:**
- [ ] fail2ban instalado e configurado.
- [ ] Teste de bloqueio validado.

## 12. [Backup] Definir rotina de backup

**Descrição:** Definir e documentar rotina de backup do banco de dados e arquivos de configuração, sem versionar backups reais no repositório.

**Critérios de aceite:**
- [ ] Rotina de backup documentada.
- [ ] Local de armazenamento dos backups definido (fora do repositório Git).

## 13. [Docs] Criar guia de instalação local

**Descrição:** Criar guia passo a passo para instalação do ambiente local de desenvolvimento (emulador + banco).

**Critérios de aceite:**
- [ ] Guia criado em `docs/`.
- [ ] Passos validados em pelo menos um ambiente de teste.

## 14. [Docs] Criar guia de operação da VPS

**Descrição:** Criar guia de operação da VPS cobrindo start/stop de serviços, monitoramento básico e procedimentos de manutenção.

**Critérios de aceite:**
- [ ] Guia criado em `docs/04-operacao-vps.md` (complementando o conteúdo existente, se aplicável).
- [ ] Procedimentos revisados.

## 15. [Governança] Definir regras do alpha fechado

**Descrição:** Definir regras claras para participação no alpha fechado (quem participa, expectativas, coleta de feedback e bugs).

**Critérios de aceite:**
- [ ] Regras documentadas em `docs/05-governanca.md` ou documento específico.
- [ ] Critérios de entrada e saída do alpha definidos.
