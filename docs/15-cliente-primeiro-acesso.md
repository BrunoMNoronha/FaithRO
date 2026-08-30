# Cliente do FaithRO: primeiro acesso (planejado)

> **Escopo:** documento de referência e planejamento. Nenhuma alteração de
> código, banco ou configuração operacional é executada por este documento.
> Nenhum cliente completo, executável, GRF ou asset proprietário é
> redistribuído por este documento ou pelo repositório. Todo o fluxo abaixo é
> **planejado** e depende de homologação futura de componentes ainda
> inexistentes (patcher, `faithro.grf`, XML real, domínio/CDN).

## Objetivo

Explicar, de forma segura e rastreável, como um jogador prepara uma instalação
**legítima** do cliente e realiza o primeiro acesso ao FaithRO - Laus Deo, sem
que o projeto redistribua qualquer conteúdo proprietário da Gravity ou de
terceiros sem licença.

Este documento **não** cria um cliente, **não** aplica patches no executável e
**não** homologa nenhuma ferramenta. Ele descreve o processo previsto e a
estrutura planejada dos arquivos próprios do FaithRO.

## Baseline adotado

O primeiro acesso pressupõe o baseline já registrado no projeto; **não** o
redefina aqui:

| Item | Valor | Referência |
| --- | --- | --- |
| `PACKETVER` | `20211103` | [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md), [12-configuracao-packetver.md](12-configuracao-packetver.md) |
| Cliente-alvo | `2021-11-03_Ragexe` (família `Ragexe`) | [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md) |
| Packet obfuscation | sem obfuscação efetiva no padrão do baseline | [09 §6](09-cliente-baseline-protocolo.md) |

> A compatibilidade **não** é garantida pelo nome nem pela data do executável.
> Ver [09 §2](09-cliente-baseline-protocolo.md).

## Pré-requisitos

- Windows compatível com o cliente-alvo (ver requisitos do cliente-base e das
  ferramentas; o OpenSetup declara suporte a Windows 2000/XP/Vista/7/8/8.1/10/11).
- Espaço em disco suficiente para o cliente-base completo (o instalador oficial
  atual ocupa **vários GiB**; reserve folga para a instalação descompactada).
- Acesso à internet para obter o cliente-base **diretamente da fonte
  autorizada** e, futuramente, para o patcher do FaithRO.
- **Cliente-base obtido diretamente da fonte autorizada** (Gravity). O FaithRO
  **não** distribui o cliente-base — ver
  [16-politica-distribuicao-cliente.md](16-politica-distribuicao-cliente.md).
- Patcher/bootstrap do FaithRO **quando futuramente homologado** (ainda não
  existe; ver "Pendências").

## Fluxo previsto (planejado)

> Todo o fluxo está marcado como **planejado**. Cada passo que depende de um
> componente ainda não homologado é sinalizado com `(pendente de homologação)`.

1. O jogador obtém o **cliente-base** diretamente da **fonte autorizada** da
   Gravity. O FaithRO apenas indica a página oficial; não hospeda o arquivo.
2. O jogador instala o cliente-base em uma **pasta dedicada**, separada de
   qualquer instalação de outro servidor.
3. O jogador instala ou copia **somente os arquivos próprios do FaithRO**
   (assets próprios, `faithro.grf`, `data.ini`, configuração) — `(pendente de
   homologação)`.
4. O **patcher do FaithRO** atualiza **exclusivamente** arquivos próprios ou
   licenciados, nunca o executável ou os GRFs oficiais da Gravity — `(pendente
   de homologação)`.
5. O jogador executa o **configurador homologado** (por exemplo, o OpenSetup,
   obtido da página oficial do autor — ver política) para resolução, tela e
   áudio.
6. O jogador abre o **launcher do FaithRO** — `(pendente de homologação)`.
7. O jogador realiza o **primeiro login** — `(pendente de validação;
   requer servidor e cliente reais testados)`.

## Arquivos esperados do FaithRO (estrutura planejada)

Os nomes abaixo são **provisórios** e podem mudar após a homologação. Nenhum
destes arquivos existe ou é versionado ainda; apenas assets **próprios ou
licenciados** poderão ser distribuídos.

```text
FaithRO/
├── FaithRO-Patcher.exe        # launcher/patcher próprio (a homologar)
├── faithro.grf                # GRF com assets PRÓPRIOS/licenciados do FaithRO
├── data.ini                   # ordem de leitura dos data/GRF (ver template)
├── data/
│   └── clientinfo.xml          # ou sclientinfo.xml (a confirmar no cliente real)
├── README-PRIMEIRO-ACESSO.txt
├── LICENSES-TERCEIROS.txt     # atribuições exigidas por dependências
└── SHA256SUMS.txt             # checksums dos arquivos próprios distribuídos
```

> `faithro.grf` deve conter **apenas** conteúdo próprio ou licenciado. Ele
> **não** substitui `data.grf`/`rdata.grf` oficiais e **não** pode empacotar
> assets da Gravity. Ver [16](16-politica-distribuicao-cliente.md).

Templates seguros e comentados estão versionados em
[`client/templates/`](../client/templates/) e o esqueleto do manifesto de
atualização em [`client/manifests/`](../client/manifests/).

## Configurador (OpenSetup) — observação de licença

O OpenSetup (autor Ai4rei/AN) é distribuído sob **CC BY-NC 4.0** e o autor
**desencoraja mirrors e hot-linking**. Portanto o FaithRO deve **direcionar o
jogador à página oficial** do autor, e não hospedar/reempacotar o arquivo. A
classificação completa está em
[16-politica-distribuicao-cliente.md](16-politica-distribuicao-cliente.md).

## Solução de problemas (apenas orientações seguras)

- Conferir o **SHA-256** dos arquivos próprios do FaithRO contra `SHA256SUMS.txt`.
- Executar o cliente/patcher a partir de uma **pasta com permissão de escrita**
  (evitar `C:\Program Files` sem necessidade).
- Verificar **conectividade** com o servidor (portas de login/char/map).
- **Não misturar** instalações de outros servidores na mesma pasta.
- **Não substituir** arquivos aleatoriamente nem sobrescrever GRFs oficiais.
- **Não baixar DLLs avulsas** de fontes não confiáveis.
- **Não desativar antivírus**, Windows Defender ou firewall; não recomendar
  exclusões globais. Falsos positivos, quando ocorrerem, devem ser analisados
  (origem, hash, assinatura), não ignorados às cegas.
- **Não conceder privilégio de administrador** sem necessidade comprovada.
- Coletar logs **sem** dados de conta (sem senha, token ou dados pessoais).

## Matriz de testes (planejada)

Estes testes são **planejados**; nenhum é executado nesta etapa. Não há ambiente
cliente homologado disponível. Ver também
[09 §14](09-cliente-baseline-protocolo.md).

| Cenário | O que validar | Estado |
| --- | --- | --- |
| Instalação em pasta limpa | cliente-base instala isolado de outros servidores | Pendente |
| Aplicação inicial dos arquivos FaithRO | arquivos próprios copiados sem tocar no core oficial | Pendente |
| Atualização completa | patcher aplica todos os arquivos do manifesto | Pendente |
| Atualização interrompida e retomada | retomar sem corromper a instalação | Pendente |
| Validação de SHA-256 | checksums conferem com `SHA256SUMS.txt` | Pendente |
| Primeira abertura | executável inicia sem DLL ausente nem falha imediata | Pendente |
| Configuração de resolução | resolução aplicada pelo configurador homologado | Pendente |
| Tela cheia e janela | alternância funciona | Pendente |
| Áudio | som configurável e audível | Pendente |
| Login | cliente alcança o login-server; sem `Unknown packet` | Pendente |
| Seleção de personagem | lista abre; seleção conecta ao map-server | Pendente |
| Entrada em mapa | personagem entra e se move | Pendente |
| Reconexão | reconecta após queda | Pendente |
| Acentuação em português | textos com acento exibidos corretamente | Pendente |
| Ausência de arquivos de outros servidores | nenhuma contaminação de outra instalação | Pendente |
| Comportamento no Windows Defender | analisar sem desativar proteção | Pendente |
| Rollback para versão anterior | volta ao último `faithro.grf`/manifesto homologado | Pendente |
| Incompatibilidade cliente/servidor | erro tratado e diagnosticável | Pendente |
| Falha do patch server | patcher falha de forma segura | Pendente |
| Arquivo corrompido | detecção por checksum e reparo/rebaixa | Pendente |
| Manifesto inválido | patcher rejeita manifesto malformado | Pendente |

## Riscos

- **Jurídico:** redistribuir cliente-base, executável, GRF ou assets da Gravity
  sem licença. Mitigação: FaithRO só distribui conteúdo próprio/licenciado e
  direciona à fonte oficial (ver [16](16-politica-distribuicao-cliente.md)).
- **Técnico (protocolo):** divergência de `PACKETVER`/obfuscação →
  `Unknown packet`/desconexão. Ver [09 §6 e §14](09-cliente-baseline-protocolo.md).
- **Operacional:** instruções de instalação que quebram outras instalações ou
  exigem privilégios desnecessários. Mitigação: pasta dedicada, sem admin.
- **Segurança:** orientar desativação de antivírus ou download de DLLs avulsas.
  Mitigação: proibido neste projeto.
- **Dependência de ferramenta comunitária:** o configurador é de terceiros
  (licença NC); indisponibilidade da página oficial afeta o fluxo. Mitigação:
  apenas link para a fonte oficial; sem mirror.

## Rollback

- Este documento não altera ambiente. O rollback documental é reverter o commit
  desta branch.
- Para o fluxo do jogador (quando o patcher existir): manter o **último
  `faithro.grf` e o último manifesto homologados** como ponto de retorno;
  reverter para eles em caso de patch com falha, sempre preservando o backup
  anterior antes de aplicar uma atualização.

## Referências cruzadas

- [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md) — baseline,
  protocolo, obfuscação e matriz de compatibilidade.
- [10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md) —
  política e hierarquia de fontes.
- [12-configuracao-packetver.md](12-configuracao-packetver.md) — procedimento
  planejado de `PACKETVER`/obfuscação/web server.
- [16-politica-distribuicao-cliente.md](16-politica-distribuicao-cliente.md) —
  o que pode ou não ser distribuído e auditoria dos downloads.
- [`client/README.md`](../client/README.md) — estrutura segura de `client/`.
