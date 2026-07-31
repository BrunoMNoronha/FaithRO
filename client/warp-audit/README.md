# `client/warp-audit/` — auditoria estática do WARP (ETAPA 2P-D)

> Esta pasta contém **apenas artefatos textuais** da auditoria estática do WARP
> (manifesto, achados de segurança, seleção de patches e seus schemas). **Nenhum**
> arquivo do WARP, do `Ragexe`, GRF, DLL, `.asi` ou asset proprietário é — ou pode
> ser — versionado aqui. O código-fonte do WARP **não** é copiado para o FaithRO.

## Contexto

A decisão de ferramenta ([docs/28](../../docs/28-decisao-ferramenta-preparacao-cliente.md))
aprovou o **WARP com restrições** e transferiu para a ETAPA 2P-D a auditoria
estática aprofundada do commit fixado. Esta pasta é o resultado versionado dessa
auditoria. O relatório completo está em
[docs/30-auditoria-estatica-warp.md](../../docs/30-auditoria-estatica-warp.md).

- **Origem oficial:** `https://github.com/Neo-Mind/WARP.git` (sem mirror).
- **Branch:** `rock_win32`.
- **Commit fixado:** `9b1173e9e4e135c68e150704f01186ab5e763acd`.
- **Licença:** GNU GPL v3.

## Arquivos

| Arquivo | Conteúdo |
| --- | --- |
| [`upstream-manifest.example.json`](upstream-manifest.example.json) | Origem, integridade (tree digest, SHA-256 de arquivos críticos), inventário, binários rastreados, submódulos, toolchain. |
| [`security-findings.example.json`](security-findings.example.json) | Achados W1–W10 (severidade, evidência, impacto, mitigação, pendência humana). |
| [`patch-selection.example.json`](patch-selection.example.json) | Patches candidatos mínimos, sensíveis e rejeitados; flags de autorização. |
| [`schemas/`](schemas/) | JSON Schemas (draft-07) dos três artefatos. |

## Garantias desta etapa

O WARP **não** foi compilado nem executado. **Nenhum** executável do cliente foi
copiado ou modificado. **Nenhum** asset proprietário foi manipulado. As flags nos
artefatos permanecem:

```text
source_executed=false  source_built=false  binary_created=false  client_modified=false
execution_allowed=false  final_selection_allowed=false  human_authorization_required=true
```

## Principais achados (resumo)

- **W1 (ALTO):** o commit fixado em `rock_win32` **não** contém fonte C++/Qt nem
  receita de build; o núcleo é distribuído **apenas** como binário prebuilt em
  `win32/`. "Compilar do fonte" não é satisfeito por esta branch.
- **W2/W3 (ALTO):** patches sensíveis presentes (`CustomDLL` injeta DLL arbitrária;
  `DisableProtect`, `DisableEncr`, `EnableProxy`). Nenhum é necessário ao primeiro
  acesso; todos exigem decisão separada.
- **W8 (INFORMATIVO):** nenhuma superfície de rede, auto-update ou telemetria foi
  encontrada no conjunto de **scripts** inspecionado (o binário do núcleo não foi
  auditado estaticamente).

## Validação

O script [`scripts/validate-warp-audit.py`](../../scripts/validate-warp-audit.py)
valida os três JSONs contra os schemas e contra regras de segurança (SHA de 40/64
caracteres, flags de build/execução/modificação proibidas em `true`, ausência de
IP, senha, token e caminho pessoal). Usa **apenas a biblioteca padrão** do Python
e não acessa a rede.

## Propriedade intelectual

WARP é **GPL-3.0** (uso apenas local; binário não versionado no FaithRO). `Ragexe`,
GRF, DLLs e assets da Gravity são **proprietários** — proibido versionar, hospedar,
empacotar ou compartilhar (ver [docs/16](../../docs/16-politica-distribuicao-cliente.md)).

## Referências

- [docs/28](../../docs/28-decisao-ferramenta-preparacao-cliente.md) — decisão da ferramenta.
- [docs/29](../../docs/29-compatibilidade-cliente-2021-11-05-packetver.md) — compatibilidade do cliente.
- [docs/30](../../docs/30-auditoria-estatica-warp.md) — relatório desta auditoria.
- [docs/16](../../docs/16-politica-distribuicao-cliente.md) — política de distribuição.
