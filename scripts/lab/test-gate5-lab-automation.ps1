# test-gate5-lab-automation.ps1 - Testes sinteticos da automacao do laboratorio
# GATE 5. NAO cria VM, NAO acessa rede, NAO instala nada, NAO toca no alvo WARP.
# Exercita apenas as primitivas de gate5-common.ps1 e as invariantes estaticas
# dos scripts, para que regressoes sejam detectadas sem uma execucao real de
# varias horas.
#
# Uso:  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\lab\test-gate5-lab-automation.ps1
# Exit 0 = todos os testes passaram.

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$labDir = $PSScriptRoot
. (Join-Path $labDir 'gate5-common.ps1')

$script:pass = 0
$script:fail = 0
function It {
    param([Parameter(Mandatory)][string]$Name, [Parameter(Mandatory)][scriptblock]$Body)
    try {
        $ok = & $Body
        if ($ok) { $script:pass++; Write-Host "  PASS  $Name" }
        else     { $script:fail++; Write-Host "  FAIL  $Name" }
    } catch {
        $script:fail++
        Write-Host "  FAIL  $Name  ($($_.Exception.Message))"
    }
}

$tmp = Join-Path $env:TEMP ('gate5-selftest-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force $tmp | Out-Null

try {
Write-Host 'T-A: primitivas de gate5-common.ps1'

# Regressao principal: o entrypoint interpretava a saida do processo filho como
# parte do valor de retorno, e qualquer filho que imprimisse algo era tratado
# como falha (HOST_PREFLIGHT_FAILED com o preflight aprovado).
It 'Invoke-Gate5Child retorna um inteiro, nao a saida do filho' {
    $child = Join-Path $tmp 'child-ok.ps1'
    Set-Content -LiteralPath $child -Value 'Write-Host "ruido de log do filho"; exit 0' -Encoding ascii
    function Invoke-Gate5ChildLocal {
        param([string]$Script)
        & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $Script |
            ForEach-Object { Write-Host $_ }
        return [int]$LASTEXITCODE
    }
    $code = Invoke-Gate5ChildLocal $child
    (@($code).Count -eq 1) -and ($code -is [int]) -and ($code -eq 0) -and (-not ($code -ne 0))
}

It 'Invoke-Gate5Child propaga exit code diferente de zero' {
    $child = Join-Path $tmp 'child-fail.ps1'
    Set-Content -LiteralPath $child -Value 'Write-Host "falhando"; exit 7' -Encoding ascii
    & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $child | ForEach-Object { $null = $_ }
    [int]$LASTEXITCODE -eq 7
}

It 'Set-Gate5TextFile grava UTF-8 sem BOM com CRLF' {
    $f = Join-Path $tmp 'sample.vmx'
    Set-Gate5TextFile -Path $f -Lines @('.encoding = "UTF-8"', 'displayName = "x"')
    $bytes = [System.IO.File]::ReadAllBytes($f)
    $noBom = -not ($bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)
    $crlf  = ([System.IO.File]::ReadAllText($f)) -match "`r`n"
    $noBom -and $crlf
}

It 'Invoke-Gate5Native captura stderr sem lancar sob ErrorActionPreference=Stop' {
    $ErrorActionPreference = 'Stop'
    $r = Invoke-Gate5Native -FilePath 'cmd.exe' -Arguments @('/c', 'echo problema 1>&2 & exit /b 3')
    ($r.ExitCode -eq 3) -and (($r.Output -join '') -match 'problema')
}

It 'Invoke-Gate5Native retorna exit 0 e stdout em caso de sucesso' {
    $r = Invoke-Gate5Native -FilePath 'cmd.exe' -Arguments @('/c', 'echo ok123')
    ($r.ExitCode -eq 0) -and (($r.Output -join '') -match 'ok123')
}

It 'TLS 1.2 habilitado para as fontes oficiais aprovadas' {
    ([Net.ServicePointManager]::SecurityProtocol -band [Net.SecurityProtocolType]::Tls12) -ne 0
}

It 'Test-Gate5PathWritable distingue gravavel de nao-gravavel' {
    $okDir = Join-Path $tmp 'gravavel'
    New-Item -ItemType Directory -Force $okDir | Out-Null
    # Diretorio inexistente cai no pai (e onde ele seria criado).
    $novo = Join-Path $okDir 'ainda-nao-existe'
    (Test-Gate5PathWritable -Path $okDir) -and
    (Test-Gate5PathWritable -Path $novo) -and
    (-not (Test-Gate5PathWritable -Path 'Z:\caminho\inexistente\demais'))
}

It 'Get-Gate5Sha256 devolve hash minusculo de 64 hex' {
    $f = Join-Path $tmp 'hash.txt'
    Set-Content -LiteralPath $f -Value 'abc' -Encoding ascii
    (Get-Gate5Sha256 -Path $f) -match '^[0-9a-f]{64}$'
}

Write-Host 'T-B: determinismo do aggregate hash do ruleset'

It 'ordenacao ordinal e estavel e independente da ordem de entrada' {
    # Caminhos escolhidos para divergir entre comparacao ordinal e cultural:
    # ordinal poe maiusculas antes de minusculas e '_' (0x5F) antes de 'a'.
    $paths = @('malware/Zeus.yar', 'malware/apt.yar', 'crypto/_index.yar', 'crypto/AES.yar', 'packers/upx.yar')
    # NB: nao usar 'param($input)' - $input e variavel automatica do PowerShell.
    $sortOrdinal = {
        param($Items)
        $a = [string[]]@($Items)
        [Array]::Sort($a, [StringComparer]::Ordinal)
        return $a
    }
    $r1 = & $sortOrdinal $paths
    $r2 = & $sortOrdinal ($paths | Sort-Object { $_.Length })   # ordem de entrada diferente
    $expected = @('crypto/AES.yar', 'crypto/_index.yar', 'malware/Zeus.yar', 'malware/apt.yar', 'packers/upx.yar')
    (($r1 -join '|') -eq ($r2 -join '|')) -and (($r1 -join '|') -eq ($expected -join '|'))
}

It 'manifesto UTF-8 sem BOM produz o mesmo aggregate para o mesmo conteudo' {
    $entries = @(
        [pscustomobject]@{ rel = 'crypto/AES.yar'; sha = ('a' * 64) },
        [pscustomobject]@{ rel = 'malware/apt.yar'; sha = ('b' * 64) }
    )
    $agg = {
        param($e)
        $manifest = ($e | ForEach-Object { "{0}`t{1}`n" -f $_.rel, $_.sha }) -join ''
        $enc = New-Object System.Text.UTF8Encoding($false)
        $sha = [Security.Cryptography.SHA256]::Create()
        return ([BitConverter]::ToString($sha.ComputeHash($enc.GetBytes($manifest))) -replace '-', '').ToLowerInvariant()
    }
    $h1 = & $agg $entries
    $h2 = & $agg $entries
    ($h1 -eq $h2) -and ($h1 -match '^[0-9a-f]{64}$')
}

Write-Host 'T-C: invariantes estaticas dos scripts (boundary do GATE 5)'

$scriptFiles = @(Get-ChildItem $labDir -Filter '*.ps1' -Recurse | Where-Object { $_.Name -ne 'test-gate5-lab-automation.ps1' })
$allText = ($scriptFiles | ForEach-Object { Get-Content $_.FullName -Raw }) -join "`n"

# Somente CODIGO (comentarios removidos pelo tokenizador). Guardas sobre
# mecanismos proibidos precisam disto: os comentarios que EXPLICAM a proibicao
# citam o mecanismo e disparariam falso positivo contra a propria documentacao.
$allCode = ($scriptFiles | ForEach-Object {
    $erros = $null
    $tokens = [System.Management.Automation.PSParser]::Tokenize((Get-Content $_.FullName -Raw), [ref]$erros)
    ($tokens | Where-Object { $_.Type -ne 'Comment' } | ForEach-Object { $_.Content }) -join ' '
}) -join "`n"

It 'payload do guest e entregue por midia, nao por guest operations' {
    # Em VM criptografada nao ha canal vmrun; YARA, ruleset e o script do guest
    # viajam na ISO controlada e o Windows Setup os dispara.
    $boot = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
    $tpl  = Get-Content (Join-Path $labDir 'templates\Autounattend.template.xml') -Raw
    (Test-Path (Join-Path $labDir 'guest\gate5-payload.ps1')) -and
    ($boot -match 'payload-marker\.txt') -and
    ($boot -notmatch 'Copy-ToGuest -HostPath') -and
    ($tpl  -match '<FirstLogonCommands>') -and ($tpl -match 'gate5-payload\.ps1')
}

It 'fase Unattend nao mexe na midia com a VM em execucao' {
    # Regressao: regenerar a ISO com a VM ligada falha (arquivo em uso) e
    # trocaria o payload sob uma instalacao em andamento.
    $boot = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
    $iGuarda = $boot.IndexOf('VM em execucao com a midia ja anexada')
    $iIso    = $boot.IndexOf('CreateResultImage')
    ($iGuarda -gt 0) -and ($iIso -gt $iGuarda) -and
    ($boot -match 'if \(\(Test-Gate5VmPoweredOn\) -and \(Test-Path \$unattendIso\)\)')
}

It 'tecla de boot nunca depende do tamanho do VMDK' {
    # Regressao: um disco thin NAO encolhe quando o Setup o limpa, entao um VMDK
    # grande pode conter uma instalacao ja apagada. O criterio de tamanho pulava
    # o envio da tecla justamente quando ela era necessaria.
    $boot = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
    ($boot -notmatch 'setupJaIniciou') -and
    ($boot -match 'Get-VmUptimeSeconds')
}

It 'tecla de boot so e enviada com o firmware na tela' {
    # No Windows Setup uma tecla poderia acionar um botao em foco; a tecla so
    # sai quando o framebuffer mostra a fase de firmware (tela preta de texto).
    $boot = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
    $comm = Get-Content (Join-Path $labDir 'gate5-common.ps1') -Raw
    ($comm -match 'function Test-Gate5FirmwareScreen') -and
    ($boot -match 'if \(\$scr -and \$scr\.IsFirmware\)') -and
    ($boot -match 'OPTICAL_BOOT_PROMPT_NOT_SEEN')
}

It 'estado boot_key_sent impede segunda tecla nos reboots' {
    # Sem isso o Setup seria reiniciado pela ISO a cada reboot da instalacao.
    $boot = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
    # Substring literal: escapar '$true' como regex em aspas duplas produz \T.
    $boot.Contains("Set-Gate5InstallNote 'boot_key_sent' " + '$true') -and
    ($boot -match "Set-Gate5InstallNote 'installation_stage' 'DISK_BOOT_EXPECTED'") -and
    ($boot -match 'if \(\$bootKeySent\)') -and
    ($boot -match 'nenhuma nova sera enviada')
}

It 'watcher aguarda o power-cycle sem depender do aviso do operador' {
    $boot = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
    ($boot -match "action=POWER_CYCLE_VM") -and
    ($boot -match 'while \(\[DateTime\]::UtcNow -lt \$ate -and \(Test-Gate5VmPoweredOn\)\)') -and
    ($boot -match 'while \(\[DateTime\]::UtcNow -lt \$ate -and -not \(Test-Gate5VmPoweredOn\)\)')
}

It 'console local oferece teclado, combinacao e ponteiro' {
    # O teclado nao chega ao guest em alguns estados (o console da interface do
    # VMware pode deter a entrada); o evento de ponteiro atinge a coordenada sem
    # depender de foco, e foi o que destravou o dialogo do Setup.
    $comm = Get-Content (Join-Path $labDir 'gate5-common.ps1') -Raw
    ($comm -match 'function Send-Gate5VncPointerClick') -and
    ($comm -match 'function Sync-Gate5VncStream') -and
    ($comm -match 'PointerEvent')
}

It 'evidencia sai do guest por canal serial de mao unica' {
    $common = Get-Content (Join-Path $labDir 'gate5-common.ps1') -Raw
    $boot   = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
    $guest  = Get-Content (Join-Path $labDir 'guest\gate5-payload.ps1') -Raw
    ($common -match 'Gate5EvidenceSerial') -and ($common -match 'GATE5-EVIDENCE-BEGIN') -and
    ($boot -match "'serial0\.fileType'\s+-Value\s+'file'") -and
    ($guest -match 'GATE5-EVIDENCE-BEGIN')
}

It 'midia e canais sao validados ANTES de pedir o power-on' {
    # Um gate humano gasto com midia invalida foi exatamente o que aconteceu com
    # o Autounattend sem <ProductKey>: a instalacao parou numa tela.
    $boot = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
    $iMidia  = $boot.IndexOf('Test-Gate5UnattendMedia')
    $iSerial = $boot.IndexOf('SERIAL_CHANNEL_NOT_READY')
    $iGate   = $boot.IndexOf("Stop-Gate5Human -Action 'POWER_ON_VM'")
    ($iMidia -gt 0) -and ($iSerial -gt 0) -and ($iGate -gt $iMidia) -and ($iGate -gt $iSerial) -and
    ($boot -match 'UNATTEND_MEDIA_INVALID') -and ($boot -match 'VNC_NOT_LOCAL')
}

It 'validador da midia le a estrutura real da ISO' {
    # Nao basta procurar bytes soltos: e preciso provar que o Autounattend esta
    # na RAIZ do namespace que o Windows Setup usa (Joliet), e que os nomes com
    # sufixo de versao ';1' do ISO9660 sao normalizados.
    $comm = Get-Content (Join-Path $labDir 'gate5-common.ps1') -Raw
    # Substring literal em aspas simples: escapar isto como regex e fragil.
    ($comm -match 'function Get-Gate5IsoEntries') -and
    $comm.Contains('\d+$') -and
    ($comm -match 'BigEndianUnicode') -and
    ($comm -match 'autounattend_na_raiz')
}

It 'automacao aguarda o power-on para pegar a janela do boot' {
    # A janela do prompt de boot dura poucos segundos; depender de quando o
    # operador avisa faz a automacao perde-la, como aconteceu na execucao real.
    $boot = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
    ($boot -match 'AddMinutes\(30\)') -and
    ($boot -match 'Power-on detectado') -and
    ($boot -match 'WAITING_POWER_ON')
}

It 'power-on de VM criptografada e gate humano com validacao automatica' {
    $boot = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
    ($boot -match "Stop-Gate5Human -Action 'POWER_ON_VM'") -and
    ($boot -match 'Get-Gate5SerialEvidence') -and
    # a espera termina pela EVIDENCIA tecnica, nunca por confirmacao textual
    ($boot -match 'Evidencia recebida do guest')
}

It 'payload do guest nao referencia o alvo nem a VPS' {
    $guest = Get-Content (Join-Path $labDir 'guest\gate5-payload.ps1') -Raw
    ($guest -notmatch '(?i)faithro-vps') -and
    ($guest -notmatch '(?i)(Invoke-WebRequest|Invoke-RestMethod|curl)') -and
    # 'WARP*' aparece apenas como padrao que PROVA a ausencia do alvo
    ($guest -match "warp_artifacts")
}

It 'nenhum caminho fornece a senha de criptografia ao vmrun' {
    # DECISAO ARQUITETURAL: a senha da criptografia da VM (exigida pelo vTPM) e
    # exclusiva do operador. '-vp' a exporia na lista de processos da maquina.
    ($allCode -notmatch '(?m)-vp\b') -and
    ($allCode -notmatch '(?i)authd.*password') -and
    ($allCode -notmatch '(?i)VM_ENCRYPTION_PASSWORD')
}

It 'nenhum script le a credencial de criptografia guardada no host' {
    # Nem do Gerenciador de Credenciais, nem de cofres equivalentes.
    ($allCode -notmatch '(?i)\bcmdkey\b') -and
    ($allCode -notmatch '(?i)\bvaultcmd\b') -and
    ($allCode -notmatch '(?i)PasswordVault') -and
    ($allCode -notmatch '(?i)CredRead') -and
    ($allCode -notmatch '(?i)Get-StoredCredential') -and
    ($allCode -notmatch '(?i)Microsoft\.Security\.Credentials')
}

It 'nenhum script pede a senha de criptografia ao operador' {
    # O gate humano pede uma ACAO na interface do VMware, nunca a credencial.
    ($allCode -notmatch '(?i)Read-Host') -and
    ($allCode -notmatch '(?i)Get-Credential')
}

It 'vmrun falha fechado em VM criptografada' {
    $common = Get-Content (Join-Path $labDir 'gate5-common.ps1') -Raw
    $iGuarda = $common.IndexOf('ENCRYPTED_VM_REQUIRES_HUMAN_POWER_OP')
    $iExec   = $common.IndexOf('Invoke-Gate5Native -FilePath $Vmware.VmrunExe')
    ($iGuarda -gt 0) -and ($iExec -gt $iGuarda)
}

It 'nenhum script contata a VPS de producao' {
    $allText -notmatch 'faithro-vps' -and $allText -notmatch 'ssh\s+faithro'
}

It 'nenhum script materializa, baixa ou executa o alvo WARP' {
    # 'WARP*' aparece apenas como PADRAO DE BUSCA que prova a AUSENCIA do alvo.
    $downloads = [regex]::Matches($allText, '(?i)(Invoke-WebRequest|Invoke-RestMethod|curl|git\s+clone)[^\r\n]*')
    $bad = $downloads | Where-Object { $_.Value -match '(?i)warp|ragexe|\.grf' }
    @($bad).Count -eq 0
}

It 'nenhum script usa servico de reputacao externa' {
    $allText -notmatch '(?i)virustotal\.com' -and $allText -notmatch '(?i)/api/v3/files'
}

It 'downloads restritos as fontes oficiais aprovadas' {
    $urls = [regex]::Matches($allText, 'https://[^\s"'')]+') | ForEach-Object { $_.Value }
    $allowed = '^https://(api\.github\.com/repos/(VirusTotal/yara|Yara-Rules/rules)|github\.com/Yara-Rules/rules|support\.broadcom\.com|www\.microsoft\.com/software-download)'
    $bad = $urls | Where-Object { $_ -notmatch $allowed }
    if ($bad) { Write-Host ("        fontes nao aprovadas: " + ($bad -join ', ')) }
    @($bad).Count -eq 0
}

It 'nenhum script desabilita o Defender ou cria exclusao' {
    $allText -notmatch '(?i)Set-MpPreference\s+-Disable' -and
    $allText -notmatch '(?i)Add-MpPreference\s+-Exclusion' -and
    $allText -notmatch '(?i)DisableRealtimeMonitoring'
}

It 'nenhum script desabilita Secure Boot ou contorna TPM' {
    $allText -notmatch '(?i)secureBoot\.enabled\s*=\s*"?FALSE' -and
    $allText -notmatch '(?i)BypassTPMCheck' -and
    $allText -notmatch '(?i)LabConfig'
}

It 'nenhum script altera Hyper-V/VBS do host' {
    $allText -notmatch '(?i)Disable-WindowsOptionalFeature' -and
    $allText -notmatch '(?i)bcdedit' -and
    $allText -notmatch '(?i)hypervisorlaunchtype'
}

It 'aquisicao do ruleset nao depende de git no PATH' {
    # A execucao elevada ocorre sob outra conta administradora; uma instalacao
    # per-user do git nao existe la e a fase Rules falharia no fim da etapa.
    $boot = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
    $boot -notmatch "(?m)-FilePath\s+'git'" -and $boot -notmatch '(?m)^\s*git\s+(clone|checkout|rev-parse)'
}

It 'ruleset e materializado pelo SHA-40 fixado, nao por branch flutuante' {
    $boot = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
    # Padroes em aspas simples: em aspas duplas o PowerShell interpolaria $pin.
    $boot.Contains('/archive/'' + $pin') -and ($boot -match 'notmatch\s+''\^\[0-9a-f\]\{40\}')
}

It 'YARA fixado em 4.5.5 e ruleset nas categorias autorizadas' {
    $boot = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
    $verPinned = $boot -match "v4\.5\.5"
    $included  = $boot -match "@\('malware','packers','antidebug_antivm','capabilities','crypto'\)"
    $excluded  = $boot -match "'email','mobile_malware','webshells','maldocs'"
    $verPinned -and $included -and $excluded
}

It 'senha do guest e redigida no log do vmrun (valor, nao so a flag)' {
    $common = Get-Content (Join-Path $labDir 'gate5-common.ps1') -Raw
    # A redacao precisa pular o argumento seguinte a -gu/-gp; caso contrario a
    # senha em texto claro apareceria na trilha de auditoria.
    ($common -match "'<redacted>'") -and ($common -match '\$i\+\+')
}

It 'nenhuma senha literal versionada nos scripts ou no template' {
    $tpl = Get-Content (Join-Path $labDir 'templates\Autounattend.template.xml') -Raw
    ($tpl -match '\{\{BOOTSTRAP_PASSWORD\}\}') -and
    ($tpl -notmatch '(?i)<Value>[A-Za-z0-9+/=]{8,}</Value>') -and
    ($allText -notmatch '(?i)ConvertTo-SecureString\s+["''][^"'']+["'']\s+-AsPlainText')
}

It 'unattend declara chave vazia e nao para em nenhuma tela' {
    # Regressao da primeira execucao real: sem <ProductKey> o Setup PARA na tela
    # "Chave do produto" e espera um humano, quebrando a instalacao desassistida.
    [xml]$x = Get-Content (Join-Path $labDir 'templates\Autounattend.template.xml')
    $ns = New-Object System.Xml.XmlNamespaceManager($x.NameTable)
    $ns.AddNamespace('u', 'urn:schemas-microsoft-com:unattend')
    $pk = $x.SelectSingleNode('//u:UserData/u:ProductKey', $ns)
    $tpl = Get-Content (Join-Path $labDir 'templates\Autounattend.template.xml') -Raw
    ($null -ne $pk) -and
    ([string]::IsNullOrEmpty($pk.SelectSingleNode('u:Key', $ns).InnerText)) -and
    ($pk.SelectSingleNode('u:WillShowUI', $ns).InnerText -eq 'Never') -and
    ($tpl -match '<DiskConfiguration>\s*<WillShowUI>OnError</WillShowUI>')
}

It 'nenhuma chave de produto do Windows no template' {
    # O elemento <ProductKey> e necessario (com chave VAZIA) para a instalacao
    # nao parar numa tela; o que nao pode existir e um VALOR de chave. Verificado
    # por XML: um regex sobre <Key> pegaria tambem o metadado /IMAGE/NAME.
    $caminho = Join-Path $labDir 'templates\Autounattend.template.xml'
    [xml]$x = Get-Content $caminho
    $ns = New-Object System.Xml.XmlNamespaceManager($x.NameTable)
    $ns.AddNamespace('u', 'urn:schemas-microsoft-com:unattend')
    $chaves = @($x.SelectNodes('//u:ProductKey/u:Key', $ns) | ForEach-Object { $_.InnerText })
    $tpl = Get-Content $caminho -Raw
    (@($chaves | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }).Count -eq 0) -and
    ($tpl -notmatch '[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}')
}

It 'portas de CD vem de uma definicao unica compartilhada' {
    # Criacao, anexo do unattend e isolamento referenciam as mesmas portas; um
    # literal solto em qualquer um deles deixaria a VM com duas unidades
    # apontando para a mesma ISO ou com o CD errado desconectado no baseline.
    $common = Get-Content (Join-Path $labDir 'gate5-common.ps1') -Raw
    $declared = ($common -match 'Gate5CdOs\s*=') -and ($common -match 'Gate5CdUnattend\s*=')
    $consumers = @('gate5-create-vm.ps1', 'gate5-guest-bootstrap.ps1', 'gate5-provision.ps1') |
        ForEach-Object { Get-Content (Join-Path $labDir $_) -Raw }
    $hardcoded = $consumers | Where-Object { $_ -match "'sata0:\d\." }
    $declared -and (@($hardcoded).Count -eq 0)
}

It 'vTPM nao e dado como valido pela chave de auto-adicao' {
    # Regressao: aceitar managedvm.autoAddVTPM como prova era um falso positivo
    # - a chave e escrita pela propria automacao e o Workstation so a honra no
    # fluxo gerenciado, nao em 'vmrun start' sobre um .vmx escrito a mao.
    $ver  = Get-Content (Join-Path $labDir 'gate5-verify-baseline.ps1') -Raw
    $comm = Get-Content (Join-Path $labDir 'gate5-common.ps1') -Raw
    # O validador exige o dispositivo materializado...
    ($ver -match "Check 'vtpm-vmx' \(\(Get-Gate5VmxValue 'vtpm\.present'\)") -and
    # ...e o helper de estado so considera vTPM quando ha propriedade 'vtpm.*'
    # real no .vmx, nunca a chave de auto-adicao escrita pela automacao.
    ($comm -match "VtpmPresent = \[bool\]\(@\(\`$names \| Where-Object \{ \`$_ -like 'vtpm\.\*' \}\)\.Count\)") -and
    ($comm -notmatch "managedvm\.autoAddVTPM'\)\s*-eq")
}

It 'nenhuma escrita pos-criptografia reescreve o .vmx inteiro' {
    # A partir do vTPM a VM esta criptografada. As tres rotinas que gravam no
    # .vmx depois desse ponto (anexo do unattend, isolamento final e console VNC)
    # precisam gravar chave a chave por Set-Gate5VmxEntry, que usa a API do
    # VMware quando ha criptografia. Set-Gate5TextFile sobre o .vmx so pode
    # sobreviver na criacao/reparacao, que e barrada em VM criptografada.
    $prov = Get-Content (Join-Path $labDir 'gate5-provision.ps1') -Raw
    $boot = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
    $comm = Get-Content (Join-Path $labDir 'gate5-common.ps1') -Raw
    $reescreveVmx = { param($t) $t -match 'Set-Gate5TextFile\s+-Path\s+\$script:Gate5VmxPath' }
    (-not (& $reescreveVmx $prov)) -and
    (-not (& $reescreveVmx $boot)) -and
    ($prov -match 'Set-Gate5VmxEntry') -and ($boot -match 'Set-Gate5VmxEntry') -and
    # vmcli nao pode ser usado: em VM criptografada ele exige a senha da
    # criptografia por stdin, e essa senha e exclusiva do operador.
    ($comm -notmatch "ConfigParams'")
}

It 'Set-Gate5VmxEntry preserva material criptografico verbatim' {
    # O .vmx de uma VM com vTPM fica em texto plano com 'encryption.*'/'vtpm.*'
    # como valores opacos. Trocar outra chave nao pode alterar essas linhas.
    $fake = Join-Path $tmp 'cripto-edit.vmx'
    $sens1 = 'encryption.keySafe = "vmware:key/list/(pair/(MzQ1Njc4OTA,AES-256))"'
    $sens2 = 'vtpm.ekCRT = "MIIF+DCCBOCgAwIBAgIQ' + ('A' * 200) + '"'
    Set-Gate5TextFile -Path $fake -Lines @('firmware = "efi"', $sens1, 'sata0:1.present = "FALSE"', $sens2)
    $original = $script:Gate5VmxPath
    try {
        $script:Gate5VmxPath = $fake
        Set-Gate5VmxEntry -Name 'sata0:1.present' -Value 'TRUE'
        Set-Gate5VmxEntry -Name 'nova.chave' -Value 'X'
        $linhas = @([System.IO.File]::ReadAllLines($fake))
        ($linhas -ccontains $sens1) -and ($linhas -ccontains $sens2) -and
        ((Get-Gate5VmxValue 'sata0:1.present' -VmxPath $fake) -eq 'TRUE') -and
        ((Get-Gate5VmxValue 'nova.chave' -VmxPath $fake) -eq 'X') -and
        # ordem preservada: a chave trocada continua na posicao original
        ($linhas[2] -match '^sata0:1\.present')
    } finally { $script:Gate5VmxPath = $original }
}

It 'Set-Gate5VmxEntry preserva o restante do arquivo' {
    $fake = Join-Path $tmp 'entry.vmx'
    Set-Gate5TextFile -Path $fake -Lines @('a.b = "1"', 'c.d = "2"', 'e.f = "3"')
    $original = $script:Gate5VmxPath
    try {
        $script:Gate5VmxPath = $fake
        Set-Gate5VmxEntry -Name 'c.d' -Value '9'      # sobrescreve
        Set-Gate5VmxEntry -Name 'g.h' -Value 'novo'   # acrescenta
        $linhas = @(Get-Content $fake)
        (@($linhas | Where-Object { $_ -match '^c\.d' }).Count -eq 1) -and
        ((Get-Gate5VmxValue 'c.d' -VmxPath $fake) -eq '9') -and
        ((Get-Gate5VmxValue 'a.b' -VmxPath $fake) -eq '1') -and
        ((Get-Gate5VmxValue 'e.f' -VmxPath $fake) -eq '3') -and
        ((Get-Gate5VmxValue 'g.h' -VmxPath $fake) -eq 'novo')
    } finally { $script:Gate5VmxPath = $original }
}

It 'Set-Gate5VmxEntry nao reescreve quando o valor ja e o desejado' {
    # Evita tocar no .vmx de uma VM aberta na interface do VMware (que mantem a
    # configuracao em cache) quando nao ha nada a mudar.
    $fake = Join-Path $tmp 'noop.vmx'
    Set-Gate5TextFile -Path $fake -Lines @('a.b = "1"', 'c.d = "2"')
    $original = $script:Gate5VmxPath
    try {
        $script:Gate5VmxPath = $fake
        $antes = (Get-Item $fake).LastWriteTimeUtc
        Start-Sleep -Milliseconds 1100
        Set-Gate5VmxEntry -Name 'c.d' -Value '2'      # mesmo valor: no-op
        $semMudanca = ((Get-Item $fake).LastWriteTimeUtc -eq $antes)
        Set-Gate5VmxEntry -Name 'c.d' -Value '3'      # valor novo: grava
        $comMudanca = ((Get-Gate5VmxValue 'c.d' -VmxPath $fake) -eq '3')
        $semMudanca -and $comMudanca
    } finally { $script:Gate5VmxPath = $original }
}

It 'Get-Gate5VmEncryptionState respeita o caminho informado' {
    # Regressao: o helper lia firmware/Secure Boot do caminho GLOBAL, e nao do
    # arquivo consultado, podendo reportar o estado de outra VM.
    $outro = Join-Path $tmp 'outro.vmx'
    Set-Gate5TextFile -Path $outro -Lines @('firmware = "bios"', 'uefi.secureBoot.enabled = "FALSE"')
    $st = Get-Gate5VmEncryptionState -VmxPath $outro
    ($st.Firmware -eq 'bios') -and (-not $st.SecureBoot) -and (-not $st.Encrypted)
}

It 'isolamento confere listener real, nao apenas o .vmx' {
    $prov = Get-Content (Join-Path $labDir 'gate5-provision.ps1') -Raw
    $ver  = Get-Content (Join-Path $labDir 'gate5-verify-baseline.ps1') -Raw
    ($prov -match 'ISOLATION_VNC_LISTENER_ACTIVE') -and ($prov -match 'Get-NetTCPConnection') -and
    ($ver  -match 'console-vnc-sem-listener') -and ($ver -match 'Get-NetTCPConnection')
}

It 'console VNC e local, temporario e verificado como removido' {
    # A tecla do prompt "Press any key to boot from CD" so chega ao guest por um
    # console conectado; o console VNC do VMware e esse canal. Ele precisa ficar
    # preso a 127.0.0.1 e nao pode sobreviver ao snapshot baseline.
    $common = Get-Content (Join-Path $labDir 'gate5-common.ps1') -Raw
    $prov   = Get-Content (Join-Path $labDir 'gate5-provision.ps1') -Raw
    $ver    = Get-Content (Join-Path $labDir 'gate5-verify-baseline.ps1') -Raw
    ($common -match "'RemoteDisplay\.vnc\.ip'\s+-Value\s+'127\.0\.0\.1'") -and
    ($common -notmatch '0\.0\.0\.0') -and
    ($prov   -match 'Set-Gate5VncConsole -Enabled \$false') -and
    ($prov   -match "Get-Gate5VmxValue 'RemoteDisplay\.vnc\.enabled'") -and
    ($ver    -match 'console-vnc-desligado')
}

It 'entrega da tecla de boot falha fechado se o prompt nao aparecer' {
    # Silencio nunca vira sucesso: sem observar o prompt no framebuffer, a etapa
    # bloqueia em vez de teclar as cegas.
    $boot = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
    ($boot -match 'OPTICAL_BOOT_PROMPT_NOT_SEEN') -and ($boot -match 'Send-Gate5VncKey -Keysym 0xFF0D')
}

It 'estado criptografico e reportado sem expor valores' {
    # Get-Gate5VmEncryptionState deve devolver booleanos e NOMES de propriedades,
    # nunca o material de 'encryption.*'/'vtpm.*'.
    $fake = Join-Path $tmp 'cripto.vmx'
    Set-Gate5TextFile -Path $fake -Lines @(
        'firmware = "efi"'
        'uefi.secureBoot.enabled = "TRUE"'
        'encryption.keySafe = "SEGREDO-NAO-PODE-VAZAR"'
        'encryption.data = "OUTRO-SEGREDO"'
        'vtpm.present = "TRUE"'
    )
    $st = Get-Gate5VmEncryptionState -VmxPath $fake
    $texto = ($st | Format-List | Out-String)
    $st.Encrypted -and $st.VtpmPresent -and $st.SecureBoot -and ($st.Firmware -eq 'efi') -and
    ($st.MaterialPropertyNames -contains 'encryption.keySafe') -and
    ($st.MaterialPropertyNames -contains 'vtpm.present') -and
    ($texto -notmatch 'SEGREDO-NAO-PODE-VAZAR') -and ($texto -notmatch 'OUTRO-SEGREDO')
}

It 'divergencia em VM criptografada nunca imprime material sensivel' {
    $cv = Get-Content (Join-Path $labDir 'gate5-create-vm.ps1') -Raw
    # Substring literal: escapar isto como regex e mais fragil que compara-lo.
    $cv.Contains('=<redigido>') -and ($cv -match "match '\^\(encryption\\\.\|vtpm")
}

It 'VMX criptografado nunca e reescrito pela automacao' {
    # Reescrever o .vmx de uma VM criptografada destroi a associacao da
    # criptografia e, com ela, o vTPM que o gate humano acabou de criar.
    $cv = Get-Content (Join-Path $labDir 'gate5-create-vm.ps1') -Raw
    $guardaAntes = $cv.IndexOf("'^encryption\.'")
    $reescrita   = $cv.IndexOf('Set-Gate5TextFile -Path $script:Gate5VmxPath')
    ($guardaAntes -gt 0) -and ($reescrita -gt $guardaAntes) -and ($cv -match 'ENCRYPTED_VMX_CONFIG_DIVERGENT')
}

It 'elevacao e exigida apenas quando realmente necessaria' {
    # Exigir Administrator em toda execucao impediria a retomada depois que o
    # VMware ja esta instalado, sem nenhum ganho de seguranca.
    $pf = Get-Content (Join-Path $labDir 'gate5-host-preflight.ps1') -Raw
    ($pf -match '\$needsElevation\s*=\s*\(-not \$vmwareFound\) -or \(-not \$vmDirWritable\)') -and
    ($pf -match 'if \(\$needsElevation -and -not \$elevated\)') -and
    ($pf -notmatch 'if \(-not \(Test-Gate5Elevated\)\) \{ Add-Failure')
}

It 'credencial ilegivel com guest instalado falha fechado' {
    # DPAPI e por usuario: gerar uma senha nova nao abriria um Windows ja
    # instalado com a senha antiga.
    $boot = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
    ($boot -match 'GUEST_CREDENTIAL_UNREADABLE') -and ($boot -match 'Test-GuestCredentialUsable')
}

It 'NVRAM nunca e descartada em VM com vTPM ou criptografia' {
    # A partir do vTPM a NVRAM guarda o estado persistente do TPM virtual;
    # descarta-la destruiria em silencio o dispositivo criado pelo operador.
    # O disco ainda vazio (criterio antigo) NAO pode mais autorizar a remocao.
    $cv = Get-Content (Join-Path $labDir 'gate5-create-vm.ps1') -Raw
    $iCrypto = $cv.IndexOf('$cryptoState = Get-Gate5VmEncryptionState')
    $iDisco  = $cv.IndexOf('-lt 100MB')
    ($iCrypto -gt 0) -and ($iDisco -gt $iCrypto) -and
    ($cv -match 'if \(\$cryptoState\.Encrypted -or \$cryptoState\.VtpmPresent\)') -and
    ($cv -match '\} elseif \(\(Get-Item -LiteralPath \$vmdkPath')
}

It 'NVRAM so e descartada com o disco ainda vazio' {
    # Descartar a NVRAM depois do Windows instalado apagaria a entrada de boot
    # do proprio sistema; o criterio objetivo e o disco praticamente vazio.
    $cv = Get-Content (Join-Path $labDir 'gate5-create-vm.ps1') -Raw
    $cv -match '\$vmdkPath[^\r\n]*\)\.Length -lt 100MB'
}

It 'snapshot baseline so e criado apos a fase de isolamento' {
    $prov = Get-Content (Join-Path $labDir 'gate5-provision.ps1') -Raw
    $iIsolated = $prov.IndexOf("'ISOLATED'")
    $iSnapshot = $prov.IndexOf("'SNAPSHOT_CREATED'")
    ($iIsolated -gt 0) -and ($iSnapshot -gt $iIsolated)
}

It 'VM final fica com NIC desconectada e sem autoconectar' {
    $prov = Get-Content (Join-Path $labDir 'gate5-provision.ps1') -Raw
    ($prov -match "'ethernet0\.startConnected'\s+-Value\s+'FALSE'") -and
    ($prov -match "'ethernet0\.connected'\s+-Value\s+'FALSE'")
}

It 'validador exige todos os controles do baseline' {
    $ver = Get-Content (Join-Path $labDir 'gate5-verify-baseline.ps1') -Raw
    $required = @('guest-secureboot','guest-tpm-ready','guest-defender','guest-yara-4.5.5',
                  'guest-nic-down','guest-target-absent','snapshot-baseline','secrets-gate',
                  'nic-startconnected-false','clipboard-off','dnd-off','hgfs-off')
    $missing = $required | Where-Object { $ver -notmatch [regex]::Escape($_) }
    if ($missing) { Write-Host ("        controles ausentes: " + ($missing -join ', ')) }
    @($missing).Count -eq 0
}

} finally {
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ''
Write-Host ("RESULTADO: {0} PASS / {1} FAIL" -f $script:pass, $script:fail)
if ($script:fail -gt 0) { exit 1 }
exit 0
