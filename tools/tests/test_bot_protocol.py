"""Testes do protocolo do FaithBot (tools/bot): tamanhos, posicoes e decodificadores."""
import json
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from bot import protocol as P  # noqa: E402


def test_tabela_e_do_packetver_certo():
    m, c, names = P.load_lengths()
    assert json.load(open(ROOT / "tools/bot/packet_lengths.json"))["packetver"] == P.PACKETVER
    assert m[P.ZC_ACCEPT_ENTER] == 13
    assert m[P.ZC_NOTIFY_STANDENTRY] == -1 and m[P.ZC_NOTIFY_MOVEENTRY] == -1
    assert c[P.HC_NOTIFY_ZONESVR] == 156 and c[P.HC_ACCEPT_MAKECHAR] == 177
    assert names[P.ZC_ACK_REQNAMEALL_NPC] == "ZC_ACK_REQNAMEALL_NPC"


def test_tamanhos_dos_structs():
    assert P.CHARACTER_INFO_SIZE == 175
    assert struct.calcsize(P.AC_ACCEPT_HEAD) == 64 and struct.calcsize(P.AC_ACCEPT_SUB) == 160
    assert struct.calcsize(P.HC_ACCEPT_ENTER_HEAD) == 27
    assert len(P.pack_ca_login("a", "b")) == 55
    assert len(P.pack_ch_enter(P.LoginOk(1, 2, 3, 0, b""))) == 17
    assert len(P.pack_ch_make_char("FaithBot", 0, 0)) == 36
    assert len(P.pack_cz_enter(1, 2, 3, 4, 0)) == 23
    assert len(P.pack_walk(1, 1)) == 5 and len(P.pack_action(1, 7)) == 7 and len(P.pack_tick(1)) == 6
    assert len(P.pack_npc_click(1)) == 7 and len(P.pack_npc_menu(1, 2)) == 7 and len(P.pack_npc_next(1)) == 6
    assert len(P.pack_npc_input_num(1, 5)) == 10 and len(P.pack_buysell_select(1)) == 7


def test_cz_enter_offsets():
    p = P.pack_cz_enter(0xAAAAAAAA, 0xBBBBBBBB, 0xCCCCCCCC, 0xDDDDDDDD, 1)
    assert struct.unpack_from("<I", p, 2)[0] == 0xAAAAAAAA
    assert struct.unpack_from("<I", p, 6)[0] == 0xBBBBBBBB
    assert struct.unpack_from("<I", p, 10)[0] == 0xCCCCCCCC
    assert struct.unpack_from("<I", p, 14)[0] == 0xDDDDDDDD
    assert p[22] == 1


@pytest.mark.parametrize("x,y,d", [(0, 0, 0), (155, 180, 4), (1023, 1023, 15), (300, 7, 1)])
def test_pos_roundtrip(x, y, d):
    assert P.decode_pos(P.encode_pos(x, y, d)) == (x, y, d)


def test_pos2():
    # WBUFPOS2(156, 187, 160, 190, 8, 8) como o rAthena codifica
    x0, y0, x1, y1, sx, sy = 156, 187, 160, 190, 8, 8
    b = bytes([x0 >> 2, ((x0 << 6) | (y0 >> 4)) & 0xFF, ((y0 << 4) | (x1 >> 6)) & 0xFF,
               ((x1 << 2) | (y1 >> 8)) & 0xFF, y1 & 0xFF, ((sx << 4) | sy) & 0xFF])
    assert P.decode_pos2(b) == (x0, y0, x1, y1, sx, sy)


def test_ip_str():
    # rAthena escreve htonl(ip) num uint32 little-endian: bytes na ordem a.b.c.d
    assert P.ip_str(struct.unpack("<I", bytes([129, 121, 46, 11]))[0]) == "129.121.46.11"


def test_ac_accept_login():
    sub = struct.pack(P.AC_ACCEPT_SUB, struct.unpack("<I", bytes([127, 0, 0, 1]))[0], 6121, P.fixed("FaithRO", 20), 3, 0, 0, b"\0" * 128)
    body = struct.pack(P.AC_ACCEPT_HEAD, P.AC_ACCEPT_LOGIN, 64 + 160, 11, 2000000, 22, 0, b"\0" * 26, 1, b"\0" * 17) + sub
    ok = P.unpack_ac_accept_login(body)
    assert (ok.login_id1, ok.account_id, ok.login_id2, ok.sex) == (11, 2000000, 22, 1)
    assert ok.servers[0].ip == "127.0.0.1" and ok.servers[0].port == 6121 and ok.servers[0].name == "FaithRO"


def test_hc_accept_enter_e_character_info():
    vals = [150000, 1234, 500, 77, 10, 0, 0, 0, 0, 0, 3, 40, 40, 11, 11, 150, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0,
            P.fixed("FaithBot", 24), 1, 1, 1, 1, 1, 1, 0, 0, 0, P.fixed("prontera", 16), 0, 0, 0, 0, 1]
    ci = struct.pack(P.CHARACTER_INFO, *vals)
    assert len(ci) == 175
    p = struct.pack(P.HC_ACCEPT_ENTER_HEAD, P.HC_ACCEPT_ENTER, 27 + 175, 5, 5, 5, b"\0" * 20) + ci
    total, chars = P.unpack_hc_accept_enter(p)
    assert total == 5 and len(chars) == 1
    c = chars[0]
    assert (c.char_id, c.name, c.slot, c.base_level, c.job_level, c.zeny, c.hp, c.map, c.sex) == (150000, "FaithBot", 0, 1, 10, 500, 40, "prontera", 1)


def test_menu_say_e_vanish():
    npc, items = P.unpack_menu_list(struct.pack("<HHI", P.ZC_MENU_LIST, 8 + 12, 110000000) + b"Rates:Sair:\0")
    assert npc == 110000000 and items == ["Rates", "Sair"]
    npc, text = P.unpack_say_dialog(struct.pack("<HHI", P.ZC_SAY_DIALOG, 8 + 6, 7) + b"Ol\xe1!\0")
    assert (npc, text) == (7, "Olá!")
    assert P.unpack_vanish(struct.pack("<HIB", P.ZC_NOTIFY_VANISH, 99, 1)) == (99, 1)


@pytest.mark.parametrize('text,visible,choice,wire_index',[
    (':Status:Abandonar::Info:', ['Status','Abandonar','Info'], 'Status', 1),
    ('A::B', ['A','B'], 'B', 2),
    (' :A::', [' ','A'], 'A', 2),
])
def test_empty_menu_options_do_not_shift_client_reply(text,visible,choice,wire_index):
    from bot.actions import Actions
    body=text.encode(P.ENCODING)+b'\0'
    npc,items=P.unpack_menu_list(struct.pack('<HHI',P.ZC_MENU_LIST,8+len(body),123)+body)
    assert items==visible
    packet=P.pack_npc_menu(npc,Actions._menu_index(items,choice))
    assert packet[-1]==wire_index


def test_purchase_list():
    sub = struct.pack("<IIIBHI", 1750, 1, 1, 10, 0, 0) + struct.pack("<IIIBHI", 501, 50, 40, 0, 0, 0)
    p = struct.pack("<HH", P.ZC_PC_PURCHASE_ITEMLIST, 4 + len(sub)) + sub
    lst = P.unpack_purchase_list(p)
    assert [(i.item_id, i.discount) for i in lst] == [(1750, 1), (501, 40)]
    b = P.pack_buy([(1750, 100), (501, 2)])
    assert struct.unpack_from("<H", b, 2)[0] == len(b) == 4 + 12
    assert struct.unpack_from("<HI", b, 4) == (100, 1750)


def test_unit_idle_e_walking():
    head = struct.pack(P._UNIT_HEAD, P.ZC_NOTIFY_STANDENTRY, 0, P.UT_NPC, 110000001, 0, 0, 0, 0, 0, 4020,
                       0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    tail = P.encode_pos(160, 187, 4) + struct.pack("<BBBhhiiBH", 5, 5, 0, 1, 0, 0, 0, 0, 0) + P.fixed("Mercado Premium", 24)
    p = head + tail
    p = struct.pack("<H", P.ZC_NOTIFY_STANDENTRY) + struct.pack("<H", len(p)) + p[4:]
    u = P.unpack_unit(P.ZC_NOTIFY_STANDENTRY, p)
    assert (u.aid, u.type, u.job, u.x, u.y, u.name) == (110000001, P.UT_NPC, 4020, 160, 187, "Mercado Premium")

    move = bytes([156 >> 2, ((156 << 6) | (187 >> 4)) & 0xFF, ((187 << 4) | (160 >> 6)) & 0xFF, ((160 << 2) | (190 >> 8)) & 0xFF, 190, 0x88])
    headw = struct.pack("<HHBIIhhhihHIIHIHHhhhHIhhiBB", P.ZC_NOTIFY_MOVEENTRY, 0, P.UT_MOB, 2001, 1002, 150, 0, 0, 0, 1002,
                        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    tailw = move + struct.pack("<BBhhiiBH", 5, 5, 1, 0, 60, 55, 0, 0) + P.fixed("Poring", 24)
    pw = headw + tailw
    pw = pw[:2] + struct.pack("<H", len(pw)) + pw[4:]
    u = P.unpack_unit(P.ZC_NOTIFY_MOVEENTRY, pw)
    assert (u.aid, u.type, u.x, u.y, u.hp, u.max_hp, u.name) == (2001, P.UT_MOB, 160, 190, 55, 60, "Poring")


def test_whisper():
    b = P.pack_whisper("NPC:FaithRO_Presente", "Fulano#novo")
    assert struct.unpack_from("<HH", b) == (P.CZ_WHISPER, len(b)) and len(b) == 28 + len(b"Fulano#novo\0")
    assert b[4:28].rstrip(b"\0") == b"NPC:FaithRO_Presente" and b[28:] == b"Fulano#novo\0"
    p = struct.pack("<HHI24sB", P.ZC_WHISPER, 33 + 4, 150000, P.fixed("Night", 24), 0) + b"oi!\0"
    assert P.unpack_whisper(p) == (150000, "Night", "oi!")
    assert P.unpack_whisper_ack(struct.pack("<HBI", P.ZC_ACK_WHISPER, 1, 0)) == (1, 0)
    m, _, _ = P.load_lengths()
    assert m[P.ZC_WHISPER] == -1 and m[P.ZC_ACK_WHISPER] == 7 and m[P.CZ_WHISPER] == -1


def test_chat_pack():
    b = P.pack_chat("FaithBot", "oi")
    assert struct.unpack_from("<HH", b) == (P.CZ_REQUEST_CHAT, len(b))
    assert b[4:] == b"FaithBot : oi\0"
