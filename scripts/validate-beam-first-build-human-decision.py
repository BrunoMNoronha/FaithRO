#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador estático do PACOTE DE DECISÃO HUMANA e do REGISTRO DE DECISÃO (formulário
não preenchido) do primeiro build controlado do Beam Patcher (ETAPA 2O-D1-B14).

Valida, de forma determinística e offline, os artefatos VERSIONADOS:
  * client/patcher/beam-audit/first-build-human-decision-package.example.json
  * client/patcher/beam-audit/first-build-human-decision-record.example.json
contra os schemas em client/patcher/beam-audit/schemas/, recomputando os hashes
reais dos artefatos referenciados e conferindo o fim de linha canônico (LF).

Confirma que:
  * o pacote NÃO concede autorização e NÃO permite execução;
  * o registro representa APENAS o estado pendente (nenhuma decisão, nenhuma
    identidade, nenhuma janela, nenhuma autorização);
  * os SHA-256 declarados coincidem, byte a byte, com os arquivos reais;
  * os arquivos com hash estão em LF (o hash persistido é reproduzível);
  * a solicitação, o runbook e a autorização referenciados permanecem bloqueados.

Este validador NÃO clona o Beam, NÃO instala nada, NÃO resolve dependências,
NÃO executa build, NÃO executa binário, NÃO executa Git/Rust/Cargo/PowerShell,
NÃO grava no repositório e NÃO acessa a rede. Não normaliza silenciosamente:
verifica os bytes reais e sinaliza CRLF como erro.

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

# Âncoras canônicas desta etapa.
EXPECTED_FAITHRO_COMMIT = "4251c373a8bcdbb9e49369668711d64d8140aad3"
EXPECTED_PR = 39
REQUIRED_TOOLCHAIN = "1.85.0-x86_64-pc-windows-msvc"
PRESERVED_TOOLCHAIN = "1.77.2-x86_64-pc-windows-msvc"

PACKAGE_REF = "client/patcher/beam-audit/first-build-human-decision-package.example.json"
RECORD_REF = "client/patcher/beam-audit/first-build-human-decision-record.example.json"
REQUEST_REF = "client/patcher/beam-audit/first-build-authorization-request.example.json"
RUNBOOK_REF = "client/patcher/beam-audit/first-build-runbook.example.json"
AUTHORIZATION_REF = "client/patcher/beam-audit/first-build-authorization.example.json"
PLAN_REF = "client/patcher/beam-audit/first-build-plan.example.json"
DOCUMENT_REF = "docs/26-pacote-decisao-humana-primeiro-build-beam.md"

# role -> caminho do artefato referenciado (cujo hash é persistido).
HASHED_ARTIFACTS = {
    "authorization_request": REQUEST_REF,
    "runbook": RUNBOOK_REF,
    "authorization_template": AUTHORIZATION_REF,
    "build_plan": PLAN_REF,
}

OFFICIAL_HOSTS = (
    "github.com", "static.rust-lang.org", "crates.io",
    "index.crates.io", "static.crates.io", "win.rustup.rs",
    "rust-lang.org", "forge.rust-lang.org",
)

URL_RE = re.compile(r"(?i)\bhttps?://([a-z0-9._-]+)")
FILE_URL = re.compile(r"(?i)\bfile://")
ABS_PATH = re.compile(r"(?i)(^|[\s\"'=:])([a-z]:[\\/]|/(?:home|users|etc|root|var|opt|mnt)/)")
PERSONAL_PATH = re.compile(r"(?i)([a-z]:\\users\\[^\\/\"']+|/home/[^/\"']+|/users/[^/\"']+)")
CRED_KEY = re.compile(
    r"(?i)(password|passwd|senha|secret|client_secret|token|api[_-]?key|bearer)$")
PIPE_TO_SHELL = re.compile(
    r"(?i)(curl[^\n]*\|\s*(sh|bash)|wget[^\n]*\|\s*(sh|bash)|"
    r"\birm\b[^\n]*\|\s*iex|iwr[^\n]*\|\s*iex|\|\s*iex\b)")
SECRET_VALUE = re.compile(
    r"(?i)(gh[pousr]_[a-z0-9]{20,}|AKIA[0-9A-Z]{12,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[baprs]-[a-z0-9-]{10,})")
EMAIL_RE = re.compile(r"(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b")
IPV4 = re.compile(r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b")
PROPRIETARY = re.compile(r"(?i)(\.grf\b|\.gpf\b|\.rgz\b|\bragexe\b|data\.grf|\.gr2\b)")

FORBIDDEN_TOKENS = [
    (re.compile(r"\.\.[\\/]"), "usa travessia de diretório (..)"),
    (re.compile(r"(?i)\bcmd(\.exe)?\s+/c\b"), "usa wrapper cmd /c"),
    (re.compile(r"(?i)\b(powershell|pwsh)(\.exe)?\b[^\n]*\s-(c|command|enc|encodedcommand)\b"),
     "usa wrapper powershell -Command/-EncodedCommand"),
    (re.compile(r"(?i)\b(bash|sh|zsh|dash)\b\s+-c\b"), "usa wrapper de shell POSIX -c"),
    (re.compile(r"(?i)\b(invoke-expression|iex)\b"), "usa Invoke-Expression"),
    (re.compile(r"(?i)\b(invoke-webrequest|iwr|curl|wget|start-bitstransfer)\b"),
     "usa verbo de download"),
    (re.compile(r"(?i)\bgit\s+clone\b"), "usa git clone"),
    (re.compile(r"(?i)\bssh\b|faithro-vps|\bscp\b|\bsftp\b"), "referencia acesso a VPS"),
    (re.compile(r"&"), "usa operador de chamada/concatenação &"),
    (re.compile(r"[;|`]"), "usa metacaractere de shell (; | `)"),
    (re.compile(r"\$[({]"), "usa substituição de shell $(...) ou ${...}"),
    (re.compile(r"(?i)\b(rm|rmdir|del|erase|format|mkfs|shutdown|reboot|"
                r"taskkill|schtasks|icacls|takeown|attrib)\b\s+[-/]?\S"),
     "usa verbo de comando destrutivo"),
    (re.compile(r"[<>]"), "usa redirecionamento/sinal de shell (< ou >)"),
    (re.compile(r"[\r\n]"), "contém quebra de linha embutida"),
]

# Chaves cujo valor é, legitimamente, um caminho relativo versionado do repo.
_PATH_KEYS = {
    "document_reference", "package_reference", "request_reference",
    "authorization_reference", "decision_record_reference", "path", "artifact",
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------------------
# Mini-validador de JSON Schema (subconjunto).
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
    if "maxLength" in schema and isinstance(data, str) and len(data) > schema["maxLength"]:
        errors.append("%s: string longa demais" % where)
    if "minimum" in schema and isinstance(data, int) and not isinstance(data, bool):
        if data < schema["minimum"]:
            errors.append("%s: valor abaixo do mínimo" % where)
    if "maximum" in schema and isinstance(data, int) and not isinstance(data, bool):
        if data > schema["maximum"]:
            errors.append("%s: valor acima do máximo" % where)
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
            errors.append("%s: lista com itens em excesso" % where)
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(data):
                schema_check(item, item_schema, "%s[%d]" % (where, i), errors)


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
        leaf = keypath.split(".")[-1].split("[")[0]
        if PIPE_TO_SHELL.search(s):
            errors.append("%s%s: comando pipe-to-shell proibido: %s" % (label, keypath, s[:80]))
        if PERSONAL_PATH.search(s):
            errors.append("%s%s: possível caminho pessoal: %s" % (label, keypath, s[:80]))
        if FILE_URL.search(s):
            errors.append("%s%s: link file:// proibido: %s" % (label, keypath, s[:80]))
        if leaf not in _PATH_KEYS and ABS_PATH.search(s):
            errors.append("%s%s: caminho absoluto proibido: %s" % (label, keypath, s[:80]))
        if SECRET_VALUE.search(s):
            errors.append("%s%s: possível segredo/token/chave: %s" % (label, keypath, s[:40]))
        if EMAIL_RE.search(s):
            errors.append("%s%s: possível e-mail: %s" % (label, keypath, s[:60]))
        if PROPRIETARY.search(s):
            errors.append("%s%s: possível asset proprietário: %s" % (label, keypath, s[:60]))
        ip = _public_ip(s)
        if ip:
            errors.append("%s%s: possível IP público: %s" % (label, keypath, ip))
        for m in URL_RE.finditer(s):
            host = m.group(1)
            if not any(host == h or host.endswith("." + h) for h in OFFICIAL_HOSTS):
                errors.append("%s%s: URL de host não oficial: %s" % (label, keypath, host))
        for rx, why in FORBIDDEN_TOKENS:
            if rx.search(s):
                errors.append("%s%s: %s: %s" % (label, keypath, why, s[:80]))
        if CRED_KEY.search(leaf):
            v = s.strip()
            if v:
                errors.append("%s%s: possível segredo em campo sensível" % (label, keypath))


# ---------------------------------------------------------------------------
# Recomputação de hash + verificação de EOL canônico (LF).
# ---------------------------------------------------------------------------
def real_sha_and_eol(rel_path):
    abspath = os.path.join(REPO, rel_path)
    if not os.path.isfile(abspath):
        return None, None
    raw = read_bytes(abspath)
    has_crlf = b"\r\n" in raw
    return sha256_bytes(raw), has_crlf


# ---------------------------------------------------------------------------
# Regras de negócio: PACOTE.
# ---------------------------------------------------------------------------
def check_package(pkg, request, runbook, authorization, errors):
    if pkg.get("faithro_reference_commit") != EXPECTED_FAITHRO_COMMIT:
        errors.append("package.faithro_reference_commit != commit da integração (%s)" % EXPECTED_FAITHRO_COMMIT)
    for k in ("grants_authorization", "permits_execution", "decision_recorded"):
        if pkg.get(k) is not False:
            errors.append("package.%s deve ser false" % k)
    for k in ("grant_is_separate_artifact", "merge_is_not_authorization", "decision_is_not_execution"):
        if pkg.get(k) is not True:
            errors.append("package.%s deve ser true" % k)

    pri = pkg.get("pr_integration", {})
    if not isinstance(pri, dict):
        pri = {}
    if pri.get("pr_number") != EXPECTED_PR:
        errors.append("package.pr_integration.pr_number != %d" % EXPECTED_PR)
    if pri.get("merge_commit") != EXPECTED_FAITHRO_COMMIT:
        errors.append("package.pr_integration.merge_commit != merge do PR #39")

    rr = pkg.get("request_reference", {})
    if not isinstance(rr, dict):
        rr = {}
    if rr.get("path") != REQUEST_REF:
        errors.append("package.request_reference.path incorreto")
    if rr.get("expected_request_status") != "PENDING_HUMAN_DECISION":
        errors.append("package.request_reference.expected_request_status incorreto")
    req_sha, req_crlf = real_sha_and_eol(REQUEST_REF)
    if req_sha is not None:
        if rr.get("sha256") != req_sha:
            errors.append("package.request_reference.sha256 divergente do arquivo real (%s)" % req_sha)
        if req_crlf:
            errors.append("solicitação referenciada NÃO está em LF (hash não reproduzível)")

    if pkg.get("decision_record_reference") != RECORD_REF:
        errors.append("package.decision_record_reference incorreto")

    # Artefatos referenciados: papéis, caminhos, hashes reais e EOL canônico.
    arts = pkg.get("referenced_artifacts", [])
    if not isinstance(arts, list):
        arts = []
    seen_roles = []
    for i, a in enumerate(arts):
        if not isinstance(a, dict):
            errors.append("package.referenced_artifacts[%d] não é objeto" % i)
            continue
        role = a.get("role")
        seen_roles.append(role)
        expected_path = HASHED_ARTIFACTS.get(role)
        if expected_path is None:
            errors.append("package.referenced_artifacts[%d]: papel desconhecido: %r" % (i, role))
            continue
        if a.get("path") != expected_path:
            errors.append("package.referenced_artifacts[%d] (%s): caminho incorreto" % (i, role))
        if a.get("eol") != "lf":
            errors.append("package.referenced_artifacts[%d] (%s): eol deve ser lf" % (i, role))
        real_sha, has_crlf = real_sha_and_eol(expected_path)
        if real_sha is None:
            errors.append("package.referenced_artifacts[%d] (%s): arquivo inexistente" % (i, role))
            continue
        if a.get("sha256") != real_sha:
            errors.append("package.referenced_artifacts[%d] (%s): sha256 divergente do real (%s)"
                          % (i, role, real_sha))
        if has_crlf:
            errors.append("package.referenced_artifacts[%d] (%s): arquivo NÃO está em LF (hash não reproduzível)"
                          % (i, role))
    for role in HASHED_ARTIFACTS:
        if seen_roles.count(role) != 1:
            errors.append("package.referenced_artifacts: papel obrigatório ausente ou repetido: %s" % role)

    tc = pkg.get("toolchain", {})
    if not isinstance(tc, dict):
        tc = {}
    if tc.get("required_toolchain") != REQUIRED_TOOLCHAIN:
        errors.append("package.toolchain.required_toolchain incorreta")
    if tc.get("preserved_default_toolchain") != PRESERVED_TOOLCHAIN:
        errors.append("package.toolchain.preserved_default_toolchain incorreta")

    for k in ("presented_scope", "permanently_forbidden", "risks", "authority_criteria",
              "approval_rules", "refusal_rules", "single_use_rules", "revocation_rules",
              "decision_checklist", "delivery_procedure", "return_procedure"):
        if not pkg.get(k):
            errors.append("package.%s ausente" % k)

    # Cross-check: solicitação referenciada permanece PENDENTE e não concedida.
    if isinstance(request, dict):
        if request.get("request_status") != "PENDING_HUMAN_DECISION":
            errors.append("solicitação referenciada não está PENDING_HUMAN_DECISION")
        for k in ("authorization_granted", "execution_permitted"):
            if request.get(k) is not False:
                errors.append("solicitação referenciada NÃO está bloqueada: %s != false" % k)

    # Cross-check: runbook e autorização referenciados permanecem bloqueados.
    if isinstance(runbook, dict):
        ps = runbook.get("process_state", {})
        if not isinstance(ps, dict):
            ps = {}
        for k in ("human_authorization_granted", "execution_authorized", "build_started",
                  "binary_produced", "binary_executed", "deploy_performed", "vps_accessed"):
            if ps.get(k) is not False:
                errors.append("runbook referenciado NÃO está bloqueado: process_state.%s != false" % k)
        if runbook.get("executes_build") is not False:
            errors.append("runbook referenciado declara executes_build != false")
    if isinstance(authorization, dict):
        for k in ("authorization_granted", "execution_permitted", "authorization_used"):
            if authorization.get(k) is not False:
                errors.append("autorização referenciada NÃO está bloqueada: %s != false" % k)
        if authorization.get("authorization_state") != "template-not-granted":
            errors.append("autorização referenciada não está em template-not-granted")


# ---------------------------------------------------------------------------
# Regras de negócio: REGISTRO (formulário em branco, pendente).
# ---------------------------------------------------------------------------
def check_record(rec, errors):
    if rec.get("decision_status") != "PENDING":
        errors.append("record.decision_status deve ser PENDING")
    if rec.get("decision") is not None:
        errors.append("record.decision deve ser null (nenhuma decisão)")
    for k in ("authorization_granted", "execution_permitted", "authorization_used",
              "authorization_revoked", "decision_recorded", "build_started",
              "beam_downloaded", "binary_produced"):
        if rec.get(k) is not False:
            errors.append("record.%s deve ser false" % k)
    if rec.get("single_use_required") is not True:
        errors.append("record.single_use_required deve ser true")

    au = rec.get("authority", {})
    if not isinstance(au, dict):
        au = {}
    for k in ("identifier", "role", "authority_basis", "verifiable_channel",
              "auditable_reference", "decision_timestamp_utc"):
        if au.get(k) is not None:
            errors.append("record.authority.%s deve ser null (sem identidade inventada)" % k)
    if au.get("identity_confirmed") is not False:
        errors.append("record.authority.identity_confirmed deve ser false")

    ap = rec.get("approval", {})
    if not isinstance(ap, dict):
        ap = {}
    for k in ("window_not_before_utc", "window_not_after_utc", "justification",
              "confirmed_faithro_commit", "confirmed_request_sha256", "confirmed_runbook_sha256"):
        if ap.get(k) is not None:
            errors.append("record.approval.%s deve ser null (sem aprovação preenchida)" % k)
    if ap.get("single_use_confirmed") is not False:
        errors.append("record.approval.single_use_confirmed deve ser false")

    rf = rec.get("refusal", {})
    if not isinstance(rf, dict):
        rf = {}
    for k in ("justification", "unmet_conditions"):
        if rf.get(k) is not None:
            errors.append("record.refusal.%s deve ser null (sem recusa preenchida)" % k)

    rev = rec.get("revocation", {})
    if not isinstance(rev, dict):
        rev = {}
    if rev.get("revoked") is not False:
        errors.append("record.revocation.revoked deve ser false")

    if rec.get("package_reference") != PACKAGE_REF:
        errors.append("record.package_reference incorreto")


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
def validate_all(package, record, request, runbook, authorization,
                 pkg_schema, rec_schema, scan_binaries=True):
    errors = []
    schema_check(package, pkg_schema, "package", errors)
    schema_check(record, rec_schema, "record", errors)
    check_no_forbidden(package, "package", errors)
    check_no_forbidden(record, "record", errors)
    check_package(package, request, runbook, authorization, errors)
    check_record(record, errors)
    if scan_binaries:
        check_no_build_binaries(errors)
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Valida o pacote de decisão humana e o registro de decisão do "
                    "primeiro build controlado do Beam Patcher (offline; não clona, "
                    "não instala, não constrói, não executa, não decide, não autoriza).")
    parser.add_argument("--package", default=os.path.join(BEAM_AUDIT, "first-build-human-decision-package.example.json"))
    parser.add_argument("--record", default=os.path.join(BEAM_AUDIT, "first-build-human-decision-record.example.json"))
    parser.add_argument("--request", default=os.path.join(BEAM_AUDIT, "first-build-authorization-request.example.json"))
    parser.add_argument("--runbook", default=os.path.join(BEAM_AUDIT, "first-build-runbook.example.json"))
    parser.add_argument("--authorization", default=os.path.join(BEAM_AUDIT, "first-build-authorization.example.json"))
    args = parser.parse_args(argv)

    try:
        package = load_json(args.package)
        record = load_json(args.record)
        request = load_json(args.request)
        runbook = load_json(args.runbook)
        authorization = load_json(args.authorization)
        pkg_schema = load_json(os.path.join(SCHEMAS, "first-build-human-decision-package.schema.json"))
        rec_schema = load_json(os.path.join(SCHEMAS, "first-build-human-decision-record.schema.json"))
    except (OSError, ValueError) as e:
        print("ERRO ao carregar JSON: %s" % e, file=sys.stderr)
        return 2

    errors = validate_all(package, record, request, runbook, authorization,
                          pkg_schema, rec_schema)

    if errors:
        print("Pacote/registro de decisão humana do primeiro build: FAIL")
        for e in errors:
            print("  - " + e)
        return 1

    print("Pacote/registro de decisão humana do primeiro build: OK")
    print("faithro=%s | pr=#%d | artefatos referenciados=%d"
          % (package["faithro_reference_commit"][:10], EXPECTED_PR,
             len(package.get("referenced_artifacts", []))))
    print("grants_authorization=%s | permits_execution=%s | decision_status=%s"
          % (package["grants_authorization"], package["permits_execution"],
             record["decision_status"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
