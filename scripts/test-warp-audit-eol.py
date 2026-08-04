#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de invariantes de EOL dos artefatos byte-fixados da auditoria WARP
(ETAPA 2P-E-C3-LF). Garante que os tres arquivos cuja proveniencia/integridade e
validada byte a byte permanecem em LF mesmo em checkouts Windows com
core.autocrlf=true, protegidos por regras `text eol=lf` no .gitattributes.

O teste:
  * consulta os atributos Git efetivos (git check-attr) e exige text=set + eol=lf;
  * le os arquivos da WORKTREE em modo binario (nao apenas o index);
  * rejeita BOM, qualquer byte CR e (na saida do parser) ausencia de newline final;
  * recalcula SHA-256 da saida e o Git blob OID da saida, do parser e dos testes;
  * compara EXATAMENTE com os valores fixados do GATE 3.

Offline e sem dependencias externas: usa apenas a stdlib do Python e o comando `git`
para consultar atributos. NAO acessa a rede, NAO altera arquivos e NAO executa o WARP.
Retorna codigo != 0 em qualquer divergencia.
"""
import hashlib
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPTS_DIR)

PARSER_OUTPUT = ("client/warp-audit/evidence/"
                 "binary-audit-gate-03-corrective-repeat-parser-output-2026-08-03.json")
PARSER = "scripts/inspect-warp-pe-identity.py"
PARSER_TEST = "scripts/test-warp-pe-identity.py"

PROTECTED = [PARSER_OUTPUT, PARSER, PARSER_TEST]

EXPECTED = {
    "output_sha256": "932968244170200b303dfd9674215ea1358a549b3e71f8034a7fb5ba4ce0f816",
    "output_git_blob_oid": "c1e66885850811a49395a5cae613c20cf4abb7a3",
    "parser_git_blob_oid": "3442ddfc585b61bba19293ce0980d7addcd7ae5b",
    "parser_test_git_blob_oid": "6d7cab1b2ae7ea8514718b7b98f2bd324fb38a41",
}

passed = 0
failed = 0


def ok(label):
    global passed
    passed += 1
    print(f"[OK]    {label}")


def bad(label, detail=""):
    global failed
    failed += 1
    print(f"[FALHA] {label}" + (f": {detail}" if detail else ""))


def git_blob_oid(data):
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_bytes(rel):
    with open(os.path.join(REPO_ROOT, rel), "rb") as fh:
        return fh.read()


def check_attr(rel):
    """Retorna (text, eol) efetivos do Git para o caminho (ou (None, None))."""
    out = subprocess.run(
        ["git", "-C", REPO_ROOT, "check-attr", "text", "eol", "--", rel],
        capture_output=True, text=True)
    if out.returncode != 0:
        return None, None, out.stderr.strip()
    text = eol = None
    for line in out.stdout.splitlines():
        # formato: "<path>: <attr>: <value>"
        parts = line.rsplit(": ", 2)
        if len(parts) == 3:
            _, attr, value = parts
            if attr == "text":
                text = value
            elif attr == "eol":
                eol = value
    return text, eol, ""


def main():
    # 1) Atributos Git efetivos: text=set + eol=lf nos tres arquivos protegidos.
    for rel in PROTECTED:
        text, eol, err = check_attr(rel)
        if err:
            bad(f"check-attr {rel}", err)
            continue
        if text == "set" and eol == "lf":
            ok(f"atributos LF (text=set, eol=lf): {rel}")
        else:
            bad(f"atributos de {rel}", f"text={text!r} eol={eol!r} (esperado set/lf)")

    # 2) Bytes reais da worktree: sem BOM, sem CR.
    for rel in PROTECTED:
        try:
            data = read_bytes(rel)
        except OSError as exc:
            bad(f"leitura de {rel}", str(exc))
            continue
        if data.startswith(b"\xef\xbb\xbf"):
            bad(f"{rel}: BOM UTF-8 proibido")
        elif b"\r" in data:
            bad(f"{rel}: byte CR proibido (checkout converteu LF->CRLF?)")
        else:
            ok(f"sem BOM e sem CR: {rel}")

    # 3) Saida do parser: newline final unico e hashes fixos.
    po = read_bytes(PARSER_OUTPUT)
    if po.endswith(b"\n") and not po.endswith(b"\n\n"):
        ok("saida do parser: newline final unico")
    else:
        bad("saida do parser: newline final unico ausente/duplicado")

    checks = [
        ("output_sha256", sha256(po)),
        ("output_git_blob_oid", git_blob_oid(po)),
        ("parser_git_blob_oid", git_blob_oid(read_bytes(PARSER))),
        ("parser_test_git_blob_oid", git_blob_oid(read_bytes(PARSER_TEST))),
    ]
    for key, actual in checks:
        if actual == EXPECTED[key]:
            ok(f"{key} == {EXPECTED[key]}")
        else:
            bad(f"{key}", f"obtido {actual}, esperado {EXPECTED[key]}")

    print(f"\nResumo: {passed} OK, {failed} falha(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
