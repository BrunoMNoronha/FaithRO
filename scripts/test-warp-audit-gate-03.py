#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes positivos e negativos dos artefatos do GATE 3 apos a revisao corretiva
2P-E-C3-R1: registro de decisao (AUTHORIZE_GATE_3, inalterado) e evidencia
INVALIDADA/pendente de repeticao (EVIDENCE_INVALIDATED_PENDING_REPEAT).

Offline e sem dependencias externas: importa scripts/validate-warp-audit.py e exercita
validate_gate3_decision/validate_gate3_evidence contra os artefatos reais e mutacoes
invalidas. Nao acessa a rede, nao materializa binario e nao executa o WARP.

Cobre, alem do PASS, os negativos das FASEs E/F (D1-D4), incluindo o caso especifico
pe_format=PE32 + magic 0x010b + size_of_optional_header=267 apresentado como medicao
confirmada (deve reprovar), semantica ambigua 'opened', ferramenta invoked=false com
exit_code nao nulo, e divergencia de identificadores do GATE 2.
"""
import copy
import importlib.util
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPTS_DIR)
AUDIT_DIR = os.path.join(REPO_ROOT, "client", "warp-audit")
SCHEMA_DIR = os.path.join(AUDIT_DIR, "schemas")
DECISIONS_DIR = os.path.join(AUDIT_DIR, "decisions")
EVIDENCE_DIR = os.path.join(AUDIT_DIR, "evidence")

DEC_FILE = "binary-audit-gate-03-decision-record-2026-08-03.json"
EV_FILE = "binary-audit-gate-03-identity-signature-evidence-2026-08-03.json"
GATE2_DEC_FILE = "binary-audit-gate-02-decision-record-2026-08-01.json"
GATE2_EV_FILE = "binary-audit-gate-02-integrity-evidence-2026-08-01.json"


def load_module():
    path = os.path.join(SCRIPTS_DIR, "validate-warp-audit.py")
    spec = importlib.util.spec_from_file_location("validate_warp_audit", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def setpath(keys, value):
    def _f(rec):
        node = rec
        for k in keys[:-1]:
            node = node[k]
        node[keys[-1]] = value
    return _f


def delpath(keys):
    def _f(rec):
        node = rec
        for k in keys[:-1]:
            node = node[k]
        del node[keys[-1]]
    return _f


def main():
    mod = load_module()
    dschema = load_json(os.path.join(SCHEMA_DIR, "binary-audit-gate-03-decision-record-real.schema.json"))
    eschema = load_json(os.path.join(SCHEMA_DIR, "binary-audit-gate-03-identity-signature-evidence.schema.json"))
    plan = load_json(os.path.join(AUDIT_DIR, "binary-audit-plan.example.json"))
    gate2_decision = load_json(os.path.join(DECISIONS_DIR, GATE2_DEC_FILE))
    gate2_evidence = load_json(os.path.join(EVIDENCE_DIR, GATE2_EV_FILE))
    base_dec = load_json(os.path.join(DECISIONS_DIR, DEC_FILE))
    base_ev = load_json(os.path.join(EVIDENCE_DIR, EV_FILE))

    passed = 0
    failed = 0

    def run_dec(rec, g2d=None, g2e=None):
        errs = []
        mod.validate_gate3_decision(rec, dschema, plan,
                                    gate2_decision if g2d is None else g2d,
                                    gate2_evidence if g2e is None else g2e,
                                    DEC_FILE, errs)
        return errs

    def run_ev(ev, g3=None, g2e=None):
        errs = []
        mod.validate_gate3_evidence(ev, eschema,
                                    base_dec if g3 is None else g3,
                                    gate2_evidence if g2e is None else g2e,
                                    EV_FILE, errs)
        return errs

    def ok(label, errs):
        nonlocal passed, failed
        if errs:
            failed += 1
            print(f"[FALHA] (esperava OK) {label}: {len(errs)} erro(s)")
            for e in errs[:6]:
                print("    -", e)
        else:
            passed += 1
            print(f"[OK+]   {label}")

    def bad(label, errs):
        nonlocal passed, failed
        if errs:
            passed += 1
            print(f"[OK-]   {label} (reprovado, {len(errs)} erro(s))")
        else:
            failed += 1
            print(f"[FALHA] (esperava reprovacao) {label}")

    def dec_fail(label, mutate, **ctx):
        rec = copy.deepcopy(base_dec)
        mutate(rec)
        bad(label, run_dec(rec, **ctx))

    def ev_fail(label, mutate, **ctx):
        ev = copy.deepcopy(base_ev)
        mutate(ev)
        bad(label, run_ev(ev, **ctx))

    # ---------- Positivos ----------
    ok("decisao real integra", run_dec(copy.deepcopy(base_dec)))
    ok("evidencia real (invalidada) integra", run_ev(copy.deepcopy(base_ev)))

    # ---------- Negativos: DECISAO (inalterada) ----------
    dec_fail("decisao incorreta", setpath(["decision"], "AUTHORIZE_GATE_2"))
    dec_fail("gate.id incorreto", setpath(["gate", "id"], 4))
    dec_fail("gate_3_authorized=false", setpath(["authorizations", "gate_3_authorized"], False))
    dec_fail("gate_4_authorized=true", setpath(["authorizations", "gate_4_authorized"], True))
    dec_fail("execution_authorized=true", setpath(["authorizations", "execution_authorized"], True))
    dec_fail("external_reputation_upload_authorized=true",
             setpath(["authorizations", "external_reputation_upload_authorized"], True))
    dec_fail("squash do PR #50 incorreto",
             setpath(["integration_ref", "squash_commit"], "0" * 40))
    dec_fail("precondition.gate_2_outcome != PASS", setpath(["precondition", "gate_2_outcome"], "STOPPED"))
    dec_fail("conditions insuficientes", lambda r: r.__setitem__("conditions", r["conditions"][:5]))
    dec_fail("propriedade inesperada", lambda r: r.__setitem__("x", 1))

    # ---------- Negativos: EVIDENCIA (estrutura invalidada) ----------
    ev_fail("outcome != EVIDENCE_INVALIDATED_PENDING_REPEAT", setpath(["outcome"], "COMPLETED_PASS"))
    ev_fail("status != outcome", setpath(["status"], "COMPLETED_PASS"))
    ev_fail("gate.id incorreto", setpath(["gate", "id"], 4))

    # (1) blob OID incorreto; (2) SHA-256 incorreto; (3) tamanho incorreto
    ev_fail("blob OID (git hash-object) incorreto",
            setpath(["identity_reconfirmation", "git_blob_oid_git_hash_object"], "4" * 40))
    ev_fail("SHA-256 divergente do GATE 2",
            setpath(["identity_reconfirmation", "sha256_local"], "a" * 64))
    ev_fail("SHA-256 = Git OID (confusao)",
            setpath(["identity_reconfirmation", "sha256_local"], "c853da42d18dfe090b4e941b435d989311faf3dc"))
    ev_fail("tamanho observado divergente",
            setpath(["identity_reconfirmation", "size_bytes_observed"], 999))

    # D1 — semantica de leitura estatica
    ev_fail("campo ambiguo 'opened' presente",
            setpath(["identity_reconfirmation", "opened"], False))
    ev_fail("file_read_for_static_inspection=false",
            setpath(["identity_reconfirmation", "file_read_for_static_inspection"], False))
    ev_fail("launched=true", setpath(["identity_reconfirmation", "launched"], True))
    ev_fail("executed=true", setpath(["identity_reconfirmation", "executed"], True))
    ev_fail("loaded_as_executable=true", setpath(["identity_reconfirmation", "loaded_as_executable"], True))
    ev_fail("materialized_file_count=2", setpath(["identity_reconfirmation", "materialized_file_count"], 2))
    ev_fail("temporary_dir_outside_repo=false",
            setpath(["identity_reconfirmation", "temporary_dir_outside_repo"], False))

    # D2 — size_of_optional_header == magic apresentado como medicao confirmada
    ev_fail("soh=267 apresentado como medicao confirmada (D2)",
            setpath(["pe_identity_observed", "size_of_optional_header_status"], "MEASURED_CONFIRMED"))
    ev_fail("pe_valid_status afirmado (nao pendente)",
            setpath(["pe_identity_observed", "pe_valid_status"], "VALID"))
    ev_fail("pe_valid afirmado como fato",
            setpath(["pe_identity_observed", "pe_valid"], True))
    ev_fail("produced_by incorreto",
            setpath(["pe_identity_observed", "produced_by"], "REVIEWED_PARSER"))
    ev_fail("version_info_status afirmado",
            setpath(["pe_identity_observed", "version_info_status"], "PRESENT"))
    ev_fail("original_filename preservado como fato",
            setpath(["pe_identity_observed", "original_filename"], "WARP.exe"))
    ev_fail("reconfirmation_required=false (PE)",
            setpath(["pe_identity_observed", "reconfirmation_required"], False))

    # Assinatura observada
    ev_fail("authenticode determination_status afirmado",
            setpath(["authenticode_observed", "determination_status"], "ABSENT_CONFIRMED"))
    ev_fail("authenticode reconfirmation_required=false",
            setpath(["authenticode_observed", "reconfirmation_required"], False))
    ev_fail("cryptographic_verification fora do enum",
            setpath(["authenticode_observed", "cryptographic_verification"], "MAGICAMENTE_VALIDA"))

    # Semantica presenca/validade/confianca/seguranca
    ev_fail("afirmacao de arquivo seguro (semantica)",
            setpath(["signature_semantics", "not_equal_file_safe"], False))
    ev_fail("assinatura ausente = malware (semantica)",
            setpath(["signature_semantics", "absence_not_equal_malware"], False))
    ev_fail("timestamp tratado como confiavel (semantica)",
            setpath(["signature_semantics", "timestamp_not_trusted"], False))

    # Inspetor revisavel
    ev_fail("reviewed_parser executado sobre o WARP.exe",
            setpath(["reviewed_parser", "run_on_warp_exe"], True))
    ev_fail("reviewed_parser executa/carrega PE",
            setpath(["reviewed_parser", "executes_or_loads_pe"], True))

    # D4 — ferramenta disponivel x invocada
    ev_fail("openssl invoked=false com exit_code nao nulo",
            setpath(["tools", 3, "exit_code"], 0))
    ev_fail("gh invoked=true com exit_code null",
            setpath(["tools", 0, "exit_code"], None))
    ev_fail("openssl invoked=false com completed=true",
            setpath(["tools", 3, "completed"], True))

    # Revisao corretiva / execucao original
    ev_fail("nova materializacao declarada",
            setpath(["corrective_review", "new_materialization_performed"], True))
    ev_fail("nova execucao declarada",
            setpath(["corrective_review", "new_execution_performed"], True))
    ev_fail("reuso de timestamps como nova execucao",
            setpath(["corrective_review", "reused_prior_timestamps_as_new_run"], True))
    ev_fail("finding D2 removido",
            lambda e: e["corrective_review"].__setitem__(
                "findings", [f for f in e["corrective_review"]["findings"] if f["id"] != "D2"]))
    ev_fail("original_execution nao marcado como superseded",
            setpath(["original_execution", "superseded_by_corrective_review"], False))
    ev_fail("timestamp fora de ordem (start>finish)",
            setpath(["original_execution", "started_at"], "2026-08-03T23:59:59Z"))

    # Seguranca / fatos preservados
    ev_fail("temporary_file_removed=false", setpath(["security_assertions", "temporary_file_removed"], False))
    ev_fail("no_network_after_fetch=false", setpath(["security_assertions", "no_network_after_fetch"], False))
    ev_fail("no_new_execution_performed=false", setpath(["security_assertions", "no_new_execution_performed"], False))
    ev_fail("no_ragexe_access=false", setpath(["security_assertions", "no_ragexe_access"], False))
    ev_fail("gate_4_authorized=true (evidencia)", setpath(["security_assertions", "gate_4_authorized"], True))
    ev_fail("binary_versioned=true", setpath(["security_assertions", "binary_versioned"], True))
    ev_fail("preserved sha256 do GATE 2 incorreto",
            setpath(["preserved_gate_2_facts", "artifact_sha256"], "b" * 64))
    ev_fail("preserved blob OID incorreto",
            setpath(["preserved_gate_2_facts", "artifact_blob_oid"], "c" * 40))

    # Refs / integracao / extras
    ev_fail("reviewed_parser_ref inexistente",
            setpath(["reviewed_parser_ref", "path"], "scripts/nao-existe.py"))
    ev_fail("gate_2_evidence_ref inexistente",
            setpath(["gate_2_evidence_ref", "path"], "client/warp-audit/evidence/nao-existe.json"))
    ev_fail("integration_ref squash incorreto",
            setpath(["integration_ref", "squash_commit"], "0" * 40))
    ev_fail("upstream commit divergente", setpath(["upstream_expected", "commit_oid"], "1" * 40))
    ev_fail("propriedade inesperada", lambda e: e.__setitem__("x", 1))

    def add_download(ev):
        ev["notes"] = ev["notes"] + " curl https://x/WARP.exe"
    ev_fail("comando de download embutido", add_download)
    def add_exec(ev):
        ev["notes"] = ev["notes"] + " executar WARP.exe"
    ev_fail("comando de execucao embutido", add_exec)

    # (15) divergencia com os identificadores do GATE 2
    g2e_diff = copy.deepcopy(gate2_evidence)
    g2e_diff["integrity"]["sha256_local"] = "b" * 64
    ev_fail("SHA-256 diverge do GATE 2 (cross-check)", lambda e: None, g2e=g2e_diff)
    # cross-check: decisao do GATE 3 nao autoriza
    g3_bad = copy.deepcopy(base_dec)
    g3_bad["authorizations"]["gate_3_authorized"] = False
    ev_fail("decisao do GATE 3 nao autoriza", lambda e: None, g3=g3_bad)

    # ================= Repeticao corretiva (2P-E-C3-R2/R3/R4) =================
    import struct as _struct, tempfile as _tempfile, shutil as _shutil
    rd_schema = load_json(os.path.join(SCHEMA_DIR, "binary-audit-gate-03-corrective-repeat-decision-record-real.schema.json"))
    pass_schema = load_json(os.path.join(SCHEMA_DIR, "binary-audit-gate-03-corrective-repeat-pass-evidence.schema.json"))
    fail_schema = load_json(os.path.join(SCHEMA_DIR, "binary-audit-gate-03-corrective-repeat-fail-evidence.schema.json"))
    stopped_schema = load_json(os.path.join(SCHEMA_DIR, "binary-audit-gate-03-corrective-repeat-stopped-evidence.schema.json"))

    inspspec = importlib.util.spec_from_file_location("insp_r4", os.path.join(SCRIPTS_DIR, "inspect-warp-pe-identity.py"))
    insp = importlib.util.module_from_spec(inspspec); inspspec.loader.exec_module(insp)

    def _blob(rel):
        with open(os.path.join(REPO_ROOT, rel), "rb") as fh:
            return mod.git_blob_oid_for_bytes(fh.read())
    PARSER_OID = _blob("scripts/inspect-warp-pe-identity.py")
    TEST_OID = _blob("scripts/test-warp-pe-identity.py")
    COMMIT = "b" * 40

    def _fixture_5sec():
        dos = bytearray(0x40); dos[0:2] = b"MZ"; _struct.pack_into("<I", dos, 0x3C, 0x40)
        coff = bytearray(20); _struct.pack_into("<H", coff, 0, 0x014c); _struct.pack_into("<H", coff, 2, 5)
        _struct.pack_into("<H", coff, 16, 0xE0); _struct.pack_into("<H", coff, 18, 0x0102)
        opt = bytearray(0xE0); _struct.pack_into("<H", opt, 0, 0x010b)
        _struct.pack_into("<I", opt, 32, 0x1000); _struct.pack_into("<I", opt, 36, 0x200)
        _struct.pack_into("<I", opt, 60, 1024); _struct.pack_into("<H", opt, 68, 2); _struct.pack_into("<I", opt, 92, 16)
        h = bytes(dos) + b"PE\x00\x00" + bytes(coff) + bytes(opt) + b"\x00" * 200
        return h + b"\x00" * (1024 - len(h))
    PO = insp.inspect(_fixture_5sec())
    PO_RAW = mod._canonical_parser_output_bytes(PO)
    PO_SHA = mod._sha256_hex(PO_RAW)
    PO_NAME = "binary-audit-gate-03-corrective-repeat-parser-output-2026-09-01.json"
    PO_PATH = "client/warp-audit/evidence/" + PO_NAME

    DEC_REF = {"path": "client/warp-audit/decisions/binary-audit-gate-03-decision-record-2026-08-03.json"}
    INVAL_REF = {"path": "client/warp-audit/evidence/binary-audit-gate-03-identity-signature-evidence-2026-08-03.json"}
    PARSER_REF = {"path": "scripts/inspect-warp-pe-identity.py"}
    TESTREF = {"path": "scripts/test-warp-pe-identity.py"}
    INTEG = {"pr": 50, "squash_commit": "6ab37b2a7ae65fd6b4fdf184759b345cf9ce4bd6", "base_branch": "dev"}
    SHA = "345f3464ee72a60afc97bde0773410f47348a00d8629182fe52741c5f1a42874"
    BLOB = "c853da42d18dfe090b4e941b435d989311faf3dc"

    def make_repeat_decision():
        return {
            "schema_version": 1, "project": "WARP", "stage": "2P-E-C3-REPEAT",
            "record_type": "binary-audit-gate-03-corrective-repeat-human-decision-real",
            "status": "AUTHORIZED_FOR_SINGLE_GATE", "note": "sintetico",
            "original_decision_ref": DEC_REF, "original_invalidated_evidence_ref": INVAL_REF,
            "r1_review_ref": INVAL_REF, "reviewed_parser_ref": PARSER_REF,
            "reviewed_parser_test_ref": TESTREF, "integration_ref": INTEG,
            "reviewed_parser_commit": COMMIT, "reviewed_parser_git_blob_oid": PARSER_OID,
            "reviewed_parser_test_git_blob_oid": TEST_OID,
            "gate": {"id": 3, "name": "IDENTITY_AND_SIGNATURE"},
            "decider": "BrunoMNoronha", "role": "Responsavel tecnico do FaithRO",
            "authority": "Responsavel tecnico do FaithRO", "channel": "Claude Code",
            "date": "2026-08-03", "decision": "AUTHORIZE_CORRECTIVE_REPEAT_GATE_3",
            "justification": "sintetico", "authorized_scope": "sintetico",
            "materialization_scope": {
                "repository_full_name": "Neo-Mind/WARP", "repository_visibility": "PUBLIC",
                "expected_branch": "rock_win32", "commit_oid": "9b1173e9e4e135c68e150704f01186ab5e763acd",
                "tree_oid": "1aebae06d5c71a145afc35cc72fcf5c210a08758", "artifact_path": "win32/WARP.exe",
                "artifact_blob_oid": BLOB, "artifact_blob_oid_algorithm": "GIT_OBJECT_ID",
                "artifact_blob_size": 1137152, "max_files": 1, "network_scope": "GITHUB_OFFICIAL_ONLY"},
            "repeat_scope": {"exactly_one_repeat": True, "repeat_index": 1},
            "precondition": {"gate_2_outcome": "COMPLETED_PASS", "original_evidence_invalidated": True},
            "allowed_methods": ["rematerializar e inspecionar com o parser revisado"],
            "prohibited_actions": ["executar", "GATE 4", "VPS", "Ragexe"],
            "conditions": [{"n": i, "text": f"cond {i}"} for i in range(1, 16)],
            "authorizations": {
                "human_decision_required": True, "human_decision_received": True, "gate_selected": True,
                "gate_3_corrective_repeat_authorized": True, "temporary_materialization_authorized": True,
                "local_hashing_authorized": True, "static_identity_inspection_authorized": True,
                "authenticode_inspection_authorized": True, "gate_4_authorized": False,
                "execution_authorized": False, "dynamic_analysis_authorized": False,
                "external_reputation_upload_authorized": False, "network_validation_authorized": False,
                "sandbox_creation_authorized": False, "client_copy_provision_authorized": False,
                "client_modification_authorized": False, "patch_review_authorized": False,
                "patch_application_authorized": False, "client_preparation_authorized": False,
                "test_account_authorized": False, "first_login_authorized": False,
                "vps_access_authorized": False, "distribution_authorized": False,
                "second_repeat_authorized": False},
            "execution_state": "AUTHORIZED_NOT_STARTED", "rollback": "sintetico", "notes": "sintetico",
        }

    def make_repeat_pass_evidence():
        poct = PO["certificate_table"]
        return {
            "schema_version": 1, "project": "WARP", "stage": "2P-E-C3-REPEAT",
            "record_type": "binary-audit-gate-03-corrective-repeat-pass-evidence-real",
            "status": "COMPLETED_PASS", "outcome": "COMPLETED_PASS",
            "gate": {"id": 3, "name": "IDENTITY_AND_SIGNATURE"},
            "original_invalidated_evidence_ref": INVAL_REF, "corrective_repeat_decision_ref": DEC_REF,
            "reviewed_parser_ref": PARSER_REF, "reviewed_parser_commit": COMMIT,
            "reviewed_parser_git_blob_oid": PARSER_OID, "reviewed_parser_test_ref": TESTREF,
            "reviewed_parser_test_git_blob_oid": TEST_OID,
            "reviewed_parser_output_ref": {"path": PO_PATH}, "reviewed_parser_output_sha256": PO_SHA,
            "parser_execution": {"parser_invoked": True, "parser_completed": True, "parser_output_produced": True},
            "integration_ref": INTEG,
            "execution": {
                "gate_3_repeat_started": True, "gate_3_repeat_completed": True, "execution_state": "COMPLETED",
                "started_at": "2026-09-01T10:00:00.000Z", "finished_at": "2026-09-01T10:00:01.000Z",
                "cleanup_at": "2026-09-01T10:00:02.000Z", "operator": "agente FaithRO",
                "method": "GITHUB_OFFICIAL_GIT_DATA_API_BLOB_BY_OID", "network_scope": "GITHUB_OFFICIAL_ONLY",
                "timestamps_precision": "reais"},
            "upstream_expected": {
                "repository_full_name": "Neo-Mind/WARP", "expected_branch": "rock_win32",
                "commit_oid": "9b1173e9e4e135c68e150704f01186ab5e763acd",
                "tree_oid": "1aebae06d5c71a145afc35cc72fcf5c210a08758", "artifact_path": "win32/WARP.exe",
                "artifact_blob_oid": BLOB, "artifact_blob_size": 1137152},
            "identity_reconfirmation": {
                "materialized_file_count": 1, "temporary_dir_outside_repo": True,
                "size_bytes_observed": 1137152, "size_match": True, "git_blob_oid_computed": BLOB,
                "git_blob_oid_match": True, "sha256_local": SHA, "sha256_match": True,
                "identity_matches_gate_2": True, "file_read_for_static_inspection": True,
                "launched": False, "executed": False, "loaded_as_executable": False},
            "pe_identity": {
                "produced_by": "REVIEWED_VERSIONED_PARSER", "pe_format": PO["pe_format"],
                "size_of_optional_header": PO["size_of_optional_header"],
                "number_of_sections": PO["number_of_sections"], "size_of_headers": PO["size_of_headers"],
                "executable_image_flag_present": True, "pe_headers_structurally_parseable": True,
                "full_pe_validation_performed": False},
            "certificate_table": {
                "produced_by": "REVIEWED_VERSIONED_PARSER", "present": poct["present"],
                "structurally_parseable": True, "entry_count": poct["entry_count"],
                "first_field_is_file_offset_not_rva": True},
            "signature_semantics": {
                "signature_present_means_present_only": True, "presence_not_equal_valid": True,
                "valid_not_equal_trusted": True, "trusted_not_equal_current_certificate": True,
                "timestamp_not_trusted": True, "not_equal_file_safe": True, "absence_not_equal_malware": True},
            "reviewed_parser": {
                "path": "scripts/inspect-warp-pe-identity.py", "test_path": "scripts/test-warp-pe-identity.py",
                "git_blob_oid": PARSER_OID, "stdlib_only": True, "network_access": False,
                "executes_or_loads_pe": False, "run_on_warp_exe": True},
            "security_assertions": {
                "no_execution_performed": True, "no_dynamic_analysis_performed": True, "no_sandbox_created": True,
                "no_wine_or_vm_load": True, "no_network_after_fetch": True, "no_external_service_upload": True,
                "no_gate4_inspection_performed": True, "no_ragexe_access": True, "no_vps_access": True,
                "temporary_file_removed": True, "temporary_dir_removed": True, "binary_versioned": False,
                "gate_4_authorized": False},
            "preserved_gate_2_facts": {"artifact_blob_oid": BLOB, "artifact_blob_size": 1137152, "artifact_sha256": SHA},
            "findings": ["s"], "limitations": ["a", "b", "c"], "rollback": "s", "notes": "s",
        }

    def make_repeat_fail_evidence(invoked=False, completed=False, produced=False):
        ev = {
            "schema_version": 1, "project": "WARP", "stage": "2P-E-C3-REPEAT",
            "record_type": "binary-audit-gate-03-corrective-repeat-fail-evidence-real",
            "status": "COMPLETED_FAIL", "outcome": "COMPLETED_FAIL",
            "gate": {"id": 3, "name": "IDENTITY_AND_SIGNATURE"},
            "original_invalidated_evidence_ref": INVAL_REF, "corrective_repeat_decision_ref": DEC_REF,
            "reviewed_parser_ref": PARSER_REF, "reviewed_parser_commit": COMMIT,
            "reviewed_parser_git_blob_oid": PARSER_OID, "reviewed_parser_test_ref": TESTREF,
            "reviewed_parser_test_git_blob_oid": TEST_OID, "integration_ref": INTEG,
            "parser_execution": {"parser_invoked": invoked, "parser_completed": completed,
                                 "parser_output_produced": produced},
            "failure": {"category": "SHA256_MISMATCH", "reason": "SHA divergente",
                        "identity_matches_gate_2": False, "cleanup_attempted": True},
            "reviewed_parser": {"path": "scripts/inspect-warp-pe-identity.py", "git_blob_oid": PARSER_OID,
                                "executes_or_loads_pe": False, "run_on_warp_exe": invoked},
            "security_assertions": {"no_execution_performed": True, "no_gate4_inspection_performed": True,
                                    "no_ragexe_access": True, "no_vps_access": True, "binary_versioned": False,
                                    "gate_4_authorized": False},
            "findings": ["falha"], "limitations": ["a"], "rollback": "s", "notes": "s",
        }
        if produced:
            ev["reviewed_parser_output_ref"] = {"path": PO_PATH}
            ev["reviewed_parser_output_sha256"] = PO_SHA
        return ev

    # Atalho: POST_OUTPUT_FAIL valido (true/true/true) com saida presa.
    def make_repeat_fail_post_output():
        return make_repeat_fail_evidence(invoked=True, completed=True, produced=True)

    def make_repeat_stopped_evidence():
        return {
            "schema_version": 1, "project": "WARP", "stage": "2P-E-C3-REPEAT",
            "record_type": "binary-audit-gate-03-corrective-repeat-stopped-evidence-real",
            "status": "STOPPED", "outcome": "STOPPED",
            "gate": {"id": 3, "name": "IDENTITY_AND_SIGNATURE"},
            "original_invalidated_evidence_ref": INVAL_REF, "corrective_repeat_decision_ref": DEC_REF,
            "reviewed_parser_ref": PARSER_REF, "reviewed_parser_test_ref": TESTREF, "integration_ref": INTEG,
            "stop": {"category": "OPERATOR_STOP_PATH", "reason": "operador interrompeu",
                     "stage_when_stopped": "BEFORE_MATERIALIZATION", "materialization_started": False,
                     "parser_invoked": False, "parser_output_produced": False, "cleanup_required": False,
                     "cleanup_attempted": False, "cleanup_completed": True, "gate_3_repeat_completed": False},
            "reviewed_parser": {"path": "scripts/inspect-warp-pe-identity.py", "run_on_warp_exe": False},
            "security_assertions": {"no_execution_performed": True, "no_gate4_inspection_performed": True,
                                    "no_ragexe_access": True, "no_vps_access": True, "binary_versioned": False,
                                    "gate_4_authorized": False},
            "findings": ["stop"], "limitations": ["a"], "rollback": "s", "notes": "s",
        }

    def run_rd(rec):
        errs = []; mod.validate_gate3_repeat_decision(rec, rd_schema, "d.json", errs); return errs

    def run_pass(ev, dec=None, raw="AUTO", path="AUTO", name="AUTO"):
        errs = []
        mod.validate_gate3_repeat_evidence(
            ev, pass_schema, make_repeat_decision() if dec is None else dec, "pass.json", errs,
            parser_output_raw=(PO_RAW if raw == "AUTO" else raw),
            parser_output_path=(PO_PATH if path == "AUTO" else path),
            present_output_name=(PO_NAME if name == "AUTO" else name))
        return errs

    def run_fail(ev, raw=None, path="AUTO", name="AUTO"):
        errs = []
        # Espelha o orquestrador: quando ha saida, o caminho/nome reais sao fornecidos.
        if path == "AUTO":
            path = PO_PATH if raw is not None else None
        if name == "AUTO":
            name = PO_NAME if raw is not None else None
        mod.validate_gate3_repeat_evidence(ev, fail_schema, make_repeat_decision(), "fail.json", errs,
                                           parser_output_raw=raw, parser_output_path=path,
                                           present_output_name=name)
        return errs

    def run_stopped(ev, raw=None):
        errs = []
        mod.validate_gate3_repeat_evidence(ev, stopped_schema, make_repeat_decision(), "stop.json", errs,
                                           parser_output_raw=raw)
        return errs

    # ----- Positivos -----
    ok("repeticao: decisao integra", run_rd(make_repeat_decision()))
    ok("repeticao: PASS integro", run_pass(make_repeat_pass_evidence()))
    # Estados FAIL validos (14) PRE_PARSER, (15) PARSER_ERROR_WITHOUT_OUTPUT, (16) POST_OUTPUT.
    ok("repeticao: FAIL PRE_PARSER (false/false/false, sem saida)",
       run_fail(make_repeat_fail_evidence()))
    ok("repeticao: FAIL PARSER_ERROR (true/false/false, sem saida)",
       run_fail(make_repeat_fail_evidence(invoked=True)))
    ok("repeticao: FAIL POST_OUTPUT (true/true/true, saida presa)",
       run_fail(make_repeat_fail_post_output(), raw=PO_RAW))
    ok("repeticao: STOPPED antes da materializacao", run_stopped(make_repeat_stopped_evidence()))

    def rd_fail(label, mutate):
        rec = copy.deepcopy(make_repeat_decision()); mutate(rec); bad(label, run_rd(rec))

    rd_fail("RD: gate_4_authorized=true", setpath(["authorizations", "gate_4_authorized"], True))
    rd_fail("RD: segunda repeticao", setpath(["authorizations", "second_repeat_authorized"], True))
    rd_fail("RD: repeat_index!=1", setpath(["repeat_scope", "repeat_index"], 2))
    rd_fail("RD: OID do parser divergente", setpath(["reviewed_parser_git_blob_oid"], "a" * 40))
    rd_fail("RD: OID dos testes divergente", setpath(["reviewed_parser_test_git_blob_oid"], "b" * 40))
    rd_fail("RD: commit malformado", setpath(["reviewed_parser_commit"], "nothex"))

    def pass_fail(label, mutate, **kw):
        ev = copy.deepcopy(make_repeat_pass_evidence()); mutate(ev); bad(label, run_pass(ev, **kw))

    pass_fail("PASS: gate_4_authorized=true", setpath(["security_assertions", "gate_4_authorized"], True))
    pass_fail("PASS: identidade != GATE 2", setpath(["identity_reconfirmation", "sha256_local"], "e" * 64))
    pass_fail("PASS: run_on_warp_exe false", setpath(["reviewed_parser", "run_on_warp_exe"], False))
    pass_fail("PASS: OID dos testes divergente", setpath(["reviewed_parser_test_git_blob_oid"], "c" * 40))
    pass_fail("PASS: commit diverge da decisao", setpath(["reviewed_parser_commit"], "d" * 40))
    pass_fail("PASS: campo pe_identity diverge da saida", setpath(["pe_identity", "size_of_headers"], 4096))
    pass_fail("PASS: sem saida", lambda e: None, raw=None)
    pass_fail("PASS: ref aponta para arquivo diferente",
              setpath(["reviewed_parser_output_ref", "path"], "client/warp-audit/evidence/outro.json"))
    pass_fail("PASS: nome/data da saida divergente", lambda e: None,
              name="binary-audit-gate-03-corrective-repeat-parser-output-2099-01-01.json")
    # bytes reais diferentes (hash correto sobre canonica, mas raw diferente)
    bad("PASS: espaco extra", run_pass(make_repeat_pass_evidence(), raw=PO_RAW[:-1] + b" \n"))
    bad("PASS: newline extra", run_pass(make_repeat_pass_evidence(), raw=PO_RAW + b"\n"))
    bad("PASS: newline ausente", run_pass(make_repeat_pass_evidence(), raw=PO_RAW.rstrip(b"\n")))
    bad("PASS: CRLF", run_pass(make_repeat_pass_evidence(), raw=PO_RAW.replace(b"\n", b"\r\n")))
    bad("PASS: BOM", run_pass(make_repeat_pass_evidence(), raw=b"\xef\xbb\xbf" + PO_RAW))
    # chave duplicada
    dup = PO_RAW[:-2] + b',\n  "file_size": 1\n' + PO_RAW[-2:]
    bad("PASS: chave duplicada", run_pass(make_repeat_pass_evidence(), raw=dup))

    def po_tampered(mutate):
        d = copy.deepcopy(PO); mutate(d)
        raw = mod._canonical_parser_output_bytes(d)
        ev = make_repeat_pass_evidence(); ev["reviewed_parser_output_sha256"] = mod._sha256_hex(raw)
        return ev, raw
    ev_t, raw_t = po_tampered(lambda d: d.__setitem__("x_extra", 1))
    bad("PASS: campo adicional no topo da saida", run_pass(ev_t, raw=raw_t))
    ev_t, raw_t = po_tampered(lambda d: d["section_table"].__setitem__("x", 1))
    bad("PASS: campo adicional em section_table", run_pass(ev_t, raw=raw_t))
    ev_t, raw_t = po_tampered(lambda d: d["certificate_table"].__setitem__("x", 1))
    bad("PASS: campo adicional em certificate_table", run_pass(ev_t, raw=raw_t))
    ev_t, raw_t = po_tampered(lambda d: d.__setitem__("note_padding", "secret= REGEX_TRIGGER_NOT_REAL"))
    bad("PASS: segredo em campo (schema fechado)", run_pass(ev_t, raw=raw_t))
    ev_t, raw_t = po_tampered(lambda d: d["certificate_table"].__setitem__("note_padding", "bCertificate DER blob"))
    bad("PASS: conteudo tipo bCertificate", run_pass(ev_t, raw=raw_t))

    def fail_fail(label, mutate, raw=None):
        ev = copy.deepcopy(make_repeat_fail_evidence()); mutate(ev); bad(label, run_fail(ev, raw=raw))
    fail_fail("FAIL: sem motivo", delpath(["failure", "reason"]))
    fail_fail("FAIL: cleanup nao tentado", setpath(["failure", "cleanup_attempted"], False))
    fail_fail("FAIL: gate_4=true", setpath(["security_assertions", "gate_4_authorized"], True))
    # produced=false mas com saida presente (10)
    bad("FAIL: produced=false com saida", run_fail(make_repeat_fail_evidence(), raw=PO_RAW))

    # ---- (R4.1-D1) Ligacao da saida presa por caminho/hash exatos no POST_OUTPUT ----
    def fail_post_mut(mutate):
        ev = copy.deepcopy(make_repeat_fail_post_output()); mutate(ev); return ev
    # (1) saida presente + referencia para OUTRO arquivo (nome diferente)
    bad("FAIL: ref para arquivo diferente",
        run_fail(fail_post_mut(setpath(["reviewed_parser_output_ref", "path"],
                                       "client/warp-audit/evidence/outro.json")), raw=PO_RAW))
    # (2) referencia com MESMO nome, porem em DIRETORIO diferente (nao basta endswith)
    bad("FAIL: ref mesmo nome, diretorio diferente",
        run_fail(fail_post_mut(setpath(["reviewed_parser_output_ref", "path"],
                                       "client/warp-audit/decisions/" + PO_NAME)), raw=PO_RAW))
    # (3) referencia presente, mas SEM o arquivo de saida (raw ausente)
    bad("FAIL: referencia sem arquivo (saida ausente)",
        run_fail(make_repeat_fail_post_output(), raw=None))
    # (4) arquivo de saida presente, mas SEM referencia
    bad("FAIL: arquivo sem referencia",
        run_fail(fail_post_mut(delpath(["reviewed_parser_output_ref"])), raw=PO_RAW))
    # (5) hash correto sobre os bytes, porem referencia apontando para outro arquivo
    bad("FAIL: hash correto + referencia errada",
        run_fail(fail_post_mut(setpath(["reviewed_parser_output_ref", "path"],
                                       "client/warp-audit/evidence/outro-nome.json")), raw=PO_RAW))

    # ---- (R4.1-D2) Estados impossiveis de parser_execution no COMPLETED_FAIL ----
    # (6) false/true/false
    bad("FAIL: estado impossivel false/true/false",
        run_fail(make_repeat_fail_evidence(invoked=False, completed=True, produced=False)))
    # (7) false/false/true
    bad("FAIL: estado impossivel false/false/true",
        run_fail(make_repeat_fail_evidence(invoked=False, completed=False, produced=True), raw=PO_RAW))
    # (8) false/true/true
    bad("FAIL: estado impossivel false/true/true",
        run_fail(make_repeat_fail_evidence(invoked=False, completed=True, produced=True), raw=PO_RAW))
    # (9) true/false/true
    bad("FAIL: estado impossivel true/false/true",
        run_fail(make_repeat_fail_evidence(invoked=True, completed=False, produced=True), raw=PO_RAW))

    # (10) PASS com qualquer estado != true/true/true
    pass_fail("PASS: parser_execution != true/true/true",
              setpath(["parser_execution", "parser_completed"], False))

    def stopped_fail(label, mutate, raw=None):
        ev = copy.deepcopy(make_repeat_stopped_evidence()); mutate(ev); bad(label, run_stopped(ev, raw=raw))
    stopped_fail("STOPPED: marcado COMPLETED (schema)", setpath(["outcome"], "COMPLETED_PASS"))
    stopped_fail("STOPPED: sem motivo", delpath(["stop", "reason"]))
    stopped_fail("STOPPED: gate_4=true", setpath(["security_assertions", "gate_4_authorized"], True))
    # (11) STOPPED com saida presente (orfa)
    bad("STOPPED: saida orfa", run_stopped(make_repeat_stopped_evidence(), raw=PO_RAW))
    # (12) STOPPED afirmando producao de saida
    stopped_fail("STOPPED: afirma producao de saida",
                 setpath(["stop", "parser_output_produced"], True))
    # (13) gate_4_authorized=true na decisao da repeticao
    rd_fail("RD: gate_4_authorized=true (bis)", setpath(["authorizations", "gate_4_authorized"], True))

    # ----- Orquestrador (maquina de estados) com diretorios temporarios -----
    def run_orch(dec_files, ev_files, po_files):
        tmp = _tempfile.mkdtemp(prefix="repeat-orch-")
        dd = os.path.join(tmp, "decisions"); ed = os.path.join(tmp, "evidence")
        os.makedirs(dd); os.makedirs(ed)
        for n, obj in dec_files:
            with open(os.path.join(dd, n), "w", encoding="utf-8") as fh: json.dump(obj, fh)
        for n, obj in ev_files:
            with open(os.path.join(ed, n), "w", encoding="utf-8") as fh: json.dump(obj, fh)
        for n, raw in po_files:
            with open(os.path.join(ed, n), "wb") as fh: fh.write(raw)
        old_d, old_e = mod.DECISIONS_DIR, mod.EVIDENCE_DIR
        mod.DECISIONS_DIR = dd; mod.EVIDENCE_DIR = ed
        errs = []
        try:
            mod.validate_gate3_repeat(errs)
        finally:
            mod.DECISIONS_DIR = old_d; mod.EVIDENCE_DIR = old_e
            _shutil.rmtree(tmp, ignore_errors=True)
        return errs

    DN = "binary-audit-gate-03-corrective-repeat-decision-record-2026-09-01.json"
    EN = "binary-audit-gate-03-corrective-repeat-evidence-2026-09-01.json"
    dec_obj = make_repeat_decision()
    pass_obj = make_repeat_pass_evidence()
    pass_obj["corrective_repeat_decision_ref"] = {"path": "client/warp-audit/decisions/" + DN}

    bad("ORCH: evidencia sem decisao", run_orch([], [(EN, pass_obj)], []))
    bad("ORCH: saida sem decisao", run_orch([], [], [(PO_NAME, PO_RAW)]))
    bad("ORCH: evidencia+saida sem decisao", run_orch([], [(EN, pass_obj)], [(PO_NAME, PO_RAW)]))
    bad("ORCH: decisao+saida sem evidencia", run_orch([(DN, dec_obj)], [], [(PO_NAME, PO_RAW)]))
    bad("ORCH: duas decisoes", run_orch([(DN, dec_obj), ("binary-audit-gate-03-corrective-repeat-decision-record-2026-09-02.json", dec_obj)], [], []))
    bad("ORCH: duas evidencias", run_orch([(DN, dec_obj)],
        [(EN, pass_obj), ("binary-audit-gate-03-corrective-repeat-evidence-2026-09-02.json", pass_obj)],
        [(PO_NAME, PO_RAW)]))
    bad("ORCH: duas saidas", run_orch([(DN, dec_obj)], [(EN, pass_obj)],
        [(PO_NAME, PO_RAW), ("binary-audit-gate-03-corrective-repeat-parser-output-2026-09-02.json", PO_RAW)]))
    ok("ORCH: autorizado sem execucao (so decisao)", run_orch([(DN, dec_obj)], [], []))
    ok("ORCH: cadeia PASS completa e integra", run_orch([(DN, dec_obj)], [(EN, pass_obj)], [(PO_NAME, PO_RAW)]))
    # (19) estado sem decisao/evidencia/saida continua valido
    ok("ORCH: vazio (sem repeticao)", run_orch([], [], []))

    # ---- Cadeia FAIL pelo orquestrador real (ligacao exata da saida) ----
    def fail_for_orch(base):
        ev = copy.deepcopy(base); ev["corrective_repeat_decision_ref"] = {"path": "client/warp-audit/decisions/" + DN}
        return ev
    fail_post_obj = fail_for_orch(make_repeat_fail_post_output())
    fail_pre_obj = fail_for_orch(make_repeat_fail_evidence())
    ok("ORCH: cadeia FAIL POST_OUTPUT integra",
       run_orch([(DN, dec_obj)], [(EN, fail_post_obj)], [(PO_NAME, PO_RAW)]))
    ok("ORCH: cadeia FAIL PRE_PARSER integra (sem saida)",
       run_orch([(DN, dec_obj)], [(EN, fail_pre_obj)], []))
    fail_wrong = fail_for_orch(make_repeat_fail_post_output())
    fail_wrong["reviewed_parser_output_ref"] = {"path": "client/warp-audit/evidence/outro.json"}
    bad("ORCH: FAIL POST_OUTPUT com ref para outro arquivo",
        run_orch([(DN, dec_obj)], [(EN, fail_wrong)], [(PO_NAME, PO_RAW)]))
    fail_samename = fail_for_orch(make_repeat_fail_post_output())
    fail_samename["reviewed_parser_output_ref"] = {"path": "client/warp-audit/decisions/" + PO_NAME}
    bad("ORCH: FAIL POST_OUTPUT com ref mesmo nome em diretorio diferente",
        run_orch([(DN, dec_obj)], [(EN, fail_samename)], [(PO_NAME, PO_RAW)]))

    print(f"\nResumo: {passed} teste(s) OK, {failed} falha(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"[ERRO] falha inesperada: {exc}")
        sys.exit(2)
