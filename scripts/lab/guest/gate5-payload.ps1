# gate5-payload.ps1 - Executado DENTRO do guest FaithRO-GATE5-LAB.
#
# Entregue por midia controlada (a ISO gerada e verificada no host) e disparado
# pelo proprio Windows Setup. Nao existe canal de guest operations: a VM e
# criptografada por exigencia do vTPM e, nesse estado, 'vmrun' so operaria com a
# senha da criptografia, que pertence exclusivamente ao operador (docs/48 §12).
#
# Fluxo (idempotente e retomavel entre reboots do proprio guest):
#   INSTALL  -> instala YARA e o ruleset a partir da midia
#   UPDATE   -> Windows Update ate nao restar atualizacao aplicavel
#   EVIDENCE -> coleta as provas e as escreve na porta serial (arquivo no host)
#
# A porta serial e um canal de SAIDA de mao unica: o guest escreve, o host le.
# Nenhum segredo trafega por ela - apenas metadados de validacao.

$ErrorActionPreference = 'Continue'
$Gate5Dir   = 'C:\gate5'
$StageFile  = Join-Path $Gate5Dir 'stage.txt'
$LogFile    = Join-Path $Gate5Dir 'payload.log'
$TaskName   = 'Gate5Payload'
$SerialPort = 'COM1'

function Write-Log([string]$m) {
    $line = '{0}Z {1}' -f ([DateTime]::UtcNow.ToString('s')), $m
    Write-Host $line
    try { Add-Content -LiteralPath $LogFile -Value $line -Encoding utf8 } catch {}
}

function Send-Serial([string]$Text) {
    # Escreve no serial em blocos: o buffer do dispositivo virtual e pequeno e
    # uma escrita unica muito grande pode ser truncada no arquivo do host.
    try {
        $sp = New-Object System.IO.Ports.SerialPort $SerialPort, 115200, 'None', 8, 'One'
        $sp.WriteTimeout = 10000
        $sp.Open()
        $chunk = 512
        for ($i = 0; $i -lt $Text.Length; $i += $chunk) {
            $sp.Write($Text.Substring($i, [Math]::Min($chunk, $Text.Length - $i)))
            Start-Sleep -Milliseconds 40
        }
        $sp.Write("`r`n")
        Start-Sleep -Milliseconds 300
        $sp.Close()
        return $true
    } catch {
        Write-Log ("SERIAL FALHOU: " + $_.Exception.Message)
        return $false
    }
}

function Send-Heartbeat([string]$Estagio, [string]$Detalhe = '') {
    # Batimento de progresso pela serial. Sem isto o host so recebia sinal no
    # FIM de tudo e nao conseguia distinguir "payload trabalhando" de "payload
    # morto" - foi preciso pericia de tela para saber que o script rodava.
    # Marcador proprio, diferente do bloco de evidencia, para nao confundir o
    # parser fail-closed do host.
    $m = '<<<GATE5-STAGE:' + $Estagio + '|' + ([DateTime]::UtcNow.ToString('s')) + 'Z'
    if ($Detalhe) { $m += '|' + $Detalhe }
    $m += '>>>'
    [void](Send-Serial $m)
    Write-Log ("heartbeat " + $Estagio + " " + $Detalhe)
}

function Get-Stage { if (Test-Path $StageFile) { (Get-Content $StageFile -Raw).Trim() } else { 'INSTALL' } }
function Set-Stage([string]$s) { Set-Content -LiteralPath $StageFile -Value $s -Encoding ascii; Write-Log "stage=$s"; Send-Heartbeat $s }

function Find-PayloadRoot {
    # A midia controlada e reconhecida por um marcador proprio, nunca por letra
    # de unidade fixa (a atribuicao varia entre boots).
    foreach ($v in (Get-Volume -ErrorAction SilentlyContinue | Where-Object { $_.DriveLetter })) {
        $p = '{0}:\gate5' -f $v.DriveLetter
        if (Test-Path (Join-Path $p 'payload-marker.txt')) { return $p }
    }
    return $null
}

function Register-StartupTask {
    # Reexecuta o payload apos cada reboot do guest ate a etapa EVIDENCE concluir.
    try {
        $action  = New-ScheduledTaskAction -Execute 'powershell.exe' `
                    -Argument ('-NoProfile -ExecutionPolicy Bypass -File "{0}\gate5-payload.ps1"' -f $Gate5Dir)
        $trigger = New-ScheduledTaskTrigger -AtStartup
        $princ   = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -RunLevel Highest
        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $princ -Force | Out-Null
        Write-Log 'tarefa de retomada registrada'
    } catch { Write-Log ("registro da tarefa falhou: " + $_.Exception.Message) }
}

function Unregister-StartupTask {
    try { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue } catch {}
}

New-Item -ItemType Directory -Force $Gate5Dir | Out-Null
Write-Log '=== payload GATE 5 iniciado ==='
# Primeiro sinal de vida: prova ao host que FirstLogonCommands disparou e que o
# script esta executando, antes de qualquer etapa demorada.
Send-Heartbeat 'PAYLOAD_STARTED' ("stage=" + (Get-Stage))

# ---------------------------------------------------------------- INSTALL ----
if ((Get-Stage) -eq 'INSTALL') {
    $root = Find-PayloadRoot
    if (-not $root) { Write-Log 'PAYLOAD NAO ENCONTRADO na midia'; Send-Serial '{"gate5_error":"payload_media_not_found"}' | Out-Null; exit 1 }
    Write-Log "payload encontrado em $root"

    # Copia o proprio script para o disco: a midia e desconectada no isolamento.
    Copy-Item (Join-Path $root 'gate5-payload.ps1') (Join-Path $Gate5Dir 'gate5-payload.ps1') -Force
    New-Item -ItemType Directory -Force 'C:\Tools\YARA' | Out-Null
    Copy-Item (Join-Path $root 'yara\*') 'C:\Tools\YARA\' -Force
    New-Item -ItemType Directory -Force 'C:\Tools\YARA-Rules' | Out-Null
    Copy-Item (Join-Path $root 'rules\*') 'C:\Tools\YARA-Rules\' -Recurse -Force
    Write-Log 'YARA e ruleset instalados a partir da midia'

    Register-StartupTask
    Set-Stage 'UPDATE'
}

# ----------------------------------------------------------------- UPDATE ----
if ((Get-Stage) -eq 'UPDATE') {
    try {
        $session  = New-Object -ComObject Microsoft.Update.Session
        $searcher = $session.CreateUpdateSearcher()
        $result   = $searcher.Search("IsInstalled=0 and IsHidden=0 and Type='Software'")
        Write-Log ("Windows Update: encontradas=" + $result.Updates.Count)
        Send-Heartbeat 'UPDATE_SEARCH_DONE' ("encontradas=" + $result.Updates.Count)
        if ($result.Updates.Count -gt 0) {
            $coll = New-Object -ComObject Microsoft.Update.UpdateColl
            foreach ($u in $result.Updates) { if (-not $u.EulaAccepted) { $u.AcceptEula() }; $coll.Add($u) | Out-Null }
            $dl = $session.CreateUpdateDownloader(); $dl.Updates = $coll; $dl.Download() | Out-Null
            $inst = $session.CreateUpdateInstaller(); $inst.Updates = $coll
            $ir = $inst.Install()
            Write-Log ("Windows Update: instaladas=" + $coll.Count + " reboot=" + $ir.RebootRequired)
            Send-Heartbeat 'UPDATE_INSTALLED' ("instaladas=" + $coll.Count + ";reboot=" + $ir.RebootRequired)
            if ($ir.RebootRequired) { Write-Log 'reiniciando o guest para concluir as atualizacoes'; Restart-Computer -Force; exit 0 }
            # Ainda pode haver updates encadeados: repete no proximo ciclo.
            Restart-Computer -Force
            exit 0
        }
        Write-Log 'Windows Update: nenhuma atualizacao aplicavel restante'
        Set-Stage 'EVIDENCE'
    } catch {
        Write-Log ("Windows Update falhou: " + $_.Exception.Message)
        Set-Stage 'EVIDENCE'   # segue para a coleta; o host decide pelo conteudo
    }
}

# --------------------------------------------------------------- EVIDENCE ----
if ((Get-Stage) -eq 'EVIDENCE') {
    Write-Log 'coletando evidencias'

    $os  = Get-CimInstance Win32_OperatingSystem
    $cs  = Get-CimInstance Win32_ComputerSystem
    $sb  = $false; try { $sb = Confirm-SecureBootUEFI } catch {}
    $tpm = $null;  try { $tpm = Get-Tpm } catch {}
    $mp  = $null;  try { $mp = Get-MpComputerStatus } catch {}

    $mpCmd = $null
    try {
        $plat = Get-ChildItem "$env:ProgramData\Microsoft\Windows Defender\Platform" -Directory -ErrorAction Stop |
                Sort-Object Name -Descending | Select-Object -First 1
        $mpCmd = Join-Path $plat.FullName 'MpCmdRun.exe'
    } catch {}
    if (-not $mpCmd -or -not (Test-Path $mpCmd)) { $mpCmd = "$env:ProgramFiles\Windows Defender\MpCmdRun.exe" }

    $yaraVer = ''
    try { $yaraVer = (& 'C:\Tools\YARA\yara64.exe' --version 2>&1 | Out-String).Trim() } catch {}
    $rulesOk = $false
    try {
        # Compila o indice DENTRO do guest: prova que o ruleset entregue esta
        # integro e utilizavel ali, nao apenas que os arquivos existem.
        & 'C:\Tools\YARA\yarac64.exe' 'C:\Tools\YARA-Rules\gate5-index.yar' "$env:TEMP\gate5-guest.yrc" 2>&1 | Out-Null
        $rulesOk = ($LASTEXITCODE -eq 0)
        Remove-Item "$env:TEMP\gate5-guest.yrc" -Force -ErrorAction SilentlyContinue
    } catch {}
    $rulesCount = @(Get-ChildItem 'C:\Tools\YARA-Rules' -Recurse -File -Include '*.yar', '*.yara' -ErrorAction SilentlyContinue).Count

    # Varredura de secrets: padroes DECISORIOS (acerto reprova) separados dos
    # INFORMATIVOS (substrings genericas que o proprio Windows usa).
    $gating = @('*.pem', '*.ppk', 'id_rsa*', 'id_ed25519*', '*.sql', '*.dump', '.env', '.env.*',
                '*faithro*', 'Ragexe*', '*.grf', 'WARP*', '*.gat', '*.rsw')
    $info   = @('*credential*', '*token*', '*github*')
    $roots  = @('C:\Users', 'C:\gate5', 'C:\Tools', 'C:\Temp', 'C:\Windows\Temp')
    function Find-Hits([string[]]$Pats) {
        $acc = @()
        foreach ($r in $roots) {
            if (Test-Path $r) {
                foreach ($p in $Pats) {
                    $acc += Get-ChildItem $r -Recurse -Force -Filter $p -ErrorAction SilentlyContinue |
                            Where-Object { -not $_.PSIsContainer } | Select-Object -ExpandProperty FullName
                }
            }
        }
        return @($acc | Sort-Object -Unique)
    }
    $benign = '\\Tools\\YARA'
    $hits = @(Find-Hits $gating | Where-Object { $_ -notmatch $benign })
    $infoHits = @(Find-Hits $info | Where-Object { $_ -notmatch $benign })
    $warp = @(Get-ChildItem 'C:\' -Recurse -Depth 3 -Filter 'WARP*' -ErrorAction SilentlyContinue).Count

    $ev = [ordered]@{
        schema            = 'gate5-guest-evidence/v1'
        timestamp_utc     = [DateTime]::UtcNow.ToString('s') + 'Z'
        os_caption        = $os.Caption
        os_version        = $os.Version
        os_build          = $os.BuildNumber
        os_arch           = $os.OSArchitecture
        os_locale         = (Get-Culture).Name
        computer_name     = $cs.Name
        secure_boot       = [bool]$sb
        tpm_present       = [bool]($tpm -and $tpm.TpmPresent)
        tpm_ready         = [bool]($tpm -and $tpm.TpmReady)
        defender_av       = [bool]($mp -and $mp.AntivirusEnabled)
        defender_rt       = [bool]($mp -and $mp.RealTimeProtectionEnabled)
        defender_platform = if ($mp) { $mp.AMProductVersion } else { $null }
        defender_engine   = if ($mp) { $mp.AMEngineVersion } else { $null }
        defender_sigs     = if ($mp) { $mp.AntivirusSignatureVersion } else { $null }
        mpcmdrun_path     = $mpCmd
        mpcmdrun_sha256   = if (Test-Path $mpCmd) { (Get-FileHash $mpCmd -Algorithm SHA256).Hash.ToLowerInvariant() } else { $null }
        yara_version      = $yaraVer
        yara_sha256       = if (Test-Path 'C:\Tools\YARA\yara64.exe') { (Get-FileHash 'C:\Tools\YARA\yara64.exe' -Algorithm SHA256).Hash.ToLowerInvariant() } else { $null }
        rules_compile_ok  = $rulesOk
        rules_file_count  = $rulesCount
        nics_up           = @(Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq 'Up' }).Count
        warp_artifacts    = $warp
        secrets_gating    = @($hits)
        secrets_gating_count = @($hits).Count
        secrets_info_count   = @($infoHits).Count
    }

    # Limpeza de bootstrap antes de fechar (o snapshot vem depois).
    Remove-Item 'C:\gate5\*.json' -Force -ErrorAction SilentlyContinue
    try { Clear-RecycleBin -Force -ErrorAction SilentlyContinue } catch {}
    Remove-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name DefaultPassword -ErrorAction SilentlyContinue
    Remove-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name AutoAdminLogon  -ErrorAction SilentlyContinue

    $json = ($ev | ConvertTo-Json -Depth 5 -Compress)
    $payload = "<<<GATE5-EVIDENCE-BEGIN>>>" + $json + "<<<GATE5-EVIDENCE-END>>>"
    $ok = Send-Serial $payload
    Set-Content -LiteralPath (Join-Path $Gate5Dir 'evidence.json') -Value $json -Encoding utf8
    Write-Log ("evidencia enviada pela serial: " + $ok)

    Set-Stage 'DONE'
    Unregister-StartupTask
    Write-Log '=== payload GATE 5 concluido ==='
}
