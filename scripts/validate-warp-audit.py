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
# Prefixos da FUTURA repeticao corretiva do GATE 3 (convencao; nenhum arquivo real).
GATE3_REPEAT_EVIDENCE_PREFIX = "binary-audit-gate-03-corrective-repeat-evidence-"
GATE3_REPEAT_PARSER_OUTPUT_PREFIX = "binary-audit-gate-03-corrective-repeat-parser-output-"
# Prefixos aceitos em evidence/ (o orquestrador de cada gate filtra o seu proprio).
# GATE4_* sao aceitos como CONVENCAO (futuros); nesta preparacao nenhum arquivo real existe.
EVIDENCE_FILE_PREFIXES = (GATE0_EVIDENCE_PREFIX, GATE2_EVIDENCE_PREFIX,
                          GATE3_EVIDENCE_PREFIX, GATE3_REPEAT_EVIDENCE_PREFIX,
                          GATE3_REPEAT_PARSER_OUTPUT_PREFIX,
                          "binary-audit-gate-04-pass-evidence-",
                          "binary-audit-gate-04-fail-evidence-",
                          "binary-audit-gate-04-stopped-evidence-",
                          "binary-audit-gate-04-static-inventory-output-")
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
GATE3_REPEAT_PASS_EVIDENCE_SCHEMA = "binary-audit-gate-03-corrective-repeat-pass-evidence.schema.json"
GATE3_REPEAT_FAIL_EVIDENCE_SCHEMA = "binary-audit-gate-03-corrective-repeat-fail-evidence.schema.json"
GATE3_REPEAT_STOPPED_EVIDENCE_SCHEMA = "binary-audit-gate-03-corrective-repeat-stopped-evidence.schema.json"
GATE3_REPEAT_PARSER_OUTPUT_SCHEMA = "binary-audit-gate-03-corrective-repeat-parser-output.schema.json"
GATE3_REPEAT_DECISION_PREFIX = "binary-audit-gate-03-corrective-repeat-decision-record-"
GATE3_HISTORICAL_INVALIDATED_EVIDENCE = "binary-audit-gate-03-identity-signature-evidence-2026-08-03.json"
REVIEWED_PARSER_PATH = "scripts/inspect-warp-pe-identity.py"
REVIEWED_PARSER_TEST_PATH = "scripts/test-warp-pe-identity.py"

# --- ETAPA 2P-E-C4-PREP: GATE 4 (inventario PE estatico offline) ---
# PREPARACAO APENAS: cria e valida a CONVENCAO (schemas + ferramenta) do futuro GATE 4.
# Nesta etapa NAO existe decisao/evidencia/saida real do GATE 4 (contagens = 0). A futura
# autorizacao operacional ocorrera em PR separado, referenciando o squash integrado desta
# preparacao e os Git blob OIDs exatos do analisador e dos testes revisados. O validador
# reprova criacao prematura, orfaos, duplicacao, autorizacao transitiva do GATE 5, saida
# com conteudo proibido e estados impossiveis do analisador.
GATE4_DECISION_SCHEMA = "binary-audit-gate-04-decision-record-real.schema.json"
GATE4_PASS_EVIDENCE_SCHEMA = "binary-audit-gate-04-pass-evidence.schema.json"
GATE4_FAIL_EVIDENCE_SCHEMA = "binary-audit-gate-04-fail-evidence.schema.json"
GATE4_STOPPED_EVIDENCE_SCHEMA = "binary-audit-gate-04-stopped-evidence.schema.json"
GATE4_OUTPUT_SCHEMA = "binary-audit-gate-04-static-inventory-output.schema.json"
GATE4_ALL_SCHEMAS = (
    GATE4_DECISION_SCHEMA, GATE4_PASS_EVIDENCE_SCHEMA, GATE4_FAIL_EVIDENCE_SCHEMA,
    GATE4_STOPPED_EVIDENCE_SCHEMA, GATE4_OUTPUT_SCHEMA,
)
GATE4_DECISION_PREFIX = "binary-audit-gate-04-decision-record-"
GATE4_PASS_EVIDENCE_PREFIX = "binary-audit-gate-04-pass-evidence-"
GATE4_FAIL_EVIDENCE_PREFIX = "binary-audit-gate-04-fail-evidence-"
GATE4_STOPPED_EVIDENCE_PREFIX = "binary-audit-gate-04-stopped-evidence-"
GATE4_OUTPUT_PREFIX = "binary-audit-gate-04-static-inventory-output-"
GATE4_EVIDENCE_PREFIXES = (GATE4_PASS_EVIDENCE_PREFIX, GATE4_FAIL_EVIDENCE_PREFIX,
                           GATE4_STOPPED_EVIDENCE_PREFIX)
REVIEWED_ANALYZER_PATH = "scripts/inspect-warp-pe-static.py"
REVIEWED_ANALYZER_TEST_PATH = "scripts/test-warp-pe-static.py"
GATE3_REPEAT_PASS_EVIDENCE = "binary-audit-gate-03-corrective-repeat-evidence-2026-08-03.json"
# Flags true no registro de decisao do GATE 4 (decisao + pre-condicao + grants do gate).
GATE4_DECISION_TRUE_FLAGS = {
    "human_decision_required", "human_decision_received", "gate_selected",
    "gate_3_completed", "temporary_materialization_authorized",
    "local_hashing_authorized", "static_inventory_authorized",
    "gate_4_authorized", "gate_4_execution_authorized",
}
# Pontos criticos que DEVEM permanecer false no GATE 4 (sem autorizacao transitiva).
GATE4_CRITICAL_FALSE = {
    "gate_5_authorized", "dynamic_analysis_authorized", "emulation_authorized",
    "unpacking_authorized", "execution_authorized",
    "external_reputation_upload_authorized", "network_validation_authorized",
    "sandbox_creation_authorized", "client_copy_provision_authorized",
    "client_modification_authorized", "patch_review_authorized",
    "patch_application_authorized", "client_preparation_authorized",
    "test_account_authorized", "first_login_authorized", "vps_access_authorized",
    "distribution_authorized",
}
# Estados FECHADOS validos da tri-flag analyzer_invoked/completed/output_produced no FAIL.
GATE4_FAIL_ANALYZER_STATES = {
    (False, False, False),  # PRE_ANALYZER_FAIL
    (True, False, False),   # ANALYZER_ERROR_WITHOUT_OUTPUT
    (True, True, True),     # POST_OUTPUT_FAIL
}


def git_blob_oid_for_bytes(data):
    """Recalcula o Git object ID (blob) localmente: SHA-1('blob <size>\\0' + content).
    Sem subprocess e sem rede. Confirma proveniencia contra os bytes reais da worktree."""
    import hashlib as _hashlib
    header = b"blob %d\x00" % len(data)
    return _hashlib.sha1(header + data).hexdigest()


def _git_blob_oid_of_repo_file(rel_path):
    """Git blob OID do arquivo textual atual da worktree (ou None se ausente)."""
    p = os.path.join(REPO_ROOT, rel_path)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, "rb") as fh:
            return git_blob_oid_for_bytes(fh.read())
    except OSError:
        return None


def _canonical_parser_output_bytes(obj):
    """Forma canonica do artefato de saida do parser (igual ao stdout do inspetor:
    json.dumps(indent=2, sort_keys=True) + '\\n'). Base para o SHA-256 amarrado."""
    import hashlib as _hashlib  # noqa: F401 (import local para manter stdlib-only)
    text = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return text.encode("utf-8")


def _sha256_hex(data):
    import hashlib as _hashlib
    return _hashlib.sha256(data).hexdigest()


def _reject_duplicate_keys(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise ValueError("chave JSON duplicada: %r" % k)
        seen[k] = v
    return seen


# Padroes proibidos na saida direta do parser (defesa em profundidade).
_PARSER_OUTPUT_BASE64_RE = re.compile(r"[A-Za-z0-9+/]{40,}={0,2}")
_PARSER_OUTPUT_BCERT_RE = re.compile(r"(?i)bcertificate|-----BEGIN")


def validate_parser_output_raw(raw_bytes, declared_sha256, filename, errors):
    """Prende a saida do parser aos BYTES EXATOS versionados (2P-E-C3-R4).

    Calcula o SHA-256 diretamente sobre `raw_bytes`; rejeita BOM, CRLF, ausencia/excesso
    de newline final e dados apos o newline; carrega o JSON rejeitando chaves duplicadas;
    exige raw_bytes == forma canonica (indent=2, sort_keys); valida contra o schema
    FECHADO; e aplica varreduras de seguranca. Retorna o dict parseado (ou None em erro).
    """
    if not isinstance(raw_bytes, (bytes, bytearray)):
        errors.append(f"{filename}: saida do parser ausente (bytes esperados)")
        return None
    raw = bytes(raw_bytes)
    if not isinstance(declared_sha256, str) or not HEX64_RE.match(declared_sha256):
        errors.append(f"{filename}: reviewed_parser_output_sha256 deve ter 64 hex")
    else:
        actual = _sha256_hex(raw)
        if actual != declared_sha256:
            errors.append(f"{filename}: SHA-256 dos bytes reais da saida nao confere com o registrado")
    # BOM / CRLF / newline final unico / sem dados apos o newline.
    if raw.startswith(b"\xef\xbb\xbf"):
        errors.append(f"{filename}: saida do parser com BOM UTF-8 proibido")
    if b"\r\n" in raw or b"\r" in raw:
        errors.append(f"{filename}: saida do parser com CRLF proibido")
    if not raw.endswith(b"\n"):
        errors.append(f"{filename}: saida do parser sem newline final")
    elif raw.endswith(b"\n\n"):
        errors.append(f"{filename}: saida do parser com newline final duplicado / dados apos o newline")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        errors.append(f"{filename}: saida do parser nao e UTF-8 estrito")
        return None
    try:
        parsed = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except ValueError as exc:
        errors.append(f"{filename}: saida do parser com JSON invalido/duplicado: {exc}")
        return None
    expected = _canonical_parser_output_bytes(parsed)
    if raw != expected:
        errors.append(f"{filename}: bytes da saida != forma deterministica (ordenacao/indentacao/encoding)")
    # Schema fechado + seguranca.
    try:
        po_schema = load_json(os.path.join(SCHEMA_DIR, GATE3_REPEAT_PARSER_OUTPUT_SCHEMA))
        validate_node(parsed, po_schema, "parser-output", errors)
    except Fail as exc:
        errors.append(str(exc))
    security_scan(parsed, errors)
    planning_content_scan(parsed, filename, errors)
    for where, s in iter_strings(parsed):
        if _PARSER_OUTPUT_BCERT_RE.search(s):
            errors.append(f"{filename}{where}: conteudo semelhante a bCertificate/PEM proibido na saida")
        if _PARSER_OUTPUT_BASE64_RE.search(s):
            errors.append(f"{filename}{where}: bloco base64/binario proibido na saida do parser")
    return parsed

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


def _recompute_and_compare_oid(field, path, registered, filename, errors):
    """Recalcula o Git blob OID do arquivo `path` e compara com `registered`.
    _git_blob_oid_of_repo_file()==None e ERRO (nunca validacao omitida)."""
    actual = _git_blob_oid_of_repo_file(path)
    if actual is None:
        errors.append(f"{filename}: {field}: arquivo {path} ausente para recalcular o Git blob OID")
        return
    if not isinstance(registered, str) or not HEX40_RE.match(registered):
        errors.append(f"{filename}: {field} deve ser Git object ID de 40 hex")
        return
    if registered != actual:
        errors.append(f"{filename}: {field} nao confere com o conteudo atual de {path} (esperado {actual})")


def validate_gate3_repeat_decision(record, schema, filename, errors):
    """Valida a FUTURA decisao humana da repeticao corretiva do GATE 3 (importavel)."""
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

    for field in ("original_decision_ref", "original_invalidated_evidence_ref",
                  "r1_review_ref", "reviewed_parser_ref", "reviewed_parser_test_ref"):
        ref = record.get(field)
        _ref_ok(ref.get("path") if isinstance(ref, dict) else None, field, filename, errors)
    oi = record.get("original_invalidated_evidence_ref") or {}
    if isinstance(oi, dict) and oi.get("path") and not oi["path"].endswith(GATE3_HISTORICAL_INVALIDATED_EVIDENCE):
        errors.append(f"{filename}: original_invalidated_evidence_ref deve apontar para a evidencia invalidada do GATE 3")

    # Proveniencia amarrada ao CONTEUDO REAL (parser e testes).
    _recompute_and_compare_oid("reviewed_parser_git_blob_oid", REVIEWED_PARSER_PATH,
                               record.get("reviewed_parser_git_blob_oid"), filename, errors)
    _recompute_and_compare_oid("reviewed_parser_test_git_blob_oid", REVIEWED_PARSER_TEST_PATH,
                               record.get("reviewed_parser_test_git_blob_oid"), filename, errors)
    if not isinstance(record.get("reviewed_parser_commit"), str) or not HEX40_RE.match(record.get("reviewed_parser_commit", "")):
        errors.append(f"{filename}: reviewed_parser_commit deve ter 40 hex (confirmado pelo gate Git externo; a relacao commit->arvore NAO e verificada pelo validador offline)")
    return errors


def _repeat_evidence_schema_for(outcome):
    return {
        "COMPLETED_PASS": GATE3_REPEAT_PASS_EVIDENCE_SCHEMA,
        "COMPLETED_FAIL": GATE3_REPEAT_FAIL_EVIDENCE_SCHEMA,
        "STOPPED": GATE3_REPEAT_STOPPED_EVIDENCE_SCHEMA,
    }.get(outcome)


# Campos da saida do parser que a evidencia PASS duplica e que devem ser IDENTICOS.
_PASS_CROSSCHECK_FIELDS = (
    "file_size", "mz_present", "pe_signature_present", "pe_format", "optional_header_magic",
    "machine", "machine_value", "subsystem", "subsystem_value", "number_of_sections",
    "size_of_optional_header", "size_of_headers", "section_alignment", "file_alignment",
    "executable_image_flag_present", "section_table", "certificate_table",
    "pe_headers_structurally_parseable", "full_pe_validation_performed",
    "section_contents_validated", "security_evaluation_performed", "executed",
    "loaded_as_executable", "launched",
)


# Estados FECHADOS validos da tri-flag parser_invoked/parser_completed/parser_output_produced
# no caminho COMPLETED_FAIL (2P-E-C3-R4.1). Qualquer outra combinacao e reprovada.
GATE3_FAIL_PARSER_STATES = {
    (False, False, False),  # PRE_PARSER_FAIL: falha antes de invocar o parser.
    (True, False, False),   # PARSER_ERROR_WITHOUT_OUTPUT: parser retornou erro sem JSON valido.
    (True, True, True),     # POST_OUTPUT_FAIL: saida valida produzida, falha posterior.
}


def validate_parser_execution_state(invoked, completed, output_produced, outcome,
                                    filename, errors, has_completed=True):
    """Valida os invariantes da tri-flag parser_invoked/parser_completed/parser_output_produced
    e o conjunto FECHADO de estados por outcome (2P-E-C3-R4.1). Compartilhada por PASS/FAIL/STOPPED.

    STOPPED nao modela parser_completed (has_completed=False): valida apenas as relacoes
    possiveis entre invoked e output_produced. LIMITACAO documentada: sem parser_completed,
    'parser_invoked=false => parser_completed=false' nao pode ser verificado no STOPPED (o
    campo nao existe); os campos equivalentes existentes sao validados e a saida permanece
    proibida (parser_output_produced=false).
    """
    # --- Invariantes gerais (implicacoes logicas entre as flags) ---
    if has_completed:
        if completed is True and invoked is not True:
            errors.append(f"{filename}: parser_completed=true exige parser_invoked=true")
        if output_produced is True and not (invoked is True and completed is True):
            errors.append(f"{filename}: parser_output_produced=true exige parser_invoked=true e parser_completed=true")
        if invoked is False and (completed is not False or output_produced is not False):
            errors.append(f"{filename}: parser_invoked=false exige parser_completed=false e parser_output_produced=false")
        if completed is False and output_produced is not False:
            errors.append(f"{filename}: parser_completed=false exige parser_output_produced=false")
    else:
        # STOPPED: sem parser_completed. A saida ainda exige invocacao.
        if output_produced is True and invoked is not True:
            errors.append(f"{filename}: parser_output_produced=true exige parser_invoked=true")

    # --- Estados FECHADOS por outcome ---
    if outcome == "COMPLETED_PASS":
        if not (invoked is True and completed is True and output_produced is True):
            errors.append(f"{filename}: PASS exige parser_execution invoked/completed/output_produced=true")
    elif outcome == "COMPLETED_FAIL":
        if (invoked, completed, output_produced) not in GATE3_FAIL_PARSER_STATES:
            errors.append(
                f"{filename}: COMPLETED_FAIL exige um estado valido de parser_execution "
                f"[PRE_PARSER_FAIL(false/false/false), PARSER_ERROR_WITHOUT_OUTPUT(true/false/false), "
                f"POST_OUTPUT_FAIL(true/true/true)]; obtido "
                f"invoked={invoked!r}/completed={completed!r}/output_produced={output_produced!r}")
    elif outcome == "STOPPED":
        if output_produced is not False:
            errors.append(f"{filename}: STOPPED exige parser_output_produced=false")


def validate_gate3_repeat_evidence(ev, schema, repeat_decision, filename, errors,
                                   parser_output_raw=None, parser_output_path=None,
                                   present_output_name=None):
    """Valida a FUTURA evidencia da repeticao (PASS/FAIL/STOPPED) — importavel.

    parser_output_raw sao os BYTES EXATOS do arquivo de saida (ou None). A ligacao
    (referencia, hash, bytes) e verificada aqui conforme o outcome.
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

    outcome = ev.get("outcome")
    if ev.get("status") != outcome:
        errors.append(f"{filename}: status deve ser igual a outcome")

    sa = ev.get("security_assertions") or {}
    if sa.get("gate_4_authorized") is not False:
        errors.append(f"{filename}: security_assertions.gate_4_authorized deve ser false")
    for k in ("no_execution_performed", "no_gate4_inspection_performed", "no_ragexe_access",
              "no_vps_access"):
        if sa.get(k) is not True:
            errors.append(f"{filename}: security_assertions.{k} deve ser true")

    # corrective_repeat_decision_ref e verificado por IGUALDADE EXATA no orquestrador
    # (aponta para a decisao real presente); os demais apontam para arquivos estaveis.
    for field in ("original_invalidated_evidence_ref", "reviewed_parser_ref",
                  "reviewed_parser_test_ref"):
        if field in ev:
            ref = ev.get(field)
            _ref_ok(ref.get("path") if isinstance(ref, dict) else None, field, filename, errors)

    # Cross-check com a decisao (mesmo commit e mesmos OIDs).
    if isinstance(repeat_decision, dict):
        if repeat_decision.get("decision") != "AUTHORIZE_CORRECTIVE_REPEAT_GATE_3":
            errors.append(f"{filename}: repeticao sem decisao AUTHORIZE_CORRECTIVE_REPEAT_GATE_3")
        for k in ("reviewed_parser_git_blob_oid", "reviewed_parser_test_git_blob_oid",
                  "reviewed_parser_commit"):
            if k in ev and ev.get(k) != repeat_decision.get(k):
                errors.append(f"{filename}: {k} diverge da decisao da repeticao")
    else:
        errors.append(f"{filename}: decisao da repeticao ausente/invalida")

    pex = ev.get("parser_execution") or {}

    if outcome == "COMPLETED_PASS":
        validate_parser_execution_state(
            pex.get("parser_invoked"), pex.get("parser_completed"),
            pex.get("parser_output_produced"), outcome, filename, errors)
        pe = ev.get("pe_identity") or {}
        if pe.get("produced_by") != "REVIEWED_VERSIONED_PARSER":
            errors.append(f"{filename}: pe_identity.produced_by deve ser REVIEWED_VERSIONED_PARSER")
        if pe.get("pe_headers_structurally_parseable") is not True:
            errors.append(f"{filename}: PASS exige pe_headers_structurally_parseable=true")
        rp = ev.get("reviewed_parser") or {}
        if rp.get("run_on_warp_exe") is not True or rp.get("executes_or_loads_pe") is not False:
            errors.append(f"{filename}: PASS exige reviewed_parser.run_on_warp_exe=true e executes_or_loads_pe=false")
        ir = ev.get("identity_reconfirmation") or {}
        if ir.get("sha256_local") != EXPECTED_ARTIFACT_SHA256 or ir.get("identity_matches_gate_2") is not True:
            errors.append(f"{filename}: PASS exige identidade IGUAL ao GATE 2")
        if ir.get("executed") is not False or ir.get("loaded_as_executable") is not False:
            errors.append(f"{filename}: PASS: executado/carregado devem ser false")
        # Proveniencia dos OIDs contra o conteudo real.
        _recompute_and_compare_oid("reviewed_parser_git_blob_oid", REVIEWED_PARSER_PATH,
                                   ev.get("reviewed_parser_git_blob_oid"), filename, errors)
        _recompute_and_compare_oid("reviewed_parser_test_git_blob_oid", REVIEWED_PARSER_TEST_PATH,
                                   ev.get("reviewed_parser_test_git_blob_oid"), filename, errors)
        # A saida EXATA do parser e OBRIGATORIA no PASS.
        if parser_output_raw is None:
            errors.append(f"{filename}: PASS exige a saida real do parser (parser_output ausente)")
        else:
            po = validate_parser_output_raw(parser_output_raw, ev.get("reviewed_parser_output_sha256"),
                                            filename, errors)
            # Referencia deve apontar EXATAMENTE para o arquivo presente.
            ref = (ev.get("reviewed_parser_output_ref") or {}).get("path")
            if present_output_name is not None and ref is not None and not ref.endswith("/" + present_output_name):
                errors.append(f"{filename}: reviewed_parser_output_ref nao aponta para a saida presente ({present_output_name})")
            if parser_output_path is not None and ref != parser_output_path:
                errors.append(f"{filename}: reviewed_parser_output_ref.path != caminho real da saida")
            # Cross-check integral de todos os campos duplicados.
            if isinstance(po, dict):
                for f in _PASS_CROSSCHECK_FIELDS:
                    if f in pe and pe.get(f) != po.get(f):
                        errors.append(f"{filename}: pe_identity.{f} diverge da saida do parser")
                ct = ev.get("certificate_table")
                if isinstance(ct, dict):
                    poct = po.get("certificate_table") or {}
                    for f in ("present", "structurally_parseable", "entry_count", "first_field_is_file_offset_not_rva"):
                        if f in ct and ct.get(f) != poct.get(f):
                            errors.append(f"{filename}: certificate_table.{f} diverge da saida do parser")
    elif outcome == "COMPLETED_FAIL":
        validate_parser_execution_state(
            pex.get("parser_invoked"), pex.get("parser_completed"),
            pex.get("parser_output_produced"), outcome, filename, errors)
        fail = ev.get("failure") or {}
        if not fail.get("reason") or not fail.get("category"):
            errors.append(f"{filename}: COMPLETED_FAIL exige failure.category e failure.reason")
        if fail.get("cleanup_attempted") is not True:
            errors.append(f"{filename}: COMPLETED_FAIL exige cleanup_attempted=true")
        produced = pex.get("parser_output_produced")
        if produced is True:
            # POST_OUTPUT_FAIL: saida obrigatoria, PRESA por bytes e por caminho canonico
            # exato ao unico arquivo reconhecido pelo orquestrador (mesma regra do PASS).
            if parser_output_raw is None:
                errors.append(f"{filename}: FAIL com parser_output_produced=true exige a saida real")
            elif present_output_name is None or parser_output_path is None:
                errors.append(f"{filename}: FAIL com saida exige nome/caminho reais da saida (execute pelo orquestrador)")
            else:
                validate_parser_output_raw(parser_output_raw, ev.get("reviewed_parser_output_sha256"), filename, errors)
                ref = (ev.get("reviewed_parser_output_ref") or {}).get("path")
                if "reviewed_parser_output_ref" not in ev or ref is None:
                    errors.append(f"{filename}: FAIL com saida exige reviewed_parser_output_ref")
                else:
                    if not ref.endswith("/" + present_output_name):
                        errors.append(f"{filename}: reviewed_parser_output_ref nao aponta para a saida presente ({present_output_name})")
                    if ref != parser_output_path:
                        errors.append(f"{filename}: reviewed_parser_output_ref.path != caminho real da saida")
        else:
            if "reviewed_parser_output_ref" in ev or "reviewed_parser_output_sha256" in ev:
                errors.append(f"{filename}: FAIL sem saida NAO pode ter reviewed_parser_output_ref/sha256")
            if parser_output_raw is not None:
                errors.append(f"{filename}: FAIL sem parser_output_produced nao pode ter saida presente")
        _recompute_and_compare_oid("reviewed_parser_git_blob_oid", REVIEWED_PARSER_PATH,
                                   ev.get("reviewed_parser_git_blob_oid"), filename, errors)
        _recompute_and_compare_oid("reviewed_parser_test_git_blob_oid", REVIEWED_PARSER_TEST_PATH,
                                   ev.get("reviewed_parser_test_git_blob_oid"), filename, errors)
    elif outcome == "STOPPED":
        stop = ev.get("stop") or {}
        # STOPPED modela apenas parser_invoked e parser_output_produced (sem parser_completed).
        validate_parser_execution_state(
            stop.get("parser_invoked"), None, stop.get("parser_output_produced"),
            outcome, filename, errors, has_completed=False)
        if not stop.get("reason") or not stop.get("category"):
            errors.append(f"{filename}: STOPPED exige stop.category e stop.reason")
        if stop.get("gate_3_repeat_completed") is not False:
            errors.append(f"{filename}: STOPPED exige gate_3_repeat_completed=false")
        if parser_output_raw is not None:
            errors.append(f"{filename}: STOPPED nao pode ter saida do parser presente")
    else:
        errors.append(f"{filename}: outcome fora do conjunto permitido")
    return errors


def validate_gate3_repeat(errors):
    """Orquestra a maquina de estados da repeticao corretiva (atomica), impedindo
    artefatos orfaos e duplicados. Nesta etapa NAO deve existir registro real."""
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
    dec_names = sorted(f for f in os.listdir(DECISIONS_DIR)
                       if f.startswith(GATE3_REPEAT_DECISION_PREFIX) and f.endswith(".json"))
    ev_names, po_names = [], []
    if os.path.isdir(EVIDENCE_DIR):
        ev_names = sorted(f for f in os.listdir(EVIDENCE_DIR)
                          if f.startswith(GATE3_REPEAT_EVIDENCE_PREFIX) and f.endswith(".json"))
        po_names = sorted(f for f in os.listdir(EVIDENCE_DIR)
                          if f.startswith(GATE3_REPEAT_PARSER_OUTPUT_PREFIX) and f.endswith(".json"))

    # Duplicacao: no maximo um de cada.
    if len(dec_names) > 1:
        errors.append(f"repeticao: mais de uma decisao real ({dec_names})")
    if len(ev_names) > 1:
        errors.append(f"repeticao: mais de uma evidencia real ({ev_names})")
    if len(po_names) > 1:
        errors.append(f"repeticao: mais de uma saida real do parser ({po_names})")

    # ---- Maquina de estados (atomica) ----
    # Sem decisao: NAO pode haver evidencia nem saida (artefato orfao).
    if not dec_names:
        if ev_names:
            errors.append(f"repeticao: evidencia sem decisao (orfa): {ev_names}")
        if po_names:
            errors.append(f"repeticao: saida do parser sem decisao (orfa): {po_names}")
        return

    # Decisao presente: validar.
    repeat_decision = {}
    try:
        dschema = load_json(os.path.join(SCHEMA_DIR, GATE3_REPEAT_DECISION_SCHEMA))
    except Fail as exc:
        errors.append(str(exc)); dschema = None
    dname = dec_names[0]
    derr = []
    try:
        repeat_decision = load_json(os.path.join(DECISIONS_DIR, dname))
        if dschema is not None:
            validate_gate3_repeat_decision(repeat_decision, dschema, dname, derr)
    except Fail as exc:
        derr.append(str(exc))
    if derr:
        errors.extend(derr)
        print(f"[FALHA] decisions/{dname}: {len(derr)} problema(s)")
        for e in derr:
            print(f"    - {e}")
    else:
        print(f"[OK]    decisions/{dname}")

    # Decisao sem evidencia: saida orfa e proibida (autorizado, ainda nao executado).
    if not ev_names:
        if po_names:
            errors.append(f"repeticao: saida do parser sem evidencia (orfa): {po_names}")
        return

    # Evidencia presente: dispatch por outcome; ligar bytes exatos da saida.
    ev_name = ev_names[0]
    po_name = po_names[0] if po_names else None
    parser_output_raw = None
    parser_output_path = None
    if po_name is not None:
        parser_output_path = "client/warp-audit/evidence/" + po_name
        try:
            with open(os.path.join(EVIDENCE_DIR, po_name), "rb") as fh:
                parser_output_raw = fh.read()
        except OSError as exc:
            errors.append(f"repeticao: falha ao ler a saida do parser: {exc}")

    everr = []
    try:
        ev = load_json(os.path.join(EVIDENCE_DIR, ev_name))
        eschema_name = _repeat_evidence_schema_for(ev.get("outcome"))
        if eschema_name is None:
            everr.append(f"{ev_name}: outcome sem schema correspondente")
        else:
            eschema = load_json(os.path.join(SCHEMA_DIR, eschema_name))
            crd = (ev.get("corrective_repeat_decision_ref") or {}).get("path")
            expected_dec = "client/warp-audit/decisions/" + dname
            if crd != expected_dec:
                everr.append(f"{ev_name}: corrective_repeat_decision_ref deve ser exatamente {expected_dec}")
            validate_gate3_repeat_evidence(ev, eschema, repeat_decision, ev_name, everr,
                                           parser_output_raw=parser_output_raw,
                                           parser_output_path=parser_output_path,
                                           present_output_name=po_name)
    except Fail as exc:
        everr.append(str(exc))
    if everr:
        errors.extend(everr)
        print(f"[FALHA] evidence/{ev_name}: {len(everr)} problema(s)")
        for e in everr:
            print(f"    - {e}")
    else:
        print(f"[OK]    evidence/{ev_name}")


# --- ETAPA 2P-E-C4-PREP: validacao da CONVENCAO e da maquina de estados do GATE 4 ---
# Regex de conteudo proibido na saida do inventario (defesa em profundidade). NAO se
# aplica planning_content_scan aqui: o inventario legitimamente registra URLs/dominios/
# caminhos como INDICADORES textuais; a proibicao e de bytes brutos, bCertificate e base64.
_GATE4_OUTPUT_BASE64_RE = _PARSER_OUTPUT_BASE64_RE
_GATE4_OUTPUT_BCERT_RE = _PARSER_OUTPUT_BCERT_RE


def validate_gate4_output_raw(raw_bytes, declared_sha256, filename, errors):
    """Prende a saida do inventario aos BYTES EXATOS versionados (2P-E-C4-PREP).

    SHA-256 sobre os bytes reais; rejeita BOM/CRLF/newline duplicado/dados apos newline;
    chaves duplicadas; exige forma canonica (indent=2, sort_keys); valida contra o schema
    FECHADO da saida; aplica security_scan e proibe bCertificate/base64/bytes brutos.
    Retorna o dict parseado (ou None em erro)."""
    if not isinstance(raw_bytes, (bytes, bytearray)):
        errors.append(f"{filename}: saida do inventario ausente (bytes esperados)")
        return None
    raw = bytes(raw_bytes)
    if not isinstance(declared_sha256, str) or not HEX64_RE.match(declared_sha256):
        errors.append(f"{filename}: reviewed_analyzer_output_sha256 deve ter 64 hex")
    else:
        if _sha256_hex(raw) != declared_sha256:
            errors.append(f"{filename}: SHA-256 dos bytes reais da saida nao confere com o registrado")
    if raw.startswith(b"\xef\xbb\xbf"):
        errors.append(f"{filename}: saida do inventario com BOM UTF-8 proibido")
    if b"\r\n" in raw or b"\r" in raw:
        errors.append(f"{filename}: saida do inventario com CRLF proibido")
    if not raw.endswith(b"\n"):
        errors.append(f"{filename}: saida do inventario sem newline final")
    elif raw.endswith(b"\n\n"):
        errors.append(f"{filename}: saida do inventario com newline final duplicado / dados apos o newline")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        errors.append(f"{filename}: saida do inventario nao e UTF-8 estrito")
        return None
    try:
        parsed = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except ValueError as exc:
        errors.append(f"{filename}: saida do inventario com JSON invalido/duplicado: {exc}")
        return None
    if raw != _canonical_parser_output_bytes(parsed):
        errors.append(f"{filename}: bytes da saida != forma deterministica (ordenacao/indentacao/encoding)")
    try:
        po_schema = load_json(os.path.join(SCHEMA_DIR, GATE4_OUTPUT_SCHEMA))
        validate_node(parsed, po_schema, "gate-04-output", errors)
    except Fail as exc:
        errors.append(str(exc))
    security_scan(parsed, errors)
    for where, s in iter_strings(parsed):
        if _GATE4_OUTPUT_BCERT_RE.search(s):
            errors.append(f"{filename}{where}: conteudo semelhante a bCertificate/PEM proibido na saida")
        if _GATE4_OUTPUT_BASE64_RE.search(s):
            errors.append(f"{filename}{where}: bloco base64/binario proibido na saida do inventario")
    return parsed


def validate_gate4_decision(record, schema, filename, errors):
    """Valida a FUTURA decisao humana do GATE 4 (AUTHORIZE_GATE_4_EXECUTION). Importavel.

    Exige: decisao/gate corretos; identidade/data/condicoes numeradas 1..N; SOMENTE os
    grants do GATE 4 em true; gate_5_authorized e demais pontos criticos em false;
    escopo fechado ao blob canonico; pre-condicao GATE 3 = COMPLETED_PASS; proveniencia
    do analisador e dos testes recalculada contra o conteudo real da worktree."""
    kv = []
    schema_keyword_violations(schema, "gate-04-decision.schema", kv)
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
    if not isinstance(g, dict) or g.get("id") != 4 or g.get("name") != "STATIC_PE_INVENTORY":
        errors.append(f"{filename}: gate deve ser id=4 name=STATIC_PE_INVENTORY")
    if record.get("decision") != "AUTHORIZE_GATE_4_EXECUTION":
        errors.append(f"{filename}: decision deve ser AUTHORIZE_GATE_4_EXECUTION")
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
    if not isinstance(conds, list) or len(conds) < 15:
        errors.append(f"{filename}: 'conditions' deve ter ao menos 15 itens")
        conds = conds if isinstance(conds, list) else []
    ns = [c.get("n") for c in conds if isinstance(c, dict)]
    if ns != list(range(1, len(conds) + 1)):
        errors.append(f"{filename}: conditions devem ser numeradas 1..N em ordem, sem lacuna/repeticao")
    for i, c in enumerate(conds):
        if not isinstance(c, dict) or not str(c.get("text", "")).strip():
            errors.append(f"{filename}: conditions[{i}] sem texto")

    auth = record.get("authorizations")
    if not isinstance(auth, dict):
        errors.append(f"{filename}: 'authorizations' ausente")
    else:
        for k, v in auth.items():
            if k in GATE4_DECISION_TRUE_FLAGS:
                if v is not True:
                    errors.append(f"{filename}: authorizations.{k} deve ser true")
            elif v is not False:
                errors.append(f"{filename}: authorizations.{k} deve ser false (grants do GATE 4 sao limitados)")
        if auth.get("gate_4_execution_authorized") is not True:
            errors.append(f"{filename}: authorizations.gate_4_execution_authorized deve ser true (grant do GATE 4)")
        for k in GATE4_CRITICAL_FALSE:
            if auth.get(k) is not False:
                errors.append(f"{filename}: authorizations.{k} deve ser false (sem autorizacao transitiva)")

    _check_materialization_scope(record.get("materialization_scope"), filename, errors)

    pc = record.get("precondition")
    if not isinstance(pc, dict):
        errors.append(f"{filename}: 'precondition' ausente")
    else:
        if pc.get("gate_3_completed") is not True:
            errors.append(f"{filename}: precondition.gate_3_completed deve ser true")
        if pc.get("gate_3_outcome") != "COMPLETED_PASS":
            errors.append(f"{filename}: precondition.gate_3_outcome deve ser COMPLETED_PASS")

    ir = record.get("integration_ref")
    if not isinstance(ir, dict) or ir.get("base_branch") != "dev":
        errors.append(f"{filename}: integration_ref.base_branch deve ser dev (squash da preparacao integrada)")

    for field in ("plan_ref", "source_decision_ref", "prior_gate_decision_ref",
                  "gate_3_evidence_ref", "reviewed_analyzer_ref", "reviewed_analyzer_test_ref"):
        ref = record.get(field)
        _ref_ok(ref.get("path") if isinstance(ref, dict) else None, field, filename, errors)

    _recompute_and_compare_oid("reviewed_analyzer_git_blob_oid", REVIEWED_ANALYZER_PATH,
                               record.get("reviewed_analyzer_git_blob_oid"), filename, errors)
    _recompute_and_compare_oid("reviewed_analyzer_test_git_blob_oid", REVIEWED_ANALYZER_TEST_PATH,
                               record.get("reviewed_analyzer_test_git_blob_oid"), filename, errors)
    if not isinstance(record.get("reviewed_analyzer_commit"), str) or not HEX40_RE.match(record.get("reviewed_analyzer_commit", "")):
        errors.append(f"{filename}: reviewed_analyzer_commit deve ter 40 hex (confirmado pelo gate Git externo)")
    return errors


def validate_gate4_evidence(ev, schema, decision, filename, errors,
                            output_raw=None, output_path=None, present_output_name=None):
    """Valida a FUTURA evidencia do GATE 4 (PASS/FAIL/STOPPED). Importavel.

    Dispatch por outcome; a saida do inventario (quando exigida) e presa por bytes e por
    referencia exata. gate_5_authorized DEVE ser false. Sem autorizacao transitiva."""
    kv = []
    schema_keyword_violations(schema, "gate-04-evidence.schema", kv)
    errors.extend(kv)
    validate_node(ev, schema, filename, errors)
    security_scan(ev, errors)
    _content_scan_allow_hashes(ev, filename, errors)

    if not isinstance(ev, dict):
        errors.append(f"{filename}: evidencia nao e objeto")
        return errors

    outcome = ev.get("outcome")
    if ev.get("status") != outcome:
        errors.append(f"{filename}: status deve ser igual a outcome")
    g = ev.get("gate")
    if not isinstance(g, dict) or g.get("id") != 4 or g.get("name") != "STATIC_PE_INVENTORY":
        errors.append(f"{filename}: gate deve ser id=4 name=STATIC_PE_INVENTORY")

    sa = ev.get("security_assertions") or {}
    if sa.get("gate_5_authorized") is not False:
        errors.append(f"{filename}: security_assertions.gate_5_authorized deve ser false")
    for k in ("no_execution_performed", "no_gate5_inspection_performed",
              "no_ragexe_access", "no_vps_access"):
        if sa.get(k) is not True:
            errors.append(f"{filename}: security_assertions.{k} deve ser true")

    if isinstance(decision, dict):
        a = decision.get("authorizations", {})
        if decision.get("decision") != "AUTHORIZE_GATE_4_EXECUTION" or a.get("gate_4_execution_authorized") is not True:
            errors.append(f"{filename}: decisao do GATE 4 nao autoriza a execucao")
        if a.get("gate_5_authorized") is not False:
            errors.append(f"{filename}: decisao do GATE 4 nao pode autorizar o GATE 5")
    else:
        errors.append(f"{filename}: decisao do GATE 4 ausente/invalida")

    _recompute_and_compare_oid("reviewed_analyzer_git_blob_oid", REVIEWED_ANALYZER_PATH,
                               ev.get("reviewed_analyzer_git_blob_oid"), filename, errors)
    _recompute_and_compare_oid("reviewed_analyzer_test_git_blob_oid", REVIEWED_ANALYZER_TEST_PATH,
                               ev.get("reviewed_analyzer_test_git_blob_oid"), filename, errors)

    pex = ev.get("parser_execution") or {}
    inv = pex.get("analyzer_invoked")
    comp = pex.get("analyzer_completed")
    prod = pex.get("analyzer_output_produced")

    if outcome == "COMPLETED_PASS":
        validate_parser_execution_state(inv, comp, prod, outcome, filename, errors)
        summ = ev.get("static_inventory_summary") or {}
        if summ.get("produced_by") != "REVIEWED_VERSIONED_ANALYZER":
            errors.append(f"{filename}: static_inventory_summary.produced_by deve ser REVIEWED_VERSIONED_ANALYZER")
        ra = ev.get("reviewed_analyzer") or {}
        if ra.get("run_on_warp_exe") is not True or ra.get("executes_or_loads_pe") is not False:
            errors.append(f"{filename}: PASS exige reviewed_analyzer.run_on_warp_exe=true e executes_or_loads_pe=false")
        if ra.get("emulates_pe") is not False or ra.get("unpacks_dynamically") is not False:
            errors.append(f"{filename}: PASS exige reviewed_analyzer sem emulacao/descompactacao")
        ir = ev.get("identity_reconfirmation") or {}
        if ir.get("sha256_local") != EXPECTED_ARTIFACT_SHA256 or ir.get("identity_matches_gate_2") is not True:
            errors.append(f"{filename}: PASS exige identidade IGUAL ao GATE 2")
        if ir.get("executed") is not False or ir.get("loaded_as_executable") is not False:
            errors.append(f"{filename}: PASS: executado/carregado devem ser false")
        pf = ev.get("preserved_gate_3_facts") or {}
        if pf.get("artifact_sha256") != EXPECTED_ARTIFACT_SHA256 or pf.get("artifact_blob_oid") != EXPECTED_ARTIFACT_BLOB:
            errors.append(f"{filename}: preserved_gate_3_facts deve preservar os fatos do GATE 2/3")
        if output_raw is None:
            errors.append(f"{filename}: PASS exige a saida real do inventario (output ausente)")
        else:
            validate_gate4_output_raw(output_raw, ev.get("reviewed_analyzer_output_sha256"), filename, errors)
            ref = (ev.get("reviewed_analyzer_output_ref") or {}).get("path")
            if present_output_name is not None and (ref is None or not ref.endswith("/" + present_output_name)):
                errors.append(f"{filename}: reviewed_analyzer_output_ref nao aponta para a saida presente ({present_output_name})")
            if output_path is not None and ref != output_path:
                errors.append(f"{filename}: reviewed_analyzer_output_ref.path != caminho real da saida")
    elif outcome == "COMPLETED_FAIL":
        validate_parser_execution_state(inv, comp, prod, outcome, filename, errors)
        if (inv, comp, prod) not in GATE4_FAIL_ANALYZER_STATES:
            errors.append(f"{filename}: COMPLETED_FAIL exige estado fechado de parser_execution "
                          f"[PRE_ANALYZER_FAIL/ANALYZER_ERROR_WITHOUT_OUTPUT/POST_OUTPUT_FAIL]")
        fail = ev.get("failure") or {}
        if not fail.get("reason") or not fail.get("category"):
            errors.append(f"{filename}: COMPLETED_FAIL exige failure.category e failure.reason")
        if fail.get("cleanup_attempted") is not True:
            errors.append(f"{filename}: COMPLETED_FAIL exige cleanup_attempted=true")
        if prod is True:
            if output_raw is None or present_output_name is None or output_path is None:
                errors.append(f"{filename}: FAIL com saida exige a saida real (execute pelo orquestrador)")
            else:
                validate_gate4_output_raw(output_raw, ev.get("reviewed_analyzer_output_sha256"), filename, errors)
                ref = (ev.get("reviewed_analyzer_output_ref") or {}).get("path")
                if "reviewed_analyzer_output_ref" not in ev or ref is None:
                    errors.append(f"{filename}: FAIL com saida exige reviewed_analyzer_output_ref")
                elif not ref.endswith("/" + present_output_name) or ref != output_path:
                    errors.append(f"{filename}: reviewed_analyzer_output_ref nao aponta para a saida presente")
        else:
            if "reviewed_analyzer_output_ref" in ev or "reviewed_analyzer_output_sha256" in ev:
                errors.append(f"{filename}: FAIL sem saida NAO pode ter reviewed_analyzer_output_ref/sha256")
            if output_raw is not None:
                errors.append(f"{filename}: FAIL sem analyzer_output_produced nao pode ter saida presente")
    elif outcome == "STOPPED":
        stop = ev.get("stop") or {}
        validate_parser_execution_state(
            stop.get("analyzer_invoked"), None, stop.get("analyzer_output_produced"),
            outcome, filename, errors, has_completed=False)
        if not stop.get("reason") or not stop.get("category"):
            errors.append(f"{filename}: STOPPED exige stop.category e stop.reason")
        if stop.get("gate_4_completed") is not False:
            errors.append(f"{filename}: STOPPED exige gate_4_completed=false")
        if output_raw is not None:
            errors.append(f"{filename}: STOPPED nao pode ter saida do inventario presente")
    else:
        errors.append(f"{filename}: outcome fora do conjunto permitido")
    return errors


def _gate4_evidence_schema_for(outcome):
    return {
        "COMPLETED_PASS": GATE4_PASS_EVIDENCE_SCHEMA,
        "COMPLETED_FAIL": GATE4_FAIL_EVIDENCE_SCHEMA,
        "STOPPED": GATE4_STOPPED_EVIDENCE_SCHEMA,
    }.get(outcome)


def validate_gate4_prep(errors):
    """Orquestra a preparacao do GATE 4 (2P-E-C4-PREP) e a maquina de estados atomica.

    Confirma a CONVENCAO (5 schemas + analisador + testes versionados) e impede
    criacao prematura, orfaos e duplicacao. Nesta preparacao NAO deve existir decisao/
    evidencia/saida real do GATE 4 (contagens = 0); a autorizacao operacional ocorrera
    em PR separado. Imprime a confirmacao semantica exigida pela etapa."""
    # 1) Convencao presente e keyword-clean.
    prep_ok = True
    for sname in GATE4_ALL_SCHEMAS:
        spath = os.path.join(SCHEMA_DIR, sname)
        if not os.path.isfile(spath):
            errors.append(f"gate-04-prep: schema ausente: {sname}")
            prep_ok = False
            continue
        try:
            sch = load_json(spath)
        except Fail as exc:
            errors.append(str(exc)); prep_ok = False; continue
        kv = []
        schema_keyword_violations(sch, sname, kv)
        if kv:
            errors.extend(kv); prep_ok = False
    for tool in (REVIEWED_ANALYZER_PATH, REVIEWED_ANALYZER_TEST_PATH):
        if not os.path.isfile(os.path.join(REPO_ROOT, tool)):
            errors.append(f"gate-04-prep: ferramenta ausente: {tool}")
            prep_ok = False

    # 2) Contagem de artefatos reais do GATE 4.
    dec_names, ev_names, po_names = [], [], []
    if os.path.isdir(DECISIONS_DIR):
        dec_names = sorted(f for f in os.listdir(DECISIONS_DIR)
                           if f.startswith(GATE4_DECISION_PREFIX) and f.endswith(".json"))
    if os.path.isdir(EVIDENCE_DIR):
        ev_names = sorted(f for f in os.listdir(EVIDENCE_DIR)
                          if f.startswith(GATE4_EVIDENCE_PREFIXES) and f.endswith(".json"))
        po_names = sorted(f for f in os.listdir(EVIDENCE_DIR)
                          if f.startswith(GATE4_OUTPUT_PREFIX) and f.endswith(".json"))

    # 3) Duplicacao: no maximo um de cada.
    if len(dec_names) > 1:
        errors.append(f"gate-04: mais de uma decisao real ({dec_names})")
    if len(ev_names) > 1:
        errors.append(f"gate-04: mais de uma evidencia real ({ev_names})")
    if len(po_names) > 1:
        errors.append(f"gate-04: mais de uma saida real do inventario ({po_names})")

    # 4) Maquina de estados atomica (decisao -> evidencia -> saida).
    gate_4_authorized = False
    gate_4_execution_authorized = False
    if not dec_names:
        if ev_names:
            errors.append(f"gate-04: evidencia sem decisao (orfa): {ev_names}")
        if po_names:
            errors.append(f"gate-04: saida sem decisao (orfa): {po_names}")
    else:
        decision = {}
        try:
            dschema = load_json(os.path.join(SCHEMA_DIR, GATE4_DECISION_SCHEMA))
        except Fail as exc:
            errors.append(str(exc)); dschema = None
        dname = dec_names[0]
        derr = []
        try:
            decision = load_json(os.path.join(DECISIONS_DIR, dname))
            if dschema is not None:
                validate_gate4_decision(decision, dschema, dname, derr)
        except Fail as exc:
            derr.append(str(exc))
        if derr:
            errors.extend(derr)
            print(f"[FALHA] decisions/{dname}: {len(derr)} problema(s)")
            for e in derr:
                print(f"    - {e}")
        else:
            print(f"[OK]    decisions/{dname}")
        if isinstance(decision, dict) and not derr:
            a = decision.get("authorizations", {})
            gate_4_authorized = a.get("gate_4_authorized") is True
            gate_4_execution_authorized = a.get("gate_4_execution_authorized") is True

        if not ev_names:
            if po_names:
                errors.append(f"gate-04: saida sem evidencia (orfa): {po_names}")
        else:
            ev_name = ev_names[0]
            po_name = po_names[0] if po_names else None
            output_raw = None
            output_path = None
            if po_name is not None:
                output_path = "client/warp-audit/evidence/" + po_name
                try:
                    with open(os.path.join(EVIDENCE_DIR, po_name), "rb") as fh:
                        output_raw = fh.read()
                except OSError as exc:
                    errors.append(f"gate-04: falha ao ler a saida do inventario: {exc}")
            everr = []
            try:
                ev = load_json(os.path.join(EVIDENCE_DIR, ev_name))
                eschema_name = _gate4_evidence_schema_for(ev.get("outcome"))
                if eschema_name is None:
                    everr.append(f"{ev_name}: outcome sem schema correspondente")
                else:
                    eschema = load_json(os.path.join(SCHEMA_DIR, eschema_name))
                    dref = (ev.get("gate_4_decision_ref") or {}).get("path")
                    expected_dec = "client/warp-audit/decisions/" + dec_names[0]
                    if dref != expected_dec:
                        everr.append(f"{ev_name}: gate_4_decision_ref deve ser exatamente {expected_dec}")
                    validate_gate4_evidence(ev, eschema, decision, ev_name, everr,
                                            output_raw=output_raw, output_path=output_path,
                                            present_output_name=po_name)
            except Fail as exc:
                everr.append(str(exc))
            if everr:
                errors.extend(everr)
                print(f"[FALHA] evidence/{ev_name}: {len(everr)} problema(s)")
                for e in everr:
                    print(f"    - {e}")
            else:
                print(f"[OK]    evidence/{ev_name}")

    # 5) Confirmacao semantica exigida por 2P-E-C4-PREP.
    print("[OK]    gate-04-prep (2P-E-C4-PREP): "
          f"gate_4_preparation_completed={str(prep_ok).lower()} "
          f"gate_4_authorized={str(gate_4_authorized).lower()} "
          f"gate_4_execution_authorized={str(gate_4_execution_authorized).lower()} "
          f"gate_4_real_decision_count={len(dec_names)} "
          f"gate_4_real_evidence_count={len(ev_names)} "
          f"gate_4_real_output_count={len(po_names)} gate_5_authorized=false")


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

    gate4_prep_errors = []
    validate_gate4_prep(gate4_prep_errors)
    all_errors.extend(gate4_prep_errors)

    if all_errors:
        print(f"\nValidacao FALHOU com {len(all_errors)} problema(s).")
        return 1
    print(f"\nValidacao OK: {len(ARTIFACTS)} artefatos, schemas, regras de seguranca, "
          f"cross-checks, registros reais de decisao, plano da auditoria binaria, "
          f"autorizacao do GATE 0, evidencia do GATE 0, autorizacao do GATE 1, "
          f"decisao/evidencia do GATE 2, decisao/evidencia do GATE 3, "
          f"convencao da repeticao corretiva (sem registros reais) e "
          f"preparacao do GATE 4 (2P-E-C4-PREP; sem registros reais).")
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
