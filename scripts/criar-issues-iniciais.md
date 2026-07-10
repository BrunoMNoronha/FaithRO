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

## 7. [Config] Definir base level 255, atributos 185 e ASPD 197

> Registro histórico: o escopo original desta issue citava base level máximo
> 185. Essa decisão foi substituída em 2026-07-10 por base level máximo 255.
> Posteriormente, o atributo máximo inicialmente registrado como 187 foi
> corrigido para 185, e a ASPD máxima planejada foi definida em 197. O antigo
> base level máximo 185 é **histórico revogado**; o atributo/status natural
> máximo individual 185 é **decisão vigente** — nunca trate os dois como
> equivalentes. Job level máximo permanece pendente de definição por classe.
> Nenhum desses valores está implantado ou validado operacionalmente. A
> issue #8 no GitHub é a fonte canônica deste escopo e critérios; este
> template deve permanecer alinhado a ela.

**Descrição:** Configurar e validar base level máximo 255, atributo/status
natural máximo individual 185 e ASPD máxima 197 para o FaithRO em mecânica
Pre-Renewal, sem 3ª classes, cobrindo:

- curva completa de EXP até 255 e EXP por faixa de level;
- quantidade total de pontos de status e curva de concessão por level;
- custo dos atributos até 185 e clamp natural de STR/AGI/VIT/INT/DEX/LUK em
  185;
- atributos finais (com equipamentos, cartas, refinos e buffs);
- ASPD máxima 197, validada por classe e tipo de arma, incluindo bônus
  fixos e percentuais, poções, buffs, equipamentos, cartas e tentativas de
  ultrapassar o limite;
- distinção entre AGI, ASPD, delay de ataque e delays de skills (ASPD não
  elimina pós-conjuração nem substitui delay próprio de skill);
- job level máximo por classe permitida;
- limites de HP/SP por classe;
- cast, HIT, FLEE e resistência a status nas faixas altas de level;
- interface do cliente (exibição de level 255, atributos 185 e ASPD 197);
- resetador, job changer e comandos administrativos;
- impacto em PvM, MVP, PvP e WoE (ou adiamento formal de PvP/WoE);
- impacto de ASPD 197 na carga do map-server;
- plano de rollback;
- garantia de que nenhuma 3ª classe é liberada pela progressão.

Nenhum desses itens está implantado ou validado nesta tarefa.

**Critérios de aceite:**
- [ ] Base level máximo 255 documentado.
- [ ] Atributo/status natural máximo individual 185 documentado.
- [ ] ASPD máxima 197 documentada.
- [ ] Job level máximo definido para cada classe permitida.
- [ ] Arquivos reais de configuração identificados.
- [ ] Alterações priorizadas em `conf/import` e `db/import`.
- [ ] Curva completa de EXP até 255 definida.
- [ ] EXP por faixa de level revisada.
- [ ] Quantidade total de pontos de status definida.
- [ ] Curva de concessão de pontos de status definida.
- [ ] Custo dos atributos até 185 validado.
- [ ] Clamp natural de STR/AGI/VIT/INT/DEX/LUK em 185 validado.
- [ ] Atributos finais com equipamentos e buffs validados.
- [ ] Limites de HP/SP avaliados por classe.
- [ ] ASPD 197 validada por classe e tipo de arma.
- [ ] Bônus fixos e percentuais de ASPD testados.
- [ ] Poções, buffs, equipamentos e cartas de ASPD testados.
- [ ] Tentativas de ultrapassar ASPD 197 testadas.
- [ ] AGI e ASPD tratadas como grandezas distintas.
- [ ] ASPD e delays de skills tratados como grandezas distintas.
- [ ] Cast, HIT, FLEE e resistência a status avaliados.
- [ ] Interface do cliente validada para level 255, atributos 185 e ASPD 197.
- [ ] Resetador e job changer testados.
- [ ] Comandos administrativos testados.
- [ ] PvM e MVP testados.
- [ ] PvP e WoE testados ou formalmente adiados.
- [ ] Impacto de ASPD 197 no map-server avaliado.
- [ ] Plano de rollback documentado.
- [ ] Nenhuma 3ª classe liberada pela progressão.

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
