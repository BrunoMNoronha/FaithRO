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
# neste arquivo. Substitui as guest operations do vmrun, indisponiveis em VM
# criptografada (docs/48 §12). Trafega apenas metadados de validacao.
$script:Gate5EvidenceSerial = Join-Path $script:Gate5VmDir 'gate5-evidence-serial.txt'

$script:Gate5StagingDirs = @('C:\Users\bruno\Downloads', 'C:\Installers', 'C:\ISO', 'C:\VMs', 'C:\Tools')
$script:Gate5YaraDir    = 'C:\Tools\YARA'
$script:Gate5RulesDir   = 'C:\Tools\YARA-Rules'
$script:Gate5YaraVersion = '4.5.5'

# Ordem canonica das fases (checkpoints). A retomada percorre esta lista.
$script:Gate5Phases = @(
    'HOST_PREFLIGHT_OK',
    'VMWARE_INSTALLED',
    'ISO_VALIDATED',
    'VM_CREATED',
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
    if ($script:Gate5LogFile) { Add-Content -Path $script:Gate5LogFile -Value $line -Encoding utf8 }
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
    param([Parameter(Mandatory)]$State, [Parameter(Mandatory)][string]$Phase)
    if (-not (Test-Gate5Phase -State $State -Phase $Phase)) {
        $State.completed = @($State.completed) + $Phase
        Save-Gate5State -State $State
        Write-Gate5Log "CHECKPOINT alcancado: $Phase"
    }
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

function Get-Gate5SerialEvidence {
    # Le a evidencia que o guest escreveu na porta serial. Retorna $null enquanto
    # o bloco completo (com marcadores de inicio e fim) nao tiver chegado.
    param([string]$Path = $script:Gate5EvidenceSerial)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try {
        $fs = [System.IO.File]::Open($Path, 'Open', 'Read', 'ReadWrite')
        try { $texto = (New-Object System.IO.StreamReader($fs)).ReadToEnd() } finally { $fs.Close() }
    } catch { return $null }
    $m = [regex]::Match($texto, '<<<GATE5-EVIDENCE-BEGIN>>>(?<j>.*?)<<<GATE5-EVIDENCE-END>>>', 'Singleline')
    if (-not $m.Success) { return $null }
    try { return ($m.Groups['j'].Value -replace '[\r\n]', '') | ConvertFrom-Json } catch { return $null }
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
            Start-Sleep -Milliseconds 60
        }
        return 'OK'
    } catch {
        return ('erro: ' + $_.Exception.Message)
    } finally {
        $client.Close()
    }
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
        Start-Sleep -Milliseconds 300
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
            return $buf
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

function Get-Gate5VmxValue {
    param([Parameter(Mandatory)][string]$Key, [string]$VmxPath)
    if (-not $VmxPath) { $VmxPath = $script:Gate5VmxPath }
    if (-not (Test-Path $VmxPath)) { return $null }
    $line = Select-String -LiteralPath $VmxPath -Pattern ('^{0}\s*=\s*"(.*)"' -f [regex]::Escape($Key)) | Select-Object -First 1
    if ($line) { return $line.Matches[0].Groups[1].Value }
    return $null
}
