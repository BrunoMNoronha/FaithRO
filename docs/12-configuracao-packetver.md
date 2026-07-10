# Procedimento Planejado: Configuração de PACKETVER, Obfuscação e Web Server

> **Escopo:** Procedimento documental.
> Nenhuma alteração técnica deve ser executada a partir deste documento de forma
> automática. As instruções a seguir constituem um plano futuro para o operador
> do FaithRO.

## Objetivo

Fornecer as instruções planejadas para configurar o protocolo (`PACKETVER`),
o alinhamento da packet obfuscation e a ativação do web server, garantindo a
compatibilidade entre o cliente de referência e o emulador rAthena, mantendo
a integridade do ambiente.

## Contexto e premissas

- Emulador: rAthena.
- O baseline atual adotado pelo projeto pretende `PACKETVER` 20211103.
- PACKETVER padrão identificado no código upstream consultado: 20211103.
- PACKETVER do checkout usado pelo FaithRO: pendente de validação.
- PACKETVER efetivamente compilado no binário da VPS: pendente de validação.
- **Permissões:** O operador deve possuir acesso seguro à VPS e aos utilitários de compilação.
- **Limitações:** O alinhamento de packet obfuscation e XML/Lua depende de um cliente
  obtido legalmente pelo responsável pelo FaithRO.

## Arquivos afetados

- **Diretórios e Arquivos:**
  - `src/custom/defines_pre.hpp`
  - `conf/import/web_conf.txt` (ou outro import adequado)
- **Serviços systemd:** `<UNIDADE-LOGIN>`, `<UNIDADE-CHAR>`, `<UNIDADE-MAP>`, `<UNIDADE-WEB>`
- **Portas:** Porta do web server (`8888/tcp` por padrão upstream, pendente de definição para o projeto).

## Passos

1. **Configuração futura de PACKETVER**
   O projeto adotará a configuração via customização, que é a mais rastreável.
   No diretório do repositório rAthena (`/opt/faithro/rathena`), verifique o arquivo `src/custom/defines_pre.hpp`.
   Adicione ou modifique a seguinte linha:
   ```cpp
   #define PACKETVER 20211103
   ```
   
   *Alternativa por argumento de compilação:*
   ```bash
   ./configure --enable-packetver=20211103
   ```

2. **Alinhamento de Packet Obfuscation**
   Confirme se a obfuscação requerida pelo cliente possui patches.
   Comportamento padrão da packet obfuscation: identificado no código upstream consultado (chaves zeradas no baseline).
   Configuração do checkout FaithRO: pendente de validação.
   Configuração do binário executado na VPS: pendente de validação.
   Alinhamento com o cliente de referência: pendente de teste com cliente obtido legalmente pelo responsável.

3. **Habilitação do Web Server**
   Suporte, macro e implementação do web server identificados no código upstream consultado.
   Estado do checkout FaithRO: pendente de validação.
   Estado de compilação, serviço, porta, tabelas e exposição na VPS: pendente de validação e implantação em tarefa própria.
   Prepare a configuração em `conf/import/web_conf.txt` e não exponha a porta diretamente para a internet.

4. **Compilação Limpa**
   Para aplicar o `PACKETVER`, é necessária uma compilação limpa.
   ```bash
   make clean
   ./configure
   make server
   ```

5. **Reinício de Serviços**
   Reinicie os serviços afetados utilizando os placeholders (ou os nomes reais já verificados):
   ```bash
   systemctl restart <UNIDADE-LOGIN>
   systemctl restart <UNIDADE-CHAR>
   systemctl restart <UNIDADE-MAP>
   systemctl restart <UNIDADE-WEB>
   ```

## Testes

1. Verifique se o login foi bem sucedido através da conexão do cliente (`<IP-CLIENTE>` autorizado).
2. Verifique os logs dos servidores (substitua pelo nome correto dos serviços):
   ```bash
   journalctl -u <UNIDADE-LOGIN> -n 50 --no-pager
   journalctl -u <UNIDADE-MAP> -n 50 --no-pager
   ```
3. Garanta o funcionamento base do cliente e do emulador.
4. Verifique a listagem e emblemas da guilda (dependência direta do web server).

## Riscos

- **Incompatibilidade de protocolo:** Resulta na desconexão imediata ou erros de pacotes se o cliente e o servidor possuírem versões distintas.
- **Divergência de Obfuscação:** Uma divergência entre a configuração de packet obfuscation do cliente e do servidor pode causar pacotes inválidos, falhas de interpretação, desconexão ou erros nos logs. A mensagem exata depende do pacote e do ponto da comunicação afetado.
- **Exposição do Web Server:** A porta do web server exposta sem restrições pode gerar riscos de negação de serviço.
- **Falha de compilação:** Pode ocorrer se overrides conflitantes forem declarados.

## Rollback

### Antes do merge
Fechar o PR sem merge e preservar ou excluir a branch somente após confirmar que nenhum trabalho adicional depende dela.
Para desfazer o commit na própria feature branch sem reescrever histórico:
```powershell
git switch docs/organizar-base-conhecimento-rathena
git revert <COMMIT>
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

## Referências

- [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md)
- [10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md)
- [Wiki oficial do rAthena](https://github.com/rathena/rathena/wiki)
