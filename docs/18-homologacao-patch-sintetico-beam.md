# Homologação sintética do fluxo do Beam Patcher (ETAPA 2O-D)

> **Escopo:** homologação de um **laboratório 100% sintético** do fluxo conceitual
> de atualização do Beam Patcher. **Não** usa cliente Ragnarok, `Ragexe`,
> `data.grf`/`rdata.grf`, GRF, BGM, sprite, mapa ou qualquer asset da Gravity.
> **Não** executa o binário do Beam, **não** faz deploy e **não** acessa a VPS.
> Complementa [17-decisao-patcher-launcher.md](17-decisao-patcher-launcher.md).
>
> **Classificação final:** **APROVADO COM RESTRIÇÕES** — o laboratório e as
> validações próprias passam; a execução dinâmica do Beam está bloqueada por
> ausência de toolchain (ver §17).

## 1. Objetivo

Determinar, com evidências reproduzíveis, se o Beam Patcher pode avançar para uma
homologação posterior mais próxima do cliente real, exercitando o fluxo:

```text
manifesto → servidor HTTP 127.0.0.1 → download → verificação de integridade
→ aplicação em diretório sintético descartável → validação do estado final
```

sem cliente real, sem executável de terceiros e sem asset proprietário.

## 2. Escopo

- Gerador determinístico do conteúdo sintético.
- Manifesto conceitual + payload servido por loopback.
- Verificação de integridade por SHA-256.
- Simulador de aplicação (do laboratório, **não** o Beam) e prova de invariantes.
- Testes negativos de segurança (traversal, malformado, hash incompatível, etc.).
- Workflow de CI para os artefatos sintéticos.

## 3. Premissas

- Toolchain já instalada é a única utilizável; **nada** é instalado nesta etapa.
- O patch server é do próprio FaithRO e loopback-only no laboratório.
- SHA-256 é o controle de integridade primário.
- Nenhum binário de terceiros é executado sem origem e versão verificáveis.

## 4. Exclusões

Não há, em nenhum ponto: cliente Ragnarok, `Ragexe`, `data.grf`/`rdata.grf`, GRF,
BGM, sprite, mapa, executável (oficial ou modificado), pacote comunitário com
asset proprietário, binário de terceiros versionado, build do Beam, instalação de
Rust/Node/Tauri/Build Tools, deploy, acesso à VPS, SSO, auto-update ou lançamento
de executável após o patch.

## 5. Ambiente

| Ferramenta | Disponível | Versão | Observação |
| --- | --- | --- | --- |
| Python 3 | Sim | 3.14.6 | Usado no gerador, validador e servidor loopback (stdlib) |
| Git | Sim | 2.55.0 | Controle de versão |
| Node.js | Sim | 24.18.0 | Não utilizado (Tauri também exige Rust) |
| npm | Sim | 11.16.0 | Não utilizado |
| rustc | **Não** | — | **Necessário** para compilar o Beam |
| cargo | **Não** | — | **Necessário** para compilar o Beam |
| pnpm | Não | — | Não utilizado |

Sistema: Windows 11. Nenhuma variável de ambiente global ou PATH foi alterada.

## 6. Versão e origem do Beam

- Origem oficial: `https://github.com/beamguides/beam-patcher` (sem mirror).
- Referência fixada: **v1.0.1**, commit **`feed978870`** (ver docs/17).
- **Nenhum fonte local do Beam** foi encontrado ou clonado nesta etapa; nenhum
  binário do Beam foi construído ou executado. Não há hash de binário a informar.
- Decisão: **não clonar** o repositório de terceiros nesta etapa — sem toolchain
  Rust, um clone não permitiria build nem execução auditável, e o formato binário
  `.beam` não seria consumível de qualquer forma. A confirmação do formato binário
  fica para a ETAPA 2O-D1.

## 7. Ferramentas disponíveis

Ver §5. Cenário **D2** (toolchain do Beam ausente): prosseguiu-se com o
laboratório sintético em Python (stdlib), sem instalar nada.

## 8. Estrutura do laboratório

Artefatos versionados (todos textuais, próprios, UTF-8, LF):

```text
scripts/generate-synthetic-patch-lab.py     # gerador determinístico
scripts/validate-synthetic-patch-lab.py     # validador + simulador + self-test
client/patcher/fixtures/synthetic/
├── README.md
├── source/{config,data,remove}/…           # conteúdo-fonte que o patch entrega
├── expected/manifest.example.json          # manifesto conceitual determinístico
├── expected/target-state.example.json      # SHA-256 de before/after
└── scenarios/…                             # documentação G1–G15
client/patcher/lab/README.md                # execução (lab fora do repo)
.github/workflows/validate-synthetic-patch-lab.yml
```

Laboratório **executável** (gerado em diretório temporário descartável, nunca
versionado):

```text
<DIR_TEMPORARIO>/lab/
├── target-before/   config/ data/{version.txt,obsolete.txt} logs/
├── target-after/    config/ data/{version.txt,welcome.txt}  logs/
├── server/          manifest.json  files/…
├── expected-state.json
└── LAB-METADATA.json
```

## 9. Formato dos artefatos

O patch é um **manifesto JSON conceitual** mais os arquivos de payload servidos
por loopback. Todos marcados com:

```text
FORMATO CONCEITUAL — NÃO CONSUMÍVEL PELO BEAM
```

O formato binário oficial do Beam (`.beam`) **não** foi confirmado a partir do
fonte fixado (sem toolchain). Nenhum arquivo recebe extensão real do Beam. É
proibido chamar este manifesto de "pacote Beam".

## 10. Manifestos e integridade

- `hash_algorithm: sha256` obrigatório; `md5`/`sha1` como fonte primária são
  rejeitados. Se o Beam exigir MD5 no seu formato, o MD5 seria apenas
  compatibilidade — o SHA-256 permanece como controle independente do FaithRO.
- Cada ação `create`/`update` traz `sha256` (64 hex) e `size`; `remove` não tem
  payload.
- Ações ordenadas deterministicamente por `(op, path)`; caminhos sempre em `/`.
- Sem timestamps variáveis nos artefatos → geração reproduzível byte a byte.

## 11. Servidor HTTP loopback

`python -m http.server 0 --bind 127.0.0.1 --directory <…>/lab/server`. Bind
exclusivo em `127.0.0.1`, porta dinâmica, servindo apenas `server/`; nunca
`0.0.0.0`/`::`, nunca a raiz do repositório, sem upload, sem firewall, encerrado
ao final.

## 12. Metodologia

1. Gerar o laboratório em diretório temporário.
2. Validar `--root`: integridade SHA-256, comparação com `expected-state.json`,
   aplicação pelo simulador e reaplicação (idempotência).
3. Servir por loopback e baixar o payload; conferir hash do download.
4. Executar `--self-test`: bateria de manifestos maliciosos/malformados em
   diretórios temporários; nenhum deve passar.
5. Provar determinismo comparando duas gerações por hash de árvore.
6. Confirmar independência de CWD executando de um diretório externo.
7. Confirmar ausência de binários rastreados e escopo do diff.

Distinção explícita de estados de teste: **executado**, **verificado por código**,
**não executado**, **bloqueado**.

## 13. Matriz G1–G15

| Teste | Objetivo | Método | Resultado | Evidência | Observação |
| ----- | -------- | ------ | --------- | --------- | ---------- |
| G1 — Geração determinística | Duas gerações iguais | `generate` ×2 + hash de árvore | **PASS** | §14.1 | Árvores com SHA-256 idêntico |
| G2 — Estado inicial | version 0, obsolete presente, flag false | `--root` compara `target-before` com `expected-state` | **PASS** | §14.2 | Verificado por código |
| G3 — Manifesto válido | Todos os SHA-256 conferem | `--root` (payload-integridade) | **PASS** | §14.2 | 3 payloads conferidos |
| G4 — Download em loopback | Servir e baixar por 127.0.0.1 | `http.server` porta dinâmica + download | **PASS** | §14.3 | Hash do download confere |
| G5 — Aplicação válida (simulador) | Aplicar e atingir target-after | Simulador do laboratório | **PASS** | §14.2 | **Não é o Beam** |
| G5b — Aplicação pelo Beam | Aplicar pelo binário do Beam | — | **BLOQUEADO** | §17 | Toolchain ausente |
| G6 — Idempotência | Reaplicar não corrompe | Simulador reaplica | **PASS** | §14.2 | Estado final estável |
| G7 — Hash incompatível | Payload adulterado rejeitado | Corromper 1 byte + `--root` | **PASS** | §14.4 | Alvo não modificado; exit≠0 |
| G8 — Manifesto malformado | JSON/campo/ação inválidos rejeitados | `--self-test` + JSON quebrado | **PASS** | §14.5 | Rejeitado antes de aplicar |
| G9 — Path traversal | `..`/absoluto/UNC rejeitados | `--self-test` + canário | **PASS** | §14.6 | Canário externo intacto |
| G10 — Sobreposição de ações | create/update × remove rejeitado | `--self-test` (overlap) | **PASS** | §14.5 | Duplicidade também rejeitada |
| G11 — Interrupção (invariante) | `.part` não vira final | Parcial órfão + escrita atômica | **PASS** | §14.7 | target-after nunca tem `.part` |
| G11b — Atomicidade do Beam | Retomada real do Beam | — | **BLOQUEADO** | §17 | Toolchain ausente |
| G12 — Sem execução arbitrária | Sem comando pós-patch | Manifesto + validador rejeita | **PASS** | §14.8 | `post_patch_command: null` |
| G13 — SSO/self-update off | SSO e auto-update desabilitados | Templates + manifesto | **PASS** | §14.8 | `sso_enabled/auto_update: false` |
| G14 — Recuperação | Restaurar estado anterior | `target-before` = snapshot de rollback | **PASS** | §14.2 | Operacional; nativo do Beam bloqueado |
| G15 — Logs | Sem token/senha/dado privado | Inspeção de saída | **PASS** | §14.9 | Só caminho relativo/hash/loopback |

Resultados permitidos: `PASS`, `FAIL`, `NÃO EXECUTADO`, `BLOQUEADO`,
`NÃO APLICÁVEL`. Nenhum teste bloqueado foi registrado como aprovado.

## 14. Evidências

Caminhos pessoais redigidos como `<DIR_TEMPORARIO>`. Todos os comandos foram
executados neste ambiente.

### 14.1 G1 — Determinismo

```text
lab-a árvore: 3fa08fc8…c8c2
lab-b árvore: 3fa08fc8…c8c2
G1: PASS (determinístico)
CWD externo: PASS
```

### 14.2 `--root` (G2, G3, G5, G6, G14)

```text
Lab: OK (<DIR_TEMPORARIO>/lab)
  [PASS] formato-conceitual
  [PASS] manifesto-estrutura-e-seguranca
  [PASS] payload-integridade-sha256
  [PASS] estados-before-after-conferem
  [PASS] simulador-atinge-target-after
  [PASS] simulador-idempotente
```

### 14.3 G4 — Download loopback

```text
servidor: http://127.0.0.1:<PORTA_DINAMICA> (loopback)
baixado data/welcome.txt                 sha256_ok=True
baixado config/faithro-settings.json     sha256_ok=True
baixado data/version.txt                 sha256_ok=True
G4: PASS
servidor encerrado
```

### 14.4 G7 — Hash incompatível

```text
payload corrompido: <DIR_TEMPORARIO>/lab-corrupt/server/files/data/welcome.txt
Validação: FAIL
  - SHA-256 do payload não confere: data/welcome.txt
exit=1
G7: PASS (integridade rejeitada; alvo não modificado)
```

### 14.5 G8/G10 — Malformado e sobreposição

```text
Self-test: OK (21 casos negativos rejeitados)
# inclui: JSON inválido, size ausente/negativo, sha256 inválido, op desconhecido,
# actions ausente, ação duplicada, overlap create/remove, algoritmo fraco,
# sso/auto-update, comando pós-patch, extensão .exe/.zip, URL http/https externa.
```

### 14.6 G9 — Path traversal

```text
Validação: FAIL
  - componente '..' (traversal) não permitido: ../outside/must-not-change.txt
exit=1 | canário igual? sim
G9: PASS
```

### 14.7 G11 — Interrupção

```text
criado parcial: welcome.txt.part
target-after contém .part? False
parcial removido com segurança; alvo não corrompido
G11: PASS
```

### 14.8 G12/G13 — Execução/SSO

```text
post_patch_command: None
sso_enabled: False
auto_update: False
G12/G13: PASS
```

### 14.9 G15 — Logs

Saída do validador contém apenas caminho relativo e divergência de integridade;
o servidor loopback registra apenas `127.0.0.1` e a linha de requisição. Nenhum
token, senha, `Authorization`, `Bearer`, hostname/IP privado ou conteúdo completo
de arquivo desnecessário é emitido. Observação: o `stdout` do gerador ecoa o
diretório de saída escolhido pelo operador (temporário e local, não versionado).

## 15. Resultados

- Fluxo conceitual completo exercitado: manifesto → loopback → download →
  integridade → aplicação (simulador) → estado final.
- Determinismo e independência de CWD confirmados.
- Todos os testes negativos de segurança rejeitados (traversal, malformado, hash
  incompatível, overlap, execução arbitrária, SSO/auto-update, URL externa,
  extensões proibidas).
- Integridade por SHA-256 é o controle primário e efetivo.

## 16. Testes não executados

- G5b (aplicação pelo Beam) e G11b (atomicidade dinâmica do Beam): dependem do
  binário do Beam.

## 17. Bloqueios

```text
TESTE DINÂMICO DO BEAM — BLOQUEADO
Causa: toolchain Rust/Cargo ausente (rustc/cargo não instalados) e a etapa
proíbe instalar Rust/Node/Tauri/Build Tools. Sem build, o binário do Beam não
pode ser produzido nem executado com origem verificável nesta etapa.
```

Consequência: a classificação não pode ser "homologação dinâmica completa".

## 18. Segurança

- **Traversal:** `check_safe_relpath` rejeita vazio, `\x00`, barra invertida,
  `/` inicial, `//` (UNC), drive `[A-Za-z]:`, `..` e componente vazio.
- **Integridade:** SHA-256 e tamanho verificados antes de qualquer escrita.
- **Escrita:** apenas dentro do alvo temporário; escrita atômica via `.part` +
  `os.replace`; canário externo verificado intacto.
- **Execução:** sem comando pós-patch, sem shell, sem lançamento de executável.
- **Rede:** somente loopback; URLs externas (http e https) rejeitadas no lab.
- **Privilégio:** nada executado como administrador; TLS/antivírus não tocados.
- **SSO/self-update:** desabilitados em templates e no manifesto.

## 19. Licenciamento

Beam Patcher: MIT OR Apache-2.0 (permissiva; ver docs/17 e
`client/licenses/README.md`). Todo o conteúdo do laboratório é próprio do
FaithRO; nenhum asset de terceiros foi versionado ou redistribuído.

## 20. Limitações

- Fluxo provado é **conceitual**; não é o formato binário nem o executor do Beam.
- Sem confirmação do formato `.beam` a partir do fonte (sem toolchain).
- O simulador não substitui o comportamento real do Beam (downloader, GRF,
  Tauri/WebView).

## 21. Riscos residuais

- Auditoria integral do fonte do Beam e do parsing de patchlist ainda pendente
  (herdado de docs/17).
- Comportamento do Beam no Windows Defender e code signing não avaliados.
- Maturidade do projeto Beam (v1.0 recente) exige acompanhamento.

## 22. Critério de aprovação

Enquadra-se em **APROVADO COM RESTRIÇÕES**: o laboratório e as validações próprias
passam; nenhum problema de segurança no conteúdo próprio; o Beam não pôde ser
executado por ausência de toolchain (bloqueio legítimo), e as limitações estão
registradas. Não se enquadra em "APROVADO PARA PRÓXIMO PROTÓTIPO" porque este
exige execução dinâmica do Beam com origem verificada.

## 23. Próxima etapa

```text
ETAPA 2O-D1 — Preparar ambiente controlado para build e execução auditável do
Beam Patcher (toolchain Rust fixada, build em pasta temporária fora do repo,
confirmação do formato .beam e execução loopback sem privilégios).
```

## 24. Rollback

- Etapa Git: reverter o commit desta branch via `git revert` em novo commit na
  própria branch, ou fechar o PR sem merge. `dev` não é alterada.
- Laboratório: é sempre temporário e descartável (`rm -rf <DIR_TEMPORARIO>`);
  encerrar o servidor HTTP ao final. Nenhum componente foi implantado; a VPS não
  foi acessada.

## 25. Referências

- [17-decisao-patcher-launcher.md](17-decisao-patcher-launcher.md) — seleção do
  patcher (Beam principal, RPatchur reserva).
- [`client/patcher/fixtures/synthetic/README.md`](../client/patcher/fixtures/synthetic/README.md)
  — estrutura e comandos do laboratório.
- [`client/patcher/lab/README.md`](../client/patcher/lab/README.md) — execução.
- [16-politica-distribuicao-cliente.md](16-politica-distribuicao-cliente.md) —
  o que pode/não pode ser distribuído.
- `scripts/generate-synthetic-patch-lab.py`, `scripts/validate-synthetic-patch-lab.py`.
