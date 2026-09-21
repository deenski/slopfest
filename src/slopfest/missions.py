from __future__ import annotations
from dataclasses import dataclass, field
import random
from .model import Planet

@dataclass
class Mission:
    mission_id: int
    kind: str
    title: str
    description: str
    origin_name: str
    target_name: str | None
    mineral: str | None
    amount: int
    reward: int
    status: str = "available"
    pirate_kill_start: int = 0

    @property
    def short_status(self) -> str:
        return self.status.upper()

@dataclass
class MissionBoard:
    next_id: int = 1
    boards: dict[str, list[Mission]] = field(default_factory=dict)
    active: list[Mission] = field(default_factory=list)
    completed: int = 0
    pirate_kills: int = 0

    def _make(self, kind, title, description, origin_name, target_name, mineral, amount, reward) -> Mission:
        mission = Mission(self.next_id, kind, title, description, origin_name, target_name, mineral, amount, reward)
        self.next_id += 1
        return mission

    def contracts_for(self, origin: Planet, planets: list[Planet], rng: random.Random) -> list[Mission]:
        if origin.name in self.boards:
            return self.boards[origin.name]
        others = [p for p in planets if p.name != origin.name]
        rng.shuffle(others)
        missions: list[Mission] = []
        if others:
            target = others[0]
            distance = origin.pos.distance_to(target.pos)
            missions.append(self._make(
                "courier", f"Courier run to {target.name}",
                f"Carry sealed Wayline correspondence to {target.name}.",
                origin.name, target.name, None, 0, 55 + int(distance / 65)
            ))
        if len(others) > 1:
            target = others[1]
            amount = rng.randint(4, 8)
            missions.append(self._make(
                "delivery", f"Deliver {amount} {origin.mineral}",
                f"Deliver {amount} units of {origin.mineral} to {target.name}.",
                origin.name, target.name, origin.mineral, amount, 80 + amount * 11
            ))
        missions.append(self._make(
            "bounty", "Pirate suppression", "Destroy one unaffiliated raider vessel.",
            origin.name, None, None, 1, 145
        ))
        self.boards[origin.name] = missions
        return missions

    def accept(self, mission: Mission) -> bool:
        if mission.status != "available":
            return False
        mission.status = "active"
        if mission.kind == "bounty":
            mission.pirate_kill_start = self.pirate_kills
        self.active.append(mission)
        return True

    def note_pirate_kill(self) -> list[Mission]:
        self.pirate_kills += 1
        completed = []
        for mission in list(self.active):
            if mission.kind == "bounty" and self.pirate_kills > mission.pirate_kill_start:
                mission.status = "completed"
                self.active.remove(mission)
                self.completed += 1
                completed.append(mission)
        return completed

    def arrive(self, planet: Planet, cargo_mineral: str | None, cargo_amount: int):
        completed = []
        consume = 0
        reward = 0
        for mission in list(self.active):
            if mission.target_name != planet.name:
                continue
            if mission.kind == "courier":
                pass
            elif mission.kind == "delivery":
                if cargo_mineral != mission.mineral or cargo_amount < mission.amount:
                    continue
                consume += mission.amount
            else:
                continue
            mission.status = "completed"
            self.active.remove(mission)
            self.completed += 1
            completed.append(mission)
            reward += mission.reward
        return completed, consume, reward
