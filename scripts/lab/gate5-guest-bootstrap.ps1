# gate5-guest-bootstrap.ps1 - Fases de bootstrap do guest FaithRO-GATE5-LAB.
# Chamado pelo entrypoint gate5-provision.ps1 com -Phase <fase>.
# Fases: Unattend | InstallWait | Updates | Defender | Vcruntime | Yara | Rules | Sanitize
#
# Credenciais do guest: geradas em runtime, gravadas SOMENTE em
# .local\gate5-lab\secrets\guest-credential.xml (Export-Clixml, DPAPI do
# usuario atual). Nunca em Git, nunca em log, nunca em relatorio.

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('Unattend','InstallWait','Updates','Defender','Vcruntime','Yara','Rules','Sanitize')]
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
        # Idempotencia: com a VM ligada, a midia ja esta montada e em uso pelo
        # Setup - regenerar a ISO falharia (arquivo bloqueado) e, pior, trocaria
        # o payload sob os pes de uma instalacao em andamento.
        if ((Test-Gate5VmPoweredOn) -and (Test-Path $unattendIso)) {
            $tplPath = Join-Path $PSScriptRoot 'templates\Autounattend.template.xml'
            $midiaAtual = (Get-Item $unattendIso).LastWriteTimeUtc -ge (Get-Item $tplPath).LastWriteTimeUtc
            if ($midiaAtual) {
                Write-Gate5Log 'VM em execucao com a midia ja anexada e atualizada: fase Unattend nada a fazer.'
                exit 0
            }
            # Template mais novo que a midia: e preciso reconstruir, e isso so e
            # possivel com a VM desligada (a ISO esta montada). Aguardamos o
            # power-off aqui para que um unico ciclo do operador baste.
            Write-Gate5Log 'Template mais novo que a midia: reconstrucao necessaria com a VM desligada.' 'WARN'
            Write-Gate5Log 'HUMAN_ACTION_REQUIRED POWER_CYCLE_VM' 'GATE'
            Write-Host ''
            Write-Host 'HUMAN_ACTION_REQUIRED'
            Write-Host 'action=POWER_CYCLE_VM'
            Write-Host 'Na interface do VMware: Power -> Power Off, aguarde desligar, e Power on.'
            Write-Host 'A automacao reconstroi a midia enquanto a VM estiver desligada e age sozinha no boot.'
            Write-Host ''
            $ate = [DateTime]::UtcNow.AddMinutes(30)
            while ([DateTime]::UtcNow -lt $ate -and (Test-Gate5VmPoweredOn)) { Start-Sleep -Seconds 3 }
            if (Test-Gate5VmPoweredOn) {
                Stop-Gate5Human -Action 'POWER_CYCLE_VM' -Detail 'A VM nao foi desligada em 30 minutos. Reexecute gate5-provision.ps1 quando puder faze-lo.'
            }
            Write-Gate5Log 'VM desligada; reconstruindo a midia com o template corrigido.'
        }

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
        if (Test-Path $stageDir) { Remove-Item $stageDir -Recurse -Force }
        New-Item -ItemType Directory -Force $stageDir | Out-Null
        Set-Content -Path (Join-Path $stageDir 'Autounattend.xml') -Value $rendered -Encoding utf8

        # 2b) Payload da MIDIA CONTROLADA. Sem guest operations do vmrun (VM
        # criptografada, docs/48 §12), tudo o que o guest precisa viaja nesta
        # ISO e e instalado pelo proprio script que o Windows Setup dispara.
        $payloadDir = Join-Path $stageDir 'gate5'
        New-Item -ItemType Directory -Force (Join-Path $payloadDir 'yara')  | Out-Null
        New-Item -ItemType Directory -Force (Join-Path $payloadDir 'rules') | Out-Null
        New-Item -ItemType Directory -Force (Join-Path $payloadDir 'vcredist') | Out-Null
        Copy-Item (Join-Path $PSScriptRoot 'guest\gate5-payload.ps1') $payloadDir -Force
        Set-Content -Path (Join-Path $payloadDir 'payload-marker.txt') -Value 'FaithRO-GATE5-LAB payload' -Encoding ascii
        foreach ($bin in 'yara64.exe', 'yarac64.exe') {
            $src = Join-Path $script:Gate5YaraDir $bin
            if (-not (Test-Path $src)) { throw "GATE5: $bin ausente em $($script:Gate5YaraDir); execute a fase Yara antes." }
            Copy-Item $src (Join-Path $payloadDir 'yara') -Force
        }
        if (-not (Test-Path (Join-Path $script:Gate5RulesDir 'gate5-index.yar'))) {
            throw 'GATE5: ruleset nao preparado; execute a fase Rules antes.'
        }
        Copy-Item (Join-Path $script:Gate5RulesDir '*') (Join-Path $payloadDir 'rules') -Recurse -Force

        # Runtime do Visual C++: embarcado na midia como PACOTE OFICIAL assinado.
        # O guest instala silenciosamente antes de tocar no YARA. Copiar DLL solta
        # do host seria mais simples e esta PROIBIDO (docs/48 SS13).
        $vcExeStage = Join-Path (Join-Path $script:Gate5LocalDir 'vcredist-stage') 'vc_redist.x64.exe'
        $vcPinFile  = Join-Path $script:Gate5EvidenceDir 'vcruntime-pin.json'
        if (-not (Test-Path $vcExeStage) -or -not (Test-Path $vcPinFile)) {
            throw 'GATE5: redistribuivel do Visual C++ ausente; execute a fase Vcruntime antes.'
        }
        # Reverificacao na hora de embarcar: o pin so vale se o arquivo que entra
        # na midia for o MESMO que foi assinado e hasheado na aquisicao.
        $vcPinObj = Get-Content $vcPinFile -Raw | ConvertFrom-Json
        $vcShaNow = Get-Gate5Sha256 -Path $vcExeStage
        if ($vcShaNow -ne $vcPinObj.sha256) {
            Stop-Gate5Blocked -Blocker 'VCRUNTIME_HASH_MISMATCH' -Detail @"
O artefato do staging mudou depois da aquisicao e NAO foi embarcado.
  pin   = $($vcPinObj.sha256)
  atual = $vcShaNow
"@
        }
        Copy-Item $vcExeStage (Join-Path $payloadDir 'vcredist') -Force
        Copy-Item $vcPinFile  (Join-Path $payloadDir 'vcredist\vcruntime-pin.json') -Force

        # Pin do ruleset na midia: sem ele o guest consegue contar arquivos, mas
        # nao PROVAR que o conjunto entregue e o commit pinado - foi o que deixou
        # ruleset_pinned sem verificacao na primeira instalacao limpa. Vai o
        # commit SHA-40, o agregado e o manifesto <rel, sha> completo, para que o
        # guest recompute o agregado com a mesma regra do host.
        $rulesEvFile = Join-Path $script:Gate5EvidenceDir 'ruleset.json'
        if (-not (Test-Path $rulesEvFile)) { throw 'GATE5: evidencia do ruleset ausente; execute a fase Rules antes.' }
        $rulesEv = Get-Content $rulesEvFile -Raw | ConvertFrom-Json
        if ([string]$rulesEv.commit_sha40 -notmatch '^[0-9a-f]{40}$') { throw 'GATE5: pin do ruleset sem SHA-40 valido.' }
        # Fora da pasta 'rules': o que estiver la dentro e copiado para
        # C:\Tools\YARA-Rules e entraria no proprio conjunto que ele descreve.
        [ordered]@{
            schema           = 'gate5-lab-ruleset-pin/v1'
            repo             = 'https://github.com/Yara-Rules/rules'
            commit_sha40     = $rulesEv.commit_sha40
            file_count       = $rulesEv.file_count
            aggregate_sha256 = $rulesEv.aggregate_sha256
            files            = @($rulesEv.files)
        } | ConvertTo-Json -Depth 5 | Out-File (Join-Path $payloadDir 'rules-pin.json') -Encoding utf8
        $payloadFiles = @(Get-ChildItem $payloadDir -Recurse -File)
        Write-Gate5Log ("Payload da midia: {0} arquivos, {1:N1} MB" -f $payloadFiles.Count, (($payloadFiles | Measure-Object Length -Sum).Sum / 1MB))

        # 3) Gerar ISO auxiliar com IMAPI2FS (COM nativo do Windows, sem downloads)
        $fsi = New-Object -ComObject IMAPI2FS.MsftFileSystemImage
        $fsi.FileSystemsToCreate = 3   # ISO9660 + Joliet
        $fsi.VolumeName = 'GATE5UNATTEND'
        $fsi.Root.AddTree($stageDir, $false)
        $img = $fsi.CreateResultImage()
        $stream = $img.ImageStream
        Remove-Item $unattendIso -Force -ErrorAction SilentlyContinue
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
        if (-not (Test-Path $unattendIso)) { throw 'GATE5: falha ao gerar ISO de unattend.' }

        # O IMAPI mantem handles abertos na arvore de origem enquanto os objetos
        # COM vivem; liberar antes de apagar o staging, com repeticao curta para
        # o caso de um antivirus ainda estar lendo os arquivos recem-gravados.
        foreach ($com in $stream, $img, $fsi) {
            try { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($com) } catch {}
        }
        [GC]::Collect(); [GC]::WaitForPendingFinalizers()
        for ($try = 1; $try -le 5; $try++) {
            try { Remove-Item $stageDir -Recurse -Force -ErrorAction Stop; break }
            catch { if ($try -eq 5) { Write-Gate5Log "staging nao removido ($stageDir): $($_.Exception.Message)" 'WARN' } else { Start-Sleep -Seconds 2 } }
        }
        Write-Gate5Log "ISO de unattend gerada: $unattendIso (sera destruida na fase Sanitize)."

        # 4) Anexar como segundo CD-ROM no VMX (VM precisa estar desligada)
        # Chave a chave: se a VM ja estiver criptografada (vTPM adicionado), o
        # .vmx nao pode ser reescrito por inteiro sem destruir a criptografia.
        $cd = $script:Gate5CdUnattend
        Set-Gate5VmxEntry -Name ('{0}.present' -f $cd)         -Value 'TRUE'          -Vmware $vmware
        Set-Gate5VmxEntry -Name ('{0}.deviceType' -f $cd)      -Value 'cdrom-image'   -Vmware $vmware
        Set-Gate5VmxEntry -Name ('{0}.fileName' -f $cd)        -Value $unattendIso    -Vmware $vmware
        Set-Gate5VmxEntry -Name ('{0}.startConnected' -f $cd)  -Value 'TRUE'          -Vmware $vmware
        Write-Gate5Log "ISO de unattend anexada em $cd."

        # Canal de evidencia: porta serial do guest gravando num arquivo do host.
        # E um canal de SAIDA de mao unica (o guest escreve, o host le), que
        # substitui as guest operations indisponiveis na VM criptografada. Nao
        # transporta segredo - apenas metadados de validacao.
        Set-Gate5VmxEntry -Name 'serial0.present'        -Value 'TRUE'                       -Vmware $vmware
        Set-Gate5VmxEntry -Name 'serial0.fileType'       -Value 'file'                       -Vmware $vmware
        Set-Gate5VmxEntry -Name 'serial0.fileName'       -Value $script:Gate5EvidenceSerial  -Vmware $vmware
        Set-Gate5VmxEntry -Name 'serial0.startConnected' -Value 'TRUE'                       -Vmware $vmware
        Set-Gate5VmxEntry -Name 'serial0.yieldOnMsrRead' -Value 'TRUE'                       -Vmware $vmware
        if (Test-Path $script:Gate5EvidenceSerial) { Remove-Item $script:Gate5EvidenceSerial -Force }
        Write-Gate5Log "Canal serial de evidencia: $($script:Gate5EvidenceSerial)"
        exit 0
    }

    # -------------------------------------------------------------------------
    'InstallWait' {
        # VM criptografada (exigencia do vTPM): 'vmrun' nao pode liga-la sem a
        # senha, que pertence exclusivamente ao operador. As operacoes de energia
        # sao GATES HUMANOS formais na interface do VMware; tudo o que vem depois
        # e validado tecnicamente aqui - a confirmacao textual do operador nunca
        # e aceita como prova. Ver docs/48 §12.
        $vmdk  = Join-Path $script:Gate5VmDir 'FaithRO-GATE5-LAB.vmdk'
        $state = Get-Gate5State
        $bootKeySent = $false
        if ($state.notes.PSObject.Properties['boot_key_sent']) { $bootKeySent = [bool]$state.notes.boot_key_sent }

        function Get-VmUptimeSeconds {
            $p = @(Get-Process -Name 'vmware-vmx' -ErrorAction SilentlyContinue) | Select-Object -First 1
            if ($p) { return ((Get-Date) - $p.StartTime).TotalSeconds }
            return 0
        }
        function Set-Gate5InstallNote {
            param([string]$Nome, $Valor)
            $state.notes | Add-Member -NotePropertyName $Nome -NotePropertyValue $Valor -Force
            Save-Gate5State $state
        }
        function Assert-Gate5PreConditions {
            # Fail-closed antes de gastar um gate humano: midia invalida faria a
            # instalacao parar numa tela, como ja aconteceu com o Autounattend
            # sem <ProductKey>.
            $midia = Test-Gate5UnattendMedia
            $ruins = @($midia.PSObject.Properties |
                       Where-Object { $_.Name -ne 'iso_bytes' -and $_.Value -ne $true } |
                       ForEach-Object { $_.Name })
            if ($ruins.Count -gt 0) {
                Stop-Gate5Blocked -Blocker 'UNATTEND_MEDIA_INVALID' -Detail ("controles reprovados: " + ($ruins -join ', '))
            }
            if ((Get-Gate5VmxValue 'serial0.fileType') -ne 'file' -or
                (Get-Gate5VmxValue 'serial0.fileName') -ne $script:Gate5EvidenceSerial) {
                Stop-Gate5Blocked -Blocker 'SERIAL_CHANNEL_NOT_READY' -Detail 'porta serial da VM nao aponta para o arquivo de evidencia do host'
            }
            if ((Get-Gate5VmxValue 'RemoteDisplay.vnc.ip') -ne '127.0.0.1') {
                Stop-Gate5Blocked -Blocker 'VNC_NOT_LOCAL' -Detail 'console temporario precisa estar preso a 127.0.0.1'
            }
            Write-Gate5Log ("Midia e canais validados ({0:N1} MB): Autounattend na raiz, chave vazia, payload completo." -f ($midia.iso_bytes / 1MB))
        }

        # --- 0) Evidencia ja recebida? ---------------------------------------
        $ev = Get-Gate5SerialEvidence
        if ($ev) {
            $destino = Join-Path $script:Gate5EvidenceDir 'guest-evidence.json'
            ($ev | ConvertTo-Json -Depth 6) | Out-File $destino -Encoding utf8
            Write-Gate5Log 'Guest ja reportou evidencia pela serial; instalacao concluida.'
            exit 0
        }

        # --- 1) Sessao antiga: VM ligada fora da janela e sem tecla entregue --
        # Essa instalacao e descartavel; esperamos o operador desliga-la para que
        # o proximo boot comece limpo e dentro da janela do prompt optico.
        if ((Test-Gate5VmPoweredOn) -and -not $bootKeySent -and (Get-VmUptimeSeconds) -gt 150) {
            Assert-Gate5PreConditions
            Write-Gate5Log 'HUMAN_ACTION_REQUIRED POWER_CYCLE_VM' 'GATE'
            Write-Host ''
            Write-Host 'HUMAN_ACTION_REQUIRED'
            Write-Host 'action=POWER_CYCLE_VM'
            Write-Host 'Na interface do VMware: Power -> Power Off, aguarde desligar, e Power on.'
            Write-Host 'Nao interaja com a instalacao: ela e desassistida.'
            Write-Host 'A automacao esta AGUARDANDO e agira sozinha na janela do boot.'
            Write-Host ''
            Set-Gate5InstallNote 'installation_stage' 'WAITING_POWER_CYCLE'
            $ate = [DateTime]::UtcNow.AddMinutes(30)
            while ([DateTime]::UtcNow -lt $ate -and (Test-Gate5VmPoweredOn)) { Start-Sleep -Seconds 3 }
            if (Test-Gate5VmPoweredOn) {
                Stop-Gate5Human -Action 'POWER_CYCLE_VM' -Detail 'A VM nao foi desligada em 30 minutos. Reexecute gate5-provision.ps1 quando puder faze-lo.'
            }
            Write-Gate5Log 'VM desligada; aguardando o novo power-on.'
        }

        # --- 2) Aguardar o power-on -------------------------------------------
        if (-not (Test-Gate5VmPoweredOn)) {
            if ((Get-Gate5State).notes.installation_stage -ne 'WAITING_POWER_CYCLE') { Assert-Gate5PreConditions }
            Write-Gate5Log 'HUMAN_ACTION_REQUIRED POWER_ON_VM' 'GATE'
            Write-Host ''
            Write-Host 'HUMAN_ACTION_REQUIRED'
            Write-Host 'action=POWER_ON_VM'
            Write-Host 'Ligue a VM na interface do VMware (Power on this virtual machine).'
            Write-Host 'A automacao esta AGUARDANDO o power-on e agira sozinha na janela do boot.'
            Write-Host ''
            Set-Gate5InstallNote 'installation_stage' 'WAITING_POWER_ON'
            $ate = [DateTime]::UtcNow.AddMinutes(30)
            while ([DateTime]::UtcNow -lt $ate -and -not (Test-Gate5VmPoweredOn)) { Start-Sleep -Seconds 3 }
            if (-not (Test-Gate5VmPoweredOn)) {
                Stop-Gate5Human -Action 'POWER_ON_VM' -Detail 'A VM nao foi ligada em 30 minutos. Reexecute gate5-provision.ps1 quando puder liga-la.'
            }
        }
        Write-Gate5Log ("Power-on detectado (uptime {0:N0}s)." -f (Get-VmUptimeSeconds))

        # --- 3) Janela do boot optico, com verificacao VISUAL ------------------
        # A tecla so e enviada quando o framebuffer mostra a fase de firmware
        # (tela preta de texto). No Windows Setup uma tecla poderia acionar um
        # botao em foco, e por isso nunca e enviada la.
        if ($bootKeySent) {
            Write-Gate5Log 'Tecla de boot ja entregue nesta instalacao: nenhuma nova sera enviada (boot pelo disco esperado).'
        } else {
            # 'boot_key_sent' significa "o boot optico REALMENTE disparou", nao
            # "uma tecla foi enviada": marcar no envio gastava a unica tecla numa
            # tela preta anterior ao prompt e, quando o prompt aparecia, ja nao
            # restava tecla. O prompt e respondido sempre que aparecer, ate o
            # Setup comecar a gravar no disco - so entao o estado e fixado e
            # nenhuma tecla e enviada nos reboots seguintes.
            $tela      = Join-Path $script:Gate5EvidenceDir 'boot-window.png'
            $discoBase = (Get-Item $vmdk).Length
            $ate       = [DateTime]::UtcNow.AddMinutes(10)
            $instalando = $false
            while ([DateTime]::UtcNow -lt $ate -and -not $instalando) {
                $cap = Save-Gate5VncScreenshot -Path $tela
                if ($cap -ne 'OK') {
                    Write-Gate5Log "Captura do console falhou: $cap" 'WARN'
                } else {
                    $scr = Test-Gate5BootPromptOnScreen -ImagePath $tela
                    if ($scr -and $scr.HasPrompt) {
                        $r = Send-Gate5VncKey -Keysym 0xFF0D
                        Write-Gate5Log ("Prompt de boot na tela (dark={0} topo={1}); tecla entregue: {2}" -f $scr.DarkFraction, $scr.BrightTop, $r)
                    }
                }
                if ((Get-Item $vmdk).Length -gt ($discoBase + 200MB)) { $instalando = $true }
                if (-not $instalando) { Start-Sleep -Seconds 2 }
            }
            if ($instalando) {
                $bootKeySent = $true
                Set-Gate5InstallNote 'boot_key_sent' $true
                Set-Gate5InstallNote 'installation_stage' 'DISK_BOOT_EXPECTED'
                Write-Gate5Log 'installation_stage=OPTICAL_BOOT_TRIGGERED -> DISK_BOOT_EXPECTED (Setup gravando no disco).'
            } else {
                Stop-Gate5Blocked -Blocker 'OPTICAL_BOOT_PROMPT_NOT_SEEN' -Detail @'
O Setup nao comecou a gravar no disco em 10 minutos apos o power-on. O prompt de
boot pelo CD foi respondido sempre que apareceu no console local; nenhuma tecla
e enviada fora dele. Refaca o power-cycle com a automacao ja aguardando.
'@
            }
        }

        # --- 4) Acompanhar a instalacao pelo canal serial ----------------------
        # O guest reinicia sozinho quantas vezes precisar; nenhuma tecla de boot
        # e enviada nesses reboots (boot_key_sent). O fim e sinalizado pela
        # chegada do bloco COMPLETO de evidencia na serial.
        $limite = [DateTime]::UtcNow.AddHours(4)
        while ([DateTime]::UtcNow -lt $limite) {
            $ev = Get-Gate5SerialEvidence
            if ($ev) {
                $destino = Join-Path $script:Gate5EvidenceDir 'guest-evidence.json'
                ($ev | ConvertTo-Json -Depth 6) | Out-File $destino -Encoding utf8
                Write-Gate5Log ("Evidencia recebida do guest: {0} build {1}" -f $ev.os_caption, $ev.os_build)
                Set-Gate5InstallNote 'installation_stage' 'GUEST_REPORTED'
                # A evidencia e gravada ANTES de qualquer decisao: um bloqueio
                # nao pode custar a prova que o justifica.
                $campos = @($ev.PSObject.Properties.Name)
                $blk = @()
                if ($campos -contains 'blockers') { $blk = @($ev.blockers) | Where-Object { $_ } }
                if ($blk.Count -gt 0) {
                    Stop-Gate5Blocked -Blocker ([string]$blk[0]) -Detail @"
Bloqueadores reportados pelo proprio guest: $($blk -join ', ')
Evidencia preservada em $destino
"@
                }
                # Criterios do baseline verificados dentro do guest. Reprovar aqui
                # evita seguir para isolamento e snapshot com um baseline invalido.
                $reprovados = @()
                if ($campos -contains 'yara_runtime_ok' -and -not $ev.yara_runtime_ok) { $reprovados += 'yara_4_5_5' }
                if ($campos -contains 'ruleset_pinned'  -and -not $ev.ruleset_pinned)  { $reprovados += 'ruleset_pinned' }
                if ($campos -contains 'sanitize_pass'   -and -not $ev.sanitize_pass)   { $reprovados += 'sanitize_pass' }
                if ($campos -contains 'tpm_2_0'         -and -not $ev.tpm_2_0)         { $reprovados += 'tpm_2_0' }
                if ($reprovados.Count -gt 0) {
                    Stop-Gate5Blocked -Blocker 'GUEST_BASELINE_CRITERIA_FAILED' -Detail @"
Criterios reprovados dentro do guest: $($reprovados -join ', ')
Evidencia preservada em $destino
"@
                }
                exit 0
            }
            if (-not (Test-Gate5VmPoweredOn)) {
                Start-Sleep -Seconds 60
                if (-not (Get-Gate5SerialEvidence)) {
                    Stop-Gate5Human -Action 'POWER_ON_VM' -Detail 'A VM desligou sem reportar evidencia. Ligue-a novamente pela interface do VMware e reexecute gate5-provision.ps1.'
                }
            }
            Start-Sleep -Seconds 60
        }
        throw 'GATE5: timeout (4h) aguardando a evidencia do guest pela serial.'
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
    'Vcruntime' {
        # Aquisicao HOST-side do redistribuivel OFICIAL do Visual C++ (x64), a
        # dependencia real do yara64.exe/yarac64.exe. Cada etapa falha fechado:
        # origem, assinatura, hash pinado. Nada e copiado do proprio host.
        $stage   = Join-Path $script:Gate5LocalDir 'vcredist-stage'
        New-Item -ItemType Directory -Force $stage | Out-Null
        $vcExe   = Join-Path $stage 'vc_redist.x64.exe'
        $pinFile = Join-Path $script:Gate5EvidenceDir 'vcruntime-pin.json'
        $pin     = if (Test-Path $pinFile) { Get-Content $pinFile -Raw | ConvertFrom-Json } else { $null }
        $urlEfetiva = if ($pin) { [string]$pin.effective_url } else { '' }

        if (-not (Test-Path $vcExe)) {
            if (-not (Test-Gate5MicrosoftSource -Uri $script:Gate5VcRedistUrl)) {
                Stop-Gate5Blocked -Blocker 'VCRUNTIME_SOURCE_NOT_MICROSOFT' `
                    -Detail ("URL declarada fora da allowlist Microsoft: " + $script:Gate5VcRedistUrl)
            }
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Write-Gate5Log ("Baixando o redistribuivel oficial do Visual C++: " + $script:Gate5VcRedistUrl)
            # HttpWebRequest em vez de Invoke-WebRequest: precisamos da URL
            # EFETIVA (ResponseUri) para provar que o redirecionamento do aka.ms
            # terminou num host da Microsoft, antes de gravar um unico byte.
            $req = [Net.HttpWebRequest]::Create($script:Gate5VcRedistUrl)
            $req.AllowAutoRedirect = $true
            $req.UserAgent = 'FaithRO-GATE5-Lab'
            $resp = $req.GetResponse()
            $urlEfetiva = $resp.ResponseUri.AbsoluteUri
            if (-not (Test-Gate5MicrosoftSource -Uri $urlEfetiva)) {
                $resp.Close()
                Stop-Gate5Blocked -Blocker 'VCRUNTIME_SOURCE_NOT_MICROSOFT' `
                    -Detail ("URL efetiva apos redirecionamento fora da allowlist Microsoft: " + $urlEfetiva)
            }
            $fs = [IO.File]::Create($vcExe)
            try { $resp.GetResponseStream().CopyTo($fs) } finally { $fs.Close(); $resp.Close() }
            Write-Gate5Log ("URL efetiva: " + $urlEfetiva)
        }

        $sig = Get-Gate5AuthenticodeMicrosoft -Path $vcExe
        if (-not $sig.Valid) {
            Remove-Item $vcExe -Force -ErrorAction SilentlyContinue
            Stop-Gate5Blocked -Blocker 'VCRUNTIME_SIGNATURE_INVALID' -Detail @"
Assinatura Authenticode recusada (artefato descartado).
  status  = $($sig.Status)
  subject = $($sig.Subject)
Exigido: status Valid E certificado emitido para a Microsoft Corporation.
"@
        }

        $vcSha  = Get-Gate5Sha256 -Path $vcExe
        $vcInfo = (Get-Item $vcExe).VersionInfo
        $vcVer  = [string]$vcInfo.ProductVersion
        if ($pin -and $pin.sha256 -and ($pin.sha256 -ne $vcSha)) {
            Stop-Gate5Blocked -Blocker 'VCRUNTIME_HASH_MISMATCH' -Detail @"
O artefato do staging nao confere com o pin registrado.
  pin      = $($pin.sha256)
  atual    = $vcSha
Apague $vcExe para readquirir a partir da fonte oficial, ou investigue a
divergencia antes de prosseguir.
"@
        }
        # A versao do pacote precisa cobrir o toolset com que o YARA 4.5.5 foi
        # compilado; um runtime mais antigo instalaria sem erro e ainda assim
        # deixaria o yara64.exe sem iniciar.
        $vcMajorMinor = $null
        if ($vcVer -match '^(\d+)\.(\d+)') { $vcMajorMinor = [Version]("{0}.{1}" -f $Matches[1], $Matches[2]) }
        if (-not $vcMajorMinor -or $vcMajorMinor -lt $script:Gate5VcRuntimeMinVersion) {
            Stop-Gate5Blocked -Blocker 'YARA_RUNTIME_DEPENDENCY_UNSATISFIED' -Detail @"
O redistribuivel obtido nao cobre o toolset exigido pelo YARA $($script:Gate5YaraVersion).
  versao do pacote = $vcVer
  minimo exigido   = $($script:Gate5VcRuntimeMinVersion)
"@
        }

        [ordered]@{
            schema           = 'gate5-lab-vcruntime/v1'
            source           = 'Microsoft Visual C++ Redistributable x64 (oficial)'
            declared_url     = $script:Gate5VcRedistUrl
            effective_url    = $urlEfetiva
            file_name        = 'vc_redist.x64.exe'
            size_bytes       = (Get-Item $vcExe).Length
            sha256           = $vcSha
            product_version  = $vcVer
            file_version     = [string]$vcInfo.FileVersion
            signature_status = $sig.Status
            signature_subject= $sig.Subject
            signature_thumbprint = $sig.Thumbprint
            min_runtime_version  = $script:Gate5VcRuntimeMinVersion.ToString()
            timestamp_utc    = [DateTime]::UtcNow.ToString('s') + 'Z'
        } | ConvertTo-Json | Out-File $pinFile -Encoding utf8
        Copy-Item $pinFile (Join-Path $script:Gate5EvidenceDir 'vcruntime.json') -Force
        Write-Gate5Log ("Redistribuivel do Visual C++ verificado e pinado: versao={0} sha256={1}" -f $vcVer, $vcSha)
        Write-Gate5Log 'Entrega ao guest sera feita pela midia controlada (sem copiar DLL do host).'
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

        # Espelho local em C:\Tools\YARA. A entrega ao guest NAO usa guest
        # operations do vmrun (indisponiveis em VM criptografada, ver docs/48
        # §12): os binarios vao no payload da ISO controlada e sao instalados
        # pelo proprio script que o Windows Setup executa dentro do guest.
        New-Item -ItemType Directory -Force $script:Gate5YaraDir | Out-Null
        Copy-Item $yaraExe.FullName  (Join-Path $script:Gate5YaraDir 'yara64.exe')  -Force
        Copy-Item $yaracExe.FullName (Join-Path $script:Gate5YaraDir 'yarac64.exe') -Force
        Write-Gate5Log 'YARA 4.5.5 verificado e preparado no host para entrega por midia controlada.'
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

        # O conjunto efetivo fica pronto no host; a entrega ao guest e feita pelo
        # payload da ISO controlada (sem guest operations do vmrun).
        Write-Gate5Log 'Ruleset pinado, compilado e preparado no host para entrega por midia controlada.'
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
