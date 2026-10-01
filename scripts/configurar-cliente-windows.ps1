#Requires -Version 5.1
<#
.SYNOPSIS
Cria backup dos arquivos envolvidos e configura o cliente instalado, sem VM.
.DESCRIPTION
Nao copia a instalacao inteira nem altera binarios/GRFs. XML opcional exige
valores explicitos. Use -WhatIf para validar sem escrever.
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [Alias('SourcePath')][string]$ClientPath = 'C:\Gravity\Ragnarok',
    [Parameter(Mandatory = $true)][string]$BackupPath,
    [ValidatePattern('^[a-fA-F0-9]{64}$')]
    [string]$ExpectedExecutableSha256 = '8990A9A9CD6623E173BCC8B406A311AF32773EB881E539082126B768C14E95A0',
    [ValidateSet('clientinfo.xml', 'sclientinfo.xml')][string]$ConnectionFile,
    [string]$ServerHost,
    [ValidateRange(1, 65535)][int]$LoginPort = 6900,
    [string]$ServiceType,
    [string]$ServerType,
    [ValidateRange(0, 2147483647)][int]$ClientVersion,
    [ValidateRange(0, 2147483647)][int]$LangType,
    [string]$DisplayName = 'FaithRO - Laus Deo'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
function Assert-PlainPath([string]$Path) {
    $cursor = $Path
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            $item = Get-Item -LiteralPath $cursor -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Link/junction nao permitido: $cursor"
            }
        }
        $parent = Split-Path -Path $cursor -Parent
        if ($parent -eq $cursor) { break }
        $cursor = $parent
    }
}
function Test-Within([string]$Child, [string]$Parent) {
    return $Child.Equals($Parent, [StringComparison]::OrdinalIgnoreCase) -or
        $Child.StartsWith(($Parent.TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar), [StringComparison]::OrdinalIgnoreCase)
}
function Write-Evidence($Evidence) {
    [IO.File]::WriteAllText($evidencePath, (($Evidence | ConvertTo-Json -Depth 8) + "`n"), (New-Object Text.UTF8Encoding($false)))
}
$client = [IO.Path]::GetFullPath($ClientPath).TrimEnd('\', '/')
$backup = [IO.Path]::GetFullPath($BackupPath).TrimEnd('\', '/')
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\', '/')
if (-not (Test-Path -LiteralPath $client -PathType Container)) { throw 'Cliente instalado nao encontrado.' }
if ((Test-Within $backup $client) -or (Test-Within $client $backup)) { throw 'Backup deve ficar separado da instalacao.' }
if ((Test-Within $client $repoRoot) -or (Test-Within $backup $repoRoot)) { throw 'Cliente e backup devem ficar fora do repositorio.' }
Assert-PlainPath $client
Assert-PlainPath $backup
if (Test-Path -LiteralPath $backup) { throw 'Backup ja existe; escolha uma nova pasta.' }
if (-not (Test-Path -LiteralPath (Split-Path $backup -Parent) -PathType Container)) { throw 'Pasta pai do backup inexistente.' }
foreach ($required in @('Ragexe.exe','data.grf','Setup.exe')) {
    $path = Join-Path $client $required
    Assert-PlainPath $path
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Arquivo obrigatorio ausente: $required" }
}
$exe = Join-Path $client 'Ragexe.exe'
$signature = Get-AuthenticodeSignature -LiteralPath $exe
if ($signature.Status -ne 'Valid' -or -not $signature.SignerCertificate -or
    $signature.SignerCertificate.Subject -notmatch '(?i)GRAVITY') { throw 'Assinatura valida da Gravity nao comprovada.' }
if ((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ne $ExpectedExecutableSha256) { throw 'Ragexe divergente da baseline informada.' }
$xmlParameters = @('ServerHost','ServiceType','ServerType','ClientVersion','LangType')
$xmlPath = $null
if ($ConnectionFile) {
    foreach ($parameter in $xmlParameters) {
        if (-not $PSBoundParameters.ContainsKey($parameter)) { throw "XML exige valor homologado explicito: -$parameter" }
    }
    foreach ($value in @($ServerHost,$ServiceType,$ServerType,$DisplayName)) {
        if ([string]::IsNullOrWhiteSpace($value) -or $value -match '[<>\r\n]') { throw 'Valor XML invalido ou placeholder.' }
    }
    if ([Uri]::CheckHostName($ServerHost) -eq [UriHostNameType]::Unknown) { throw 'Host invalido.' }
    $dataPath = Join-Path $client 'data'
    Assert-PlainPath $dataPath
    if ((Test-Path -LiteralPath $dataPath) -and -not (Test-Path -LiteralPath $dataPath -PathType Container)) { throw 'data deve ser uma pasta.' }
    $xmlPath = Join-Path $dataPath $ConnectionFile
    Assert-PlainPath $xmlPath
    if ((Test-Path -LiteralPath $xmlPath) -and -not (Test-Path -LiteralPath $xmlPath -PathType Leaf)) { throw 'Destino XML deve ser arquivo.' }
} elseif (@($xmlParameters + @('LoginPort','DisplayName') | Where-Object { $PSBoundParameters.ContainsKey($_) }).Count -gt 0) {
    throw 'Parametros de conexao exigem -ConnectionFile.'
}
# Apenas arquivos de configuracao e executaveis pequenos; GRFs nao sao alterados/copiados.
$relativePaths = @('Ragexe.exe','Setup.exe','data.ini','data/clientinfo.xml','data/sclientinfo.xml')
$inventory = @(
    foreach ($relative in $relativePaths) {
        $path = Join-Path $client $relative
        Assert-PlainPath $path
        if (Test-Path -LiteralPath $path) {
            if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Esperado arquivo: $relative" }
            [ordered]@{path=$relative; sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash}
        }
    }
)
if (-not $PSCmdlet.ShouldProcess($client, "Criar backup em $backup e gravar XML se solicitado")) { return }
$evidencePath = Join-Path $backup 'faithro-preparation.json'
$evidence = [ordered]@{
    schema_version=1; status='BACKUP_IN_PROGRESS'; created_utc=[DateTime]::UtcNow.ToString('o')
    client=$client; backup=$backup; files=$inventory; new_files=@(); new_directories=@()
    binary_patching_performed=$false; client_executed=$false; login_validated=$false
    connection_file=$null; connection_sha256=$null
}
New-Item -ItemType Directory -Path $backup | Out-Null
try {
    Write-Evidence $evidence
    foreach ($file in $inventory) {
        $target = Join-Path $backup $file.path
        $parent = Split-Path $target -Parent
        if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
        Copy-Item -LiteralPath (Join-Path $client $file.path) -Destination $target
        if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $file.sha256) { throw 'Backup divergente; configuracao nao aplicada.' }
    }
    foreach ($file in $inventory) {
        if ((Get-FileHash -LiteralPath (Join-Path $client $file.path) -Algorithm SHA256).Hash -ne $file.sha256) { throw 'Cliente mudou durante o backup; interrompa os processos.' }
    }
    $evidence.status='BACKUP_VERIFIED'
    Write-Evidence $evidence
    if ($ConnectionFile) {
        if (-not (Test-Path -LiteralPath $dataPath)) { $evidence.new_directories=@('data') }
        if (-not (Test-Path -LiteralPath $xmlPath)) { $evidence.new_files=@('data/' + $ConnectionFile) }
        $evidence.status='CONFIGURATION_IN_PROGRESS'
        Write-Evidence $evidence
        if (-not (Test-Path -LiteralPath $dataPath)) { New-Item -ItemType Directory -Path $dataPath | Out-Null }
        $settings = New-Object Xml.XmlWriterSettings
        $settings.Encoding = New-Object Text.UTF8Encoding($false)
        $settings.Indent = $true
        # Monta o XML em memoria antes de substituir qualquer configuracao.
        $stream = New-Object IO.MemoryStream
        $writer = [Xml.XmlWriter]::Create($stream, $settings)
        try {
            $writer.WriteStartDocument(); $writer.WriteStartElement('clientinfo')
            $writer.WriteElementString('servicetype',$ServiceType); $writer.WriteElementString('servertype',$ServerType)
            $writer.WriteStartElement('connection')
            foreach ($pair in @(@('display',$DisplayName),@('address',$ServerHost),@('port',[string]$LoginPort),
                @('version',[string]$ClientVersion),@('langtype',[string]$LangType))) { $writer.WriteElementString($pair[0],$pair[1]) }
            $writer.WriteEndElement(); $writer.WriteEndElement(); $writer.WriteEndDocument(); $writer.Flush()
            $bytes = $stream.ToArray()
        } finally { $writer.Dispose(); $stream.Dispose() }
        [IO.File]::WriteAllBytes($xmlPath,$bytes)
        $evidence.connection_file='data/' + $ConnectionFile
        $evidence.connection_sha256=(Get-FileHash -LiteralPath $xmlPath -Algorithm SHA256).Hash
    }
    $evidence.status='PREPARED_NOT_PATCHED_NOT_LOGIN_VALIDATED'
    Write-Evidence $evidence
    Write-Host "[OK] Backup verificado: $backup"
    Write-Host '[INFO] Cliente configurado quando XML solicitado. Sem patches ou login; GRFs intactos.'
} catch {
    $evidence.status='FAILED_CHECK_BACKUP_BEFORE_RETRY'
    Write-Evidence $evidence
    Write-Warning 'Interrompido. Preserve backup/evidencias e confira o XML antes de tentar novamente.'
    throw
}
