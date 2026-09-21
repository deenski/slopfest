from __future__ import annotations

from dataclasses import dataclass, field
import pygame

from .equipment import CARGO_CAPACITY, ENGINE_SPEED, RADAR_RANGE, SHIELDS
from .weapons import WEAPONS


MINERAL_VALUES = {
    "Iron": 5,
    "Silica": 6,
    "Cobalt": 8,
    "Rare Earths": 11,
    "Helium-3": 13,
    "Uranium": 15,
}

SPECIALIZATIONS = (
    "Mining Colony",
    "Trade Hub",
    "Shipyard",
    "Fortress",
    "Research Outpost",
)


@dataclass
class Planet:
    name: str
    pos: pygame.Vector2
    radius: int
    income: int
    mineral: str
    richness: float
    market_factor: float
    lore: str
    population_millions: float = 0.0
    habitability: int = 50
    government: str = "Independent Council"
    climate: str = "Temperate"
    traffic: str = "Light"
    owner: int | None = None
    development: int = 0
    defense: int = 0
    specialization: str | None = None
    garrison: float = 100.0
    infrastructure: float = 100.0
    orbital_cooldown: float = 0.0

    @property
    def settlement_scale(self) -> str:
        if self.population_millions >= 10:
            return "Major world"
        if self.population_millions >= 4:
            return "Established colony"
        if self.population_millions >= 1:
            return "Frontier colony"
        return "Outpost"

    @property
    def strategic_value(self) -> int:
        score = self.current_income * 8 + int(self.richness * 10) + self.development * 9
        score += self.defense * 6 + self.habitability // 10
        if self.specialization is not None:
            score += 12
        return score

    @property
    def colonize_cost(self) -> int:
        return 40 + self.income * 14 + int(self.richness * 9)

    @property
    def development_cost(self) -> int:
        return 45 + self.development * 55

    @property
    def defense_cost(self) -> int:
        return 50 + self.defense * 65

    @property
    def specialization_cost(self) -> int:
        return 130 + self.development * 25

    @property
    def current_income(self) -> int:
        bonus = int(self.development * max(1, self.richness))
        if self.specialization == "Mining Colony":
            bonus += 2 + int(self.richness)
        elif self.specialization == "Trade Hub":
            bonus += 3
        elif self.specialization == "Research Outpost":
            bonus += 1
        return self.income + bonus

    @property
    def mining_multiplier(self) -> float:
        return 1.7 if self.specialization == "Mining Colony" else 1.0

    @property
    def orbital_range(self) -> float:
        base = 360.0 + self.defense * 65.0
        if self.specialization == "Fortress":
            base += 230.0
        return base

    @property
    def orbital_damage(self) -> float:
        base = 3.0 + self.defense * 1.7
        if self.specialization == "Fortress":
            base += 4.0
        return base

    @property
    def radar_range(self) -> float:
        base = 480.0
        if self.specialization == "Fortress":
            base += 170.0
        elif self.specialization == "Research Outpost":
            base += 320.0
        return base

    def base_sell_price(self, mineral: str) -> int:
        base = MINERAL_VALUES[mineral]
        scarcity_bonus = 0.65 if mineral == self.mineral else 1.0
        trade_bonus = 1.28 if self.specialization == "Trade Hub" else 1.0
        return max(1, int(base * self.market_factor * scarcity_bonus * trade_bonus))


@dataclass
class Ship:
    faction_id: int
    pos: pygame.Vector2
    credits: float = 0.0
    max_health: float = 100.0
    health: float = 100.0
    destination: pygame.Vector2 = field(default_factory=pygame.Vector2)
    velocity: pygame.Vector2 = field(default_factory=pygame.Vector2)
    fire_cooldown: float = 0.0
    cargo_mineral: str | None = None
    cargo_amount: int = 0
    weapon_name: str = "Pulse Laser"
    owned_weapons: list[str] = field(default_factory=lambda: ["Pulse Laser"])
    shield_level: int = 1
    engine_level: int = 1
    radar_level: int = 1
    cargo_level: int = 1
    shields: float = 55.0
    last_damage_timer: float = 999.0
    marines: int = 8
    unique_modules: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.destination = self.pos.copy()
        self.shields = self.max_shields

    @property
    def alive(self) -> bool:
        return self.health > 0

    @property
    def speed(self) -> float:
        bonus = 40.0 if "Slipstream Governor" in self.unique_modules else 0.0
        return ENGINE_SPEED[self.engine_level] + bonus

    @property
    def radar_range(self) -> float:
        bonus = 300.0 if "Ghost Compass" in self.unique_modules else 0.0
        return RADAR_RANGE[self.radar_level] + bonus

    @property
    def cargo_capacity(self) -> int:
        return CARGO_CAPACITY[self.cargo_level]

    @property
    def cargo_free(self) -> int:
        return max(0, self.cargo_capacity - self.cargo_amount)

    @property
    def max_shields(self) -> float:
        bonus = 25.0 if "Severance Capacitor" in self.unique_modules else 0.0
        return SHIELDS[self.shield_level]["capacity"] + bonus

    @property
    def shield_regen(self) -> float:
        return SHIELDS[self.shield_level]["regen"]

    @property
    def shield_delay(self) -> float:
        return SHIELDS[self.shield_level]["delay"]

    @property
    def weapon(self):
        return WEAPONS[self.weapon_name]

    @property
    def weapon_damage(self) -> float:
        return self.weapon.damage

    @property
    def weapon_cooldown(self) -> float:
        factor = 0.85 if "Mnemonic Cooler" in self.unique_modules else 1.0
        return self.weapon.cooldown * factor

    @property
    def projectile_speed(self) -> float:
        return self.weapon.projectile_speed

    def move(self, dt: float) -> None:
        if not self.alive:
            return
        delta = self.destination - self.pos
        desired = pygame.Vector2()
        if delta.length_squared() > 25:
            desired = delta.normalize() * self.speed

        response = 3.7 if desired.length_squared() else 6.0
        self.velocity += (desired - self.velocity) * min(1.0, response * dt)
        if delta.length_squared() < 400 and self.velocity.length() > 0:
            self.velocity *= max(0.0, 1.0 - 3.8 * dt)

        self.pos += self.velocity * dt
        if delta.length_squared() < 16 and self.velocity.length_squared() < 16:
            self.pos = self.destination.copy()
            self.velocity.update(0, 0)

    def update(self, dt: float) -> None:
        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)
        self.last_damage_timer += dt
        if self.last_damage_timer >= self.shield_delay and self.shields < self.max_shields:
            self.shields = min(self.max_shields, self.shields + self.shield_regen * dt)

    def take_damage(self, amount: float) -> None:
        self.last_damage_timer = 0.0
        if self.shields > 0:
            absorbed = min(self.shields, amount)
            self.shields -= absorbed
            amount -= absorbed
        if amount > 0:
            self.health = max(0.0, self.health - amount)

    def upgrade_module(self, module_index: int) -> None:
        attrs = ("shield_level", "engine_level", "radar_level", "cargo_level")
        attr = attrs[module_index]
        old_max = self.max_shields
        setattr(self, attr, getattr(self, attr) + 1)
        if module_index == 0:
            self.shields += self.max_shields - old_max


@dataclass
class Bolt:
    owner: int
    pos: pygame.Vector2
    velocity: pygame.Vector2
    damage: float
    ttl: float = 1.35
    source: str = "ship"
    planet_multiplier: float = 1.0

    def update(self, dt: float) -> None:
        self.pos += self.velocity * dt
        self.ttl -= dt


@dataclass
class FactionIdentity:
    faction_name: str = "Wayfarer Compact"
    ship_name: str = "Tax Evasion"
    palette_index: int = 0
    insignia_index: int = 0
