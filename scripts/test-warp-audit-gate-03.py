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

    print(f"\nResumo: {passed} teste(s) OK, {failed} falha(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"[ERRO] falha inesperada: {exc}")
        sys.exit(2)
