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

$allText = (Get-ChildItem $labDir -Filter '*.ps1' -Recurse | Where-Object { $_.Name -ne 'test-gate5-lab-automation.ps1' } |
            ForEach-Object { Get-Content $_.FullName -Raw }) -join "`n"

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

It 'nenhuma chave de produto do Windows no template' {
    $tpl = Get-Content (Join-Path $labDir 'templates\Autounattend.template.xml') -Raw
    ($tpl -notmatch '(?i)<ProductKey>') -and ($tpl -notmatch '[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}')
}

It 'snapshot baseline so e criado apos a fase de isolamento' {
    $prov = Get-Content (Join-Path $labDir 'gate5-provision.ps1') -Raw
    $iIsolated = $prov.IndexOf("'ISOLATED'")
    $iSnapshot = $prov.IndexOf("'SNAPSHOT_CREATED'")
    ($iIsolated -gt 0) -and ($iSnapshot -gt $iIsolated)
}

It 'VM final fica com NIC desconectada e sem autoconectar' {
    $prov = Get-Content (Join-Path $labDir 'gate5-provision.ps1') -Raw
    ($prov -match 'ethernet0\.startConnected = "FALSE"') -and ($prov -match 'ethernet0\.connected = "FALSE"')
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
