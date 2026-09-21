from __future__ import annotations

import pygame

from .assets import ASSETS, unique_asset_name, weapon_asset_name


_CACHE: dict[tuple[tuple[int, int, int], tuple[int, int, int], bool], pygame.Surface] = {}
_PLAYER_CACHE: dict[tuple, pygame.Surface] = {}


PLAYER_PATTERN = (
    ".......A........",
    "......AAA.......",
    ".....APAPA......",
    "....AAPAPAA.....",
    "...AAPPPPAA.....",
    "..AAPPPPPPAA....",
    ".AAPPPPPPPPAA...",
    "AAPPPPPPPPPPAA..",
    "..APPPPPPPPA....",
    "...APPPPPPPA....",
    "...AAAPPPAAA....",
    "....A.PP.A......",
    ".....P..P.......",
    "....E....E......",
    "................",
    "................",
)

ENEMY_PATTERN = (
    "......RRR.......",
    ".....RPRPR......",
    "...RRPPPPPRR....",
    "..RPPPRRPPPPR...",
    ".RPPPPRRPPPPPR..",
    "RPPPPPRRPPPPPPR.",
    ".RRPPPPPPPPPPRR.",
    "...RPPPPPPPPR...",
    "...RRPPPPPRR....",
    "..R.RPPPPPR.R...",
    ".R...RPPPR...R..",
    ".....RPPPR......",
    "......PPP.......",
    ".....E...E......",
    "................",
    "................",
)


def _make_sprite(
    primary: tuple[int, int, int],
    accent: tuple[int, int, int],
    enemy: bool,
) -> pygame.Surface:
    key = (primary, accent, enemy)
    if key in _CACHE:
        return _CACHE[key]

    pattern = ENEMY_PATTERN if enemy else PLAYER_PATTERN
    surf = pygame.Surface((16, 16), pygame.SRCALPHA)
    engine = (255, 181, 78)
    for y, row in enumerate(pattern):
        for x, ch in enumerate(row):
            if ch in ("P", "R"):
                surf.set_at((x, y), primary)
            elif ch == "A":
                surf.set_at((x, y), accent)
            elif ch == "E":
                surf.set_at((x, y), engine)

    _CACHE[key] = surf
    return surf


def _recolor_base(source: pygame.Surface, primary: tuple[int, int, int], accent: tuple[int, int, int]) -> pygame.Surface:
    result = source.copy()
    for x in range(result.get_width()):
        for y in range(result.get_height()):
            c = result.get_at((x, y))
            if c.a == 0:
                continue
            if c.r > 225 and c.g > 225 and c.b > 225:
                result.set_at((x, y), (*primary, c.a))
            elif 75 <= c.r <= 120 and 90 <= c.g <= 145:
                result.set_at((x, y), (*accent, c.a))
    return result


def player_ship_surface(ship, primary: tuple[int, int, int], accent: tuple[int, int, int]) -> pygame.Surface:
    """Compose the visible player ship from base hull + installed hardware assets."""
    key = (
        primary,
        accent,
        ship.weapon_name,
        ship.shield_level,
        ship.engine_level,
        ship.radar_level,
        ship.cargo_level,
        tuple(sorted(ship.unique_modules)),
    )
    if key in _PLAYER_CACHE:
        return _PLAYER_CACHE[key]

    composed = _recolor_base(ASSETS.image("ship/base.png"), primary, accent)
    overlays = [
        f"ship/weapon_{weapon_asset_name(ship.weapon_name)}.png",
        f"ship/engine_t{ship.engine_level}.png",
        f"ship/shield_t{ship.shield_level}.png",
        f"ship/radar_t{ship.radar_level}.png",
        f"ship/cargo_t{ship.cargo_level}.png",
    ]
    overlays.extend(f"ship/unique_{unique_asset_name(name)}.png" for name in ship.unique_modules)
    for relative in overlays:
        composed.blit(ASSETS.image(relative), (0, 0))

    _PLAYER_CACHE[key] = composed
    return composed


def draw_ship(
    target: pygame.Surface,
    center: pygame.Vector2,
    heading: pygame.Vector2,
    primary: tuple[int, int, int],
    accent: tuple[int, int, int],
    enemy: bool = False,
    ship=None,
    scale: int = 2,
) -> None:
    if not enemy and ship is not None:
        sprite = player_ship_surface(ship, primary, accent)
    else:
        sprite = _make_sprite(primary, accent, enemy)

    angle = 0.0
    if heading.length_squared() > 0.01:
        angle = heading.angle_to(pygame.Vector2(0, -1))
    quantized = round(angle / 22.5) * 22.5
    rotated = pygame.transform.rotate(sprite, quantized)
    scaled = pygame.transform.scale(
        rotated,
        (rotated.get_width() * scale, rotated.get_height() * scale),
    )
    rect = scaled.get_rect(center=(round(center.x), round(center.y)))
    target.blit(scaled, rect)
