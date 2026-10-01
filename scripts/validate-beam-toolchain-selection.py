#!/usr/bin/env python3
"""
Valida a evidência estática de seleção da toolchain Rust para o Beam Patcher (ETAPA 2O-D1-B2).
Garante que a versão candidata (Rust 1.85.0) atende a todas as restrições estáticas do grafo,
sem autorizar instalação ou compilação, e sem vazamento de segredos ou caminhos pessoais.
"""

import json
import os
import sys
from pathlib import Path


def main():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    evidence_path = repo_root / "client" / "patcher" / "beam-audit" / "evidence" / "toolchain-selection.json"
    schema_path = repo_root / "client" / "patcher" / "beam-audit" / "schemas" / "toolchain-selection.schema.json"

    if not evidence_path.is_file():
        print(f"ERRO: arquivo de evidência não encontrado: {evidence_path}")
        sys.exit(1)

    if not schema_path.is_file():
        print(f"ERRO: arquivo de schema não encontrado: {schema_path}")
        sys.exit(1)

    # Verificar ausência de binários no repositório
    forbidden_exts = {".exe", ".dll", ".pdb", ".msi", ".zip", ".grf", ".beam"}
    for root, _, files in os.walk(repo_root / "client" / "patcher"):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in forbidden_exts:
                print(f"ERRO: binário proibido encontrado no repositório: {os.path.join(root, f)}")
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

    # Validações semânticas estáticas
    if data.get("schema_version") != 1:
        print("ERRO: schema_version deve ser 1")
        sys.exit(1)

    if data.get("stage") != "2O-D1-B2":
        print("ERRO: stage deve ser '2O-D1-B2'")
        sys.exit(1)

    upstream = data.get("upstream", {})
    if upstream.get("repository") != "beamguides/beam-patcher":
        print("ERRO: repository upstream incorreto")
        sys.exit(1)

    if upstream.get("commit") != "feed97887090d121f796bc1b941390e28b7a2da5":
        print("ERRO: commit upstream incorreto")
        sys.exit(1)

    if upstream.get("official_lockfile_found") is not False:
        print("ERRO: official_lockfile_found deve ser false")
        sys.exit(1)

    lock_res = data.get("lockfile_resolution", {})
    if lock_res.get("git_dependencies") != 0:
        print("ERRO: git_dependencies deve ser 0")
        sys.exit(1)

    if lock_res.get("alternate_registries") != 0:
        print("ERRO: alternate_registries deve ser 0")
        sys.exit(1)

    if lock_res.get("graph_drift_detected") and not lock_res.get("drift_explanation"):
        print("ERRO: deriva de grafo detectada sem justificativa explícita")
        sys.exit(1)

    tc = data.get("toolchain", {})
    if tc.get("installed_rust_version") != "1.77.2":
        print("ERRO: installed_rust_version deve ser 1.77.2")
        sys.exit(1)

    if tc.get("minimum_observed_rust_version") != "1.85.0":
        print("ERRO: minimum_observed_rust_version deve ser 1.85.0")
        sys.exit(1)

    candidate = tc.get("candidate_rust_version", "")
    if candidate != "1.85.0":
        print("ERRO: candidate_rust_version deve ser 1.85.0")
        sys.exit(1)

    graph = data.get("graph_analysis", {})
    if graph.get("unverifiable_packages", 0) > 0:
        print("ERRO: não é permitida aprovação com pacotes não verificáveis")
        sys.exit(1)

    highest_msrv = graph.get("highest_declared_msrv", {}).get("required_rust", "")
    if highest_msrv == "1.85" and candidate < "1.85":
        print("ERRO: candidata inferior ao maior MSRV declarado")
        sys.exit(1)

    if "2024" in graph.get("editions_observed", []) and candidate < "1.85":
        print("ERRO: edition 2024 exige Rust >= 1.85.0")
        sys.exit(1)

    sec = data.get("security_flags", {})
    expected_sec = {
        "installation_authorized": False,
        "build_authorized": False,
        "build_started": False,
        "binary_produced": False,
        "binary_executed": False,
        "dependencies_modified": False,
        "toolchain_elevated": False,
        "deploy_performed": False,
        "vps_accessed": False,
        "next_authorization_required": True,
    }

    for flag, expected in expected_sec.items():
        if sec.get(flag) is not expected:
            print(f"ERRO: flag {flag} esperada {expected}, obteve {sec.get(flag)}")
            sys.exit(1)

    status = tc.get("candidate_status")
    if status == "approved-for-future-installation":
        if sec.get("installation_authorized") or sec.get("build_authorized"):
            print("ERRO: aprovação não pode autorizar instalação ou build antecipadamente")
            sys.exit(1)

    print("Validação da seleção da toolchain Rust: OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
