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
GATE0_EVIDENCE_PREFIX = "binary-audit-gate-00-provenance-evidence-"
# Prefixo de evidencia do GATE 2 (ETAPA 2P-E-C2-A).
GATE2_EVIDENCE_PREFIX = "binary-audit-gate-02-integrity-evidence-"
# Prefixo de evidencia do GATE 3 (ETAPA 2P-E-C3).
GATE3_EVIDENCE_PREFIX = "binary-audit-gate-03-identity-signature-evidence-"
# Prefixo de evidencia da FUTURA repeticao corretiva do GATE 3 (ETAPA 2P-E-C3-R2:
# convencao; nenhum arquivo real existe ainda).
GATE3_REPEAT_EVIDENCE_PREFIX = "binary-audit-gate-03-corrective-repeat-evidence-"
# Prefixos aceitos em evidence/ (o orquestrador de cada gate filtra o seu proprio).
EVIDENCE_FILE_PREFIXES = (GATE0_EVIDENCE_PREFIX, GATE2_EVIDENCE_PREFIX,
                          GATE3_EVIDENCE_PREFIX, GATE3_REPEAT_EVIDENCE_PREFIX)
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

# --- ETAPA 2P-E-C1-A: registro real da autorizacao humana do GATE 1 ---
# GATE 1 e DECISAO HUMANA APENAS (autorizacao para materializacao): nao materializa,
# nao baixa, nao acessa conteudo, nao hasheia, nao inspeciona e nao executa nada. Ele
# apenas autoriza uma materializacao FUTURA do blob fixado, num GATE 2 separado.
GATE1_SCHEMA = "binary-audit-gate-01-decision-record-real.schema.json"
GATE1_DECISION_PREFIX = "binary-audit-gate-01-decision-record-"
EXPECTED_TREE_OID = "1aebae06d5c71a145afc35cc72fcf5c210a08758"
EXPECTED_PR48_SQUASH = "219b96b0688d9e5b71ae555b23e4166ef136424d"
# Flags que DEVEM ser true no registro do GATE 1 (decisao humana + autorizacao concedida).
GATE1_TRUE_FLAGS = {
    "human_decision_required", "human_decision_received", "gate_selected",
    "gate_0_completed", "materialization_authorized",
}
# Pontos criticos que DEVEM permanecer false mesmo com a materializacao autorizada.
GATE1_CRITICAL_FALSE = {
    "gate_2_authorized", "hashing_authorized", "static_inspection_authorized",
    "execution_without_client_authorized", "client_copy_provision_authorized",
    "execution_with_client_copy_authorized", "distribution_authorized",
    "first_login_authorized", "vps_access_authorized",
}

# --- ETAPA 2P-E-C2-A: GATE 2 (materializacao e integridade local) ---
# GATE 2 obtem exatamente o blob fixado, calcula integridade local e remove o
# arquivo. Autoriza materializacao e hashing; NAO autoriza execucao, inspecao
# estatica/dinamica, sandbox, integracao no cliente, distribuicao, VPS nem o GATE 3.
GATE2_DECISION_SCHEMA = "binary-audit-gate-02-decision-record-real.schema.json"
GATE2_EVIDENCE_SCHEMA = "binary-audit-gate-02-integrity-evidence.schema.json"
GATE2_DECISION_PREFIX = "binary-audit-gate-02-decision-record-"
GATE1_DECISION_RECORD = "binary-audit-gate-01-decision-record-2026-08-01.json"
# Squash do PR #49 (integrou o GATE 1); referenciado pelos artefatos do GATE 2.
EXPECTED_PR49_SQUASH = "6a078f338bc69307e942ba390b565da4008acc40"
# SHA-256 local esperado do conteudo do blob fixado (imutavel; confere o registro).
EXPECTED_ARTIFACT_SHA256 = (
    "345f3464ee72a60afc97bde0773410f47348a00d8629182fe52741c5f1a42874")
# Flags true no registro de decisao do GATE 2 (decisao + pre-condicao + grants).
GATE2_DECISION_TRUE_FLAGS = {
    "human_decision_required", "human_decision_received", "gate_selected",
    "gate_0_completed", "materialization_authorized", "gate_2_authorized",
    "hashing_authorized",
}
# Pontos criticos que DEVEM permanecer false no GATE 2 (sem autorizacao transitiva).
GATE2_CRITICAL_FALSE = {
    "gate_3_authorized", "static_inspection_authorized",
    "execution_without_client_authorized", "execution_with_client_copy_authorized",
    "client_copy_provision_authorized", "external_reputation_upload_authorized",
    "sandbox_creation_authorized", "distribution_authorized",
    "first_login_authorized", "vps_access_authorized",
}
# Regex hexadecimal generica (para diferenciar 40-hex Git OID de 64-hex SHA-256).
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")

# --- ETAPA 2P-E-C3: GATE 3 (identidade e assinatura estatica offline) ---
# GATE 3 rematerializa temporariamente o mesmo blob fixado, reconfirma a identidade
# local (tamanho, Git OID e SHA-256 iguais aos do GATE 2) e inspeciona estaticamente
# APENAS a identidade do PE e a assinatura Authenticode. NAO executa/carrega o binario,
# NAO faz analise dinamica/sandbox/rede pos-obtencao, NAO inventaria secoes/imports/
# exports/strings (GATE 4) e NAO autoriza o GATE 4.
GATE3_DECISION_SCHEMA = "binary-audit-gate-03-decision-record-real.schema.json"
GATE3_EVIDENCE_SCHEMA = "binary-audit-gate-03-identity-signature-evidence.schema.json"
GATE3_DECISION_PREFIX = "binary-audit-gate-03-decision-record-"
GATE2_DECISION_RECORD = "binary-audit-gate-02-decision-record-2026-08-01.json"
GATE2_EVIDENCE_RECORD = "binary-audit-gate-02-integrity-evidence-2026-08-01.json"
# Squash do PR #50 (integrou a decisao/evidencia do GATE 2); referenciado pelo GATE 3.
EXPECTED_PR50_SQUASH = "6ab37b2a7ae65fd6b4fdf184759b345cf9ce4bd6"
# Flags true no registro de decisao do GATE 3 (decisao + pre-condicao + grants do gate).
GATE3_DECISION_TRUE_FLAGS = {
    "human_decision_required", "human_decision_received", "gate_selected",
    "gate_2_completed", "temporary_materialization_authorized",
    "local_hashing_authorized", "static_identity_inspection_authorized",
    "authenticode_inspection_authorized", "gate_3_authorized",
}
# Pontos criticos que DEVEM permanecer false no GATE 3 (sem autorizacao transitiva).
GATE3_CRITICAL_FALSE = {
    "gate_4_authorized", "execution_authorized", "dynamic_analysis_authorized",
    "external_reputation_upload_authorized", "network_validation_authorized",
    "sandbox_creation_authorized", "client_copy_provision_authorized",
    "client_modification_authorized", "patch_review_authorized",
    "patch_application_authorized", "client_preparation_authorized",
    "test_account_authorized", "first_login_authorized", "vps_access_authorized",
    "distribution_authorized",
}
# Estados fechados da inspecao de assinatura (conjunto FECHADO).
GATE3_CRYPTO_VERIF_STATES = {
    "NOT_PERFORMED_OFFLINE", "PERFORMED_VALID", "PERFORMED_INVALID",
    "NOT_APPLICABLE_NO_SIGNATURE",
}
GATE3_CHAIN_TRUST_STATES = {
    "NOT_EVALUATED_OFFLINE", "NOT_APPLICABLE_NO_SIGNATURE",
}

# --- ETAPA 2P-E-C3-R2: convencao da FUTURA repeticao corretiva do GATE 3 ---
# Schemas e validadores prontos para quando (e SE) uma repeticao corretiva for
# autorizada por decisao humana separada. Nesta etapa NAO existe registro real; a
# evidencia historica invalidada permanece EVIDENCE_INVALIDATED_PENDING_REPEAT e NUNCA
# pode ser revertida a COMPLETED_PASS.
GATE3_REPEAT_DECISION_SCHEMA = "binary-audit-gate-03-corrective-repeat-decision-record-real.schema.json"
GATE3_REPEAT_EVIDENCE_SCHEMA = "binary-audit-gate-03-corrective-repeat-evidence.schema.json"
GATE3_REPEAT_DECISION_PREFIX = "binary-audit-gate-03-corrective-repeat-decision-record-"
GATE3_HISTORICAL_INVALIDATED_EVIDENCE = "binary-audit-gate-03-identity-signature-evidence-2026-08-03.json"

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
                   if f.startswith(GATE0_EVIDENCE_PREFIX) and f.endswith(".json"))
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


def validate_gate1_record(record, schema, plan, gate0_decision, gate0_evidence,
                          filename, errors):
    """Valida o registro REAL da autorizacao humana do GATE 1 (importavel).

    O GATE 1 e decisao-humana-apenas: autoriza uma materializacao FUTURA do blob
    fixado (GATE 2 separado). NADA e materializado, baixado, acessado, hasheado,
    inspecionado ou executado nesta etapa. A funcao exige, alem do schema, que a
    unica autorizacao concedida seja materialization_authorized=true, que todos os
    demais pontos criticos permanecam false, que o escopo esteja fechado ao objeto
    imutavel canonico e que a cadeia (plano, decisao e evidencia do GATE 0, squash
    do PR #48) seja coerente.
    """
    kv = []
    schema_keyword_violations(schema, "gate-01.schema", kv)
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
    if gid != 1:
        errors.append(f"{filename}: gate.id deve ser 1")
    if gname != "MATERIALIZATION_AUTHORIZATION":
        errors.append(f"{filename}: gate.name deve ser MATERIALIZATION_AUTHORIZATION")
    if record.get("decision") != "AUTHORIZE_MATERIALIZATION":
        errors.append(f"{filename}: decision deve ser AUTHORIZE_MATERIALIZATION")
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

    # Condicoes: >=20, numeradas 1..N em ordem, sem lacuna/repeticao, com texto.
    conds = record.get("conditions")
    if not isinstance(conds, list) or len(conds) < 20:
        errors.append(f"{filename}: 'conditions' deve ter ao menos 20 itens")
        conds = conds if isinstance(conds, list) else []
    ns = [c.get("n") for c in conds if isinstance(c, dict)]
    if ns != list(range(1, len(conds) + 1)):
        errors.append(f"{filename}: conditions devem ser numeradas 1..N em ordem, sem lacuna/repeticao")
    for i, c in enumerate(conds):
        if not isinstance(c, dict) or not str(c.get("text", "")).strip():
            errors.append(f"{filename}: conditions[{i}] sem texto")

    # Autorizacoes: SOMENTE a materializacao (e as flags de decisao/pre-condicao) em
    # true; todas as demais false. Defesa explicita dos pontos criticos.
    auth = record.get("authorizations")
    if not isinstance(auth, dict):
        errors.append(f"{filename}: 'authorizations' ausente")
    else:
        for k, v in auth.items():
            if k in GATE1_TRUE_FLAGS:
                if v is not True:
                    errors.append(f"{filename}: authorizations.{k} deve ser true")
            elif v is not False:
                errors.append(f"{filename}: authorizations.{k} deve ser false "
                              f"(unica autorizacao concedida e materialization_authorized)")
        if auth.get("materialization_authorized") is not True:
            errors.append(f"{filename}: authorizations.materialization_authorized deve ser true (grant do GATE 1)")
        for k in GATE1_CRITICAL_FALSE:
            if auth.get(k) is not False:
                errors.append(f"{filename}: authorizations.{k} deve ser false (sem autorizacao transitiva)")

    # Invariantes de seguranca: nada foi materializado/acessado/hasheado nesta etapa.
    sa = record.get("security_assertions")
    if not isinstance(sa, dict):
        errors.append(f"{filename}: 'security_assertions' ausente")
    else:
        if sa.get("binary_sha256") is not None:
            errors.append(f"{filename}: security_assertions.binary_sha256 deve ser null")
        for k in ("blob_content_accessed", "binary_materialized", "binary_sha256_computed",
                  "raw_responses_versioned", "binary_versioned"):
            if sa.get(k) is not False:
                errors.append(f"{filename}: security_assertions.{k} deve ser false")
        for k in ("no_download_performed", "no_upstream_query_this_stage",
                  "no_clone_or_fetch_upstream", "no_archive_or_release_asset",
                  "no_static_inspection_performed", "no_execution_performed",
                  "no_sandbox_created", "no_vps_access"):
            if sa.get(k) is not True:
                errors.append(f"{filename}: security_assertions.{k} deve ser true")

    # Escopo fechado ao objeto imutavel canonico (identificadores exatos).
    ms = record.get("materialization_scope")
    if not isinstance(ms, dict):
        errors.append(f"{filename}: 'materialization_scope' ausente")
    else:
        expected_scope = {
            "repository_full_name": EXPECTED_REPOSITORY,
            "commit_oid": EXPECTED_PINNED_COMMIT,
            "tree_oid": EXPECTED_TREE_OID,
            "artifact_path": EXPECTED_ARTIFACT_PATH,
            "artifact_blob_oid": EXPECTED_ARTIFACT_BLOB,
            "artifact_blob_oid_algorithm": "GIT_OBJECT_ID",
            "artifact_blob_size": EXPECTED_ARTIFACT_SIZE,
            "max_files": 1,
            "network_scope": "GITHUB_OFFICIAL_ONLY",
        }
        for k, exp in expected_scope.items():
            if ms.get(k) != exp:
                errors.append(f"{filename}: materialization_scope.{k} deve ser {exp!r}")

    # Referencia explicita e correta ao squash do PR #48.
    ir = record.get("integration_ref")
    if not isinstance(ir, dict):
        errors.append(f"{filename}: 'integration_ref' ausente")
    else:
        if ir.get("pr") != 48:
            errors.append(f"{filename}: integration_ref.pr deve ser 48")
        if ir.get("squash_commit") != EXPECTED_PR48_SQUASH:
            errors.append(f"{filename}: integration_ref.squash_commit deve ser o squash do PR #48")
        if ir.get("base_branch") != "dev":
            errors.append(f"{filename}: integration_ref.base_branch deve ser dev")

    # Pre-condicao do GATE 0 (declarada no registro).
    pc = record.get("gate_0_precondition")
    if not isinstance(pc, dict):
        errors.append(f"{filename}: 'gate_0_precondition' ausente")
    else:
        if pc.get("gate_0_completed") is not True:
            errors.append(f"{filename}: gate_0_precondition.gate_0_completed deve ser true")
        if pc.get("gate_0_outcome") != "COMPLETED_PASS":
            errors.append(f"{filename}: gate_0_precondition.gate_0_outcome deve ser COMPLETED_PASS")

    # Referencias relativas e existentes.
    for field in ("plan_ref", "source_decision_ref", "prior_gate_decision_ref",
                  "gate_0_evidence_ref"):
        ref = record.get(field)
        _ref_ok(ref.get("path") if isinstance(ref, dict) else None, field, filename, errors)

    # Cross-check: plano contem GATE 1.
    if isinstance(plan, dict):
        plan_gate_ids = [x.get("gate_id") for x in plan.get("gates", []) if isinstance(x, dict)]
        if 1 not in plan_gate_ids:
            errors.append(f"{filename}: plano nao contem GATE 1 correspondente")

    # Cross-check: decisao anterior (GATE 0) e APPROVE_GATE_0.
    if isinstance(gate0_decision, dict):
        if gate0_decision.get("decision") != "APPROVE_GATE_0":
            errors.append(f"{filename}: decisao anterior referenciada nao e APPROVE_GATE_0")
    else:
        errors.append(f"{filename}: registro de decisao do GATE 0 ausente/invalido")

    # Cross-check: evidencia do GATE 0 concluida com COMPLETED_PASS e sem materializacao.
    if isinstance(gate0_evidence, dict):
        if gate0_evidence.get("outcome") != "COMPLETED_PASS":
            errors.append(f"{filename}: evidencia do GATE 0 nao esta COMPLETED_PASS")
        ex = gate0_evidence.get("execution") or {}
        if ex.get("gate_0_completed") is not True:
            errors.append(f"{filename}: evidencia do GATE 0 nao confirma gate_0_completed=true")
        ae = gate0_evidence.get("artifact_evidence") or {}
        if ae.get("binary_materialized") is not False or ae.get("binary_sha256") is not None:
            errors.append(f"{filename}: evidencia do GATE 0 indica materializacao/hash inesperados")
    else:
        errors.append(f"{filename}: evidencia do GATE 0 ausente/invalida")

    return errors


def validate_gate1(errors):
    """Orquestra a validacao do(s) registro(s) reais de decisao do GATE 1."""
    if not os.path.isdir(DECISIONS_DIR):
        return
    names = sorted(f for f in os.listdir(DECISIONS_DIR)
                   if f.startswith(GATE1_DECISION_PREFIX) and f.endswith(".json"))
    if not names:
        return  # ainda sem registro de GATE 1
    plan = {}
    try:
        plan = load_json(os.path.join(AUDIT_DIR, PLAN_TEMPLATE))
    except Fail:
        plan = {}
    gate0_decision = {}
    try:
        gate0_decision = load_json(os.path.join(DECISIONS_DIR, GATE0_DECISION_RECORD))
    except Fail:
        gate0_decision = {}
    gate0_evidence = {}
    if os.path.isdir(EVIDENCE_DIR):
        ev_names = sorted(f for f in os.listdir(EVIDENCE_DIR)
                          if f.startswith(GATE0_EVIDENCE_PREFIX) and f.endswith(".json"))
        if ev_names:
            try:
                gate0_evidence = load_json(os.path.join(EVIDENCE_DIR, ev_names[-1]))
            except Fail:
                gate0_evidence = {}
    try:
        schema = load_json(os.path.join(SCHEMA_DIR, GATE1_SCHEMA))
    except Fail as exc:
        errors.append(str(exc))
        return
    for name in names:
        rec_errors = []
        try:
            record = load_json(os.path.join(DECISIONS_DIR, name))
            validate_gate1_record(record, schema, plan, gate0_decision,
                                  gate0_evidence, name, rec_errors)
        except Fail as exc:
            rec_errors.append(str(exc))
        if rec_errors:
            errors.extend(rec_errors)
            print(f"[FALHA] decisions/{name}: {len(rec_errors)} problema(s)")
            for e in rec_errors:
                print(f"    - {e}")
        else:
            print(f"[OK]    decisions/{name}")


def _content_scan_allow_hashes(data, label, errors):
    """Como planning_content_scan, mas SEM a regra de 64-hex (o GATE 2 registra
    legitimamente o SHA-256). Ainda proibe comandos de download/execucao, URLs de
    binario e texto de aprovacao implicita do prebuilt."""
    for where, text in iter_strings(data):
        if DOWNLOAD_CMD_RE.search(text):
            errors.append(f"{label}{where}: comando de download proibido")
        if BINARY_URL_RE.search(text):
            errors.append(f"{label}{where}: URL direta para binario proibida")
        if WARP_EXEC_RE.search(text):
            errors.append(f"{label}{where}: comando de execucao do WARP proibido")
        if CLIENT_EXEC_RE.search(text):
            errors.append(f"{label}{where}: comando de execucao do cliente proibido")
        if FORBIDDEN_ENDPOINT_RE.search(text):
            errors.append(f"{label}{where}: endpoint/URL de conteudo bruto proibido")
        for rx in IMPLICIT_APPROVAL_RES:
            if rx.search(text):
                errors.append(f"{label}{where}: texto sugere aprovacao implicita do prebuilt")
                break


def validate_gate2_decision(record, schema, plan, gate1_decision, gate0_evidence,
                            filename, errors):
    """Valida o registro REAL da autorizacao humana do GATE 2 (importavel)."""
    kv = []
    schema_keyword_violations(schema, "gate-02-decision.schema", kv)
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
    if not isinstance(g, dict) or g.get("id") != 2 or g.get("name") != "MATERIALIZATION_AND_LOCAL_INTEGRITY":
        errors.append(f"{filename}: gate deve ser id=2 name=MATERIALIZATION_AND_LOCAL_INTEGRITY")
    if record.get("decision") != "AUTHORIZE_GATE_2":
        errors.append(f"{filename}: decision deve ser AUTHORIZE_GATE_2")
    if record.get("execution_state") != "AUTHORIZED_NOT_STARTED":
        errors.append(f"{filename}: execution_state deve ser AUTHORIZED_NOT_STARTED")

    for field in ("decider", "role", "authority", "channel"):
        val = record.get(field)
        if not isinstance(val, str) or not val.strip():
            errors.append(f"{filename}: campo '{field}' vazio")
        elif PLACEHOLDER_RE.search(val):
            errors.append(f"{filename}: campo '{field}' parece placeholder (categoria: placeholder)")
    if not valid_iso_date(record.get("date")):
        errors.append(f"{filename}: campo 'date' nao e uma data ISO valida")

    conds = record.get("conditions")
    if not isinstance(conds, list) or len(conds) < 20:
        errors.append(f"{filename}: 'conditions' deve ter ao menos 20 itens")
        conds = conds if isinstance(conds, list) else []
    ns = [c.get("n") for c in conds if isinstance(c, dict)]
    if ns != list(range(1, len(conds) + 1)):
        errors.append(f"{filename}: conditions devem ser numeradas 1..N em ordem, sem lacuna/repeticao")

    auth = record.get("authorizations")
    if not isinstance(auth, dict):
        errors.append(f"{filename}: 'authorizations' ausente")
    else:
        for k, v in auth.items():
            if k in GATE2_DECISION_TRUE_FLAGS:
                if v is not True:
                    errors.append(f"{filename}: authorizations.{k} deve ser true")
            elif v is not False:
                errors.append(f"{filename}: authorizations.{k} deve ser false (grants do GATE 2 sao limitados)")
        for k in GATE2_CRITICAL_FALSE:
            if auth.get(k) is not False:
                errors.append(f"{filename}: authorizations.{k} deve ser false (sem autorizacao transitiva)")

    _check_materialization_scope(record.get("materialization_scope"), filename, errors)
    _check_integration_ref(record.get("integration_ref"), filename, errors)

    pc = record.get("precondition")
    if not isinstance(pc, dict):
        errors.append(f"{filename}: 'precondition' ausente")
    else:
        if pc.get("gate_0_completed") is not True:
            errors.append(f"{filename}: precondition.gate_0_completed deve ser true")
        if pc.get("gate_0_outcome") != "COMPLETED_PASS":
            errors.append(f"{filename}: precondition.gate_0_outcome deve ser COMPLETED_PASS")
        if pc.get("gate_1_materialization_authorized") is not True:
            errors.append(f"{filename}: precondition.gate_1_materialization_authorized deve ser true")

    for field in ("plan_ref", "source_decision_ref", "prior_gate_decision_ref",
                  "gate_0_evidence_ref"):
        ref = record.get(field)
        _ref_ok(ref.get("path") if isinstance(ref, dict) else None, field, filename, errors)

    if isinstance(plan, dict):
        plan_gate_ids = [x.get("gate_id") for x in plan.get("gates", []) if isinstance(x, dict)]
        if 2 not in plan_gate_ids:
            errors.append(f"{filename}: plano nao contem GATE 2 correspondente")
    if isinstance(gate1_decision, dict):
        a1 = gate1_decision.get("authorizations", {})
        if gate1_decision.get("decision") != "AUTHORIZE_MATERIALIZATION" or a1.get("materialization_authorized") is not True:
            errors.append(f"{filename}: GATE 1 referenciado nao autoriza materializacao")
    else:
        errors.append(f"{filename}: decisao do GATE 1 ausente/invalida")
    if isinstance(gate0_evidence, dict):
        if gate0_evidence.get("outcome") != "COMPLETED_PASS":
            errors.append(f"{filename}: evidencia do GATE 0 nao esta COMPLETED_PASS")
    else:
        errors.append(f"{filename}: evidencia do GATE 0 ausente/invalida")
    return errors


def _check_materialization_scope(ms, filename, errors):
    """Escopo fechado ao objeto imutavel canonico (identificadores exatos)."""
    if not isinstance(ms, dict):
        errors.append(f"{filename}: 'materialization_scope' ausente")
        return
    expected = {
        "repository_full_name": EXPECTED_REPOSITORY,
        "commit_oid": EXPECTED_PINNED_COMMIT,
        "tree_oid": EXPECTED_TREE_OID,
        "artifact_path": EXPECTED_ARTIFACT_PATH,
        "artifact_blob_oid": EXPECTED_ARTIFACT_BLOB,
        "artifact_blob_oid_algorithm": "GIT_OBJECT_ID",
        "artifact_blob_size": EXPECTED_ARTIFACT_SIZE,
        "max_files": 1,
        "network_scope": "GITHUB_OFFICIAL_ONLY",
    }
    for k, exp in expected.items():
        if ms.get(k) != exp:
            errors.append(f"{filename}: materialization_scope.{k} deve ser {exp!r}")


def _check_integration_ref(ir, filename, errors):
    if not isinstance(ir, dict):
        errors.append(f"{filename}: 'integration_ref' ausente")
        return
    if ir.get("pr") != 49:
        errors.append(f"{filename}: integration_ref.pr deve ser 49")
    if ir.get("squash_commit") != EXPECTED_PR49_SQUASH:
        errors.append(f"{filename}: integration_ref.squash_commit deve ser o squash do PR #49")
    if ir.get("base_branch") != "dev":
        errors.append(f"{filename}: integration_ref.base_branch deve ser dev")


def validate_gate2_evidence(ev, schema, gate2_decision, gate1_decision,
                            gate0_evidence, filename, errors):
    """Valida a evidencia REAL da execucao do GATE 2 (offline, importavel).

    Ao contrario dos artefatos de planejamento, a evidencia do GATE 2 registra
    legitimamente o SHA-256 do conteudo; por isso a varredura de conteudo NAO aplica
    a regra generica de 64-hex, mas ainda proibe download/execucao/URLs de binario.
    """
    kv = []
    schema_keyword_violations(schema, "gate-02-evidence.schema", kv)
    errors.extend(kv)
    validate_node(ev, schema, filename, errors)
    security_scan(ev, errors)
    _content_scan_allow_hashes(ev, filename, errors)

    if not isinstance(ev, dict):
        errors.append(f"{filename}: evidencia nao e objeto")
        return errors

    if ev.get("status") != ev.get("outcome"):
        errors.append(f"{filename}: status deve ser igual a outcome")
    if ev.get("outcome") != "COMPLETED_PASS":
        errors.append(f"{filename}: outcome deve ser COMPLETED_PASS")
    g = ev.get("gate")
    if not isinstance(g, dict) or g.get("id") != 2 or g.get("name") != "MATERIALIZATION_AND_LOCAL_INTEGRITY":
        errors.append(f"{filename}: gate deve ser id=2 name=MATERIALIZATION_AND_LOCAL_INTEGRITY")

    # Execucao: iniciada, concluida, tempos ordenados e reais.
    ex = ev.get("execution") or {}
    if ex.get("gate_2_started") is not True or ex.get("gate_2_completed") is not True:
        errors.append(f"{filename}: execution deve ter gate_2_started e gate_2_completed true")
    if ex.get("execution_state") != "COMPLETED":
        errors.append(f"{filename}: execution_state deve ser COMPLETED")
    st, ft, cl = ex.get("started_at"), ex.get("finished_at"), ex.get("cleanup_at")
    if isinstance(st, str) and isinstance(ft, str) and st > ft:
        errors.append(f"{filename}: started_at posterior a finished_at")
    if isinstance(ft, str) and isinstance(cl, str) and ft > cl:
        errors.append(f"{filename}: finished_at posterior a cleanup_at (limpeza deve ser depois)")
    if ex.get("method") != "GITHUB_OFFICIAL_GIT_DATA_API_BLOB_BY_OID":
        errors.append(f"{filename}: method fora do conjunto autorizado")
    if ex.get("network_scope") != "GITHUB_OFFICIAL_ONLY":
        errors.append(f"{filename}: network_scope deve ser GITHUB_OFFICIAL_ONLY")

    # Identificadores esperados == canonicos.
    up = ev.get("upstream_expected") or {}
    for k, exp in (("repository_full_name", EXPECTED_REPOSITORY),
                   ("commit_oid", EXPECTED_PINNED_COMMIT),
                   ("tree_oid", EXPECTED_TREE_OID),
                   ("artifact_path", EXPECTED_ARTIFACT_PATH),
                   ("artifact_blob_oid", EXPECTED_ARTIFACT_BLOB),
                   ("artifact_blob_size", EXPECTED_ARTIFACT_SIZE)):
        if up.get(k) != exp:
            errors.append(f"{filename}: upstream_expected.{k} deve ser {exp!r}")

    # Reconfirmacao de identidade.
    ir = ev.get("identity_reconfirmation") or {}
    if ir.get("identity_match") is not True:
        errors.append(f"{filename}: identity_reconfirmation.identity_match deve ser true")
    if ir.get("artifact_entry_type") != "blob":
        errors.append(f"{filename}: artifact_entry_type deve ser blob")

    # Materializacao: exatamente 1 arquivo, fora do repo, nao aberto/executado.
    mt = ev.get("materialization") or {}
    if mt.get("materialized_file_count") != 1:
        errors.append(f"{filename}: materialized_file_count deve ser 1")
    if mt.get("temporary_dir_outside_repo") is not True:
        errors.append(f"{filename}: temporary_dir_outside_repo deve ser true")
    if mt.get("opened") is not False or mt.get("executed") is not False:
        errors.append(f"{filename}: materialization.opened/executed devem ser false")

    # Integridade: tamanhos e Git OIDs iguais; SHA-256 valido e distinto do Git OID.
    it = ev.get("integrity") or {}
    if it.get("expected_size") != EXPECTED_ARTIFACT_SIZE or it.get("observed_size") != EXPECTED_ARTIFACT_SIZE:
        errors.append(f"{filename}: tamanhos devem ser {EXPECTED_ARTIFACT_SIZE}")
    if it.get("size_match") is not True:
        errors.append(f"{filename}: integrity.size_match deve ser true")
    if it.get("git_blob_oid_algorithm") != "GIT_OBJECT_ID":
        errors.append(f"{filename}: git_blob_oid_algorithm deve ser GIT_OBJECT_ID")
    goe, goc = it.get("git_blob_oid_expected"), it.get("git_blob_oid_computed")
    if goe != EXPECTED_ARTIFACT_BLOB or goc != EXPECTED_ARTIFACT_BLOB:
        errors.append(f"{filename}: git_blob_oid esperado/calculado devem ser {EXPECTED_ARTIFACT_BLOB}")
    if it.get("git_blob_oid_match") is not True:
        errors.append(f"{filename}: integrity.git_blob_oid_match deve ser true")
    sha = it.get("sha256_local")
    if not isinstance(sha, str) or not HEX64_RE.match(sha):
        errors.append(f"{filename}: sha256_local deve ter 64 caracteres hex")
    elif sha != EXPECTED_ARTIFACT_SHA256:
        errors.append(f"{filename}: sha256_local nao confere com o conteudo do blob fixado")
    if it.get("sha256_algorithm") != "SHA-256":
        errors.append(f"{filename}: sha256_algorithm deve ser SHA-256")
    if it.get("sha256_length") != 64:
        errors.append(f"{filename}: sha256_length deve ser 64")
    # Separacao SHA-256 x Git OID: nunca podem ser iguais.
    if isinstance(sha, str) and sha == EXPECTED_ARTIFACT_BLOB:
        errors.append(f"{filename}: SHA-256 nao pode ser igual ao Git object ID")
    if isinstance(sha, str) and HEX40_RE.match(sha):
        errors.append(f"{filename}: SHA-256 nao pode ter 40 hex (isso e Git OID)")
    if it.get("sha256_is_not_git_oid") is not True:
        errors.append(f"{filename}: integrity.sha256_is_not_git_oid deve ser true")

    # Invariantes de seguranca.
    sa = ev.get("security_assertions") or {}
    for k in ("blob_content_accessed", "binary_materialized", "binary_sha256_computed"):
        if sa.get(k) is not True:
            errors.append(f"{filename}: security_assertions.{k} deve ser true (contexto GATE 2)")
    bs = sa.get("binary_sha256")
    if not isinstance(bs, str) or not HEX64_RE.match(bs):
        errors.append(f"{filename}: security_assertions.binary_sha256 deve ter 64 hex")
    elif bs != EXPECTED_ARTIFACT_SHA256:
        errors.append(f"{filename}: security_assertions.binary_sha256 nao confere")
    if sa.get("materialized_file_count") != 1:
        errors.append(f"{filename}: security_assertions.materialized_file_count deve ser 1")
    for k in ("no_execution_performed", "no_static_inspection_performed",
              "no_dynamic_analysis_performed", "no_sandbox_created",
              "no_client_integration", "no_distribution", "no_vps_access",
              "no_clone_or_archive", "no_release_asset", "no_mirror_or_third_party",
              "no_external_service_upload", "temporary_file_removed",
              "temporary_dir_removed"):
        if sa.get(k) is not True:
            errors.append(f"{filename}: security_assertions.{k} deve ser true")
    for k in ("binary_versioned", "raw_responses_versioned", "gate_3_authorized"):
        if sa.get(k) is not False:
            errors.append(f"{filename}: security_assertions.{k} deve ser false")

    if not ev.get("limitations"):
        errors.append(f"{filename}: limitations obrigatorias ausentes")

    # Referencias relativas e existentes.
    for field in ("authorization_ref", "plan_ref", "gate_0_evidence_ref",
                  "gate_1_decision_ref"):
        ref = ev.get(field)
        _ref_ok(ref.get("path") if isinstance(ref, dict) else None, field, filename, errors)
    _check_integration_ref(ev.get("integration_ref"), filename, errors)

    # Cross-check: decisao do GATE 2 autoriza (gate_2_authorized=true).
    if isinstance(gate2_decision, dict):
        a2 = gate2_decision.get("authorizations", {})
        if gate2_decision.get("decision") != "AUTHORIZE_GATE_2" or a2.get("gate_2_authorized") is not True:
            errors.append(f"{filename}: decisao do GATE 2 nao autoriza a execucao")
        if a2.get("gate_3_authorized") is not False:
            errors.append(f"{filename}: decisao do GATE 2 nao pode autorizar o GATE 3")
    else:
        errors.append(f"{filename}: decisao do GATE 2 ausente/invalida")
    return errors


def validate_gate2(errors):
    """Orquestra a validacao dos artefatos do GATE 2 (decisao + evidencia)."""
    if not os.path.isdir(DECISIONS_DIR):
        return
    plan = {}
    try:
        plan = load_json(os.path.join(AUDIT_DIR, PLAN_TEMPLATE))
    except Fail:
        plan = {}
    gate1_decision = {}
    try:
        gate1_decision = load_json(os.path.join(DECISIONS_DIR, GATE1_DECISION_RECORD))
    except Fail:
        gate1_decision = {}
    gate0_evidence = {}
    if os.path.isdir(EVIDENCE_DIR):
        g0 = sorted(f for f in os.listdir(EVIDENCE_DIR)
                    if f.startswith(GATE0_EVIDENCE_PREFIX) and f.endswith(".json"))
        if g0:
            try:
                gate0_evidence = load_json(os.path.join(EVIDENCE_DIR, g0[-1]))
            except Fail:
                gate0_evidence = {}

    # Decisao do GATE 2.
    dec_names = sorted(f for f in os.listdir(DECISIONS_DIR)
                       if f.startswith(GATE2_DECISION_PREFIX) and f.endswith(".json"))
    gate2_decision = {}
    if dec_names:
        try:
            dschema = load_json(os.path.join(SCHEMA_DIR, GATE2_DECISION_SCHEMA))
        except Fail as exc:
            errors.append(str(exc))
            dschema = None
        for name in dec_names:
            derr = []
            try:
                rec = load_json(os.path.join(DECISIONS_DIR, name))
                gate2_decision = rec
                if dschema is not None:
                    validate_gate2_decision(rec, dschema, plan, gate1_decision,
                                            gate0_evidence, name, derr)
            except Fail as exc:
                derr.append(str(exc))
            if derr:
                errors.extend(derr)
                print(f"[FALHA] decisions/{name}: {len(derr)} problema(s)")
                for e in derr:
                    print(f"    - {e}")
            else:
                print(f"[OK]    decisions/{name}")

    # Evidencia do GATE 2.
    if os.path.isdir(EVIDENCE_DIR):
        ev_names = sorted(f for f in os.listdir(EVIDENCE_DIR)
                          if f.startswith(GATE2_EVIDENCE_PREFIX) and f.endswith(".json"))
        if ev_names:
            try:
                eschema = load_json(os.path.join(SCHEMA_DIR, GATE2_EVIDENCE_SCHEMA))
            except Fail as exc:
                errors.append(str(exc))
                eschema = None
            for name in ev_names:
                everr = []
                try:
                    ev = load_json(os.path.join(EVIDENCE_DIR, name))
                    if eschema is not None:
                        validate_gate2_evidence(ev, eschema, gate2_decision,
                                                gate1_decision, gate0_evidence, name, everr)
                except Fail as exc:
                    everr.append(str(exc))
                if everr:
                    errors.extend(everr)
                    print(f"[FALHA] evidence/{name}: {len(everr)} problema(s)")
                    for e in everr:
                        print(f"    - {e}")
                else:
                    print(f"[OK]    evidence/{name}")


def validate_gate3_decision(record, schema, plan, gate2_decision, gate2_evidence,
                            filename, errors):
    """Valida o registro REAL da autorizacao humana do GATE 3 (importavel).

    Exige, alem do schema: decisao AUTHORIZE_GATE_3; escopo fechado ao blob fixado
    canonico; SOMENTE os grants do GATE 3 (materializacao temporaria, hashing local,
    inspecao de identidade do PE e de Authenticode) em true; gate_4_authorized e todas
    as demais flags operacionais em false; pre-condicao GATE 2 = COMPLETED_PASS; e
    cross-checks com o plano, a decisao e a evidencia do GATE 2 e com o squash do PR #50.
    """
    kv = []
    schema_keyword_violations(schema, "gate-03-decision.schema", kv)
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
    if not isinstance(g, dict) or g.get("id") != 3 or g.get("name") != "IDENTITY_AND_SIGNATURE":
        errors.append(f"{filename}: gate deve ser id=3 name=IDENTITY_AND_SIGNATURE")
    if record.get("decision") != "AUTHORIZE_GATE_3":
        errors.append(f"{filename}: decision deve ser AUTHORIZE_GATE_3")
    if record.get("execution_state") != "AUTHORIZED_NOT_STARTED":
        errors.append(f"{filename}: execution_state deve ser AUTHORIZED_NOT_STARTED")

    for field in ("decider", "role", "authority", "channel"):
        val = record.get(field)
        if not isinstance(val, str) or not val.strip():
            errors.append(f"{filename}: campo '{field}' vazio")
        elif PLACEHOLDER_RE.search(val):
            errors.append(f"{filename}: campo '{field}' parece placeholder (categoria: placeholder)")
    if not valid_iso_date(record.get("date")):
        errors.append(f"{filename}: campo 'date' nao e uma data ISO valida")

    conds = record.get("conditions")
    if not isinstance(conds, list) or len(conds) < 20:
        errors.append(f"{filename}: 'conditions' deve ter ao menos 20 itens")
        conds = conds if isinstance(conds, list) else []
    ns = [c.get("n") for c in conds if isinstance(c, dict)]
    if ns != list(range(1, len(conds) + 1)):
        errors.append(f"{filename}: conditions devem ser numeradas 1..N em ordem, sem lacuna/repeticao")

    auth = record.get("authorizations")
    if not isinstance(auth, dict):
        errors.append(f"{filename}: 'authorizations' ausente")
    else:
        for k, v in auth.items():
            if k in GATE3_DECISION_TRUE_FLAGS:
                if v is not True:
                    errors.append(f"{filename}: authorizations.{k} deve ser true")
            elif v is not False:
                errors.append(f"{filename}: authorizations.{k} deve ser false (grants do GATE 3 sao limitados)")
        if auth.get("gate_3_authorized") is not True:
            errors.append(f"{filename}: authorizations.gate_3_authorized deve ser true (grant do GATE 3)")
        for k in GATE3_CRITICAL_FALSE:
            if auth.get(k) is not False:
                errors.append(f"{filename}: authorizations.{k} deve ser false (sem autorizacao transitiva)")

    _check_materialization_scope(record.get("materialization_scope"), filename, errors)

    ir = record.get("integration_ref")
    if not isinstance(ir, dict):
        errors.append(f"{filename}: 'integration_ref' ausente")
    else:
        if ir.get("pr") != 50:
            errors.append(f"{filename}: integration_ref.pr deve ser 50")
        if ir.get("squash_commit") != EXPECTED_PR50_SQUASH:
            errors.append(f"{filename}: integration_ref.squash_commit deve ser o squash do PR #50")
        if ir.get("base_branch") != "dev":
            errors.append(f"{filename}: integration_ref.base_branch deve ser dev")

    pc = record.get("precondition")
    if not isinstance(pc, dict):
        errors.append(f"{filename}: 'precondition' ausente")
    else:
        if pc.get("gate_2_completed") is not True:
            errors.append(f"{filename}: precondition.gate_2_completed deve ser true")
        if pc.get("gate_2_outcome") != "COMPLETED_PASS":
            errors.append(f"{filename}: precondition.gate_2_outcome deve ser COMPLETED_PASS")

    for field in ("plan_ref", "source_decision_ref", "prior_gate_decision_ref",
                  "gate_2_evidence_ref"):
        ref = record.get(field)
        _ref_ok(ref.get("path") if isinstance(ref, dict) else None, field, filename, errors)

    if isinstance(plan, dict):
        plan_gate_ids = [x.get("gate_id") for x in plan.get("gates", []) if isinstance(x, dict)]
        if 3 not in plan_gate_ids:
            errors.append(f"{filename}: plano nao contem GATE 3 correspondente")
    if isinstance(gate2_decision, dict):
        a2 = gate2_decision.get("authorizations", {})
        if gate2_decision.get("decision") != "AUTHORIZE_GATE_2" or a2.get("gate_2_authorized") is not True:
            errors.append(f"{filename}: GATE 2 referenciado nao autoriza materializacao")
    else:
        errors.append(f"{filename}: decisao do GATE 2 ausente/invalida")
    if isinstance(gate2_evidence, dict):
        if gate2_evidence.get("outcome") != "COMPLETED_PASS":
            errors.append(f"{filename}: evidencia do GATE 2 nao esta COMPLETED_PASS")
    else:
        errors.append(f"{filename}: evidencia do GATE 2 ausente/invalida")
    return errors


def _magic_str_to_int(magic_str):
    """Converte '0x010b' -> 267; retorna None se nao parseavel."""
    if isinstance(magic_str, str):
        try:
            return int(magic_str, 16)
        except ValueError:
            return None
    return None


def validate_gate3_evidence(ev, schema, gate3_decision, gate2_evidence,
                            filename, errors):
    """Valida a evidencia REAL do GATE 3 apos a revisao corretiva 2P-E-C3-R1.

    O COMPLETED_PASS original foi SUSPENSO. A evidencia agora esta em
    EVIDENCE_INVALIDATED_PENDING_REPEAT e deve: (a) corrigir a semantica de leitura
    estatica (sem 'opened' ambiguo; file_read_for_static_inspection=true e
    launched/executed/loaded_as_executable=false); (b) marcar
    size_of_optional_header como MEASUREMENT_REQUIRES_RECONFIRMATION quando coincide
    com o magic (D2) e nunca aceitar um valor confirmado igual ao magic; (c) referenciar
    o inspetor PE versionado (nao executado sobre o WARP.exe); (d) distinguir
    ferramenta disponivel de invocada, com exit_code=null quando invoked=false;
    (e) preservar os fatos do GATE 2; e (f) manter gate_4_authorized=false e nenhuma
    nova materializacao/execucao.
    """
    kv = []
    schema_keyword_violations(schema, "gate-03-evidence.schema", kv)
    errors.extend(kv)
    validate_node(ev, schema, filename, errors)
    security_scan(ev, errors)
    _content_scan_allow_hashes(ev, filename, errors)

    if not isinstance(ev, dict):
        errors.append(f"{filename}: evidencia nao e objeto")
        return errors

    if ev.get("status") != ev.get("outcome"):
        errors.append(f"{filename}: status deve ser igual a outcome")
    if ev.get("outcome") != "EVIDENCE_INVALIDATED_PENDING_REPEAT":
        errors.append(f"{filename}: outcome deve ser EVIDENCE_INVALIDATED_PENDING_REPEAT (COMPLETED_PASS suspenso)")
    g = ev.get("gate")
    if not isinstance(g, dict) or g.get("id") != 3 or g.get("name") != "IDENTITY_AND_SIGNATURE":
        errors.append(f"{filename}: gate deve ser id=3 name=IDENTITY_AND_SIGNATURE")

    # Execucao ORIGINAL (superseded): tempos reais ordenados; sem nova execucao.
    ox = ev.get("original_execution") or {}
    if ox.get("gate_3_started") is not True or ox.get("gate_3_completed") is not True:
        errors.append(f"{filename}: original_execution deve ter gate_3_started/completed true")
    if ox.get("execution_state") != "COMPLETED":
        errors.append(f"{filename}: original_execution.execution_state deve ser COMPLETED")
    st, ft, cl = ox.get("started_at"), ox.get("finished_at"), ox.get("cleanup_at")
    if isinstance(st, str) and isinstance(ft, str) and st > ft:
        errors.append(f"{filename}: started_at posterior a finished_at")
    if isinstance(ft, str) and isinstance(cl, str) and ft > cl:
        errors.append(f"{filename}: finished_at posterior a cleanup_at")
    if ox.get("method") != "GITHUB_OFFICIAL_GIT_DATA_API_BLOB_BY_OID":
        errors.append(f"{filename}: original_execution.method fora do conjunto autorizado")
    if ox.get("network_scope") != "GITHUB_OFFICIAL_ONLY":
        errors.append(f"{filename}: original_execution.network_scope deve ser GITHUB_OFFICIAL_ONLY")
    if ox.get("superseded_by_corrective_review") is not True:
        errors.append(f"{filename}: original_execution deve marcar superseded_by_corrective_review=true")

    # Revisao corretiva: sem nova materializacao/execucao; D1-D4 registrados.
    cr = ev.get("corrective_review") or {}
    if cr.get("stage") != "2P-E-C3-R1":
        errors.append(f"{filename}: corrective_review.stage deve ser 2P-E-C3-R1")
    for k in ("new_materialization_performed", "new_execution_performed",
              "reused_prior_timestamps_as_new_run"):
        if cr.get(k) is not False:
            errors.append(f"{filename}: corrective_review.{k} deve ser false")
    cr_findings = cr.get("findings")
    if not isinstance(cr_findings, list) or len(cr_findings) < 4:
        errors.append(f"{filename}: corrective_review.findings deve registrar ao menos D1-D4")
        cr_findings = cr_findings if isinstance(cr_findings, list) else []
    ids = {f.get("id") for f in cr_findings if isinstance(f, dict)}
    for req in ("D1", "D2", "D3", "D4"):
        if req not in ids:
            errors.append(f"{filename}: corrective_review.findings deve conter {req}")

    # Identificadores esperados == canonicos.
    up = ev.get("upstream_expected") or {}
    for k, exp in (("repository_full_name", EXPECTED_REPOSITORY),
                   ("commit_oid", EXPECTED_PINNED_COMMIT),
                   ("tree_oid", EXPECTED_TREE_OID),
                   ("artifact_path", EXPECTED_ARTIFACT_PATH),
                   ("artifact_blob_oid", EXPECTED_ARTIFACT_BLOB),
                   ("artifact_blob_size", EXPECTED_ARTIFACT_SIZE)):
        if up.get(k) != exp:
            errors.append(f"{filename}: upstream_expected.{k} deve ser {exp!r}")

    # Reconfirmacao de identidade (fatos do GATE 2 preservados) + D1 (leitura estatica).
    ir = ev.get("identity_reconfirmation") or {}
    if ir.get("materialized_file_count") != 1:
        errors.append(f"{filename}: identity_reconfirmation.materialized_file_count deve ser 1")
    if ir.get("temporary_dir_outside_repo") is not True:
        errors.append(f"{filename}: temporary_dir_outside_repo deve ser true")
    # D1: leitura estatica explicita; SEM 'opened' ambiguo.
    if "opened" in ir:
        errors.append(f"{filename}: campo ambiguo 'opened' nao pode existir (use file_read_for_static_inspection)")
    if ir.get("file_read_for_static_inspection") is not True:
        errors.append(f"{filename}: file_read_for_static_inspection deve ser true (o conteudo foi lido)")
    for k in ("launched", "executed", "loaded_as_executable"):
        if ir.get(k) is not False:
            errors.append(f"{filename}: identity_reconfirmation.{k} deve ser false")
    if ir.get("size_bytes_observed") != EXPECTED_ARTIFACT_SIZE or ir.get("size_match") is not True:
        errors.append(f"{filename}: tamanho reconfirmado deve ser {EXPECTED_ARTIFACT_SIZE} e size_match=true")
    if ir.get("git_blob_oid_algorithm") != "GIT_OBJECT_ID":
        errors.append(f"{filename}: git_blob_oid_algorithm deve ser GIT_OBJECT_ID")
    for k in ("git_blob_oid_expected", "git_blob_oid_git_hash_object", "git_blob_oid_independent"):
        if ir.get(k) != EXPECTED_ARTIFACT_BLOB:
            errors.append(f"{filename}: identity_reconfirmation.{k} deve ser {EXPECTED_ARTIFACT_BLOB}")
    if ir.get("git_blob_oid_match") is not True:
        errors.append(f"{filename}: git_blob_oid_match deve ser true")
    sha = ir.get("sha256_local")
    if not isinstance(sha, str) or not HEX64_RE.match(sha):
        errors.append(f"{filename}: sha256_local deve ter 64 caracteres hex")
    elif sha != EXPECTED_ARTIFACT_SHA256:
        errors.append(f"{filename}: sha256_local nao confere com o conteudo do blob fixado (GATE 2)")
    if ir.get("sha256_expected") != EXPECTED_ARTIFACT_SHA256:
        errors.append(f"{filename}: sha256_expected deve ser o SHA-256 do GATE 2")
    if ir.get("sha256_match") is not True:
        errors.append(f"{filename}: sha256_match deve ser true")
    if isinstance(sha, str) and (sha == EXPECTED_ARTIFACT_BLOB or HEX40_RE.match(sha)):
        errors.append(f"{filename}: SHA-256 nao pode ser igual ao Git object ID nem ter 40 hex")
    if ir.get("sha256_is_not_git_oid") is not True:
        errors.append(f"{filename}: sha256_is_not_git_oid deve ser true")
    if ir.get("identity_matches_gate_2") is not True:
        errors.append(f"{filename}: identity_matches_gate_2 deve ser true")

    # Identidade PE OBSERVADA (parser nao versionado): pendente de reconfirmacao.
    pe = ev.get("pe_identity_observed") or {}
    if pe.get("produced_by") != "UNVERSIONED_SCRATCHPAD_PARSER":
        errors.append(f"{filename}: pe_identity_observed.produced_by deve ser UNVERSIONED_SCRATCHPAD_PARSER")
    if pe.get("reconfirmation_required") is not True:
        errors.append(f"{filename}: pe_identity_observed.reconfirmation_required deve ser true")
    # D2: pe_valid nao pode ser afirmado como true; deve ser um status pendente.
    if pe.get("pe_valid_status") != "PENDING_RECONFIRMATION":
        errors.append(f"{filename}: pe_valid_status deve ser PENDING_RECONFIRMATION (nao aceitar pe_valid=true por afirmacao)")
    if "pe_valid" in pe:
        errors.append(f"{filename}: pe_identity_observed nao pode afirmar 'pe_valid' (use pe_valid_status)")
    if pe.get("size_of_optional_header_status") != "MEASUREMENT_REQUIRES_RECONFIRMATION":
        errors.append(f"{filename}: size_of_optional_header_status deve ser MEASUREMENT_REQUIRES_RECONFIRMATION")
    # D2 (dependente da PROVENIENCIA — 2P-E-C3-R2): isto NAO e uma regra geral de que
    # "size_of_optional_header == magic" e invalido. E especifica da evidencia HISTORICA
    # produzida pelo parser NAO versionado (produced_by=UNVERSIONED_SCRATCHPAD_PARSER),
    # cuja causa-raiz foi o offset incorreto: naquele contexto, o valor 267 (== magic PE32)
    # exige status MEASUREMENT_REQUIRES_RECONFIRMATION. Uma futura evidencia do parser
    # revisado pode registrar valores iguais se os bytes reais assim determinarem (validada
    # por validate_gate3_corrective_repeat_evidence, sem esta regra).
    soh = pe.get("size_of_optional_header_observed")
    magic_int = _magic_str_to_int(pe.get("optional_header_magic_observed"))
    if pe.get("produced_by") == "UNVERSIONED_SCRATCHPAD_PARSER":
        if isinstance(soh, int) and magic_int is not None and soh == magic_int:
            if pe.get("size_of_optional_header_status") != "MEASUREMENT_REQUIRES_RECONFIRMATION":
                errors.append(f"{filename}: size_of_optional_header ({soh}) == magic ({magic_int}) "
                              f"no parser nao versionado exige MEASUREMENT_REQUIRES_RECONFIRMATION")
    if pe.get("version_info_status") != "NOT_DETERMINED_BY_REVIEWED_PARSER":
        errors.append(f"{filename}: version_info_status deve ser NOT_DETERMINED_BY_REVIEWED_PARSER")
    if pe.get("original_filename_status") != "NOT_DETERMINED_BY_REVIEWED_PARSER":
        errors.append(f"{filename}: original_filename_status deve ser NOT_DETERMINED_BY_REVIEWED_PARSER")
    if "original_filename" in pe:
        errors.append(f"{filename}: nao preservar OriginalFilename como fato (use original_filename_status)")

    # Assinatura Authenticode OBSERVADA: pendente de reconfirmacao.
    au = ev.get("authenticode_observed") or {}
    if au.get("produced_by") != "UNVERSIONED_SCRATCHPAD_PARSER":
        errors.append(f"{filename}: authenticode_observed.produced_by deve ser UNVERSIONED_SCRATCHPAD_PARSER")
    if au.get("reconfirmation_required") is not True:
        errors.append(f"{filename}: authenticode_observed.reconfirmation_required deve ser true")
    if au.get("determination_status") != "PENDING_RECONFIRMATION":
        errors.append(f"{filename}: authenticode_observed.determination_status deve ser PENDING_RECONFIRMATION")
    if au.get("cryptographic_verification") not in GATE3_CRYPTO_VERIF_STATES:
        errors.append(f"{filename}: cryptographic_verification fora do conjunto fechado")
    if au.get("chain_trust_state") not in GATE3_CHAIN_TRUST_STATES:
        errors.append(f"{filename}: chain_trust_state fora do conjunto fechado")

    # Semantica de assinatura: separacao presenca/validade/confianca/seguranca.
    ss = ev.get("signature_semantics") or {}
    for k in ("signature_present_means_present_only", "presence_not_equal_valid",
              "valid_not_equal_trusted", "trusted_not_equal_current_certificate",
              "timestamp_not_trusted", "not_equal_file_safe", "absence_not_equal_malware"):
        if ss.get(k) is not True:
            errors.append(f"{filename}: signature_semantics.{k} deve ser true")

    # Inspetor PE revisavel: versionado, offline, NAO executado sobre o WARP.exe.
    rp = ev.get("reviewed_parser") or {}
    if rp.get("stdlib_only") is not True or rp.get("network_access") is not False:
        errors.append(f"{filename}: reviewed_parser deve ser stdlib_only e sem rede")
    if rp.get("executes_or_loads_pe") is not False:
        errors.append(f"{filename}: reviewed_parser.executes_or_loads_pe deve ser false")
    if rp.get("run_on_warp_exe") is not False:
        errors.append(f"{filename}: reviewed_parser.run_on_warp_exe deve ser false (nova materializacao nao autorizada)")

    # D4: ferramenta disponivel x invocada; exit_code=null quando invoked=false.
    tools = ev.get("tools")
    if not isinstance(tools, list) or not tools:
        errors.append(f"{filename}: 'tools' deve registrar ao menos uma ferramenta")
    else:
        for i, t in enumerate(tools):
            if not isinstance(t, dict):
                continue
            invoked = t.get("invoked")
            completed = t.get("completed")
            ec = t.get("exit_code")
            if invoked is False:
                if ec is not None:
                    errors.append(f"{filename}: tools[{i}] invoked=false exige exit_code=null")
                if completed is not False:
                    errors.append(f"{filename}: tools[{i}] invoked=false exige completed=false")
            elif invoked is True:
                if not isinstance(ec, int):
                    errors.append(f"{filename}: tools[{i}] invoked=true exige exit_code inteiro")
            else:
                errors.append(f"{filename}: tools[{i}].invoked deve ser booleano")

    # Invariantes de seguranca (inclui: sem nova materializacao/execucao).
    sa = ev.get("security_assertions") or {}
    for k in ("blob_content_accessed", "binary_materialized",
              "static_identity_inspection_performed", "authenticode_inspection_performed",
              "no_new_materialization_performed", "no_new_execution_performed",
              "no_execution_performed", "no_dynamic_analysis_performed",
              "no_sandbox_created", "no_wine_or_vm_load", "no_network_after_fetch",
              "no_external_service_upload", "no_additional_file_materialized",
              "no_gate4_inspection_performed", "no_client_access", "no_ragexe_access",
              "no_patch_selected_or_applied", "no_clientinfo_modified", "no_vps_access",
              "temporary_file_removed", "temporary_dir_removed"):
        if sa.get(k) is not True:
            errors.append(f"{filename}: security_assertions.{k} deve ser true")
    for k in ("binary_versioned", "raw_signature_versioned", "gate_4_authorized"):
        if sa.get(k) is not False:
            errors.append(f"{filename}: security_assertions.{k} deve ser false")

    # Fatos preservados do GATE 2.
    pf = ev.get("preserved_gate_2_facts") or {}
    if pf.get("artifact_blob_oid") != EXPECTED_ARTIFACT_BLOB:
        errors.append(f"{filename}: preserved_gate_2_facts.artifact_blob_oid deve ser {EXPECTED_ARTIFACT_BLOB}")
    if pf.get("artifact_blob_size") != EXPECTED_ARTIFACT_SIZE:
        errors.append(f"{filename}: preserved_gate_2_facts.artifact_blob_size deve ser {EXPECTED_ARTIFACT_SIZE}")
    if pf.get("artifact_sha256") != EXPECTED_ARTIFACT_SHA256:
        errors.append(f"{filename}: preserved_gate_2_facts.artifact_sha256 deve ser o SHA-256 do GATE 2")
    for k in ("prior_materialization_performed", "prior_cleanup_performed",
              "no_execution", "binary_not_versioned"):
        if pf.get(k) is not True:
            errors.append(f"{filename}: preserved_gate_2_facts.{k} deve ser true")

    if not ev.get("pending_reconfirmation"):
        errors.append(f"{filename}: pending_reconfirmation obrigatorio ausente")
    if not ev.get("findings"):
        errors.append(f"{filename}: findings obrigatorios ausentes")
    if not ev.get("limitations") or len(ev.get("limitations")) < 4:
        errors.append(f"{filename}: limitations obrigatorias (>=4) ausentes")

    for field in ("authorization_ref", "plan_ref", "gate_2_decision_ref",
                  "gate_2_evidence_ref", "reviewed_parser_ref", "reviewed_parser_test_ref"):
        ref = ev.get(field)
        _ref_ok(ref.get("path") if isinstance(ref, dict) else None, field, filename, errors)
    ir2 = ev.get("integration_ref")
    if not isinstance(ir2, dict) or ir2.get("pr") != 50 or ir2.get("squash_commit") != EXPECTED_PR50_SQUASH or ir2.get("base_branch") != "dev":
        errors.append(f"{filename}: integration_ref deve referenciar o squash do PR #50 em dev")

    # Cross-check: decisao do GATE 3 autoriza (gate_3_authorized=true) e nao o GATE 4.
    if isinstance(gate3_decision, dict):
        a3 = gate3_decision.get("authorizations", {})
        if gate3_decision.get("decision") != "AUTHORIZE_GATE_3" or a3.get("gate_3_authorized") is not True:
            errors.append(f"{filename}: decisao do GATE 3 nao autoriza a execucao")
        if a3.get("gate_4_authorized") is not False:
            errors.append(f"{filename}: decisao do GATE 3 nao pode autorizar o GATE 4")
    else:
        errors.append(f"{filename}: decisao do GATE 3 ausente/invalida")
    # Cross-check: evidencia do GATE 2 esta COMPLETED_PASS (identidade base preservada).
    if isinstance(gate2_evidence, dict):
        if gate2_evidence.get("outcome") != "COMPLETED_PASS":
            errors.append(f"{filename}: evidencia do GATE 2 nao esta COMPLETED_PASS")
        it2 = gate2_evidence.get("integrity") or {}
        if it2.get("sha256_local") and it2.get("sha256_local") != ir.get("sha256_local"):
            errors.append(f"{filename}: SHA-256 do GATE 3 diverge do SHA-256 registrado no GATE 2")
    else:
        errors.append(f"{filename}: evidencia do GATE 2 ausente/invalida")
    return errors


def validate_gate3(errors):
    """Orquestra a validacao dos artefatos do GATE 3 (decisao + evidencia)."""
    if not os.path.isdir(DECISIONS_DIR):
        return
    plan = {}
    try:
        plan = load_json(os.path.join(AUDIT_DIR, PLAN_TEMPLATE))
    except Fail:
        plan = {}
    gate2_decision = {}
    try:
        gate2_decision = load_json(os.path.join(DECISIONS_DIR, GATE2_DECISION_RECORD))
    except Fail:
        gate2_decision = {}
    gate2_evidence = {}
    if os.path.isdir(EVIDENCE_DIR):
        try:
            gate2_evidence = load_json(os.path.join(EVIDENCE_DIR, GATE2_EVIDENCE_RECORD))
        except Fail:
            gate2_evidence = {}

    # Decisao do GATE 3.
    dec_names = sorted(f for f in os.listdir(DECISIONS_DIR)
                       if f.startswith(GATE3_DECISION_PREFIX) and f.endswith(".json"))
    gate3_decision = {}
    if dec_names:
        try:
            dschema = load_json(os.path.join(SCHEMA_DIR, GATE3_DECISION_SCHEMA))
        except Fail as exc:
            errors.append(str(exc))
            dschema = None
        for name in dec_names:
            derr = []
            try:
                rec = load_json(os.path.join(DECISIONS_DIR, name))
                gate3_decision = rec
                if dschema is not None:
                    validate_gate3_decision(rec, dschema, plan, gate2_decision,
                                            gate2_evidence, name, derr)
            except Fail as exc:
                derr.append(str(exc))
            if derr:
                errors.extend(derr)
                print(f"[FALHA] decisions/{name}: {len(derr)} problema(s)")
                for e in derr:
                    print(f"    - {e}")
            else:
                print(f"[OK]    decisions/{name}")

    # Evidencia do GATE 3.
    if os.path.isdir(EVIDENCE_DIR):
        ev_names = sorted(f for f in os.listdir(EVIDENCE_DIR)
                          if f.startswith(GATE3_EVIDENCE_PREFIX) and f.endswith(".json"))
        if ev_names:
            try:
                eschema = load_json(os.path.join(SCHEMA_DIR, GATE3_EVIDENCE_SCHEMA))
            except Fail as exc:
                errors.append(str(exc))
                eschema = None
            for name in ev_names:
                everr = []
                try:
                    ev = load_json(os.path.join(EVIDENCE_DIR, name))
                    if eschema is not None:
                        validate_gate3_evidence(ev, eschema, gate3_decision,
                                                gate2_evidence, name, everr)
                except Fail as exc:
                    everr.append(str(exc))
                if everr:
                    errors.extend(everr)
                    print(f"[FALHA] evidence/{name}: {len(everr)} problema(s)")
                    for e in everr:
                        print(f"    - {e}")
                else:
                    print(f"[OK]    evidence/{name}")


def validate_gate3_repeat_decision(record, schema, filename, errors):
    """Valida a FUTURA decisao humana da repeticao corretiva do GATE 3 (importavel).

    Exige: decisao AUTHORIZE_CORRECTIVE_REPEAT_GATE_3; escopo fechado ao blob fixado;
    EXATAMENTE uma repeticao (segunda nao autorizada); referencias A decisao original,
    A evidencia invalidada, A revisao R1, ao parser revisado, aos seus testes e aos Git
    blob OIDs; gate_4_authorized=false e nenhuma autorizacao transitiva.
    """
    kv = []
    schema_keyword_violations(schema, "gate-03-repeat-decision.schema", kv)
    errors.extend(kv)
    validate_node(record, schema, filename, errors)
    security_scan(record, errors)
    planning_content_scan(record, filename, errors)

    if not isinstance(record, dict):
        errors.append(f"{filename}: registro nao e objeto")
        return errors

    if record.get("decision") != "AUTHORIZE_CORRECTIVE_REPEAT_GATE_3":
        errors.append(f"{filename}: decision deve ser AUTHORIZE_CORRECTIVE_REPEAT_GATE_3")
    if record.get("execution_state") != "AUTHORIZED_NOT_STARTED":
        errors.append(f"{filename}: execution_state deve ser AUTHORIZED_NOT_STARTED")

    for field in ("decider", "role", "authority", "channel"):
        val = record.get(field)
        if not isinstance(val, str) or not val.strip():
            errors.append(f"{filename}: campo '{field}' vazio")
        elif PLACEHOLDER_RE.search(val):
            errors.append(f"{filename}: campo '{field}' parece placeholder (categoria: placeholder)")
    if not valid_iso_date(record.get("date")):
        errors.append(f"{filename}: campo 'date' nao e uma data ISO valida")

    rs = record.get("repeat_scope") or {}
    if rs.get("exactly_one_repeat") is not True or rs.get("repeat_index") != 1:
        errors.append(f"{filename}: repeat_scope deve ser exactly_one_repeat=true, repeat_index=1")

    auth = record.get("authorizations") or {}
    if auth.get("gate_3_corrective_repeat_authorized") is not True:
        errors.append(f"{filename}: gate_3_corrective_repeat_authorized deve ser true")
    for k in ("gate_4_authorized", "execution_authorized", "dynamic_analysis_authorized",
              "external_reputation_upload_authorized", "network_validation_authorized",
              "sandbox_creation_authorized", "client_copy_provision_authorized",
              "client_modification_authorized", "patch_review_authorized",
              "patch_application_authorized", "client_preparation_authorized",
              "test_account_authorized", "first_login_authorized", "vps_access_authorized",
              "distribution_authorized", "second_repeat_authorized"):
        if auth.get(k) is not False:
            errors.append(f"{filename}: authorizations.{k} deve ser false (sem autorizacao transitiva)")

    _check_materialization_scope(record.get("materialization_scope"), filename, errors)

    # Referencias exigidas devem existir no repositorio.
    for field in ("original_decision_ref", "original_invalidated_evidence_ref",
                  "r1_review_ref", "reviewed_parser_ref", "reviewed_parser_test_ref"):
        ref = record.get(field)
        _ref_ok(ref.get("path") if isinstance(ref, dict) else None, field, filename, errors)
    # A evidencia original referenciada deve ser a historica invalidada.
    oi = record.get("original_invalidated_evidence_ref") or {}
    if isinstance(oi, dict) and oi.get("path") and not oi["path"].endswith(GATE3_HISTORICAL_INVALIDATED_EVIDENCE):
        errors.append(f"{filename}: original_invalidated_evidence_ref deve apontar para a evidencia invalidada do GATE 3")
    # Referencias ao commit/blobs do parser (40 hex).
    for field in ("reviewed_parser_commit", "reviewed_parser_git_blob_oid",
                  "reviewed_parser_test_git_blob_oid"):
        v = record.get(field)
        if not isinstance(v, str) or not HEX40_RE.match(v):
            errors.append(f"{filename}: {field} deve ser Git object ID de 40 hex")
    return errors


def validate_gate3_repeat_evidence(ev, schema, repeat_decision, filename, errors):
    """Valida a FUTURA evidencia da repeticao corretiva do GATE 3 (importavel).

    Exige: produzida pelo parser REVISADO/VERSIONADO; referencia A evidencia invalidada
    (que permanece historica), A decisao da repeticao e ao parser; Git blob OID do parser
    igual ao da decisao (proveniencia); identidade IGUAL ao GATE 2; gate_4_authorized=false;
    e sem execucao/carga do binario.
    """
    kv = []
    schema_keyword_violations(schema, "gate-03-repeat-evidence.schema", kv)
    errors.extend(kv)
    validate_node(ev, schema, filename, errors)
    security_scan(ev, errors)
    _content_scan_allow_hashes(ev, filename, errors)

    if not isinstance(ev, dict):
        errors.append(f"{filename}: evidencia nao e objeto")
        return errors

    if ev.get("status") != ev.get("outcome"):
        errors.append(f"{filename}: status deve ser igual a outcome")
    if ev.get("outcome") not in ("COMPLETED_PASS", "COMPLETED_FAIL", "STOPPED"):
        errors.append(f"{filename}: outcome fora do conjunto permitido")

    pe = ev.get("pe_identity") or {}
    if pe.get("produced_by") != "REVIEWED_VERSIONED_PARSER":
        errors.append(f"{filename}: pe_identity.produced_by deve ser REVIEWED_VERSIONED_PARSER")

    rp = ev.get("reviewed_parser") or {}
    if rp.get("run_on_warp_exe") is not True:
        errors.append(f"{filename}: reviewed_parser.run_on_warp_exe deve ser true (repeticao usa o parser revisado)")
    if rp.get("executes_or_loads_pe") is not False:
        errors.append(f"{filename}: reviewed_parser.executes_or_loads_pe deve ser false")

    sa = ev.get("security_assertions") or {}
    if sa.get("gate_4_authorized") is not False:
        errors.append(f"{filename}: security_assertions.gate_4_authorized deve ser false")
    for k in ("no_execution_performed", "no_gate4_inspection_performed", "no_ragexe_access",
              "no_vps_access", "temporary_file_removed"):
        if sa.get(k) is not True:
            errors.append(f"{filename}: security_assertions.{k} deve ser true")

    ir = ev.get("identity_reconfirmation") or {}
    if ir.get("sha256_local") != EXPECTED_ARTIFACT_SHA256 or ir.get("identity_matches_gate_2") is not True:
        errors.append(f"{filename}: identidade da repeticao deve corresponder ao GATE 2")
    if ir.get("executed") is not False or ir.get("loaded_as_executable") is not False:
        errors.append(f"{filename}: identity_reconfirmation executado/carregado devem ser false")

    # Proveniencia: Git blob OID do parser deve coincidir com o da decisao (parser exato).
    ev_oid = ev.get("reviewed_parser_git_blob_oid")
    if not isinstance(ev_oid, str) or not HEX40_RE.match(ev_oid):
        errors.append(f"{filename}: reviewed_parser_git_blob_oid deve ser 40 hex")
    if isinstance(repeat_decision, dict):
        if repeat_decision.get("decision") != "AUTHORIZE_CORRECTIVE_REPEAT_GATE_3":
            errors.append(f"{filename}: repeticao sem decisao AUTHORIZE_CORRECTIVE_REPEAT_GATE_3")
        dec_oid = repeat_decision.get("reviewed_parser_git_blob_oid")
        if isinstance(ev_oid, str) and dec_oid is not None and ev_oid != dec_oid:
            errors.append(f"{filename}: Git blob OID do parser diverge do registrado na decisao da repeticao")
    else:
        errors.append(f"{filename}: decisao da repeticao ausente/invalida")

    # Referencias exigidas.
    for field in ("original_invalidated_evidence_ref", "corrective_repeat_decision_ref",
                  "reviewed_parser_ref", "reviewed_parser_test_ref"):
        ref = ev.get(field)
        _ref_ok(ref.get("path") if isinstance(ref, dict) else None, field, filename, errors)
    return errors


def validate_gate3_repeat(errors):
    """Orquestra a validacao dos artefatos da repeticao corretiva do GATE 3.

    Nesta etapa NAO deve existir registro real; a funcao roda apenas se arquivos
    aparecerem no futuro. Sempre reafirma que a evidencia historica permanece
    invalidada (nunca revertida a COMPLETED_PASS)."""
    hist = os.path.join(EVIDENCE_DIR, GATE3_HISTORICAL_INVALIDATED_EVIDENCE)
    if os.path.isfile(hist):
        try:
            h = load_json(hist)
            if h.get("outcome") == "COMPLETED_PASS" or h.get("status") == "COMPLETED_PASS":
                errors.append(f"evidence/{GATE3_HISTORICAL_INVALIDATED_EVIDENCE}: "
                              f"evidencia historica invalidada NAO pode voltar a COMPLETED_PASS")
        except Fail:
            pass
    if not os.path.isdir(DECISIONS_DIR):
        return
    repeat_decision = {}
    dec_names = sorted(f for f in os.listdir(DECISIONS_DIR)
                       if f.startswith(GATE3_REPEAT_DECISION_PREFIX) and f.endswith(".json"))
    if dec_names:
        try:
            dschema = load_json(os.path.join(SCHEMA_DIR, GATE3_REPEAT_DECISION_SCHEMA))
        except Fail as exc:
            errors.append(str(exc))
            dschema = None
        for name in dec_names:
            derr = []
            try:
                rec = load_json(os.path.join(DECISIONS_DIR, name))
                repeat_decision = rec
                if dschema is not None:
                    validate_gate3_repeat_decision(rec, dschema, name, derr)
            except Fail as exc:
                derr.append(str(exc))
            if derr:
                errors.extend(derr)
                print(f"[FALHA] decisions/{name}: {len(derr)} problema(s)")
                for e in derr:
                    print(f"    - {e}")
            else:
                print(f"[OK]    decisions/{name}")
    if os.path.isdir(EVIDENCE_DIR):
        ev_names = sorted(f for f in os.listdir(EVIDENCE_DIR)
                          if f.startswith(GATE3_REPEAT_EVIDENCE_PREFIX) and f.endswith(".json"))
        if ev_names:
            try:
                eschema = load_json(os.path.join(SCHEMA_DIR, GATE3_REPEAT_EVIDENCE_SCHEMA))
            except Fail as exc:
                errors.append(str(exc))
                eschema = None
            for name in ev_names:
                everr = []
                try:
                    ev = load_json(os.path.join(EVIDENCE_DIR, name))
                    if eschema is not None:
                        validate_gate3_repeat_evidence(ev, eschema, repeat_decision, name, everr)
                except Fail as exc:
                    everr.append(str(exc))
                if everr:
                    errors.extend(everr)
                    print(f"[FALHA] evidence/{name}: {len(everr)} problema(s)")
                    for e in everr:
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

    gate1_errors = []
    validate_gate1(gate1_errors)
    all_errors.extend(gate1_errors)

    gate2_errors = []
    validate_gate2(gate2_errors)
    all_errors.extend(gate2_errors)

    gate3_errors = []
    validate_gate3(gate3_errors)
    all_errors.extend(gate3_errors)

    gate3_repeat_errors = []
    validate_gate3_repeat(gate3_repeat_errors)
    all_errors.extend(gate3_repeat_errors)

    if all_errors:
        print(f"\nValidacao FALHOU com {len(all_errors)} problema(s).")
        return 1
    print(f"\nValidacao OK: {len(ARTIFACTS)} artefatos, schemas, regras de seguranca, "
          f"cross-checks, registros reais de decisao, plano da auditoria binaria, "
          f"autorizacao do GATE 0, evidencia do GATE 0, autorizacao do GATE 1, "
          f"decisao/evidencia do GATE 2, decisao/evidencia do GATE 3 e "
          f"convencao da repeticao corretiva (sem registros reais).")
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
