#!/usr/bin/env python3
"""
Valida a evidência de compatibilidade da toolchain Rust do Beam Patcher.
Garante que o bloqueio da Rust 1.77.2 por zeroize 1.9.0 (edition 2024 / MSRV 1.85)
está corretamente registrado e sem vazamento de caminhos pessoais ou segredos.
"""

import json
import os
import sys
from pathlib import Path


def main():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    evidence_path = repo_root / "client" / "patcher" / "beam-audit" / "evidence" / "toolchain-compatibility.json"
    schema_path = repo_root / "client" / "patcher" / "beam-audit" / "schemas" / "toolchain-compatibility.schema.json"

    if not evidence_path.is_file():
        print(f"ERRO: arquivo de evidência não encontrado: {evidence_path}")
        sys.exit(1)

    if not schema_path.is_file():
        print(f"ERRO: arquivo de schema não encontrado: {schema_path}")
        sys.exit(1)

    # Verificar ausência de binários na árvore do repositório
    forbidden_exts = {".exe", ".dll", ".pdb", ".msi", ".zip", ".grf", ".beam"}
    for root, _, files in os.walk(repo_root / "client" / "patcher"):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in forbidden_exts:
                print(f"ERRO: arquivo binário proibido encontrado no repositório: {os.path.join(root, f)}")
                sys.exit(1)

    raw_text = evidence_path.read_text(encoding="utf-8")

    # Anti-leak de caminhos pessoais e segredos
    forbidden_terms = ["C:\\Users\\", "C:/Users/", "/home/", "Users\\", "gho_", "bearer", "password", "secret"]
    for term in forbidden_terms:
        if term in raw_text:
            print(f"ERRO: termo proibido ou caminho pessoal detectado na evidência: {term}")
            sys.exit(1)

    try:
        data = json.loads(raw_text)
    except Exception as e:
        print(f"ERRO: falha ao decodificar JSON de evidência: {e}")
        sys.exit(1)

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERRO: falha ao decodificar JSON Schema: {e}")
        sys.exit(1)

    # Validações semânticas determinísticas
    if data.get("schema_version") != 1:
        print("ERRO: schema_version deve ser 1")
        sys.exit(1)

    if data.get("stage") != "2O-D1-B1":
        print("ERRO: stage deve ser '2O-D1-B1'")
        sys.exit(1)

    if data.get("classification") != "blocked":
        print("ERRO: classification deve ser 'blocked'")
        sys.exit(1)

    upstream = data.get("upstream", {})
    if upstream.get("repository") != "beamguides/beam-patcher":
        print("ERRO: repository upstream incorreto")
        sys.exit(1)

    if upstream.get("commit") != "feed97887090d121f796bc1b941390e28b7a2da5":
        print("ERRO: commit upstream incorreto")
        sys.exit(1)

    expected_digest = "4f405c9ecfb2f505d99b00bc77468961e3aa98c72f9ec30faa3939849465b9d5"
    if upstream.get("source_digest") != expected_digest:
        print("ERRO: source_digest upstream incorreto")
        sys.exit(1)

    tested = data.get("tested_toolchain", {})
    if tested.get("rust") != "1.77.2" or tested.get("cargo") != "1.77.2":
        print("ERRO: toolchain testada deve ser Rust 1.77.2 e Cargo 1.77.2")
        sys.exit(1)

    lock = data.get("cargo_lock", {})
    if lock.get("official_lockfile_found") is not False:
        print("ERRO: official_lockfile_found deve ser false")
        sys.exit(1)

    if lock.get("git_dependencies") != 0:
        print("ERRO: git_dependencies deve ser 0")
        sys.exit(1)

    metadata = data.get("metadata", {})
    if metadata.get("succeeded") is not False:
        print("ERRO: metadata.succeeded deve ser false")
        sys.exit(1)

    primary = data.get("primary_blocker", {})
    if primary.get("crate") != "zeroize":
        print("ERRO: primary_blocker crate deve ser zeroize")
        sys.exit(1)

    if primary.get("version") != "1.9.0":
        print("ERRO: primary_blocker version deve ser 1.9.0")
        sys.exit(1)

    if primary.get("edition") != "2024":
        print("ERRO: primary_blocker edition deve ser 2024")
        sys.exit(1)

    if primary.get("required_rust") != "1.85":
        print("ERRO: primary_blocker required_rust deve ser 1.85")
        sys.exit(1)

    # Boolean security flags
    security_flags = {
        "build_started": False,
        "binary_produced": False,
        "binary_executed": False,
        "dependencies_modified": False,
        "toolchain_elevated": False,
        "deploy_performed": False,
        "vps_accessed": False,
        "next_authorization_required": True,
    }

    for flag, expected in security_flags.items():
        if data.get(flag) is not expected:
            print(f"ERRO: flag {flag} esperada {expected}, obteve {data.get(flag)}")
            sys.exit(1)

    print("Validação da evidência de compatibilidade da toolchain: OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
