#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes do inspetor PE offline (scripts/inspect-warp-pe-identity.py), ETAPAs
2P-E-C3-R1/R2/R3.

Constroi PEs SINTETICOS ESTRUTURALMENTE COERENTES em memoria e em arquivos temporarios
removidos ao final; NUNCA versiona um executavel real e NUNCA executa/carrega o arquivo.
Cada fixture valida contem DOS + PE + COFF + Optional Header + Section Table (N
cabecalhos de 40 bytes) + padding ate SizeOfHeaders + (opcional) Certificate Table
DEPOIS dos cabecalhos.

Focos: leitura de campo no offset correto (soh em coff+16; soh=267 legitimo);
Section Table (NumberOfSections, SizeOfHeaders, alinhamento, flag de imagem executavel);
Certificate Table estrutural sem sobreposicao aos cabecalhos e sem expor bCertificate.

Offline: sem rede, sem subprocess de execucao, sem imports de rede.
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


def load_module():
    path = os.path.join(SCRIPTS_DIR, "inspect-warp-pe-identity.py")
    spec = importlib.util.spec_from_file_location("inspect_warp_pe_identity", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def align8(v):
    return (v + 7) & ~7


DOS = 0x40
PE_SIG = 4
COFF = 20
OPT_OFF = DOS + PE_SIG + COFF  # 0x58 = 88


def build_pe(magic=0x010b, soh=0xE0, num_rva=16, num_rva_off=92, datadir_off=96,
             coff_soh=None, num_sections=1, sections_written=None,
             section_alignment=0x1000, file_alignment=0x200, size_of_headers=0x200,
             header_region_len=None, cert_offset=0, cert_size=0, trailer=b"",
             characteristics=0x0102, opt_actual_len=None):
    """Constroi um PE sintetico ESTRUTURALMENTE COERENTE (imagem executavel)."""
    coff_soh = soh if coff_soh is None else coff_soh
    sections_written = num_sections if sections_written is None else sections_written
    dos = bytearray(DOS)
    dos[0:2] = b"MZ"
    struct.pack_into("<I", dos, 0x3C, DOS)  # e_lfanew = 0x40
    pe = b"PE\x00\x00"
    coff = bytearray(COFF)
    struct.pack_into("<H", coff, 0, 0x014c)         # Machine = x86
    struct.pack_into("<H", coff, 2, num_sections)   # NumberOfSections (declarado)
    struct.pack_into("<I", coff, 4, 0)              # TimeDateStamp
    struct.pack_into("<H", coff, 16, coff_soh)      # SizeOfOptionalHeader (coff+16)
    struct.pack_into("<H", coff, 18, characteristics)
    opt = bytearray(soh)
    struct.pack_into("<H", opt, 0, magic)
    if 36 <= len(opt):
        struct.pack_into("<I", opt, 32, section_alignment)
    if 40 <= len(opt):
        struct.pack_into("<I", opt, 36, file_alignment)
    if 64 <= len(opt):
        struct.pack_into("<I", opt, 60, size_of_headers)
    if 68 <= len(opt):
        struct.pack_into("<I", opt, 64, 0)          # CheckSum
    if 70 <= len(opt):
        struct.pack_into("<H", opt, 68, 2)          # Subsystem = WINDOWS_GUI
    if num_rva_off + 4 <= len(opt):
        struct.pack_into("<I", opt, num_rva_off, num_rva)
    for i in range(num_rva):
        eoff = datadir_off + i * 8
        if eoff + 8 <= len(opt):
            if i == 4:
                struct.pack_into("<I", opt, eoff, cert_offset)
                struct.pack_into("<I", opt, eoff + 4, cert_size)
            else:
                struct.pack_into("<I", opt, eoff, 0)
                struct.pack_into("<I", opt, eoff + 4, 0)
    if opt_actual_len is not None:
        opt = opt[:opt_actual_len]
    sect = b"\x00" * (sections_written * 40)
    header = bytes(dos) + pe + bytes(coff) + bytes(opt) + sect
    region_len = size_of_headers if header_region_len is None else header_region_len
    if len(header) < region_len:
        header += b"\x00" * (region_len - len(header))
    return header + trailer


def pe32(**kw):
    return build_pe(0x010b, 0xE0, 16, 92, 96, **kw)


def pe32plus(**kw):
    return build_pe(0x020b, 0xF0, 16, 108, 112, **kw)


def wincert(dw_length, revision=0x0200, ctype=0x0002, fill=b"\xAA"):
    header = struct.pack("<IHH", dw_length, revision, ctype)
    content_len = max(dw_length - 8, 0)
    content = (fill * (content_len // len(fill) + 1))[:content_len]
    pad = align8(dw_length) - dw_length
    return header + content + b"\x00" * pad


def table(*dw_lengths, **kw):
    return b"".join(wincert(dl, **kw) for dl in dw_lengths)


def cert_pe(trailer, cert_offset=0x200, cert_size=None, **kw):
    """PE32 valido com a Certificate Table posicionada em cert_offset (>= SizeOfHeaders)."""
    cert_size = len(trailer) if cert_size is None else cert_size
    return pe32(cert_offset=cert_offset, cert_size=cert_size, trailer=trailer, **kw)


def main():
    mod = load_module()
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
            print(f"[FALHA] (esperava parse OK) {label}: {exc}")
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
            print(f"[FALHA] (esperava PEError, veio {type(exc).__name__}) {label}")
        else:
            failed += 1
            print(f"[FALHA] (esperava rejeicao) {label}")

    # ===== Identidade / offsets / Section Table =====
    expect_ok("PE32 valido (1 secao)", pe32(), lambda r: [
        ("pe_format PE32", r["pe_format"] == "PE32"),
        ("soh 224", r["size_of_optional_header"] == 224),
        ("secoes 1", r["number_of_sections"] == 1),
        ("section_table declared 1", r["section_table"]["declared_entry_count"] == 1),
        ("section_table within_file", r["section_table"]["within_file"] is True),
        ("contents_inspected false", r["section_table"]["contents_inspected"] is False),
        ("size_of_headers 512", r["size_of_headers"] == 512),
        ("exec flag presente", r["executable_image_flag_present"] is True),
        ("headers parseaveis", r["pe_headers_structurally_parseable"] is True),
        ("SEM pe_valid", "pe_valid" not in r),
        ("full validation false", r["full_pe_validation_performed"] is False),
        ("cert ausente", r["certificate_table"]["present"] is False),
    ])
    expect_ok("PE32+ valido", pe32plus(), lambda r: [
        ("pe_format PE32+", r["pe_format"] == "PE32+"),
        ("soh 240", r["size_of_optional_header"] == 240),
        ("headers parseaveis", r["pe_headers_structurally_parseable"] is True),
    ])
    expect_ok("PE32 valido (5 secoes)", pe32(num_sections=5), lambda r: [
        ("section_table declared 5", r["section_table"]["declared_entry_count"] == 5),
        ("total_size 200", r["section_table"]["total_size"] == 200),
    ])
    # Regressao R1 (offset) e R2 (soh=267 legitimo).
    expect_ok("regressao 0xE0 -> 224", pe32(), lambda r: [
        ("soh 224", r["size_of_optional_header"] == 224),
        ("soh != 267", r["size_of_optional_header"] != 267),
    ])
    expect_ok("soh=267 (== magic) valido", build_pe(0x010b, 267, 16, 92, 96), lambda r: [
        ("soh 267", r["size_of_optional_header"] == 267),
        ("headers parseaveis", r["pe_headers_structurally_parseable"] is True),
    ])

    # ---- Negativos de cabecalho ----
    expect_fail("MZ ausente", b"XX" + pe32()[2:])
    bad_lfa = bytearray(pe32()); struct.pack_into("<I", bad_lfa, 0x3C, 0x7fffffff)
    expect_fail("e_lfanew fora do arquivo", bytes(bad_lfa))
    bad_pe = bytearray(pe32()); bad_pe[0x40:0x44] = b"XXXX"
    expect_fail("assinatura PE ausente", bytes(bad_pe))
    expect_fail("COFF truncado", pe32()[:0x44 + 10])
    expect_fail("Optional Header truncado", pe32()[:OPT_OFF + 10])
    expect_fail("SizeOfOptionalHeader pequeno", build_pe(0x010b, 80, 16, 92, 96, coff_soh=80))
    expect_fail("magic desconhecido", build_pe(0x1234, 0xE0, 16, 92, 96))
    expect_fail("NumberOfRvaAndSizes incompativel", build_pe(0x010b, 0xE0, 100, 92, 96))

    # ---- Section Table (FASE C/D) ----
    expect_fail("NumberOfSections=0", pe32(num_sections=0))
    expect_fail("NumberOfSections=97", pe32(num_sections=97, sections_written=1))
    expect_fail("Section Table truncada (end > file)",
                pe32(num_sections=8, sections_written=2, header_region_len=0))
    expect_fail("apenas 4 de 5 headers presentes",
                pe32(num_sections=5, sections_written=4, header_region_len=472))
    expect_fail("SizeOfHeaders < section_table_end",
                pe32(num_sections=5, size_of_headers=384, file_alignment=128, header_region_len=512))
    expect_fail("SizeOfHeaders > file_size",
                pe32(num_sections=1, size_of_headers=0x10000, header_region_len=512))
    expect_fail("SizeOfHeaders desalinhado",
                pe32(num_sections=1, size_of_headers=513, header_region_len=1024))
    expect_fail("flag executavel ausente", pe32(characteristics=0x0000))

    # ---- Certificate Table (FASE D/E) ----
    expect_ok("cert ausente", pe32(), lambda r: [
        ("present false", r["certificate_table"]["present"] is False),
        ("structurally_parseable", r["certificate_table"]["structurally_parseable"] is True),
    ])
    expect_fail("cert offset0/size!=0 (parcial)",
                pe32(cert_offset=0, cert_size=16, trailer=b"\x00" * 16))
    expect_fail("cert offset!=0/size0 (parcial)",
                pe32(cert_offset=0x200, cert_size=0, trailer=b"\x00" * 16))
    expect_fail("cert desalinhado", cert_pe(b"\x00" * 24, cert_offset=0x201))
    expect_fail("cert size < 8", cert_pe(b"\x00" * 8, cert_size=4))
    expect_fail("dwLength < 8", cert_pe(struct.pack("<IHH", 4, 0x0200, 0x0002), cert_size=8))
    expect_fail("dwLength alem da tabela",
                cert_pe(struct.pack("<IHH", 64, 0x0200, 0x0002) + b"\x00" * 8, cert_size=16))
    expect_fail("entrada truncada", cert_pe(wincert(16) + b"\x00" * 4, cert_size=20))
    expect_fail("padding nao-zero",
                cert_pe(struct.pack("<IHH", 12, 0x0200, 0x0002) + b"\x00" * 4 + b"\xFF" * 4, cert_size=16))
    # D2/D3: Certificate Table sobreposta aos cabecalhos / Section Table.
    expect_fail("cert sobreposta a Section Table (offset 312)",
                pe32(cert_offset=312, cert_size=16, trailer=b"\x00" * 16, header_region_len=512))
    expect_fail("cert sobreposta ao intervalo de headers (offset 100)",
                pe32(cert_offset=100, cert_size=16, trailer=b"\x00" * 16, header_region_len=512))
    # D-14: Certificate Table apos SizeOfHeaders -> aceitar.
    expect_ok("uma entrada PKCS#7 apos headers", cert_pe(table(24)), lambda r: [
        ("present true", r["certificate_table"]["present"] is True),
        ("entry_count 1", r["certificate_table"]["entry_count"] == 1),
        ("type PKCS7", r["certificate_table"]["entries"][0]["certificate_type_name"] == "WIN_CERT_TYPE_PKCS_SIGNED_DATA"),
        ("declared_dw_length 24", r["certificate_table"]["entries"][0]["declared_dw_length"] == 24),
    ])
    expect_ok("duas entradas apos headers", cert_pe(table(16, 24)), lambda r: [
        ("entry_count 2", r["certificate_table"]["entry_count"] == 2),
    ])
    expect_ok("padding align8 (dwLength nao multiplo de 8)", cert_pe(table(20, 12)), lambda r: [
        ("padding_length 4", r["certificate_table"]["entries"][0]["padding_length"] == 4),
        ("padding zero", r["certificate_table"]["entries"][0]["padding_zero_filled"] is True),
    ])
    expect_ok("tipo PKCS1_SIGN 0x0009 reconhecido", cert_pe(table(16, ctype=0x0009)), lambda r: [
        ("type name", r["certificate_table"]["entries"][0]["certificate_type_name"] == "WIN_CERT_TYPE_PKCS1_SIGN"),
    ])
    expect_fail("soma final incompativel", cert_pe(table(16) + b"\x00" * 8, cert_size=24))

    # nenhum conteudo de bCertificate no JSON
    marker = b"CERTBODYMARKER42"
    blob = struct.pack("<IHH", 8 + len(marker), 0x0200, 0x0002) + marker
    blob = blob + b"\x00" * (align8(len(blob)) - len(blob))
    r15 = expect_ok("cert presente com conteudo", cert_pe(blob, cert_size=len(blob)), lambda r: [
        ("present true", r["certificate_table"]["present"] is True),
    ])
    if r15 is not None:
        js = json.dumps(r15, ensure_ascii=False)
        ok("nenhum bCertificate no JSON", "CERTBODYMARKER" not in js)
        keys = set(r15["certificate_table"]["entries"][0].keys())
        ok("apenas metadados estruturais",
           keys == {"declared_dw_length", "aligned_span", "padding_length",
                    "padding_zero_filled", "revision", "certificate_type", "certificate_type_name"})

    # fixtures temporarias removidas; nenhum arquivo executado.
    tmpdir = tempfile.mkdtemp(prefix="pe-fixtures-")
    removed = True
    try:
        good = os.path.join(tmpdir, "good.bin")
        with open(good, "wb") as fh:
            fh.write(cert_pe(table(24)))
        r = mod.inspect(open(good, "rb").read())
        ok("nao executa/carrega o arquivo",
           r["executed"] is False and r["loaded_as_executable"] is False and r["launched"] is False)
        ok("main() exit 0 em PE valido", mod.main(["x", good]) == 0)
        bad = os.path.join(tmpdir, "bad.bin")
        with open(bad, "wb") as fh:
            fh.write(b"not a pe")
        ok("main() exit != 0 em invalido", mod.main(["x", bad]) != 0)
    finally:
        for f in ("good.bin", "bad.bin"):
            p = os.path.join(tmpdir, f)
            if os.path.exists(p):
                os.remove(p)
        try:
            os.rmdir(tmpdir)
        except OSError:
            removed = False
    ok("fixtures temporarias removidas", removed and not os.path.exists(tmpdir))

    print(f"\nResumo: {passed} teste(s) OK, {failed} falha(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"[ERRO] falha inesperada: {exc}")
        sys.exit(2)
