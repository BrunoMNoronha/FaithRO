"""
FaithRO FaithBot - acoes de alto nivel sobre uma Session: andar, falar com NPC, comprar, atacar.
"""
from __future__ import annotations

import logging
import random
import time
from typing import List, Optional, Sequence, Tuple, Union

from . import protocol as P
from .client import BotError, Session

log = logging.getLogger("faithbot")

MAX_HOP = 28          # o servidor so calcula caminho ate 32 celulas (MAX_WALKPATH)


def _dist(ax, ay, bx, by) -> int:
    return max(abs(ax - bx), abs(ay - by))


class Actions:
    def __init__(self, s: Session):
        self.s = s

    # ------------------------------------------------------------------ movimento
    def _hop_candidates(self, x: int, y: int):
        """Pontos intermediarios na direcao de (x,y): o salto direto, saltos mais curtos e desvios laterais."""
        s = self.s
        dx, dy = x - s.me.x, y - s.me.y
        d = max(abs(dx), abs(dy))
        if d <= MAX_HOP:
            yield x, y
        ux, uy = dx / d, dy / d
        px, py = -uy, ux                      # perpendicular
        seen = set()
        for hop in (MAX_HOP, 20, 12, 6):
            for side in (0, 4, -4, 8, -8, 12, -12, 16, -16, 20, -20, 24, -24):
                tx = s.me.x + round(ux * hop + px * side)
                ty = s.me.y + round(uy * hop + py * side)
                if (tx, ty) != (s.me.x, s.me.y) and (tx, ty) not in seen and tx >= 0 and ty >= 0:
                    seen.add((tx, ty))
                    yield tx, ty

    def _try_walk(self, tx: int, ty: int, wait: float = 0.8) -> bool:
        """Manda andar ate (tx,ty) e devolve True se o servidor confirmou movimento."""
        s = self.s
        before = (s.me.x, s.me.y)
        s.send(P.pack_walk(tx, ty))
        try:
            s.wait_for(lambda: (s.me.x, s.me.y) != before, wait, "inicio do movimento")
        except BotError:
            return False
        steps = _dist(before[0], before[1], s.me.x, s.me.y)
        s.pump(min(8.0, 0.16 * steps + 0.25))   # ZC_NOTIFY_PLAYERMOVE ja traz o destino; espera o trajeto
        return True

    def walk_to(self, x: int, y: int, tolerance: int = 1, timeout: float = 180.0) -> bool:
        """Anda em saltos de ate MAX_HOP celulas (limite de caminho do servidor). Quando o ponto
        intermediario e bloqueado (ex. a fonte de Prontera), tenta saltos menores e desvios laterais."""
        s = self.s
        end = time.monotonic() + timeout
        visited = set()
        start_map = s.me.map
        while _dist(s.me.x, s.me.y, x, y) > tolerance:
            if s.me.map != start_map:          # entrou num portal: as coordenadas antigas nao valem mais
                log.info("walk_to: mudou de mapa para %s (%d,%d)", s.me.map, s.me.x, s.me.y)
                return True
            if time.monotonic() > end:
                raise BotError(f"walk_to({x},{y}): tempo esgotado em ({s.me.x},{s.me.y})")
            start = (s.me.x, s.me.y)
            visited.add(start)
            for tx, ty in self._hop_candidates(x, y):
                if (tx, ty) not in visited and self._try_walk(tx, ty):
                    break
            if (s.me.x, s.me.y) == start:
                # obstaculo grande (ex. a fonte de Prontera): contorna por qualquer lado que
                # ainda nao foi visitado, preferindo o que mais aproxima do alvo
                escapes = []
                for r in (8, 16):
                    for ddx, ddy in ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)):
                        tx, ty = start[0] + ddx * r, start[1] + ddy * r
                        if tx >= 0 and ty >= 0 and (tx, ty) not in visited:
                            escapes.append((_dist(tx, ty, x, y), tx, ty))
                for _, tx, ty in sorted(escapes):
                    if self._try_walk(tx, ty):
                        break
            if (s.me.x, s.me.y) == start:
                raise BotError(f"walk_to({x},{y}): sem progresso em ({s.me.x},{s.me.y}); caminho bloqueado?")
        return True

    # ------------------------------------------------------------------ NPC
    def find_npc(self, target: Union[str, int], wait: float = 3.0) -> P.Unit:
        s = self.s
        if isinstance(target, int):
            u = s.units.get(target)
            if not u:
                raise BotError(f"NPC com id {target} nao esta na tela")
            return u
        end = time.monotonic() + wait
        while True:
            cands = s.find_units(target)
            found = [u for u in cands if u.type in P.NPC_TYPES] or [u for u in cands if u.type == P.UT_PC and u.name]
            if found:
                return found[0]
            if time.monotonic() > end:
                visible = sorted({P.display_name(u.name) for u in s.units.values() if u.type in P.NPC_TYPES and u.name})
                raise BotError(f"NPC {target!r} nao encontrado na tela. Visiveis: {', '.join(visible) or 'nenhum'}")
            s.pump(0.3)

    def approach(self, u: P.Unit, within: int = 2):
        if _dist(self.s.me.x, self.s.me.y, u.x, u.y) > within:
            self.walk_to(u.x, u.y, tolerance=within)

    def talk(self, target: Union[str, int], choices: Sequence[Union[int, str]] = (), auto_next: bool = True,
             timeout: float = 8.0, approach: bool = True) -> List[str]:
        """Clica no NPC e segue o dialogo. `choices` responde menus/inputs em ordem:
        int = opcao do menu (1..N) ou numero para input; str = texto para input ou prefixo da opcao.
        Devolve a transcricao."""
        s = self.s
        u = self.find_npc(target)
        if approach:
            self.approach(u, within=3)
        s.dialog.reset(u.aid)
        s.dialog.closed = True
        s.send(P.pack_npc_click(u.aid))
        queue = list(choices)
        idle = 0.0
        while True:
            try:
                s.wait_for(lambda: s.dialog.waiting is not None, timeout, f"dialogo do NPC {u.name!r}")
            except BotError:
                if s.dialog.transcript:
                    s.dialog.transcript.append("[fim sem close]")
                    return s.dialog.transcript
                raise
            w = s.dialog.waiting
            s.dialog.waiting = None
            npc = s.dialog.npc or u.aid
            if w == "next":
                if not auto_next:
                    return s.dialog.transcript
                s.pump(0.1)
                s.send(P.pack_npc_next(npc))
            elif w == "close":
                s.send(P.pack_npc_close(npc))
                s.dialog.closed = True
                s.dialog.transcript.append("[close]")
                s.pump(0.2)
                return s.dialog.transcript
            elif w == "menu":
                if not queue:
                    s.send(P.pack_npc_menu(npc, 255))
                    s.dialog.transcript.append("[menu cancelado: sem escolha pendente]")
                    s.dialog.closed = True
                    s.pump(0.3)
                    return s.dialog.transcript
                c = queue.pop(0)
                idx = self._menu_index(s.dialog.menu, c)
                s.dialog.transcript.append(f"[escolha {idx}: {s.dialog.menu[idx - 1] if 0 < idx <= len(s.dialog.menu) else '?'}]")
                s.send(P.pack_npc_menu(npc, idx))
            elif w == "input_num":
                v = int(queue.pop(0)) if queue else 0
                s.dialog.transcript.append(f"[input {v}]")
                s.send(P.pack_npc_input_num(npc, v))
            elif w == "input_str":
                v = str(queue.pop(0)) if queue else ""
                s.dialog.transcript.append(f"[input {v!r}]")
                s.send(P.pack_npc_input_str(npc, v))
            elif w == "dealtype":
                s.dialog.transcript.append("[loja: comprar]")
                s.send(P.pack_buysell_select(npc, buy=True))
            elif w in ("shop", "cashshop"):
                # a lista ficou em s.dialog.shop; quem chamou decide (ver buy())
                s.dialog.waiting = w
                return s.dialog.transcript
            else:
                raise BotError(f"estado de dialogo desconhecido: {w}")

    @staticmethod
    def _menu_index(menu: List[str], choice: Union[int, str]) -> int:
        if isinstance(choice, int):
            return choice
        c = str(choice).strip().lower()
        if c.isdigit():
            return int(c)
        for i, item in enumerate(menu, 1):
            if item.strip().lower().startswith(c):
                return i
        raise BotError(f"opcao {choice!r} nao esta no menu: {menu}")

    # ------------------------------------------------------------------ loja
    def open_shop(self, target: Union[str, int], choices: Sequence[Union[int, str]] = ()) -> List[P.ShopItem]:
        self.talk(target, choices=choices)
        s = self.s
        if s.dialog.waiting not in ("shop", "cashshop"):
            s.wait_for(lambda: s.dialog.waiting in ("shop", "cashshop"), 5.0, "lista da loja")
        return s.dialog.shop

    def buy(self, target: Union[str, int], items: Sequence[Tuple[int, int]], choices: Sequence[Union[int, str]] = ()) -> int:
        """items: [(item_id, quantidade)]. Devolve o codigo de ZC_PC_PURCHASE_RESULT (0 = ok)."""
        s = self.s
        lst = self.open_shop(target, choices)
        offered = {i.item_id for i in lst}
        missing = [i for i, _ in items if i not in offered]
        if missing:
            raise BotError(f"loja nao vende {missing}; oferece {sorted(offered)}")
        s.dialog.last_purchase = None  # type: ignore[attr-defined]
        if s.dialog.waiting == "cashshop":
            s.send(P.pack_cash_buy(list(items)))
        else:
            s.send(P.pack_buy(list(items)))
        s.dialog.waiting = None
        s.wait_for(lambda: getattr(s.dialog, "last_purchase", None) is not None, 5.0, "resultado da compra")
        return s.dialog.last_purchase  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ combate
    def attack(self, target: Union[str, int], timeout: float = 30.0) -> bool:
        """Ataca ate o alvo sumir (morrer) ou o tempo acabar. Devolve True se o alvo sumiu."""
        s = self.s
        u = s.units.get(target) if isinstance(target, int) else None
        if u is None:
            cands = [m for m in s.find_units(target if isinstance(target, str) else None, P.UT_MOB)]
            if not cands:
                raise BotError(f"monstro {target!r} nao esta na tela")
            u = cands[0]
        self.approach(u, within=1)
        end = time.monotonic() + timeout
        s.send(P.pack_action(u.aid, 7))
        last = time.monotonic()
        while u.aid in s.units:
            if time.monotonic() > end or s.me.dead:
                return False
            if time.monotonic() - last > 3:
                s.send(P.pack_action(u.aid, 7))
                last = time.monotonic()
            s.pump(0.3)
        return True

    def respawn(self) -> None:
        """Morto: volta ao ponto de salvamento (CZ_RESTART tipo 0) e espera o novo mapa."""
        s = self.s
        s.send(P.pack_restart(to_char_select=False))
        s.pump(3.0)
        s.me.dead = False
        log.info("renasceu em %s (%d,%d)", s.me.map, s.me.x, s.me.y)

    def pickup_all(self, radius: int = 6) -> int:
        s = self.s
        n = 0
        for aid, (item, x, y, amount) in list(s.items.items()):
            if _dist(s.me.x, s.me.y, x, y) <= radius:
                self.walk_to(x, y, tolerance=1, timeout=10)
                s.send(P.pack_pickup(aid))
                s.pump(0.5)
                n += 1
        return n

    def grind(self, mob: Optional[str], seconds: float) -> dict:
        s = self.s
        end = time.monotonic() + seconds
        kills, fails = 0, 0
        idle_since = None
        rng = random.Random(7)
        while time.monotonic() < end:
            cands = s.find_units(mob, P.UT_MOB)
            if not cands:
                s.pump(1.0)
                idle_since = idle_since or time.monotonic()
                if time.monotonic() - idle_since > 3:   # nada na tela: perambula para achar o alvo
                    idle_since = None
                    tx = max(1, s.me.x + rng.randint(-18, 18))
                    ty = max(1, s.me.y + rng.randint(-18, 18))
                    try:
                        self.walk_to(tx, ty, tolerance=4, timeout=20)
                    except BotError as e:
                        log.debug("perambular: %s", e)
                continue
            idle_since = None
            target = cands[0]
            ok = self.attack(target.aid, timeout=min(30, end - time.monotonic()))
            if s.me.dead:
                log.warning("o bot morreu lutando com %s; voltando ao ponto de salvamento", target.name)
                self.respawn()
                return {"kills": kills, "fails": fails, "deaths": 1, "killed_by": target.name,
                        "zeny": s.me.zeny, "base_exp": s.me.base_exp, "hp": s.me.hp, "map": s.me.map}
            kills += 1 if ok else 0
            fails += 0 if ok else 1
            if ok:
                self.pickup_all()
        return {"kills": kills, "fails": fails, "deaths": 0, "zeny": s.me.zeny, "base_exp": s.me.base_exp,
                "hp": s.me.hp, "map": s.me.map}

    # ------------------------------------------------------------------ chat
    def say(self, text: str, wait: float = 1.0) -> bool:
        s = self.s
        n = len(s.chat)
        s.send(P.pack_chat(s.me.name, text))
        s.pump(wait)
        return any(c.kind == "self" for c in s.chat[n:])

    def whisper(self, target: str, text: str, wait: float = 3.0) -> int:
        """Sussurra e devolve o resultado (0 = entregue; ver P.WHISPER_RESULTS)."""
        s = self.s
        s.last_whisper_ack = None
        s.send(P.pack_whisper(target, text))
        try:
            s.wait_for(lambda: s.last_whisper_ack is not None, wait, "confirmacao do sussurro")
        except BotError:
            return -1
        return s.last_whisper_ack

    # ------------------------------------------------------------------ boas-vindas
    GIFT_NPC = "NPC:FaithRO_Presente"

    def gift(self, target: str, kind: str = "volta", wait: float = 5.0) -> str:
        """Pede ao NPC FaithRO_Presente (server/npc/custom/faithro/presente.txt) que entregue o presente.
        -> "PRESENTE_OK" | "PRESENTE_JA" | "PRESENTE_OFFLINE" | "SEM_RESPOSTA"."""
        s = self.s
        n = len(s.chat)
        s.send(P.pack_whisper(self.GIFT_NPC, f"{target}#{kind}"))
        end = time.monotonic() + wait
        while time.monotonic() < end:
            s.pump(0.3)
            for c in s.chat[n:]:
                if c.kind == "self" and c.text.startswith("PRESENTE_"):
                    return c.text.split(" ", 1)[0]
        return "SEM_RESPOSTA"

    def welcome(self, name: str, map_name: str, x: int, y: int, new_player: bool,
                stay_seconds: float = 90.0, messages: Optional[dict] = None) -> dict:
        """Vai ate o jogador (se estiver no mesmo mapa), da as boas-vindas, entrega o presente,
        espera e se despede. Fora do mapa do bot, tudo vai por sussurro."""
        s = self.s
        m = dict(DEFAULT_MESSAGES)
        m.update(messages or {})
        kind = "novo" if new_player else "volta"
        reached = False
        if map_name == s.me.map:
            try:
                self.walk_to(x, y, tolerance=3, timeout=120)
                reached = True
            except BotError as e:
                log.info("welcome: nao alcancei %s em (%d,%d): %s", name, x, y, e)
        hello = m["novo" if new_player else "volta"].format(nome=name)
        if reached:
            self.say(hello)
        else:
            self.whisper(name, hello)
        s.pump(2.0)
        result = self.gift(name, kind)
        if result == "PRESENTE_OK":
            text = m["presente"].format(nome=name)
            self.say(text) if reached else self.whisper(name, text)
        log.info("welcome %s (%s): presente=%s alcancado=%s", name, kind, result, reached)
        end = time.monotonic() + stay_seconds
        while time.monotonic() < end:
            s.pump(1.0)
        bye = m["tchau"].format(nome=name)
        if reached:
            self.say(bye)
        else:
            self.whisper(name, bye)
        s.pump(1.0)
        return {"name": name, "kind": kind, "reached": reached, "gift": result}


DEFAULT_MESSAGES = {
    "novo": "Bem-vindo(a) ao FaithRO, {nome}! Eu sou o FaithBot. O Guia aqui em Prontera explica as rates e as regras.",
    "volta": "Bem-vindo(a) de volta, {nome}! Bom jogo!",
    "presente": "Deixei um presente de boas-vindas no seu inventario, {nome}.",
    "tchau": "Vou indo, {nome}. Qualquer duvida, fale com a equipe no site faithro.site. Ate mais!",
}
