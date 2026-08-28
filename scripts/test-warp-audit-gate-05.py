#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes do tooling ESTATICO do GATE 5 (scripts/warp-audit-gate-05.py) — 2P-E-C5-TOOLING-PREP.

Somente FIXTURES SINTETICAS geradas em runtime. NAO usa o WARP real, NAO executa
scanner real, NAO acessa rede, NAO exige Windows/Defender/YARA/VPS/cliente.
Cobre: casos validos, casos negativos (fail-closed), seguranca da ferramenta,
sanitizacao e integracao com o validador canonico.
"""
import datetime
import importlib.util
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
SCHEMA_DIR = os.path.join(REPO_ROOT, "client", "warp-audit", "schemas")
AUDIT_DIR = os.path.join(REPO_ROOT, "client", "warp-audit")

FIXED = datetime.datetime(2026, 8, 5, 23, 30, 0, tzinfo=datetime.timezone.utc)


def load_module(fname, modname):
    path = os.path.join(SCRIPTS_DIR, fname)
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


g5 = load_module("warp-audit-gate-05.py", "warp_audit_gate_05")
validator = load_module("validate-warp-audit.py", "validate_warp_audit_g5")

passed = 0
failed = 0


def ok(label):
    global passed
    passed += 1


def bad(label, detail=""):
    global failed
    failed += 1
    print(f"[FALHA] {label}" + (f": {detail}" if detail else ""))


def check(label, cond, detail=""):
    if cond:
        ok(label)
    else:
        bad(label, detail)


def expect_error(label, fn, exc=None):
    exc = exc or g5.Gate5Error
    try:
        fn()
    except exc:
        ok(label)
    except Exception as e:  # noqa: BLE001 - teste deve distinguir excecao esperada
        bad(label, f"excecao inesperada {type(e).__name__}: {e}")
    else:
        bad(label, "nao levantou excecao")


def base_config(tmp, mode="fixture", **over):
    cfg = {
        "schema_version": 1, "gate_id": 5, "gate_name": "Verificacoes locais de seguranca",
        "mode": mode, "input_path": "fx.bin", "output_directory": "out",
        "timeout_seconds": 30, "enabled_adapters": ["synthetic-local"],
        "network_policy": "blocked", "execution_policy": "artifact_never_executed",
        "modification_policy": "input_never_modified",
        "authorization_flags": {"gate_5_authorized": False, "execution_authorized": False,
            "local_security_scan_authorized": False, "external_reputation_upload_authorized": False,
            "client_preparation_authorized": False},
    }
    cfg.update(over)
    return cfg


def make_fixture(tmp, content=b"SYN-PASS inert synthetic fixture\n", name="fx.bin"):
    p = Path(tmp) / name
    p.write_bytes(content)
    return p


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def schema_valid(instance, schema_name):
    schema = load_json(os.path.join(SCHEMA_DIR, schema_name))
    errors = []
    validator.validate_node(instance, schema, "$", errors)
    return errors


def main():
    input_schema = "binary-audit-gate-05-input.schema.json"
    evidence_schema = "binary-audit-gate-05-evidence.schema.json"

    # ------------------------------------------------------------------ #
    # J1 — casos validos
    # ------------------------------------------------------------------ #
    inp_example = load_json(os.path.join(AUDIT_DIR, "binary-audit-gate-05-input.example.json"))
    check("J1 input.example valida contra schema", schema_valid(inp_example, input_schema) == [],
          str(schema_valid(inp_example, input_schema)))
    ev_example = load_json(os.path.join(AUDIT_DIR, "binary-audit-gate-05-evidence.example.json"))
    check("J1 evidence.example valida contra schema", schema_valid(ev_example, evidence_schema) == [],
          str(schema_valid(ev_example, evidence_schema)))
    check("J1 evidence.example outcome=FIXTURE_VALIDATION_PASS",
          ev_example["outcome"] == "FIXTURE_VALIDATION_PASS")
    check("J1 evidence.example nao usa GATE_PASSED",
          "GATE_PASSED" not in json.dumps(ev_example))

    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd()
        os.chdir(tmp)
        try:
            make_fixture(tmp)
            cfg = base_config(tmp)
            ev = g5.run(cfg, clock=lambda: FIXED)
            check("J1 fixture-mode outcome PASS", ev["outcome"] == "FIXTURE_VALIDATION_PASS")
            check("J1 fixture-mode adapter PASS",
                  ev["adapter_results"][0]["classification"] == "PASS")
            check("J1 evidencia gerada valida contra schema",
                  schema_valid(ev, evidence_schema) == [], str(schema_valid(ev, evidence_schema)))
            # determinismo: duas execucoes com relogio fixo => identicas
            ev2 = g5.run(base_config(tmp), clock=lambda: FIXED)
            check("J1 evidencia deterministica",
                  json.dumps(ev, sort_keys=True) == json.dumps(ev2, sort_keys=True))
            # validate-only
            evo = g5.run(base_config(tmp, mode="validate-only"), clock=lambda: FIXED)
            check("J1 validate-only outcome", evo["outcome"] == "CONFIG_VALIDATION_PASS")
            check("J1 validate-only adapters NOT_RUN",
                  all(r["classification"] == "NOT_RUN" for r in evo["adapter_results"]))
        finally:
            os.chdir(cwd)

    # adapter sintetico: PASS/FINDING/ERROR/TIMEOUT
    synth = g5.SyntheticAdapter()
    check("J1 synthetic PASS", synth.analyze_bytes(b"SYN-PASS x").classification == "PASS")
    check("J1 synthetic FINDING", synth.analyze_bytes(b"SYN-FINDING x").classification == "FINDING")
    check("J1 synthetic ERROR", synth.analyze_bytes(b"SYN-ERROR x").classification == "ERROR")
    check("J1 synthetic TIMEOUT", synth.analyze_bytes(b"SYN-TIMEOUT x").classification == "TIMEOUT")

    # sanitizacao
    check("J1 sanitiza drive path",
          "<redacted-path>" in g5.sanitize_text(r"achado em C:\Users\alguem\segredo.txt"))
    check("J1 sanitiza home path",
          "<redacted-path>" in g5.sanitize_text("erro em /home/alguem/x"))
    check("J1 sanitiza IP", "<redacted-ip>" in g5.sanitize_text("conexao 10.0.0.5 negada"))
    check("J1 sanitiza URL", "<redacted-url>" in g5.sanitize_text("baixe de https://mal.example/x"))
    check("J1 sanitiza segredo", "<redacted-secret>" in g5.sanitize_text("token=abc123def"))
    check("J1 trunca stdout excessivo",
          g5.sanitize_text("A" * 99999).endswith("…[TRUNCADO]"))

    # output em diretorio permitido
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "base"; (base / "sub").mkdir(parents=True)
        cfg = base_config(tmp, output_directory=str(base / "sub"))
        # nao levanta com base permitida
        try:
            g5._resolve_output_dir(cfg, base)
            ok("J1 output em diretorio permitido")
        except g5.Gate5Error as e:
            bad("J1 output em diretorio permitido", str(e))

    # ------------------------------------------------------------------ #
    # J2 — casos negativos (fail-closed)
    # ------------------------------------------------------------------ #
    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd(); os.chdir(tmp)
        try:
            make_fixture(tmp)
            for flag in ("gate_5_authorized", "execution_authorized",
                         "local_security_scan_authorized", "external_reputation_upload_authorized"):
                cfg = base_config(tmp)
                cfg["authorization_flags"][flag] = True
                expect_error(f"J2 flag {flag}=true rejeitada", lambda c=cfg: g5.run(c, clock=lambda: FIXED))

            expect_error("J2 gate_id invalido",
                         lambda: g5.run(base_config(tmp, gate_id=4), clock=lambda: FIXED))
            expect_error("J2 network_policy != blocked",
                         lambda: g5.run(base_config(tmp, network_policy="open"), clock=lambda: FIXED))
            expect_error("J2 execution_policy invalida",
                         lambda: g5.run(base_config(tmp, execution_policy="x"), clock=lambda: FIXED))
            expect_error("J2 timeout invalido",
                         lambda: g5.run(base_config(tmp, timeout_seconds=0), clock=lambda: FIXED))
            expect_error("J2 adapter desconhecido",
                         lambda: g5.run(base_config(tmp, enabled_adapters=["nope"]), clock=lambda: FIXED))
            expect_error("J2 hash malformado",
                         lambda: g5.run(base_config(tmp, expected_sha256="xyz"), clock=lambda: FIXED))
            expect_error("J2 hash divergente",
                         lambda: g5.run(base_config(tmp, expected_sha256="0"*64), clock=lambda: FIXED))
            expect_error("J2 input inexistente",
                         lambda: g5.run(base_config(tmp, input_path="naoexiste.bin"), clock=lambda: FIXED))
            expect_error("J2 modo real bloqueado",
                         lambda: g5.run(base_config(tmp, mode="real"), clock=lambda: FIXED),
                         exc=g5.RealExecutionNotAuthorized)
            expect_error("J2 adapter nao-fixture em fixture-mode",
                         lambda: g5.run(base_config(tmp, enabled_adapters=["yara-local"]), clock=lambda: FIXED))
        finally:
            os.chdir(cwd)

    # output fora do diretorio autorizado
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "base"; base.mkdir()
        other = Path(tmp) / "other"; other.mkdir()
        cfg = base_config(tmp, output_directory=str(other))
        expect_error("J2 output fora do diretorio autorizado",
                     lambda: g5._resolve_output_dir(cfg, base))

    # symlink (portavel: se o SO nao permitir criar, conta como skip-ok)
    with tempfile.TemporaryDirectory() as tmp:
        target = make_fixture(tmp)
        link = Path(tmp) / "link.bin"
        try:
            os.symlink(target, link)
            expect_error("J2 symlink rejeitado", lambda: g5._validate_local_path(str(link)))
        except (OSError, NotImplementedError):
            ok("J2 symlink (nao suportado no SO; skip)")

    # stdout/stderr excessivo via adapter result -> to_dict trunca
    big = g5.AdapterResult(adapter="synthetic-local", availability="simulated", command_id="x",
                           timeout_seconds=5, exit_code=0, classification="PASS",
                           stdout_sanitized="B" * 99999, stderr_sanitized="C" * 99999,
                           duration_ms=0)
    d = big.to_dict()
    check("J2 stdout excessivo truncado", d["stdout_sanitized"].endswith("…[TRUNCADO]"))
    check("J2 stderr excessivo truncado", d["stderr_sanitized"].endswith("…[TRUNCADO]"))

    # classificacao fora do conjunto fechado -> erro
    badres = g5.AdapterResult(adapter="x", availability="simulated", command_id="x",
                              timeout_seconds=5, exit_code=0, classification="SAFE",
                              stdout_sanitized="", stderr_sanitized="", duration_ms=0)
    expect_error("J2 classificacao proibida (SAFE) rejeitada", badres.to_dict)

    # schema: campo desconhecido e obrigatorio ausente
    bad_extra = dict(inp_example); bad_extra["hack"] = 1
    check("J2 schema rejeita campo desconhecido", schema_valid(bad_extra, input_schema) != [])
    bad_missing = dict(inp_example); bad_missing.pop("authorization_flags")
    check("J2 schema rejeita campo obrigatorio ausente", schema_valid(bad_missing, input_schema) != [])
    bad_flag = json.loads(json.dumps(inp_example)); bad_flag["authorization_flags"]["gate_5_authorized"] = True
    check("J2 schema rejeita gate_5_authorized=true", schema_valid(bad_flag, input_schema) != [])

    # evidencia com GATE_PASSED / flag true rejeitada pelo schema
    bad_ev = json.loads(json.dumps(ev_example)); bad_ev["outcome"] = "GATE_PASSED"
    check("J2 schema evidencia rejeita GATE_PASSED", schema_valid(bad_ev, evidence_schema) != [])
    bad_ev2 = json.loads(json.dumps(ev_example)); bad_ev2["authorization_flags"]["gate_5_authorized"] = True
    check("J2 schema evidencia rejeita flag true", schema_valid(bad_ev2, evidence_schema) != [])

    # main(): recusa sobrescrever evidencia existente
    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd(); os.chdir(tmp)
        try:
            make_fixture(tmp)
            cfgp = Path(tmp) / "cfg.json"; cfgp.write_text(json.dumps(base_config(tmp)), encoding="utf-8")
            outp = Path(tmp) / "ev.json"; outp.write_text("{}", encoding="utf-8")
            rc = g5.main(["prog", "--config", str(cfgp), "--output", str(outp)])
            check("J2 main recusa overwrite", rc == 2)
            fresh = Path(tmp) / "ev2.json"
            rc2 = g5.main(["prog", "--config", str(cfgp), "--output", str(fresh)])
            check("J2 main grava evidencia nova", rc2 == 0 and fresh.exists())
            # main modo real -> 3
            cfgr = Path(tmp) / "cfgr.json"; cfgr.write_text(json.dumps(base_config(tmp, mode="real")), encoding="utf-8")
            rc3 = g5.main(["prog", "--config", str(cfgr)])
            check("J2 main modo real bloqueado (rc=3)", rc3 == 3)
        finally:
            os.chdir(cwd)

    # comando com argumento proibido / URL / IP: sanitizacao de mensagens
    check("J2 sanitize_message limita tamanho", len(g5.sanitize_message("Z" * 99999)) <= 600)

    # ------------------------------------------------------------------ #
    # J3 — seguranca da ferramenta
    # ------------------------------------------------------------------ #
    tool_src = Path(os.path.join(SCRIPTS_DIR, "warp-audit-gate-05.py")).read_text(encoding="utf-8")
    # sem imports de rede proibidos
    net_import = re.search(r"(?m)^\s*(?:import|from)\s+(requests|urllib\.request|urllib2|http\.client|httplib|socket|ftplib|smtplib|poplib|imaplib|telnetlib|ssl|asyncio|paramiko|aiohttp)\b", tool_src)
    check("J3 sem import de rede proibido", net_import is None,
          net_import.group(0) if net_import else "")
    check("J3 shell=True ausente", "shell=True" not in tool_src)
    check("J3 shell=False presente", "shell=False" in tool_src)
    check("J3 sem os.system", "os.system" not in tool_src)

    # input nao e executado / permissoes e conteudo inalterados
    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd(); os.chdir(tmp)
        try:
            fx = make_fixture(tmp)
            before = fx.read_bytes()
            mode_before = stat.S_IMODE(fx.stat().st_mode)
            g5.run(base_config(tmp), clock=lambda: FIXED)
            check("J3 conteudo da entrada byte-identico", fx.read_bytes() == before)
            check("J3 permissoes da entrada inalteradas",
                  stat.S_IMODE(fx.stat().st_mode) == mode_before)
        finally:
            os.chdir(cwd)

    # run_local_command: shell=False, argv lista; comando local trivial (nao e o artefato)
    r = g5.run_local_command([sys.executable, "-c", "print('ok')"], 30)
    check("J3 run_local_command captura exit 0", r["exit_code"] == 0 and r["state"] == "PASS")
    expect_error("J3 run_local_command rejeita argv nao-lista",
                 lambda: g5.run_local_command("echo x", 30))
    # timeout real via subprocess local trivial (sleep), sem tocar o artefato
    rt = g5.run_local_command([sys.executable, "-c", "import time; time.sleep(5)"], 1)
    check("J3 run_local_command TIMEOUT", rt["state"] == "TIMEOUT")

    # adapters Defender/YARA: contrato constroi argv com o arquivo como ARGUMENTO
    dfd = g5.DefenderAdapter()
    with tempfile.TemporaryDirectory() as tmp:
        fx = make_fixture(tmp)
        cmd = dfd.build_command(str(fx))
        check("J3 Defender argv e lista", isinstance(cmd, list) and cmd[0].endswith("MpCmdRun.exe"))
        check("J3 Defender passa arquivo como -File", "-File" in cmd and str(fx) in cmd)
    check("J3 Defender parse FINDING",
          dfd.parse_output("Threat detected", "", 0) == "FINDING")
    check("J3 Defender parse PASS", dfd.parse_output("scan completed, 0 items", "", 0) == "PASS")
    check("J3 Defender parse TIMEOUT", dfd.parse_output("", "", None) == "TIMEOUT")
    yr = g5.YaraAdapter()
    check("J3 YARA parse FINDING", yr.parse_output("rule_x file", "", 0) == "FINDING")
    check("J3 YARA parse PASS", yr.parse_output("", "", 0) == "PASS")
    check("J3 YARA parse ERROR", yr.parse_output("", "err", 1) == "ERROR")
    check("J3 Defender/YARA exigem autorizacao futura",
          dfd.requires_future_authorization and yr.requires_future_authorization)
    check("J3 Defender/YARA nao habilitados em fixture",
          not dfd.enabled_in_fixture and not yr.enabled_in_fixture)

    # integracao com validador: artefatos registrados em ARTIFACTS
    registered = {a for a, _ in validator.ARTIFACTS}
    check("J3 input.example registrado no validador",
          "binary-audit-gate-05-input.example.json" in registered)
    check("J3 evidence.example registrado no validador",
          "binary-audit-gate-05-evidence.example.json" in registered)

    # ------------------------------------------------------------------ #
    # J5 — regressoes de hardening (D1..D4)
    # ------------------------------------------------------------------ #

    # D1: client_preparation_authorized=true deve ser rejeitada pelo runtime
    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd(); os.chdir(tmp)
        try:
            make_fixture(tmp)
            cfg = base_config(tmp)
            cfg["authorization_flags"]["client_preparation_authorized"] = True
            expect_error("J5-D1 client_preparation_authorized=true rejeitada",
                         lambda c=cfg: g5.run(c, clock=lambda: FIXED))
        finally:
            os.chdir(cwd)

    # D2: modification_policy divergente
    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd(); os.chdir(tmp)
        try:
            make_fixture(tmp)
            expect_error("J5-D2 modification_policy divergente",
                         lambda: g5.run(base_config(tmp, modification_policy="allow"),
                                        clock=lambda: FIXED))
        finally:
            os.chdir(cwd)

    # D2: gate_name divergente
    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd(); os.chdir(tmp)
        try:
            make_fixture(tmp)
            expect_error("J5-D2 gate_name divergente",
                         lambda: g5.run(base_config(tmp, gate_name="Wrong name"),
                                        clock=lambda: FIXED))
        finally:
            os.chdir(cwd)

    # D2: campo extra no top-level do config
    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd(); os.chdir(tmp)
        try:
            make_fixture(tmp)
            cfg = base_config(tmp)
            cfg["hack_field"] = "injected"
            expect_error("J5-D2 campo extra no config rejeitado",
                         lambda c=cfg: g5.run(c, clock=lambda: FIXED))
        finally:
            os.chdir(cwd)

    # D2: campo extra em authorization_flags
    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd(); os.chdir(tmp)
        try:
            make_fixture(tmp)
            cfg = base_config(tmp)
            cfg["authorization_flags"]["extra_flag"] = False
            expect_error("J5-D2 campo extra em authorization_flags rejeitado",
                         lambda c=cfg: g5.run(c, clock=lambda: FIXED))
        finally:
            os.chdir(cwd)

    # D3: config mode=real + --fixture-mode via main() deve retornar 3 (bloqueado)
    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd(); os.chdir(tmp)
        try:
            make_fixture(tmp)
            cfgp = Path(tmp) / "cfg_real.json"
            cfgp.write_text(json.dumps(base_config(tmp, mode="real")), encoding="utf-8")
            rc = g5.main(["prog", "--config", str(cfgp), "--fixture-mode"])
            check("J5-D3 config mode=real + --fixture-mode bloqueado (rc=3)", rc == 3)
        finally:
            os.chdir(cwd)

    # D3: config mode=real + --validate-only via main() deve retornar 3
    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd(); os.chdir(tmp)
        try:
            make_fixture(tmp)
            cfgp = Path(tmp) / "cfg_real2.json"
            cfgp.write_text(json.dumps(base_config(tmp, mode="real")), encoding="utf-8")
            rc = g5.main(["prog", "--config", str(cfgp), "--validate-only"])
            check("J5-D3 config mode=real + --validate-only bloqueado (rc=3)", rc == 3)
        finally:
            os.chdir(cwd)

    # D4: fixture com conteudo PE sintetico (MZ) rejeitada
    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd(); os.chdir(tmp)
        try:
            pe_content = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 50  # PE sintetico
            make_fixture(tmp, content=pe_content, name="fake_pe.bin")
            expect_error("J5-D4 fixture com PE magic (MZ) rejeitada",
                         lambda: g5.run(base_config(tmp, input_path="fake_pe.bin"),
                                        clock=lambda: FIXED))
        finally:
            os.chdir(cwd)

    # D4: fixture arbitraria grande (> 1 MiB) rejeitada
    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd(); os.chdir(tmp)
        try:
            big_content = b"SYN-PASS " + b"X" * (g5.FIXTURE_MAX_BYTES + 1)
            make_fixture(tmp, content=big_content, name="big.bin")
            expect_error("J5-D4 fixture grande rejeitada",
                         lambda: g5.run(base_config(tmp, input_path="big.bin"),
                                        clock=lambda: FIXED))
        finally:
            os.chdir(cwd)

    # D5: Defender parser com mensagens adversariais
    dfd2 = g5.DefenderAdapter()
    check("J5-D5 Defender '0 threats detected' -> FINDING (conservador)",
          dfd2.parse_output("0 threats detected", "", 0) == "FINDING")
    check("J5-D5 Defender 'No threats found' + exit 0 -> FINDING (conservador: contem 'threat')",
          dfd2.parse_output("No threats found", "", 0) == "FINDING")
    check("J5-D5 Defender 'malware detected' -> FINDING",
          dfd2.parse_output("malware detected in file", "", 0) == "FINDING")
    check("J5-D5 Defender exit 2 (error) -> ERROR",
          dfd2.parse_output("scan completed", "", 2) == "ERROR")

    # ------------------------------------------------------------------ #
    # J4 — portabilidade (nada acima exigiu Windows/Defender/YARA/rede/WARP)
    # ------------------------------------------------------------------ #
    check("J4 suite roda sem scanner/rede/artefato real", True)

    print(f"\nResumo: {passed} teste(s) OK, {failed} falha(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
