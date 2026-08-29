# gate5-common.ps1 - Funcoes compartilhadas da automacao do laboratorio GATE 5.
# Dot-source este arquivo. Nao executa nada sozinho. Fail-closed por padrao.
#
# Regras invioladas por esta automacao (ETAPA 2P-E-C5-LAB-AUTOPROVISION):
#   target_materialized=false / artifact_executed=false / vps_accessed=false
#   Nenhum contato com o alvo WARP, com a VPS ou com servicos de reputacao externa.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- Caminhos canonicos -------------------------------------------------------
$script:Gate5RepoRoot   = (git -C (Split-Path -Parent $PSScriptRoot) rev-parse --show-toplevel 2>$null)
if (-not $script:Gate5RepoRoot) { throw 'GATE5: repositorio Git nao localizado a partir de scripts/lab.' }
$script:Gate5RepoRoot   = $script:Gate5RepoRoot -replace '/', '\'
$script:Gate5LocalDir   = Join-Path $script:Gate5RepoRoot '.local\gate5-lab'
$script:Gate5LogDir     = Join-Path $script:Gate5LocalDir 'logs'
$script:Gate5SecretDir  = Join-Path $script:Gate5LocalDir 'secrets'
$script:Gate5StateFile  = Join-Path $script:Gate5LocalDir 'state.json'
$script:Gate5EvidenceDir= Join-Path $script:Gate5LocalDir 'evidence'

$script:Gate5VmName     = 'FaithRO-GATE5-LAB'
$script:Gate5VmDir      = 'C:\VMs\FaithRO-GATE5-LAB'
$script:Gate5VmxPath    = Join-Path $script:Gate5VmDir 'FaithRO-GATE5-LAB.vmx'
$script:Gate5SnapshotName = 'BASELINE_GATE5_ISOLATED'

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
    $stamp = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')
    $script:Gate5LogFile = Join-Path $script:Gate5LogDir "provision-$stamp.log"
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

function Test-Gate5Elevated {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    return ([Security.Principal.WindowsPrincipal]$id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
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
    $printable = ($Arguments | ForEach-Object { if ($_ -match '^-g[up]$') { '<redacted-flag>' } else { $_ } }) -join ' '
    Write-Gate5Log "vmrun $printable"
    $out = & $Vmware.VmrunExe -T ws @Arguments 2>&1
    $code = $LASTEXITCODE
    if ($code -ne 0 -and -not $AllowFailure) {
        Write-Gate5Log "vmrun exit=$code saida=$out" 'ERROR'
        throw "GATE5: vmrun falhou (exit $code): $out"
    }
    return [pscustomobject]@{ ExitCode = $code; Output = $out }
}

function Get-Gate5VmxValue {
    param([Parameter(Mandatory)][string]$Key)
    if (-not (Test-Path $script:Gate5VmxPath)) { return $null }
    $line = Select-String -LiteralPath $script:Gate5VmxPath -Pattern ('^{0}\s*=\s*"(.*)"' -f [regex]::Escape($Key)) | Select-Object -First 1
    if ($line) { return $line.Matches[0].Groups[1].Value }
    return $null
}
