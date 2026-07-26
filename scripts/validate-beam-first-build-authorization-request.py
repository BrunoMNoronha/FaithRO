#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador estático da SOLICITAÇÃO FORMAL DE AUTORIZAÇÃO do primeiro build
controlado do Beam Patcher (ETAPA 2O-D1-B12).

Valida, de forma determinística e offline, o artefato VERSIONADO:
  * client/patcher/beam-audit/first-build-authorization-request.example.json
contra o schema em client/patcher/beam-audit/schemas/ e faz verificação cruzada
com o runbook e com o modelo de autorização versionados, confirmando que:
  * a solicitação permanece PENDENTE de decisão humana;
  * a solicitação NÃO concede (e NÃO pode conceder) autorização a si mesma;
  * o SHA-256 do runbook e do modelo de autorização declarados na solicitação
    correspondem, byte a byte, aos arquivos reais do repositório;
  * o vínculo com o commit de referência do FaithRO existe e é bem-formado;
  * a decisão humana pertence a um artefato SEPARADO (a autorização), que
    permanece NÃO concedida.

Este validador NÃO clona o Beam, NÃO instala nada, NÃO resolve dependências,
NÃO executa build, NÃO executa binário, NÃO executa Git/Rust/Cargo/PowerShell,
NÃO grava no repositório e NÃO acessa a rede.

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
EXPECTED_FAITHRO_COMMIT = "0c7e3c78a15605e44d4618c26ecf0e169d36e475"
REQUIRED_TOOLCHAIN = "1.85.0-x86_64-pc-windows-msvc"
PRESERVED_TOOLCHAIN = "1.77.2-x86_64-pc-windows-msvc"

REQUEST_REF = "client/patcher/beam-audit/first-build-authorization-request.example.json"
RUNBOOK_REF = "client/patcher/beam-audit/first-build-runbook.example.json"
AUTHORIZATION_REF = "client/patcher/beam-audit/first-build-authorization.example.json"
EVIDENCE_REF = "client/patcher/beam-audit/first-build-execution-evidence.example.json"
DOCUMENT_REF = "docs/25-solicitacao-autorizacao-primeiro-build-beam.md"

# Hosts oficiais aceitos em qualquer URL textual do artefato.
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
IPV4 = re.compile(r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b")
PROPRIETARY = re.compile(r"(?i)(\.grf\b|\.gpf\b|\.rgz\b|\bragexe\b|data\.grf|\.gr2\b)")

# Padrões proibidos em QUALQUER string do artefato (execução indireta / travessia).
FORBIDDEN_TOKENS = [
    (re.compile(r"\.\.[\\/]"), "usa travessia de diretório (..)"),
    (re.compile(r"(?i)\bcmd(\.exe)?\s+/c\b"), "usa wrapper cmd /c"),
    (re.compile(r"(?i)\b(powershell|pwsh)(\.exe)?\b[^\n]*\s-(c|command|enc|encodedcommand)\b"),
     "usa wrapper powershell -Command/-EncodedCommand"),
    (re.compile(r"(?i)\b(bash|sh|zsh|dash)\b\s+-c\b"), "usa wrapper de shell POSIX -c"),
    (re.compile(r"(?i)\b(invoke-expression|iex)\b"), "usa Invoke-Expression"),
    (re.compile(r"(?i)\b(invoke-webrequest|iwr|curl|wget|start-bitstransfer)\b"),
     "usa verbo de download"),
    (re.compile(r"(?i)\bssh\b|faithro-vps|\bscp\b|\bsftp\b"), "referencia acesso a VPS"),
    (re.compile(r"&"), "usa operador de chamada/concatenação &"),
    # Metacaracteres de shell (separador, pipe, substituição): documentos
    # declarativos não devem conter sintaxe de shell embutida.
    (re.compile(r"[;|`]"), "usa metacaractere de shell (; | `)"),
    (re.compile(r"\$[({]"), "usa substituição de shell $(...) ou ${...}"),
    # Verbos de comando destrutivo seguidos de argumento (ex.: rm -rf).
    (re.compile(r"(?i)\b(rm|rmdir|del|erase|format|mkfs|shutdown|reboot|"
                r"taskkill|schtasks|icacls|takeown|attrib)\b\s+[-/]?\S"),
     "usa verbo de comando destrutivo"),
    # Redirecionamento de shell e quebra de linha embutida (ocultariam um
    # segundo comando): campos declarativos são de linha única, sem < > nem CR/LF.
    (re.compile(r"[<>]"), "usa redirecionamento/sinal de shell (< ou >)"),
    (re.compile(r"[\r\n]"), "contém quebra de linha embutida"),
]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Mini-validador de JSON Schema (subconjunto): additionalProperties:false,
# type-lista, const, enum, pattern, minLength, minItems, minimum.
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


# Chaves cujo valor é, legitimamente, um caminho relativo versionado do repo.
_PATH_KEYS = {
    "document_reference", "runbook_reference", "authorization_reference",
    "evidence_reference", "runbook_path", "authorization_template_path", "artifact",
}


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
# Regras de negócio da SOLICITAÇÃO.
# ---------------------------------------------------------------------------
def check_request(req, runbook, authorization, runbook_sha, auth_sha, errors):
    # Estado inicial: pendente, sem qualquer concessão/execução.
    if req.get("request_status") != "PENDING_HUMAN_DECISION":
        errors.append("request.request_status deve ser PENDING_HUMAN_DECISION")
    for k in ("authorization_granted", "execution_permitted", "authorization_used",
              "authorization_revoked", "build_started", "beam_downloaded",
              "binary_produced"):
        if req.get(k) is not False:
            errors.append("request.%s deve ser false nesta etapa" % k)
    for k in ("single_use_required", "grant_is_separate_artifact",
              "merge_is_not_authorization", "review_is_not_authorization"):
        if req.get(k) is not True:
            errors.append("request.%s deve ser true" % k)

    # Referências cruzadas.
    if req.get("document_reference") != DOCUMENT_REF:
        errors.append("request.document_reference incorreto")
    if req.get("runbook_reference") != RUNBOOK_REF:
        errors.append("request.runbook_reference incorreto")
    if req.get("authorization_reference") != AUTHORIZATION_REF:
        errors.append("request.authorization_reference incorreto")
    if req.get("evidence_reference") != EVIDENCE_REF:
        errors.append("request.evidence_reference incorreto")

    # Submissão: vínculo com o SHA do FaithRO e hashes reais.
    # Guarda de tipo: se o schema já rejeitou o tipo do nó, evita AttributeError
    # e mantém mensagens de erro limpas (o erro de tipo é reportado por schema_check).
    sub = req.get("submission", {})
    if not isinstance(sub, dict):
        sub = {}
    if sub.get("faithro_reference_commit") != EXPECTED_FAITHRO_COMMIT:
        errors.append("request.submission.faithro_reference_commit != commit de referência (%s)"
                      % EXPECTED_FAITHRO_COMMIT)
    if sub.get("runbook_path") != RUNBOOK_REF:
        errors.append("request.submission.runbook_path incorreto")
    if sub.get("authorization_template_path") != AUTHORIZATION_REF:
        errors.append("request.submission.authorization_template_path incorreto")
    if sub.get("runbook_sha256") != runbook_sha:
        errors.append("request.submission.runbook_sha256 divergente do runbook real (%s)" % runbook_sha)
    if sub.get("authorization_template_sha256") != auth_sha:
        errors.append("request.submission.authorization_template_sha256 divergente do arquivo real (%s)" % auth_sha)
    if sub.get("required_toolchain") != REQUIRED_TOOLCHAIN:
        errors.append("request.submission.required_toolchain incorreta")
    if sub.get("preserved_default_toolchain") != PRESERVED_TOOLCHAIN:
        errors.append("request.submission.preserved_default_toolchain incorreta")
    if sub.get("runbook_version") != runbook.get("runbook_version"):
        errors.append("request.submission.runbook_version divergente do runbook")
    for k in ("default_toolchain_change_forbidden", "permanent_path_change_forbidden",
              "override_forbidden"):
        if sub.get(k) is not True:
            errors.append("request.submission.%s deve ser true" % k)

    # Escopo e proibições não vazios.
    if not req.get("requested_scope"):
        errors.append("request.requested_scope ausente")
    if not req.get("actions_remaining_forbidden"):
        errors.append("request.actions_remaining_forbidden ausente")
    if not req.get("decision_inputs_required"):
        errors.append("request.decision_inputs_required ausente")

    # Alvo da decisão: artefato SEPARADO, com expiração e uso único obrigatórios.
    dt = req.get("decision_target", {})
    if not isinstance(dt, dict):
        dt = {}
    if dt.get("artifact") != AUTHORIZATION_REF:
        errors.append("request.decision_target.artifact deve apontar para a autorização separada")
    if dt.get("expiration_required_on_grant") is not True:
        errors.append("request.decision_target.expiration_required_on_grant deve ser true")
    if dt.get("single_use_required_on_grant") is not True:
        errors.append("request.decision_target.single_use_required_on_grant deve ser true")

    # Cross-check: o runbook referenciado deve permanecer NÃO autorizado.
    ps = runbook.get("process_state", {}) if isinstance(runbook, dict) else {}
    if not isinstance(ps, dict):
        ps = {}
    for k in ("human_authorization_granted", "execution_authorized", "execution_started",
              "build_started", "build_completed", "binary_produced", "binary_executed",
              "deploy_performed", "vps_accessed"):
        if ps.get(k) is not False:
            errors.append("runbook referenciado NÃO está bloqueado: process_state.%s != false" % k)
    if runbook.get("executes_build") is not False:
        errors.append("runbook referenciado declara executes_build != false")

    # Cross-check: o modelo de autorização referenciado deve permanecer NÃO concedido.
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
def validate_all(request, runbook, authorization, req_schema,
                 runbook_sha, auth_sha, scan_binaries=True):
    errors = []
    schema_check(request, req_schema, "request", errors)
    check_no_forbidden(request, "request", errors)
    check_request(request, runbook, authorization, runbook_sha, auth_sha, errors)
    if scan_binaries:
        check_no_build_binaries(errors)
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Valida a solicitação formal de autorização do primeiro build "
                    "controlado do Beam Patcher (offline; não clona, não instala, "
                    "não constrói, não executa, não concede autorização).")
    parser.add_argument("--request", default=os.path.join(BEAM_AUDIT, "first-build-authorization-request.example.json"))
    parser.add_argument("--runbook", default=os.path.join(BEAM_AUDIT, "first-build-runbook.example.json"))
    parser.add_argument("--authorization", default=os.path.join(BEAM_AUDIT, "first-build-authorization.example.json"))
    args = parser.parse_args(argv)

    try:
        request = load_json(args.request)
        runbook = load_json(args.runbook)
        authorization = load_json(args.authorization)
        req_schema = load_json(os.path.join(SCHEMAS, "first-build-authorization-request.schema.json"))
    except (OSError, ValueError) as e:
        print("ERRO ao carregar JSON: %s" % e, file=sys.stderr)
        return 2

    runbook_file = os.path.join(REPO, RUNBOOK_REF)
    auth_file = os.path.join(REPO, AUTHORIZATION_REF)
    if not os.path.isfile(runbook_file) or not os.path.isfile(auth_file):
        print("ERRO: runbook ou autorização versionados não encontrados", file=sys.stderr)
        return 2
    runbook_sha = sha256_file(runbook_file)
    auth_sha = sha256_file(auth_file)

    errors = validate_all(request, runbook, authorization, req_schema, runbook_sha, auth_sha)

    if errors:
        print("Solicitação de autorização do primeiro build: FAIL")
        for e in errors:
            print("  - " + e)
        return 1

    print("Solicitação de autorização do primeiro build: OK")
    print("faithro=%s | runbook_sha=%s | auth_sha=%s"
          % (request["submission"]["faithro_reference_commit"][:10],
             runbook_sha[:10], auth_sha[:10]))
    print("request_status=%s | authorization_granted=%s | execution_permitted=%s"
          % (request["request_status"], request["authorization_granted"],
             request["execution_permitted"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
