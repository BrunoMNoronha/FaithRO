#!/usr/bin/env python3
"""
Valida o plano controlado de instalação isolada da toolchain Rust 1.85.0 (ETAPA 2O-D1-B4 e 2O-D1-B5).

Garante estaticamente que:
  - A toolchain candidata é estritamente 1.85.0-x86_64-pc-windows-msvc;
  - A toolchain ativa 1.77.2-x86_64-pc-windows-msvc é totalmente preservada;
  - A estratégia de coexistência usa toolchain nomeada sem alterar default nem criar override;
  - Todas as 10 flags de segurança permanecem desabilitadas (False);
  - Autorização explícita é exigida para etapas futuras (next_authorization_required: True);
  - Não existem vazamentos de caminhos pessoais ou segredos.
"""

import argparse
import json
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Validador estático do plano de instalação isolada da toolchain Rust 1.85.0."
    )
    parser.add_argument(
        "--plan",
        help="Caminho explícito para o JSON do plano (padrão: client/patcher/beam-audit/toolchain-installation-plan.example.json)"
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    if args.plan:
        plan_path = Path(args.plan).resolve()
    else:
        plan_path = repo_root / "client" / "patcher" / "beam-audit" / "toolchain-installation-plan.example.json"

    schema_path = repo_root / "client" / "patcher" / "beam-audit" / "schemas" / "toolchain-installation-plan.schema.json"

    if not plan_path.is_file():
        print(f"ERRO: arquivo de plano não encontrado: {plan_path}")
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

    raw_text = plan_path.read_text(encoding="utf-8")

    # Anti-leak de caminhos pessoais e segredos
    forbidden_terms = ["C:\\Users\\", "C:/Users/", "/home/", "Users\\", "gho_", "bearer", "password", "secret"]
    for term in forbidden_terms:
        if term in raw_text:
            print(f"ERRO: termo proibido ou caminho pessoal detectado no plano: {term}")
            sys.exit(1)

    try:
        data = json.loads(raw_text)
    except Exception as e:
        print(f"ERRO: falha ao decodificar JSON do plano: {e}")
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

    if data.get("stage") != "2O-D1-B4":
        print("ERRO: stage deve ser '2O-D1-B4'")
        sys.exit(1)

    target = data.get("target_toolchain", {})
    if target.get("version") != "1.85.0":
        print("ERRO: target_toolchain version deve ser '1.85.0'")
        sys.exit(1)

    if target.get("host_triple") != "x86_64-pc-windows-msvc":
        print("ERRO: target_toolchain host_triple deve ser 'x86_64-pc-windows-msvc'")
        sys.exit(1)

    if target.get("profile") != "minimal":
        print("ERRO: profile de instalação deve ser 'minimal'")
        sys.exit(1)

    components = target.get("components", [])
    if sorted(components) != ["cargo", "rust-std", "rustc"]:
        print("ERRO: componentes do target_toolchain devem ser exatamente ['rustc', 'cargo', 'rust-std']")
        sys.exit(1)

    targets = target.get("targets", [])
    if targets != ["x86_64-pc-windows-msvc"]:
        print("ERRO: targets do target_toolchain deve ser ['x86_64-pc-windows-msvc']")
        sys.exit(1)

    existing = data.get("existing_toolchain", {})
    if existing.get("version") != "1.77.2":
        print("ERRO: existing_toolchain version deve ser '1.77.2'")
        sys.exit(1)

    if existing.get("status") != "active-default-preserved":
        print("ERRO: existing_toolchain status deve ser 'active-default-preserved'")
        sys.exit(1)

    coex = data.get("coexistence_strategy", {})
    if coex.get("named_toolchain_only") is not True:
        print("ERRO: named_toolchain_only deve ser true")
        sys.exit(1)

    if coex.get("default_toolchain_modified") is not False:
        print("ERRO: default_toolchain_modified deve ser false")
        sys.exit(1)

    if coex.get("persistent_override_created") is not False:
        print("ERRO: persistent_override_created deve ser false")
        sys.exit(1)

    inst_cmd = data.get("installation_command", {}).get("command", "")
    if "rustup update" in inst_cmd or "rustup default" in inst_cmd or "rustup override" in inst_cmd:
        print("ERRO: comando de instalação não pode usar 'rustup update', 'rustup default' nem 'rustup override'")
        sys.exit(1)

    if inst_cmd != "rustup toolchain install 1.85.0-x86_64-pc-windows-msvc --profile minimal":
        print("ERRO: comando de instalação diverge do padrão mínimo exigido")
        sys.exit(1)

    verif_cmds = data.get("verification_commands", [])
    if not verif_cmds or len(verif_cmds) < 4:
        print("ERRO: verification_commands deve conter ao menos os comandos de verificação de toolchains")
        sys.exit(1)

    has_185_check = any("1.85.0" in cmd for cmd in verif_cmds)
    has_177_check = any("1.77.2" in cmd for cmd in verif_cmds)
    if not (has_185_check and has_177_check):
        print("ERRO: verification_commands deve verificar explicitamente 1.85.0 e a preservação da 1.77.2")
        sys.exit(1)

    rollback = data.get("rollback_command", {})
    rb_cmd = rollback.get("command", "")
    if rb_cmd != "rustup toolchain uninstall 1.85.0-x86_64-pc-windows-msvc":
        print("ERRO: rollback_command deve ser 'rustup toolchain uninstall 1.85.0-x86_64-pc-windows-msvc'")
        sys.exit(1)

    if "1.77.2" in rb_cmd:
        print("ERRO: rollback não pode desinstalar a Rust 1.77.2")
        sys.exit(1)

    if rollback.get("preserves_existing_toolchain") is not True:
        print("ERRO: rollback deve preservar explicitamente a toolchain existente")
        sys.exit(1)

    sec = data.get("security_flags", {})
    expected_sec = {
        "installation_authorized": False,
        "build_authorized": False,
        "toolchain_changed": False,
        "default_toolchain_change_allowed": False,
        "persistent_override_allowed": False,
        "permanent_path_change_allowed": False,
        "elevated_shell_allowed": False,
        "vps_access_allowed": False,
        "deploy_allowed": False,
        "next_authorization_required": True,
    }

    for flag, expected in expected_sec.items():
        if sec.get(flag) is not expected:
            print(f"ERRO: flag {flag} esperada {expected}, obteve {sec.get(flag)}")
            sys.exit(1)

    print("Validação do plano de instalação isolada da toolchain Rust: OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
