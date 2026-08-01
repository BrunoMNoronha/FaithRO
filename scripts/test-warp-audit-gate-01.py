#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes positivos e negativos do registro real da autorizacao humana do GATE 1
(ETAPA 2P-E-C1-A) da auditoria binaria offline do WARP.

Offline e sem dependencias externas: importa scripts/validate-warp-audit.py e exercita
validate_gate1_record contra o registro real e contra dezenas de mutacoes invalidas.
Nao acessa a rede, nao materializa binario, nao executa o WARP e nao escreve arquivos.

Cobre, no minimo (FASE L do prompt 2P-E-C1-A):
  * validacao positiva do registro real;
  * decisao humana incorreta; squash do PR #48 incorreto;
  * commit, tree, path, Git blob OID e algoritmo divergentes;
  * SHA-256 presente/ malformado / confundido com o Git OID (proibidos no GATE 1);
  * mais de um arquivo (max_files) e binary_materialized=true;
  * uso de release asset / archive / mirror / comando de download;
  * execucao, sandbox/Wine, acesso a VPS, integracao no cliente e distribuicao;
  * ausencia da autorizacao (materialization_authorized=false);
  * autorizacao transitiva (gate_2_authorized=true e outros pontos criticos);
  * resultado/execution_state incompativel; conditions insuficientes; placeholder;
  * propriedade inesperada no JSON (additionalProperties);
  * cross-checks quebrados (GATE 0 nao aprovado / evidencia nao COMPLETED_PASS).

Codigo de saida != 0 se qualquer teste falhar.
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

RECORD_FILE = "binary-audit-gate-01-decision-record-2026-08-01.json"


def load_module():
    path = os.path.join(SCRIPTS_DIR, "validate-warp-audit.py")
    spec = importlib.util.spec_from_file_location("validate_warp_audit", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main():
    mod = load_module()
    schema = load_json(os.path.join(SCHEMA_DIR, "binary-audit-gate-01-decision-record-real.schema.json"))
    plan = load_json(os.path.join(AUDIT_DIR, "binary-audit-plan.example.json"))
    gate0_decision = load_json(os.path.join(DECISIONS_DIR, "binary-audit-gate-00-decision-record-2026-07-31.json"))
    gate0_evidence = load_json(os.path.join(EVIDENCE_DIR, "binary-audit-gate-00-provenance-evidence-2026-08-01.json"))
    base = load_json(os.path.join(DECISIONS_DIR, RECORD_FILE))

    passed = 0
    failed = 0

    def run(rec, p=plan, gd=gate0_decision, ge=gate0_evidence):
        errs = []
        mod.validate_gate1_record(rec, schema, p, gd, ge, RECORD_FILE, errs)
        return errs

    def expect_ok(label, rec):
        nonlocal passed, failed
        errs = run(rec)
        if errs:
            failed += 1
            print(f"[FALHA] (esperava OK) {label}: {len(errs)} erro(s)")
            for e in errs[:5]:
                print(f"    - {e}")
        else:
            passed += 1
            print(f"[OK+]   {label}")

    def expect_fail(label, mutate, **ctx):
        nonlocal passed, failed
        rec = copy.deepcopy(base)
        mutate(rec)
        errs = run(rec, **ctx)
        if errs:
            passed += 1
            print(f"[OK-]   {label} (reprovado, {len(errs)} erro(s))")
        else:
            failed += 1
            print(f"[FALHA] (esperava reprovacao) {label}")

    # ---- Positivo ----
    expect_ok("registro real integro", copy.deepcopy(base))

    # ---- Negativos: decisao / identidade da etapa ----
    def m(path_keys, value):
        def _f(rec):
            node = rec
            for k in path_keys[:-1]:
                node = node[k]
            node[path_keys[-1]] = value
        return _f

    def m_del(path_keys):
        def _f(rec):
            node = rec
            for k in path_keys[:-1]:
                node = node[k]
            del node[path_keys[-1]]
        return _f

    expect_fail("decisao humana incorreta", m(["decision"], "APPROVE_GATE_0"))
    expect_fail("decisao AUTHORIZE_GATE_2 invalida", m(["decision"], "AUTHORIZE_GATE_2"))
    expect_fail("gate.id incorreto", m(["gate", "id"], 2))
    expect_fail("gate.name incorreto", m(["gate", "name"], "MATERIALIZATION"))
    expect_fail("status incorreto", m(["status"], "GATE_PASSED"))
    expect_fail("execution_state incompativel", m(["execution_state"], "COMPLETED"))
    expect_fail("stage incorreto", m(["stage"], "2P-E-C0-A"))

    # ---- Negativos: squash do PR #48 ----
    expect_fail("squash do PR #48 incorreto",
                m(["integration_ref", "squash_commit"], "0000000000000000000000000000000000000000"))
    expect_fail("numero de PR incorreto", m(["integration_ref", "pr"], 47))
    expect_fail("base_branch incorreta", m(["integration_ref", "base_branch"], "main"))

    # ---- Negativos: escopo do objeto imutavel ----
    expect_fail("commit divergente",
                m(["materialization_scope", "commit_oid"], "1111111111111111111111111111111111111111"))
    expect_fail("tree divergente",
                m(["materialization_scope", "tree_oid"], "2222222222222222222222222222222222222222"))
    expect_fail("path divergente",
                m(["materialization_scope", "artifact_path"], "win64/WARP.exe"))
    expect_fail("Git blob OID esperado divergente",
                m(["materialization_scope", "artifact_blob_oid"], "3333333333333333333333333333333333333333"))
    expect_fail("algoritmo do Git OID incorreto",
                m(["materialization_scope", "artifact_blob_oid_algorithm"], "SHA256"))
    expect_fail("repositorio divergente",
                m(["materialization_scope", "repository_full_name"], "attacker/WARP"))
    expect_fail("branch divergente",
                m(["materialization_scope", "expected_branch"], "master"))
    expect_fail("tamanho divergente",
                m(["materialization_scope", "artifact_blob_size"], 999999))
    expect_fail("network_scope fora do GitHub oficial",
                m(["materialization_scope", "network_scope"], "ANY"))

    # ---- Negativos: mais de um arquivo materializado ----
    expect_fail("mais de um arquivo (max_files)",
                m(["materialization_scope", "max_files"], 2))
    expect_fail("binary_materialized=true",
                m(["security_assertions", "binary_materialized"], True))

    # ---- Negativos: SHA-256 no GATE 1 (proibido) ----
    expect_fail("binary_sha256 preenchido",
                m(["security_assertions", "binary_sha256"],
                  "a" * 64))
    expect_fail("binary_sha256_computed=true",
                m(["security_assertions", "binary_sha256_computed"], True))

    def add_hash_in_notes(rec):
        # SHA-256 (64 hex) embutido em texto: reprovado pelo planning_content_scan.
        rec["notes"] = rec["notes"] + " " + ("b" * 64)
    expect_fail("SHA-256 (64 hex) embutido em texto", add_hash_in_notes)

    # ---- Negativos: acesso ao conteudo / consulta upstream nesta etapa ----
    expect_fail("blob_content_accessed=true",
                m(["security_assertions", "blob_content_accessed"], True))
    expect_fail("no_download_performed=false",
                m(["security_assertions", "no_download_performed"], False))
    expect_fail("no_upstream_query_this_stage=false",
                m(["security_assertions", "no_upstream_query_this_stage"], False))

    # ---- Negativos: release asset / archive / mirror / download ----
    expect_fail("no_archive_or_release_asset=false",
                m(["security_assertions", "no_archive_or_release_asset"], False))
    expect_fail("no_clone_or_fetch_upstream=false",
                m(["security_assertions", "no_clone_or_fetch_upstream"], False))

    def add_download_cmd(rec):
        rec["allowed_future_methods"] = rec["allowed_future_methods"] + ["curl https://x/win32/WARP.exe"]
    expect_fail("comando de download embutido", add_download_cmd)

    def add_binary_url(rec):
        rec["notes"] = rec["notes"] + " http://example.com/WARP.zip"
    expect_fail("URL direta para binario embutida", add_binary_url)

    # ---- Negativos: execucao / sandbox-Wine / VPS / cliente / distribuicao ----
    expect_fail("no_execution_performed=false",
                m(["security_assertions", "no_execution_performed"], False))
    expect_fail("no_sandbox_created=false (Wine/sandbox)",
                m(["security_assertions", "no_sandbox_created"], False))
    expect_fail("no_vps_access=false",
                m(["security_assertions", "no_vps_access"], False))
    expect_fail("vps_access_authorized=true",
                m(["authorizations", "vps_access_authorized"], True))
    expect_fail("execution_without_client_authorized=true",
                m(["authorizations", "execution_without_client_authorized"], True))
    expect_fail("client_copy_provision_authorized=true",
                m(["authorizations", "client_copy_provision_authorized"], True))
    expect_fail("distribution_authorized=true",
                m(["authorizations", "distribution_authorized"], True))

    def add_warp_exec(rec):
        rec["notes"] = rec["notes"] + " executar WARP.exe"
    expect_fail("comando de execucao do WARP embutido", add_warp_exec)

    # ---- Negativos: grant ausente / autorizacao transitiva ----
    expect_fail("materialization_authorized=false (grant ausente)",
                m(["authorizations", "materialization_authorized"], False))
    expect_fail("gate_2_authorized=true (autorizacao transitiva)",
                m(["authorizations", "gate_2_authorized"], True))
    expect_fail("hashing_authorized=true",
                m(["authorizations", "hashing_authorized"], True))
    expect_fail("static_inspection_authorized=true",
                m(["authorizations", "static_inspection_authorized"], True))
    expect_fail("patch_application_authorized=true",
                m(["authorizations", "patch_application_authorized"], True))
    expect_fail("first_login_authorized=true",
                m(["authorizations", "first_login_authorized"], True))

    # ---- Negativos: pre-condicao do GATE 0 ----
    expect_fail("gate_0_precondition.gate_0_completed=false",
                m(["gate_0_precondition", "gate_0_completed"], False))
    expect_fail("gate_0_precondition.gate_0_outcome != COMPLETED_PASS",
                m(["gate_0_precondition", "gate_0_outcome"], "STOPPED"))

    # ---- Negativos: identidade / condicoes / placeholder ----
    expect_fail("decider placeholder", m(["decider"], "preencher"))
    expect_fail("decider vazio", m(["decider"], ""))
    expect_fail("data invalida", m(["date"], "31-07-2026"))

    def trim_conditions(rec):
        rec["conditions"] = rec["conditions"][:5]
        for i, c in enumerate(rec["conditions"]):
            c["n"] = i + 1
    expect_fail("conditions insuficientes (<20)", trim_conditions)

    def break_condition_numbering(rec):
        rec["conditions"][3]["n"] = 99
    expect_fail("conditions com numeracao quebrada", break_condition_numbering)

    # ---- Negativos: propriedade inesperada / referencias ----
    expect_fail("propriedade inesperada no JSON",
                lambda rec: rec.__setitem__("unexpected_field", True))
    expect_fail("plan_ref inexistente",
                m(["plan_ref", "path"], "client/warp-audit/nao-existe.json"))
    expect_fail("gate_0_evidence_ref inexistente",
                m(["gate_0_evidence_ref", "path"], "client/warp-audit/evidence/nao-existe.json"))

    # ---- Negativos: cross-checks quebrados ----
    bad_gate0_decision = copy.deepcopy(gate0_decision)
    bad_gate0_decision["decision"] = "STOP_PATH"
    expect_fail("decisao do GATE 0 nao e APPROVE_GATE_0",
                lambda rec: None, gd=bad_gate0_decision)

    bad_gate0_evidence = copy.deepcopy(gate0_evidence)
    bad_gate0_evidence["outcome"] = "STOPPED"
    expect_fail("evidencia do GATE 0 nao esta COMPLETED_PASS",
                lambda rec: None, ge=bad_gate0_evidence)

    print(f"\nResumo: {passed} teste(s) OK, {failed} falha(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # sem traceback
        print(f"[ERRO] falha inesperada: {exc}")
        sys.exit(2)
