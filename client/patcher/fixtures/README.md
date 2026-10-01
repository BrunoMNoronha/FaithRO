# Fixtures de laboratório sintético do patcher

> Conteúdo **100% sintético e textual**, para testar um patcher **sem** cliente
> real, sem `Ragexe`, sem `data.grf`/`rdata.grf`, sem OpenSetup e sem qualquer
> asset da Gravity. Nenhum binário é versionado aqui. Ver
> [`docs/17-decisao-patcher-launcher.md`](../../../docs/17-decisao-patcher-launcher.md).

## Homologação sintética executável (ETAPA 2O-D)

A homologação do **fluxo conceitual** do Beam (gerador determinístico, servidor
loopback, integridade SHA-256, simulador de aplicação e testes negativos) está em
[`synthetic/`](synthetic/README.md) e documentada em
[`docs/18-homologacao-patch-sintetico-beam.md`](../../../docs/18-homologacao-patch-sintetico-beam.md).

```bash
python scripts/generate-synthetic-patch-lab.py --output <DIR_TEMPORARIO>/lab
python scripts/validate-synthetic-patch-lab.py --root <DIR_TEMPORARIO>/lab
python scripts/validate-synthetic-patch-lab.py --self-test
```

Distinção obrigatória: o patch de `synthetic/` é um **manifesto conceitual**
(`FORMATO CONCEITUAL — NÃO CONSUMÍVEL PELO BEAM`) e é aplicado pelo **simulador do
laboratório**, nunca pelo Beam. A execução dinâmica do Beam está
`BLOQUEADO — TOOLCHAIN DO BEAM NÃO DISPONÍVEL`.

O plano G1–G15 abaixo é o roteiro histórico com o binário do patcher; a matriz
efetivamente executada nesta etapa está em docs/18.

## Estado dos testes dinâmicos

Os testes G1–G15 abaixo **ainda não foram executados**. Motivo registrado
honestamente: o candidato principal (Beam Patcher) exige toolchain Rust
1.75+/Tauri para compilar, e a etapa de homologação **proíbe instalar
runtimes/servidor web**; além disso, evitou-se executar um binário de terceiros
ainda não auditado integralmente. Esta pasta versiona a **estrutura** e o **plano
de testes** para execução em etapa futura, em ambiente próprio.

## Estrutura de laboratório (conceitual, fora do repositório)

O laboratório real deve ser criado **fora** do repositório e fora de qualquer
instalação de cliente:

```text
faithro-patcher-lab/
├── client-root/            # raiz do "cliente" sintético
│   ├── version.txt         # começa em "1"
│   ├── faithro-lab.grf     # GRF sintético gerado no lab (NÃO versionar)
│   └── data/
│       └── synthetic.txt
├── patch-server/           # servido em http://127.0.0.1:8000 (loopback)
│   ├── patchlist.txt
│   ├── version.json
│   └── files/              # patches sintéticos (.beam/.thor) gerados no lab
├── outside-root/
│   └── must-not-change.txt # canário do teste de path traversal (G9)
├── logs/
└── backup/                 # cópia para rollback operacional (G14)
```

### Servidor HTTP local

Servir **apenas** em `127.0.0.1`, sem expor porta à rede e sem abrir firewall.
Preferir uma ferramenta **já disponível** no ambiente (ex.: `python -m http.server
8000 --bind 127.0.0.1`, usando o Python da biblioteca padrão já presente). **Não**
instalar Python/Node/Rust/.NET/servidor web/gerenciadores de pacote para isto. Se
não houver forma segura de servir localmente, registrar
`BLOQUEADO — SERVIDOR DE TESTE LOCAL INDISPONÍVEL` e concluir apenas a auditoria
estática.

## Plano de testes G1–G15

| Teste | O que validar | Critério de aprovação |
| --- | --- | --- |
| G1 — Atualização inicial | `version.txt` 1→2; novo arquivo criado; hash final confere | Atualiza e verifica hash |
| G2 — Idempotência | Reexecutar não corrompe; sem download desnecessário | Estado estável |
| G3 — Arquivo local corrompido | Alterar arquivo local; detectar e reparar | Detecta por hash (não só por número) |
| G4 — Patch corrompido no servidor | Alterar conteúdo servido sem atualizar checksum | **Rejeita** (senão, reprova integridade) |
| G5 — Interrupção durante escrita | Interromper e reiniciar | Retoma; sem arquivo final parcial |
| G6 — Arquivo de destino bloqueado | Manter arquivo aberto | Erro claro; sem estado inconsistente |
| G7 — Falha de rede | Parar o servidor | Erro seguro; **não** lança cliente após patch incompleto |
| G8 — HTTP 404 | Remover um patch do servidor | Ausência tratada como erro; sem sucesso parcial silencioso |
| G9 — **Path traversal** | Patch tenta gravar `../outside-root/must-not-change.txt`, `..\outside-root\...` e caminho absoluto sintético | `must-not-change.txt` **inalterado**; senão `REPROVADO — PATH TRAVERSAL CONFIRMADO` |
| G10 — Subdiretórios | Criar arquivos em subpastas válidas | Ficam dentro de `client-root` |
| G11 — Espaços e Unicode | `data/teste com espaço.txt`, `data/acentuação-faithro.txt` | Tratados corretamente |
| G12 — Launcher sintético | Processo benigno cria `launch-marker/launched.txt` | Lança só após patch OK; argumentos preservados; sem shell injection |
| G13 — Segunda instância | Abrir duas instâncias | Lock/concorrência; sem escrita simultânea |
| G14 — Rollback | Aplicar update e restaurar backup | Volta ao estado anterior; registrar se é nativo ou operacional |
| G15 — Logs | Inspecionar logs | Sem senha, token, caminho pessoal, parâmetro sensível ou dado de conta |

> Regras de execução: não rodar como administrador; não desativar antivírus; não
> adicionar exclusões; não usar credenciais; não habilitar SSO; não apontar para
> executável real do cliente.

## Arquivos sintéticos versionados nesta pasta

- [`patchlist.example.txt`](patchlist.example.txt) — patchlist de exemplo (nome +
  SHA-256 por linha).
- [`version.example.json`](version.example.json) — `version.json` sintético do
  self-updater.

Os patches em si (`.beam`/`.thor`) e o `faithro-lab.grf` são **gerados no
laboratório** e **não** são versionados (bloqueados por `.gitignore`).
</content>
