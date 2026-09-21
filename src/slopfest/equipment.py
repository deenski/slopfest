from __future__ import annotations

MODULE_NAMES = ("Shields", "Engine", "Radar", "Cargo")
MAX_MODULE_LEVEL = 4

UPGRADE_COSTS = {1: 110, 2: 190, 3: 310}

SHIELDS = {
    1: {"capacity": 55.0, "regen": 6.0, "delay": 3.0},
    2: {"capacity": 80.0, "regen": 8.0, "delay": 2.8},
    3: {"capacity": 110.0, "regen": 10.5, "delay": 2.5},
    4: {"capacity": 145.0, "regen": 13.0, "delay": 2.2},
}
ENGINE_SPEED = {1: 310.0, 2: 350.0, 3: 395.0, 4: 445.0}
RADAR_RANGE = {1: 825.0, 2: 1025.0, 3: 1275.0, 4: 1600.0}
CARGO_CAPACITY = {1: 30, 2: 45, 3: 65, 4: 90}


def upgrade_cost(current_level: int) -> int | None:
    if current_level >= MAX_MODULE_LEVEL:
        return None
    return UPGRADE_COSTS[current_level]
