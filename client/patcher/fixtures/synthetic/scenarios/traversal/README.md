# Cenário `traversal/`

Prova que nenhum caminho pode escapar do diretório-alvo. O manifesto malicioso
**não é versionado**; é gerado em memória por `--self-test`.

## Cobre

- **G9 — Path traversal:** manifestos com `../fora.txt`, `..\fora.txt`, caminho
  absoluto Unix (`/data/x`), absoluto Windows (`C:/…`), UNC (`//host/share/…`),
  caminho vazio, NUL e barra invertida ambígua são **todos rejeitados**. Um
  canário fora do alvo permanece intacto (verificado por hash).
- **G10 — Subdiretórios válidos:** caminhos como `data/sub/arquivo.txt` são
  aceitos e permanecem dentro do alvo (a rejeição vale só para escape).

## Como executar

```bash
python scripts/validate-synthetic-patch-lab.py --self-test   # inclui os casos de traversal
```

Regras aplicadas em `check_safe_relpath`: rejeita string vazia, `\x00`,
barra invertida, `/` inicial, `//` (UNC), `[A-Za-z]:` (drive), componente `..`
e componente vazio.
