#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditor estático determinístico do fonte upstream do Beam Patcher (ETAPA 2O-D1).

Produz um inventário reproduzível de um clone LOCAL e TEMPORÁRIO do Beam Patcher
(fora do repositório FaithRO), sem construir, executar ou importar nada do Beam.
A saída é um JSON usado como evidência da auditoria pré-build e para preencher/
conferir o manifesto versionado em client/patcher/beam-audit/.

Garantias (ver docs/19-preparacao-build-auditavel-beam.md, FASE H):
  * Apenas biblioteca padrão do Python (sem dependências externas).
  * Entrada explícita --source e saída explícita --output (não depende do CWD).
  * Não acessa a internet; não executa arquivos upstream; não importa módulos Beam.
  * Não segue symlinks para fora da árvore; ignora .git como conteúdo de produto.
  * Inventário ordenado; SHA-256 por arquivo; digest determinístico da árvore.
  * Identifica Cargo.toml/Cargo.lock/rust-toolchain(.toml)/tauri.conf.json,
    licenças, workflows, scripts (.bat/.cmd/.ps1/.sh), binários rastreados,
    submódulos, dependências Git/path, features Tauri, comandos externos e URLs.
  * NÃO copia o fonte para o FaithRO; NÃO armazena conteúdo integral de arquivos.
    Apenas trechos curtos e redigidos (uma linha, truncada) como evidência.
  * Código de saída != 0 em falha.
"""
import argparse
import hashlib
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

SCHEMA_VERSION = 1

# Extensões consideradas binárias/proprietárias quando RASTREADAS no upstream.
BINARY_EXTS = (
    ".exe", ".dll", ".msi", ".bin", ".iso", ".grf", ".gpf", ".rgz", ".thor",
    ".beam", ".7z", ".rar", ".zip", ".pak", ".ico", ".icns", ".png", ".jpg",
    ".jpeg", ".gif", ".bmp", ".mp3", ".mp4", ".wav", ".ogg", ".ttf", ".otf",
    ".woff", ".woff2", ".webp",
)
# Scripts executáveis de shell/host.
SCRIPT_EXTS = (".bat", ".cmd", ".ps1", ".sh")
# Arquivos críticos identificados por nome-base.
CRITICAL_BASENAMES = (
    "Cargo.toml", "Cargo.lock", "rust-toolchain", "rust-toolchain.toml",
    "tauri.conf.json", "build.rs", ".gitmodules",
)
LICENSE_HINT = re.compile(r"(?i)(^|/)(LICENSE|COPYING|NOTICE)")
MAX_BYTES_HASH = 64 * 1024 * 1024  # salvaguarda: não ler arquivo gigante inteiro

# Padrões de auditoria de processos (fluxo de execução).
PROC_RE = re.compile(
    r"(Command::new|std::process|tokio::process|cmd\.exe|powershell|"
    r"sh -c|bash -c|shell::open|open::that|\.spawn\(|\.status\(|\.output\()"
)
# Padrões de rede.
NET_RE = re.compile(
    r"(?i)(reqwest|TcpStream|UdpSocket|WebSocket|native-tls|rustls|openssl|"
    r"danger_accept_invalid|accept_invalid)"
)
URL_RE = re.compile(r"(?i)\bhttps?://[a-z0-9._~:/%\-]+")
# Dependências Git/path em Cargo.toml (léxico; não é parser TOML completo).
GIT_DEP_RE = re.compile(r"(?i)\bgit\s*=\s*[\"']([^\"']+)[\"']")
PATH_DEP_RE = re.compile(r"(?i)\bpath\s*=\s*[\"']([^\"']+)[\"']")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def redact_snippet(line):
    """Uma linha curta, sem conteúdo sensível, como evidência."""
    s = line.strip()
    if len(s) > 160:
        s = s[:157] + "..."
    return s


def is_within(base, target):
    """True se target está dentro de base (após resolução de caminho real)."""
    base_r = os.path.realpath(base)
    tgt_r = os.path.realpath(target)
    try:
        return os.path.commonpath([base_r, tgt_r]) == base_r
    except ValueError:
        return False


def walk_files(source):
    """Gera caminhos de arquivo ordenados, ignorando .git e symlinks que
    escapam da árvore."""
    collected = []
    for root, dirs, files in os.walk(source):
        # Nunca descer em .git nem em symlinks de diretório que escapem.
        pruned = []
        for d in dirs:
            full = os.path.join(root, d)
            if d == ".git":
                continue
            if os.path.islink(full) and not is_within(source, full):
                continue
            pruned.append(d)
        dirs[:] = sorted(pruned)
        for fn in sorted(files):
            full = os.path.join(root, fn)
            if os.path.islink(full) and not is_within(source, full):
                continue
            collected.append(full)
    return sorted(collected, key=lambda p: os.path.relpath(p, source).replace("\\", "/"))


def read_text_lines(path):
    try:
        with open(path, "rb") as f:
            data = f.read(MAX_BYTES_HASH)
        return data.decode("utf-8", errors="replace").splitlines()
    except OSError:
        return []


def parse_cargo_toml(path, rel):
    """Extração léxica (sem parser TOML) de dados sensíveis de um Cargo.toml."""
    info = {
        "path": rel,
        "workspace_members": [],
        "is_workspace_root": False,
        "git_dependencies": [],
        "path_dependencies": [],
        "dependency_lines": [],
        "tauri_features": [],
    }
    lines = read_text_lines(path)
    in_members = False
    in_tauri = False
    for line in lines:
        stripped = line.strip()
        low = stripped.lower()
        if low.startswith("members") and "=" in low:
            in_members = "[" in stripped and "]" not in stripped
            for m in re.findall(r"[\"']([^\"']+)[\"']", stripped):
                info["workspace_members"].append(m)
            info["is_workspace_root"] = True
            continue
        if in_members:
            for m in re.findall(r"[\"']([^\"']+)[\"']", stripped):
                info["workspace_members"].append(m)
            if "]" in stripped:
                in_members = False
            continue
        gm = GIT_DEP_RE.search(stripped)
        if gm:
            info["git_dependencies"].append({"line": redact_snippet(stripped),
                                             "git": gm.group(1)})
        pm = PATH_DEP_RE.search(stripped)
        if pm:
            info["path_dependencies"].append({"line": redact_snippet(stripped),
                                              "path": pm.group(1)})
        # Features Tauri: capturar strings dentro de blocos features = [ ... ]
        if "tauri" in low and "features" in low:
            in_tauri = "[" in stripped and "]" not in stripped
            for f in re.findall(r"[\"']([^\"']+)[\"']", stripped):
                if f not in ("tauri", "tauri-build"):
                    info["tauri_features"].append(f)
            continue
        if in_tauri:
            for f in re.findall(r"[\"']([^\"']+)[\"']", stripped):
                info["tauri_features"].append(f)
            if "]" in stripped:
                in_tauri = False
            continue
        if low.startswith(("tokio", "serde", "reqwest", "tauri", "flate2",
                            "sha2", "md5", "anyhow", "thiserror", "tracing",
                            "futures", "bytes", "async-trait", "serde_yaml",
                            "serde_json")) and "=" in stripped:
            info["dependency_lines"].append(redact_snippet(stripped))
    # Normalizar / deduplicar mantendo ordem determinística.
    info["workspace_members"] = sorted(set(info["workspace_members"]))
    info["tauri_features"] = sorted(set(info["tauri_features"]))
    return info


def parse_tauri_conf(path, rel):
    """Achados de segurança do tauri.conf.json (parse JSON tolerante)."""
    out = {"path": rel, "parsed": False}
    lines = read_text_lines(path)
    try:
        data = json.loads("\n".join(lines))
    except (json.JSONDecodeError, ValueError):
        return out
    out["parsed"] = True
    tauri = data.get("tauri", {}) if isinstance(data, dict) else {}
    allow = tauri.get("allowlist", {}) or {}
    http = allow.get("http", {}) or {}
    shell = allow.get("shell", {}) or {}
    dialog = allow.get("dialog", {}) or {}
    fs = allow.get("fs", {}) or {}
    updater = tauri.get("updater", {}) or {}
    security = tauri.get("security", {}) or {}
    bundle = tauri.get("bundle", {}) or {}
    out["allowlist_all"] = allow.get("all")
    out["http_all"] = http.get("all")
    out["http_scope"] = http.get("scope")
    out["shell_open"] = shell.get("open")
    out["shell_all"] = shell.get("all")
    out["dialog_open"] = dialog.get("open")
    out["dialog_save"] = dialog.get("save")
    out["fs_scope"] = fs.get("scope")
    out["updater_active"] = updater.get("active")
    out["updater_endpoints"] = updater.get("endpoints")
    out["updater_dialog"] = updater.get("dialog")
    out["csp"] = security.get("csp")
    out["bundle_active"] = bundle.get("active")
    out["bundle_targets"] = bundle.get("targets")
    return out


def scan_source(source, rel, path, findings):
    """Coleta ocorrências de processo/rede/URLs em arquivos textuais de código."""
    if not rel.endswith((".rs", ".toml", ".json", ".yml", ".yaml", ".js", ".ts",
                         ".html")):
        return
    for i, line in enumerate(read_text_lines(path), 1):
        if PROC_RE.search(line):
            findings["process"].append({"file": rel, "line": i,
                                        "evidence": redact_snippet(line)})
        if NET_RE.search(line):
            findings["network"].append({"file": rel, "line": i,
                                        "evidence": redact_snippet(line)})
        for m in URL_RE.finditer(line):
            findings["urls"].append(m.group(0))


def build_audit(source):
    files = walk_files(source)
    if not files:
        raise SystemExit("Fonte vazio ou inacessível: %s" % source)

    inventory = []
    tree_lines = []
    critical_files = []
    scripts = []
    binaries = []
    licenses = []
    workflows = []
    cargo_tomls = []
    tauri_confs = []
    build_scripts = []
    has_cargo_lock = False
    has_rust_toolchain = False
    findings = {"process": [], "network": [], "urls": []}

    for path in files:
        rel = os.path.relpath(path, source).replace("\\", "/")
        try:
            size = os.path.getsize(path)
        except OSError:
            size = -1
        digest = sha256_file(path) if 0 <= size <= MAX_BYTES_HASH else ""
        ext = os.path.splitext(rel)[1].lower()
        base = os.path.basename(rel)
        entry = {"path": rel, "size": size, "sha256": digest, "ext": ext}
        inventory.append(entry)
        tree_lines.append("%s\0%s" % (rel, digest))

        if base in CRITICAL_BASENAMES or LICENSE_HINT.search(rel):
            critical_files.append(entry)
        if base == "Cargo.lock":
            has_cargo_lock = True
        if base in ("rust-toolchain", "rust-toolchain.toml"):
            has_rust_toolchain = True
        if LICENSE_HINT.search(rel):
            licenses.append(rel)
        if base == "Cargo.toml":
            cargo_tomls.append(parse_cargo_toml(path, rel))
        if base == "tauri.conf.json":
            tauri_confs.append(parse_tauri_conf(path, rel))
        if base == "build.rs":
            build_scripts.append(rel)
        if ext in SCRIPT_EXTS:
            scripts.append(rel)
        if ext in BINARY_EXTS:
            binaries.append({"path": rel, "size": size, "sha256": digest})
        if "/.github/workflows/" in ("/" + rel) or rel.startswith(".github/workflows/") \
                or "/workflows/" in ("/" + rel):
            if rel.endswith((".yml", ".yaml")):
                workflows.append(rel)

        scan_source(source, rel, path, findings)

    # Digest determinístico da árvore.
    tree_blob = "\n".join(sorted(tree_lines)).encode("utf-8")
    tree_digest = hashlib.sha256(tree_blob).hexdigest()

    # Submódulos.
    submodules = []
    gm_path = os.path.join(source, ".gitmodules")
    if os.path.isfile(gm_path):
        for line in read_text_lines(gm_path):
            m = re.search(r"(?i)\burl\s*=\s*(\S+)", line)
            if m:
                submodules.append(m.group(1))

    # Consolidar dependências Git/path do workspace.
    git_deps = []
    path_deps = []
    workspace_members = []
    tauri_features = []
    for c in cargo_tomls:
        git_deps.extend(c["git_dependencies"])
        path_deps.extend(c["path_dependencies"])
        workspace_members.extend(c["workspace_members"])
        tauri_features.extend(c["tauri_features"])

    audit = {
        "schema_version": SCHEMA_VERSION,
        "project": "Beam Patcher",
        "audit_scope": "static-pre-build",
        "source_executed": False,
        "source_built": False,
        "binary_created": False,
        "tree_digest_algorithm": "sha256",
        "tree_digest": tree_digest,
        "file_count": len(inventory),
        "cargo_lock_present_upstream": has_cargo_lock,
        "rust_toolchain_file_present": has_rust_toolchain,
        "workspace_members": sorted(set(workspace_members)),
        "tauri_features": sorted(set(tauri_features)),
        "critical_files": critical_files,
        "licenses": sorted(set(licenses)),
        "workflows": sorted(set(workflows)),
        "shell_scripts": sorted(set(scripts)),
        "build_scripts": sorted(set(build_scripts)),
        "tracked_binaries": binaries,
        "submodule_urls": sorted(set(submodules)),
        "git_dependencies": git_deps,
        "path_dependencies": path_deps,
        "tauri_config": tauri_confs,
        "process_findings": findings["process"],
        "network_findings": findings["network"],
        "external_urls": sorted(set(findings["urls"])),
        "inventory": inventory,
    }
    return audit


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Auditoria estática determinística do fonte upstream do Beam "
                    "Patcher (não constrói, não executa, não copia o fonte).")
    parser.add_argument("--source", required=True,
                        help="Diretório do clone temporário do Beam (fora do FaithRO).")
    parser.add_argument("--output", required=True,
                        help="Arquivo JSON de saída com o inventário da auditoria.")
    args = parser.parse_args(argv)

    source = os.path.abspath(args.source)
    if not os.path.isdir(source):
        print("ERRO: --source não é um diretório: %s" % source, file=sys.stderr)
        return 2
    # Recusar auditar dentro do próprio FaithRO (o fonte deve ser externo).
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if is_within(repo, source):
        print("ERRO: --source está dentro do repositório FaithRO; o fonte "
              "upstream deve permanecer externo.", file=sys.stderr)
        return 2

    audit = build_audit(source)

    out = os.path.abspath(args.output)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(audit, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    print("Auditoria upstream: OK")
    print("Arquivos inventariados: %d" % audit["file_count"])
    print("tree_digest (sha256): %s" % audit["tree_digest"])
    print("Cargo.lock presente: %s" % audit["cargo_lock_present_upstream"])
    print("rust-toolchain presente: %s" % audit["rust_toolchain_file_present"])
    print("Binários rastreados: %d" % len(audit["tracked_binaries"]))
    print("Saída: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
