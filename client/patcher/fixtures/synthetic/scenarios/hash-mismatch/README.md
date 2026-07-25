# Cenário `hash-mismatch/`

Prova que a integridade por SHA-256 é o controle primário e que um payload
adulterado é rejeitado **antes** de modificar o alvo.

## Cobre

- **G7 — Hash incompatível:** altera 1 byte de um arquivo em `server/files/` sem
  atualizar o manifesto. A validação `--root` falha com "SHA-256 do payload não
  confere", retorna código diferente de zero e o alvo sintético não é modificado.

## Como executar

```bash
python scripts/generate-synthetic-patch-lab.py --output /tmp/lab
# corromper 1 byte do payload servido:
python - <<'PY'
p = "/tmp/lab/server/files/data/welcome.txt"
b = bytearray(open(p, "rb").read()); b[0] ^= 1; open(p, "wb").write(b)
PY
python scripts/validate-synthetic-patch-lab.py --root /tmp/lab   # deve FALHAR
```

O erro não expõe conteúdo sensível: informa apenas o caminho relativo e a
divergência de integridade.
