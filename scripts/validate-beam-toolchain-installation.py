#!/usr/bin/env python3
"""
Valida a evidência estática da instalação isolada da toolchain Rust 1.85.0 (ETAPA 2O-D1-B6).

Garante estaticamente que:
  - A toolchain instalada é estritamente 1.85.0-x86_64-pc-windows-msvc;
  - A toolchain ativa 1.77.2-x86_64-pc-windows-msvc permanece como padrão intocada;
  - A instalação foi autorizada, executada e validada com exit_code 0;
  - As flags de segurança proíbem build, alteração de default, override ou deploy;
  - Não existem vazamentos de caminhos pessoais ou segredos.
"""

import argparse
import json
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Validador estático da evidência de instalação da toolchain Rust 1.85.0."
    )
    parser.add_argument(
        "--evidence",
        help="Caminho explícito para a evidência JSON (padrão: client/patcher/beam-audit/evidence/toolchain-installation.json)"
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    if args.evidence:
        ev_path = Path(args.evidence).resolve()
    else:
        ev_path = repo_root / "client" / "patcher" / "beam-audit" / "evidence" / "toolchain-installation.json"

    schema_path = repo_root / "client" / "patcher" / "beam-audit" / "schemas" / "toolchain-installation.schema.json"

    if not ev_path.is_file():
        print(f"ERRO: arquivo de evidência não encontrado: {ev_path}")
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

    raw_text = ev_path.read_text(encoding="utf-8")

    # Anti-leak de caminhos pessoais e segredos
    forbidden_terms = ["C:\\Users\\", "C:/Users/", "/home/", "Users\\", "gho_", "bearer", "password", "secret"]
    for term in forbidden_terms:
        if term in raw_text:
            print(f"ERRO: termo proibido ou caminho pessoal detectado na evidência: {term}")
            sys.exit(1)

    try:
        data = json.loads(raw_text)
    except Exception as e:
        print(f"ERRO: falha ao decodificar JSON da evidência: {e}")
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

    if data.get("stage") != "2O-D1-B6":
        print("ERRO: stage deve ser '2O-D1-B6'")
        sys.exit(1)

    if not data.get("timestamp_utc"):
        print("ERRO: timestamp_utc é obrigatório")
        sys.exit(1)

    if not data.get("faithro_commit") or len(data.get("faithro_commit")) != 40:
        print("ERRO: faithro_commit deve ser SHA-1 de 40 caracteres")
        sys.exit(1)

    if data.get("branch") != "build/install-rust-185-beam":
        print("ERRO: branch deve ser 'build/install-rust-185-beam'")
        sys.exit(1)

    inst = data.get("installed_toolchain", {})
    if inst.get("version") != "1.85.0":
        print("ERRO: installed_toolchain version deve ser '1.85.0'")
        sys.exit(1)

    if inst.get("cargo_version") != "1.85.0":
        print("ERRO: installed_toolchain cargo_version deve ser '1.85.0'")
        sys.exit(1)

    if inst.get("host_triple") != "x86_64-pc-windows-msvc":
        print("ERRO: installed_toolchain host_triple deve ser 'x86_64-pc-windows-msvc'")
        sys.exit(1)

    if inst.get("profile") != "minimal":
        print("ERRO: profile de instalação deve ser 'minimal'")
        sys.exit(1)

    components = inst.get("components", [])
    if sorted(components) != ["cargo", "rust-std", "rustc"]:
        print("ERRO: componentes da installed_toolchain devem ser exatamente ['rustc', 'cargo', 'rust-std']")
        sys.exit(1)

    targets = inst.get("targets", [])
    if targets != ["x86_64-pc-windows-msvc"]:
        print("ERRO: targets da installed_toolchain deve ser ['x86_64-pc-windows-msvc']")
        sys.exit(1)

    pres = data.get("preserved_toolchain", {})
    if pres.get("version") != "1.77.2":
        print("ERRO: preserved_toolchain version deve ser '1.77.2'")
        sys.exit(1)

    if pres.get("cargo_version") != "1.77.2":
        print("ERRO: preserved_toolchain cargo_version deve ser '1.77.2'")
        sys.exit(1)

    if pres.get("status") != "active-default-preserved":
        print("ERRO: preserved_toolchain status deve ser 'active-default-preserved'")
        sys.exit(1)

    exec_info = data.get("installation_execution", {})
    if exec_info.get("exit_code") != 0:
        print("ERRO: installation_execution exit_code deve ser 0")
        sys.exit(1)

    if exec_info.get("command") != "rustup toolchain install 1.85.0-x86_64-pc-windows-msvc --profile minimal":
        print("ERRO: comando de instalação diverge do padrão")
        sys.exit(1)

    if not exec_info.get("start_timestamp_utc") or not exec_info.get("end_timestamp_utc"):
        print("ERRO: timestamps de execução são obrigatórios")
        sys.exit(1)

    coex = data.get("coexistence_status", {})
    if coex.get("default_toolchain_before") != "1.77.2-x86_64-pc-windows-msvc":
        print("ERRO: default_toolchain_before deve ser '1.77.2-x86_64-pc-windows-msvc'")
        sys.exit(1)

    if coex.get("default_toolchain_after") != "1.77.2-x86_64-pc-windows-msvc":
        print("ERRO: default_toolchain_after deve ser '1.77.2-x86_64-pc-windows-msvc'")
        sys.exit(1)

    if coex.get("active_toolchain_before") != "1.77.2-x86_64-pc-windows-msvc":
        print("ERRO: active_toolchain_before deve ser '1.77.2-x86_64-pc-windows-msvc'")
        sys.exit(1)

    if coex.get("active_toolchain_after") != "1.77.2-x86_64-pc-windows-msvc":
        print("ERRO: active_toolchain_after deve ser '1.77.2-x86_64-pc-windows-msvc'")
        sys.exit(1)

    if coex.get("overrides_before") != 0 or coex.get("overrides_after") != 0:
        print("ERRO: overrides_before e overrides_after devem ser 0")
        sys.exit(1)

    sec = data.get("security_flags", {})
    expected_sec = {
        "installation_authorized": True,
        "installation_executed": True,
        "installation_validated": True,
        "toolchain_added": True,
        "default_toolchain_changed": False,
        "persistent_override_created": False,
        "permanent_path_changed": False,
        "build_authorized": False,
        "build_started": False,
        "binary_produced": False,
        "binary_executed": False,
        "dependencies_modified": False,
        "cargo_lock_created": False,
        "deploy_performed": False,
        "vps_accessed": False,
        "windows_defender_disabled": False,
        "next_authorization_required": True,
    }

    for flag, expected in expected_sec.items():
        if sec.get(flag) is not expected:
            print(f"ERRO: flag {flag} esperada {expected}, obteve {sec.get(flag)}")
            sys.exit(1)

    gov = data.get("governance_exception", {})
    if gov.get("direct_dev_commit") != "d1b8a1ea7c30205ef8603081bfe412bd40625236":
        print("ERRO: direct_dev_commit de exceção de governança divergente")
        sys.exit(1)

    print("Validação da evidência de instalação da toolchain Rust 1.85.0: OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
