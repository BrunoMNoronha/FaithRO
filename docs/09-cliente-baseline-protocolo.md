# Cliente, protocolo e baseline de compatibilidade

> **Escopo:** documento de referência e planejamento. Nenhuma alteração de
> código, banco ou configuração operacional é executada por este documento.
> Todos os comandos de compilação e teste são **planejados para execução
> futura** por um operador humano, fora desta tarefa.

## Objetivo

Registrar, de forma rastreável, o cliente-alvo e o protocolo adotados pelo
FaithRO - Laos Deos, deixando explícita a diferença entre conceitos que são
frequentemente confundidos na comunidade (`Ragexe`, `PACKETVER_RE`, Renewal e
Pre-Renewal) e definindo o processo de validação de compatibilidade
cliente-servidor.

## Contexto e premissas

- Emulador: rAthena.
- Sistema: Ubuntu Server 22.04, MariaDB.
- **Commit upstream de referência:** `7f080871c8b3bbe7a79027194633201c63422ee1`
  (abreviado `7f080871c`). As afirmações "confirmado no código" deste documento
  foram verificadas **neste commit fixado** no GitHub (acesso em 2026-07-10).
- Este repositório é de **documentação/planejamento** e **não** contém um
  checkout do rAthena. Diferencie sempre os seguintes níveis de evidência:
  - **Comportamento no código oficial upstream do rAthena:** confirmado no código consultado (`7f080871c`).
  - **Estado do checkout utilizado pelo FaithRO:** pendente de validação (pois o core não está presente no workspace).
  - **Estado efetivamente compilado e executado na VPS:** pendente de validação (pois não há acesso ao ambiente Linux nesta missão).
- Terceiras classes: desabilitadas por decisão de conteúdo do FaithRO.
- Level máximo: 185, sujeito a balanceamento próprio (ver
  [00-base-conhecimento.md](00-base-conhecimento.md)).

## 1. Baseline do projeto

| Item | Valor |
| --- | --- |
| Cliente de referência | `2021-11-03_Ragexe` |
| Família adotada | `Ragexe` |
| PACKETVER pretendido | `20211103` |
| Modo Renewal ou Pre-Renewal | decisão independente do cliente e pendente de confirmação documental no FaithRO |
| Terceiras classes | desabilitadas por decisão do projeto |
| Level máximo planejado | 185, sujeito a balanceamento e validação próprios |

`2021-11-03_Ragexe` **não** é "o cliente mais novo". Ele é o **cliente de
referência / baseline conservador** adotado pelo projeto, escolhido por
alinhamento com o valor padrão do rAthena e com a matriz de CI oficial. Clientes
posteriores podem ter suporte parcial ou comunitário, mas **não** substituem o
baseline sem análise de compatibilidade, testes, decisão técnica, documentação e
plano de rollback. A compatibilidade funcional real depende de teste cliente-servidor.

## 2. Compatibilidade não é determinada só pelo nome

Deixe explícito no projeto:

- o nome do executável **não** garante compatibilidade;
- a data no nome do arquivo **não** garante compatibilidade;
- renomear o executável **não** altera o protocolo dele;
- um cliente mais novo **não** é automaticamente melhor nem compatível;
- o `PACKETVER` do servidor precisa corresponder à data e à estrutura de pacotes
  do cliente;
- a variante do executável (`Ragexe` vs `RagexeRE` etc.) precisa ser confirmada;
- a obfuscação de pacotes precisa estar alinhada entre cliente e servidor;
- os patches aplicados ao cliente precisam ser conhecidos e documentados;
- após qualquer mudança de protocolo, o servidor deve ser **recompilado de forma
  limpa** e reiniciado de forma controlada;
- dados, Lua, XML e configurações externas ao executável também podem causar
  falhas, mesmo com `PACKETVER` correto.

## 3. `Ragexe` versus `PACKETVER_RE`

Estes conceitos **não** são equivalentes:

- **`PACKETVER`** — data do protocolo de comunicação entre cliente e servidor.
  Para o baseline: `PACKETVER=20211103`.
- **`Ragexe`** — família do executável cliente adotado para 3 de novembro de
  2021. Identificação: `2021-11-03_Ragexe`.
- **`PACKETVER_RE`** — macro **interna** do código do rAthena, definida
  automaticamente para certas faixas de datas.

**Comportamento no código oficial upstream do rAthena:** confirmado no código consultado no commit `7f080871c`
([`src/config/packets.hpp`](https://github.com/rathena/rathena/blob/7f080871c8b3bbe7a79027194633201c63422ee1/src/config/packets.hpp)):

```c
#ifndef PACKETVER_RE
	#if ( PACKETVER > 20151104 && PACKETVER < 20180704 ) || ( PACKETVER >= 20200902 && PACKETVER <= 20211118 )
		#define PACKETVER_RE
	#endif
#endif
```

No código upstream consultado, o PACKETVER 20211103 está dentro do
intervalo inclusivo de 20200902 a 20211118 que cria internamente a macro
PACKETVER_RE. Essa macro é uma classificação interna do rAthena, não
transforma o executável em RagexeRE e não constitui uma regra aberta
para todas as versões posteriores a setembro de 2020.

- o cliente de referência continua sendo `2021-11-03_Ragexe` (família `Ragexe`);
- **não** se deve editar nem forçar manualmente `PACKETVER_RE` apenas para "fazer
  o nome parecer consistente".

> Não documente o cliente-alvo como `2021-11-03_RagexeRE` sem evidência concreta.
> Não há evidência técnica para isso; a variante adotada é `Ragexe`.

## 4. Renewal, Pre-Renewal e classes

- `PACKETVER` trata do **protocolo**.
- Renewal e Pre-Renewal tratam das **regras do servidor** (mecânicas, fórmulas).
- O mesmo `PACKETVER=20211103` pode ser compilado pelo rAthena em modo
  Pre-Renewal **ou** Renewal — a CI oficial compila ambos (ver
  [10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md)).
- Um cliente de 2021 **não** habilita, por si só, terceiras ou quartas classes.
- A ausência de terceiras classes é controlada **no servidor** (conteúdo e
  balanceamento), não pelo cliente.
- A presença de sprites, interfaces ou dados de 3ª classe no cliente **não**
  significa que o conteúdo esteja habilitado no servidor.
- O level 185 sem terceiras classes é uma customização do FaithRO e exige
  balanceamento próprio.

## 5. Packet obfuscation

A obfuscação é uma exigência de alinhamento entre cliente e servidor. Não se deve habilitar ou desabilitar automaticamente, nem registrar chaves reais.

- **Comportamento upstream:** suporte e regras identificados no código oficial consultado.
- **Checkout FaithRO:** pendente de validação.
- **Binário compilado na VPS:** pendente de validação.
- **Executável cliente e patches aplicados:** pendentes de validação.
- **Alinhamento cliente-servidor:** pendente de teste.

## 6. Web server do rAthena

- **Suporte, macro e implementação do web server:** identificados no código upstream consultado (em `src/config/packets.hpp`, existe `#define WEB_SERVER_ENABLE PACKETVER > 20200300`).
- **Estado do checkout FaithRO:** pendente de validação.
- **Estado de compilação, serviço, porta, tabelas e exposição na VPS:** pendente de validação e implantação em tarefa própria.

Não expor o serviço publicamente sem validação de riscos. O web server não é um requisito confirmado para login básico.

## 7. XML, Lua e configurações externas

Não assumir automaticamente qual arquivo o cliente lê (`clientinfo.xml`,
`sclientinfo.xml`, caminho em GRF ou arquivo Lua específico). Documentar somente o que
for **confirmado no cliente legalmente obtido pelo responsável**.

## 8. Patches do cliente

Registrar cada patch por nome e finalidade. **Não** apresentar uma lista genérica
de patches como universalmente correta.

| Patch | Obrigatório | Motivo | Risco | Resultado do teste |
| ----- | ----------- | ------ | ----- | ------------------ |
| Leitura da pasta `data` | Pendente | Pendente | Pendente | Pendente de validação |
| Leitura de arquivo XML | Pendente | Pendente | Pendente | Pendente de validação |
| Endereço de conexão | Pendente | Pendente | Pendente | Pendente de validação |
| Packet encryption | Pendente | Pendente | Pendente | Pendente de validação |
| Configurações externas e Lua | Pendente | Pendente | Pendente | Pendente de validação |
| Arquivos ausentes | Pendente | Pendente | Pendente | Pendente de validação |

## 9. Matriz de compatibilidade

| Componente            | Valor esperado         | Valor encontrado | Estado | Evidência |
| --------------------- | ---------------------- | ---------------- | ------ | --------- |
| Commit rAthena        | Estado confirmado      | Pendente         | pendente de validação | Requer acesso à VPS |
| `PACKETVER`           | `20211103`             | Pendente         | pendente de validação | Requer acesso à VPS |
| Família               | `Ragexe`               | Pendente         | pendente de validação | Requer teste real |
| Data do cliente       | `2021-11-03`           | Pendente         | pendente de validação | Requer teste real |
| Macro interna         | Conforme código        | `PACKETVER_RE`   | confirmado no código upstream | `src/config/packets.hpp` @ 7f080871c |
| Modo servidor         | Configuração FaithRO   | Pendente         | pendente de validação | Requer acesso à VPS |
| Packet obfuscation    | Pendente de alinhamento  | Pendente         | pendente de validação | Requer teste real e VPS |
| Arquivo XML/Lua       | Confirmado por teste   | Pendente         | pendente de validação | Requer teste real |
| Web server            | Confirmado ou pendente | Pendente         | pendente de validação e implantação | Tarefa própria |
| Login                 | Funcional              | Pendente         | pendente de validação | Requer teste cliente-servidor |
| Seleção de personagem | Funcional              | Pendente         | pendente de validação | Requer teste cliente-servidor |
| Entrada no mapa       | Funcional              | Pendente         | pendente de validação | Requer teste cliente-servidor |
| Movimento             | Funcional              | Pendente         | pendente de validação | Requer teste cliente-servidor |
| NPCs                  | Funcionais             | Pendente         | pendente de validação | Requer teste cliente-servidor |
| Inventário            | Funcional              | Pendente         | pendente de validação | Requer teste cliente-servidor |
| Guilda/emblema        | Funcional ou pendente  | Pendente         | pendente de validação | Requer teste cliente-servidor |

## 10. Plano mínimo de testes (planejado)

Portas de referência do projeto (padrão rAthena; confirmar na implantação):
login `<PORTA>`, char `<PORTA>`, map `<PORTA>`; web server `<PORTA>`.
As portas efetivas estão pendentes de validação. Durante os testes, não abrir a
conexão globalmente. Usar `<IP-CLIENTE>` restrito.

### Inicialização
- abertura do executável;
- DLLs ausentes;
- encerramento imediato;
- janela e resolução;
- mensagens de erro.

### Conexão
- conexão com `<IP-VPS>:<PORTA>`;
- tentativa registrada no login-server;
- ausência de encerramento por divergência de protocolo;
- comportamento diante de credenciais inválidas;
- reconexão.

### Personagem e mapa
- lista de personagens;
- criação, quando permitida;
- seleção;
- conexão com char-server;
- conexão com map-server;
- entrada no mapa;
- movimento;
- NPCs e itens funcionam;
- inventário abre;
- chat.

### Recursos adicionais
- grupo, guilda, emblema, armazém, comércio, atalhos, interface, tradução, reconexão.

## 11. Riscos

- Indisponibilidade por erro de conexão.
- Uma divergência entre a configuração de packet obfuscation do cliente e do servidor pode causar pacotes inválidos, falhas de interpretação, desconexão ou erros nos logs. A mensagem exata depende do pacote e do ponto da comunicação afetado.
- Perda de configuração de baseline em recompilações futuras.
- Manutenção futura dificultada por uso de binários sem suporte.

## 12. Rollback

### Antes do merge
Fechar o PR sem merge e preservar ou excluir a branch somente após confirmar que nenhum trabalho adicional depende dela.
Para desfazer o commit na própria feature branch sem reescrever histórico:
```powershell
git switch docs/organizar-base-conhecimento-rathena
git revert --no-commit 6ef5602^..fabe0ff
git commit -m "revert: desfaz organização da base rAthena"
git push
```

### Depois de merge tradicional
Identificar e reverter o merge commit criado na branch de destino:
```powershell
git log --oneline --merges dev
git revert -m 1 <COMMIT-DE-MERGE>
```

### Depois de squash merge
Identificar e reverter o commit squash criado em `dev`:
```powershell
git log --oneline dev
git revert <COMMIT-SQUASH>
```

### Alterações ainda não commitadas
Somente nesse caso, restaurar os arquivos modificados:
```powershell
git restore -- `
  docs/00-base-conhecimento.md `
  docs/09-cliente-baseline-protocolo.md `
  docs/10-fontes-comunitarias-rathena.md
```
Para um novo arquivo não rastreado:
```powershell
Remove-Item docs\12-configuracao-packetver.md
```

## 13. Referências

Ver a classificação detalhada de fontes e documentação comunitária em [10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md).
