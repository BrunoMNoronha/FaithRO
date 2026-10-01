#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes positivos e negativos dos artefatos do GATE 2 (ETAPA 2P-E-C2-A):
registro de decisao (AUTHORIZE_GATE_2) e evidencia real de materializacao e
integridade local do artefato WARP.

Offline e sem dependencias externas: importa scripts/validate-warp-audit.py e exercita
validate_gate2_decision/validate_gate2_evidence contra os artefatos reais e contra
mutacoes invalidas. Nao acessa a rede, nao materializa binario, nao executa o WARP e
nao escreve arquivos. Criterio primario: codigo de saida / rejeicao correta.

Cobre, no minimo (FASE K do prompt 2P-E-C2-A):
  * positivos: decisao real e evidencia real;
  * negativos: decisao incorreta; squash do PR #49 incorreto; GATE 1 nao concluido;
    gate_2_authorized=false; gate_3_authorized=true; commit/tree/path/blob OID
    esperado/calculado/algoritmo/tamanho esperado/observado divergentes; SHA-256
    ausente/malformado/confundido com Git OID; zero ou >1 arquivo; arquivo temporario
    nao removido; archive/release/mirror/clone; arquivos adicionais; execucao; Wine/
    sandbox; inspecao estatica antecipada; analise dinamica; integracao no cliente;
    distribuicao; VPS; propriedade inesperada; PASS incompativel; timestamp fora de
    ordem; timestamp representativo declarado como preciso.
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

DEC_FILE = "binary-audit-gate-02-decision-record-2026-08-01.json"
EV_FILE = "binary-audit-gate-02-integrity-evidence-2026-08-01.json"


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
    dschema = load_json(os.path.join(SCHEMA_DIR, "binary-audit-gate-02-decision-record-real.schema.json"))
    eschema = load_json(os.path.join(SCHEMA_DIR, "binary-audit-gate-02-integrity-evidence.schema.json"))
    plan = load_json(os.path.join(AUDIT_DIR, "binary-audit-plan.example.json"))
    gate1_decision = load_json(os.path.join(DECISIONS_DIR, "binary-audit-gate-01-decision-record-2026-08-01.json"))
    gate0_evidence = load_json(os.path.join(EVIDENCE_DIR, "binary-audit-gate-00-provenance-evidence-2026-08-01.json"))
    base_dec = load_json(os.path.join(DECISIONS_DIR, DEC_FILE))
    base_ev = load_json(os.path.join(EVIDENCE_DIR, EV_FILE))

    passed = 0
    failed = 0

    def run_dec(rec, g1=None, g0=None):
        errs = []
        mod.validate_gate2_decision(rec, dschema, plan,
                                    gate1_decision if g1 is None else g1,
                                    gate0_evidence if g0 is None else g0,
                                    DEC_FILE, errs)
        return errs

    def run_ev(ev, g2=None, g1=None, g0=None):
        errs = []
        mod.validate_gate2_evidence(ev, eschema,
                                    base_dec if g2 is None else g2,
                                    gate1_decision if g1 is None else g1,
                                    gate0_evidence if g0 is None else g0,
                                    EV_FILE, errs)
        return errs

    def ok(label, errs):
        nonlocal passed, failed
        if errs:
            failed += 1
            print(f"[FALHA] (esperava OK) {label}: {len(errs)} erro(s)")
            for e in errs[:5]:
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
    ok("evidencia real integra", run_ev(copy.deepcopy(base_ev)))

    # ---------- Negativos: DECISAO ----------
    dec_fail("decisao incorreta", setpath(["decision"], "AUTHORIZE_MATERIALIZATION"))
    dec_fail("gate.id incorreto", setpath(["gate", "id"], 3))
    dec_fail("status incorreto", setpath(["status"], "GATE_PASSED"))
    dec_fail("execution_state incorreto", setpath(["execution_state"], "COMPLETED"))
    dec_fail("squash do PR #49 incorreto",
             setpath(["integration_ref", "squash_commit"], "0" * 40))
    dec_fail("pr incorreto", setpath(["integration_ref", "pr"], 48))
    dec_fail("gate_2_authorized=false", setpath(["authorizations", "gate_2_authorized"], False))
    dec_fail("gate_3_authorized=true", setpath(["authorizations", "gate_3_authorized"], True))
    dec_fail("static_inspection_authorized=true", setpath(["authorizations", "static_inspection_authorized"], True))
    dec_fail("execution_without_client_authorized=true", setpath(["authorizations", "execution_without_client_authorized"], True))
    dec_fail("distribution_authorized=true", setpath(["authorizations", "distribution_authorized"], True))
    dec_fail("vps_access_authorized=true", setpath(["authorizations", "vps_access_authorized"], True))
    dec_fail("commit divergente (escopo)", setpath(["materialization_scope", "commit_oid"], "1" * 40))
    dec_fail("blob OID divergente (escopo)", setpath(["materialization_scope", "artifact_blob_oid"], "2" * 40))
    dec_fail("max_files != 1 (escopo)", setpath(["materialization_scope", "max_files"], 2))
    dec_fail("precondition.gate_0_outcome != PASS", setpath(["precondition", "gate_0_outcome"], "STOPPED"))
    dec_fail("conditions insuficientes", lambda r: r.__setitem__("conditions", r["conditions"][:5]))
    dec_fail("propriedade inesperada", lambda r: r.__setitem__("x", 1))
    dec_fail("plan_ref inexistente", setpath(["plan_ref", "path"], "client/warp-audit/nao-existe.json"))
    # cross-check: GATE 1 nao concluido / nao autoriza materializacao
    g1_bad = copy.deepcopy(gate1_decision)
    g1_bad["authorizations"]["materialization_authorized"] = False
    dec_fail("GATE 1 nao autoriza materializacao", lambda r: None, g1=g1_bad)
    # cross-check: GATE 0 nao PASS
    g0_bad = copy.deepcopy(gate0_evidence)
    g0_bad["outcome"] = "STOPPED"
    dec_fail("GATE 0 nao esta COMPLETED_PASS", lambda r: None, g0=g0_bad)

    # ---------- Negativos: EVIDENCIA ----------
    ev_fail("outcome != COMPLETED_PASS", setpath(["outcome"], "COMPLETED_FAIL"))
    ev_fail("status != outcome", setpath(["status"], "STOPPED"))
    ev_fail("gate.id incorreto", setpath(["gate", "id"], 3))
    ev_fail("commit divergente", setpath(["upstream_expected", "commit_oid"], "1" * 40))
    ev_fail("tree divergente", setpath(["upstream_expected", "tree_oid"], "2" * 40))
    ev_fail("path divergente", setpath(["upstream_expected", "artifact_path"], "win64/WARP.exe"))
    ev_fail("blob OID esperado divergente", setpath(["upstream_expected", "artifact_blob_oid"], "3" * 40))
    ev_fail("algoritmo do Git OID incorreto", setpath(["integrity", "git_blob_oid_algorithm"], "SHA256"))
    ev_fail("Git OID calculado divergente", setpath(["integrity", "git_blob_oid_computed"], "4" * 40))
    ev_fail("Git OID match=false com PASS", setpath(["integrity", "git_blob_oid_match"], False))
    ev_fail("tamanho esperado divergente", setpath(["integrity", "expected_size"], 999))
    ev_fail("tamanho observado divergente", setpath(["integrity", "observed_size"], 999))
    ev_fail("size_match=false com PASS", setpath(["integrity", "size_match"], False))
    ev_fail("SHA-256 ausente", delpath(["integrity", "sha256_local"]))
    ev_fail("SHA-256 malformado", setpath(["integrity", "sha256_local"], "xyz"))
    ev_fail("SHA-256 = Git OID (confusao)", setpath(["integrity", "sha256_local"], "c853da42d18dfe090b4e941b435d989311faf3dc"))
    ev_fail("SHA-256 divergente do conteudo", setpath(["integrity", "sha256_local"], "a" * 64))
    ev_fail("sha256_is_not_git_oid=false", setpath(["integrity", "sha256_is_not_git_oid"], False))
    ev_fail("zero arquivos materializados", setpath(["materialization", "materialized_file_count"], 0))
    ev_fail("mais de um arquivo materializado", setpath(["materialization", "materialized_file_count"], 2))
    ev_fail("arquivo aberto", setpath(["materialization", "opened"], True))
    ev_fail("arquivo executado", setpath(["materialization", "executed"], True))
    ev_fail("temporary_file_removed=false", setpath(["security_assertions", "temporary_file_removed"], False))
    ev_fail("no_execution_performed=false", setpath(["security_assertions", "no_execution_performed"], False))
    ev_fail("no_static_inspection_performed=false", setpath(["security_assertions", "no_static_inspection_performed"], False))
    ev_fail("no_dynamic_analysis_performed=false", setpath(["security_assertions", "no_dynamic_analysis_performed"], False))
    ev_fail("no_sandbox_created=false (Wine/sandbox)", setpath(["security_assertions", "no_sandbox_created"], False))
    ev_fail("no_client_integration=false", setpath(["security_assertions", "no_client_integration"], False))
    ev_fail("no_distribution=false", setpath(["security_assertions", "no_distribution"], False))
    ev_fail("no_vps_access=false", setpath(["security_assertions", "no_vps_access"], False))
    ev_fail("no_clone_or_archive=false", setpath(["security_assertions", "no_clone_or_archive"], False))
    ev_fail("no_release_asset=false", setpath(["security_assertions", "no_release_asset"], False))
    ev_fail("no_mirror_or_third_party=false", setpath(["security_assertions", "no_mirror_or_third_party"], False))
    ev_fail("binary_versioned=true", setpath(["security_assertions", "binary_versioned"], True))
    ev_fail("gate_3_authorized=true (evidencia)", setpath(["security_assertions", "gate_3_authorized"], True))
    ev_fail("method fora do conjunto", setpath(["execution", "method"], "git clone"))
    ev_fail("network_scope invalido", setpath(["execution", "network_scope"], "ANY"))
    ev_fail("timestamp fora de ordem (start>finish)",
            setpath(["execution", "started_at"], "2026-08-01T23:59:59Z"))
    ev_fail("limpeza antes do fim (finish>cleanup)",
            setpath(["execution", "cleanup_at"], "2026-08-01T00:00:00Z"))
    ev_fail("propriedade inesperada", lambda e: e.__setitem__("x", 1))
    ev_fail("gate_0_evidence_ref inexistente",
            setpath(["gate_0_evidence_ref", "path"], "client/warp-audit/evidence/nao-existe.json"))

    def add_download(ev):
        ev["notes"] = ev["notes"] + " curl https://x/WARP.exe"
    ev_fail("comando de download embutido", add_download)
    def add_exec(ev):
        ev["notes"] = ev["notes"] + " executar WARP.exe"
    ev_fail("comando de execucao embutido", add_exec)

    # cross-check: decisao do GATE 2 nao autoriza
    g2_bad = copy.deepcopy(base_dec)
    g2_bad["authorizations"]["gate_2_authorized"] = False
    ev_fail("decisao do GATE 2 nao autoriza", lambda e: None, g2=g2_bad)

    print(f"\nResumo: {passed} teste(s) OK, {failed} falha(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"[ERRO] falha inesperada: {exc}")
        sys.exit(2)
