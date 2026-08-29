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

# Recuperacao de um power-on interrompido: um vmware-vmx que morre deixa
# diretorios *.lck e um .vmem que impedem religar a VM. So removemos esses
# residuos quando o VMware confirma que a VM NAO esta em execucao, e apenas
# dentro do diretorio desta VM (nunca com wildcard amplo).
if (Test-Path $script:Gate5VmxPath) {
    $running = (Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('list') -AllowFailure).Output
    if ($running -match [regex]::Escape($script:Gate5VmxPath)) {
        Write-Gate5Log 'VM em execucao; residuos de lock nao serao tocados.'
    } else {
        $stale = @(Get-ChildItem -LiteralPath $script:Gate5VmDir -Filter '*.lck' -Directory -ErrorAction SilentlyContinue) +
                 @(Get-ChildItem -LiteralPath $script:Gate5VmDir -Filter '*.vmem' -File -ErrorAction SilentlyContinue) +
                 @(Get-ChildItem -LiteralPath $script:Gate5VmDir -Filter 'vmware-vmx*.dmp' -File -ErrorAction SilentlyContinue)
        # NVRAM: as variaveis UEFI gravadas durante um power-on que falhou ficam
        # com a enumeracao de dispositivos daquele momento, e o firmware deixa de
        # enxergar unidades que passaram a existir depois (observado: o CD do
        # sistema sumiu do Boot Manager ate a NVRAM ser descartada). So e seguro
        # descartar enquanto o Windows ainda nao foi instalado - criterio
        # objetivo: o disco virtual ainda esta praticamente vazio.
        #
        # E NUNCA em VM criptografada: a partir do vTPM, a NVRAM guarda o estado
        # persistente do TPM virtual. Descarta-la ali destruiria em silencio o
        # dispositivo que o operador acabou de criar pela interface do VMware.
        $cryptoState = Get-Gate5VmEncryptionState
        if ($cryptoState.Encrypted -or $cryptoState.VtpmPresent) {
            Write-Gate5Log 'VM com vTPM/criptografia: NVRAM preservada (guarda o estado do TPM).'
        } elseif ((Get-Item -LiteralPath $vmdkPath -ErrorAction SilentlyContinue).Length -lt 100MB) {
            $stale += @(Get-ChildItem -LiteralPath $script:Gate5VmDir -File -ErrorAction SilentlyContinue |
                        Where-Object { $_.Name -eq 'nvram' -or $_.Extension -eq '.nvram' })
        }
        foreach ($s in $stale) {
            Write-Gate5Log ("Removendo residuo de execucao interrompida: {0}" -f $s.Name)
            Remove-Item -LiteralPath $s.FullName -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

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
# Chaves canonicas do laboratorio. Aplicadas tanto na criacao quanto na
# REPARACAO de um VMX ja existente: chaves adicionais escritas pelo proprio
# VMware (uuid.bios, nvram, ethernet0.generatedAddress, ...) sao preservadas.
$canonical = [ordered]@{
    'config.version'          = '8'
    # Versao de hardware que ESTA instalacao do Workstation gera ao criar uma VM
    # pelo caminho suportado (conferido com 'vmcli VM Create'). Nao e hardware
    # experimental: e o padrao do produto.
    'virtualHW.version'       = '22'
    'displayName'             = 'FaithRO-GATE5-LAB'
    'guestOS'                 = 'windows11-64'
    'nvram'                   = 'FaithRO-GATE5-LAB.nvram'
    'memory.maxsize'          = '0'
    'svga.present'            = 'TRUE'
    'hpet0.present'           = 'TRUE'
    'firmware'                = 'efi'
    'uefi.secureBoot.enabled' = 'TRUE'
    'managedvm.autoAddVTPM'   = 'software'    # vTPM oficial sem full-encryption
    'numvcpus'                = '2'
    'cpuid.coresPerSocket'    = '2'
    'memsize'                 = '4096'
    # Pontes PCIe. Sem elas o barramento nao tem slot livre para a NIC: o
    # vmware-vmx aborta em msg.pci.noslotavail ("No PCIe slot available for
    # Ethernet0") e o proprio tratamento do erro termina em access violation,
    # de modo que a VM nunca chega a ligar. Estas sao as mesmas chaves que o
    # VMware Workstation grava ao criar uma VM pela sua interface.
    'pciBridge0.present'      = 'TRUE'
    'pciBridge4.present'      = 'TRUE'
    'pciBridge4.virtualDev'   = 'pcieRootPort'
    'pciBridge4.functions'    = '8'
    'pciBridge5.present'      = 'TRUE'
    'pciBridge5.virtualDev'   = 'pcieRootPort'
    'pciBridge5.functions'    = '8'
    'pciBridge6.present'      = 'TRUE'
    'pciBridge6.virtualDev'   = 'pcieRootPort'
    'pciBridge6.functions'    = '8'
    'pciBridge7.present'      = 'TRUE'
    'pciBridge7.virtualDev'   = 'pcieRootPort'
    'pciBridge7.functions'    = '8'
    # Canal VMCI: exigido pelas guest operations do vmrun (CopyFile*/runProgram*)
    'vmci0.present'           = 'TRUE'
    'nvme0.present'           = 'TRUE'
    'nvme0:0.present'         = 'TRUE'
    'nvme0:0.fileName'        = 'FaithRO-GATE5-LAB.vmdk'
    'sata0.present'                              = 'TRUE'
    ('{0}.present' -f $script:Gate5CdOs)         = 'TRUE'
    ('{0}.deviceType' -f $script:Gate5CdOs)      = 'cdrom-image'
    ('{0}.fileName' -f $script:Gate5CdOs)        = $IsoPath
    ('{0}.startConnected' -f $script:Gate5CdOs)  = 'TRUE'
    # NIC em NAT SOMENTE durante o bootstrap (updates). O isolamento final
    # (gate5-provision fase ISOLATED) forca connected=FALSE e
    # startConnected=FALSE antes do snapshot BASELINE_GATE5_ISOLATED.
    'ethernet0.present'        = 'TRUE'
    'ethernet0.connectionType' = 'nat'
    'ethernet0.virtualDev'     = 'e1000e'
    'ethernet0.startConnected' = 'TRUE'
    'usb.present'              = 'FALSE'
    'sound.present'            = 'FALSE'
    'floppy0.present'          = 'FALSE'
    # Integracoes host/guest desabilitadas desde o inicio (risco R3)
    'isolation.tools.copy.disable'  = 'TRUE'
    'isolation.tools.paste.disable' = 'TRUE'
    'isolation.tools.dnd.disable'   = 'TRUE'
    'isolation.tools.hgfs.disable'  = 'TRUE'
    'sharedFolder.maxNum'           = '0'
    'tools.upgrade.policy'          = 'manual'
}

$existing = @()
if (Test-Path $script:Gate5VmxPath) {
    $existing = @(Get-Content -LiteralPath $script:Gate5VmxPath)

    # VM criptografada: o vTPM do Workstation exige criptografia, e o material de
    # chave fica amarrado ao conteudo do .vmx. Reescrever o arquivo destruiria
    # essa associacao (e com ela o vTPM). Neste estado a configuracao e apenas
    # CONFERIDA - qualquer divergencia canonica vira bloqueio para correcao
    # humana pela interface do VMware, nunca reescrita automatica.
    if ($existing -match '^encryption\.' -or $existing -match '^vtpm\.') {
        Write-Gate5Log 'VMX com estado criptografico do VMware: somente conferencia, sem reescrita.'
        $divergentes = @()
        foreach ($k in $canonical.Keys) {
            # A ISO do sistema pode ter sido desconectada de proposito pela fase
            # de isolamento; o restante das chaves canonicas deve bater.
            if ($k -like ($script:Gate5CdOs + '*')) { continue }
            # Defesa em profundidade: nenhuma chave de material criptografico ou
            # de identidade do TPM pode ter o valor impresso, mesmo que algum dia
            # entre no conjunto canonico. Reporta-se apenas o nome.
            if ($k -match '^(encryption\.|vtpm\.)') { $divergentes += ("{0}=<redigido>" -f $k); continue }
            $v = Get-Gate5VmxValue -Key $k
            if ($v -ne $canonical[$k]) { $divergentes += ("{0}='{1}' (esperado '{2}')" -f $k, $v, $canonical[$k]) }
        }
        if ($divergentes.Count -gt 0) {
            Stop-Gate5Blocked -Blocker 'ENCRYPTED_VMX_CONFIG_DIVERGENT' -Detail @"
A VM ja possui estado criptografico do VMware (vTPM) e nao pode ser reescrita
pela automacao sem destruir a associacao da criptografia. As chaves abaixo
divergem da configuracao canonica e precisam ser ajustadas pela interface do
VMware Workstation (VM Settings), com a VM desligada:
$(($divergentes | ForEach-Object { '  - ' + $_ }) -join "`n")
"@
        }
        Write-Gate5Log 'Configuracao canonica conferida na VM criptografada.'
        exit 0
    }

    Write-Gate5Log "VMX ja existe, reparando para a configuracao canonica: $($script:Gate5VmxPath)"
} else {
    Write-Gate5Log "Criando VMX: $($script:Gate5VmxPath)"
}

# Preserva as linhas que nao sao chaves canonicas (inclusive as geradas pelo
# VMware) e reescreve as canonicas com o valor exigido.
$preserved = $existing | Where-Object {
    $line = $_
    if ($line -notmatch '^\s*([A-Za-z0-9_.:]+)\s*=') { return $false }
    $key = $Matches[1]
    if ($canonical.Contains($key) -or $key -eq '.encoding') { return $false }
    # Atribuicoes de slot PCI sao geradas pelo VMware a partir da topologia do
    # barramento. Preservar as antigas apos acrescentar as pontes PCIe faz a NIC
    # herdar um slot invalido na nova topologia e o power-on falha de novo com
    # msg.pci.noslotavail. Deixamos o VMware recalcula-las.
    if ($key -match '\.pciSlotNumber$') { return $false }
    # Dispositivos de midia de um layout anterior (por exemplo o CD do sistema
    # em outra porta) nao podem sobreviver a reparacao: duas unidades apontando
    # para a mesma ISO confundem a ordem de boot do firmware. A fase Unattend
    # reanexa a sua propria ISO depois desta etapa.
    if ($key -match '^(sata0|ide0|ide1):\d+\.') { return $false }
    return $true
}
$vmxLines = @('.encoding = "UTF-8"')
foreach ($k in $canonical.Keys) { $vmxLines += ('{0} = "{1}"' -f $k, $canonical[$k]) }
$vmxLines += $preserved
Set-Gate5TextFile -Path $script:Gate5VmxPath -Lines $vmxLines

# --- Validacao fail-closed da configuracao ------------------------------------
foreach ($k in $canonical.Keys) {
    $v = Get-Gate5VmxValue -Key $k
    if ($v -ne $canonical[$k]) { throw "GATE5: VMX invalido: $k='$v' (esperado '$($canonical[$k])')." }
}
Write-Gate5Log ("VM criada/reparada e validada ({0} chaves canonicas, {1} linhas preservadas)." -f $canonical.Count, @($preserved).Count)
exit 0
