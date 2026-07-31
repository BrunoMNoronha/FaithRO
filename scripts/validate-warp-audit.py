#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador dos artefatos da auditoria estatica do WARP (ETAPA 2P-D).

Valida os tres JSONs versionados em client/warp-audit/ contra os schemas
(draft-07, subconjunto) em client/warp-audit/schemas/ e contra regras de
seguranca do projeto.

Garantias (ver docs/30-auditoria-estatica-warp.md, FASE N):
  * Apenas biblioteca padrao do Python (sem dependencias externas).
  * Nao acessa a rede; nao executa subprocessos; nao escreve arquivos.
  * Independente do CWD (resolve caminhos a partir da raiz do repositorio).
  * Valida tipos, campos, const, enum, pattern, required e additionalProperties.
  * Exige SHA de 40 caracteres (commit) e 64 (sha256) quando presentes.
  * Impede flags de build/execucao/modificacao em `true`.
  * Rejeita caminhos absolutos e travessia em campos `path`.
  * Rejeita IPs literais, segredos, tokens e caminhos pessoais.
  * Codigo de saida != 0 em falha; sem traceback para entradas invalidas.
"""
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT_DIR = os.path.join(REPO_ROOT, "client", "warp-audit")
SCHEMA_DIR = os.path.join(AUDIT_DIR, "schemas")

ARTIFACTS = [
    ("upstream-manifest.example.json", "upstream-manifest.schema.json"),
    ("security-findings.example.json", "security-findings.schema.json"),
    ("patch-selection.example.json", "patch-selection.schema.json"),
]

# --- Regras de seguranca (valores, nao prosa) ---
IPV4_RE = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
DRIVE_PATH_RE = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]")
PERSONAL_PATH_RE = re.compile(r"(?i)(/home/|/root/|/Users/|\\Users\\)")
PRIVATE_KEY_RE = re.compile(r"BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY")
AUTH_HEADER_RE = re.compile(r"(?i)Authorization:\s*\S")
# Atribuicao de segredo: (senha|password|token|secret|api_key) seguido de : ou = e valor.
SECRET_ASSIGN_RE = re.compile(
    r"(?i)\b(pass(?:word|wd)?|senha|secret|token|api[_-]?key|bearer)\b\s*[:=]\s*\S")
TRAVERSAL_RE = re.compile(r"(^|[\\/])\.\.([\\/]|$)")


class Fail(Exception):
    pass


def load_json(path):
    if not os.path.isfile(path):
        raise Fail(f"arquivo ausente: {os.path.relpath(path, REPO_ROOT)}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (ValueError, OSError) as exc:
        raise Fail(f"JSON invalido em {os.path.relpath(path, REPO_ROOT)}: {exc}")


# ---------------------------------------------------------------------------
# Subconjunto de JSON Schema (draft-07) suficiente para estes artefatos.
# ---------------------------------------------------------------------------
def type_ok(value, jtype):
    if jtype == "object":
        return isinstance(value, dict)
    if jtype == "array":
        return isinstance(value, list)
    if jtype == "string":
        return isinstance(value, str)
    if jtype == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if jtype == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if jtype == "boolean":
        return isinstance(value, bool)
    return True


def validate_node(value, schema, where, errors):
    if "type" in schema and not type_ok(value, schema["type"]):
        errors.append(f"{where}: tipo esperado {schema['type']}")
        return  # sem tipo correto, nao adianta seguir

    if "const" in schema and value != schema["const"]:
        errors.append(f"{where}: valor deve ser {schema['const']!r}, obtido {value!r}")

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: valor {value!r} fora de enum {schema['enum']}")

    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{where}: nao casa com pattern {schema['pattern']}")
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{where}: string mais curta que {schema['minLength']}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{where}: valor {value} < minimo {schema['minimum']}")

    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{where}: campo obrigatorio ausente: {req}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    errors.append(f"{where}: propriedade nao permitida: {key}")
        for key, sub in props.items():
            if key in value:
                validate_node(value[key], sub, f"{where}.{key}", errors)

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{where}: lista com menos de {schema['minItems']} itens")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(value):
                validate_node(item, item_schema, f"{where}[{i}]", errors)


# ---------------------------------------------------------------------------
# Regras de seguranca aplicadas ao conteudo dos artefatos.
# ---------------------------------------------------------------------------
def iter_strings(node, path="$"):
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from iter_strings(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from iter_strings(v, f"{path}[{i}]")


def security_scan(data, errors):
    for where, text in iter_strings(data):
        # IPs literais (exclui a versao de schema semantico tipo x.y.z: exige 4 octetos)
        for m in IPV4_RE.finditer(text):
            octs = m.group(0).split(".")
            if all(0 <= int(o) <= 255 for o in octs):
                errors.append(f"{where}: possivel IP literal '{m.group(0)}'")
        if DRIVE_PATH_RE.search(text):
            errors.append(f"{where}: caminho com unidade (drive) proibido")
        if PERSONAL_PATH_RE.search(text):
            errors.append(f"{where}: caminho pessoal proibido")
        if PRIVATE_KEY_RE.search(text):
            errors.append(f"{where}: bloco de chave privada proibido")
        if AUTH_HEADER_RE.search(text):
            errors.append(f"{where}: header Authorization proibido")
        if SECRET_ASSIGN_RE.search(text):
            errors.append(f"{where}: atribuicao de segredo proibida")

    # Campos 'path' devem ser relativos, sem travessia.
    for where, text in iter_strings(data):
        if where.endswith(".path"):
            if text.startswith("/") or text.startswith("\\") or DRIVE_PATH_RE.match(text):
                errors.append(f"{where}: caminho absoluto proibido em campo path")
            if TRAVERSAL_RE.search(text):
                errors.append(f"{where}: travessia '..' proibida em campo path")


def forbidden_flags(data, name, errors):
    """Impede flags de build/execucao/modificacao em true."""
    must_be_false = [
        "source_executed", "source_built", "binary_created", "client_modified",
        "execution_allowed", "final_selection_allowed",
    ]
    for key in must_be_false:
        if key in data and data[key] is not False:
            errors.append(f"{name}: flag '{key}' deve ser false")
    if "human_authorization_required" in data and data["human_authorization_required"] is not True:
        errors.append(f"{name}: 'human_authorization_required' deve ser true")


def main():
    all_errors = []
    for artifact, schema_name in ARTIFACTS:
        apath = os.path.join(AUDIT_DIR, artifact)
        spath = os.path.join(SCHEMA_DIR, schema_name)
        try:
            data = load_json(apath)
            schema = load_json(spath)
        except Fail as exc:
            all_errors.append(str(exc))
            continue

        errors = []
        validate_node(data, schema, artifact, errors)
        security_scan(data, errors)
        forbidden_flags(data, artifact, errors)

        if errors:
            all_errors.extend(errors)
            print(f"[FALHA] {artifact}: {len(errors)} problema(s)")
            for e in errors:
                print(f"    - {e}")
        else:
            print(f"[OK]    {artifact}")

    if all_errors:
        print(f"\nValidacao FALHOU com {len(all_errors)} problema(s).")
        return 1
    print("\nValidacao OK: 3 artefatos, schemas e regras de seguranca.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Fail as exc:
        print(f"[ERRO] {exc}")
        sys.exit(2)
    except Exception as exc:  # sem traceback para o usuario
        print(f"[ERRO] falha inesperada: {exc}")
        sys.exit(2)
