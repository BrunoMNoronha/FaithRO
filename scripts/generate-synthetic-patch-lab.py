#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador determinístico do laboratório sintético do patcher (ETAPA 2O-D).

Materializa, em um diretório de saída EXPLÍCITO e descartável, um laboratório
100% sintético para exercitar o fluxo conceitual do Beam Patcher:

    manifesto -> servidor HTTP loopback -> download -> verificação de integridade
    -> aplicação em diretório sintético -> validação do estado final

IMPORTANTE — FORMATO CONCEITUAL:
  O "patch" gerado NÃO é um pacote .beam/.thor/.rgz/.gpf real. O formato binário
  oficial do Beam não foi confirmado a partir do fonte fixado (toolchain Rust
  ausente neste ambiente; ver docs/18). Por isso o payload é um MANIFESTO JSON
  conceitual mais os arquivos de conteúdo servidos por loopback. Todo artefato é
  marcado com:  FORMATO CONCEITUAL — NÃO CONSUMÍVEL PELO BEAM.
  É proibido renomear estes artefatos para extensões reais do Beam.

Garantias:
  - Somente biblioteca padrão do Python.
  - Resolve caminhos por __file__; independe do CWD.
  - Não acessa a rede.
  - Não grava fora do --output informado.
  - Recusa --output igual à raiz do repositório ou dentro de .git.
  - Recusa componentes '..' no --output.
  - Conteúdo determinístico: ordenado, UTF-8, LF, sem timestamps variáveis.
  - SHA-256 é o controle de integridade primário.
  - Não gera executáveis, GRFs, ZIPs ou pacotes proprietários.

Uso:
    python scripts/generate-synthetic-patch-lab.py --output <DIR>
    python scripts/generate-synthetic-patch-lab.py --output <DIR> --clean
"""
import argparse
import hashlib
import json
import os
import shutil
import sys

# Saída sempre em UTF-8, independentemente do console (Windows cp1252 etc.).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONCEPTUAL_FORMAT = "FORMATO CONCEITUAL — NÃO CONSUMÍVEL PELO BEAM"
LAB_MARKER = "LAB-METADATA.json"

# --------------------------------------------------------------------------
# Conteúdo sintético canônico (determinístico). LF garantido na escrita.
# --------------------------------------------------------------------------

SETTINGS_BEFORE = {
    "environment": "synthetic-lab",
    "feature_flag": False,
    "server": "FaithRO - Laos Deos",
}
SETTINGS_AFTER = {
    "environment": "synthetic-lab",
    "feature_flag": True,
    "server": "FaithRO - Laos Deos",
}
VERSION_BEFORE = "0\n"
VERSION_AFTER = "1\n"
OBSOLETE_TEXT = (
    "Este arquivo sintético deve ser removido pelo cenário de atualização.\n"
)
WELCOME_TEXT = "Bem-vindo ao laboratório sintético do FaithRO.\n"


def _settings_bytes(data):
    """JSON determinístico: chaves ordenadas, indentação fixa, LF, newline final."""
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    return (text + "\n").encode("utf-8")


# Estado inicial (target-before): mapeia caminho relativo (posix) -> bytes.
def target_before_files():
    return {
        "config/faithro-settings.json": _settings_bytes(SETTINGS_BEFORE),
        "data/version.txt": VERSION_BEFORE.encode("utf-8"),
        "data/obsolete.txt": OBSOLETE_TEXT.encode("utf-8"),
    }


# Estado final esperado (target-after).
def target_after_files():
    return {
        "config/faithro-settings.json": _settings_bytes(SETTINGS_AFTER),
        "data/version.txt": VERSION_AFTER.encode("utf-8"),
        "data/welcome.txt": WELCOME_TEXT.encode("utf-8"),
    }


# Payload do patch: conteúdo NOVO para ações create/update (servido por loopback).
def patch_payload_files():
    return {
        "config/faithro-settings.json": _settings_bytes(SETTINGS_AFTER),
        "data/version.txt": VERSION_AFTER.encode("utf-8"),
        "data/welcome.txt": WELCOME_TEXT.encode("utf-8"),
    }


# Ações do patch conceitual. Ordenadas deterministicamente por (op, path).
def patch_actions():
    return [
        {"op": "update", "path": "config/faithro-settings.json"},
        {"op": "update", "path": "data/version.txt"},
        {"op": "create", "path": "data/welcome.txt"},
        {"op": "remove", "path": "data/obsolete.txt"},
    ]


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def die(msg, code=2):
    sys.stderr.write("ERRO: " + msg + "\n")
    sys.exit(code)


def write_file(base, relpath, data):
    """Grava `data` em base/relpath criando diretórios. relpath é posix."""
    parts = relpath.split("/")
    target = os.path.join(base, *parts)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "wb") as f:
        f.write(data)


def sorted_items(mapping):
    return [(k, mapping[k]) for k in sorted(mapping)]


# --------------------------------------------------------------------------
# Validação do diretório de saída (segurança)
# --------------------------------------------------------------------------

def resolve_output(raw):
    if raw is None or raw.strip() == "":
        die("--output vazio não é permitido.")
    # Recusa componentes de traversal antes de normalizar.
    norm = raw.replace("\\", "/")
    for comp in norm.split("/"):
        if comp == "..":
            die("--output não pode conter componente '..' (traversal): %s" % raw)
    out = os.path.abspath(raw)
    repo_real = os.path.realpath(REPO)
    out_real = os.path.realpath(out) if os.path.exists(out) else out
    if os.path.normcase(out_real) == os.path.normcase(repo_real):
        die("--output não pode ser a raiz do repositório.")
    # Não gravar dentro de .git.
    git_dir = os.path.join(repo_real, ".git")
    if os.path.normcase(out_real).startswith(os.path.normcase(git_dir + os.sep)):
        die("--output não pode ficar dentro de .git.")
    return out


def prepare_output(out, clean):
    if os.path.exists(out):
        if not os.path.isdir(out):
            die("--output existe e não é um diretório: %s" % out)
        non_empty = bool(os.listdir(out))
        if non_empty:
            if not clean:
                die("--output não está vazio. Use --clean para regenerar "
                    "(somente labs marcados por %s são removidos)." % LAB_MARKER)
            # Segurança: só limpar diretórios que sejam claramente um lab nosso.
            marker = os.path.join(out, LAB_MARKER)
            if not os.path.exists(marker):
                die("--clean recusado: %s não contém %s; não vou remover um "
                    "diretório que não foi criado por este gerador."
                    % (out, LAB_MARKER))
            shutil.rmtree(out)
    os.makedirs(out, exist_ok=True)


# --------------------------------------------------------------------------
# Geração
# --------------------------------------------------------------------------

def build_manifest(payload):
    """Constrói o manifesto conceitual com SHA-256 e tamanho por ação."""
    payload_hashes = {p: (sha256_bytes(b), len(b)) for p, b in payload.items()}
    actions_out = []
    for act in patch_actions():
        op = act["op"]
        path = act["path"]
        entry = {"op": op, "path": path}
        if op in ("create", "update"):
            if path not in payload_hashes:
                die("payload ausente para ação %s %s" % (op, path))
            digest, size = payload_hashes[path]
            entry["sha256"] = digest
            entry["size"] = size
        actions_out.append(entry)
    # Ordena deterministicamente por (op, path).
    actions_out.sort(key=lambda a: (a["op"], a["path"]))
    manifest = {
        "format": CONCEPTUAL_FORMAT,
        "lab": "faithro-synthetic-patch-lab",
        "schema_version": 1,
        "hash_algorithm": "sha256",
        "loopback_only": True,
        "sso_enabled": False,
        "auto_update": False,
        "post_patch_command": None,
        "actions": actions_out,
    }
    return manifest


def state_index(files):
    """Índice determinístico {path: {sha256, size}} de um conjunto de arquivos."""
    return {
        p: {"sha256": sha256_bytes(b), "size": len(b)}
        for p, b in sorted_items(files)
    }


def generate(out):
    before = target_before_files()
    after = target_after_files()
    payload = patch_payload_files()
    manifest = build_manifest(payload)

    # 1) Estado inicial.
    for relpath, data in sorted_items(before):
        write_file(os.path.join(out, "target-before"), relpath, data)
    # Diretório logs/ vazio previsto no estado inicial.
    os.makedirs(os.path.join(out, "target-before", "logs"), exist_ok=True)

    # 2) Estado final esperado (referência para comparação).
    for relpath, data in sorted_items(after):
        write_file(os.path.join(out, "target-after"), relpath, data)
    os.makedirs(os.path.join(out, "target-after", "logs"), exist_ok=True)

    # 3) Servidor loopback: manifesto + arquivos de payload.
    server = os.path.join(out, "server")
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2,
                                 sort_keys=True) + "\n").encode("utf-8")
    write_file(server, "manifest.json", manifest_bytes)
    for relpath, data in sorted_items(payload):
        write_file(os.path.join(server, "files"), relpath, data)

    # 4) Índices esperados (SHA-256) — controle independente do simulador.
    expected = {
        "format": CONCEPTUAL_FORMAT,
        "target_before": state_index(before),
        "target_after": state_index(after),
    }
    expected_bytes = (json.dumps(expected, ensure_ascii=False, indent=2,
                                 sort_keys=True) + "\n").encode("utf-8")
    write_file(out, "expected-state.json", expected_bytes)

    # 5) Marcador do lab (sem timestamps variáveis — determinístico).
    meta = {
        "format": CONCEPTUAL_FORMAT,
        "generator": "scripts/generate-synthetic-patch-lab.py",
        "lab": "faithro-synthetic-patch-lab",
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "note": "Diretório descartável. Nenhum binário. Servir apenas em 127.0.0.1.",
        "schema_version": 1,
    }
    meta_bytes = (json.dumps(meta, ensure_ascii=False, indent=2,
                             sort_keys=True) + "\n").encode("utf-8")
    write_file(out, LAB_MARKER, meta_bytes)

    return manifest, sha256_bytes(manifest_bytes)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Gera o laboratório sintético do patcher (formato conceitual, "
                    "não consumível pelo Beam).")
    parser.add_argument("--output", required=True,
                        help="Diretório de saída descartável (obrigatório).")
    parser.add_argument("--clean", action="store_true",
                        help="Regenera removendo um lab anterior marcado por "
                             "LAB-METADATA.json.")
    args = parser.parse_args(argv)

    out = resolve_output(args.output)
    prepare_output(out, args.clean)
    manifest, manifest_hash = generate(out)

    n_actions = len(manifest["actions"])
    print("Lab sintético gerado com sucesso.")
    print("  Saída: %s" % out)
    print("  Formato: %s" % CONCEPTUAL_FORMAT)
    print("  Ações no manifesto: %d" % n_actions)
    print("  SHA-256 do manifesto: %s" % manifest_hash)
    print("  Servir SOMENTE em 127.0.0.1 (loopback). Diretório é descartável.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
