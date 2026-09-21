from __future__ import annotations

from dataclasses import dataclass
import pygame


SECTOR_SIZE = 1000


@dataclass(frozen=True)
class SectorInfo:
    label: str
    col: int
    row: int
    known_worlds: int
    friendly_worlds: int
    neutral_worlds: int
    hostile_worlds: int
    known_sites: int
    hostile_ships: int
    pirates: int
    risk: str


def sector_coords(pos: pygame.Vector2) -> tuple[int, int]:
    return int(pos.x // SECTOR_SIZE), int(pos.y // SECTOR_SIZE)


def sector_label(pos: pygame.Vector2) -> str:
    col, row = sector_coords(pos)
    return f"{chr(ord('A') + max(0, min(25, col)))}{row + 1}"


def sector_bounds(pos: pygame.Vector2) -> pygame.Rect:
    col, row = sector_coords(pos)
    return pygame.Rect(col * SECTOR_SIZE, row * SECTOR_SIZE, SECTOR_SIZE, SECTOR_SIZE)


def hostility_label(owner: int | None, factions: dict, player_id: int = 0) -> tuple[str, tuple[int,int,int]]:
    if owner is None:
        return "INDEPENDENT", (172, 165, 140)
    if owner == player_id:
        return "YOUR TERRITORY", (92, 235, 148)
    faction = factions.get(owner)
    if faction is None:
        return "UNKNOWN", (170, 170, 180)
    if faction.treaty == "war":
        return f"HOSTILE • {faction.relation:+d}", (255, 91, 100)
    if faction.treaty == "alliance":
        return f"ALLIED • {faction.relation:+d}", (92, 235, 148)
    if faction.treaty == "trade":
        return f"TRADE PACT • {faction.relation:+d}", (255, 205, 92)
    if faction.relation <= -25:
        return f"UNFRIENDLY • {faction.relation:+d}", (255, 145, 67)
    if faction.relation >= 35:
        return f"FRIENDLY • {faction.relation:+d}", (105, 220, 205)
    return f"NEUTRAL • {faction.relation:+d}", (170, 180, 195)


def summarize_sector(game, pos: pygame.Vector2) -> SectorInfo:
    bounds = sector_bounds(pos)
    col, row = sector_coords(pos)
    known = [p for p in game.world.planets if game.planet_visible(p) and bounds.collidepoint(p.pos.x, p.pos.y)]
    friendly = sum(1 for p in known if p.owner == 0)
    neutral = sum(1 for p in known if p.owner is None)
    hostile = sum(1 for p in known if p.owner in game.factions and game.factions[p.owner].hostile)
    sites = sum(1 for s in game.sites if s.discovered and bounds.collidepoint(s.pos.x, s.pos.y))
    hostile_ships = sum(
        1 for s in game.ai_ships.values()
        if s.alive and game.ship_visible(s)
        and s.faction_id in game.factions and game.factions[s.faction_id].hostile
        and bounds.collidepoint(s.pos.x, s.pos.y)
    )
    pirates = sum(
        1 for s in game.pirates
        if s.alive and game.ship_visible(s) and bounds.collidepoint(s.pos.x, s.pos.y)
    )
    pressure = hostile * 2 + hostile_ships * 3 + pirates * 2
    risk = "LOW" if pressure == 0 else "GUARDED" if pressure <= 3 else "DANGEROUS" if pressure <= 7 else "SEVERE"
    return SectorInfo(
        label=f"{chr(ord('A') + max(0, min(25, col)))}{row + 1}",
        col=col,
        row=row,
        known_worlds=len(known),
        friendly_worlds=friendly,
        neutral_worlds=neutral,
        hostile_worlds=hostile,
        known_sites=sites,
        hostile_ships=hostile_ships,
        pirates=pirates,
        risk=risk,
    )
