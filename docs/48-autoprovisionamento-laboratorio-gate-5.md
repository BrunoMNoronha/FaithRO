# Autoprovisionamento automatizado do laboratório GATE 5

> **Etapa:** 2P-E-C5-LAB-AUTOPROVISION  
> **Predecessor:** 2P-E-C5-LAB-PROVISION-EXEC (resultado: bloqueado — host sem VMware Workstation Pro 26H1 e sem ISO oficial do Windows 11)  
> **Especificação de base:** [doc 47](47-provisao-laboratorio-gate-5.md)  
> **Estado desta etapa:** `LAB_AUTOPROVISION_BLOCKED` — os dois downloads do operador foram concluídos e a automação avançou até a criação da VM; agora bloqueia em `VTPM_AUTOMATION_NOT_SUPPORTED` (ver §11)  
> **Data:** 2026-08-28 (execução real em 2026-08-29 UTC)

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
scripts/lab/test-gate5-lab-automation.ps1        # testes sintéticos (sem VM, sem rede, sem alvo)
```

Os testes rodam sem VMware, sem rede e sem elevação:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\lab\test-gate5-lab-automation.ps1
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

- **VM:** `C:\VMs\FaithRO-GATE5-LAB\`, 2 vCPU, 4096 MB, disco 60 GB thin (`vmware-vdiskmanager -c -s 60GB -a nvme -t 0`), `firmware=efi`, `uefi.secureBoot.enabled=TRUE`. O `.vmx` é escrito a partir de um conjunto **canônico** de chaves e reparado de forma idempotente (chaves geradas pelo VMware, como `uuid.bios`, são preservadas). O conjunto inclui as pontes PCIe (`pciBridge0/4/5/6/7`) e `virtualHW.version="22"`, conferidos contra a saída de `vmcli VM Create` desta instalação — sem as pontes não há slot PCIe para a NIC e o `vmware-vmx` aborta antes de ligar.
- **vTPM:** `managedvm.autoAddVTPM="software"` é declarado, mas **não basta**: essa chave é honrada pelo fluxo gerenciado do Workstation e não por `vmrun start` sobre um `.vmx` escrito a mão. A automação exige **evidência** de um dispositivo TPM (chave `vtpm.present` materializada ou registro no `vmware.log`) e, na ausência dela, para com `VTPM_AUTOMATION_NOT_SUPPORTED` — nunca improvisa chaves `.vmx` nem contorna o requisito de TPM do Windows 11. Ver §11.
- **Windows Setup:** `Autounattend.xml` (pt-BR, ABNT2, fuso E. South America, `FAITHRO-GATE5`), entregue por ISO auxiliar gerada com IMAPI2FS (COM nativo), fluxo legítimo sem chave de produto (edição por `IMAGE/NAME`). Conta local `gate5boot` só de bootstrap, com senha aleatória de runtime; removida da configuração e sanitizada antes do snapshot.
- **Integrações host/guest:** desabilitadas no VMX desde a criação (`isolation.tools.copy/paste/dnd/hgfs.disable=TRUE`, `sharedFolder.maxNum=0`, `usb.present=FALSE`).
- **Windows Update:** COM `Microsoft.Update.Session` no guest, com reboot somente do guest, até zero atualizações aplicáveis (máx. 6 ciclos).
- **Defender:** `Update-MpSignature`, evidência com plataforma/engine/assinaturas e SHA-256 do `MpCmdRun.exe`; permanece com antivírus e realtime habilitados.
- **YARA 4.5.5:** download host-side dos metadados/asset win64 da release oficial `VirusTotal/yara v4.5.5`, verificação de tamanho/versão/SHA-256, cópia para `C:\Tools\YARA` no guest e reverificação dentro do guest.
- **Ruleset:** SHA-40 da branch default de `Yara-Rules/rules` resolvido **uma vez** pela API oficial do GitHub e pinado, com o conteúdo materializado pelo *zipball* daquele commit exato (sem depender de `git` no `PATH`: o provisionamento roda elevado sob outra conta administradora, onde uma instalação per-user do git não existe) (`.local\...\evidence\ruleset-pin.json`); categorias incluídas `malware, packers, antidebug_antivm, capabilities, crypto`; excluídas `email, mobile_malware, webshells, maldocs`; licença GPL-2.0 preservada; compilação por arquivo com `yarac64` (exclusão individual documentada apenas para regra que não compila em 4.5.5); índice `gate5-index.yar` compilado com 0 erros; hashes individuais + aggregate SHA-256 determinístico (manifesto `<path>\t<sha256>\n`, UTF-8 sem BOM, ordenação ordinal).
- **Isolamento final:** VM desligada → `ethernet0.connected=FALSE`, `ethernet0.startConnected=FALSE`, ISO desanexada — só então o snapshot `BASELINE_GATE5_ISOLATED` é criado (nunca com egress ativo).
- **Verificação pós-snapshot:** a VM é ligada isolada e o guest comprova `Confirm-SecureBootUEFI`, `Get-Tpm`, Defender ativo, YARA 4.5.5, índice de regras, 0 NICs ativas e ausência de artefatos WARP; depois é desligada. A rede não é reconectada.

## 5. Idempotência e retomada

- Cada fase detecta o que já existe (VMware instalado, VMDK/VMX presentes, pin de ruleset gravado) e não recria/reinstala.
- Interrupções (inclusive reboot do host exigido pelo instalador VMware — `LAB_AUTOPROVISION_PAUSED / HOST_REBOOT_REQUIRED`) são retomadas reexecutando o mesmo entrypoint; o checkpoint da última fase concluída é preservado.
- `state.json` vazio/corrompido reinicia os checkpoints com aviso (as fases redetectam o existente).
- Bloqueios saem com exit 2 e mensagem `LAB_AUTOPROVISION_BLOCKED blocker=<causa>`; pausas com exit 3.

## 6. Execução real e validações (2026-08-29 UTC)

Com o instalador e a ISO já materializados pelo operador, a automação foi executada de verdade em sessão elevada. Resultados por fase:

| Fase | Resultado |
|---|---|
| `HOST_PREFLIGHT_OK` | PASS — Windows 11 build 26200 x64, i5-1235U, 16,89 GB RAM, ~74,9 GB livres em C:, virtualização disponível (Hyper-V/VBS ativo, **preservado**) |
| `VMWARE_INSTALLED` | PASS — `VMware-Workstation-Full-26H1-25388281.exe`, Authenticode **Valid** (`CN=Broadcom Inc`), `ProductVersion=26.0.0`, SHA-256 `a0ef9087607d9cad20b08139e73e41242e044ad5bd8cee141d3bad314586737f`; instalado em `C:\Program Files\VMware\VMware Workstation` sem exigir reboot |
| `ISO_VALIDATED` | PASS — `Win11_25H2_BrazilianPortuguese_x64_v2.iso`, SHA-256 `50fe4703cf0df0072e093d1f5d58ed450e4c49d8ca960433bbe6278d5ef10107` **idêntico** ao sidecar oficial; edição `Windows 11 Pro` confirmada no `install.wim` (índice 4) |
| `VM_CREATED` | PASS — VMDK thin 60 GB + `.vmx` canônico validado |
| `GUEST_INSTALLED` | **BLOQUEADO** — ver §11 |

Validações do repositório (sessão não elevada):

| Teste | Resultado |
|---|---|
| Parse de todos os `.ps1` e do template XML | 0 erros |
| `scripts/lab/test-gate5-lab-automation.ps1` | 28 PASS / 0 FAIL |
| `python scripts/validate-warp-audit.py` | OK (8 artefatos, schemas, cross-checks, GATE 0–5) |
| `git diff --check` | sem problemas de whitespace |

## 7. Defeitos corrigidos durante a execução

A execução real expôs defeitos que a etapa anterior não podia detectar. Todos foram corrigidos e cobertos por teste:

| # | Defeito | Efeito observado |
|---|---|---|
| D1 | `Invoke-Gate5Child` devolvia a saída do processo filho junto com o exit code | `$code -ne 0` comparava um array e era sempre verdadeiro: a etapa parava com `HOST_PREFLIGHT_FAILED` **com o pré-flight aprovado** |
| D2 | A redação do log do `vmrun` mascarava as flags `-gu/-gp` mas não o valor seguinte | senha do guest gravada em texto claro na trilha de auditoria |
| D3 | Fase `Rules` dependia de `git` no `PATH` | a sessão elevada roda sob outra conta administradora, sem o git per-user; a fase falharia no fim da etapa |
| D4 | Aggregate hash do ruleset ordenado com `Sort-Object` (sensível a cultura) | hash dependente do locale, quebrando a reprodutibilidade exigida |
| D5 | `2>&1` sobre programas nativos com `ErrorActionPreference='Stop'` | `NativeCommandError` abortaria `vmrun`, `vmware-vdiskmanager` e `yarac` |
| D6 | Sem TLS 1.2 explícito no PowerShell 5.1 | handshake com as fontes oficiais falharia na fase Yara |
| D7 | Argumentos de instalação silenciosa do VMware passados como array | espaço após `/v` invalida a sintaxe oficial `/s /v"<props>"` |
| D8 | `.vmx` gravado com `Set-Content -Encoding utf8` (prefixa BOM) | risco de rejeição da primeira chave de configuração |
| D9 | ISO escolhida pela mais recente | havia duas cópias da mesma ISO com o mesmo timestamp e só uma com sidecar oficial; a seleção passou a ser por procedência comprovada |
| D10 | `Sanitize` reprovava por padrões genéricos (`*token*`, `*github*`, `*credential*`) | falsos positivos em arquivos internos do Windows reprovariam a etapa no fim; padrões decisórios e informativos foram separados |
| D11 | `.vmx` sem as pontes PCIe | `msg.pci.noslotavail` para a NIC e **access violation** no `vmware-vmx`: a VM nunca ligava |
| D12 | Reparo do `.vmx` preservava `*.pciSlotNumber` da topologia antiga | a NIC herdava um slot inválido e o power-on falhava de novo |
| D13 | NVRAM de um power-on que falhou | o firmware deixou de enumerar o CD do sistema; descartada quando o disco ainda está vazio |
| D14 | Verificação do vTPM aceitava a própria chave escrita pela automação | falso positivo: registrava "vTPM confirmado" sem TPM algum |

Evidências brutas ficam em `.local\gate5-lab\evidence\` (não versionadas): `vmware-crash-pci-noslotavail.log` e capturas de tela do firmware do guest.

## 8. Riscos e mitigações

Herdados do prompt/doc 47: R1 instalador adulterado (assinatura+SHA-256+fonte oficial), R2 ISO adulterada (sidecar com hash oficial Microsoft, obrigatório), R3 escape host↔guest (integrações off desde a criação), R4 segredo persistente (senha runtime + DPAPI + fase Sanitize + snapshot só depois), R5 egress pós-baseline (NIC disconnected + startConnected=false + prova pós-snapshot), R6 automação não idempotente (checkpoints + redetecção), R7 disco (pré-flight exige ≥40 GB livres antes do VMDK), R8 Hyper-V/VBS (nunca alterado automaticamente; conflito real → `HOST_VIRTUALIZATION_CONFLICT_REQUIRES_DECISION`).

## 9. Rollback

- **VMware:** uninstall/repair oficial pelo Painel de Controle/instalador; não afeta outros produtos.
- **VM:** desligar → `vmrun deleteVM` ou remover somente `C:\VMs\FaithRO-GATE5-LAB\` (autocontida; sem wildcards).
- **Repositório:** reverter apenas `scripts/lab/**`, `docs/48-*.md` e a entrada `.local/` do `.gitignore`; nunca `git reset --hard`/`git clean -fdx`.
- **Estado local:** apagar `.local\gate5-lab\` remove estado/logs/segredos de runtime.

## 10. Gates que permanecem humanos

1. ~~Download autenticado do instalador VMware 26H1 (Broadcom)~~ — **concluído**;
2. ~~Download da ISO oficial + cópia do SHA-256 oficial da Microsoft (sidecar)~~ — **concluído**;
3. **Adicionar o vTPM pela interface do Workstation** (ver §11) — pendente;
4. **Aprovação de UAC** a cada execução: nesta máquina a conta de trabalho não pertence ao grupo de administradores, e a elevação usa outra conta administrativa. O provisionamento só avança enquanto o operador aprovar o prompt do Windows; a senha nunca é manipulada pela automação. Como consequência, os segredos de bootstrap ficam protegidos por DPAPI **da conta elevada** — todas as execuções devem usar a mesma conta;
5. Reboot do host, se exigido pelo instalador VMware (não foi necessário nesta instalação);
6. Decisões posteriores da cadeia GATE 5 (materialização/scan do alvo) — **fora do escopo desta automação**, que termina no snapshot `BASELINE_GATE5_ISOLATED`.

## 11. Bloqueio atual: vTPM e boot do instalador

**Bloqueador:** `VTPM_AUTOMATION_NOT_SUPPORTED`.

Constatado empiricamente nesta instalação do Workstation 26.0.0:

- `managedvm.autoAddVTPM="software"` aparece no `DICT` do `vmware.log`, mas **nenhum dispositivo TPM é criado** quando a VM é ligada por `vmrun start` sobre um `.vmx` escrito a mão;
- `vmrun` não expõe comando de TPM;
- `vmcli` não possui módulo de TPM nem de criptografia (módulos disponíveis: `Chipset, ConfigParams, Disk, Ethernet, Guest, HGFS, MKS, Nvme, Power, Sata, Serial, Snapshot, Tools, VM`);
- o vTPM do Workstation exige criptografia (ao menos parcial) da VM, cujo material de chave só o próprio VMware gera — **inventar essas chaves é proibido por esta etapa**, assim como contornar o requisito de TPM do Windows 11.

**Único passo humano necessário:** abrir o VMware Workstation, abrir `C:\VMs\FaithRO-GATE5-LAB\FaithRO-GATE5-LAB.vmx`, `VM Settings → Add → Trusted Platform Module`, aceitar a criptografia proposta pelo produto (a senha **não** deve ser versionada nem registrada em log) e fechar. Em seguida reexecutar, em PowerShell elevado:

```powershell
.\scripts\lab\gate5-provision.ps1
```

A automação retoma do checkpoint `VM_CREATED` sem refazer o que já está pronto.

**Pendência não resolvida (verificar na próxima execução):** com a NVRAM anterior descartada, o Boot Manager do firmware passou a enumerar todos os dispositivos (`NVME Namespace`, dois `SATA CDROM Drive`, `Network`), mas a tentativa de boot pelo CD do sistema terminou em `Status upon boot failure: No Media` e o Windows Setup não iniciou (disco virtual permaneceu vazio). As correções D11–D13 (pontes PCIe, recálculo dos slots PCI, descarte da NVRAM obsoleta), a mudança do CD do sistema para a porta `sata0:0` e o envio de teclas para o prompt "Press any key to boot from CD" foram aplicadas, **mas ainda não puderam ser verificadas fim-a-fim** porque a elevação deixou de ser concedida. Se o `No Media` persistir após a adição do vTPM, o próximo passo de diagnóstico é comparar o `.vmx` com o de uma VM criada inteiramente pela interface do Workstation com a mesma ISO anexada.

## 12. Próxima etapa

Somente após `LAB_AUTOPROVISION_COMPLETE` (critério do prompt: todas as flags de sucesso verdadeiras e as flags proibidas falsas): `ETAPA 2P-E-C5-REAL-EXEC-PREFLIGHT-RERUN`, em sessão separada.
