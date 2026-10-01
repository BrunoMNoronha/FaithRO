#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador determinístico dos overrides de progressão do FaithRO (ETAPA 2N-C, issue #8).

- Usa apenas a biblioteca padrão (sem PyYAML, sem instalação de dependências).
- Não inicia o map-server; faz validação estrutural e de valores.
- Retorna código != 0 em qualquer falha.

Verifica:
  * conf/import/battle_conf.txt  -> max_parameter/max_trans_parameter/max_aspd
  * db/import/statpoint.yml       -> 55 níveis (201..255), marcos, monotonicidade
  * db/import/job_stats.yml       -> Base EXP 99..255 (157), marcos, MaxBaseLevel 185,
                                     ordem MaxBaseLevel antes de BaseExp, sem MaxJobLevel,
                                     sem classes de 3ª/4ª geração
  * ausência de db/import/job_exp.yml (arquivo errado)
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OVERLAY = os.path.join(REPO, "deploy", "rathena-overlay")
BATTLE = os.path.join(OVERLAY, "conf", "import", "battle_conf.txt")
STATPOINT = os.path.join(OVERLAY, "db", "import", "statpoint.yml")
JOBSTATS = os.path.join(OVERLAY, "db", "import", "job_stats.yml")

INT64_MAX = 9223372036854775807
SENTINEL = 99999999

# Marcos aprovados (ETAPA 2N-B).
EXP_MARKS = {99: 100000000, 150: 653400000, 185: 2863000000,
             200: 5751000000, 225: 20990000000, 254: 119100000000, 255: SENTINEL}
SP_MARKS = {201: 4588, 225: 5670, 240: 6405, 255: 7185}

# Nomes de classes de 3ª/4ª geração (não podem aparecer nos overrides).
# Apenas nomes completos e inequívocos — sem tokens ambíguos como "_T", que
# apareceria em jobs legítimos (ex.: "Baby_Thief").
FORBIDDEN_JOB_TOKENS = [
    "Rune_Knight", "Royal_Guard", "Warlock", "Sorcerer", "Arch_Bishop",
    "Ranger", "Mechanic", "Genetic", "Guillotine_Cross", "Shadow_Chaser",
    "Sura", "Minstrel", "Wanderer", "Kagerou", "Oboro", "Rebellion",
    "Summoner", "Star_Emperor", "Soul_Reaper", "Dragon_Knight", "Meister",
    "Shadow_Cross", "Arch_Mage", "Cardinal", "Windhawk", "Imperial_Guard",
    "Biolo", "Abyss_Chaser", "Elemental_Master", "Inquisitor", "Troubadour",
    "Trouvere", "Hyper_Novice", "Spirit_Handler", "Night_Watch", "Sky_Emperor",
    "Shinkiro", "Shiranui",
]

errors = []
notes = []


def fail(msg):
    errors.append(msg)


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def strip_comments(text):
    """Remove linhas de comentário (# ... e // ...) e comentários inline,
    para que menções a chaves dentro de comentários não gerem falso positivo."""
    out = []
    for line in text.splitlines():
        s = line
        h = s.find("#")
        if h != -1:
            s = s[:h]
        d = s.find("//")
        if d != -1:
            s = s[:d]
        out.append(s)
    return "\n".join(out)


def check_no_tabs_utf8(path, label):
    raw = open(path, "rb").read()
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        fail("%s: não é UTF-8 válido" % label)
    # YAML não pode ter tab na indentação
    for i, line in enumerate(raw.split(b"\n"), 1):
        stripped = line.lstrip(b" ")
        if stripped[:1] == b"\t" or (line[:1] == b"\t"):
            fail("%s: tab na indentação (linha %d)" % (label, i))


def parse_yaml_pairs(text, key_a, key_b):
    """Extrai pares (key_a, key_b) de um YAML simples '- key_a: N' / '  key_b: M'.
    Não depende da ordem de leitura; devolve lista de (int, int)."""
    pairs = []
    cur = None
    for line in text.splitlines():
        m = re.match(r"\s*-?\s*%s:\s*(-?\d+)\s*$" % re.escape(key_a), line)
        if m:
            cur = int(m.group(1))
            continue
        m = re.match(r"\s*%s:\s*(-?\d+)\s*$" % re.escape(key_b), line)
        if m and cur is not None:
            pairs.append((cur, int(m.group(1)))); cur = None
    return pairs


def check_float_presence(text, label):
    if re.search(r":\s*-?\d+\.\d+", text):
        fail("%s: valor float detectado (esperado inteiro)" % label)


# ------------------------------------------------------------------ battle_conf
def validate_battle():
    if not os.path.isfile(BATTLE):
        fail("battle_conf.txt ausente"); return {}
    check_no_tabs_utf8(BATTLE, "battle_conf.txt")
    text = read(BATTLE)
    vals = {}
    seen = {}
    for raw in text.splitlines():
        line = raw.split("//", 1)[0].strip()
        m = re.match(r"([A-Za-z0-9_]+)\s*:\s*(\d+)\s*$", line)
        if m:
            k, v = m.group(1), int(m.group(2))
            seen[k] = seen.get(k, 0) + 1
            vals[k] = v
    for k in ("max_parameter", "max_trans_parameter", "max_aspd"):
        if seen.get(k, 0) == 0:
            fail("battle_conf.txt: chave ausente: %s" % k)
        elif seen[k] > 1:
            fail("battle_conf.txt: chave duplicada: %s" % k)
    if vals.get("max_parameter") != 185:
        fail("battle_conf.txt: max_parameter != 185 (%s)" % vals.get("max_parameter"))
    if vals.get("max_trans_parameter") != 185:
        fail("battle_conf.txt: max_trans_parameter != 185 (%s)" % vals.get("max_trans_parameter"))
    if vals.get("max_aspd") != 197:
        fail("battle_conf.txt: max_aspd != 197 (%s)" % vals.get("max_aspd"))
    for forbidden in ("max_third_aspd", "max_extended_aspd", "max_summoner_aspd"):
        if forbidden in vals:
            fail("battle_conf.txt: não deve alterar %s" % forbidden)
    return vals


# ------------------------------------------------------------------- statpoint
def validate_statpoint():
    if not os.path.isfile(STATPOINT):
        fail("statpoint.yml ausente"); return 0
    check_no_tabs_utf8(STATPOINT, "statpoint.yml")
    text = read(STATPOINT)
    check_float_presence(text, "statpoint.yml")
    if "Type: STATPOINT_DB" not in text:
        fail("statpoint.yml: Header Type STATPOINT_DB ausente")
    if "Version: 2" not in text:
        fail("statpoint.yml: Version 2 esperada")
    pairs = parse_yaml_pairs(text, "Level", "Points")
    levels = [lv for lv, _ in pairs]
    if len(pairs) != 55:
        fail("statpoint.yml: esperadas 55 entradas, encontradas %d" % len(pairs))
    if sorted(levels) != list(range(201, 256)):
        missing = sorted(set(range(201, 256)) - set(levels))
        dups = sorted(set(x for x in levels if levels.count(x) > 1))
        fail("statpoint.yml: níveis 201..255 inconsistentes (faltando=%s dup=%s)" % (missing, dups))
    d = dict(pairs)
    prev = None
    for lv in range(201, 256):
        if lv in d:
            if d[lv] < 0:
                fail("statpoint.yml: Points negativo em %d" % lv)
            if prev is not None and d[lv] <= prev:
                fail("statpoint.yml: Points não estritamente crescente em %d" % lv)
            prev = d[lv]
    for lv, exp in SP_MARKS.items():
        if d.get(lv) != exp:
            fail("statpoint.yml: marco Points(%d) esperado %d, obtido %s" % (lv, exp, d.get(lv)))
    if any(lv < 201 for lv in levels):
        fail("statpoint.yml: alterou níveis <= 200 (proibido)")
    return len(pairs)


# ------------------------------------------------------------------- job_stats
def validate_jobstats():
    # Arquivo errado não pode existir.
    wrong = os.path.join(OVERLAY, "db", "import", "job_exp.yml")
    if os.path.exists(wrong):
        fail("db/import/job_exp.yml existe (arquivo errado; usar job_stats.yml)")
    if not os.path.isfile(JOBSTATS):
        fail("job_stats.yml ausente"); return 0
    check_no_tabs_utf8(JOBSTATS, "job_stats.yml")
    text = read(JOBSTATS)
    code = strip_comments(text)  # sem comentários, para checagens estruturais
    check_float_presence(code, "job_stats.yml")
    if "Type: JOB_STATS" not in code:
        fail("job_stats.yml: Header Type JOB_STATS ausente")
    if "Version: 4" not in code:
        fail("job_stats.yml: Version 4 esperada")
    if len(re.findall(r"(?m)^Header:\s*$", code)) != 1:
        fail("job_stats.yml: deve haver exatamente 1 Header")
    if len(re.findall(r"(?m)^Body:\s*$", code)) != 1:
        fail("job_stats.yml: deve haver exatamente 1 bloco Body")
    if re.search(r"(?m)^\s*-?\s*MaxJobLevel\s*:", code):
        fail("job_stats.yml: MaxJobLevel não deve ser alterado")
    if re.search(r"(?m)^\s*-?\s*JobExp\s*:", code):
        fail("job_stats.yml: JobExp não deve ser alterado")
    for tok in FORBIDDEN_JOB_TOKENS:
        if re.search(r"(?m)^\s*%s\s*:\s*true\s*$" % re.escape(tok), code):
            fail("job_stats.yml: classe não autorizada detectada: %s" % tok)

    # Ordem MaxBaseLevel antes de BaseExp, e MaxBaseLevel == 185 em cada grupo.
    groups = 0
    for block in re.split(r"(?m)^\s*-\s*Jobs:\s*$", code)[1:]:
        groups += 1
        mbl = re.search(r"MaxBaseLevel:\s*(\d+)", block)
        bex = block.find("BaseExp:")
        if not mbl:
            fail("job_stats.yml: grupo %d sem MaxBaseLevel" % groups); continue
        if int(mbl.group(1)) != 185:
            fail("job_stats.yml: grupo %d MaxBaseLevel != 185" % groups)
        if bex == -1:
            fail("job_stats.yml: grupo %d sem BaseExp" % groups); continue
        if block.find("MaxBaseLevel") > bex:
            fail("job_stats.yml: grupo %d MaxBaseLevel deve vir antes de BaseExp" % groups)
    if groups < 2:
        fail("job_stats.yml: esperados >= 2 grupos de Base EXP, encontrados %d" % groups)

    # Base EXP: cada grupo deve ter 157 níveis (99..255) idênticos e válidos.
    pairs = parse_yaml_pairs(code, "Level", "Exp")
    per_group = 157
    if len(pairs) != per_group * groups:
        fail("job_stats.yml: esperadas %d entradas BaseExp (%d/grupo x %d), obtidas %d"
             % (per_group * groups, per_group, groups, len(pairs)))
    # Fatiar por grupo e validar cada fatia.
    for gi in range(groups):
        chunk = pairs[gi * per_group:(gi + 1) * per_group]
        levels = [lv for lv, _ in chunk]
        if sorted(levels) != list(range(99, 256)):
            missing = sorted(set(range(99, 256)) - set(levels))
            dups = sorted(set(x for x in levels if levels.count(x) > 1))
            fail("job_stats.yml: grupo %d níveis 99..255 inconsistentes (faltando=%s dup=%s)"
                 % (gi + 1, missing, dups)); continue
        d = dict(chunk)
        for lv in range(99, 256):
            if d[lv] <= 0:
                fail("job_stats.yml: grupo %d Exp <= 0 em %d" % (gi + 1, lv))
            if d[lv] >= INT64_MAX:
                fail("job_stats.yml: grupo %d Exp >= INT64_MAX em %d" % (gi + 1, lv))
        # 99..254 estritamente crescente
        for lv in range(100, 255):
            if d[lv] <= d[lv - 1]:
                fail("job_stats.yml: grupo %d Exp não crescente em %d" % (gi + 1, lv))
        if d[255] != SENTINEL:
            fail("job_stats.yml: grupo %d Exp(255) != %d" % (gi + 1, SENTINEL))
        for lv, exp in EXP_MARKS.items():
            if d.get(lv) != exp:
                fail("job_stats.yml: grupo %d marco Exp(%d) esperado %d, obtido %s"
                     % (gi + 1, lv, exp, d.get(lv)))
    return per_group


def main():
    vals = validate_battle()
    sp = validate_statpoint()
    be = validate_jobstats()
    if errors:
        print("Progression overrides: FAIL")
        for e in errors:
            print("  - " + e)
        return 1
    print("Progression overrides: OK")
    print("Base EXP entries: %d" % be)
    print("Stat point entries: %d" % sp)
    print("Base level cap: 185")
    print("Natural stat cap: %d" % vals.get("max_parameter"))
    print("Trans stat cap: %d" % vals.get("max_trans_parameter"))
    print("ASPD cap: %d" % vals.get("max_aspd"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
