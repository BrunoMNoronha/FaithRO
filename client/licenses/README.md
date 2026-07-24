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
