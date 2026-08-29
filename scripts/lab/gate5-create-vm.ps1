# gate5-create-vm.ps1 - Cria a VM FaithRO-GATE5-LAB (VMX + VMDK thin 60 GB).
# Idempotente: se a VM ja existe com configuracao valida, nao recria.
# Requer: VMware Workstation Pro instalado e ISO Windows 11 validada.
#
# Secure Boot: uefi.secureBoot.enabled = TRUE (mecanismo suportado).
# vTPM: managedvm.autoAddVTPM = "software" - mecanismo oficial do Workstation
# (17+/26H1) que adiciona TPM virtual sem exigir criptografia completa da VM.
# Se o guest nao comprovar TpmPresent/TpmReady, o verificador falha e a etapa
# para com VTPM_AUTOMATION_NOT_SUPPORTED (nunca improvisar chaves .vmx).

[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$IsoPath,
    [switch]$AsChild
)

. (Join-Path $PSScriptRoot 'gate5-common.ps1')
if (-not (Get-Variable -Name Gate5LogFile -Scope Script -ErrorAction SilentlyContinue)) { Initialize-Gate5Log }

$vmware = Find-Gate5VmwareInstall
if (-not $vmware) { throw 'GATE5: VMware Workstation nao instalado; execute gate5-provision.ps1.' }
if (-not (Test-Path $IsoPath)) { throw "GATE5: ISO nao encontrada: $IsoPath" }

if (-not (Test-Path $script:Gate5VmDir)) { New-Item -ItemType Directory -Force $script:Gate5VmDir | Out-Null }

$vmdkPath = Join-Path $script:Gate5VmDir 'FaithRO-GATE5-LAB.vmdk'

# --- Disco: 60 GB thin (growable single file, adapter nvme) -------------------
if (Test-Path $vmdkPath) {
    Write-Gate5Log "VMDK ja existe, preservando: $vmdkPath"
} else {
    Write-Gate5Log 'Criando VMDK thin de 60 GB (nvme, growable)...'
    $vd = Invoke-Gate5Native -FilePath $vmware.VdiskManagerExe -Arguments @('-c', '-s', '60GB', '-a', 'nvme', '-t', '0', $vmdkPath)
    if ($vd.ExitCode -ne 0 -or -not (Test-Path $vmdkPath)) {
        throw ("GATE5: vmware-vdiskmanager falhou (exit {0}): {1}" -f $vd.ExitCode, ($vd.Output -join ' | '))
    }
}

# --- Autounattend em imagem floppy/secundaria nao e usado: a ISO oficial e
# anexada como esta e o Autounattend.xml e entregue via imagem ISO auxiliar
# gerada pelo bootstrap (ver gate5-guest-bootstrap.ps1). ------------------------

# --- VMX ----------------------------------------------------------------------
if (Test-Path $script:Gate5VmxPath) {
    Write-Gate5Log "VMX ja existe, validando configuracao: $($script:Gate5VmxPath)"
} else {
    $vmx = @(
        '.encoding = "UTF-8"'
        'config.version = "8"'
        'virtualHW.version = "21"'          # hardware suportado (nao experimental)
        'displayName = "FaithRO-GATE5-LAB"'
        'guestOS = "windows11-64"'
        'firmware = "efi"'
        'uefi.secureBoot.enabled = "TRUE"'
        'managedvm.autoAddVTPM = "software"' # vTPM oficial sem full-encryption
        'numvcpus = "2"'
        'cpuid.coresPerSocket = "2"'
        'memsize = "4096"'
        'nvme0.present = "TRUE"'
        'nvme0:0.present = "TRUE"'
        'nvme0:0.fileName = "FaithRO-GATE5-LAB.vmdk"'
        'sata0.present = "TRUE"'
        'sata0:1.present = "TRUE"'
        'sata0:1.deviceType = "cdrom-image"'
        ('sata0:1.fileName = "{0}"' -f $IsoPath)
        'sata0:1.startConnected = "TRUE"'
        # NIC em NAT SOMENTE durante o bootstrap (updates). O isolamento final
        # (gate5-provision fase ISOLATED) forca connected=FALSE e
        # startConnected=FALSE antes do snapshot BASELINE_GATE5_ISOLATED.
        'ethernet0.present = "TRUE"'
        'ethernet0.connectionType = "nat"'
        'ethernet0.virtualDev = "e1000e"'
        'ethernet0.startConnected = "TRUE"'
        'usb.present = "FALSE"'
        'sound.present = "FALSE"'
        'floppy0.present = "FALSE"'
        # Integracoes host/guest desabilitadas desde o inicio (risco R3)
        'isolation.tools.copy.disable = "TRUE"'
        'isolation.tools.paste.disable = "TRUE"'
        'isolation.tools.dnd.disable = "TRUE"'
        'isolation.tools.hgfs.disable = "TRUE"'
        'sharedFolder.maxNum = "0"'
        'tools.upgrade.policy = "manual"'
    )
    Set-Gate5TextFile -Path $script:Gate5VmxPath -Lines $vmx
    Write-Gate5Log "VMX criado: $($script:Gate5VmxPath)"
}

# --- Validacao fail-closed da configuracao ------------------------------------
$checks = @{
    'firmware'                 = 'efi'
    'uefi.secureBoot.enabled'  = 'TRUE'
    'managedvm.autoAddVTPM'    = 'software'
    'numvcpus'                 = '2'
    'memsize'                  = '4096'
    'isolation.tools.copy.disable'  = 'TRUE'
    'isolation.tools.paste.disable' = 'TRUE'
    'isolation.tools.dnd.disable'   = 'TRUE'
    'isolation.tools.hgfs.disable'  = 'TRUE'
}
foreach ($k in $checks.Keys) {
    $v = Get-Gate5VmxValue -Key $k
    if ($v -ne $checks[$k]) { throw "GATE5: VMX invalido: $k='$v' (esperado '$($checks[$k])')." }
}
Write-Gate5Log 'VM criada/validada com configuracao conforme.'
exit 0
