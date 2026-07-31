# `client/` — templates e estrutura de distribuição do cliente

> Esta pasta **não** contém um cliente completo. Ela guarda apenas **templates
> textuais**, **exemplos de manifesto** e o **processo de licenças** para a
> futura distribuição do cliente do FaithRO. Nenhum executável, GRF ou asset
> proprietário pode ser versionado aqui.

## O que esta pasta é

- Um lugar versionado para **arquivos de exemplo com placeholders** (`.example`).
- O **registro de licenças** de dependências de terceiros
  ([`licenses/`](licenses/)).
- O **esqueleto do manifesto** de atualização ([`manifests/`](manifests/)).

## O que esta pasta NÃO deve receber

Proibido versionar aqui (bloqueado por [`.gitignore`](../.gitignore) e pelo
validador):

- `*.exe`, `*.dll` (executáveis, launchers, patchers, DLLs);
- `*.grf`, `*.rgz`, `*.thor` (GRFs e pacotes de patch);
- `*.zip`, `*.rar`, `*.7z` (pacotes compactados);
- qualquer asset oficial da Gravity (sprite, mapa, música);
- qualquer arquivo proprietário ou sem licença comprovada.

Ver a política completa em
[`docs/16-politica-distribuicao-cliente.md`](../docs/16-politica-distribuicao-cliente.md).

## Estrutura

```text
client/
├── README.md                      # este arquivo
├── templates/
│   ├── data.ini.example           # ordem de leitura dos data/GRF (placeholders)
│   └── clientinfo.xml.example      # configuração de conexão (placeholders)
├── manifests/
│   └── manifest.example.json       # esqueleto do manifesto de atualização
└── licenses/
    └── README.md                   # processo obrigatório de registro de licenças
```

## Como usar os templates

1. Copie o `.example` para o nome real **fora do controle de versão** (o arquivo
   real do jogador não deve ser commitado).
2. Substitua os placeholders (`<HOST_PUBLICO_FAITHRO>`, `<PORTA_LOGIN>`, etc.)
   pelos valores homologados no momento da distribuição.
3. **Nunca** coloque IP real, porta real não confirmada, domínio não aprovado,
   credenciais, tokens ou chaves nos arquivos versionados.
4. Confirme o formato esperado contra o cliente real antes de distribuir
   (ver [`docs/09` §8](../docs/09-cliente-baseline-protocolo.md)).

## Como registrar licenças

Toda dependência de terceiros distribuída pelo FaithRO precisa de um registro em
[`licenses/README.md`](licenses/README.md) antes de ser incluída em qualquer
pacote. Sem registro aprovado, o componente permanece **pendente de licença**.

## Como gerar checksums (planejado)

Quando houver arquivos próprios a distribuir, gere um `SHA256SUMS.txt` com o
hash de cada arquivo do pacote. Exemplos de comando (executados pelo operador,
fora deste repositório):

```powershell
# Windows / PowerShell
Get-FileHash -Algorithm SHA256 .\faithro.grf | Format-List
```

```bash
# Linux
sha256sum faithro.grf
```

O `SHA256SUMS.txt` (texto) **pode** ser versionado/distribuído; os binários que
ele descreve **não**.

## Como preparar futuras versões do patcher

- O patcher/launcher é um **binário próprio** e **não** é versionado aqui; será
  distribuído por CDN/patch server próprios quando homologado.
- O [`manifests/manifest.example.json`](manifests/manifest.example.json) define o
  **formato esperado** do manifesto (versão, lista de arquivos, hash, tamanho).
  Ele é apenas um exemplo, **sem URLs reais**.
- A implementação do patcher **não** faz parte desta etapa.

## Validação

O script [`scripts/validate-client-assets.py`](../scripts/validate-client-assets.py)
percorre `client/` e falha (código de saída ≠ 0) se encontrar qualquer arquivo
fora da allowlist textual (por exemplo, um binário ou pacote proprietário).
Ele usa **apenas a biblioteca padrão** e não acessa nada fora do repositório.

## Preparação do executável (hex) — decisão

A preparação do **executável** do cliente (habilitar `data` folder, `clientinfo`
de FaithRO, `langtype` etc.) **não** é feita por um patcher de GRF. A ferramenta
para isso é decidida em
[`docs/28-decisao-ferramenta-preparacao-cliente.md`](../docs/28-decisao-ferramenta-preparacao-cliente.md)
(**WARP** — `APROVAR COM RESTRIÇÕES`; NEMO atual **rejeitado** por licença
ausente). A compatibilidade do cliente 2021-11-05 com o servidor está em
[`docs/29-compatibilidade-cliente-2021-11-05-packetver.md`](../docs/29-compatibilidade-cliente-2021-11-05-packetver.md)
(`PROVÁVEL`, sem rebuild). A auditoria estática aprofundada do WARP no commit
fixado está em [`warp-audit/`](warp-audit/) e
[`docs/30-auditoria-estatica-warp.md`](../docs/30-auditoria-estatica-warp.md)
(`BLOQUEADO PARA BUILD DO FONTE` — núcleo só prebuilt no commit — e `APROVADO COM
RESTRIÇÕES` apenas para decidir o caminho do núcleo). Nenhuma dessas etapas
modifica o executável sem autorização humana; nada do cliente é versionado aqui.

## Referências

- [`docs/15-cliente-primeiro-acesso.md`](../docs/15-cliente-primeiro-acesso.md)
- [`docs/16-politica-distribuicao-cliente.md`](../docs/16-politica-distribuicao-cliente.md)
- [`docs/09-cliente-baseline-protocolo.md`](../docs/09-cliente-baseline-protocolo.md)
- [`docs/28-decisao-ferramenta-preparacao-cliente.md`](../docs/28-decisao-ferramenta-preparacao-cliente.md)
- [`docs/29-compatibilidade-cliente-2021-11-05-packetver.md`](../docs/29-compatibilidade-cliente-2021-11-05-packetver.md)
