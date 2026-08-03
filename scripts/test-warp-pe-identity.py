#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes do inspetor PE offline (scripts/inspect-warp-pe-identity.py), ETAPAs
2P-E-C3-R1/R2.

Constroi PEs SINTETICOS em memoria (bytes) e em arquivos temporarios removidos ao
final; NUNCA versiona um executavel real e NUNCA executa/carrega o arquivo. Valida a
LOGICA REAL do parser, com foco:
  * na leitura do campo no offset correto (SizeOfOptionalHeader em coff+16, Magic no
    inicio do Optional Header) — inclusive a coincidencia numerica legitima soh=267
    (NAO deve ser rejeitada apenas por igualdade ao magic PE32 0x010b);
  * no parsing ESTRUTURAL da Certificate Table (WIN_CERTIFICATE), sem interpretar o
    PKCS#7 (bCertificate nunca aparece no JSON).

Offline: nao acessa a rede, nao usa subprocess para iniciar o arquivo, nao importa
modulos de rede.
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


def build_pe(magic=0x010b, soh=0xE0, num_rva=16, num_rva_off=92, datadir_off=96,
             coff_soh=None, cert_offset=0, cert_size=0, trailer=b"",
             opt_actual_len=None):
    """Constroi um PE sintetico minimo (apenas cabecalhos). `trailer` e anexado apos
    o Optional Header (usado como area da Certificate Table). dd[4] recebe
    (cert_offset, cert_size) exatamente como dados."""
    coff_soh = soh if coff_soh is None else coff_soh
    dos = bytearray(0x40)
    dos[0:2] = b"MZ"
    struct.pack_into("<I", dos, 0x3C, 0x40)  # e_lfanew
    pe = b"PE\x00\x00"
    coff = bytearray(20)
    struct.pack_into("<H", coff, 0, 0x014c)     # Machine = x86
    struct.pack_into("<H", coff, 2, 1)          # NumberOfSections
    struct.pack_into("<I", coff, 4, 0)          # TimeDateStamp
    struct.pack_into("<H", coff, 16, coff_soh)  # SizeOfOptionalHeader (coff+16)
    struct.pack_into("<H", coff, 18, 0x0102)    # Characteristics
    opt = bytearray(soh)
    struct.pack_into("<H", opt, 0, magic)
    if len(opt) >= 68:
        struct.pack_into("<I", opt, 64, 0)      # CheckSum
    if len(opt) >= 70:
        struct.pack_into("<H", opt, 68, 2)      # Subsystem = WINDOWS_GUI
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
    return bytes(dos) + pe + bytes(coff) + bytes(opt) + trailer


def pe32(**kw):
    return build_pe(0x010b, 0xE0, 16, 92, 96, **kw)


def pe32plus(**kw):
    return build_pe(0x020b, 0xF0, 16, 108, 112, **kw)


HEADER_LEN_PE32 = 0x40 + 4 + 20 + 0xE0  # 312, alinhado a 8


def wincert(dw_length, revision=0x0200, ctype=0x0002, fill=b"\xAA"):
    """Uma entrada WIN_CERTIFICATE de tamanho align8(dw_length)."""
    header = struct.pack("<IHH", dw_length, revision, ctype)
    content_len = max(dw_length - 8, 0)
    content = (fill * (content_len // len(fill) + 1))[:content_len]
    pad = align8(dw_length) - dw_length
    return header + content + b"\x00" * pad


def table(*dw_lengths, **kw):
    return b"".join(wincert(dl, **kw) for dl in dw_lengths)


def cert_pe(trailer, cert_offset=HEADER_LEN_PE32, cert_size=None):
    cert_size = len(trailer) if cert_size is None else cert_size
    return pe32(cert_offset=cert_offset, cert_size=cert_size, trailer=trailer)


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

    # ===== Identidade / offsets =====
    expect_ok("PE32 valido", pe32(), lambda r: [
        ("pe_format PE32", r["pe_format"] == "PE32"),
        ("magic 0x010b", r["optional_header_magic"] == "0x010b"),
        ("soh 224", r["size_of_optional_header"] == 224),
        ("cert ausente", r["certificate_table"]["present"] is False),
        ("cert parseavel", r["certificate_table"]["structurally_parseable"] is True),
        ("nao executado", r["executed"] is False and r["loaded_as_executable"] is False),
    ])
    expect_ok("PE32+ valido", pe32plus(), lambda r: [
        ("pe_format PE32+", r["pe_format"] == "PE32+"),
        ("soh 240", r["size_of_optional_header"] == 240),
    ])
    # Regressao R1 (offset): soh 0xE0 -> 224, nunca 267.
    expect_ok("regressao offset (soh 0xE0 -> 224)", pe32(), lambda r: [
        ("soh == 224", r["size_of_optional_header"] == 224),
        ("soh != 267", r["size_of_optional_header"] != 267),
    ])
    # R2-D1: coincidencia numerica legitima soh == 267 (== magic PE32) NAO rejeita.
    pe267 = build_pe(0x010b, 267, 16, 92, 96)  # optional header de 267 bytes
    expect_ok("R2: soh=267 (== magic) e valido", pe267, lambda r: [
        ("soh == 267", r["size_of_optional_header"] == 267),
        ("magic 0x010b", r["optional_header_magic"] == "0x010b"),
        ("pe_format PE32", r["pe_format"] == "PE32"),
        ("observacao registrada", r.get("size_of_optional_header_equals_magic_observation") is True),
        ("nao ha regra de invalidade por igualdade", r["pe_valid"] is True),
    ])

    expect_fail("MZ ausente", b"XX" + pe32()[2:])
    bad_lfa = bytearray(pe32()); struct.pack_into("<I", bad_lfa, 0x3C, 0x7fffffff)
    expect_fail("e_lfanew fora do arquivo", bytes(bad_lfa))
    bad_pe = bytearray(pe32()); bad_pe[0x40:0x44] = b"XXXX"
    expect_fail("assinatura PE ausente", bytes(bad_pe))
    expect_fail("COFF truncado", pe32()[:0x44 + 10])
    expect_fail("Optional Header truncado", pe32(opt_actual_len=0x40))
    expect_fail("SizeOfOptionalHeader pequeno", build_pe(0x010b, 80, 16, 92, 96, coff_soh=80))
    expect_fail("magic desconhecido", build_pe(0x1234, 0xE0, 16, 92, 96))
    expect_fail("NumberOfRvaAndSizes incompativel", build_pe(0x010b, 0xE0, 100, 92, 96))

    # ===== Certificate Table (FASE D/E) =====
    # 1) ausente (offset 0 / size 0)
    expect_ok("cert ausente offset0/size0", pe32(), lambda r: [
        ("present false", r["certificate_table"]["present"] is False),
        ("structurally_parseable true", r["certificate_table"]["structurally_parseable"] is True),
        ("entry_count 0", r["certificate_table"]["entry_count"] == 0),
    ])
    # 2) offset 0 / size != 0 -> rejeitar
    expect_fail("cert offset0/size!=0 (parcial)",
                pe32(cert_offset=0, cert_size=16, trailer=b"\x00" * 16))
    # 3) offset != 0 / size 0 -> rejeitar
    expect_fail("cert offset!=0/size0 (parcial)",
                pe32(cert_offset=HEADER_LEN_PE32, cert_size=0, trailer=b"\x00" * 16))
    # 4) offset desalinhado -> rejeitar
    expect_fail("cert offset desalinhado",
                pe32(cert_offset=HEADER_LEN_PE32 + 1, cert_size=16, trailer=b"\x00" * 24))
    # 5) tamanho < 8 -> rejeitar
    expect_fail("cert size < 8", cert_pe(b"\x00" * 8, cert_size=4))
    # 6) dwLength < 8 -> rejeitar
    expect_fail("dwLength < 8",
                cert_pe(struct.pack("<IHH", 4, 0x0200, 0x0002), cert_size=8))
    # 7) dwLength alem da tabela -> rejeitar
    expect_fail("dwLength alem da tabela",
                cert_pe(struct.pack("<IHH", 64, 0x0200, 0x0002) + b"\x00" * 8, cert_size=16))
    # 8) entrada truncada (segunda entrada cortada)
    expect_fail("entrada truncada",
                cert_pe(wincert(16) + b"\x00" * 4, cert_size=20))
    # 9) uma entrada PKCS#7 sintetica valida
    expect_ok("uma entrada PKCS#7 valida", cert_pe(table(24)), lambda r: [
        ("present true", r["certificate_table"]["present"] is True),
        ("entry_count 1", r["certificate_table"]["entry_count"] == 1),
        ("type PKCS7", r["certificate_table"]["entries"][0]["certificate_type_name"] == "WIN_CERT_TYPE_PKCS_SIGNED_DATA"),
        ("dw_length 24", r["certificate_table"]["entries"][0]["dw_length"] == 24),
    ])
    # 10) duas entradas validas
    expect_ok("duas entradas validas", cert_pe(table(16, 24)), lambda r: [
        ("entry_count 2", r["certificate_table"]["entry_count"] == 2),
    ])
    # 11/12) progressao alinhada a 8 + padding valido (dwLength nao multiplo de 8)
    expect_ok("progressao align8 + padding", cert_pe(table(20, 12)), lambda r: [
        ("entry_count 2", r["certificate_table"]["entry_count"] == 2),
        ("dw_length 20", r["certificate_table"]["entries"][0]["dw_length"] == 20),
        ("dw_length 12", r["certificate_table"]["entries"][1]["dw_length"] == 12),
    ])
    # 13) soma final incompativel com o tamanho da tabela -> rejeitar
    expect_fail("soma final incompativel", cert_pe(table(16) + b"\x00" * 8, cert_size=24))
    # 14) ausencia de loop/progresso zero (muitas entradas minimas terminam)
    expect_ok("muitas entradas minimas terminam", cert_pe(table(*([8] * 10))), lambda r: [
        ("entry_count 10", r["certificate_table"]["entry_count"] == 10),
    ])
    # 15) nenhum conteudo de bCertificate aparece no JSON
    marker = b"CERTBODYMARKER42"
    blob = struct.pack("<IHH", 8 + len(marker), 0x0200, 0x0002) + marker
    blob = blob + b"\x00" * (align8(len(blob)) - len(blob))
    r15 = expect_ok("cert presente com conteudo", cert_pe(blob, cert_size=len(blob)), lambda r: [
        ("present true", r["certificate_table"]["present"] is True),
    ])
    if r15 is not None:
        js = json.dumps(r15, ensure_ascii=False)
        ok("15 nenhum bCertificate no JSON", "CERTBODYMARKER" not in js)
        entry_keys = set(r15["certificate_table"]["entries"][0].keys())
        ok("15 apenas metadados estruturais",
           entry_keys == {"dw_length", "revision", "certificate_type", "certificate_type_name"})

    # 16/17) fixtures temporarias removidas; nenhum arquivo executado.
    tmpdir = tempfile.mkdtemp(prefix="pe-fixtures-")
    removed = True
    try:
        good = os.path.join(tmpdir, "good.bin")
        with open(good, "wb") as fh:
            fh.write(cert_pe(table(24)))
        r = mod.inspect(open(good, "rb").read())
        ok("17 nao executa/carrega o arquivo",
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
    ok("16 fixtures temporarias removidas", removed and not os.path.exists(tmpdir))

    print(f"\nResumo: {passed} teste(s) OK, {failed} falha(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"[ERRO] falha inesperada: {exc}")
        sys.exit(2)
