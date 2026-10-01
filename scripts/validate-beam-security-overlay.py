#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador do overlay de segurança de laboratório do Beam Patcher (ETAPA 2O-D1).

Verifica, de forma determinística e sem build, que o patch
client/patcher/beam-audit/overlays/beam-lab-security.patch:
  * aplica-se ao commit fixado do fonte upstream (clone temporário externo);
  * é textual (sem bloco binário) e limitado ao escopo de segurança;
  * não toca licenças nem adiciona fonte de terceiros (nenhum arquivo novo);
  * desabilita o updater do Tauri e esvazia os endpoints;
  * restringe o HTTP a loopback (remove curingas e domínios externos);
  * desabilita shell.open;
  * define uma CSP não nula;
  * desabilita o bundle/installer e evita targets "all";
  * remove as features Tauri http-all/shell-open/updater;
  * bloqueia o lançamento de cliente, setup e SSO no laboratório.

Regras (ver docs/19, FASE O):
  * Apenas biblioteca padrão do Python.
  * NÃO aplica o patch no repositório FaithRO; usa cópia temporária do --source.
  * Só chama o executável `git` (nunca cargo/rustc/node/npm/powershell/cmd).
  * Código de saída != 0 em qualquer falha; remove a cópia temporária ao final.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

EXPECTED_COMMIT = "feed97887090d121f796bc1b941390e28b7a2da5"

# Arquivos que o overlay pode legitimamente tocar (somente segurança).
ALLOWED_FILES = {
    "beam-ui/tauri.conf.json",
    "beam-ui/Cargo.toml",
    "beam-ui/src/commands.rs",
    "beam-core/src/sso.rs",
}
# Hosts permitidos no laboratório.
LOOPBACK_HOSTS = ("127.0.0.1", "localhost")
# Host interno do protocolo asset do Tauri (permitido na CSP).
ASSET_HOST = "asset.localhost"

errors = []


def fail(msg):
    errors.append(msg)


def git(args, cwd=None):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)


def parse_touched_files(patch_text):
    """Retorna (touched, added_files) a partir dos cabeçalhos do diff."""
    touched = []
    added = []
    for line in patch_text.splitlines():
        m = re.match(r"^diff --git a/(.+?) b/(.+)$", line)
        if m:
            touched.append(m.group(2))
        if line.startswith("new file mode"):
            added.append(touched[-1] if touched else "<desconhecido>")
        if line.startswith("--- /dev/null"):
            # criação de arquivo
            added.append(touched[-1] if touched else "<desconhecido>")
    return touched, added


def check_scope(patch_text):
    touched, added = parse_touched_files(patch_text)
    if not touched:
        fail("patch não contém nenhum diff reconhecível")
    for f in touched:
        if re.search(r"(^|/)(LICENSE|COPYING|NOTICE)", f, re.IGNORECASE):
            fail("patch toca arquivo de licença: %s" % f)
        if f not in ALLOWED_FILES:
            fail("patch fora do escopo de segurança: %s" % f)
    if added:
        fail("patch adiciona/cria arquivo(s) novo(s) (proibido): %s" % ", ".join(sorted(set(added))))
    if "GIT binary patch" in patch_text:
        fail("patch contém bloco binário (proibido)")


def check_tauri_conf(root):
    path = os.path.join(root, "beam-ui", "tauri.conf.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        fail("tauri.conf.json inválido após overlay: %s" % e)
        return
    tauri = data.get("tauri", {})
    allow = tauri.get("allowlist", {})
    http = allow.get("http", {})
    shell = allow.get("shell", {})
    updater = tauri.get("updater", {})
    security = tauri.get("security", {})
    bundle = tauri.get("bundle", {})

    if http.get("all") is not False:
        fail("http.all deve ser false no laboratório")
    for url in (http.get("scope") or []):
        host = re.sub(r"(?i)^https?://", "", url).split("/")[0].split(":")[0]
        if host not in LOOPBACK_HOSTS:
            fail("http.scope contém host não-loopback: %s" % url)
    if shell.get("open") is not False:
        fail("shell.open deve ser false no laboratório")
    if updater.get("active") is not False:
        fail("updater.active deve ser false no laboratório")
    if updater.get("endpoints"):
        fail("updater.endpoints deve estar vazio no laboratório")
    csp = security.get("csp")
    if not isinstance(csp, str) or not csp.strip():
        fail("security.csp deve ser uma string não vazia (CSP definida)")
    else:
        # A CSP não pode liberar conexões externas (apenas self/loopback/asset).
        for m in re.finditer(r"(?i)\bhttps?://([a-z0-9._-]+)", csp):
            host = m.group(1)
            if host not in LOOPBACK_HOSTS and host != ASSET_HOST:
                fail("CSP referencia host externo: %s" % host)
    if bundle.get("active") is not False:
        fail("bundle.active deve ser false no primeiro build")
    if bundle.get("targets") == "all":
        fail('bundle.targets não pode ser "all"')

    # Nenhum executável de jogo configurado no overlay.
    blob = json.dumps(data)
    if re.search(r"(?i)\.exe\b", blob):
        fail("tauri.conf.json referencia um .exe após overlay (não permitido)")


def check_cargo_features(root):
    path = os.path.join(root, "beam-ui", "Cargo.toml")
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        fail("beam-ui/Cargo.toml ilegível: %s" % e)
        return
    for feat in ("http-all", "shell-open", "updater"):
        if re.search(r'"%s"' % re.escape(feat), text):
            fail("feature Tauri de risco ainda presente: %s" % feat)


def check_launch_guards(root):
    cmds = os.path.join(root, "beam-ui", "src", "commands.rs")
    sso = os.path.join(root, "beam-core", "src", "sso.rs")
    try:
        ctext = open(cmds, "r", encoding="utf-8").read()
        stext = open(sso, "r", encoding="utf-8").read()
    except OSError as e:
        fail("fonte esperado ilegível após overlay: %s" % e)
        return
    if "client launch disabled by security overlay" not in ctext:
        fail("lançamento de cliente não foi bloqueado")
    if "setup launch disabled by security overlay" not in ctext:
        fail("lançamento de setup não foi bloqueado")
    if re.search(r"Command::new\(&client_exe\)", ctext):
        fail("Command::new(&client_exe) ainda presente")
    if re.search(r"Command::new\(&setup_exe_path\)", ctext):
        fail("Command::new(&setup_exe_path) ainda presente")
    if "SSO game launch disabled by security overlay" not in stext:
        fail("lançamento via SSO não foi bloqueado")
    if re.search(r"std::process::Command::new\(executable\)", stext):
        fail("std::process::Command::new(executable) ainda presente no SSO")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Valida o overlay de segurança de laboratório do Beam Patcher "
                    "contra um clone temporário do commit fixado.")
    parser.add_argument("--source",
                        help="Clone temporário do Beam (fora do FaithRO), no commit fixado.")
    parser.add_argument("--patch", required=True,
                        help="Caminho do overlay .patch a validar.")
    parser.add_argument("--commit", default=EXPECTED_COMMIT,
                        help="Commit upstream esperado (default: commit fixado).")
    parser.add_argument("--static-only", action="store_true",
                        help="Valida apenas o patch (escopo/textual/sem binário), "
                             "sem clone do upstream. Para CI sem acesso externo.")
    args = parser.parse_args(argv)

    patch = os.path.abspath(args.patch)
    if not os.path.isfile(patch):
        print("ERRO: --patch não existe: %s" % patch, file=sys.stderr)
        return 2

    if args.static_only:
        with open(patch, "r", encoding="utf-8", errors="replace") as f:
            check_scope(f.read())
        if errors:
            print("Overlay de segurança (estático): FAIL")
            for e in errors:
                print("  - " + e)
            return 1
        print("Overlay de segurança (estático): OK")
        print("Patch textual, no escopo, sem binário/licença/arquivo novo.")
        return 0

    if not args.source:
        print("ERRO: --source é obrigatório (ou use --static-only)", file=sys.stderr)
        return 2
    source = os.path.abspath(args.source)
    if not os.path.isdir(source):
        print("ERRO: --source não é diretório: %s" % source, file=sys.stderr)
        return 2

    # Nunca aplicar no FaithRO.
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.commonpath([os.path.realpath(repo), os.path.realpath(source)]) == os.path.realpath(repo):
        print("ERRO: --source está dentro do FaithRO; o overlay não pode ser "
              "aplicado no repositório.", file=sys.stderr)
        return 2

    with open(patch, "r", encoding="utf-8", errors="replace") as f:
        patch_text = f.read()

    # Escopo e ausência de binário/licença/arquivo novo.
    check_scope(patch_text)

    # Confirmar base = commit fixado (se --source for repositório git).
    r = git(["rev-parse", "HEAD"], cwd=source)
    if r.returncode == 0:
        head = r.stdout.strip()
        if not head.startswith(args.commit[:10]):
            fail("HEAD do --source (%s) não corresponde ao commit fixado (%s)"
                 % (head[:12], args.commit[:12]))
    else:
        fail("não foi possível confirmar o commit base do --source")

    # git apply --check contra o próprio clone (não modifica o clone).
    r = git(["apply", "--check", patch], cwd=source)
    if r.returncode != 0:
        fail("git apply --check falhou: %s" % (r.stderr.strip() or r.stdout.strip()))

    # Aplicar em cópia temporária e validar semanticamente.
    tmp = tempfile.mkdtemp(prefix="faithro-overlay-check-")
    try:
        dst = os.path.join(tmp, "src")
        shutil.copytree(source, dst,
                        ignore=shutil.ignore_patterns(".git"))
        r = git(["apply", patch], cwd=dst)
        if r.returncode != 0:
            fail("git apply (cópia temporária) falhou: %s"
                 % (r.stderr.strip() or r.stdout.strip()))
        else:
            check_tauri_conf(dst)
            check_cargo_features(dst)
            check_launch_guards(dst)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if errors:
        print("Overlay de segurança: FAIL")
        for e in errors:
            print("  - " + e)
        return 1

    print("Overlay de segurança: OK")
    print("Patch textual, no escopo, aplicável ao commit fixado.")
    print("Updater desabilitado; HTTP loopback; shell off; CSP definida; "
          "bundle off; lançamentos bloqueados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
