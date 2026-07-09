# Preparação da VPS Ubuntu 22.04

> Documento de planejamento da issue #2 — [Infra] Preparar VPS Ubuntu 22.04.
> Esta etapa é **apenas documental**. Nenhum comando deve ser executado na VPS
> a partir deste documento. A execução real será feita em uma etapa posterior,
> após revisão e aprovação deste plano.

## Objetivo

Preparar a VPS base Ubuntu 22.04 para, no futuro, receber as dependências, o
banco de dados, o emulador e os serviços do FaithRO - Laos Deos.

Nesta etapa **não** se instala o rAthena e **não** se instala o MariaDB. O foco
é deixar o sistema operacional atualizado, com um usuário operacional não-root,
acesso SSH validado, firewall básico ativo e a estrutura de diretórios inicial
criada — tudo documentado e reversível.

## Premissas

- VPS Ubuntu 22.04.
- 1 vCPU.
- 2 GB RAM.
- 50 GB de disco.
- Acesso SSH administrativo disponível.
- Projeto sem fins lucrativos.
- Não usar `root` como usuário operacional permanente.
- Não expor senhas, tokens, chaves SSH, IPs sensíveis ou dados privados nesta
  documentação.

## Fora de escopo

Esta issue **não** cobre:

- Instalação do rAthena.
- Instalação/configuração do MariaDB.
- Configuração final de rates.
- Level máximo 185.
- Bloqueio de 3ª classes.
- Distribuição de cliente, GRF, executáveis ou assets proprietários.
- Deploy público do servidor.

## Plano de execução proposto

> Todos os comandos abaixo são **planejados para execução futura** na VPS, feita
> por um operador humano com acesso SSH. Eles não devem ser executados a partir
> desta máquina de desenvolvimento nem automatizados nesta etapa. Onde há
> `sudo`, assume-se um usuário administrativo já existente.

### 1. Atualização do sistema

```bash
sudo apt update
sudo apt upgrade -y
```

Objetivo: garantir que o sistema base esteja atualizado antes de qualquer
instalação futura.

### 2. Instalação de pacotes básicos

```bash
sudo apt install -y \
  git \
  curl \
  wget \
  unzip \
  tar \
  ca-certificates \
  build-essential \
  software-properties-common
```

Objetivo: disponibilizar utilitários de rede, descompactação e ferramentas de
build que serão exigidos pelas próximas issues (#3, #5). Não instala o emulador,
apenas o ferramental de base.

### 3. Configuração de timezone

```bash
timedatectl list-timezones | grep -i sao_paulo
sudo timedatectl set-timezone America/Sao_Paulo
timedatectl
```

Objetivo: alinhar o horário do servidor ao fuso de operação do projeto,
facilitando leitura de logs e agendamento de backups.

### 4. Criação de usuário operacional não-root

Exemplo de usuário: `faithro`.

```bash
sudo adduser faithro
```

Objetivo: separar a operação diária do usuário `root`. A senha definida aqui não
deve ser registrada nesta documentação.

### 5. Configuração básica de sudo para o usuário

```bash
sudo usermod -aG sudo faithro
```

Objetivo: permitir que o usuário operacional execute tarefas administrativas via
`sudo`, sem operar logado como `root`.

### 6. Endurecimento inicial de SSH

Ordem segura recomendada:

1. Copiar a chave pública para o novo usuário (a partir da estação local do
   operador):

   ```bash
   ssh-copy-id faithro@SEU_HOST
   ```

2. **Validar** o acesso por chave abrindo uma **nova** sessão SSH como `faithro`,
   sem fechar a sessão administrativa atual.
3. Somente após confirmar o acesso por chave, ajustar `/etc/ssh/sshd_config`
   para preferir autenticação por chave e reduzir o uso de senha:

   ```bash
   sudo nano /etc/ssh/sshd_config
   # Sugestões (revisar antes de aplicar):
   #   PasswordAuthentication no
   #   PubkeyAuthentication yes
   sudo systemctl restart ssh
   ```

> **Não** desabilite o login de `root` nem a autenticação por senha antes de
> confirmar que o acesso alternativo (usuário não-root por chave) funciona em uma
> sessão independente. Perder o acesso à VPS é o principal risco desta issue.

### 7. Firewall inicial com `ufw`

```bash
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status verbose
```

Objetivo: ativar o firewall liberando **apenas** o SSH nesta etapa. As portas do
servidor de jogo (login/char/map) **não** devem ser abertas agora — elas serão
tratadas nas issues de emulador, com justificativa e documentação próprias.

> Se o SSH usar porta customizada em vez da 22, libere a porta correta **antes**
> de habilitar o `ufw`, para não bloquear o próprio acesso. Ver
> [04-operacao-vps.md](04-operacao-vps.md) para o mapa de portas do projeto.

### 8. Estrutura inicial de diretórios

```bash
sudo mkdir -p /opt/faithro
sudo mkdir -p /opt/faithro/backups
sudo mkdir -p /opt/faithro/logs
```

Objetivo: criar a base de diretórios onde, futuramente, ficarão o emulador,
os backups e os logs operacionais.

### 9. Convenções de permissões

```bash
sudo chown -R faithro:faithro /opt/faithro
sudo chmod -R 750 /opt/faithro
```

Objetivo: dar ao usuário operacional a propriedade da árvore `/opt/faithro`,
evitando operar como `root` no dia a dia e restringindo o acesso de terceiros.
As permissões finais podem ser refinadas quando os serviços forem instalados.

### 10. Checklist de validação

- [ ] Sistema atualizado (`apt update && apt upgrade`).
- [ ] Pacotes básicos instalados.
- [ ] Timezone configurado.
- [ ] Usuário `faithro` criado.
- [ ] `sudo` funcional para `faithro`.
- [ ] Acesso SSH por chave validado em nova sessão.
- [ ] Firewall ativo liberando apenas SSH.
- [ ] Diretórios `/opt/faithro`, `/opt/faithro/backups`, `/opt/faithro/logs`
      criados.
- [ ] Permissões aplicadas.

## Testes / validações

Comandos de validação planejados (também para execução futura na VPS):

```bash
lsb_release -a          # confirma Ubuntu 22.04
uname -a                # confirma kernel/arquitetura
free -h                 # confirma memória disponível
df -h                   # confirma espaço em disco
whoami                  # confirma usuário atual
groups                  # confirma grupos (deve incluir sudo)
sudo -l                 # confirma permissões de sudo
timedatectl             # confirma timezone
ufw status verbose      # confirma firewall e regras
```

Além disso:

- Abrir uma **nova** sessão SSH com o usuário `faithro` e confirmar login por
  chave, mantendo a sessão administrativa original aberta.
- Verificar que `/opt/faithro` e subdiretórios existem e pertencem a `faithro`.

## Riscos

- **Bloqueio acidental de SSH pelo firewall**: habilitar o `ufw` sem liberar a
  porta correta de SSH pode derrubar o acesso.
- **Perda de acesso ao desativar `root`/senha cedo demais**: endurecer o SSH
  antes de validar o acesso alternativo pode trancar a VPS.
- **Pacotes incompletos para etapas futuras**: faltar dependência de build pode
  travar as issues #3 e #5.
- **VPS pequena para carga real**: 1 vCPU e 2 GB de RAM atendem
  desenvolvimento/alpha fechado, mas exigem monitoramento sob carga.
- **Misturar infra com emulador**: instalar rAthena/MariaDB nesta etapa quebra o
  planejamento e dificulta o rollback.

## Rollback

Estratégia de rollback segura:

- **Não fechar a sessão SSH original** até validar uma nova sessão com o usuário
  não-root.
- Se o firewall bloquear o acesso, reverter as regras do `ufw` (ou desabilitá-lo
  temporariamente) a partir do console da HostGator, se disponível:

  ```bash
  sudo ufw disable
  ```

- Remover o usuário criado **apenas** se outro acesso administrativo estiver
  garantido:

  ```bash
  sudo deluser --remove-home faithro
  ```

- Registrar todos os comandos efetivamente executados, para auditoria e reversão.
- Se a HostGator oferecer snapshot/backup da VPS, criar um **antes** de mudanças
  relevantes, para permitir restauração completa.

## Critérios de aceite da issue #2

- [ ] VPS atualizada.
- [ ] Usuário não-root criado e validado.
- [ ] SSH validado com usuário não-root.
- [ ] Firewall ativo sem bloquear o acesso SSH.
- [ ] Diretórios base criados.
- [ ] Comandos e evidências documentados.
- [ ] Nenhum rAthena instalado nesta issue.
- [ ] Nenhum MariaDB instalado nesta issue.

## Relação com issues futuras

Este preparo é pré-requisito ou está relacionado a:

- #3 — Instalar dependências do rAthena.
- #4 — Instalar e configurar MariaDB.
- #5 — Clonar e compilar rAthena.
- #10 — Configurar usuário não-root.
- #11 — Configurar firewall.
- #13 — Definir rotina de backup.

## Próximo passo

Revisar este documento via PR. Após aprovação, executar a issue #2 na VPS
seguindo este plano, com atenção especial para **não bloquear o acesso SSH** e
para validar cada etapa antes de avançar.

Refs: #2
