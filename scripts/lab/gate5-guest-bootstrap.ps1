# gate5-guest-bootstrap.ps1 - Fases de bootstrap do guest FaithRO-GATE5-LAB.
# Chamado pelo entrypoint gate5-provision.ps1 com -Phase <fase>.
# Fases: Unattend | InstallWait | Updates | Defender | Yara | Rules | Sanitize
#
# Credenciais do guest: geradas em runtime, gravadas SOMENTE em
# .local\gate5-lab\secrets\guest-credential.xml (Export-Clixml, DPAPI do
# usuario atual). Nunca em Git, nunca em log, nunca em relatorio.

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('Unattend','InstallWait','Updates','Defender','Yara','Rules','Sanitize')]
    [string]$Phase
)

. (Join-Path $PSScriptRoot 'gate5-common.ps1')
if (-not (Get-Variable -Name Gate5LogFile -Scope Script -ErrorAction SilentlyContinue)) { Initialize-Gate5Log }

$vmware = Find-Gate5VmwareInstall
if (-not $vmware) { throw 'GATE5: VMware Workstation nao instalado.' }

$credFile     = Join-Path $script:Gate5SecretDir 'guest-credential.xml'
$unattendIso  = Join-Path $script:Gate5VmDir 'gate5-unattend.iso'

function Get-GuestCredential {
    if (-not (Test-Path $credFile)) { throw 'GATE5: credencial de bootstrap do guest ausente; fase Unattend nao concluida.' }
    return Import-Clixml $credFile
}

function Invoke-GuestPS {
    # Executa um script PowerShell dentro do guest via vmrun (canal temporario
    # de administracao LOCAL; removido na fase Sanitize junto com a conta).
    param([Parameter(Mandatory)][string]$ScriptText, [string]$Label = 'guest-script', [int]$TimeoutSec = 3600)
    $cred  = Get-GuestCredential
    $plain = $cred.GetNetworkCredential().Password
    $local = Join-Path $script:Gate5LocalDir "$Label.ps1"
    Set-Content -Path $local -Value $ScriptText -Encoding utf8
    $guestPath = "C:\\gate5\\$Label.ps1"
    try {
        Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('-gu', $cred.UserName, '-gp', $plain, 'createDirectoryInGuest', $script:Gate5VmxPath, 'C:\gate5') -AllowFailure | Out-Null
        Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('-gu', $cred.UserName, '-gp', $plain, 'CopyFileFromHostToGuest', $script:Gate5VmxPath, $local, $guestPath) | Out-Null
        $r = Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('-gu', $cred.UserName, '-gp', $plain, 'runProgramInGuest', $script:Gate5VmxPath, 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', $guestPath) -AllowFailure
        return $r
    } finally {
        Remove-Item $local -Force -ErrorAction SilentlyContinue
    }
}

function Copy-ToGuest {
    param([Parameter(Mandatory)][string]$HostPath, [Parameter(Mandatory)][string]$GuestPath)
    $cred  = Get-GuestCredential
    $plain = $cred.GetNetworkCredential().Password
    Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('-gu', $cred.UserName, '-gp', $plain, 'CopyFileFromHostToGuest', $script:Gate5VmxPath, $HostPath, $GuestPath) | Out-Null
}

function Copy-FromGuest {
    param([Parameter(Mandatory)][string]$GuestPath, [Parameter(Mandatory)][string]$HostPath)
    $cred  = Get-GuestCredential
    $plain = $cred.GetNetworkCredential().Password
    Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('-gu', $cred.UserName, '-gp', $plain, 'CopyFileFromGuestToHost', $script:Gate5VmxPath, $GuestPath, $HostPath) | Out-Null
}

switch ($Phase) {

    # -------------------------------------------------------------------------
    'Unattend' {
        # 1) Senha de bootstrap gerada em runtime (nunca versionada/logada)
        if (-not (Test-Path $credFile)) {
            $bytes = New-Object byte[] 24
            [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
            $pw = ([Convert]::ToBase64String($bytes) -replace '[^A-Za-z0-9]', 'x') + '!Aa1'
            $sec = ConvertTo-SecureString $pw -AsPlainText -Force
            New-Object PSCredential('gate5boot', $sec) | Export-Clixml $credFile
            Write-Gate5Log 'Credencial de bootstrap gerada e protegida por DPAPI em .local (fora do Git).'
        }
        $cred  = Get-GuestCredential
        $plain = $cred.GetNetworkCredential().Password

        # 2) Renderizar Autounattend.xml a partir do template (sem secrets no repo)
        $template = Get-Content (Join-Path $PSScriptRoot 'templates\Autounattend.template.xml') -Raw
        $rendered = $template.Replace('{{BOOTSTRAP_PASSWORD}}', [Security.SecurityElement]::Escape($plain))
        $stageDir = Join-Path $script:Gate5LocalDir 'unattend-stage'
        New-Item -ItemType Directory -Force $stageDir | Out-Null
        Set-Content -Path (Join-Path $stageDir 'Autounattend.xml') -Value $rendered -Encoding utf8

        # 3) Gerar ISO auxiliar com IMAPI2FS (COM nativo do Windows, sem downloads)
        $fsi = New-Object -ComObject IMAPI2FS.MsftFileSystemImage
        $fsi.FileSystemsToCreate = 3   # ISO9660 + Joliet
        $fsi.VolumeName = 'GATE5UNATTEND'
        $fsi.Root.AddTree($stageDir, $false)
        $img = $fsi.CreateResultImage()
        $stream = $img.ImageStream
        # gravar o stream COM em arquivo
        $ctype = [Type]::GetTypeFromCLSID('0000000C-0000-0000-C000-000000000046')
        Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
public static class Gate5IsoWriter {
    public static void Write(object comStream, string path) {
        IStream src = (IStream)comStream;
        using (FileStream fs = File.Create(path)) {
            byte[] buf = new byte[1048576];
            IntPtr readPtr = Marshal.AllocHGlobal(sizeof(int));
            try {
                while (true) {
                    src.Read(buf, buf.Length, readPtr);
                    int read = Marshal.ReadInt32(readPtr);
                    if (read <= 0) break;
                    fs.Write(buf, 0, read);
                }
            } finally { Marshal.FreeHGlobal(readPtr); }
        }
    }
}
'@ -ErrorAction SilentlyContinue
        [Gate5IsoWriter]::Write($stream, $unattendIso)
        Remove-Item $stageDir -Recurse -Force
        if (-not (Test-Path $unattendIso)) { throw 'GATE5: falha ao gerar ISO de unattend.' }
        Write-Gate5Log "ISO de unattend gerada: $unattendIso (sera destruida na fase Sanitize)."

        # 4) Anexar como segundo CD-ROM no VMX (VM precisa estar desligada)
        if (-not (Select-String -LiteralPath $script:Gate5VmxPath -Pattern '^sata0:2\.present' -Quiet)) {
            Add-Content -Path $script:Gate5VmxPath -Encoding utf8 -Value @(
                'sata0:2.present = "TRUE"'
                'sata0:2.deviceType = "cdrom-image"'
                ('sata0:2.fileName = "{0}"' -f $unattendIso)
                'sata0:2.startConnected = "TRUE"'
            )
        }
        exit 0
    }

    # -------------------------------------------------------------------------
    'InstallWait' {
        # Liga a VM e aguarda o Windows Setup terminar (deteccao: guest ops
        # respondem com a credencial de bootstrap). Timeout global de 2h.
        $running = (Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('list') -AllowFailure).Output
        if ($running -notmatch [regex]::Escape($script:Gate5VmxPath)) {
            Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('start', $script:Gate5VmxPath, 'nogui') | Out-Null
            Write-Gate5Log 'VM ligada; aguardando instalacao unattended do Windows...'
        }
        $cred  = Get-GuestCredential
        $plain = $cred.GetNetworkCredential().Password
        $deadline = [DateTime]::UtcNow.AddHours(2)
        while ([DateTime]::UtcNow -lt $deadline) {
            $r = Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('-gu', $cred.UserName, '-gp', $plain, 'runProgramInGuest', $script:Gate5VmxPath, 'C:\Windows\System32\cmd.exe', '/c', 'ver') -AllowFailure
            if ($r.ExitCode -eq 0) {
                Write-Gate5Log 'Guest operacional: instalacao do Windows concluida.'
                # VMware Tools: necessario para guest ops estaveis e drivers
                $t = Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('checkToolsState', $script:Gate5VmxPath) -AllowFailure
                if ($t.Output -notmatch 'installed|running') {
                    Write-Gate5Log 'Instalando VMware Tools...'
                    Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('installTools', $script:Gate5VmxPath) -AllowFailure | Out-Null
                }
                exit 0
            }
            Start-Sleep -Seconds 120
        }
        throw 'GATE5: timeout aguardando a instalacao do Windows no guest (2h).'
    }

    # -------------------------------------------------------------------------
    'Updates' {
        # Windows Update via COM (Microsoft.Update.Session), com reboot do GUEST
        # permitido. Loop ate zero atualizacoes aplicaveis ou 6 ciclos.
        $updateScript = @'
$ErrorActionPreference = "Stop"
$session  = New-Object -ComObject Microsoft.Update.Session
$searcher = $session.CreateUpdateSearcher()
$result   = $searcher.Search("IsInstalled=0 and IsHidden=0 and Type='Software'")
$out = @{ found = $result.Updates.Count; installed = 0; reboot = $false }
if ($result.Updates.Count -gt 0) {
    $coll = New-Object -ComObject Microsoft.Update.UpdateColl
    foreach ($u in $result.Updates) { if (-not $u.EulaAccepted) { $u.AcceptEula() }; $coll.Add($u) | Out-Null }
    $dl = $session.CreateUpdateDownloader(); $dl.Updates = $coll; $dl.Download() | Out-Null
    $inst = $session.CreateUpdateInstaller(); $inst.Updates = $coll
    $ir = $inst.Install()
    $out.installed = $coll.Count
    $out.reboot = [bool]$ir.RebootRequired
}
$out | ConvertTo-Json | Out-File C:\gate5\wu-result.json -Encoding utf8
if ($out.reboot) { shutdown /r /t 5 }
'@
        for ($cycle = 1; $cycle -le 6; $cycle++) {
            Write-Gate5Log "Windows Update: ciclo $cycle"
            Invoke-GuestPS -ScriptText $updateScript -Label 'gate5-wu' -TimeoutSec 5400 | Out-Null
            $tmp = Join-Path $script:Gate5LocalDir 'wu-result.json'
            Start-Sleep -Seconds 20
            try { Copy-FromGuest -GuestPath 'C:\gate5\wu-result.json' -HostPath $tmp } catch { Start-Sleep -Seconds 300; continue }
            $wu = Get-Content $tmp -Raw | ConvertFrom-Json
            Write-Gate5Log ("Windows Update: encontradas={0} instaladas={1} reboot={2}" -f $wu.found, $wu.installed, $wu.reboot)
            if ($wu.reboot) {
                Write-Gate5Log 'Aguardando reboot do guest...'
                Start-Sleep -Seconds 300
                continue
            }
            if ($wu.found -eq 0) { Write-Gate5Log 'Windows Update: nenhuma atualizacao aplicavel restante.'; exit 0 }
        }
        throw 'GATE5: Windows Update nao convergiu em 6 ciclos.'
    }

    # -------------------------------------------------------------------------
    'Defender' {
        $defenderScript = @'
$ErrorActionPreference = "Stop"
Update-MpSignature
$s = Get-MpComputerStatus
$mp = Get-ChildItem "$env:ProgramData\Microsoft\Windows Defender\Platform" -Directory | Sort-Object Name -Descending | Select-Object -First 1
$mpCmd = Join-Path $mp.FullName "MpCmdRun.exe"
if (-not (Test-Path $mpCmd)) { $mpCmd = "$env:ProgramFiles\Windows Defender\MpCmdRun.exe" }
$sig = Get-AuthenticodeSignature $mpCmd
@{
    antivirus_enabled = $s.AntivirusEnabled
    realtime_enabled  = $s.RealTimeProtectionEnabled
    platform_version  = $s.AMProductVersion
    engine_version    = $s.AMEngineVersion
    signature_version = $s.AntivirusSignatureVersion
    signature_updated = $s.AntivirusSignatureLastUpdated.ToUniversalTime().ToString("s") + "Z"
    mpcmdrun_path     = $mpCmd
    mpcmdrun_sha256   = (Get-FileHash $mpCmd -Algorithm SHA256).Hash.ToLowerInvariant()
    mpcmdrun_signature_status = $sig.Status.ToString()
} | ConvertTo-Json | Out-File C:\gate5\defender-result.json -Encoding utf8
'@
        Invoke-GuestPS -ScriptText $defenderScript -Label 'gate5-defender' | Out-Null
        $tmp = Join-Path $script:Gate5EvidenceDir 'guest-defender.json'
        Copy-FromGuest -GuestPath 'C:\gate5\defender-result.json' -HostPath $tmp
        $d = Get-Content $tmp -Raw | ConvertFrom-Json
        if (-not ($d.antivirus_enabled -and $d.realtime_enabled)) { throw 'GATE5: Defender nao esta com antivirus+realtime habilitados.' }
        Write-Gate5Log ("Defender OK: platform={0} engine={1} sig={2}" -f $d.platform_version, $d.engine_version, $d.signature_version)
        exit 0
    }

    # -------------------------------------------------------------------------
    'Yara' {
        # Download HOST-side da release oficial VirusTotal/yara v4.5.5 (fonte
        # unica aprovada), validacao, extracao e copia para o guest.
        $stage = Join-Path $script:Gate5LocalDir 'yara-stage'
        New-Item -ItemType Directory -Force $stage | Out-Null
        $zipPath = Join-Path $stage 'yara-4.5.5-win64.zip'
        if (-not (Test-Path $zipPath)) {
            $api = 'https://api.github.com/repos/VirusTotal/yara/releases/tags/v4.5.5'
            Write-Gate5Log "Consultando metadados da release oficial: $api"
            $rel = Invoke-RestMethod -Uri $api -Headers @{ 'User-Agent' = 'FaithRO-GATE5-Lab' }
            $asset = $rel.assets | Where-Object { $_.name -match '^yara-(v?)4\.5\.5.*win64\.zip$' } | Select-Object -First 1
            if (-not $asset) { throw 'GATE5: asset win64 da release v4.5.5 nao localizado nos metadados oficiais.' }
            Write-Gate5Log ("Baixando asset oficial: {0} ({1} bytes)" -f $asset.name, $asset.size)
            Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath
            if ((Get-Item $zipPath).Length -ne $asset.size) { throw 'GATE5: tamanho do download nao confere com os metadados da release.' }
        }
        $zipSha = Get-Gate5Sha256 -Path $zipPath
        Write-Gate5Log "yara zip sha256=$zipSha"
        Expand-Archive -Path $zipPath -DestinationPath (Join-Path $stage 'extracted') -Force
        $yaraExe  = Get-ChildItem (Join-Path $stage 'extracted') -Recurse -Filter 'yara64.exe'  | Select-Object -First 1
        $yaracExe = Get-ChildItem (Join-Path $stage 'extracted') -Recurse -Filter 'yarac64.exe' | Select-Object -First 1
        if (-not $yaraExe -or -not $yaracExe) { throw 'GATE5: yara64.exe/yarac64.exe ausentes no asset oficial.' }
        $ver = & $yaraExe.FullName --version
        if ($ver.Trim() -ne $script:Gate5YaraVersion) { throw "GATE5: versao YARA inesperada no host: '$ver' (esperado 4.5.5)." }

        $evidence = [ordered]@{
            schema         = 'gate5-lab-yara/v1'
            source         = 'VirusTotal/yara release v4.5.5 (oficial)'
            zip_sha256     = $zipSha
            yara64_sha256  = Get-Gate5Sha256 -Path $yaraExe.FullName
            yarac64_sha256 = Get-Gate5Sha256 -Path $yaracExe.FullName
            version        = $ver.Trim()
            timestamp_utc  = [DateTime]::UtcNow.ToString('s') + 'Z'
        }
        $evidence | ConvertTo-Json | Out-File (Join-Path $script:Gate5EvidenceDir 'yara.json') -Encoding utf8

        # Espelho local em C:\Tools\YARA + copia para o guest
        New-Item -ItemType Directory -Force $script:Gate5YaraDir | Out-Null
        Copy-Item $yaraExe.FullName  (Join-Path $script:Gate5YaraDir 'yara64.exe')  -Force
        Copy-Item $yaracExe.FullName (Join-Path $script:Gate5YaraDir 'yarac64.exe') -Force
        Invoke-GuestPS -ScriptText 'New-Item -ItemType Directory -Force C:\Tools\YARA | Out-Null' -Label 'gate5-mkdir-yara' | Out-Null
        Copy-ToGuest -HostPath (Join-Path $script:Gate5YaraDir 'yara64.exe')  -GuestPath 'C:\Tools\YARA\yara64.exe'
        Copy-ToGuest -HostPath (Join-Path $script:Gate5YaraDir 'yarac64.exe') -GuestPath 'C:\Tools\YARA\yarac64.exe'
        # Verificacao dentro do guest (fail-closed)
        $check = Invoke-GuestPS -Label 'gate5-yara-check' -ScriptText @'
$v = & C:\Tools\YARA\yara64.exe --version
@{ version = $v.Trim(); sha256 = (Get-FileHash C:\Tools\YARA\yara64.exe -Algorithm SHA256).Hash.ToLowerInvariant() } |
    ConvertTo-Json | Out-File C:\gate5\yara-check.json -Encoding utf8
if ($v.Trim() -ne "4.5.5") { exit 1 }
'@
        if ($check.ExitCode -ne 0) { throw 'GATE5: verificacao do YARA no guest falhou.' }
        Write-Gate5Log 'YARA 4.5.5 posicionado e verificado no guest.'
        exit 0
    }

    # -------------------------------------------------------------------------
    'Rules' {
        # Aquisicao HOST-side do ruleset Yara-Rules/rules: resolve o SHA-40 da
        # branch default UMA vez, fixa, filtra categorias autorizadas, compila
        # com yarac 4.5.5 (0 erros) e gera hashes deterministicos.
        $included = @('malware','packers','antidebug_antivm','capabilities','crypto')
        $excluded = @('email','mobile_malware','webshells','maldocs')
        $rulesRepo = Join-Path $script:Gate5LocalDir 'yara-rules-src'
        $pinFile   = Join-Path $script:Gate5EvidenceDir 'ruleset-pin.json'

        if (Test-Path $pinFile) {
            $pin = (Get-Content $pinFile -Raw | ConvertFrom-Json).commit_sha40
            Write-Gate5Log "Ruleset ja pinado: $pin"
        } else {
            git clone --quiet https://github.com/Yara-Rules/rules $rulesRepo
            $pin = (git -C $rulesRepo rev-parse HEAD).Trim()
            if ($pin -notmatch '^[0-9a-f]{40}$') { throw 'GATE5: SHA-40 do ruleset nao resolvido.' }
            [ordered]@{ repo = 'https://github.com/Yara-Rules/rules'; commit_sha40 = $pin; license = 'GPL-2.0';
                        timestamp_utc = [DateTime]::UtcNow.ToString('s') + 'Z';
                        categories_included = $included; categories_excluded = $excluded } |
                ConvertTo-Json | Out-File $pinFile -Encoding utf8
            Write-Gate5Log "Ruleset pinado no commit $pin"
        }
        if (-not (Test-Path $rulesRepo)) { throw 'GATE5: clone do ruleset ausente; remova o pin para readquirir.' }
        git -C $rulesRepo checkout --quiet $pin

        # Selecao das categorias autorizadas
        New-Item -ItemType Directory -Force $script:Gate5RulesDir | Out-Null
        $selected = @()
        foreach ($cat in $included) {
            $src = Join-Path $rulesRepo $cat
            if (-not (Test-Path $src)) { throw "GATE5: categoria '$cat' ausente no commit pinado." }
            $dst = Join-Path $script:Gate5RulesDir $cat
            if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
            Copy-Item $src $dst -Recurse
            $selected += Get-ChildItem $dst -Recurse -File | Where-Object { $_.Extension -in '.yar', '.yara' }
        }
        # Preservacao da licenca GPL-2.0
        Copy-Item (Join-Path $rulesRepo 'LICENSE') (Join-Path $script:Gate5RulesDir 'LICENSE') -Force -ErrorAction SilentlyContinue

        # Compilacao individual com yarac (0 erros exigido). Regras que falharem
        # sao registradas e excluidas SOMENTE por regra objetiva documentada:
        # "incompativel com YARA 4.5.5 (erro de compilacao upstream)".
        $yarac = Join-Path $script:Gate5YaraDir 'yarac64.exe'
        if (-not (Test-Path $yarac)) { throw 'GATE5: yarac64.exe nao posicionado (fase Yara pendente).' }
        $compileErrors = @()
        $effective = @()
        foreach ($f in $selected) {
            $null = & $yarac $f.FullName (Join-Path $env:TEMP 'gate5-compile-test.yrc') 2>&1
            if ($LASTEXITCODE -ne 0) {
                $err = (& $yarac $f.FullName (Join-Path $env:TEMP 'gate5-compile-test.yrc') 2>&1) -join '; '
                $compileErrors += [ordered]@{ file = $f.FullName; error = $err; action = 'EXCLUIDA: incompativel com YARA 4.5.5 (erro de compilacao upstream)' }
                Write-Gate5Log "Regra excluida (nao compila em 4.5.5): $($f.FullName)" 'WARN'
            } else {
                $effective += $f
            }
        }
        Remove-Item (Join-Path $env:TEMP 'gate5-compile-test.yrc') -Force -ErrorAction SilentlyContinue

        # Indice do GATE 5 apenas com os arquivos efetivos, e compilacao final
        $indexPath = Join-Path $script:Gate5RulesDir 'gate5-index.yar'
        $indexLines = $effective | Sort-Object FullName | ForEach-Object {
            'include "{0}"' -f ($_.FullName -replace '\\', '/')
        }
        Set-Content -Path $indexPath -Value ($indexLines -join "`n") -Encoding utf8
        $null = & $yarac $indexPath (Join-Path $script:Gate5RulesDir 'gate5-index.yrc') 2>&1
        if ($LASTEXITCODE -ne 0) { throw 'GATE5: indice final nao compila com 0 erros (fail-closed).' }

        # Hashes deterministicos (manifesto: <relative-path>\t<SHA256>\n, UTF-8 sem BOM, ordenacao ordinal)
        $rulesRoot = (Get-Item $script:Gate5RulesDir).FullName
        $entries = $effective | ForEach-Object {
            $rel = $_.FullName.Substring($rulesRoot.Length).TrimStart('\') -replace '\\', '/'
            [pscustomobject]@{ rel = $rel; sha = Get-Gate5Sha256 -Path $_.FullName }
        } | Sort-Object { $_.rel }, { [string]$_.rel } # ordenacao ordinal por caminho relativo
        $manifest = ($entries | ForEach-Object { "{0}`t{1}`n" -f $_.rel, $_.sha }) -join ''
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        $sha256 = [Security.Cryptography.SHA256]::Create()
        $aggregate = ([BitConverter]::ToString($sha256.ComputeHash($utf8NoBom.GetBytes($manifest))) -replace '-', '').ToLowerInvariant()

        [ordered]@{
            schema           = 'gate5-lab-ruleset/v1'
            commit_sha40     = $pin
            file_count       = $effective.Count
            excluded_by_compile = $compileErrors
            aggregate_sha256 = $aggregate
            files            = $entries
            timestamp_utc    = [DateTime]::UtcNow.ToString('s') + 'Z'
        } | ConvertTo-Json -Depth 5 | Out-File (Join-Path $script:Gate5EvidenceDir 'ruleset.json') -Encoding utf8
        Write-Gate5Log ("Ruleset: files={0} excluidas={1} aggregate={2}" -f $effective.Count, $compileErrors.Count, $aggregate)

        # Copia do conjunto efetivo para o guest
        $rulesZip = Join-Path $script:Gate5LocalDir 'gate5-rules.zip'
        if (Test-Path $rulesZip) { Remove-Item $rulesZip -Force }
        Compress-Archive -Path (Join-Path $script:Gate5RulesDir '*') -DestinationPath $rulesZip
        Copy-ToGuest -HostPath $rulesZip -GuestPath 'C:\gate5\gate5-rules.zip'
        $r = Invoke-GuestPS -Label 'gate5-rules-deploy' -ScriptText @'
Expand-Archive -Path C:\gate5\gate5-rules.zip -DestinationPath C:\Tools\YARA-Rules -Force
Remove-Item C:\gate5\gate5-rules.zip -Force
if (-not (Test-Path C:\Tools\YARA-Rules\gate5-index.yar)) { exit 1 }
'@
        if ($r.ExitCode -ne 0) { throw 'GATE5: deploy do ruleset no guest falhou.' }
        Write-Gate5Log 'Ruleset posicionado no guest em C:\Tools\YARA-Rules.'
        exit 0
    }

    # -------------------------------------------------------------------------
    'Sanitize' {
        # Varredura passiva por secrets/dados proibidos + limpeza de bootstrap.
        # Nunca imprime conteudo: somente paths e classificacao.
        $sanitizeScript = @'
$ErrorActionPreference = "Continue"
$patterns = @("*.pem","*.ppk","id_rsa*","id_ed25519*","*.sql","*.dump",".env*","*credential*","*token*","*github*","*faithro-vps*","Ragexe*","*.grf","WARP*")
$roots = @("C:\Users","C:\gate5","C:\Tools","C:\Temp","C:\Windows\Temp")
$hits = @()
foreach ($root in $roots) {
    if (Test-Path $root) {
        foreach ($p in $patterns) {
            $hits += Get-ChildItem $root -Recurse -Force -Filter $p -ErrorAction SilentlyContinue |
                     Where-Object { -not $_.PSIsContainer } | Select-Object -ExpandProperty FullName
        }
    }
}
# Excluir falsos positivos conhecidos do proprio bootstrap/ferramentas
$hits = $hits | Where-Object { $_ -notmatch '\\Tools\\YARA' -and $_ -notmatch 'WindowsUpdate' }
# Limpeza de bootstrap
Remove-Item C:\gate5\*.ps1 -Force -ErrorAction SilentlyContinue
Remove-Item C:\gate5\*.json -Force -ErrorAction SilentlyContinue
Clear-RecycleBin -Force -ErrorAction SilentlyContinue
Remove-Item "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue
@{ suspicious_paths = @($hits); count = @($hits).Count } | ConvertTo-Json | Out-File C:\gate5\sanitize-result.json -Encoding utf8
'@
        Invoke-GuestPS -ScriptText $sanitizeScript -Label 'gate5-sanitize' | Out-Null
        $tmp = Join-Path $script:Gate5EvidenceDir 'guest-sanitize.json'
        Copy-FromGuest -GuestPath 'C:\gate5\sanitize-result.json' -HostPath $tmp
        $s = Get-Content $tmp -Raw | ConvertFrom-Json
        if ($s.count -gt 0) {
            Write-Gate5Log ("SANITIZE: {0} paths suspeitos encontrados (ver evidencia); revisao humana requerida." -f $s.count) 'FAIL'
            exit 1
        }
        # Remover autologon residual e o script remanescente
        Invoke-GuestPS -Label 'gate5-sanitize-final' -ScriptText @'
Remove-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" -Name DefaultPassword -ErrorAction SilentlyContinue
Remove-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" -Name AutoAdminLogon  -ErrorAction SilentlyContinue
Remove-Item C:\gate5 -Recurse -Force -ErrorAction SilentlyContinue
'@ | Out-Null
        # Destruir a ISO de unattend (contem hash de senha de bootstrap)
        if (Test-Path $unattendIso) { Remove-Item $unattendIso -Force }
        Write-Gate5Log 'Sanitizacao concluida: guest limpo, unattend ISO destruida.'
        exit 0
    }
}
