#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador dos artefatos do WARP (2P-D ... 2P-E-C0-A / 2P-E-C0-B). Offline: valida a
evidencia do GATE 0 sem consultar o upstream (apenas estrutura e consistencia).

Valida os JSONs versionados em client/warp-audit/ contra os schemas
(draft-07, subconjunto) em client/warp-audit/schemas/ e contra regras de
seguranca do projeto. Inclui, alem do template EM BRANCO do registro de decisao,
o(s) registro(s) REAL(is) de decisao humana em client/warp-audit/decisions/
(ETAPA 2P-E-A2): confirma que o template continua vazio, que o registro real
contem a decisao (opcao PREBUILT_PATH para 2026-07-31), que nenhuma autorizacao
operacional esta true, que identidade/autoridade nao sao placeholders, que a data
e valida, que justificativa e condicoes nao estao vazias, que as condicoes estao
numeradas 1..N em ordem (sem lacuna/repeticao), que os patches sensiveis continuam
bloqueados e os candidatos apenas revisados (conjuntos exatos), que as referencias
existem e que pacote e registro usam o mesmo commit fixado.

Garantias (ver docs/30-auditoria-estatica-warp.md, FASE N):
  * Apenas biblioteca padrao do Python (sem dependencias externas).
  * Nao acessa a rede; nao executa subprocessos; nao escreve arquivos.
  * Independente do CWD (resolve caminhos a partir da raiz do repositorio).
  * Valida tipos, campos, const, enum, pattern, required e additionalProperties.
  * Exige SHA de 40 caracteres (commit) e 64 (sha256) quando presentes.
  * Impede flags de build/execucao/modificacao/uso-do-prebuilt em `true`.
  * Rejeita caminhos absolutos e travessia em campos `path`.
  * Rejeita IPs literais, segredos, tokens e caminhos pessoais.
  * Codigo de saida != 0 em falha; sem traceback para entradas invalidas.

Este validador NAO concede autorizacao. Uma classificacao positiva, o merge do
PR, a presenca de um patch candidato ou a criacao do laboratorio NAO equivalem a
autorizacao de build, execucao, uso do prebuilt ou modificacao do cliente.
"""
import datetime
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT_DIR = os.path.join(REPO_ROOT, "client", "warp-audit")
SCHEMA_DIR = os.path.join(AUDIT_DIR, "schemas")
DECISIONS_DIR = os.path.join(AUDIT_DIR, "decisions")

ARTIFACTS = [
    ("upstream-manifest.example.json", "upstream-manifest.schema.json"),
    ("security-findings.example.json", "security-findings.schema.json"),
    ("patch-selection.example.json", "patch-selection.schema.json"),
    ("core-path-decision-package.example.json", "core-path-decision-package.schema.json"),
    ("core-path-decision-record.example.json", "core-path-decision-record.schema.json"),
]

# ETAPA 2P-E-A2: registro REAL da decisao humana (preenchido, fora do template).
REAL_RECORD_SCHEMA = "core-path-decision-record-real.schema.json"
EXPECTED_PINNED_COMMIT = "9b1173e9e4e135c68e150704f01186ab5e763acd"
# Opcao esperada por registro real datado (comprova a selecao registrada sem
# engessar registros futuros de outra opcao). A selecao NAO e autorizacao.
EXPECTED_OPTION_BY_FILE = {
    "core-path-decision-record-2026-07-31.json": "PREBUILT_PATH",
}
# Flags operacionais que DEVEM permanecer false mesmo com uma opcao selecionada.
OPERATIONAL_FLAGS = [
    "source_path_authorized", "prebuilt_path_authorized",
    "alternative_tool_authorized", "stop_path_selected",
    "materialization_authorized", "build_authorized", "execution_authorized",
    "client_provision_authorized", "client_modification_authorized",
    "first_login_authorized",
]
# Flags de decisao humana que DEVEM ser true no registro real.
DECISION_TRUE_FLAGS = [
    "human_decision_required", "human_decision_received", "option_selected",
]
# Patches sensiveis que DEVEM permanecer bloqueados (nao remover/reclassificar).
EXPECTED_BLOCKED_PATCHES = {
    "CustomDLL", "DisableProtect", "DisableEncr", "EnableProxy",
}
# Patches que permanecem SOMENTE candidatos revisados (nao autorizar/aplicar).
EXPECTED_REVIEWED_CANDIDATES = {
    "DataFolderFirst", "CallKoreaClientInfo",
}

# --- ETAPA 2P-E-B-PREBUILT: plano da auditoria binaria offline (templates) ---
PLAN_TEMPLATE = "binary-audit-plan.example.json"
PLAN_SCHEMA = "binary-audit-plan.schema.json"
GATE_TEMPLATE = "binary-audit-gate-record.example.json"
GATE_SCHEMA = "binary-audit-gate-record.schema.json"
EXPECTED_GATE_COUNT = 17  # GATE 0..16
# Flags documentais que PODEM ser true no plano; todas as demais sao operacionais.
PLAN_DOC_TRUE_FLAGS = {"plan_creation_authorized", "plan_created"}
# Palavras-chave de JSON Schema que o mini-validador (validate_node) implementa.
IMPLEMENTED_SCHEMA_KEYWORDS = {
    "$schema", "$id", "title", "description", "$comment",
    "type", "const", "enum", "pattern", "minLength", "minimum",
    "required", "additionalProperties", "properties", "items", "minItems",
}
# Conteudo proibido nos templates de planejamento (defesa em profundidade).
DOWNLOAD_CMD_RE = re.compile(
    r"(?i)\b(curl|wget|invoke-webrequest|iwr|start-bitstransfer|bitsadmin|"
    r"certutil|git\s+(?:clone|fetch|pull)|scp|sftp|aria2c|Start-BitsTransfer)\b")
BINARY_URL_RE = re.compile(
    r"(?i)\bhttps?://\S+\.(exe|dll|zip|7z|rar|grf|rgz|thor|asi|msi|bin|cab)\b")
# Execucao do WARP: exige verbo de execucao ou prefixo de run (./ ou .\) antes do
# nome do arquivo. Uma REFERENCIA de caminho (ex.: win32/WARP.exe) NAO e execucao.
WARP_EXEC_RE = re.compile(
    r"(?i)(?:\brodar\b|\brun\b|\bstart\b|\blaunch\b|\bexecut(?:ar|e)\b|\biniciar\b|"
    r"\./|\.\\)\s*[\"']?WARP(?:_console|_bench)?\.exe\b")
CLIENT_EXEC_RE = re.compile(
    r"(?i)(?:\brodar\b|\brun\b|\bstart\b|\blaunch\b|\bexecut(?:ar|e)\b|\biniciar\b|"
    r"\./|\.\\)\s*[\"']?ragexe[a-z0-9_]*\.exe\b")
BIN_HASH_RE = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])")
IMPLICIT_APPROVAL_RES = [
    re.compile(r"(?i)\b(prebuilt|binario|nucleo)\b[^.\n]{0,24}\b"
              r"(aprovad[oa]|validad[oa]|homologad[oa]|confiavel|seguro)\b"),
    re.compile(r"(?i)\b(aprovad[oa]|validad[oa]|homologad[oa])\s+(o\s+|do\s+)?"
              r"(prebuilt|binario|nucleo)\b"),
]

# --- ETAPA 2P-E-C0-A: registro real da autorizacao humana do GATE 0 ---
GATE0_SCHEMA = "binary-audit-gate-00-decision-record-real.schema.json"
# Metodos permitidos: conjunto FECHADO (nem extra, nem faltante).
GATE0_ALLOWED_METHODS = {
    "GitHub API de metadados", "GitHub web metadata", "GitHub connector",
    "git ls-remote", "endpoints de commit", "endpoints de arvore",
    "endpoints de refs", "metadados de tags", "metadados de releases",
    "licenca e documentacao textual",
}
# Acoes proibidas: conjunto MINIMO obrigatorio (subconjunto exigido).
GATE0_PROHIBITED_MIN = {
    "clone", "fetch upstream", "pull upstream", "archive", "release asset",
    "blob binario", "conteudo do prebuilt", "materializacao", "extracao",
    "hashing do binario real", "inspecao PE", "Authenticode", "antivirus",
    "execucao", "sandbox", "cliente", "patches", "login", "VPS",
    "distribuicao", "alteracao do servidor",
}
GATE0_TRUE_FLAGS = {
    "human_decision_required", "human_decision_received", "gate_selected",
    "provenance_reconfirmation_authorized",
}
# Nomes de arquivo permitidos no diretorio decisions/.
DECISION_FILE_PREFIXES = (
    "core-path-decision-record-", "binary-audit-gate-",
)

# --- ETAPA 2P-E-C0-B: evidencia real da execucao do GATE 0 (metadados) ---
EVIDENCE_DIR = os.path.join(AUDIT_DIR, "evidence")
GATE0_EVIDENCE_SCHEMA = "binary-audit-gate-00-provenance-evidence.schema.json"
GATE0_DECISION_RECORD = "binary-audit-gate-00-decision-record-2026-07-31.json"
EVIDENCE_FILE_PREFIXES = ("binary-audit-gate-00-provenance-evidence-",)
# Valores canonicos esperados (dos artefatos internos das etapas anteriores).
EXPECTED_ARTIFACT_PATH = "win32/WARP.exe"
EXPECTED_ARTIFACT_BLOB = "c853da42d18dfe090b4e941b435d989311faf3dc"
EXPECTED_ARTIFACT_SIZE = 1137152
EXPECTED_REPOSITORY = "Neo-Mind/WARP"
ALLOWED_ENDPOINT_CLASSES = {
    "REPOSITORY_METADATA", "GIT_COMMIT_METADATA", "GIT_TREE_METADATA",
    "REF_METADATA", "TAG_METADATA", "RELEASE_METADATA", "LICENSE_METADATA",
}
# Endpoints/URLs que retornam CONTEUDO — proibidos no GATE 0 (defesa em profundidade).
FORBIDDEN_ENDPOINT_RE = re.compile(
    r"(?i)(git/blobs/|/contents/|zipball|tarball|download_url|"
    r"browser_download_url|archive_url|raw\.githubusercontent\.com|"
    r"codeload\.github\.com)")
# Deteccao de placeholders em identidade/autoridade/canal (nao inventados).
PLACEHOLDER_RE = re.compile(
    r"(?i)(<[^>]*>|\bplaceholder\b|\bexample\b|\bexemplo\b|\bto ?do\b|\btbd\b|"
    r"\bfulano\b|\bpreencher\b|\bnull\b|\bnome do decisor\b|\bseu nome\b|x{3,})")

# --- Regras de seguranca (valores, nao prosa) ---
IPV4_RE = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
DRIVE_PATH_RE = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]")
PERSONAL_PATH_RE = re.compile(r"(?i)(/home/|/root/|/Users/|\\Users\\)")
PRIVATE_KEY_RE = re.compile(r"BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY")
AUTH_HEADER_RE = re.compile(r"(?i)Authorization:\s*\S")
# Atribuicao de segredo: (senha|password|token|secret|api_key) seguido de : ou = e valor.
SECRET_ASSIGN_RE = re.compile(
    r"(?i)\b(pass(?:word|wd)?|senha|secret|token|api[_-]?key|bearer)\b\s*[:=]\s*\S")
TRAVERSAL_RE = re.compile(r"(^|[\\/])\.\.([\\/]|$)")


class Fail(Exception):
    pass


def load_json(path):
    if not os.path.isfile(path):
        raise Fail(f"arquivo ausente: {os.path.relpath(path, REPO_ROOT)}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (ValueError, OSError) as exc:
        raise Fail(f"JSON invalido em {os.path.relpath(path, REPO_ROOT)}: {exc}")


# ---------------------------------------------------------------------------
# Subconjunto de JSON Schema (draft-07) suficiente para estes artefatos.
# ---------------------------------------------------------------------------
def type_ok(value, jtype):
    if jtype == "object":
        return isinstance(value, dict)
    if jtype == "array":
        return isinstance(value, list)
    if jtype == "string":
        return isinstance(value, str)
    if jtype == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if jtype == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if jtype == "boolean":
        return isinstance(value, bool)
    if jtype == "null":
        return value is None
    return True


def validate_node(value, schema, where, errors):
    if "type" in schema and not type_ok(value, schema["type"]):
        errors.append(f"{where}: tipo esperado {schema['type']}")
        return  # sem tipo correto, nao adianta seguir

    if "const" in schema and value != schema["const"]:
        errors.append(f"{where}: valor deve ser {schema['const']!r}, obtido {value!r}")

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: valor {value!r} fora de enum {schema['enum']}")

    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{where}: nao casa com pattern {schema['pattern']}")
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{where}: string mais curta que {schema['minLength']}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{where}: valor {value} < minimo {schema['minimum']}")

    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{where}: campo obrigatorio ausente: {req}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    errors.append(f"{where}: propriedade nao permitida: {key}")
        for key, sub in props.items():
            if key in value:
                validate_node(value[key], sub, f"{where}.{key}", errors)

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{where}: lista com menos de {schema['minItems']} itens")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(value):
                validate_node(item, item_schema, f"{where}[{i}]", errors)


# ---------------------------------------------------------------------------
# Regras de seguranca aplicadas ao conteudo dos artefatos.
# ---------------------------------------------------------------------------
def iter_strings(node, path="$"):
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from iter_strings(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from iter_strings(v, f"{path}[{i}]")


def security_scan(data, errors):
    for where, text in iter_strings(data):
        # IPs literais (exclui a versao de schema semantico tipo x.y.z: exige 4 octetos)
        for m in IPV4_RE.finditer(text):
            octs = m.group(0).split(".")
            if all(0 <= int(o) <= 255 for o in octs):
                errors.append(f"{where}: possivel IP literal detectado (categoria: IP)")
                break
        if DRIVE_PATH_RE.search(text):
            errors.append(f"{where}: caminho com unidade (drive) proibido")
        if PERSONAL_PATH_RE.search(text):
            errors.append(f"{where}: caminho pessoal proibido")
        if PRIVATE_KEY_RE.search(text):
            errors.append(f"{where}: bloco de chave privada proibido")
        if AUTH_HEADER_RE.search(text):
            errors.append(f"{where}: header Authorization proibido")
        if SECRET_ASSIGN_RE.search(text):
            errors.append(f"{where}: atribuicao de segredo proibida")

    # Campos 'path' devem ser relativos, sem travessia.
    for where, text in iter_strings(data):
        if where.endswith(".path"):
            if text.startswith("/") or text.startswith("\\") or DRIVE_PATH_RE.match(text):
                errors.append(f"{where}: caminho absoluto proibido em campo path")
            if TRAVERSAL_RE.search(text):
                errors.append(f"{where}: travessia '..' proibida em campo path")


def forbidden_flags(data, name, errors):
    """Impede flags de build/execucao/modificacao em true."""
    must_be_false = [
        "source_executed", "source_built", "binary_created", "client_modified",
        "execution_allowed", "final_selection_allowed",
        "prebuilt_use_authorized", "core_build_possible_with_pinned_commit",
        # ETAPA 2P-E-A: pacote e registro de decisao do caminho do nucleo.
        "human_decision_received",
        "decision_received", "option_selected", "source_path_authorized",
        "prebuilt_path_authorized", "alternative_tool_authorized",
        "stop_path_selected", "materialization_authorized", "build_authorized",
        "execution_authorized", "client_provision_authorized",
        "client_modification_authorized", "first_login_authorized",
    ]
    for key in must_be_false:
        if key in data and data[key] is not False:
            errors.append(f"{name}: flag '{key}' deve ser false")
    if "human_authorization_required" in data and data["human_authorization_required"] is not True:
        errors.append(f"{name}: 'human_authorization_required' deve ser true")


def cross_checks(errors):
    """Checagens entre artefatos e existencia de referencias (ETAPA 2P-E-A)."""
    pkg_path = os.path.join(AUDIT_DIR, "core-path-decision-package.example.json")
    rec_path = os.path.join(AUDIT_DIR, "core-path-decision-record.example.json")
    if not (os.path.isfile(pkg_path) and os.path.isfile(rec_path)):
        return
    try:
        pkg = load_json(pkg_path)
        rec = load_json(rec_path)
    except Fail as exc:
        errors.append(str(exc))
        return
    # Referencias do pacote devem existir no repositorio.
    for ref in pkg.get("references", []):
        rp = ref.get("path", "")
        if not os.path.isfile(os.path.join(REPO_ROOT, rp)):
            errors.append(f"pacote: referencia ausente no repo: {rp}")
    # Pacote e registro nao podem se contradizer: ambos em estado pendente/branco.
    if pkg.get("state") != "PENDING_HUMAN_DECISION":
        errors.append("pacote: state deve ser PENDING_HUMAN_DECISION")
    if rec.get("status") != "PENDING":
        errors.append("registro: status deve ser PENDING")
    for flag in ("decision_received", "option_selected", "human_decision_received"):
        if pkg.get(flag) is not False or rec.get(flag) is not False:
            errors.append(f"contradicao pacote/registro: '{flag}' deve ser false em ambos")
    if rec.get("selected_option") is not None:
        errors.append("registro: selected_option deve permanecer null")
    # Nenhuma opcao do pacote pode estar selecionada (defesa em profundidade).
    for i, opt in enumerate(pkg.get("options", [])):
        if opt.get("selected") is not False:
            errors.append(f"pacote: options[{i}].selected deve ser false")


def valid_iso_date(value):
    if not isinstance(value, str):
        return False
    try:
        datetime.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def validate_real_record(record, schema, package, filename, errors):
    """Valida um registro REAL de decisao humana (ETAPA 2P-E-A2).

    Importavel pelos testes negativos. `package` e o pacote de decisao (dict) para
    conferir o commit fixado. Nao concede autorizacao: exige que toda flag
    operacional permaneca false, inclusive quando uma opcao esta selecionada.
    """
    if not isinstance(schema, dict):
        errors.append(f"{filename}: schema do registro real ausente/invalido")
        return errors
    validate_node(record, schema, filename, errors)
    security_scan(record, errors)

    if not isinstance(record, dict):
        errors.append(f"{filename}: registro nao e objeto")
        return errors

    if record.get("status") != "DECIDED":
        errors.append(f"{filename}: status deve ser DECIDED")

    decision = record.get("decision")
    option = decision.get("option") if isinstance(decision, dict) else None
    if not option:
        errors.append(f"{filename}: decision.option ausente (selecao deve estar em decision.option)")
    expected_opt = EXPECTED_OPTION_BY_FILE.get(filename)
    if expected_opt is not None and option != expected_opt:
        errors.append(f"{filename}: decision.option deve ser {expected_opt}, obtido {option!r}")

    # A selecao NUNCA pode aparecer como *_authorized=true (defesa em profundidade).
    auth = record.get("authorizations")
    if not isinstance(auth, dict):
        auth = {}
        errors.append(f"{filename}: bloco 'authorizations' ausente")
    for k in DECISION_TRUE_FLAGS:
        if auth.get(k) is not True:
            errors.append(f"{filename}: authorizations.{k} deve ser true")
    for k in OPERATIONAL_FLAGS:
        if auth.get(k) is not False:
            errors.append(f"{filename}: authorizations.{k} deve ser false (selecao nao e autorizacao)")

    # Identidade e autoridade nao podem ser placeholders nem vazios.
    for field in ("decider", "role", "authority", "channel"):
        val = record.get(field)
        if not isinstance(val, str) or not val.strip():
            errors.append(f"{filename}: campo '{field}' vazio")
        elif PLACEHOLDER_RE.search(val):
            errors.append(f"{filename}: campo '{field}' parece placeholder (categoria: placeholder)")

    if not valid_iso_date(record.get("date")):
        errors.append(f"{filename}: campo 'date' nao e uma data ISO valida")

    just = record.get("justification")
    if not isinstance(just, str) or not just.strip():
        errors.append(f"{filename}: 'justification' vazia")

    conds = record.get("conditions")
    if not isinstance(conds, list) or len(conds) < 15:
        errors.append(f"{filename}: 'conditions' deve ter ao menos 15 itens")
    else:
        for i, c in enumerate(conds):
            if not isinstance(c, dict) or not str(c.get("text", "")).strip():
                errors.append(f"{filename}: conditions[{i}] sem texto")
        # Numeracao sequencial 1..N, sem lacuna, sem repeticao, sem fora de ordem.
        ns = [c.get("n") for c in conds if isinstance(c, dict)]
        if ns != list(range(1, len(conds) + 1)):
            errors.append(f"{filename}: conditions devem ser numeradas 1..N em ordem, "
                          f"sem lacuna nem repeticao")

    # Patches sensiveis: conjunto EXATO (nao remover, reclassificar nem adicionar).
    bp = record.get("blocked_patches")
    if not isinstance(bp, list) or set(bp) != EXPECTED_BLOCKED_PATCHES:
        errors.append(f"{filename}: blocked_patches deve ser exatamente "
                      f"{sorted(EXPECTED_BLOCKED_PATCHES)} (bloqueio nao pode ser enfraquecido)")
    roc = record.get("reviewed_only_candidates")
    if not isinstance(roc, list) or set(roc) != EXPECTED_REVIEWED_CANDIDATES:
        errors.append(f"{filename}: reviewed_only_candidates deve ser exatamente "
                      f"{sorted(EXPECTED_REVIEWED_CANDIDATES)} (nao aprovar nem reclassificar)")
    if isinstance(bp, list) and isinstance(roc, list):
        overlap = set(bp) & set(roc)
        if overlap:
            errors.append(f"{filename}: patch nao pode estar em blocked_patches e "
                          f"reviewed_only_candidates ao mesmo tempo: {sorted(overlap)}")

    # Pacote e registro devem usar o mesmo commit fixado.
    rec_commit = record.get("commit_pinned")
    if rec_commit != EXPECTED_PINNED_COMMIT:
        errors.append(f"{filename}: commit_pinned != commit fixado ({EXPECTED_PINNED_COMMIT})")
    pref = record.get("package_ref")
    pref_commit = pref.get("commit_pinned") if isinstance(pref, dict) else None
    if pref_commit != rec_commit:
        errors.append(f"{filename}: package_ref.commit_pinned difere de commit_pinned")
    pkg_commit = package.get("commit_pinned") if isinstance(package, dict) else None
    if pkg_commit is not None and rec_commit != pkg_commit:
        errors.append(f"{filename}: commit_pinned difere do commit do pacote ({pkg_commit})")

    # Referencias (pacote e template) devem existir no repositorio.
    tref = record.get("template_ref")
    for field, ref in (("package_ref", pref), ("template_ref", tref)):
        rp = ref.get("path") if isinstance(ref, dict) else None
        if not rp:
            errors.append(f"{filename}: {field}.path ausente")
        elif not os.path.isfile(os.path.join(REPO_ROOT, rp)):
            errors.append(f"{filename}: {field}.path referencia arquivo inexistente")

    return errors


def check_decisions_dir_names(names, errors):
    """decisions/ so pode conter registros reais reconhecidos (caminho do nucleo e
    registros de gate da auditoria binaria). Qualquer outro arquivo e reprovado."""
    for n in names:
        if not (n.endswith(".json") and n.startswith(DECISION_FILE_PREFIXES)):
            errors.append(f"decisions/: arquivo inesperado '{n}'")


def validate_real_records(errors):
    """Percorre client/warp-audit/decisions/ e valida cada registro real."""
    if not os.path.isdir(DECISIONS_DIR):
        return  # sem registros reais ainda: nada a validar
    check_decisions_dir_names(sorted(os.listdir(DECISIONS_DIR)), errors)
    package = {}
    pkg_path = os.path.join(AUDIT_DIR, "core-path-decision-package.example.json")
    try:
        package = load_json(pkg_path)
    except Fail:
        package = {}
    try:
        schema = load_json(os.path.join(SCHEMA_DIR, REAL_RECORD_SCHEMA))
    except Fail as exc:
        errors.append(str(exc))
        return
    names = sorted(
        f for f in os.listdir(DECISIONS_DIR)
        if f.startswith("core-path-decision-record-") and f.endswith(".json"))
    if not names:
        errors.append("decisions/: nenhum registro real de decisao encontrado")
        return
    for name in names:
        try:
            record = load_json(os.path.join(DECISIONS_DIR, name))
        except Fail as exc:
            errors.append(str(exc))
            print(f"[FALHA] decisions/{name}: JSON invalido")
            continue
        rec_errors = []
        validate_real_record(record, schema, package, name, rec_errors)
        if rec_errors:
            errors.extend(rec_errors)
            print(f"[FALHA] decisions/{name}: {len(rec_errors)} problema(s)")
            for e in rec_errors:
                print(f"    - {e}")
        else:
            print(f"[OK]    decisions/{name}")


def schema_keyword_violations(node, where, viol):
    """Reprova se um schema usar keyword de validacao nao implementada pelo
    mini-validador (evita 'validacao aparente')."""
    if not isinstance(node, dict):
        return
    for k in node:
        if k not in IMPLEMENTED_SCHEMA_KEYWORDS:
            viol.append(f"{where}: keyword de schema nao suportada pelo validador: {k}")
    props = node.get("properties")
    if isinstance(props, dict):
        for name, sub in props.items():
            schema_keyword_violations(sub, f"{where}.properties.{name}", viol)
    items = node.get("items")
    if isinstance(items, dict):
        schema_keyword_violations(items, f"{where}.items", viol)
    ap = node.get("additionalProperties")
    if isinstance(ap, dict):
        schema_keyword_violations(ap, f"{where}.additionalProperties", viol)


def planning_content_scan(data, label, errors):
    """Regras de conteudo dos templates de planejamento (sem materializacao)."""
    for where, text in iter_strings(data):
        if DOWNLOAD_CMD_RE.search(text):
            errors.append(f"{label}{where}: comando de download proibido no plano")
        if BINARY_URL_RE.search(text):
            errors.append(f"{label}{where}: URL direta para binario proibida")
        if WARP_EXEC_RE.search(text):
            errors.append(f"{label}{where}: comando de execucao do WARP proibido")
        if CLIENT_EXEC_RE.search(text):
            errors.append(f"{label}{where}: comando de execucao do cliente proibido")
        if BIN_HASH_RE.search(text):
            errors.append(f"{label}{where}: possivel hash de binario (64 hex) proibido no plano")
        for rx in IMPLICIT_APPROVAL_RES:
            if rx.search(text):
                errors.append(f"{label}{where}: texto sugere aprovacao implicita do prebuilt")
                break


def _ref_ok(rel_path, field, label, errors):
    if not isinstance(rel_path, str) or not rel_path:
        errors.append(f"{label}: {field} ausente")
        return
    if rel_path.startswith("/") or rel_path.startswith("\\") or DRIVE_PATH_RE.match(rel_path):
        errors.append(f"{label}: {field} nao pode ser caminho absoluto")
    if TRAVERSAL_RE.search(rel_path):
        errors.append(f"{label}: {field} nao pode conter travessia '..'")
    if not os.path.isfile(os.path.join(REPO_ROOT, rel_path)):
        errors.append(f"{label}: {field} referencia arquivo inexistente")


def validate_binary_audit_plan(plan, schema, record, filename, errors):
    """Valida o template do plano da auditoria binaria (importavel nos testes)."""
    kv = []
    schema_keyword_violations(schema, "binary-audit-plan.schema", kv)
    errors.extend(kv)
    validate_node(plan, schema, filename, errors)
    security_scan(plan, errors)
    planning_content_scan(plan, filename, errors)

    if not isinstance(plan, dict):
        errors.append(f"{filename}: plano nao e objeto")
        return errors

    # Referencias relativas existentes.
    _ref_ok(plan.get("source_decision_record"), "source_decision_record", filename, errors)

    # Commit fixado consistente com a ETAPA 2P-E-A2.
    commit = plan.get("upstream_commit_pinned")
    if commit != EXPECTED_PINNED_COMMIT:
        errors.append(f"{filename}: upstream_commit_pinned != commit fixado ({EXPECTED_PINNED_COMMIT})")
    rec_commit = record.get("commit_pinned") if isinstance(record, dict) else None
    if rec_commit is not None and commit != rec_commit:
        errors.append(f"{filename}: upstream_commit_pinned difere do registro 2P-E-A2 ({rec_commit})")

    # Gates: quantidade, IDs unicos e ordenados 0..N, nomes, STOP_PATH previsto.
    gates = plan.get("gates")
    if not isinstance(gates, list) or len(gates) < EXPECTED_GATE_COUNT:
        errors.append(f"{filename}: gates deve ter ao menos {EXPECTED_GATE_COUNT} itens")
        gates = gates if isinstance(gates, list) else []
    ids = [g.get("gate_id") for g in gates if isinstance(g, dict)]
    if ids != list(range(0, len(gates))):
        errors.append(f"{filename}: gate_id deve ser unico e sequencial 0..N em ordem")
    for i, g in enumerate(gates):
        if not isinstance(g, dict):
            errors.append(f"{filename}: gates[{i}] nao e objeto")
            continue
        if not str(g.get("gate_name", "")).strip():
            errors.append(f"{filename}: gates[{i}].gate_name vazio")
        if "STOP_PATH" not in (g.get("exit_options") or []):
            errors.append(f"{filename}: gates[{i}] deve prever STOP_PATH em exit_options")

    # Criterios de interrupcao nao vazios.
    if not plan.get("stop_criteria"):
        errors.append(f"{filename}: stop_criteria nao pode ser vazio")

    # Conjuntos de patches exatos e disjuntos.
    bp = plan.get("blocked_patches")
    if not isinstance(bp, list) or set(bp) != EXPECTED_BLOCKED_PATCHES:
        errors.append(f"{filename}: blocked_patches deve ser exatamente {sorted(EXPECTED_BLOCKED_PATCHES)}")
    roc = plan.get("reviewed_only_candidates")
    if not isinstance(roc, list) or set(roc) != EXPECTED_REVIEWED_CANDIDATES:
        errors.append(f"{filename}: reviewed_only_candidates deve ser exatamente {sorted(EXPECTED_REVIEWED_CANDIDATES)}")
    if isinstance(bp, list) and isinstance(roc, list) and (set(bp) & set(roc)):
        errors.append(f"{filename}: blocked_patches e reviewed_only_candidates devem ser disjuntos")

    # Autorizacoes: somente as documentais em true; todas as demais em false.
    auth = plan.get("authorizations")
    if not isinstance(auth, dict):
        errors.append(f"{filename}: 'authorizations' ausente")
    else:
        for k, v in auth.items():
            if k in PLAN_DOC_TRUE_FLAGS:
                if v is not True:
                    errors.append(f"{filename}: authorizations.{k} deve ser true")
            elif v is not False:
                errors.append(f"{filename}: authorizations.{k} deve ser false (autorizacao operacional)")
    return errors


def validate_binary_audit_gate_template(gate, schema, filename, errors):
    """Valida o template EM BRANCO do registro de decisao por gate."""
    kv = []
    schema_keyword_violations(schema, "binary-audit-gate-record.schema", kv)
    errors.extend(kv)
    validate_node(gate, schema, filename, errors)
    security_scan(gate, errors)
    planning_content_scan(gate, filename, errors)

    if not isinstance(gate, dict):
        errors.append(f"{filename}: template de gate nao e objeto")
        return errors

    if gate.get("status") != "PENDING":
        errors.append(f"{filename}: status do template de gate deve ser PENDING")
    for k in ("gate_id", "gate_name", "decision", "decider", "role", "authority",
              "channel", "date", "justification", "conditions", "evidence_required",
              "supersedes", "rollback", "notes"):
        if gate.get(k) is not None:
            errors.append(f"{filename}: campo '{k}' deve ser null no template (sem decisao real)")
    pref = gate.get("plan_ref")
    _ref_ok(pref.get("path") if isinstance(pref, dict) else None, "plan_ref.path", filename, errors)

    auth = gate.get("authorizations")
    if not isinstance(auth, dict):
        errors.append(f"{filename}: 'authorizations' ausente")
    else:
        if auth.get("human_decision_required") is not True:
            errors.append(f"{filename}: authorizations.human_decision_required deve ser true")
        for k, v in auth.items():
            if k == "human_decision_required":
                continue
            if v is not False:
                errors.append(f"{filename}: authorizations.{k} deve ser false no template")
    return errors


def validate_binary_audit(errors):
    """Orquestra a validacao dos templates da ETAPA 2P-E-B-PREBUILT."""
    plan_path = os.path.join(AUDIT_DIR, PLAN_TEMPLATE)
    gate_path = os.path.join(AUDIT_DIR, GATE_TEMPLATE)
    if not (os.path.isfile(plan_path) or os.path.isfile(gate_path)):
        return  # etapa ainda nao presente
    record = {}
    rec_path = os.path.join(DECISIONS_DIR, "core-path-decision-record-2026-07-31.json")
    try:
        record = load_json(rec_path)
    except Fail:
        record = {}
    # Plano
    perr = []
    try:
        plan = load_json(plan_path)
        pschema = load_json(os.path.join(SCHEMA_DIR, PLAN_SCHEMA))
        validate_binary_audit_plan(plan, pschema, record, PLAN_TEMPLATE, perr)
    except Fail as exc:
        perr.append(str(exc))
    if perr:
        errors.extend(perr)
        print(f"[FALHA] {PLAN_TEMPLATE}: {len(perr)} problema(s)")
        for e in perr:
            print(f"    - {e}")
    else:
        print(f"[OK]    {PLAN_TEMPLATE}")
    # Template de gate
    gerr = []
    try:
        gate = load_json(gate_path)
        gschema = load_json(os.path.join(SCHEMA_DIR, GATE_SCHEMA))
        validate_binary_audit_gate_template(gate, gschema, GATE_TEMPLATE, gerr)
    except Fail as exc:
        gerr.append(str(exc))
    if gerr:
        errors.extend(gerr)
        print(f"[FALHA] {GATE_TEMPLATE}: {len(gerr)} problema(s)")
        for e in gerr:
            print(f"    - {e}")
    else:
        print(f"[OK]    {GATE_TEMPLATE}")


def validate_gate0_record(record, schema, plan, filename, errors):
    """Valida o registro REAL da autorizacao humana do GATE 0 (importavel)."""
    kv = []
    schema_keyword_violations(schema, "gate-00.schema", kv)
    errors.extend(kv)
    validate_node(record, schema, filename, errors)
    security_scan(record, errors)
    planning_content_scan(record, filename, errors)

    if not isinstance(record, dict):
        errors.append(f"{filename}: registro nao e objeto")
        return errors

    if record.get("status") != "AUTHORIZED_FOR_SINGLE_GATE":
        errors.append(f"{filename}: status deve ser AUTHORIZED_FOR_SINGLE_GATE")
    g = record.get("gate")
    gid = g.get("id") if isinstance(g, dict) else None
    gname = g.get("name") if isinstance(g, dict) else None
    if gid != 0:
        errors.append(f"{filename}: gate.id deve ser 0")
    if gname != "PROVENANCE_RECONFIRMATION":
        errors.append(f"{filename}: gate.name deve ser PROVENANCE_RECONFIRMATION")
    if record.get("decision") != "APPROVE_GATE_0":
        errors.append(f"{filename}: decision deve ser APPROVE_GATE_0")
    if record.get("execution_state") != "AUTHORIZED_NOT_STARTED":
        errors.append(f"{filename}: execution_state deve ser AUTHORIZED_NOT_STARTED")

    # Identidade/autoridade nao vazias nem placeholder.
    for field in ("decider", "role", "authority", "channel"):
        val = record.get(field)
        if not isinstance(val, str) or not val.strip():
            errors.append(f"{filename}: campo '{field}' vazio")
        elif PLACEHOLDER_RE.search(val):
            errors.append(f"{filename}: campo '{field}' parece placeholder (categoria: placeholder)")
    if not valid_iso_date(record.get("date")):
        errors.append(f"{filename}: campo 'date' nao e uma data ISO valida")

    # Condicoes: >=17, numeradas 1..N em ordem, sem lacuna/repeticao, com texto.
    conds = record.get("conditions")
    if not isinstance(conds, list) or len(conds) < 17:
        errors.append(f"{filename}: 'conditions' deve ter ao menos 17 itens")
        conds = conds if isinstance(conds, list) else []
    ns = [c.get("n") for c in conds if isinstance(c, dict)]
    if ns != list(range(1, len(conds) + 1)):
        errors.append(f"{filename}: conditions devem ser numeradas 1..N em ordem, sem lacuna/repeticao")
    for i, c in enumerate(conds):
        if not isinstance(c, dict) or not str(c.get("text", "")).strip():
            errors.append(f"{filename}: conditions[{i}] sem texto")

    # Metodos permitidos: conjunto FECHADO (exatamente o esperado).
    am = record.get("allowed_methods")
    if not isinstance(am, list) or set(am) != GATE0_ALLOWED_METHODS:
        errors.append(f"{filename}: allowed_methods deve ser exatamente o conjunto permitido de metadados")
    # Acoes proibidas: conjunto MINIMO obrigatorio (subconjunto exigido).
    pa = record.get("prohibited_actions")
    if not isinstance(pa, list) or not GATE0_PROHIBITED_MIN.issubset(set(pa)):
        faltando = sorted(GATE0_PROHIBITED_MIN - set(pa if isinstance(pa, list) else []))
        errors.append(f"{filename}: prohibited_actions faltando itens obrigatorios: {faltando}")

    # Autorizacoes: somente as quatro documentais/GATE0 em true; todas as demais false.
    auth = record.get("authorizations")
    if not isinstance(auth, dict):
        errors.append(f"{filename}: 'authorizations' ausente")
    else:
        for k, v in auth.items():
            if k in GATE0_TRUE_FLAGS:
                if v is not True:
                    errors.append(f"{filename}: authorizations.{k} deve ser true")
            elif v is not False:
                errors.append(f"{filename}: authorizations.{k} deve ser false (nenhuma autorizacao alem do GATE 0)")
        # Defesa explicita dos pontos criticos.
        for k in ("gate_0_started", "gate_0_completed", "gate_1_authorized",
                  "materialization_authorized", "execution_without_client_authorized"):
            if auth.get(k) is not False:
                errors.append(f"{filename}: authorizations.{k} deve ser false")

    # Referencias relativas e existentes; plano e registro no mesmo GATE 0.
    for field in ("plan_ref", "source_decision_ref"):
        ref = record.get(field)
        _ref_ok(ref.get("path") if isinstance(ref, dict) else None, field, filename, errors)
    if isinstance(plan, dict):
        plan_gate_ids = [x.get("gate_id") for x in plan.get("gates", []) if isinstance(x, dict)]
        if 0 not in plan_gate_ids:
            errors.append(f"{filename}: plano nao contem GATE 0 correspondente")
    return errors


def validate_gate0(errors):
    """Orquestra a validacao do(s) registro(s) reais de decisao do GATE 0."""
    if not os.path.isdir(DECISIONS_DIR):
        return
    names = sorted(f for f in os.listdir(DECISIONS_DIR)
                   if f.startswith("binary-audit-gate-00-decision-record-") and f.endswith(".json"))
    if not names:
        return  # ainda sem registro de GATE 0
    plan = {}
    try:
        plan = load_json(os.path.join(AUDIT_DIR, PLAN_TEMPLATE))
    except Fail:
        plan = {}
    try:
        schema = load_json(os.path.join(SCHEMA_DIR, GATE0_SCHEMA))
    except Fail as exc:
        errors.append(str(exc))
        return
    for name in names:
        rec_errors = []
        try:
            record = load_json(os.path.join(DECISIONS_DIR, name))
            validate_gate0_record(record, schema, plan, name, rec_errors)
        except Fail as exc:
            rec_errors.append(str(exc))
        if rec_errors:
            errors.extend(rec_errors)
            print(f"[FALHA] decisions/{name}: {len(rec_errors)} problema(s)")
            for e in rec_errors:
                print(f"    - {e}")
        else:
            print(f"[OK]    decisions/{name}")


def check_evidence_dir_names(names, errors):
    """evidence/ so pode conter registros reconhecidos de evidencia de gate."""
    for n in names:
        if not (n.endswith(".json") and n.startswith(EVIDENCE_FILE_PREFIXES)):
            errors.append(f"evidence/: arquivo inesperado '{n}'")


def validate_gate0_evidence(ev, schema, authorization, filename, errors):
    """Valida a evidencia real da execucao do GATE 0 (offline, importavel)."""
    kv = []
    schema_keyword_violations(schema, "gate-00-evidence.schema", kv)
    errors.extend(kv)
    validate_node(ev, schema, filename, errors)
    security_scan(ev, errors)
    planning_content_scan(ev, filename, errors)

    if not isinstance(ev, dict):
        errors.append(f"{filename}: evidencia nao e objeto")
        return errors

    # Endpoints/URLs de conteudo proibidos em qualquer string.
    for where, text in iter_strings(ev):
        if FORBIDDEN_ENDPOINT_RE.search(text):
            errors.append(f"{filename}{where}: endpoint/URL de conteudo proibido (categoria: content-endpoint)")

    status = ev.get("status")
    outcome = ev.get("outcome")
    if status != outcome:
        errors.append(f"{filename}: status ({status}) deve ser igual a outcome ({outcome})")

    gate = ev.get("gate") or {}
    if gate.get("id") != 0 or gate.get("name") != "PROVENANCE_RECONFIRMATION":
        errors.append(f"{filename}: gate deve ser id=0 name=PROVENANCE_RECONFIRMATION")

    # Autorizacao anterior valida.
    if isinstance(authorization, dict):
        if authorization.get("decision") != "APPROVE_GATE_0":
            errors.append(f"{filename}: autorizacao anterior nao e APPROVE_GATE_0")
        aauth = authorization.get("authorizations", {})
        if aauth.get("provenance_reconfirmation_authorized") is not True:
            errors.append(f"{filename}: autorizacao anterior nao habilita provenance_reconfirmation")
    else:
        errors.append(f"{filename}: registro de autorizacao do GATE 0 ausente/invalido")

    ex = ev.get("execution") or {}
    st, ft = ex.get("started_at"), ex.get("finished_at")
    if isinstance(st, str) and isinstance(ft, str) and st > ft:
        errors.append(f"{filename}: started_at posterior a finished_at")

    # Consistencia status <-> execucao.
    if status in ("COMPLETED_PASS", "COMPLETED_INCONCLUSIVE"):
        if ex.get("gate_0_completed") is not True or ex.get("execution_state") != "COMPLETED":
            errors.append(f"{filename}: {status} exige gate_0_completed=true e execution_state=COMPLETED")
    elif status == "STOPPED":
        if ex.get("gate_0_completed") is not False or ex.get("execution_state") != "STOPPED":
            errors.append(f"{filename}: STOPPED exige gate_0_completed=false e execution_state=STOPPED")
        if not ev.get("findings"):
            errors.append(f"{filename}: STOPPED exige motivo registrado em findings")

    # Commit esperado deve coincidir com o commit fixado das etapas anteriores.
    up_exp = ev.get("upstream_expected") or {}
    if up_exp.get("commit_oid") != EXPECTED_PINNED_COMMIT:
        errors.append(f"{filename}: upstream_expected.commit_oid != commit fixado")
    if up_exp.get("artifact_path") != EXPECTED_ARTIFACT_PATH:
        errors.append(f"{filename}: upstream_expected.artifact_path inconsistente com os documentos internos")
    if up_exp.get("repository_full_name") != EXPECTED_REPOSITORY:
        errors.append(f"{filename}: upstream_expected.repository inconsistente")

    ce = ev.get("commit_evidence") or {}
    te = ev.get("tree_evidence") or {}
    ae = ev.get("artifact_evidence") or {}

    # Invariantes de seguranca do artefato.
    if ae.get("binary_sha256") is not None:
        errors.append(f"{filename}: binary_sha256 deve ser null")
    for k in ("binary_sha256_computed", "blob_content_accessed", "binary_materialized"):
        if ae.get(k) is not False:
            errors.append(f"{filename}: artifact_evidence.{k} deve ser false")
    if ae.get("git_blob_oid_algorithm") != "GIT_OBJECT_ID":
        errors.append(f"{filename}: git_blob_oid_algorithm deve ser GIT_OBJECT_ID")
    if isinstance(ae.get("size_bytes_metadata"), int) and ae["size_bytes_metadata"] < 0:
        errors.append(f"{filename}: size_bytes_metadata nao pode ser negativo")

    # Regras especificas de COMPLETED_PASS.
    if status == "COMPLETED_PASS":
        if ce.get("observed_commit_oid") != ce.get("expected_commit_oid"):
            errors.append(f"{filename}: COMPLETED_PASS exige commit observado == esperado")
        if ce.get("object_type") != "commit" or ce.get("commit_exists") is not True:
            errors.append(f"{filename}: COMPLETED_PASS exige objeto commit existente")
        if te.get("matching_paths_count") != 1:
            errors.append(f"{filename}: COMPLETED_PASS exige exatamente 1 correspondencia de caminho")
        if te.get("artifact_entry_type") != "blob":
            errors.append(f"{filename}: COMPLETED_PASS exige entrada do tipo blob")
        if te.get("artifact_path_found") != EXPECTED_ARTIFACT_PATH:
            errors.append(f"{filename}: COMPLETED_PASS exige caminho canonico encontrado")
        if ae.get("git_blob_oid") != EXPECTED_ARTIFACT_BLOB:
            errors.append(f"{filename}: COMPLETED_PASS exige blob OID consistente com o esperado")
        if ae.get("size_bytes_metadata") != EXPECTED_ARTIFACT_SIZE:
            errors.append(f"{filename}: COMPLETED_PASS exige tamanho consistente com o esperado")
        cm = ev.get("consistency_matrix") or []
        if any(row.get("result") != "MATCH" for row in cm if isinstance(row, dict)):
            errors.append(f"{filename}: COMPLETED_PASS nao admite linha != MATCH na matriz")
    elif status == "COMPLETED_INCONCLUSIVE":
        if not ev.get("limitations"):
            errors.append(f"{filename}: COMPLETED_INCONCLUSIVE exige limitacoes registradas")

    # Query log: sequencia e timestamps ordenados; classes permitidas.
    ql = ev.get("query_log") or []
    seqs = [q.get("sequence") for q in ql if isinstance(q, dict)]
    if seqs != list(range(1, len(ql) + 1)):
        errors.append(f"{filename}: query_log deve ter sequence 1..N em ordem")
    tss = [q.get("timestamp") for q in ql if isinstance(q, dict)]
    if tss != sorted(tss):
        errors.append(f"{filename}: query_log deve ter timestamps nao decrescentes")
    for q in ql:
        if isinstance(q, dict) and q.get("endpoint_class") not in ALLOWED_ENDPOINT_CLASSES:
            errors.append(f"{filename}: query_log endpoint_class nao permitido: {q.get('endpoint_class')}")

    # Autorizacoes operacionais: todas false; GATE 1 false.
    auth = ev.get("authorizations") or {}
    for k, v in auth.items():
        if v is not False:
            errors.append(f"{filename}: authorizations.{k} deve ser false (execucao do GATE 0 nao autoriza nada)")

    # Referencias relativas e existentes.
    for field in ("authorization_ref", "plan_ref", "source_decision_ref"):
        ref = ev.get(field)
        _ref_ok(ref.get("path") if isinstance(ref, dict) else None, field, filename, errors)
    return errors


def validate_gate0_evidence_all(errors):
    """Orquestra a validacao da(s) evidencia(s) do GATE 0."""
    if not os.path.isdir(EVIDENCE_DIR):
        return
    check_evidence_dir_names(sorted(os.listdir(EVIDENCE_DIR)), errors)
    names = sorted(f for f in os.listdir(EVIDENCE_DIR)
                   if f.startswith(EVIDENCE_FILE_PREFIXES) and f.endswith(".json"))
    if not names:
        return
    authorization = {}
    try:
        authorization = load_json(os.path.join(DECISIONS_DIR, GATE0_DECISION_RECORD))
    except Fail:
        authorization = {}
    try:
        schema = load_json(os.path.join(SCHEMA_DIR, GATE0_EVIDENCE_SCHEMA))
    except Fail as exc:
        errors.append(str(exc))
        return
    for name in names:
        ev_errors = []
        try:
            ev = load_json(os.path.join(EVIDENCE_DIR, name))
            validate_gate0_evidence(ev, schema, authorization, name, ev_errors)
        except Fail as exc:
            ev_errors.append(str(exc))
        if ev_errors:
            errors.extend(ev_errors)
            print(f"[FALHA] evidence/{name}: {len(ev_errors)} problema(s)")
            for e in ev_errors:
                print(f"    - {e}")
        else:
            print(f"[OK]    evidence/{name}")


def main():
    all_errors = []
    for artifact, schema_name in ARTIFACTS:
        apath = os.path.join(AUDIT_DIR, artifact)
        spath = os.path.join(SCHEMA_DIR, schema_name)
        try:
            data = load_json(apath)
            schema = load_json(spath)
        except Fail as exc:
            all_errors.append(str(exc))
            continue

        errors = []
        validate_node(data, schema, artifact, errors)
        security_scan(data, errors)
        forbidden_flags(data, artifact, errors)

        if errors:
            all_errors.extend(errors)
            print(f"[FALHA] {artifact}: {len(errors)} problema(s)")
            for e in errors:
                print(f"    - {e}")
        else:
            print(f"[OK]    {artifact}")

    cross_errors = []
    cross_checks(cross_errors)
    if cross_errors:
        all_errors.extend(cross_errors)
        print(f"[FALHA] cross-checks: {len(cross_errors)} problema(s)")
        for e in cross_errors:
            print(f"    - {e}")
    else:
        print("[OK]    cross-checks (pacote/registro/referencias)")

    real_errors = []
    validate_real_records(real_errors)
    all_errors.extend(real_errors)

    binary_errors = []
    validate_binary_audit(binary_errors)
    all_errors.extend(binary_errors)

    gate0_errors = []
    validate_gate0(gate0_errors)
    all_errors.extend(gate0_errors)

    evidence_errors = []
    validate_gate0_evidence_all(evidence_errors)
    all_errors.extend(evidence_errors)

    if all_errors:
        print(f"\nValidacao FALHOU com {len(all_errors)} problema(s).")
        return 1
    print(f"\nValidacao OK: {len(ARTIFACTS)} artefatos, schemas, regras de seguranca, "
          f"cross-checks, registros reais de decisao, plano da auditoria binaria, "
          f"autorizacao do GATE 0 e evidencia do GATE 0.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Fail as exc:
        print(f"[ERRO] {exc}")
        sys.exit(2)
    except Exception as exc:  # sem traceback para o usuario
        print(f"[ERRO] falha inesperada: {exc}")
        sys.exit(2)
