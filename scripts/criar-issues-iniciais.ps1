<#
    Script: criar-issues-iniciais.ps1
    Objetivo: Criar as 15 issues iniciais do backlog tecnico do FaithRO no GitHub,
    com base no conteudo de scripts/criar-issues-iniciais.md, usando o GitHub CLI (gh).

    Pre-requisitos:
      - GitHub CLI instalado (gh --version).
      - Autenticado no GitHub (gh auth login / gh auth status).
      - Permissao de escrita no repositorio BrunoMNoronha/FaithRO.

    Seguranca:
      - Este script NAO contem tokens, senhas ou dados sensiveis.
      - Por padrao roda em modo DRY RUN ($DryRun = $true): apenas IMPRIME
        os comandos "gh issue create" que seriam executados, sem criar nada.
      - Para executar de verdade, mude $DryRun para $false E confirme
        que revisou a lista de issues abaixo.

    As labels usadas (infra, banco, emulador, config, seguranca, backup, docs, governanca)
    podem NAO existir ainda no repositorio. O "gh issue create" falha se a label nao existir.
    Crie as labels antes (Settings > Labels no GitHub, ou "gh label create") ou remova o
    parametro --label das issues correspondentes.
#>

$Repo = "BrunoMNoronha/FaithRO"
$DryRun = $true

$Issues = @(
    @{ Title = "[Infra] Preparar VPS Ubuntu 22.04"; Label = "infra"; Body = @"
Preparar a VPS Ubuntu 22.04 (1 vCPU, 2 GB RAM, 50 GB) que servira de base para o servidor, incluindo atualizacao do sistema e pacotes essenciais.

Criterios de aceite:
- [ ] Sistema atualizado (apt update && apt upgrade).
- [ ] Pacotes basicos instalados (git, curl, build-essential, etc.).
- [ ] Acesso SSH validado.
"@ },
    @{ Title = "[Infra] Instalar dependências do rAthena"; Label = "infra"; Body = @"
Instalar as dependencias necessarias para compilar e rodar o rAthena na VPS ou ambiente local.

Criterios de aceite:
- [ ] Lista de dependencias documentada em docs/.
- [ ] Dependencias instaladas e validadas em ambiente de teste.
"@ },
    @{ Title = "[Banco] Instalar e configurar MariaDB"; Label = "banco"; Body = @"
Instalar o MariaDB e realizar configuracao inicial de seguranca (usuario, senha, acesso restrito).

Criterios de aceite:
- [ ] MariaDB instalado.
- [ ] mysql_secure_installation (ou equivalente) executado.
- [ ] Usuario de banco dedicado ao rAthena criado, sem usar root.
"@ },
    @{ Title = "[Emulador] Clonar e compilar rAthena"; Label = "emulador"; Body = @"
Clonar o rAthena em ambiente de desenvolvimento e compilar com sucesso, sem alterar o core.

Criterios de aceite:
- [ ] Repositorio clonado em ambiente local/dev.
- [ ] Compilacao concluida sem erros.
- [ ] login-server, char-server e map-server sobem localmente.
"@ },
    @{ Title = "[Config] Definir episódio/referência mecânica"; Label = "config"; Body = @"
Definir formalmente o episodio ou referencia de mecanica old school/pre-renewal que servira de base para configuracoes futuras.

Criterios de aceite:
- [ ] Episodio/referencia documentado em docs/03-configuracao-alvo.md.
- [ ] Justificativa registrada.
"@ },
    @{ Title = "[Config] Definir rates iniciais"; Label = "config"; Body = @"
Definir rates iniciais de EXP, drop e demais parametros de economia para o modelo high rate.

Criterios de aceite:
- [ ] Rates definidos e documentados.
- [ ] Revisao para evitar desbalanceamento severo.
"@ },
    @{ Title = "[Config] Definir level máximo 185"; Label = "config"; Body = @"
Confirmar e documentar a configuracao de level base maximo em 185, incluindo ajustes de EXP table necessarios.

Criterios de aceite:
- [ ] Configuracao documentada.
- [ ] Plano de ajuste de EXP table descrito.
"@ },
    @{ Title = "[Config] Bloquear 3ª classes"; Label = "config"; Body = @"
Garantir que classes de 3a (terceira) nao estejam disponiveis, mantendo o escopo old school do projeto.

Criterios de aceite:
- [ ] Job restrictions documentadas.
- [ ] Plano de validacao (teste de troca de classe) descrito.
"@ },
    @{ Title = "[Segurança] Configurar usuário não-root"; Label = "seguranca"; Body = @"
Criar usuario nao-root dedicado para operacao do servidor na VPS.

Criterios de aceite:
- [ ] Usuario criado com permissoes minimas necessarias.
- [ ] Acesso root direto via senha desabilitado.
"@ },
    @{ Title = "[Segurança] Configurar firewall"; Label = "seguranca"; Body = @"
Configurar firewall (ex.: ufw) liberando apenas as portas necessarias para SSH e servicos do emulador.

Criterios de aceite:
- [ ] Regras de firewall documentadas.
- [ ] Firewall ativo e testado.
"@ },
    @{ Title = "[Segurança] Configurar fail2ban"; Label = "seguranca"; Body = @"
Configurar fail2ban para proteger o acesso SSH contra tentativas de forca bruta.

Criterios de aceite:
- [ ] fail2ban instalado e configurado.
- [ ] Teste de bloqueio validado.
"@ },
    @{ Title = "[Backup] Definir rotina de backup"; Label = "backup"; Body = @"
Definir e documentar rotina de backup do banco de dados e arquivos de configuracao, sem versionar backups reais no repositorio.

Criterios de aceite:
- [ ] Rotina de backup documentada.
- [ ] Local de armazenamento dos backups definido (fora do repositorio Git).
"@ },
    @{ Title = "[Docs] Criar guia de instalação local"; Label = "docs"; Body = @"
Criar guia passo a passo para instalacao do ambiente local de desenvolvimento (emulador + banco).

Criterios de aceite:
- [ ] Guia criado em docs/.
- [ ] Passos validados em pelo menos um ambiente de teste.
"@ },
    @{ Title = "[Docs] Criar guia de operação da VPS"; Label = "docs"; Body = @"
Criar guia de operacao da VPS cobrindo start/stop de servicos, monitoramento basico e procedimentos de manutencao.

Criterios de aceite:
- [ ] Guia criado em docs/04-operacao-vps.md (complementando o conteudo existente, se aplicavel).
- [ ] Procedimentos revisados.
"@ },
    @{ Title = "[Governança] Definir regras do alpha fechado"; Label = "governanca"; Body = @"
Definir regras claras para participacao no alpha fechado (quem participa, expectativas, coleta de feedback e bugs).

Criterios de aceite:
- [ ] Regras documentadas em docs/05-governanca.md ou documento especifico.
- [ ] Criterios de entrada e saida do alpha definidos.
"@ }
)

Write-Host "Repositorio alvo: $Repo"
Write-Host "Modo DryRun: $DryRun"
Write-Host "Total de issues a processar: $($Issues.Count)"
Write-Host ""

foreach ($Issue in $Issues) {
    $BodyFile = New-TemporaryFile
    Set-Content -Path $BodyFile -Value $Issue.Body -Encoding utf8

    $CommandDescription = "gh issue create --repo `"$Repo`" --title `"$($Issue.Title)`" --label `"$($Issue.Label)`" --body-file `"$BodyFile`""

    if ($DryRun) {
        Write-Host "[DRY RUN] $CommandDescription"
    }
    else {
        Write-Host "Criando issue: $($Issue.Title)"
        gh issue create --repo $Repo --title $Issue.Title --label $Issue.Label --body-file $BodyFile
    }

    Remove-Item $BodyFile -Force -ErrorAction SilentlyContinue
}

Write-Host ""
if ($DryRun) {
    Write-Host "Nenhuma issue foi criada (DryRun = `$true). Revise a lista acima e, se estiver correta, altere `$DryRun para `$false para executar de verdade."
}
else {
    Write-Host "Processamento concluido. Verifique as issues criadas em https://github.com/$Repo/issues"
}
