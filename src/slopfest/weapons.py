from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WeaponSpec:
    name: str
    price: int
    damage: float
    cooldown: float
    projectile_speed: float
    projectile_ttl: float
    planet_multiplier: float
    description: str


WEAPONS: dict[str, WeaponSpec] = {
    "Pulse Laser": WeaponSpec(
        "Pulse Laser", 0, 8.0, 0.18, 720.0, 1.35, 1.0,
        "Reliable general-purpose emitter. Cheap, quick, boring in the comforting way.",
    ),
    "Twin Laser": WeaponSpec(
        "Twin Laser", 180, 6.2, 0.095, 765.0, 1.25, 0.85,
        "High sustained fire. Excellent against ships, less impressive against hardened worlds.",
    ),
    "Heavy Blaster": WeaponSpec(
        "Heavy Blaster", 260, 18.0, 0.42, 575.0, 1.55, 1.55,
        "Slow, ugly packets of bad news. Particularly effective during bombardment.",
    ),
    "Relay Lance": WeaponSpec(
        "Relay Lance", 475, 25.0, 0.62, 1050.0, 1.20, 1.30,
        "Pre-Severance targeting geometry wrapped around a modern power feed. Expensive and rude.",
    ),
}


def inventory_for_planet(specialization: str | None) -> list[str]:
    inventory = ["Pulse Laser", "Twin Laser"]
    if specialization in ("Shipyard", "Fortress", "Trade Hub"):
        inventory.append("Heavy Blaster")
    if specialization in ("Research Outpost", "Shipyard"):
        inventory.append("Relay Lance")
    return inventory
