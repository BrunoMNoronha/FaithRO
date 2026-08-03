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

# Tipos de WIN_CERTIFICATE (wCertificateType). Apenas metadado estrutural; o
# conteudo (bCertificate / PKCS#7) NAO e interpretado nem emitido.
WIN_CERT_TYPE = {
    0x0001: "WIN_CERT_TYPE_X509",
    0x0002: "WIN_CERT_TYPE_PKCS_SIGNED_DATA",
    0x0003: "WIN_CERT_TYPE_RESERVED_1",
    0x0004: "WIN_CERT_TYPE_TS_STACK_SIGNED",
}


def align8(value):
    """Arredonda para o proximo multiplo de 8 (alinhamento do WIN_CERTIFICATE)."""
    return (value + 7) & ~7


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


def _parse_certificate_table(data, n, dd_start, num_rva):
    """Parsing ESTRUTURAL da Certificate Table (WIN_CERTIFICATE), sem interpretar o
    PKCS#7. Retorna apenas metadados. 'structurally_parseable' significa que a
    presenca/ausencia foi determinada de forma estrutural coerente — NAO que existe
    uma assinatura valida. Levanta PEError em inconsistencia estrutural.

    Regras (2P-E-C3-R2):
      * a entrada so existe quando NumberOfRvaAndSizes > 4;
      * o primeiro campo e file offset (nao RVA);
      * offset e tamanho devem ser ambos zero ou ambos != zero (par parcial e rejeitado);
      * quando presente: offset/tamanho dentro do arquivo, soma sem overflow, inicio
        alinhado a 8 bytes, tamanho >= 8 (ao menos um cabecalho WIN_CERTIFICATE);
      * percorre entradas: >=8 bytes restantes, dwLength>=8, dwLength dentro da tabela,
        avanco por align8(dwLength) > 0 (sem loop), soma final == tamanho da tabela.
    """
    cert = {
        "index": CERT_TABLE_INDEX,
        "first_field_is_file_offset_not_rva": True,
        "present": False,
        "structurally_parseable": True,
        "file_offset": 0,
        "size": 0,
        "entry_count": 0,
        "entries": [],
    }
    # 1) A entrada so existe quando NumberOfRvaAndSizes > 4.
    if num_rva <= CERT_TABLE_INDEX:
        cert["security_directory_entry_present"] = False
        return cert
    cert["security_directory_entry_present"] = True

    entry = dd_start + CERT_TABLE_INDEX * DATADIR_ENTRY_SIZE
    cert_off = _u32(data, entry)
    cert_size = _u32(data, entry + 4)
    cert["file_offset"] = cert_off
    cert["size"] = cert_size

    # 3/4) Ambos zero => ausente; par parcialmente zerado => inconsistente.
    if cert_off == 0 and cert_size == 0:
        return cert  # present=False, structurally_parseable=True, entry_count=0
    if (cert_off == 0) != (cert_size == 0):
        raise PEError("Certificate Table com par offset/tamanho parcialmente zerado")

    # 5) Presente: bounds, overflow, alinhamento e tamanho minimo.
    if cert_off < 0 or cert_size < 0:
        raise PEError("Certificate Table com offset/tamanho negativo")
    if cert_off > n or cert_size > n:
        raise PEError("Certificate Table: offset/tamanho fora do arquivo")
    if cert_off + cert_size > n:  # soma sem overflow (Python: inteiros exatos)
        raise PEError("Certificate Table ultrapassa o fim do arquivo")
    if cert_off % 8 != 0:
        raise PEError("Certificate Table: inicio nao alinhado a 8 bytes")
    if cert_size < 8:
        raise PEError("Certificate Table: tamanho < 8 (sem cabecalho WIN_CERTIFICATE)")

    # 6..9) Percorre WIN_CERTIFICATE sem interpretar bCertificate.
    end = cert_off + cert_size
    pos = cert_off
    entries = []
    guard = 0
    while pos < end:
        guard += 1
        if guard > 4096:
            raise PEError("Certificate Table: numero de entradas implausivel (loop?)")
        remaining = end - pos
        if remaining < 8:
            raise PEError("Certificate Table: bytes restantes (%d) < cabecalho "
                          "WIN_CERTIFICATE; soma final incompativel" % remaining)
        dw_length = _u32(data, pos)
        w_revision = _u16(data, pos + 4)
        w_cert_type = _u16(data, pos + 6)
        if dw_length < 8:
            raise PEError("WIN_CERTIFICATE dwLength (%d) < 8" % dw_length)
        if pos + dw_length > end:
            raise PEError("WIN_CERTIFICATE dwLength ultrapassa a tabela")
        entries.append({
            "dw_length": dw_length,
            "revision": "0x%04x" % w_revision,
            "certificate_type": "0x%04x" % w_cert_type,
            "certificate_type_name": WIN_CERT_TYPE.get(w_cert_type, "OTHER"),
        })
        step = align8(dw_length)
        if step <= 0:
            raise PEError("WIN_CERTIFICATE avanco nao positivo")
        pos += step
    # 9) A soma dos avancos deve coincidir exatamente com o tamanho da tabela
    #    (cada entrada e alinhada a 8 bytes; padding previsto pela especificacao).
    if pos != end:
        raise PEError("Certificate Table: soma final (%d) != tamanho declarado (%d)"
                      % (pos - cert_off, cert_size))

    cert["present"] = True
    cert["within_file"] = True
    cert["entry_count"] = len(entries)
    cert["entries"] = entries
    return cert


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

    # OBSERVACAO (NAO e regra de invalidade): registra apenas se, por coincidencia
    # numerica, SizeOfOptionalHeader e Magic sao iguais. A igualdade NAO viola o
    # formato PE (ex.: soh 267 e um valor legitimo). A garantia contra o bug de offset
    # (2P-E-C3-R1) e ler soh de coff+16 e Magic do inicio do Optional Header, campos
    # SEPARADOS, exercitados por testes de regressao — nao rejeitar por igualdade.
    result["size_of_optional_header_equals_magic_observation"] = (size_opt == magic)

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

    # 21/22/23) Certificate Table (IMAGE_DIRECTORY_ENTRY_SECURITY): parsing estrutural
    #           limitado ao GATE 3. O primeiro campo do Data Directory e um FILE OFFSET
    #           (nao RVA). Percorre os WIN_CERTIFICATE sem interpretar o PKCS#7
    #           (bCertificate) e emite apenas metadados estruturais.
    result["certificate_table"] = _parse_certificate_table(
        data, n, dd_start, num_rva)

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
