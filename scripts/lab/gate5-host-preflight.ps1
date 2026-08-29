# gate5-host-preflight.ps1 - Pre-flight do HOST para o laboratorio GATE 5.
# Somente leitura + registro. Exit 0 = host apto; exit != 0 = inapto/bloqueado.
# Nao altera Hyper-V/VBS, nao instala nada, nao acessa rede.

[CmdletBinding()]
param([switch]$AsChild)  # quando chamado pelo entrypoint, nao finaliza o processo com Stop-*

. (Join-Path $PSScriptRoot 'gate5-common.ps1')
if (-not (Get-Variable -Name Gate5LogFile -Scope Script -ErrorAction SilentlyContinue)) { Initialize-Gate5Log }

$result = [ordered]@{ pass = $true; failures = @() }
function Add-Failure([string]$Msg) { $result.pass = $false; $result.failures += $Msg; Write-Gate5Log $Msg 'FAIL' }

$os  = Get-CimInstance Win32_OperatingSystem
$cs  = Get-CimInstance Win32_ComputerSystem
$cpu = Get-CimInstance Win32_Processor
$c   = Get-PSDrive C

Write-Gate5Log ("host os={0} build={1} arch={2}" -f $os.Caption, $os.BuildNumber, $os.OSArchitecture)
Write-Gate5Log ("host cpu={0} cores={1} lp={2}" -f $cpu.Name, $cpu.NumberOfCores, $cpu.NumberOfLogicalProcessors)
Write-Gate5Log ("host ram_bytes={0} hypervisor_present={1}" -f $cs.TotalPhysicalMemory, $cs.HypervisorPresent)
Write-Gate5Log ("host c_free_bytes={0}" -f $c.Free)

# Windows 11 x64 (build >= 22000)
if ([int]$os.BuildNumber -lt 22000 -or $os.OSArchitecture -notmatch '64') { Add-Failure 'PREFLIGHT: host nao e Windows 11 x64.' }

# CPU x64 com virtualizacao. Com Hyper-V/VBS ativos o firmware flag aparece
# como False no Win32_Processor; HypervisorPresent=True tambem comprova suporte.
if (-not ($cpu.VirtualizationFirmwareEnabled -or $cs.HypervisorPresent)) {
    Add-Failure 'PREFLIGHT: virtualizacao nao disponivel (nem firmware nem hypervisor presente).'
}
if ($cs.HypervisorPresent) {
    Write-Gate5Log 'AVISO: Hyper-V/VBS ativo no host. NAO sera desativado automaticamente; VMware Workstation moderno usa Windows Hypervisor Platform. Se houver conflito real, reportar HOST_VIRTUALIZATION_CONFLICT_REQUIRES_DECISION.' 'WARN'
}

# RAM fisica >= 16 GB (tolerancia de 5% para reserva de firmware)
if ($cs.TotalPhysicalMemory -lt (16GB * 0.95)) { Add-Failure ("PREFLIGHT: RAM fisica insuficiente ({0} bytes < ~16 GB)." -f $cs.TotalPhysicalMemory) }

# Espaco em disco: VM thin de 60 GB + ISO/instaladores; margem minima de 40 GB
# livres para iniciar (thin cresce sob demanda; abortamos antes de criar o VMDK
# se nao houver margem segura - risco R7).
$minFree = 40GB
if ($c.Free -lt $minFree) { Add-Failure ("PREFLIGHT: espaco livre em C: insuficiente ({0:N1} GB < 40 GB)." -f ($c.Free / 1GB)) }

# Privilegio administrativo: exigido SOMENTE para o que realmente precisa dele -
# instalar o VMware e criar o diretorio da VM. Depois disso o laboratorio opera
# sem privilegio administrativo (menor privilegio, que e o estado preferivel), e
# exigir elevacao em toda execucao apenas impediria a retomada, sem ganho de
# seguranca. Nesta maquina a elevacao ainda usa outra conta administrativa, o que
# tornaria os segredos DPAPI dependentes dela.
$vmwareFound     = $null -ne (Find-Gate5VmwareInstall)
$vmDirWritable   = Test-Gate5PathWritable -Path $script:Gate5VmDir
$elevated        = Test-Gate5Elevated
$needsElevation  = (-not $vmwareFound) -or (-not $vmDirWritable)
Write-Gate5Log ("host vmware_instalado={0} vm_dir_gravavel={1} elevado={2} elevacao_necessaria={3}" -f $vmwareFound, $vmDirWritable, $elevated, $needsElevation)
if ($needsElevation -and -not $elevated) {
    if (-not $vmwareFound) {
        Add-Failure 'PREFLIGHT: VMware Workstation nao esta instalado e a sessao nao esta elevada (a instalacao exige Administrator).'
    } else {
        Add-Failure ("PREFLIGHT: sem permissao de escrita em {0} e a sessao nao esta elevada." -f $script:Gate5VmDir)
    }
}

# Registro de evidencia do pre-flight
$evidence = [ordered]@{
    schema        = 'gate5-lab-host-preflight/v1'
    timestamp_utc = [DateTime]::UtcNow.ToString('s') + 'Z'
    os            = $os.Caption
    os_build      = $os.BuildNumber
    os_arch       = $os.OSArchitecture
    cpu           = $cpu.Name
    ram_bytes     = $cs.TotalPhysicalMemory
    hypervisor_present = [bool]$cs.HypervisorPresent
    c_free_bytes  = $c.Free
    elevated          = $elevated
    vmware_installed  = $vmwareFound
    vm_dir_writable   = $vmDirWritable
    elevation_needed  = $needsElevation
    pass          = $result.pass
    failures      = $result.failures
}
$evidence | ConvertTo-Json -Depth 4 | Out-File (Join-Path $script:Gate5EvidenceDir 'host-preflight.json') -Encoding utf8

if (-not $result.pass) {
    Write-Gate5Log ('PREFLIGHT FAIL: ' + ($result.failures -join ' | ')) 'FAIL'
    exit 1
}
Write-Gate5Log 'PREFLIGHT PASS'
exit 0
