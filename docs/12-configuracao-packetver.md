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
- O baseline atual adotado pelo projeto requer `PACKETVER` configurado como `20211103`.
- A variante de obfuscação para o cliente de referência pressupõe alinhamento (chaves zero, no baseline).
- O web server requer configuração específica e deve ser testado.
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
   Confirme se a obfuscação requerida pelo cliente possui patches. Para o baseline `20211103`,
   as chaves padrão do rAthena são zero e o suporte base é ativado pelas macros de código.
   Alinhe o patch do cliente ("Disable Packet Encryption") de acordo com o comportamento testado.

3. **Habilitação do Web Server**
   O código do rAthena ativa o web server automaticamente via `WEB_SERVER_ENABLE` para este `PACKETVER`.
   Prepare a configuração em `conf/import/web_conf.txt` e não exponha a porta diretamente para a internet 
   sem a configuração de segurança adequada.

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
3. Garanta que o console não registre "Unknown Packet Version".
4. Verifique a listagem e emblemas da guilda (dependência direta do web server).

## Riscos

- **Incompatibilidade de protocolo:** Resulta na desconexão imediata ou erros de pacotes se o cliente e o servidor possuírem versões distintas.
- **Exposição do Web Server:** A porta do web server exposta sem restrições pode gerar riscos de negação de serviço.
- **Falha de compilação:** Pode ocorrer se overrides conflitantes forem declarados.

## Rollback

1. **Restauração:** Não dependa de backup inexistente. Antes da modificação (Passo 1), crie uma cópia de segurança do binário anterior:
   ```bash
   cp login-server login-server.bak
   cp char-server char-server.bak
   cp map-server map-server.bak
   cp web-server web-server.bak
   ```
2. **Reversão:** Reverta `src/custom/defines_pre.hpp` e recompile limpamente (`make clean && make server`), ou simplesmente restaure os binários da extensão `.bak` e reinicie os serviços, caso a falha impeça a execução.
3. **Verificação final:** Execute os passos da seção de Testes para confirmar que o ambiente voltou ao estado original.

## Referências

- [09-cliente-baseline-protocolo.md](09-cliente-baseline-protocolo.md)
- [10-fontes-comunitarias-rathena.md](10-fontes-comunitarias-rathena.md)
- [Wiki oficial do rAthena](https://github.com/rathena/rathena/wiki)
