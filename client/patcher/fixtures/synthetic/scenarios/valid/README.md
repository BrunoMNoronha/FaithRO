# Cenário `valid/`

Caminho feliz do laboratório. Prova geração determinística, integridade e
aplicação conceitual.

## Cobre

- **G1 — Geração determinística:** duas gerações produzem manifestos e hashes
  idênticos.
- **G3 — Manifesto válido:** todos os SHA-256 do manifesto conferem com o payload.
- **G4 — Download em loopback:** payload servido por `127.0.0.1` e baixado; o
  hash do download confere.
- **G5 — Aplicação válida:** aplicada pelo **simulador do laboratório** (não pelo
  Beam); o estado final iguala `target-after`. A aplicação pelo próprio Beam está
  `BLOQUEADO — TOOLCHAIN DO BEAM NÃO DISPONÍVEL`.
- **G6 — Idempotência:** reaplicar não corrompe nem duplica; estado final estável.

## Como executar

```bash
python scripts/generate-synthetic-patch-lab.py --output /tmp/lab
python scripts/validate-synthetic-patch-lab.py --root /tmp/lab
```

O modo `--root` executa geração de invariantes, integridade SHA-256, comparação
com `expected-state.json`, aplicação pelo simulador e reaplicação (idempotência).
