from __future__ import annotations
from dataclasses import dataclass, field
import random
from .model import MINERAL_VALUES, Planet

MINERALS = tuple(MINERAL_VALUES)

@dataclass
class MarketState:
    multipliers: dict[tuple[str, str], float] = field(default_factory=dict)
    timer: float = 0.0
    cycle: int = 0

    @classmethod
    def create(cls, planets: list[Planet], rng: random.Random) -> "MarketState":
        obj = cls()
        for planet in planets:
            for mineral in MINERALS:
                obj.multipliers[(planet.name, mineral)] = rng.uniform(0.88, 1.18)
        return obj

    def update(self, dt: float, planets: list[Planet], rng: random.Random) -> bool:
        self.timer += dt
        if self.timer < 32.0:
            return False
        self.timer -= 32.0
        self.cycle += 1
        for planet in planets:
            for mineral in MINERALS:
                key = (planet.name, mineral)
                old = self.multipliers.get(key, 1.0)
                drift = rng.uniform(-0.10, 0.10)
                mean_pull = (1.0 - old) * 0.12
                self.multipliers[key] = max(0.68, min(1.55, old + drift + mean_pull))
        return True

    def demand_factor(self, planet: Planet, mineral: str) -> float:
        factor = self.multipliers.get((planet.name, mineral), 1.0)
        if mineral == planet.mineral:
            factor *= 0.62
        if planet.specialization == "Trade Hub":
            factor *= 1.18
        elif planet.specialization == "Shipyard" and mineral in ("Iron", "Cobalt", "Rare Earths"):
            factor *= 1.34
        elif planet.specialization == "Fortress" and mineral in ("Cobalt", "Uranium"):
            factor *= 1.25
        elif planet.specialization == "Research Outpost" and mineral in ("Rare Earths", "Helium-3"):
            factor *= 1.35
        return factor

    def sell_price(self, planet: Planet, mineral: str) -> int:
        return max(1, round(MINERAL_VALUES[mineral] * planet.market_factor * self.demand_factor(planet, mineral)))

    def buy_price(self, planet: Planet) -> int:
        retail = self.sell_price(planet, planet.mineral)
        discount = 0.60 if planet.specialization == "Trade Hub" else 0.68
        return max(1, round(retail * discount))

    def best_routes(self, planets: list[Planet], limit: int = 10) -> list[tuple[int, str, str, str, int, int]]:
        routes = []
        for origin in planets:
            mineral = origin.mineral
            buy = self.buy_price(origin)
            for target in planets:
                if target is origin:
                    continue
                sell = self.sell_price(target, mineral)
                profit = sell - buy
                if profit > 0:
                    routes.append((profit, origin.name, target.name, mineral, buy, sell))
        routes.sort(reverse=True, key=lambda r: r[0])
        return routes[:limit]
