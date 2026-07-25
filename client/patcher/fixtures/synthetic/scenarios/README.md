# Cenários do laboratório sintético (G1–G15)

Cada subpasta documenta um cenário. Os manifestos **inválidos** (traversal,
malformado, hash incompatível) **não são versionados** como arquivos: eles são
gerados em memória, em diretórios temporários, por
`scripts/validate-synthetic-patch-lab.py --self-test`. Assim o repositório nunca
guarda um manifesto inseguro, e o validador de configuração
(`scripts/validate-patcher-config.py`) — que rejeita `..`/caminhos absolutos —
permanece verde.

## Mapa cenário → teste → como é executado

| Cenário | Testes | Como é executado | Onde |
| --- | --- | --- | --- |
| [`valid/`](valid/README.md) | G1, G3, G4, G5, G6 | gerar + validar `--root` + servidor loopback | script |
| [`hash-mismatch/`](hash-mismatch/README.md) | G7 | corromper 1 byte do payload e validar `--root` | script |
| [`traversal/`](traversal/README.md) | G9, G10 | manifesto com `..`/absoluto/UNC + `--self-test` | script |
| [`malformed-manifest/`](malformed-manifest/README.md) | G8, G10 | JSON inválido/campo ausente/overlap + `--self-test` | script |
| [`interrupted-download/`](interrupted-download/README.md) | G11 | payload parcial `.part` não vira final | script |

## Testes dependentes do Beam

G5 (aplicação pelo Beam), G14 (rollback nativo do Beam) e a atomicidade dinâmica
de G11 dependem do binário do Beam e estão classificados como
`BLOQUEADO — TOOLCHAIN DO BEAM NÃO DISPONÍVEL`. O simulador do laboratório prova
apenas as fixtures e os invariantes, nunca o Beam.
