# gate5-verify-baseline.ps1 - Validador final do laboratorio FaithRO-GATE5-LAB.
# Exit 0 SOMENTE quando TODOS os controles estiverem satisfeitos (fail-closed).
# Liga a VM isolada, coleta provas dentro do guest, desliga a VM.
# NUNCA reconecta a rede. NUNCA materializa o alvo WARP.

[CmdletBinding()]
param([switch]$SkipPowerCycle)  # para reexecucao com a VM ja ligada

. (Join-Path $PSScriptRoot 'gate5-common.ps1')
if (-not (Get-Variable -Name Gate5LogFile -Scope Script -ErrorAction SilentlyContinue)) { Initialize-Gate5Log }

$failures = @()
function Check([string]$Name, [bool]$Ok, [string]$Detail = '') {
    $status = if ($Ok) { 'PASS' } else { 'FAIL' }
    Write-Gate5Log ("VERIFY {0}: {1} {2}" -f $status, $Name, $Detail)
    if (-not $Ok) { $script:failures += $Name }
}

# --- Controles verificaveis no host ------------------------------------------
$vmware = Find-Gate5VmwareInstall
Check 'vmware-instalado' ($null -ne $vmware)
if ($vmware) { Check 'vmware-26h1' ($vmware.DisplayVersion -match '^26\.') "versao=$($vmware.DisplayVersion)" }
Check 'vm-existe' (Test-Path $script:Gate5VmxPath) $script:Gate5VmxPath

if (Test-Path $script:Gate5VmxPath) {
    Check 'guest-windows11-x64' ((Get-Gate5VmxValue 'guestOS') -eq 'windows11-64')
    Check 'vcpu-2'   ((Get-Gate5VmxValue 'numvcpus') -eq '2')
    Check 'ram-4096' ((Get-Gate5VmxValue 'memsize') -eq '4096')
    Check 'uefi'     ((Get-Gate5VmxValue 'firmware') -eq 'efi')
    Check 'secureboot-vmx' ((Get-Gate5VmxValue 'uefi.secureBoot.enabled') -eq 'TRUE')
    $vtpmCfg = (Get-Gate5VmxValue 'managedvm.autoAddVTPM') -eq 'software' -or (Get-Gate5VmxValue 'vtpm.present') -eq 'TRUE'
    Check 'vtpm-vmx' $vtpmCfg
    Check 'nic-startconnected-false' ((Get-Gate5VmxValue 'ethernet0.startConnected') -eq 'FALSE')
    $nicConn = Get-Gate5VmxValue 'ethernet0.connected'
    Check 'nic-disconnected' ($nicConn -eq 'FALSE' -or ((Get-Gate5VmxValue 'ethernet0.startConnected') -eq 'FALSE' -and $null -eq $nicConn))
    Check 'clipboard-off' ((Get-Gate5VmxValue 'isolation.tools.copy.disable') -eq 'TRUE' -and (Get-Gate5VmxValue 'isolation.tools.paste.disable') -eq 'TRUE')
    Check 'dnd-off'  ((Get-Gate5VmxValue 'isolation.tools.dnd.disable') -eq 'TRUE')
    Check 'hgfs-off' ((Get-Gate5VmxValue 'isolation.tools.hgfs.disable') -eq 'TRUE')
    Check 'usb-off'  ((Get-Gate5VmxValue 'usb.present') -ne 'TRUE')
    $vmdk = Join-Path $script:Gate5VmDir 'FaithRO-GATE5-LAB.vmdk'
    Check 'disk-60gb-existe' (Test-Path $vmdk)
}

# --- Snapshot -----------------------------------------------------------------
if ($vmware -and (Test-Path $script:Gate5VmxPath)) {
    $snaps = (Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('listSnapshots', $script:Gate5VmxPath) -AllowFailure).Output
    Check 'snapshot-baseline' ($snaps -match [regex]::Escape($script:Gate5SnapshotName))
}

# --- Evidencias de tooling (host-side, geradas pelo bootstrap) ----------------
$yaraEv    = Join-Path $script:Gate5EvidenceDir 'yara.json'
$rulesEv   = Join-Path $script:Gate5EvidenceDir 'ruleset.json'
$defEv     = Join-Path $script:Gate5EvidenceDir 'guest-defender.json'
Check 'evidencia-yara' (Test-Path $yaraEv)
Check 'evidencia-ruleset' (Test-Path $rulesEv)
Check 'evidencia-defender' (Test-Path $defEv)
if (Test-Path $yaraEv)  { $y = Get-Content $yaraEv -Raw | ConvertFrom-Json;  Check 'yara-4.5.5' ($y.version -eq '4.5.5') }
if (Test-Path $rulesEv) {
    $r = Get-Content $rulesEv -Raw | ConvertFrom-Json
    Check 'ruleset-sha40' ($r.commit_sha40 -match '^[0-9a-f]{40}$') $r.commit_sha40
    Check 'ruleset-aggregate' ($r.aggregate_sha256 -match '^[0-9a-f]{64}$')
    Check 'ruleset-files' ($r.file_count -gt 0) "file_count=$($r.file_count)"
}
if (Test-Path $defEv)   { $d = Get-Content $defEv -Raw | ConvertFrom-Json; Check 'defender-enabled' ([bool]$d.antivirus_enabled -and [bool]$d.realtime_enabled) }

# --- Prova dentro do guest (VM isolada; power-on -> coleta -> power-off) ------
$guestProof = $null
# A prova no guest roda mesmo com falhas ja registradas no host: interromper
# aqui esconderia o estado real do guest justamente no relatorio de diagnostico.
if ($vmware -and (Test-Path $script:Gate5VmxPath)) {
    $credFile = Join-Path $script:Gate5SecretDir 'guest-credential.xml'
    if (-not (Test-Path $credFile)) {
        Check 'guest-proof' $false 'credencial de verificacao ausente (esperada em .local; nunca versionada)'
    } else {
        $cred  = Import-Clixml $credFile
        $plain = $cred.GetNetworkCredential().Password
        $wasRunning = ((Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('list') -AllowFailure).Output -match [regex]::Escape($script:Gate5VmxPath))
        if (-not $wasRunning -and -not $SkipPowerCycle) {
            Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('start', $script:Gate5VmxPath, 'nogui') | Out-Null
            Start-Sleep -Seconds 90
        }
        $proofScript = Join-Path $script:Gate5LocalDir 'gate5-proof.ps1'
        Set-Content -Path $proofScript -Encoding utf8 -Value @'
$tpm = Get-Tpm
$sb  = $false; try { $sb = Confirm-SecureBootUEFI } catch {}
$mp  = Get-MpComputerStatus
$yv  = ""; try { $yv = (& C:\Tools\YARA\yara64.exe --version).Trim() } catch {}
$nic = @(Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object Status -eq "Up").Count
$warp = @(Get-ChildItem C:\ -Recurse -Depth 3 -Filter "WARP*" -ErrorAction SilentlyContinue).Count
@{
    secure_boot = [bool]$sb
    tpm_present = [bool]$tpm.TpmPresent
    tpm_ready   = [bool]$tpm.TpmReady
    defender_av = [bool]$mp.AntivirusEnabled
    defender_rt = [bool]$mp.RealTimeProtectionEnabled
    yara_version = $yv
    rules_index  = (Test-Path C:\Tools\YARA-Rules\gate5-index.yar)
    nics_up      = $nic
    warp_artifacts = $warp
    os_arch      = $env:PROCESSOR_ARCHITECTURE
} | ConvertTo-Json | Out-File C:\Users\Public\gate5-proof.json -Encoding utf8
'@
        Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('-gu', $cred.UserName, '-gp', $plain, 'CopyFileFromHostToGuest', $script:Gate5VmxPath, $proofScript, 'C:\Users\Public\gate5-proof.ps1') | Out-Null
        Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('-gu', $cred.UserName, '-gp', $plain, 'runProgramInGuest', $script:Gate5VmxPath, 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', 'C:\Users\Public\gate5-proof.ps1') -AllowFailure | Out-Null
        $proofOut = Join-Path $script:Gate5EvidenceDir 'guest-baseline-proof.json'
        Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('-gu', $cred.UserName, '-gp', $plain, 'CopyFileFromGuestToHost', $script:Gate5VmxPath, 'C:\Users\Public\gate5-proof.json', $proofOut) | Out-Null
        Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('-gu', $cred.UserName, '-gp', $plain, 'runProgramInGuest', $script:Gate5VmxPath, 'C:\Windows\System32\cmd.exe', '/c', 'del /f C:\Users\Public\gate5-proof.ps1 C:\Users\Public\gate5-proof.json') -AllowFailure | Out-Null
        Remove-Item $proofScript -Force -ErrorAction SilentlyContinue
        $guestProof = Get-Content $proofOut -Raw | ConvertFrom-Json
        Check 'guest-secureboot' ([bool]$guestProof.secure_boot)
        Check 'guest-tpm-present' ([bool]$guestProof.tpm_present)
        Check 'guest-tpm-ready' ([bool]$guestProof.tpm_ready)
        Check 'guest-defender' ([bool]$guestProof.defender_av -and [bool]$guestProof.defender_rt)
        Check 'guest-yara-4.5.5' ($guestProof.yara_version -eq '4.5.5')
        Check 'guest-rules-index' ([bool]$guestProof.rules_index)
        Check 'guest-nic-down' ($guestProof.nics_up -eq 0) "nics_up=$($guestProof.nics_up)"
        Check 'guest-target-absent' ($guestProof.warp_artifacts -eq 0) "warp_artifacts=$($guestProof.warp_artifacts)"
        Check 'guest-x64' ($guestProof.os_arch -eq 'AMD64')
        if (-not $wasRunning -and -not $SkipPowerCycle) {
            Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('stop', $script:Gate5VmxPath, 'soft') -AllowFailure | Out-Null
        }
    }
}

# --- Secrets gate (evidencia da sanitizacao) ----------------------------------
$sanEv = Join-Path $script:Gate5EvidenceDir 'guest-sanitize.json'
Check 'secrets-gate' ((Test-Path $sanEv) -and ((Get-Content $sanEv -Raw | ConvertFrom-Json).count -eq 0))

# --- Resultado ----------------------------------------------------------------
if ($failures.Count -gt 0) {
    Write-Gate5Log ("VERIFY-BASELINE FAIL: {0} controles reprovados: {1}" -f $failures.Count, ($failures -join ', ')) 'FAIL'
    exit 1
}
Write-Gate5Log 'VERIFY-BASELINE PASS: todos os controles satisfeitos.'
Write-Host 'LAB_BASELINE_READY=true'
exit 0
