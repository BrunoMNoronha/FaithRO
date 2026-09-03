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
    # Exige o dispositivo materializado. 'managedvm.autoAddVTPM' e apenas um
    # pedido de auto-adicao e nao prova que existe um TPM na VM.
    Check 'vtpm-vmx' ((Get-Gate5VmxValue 'vtpm.present') -eq 'TRUE')
    Check 'nic-startconnected-false' ((Get-Gate5VmxValue 'ethernet0.startConnected') -eq 'FALSE')
    $nicConn = Get-Gate5VmxValue 'ethernet0.connected'
    Check 'nic-disconnected' ($nicConn -eq 'FALSE' -or ((Get-Gate5VmxValue 'ethernet0.startConnected') -eq 'FALSE' -and $null -eq $nicConn))
    Check 'clipboard-off' ((Get-Gate5VmxValue 'isolation.tools.copy.disable') -eq 'TRUE' -and (Get-Gate5VmxValue 'isolation.tools.paste.disable') -eq 'TRUE')
    Check 'dnd-off'  ((Get-Gate5VmxValue 'isolation.tools.dnd.disable') -eq 'TRUE')
    Check 'hgfs-off' ((Get-Gate5VmxValue 'isolation.tools.hgfs.disable') -eq 'TRUE')
    Check 'usb-off'  ((Get-Gate5VmxValue 'usb.present') -ne 'TRUE')
    # O console VNC e um canal de administracao LOCAL e TEMPORARIO da instalacao;
    # nao pode sobreviver ao baseline. Em VM criptografada a chave e desligada em
    # vez de removida (o .vmx nao pode ser reescrito), entao vale ausente OU FALSE.
    $vncCfg = Get-Gate5VmxValue 'RemoteDisplay.vnc.enabled'
    Check 'console-vnc-desligado' ($null -eq $vncCfg -or $vncCfg -eq 'FALSE') "valor=$vncCfg"
    # Prova independente do .vmx: nenhum listener na porta temporaria do host.
    $vncListen = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
                   Where-Object { $_.LocalPort -eq $script:Gate5VncPort })
    Check 'console-vnc-sem-listener' ($vncListen.Count -eq 0) ("porta=" + $script:Gate5VncPort)
    # Override de instalacao nao pode sobreviver ao baseline: a VM final depende
    # da ordem normal registrada pelo UEFI/Windows Boot Manager.
    Check 'sem-override-de-boot' (($null -eq (Get-Gate5VmxValue 'bios.bootOrder')) -and ($null -eq (Get-Gate5VmxValue 'efi.bootOrder')))
    $vmdk = Join-Path $script:Gate5VmDir 'FaithRO-GATE5-LAB.vmdk'
    Check 'disk-70gb-existe' (Test-Path $vmdk)
}

# --- Snapshot -----------------------------------------------------------------
if (Test-Path $script:Gate5VmxPath) {
    Check 'snapshot-baseline' (Test-Gate5SnapshotExists -SnapshotName $script:Gate5SnapshotName -VmxPath $script:Gate5VmxPath -Vmware $vmware)
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
    if ((Get-Gate5VmEncryptionState).Encrypted) {
        # Em VM criptografada nao ha guest operations (docs/48 §12).
        # A prova primaria e o testemunho reportado pelo guest pela serial (ver § abaixo).
    } else {
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
}

# --- Evidencia reportada pelo proprio guest pela serial -----------------------
# Esta e a prova primaria do baseline: numa VM criptografada nao ha guest
# operations, entao o que o guest escreveu na serial e o unico testemunho de
# dentro. Os controles abaixo foram os que reprovaram na primeira instalacao
# limpa e passaram a ter verificacao explicita.
# O baseline e sempre o da execucao CORRENTE: a evidencia de uma execucao
# anterior fica preservada no diretorio dela e nunca aprova a atual.
$serialEv = Join-Path (Join-Path $script:Gate5EvidenceDir (Get-Gate5RunId)) 'guest-evidence.json'
Check 'evidencia-guest-serial' (Test-Path $serialEv)
# 'guest-evidence.json' e um artefato DERIVADO. O testemunho BRUTO sao os sinks
# seriais preservados em <run-dir>\serial, um por power-on. Exigir os dois
# impede que uma evidencia derivada aprove um baseline cujo original sumiu -
# que e exatamente o estado em que a RUN-02 terminou (docs/48 §16).
$sinksSeriais = @(Get-Gate5SerialSinks)
Check 'sinks-seriais-preservados' ($sinksSeriais.Count -gt 0) ("sinks=" + $sinksSeriais.Count)
if (Test-Path $serialEv) {
    $g = Get-Content $serialEv -Raw | ConvertFrom-Json
    $campos = @($g.PSObject.Properties.Name)
    Check 'guest-sem-blockers' ((-not ($campos -contains 'blockers')) -or (@($g.blockers).Count -eq 0)) ("blockers=" + (@($g.blockers) -join ','))
    Check 'guest-tpm-2.0' ([bool]($campos -contains 'tpm_2_0' -and $g.tpm_2_0)) ("spec=" + $g.tpm_spec_version)
    Check 'guest-vcruntime' ([bool]($campos -contains 'vcruntime_sufficient' -and $g.vcruntime_sufficient)) ("versao=" + $g.vcruntime_version)
    Check 'guest-yara-runtime' ([bool]($campos -contains 'yara_runtime_ok' -and $g.yara_runtime_ok)) ("yara=" + $g.yara_version)
    Check 'guest-ruleset-pinned' ([bool]($campos -contains 'ruleset_pinned' -and $g.ruleset_pinned)) ("commit=" + $g.ruleset_commit)
    Check 'guest-ruleset-compila' ([bool]$g.rules_compile_ok)
    Check 'guest-sanitize' ([bool]($campos -contains 'sanitize_pass' -and $g.sanitize_pass)) ("gating=" + $g.secrets_gating_count + " vendor=" + $g.secrets_vendor_count)
}

# --- Secrets gate (evidencia da sanitizacao) ----------------------------------
# Aceita as DUAS origens de prova: o arquivo da fase Sanitize por guest
# operations (so existe em VM nao criptografada) ou a varredura que o proprio
# payload faz e reporta pela serial. Exigir apenas a primeira reprovaria sempre
# no desenho atual, em que a VM e criptografada por causa do vTPM.
$sanEv = Join-Path $script:Gate5EvidenceDir 'guest-sanitize.json'
$sanLegado = (Test-Path $sanEv) -and ((Get-Content $sanEv -Raw | ConvertFrom-Json).count -eq 0)
$sanSerial = (Test-Path $serialEv) -and [bool](Get-Content $serialEv -Raw | ConvertFrom-Json).sanitize_pass
Check 'secrets-gate' ($sanLegado -or $sanSerial)

# --- Resultado ----------------------------------------------------------------
if ($failures.Count -gt 0) {
    Write-Gate5Log ("VERIFY-BASELINE FAIL: {0} controles reprovados: {1}" -f $failures.Count, ($failures -join ', ')) 'FAIL'
    exit 1
}
Write-Gate5Log 'VERIFY-BASELINE PASS: todos os controles satisfeitos.'
Write-Host 'LAB_BASELINE_READY=true'
exit 0
