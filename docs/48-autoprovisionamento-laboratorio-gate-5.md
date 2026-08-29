# Autoprovisionamento automatizado do laboratório GATE 5

> **Etapa:** 2P-E-C5-LAB-AUTOPROVISION  
> **Predecessor:** 2P-E-C5-LAB-PROVISION-EXEC (resultado: bloqueado — host sem VMware Workstation Pro 26H1 e sem ISO oficial do Windows 11)  
> **Especificação de base:** [doc 47](47-provisao-laboratorio-gate-5.md)  
> **Estado desta etapa:** `LAB_AUTOPROVISION_BLOCKED` (bloqueadores de download do operador; automação implantada e testada até o gate)  
> **Data:** 2026-08-28

```text
target_materialized=false
artifact_executed=false
defender_target_scan_executed=false
yara_target_scan_executed=false
external_reputation_used=false
vps_accessed=false
client_prepared=false
distribution_performed=false
```

---

## 1. Objetivo

Automatizar, de forma idempotente e fail-closed, o provisionamento do laboratório `FaithRO-GATE5-LAB` (VM Windows 11 x64 isolada) até o snapshot `BASELINE_GATE5_ISOLATED`, conforme a arquitetura e o runbook do [doc 47](47-provisao-laboratorio-gate-5.md). O boundary desta automação é o snapshot baseline validado: **nenhum contato com o alvo WARP, com a VPS ou com serviços externos de reputação**.

## 2. Pré-requisitos (gates humanos irredutíveis)

Dois insumos exigem ação humana legítima e **não são automatizáveis** (licença/autenticação):

1. **Instalador VMware Workstation Pro 26H1** — download autenticado no Broadcom Support Portal; salvar como `VMware-workstation-full-<versao>.exe` em `C:\Installers`. A automação valida assinatura Authenticode (publisher VMware/Broadcom), versão 26.x e registra SHA-256.
2. **ISO oficial Windows 11 x64** (preferência 25H2, pt-BR) — download em `https://www.microsoft.com/software-download/windows11`; salvar em `C:\ISO` junto com um sidecar `<iso>.sha256.official` contendo o SHA-256 oficial exibido pela Microsoft ("Verify your download"). Sem o sidecar, a automação bloqueia com `WINDOWS_ISO_PROVENANCE_UNVERIFIED` (fail-closed; ISO sem procedência comprovada nunca é aceita).

Além disso, o entrypoint deve rodar em **PowerShell elevado** (validado no pré-flight).

## 3. Arquivos

```text
scripts/lab/gate5-provision.ps1          # entrypoint (máquina de estados, retomável)
scripts/lab/gate5-common.ps1             # helpers: log UTC, estado, hashes, vmrun, VMX
scripts/lab/gate5-host-preflight.ps1     # pré-flight do host (somente leitura)
scripts/lab/gate5-create-vm.ps1          # VMX + VMDK thin 60 GB (UEFI/Secure Boot/vTPM)
scripts/lab/gate5-guest-bootstrap.ps1    # fases do guest: Unattend/InstallWait/Updates/Defender/Yara/Rules/Sanitize
scripts/lab/gate5-verify-baseline.ps1    # validador final (exit 0 só com todos os controles)
scripts/lab/templates/Autounattend.template.xml  # sem secrets ({{BOOTSTRAP_PASSWORD}} renderizado em runtime)
```

Estado, logs, evidências e segredos de runtime ficam em `.local\gate5-lab\` (ignorado pelo Git; ver `.gitignore`). Segredos de bootstrap são gerados em runtime, protegidos por DPAPI (`Export-Clixml`) e sanitizados antes do snapshot.

## 4. Entrypoint e fluxo

```powershell
.\scripts\lab\gate5-provision.ps1
```

Fases (checkpoints em `.local\gate5-lab\state.json`; fases concluídas não repetem):

```text
HOST_PREFLIGHT_OK → VMWARE_INSTALLED → ISO_VALIDATED → VM_CREATED →
GUEST_INSTALLED → GUEST_UPDATED → DEFENDER_READY → YARA_READY →
RULESET_READY → SANITIZED → ISOLATED → SNAPSHOT_CREATED → BASELINE_VERIFIED
```

Pontos técnicos principais:

- **VM:** `C:\VMs\FaithRO-GATE5-LAB\`, 2 vCPU, 4096 MB, disco 60 GB thin (`vmware-vdiskmanager -c -s 60GB -a nvme -t 0`), `firmware=efi`, `uefi.secureBoot.enabled=TRUE`, vTPM via `managedvm.autoAddVTPM="software"` (mecanismo oficial do Workstation, sem full-encryption). Se o guest não comprovar `TpmPresent/TpmReady`, o validador falha — nunca improvisar chaves `.vmx` (`VTPM_AUTOMATION_NOT_SUPPORTED`).
- **Windows Setup:** `Autounattend.xml` (pt-BR, ABNT2, fuso E. South America, `FAITHRO-GATE5`), entregue por ISO auxiliar gerada com IMAPI2FS (COM nativo), fluxo legítimo sem chave de produto (edição por `IMAGE/NAME`). Conta local `gate5boot` só de bootstrap, com senha aleatória de runtime; removida da configuração e sanitizada antes do snapshot.
- **Integrações host/guest:** desabilitadas no VMX desde a criação (`isolation.tools.copy/paste/dnd/hgfs.disable=TRUE`, `sharedFolder.maxNum=0`, `usb.present=FALSE`).
- **Windows Update:** COM `Microsoft.Update.Session` no guest, com reboot somente do guest, até zero atualizações aplicáveis (máx. 6 ciclos).
- **Defender:** `Update-MpSignature`, evidência com plataforma/engine/assinaturas e SHA-256 do `MpCmdRun.exe`; permanece com antivírus e realtime habilitados.
- **YARA 4.5.5:** download host-side dos metadados/asset win64 da release oficial `VirusTotal/yara v4.5.5`, verificação de tamanho/versão/SHA-256, cópia para `C:\Tools\YARA` no guest e reverificação dentro do guest.
- **Ruleset:** clone de `Yara-Rules/rules`, SHA-40 da branch default resolvido **uma vez** e pinado (`.local\...\evidence\ruleset-pin.json`); categorias incluídas `malware, packers, antidebug_antivm, capabilities, crypto`; excluídas `email, mobile_malware, webshells, maldocs`; licença GPL-2.0 preservada; compilação por arquivo com `yarac64` (exclusão individual documentada apenas para regra que não compila em 4.5.5); índice `gate5-index.yar` compilado com 0 erros; hashes individuais + aggregate SHA-256 determinístico (manifesto `<path>\t<sha256>\n`, UTF-8 sem BOM, ordenação ordinal).
- **Isolamento final:** VM desligada → `ethernet0.connected=FALSE`, `ethernet0.startConnected=FALSE`, ISO desanexada — só então o snapshot `BASELINE_GATE5_ISOLATED` é criado (nunca com egress ativo).
- **Verificação pós-snapshot:** a VM é ligada isolada e o guest comprova `Confirm-SecureBootUEFI`, `Get-Tpm`, Defender ativo, YARA 4.5.5, índice de regras, 0 NICs ativas e ausência de artefatos WARP; depois é desligada. A rede não é reconectada.

## 5. Idempotência e retomada

- Cada fase detecta o que já existe (VMware instalado, VMDK/VMX presentes, pin de ruleset gravado) e não recria/reinstala.
- Interrupções (inclusive reboot do host exigido pelo instalador VMware — `LAB_AUTOPROVISION_PAUSED / HOST_REBOOT_REQUIRED`) são retomadas reexecutando o mesmo entrypoint; o checkpoint da última fase concluída é preservado.
- `state.json` vazio/corrompido reinicia os checkpoints com aviso (as fases redetectam o existente).
- Bloqueios saem com exit 2 e mensagem `LAB_AUTOPROVISION_BLOCKED blocker=<causa>`; pausas com exit 3.

## 6. Validações e testes realizados nesta etapa (2026-08-28)

Sem VMware/ISO no host, o caminho executável foi testado de verdade até os gates:

| Teste | Resultado |
|---|---|
| Parse de todos os `.ps1` e do template XML | 0 erros |
| Execução real do entrypoint (sessão não elevada) | `HOST_PREFLIGHT_FAILED` correto; evidência `host-preflight.json` gerada (SO/RAM/disco/virtualização PASS; só elevação FAIL) |
| Retomada com checkpoint `HOST_PREFLIGHT_OK` | bloqueia exatamente com `VMWARE_INSTALLER_REQUIRES_OPERATOR_DOWNLOAD` |
| Retomada com checkpoint `VMWARE_INSTALLED` | bloqueia exatamente com `WINDOWS_ISO_REQUIRES_OPERATOR_DOWNLOAD`; ISO não-Windows (`xcp-ng`) corretamente rejeitada |
| `python scripts/validate-warp-audit.py` e suítes existentes | ver PR desta etapa |

As fases 4–13 (VM, guest, snapshot) só podem ser exercitadas fim-a-fim após os dois downloads do operador; estão implementadas fail-closed (qualquer inconsistência aborta com exit ≠ 0).

## 7. Riscos e mitigações

Herdados do prompt/doc 47: R1 instalador adulterado (assinatura+SHA-256+fonte oficial), R2 ISO adulterada (sidecar com hash oficial Microsoft, obrigatório), R3 escape host↔guest (integrações off desde a criação), R4 segredo persistente (senha runtime + DPAPI + fase Sanitize + snapshot só depois), R5 egress pós-baseline (NIC disconnected + startConnected=false + prova pós-snapshot), R6 automação não idempotente (checkpoints + redetecção), R7 disco (pré-flight exige ≥40 GB livres antes do VMDK), R8 Hyper-V/VBS (nunca alterado automaticamente; conflito real → `HOST_VIRTUALIZATION_CONFLICT_REQUIRES_DECISION`).

## 8. Rollback

- **VMware:** uninstall/repair oficial pelo Painel de Controle/instalador; não afeta outros produtos.
- **VM:** desligar → `vmrun deleteVM` ou remover somente `C:\VMs\FaithRO-GATE5-LAB\` (autocontida; sem wildcards).
- **Repositório:** reverter apenas `scripts/lab/**`, `docs/48-*.md` e a entrada `.local/` do `.gitignore`; nunca `git reset --hard`/`git clean -fdx`.
- **Estado local:** apagar `.local\gate5-lab\` remove estado/logs/segredos de runtime.

## 9. Gates que permanecem humanos

1. Download autenticado do instalador VMware 26H1 (Broadcom);
2. Download da ISO oficial + cópia do SHA-256 oficial da Microsoft (sidecar);
3. Reboot do host, se exigido pelo instalador VMware;
4. Decisões posteriores da cadeia GATE 5 (materialização/scan do alvo) — **fora do escopo desta automação**, que termina no snapshot `BASELINE_GATE5_ISOLATED`.

## 10. Próxima etapa

Somente após `LAB_AUTOPROVISION_COMPLETE` (critério do prompt: todas as flags de sucesso verdadeiras e as flags proibidas falsas): `ETAPA 2P-E-C5-REAL-EXEC-PREFLIGHT-RERUN`, em sessão separada.
