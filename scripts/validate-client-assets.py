#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador determinístico dos arquivos versionados em client/ (ETAPA 2O-A).

Objetivo: impedir o commit acidental de binários ou assets proprietários
(executáveis, GRFs, pacotes de patch, arquivos compactados) dentro de client/,
e garantir que os templates de exemplo permaneçam textuais e bem-formados.

- Usa apenas a biblioteca padrão (sem dependências externas).
- Não acessa nada fora do repositório; não executa binários.
- Independe do diretório de execução (usa __file__ para achar a raiz).
- Retorna código != 0 em qualquer violação.

Regras:
  * Somente uma ALLOWLIST explícita de sufixos textuais é permitida em client/.
  * Extensões proprietárias/binárias são explicitamente rejeitadas.
  * Nenhum arquivo em client/ pode exceder MAX_BYTES.
  * Arquivos .json devem ser JSON sintaticamente válido.
  * Arquivos XML de exemplo (*.xml / *.xml.example) devem ser bem-formados.
"""
import json
import os
import sys
from xml.dom import minidom

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT = os.path.join(REPO, "client")

# Allowlist explícita de sufixos textuais versionáveis em client/.
ALLOWED_SUFFIXES = (
    ".md",
    ".txt",
    ".json",
    ".example",   # cobre data.ini.example, clientinfo.xml.example, etc.
    ".gitkeep",
    ".gitignore",
)

# Extensões proibidas (mensagem mais clara do que apenas "fora da allowlist").
FORBIDDEN_EXTS = (
    ".exe", ".dll", ".grf", ".gpf", ".rgz", ".thor",
    ".7z", ".rar", ".zip", ".msi", ".bin", ".iso",
)

MAX_BYTES = 1024 * 1024  # 1 MiB

errors = []


def fail(msg):
    errors.append(msg)


def rel(path):
    return os.path.relpath(path, REPO).replace("\\", "/")


def check_file(path):
    r = rel(path)
    name = os.path.basename(path)
    ext = os.path.splitext(name)[1].lower()

    # Links simbólicos não são permitidos em client/: um symlink poderia
    # apontar para fora do repositório e ser lido/seguido. Falhar antes de
    # qualquer getsize/open evita esse escape de forma segura.
    if os.path.islink(path):
        fail("%s: link simbólico não permitido em client/" % r)
        return

    if ext in FORBIDDEN_EXTS:
        fail("%s: extensão proibida (%s) — binário/proprietário não pode ser versionado" % (r, ext))
        return
    if not name.endswith(ALLOWED_SUFFIXES):
        fail("%s: fora da allowlist textual de client/ (sufixos permitidos: %s)"
             % (r, ", ".join(ALLOWED_SUFFIXES)))
        return

    size = os.path.getsize(path)
    if size > MAX_BYTES:
        fail("%s: %d bytes excede o limite de %d bytes (1 MiB)" % (r, size, MAX_BYTES))

    # Deve ser UTF-8 válido (arquivos textuais).
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

    if name.endswith(".xml") or name.endswith(".xml.example"):
        try:
            minidom.parseString(data)
        except Exception as e:  # xml.parsers.expat.ExpatError e afins
            fail("%s: XML mal-formado (%s)" % (r, e))


def main():
    if not os.path.isdir(CLIENT):
        print("Client assets: OK (pasta client/ ausente, nada a validar)")
        return 0

    count = 0
    # os.walk não segue symlinks de diretório por padrão (followlinks=False),
    # de modo que um symlink de pasta nunca é percorrido. Ainda assim,
    # sinalizamos qualquer symlink de diretório explicitamente e o removemos
    # da travessia, tratando o risco de forma segura.
    for root, dirs, files in os.walk(CLIENT):
        for d in sorted(dirs):
            if os.path.islink(os.path.join(root, d)):
                fail("%s: link simbólico de diretório não permitido em client/"
                     % rel(os.path.join(root, d)))
        # Não descer em diretórios de VCS nem em symlinks de diretório.
        dirs[:] = [d for d in dirs
                   if d != ".git" and not os.path.islink(os.path.join(root, d))]
        for fn in sorted(files):
            count += 1
            check_file(os.path.join(root, fn))

    if errors:
        print("Client assets: FAIL")
        for e in errors:
            print("  - " + e)
        return 1

    print("Client assets: OK")
    print("Arquivos verificados em client/: %d" % count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
