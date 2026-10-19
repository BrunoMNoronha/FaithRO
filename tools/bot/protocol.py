"""
FaithRO FaithBot - protocolo do rAthena para PACKETVER 20260219 (pre-re, sem ofuscacao, sem shuffle).

Fonte de verdade: src/common/packets.hpp, src/map/packets.hpp, src/map/packets_struct.hpp e
src/map/clif_packetdb.hpp do rAthena compilado na VPS. Os tamanhos ficam em packet_lengths.json
(gerado por gen_packet_lengths.py) e os corpos pre-processados em structs.txt.

Convencoes: little-endian; strings C terminadas em zero, preenchidas com zeros; charset cp1252
(o servidor converte os textos pt-BR para Windows-1252, ver docs/traducao.md).
"""
from __future__ import annotations

import json
import os
import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

PACKETVER = 20260219
CLIENT_VERSION = 55          # clientinfo.xml <version>55</version>
CLIENT_TYPE = 0
ENCODING = "cp1252"
NAME_LENGTH = 24
MAP_NAME_LENGTH_EXT = 16

# ---------------------------------------------------------------- IDs: cliente -> servidor
CA_LOGIN = 0x0064
CH_ENTER = 0x0065
CH_SELECT_CHAR = 0x0066
CH_MAKE_CHAR = 0x0A39
CH_CHARLIST_REQ = 0x09A1
CZ_ENTER = 0x0436                 # 23 bytes (PACKETVER_RE_NUM >= 20211103 || MAIN >= 20220330)
CZ_NOTIFY_ACTORINIT = 0x007D      # LoadEndAck
CZ_REQUEST_TIME = 0x0360          # TickSend
CZ_REQUEST_MOVE = 0x035F          # WalkToXY
CZ_CHANGE_DIRECTION = 0x0361
CZ_ITEM_PICKUP = 0x0362
CZ_REQNAME = 0x0368               # GetCharNameRequest
CZ_REQUEST_ACT = 0x0437           # ActionRequest
CZ_REQUEST_CHAT = 0x00F3          # GlobalMessage (ultima definicao em clif_packetdb.hpp; 0x8c e outro pacote aqui)
CZ_CONTACTNPC = 0x0090
CZ_REQ_NEXT_SCRIPT = 0x00B9
CZ_CHOOSE_MENU = 0x00B8
CZ_CLOSE_DIALOG = 0x0146
CZ_INPUT_EDITDLG = 0x0143
CZ_INPUT_EDITDLGSTR = 0x01D5
CZ_ACK_SELECT_DEALTYPE = 0x00C5   # NpcBuySellSelected
CZ_PC_PURCHASE_ITEMLIST = 0x00C8
CZ_PC_BUY_CASH_POINT_ITEM = 0x0288
CZ_RESTART = 0x00B2
CZ_REQ_DISCONNECT = 0x018A
CZ_WHISPER = 0x0096               # WisMessage: len u16, destinatario 24s, texto

# ---------------------------------------------------------------- IDs: servidor -> cliente
AC_ACCEPT_LOGIN = 0x0AC4
AC_REFUSE_LOGIN = 0x083E
AC_REFUSE_LOGIN_OLD = 0x006A
SC_NOTIFY_BAN = 0x0081
HC_ACCEPT_ENTER2 = 0x082D
HC_ACCEPT_ENTER = 0x006B
HC_REFUSE_ENTER = 0x006C
HC_CHARLIST_NOTIFY = 0x09A0
HC_BLOCK_CHARACTER = 0x020D
HC_SECOND_PASSWD_LOGIN = 0x08B9
HC_ACCEPT_MAKECHAR = 0x0B6F
HC_REFUSE_MAKECHAR = 0x006E
HC_NOTIFY_ZONESVR = 0x0AC5
ZC_AID = 0x0283
ZC_ACCEPT_ENTER = 0x02EB
ZC_REFUSE_ENTER = 0x0074
ZC_NOTIFY_TIME = 0x007F
ZC_NOTIFY_VANISH = 0x0080
ZC_NOTIFY_PLAYERMOVE = 0x0087
ZC_NPCACK_MAPMOVE = 0x0091
ZC_ACK_REQNAMEALL = 0x0A30
ZC_ACK_REQNAMEALL_NPC = 0x0ADF
ZC_NOTIFY_CHAT = 0x008D
ZC_NOTIFY_PLAYERCHAT = 0x008E
ZC_BROADCAST = 0x009A
ZC_BROADCAST2 = 0x01C3
ZC_NOTIFY_ACT = 0x08C8
ZC_PAR_CHANGE = 0x00B0
ZC_LONGPAR_CHANGE = 0x00B1
ZC_LONGLONGPAR_CHANGE = 0x0ACB
ZC_SAY_DIALOG = 0x00B4
ZC_WAIT_DIALOG = 0x00B5
ZC_CLOSE_DIALOG = 0x00B6
ZC_MENU_LIST = 0x00B7
ZC_OPEN_EDITDLG = 0x0142
ZC_OPEN_EDITDLGSTR = 0x01D4
ZC_SELECT_DEALTYPE = 0x00C4
ZC_PC_PURCHASE_ITEMLIST = 0x0B77
ZC_PC_PURCHASE_RESULT = 0x00CA
ZC_PC_CASH_POINT_ITEMLIST = 0x0287
ZC_NOTIFY_STANDENTRY = 0x09FF    # idle_unitType
ZC_NOTIFY_NEWENTRY = 0x09FE      # spawn_unitType
ZC_NOTIFY_MOVEENTRY = 0x09FD     # unit_walkingType
ZC_ITEM_ENTRY = 0x009D
ZC_ITEM_FALL_ENTRY = 0x0ADD   # dropflooritemType (PACKETVER >= 20180418)
ZC_ITEM_DISAPPEAR = 0x00A1
ZC_ITEM_PICKUP_ACK = 0x0B41
ZC_MSG = 0x0291
ZC_MSG_COLOR = 0x09CD
ZC_ACK_REQ_DISCONNECT = 0x018B
ZC_WHISPER = 0x09DE               # len u16, senderGID u32, sender 24s, isAdmin u8, texto
ZC_ACK_WHISPER = 0x09DF           # result u8 (0 ok, 1 offline, 2 ignorado, 3 ignora todos), CID u32
WHISPER_RESULTS = {0: "entregue", 1: "destinatario offline", 2: "destinatario ignora voce", 3: "destinatario ignora todos"}

# Variaveis de ZC_PAR_CHANGE / ZC_LONGPAR_CHANGE (enum _sp em src/map/status.hpp)
SP_SPEED, SP_BASEEXP, SP_JOBEXP, SP_KARMA, SP_MANNER, SP_HP, SP_MAXHP, SP_SP, SP_MAXSP = 0, 1, 2, 3, 4, 5, 6, 7, 8
SP_STATUSPOINT, SP_BASELEVEL, SP_SKILLPOINT, SP_JOBLEVEL, SP_ZENY = 9, 11, 12, 55, 20
SP_WEIGHT, SP_MAXWEIGHT = 24, 25
SP_NAMES = {0: "speed", 1: "base_exp", 2: "job_exp", 5: "hp", 6: "max_hp", 7: "sp", 8: "max_sp",
            9: "status_points", 11: "base_level", 12: "skill_points", 20: "zeny", 24: "weight",
            25: "max_weight", 55: "job_level"}

# Tipos de objeto em packet_idle_unit.objecttype (enum e_unit_type / BL_*)
UT_PC, UT_NPC, UT_ITEM, UT_SKILL, UT_UNKNOWN, UT_MOB, UT_EVENT, UT_PET, UT_HOM, UT_MERC, UT_ELEM, UT_NPC_SHOP = range(12)
# clif_bl_type: NPC com sprite de classe de jogador (ex. 4020) chega como 0 (pc); os demais como 6 (event)
UT_NAMES = {0: "pc", 1: "npc", 2: "item", 3: "skill", 4: "?", 5: "mob", 6: "npc", 7: "pet",
            8: "hom", 9: "merc", 10: "elem", 11: "npc_shop", 12: "npc_abr", 13: "npc_bionic"}
NPC_TYPES = (UT_NPC, UT_EVENT, UT_NPC_SHOP, 12, 13)


def display_name(name: str) -> str:
    """'Warpra#32' -> 'Warpra' (a parte apos # e o nome oculto do script)."""
    return name.split("#", 1)[0]

REFUSE_REASONS = {
    0: "conta inexistente", 1: "senha incorreta", 2: "conta expirada", 3: "rejeitado pelo servidor",
    4: "conta bloqueada", 5: "versao do cliente incorreta", 6: "banida temporariamente", 99: "conta apagada",
}
MAP_REFUSE_REASONS = {0: "servidor fechado", 1: "servidor fechado", 2: "ja conectado", 3: "rejeitado pelo servidor",
                      8: "conexao anterior ainda reconhecida; tente de novo em alguns segundos"}

# ---------------------------------------------------------------- tabela de tamanhos
_HERE = os.path.dirname(os.path.abspath(__file__))


def load_lengths(path: str = os.path.join(_HERE, "packet_lengths.json")) -> Tuple[Dict[int, int], Dict[int, int], Dict[int, str]]:
    """-> (map_lengths, charlogin_lengths, names). -1 = tamanho nos bytes 2..3."""
    with open(path) as fh:
        d = json.load(fh)
    if d.get("packetver") != PACKETVER:
        raise RuntimeError(f"packet_lengths.json e do PACKETVER {d.get('packetver')}, protocol.py espera {PACKETVER}")
    m = {int(k): v for k, v in d["map"].items()}
    c = {int(k): v for k, v in d["charlogin"].items()}
    # Pacotes enviados pelo char-server com WFIFO fixo (fora dos structs): tamanhos de char_clif.cpp.
    c.setdefault(HC_ACCEPT_ENTER2, 29)
    c.setdefault(HC_CHARLIST_NOTIFY, 6)
    c.setdefault(HC_SECOND_PASSWD_LOGIN, 12)
    c.setdefault(HC_ACCEPT_ENTER, -1)
    c.setdefault(HC_BLOCK_CHARACTER, -1)
    c.setdefault(HC_NOTIFY_ZONESVR, 156)
    c.setdefault(HC_REFUSE_ENTER, 3)
    c.setdefault(HC_ACCEPT_MAKECHAR, 177)
    c.setdefault(HC_REFUSE_MAKECHAR, 3)
    c.setdefault(SC_NOTIFY_BAN, 3)
    c.setdefault(AC_ACCEPT_LOGIN, -1)
    c.setdefault(AC_REFUSE_LOGIN, 26)
    c.setdefault(AC_REFUSE_LOGIN_OLD, 23)
    m.setdefault(ZC_AID, 6)
    m.setdefault(ZC_ITEM_FALL_ENTRY, 24)
    names = {int(k): v for k, v in d.get("names", {}).items()}
    return m, c, names


# ---------------------------------------------------------------- utilidades
def cstr(raw: bytes) -> str:
    return raw.split(b"\0", 1)[0].decode(ENCODING, errors="replace")


def fixed(text: str, size: int) -> bytes:
    b = text.encode(ENCODING, errors="replace")[: size - 1]
    return b + b"\0" * (size - len(b))


def ip_str(ip_le: int) -> str:
    """IP como o rAthena envia (uint32 na ordem de rede, lido como little-endian)."""
    b = struct.pack("<I", ip_le)
    return ".".join(str(x) for x in b)


def encode_pos(x: int, y: int, direction: int = 0) -> bytes:
    """WBUFPOS: 3 bytes."""
    return bytes([(x >> 2) & 0xFF, ((x << 6) | ((y >> 4) & 0x3F)) & 0xFF, ((y << 4) | (direction & 0xF)) & 0xFF])


def decode_pos(b: bytes) -> Tuple[int, int, int]:
    """RBUFPOS -> (x, y, dir)."""
    x = ((b[0] << 2) | (b[1] >> 6)) & 0x3FF
    y = (((b[1] & 0x3F) << 4) | (b[2] >> 4)) & 0x3FF
    return x, y, b[2] & 0xF


def decode_pos2(b: bytes) -> Tuple[int, int, int, int, int, int]:
    """RBUFPOS2 (MoveData, 6 bytes) -> (x0, y0, x1, y1, sx0, sy0)."""
    x0 = ((b[0] << 2) | (b[1] >> 6)) & 0x3FF
    y0 = (((b[1] & 0x3F) << 4) | (b[2] >> 4)) & 0x3FF
    x1 = (((b[2] & 0x0F) << 6) | (b[3] >> 2)) & 0x3FF
    y1 = (((b[3] & 0x03) << 8) | b[4]) & 0x3FF
    return x0, y0, x1, y1, b[5] >> 4, b[5] & 0xF


# ---------------------------------------------------------------- login
def pack_ca_login(userid: str, password: str) -> bytes:
    return struct.pack("<HI24s24sB", CA_LOGIN, CLIENT_VERSION, fixed(userid, 24), fixed(password, 24), CLIENT_TYPE)


@dataclass
class CharServer:
    ip: str
    port: int
    name: str
    users: int
    type: int


@dataclass
class LoginOk:
    login_id1: int
    account_id: int
    login_id2: int
    sex: int
    token: bytes
    servers: List[CharServer] = field(default_factory=list)


AC_ACCEPT_HEAD = "<HHIIII26sB17s"       # 2+2+4+4+4+4+26+1+17 = 64
AC_ACCEPT_SUB = "<IH20sHHH128s"         # 160


def unpack_ac_accept_login(p: bytes) -> LoginOk:
    _, length, id1, aid, id2, _lastip, _lastlogin, sex, token = struct.unpack_from(AC_ACCEPT_HEAD, p, 0)
    head = struct.calcsize(AC_ACCEPT_HEAD)
    sub = struct.calcsize(AC_ACCEPT_SUB)
    servers = []
    for off in range(head, min(length, len(p)) - sub + 1, sub):
        ip, port, name, users, typ, _new, _unk = struct.unpack_from(AC_ACCEPT_SUB, p, off)
        servers.append(CharServer(ip_str(ip), port, cstr(name), users, typ))
    return LoginOk(id1, aid, id2, sex, token, servers)


def unpack_ac_refuse(p: bytes) -> Tuple[int, str]:
    pid = struct.unpack_from("<H", p)[0]
    code = struct.unpack_from("<I" if pid == AC_REFUSE_LOGIN else "<B", p, 2)[0]
    return code, REFUSE_REASONS.get(code, "outro motivo")


# ---------------------------------------------------------------- char-server
def pack_ch_enter(login: LoginOk) -> bytes:
    return struct.pack("<HIIIHB", CH_ENTER, login.account_id, login.login_id1, login.login_id2, 0, login.sex)


def pack_ch_select_char(slot: int) -> bytes:
    return struct.pack("<HB", CH_SELECT_CHAR, slot)


def pack_ch_make_char(name: str, slot: int, sex: int, hair_color: int = 1, hair_style: int = 1, job: int = 0) -> bytes:
    return struct.pack("<H24sBHHIB", CH_MAKE_CHAR, fixed(name, 24), slot, hair_color, hair_style, job, sex)


# CHARACTER_INFO (175 bytes) - ver structs.txt
CHARACTER_INFO = ("<I q i q iiiiii h qqqq hhhhhhhhhhhhh 24s BBBBBB BB h 16s iiii B").replace(" ", "")
CHARACTER_INFO_SIZE = struct.calcsize(CHARACTER_INFO)   # 175
CHARACTER_INFO_FIELDS = (
    "char_id exp zeny job_exp job_level body_state health_state effect_state karma manner status_points "
    "hp max_hp sp max_sp speed job hair body weapon base_level skill_points accessory shield accessory2 "
    "accessory3 hair_color clothes_color name str agi vit int dex luk slot hair_color2 rename map "
    "delete_date robe slot_changes name_changes sex").split()


@dataclass
class CharInfo:
    char_id: int
    name: str
    slot: int
    job: int
    base_level: int
    job_level: int
    zeny: int
    hp: int
    max_hp: int
    sp: int
    max_sp: int
    map: str
    sex: int
    raw: dict = field(default_factory=dict, repr=False)


def unpack_character_info(p: bytes, off: int) -> CharInfo:
    vals = struct.unpack_from(CHARACTER_INFO, p, off)
    d = dict(zip(CHARACTER_INFO_FIELDS, vals))
    return CharInfo(d["char_id"], cstr(d["name"]), d["slot"], d["job"], d["base_level"], d["job_level"],
                    d["zeny"], d["hp"], d["max_hp"], d["sp"], d["max_sp"], cstr(d["map"]), d["sex"], d)


HC_ACCEPT_ENTER_HEAD = "<HHBBB20s"   # 27 bytes


def unpack_hc_accept_enter(p: bytes) -> Tuple[int, List[CharInfo]]:
    """-> (total_slots, chars)."""
    _, length, total, _ps, _pe, _ext = struct.unpack_from(HC_ACCEPT_ENTER_HEAD, p, 0)
    head = struct.calcsize(HC_ACCEPT_ENTER_HEAD)
    chars = []
    body = min(length, len(p)) - head
    if body % CHARACTER_INFO_SIZE:
        raise ValueError(f"HC_ACCEPT_ENTER: corpo de {body} bytes nao e multiplo de {CHARACTER_INFO_SIZE}")
    for i in range(body // CHARACTER_INFO_SIZE):
        chars.append(unpack_character_info(p, head + i * CHARACTER_INFO_SIZE))
    return total, chars


@dataclass
class ZoneServer:
    char_id: int
    map: str
    ip: str
    port: int


def unpack_hc_notify_zonesvr(p: bytes) -> ZoneServer:
    _, cid, mapname, ip, port, _domain = struct.unpack_from("<HI16sIH128s", p, 0)
    return ZoneServer(cid, cstr(mapname), ip_str(ip), port)


# ---------------------------------------------------------------- map-server: envio
def pack_cz_enter(account_id: int, char_id: int, login_id1: int, client_tick: int, sex: int) -> bytes:
    # parseable_packet(0x0436, 23, clif_parse_WantToConnection, 2, 6, 10, 14, 22)
    return struct.pack("<HIIIIIB", CZ_ENTER, account_id, char_id, login_id1, client_tick, 0, sex)


def pack_load_end_ack() -> bytes:
    return struct.pack("<H", CZ_NOTIFY_ACTORINIT)


def pack_tick(client_tick: int) -> bytes:
    return struct.pack("<HI", CZ_REQUEST_TIME, client_tick & 0xFFFFFFFF)


def pack_walk(x: int, y: int) -> bytes:
    return struct.pack("<H", CZ_REQUEST_MOVE) + encode_pos(x, y, 0)


def pack_action(target_aid: int, action: int) -> bytes:
    """action: 0 ataque unico, 7 ataque continuo, 2 sentar, 3 levantar."""
    return struct.pack("<HIB", CZ_REQUEST_ACT, target_aid, action)


def pack_reqname(aid: int) -> bytes:
    return struct.pack("<HI", CZ_REQNAME, aid)


def pack_pickup(item_aid: int) -> bytes:
    return struct.pack("<HI", CZ_ITEM_PICKUP, item_aid)


def pack_chat(char_name: str, text: str) -> bytes:
    msg = fixed(f"{char_name} : {text}", 256)
    msg = msg[: msg.index(b"\0") + 1]
    return struct.pack("<HH", CZ_REQUEST_CHAT, 4 + len(msg)) + msg


def pack_whisper(target: str, text: str) -> bytes:
    """Sussurro para um jogador ou para um NPC ("NPC:Nome", parametros separados por #)."""
    msg = text.encode(ENCODING, errors="replace")[:250] + b"\0"
    return struct.pack("<HH24s", CZ_WHISPER, 28 + len(msg), fixed(target, 24)) + msg


def unpack_whisper(p: bytes) -> Tuple[int, str, str]:
    """-> (sender_gid, sender, texto)."""
    _, length, gid, sender, _admin = struct.unpack_from("<HHI24sB", p)
    return gid, cstr(sender), cstr(p[33:length])


def unpack_whisper_ack(p: bytes) -> Tuple[int, int]:
    _, result, cid = struct.unpack_from("<HBI", p)
    return result, cid


def pack_npc_click(npc_aid: int) -> bytes:
    return struct.pack("<HIB", CZ_CONTACTNPC, npc_aid, 1)


def pack_npc_next(npc_aid: int) -> bytes:
    return struct.pack("<HI", CZ_REQ_NEXT_SCRIPT, npc_aid)


def pack_npc_menu(npc_aid: int, choice: int) -> bytes:
    """choice: 1..N, 255 = cancelar."""
    return struct.pack("<HIB", CZ_CHOOSE_MENU, npc_aid, choice)


def pack_npc_close(npc_aid: int) -> bytes:
    return struct.pack("<HI", CZ_CLOSE_DIALOG, npc_aid)


def pack_npc_input_num(npc_aid: int, value: int) -> bytes:
    return struct.pack("<HIi", CZ_INPUT_EDITDLG, npc_aid, value)


def pack_npc_input_str(npc_aid: int, text: str) -> bytes:
    b = text.encode(ENCODING, errors="replace") + b"\0"
    return struct.pack("<HHI", CZ_INPUT_EDITDLGSTR, 8 + len(b), npc_aid) + b


def pack_buysell_select(npc_aid: int, buy: bool = True) -> bytes:
    return struct.pack("<HIB", CZ_ACK_SELECT_DEALTYPE, npc_aid, 0 if buy else 1)


def pack_buy(items: List[Tuple[int, int]]) -> bytes:
    """items: [(item_id, amount)]."""
    body = b"".join(struct.pack("<HI", amount, item_id) for item_id, amount in items)
    return struct.pack("<HH", CZ_PC_PURCHASE_ITEMLIST, 4 + len(body)) + body


def pack_cash_buy(items: List[Tuple[int, int]], kafra_points: int = 0) -> bytes:
    body = b"".join(struct.pack("<HI", amount, item_id) for item_id, amount in items)
    return struct.pack("<HHIH", CZ_PC_BUY_CASH_POINT_ITEM, 10 + len(body), kafra_points, len(items)) + body


def pack_quit() -> bytes:
    return struct.pack("<HH", CZ_REQ_DISCONNECT, 0)


def pack_restart(to_char_select: bool = True) -> bytes:
    return struct.pack("<HB", CZ_RESTART, 1 if to_char_select else 0)


# ---------------------------------------------------------------- map-server: recepcao
@dataclass
class Unit:
    aid: int
    type: int
    job: int
    x: int
    y: int
    name: str = ""
    hp: int = 0
    max_hp: int = 0
    level: int = 0
    gid: int = 0
    is_boss: bool = False

    @property
    def kind(self) -> str:
        return UT_NAMES.get(self.type, str(self.type))


# packet_idle_unit / packet_spawn_unit ate 'sex' (igual nos dois), depois diverge.
_UNIT_HEAD = "<HHBIIhhhihHIIHHHhhhHIhhiBB"   # ate sex
_UNIT_HEAD_SIZE = struct.calcsize(_UNIT_HEAD)


def unpack_unit(pid: int, p: bytes) -> Unit:
    vals = struct.unpack_from(_UNIT_HEAD, p, 0)
    _, length, objtype, aid, gid, _speed, _bs, _hs, _es, job = vals[:10]
    off = _UNIT_HEAD_SIZE
    if pid == ZC_NOTIFY_MOVEENTRY:
        # packet_unit_walking: 'accessory' e seguido de moveStartTime (u32) ANTES de accessory2
        vals = struct.unpack_from("<HHBIIhhhihHIIHIHHhhhHIhhiBB", p, 0)
        _, length, objtype, aid, gid, _speed, _bs, _hs, _es, job = vals[:10]
        off = struct.calcsize("<HHBIIhhhihHIIHIHHhhhHIhhiBB")
        x0, y0, x1, y1, _, _ = decode_pos2(p[off:off + 6])
        off += 6
        x, y = x1, y1
        _xs, _ys, level, _font, max_hp, hp, is_boss, _body = struct.unpack_from("<BBhhiiBH", p, off)
        off += struct.calcsize("<BBhhiiBH")
    else:
        x, y, _d = decode_pos(p[off:off + 3])
        off += 3
        if pid == ZC_NOTIFY_STANDENTRY:
            _xs, _ys, _state, level, _font, max_hp, hp, is_boss, _body = struct.unpack_from("<BBBhhiiBH", p, off)
            off += struct.calcsize("<BBBhhiiBH")
        else:  # NEWENTRY
            _xs, _ys, level, _font, max_hp, hp, is_boss, _body = struct.unpack_from("<BBhhiiBh", p, off)
            off += struct.calcsize("<BBhhiiBh")
    name = cstr(p[off:off + NAME_LENGTH]) if len(p) >= off + 1 else ""
    return Unit(aid, objtype, job, x, y, name, hp, max_hp, level, gid, bool(is_boss))


def unpack_vanish(p: bytes) -> Tuple[int, int]:
    """-> (aid, type) type: 0 saiu da visao, 1 morreu, 2 deslogou, 3 teleportou."""
    _, aid, typ = struct.unpack_from("<HIB", p)
    return aid, typ


def unpack_accept_enter(p: bytes) -> Tuple[int, int, int, int]:
    """-> (start_time, x, y, dir)."""
    _, start, pos, _xs, _ys, _font = struct.unpack_from("<HI3sBBH", p)
    x, y, d = decode_pos(pos)
    return start, x, y, d


def unpack_playermove(p: bytes) -> Tuple[int, int, int, int]:
    _, _t, move = struct.unpack_from("<HI6s", p)
    x0, y0, x1, y1, _, _ = decode_pos2(move)
    return x0, y0, x1, y1


def unpack_mapmove(p: bytes) -> Tuple[str, int, int]:
    _, mapname, x, y = struct.unpack_from("<H16sHH", p)
    return cstr(mapname), x, y


def unpack_par_change(p: bytes) -> Tuple[int, int]:
    _, var, val = struct.unpack_from("<HHi", p)
    return var, val


def unpack_longlongpar_change(p: bytes) -> Tuple[int, int]:
    _, var, val = struct.unpack_from("<HHq", p)
    return var, val


def unpack_name_all(p: bytes) -> Tuple[int, str]:
    _, gid, name = struct.unpack_from("<HI24s", p)
    return gid, cstr(name)


def unpack_name_npc(p: bytes) -> Tuple[int, str]:
    _, gid, _group, name = struct.unpack_from("<HIi24s", p)
    return gid, cstr(name)


def unpack_say_dialog(p: bytes) -> Tuple[int, str]:
    _, length, npc = struct.unpack_from("<HHI", p)
    return npc, cstr(p[8:length])


def unpack_npc_id(p: bytes) -> int:
    return struct.unpack_from("<HI", p)[1]


def unpack_menu_list(p: bytes) -> Tuple[int, List[str]]:
    _, length, npc = struct.unpack_from("<HHI", p)
    text = cstr(p[8:length])
    # The client hides empty entries; its reply is the visible ordinal.
    # script.cpp menu_countoptions maps that ordinal back to the script index.
    return npc, [t for t in text.split(":") if t]


def unpack_notify_chat(p: bytes) -> Tuple[int, str]:
    _, length, gid = struct.unpack_from("<HHI", p)
    return gid, cstr(p[8:length])


def unpack_varlen_text(p: bytes, head: int) -> str:
    length = struct.unpack_from("<H", p, 2)[0]
    return cstr(p[head:length])


@dataclass
class ShopItem:
    item_id: int
    price: int
    discount: int
    type: int


def unpack_purchase_list(p: bytes) -> List[ShopItem]:
    # PACKET_ZC_PC_PURCHASE_ITEMLIST_sub: itemId u32, price u32, discountPrice u32, itemType u8, viewSprite u16, location u32
    length = struct.unpack_from("<H", p, 2)[0]
    fmt, size = "<IIIBHI", struct.calcsize("<IIIBHI")
    out = []
    for off in range(4, length - size + 1, size):
        item, price, disc, typ, _view, _loc = struct.unpack_from(fmt, p, off)
        out.append(ShopItem(item, price, disc, typ))
    return out


def unpack_cash_list(p: bytes) -> Tuple[int, int, List[ShopItem]]:
    _, length, cash, kafra = struct.unpack_from("<HHII", p)
    fmt, size = "<IIBI", struct.calcsize("<IIBI")
    out = []
    for off in range(12, length - size + 1, size):
        price, disc, typ, item = struct.unpack_from(fmt, p, off)
        out.append(ShopItem(item, price, disc, typ))
    return cash, kafra, out


def unpack_notify_act(p: bytes) -> Tuple[int, int, int, int]:
    """-> (src, target, damage, type)."""
    _, src, tgt, _tick, _ss, _ds, dmg, _sp, _div, typ, dmg2 = struct.unpack_from("<HiiiiiibHBi", p)
    return src, tgt, dmg + dmg2, typ


def unpack_item_entry(p: bytes) -> Tuple[int, int, int, int, int]:
    """-> (aid, item_id, x, y, amount)."""
    _, aid, item, _ident, x, y, amount, _sx, _sy = struct.unpack_from("<HIIBHHHBB", p)
    return aid, item, x, y, amount


def unpack_item_fall(p: bytes) -> Tuple[int, int, int, int, int]:
    """packet_dropflooritem 0x0add (24 bytes): ITAID u32, ITID u32, type u16, IsIdentified u8, xPos i16,
    yPos i16, subX u8, subY u8, count i16, showdropeffect i8, dropeffectmode i16 -> (aid, item_id, x, y, amount)."""
    _, aid, item, _typ, _ident, x, y, _sx, _sy, amount, _fx, _mode = struct.unpack_from("<HIIHBhhBBhbh", p)
    return aid, item, x, y, amount
