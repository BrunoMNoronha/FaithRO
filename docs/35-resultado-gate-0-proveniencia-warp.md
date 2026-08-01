# Resultado do GATE 0 — reconfirmação de proveniência do WARP

> **Estado atual:** `GATE 0 CONCLUÍDO — APROVADO POR METADADOS` (ETAPA 2P-E-C0-B).
> **Data da execução:** 2026-08-01.
> **Escopo:** execução **exclusiva** do GATE 0 por **metadados públicos e oficiais**.
> **Nenhum** conteúdo de blob foi acessado; **nenhum** binário foi baixado,
> materializado, hasheado, inspecionado ou executado; **nenhuma** sandbox foi
> criada. A aprovação por metadados **não** significa confiança, segurança ou
> aprovação do binário e **não** autoriza o GATE 1.
> Continua [34](34-registro-autorizacao-gate-0-proveniencia-warp.md); observa
> [30](30-auditoria-estatica-warp.md), [31](31-decisao-caminho-nucleo-warp.md),
> [33](33-plano-auditoria-binaria-offline-warp.md) e
> [16](16-politica-distribuicao-cliente.md).

## 1. Objetivo

Executar exclusivamente o `GATE 0 — PROVENANCE_RECONFIRMATION` do plano da auditoria
binária offline, reconfirmando a proveniência do prebuilt do WARP **somente por
metadados oficiais**.

## 2. Autorização de origem

Registro de autorização
[`binary-audit-gate-00-decision-record-2026-07-31.json`](../client/warp-audit/decisions/binary-audit-gate-00-decision-record-2026-07-31.json)
(ETAPA 2P-E-C0-A): `APPROVE_GATE_0`, `provenance_reconfirmation_authorized=true`;
todas as demais autorizações `false`.

## 3. Escopo executado

Reconfirmação por metadados de: identidade do repositório; existência do commit
fixado; objeto/árvore; caminho do prebuilt; tipo, object ID e tamanho do blob;
refs/tags/releases; licença; e consistência entre o upstream e os registros do
FaithRO.

## 4. Métodos utilizados

GitHub GraphQL (campos selecionados) e GitHub REST Git Database API (commit e
árvore) e REST de refs — **somente metadados**. Fonte: `github.com`.

## 5. Métodos não utilizados

`git ls-remote` (não foi necessário); nenhum clone, fetch/pull do upstream, archive,
release asset, endpoint de blob (`git/blobs`), endpoint de contents, `download_url`,
`raw.githubusercontent.com` ou `codeload.github.com`; nenhum `curl`/`wget`/download.

## 6. Data e operador

2026-08-01; execução pelo agente FaithRO (Claude Code) sob autorização humana de
`BrunoMNoronha`.

## 7. Repositório esperado e observado

Esperado `Neo-Mind/WARP`; observado `Neo-Mind/WARP` (PUBLIC, não fork, não
arquivado, branch padrão `rock_win32`). **Consistente.**

## 8. Commit esperado e observado

Esperado `9b1173e9e4e135c68e150704f01186ab5e763acd`; observado idêntico; objeto do
tipo `commit` (merge, 2 parents); datas 2026-05-07. **Consistente.**

## 9. Árvore

`tree_oid = 1aebae06d5c71a145afc35cc72fcf5c210a08758` (coincide com o registro de
[docs/30](30-auditoria-estatica-warp.md)); resposta **não truncada**.

## 10. Caminho do artefato

Esperado `win32/WARP.exe`; encontrado `win32/WARP.exe`, exatamente **uma**
correspondência canônica, do tipo `blob`. **Consistente.**

## 11. Git blob object ID

`c853da42d18dfe090b4e941b435d989311faf3dc`.

> **Importante:** este é o **identificador do objeto Git informado pelo upstream**;
> **não** é um SHA-256 calculado localmente sobre o binário. O conteúdo do blob
> **não** foi acessado (`blob_content_accessed=false`, `binary_sha256=null`,
> `binary_sha256_computed=false`).

## 12. Tamanho informado por metadados

`1.137.152 bytes` (coincide com o registro interno). Obtido do metadado da árvore,
sem acessar o conteúdo.

## 13. Refs

10 heads observadas (`base`, `deb32`, `deb64`, `docs`, `gh-pages`, `rock`,
`rock_deb32`, `rock_deb64`, `rock_win32`, `win32`); o commit fixado é a **cabeça** de
`rock_win32` (1 ref direta). A ancestralidade por outras branches **não** foi
estabelecida pelo GATE 0 (`not_established_by_gate_0`).

## 14. Tags

`0` tags observadas.

## 15. Releases

`0` releases observadas. Nenhuma URL de asset foi selecionada, registrada ou
seguida.

## 16. Licença

`GNU General Public License v3.0` (`GPL-3.0`), declarada nos metadados. Consistente
com os registros internos. Não é parecer jurídico.

## 17. Matriz esperado × observado

| Campo | Esperado | Observado | Resultado |
| --- | --- | --- | :-: |
| repository_full_name | Neo-Mind/WARP | Neo-Mind/WARP | MATCH |
| commit_oid | 9b1173e9… | 9b1173e9… | MATCH |
| tree_oid | 1aebae06… | 1aebae06… | MATCH |
| artifact_path | win32/WARP.exe | win32/WARP.exe | MATCH |
| artifact_object_type | blob | blob | MATCH |
| artifact_blob_oid | c853da42… | c853da42… | MATCH |
| artifact_blob_size | 1137152 | 1137152 | MATCH |
| license | GPL-3.0 | GPL-3.0 | MATCH |
| direct_refs | rock_win32 (head) | rock_win32 (1 head) | MATCH |
| tags | 0 | 0 | MATCH |
| releases | 0 | 0 | MATCH |

Detalhes normalizados em
[`binary-audit-gate-00-provenance-evidence-2026-08-01.json`](../client/warp-audit/evidence/binary-audit-gate-00-provenance-evidence-2026-08-01.json).

## 18. Limitações

- A **ancestralidade** do commit não foi estabelecida pelo GATE 0 (para não ampliar
  o escopo).
- `0 tags`/`0 releases`: não há hash publicado nem assinatura em release — já constava
  da cadeia documental; não contradiz o esperado.
- O `git_blob_oid` **não** é um SHA-256 local do binário (conteúdo não acessado).
- Retrato pontual de 2026-08-01; **não** prova integridade nem segurança do binário.

## 19. Achados

Repositório, commit, árvore, caminho, tipo de objeto, blob OID e tamanho **coincidem**
com os registros internos; o commit é a cabeça de `rock_win32`; licença GPL-3.0
consistente.

## 20. Resultado

```text
COMPLETED_PASS
```

Significa **apenas**:

```text
A proveniência declarada é consistente com os metadados oficiais observados.
```

**Não** significa confiança no binário, segurança do binário, autorização para
download, materialização ou execução.

## 21. Critérios de interrupção

Nenhum critério de interrupção foi acionado: não houve divergência, commit ausente,
objeto incompatível, árvore inacessível, caminho ausente, correspondência múltipla,
resposta com conteúdo, redirect de download nem necessidade de ampliar o escopo.

## 22. Segurança

Execução **somente metadados** (`network_scope=GITHUB_OFFICIAL_ONLY`). Nenhum
endpoint de blob/contents, nenhuma URL direta, nenhum download. Respostas brutas
**não** foram versionadas; apenas campos normalizados foram registrados. Nenhum
token, IP, chave ou caminho pessoal registrado.

## 23. Propriedade intelectual

WARP é GPL-3.0 (uso local; binário **não** versionado). `Ragexe`, GRF, DLLs e assets
Gravity são proprietários (ver [16](16-politica-distribuicao-cliente.md)). Nenhum
conteúdo binário foi acessado.

## 24. Confirmação de ausência de materialização

`binary_materialized=false`, `blob_content_accessed=false`,
`binary_sha256_computed=false`, `binary_sha256=null`. Nenhum binário foi baixado,
materializado ou hasheado.

## 25. Autorizações ainda falsas

`gate_1_authorized`, `materialization_authorized`, `hashing_authorized`,
`static_inspection_authorized`, `sandbox_creation_authorized`,
`execution_without_client_authorized`, `client_copy_provision_authorized`,
`patch_application_authorized`, `first_login_authorized`, `distribution_authorized`
e as demais permanecem **`false`**. A execução do GATE 0 **não** altera nenhuma
autorização.

## 26. Riscos

R1 metadado tratado como conteúdo confiável; R2 endpoint retornar conteúdo; R3 URL de
asset; R4 resultado positivo autorizar GATE 1; R5 árvore truncada; R6 evidência não
reproduzível; R7 resposta bruta com segredo. Mitigações: separação Git object ID ×
hash local, classes de endpoint fechadas, sem URLs de asset, GATE 1 `false` com nova
decisão humana obrigatória, verificação de `truncated`, query log abstrato e não
versionar respostas brutas.

## 27. Rollback

Antes do merge: corrigir por novo commit; manter draft; fechar o PR; sem force; sem
reescrever `dev`. Após integração: branch de `dev`, reverter o squash, validar, abrir
PR de reversão. O revert **não** apaga o fato de que consultas públicas de metadados
ocorreram, **não** autoriza o GATE 1 e **não** substitui decisão humana.

## 28. Estado atual

```text
GATE 0 CONCLUÍDO — APROVADO POR METADADOS
```

## 29. Próxima decisão humana

Somente após revisão e integração deste resultado
(`ETAPA 2P-E-C0-B-R`), poderá ser solicitada uma nova decisão humana entre:

```text
AUTHORIZE_GATE_1
REPEAT_GATE_0
STOP_PATH
```

Nenhuma dessas opções está selecionada. Um `COMPLETED_PASS` **não** seleciona
`AUTHORIZE_GATE_1` automaticamente.

## Estado de verificação

- **Fato:** metadados oficiais observados coincidem com os registros internos
  (repo, commit, árvore, caminho, blob OID, tamanho, licença); commit na cabeça de
  `rock_win32`; 0 tags/releases.
- **Inferência/decisão:** `COMPLETED_PASS` — proveniência declarada consistente com
  os metadados; **não** é juízo sobre a segurança do binário.
- **Pendência:** revisão/integração (2P-E-C0-B-R) e, depois, decisão humana entre
  `AUTHORIZE_GATE_1` / `REPEAT_GATE_0` / `STOP_PATH`.
- **Nota:** decisão técnica e de conformidade do projeto, **não** parecer jurídico.
