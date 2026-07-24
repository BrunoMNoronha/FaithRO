# Política de distribuição do cliente do FaithRO

> **Escopo:** documento de referência e governança. Define o que o FaithRO pode
> ou não distribuir, hospedar ou versionar em relação ao cliente. Não altera
> código, banco ou configuração operacional. Complementa
> [09-cliente-baseline-protocolo.md §10–§12](09-cliente-baseline-protocolo.md) e
> [15-cliente-primeiro-acesso.md](15-cliente-primeiro-acesso.md).

## Objetivo

Estabelecer, de forma explícita e auditável, a classificação de origem, licença
e permissão de distribuição de cada componente do cliente, evitando que o
projeto redistribua conteúdo proprietário da Gravity ou de terceiros sem
licença comprovada.

## Princípios

- **Ausência de proibição não é permissão.** Sem licença que autorize
  redistribuição, o componente é tratado como **pendente** ou **proibido**.
- **Existência pública não autoriza redistribuição.** Um arquivo estar
  disponível na internet não concede licença.
- **Um hash identifica, não licencia.** Registrar SHA-256 serve para
  identificação de um arquivo já possuído legalmente, não para redistribuí-lo.
- **Preferir link à hospedagem.** Quando a licença ou o autor não autorizarem
  claramente mirror/reempacotamento, apenas **direcionar à fonte oficial**.
- **Sem mirrors não oficiais.** Não publicar links de Mega, Google Drive,
  MediaFire ou equivalentes. Links comunitários devem apontar para a **página da
  discussão/projeto**, não para anexos executáveis.

## Classificações possíveis

```text
Permitido
Permitido com atribuição
Somente link para fonte oficial
Uso interno
Pendente de licença
Proibido redistribuir
```

## Tabela de classificação por componente

| Componente | Origem | Função | Pode entrar no Git? | Pode ser hospedado pelo FaithRO? | Ação |
| --- | --- | --- | --- | --- | --- |
| `RAG_SETUP_211105` | Gravity Co., Ltd. (oficial) | Instalador do cliente-base completo | **Não** | **Não** | **Proibido redistribuir** — apenas link para a fonte oficial da Gravity |
| `2021-11-03_Ragexe` (executável) | Gravity (executável) / hexed comunitário | Executável do cliente-alvo | **Não** | **Não** | **Proibido redistribuir** — não hospedar executáveis (originais ou modificados) |
| OpenSetup (`opensetup.exe`) | Ai4rei/AN | Configurador de vídeo/áudio | **Não** | **Não** | **Somente link para fonte oficial** — CC BY-NC 4.0; autor desencoraja mirrors/hot-link |
| `faithro.grf` | FaithRO (próprio) | GRF com assets próprios/licenciados | **Não** (binário; ver `.gitignore`) | **Sim**, quando homologado e composto só de conteúdo próprio/licenciado | Distribuir via patcher/CDN próprios |
| `data.ini` | FaithRO (próprio) | Ordem de leitura dos data/GRF | **Somente como `.example`** | **Sim** (texto próprio) | Versionar template; distribuir o real com o pacote |
| `clientinfo.xml` / `sclientinfo.xml` | FaithRO (próprio) | Configuração de conexão do cliente | **Somente como `.example`** | **Sim** (texto próprio) | Versionar template com placeholders; sem IP/porta reais |
| Launcher/patcher próprio | FaithRO (próprio) | Bootstrap e atualização | **Não** (binário) | **Sim**, quando homologado | Distribuir via CDN própria; assinar código futuramente |
| Checksums (`SHA256SUMS.txt`) | FaithRO (próprio) | Verificação de integridade | **Sim** (texto) | **Sim** | Gerar e publicar com cada versão |
| Assets visuais próprios | FaithRO (próprio) | Sprites/telas/UI autorais | **Não** (binário) | **Sim** | Empacotar em `faithro.grf` |
| Assets da Gravity | Gravity Co., Ltd. | Sprites, mapas, música oficiais | **Não** | **Não** | **Proibido redistribuir** |
| Traduções comunitárias | Comunidade | Tradução de textos/UI | **Não**, sem licença comprovada | **Não**, sem licença comprovada | **Pendente de licença** até comprovação por autor/licença |
| DLLs de terceiros | Terceiros | Bibliotecas de apoio | **Não** (binário) | Depende da licença de cada DLL | **Pendente de licença** — avaliar caso a caso; não baixar DLLs avulsas |

> Componentes marcados **Pendente de licença** só mudam de classificação após
> comprovação registrada em [`client/licenses/README.md`](../client/licenses/README.md).

## Downloads auditados localmente

Auditoria **read-only** (sem execução, sem upload, sem cópia para o repositório).
Data da auditoria: **2026-07-24**. Caminhos pessoais **não** são registrados:
os arquivos residem em `<CAMINHO_LOCAL_REDACTED>`.

### 1. `RAG_SETUP_211105.exe`

| Campo | Valor |
| --- | --- |
| Nome completo | `RAG_SETUP_211105.exe` |
| Tamanho | 3.427.631.040 bytes (~3,19 GiB) |
| SHA-256 | `D9067CC9AC62C85FA599AC94BBB19E9E96A1B7529181252806DC1DF49E0293AA` |
| Tipo | Executável PE (InstallShield Setup Launcher Unicode); `ProductName` "Ragnarok"; `CompanyName` "Gravity"; `FileVersion` 17.2 |
| Assinatura | **Válida** |
| Publicador | `CN="GRAVITY Co., Ltd.", O="GRAVITY Co., Ltd.", L=Mapo-gu, S=Seoul, C=KR` |
| Emissor | `DigiCert SHA2 Assured ID Code Signing CA` |
| Timestamp | `DigiCert Timestamp 2021` |
| Formato | Instalador único (cliente-base completo) |
| Origem declarada | Gravity (fonte documentada: `http://rofull.gnjoy.com/RAG_SETUP_211105.exe`) |
| Situação de licença | Proprietária — Gravity Co., Ltd. |
| Decisão de distribuição | **Proibido redistribuir** — apenas link para a fonte oficial |

### 2. `2026-07-04opensetup-lua-3.5.0.692.zip`

| Campo | Valor |
| --- | --- |
| Nome completo | `2026-07-04opensetup-lua-3.5.0.692.zip` |
| Tamanho | 266.480 bytes (~260,2 KiB) |
| SHA-256 | `7B9A1A037CF2207D98F539102B60AA7D6C515194F220EF7E23EA1EABB3D96F6A` |
| Tipo | Arquivo ZIP contendo `opensetup.exe` (736.696 bytes), `opensetup.ini.sample` e `doc/` (licenças e readme) |
| Assinatura | ZIP sem assinatura Authenticode (esperado para `.zip`) |
| Publicador/autor | Ai4rei/AN |
| Origem declarada | Página oficial `https://nn.ai4rei.net/dev/opensetup/`; versão estável **3.5.0.692 (2026-07-04)** — confere com o nome do arquivo |
| Situação de licença | **CC BY-NC 4.0** (principal, `doc/license.txt`); componente Lua sob licença MIT (`doc/license-lua.txt`); ícones Fugue sob CC BY 3.0 (`doc/license-tabicons.txt`) |
| Redistribuição | Autor **desencoraja mirrors e hot-linking** na página oficial |
| Decisão de distribuição | **Somente link para fonte oficial** — não hospedar nem reempacotar |

> Observação sobre a CC BY-NC 4.0: a licença permite compartilhamento
> não-comercial **com atribuição**. Ainda assim, como o autor **pede
> explicitamente que não sejam criados mirrors** e que se aponte para a seção
> oficial (para evitar versões desatualizadas), a decisão do FaithRO é a mais
> conservadora e respeitosa: **apenas link para a fonte oficial**. Não
> interpretar a licença permissiva como convite a reempacotar.

## Riscos

- **Licenciamento:** classificar erroneamente um componente proprietário como
  distribuível. Mitigação: tabela acima + registro obrigatório em
  `client/licenses/`.
- **Links indisponíveis:** páginas oficiais podem sair do ar; não substituir por
  mirror não oficial. Mitigação: registrar apenas fontes oficiais e revalidar
  periodicamente.
- **Falsos positivos de antivírus** em ferramentas comunitárias: analisar
  (origem, hash, assinatura), nunca recomendar desativar proteção.
- **Commit acidental de conteúdo proprietário:** binários entrando no Git.
  Mitigação: `.gitignore` + validador `scripts/validate-client-assets.py`.

## Rollback

Este documento não altera ambiente. O rollback é reverter o commit desta branch.
Nenhuma configuração ativa, arquivo do servidor ou binário do cliente é alterado.

## Referências cruzadas

- [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md) — §10 a §12,
  arquivos que podem/não podem ser documentados ou versionados.
- [10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md) —
  hierarquia e níveis de confiança das fontes.
- [15-cliente-primeiro-acesso.md](15-cliente-primeiro-acesso.md) — fluxo de
  primeiro acesso.
- [`client/README.md`](../client/README.md) e
  [`client/licenses/README.md`](../client/licenses/README.md) — estrutura e
  processo de registro de licenças.
