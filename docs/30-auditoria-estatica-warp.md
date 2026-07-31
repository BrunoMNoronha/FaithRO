# Auditoria estática aprofundada do WARP e preparação do laboratório

> **Status:** AUDITORIA ESTÁTICA CONCLUÍDA / NADA COMPILADO OU EXECUTADO (ETAPA 2P-D).
> **Data:** 2026-07-31.
> **Classificação final:** **APROVADO COM RESTRIÇÕES** (para *planejar* um build
> controlado; ver [§16](#16-decisão-final)).
> **Escopo:** auditoria estática do código-fonte textual do WARP no commit
> fixado e preparação de um laboratório **vazio**. O WARP **não** foi compilado
> nem executado; **nenhum** binário de terceiros foi executado; **nenhum**
> executável do cliente foi copiado ou modificado; **PACKETVER** não foi
> alterado; a VPS não foi acessada.
> Continua [28](28-decisao-ferramenta-preparacao-cliente.md) e
> [29](29-compatibilidade-cliente-2021-11-05-packetver.md); observa
> [16](16-politica-distribuicao-cliente.md).

## 1. Objetivo

Auditar estaticamente, em profundidade, o código-fonte do WARP no commit fixado
`9b1173e9e4e135c68e150704f01186ab5e763acd` e preparar um laboratório local
isolado para uma **futura** compilação e execução controlada — sem compilar,
executar, baixar binários, modificar o `Ragexe`, criar conta, acessar a VPS ou
realizar login. A etapa determina se o WARP pode **avançar para o planejamento**
de um build controlado e quais controles adicionais serão necessários.

Esta aprovação **não** autoriza build, execução, modificação do cliente,
preparação do `Ragexe`, acesso ao servidor ou primeiro login.

## 2. Contexto

- PR #42 integrado por squash em `dev` (SHA `e39ead56c02c02f0365296ffc52e07c62fb9e7b8`).
- WARP aprovado documentalmente **com restrições** ([28](28-decisao-ferramenta-preparacao-cliente.md)).
- Commit fixado: `9b1173e9e4e135c68e150704f01186ab5e763acd`; branch upstream `rock_win32`.
- Compatibilidade do cliente com `PACKETVER=20211103`: **PROVÁVEL** ([29](29-compatibilidade-cliente-2021-11-05-packetver.md)); nenhum rebuild do rAthena recomendado.
- PR #41 (fluxo do Beam) permanece aberto, draft e conflitante com `dev`; é
  **independente** do WARP e **não** foi tocado nesta etapa.

## 3. Arquivos afetados

Criados no FaithRO (apenas texto):

- `docs/30-auditoria-estatica-warp.md` (este documento);
- `client/warp-audit/README.md`;
- `client/warp-audit/upstream-manifest.example.json`;
- `client/warp-audit/security-findings.example.json`;
- `client/warp-audit/patch-selection.example.json`;
- `client/warp-audit/schemas/{upstream-manifest,security-findings,patch-selection}.schema.json`;
- `scripts/validate-warp-audit.py`;
- `.github/workflows/validate-warp-audit.yml`;
- atualizações em `docs/README.md` e `client/README.md`.

Não alterados: `client/patcher/` (fluxo do Beam), documentos do Beam, PR #41.

## 4. Origem e integridade

| Item | Resultado |
| --- | --- |
| Origem | `https://github.com/Neo-Mind/WARP.git` (oficial, sem mirror) |
| Aquisição | `git clone --filter=blob:none --no-checkout` + `sparse-checkout` excluindo binários |
| Objeto do commit | `commit` (`git cat-file -t`) |
| SHA completo | `9b1173e9e4e135c68e150704f01186ab5e763acd` (coincide) |
| Autor / data | Neo (mantenedor) / 2026-05-07 (UTC 15:02:45) — merge do PR #202 (tradução) |
| Branch contendo o commit | `origin/rock_win32` (`branch -r --contains`) |
| `git fsck --full` | sem corrupção |
| Estado do working tree | `detached HEAD` limpo no SHA fixado |
| Submódulos | apenas `Wiki` (documentação), **não** inicializado |
| Tree object (SHA-1) | `1aebae06d5c71a145afc35cc72fcf5c210a08758` |
| Tree digest (SHA-256 da listagem ordenada) | `c09b48906f940f9d579a7f1eef94e0108ba791aa2bc8fae0c9b4633154a0521a` |

SHA-256 de arquivos documentais/catálogo e dos patches candidatos e sensíveis
estão registrados em
[`client/warp-audit/upstream-manifest.example.json`](../client/warp-audit/upstream-manifest.example.json).

## 5. Inventário

- **349** blobs, **33,33 MiB** no total.
- Por classe: **executáveis/bibliotecas** (`.dll`×20, `.exe`×3, `.asi`×1) =
  **30,30 MiB**; **mídia/fontes** (`.png`×59, `.ttf`×2, `.ico`×1) = 0,45 MiB;
  **texto** (`.qjs`×180, `.yml`×32, `.lub`×11, `.mjs`×14, `.ejs`×5, `.md`×4,
  demais) = 2,72 MiB.
- Os `.lub` iniciam com `--[[` → são **Lua textual** (templates de dados), não
  bytecode.

### 5.1 Arquivos compilados encontrados (não materializados)

O commit versiona **24 binários** (31,78 MiB):

- `win32/`: **build prebuilt completo do WARP para Windows** — `WARP.exe`,
  `WARP_bench.exe`, `WARP_console.exe`, `Qt5*.dll` (Core/Gui/Network/Qml/Quick/…),
  `msvcp140.dll`, `vcruntime140.dll`, `d3dcompiler_47.dll`, `libEGL/libGLESv2`,
  plugins QML, `GATE.dll`, `YAML.dll`;
- `Inputs/CDClient.dll` e `Inputs/rdll2.asi`: **payloads injetáveis no cliente**
  (usados pelo patch `CustomDLL`).

Todos foram **classificados por metadados** (caminho, blob SHA, tamanho) e
**nenhum** foi materializado no working tree (via `sparse-checkout`) nem copiado
para o FaithRO. O checkout seletivo trouxe **somente texto**.

## 6. Cadeia de build

Busca por `.pro`, `.pri`, `CMakeLists.txt`, `.cmake`, `.vcxproj`, `.sln`,
`Makefile`, `.qrc` e por fontes `.cpp/.h`: **zero ocorrências**. A branch
`rock_win32` no commit fixado **não** contém fonte C++/Qt nem receita de build; o
núcleo é distribuído **apenas** como binário prebuilt em `win32/`. As demais
branches remotas (`base`, `win32`, `deb32/64`, `rock*`, `docs`, `gh-pages`) são
de distribuição por plataforma; nenhuma branch de fonte foi auditada (fora do
commit fixado). (Ver achado **W1**.)

```text
BUILD REPRODUZÍVEL:      NÃO (sem fonte do núcleo e sem receita neste commit)
TOOLCHAIN IDENTIFICÁVEL: PARCIAL (C++/Qt5 pelo README/DLLs; sem arquivos de projeto)
DEPENDÊNCIAS FIXADAS:    NÃO (nenhuma manifesto de build no commit)
BUILD EXIGE REDE:        INCONCLUSIVO (sem receita para avaliar)
ARQUITETURA:             x86 (win32; DLLs de 32 bits)
ARQUIVOS DE SAÍDA:       WARP.exe (+ Qt runtime) — hoje entregues prontos em win32/
RISCOS:                  confiar em binário prebuilt; ausência de fonte auditável do núcleo
```

## 7. Núcleo (C++/Qt)

O núcleo (abertura/leitura do PE, parsing de cabeçalhos, aplicação de patches,
escrita da saída, backup, atomicidade, logs, carregamento de scripts) reside no
binário `win32/WARP.exe`, **não** presente como fonte no commit — portanto **não
auditável estaticamente** nesta etapa. O que é observável é a **superfície que o
núcleo expõe ao JavaScript**:

- **`Exe`** — representa o PE do cliente carregado. Métodos observados:
  `FindHex/FindHexN/FindText/FindLastHex` (busca de padrão), `Get/Set Int/Uint/Hex/Text/Float`
  (leitura/escrita de bytes), `SetJMP/SetNOPs/SetCALL/Allocate` (patch de código),
  `Phy/Vir/Rva/GetTgtAddr/Vir2Phy` (tradução de endereços), `BuildDate/Version/
  MinorVer/ImageBase/GetSectBegin/FindFunc` (parsing PE / import table),
  `GetUserInput/GetInt/GetSavedInput` (entrada do usuário), `FilePath/FileSize`.
- **`Warp`** — `LoadYaml` (lê YAML dos diretórios do WARP), `Get/SetPatchState`,
  `TestMode`, `Show/ShowInDir`, `identify`, `Path/TgtExe`, `Execute` (ver **W6**).

A superfície nativa exposta ao JS é essencialmente um **patcher de PE**: não há
API de rede, de spawn de processo do sistema, de registro do Windows nem de
carregamento de DLL **para dentro do WARP**.

> **Distinção importante:** strings como `ShellExecuteA`, `LoadLibraryA`,
> `GetProcAddress` que aparecem em `Scripts/Patches/*` são **código x86 emitido
> _no cliente_** por patches (ex.: `UseDefaultBrowser`, `EnableDnsSupport`),
> **não** chamadas do WARP ao sistema.

## 8. Rede, execução externa, DLLs e plugins

Busca em `Scripts/` por `QNetworkAccessManager/Request/Reply`, `QTcpSocket`,
`QUdpSocket`, `XMLHttpRequest`, `fetch(`, `WebSocket`, `download`, `auto-update`,
`telemetry`, `QProcess`, `system(`, `popen`, `ShellExecute`/`CreateProcess`/
`WinExec` (como chamada do WARP), `LoadLibrary`/`GetProcAddress` (como chamada do
WARP), `QPluginLoader`, `QSettings`: **nenhuma ocorrência de superfície de rede,
atualização, telemetria, shell ou plugin no conjunto de scripts inspecionado**.
As únicas URLs `http` nos scripts são cabeçalhos de licença GPL
(`http://www.gnu.org/licenses/`). (Achado informativo **W8**; a conclusão **não**
abrange o binário do núcleo.)

## 9. JavaScript

Engine: JavaScript ECMA-262 embarcada no núcleo nativo (módulos `.mjs`, patches
`.qjs`, templates `.ejs`). Os scripts são descobertos em `Scripts/` (`Init/` a
cada carga; `Support/`, `Patches/`, `Extensions/`). Módulos usam `import` dentro
da árvore `Scripts/`. Há escrita de arquivos via classe nativa
`TextFile(caminho, encoding, modo)` (ex.: extensões que gravam em `Outputs/` via
diálogo `D_OutFile`).

### 9.1 Matriz de superfícies

| Superfície | Permitida pelo engine | Exposta/usada pelo WARP | Risco |
| --- | :-: | :-: | --- |
| Ler arquivos | Sim | Sim (`TextFile 'r'`, `Warp.LoadYaml`, `Exe` reads) | Baixo |
| Escrever arquivos | Sim | Sim (`TextFile 'w'`, normalmente via diálogo `D_OutFile`) | **Médio** (não sandboxed — **W4**) |
| Executar processo do SO | Possível no engine | **Não** evidenciado nos scripts | Baixo |
| Carregar DLL no WARP | Possível | **Não** (só o núcleo carrega Qt) | Baixo |
| Acessar rede | Possível | **Não** evidenciado | Baixo |
| Acessar registro | Possível | **Não** evidenciado (patches mexem no registro do _cliente_) | Baixo |
| Avaliar código dinâmico | Sim | Sim (`eval` sobre identificadores próprios — **W5**) | Médio |
| Importar script externo | Sim (na árvore `Scripts/`) | Sim (módulos internos) | Baixo |
| Sair do diretório | Possível via `TextFile`/caminho | Limitado por diálogo | Médio |

`Warp.Execute` (única ocorrência, `IncrHairs.qjs`) decodifica e executa **blobs
opacos criptografados** — estágio **não auditável estaticamente** (**W6**);
`IncrHairs` é cosmético e **não** faz parte do conjunto mínimo.

## 10. Caminhos e escrita

A escrita do executável de saída, backup automático, atomicidade e tratamento de
`path traversal`/nomes reservados residem no **núcleo binário** (não auditável
como fonte). Do lado JS, a saída usa `Outputs/` por convenção e diálogo de
arquivo; `TextFile` aceita caminho arbitrário (**W4**). Sem evidência de
travessia maliciosa nos scripts inspecionados.

```text
SAÍDA SEPARADA DA ENTRADA:        PARCIAL (Inputs/ vs Outputs/ por convenção; padrão do núcleo não auditável)
BACKUP AUTOMÁTICO:                INCONCLUSIVO (núcleo binário)
ESCRITA ATÔMICA:                  INCONCLUSIVO (núcleo binário)
PATH TRAVERSAL MITIGADO:          INCONCLUSIVO (núcleo binário; JS não sandboxed)
ORIGINAL PRESERVADO POR PADRÃO:   PARCIAL (fluxo Inputs/Outputs preserva; padrão do núcleo não confirmado)
```

Mitigação de laboratório: trabalhar sobre `input-working`, preservar
`input-original`, gerar hash antes/depois e backup manual antes de qualquer
escrita.

## 11. Reconhecimento do executável

`Tables/NemoMap.yml` apenas inclui `Tables/Patch.yml` e `Tables/Input.yml`. O
reconhecimento é **heurístico**: `Exe.BuildDate` (timestamp PE), `Exe.Version` e
casamento de padrões (`FindHex/FindText`). **Não** há reconhecimento por
hash/checksum nem allowlist de builds exatos (nenhum `sha/md5/crc` em `Scripts`/
`Tables`). Metadados já documentados do cliente: família Ragexe, x86, timestamp
PE 2021-11-05, SHA-256 já registrado, assinatura Gravity válida. Nenhum teste
real de reconhecimento foi executado.

```text
PERFIL CANDIDATO ENCONTRADO:      INCONCLUSIVO (exige o arquivo real na etapa futura)
RECONHECIMENTO POR HASH:          NÃO
RECONHECIMENTO POR PADRÃO:        SIM (BuildDate/Version + FindHex/FindText)
CLIENTE DESCONHECIDO É REJEITADO: PARCIAL (sem rejeição global; cada patch falha se o padrão não casar)
RISCO DE FALSO POSITIVO:          MÉDIO
```

## 12. Patches candidatos

Detalhes em
[`client/warp-audit/patch-selection.example.json`](../client/warp-audit/patch-selection.example.json).

| Patch | Finalidade | Necessário 1º acesso | Classificação |
| --- | --- | :-: | --- |
| `DataFolderFirst` | Ler pasta `data` antes do GRF (NOP em saltos após `g_readFolderFirst`; valida e lança erro se o padrão não casar) | Sim | CANDIDATO MÍNIMO |
| `CallKoreaClientInfo` | Corrigir `InitClientInfo` para chamar ambos os seletores de `clientinfo` | Sim | CANDIDATO MÍNIMO |
| `MultiGRFs` | Múltiplos GRFs (se o FaithRO distribuir GRF próprio) | Não | PENDENTE DE TESTE |
| `EnableDnsSupport` | Resolver host por nome (se `clientinfo` usar domínio) | Não | PENDENTE DE TESTE |
| `RestoreClientInfo` | Restaurar leitura de `clientinfo` (variante `.ejs`) | Não | PENDENTE DE TESTE |

Todos os candidatos observados fazem **edições de bytes pequenas e
determinísticas**, com validação prévia (lançam `Error` quando o padrão não é
encontrado — sem escrita às cegas). Nenhum é obrigatório antes do reconhecimento
real, teste em cópia isolada e autorização humana.

## 13. Patches sensíveis

Permanecem **SENSÍVEL — DECISÃO SEPARADA**; **nenhum** é necessário ao primeiro
acesso e **nenhum** pode ser aplicado por padrão.

| Patch (interno) | Efeito | Achado |
| --- | --- | :-: |
| `DisableProtect` (`NoHShield`) | Neutraliza HackShield/AhnLab; remove `aossdk.dll` do import | W3 |
| `DisableEncr` (`NoLoginEncr`) | Login envia a senha **não** criptografada | W3 |
| `CustomDLL` | Reescreve a import table para **injetar DLL arbitrária** (payloads padrão `Inputs/CDClient.dll`, `Inputs/rdll2.asi`) | W2 |
| `EnableProxy` | Desvia `connect()` para função custom que reusa o primeiro IP | W3 |

## 14. Laboratório

Criado **fora** do repositório e do cliente, em área local não sincronizada,
**vazio** nesta etapa: `README.txt` + pastas `upstream/`, `input-original/`,
`input-working/`, `output/`, `backups/`, `evidence/`, `logs/` (todas vazias).
Nenhum `Ragexe`, GRF, DLL, configuração real, IP, conta ou senha foi colocado. O
`README.txt` registra finalidade, proibições, commit do WARP, política de não
redistribuição, a sequência futura de autorização e o rollback por exclusão. O
caminho pessoal do laboratório **não** é versionado.

## 15. Testes, achados, riscos, rollback

### 15.1 Testes

- **Integridade Git:** `cat-file -t` = `commit`; SHA coincide; `branch --contains`
  = `rock_win32`; `fsck --full` sem corrupção; `detached HEAD` limpo.
- **Checkout seletivo:** confirmado que **nenhum** binário (`.dll/.exe/.asi/.png/
  .ttf/.ico`) foi materializado no working tree.
- **Validador:** `scripts/validate-warp-audit.py` aprova os três JSONs; **14
  testes negativos** rejeitados (SHA curto, `source_built/binary_created/
  client_modified=true`, `sha256` inválido, IP, caminho pessoal, drive, path
  absoluto, travessia, senha/token atribuídos, propriedade extra, `const`
  errado, JSON inválido) — todos com código de saída ≠ 0 e sem traceback.
- **Hardening do diff:** varredura por `.exe/.dll/.grf/.zip`, `password/senha/
  secret/token`, `C:\Users\`, `/home/`, `BEGIN PRIVATE KEY`, `Authorization:` —
  ocorrências revisadas individualmente (ver [§15.4](#154-notas-da-varredura)).

### 15.2 Achados (resumo — detalhe em `security-findings.example.json`)

| ID | Sev. | Tema | Bloqueia build futuro? |
| --- | --- | --- | :-: |
| W1 | ALTO | Sem fonte/receita de build no commit; núcleo só prebuilt | **Sim** (para o caminho "compilar do fonte") |
| W2 | ALTO | `CustomDLL` injeta DLL arbitrária (payloads opacos) | Não (fora do mínimo) |
| W3 | ALTO | Patches sensíveis presentes | Não (fora do mínimo) |
| W4 | MÉDIO | `TextFile` grava caminho arbitrário (JS não sandboxed) | Não |
| W5 | MÉDIO | `eval` dinâmico no framework | Não |
| W6 | MÉDIO | Estágio opaco `Warp.Execute` em `IncrHairs` (cosmético) | Não |
| W7 | MÉDIO | Reconhecimento heurístico; risco de falso positivo | Não (mitigável) |
| W8 | INFO | Sem rede/auto-update/telemetria nos scripts | Não |
| W9 | BAIXO | Escrita/backup/atomicidade não auditáveis (núcleo) | Não (mitigável no lab) |
| W10 | INFO | Submódulo só de Wiki, não inicializado | Não |

### 15.3 Riscos

- **Confiança no binário prebuilt** (W1): o núcleo não é auditável como fonte
  neste commit. Mitigação: localizar/auditar a fonte do núcleo **ou** tratar
  `win32/WARP.exe` como binário de terceiros (execução local não elevada, fora da
  VPS, com varredura) — decisão humana separada.
- **Injeção de DLL / patches sensíveis** (W2/W3): jamais por padrão; auditoria e
  autorização individuais.
- **Corrupção do executável**: mitigada por cópia de laboratório + hash + rollback
  por exclusão; original preservado.
- **Legal/PI**: WARP é GPL (uso local); `Ragexe`/assets Gravity são proprietários
  e **nunca** redistribuídos.

### 15.4 Notas da varredura

As únicas ocorrências "sensíveis" no diff são **texto legítimo do relatório**: a
palavra "senha" descrevendo o efeito de `DisableEncr`; o SHA-256 já documentado do
cliente; a URL oficial `https://github.com/Neo-Mind/WARP` (fonte). Não há IP,
segredo, token, caminho pessoal, binário, DLL, GRF, ZIP ou código-fonte do WARP
versionado.

### 15.5 Rollback

Antes do commit: remover os novos arquivos da branch; excluir o laboratório
vazio; excluir o clone temporário do WARP; não tocar em outras worktrees. Antes do
merge: fechar o PR ou corrigir a branch; excluir a worktree dedicada após
preservar evidências; não reescrever `dev`. Após eventual merge: branch a partir
de `dev`, reverter o commit/squash, validar, abrir PR de reversão; sem force push.
Nenhuma reversão de VPS, banco, cliente ou firewall é necessária.

## 16. Decisão final

| Área | Estado | Bloqueia build futuro? |
| --- | --- | :-: |
| Origem e commit | Verificado (oficial, SHA/branch conferidos) | Não |
| Licença | GPL-3.0 (uso local) | Não |
| Inventário | Completo; 24 binários não materializados | Não |
| Build | Sem fonte/receita no commit (W1) | **Sim** (caminho "compilar do fonte") |
| Dependências | Não fixadas no commit | Parcial |
| Rede | Não evidenciada nos scripts (W8) | Não |
| Execução externa | Não evidenciada nos scripts | Não |
| Plugins/DLL | `CustomDLL` injeta no cliente (W2) | Não (fora do mínimo) |
| JavaScript | `eval`/`TextFile` (W4/W5); ofuscação isolada (W6) | Não |
| Caminhos | Núcleo não auditável; JS não sandboxed (W9) | Não (mitigável) |
| Escrita atômica / Backup | Inconclusivo (núcleo) | Não (mitigável) |
| Reconhecimento | Heurístico, sem hash (W7) | Não (mitigável) |
| Patches mínimos | `DataFolderFirst`, `CallKoreaClientInfo` — auditáveis | Não |
| Patches sensíveis | Presentes; decisão separada (W2/W3) | Não |
| Reprodutibilidade | Baixa neste commit | Parcial |
| Laboratório | Criado, vazio, isolado | Não |

**Resultado:** **APROVADO COM RESTRIÇÕES** para *planejar* um build controlado.
As restrições materiais são W1 (definir o caminho: auditar a fonte do núcleo ou
tratar o prebuilt como binário de terceiros), o tratamento separado dos patches
sensíveis (W2/W3) e as mitigações de laboratório para W4/W7/W9.

```text
BUILD_AUTORIZADO=false
EXECUCAO_AUTORIZADA=false
MODIFICACAO_CLIENTE_AUTORIZADA=false
PRIMEIRO_LOGIN_AUTORIZADO=false
```

## 17. Limitações

- O núcleo C++/Qt **não** está presente como fonte no commit fixado; conclusões
  sobre backup, atomicidade e path traversal do núcleo são inconclusivas.
- A conclusão de "sem rede/auto-update/telemetria" abrange **apenas** o conjunto
  de scripts e tabelas inspecionado, **não** o binário prebuilt.
- Os 165 scripts de patch foram auditados por amostragem e leitura integral dos
  candidatos e sensíveis; um estágio (`IncrHairs`) é opaco por design.
- Nenhum teste dinâmico, de reconhecimento ou de compatibilidade foi executado.

## 18. Próxima etapa permitida

Somente após revisão e integração humana desta etapa: **ETAPA 2P-E** —
planejamento e autorização do primeiro build controlado do WARP, mantendo
separadas as autorizações para (1) instalar/selecionar toolchain, (2) compilar,
(3) executar o WARP sem cliente, (4) testar o reconhecimento do `Ragexe`, (5)
modificar uma cópia do `Ragexe`, (6) primeiro login. **Nenhuma** dessas
autorizações é concedida aqui.

## Estado de verificação

- **Fato:** integridade Git; inventário e binários rastreados; ausência de fonte/
  receita no commit; superfície nativa (`Exe`/`Warp`) e ausência de rede/shell nos
  scripts; reconhecimento heurístico sem hash; comportamento dos patches
  candidatos e sensíveis.
- **Inferência/decisão:** APROVADO COM RESTRIÇÕES para planejar o build; W1 como
  restrição material; patches sensíveis fora do mínimo.
- **Pendência:** decisão humana sobre o caminho do núcleo (fonte × prebuilt) e
  sobre cada patch sensível; reconhecimento real e teste de login em etapas
  futuras autorizadas.
- **Nota:** decisão técnica e de conformidade do projeto, **não** parecer jurídico.
