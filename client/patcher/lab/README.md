# `client/patcher/lab/` — execução do laboratório sintético

> Esta pasta **não** contém o laboratório executável. O laboratório é sempre
> gerado em um diretório **temporário e descartável fora do repositório**. Aqui
> ficam apenas as instruções de execução. Nenhum binário, GRF, pacote de patch ou
> asset proprietário é versionado. Ver
> [`docs/18-homologacao-patch-sintetico-beam.md`](../../../docs/18-homologacao-patch-sintetico-beam.md)
> e [`../fixtures/synthetic/README.md`](../fixtures/synthetic/README.md).

## Pré-requisitos

- Apenas Python 3 da biblioteca padrão (já disponível no ambiente). **Não**
  instalar Rust, Node.js, Tauri, Build Tools nem servidor web.
- Não executar como administrador; não desabilitar TLS/antivírus; não abrir
  firewall; não acessar a VPS.

## Passo a passo

```bash
# 1) diretório temporário descartável (fora do repositório)
TEMP_DIR="$(python -c 'import tempfile,pathlib;print(pathlib.Path(tempfile.mkdtemp(prefix="faithro-beam-lab-")).as_posix())')"

# 2) gerar o laboratório sintético
python scripts/generate-synthetic-patch-lab.py --output "$TEMP_DIR/lab"

# 3) validar (integridade SHA-256 + invariantes + simulador do laboratório)
python scripts/validate-synthetic-patch-lab.py --root "$TEMP_DIR/lab"

# 4) testes negativos de segurança (nenhum deve passar)
python scripts/validate-synthetic-patch-lab.py --self-test

# 5) (opcional) servir por loopback e baixar o payload
python -m http.server 0 --bind 127.0.0.1 --directory "$TEMP_DIR/lab/server"

# 6) remover o laboratório temporário ao final
rm -rf "$TEMP_DIR"
```

## Regras de segurança da execução

- Servidor HTTP **somente** em `127.0.0.1`, porta dinâmica, servindo apenas
  `…/lab/server`; nunca `0.0.0.0`/`::` e nunca a raiz do repositório.
- Nenhum executável é lançado após o patch; não há SSO nem auto-update.
- O executor de aplicação é o **simulador do laboratório** (não é o Beam); a
  execução dinâmica do Beam está `BLOQUEADO — TOOLCHAIN DO BEAM NÃO DISPONÍVEL`.
- Encerrar o servidor HTTP e remover o diretório temporário ao final.
