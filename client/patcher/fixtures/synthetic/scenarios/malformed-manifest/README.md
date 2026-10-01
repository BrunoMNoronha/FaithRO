# Cenário `malformed-manifest/`

Prova que um manifesto malformado ou perigoso é rejeitado **antes** de qualquer
aplicação. Os manifestos inválidos são gerados em memória por `--self-test`.

## Cobre

- **G8 — Manifesto malformado:** JSON inválido, campo obrigatório ausente
  (`size`/`actions`), `sha256` com formato inválido, `size` negativo, `op`
  desconhecido.
- **G10 — Sobreposição de ações:** o mesmo caminho em create/update **e** remove
  é rejeitado; ação duplicada para o mesmo caminho é rejeitada.
- Rejeições de segurança adicionais cobertas pela mesma bateria: algoritmo fraco
  (`md5`/`sha1`) como fonte primária, `sso_enabled: true`, `auto_update: true`,
  `post_patch_command`, extensão executável (`.exe`) e compactada (`.zip`),
  URL HTTP externa e URL HTTPS externa em laboratório loopback.

## Como executar

```bash
python scripts/validate-synthetic-patch-lab.py --self-test
```

Cada caso deve falhar e retornar código diferente de zero, sem tocar nas fixtures
canônicas versionadas.
