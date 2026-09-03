# Índice da documentação — FaithRO - Laos Deos

Índice central da base de conhecimento técnica do projeto. Toda a documentação
está em português brasileiro. Este índice não renumera os documentos existentes;
apenas os organiza por categoria e registra estado e dependências.

## Como usar

- Comece por [00-base-conhecimento.md](00-base-conhecimento.md) para a visão do
  projeto.
- Para cliente/protocolo, veja [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md).
- Para a política de fontes, veja [10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md).

## Estados possíveis

- **Estado documental** — maturidade do texto: `planejado` · `em elaboração` ·
  `validado` · `desatualizado`.
- **Estado de implantação** — o procedimento descrito já foi executado no
  ambiente real: `não aplicável` (documento conceitual) · `não iniciado` ·
  `em andamento` · `implantado` · `pendente de validação`.

> Um documento pode ter texto `validado` e implantação `não iniciado`. Não marque
> o texto como pendente apenas porque o cliente ou serviço ainda não foi testado.

## Índice por documento

| Documento | Finalidade | Público-alvo | Estado documental | Estado de implantação | Dependências | Última revisão |
| --- | --- | --- | --- | --- | --- | --- |
| [00-base-conhecimento.md](00-base-conhecimento.md) | Visão geral, definição de old school, base level 255, atributos máximos 185 e ASPD máxima 197 | Todos | validado | não aplicável | — | 2026-07-10 |
| [01-decisao-tecnica.md](01-decisao-tecnica.md) | Escolha do emulador (rAthena) | Técnico | validado | não aplicável | 00 | 2026-07-10 |
| [02-roadmap.md](02-roadmap.md) | Fases do projeto | Todos | em elaboração | não aplicável | 00, 01 | 2026-07-10 |
| [03-configuracao-alvo.md](03-configuracao-alvo.md) | Referência mecânica Pre-Renewal e planejamento de base level 255, atributos 185, ASPD 197, classes, rates e conteúdo | Config/gameplay | validado | parcialmente implantado[^1] | 00, 09, 10, 11 | 2026-07-10 |
| [04-operacao-vps.md](04-operacao-vps.md) | Hardware, hardening, portas, backups | Infra/operação | em elaboração | não iniciado | 08 | 2026-07-10 |
| [05-governanca.md](05-governanca.md) | Princípios, regras de mudança, ADRs | Todos | validado | não aplicável | — | 2026-07-10 |
| [06-plano-execucao-inicial.md](06-plano-execucao-inicial.md) | Fluxo de branches e backlog inicial | Técnico | validado | não aplicável | 07 | 2026-07-10 |
| [07-fluxo-pull-request.md](07-fluxo-pull-request.md) | Processo de PR | Colaboradores | validado | não aplicável | 06 | 2026-07-10 |
| [08-preparar-vps-ubuntu-2204.md](08-preparar-vps-ubuntu-2204.md) | Preparação da VPS (issue #2) | Infra | validado | não iniciado | 04 | 2026-07-10 |
| [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md) | Cliente, `PACKETVER`, obfuscação, web server, matriz e testes | Cliente/protocolo | validado | não iniciado | 01, 10 | 2026-07-10 |
| [10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md) | Política e tabela de fontes | Técnico/documental | validado | não aplicável | — | 2026-07-10 |
| [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md) | Unidades systemd do rAthena, binários, portas e web server | Infra/operação | validado | implantado (login/char/map); web server não implantado | 04, 09 | 2026-07-10 |
| [12-configuracao-packetver.md](12-configuracao-packetver.md) | Procedimento planejado de configuração de `PACKETVER`, obfuscação e web server | Cliente/protocolo | validado | não iniciado | 09, 10, 11 | 2026-07-10 |
| [13-credenciais-sql-rathena.md](13-credenciais-sql-rathena.md) | Auditoria e rotação segura das credenciais MariaDB do rAthena (usuário único `faithro_app`, seis diretivas `*_pw`) | Infra/operação/segurança | validado | implantado (rotação executada e validada) | 04, 11 | 2026-07-11 |
| [14-progressao-base-255-overrides.md](14-progressao-base-255-overrides.md) | Overrides versionados de progressão (Base 255, atributos 185, ASPD 197, Curva EXP B, stat points Modelo B); mapeamento para `/opt/faithro/rathena` | Config/gameplay | validado | não iniciado (implementação versionada; não implantado) | 03, 11 | 2026-07-11 |
| [23-planejamento-primeiro-build-controlado-beam.md](23-planejamento-primeiro-build-controlado-beam.md) | Plano do primeiro build controlado do Beam Patcher (Rust 1.85.0 nomeada; build bloqueado, exige autorização humana) | Cliente/build/segurança | validado | não iniciado (build não autorizado) | 19, 20, 21, 22 | 2026-07-25 |
| [24-runbook-primeiro-build-controlado-beam.md](24-runbook-primeiro-build-controlado-beam.md) | Runbook operacional, modelo de autorização humana e template de evidência do primeiro build (build bloqueado; autorização não concedida) | Cliente/build/segurança | validado | não iniciado (autorização não concedida) | 19, 20, 21, 22, 23 | 2026-07-25 |
| [25-solicitacao-autorizacao-primeiro-build-beam.md](25-solicitacao-autorizacao-primeiro-build-beam.md) | Solicitação formal de autorização humana do primeiro build (pendente de decisão; não concede autorização; merge do PR não equivale à autorização) | Cliente/build/segurança | validado | não iniciado (decisão humana pendente) | 19, 20, 21, 22, 23, 24 | 2026-07-26 |
| [26-pacote-decisao-humana-primeiro-build-beam.md](26-pacote-decisao-humana-primeiro-build-beam.md) | Pacote de decisão humana e registro de decisão em branco do primeiro build (decisão não tomada; não concede autorização; decisão não executa o build) | Cliente/build/segurança | validado | não iniciado (decisão humana pendente) | 19, 20, 21, 22, 23, 24, 25 | 2026-07-26 |
| [28-decisao-ferramenta-preparacao-cliente.md](28-decisao-ferramenta-preparacao-cliente.md) | Decisão da ferramenta de preparação (hex) do executável do cliente: WARP `APROVAR COM RESTRIÇÕES`, NEMO atual (4144) `REJEITADO` por licença ausente; não autoriza execução | Cliente/segurança | validado | não iniciado (autorização humana pendente) | 09, 16, 17, 29 | 2026-07-27 |
| [29-compatibilidade-cliente-2021-11-05-packetver.md](29-compatibilidade-cliente-2021-11-05-packetver.md) | Reconciliação do cliente 2021-11-05 com `PACKETVER=20211103`: compatibilidade `PROVÁVEL`, sem rebuild do servidor; teste de login controlado pendente | Cliente/protocolo | validado | não iniciado | 09, 12 | 2026-07-27 |
| [30-auditoria-estatica-warp.md](30-auditoria-estatica-warp.md) | Auditoria estática aprofundada do WARP (commit fixado) e laboratório vazio: `BLOQUEADO PARA BUILD DO FONTE` (núcleo só prebuilt no commit — W1) e `APROVADO COM RESTRIÇÕES` apenas para decidir o caminho do núcleo (2P-E-A); patches sensíveis fora do mínimo; não autoriza build/execução/uso do prebuilt/modificação do cliente | Cliente/build/segurança | validado | não iniciado (build não autorizado) | 16, 28, 29 | 2026-07-31 |
| [31-decisao-caminho-nucleo-warp.md](31-decisao-caminho-nucleo-warp.md) | Investigação do caminho do núcleo (2P-E-A) e pacote de decisão humana: fonte C++/Qt `FONTE NÃO LOCALIZADA NO ESCOPO PESQUISADO`; blob do prebuilt no repo oficial com `PROVENIÊNCIA PARCIAL` (custody FRACA, sem validar o binário); recomendação = submeter `PREBUILT_PATH` e `STOP_PATH` ao decisor sem preferência automática; nenhuma opção selecionada, nenhuma autorização | Cliente/build/segurança | validado | não iniciado (decisão humana pendente) | 16, 28, 30 | 2026-07-31 |
| [32-registro-decisao-caminho-nucleo-warp.md](32-registro-decisao-caminho-nucleo-warp.md) | Registro da decisão humana (2P-E-A2): `PREBUILT_PATH` **selecionado apenas para planejamento** da auditoria binária offline; prebuilt não materializado nem executado; todas as flags operacionais `false`; template preservado em branco; merge não autoriza a próxima ação; cada gate futuro exige decisão humana separada | Cliente/build/segurança | validado | não iniciado (só planejamento autorizado) | 16, 28, 30, 31 | 2026-07-31 |
| [33-plano-auditoria-binaria-offline-warp.md](33-plano-auditoria-binaria-offline-warp.md) | Plano (2P-E-B-PREBUILT) da auditoria binária **offline** do prebuilt em 17 gates independentes com decisão humana e `STOP_PATH`: `PLANO CRIADO — NENHUMA MATERIALIZAÇÃO AUTORIZADA`; nada baixado/materializado/executado; todas as autorizações operacionais `false`; merge não autoriza o GATE 1 | Cliente/build/segurança | validado | não iniciado (só planejamento) | 16, 30, 31, 32 | 2026-07-31 |
| [34-registro-autorizacao-gate-0-proveniencia-warp.md](34-registro-autorizacao-gate-0-proveniencia-warp.md) | Registro (2P-E-C0-A) da autorização humana **exclusiva do GATE 0** (reconfirmação de proveniência por metadados): `GATE 0 AUTORIZADO — AINDA NÃO INICIADO`; só `provenance_reconfirmation_authorized=true`; nenhuma consulta upstream nesta etapa; nada materializado; GATE 1 proibido; merge não executa o GATE 0 | Cliente/build/segurança | validado | autorizado, não iniciado | 16, 30, 32, 33 | 2026-07-31 |
| [35-resultado-gate-0-proveniencia-warp.md](35-resultado-gate-0-proveniencia-warp.md) | Resultado (2P-E-C0-B) da execução do GATE 0 **por metadados oficiais**: `GATE 0 CONCLUÍDO — APROVADO POR METADADOS` (`COMPLETED_PASS`); proveniência declarada consistente com os metadados (repo/commit/árvore/caminho/blob OID/tamanho/licença); **nenhum** conteúdo de blob acessado, nada baixado/materializado/executado; Git object ID ≠ SHA-256 local; GATE 1 ainda proibido, exige nova decisão humana | Cliente/build/segurança | validado | concluído (aprovado por metadados) | 16, 30, 33, 34 | 2026-08-01 |
| [38-auditoria-prontidao-primeiro-acesso.md](38-auditoria-prontidao-primeiro-acesso.md) | Registro consolidado da auditoria de prontidão do primeiro acesso (somente leitura, 2026-08-03): reconfirma runtime do servidor e `PACKETVER=20211103` sem override; registra `new_account: no` como decisão de segurança + procedimento planejado de conta de homologação; reconcilia a cadeia WARP (GATE 2 concluído, GATE 3 não autorizado); decisão `BLOQUEADO PARA HOMOLOGAÇÃO` | Cliente/protocolo | validado | não iniciado (bloqueado) | 04, 09, 11, 12, 13, 28, 29, 37 | 2026-08-03 |
| [39-resultado-gate-3-identidade-assinatura-warp.md](39-resultado-gate-3-identidade-assinatura-warp.md) | Resultado (2P-E-C3) do **GATE 3** (identidade e assinatura estática **offline**) **após revisão corretiva 2P-E-C3-R1**: `EVIDENCE_INVALIDATED_PENDING_REPEAT` — o `COMPLETED_PASS` foi **suspenso** (D1 semântica de `opened`; D2 `size_of_optional_header=267` == magic PE32, indício de offset incorreto; D3 parser não versionado, agora substituído por [`scripts/inspect-warp-pe-identity.py`](../scripts/inspect-warp-pe-identity.py) com fixtures; D4 OpenSSL não invocado). Fatos do GATE 2 (blob OID/tamanho/SHA-256) **preservados**; identidade PE/assinatura **pendentes de reconfirmação**; **sem nova materialização**; **GATE 4 não autorizado**. Revisões R2/R3/R4/R4.1 endureceram o inspetor PE (Section Table, `SizeOfHeaders`, Certificate Table estrutural), modelaram estados PASS/FAIL/STOPPED, fecharam a atomicidade da repetição (sem artefatos órfãos), a saída presa aos bytes exatos (schema fechado) e a proveniência do parser/testes recalculada offline, e (R4.1) prenderam a referência da saída no caminho `COMPLETED_FAIL` por igualdade exata e validaram os invariantes de `parser_execution` (estados FAIL fechados). **Repetição corretiva executada (2P-E-C3-REPEAT): `COMPLETED_PASS`** sob decisão humana real `AUTHORIZE_CORRECTIVE_REPEAT_GATE_3` — materialização única do blob `c853da42…` (GitHub oficial, por object ID), identidade reconfirmada igual ao GATE 2, parser revisado só-leitura (`SizeOfOptionalHeader=224`, magic `0x010b`, 5 seções, Certificate Table `present=false`), saída presa por bytes, binário removido, sem execução; evidência histórica invalidada **preservada**; GATE 4 e 2ª repetição não autorizados | Cliente/build/segurança | validado | repetição executada (COMPLETED_PASS) | 16, 33, 35, 37 | 2026-08-03 |
| [40-preparacao-gate-4-inventario-pe-estatico-warp.md](40-preparacao-gate-4-inventario-pe-estatico-warp.md) | Preparação (2P-E-C4-PREP) da ferramenta do **GATE 4** (inventário PE **estático offline**): analisador [`scripts/inspect-warp-pe-static.py`](../scripts/inspect-warp-pe-static.py) (stdlib, bounds checking, fail-closed, saída determinística sanitizada) + testes com **fixtures sintéticas** [`scripts/test-warp-pe-static.py`](../scripts/test-warp-pe-static.py); schemas fechados de saída/decisão/evidência PASS-FAIL-STOPPED do GATE 4; validador estendido (`gate-04-prep`: convenção, máquina de estados atômica, `gate_4_authorized=false`, `gate_5_authorized=false`, contagens reais = 0). **Não** executa o GATE 4, **não** materializa/inspeciona o `WARP.exe`, **não** cria decisão/evidência/saída real; artefatos byte-fixados do GATE 3 **inalterados**. Próxima decisão humana (PR separado): `AUTHORIZE_GATE_4_EXECUTION` / `STOP_PATH` | Cliente/build/segurança | validado | preparação (execução não autorizada) | 16, 33, 39 | 2026-08-04 |
| [42-autorizacao-execucao-gate-4-inventario-pe-warp.md](42-autorizacao-execucao-gate-4-inventario-pe-warp.md) | Registro (2P-E-C4-AUTH) da **decisão humana real** `AUTHORIZE_GATE_4_EXECUTION` (decisor `BrunoMNoronha`): autoriza **uma única** execução do **GATE 4** (inventário PE estático offline), presa ao squash `a5843c3` (PR #54) e aos blobs `f223ae7b` (analisador) / `fdc79947` (testes). **DECISÃO AUTORIZADA — EXECUÇÃO NÃO INICIADA**: `gate_4_authorized=true`, `gate_4_execution_authorized=true`, `gate_5_authorized=false`, `execution_authorized=false`; **não** executa o PE, **não** materializa `WARP.exe`, **não** cria saída/evidência real. A execução ocorrerá em **PR separado** | Cliente/build/segurança | validado | decisão registrada (execução não iniciada) | 40 | 2026-08-05 |
| [43-resultado-gate-4-inventario-pe-estatico-warp.md](43-resultado-gate-4-inventario-pe-estatico-warp.md) | Resultado (2P-E-C4-EXEC) da execução **única** do **GATE 4** (inventário PE estático offline): **`COMPLETED_PASS`**. Blob `c853da42…` materializado por object ID (GitHub oficial), identidade reconfirmada (1137152 bytes, git OID `c853da42…`, SHA-256 `345f3464…`), analisador revisado invocado **uma vez** (só-leitura, exit 0), saída presa por SHA-256 `84c3c49a…`, binário e diretório **removidos**. PE32 x86 Qt5, 5 seções (sem W+X), não assinado, `asInvoker`, sem imports de rede/injeção. `COMPLETED_PASS` = auditoria estática conforme o contrato, **não** aprova o binário; **GATE 5 e uso no cliente não autorizados**; nenhum binário versionado | Cliente/build/segurança | validado | COMPLETED_PASS | 40, 42 | 2026-08-05 |
| [44-gate-5-decisao-e-plano.md](44-gate-5-decisao-e-plano.md) | Preparação (2P-E-C5-PREP) da **decisão humana do GATE 5** (verificações locais de segurança): identifica a definição canônica (doc 33 §11; plano `gate_id=5`), classifica como **D2** (nomeado/definido em alto nível, preparação operacional ausente), analisa lacunas/riscos e propõe plano de controle e matriz de decisão. **Não** executa o GATE 5, **não** repete o GATE 4, **não** altera a saída/evidência do GATE 4, **não** materializa/executa PE, **não** prepara cliente nem acessa VPS. `decision_status=PENDING_HUMAN_DECISION`, `gate_5_authorized=false`, `execution_authorized=false`, `client_preparation_authorized=false`. Decisão humana pendente em PR separado | Cliente/build/segurança | validado | preparação (GATE 5 não autorizado) | 16, 33, 40, 43 | 2026-08-05 |
| [45-gate-5-preparacao-operacional.md](45-gate-5-preparacao-operacional.md) | Preparação operacional (2P-E-C5-TOOLING-PREP) do **GATE 5** (verificações locais de segurança): orquestrador estático [`scripts/warp-audit-gate-05.py`](../scripts/warp-audit-gate-05.py) (stdlib, fail-closed, sem rede, sem execução do artefato; modos `--validate-only`/`--fixture-mode`; **modo real bloqueado**) + testes só com **fixtures sintéticas** [`scripts/test-warp-audit-gate-05.py`](../scripts/test-warp-audit-gate-05.py); schemas fechados de entrada/evidência (flags `false`; evidência de exemplo `FIXTURE_VALIDATION_PASS`, nunca `GATE_PASSED`); adapters `synthetic-local` (habilitado) e `windows-defender-local`/`yara-local` (**só contrato**, não executados); validador/CI/`.gitattributes`/EOL estendidos. **Não** executa o GATE 5, **não** usa o WARP real, **não** executa scanner real, **não** faz upload, **não** prepara cliente nem acessa VPS. `gate_5_authorized=false`, `execution_authorized=false`, `local_security_scan_authorized=false`, `external_reputation_upload_authorized=false`, `client_preparation_authorized=false`. Execução real exige nova decisão humana em PR separado | Cliente/build/segurança | validado | preparação (execução não autorizada) | 16, 33, 40, 44 | 2026-08-05 |
| [46-decisao-execucao-real-gate-5-verificacoes-locais.md](46-decisao-execucao-real-gate-5-verificacoes-locais.md) | Registro (2P-E-C5-REAL-AUTH-DECISION) da **decisão humana real** de autorização condicional da execução real do **GATE 5** (verificações locais de segurança): `AUTHORIZE_GATE_5_LOCAL_EXECUTION` (decisor `BrunoMNoronha`); fecha as lacunas do doc 44 §10 (lista fechada Defender+YARA, ambiente isolado, R13, critérios de resultado PASS/FINDING/ERROR/TIMEOUT/BLOCKED); `gate_5_authorized=true`, `local_security_scan_authorized=true`, `temporary_materialization_authorized=true`, `execution_authorized=false`, `client_preparation_authorized=false`. **DECISÃO AUTORIZADA — EXECUÇÃO NÃO INICIADA**; execução real em PR separado | Cliente/build/segurança | validado | decisão registrada (execução não iniciada) | 16, 33, 40, 44, 45 | 2026-08-28 |
| [47-provisao-laboratorio-gate-5.md](47-provisao-laboratorio-gate-5.md) | Especificação, runbook e auditoria de prontidão da provisão do laboratório isolado para o GATE 5 (VM Windows descartável, isolamento externo de rede, YARA 4.5.5, Yara-Rules/rules pinado); registra pré-condições e bloqueios BLK-01..BLK-04 | Infra/segurança/auditoria | validado | em andamento (bloqueios registrados; alvo não materializado) | 16, 33, 40, 44, 45, 46 | 2026-08-28 |
| [48-autoprovisionamento-laboratorio-gate-5.md](48-autoprovisionamento-laboratorio-gate-5.md) | Especificação e automação fail-closed de autoprovisionamento do laboratório GATE 5 | Infra/segurança/automação | validado | implantado | 47 | 2026-09-03 |
| [49-prontidao-operacional-runtime-primeiro-acesso.md](49-prontidao-operacional-runtime-primeiro-acesso.md) | Homologação e validação da prontidão de runtime do servidor (login, char, map, MariaDB, systemd, firewall e perfil de conexão) para o primeiro acesso | Infra/operação | validado | implantado | 04, 11, 13, 29, 38 | 2026-09-03 |
| [50-primeiro-acesso-cliente.md](50-primeiro-acesso-cliente.md) | Reconciliação de drift (Base Level 185, Packet Obfuscation) e prontidão para o handshake de primeiro acesso do cliente | Infra/operação | validado | implantado | 04, 11, 13, 29, 49 | 2026-09-03 |
| [99-checklists.md](99-checklists.md) | Listas de verificação para deploy, rollback e manutenção. | Todos | validado | não aplicável | — | 2026-07-10 |

[^1]: No documento 03, "parcialmente implantado" significa apenas que a
    configuração registrada do build está alinhada com Pre-Renewal. Base
    level 255, atributos naturais máximos 185, ASPD máxima 197, rates,
    classes e conteúdo continuam pendentes de implantação e validação.

## Índice por categoria

- **Visão geral e decisões:** [00](00-base-conhecimento.md),
  [01](01-decisao-tecnica.md), [05](05-governanca.md).
- **Planejamento e processo:** [02](02-roadmap.md),
  [06](06-plano-execucao-inicial.md), [07](07-fluxo-pull-request.md),
  [99](99-checklists.md).
- **Infraestrutura e operação:** [04](04-operacao-vps.md),
  [08-preparar-vps-ubuntu-2204.md](08-preparar-vps-ubuntu-2204.md),
  [11-servicos-systemd-rathena.md](11-servicos-systemd-rathena.md),
  [13-credenciais-sql-rathena.md](13-credenciais-sql-rathena.md),
  [47-provisao-laboratorio-gate-5.md](47-provisao-laboratorio-gate-5.md),
  [48-autoprovisionamento-laboratorio-gate-5.md](48-autoprovisionamento-laboratorio-gate-5.md),
  [49-prontidao-operacional-runtime-primeiro-acesso.md](49-prontidao-operacional-runtime-primeiro-acesso.md),
  [50-primeiro-acesso-cliente.md](50-primeiro-acesso-cliente.md).
- **Gameplay e balanceamento:** [03](03-configuracao-alvo.md) (mecânica
  Pre-Renewal, base level 255, atributos máximos 185, ASPD máxima 197 e
  rates, ver também [00](00-base-conhecimento.md)),
  [14](14-progressao-base-255-overrides.md) (overrides versionados de
  progressão; ainda não implantados).
- **Cliente e protocolo:** [09](09-cliente-baseline-protocolo.md),
  [12](12-configuracao-packetver.md),
  [29](29-compatibilidade-cliente-2021-11-05-packetver.md) (cliente 2021-11-05 ×
  `PACKETVER=20211103`, compatibilidade `PROVÁVEL`, sem rebuild),
  [38](38-auditoria-prontidao-primeiro-acesso.md) (registro consolidado da
  auditoria de prontidão do primeiro acesso; runtime reconfirmado; `new_account:
  no` como decisão de segurança; cadeia WARP no GATE 2; `BLOQUEADO PARA
  HOMOLOGAÇÃO`).
- **Preparação do executável do cliente:**
  [28](28-decisao-ferramenta-preparacao-cliente.md) (decisão da ferramenta de
  hex: WARP aprovado com restrições; NEMO atual rejeitado por licença ausente;
  não autoriza execução),
  [30](30-auditoria-estatica-warp.md) (auditoria estática aprofundada do WARP no
  commit fixado e laboratório vazio; `BLOQUEADO PARA BUILD DO FONTE` e `APROVADO
  COM RESTRIÇÕES` apenas para decidir o caminho do núcleo (2P-E-A); não autoriza
  build, execução, uso do prebuilt nem modificação do cliente),
  [31](31-decisao-caminho-nucleo-warp.md) (investigação do caminho do núcleo e
  pacote de decisão humana; fonte não localizada, prebuilt com proveniência
  parcial; nenhuma opção selecionada, nenhuma autorização),
  [32](32-registro-decisao-caminho-nucleo-warp.md) (registro da decisão humana:
  `PREBUILT_PATH` selecionado **apenas para planejamento** da auditoria binária
  offline; prebuilt não materializado nem executado; flags operacionais `false`;
  merge não autoriza a próxima ação),
  [33](33-plano-auditoria-binaria-offline-warp.md) (plano da auditoria binária
  offline em 17 gates independentes; `PLANO CRIADO — NENHUMA MATERIALIZAÇÃO
  AUTORIZADA`; nada materializado/executado; merge não autoriza o GATE 1),
  [34](34-registro-autorizacao-gate-0-proveniencia-warp.md) (registro da autorização
  humana **exclusiva do GATE 0** — reconfirmação de proveniência por metadados;
  `GATE 0 AUTORIZADO — AINDA NÃO INICIADO`; nenhuma consulta upstream nesta etapa;
  GATE 1 proibido; merge não executa o GATE 0),
  [35](35-resultado-gate-0-proveniencia-warp.md) (resultado da execução do GATE 0 por
  metadados oficiais; `GATE 0 CONCLUÍDO — APROVADO POR METADADOS` — proveniência
  consistente; nada baixado/materializado/executado; Git object ID ≠ SHA-256 local;
  GATE 1 exige nova decisão humana),
  [36](36-registro-autorizacao-gate-1-materializacao-warp.md) (registro da autorização
  do GATE 1 — materialização),
  [37](37-resultado-gate-2-materializacao-integridade-warp.md) (resultado do GATE 2 —
  integridade local e hashing),
  [39](39-resultado-gate-3-identidade-assinatura-warp.md) (resultado do GATE 3 —
  identidade e assinatura estática offline),
  [40](40-preparacao-gate-4-inventario-pe-estatico-warp.md) (preparação da ferramenta
  do GATE 4 — inventário PE estático),
  [42](42-autorizacao-execucao-gate-4-inventario-pe-warp.md) (autorização da execução
  do GATE 4),
  [43](43-resultado-gate-4-inventario-pe-estatico-warp.md) (resultado da execução do
  GATE 4 — COMPLETED_PASS),
  [44](44-gate-5-decisao-e-plano.md) (preparação da decisão e plano de controle do
  GATE 5 — verificações locais de segurança),
  [45](45-gate-5-preparacao-operacional.md) (preparação operacional do GATE 5 —
  orquestrador, schemas, testes sintéticos),
  [46](46-decisao-execucao-real-gate-5-verificacoes-locais.md) (registro da decisão
  humana real de autorização condicional da execução real do GATE 5),
  [47](47-provisao-laboratorio-gate-5.md) (especificação, runbook e auditoria de
  prontidão do laboratório isolado para o GATE 5; bloqueios BLK-01..BLK-04).
- **Patcher e build auditável do Beam:**
  [23](23-planejamento-primeiro-build-controlado-beam.md) (planejamento do
  primeiro build controlado; build ainda não autorizado),
  [24](24-runbook-primeiro-build-controlado-beam.md) (runbook operacional,
  autorização humana e evidência; autorização não concedida),
  [25](25-solicitacao-autorizacao-primeiro-build-beam.md) (solicitação formal
  de autorização humana; pendente de decisão, não concede autorização),
  [26](26-pacote-decisao-humana-primeiro-build-beam.md) (pacote de decisão
  humana e registro em branco; decisão não tomada, não concede autorização).
- **Fontes comunitárias:** [10](10-fontes-comunitarias-rathena.md).
- **Templates:** [templates/ADR.md](templates/ADR.md),
  [templates/PULL_REQUEST_TEMPLATE.md](templates/PULL_REQUEST_TEMPLATE.md).

## Convenções

- Numeração `NN-nome.md`; próximos documentos usam o próximo número livre (a
  partir de `11`), sem renumerar os existentes.
- Documentos de procedimento técnico devem conter: Objetivo, Contexto e
  premissas, Arquivos afetados, Passos, Testes, Riscos, Rollback, Referências.
- Distinguir sempre: fato oficial, fato confirmado no código, decisão do projeto,
  recomendação comunitária, hipótese e pendência.
- Não versionar segredos nem material proprietário (ver
  [../SECURITY.md](../SECURITY.md) e [05-governanca.md](05-governanca.md)).
</content>
