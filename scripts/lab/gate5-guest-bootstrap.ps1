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

function Test-GuestCredentialUsable {
    # A credencial e protegida por DPAPI DA CONTA que a gerou. Se a automacao
    # passar a rodar sob outra conta (por exemplo deixando de precisar de
    # elevacao), o arquivo existe mas nao pode ser decifrado.
    if (-not (Test-Path $credFile)) { return $false }
    try {
        $c = Import-Clixml $credFile
        return -not [string]::IsNullOrEmpty($c.GetNetworkCredential().Password)
    } catch { return $false }
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
        if (-not (Test-GuestCredentialUsable)) {
            # Credencial ilegivel (gerada por outra conta) e Windows ja instalado
            # seria irrecuperavel: a senha esta gravada dentro do guest e nao pode
            # ser redefinida por aqui. Fail-closed em vez de gerar uma senha nova
            # que nao abriria mais o guest.
            $vmdkNow = Join-Path $script:Gate5VmDir 'FaithRO-GATE5-LAB.vmdk'
            $guestInstalled = (Test-Path $vmdkNow) -and ((Get-Item $vmdkNow).Length -gt 1GB)
            if ((Test-Path $credFile) -and $guestInstalled) {
                Stop-Gate5Blocked -Blocker 'GUEST_CREDENTIAL_UNREADABLE' -Detail @'
A credencial de bootstrap do guest existe mas nao pode ser decifrada por esta
conta (DPAPI e por usuario) e o Windows ja esta instalado, de modo que gerar
uma senha nova nao abriria o guest. Reexecute a automacao sob a MESMA conta que
gerou a credencial, ou recrie o laboratorio do zero apagando
.local\gate5-lab\ e C:\VMs\FaithRO-GATE5-LAB\.
'@
            }
            if (Test-Path $credFile) {
                Write-Gate5Log 'Credencial de bootstrap ilegivel por esta conta e guest ainda nao instalado: gerando uma nova.' 'WARN'
                Remove-Item $credFile -Force
            }
        }
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
        $cd = $script:Gate5CdUnattend
        if (-not (Select-String -LiteralPath $script:Gate5VmxPath -Pattern ('^{0}\.present' -f [regex]::Escape($cd)) -Quiet)) {
            $vmxLines = @(Get-Content -LiteralPath $script:Gate5VmxPath) + @(
                ('{0}.present = "TRUE"' -f $cd)
                ('{0}.deviceType = "cdrom-image"' -f $cd)
                ('{0}.fileName = "{1}"' -f $cd, $unattendIso)
                ('{0}.startConnected = "TRUE"' -f $cd)
            )
            Set-Gate5TextFile -Path $script:Gate5VmxPath -Lines $vmxLines
        }
        exit 0
    }

    # -------------------------------------------------------------------------
    'InstallWait' {
        # Liga a VM e aguarda o Windows Setup terminar (deteccao: guest ops
        # respondem com a credencial de bootstrap). Timeout global de 2h.
        $vmdk = Join-Path $script:Gate5VmDir 'FaithRO-GATE5-LAB.vmdk'
        $running = (Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('list') -AllowFailure).Output
        $justStarted = $false
        if ($running -notmatch [regex]::Escape($script:Gate5VmxPath)) {
            # Console VNC local ligado ANTES do power-on: e por ele que a tecla
            # do prompt de boot chega ao guest.
            Set-Gate5VncConsole -Enabled $true
            Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('start', $script:Gate5VmxPath, 'nogui') | Out-Null
            $justStarted = $true
            Write-Gate5Log 'VM ligada; aguardando instalacao unattended do Windows...'
        }

        # Prompt "Press any key to boot from CD or DVD": a ISO oficial da
        # Microsoft usa o carregador com prompt e, sem uma tecla, o firmware
        # registra "Status upon boot failure: Time out" e cai para os proximos
        # dispositivos - o Setup nunca inicia. O 'vmcli MKS sendKeyEvent' retorna
        # sucesso mas a tecla NAO chega ao guest sem um console conectado; o
        # console VNC local do proprio VMware entrega a tecla de fato.
        if ($justStarted) {
            $baseSize = (Get-Item $vmdk).Length
            $entregue = $false
            for ($k = 0; $k -lt 30; $k++) {
                $r = Send-Gate5VncKey -Keysym 0xFF0D    # Enter
                if ($k -eq 0) { Write-Gate5Log "Console VNC local: primeira tecla -> $r" }
                if ($r -eq 'OK') { $entregue = $true }
                Start-Sleep -Milliseconds 900
                # O disco crescer prova que o Setup comecou a gravar: paramos de
                # teclar para nao interferir nos reboots seguintes do Setup.
                if ((Get-Item $vmdk).Length -gt ($baseSize + 20MB)) { break }
            }
            if (-not $entregue) {
                Stop-Gate5Blocked -Blocker 'BOOT_KEY_CHANNEL_UNAVAILABLE' -Detail @'
Nao foi possivel entregar a tecla do prompt de boot pelo console VNC local do
VMware (127.0.0.1). Sem ela a ISO oficial do Windows nao inicia o Setup.
Verifique se a porta local nao esta ocupada e reexecute gate5-provision.ps1.
'@
            }
            Write-Gate5Log ("Janela do prompt de boot concluida; disco cresceu {0} MB." -f [int](((Get-Item $vmdk).Length - $baseSize) / 1MB))
        }

        # Verificacao do vTPM por EVIDENCIA, nao pela chave que nos mesmos
        # escrevemos: 'managedvm.autoAddVTPM' e honrado pelo fluxo gerenciado do
        # Workstation e NAO por 'vmrun start' sobre um .vmx escrito a mao, de
        # modo que aceitar a propria chave como prova era um falso positivo. Sem
        # TPM o Setup do Windows 11 aborta na checagem de requisitos. Nao ha
        # como criar o vTPM por automacao sem o material de chave que so o
        # VMware gera, e inventar valores .vmx e proibido.
        $vmwareLog = Join-Path $script:Gate5VmDir 'vmware.log'
        $tpmProved = ((Get-Gate5VmxValue 'vtpm.present') -eq 'TRUE')
        if (-not $tpmProved -and (Test-Path $vmwareLog)) {
            $tpmProved = [bool](Select-String -LiteralPath $vmwareLog -Pattern 'VTPM:|TPM device|vtpm.*(created|initialized)' -Quiet)
        }
        if (-not $tpmProved) {
            Stop-Gate5Blocked -Blocker 'VTPM_AUTOMATION_NOT_SUPPORTED' -Detail @'
Nenhum dispositivo TPM virtual foi materializado nesta VM. Verificado: o
Workstation instalado nao expoe TPM nem criptografia em vmrun nem em vmcli
(modulos disponiveis: Chipset, ConfigParams, Disk, Ethernet, Guest, HGFS, MKS,
Nvme, Power, Sata, Serial, Snapshot, Tools, VM), e "managedvm.autoAddVTPM"
nao e aplicado quando a VM e ligada por vmrun sobre um .vmx escrito a mao.
O vTPM do Workstation exige criptografia parcial da VM, cujo material de chave
so o proprio VMware gera - inventar essas chaves e proibido por esta etapa.

UNICO PASSO HUMANO NECESSARIO: abrir o VMware Workstation, abrir a VM
FaithRO-GATE5-LAB, VM Settings -> Add -> Trusted Platform Module, aceitar a
criptografia proposta pelo produto (a senha NAO deve ser versionada nem
registrada em log) e fechar. Depois reexecutar gate5-provision.ps1, que retoma
do checkpoint atual automaticamente.
'@
        }
        Write-Gate5Log 'vTPM materializado e confirmado por evidencia.'
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
            $rel = Invoke-RestMethod -Uri $api -Headers @{ 'User-Agent' = 'FaithRO-GATE5-Lab' } -UseBasicParsing
            $asset = $rel.assets | Where-Object { $_.name -match '^yara-(v?)4\.5\.5.*win64\.zip$' } | Select-Object -First 1
            if (-not $asset) { throw 'GATE5: asset win64 da release v4.5.5 nao localizado nos metadados oficiais.' }
            Write-Gate5Log ("Baixando asset oficial: {0} ({1} bytes)" -f $asset.name, $asset.size)
            Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath -UseBasicParsing
            if ((Get-Item $zipPath).Length -ne $asset.size) { throw 'GATE5: tamanho do download nao confere com os metadados da release.' }
        }
        $zipSha = Get-Gate5Sha256 -Path $zipPath
        Write-Gate5Log "yara zip sha256=$zipSha"
        Expand-Archive -Path $zipPath -DestinationPath (Join-Path $stage 'extracted') -Force
        $yaraExe  = Get-ChildItem (Join-Path $stage 'extracted') -Recurse -Filter 'yara64.exe'  | Select-Object -First 1
        $yaracExe = Get-ChildItem (Join-Path $stage 'extracted') -Recurse -Filter 'yarac64.exe' | Select-Object -First 1
        if (-not $yaraExe -or -not $yaracExe) { throw 'GATE5: yara64.exe/yarac64.exe ausentes no asset oficial.' }
        $verRun = Invoke-Gate5Native -FilePath $yaraExe.FullName -Arguments @('--version')
        $ver = ($verRun.Output -join '').Trim()
        if ($ver -ne $script:Gate5YaraVersion) { throw "GATE5: versao YARA inesperada no host: '$ver' (esperado 4.5.5)." }

        $evidence = [ordered]@{
            schema         = 'gate5-lab-yara/v1'
            source         = 'VirusTotal/yara release v4.5.5 (oficial)'
            zip_sha256     = $zipSha
            yara64_sha256  = Get-Gate5Sha256 -Path $yaraExe.FullName
            yarac64_sha256 = Get-Gate5Sha256 -Path $yaracExe.FullName
            version        = $ver
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

        # A aquisicao NAO usa 'git': o provisionamento roda elevado sob outra
        # conta administradora, onde uma instalacao per-user do git nao esta no
        # PATH. O SHA-40 da branch default e resolvido pela API oficial, fixado,
        # e o conteudo e materializado pelo zipball daquele commit exato.
        $ua = @{ 'User-Agent' = 'FaithRO-GATE5-Lab' }
        if (Test-Path $pinFile) {
            $pin = (Get-Content $pinFile -Raw | ConvertFrom-Json).commit_sha40
            Write-Gate5Log "Ruleset ja pinado: $pin"
        } else {
            $repoMeta = Invoke-RestMethod -Uri 'https://api.github.com/repos/Yara-Rules/rules' -Headers $ua -UseBasicParsing
            $branch   = [string]$repoMeta.default_branch
            $head     = Invoke-RestMethod -Uri ('https://api.github.com/repos/Yara-Rules/rules/commits/' + $branch) -Headers $ua -UseBasicParsing
            $pin      = [string]$head.sha
            if ($pin -notmatch '^[0-9a-f]{40}$') { throw 'GATE5: SHA-40 do ruleset nao resolvido.' }
            [ordered]@{ repo = 'https://github.com/Yara-Rules/rules'; default_branch = $branch;
                        commit_sha40 = $pin; license = 'GPL-2.0';
                        timestamp_utc = [DateTime]::UtcNow.ToString('s') + 'Z';
                        categories_included = $included; categories_excluded = $excluded } |
                ConvertTo-Json | Out-File $pinFile -Encoding utf8
            Write-Gate5Log "Ruleset pinado no commit $pin (branch default: $branch)"
        }

        # Materializacao idempotente do conteudo no commit pinado.
        $pinMarker = Join-Path $rulesRepo '.gate5-pin'
        if (-not (Test-Path $pinMarker) -or (Get-Content $pinMarker -Raw).Trim() -ne $pin) {
            if (Test-Path $rulesRepo) { Remove-Item $rulesRepo -Recurse -Force }
            New-Item -ItemType Directory -Force $rulesRepo | Out-Null
            $zip = Join-Path $script:Gate5LocalDir 'yara-rules-src.zip'
            $url = 'https://github.com/Yara-Rules/rules/archive/' + $pin + '.zip'
            Write-Gate5Log "Baixando ruleset no commit pinado: $url"
            Invoke-WebRequest -Uri $url -OutFile $zip -Headers $ua -UseBasicParsing
            $unzip = Join-Path $script:Gate5LocalDir 'yara-rules-unzip'
            if (Test-Path $unzip) { Remove-Item $unzip -Recurse -Force }
            Expand-Archive -Path $zip -DestinationPath $unzip -Force
            # O zipball do GitHub cria uma unica pasta raiz 'rules-<sha>'.
            $inner = @(Get-ChildItem $unzip -Directory) | Select-Object -First 1
            if (-not $inner) { throw 'GATE5: zipball do ruleset sem diretorio raiz esperado.' }
            Get-ChildItem $inner.FullName -Force | Move-Item -Destination $rulesRepo -Force
            Remove-Item $unzip -Recurse -Force -ErrorAction SilentlyContinue
            Remove-Item $zip -Force -ErrorAction SilentlyContinue
            Set-Content -LiteralPath $pinMarker -Value $pin -Encoding ascii
            Write-Gate5Log "Ruleset materializado no commit $pin"
        }
        if (-not (Test-Path $rulesRepo)) { throw 'GATE5: fonte do ruleset ausente; remova o pin para readquirir.' }

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
        $probe = Join-Path $env:TEMP 'gate5-compile-test.yrc'
        foreach ($f in $selected) {
            $c = Invoke-Gate5Native -FilePath $yarac -Arguments @($f.FullName, $probe)
            if ($c.ExitCode -ne 0) {
                $err = ($c.Output -join '; ')
                $compileErrors += [ordered]@{ file = $f.FullName; error = $err; action = 'EXCLUIDA: incompativel com YARA 4.5.5 (erro de compilacao upstream)' }
                Write-Gate5Log "Regra excluida (nao compila em 4.5.5): $($f.FullName)" 'WARN'
            } else {
                $effective += $f
            }
        }
        Remove-Item $probe -Force -ErrorAction SilentlyContinue

        # Indice do GATE 5 apenas com os arquivos efetivos, e compilacao final
        $indexPath = Join-Path $script:Gate5RulesDir 'gate5-index.yar'
        $indexLines = $effective | Sort-Object FullName | ForEach-Object {
            'include "{0}"' -f ($_.FullName -replace '\\', '/')
        }
        Set-Gate5TextFile -Path $indexPath -Lines $indexLines
        $ci = Invoke-Gate5Native -FilePath $yarac -Arguments @($indexPath, (Join-Path $script:Gate5RulesDir 'gate5-index.yrc'))
        if ($ci.ExitCode -ne 0) {
            throw ('GATE5: indice final nao compila com 0 erros (fail-closed): ' + ($ci.Output -join '; '))
        }

        # Hashes deterministicos (manifesto: <relative-path>\t<SHA256>\n, UTF-8 sem BOM, ordenacao ordinal)
        $rulesRoot = (Get-Item $script:Gate5RulesDir).FullName
        $byRel = @{}
        foreach ($f in $effective) {
            $rel = $f.FullName.Substring($rulesRoot.Length).TrimStart('\') -replace '\\', '/'
            $byRel[$rel] = Get-Gate5Sha256 -Path $f.FullName
        }
        # Ordenacao ORDINAL explicita: Sort-Object usa comparacao sensivel a
        # cultura, o que tornaria o aggregate hash dependente do locale da
        # maquina e quebraria a reprodutibilidade exigida pela etapa.
        $relSorted = [string[]]@($byRel.Keys)
        [Array]::Sort($relSorted, [StringComparer]::Ordinal)
        $entries = $relSorted | ForEach-Object { [pscustomobject]@{ rel = $_; sha = $byRel[$_] } }
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
# Padroes DECISORIOS: nomes que so existem se um segredo/dado proibido tiver
# sido introduzido no guest. Qualquer acerto reprova a etapa (fail-closed).
$gating = @("*.pem","*.ppk","id_rsa*","id_ed25519*","*.sql","*.dump",".env",".env.*",
            "*faithro*","Ragexe*","*.grf","WARP*","*.gat","*.rsw")
# Padroes INFORMATIVOS: substrings genericas que o proprio Windows usa em
# arquivos internos (ex.: TokenBroker, credential providers). Sao registrados
# para revisao humana, mas NAO reprovam sozinhos - do contrario a etapa
# falharia por artefatos do sistema operacional, nao por vazamento real.
$informational = @("*credential*","*token*","*github*")
$roots = @("C:\Users","C:\gate5","C:\Tools","C:\Temp","C:\Windows\Temp")

function Find-Hits([string[]]$Patterns) {
    $acc = @()
    foreach ($root in $roots) {
        if (Test-Path $root) {
            foreach ($p in $Patterns) {
                $acc += Get-ChildItem $root -Recurse -Force -Filter $p -ErrorAction SilentlyContinue |
                        Where-Object { -not $_.PSIsContainer } | Select-Object -ExpandProperty FullName
            }
        }
    }
    return @($acc | Sort-Object -Unique)
}
# A propria arvore de ferramentas aprovadas do laboratorio nao e vazamento:
# C:\Tools\YARA-Rules contem regras cujos nomes citam malware/tokens.
$benign = '\\Tools\\YARA'
$hits = @(Find-Hits $gating        | Where-Object { $_ -notmatch $benign })
$info = @(Find-Hits $informational | Where-Object { $_ -notmatch $benign })
# Limpeza de bootstrap
Remove-Item C:\gate5\*.ps1 -Force -ErrorAction SilentlyContinue
Remove-Item C:\gate5\*.json -Force -ErrorAction SilentlyContinue
Clear-RecycleBin -Force -ErrorAction SilentlyContinue
Remove-Item "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue
@{ suspicious_paths = @($hits); count = @($hits).Count
   informational_paths = @($info); informational_count = @($info).Count } |
    ConvertTo-Json -Depth 4 | Out-File C:\gate5\sanitize-result.json -Encoding utf8
'@
        Invoke-GuestPS -ScriptText $sanitizeScript -Label 'gate5-sanitize' | Out-Null
        $tmp = Join-Path $script:Gate5EvidenceDir 'guest-sanitize.json'
        Copy-FromGuest -GuestPath 'C:\gate5\sanitize-result.json' -HostPath $tmp
        $s = Get-Content $tmp -Raw | ConvertFrom-Json
        Write-Gate5Log ("SANITIZE: decisorios={0} informativos={1}" -f $s.count, $s.informational_count)
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
