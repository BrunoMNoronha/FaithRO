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
│   ├── first-build-plan.example.json # plano do primeiro build controlado (D1-B8)
│   ├── first-build-runbook.example.json        # runbook operacional do primeiro build (D1-B10)
│   ├── first-build-authorization.example.json  # modelo de autorização humana, não concedido (D1-B10)
│   ├── first-build-authorization-request.example.json # solicitação formal de autorização, pendente (D1-B12)
│   ├── first-build-execution-evidence.example.json # template de evidência futura, não executado (D1-B10)
│   ├── evidence/                     # evidências de compatibilidade/seleção/instalação
│   ├── overlays/                     # overlay de segurança de laboratório (.patch textual)
│   └── schemas/                      # schemas do manifesto e dos planos
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

## Auditoria de build, seleção de toolchain, plano e instalação isolada (ETAPAS 2O-D1, 2O-D1-B1 a 2O-D1-B6)

A preparação para uma futura construção auditável do Beam (auditoria estática do
commit fixado `feed978870`, manifesto da origem, overlay de segurança de
laboratório, plano controlado de instalação/build e validadores/CI) está em
[`beam-audit/`](beam-audit/) e documentada em
[`docs/19-preparacao-build-auditavel-beam.md`](../../docs/19-preparacao-build-auditavel-beam.md).

Na ETAPA 2O-D1-B1, a toolchain Rust 1.77.2 foi empiricamente testada e **REJEITADA**:
a dependência `zeroize 1.9.0` exige `edition = "2024"` e `rust-version = "1.85"`,
impedindo qualquer compilação com a Rust 1.77.2 (ver [`beam-audit/evidence/toolchain-compatibility.json`](beam-audit/evidence/toolchain-compatibility.json)).

Nas ETAPAS 2O-D1-B2 e 2O-D1-B3, a toolchain Rust **`1.85.0`** foi selecionada e reconciliada por auditoria estática
como a menor versão mínima compatível com o grafo de dependências do Beam. Ver evidência em
[`beam-audit/evidence/toolchain-selection.json`](beam-audit/evidence/toolchain-selection.json)
e documentação em [`docs/20-primeiro-build-controlado-beam.md`](../../docs/20-primeiro-build-controlado-beam.md).

Nas ETAPAS 2O-D1-B4 e 2O-D1-B5, o plano técnico de coexistência da Rust 1.85.0 foi documentado e integrado em [`docs/21-plano-instalacao-toolchain-rust-beam.md`](../../docs/21-plano-instalacao-toolchain-rust-beam.md).

Na ETAPA 2O-D1-B6, a instalação isolada da toolchain nomeada `1.85.0-x86_64-pc-windows-msvc` (perfil `minimal`) foi **EXECUTADA E VALIDADA** empiricamente (mantendo a Rust 1.77.2 como default ativa). Ver evidência em [`beam-audit/evidence/toolchain-installation.json`](beam-audit/evidence/toolchain-installation.json) e documentação em [`docs/22-instalacao-isolada-toolchain-rust-beam.md`](../../docs/22-instalacao-isolada-toolchain-rust-beam.md).

Na ETAPA 2O-D1-B8, o **plano do primeiro build controlado** foi modelado como artefato versionado e validável ([`beam-audit/first-build-plan.example.json`](beam-audit/first-build-plan.example.json)) e documentado em [`docs/23-planejamento-primeiro-build-controlado-beam.md`](../../docs/23-planejamento-primeiro-build-controlado-beam.md). O plano registra a **autorização de execução como BLOQUEADA** (`build_authorized=false`, `next_human_authorization_required=true`) e exige autorização humana explícita em etapa posterior.

Na ETAPA 2O-D1-B10, o plano foi transformado em **runbook operacional** com **checkpoint de autorização humana**, **go/no-go** e **modelo de evidência**, em três artefatos separados por responsabilidade ([`beam-audit/first-build-runbook.example.json`](beam-audit/first-build-runbook.example.json), [`beam-audit/first-build-authorization.example.json`](beam-audit/first-build-authorization.example.json), [`beam-audit/first-build-execution-evidence.example.json`](beam-audit/first-build-execution-evidence.example.json)) e documentado em [`docs/24-runbook-primeiro-build-controlado-beam.md`](../../docs/24-runbook-primeiro-build-controlado-beam.md). A **autorização humana continua NÃO concedida** (`authorization_granted=false`, `execution_permitted=false`).

Na ETAPA 2O-D1-B12, foi preparada a **solicitação formal de autorização humana** do primeiro build como artefato versionado e validável ([`beam-audit/first-build-authorization-request.example.json`](beam-audit/first-build-authorization-request.example.json)), vinculada ao commit de referência do FaithRO e ao SHA-256 do runbook e do modelo de autorização, e documentada em [`docs/25-solicitacao-autorizacao-primeiro-build-beam.md`](../../docs/25-solicitacao-autorizacao-primeiro-build-beam.md). A solicitação **não concede** e **não pode conceder** autorização a si mesma (`request_status=PENDING_HUMAN_DECISION`); a decisão pertence ao artefato de autorização separado, em etapa posterior. **Merge ou aprovação de PR não equivalem à autorização operacional.**

**Build permanece NÃO autorizado. Nenhum binário foi compilado ou executado.**

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
