#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspetor PE OFFLINE, revisavel e testavel (ETAPA 2P-E-C3-R1).

Le um arquivo local e emite, em stdout, um JSON deterministico com a IDENTIDADE
estrutural minima de um PE (cabecalhos DOS/COFF/Optional e a presenca da Certificate
Table). NAO executa, NAO carrega, NAO baixa nada e NAO acessa a rede. Usa apenas a
biblioteca padrao do Python. Sai com codigo != 0 em PE truncado, invalido ou
inconsistente. NUNCA imprime conteudo binario.

Este inspetor foi criado para substituir, de forma auditavel, o parser de scratchpad
nao versionado que gerou a evidencia inicial do GATE 3 (ver docs/39). Ele NAO faz
inventario de imports/exports/strings/entropia/TLS/recursos (isso pertence ao GATE 4)
e NAO decodifica recursos de versao: os campos de versao sao reportados como
NOT_DETERMINED_BY_REVIEWED_PARSER.

Uso:
    python scripts/inspect-warp-pe-identity.py <caminho-local>

Nao ha logica de download nem de rede: o unico argumento e um caminho local ja
existente. O chamador e responsavel por prover o arquivo; este script apenas o le.
"""
import json
import os
import struct
import sys

MACHINE = {
    0x014c: "IMAGE_FILE_MACHINE_I386 (x86)",
    0x8664: "IMAGE_FILE_MACHINE_AMD64 (x64)",
    0x01c0: "IMAGE_FILE_MACHINE_ARM",
    0xaa64: "IMAGE_FILE_MACHINE_ARM64",
    0x01c4: "IMAGE_FILE_MACHINE_ARMNT",
    0x0200: "IMAGE_FILE_MACHINE_IA64",
}
SUBSYSTEM = {
    0: "IMAGE_SUBSYSTEM_UNKNOWN",
    1: "IMAGE_SUBSYSTEM_NATIVE",
    2: "IMAGE_SUBSYSTEM_WINDOWS_GUI",
    3: "IMAGE_SUBSYSTEM_WINDOWS_CUI",
    9: "IMAGE_SUBSYSTEM_WINDOWS_CE_GUI",
}
MAGIC_PE32 = 0x010b
MAGIC_PE32_PLUS = 0x020b

# Offsets internos do COFF File Header (a partir do inicio do COFF, logo apos 'PE\0\0').
COFF_MACHINE = 0
COFF_NUMBER_OF_SECTIONS = 2
COFF_TIMEDATESTAMP = 4
COFF_SIZE_OF_OPTIONAL_HEADER = 16  # NAO confundir com o inicio do Optional Header.
COFF_CHARACTERISTICS = 18
COFF_SIZE = 20

# Offsets internos do Optional Header (a partir do Magic).
OPT_MAGIC = 0
OPT_CHECKSUM = 64
OPT_SUBSYSTEM = 68
OPT_NUM_RVA_PE32 = 92
OPT_NUM_RVA_PE32_PLUS = 108
OPT_DATADIR_PE32 = 96
OPT_DATADIR_PE32_PLUS = 112
DATADIR_ENTRY_SIZE = 8
CERT_TABLE_INDEX = 4  # IMAGE_DIRECTORY_ENTRY_SECURITY


class PEError(Exception):
    """Erro de PE truncado, invalido ou inconsistente."""


def _u16(data, off):
    if off < 0 or off + 2 > len(data):
        raise PEError(f"leitura u16 fora do arquivo no offset {off}")
    return struct.unpack_from("<H", data, off)[0]


def _u32(data, off):
    if off < 0 or off + 4 > len(data):
        raise PEError(f"leitura u32 fora do arquivo no offset {off}")
    return struct.unpack_from("<I", data, off)[0]


def inspect(data):
    """Recebe os bytes do arquivo e retorna o dict de identidade. Levanta PEError."""
    n = len(data)
    result = {"file_size": n}

    # 1) Tamanho minimo do cabecalho DOS (precisa conter e_lfanew em 0x3C).
    if n < 0x40:
        raise PEError("arquivo menor que o cabecalho DOS minimo (64 bytes)")

    # 2) Assinatura MZ.
    result["mz_present"] = data[0:2] == b"MZ"
    if not result["mz_present"]:
        raise PEError("assinatura MZ ausente")

    # 3) Leitura segura de e_lfanew.
    e_lfanew = _u32(data, 0x3C)
    result["e_lfanew"] = e_lfanew

    # 4) e_lfanew deve apontar para regiao valida (com espaco para 'PE\0\0').
    if e_lfanew < 0x40 or e_lfanew + 4 > n:
        raise PEError(f"e_lfanew ({e_lfanew}) fora da regiao valida do arquivo")

    # 5) Assinatura PE\0\0.
    result["pe_signature_present"] = data[e_lfanew:e_lfanew + 4] == b"PE\x00\x00"
    if not result["pe_signature_present"]:
        raise PEError("assinatura PE\\0\\0 ausente")

    # 6) COFF File Header completo.
    coff = e_lfanew + 4
    if coff + COFF_SIZE > n:
        raise PEError("COFF File Header truncado")

    # 7) Machine.
    machine = _u16(data, coff + COFF_MACHINE)
    result["machine_value"] = "0x%04x" % machine
    result["machine"] = MACHINE.get(machine, "OTHER")
    # 8) NumberOfSections.
    result["number_of_sections"] = _u16(data, coff + COFF_NUMBER_OF_SECTIONS)
    # 9) TimeDateStamp (metadado NAO confiavel).
    result["timedatestamp_raw"] = _u32(data, coff + COFF_TIMEDATESTAMP)
    result["timedatestamp_is_trusted"] = False
    # 10) SizeOfOptionalHeader lido do CAMPO CORRETO do COFF (coff+16), NAO do magic.
    size_opt = _u16(data, coff + COFF_SIZE_OF_OPTIONAL_HEADER)
    result["size_of_optional_header"] = size_opt
    result["characteristics"] = "0x%04x" % _u16(data, coff + COFF_CHARACTERISTICS)

    # 11) Inicio do Optional Header calculado SEPARADAMENTE.
    opt = coff + COFF_SIZE
    result["optional_header_offset"] = opt
    if size_opt < 2:
        raise PEError(f"SizeOfOptionalHeader ({size_opt}) menor que o minimo")
    # 15) O Optional Header (conforme declarado) deve caber no arquivo.
    if opt + size_opt > n:
        raise PEError("Optional Header declarado ultrapassa o fim do arquivo")

    # 12) Magic lido do inicio do Optional Header.
    magic = _u16(data, opt + OPT_MAGIC)
    result["optional_header_magic"] = "0x%04x" % magic
    # 13/14) Suporte explicito a PE32/PE32+; rejeitar magic desconhecido.
    if magic == MAGIC_PE32:
        result["pe_format"] = "PE32"
        num_rva_off = OPT_NUM_RVA_PE32
        datadir_off = OPT_DATADIR_PE32
    elif magic == MAGIC_PE32_PLUS:
        result["pe_format"] = "PE32+"
        num_rva_off = OPT_NUM_RVA_PE32_PLUS
        datadir_off = OPT_DATADIR_PE32_PLUS
    else:
        raise PEError(f"magic desconhecido no Optional Header: 0x%04x" % magic)

    # Coerencia D2: SizeOfOptionalHeader NAO pode ser igual ao magic (indicio de
    # leitura do campo errado, ex.: 0x010b == 267).
    result["size_of_optional_header_equals_magic"] = (size_opt == magic)
    if size_opt == magic:
        raise PEError(
            "SizeOfOptionalHeader igual ao magic (0x%04x); indicio de offset "
            "incorreto na leitura do campo" % magic)

    # 16) Campos acessados devem caber em SizeOfOptionalHeader e no arquivo.
    def opt_field_bounds(field_off, width, name):
        if field_off + width > size_opt:
            raise PEError(f"{name} fora de SizeOfOptionalHeader")
        if opt + field_off + width > n:
            raise PEError(f"{name} fora do arquivo")

    # 17) Subsystem.
    opt_field_bounds(OPT_SUBSYSTEM, 2, "Subsystem")
    subs = _u16(data, opt + OPT_SUBSYSTEM)
    result["subsystem_value"] = subs
    result["subsystem"] = SUBSYSTEM.get(subs, "OTHER")
    # 18) CheckSum (metadado declarado).
    opt_field_bounds(OPT_CHECKSUM, 4, "CheckSum")
    result["checksum_declared"] = "0x%08x" % _u32(data, opt + OPT_CHECKSUM)
    # 19) NumberOfRvaAndSizes.
    opt_field_bounds(num_rva_off, 4, "NumberOfRvaAndSizes")
    num_rva = _u32(data, opt + num_rva_off)
    result["number_of_rva_and_sizes"] = num_rva

    # 20) Data Directory validado contra SizeOfOptionalHeader, NumberOfRvaAndSizes
    #     e o tamanho fisico do arquivo.
    dd_start = opt + datadir_off
    if num_rva > 65535:
        raise PEError("NumberOfRvaAndSizes implausivelmente grande")
    dd_bytes = num_rva * DATADIR_ENTRY_SIZE
    if datadir_off + dd_bytes > size_opt:
        raise PEError("Data Directory nao cabe em SizeOfOptionalHeader")
    if dd_start + dd_bytes > n:
        raise PEError("Data Directory ultrapassa o fim do arquivo")

    # 21/22/23) Certificate Table no indice correto; primeiro campo e FILE OFFSET
    #           (nao RVA); offset e tamanho nao podem ultrapassar o arquivo.
    cert = {"present": False, "index": CERT_TABLE_INDEX,
            "first_field_is_file_offset_not_rva": True}
    if num_rva > CERT_TABLE_INDEX:
        entry = dd_start + CERT_TABLE_INDEX * DATADIR_ENTRY_SIZE
        cert_off = _u32(data, entry)
        cert_size = _u32(data, entry + 4)
        cert["file_offset"] = cert_off
        cert["size"] = cert_size
        if cert_size > 0 and cert_off > 0:
            if cert_off + cert_size > n:
                raise PEError("Certificate Table ultrapassa o fim do arquivo")
            cert["present"] = True
            cert["within_file"] = True
        else:
            cert["within_file"] = True
    result["certificate_table"] = cert

    # Informacoes de versao: NAO decodificadas por este parser revisavel (recurso).
    result["version_info_status"] = "NOT_DETERMINED_BY_REVIEWED_PARSER"

    # Identidade estrutural consistente ate aqui.
    result["pe_valid"] = True
    result["file_read_for_static_inspection"] = True
    result["launched"] = False
    result["executed"] = False
    result["loaded_as_executable"] = False
    return result


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("uso: inspect-warp-pe-identity.py <caminho-local>\n")
        return 2
    path = argv[1]
    if not os.path.isfile(path):
        sys.stderr.write(f"arquivo inexistente: {path}\n")
        return 2
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        sys.stderr.write(f"falha ao ler arquivo: {exc}\n")
        return 2
    try:
        result = inspect(data)
    except PEError as exc:
        sys.stderr.write(f"PE invalido/inconsistente: {exc}\n")
        return 2
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
