# `docs/21-plano-instalacao-toolchain-rust-beam.md` — Plano de Instalação Isolada da Toolchain Rust 1.85.0

> **Status:** PLANEJADO / DOCUMENTADO (ETAPA 2O-D1-B4)  
> **Data:** 2026-07-25  
> **Toolchain Ativa Conservada:** `1.77.2-x86_64-pc-windows-msvc`  
> **Toolchain Candidata Planejada:** `1.85.0-x86_64-pc-windows-msvc`  
> **Instalação Autorizada:** `NÃO` (exige autorização humana prévia para etapa posterior)  
> **Build Autorizado:** `NÃO`

---

## 1. Objetivo

Apresentar o plano técnico, seguro, reproduzível e reversível para a **futura instalação isolada** da toolchain Rust `1.85.0-x86_64-pc-windows-msvc`, necessária para a futura compilação auditável do Beam Patcher (demonstrada nas ETAPAS 2O-D1-B1 a 2O-D1-B3).

O objetivo central é garantir a **coexistência pacífica** com a toolchain já instalada (`1.77.2-x86_64-pc-windows-msvc`), garantindo que nenhuma alteração global, de variáveis de ambiente permanentes ou da toolchain padrão (`default`) ocorra no ambiente de desenvolvimento.

---

## 2. Inventário do Ambiente (Somente Leitura)

Conforme verificado estaticamente na ETAPA 2O-D1-B4:

- **Sistema Operacional**: Windows 11 (build 10.0.26200), 64-bit AMD64.
- **Processo Shell**: PowerShell 64-bit, privilégios normais (**não elevado**).
- **Espaço em Disco Livre**: `116.18 GB` livres no volume `%USERPROFILE%` (requisito mínimo: 5 GB).
- **Gerenciador de Toolchains (`rustup`)**: `1.29.0`.
- **Toolchain Ativa e Padrão**: `1.77.2-x86_64-pc-windows-msvc`.
- **Toolchains Instaladas**: Apenas `1.77.2-x86_64-pc-windows-msvc`.
- **Toolchain Candidata 1.85.0**: **Ausente** (confirmado que não está instalada).
- **Overrides Locais**: Nenhum override ativo no repositório.

---

## 3. Estratégia de Coexistência (Toolchains Nomeadas)

A futura instalação utilizará **estritamente toolchains nomeadas**, sem modificar a toolchain padrão do sistema nem criar overrides permanentes no repositório.

### Diretrizes Obrigatórias
1. **Toolchain Padrão Intacta**: O comando `rustup default` **jamais** será alterado para `1.85.0`. A toolchain `1.77.2` continuará sendo a padrão global.
2. **Uso de Toolchain Nomeada Explicita**: Qualquer invocação futura da Rust `1.85.0` usará os prefixos:
   ```powershell
   rustup run 1.85.0-x86_64-pc-windows-msvc rustc --version
   cargo +1.85.0-x86_64-pc-windows-msvc <COMANDO>
   ```
3. **Sem Variáveis de Ambiente Permanentes**: Nenhuma alteração no `%PATH%` ou no registro do Windows será realizada.
4. **Sem Arquivos de Override no Git**: Não serão adicionados arquivos `rust-toolchain` ou `rust-toolchain.toml` ao repositório FaithRO.

---

## 4. Comando Futuro de Instalação (Perfil Mínimo)

O comando planejado para execução em etapa futura autorizada é:

```powershell
rustup toolchain install 1.85.0-x86_64-pc-windows-msvc --profile minimal
```

### Componentes Incluídos no Perfil Minimal
- `rustc` (compilador Rust versionado)
- `cargo` (gerenciador de pacotes)
- `rust-std-x86_64-pc-windows-msvc` (biblioteca padrão para o target host)

### Componentes Excluídos Inicialmente
- `rustfmt` (não essencial para build pré-homologado)
- `clippy` (não essencial para build pré-homologado)
- `llvm-tools` (não essencial)
- `nightly` (proibido)

---

## 5. Pré-Checks de Instalação (17 Gates Executáveis)

Antes de executar qualquer comando de instalação em uma etapa futura, todos os 17 gates abaixo deverão ser confirmados com sucesso:

1. **Working Tree Limpa**: `git status --short` retorna vazio.
2. **Branch Correta**: Ativo na branch autorizada da etapa.
3. **Sem Operações Pendentes**: Ausência de merge/rebase/cherry-pick pendentes.
4. **PowerShell Não Elevado**: Confirmado que o processo não roda como Administrador.
5. **Rust 1.77.2 Operacional**: `rustc --version` e `cargo --version` funcionam normalmente.
6. **Rust 1.85.0 Ausente**: Confirmado por `rustup toolchain list` que `1.85.0` não consta na lista.
7. **Espaço Livre em Disco**: Mais de 5 GB disponíveis no volume do `%USERPROFILE%`.
8. **Conectividade HTTPS Oficial**: Acesso a `static.rust-lang.org` e `crates.io`.
9. **Certificado TLS Válido**: Sem bypass ou desabilitação de SSL.
10. **Rustup Operacional**: `rustup --version` responde sem erro.
11. **Visual Studio Build Tools Presente**: Compilador C/C++ MSVC e ferramentas `vswhere.exe` detectadas.
12. **Windows SDK Presente**: Bibliotecas nativas do Windows de 64 bits instaladas.
13. **Sem Build Ativo**: Nenhum processo `cargo`, `rustc` ou `beam` em execução.
14. **Sem Processo Cargo Concorrente**: Verificado no Gerenciador de Tarefas / `Get-Process`.
15. **Diretórios Temporários Válidos**: `%TEMP%` acessível e gravável.
16. **Plano de Rollback Pronto**: Script e comandos de remoção validados.
17. **Autorização Humana Registrada**: Aprovação prévia e explícita do usuário.

---

## 6. Validações Pós-Instalação Futuras

Imediatamente após a instalação futura, a verificação deverá confirmar:

```powershell
rustup toolchain list
rustup run 1.85.0-x86_64-pc-windows-msvc rustc --version --verbose
rustup run 1.85.0-x86_64-pc-windows-msvc cargo --version --verbose
rustup run 1.77.2-x86_64-pc-windows-msvc rustc --version --verbose
rustup run 1.77.2-x86_64-pc-windows-msvc cargo --version --verbose
```

Critérios de Aceito:
- Toolchain `1.85.0-x86_64-pc-windows-msvc` listada como instalada.
- Toolchain `1.77.2-x86_64-pc-windows-msvc` continua como `(active, default)`.
- Nenhuma alteração no arquivo de ambiente do usuário.

---

## 7. Procedimento e Gatilhos de Rollback

### Comando de Rollback
Caso qualquer anomalia seja detectada durante ou após a instalação futura, o rollback será executado pelo comando:

```powershell
rustup toolchain uninstall 1.85.0-x86_64-pc-windows-msvc
```

### Gatilhos Automáticos de Rollback
1. Versão instalada pelo `rustup` diferente de `1.85.0`.
2. Target/host instalado diferente de `x86_64-pc-windows-msvc`.
3. Ausência do `cargo` na toolchain 1.85.0.
4. Alteração indevida da toolchain padrão (`default` modificada).
5. Remoção ou corrupção da toolchain `1.77.2`.
6. Instalação parcial por falha de rede ou interrupção.

---

## 8. Artefatos Versionados nesta Etapa

- **Schema JSON**: [`client/patcher/beam-audit/schemas/toolchain-installation-plan.schema.json`](../client/patcher/beam-audit/schemas/toolchain-installation-plan.schema.json)
- **Plano JSON**: [`client/patcher/beam-audit/toolchain-installation-plan.example.json`](../client/patcher/beam-audit/toolchain-installation-plan.example.json)
- **Validador em Python**: [`scripts/validate-beam-toolchain-installation-plan.py`](../scripts/validate-beam-toolchain-installation-plan.py)
- **Workflow de CI**: [`.github/workflows/validate-beam-toolchain-installation-plan.yml`](../.github/workflows/validate-beam-toolchain-installation-plan.yml)

---

## 9. Declarações Finais de Conformidade

- **Nenhuma ferramenta foi instalada nesta etapa.**
- **Nenhuma toolchain foi alterada** (Rust `1.77.2` permanece ativa e padrão).
- **Rust `1.85.0` não foi instalada.**
- **Nenhum override de toolchain foi criado.**
- **Nenhum build foi iniciado.**
- **Nenhum binário foi produzido ou executado.**
- **Nenhuma dependência foi modificada.**
- **Nenhum `Cargo.lock` foi criado ou versionado.**
- **Nenhum deploy foi realizado.**
- **A VPS não foi acessada.**
- **O Windows Defender não foi desabilitado.**
