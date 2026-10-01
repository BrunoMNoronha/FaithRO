#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador estático do MANIFESTO DE APRESENTACAO e do COMPROVANTE DE ENTREGA
(formulário não preenchido) da apresentacao controlada do pacote de decisao do
primeiro build controlado do Beam Patcher (ETAPA 2O-D1-B16).

Valida, de forma determinística e offline, os artefatos VERSIONADOS:
  * client/patcher/beam-audit/first-build-human-presentation-manifest.example.json
  * client/patcher/beam-audit/first-build-human-presentation-receipt.example.json
contra os schemas, recomputando os hashes reais dos artefatos apresentados e
conferindo o fim de linha canônico (LF).

Confirma que:
  * o manifesto está em estado NAO apresentado e NAO seleciona canal, NAO
    identifica decisor, NAO registra decisao e NAO concede autorizacao;
  * o comprovante representa APENAS o estado anterior a apresentacao (nenhuma
    entrega, nenhum recebimento, nenhuma identidade, nenhuma decisao);
  * os SHA-256 declarados coincidem, byte a byte, com os arquivos reais;
  * os arquivos apresentados estão em LF (hash reproduzível);
  * o pacote, o registro, a solicitacao e a autorizacao continuam bloqueados.

Este validador NAO clona o Beam, NAO instala nada, NAO resolve dependências,
NAO executa build, NAO executa binário, NAO executa Git/Rust/Cargo/PowerShell,
NAO grava no repositório, NAO envia comunicacao e NAO acessa a rede. Não
normaliza silenciosamente: verifica os bytes reais e sinaliza CRLF como erro.

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
EXPECTED_FAITHRO_COMMIT = "c5473a22c4c4fb301e91f35779a83d9bc4bca99a"
EXPECTED_PR = 40

MANIFEST_REF = "client/patcher/beam-audit/first-build-human-presentation-manifest.example.json"
RECEIPT_REF = "client/patcher/beam-audit/first-build-human-presentation-receipt.example.json"
PACKAGE_REF = "client/patcher/beam-audit/first-build-human-decision-package.example.json"
RECORD_REF = "client/patcher/beam-audit/first-build-human-decision-record.example.json"
REQUEST_REF = "client/patcher/beam-audit/first-build-authorization-request.example.json"
RUNBOOK_REF = "client/patcher/beam-audit/first-build-runbook.example.json"
AUTHORIZATION_REF = "client/patcher/beam-audit/first-build-authorization.example.json"
PLAN_REF = "client/patcher/beam-audit/first-build-plan.example.json"
DOCUMENT_REF = "docs/27-apresentacao-controlada-pacote-decisao-beam.md"

# role -> caminho do artefato apresentado (cujo hash é persistido).
PRESENTED_ARTIFACTS = {
    "decision_package": PACKAGE_REF,
    "decision_record": RECORD_REF,
    "authorization_request": REQUEST_REF,
    "runbook": RUNBOOK_REF,
    "build_plan": PLAN_REF,
    "authorization_template": AUTHORIZATION_REF,
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
    r"(?i)(password|passwd|senha|secret|client_secret|token|api[_-]?key|bearer|cookie)$")
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
    "document_reference", "manifest_reference", "package_reference",
    "decision_record_reference", "receipt_reference", "path",
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


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
    return hashlib.sha256(raw).hexdigest(), has_crlf


# ---------------------------------------------------------------------------
# Regras de negócio: MANIFESTO.
# ---------------------------------------------------------------------------
def check_manifest(man, package, record, request, runbook, authorization, errors):
    if man.get("faithro_reference_commit") != EXPECTED_FAITHRO_COMMIT:
        errors.append("manifest.faithro_reference_commit != commit da integração (%s)" % EXPECTED_FAITHRO_COMMIT)
    if man.get("presentation_status") != "NOT_PRESENTED":
        errors.append("manifest.presentation_status deve ser NOT_PRESENTED")
    for k in ("channel_selected", "decision_maker_identified", "authority_verified",
              "package_delivered", "package_received", "decision_requested",
              "decision_received", "authorization_granted", "execution_permitted",
              "build_started", "beam_downloaded", "binary_produced"):
        if man.get(k) is not False:
            errors.append("manifest.%s deve ser false" % k)
    for k in ("presentation_is_not_decision", "receipt_is_not_decision",
              "decision_is_not_authorization", "decision_is_not_execution",
              "merge_is_not_presentation"):
        if man.get(k) is not True:
            errors.append("manifest.%s deve ser true" % k)

    pri = man.get("pr_integration", {})
    if not isinstance(pri, dict):
        pri = {}
    if pri.get("pr_number") != EXPECTED_PR:
        errors.append("manifest.pr_integration.pr_number != %d" % EXPECTED_PR)
    if pri.get("merge_commit") != EXPECTED_FAITHRO_COMMIT:
        errors.append("manifest.pr_integration.merge_commit != merge do PR #40")

    if man.get("receipt_reference") != RECEIPT_REF:
        errors.append("manifest.receipt_reference incorreto")

    ast = man.get("authority_state", {})
    if not isinstance(ast, dict):
        ast = {}
    for k in ("decision_maker_identified", "identity_confirmed", "authority_confirmed"):
        if ast.get(k) is not False:
            errors.append("manifest.authority_state.%s deve ser false" % k)
    for k in ("inferred_from_repository_owner_forbidden", "inferred_from_github_user_forbidden",
              "lookup_in_contacts_or_email_forbidden"):
        if ast.get(k) is not True:
            errors.append("manifest.authority_state.%s deve ser true" % k)

    # Artefatos apresentados: papéis, caminhos, hashes reais e EOL canônico.
    arts = man.get("presented_artifacts", [])
    if not isinstance(arts, list):
        arts = []
    seen = []
    for i, a in enumerate(arts):
        if not isinstance(a, dict):
            errors.append("manifest.presented_artifacts[%d] não é objeto" % i)
            continue
        role = a.get("role")
        seen.append(role)
        expected_path = PRESENTED_ARTIFACTS.get(role)
        if expected_path is None:
            errors.append("manifest.presented_artifacts[%d]: papel desconhecido: %r" % (i, role))
            continue
        if a.get("path") != expected_path:
            errors.append("manifest.presented_artifacts[%d] (%s): caminho incorreto" % (i, role))
        if a.get("eol") != "lf":
            errors.append("manifest.presented_artifacts[%d] (%s): eol deve ser lf" % (i, role))
        real_sha, has_crlf = real_sha_and_eol(expected_path)
        if real_sha is None:
            errors.append("manifest.presented_artifacts[%d] (%s): arquivo inexistente" % (i, role))
            continue
        if a.get("sha256") != real_sha:
            errors.append("manifest.presented_artifacts[%d] (%s): sha256 divergente do real (%s)"
                          % (i, role, real_sha))
        if has_crlf:
            errors.append("manifest.presented_artifacts[%d] (%s): arquivo NÃO está em LF (hash não reproduzível)"
                          % (i, role))
    for role in PRESENTED_ARTIFACTS:
        if seen.count(role) != 1:
            errors.append("manifest.presented_artifacts: papel obrigatório ausente ou repetido: %s" % role)

    for k in ("presentation_content", "allowed_channel_categories", "channel_requirements",
              "authority_requirements", "pre_presentation_checklist", "integrity_procedure",
              "delivery_record_fields", "return_procedure", "acceptance_criteria",
              "permanently_forbidden"):
        if not man.get(k):
            errors.append("manifest.%s ausente" % k)

    _cross_check_blocked(package, record, request, runbook, authorization, errors)


# ---------------------------------------------------------------------------
# Regras de negócio: COMPROVANTE (formulário em branco, não apresentado).
# ---------------------------------------------------------------------------
def check_receipt(rec, errors):
    if rec.get("presentation_status") != "NOT_PRESENTED":
        errors.append("receipt.presentation_status deve ser NOT_PRESENTED")
    for k in ("channel_selected", "delivered", "received", "recipient_identity_confirmed",
              "authority_confirmed", "package_integrity_confirmed", "decision_requested",
              "decision_received", "authorization_granted", "execution_permitted",
              "build_started", "beam_downloaded", "binary_produced"):
        if rec.get(k) is not False:
            errors.append("receipt.%s deve ser false" % k)

    ch = rec.get("channel", {})
    if not isinstance(ch, dict):
        ch = {}
    for k in ("category", "reference", "access_controlled", "sender", "recipient", "presented_utc"):
        if ch.get(k) is not None:
            errors.append("receipt.channel.%s deve ser null (nenhum canal selecionado)" % k)

    rp = rec.get("recipient", {})
    if not isinstance(rp, dict):
        rp = {}
    for k in ("identifier", "role", "authority_basis", "contact_channel", "designation_reference"):
        if rp.get(k) is not None:
            errors.append("receipt.recipient.%s deve ser null (sem identidade)" % k)

    dl = rec.get("delivery", {})
    if not isinstance(dl, dict):
        dl = {}
    for k in ("delivered_utc", "delivery_reference", "presented_version",
              "presented_manifest_sha256", "integrity_report_reference"):
        if dl.get(k) is not None:
            errors.append("receipt.delivery.%s deve ser null (nenhuma entrega)" % k)

    if rec.get("manifest_reference") != MANIFEST_REF:
        errors.append("receipt.manifest_reference incorreto")


def _cross_check_blocked(package, record, request, runbook, authorization, errors):
    if isinstance(package, dict):
        for k in ("grants_authorization", "permits_execution", "decision_recorded"):
            if package.get(k) is not False:
                errors.append("pacote referenciado NÃO está bloqueado: %s != false" % k)
    if isinstance(record, dict):
        if record.get("decision_status") != "PENDING":
            errors.append("registro referenciado não está PENDING")
        if record.get("decision") is not None:
            errors.append("registro referenciado tem decisão != null")
        for k in ("authorization_granted", "execution_permitted", "decision_recorded"):
            if record.get(k) is not False:
                errors.append("registro referenciado NÃO está bloqueado: %s != false" % k)
    if isinstance(request, dict):
        if request.get("request_status") != "PENDING_HUMAN_DECISION":
            errors.append("solicitação referenciada não está PENDING_HUMAN_DECISION")
        for k in ("authorization_granted", "execution_permitted", "authorization_used"):
            if request.get(k) is not False:
                errors.append("solicitação referenciada NÃO está bloqueada: %s != false" % k)
    if isinstance(runbook, dict):
        if runbook.get("executes_build") is not False:
            errors.append("runbook referenciado declara executes_build != false")
        ps = runbook.get("process_state", {})
        if isinstance(ps, dict) and ps.get("build_started") is not False:
            errors.append("runbook referenciado NÃO está bloqueado: build_started != false")
    if isinstance(authorization, dict):
        for k in ("authorization_granted", "execution_permitted", "authorization_used"):
            if authorization.get(k) is not False:
                errors.append("autorização referenciada NÃO está bloqueada: %s != false" % k)
        if authorization.get("authorization_state") != "template-not-granted":
            errors.append("autorização referenciada não está em template-not-granted")


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
def validate_all(manifest, receipt, package, record, request, runbook, authorization,
                 man_schema, rec_schema, scan_binaries=True):
    errors = []
    schema_check(manifest, man_schema, "manifest", errors)
    schema_check(receipt, rec_schema, "receipt", errors)
    check_no_forbidden(manifest, "manifest", errors)
    check_no_forbidden(receipt, "receipt", errors)
    check_manifest(manifest, package, record, request, runbook, authorization, errors)
    check_receipt(receipt, errors)
    if scan_binaries:
        check_no_build_binaries(errors)
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Valida o manifesto de apresentacao e o comprovante de entrega da "
                    "apresentacao controlada do pacote de decisao do primeiro build "
                    "controlado do Beam Patcher (offline; não apresenta, não decide, "
                    "não autoriza, não envia comunicacao).")
    parser.add_argument("--manifest", default=os.path.join(BEAM_AUDIT, "first-build-human-presentation-manifest.example.json"))
    parser.add_argument("--receipt", default=os.path.join(BEAM_AUDIT, "first-build-human-presentation-receipt.example.json"))
    parser.add_argument("--package", default=os.path.join(BEAM_AUDIT, "first-build-human-decision-package.example.json"))
    parser.add_argument("--record", default=os.path.join(BEAM_AUDIT, "first-build-human-decision-record.example.json"))
    parser.add_argument("--request", default=os.path.join(BEAM_AUDIT, "first-build-authorization-request.example.json"))
    parser.add_argument("--runbook", default=os.path.join(BEAM_AUDIT, "first-build-runbook.example.json"))
    parser.add_argument("--authorization", default=os.path.join(BEAM_AUDIT, "first-build-authorization.example.json"))
    args = parser.parse_args(argv)

    try:
        manifest = load_json(args.manifest)
        receipt = load_json(args.receipt)
        package = load_json(args.package)
        record = load_json(args.record)
        request = load_json(args.request)
        runbook = load_json(args.runbook)
        authorization = load_json(args.authorization)
        man_schema = load_json(os.path.join(SCHEMAS, "first-build-human-presentation-manifest.schema.json"))
        rec_schema = load_json(os.path.join(SCHEMAS, "first-build-human-presentation-receipt.schema.json"))
    except (OSError, ValueError) as e:
        print("ERRO ao carregar JSON: %s" % e, file=sys.stderr)
        return 2

    errors = validate_all(manifest, receipt, package, record, request, runbook, authorization,
                          man_schema, rec_schema)

    if errors:
        print("Manifesto/comprovante de apresentacao do primeiro build: FAIL")
        for e in errors:
            print("  - " + e)
        return 1

    print("Manifesto/comprovante de apresentacao do primeiro build: OK")
    print("faithro=%s | pr=#%d | artefatos apresentados=%d"
          % (manifest["faithro_reference_commit"][:10], EXPECTED_PR,
             len(manifest.get("presented_artifacts", []))))
    print("presentation_status=%s | authorization_granted=%s | execution_permitted=%s"
          % (manifest["presentation_status"], manifest["authorization_granted"],
             manifest["execution_permitted"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
