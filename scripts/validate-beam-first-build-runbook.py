#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador estático do RUNBOOK, do MODELO DE AUTORIZAÇÃO e do TEMPLATE DE
EVIDÊNCIA do primeiro build controlado do Beam Patcher (ETAPA 2O-D1-B10).

Valida, de forma determinística e offline, os artefatos VERSIONADOS:
  * client/patcher/beam-audit/first-build-runbook.example.json
  * client/patcher/beam-audit/first-build-authorization.example.json
  * client/patcher/beam-audit/first-build-execution-evidence.example.json
contra os schemas em client/patcher/beam-audit/schemas/ e faz verificação
cruzada com o plano do primeiro build, o manifesto upstream e o overlay.

Este validador NÃO clona o Beam, NÃO instala nada, NÃO resolve dependências,
NÃO executa build, NÃO executa binário, NÃO executa Git/Rust/Cargo/PowerShell
e NÃO acessa a rede. Ele apenas confirma que o runbook documenta uma execução
futura que permanece BLOQUEADA, que a autorização NÃO está concedida e que a
evidência NÃO declara execução.

Apenas biblioteca padrão. Independe do CWD (resolve por __file__).
Código de saída 0 somente para conjunto válido; != 0 para qualquer violação.
"""
import argparse
import hashlib
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
SCHEMAS = os.path.join(BEAM_AUDIT, "schemas")

EXPECTED_COMMIT = "feed97887090d121f796bc1b941390e28b7a2da5"
EXPECTED_REPO = "beamguides/beam-patcher"
EXPECTED_TREE_DIGEST = "4f405c9ecfb2f505d99b00bc77468961e3aa98c72f9ec30faa3939849465b9d5"
EXPECTED_DEV_COMMIT = "4c6a908e09cad84d7ad275267c9b4f912c56b76e"
REQUIRED_TOOLCHAIN = "1.85.0-x86_64-pc-windows-msvc"
PRESERVED_TOOLCHAIN = "1.77.2-x86_64-pc-windows-msvc"
OVERLAY_PATH = "client/patcher/beam-audit/overlays/beam-lab-security.patch"

RUNBOOK_REF = "client/patcher/beam-audit/first-build-runbook.example.json"
AUTHORIZATION_REF = "client/patcher/beam-audit/first-build-authorization.example.json"
EVIDENCE_REF = "client/patcher/beam-audit/first-build-execution-evidence.example.json"
PLAN_REF = "client/patcher/beam-audit/first-build-plan.example.json"

# 25 fases canônicas do runbook (ordem operacional planejada).
CANONICAL_PHASES = [
    "host_gate", "authorization_check", "prepare_workspace", "capture_baseline",
    "acquire_source", "verify_integrity", "initial_inventory", "prepare_overlay",
    "apply_overlay", "validate_overlay", "verify_toolchain", "verify_components_targets",
    "prepare_dependencies", "offline_transition", "primary_build", "capture_exit_code",
    "inventory_artifacts", "hash_artifacts", "static_inspection", "confirm_no_execution",
    "cleanup", "capture_final_state", "reconciliation", "closure", "generate_evidence",
]
# Passos que podem ser executados agora apenas para validar o ambiente (somente leitura).
ALLOWED_READONLY_PHASES = {
    "host_gate", "authorization_check", "capture_baseline",
    "verify_toolchain", "verify_components_targets",
}
# Fases nas quais a rede é permitida (na execução futura). Todas devem ficar bloqueadas.
NETWORK_PHASES = {"acquire_source", "prepare_dependencies", "offline_transition"}

# Hosts oficiais aceitos em qualquer URL textual dos artefatos.
OFFICIAL_HOSTS = (
    "github.com", "static.rust-lang.org", "crates.io",
    "index.crates.io", "static.crates.io", "win.rustup.rs",
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
SECRET_VALUE = re.compile(
    r"(?i)(gh[pousr]_[a-z0-9]{20,}|AKIA[0-9A-Z]{12,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[baprs]-[a-z0-9-]{10,})")
IPV4 = re.compile(r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b")
# Tokens de asset proprietário (arquivos/binários do cliente Ragnarok/Gravity).
PROPRIETARY = re.compile(r"(?i)(\.grf\b|\.gpf\b|\.rgz\b|\bragexe\b|data\.grf|\.gr2\b)")

# Padrões proibidos em QUALQUER comando planejado dos passos do runbook.
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
    (re.compile(r"(?i)cargo\s+update(\s|$)"), "altera dependências via cargo update"),
    (re.compile(r"(?i)target[\\/]release[\\/][^\s;]*\.exe"), "executa binário de target/release"),
    (re.compile(r"(?i)\bssh\b|faithro-vps|\bscp\b"), "acessa a VPS"),
    (re.compile(r"(?i)runas|-Verb\s+RunAs"), "solicita privilégio administrativo"),
    (re.compile(r"(?i)Set-MpPreference|Add-MpPreference|DisableRealtimeMonitoring|Windows\s*Defender"),
     "altera o Windows Defender"),
    (re.compile(r"(?i)checkout\s+-b\b"), "usa branch flutuante no checkout"),
    (re.compile(r"(?i)clone[^\n]*(--branch|\s-b\s)"), "clona branch flutuante"),
]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_placeholder(v):
    return isinstance(v, str) and v.startswith("<") and v.endswith(">")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Mini-validador de JSON Schema (subconjunto), com additionalProperties:false,
# type-lista, const, enum, pattern, minLength, minItems, maxItems, minimum.
# ---------------------------------------------------------------------------
TYPES = {
    "object": dict, "array": list, "string": str, "integer": int,
    "boolean": bool, "number": (int, float), "null": type(None),
}


def _type_ok(data, t):
    if t == "integer":
        return isinstance(data, int) and not isinstance(data, bool)
    if t == "boolean":
        return isinstance(data, bool)
    if t == "null":
        return data is None
    py = TYPES.get(t)
    return py is not None and isinstance(data, py)


def schema_check(data, schema, where, errors):
    t = schema.get("type")
    if t:
        types = t if isinstance(t, list) else [t]
        if not any(_type_ok(data, tt) for tt in types):
            errors.append("%s: tipo inválido (esperado %s)" % (where, t))
            return
    if "const" in schema and data != schema["const"]:
        errors.append("%s: valor deve ser %r (veio %r)" % (where, schema["const"], data))
    if "enum" in schema and data not in schema["enum"]:
        errors.append("%s: valor %r fora do enum %r" % (where, data, schema["enum"]))
    if "pattern" in schema and isinstance(data, str):
        if not re.search(schema["pattern"], data):
            errors.append("%s: não casa com o padrão %s" % (where, schema["pattern"]))
    if "minLength" in schema and isinstance(data, str) and len(data) < schema["minLength"]:
        errors.append("%s: string curta demais" % where)
    if "minimum" in schema and isinstance(data, int) and not isinstance(data, bool):
        if data < schema["minimum"]:
            errors.append("%s: valor abaixo do mínimo" % where)
    if isinstance(data, dict):
        for req in schema.get("required", []):
            if req not in data:
                errors.append("%s: campo obrigatório ausente: %s" % (where, req))
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for k in data:
                if k not in props:
                    errors.append("%s: campo desconhecido não permitido: %s" % (where, k))
        for k, sub in props.items():
            if k in data:
                schema_check(data[k], sub, "%s.%s" % (where, k), errors)
    if isinstance(data, list):
        if "minItems" in schema and len(data) < schema["minItems"]:
            errors.append("%s: lista com poucos itens" % where)
        if "maxItems" in schema and len(data) > schema["maxItems"]:
            errors.append("%s: lista deve estar vazia nesta etapa" % where)
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(data):
                schema_check(item, item_schema, "%s[%d]" % (where, i), errors)


# ---------------------------------------------------------------------------
# Varredura recursiva de strings (segredos, caminhos, URLs, file://, IPs).
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


def _public_ip(s):
    for m in IPV4.finditer(s):
        octs = [int(x) for x in m.groups()]
        if any(o > 255 for o in octs):
            continue
        a, b = octs[0], octs[1]
        if a == 127 or a == 10 or a == 0 or (a == 255 and b == 255):
            continue
        if a == 192 and b == 168:
            continue
        if a == 172 and 16 <= b <= 31:
            continue
        if a == 169 and b == 254:
            continue
        return m.group(0)
    return None


def check_no_forbidden(node, label, errors):
    for keypath, s in walk_strings(node):
        if PIPE_TO_SHELL.search(s):
            errors.append("%s%s: comando pipe-to-shell proibido: %s" % (label, keypath, s[:80]))
        if PERSONAL_PATH.search(s):
            errors.append("%s%s: possível caminho pessoal: %s" % (label, keypath, s[:80]))
        if FILE_URL.search(s):
            errors.append("%s%s: link file:// proibido: %s" % (label, keypath, s[:80]))
        if SECRET_VALUE.search(s):
            errors.append("%s%s: possível segredo/token/chave: %s" % (label, keypath, s[:40]))
        if PROPRIETARY.search(s):
            errors.append("%s%s: possível asset proprietário: %s" % (label, keypath, s[:60]))
        ip = _public_ip(s)
        if ip:
            errors.append("%s%s: possível IP público: %s" % (label, keypath, ip))
        for m in URL_RE.finditer(s):
            host = m.group(1)
            if not any(host == h or host.endswith("." + h) for h in OFFICIAL_HOSTS):
                errors.append("%s%s: URL de host não oficial: %s" % (label, keypath, host))
        leaf = keypath.split(".")[-1].split("[")[0]
        if CRED_KEY.search(leaf):
            v = s.strip()
            if v and not is_placeholder(v):
                errors.append("%s%s: possível segredo em campo sensível" % (label, keypath))


# ---------------------------------------------------------------------------
# Regras de negócio: RUNBOOK.
# ---------------------------------------------------------------------------
def check_runbook(rb, manifest, plan, overlay_sha, errors):
    if rb.get("executes_build") is not False:
        errors.append("runbook.executes_build deve ser false")
    if rb.get("governance_commit") != EXPECTED_DEV_COMMIT:
        errors.append("runbook.governance_commit divergente do baseline de dev (%s)" % EXPECTED_DEV_COMMIT)

    ps = rb.get("process_state", {})
    ps_false = [
        "human_authorization_granted", "execution_authorized", "execution_started",
        "build_started", "build_completed", "binary_produced", "binary_executed",
        "deploy_performed", "vps_accessed",
    ]
    for k in ps_false:
        if ps.get(k) is not False:
            errors.append("runbook.process_state.%s deve ser false" % k)
    if ps.get("human_authorization_required") is not True:
        errors.append("runbook.process_state.human_authorization_required deve ser true")

    if rb.get("proprietary_assets_included") is not False:
        errors.append("runbook.proprietary_assets_included deve ser false")
    if rb.get("deploy") is not False:
        errors.append("runbook.deploy deve ser false")
    if rb.get("access_vps") is not False:
        errors.append("runbook.access_vps deve ser false")

    # Origem/integridade cruzada.
    src = rb.get("source", {})
    if src.get("commit") != EXPECTED_COMMIT:
        errors.append("runbook.source.commit != commit fixado")
    if src.get("tree_digest") != EXPECTED_TREE_DIGEST:
        errors.append("runbook.source.tree_digest divergente")
    if manifest.get("commit") != EXPECTED_COMMIT or manifest.get("tree_digest") != EXPECTED_TREE_DIGEST:
        errors.append("manifesto: commit/digest divergente do fixado")
    if plan.get("source", {}).get("commit") != EXPECTED_COMMIT:
        errors.append("plano: commit divergente do fixado")

    # Toolchain.
    tc = rb.get("toolchain", {})
    if tc.get("required_toolchain") != REQUIRED_TOOLCHAIN:
        errors.append("runbook.toolchain.required_toolchain incorreta")
    if tc.get("preserved_default_toolchain") != PRESERVED_TOOLCHAIN:
        errors.append("runbook.toolchain.preserved_default_toolchain incorreta")

    # Workspace externo obrigatório.
    ws = rb.get("workspace", {})
    if ws.get("inside_faithro_repo_forbidden") is not True:
        errors.append("runbook.workspace.inside_faithro_repo_forbidden deve ser true")

    # Passos: IDs, ordenação, dependências, execução, rede, comandos.
    steps = rb.get("steps", [])
    ids = [s.get("id") for s in steps]
    if len(ids) != len(set(ids)):
        errors.append("runbook.steps: IDs duplicados")
    order_of = {}
    phase_of = {}
    for i, s in enumerate(steps):
        sid = s.get("id")
        order = s.get("order")
        phase = s.get("phase")
        order_of[phase] = order
        phase_of[phase] = sid
        if order != i + 1:
            errors.append("runbook.steps[%d] (%s): order deve ser %d (sequencial)" % (i, sid, i + 1))
        if phase not in CANONICAL_PHASES:
            errors.append("runbook.steps[%d] (%s): fase desconhecida: %s" % (i, sid, phase))
        # Dependências existentes e anteriores.
        for dep in s.get("depends_on", []):
            if dep not in ids:
                errors.append("runbook.steps[%d] (%s): depends_on inexistente: %s" % (i, sid, dep))
            elif ids.index(dep) >= i:
                errors.append("runbook.steps[%d] (%s): depends_on não anterior: %s" % (i, sid, dep))
        # Execução coerente com a classe da fase.
        execu = s.get("execution")
        if phase in ALLOWED_READONLY_PHASES:
            if execu != "allowed_read_only":
                errors.append("runbook.steps[%d] (%s): fase de leitura deve ser allowed_read_only" % (i, sid))
        else:
            if execu != "blocked_pending_authorization":
                errors.append("runbook.steps[%d] (%s): fase deve permanecer bloqueada nesta etapa" % (i, sid))
        # Rede só nas fases previstas; e essas fases devem estar bloqueadas.
        if s.get("network") is True:
            if phase not in NETWORK_PHASES:
                errors.append("runbook.steps[%d] (%s): rede não permitida nesta fase" % (i, sid))
            if execu != "blocked_pending_authorization":
                errors.append("runbook.steps[%d] (%s): fase com rede deve ficar bloqueada" % (i, sid))
        # Comandos proibidos e regras de cargo.
        cmd = s.get("command", "")
        for rx, why in FORBIDDEN_CMD:
            if rx.search(cmd):
                errors.append("runbook.steps[%d] (%s): comando %s: %s" % (i, sid, why, cmd[:90]))
        if re.search(r"(?i)\bcargo\b", cmd) and REQUIRED_TOOLCHAIN not in cmd:
            errors.append("runbook.steps[%d] (%s): cargo sem toolchain nomeada %s" % (i, sid, REQUIRED_TOOLCHAIN))
        if re.search(r"(?i)cargo\s+build", cmd):
            if "--locked" not in cmd or "--offline" not in cmd:
                errors.append("runbook.steps[%d] (%s): cargo build deve ser --locked --offline" % (i, sid))
            if "bundle" in cmd or "tauri build" in cmd:
                errors.append("runbook.steps[%d] (%s): build não pode empacotar/instalar" % (i, sid))

    # Todas as 25 fases canônicas presentes, exatamente uma vez.
    present = [s.get("phase") for s in steps]
    for ph in CANONICAL_PHASES:
        if present.count(ph) != 1:
            errors.append("runbook.steps: fase obrigatória ausente ou repetida: %s" % ph)

    # host_gate é o primeiro passo.
    if order_of.get("host_gate") != 1:
        errors.append("runbook.steps: host_gate deve ser o primeiro passo")

    # Checkout destacado do commit fixado presente em algum comando.
    if not any("checkout --detach %s" % EXPECTED_COMMIT in s.get("command", "") for s in steps):
        errors.append("runbook.steps: falta checkout --detach do commit fixado (proíbe branch flutuante)")

    # Ordenação: nada de saltar para o build antes das pré-condições.
    def ord_of(ph):
        return order_of.get(ph)

    pb = ord_of("primary_build")
    if pb is None:
        errors.append("runbook.steps: fase primary_build ausente")
    else:
        before_build = [
            "authorization_check", "acquire_source", "verify_integrity",
            "apply_overlay", "validate_overlay", "verify_toolchain",
            "verify_components_targets", "prepare_dependencies", "offline_transition",
        ]
        for ph in before_build:
            o = ord_of(ph)
            if o is None or o >= pb:
                errors.append("runbook.steps: %s deve ocorrer antes de primary_build" % ph)
        # Integridade antes do overlay; overlay aplicado antes de validado.
        if ord_of("verify_integrity") is not None and ord_of("apply_overlay") is not None:
            if ord_of("verify_integrity") >= ord_of("apply_overlay"):
                errors.append("runbook.steps: verify_integrity deve ocorrer antes de apply_overlay")
        if ord_of("apply_overlay") is not None and ord_of("validate_overlay") is not None:
            if ord_of("apply_overlay") >= ord_of("validate_overlay"):
                errors.append("runbook.steps: apply_overlay deve ocorrer antes de validate_overlay")
        # Limpeza depois do build; evidência é o último passo.
        if ord_of("cleanup") is not None and ord_of("cleanup") <= pb:
            errors.append("runbook.steps: cleanup deve ocorrer após primary_build")
    if order_of.get("generate_evidence") != len(steps):
        errors.append("runbook.steps: generate_evidence deve ser o último passo")

    # Deve existir passo de limpeza e o overlay referenciado deve existir.
    if "cleanup" not in present:
        errors.append("runbook.steps: passo de limpeza ausente")
    if not os.path.isfile(os.path.join(REPO, OVERLAY_PATH)):
        errors.append("overlay referenciado não existe: %s" % OVERLAY_PATH)

    # go/no-go sem decisão implícita.
    g = rb.get("go_no_go", {})
    if g.get("default_decision") != "NO-GO":
        errors.append("runbook.go_no_go.default_decision deve ser NO-GO")
    if g.get("proceed_with_reservations_allowed") is not False:
        errors.append("runbook.go_no_go.proceed_with_reservations_allowed deve ser false")
    if g.get("ambiguous_result_is") != "NO-GO":
        errors.append("runbook.go_no_go.ambiguous_result_is deve ser NO-GO")
    if not g.get("go_conditions"):
        errors.append("runbook.go_no_go.go_conditions ausente")
    if not g.get("no_go_conditions"):
        errors.append("runbook.go_no_go.no_go_conditions ausente")

    # Procedimentos obrigatórios.
    if not rb.get("interruption_procedure"):
        errors.append("runbook.interruption_procedure ausente")
    if not rb.get("cleanup_procedure"):
        errors.append("runbook.cleanup_procedure ausente")
    if not rb.get("rollback_procedure"):
        errors.append("runbook.rollback_procedure ausente")

    # Referências cruzadas.
    if rb.get("plan_reference") != PLAN_REF:
        errors.append("runbook.plan_reference incorreto")
    if rb.get("authorization_reference") != AUTHORIZATION_REF:
        errors.append("runbook.authorization_reference incorreto")
    if rb.get("evidence_reference") != EVIDENCE_REF:
        errors.append("runbook.evidence_reference incorreto")


# ---------------------------------------------------------------------------
# Regras de negócio: AUTORIZAÇÃO (template, não concedida).
# ---------------------------------------------------------------------------
def check_authorization(au, overlay_sha, errors):
    if au.get("authorization_state") != "template-not-granted":
        errors.append("authorization.authorization_state deve ser template-not-granted")
    for k in ("authorization_granted", "execution_permitted", "authorization_used",
              "authorization_revoked", "read_risks_confirmed", "go_no_go_confirmed"):
        if au.get(k) is not False:
            errors.append("authorization.%s deve ser false nesta etapa" % k)
    for k in ("single_use", "required_before_execution"):
        if au.get(k) is not True:
            errors.append("authorization.%s deve ser true" % k)

    b = au.get("binding", {})
    if b.get("upstream_commit") != EXPECTED_COMMIT:
        errors.append("authorization.binding.upstream_commit != commit fixado")
    if b.get("upstream_tree_digest") != EXPECTED_TREE_DIGEST:
        errors.append("authorization.binding.upstream_tree_digest divergente")
    if b.get("overlay_path") != OVERLAY_PATH:
        errors.append("authorization.binding.overlay_path incorreto")
    if b.get("overlay_sha256") != overlay_sha:
        errors.append("authorization.binding.overlay_sha256 divergente do overlay real")
    if b.get("toolchain") != REQUIRED_TOOLCHAIN:
        errors.append("authorization.binding.toolchain incorreta")
    if b.get("preserved_default_toolchain") != PRESERVED_TOOLCHAIN:
        errors.append("authorization.binding.preserved_default_toolchain incorreta")
    if b.get("target") != "x86_64-pc-windows-msvc":
        errors.append("authorization.binding.target incorreto")
    # Vínculo humano/futuro: deve estar em placeholder (decisão ainda não tomada),
    # nunca já preenchido como se aprovado.
    for k in ("faithro_commit", "runbook_sha", "authorized_host_label"):
        if not is_placeholder(b.get(k)):
            errors.append("authorization.binding.%s deve ser placeholder no template (decisão pendente)" % k)
    for k in ("authorization_id", "authorizer", "authorization_timestamp_utc", "justification"):
        if not is_placeholder(au.get(k)):
            errors.append("authorization.%s deve ser placeholder no template (decisão pendente)" % k)

    # Janela obrigatória e limitada. No template, os instantes ainda são decisão
    # humana pendente: devem permanecer placeholders (nunca uma data concreta,
    # que poderia representar uma janela já preenchida ou expirada).
    w = au.get("validity_window", {})
    if not is_placeholder(w.get("not_before_utc")):
        errors.append("authorization.validity_window.not_before_utc deve ser placeholder no template")
    if not is_placeholder(w.get("not_after_utc")):
        errors.append("authorization.validity_window.not_after_utc deve ser placeholder no template (sem data concreta/expiração)")
    if w.get("unlimited_window_forbidden") is not True:
        errors.append("authorization.validity_window.unlimited_window_forbidden deve ser true")
    mdh = w.get("max_duration_hours")
    if not isinstance(mdh, int) or isinstance(mdh, bool) or mdh < 1 or mdh > 24:
        errors.append("authorization.validity_window.max_duration_hours deve ser 1..24 (janela limitada)")

    # Escopo e proibições não vazios.
    if not au.get("allowed_scope"):
        errors.append("authorization.allowed_scope ausente")
    if not au.get("forbidden_actions"):
        errors.append("authorization.forbidden_actions ausente")

    rev = au.get("revocation", {})
    if rev.get("revocable") is not True:
        errors.append("authorization.revocation.revocable deve ser true")
    if rev.get("revoked") is not False:
        errors.append("authorization.revocation.revoked deve ser false")

    eb = au.get("evidence_binding", {})
    if eb.get("requires_evidence") is not True:
        errors.append("authorization.evidence_binding.requires_evidence deve ser true")
    if eb.get("evidence_completed") is not False:
        errors.append("authorization.evidence_binding.evidence_completed deve ser false")
    if eb.get("evidence_reference") != EVIDENCE_REF:
        errors.append("authorization.evidence_binding.evidence_reference incorreto")

    if au.get("runbook_reference") != RUNBOOK_REF:
        errors.append("authorization.runbook_reference incorreto")


# ---------------------------------------------------------------------------
# Regras de negócio: EVIDÊNCIA (template, execução não iniciada).
# ---------------------------------------------------------------------------
def check_evidence(ev, overlay_sha, errors):
    if ev.get("evidence_state") != "template-not-executed":
        errors.append("evidence.evidence_state deve ser template-not-executed")

    pf = ev.get("process_flags", {})
    for k in ("execution_started", "build_started", "build_completed",
              "binary_produced", "binary_executed", "deploy_performed", "vps_accessed"):
        if pf.get(k) is not False:
            errors.append("evidence.process_flags.%s deve ser false" % k)

    idy = ev.get("identity", {})
    if idy.get("beam_commit") != EXPECTED_COMMIT:
        errors.append("evidence.identity.beam_commit != commit fixado")
    if idy.get("beam_tree_digest") != EXPECTED_TREE_DIGEST:
        errors.append("evidence.identity.beam_tree_digest divergente")
    if idy.get("overlay_sha256") != overlay_sha:
        errors.append("evidence.identity.overlay_sha256 divergente do overlay real")
    for k in ("runbook_sha", "authorization_id", "faithro_commit", "host_label",
              "started_utc", "ended_utc"):
        if idy.get(k) != "<PENDENTE>":
            errors.append("evidence.identity.%s deve ser <PENDENTE> (execução não iniciada)" % k)

    # Baseline e estado final: strings devem ser <PENDENTE> no template.
    base = ev.get("baseline", {})
    for k, v in base.items():
        if isinstance(v, str) and v != "<PENDENTE>":
            errors.append("evidence.baseline.%s deve ser <PENDENTE> no template" % k)
    if base.get("vps_absent_confirmed") is not True:
        errors.append("evidence.baseline.vps_absent_confirmed deve ser true")

    ex = ev.get("execution", {})
    for k in ("steps", "executed_commands", "downloaded_files", "produced_artifacts"):
        if ex.get(k) != []:
            errors.append("evidence.execution.%s deve estar vazio (nenhuma execução)" % k)
    if ex.get("interrupted") is not False:
        errors.append("evidence.execution.interrupted deve ser false")

    fs = ev.get("final_state", {})
    for k, v in fs.items():
        if isinstance(v, str) and v != "<PENDENTE>":
            errors.append("evidence.final_state.%s deve ser <PENDENTE> no template" % k)
    for k in ("binary_produced", "binary_executed", "deploy_performed",
              "vps_accessed", "cleanup_done"):
        if fs.get(k) is not False:
            errors.append("evidence.final_state.%s deve ser false" % k)
    for k in ("files_outside_workspace", "divergences"):
        if fs.get(k) != []:
            errors.append("evidence.final_state.%s deve estar vazio" % k)

    if ev.get("runbook_reference") != RUNBOOK_REF:
        errors.append("evidence.runbook_reference incorreto")
    if ev.get("authorization_reference") != AUTHORIZATION_REF:
        errors.append("evidence.authorization_reference incorreto")


def check_no_build_binaries(errors):
    forbidden_exts = {".exe", ".dll", ".pdb", ".msi", ".zip", ".grf", ".beam"}
    base = os.path.join(REPO, "client", "patcher")
    for root, _, files in os.walk(base):
        for f in files:
            if os.path.splitext(f)[1].lower() in forbidden_exts:
                errors.append("binário proibido versionado: %s" % os.path.join(root, f))


# ---------------------------------------------------------------------------
# Orquestração validável (importável pelos testes negativos).
# ---------------------------------------------------------------------------
def validate_all(runbook, authorization, evidence, manifest, plan,
                 rb_schema, au_schema, ev_schema, overlay_sha, scan_binaries=True):
    errors = []
    schema_check(runbook, rb_schema, "runbook", errors)
    schema_check(authorization, au_schema, "authorization", errors)
    schema_check(evidence, ev_schema, "evidence", errors)
    check_no_forbidden(runbook, "runbook", errors)
    check_no_forbidden(authorization, "authorization", errors)
    check_no_forbidden(evidence, "evidence", errors)
    check_runbook(runbook, manifest, plan, overlay_sha, errors)
    check_authorization(authorization, overlay_sha, errors)
    check_evidence(evidence, overlay_sha, errors)
    if scan_binaries:
        check_no_build_binaries(errors)
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Valida runbook, autorização e evidência do primeiro build "
                    "controlado do Beam Patcher (offline; não clona, não instala, "
                    "não constrói, não executa).")
    parser.add_argument("--runbook", default=os.path.join(BEAM_AUDIT, "first-build-runbook.example.json"))
    parser.add_argument("--authorization", default=os.path.join(BEAM_AUDIT, "first-build-authorization.example.json"))
    parser.add_argument("--evidence", default=os.path.join(BEAM_AUDIT, "first-build-execution-evidence.example.json"))
    parser.add_argument("--manifest", default=os.path.join(BEAM_AUDIT, "upstream-manifest.example.json"))
    parser.add_argument("--plan", default=os.path.join(BEAM_AUDIT, "first-build-plan.example.json"))
    args = parser.parse_args(argv)

    try:
        runbook = load_json(args.runbook)
        authorization = load_json(args.authorization)
        evidence = load_json(args.evidence)
        manifest = load_json(args.manifest)
        plan = load_json(args.plan)
        rb_schema = load_json(os.path.join(SCHEMAS, "first-build-runbook.schema.json"))
        au_schema = load_json(os.path.join(SCHEMAS, "first-build-authorization.schema.json"))
        ev_schema = load_json(os.path.join(SCHEMAS, "first-build-execution-evidence.schema.json"))
    except (OSError, ValueError) as e:
        print("ERRO ao carregar JSON: %s" % e, file=sys.stderr)
        return 2

    overlay_file = os.path.join(REPO, OVERLAY_PATH)
    if not os.path.isfile(overlay_file):
        print("ERRO: overlay não encontrado: %s" % OVERLAY_PATH, file=sys.stderr)
        return 2
    overlay_sha = sha256_file(overlay_file)

    errors = validate_all(runbook, authorization, evidence, manifest, plan,
                          rb_schema, au_schema, ev_schema, overlay_sha)

    if errors:
        print("Runbook/autorização/evidência do primeiro build: FAIL")
        for e in errors:
            print("  - " + e)
        return 1

    print("Runbook/autorização/evidência do primeiro build: OK")
    print("governance=%s | beam=%s | overlay_sha=%s"
          % (runbook["governance_commit"][:10], runbook["source"]["commit"][:10], overlay_sha[:10]))
    print("authorization_granted=%s | execution_permitted=%s | evidence_state=%s"
          % (authorization["authorization_granted"], authorization["execution_permitted"],
             evidence["evidence_state"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
