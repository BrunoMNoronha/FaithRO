#Requires -Version 5.1
# Fixtures sinteticas; nao utiliza cliente real, rede ou VM.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path $PSScriptRoot 'configurar-cliente-windows.ps1'
$testRoot = Join-Path ([IO.Path]::GetTempPath()) ('faithro-client-test-' + [guid]::NewGuid().ToString('N'))
$source = Join-Path $testRoot 'source'
New-Item -ItemType Directory -Path $source | Out-Null
foreach ($name in @('Ragexe.exe', 'data.grf', 'Setup.exe')) {
    [IO.File]::WriteAllText((Join-Path $source $name), 'fixture sintetica ' + $name)
}
New-Item -ItemType Directory -Path (Join-Path $source 'BGM') | Out-Null
[IO.File]::WriteAllText((Join-Path $source 'BGM/test.txt'), 'fixture')
$expected = (Get-FileHash -LiteralPath (Join-Path $source 'Ragexe.exe')).Hash
$before = (Get-FileHash -LiteralPath (Join-Path $source 'Ragexe.exe')).Hash
$mockSignature = @{ State = 'Valid' }
# Mock so nesta suite; o script de producao usa o cmdlet real.
${function:Get-AuthenticodeSignature} = {
    param([string]$LiteralPath)
    [PSCustomObject]@{ Status =  $mockSignature.State; SignerCertificate = [PSCustomObject]@{ Subject = 'CN=GRAVITY Co., Ltd.' } }
}.GetNewClosure()
$common = @{ ClientPath = $source; ExpectedExecutableSha256 = $expected }
$script:passed = 0
function Assert-Test([bool]$Condition, [string]$Name) {
    if (-not $Condition) { throw "FAIL: $Name" }
    $script:passed++
    Write-Host "PASS: $Name"
}
function Assert-Rejected($Arguments, [string]$Name) {
    $rejected = $false
    try { & $scriptPath @common @Arguments } catch { $rejected = $true }
    Assert-Test $rejected $Name
}
$dry = Join-Path $testRoot 'dry'
& $scriptPath @common -BackupPath $dry -WhatIf
Assert-Test (-not (Test-Path -LiteralPath $dry)) 'WhatIf nao cria backup ou configuracao'
$copy = Join-Path $testRoot 'backup-only'
& $scriptPath @common -BackupPath $copy
Assert-Test ((Get-FileHash -LiteralPath (Join-Path $copy 'Ragexe.exe')).Hash -eq $before) 'backup do executavel confere'
Assert-Test (-not (Test-Path -LiteralPath (Join-Path $copy 'data.grf')) -and
    -not (Test-Path -LiteralPath (Join-Path $copy 'BGM'))) 'nao copia GRFs ou diretorio inteiro'
Assert-Test (-not (Test-Path -LiteralPath (Join-Path $source 'data/clientinfo.xml'))) 'nao inventa XML por padrao'
Assert-Rejected @{BackupPath=$copy} 'recusa sobrescrever backup'
Assert-Rejected @{BackupPath=(Join-Path $source 'nested')} 'recusa backup dentro do cliente'
Assert-Rejected @{BackupPath=(Join-Path $PSScriptRoot 'forbidden-client')} 'recusa backup no repositorio'
Assert-Rejected @{BackupPath=(Join-Path $testRoot 'missing-xml');ConnectionFile='clientinfo.xml'} 'XML exige valores explicitos'
$mockSignature.State = 'NotSigned'
Assert-Rejected @{BackupPath=(Join-Path $testRoot 'unsigned')} 'recusa assinatura invalida'
$mockSignature.State = 'Valid'
$data = Join-Path $source 'data'
New-Item -ItemType Directory -Path $data | Out-Null
$xmlFile = Join-Path $data 'clientinfo.xml'
[IO.File]::WriteAllText($xmlFile,'<clientinfo>original</clientinfo>')
$originalXml = (Get-FileHash -LiteralPath $xmlFile).Hash
$xmlBackup = Join-Path $testRoot 'xml-backup'
& $scriptPath @common -BackupPath $xmlBackup -ConnectionFile clientinfo.xml -ServerHost 127.0.0.1 `
    -ServiceType korea -ServerType primary -ClientVersion 1 -LangType 1 -DisplayName 'Teste & teste'
Assert-Test ((Get-FileHash -LiteralPath (Join-Path $xmlBackup 'data/clientinfo.xml')).Hash -eq $originalXml) 'XML anterior preservado antes de substituir'
[xml]$xml = Get-Content -LiteralPath $xmlFile -Raw
Assert-Test ($xml.clientinfo.connection.display -eq 'Teste & teste') 'XML escapa caracteres corretamente'
Assert-Test ((Get-FileHash -LiteralPath (Join-Path $source 'Ragexe.exe')).Hash -eq $before) 'executavel original intacto'
$evidence = Get-Content -LiteralPath (Join-Path $xmlBackup 'faithro-preparation.json') -Raw | ConvertFrom-Json
Assert-Test (-not $evidence.login_validated -and $evidence.new_files.Count -eq 0) 'evidencia registra atualizacao sem alegar login'
$newBackup = Join-Path $testRoot 'new-xml-backup'
& $scriptPath @common -BackupPath $newBackup -ConnectionFile sclientinfo.xml -ServerHost 127.0.0.1 `
    -ServiceType korea -ServerType primary -ClientVersion 1 -LangType 1
$evidence = Get-Content -LiteralPath (Join-Path $newBackup 'faithro-preparation.json') -Raw | ConvertFrom-Json
Assert-Test ($evidence.new_files.Count -eq 1 -and $evidence.new_files[0] -eq 'data/sclientinfo.xml') 'evidencia identifica arquivo novo para rollback'
Write-Host "RESULTADO: $script:passed PASS; fixtures preservadas em $testRoot"
