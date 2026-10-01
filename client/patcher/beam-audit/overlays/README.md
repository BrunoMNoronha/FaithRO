# `overlays/` — overlay de segurança de laboratório do Beam Patcher

> Contém **apenas** um patch textual de endurecimento de segurança para o
> **laboratório**, gerado contra o commit fixado do Beam
> (`feed97887090d121f796bc1b941390e28b7a2da5`). **Não** é fonte do Beam, **não**
> é binário e **não** deve ser aplicado no repositório FaithRO.

## `beam-lab-security.patch`

Gerado com `git diff` sobre uma **cópia temporária** do clone upstream (o clone
canônico usado como evidência permanece intacto). Alvo de aplicação: um clone
**temporário externo** do Beam, na D1-B, **antes** do primeiro build.

Mudanças (somente segurança de laboratório):

| Arquivo upstream | Mudança |
| ---------------- | ------- |
| `beam-ui/tauri.conf.json` | `updater.active=false`, endpoints vazios, `dialog=false` |
| `beam-ui/tauri.conf.json` | `http.all=false`, escopo HTTP restrito a loopback (remove `https://**`, curinga http e domínio externo) |
| `beam-ui/tauri.conf.json` | `shell.open=false` |
| `beam-ui/tauri.conf.json` | `dialog.open/save=false` |
| `beam-ui/tauri.conf.json` | CSP definida (deixa de ser `null`), `connect-src` só self/loopback/asset |
| `beam-ui/tauri.conf.json` | `bundle.active=false`, `targets=[]` (sem installer no primeiro build) |
| `beam-ui/Cargo.toml` | remove features `http-all`, `shell-open`, `updater` |
| `beam-ui/src/commands.rs` | bloqueia lançamento de cliente e de setup no laboratório |
| `beam-core/src/sso.rs` | bloqueia lançamento de jogo via SSO no laboratório |

## Aplicar (apenas na D1-B, em clone temporário externo)

```bash
# NÃO aplicar no FaithRO. Alvo: clone temporário do Beam no commit fixado.
git -C /tmp/beam apply --check client/patcher/beam-audit/overlays/beam-lab-security.patch
git -C /tmp/beam apply         client/patcher/beam-audit/overlays/beam-lab-security.patch
```

## Validar (offline, sem build)

```bash
python scripts/validate-beam-security-overlay.py \
  --source /tmp/beam \
  --patch client/patcher/beam-audit/overlays/beam-lab-security.patch
```

## Notas

- O patch preserva os finais de linha CRLF do upstream. O `.gitattributes` marca
  `*.patch` desta pasta como `-text` para o Git **não** reescrever seus bytes,
  garantindo que continue aplicável.
- O overlay endurece o **binário**; a restrição de endpoints/patchlist a loopback
  no laboratório é reforçada também pela config
  [`../../templates/beam-config.lab.example.yml`](../../templates/beam-config.lab.example.yml).
