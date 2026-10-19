"""
FaithRO FaithBot - sessao de rede: login -> char -> map, loop de eventos e estado do mundo.

Uso basico:
    s = Session(host="127.0.0.1")
    s.login(user, password)          # uma tentativa so (ban de IP por senha errada!)
    s.enter_char(slot=0, create_name="FaithBot")
    s.enter_map()
    s.pump(2.0)                      # processa pacotes por 2 s
    s.quit()

Tudo sincrono, sem threads: pump()/wait_for() leem o socket com select e despacham para
os handlers registrados com on(packet_id). Pacote sem tamanho conhecido = erro fatal
(nao ha como ressincronizar o stream).
"""
from __future__ import annotations

import logging
import select
import socket
import struct
import sys
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from . import protocol as P

log = logging.getLogger("faithbot")


class BotError(RuntimeError):
    pass


class UnknownPacket(BotError):
    pass


class LoginRefused(BotError):
    pass


class MapRefused(BotError):
    def __init__(self, code: int, msg: str):
        super().__init__(msg)
        self.code = code


@dataclass
class Me:
    account_id: int = 0
    char_id: int = 0
    name: str = ""
    sex: int = 0
    map: str = ""
    x: int = 0
    y: int = 0
    hp: int = 0
    max_hp: int = 0
    sp: int = 0
    max_sp: int = 0
    zeny: int = 0
    base_level: int = 0
    job_level: int = 0
    base_exp: int = 0
    job_exp: int = 0
    weight: int = 0
    max_weight: int = 0
    dead: bool = False


@dataclass
class Dialog:
    """Estado da conversa com um NPC."""
    npc: int = 0
    lines: List[str] = field(default_factory=list)      # texto acumulado desde o ultimo evento
    transcript: List[str] = field(default_factory=list)  # tudo, com marcadores
    waiting: Optional[str] = None   # None | "next" | "close" | "menu" | "input_num" | "input_str" | "shop" | "cashshop"
    menu: List[str] = field(default_factory=list)
    shop: List[P.ShopItem] = field(default_factory=list)
    cash_points: int = 0
    closed: bool = True

    def reset(self, npc: int):
        self.npc, self.lines, self.transcript, self.waiting, self.menu, self.shop = npc, [], [], None, [], []
        self.closed = False


@dataclass
class ChatLine:
    kind: str      # "chat" | "self" | "broadcast"
    gid: int
    text: str
    t: float


class Session:
    def __init__(self, host: str = "127.0.0.1", login_port: int = 6900,
                 char_host: Optional[str] = None, map_host: Optional[str] = None, timeout: float = 10.0):
        self.host, self.login_port = host, login_port
        self.char_host, self.map_host = char_host, map_host
        self.timeout = timeout
        self.map_lengths, self.charlogin_lengths, self.names = P.load_lengths()
        self.sock: Optional[socket.socket] = None
        self.phase = "none"            # none | login | char | map
        self.buf = b""
        self.login_ok: Optional[P.LoginOk] = None
        self.chars: List[P.CharInfo] = []
        self.zone: Optional[P.ZoneServer] = None
        self.me = Me()
        self.units: Dict[int, P.Unit] = {}
        self.items: Dict[int, tuple] = {}     # aid -> (item_id, x, y, amount)
        self.dialog = Dialog()
        self.chat: List[ChatLine] = []
        self.pending_names: Dict[int, float] = {}
        self.handlers: Dict[int, List[Callable[[int, bytes], None]]] = {}
        self.unhandled: Dict[int, int] = {}
        self.trace: List[tuple] = []          # ultimos (pid, len, hex) recebidos, para depurar framing
        self.server_tick = 0
        self.last_whisper_ack: Optional[int] = None
        self._tick_at = 0.0
        self._t0 = time.monotonic()
        self._install_map_handlers()

    # ------------------------------------------------------------------ util
    def client_tick(self) -> int:
        return int((time.monotonic() - self._t0) * 1000) & 0xFFFFFFFF

    def on(self, pid: int, fn: Callable[[int, bytes], None]):
        self.handlers.setdefault(pid, []).append(fn)

    def _connect(self, host: str, port: int, phase: str):
        self.close()
        log.info("conectando %s:%d (%s)", host, port, phase)
        self.sock = socket.create_connection((host, port), timeout=self.timeout)
        self.sock.setblocking(False)
        self.phase, self.buf = phase, b""

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = None

    def send(self, data: bytes):
        if not self.sock:
            raise BotError("sem conexao")
        log.debug("-> 0x%04x %d bytes", struct.unpack_from("<H", data)[0], len(data))
        self.sock.sendall(data)

    def _lengths(self) -> Dict[int, int]:
        return self.map_lengths if self.phase == "map" else self.charlogin_lengths

    def _recv_some(self, timeout: float) -> bool:
        r, _, _ = select.select([self.sock], [], [], max(0.0, timeout))
        if not r:
            return False
        data = self.sock.recv(65536)
        if not data:
            raise BotError(f"conexao fechada pelo servidor ({self.phase})")
        self.buf += data
        return True

    def _frames(self):
        """Gera (pid, bytes) completos do buffer; para no primeiro incompleto."""
        lengths = self._lengths()
        while len(self.buf) >= 2:
            pid = struct.unpack_from("<H", self.buf)[0]
            ln = lengths.get(pid)
            if ln is None:
                hist = " ".join(f"0x{p:04x}:{n}" for p, n, _ in self.trace[-10:])
                last = self.trace[-1][2] if self.trace else ""
                raise UnknownPacket(f"pacote 0x{pid:04x} sem tamanho conhecido ({self.phase}); inicio: {self.buf[:32].hex()}; "
                                    f"ultimos pacotes: {hist}; bytes do ultimo: {last}")
            if ln == -1:
                if len(self.buf) < 4:
                    return
                ln = struct.unpack_from("<H", self.buf, 2)[0]
                if ln < 4:
                    raise BotError(f"pacote 0x{pid:04x} com tamanho invalido {ln}")
            if len(self.buf) < ln:
                return
            frame, self.buf = self.buf[:ln], self.buf[ln:]
            self.trace.append((pid, len(frame), frame[:64].hex()))
            del self.trace[:-40]
            log.debug("<- 0x%04x %d bytes (%s)", pid, len(frame), self.names.get(pid, "?"))
            yield pid, frame

    def _dispatch(self, pid: int, frame: bytes):
        fns = self.handlers.get(pid)
        if not fns:
            self.unhandled[pid] = self.unhandled.get(pid, 0) + 1
            return
        for fn in fns:
            fn(pid, frame)

    def pump(self, seconds: float = 0.0):
        """Processa pacotes por ate `seconds` (0 = so o que ja chegou)."""
        end = time.monotonic() + seconds
        while True:
            for pid, frame in self._frames():
                self._dispatch(pid, frame)
            if self.phase == "map" and time.monotonic() - self._tick_at > 10:
                self._tick_at = time.monotonic()
                self.send(P.pack_tick(self.client_tick()))
            remaining = end - time.monotonic()
            if remaining <= 0 and seconds > 0:
                return
            if seconds <= 0:
                if not self._recv_some(0):
                    return
            else:
                self._recv_some(min(remaining, 0.25))

    def wait_for(self, pred: Callable[[], bool], timeout: float, what: str = "resposta") -> None:
        end = time.monotonic() + timeout
        while not pred():
            if time.monotonic() > end:
                raise BotError(f"tempo esgotado esperando {what}")
            self.pump(0.1)

    def read_packet(self, timeout: float) -> tuple:
        """Le um pacote inteiro sem passar pelos handlers (fases login/char)."""
        end = time.monotonic() + timeout
        while True:
            for pid, frame in self._frames():
                return pid, frame
            if time.monotonic() > end:
                raise BotError(f"tempo esgotado ({self.phase})")
            self._recv_some(min(0.5, end - time.monotonic()))

    def _read_raw(self, n: int, timeout: float) -> bytes:
        end = time.monotonic() + timeout
        while len(self.buf) < n:
            if time.monotonic() > end:
                raise BotError("tempo esgotado lendo bytes crus")
            self._recv_some(0.5)
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    # ------------------------------------------------------------------ login
    def login(self, userid: str, password: str, retries: int = 3) -> P.LoginOk:
        """UMA tentativa de senha. Senha errada encerra: o login-server bane o IP apos 7 falhas em 5 min.
        So repete quando o motivo e 'conta ainda online' (0x81 codigo 8), que nao conta como falha."""
        self._last_user, self._last_pass = userid, password
        for attempt in range(retries + 1):
            self._connect(self.host, self.login_port, "login")
            self.send(P.pack_ca_login(userid, password))
            pid, frame = self.read_packet(self.timeout)
            if pid == P.SC_NOTIFY_BAN and frame[2] == 8 and attempt < retries:
                log.info("login-server: conta ainda registrada como online; nova tentativa em 10 s")
                self.close()
                time.sleep(10.0)
                continue
            break
        if pid == P.AC_ACCEPT_LOGIN:
            self.login_ok = P.unpack_ac_accept_login(frame)
            self.me.account_id, self.me.sex = self.login_ok.account_id, self.login_ok.sex
            log.info("login ok: account_id=%d, %d char-server(s)", self.me.account_id, len(self.login_ok.servers))
            return self.login_ok
        if pid in (P.AC_REFUSE_LOGIN, P.AC_REFUSE_LOGIN_OLD):
            code, why = P.unpack_ac_refuse(frame)
            raise LoginRefused(f"login recusado (codigo {code}: {why})")
        if pid == P.SC_NOTIFY_BAN:
            raise LoginRefused(f"desconectado pelo login-server (0x0081, motivo {frame[2]})")
        raise BotError(f"resposta inesperada do login-server: 0x{pid:04x}")

    # ------------------------------------------------------------------ char
    def enter_char(self, slot: int = 0, create_name: Optional[str] = None, char_host: Optional[str] = None) -> P.ZoneServer:
        if not self.login_ok:
            raise BotError("faca login antes")
        self._last_slot = slot
        srv = self.login_ok.servers[0]
        host = char_host or self.char_host or srv.ip
        self._connect(host, srv.port, "char")
        self.send(P.pack_ch_enter(self.login_ok))
        aid = struct.unpack("<I", self._read_raw(4, self.timeout))[0]
        if aid != self.me.account_id:
            raise BotError(f"char-server devolveu account_id {aid}, esperado {self.me.account_id}")
        self.chars = []
        got_list = False
        # le ate receber a lista (0x6b) e o stream ficar quieto por 0,5 s
        end = time.monotonic() + self.timeout
        quiet_since = None
        while time.monotonic() < end:
            try:
                pid, frame = self.read_packet(0.5)
            except BotError:
                if got_list:
                    break
                continue
            if pid == P.HC_ACCEPT_ENTER:
                _total, self.chars = P.unpack_hc_accept_enter(frame)
                got_list = True
            elif pid == P.HC_REFUSE_ENTER:
                raise BotError(f"char-server recusou (0x006c, codigo {frame[2]})")
            elif not self._char_chatter(pid, frame):
                log.debug("char: ignorando 0x%04x", pid)
            if got_list and not self.buf:
                self._recv_some(0.3)
                if not self.buf:
                    break
        if not got_list:
            raise BotError("lista de personagens nao recebida")
        log.info("personagens: %s", ", ".join(f"[{c.slot}] {c.name} Lv{c.base_level}" for c in self.chars) or "nenhum")

        chosen = next((c for c in self.chars if c.slot == slot), None)
        if chosen is None:
            if not create_name:
                raise BotError(f"sem personagem no slot {slot} e create_name nao informado")
            log.info("criando personagem %r no slot %d", create_name, slot)
            self.send(P.pack_ch_make_char(create_name, slot, self.me.sex))
            while True:
                pid, frame = self.read_packet(self.timeout)
                if pid == P.HC_REFUSE_MAKECHAR:
                    raise BotError(f"criacao recusada (codigo {frame[2]})")
                if pid == P.HC_ACCEPT_MAKECHAR:
                    break
                if not self._char_chatter(pid, frame):
                    raise BotError(f"resposta inesperada ao criar personagem: 0x{pid:04x}")
            chosen = P.unpack_character_info(frame, 2)
            self.chars.append(chosen)
        self.me.char_id, self.me.name = chosen.char_id, chosen.name
        self.me.base_level, self.me.job_level, self.me.zeny = chosen.base_level, chosen.job_level, chosen.zeny

        self.send(P.pack_ch_select_char(chosen.slot))
        while True:
            pid, frame = self.read_packet(self.timeout)
            if pid == P.HC_NOTIFY_ZONESVR:
                self.zone = P.unpack_hc_notify_zonesvr(frame)
                log.info("map-server %s:%d, mapa %s", self.zone.ip, self.zone.port, self.zone.map)
                return self.zone
            if pid == P.HC_REFUSE_ENTER:
                raise BotError(f"selecao recusada (0x006c, codigo {frame[2]})")
            if not self._char_chatter(pid, frame):
                log.debug("char: ignorando 0x%04x apos select", pid)

    def _char_chatter(self, pid: int, frame: bytes) -> bool:
        """Pacotes informativos do char-server que podem chegar a qualquer momento."""
        if pid == P.HC_SECOND_PASSWD_LOGIN:
            state = struct.unpack_from("<H", frame, 10)[0]
            if state not in (0, 7):  # 0 = desligado/correto, 7 = aprovado
                raise BotError(f"char-server pede PIN (estado {state}); desligue pincode_enabled ou cadastre o PIN")
            return True
        return pid in (P.HC_ACCEPT_ENTER2, P.HC_CHARLIST_NOTIFY, P.HC_BLOCK_CHARACTER)

    # ------------------------------------------------------------------ map
    def enter_map(self, map_host: Optional[str] = None, retries: int = 2) -> None:
        """Entra no map-server. Codigo 8 (conexao anterior ainda reconhecida) e transitorio:
        espera e tenta de novo, refazendo login/char porque o login_id1 ja foi consumido."""
        for attempt in range(retries + 1):
            try:
                return self._enter_map_once(map_host)
            except MapRefused as e:
                # 8: conexao anterior ainda reconhecida; some em alguns segundos. Outros codigos: parar.
                if e.code != 8 or attempt == retries:
                    raise
                log.info("map-server: %s; nova tentativa em 5 s", e)
                time.sleep(5.0)
                self.login(self._last_user, self._last_pass)
                self.enter_char(self._last_slot)

    def _enter_map_once(self, map_host: Optional[str] = None) -> None:
        if not self.zone or not self.login_ok:
            raise BotError("selecione o personagem antes")
        host = map_host or self.map_host or self.zone.ip
        self._connect(host, self.zone.port, "map")
        self.me.map = self.zone.map
        self.units.clear()
        self.items.clear()
        # o servidor exige que o primeiro pacote seja SO o CZ_ENTER (RFIFOREST == 23): nenhum tick antes do accept
        self._tick_at = time.monotonic()
        self.send(P.pack_cz_enter(self.me.account_id, self.me.char_id, self.login_ok.login_id1, self.client_tick(), self.me.sex))
        entered = {"ok": False}

        def on_accept(pid, frame):
            _start, x, y, _d = P.unpack_accept_enter(frame)
            self.me.x, self.me.y = x, y
            entered["ok"] = True

        refused = {"code": None}

        def on_refuse(pid, frame):
            refused["code"] = frame[2]

        self.on(P.ZC_ACCEPT_ENTER, on_accept)
        self.on(P.ZC_REFUSE_ENTER, on_refuse)
        self.on(P.AC_REFUSE_LOGIN_OLD, on_refuse)   # 0x6a tambem e usado pelo map-server
        self.on(P.SC_NOTIFY_BAN, on_refuse)         # 0x81: ex. codigo 8 "conexao anterior ainda reconhecida"
        try:
            self.wait_for(lambda: entered["ok"] or refused["code"] is not None, self.timeout, "ZC_ACCEPT_ENTER")
        except BotError:
            if refused["code"] is None:
                raise
        if refused["code"] is not None:
            code = refused["code"]
            raise MapRefused(code, f"map-server recusou: {P.MAP_REFUSE_REASONS.get(code, code)} (codigo {code})")
        self.send(P.pack_load_end_ack())
        self._tick_at = time.monotonic()
        self.send(P.pack_tick(self.client_tick()))
        self.pump(1.0)
        log.info("no mapa %s (%d,%d) como %s", self.me.map, self.me.x, self.me.y, self.me.name)

    def quit(self, timeout: float = 15.0):
        """Sai do jogo de forma limpa. O servidor so aceita (0x18b codigo 0) depois de ~10 s sem
        acao; ate la responde 1 e o bot espera, senao o personagem fica 'online' e a proxima
        conexao e recusada (codigo 8)."""
        if self.sock and self.phase == "map":
            self._quit_ack = None
            self.on(P.ZC_ACK_REQ_DISCONNECT, lambda pid, f: setattr(self, "_quit_ack", struct.unpack_from("<H", f, 2)[0]))
            end = time.monotonic() + timeout
            try:
                while time.monotonic() < end:
                    self._quit_ack = None
                    self.send(P.pack_quit())
                    self.wait_for(lambda: self._quit_ack is not None, 3.0, "resposta do quit")
                    if self._quit_ack == 0:
                        break
                    self.pump(2.0)
                else:
                    log.warning("servidor nao liberou o quit a tempo; fechando mesmo assim")
            except (BotError, OSError) as e:
                log.debug("quit: %s", e)
        self.close()

    # ------------------------------------------------------------------ handlers do mapa
    def _install_map_handlers(self):
        self.on(P.ZC_AID, lambda pid, f: None)
        self.on(P.ZC_NOTIFY_TIME, self._h_time)
        for pid in (P.ZC_NOTIFY_STANDENTRY, P.ZC_NOTIFY_NEWENTRY, P.ZC_NOTIFY_MOVEENTRY):
            self.on(pid, self._h_unit)
        self.on(P.ZC_NOTIFY_VANISH, self._h_vanish)
        self.on(P.ZC_NOTIFY_PLAYERMOVE, self._h_playermove)
        self.on(P.ZC_NPCACK_MAPMOVE, self._h_mapmove)
        self.on(P.ZC_ACK_REQNAMEALL, self._h_name)
        self.on(P.ZC_ACK_REQNAMEALL_NPC, self._h_name_npc)
        self.on(P.ZC_PAR_CHANGE, self._h_par)
        self.on(P.ZC_LONGPAR_CHANGE, self._h_par)
        self.on(P.ZC_LONGLONGPAR_CHANGE, self._h_longlongpar)
        self.on(P.ZC_SAY_DIALOG, self._h_say)
        self.on(P.ZC_WAIT_DIALOG, self._h_wait)
        self.on(P.ZC_CLOSE_DIALOG, self._h_close)
        self.on(P.ZC_MENU_LIST, self._h_menu)
        self.on(P.ZC_OPEN_EDITDLG, self._h_input_num)
        self.on(P.ZC_OPEN_EDITDLGSTR, self._h_input_str)
        self.on(P.ZC_SELECT_DEALTYPE, self._h_dealtype)
        self.on(P.ZC_PC_PURCHASE_ITEMLIST, self._h_shop)
        self.on(P.ZC_PC_CASH_POINT_ITEMLIST, self._h_cashshop)
        self.on(P.ZC_PC_PURCHASE_RESULT, self._h_purchase_result)
        self.on(P.ZC_NOTIFY_CHAT, self._h_chat)
        self.on(P.ZC_NOTIFY_PLAYERCHAT, self._h_selfchat)
        self.on(P.ZC_WHISPER, self._h_whisper)
        self.on(P.ZC_ACK_WHISPER, self._h_whisper_ack)
        self.on(P.ZC_BROADCAST, lambda pid, f: self._push_chat("broadcast", 0, P.unpack_varlen_text(f, 4)))
        self.on(P.ZC_BROADCAST2, lambda pid, f: self._push_chat("broadcast", 0, P.unpack_varlen_text(f, 16)))
        self.on(P.ZC_NOTIFY_ACT, self._h_act)
        self.on(P.ZC_ITEM_ENTRY, self._h_item)
        self.on(P.ZC_ITEM_FALL_ENTRY, self._h_item_fall)
        self.on(P.ZC_ITEM_DISAPPEAR, lambda pid, f: self.items.pop(struct.unpack_from("<I", f, 2)[0], None))

    def _h_time(self, pid, f):
        self.server_tick = struct.unpack_from("<I", f, 2)[0]

    def _h_unit(self, pid, f):
        try:
            u = P.unpack_unit(pid, f)
        except struct.error as e:
            log.debug("unit 0x%04x indecifravel (%d bytes): %s", pid, len(f), e)
            return
        if u.aid == self.me.account_id:
            self.me.x, self.me.y = u.x, u.y
            return
        old = self.units.get(u.aid)
        if old and not u.name:
            u.name = old.name
        self.units[u.aid] = u
        if not u.name and u.type in (P.UT_PC, P.UT_NPC, P.UT_MOB, P.UT_NPC_SHOP) and u.aid not in self.pending_names:
            self.pending_names[u.aid] = time.monotonic()
            self.send(P.pack_reqname(u.aid))

    def _h_vanish(self, pid, f):
        aid, typ = P.unpack_vanish(f)
        if aid == self.me.account_id:
            if typ == 1:
                self.me.dead = True
            return
        self.units.pop(aid, None)
        self.pending_names.pop(aid, None)

    def _h_playermove(self, pid, f):
        _x0, _y0, x1, y1 = P.unpack_playermove(f)
        self.me.x, self.me.y = x1, y1

    def _h_mapmove(self, pid, f):
        m, x, y = P.unpack_mapmove(f)
        self.me.map, self.me.x, self.me.y = m.split(".")[0], x, y
        self.units.clear()
        self.items.clear()
        # o cliente confirma o carregamento do novo mapa
        self.send(P.pack_load_end_ack())

    def _h_name(self, pid, f):
        gid, name = P.unpack_name_all(f)
        self._set_name(gid, name)

    def _h_name_npc(self, pid, f):
        gid, name = P.unpack_name_npc(f)
        self._set_name(gid, name)

    def _set_name(self, gid, name):
        self.pending_names.pop(gid, None)
        if gid == self.me.account_id:
            self.me.name = name
        elif gid in self.units:
            self.units[gid].name = name

    def _h_par(self, pid, f):
        var, val = P.unpack_par_change(f)
        self._apply_par(var, val)

    def _h_longlongpar(self, pid, f):
        var, val = P.unpack_longlongpar_change(f)
        self._apply_par(var, val)

    def _apply_par(self, var, val):
        name = P.SP_NAMES.get(var)
        if name and hasattr(self.me, name):
            setattr(self.me, name, val)
        if var == P.SP_HP:
            self.me.dead = val <= 0

    # --- dialogo
    def _h_say(self, pid, f):
        npc, text = P.unpack_say_dialog(f)
        if self.dialog.closed or self.dialog.npc != npc:
            self.dialog.reset(npc)
        self.dialog.lines.append(text)
        self.dialog.transcript.append(text)

    def _h_wait(self, pid, f):
        self.dialog.npc = P.unpack_npc_id(f)
        self.dialog.waiting = "next"
        self.dialog.closed = False

    def _h_close(self, pid, f):
        self.dialog.npc = P.unpack_npc_id(f)
        self.dialog.waiting = "close"
        self.dialog.closed = False

    def _h_menu(self, pid, f):
        npc, items = P.unpack_menu_list(f)
        if self.dialog.closed or self.dialog.npc != npc:
            self.dialog.reset(npc)
        self.dialog.menu = items
        self.dialog.waiting = "menu"
        self.dialog.transcript.append("[menu] " + " | ".join(f"{i + 1}. {t}" for i, t in enumerate(items)))

    def _h_input_num(self, pid, f):
        self.dialog.npc = P.unpack_npc_id(f)
        self.dialog.waiting = "input_num"
        self.dialog.closed = False

    def _h_input_str(self, pid, f):
        self.dialog.npc = P.unpack_npc_id(f)
        self.dialog.waiting = "input_str"
        self.dialog.closed = False

    def _h_dealtype(self, pid, f):
        self.dialog.npc = P.unpack_npc_id(f)
        self.dialog.waiting = "dealtype"
        self.dialog.closed = False

    def _h_shop(self, pid, f):
        self.dialog.shop = P.unpack_purchase_list(f)
        self.dialog.waiting = "shop"
        self.dialog.closed = False
        self.dialog.transcript.append("[loja] " + ", ".join(f"{i.item_id}:{i.discount}z" for i in self.dialog.shop))

    def _h_cashshop(self, pid, f):
        cash, _kafra, items = P.unpack_cash_list(f)
        self.dialog.shop, self.dialog.cash_points = items, cash
        self.dialog.waiting = "cashshop"
        self.dialog.closed = False
        self.dialog.transcript.append(f"[cashshop {cash} pts] " + ", ".join(f"{i.item_id}:{i.discount}" for i in items))

    def _h_purchase_result(self, pid, f):
        self.dialog.transcript.append(f"[compra] resultado {f[2]}")
        self.dialog.last_purchase = f[2]  # type: ignore[attr-defined]

    # --- chat e combate
    def _push_chat(self, kind, gid, text):
        self.chat.append(ChatLine(kind, gid, text, time.monotonic()))
        del self.chat[:-200]
        log.info("[%s] %s", kind, text)

    def _h_chat(self, pid, f):
        gid, text = P.unpack_notify_chat(f)
        self._push_chat("chat", gid, text)

    def _h_selfchat(self, pid, f):
        self._push_chat("self", self.me.account_id, P.unpack_varlen_text(f, 4))

    def _h_whisper(self, pid, f):
        gid, sender, text = P.unpack_whisper(f)
        self._push_chat("whisper", gid, f"{sender}: {text}")

    def _h_whisper_ack(self, pid, f):
        self.last_whisper_ack = P.unpack_whisper_ack(f)[0]

    def _h_act(self, pid, f):
        src, tgt, dmg, typ = P.unpack_notify_act(f)
        if typ in (0, 4, 8, 10) and dmg:  # dano normal / critico / multi-hit
            u = self.units.get(tgt)
            if u:
                u.hp = max(0, u.hp - dmg) if u.hp else 0
            log.debug("ataque %d -> %d: %d", src, tgt, dmg)

    def _h_item(self, pid, f):
        aid, item, x, y, amount = P.unpack_item_entry(f)
        self.items[aid] = (item, x, y, amount)

    def _h_item_fall(self, pid, f):
        try:
            aid, item, x, y, amount = P.unpack_item_fall(f)
        except struct.error:
            return
        self.items[aid] = (item, x, y, amount)

    # ------------------------------------------------------------------ consultas
    def find_units(self, name: Optional[str] = None, kind: Optional[int] = None) -> List[P.Unit]:
        out = []
        for u in self.units.values():
            if kind is not None and u.type != kind:
                continue
            if name:
                full, disp, want = u.name.lower(), P.display_name(u.name).lower(), name.lower()
                if want not in (full, disp) and not disp.startswith(want):
                    continue
            out.append(u)
        out.sort(key=lambda u: abs(u.x - self.me.x) + abs(u.y - self.me.y))
        return out

    def status(self) -> str:
        m = self.me
        return (f"{m.name} {m.map} ({m.x},{m.y}) Lv{m.base_level}/{m.job_level} HP {m.hp}/{m.max_hp} "
                f"SP {m.sp}/{m.max_sp} zeny {m.zeny} peso {m.weight}/{m.max_weight}")
