#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador do manifesto upstream e do plano de build auditável do Beam Patcher
(ETAPA 2O-D1).

Valida, de forma determinística e offline, os artefatos VERSIONADOS:
  * client/patcher/beam-audit/upstream-manifest.example.json
  * client/patcher/beam-audit/build-plan.example.json
contra os schemas em client/patcher/beam-audit/schemas/ e contra as regras de
segurança da etapa (docs/19, FASE S). Não clona o Beam, não instala nada, não
executa build e não acessa a rede.

Regras (FASE S):
  commit fixado; origem oficial; versão exata da toolchain; target MSVC;
  arquitetura; nenhuma versão "latest"; nenhuma URL não oficial; nenhum
  comando pipe-to-shell; overlay obrigatório; build sem bundle; --locked;
  segundo build --offline; SHA-256 obrigatório; nenhum deploy; nenhuma execução
  do binário; rollback presente; diretórios temporários; ausência de dados
  pessoais; ausência de segredos.

Apenas biblioteca padrão. Independe do CWD. Código de saída != 0 em falha.
"""
import argparse
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BEAM_AUDIT = os.path.join(REPO, "client", "patcher", "beam-audit")

EXPECTED_COMMIT = "feed97887090d121f796bc1b941390e28b7a2da5"
EXPECTED_REPO = "beamguides/beam-patcher"
OVERLAY_PATH = "client/patcher/beam-audit/overlays/beam-lab-security.patch"

OFFICIAL_HOSTS = (
    "github.com", "win.rustup.rs", "static.rust-lang.org", "rust-lang.org",
    "forge.rust-lang.org", "visualstudio.microsoft.com", "aka.ms",
    "developer.microsoft.com", "microsoft.com",
)
PIPE_TO_SHELL = re.compile(
    r"(?i)(curl[^\n]*\|\s*(sh|bash)|wget[^\n]*\|\s*(sh|bash)|"
    r"\birm\b[^\n]*\|\s*iex|iwr[^\n]*\|\s*iex|\|\s*iex\b)")
URL_RE = re.compile(r"(?i)\bhttps?://([a-z0-9._-]+)")
PERSONAL_PATH = re.compile(r"(?i)([a-z]:\\users\\[^\\/\"']+|/home/[^/\"']+|/users/[^/\"']+)")
CRED_KEY = re.compile(
    r"(?i)(password|passwd|senha|secret|client_secret|token|api[_-]?key|bearer)$")

errors = []


def fail(msg):
    errors.append(msg)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Mini-validador de JSON Schema (subconjunto: type/const/pattern/enum/required/
# properties/items/minItems/minLength/minimum/minProperties).
# ---------------------------------------------------------------------------
TYPES = {
    "object": dict, "array": list, "string": str, "integer": int,
    "boolean": bool, "number": (int, float),
}


def schema_check(data, schema, where):
    t = schema.get("type")
    if t:
        py = TYPES.get(t)
        # bool é subclasse de int: tratar separadamente.
        if t == "integer" and isinstance(data, bool):
            fail("%s: esperado integer, veio boolean" % where)
            return
        if py and not isinstance(data, py):
            fail("%s: esperado tipo %s" % (where, t))
            return
    if "const" in schema and data != schema["const"]:
        fail("%s: valor deve ser %r (veio %r)" % (where, schema["const"], data))
    if "enum" in schema and data not in schema["enum"]:
        fail("%s: valor %r fora do enum %r" % (where, data, schema["enum"]))
    if "pattern" in schema and isinstance(data, str):
        if not re.search(schema["pattern"], data):
            fail("%s: não casa com o padrão %s" % (where, schema["pattern"]))
    if "minLength" in schema and isinstance(data, str) and len(data) < schema["minLength"]:
        fail("%s: string curta demais" % where)
    if "minimum" in schema and isinstance(data, (int, float)) and not isinstance(data, bool):
        if data < schema["minimum"]:
            fail("%s: menor que o mínimo" % where)
    if isinstance(data, dict):
        for req in schema.get("required", []):
            if req not in data:
                fail("%s: campo obrigatório ausente: %s" % (where, req))
        if "minProperties" in schema and len(data) < schema["minProperties"]:
            fail("%s: poucas propriedades" % where)
        props = schema.get("properties", {})
        for k, sub in props.items():
            if k in data:
                schema_check(data[k], sub, "%s.%s" % (where, k))
    if isinstance(data, list):
        if "minItems" in schema and len(data) < schema["minItems"]:
            fail("%s: lista com poucos itens" % where)
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(data):
                schema_check(item, item_schema, "%s[%d]" % (where, i))


# ---------------------------------------------------------------------------
# Varredura recursiva de valores.
# ---------------------------------------------------------------------------
def walk_strings(node, keypath=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk_strings(v, "%s.%s" % (keypath, k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_strings(v, "%s[%d]" % (keypath, i))
    elif isinstance(node, str):
        yield keypath, node


def check_no_forbidden(node, label):
    for keypath, s in walk_strings(node):
        if PIPE_TO_SHELL.search(s):
            fail("%s%s: comando pipe-to-shell proibido: %s" % (label, keypath, s[:80]))
        if PERSONAL_PATH.search(s):
            fail("%s%s: possível caminho pessoal: %s" % (label, keypath, s[:80]))
        for m in URL_RE.finditer(s):
            host = m.group(1)
            if not any(host == h or host.endswith("." + h) for h in OFFICIAL_HOSTS):
                fail("%s%s: URL de host não oficial: %s" % (label, keypath, host))
        # segredo: chave sensível com valor não placeholder.
        leaf = keypath.split(".")[-1].split("[")[0]
        if CRED_KEY.search(leaf):
            v = s.strip()
            if v and not (v.startswith("<") and v.endswith(">")):
                fail("%s%s: possível segredo em campo sensível" % (label, keypath))


# ---------------------------------------------------------------------------
# Regras de negócio.
# ---------------------------------------------------------------------------
def check_business(manifest, plan):
    # Manifesto <-> plano.
    if manifest.get("commit") != EXPECTED_COMMIT:
        fail("manifesto: commit != commit fixado")
    if manifest.get("repository") != EXPECTED_REPO:
        fail("manifesto: repository != %s" % EXPECTED_REPO)
    if not manifest.get("license_expression"):
        fail("manifesto: license_expression ausente")

    up = plan.get("upstream", {})
    if up.get("commit") != EXPECTED_COMMIT:
        fail("plano: upstream.commit != commit fixado")
    if up.get("commit") != manifest.get("commit"):
        fail("plano/manifesto: commit divergente")
    if up.get("official_source") != "https://github.com/beamguides/beam-patcher":
        fail("plano: official_source não é o repositório oficial")
    if up.get("checkout_mode") != "detached":
        fail("plano: checkout_mode deve ser detached")

    tc = plan.get("toolchain", {})
    rv = tc.get("rust_version", "")
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", rv)
    if not m:
        fail("plano: rust_version deve ser exata X.Y.Z (veio %r)" % rv)
    else:
        major, minor = int(m.group(1)), int(m.group(2))
        if (major, minor) < (1, 75):
            fail("plano: rust_version < 1.75 (veio %s)" % rv)
    if rv.lower() == "latest":
        fail("plano: rust_version não pode ser 'latest'")
    if tc.get("target") != "x86_64-pc-windows-msvc":
        fail("plano: target deve ser x86_64-pc-windows-msvc")
    if not tc.get("host_triple"):
        fail("plano: host_triple ausente")
    if not tc.get("architecture"):
        fail("plano: architecture ausente")

    # Versões "latest" em pré-requisitos.
    for i, pre in enumerate(plan.get("prerequisites", [])):
        ver = str(pre.get("version", ""))
        if ver.strip().lower() == "latest" or re.search(r"(?i)\blatest\b", ver):
            fail("plano: prerequisites[%d].version usa 'latest' sem versão efetiva" % i)
        src = pre.get("source", "")
        if not src.startswith("https://"):
            fail("plano: prerequisites[%d].source não é https oficial" % i)

    ir = plan.get("install_rules", {})
    for k in ("no_pipe_to_shell", "no_irm_iex",
              "no_latest_without_recording_effective_version"):
        if ir.get(k) is not True:
            fail("plano: install_rules.%s deve ser true" % k)
    if ir.get("run_as_administrator") is not False:
        fail("plano: install_rules.run_as_administrator deve ser false")
    if ir.get("modify_global_path") is not False:
        fail("plano: install_rules.modify_global_path deve ser false")

    build = plan.get("build", {})
    if build.get("workspace_is_temporary") is not True:
        fail("plano: build.workspace_is_temporary deve ser true")
    if build.get("bundle") is not False:
        fail("plano: build.bundle deve ser false")
    if build.get("installer") is not False:
        fail("plano: build.installer deve ser false")
    if build.get("locked") is not True:
        fail("plano: build.locked deve ser true")
    if build.get("offline_second_build") is not True:
        fail("plano: build.offline_second_build deve ser true")
    if build.get("sha256_required") is not True:
        fail("plano: build.sha256_required deve ser true")
    if build.get("execute_binary") is not False:
        fail("plano: build.execute_binary deve ser false")
    cmd = build.get("primary_build_command", "")
    if "--locked" not in cmd:
        fail("plano: primary_build_command deve conter --locked")
    if "--offline" not in cmd:
        fail("plano: primary_build_command deve conter --offline")
    if "bundle" in cmd or "tauri build" in cmd:
        fail("plano: primary_build_command não deve empacotar/instalar")

    ov = plan.get("overlay", {})
    if ov.get("required") is not True:
        fail("plano: overlay.required deve ser true")
    if ov.get("path") != OVERLAY_PATH:
        fail("plano: overlay.path incorreto")
    if not os.path.isfile(os.path.join(REPO, OVERLAY_PATH)):
        fail("plano: overlay referenciado não existe no repositório")

    net = plan.get("network_policy", {})
    for host in net.get("first_execution_allows_only", []):
        if host not in ("127.0.0.1", "localhost"):
            fail("plano: rede da primeira execução deve ser só loopback (veio %s)" % host)
    if net.get("external_dns_during_first_run") is not False:
        fail("plano: external_dns_during_first_run deve ser false")
    if net.get("broad_network_release") is not False:
        fail("plano: broad_network_release deve ser false")

    if plan.get("deploy") is not False:
        fail("plano: deploy deve ser false")
    if plan.get("access_vps") is not False:
        fail("plano: access_vps deve ser false")
    if not plan.get("rollback"):
        fail("plano: rollback ausente")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Valida o manifesto upstream e o plano de build do Beam "
                    "Patcher (offline; não clona, não instala, não constrói).")
    parser.add_argument("--manifest",
                        default=os.path.join(BEAM_AUDIT, "upstream-manifest.example.json"))
    parser.add_argument("--plan",
                        default=os.path.join(BEAM_AUDIT, "build-plan.example.json"))
    parser.add_argument("--manifest-schema",
                        default=os.path.join(BEAM_AUDIT, "schemas", "upstream-manifest.schema.json"))
    parser.add_argument("--plan-schema",
                        default=os.path.join(BEAM_AUDIT, "schemas", "build-plan.schema.json"))
    args = parser.parse_args(argv)

    try:
        manifest = load_json(args.manifest)
        plan = load_json(args.plan)
        manifest_schema = load_json(args.manifest_schema)
        plan_schema = load_json(args.plan_schema)
    except (OSError, ValueError) as e:
        print("ERRO ao carregar JSON: %s" % e, file=sys.stderr)
        return 2

    schema_check(manifest, manifest_schema, "manifest")
    schema_check(plan, plan_schema, "plan")
    check_no_forbidden(manifest, "manifest")
    check_no_forbidden(plan, "plan")
    check_business(manifest, plan)

    if errors:
        print("Plano de build/manifesto: FAIL")
        for e in errors:
            print("  - " + e)
        return 1

    print("Plano de build/manifesto: OK")
    print("Manifesto e plano válidos contra os schemas e as regras da etapa.")
    print("commit=%s | rust=%s | target=%s"
          % (plan["upstream"]["commit"][:10],
             plan["toolchain"]["rust_version"],
             plan["toolchain"]["target"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
