# Registro de licenças de terceiros (`client/licenses/`)

> Toda dependência de terceiros que o FaithRO pretenda **distribuir** ou
> **empacotar** precisa de um registro aprovado aqui **antes** de ser incluída
> em qualquer pacote. Sem registro, o componente permanece **Pendente de
> licença** e **não** pode ser distribuído.

## Processo obrigatório

Para cada dependência, registre os campos abaixo (crie um arquivo por
dependência, por exemplo `opensetup.md`, ou uma seção nesta pasta):

- **Nome**
- **Versão**
- **Autor/publicador**
- **Site oficial**
- **Licença** (nome e link)
- **Arquivo de licença** (caminho do texto de licença, quando aplicável)
- **Permissão de redistribuição** (sim / não / com atribuição / com ressalvas)
- **Atribuição exigida** (texto exato, quando houver)
- **Hash do pacote** (SHA-256 do arquivo auditado)
- **Data da auditoria**
- **Decisão do FaithRO** (uma das classificações da política)

Classificações válidas (ver
[`docs/16-politica-distribuicao-cliente.md`](../../docs/16-politica-distribuicao-cliente.md)):

```text
Permitido
Permitido com atribuição
Somente link para fonte oficial
Uso interno
Pendente de licença
Proibido redistribuir
```

## Regras

- **Ausência de proibição não é permissão.** Sem licença clara, use **Pendente
  de licença**.
- **Não** versionar o binário da dependência aqui — apenas o **registro
  textual** e, quando permitido pela licença, o **texto da licença**.
- Componentes **Pendente de licença** ou **Proibido redistribuir** não entram em
  nenhum pacote distribuído.
- Alterações de classificação exigem revisão em Pull Request.

## Exemplo preenchido (auditoria de 2026-07-24)

Registro do configurador atualmente considerado para o fluxo de primeiro acesso:

| Campo | Valor |
| --- | --- |
| Nome | RO OpenSetup |
| Versão | 3.5.0.692 (2026-07-04) |
| Autor/publicador | Ai4rei/AN |
| Site oficial | `https://nn.ai4rei.net/dev/opensetup/` |
| Licença | Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0); componente Lua sob licença MIT; ícones Fugue sob CC BY 3.0 |
| Arquivo de licença | `doc/license.txt`, `doc/license-lua.txt`, `doc/license-tabicons.txt` (dentro do pacote oficial) |
| Permissão de redistribuição | Licença permite compartilhamento não-comercial com atribuição, **porém o autor desencoraja mirrors e hot-linking** |
| Atribuição exigida | "RO OpenSetup (c) 2010-2026 Ai4rei/AN" |
| Hash do pacote | SHA-256 `7B9A1A037CF2207D98F539102B60AA7D6C515194F220EF7E23EA1EABB3D96F6A` |
| Data da auditoria | 2026-07-24 |
| Decisão do FaithRO | **Somente link para fonte oficial** — não hospedar nem reempacotar |

> Este registro é um exemplo de preenchimento e a base da decisão registrada na
> política. Novas dependências devem seguir o mesmo formato.

## Patcher/launcher avaliados (auditoria de 2026-07-24)

Registro das alternativas de patcher/launcher avaliadas na decisão
[`docs/17-decisao-patcher-launcher.md`](../../docs/17-decisao-patcher-launcher.md).
Nenhum binário é versionado; este é apenas o registro textual.

| Ferramenta | Versão | Autor | Licença | Origem oficial | Modificação | Redistribuição | Proíbe mirror? | Decisão do FaithRO |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Beam Patcher** | v1.0.1 / commit `feed978870` | Beam Patcher Team | MIT OR Apache-2.0 | `github.com/beamguides/beam-patcher` | Sim | Sim (com atribuição da licença) | Não | **Principal — self-host permitido** |
| **RPatchur** | v0.3.0 / commit `21a5482771` | L1nkZ | MIT OR Apache-2.0 | `github.com/L1nkZ/rpatchur` | Sim | Sim (com atribuição da licença) | Não | **Reserva — self-host permitido; upstream estagnado** |
| **Elurair** | v2.21.4.614 | Ai4rei/AN | CC BY-NC 4.0 (fechado) | `elurair.com` | Não (binário fechado) | Não-comercial, mas mirror proibido | **Sim** | Não recomendado — apenas link, sem hospedar/modificar |
| **RO Patcher Lite** | v4.11.0.1395 | Ai4rei/AN | CC BY-NC-ND 4.0 (fechado) | `nn.ai4rei.net/dev/rsu/` | **Não (NoDerivatives)** | Não; mirror proibido | **Sim** | Bloqueado por licença — apenas link |
| **Thor Patcher** | v3.0 alpha 2 | Aeomin | Não declarada claramente | `sourceforge.net/projects/patcherproj` | Indefinido | Indefinido | Indefinido | Bloqueado por manutenção (dormente desde 2016) |

Atribuição exigida (quando aplicável):

- **Beam Patcher:** manter avisos das licenças MIT e Apache-2.0 (arquivos
  `LICENSE-MIT`, `LICENSE-APACHE`) em qualquer redistribuição/fork.
- **RPatchur:** idem (MIT/Apache-2.0).
- **Elurair / RO Patcher Lite:** atribuição a Ai4rei/AN conforme CC BY-NC(-ND);
  o FaithRO **não** redistribui nem hospeda estas ferramentas.

> Componentes classificados como bloqueados ou não recomendados **não** entram em
> nenhum pacote distribuído pelo FaithRO. A confirmação de licença do Thor Patcher
> permanece **pendente** caso se queira reavaliá-lo no futuro.
