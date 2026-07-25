#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador determinístico da configuração de patcher versionada em
client/patcher/ (ETAPA 2O-C).

Objetivo: garantir que os templates e fixtures do patcher permaneçam textuais,
seguros e sem segredos, e que as regras de segurança da decisão
(docs/17-decisao-patcher-launcher.md) sejam mecanicamente verificáveis.

- Usa apenas a biblioteca padrão (sem dependências externas; sem PyYAML).
  Como a stdlib não traz parser YAML, a checagem de .yml/.yaml é LÉXICA
  (linha a linha), suficiente para as regras de segurança abaixo.
- Não acessa nada fora do repositório; não executa binários; não segue symlinks.
- Independe do diretório de execução (usa __file__ para achar a raiz).
- Retorna código != 0 em qualquer violação.

Regras aplicadas em client/patcher/:
  * Allowlist textual de sufixos; extensões binárias/proprietárias rejeitadas.
  * Nenhum arquivo acima de MAX_BYTES; deve ser UTF-8.
  * .json deve ser JSON válido.
  * URLs: https:// sempre permitido; http:// permitido SOMENTE para
    127.0.0.1/localhost e SOMENTE em arquivos de laboratório (nome contém
    "lab" ou caminho contém "fixtures"). Em produção, http:// é rejeitado.
  * Rejeita credenciais/tokens (password/senha/secret/token/api_key/...).
  * Rejeita habilitar SSO (sso.enabled: true) e salvamento de senha.
  * Rejeita comandos pós-patch (post_patch/exec/command/run/cmd).
  * Rejeita caminhos absolutos e componentes ".." em valores e no patchlist.
"""
import json
import os
import re
import sys

# Saída sempre em UTF-8, independentemente do console (Windows cp1252 etc.).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATCHER = os.path.join(REPO, "client", "patcher")

ALLOWED_SUFFIXES = (
    ".md", ".txt", ".json", ".yml", ".yaml", ".example",
    ".patch",  # overlay de segurança de laboratório (client/patcher/beam-audit/overlays/)
    ".gitkeep", ".gitignore",
)
FORBIDDEN_EXTS = (
    ".exe", ".dll", ".grf", ".gpf", ".rgz", ".thor",
    ".7z", ".rar", ".zip", ".msi", ".bin", ".iso",
)
MAX_BYTES = 1024 * 1024  # 1 MiB

# Segredos/credenciais: chave sensível com valor não vazio e não placeholder.
CRED_KEY = re.compile(
    r'(?i)\b(password|passwd|senha|secret|client_secret|token|api[_-]?key|'
    r'authorization|bearer|save_password|remember_password)\b\s*[:=]\s*(\S.*)?$'
)
# Comandos pós-patch / execução arbitrária.
CMD_KEY = re.compile(
    r'(?i)^\s*(post[_-]?patch|pre[_-]?patch|exec|execute|command|cmd|run|'
    r'shell|script|hook)\s*:\s*(\S.*)?$'
)
URL_RE = re.compile(r'(?i)\bhttps?://[^\s"\'<>]+')
SSO_ENABLED_TRUE = re.compile(r'(?i)^\s*enabled\s*:\s*true\b')

errors = []


def fail(msg):
    errors.append(msg)


def rel(path):
    return os.path.relpath(path, REPO).replace("\\", "/")


def is_lab_file(path):
    p = rel(path).lower()
    # beam-audit/ descreve um laboratório loopback-only (manifesto/plano/overlay
    # e schemas da auditoria pré-build do Beam); loopback é esperado ali.
    return ("fixtures/" in p) or ("beam-audit/" in p) or ("lab" in os.path.basename(p))


def _value_is_placeholder(val):
    v = val.strip().strip('"').strip("'")
    # Placeholders <...>, nulos e vazios não são segredos reais.
    return (v == "" or v.lower() in ("null", "none", "false", "true", "[]", "{}")
            or (v.startswith("<") and v.endswith(">")))


def check_urls(path, lineno, line):
    lab = is_lab_file(path)
    for m in URL_RE.finditer(line):
        url = m.group(0)
        low = url.lower()
        if low.startswith("http://"):
            host = low[len("http://"):].split("/")[0].split(":")[0]
            if host not in ("127.0.0.1", "localhost"):
                fail("%s:%d: URL HTTP não-loopback proibida: %s" % (rel(path), lineno, url))
            elif not lab:
                fail("%s:%d: http://127.0.0.1 só é permitido em fixtures/arquivos de laboratório: %s"
                     % (rel(path), lineno, url))
        # https:// é sempre aceito.
    # Produção não deve apontar para loopback.
    if not lab and re.search(r'(?i)\b(127\.0\.0\.1|localhost)\b', line):
        fail("%s:%d: referência a loopback em arquivo de produção" % (rel(path), lineno))


def check_paths(path, lineno, line):
    # Remove URLs antes das checagens de caminho (evita falso positivo do
    # esquema "https://" casar com regra de drive "s:/" e do path do URL).
    cleaned = URL_RE.sub(" ", line)
    # Componente ".." (traversal) em qualquer parte da linha.
    if re.search(r'(^|[\s"\'=:/\\])\.\.([/\\]|$|["\'\s])', cleaned):
        fail("%s:%d: componente '..' não permitido (path traversal): %s"
             % (rel(path), lineno, line.strip()))
    # Caminho absoluto Windows (C:\) ou drive em valor.
    if re.search(r'(?i)(^|[\s"\'=:])[a-z]:[\\/]', cleaned):
        fail("%s:%d: caminho absoluto (drive) não permitido: %s"
             % (rel(path), lineno, line.strip()))


def check_text_line(path, lineno, raw, config_rules):
    """Checa uma linha. Segredos são verificados em todo arquivo textual; as
    regras de configuração (URLs, caminhos, comandos) só em arquivos de dados
    (.yml/.yaml/.json/patchlist), não em documentação .md, que legitimamente
    contém links relativos e URLs de exemplo."""
    line = raw.rstrip("\n")
    stripped = line.strip()
    if stripped.startswith("#") or stripped.startswith(";"):
        return  # comentário
    m = CRED_KEY.search(line)
    if m and not _value_is_placeholder(m.group(2) or ""):
        fail("%s:%d: possível credencial/segredo: %s" % (rel(path), lineno, stripped))
    if not config_rules:
        return
    if CMD_KEY.match(line):
        fail("%s:%d: comando pós-patch/execução não permitido: %s" % (rel(path), lineno, stripped))
    check_urls(path, lineno, line)
    check_paths(path, lineno, line)


def check_sso(path, text):
    # Rejeita sso.enabled: true (bloco YAML por indentação simples).
    lines = text.splitlines()
    in_sso = False
    for i, line in enumerate(lines, 1):
        if re.match(r'(?i)^\s*sso\s*:\s*$', line):
            in_sso = True
            continue
        if in_sso:
            # sai do bloco ao encontrar chave de nível 0 (sem indentação)
            if line and not line[0].isspace() and not line.lstrip().startswith("#"):
                in_sso = False
            elif SSO_ENABLED_TRUE.match(line):
                fail("%s:%d: SSO não pode ser habilitado (sso.enabled: true)" % (rel(path), i))


def check_patchlist(path, text):
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        name = parts[0]
        if name.startswith("/") or re.match(r'(?i)^[a-z]:[\\/]', name) or ".." in name:
            fail("%s:%d: nome de patch inseguro (absoluto/traversal): %s" % (rel(path), i, name))
        if len(parts) >= 2:
            h = parts[1]
            if not re.fullmatch(r'[0-9a-fA-F]{64}', h):
                fail("%s:%d: hash não é SHA-256 hex de 64 caracteres: %s" % (rel(path), i, h))


def check_file(path):
    r = rel(path)
    name = os.path.basename(path)
    ext = os.path.splitext(name)[1].lower()

    if os.path.islink(path):
        fail("%s: link simbólico não permitido em client/patcher/" % r)
        return
    if ext in FORBIDDEN_EXTS:
        fail("%s: extensão proibida (%s) — binário/proprietário não pode ser versionado" % (r, ext))
        return
    if not name.endswith(ALLOWED_SUFFIXES):
        fail("%s: fora da allowlist textual (sufixos: %s)" % (r, ", ".join(ALLOWED_SUFFIXES)))
        return

    if os.path.getsize(path) > MAX_BYTES:
        fail("%s: excede o limite de %d bytes (1 MiB)" % (r, MAX_BYTES))
        return

    try:
        with open(path, "rb") as f:
            data = f.read()
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        fail("%s: não é UTF-8 válido (esperado arquivo textual)" % r)
        return

    if name.endswith(".json"):
        try:
            json.loads(text)
        except json.JSONDecodeError as e:
            fail("%s: JSON inválido (%s)" % (r, e))

    if name.endswith((".yml", ".yaml")) or ".yml." in name or ".yaml." in name:
        check_sso(path, text)

    is_patchlist = name.startswith("patchlist")
    if is_patchlist:
        check_patchlist(path, text)

    # Regras de configuração (URLs/caminhos/comandos) só em arquivos de dados.
    config_rules = name.endswith((".yml", ".yaml", ".json")) or is_patchlist
    for i, raw in enumerate(text.splitlines(), 1):
        check_text_line(path, i, raw, config_rules)


def main():
    if not os.path.isdir(PATCHER):
        print("Patcher config: OK (pasta client/patcher/ ausente, nada a validar)")
        return 0

    count = 0
    for root, dirs, files in os.walk(PATCHER):
        for d in sorted(dirs):
            if os.path.islink(os.path.join(root, d)):
                fail("%s: link simbólico de diretório não permitido" % rel(os.path.join(root, d)))
        dirs[:] = [d for d in dirs
                   if d != ".git" and not os.path.islink(os.path.join(root, d))]
        for fn in sorted(files):
            count += 1
            check_file(os.path.join(root, fn))

    if errors:
        print("Patcher config: FAIL")
        for e in errors:
            print("  - " + e)
        return 1

    print("Patcher config: OK")
    print("Arquivos verificados em client/patcher/: %d" % count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
