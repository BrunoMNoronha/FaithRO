#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inventario PE ESTATICO offline, revisavel e testavel (ETAPA 2P-E-C4-PREP).

Le um arquivo local (modo binario, somente leitura) e emite, em stdout, um JSON
DETERMINISTICO com um inventario PE estatico: cabecalhos, secoes (caracteristicas,
permissoes, tamanhos raw/virtual, entropia), overlay, imports (por nome e ordinal),
exports, recursos/manifest (nivel de execucao solicitado), TLS callbacks, relocations,
debug directory, Certificate Table (somente estrutura), dependencias declaradas,
indicadores estruturais de empacotamento e indicadores textuais (DLLs, APIs, URLs,
dominios, caminhos, mutex/servico/registro) SANITIZADOS e LIMITADOS.

NAO executa, NAO carrega, NAO emula, NAO descompacta dinamicamente e NAO baixa nada.
NAO acessa a rede. Usa APENAS a biblioteca padrao do Python. Falha FECHADA (exit != 0)
em PE truncado, inconsistente ou sobreposto. NUNCA emite bytes brutos, conteudo de
`bCertificate`, base64, hexdumps, dump integral de recursos/strings, segredos ou
caminhos pessoais.

Escopo (contrato do GATE 4 — ver docs/40): APENAS inventario estatico. Uma API importada
NAO prova uso; uma string NAO prova comportamento; entropia alta NAO prova empacotamento
nem malware; ausencia de indicador NAO prova seguranca; achados estaticos exigem
interpretacao contextual; nenhuma conclusao depende de uma unica metrica. Este inventario
NAO executa, NAO autoriza o GATE 5 e NAO autoriza uso no cliente ou distribuicao.

Esta ferramenta e DELIBERADAMENTE separada de scripts/inspect-warp-pe-identity.py
(GATE 3, byte-fixado). Nao ha codigo compartilhado importado entre as duas, para nao
alterar os Git blob OIDs protegidos do GATE 3.

Uso:
    python scripts/inspect-warp-pe-static.py <caminho-local>

Nao ha logica de download nem de rede: o unico argumento e um caminho local ja
existente. O chamador e responsavel por prover o arquivo; este script apenas o le.
"""
import json
import math
import os
import re
import struct
import sys

# --------------------------------------------------------------------------- #
# Constantes de formato PE.
# --------------------------------------------------------------------------- #
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

COFF_MACHINE = 0
COFF_NUMBER_OF_SECTIONS = 2
COFF_TIMEDATESTAMP = 4
COFF_SIZE_OF_OPTIONAL_HEADER = 16
COFF_CHARACTERISTICS = 18
COFF_SIZE = 20

OPT_MAGIC = 0
OPT_SECTION_ALIGNMENT = 32
OPT_FILE_ALIGNMENT = 36
OPT_SIZE_OF_IMAGE = 56
OPT_SIZE_OF_HEADERS = 60
OPT_SUBSYSTEM = 68
# ImageBase e NumberOfRvaAndSizes/DataDirectory tem offsets distintos em PE32/PE32+.
OPT_IMAGE_BASE_PE32 = 28          # 4 bytes
OPT_IMAGE_BASE_PE32_PLUS = 24     # 8 bytes
OPT_NUM_RVA_PE32 = 92
OPT_NUM_RVA_PE32_PLUS = 108
OPT_DATADIR_PE32 = 96
OPT_DATADIR_PE32_PLUS = 112
DATADIR_ENTRY_SIZE = 8

DIR_EXPORT = 0
DIR_IMPORT = 1
DIR_RESOURCE = 2
DIR_SECURITY = 4
DIR_BASERELOC = 5
DIR_DEBUG = 6
DIR_TLS = 9

SECTION_HEADER_SIZE = 40
MAX_IMAGE_SECTIONS = 96
IMAGE_FILE_EXECUTABLE_IMAGE = 0x0002

SCN_CNT_CODE = 0x00000020
SCN_CNT_INITIALIZED_DATA = 0x00000040
SCN_CNT_UNINITIALIZED_DATA = 0x00000080
SCN_MEM_DISCARDABLE = 0x02000000
SCN_MEM_EXECUTE = 0x20000000
SCN_MEM_READ = 0x40000000
SCN_MEM_WRITE = 0x80000000

WIN_CERT_TYPE = {
    0x0001: "WIN_CERT_TYPE_X509",
    0x0002: "WIN_CERT_TYPE_PKCS_SIGNED_DATA",
    0x0003: "WIN_CERT_TYPE_RESERVED_1",
    0x0004: "WIN_CERT_TYPE_TS_STACK_SIGNED",
    0x0009: "WIN_CERT_TYPE_PKCS1_SIGN",
}
RT_MANIFEST = 24
DEBUG_TYPE = {
    0: "UNKNOWN", 1: "COFF", 2: "CODEVIEW", 3: "FPO", 4: "MISC",
    5: "EXCEPTION", 6: "FIXUP", 9: "BORLAND", 12: "VC_FEATURE",
    13: "POGO", 14: "ILTCG", 16: "REPRO",
}

# --------------------------------------------------------------------------- #
# Limites (impedem evidencias descontroladas). Truncamento e registrado.
# --------------------------------------------------------------------------- #
MAX_IMPORT_DLLS = 128
MAX_APIS_PER_DLL = 256
MAX_ORDINALS_PER_DLL = 256
MAX_EXPORT_NAMES = 128
MAX_RELOC_BLOCKS = 8192
MAX_DEBUG_ENTRIES = 64
MAX_TLS_CALLBACKS = 256
MAX_CERT_ENTRIES = 16
MAX_RESOURCE_TYPES = 64
MAX_STRINGS_PER_CATEGORY = 100
MAX_ITEM_CHARS = 120
MIN_STRING_LEN = 5
MAX_STRING_SCAN_BYTES = 8 * 1024 * 1024   # limite defensivo de varredura
BASE64_RUN_RE = re.compile(r"[A-Za-z0-9+/]{40,}={0,2}")

# --------------------------------------------------------------------------- #
# Tabela FECHADA de classificacao de imports (case-insensitive deterministica).
# Cada API mapeia para EXATAMENTE uma categoria (associacao primaria). Uma API
# desconhecida NAO e classificada por suposicao. Presenca de import NAO e veredito.
# --------------------------------------------------------------------------- #
IMPORT_CLASSIFICATION = {
    # network
    "socket": "network", "connect": "network", "send": "network", "recv": "network",
    "wsastartup": "network", "wsaconnect": "network", "wsasocketa": "network",
    "wsasocketw": "network", "gethostbyname": "network", "getaddrinfo": "network",
    "inet_addr": "network", "bind": "network", "listen": "network", "accept": "network",
    "closesocket": "network", "internetopena": "network", "internetopenw": "network",
    "internetconnecta": "network", "internetconnectw": "network",
    "internetreadfile": "network", "httpopenrequesta": "network",
    "httpopenrequestw": "network", "httpsendrequesta": "network",
    "httpsendrequestw": "network", "urldownloadtofilea": "network",
    "urldownloadtofilew": "network", "winhttpopen": "network",
    "winhttpconnect": "network", "winhttpsendrequest": "network",
    "dnsquery_a": "network", "dnsquery_w": "network",
    # process
    "createprocessa": "process", "createprocessw": "process",
    "createprocessinternalw": "process", "shellexecutea": "process",
    "shellexecutew": "process", "shellexecuteexa": "process",
    "shellexecuteexw": "process", "winexec": "process", "createthread": "process",
    "terminateprocess": "process", "exitprocess": "process",
    "ntcreateuserprocess": "process",
    # service
    "openscmanagera": "service", "openscmanagerw": "service",
    "createservicea": "service", "createservicew": "service",
    "openservicea": "service", "openservicew": "service",
    "startservicea": "service", "startservicew": "service",
    "controlservice": "service", "changeserviceconfiga": "service",
    "changeserviceconfigw": "service", "queryserviceconfiga": "service",
    # registry
    "regopenkeya": "registry", "regopenkeyexa": "registry", "regopenkeyexw": "registry",
    "regsetvaluea": "registry", "regsetvalueexa": "registry", "regsetvalueexw": "registry",
    "regcreatekeya": "registry", "regcreatekeyexa": "registry",
    "regcreatekeyexw": "registry", "regqueryvalueexa": "registry",
    "regqueryvalueexw": "registry", "regdeletekeya": "registry",
    "regdeletevaluea": "registry",
    # remote_memory
    "virtualallocex": "remote_memory", "writeprocessmemory": "remote_memory",
    "readprocessmemory": "remote_memory", "virtualprotectex": "remote_memory",
    "openprocess": "remote_memory", "ntwritevirtualmemory": "remote_memory",
    "ntreadvirtualmemory": "remote_memory",
    # injection
    "createremotethread": "injection", "createremotethreadex": "injection",
    "ntcreatethreadex": "injection", "queueuserapc": "injection",
    "setwindowshookexa": "injection", "setwindowshookexw": "injection",
    "rtlcreateuserthread": "injection",
    # library_loading
    "loadlibrarya": "library_loading", "loadlibraryw": "library_loading",
    "loadlibraryexa": "library_loading", "loadlibraryexw": "library_loading",
    "getprocaddress": "library_loading", "ldrloaddll": "library_loading",
    "getmodulehandlea": "library_loading", "getmodulehandlew": "library_loading",
    # crypto
    "cryptencrypt": "crypto", "cryptdecrypt": "crypto",
    "cryptacquirecontexta": "crypto", "cryptacquirecontextw": "crypto",
    "cryptgenkey": "crypto", "cryptcreatehash": "crypto", "crypthashdata": "crypto",
    "bcryptencrypt": "crypto", "bcryptdecrypt": "crypto",
    "cryptstringtobinarya": "crypto", "cryptbinarytostringa": "crypto",
    # debug_anti_debug
    "isdebuggerpresent": "debug_anti_debug",
    "checkremotedebuggerpresent": "debug_anti_debug",
    "ntqueryinformationprocess": "debug_anti_debug",
    "outputdebugstringa": "debug_anti_debug", "outputdebugstringw": "debug_anti_debug",
    "ntsetinformationthread": "debug_anti_debug",
    "gettickcount": "debug_anti_debug", "queryperformancecounter": "debug_anti_debug",
}
CLASSIFICATION_CATEGORIES = (
    "network", "process", "service", "registry", "remote_memory", "injection",
    "library_loading", "crypto", "debug_anti_debug",
)

# --------------------------------------------------------------------------- #
# Sanitizacao de indicadores textuais.
# --------------------------------------------------------------------------- #
URL_RE = re.compile(r"(?i)\b(?:https?|ftp)://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]{3,}")
DOMAIN_RE = re.compile(
    r"(?i)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?:com|net|org|io|ru|cn|kr|br|info|biz|xyz|top|online|site)\b")
# Caminhos com unidade (drive) ou home pessoal: REDIGIDOS/REJEITADOS (nunca emitidos).
DRIVE_PATH_RE = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]")
PERSONAL_PATH_RE = re.compile(r"(?i)(/home/|/root/|/users/|\\users\\)")
# Caminho embutido "generico" (sem drive/home): backslash ou forward slash com segmento.
EMBEDDED_PATH_RE = re.compile(r"(?:[\\/][A-Za-z0-9_.\- ]{1,40}){2,}")
# Mutex/servico/registro por REGRA EXPLICITA (nao por suposicao livre).
MUTEX_SVC_REG_RE = re.compile(
    r"(?i)^(?:global\\|local\\|session\\|"
    r"(?:hklm|hkcu|hkey_[a-z_]+)\\|software\\|system\\currentcontrolset)")
DEBUG_PACK_RE = re.compile(
    r"(?i)\b(?:UPX[0-9!]?|\.upx|MPRESS|ASPack|FSG!|PECompact|Themida|VMProtect|"
    r"\.petite|nsp[0-9]|Enigma|MoleBox|PEBundle|kkrunchy|\.pdb|WinLicense)\b")
# Segredos/tokens/chaves: NUNCA podem aparecer na saida (rejeitados por regra).
SECRET_RE = re.compile(
    r"(?i)\b(pass(?:word|wd)?|senha|secret|token|api[_-]?key|bearer|private[_-]?key)\b"
    r"\s*[:=]\s*\S")
PRIVATE_KEY_RE = re.compile(r"BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY")
# IPs literais: a politica do projeto proibe IP em qualquer artefato versionado.
IPV4_RE = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
AUTH_HEADER_RE = re.compile(r"(?i)Authorization:\s*\S")


class PEError(Exception):
    """PE truncado, invalido, inconsistente ou sobreposto."""


def _u16(data, off):
    if off < 0 or off + 2 > len(data):
        raise PEError("leitura u16 fora do arquivo no offset %d" % off)
    return struct.unpack_from("<H", data, off)[0]


def _u32(data, off):
    if off < 0 or off + 4 > len(data):
        raise PEError("leitura u32 fora do arquivo no offset %d" % off)
    return struct.unpack_from("<I", data, off)[0]


def _u64(data, off):
    if off < 0 or off + 8 > len(data):
        raise PEError("leitura u64 fora do arquivo no offset %d" % off)
    return struct.unpack_from("<Q", data, off)[0]


def entropy(chunk):
    """Entropia de Shannon (bits/byte, 0..8), determinista. chunk vazio -> 0.0."""
    n = len(chunk)
    if n == 0:
        return 0.0
    counts = [0] * 256
    for b in chunk:
        counts[b] += 1
    ent = 0.0
    for c in counts:
        if c:
            p = c / n
            ent -= p * math.log2(p)
    return round(ent, 6)


def _sanitize_str(s):
    """Trunca a MAX_ITEM_CHARS e remove caracteres de controle (defesa)."""
    s = "".join(ch for ch in s if ch == "\t" or ord(ch) >= 0x20)
    if len(s) > MAX_ITEM_CHARS:
        s = s[:MAX_ITEM_CHARS]
    return s


def _forbidden_indicator(s):
    """True se a string NAO pode ser emitida (segredo, chave, drive/home, base64)."""
    if SECRET_RE.search(s) or PRIVATE_KEY_RE.search(s) or AUTH_HEADER_RE.search(s):
        return True
    if DRIVE_PATH_RE.search(s) or PERSONAL_PATH_RE.search(s):
        return True
    if BASE64_RUN_RE.search(s):
        return True
    for m in IPV4_RE.finditer(s):
        if all(0 <= int(o) <= 255 for o in m.group(0).split(".")):
            return True
    return False


def _bounded_sorted(values, limit):
    """Dedup determinista + ordenacao + truncamento. Retorna (lista, truncated)."""
    uniq = sorted(set(values))
    truncated = len(uniq) > limit
    return uniq[:limit], truncated


# --------------------------------------------------------------------------- #
# Mapa RVA -> offset de arquivo (via Section Table). Fail-closed.
# --------------------------------------------------------------------------- #
def rva_to_offset(sections, rva, file_size):
    """Retorna o offset de arquivo para uma RVA, ou None se nao mapeavel."""
    for s in sections:
        va = s["virtual_address"]
        vsize = s["virtual_size"] if s["virtual_size"] else s["size_of_raw_data"]
        raw = s["pointer_to_raw_data"]
        rawsize = s["size_of_raw_data"]
        if va <= rva < va + max(vsize, rawsize):
            delta = rva - va
            if delta >= rawsize:
                return None  # cai no espaco virtual sem backing fisico
            off = raw + delta
            if off < 0 or off > file_size:
                return None
            return off
    return None


def _read_c_string(data, off, maxlen=256):
    """Le uma string ASCII terminada em NUL a partir de off. Fail-closed em bounds."""
    if off < 0 or off >= len(data):
        raise PEError("string fora do arquivo no offset %d" % off)
    end = min(len(data), off + maxlen)
    raw = data[off:end]
    nul = raw.find(b"\x00")
    if nul == -1:
        raw = raw[:maxlen]
    else:
        raw = raw[:nul]
    return raw.decode("latin-1", errors="replace")


# --------------------------------------------------------------------------- #
# Parsers de diretorios.
# --------------------------------------------------------------------------- #
def parse_sections(data, section_table_offset, num_sections, file_size):
    sections = []
    for i in range(num_sections):
        base = section_table_offset + i * SECTION_HEADER_SIZE
        if base + SECTION_HEADER_SIZE > file_size:
            raise PEError("Section Table truncada na entrada %d" % i)
        raw_name = data[base:base + 8]
        name = raw_name.split(b"\x00", 1)[0].decode("latin-1", errors="replace")
        name = _sanitize_str(name)
        virtual_size = _u32(data, base + 8)
        virtual_address = _u32(data, base + 12)
        size_of_raw_data = _u32(data, base + 16)
        pointer_to_raw_data = _u32(data, base + 20)
        characteristics = _u32(data, base + 36)
        # Entropia sobre os bytes raw fisicos (bounded ao arquivo).
        ent = 0.0
        raw_present = False
        if size_of_raw_data > 0 and pointer_to_raw_data > 0:
            start = pointer_to_raw_data
            stop = pointer_to_raw_data + size_of_raw_data
            if start < file_size:
                raw_present = True
                ent = entropy(data[start:min(stop, file_size)])
        sections.append({
            "index": i,
            "name": name,
            "virtual_size": virtual_size,
            "virtual_address": virtual_address,
            "size_of_raw_data": size_of_raw_data,
            "pointer_to_raw_data": pointer_to_raw_data,
            "characteristics": "0x%08x" % characteristics,
            "mem_read": bool(characteristics & SCN_MEM_READ),
            "mem_write": bool(characteristics & SCN_MEM_WRITE),
            "mem_execute": bool(characteristics & SCN_MEM_EXECUTE),
            "cnt_code": bool(characteristics & SCN_CNT_CODE),
            "cnt_initialized_data": bool(characteristics & SCN_CNT_INITIALIZED_DATA),
            "cnt_uninitialized_data": bool(characteristics & SCN_CNT_UNINITIALIZED_DATA),
            "discardable": bool(characteristics & SCN_MEM_DISCARDABLE),
            "writable_and_executable": bool(characteristics & SCN_MEM_WRITE)
            and bool(characteristics & SCN_MEM_EXECUTE),
            "raw_data_present": raw_present,
            "entropy": ent,
        })
    return sections


def compute_overlay(sections, file_size):
    """Overlay = bytes fisicos apos o fim da ultima secao raw. Sem conteudo."""
    end = 0
    for s in sections:
        if s["size_of_raw_data"] > 0 and s["pointer_to_raw_data"] > 0:
            e = s["pointer_to_raw_data"] + s["size_of_raw_data"]
            if e > end:
                end = e
    if end > file_size:
        end = file_size
    overlay_size = file_size - end
    return {
        "present": overlay_size > 0,
        "offset": end,
        "size": overlay_size,
        "content_emitted": False,
    }


def parse_imports(data, sections, dd, file_size, is_plus):
    """IMAGE_IMPORT_DESCRIPTOR array. Emite DLLs, APIs por nome e ordinais.
    Fail-open estrutural: uma DLL truncada interrompe a coleta com truncated=true."""
    result = {
        "present": False,
        "dll_count": 0,
        "dlls": [],
        "truncated": False,
        "note": "Import presente NAO prova que a funcionalidade e utilizada.",
    }
    if DIR_IMPORT >= len(dd):
        return result
    imp_rva, imp_size = dd[DIR_IMPORT]
    if imp_rva == 0 or imp_size == 0:
        return result
    base = rva_to_offset(sections, imp_rva, file_size)
    if base is None:
        raise PEError("Import Directory: RVA nao mapeavel")
    result["present"] = True
    thunk_width = 8 if is_plus else 4
    ordinal_mask = 0x8000000000000000 if is_plus else 0x80000000
    dlls = []
    idx = 0
    guard = 0
    while True:
        guard += 1
        if guard > MAX_IMPORT_DLLS + 1:
            result["truncated"] = True
            break
        desc = base + idx * 20
        if desc + 20 > file_size:
            raise PEError("Import descriptor truncado")
        oft = _u32(data, desc)             # OriginalFirstThunk (ILT)
        name_rva = _u32(data, desc + 12)
        ft = _u32(data, desc + 16)         # FirstThunk (IAT)
        if oft == 0 and name_rva == 0 and ft == 0:
            break  # descritor nulo terminal
        if len(dlls) >= MAX_IMPORT_DLLS:
            result["truncated"] = True
            break
        name_off = rva_to_offset(sections, name_rva, file_size) if name_rva else None
        dll_name = _sanitize_str(_read_c_string(data, name_off)) if name_off else ""
        thunk_rva = oft if oft else ft
        apis, ordinals, dll_trunc = _walk_thunks(
            data, sections, thunk_rva, thunk_width, ordinal_mask, file_size)
        apis_sorted, at = _bounded_sorted(apis, MAX_APIS_PER_DLL)
        ords_sorted = sorted(set(ordinals))
        ot = len(ords_sorted) > MAX_ORDINALS_PER_DLL
        ords_sorted = ords_sorted[:MAX_ORDINALS_PER_DLL]
        dlls.append({
            "name": dll_name,
            "api_count": len(apis_sorted),
            "ordinal_count": len(ords_sorted),
            "apis": apis_sorted,
            "ordinals": ords_sorted,
            "truncated": bool(dll_trunc or at or ot),
        })
        idx += 1
    dlls.sort(key=lambda d: (d["name"], d["api_count"]))
    result["dlls"] = dlls
    result["dll_count"] = len(dlls)
    return result


def _walk_thunks(data, sections, thunk_rva, width, ordinal_mask, file_size):
    apis, ordinals = [], []
    truncated = False
    if not thunk_rva:
        return apis, ordinals, truncated
    toff = rva_to_offset(sections, thunk_rva, file_size)
    if toff is None:
        raise PEError("thunk array: RVA nao mapeavel")
    i = 0
    while True:
        if len(apis) + len(ordinals) > MAX_APIS_PER_DLL + MAX_ORDINALS_PER_DLL:
            truncated = True
            break
        entry_off = toff + i * width
        if entry_off + width > file_size:
            raise PEError("thunk array truncado")
        val = _u64(data, entry_off) if width == 8 else _u32(data, entry_off)
        if val == 0:
            break
        if val & ordinal_mask:
            ordinals.append(val & 0xFFFF)
        else:
            name_rva = val & (0x7FFFFFFF if width == 4 else 0x7FFFFFFFFFFFFFFF)
            noff = rva_to_offset(sections, name_rva, file_size)
            if noff is None:
                raise PEError("IMAGE_IMPORT_BY_NAME: RVA nao mapeavel")
            # Hint (u16) + nome ASCII terminado em NUL.
            api = _sanitize_str(_read_c_string(data, noff + 2))
            if api:
                apis.append(api)
        i += 1
        if i > (MAX_APIS_PER_DLL + MAX_ORDINALS_PER_DLL) * 2:
            truncated = True
            break
    return apis, ordinals, truncated


def parse_exports(data, sections, dd, file_size):
    result = {
        "present": False, "dll_name": "", "ordinal_base": 0,
        "function_count": 0, "name_count": 0, "names": [], "truncated": False,
    }
    if DIR_EXPORT >= len(dd):
        return result
    exp_rva, exp_size = dd[DIR_EXPORT]
    if exp_rva == 0 or exp_size == 0:
        return result
    base = rva_to_offset(sections, exp_rva, file_size)
    if base is None:
        raise PEError("Export Directory: RVA nao mapeavel")
    if base + 40 > file_size:
        raise PEError("Export Directory truncado")
    result["present"] = True
    name_rva = _u32(data, base + 12)
    result["ordinal_base"] = _u32(data, base + 16)
    result["function_count"] = _u32(data, base + 20)
    number_of_names = _u32(data, base + 24)
    result["name_count"] = number_of_names
    addr_names_rva = _u32(data, base + 32)
    if name_rva:
        noff = rva_to_offset(sections, name_rva, file_size)
        if noff is not None:
            result["dll_name"] = _sanitize_str(_read_c_string(data, noff))
    names = []
    if addr_names_rva and number_of_names:
        aoff = rva_to_offset(sections, addr_names_rva, file_size)
        if aoff is None:
            raise PEError("Export AddressOfNames: RVA nao mapeavel")
        count = min(number_of_names, MAX_EXPORT_NAMES)
        for i in range(count):
            ptr_off = aoff + i * 4
            if ptr_off + 4 > file_size:
                raise PEError("Export AddressOfNames truncado")
            nrva = _u32(data, ptr_off)
            noff = rva_to_offset(sections, nrva, file_size)
            if noff is not None:
                nm = _sanitize_str(_read_c_string(data, noff))
                if nm:
                    names.append(nm)
        result["truncated"] = number_of_names > MAX_EXPORT_NAMES
    names_sorted, nt = _bounded_sorted(names, MAX_EXPORT_NAMES)
    result["names"] = names_sorted
    result["truncated"] = bool(result["truncated"] or nt)
    return result


def _walk_resource_dir(data, sections, dir_rva, dir_off, file_size, want_manifest):
    """Percorre o topo do diretorio de recursos: coleta type IDs e localiza o
    no do manifesto (RT_MANIFEST). Retorna (type_ids, manifest_leaf_rva|None)."""
    type_ids = []
    manifest_leaf = None
    if dir_off + 16 > file_size:
        raise PEError("Resource Directory truncado")
    n_named = _u16(data, dir_off + 12)
    n_id = _u16(data, dir_off + 14)
    total = n_named + n_id
    if total > 4096:
        raise PEError("Resource Directory: numero de entradas implausivel")
    for i in range(total):
        ent = dir_off + 16 + i * 8
        if ent + 8 > file_size:
            raise PEError("Resource entry truncada")
        name_field = _u32(data, ent)
        offset_field = _u32(data, ent + 4)
        is_named = bool(name_field & 0x80000000)
        type_id = None
        if not is_named:
            type_id = name_field & 0x7FFFFFFF
            type_ids.append(type_id)
        if want_manifest and type_id == RT_MANIFEST and (offset_field & 0x80000000):
            manifest_leaf = _find_first_leaf(
                data, sections, dir_rva, offset_field & 0x7FFFFFFF,
                dir_off, file_size, depth=0)
    return type_ids, manifest_leaf


def _find_first_leaf(data, sections, dir_rva, sub_off_rel, res_base_off, file_size, depth):
    """Desce ate a primeira folha (IMAGE_RESOURCE_DATA_ENTRY) e retorna sua RVA."""
    if depth > 6:
        return None
    node = res_base_off + sub_off_rel
    if node + 16 > file_size:
        raise PEError("Resource subdir truncado")
    n_named = _u16(data, node + 12)
    n_id = _u16(data, node + 14)
    total = n_named + n_id
    if total == 0:
        return None
    ent = node + 16
    if ent + 8 > file_size:
        raise PEError("Resource entry truncada")
    offset_field = _u32(data, ent + 4)
    if offset_field & 0x80000000:
        return _find_first_leaf(data, sections, dir_rva, offset_field & 0x7FFFFFFF,
                                res_base_off, file_size, depth + 1)
    # Folha: IMAGE_RESOURCE_DATA_ENTRY em res_base_off + offset_field.
    leaf = res_base_off + offset_field
    if leaf + 16 > file_size:
        raise PEError("Resource data entry truncada")
    data_rva = _u32(data, leaf)
    size = _u32(data, leaf + 4)
    return (data_rva, size)


REQ_LEVEL_RE = re.compile(rb'(?i)level\s*=\s*["\'](asInvoker|highestAvailable|requireAdministrator)["\']')


def parse_resources(data, sections, dd, file_size):
    result = {
        "present": False, "type_ids": [], "manifest_present": False,
        "requested_execution_level": "NOT_PRESENT", "truncated": False,
    }
    if DIR_RESOURCE >= len(dd):
        return result
    res_rva, res_size = dd[DIR_RESOURCE]
    if res_rva == 0 or res_size == 0:
        return result
    base = rva_to_offset(sections, res_rva, file_size)
    if base is None:
        raise PEError("Resource Directory: RVA nao mapeavel")
    result["present"] = True
    type_ids, manifest_leaf = _walk_resource_dir(
        data, sections, res_rva, base, file_size, want_manifest=True)
    ids_sorted, tt = _bounded_sorted(type_ids, MAX_RESOURCE_TYPES)
    result["type_ids"] = ids_sorted
    result["truncated"] = tt
    if manifest_leaf is not None:
        result["manifest_present"] = True
        data_rva, msize = manifest_leaf
        moff = rva_to_offset(sections, data_rva, file_size)
        if moff is not None and msize > 0:
            end = min(file_size, moff + min(msize, 65536))
            blob = data[moff:end]
            m = REQ_LEVEL_RE.search(blob)
            if m:
                result["requested_execution_level"] = m.group(1).decode("ascii")
            else:
                result["requested_execution_level"] = "NOT_DETERMINED"
        else:
            result["requested_execution_level"] = "NOT_DETERMINED"
    return result


def parse_tls(data, sections, dd, file_size, is_plus, image_base):
    result = {"present": False, "callback_count": 0, "truncated": False}
    if DIR_TLS >= len(dd):
        return result
    tls_rva, tls_size = dd[DIR_TLS]
    if tls_rva == 0 or tls_size == 0:
        return result
    base = rva_to_offset(sections, tls_rva, file_size)
    if base is None:
        raise PEError("TLS Directory: RVA nao mapeavel")
    result["present"] = True
    ptr_width = 8 if is_plus else 4
    # AddressOfCallBacks e o 4o ponteiro do IMAGE_TLS_DIRECTORY (VA, nao RVA).
    cb_field = base + 3 * ptr_width
    if cb_field + ptr_width > file_size:
        raise PEError("TLS Directory truncado")
    cb_va = _u64(data, cb_field) if is_plus else _u32(data, cb_field)
    if cb_va == 0:
        return result
    cb_rva = cb_va - image_base
    if cb_rva < 0:
        return result
    cb_off = rva_to_offset(sections, cb_rva, file_size)
    if cb_off is None:
        return result
    count = 0
    i = 0
    while True:
        eoff = cb_off + i * ptr_width
        if eoff + ptr_width > file_size:
            raise PEError("TLS callback array truncado")
        val = _u64(data, eoff) if is_plus else _u32(data, eoff)
        if val == 0:
            break
        count += 1
        i += 1
        if count > MAX_TLS_CALLBACKS:
            result["truncated"] = True
            break
    result["callback_count"] = count
    return result


def parse_relocations(data, sections, dd, file_size):
    result = {"present": False, "total_size": 0, "block_count": 0, "truncated": False}
    if DIR_BASERELOC >= len(dd):
        return result
    reloc_rva, reloc_size = dd[DIR_BASERELOC]
    if reloc_rva == 0 or reloc_size == 0:
        return result
    base = rva_to_offset(sections, reloc_rva, file_size)
    if base is None:
        raise PEError("Base Relocation Directory: RVA nao mapeavel")
    result["present"] = True
    result["total_size"] = reloc_size
    pos = base
    end = base + reloc_size
    if end > file_size:
        end = file_size
    blocks = 0
    while pos + 8 <= end:
        block_size = _u32(data, pos + 4)
        if block_size < 8:
            break  # bloco degenerado; para de forma fechada
        blocks += 1
        pos += block_size
        if blocks > MAX_RELOC_BLOCKS:
            result["truncated"] = True
            break
    result["block_count"] = blocks
    return result


def parse_debug(data, sections, dd, file_size):
    result = {"present": False, "entry_count": 0, "types": [],
              "has_codeview": False, "truncated": False}
    if DIR_DEBUG >= len(dd):
        return result
    dbg_rva, dbg_size = dd[DIR_DEBUG]
    if dbg_rva == 0 or dbg_size == 0:
        return result
    base = rva_to_offset(sections, dbg_rva, file_size)
    if base is None:
        raise PEError("Debug Directory: RVA nao mapeavel")
    result["present"] = True
    count = dbg_size // 28
    types = []
    shown = min(count, MAX_DEBUG_ENTRIES)
    for i in range(shown):
        ent = base + i * 28
        if ent + 28 > file_size:
            raise PEError("Debug Directory truncado")
        t = _u32(data, ent + 12)
        types.append(DEBUG_TYPE.get(t, "TYPE_%d" % t))
        if t == 2:
            result["has_codeview"] = True
    result["entry_count"] = count
    result["types"] = sorted(set(types))
    result["truncated"] = count > MAX_DEBUG_ENTRIES
    return result


def parse_certificate_table(data, dd, size_of_headers, file_size):
    """Estrutura apenas (WIN_CERTIFICATE); NUNCA emite bCertificate."""
    result = {
        "present": False, "structurally_parseable": True, "file_offset": 0,
        "size": 0, "entry_count": 0, "entries": [], "truncated": False,
        "first_field_is_file_offset_not_rva": True,
        "note": "Certificate Table apenas como estrutura; assinatura ausente NAO e malware.",
    }
    if DIR_SECURITY >= len(dd):
        return result
    cert_off, cert_size = dd[DIR_SECURITY]
    if cert_off == 0 and cert_size == 0:
        return result
    if (cert_off == 0) != (cert_size == 0):
        raise PEError("Certificate Table com par offset/tamanho parcialmente zerado")
    if cert_off < size_of_headers:
        raise PEError("Certificate Table sobreposta aos cabecalhos")
    if cert_off + cert_size > file_size:
        raise PEError("Certificate Table ultrapassa o fim do arquivo")
    if cert_off % 8 != 0:
        raise PEError("Certificate Table: inicio nao alinhado a 8 bytes")
    if cert_size < 8:
        raise PEError("Certificate Table: tamanho < 8")
    result["present"] = True
    result["file_offset"] = cert_off
    result["size"] = cert_size
    pos = cert_off
    end = cert_off + cert_size
    entries = []
    guard = 0
    while pos < end:
        guard += 1
        if guard > 4096:
            raise PEError("Certificate Table: numero de entradas implausivel")
        if end - pos < 8:
            raise PEError("Certificate Table: bytes restantes < cabecalho WIN_CERTIFICATE")
        dw_length = _u32(data, pos)
        w_revision = _u16(data, pos + 4)
        w_cert_type = _u16(data, pos + 6)
        if dw_length < 8 or pos + dw_length > end:
            raise PEError("WIN_CERTIFICATE dwLength invalido")
        aligned = (dw_length + 7) & ~7
        if pos + aligned > end:
            raise PEError("WIN_CERTIFICATE padding align8 ultrapassa a tabela")
        if len(entries) < MAX_CERT_ENTRIES:
            entries.append({
                "declared_dw_length": dw_length,
                "revision": "0x%04x" % w_revision,
                "certificate_type": "0x%04x" % w_cert_type,
                "certificate_type_name": WIN_CERT_TYPE.get(w_cert_type, "OTHER"),
            })
        else:
            result["truncated"] = True
        pos += aligned
    if pos != end:
        raise PEError("Certificate Table: soma final != tamanho declarado")
    result["entry_count"] = guard
    result["entries"] = entries
    return result


# --------------------------------------------------------------------------- #
# Indicadores textuais (strings) SANITIZADOS e LIMITADOS.
# --------------------------------------------------------------------------- #
def _extract_strings(data):
    """Extrai runs ASCII e UTF-16LE imprimiveis (>= MIN_STRING_LEN). Bounded."""
    scan = data[:MAX_STRING_SCAN_BYTES]
    out = []
    # ASCII
    cur = bytearray()
    for b in scan:
        if 0x20 <= b < 0x7F:
            cur.append(b)
        else:
            if len(cur) >= MIN_STRING_LEN:
                out.append(cur.decode("ascii", errors="ignore"))
            cur = bytearray()
    if len(cur) >= MIN_STRING_LEN:
        out.append(cur.decode("ascii", errors="ignore"))
    # UTF-16LE (heuristica: byte imprimivel seguido de 0x00)
    cur = bytearray()
    i = 0
    n = len(scan) - 1
    while i < n:
        lo = scan[i]
        hi = scan[i + 1]
        if 0x20 <= lo < 0x7F and hi == 0x00:
            cur.append(lo)
            i += 2
            continue
        if len(cur) >= MIN_STRING_LEN:
            out.append(cur.decode("ascii", errors="ignore"))
        cur = bytearray()
        i += 1
    if len(cur) >= MIN_STRING_LEN:
        out.append(cur.decode("ascii", errors="ignore"))
    return out


def classify_strings(data):
    urls, domains, paths, mutex_svc_reg, debug_pack = [], [], [], [], []
    redacted = 0
    for s in _extract_strings(data):
        s = _sanitize_str(s)
        if not s:
            continue
        if _forbidden_indicator(s):
            redacted += 1
            continue
        matched = False
        for m in URL_RE.findall(s):
            urls.append(_sanitize_str(m))
            matched = True
        for m in DOMAIN_RE.findall(s):
            domains.append(_sanitize_str(m))
            matched = True
        if MUTEX_SVC_REG_RE.search(s):
            mutex_svc_reg.append(s)
            matched = True
        if DEBUG_PACK_RE.search(s):
            debug_pack.append(s)
            matched = True
        if not matched and EMBEDDED_PATH_RE.search(s):
            # Reconfirma que nao ha drive/home (ja filtrado) antes de emitir.
            if not (DRIVE_PATH_RE.search(s) or PERSONAL_PATH_RE.search(s)):
                paths.append(s)

    def pack(values):
        vals, trunc = _bounded_sorted(values, MAX_STRINGS_PER_CATEGORY)
        return {"values": vals, "count": len(vals), "truncated": trunc}

    return {
        "note": "Indicadores textuais NAO provam comportamento; sao pistas para revisao.",
        "redacted_count": redacted,
        "urls": pack(urls),
        "domains": pack(domains),
        "embedded_paths": pack(paths),
        "mutex_service_registry": pack(mutex_svc_reg),
        "debug_packing_indicators": pack(debug_pack),
    }


def classify_imports(imports):
    buckets = {c: [] for c in CLASSIFICATION_CATEGORIES}
    for dll in imports.get("dlls", []):
        for api in dll.get("apis", []):
            cat = IMPORT_CLASSIFICATION.get(api.lower())
            if cat:
                buckets[cat].append(api)
    out = {"note": "Classificacao por associacao primaria; presenca de import NAO e "
                    "veredito; API desconhecida NAO e classificada."}
    for c in CLASSIFICATION_CATEGORIES:
        vals, trunc = _bounded_sorted(buckets[c], MAX_STRINGS_PER_CATEGORY)
        out[c] = {"values": vals, "count": len(vals), "truncated": trunc}
    return out


def compute_heuristics(sections, overlay, imports):
    """Indicadores ESTRUTURAIS de empacotamento (heuristicas, NAO veredito)."""
    indicators = []
    for s in sections:
        if s["writable_and_executable"]:
            indicators.append({
                "indicator": "WRITABLE_AND_EXECUTABLE_SECTION",
                "section": s["name"], "detail": "secao gravavel e executavel"})
        if s["raw_data_present"] and s["entropy"] >= 7.2 and s["size_of_raw_data"] >= 512:
            indicators.append({
                "indicator": "HIGH_ENTROPY_SECTION",
                "section": s["name"],
                "detail": "entropia %.6f (alta; NAO prova empacotamento)" % s["entropy"]})
        if s["virtual_size"] > 0 and s["size_of_raw_data"] == 0 and s["mem_execute"]:
            indicators.append({
                "indicator": "VIRTUAL_ONLY_EXECUTABLE_SECTION",
                "section": s["name"], "detail": "secao executavel sem dados raw"})
    if overlay["present"] and overlay["size"] >= 4096:
        indicators.append({
            "indicator": "OVERLAY_PRESENT",
            "section": "", "detail": "overlay de %d bytes" % overlay["size"]})
    if imports["present"] and imports["dll_count"] <= 2:
        indicators.append({
            "indicator": "FEW_IMPORTED_DLLS",
            "section": "", "detail": "%d DLL(s) importada(s)" % imports["dll_count"]})
    return {
        "note": "Heuristicas estruturais; entropia alta isolada NAO prova empacotamento "
                "nem malware; nenhuma conclusao depende de uma unica metrica.",
        "indicators": indicators,
        "indicator_count": len(indicators),
    }


# --------------------------------------------------------------------------- #
# Cabecalhos (parse minimo e fechado, dedicado ao GATE 4).
# --------------------------------------------------------------------------- #
def parse_headers(data):
    n = len(data)
    if n < 0x40:
        raise PEError("arquivo menor que o cabecalho DOS minimo (64 bytes)")
    if data[0:2] != b"MZ":
        raise PEError("assinatura MZ ausente")
    e_lfanew = _u32(data, 0x3C)
    if e_lfanew < 0x40 or e_lfanew + 4 > n:
        raise PEError("e_lfanew (%d) fora da regiao valida" % e_lfanew)
    if data[e_lfanew:e_lfanew + 4] != b"PE\x00\x00":
        raise PEError("assinatura PE\\0\\0 ausente")
    coff = e_lfanew + 4
    if coff + COFF_SIZE > n:
        raise PEError("COFF File Header truncado")
    machine = _u16(data, coff + COFF_MACHINE)
    num_sections = _u16(data, coff + COFF_NUMBER_OF_SECTIONS)
    timedatestamp = _u32(data, coff + COFF_TIMEDATESTAMP)
    size_opt = _u16(data, coff + COFF_SIZE_OF_OPTIONAL_HEADER)
    characteristics = _u16(data, coff + COFF_CHARACTERISTICS)
    if not (characteristics & IMAGE_FILE_EXECUTABLE_IMAGE):
        raise PEError("IMAGE_FILE_EXECUTABLE_IMAGE ausente")
    if num_sections < 1:
        raise PEError("NumberOfSections < 1")
    if num_sections > MAX_IMAGE_SECTIONS:
        raise PEError("NumberOfSections (%d) > %d" % (num_sections, MAX_IMAGE_SECTIONS))
    opt = coff + COFF_SIZE
    if size_opt < 2 or opt + size_opt > n:
        raise PEError("Optional Header truncado ou invalido")
    magic = _u16(data, opt + OPT_MAGIC)
    if magic == MAGIC_PE32:
        is_plus = False
        num_rva_off, datadir_off = OPT_NUM_RVA_PE32, OPT_DATADIR_PE32
        image_base = _u32(data, opt + OPT_IMAGE_BASE_PE32)
    elif magic == MAGIC_PE32_PLUS:
        is_plus = True
        num_rva_off, datadir_off = OPT_NUM_RVA_PE32_PLUS, OPT_DATADIR_PE32_PLUS
        image_base = _u64(data, opt + OPT_IMAGE_BASE_PE32_PLUS)
    else:
        raise PEError("magic desconhecido no Optional Header: 0x%04x" % magic)

    def opt_field(off, width, name):
        if off + width > size_opt or opt + off + width > n:
            raise PEError("%s fora do Optional Header/arquivo" % name)

    opt_field(OPT_SUBSYSTEM, 2, "Subsystem")
    subsystem = _u16(data, opt + OPT_SUBSYSTEM)
    opt_field(OPT_SECTION_ALIGNMENT, 4, "SectionAlignment")
    section_alignment = _u32(data, opt + OPT_SECTION_ALIGNMENT)
    opt_field(OPT_FILE_ALIGNMENT, 4, "FileAlignment")
    file_alignment = _u32(data, opt + OPT_FILE_ALIGNMENT)
    opt_field(OPT_SIZE_OF_HEADERS, 4, "SizeOfHeaders")
    size_of_headers = _u32(data, opt + OPT_SIZE_OF_HEADERS)
    opt_field(OPT_SIZE_OF_IMAGE, 4, "SizeOfImage")
    size_of_image = _u32(data, opt + OPT_SIZE_OF_IMAGE)
    opt_field(num_rva_off, 4, "NumberOfRvaAndSizes")
    num_rva = _u32(data, opt + num_rva_off)
    if num_rva > 65535:
        raise PEError("NumberOfRvaAndSizes implausivelmente grande")
    dd_start = opt + datadir_off
    dd_bytes = num_rva * DATADIR_ENTRY_SIZE
    if datadir_off + dd_bytes > size_opt or dd_start + dd_bytes > n:
        raise PEError("Data Directory nao cabe no Optional Header/arquivo")
    dd = []
    for i in range(num_rva):
        e = dd_start + i * DATADIR_ENTRY_SIZE
        dd.append((_u32(data, e), _u32(data, e + 4)))

    section_table_offset = opt + size_opt
    section_table_end = section_table_offset + num_sections * SECTION_HEADER_SIZE
    if section_table_end > n:
        raise PEError("Section Table ultrapassa o fim do arquivo (truncada)")
    if size_of_headers < section_table_end or size_of_headers > n:
        raise PEError("SizeOfHeaders inconsistente com a Section Table/arquivo")

    headers = {
        "file_size": n,
        "e_lfanew": e_lfanew,
        "machine_value": "0x%04x" % machine,
        "machine": MACHINE.get(machine, "OTHER"),
        "number_of_sections": num_sections,
        "timedatestamp_raw": timedatestamp,
        "timedatestamp_is_trusted": False,
        "size_of_optional_header": size_opt,
        "characteristics": "0x%04x" % characteristics,
        "optional_header_magic": "0x%04x" % magic,
        "pe_format": "PE32+" if is_plus else "PE32",
        "image_base": "0x%016x" % image_base if is_plus else "0x%08x" % image_base,
        "subsystem_value": subsystem,
        "subsystem": SUBSYSTEM.get(subsystem, "OTHER"),
        "section_alignment": section_alignment,
        "file_alignment": file_alignment,
        "size_of_headers": size_of_headers,
        "size_of_image": size_of_image,
        "number_of_rva_and_sizes": num_rva,
        "section_table_offset": section_table_offset,
        "executable_image_flag_present": True,
    }
    ctx = {
        "is_plus": is_plus, "image_base": image_base, "dd": dd,
        "size_of_headers": size_of_headers, "num_sections": num_sections,
        "section_table_offset": section_table_offset,
    }
    return headers, ctx


def inspect(data):
    """Recebe os bytes do arquivo e retorna o dict de inventario. Levanta PEError."""
    headers, ctx = parse_headers(data)
    file_size = headers["file_size"]
    sections = parse_sections(
        data, ctx["section_table_offset"], ctx["num_sections"], file_size)
    overlay = compute_overlay(sections, file_size)
    imports = parse_imports(data, sections, ctx["dd"], file_size, ctx["is_plus"])
    exports = parse_exports(data, sections, ctx["dd"], file_size)
    resources = parse_resources(data, sections, ctx["dd"], file_size)
    tls = parse_tls(data, sections, ctx["dd"], file_size, ctx["is_plus"], ctx["image_base"])
    relocations = parse_relocations(data, sections, ctx["dd"], file_size)
    debug = parse_debug(data, sections, ctx["dd"], file_size)
    certificate_table = parse_certificate_table(
        data, ctx["dd"], ctx["size_of_headers"], file_size)
    dependencies, dep_trunc = _bounded_sorted(
        [d["name"] for d in imports["dlls"] if d["name"]], MAX_IMPORT_DLLS)

    total_entropy = entropy(data[:file_size])

    structural_facts = {
        "headers": headers,
        "sections": sections,
        "section_count": len(sections),
        "overlay": overlay,
        "total_entropy": total_entropy,
        "imports": imports,
        "exports": exports,
        "resources": resources,
        "tls_callbacks": tls,
        "relocations": relocations,
        "debug_directory": debug,
        "certificate_table": certificate_table,
        "declared_dependencies": {
            "dll_names": dependencies,
            "count": len(dependencies),
            "truncated": dep_trunc,
        },
    }
    result = {
        "record_type": "warp-pe-static-inventory",
        "analysis_metadata": {
            "static_only": True,
            "file_read_for_static_inspection": True,
            "launched": False,
            "executed": False,
            "loaded_as_executable": False,
            "emulated": False,
            "unpacked_dynamically": False,
            "network_access": False,
            "pe_format": headers["pe_format"],
        },
        "structural_facts": structural_facts,
        "heuristics": compute_heuristics(sections, overlay, imports),
        "import_classification": classify_imports(imports),
        "string_indicators": classify_strings(data),
        "limitations": [
            "Uma API importada NAO prova que a funcionalidade e utilizada.",
            "Uma string NAO prova comportamento.",
            "Entropia alta isoladamente NAO prova empacotamento nem malware.",
            "Ausencia de indicador NAO prova seguranca.",
            "Achados estaticos exigem interpretacao contextual.",
            "Nenhuma conclusao deve depender de uma unica metrica.",
            "O inventario NAO executa, carrega, emula nem descompacta dinamicamente o PE.",
            "O GATE 4 NAO autoriza o GATE 5 nem uso no cliente ou distribuicao.",
        ],
    }
    return result


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("uso: inspect-warp-pe-static.py <caminho-local>\n")
        return 2
    path = argv[1]
    if not os.path.isfile(path):
        sys.stderr.write("arquivo inexistente: %s\n" % path)
        return 2
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        sys.stderr.write("falha ao ler arquivo: %s\n" % exc)
        return 2
    try:
        result = inspect(data)
    except PEError as exc:
        sys.stderr.write("PE invalido/inconsistente: %s\n" % exc)
        return 2
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
