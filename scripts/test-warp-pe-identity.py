#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes do inspetor PE offline (scripts/inspect-warp-pe-identity.py), ETAPA 2P-E-C3-R1.

Constroi PEs SINTETICOS em memoria (bytes) e em arquivos temporarios removidos ao
final; NUNCA versiona um executavel real e NUNCA executa/carrega o arquivo. Valida a
LOGICA REAL do parser (nao mutacoes de JSON de evidencia), com foco na regressao D2
(SizeOfOptionalHeader nao pode virar 267 = magic PE32) e no bounds checking.

Offline: nao acessa a rede, nao usa subprocess para iniciar o arquivo, nao importa
modulos de rede. Criterio: parse correto nos casos validos e rejeicao (excecao / exit
!= 0) nos invalidos.
"""
import importlib.util
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


def build_pe(magic, soh, num_rva, num_rva_off, datadir_off,
             coff_soh=None, cert_offset=0, cert_size=0, cert_blob=b"",
             opt_actual_len=None):
    """Constroi um PE sintetico minimo (apenas cabecalhos, sem secoes/codigo).

    - `soh` e o SizeOfOptionalHeader declarado no COFF (via `coff_soh`, se dado) e o
      tamanho logico do Optional Header.
    - `opt_actual_len` permite gerar MENOS bytes de Optional Header que o declarado
      (para simular truncamento).
    """
    coff_soh = soh if coff_soh is None else coff_soh
    dos = bytearray(0x40)
    dos[0:2] = b"MZ"
    struct.pack_into("<I", dos, 0x3C, 0x40)  # e_lfanew
    pe = b"PE\x00\x00"
    coff = bytearray(20)
    struct.pack_into("<H", coff, 0, 0x014c)   # Machine = x86
    struct.pack_into("<H", coff, 2, 1)        # NumberOfSections
    struct.pack_into("<I", coff, 4, 0)        # TimeDateStamp
    struct.pack_into("<H", coff, 16, coff_soh)  # SizeOfOptionalHeader (campo correto)
    struct.pack_into("<H", coff, 18, 0x0102)  # Characteristics
    opt = bytearray(soh)
    struct.pack_into("<H", opt, 0, magic)
    if len(opt) >= 68:
        struct.pack_into("<I", opt, 64, 0)    # CheckSum
    if len(opt) >= 70:
        struct.pack_into("<H", opt, 68, 2)    # Subsystem = WINDOWS_GUI
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
    body = bytes(dos) + pe + bytes(coff) + bytes(opt) + cert_blob
    return body


def pe32(**kw):
    return build_pe(0x010b, 0xE0, 16, 92, 96, **kw)


def pe32plus(**kw):
    return build_pe(0x020b, 0xF0, 16, 108, 112, **kw)


HEADER_LEN_PE32 = 0x40 + 4 + 20 + 0xE0  # DOS + PE + COFF + Optional(0xE0)


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
            return
        if checks:
            for desc, cond in checks(r):
                ok(f"{label}: {desc}", cond)
        else:
            passed += 1
            print(f"[OK+]   {label}")

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

    # 1) PE32 valido.
    expect_ok("1 PE32 valido", pe32(), lambda r: [
        ("pe_format PE32", r["pe_format"] == "PE32"),
        ("magic 0x010b", r["optional_header_magic"] == "0x010b"),
        ("soh 224", r["size_of_optional_header"] == 224),
        ("num_rva 16", r["number_of_rva_and_sizes"] == 16),
        ("subsystem 2", r["subsystem_value"] == 2),
        ("cert ausente", r["certificate_table"]["present"] is False),
        ("nao executado", r["executed"] is False and r["loaded_as_executable"] is False),
        ("lido para inspecao", r["file_read_for_static_inspection"] is True),
    ])

    # 2) PE32+ valido.
    expect_ok("2 PE32+ valido", pe32plus(), lambda r: [
        ("pe_format PE32+", r["pe_format"] == "PE32+"),
        ("magic 0x020b", r["optional_header_magic"] == "0x020b"),
        ("soh 240", r["size_of_optional_header"] == 240),
        ("num_rva 16", r["number_of_rva_and_sizes"] == 16),
    ])

    # 3) Regressao D2: magic 0x10b + soh 0xE0 => parser NAO retorna 267.
    expect_ok("3 regressao D2 (soh != magic)", pe32(), lambda r: [
        ("soh == 224 (0xE0)", r["size_of_optional_header"] == 224),
        ("soh != 267 (0x10b)", r["size_of_optional_header"] != 267),
        ("soh != magic", r["size_of_optional_header_equals_magic"] is False),
    ])

    # 4) MZ ausente.
    bad_mz = bytearray(pe32())
    bad_mz[0:2] = b"XX"
    expect_fail("4 MZ ausente", bytes(bad_mz))

    # 5) e_lfanew fora do arquivo.
    bad_lfa = bytearray(pe32())
    struct.pack_into("<I", bad_lfa, 0x3C, 0x7fffffff)
    expect_fail("5 e_lfanew fora do arquivo", bytes(bad_lfa))

    # 6) Assinatura PE ausente.
    bad_pe = bytearray(pe32())
    bad_pe[0x40:0x44] = b"XXXX"
    expect_fail("6 assinatura PE ausente", bytes(bad_pe))

    # 7) COFF header truncado.
    expect_fail("7 COFF truncado", pe32()[:0x44 + 10])

    # 8) Optional header truncado (declara 0xE0, entrega menos).
    expect_fail("8 Optional Header truncado",
                pe32(opt_actual_len=0x40))

    # 9) SizeOfOptionalHeader menor que o necessario (num_rva alem do soh).
    expect_fail("9 SizeOfOptionalHeader pequeno",
                build_pe(0x010b, 80, 16, 92, 96, coff_soh=80))

    # 10) Magic desconhecido.
    expect_fail("10 magic desconhecido",
                build_pe(0x1234, 0xE0, 16, 92, 96))

    # 11) NumberOfRvaAndSizes incompativel (nao cabe no soh/arquivo).
    expect_fail("11 NumberOfRvaAndSizes incompativel",
                build_pe(0x010b, 0xE0, 100, 92, 96))

    # 12) Certificate Table alem do fim do arquivo.
    expect_fail("12 Certificate Table alem do fim",
                pe32(cert_offset=HEADER_LEN_PE32 + 1000, cert_size=16))

    # 13) Certificate Table parcialmente truncada.
    expect_fail("13 Certificate Table truncada",
                pe32(cert_offset=HEADER_LEN_PE32, cert_size=64,
                     cert_blob=b"\x00" * 10))

    # 14) Certificate Table sintetica estruturalmente valida (presente).
    blob = b"\x10\x00\x00\x00\x00\x02\x02\x00" + b"\xAA" * 8  # WIN_CERTIFICATE min
    expect_ok("14 Certificate Table presente",
              pe32(cert_offset=HEADER_LEN_PE32, cert_size=len(blob), cert_blob=blob),
              lambda r: [
                  ("cert presente", r["certificate_table"]["present"] is True),
                  ("dentro do arquivo", r["certificate_table"]["within_file"] is True),
                  ("primeiro campo e file offset", r["certificate_table"]["first_field_is_file_offset_not_rva"] is True),
              ])

    # 15) Nenhum teste executa o arquivo: exercitamos main() com exit codes usando
    #     arquivos temporarios removidos (leitura apenas; sem subprocess de execucao).
    tmpdir = tempfile.mkdtemp(prefix="pe-fixtures-")
    fixtures_removed = True
    try:
        good = os.path.join(tmpdir, "good.bin")
        with open(good, "wb") as fh:
            fh.write(pe32())
        ok("15a main() exit 0 em PE valido", mod.main(["x", good]) == 0)
        bad = os.path.join(tmpdir, "bad.bin")
        with open(bad, "wb") as fh:
            fh.write(b"not a pe")
        ok("15b main() exit != 0 em invalido", mod.main(["x", bad]) != 0)
        ok("15c main() exit != 0 em inexistente",
           mod.main(["x", os.path.join(tmpdir, "nope.bin")]) != 0)
    finally:
        for f in ("good.bin", "bad.bin"):
            p = os.path.join(tmpdir, f)
            if os.path.exists(p):
                os.remove(p)
        try:
            os.rmdir(tmpdir)
        except OSError:
            fixtures_removed = False
    ok("15d fixtures temporarias removidas", fixtures_removed and not os.path.exists(tmpdir))

    print(f"\nResumo: {passed} teste(s) OK, {failed} falha(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"[ERRO] falha inesperada: {exc}")
        sys.exit(2)
