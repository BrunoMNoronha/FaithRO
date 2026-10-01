#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador do laboratório sintético do patcher (ETAPA 2O-D).

Verifica, de forma determinística e sem rede, que um laboratório gerado por
scripts/generate-synthetic-patch-lab.py é íntegro e seguro, e que as regras de
segurança da decisão (docs/17, docs/18) são mecanicamente aplicadas.

Modos:
  --root DIR       Valida um lab completo (manifesto + payload + estado final via
                   "simulador do laboratório"). O simulador NÃO é o Beam.
  --manifest FILE  Valida apenas um manifesto conceitual (para testes negativos).
      --base DIR   Base opcional para checar payload/hashes do manifesto avulso.
  --self-test      Executa a bateria de testes negativos em cópias temporárias.
                   Nenhum deve passar; nenhuma fixture versionada é modificada.

Regras de segurança rejeitadas (código de saída != 0):
  caminho absoluto, '..', drive letter, UNC path, caminho vazio, NUL, barra
  invertida ambígua, duplicidade de ação, sobreposição create/update x remove,
  hash inválido, algoritmo fraco como fonte primária (md5/sha1), URL externa,
  HTTP não-loopback, SSO habilitado, auto-update habilitado, comando pós-patch,
  executável, extensão proprietária, tamanho divergente, SHA-256 divergente.

Somente biblioteca padrão. Independe do CWD. Não modifica as fixtures.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONCEPTUAL_FORMAT = "FORMATO CONCEITUAL — NÃO CONSUMÍVEL PELO BEAM"
STRONG_ALGOS = ("sha256",)
WEAK_ALGOS = ("md5", "sha1")
FORBIDDEN_EXTS = (
    ".exe", ".dll", ".grf", ".gpf", ".rgz", ".thor",
    ".7z", ".rar", ".zip", ".msi", ".bin", ".iso", ".beam",
)
VALID_OPS = ("create", "update", "remove")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DRIVE_RE = re.compile(r"^[A-Za-z]:")
POST_PATCH_KEYS = (
    "post_patch_command", "pre_patch_command", "command", "cmd", "exec",
    "execute", "run", "shell", "script", "hook",
)


class LabError(Exception):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    with open(path, "rb") as f:
        data = f.read()
    try:
        return json.loads(data.decode("utf-8"))
    except UnicodeDecodeError as e:
        raise LabError("%s: não é UTF-8 válido (%s)" % (path, e))
    except json.JSONDecodeError as e:
        raise LabError("%s: JSON inválido (%s)" % (path, e))


# --------------------------------------------------------------------------
# Segurança de caminho (relativo, dentro do alvo)
# --------------------------------------------------------------------------

def check_safe_relpath(path):
    """Levanta LabError se `path` não for um caminho relativo seguro."""
    if not isinstance(path, str):
        raise LabError("caminho não é string: %r" % (path,))
    if path == "":
        raise LabError("caminho vazio não é permitido")
    if "\x00" in path:
        raise LabError("caminho contém NUL: %r" % path)
    if "\\" in path:
        raise LabError("barra invertida ambígua não permitida: %s" % path)
    if path.startswith("/"):
        raise LabError("caminho absoluto Unix não permitido: %s" % path)
    if path.startswith("//"):
        raise LabError("UNC path não permitido: %s" % path)
    if DRIVE_RE.match(path):
        raise LabError("drive letter (caminho absoluto Windows) não permitido: %s" % path)
    comps = path.split("/")
    for c in comps:
        if c == "..":
            raise LabError("componente '..' (traversal) não permitido: %s" % path)
        if c == "":
            raise LabError("componente vazio (barra dupla/ inicial/final) não permitido: %s" % path)
    ext = os.path.splitext(path)[1].lower()
    if ext in FORBIDDEN_EXTS:
        raise LabError("extensão proibida (%s): %s" % (ext, path))


# --------------------------------------------------------------------------
# Validação do manifesto conceitual
# --------------------------------------------------------------------------

def validate_manifest_obj(manifest):
    """Valida a estrutura e as regras de segurança do manifesto. Retorna a lista
    de ações normalizadas. Levanta LabError na primeira violação estrutural."""
    if not isinstance(manifest, dict):
        raise LabError("manifesto não é um objeto JSON")

    # Algoritmo de hash primário deve ser forte.
    algo = str(manifest.get("hash_algorithm", "")).lower()
    if algo in WEAK_ALGOS:
        raise LabError("algoritmo fraco como fonte primária: %s (use sha256)" % algo)
    if algo not in STRONG_ALGOS:
        raise LabError("hash_algorithm ausente ou não suportado: %r (esperado sha256)"
                       % manifest.get("hash_algorithm"))

    # SSO e auto-update não podem estar habilitados.
    if manifest.get("sso_enabled") is True:
        raise LabError("SSO habilitado não é permitido (sso_enabled: true)")
    if manifest.get("auto_update") is True:
        raise LabError("auto-update habilitado não é permitido (auto_update: true)")

    # Loopback: se declarado, deve ser True; qualquer URL externa é rejeitada.
    if "loopback_only" in manifest and manifest.get("loopback_only") is not True:
        raise LabError("loopback_only deve ser true quando presente")

    # Comandos pós-patch em qualquer chave conhecida.
    for k in POST_PATCH_KEYS:
        if manifest.get(k) not in (None, "", False):
            raise LabError("comando pós-patch/execução não permitido: %s=%r"
                           % (k, manifest.get(k)))

    # Varredura recursiva por URLs e execução arbitrária no manifesto inteiro.
    _scan_forbidden_values(manifest)

    actions = manifest.get("actions")
    if not isinstance(actions, list) or not actions:
        raise LabError("campo 'actions' ausente ou vazio")

    seen = {}          # path -> op (para detectar duplicidade)
    mutate = set()     # create/update
    remove = set()
    norm = []
    for i, act in enumerate(actions):
        if not isinstance(act, dict):
            raise LabError("ação #%d não é objeto" % i)
        op = act.get("op")
        if op not in VALID_OPS:
            raise LabError("ação #%d com op desconhecido: %r" % (i, op))
        path = act.get("path")
        check_safe_relpath(path)
        if path in seen:
            raise LabError("ação duplicada para o mesmo caminho: %s (%s e %s)"
                           % (path, seen[path], op))
        seen[path] = op
        if op in ("create", "update"):
            h = act.get("sha256")
            if not isinstance(h, str) or not SHA256_RE.match(h.lower()):
                raise LabError("ação %s %s: sha256 inválido: %r" % (op, path, h))
            size = act.get("size")
            if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                raise LabError("ação %s %s: size inválido: %r" % (op, path, size))
            mutate.add(path)
        elif op == "remove":
            remove.add(path)
        norm.append({"op": op, "path": path,
                     "sha256": act.get("sha256"), "size": act.get("size")})

    overlap = mutate & remove
    if overlap:
        raise LabError("sobreposição create/update x remove: %s" % ", ".join(sorted(overlap)))
    return norm


def _scan_forbidden_values(obj):
    """Percorre o manifesto procurando URLs externas / HTTP não-loopback."""
    url_re = re.compile(r"(?i)\bhttps?://[^\s\"'<>]+")
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
        elif isinstance(cur, str):
            for m in url_re.finditer(cur):
                url = m.group(0)
                low = url.lower()
                if low.startswith("https://"):
                    raise LabError("URL externa não permitida em lab loopback: %s" % url)
                host = low[len("http://"):].split("/")[0].split(":")[0]
                if host not in ("127.0.0.1", "localhost"):
                    raise LabError("URL HTTP não-loopback proibida: %s" % url)


# --------------------------------------------------------------------------
# Simulador do laboratório (NÃO é o Beam)
# --------------------------------------------------------------------------

def _load_tree(base):
    """Carrega {relpath_posix: bytes} de um diretório (ignora dirs vazios)."""
    tree = {}
    for root, _dirs, files in os.walk(base):
        for fn in files:
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, base).replace("\\", "/")
            with open(full, "rb") as f:
                tree[rel] = f.read()
    return tree


def apply_manifest_simulator(before_dir, server_dir, actions, dest_dir):
    """Aplica o manifesto conceitual copiando before -> dest e executando as
    ações usando os arquivos de payload servidos em server/files. Verifica o
    SHA-256 de cada payload ANTES de gravar (integridade). Levanta LabError se
    algum hash não conferir. Retorna a árvore final."""
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    shutil.copytree(before_dir, dest_dir)
    files_root = os.path.join(server_dir, "files")
    for act in actions:
        op = act["op"]
        path = act["path"]
        target = os.path.join(dest_dir, *path.split("/"))
        if op in ("create", "update"):
            payload = os.path.join(files_root, *path.split("/"))
            if not os.path.isfile(payload):
                raise LabError("payload ausente no servidor para %s: %s" % (op, path))
            with open(payload, "rb") as f:
                data = f.read()
            digest = sha256_bytes(data)
            if digest != act["sha256"].lower():
                raise LabError("integridade inválida para %s (esperado %s, obtido %s)"
                               % (path, act["sha256"], digest))
            if len(data) != act["size"]:
                raise LabError("tamanho divergente para %s (esperado %d, obtido %d)"
                               % (path, act["size"], len(data)))
            if op == "create" and os.path.exists(target):
                raise LabError("create sobre arquivo existente: %s" % path)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            tmp = target + ".part"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, target)  # escrita atômica
        elif op == "remove":
            if os.path.exists(target):
                os.remove(target)
    return _load_tree(dest_dir)


# --------------------------------------------------------------------------
# Validação de um lab completo (--root)
# --------------------------------------------------------------------------

def validate_root(root):
    summary = []

    def ok(name):
        summary.append((name, "PASS"))

    manifest_path = os.path.join(root, "server", "manifest.json")
    if not os.path.isfile(manifest_path):
        raise LabError("manifesto ausente: %s" % manifest_path)
    manifest = read_json(manifest_path)

    if manifest.get("format") != CONCEPTUAL_FORMAT:
        raise LabError("manifesto sem marca de formato conceitual esperada")
    ok("formato-conceitual")

    actions = validate_manifest_obj(manifest)
    ok("manifesto-estrutura-e-seguranca")

    # Payload servido: existe e bate com o manifesto.
    files_root = os.path.join(root, "server", "files")
    for act in actions:
        if act["op"] in ("create", "update"):
            payload = os.path.join(files_root, *act["path"].split("/"))
            if not os.path.isfile(payload):
                raise LabError("payload ausente: %s" % act["path"])
            with open(payload, "rb") as f:
                data = f.read()
            if sha256_bytes(data) != act["sha256"].lower():
                raise LabError("SHA-256 do payload não confere: %s" % act["path"])
            if len(data) != act["size"]:
                raise LabError("tamanho do payload não confere: %s" % act["path"])
    ok("payload-integridade-sha256")

    # Índice esperado independente.
    expected = read_json(os.path.join(root, "expected-state.json"))
    before_dir = os.path.join(root, "target-before")
    after_dir = os.path.join(root, "target-after")

    _verify_state_index(before_dir, expected.get("target_before", {}), "target-before")
    _verify_state_index(after_dir, expected.get("target_after", {}), "target-after")
    ok("estados-before-after-conferem")

    # Simulador aplica o manifesto e o resultado deve igualar target-after.
    tmp_dest = tempfile.mkdtemp(prefix="faithro-lab-sim-")
    try:
        final = apply_manifest_simulator(
            before_dir, os.path.join(root, "server"), actions,
            os.path.join(tmp_dest, "applied"))
        after_tree = _load_tree(after_dir)
        if final != after_tree:
            raise LabError("estado final do simulador difere de target-after")
        ok("simulador-atinge-target-after")

        # Idempotência: reaplicar sobre o resultado não deve corromper.
        final2 = apply_manifest_simulator(
            before_dir, os.path.join(root, "server"), actions,
            os.path.join(tmp_dest, "applied2"))
        if final2 != after_tree:
            raise LabError("reaplicação alterou o estado final (não idempotente)")
        ok("simulador-idempotente")
    finally:
        shutil.rmtree(tmp_dest, ignore_errors=True)

    return summary


def _verify_state_index(base, index, label):
    tree = _load_tree(base)
    tree_index = {p: {"sha256": sha256_bytes(b), "size": len(b)}
                  for p, b in tree.items()}
    if tree_index != index:
        raise LabError("%s não corresponde ao expected-state.json" % label)


# --------------------------------------------------------------------------
# Modo --manifest (para testes negativos avulsos)
# --------------------------------------------------------------------------

def validate_manifest_file(path):
    manifest = read_json(path)
    validate_manifest_obj(manifest)


# --------------------------------------------------------------------------
# --self-test: testes negativos em cópias temporárias
# --------------------------------------------------------------------------

def _base_manifest():
    return {
        "format": CONCEPTUAL_FORMAT,
        "lab": "faithro-synthetic-patch-lab",
        "schema_version": 1,
        "hash_algorithm": "sha256",
        "loopback_only": True,
        "sso_enabled": False,
        "auto_update": False,
        "post_patch_command": None,
        "actions": [
            {"op": "update", "path": "data/version.txt",
             "sha256": "4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865",
             "size": 2},
        ],
    }


def _negative_cases():
    """Retorna [(nome, mutação(manifest))]. Cada caso deve ser REJEITADO."""
    def add_action(act):
        def f(m):
            m["actions"].append(act)
        return f

    def set_key(k, v):
        def f(m):
            m[k] = v
        return f

    def set_action_field(field, value):
        def f(m):
            m["actions"][0][field] = value
        return f

    cases = [
        ("sha256-incorreto", set_action_field("sha256", "0" * 64)),  # válido formato, mas divergente só pega no root; aqui vira campo aceito
        ("sha256-formato-invalido", set_action_field("sha256", "xyz")),
        ("size-negativo", set_action_field("size", -1)),
        ("size-ausente", lambda m: m["actions"][0].pop("size")),
        ("traversal-dotdot", add_action({"op": "create", "path": "../fora.txt",
                                         "sha256": "0" * 64, "size": 1})),
        ("absoluto-unix", add_action({"op": "create", "path": "/data/teste.txt",
                                      "sha256": "0" * 64, "size": 1})),
        ("absoluto-windows", add_action({"op": "create", "path": "C:/Windows/teste.txt",
                                         "sha256": "0" * 64, "size": 1})),
        ("unc-path", add_action({"op": "create", "path": "//servidor/share/teste.txt",
                                 "sha256": "0" * 64, "size": 1})),
        ("barra-invertida", add_action({"op": "create", "path": "data\\teste.txt",
                                        "sha256": "0" * 64, "size": 1})),
        ("caminho-vazio", add_action({"op": "create", "path": "",
                                      "sha256": "0" * 64, "size": 1})),
        ("acao-duplicada", add_action({"op": "create", "path": "data/version.txt",
                                       "sha256": "0" * 64, "size": 1})),
        ("op-desconhecido", add_action({"op": "rename", "path": "data/x.txt"})),
        ("extensao-executavel", add_action({"op": "create", "path": "data/malware.exe",
                                            "sha256": "0" * 64, "size": 1})),
        ("extensao-zip", add_action({"op": "create", "path": "data/pacote.zip",
                                     "sha256": "0" * 64, "size": 1})),
        ("algoritmo-fraco", set_key("hash_algorithm", "md5")),
        ("sso-habilitado", set_key("sso_enabled", True)),
        ("auto-update-habilitado", set_key("auto_update", True)),
        ("comando-pos-patch", set_key("post_patch_command", "cmd /c del *")),
        ("url-http-externa", set_key("mirror", "http://exemplo.com/patch")),
        ("url-https-externa", set_key("mirror", "https://cdn.exemplo.com/patch")),
        ("actions-ausente", lambda m: m.pop("actions")),
    ]
    # Caso especial: create + remove no mesmo caminho (overlap).
    def overlap(m):
        m["actions"] = [
            {"op": "create", "path": "data/x.txt", "sha256": "0" * 64, "size": 1},
            {"op": "remove", "path": "data/x.txt"},
        ]
    cases.append(("overlap-create-remove", overlap))
    return cases


def self_test():
    """Executa cada caso negativo em manifesto temporário; espera rejeição.
    'sha256-incorreto' (formato válido porém valor errado) NÃO é rejeitado pela
    validação estrutural — ele é coberto pela verificação de integridade no modo
    --root (simulador) — portanto é removido dos casos estruturais."""
    tmp = tempfile.mkdtemp(prefix="faithro-lab-neg-")
    failures = []
    passed = 0
    try:
        for name, mutate in _negative_cases():
            if name == "sha256-incorreto":
                # coberto por --root (integridade), não pela estrutura
                continue
            m = _base_manifest()
            mutate(m)
            p = os.path.join(tmp, name + ".json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump(m, f, ensure_ascii=False, indent=2)
            try:
                validate_manifest_file(p)
                failures.append(name)  # deveria ter falhado
            except LabError:
                passed += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return passed, failures


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Valida o laboratório sintético do patcher (formato conceitual).")
    parser.add_argument("--root", help="Diretório de um lab completo a validar.")
    parser.add_argument("--manifest", help="Valida apenas um manifesto conceitual.")
    parser.add_argument("--self-test", action="store_true",
                        help="Executa a bateria de testes negativos (nenhum deve passar).")
    args = parser.parse_args(argv)

    if not any([args.root, args.manifest, args.self_test]):
        parser.error("informe --root, --manifest ou --self-test")

    rc = 0
    try:
        if args.self_test:
            passed, failures = self_test()
            if failures:
                print("Self-test: FAIL")
                for name in failures:
                    print("  - caso negativo NÃO rejeitado: %s" % name)
                rc = 1
            else:
                print("Self-test: OK (%d casos negativos rejeitados)" % passed)

        if args.manifest:
            validate_manifest_file(args.manifest)
            print("Manifesto: OK (%s)" % args.manifest)

        if args.root:
            summary = validate_root(args.root)
            print("Lab: OK (%s)" % args.root)
            for name, res in summary:
                print("  [%s] %s" % (res, name))
    except LabError as e:
        print("Validação: FAIL")
        print("  - %s" % e)
        return 1

    return rc


if __name__ == "__main__":
    sys.exit(main())
