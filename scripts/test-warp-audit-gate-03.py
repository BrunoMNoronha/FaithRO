#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes positivos e negativos dos artefatos do GATE 3 (ETAPA 2P-E-C3):
registro de decisao (AUTHORIZE_GATE_3) e evidencia real de identidade do PE e
assinatura Authenticode (inspecao estatica offline) do artefato WARP.

Offline e sem dependencias externas: importa scripts/validate-warp-audit.py e exercita
validate_gate3_decision/validate_gate3_evidence contra os artefatos reais e contra
mutacoes invalidas. Nao acessa a rede, nao materializa binario, nao executa o WARP e
nao escreve arquivos. Criterio primario: rejeicao correta.

Cobre, no minimo (FASE J do prompt 2P-E-C3):
  * positivos: decisao real e evidencia real;
  * negativos (15 obrigatorios): blob OID incorreto; SHA-256 incorreto; tamanho
    incorreto; gate_3_authorized=false com evidencia concluida; gate_4_authorized=true;
    execution_authorized=true; external_reputation_upload_authorized=true; afirmacao de
    'assinatura valida' sem evidencia da ferramenta; afirmacao de 'arquivo seguro'
    derivada apenas da assinatura; limpeza nao confirmada; mais de um arquivo
    materializado; caminho dentro da worktree; tentativa de rede; enum/condicao fora do
    conjunto fechado; divergencia com os identificadores do GATE 2.
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
    dec_fail("decisao incorreta", setpath(["decision"], "AUTHORIZE_GATE_2"))
    dec_fail("gate.id incorreto", setpath(["gate", "id"], 4))
    dec_fail("gate.name incorreto", setpath(["gate", "name"], "PE_STATIC_INVENTORY"))
    dec_fail("status incorreto", setpath(["status"], "GATE_PASSED"))
    dec_fail("execution_state incorreto", setpath(["execution_state"], "COMPLETED"))
    dec_fail("squash do PR #50 incorreto",
             setpath(["integration_ref", "squash_commit"], "0" * 40))
    dec_fail("pr incorreto", setpath(["integration_ref", "pr"], 49))
    # (4) gate_3_authorized=false
    dec_fail("gate_3_authorized=false", setpath(["authorizations", "gate_3_authorized"], False))
    # (5) gate_4_authorized=true
    dec_fail("gate_4_authorized=true", setpath(["authorizations", "gate_4_authorized"], True))
    # (6) execution_authorized=true
    dec_fail("execution_authorized=true", setpath(["authorizations", "execution_authorized"], True))
    # (7) external_reputation_upload_authorized=true
    dec_fail("external_reputation_upload_authorized=true",
             setpath(["authorizations", "external_reputation_upload_authorized"], True))
    dec_fail("dynamic_analysis_authorized=true",
             setpath(["authorizations", "dynamic_analysis_authorized"], True))
    dec_fail("network_validation_authorized=true",
             setpath(["authorizations", "network_validation_authorized"], True))
    dec_fail("vps_access_authorized=true", setpath(["authorizations", "vps_access_authorized"], True))
    # (1/3 no escopo) commit/blob/max_files divergentes
    dec_fail("commit divergente (escopo)", setpath(["materialization_scope", "commit_oid"], "1" * 40))
    dec_fail("blob OID divergente (escopo)", setpath(["materialization_scope", "artifact_blob_oid"], "2" * 40))
    dec_fail("max_files != 1 (escopo)", setpath(["materialization_scope", "max_files"], 2))
    dec_fail("precondition.gate_2_outcome != PASS", setpath(["precondition", "gate_2_outcome"], "STOPPED"))
    dec_fail("conditions insuficientes", lambda r: r.__setitem__("conditions", r["conditions"][:5]))
    dec_fail("propriedade inesperada", lambda r: r.__setitem__("x", 1))
    dec_fail("plan_ref inexistente", setpath(["plan_ref", "path"], "client/warp-audit/nao-existe.json"))
    # cross-check: GATE 2 nao autoriza materializacao / nao PASS
    g2d_bad = copy.deepcopy(gate2_decision)
    g2d_bad["authorizations"]["gate_2_authorized"] = False
    dec_fail("GATE 2 nao autoriza materializacao", lambda r: None, g2d=g2d_bad)
    g2e_bad = copy.deepcopy(gate2_evidence)
    g2e_bad["outcome"] = "STOPPED"
    dec_fail("GATE 2 nao esta COMPLETED_PASS", lambda r: None, g2e=g2e_bad)

    # ---------- Negativos: EVIDENCIA ----------
    ev_fail("outcome != COMPLETED_PASS", setpath(["outcome"], "COMPLETED_FAIL"))
    ev_fail("status != outcome", setpath(["status"], "STOPPED"))
    ev_fail("gate.id incorreto", setpath(["gate", "id"], 4))
    # (1) blob OID incorreto
    ev_fail("blob OID (git hash-object) incorreto",
            setpath(["identity_reconfirmation", "git_blob_oid_git_hash_object"], "4" * 40))
    ev_fail("blob OID (independente) incorreto",
            setpath(["identity_reconfirmation", "git_blob_oid_independent"], "5" * 40))
    ev_fail("git_blob_oid_match=false", setpath(["identity_reconfirmation", "git_blob_oid_match"], False))
    # (2) SHA-256 incorreto
    ev_fail("SHA-256 divergente do GATE 2",
            setpath(["identity_reconfirmation", "sha256_local"], "a" * 64))
    ev_fail("SHA-256 ausente", delpath(["identity_reconfirmation", "sha256_local"]))
    ev_fail("SHA-256 malformado", setpath(["identity_reconfirmation", "sha256_local"], "xyz"))
    ev_fail("SHA-256 = Git OID (confusao)",
            setpath(["identity_reconfirmation", "sha256_local"], "c853da42d18dfe090b4e941b435d989311faf3dc"))
    # (3) tamanho incorreto
    ev_fail("tamanho observado divergente",
            setpath(["identity_reconfirmation", "size_bytes_observed"], 999))
    ev_fail("size_match=false", setpath(["identity_reconfirmation", "size_match"], False))
    ev_fail("identity_matches_gate_2=false",
            setpath(["identity_reconfirmation", "identity_matches_gate_2"], False))
    # (11) mais de um arquivo materializado
    ev_fail("mais de um arquivo materializado",
            setpath(["identity_reconfirmation", "materialized_file_count"], 2))
    ev_fail("zero arquivos materializados",
            setpath(["identity_reconfirmation", "materialized_file_count"], 0))
    # (12) caminho dentro da worktree
    ev_fail("caminho dentro da worktree",
            setpath(["identity_reconfirmation", "temporary_dir_outside_repo"], False))
    ev_fail("arquivo aberto", setpath(["identity_reconfirmation", "opened"], True))
    ev_fail("arquivo executado", setpath(["identity_reconfirmation", "executed"], True))
    # PE
    ev_fail("PE invalido", setpath(["pe_identity", "pe_valid"], False))
    ev_fail("PE sem MZ", setpath(["pe_identity", "mz_present"], False))
    ev_fail("PE formato invalido", setpath(["pe_identity", "pe_format"], "ELF"))
    # (8) 'assinatura valida' sem evidencia da ferramenta (overclaim)
    def overclaim_valid(ev):
        ev["authenticode"]["authenticode_signature_present"] = True
        ev["authenticode"]["certificate_table_present"] = True
        ev["authenticode"]["cryptographic_verification"] = "PERFORMED_VALID"
        ev["authenticode"]["structurally_parseable"] = False
    ev_fail("assinatura 'valida' sem parse estrutural (overclaim)", overclaim_valid)
    # (9) 'arquivo seguro' derivado apenas da assinatura
    ev_fail("afirmacao de arquivo seguro (semantica)",
            setpath(["signature_semantics", "not_equal_file_safe"], False))
    ev_fail("assinatura ausente = malware (semantica)",
            setpath(["signature_semantics", "absence_not_equal_malware"], False))
    ev_fail("timestamp tratado como confiavel (semantica)",
            setpath(["signature_semantics", "timestamp_not_trusted"], False))
    # (14) enum fora do conjunto fechado
    ev_fail("cryptographic_verification fora do enum",
            setpath(["authenticode", "cryptographic_verification"], "MAGICAMENTE_VALIDA"))
    ev_fail("chain_trust_state fora do enum",
            setpath(["authenticode", "chain_trust_state"], "TRUSTED_SOMEHOW"))
    # coerencia assinatura ausente
    ev_fail("assinatura ausente com signatario preenchido",
            setpath(["authenticode", "signer_subject"], "CN=Fabricante"))
    # (10) limpeza nao confirmada
    ev_fail("temporary_file_removed=false", setpath(["security_assertions", "temporary_file_removed"], False))
    ev_fail("temporary_dir_removed=false", setpath(["security_assertions", "temporary_dir_removed"], False))
    # (13) tentativa de rede
    ev_fail("no_network_after_fetch=false", setpath(["security_assertions", "no_network_after_fetch"], False))
    ev_fail("no_execution_performed=false", setpath(["security_assertions", "no_execution_performed"], False))
    ev_fail("no_dynamic_analysis_performed=false", setpath(["security_assertions", "no_dynamic_analysis_performed"], False))
    ev_fail("no_sandbox_created=false (Wine/sandbox)", setpath(["security_assertions", "no_sandbox_created"], False))
    ev_fail("no_gate4_inspection_performed=false", setpath(["security_assertions", "no_gate4_inspection_performed"], False))
    ev_fail("no_ragexe_access=false", setpath(["security_assertions", "no_ragexe_access"], False))
    ev_fail("no_external_service_upload=false", setpath(["security_assertions", "no_external_service_upload"], False))
    ev_fail("binary_versioned=true", setpath(["security_assertions", "binary_versioned"], True))
    # gate_4_authorized=true (evidencia)
    ev_fail("gate_4_authorized=true (evidencia)", setpath(["security_assertions", "gate_4_authorized"], True))
    ev_fail("method fora do conjunto", setpath(["execution", "method"], "git clone"))
    ev_fail("network_scope invalido", setpath(["execution", "network_scope"], "ANY"))
    ev_fail("timestamp fora de ordem (start>finish)",
            setpath(["execution", "started_at"], "2026-08-03T23:59:59Z"))
    ev_fail("limpeza antes do fim (finish>cleanup)",
            setpath(["execution", "cleanup_at"], "2026-08-03T00:00:00Z"))
    ev_fail("propriedade inesperada", lambda e: e.__setitem__("x", 1))
    ev_fail("gate_2_evidence_ref inexistente",
            setpath(["gate_2_evidence_ref", "path"], "client/warp-audit/evidence/nao-existe.json"))
    ev_fail("integration_ref squash incorreto",
            setpath(["integration_ref", "squash_commit"], "0" * 40))

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
    ev_fail("upstream commit divergente", setpath(["upstream_expected", "commit_oid"], "1" * 40))
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
