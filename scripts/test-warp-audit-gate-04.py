#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes positivos e negativos da CONVENCAO e da maquina de estados do GATE 4
(ETAPA 2P-E-C4-PREP), exercitando scripts/validate-warp-audit.py.

Constroi, em memoria, uma decisao e evidencias (PASS/FAIL/STOPPED) SINTETICAS validas e
mutacoes invalidas, alem da saida real do inventario (gerada pelo analisador revisado
sobre um PE SINTETICO). NAO cria arquivos reais do GATE 4, NAO materializa o WARP, NAO
acessa cliente/Ragexe/VPS/rede. Verifica que o validador:
  * aceita uma decisao/evidencia bem-formadas;
  * reprova gate_5 autorizado, gate_4_execution ausente, OIDs divergentes;
  * reprova PASS sem saida deterministica, STOPPED com saida e FAIL em estado impossivel;
  * prende a saida do inventario aos bytes exatos (BOM/CRLF/base64/chave duplicada).
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
SCHEMA_DIR = os.path.join(REPO_ROOT, "client", "warp-audit", "schemas")

SHA256_WARP = "345f3464ee72a60afc97bde0773410f47348a00d8629182fe52741c5f1a42874"
BLOB_WARP = "c853da42d18dfe090b4e941b435d989311faf3dc"


def load_module(fname, modname):
    path = os.path.join(SCRIPTS_DIR, fname)
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_json(name):
    with open(os.path.join(SCHEMA_DIR, name), "r", encoding="utf-8") as fh:
        return json.load(fh)


def make_decision(analyzer_oid, test_oid):
    auth = {k: True for k in (
        "human_decision_required", "human_decision_received", "gate_selected",
        "gate_3_completed", "temporary_materialization_authorized",
        "local_hashing_authorized", "static_inventory_authorized",
        "gate_4_authorized", "gate_4_execution_authorized")}
    auth.update({k: False for k in (
        "gate_5_authorized", "dynamic_analysis_authorized", "emulation_authorized",
        "unpacking_authorized", "execution_authorized",
        "external_reputation_upload_authorized", "network_validation_authorized",
        "sandbox_creation_authorized", "client_copy_provision_authorized",
        "client_modification_authorized", "patch_review_authorized",
        "patch_application_authorized", "client_preparation_authorized",
        "test_account_authorized", "first_login_authorized", "vps_access_authorized",
        "distribution_authorized")})
    return {
        "schema_version": 1, "project": "WARP", "stage": "2P-E-C4",
        "record_type": "binary-audit-gate-04-decision-record-real",
        "status": "AUTHORIZED_FOR_SINGLE_GATE",
        "gate": {"id": 4, "name": "STATIC_PE_INVENTORY"},
        "decision": "AUTHORIZE_GATE_4_EXECUTION",
        "execution_state": "AUTHORIZED_NOT_STARTED",
        "decider": "Mantenedor FaithRO", "role": "Mantenedor",
        "authority": "Responsavel tecnico do projeto", "channel": "Revisao de PR no GitHub",
        "date": "2026-08-10",
        "justification": "Autorizar exclusivamente a execucao do inventario PE estatico offline.",
        "conditions": [{"n": i + 1, "text": "condicao %d" % (i + 1)} for i in range(15)],
        "authorizations": auth,
        "materialization_scope": {
            "repository_full_name": "Neo-Mind/WARP",
            "commit_oid": "9b1173e9e4e135c68e150704f01186ab5e763acd",
            "tree_oid": "1aebae06d5c71a145afc35cc72fcf5c210a08758",
            "artifact_path": "win32/WARP.exe", "artifact_blob_oid": BLOB_WARP,
            "artifact_blob_oid_algorithm": "GIT_OBJECT_ID",
            "artifact_blob_size": 1137152, "max_files": 1,
            "network_scope": "GITHUB_OFFICIAL_ONLY"},
        "precondition": {"gate_3_completed": True, "gate_3_outcome": "COMPLETED_PASS"},
        "integration_ref": {"pr": 99, "squash_commit": "a" * 40, "base_branch": "dev"},
        "plan_ref": {"path": "client/warp-audit/binary-audit-plan.example.json"},
        "source_decision_ref": {"path": "client/warp-audit/decisions/core-path-decision-record-2026-07-31.json"},
        "prior_gate_decision_ref": {"path": "client/warp-audit/decisions/binary-audit-gate-03-corrective-repeat-decision-record-2026-08-03.json"},
        "gate_3_evidence_ref": {"path": "client/warp-audit/evidence/binary-audit-gate-03-corrective-repeat-evidence-2026-08-03.json"},
        "reviewed_analyzer_ref": {"path": "scripts/inspect-warp-pe-static.py"},
        "reviewed_analyzer_commit": "0" * 40,
        "reviewed_analyzer_git_blob_oid": analyzer_oid,
        "reviewed_analyzer_test_ref": {"path": "scripts/test-warp-pe-static.py"},
        "reviewed_analyzer_test_git_blob_oid": test_oid,
        "rollback": "reverter o squash em novo PR", "notes": "sem autorizacao transitiva",
    }


def make_pass_evidence(analyzer_oid, test_oid, out_sha, out_name):
    return {
        "schema_version": 1, "project": "WARP", "stage": "2P-E-C4",
        "record_type": "binary-audit-gate-04-pass-evidence-real",
        "status": "COMPLETED_PASS", "outcome": "COMPLETED_PASS",
        "gate": {"id": 4, "name": "STATIC_PE_INVENTORY"},
        "gate_4_decision_ref": {"path": "client/warp-audit/decisions/binary-audit-gate-04-decision-record-2026-08-10.json"},
        "reviewed_analyzer_ref": {"path": "scripts/inspect-warp-pe-static.py"},
        "reviewed_analyzer_commit": "0" * 40,
        "reviewed_analyzer_git_blob_oid": analyzer_oid,
        "reviewed_analyzer_test_ref": {"path": "scripts/test-warp-pe-static.py"},
        "reviewed_analyzer_test_git_blob_oid": test_oid,
        "reviewed_analyzer_output_ref": {"path": "client/warp-audit/evidence/" + out_name},
        "reviewed_analyzer_output_sha256": out_sha,
        "parser_execution": {"analyzer_invoked": True, "analyzer_completed": True,
                             "analyzer_output_produced": True},
        "execution": {"gate_4_started": True, "gate_4_completed": True,
                      "execution_state": "COMPLETED", "started_at": "2026-08-10T10:00:00",
                      "finished_at": "2026-08-10T10:01:00", "cleanup_at": "2026-08-10T10:02:00",
                      "operator": "Mantenedor", "method": "GITHUB_OFFICIAL_GIT_DATA_API_BLOB_BY_OID",
                      "network_scope": "GITHUB_OFFICIAL_ONLY"},
        "upstream_expected": {"repository_full_name": "Neo-Mind/WARP", "expected_branch": "rock_win32",
                              "commit_oid": "9b1173e9e4e135c68e150704f01186ab5e763acd",
                              "tree_oid": "1aebae06d5c71a145afc35cc72fcf5c210a08758",
                              "artifact_path": "win32/WARP.exe", "artifact_blob_oid": BLOB_WARP,
                              "artifact_blob_size": 1137152},
        "identity_reconfirmation": {"materialized_file_count": 1, "temporary_dir_outside_repo": True,
                                    "size_bytes_observed": 1137152, "size_match": True,
                                    "git_blob_oid_computed": BLOB_WARP, "git_blob_oid_match": True,
                                    "sha256_local": SHA256_WARP, "sha256_match": True,
                                    "identity_matches_gate_2": True,
                                    "file_read_for_static_inspection": True, "launched": False,
                                    "executed": False, "loaded_as_executable": False},
        "static_inventory_summary": {"produced_by": "REVIEWED_VERSIONED_ANALYZER", "pe_format": "PE32",
                                     "section_count": 5, "import_dll_count": 3, "export_present": False,
                                     "manifest_present": True, "requested_execution_level": "asInvoker",
                                     "signature_present": False, "overlay_present": False,
                                     "tls_callbacks_present": False, "relocations_present": True,
                                     "debug_directory_present": True},
        "reviewed_analyzer": {"path": "scripts/inspect-warp-pe-static.py",
                              "test_path": "scripts/test-warp-pe-static.py",
                              "git_blob_oid": analyzer_oid, "stdlib_only": True, "network_access": False,
                              "executes_or_loads_pe": False, "emulates_pe": False,
                              "unpacks_dynamically": False, "run_on_warp_exe": True},
        "security_assertions": {k: True for k in (
            "no_execution_performed", "no_dynamic_analysis_performed", "no_emulation_performed",
            "no_unpacking_performed", "no_sandbox_created", "no_wine_or_vm_load",
            "no_network_after_fetch", "no_external_service_upload", "no_gate5_inspection_performed",
            "no_ragexe_access", "no_client_access", "no_vps_access", "temporary_file_removed",
            "temporary_dir_removed")} | {"binary_versioned": False, "raw_bytes_versioned": False,
                                         "gate_5_authorized": False},
        "preserved_gate_3_facts": {"artifact_blob_oid": BLOB_WARP, "artifact_blob_size": 1137152,
                                   "artifact_sha256": SHA256_WARP},
        "findings": ["inventario estatico concluido"],
        "limitations": ["l1", "l2", "l3", "l4", "l5", "l6"],
        "rollback": "reverter o squash", "notes": "resultado significa apenas inventario concluido",
    }


def main():
    val = load_module("validate-warp-audit.py", "validate_warp_audit")
    analyzer = load_module("inspect-warp-pe-static.py", "inspect_warp_pe_static")
    builder = load_module("test-warp-pe-static.py", "test_warp_pe_static")

    with open(os.path.join(SCRIPTS_DIR, "inspect-warp-pe-static.py"), "rb") as fh:
        analyzer_oid = val.git_blob_oid_for_bytes(fh.read())
    with open(os.path.join(SCRIPTS_DIR, "test-warp-pe-static.py"), "rb") as fh:
        test_oid = val.git_blob_oid_for_bytes(fh.read())

    dschema = load_json(val.GATE4_DECISION_SCHEMA)
    pass_schema = load_json(val.GATE4_PASS_EVIDENCE_SCHEMA)
    fail_schema = load_json(val.GATE4_FAIL_EVIDENCE_SCHEMA)
    stopped_schema = load_json(val.GATE4_STOPPED_EVIDENCE_SCHEMA)

    # Saida real do inventario a partir de um PE sintetico.
    pe = builder.build_pe(imports=[("KERNEL32.dll", ["LoadLibraryA"], [])],
                          manifest=b'<x><requestedExecutionLevel level="asInvoker"/></x>')
    out_obj = analyzer.inspect(pe)
    out_raw = (json.dumps(out_obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    out_sha = val._sha256_hex(out_raw)
    out_name = "binary-audit-gate-04-static-inventory-output-2026-08-10.json"
    out_path = "client/warp-audit/evidence/" + out_name

    passed = 0
    failed = 0

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

    def run_dec(rec):
        e = []
        val.validate_gate4_decision(rec, dschema, "gate-04-decision.json", e)
        return e

    def run_ev(ev, schema, raw=None, name=None, path=None, decision=None):
        e = []
        val.validate_gate4_evidence(ev, schema, decision if decision is not None else make_decision(analyzer_oid, test_oid),
                                    "gate-04-evidence.json", e,
                                    output_raw=raw, present_output_name=name, output_path=path)
        return e

    # ===== Decisao positiva/negativa =====
    ok("decisao valida", run_dec(make_decision(analyzer_oid, test_oid)))
    d = make_decision(analyzer_oid, test_oid); d["authorizations"]["gate_5_authorized"] = True
    bad("decisao com gate_5 autorizado", run_dec(d))
    d = make_decision(analyzer_oid, test_oid); d["authorizations"]["gate_4_execution_authorized"] = False
    bad("decisao sem gate_4_execution", run_dec(d))
    d = make_decision(analyzer_oid, test_oid); d["reviewed_analyzer_git_blob_oid"] = "b" * 40
    bad("decisao com OID do analisador divergente", run_dec(d))
    d = make_decision(analyzer_oid, test_oid); d["precondition"]["gate_3_outcome"] = "STOPPED"
    bad("decisao sem pre-condicao GATE 3 PASS", run_dec(d))
    d = make_decision(analyzer_oid, test_oid); d["decider"] = "TODO"
    bad("decisao com placeholder no decisor", run_dec(d))
    d = make_decision(analyzer_oid, test_oid); d["conditions"] = d["conditions"][:14]
    bad("decisao com poucas condicoes", run_dec(d))

    # ===== Evidencia PASS positiva/negativa =====
    ok("PASS valido", run_ev(make_pass_evidence(analyzer_oid, test_oid, out_sha, out_name),
                             pass_schema, raw=out_raw, name=out_name, path=out_path))
    bad("PASS sem saida deterministica (output ausente)",
        run_ev(make_pass_evidence(analyzer_oid, test_oid, out_sha, out_name), pass_schema))
    ev = make_pass_evidence(analyzer_oid, test_oid, out_sha, out_name)
    ev["security_assertions"]["gate_5_authorized"] = True
    bad("PASS com gate_5 autorizado",
        run_ev(ev, pass_schema, raw=out_raw, name=out_name, path=out_path))
    ev = make_pass_evidence(analyzer_oid, test_oid, out_sha, out_name)
    ev["identity_reconfirmation"]["sha256_local"] = "f" * 64
    bad("PASS com identidade divergente do GATE 2",
        run_ev(ev, pass_schema, raw=out_raw, name=out_name, path=out_path))
    ev = make_pass_evidence(analyzer_oid, test_oid, "e" * 64, out_name)
    bad("PASS com SHA-256 da saida divergente",
        run_ev(ev, pass_schema, raw=out_raw, name=out_name, path=out_path))
    ev = make_pass_evidence(analyzer_oid, test_oid, out_sha, out_name)
    ev["reviewed_analyzer"]["run_on_warp_exe"] = False
    bad("PASS sem run_on_warp_exe",
        run_ev(ev, pass_schema, raw=out_raw, name=out_name, path=out_path))

    # ===== Saida do inventario: bytes exatos =====
    e = []; val.validate_gate4_output_raw(out_raw, out_sha, "out.json", e)
    ok("saida do inventario valida", e)
    e = []; val.validate_gate4_output_raw(b"\xef\xbb\xbf" + out_raw, out_sha, "out.json", e)
    bad("saida com BOM", e)
    e = []; val.validate_gate4_output_raw(out_raw.replace(b"\n", b"\r\n", 1), out_sha, "out.json", e)
    bad("saida com CRLF", e)
    e = []; val.validate_gate4_output_raw(out_raw + b"trailer", out_sha, "out.json", e)
    bad("saida com dados apos newline", e)

    # ===== Evidencia FAIL: estados fechados =====
    def make_fail(inv, comp, prod, with_output=False):
        ev = {
            "schema_version": 1, "project": "WARP", "stage": "2P-E-C4",
            "record_type": "binary-audit-gate-04-fail-evidence-real",
            "status": "COMPLETED_FAIL", "outcome": "COMPLETED_FAIL",
            "gate": {"id": 4, "name": "STATIC_PE_INVENTORY"},
            "gate_4_decision_ref": {"path": "client/warp-audit/decisions/binary-audit-gate-04-decision-record-2026-08-10.json"},
            "reviewed_analyzer_ref": {"path": "scripts/inspect-warp-pe-static.py"},
            "reviewed_analyzer_commit": "0" * 40,
            "reviewed_analyzer_git_blob_oid": analyzer_oid,
            "reviewed_analyzer_test_ref": {"path": "scripts/test-warp-pe-static.py"},
            "reviewed_analyzer_test_git_blob_oid": test_oid,
            "parser_execution": {"analyzer_invoked": inv, "analyzer_completed": comp,
                                 "analyzer_output_produced": prod},
            "failure": {"category": "PARSE", "reason": "PE truncado", "cleanup_attempted": True},
            "security_assertions": {"no_execution_performed": True, "no_gate5_inspection_performed": True,
                                    "no_ragexe_access": True, "no_vps_access": True,
                                    "gate_5_authorized": False},
            "findings": ["falhou"], "limitations": ["l1"], "rollback": "reverter",
            "notes": "falha",
        }
        if with_output:
            ev["reviewed_analyzer_output_ref"] = {"path": out_path}
            ev["reviewed_analyzer_output_sha256"] = out_sha
        return ev

    ok("FAIL PRE_ANALYZER (false/false/false)", run_ev(make_fail(False, False, False), fail_schema))
    ok("FAIL ANALYZER_ERROR (true/false/false)", run_ev(make_fail(True, False, False), fail_schema))
    bad("FAIL estado impossivel (false/true/false)", run_ev(make_fail(False, True, False), fail_schema))
    bad("FAIL estado impossivel (true/false/true)", run_ev(make_fail(True, False, True), fail_schema))
    ok("FAIL POST_OUTPUT (true/true/true) com saida",
       run_ev(make_fail(True, True, True, with_output=True), fail_schema,
              raw=out_raw, name=out_name, path=out_path))
    bad("FAIL sem saida mas com output_ref",
        run_ev(make_fail(True, False, False, with_output=True), fail_schema))

    # ===== Evidencia STOPPED =====
    def make_stopped(with_output=False):
        return {
            "schema_version": 1, "project": "WARP", "stage": "2P-E-C4",
            "record_type": "binary-audit-gate-04-stopped-evidence-real",
            "status": "STOPPED", "outcome": "STOPPED",
            "gate": {"id": 4, "name": "STATIC_PE_INVENTORY"},
            "gate_4_decision_ref": {"path": "client/warp-audit/decisions/binary-audit-gate-04-decision-record-2026-08-10.json"},
            "reviewed_analyzer_ref": {"path": "scripts/inspect-warp-pe-static.py"},
            "reviewed_analyzer_commit": "0" * 40,
            "reviewed_analyzer_git_blob_oid": analyzer_oid,
            "reviewed_analyzer_test_ref": {"path": "scripts/test-warp-pe-static.py"},
            "reviewed_analyzer_test_git_blob_oid": test_oid,
            "stop": {"category": "HUMAN", "reason": "interrompido", "stage_when_stopped": "pre-analise",
                     "gate_4_completed": False, "analyzer_invoked": False,
                     "analyzer_output_produced": False, "cleanup_required": False,
                     "cleanup_attempted": True, "cleanup_completed": True},
            "security_assertions": {"no_execution_performed": True, "no_gate5_inspection_performed": True,
                                    "no_ragexe_access": True, "no_vps_access": True,
                                    "gate_5_authorized": False},
            "findings": ["parado"], "limitations": ["l1"], "rollback": "reverter", "notes": "stop",
        }
    ok("STOPPED valido", run_ev(make_stopped(), stopped_schema))
    bad("STOPPED com saida presente",
        run_ev(make_stopped(), stopped_schema, raw=out_raw, name=out_name, path=out_path))

    print(f"\nResumo: {passed} teste(s) OK, {failed} falha(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"[ERRO] falha inesperada: {type(exc).__name__}: {exc}")
        sys.exit(2)
