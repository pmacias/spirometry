"""Write tests/fixtures/sample_runs.jsonl: seven synthetic run records.

Nothing here comes from a real run. Hashes, seeds, times, HP, gold, decks and offers are
generated from a fixed random seed; only the game's own ids (cards, relics, encounters,
builds) are real, because the parser checks them against the game's lists. The shape follows
notes/run_schema.md, and the floors are laid out to cover the cases tests/test_runs.py pins.

    python tests/fixtures/make_sample_runs.py
"""
import copy
import hashlib
import json
import pathlib
import random
import re

OUT = pathlib.Path(__file__).with_name("sample_runs.jsonl")

ACTS = ["ACT.OVERGROWTH", "ACT.HIVE", "ACT.GLORY"]
COLORLESS = ["BELIEVE_IN_YOU", "ETERNAL_ARMOR", "FASTEN", "SEEKER_STRIKE"]
POOL = {
    "REGENT": ["BULWARK", "COLLISION_COURSE", "CRESCENT_SPEAR", "FURNACE", "GATHER_LIGHT",
               "GLITTERSTREAM", "HEIRLOOM_HAMMER", "I_AM_INVINCIBLE", "KINGLY_KICK", "PARRY",
               "PATTER", "REFINE_BLADE", "REFLECT", "ROYALTIES", "SOLAR_STRIKE",
               "WROUGHT_IN_WAR"],
    "SILENT": ["ANTICIPATE", "CORROSIVE_WAVE", "FLICK_FLACK", "GRAND_FINALE", "LEADING_STRIKE",
               "MEMENTO_MORI", "PINPOINT", "POUNCE", "SERPENT_FORM", "SKEWER", "UNTOUCHABLE"],
    "NECROBINDER": ["DANSE_MACABRE", "DEATH_MARCH", "DEBILITATE", "SCULPTING_STRIKE", "SIC_EM",
                    "THE_SCYTHE"],
    "IRONCLAD": ["FIGHT_ME", "HEMOKINESIS", "JUGGERNAUT", "UNRELENTING"],
    "DEFECT": ["HYPERBEAM", "SYNTHESIS", "UPROAR"],
}
START_CARDS = {"SILENT": 12}                        # everyone else starts with 10
FIGHTS = {
    "monster": [("SEAPUNK_WEAK", ["SEAPUNK"]), ("NIBBITS_WEAK", ["NIBBIT"]),
                ("SLIMES_WEAK", ["LEAF_SLIME_S", "TWIG_SLIME_S"]),
                ("TUNNELER_NORMAL", ["TUNNELER"]), ("MYTES_NORMAL", ["MYTE", "MYTE"]),
                ("AXEBOTS_NORMAL", ["AXEBOT", "AXEBOT"]), ("LIVING_FOG_NORMAL", ["LIVING_FOG"]),
                ("CULTISTS_NORMAL", ["CALCIFIED_CULTIST", "DAMP_CULTIST"]),
                ("SEWER_CLAM_NORMAL", ["SEWER_CLAM"])],
    "elite": [("BYGONE_EFFIGY_ELITE", ["BYGONE_EFFIGY"]), ("TERROR_EEL_ELITE", ["TERROR_EEL"]),
              ("SOUL_NEXUS_ELITE", ["SOUL_NEXUS"]), ("MECHA_KNIGHT_ELITE", ["MECHA_KNIGHT"])],
    "boss": [("LAGAVULIN_MATRIARCH_BOSS", ["LAGAVULIN_MATRIARCH"]),
             ("THE_INSATIABLE_BOSS", ["THE_INSATIABLE"]), ("DOORMAKER_BOSS", ["DOOR"])],
}
EVENTS = ["DROWNING_BEACON", "POTION_COURIER", "SELF_HELP_BOOK", "WHISPERING_HOLLOW"]
RELICS = ["ANCHOR", "BAG_OF_MARBLES", "CANDELABRA", "LEES_WAFFLE", "MEAL_TICKET", "PEN_NIB",
          "PERMAFROST", "REGALITE", "TOOLBOX", "WHETSTONE"]
POTIONS = ["BLOCK_POTION", "ENERGY_POTION", "FIRE_POTION", "SPEED_POTION", "WEAK_POTION"]


def run_hash(prefix, label):
    """16 hex characters. The prefix fixes the sort order tests/test_runs.py relies on."""
    return prefix + hashlib.sha256(label.encode()).hexdigest()[:16 - len(prefix)]


class Run:
    """Builds one record floor by floor, keeping decks, HP and gold consistent."""

    def __init__(self, label, prefix, seed, start_time, build, schema, ascension, characters):
        self.rng = random.Random(label)
        self.schema, self.floor = schema, 0
        self.ids = [1] if len(characters) == 1 else [1001 + i for i in range(len(characters))]
        self.chars = dict(zip(self.ids, characters))
        self.deck, self.relics = {}, {pid: [] for pid in self.ids}
        self.hp, self.gold = dict.fromkeys(self.ids, 70), dict.fromkeys(self.ids, 99)
        for pid, char in self.chars.items():
            n = START_CARDS.get(char, 10)
            cards = [f"STRIKE_{char}"] * (n // 2) + [f"DEFEND_{char}"] * (n - n // 2)
            cards += ["ASCENDERS_BANE"] * (ascension >= 5)
            self.deck[pid] = [{"id": f"CARD.{c}", "floor_added_to_deck": 1} for c in cards]
        self.history = []
        self.record = dict(
            acts=ACTS, ascension=ascension, build_id=build, game_mode="standard",
            killed_by_encounter="NONE.NONE", killed_by_event="NONE.NONE",
            map_point_history=self.history, modifiers=[], platform_type="steam",
            run_hash=run_hash(prefix, label), run_time=self.rng.randint(600, 3600),
            schema_version=schema, seed=seed, start_time=start_time, was_abandoned=False,
            win=False)

    def stats(self, pid, damage=0):
        gained = self.rng.randint(10, 25) if damage else 0
        self.hp[pid] = max(1, self.hp[pid] - damage)
        self.gold[pid] += gained
        st = dict(player_id=pid, current_hp=self.hp[pid], max_hp=70, damage_taken=damage,
                  hp_healed=0, max_hp_gained=0, max_hp_lost=0, current_gold=self.gold[pid],
                  gold_gained=gained, gold_lost=0, gold_spent=0, gold_stolen=0)
        if self.schema >= 10:
            st.update(stolen_loot=0, is_affected_by_fur_coat=False)
        return st

    def add_floor(self, map_point_type, rooms, stats):
        self.history[-1].append(dict(map_point_type=map_point_type, rooms=rooms,
                                     player_stats=stats))

    def card(self, cid, upgraded):
        return {"id": f"CARD.{cid}", **({"current_upgrade_level": 1} if upgraded else {})}

    def gain(self, st, card):
        """Add `card` to the player's final deck and the floor's cards_gained."""
        st.setdefault("cards_gained", []).append(dict(card))
        self.deck[st["player_id"]].append({**card, "floor_added_to_deck": self.floor})

    def offers(self, st, screens, char, extra=None):
        """One list of 3-card screens; `screens` says, per screen, whether a card is picked.
        `extra` replaces the first offer of the first unpicked screen (see the PREPARE run)."""
        pool, up = POOL[char], len(self.history) > 1 and self.rng.random() < 0.4
        out = []
        for picked in screens:
            names = self.rng.sample(pool, 3)
            if extra and not picked:
                names[0], extra = extra, None
            at = self.rng.randrange(3) if picked else None
            for i, name in enumerate(names):
                c = self.card(name, up)
                if i == at:
                    self.gain(st, c)
                    c = {**c, "floor_added_to_deck": self.floor}
                out.append({"card": c, "was_picked": i == at})
        return out

    def fight(self, kind, screens=(), last=False, encounter=None, extra=None):
        """A fight. `screens` as in offers(); empty means no reward (the run ended here)."""
        self.floor += 1
        name, monsters = encounter or self.rng.choice(FIGHTS[kind])
        stats = []
        for pid, char in self.chars.items():
            st = self.stats(pid, self.rng.randint(0, 8))
            if screens:
                st["card_choices"] = self.offers(st, screens, char, extra)
            if not last and self.rng.random() < 0.3:
                st["potion_choices"] = [{"choice": f"POTION.{self.rng.choice(POTIONS)}",
                                         "was_picked": self.rng.random() < 0.5}]
            stats.append(st)
        self.add_floor(kind, [{"model_id": f"ENCOUNTER.{name}", "room_type": kind,
                               "monster_ids": [f"MONSTER.{m}" for m in monsters],
                               "turns_taken": self.rng.randint(2, 7)}], stats)
        if last:
            self.record["killed_by_encounter"] = f"ENCOUNTER.{name}"

    def ancient(self, event="NEOW", offered=0, gained=0):
        """The opening Neow floor, or a later ancient: a relic, and optionally cards."""
        self.floor += 1
        stats = []
        for pid, char in self.chars.items():
            st = self.stats(pid)
            names = self.rng.sample(RELICS, 3)
            st["ancient_choice"] = [{"TextKey": n, "title": {"key": f"{n}.title", "table": "relics"},
                                     "was_chosen": i == 0} for i, n in enumerate(names)]
            st["event_choices"] = [{"title": {"key": f"{names[0]}.title", "table": "relics"}}]
            st["relic_choices"] = [{"choice": f"RELIC.{names[0]}", "was_picked": True}]
            self.relics[pid].append({"id": f"RELIC.{names[0]}",
                                     "floor_added_to_deck": self.floor})
            cards = self.rng.sample(POOL[char], offered + gained)
            if offered:
                st["card_choices"] = [{"card": self.card(c, False), "was_picked": False}
                                      for c in cards[:offered]]
            for c in cards[offered:]:
                self.gain(st, self.card(c, False))
            stats.append(st)
        self.add_floor("ancient", [{"model_id": f"EVENT.{event}", "room_type": "event",
                                    "turns_taken": 0}], stats)

    def shop(self, shelf, bought=(), colorless=()):
        """A solo shop: `shelf` cards left unsold, the bought ones only in cards_gained."""
        self.floor += 1
        pid, char = self.ids[0], self.chars[self.ids[0]]
        st = self.stats(pid)
        names = self.rng.sample(POOL[char], min(shelf, len(POOL[char])))
        st["card_choices"] = [{"card": self.card(n, False), "was_picked": False} for n in names]
        for name in (*bought, *colorless):
            self.gain(st, self.card(name, False))
        if colorless:
            st["bought_colorless"] = [f"CARD.{n}" for n in colorless]
        st["gold_spent"] = 40 * (len(bought) + len(colorless))
        self.add_floor("shop", [{"room_type": "shop", "turns_taken": 0}], [st])

    def event(self, offered=0):
        self.floor += 1
        name = self.rng.choice(EVENTS)
        stats = []
        for pid, char in self.chars.items():
            st = self.stats(pid)
            st["event_choices"] = [{"title": {"key": f"{name}.pages.INITIAL.options.LEAVE.title",
                                              "table": "events"}}]
            if offered:
                st["card_choices"] = [{"card": self.card(c, False), "was_picked": False}
                                      for c in self.rng.sample(POOL[char], offered)]
            stats.append(st)
        self.add_floor("unknown", [{"model_id": f"EVENT.{name}", "room_type": "event",
                                    "turns_taken": 0}], stats)

    def rest(self):
        self.floor += 1
        stats = []
        for pid in self.ids:
            st = self.stats(pid)
            st["rest_site_choices"] = ["HEAL"]
            stats.append(st)
        self.add_floor("rest_site", [{"room_type": "rest_site", "turns_taken": 0}], stats)

    def treasure(self):
        self.floor += 1
        stats = []
        for pid in self.ids:
            st = self.stats(pid)
            relic = self.rng.choice(RELICS)
            st["relic_choices"] = [{"choice": f"RELIC.{relic}", "was_picked": True}]
            self.relics[pid].append({"id": f"RELIC.{relic}", "floor_added_to_deck": self.floor})
            stats.append(st)
        self.add_floor("treasure", [{"room_type": "treasure", "turns_taken": 0}], stats)

    def new_act(self):
        self.history.append([])

    def done(self, **fields):
        self.record.update(fields)
        self.record["players"] = [
            dict(character=f"CHARACTER.{self.chars[pid]}", deck=self.deck[pid], id=pid,
                 max_potion_slot_count=3, potions=[], relics=self.relics[pid])
            for pid in self.ids]
        return self.record


def solo_win():
    r = Run("win", "2", "SYNTHWIN0001", 1773200000, "v0.98.3", 8, 7, ["REGENT"])
    r.new_act()
    r.ancient()
    for picks in (1, 1):
        r.fight("monster", [picks])
    r.shop(6, bought=["BULWARK"])
    for picks in (1, 0):
        r.fight("monster", [picks])
    r.fight("elite", [1])
    r.rest()
    for picks in (1, 1, 1, 1):
        r.fight("monster", [picks])
    r.treasure()
    r.fight("elite", [0])
    r.fight("boss", [1], encounter=FIGHTS["boss"][0])
    r.new_act()
    r.ancient("OROBAS")
    for picks in (1, 0):
        r.fight("monster", [picks])
    r.shop(6, bought=["PARRY"], colorless=["FASTEN"])
    for picks in (1, 0, 0, 1):
        r.fight("monster", [picks])
    r.fight("elite", [0])
    r.shop(6)
    r.fight("boss", [0], encounter=FIGHTS["boss"][1])
    r.new_act()
    r.ancient("TANX")
    for picks in (0, 1, 0, 0, 0):
        r.fight("monster", [picks])
    r.event(offered=3)
    r.shop(6, bought=["REFLECT"])
    r.fight("elite", [0])
    r.rest()
    r.fight("boss", encounter=FIGHTS["boss"][2])
    # a game enchantment on one offer: the mod check must leave it alone
    first_list = r.history[0][1]["player_stats"][0]["card_choices"]
    first_list[0]["card"]["enchantment"] = {"id": "ENCHANTMENT.NIMBLE", "amount": 2}
    return r.done(win=True)


def six_card_loss():
    """A loss on a build with two reward screens per fight (a 6-card list)."""
    r = Run("six", "3", "SYNTHSIX0002", 1774000000, "v0.100.0", 8, 6, ["SILENT"])
    r.new_act()
    r.ancient(offered=2)
    r.fight("monster", [1, 1])
    r.fight("monster", [1, 0])
    r.fight("monster", [1, 0])
    r.treasure()
    r.event()
    r.shop(6, bought=["POUNCE"])
    r.fight("monster", [0, 0])
    r.fight("elite", last=True)
    return r.done()


def abandoned_mid_fight():
    r = Run("abandoned", "4", "SYNTHABN0003", 1773300000, "v0.98.3", 8, 3, ["DEFECT"])
    r.new_act()
    r.ancient()
    r.fight("monster", [1])
    r.fight("monster", [1])
    r.fight("monster", [1], last=True)
    return r.done(was_abandoned=True)


def coop_loss():
    """Two players, Steam-style ids replaced by 1001 and 1002 as the tests expect."""
    r = Run("coop", "1", "SYNTHCOP0004", 1773900000, "v0.99.1", 8, 4, ["NECROBINDER", "IRONCLAD"])
    r.new_act()
    r.ancient()
    r.fight("monster", [1])
    r.fight("monster", [1])
    r.event()
    r.fight("monster", [1])
    r.fight("elite", last=True)
    return r.done()


def beta_card_run():
    """An abandoned beta run offered PREPARE, a card that never reached the card list."""
    r = Run("prepare", "5", "SYNTHPRE0005", 1774100000, "v0.100.0", 8, 8, ["SILENT"])
    r.new_act()
    r.ancient()
    for screens in ([1], [1], [1], [1]):
        r.fight("monster", screens)
    # the offer goes on an unpicked slot of the second fight
    choices = r.history[0][2]["player_stats"][0]["card_choices"]
    next(c for c in choices if not c["was_picked"])["card"] = {"id": "CARD.PREPARE"}
    r.fight("monster", last=True)
    return r.done(was_abandoned=True)


def schema10_run():
    r = Run("schema10", "ab", "SYNTHS100006", 1790000000, "v0.111.0", 10, 10, ["NECROBINDER"])
    r.new_act()
    r.ancient(gained=1)
    r.fight("monster", [1])
    r.fight("monster", [1])
    r.event()
    r.fight("monster", [1])
    r.fight("monster", last=True)
    rec = r.done(_sts="slay-the-stats/v0.0.0")
    rec["players"][0]["badges"] = []
    return rec


def main():
    records = [solo_win(), six_card_loss(), abandoned_mid_fight(), coop_loss(), beta_card_run(),
               schema10_run()]
    # The same run uploaded again: another run_hash and no uploader tag.
    copy_of = copy.deepcopy(records[-1])
    del copy_of["_sts"]
    copy_of["run_hash"] = run_hash("c", "schema10-copy")
    records.append(copy_of)
    text = "\n".join(json.dumps(r, sort_keys=True) for r in records) + "\n"
    assert not re.search(r"\d{15,}", text) and "1001" not in "".join(
        r["run_hash"] for r in records)
    OUT.write_text(text)
    for name, r in zip(("WIN", "SIX", "ABANDONED", "COOP", "PREPARE", "SCHEMA10",
                        "SCHEMA10_COPY"), records):
        print(f"{name:14} {r['run_hash']} {r['seed']} {r['start_time']}")


if __name__ == "__main__":
    main()
