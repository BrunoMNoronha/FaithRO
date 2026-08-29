# Autoprovisionamento automatizado do laboratório GATE 5

> - **Etapa:** 2P-E-C5-LAB-AUTOPROVISION
> - **Predecessor:** 2P-E-C5-LAB-PROVISION-EXEC (resultado: bloqueado — host sem VMware Workstation Pro 26H1 e sem ISO oficial do Windows 11)
> - **Especificação de base:** [doc 47](47-provisao-laboratorio-gate-5.md)
> - **Estado desta etapa:** `LAB_AUTOPROVISION_BLOCKED` — VMware, ISO e VM prontos; o boot da ISO foi **resolvido e comprovado**; resta um único gate humano: adicionar o vTPM pela interface do Workstation (ver §11)
> - **Data:** 2026-08-28; execução real e recuperação em 2026-08-29 (etapa 2P-E-C5-LAB-VTPM-BOOT-RECOVERY)

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

A elevação (**PowerShell como Administrador**) é exigida **apenas** para instalar o VMware e criar `C:\VMs\FaithRO-GATE5-LAB\`. Depois disso — verificado nesta máquina — `vmrun`, `vmcli` e o diretório da VM são acessíveis pela conta de trabalho comum, e o pré-flight deixa de exigir privilégio administrativo. Rodar sem elevação é o estado preferível (menor privilégio) e evita que os segredos de bootstrap fiquem presos à conta administrativa via DPAPI.

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
- **Boot da ISO:** a ISO oficial da Microsoft usa o carregador com o prompt *"Press any key to boot from CD or DVD"*. Sem uma tecla, o firmware registra `Status upon boot failure: Time out`, desiste do CD e a VM fica presa no Boot Manager — o Setup nunca inicia. `vmcli MKS sendKeyEvent`/`sendKeySequence` retornam sucesso mas **a tecla não chega ao guest** sem um console conectado, e `vmrun start ... gui` bloqueia. A automação usa então o **console VNC do próprio VMware** como canal **local e temporário** (preso a `127.0.0.1`), com um cliente RFB 3.8 mínimo embutido, e para de teclar assim que o disco cresce (prova de que o Setup começou a gravar). O canal é removido na fase de isolamento e sua ausência é conferida pelo validador antes do snapshot; se o console não responder, a etapa falha fechada com `BOOT_KEY_CHANNEL_UNAVAILABLE`.
- **Windows Setup:** `Autounattend.xml` (pt-BR, ABNT2, fuso E. South America, `FAITHRO-GATE5`), entregue por ISO auxiliar gerada com IMAPI2FS (COM nativo), fluxo legítimo sem chave de produto (edição por `IMAGE/NAME`). Conta local `gate5boot` só de bootstrap, com senha aleatória de runtime; removida da configuração e sanitizada antes do snapshot.
- **Integrações host/guest:** desabilitadas no VMX desde a criação (`isolation.tools.copy/paste/dnd/hgfs.disable=TRUE`, `sharedFolder.maxNum=0`, `usb.present=FALSE`).
- **Windows Update:** COM `Microsoft.Update.Session` no guest, com reboot somente do guest, até zero atualizações aplicáveis (máx. 6 ciclos).
- **Defender:** `Update-MpSignature`, evidência com plataforma/engine/assinaturas e SHA-256 do `MpCmdRun.exe`; permanece com antivírus e realtime habilitados.
- **YARA 4.5.5:** download host-side dos metadados/asset win64 da release oficial `VirusTotal/yara v4.5.5`, verificação de tamanho/versão/SHA-256, cópia para `C:\Tools\YARA` no guest e reverificação dentro do guest.
- **Ruleset:** SHA-40 da branch default de `Yara-Rules/rules` resolvido **uma vez** pela API oficial do GitHub e pinado, com o conteúdo materializado pelo *zipball* daquele commit exato (sem depender de `git` no `PATH`, que não existe em toda conta capaz de rodar o provisionamento — uma instalação per-user do git não é visível para outra conta) (`.local\...\evidence\ruleset-pin.json`); categorias incluídas `malware, packers, antidebug_antivm, capabilities, crypto`; excluídas `email, mobile_malware, webshells, maldocs`; licença GPL-2.0 preservada; compilação por arquivo com `yarac64` (exclusão individual documentada apenas para regra que não compila em 4.5.5); índice `gate5-index.yar` compilado com 0 erros; hashes individuais + aggregate SHA-256 determinístico (manifesto `<path>\t<sha256>\n`, UTF-8 sem BOM, ordenação ordinal).
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
| D15 | Boot da ISO expirava no prompt "Press any key" e a tecla não chegava ao guest | Setup nunca iniciava; resolvido com console VNC local temporário + cliente RFB (§4) |
| D16 | Pré-flight exigia elevação em toda execução | impedia a retomada depois que o VMware já estava instalado, sem ganho de segurança |
| D17 | Credencial de bootstrap protegida por DPAPI de outra conta | ao deixar de rodar elevado, o arquivo fica ilegível; agora é regerada antes da instalação ou falha fechada depois dela |
| D18 | Reparo do `.vmx` reescreveria uma VM já criptografada | destruiria a associação da criptografia e, com ela, o vTPM; nesse estado a automação apenas confere |

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
4. ~~Aprovação de UAC a cada execução~~ — **não é mais necessária**: com o VMware já instalado e o diretório da VM gravável, a automação roda pela conta de trabalho comum (§2). Nesta máquina a conta de trabalho não pertence ao grupo de administradores e a elevação usaria outra conta administrativa, o que prenderia os segredos de bootstrap ao DPAPI dela — rodar sem elevação é o estado preferível e evita esse acoplamento;
5. Reboot do host, se exigido pelo instalador VMware (não foi necessário nesta instalação);
6. Decisões posteriores da cadeia GATE 5 (materialização/scan do alvo) — **fora do escopo desta automação**, que termina no snapshot `BASELINE_GATE5_ISOLATED`.

## 11. Bloqueio atual: gate humano do vTPM

**Bloqueador:** `HUMAN_GATE_REQUIRED — VMWARE_VTPM`.

Constatado empiricamente nesta instalação do Workstation 26.0.0: `managedvm.autoAddVTPM="software"` aparece no `DICT` do `vmware.log` mas **nenhum dispositivo TPM é criado** por `vmrun start` sobre um `.vmx` escrito à mão; `vmrun` não expõe comando de TPM; `vmcli` não possui módulo de TPM nem de criptografia. O vTPM do Workstation exige criptografia da VM, cujo material de chave só o próprio VMware gera — inventar essas chaves, copiar identidade TPM de outra VM ou contornar o requisito de TPM do Windows 11 são ações **proibidas** nesta etapa.

**Estado em 2026-08-29 (`PRE_VTPM_READY`):** a VM órfã que ficara ligada sob a conta administrativa foi encerrada pelo operador (confirmado por abertura exclusiva do VMDK, não apenas por `vmrun`), os resíduos do hard power-off foram removidos com a VM comprovadamente parada, e a configuração canônica foi aplicada **antes** da criptografia — `virtualHW.version=22`, `numvcpus=2`, `memsize=4096`, `firmware=efi`, Secure Boot ligado, disco 60 GB thin em NVMe, ISO do Windows em `sata0:0`, ISO de unattend em `sata0:1`, shared folders/clipboard/drag-and-drop/USB desabilitados, identidade da VM (`uuid.bios`, MAC gerado) preservada.

**Passo humano restante:** abrir o VMware Workstation → abrir `C:\VMs\FaithRO-GATE5-LAB\FaithRO-GATE5-LAB.vmx` → com a VM desligada → `VM Settings` → `Add` → `Trusted Platform Module` → aceitar a criptografia proposta pelo produto → fechar `VM Settings` → **não iniciar a VM manualmente**.

A senha de criptografia é definida e mantida **exclusivamente pelo operador**: não deve ser digitada no terminal, versionada nem registrada em log.

Depois disso, retomar com:

```powershell
.\scripts\lab\gate5-provision.ps1
```

sem elevação — o pré-flight já não a exige (§2) e a retomada parte do checkpoint `VM_CREATED`.

**Não é mais bloqueio:** o boot da ISO. Ele foi diagnosticado e resolvido nesta etapa, com o Windows 11 Setup em pt-BR comprovadamente iniciando (§4, §7-D15).

## 12. Decisão arquitetural: a senha da criptografia nunca passa pela automação

**Contexto.** O Windows 11 exige TPM 2.0; o vTPM do VMware Workstation exige criptografia da VM. Comprovado nesta instalação, com a VM já criptografada:

- `vmrun` recusa **qualquer** operação — inclusive leitura, como `listSnapshots` — com `Cannot open VM: ..., A password is required for this operation`;
- `vmcli` recusa com `Something went wrong while getting password from stdin`, mesmo para `ConfigParams query`;
- a senha **está** guardada no Gerenciador de Credenciais do Windows (destino `VMware Encrypted VM: <caminho do .vmx>`), colocada lá pelo próprio VMware a pedido do operador, mas as ferramentas de linha de comando não consultam esse cofre;
- a única forma de fornecê-la ao `vmrun` seria `-vp <senha>`, que a exporia na **lista de processos** da máquina — que tem outras contas.

**Decisão (2026-08-29).** A senha de criptografia é exclusiva do operador. A automação **não** a lê, não a pede, não a armazena e não a transporta — nem por `-vp`, nem pelo Gerenciador de Credenciais, nem por variável de ambiente, stdin, arquivo ou argumento de processo. O pequeno custo operacional de algumas intervenções manuais é aceito em vez de reduzir a segurança do desenho.

**Consequências:**

1. Operações de energia e snapshot da VM criptografada são **gates humanos formais** na interface do VMware — parte auditável do procedimento, não falha de automação.
2. Todo payload destinado ao guest é entregue por **mídia controlada** (ISO gerada e verificada no host), não por *guest operations* do `vmrun`.
3. Cada gate humano é mínimo, explícito e seguido de **validação técnica automática** — a confirmação textual do operador nunca é aceita como prova.
4. `Invoke-Gate5Vmrun` falha fechado em VM criptografada (`ENCRYPTED_VM_REQUIRES_HUMAN_POWER_OP`) em vez de tentar a operação.
5. O `.vmx` continua editável porque, no modo de criptografia parcial que o TPM exige, ele permanece em texto plano; `Set-Gate5VmxEntry` troca uma chave por vez e **verifica** que as linhas de material criptográfico saem intactas.

**Testes que impedem regressão:** nenhum caminho fornece a senha ao `vmrun` (`-vp`); nenhum script lê credencial do host (`cmdkey`, `vaultcmd`, `PasswordVault`, `CredRead`, `Get-StoredCredential`); nenhum script pede senha ao operador (`Read-Host`, `Get-Credential`); e `vmrun` falha fechado em VM criptografada. As guardas analisam **apenas código** (comentários removidos pelo tokenizador), para que a documentação da proibição não gere falso positivo.

## 13. Decisão arquitetural: o runtime do Visual C++ vem do pacote oficial da Microsoft

**Contexto.** A primeira instalação limpa chegou ao fim e reportou a evidência completa pela serial, mas com três critérios reprovados:

| Critério | Resultado | Causa raiz |
| --- | --- | --- |
| `yara_4_5_5` | `yara_version` vazio, `rules_compile_ok=false` | `yara64.exe` e `yarac64.exe` importam `VCRUNTIME140.dll`, ausente num Windows 11 limpo — os binários nem iniciam |
| `sanitize_pass` | 67 acertos decisórios | todos `*.sql` sob `AppData\Local\Microsoft\OneDrive\...\WebAssets\sql\`: modelos de consulta do próprio OneDrive, falso positivo do padrão genérico por extensão |
| `ruleset_pinned` | sem verificação possível | a evidência do guest não carregava o commit SHA-40 nem o agregado; contar arquivos não prova o pin |

A dependência foi confirmada lendo a **tabela de importações PE** do `yara64.exe` no host. Ela funciona no host porque o instalador do VMware deposita esse runtime; as `api-ms-win-crt-*` fazem parte do Windows, a `VCRUNTIME140.dll` não.

**Decisão humana (2026-08-29).** O runtime vem **exclusivamente** do redistribuível oficial da Microsoft. Copiar `VCRUNTIME140.dll`/`MSVCP140.dll` do próprio host (implantação *app-local*, tecnicamente permitida pela Microsoft) foi **recusado**: a procedência seria a instalação local em vez de um pacote assinado e versionado. Seguir sem YARA também foi recusado — YARA e o ruleset pinado são requisitos explícitos do baseline do GATE 5.

**Pipeline resultante (fail-closed em cada etapa).**

No host, fase `Vcruntime` (checkpoint `VCRUNTIME_READY`, antes de `Yara`/`Rules`/mídia):

1. valida a URL declarada contra a *allowlist* de hosts da Microsoft;
2. baixa por `HttpWebRequest` e valida a **URL efetiva** (o `aka.ms` redireciona) **antes de gravar um único byte** — `VCRUNTIME_SOURCE_NOT_MICROSOFT`;
3. exige Authenticode `Valid` **e** titular `Microsoft Corporation`, descartando o arquivo se falhar — `VCRUNTIME_SIGNATURE_INVALID`;
4. calcula o SHA-256, grava o pin em `evidence/vcruntime-pin.json` e recusa qualquer divergência posterior — `VCRUNTIME_HASH_MISMATCH`;
5. confere que a versão do pacote cobre o toolset do YARA 4.5.5 (mínimo 14.30) — `YARA_RUNTIME_DEPENDENCY_UNSATISFIED`;
6. preserva o artefato no *staging* controlado (`.local/gate5-lab/vcredist-stage/`, fora do Git).

Na construção da mídia, o SHA-256 é **reconferido na hora de embarcar** — o pin só vale se o arquivo que entra na ISO for o mesmo que foi assinado.

No guest, antes de qualquer uso do YARA:

1. detecta o runtime v14 x64 já instalado pela chave `HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64` **e** pela presença da DLL — a mera existência do arquivo **não** é aceita como prova;
2. se ausente ou insuficiente, confere hash e Authenticode do instalador **na mídia** e o executa com `/install /quiet /norestart`;
3. aceita os códigos 0, 1638 e 3010, mas valida pelo **resultado** (registro + versão + DLL), não pelo código de saída — `VCRUNTIME_INSTALL_FAILED`;
4. prova a correção pela **execução real** de `yara --version` — `YARA_RUNTIME_DEPENDENCY_UNSATISFIED`;
5. só então avança para ruleset e sanitize.

**Correções dos outros dois achados.**

- **Sanitize.** Os padrões decisórios foram separados em *incondicionais* (material de chave e artefatos do projeto: `*.pem`, `id_rsa*`, `.env`, `*faithro*`, `WARP*`, `*.grf`, …) e *por extensão genérica* (`*.sql`, `*.dump`), estes últimos informativos apenas sob `AppData\Local\Microsoft\` e `AppData\Local\Packages\`. Uma chave privada nessas pastas **continua reprovando**. Os acertos de fornecedor são contados e amostrados na evidência — nunca descartados em silêncio.
- **Pin do ruleset.** A mídia passa a carregar `rules-pin.json` com o commit SHA-40, o agregado e o manifesto `<rel, sha256>` completo. O guest **recomputa** o agregado com a mesma regra do host (manifesto `<rel>TAB<sha256>LF`, na ordem do pin, UTF-8 sem BOM) e reporta `ruleset_pinned` só quando o valor bate e nenhum arquivo falta ou diverge. O pin viaja **fora** de `rules/`: dentro dela entraria no próprio conjunto que descreve.
- **`tpm_2_0`.** A evidência trazia `TpmPresent`/`TpmReady`, que não distinguem 1.2 de 2.0. Passa a coletar `SpecVersion` de `Win32_Tpm`.

**Reação do host.** A evidência é gravada **antes** de qualquer decisão; um bloqueio não pode custar a prova que o justifica. Depois disso, bloqueadores reportados pelo guest viram `LAB_AUTOPROVISION_BLOCKED` com o próprio código, e critérios reprovados viram `GUEST_BASELINE_CRITERIA_FAILED` — o provisionamento não segue para isolamento e snapshot com um baseline inválido.

**Arquivos afetados:** `scripts/lab/gate5-common.ps1`, `scripts/lab/gate5-guest-bootstrap.ps1`, `scripts/lab/guest/gate5-payload.ps1`, `scripts/lab/gate5-provision.ps1`, `scripts/lab/gate5-verify-baseline.ps1`, `scripts/lab/test-gate5-lab-automation.ps1`.

**Testes de regressão (102 PASS / 0 FAIL, sintéticos — sem VM, sem rede, sem alvo):** origem oficial aceita/recusada (inclusive sufixo parecido como `download.microsoft.com.evil.example` e HTTP puro); **nenhum script copia `VCRUNTIME`/`MSVCP` do host**, fechando a porta do *fallback app-local*; a URL efetiva é provada antes da gravação; a assinatura é exigida antes do pin; os cinco bloqueadores existem; a presença da DLL não basta; a validação é pelo resultado; ruleset e sanitize só rodam depois do YARA provado; o agregado do ruleset recomputado no guest bate com a regra do host, e reprova com regra alterada, regra faltante ou sem SHA-40; modelos `.sql` do OneDrive deixam de reprovar, mas chave privada e artefato do alvo reprovam **até** dentro de pasta de fornecedor; a evidência carrega todos os critérios; o host preserva a evidência antes de bloquear.

A *allowlist* de downloads do laboratório foi estendida para `aka.ms/vs/<n>/release/vc_redist.x64.exe`, com o motivo registrado no próprio teste.

**Riscos residuais.**

1. O `aka.ms` resolve para a versão corrente do pacote: a primeira aquisição fixa o SHA-256 e as seguintes precisam bater. Trocar de versão é uma decisão consciente (apagar o *staging* para readquirir), não um efeito silencioso.
2. Executar um instalador dentro do guest amplia levemente a superfície de bootstrap. Mitigação: pacote assinado pela Microsoft, hash pinado, verificado no host e de novo no guest, em VM isolada e descartável.
3. O código de saída 3010 (pede reinício) é aceito; se algum cenário exigir o reinício para o runtime funcionar, a prova por `yara --version` reprova e o bloqueio aparece — nunca um falso positivo.

**Rollback.** Reverter o commit desta correção restaura o pipeline anterior, que instala YARA sem runtime e volta a reprovar `yara_4_5_5`; nada no host é alterado além de `.local/gate5-lab/` (fora do Git) e a VM não é tocada. Para descartar apenas o artefato: apagar `.local/gate5-lab/vcredist-stage/` e `evidence/vcruntime-pin.json`.

**Impossibilidade de aplicar ao guest atual.** O único canal de entrega controlado é a mídia, consumida pelo Windows Setup no primeiro logon; o payload da instalação atual já concluiu (`stage=DONE`, tarefa de retomada removida) e a VM criptografada não oferece *guest operations*. Injetar o runtime manualmente no guest atual quebraria a reprodutibilidade do baseline. Logo, a correção exige **nova mídia e nova instalação limpa**, com a VM desligada — um único ciclo, com o watcher já maduro.

## 14. Próxima etapa

Somente após `LAB_AUTOPROVISION_COMPLETE` (critério do prompt: todas as flags de sucesso verdadeiras e as flags proibidas falsas): `ETAPA 2P-E-C5-REAL-EXEC-PREFLIGHT-RERUN`, em sessão separada.
