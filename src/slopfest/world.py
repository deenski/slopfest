from __future__ import annotations

import random
import pygame

from .lore import LORE_FRAGMENTS
from .model import Planet


WORLD_SIZE = pygame.Vector2(6000, 6000)


class World:
    def __init__(self, seed: int = 97, planet_count: int = 34) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self.stars = [
            pygame.Vector2(
                self.rng.uniform(0, WORLD_SIZE.x),
                self.rng.uniform(0, WORLD_SIZE.y),
            )
            for _ in range(900)
        ]
        self.nebulae = [
            (
                pygame.Vector2(
                    self.rng.uniform(200, WORLD_SIZE.x - 200),
                    self.rng.uniform(200, WORLD_SIZE.y - 200),
                ),
                self.rng.randint(140, 320),
            )
            for _ in range(10)
        ]
        self.planets = self._make_planets(planet_count)

    def _make_planets(self, count: int) -> list[Planet]:
        planets: list[Planet] = []
        syllables_a = ["Ar", "Bel", "Cy", "Dr", "El", "Fen", "Gal", "Hel", "Io", "Jor", "Kai", "Lux"]
        syllables_b = ["adon", "aris", "ora", "ion", "eth", "os", "ara", "une", "yx", "eron"]
        minerals = ["Iron", "Silica", "Uranium", "Helium-3", "Cobalt", "Rare Earths"]
        governments = [
            "Charter Council", "Merchant Compact", "Cooperative Assembly",
            "Civic Directorate", "Settlement Board", "Relay Wardens",
        ]
        climates = ["Temperate", "Arid", "Frozen", "Oceanic", "Stormbound", "Barren", "Tidal"]
        traffic_levels = ["Sparse", "Light", "Moderate", "Busy"]

        attempts = 0
        while len(planets) < count and attempts < 5000:
            attempts += 1
            pos = pygame.Vector2(
                self.rng.uniform(350, WORLD_SIZE.x - 350),
                self.rng.uniform(350, WORLD_SIZE.y - 350),
            )
            if any(pos.distance_to(p.pos) < 300 for p in planets):
                continue

            name = self.rng.choice(syllables_a) + self.rng.choice(syllables_b)
            if any(p.name == name for p in planets):
                name += str(len(planets) + 1)

            lore = self.rng.choice(LORE_FRAGMENTS)
            # Metadata uses an independent RNG so adding informational fields never
            # changes the legacy galaxy layout for an existing seed/save.
            meta_rng = random.Random(f"{self.seed}:{name}:{len(planets)}")
            planets.append(
                Planet(
                    name=name,
                    pos=pos,
                    radius=self.rng.randint(18, 34),
                    income=self.rng.randint(1, 5),
                    mineral=self.rng.choice(minerals),
                    richness=round(self.rng.uniform(0.7, 2.0), 1),
                    market_factor=round(self.rng.uniform(0.75, 1.55), 2),
                    lore=lore,
                    population_millions=round(meta_rng.uniform(0.2, 12.0), 1),
                    habitability=meta_rng.randint(28, 94),
                    government=meta_rng.choice(governments),
                    climate=meta_rng.choice(climates),
                    traffic=meta_rng.choice(traffic_levels),
                )
            )

        return planets
