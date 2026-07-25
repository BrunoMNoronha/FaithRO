# `client/patcher/` — estratégia de patcher/launcher (protótipo)

> Esta pasta **não** contém nenhum binário de patcher. Guarda apenas a decisão
> aplicada, **templates de configuração com placeholders** e **fixtures textuais**
> de laboratório sintético. Nenhum executável, GRF, `.thor`, `.rgz` ou pacote é
> versionado aqui. Ver a decisão completa em
> [`docs/17-decisao-patcher-launcher.md`](../../docs/17-decisao-patcher-launcher.md).

## Decisão vigente

- **Candidato principal:** **Beam Patcher** (`beamguides/beam-patcher`).
- **Versão a fixar:** v1.0.1, commit `feed978870`.
- **Licença:** MIT OR Apache-2.0 (permite redistribuição, modificação e self-host).
- **Origem oficial:** `https://github.com/beamguides/beam-patcher` — **sem mirror**.
- **Classificação:** APROVADO PARA PROTÓTIPO LOCAL CONTROLADO (não é produção).
- **Candidato reserva:** **RPatchur** (`L1nkZ/rpatchur`), v0.3.0 / commit
  `21a5482771` — permissivo, porém upstream estagnado (exigiria fork interno).

## Não há binário versionado

O binário do patcher **nunca** entra no Git (bloqueado por
[`.gitignore`](../../.gitignore) e pelos validadores). Para obtê-lo:

1. **Release oficial:** baixar da página oficial do Beam Patcher (GitHub
   Releases). **Não** usar mirrors de terceiros.
2. **Compilar do fonte** (recomendado para auditar antes de usar):
   ```bash
   # fora do repositório do FaithRO; requer toolchain Rust 1.75+
   git clone https://github.com/beamguides/beam-patcher
   cd beam-patcher
   git checkout feed978870   # fixar a versão auditada
   cargo build --release
   ```
   A instalação de toolchains **não** faz parte da etapa de homologação atual.

## Estrutura desta pasta

```text
client/patcher/
├── README.md                         # este arquivo
├── lab/
│   └── README.md                     # como executar o lab sintético (fora do repo)
├── templates/
│   ├── beam-config.prod.example.yml  # config de PRODUÇÃO (HTTPS, placeholders)
│   └── beam-config.lab.example.yml   # config de LABORATÓRIO (127.0.0.1)
├── beam-audit/                       # auditoria estática pré-build (ETAPA 2O-D1)
│   ├── README.md
│   ├── upstream-manifest.example.json
│   ├── security-findings.example.json
│   ├── build-plan.example.json
│   ├── overlays/                     # overlay de segurança de laboratório (.patch textual)
│   └── schemas/                      # schemas do manifesto e do plano
└── fixtures/
    ├── README.md                     # estrutura do lab + plano de testes G1–G15
    ├── patchlist.example.txt         # patchlist sintético (nomes + SHA-256)
    ├── version.example.json          # version.json sintético do self-updater
    └── synthetic/                    # homologação sintética executável (ETAPA 2O-D)
        ├── README.md
        ├── source/                   # conteúdo-fonte que o patch entrega
        ├── expected/                 # manifesto + estados determinísticos (SHA-256)
        └── scenarios/                # cenários G1–G15 (valid, hash-mismatch, …)
```

## Auditoria de build (ETAPA 2O-D1)

A preparação para uma futura construção auditável do Beam (auditoria estática do
commit fixado `feed978870`, manifesto da origem, overlay de segurança de
laboratório, plano controlado de instalação/build e validadores/CI) está em
[`beam-audit/`](beam-audit/) e documentada em
[`docs/19-preparacao-build-auditavel-beam.md`](../../docs/19-preparacao-build-auditavel-beam.md).
**Nada foi instalado, construído, executado ou implantado.**

## Homologação sintética do fluxo (ETAPA 2O-D)

O **fluxo conceitual** do Beam (manifesto → loopback → download → integridade →
aplicação → estado final) é homologado de forma 100% sintética. Ver
[`docs/18-homologacao-patch-sintetico-beam.md`](../../docs/18-homologacao-patch-sintetico-beam.md)
e [`fixtures/synthetic/README.md`](fixtures/synthetic/README.md).

```bash
python scripts/generate-synthetic-patch-lab.py --output <DIR_TEMPORARIO>/lab
python scripts/validate-synthetic-patch-lab.py --root <DIR_TEMPORARIO>/lab
python scripts/validate-synthetic-patch-lab.py --self-test
```

- O patch sintético é um **manifesto conceitual**
  (`FORMATO CONCEITUAL — NÃO CONSUMÍVEL PELO BEAM`), **não** um pacote
  `.beam`/`.thor` real; o formato binário do Beam não foi confirmado sem a
  toolchain Rust.
- A aplicação usa o **simulador do laboratório**, nunca o Beam. A execução
  dinâmica do Beam está `BLOQUEADO — TOOLCHAIN DO BEAM NÃO DISPONÍVEL`.
- **Status da homologação:** `APROVADO COM RESTRIÇÕES` (lab e validações próprias
  passam; Beam não executado por ausência de toolchain).

## Arquivos permitidos e proibidos

**Permitido:** `.md`, `.txt`, `.json`, `.yml`/`.yaml` e `.example` **textuais**,
com placeholders.

**Proibido (bloqueado por `.gitignore` e validadores):** `*.exe`, `*.dll`,
`*.grf`, `*.gpf`, `*.thor`, `*.rgz`, `*.zip`, `*.rar`, `*.7z`, o binário do
patcher, GRFs, pacotes de patch e qualquer asset proprietário.

## Regras de configuração (segurança)

Os templates e qualquer configuração real devem:

- usar **HTTPS** em produção; `http://127.0.0.1` **apenas** em fixtures de
  laboratório claramente marcadas;
- **não** conter domínio real, IP real, porta real, senha, token ou caminho
  pessoal;
- **não** habilitar SSO (`sso.enabled: false`);
- **não** salvar senha;
- **não** iniciar o cliente após um patch incompleto;
- apontar `client_exe`/`setup_exe` por **nome** (nunca um `Ragexe.exe` real
  versionado).

## Como preparar patches (planejado)

1. Gerar o `faithro.grf` com conteúdo **apenas** próprio/licenciado (nunca assets
   da Gravity — ver [16](../../docs/16-politica-distribuicao-cliente.md)).
2. Empacotar deltas no formato do Beam (`.beam`/`.thor`/`.rgz`) — **fora** do Git.
3. Publicar `patchlist.txt` (nome + SHA-256 por linha) e, se usar self-update,
   `version.json` com o SHA-256 do novo patcher.

## Como validar checksums

O `patchlist.txt` deve listar o **SHA-256** de cada patch; o Beam verifica a
integridade antes de aplicar. Para gerar hashes (fora do repositório):

```bash
sha256sum 001_inicial.beam        # Linux
```
```powershell
Get-FileHash -Algorithm SHA256 .\001_inicial.beam | Format-List   # Windows
```

## Como fazer rollback

- **Operacional:** manter o **último `faithro.grf` e o último `patchlist`
  homologados** como ponto de retorno; restaurar o backup antes de reaplicar.
- **Documental:** reverter o commit do PR correspondente.

O rollback nativo do Beam não foi validado nesta etapa (teste G14 pendente).

## Como promover uma versão de laboratório para homologação real

1. Auditar integralmente o fonte do Beam na versão fixada (parsing de patchlist,
   path traversal, superfície Tauri/WebView).
2. Compilar internamente e assinar o binário (code signing) — pendente.
3. Executar o plano G1–G15 (ver [`fixtures/README.md`](fixtures/README.md)) em
   laboratório com o binário compilado.
4. Definir patch server HTTPS próprio e testar com `faithro.grf` real.
5. Só então revisar a classificação de "protótipo" para um estágio superior — em
   PR próprio, com evidências. **Nunca** declarar "produção" sem esses passos.
</content>
