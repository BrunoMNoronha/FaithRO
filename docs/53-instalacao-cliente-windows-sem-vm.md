# Instalação e preparação do cliente no Windows, sem VM

> Atualizado em 2026-10-01. Guia para o operador do primeiro acesso de teste.
> A instalação oficial e a preparação para o FaithRO são etapas distintas.
> O procedimento de conexão ainda depende de homologação da ferramenta e dos
> patches no host. Este guia não comprova instalação, patch ou login executados.

## Download direto do cliente oficial

[Baixar RAG_SETUP_211105.exe — instalador oficial da Gravity](https://rofull.gnjoy.com/RAG_SETUP_211105.exe)

Tamanho informado pelo servidor: **3,43 GB** (3.427.631.040 bytes).
Link verificado em 2026-10-01. Após o download, confira assinatura e SHA-256
conforme os passos 2 e 3 antes de executar o instalador.

## Objetivo e contexto

Instalar ou reaproveitar o cliente oficial, preservar os arquivos envolvidos em backup e configurar a
instalação existente para testar login → personagem → mapa no FaithRO - Laus Deo.
Todo o trabalho acontece no Windows do operador, sem VM, conforme a
[decisão registrada no documento 52](52-gate5-validacao-pos-snapshot-baseline-preparacao-cliente.md#decisao-vigente-primeiro-acesso-no-windows-sem-vm).

O cliente inventariado em setembro foi instalado a partir de
`RAG_SETUP_211105` e localizado em `C:\Gravity\Ragnarok`. Seu `Ragexe.exe`
tem timestamp PE 2021-11-05 e compatibilidade **provável**, ainda não comprovada
no jogo, com o servidor `PACKETVER=20211103`. Um download oficial mais recente
não substitui automaticamente essa baseline. Ver [documento 29](29-compatibilidade-cliente-2021-11-05-packetver.md).

## Pré-requisitos

- Windows do operador, Defender ativo e espaço para o cliente completo e o backup dos arquivos envolvidos.
- Cliente e assets obtidos legitimamente da fonte oficial; sem mirrors comunitários.
- Pasta de backup escolhida pelo operador, fora do repositório e da instalação.
- Pasta de evidências fora do Git; não registrar senha ou dados de jogadores.
- Para o login: servidor disponível, IP autorizado no firewall e conta de teste.

Não é necessário instalar VMware, criar snapshot ou executar `scripts/lab/`.
Não instale launcher/patcher do FaithRO: ainda não existe um pacote homologado
para jogadores. Não baixe DLLs avulsas para resolver erros.

## Passo 1 — Conferir se o cliente já está instalado

1. Abra o Explorador de Arquivos e consulte `C:\Gravity\Ragnarok`.
2. Confira `Ragexe.exe`, `data.grf` e `Setup.exe`.
3. Se estiverem presentes, prossiga para o passo 3; não reinstale nem atualize
   automaticamente a instalação já inventariada.
4. Se a pasta não existir, verifique o destino escolhido na instalação anterior.
   Se não houver cliente instalado, siga o passo 2.

## Passo 2 — Instalar o cliente oficial, se necessário

1. Abra a [página oficial de downloads do kRO/Gravity](https://ro.gnjoy.com/pds/down/).
   Para o instalador atual, há também a [página oficial de confirmação do download](https://ro.gnjoy.com/ResService/game/download/gamedownloadpopupV2.asp?game=ro&type=exe).
2. Para reproduzir a baseline, use o instalador oficial já possuído ou o
   [RAG_SETUP_211105.exe no servidor oficial da Gravity](https://rofull.gnjoy.com/RAG_SETUP_211105.exe).
   O endereço histórico respondeu com HTTP 200 em 2026-10-01; não foi baixado
   nem executado nesta verificação. A página de downloads atual pode oferecer outra
   versão: registre sua identidade e trate a compatibilidade como pendente.
3. Antes de executar o instalador, abra **Propriedades → Assinaturas Digitais**
   e verifique a assinatura da Gravity. Registre também seu SHA-256:

   ```powershell
   $installerPath = Read-Host 'Caminho completo do instalador oficial'
   Get-AuthenticodeSignature -LiteralPath $installerPath |
     Select-Object Status, @{Name='Signatario';Expression={$_.SignerCertificate.Subject}}
   Get-FileHash -LiteralPath $installerPath -Algorithm SHA256
   ```

4. Se origem ou assinatura não puderem ser verificadas, interrompa e investigue;
   não contorne alertas nem desative o Defender.
5. Execute o instalador oficial, leia os termos e escolha uma pasta dedicada.
   Registre o destino real. A instalação conhecida do projeto usa
   `C:\Gravity\Ragnarok`; não sobrescreva uma instalação existente.
6. Ao terminar, confira os arquivos do passo 1.
7. Não execute o patcher oficial para atualizar automaticamente essa baseline:
   uma atualização pode trocar o executável e invalidar a identificação histórica.

## Passo 3 — Identificar e preservar o original

Execute no PowerShell, ajustando o caminho caso sua instalação seja diferente:

```powershell
$clientSource = (Resolve-Path -LiteralPath 'C:\Gravity\Ragnarok').Path
Get-FileHash -LiteralPath (Join-Path $clientSource 'Ragexe.exe') -Algorithm SHA256
Get-FileHash -LiteralPath (Join-Path $clientSource 'data.grf') -Algorithm SHA256
Get-AuthenticodeSignature -LiteralPath (Join-Path $clientSource 'Ragexe.exe') |
  Select-Object Status, @{Name='Signatario';Expression={$_.SignerCertificate.Subject}}
```

Referências da instalação inventariada em 03/09/2026:

| Arquivo | SHA-256 histórico |
| --- | --- |
| `Ragexe.exe` | `8990A9A9CD6623E173BCC8B406A311AF32773EB881E539082126B768C14E95A0` |
| `data.grf` | `6DCAE744FB8E5FC1FCAFBE8CFB3F5392E9D89B431E56811C3618462D5DE2D53A` |

Se houver divergência, classifique a instalação antes de prosseguir. Esses hashes
identificam os arquivos históricos; não garantem segurança nem compatibilidade
de qualquer versão nova. Preserve o resultado na pasta de evidências.

## Passo 4 — Backup e configuração na instalação existente

Por decisão do usuário em 2026-10-01, não é necessário copiar o diretório inteiro.
O fluxo vigente cria backup dos arquivos envolvidos e adiciona/atualiza o XML
na instalação existente. GRFs e executáveis não são modificados pelo script.

Use [configurar-cliente-windows.ps1](../scripts/configurar-cliente-windows.ps1)
no PowerShell 5.1+, a partir da raiz do repositório. Feche cliente e configurador.
Escolha uma pasta de backup NOVA, fora do cliente e do repositório, cujo diretório
pai já exista. Não sobrescreva nem reutilize backups.

```powershell
$clientBackup = Read-Host 'Caminho absoluto de uma NOVA pasta de backup'
.\scripts\configurar-cliente-windows.ps1 -BackupPath $clientBackup -WhatIf
.\scripts\configurar-cliente-windows.ps1 -BackupPath $clientBackup
```

A origem padrão é `C:\Gravity\Ragnarok`; ajuste `-ClientPath` se necessário.
Sem parâmetros XML, o script faz somente backup. Ele exige assinatura válida da
Gravity e o hash histórico do Ragexe. `-ExpectedExecutableSha256` só deve apontar
para outra baseline já identificada; não é correção automática de divergência.
`-WhatIf` valida as pré-condições sem escrita; não comprova espaço/permissões.

São preservados, quando presentes: `Ragexe.exe`, `Setup.exe`, `data.ini`,
`data/clientinfo.xml` e `data/sclientinfo.xml`. Todos os backups são conferidos
por SHA-256 antes da configuração. `data.grf`, músicas e demais assets não são
copiados. Links/junctions nos caminhos envolvidos são recusados.

### Adicionar ou atualizar o XML

Somente após confirmar os valores do passo 6, execute:

```powershell
$confirmedHost = Read-Host 'Host confirmado'
$confirmedService = Read-Host 'ServiceType confirmado'
$confirmedServer = Read-Host 'ServerType confirmado'
$confirmedVersion = [int](Read-Host 'Valor XML version confirmado')
$confirmedLang = [int](Read-Host 'LangType confirmado')
$confirmedFile = Read-Host 'Arquivo confirmado: clientinfo.xml ou sclientinfo.xml'
$clientBackup = Read-Host 'NOVA pasta de backup desta tentativa'
.\scripts\configurar-cliente-windows.ps1 -BackupPath $clientBackup `
  -ConnectionFile $confirmedFile -ServerHost $confirmedHost `
  -ServiceType $confirmedService -ServerType $confirmedServer `
  -ClientVersion $confirmedVersion -LangType $confirmedLang -WhatIf
# Apos conferir, repita o comando retirando somente -WhatIf.
```

O XML é escrito em UTF-8 na pasta `data` da instalação. `-LoginPort` tem padrão
6900; `-DisplayName`, FaithRO - Laus Deo. Outros valores exigem fornecimento
explícito. Não inclua senhas. Codificação, localização e leitura pelo executável
continuam pendentes de homologação. O script não aplica patches, não cria
`data.ini`, não executa cliente/Setup e não altera firewall, servidor ou GRFs.

`faithro-preparation.json` fica no backup, com hashes, arquivos novos e estado.
Sucesso é `PREPARED_NOT_PATCHED_NOT_LOGIN_VALIDATED`; falha é
`FAILED_CHECK_BACKUP_BEFORE_RETRY`. Em falha, preserve evidências e verifique o
XML: pode haver configuração parcial, mas o backup anterior permanece disponível.

**Rollback:** feche o cliente, restaure somente o XML anterior a partir do backup
verificado. Se ele não existia, remova apenas o arquivo novo indicado em
`new_files` da evidência. Remova `data` somente se criada nesta tentativa e vazia.
Não restaure executáveis/GRFs que não foram alterados; não há exclusão automática.

**Testes:** `powershell -NoProfile -File scripts/test-configurar-cliente-windows.ps1`
— 14 verificações aprovadas com arquivos sintéticos e assinatura simulada somente
na suíte. Nenhuma instalação real foi configurada. Teste manual pendente:
`-WhatIf` na instalação real, backup e comparação dos hashes; depois conferir
XML e rollback. Isso não comprova login.

## Passo 5 — Configurar vídeo e áudio

1. Abra `Setup.exe` **da instalação existente**.
2. Escolha opções disponíveis e compatíveis com a estação; para o primeiro teste,
   prefira modo janela e uma resolução suportada pelo configurador.
3. Salve e feche o configurador. Registre qualquer erro e os arquivos alterados.
4. O [OpenSetup na página oficial do autor](https://nn.ai4rei.net/dev/opensetup/)
   é alternativa documentada, mas não é dependência deste guia.
   Não substitua o configurador sem verificar origem, versão e licença.

## Passo 6 — Preparar a conexão com o FaithRO (pendente)

**Ponto de parada:** a instalação oficial não está pronta para conectar ao
FaithRO apenas por receber um XML. O executável original ainda aponta para a
infraestrutura oficial e sua leitura de configuração externa não foi homologada.

Antes de aplicar qualquer alteração na instalação:

1. Consulte o [repositório oficial do WARP](https://github.com/Neo-Mind/WARP)
   e a [revisão fixada pelo projeto](https://github.com/Neo-Mind/WARP/tree/9b1173e9e4e135c68e150704f01186ab5e763acd).
   Identifique e verifique a ferramenta, incluindo origem, versão, hash,
   licença e núcleo prebuilt. Auditoria estática não comprova prontidão no host.
2. Reconcilie o perfil de patches e comprove seu reconhecimento do executável real.
   `DataFolderFirst` e `CallKoreaClientInfo` são candidatos; `RestoreClientInfo`
   e `LangType` não devem ser aplicados por suposição. Registre a seleção exata.
3. Confirme se o cliente preparado lê `clientinfo.xml` ou `sclientinfo.xml`,
   sua localização, codificação, `servicetype`, `servertype`, `version` e `langtype`.
   O campo XML `version` não deve ser preenchido automaticamente com o PACKETVER
   sem comprovação da semântica usada pelo cliente.
4. Use [o template de conexão](../client/templates/clientinfo.xml.example)
   apenas como referência; todos os placeholders precisam de valores validados.
5. O endpoint histórico foi `129.121.46.11:6900`; confirme o endpoint vigente
   com o operador do servidor antes de produzir a configuração real.
6. Somente após essa validação, prepare a configuração após backup e registre as alterações e hashes.
   Qualquer patch binário exige procedimento próprio; o script não o aplica.

Não há comando ou sequência de cliques WARP homologados neste guia. Não faça
hex edit manual, injeção de DLL, bypass de anticheat ou desativação de Defender.
Não copie `data.ini.example` como configuração pronta: ele cita GRFs próprios
planejados e suporte a múltiplos GRFs que não são requisitos comprovados do teste.

## Passo 7 — Conferir rede e conta de teste

Com o endpoint confirmado, execute:

```powershell
$serverHost = Read-Host 'Host vigente confirmado pelo operador do FaithRO'
foreach ($gamePort in 6900, 6121, 5121) {
  Test-NetConnection -ComputerName $serverHost -Port $gamePort |
    Select-Object ComputerName, RemotePort, TcpTestSucceeded
}
```

As portas acima são a baseline registrada; confirme-as se a configuração mudou.
Se algum teste falhar, peça ao operador para conferir serviço e autorização do
IP atual. Não libere portas para qualquer origem nem altere firewall pelo guia.
MariaDB não precisa ficar acessível externamente. TCP aprovado ainda não é login.

Confirme a conta de homologação por canal adequado. A baseline do servidor tem
`new_account: no`: não tente criar conta com sufixos `_M`/`_F`. Não grave senhas
em XML, scripts, capturas ou documentação.

## Passo 8 — Primeiro acesso e evidências

Após concluir o passo 6, use o executável e o método de inicialização validados
na instalação configurada, mantendo o diretório de trabalho nela. Não use `Ragnarok.exe` como
launcher do FaithRO por suposição: esse é o launcher oficial.

| Checkpoint | Evidência mínima |
| --- | --- |
| H2 — Handshake | Pacote de login reconhecido pelo servidor |
| H3 — Autenticação | Conta de teste autenticada |
| H4 — Login → char | Acesso à seleção de personagens |
| H5 — Personagem | Selecionar ou criar personagem permitido |
| H6 — Char → map | Carregamento do mapa concluído |
| H7 — Dentro do jogo | Personagem visível, movimentação e interface funcionando |

Registre horário, versão/hash do cliente preparado, checkpoints, erros e logs
sanitizados. Não altere PACKETVER, limite de nível ou criptografia para mascarar
uma falha. A divergência base 255 × runtime 185 continua pendente de reconciliação;
esse teste não comprova progressão, balanceamento ou prontidão para alpha.

## Diagnóstico de falhas

| Sintoma | Próxima verificação |
| --- | --- |
| Arquivo ausente ou hash divergente | Origem, versão e integridade da instalação |
| Configurador/cliente não inicia | Mensagem exata, arquivos presentes e alertas de segurança; sem DLL avulsa |
| Cliente tenta conectar ao servidor oficial | Executável lançado, diretório de trabalho e leitura efetiva do XML |
| TCP falha | Endpoint, serviços e regra para o IP atual do operador |
| TCP passa, handshake falha | Protocolo, patches e configuração efetiva do cliente |
| Autenticação rejeitada | Conta, status e credenciais pelo operador; sem registrar senha |
| Login funciona, mapa falha | Handoff e conectividade das portas char/map; logs dos serviços |

## Arquivos afetados, riscos e rollback

A execução do script afeta somente o XML selecionado na instalação e o backup
local. Executáveis, GRFs e servidor permanecem inalterados. Falhas de escrita
podem deixar XML parcial; restaure a configuração conforme a evidência do backup.
Ferramentas futuras executadas no host podem afetar a estação; backup de arquivos
não oferece isolamento equivalente a VM. Não apague backups ou evidências.

## Checklist de conclusão

- [ ] Cliente de origem legítima identificado e assinatura/hash registrados.
- [ ] Backup dos arquivos envolvidos verificado antes da configuração.
- [ ] Ferramenta e perfil de preparação validados no host.
- [ ] Configuração de conexão efetivamente lida pelo cliente.
- [ ] Rede e conta de teste confirmadas.
- [ ] H2–H7 comprovados e logs sanitizados registrados.
- [ ] Executáveis/GRFs intactos; nenhum proprietário ou segredo no Git.

## Referências

### Links externos verificados em 2026-10-01

| Destino | Resultado da verificação | Limite |
| --- | --- | --- |
| [Downloads oficiais kRO/Gravity](https://ro.gnjoy.com/pds/down/) | Página de downloads lida | Versão atual não comprova compatibilidade com FaithRO |
| [Confirmação do download oficial](https://ro.gnjoy.com/ResService/game/download/gamedownloadpopupV2.asp?game=ro&type=exe) | HTTP 200 | Página de confirmação; não é o instalador histórico |
| [Instalador histórico RAG_SETUP_211105.exe](https://rofull.gnjoy.com/RAG_SETUP_211105.exe) | HEAD: HTTP 200; `application/x-msdownload`; nome confirmado em `Content-Disposition`; 3.427.631.040 bytes | Conteúdo não baixado; assinatura e hash local ainda devem ser conferidos |
| [OpenSetup — autor](https://nn.ai4rei.net/dev/opensetup/) | HTTP 200 e HTML identificado como RO OpenSetup | Nenhum pacote baixado ou homologado |
| [WARP — upstream](https://github.com/Neo-Mind/WARP) | Página do repositório lida | Disponibilidade não comprova segurança da ferramenta |
| [WARP — commit auditado](https://github.com/Neo-Mind/WARP/tree/9b1173e9e4e135c68e150704f01186ab5e763acd) | HTTP 200 | Preserva a referência; não autoriza usar a versão mais recente |

O servidor do instalador histórico declarou o metadado SHA-256
`d9067cc9ac62c85fa599ac94bbb19e9e96a1b7529181252806dc1df49e0293aa`.
Esse valor foi lido no cabeçalho HTTP, **não recalculado a partir do download**.
A acessibilidade dos links pode mudar; valide origem, assinatura e integridade
antes de executar qualquer arquivo. Nenhum mirror foi utilizado.

### Documentos e templates do projeto

- [Baseline e protocolo](09-cliente-baseline-protocolo.md).
- [Primeiro acesso planejado para jogadores](15-cliente-primeiro-acesso.md).
- [Política de distribuição](16-politica-distribuicao-cliente.md).
- [Identidade e compatibilidade do executável](29-compatibilidade-cliente-2021-11-05-packetver.md).
- [Resultados históricos do primeiro acesso](50-primeiro-acesso-cliente.md).
- [Decisão vigente sem VM](52-gate5-validacao-pos-snapshot-baseline-preparacao-cliente.md).
