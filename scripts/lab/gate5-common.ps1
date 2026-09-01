# gate5-common.ps1 - Funcoes compartilhadas da automacao do laboratorio GATE 5.
# Dot-source este arquivo. Nao executa nada sozinho. Fail-closed por padrao.
#
# Regras invioladas por esta automacao (ETAPA 2P-E-C5-LAB-AUTOPROVISION):
#   target_materialized=false / artifact_executed=false / vps_accessed=false
#   Nenhum contato com o alvo WARP, com a VPS ou com servicos de reputacao externa.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# TLS 1.2+ explicito: o PowerShell 5.1 ainda negocia SSL3/TLS1.0 por padrao e
# as fontes oficiais aprovadas (api.github.com / objects.githubusercontent.com)
# recusam handshakes abaixo de TLS 1.2. Sem isto a fase Yara falha na conexao.
try {
    [Net.ServicePointManager]::SecurityProtocol =
        [Net.SecurityProtocolType]::Tls12 -bor [Net.ServicePointManager]::SecurityProtocol
} catch {}

# --- Caminhos canonicos -------------------------------------------------------
# Raiz do repo derivada do caminho do script (scripts\lab -> raiz), sem git:
# o provisionamento elevado pode rodar sob outra conta administradora, na qual
# git falharia por "dubious ownership" no repo de outro usuario.
$script:Gate5RepoRoot   = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path (Join-Path $script:Gate5RepoRoot 'scripts\lab\gate5-common.ps1'))) {
    throw 'GATE5: raiz do repositorio nao derivada corretamente de scripts/lab.'
}
$script:Gate5LocalDir   = Join-Path $script:Gate5RepoRoot '.local\gate5-lab'
$script:Gate5LogDir     = Join-Path $script:Gate5LocalDir 'logs'
$script:Gate5SecretDir  = Join-Path $script:Gate5LocalDir 'secrets'
$script:Gate5StateFile  = Join-Path $script:Gate5LocalDir 'state.json'
$script:Gate5EvidenceDir= Join-Path $script:Gate5LocalDir 'evidence'

# Namespace de evidencia por EXECUCAO. A instalacao limpa da RUN-01 reprovou
# tres criterios e por isso vale como prova de um baseline recusado, nao como
# lixo temporario: a RUN-02 precisa de um diretorio proprio para nao sobrescreve-la.
# A execucao corrente vem do estado (notes.run_id); o default acompanha a etapa.
$script:Gate5RunIdDefault = 'run-02-clean-install'

$script:Gate5VmName     = 'FaithRO-GATE5-LAB'
$script:Gate5VmDir      = 'C:\VMs\FaithRO-GATE5-LAB'
$script:Gate5VmxPath    = Join-Path $script:Gate5VmDir 'FaithRO-GATE5-LAB.vmx'
$script:Gate5SnapshotName = 'BASELINE_GATE5_ISOLATED'

# Portas de CD-ROM da VM, definidas em um unico lugar porque tres scripts as
# referenciam (criacao, anexo do unattend e isolamento final). O VMware numera
# os dispositivos SATA a partir da porta 0; usar portas 1/2 deixando a 0 vazia
# nao e a convencao que o proprio produto gera.
$script:Gate5CdOs       = 'sata0:0'   # ISO oficial do Windows
$script:Gate5CdUnattend = 'sata0:1'   # ISO auxiliar com o Autounattend.xml

# Console VNC do proprio VMware, usado APENAS como canal LOCAL e TEMPORARIO para
# entregar a tecla exigida pelo prompt "Press any key to boot from CD or DVD" da
# ISO oficial (o vmcli MKS aceita a tecla mas ela nao chega ao guest sem um
# console conectado). Fica preso a 127.0.0.1, e removido na fase de isolamento e
# a sua ausencia e conferida pelo validador antes do snapshot.
$script:Gate5VncPort = 5943

# Canal de SAIDA de mao unica do guest para o host: a porta serial da VM grava
# num arquivo do host. Substitui as guest operations do vmrun, indisponiveis em
# VM criptografada (docs/48 §12). Trafega apenas metadados de validacao.
#
# NAO existe mais um caminho FIXO de sink serial, e isto e deliberado. O VMware
# abre 'serial0.fileName' em modo destrutivo a cada power-on: enquanto um unico
# caminho serviu de sink para todos os power-ons, cada novo power-on zerava a
# evidencia do anterior - foi assim que a evidencia da RUN-02 se perdeu. Cada
# power-on passa a receber um sink PROPRIO, alocado por New-Gate5SerialSink em
# <run-dir>\serial\boot-NNNN.txt. Ver docs/48 §16.

$script:Gate5StagingDirs = @('C:\Users\bruno\Downloads', 'C:\Installers', 'C:\ISO', 'C:\VMs', 'C:\Tools')
$script:Gate5YaraDir    = 'C:\Tools\YARA'
$script:Gate5RulesDir   = 'C:\Tools\YARA-Rules'
$script:Gate5YaraVersion = '4.5.5'

# Runtime do Visual C++ exigido pelo YARA. Os binarios oficiais yara64.exe e
# yarac64.exe importam VCRUNTIME140.dll, que NAO existe num Windows 11 limpo (as
# api-ms-win-crt-* fazem parte do sistema, esta nao). Sem ela nenhum dos dois
# inicia - foi exatamente o que reprovou yara_4_5_5 e rules_compile_ok na
# primeira instalacao limpa.
# DECISAO ARQUITETURAL (docs/48 SS13): o runtime vem do REDISTRIBUIVEL OFICIAL da
# Microsoft, com Authenticode valido e SHA-256 pinado. Copiar VCRUNTIME140.dll ou
# MSVCP140.dll do proprio host ("app-local") e PROIBIDO: a proveniencia seria a
# instalacao local, nao um pacote assinado e versionado da Microsoft.
$script:Gate5VcRedistUrl = 'https://aka.ms/vs/17/release/vc_redist.x64.exe'
# Hosts aceitos como origem oficial. O aka.ms redireciona, entao o host EFETIVO
# do download tambem e verificado contra esta lista (fail-closed).
$script:Gate5MicrosoftHosts = @(
    'aka.ms', 'go.microsoft.com', 'download.microsoft.com',
    'download.visualstudio.microsoft.com', 'vsblob.vsassets.io'
)
# Menor versao do runtime v14 x64 aceita no guest. O YARA 4.5.5 oficial e
# compilado com o toolset do VS2022 (14.3x); versoes anteriores da mesma familia
# binaria exportam simbolos a menos e o processo ainda falharia ao iniciar.
$script:Gate5VcRuntimeMinVersion = [Version]'14.30'

# Ordem canonica das fases (checkpoints). A retomada percorre esta lista.
$script:Gate5Phases = @(
    'HOST_PREFLIGHT_OK',
    'VMWARE_INSTALLED',
    'ISO_VALIDATED',
    'VM_CREATED',
    'VCRUNTIME_READY',
    'GUEST_INSTALLED',
    'GUEST_UPDATED',
    'DEFENDER_READY',
    'YARA_READY',
    'RULESET_READY',
    'SANITIZED',
    'ISOLATED',
    'SNAPSHOT_CREATED',
    'BASELINE_VERIFIED'
)

# --- Log ----------------------------------------------------------------------
function Initialize-Gate5Log {
    foreach ($d in @($script:Gate5LocalDir, $script:Gate5LogDir, $script:Gate5SecretDir, $script:Gate5EvidenceDir)) {
        if (-not (Test-Path $d)) { New-Item -ItemType Directory -Force $d | Out-Null }
    }
    # Um unico log por execucao, compartilhado com os processos filhos via
    # GATE5_LOG_FILE: sem isto cada fase gerava um arquivo solto e a trilha de
    # auditoria ficava fragmentada entre pai e filhos.
    if ($env:GATE5_LOG_FILE) {
        $script:Gate5LogFile = $env:GATE5_LOG_FILE
    } else {
        $stamp = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')
        $script:Gate5LogFile = Join-Path $script:Gate5LogDir "provision-$stamp.log"
        $env:GATE5_LOG_FILE = $script:Gate5LogFile
    }
}

function Write-Gate5Log {
    param([Parameter(Mandatory)][string]$Message, [string]$Level = 'INFO')
    $line = '{0}Z [{1}] {2}' -f [DateTime]::UtcNow.ToString('s'), $Level, $Message
    Write-Host $line
    # Sob Set-StrictMode, ler uma variavel nunca atribuida LANCA. Qualquer helper
    # que registre log antes de Initialize-Gate5Log quebraria por isso, entao a
    # existencia e verificada em vez de assumida.
    $arquivo = Get-Variable -Name Gate5LogFile -Scope Script -ValueOnly -ErrorAction SilentlyContinue
    if ($arquivo) { Add-Content -Path $arquivo -Value $line -Encoding utf8 }
}

# --- Estado / checkpoints -----------------------------------------------------
function Get-Gate5State {
    $fresh = [pscustomobject]@{
        schema    = 'gate5-lab-autoprovision-state/v1'
        completed = @()
        notes     = [pscustomobject]@{}
    }
    if (Test-Path $script:Gate5StateFile) {
        $raw = Get-Content $script:Gate5StateFile -Raw -ErrorAction SilentlyContinue
        if ($raw -and $raw.Trim()) {
            try {
                $parsed = $raw | ConvertFrom-Json
                if ($parsed -and $parsed.PSObject.Properties['completed']) { return $parsed }
            } catch {}
        }
        # Arquivo de estado vazio/corrompido: recomecar e fase a fase redetectar
        # o que ja existe (fases sao idempotentes). Nunca prosseguir com nulo.
        Write-Gate5Log 'state.json vazio ou invalido; reiniciando checkpoints (fases idempotentes redetectam o existente).' 'WARN'
    }
    return $fresh
}

function Save-Gate5State {
    param([Parameter(Mandatory)]$State)
    $State | ConvertTo-Json -Depth 8 | Out-File -FilePath $script:Gate5StateFile -Encoding utf8
}

function Test-Gate5Phase {
    param([Parameter(Mandatory)]$State, [Parameter(Mandatory)][string]$Phase)
    return @($State.completed) -contains $Phase
}

function Complete-Gate5Phase {
    # RELE o estado do disco antes de gravar. O entrypoint carrega o estado uma
    # vez no inicio, mas as fases rodam em processos filhos que gravam suas
    # proprias notas (boot_key_sent, installation_stage). Salvar o objeto que o
    # pai tem em memoria sobrescrevia essas notas com valores velhos - na pratica
    # apagava a marca anti-loop do boot optico logo apos ela ser definida.
    param([Parameter(Mandatory)]$State, [Parameter(Mandatory)][string]$Phase)
    $atual = Get-Gate5State
    if (-not (Test-Gate5Phase -State $atual -Phase $Phase)) {
        $atual.completed = @($atual.completed) + $Phase
        Save-Gate5State -State $atual
        Write-Gate5Log "CHECKPOINT alcancado: $Phase"
    }
    # Mantem o objeto do chamador alinhado com o que ficou no disco.
    $State.completed = @($atual.completed)
    $State.notes     = $atual.notes
}

# --- Namespace de evidencia por execucao -------------------------------------
function Get-Gate5RunId {
    # Identificador da execucao corrente. Fica no estado para que todas as fases
    # filhas (processos separados) escrevam no MESMO diretorio.
    $s = Get-Gate5State
    if ($s.notes -and $s.notes.PSObject.Properties['run_id']) {
        $v = [string]$s.notes.run_id
        if ($v) { return $v }
    }
    return $script:Gate5RunIdDefault
}

function Test-Gate5RunSealed {
    # Uma execucao SELADA e evidencia fechada: a RUN-01 reprovou tres criterios e
    # justamente por isso e prova, nao rascunho. Escrever nela e proibido.
    param([Parameter(Mandatory)][string]$RunId)
    return (Test-Path (Join-Path (Join-Path $script:Gate5EvidenceDir $RunId) 'sealed.json'))
}

function Get-Gate5RunDir {
    # Diretorio de evidencia da execucao corrente, criado sob demanda. Falha
    # fechado se a execucao ja tiver sido selada - sobrescrever a prova de uma
    # execucao anterior seria destruir evidencia, nao reaproveitar espaco.
    param([string]$RunId)
    if (-not $RunId) { $RunId = Get-Gate5RunId }
    if (Test-Gate5RunSealed -RunId $RunId) {
        Stop-Gate5Blocked -Blocker 'RUN_EVIDENCE_SEALED' -Detail "a execucao '$RunId' ja esta selada; defina notes.run_id para uma nova execucao antes de gravar evidencia."
    }
    $dir = Join-Path $script:Gate5EvidenceDir $RunId
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force $dir | Out-Null }
    return $dir
}

# --- Saidas padronizadas (fail-closed) ---------------------------------------
function Stop-Gate5Blocked {
    param([Parameter(Mandatory)][string]$Blocker, [string]$Detail = '')
    Write-Gate5Log "LAB_AUTOPROVISION_BLOCKED blocker=$Blocker $Detail" 'BLOCK'
    Write-Host ''
    Write-Host 'LAB_AUTOPROVISION_BLOCKED'
    Write-Host "blocker=$Blocker"
    if ($Detail) { Write-Host $Detail }
    exit 2
}

function Stop-Gate5Human {
    # Gate humano FORMAL: uma acao que so pode ser feita na interface do VMware
    # porque a VM e criptografada e a senha pertence ao operador. Nao e falha de
    # automacao - e parte auditavel do procedimento, sempre seguida de validacao
    # tecnica automatica na proxima execucao.
    param([Parameter(Mandatory)][string]$Action, [string]$Detail = '')
    Write-Gate5Log "HUMAN_ACTION_REQUIRED $Action" 'GATE'
    Write-Host ''
    Write-Host 'HUMAN_ACTION_REQUIRED'
    Write-Host "action=$Action"
    if ($Detail) { Write-Host $Detail }
    exit 4
}

function Test-Gate5VmPoweredOn {
    # Sem vmrun (VM criptografada): a presenca de um processo vmware-vmx com o
    # .vmx travado e a prova de que ESTA VM esta ligada.
    $lockDirs = @(Get-ChildItem -LiteralPath $script:Gate5VmDir -Force -Directory -ErrorAction SilentlyContinue |
                  Where-Object { $_.Name -like '*.vmdk.lck' -or $_.Name -like '*.vmem.lck' })
    $proc = @(Get-Process -Name 'vmware-vmx' -ErrorAction SilentlyContinue)
    return (($proc.Count -gt 0) -and ($lockDirs.Count -gt 0))
}

function Get-Gate5SerialSinkDir {
    # Diretorio dos sinks seriais da execucao corrente: <run-dir>\serial.
    #
    # Fica DENTRO do diretorio da RUN de proposito: Get-Gate5RunDir falha fechado
    # numa execucao ja selada (RUN_EVIDENCE_SEALED), e com isso nenhum sink novo
    # pode ser alocado dentro de evidencia fechada.
    param([string]$RunId)
    $dir = Join-Path (Get-Gate5RunDir -RunId $RunId) 'serial'
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force $dir | Out-Null }
    return $dir
}

function Get-Gate5SerialSinks {
    # Sinks seriais ja alocados na execucao, do mais ANTIGO para o mais recente.
    # A ordem vem do numero no nome (boot-0001, boot-0002, ...), nao do carimbo
    # de tempo do arquivo: o VMware reescreve o mtime a cada power-on.
    param([string]$RunId)
    if (-not $RunId) { $RunId = Get-Gate5RunId }
    $dir = Join-Path (Join-Path $script:Gate5EvidenceDir $RunId) 'serial'
    if (-not (Test-Path -LiteralPath $dir)) { return @() }
    return @(Get-ChildItem -LiteralPath $dir -File -Filter 'boot-*.txt' -ErrorAction SilentlyContinue |
             Where-Object { $_.Name -match '^boot-(\d{4})\.txt$' } |
             Sort-Object { [int]([regex]::Match($_.Name, '^boot-(\d{4})\.txt$').Groups[1].Value) } |
             ForEach-Object { $_.FullName })
}

function New-Gate5SerialSink {
    # Aloca um sink serial NOVO para o proximo power-on e aponta a porta serial
    # da VM para ele.
    #
    # RAIZ DO INCIDENTE: o VMware abre o arquivo de 'serial0.fileName' em modo
    # destrutivo a CADA power-on (processo vmware-vmx novo) - nao a cada reboot
    # do guest. Provado no vmware-1.log da RUN-02: 19 boots EFI sob o mesmo PID
    # 4184, com a serial ACUMULANDO 3232 bytes. Enquanto o mesmo caminho serviu
    # de sink para todos os power-ons, cada novo power-on zerou a evidencia do
    # anterior - foi assim que a evidencia da RUN-02 (blockers:[]) se perdeu.
    #
    # INVARIANTE: um sink ja usado num power-on NUNCA volta a ser sink de outro.
    # O numero de sequencia e derivado do PROPRIO diretorio, e nao do state.json:
    # se o orquestrador morrer e for reiniciado, o filesystem continua sabendo
    # quais sinks existem, e a alocacao segue do maior numero presente. Um
    # arquivo existente jamais e reaproveitado nem truncado por esta funcao.
    param([string]$RunId, $Vmware)

    # As mesmas guardas da ordem de boot: a configuracao so e lida no power-on, e
    # com a interface aberta a escrita PASSA no arquivo e e descartada no Power On
    # a partir da copia em cache - a VM bootaria com o sink ANTIGO e o truncaria.
    if (Test-Gate5VmPoweredOn) {
        throw 'GATE5: o sink serial so pode ser trocado com a VM desligada.'
    }
    if (Test-Gate5VmwareUiRunning) {
        throw 'GATE5: a interface do VMware esta aberta e descartaria a troca do sink serial no Power On.'
    }

    $dir = Get-Gate5SerialSinkDir -RunId $RunId
    $usados = @(Get-Gate5SerialSinks -RunId $RunId)
    $n = 0
    foreach ($u in $usados) {
        $m = [regex]::Match((Split-Path -Leaf $u), '^boot-(\d{4})\.txt$')
        if ($m.Success) { $v = [int]$m.Groups[1].Value; if ($v -gt $n) { $n = $v } }
    }
    # O arquivo e criado VAZIO aqui, na alocacao, em vez de ser deixado para o
    # VMware criar no power-on. E isso que torna a sequencia DURAVEL: o proximo
    # sink e deduzido do diretorio, e nao do state.json, entao um orquestrador
    # que morra e volte nao reaponta para um sink ja usado. Truncar um arquivo
    # recem-criado e vazio nao custa nada; truncar o do boot anterior custou a
    # evidencia da RUN-02.
    #
    # 'CreateNew' e ATOMICO: se o nome ja existir a criacao falha e a sequencia
    # avanca, em vez de sobrescrever evidencia. Nenhum arquivo existente e
    # aberto para escrita por esta funcao.
    $sink = $null
    while ($null -eq $sink) {
        $n++
        if ($n -gt 9999) { throw 'GATE5: sequencia de sinks seriais esgotada (boot-9999).' }
        $candidato = Join-Path $dir ('boot-{0:D4}.txt' -f $n)
        try {
            $fs = [System.IO.File]::Open($candidato, 'CreateNew', 'Write', 'None')
            $fs.Dispose()
            $sink = $candidato
        } catch [System.IO.IOException] {
            # nome ja ocupado: seguir para o proximo da sequencia
        }
    }

    Set-Gate5VmxEntry -Name 'serial0.present'        -Value 'TRUE'  -Vmware $Vmware
    Set-Gate5VmxEntry -Name 'serial0.fileType'       -Value 'file'  -Vmware $Vmware
    Set-Gate5VmxEntry -Name 'serial0.fileName'       -Value $sink   -Vmware $Vmware
    Set-Gate5VmxEntry -Name 'serial0.startConnected' -Value 'TRUE'  -Vmware $Vmware
    Set-Gate5VmxEntry -Name 'serial0.yieldOnMsrRead' -Value 'TRUE'  -Vmware $Vmware
    $lido = Get-Gate5VmxValue -Key 'serial0.fileName'
    if ($lido -ne $sink) {
        throw ("GATE5: serial0.fileName nao persistiu no .vmx (lido '{0}', esperado '{1}')." -f $lido, $sink)
    }

    # Vinculo boot -> arquivo, auditavel fora do nome do arquivo.
    try {
        $st = Get-Gate5State
        $hist = @()
        if ($st.notes.PSObject.Properties['serial_sinks']) { $hist = @($st.notes.serial_sinks) }
        $hist += [pscustomobject]@{ sink = (Split-Path -Leaf $sink); alocado_utc = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ') }
        $st.notes | Add-Member -NotePropertyName 'serial_sinks' -NotePropertyValue $hist -Force
        Save-Gate5State $st
    } catch { Write-Gate5Log "historico de sinks seriais nao registrado no estado: $($_.Exception.Message)" 'WARN' }

    Write-Gate5Log ("Sink serial deste power-on: {0} (os anteriores permanecem intactos)." -f $sink)
    return $sink
}

function Get-Gate5ActiveSerialSink {
    # Sink para onde a porta serial da VM aponta AGORA, segundo o .vmx.
    return (Get-Gate5VmxValue -Key 'serial0.fileName')
}

function Read-Gate5SerialText {
    # Le um sink serial com compartilhamento total: o vmware-vmx mantem o arquivo
    # aberto para escrita enquanto a VM esta ligada.
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try {
        $fs = [System.IO.File]::Open($Path, 'Open', 'Read', 'ReadWrite')
        try { return (New-Object System.IO.StreamReader($fs)).ReadToEnd() } finally { $fs.Close() }
    } catch { return $null }
}

function Get-Gate5SerialReadOrder {
    # Sinks a consultar, do mais RECENTE para o mais antigo.
    #
    # Varrer todos, e nao apenas o sink ativo, e o que torna a leitura robusta a
    # um reinicio do orquestrador: a evidencia pode ter chegado num power-on
    # anterior. Antes, ela so era encontrada enquanto o caminho fixo ainda a
    # contivesse - que e exatamente o que o truncamento destruia.
    param([string]$RunId)
    $sinks = @(Get-Gate5SerialSinks -RunId $RunId)
    [array]::Reverse($sinks)
    return @($sinks)
}

function Get-Gate5SerialEvidence {
    # Le a evidencia que o guest escreveu na porta serial. Retorna $null enquanto
    # o bloco completo (com marcadores de inicio e fim) nao tiver chegado.
    # Sem -Path, procura em todos os sinks da execucao (mais recente primeiro).
    param([string]$Path, [string]$RunId)
    $alvos = @()
    if ($Path) { $alvos = @($Path) } else { $alvos = @(Get-Gate5SerialReadOrder -RunId $RunId) }
    foreach ($alvo in $alvos) {
        $texto = Read-Gate5SerialText -Path $alvo
        if ($null -eq $texto) { continue }
        $m = [regex]::Match($texto, '<<<GATE5-EVIDENCE-BEGIN>>>(?<j>.*?)<<<GATE5-EVIDENCE-END>>>', 'Singleline')
        if (-not $m.Success) { continue }
        try { return ($m.Groups['j'].Value -replace '[\r\n]', '') | ConvertFrom-Json } catch { continue }
    }
    return $null
}

function Get-Gate5SerialStages {
    # Batimentos de progresso do payload. Servem para saber SE o guest esta
    # trabalhando; nao substituem a evidencia, que continua exigindo o bloco
    # completo START->END em Get-Gate5SerialEvidence (fail-closed inalterado).
    # Sem -Path, agrega os batimentos de TODOS os sinks da execucao, do mais
    # antigo para o mais recente: a instalacao atravessa varios power-ons.
    param([string]$Path, [string]$RunId)
    $alvos = @()
    if ($Path) { $alvos = @($Path) } else { $alvos = @(Get-Gate5SerialSinks -RunId $RunId) }
    $texto = ''
    foreach ($alvo in $alvos) {
        $t = Read-Gate5SerialText -Path $alvo
        if ($t) { $texto = $texto + $t + [Environment]::NewLine }
    }
    if (-not $texto) { return @() }
    $saida = @()
    foreach ($m in [regex]::Matches($texto, '<<<GATE5-STAGE:(?<n>[^|>]+)\|(?<t>[^|>]+)(\|(?<d>[^>]*))?>>>')) {
        $saida += [pscustomobject]@{
            Stage     = $m.Groups['n'].Value
            Timestamp = $m.Groups['t'].Value
            Detail    = $m.Groups['d'].Value
        }
    }
    return $saida
}

function Stop-Gate5Paused {
    param([Parameter(Mandatory)][string]$Reason, [string]$Detail = '')
    Write-Gate5Log "LAB_AUTOPROVISION_PAUSED reason=$Reason $Detail" 'PAUSE'
    Write-Host ''
    Write-Host 'LAB_AUTOPROVISION_PAUSED'
    Write-Host "reason=$Reason"
    Write-Host 'resume_supported=true'
    if ($Detail) { Write-Host $Detail }
    exit 3
}

# --- Utilidades ---------------------------------------------------------------
function Get-Gate5Sha256 {
    param([Parameter(Mandatory)][string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Set-Gate5TextFile {
    # Grava texto em UTF-8 SEM BOM com quebras CRLF. Necessario para arquivos
    # .vmx: Set-Content -Encoding utf8 no PowerShell 5.1 prefixa um BOM, que o
    # VMware pode rejeitar ao interpretar a primeira chave de configuracao.
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)][string[]]$Lines)
    $text = ($Lines -join "`r`n") + "`r`n"
    [System.IO.File]::WriteAllText($Path, $text, (New-Object System.Text.UTF8Encoding($false)))
}

function Invoke-Gate5Native {
    # Executa um programa nativo capturando stdout+stderr sem que o
    # NativeCommandError do PowerShell 5.1 dispare por causa de
    # $ErrorActionPreference='Stop' (stderr redirecionado vira ErrorRecord).
    param([Parameter(Mandatory)][string]$FilePath, [string[]]$Arguments = @())
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = & $FilePath @Arguments 2>&1 | ForEach-Object { [string]$_ }
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    return [pscustomobject]@{ ExitCode = [int]$code; Output = @($out) }
}

function Test-Gate5MicrosoftSource {
    # Origem OFICIAL Microsoft: esquema HTTPS e host na allowlist. Usada tanto na
    # URL declarada quanto na URL EFETIVA obtida apos os redirecionamentos, para
    # que um redirect sequestrado nao entregue um binario de terceiro.
    param([Parameter(Mandatory)][string]$Uri)
    try { $u = [Uri]$Uri } catch { return $false }
    if ($u.Scheme -ne 'https') { return $false }
    $nome = $u.Host.ToLowerInvariant()
    return [bool](@($script:Gate5MicrosoftHosts) -contains $nome)
}

function Get-Gate5AuthenticodeMicrosoft {
    # Assinatura Authenticode VALIDA e emitida para a Microsoft Corporation.
    # Retorna o veredito com os dados de auditoria (nunca material secreto).
    param([Parameter(Mandatory)][string]$Path)
    $sig = Get-AuthenticodeSignature -LiteralPath $Path
    $assunto = ''
    $digital = ''
    if ($sig.SignerCertificate) {
        $assunto = $sig.SignerCertificate.Subject
        $digital = $sig.SignerCertificate.Thumbprint
    }
    $microsoft = ($assunto -match '(?i)O=Microsoft Corporation') -or ($assunto -match '(?i)CN=Microsoft Corporation')
    return [pscustomobject]@{
        Status     = $sig.Status.ToString()
        Subject    = $assunto
        Thumbprint = $digital
        Valid      = (($sig.Status -eq 'Valid') -and $microsoft)
    }
}

function Test-Gate5Elevated {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    return ([Security.Principal.WindowsPrincipal]$id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-Gate5PathWritable {
    # Escrita real de um arquivo-sonda (ACL efetiva, nao apenas herdada).
    # Se o diretorio ainda nao existe, testa o pai - e nele que ele sera criado.
    param([Parameter(Mandatory)][string]$Path)
    $target = $Path
    if (-not (Test-Path -LiteralPath $target)) { $target = Split-Path -Parent $target }
    if (-not (Test-Path -LiteralPath $target)) { return $false }
    $probe = Join-Path $target ('.gate5-write-probe-' + [Guid]::NewGuid().ToString('N'))
    try {
        Set-Content -LiteralPath $probe -Value 'probe' -ErrorAction Stop
        Remove-Item -LiteralPath $probe -Force -ErrorAction SilentlyContinue
        return $true
    } catch { return $false }
}

function Find-Gate5VmwareInstall {
    # Retorna caminhos reais dos executaveis VMware ou $null se nao instalado.
    $candidates = @(
        'C:\Program Files (x86)\VMware\VMware Workstation',
        'C:\Program Files\VMware\VMware Workstation'
    )
    $reg = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
                            'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue |
           Where-Object { $_.PSObject.Properties['DisplayName'] -and $_.DisplayName -match 'VMware Workstation' } | Select-Object -First 1
    if ($reg -and $reg.PSObject.Properties['InstallLocation'] -and $reg.InstallLocation) { $candidates = @($reg.InstallLocation) + $candidates }
    foreach ($dir in $candidates) {
        $vmware = Join-Path $dir 'vmware.exe'
        if (Test-Path $vmware) {
            return [pscustomobject]@{
                InstallDir       = $dir
                VmwareExe        = $vmware
                VmrunExe         = Join-Path $dir 'vmrun.exe'
                VdiskManagerExe  = Join-Path $dir 'vmware-vdiskmanager.exe'
                DisplayVersion   = if ($reg) { $reg.DisplayVersion } else { (Get-Item $vmware).VersionInfo.ProductVersion }
            }
        }
    }
    return $null
}

function Find-Gate5File {
    # Busca fail-closed em diretorios de staging por um padrao de nome de arquivo.
    param([Parameter(Mandatory)][string]$Pattern, [int]$Depth = 2)
    $found = @()
    foreach ($dir in $script:Gate5StagingDirs) {
        if (Test-Path $dir) {
            $found += Get-ChildItem $dir -Recurse -Depth $Depth -File -Filter $Pattern -ErrorAction SilentlyContinue
        }
    }
    return $found | Sort-Object LastWriteTime -Descending
}

function Get-Gate5IsoSidecar {
    # Caminho do sidecar com o SHA-256 oficial da Microsoft ao lado da ISO,
    # ou $null se ausente. Aceita '<iso>.sha256.official' e a variante '.txt'
    # (o Bloco de Notas do Windows acrescenta .txt ao salvar).
    param([Parameter(Mandatory)][string]$IsoPath)
    foreach ($cand in @("$IsoPath.sha256.official", "$IsoPath.sha256.official.txt")) {
        if (Test-Path -LiteralPath $cand) { return $cand }
    }
    return $null
}

function Assert-Gate5AuthenticodeValid {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$PublisherPattern
    )
    $sig = Get-AuthenticodeSignature -LiteralPath $Path
    if ($sig.Status -ne 'Valid') {
        Stop-Gate5Blocked -Blocker 'UNSIGNED_OR_INVALID_SIGNATURE' -Detail "arquivo=$Path status=$($sig.Status)"
    }
    if ($sig.SignerCertificate.Subject -notmatch $PublisherPattern) {
        Stop-Gate5Blocked -Blocker 'UNEXPECTED_PUBLISHER' -Detail "arquivo=$Path subject=$($sig.SignerCertificate.Subject)"
    }
    return $sig
}

function Invoke-Gate5Vmrun {
    # Wrapper fail-closed do vmrun. Nunca imprime credenciais.
    param(
        [Parameter(Mandatory)]$Vmware,
        [Parameter(Mandatory)][string[]]$Arguments,
        [switch]$AllowFailure
    )
    # DECISAO ARQUITETURAL (2026-08-29): em VM criptografada, 'vmrun' exige a
    # senha da criptografia ("A password is required for this operation") e a
    # unica forma de fornece-la seria '-vp <senha>' na linha de comando, o que
    # exporia a credencial na lista de processos da maquina. A senha e exclusiva
    # do operador: a automacao nao a le, nao a pede e nao a transporta. Por isso
    # as operacoes de energia/snapshot de uma VM criptografada sao GATES HUMANOS
    # na interface do VMware, e o vmrun falha fechado aqui em vez de tentar.
    if ((Get-Gate5VmEncryptionState).Encrypted) {
        $op = @($Arguments | Where-Object { $_ -notmatch '^-' })[0]
        Stop-Gate5Blocked -Blocker 'ENCRYPTED_VM_REQUIRES_HUMAN_POWER_OP' -Detail @"
A VM esta criptografada (exigencia do vTPM) e o vmrun so operaria nela com a
senha da criptografia, que pertence exclusivamente ao operador e nunca e
manipulada por esta automacao. Operacao recusada: '$op'.
Execute essa operacao pela interface do VMware Workstation; a automacao valida
o resultado tecnicamente em seguida.
"@
    }

    # Redacao: '-gu'/'-gp' sao seguidos do usuario/senha do guest; suprimimos o
    # proprio valor, nao apenas a flag, para que nada vaze no log.
    $printable = @()
    for ($i = 0; $i -lt $Arguments.Count; $i++) {
        if ($Arguments[$i] -match '^-g[up]$') { $printable += $Arguments[$i]; $printable += '<redacted>'; $i++ }
        else { $printable += $Arguments[$i] }
    }
    Write-Gate5Log ("vmrun " + ($printable -join ' '))
    $r = Invoke-Gate5Native -FilePath $Vmware.VmrunExe -Arguments (@('-T', 'ws') + $Arguments)
    if ($r.ExitCode -ne 0 -and -not $AllowFailure) {
        Write-Gate5Log ("vmrun exit={0} saida={1}" -f $r.ExitCode, ($r.Output -join ' | ')) 'ERROR'
        throw ("GATE5: vmrun falhou (exit {0}): {1}" -f $r.ExitCode, ($r.Output -join ' | '))
    }
    return $r
}

function Get-Gate5VmEncryptionState {
    # Estado criptografico da VM a partir do .vmx, SEM NUNCA devolver valores:
    # 'encryption.*' e 'vtpm.*' carregam material de chave e identidade do TPM.
    # Retorna apenas booleanos e os NOMES das propriedades encontradas, para que
    # a evidencia possa ser registrada sem vazar segredo.
    param([string]$VmxPath = $script:Gate5VmxPath)
    $state = [pscustomobject]@{
        Encrypted             = $false
        VtpmPresent           = $false
        MaterialPropertyNames = @()
        Firmware              = $null
        SecureBoot            = $false
    }
    if (-not (Test-Path -LiteralPath $VmxPath)) { return $state }
    $names = @()
    foreach ($line in Get-Content -LiteralPath $VmxPath) {
        if ($line -match '^\s*([A-Za-z0-9_.:]+)\s*=') {
            $key = $Matches[1]
            if ($key -match '^(encryption\.|vtpm\.)') { $names += $key }
        }
    }
    $state.MaterialPropertyNames = @($names | Sort-Object -Unique)
    $state.Encrypted   = [bool](@($names | Where-Object { $_ -like 'encryption.*' }).Count)
    $state.VtpmPresent = [bool](@($names | Where-Object { $_ -like 'vtpm.*' }).Count)
    # Ler do MESMO arquivo inspecionado acima: usar o caminho global aqui faria
    # o helper reportar firmware/Secure Boot de outra VM que nao a consultada.
    $state.Firmware    = Get-Gate5VmxValue -Key 'firmware' -VmxPath $VmxPath
    $state.SecureBoot  = ((Get-Gate5VmxValue -Key 'uefi.secureBoot.enabled' -VmxPath $VmxPath) -eq 'TRUE')
    return $state
}

function Set-Gate5VmxEntry {
    # Grava UMA chave no .vmx preservando tudo o mais.
    #
    # Depois que o operador adiciona o vTPM, o VMware guarda no .vmx as chaves
    # 'encryption.*' e o material 'vtpm.*'. No modo de criptografia parcial que o
    # TPM exige, o .vmx permanece em TEXTO PLANO e esse material aparece como
    # valores opacos: e seguro trocar OUTRAS chaves desde que essas linhas saiam
    # intactas, e e isso que esta funcao garante e verifica.
    #
    # 'vmcli ConfigParams SetEntry' NAO serve aqui: em VM criptografada ele exige
    # a senha da criptografia pela entrada padrao ("Something went wrong while
    # getting password from stdin"), e essa senha e exclusiva do operador - a
    # automacao nunca a conhece, pede ou registra.
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Value,
        $Vmware
    )
    if (-not (Test-Path $script:Gate5VmxPath)) { throw 'GATE5: VMX inexistente ao gravar configuracao.' }

    # Idempotencia: se a chave ja tem o valor desejado, nao reescrever o arquivo.
    # Alem de evitar trabalho inutil, isso impede tocar no .vmx de uma VM aberta
    # na interface do VMware (que mantem a configuracao em cache) quando nao ha
    # nada a mudar - o arquivo so e reescrito quando realmente muda algo.
    if ((Get-Gate5VmxValue -Key $Name) -eq $Value) { return }

    $encoding = New-Object System.Text.UTF8Encoding($false)
    $before   = @([System.IO.File]::ReadAllLines($script:Gate5VmxPath))
    $sensivel = '^\s*(encryption\.|vtpm\.)'
    $antes    = @($before | Where-Object { $_ -match $sensivel })

    # Substituicao NO LUGAR: a linha alvo troca de valor e todas as demais saem
    # verbatim, na mesma ordem. Nada de reconstruir o arquivo a partir de um
    # template - o material criptografico e copiado como esta, sem ser lido.
    $pattern  = '^\s*{0}\s*=' -f [regex]::Escape($Name)
    $nova     = '{0} = "{1}"' -f $Name, $Value
    $saida    = New-Object System.Collections.Generic.List[string]
    $trocou   = $false
    foreach ($linha in $before) {
        if ($linha -match $pattern) {
            if (-not $trocou) { $saida.Add($nova); $trocou = $true }   # duplicatas da chave sao descartadas
        } else {
            $saida.Add($linha)
        }
    }
    if (-not $trocou) { $saida.Add($nova) }
    [System.IO.File]::WriteAllText($script:Gate5VmxPath, (($saida -join "`r`n") + "`r`n"), $encoding)

    # Fail-closed: as linhas de material criptografico precisam sair IDENTICAS
    # (comparacao sensivel a maiusculas). Qualquer desvio reverte a escrita.
    $depois = @([System.IO.File]::ReadAllLines($script:Gate5VmxPath) | Where-Object { $_ -match $sensivel })
    $intacto = ($antes.Count -eq $depois.Count)
    if ($intacto) {
        for ($i = 0; $i -lt $antes.Count; $i++) {
            if ($antes[$i] -cne $depois[$i]) { $intacto = $false; break }
        }
    }
    if (-not $intacto) {
        [System.IO.File]::WriteAllText($script:Gate5VmxPath, (($before -join "`r`n") + "`r`n"), $encoding)
        throw ("GATE5: a escrita de '{0}' teria alterado material criptografico do .vmx; alteracao revertida." -f $Name)
    }
}

function Remove-Gate5VmxEntry {
    # Apaga UMA chave do .vmx preservando tudo o mais, com a mesma garantia
    # fail-closed de Set-Gate5VmxEntry: as linhas 'encryption.*'/'vtpm.*' saem
    # verbatim ou a escrita e revertida. Existe para retirar chaves de ordem de
    # boot que ja nao valem, em vez de deixar no arquivo um valor que o firmware
    # reprovou e que so polui o proximo power-on.
    param([Parameter(Mandatory)][string]$Name)
    if (-not (Test-Path $script:Gate5VmxPath)) { throw 'GATE5: VMX inexistente ao remover configuracao.' }
    if ($null -eq (Get-Gate5VmxValue -Key $Name)) { return }

    $encoding = New-Object System.Text.UTF8Encoding($false)
    $before   = @([System.IO.File]::ReadAllLines($script:Gate5VmxPath))
    $sensivel = '^\s*(encryption\.|vtpm\.)'
    $antes    = @($before | Where-Object { $_ -match $sensivel })

    $pattern = '^\s*{0}\s*=' -f [regex]::Escape($Name)
    $saida   = @($before | Where-Object { $_ -notmatch $pattern })
    [System.IO.File]::WriteAllText($script:Gate5VmxPath, (($saida -join "`r`n") + "`r`n"), $encoding)

    $depois  = @([System.IO.File]::ReadAllLines($script:Gate5VmxPath) | Where-Object { $_ -match $sensivel })
    $intacto = ($antes.Count -eq $depois.Count)
    if ($intacto) {
        for ($i = 0; $i -lt $antes.Count; $i++) {
            if ($antes[$i] -cne $depois[$i]) { $intacto = $false; break }
        }
    }
    if (-not $intacto) {
        [System.IO.File]::WriteAllText($script:Gate5VmxPath, (($before -join "`r`n") + "`r`n"), $encoding)
        throw ("GATE5: a remocao de '{0}' teria alterado material criptografico do .vmx; alteracao revertida." -f $Name)
    }
    Write-Gate5Log ("Chave '{0}' removida do .vmx." -f $Name)
}

function Get-Gate5EfiBootDevice {
    # Le do vmware.log qual dispositivo o firmware EFI escolheu de fato, na forma
    #   ...Z ... Guest: About to do EFI boot: Windows Boot Manager
    #
    # E a unica prova objetiva de POR ONDE a VM bootou. A tela nao serve: o
    # prompt optico desaparece tanto quando a tecla e aceita quanto quando ele
    # nunca chegou a ser exibido, e as duas situacoes terminam numa tela clara.
    #
    # O vmware-vmx mantem o log aberto para escrita durante toda a execucao, por
    # isso a leitura e compartilhada. Reboots do Setup escrevem no MESMO arquivo
    # (o log so rotaciona no power-on), de onde vem devolver a ULTIMA ocorrencia.
    param(
        [nullable[datetime]]$Since,      # UTC; descarta boots anteriores a este instante
        [string]$LogPath = (Join-Path $script:Gate5VmDir 'vmware.log')
    )
    if (-not (Test-Path -LiteralPath $LogPath)) { return $null }
    $fs = [System.IO.File]::Open($LogPath, 'Open', 'Read', 'ReadWrite')
    try {
        $reader = New-Object System.IO.StreamReader($fs)
        try {
            $ultimo = $null
            while (-not $reader.EndOfStream) {
                $linha = $reader.ReadLine()
                if ($linha -notmatch 'About to do EFI boot:\s*(.+?)\s*$') { continue }
                $device = $Matches[1]
                $quando = $null
                if ($linha -match '^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)') {
                    $quando = [datetime]::Parse(
                        $Matches[1],
                        [Globalization.CultureInfo]::InvariantCulture,
                        [Globalization.DateTimeStyles]::AdjustToUniversal -bor
                        [Globalization.DateTimeStyles]::AssumeUniversal)
                }
                # Sem timestamp legivel a linha e descartada quando ha filtro:
                # aceitar um boot de origem desconhecida como se fosse o atual
                # e exatamente o tipo de prova fraca que este gate recusa.
                if ($null -ne $Since -and (($null -eq $quando) -or ($quando -lt $Since))) { continue }
                $ultimo = [pscustomobject]@{
                    Device    = $device
                    WhenUtc   = $quando
                    IsOptical = [bool]($device -match 'CDROM|CD-ROM|DVD')
                    IsDisk    = [bool]($device -match 'Windows Boot Manager|NVME|NVMe|Hard Disk')
                }
            }
            return $ultimo
        } finally { $reader.Dispose() }
    } finally { $fs.Dispose() }
}

function Test-Gate5VmwareUiRunning {
    # A interface do VMware Workstation ('vmware.exe') carrega a configuracao da
    # VM ao abri-la e REESCREVE o .vmx a partir dessa copia em cache no Power On.
    # Qualquer chave acrescentada ao arquivo depois disso e descartada em
    # silencio - a escrita e a releitura da automacao passam, e o firmware ainda
    # assim nunca ve a chave. Provado na RUN-02 tentativa 3: efi.bootOrder foi
    # gravada as 16:02:38Z e o vmware-vmx leu o DICT as 16:02:55.782Z ja sem ela,
    # enquanto RemoteDisplay.vnc.port - gravada antes de a interface abrir a VM -
    # sobreviveu.
    return [bool](@(Get-Process -Name 'vmware' -ErrorAction SilentlyContinue).Count)
}

function Get-Gate5VmwareLogDictValue {
    # Le um valor do dump DICT que o vmware-vmx imprime no vmware.log ao ligar.
    # E a prova de que a chave chegou de fato ao firmware: o .vmx em disco pode
    # ter sido reescrito por cima depois, e conferi-lo ali nao demonstra nada.
    param(
        [Parameter(Mandatory)][string]$Key,
        [string]$LogPath = (Join-Path $script:Gate5VmDir 'vmware.log')
    )
    if (-not (Test-Path -LiteralPath $LogPath)) { return $null }
    $fs = [System.IO.File]::Open($LogPath, 'Open', 'Read', 'ReadWrite')
    try {
        $reader = New-Object System.IO.StreamReader($fs)
        try {
            $padrao = 'DICT\s+{0}\s*=\s*"(.*)"\s*$' -f [regex]::Escape($Key)
            $valor = $null
            while (-not $reader.EndOfStream) {
                $linha = $reader.ReadLine()
                if ($linha -match $padrao) { $valor = $Matches[1] }
            }
            return $valor
        } finally { $reader.Dispose() }
    } finally { $fs.Dispose() }
}

function Get-Gate5EfiBootOrderRejections {
    # Tokens de efi.bootOrder que o FIRMWARE recusou neste power-on, na forma
    #   ...Z ... Unrecognized efi.bootOrder: "cdrom".
    #
    # Detector de regressao: a automacao nao grava mais 'efi.bootOrder' (ver
    # Set-Gate5OpticalBootFirst, que ate a remove do .vmx). Se estas linhas
    # voltarem a aparecer, alguem reintroduziu a chave e o boot vai falhar em
    # silencio, parecendo "o firmware ignorou a ordem".
    param([string]$LogPath = (Join-Path $script:Gate5VmDir 'vmware.log'))
    if (-not (Test-Path -LiteralPath $LogPath)) { return @() }
    $fs = [System.IO.File]::Open($LogPath, 'Open', 'Read', 'ReadWrite')
    try {
        $reader = New-Object System.IO.StreamReader($fs)
        try {
            $tokens = New-Object System.Collections.Generic.List[string]
            while (-not $reader.EndOfStream) {
                $linha = $reader.ReadLine()
                if ($linha -match 'Unrecognized efi\.bootOrder:\s*"([^"]*)"') {
                    if (-not $tokens.Contains($Matches[1])) { $tokens.Add($Matches[1]) }
                }
            }
            return @($tokens)
        } finally { $reader.Dispose() }
    } finally { $fs.Dispose() }
}

function Set-Gate5OpticalBootFirst {
    # Poe a unidade optica na frente do disco na ordem de boot do firmware.
    #
    # Numa VM recem-criada o disco esta vazio e o firmware EFI cai no CD sozinho
    # - foi assim que a RUN-01 instalou. Depois da primeira instalacao isso deixa
    # de valer: o Windows grava a sua entrada 'Windows Boot Manager' na NVRAM e o
    # firmware passa a boota-la direto, SEM exibir 'Press any key to boot from CD
    # or DVD'. Foi o que reprovou as duas tentativas da RUN-02: nenhuma tecla
    # poderia ter ajudado, porque prompt nenhum chegou a existir (vmware.log:
    # 'About to do EFI boot: Windows Boot Manager', 3,6 s apos o power-on).
    #
    # O Workstation documenta 'bios.bootOrder' com os tokens cdrom/hdd para
    # priorizacao do meio optico durante a instalacao. E a unica chave de ordem
    # de boot com vocabulario documentado, e por isso a usada aqui.
    #
    # Se esta instalacao do Workstation nao honrar a chave, o caminho suportado e
    # o menu de firmware da propria interface (Power -> Power On to Firmware),
    # com selecao manual do CD/DVD neste primeiro boot - NAO um vocabulario
    # alternativo descoberto por tentativa. Ver docs/48 (limitacao observada).
    #
    # A NVRAM nao e tocada nem removida: a ordem e imposta por cima dela na
    # inicializacao do firmware, e o vTPM depende daquele arquivo.
    param([string]$Value = 'cdrom,hdd')
    $validos = @('cdrom', 'hdd', 'floppy', 'ethernet')
    foreach ($t in ($Value -split ',')) {
        if ($validos -notcontains $t.Trim().ToLowerInvariant()) {
            throw ("GATE5: token invalido em bios.bootOrder: '{0}'." -f $t)
        }
    }
    # A configuracao so e lida no power-on, e o VMware reescreve o .vmx ao
    # desligar: gravar com a VM ligada nao teria efeito e ainda seria perdido.
    if (Test-Gate5VmPoweredOn) {
        throw 'GATE5: a ordem de boot so pode ser ajustada com a VM desligada.'
    }
    # Com a interface aberta a escrita PASSA e mesmo assim nao chega ao firmware
    # (ver Test-Gate5VmwareUiRunning). Falhar aqui e melhor do que gravar, reler
    # com sucesso e so descobrir o descarte depois de gastar um gate de power-on.
    if (Test-Gate5VmwareUiRunning) {
        throw 'GATE5: a interface do VMware esta aberta e descartaria a ordem de boot no Power On.'
    }
    # 'efi.bootOrder' foi tentada na RUN-02 e o firmware recusou os tokens que
    # recebeu ('Unrecognized efi.bootOrder'). A chave sai do .vmx para que o
    # proximo power-on teste 'bios.bootOrder' sem um valor ja reprovado ao lado.
    Remove-Gate5VmxEntry -Name 'efi.bootOrder'
    Set-Gate5VmxEntry -Name 'bios.bootOrder' -Value $Value
    $lido = Get-Gate5VmxValue -Key 'bios.bootOrder'
    if ($lido -ne $Value) {
        throw ("GATE5: bios.bootOrder nao persistiu no .vmx (lido '{0}', esperado '{1}')." -f $lido, $Value)
    }
    Write-Gate5Log ("Ordem de boot do firmware fixada em '{0}': a midia optica vem antes do disco." -f $Value)
}

function Remove-Gate5BootOverride {
    # Transicao simetrica de Set-Gate5OpticalBootFirst: retira do .vmx a override
    # de ordem de boot depois que ela ja cumpriu o seu papel.
    #
    # A override existe para UM boot - o primeiro, pela midia de instalacao. Dali
    # em diante o estado operacional correto e a AUSENCIA da chave: o firmware
    # segue a entrada 'Windows Boot Manager' que o Windows gravou na NVRAM. E o
    # mesmo estado que a fase de isolamento impoe (gate5-provision.ps1, FASE 11) e
    # que o validador do baseline confere em 'sem-override-de-boot'. A chave e
    # REMOVIDA, e nao invertida para 'hdd', para que nada no .vmx continue
    # disputando a decisao do firmware.
    #
    # Sem esta transicao a override sobrevive a todos os reboots do Setup e, se o
    # run abortar antes da FASE 11, fica no arquivo indefinidamente. Foi o que
    # aconteceu na RUN-02: o run parou em GUEST_PHASE_FAILED_INSTALLWAIT e os seis
    # reboots seguintes registraram 'About to do EFI boot: EFI VMware Virtual SATA
    # CDROM Drive' ANTES do 'Windows Boot Manager'. Nenhum chegou a bootar o
    # instalador porque o prompt "Press any key" expirou - seis vezes seguidas.
    #
    # A NVRAM nao e tocada nem removida: o vTPM depende daquele arquivo.
    if (Test-Gate5VmPoweredOn) {
        throw 'GATE5: a ordem de boot so pode ser ajustada com a VM desligada.'
    }
    # Mesma armadilha da escrita: com a interface aberta a remocao PASSA no
    # arquivo e e descartada no Power On, a partir da copia em cache.
    if (Test-Gate5VmwareUiRunning) {
        throw 'GATE5: a interface do VMware esta aberta e descartaria a remocao da ordem de boot no Power On.'
    }
    Remove-Gate5VmxEntry -Name 'bios.bootOrder'
    Remove-Gate5VmxEntry -Name 'efi.bootOrder'
    # Idempotente: chamar de novo com as chaves ja ausentes nao reescreve o .vmx
    # (Remove-Gate5VmxEntry retorna cedo) e ainda assim reconfere o estado.
    foreach ($chave in @('bios.bootOrder', 'efi.bootOrder')) {
        $lido = Get-Gate5VmxValue -Key $chave
        if ($null -ne $lido) {
            throw ("GATE5: '{0}' continua no .vmx apos a remocao (valor '{1}')." -f $chave, $lido)
        }
    }
    Write-Gate5Log 'Override de ordem de boot retirada do .vmx: a VM volta a bootar pela ordem registrada no UEFI/NVRAM.'
}

function Set-Gate5VncConsole {
    # Liga/desliga o console VNC local do VMware no VMX (VM deve estar desligada).
    # Nunca define senha porque o socket fica preso a 127.0.0.1 e o canal existe
    # somente durante a instalacao do guest; a fase de isolamento o remove.
    param([Parameter(Mandatory)][bool]$Enabled)
    if (-not (Test-Path $script:Gate5VmxPath)) { throw 'GATE5: VMX inexistente ao configurar o console VNC.' }
    if ($Enabled) {
        Set-Gate5VmxEntry -Name 'RemoteDisplay.vnc.enabled' -Value 'TRUE'
        Set-Gate5VmxEntry -Name 'RemoteDisplay.vnc.port'    -Value ([string]$script:Gate5VncPort)
        Set-Gate5VmxEntry -Name 'RemoteDisplay.vnc.ip'      -Value '127.0.0.1'
    } elseif ((Get-Gate5VmEncryptionState).Encrypted) {
        # Em VM criptografada nao se remove linha (o arquivo nao pode ser
        # reescrito); desligar o console tem o mesmo efeito e o validador
        # aceita ausente OU FALSE, alem de conferir o listener real no host.
        Set-Gate5VmxEntry -Name 'RemoteDisplay.vnc.enabled' -Value 'FALSE'
    } else {
        $lines = @(Get-Content -LiteralPath $script:Gate5VmxPath | Where-Object { $_ -notmatch '^RemoteDisplay\.vnc\.' })
        Set-Gate5TextFile -Path $script:Gate5VmxPath -Lines $lines
    }
    Write-Gate5Log ("Console VNC local {0} (127.0.0.1:{1})." -f $(if ($Enabled) { 'HABILITADO' } else { 'DESLIGADO' }), $script:Gate5VncPort)
}

function Send-Gate5VncKey {
    # Cliente RFB 3.8 minimo: handshake, auth None e um par KeyEvent down/up.
    # Retorna 'OK' ou uma descricao do erro (nunca lanca, para nao derrubar o
    # laco de boot quando o console ainda nao esta pronto).
    param([Parameter(Mandatory)][uint32]$Keysym, [int]$Port = $script:Gate5VncPort)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $client.Connect('127.0.0.1', $Port)
        $stream = $client.GetStream()
        $stream.ReadTimeout = 5000; $stream.WriteTimeout = 5000

        $buf = New-Object byte[] 12
        if ($stream.Read($buf, 0, 12) -lt 12) { return 'handshake RFB incompleto' }
        $stream.Write([Text.Encoding]::ASCII.GetBytes("RFB 003.008`n"), 0, 12)

        $one = New-Object byte[] 1
        if ($stream.Read($one, 0, 1) -lt 1) { return 'servidor nao ofereceu tipos de seguranca' }
        $count = [int]$one[0]
        if ($count -eq 0) { return 'servidor recusou a conexao' }
        $types = New-Object byte[] $count
        $stream.Read($types, 0, $count) | Out-Null
        if ($types -notcontains 1) { return ('console VNC exige autenticacao (tipos: ' + ($types -join ',') + ')') }
        $stream.Write([byte[]]@(1), 0, 1)

        $result = New-Object byte[] 4
        $stream.Read($result, 0, 4) | Out-Null
        if (($result[0] -bor $result[1] -bor $result[2] -bor $result[3]) -ne 0) { return 'SecurityResult negativo' }

        $stream.Write([byte[]]@(1), 0, 1)   # ClientInit: sessao compartilhada
        $serverInit = New-Object byte[] 24
        $stream.Read($serverInit, 0, 24) | Out-Null
        $nameLen = [int]$serverInit[20] * 16777216 + [int]$serverInit[21] * 65536 +
                   [int]$serverInit[22] * 256 + [int]$serverInit[23]
        if ($nameLen -gt 0) {
            $name = New-Object byte[] $nameLen
            $stream.Read($name, 0, $nameLen) | Out-Null
        }

        foreach ($down in 1, 0) {
            $msg = [byte[]]@(4, [byte]$down, 0, 0,
                             [byte](($Keysym -shr 24) -band 0xFF), [byte](($Keysym -shr 16) -band 0xFF),
                             [byte](($Keysym -shr 8)  -band 0xFF), [byte]($Keysym -band 0xFF))
            $stream.Write($msg, 0, 8)
            $stream.Flush()
            Start-Sleep -Milliseconds 120
        }
        Sync-Gate5VncStream -Stream $stream
        return 'OK'
    } catch {
        return ('erro: ' + $_.Exception.Message)
    } finally {
        $client.Close()
    }
}

function Sync-Gate5VncStream {
    # Fecha o ciclo com o servidor VNC antes de encerrar a conexao: pede uma
    # atualizacao de framebuffer e espera a resposta. Sem isso o socket era
    # fechado logo apos os KeyEvent e o servidor descartava a entrada ainda nao
    # processada - a tecla "chegava" pelo protocolo mas nunca no guest.
    param([Parameter(Mandatory)][System.IO.Stream]$Stream)
    try {
        # FramebufferUpdateRequest incremental de 1x1 pixel: barato e suficiente
        # para forcar o servidor a processar tudo o que veio antes.
        $Stream.Write([byte[]]@(3, 1, 0,0, 0,0, 0,1, 0,1), 0, 10)
        $Stream.Flush()
        $eco = New-Object byte[] 1
        $Stream.ReadTimeout = 4000
        [void]$Stream.Read($eco, 0, 1)
    } catch { }
    Start-Sleep -Milliseconds 250
}

function Send-Gate5VncPointerClick {
    # Clique pelo console VNC local. Serve quando o teclado nao chega ao guest
    # (o console da interface do VMware pode deter a entrada): o evento de
    # ponteiro do RFB atinge a coordenada diretamente, sem depender de foco.
    param(
        [Parameter(Mandatory)][int]$X,
        [Parameter(Mandatory)][int]$Y,
        [int]$Port = $script:Gate5VncPort
    )
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $client.Connect('127.0.0.1', $Port)
        $s = $client.GetStream(); $s.ReadTimeout = 6000; $s.WriteTimeout = 6000
        $buf = New-Object byte[] 12
        if ($s.Read($buf, 0, 12) -lt 12) { return 'handshake RFB incompleto' }
        $s.Write([Text.Encoding]::ASCII.GetBytes("RFB 003.008`n"), 0, 12)
        $one = New-Object byte[] 1
        if ($s.Read($one, 0, 1) -lt 1) { return 'sem tipos de seguranca' }
        $count = [int]$one[0]; if ($count -eq 0) { return 'conexao recusada' }
        $types = New-Object byte[] $count; $s.Read($types, 0, $count) | Out-Null
        if ($types -notcontains 1) { return 'console exige autenticacao' }
        $s.Write([byte[]]@(1), 0, 1)
        $res = New-Object byte[] 4; $s.Read($res, 0, 4) | Out-Null
        if (($res[0] -bor $res[1] -bor $res[2] -bor $res[3]) -ne 0) { return 'SecurityResult negativo' }
        $s.Write([byte[]]@(1), 0, 1)
        $si = New-Object byte[] 24; $s.Read($si, 0, 24) | Out-Null
        $nameLen = [int]$si[20]*16777216 + [int]$si[21]*65536 + [int]$si[22]*256 + [int]$si[23]
        if ($nameLen -gt 0) { $nm = New-Object byte[] $nameLen; $s.Read($nm, 0, $nameLen) | Out-Null }

        # PointerEvent: tipo 5, mascara de botoes, x e y (big-endian).
        $pointer = {
            param($stream, [int]$mask, [int]$px, [int]$py)
            $m = [byte[]]@(5, [byte]$mask,
                           [byte](($px -shr 8) -band 0xFF), [byte]($px -band 0xFF),
                           [byte](($py -shr 8) -band 0xFF), [byte]($py -band 0xFF))
            $stream.Write($m, 0, 6); $stream.Flush(); Start-Sleep -Milliseconds 120
        }
        & $pointer $s 0 $X $Y      # move
        & $pointer $s 1 $X $Y      # botao esquerdo pressionado
        & $pointer $s 0 $X $Y      # solto
        Sync-Gate5VncStream -Stream $s
        return 'OK'
    } catch { return ('erro: ' + $_.Exception.Message) }
    finally { $client.Close() }
}

function Send-Gate5VncKeyCombo {
    # Combinacao de teclas pelo console VNC local: pressiona os keysyms na ordem
    # dada e solta na ordem inversa (ex.: Alt_L + 'n' para acionar um acelerador
    # sublinhado de dialogo). Usa acelerador em vez de navegar por setas porque
    # o alvo fica deterministico, sem depender de onde esta o foco.
    param([Parameter(Mandatory)][uint32[]]$Keysyms, [int]$Port = $script:Gate5VncPort)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $client.Connect('127.0.0.1', $Port)
        $s = $client.GetStream(); $s.ReadTimeout = 5000; $s.WriteTimeout = 5000
        $buf = New-Object byte[] 12
        if ($s.Read($buf, 0, 12) -lt 12) { return 'handshake RFB incompleto' }
        $s.Write([Text.Encoding]::ASCII.GetBytes("RFB 003.008`n"), 0, 12)
        $one = New-Object byte[] 1
        if ($s.Read($one, 0, 1) -lt 1) { return 'sem tipos de seguranca' }
        $count = [int]$one[0]; if ($count -eq 0) { return 'conexao recusada' }
        $types = New-Object byte[] $count; $s.Read($types, 0, $count) | Out-Null
        if ($types -notcontains 1) { return 'console exige autenticacao' }
        $s.Write([byte[]]@(1), 0, 1)
        $res = New-Object byte[] 4; $s.Read($res, 0, 4) | Out-Null
        if (($res[0] -bor $res[1] -bor $res[2] -bor $res[3]) -ne 0) { return 'SecurityResult negativo' }
        $s.Write([byte[]]@(1), 0, 1)
        $si = New-Object byte[] 24; $s.Read($si, 0, 24) | Out-Null
        $nameLen = [int]$si[20]*16777216 + [int]$si[21]*65536 + [int]$si[22]*256 + [int]$si[23]
        if ($nameLen -gt 0) { $nm = New-Object byte[] $nameLen; $s.Read($nm, 0, $nameLen) | Out-Null }

        $enviar = {
            param($stream, [uint32]$k, [int]$down)
            $m = [byte[]]@(4, [byte]$down, 0, 0,
                           [byte](($k -shr 24) -band 0xFF), [byte](($k -shr 16) -band 0xFF),
                           [byte](($k -shr 8) -band 0xFF),  [byte]($k -band 0xFF))
            $stream.Write($m, 0, 8); $stream.Flush(); Start-Sleep -Milliseconds 60
        }
        foreach ($k in $Keysyms) { & $enviar $s $k 1 }
        for ($i = $Keysyms.Count - 1; $i -ge 0; $i--) { & $enviar $s $Keysyms[$i] 0 }
        Sync-Gate5VncStream -Stream $s
        return 'OK'
    } catch { return ('erro: ' + $_.Exception.Message) }
    finally { $client.Close() }
}

function Save-Gate5VncScreenshot {
    # Captura a tela do guest pelo console VNC LOCAL (127.0.0.1), decodificando
    # RAW do proprio protocolo RFB. Necessario porque 'vmcli MKS
    # captureScreenshot' exige a senha da criptografia em VM criptografada, e
    # essa senha nunca passa pela automacao (docs/48 §12). Retorna 'OK' ou o erro.
    param([Parameter(Mandatory)][string]$Path, [int]$Port = $script:Gate5VncPort)

    # System.Drawing nao e carregado sozinho em 'powershell -NoProfile
    # -NonInteractive', que e como as fases rodam: sem isto a captura falhava
    # silenciosamente no watcher e o detector nunca tinha imagem para analisar.
    Add-Type -AssemblyName System.Drawing -ErrorAction SilentlyContinue
    # O diretorio de trabalho do .NET nao acompanha o do PowerShell, entao um
    # caminho relativo gravaria em outro lugar (ou falharia com "erro generico
    # de GDI+"). Resolvemos para absoluto e garantimos o diretorio.
    if (-not [System.IO.Path]::IsPathRooted($Path)) { $Path = Join-Path (Get-Location).Path $Path }
    $destDir = Split-Path -Parent $Path
    if ($destDir -and -not (Test-Path -LiteralPath $destDir)) {
        New-Item -ItemType Directory -Force $destDir | Out-Null
    }

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $client.Connect('127.0.0.1', $Port)
        $s = $client.GetStream(); $s.ReadTimeout = 20000; $s.WriteTimeout = 20000

        function Read-Exact([System.IO.Stream]$Stream, [int]$Count) {
            $buf = New-Object byte[] $Count; $off = 0
            while ($off -lt $Count) {
                $n = $Stream.Read($buf, $off, $Count - $off)
                if ($n -le 0) { throw 'conexao encerrada pelo servidor VNC' }
                $off += $n
            }
            # ',': sem o operador de virgula o PowerShell DESENROLA o array no
            # pipeline e o chamador recebe um Object[] de um elemento por byte.
            # Marshal::Copy entao re-coage o vetor inteiro a cada chamada - com
            # rects de 1 MB (tela 1024x768) uma captura passava de minutos e o
            # watcher perdia a janela do prompt de boot. Em 640x480 o custo era
            # pequeno o bastante para o defeito nao aparecer.
            return ,$buf
        }

        [void](Read-Exact $s 12)
        $s.Write([Text.Encoding]::ASCII.GetBytes("RFB 003.008`n"), 0, 12)
        $n = (Read-Exact $s 1)[0]
        if ($n -eq 0) { return 'servidor recusou a conexao' }
        $types = Read-Exact $s $n
        if ($types -notcontains 1) { return 'console VNC exige autenticacao' }
        $s.Write([byte[]]@(1), 0, 1)
        $res = Read-Exact $s 4
        if (($res[0] -bor $res[1] -bor $res[2] -bor $res[3]) -ne 0) { return 'SecurityResult negativo' }
        $s.Write([byte[]]@(1), 0, 1)                       # ClientInit compartilhado
        $si = Read-Exact $s 24
        $w = [int]$si[0] * 256 + [int]$si[1]
        $h = [int]$si[2] * 256 + [int]$si[3]
        $nameLen = [int]$si[20] * 16777216 + [int]$si[21] * 65536 + [int]$si[22] * 256 + [int]$si[23]
        if ($nameLen -gt 0) { [void](Read-Exact $s $nameLen) }
        if ($w -le 0 -or $h -le 0) { return "dimensoes invalidas ($w x $h)" }

        # SetPixelFormat: 32bpp BGRX, para decodificar RAW sem ambiguidade.
        $s.Write([byte[]]@(0,0,0,0, 32,24,0,1, 0,255,0,255,0,255, 16,8,0, 0,0,0), 0, 20)
        # SetEncodings: apenas RAW(0)
        $s.Write([byte[]]@(2,0,0,1, 0,0,0,0), 0, 8)
        # FramebufferUpdateRequest completo (incremental=0)
        $req = [byte[]]@(3, 0, 0,0, 0,0,
                         [byte](($w -shr 8) -band 0xFF), [byte]($w -band 0xFF),
                         [byte](($h -shr 8) -band 0xFF), [byte]($h -band 0xFF))
        $s.Write($req, 0, 10); $s.Flush()

        $hdr = Read-Exact $s 4
        if ($hdr[0] -ne 0) { return "mensagem inesperada do servidor (tipo $($hdr[0]))" }
        $rects = [int]$hdr[2] * 256 + [int]$hdr[3]
        $bmp = New-Object System.Drawing.Bitmap($w, $h)
        for ($r = 0; $r -lt $rects; $r++) {
            $rh = Read-Exact $s 12
            $rx = [int]$rh[0]*256 + [int]$rh[1]; $ry = [int]$rh[2]*256 + [int]$rh[3]
            $rw = [int]$rh[4]*256 + [int]$rh[5]; $rhh = [int]$rh[6]*256 + [int]$rh[7]
            $enc = [BitConverter]::ToInt32(@($rh[11], $rh[10], $rh[9], $rh[8]), 0)
            if ($enc -ne 0) { return "encoding nao-RAW recebido ($enc)" }
            if ($rw -le 0 -or $rhh -le 0) { continue }
            $data = Read-Exact $s ($rw * $rhh * 4)
            $rect = New-Object System.Drawing.Rectangle($rx, $ry, $rw, $rhh)
            $bd = $bmp.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::WriteOnly,
                                [System.Drawing.Imaging.PixelFormat]::Format32bppRgb)
            try {
                for ($y = 0; $y -lt $rhh; $y++) {
                    [System.Runtime.InteropServices.Marshal]::Copy(
                        $data, $y * $rw * 4, [IntPtr]($bd.Scan0.ToInt64() + $y * $bd.Stride), $rw * 4)
                }
            } finally { $bmp.UnlockBits($bd) }
        }
        $bmp.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
        $bmp.Dispose()
        return 'OK'
    } catch {
        return ('erro: ' + $_.Exception.Message)
    } finally { $client.Close() }
}

function Test-Gate5FirmwareScreen {
    # Decide, pelo FRAMEBUFFER, se o guest esta na fase de firmware (prompt de
    # boot pelo CD, lista de dispositivos ou Boot Manager) ou ja dentro do
    # Windows Setup. E o que autoriza enviar a tecla do prompt: no firmware uma
    # tecla e inofensiva, no Setup ela poderia acionar um botao em foco.
    #
    # Criterio: as telas de firmware sao quase totalmente pretas (texto claro
    # sobre fundo preto), enquanto o Setup pinta a tela inteira de azul-escuro.
    # Amostragem de 1 em cada 4 pixels nos dois eixos - suficiente e barato.
    param([Parameter(Mandatory)][string]$ImagePath, [double]$MinDark = 0.90)
    if (-not (Test-Path -LiteralPath $ImagePath)) { return $null }
    Add-Type -AssemblyName System.Drawing -ErrorAction SilentlyContinue
    $bmp = New-Object System.Drawing.Bitmap($ImagePath)
    try {
        $rect = New-Object System.Drawing.Rectangle(0, 0, $bmp.Width, $bmp.Height)
        $bd = $bmp.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::ReadOnly,
                            [System.Drawing.Imaging.PixelFormat]::Format32bppRgb)
        try {
            $bytes = New-Object byte[] ($bd.Stride * $bmp.Height)
            [System.Runtime.InteropServices.Marshal]::Copy($bd.Scan0, $bytes, 0, $bytes.Length)
            $escuros = 0; $total = 0
            for ($y = 0; $y -lt $bmp.Height; $y += 4) {
                $linha = $y * $bd.Stride
                for ($x = 0; $x -lt $bmp.Width; $x += 4) {
                    $i = $linha + $x * 4
                    if ((([int]$bytes[$i] + [int]$bytes[$i + 1] + [int]$bytes[$i + 2]) / 3) -lt 32) { $escuros++ }
                    $total++
                }
            }
            $fracao = if ($total -gt 0) { [double]$escuros / $total } else { 0 }
            return [pscustomobject]@{
                DarkFraction = [math]::Round($fracao, 4)
                IsFirmware   = ($fracao -ge $MinDark)
                Width        = $bmp.Width
                Height       = $bmp.Height
            }
        } finally { $bmp.UnlockBits($bd) }
    } finally { $bmp.Dispose() }
}

function Test-Gate5BootPromptOnScreen {
    # Detecta o PROMPT "Press any key to boot from CD or DVD" especificamente,
    # e nao apenas "tela preta". O prompt escreve texto claro numa FAIXA
    # SUPERIOR estreita; entre as fases do firmware a tela fica preta e VAZIA.
    # Sem essa distincao a automacao gastava sua tecla numa tela preta anterior
    # ao prompt, e quando o prompt aparecia ja nao restava tecla para envia-lo.
    param(
        [Parameter(Mandatory)][string]$ImagePath,
        # O sinal discriminante e o TEXTO CLARO NO TOPO. O criterio de escuridao
        # fica frouxo de proposito: o prompt costuma aparecer sobreposto a tela
        # anterior (ex.: sobre o Boot Manager), quando a fracao escura cai para
        # ~0,64 - exigir 0,85 ali fazia o prompt real passar despercebido.
        [double]$MinDark = 0.50,
        [int]$MinBrightTop = 120
    )
    if (-not (Test-Path -LiteralPath $ImagePath)) { return $null }
    Add-Type -AssemblyName System.Drawing -ErrorAction SilentlyContinue
    $bmp = New-Object System.Drawing.Bitmap($ImagePath)
    try {
        $rect = New-Object System.Drawing.Rectangle(0, 0, $bmp.Width, $bmp.Height)
        $bd = $bmp.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::ReadOnly,
                            [System.Drawing.Imaging.PixelFormat]::Format32bppRgb)
        try {
            $bytes = New-Object byte[] ($bd.Stride * $bmp.Height)
            [System.Runtime.InteropServices.Marshal]::Copy($bd.Scan0, $bytes, 0, $bytes.Length)
            $escuros = 0; $total = 0; $clarosTopo = 0
            $topo = [math]::Min(46, $bmp.Height - 1)
            for ($y = 0; $y -lt $bmp.Height; $y += 2) {
                $linha = $y * $bd.Stride
                for ($x = 0; $x -lt $bmp.Width; $x += 2) {
                    $i = $linha + $x * 4
                    $lum = ([int]$bytes[$i] + [int]$bytes[$i + 1] + [int]$bytes[$i + 2]) / 3
                    if ($lum -lt 32) { $escuros++ }
                    $total++
                    if ($y -ge 8 -and $y -le $topo -and $lum -gt 180) { $clarosTopo++ }
                }
            }
            $fracao = if ($total -gt 0) { [double]$escuros / $total } else { 0 }
            return [pscustomobject]@{
                DarkFraction = [math]::Round($fracao, 4)
                BrightTop    = $clarosTopo
                HasPrompt    = (($fracao -ge $MinDark) -and ($clarosTopo -ge $MinBrightTop))
                IsFirmware   = ($fracao -ge $MinDark)
            }
        } finally { $bmp.UnlockBits($bd) }
    } finally { $bmp.Dispose() }
}

function Get-Gate5IsoEntries {
    # Lista as entradas de um diretorio da ISO pelo namespace Joliet - que e o
    # que o Windows Setup usa para nomes longos como 'Autounattend.xml'. Serve
    # para provar onde os arquivos estao de fato na midia, e nao apenas que
    # aparecem em algum lugar dos bytes.
    #
    # Os nomes trazem o sufixo de versao ';1' do ISO9660, que os drivers de
    # sistema de arquivos ignoram; normalizamos aqui para comparar por nome.
    param(
        [Parameter(Mandatory)][string]$IsoPath,
        [string]$SubPath   # ex.: 'gate5' ou 'gate5/rules'; vazio = raiz
    )
    $fs = [System.IO.File]::Open($IsoPath, 'Open', 'Read', 'ReadWrite')
    try {
        $sector = New-Object byte[] 2048
        $svdLba = $null
        for ($i = 16; $i -lt 40; $i++) {
            $fs.Seek($i * 2048, 'Begin') | Out-Null
            if ($fs.Read($sector, 0, 2048) -lt 2048) { break }
            $id = [Text.Encoding]::ASCII.GetString($sector, 1, 5)
            if ($id -ne 'CD001') { continue }
            if ($sector[0] -eq 255) { break }                     # terminador
            # Tipo 2 = Supplementary (Joliet quando o escape e %/@ %/C %/E)
            if ($sector[0] -eq 2 -and $sector[88] -eq 0x25 -and $sector[89] -eq 0x2F) {
                $svdLba = [BitConverter]::ToUInt32($sector, 156 + 2)
                $svdLen = [BitConverter]::ToUInt32($sector, 156 + 10)
                break
            }
        }
        if ($null -eq $svdLba) { return $null }                   # sem Joliet

        $lerDiretorio = {
            param([uint32]$Lba, [uint32]$Tamanho)
            $dir = New-Object byte[] $Tamanho
            $fs.Seek([int64]$Lba * 2048, 'Begin') | Out-Null
            $fs.Read($dir, 0, $Tamanho) | Out-Null
            $itens = @()
            $p = 0
            while ($p -lt $dir.Length) {
                $len = $dir[$p]
                if ($len -eq 0) {
                    $p = [int](([math]::Floor($p / 2048) + 1) * 2048)   # proximo setor
                    if ($p -ge $dir.Length) { break }
                    continue
                }
                $nameLen = $dir[$p + 32]
                if ($nameLen -gt 1) {
                    $nome = [Text.Encoding]::BigEndianUnicode.GetString($dir, $p + 33, $nameLen)
                    $itens += [pscustomobject]@{
                        Name        = ($nome -replace ';\d+$', '')
                        IsDirectory = (($dir[$p + 25] -band 0x02) -ne 0)
                        Lba         = [BitConverter]::ToUInt32($dir, $p + 2)
                        Size        = [BitConverter]::ToUInt32($dir, $p + 10)
                    }
                }
                $p += $len
            }
            return $itens
        }

        $atualLba = $svdLba; $atualLen = $svdLen
        if ($SubPath) {
            foreach ($parte in ($SubPath -split '[\/]' | Where-Object { $_ })) {
                $filhos = & $lerDiretorio $atualLba $atualLen
                $alvo = @($filhos | Where-Object { $_.IsDirectory -and $_.Name -eq $parte }) | Select-Object -First 1
                if (-not $alvo) { return $null }
                $atualLba = $alvo.Lba; $atualLen = $alvo.Size
            }
        }
        return (& $lerDiretorio $atualLba $atualLen)
    } finally { $fs.Close() }
}

function Get-Gate5IsoFileBytes {
    # Le os bytes de um arquivo DENTRO da ISO, pelo extent do namespace Joliet.
    # Permite validar o Autounattend realmente gravado na midia sem monta-la e
    # sem nunca imprimir seu conteudo (ele carrega a senha de bootstrap).
    param(
        [Parameter(Mandatory)][string]$IsoPath,
        [Parameter(Mandatory)][string]$Name,
        [string]$SubPath
    )
    # Diretorio inexistente devolve $null; sob Set-StrictMode filtrar $null por
    # propriedade lanca, e "arquivo ausente" tem de ser $null, nunca excecao.
    $entradas = @(Get-Gate5IsoEntries -IsoPath $IsoPath -SubPath $SubPath | Where-Object { $_ })
    $alvo = @($entradas | Where-Object { -not $_.IsDirectory -and $_.Name -eq $Name }) | Select-Object -First 1
    if (-not $alvo) { return $null }
    $fs = [System.IO.File]::Open($IsoPath, 'Open', 'Read', 'ReadWrite')
    try {
        $buf = New-Object byte[] $alvo.Size
        $fs.Seek([int64]$alvo.Lba * 2048, 'Begin') | Out-Null
        # Leitura em laco: uma unica chamada a Read nao garante preencher o
        # buffer, e o redistribuivel embarcado tem dezenas de MB - conferir o
        # SHA-256 sobre uma leitura parcial reprovaria um arquivo integro.
        $lidos = 0
        while ($lidos -lt $alvo.Size) {
            $n = $fs.Read($buf, $lidos, [int]($alvo.Size - $lidos))
            if ($n -le 0) { break }
            $lidos += $n
        }
        if ($lidos -ne $alvo.Size) { return $null }
        # ',' pelo mesmo motivo de Read-Exact: sem ele o chamador recebe um
        # Object[] de dezenas de milhoes de elementos para o redistribuivel.
        return ,$buf
    } finally { $fs.Close() }
}

function Test-Gate5UnattendMedia {
    # Validacao fail-closed da midia controlada, ANTES de qualquer power-on.
    # Nunca imprime o conteudo do Autounattend (ele carrega a senha de bootstrap
    # renderizada); apenas confirma propriedades por marcadores.
    param([string]$IsoPath = (Join-Path $script:Gate5VmDir 'gate5-unattend.iso'))
    $r = [ordered]@{
        iso_present = (Test-Path $IsoPath); iso_bytes = 0
        autounattend_na_raiz = $false; payload_na_raiz = $false
        product_key_vazio = $false; product_key_ui_never = $false
        edicao_windows_11_pro = $false; locale_pt_br = $false
        payload_script = $false; yara_bin = $false; ruleset_index = $false
        ruleset_sha40 = $false; ruleset_manifest = $false
        vcredist_x64 = $false; vcredist_sha256 = $false
        sem_chave_real = $false; sem_segredos = $false
        ordem_particionamento_ok = $false
    }
    if (-not $r.iso_present) { return [pscustomobject]$r }
    $r.iso_bytes = (Get-Item $IsoPath).Length

    $raiz = Get-Gate5IsoEntries -IsoPath $IsoPath
    if ($raiz) {
        $r.autounattend_na_raiz = [bool](@($raiz | Where-Object { $_.Name -eq 'Autounattend.xml' -and -not $_.IsDirectory }).Count)
        $r.payload_na_raiz      = [bool](@($raiz | Where-Object { $_.Name -eq 'gate5' -and $_.IsDirectory }).Count)
    }
    # 'Where-Object { $_ }': um diretorio ausente devolve $null, e sob
    # Set-StrictMode filtrar $null por propriedade LANCA em vez de reprovar o
    # controle - uma midia incompleta tem de dar 'false', nunca excecao.
    $g5    = @(Get-Gate5IsoEntries -IsoPath $IsoPath -SubPath 'gate5'       | Where-Object { $_ })
    $yara  = @(Get-Gate5IsoEntries -IsoPath $IsoPath -SubPath 'gate5/yara'  | Where-Object { $_ })
    $rules = @(Get-Gate5IsoEntries -IsoPath $IsoPath -SubPath 'gate5/rules' | Where-Object { $_ })
    # Ordem dos elementos do particionamento CONFERIDA NO ARQUIVO DA MIDIA, nao
    # no template do repositorio: e o que o Windows Setup realmente vai ler. O
    # conteudo nunca e impresso (carrega a senha de bootstrap renderizada).
    $bytesUnattend = Get-Gate5IsoFileBytes -IsoPath $IsoPath -Name 'Autounattend.xml'
    if ($bytesUnattend) {
        try {
            $texto = [Text.Encoding]::UTF8.GetString($bytesUnattend).TrimStart([char]0xFEFF)
            [xml]$xa = $texto
            $nsa = New-Object System.Xml.XmlNamespaceManager($xa.NameTable)
            $nsa.AddNamespace('u', 'urn:schemas-microsoft-com:unattend')
            $disk = $xa.SelectSingleNode('//u:DiskConfiguration/u:Disk', $nsa)
            $dc   = $xa.SelectSingleNode('//u:DiskConfiguration', $nsa)
            if ($disk -and $dc) {
                $od = @($disk.ChildNodes | Where-Object { $_.NodeType -eq 'Element' } | ForEach-Object { $_.LocalName })
                $oc = @($dc.ChildNodes   | Where-Object { $_.NodeType -eq 'Element' } | ForEach-Object { $_.LocalName })
                $r.ordem_particionamento_ok = ((($od -join ',') -eq 'CreatePartitions,ModifyPartitions,DiskID,WillWipeDisk') -and
                                               (($oc -join ',') -eq 'Disk,WillShowUI'))
            }
        } catch { }
    }
    $r.payload_script = [bool](@($g5    | Where-Object { $_.Name -eq 'gate5-payload.ps1' }).Count)
    $r.yara_bin       = [bool](@($yara  | Where-Object { $_.Name -eq 'yara64.exe' }).Count)
    $r.ruleset_index  = [bool](@($rules | Where-Object { $_.Name -eq 'gate5-index.yar' }).Count)

    # Pin do ruleset GRAVADO NA MIDIA. Sem ele o guest so consegue contar
    # arquivos - foi assim que a RUN-01 declarou o ruleset sem prova nenhuma. O
    # que o guest precisa para PROVAR o commit e o SHA-40 estrito mais o
    # manifesto <rel, sha> completo com o agregado esperado.
    $bytesPin = Get-Gate5IsoFileBytes -IsoPath $IsoPath -Name 'rules-pin.json' -SubPath 'gate5'
    if ($bytesPin) {
        try {
            $pin = [Text.Encoding]::UTF8.GetString($bytesPin).TrimStart([char]0xFEFF) | ConvertFrom-Json
            # -cmatch: '-match' e insensivel a maiusculas no PowerShell e
            # deixaria passar um SHA-40 em caixa alta como se fosse o formato
            # estrito exigido. O guest compara o mesmo valor com -cmatch.
            $r.ruleset_sha40 = ([string]$pin.commit_sha40 -cmatch '^[0-9a-f]{40}$')
            $arquivos = @($pin.files)
            $r.ruleset_manifest = (
                ($arquivos.Count -gt 0) -and
                ([string]$pin.aggregate_sha256 -match '^[0-9a-f]{64}$') -and
                ([int]$pin.file_count -eq $arquivos.Count) -and
                (@($arquivos | Where-Object { -not ($_.rel) -or ([string]$_.sha -notmatch '^[0-9a-f]{64}$') }).Count -eq 0)
            )
        } catch {}
    }

    # Redistribuivel oficial do Visual C++: presente E byte-identico ao pin. O
    # hash e recomputado sobre os bytes que estao DENTRO da ISO, nao sobre o
    # arquivo do staging - a midia e o que o guest vai executar.
    $vc = @(Get-Gate5IsoEntries -IsoPath $IsoPath -SubPath 'gate5/vcredist' | Where-Object { $_ })
    $r.vcredist_x64 = [bool](@($vc | Where-Object { $_.Name -eq 'vc_redist.x64.exe' }).Count)
    $bytesVcPin = Get-Gate5IsoFileBytes -IsoPath $IsoPath -Name 'vcruntime-pin.json' -SubPath 'gate5/vcredist'
    if ($r.vcredist_x64 -and $bytesVcPin) {
        try {
            $vcPin = [Text.Encoding]::UTF8.GetString($bytesVcPin).TrimStart([char]0xFEFF) | ConvertFrom-Json
            $esperado = ([string]$vcPin.sha256).ToLowerInvariant()
            if ($esperado -match '^[0-9a-f]{64}$') {
                $bytesVc = Get-Gate5IsoFileBytes -IsoPath $IsoPath -Name 'vc_redist.x64.exe' -SubPath 'gate5/vcredist'
                if ($bytesVc) {
                    $sha = [Security.Cryptography.SHA256]::Create()
                    $obtido = ([BitConverter]::ToString($sha.ComputeHash($bytesVc)) -replace '-', '').ToLowerInvariant()
                    $r.vcredist_sha256 = ($obtido -eq $esperado)
                }
            }
        } catch {}
    }

    $bytes = [System.IO.File]::ReadAllBytes($IsoPath)
    $texto = [Text.Encoding]::UTF8.GetString($bytes)
    $r.product_key_vazio     = ($texto -match '<ProductKey>\s*<Key>\s*</Key>')
    $r.product_key_ui_never  = ($texto -match '<ProductKey>[\s\S]{0,200}?<WillShowUI>Never</WillShowUI>')
    $r.edicao_windows_11_pro = ($texto -match '<Value>Windows 11 Pro</Value>')
    $r.locale_pt_br          = ($texto -match '<UILanguage>pt-BR</UILanguage>')
    # Nenhuma chave de produto real (formato 5x5) em lugar algum da midia.
    $r.sem_chave_real        = -not ($texto -match '[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}')
    # Nenhum material sensivel embarcado. A credencial de BOOTSTRAP do guest
    # esta na midia por desenho (o Setup precisa dela) e nao entra nesta busca -
    # ela e efemera, nunca versionada e nunca impressa. O que nao pode viajar e
    # material de chave, token de servico e material criptografico da VM.
    $marcadores = @(
        '-----BEGIN [A-Z ]*PRIVATE KEY-----',
        'PuTTY-User-Key-File',
        'ghp_[A-Za-z0-9]{20}', 'github_pat_[A-Za-z0-9_]{20}',
        'encryption\.keySafe\s*=', 'encryption\.data\s*=', 'vtpm\.data\s*='
    )
    $r.sem_segredos = -not (@($marcadores | Where-Object { $texto -match $_ }).Count)
    return [pscustomobject]$r
}

function Get-Gate5VmxValue {
    param([Parameter(Mandatory)][string]$Key, [string]$VmxPath)
    if (-not $VmxPath) { $VmxPath = $script:Gate5VmxPath }
    if (-not (Test-Path $VmxPath)) { return $null }
    $line = Select-String -LiteralPath $VmxPath -Pattern ('^{0}\s*=\s*"(.*)"' -f [regex]::Escape($Key)) | Select-Object -First 1
    if ($line) { return $line.Matches[0].Groups[1].Value }
    return $null
}
