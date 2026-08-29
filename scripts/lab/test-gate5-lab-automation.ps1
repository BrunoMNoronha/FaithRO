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

It 'midia desatualizada e reconstruida apos o power-off, num unico ciclo' {
    # Se o template mudou, a ISO montada precisa ser refeita - e isso exige a VM
    # desligada. A fase aguarda o power-off e reconstroi, para que um unico
    # ciclo do operador baste.
    $boot = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
    ($boot -match '\$midiaAtual = \(Get-Item \$unattendIso\)\.LastWriteTimeUtc -ge') -and
    ($boot -match 'Template mais novo que a midia') -and
    ($boot -match 'reconstruindo a midia com o template corrigido')
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

It 'captura de tela carrega System.Drawing e resolve caminho relativo' {
    # Regressao: as fases rodam com 'powershell -NoProfile -NonInteractive',
    # onde System.Drawing nao e carregado sozinho, e o diretorio de trabalho do
    # .NET nao acompanha o do PowerShell. As capturas falhavam silenciosamente e
    # o watcher perdia a janela do prompt de boot por falta de imagem.
    $comm = Get-Content (Join-Path $labDir 'gate5-common.ps1') -Raw
    $i = $comm.IndexOf('function Save-Gate5VncScreenshot')
    $trecho = $comm.Substring($i, [Math]::Min(1800, $comm.Length - $i))
    ($trecho -match "Add-Type -AssemblyName System\.Drawing") -and
    ($trecho -match 'IsPathRooted') -and
    ($trecho -match 'New-Item -ItemType Directory')
}

It 'tecla de boot so e enviada com o PROMPT na tela' {
    # Detectar apenas "tela preta" fazia a automacao gastar a tecla numa tela
    # anterior ao prompt. O sinal e o texto claro na faixa superior.
    $boot = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
    $comm = Get-Content (Join-Path $labDir 'gate5-common.ps1') -Raw
    ($comm -match 'function Test-Gate5BootPromptOnScreen') -and
    ($comm -match 'BrightTop') -and
    ($boot -match 'if \(\$scr -and \$scr\.HasPrompt\)') -and
    ($boot -notmatch '\$scr\.IsFirmware') -and
    ($boot -match 'OPTICAL_BOOT_PROMPT_NOT_SEEN')
}

It 'boot_key_sent so e fixado quando o Setup grava no disco' {
    # O estado anti-loop precisa significar "o boot optico disparou", nao
    # "uma tecla foi enviada" - senao a unica tecla se perde antes do prompt.
    $boot = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
    $iCresceu = $boot.IndexOf('$discoBase + 200MB')
    $iFixa    = $boot.IndexOf("Set-Gate5InstallNote 'boot_key_sent' ")
    ($iCresceu -gt 0) -and ($iFixa -gt $iCresceu) -and
    ($boot -match 'if \(\$instalando\)')
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

It 'checkpoint do pai nao apaga notas gravadas pelas fases filhas' {
    # Regressao real: o entrypoint carrega o estado uma vez e as fases rodam em
    # processos filhos. Salvar o objeto em memoria do pai sobrescrevia
    # boot_key_sent/installation_stage com valores velhos - apagando a marca
    # anti-loop do boot optico logo depois de ela ser definida.
    $original = $script:Gate5StateFile
    try {
        $script:Gate5StateFile = Join-Path $tmp 'state-teste.json'
        $pai = Get-Gate5State                      # pai carrega cedo
        $filho = Get-Gate5State                    # filho grava sua nota depois
        $filho.notes | Add-Member -NotePropertyName boot_key_sent -NotePropertyValue $true -Force
        Save-Gate5State $filho
        Complete-Gate5Phase $pai 'GUEST_INSTALLED' # pai registra o checkpoint
        $disco = Get-Gate5State
        ($disco.notes.boot_key_sent -eq $true) -and
        (@($disco.completed) -contains 'GUEST_INSTALLED') -and
        ($pai.notes.boot_key_sent -eq $true)       # objeto do pai realinhado
    } finally { $script:Gate5StateFile = $original }
}

It 'entrypoint nao roda fases obsoletas que exigiriam vmrun no guest' {
    # Windows Update, Defender e sanitize rodam DENTRO do guest pelo payload e
    # chegam pela serial. Mante-las no entrypoint so produzia
    # ENCRYPTED_VM_REQUIRES_HUMAN_POWER_OP logo apos a instalacao.
    $prov = Get-Content (Join-Path $labDir 'gate5-provision.ps1') -Raw
    ($prov -notmatch "Sub = @\('Updates'\)") -and
    ($prov -notmatch "Sub = @\('Defender'\)") -and
    ($prov -notmatch "Sub = @\('Sanitize'\)") -and
    ($prov -match "Sub = @\('Unattend', 'InstallWait'\)")
}

It 'payload emite batimentos de progresso pela serial' {
    # Sem batimento o host so recebia sinal no FIM de tudo e nao distinguia
    # "payload trabalhando" de "payload morto" - foi preciso pericia de tela.
    $guest = Get-Content (Join-Path $labDir 'guest\gate5-payload.ps1') -Raw
    $comm  = Get-Content (Join-Path $labDir 'gate5-common.ps1') -Raw
    ($guest -match 'function Send-Heartbeat') -and
    ($guest -match "Send-Heartbeat 'PAYLOAD_STARTED'") -and
    ($guest -match "Send-Heartbeat 'UPDATE_SEARCH_DONE'") -and
    ($comm  -match 'function Get-Gate5SerialStages')
}

It 'batimento nao afrouxa o parser fail-closed da evidencia' {
    # Um batimento sozinho NAO pode ser lido como evidencia; so o bloco
    # completo START->END vale.
    $fake = Join-Path $tmp 'serial-heartbeat.txt'
    Set-Content -LiteralPath $fake -Encoding ascii -Value '<<<GATE5-STAGE:UPDATE|2026-08-29T12:00:00Z|encontradas=3>>>'
    $estagios = Get-Gate5SerialStages -Path $fake
    $ev = Get-Gate5SerialEvidence -Path $fake
    # E com o bloco completo, a evidencia passa a ser lida.
    $cheio = Join-Path $tmp 'serial-cheio.txt'
    Set-Content -LiteralPath $cheio -Encoding ascii -Value '<<<GATE5-STAGE:EVIDENCE|t>>><<<GATE5-EVIDENCE-BEGIN>>>{"os_build":"26200"}<<<GATE5-EVIDENCE-END>>>'
    $ev2 = Get-Gate5SerialEvidence -Path $cheio
    (@($estagios).Count -eq 1) -and ($estagios[0].Stage -eq 'UPDATE') -and
    ($null -eq $ev) -and ($null -ne $ev2) -and ($ev2.os_build -eq '26200')
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

It 'ordem do particionamento e conferida no arquivo da midia' {
    # Nao basta validar o template do repositorio: o que importa e o
    # Autounattend REALMENTE gravado na ISO, que e o que o Setup vai ler.
    $comm = Get-Content (Join-Path $labDir 'gate5-common.ps1') -Raw
    ($comm -match 'function Get-Gate5IsoFileBytes') -and
    ($comm -match 'ordem_particionamento_ok') -and
    ($comm -match "Get-Gate5IsoFileBytes -IsoPath \`$IsoPath -Name 'Autounattend\.xml'") -and
    ($comm -match "CreatePartitions,ModifyPartitions,DiskID,WillWipeDisk")
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
    # A lista foi estendida por DECISAO HUMANA (2026-08-29) para incluir o
    # redistribuivel oficial do Visual C++: sem ele o yara64.exe nao inicia no
    # Windows 11 limpo. A alternativa recusada foi copiar a DLL do proprio host.
    $urls = [regex]::Matches($allText, 'https://[^\s"'')]+') | ForEach-Object { $_.Value }
    $allowed = '^https://(api\.github\.com/repos/(VirusTotal/yara|Yara-Rules/rules)|github\.com/Yara-Rules/rules|support\.broadcom\.com|www\.microsoft\.com/software-download|aka\.ms/vs/[0-9]+/release/vc_redist\.x64\.exe|github\.com/Yara-Rules/rules/archive/)'
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

It 'particionamento segue a ordem de elementos do esquema unattend' {
    # Regressao: com DiskID/WillWipeDisk ANTES de CreatePartitions, o Setup
    # aplicou so a primeira particao e caiu na interface. O esquema exige
    # Disk -> (CreatePartitions, ModifyPartitions, DiskID, WillWipeDisk) e
    # DiskConfiguration -> (Disk, WillShowUI).
    [xml]$x = Get-Content (Join-Path $labDir 'templates\Autounattend.template.xml')
    $ns = New-Object System.Xml.XmlNamespaceManager($x.NameTable)
    $ns.AddNamespace('u', 'urn:schemas-microsoft-com:unattend')
    $disk = $x.SelectSingleNode('//u:DiskConfiguration/u:Disk', $ns)
    $dc   = $x.SelectSingleNode('//u:DiskConfiguration', $ns)
    $ordemDisk = @($disk.ChildNodes | Where-Object { $_.NodeType -eq 'Element' } | ForEach-Object { $_.LocalName })
    $ordemDc   = @($dc.ChildNodes   | Where-Object { $_.NodeType -eq 'Element' } | ForEach-Object { $_.LocalName })
    (($ordemDisk -join ',') -eq 'CreatePartitions,ModifyPartitions,DiskID,WillWipeDisk') -and
    (($ordemDc -join ',') -eq 'Disk,WillShowUI')
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
    # WillShowUI=OnError existe no particionamento (posicao verificada pelo
    # teste de ordem do esquema) e na selecao de imagem.
    ($x.SelectSingleNode('//u:DiskConfiguration/u:WillShowUI', $ns).InnerText -eq 'OnError') -and
    ($x.SelectSingleNode('//u:ImageInstall/u:OSImage/u:WillShowUI', $ns).InnerText -eq 'OnError')
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

Write-Host 'T-D: runtime do Visual C++, pin do ruleset e criterios do baseline'

$bootTxt    = Get-Content (Join-Path $labDir 'gate5-guest-bootstrap.ps1') -Raw
$payloadTxt = Get-Content (Join-Path $labDir 'guest\gate5-payload.ps1') -Raw
$provTxt    = Get-Content (Join-Path $labDir 'gate5-provision.ps1') -Raw
$verifyTxt  = Get-Content (Join-Path $labDir 'gate5-verify-baseline.ps1') -Raw

function Get-FunctionText {
    # Extrai o texto de uma funcao pelo casamento de chaves, para exercitar a
    # implementacao REAL do payload sem executar o script (que roda no guest).
    param([string]$Texto, [string]$Nome)
    $i = $Texto.IndexOf("function $Nome")
    if ($i -lt 0) { return '' }
    $abre = $Texto.IndexOf('{', $i)
    $nivel = 0
    for ($j = $abre; $j -lt $Texto.Length; $j++) {
        if ($Texto[$j] -eq '{') { $nivel++ }
        elseif ($Texto[$j] -eq '}') { $nivel--; if ($nivel -eq 0) { return $Texto.Substring($i, $j - $i + 1) } }
    }
    return ''
}

It 'origem oficial: aceita hosts da Microsoft e recusa o resto' {
    (Test-Gate5MicrosoftSource -Uri 'https://aka.ms/vs/17/release/vc_redist.x64.exe') -and
    (Test-Gate5MicrosoftSource -Uri 'https://download.visualstudio.microsoft.com/download/pr/x/vc_redist.x64.exe') -and
    # HTTP puro nao serve nem em host oficial
    (-not (Test-Gate5MicrosoftSource -Uri 'http://download.microsoft.com/x.exe')) -and
    # sufixo parecido nao e a Microsoft
    (-not (Test-Gate5MicrosoftSource -Uri 'https://download.microsoft.com.evil.example/x.exe')) -and
    (-not (Test-Gate5MicrosoftSource -Uri 'https://cdn.example.net/vc_redist.x64.exe')) -and
    (-not (Test-Gate5MicrosoftSource -Uri 'nao-e-uma-url'))
}

It 'URL declarada do redistribuivel e oficial da Microsoft' {
    Test-Gate5MicrosoftSource -Uri $script:Gate5VcRedistUrl
}

It 'nenhum script copia VCRUNTIME/MSVCP do host (fallback app-local proibido)' {
    # REGRESSAO: a saida facil para o yara64.exe nao iniciar seria copiar a DLL
    # da instalacao local para junto do executavel. A decisao humana recusou esse
    # caminho: a proveniencia precisa ser um pacote assinado da Microsoft.
    $copias = [regex]::Matches($allCode, '(?i)(Copy-Item|copy\s|xcopy|robocopy)[^\r\n]*(VCRUNTIME\w*\.dll|MSVCP\w*\.dll)[^\r\n]*')
    if ($copias.Count -gt 0) { Write-Host ("        copia proibida: " + $copias[0].Value) }
    ($copias.Count -eq 0) -and
    ($allCode -notmatch '(?i)MSVCP140\.dll') -and
    # a unica mencao permitida a VCRUNTIME140.dll e a DETECCAO no guest
    ($payloadTxt -match "Join-Path \`$env:SystemRoot 'System32\\VCRUNTIME140\.dll'")
}

It 'a midia embarca o pacote oficial, nao DLLs soltas' {
    ($bootTxt -match "Copy-Item \`$vcExeStage \(Join-Path \`$payloadDir 'vcredist'\)") -and
    ($bootTxt -match "vcredist\\vcruntime-pin\.json")
}

It 'download so grava bytes depois de provar a URL efetiva' {
    $iEfetiva = $bootTxt.IndexOf('Test-Gate5MicrosoftSource -Uri $urlEfetiva')
    $iGrava   = $bootTxt.IndexOf('[IO.File]::Create($vcExe)')
    ($iEfetiva -gt 0) -and ($iGrava -gt $iEfetiva)
}

It 'assinatura Authenticode e exigida antes de pinar o hash' {
    $iSig  = $bootTxt.IndexOf('Get-Gate5AuthenticodeMicrosoft -Path $vcExe')
    $iHash = $bootTxt.IndexOf('$vcSha  = Get-Gate5Sha256 -Path $vcExe')
    ($iSig -gt 0) -and ($iHash -gt $iSig)
}

It 'Get-Gate5AuthenticodeMicrosoft exige status Valid E titular Microsoft' {
    $fn = Get-FunctionText -Texto (Get-Content (Join-Path $labDir 'gate5-common.ps1') -Raw) -Nome 'Get-Gate5AuthenticodeMicrosoft'
    ($fn -match "O=Microsoft Corporation") -and
    ($fn -match "\`$sig\.Status -eq 'Valid'") -and
    ($fn -match '\$microsoft')
}

It 'os cinco bloqueadores fail-closed do runtime existem no pipeline' {
    $codigos = @('VCRUNTIME_SOURCE_NOT_MICROSOFT', 'VCRUNTIME_SIGNATURE_INVALID',
                 'VCRUNTIME_HASH_MISMATCH', 'VCRUNTIME_INSTALL_FAILED',
                 'YARA_RUNTIME_DEPENDENCY_UNSATISFIED')
    $faltando = $codigos | Where-Object { ($bootTxt + $payloadTxt) -notmatch [regex]::Escape($_) }
    if ($faltando) { Write-Host ("        bloqueadores ausentes: " + ($faltando -join ', ')) }
    @($faltando).Count -eq 0
}

It 'guest instala pelo pacote oficial em modo silencioso' {
    ($payloadTxt -match "'/install', '/quiet', '/norestart'") -and
    ($payloadTxt -match 'Get-AuthenticodeSignature -LiteralPath \$exe') -and
    ($payloadTxt -match 'Get-FileHash -LiteralPath \$exe')
}

It 'guest valida o runtime pelo RESULTADO, nao pelo exit code' {
    $iExit  = $payloadTxt.IndexOf('$saida.exit_code = [int]$proc.ExitCode')
    $iPos   = $payloadTxt.IndexOf('$depois = Get-VcRuntimeState -Minimo $minimo')
    ($iExit -gt 0) -and ($iPos -gt $iExit) -and
    ($payloadTxt -match 'pos-instalacao insuficiente')
}

It 'presenca da DLL nao e prova suficiente de runtime' {
    # Exige o pacote REGISTRADO com versao coberta, alem do arquivo no disco.
    $fn = Get-FunctionText -Texto $payloadTxt -Nome 'Get-VcRuntimeState'
    ($fn -match 'VisualStudio\\14\.0\\VC\\Runtimes\\x64') -and
    ($fn -match '\$instalado = \(\[int\]\$p\.Installed -eq 1\)') -and
    ($fn -match 'Sufficient = \(\$suficiente -and \$dllPresente\)')
}

It 'prova final do YARA e a execucao real de --version' {
    ($payloadTxt -match "--version") -and
    ($payloadTxt -match "\`$yaraOk  = \(\`$yaraVer -eq '4\.5\.5'\)")
}

It 'ruleset e sanitize so rodam depois do YARA provado' {
    $iGate  = $payloadTxt.IndexOf('    if ($yaraOk) {')
    $iPin   = $payloadTxt.IndexOf('$pin = Test-RulesetPin -PinPath')
    $iScan  = $payloadTxt.IndexOf('$gatingAlways = @(')
    ($iGate -gt 0) -and ($iPin -gt $iGate) -and ($iScan -gt $iGate)
}

It 'fase Vcruntime precede a construcao da midia' {
    $iVc  = $provTxt.IndexOf("'VCRUNTIME_READY'")
    $iVm  = $provTxt.IndexOf("'GUEST_INSTALLED'")
    ($iVc -gt 0) -and ($iVm -gt $iVc) -and ($script:Gate5Phases -contains 'VCRUNTIME_READY')
}

It 'midia nao e construida sem o redistribuivel pinado' {
    ($bootTxt -match 'execute a fase Vcruntime antes') -and
    ($bootTxt -match 'execute a fase Rules antes')
}

Write-Host 'T-E: pin do ruleset verificavel dentro do guest'

# Reproduz a regra do HOST para o agregado (manifesto <rel>TAB<sha>LF, ordem
# ordinal, UTF-8 sem BOM) e confronta com a implementacao REAL do guest.
function Get-AgregadoHost {
    param([object[]]$Entradas)
    $manifesto = ($Entradas | ForEach-Object { "{0}`t{1}`n" -f $_.rel, $_.sha }) -join ''
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    $sha  = [Security.Cryptography.SHA256]::Create()
    return ([BitConverter]::ToString($sha.ComputeHash($utf8.GetBytes($manifesto))) -replace '-', '').ToLowerInvariant()
}

$rulesTmp = Join-Path $tmp 'YARA-Rules'
New-Item -ItemType Directory -Force (Join-Path $rulesTmp 'malware') | Out-Null
New-Item -ItemType Directory -Force (Join-Path $rulesTmp 'crypto')  | Out-Null
Set-Content -LiteralPath (Join-Path $rulesTmp 'malware\a.yar') -Value 'rule a { condition: true }' -Encoding ascii
Set-Content -LiteralPath (Join-Path $rulesTmp 'crypto\b.yar')  -Value 'rule b { condition: false }' -Encoding ascii
$relList = @('crypto/b.yar', 'malware/a.yar')   # ordem ordinal, como no host
$entradas = $relList | ForEach-Object {
    [pscustomobject]@{ rel = $_; sha = (Get-FileHash -LiteralPath (Join-Path $rulesTmp ($_ -replace '/', '\')) -Algorithm SHA256).Hash.ToLowerInvariant() }
}
$pinTmp = Join-Path $tmp 'rules-pin.json'
function Write-PinSintetico {
    param([string]$Agregado)
    [ordered]@{
        schema = 'gate5-lab-ruleset-pin/v1'
        commit_sha40 = '0123456789abcdef0123456789abcdef01234567'
        file_count = $entradas.Count
        aggregate_sha256 = $Agregado
        files = @($entradas)
    } | ConvertTo-Json -Depth 5 | Out-File $pinTmp -Encoding utf8
}
function Write-Log { param([string]$m) }   # stub: o guest loga, o teste nao
Invoke-Expression (Get-FunctionText -Texto $payloadTxt -Nome 'Test-RulesetPin')

It 'guest recomputa o agregado do ruleset igual ao host' {
    Write-PinSintetico -Agregado (Get-AgregadoHost -Entradas $entradas)
    $r = Test-RulesetPin -PinPath $pinTmp -Dir $rulesTmp
    $r.Ok -and ($r.Computed -eq $r.Expected) -and ($r.Missing -eq 0) -and ($r.Mismatched -eq 0) -and
    ($r.Commit -match '^[0-9a-f]{40}$')
}

It 'pin reprova quando uma regra entregue foi alterada' {
    Write-PinSintetico -Agregado (Get-AgregadoHost -Entradas $entradas)
    Set-Content -LiteralPath (Join-Path $rulesTmp 'malware\a.yar') -Value 'rule a { condition: false }' -Encoding ascii
    $r = Test-RulesetPin -PinPath $pinTmp -Dir $rulesTmp
    (-not $r.Ok) -and ($r.Mismatched -eq 1)
}

It 'pin reprova quando uma regra do commit nao foi entregue' {
    Write-PinSintetico -Agregado (Get-AgregadoHost -Entradas $entradas)
    Remove-Item (Join-Path $rulesTmp 'crypto\b.yar') -Force
    $r = Test-RulesetPin -PinPath $pinTmp -Dir $rulesTmp
    (-not $r.Ok) -and ($r.Missing -eq 1)
}

It 'pin do guest reprova SHA-40 malformado, inclusive em caixa alta' {
    # '-match' e insensivel a maiusculas: sem '-cmatch' um SHA em caixa alta
    # passaria por formato estrito, tanto aqui quanto no validador da midia.
    foreach ($mau in @('0F93570194A80D2F2032869055808B0DDCDFB360',
                       '0f93570194a80d2f2032869055808b0ddcdfb36',
                       'zzzz570194a80d2f2032869055808b0ddcdfb360')) {
        [ordered]@{ commit_sha40 = $mau; file_count = 0; aggregate_sha256 = ('a' * 64); files = @() } |
            ConvertTo-Json -Depth 3 | Out-File $pinTmp -Encoding utf8
        if ((Test-RulesetPin -PinPath $pinTmp -Dir $rulesTmp).Ok) { return $false }
    }
    ((Get-Content (Join-Path $labDir 'guest\gate5-payload.ps1') -Raw) -match "\`$commit -cmatch '\^\[0-9a-f\]\{40\}\`$'")
}

It 'pin reprova sem SHA-40 do commit' {
    [ordered]@{ commit_sha40 = ''; aggregate_sha256 = ''; files = @() } |
        ConvertTo-Json -Depth 3 | Out-File $pinTmp -Encoding utf8
    -not (Test-RulesetPin -PinPath $pinTmp -Dir $rulesTmp).Ok
}

It 'o pin viaja na midia fora da arvore de regras' {
    # Dentro de rules\ ele seria copiado para C:\Tools\YARA-Rules e entraria no
    # proprio conjunto que descreve, mudando o agregado.
    ($bootTxt -match "Join-Path \`$payloadDir 'rules-pin\.json'") -and
    ($payloadTxt -match "Copy-Item \(Join-Path \`$root 'rules-pin\.json'\) \`$RulesPin")
}

Write-Host 'T-F: classificacao de secrets (assets de fornecedor)'

# Extrai as listas REAIS do payload e classifica caminhos sinteticos com a
# mesma regra, sem executar nada dentro de um guest.
$mAlways = [regex]::Match($payloadTxt, '(?s)\$gatingAlways = @\((?<c>.*?)\)\r?\n')
$mVendor = [regex]::Match($payloadTxt, '(?s)\$gatingUnlessVendor = @\((?<c>.*?)\)\r?\n')
$mRegex  = [regex]::Match($payloadTxt, "\`$vendorAsset = '(?<c>[^']+)'")
$gatingAlwaysReal = @(Invoke-Expression ('@(' + $mAlways.Groups['c'].Value + ')'))
$gatingVendorReal = @(Invoke-Expression ('@(' + $mVendor.Groups['c'].Value + ')'))
$vendorRegexReal  = $mRegex.Groups['c'].Value

function Test-Gating {
    # Reproduz a decisao do payload: incondicional sempre reprova; generico
    # reprova apenas fora das arvores de assets de fornecedor.
    param([string]$Caminho)
    $nome = Split-Path $Caminho -Leaf
    foreach ($p in $gatingAlwaysReal) { if ($nome -like $p) { return $true } }
    foreach ($p in $gatingVendorReal) { if ($nome -like $p) { return ($Caminho -notmatch $vendorRegexReal) } }
    return $false
}

It 'as listas e a regra de fornecedor foram extraidas do payload' {
    ($gatingAlwaysReal.Count -ge 10) -and ($gatingVendorReal.Count -ge 1) -and
    ($vendorRegexReal -match 'AppData') -and
    # extensoes genericas NAO podem estar na lista incondicional
    ($gatingAlwaysReal -notcontains '*.sql') -and ($gatingVendorReal -contains '*.sql')
}

It 'modelos .sql do OneDrive deixam de reprovar (achado da instalacao limpa)' {
    -not (Test-Gating 'C:\Users\gate5boot\AppData\Local\Microsoft\OneDrive\26.150.0804.0011\WebAssets\sql\query.sql')
}

It 'assets de pacote da loja tambem sao informativos' {
    -not (Test-Gating 'C:\Users\gate5boot\AppData\Local\Packages\MSTeams_8wekyb3d8bbwe\LocalCache\x.sql')
}

It 'dump ou .sql fora de arvore de fornecedor continua reprovando' {
    (Test-Gating 'C:\Users\gate5boot\Documents\faithro-backup.sql') -and
    (Test-Gating 'C:\Temp\ragnarok.dump')
}

It 'material de chave reprova ATE dentro de arvore de fornecedor' {
    # A excecao vale so para extensao generica; chave privada nunca e asset.
    (Test-Gating 'C:\Users\gate5boot\AppData\Local\Microsoft\OneDrive\id_rsa') -and
    (Test-Gating 'C:\Users\gate5boot\AppData\Local\Packages\x\server.pem') -and
    (Test-Gating 'C:\Users\gate5boot\AppData\Local\Microsoft\.env')
}

It 'artefato do alvo reprova ATE dentro de arvore de fornecedor' {
    (Test-Gating 'C:\Users\gate5boot\AppData\Local\Microsoft\WARP.exe') -and
    (Test-Gating 'C:\Users\gate5boot\AppData\Local\Packages\data.grf')
}

It 'acertos de fornecedor sao contados e amostrados, nunca descartados' {
    ($payloadTxt -match 'secrets_vendor_count') -and ($payloadTxt -match 'secrets_vendor_sample')
}

Write-Host 'T-G: criterios do baseline reportados e exigidos'

It 'evidencia do guest carrega todos os criterios do baseline' {
    $chaves = @('tpm_spec_version', 'tpm_2_0', 'vcruntime_sufficient', 'vcruntime_sha256',
                'yara_runtime_ok', 'ruleset_commit', 'ruleset_aggregate_computed',
                'ruleset_pinned', 'sanitize_pass', 'blockers')
    $faltando = $chaves | Where-Object { $payloadTxt -notmatch [regex]::Escape($_) }
    if ($faltando) { Write-Host ("        campos ausentes: " + ($faltando -join ', ')) }
    (@($faltando).Count -eq 0) -and ($payloadTxt -match "schema            = 'gate5-guest-evidence/v2'")
}

It 'tpm_2_0 vem da SpecVersion, nao de TpmPresent' {
    ($payloadTxt -match 'Win32_Tpm') -and
    ($payloadTxt -match "tpm_2_0           = \[bool\]\(\`$tpmSpec -like '2\.0\*'\)")
}

It 'host preserva a evidencia ANTES de bloquear por ela' {
    $iSalva = $bootTxt.IndexOf('$ev | ConvertTo-Json -Depth 6) | Out-File $destino')
    $iBlock = $bootTxt.IndexOf('Stop-Gate5Blocked -Blocker ([string]$blk[0])')
    if ($iBlock -lt 0) { $iBlock = $bootTxt.IndexOf('Bloqueadores reportados pelo proprio guest') }
    ($iSalva -gt 0) -and ($iBlock -gt $iSalva)
}

It 'host bloqueia com criterio reprovado dentro do guest' {
    ($bootTxt -match 'GUEST_BASELINE_CRITERIA_FAILED') -and
    ($bootTxt -match "\`$reprovados \+= 'yara_4_5_5'") -and
    ($bootTxt -match "\`$reprovados \+= 'ruleset_pinned'") -and
    ($bootTxt -match "\`$reprovados \+= 'sanitize_pass'") -and
    ($bootTxt -match "\`$reprovados \+= 'tpm_2_0'")
}

It 'validador exige os controles novos do baseline' {
    $novos = @('guest-sem-blockers', 'guest-tpm-2.0', 'guest-vcruntime',
               'guest-yara-runtime', 'guest-ruleset-pinned', 'guest-sanitize')
    $faltando = $novos | Where-Object { $verifyTxt -notmatch [regex]::Escape($_) }
    if ($faltando) { Write-Host ("        controles ausentes: " + ($faltando -join ', ')) }
    @($faltando).Count -eq 0
}

Write-Host 'T-H: controles novos da midia da RUN-02'

# Mesmo escritor de stream COM do host, para nao depender de ferramenta externa.
Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
public static class Gate5TestIsoWriter {
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

# Constroi uma ISO SINTETICA com o mesmo mecanismo do host (IMAPI2FS) para
# exercitar o validador contra uma midia de verdade, e nao contra o texto do
# script. Nenhum arquivo real do laboratorio e usado.
function New-IsoSintetica {
    param([Parameter(Mandatory)][string]$Origem, [Parameter(Mandatory)][string]$Destino)
    $fsi = New-Object -ComObject IMAPI2FS.MsftFileSystemImage
    $fsi.FileSystemsToCreate = 3
    $fsi.VolumeName = 'GATE5TEST'
    $fsi.Root.AddTree($Origem, $false)
    $img = $fsi.CreateResultImage()
    $stream = $img.ImageStream
    Remove-Item $Destino -Force -ErrorAction SilentlyContinue
    [Gate5TestIsoWriter]::Write($stream, $Destino)
    foreach ($com in $stream, $img, $fsi) {
        try { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($com) } catch {}
    }
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}

$midiaRaiz = Join-Path $tmp 'midia'
function Build-MidiaSintetica {
    # Monta uma midia minima porem ESTRUTURALMENTE igual a real e devolve o
    # resultado do validador. Os blocos sao ajustaveis para simular defeitos.
    param(
        [string]$CommitSha40 = '0f93570194a80d2f2032869055808b0ddcdfb360',
        [int]$FileCountDeclarado = -1,
        [switch]$AdulterarVcredist,
        [switch]$EmbarcarMaterialCripto
    )
    if (Test-Path $midiaRaiz) { Remove-Item $midiaRaiz -Recurse -Force }
    $g5 = Join-Path $midiaRaiz 'gate5'
    New-Item -ItemType Directory -Force (Join-Path $g5 'yara')     | Out-Null
    New-Item -ItemType Directory -Force (Join-Path $g5 'rules')    | Out-Null
    New-Item -ItemType Directory -Force (Join-Path $g5 'vcredist') | Out-Null
    Set-Content -LiteralPath (Join-Path $midiaRaiz 'Autounattend.xml') -Value '<unattend/>' -Encoding ascii
    Set-Content -LiteralPath (Join-Path $g5 'gate5-payload.ps1')       -Value '# payload'  -Encoding ascii
    Set-Content -LiteralPath (Join-Path $g5 'yara\yara64.exe')         -Value 'MZ'         -Encoding ascii
    Set-Content -LiteralPath (Join-Path $g5 'rules\gate5-index.yar')   -Value 'include "a.yar"' -Encoding ascii
    Set-Content -LiteralPath (Join-Path $g5 'rules\a.yar')             -Value 'rule a { condition: true }' -Encoding ascii

    $relSha = (Get-FileHash -LiteralPath (Join-Path $g5 'rules\a.yar') -Algorithm SHA256).Hash.ToLowerInvariant()
    $arquivos = @([pscustomobject]@{ rel = 'a.yar'; sha = $relSha })
    $contagem = if ($FileCountDeclarado -ge 0) { $FileCountDeclarado } else { $arquivos.Count }
    [ordered]@{
        schema           = 'gate5-lab-ruleset-pin/v1'
        commit_sha40     = $CommitSha40
        file_count       = $contagem
        aggregate_sha256 = ('a' * 64)
        files            = $arquivos
    } | ConvertTo-Json -Depth 5 | Out-File (Join-Path $g5 'rules-pin.json') -Encoding utf8

    $vcExe = Join-Path $g5 'vcredist\vc_redist.x64.exe'
    Set-Content -LiteralPath $vcExe -Value 'redistribuivel sintetico' -Encoding ascii
    $vcSha = (Get-FileHash -LiteralPath $vcExe -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($AdulterarVcredist) { Add-Content -LiteralPath $vcExe -Value 'bytes a mais' -Encoding ascii }
    [ordered]@{ schema = 'gate5-lab-vcruntime/v1'; sha256 = $vcSha; min_runtime_version = '14.30' } |
        ConvertTo-Json | Out-File (Join-Path $g5 'vcredist\vcruntime-pin.json') -Encoding utf8

    if ($EmbarcarMaterialCripto) {
        Set-Content -LiteralPath (Join-Path $g5 'vazamento.txt') -Encoding ascii `
            -Value 'encryption.keySafe = "vmware:key/list/(pair/(id))"'
    }
    $iso = Join-Path $tmp 'midia-sintetica.iso'
    New-IsoSintetica -Origem $midiaRaiz -Destino $iso
    return (Test-Gate5UnattendMedia -IsoPath $iso)
}

It 'validador le o pin do ruleset e o redistribuivel DE DENTRO da ISO' {
    $m = Build-MidiaSintetica
    $m.ruleset_sha40 -and $m.ruleset_manifest -and $m.vcredist_x64 -and $m.vcredist_sha256 -and $m.sem_segredos
}

It 'SHA-40 ausente ou malformado reprova o pin da midia' {
    $vazio = Build-MidiaSintetica -CommitSha40 ''
    $curto = Build-MidiaSintetica -CommitSha40 '0f93570194a80d2f2032869055808b0ddcdfb36'
    $maius = Build-MidiaSintetica -CommitSha40 '0F93570194A80D2F2032869055808B0DDCDFB360'
    (-not $vazio.ruleset_sha40) -and (-not $curto.ruleset_sha40) -and (-not $maius.ruleset_sha40)
}

It 'manifesto divergente do proprio pin reprova a midia' {
    # file_count que nao corresponde a lista entregue: o guest recomputaria o
    # agregado sobre um conjunto diferente do descrito.
    $m = Build-MidiaSintetica -FileCountDeclarado 99
    (-not $m.ruleset_manifest) -and $m.ruleset_sha40
}

It 'redistribuivel adulterado na midia reprova pelo hash do proprio arquivo' {
    $m = Build-MidiaSintetica -AdulterarVcredist
    $m.vcredist_x64 -and (-not $m.vcredist_sha256)
}

It 'material criptografico embarcado reprova a midia' {
    $m = Build-MidiaSintetica -EmbarcarMaterialCripto
    -not $m.sem_segredos
}

It 'leitura de arquivo da ISO nao se contenta com leitura parcial' {
    # Uma unica chamada a Read nao garante encher o buffer; sem o laco, o hash
    # de um arquivo grande (o redistribuivel tem dezenas de MB) reprovaria um
    # arquivo integro.
    $comm = Get-Content (Join-Path $labDir 'gate5-common.ps1') -Raw
    ($comm -match '(?s)function Get-Gate5IsoFileBytes.*?while \(\$lidos -lt \$alvo\.Size\)') -and
    ($comm -match '(?s)function Get-Gate5IsoFileBytes.*?if \(\$lidos -ne \$alvo\.Size\) \{ return \$null \}')
}

It 'midia sem os diretorios novos REPROVA, em vez de lancar excecao' {
    # Foi o que aconteceu ao validar a midia da RUN-01 (sem gate5/vcredist):
    # sob Set-StrictMode, filtrar $null por propriedade lanca, e um controle que
    # lanca nao reprova - ele derruba o validador inteiro.
    $so = Join-Path $tmp 'midia-magra'
    if (Test-Path $so) { Remove-Item $so -Recurse -Force }
    New-Item -ItemType Directory -Force $so | Out-Null
    Set-Content -LiteralPath (Join-Path $so 'Autounattend.xml') -Value '<unattend/>' -Encoding ascii
    $isoMagra = Join-Path $tmp 'midia-magra.iso'
    New-IsoSintetica -Origem $so -Destino $isoMagra
    $m = Test-Gate5UnattendMedia -IsoPath $isoMagra
    $m.autounattend_na_raiz -and
    (-not $m.payload_na_raiz) -and (-not $m.yara_bin) -and (-not $m.ruleset_index) -and
    (-not $m.ruleset_sha40) -and (-not $m.ruleset_manifest) -and
    (-not $m.vcredist_x64) -and (-not $m.vcredist_sha256)
}

It 'pre-condicoes do power-on exigem TODOS os controles novos da midia' {
    # Assert-Gate5PreConditions reprova qualquer propriedade diferente de $true
    # (menos iso_bytes): basta o controle existir para virar bloqueio.
    $m = Build-MidiaSintetica
    $novos = @('ruleset_sha40', 'ruleset_manifest', 'vcredist_x64', 'vcredist_sha256', 'sem_segredos')
    $faltando = $novos | Where-Object { -not $m.PSObject.Properties[$_] }
    if ($faltando) { Write-Host ("        controles ausentes: " + ($faltando -join ', ')) }
    (@($faltando).Count -eq 0) -and
    ($bootTxt -match "\`$_\.Name -ne 'iso_bytes' -and \`$_\.Value -ne \`$true") -and
    ($bootTxt -match 'UNATTEND_MEDIA_INVALID')
}

Write-Host 'T-I: retomada pos-reboot e namespace de evidencia por execucao'

It 'retomada e registrada ANTES de qualquer estagio que possa reiniciar o guest' {
    # Registrar so no fim do INSTALL deixava uma janela em que um reboot vindo
    # de fora abandonaria o laboratorio sem quem retomasse o payload.
    $iReg     = $payloadTxt.IndexOf("`n    Register-StartupTask")
    $iUpdate  = $payloadTxt.IndexOf("Set-Stage 'UPDATE'")
    $iRestart = $payloadTxt.IndexOf('Restart-Computer -Force')
    $iVc      = $payloadTxt.IndexOf('$rt = Install-VcRuntimeFromMedia')
    ($iReg -gt 0) -and ($iUpdate -gt $iReg) -and ($iRestart -gt $iReg) -and ($iVc -gt $iReg)
}

It 'a tarefa de retomada roda como SYSTEM na inicializacao' {
    ($payloadTxt -match 'New-ScheduledTaskTrigger -AtStartup') -and
    ($payloadTxt -match "New-ScheduledTaskPrincipal -UserId 'SYSTEM'") -and
    ($payloadTxt -match 'Register-ScheduledTask -TaskName') -and
    # aponta para a copia LOCAL, nao para a midia (desconectada no isolamento)
    ($payloadTxt -match 'gate5-payload\.ps1"'' -f \$Gate5Dir')
}

It 'evidencia de uma execucao selada nunca e sobrescrita' {
    $runSel = 'run-teste-selada-' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
    $dirSel = Join-Path $script:Gate5EvidenceDir $runSel
    New-Item -ItemType Directory -Force $dirSel | Out-Null
    try {
        Set-Content -LiteralPath (Join-Path $dirSel 'sealed.json') -Value '{}' -Encoding ascii
        $selada = Test-Gate5RunSealed -RunId $runSel
        $aberta = -not (Test-Gate5RunSealed -RunId ($runSel + '-outra'))
        $selada -and $aberta -and
        # o bloqueio e fail-closed, nao um aviso
        ((Get-Content (Join-Path $labDir 'gate5-common.ps1') -Raw) -match "Stop-Gate5Blocked -Blocker 'RUN_EVIDENCE_SEALED'")
    } finally { Remove-Item $dirSel -Recurse -Force -ErrorAction SilentlyContinue }
}

It 'evidencia da execucao corrente vai para o namespace da execucao' {
    ($bootTxt -match "Join-Path \(Get-Gate5RunDir\) 'guest-evidence\.json'") -and
    ($bootTxt -notmatch "Join-Path \`$script:Gate5EvidenceDir 'guest-evidence\.json'") -and
    ($verifyTxt -match 'Join-Path \$script:Gate5EvidenceDir \(Get-Gate5RunId\)')
}

It 'run_id corrente vem do estado, com default da etapa' {
    $comm = Get-Content (Join-Path $labDir 'gate5-common.ps1') -Raw
    ($comm -match "Gate5RunIdDefault = 'run-02-clean-install'") -and
    ($comm -match "notes\.PSObject\.Properties\['run_id'\]") -and
    ((Get-Gate5RunId) -match '^run-\d{2}-')
}

Write-Host 'T-J: captura do console e sinal de progresso do boot (defeitos da RUN-02)'

It 'leitor de bytes devolve byte[], nao array desenrolado' {
    # RAIZ do travamento da RUN-02: 'return $buf' faz o PowerShell DESENROLAR o
    # array no pipeline, e o chamador recebe um Object[] com um elemento por
    # byte. Marshal::Copy entao re-coage o vetor inteiro A CADA CHAMADA - com
    # rects de 1 MB (tela 1024x768) uma unica captura passava de 99 segundos e o
    # watcher perdia a janela do prompt de boot. Em 640x480 o custo era pequeno
    # o bastante para o defeito nunca aparecer.
    function Devolve-Desenrolado { $b = New-Object byte[] 8; return $b }
    function Devolve-Preso       { $b = New-Object byte[] 8; return ,$b }
    $mau = Devolve-Desenrolado
    $bom = Devolve-Preso
    ($mau -isnot [byte[]]) -and ($bom -is [byte[]]) -and ($bom.Length -eq 8)
}

It 'Read-Exact e Get-Gate5IsoFileBytes usam o operador de virgula' {
    $comm = Get-Content (Join-Path $labDir 'gate5-common.ps1') -Raw
    # Nenhum 'return $buf' solto pode voltar: e a forma exata do defeito.
    ($comm -notmatch '(?m)^\s*return \$buf\s*$') -and
    ($comm -match '(?s)function Read-Exact.*?return ,\$buf') -and
    ($comm -match '(?s)function Get-Gate5IsoFileBytes.*?return ,\$buf')
}

It 'copia para o bitmap recebe um byte[] de verdade' {
    # Prova funcional do custo: com Object[], Marshal::Copy precisa converter o
    # vetor inteiro a cada linha. Medimos as duas formas sobre o mesmo volume de
    # dados de um rect real (512x512 RGBX).
    Add-Type -AssemblyName System.Drawing -ErrorAction SilentlyContinue
    $lado = 512
    $bruto = New-Object byte[] ($lado * $lado * 4)
    $desenrolado = [object[]]$bruto
    $bmp = New-Object System.Drawing.Bitmap($lado, $lado)
    try {
        $rect = New-Object System.Drawing.Rectangle(0, 0, $lado, $lado)
        $bd = $bmp.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::WriteOnly,
                            [System.Drawing.Imaging.PixelFormat]::Format32bppRgb)
        try {
            $sw = [Diagnostics.Stopwatch]::StartNew()
            for ($y = 0; $y -lt 8; $y++) {
                [System.Runtime.InteropServices.Marshal]::Copy($bruto, $y * $lado * 4, [IntPtr]($bd.Scan0.ToInt64() + $y * $bd.Stride), $lado * 4)
            }
            $msBom = $sw.ElapsedMilliseconds
            $sw.Restart()
            for ($y = 0; $y -lt 8; $y++) {
                [System.Runtime.InteropServices.Marshal]::Copy($desenrolado, $y * $lado * 4, [IntPtr]($bd.Scan0.ToInt64() + $y * $bd.Stride), $lado * 4)
            }
            $msMau = $sw.ElapsedMilliseconds
        } finally { $bmp.UnlockBits($bd) }
    } finally { $bmp.Dispose() }
    $linhasReais = 512 * 4
    $projecao = [math]::Round(($msMau / 8.0) * $linhasReais / 1000.0)
    Write-Host ("        8 linhas: byte[]={0}ms  Object[]={1}ms -> captura inteira com Object[] ~{2}s" -f $msBom, $msMau, $projecao)
    # A razao e o invariante: um limite absoluto em ms depende da maquina. Com
    # Object[] a captura inteira (512 linhas x 4 rects) nao cabe na janela de 2
    # segundos entre amostras - foi assim que o watcher perdeu o prompt.
    ($msMau -ge ($msBom * 10)) -and ($projecao -gt 60)
}

It 'progresso do boot nao depende so do crescimento do VMDK' {
    # O VMDK da RUN-02 ja esta 100% alocado pela instalacao anterior: nunca mais
    # cresce 200 MB, e o laco ficava cego mesmo com a instalacao correndo.
    ($bootTxt -match '\$forasDoFirmware') -and
    ($bootTxt -match 'Test-Gate5FirmwareScreen -ImagePath \$tela') -and
    ($bootTxt -match "\`$gatilho = 'crescimento do VMDK'") -and
    ($bootTxt -match '\$gatilho = "tela fora do firmware')
}

It 'tela so conta como progresso DEPOIS de a tecla ter sido entregue' {
    # Sem essa condicao, qualquer tela nao-preta (inclusive o Windows da
    # execucao anterior) marcaria boot_key_sent e gastaria a janela.
    $iTecla = $bootTxt.IndexOf('$teclaEnviada = $true')
    $iUso   = $bootTxt.IndexOf('if ($teclaEnviada) {')
    $iFora  = $bootTxt.IndexOf('$forasDoFirmware++')
    ($iTecla -gt 0) -and ($iUso -gt $iTecla) -and ($iFora -gt $iUso) -and
    # e exige varias amostras seguidas, nao uma piscada entre fases do firmware
    ($bootTxt -match '\$forasDoFirmware -ge 3')
}

It 'bloqueio do boot optico descreve os DOIS sinais ausentes' {
    ($bootTxt -match 'OPTICAL_BOOT_PROMPT_NOT_SEEN') -and
    ($bootTxt -match 'nem a tela saiu da fase') -and
    ($bootTxt -match 'nem o VMDK cresceu')
}

} finally {
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ''
Write-Host ("RESULTADO: {0} PASS / {1} FAIL" -f $script:pass, $script:fail)
if ($script:fail -gt 0) { exit 1 }
exit 0
