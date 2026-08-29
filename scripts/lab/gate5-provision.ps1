# gate5-provision.ps1 - Entrypoint da ETAPA 2P-E-C5-LAB-AUTOPROVISION.
# Provisionamento automatizado, idempotente e fail-closed do laboratorio
# FaithRO-GATE5-LAB ate o snapshot BASELINE_GATE5_ISOLATED.
#
# Uso:  .\scripts\lab\gate5-provision.ps1
# Retomada: reexecutar o mesmo comando; checkpoints em .local\gate5-lab\state.json
# garantem que fases concluidas nao sao repetidas.
#
# BOUNDARY: esta automacao TERMINA no snapshot baseline validado. Ela NUNCA
# materializa, baixa, copia, escaneia ou executa o alvo WARP; NUNCA acessa a
# VPS; NUNCA usa reputacao externa; NUNCA prepara/distribui cliente.
#   target_materialized=false / artifact_executed=false / vps_accessed=false

[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot 'gate5-common.ps1')
Initialize-Gate5Log
Write-Gate5Log '=== ETAPA 2P-E-C5-LAB-AUTOPROVISION: inicio/retomada ==='

$state = Get-Gate5State

function Invoke-Gate5Child {
    # Retorna SOMENTE o exit code do filho. A saida do processo filho e
    # reemitida com Write-Host: se ela caisse no pipeline da funcao, o valor de
    # retorno viraria um array (linhas + codigo) e '$code -ne 0' seria sempre
    # verdadeiro, bloqueando a etapa mesmo com o filho retornando 0.
    param([Parameter(Mandatory)][string]$Script, [string[]]$Arguments = @())
    & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot $Script) @Arguments |
        ForEach-Object { Write-Host $_ }
    return [int]$LASTEXITCODE
}

# =============================================================================
# FASE 1: HOST_PREFLIGHT_OK
# =============================================================================
if (-not (Test-Gate5Phase $state 'HOST_PREFLIGHT_OK')) {
    Write-Gate5Log 'FASE: pre-flight do host'
    $code = Invoke-Gate5Child 'gate5-host-preflight.ps1' @('-AsChild')
    if ($code -ne 0) { Stop-Gate5Blocked -Blocker 'HOST_PREFLIGHT_FAILED' -Detail 'ver .local\gate5-lab\evidence\host-preflight.json' }
    Complete-Gate5Phase $state 'HOST_PREFLIGHT_OK'
}

# =============================================================================
# FASE 2: VMWARE_INSTALLED
# =============================================================================
if (-not (Test-Gate5Phase $state 'VMWARE_INSTALLED')) {
    Write-Gate5Log 'FASE: VMware Workstation Pro 26H1'
    $vmware = Find-Gate5VmwareInstall
    if ($vmware) {
        Write-Gate5Log ("VMware ja instalado: versao={0} dir={1}" -f $vmware.DisplayVersion, $vmware.InstallDir)
        if ($vmware.DisplayVersion -notmatch '^26\.') {
            Stop-Gate5Blocked -Blocker 'VMWARE_VERSION_MISMATCH' -Detail "instalada=$($vmware.DisplayVersion) esperada=26H1; nao desinstalar automaticamente"
        }
    } else {
        # Procurar instalador oficial ja baixado pelo operador (fail-closed):
        # a automacao NAO baixa do Broadcom Support Portal (login/EULA humanos).
        $installers = Find-Gate5File -Pattern 'VMware-workstation-full-*.exe'
        if (-not $installers) {
            Stop-Gate5Blocked -Blocker 'VMWARE_INSTALLER_REQUIRES_OPERATOR_DOWNLOAD' -Detail @'
Baixe o instalador oficial do VMware Workstation Pro 26H1 no Broadcom Support
Portal (https://support.broadcom.com -> VMware Workstation Pro) com sua conta,
e salve como VMware-workstation-full-<versao>.exe em C:\Installers.
Depois reexecute .\scripts\lab\gate5-provision.ps1 (retomada automatica).
'@
        }
        $inst = $installers | Select-Object -First 1
        Write-Gate5Log ("Instalador candidato: {0} ({1} bytes)" -f $inst.FullName, $inst.Length)
        # Validacao de origem: assinatura Authenticode valida + publisher VMware/Broadcom
        Assert-Gate5AuthenticodeValid -Path $inst.FullName -PublisherPattern 'VMware|Broadcom' | Out-Null
        $instSha = Get-Gate5Sha256 -Path $inst.FullName
        Write-Gate5Log "Instalador sha256=$instSha (assinatura valida)"
        $verInfo = (Get-Item $inst.FullName).VersionInfo
        if ($verInfo.ProductVersion -notmatch '^26\.') {
            Stop-Gate5Blocked -Blocker 'VMWARE_INSTALLER_NOT_26H1' -Detail "product_version=$($verInfo.ProductVersion)"
        }
        if (-not (Test-Gate5Elevated)) { Stop-Gate5Blocked -Blocker 'ELEVATION_REQUIRED' -Detail 'reexecute em PowerShell elevado' }
        # Instalacao silenciosa com os parametros documentados do instalador
        # Windows do Workstation Pro (formato oficial /s /v"/qn ..."). Confirmar
        # contra a documentacao 26H1 se a instalacao falhar.
        Write-Gate5Log 'Executando instalacao silenciosa (parametros oficiais documentados)...'
        # Formato oficial do instalador Windows do Workstation Pro: /s /v"<props>"
        # sem espaco entre /v e as aspas. Passar como UMA string preserva a
        # sintaxe; um array de argumentos insere um espaco apos /v e o
        # instalador ignora as propriedades, caindo para modo interativo.
        $installArgs = '/s /v"/qn EULAS_AGREED=1 REBOOT=ReallySuppress AUTOSOFTWAREUPDATE=0 DATACOLLECTION=0"'
        $p = Start-Process -FilePath $inst.FullName -ArgumentList $installArgs -Wait -PassThru
        Write-Gate5Log "Instalador exit=$($p.ExitCode)"
        if ($p.ExitCode -eq 3010) {
            # 3010 = ERROR_SUCCESS_REBOOT_REQUIRED: NAO reiniciar silenciosamente
            $vmware = Find-Gate5VmwareInstall
            if ($vmware) { Complete-Gate5Phase $state 'VMWARE_INSTALLED' }
            Stop-Gate5Paused -Reason 'HOST_REBOOT_REQUIRED' -Detail 'Reinicie o host e reexecute gate5-provision.ps1 (retomada automatica).'
        }
        if ($p.ExitCode -ne 0) { Stop-Gate5Blocked -Blocker 'VMWARE_INSTALL_FAILED' -Detail "exit=$($p.ExitCode); verificar parametros oficiais 26H1" }
        $vmware = Find-Gate5VmwareInstall
        if (-not $vmware) { Stop-Gate5Blocked -Blocker 'VMWARE_INSTALL_NOT_DETECTED' -Detail 'instalador retornou 0 mas produto nao localizado' }
    }
    # Registro de identidade dos executaveis principais
    foreach ($exe in @($vmware.VmwareExe, $vmware.VmrunExe, $vmware.VdiskManagerExe)) {
        if (Test-Path $exe) {
            $sig = Get-AuthenticodeSignature -LiteralPath $exe
            Write-Gate5Log ("vmware-exe path={0} sha256={1} sig={2}" -f $exe, (Get-Gate5Sha256 $exe), $sig.Status)
        } else {
            Stop-Gate5Blocked -Blocker 'VMWARE_COMPONENT_MISSING' -Detail $exe
        }
    }
    Complete-Gate5Phase $state 'VMWARE_INSTALLED'
}

# =============================================================================
# FASE 3: ISO_VALIDATED
# =============================================================================
if (-not (Test-Gate5Phase $state 'ISO_VALIDATED')) {
    Write-Gate5Log 'FASE: ISO oficial do Windows 11 x64'
    $isoCandidates = Find-Gate5File -Pattern '*.iso' | Where-Object { $_.Name -match '(?i)win.*11|windows.*11' }
    if (-not $isoCandidates) {
        Stop-Gate5Blocked -Blocker 'WINDOWS_ISO_REQUIRES_OPERATOR_DOWNLOAD' -Detail @'
Baixe a ISO oficial "Windows 11 (multi-edition ISO for x64 devices)" em
https://www.microsoft.com/software-download/windows11 (preferencia: 25H2 x64,
pt-BR) e salve em C:\ISO. Copie tambem o SHA-256 oficial exibido pela pagina
da Microsoft ("Verify your download") para um arquivo <nome-da-iso>.sha256.official
no mesmo diretorio. Depois reexecute .\scripts\lab\gate5-provision.ps1.
'@
    }
    # Selecao determinista por PROCEDENCIA, nao por data: copias da mesma ISO
    # podem existir em varios diretorios de staging com o mesmo timestamp, e
    # escolher a mais recente poderia cair numa copia sem comprovacao oficial.
    # So e candidata a ISO que tenha o sidecar com o SHA-256 da Microsoft.
    Write-Gate5Log ("ISOs Windows 11 encontradas: {0}" -f (@($isoCandidates).Count))
    $iso = $null; $sidecar = $null
    foreach ($cand in $isoCandidates) {
        $sc = Get-Gate5IsoSidecar -IsoPath $cand.FullName
        if ($sc) { $iso = $cand; $sidecar = $sc; break }
        Write-Gate5Log ("ISO ignorada (sem sidecar de hash oficial): {0}" -f $cand.FullName) 'WARN'
    }
    if (-not $iso) {
        Stop-Gate5Blocked -Blocker 'WINDOWS_ISO_PROVENANCE_UNVERIFIED' -Detail @"
ISO(s) encontrada(s), porem nenhuma com comprovacao de procedencia oficial.
Ao lado da ISO oficial, crie o arquivo <nome-da-iso>.sha256.official.txt
contendo apenas o SHA-256 exibido pela Microsoft na pagina de download
(secao "Verify your download") e reexecute a automacao.
Candidatas avaliadas:
$(@($isoCandidates | ForEach-Object { '  - ' + $_.FullName }) -join "`n")
"@
    }
    Write-Gate5Log ("ISO selecionada: {0} ({1:N1} GB)" -f $iso.FullName, ($iso.Length / 1GB))
    $isoSha = Get-Gate5Sha256 -Path $iso.FullName
    Write-Gate5Log "ISO sha256=$isoSha"
    $official = (Get-Content $sidecar -Raw).Trim().ToLowerInvariant()
    if ($official -notmatch '^[0-9a-f]{64}$') { Stop-Gate5Blocked -Blocker 'WINDOWS_ISO_OFFICIAL_HASH_MALFORMED' -Detail $sidecar }
    if ($official -ne $isoSha) { Stop-Gate5Blocked -Blocker 'WINDOWS_ISO_HASH_MISMATCH' -Detail "oficial=$official calculado=$isoSha" }
    Write-Gate5Log 'ISO validada contra o hash oficial da Microsoft.'
    $state.notes | Add-Member -NotePropertyName iso_path -NotePropertyValue $iso.FullName -Force
    $state.notes | Add-Member -NotePropertyName iso_sha256 -NotePropertyValue $isoSha -Force
    Save-Gate5State $state
    Complete-Gate5Phase $state 'ISO_VALIDATED'
}

# =============================================================================
# FASE 4: VM_CREATED
# =============================================================================
if (-not (Test-Gate5Phase $state 'VM_CREATED')) {
    Write-Gate5Log 'FASE: criacao da VM FaithRO-GATE5-LAB'
    $code = Invoke-Gate5Child 'gate5-create-vm.ps1' @('-IsoPath', $state.notes.iso_path, '-AsChild')
    if ($code -ne 0) { Stop-Gate5Blocked -Blocker 'VM_CREATION_FAILED' -Detail "exit=$code" }
    Complete-Gate5Phase $state 'VM_CREATED'
}

# =============================================================================
# FASES 5..10: bootstrap do guest (checkpoint por sub-fase)
# =============================================================================
$guestPhases = @(
    @{ Checkpoint = 'GUEST_INSTALLED'; Sub = @('Unattend', 'InstallWait') },
    @{ Checkpoint = 'GUEST_UPDATED';   Sub = @('Updates') },
    @{ Checkpoint = 'DEFENDER_READY';  Sub = @('Defender') },
    @{ Checkpoint = 'YARA_READY';      Sub = @('Yara') },
    @{ Checkpoint = 'RULESET_READY';   Sub = @('Rules') },
    @{ Checkpoint = 'SANITIZED';       Sub = @('Sanitize') }
)
foreach ($gp in $guestPhases) {
    if (-not (Test-Gate5Phase $state $gp.Checkpoint)) {
        foreach ($sub in $gp.Sub) {
            Write-Gate5Log "FASE guest: $sub"
            $code = Invoke-Gate5Child 'gate5-guest-bootstrap.ps1' @('-Phase', $sub)
            # exit 4 = GATE HUMANO (acao na interface do VMware), nao falha: a
            # fase ja imprimiu a instrucao, entao propagamos sem transformar em
            # LAB_AUTOPROVISION_BLOCKED, que mascararia a natureza da parada.
            if ($code -eq 4) {
                Write-Gate5Log "Etapa pausada em gate humano na fase $sub." 'GATE'
                exit 4
            }
            if ($code -ne 0) { Stop-Gate5Blocked -Blocker "GUEST_PHASE_FAILED_$($sub.ToUpperInvariant())" -Detail "exit=$code; ver logs em .local\gate5-lab\logs" }
        }
        Complete-Gate5Phase $state $gp.Checkpoint
    }
}

# =============================================================================
# FASE 11: ISOLATED - desligar e cortar rede/integracoes ANTES do snapshot
# =============================================================================
if (-not (Test-Gate5Phase $state 'ISOLATED')) {
    Write-Gate5Log 'FASE: isolamento final (NIC desconectada, integracoes off)'
    $vmware = Find-Gate5VmwareInstall
    $running = ((Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('list') -AllowFailure).Output -match [regex]::Escape($script:Gate5VmxPath))
    if ($running) {
        Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('stop', $script:Gate5VmxPath, 'soft') -AllowFailure | Out-Null
        Start-Sleep -Seconds 30
    }
    # Isolamento com a VM desligada. A NIC permanece PRESENTE porem desconectada
    # (para permitir uma decisao humana futura), o CD do sistema e desconectado e
    # o CD do unattend e desligado, pois sua ISO e destruida na fase Sanitize.
    #
    # Cada chave e gravada individualmente: neste ponto a VM ja esta criptografada
    # (o vTPM exige criptografia) e reescrever o .vmx inteiro destruiria a
    # associacao da criptografia junto com o vTPM. Set-Gate5VmxEntry usa a API do
    # proprio VMware quando ha criptografia.
    Set-Gate5VmxEntry -Name 'ethernet0.startConnected' -Value 'FALSE' -Vmware $vmware
    Set-Gate5VmxEntry -Name 'ethernet0.connected'      -Value 'FALSE' -Vmware $vmware
    Set-Gate5VmxEntry -Name ('{0}.startConnected' -f $script:Gate5CdOs)       -Value 'FALSE' -Vmware $vmware
    Set-Gate5VmxEntry -Name ('{0}.startConnected' -f $script:Gate5CdUnattend) -Value 'FALSE' -Vmware $vmware
    Set-Gate5VmxEntry -Name ('{0}.present' -f $script:Gate5CdUnattend)        -Value 'FALSE' -Vmware $vmware
    # Canal temporario de teclado (console VNC local) encerrado aqui: ele so
    # existe para vencer o prompt de boot pelo CD durante a instalacao.
    Set-Gate5VncConsole -Enabled $false
    foreach ($pair in @(
        @('isolation.tools.copy.disable', 'TRUE'), @('isolation.tools.paste.disable', 'TRUE'),
        @('isolation.tools.dnd.disable', 'TRUE'), @('isolation.tools.hgfs.disable', 'TRUE'))) {
        if ((Get-Gate5VmxValue $pair[0]) -ne $pair[1]) { Stop-Gate5Blocked -Blocker 'ISOLATION_VMX_INVALID' -Detail $pair[0] }
    }
    if ((Get-Gate5VmxValue 'ethernet0.startConnected') -ne 'FALSE') { Stop-Gate5Blocked -Blocker 'ISOLATION_VMX_INVALID' -Detail 'ethernet0.startConnected' }
    $vncCfg = Get-Gate5VmxValue 'RemoteDisplay.vnc.enabled'
    if ($null -ne $vncCfg -and $vncCfg -ne 'FALSE') { Stop-Gate5Blocked -Blocker 'ISOLATION_VMX_INVALID' -Detail 'console VNC temporario ainda habilitado' }
    # Nao basta o .vmx: conferir que nenhum listener temporario sobrou no host.
    $vncListen = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
                   Where-Object { $_.LocalPort -eq $script:Gate5VncPort })
    if ($vncListen.Count -gt 0) { Stop-Gate5Blocked -Blocker 'ISOLATION_VNC_LISTENER_ACTIVE' -Detail ("porta {0} ainda ouvindo no host" -f $script:Gate5VncPort) }
    Write-Gate5Log 'Isolamento aplicado e verificado no VMX.'
    Complete-Gate5Phase $state 'ISOLATED'
}

# =============================================================================
# FASE 12: SNAPSHOT_CREATED - somente com a VM ja isolada e desligada
# =============================================================================
if (-not (Test-Gate5Phase $state 'SNAPSHOT_CREATED')) {
    Write-Gate5Log "FASE: snapshot $($script:Gate5SnapshotName)"
    $vmware = Find-Gate5VmwareInstall
    $snaps = (Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('listSnapshots', $script:Gate5VmxPath) -AllowFailure).Output
    if ($snaps -match [regex]::Escape($script:Gate5SnapshotName)) {
        Write-Gate5Log 'Snapshot baseline ja existe.'
    } else {
        Invoke-Gate5Vmrun -Vmware $vmware -Arguments @('snapshot', $script:Gate5VmxPath, $script:Gate5SnapshotName) | Out-Null
        Write-Gate5Log 'Snapshot baseline criado.'
    }
    Complete-Gate5Phase $state 'SNAPSHOT_CREATED'
}

# =============================================================================
# FASE 13: BASELINE_VERIFIED - validador final (liga, prova, desliga)
# =============================================================================
if (-not (Test-Gate5Phase $state 'BASELINE_VERIFIED')) {
    Write-Gate5Log 'FASE: verificacao final do baseline'
    $code = Invoke-Gate5Child 'gate5-verify-baseline.ps1'
    if ($code -ne 0) { Stop-Gate5Blocked -Blocker 'BASELINE_VERIFICATION_FAILED' -Detail "exit=$code" }
    Complete-Gate5Phase $state 'BASELINE_VERIFIED'
}

Write-Gate5Log '=== LAB_AUTOPROVISION_COMPLETE ==='
Write-Host ''
Write-Host 'LAB_AUTOPROVISION_COMPLETE'
Write-Host 'LAB_BASELINE_READY=true'
Write-Host 'target_materialized=false'
Write-Host 'artifact_executed=false'
Write-Host 'defender_target_scan_executed=false'
Write-Host 'yara_target_scan_executed=false'
Write-Host 'external_reputation_used=false'
Write-Host 'vps_accessed=false'
Write-Host 'client_prepared=false'
Write-Host 'distribution_performed=false'
Write-Host ''
Write-Host 'BOUNDARY atingido: BASELINE_GATE5_ISOLATED. NAO prosseguir para o alvo WARP.'
Write-Host 'Proxima etapa (sessao separada): ETAPA 2P-E-C5-REAL-EXEC-PREFLIGHT-RERUN'
exit 0
