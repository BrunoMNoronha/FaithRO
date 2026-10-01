# Laboratório sintético do patcher (ETAPA 2O-D)

> Conteúdo **100% sintético, textual e próprio** do FaithRO. Serve para exercitar
> o **fluxo conceitual** do Beam Patcher sem cliente real, sem `Ragexe`, sem
> `data.grf`/`rdata.grf`, sem BGM/sprite/mapa e sem qualquer asset da Gravity.
> Nenhum binário é versionado. Ver [`docs/18-homologacao-patch-sintetico-beam.md`](../../../../docs/18-homologacao-patch-sintetico-beam.md).

## Formato conceitual (importante)

O "patch" deste laboratório **não** é um pacote `.beam`/`.thor`/`.rgz`/`.gpf`
real. O formato binário oficial do Beam **não** foi confirmado a partir do fonte
fixado (a toolchain Rust/Tauri não está disponível neste ambiente — ver docs/18).
Por isso o patch é um **manifesto JSON conceitual** + arquivos de conteúdo
servidos por loopback, todos marcados com:

```text
FORMATO CONCEITUAL — NÃO CONSUMÍVEL PELO BEAM
```

É **proibido** renomear estes artefatos para extensões reais do Beam e afirmar
que o Beam os consumiu.

## Fluxo exercitado

```text
manifesto (server/manifest.json)
   ↓
servidor HTTP em 127.0.0.1 (loopback, porta dinâmica)
   ↓
download do payload (server/files/…)
   ↓
verificação de integridade (SHA-256, tamanho)
   ↓
aplicação em diretório sintético descartável (simulador do laboratório)
   ↓
validação do estado final (target-after)
```

> O executor de aplicação é o **simulador do laboratório** embutido em
> `scripts/validate-synthetic-patch-lab.py`. Ele **não é o Beam**. Onde o Beam
> apareceria, o teste dinâmico está classificado como
> `BLOQUEADO — TOOLCHAIN DO BEAM NÃO DISPONÍVEL`.

## O que está versionado aqui

```text
synthetic/
├── README.md                              # este arquivo
├── source/                                # conteúdo-fonte que o patch entrega
│   ├── config/faithro-settings.example.json   # estado FINAL (feature_flag=true)
│   ├── data/version.txt                        # estado FINAL (1)
│   ├── data/welcome.txt                        # arquivo criado pelo patch
│   └── remove/obsolete.txt                     # arquivo que o patch remove
├── expected/
│   ├── manifest.example.json              # manifesto conceitual determinístico
│   └── target-state.example.json          # SHA-256 de target-before e target-after
└── scenarios/                             # documentação dos cenários G1–G15
    ├── README.md
    ├── valid/README.md
    ├── hash-mismatch/README.md
    ├── traversal/README.md
    ├── malformed-manifest/README.md
    └── interrupted-download/README.md
```

Os artefatos em `expected/` são **snapshots determinísticos** produzidos pelo
gerador; a CI regenera o laboratório e confere que continuam idênticos (anti-drift).

## Gerar e validar (fora do repositório)

O laboratório executável é sempre criado em um diretório **temporário e
descartável**, nunca dentro do repositório:

```bash
# gerar em um diretório temporário
python scripts/generate-synthetic-patch-lab.py --output /caminho/temporario/lab

# validar o laboratório gerado (integridade + invariantes + simulador)
python scripts/validate-synthetic-patch-lab.py --root /caminho/temporario/lab

# testes negativos de segurança (nenhum deve passar)
python scripts/validate-synthetic-patch-lab.py --self-test
```

## Servidor HTTP local

Servir **apenas** em `127.0.0.1`, porta dinâmica, com `--directory` apontando
para `…/lab/server`. Nunca `0.0.0.0`/`::`, nunca a raiz do repositório, sem
upload, sem firewall e encerrado ao final:

```bash
python -m http.server 0 --bind 127.0.0.1 --directory /caminho/temporario/lab/server
```

## Estados sintéticos

| Item | target-before | target-after |
| --- | --- | --- |
| `config/faithro-settings.json` `feature_flag` | `false` | `true` |
| `data/version.txt` | `0` | `1` |
| `data/welcome.txt` | ausente | criado |
| `data/obsolete.txt` | presente | removido |

Todos os arquivos são pequenos, UTF-8, com LF, de conteúdo próprio e regeneráveis.
