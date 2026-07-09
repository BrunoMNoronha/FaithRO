# Fluxo de Pull Request

## Objetivo

Definir um fluxo simples e seguro de contribuição para o FaithRO, garantindo que toda mudança passe por uma branch de tarefa, seja revisada via Pull Request e só chegue em `main` de forma rastreável e reversível.

## Quando usar `main`

- `main` é a base estável do projeto.
- Recebe apenas merges de `dev` (ou de branches de tarefa, em casos pontuais) já revisados.
- Nunca deve receber commits diretos de trabalho em andamento.
- Representa o estado "pronto para referência" da documentação/configuração do projeto.

## Quando usar `dev`

- `dev` é a branch de desenvolvimento integrado.
- Recebe merges das branches de tarefa.
- É o ponto de partida para novas branches de tarefa.
- Pode ser enviada (`push`) ao repositório remoto para acompanhamento, mas segue instável até virar PR para `main`.

## Quando criar branches de tarefa

Crie uma branch de tarefa sempre que for trabalhar em um item específico do backlog (ver `docs/06-plano-execucao-inicial.md` e `scripts/criar-issues-iniciais.md`), a partir de `dev`:

```
git checkout dev
git pull
git checkout -b <tipo>/<nome-da-tarefa>
```

## Padrão recomendado de branches

- `docs/nome-da-tarefa`
- `infra/nome-da-tarefa`
- `config/nome-da-tarefa`
- `emulador/nome-da-tarefa`

## Padrão de commits

- `docs: ...` — documentação.
- `chore: ...` — tarefas auxiliares, scripts, organização.
- `infra: ...` — infraestrutura (VPS, firewall, backups).
- `config: ...` — configuração de gameplay/emulador.
- `fix: ...` — correção de bug ou erro.

## Checklist antes de abrir Pull Request

- [ ] Branch de tarefa criada a partir de `dev` atualizada.
- [ ] Nenhum arquivo sensível incluído (`.env`, chaves SSH, dumps reais, backups reais, dados de jogadores).
- [ ] Nenhum cliente, GRF, executável, DLL ou asset proprietário incluído.
- [ ] Commits seguem o padrão de prefixo (`docs:`, `chore:`, `infra:`, `config:`, `fix:`).
- [ ] Descrição do PR preenchida com objetivo, arquivos afetados, passos, testes, riscos e rollback.
- [ ] `git status` e `git diff` revisados antes do push.

## Checklist antes de fazer merge

- [ ] PR revisado por pelo menos uma pessoa (ou autorrevisão cuidadosa em fase solo).
- [ ] Testes/validações descritos no PR foram executados.
- [ ] Riscos e rollback documentados e entendidos.
- [ ] Nenhuma alteração no core do emulador sem discussão prévia.
- [ ] Checklist de segurança do PR (ver `docs/templates/PULL_REQUEST_TEMPLATE.md`) conferida.

## Riscos

- Risco de misturar mudanças de escopos diferentes em uma única branch/PR, dificultando revisão e rollback.
- Risco de branches de tarefa desatualizadas em relação a `dev`, gerando conflitos.
- Risco baixo de vazamento de dados sensíveis se o checklist de segurança não for seguido.

## Rollback

- Antes do merge: fechar o PR sem merge e, se necessário, apagar a branch de tarefa.
- Depois do merge em `dev`: reverter o commit de merge (`git revert -m 1 <hash>`) ou criar um novo PR de correção.
- Depois do merge em `main`: preferir sempre um novo PR de reversão a um `git push --force`, para manter o histórico rastreável.

## Observação de segurança

Nunca incluir em nenhuma branch, commit ou Pull Request: cliente, GRF, executáveis, DLLs, assets proprietários ou sem licença, senhas, tokens, chaves SSH, dumps reais de banco de dados, backups reais ou dados de jogadores.
