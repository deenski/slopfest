from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Faction:
    faction_id: int
    name: str
    primary: tuple[int, int, int]
    accent: tuple[int, int, int]
    personality: str
    credits: float = 180.0
    relation: int = 0
    treaty: str = "neutral"
    home_name: str = ""
    respawn_timer: float = 0.0

    @property
    def state_name(self) -> str:
        if self.treaty == "war":
            return "HOSTILE"
        if self.treaty == "alliance":
            return "ALLIED"
        if self.treaty == "trade":
            return "TRADE PARTNER"
        if self.relation <= -25:
            return "UNFRIENDLY"
        if self.relation >= 35:
            return "FRIENDLY"
        return "NEUTRAL"

    @property
    def hostile(self) -> bool:
        return self.treaty == "war"

    def adjust_relation(self, amount: int) -> None:
        self.relation = max(-100, min(100, self.relation + amount))


FACTION_BLUEPRINTS = (
    ("Cobalt Assembly", (255, 91, 100), (255, 210, 215), "expansionist", -58, "war"),
    ("Free Meridian", (255, 190, 70), (255, 242, 180), "merchant", 18, "neutral"),
    ("Outer Relay Cooperative", (150, 110, 255), (225, 210, 255), "researcher", 8, "neutral"),
    ("Orison Mutual", (105, 235, 145), (220, 255, 230), "defender", 28, "neutral"),
)


def make_factions() -> dict[int, Faction]:
    result: dict[int, Faction] = {}
    for faction_id, row in enumerate(FACTION_BLUEPRINTS, start=1):
        name, primary, accent, personality, relation, treaty = row
        result[faction_id] = Faction(
            faction_id=faction_id,
            name=name,
            primary=primary,
            accent=accent,
            personality=personality,
            relation=relation,
            treaty=treaty,
        )
    return result
