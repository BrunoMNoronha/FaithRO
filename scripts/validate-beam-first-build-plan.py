#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador estático do PLANO DO PRIMEIRO BUILD CONTROLADO do Beam Patcher
(ETAPA 2O-D1-B8).

Valida, de forma determinística e offline, o artefato VERSIONADO:
  * client/patcher/beam-audit/first-build-plan.example.json
contra o schema em
  * client/patcher/beam-audit/schemas/first-build-plan.schema.json
e faz verificação cruzada com o manifesto upstream e o plano de build genérico:
  * client/patcher/beam-audit/upstream-manifest.example.json
  * client/patcher/beam-audit/build-plan.example.json

Este validador NÃO clona o Beam, NÃO instala nada, NÃO resolve dependências,
NÃO executa build, NÃO executa binário e NÃO acessa a rede. Ele apenas confirma
que o plano documenta uma execução futura que permanece BLOQUEADA e que exige
autorização humana explícita.

Apenas biblioteca padrão. Independe do CWD (resolve por __file__).
Código de saída 0 somente para plano válido; != 0 para qualquer violação.
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
EXPECTED_TREE_DIGEST = "4f405c9ecfb2f505d99b00bc77468961e3aa98c72f9ec30faa3939849465b9d5"
EXPECTED_GOVERNANCE_COMMIT = "58dfbe9b527cb31d8214e960fb27d52be10d07aa"
OVERLAY_PATH = "client/patcher/beam-audit/overlays/beam-lab-security.patch"
REQUIRED_TOOLCHAIN = "1.85.0-x86_64-pc-windows-msvc"
PRESERVED_TOOLCHAIN = "1.77.2-x86_64-pc-windows-msvc"

# Hosts oficiais permitidos para as fases de rede (derivados de docs/21 e do
# build-plan versionado). Qualquer outro host interrompe a execução futura.
ALLOWED_BUILD_HOSTS = (
    "github.com", "static.rust-lang.org", "crates.io",
    "index.crates.io", "static.crates.io", "win.rustup.rs",
)

# Hosts oficiais aceitos em qualquer URL textual do plano.
OFFICIAL_HOSTS = ALLOWED_BUILD_HOSTS + (
    "rust-lang.org", "forge.rust-lang.org",
)

URL_RE = re.compile(r"(?i)\bhttps?://([a-z0-9._-]+)")
FILE_URL = re.compile(r"(?i)\bfile://")
PERSONAL_PATH = re.compile(r"(?i)([a-z]:\\users\\[^\\/\"']+|/home/[^/\"']+|/users/[^/\"']+)")
CRED_KEY = re.compile(
    r"(?i)(password|passwd|senha|secret|client_secret|token|api[_-]?key|bearer)$")
PIPE_TO_SHELL = re.compile(
    r"(?i)(curl[^\n]*\|\s*(sh|bash)|wget[^\n]*\|\s*(sh|bash)|"
    r"\birm\b[^\n]*\|\s*iex|iwr[^\n]*\|\s*iex|\|\s*iex\b)")

# Padrões proibidos em QUALQUER comando planejado (FASE G).
FORBIDDEN_CMD = [
    (re.compile(r"(?i)rustup\s+default\s+\S"), "muda a toolchain padrão"),
    (re.compile(r"(?i)rustup\s+override\s+(set|add)"), "cria override de toolchain"),
    (re.compile(r"(?i)rustup\s+toolchain\s+install"), "instala toolchain"),
    (re.compile(r"(?i)rustup\s+component\s+add"), "instala componente"),
    (re.compile(r"(?i)rustup\s+target\s+add"), "instala target"),
    (re.compile(r"(?i)rustup\s+update"), "atualiza toolchain"),
    (re.compile(r"(?i)rustup\s+self"), "altera a instalação do rustup"),
    (re.compile(r"(?i)\bcargo\s+run\b"), "executa binário via cargo run"),
    (re.compile(r"(?i)\bcargo\s+install\b"), "instala binário via cargo install"),
    (re.compile(r"(?i)target[\\/]release[\\/][^\s;]*\.exe"), "executa binário de target/release"),
    (re.compile(r"(?i)\bssh\b|faithro-vps|\bscp\b"), "acessa a VPS"),
    (re.compile(r"(?i)runas|-Verb\s+RunAs"), "solicita privilégio administrativo"),
    (re.compile(r"(?i)Set-MpPreference|Add-MpPreference|DisableRealtimeMonitoring|Windows\s*Defender"),
     "altera o Windows Defender"),
    (re.compile(r"(?i)checkout\s+-b\b"), "usa branch flutuante no checkout"),
    (re.compile(r"(?i)clone[^\n]*(--branch|\s-b\s)"), "clona branch flutuante"),
    (re.compile(r"(?i)cargo\s+update(\s|$)"), "altera dependências via cargo update"),
]

errors = []


def fail(msg):
    errors.append(msg)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Mini-validador de JSON Schema (subconjunto), com suporte a
# additionalProperties:false para rejeitar campos desconhecidos.
# ---------------------------------------------------------------------------
TYPES = {
    "object": dict, "array": list, "string": str, "integer": int,
    "boolean": bool, "number": (int, float),
}


def schema_check(data, schema, where):
    t = schema.get("type")
    if t:
        py = TYPES.get(t)
        if t == "integer" and isinstance(data, bool):
            fail("%s: esperado integer, veio boolean" % where)
            return
        if t == "boolean" and not isinstance(data, bool):
            fail("%s: esperado boolean" % where)
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
    if isinstance(data, dict):
        for req in schema.get("required", []):
            if req not in data:
                fail("%s: campo obrigatório ausente: %s" % (where, req))
        if "minProperties" in schema and len(data) < schema["minProperties"]:
            fail("%s: poucas propriedades" % where)
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for k in data:
                if k not in props:
                    fail("%s: campo desconhecido não permitido: %s" % (where, k))
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
# Varredura recursiva de strings.
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
        if FILE_URL.search(s):
            fail("%s%s: link file:// proibido: %s" % (label, keypath, s[:80]))
        for m in URL_RE.finditer(s):
            host = m.group(1)
            if not any(host == h or host.endswith("." + h) for h in OFFICIAL_HOSTS):
                fail("%s%s: URL de host não oficial: %s" % (label, keypath, host))
        leaf = keypath.split(".")[-1].split("[")[0]
        if CRED_KEY.search(leaf):
            v = s.strip()
            if v and not (v.startswith("<") and v.endswith(">")):
                fail("%s%s: possível segredo em campo sensível" % (label, keypath))


# ---------------------------------------------------------------------------
# Regras de negócio e verificação cruzada.
# ---------------------------------------------------------------------------
def check_business(plan, manifest, build_plan):
    # ---- Estado de execução: tudo bloqueado, autorização humana obrigatória.
    es = plan.get("execution_state", {})
    must_be_false = [
        "build_authorized", "build_started", "binary_produced",
        "binary_executed", "deploy_authorized", "deploy_performed",
        "vps_access_authorized", "vps_accessed",
    ]
    for k in must_be_false:
        if es.get(k) is not False:
            fail("execution_state.%s deve ser false (build permanece bloqueado)" % k)
    if es.get("next_human_authorization_required") is not True:
        fail("execution_state.next_human_authorization_required deve ser true")

    ha = plan.get("human_authorization", {})
    if ha.get("required_before_execution") is not True:
        fail("human_authorization.required_before_execution deve ser true")
    if ha.get("granted") is not False:
        fail("human_authorization.granted deve ser false")

    if plan.get("executes_build") is not False:
        fail("executes_build deve ser false")
    if plan.get("governance_commit") != EXPECTED_GOVERNANCE_COMMIT:
        fail("governance_commit divergente do baseline de governança (origin/dev)")
    if plan.get("proprietary_assets_included") is not False:
        fail("proprietary_assets_included deve ser false")
    if plan.get("deploy") is not False:
        fail("deploy deve ser false")
    if plan.get("access_vps") is not False:
        fail("access_vps deve ser false")

    # ---- Origem e integridade (cruzamento com manifesto e build-plan).
    src = plan.get("source", {})
    if src.get("commit") != EXPECTED_COMMIT:
        fail("source.commit != commit fixado")
    if src.get("repository") != EXPECTED_REPO:
        fail("source.repository != %s" % EXPECTED_REPO)
    if src.get("checkout_mode") != "detached":
        fail("source.checkout_mode deve ser detached")
    if src.get("floating_branch_forbidden") is not True:
        fail("source.floating_branch_forbidden deve ser true")
    if manifest.get("commit") != EXPECTED_COMMIT:
        fail("manifesto: commit divergente do commit fixado")
    if src.get("commit") != manifest.get("commit"):
        fail("plano/manifesto: commit divergente")
    if build_plan.get("upstream", {}).get("commit") != EXPECTED_COMMIT:
        fail("build-plan: commit divergente do commit fixado")

    integ = src.get("integrity", {})
    if integ.get("tree_digest") != EXPECTED_TREE_DIGEST:
        fail("source.integrity.tree_digest divergente do manifesto")
    if integ.get("tree_digest") != manifest.get("tree_digest"):
        fail("plano/manifesto: tree_digest divergente")
    if integ.get("tree_digest_algorithm") != "sha256":
        fail("source.integrity.tree_digest_algorithm deve ser sha256")
    if integ.get("critical_files_recheck_required") is not True:
        fail("source.integrity.critical_files_recheck_required deve ser true")

    ws = src.get("workspace", {})
    if ws.get("inside_faithro_repo_forbidden") is not True:
        fail("source.workspace.inside_faithro_repo_forbidden deve ser true")
    if not ws.get("cleanup_method"):
        fail("source.workspace.cleanup_method ausente (limpeza obrigatória)")

    # ---- Toolchain.
    tc = plan.get("toolchain", {})
    if tc.get("required_toolchain") != REQUIRED_TOOLCHAIN:
        fail("toolchain.required_toolchain deve ser %s" % REQUIRED_TOOLCHAIN)
    if tc.get("rust_version") != "1.85.0":
        fail("toolchain.rust_version deve ser 1.85.0")
    if tc.get("preserved_default_toolchain") != PRESERVED_TOOLCHAIN:
        fail("toolchain.preserved_default_toolchain deve ser %s" % PRESERVED_TOOLCHAIN)
    if tc.get("named_invocation_required") is not True:
        fail("toolchain.named_invocation_required deve ser true")
    if tc.get("override_forbidden") is not True:
        fail("toolchain.override_forbidden deve ser true")
    if tc.get("permanent_path_change_forbidden") is not True:
        fail("toolchain.permanent_path_change_forbidden deve ser true")
    if tc.get("implicit_installation_forbidden") is not True:
        fail("toolchain.implicit_installation_forbidden deve ser true")
    if tc.get("target") != "x86_64-pc-windows-msvc":
        fail("toolchain.target deve ser x86_64-pc-windows-msvc")
    if sorted(tc.get("components", [])) != ["cargo", "rust-std", "rustc"]:
        fail("toolchain.components devem ser exatamente rustc, cargo, rust-std")
    if tc.get("targets", []) != ["x86_64-pc-windows-msvc"]:
        fail("toolchain.targets deve ser [x86_64-pc-windows-msvc]")

    # ---- Comandos planejados.
    pc = plan.get("planned_commands", {})
    if pc.get("executable_now") is not False:
        fail("planned_commands.executable_now deve ser false")
    seq = pc.get("sequence", [])
    phases = set()
    saw_detached_checkout = False
    for i, step in enumerate(seq):
        cmd = step.get("command", "")
        phase = step.get("phase", "")
        phases.add(phase)
        if step.get("authorized_now") is not False:
            fail("planned_commands.sequence[%d].authorized_now deve ser false" % i)
        for rx, why in FORBIDDEN_CMD:
            if rx.search(cmd):
                fail("planned_commands.sequence[%d] (%s): comando %s: %s"
                     % (i, phase, why, cmd[:90]))
        # Toda invocação de cargo deve usar a toolchain nomeada.
        if re.search(r"(?i)\bcargo\b", cmd) and REQUIRED_TOOLCHAIN not in cmd:
            fail("planned_commands.sequence[%d] (%s): cargo sem toolchain nomeada %s"
                 % (i, phase, REQUIRED_TOOLCHAIN))
        # Comandos de build/compilação nunca podem empacotar nem instalar.
        if re.search(r"(?i)cargo\s+build", cmd):
            if "--locked" not in cmd or "--offline" not in cmd:
                fail("planned_commands.sequence[%d] (%s): cargo build deve ser --locked --offline"
                     % (i, phase))
            if "bundle" in cmd or "tauri build" in cmd:
                fail("planned_commands.sequence[%d] (%s): build não pode empacotar/instalar"
                     % (i, phase))
        if "checkout --detach %s" % EXPECTED_COMMIT in cmd:
            saw_detached_checkout = True
    if not saw_detached_checkout:
        fail("planned_commands: falta checkout --detach do commit fixado (proíbe branch flutuante)")

    pbc = pc.get("primary_build_command", "")
    if REQUIRED_TOOLCHAIN not in pbc:
        fail("primary_build_command deve invocar a toolchain nomeada %s" % REQUIRED_TOOLCHAIN)
    if "cargo build" not in pbc or "--locked" not in pbc or "--offline" not in pbc:
        fail("primary_build_command deve ser cargo build --release --locked --offline")
    if not pc.get("cleanup_command"):
        fail("planned_commands.cleanup_command ausente (limpeza obrigatória)")

    # ---- Política de rede.
    net = plan.get("network_policy", {})
    for h in net.get("expected_hosts", []):
        if h not in ALLOWED_BUILD_HOSTS:
            fail("network_policy.expected_hosts contém host não documentado: %s" % h)
    for ph in net.get("network_allowed_phases", []):
        if ph not in phases:
            fail("network_policy.network_allowed_phases refere fase inexistente: %s" % ph)
    if net.get("unexpected_download_aborts") is not True:
        fail("network_policy.unexpected_download_aborts deve ser true")
    if net.get("credentials_required") is not False:
        fail("network_policy.credentials_required deve ser false")
    if net.get("dependencies_pinned") is not True:
        fail("network_policy.dependencies_pinned deve ser true")
    if net.get("lockfile_change_aborts") is not True:
        fail("network_policy.lockfile_change_aborts deve ser true")
    if net.get("offline_build_after_fetch") is not True:
        fail("network_policy.offline_build_after_fetch deve ser true")

    # ---- Segurança.
    sec = plan.get("security", {})
    sec_true = [
        "overlay_required", "overlay_applied_before_build",
        "overlay_fully_applied_required", "antivirus_disable_forbidden",
        "automatic_binary_execution_forbidden", "static_artifact_inspection_required",
        "binary_sha256_required", "produced_files_inventory_required",
        "output_isolated_in_temp", "files_outside_workspace_abort",
        "real_certificate_signing_forbidden", "proprietary_client_packaging_forbidden",
    ]
    for k in sec_true:
        if sec.get(k) is not True:
            fail("security.%s deve ser true" % k)
    if sec.get("overlay_path") != OVERLAY_PATH:
        fail("security.overlay_path incorreto")
    if not os.path.isfile(os.path.join(REPO, OVERLAY_PATH)):
        fail("security.overlay_path referenciado não existe no repositório")
    if build_plan.get("overlay", {}).get("path") != OVERLAY_PATH:
        fail("build-plan: overlay.path divergente do plano do primeiro build")

    # ---- Limpeza e rollback.
    cl = plan.get("cleanup", {})
    if cl.get("temp_workspace_removed") is not True:
        fail("cleanup.temp_workspace_removed deve ser true")
    if cl.get("faithro_repo_untouched_by_build") is not True:
        fail("cleanup.faithro_repo_untouched_by_build deve ser true")
    if not plan.get("rollback"):
        fail("rollback ausente")

    # ---- Critérios obrigatórios presentes.
    if not plan.get("success_criteria"):
        fail("success_criteria ausente")
    if not plan.get("failure_criteria"):
        fail("failure_criteria (critérios de interrupção) ausente")
    if not plan.get("required_future_evidence"):
        fail("required_future_evidence ausente")


def check_no_build_binaries():
    """Garante que nenhum binário/artefato de build foi versionado sob client/patcher."""
    forbidden_exts = {".exe", ".dll", ".pdb", ".msi", ".zip", ".grf", ".beam"}
    base = os.path.join(REPO, "client", "patcher")
    for root, _, files in os.walk(base):
        for f in files:
            if os.path.splitext(f)[1].lower() in forbidden_exts:
                fail("binário proibido versionado: %s" % os.path.join(root, f))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Valida o plano do primeiro build controlado do Beam Patcher "
                    "(offline; não clona, não instala, não constrói, não executa).")
    parser.add_argument("--plan",
                        default=os.path.join(BEAM_AUDIT, "first-build-plan.example.json"))
    parser.add_argument("--schema",
                        default=os.path.join(BEAM_AUDIT, "schemas", "first-build-plan.schema.json"))
    parser.add_argument("--manifest",
                        default=os.path.join(BEAM_AUDIT, "upstream-manifest.example.json"))
    parser.add_argument("--build-plan",
                        default=os.path.join(BEAM_AUDIT, "build-plan.example.json"))
    args = parser.parse_args(argv)

    try:
        plan = load_json(args.plan)
        schema = load_json(args.schema)
        manifest = load_json(args.manifest)
        build_plan = load_json(args.build_plan)
    except (OSError, ValueError) as e:
        print("ERRO ao carregar JSON: %s" % e, file=sys.stderr)
        return 2

    schema_check(plan, schema, "plan")
    check_no_forbidden(plan, "plan")
    check_business(plan, manifest, build_plan)
    check_no_build_binaries()

    if errors:
        print("Plano do primeiro build controlado: FAIL")
        for e in errors:
            print("  - " + e)
        return 1

    print("Plano do primeiro build controlado: OK")
    print("commit=%s | rust=%s | default preservada=%s"
          % (plan["source"]["commit"][:10],
             plan["toolchain"]["rust_version"],
             plan["toolchain"]["preserved_default_toolchain"]))
    print("build_authorized=%s | next_human_authorization_required=%s"
          % (plan["execution_state"]["build_authorized"],
             plan["execution_state"]["next_human_authorization_required"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
