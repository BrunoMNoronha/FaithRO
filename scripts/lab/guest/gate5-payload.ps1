# gate5-payload.ps1 - Executado DENTRO do guest FaithRO-GATE5-LAB.
#
# Entregue por midia controlada (a ISO gerada e verificada no host) e disparado
# pelo proprio Windows Setup. Nao existe canal de guest operations: a VM e
# criptografada por exigencia do vTPM e, nesse estado, 'vmrun' so operaria com a
# senha da criptografia, que pertence exclusivamente ao operador (docs/48 SS12).
#
# Fluxo (idempotente e retomavel entre reboots do proprio guest):
#   INSTALL  -> instala o runtime do Visual C++, o YARA e o ruleset da midia
#   UPDATE   -> Windows Update ate nao restar atualizacao aplicavel
#   EVIDENCE -> coleta as provas e as escreve na porta serial (arquivo no host)
#
# A porta serial e um canal de SAIDA de mao unica: o guest escreve, o host le.
# Nenhum segredo trafega por ela - apenas metadados de validacao.

$ErrorActionPreference = 'Continue'
$Gate5Dir   = 'C:\gate5'
$StageFile  = Join-Path $Gate5Dir 'stage.txt'
$LogFile    = Join-Path $Gate5Dir 'payload.log'
$RuntimeFile= Join-Path $Gate5Dir 'runtime.json'
$BlockerFile= Join-Path $Gate5Dir 'blockers.json'
$RulesPin   = Join-Path $Gate5Dir 'rules-pin.json'
$YaraDir    = 'C:\Tools\YARA'
$RulesDir   = 'C:\Tools\YARA-Rules'
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

function Get-Blockers {
    # Bloqueadores sobrevivem aos reboots do guest: o host precisa recebe-los
    # junto com a evidencia mesmo que a falha tenha ocorrido ciclos antes.
    if (Test-Path $BlockerFile) {
        try { return @((Get-Content $BlockerFile -Raw | ConvertFrom-Json)) } catch { return @() }
    }
    return @()
}

function Add-Blocker([string]$Code, [string]$Detalhe = '') {
    $atuais = @(Get-Blockers)
    if ($atuais -notcontains $Code) { $atuais = @($atuais) + $Code }
    try { ConvertTo-Json @($atuais) -Compress | Set-Content -LiteralPath $BlockerFile -Encoding ascii } catch {}
    Write-Log ("BLOCKER " + $Code + " " + $Detalhe)
    Send-Heartbeat 'BLOCKED' $Code
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

# --- Runtime do Visual C++ ----------------------------------------------------
# Os binarios oficiais do YARA importam VCRUNTIME140.dll, que NAO existe num
# Windows 11 limpo. Sem ela o processo nem inicia. O runtime vem do
# REDISTRIBUIVEL OFICIAL assinado, embarcado na midia; copiar a DLL solta do
# host ("app-local") esta proibido por decisao arquitetural (docs/48 SS13).

function Get-VcRuntimeState {
    param([Version]$Minimo)
    $chave = 'HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64'
    $instalado = $false
    $versao    = ''
    try {
        $p = Get-ItemProperty -LiteralPath $chave -ErrorAction Stop
        $instalado = ([int]$p.Installed -eq 1)
        $versao    = ('{0}.{1}.{2}' -f [int]$p.Major, [int]$p.Minor, [int]$p.Bld)
    } catch {}
    $dll = Join-Path $env:SystemRoot 'System32\VCRUNTIME140.dll'
    $dllPresente = Test-Path -LiteralPath $dll
    $dllVersao   = ''
    if ($dllPresente) { $dllVersao = [string](Get-Item -LiteralPath $dll).VersionInfo.FileVersion }
    # Suficiencia exige o REGISTRO do pacote com versao coberta. A mera presenca
    # da DLL nao basta: um arquivo solto largado por outro instalador nao prova
    # runtime completo nem versao compativel com o toolset do YARA.
    $suficiente = $false
    if ($instalado -and ($versao -match '^(\d+)\.(\d+)')) {
        try { $suficiente = ([Version]('{0}.{1}' -f $Matches[1], $Matches[2]) -ge $Minimo) } catch {}
    }
    return [pscustomobject]@{
        Installed  = $instalado
        Version    = $versao
        DllPresent = $dllPresente
        DllVersion = $dllVersao
        Sufficient = ($suficiente -and $dllPresente)
    }
}

function Install-VcRuntimeFromMedia {
    param([Parameter(Mandatory)][string]$Root)
    $dir = Join-Path $Root 'vcredist'
    $exe = Join-Path $dir 'vc_redist.x64.exe'
    $pinPath = Join-Path $dir 'vcruntime-pin.json'
    $minimo  = [Version]'14.30'
    $shaEsperado = ''
    if (Test-Path $pinPath) {
        try {
            $pin = Get-Content $pinPath -Raw | ConvertFrom-Json
            $shaEsperado = [string]$pin.sha256
            if ([string]$pin.min_runtime_version) { $minimo = [Version]$pin.min_runtime_version }
        } catch {}
    }
    $estado = Get-VcRuntimeState -Minimo $minimo
    $saida = [ordered]@{
        min_version   = $minimo.ToString()
        media_sha256  = ''
        pin_sha256    = $shaEsperado
        signature     = ''
        exit_code     = $null
        preinstalled  = [bool]$estado.Sufficient
        installed     = [bool]$estado.Installed
        version       = [string]$estado.Version
        dll_present   = [bool]$estado.DllPresent
        dll_version   = [string]$estado.DllVersion
        sufficient    = [bool]$estado.Sufficient
    }
    if ($estado.Sufficient) {
        Write-Log ("runtime v14 x64 ja presente e suficiente: " + $estado.Version)
        return [pscustomobject]$saida
    }
    if (-not (Test-Path $exe)) {
        Add-Blocker 'VCRUNTIME_INSTALL_FAILED' 'redistribuivel ausente na midia'
        return [pscustomobject]$saida
    }
    if (-not $shaEsperado) {
        Add-Blocker 'VCRUNTIME_HASH_MISMATCH' 'midia sem pin de hash'
        return [pscustomobject]$saida
    }
    # 1) Hash: o binario da midia precisa ser o mesmo que o host assinou e pinou.
    $shaMidia = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
    $saida.media_sha256 = $shaMidia
    if ($shaMidia -ne $shaEsperado.ToLowerInvariant()) {
        Add-Blocker 'VCRUNTIME_HASH_MISMATCH' ("midia=" + $shaMidia)
        return [pscustomobject]$saida
    }
    # 2) Assinatura: valida E emitida para a Microsoft Corporation, verificada
    #    tambem AQUI - a cadeia de confianca do guest e a que importa na hora de
    #    executar o instalador.
    $sig = Get-AuthenticodeSignature -LiteralPath $exe
    $assunto = if ($sig.SignerCertificate) { $sig.SignerCertificate.Subject } else { '' }
    $saida.signature = $sig.Status.ToString()
    $microsoft = ($assunto -match '(?i)O=Microsoft Corporation') -or ($assunto -match '(?i)CN=Microsoft Corporation')
    if (($sig.Status -ne 'Valid') -or (-not $microsoft)) {
        Add-Blocker 'VCRUNTIME_SIGNATURE_INVALID' ("status=" + $sig.Status)
        return [pscustomobject]$saida
    }
    # 3) Instalacao silenciosa pelo instalador OFICIAL.
    Send-Heartbeat 'VCRUNTIME_INSTALL' ("sha=" + $shaMidia.Substring(0, 12))
    try {
        $proc = Start-Process -FilePath $exe -ArgumentList '/install', '/quiet', '/norestart' -Wait -PassThru
        $saida.exit_code = [int]$proc.ExitCode
    } catch {
        Add-Blocker 'VCRUNTIME_INSTALL_FAILED' $_.Exception.Message
        return [pscustomobject]$saida
    }
    # 0 = instalado; 1638 = ja existe versao igual ou mais nova; 3010 = pede
    # reboot, mas o runtime ja fica utilizavel. Qualquer outro codigo reprova.
    if (@(0, 1638, 3010) -notcontains [int]$saida.exit_code) {
        Add-Blocker 'VCRUNTIME_INSTALL_FAILED' ("exit=" + $saida.exit_code)
        return [pscustomobject]$saida
    }
    # 4) Validacao pelo RESULTADO, nao pelo codigo de saida do instalador.
    $depois = Get-VcRuntimeState -Minimo $minimo
    $saida.installed   = [bool]$depois.Installed
    $saida.version     = [string]$depois.Version
    $saida.dll_present = [bool]$depois.DllPresent
    $saida.dll_version = [string]$depois.DllVersion
    $saida.sufficient  = [bool]$depois.Sufficient
    if (-not $depois.Sufficient) {
        Add-Blocker 'VCRUNTIME_INSTALL_FAILED' ("pos-instalacao insuficiente: versao=" + $depois.Version)
    } else {
        Write-Log ("runtime v14 x64 instalado: " + $depois.Version)
    }
    return [pscustomobject]$saida
}

function Get-YaraVersion {
    # Execucao REAL. Se a dependencia de runtime faltar, o processo nem inicia e
    # a excecao deixa a versao vazia - que e exatamente o sinal procurado.
    $v = ''
    try { $v = (& (Join-Path $YaraDir 'yara64.exe') --version 2>&1 | Out-String).Trim() } catch {}
    return $v
}

function Test-RulesetPin {
    # Recomputa o agregado do ruleset com a MESMA regra do host (manifesto
    # "<rel><TAB><sha256><LF>", na ordem do pin, UTF-8 sem BOM). Isto prova que o
    # conjunto entregue e byte-identico ao commit pinado - contar arquivos, como
    # na primeira instalacao limpa, nao provava nada.
    param([string]$PinPath, [string]$Dir)
    $commit = ''; $esperado = ''; $computado = ''; $faltando = 0; $divergentes = 0; $total = 0
    if (Test-Path $PinPath) {
        try {
            $pin = Get-Content $PinPath -Raw | ConvertFrom-Json
            $commit   = [string]$pin.commit_sha40
            $esperado = [string]$pin.aggregate_sha256
            $sb = New-Object System.Text.StringBuilder
            foreach ($e in @($pin.files)) {
                $total++
                $p = Join-Path $Dir ([string]$e.rel -replace '/', '\')
                $h = ''
                if (Test-Path -LiteralPath $p) {
                    $h = (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()
                    if ($h -ne ([string]$e.sha).ToLowerInvariant()) { $divergentes++ }
                } else { $faltando++ }
                [void]$sb.Append([string]$e.rel); [void]$sb.Append("`t"); [void]$sb.Append($h); [void]$sb.Append("`n")
            }
            $utf8 = New-Object System.Text.UTF8Encoding($false)
            $sha  = [Security.Cryptography.SHA256]::Create()
            $computado = ([BitConverter]::ToString($sha.ComputeHash($utf8.GetBytes($sb.ToString()))) -replace '-', '').ToLowerInvariant()
        } catch { Write-Log ("verificacao do pin do ruleset falhou: " + $_.Exception.Message) }
    }
    return [pscustomobject]@{
        Commit     = $commit
        Expected   = $esperado
        Computed   = $computado
        Total      = $total
        Missing    = $faltando
        Mismatched = $divergentes
        Ok         = (($commit -cmatch '^[0-9a-f]{40}$') -and $esperado -and ($computado -eq $esperado) -and ($faltando -eq 0) -and ($divergentes -eq 0))
    }
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

    # Retomada registrada AGORA, antes de qualquer etapa capaz de reiniciar o
    # guest. O instalador do runtime roda com /norestart, mas um reboot vindo de
    # outra origem antes do registro deixaria o laboratorio parado para sempre,
    # sem ninguem para retomar o payload. O custo de registrar cedo e zero.
    Register-StartupTask

    New-Item -ItemType Directory -Force $YaraDir | Out-Null
    Copy-Item (Join-Path $root 'yara\*') "$YaraDir\" -Force
    New-Item -ItemType Directory -Force $RulesDir | Out-Null
    Copy-Item (Join-Path $root 'rules\*') "$RulesDir\" -Recurse -Force
    # O pin fica FORA de C:\Tools\YARA-Rules: la dentro ele entraria no proprio
    # conjunto que descreve.
    Copy-Item (Join-Path $root 'rules-pin.json') $RulesPin -Force -ErrorAction SilentlyContinue
    Write-Log 'YARA e ruleset instalados a partir da midia'

    # Runtime ANTES do YARA: sem ele nem yara64.exe nem yarac64.exe iniciam.
    $rt = Install-VcRuntimeFromMedia -Root $root
    $yaraVersaoInstall = ''
    if ($rt.sufficient) {
        $yaraVersaoInstall = Get-YaraVersion
        if ($yaraVersaoInstall -ne '4.5.5') {
            Add-Blocker 'YARA_RUNTIME_DEPENDENCY_UNSATISFIED' ("yara --version='" + $yaraVersaoInstall + "'")
        } else {
            Write-Log 'YARA executa no guest (dependencia de runtime satisfeita)'
        }
    } else {
        Add-Blocker 'YARA_RUNTIME_DEPENDENCY_UNSATISFIED' 'runtime v14 x64 insuficiente'
    }
    $rt | Add-Member -NotePropertyName yara_version_install -NotePropertyValue $yaraVersaoInstall -Force
    ($rt | ConvertTo-Json -Depth 4) | Set-Content -LiteralPath $RuntimeFile -Encoding utf8

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

    # Versao da ESPECIFICACAO do TPM. Get-Tpm responde presente/pronto mas nao
    # diz 1.2 ou 2.0; sem isto o criterio tpm_2_0 ficava sem prova.
    $tpmSpec = ''
    try {
        $wt = Get-CimInstance -Namespace 'root\cimv2\security\microsofttpm' -ClassName Win32_Tpm -ErrorAction Stop
        $tpmSpec = ([string]$wt.SpecVersion -split ',')[0].Trim()
    } catch { Write-Log ("SpecVersion do TPM indisponivel: " + $_.Exception.Message) }

    $mpCmd = $null
    try {
        $plat = Get-ChildItem "$env:ProgramData\Microsoft\Windows Defender\Platform" -Directory -ErrorAction Stop |
                Sort-Object Name -Descending | Select-Object -First 1
        $mpCmd = Join-Path $plat.FullName 'MpCmdRun.exe'
    } catch {}
    if (-not $mpCmd -or -not (Test-Path $mpCmd)) { $mpCmd = "$env:ProgramFiles\Windows Defender\MpCmdRun.exe" }

    # Runtime + YARA: o estado do runtime vem do arquivo (sobrevive aos reboots)
    # e a versao do YARA e reconferida AGORA, por execucao real.
    $rt = $null
    if (Test-Path $RuntimeFile) { try { $rt = Get-Content $RuntimeFile -Raw | ConvertFrom-Json } catch {} }
    $yaraVer = Get-YaraVersion
    $yaraOk  = ($yaraVer -eq '4.5.5')
    if (-not $yaraOk) { Add-Blocker 'YARA_RUNTIME_DEPENDENCY_UNSATISFIED' ("yara --version='" + $yaraVer + "'") }

    # Ruleset e sanitize SO depois de o YARA provar que executa: sem ele o yarac
    # tambem nao inicia e qualquer resultado seria ruido.
    $rulesOk = $false
    $pin = $null
    $rulesCount = 0
    $hits = @(); $vendorHits = @(); $infoHits = @()
    if ($yaraOk) {
        try {
            # Compila o indice DENTRO do guest: prova que o ruleset entregue esta
            # integro e utilizavel ali, nao apenas que os arquivos existem.
            & (Join-Path $YaraDir 'yarac64.exe') (Join-Path $RulesDir 'gate5-index.yar') "$env:TEMP\gate5-guest.yrc" 2>&1 | Out-Null
            $rulesOk = ($LASTEXITCODE -eq 0)
            Remove-Item "$env:TEMP\gate5-guest.yrc" -Force -ErrorAction SilentlyContinue
        } catch {}
        $pin = Test-RulesetPin -PinPath $RulesPin -Dir $RulesDir
        $rulesCount = @(Get-ChildItem $RulesDir -Recurse -File -Include '*.yar', '*.yara' -ErrorAction SilentlyContinue).Count
        Send-Heartbeat 'RULESET_CHECKED' ("compile=" + $rulesOk + ";pin=" + $pin.Ok)

        # --- Varredura de secrets --------------------------------------------
        # Padroes DECISORIOS INCONDICIONAIS: material de chave e artefatos do
        # projeto. Reprovam em QUALQUER caminho.
        $gatingAlways = @('*.pem', '*.ppk', 'id_rsa*', 'id_ed25519*', '.env', '.env.*',
                          '*faithro*', 'Ragexe*', '*.grf', 'WARP*', '*.gat', '*.rsw')
        # Padroes por EXTENSAO GENERICA: reprovam FORA das arvores de assets de
        # aplicativos do proprio Windows. A primeira instalacao limpa reprovou
        # com 67 acertos, TODOS modelos de consulta .sql embarcados pelo
        # OneDrive - falso positivo do padrao generico, nao vazamento. Continuam
        # listados como informativos, nunca descartados em silencio.
        $gatingUnlessVendor = @('*.sql', '*.dump')
        $info   = @('*credential*', '*token*', '*github*')
        $roots  = @('C:\Users', 'C:\gate5', 'C:\Tools', 'C:\Temp', 'C:\Windows\Temp')
        # Assets de aplicativo do fornecedor. Deliberadamente estreito: so as
        # duas arvores em que o Windows e a loja depositam os proprios pacotes.
        $vendorAsset = '\\AppData\\Local\\Microsoft\\|\\AppData\\Local\\Packages\\'
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
        # A propria arvore de ferramentas aprovadas do laboratorio nao e
        # vazamento: C:\Tools\YARA-Rules contem regras cujos nomes citam malware.
        $benign = '\\Tools\\YARA'
        $hitsAlways  = @(Find-Hits $gatingAlways       | Where-Object { $_ -notmatch $benign })
        $hitsGeneric = @(Find-Hits $gatingUnlessVendor | Where-Object { $_ -notmatch $benign })
        $vendorHits  = @($hitsGeneric | Where-Object { $_ -match $vendorAsset })
        $hits        = @($hitsAlways) + @($hitsGeneric | Where-Object { $_ -notmatch $vendorAsset })
        $infoHits    = @(Find-Hits $info | Where-Object { $_ -notmatch $benign })
    } else {
        Write-Log 'ruleset e sanitize nao avaliados: dependencia de runtime do YARA insatisfeita'
    }
    $warp = @(Get-ChildItem 'C:\' -Recurse -Depth 3 -Filter 'WARP*' -ErrorAction SilentlyContinue).Count

    $blockers = @(Get-Blockers)
    $ev = [ordered]@{
        schema            = 'gate5-guest-evidence/v2'
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
        tpm_spec_version  = $tpmSpec
        tpm_2_0           = [bool]($tpmSpec -like '2.0*')
        defender_av       = [bool]($mp -and $mp.AntivirusEnabled)
        defender_rt       = [bool]($mp -and $mp.RealTimeProtectionEnabled)
        defender_platform = if ($mp) { $mp.AMProductVersion } else { $null }
        defender_engine   = if ($mp) { $mp.AMEngineVersion } else { $null }
        defender_sigs     = if ($mp) { $mp.AntivirusSignatureVersion } else { $null }
        mpcmdrun_path     = $mpCmd
        mpcmdrun_sha256   = if (Test-Path $mpCmd) { (Get-FileHash $mpCmd -Algorithm SHA256).Hash.ToLowerInvariant() } else { $null }
        vcruntime_installed    = if ($rt) { [bool]$rt.installed } else { $false }
        vcruntime_version      = if ($rt) { [string]$rt.version } else { '' }
        vcruntime_dll_version  = if ($rt) { [string]$rt.dll_version } else { '' }
        vcruntime_sufficient   = if ($rt) { [bool]$rt.sufficient } else { $false }
        vcruntime_preinstalled = if ($rt) { [bool]$rt.preinstalled } else { $false }
        vcruntime_sha256       = if ($rt) { [string]$rt.media_sha256 } else { '' }
        vcruntime_signature    = if ($rt) { [string]$rt.signature } else { '' }
        vcruntime_exit_code    = if ($rt) { $rt.exit_code } else { $null }
        yara_version      = $yaraVer
        yara_runtime_ok   = $yaraOk
        yara_sha256       = if (Test-Path (Join-Path $YaraDir 'yara64.exe')) { (Get-FileHash (Join-Path $YaraDir 'yara64.exe') -Algorithm SHA256).Hash.ToLowerInvariant() } else { $null }
        rules_compile_ok  = $rulesOk
        rules_file_count  = $rulesCount
        ruleset_commit             = if ($pin) { $pin.Commit } else { '' }
        ruleset_aggregate_expected = if ($pin) { $pin.Expected } else { '' }
        ruleset_aggregate_computed = if ($pin) { $pin.Computed } else { '' }
        ruleset_files_missing      = if ($pin) { $pin.Missing } else { $null }
        ruleset_files_mismatched   = if ($pin) { $pin.Mismatched } else { $null }
        ruleset_pinned    = [bool](($null -ne $pin) -and $pin.Ok -and $rulesOk)
        nics_up           = @(Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq 'Up' }).Count
        warp_artifacts    = $warp
        secrets_gating        = @($hits)
        secrets_gating_count  = @($hits).Count
        secrets_vendor_count  = @($vendorHits).Count
        secrets_vendor_sample = @($vendorHits | Select-Object -First 5)
        secrets_info_count    = @($infoHits).Count
        sanitize_pass     = [bool]($yaraOk -and (@($hits).Count -eq 0))
        blockers          = @($blockers)
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
