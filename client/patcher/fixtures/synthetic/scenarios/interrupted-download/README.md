# Cenário `interrupted-download/`

Prova que uma transferência interrompida não é confundida com um arquivo final.

## Cobre

- **G11 — Interrupção de download:** um arquivo parcial (`.part`) permanece
  identificável e **não** é tratado como conteúdo final; o estado `target-after`
  nunca contém `.part`; uma nova execução pode limpar ou substituir o parcial com
  segurança. O simulador do laboratório usa **escrita atômica**: grava em
  `<arquivo>.part` e só então faz `os.replace` para o destino, de modo que uma
  interrupção deixa um `.part` em vez de um destino corrompido.

## Limitação (Beam)

A **atomicidade dinâmica do próprio Beam** (comportamento real de retomada e
`.part` do downloader do Beam) está classificada como
`BLOQUEADO — TOOLCHAIN DO BEAM NÃO DISPONÍVEL`. Aqui provamos apenas o invariante
com o simulador; a documentação do Beam descreve escrita atômica, mas isso não foi
executado nesta etapa.

## Como executar

```bash
python scripts/generate-synthetic-patch-lab.py --output /tmp/lab
# criar um parcial órfão e confirmar que target-after não o contém:
python - <<'PY'
import os
open("/tmp/lab/target-before/data/welcome.txt.part", "wb").write(b"parcial")
print("after tem .part?", os.path.exists("/tmp/lab/target-after/data/welcome.txt.part"))
PY
```
