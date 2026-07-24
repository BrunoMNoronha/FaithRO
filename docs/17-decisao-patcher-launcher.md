# Decisão de patcher/launcher do FaithRO (protótipo local)

> **Escopo:** documento de decisão técnica e planejamento. **Não** altera código
> do rAthena, banco ou configuração operacional. **Não** monta o cliente final,
> **não** cria o `faithro.grf` real, **não** executa o cliente Ragnarok e **não**
> implanta patch server público. A homologação aqui registrada é
> **APROVADO PARA PROTÓTIPO LOCAL CONTROLADO** — não é homologação para produção.
> Complementa [15-cliente-primeiro-acesso.md](15-cliente-primeiro-acesso.md) e
> [16-politica-distribuicao-cliente.md](16-politica-distribuicao-cliente.md).

## 1. Objetivo

Selecionar, com base em evidência de fontes primárias, a estratégia de
patcher/launcher mais adequada ao FaithRO para atualizar **apenas conteúdo
próprio/licenciado** do cliente (o `faithro.grf` futuro), sem redistribuir
qualquer arquivo proprietário da Gravity ou de terceiros. A seleção precede a
implementação: nenhuma infraestrutura de patch é criada nesta etapa.

## 2. Contexto

- Baseline do cliente: `PACKETVER=20211103`, cliente-alvo `2021-11-03_Ragexe`,
  família `Ragexe` (ver [09](09-cliente-baseline-protocolo.md)).
- O FaithRO **não** distribui o cliente-base, o executável, `data.grf` ou
  `rdata.grf` (ver [16](16-politica-distribuicao-cliente.md)).
- O patcher só deve tocar arquivos **próprios/licenciados** do FaithRO, nunca o
  executável ou os GRFs oficiais.
- Nenhum patcher havia sido selecionado antes desta decisão. Não há issue ou ADR
  prévia específica de patcher (issues abertas verificadas em 2026-07-24; a mais
  próxima é a #14 "Criar guia de instalação local", que não decide patcher).

## 3. Alternativas avaliadas

Cinco alternativas obrigatórias, mais o descarte explícito de fontes não
confiáveis (anexos de fórum, mirrors duvidosos, pacotes pagos/fechados vinculados
a hardware — nenhum considerado).

| # | Alternativa | Autor | Tipo | Licença | Última versão | Última atividade |
| - | --- | --- | --- | --- | --- | --- |
| 1 | **Beam Patcher** (`beamguides/beam-patcher`) | Beam Patcher Team | Open source (Rust/Tauri) | **MIT OR Apache-2.0** | v1.0.1 (2026-01-18) | commit `feed978870` (2026-06-06) |
| 2 | **Elurair** (`elurair.com`) | Ai4rei/AN | Fechado (binário) | **CC BY-NC 4.0** | v2.21.4.614 (2026-07-08) | Ativo |
| 3 | **RO Patcher Lite** (`nn.ai4rei.net/dev/rsu/`) | Ai4rei/AN | Fechado (binário) | **CC BY-NC-ND 4.0** | v4.11.0.1395 (2026-07-11) | Ativo |
| 4 | **RPatchur** (`L1nkZ/rpatchur`) | L1nkZ | Open source (Rust) | **MIT OR Apache-2.0** | v0.3.0 (2021-05-07) | commit `21a5482771` (2023-01-29) |
| 5 | **Thor Patcher** (`patcherproj` no SourceForge) | Aeomin | Open source (declarado) | Não declarada claramente | v3.0 alpha 2 | Última atualização 2016-06-29 |

> Todas as datas/versões acima foram consultadas em **2026-07-24** nas fontes
> primárias (§4). Datas de commit/release do GitHub via API oficial; versões de
> ferramentas fechadas via página oficial do autor. Nenhum valor foi inventado.

## 4. Fontes

Hierarquia conforme [10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md):
repositório/página oficial → arquivos de licença → releases → documentação do
autor → fórum. Consulta em **2026-07-24**.

| Alternativa | Fonte primária | Evidência de licença | Confiança |
| --- | --- | --- | --- |
| Beam Patcher | `github.com/beamguides/beam-patcher` (API + clone read-only) | `LICENSE-MIT`, `LICENSE-APACHE`; `Cargo.toml` workspace: `license = "MIT OR Apache-2.0"` | Confirmado no código |
| Elurair | `elurair.com` (página oficial) | Rodapé CC BY-NC 4.0; nota "Do not provide mirrors… Do not hot-link" | Oficial (autor) |
| RO Patcher Lite | `nn.ai4rei.net/dev/rsu/` (página oficial) | CC BY-NC-ND 4.0; "Mirror Application Form" + nota anti-mirror | Oficial (autor) |
| RPatchur | `github.com/L1nkZ/rpatchur` (API) + `l1nkz.github.io/rpatchur` (docs) | `LICENSE-MIT`, `LICENSE-APACHE` | Confirmado no código |
| Thor Patcher | `sourceforge.net/projects/patcherproj` + wiki rAthena | Categoria "Open Source" sem SPDX explícito na página | Comunidade — requer validação |

> Observação: a licença exibida no cabeçalho do GitHub não foi tratada como
> suficiente; para Beam e RPatchur a confirmação veio dos arquivos `LICENSE-*` e
> do `Cargo.toml`. "Grátis" (Elurair/RO Patcher Lite/Thor) **não** foi
> interpretado como "redistribuição permitida".

## 5. Matriz ponderada

Notas de 0 a 5 por critério; `pontuação = Σ((nota/5) × peso)`. As duas
alternativas fechadas do Ai4rei e o Thor não recebem pontuação completa por serem
barradas em critério eliminatório (§6); a matriz compara as duas permissivas
efetivamente selecionáveis.

| Critério (peso) | Beam | RPatchur |
| --- | :-: | :-: |
| Licença e permissão de distribuição (20) | 5 | 5 |
| Segurança do processo de atualização (20) | 4 | 3 |
| Manutenção e atividade do projeto (15) | 5 | 2 |
| Integridade, atomicidade e recuperação (15) | 4 | 3 |
| Facilidade de configuração e operação (10) | 4 | 4 |
| Compatibilidade Windows 10/11 (5) | 5 | 5 |
| HTTPS e infraestrutura de patch (5) | 5 | 4 |
| Customização visual e identidade FaithRO (5) | 5 | 4 |
| Documentação e suporte comunitário (3) | 3 | 4 |
| Custo de manutenção futura (2) | 4 | 3 |
| **Pontuação ponderada** | **≈ 89,4** | **≈ 71,6** |

Justificativa das notas mais sensíveis:

- **Manutenção:** Beam com release em 2026-01 e commits até 2026-06; RPatchur com
  última release em 2021 e último commit (dependabot) em 2023 → risco de
  abandono e dependências antigas.
- **Segurança/integridade/atomicidade:** evidências de código para Beam em §7;
  RPatchur documenta `check_integrity` para THOR, mas atomicidade/retomada/rollback
  não estão descritos na documentação pública consultada.
- **Documentação/comunidade:** RPatchur é mais provado e documentado
  (`l1nkz.github.io/rpatchur`, 56 stars); Beam é recente (14 stars, v1.0 em
  2025-12) → menor validação comunitária.

## 6. Critérios eliminatórios aplicados

| Alternativa | Resultado | Motivo |
| --- | --- | --- |
| Beam Patcher | **Não eliminada** | Licença permissiva; HTTPS; integridade por hash; TLS não desabilitado (§7). Ressalvas, não bloqueios. |
| RPatchur | **Não eliminada** | Licença permissiva; HTTP/HTTPS; integridade THOR. Ressalva de manutenção, não bloqueio eliminatório. |
| RO Patcher Lite | **BLOQUEADA POR LICENÇA** | CC BY-NC-**ND**: proíbe obras derivadas (customização/identidade) e o autor proíbe mirror/hotlink → o FaithRO não pode modificar nem hospedar. |
| Elurair | **NÃO RECOMENDADA** | CC BY-NC 4.0, **fechado** (não auditável em código) e o autor proíbe mirror/hotlink → aumenta dependência de software fechado e impede auditoria de segurança e self-host. |
| Thor Patcher | **BLOQUEADA POR MANUTENÇÃO** | Última atualização 2016; projeto dormente; licença não declarada de forma clara; formato `.thor` proprietário e histórico de dependência de HTTP. |

> Nenhuma alternativa foi selecionada por popularidade. A maior pontuação não
> supera bloqueio: mesmo que uma ferramenta fechada tivesse boa UX, o bloqueio de
> licença/segurança impede a seleção.

## 7. Auditoria de segurança (candidato principal — evidência de código)

Auditoria **estática read-only** do fonte do Beam Patcher, clonado para pasta
temporária **fora** do repositório (`<CAMINHO_TEMPORARIO_REDACTED>`), sem executar
build, scripts de instalação ou o binário. Referências de arquivo relativas ao
commit `feed978870`.

| Item | Resultado | Evidência |
| --- | --- | --- |
| Validação TLS | **Não desabilitada** | `reqwest` com feature `native-tls`; nenhuma ocorrência de `danger_accept_invalid_certs`/`accept_invalid_hostname` no código. |
| HTTP vs HTTPS | HTTPS por padrão nos exemplos; HTTP só recomendado para teste local | `config.example`: "All URLs should use HTTPS for security unless testing locally". |
| Integridade de patch | **Verifica MD5 antes de aplicar** (formato BEAM); erro aborta a aplicação | `beam-core/src/patcher.rs` (`verify_file` → `Err(PatchFailed)` se falhar); deps `sha2`, `md5`. |
| Escrita atômica / recuperação | **Confirmada** | `beam-core/src/downloader.rs`: "Atomic write: stream into a temp file, then rename. Interrupted downloads leave behind a `.part` file rather than a corrupt destination." |
| Aplicação de arquivos | **Centrada em GRF** (contida) | Patches `.beam/.thor/.rgz/.gpf` são aplicados via `grf.patch_file()` dentro do GRF-alvo, não extraídos para caminhos arbitrários do sistema de arquivos. |
| Execução de processos | Sem shell; apenas executáveis do config | `Command::new` só para `client_exe`, `setup_exe` e fluxo SSO; nenhum `sh -c`/`cmd /c`/interpolação de shell. |
| Comandos pós-patch arbitrários | **Não encontrados** | Não há execução de comando arbitrário vindo do servidor de patch. |
| Credenciais / SSO | SSO **opcional, desabilitado por padrão** | `config.sso.enabled: false`. Decisão FaithRO: manter desabilitado (ver §10). |
| Privilégio administrativo | Não exigido pelo design | Escreve em `game_directory`/pasta do executável; recomenda-se pasta com permissão de escrita (ver [15](15-cliente-primeiro-acesso.md)). |
| Self-update | Presente, `auto_update: false` recomendado | `updater.enabled`; atualização manual sob confirmação. |

**Ressalva de segurança (residual):** o caminho de destino do download é montado a
partir do nome do arquivo listado no `patchlist.txt` (controlado pelo servidor de
patch). Um `patchlist` malicioso poderia, em tese, conter nomes com `..`. Como o
patch server é do próprio FaithRO (confiável) e o validador desta etapa
(`scripts/validate-patcher-config.py`) rejeita `..`/caminhos absolutos nas
fixtures/manifestos, o risco é mitigado no lado da configuração; ainda assim, a
**auditoria completa do fonte e a validação do parsing do patchlist permanecem
pendentes** antes de qualquer uso real.

## 8. Testes realizados

- **Auditoria estática de licença e código:** executada (§4, §7).
- **Matriz ponderada:** produzida (§5).
- **Validador de configuração** (`scripts/validate-patcher-config.py`): criado e
  **executado localmente** contra os templates/fixtures (Python da biblioteca
  padrão, disponível no ambiente). Ver §7 do PR e a seção "Validações".
- **Testes dinâmicos G1–G15 (laboratório com o binário do patcher):**
  **NÃO EXECUTADOS** nesta etapa. Motivo: o Beam exige toolchain Rust 1.75+/Tauri
  para compilar e esta etapa **proíbe instalar Rust/Node/.NET/servidor web**;
  executar um binário de terceiros ainda não auditado integralmente também foi
  evitado. A estrutura de laboratório sintético e o plano de testes G1–G15 estão
  versionados em [`client/patcher/fixtures/`](../client/patcher/fixtures/) para
  execução em etapa futura, com ambiente próprio e sob as mesmas restrições de
  segurança.

## 9. Resultados

- Duas alternativas passam nos critérios eliminatórios: **Beam** e **RPatchur**
  (ambas MIT/Apache, self-host e fork permitidos).
- **Beam** vence a matriz ponderada (≈ 89,4 × ≈ 71,6), principalmente por
  manutenção ativa, integridade/atomicidade evidenciadas em código e HTTPS
  multi-mirror.
- As três alternativas restantes são rejeitadas por licença (RO Patcher Lite),
  por serem fechadas/não auditáveis com mirror proibido (Elurair) ou por
  manutenção/licença (Thor).

## 10. Decisão

### Candidato principal — **Beam Patcher**

- **Versão a fixar:** v1.0.1, commit `feed978870` (2026-06-06).
- **Licença:** MIT OR Apache-2.0 (permite redistribuição, modificação e
  self-host — compatível com identidade própria e patch server próprio).
- **Origem:** `https://github.com/beamguides/beam-patcher` (binário oficial via
  release ou compilação própria; **sem mirror de terceiros**).
- **Classificação:** **APROVADO PARA PROTÓTIPO LOCAL CONTROLADO**.
- **Justificativa:** melhor equilíbrio entre licença permissiva, segurança
  evidenciada em código, manutenção ativa e customização; reduz dependência de
  software fechado (Elurair/RO Patcher Lite) e abandonado (Thor).
- **Condições de uso / ressalvas:**
  - manter **SSO desabilitado** e **sem salvamento de senha**;
  - usar **HTTPS** em produção; `http://127.0.0.1` apenas em fixtures de
    laboratório;
  - fixar a versão e **auditar o fonte integralmente** (parsing de patchlist,
    traversal, superfície Tauri/WebView) antes de qualquer uso real;
  - não iniciar o cliente após patch incompleto;
  - projeto ainda **jovem** (v1.0 em 2025-12, baixa validação comunitária) →
    acompanhar releases e issues de segurança.

### Candidato reserva — **RPatchur**

- **Quando usar:** se a auditoria integral do Beam revelar bloqueio, se a
  juventude do projeto se mostrar arriscada, ou se for necessário um patcher mais
  provado a curto prazo.
- **Versão a fixar:** v0.3.0 / commit `21a5482771` (2023-01-29).
- **Riscos adicionais:** upstream estagnado (sem release desde 2021, sem commit
  desde 2023) e dependências antigas → exigiria **fork interno** e atualização de
  dependências antes de uso real; SSO presente (manter desabilitado).

### Não recomendados / rejeitados

| Alternativa | Motivo | Reavaliação futura |
| --- | --- | --- |
| RO Patcher Lite | BLOQUEADA POR LICENÇA (CC BY-NC-ND: sem derivadas, sem mirror) | Só se o autor licenciar de forma permissiva — improvável. |
| Elurair | NÃO RECOMENDADA (fechado, não auditável, mirror proibido) | Poderia ser apenas **linkado** à página oficial se um dia se optar por launcher de terceiros; não como patcher próprio. |
| Thor Patcher | BLOQUEADA POR MANUTENÇÃO (dormente desde 2016; licença não clara) | Só como referência histórica de formato `.thor`. |

### Escopo aprovado

```text
[x] Somente laboratório sintético
[x] Configuração de exemplo (templates com placeholders)
[x] Arquivos diretos (conceito)
[ ] GRF ainda não testado
[x] Launcher sintético (plano)
[x] Sem SSO
[x] Sem cliente real
[x] Sem produção
```

> **Não** é "homologado para produção". A classificação vigente é
> **APROVADO PARA PROTÓTIPO LOCAL CONTROLADO**.

## 11. Arquivos afetados

Criados/atualizados nesta decisão (documentação e exemplos textuais — nenhum
binário):

- `docs/17-decisao-patcher-launcher.md` (este documento);
- `client/patcher/README.md`;
- `client/patcher/templates/beam-config.prod.example.yml`;
- `client/patcher/templates/beam-config.lab.example.yml`;
- `client/patcher/fixtures/` (lab sintético + plano G1–G15 + manifesto/patchlist
  de exemplo);
- `client/licenses/README.md` (registro das ferramentas avaliadas);
- `scripts/validate-patcher-config.py` + `.github/workflows/validate-patcher-config.yml`;
- `.gitignore` (reforço de bloqueio de binários de patcher, se necessário);
- `docs/00-base-conhecimento.md` (índice).

## 12. Implantação futura (não nesta etapa)

1. Auditar integralmente o fonte do Beam na versão fixada; compilar internamente.
2. Definir o patch server **próprio** (HTTPS, sem mirror de terceiros).
3. Gerar o `faithro.grf` com conteúdo **apenas** próprio/licenciado.
4. Preencher os templates com host/porta/versão homologados (sem segredos).
5. Publicar `patchlist.txt` + `version.json` + checksums SHA-256.
6. Assinar o binário do patcher (code signing) — pendente.

## 13. Testes futuros

Executar o plano G1–G15 (ver [`client/patcher/fixtures/`](../client/patcher/fixtures/))
em laboratório com o binário compilado: atualização inicial, idempotência,
arquivo/patch corrompido, interrupção, arquivo bloqueado, falha de rede, 404,
**path traversal**, subdiretórios, espaços/Unicode, launcher sintético, segunda
instância, rollback e sanidade de logs. Depois: teste com `faithro.grf` real e,
por fim, teste com cliente real (fora do escopo atual).

## 14. Riscos

- **Segurança:** auditoria integral do Beam ainda pendente (parsing de patchlist,
  traversal, superfície Tauri/WebView); testes dinâmicos não executados.
- **Manutenção:** Beam é jovem; RPatchur (reserva) está estagnado.
- **Legal:** manter o patcher restrito a conteúdo próprio/licenciado; nunca
  empacotar assets da Gravity (ver [16](16-politica-distribuicao-cliente.md)).
- **Operacional:** patch server, CDN, HTTPS público, code signing e
  comportamento no Windows Defender ainda não definidos.

## 15. Rollback

Etapa documental/Git: o rollback é reverter o commit deste PR (via `git revert`
em novo PR). Nenhum componente foi implantado; nenhuma VPS foi acessada; nenhum
patch server público foi criado. O laboratório temporário fica fora do
repositório e pode ser excluído sem efeito no projeto.

## 16. Pendências

- Auditoria integral do fonte do Beam (versão fixada) e do parsing de patchlist.
- Execução dos testes dinâmicos G1–G15 com o binário compilado.
- Teste com `faithro.grf` real (ainda não criado).
- Definição de patch server HTTPS próprio, CDN e code signing.
- Teste em Windows limpo e verificação de comportamento no Windows Defender.
- Confirmação da licença do Thor (caso se queira reavaliar o formato `.thor`).
- Validação comunitária do Beam à medida que o projeto amadurece.

## Referências cruzadas

- [15-cliente-primeiro-acesso.md](15-cliente-primeiro-acesso.md) — fluxo de
  primeiro acesso (o patcher é o passo 4/6 daquele fluxo).
- [16-politica-distribuicao-cliente.md](16-politica-distribuicao-cliente.md) —
  o que pode ou não ser distribuído; classificação de componentes.
- [10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md) —
  hierarquia de fontes aplicada aqui.
- [`client/patcher/README.md`](../client/patcher/README.md) — estrutura,
  templates, fixtures e procedimento de promoção de laboratório.
</content>
