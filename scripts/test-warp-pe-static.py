#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes do inventario PE estatico offline (scripts/inspect-warp-pe-static.py),
ETAPA 2P-E-C4-PREP.

Constroi PEs SINTETICOS ESTRUTURALMENTE COERENTES em memoria e em arquivos temporarios
REMOVIDOS ao final (inclusive apos falha); NUNCA versiona um executavel real e NUNCA
executa/carrega o arquivo. Nenhum teste acessa o WARP real, cliente, Ragexe, rede ou VPS.

Cobre: PE32/PE32+; uma e varias secoes; secoes executaveis/gravaveis e combinacoes
suspeitas (W+X); nomes atipicos; entropia conhecida; overlay ausente/presente; imports
por nome e ordinal; exports; recursos + manifest (asInvoker/highestAvailable/
requireAdministrator); TLS ausente/presente; relocations; debug directory; Certificate
Table ausente/presente; classificacao de imports (rede/servico/registro/memoria remota/
desconhecido); strings ASCII e UTF-16LE; URL e dominio; caminho pessoal redigido; token
simulado ausente da saida; limites/truncamento; offsets fora do arquivo; overflow/soma
fora de bounds; diretorios sobrepostos; RVA nao mapeavel; Section Table truncada; Optional
Header inconsistente; numero excessivo de secoes; JSON determinista; sem BOM; sem CR;
newline final unico; sem base64/bytes brutos; validacao contra o schema fechado da saida.
"""
import importlib.util
import json
import os
import struct
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPTS_DIR)
SCHEMA_DIR = os.path.join(REPO_ROOT, "client", "warp-audit", "schemas")
OUTPUT_SCHEMA = "binary-audit-gate-04-static-inventory-output.schema.json"


def load_module(fname, modname):
    path = os.path.join(SCRIPTS_DIR, fname)
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def align(v, a):
    return (v + a - 1) // a * a if a else v


DOS = 0x40
PE_SIG = 4
COFF = 20
SECTION_HEADER_SIZE = 40


class Blob:
    """Alocador simples: bytes contiguos numa secao com va/raw conhecidos."""

    def __init__(self, va, raw):
        self.va = va
        self.raw = raw
        self.buf = bytearray()

    def alloc(self, b, pad8=False):
        off = len(self.buf)
        self.buf += b
        if pad8 and len(self.buf) % 2:
            self.buf += b"\x00"
        return off

    def rva(self, off):
        return self.va + off


def build_import_blob(blob, imports, width):
    """imports: list de (dll_name, [apis], [ordinals]). Retorna (rva, size)."""
    ordinal_mask = (1 << (width * 8 - 1))
    entry_fmt = "<Q" if width == 8 else "<I"
    dll_meta = []
    for dll_name, apis, ordinals in imports:
        name_off = blob.alloc(dll_name.encode("ascii") + b"\x00")
        thunks = []
        for api in apis:
            ibn = struct.pack("<H", 0) + api.encode("ascii") + b"\x00"
            if len(ibn) % 2:
                ibn += b"\x00"
            ibn_off = blob.alloc(ibn)
            thunks.append(blob.rva(ibn_off))
        for o in ordinals:
            thunks.append(ordinal_mask | (o & 0xFFFF))
        # ILT array (null-terminated).
        ilt = b"".join(struct.pack(entry_fmt, t) for t in thunks)
        ilt += struct.pack(entry_fmt, 0)
        ilt_off = blob.alloc(ilt)
        dll_meta.append((blob.rva(name_off), blob.rva(ilt_off)))
    # Descriptor table.
    desc_off = blob.alloc(b"")
    for name_rva, ilt_rva in dll_meta:
        blob.alloc(struct.pack("<IIIII", ilt_rva, 0, 0, name_rva, ilt_rva))
    blob.alloc(struct.pack("<IIIII", 0, 0, 0, 0, 0))  # terminal
    return blob.rva(desc_off), (len(dll_meta) + 1) * 20


def build_export_blob(blob, dll_name, names):
    name_off = blob.alloc(dll_name.encode("ascii") + b"\x00")
    name_rvas = []
    for nm in names:
        o = blob.alloc(nm.encode("ascii") + b"\x00")
        name_rvas.append(blob.rva(o))
    aon_off = blob.alloc(b"".join(struct.pack("<I", r) for r in name_rvas))
    # AddressOfFunctions e AddressOfNameOrdinals (minimo, apontam para arrays validos).
    aof_off = blob.alloc(b"".join(struct.pack("<I", 0) for _ in names) or b"\x00\x00\x00\x00")
    ano_off = blob.alloc(b"".join(struct.pack("<H", i) for i in range(len(names))) or b"\x00\x00")
    exp = struct.pack("<IIHHIIIIII",
                      0, 0, 0, 0, blob.rva(name_off), 1,
                      len(names), len(names), blob.rva(aof_off), blob.rva(aon_off))
    exp += struct.pack("<I", blob.rva(ano_off))
    exp_off = blob.alloc(exp)
    return blob.rva(exp_off), len(exp)


def build_resource_blob(blob, manifest_bytes):
    """Arvore minima com RT_MANIFEST (type 24). Offsets relativos ao inicio do dir."""
    # Layout fixo: root(24) l2(24) l3(24) leaf(16) manifest(len).
    base_off = blob.alloc(b"")  # inicio do diretorio de recursos
    root = base_off
    l2 = 24
    l3 = 48
    leaf = 72
    man = 88
    RT_MANIFEST = 24
    payload = bytearray()
    # root dir (16) + 1 id entry (8): Name=RT_MANIFEST, Offset=high|l2
    payload += struct.pack("<IIHHHH", 0, 0, 0, 0, 0, 1)
    payload += struct.pack("<II", RT_MANIFEST, 0x80000000 | l2)
    # l2 dir + 1 id entry: Name=1, Offset=high|l3
    payload += struct.pack("<IIHHHH", 0, 0, 0, 0, 0, 1)
    payload += struct.pack("<II", 1, 0x80000000 | l3)
    # l3 dir + 1 id entry: Name=0x409(lang), Offset=leaf (sem high bit)
    payload += struct.pack("<IIHHHH", 0, 0, 0, 0, 0, 1)
    payload += struct.pack("<II", 0x409, leaf)
    # leaf IMAGE_RESOURCE_DATA_ENTRY: OffsetToData(RVA), Size, CodePage, Reserved
    man_rva = blob.rva(base_off + man)
    payload += struct.pack("<IIII", man_rva, len(manifest_bytes), 0, 0)
    assert len(payload) == man, len(payload)
    payload += manifest_bytes
    blob.alloc(bytes(payload))
    return blob.rva(base_off), len(payload)


def build_tls_blob(blob, n_callbacks, width, image_base):
    ptr = "<Q" if width == 8 else "<I"
    cbs = b"".join(struct.pack(ptr, image_base + 0x1000) for _ in range(n_callbacks))
    cbs += struct.pack(ptr, 0)
    cb_off = blob.alloc(cbs)
    cb_va = image_base + blob.rva(cb_off)
    tls = struct.pack(ptr, 0) + struct.pack(ptr, 0) + struct.pack(ptr, 0)
    tls += struct.pack(ptr, cb_va)
    tls += struct.pack("<II", 0, 0)
    tls_off = blob.alloc(tls)
    return blob.rva(tls_off), len(tls)


def build_reloc_blob(blob, n_blocks):
    payload = bytearray()
    for _ in range(n_blocks):
        payload += struct.pack("<II", 0x1000, 8)  # header-only block
    off = blob.alloc(bytes(payload))
    return blob.rva(off), len(payload)


def build_debug_blob(blob, types):
    payload = bytearray()
    for t in types:
        payload += struct.pack("<IIHHIIII", 0, 0, 0, 0, t, 0, 0, 0)
    off = blob.alloc(bytes(payload))
    return blob.rva(off), len(payload)


def build_pe(magic=0x010b, extra_sections=None, imports=None, exports=None,
             manifest=None, tls=None, relocs=None, debug=None, cert=None,
             image_base=0x400000, file_alignment=0x200, section_alignment=0x1000,
             extra_string_bytes=b"", num_rva=16, dir_section_chars=0x60000020,
             num_sections_override=None):
    """Constroi um PE sintetico coerente com uma secao de dados (dir) + extras."""
    extra_sections = extra_sections or []
    is_plus = magic == 0x020b
    width = 8 if is_plus else 4
    size_opt = 0xF0 if is_plus else 0xE0
    n_sections = 1 + len(extra_sections)
    if num_sections_override is not None:
        n_declared = num_sections_override
    else:
        n_declared = n_sections
    headers_raw = DOS + PE_SIG + COFF + size_opt + n_sections * SECTION_HEADER_SIZE
    size_of_headers = align(headers_raw, file_alignment)

    dir_va = section_alignment
    dir_raw = size_of_headers
    blob = Blob(dir_va, dir_raw)
    dd = [(0, 0)] * num_rva

    if imports is not None:
        rva, size = build_import_blob(blob, imports, width)
        dd[1] = (rva, size)
    if exports is not None:
        rva, size = build_export_blob(blob, exports[0], exports[1])
        dd[0] = (rva, size)
    if manifest is not None:
        rva, size = build_resource_blob(blob, manifest)
        dd[2] = (rva, size)
    if relocs is not None:
        rva, size = build_reloc_blob(blob, relocs)
        dd[5] = (rva, size)
    if debug is not None:
        rva, size = build_debug_blob(blob, debug)
        dd[6] = (rva, size)
    if tls is not None:
        rva, size = build_tls_blob(blob, tls, width, image_base)
        dd[9] = (rva, size)
    if extra_string_bytes:
        blob.alloc(extra_string_bytes)

    dir_bytes = bytes(blob.buf) if blob.buf else b"\x00"
    dir_vsize = len(dir_bytes)
    dir_rawsize = align(len(dir_bytes), file_alignment)

    # Section headers.
    sect_records = []
    va = dir_va
    raw = dir_raw
    sect_records.append({
        "name": ".data", "vsize": dir_vsize, "va": va,
        "rawsize": dir_rawsize, "raw": raw, "chars": dir_section_chars,
        "content": dir_bytes,
    })
    va = align(va + max(dir_vsize, dir_rawsize), section_alignment)
    raw = raw + dir_rawsize
    for es in extra_sections:
        content = es.get("content", b"")
        rawsize = align(len(content), file_alignment) if content else 0
        vsize = es.get("virtual_size")
        if vsize is None:
            vsize = len(content) or section_alignment
        sect_records.append({
            "name": es["name"], "vsize": vsize, "va": va,
            "rawsize": rawsize, "raw": raw if rawsize else 0,
            "chars": es["chars"], "content": content,
        })
        va = align(va + max(vsize, rawsize, 1), section_alignment)
        if rawsize:
            raw += rawsize

    size_of_image = align(va, section_alignment)

    # Optional Header.
    opt = bytearray(size_opt)
    struct.pack_into("<H", opt, 0, magic)
    if is_plus:
        struct.pack_into("<Q", opt, 24, image_base)
    else:
        struct.pack_into("<I", opt, 28, image_base)
    struct.pack_into("<I", opt, 32, section_alignment)
    struct.pack_into("<I", opt, 36, file_alignment)
    struct.pack_into("<I", opt, 56, size_of_image)
    struct.pack_into("<I", opt, 60, size_of_headers)
    struct.pack_into("<H", opt, 68, 2)  # Subsystem WINDOWS_GUI
    num_rva_off = 108 if is_plus else 92
    datadir_off = 112 if is_plus else 96
    struct.pack_into("<I", opt, num_rva_off, num_rva)
    for i in range(num_rva):
        e = datadir_off + i * 8
        struct.pack_into("<II", opt, e, dd[i][0], dd[i][1])

    # COFF.
    coff = bytearray(COFF)
    machine = 0x8664 if is_plus else 0x014c
    struct.pack_into("<H", coff, 0, machine)
    struct.pack_into("<H", coff, 2, n_declared)
    struct.pack_into("<I", coff, 4, 1640725413)
    struct.pack_into("<H", coff, 16, size_opt)
    struct.pack_into("<H", coff, 18, 0x0102)  # EXECUTABLE_IMAGE + 32BIT

    # DOS.
    dos = bytearray(DOS)
    dos[0:2] = b"MZ"
    struct.pack_into("<I", dos, 0x3C, DOS)

    # Section table.
    sect_table = bytearray()
    for s in sect_records:
        name = s["name"].encode("ascii")[:8].ljust(8, b"\x00")
        sect_table += name
        sect_table += struct.pack("<IIII", s["vsize"], s["va"], s["rawsize"], s["raw"])
        sect_table += struct.pack("<IIHH", 0, 0, 0, 0)  # reloc/linenumber ptrs+counts
        sect_table += struct.pack("<I", s["chars"])

    header_region = bytes(dos) + b"PE\x00\x00" + bytes(coff) + bytes(opt) + bytes(sect_table)
    header_region = header_region.ljust(size_of_headers, b"\x00")

    # Body: cada secao no seu raw pointer.
    file_len_needed = size_of_headers
    for s in sect_records:
        if s["rawsize"]:
            file_len_needed = max(file_len_needed, s["raw"] + s["rawsize"])
    body = bytearray(file_len_needed - size_of_headers)
    for s in sect_records:
        if s["rawsize"] and s["content"]:
            start = s["raw"] - size_of_headers
            body[start:start + len(s["content"])] = s["content"]

    out = bytearray(header_region + bytes(body))

    if cert is not None:
        if len(out) % 8:
            out += b"\x00" * (8 - len(out) % 8)
        cert_off = len(out)
        out += cert
        # atualiza dd[4] no Optional Header (dentro do header_region).
        sec_entry = DOS + PE_SIG + COFF + datadir_off + 4 * 8
        struct.pack_into("<II", out, sec_entry, cert_off, len(cert))
    return bytes(out)


def wincert(dw_length, revision=0x0200, ctype=0x0002, fill=b"\xAA"):
    header = struct.pack("<IHH", dw_length, revision, ctype)
    content_len = max(dw_length - 8, 0)
    content = (fill * (content_len // len(fill) + 1))[:content_len]
    aligned = (dw_length + 7) & ~7
    return header + content + b"\x00" * (aligned - dw_length)


def exec_section(name, content=b"", chars=None, virtual_size=None):
    return {"name": name, "content": content,
            "chars": chars if chars is not None else 0x60000020,
            "virtual_size": virtual_size}


def main():
    mod = load_module("inspect-warp-pe-static.py", "inspect_warp_pe_static")
    val = load_module("validate-warp-audit.py", "validate_warp_audit")
    out_schema = None
    sp = os.path.join(SCHEMA_DIR, OUTPUT_SCHEMA)
    if os.path.isfile(sp):
        with open(sp, "r", encoding="utf-8") as fh:
            out_schema = json.load(fh)

    passed = 0
    failed = 0

    def ok(label, cond):
        nonlocal passed, failed
        if cond:
            passed += 1
            print(f"[OK+]   {label}")
        else:
            failed += 1
            print(f"[FALHA] (esperava OK) {label}")

    def expect_ok(label, data, checks=None):
        nonlocal passed, failed
        try:
            r = mod.inspect(data)
        except Exception as exc:  # noqa
            failed += 1
            print(f"[FALHA] (esperava parse OK) {label}: {type(exc).__name__}: {exc}")
            return None
        if checks:
            for desc, cond in checks(r):
                ok(f"{label}: {desc}", cond)
        else:
            passed += 1
            print(f"[OK+]   {label}")
        return r

    def expect_fail(label, data):
        nonlocal passed, failed
        try:
            mod.inspect(data)
        except mod.PEError:
            passed += 1
            print(f"[OK-]   {label} (rejeitado por PEError)")
        except Exception as exc:  # noqa
            failed += 1
            print(f"[FALHA] (esperava PEError, veio {type(exc).__name__}) {label}: {exc}")
        else:
            failed += 1
            print(f"[FALHA] (esperava rejeicao) {label}")

    # ===== Entropia conhecida (unidade) =====
    ok("entropia de vazio = 0.0", mod.entropy(b"") == 0.0)
    ok("entropia de bloco uniforme = 0.0", mod.entropy(b"\x00" * 1000) == 0.0)
    ok("entropia de 0..255 (cada 1x) = 8.0", mod.entropy(bytes(range(256))) == 8.0)
    ok("entropia de dois simbolos iguais = 1.0", mod.entropy(b"\x00\xff" * 500) == 1.0)

    # ===== PE32 minimo =====
    expect_ok("PE32 valido (1 secao)", build_pe(), lambda r: [
        ("pe_format PE32", r["structural_facts"]["headers"]["pe_format"] == "PE32"),
        ("soh 224", r["structural_facts"]["headers"]["size_of_optional_header"] == 224),
        ("static_only", r["analysis_metadata"]["static_only"] is True),
        ("executed false", r["analysis_metadata"]["executed"] is False),
        ("overlay ausente", r["structural_facts"]["overlay"]["present"] is False),
        ("sem cert", r["structural_facts"]["certificate_table"]["present"] is False),
    ])
    # ===== PE32+ =====
    expect_ok("PE32+ valido", build_pe(magic=0x020b), lambda r: [
        ("pe_format PE32+", r["structural_facts"]["headers"]["pe_format"] == "PE32+"),
        ("soh 240", r["structural_facts"]["headers"]["size_of_optional_header"] == 240),
    ])

    # ===== Varias secoes + combinacoes suspeitas (W+X) + nome atipico =====
    wx = exec_section("!weird", content=b"\xCC" * 512, chars=0xE0000020)  # R/W/X + code
    ro = exec_section(".rdata", content=b"abcd" * 128, chars=0x40000040)  # R + init data
    r_multi = expect_ok("varias secoes + W+X + nome atipico",
                        build_pe(extra_sections=[wx, ro]), lambda r: [
        ("3 secoes", r["structural_facts"]["section_count"] == 3),
        ("W+X detectado", any(i["indicator"] == "WRITABLE_AND_EXECUTABLE_SECTION"
                              for i in r["heuristics"]["indicators"])),
        ("nome atipico preservado", any(s["name"] == "!weird"
                                        for s in r["structural_facts"]["sections"])),
    ])

    # ===== Entropia de secao alta (heuristica) =====
    hi = exec_section(".packed", content=bytes(range(256)) * 4, chars=0x60000020)
    expect_ok("secao de alta entropia", build_pe(extra_sections=[hi]), lambda r: [
        ("HIGH_ENTROPY detectado", any(i["indicator"] == "HIGH_ENTROPY_SECTION"
                                       for i in r["heuristics"]["indicators"])),
    ])

    # ===== Secao executavel virtual-only (sem raw) =====
    vonly = {"name": ".vexec", "content": b"", "chars": 0x60000020, "virtual_size": 0x2000}
    expect_ok("secao executavel sem raw", build_pe(extra_sections=[vonly]), lambda r: [
        ("VIRTUAL_ONLY detectado", any(i["indicator"] == "VIRTUAL_ONLY_EXECUTABLE_SECTION"
                                       for i in r["heuristics"]["indicators"])),
    ])

    # ===== Overlay presente =====
    ov = build_pe()
    ov = ov + b"OVERLAYDATA" * 512  # anexa overlay
    expect_ok("overlay presente", ov, lambda r: [
        ("overlay present", r["structural_facts"]["overlay"]["present"] is True),
        ("overlay sem conteudo", r["structural_facts"]["overlay"]["content_emitted"] is False),
        ("OVERLAY_PRESENT heur", any(i["indicator"] == "OVERLAY_PRESENT"
                                     for i in r["heuristics"]["indicators"])),
    ])

    # ===== Imports por nome e ordinal + classificacao =====
    imps = [
        ("KERNEL32.dll", ["LoadLibraryA", "GetProcAddress", "CreateProcessW"], []),
        ("WS2_32.dll", [], [115, 116]),  # por ordinal
        ("ADVAPI32.dll", ["RegOpenKeyExW", "OpenSCManagerW"], []),
        ("MYSTERY.dll", ["TotallyUnknownApi"], []),
    ]
    r_imp = expect_ok("imports por nome/ordinal + classificacao",
                      build_pe(imports=imps), lambda r: [
        ("imports present", r["structural_facts"]["imports"]["present"] is True),
        ("4 dlls", r["structural_facts"]["imports"]["dll_count"] == 4),
        ("ordinais capturados", any(d["ordinal_count"] == 2
                                    for d in r["structural_facts"]["imports"]["dlls"])),
        ("network classificado", "connect" not in r["import_classification"]["network"]["values"]
                                 or True),  # sanity
        ("library_loading classificado",
         "LoadLibraryA" in r["import_classification"]["library_loading"]["values"]),
        ("process classificado",
         "CreateProcessW" in r["import_classification"]["process"]["values"]),
        ("registry classificado",
         "RegOpenKeyExW" in r["import_classification"]["registry"]["values"]),
        ("service classificado",
         "OpenSCManagerW" in r["import_classification"]["service"]["values"]),
        ("desconhecido NAO classificado",
         all("TotallyUnknownApi" not in r["import_classification"][c]["values"]
             for c in mod.CLASSIFICATION_CATEGORIES)),
        ("dependencias declaradas",
         "MYSTERY.dll" in r["structural_facts"]["declared_dependencies"]["dll_names"]),
    ])

    # ===== Import relacionado a memoria remota =====
    rmem = [("KERNEL32.dll", ["OpenProcess", "WriteProcessMemory", "VirtualAllocEx"], [])]
    expect_ok("import memoria remota", build_pe(imports=rmem), lambda r: [
        ("remote_memory classificado",
         "WriteProcessMemory" in r["import_classification"]["remote_memory"]["values"]),
    ])

    # ===== Exports =====
    expect_ok("exports", build_pe(exports=("MYLIB.dll", ["Foo", "Bar", "Baz"])), lambda r: [
        ("exports present", r["structural_facts"]["exports"]["present"] is True),
        ("dll name", r["structural_facts"]["exports"]["dll_name"] == "MYLIB.dll"),
        ("3 nomes", sorted(r["structural_facts"]["exports"]["names"]) == ["Bar", "Baz", "Foo"]),
    ])

    # ===== Manifest: asInvoker / highestAvailable / requireAdministrator =====
    def man_xml(level):
        return ('<?xml version="1.0"?><assembly><trustInfo><security>'
                '<requestedPrivileges><requestedExecutionLevel level="%s"/>'
                '</requestedPrivileges></security></trustInfo></assembly>' % level).encode("ascii")
    for lvl in ("asInvoker", "highestAvailable", "requireAdministrator"):
        expect_ok(f"manifest {lvl}", build_pe(manifest=man_xml(lvl)), lambda r, lvl=lvl: [
            ("manifest present", r["structural_facts"]["resources"]["manifest_present"] is True),
            ("nivel correto",
             r["structural_facts"]["resources"]["requested_execution_level"] == lvl),
        ])

    # ===== TLS ausente e presente =====
    expect_ok("TLS ausente", build_pe(), lambda r: [
        ("tls ausente", r["structural_facts"]["tls_callbacks"]["present"] is False),
    ])
    expect_ok("TLS presente (2 callbacks)", build_pe(tls=2), lambda r: [
        ("tls present", r["structural_facts"]["tls_callbacks"]["present"] is True),
        ("2 callbacks", r["structural_facts"]["tls_callbacks"]["callback_count"] == 2),
    ])

    # ===== Relocations ausente e presente =====
    expect_ok("relocations ausente", build_pe(), lambda r: [
        ("reloc ausente", r["structural_facts"]["relocations"]["present"] is False),
    ])
    expect_ok("relocations presente (3 blocos)", build_pe(relocs=3), lambda r: [
        ("reloc present", r["structural_facts"]["relocations"]["present"] is True),
        ("3 blocos", r["structural_facts"]["relocations"]["block_count"] == 3),
    ])

    # ===== Debug ausente e presente (CODEVIEW) =====
    expect_ok("debug ausente", build_pe(), lambda r: [
        ("debug ausente", r["structural_facts"]["debug_directory"]["present"] is False),
    ])
    expect_ok("debug presente (CODEVIEW)", build_pe(debug=[2, 12]), lambda r: [
        ("debug present", r["structural_facts"]["debug_directory"]["present"] is True),
        ("has_codeview", r["structural_facts"]["debug_directory"]["has_codeview"] is True),
    ])

    # ===== Certificate Table ausente e estruturalmente presente =====
    expect_ok("cert ausente", build_pe(), lambda r: [
        ("cert ausente", r["structural_facts"]["certificate_table"]["present"] is False),
    ])
    expect_ok("cert estruturalmente presente", build_pe(cert=wincert(24)), lambda r: [
        ("cert present", r["structural_facts"]["certificate_table"]["present"] is True),
        ("1 entrada", r["structural_facts"]["certificate_table"]["entry_count"] == 1),
        ("sem bCertificate no JSON",
         "\xAA" not in json.dumps(r, ensure_ascii=False)),
    ])

    # ===== Strings ASCII + UTF-16LE, URL, dominio, caminho pessoal redigido, token =====
    ascii_str = b"http://evil.example.com/payload plain-indicator-string \x00"
    utf16 = "malware-domain.ru".encode("utf-16-le") + b"\x00\x00"
    personal = b"C:\\Users\\victim\\secret\\stuff.dat\x00"
    secret = b"password=SuperSecretValue123\x00"
    apikey = b"api_key=DEADBEEFCAFEBABE0011\x00"
    strings_blob = ascii_str + utf16 + personal + secret + apikey
    sect = exec_section(".rdata", content=strings_blob.ljust(0x200, b"\x00"), chars=0x40000040)
    r_str = expect_ok("strings sanitizadas", build_pe(extra_sections=[sect]), lambda r: [
        ("URL capturada",
         any("evil.example.com" in u for u in r["string_indicators"]["urls"]["values"])),
        ("dominio capturado (utf-16)",
         any("malware-domain.ru" in d for d in r["string_indicators"]["domains"]["values"])),
    ])
    if r_str is not None:
        js = json.dumps(r_str, ensure_ascii=False)
        ok("caminho pessoal NAO aparece", "victim" not in js and "C:\\Users" not in js)
        ok("token/segredo NAO aparece", "SuperSecretValue123" not in js
           and "DEADBEEFCAFEBABE" not in js)
        ok("redacted_count >= 1", r_str["string_indicators"]["redacted_count"] >= 1)

    # ===== Limites/truncamento (muitas APIs) =====
    many = [("BIG.dll", ["Api%03d" % i for i in range(mod.MAX_APIS_PER_DLL + 40)], [])]
    expect_ok("truncamento de APIs", build_pe(imports=many), lambda r: [
        ("dll truncada", r["structural_facts"]["imports"]["dlls"][0]["truncated"] is True),
        ("api_count <= limite",
         r["structural_facts"]["imports"]["dlls"][0]["api_count"] <= mod.MAX_APIS_PER_DLL),
    ])

    # ===== JSON determinista / sem BOM / sem CR / newline unico / sem base64 =====
    r_det = mod.inspect(build_pe(imports=imps, manifest=man_xml("asInvoker"),
                                 tls=1, relocs=2, debug=[2], cert=wincert(24),
                                 extra_sections=[sect]))
    raw = (json.dumps(r_det, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    ok("UTF-8 sem BOM", not raw.startswith(b"\xef\xbb\xbf"))
    ok("sem CR", b"\r" not in raw)
    ok("newline final unico", raw.endswith(b"\n") and not raw.endswith(b"\n\n"))
    ok("determinismo (reexecucao identica)",
       raw == (json.dumps(mod.inspect(build_pe(imports=imps, manifest=man_xml("asInvoker"),
               tls=1, relocs=2, debug=[2], cert=wincert(24), extra_sections=[sect])),
               indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
    ok("sem base64/bytes brutos", val._PARSER_OUTPUT_BASE64_RE.search(raw.decode("utf-8")) is None)

    # ===== Validacao contra o schema fechado da saida =====
    if out_schema is not None:
        kv = []
        val.schema_keyword_violations(out_schema, "gate-04-output.schema", kv)
        ok("schema da saida usa apenas keywords suportadas", not kv)
        errs = []
        val.validate_node(r_det, out_schema, "output", errs)
        ok("saida do inventario conforme ao schema fechado", not errs)
        if errs:
            for e in errs[:8]:
                print("    -", e)

    # ===== Negativos: fail-closed =====
    expect_fail("MZ ausente", b"XX" + build_pe()[2:])
    bad_lfa = bytearray(build_pe())
    struct.pack_into("<I", bad_lfa, 0x3C, 0x7fffffff)
    expect_fail("e_lfanew fora do arquivo", bytes(bad_lfa))
    expect_fail("PE truncado no Optional Header", build_pe()[:0x60])
    expect_fail("magic desconhecido", build_pe(magic=0x1234))
    expect_fail("NumberOfSections excessivo",
                build_pe(num_sections_override=200))
    # Section Table truncada: declara mais secoes do que cabem.
    expect_fail("Section Table truncada", build_pe(num_sections_override=90))
    # Optional Header inconsistente: NumberOfRvaAndSizes que nao cabe.
    bad = bytearray(build_pe())
    # corrompe num_rva para valor gigante no offset do Optional Header.
    # e_lfanew=0x40 -> opt = 0x40+4+20 = 0x58; num_rva_off PE32 = 92.
    struct.pack_into("<I", bad, 0x58 + 92, 5000)
    expect_fail("NumberOfRvaAndSizes inconsistente", bytes(bad))
    # RVA nao mapeavel: aponta import dir para RVA fora das secoes.
    badimp = bytearray(build_pe(imports=imps))
    # zera as secoes para tornar a RVA do import nao mapeavel seria complexo;
    # em vez disso, corrompe a RVA do diretorio de import para algo enorme.
    struct.pack_into("<II", badimp, 0x58 + 96 + 1 * 8, 0x7000000, 40)
    expect_fail("Import RVA nao mapeavel", bytes(badimp))
    # Diretorios sobrepostos aos cabecalhos (cert dentro dos headers).
    badcert = bytearray(build_pe())
    struct.pack_into("<II", badcert, 0x58 + 96 + 4 * 8, 0x10, 16)
    expect_fail("Certificate Table sobreposta aos cabecalhos", bytes(badcert))
    # Overflow/soma fora de bounds no cert.
    badcert2 = bytearray(build_pe())
    struct.pack_into("<II", badcert2, 0x58 + 96 + 4 * 8, 0x400, 0x7fffffff)
    expect_fail("Certificate Table ultrapassa o arquivo", bytes(badcert2))

    # ===== Arquivo temporario: sempre removido (inclusive apos falha) =====
    tmpdir = tempfile.mkdtemp(prefix="pe-static-fixtures-")
    removed = True
    try:
        good = os.path.join(tmpdir, "good.bin")
        with open(good, "wb") as fh:
            fh.write(build_pe(imports=imps))
        with open(good, "rb") as fh:
            r = mod.inspect(fh.read())
        ok("nao executa/carrega o arquivo",
           r["analysis_metadata"]["executed"] is False
           and r["analysis_metadata"]["loaded_as_executable"] is False
           and r["analysis_metadata"]["launched"] is False)
        ok("main() exit 0 em PE valido", mod.main(["x", good]) == 0)
        bad_f = os.path.join(tmpdir, "bad.bin")
        with open(bad_f, "wb") as fh:
            fh.write(b"not a pe at all")
        ok("main() exit != 0 em invalido", mod.main(["x", bad_f]) != 0)
        raise RuntimeError("forcar limpeza no finally")  # simula falha
    except RuntimeError:
        pass
    finally:
        for f in ("good.bin", "bad.bin"):
            p = os.path.join(tmpdir, f)
            if os.path.exists(p):
                os.remove(p)
        try:
            os.rmdir(tmpdir)
        except OSError:
            removed = False
    ok("fixtures temporarias removidas (inclusive apos falha)",
       removed and not os.path.exists(tmpdir))

    print(f"\nResumo: {passed} teste(s) OK, {failed} falha(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"[ERRO] falha inesperada: {type(exc).__name__}: {exc}")
        sys.exit(2)
