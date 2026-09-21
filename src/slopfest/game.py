from __future__ import annotations

import math
import random
import pygame

from .camera import Camera
from .equipment import MAX_MODULE_LEVEL, MODULE_NAMES, upgrade_cost
from .factions import Faction, make_factions
from .lore import SETTING_BLURB
from .model import Bolt, FactionIdentity, Planet, Ship, SPECIALIZATIONS
from .pixel_art import draw_ship as draw_pixel_ship, player_ship_surface
from .settings import Settings
from .weapons import WEAPONS, inventory_for_planet
from .world import World, WORLD_SIZE
from .economy import MarketState
from .missions import Mission, MissionBoard
from .discoveries import Site, generate_sites
from .match_config import MatchConfig, GALAXY_OPTIONS, RIVAL_OPTIONS, CREDIT_OPTIONS
from .savegame import has_save, read_save, write_save
from .sound import SoundManager
from .assets import ASSETS, mineral_asset_name, specialization_asset_name, weapon_asset_name, unique_asset_name
from .intel import SECTOR_SIZE, hostility_label, sector_bounds, sector_label, summarize_sector


SCREEN_SIZE = (1280, 720)
FPS = 120
PLAYER = 0
PIRATE = -1

BACKGROUND = (4, 7, 14)
TEXT = (225, 234, 246)
MUTED = (138, 153, 172)
NEUTRAL_COLOR = (165, 157, 134)
PANEL = (14, 21, 34)
PANEL_EDGE = (63, 84, 112)
BUTTON = (35, 62, 84)
BUTTON_HOVER = (50, 86, 112)
SUCCESS = (92, 235, 148)
WARNING = (255, 205, 92)
DANGER = (255, 91, 100)
PIRATE_COLOR = (255, 132, 58)
PIRATE_ACCENT = (255, 222, 155)
NEBULA = (24, 20, 46)

PALETTES = [
    ((80, 210, 255), (230, 250, 255)),
    ((255, 190, 70), (255, 239, 170)),
    ((150, 110, 255), (225, 210, 255)),
    ((105, 235, 145), (220, 255, 230)),
    ((255, 115, 185), (255, 220, 240)),
]


def wrap_text(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        test = word if not line else f"{line} {word}"
        if font.size(test)[0] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Slopfest v0.96.4")
        self.settings = Settings.load()
        flags = pygame.FULLSCREEN if self.settings.fullscreen else pygame.RESIZABLE
        self.screen = pygame.display.set_mode(SCREEN_SIZE, flags)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 19)
        self.tiny_font = pygame.font.Font(None, 16)
        self.big_font = pygame.font.Font(None, 52)
        self.audio = SoundManager(self.settings.master_volume / 100.0)
        self.nebula_cache: list[tuple[pygame.Vector2, int, pygame.Surface]] = []
        self.running = True
        self.scene = "title"
        self.settings_return_scene = "title"
        self.identity = FactionIdentity()
        self.match_config = MatchConfig()
        self.setup_field = 0
        self.setup_seed_buffer = str(self.match_config.seed)
        self.setup_seed_edit = False
        self.victory_reason = ""
        self.autosave_timer = 0.0
        self.reset(self.match_config)
        self.scene = "title"

    @property
    def player_color(self) -> tuple[int, int, int]:
        return PALETTES[self.identity.palette_index][0]

    @property
    def accent_color(self) -> tuple[int, int, int]:
        return PALETTES[self.identity.palette_index][1]

    def faction_color(self, faction_id: int | None) -> tuple[int, int, int]:
        if faction_id is None:
            return NEUTRAL_COLOR
        if faction_id == PLAYER:
            return self.player_color
        if faction_id == PIRATE:
            return PIRATE_COLOR
        return self.factions[faction_id].primary

    def faction_accent(self, faction_id: int) -> tuple[int, int, int]:
        if faction_id == PLAYER:
            return self.accent_color
        if faction_id == PIRATE:
            return PIRATE_ACCENT
        return self.factions[faction_id].accent

    def reset(self, config: MatchConfig | None = None) -> None:
        if config is not None:
            self.match_config = MatchConfig.from_dict(config.to_dict())
        cfg = self.match_config

        self.world = World(seed=cfg.seed, planet_count=cfg.planet_count)
        self.build_nebula_cache()
        self.camera = Camera(self.screen.get_size())
        self.rng = random.Random(cfg.seed ^ 0x5A17)
        all_factions: dict[int, Faction] = make_factions()
        keep_ids = list(sorted(all_factions))[:cfg.rival_count]
        self.factions = {fid: all_factions[fid] for fid in keep_ids}
        self.market = MarketState.create(self.world.planets, self.rng)
        self.missions = MissionBoard()
        site_count = 10 if cfg.planet_count <= 26 else 12 if cfg.planet_count <= 34 else 15
        self.sites: list[Site] = generate_sites(self.world.planets, WORLD_SIZE, self.rng, site_count)
        self.artifact_points = 0
        self.relays_activated = 0
        self.discovery_log: list[str] = []
        self.elapsed_match = 0.0
        self.elapsed_income = 0.0
        self.autosave_timer = 0.0
        self.ai_strategy_timer = 0.0
        self.state = "playing"
        self.victory_reason = ""
        self.message = "The Wayline is open. Pick a future before somebody picks it for you."
        self.message_timer = 6.0
        self.bolts: list[Bolt] = []
        self.discovered: set[int] = set()
        self.selected_planet: Planet | None = None
        self.arrival_target: Planet | None = None
        self.selected_site: Site | None = None
        self.arrival_site: Site | None = None
        self.planet_menu_open = False
        self.site_menu_open = False
        self.journal_open = False
        self.shop_open = False
        self.specialization_menu_open = False
        self.refit_overlay = False
        self.lore_overlay = False
        self.diplomacy_open = False
        self.trade_computer_open = False
        self.contracts_open = False
        self.missions_open = False
        self.intel_panel_open = False
        self.ship_panel_open = False
        self.sector_grid_open = False
        self.selected_faction_id = next(iter(self.factions))
        self.mining = False
        self.mining_accumulator = 0.0
        self.name_edit: str | None = None
        self.name_buffer = ""
        self.player_replacement_count = 0
        self.tutorial_open = self.settings.show_tutorial

        homes = self.choose_home_planets(len(self.factions) + 1)
        player_home = homes[0]
        player_home.owner = PLAYER
        player_home.specialization = "Shipyard"
        player_home.development = 1
        self.player = Ship(
            faction_id=PLAYER,
            pos=player_home.pos + pygame.Vector2(0, -90),
            credits=cfg.starting_credits,
            marines=10,
        )
        self.camera.center = self.player.pos.copy()

        self.ai_ships: dict[int, Ship] = {}
        self.ai_targets: dict[int, Planet | None] = {}
        for faction_id, home in zip(self.factions, homes[1:]):
            faction = self.factions[faction_id]
            home.owner = faction_id
            faction.home_name = home.name
            if faction.personality == "defender":
                home.specialization = "Fortress"; home.defense = 1
            elif faction.personality == "merchant":
                home.specialization = "Trade Hub"
            elif faction.personality == "researcher":
                home.specialization = "Research Outpost"
            else:
                home.specialization = "Shipyard"
            home.development = 1

            ship = Ship(faction_id=faction_id, pos=home.pos + pygame.Vector2(0, -90), marines=8)
            if faction.personality == "expansionist":
                ship.weapon_name = "Twin Laser"
                ship.owned_weapons.append("Twin Laser")
            self.ai_ships[faction_id] = ship
            self.ai_targets[faction_id] = None

        self.pirates: list[Ship] = []
        self.pirate_targets: list[pygame.Vector2] = []
        self.pirate_respawn: list[float] = []
        self.spawn_pirates(max(1, cfg.rival_count - 1))
        self.update_discovery()

    def choose_home_planets(self, count: int) -> list[Planet]:
        start = min(
            self.world.planets,
            key=lambda p: p.pos.distance_squared_to(pygame.Vector2(850, 850)),
        )
        chosen = [start]
        while len(chosen) < count:
            remaining = [p for p in self.world.planets if p not in chosen]
            next_planet = max(
                remaining,
                key=lambda p: min(p.pos.distance_squared_to(c.pos) for c in chosen),
            )
            chosen.append(next_planet)
        return chosen

    def run(self) -> None:
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()

    # ------------------------------------------------------------------
    # Input / scenes
    # ------------------------------------------------------------------
    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue
            if event.type == pygame.VIDEORESIZE and not self.settings.fullscreen:
                self.camera.viewport.update(event.w, event.h)
            if self.name_edit is not None:
                self.handle_name_edit(event); continue
            if self.scene == "title":
                self.handle_title_event(event); continue
            if self.scene == "setup":
                self.handle_setup_event(event); continue
            if self.scene == "settings":
                self.handle_settings_event(event); continue
            if self.scene == "paused":
                self.handle_pause_event(event); continue
            if self.scene != "game":
                continue
            if event.type == pygame.KEYDOWN:
                self.handle_keydown(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and self.state == "playing":
                if event.button == 1:
                    if not self.any_modal_open() and self.handle_quick_tab_click(event.pos):
                        continue
                    if self.handle_modal_click(event.pos):
                        continue
                    site = self.site_at_screen(event.pos)
                    if site is not None:
                        self.travel_to_site(site)
                        continue
                    planet = self.planet_at_screen(event.pos)
                    if planet is not None:
                        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                            self.selected_planet = planet
                            self.intel_panel_open = True
                            self.ship_panel_open = False
                            self.audio.play("ui")
                        else:
                            self.travel_to_planet(planet)
                    elif not self.any_modal_open():
                        self.player.destination = self.camera.screen_to_world(event.pos)
                        self.arrival_target = None
                        self.arrival_site = None
                        self.mining = False
                elif event.button == 3 and not self.any_modal_open():
                    self.player.destination = self.camera.screen_to_world(event.pos)
                    self.arrival_target = None
                    self.arrival_site = None
                    self.mining = False

    def handle_name_edit(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.name_edit = None
            self.name_buffer = ""
        elif event.key == pygame.K_RETURN:
            cleaned = self.name_buffer.strip()[:28]
            if cleaned:
                if self.name_edit == "ship":
                    self.identity.ship_name = cleaned
                else:
                    self.identity.faction_name = cleaned
            self.name_edit = None
            self.name_buffer = ""
        elif event.key == pygame.K_BACKSPACE:
            self.name_buffer = self.name_buffer[:-1]
        elif event.unicode and event.unicode.isprintable() and len(self.name_buffer) < 28:
            self.name_buffer += event.unicode

    def handle_keydown(self, key: int) -> None:
        if key == pygame.K_F1:
            self.tutorial_open = not self.tutorial_open
            self.audio.play("ui")
            return

        if key == pygame.K_ESCAPE:
            if self.close_top_modal():
                return
            self.scene = "paused"
            return

        if self.state != "playing":
            if key == pygame.K_r:
                self.reset(self.match_config)
            elif key == pygame.K_RETURN:
                self.scene = "title"
            return

        if key == pygame.K_F5:
            self.save_game(); return
        if key == pygame.K_F9:
            self.load_game(); return

        if self.any_modal_open():
            return

        if key == pygame.K_n:
            self.intel_panel_open = not self.intel_panel_open
            if self.intel_panel_open:
                self.ship_panel_open = False
            self.audio.play("ui")
        elif key == pygame.K_u:
            self.ship_panel_open = not self.ship_panel_open
            if self.ship_panel_open:
                self.intel_panel_open = False
            self.audio.play("ui")
        elif key == pygame.K_b:
            self.sector_grid_open = not self.sector_grid_open
            self.audio.play("ui")
        elif key == pygame.K_p:
            self.diplomacy_open = True
        elif key == pygame.K_k:
            self.trade_computer_open = True
        elif key == pygame.K_q:
            self.missions_open = True
        elif key == pygame.K_j:
            self.journal_open = True
        elif key == pygame.K_e:
            if not self.open_nearby_site_menu():
                self.open_nearby_planet_menu()
        elif key == pygame.K_l:
            self.lore_overlay = True
        elif key == pygame.K_TAB:
            self.refit_overlay = True
        elif key == pygame.K_F2:
            self.name_edit = "ship"; self.name_buffer = self.identity.ship_name
        elif key == pygame.K_F3:
            self.name_edit = "faction"; self.name_buffer = self.identity.faction_name
        elif key == pygame.K_v:
            self.identity.palette_index = (self.identity.palette_index + 1) % len(PALETTES)
        elif key == pygame.K_i:
            self.identity.insignia_index = (self.identity.insignia_index + 1) % 4

    def close_top_modal(self) -> bool:
        if self.tutorial_open:
            self.tutorial_open = False
        elif self.site_menu_open:
            self.site_menu_open = False
        elif self.journal_open:
            self.journal_open = False
        elif self.contracts_open:
            self.contracts_open = False; self.planet_menu_open = True
        elif self.shop_open:
            self.shop_open = False; self.planet_menu_open = True
        elif self.specialization_menu_open:
            self.specialization_menu_open = False; self.planet_menu_open = True
        elif self.trade_computer_open:
            self.trade_computer_open = False
        elif self.missions_open:
            self.missions_open = False
        elif self.diplomacy_open:
            self.diplomacy_open = False
        elif self.refit_overlay:
            self.refit_overlay = False
        elif self.lore_overlay:
            self.lore_overlay = False
        elif self.planet_menu_open:
            self.planet_menu_open = False
        else:
            return False
        return True

    def any_modal_open(self) -> bool:
        return any((
            self.tutorial_open,
            self.planet_menu_open, self.site_menu_open, self.journal_open,
            self.shop_open, self.specialization_menu_open, self.refit_overlay,
            self.lore_overlay, self.diplomacy_open, self.trade_computer_open,
            self.contracts_open, self.missions_open, self.name_edit is not None,
        ))

    def handle_modal_click(self, pos: tuple[int, int]) -> bool:
        if self.site_menu_open:
            self.handle_site_menu_click(pos); return True
        if self.contracts_open:
            self.handle_contract_click(pos); return True
        if self.shop_open:
            self.handle_shop_click(pos); return True
        if self.specialization_menu_open:
            self.handle_specialization_click(pos); return True
        if self.diplomacy_open:
            self.handle_diplomacy_click(pos); return True
        if self.planet_menu_open:
            self.handle_planet_menu_click(pos); return True
        if self.refit_overlay:
            self.handle_refit_click(pos); return True
        return (self.lore_overlay or self.trade_computer_open
                or self.missions_open or self.journal_open)

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.message_timer = max(0.0, self.message_timer - dt)
        if self.scene != "game" or self.state != "playing" or self.any_modal_open():
            return

        self.elapsed_match += dt
        self.autosave_timer += dt
        self.ai_strategy_timer += dt

        if self.autosave_timer >= 90.0:
            self.autosave_timer = 0.0
            self.save_game(silent=True)

        if self.ai_strategy_timer >= 6.0:
            self.ai_strategy_timer = 0.0
            self.ai_strategy_tick()

        if self.market.update(dt, self.world.planets, self.rng) and self.rng.random() < 0.35:
            self.say("Trade computer: regional prices have shifted.")

        self.player.move(dt); self.player.update(dt)
        for ship in self.ai_ships.values():
            ship.move(dt); ship.update(dt)
        for pirate in self.pirates:
            pirate.move(dt); pirate.update(dt)

        for ship in self.all_ships():
            ship.pos.x = max(0, min(WORLD_SIZE.x, ship.pos.x))
            ship.pos.y = max(0, min(WORLD_SIZE.y, ship.pos.y))

        self.camera.viewport.update(self.screen.get_size())
        self.camera.update(self.player.pos, dt)

        self.update_discovery()
        self.update_income(dt)
        self.update_mining(dt)
        self.update_ai(dt)
        self.update_pirates(dt)
        self.update_orbital_defenses(dt)
        self.update_weapons(dt)
        self.update_replacements(dt)
        self.check_planet_arrival()
        self.check_site_arrival()
        self.check_end_state()

        if pygame.key.get_pressed()[pygame.K_SPACE] and self.player.alive:
            self.fire_ship_at(self.player, self.camera.screen_to_world(pygame.mouse.get_pos()))

    def all_ships(self) -> list[Ship]:
        return [self.player, *self.ai_ships.values(), *self.pirates]

    def update_discovery(self) -> None:
        for i, planet in enumerate(self.world.planets):
            visible = planet.pos.distance_to(self.player.pos) <= self.player.radar_range
            if not visible:
                visible = any(
                    p.owner == PLAYER and p.pos.distance_to(planet.pos) <= p.radar_range
                    for p in self.world.planets
                )
            if visible:
                self.discovered.add(i)

        for site in self.sites:
            if site.discovered:
                continue
            visible = site.pos.distance_to(self.player.pos) <= self.player.radar_range * 0.78
            if not visible:
                visible = any(
                    p.owner == PLAYER and p.specialization == "Research Outpost"
                    and p.pos.distance_to(site.pos) <= p.radar_range
                    for p in self.world.planets
                )
            if visible:
                site.discovered = True
                self.discovery_log.append(f"Located {site.kind}: {site.name}")
                if self.message_timer <= 0.5:
                    self.say(f"Sensor contact: {site.name} ({site.kind}).")

    def planet_visible(self, planet: Planet) -> bool:
        try:
            return self.world.planets.index(planet) in self.discovered
        except ValueError:
            return False

    def ship_visible(self, ship: Ship) -> bool:
        if ship.faction_id == PLAYER:
            return True
        if ship.pos.distance_to(self.player.pos) <= self.player.radar_range:
            return True
        return any(
            p.owner == PLAYER and p.pos.distance_to(ship.pos) <= p.radar_range
            for p in self.world.planets
        )

    def update_income(self, dt: float) -> None:
        self.elapsed_income += dt
        while self.elapsed_income >= 1.0:
            self.elapsed_income -= 1.0
            self.player.credits += sum(
                max(1, p.current_income // 2)
                for p in self.world.planets if p.owner == PLAYER
            )
            for faction_id, faction in self.factions.items():
                faction.credits += sum(
                    max(1, p.current_income // 2)
                    for p in self.world.planets if p.owner == faction_id
                )

    def update_ai(self, dt: float) -> None:
        profile = self.settings.ai_profile
        for faction_id, faction in self.factions.items():
            ship = self.ai_ships[faction_id]
            if not ship.alive:
                continue

            owned = [p for p in self.world.planets if p.owner == faction_id]
            neutrals = [p for p in self.world.planets if p.owner is None]

            if ship.health < 35 and owned:
                home = min(owned, key=lambda p: ship.pos.distance_squared_to(p.pos))
                ship.destination = home.pos.copy()
                if ship.pos.distance_to(home.pos) < home.radius + 100:
                    ship.health = min(ship.max_health, ship.health + 6 * dt)
                continue

            nearby_pirates = [p for p in self.pirates if p.alive and ship.pos.distance_to(p.pos) < 460]
            if nearby_pirates:
                pirate = min(nearby_pirates, key=lambda p: ship.pos.distance_squared_to(p.pos))
                ship.destination = pirate.pos.copy()
                if ship.pos.distance_to(pirate.pos) < 610:
                    self.fire_ship_at(ship, pirate.pos, wobble=5)
                continue

            if faction.hostile and self.player.alive:
                distance = ship.pos.distance_to(self.player.pos)
                grace = profile["grace"]
                aggro = profile["aggro"]
                if faction.personality == "expansionist":
                    grace *= 0.75
                    aggro *= 1.15
                elif faction.personality == "defender":
                    aggro *= 0.8

                if self.elapsed_match >= grace and distance <= aggro:
                    orbit = pygame.Vector2(0, 175).rotate(pygame.time.get_ticks() * 0.012 + faction_id * 70)
                    ship.destination = self.player.pos + orbit
                    if distance < 610:
                        self.fire_ship_at(ship, self.player.pos, wobble=6)
                    continue

            target = self.ai_targets.get(faction_id)
            if target is None or target.owner is not None:
                if neutrals:
                    # Personalities bend the score rather than using completely different AI.
                    def score(p: Planet) -> float:
                        dist = ship.pos.distance_to(p.pos)
                        value = p.current_income * 90 + p.richness * 60
                        if faction.personality == "merchant" and p.market_factor > 1.15:
                            value += 180
                        if faction.personality == "researcher" and p.specialization is None:
                            value += 45
                        if faction.personality == "defender":
                            value -= dist * 0.03
                        return value - dist * 0.045
                    target = max(neutrals, key=score)
                    self.ai_targets[faction_id] = target
                    ship.destination = target.pos.copy()
                elif owned:
                    target = max(owned, key=lambda p: p.current_income)
                    ship.destination = target.pos.copy()

            if target is not None and target.owner is None:
                if ship.pos.distance_to(target.pos) < target.radius + 90:
                    if faction.credits >= target.colonize_cost:
                        faction.credits -= target.colonize_cost
                        target.owner = faction_id
                        target.garrison = 100
                        self.ai_targets[faction_id] = None

            # AI invests at home instead of only snowballing outward.
            if owned and faction.credits > 220 and self.rng.random() < 0.0025:
                p = max(owned, key=lambda x: x.current_income)
                if p.development < 3 and faction.credits >= p.development_cost:
                    faction.credits -= p.development_cost
                    p.development += 1
                elif p.specialization is None and faction.credits >= p.specialization_cost:
                    faction.credits -= p.specialization_cost
                    choices = {
                        "merchant": "Trade Hub",
                        "researcher": "Research Outpost",
                        "defender": "Fortress",
                        "expansionist": "Shipyard",
                    }
                    p.specialization = choices[faction.personality]

    def update_orbital_defenses(self, dt: float) -> None:
        for planet in self.world.planets:
            planet.orbital_cooldown = max(0.0, planet.orbital_cooldown - dt)
            if planet.owner is None or planet.garrison <= 0:
                continue
            if planet.defense <= 0 and planet.specialization != "Fortress":
                continue
            if planet.orbital_cooldown > 0:
                continue

            possible: list[Ship] = []
            for ship in self.all_ships():
                if not ship.alive or ship.faction_id == planet.owner:
                    continue
                if not self.are_hostile(planet.owner, ship.faction_id):
                    continue
                if ship.pos.distance_to(planet.pos) <= planet.orbital_range:
                    possible.append(ship)
            if not possible:
                continue

            target = min(possible, key=lambda s: s.pos.distance_squared_to(planet.pos))
            direction = target.pos - planet.pos
            if direction.length_squared() <= 0:
                continue
            direction = direction.normalize()
            planet.orbital_cooldown = max(0.35, 1.05 - planet.defense * 0.12)
            self.bolts.append(Bolt(
                owner=planet.owner,
                pos=planet.pos + direction * (planet.radius + 8),
                velocity=direction * 520,
                damage=planet.orbital_damage,
                ttl=1.6,
                source="planet",
            ))

    def fire_ship_at(self, ship: Ship, target: pygame.Vector2, wobble: float = 0.0) -> None:
        if not ship.alive or ship.fire_cooldown > 0:
            return
        direction = target - ship.pos
        if direction.length_squared() < 16:
            return
        direction = direction.normalize()
        if wobble:
            direction = direction.rotate(self.rng.uniform(-wobble, wobble))
        weapon = ship.weapon
        ship.fire_cooldown = ship.weapon_cooldown
        self.bolts.append(Bolt(
            owner=ship.faction_id,
            pos=ship.pos + direction * 22,
            velocity=direction * weapon.projectile_speed,
            damage=weapon.damage,
            ttl=weapon.projectile_ttl,
            planet_multiplier=weapon.planet_multiplier,
        ))
        if ship is self.player:
            self.audio.play("laser", 0.7)
        elif self.ship_visible(ship) and ship.pos.distance_to(self.player.pos) < 850:
            self.audio.play("laser", 0.32)

    def update_weapons(self, dt: float) -> None:
        surviving: list[Bolt] = []
        ships = self.all_ships()
        for bolt in self.bolts:
            bolt.update(dt)
            if bolt.ttl <= 0 or not (0 <= bolt.pos.x <= WORLD_SIZE.x and 0 <= bolt.pos.y <= WORLD_SIZE.y):
                continue

            hit = False
            for ship in ships:
                if not ship.alive or ship.faction_id == bolt.owner:
                    continue
                if bolt.pos.distance_to(ship.pos) < 18:
                    was_alive = ship.alive
                    ship.take_damage(bolt.damage)
                    self.register_attack(bolt.owner, ship.faction_id, severity=18)
                    if ship is self.player or self.ship_visible(ship):
                        self.audio.play("hit", 0.6 if ship is self.player else 0.32)
                    if was_alive and not ship.alive and ship.faction_id == PIRATE and bolt.owner == PLAYER:
                        completed = self.missions.note_pirate_kill()
                        reward = sum(m.reward for m in completed)
                        if reward:
                            self.player.credits += reward
                            self.audio.play("cash")
                            self.say(f"Pirate destroyed. Bounty contracts paid {reward} credits.")
                    hit = True
                    break
            if hit:
                continue

            for planet in self.world.planets:
                if planet.owner is None or planet.owner == bolt.owner:
                    continue
                if bolt.pos.distance_to(planet.pos) <= planet.radius:
                    self.apply_planet_damage(planet, bolt.damage * bolt.planet_multiplier, bolt.owner)
                    if planet.owner == PLAYER or self.planet_visible(planet):
                        self.audio.play("hit", 0.25)
                    hit = True
                    break
            if not hit:
                surviving.append(bolt)
        self.bolts = surviving

    def apply_planet_damage(self, planet: Planet, damage: float, attacker: int) -> None:
        self.register_attack(attacker, planet.owner, severity=25)
        old_garrison = planet.garrison
        planet.garrison = max(0.0, planet.garrison - damage * 0.9)
        planet.infrastructure = max(0.0, planet.infrastructure - damage * 0.25)
        if old_garrison > 50 >= planet.garrison and planet.development > 0:
            planet.development -= 1
        if old_garrison > 18 >= planet.garrison and planet.defense > 0:
            planet.defense -= 1
        if attacker == PLAYER and planet.garrison <= 30:
            self.say(f"{planet.name}: garrison weakened. An invasion is now possible.")

    def register_attack(self, attacker: int, defender: int | None, severity: int) -> None:
        if defender is None or attacker == defender or attacker == PIRATE or defender == PIRATE:
            return
        if attacker == PLAYER and defender in self.factions:
            faction = self.factions[defender]
            faction.adjust_relation(-severity); faction.treaty = "war"
        elif defender == PLAYER and attacker in self.factions:
            faction = self.factions[attacker]
            faction.adjust_relation(-max(5, severity // 2)); faction.treaty = "war"

    def are_hostile(self, a: int, b: int) -> bool:
        if a == b:
            return False
        if a == PIRATE or b == PIRATE:
            return True
        if a == PLAYER and b in self.factions:
            return self.factions[b].hostile
        if b == PLAYER and a in self.factions:
            return self.factions[a].hostile
        return False

    def update_replacements(self, dt: float) -> None:
        if not self.player.alive:
            yards = [
                p for p in self.world.planets
                if p.owner == PLAYER and p.specialization == "Shipyard"
            ]
            if yards:
                yard = min(yards, key=lambda p: p.pos.distance_squared_to(self.player.pos))
                cost = min(100, int(self.player.credits))
                self.player.credits -= cost
                self.player.health = self.player.max_health
                self.player.shields = self.player.max_shields
                self.player.pos = yard.pos + pygame.Vector2(0, -90)
                self.player.destination = self.player.pos.copy()
                self.player.velocity.update(0, 0)
                self.player.cargo_amount = 0
                self.player.cargo_mineral = None
                self.player.marines = max(4, self.player.marines // 2)
                self.player_replacement_count += 1
                self.say(f"Replacement ship commissioned at {yard.name}. Cost: {cost} credits.")

        for faction_id, faction in self.factions.items():
            ship = self.ai_ships[faction_id]
            if ship.alive:
                faction.respawn_timer = 0
                continue
            yards = [
                p for p in self.world.planets
                if p.owner == faction_id and p.specialization == "Shipyard"
            ]
            if not yards:
                continue
            faction.respawn_timer += dt
            if faction.respawn_timer >= 14:
                yard = yards[0]
                ship.health = ship.max_health
                ship.shields = ship.max_shields
                ship.pos = yard.pos + pygame.Vector2(0, -90)
                ship.destination = ship.pos.copy()
                ship.velocity.update(0, 0)
                faction.respawn_timer = 0

    def check_end_state(self) -> None:
        if not self.player.alive:
            yards = [
                p for p in self.world.planets
                if p.owner == PLAYER and p.specialization == "Shipyard"
            ]
            if not yards:
                self.state = "lost"
                self.victory_reason = "Your final ship was destroyed after the last Shipyard fell."
                return

        owned = [p for p in self.world.planets if p.owner == PLAYER]
        total = len(self.world.planets)
        income = sum(max(1, p.current_income // 2) for p in owned)

        if total and len(owned) / total >= self.match_config.conquest_fraction:
            self.state = "won"
            self.victory_reason = f"Conquest: {len(owned)} of {total} worlds recognize your flag."
            return

        if (
            self.player.credits >= self.match_config.economic_credits
            and income >= self.match_config.economic_income
        ):
            self.state = "won"
            self.victory_reason = (
                f"Economic dominance: {int(self.player.credits)} credits and +{income}/sec income."
            )
            return

        relay_total = sum(1 for site in self.sites if site.kind == "Wayline Relay")
        relay_target = min(self.match_config.wayline_relays, relay_total)
        if relay_target > 0 and self.relays_activated >= relay_target:
            self.state = "won"
            self.victory_reason = (
                f"Wayline restoration: {self.relays_activated}/{relay_target} regional relays activated."
            )
            return

        if not any(
            p.owner in self.factions
            for p in self.world.planets
        ):
            self.state = "won"
            self.victory_reason = "Supremacy: no rival faction retains a colony."

    # ------------------------------------------------------------------
    # Mining / economy / colony operations
    # ------------------------------------------------------------------
    def update_mining(self, dt: float) -> None:
        if not self.mining:
            return
        p = self.selected_planet
        if (
            p is None or p.owner not in (None, PLAYER)
            or self.player.pos.distance_to(p.pos) > p.radius + 135
            or self.player.cargo_free <= 0
        ):
            self.mining = False
            return
        units_per_second = max(0.5, 2.2 * p.richness * p.mining_multiplier)
        self.mining_accumulator += dt
        interval = 1.0 / units_per_second
        while self.mining_accumulator >= interval and self.player.cargo_free > 0:
            self.mining_accumulator -= interval
            self.player.cargo_mineral = p.mineral
            self.player.cargo_amount += 1

    def toggle_mining(self) -> None:
        p = self.selected_planet
        if p is None or p.owner not in (None, PLAYER):
            self.say("Mining rights unavailable here.")
            return
        if self.player.cargo_amount and self.player.cargo_mineral != p.mineral:
            self.say("Cargo hold contains another mineral.")
            return
        self.mining = not self.mining
        self.mining_accumulator = 0
        self.say("Mining engaged." if self.mining else "Mining stopped.")

    def sell_cargo_at(self, planet: Planet) -> None:
        if self.player.cargo_amount <= 0 or not self.player.cargo_mineral:
            self.say("Cargo hold is empty.")
            return
        if planet.owner in self.factions and self.factions[planet.owner].hostile:
            self.say("Their customs office is presently shooting at you.")
            return
        mineral = self.player.cargo_mineral
        units = self.player.cargo_amount
        price = self.market.sell_price(planet, mineral)
        earned = units * price
        self.player.credits += earned
        self.player.cargo_amount = 0
        self.player.cargo_mineral = None
        if planet.owner in self.factions:
            self.factions[planet.owner].adjust_relation(min(5, max(1, units // 8)))
        self.audio.play("cash")
        self.say(f"Sold {units} {mineral} at {price}/unit for {earned} credits.")

    def repair_at_planet(self, planet: Planet) -> None:
        if planet.owner in self.factions and self.factions[planet.owner].hostile:
            return
        missing = self.player.max_health - self.player.health
        if missing <= 0:
            self.say("Hull already at 100%.")
            return
        cost_per = 0.75 if planet.owner == PLAYER and planet.specialization == "Shipyard" else 1.8
        repair = min(missing, self.player.credits / cost_per)
        if repair <= 0:
            self.say("Repairs require credits.")
            return
        self.player.credits -= repair * cost_per
        self.player.health += repair
        self.say(f"Repaired {int(repair)} hull at {planet.name}.")

    def recruit_marines(self, planet: Planet) -> None:
        if planet.owner in self.factions and self.factions[planet.owner].hostile:
            return
        cost = 50
        if self.player.credits < cost:
            self.say("A 5-marine detachment costs 50 credits.")
            return
        self.player.credits -= cost
        self.player.marines += 5
        self.say("Five invasion troops embarked.")

    def try_colonize(self, planet: Planet) -> bool:
        if planet.owner is not None:
            return False
        if self.player.credits < planet.colonize_cost:
            self.say(f"Colonization requires {planet.colonize_cost} credits.")
            return False
        self.player.credits -= planet.colonize_cost
        planet.owner = PLAYER
        planet.garrison = 100
        self.say(f"{planet.name} joins {self.identity.faction_name}.")
        return True

    def invasion_requirement(self, planet: Planet) -> int:
        return max(4, math.ceil(planet.garrison / 6) + planet.development * 2 + planet.defense * 2)

    def try_invade(self, planet: Planet) -> bool:
        if planet.owner not in self.factions:
            return False
        faction = self.factions[planet.owner]
        if not faction.hostile:
            self.say("Invading a non-hostile world would be a fairly direct declaration of war.")
            faction.treaty = "war"
            faction.adjust_relation(-45)

        if planet.garrison > 35:
            self.say("Garrison too strong. Bombard it below 35% first.")
            return False

        required = self.invasion_requirement(planet)
        if self.player.marines < required:
            committed = self.player.marines
            self.player.marines = 0
            planet.garrison = max(0, planet.garrison - committed * 1.8)
            self.say(f"Invasion repelled. Need roughly {required} troops; all {committed} were lost.")
            return False

        losses = max(2, math.ceil(required * 0.55))
        self.player.marines -= losses
        former_owner = planet.owner
        planet.owner = PLAYER
        planet.garrison = 45
        planet.infrastructure = max(30, planet.infrastructure)
        self.register_attack(PLAYER, former_owner, 35)
        self.say(f"{planet.name} captured. {losses} invasion troops lost.")
        return True

    def try_develop(self, planet: Planet) -> None:
        if planet.owner != PLAYER:
            return
        if self.player.credits < planet.development_cost:
            self.say(f"Need {planet.development_cost} credits.")
            return
        self.player.credits -= planet.development_cost
        planet.development += 1
        planet.infrastructure = min(100, planet.infrastructure + 15)

    def try_fortify(self, planet: Planet) -> None:
        if planet.owner != PLAYER or planet.defense >= 3:
            return
        if self.player.credits < planet.defense_cost:
            self.say(f"Need {planet.defense_cost} credits.")
            return
        self.player.credits -= planet.defense_cost
        planet.defense += 1
        planet.garrison = min(100, planet.garrison + 20)

    def try_specialize(self, index: int) -> bool:
        p = self.selected_planet
        if p is None or p.owner != PLAYER or p.specialization is not None:
            return False
        if self.player.credits < p.specialization_cost:
            self.say(f"Specialization costs {p.specialization_cost} credits.")
            return False
        self.player.credits -= p.specialization_cost
        p.specialization = SPECIALIZATIONS[index]
        if p.specialization == "Fortress":
            p.defense = max(1, p.defense)
        return True

    def near_shipyard(self) -> Planet | None:
        yards = [
            p for p in self.world.planets
            if p.owner == PLAYER and p.specialization == "Shipyard"
            and self.player.pos.distance_to(p.pos) <= p.radius + 150
        ]
        return yards[0] if yards else None

    def try_upgrade_module(self, index: int) -> None:
        if self.near_shipyard() is None:
            self.say("Module refits require one of your Shipyards.")
            return
        levels = (
            self.player.shield_level,
            self.player.engine_level,
            self.player.radar_level,
            self.player.cargo_level,
        )
        level = levels[index]
        if level >= MAX_MODULE_LEVEL:
            self.say(f"{MODULE_NAMES[index]} is already at maximum tier.")
            return
        cost = upgrade_cost(level)
        assert cost is not None
        if self.player.credits < cost:
            self.say(f"Upgrade costs {cost} credits.")
            return
        self.player.credits -= cost
        self.player.upgrade_module(index)
        self.audio.play("cash")
        self.say(f"{MODULE_NAMES[index]} upgraded to tier {level + 1}. Hull hardware updated.")

    def ship_state(self, ship: Ship) -> dict:
        return {
            "faction_id": ship.faction_id,
            "pos": [ship.pos.x, ship.pos.y],
            "destination": [ship.destination.x, ship.destination.y],
            "velocity": [ship.velocity.x, ship.velocity.y],
            "credits": ship.credits,
            "max_health": ship.max_health,
            "health": ship.health,
            "fire_cooldown": ship.fire_cooldown,
            "cargo_mineral": ship.cargo_mineral,
            "cargo_amount": ship.cargo_amount,
            "weapon_name": ship.weapon_name,
            "owned_weapons": list(ship.owned_weapons),
            "shield_level": ship.shield_level,
            "engine_level": ship.engine_level,
            "radar_level": ship.radar_level,
            "cargo_level": ship.cargo_level,
            "shields": ship.shields,
            "last_damage_timer": ship.last_damage_timer,
            "marines": ship.marines,
            "unique_modules": list(ship.unique_modules),
        }

    def apply_ship_state(self, ship: Ship, raw: dict) -> None:
        ship.pos.update(raw.get("pos", [ship.pos.x, ship.pos.y]))
        ship.destination.update(raw.get("destination", [ship.pos.x, ship.pos.y]))
        ship.velocity.update(raw.get("velocity", [0, 0]))
        for attr in (
            "credits", "max_health", "health", "fire_cooldown", "cargo_mineral",
            "cargo_amount", "weapon_name", "shield_level", "engine_level",
            "radar_level", "cargo_level", "shields", "last_damage_timer", "marines",
        ):
            if attr in raw:
                setattr(ship, attr, raw[attr])
        ship.owned_weapons = list(raw.get("owned_weapons", ship.owned_weapons))
        ship.unique_modules = list(raw.get("unique_modules", ship.unique_modules))

    def mission_state(self, mission: Mission) -> dict:
        return {
            "mission_id": mission.mission_id,
            "kind": mission.kind,
            "title": mission.title,
            "description": mission.description,
            "origin_name": mission.origin_name,
            "target_name": mission.target_name,
            "mineral": mission.mineral,
            "amount": mission.amount,
            "reward": mission.reward,
            "status": mission.status,
            "pirate_kill_start": mission.pirate_kill_start,
        }

    def snapshot(self) -> dict:
        return {
            "config": self.match_config.to_dict(),
            "identity": {
                "faction_name": self.identity.faction_name,
                "ship_name": self.identity.ship_name,
                "palette_index": self.identity.palette_index,
                "insignia_index": self.identity.insignia_index,
            },
            "elapsed_match": self.elapsed_match,
            "artifact_points": self.artifact_points,
            "relays_activated": self.relays_activated,
            "discovered": sorted(self.discovered),
            "discovery_log": list(self.discovery_log),
            "player": self.ship_state(self.player),
            "factions": {
                str(fid): {
                    "credits": faction.credits,
                    "relation": faction.relation,
                    "treaty": faction.treaty,
                    "home_name": faction.home_name,
                    "respawn_timer": faction.respawn_timer,
                }
                for fid, faction in self.factions.items()
            },
            "ai_ships": {str(fid): self.ship_state(ship) for fid, ship in self.ai_ships.items()},
            "ai_targets": {
                str(fid): target.name if target is not None else None
                for fid, target in self.ai_targets.items()
            },
            "pirates": [self.ship_state(ship) for ship in self.pirates],
            "pirate_targets": [[v.x, v.y] for v in self.pirate_targets],
            "pirate_respawn": list(self.pirate_respawn),
            "planets": {
                p.name: {
                    "owner": p.owner,
                    "development": p.development,
                    "defense": p.defense,
                    "specialization": p.specialization,
                    "garrison": p.garrison,
                    "infrastructure": p.infrastructure,
                    "orbital_cooldown": p.orbital_cooldown,
                }
                for p in self.world.planets
            },
            "sites": {
                str(s.site_id): {
                    "discovered": s.discovered,
                    "visited": s.visited,
                    "depleted": s.depleted,
                }
                for s in self.sites
            },
            "market": {
                "timer": self.market.timer,
                "cycle": self.market.cycle,
                "multipliers": [
                    [planet, mineral, value]
                    for (planet, mineral), value in self.market.multipliers.items()
                ],
            },
            "missions": {
                "next_id": self.missions.next_id,
                "completed": self.missions.completed,
                "pirate_kills": self.missions.pirate_kills,
                "boards": {
                    name: [self.mission_state(m) for m in board]
                    for name, board in self.missions.boards.items()
                },
                "active_ids": [m.mission_id for m in self.missions.active],
            },
        }

    def save_game(self, silent: bool = False) -> bool:
        try:
            write_save(self.snapshot())
        except (OSError, TypeError, ValueError) as exc:
            if not silent:
                self.say(f"Save failed: {type(exc).__name__}.")
            return False
        if not silent:
            self.audio.play("save")
            self.say("Game saved.")
        return True

    def load_game(self) -> bool:
        try:
            payload = read_save()
            cfg = MatchConfig.from_dict(payload["config"])
            self.reset(cfg)

            ident = payload.get("identity", {})
            self.identity.faction_name = ident.get("faction_name", self.identity.faction_name)
            self.identity.ship_name = ident.get("ship_name", self.identity.ship_name)
            self.identity.palette_index = int(ident.get("palette_index", self.identity.palette_index)) % len(PALETTES)
            self.identity.insignia_index = int(ident.get("insignia_index", self.identity.insignia_index)) % 4

            self.elapsed_match = float(payload.get("elapsed_match", 0))
            self.artifact_points = int(payload.get("artifact_points", 0))
            self.relays_activated = int(payload.get("relays_activated", 0))
            self.discovered = {int(i) for i in payload.get("discovered", [])}
            self.discovery_log = list(payload.get("discovery_log", []))
            self.apply_ship_state(self.player, payload.get("player", {}))

            for fid_text, raw in payload.get("factions", {}).items():
                fid = int(fid_text)
                if fid not in self.factions:
                    continue
                faction = self.factions[fid]
                faction.credits = raw.get("credits", faction.credits)
                faction.relation = int(raw.get("relation", faction.relation))
                faction.treaty = raw.get("treaty", faction.treaty)
                faction.home_name = raw.get("home_name", faction.home_name)
                faction.respawn_timer = raw.get("respawn_timer", faction.respawn_timer)

            for fid_text, raw in payload.get("ai_ships", {}).items():
                fid = int(fid_text)
                if fid in self.ai_ships:
                    self.apply_ship_state(self.ai_ships[fid], raw)

            planet_by_name = {p.name: p for p in self.world.planets}
            for name, raw in payload.get("planets", {}).items():
                p = planet_by_name.get(name)
                if p is None:
                    continue
                for attr in (
                    "owner", "development", "defense", "specialization",
                    "garrison", "infrastructure", "orbital_cooldown",
                ):
                    if attr in raw:
                        setattr(p, attr, raw[attr])

            for fid_text, target_name in payload.get("ai_targets", {}).items():
                fid = int(fid_text)
                if fid in self.ai_targets:
                    self.ai_targets[fid] = planet_by_name.get(target_name) if target_name else None

            for site in self.sites:
                raw = payload.get("sites", {}).get(str(site.site_id), {})
                site.discovered = bool(raw.get("discovered", site.discovered))
                site.visited = bool(raw.get("visited", site.visited))
                site.depleted = bool(raw.get("depleted", site.depleted))

            market = payload.get("market", {})
            self.market.timer = float(market.get("timer", self.market.timer))
            self.market.cycle = int(market.get("cycle", self.market.cycle))
            restored_market = {}
            for row in market.get("multipliers", []):
                if isinstance(row, list) and len(row) == 3:
                    restored_market[(str(row[0]), str(row[1]))] = float(row[2])
            if restored_market:
                self.market.multipliers = restored_market

            self.missions = MissionBoard()
            mraw = payload.get("missions", {})
            self.missions.next_id = int(mraw.get("next_id", 1))
            self.missions.completed = int(mraw.get("completed", 0))
            self.missions.pirate_kills = int(mraw.get("pirate_kills", 0))
            active_ids = {int(i) for i in mraw.get("active_ids", [])}
            all_missions: dict[int, Mission] = {}
            for board_name, rows in mraw.get("boards", {}).items():
                board = []
                for row in rows:
                    mission = Mission(
                        mission_id=int(row["mission_id"]),
                        kind=row["kind"],
                        title=row["title"],
                        description=row["description"],
                        origin_name=row["origin_name"],
                        target_name=row.get("target_name"),
                        mineral=row.get("mineral"),
                        amount=int(row.get("amount", 0)),
                        reward=int(row.get("reward", 0)),
                        status=row.get("status", "available"),
                        pirate_kill_start=int(row.get("pirate_kill_start", 0)),
                    )
                    board.append(mission)
                    all_missions[mission.mission_id] = mission
                self.missions.boards[board_name] = board
            self.missions.active = [all_missions[mid] for mid in active_ids if mid in all_missions]

            pirate_rows = payload.get("pirates", [])
            for ship, raw in zip(self.pirates, pirate_rows):
                self.apply_ship_state(ship, raw)
            targets = payload.get("pirate_targets", [])
            for i, row in enumerate(targets[:len(self.pirate_targets)]):
                self.pirate_targets[i].update(row)
            respawns = payload.get("pirate_respawn", [])
            for i, value in enumerate(respawns[:len(self.pirate_respawn)]):
                self.pirate_respawn[i] = float(value)

            self.scene = "game"
            self.state = "playing"
            self.camera.center = self.player.pos.copy()
            self.say("Save loaded.")
            return True
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.scene = "title"
            self.message = f"Could not load save: {type(exc).__name__}"
            self.message_timer = 5.0
            return False

    def player_income(self) -> int:
        return sum(
            max(1, p.current_income // 2)
            for p in self.world.planets if p.owner == PLAYER
        )

    def victory_progress_lines(self) -> list[str]:
        owned = sum(1 for p in self.world.planets if p.owner == PLAYER)
        total = max(1, len(self.world.planets))
        conquest_target = max(1, math.ceil(total * self.match_config.conquest_fraction))
        relay_total = sum(1 for s in self.sites if s.kind == "Wayline Relay")
        relay_target = min(self.match_config.wayline_relays, relay_total)
        rivals_alive = len({
            p.owner for p in self.world.planets
            if p.owner in self.factions
        })
        return [
            f"Conquest: {owned}/{conquest_target} worlds",
            f"Economy: {int(self.player.credits)}/{self.match_config.economic_credits} cr, +{self.player_income()}/{self.match_config.economic_income}/sec",
            f"Wayline: {self.relays_activated}/{relay_target} relays",
            f"Supremacy: {rivals_alive} rival powers retain colonies",
        ]

    def ai_strategy_tick(self) -> None:
        for fid, faction in self.factions.items():
            ship = self.ai_ships[fid]
            if not ship.alive:
                continue

            # Military spending is paced and personality-weighted.
            if faction.credits >= 300:
                if faction.personality == "expansionist" and ship.weapon_name == "Pulse Laser":
                    faction.credits -= 180
                    ship.weapon_name = "Twin Laser"
                    if "Twin Laser" not in ship.owned_weapons:
                        ship.owned_weapons.append("Twin Laser")
                elif faction.personality == "defender" and ship.shield_level < 3:
                    cost = upgrade_cost(ship.shield_level)
                    if cost is not None and faction.credits >= cost:
                        faction.credits -= cost
                        old = ship.max_shields
                        ship.shield_level += 1
                        ship.shields += ship.max_shields - old
                elif faction.personality == "researcher" and ship.radar_level < 3:
                    cost = upgrade_cost(ship.radar_level)
                    if cost is not None and faction.credits >= cost:
                        faction.credits -= cost
                        ship.radar_level += 1
                elif faction.personality == "merchant" and ship.engine_level < 3:
                    cost = upgrade_cost(ship.engine_level)
                    if cost is not None and faction.credits >= cost:
                        faction.credits -= cost
                        ship.engine_level += 1

            # Powers that are doing well reinforce a vulnerable valuable colony.
            owned = [p for p in self.world.planets if p.owner == fid]
            if faction.credits >= 180 and owned:
                target = max(owned, key=lambda p: p.current_income - p.defense * 2)
                if target.defense < 2 and target.current_income >= 5:
                    faction.credits -= target.defense_cost
                    target.defense += 1

    # ------------------------------------------------------------------
    # Travel / planet interaction
    # ------------------------------------------------------------------
    def travel_to_planet(self, planet: Planet) -> None:
        self.selected_planet = planet
        self.arrival_target = planet
        delta = self.player.pos - planet.pos
        delta = pygame.Vector2(0, -1) if delta.length_squared() < 1 else delta.normalize()
        self.player.destination = planet.pos + delta * (planet.radius + 74)
        self.mining = False
        self.say(f"Course laid in for {planet.name}.")

    def check_planet_arrival(self) -> None:
        p = self.arrival_target
        if p is None:
            return
        if self.player.pos.distance_to(p.pos) > p.radius + 118 or self.player.velocity.length() > 45:
            return
        self.arrival_target = None
        self.selected_planet = p
        self.complete_missions_at(p)
        if self.settings.auto_open_planet_menu:
            self.planet_menu_open = True

    def open_nearby_planet_menu(self) -> None:
        candidates = [
            p for p in self.world.planets
            if self.planet_visible(p) and self.player.pos.distance_to(p.pos) <= p.radius + 135
        ]
        if not candidates:
            self.say("No world within docking range.")
            return
        self.selected_planet = min(candidates, key=lambda p: self.player.pos.distance_squared_to(p.pos))
        self.planet_menu_open = True

    def planet_at_screen(self, pos: tuple[int, int]) -> Planet | None:
        mouse = pygame.Vector2(pos)
        for p in reversed(self.world.planets):
            if not self.planet_visible(p):
                continue
            if mouse.distance_to(self.camera.world_to_screen(p.pos)) <= p.radius + 9:
                return p
        return None

    def planet_menu_actions(self) -> list[tuple[str, str, bool]]:
        p = self.selected_planet
        if p is None:
            return []
        actions = []
        hostile = p.owner in self.factions and self.factions[p.owner].hostile
        if not hostile:
            if p.owner in (None, PLAYER):
                actions.append(("mine", f"Mine {p.mineral}", True))
            buy = self.market.buy_price(p)
            actions += [
                ("buy", f"Buy up to 5 {p.mineral} ({buy}/unit)", True),
                ("trade", "Sell cargo", self.player.cargo_amount > 0),
                ("contracts", "Contracts", True),
                ("shop", "Equipment shop", True),
                ("repair", "Repair hull", self.player.health < self.player.max_health),
                ("marines", "Recruit 5 invasion troops (50 cr)", True),
            ]
        if p.owner is None:
            actions.append(("claim", f"Colonize ({p.colonize_cost} cr)", True))
        elif p.owner == PLAYER:
            actions.append(("develop", f"Develop ({p.development_cost} cr)", True))
            actions.append(("fortify", f"Fortify ({p.defense_cost} cr)", p.defense < 3))
            if p.specialization is None:
                actions.append(("spec", f"Specialize ({p.specialization_cost} cr)", True))
            if p.specialization == "Shipyard":
                actions.append(("refit", "Refit ship modules", True))
        elif hostile:
            req = self.invasion_requirement(p)
            actions.append(("invade", f"Invade (need ~{req} troops)", p.garrison <= 35))
        actions += [("lore", "Local record", True), ("depart", "Depart", True)]
        return actions

    def planet_menu_rects(self):
        actions = self.planet_menu_actions()
        return list(zip(actions, self.menu_button_rects(len(actions), 450, 36, 6)))

    def handle_planet_menu_click(self, pos: tuple[int, int]) -> None:
        p = self.selected_planet
        if p is None:
            self.planet_menu_open = False; return
        for (action, _label, enabled), rect in self.planet_menu_rects():
            if not rect.collidepoint(pos) or not enabled:
                continue
            if action == "mine":
                self.planet_menu_open = False; self.toggle_mining()
            elif action == "buy":
                self.buy_local_resource(p)
            elif action == "trade":
                self.sell_cargo_at(p)
            elif action == "contracts":
                self.planet_menu_open = False; self.contracts_open = True
            elif action == "shop":
                self.planet_menu_open = False; self.shop_open = True
            elif action == "repair":
                self.repair_at_planet(p)
            elif action == "marines":
                self.recruit_marines(p)
            elif action == "claim":
                self.try_colonize(p)
            elif action == "develop":
                self.try_develop(p)
            elif action == "fortify":
                self.try_fortify(p)
            elif action == "spec":
                self.planet_menu_open = False; self.specialization_menu_open = True
            elif action == "refit":
                self.planet_menu_open = False; self.refit_overlay = True
            elif action == "invade":
                self.try_invade(p)
            elif action == "lore":
                self.planet_menu_open = False; self.lore_overlay = True
            elif action == "depart":
                self.planet_menu_open = False
            return

    def spawn_pirates(self, count: int) -> None:
        candidates = [p for p in self.world.planets if p.owner is None and p.pos.distance_to(self.player.pos) > 900]
        self.rng.shuffle(candidates)
        for i in range(count):
            anchor = candidates[i % len(candidates)] if candidates else self.world.planets[-1]
            pirate = Ship(
                faction_id=PIRATE,
                pos=anchor.pos + pygame.Vector2(self.rng.randint(-160,160), self.rng.randint(-160,160)),
                max_health=72, health=72, marines=0,
            )
            pirate.weapon_name = "Twin Laser"
            pirate.owned_weapons.append("Twin Laser")
            pirate.shields = min(pirate.shields, 38)
            self.pirates.append(pirate)
            self.pirate_targets.append(anchor.pos.copy())
            self.pirate_respawn.append(0.0)

    def update_pirates(self, dt: float) -> None:
        traffic = [self.player, *self.ai_ships.values()]
        for i, pirate in enumerate(self.pirates):
            if not pirate.alive:
                self.pirate_respawn[i] += dt
                if self.pirate_respawn[i] >= 75:
                    anchor = self.rng.choice([p for p in self.world.planets if p.owner is None] or self.world.planets)
                    pirate.health = pirate.max_health
                    pirate.shields = min(pirate.max_shields, 38)
                    pirate.pos = anchor.pos + pygame.Vector2(120,-120)
                    pirate.destination = pirate.pos.copy()
                    pirate.velocity.update(0,0)
                    self.pirate_respawn[i] = 0
                continue
            targets = [s for s in traffic if s.alive and pirate.pos.distance_to(s.pos) < 510]
            if targets:
                target = min(targets, key=lambda s: pirate.pos.distance_squared_to(s.pos))
                pirate.destination = target.pos + pygame.Vector2(0,140).rotate(pygame.time.get_ticks()*0.017+i*80)
                if pirate.pos.distance_to(target.pos) < 600:
                    self.fire_ship_at(pirate, target.pos, wobble=9)
                continue
            if pirate.pos.distance_to(self.pirate_targets[i]) < 100:
                anchor = self.rng.choice(self.world.planets)
                self.pirate_targets[i] = anchor.pos + pygame.Vector2(self.rng.randint(-180,180), self.rng.randint(-180,180))
            pirate.destination = self.pirate_targets[i]

    def buy_local_resource(self, planet: Planet) -> None:
        mineral = planet.mineral
        if self.player.cargo_amount > 0 and self.player.cargo_mineral != mineral:
            self.say("Cargo hold contains a different commodity.")
            return
        price = self.market.buy_price(planet)
        units = min(5, self.player.cargo_free, int(self.player.credits // price))
        if units <= 0:
            self.say("Not enough credits or cargo space.")
            return
        self.player.credits -= units * price
        self.player.cargo_mineral = mineral
        self.player.cargo_amount += units
        if planet.owner in self.factions:
            self.factions[planet.owner].adjust_relation(1)
        self.audio.play("cash")
        self.say(f"Bought {units} {mineral} at {price}/unit.")

    def complete_missions_at(self, planet: Planet) -> None:
        completed, consume, reward = self.missions.arrive(planet, self.player.cargo_mineral, self.player.cargo_amount)
        if consume:
            self.player.cargo_amount -= consume
            if self.player.cargo_amount <= 0:
                self.player.cargo_amount = 0
                self.player.cargo_mineral = None
        if reward:
            self.player.credits += reward
            self.say(f"Contract complete. Paid {reward} credits.")

    def contract_rects(self):
        p = self.selected_planet
        if p is None:
            return []
        contracts = self.missions.contracts_for(p, self.world.planets, self.rng)
        return list(zip(contracts + [None], self.menu_button_rects(len(contracts)+1,590,58,8)))

    def handle_contract_click(self, pos: tuple[int,int]) -> None:
        for mission, rect in self.contract_rects():
            if not rect.collidepoint(pos):
                continue
            if mission is None:
                self.contracts_open=False; self.planet_menu_open=True
            elif self.missions.accept(mission):
                self.say(f"Accepted contract: {mission.title}")
            else:
                self.say("That contract is no longer available.")
            return

    def draw_contracts(self) -> None:
        p=self.selected_planet
        if p is None:
            return
        overlay=pygame.Surface(self.screen.get_size(),pygame.SRCALPHA); overlay.fill((0,0,0,215)); self.screen.blit(overlay,(0,0))
        sw,sh=self.screen.get_size()
        title=self.big_font.render(f"{p.name.upper()} CONTRACT BOARD",True,self.accent_color)
        self.screen.blit(title,title.get_rect(center=(sw//2,max(50,sh//2-190))))
        for mission,rect in self.contract_rects():
            if mission is None:
                self.draw_button(rect,"BACK"); continue
            self.draw_button(rect,f"{mission.title}   {mission.reward} cr   [{mission.short_status}]",mission.status=="available")
            self.screen.blit(self.tiny_font.render(mission.description,True,MUTED),(rect.x+14,rect.bottom-16))

    def draw_missions(self) -> None:
        overlay=pygame.Surface(self.screen.get_size(),pygame.SRCALPHA); overlay.fill((0,0,0,215)); self.screen.blit(overlay,(0,0))
        sw,sh=self.screen.get_size(); panel=pygame.Rect(sw//2-410,70,820,sh-140)
        pygame.draw.rect(self.screen,PANEL,panel,border_radius=10)
        self.screen.blit(self.big_font.render("ACTIVE CONTRACTS",True,self.accent_color),(panel.x+24,panel.y+22))
        y=panel.y+88
        if not self.missions.active:
            self.screen.blit(self.font.render("No active contracts. Planet boards have work.",True,MUTED),(panel.x+30,y))
        for mission in self.missions.active[:10]:
            self.screen.blit(self.font.render(mission.title,True,TEXT),(panel.x+30,y)); y+=24
            self.screen.blit(self.small_font.render(f"{mission.description}  Reward: {mission.reward} cr",True,MUTED),(panel.x+42,y)); y+=34
        footer=self.small_font.render(f"Completed {self.missions.completed} • Pirate kills {self.missions.pirate_kills} • Esc closes",True,MUTED)
        self.screen.blit(footer,(panel.x+24,panel.bottom-30))

    def peaceful_known_planets(self) -> list[Planet]:
        result=[]
        for p in self.world.planets:
            if not self.planet_visible(p):
                continue
            if p.owner in self.factions and self.factions[p.owner].hostile:
                continue
            result.append(p)
        return result

    def draw_trade_computer(self) -> None:
        overlay=pygame.Surface(self.screen.get_size(),pygame.SRCALPHA); overlay.fill((0,0,0,220)); self.screen.blit(overlay,(0,0))
        sw,sh=self.screen.get_size(); panel=pygame.Rect(sw//2-470,55,940,sh-110)
        pygame.draw.rect(self.screen,PANEL,panel,border_radius=10)
        self.screen.blit(self.big_font.render("TRADE COMPUTER",True,self.accent_color),(panel.x+24,panel.y+22))
        self.screen.blit(self.small_font.render(f"Market cycle {self.market.cycle} • prices shift about every 32 seconds",True,MUTED),(panel.x+28,panel.y+70))
        routes=self.market.best_routes(self.peaceful_known_planets(),10)
        y=panel.y+110
        headers=("PROFIT","COMMODITY","BUY","SELL","ROUTE"); xoffs=(30,115,255,335,430)
        for value,x in zip(headers,xoffs):
            self.screen.blit(self.tiny_font.render(value,True,WARNING),(panel.x+x,y))
        y+=24
        if not routes:
            self.screen.blit(self.font.render("Explore more peaceful markets to calculate routes.",True,MUTED),(panel.x+30,y))
        for profit,origin,target,mineral,buy,sell in routes:
            vals=(f"+{profit}",mineral,str(buy),str(sell),f"{origin} → {target}")
            for value,x in zip(vals,xoffs):
                self.screen.blit(self.small_font.render(value,True,TEXT),(panel.x+x,y))
            y+=28
        self.screen.blit(self.small_font.render("K or Esc closes",True,MUTED),(panel.x+24,panel.bottom-30))

    def site_at_screen(self, pos: tuple[int,int]) -> Site | None:
        mouse = pygame.Vector2(pos)
        for site in self.sites:
            if site.discovered and mouse.distance_to(self.camera.world_to_screen(site.pos)) <= 15:
                return site
        return None

    def travel_to_site(self, site: Site) -> None:
        self.selected_site = site
        self.arrival_site = site
        self.arrival_target = None
        delta = self.player.pos - site.pos
        delta = pygame.Vector2(0,-1) if delta.length_squared() < 1 else delta.normalize()
        self.player.destination = site.pos + delta * 66
        self.mining = False
        self.say(f"Course laid in for {site.name}.")

    def check_site_arrival(self) -> None:
        site = self.arrival_site
        if site is None:
            return
        if self.player.pos.distance_to(site.pos) > 95 or self.player.velocity.length() > 45:
            return
        self.arrival_site = None
        self.selected_site = site
        site.visited = True
        self.site_menu_open = True

    def open_nearby_site_menu(self) -> bool:
        candidates = [s for s in self.sites if s.discovered and self.player.pos.distance_to(s.pos) <= 100]
        if not candidates:
            return False
        self.selected_site = min(candidates,key=lambda s:self.player.pos.distance_squared_to(s.pos))
        self.site_menu_open = True
        return True

    def site_menu_rects(self):
        site = self.selected_site
        if site is None:
            return []
        labels = [(site.action_label, not site.depleted), ("DEPART", True)]
        return list(zip(labels,self.menu_button_rects(2,430,48,10)))

    def handle_site_menu_click(self, pos: tuple[int,int]) -> None:
        site = self.selected_site
        if site is None:
            self.site_menu_open=False
            return
        for (label,enabled),rect in self.site_menu_rects():
            if not rect.collidepoint(pos) or not enabled:
                continue
            if label=="DEPART":
                self.site_menu_open=False
            else:
                self.resolve_site(site)
            return

    def resolve_site(self, site: Site) -> None:
        if site.depleted:
            return
        site.depleted = True
        site.visited = True
        self.audio.play("discover")
        self.discovery_log.append(site.lore)

        if site.reward_kind == "credits":
            amount = int(site.reward_value)
            self.player.credits += amount
            self.say(f"Salvage recovered: {amount} credits.")
        elif site.reward_kind == "artifact":
            amount = int(site.reward_value)
            self.artifact_points += amount
            self.say(f"Anomaly mapped. Recovered {amount} artifact data.")
        elif site.reward_kind == "relay":
            self.relays_activated += 1
            self.artifact_points += 1
            self.player.credits += 75
            self.say(f"{site.name} activated. Wayline telemetry archived.")
        elif site.reward_kind == "module":
            module = str(site.reward_value)
            if module not in self.player.unique_modules:
                self.player.unique_modules.append(module)
                if module == "Severance Capacitor":
                    self.player.shields = self.player.max_shields
                self.say(f"Unique module recovered: {module}.")
            else:
                self.player.credits += 160
                self.say("Duplicate artifact sold to researchers for 160 credits.")
        elif site.reward_kind == "weapon":
            weapon = str(site.reward_value)
            if weapon not in self.player.owned_weapons:
                self.player.owned_weapons.append(weapon)
                self.player.weapon_name = weapon
                self.say(f"Recovered and equipped pre-Severance weapon: {weapon}.")
            else:
                self.player.credits += 180
                self.say("Recovered weapon pattern sold for 180 credits.")

    def draw_sites(self) -> None:
        w,h=self.screen.get_size()
        for site in self.sites:
            if not site.discovered:
                continue
            sp=self.camera.world_to_screen(site.pos)
            if not (-40<=sp.x<=w+40 and -40<=sp.y<=h+40):
                continue
            color=(180,145,255) if not site.depleted else (90,80,110)
            if site.kind=="Wayline Relay":
                pygame.draw.rect(self.screen,color,(int(sp.x-7),int(sp.y-7),14,14),2)
                pygame.draw.line(self.screen,color,(sp.x-11,sp.y),(sp.x+11,sp.y),1)
                pygame.draw.line(self.screen,color,(sp.x,sp.y-11),(sp.x,sp.y+11),1)
            elif site.kind=="Derelict":
                pygame.draw.polygon(self.screen,color,[(sp.x,sp.y-9),(sp.x+9,sp.y),(sp.x,sp.y+9),(sp.x-9,sp.y)],2)
            elif site.kind=="Abandoned Station":
                pygame.draw.circle(self.screen,color,sp,9,2)
                pygame.draw.circle(self.screen,color,sp,3,1)
            else:
                pygame.draw.circle(self.screen,color,sp,10,1)
                pygame.draw.circle(self.screen,color,sp,5,1)
            label=self.tiny_font.render(site.name,True,color)
            self.screen.blit(label,label.get_rect(midtop=(sp.x,sp.y+13)))

    def draw_site_menu(self) -> None:
        site=self.selected_site
        if site is None:
            return
        overlay=pygame.Surface(self.screen.get_size(),pygame.SRCALPHA)
        overlay.fill((0,0,0,215))
        self.screen.blit(overlay,(0,0))
        sw,sh=self.screen.get_size()
        title=self.big_font.render(site.name.upper(),True,(190,160,255))
        self.screen.blit(title,title.get_rect(center=(sw//2,90)))
        status='EXHAUSTED' if site.depleted else 'UNRESOLVED'
        sub=self.font.render(f"{site.kind} • {status}",True,MUTED)
        self.screen.blit(sub,sub.get_rect(center=(sw//2,128)))
        y=165
        for line in wrap_text(self.small_font,site.lore,700)[:5]:
            image=self.small_font.render(line,True,TEXT)
            self.screen.blit(image,image.get_rect(center=(sw//2,y)))
            y+=22
        for (label,enabled),rect in self.site_menu_rects():
            self.draw_button(rect,label,enabled)

    def draw_journal(self) -> None:
        overlay=pygame.Surface(self.screen.get_size(),pygame.SRCALPHA)
        overlay.fill((0,0,0,220))
        self.screen.blit(overlay,(0,0))
        sw,sh=self.screen.get_size()
        panel=pygame.Rect(sw//2-460,45,920,sh-90)
        pygame.draw.rect(self.screen,PANEL,panel,border_radius=10)
        self.screen.blit(self.big_font.render("DISCOVERY JOURNAL",True,(190,160,255)),(panel.x+24,panel.y+18))
        summary=f"Relays activated: {self.relays_activated}   Artifact data: {self.artifact_points}   Unique modules: {len(self.player.unique_modules)}"
        self.screen.blit(self.small_font.render(summary,True,WARNING),(panel.x+28,panel.y+68))
        y=panel.y+106
        if self.player.unique_modules:
            mods=" • ".join(self.player.unique_modules)
            self.screen.blit(self.small_font.render(f"Recovered tech: {mods}",True,SUCCESS),(panel.x+28,y))
            y+=30
        discovered=[s for s in self.sites if s.discovered]
        if not discovered:
            self.screen.blit(self.font.render("No non-planet contacts discovered yet.",True,MUTED),(panel.x+30,y))
        for site in discovered[:10]:
            status="resolved" if site.depleted else "unresolved"
            self.screen.blit(self.small_font.render(f"{site.kind}: {site.name} [{status}]",True,TEXT),(panel.x+30,y))
            y+=19
            if site.visited:
                snippet=site.lore if len(site.lore)<108 else site.lore[:105]+"..."
                self.screen.blit(self.tiny_font.render(snippet,True,MUTED),(panel.x+45,y))
                y+=20
            y+=5
            if y>panel.bottom-70:
                break
        footer="The records disagree. That is becoming a pattern. • J or Esc closes"
        self.screen.blit(self.small_font.render(footer,True,MUTED),(panel.x+24,panel.bottom-30))

    # ------------------------------------------------------------------
    # Shops / specialization / diplomacy
    # ------------------------------------------------------------------
    def shop_inventory(self) -> list[str]:
        p = self.selected_planet
        if p is None:
            return []
        return inventory_for_planet(p.specialization)

    def shop_rects(self):
        items = self.shop_inventory()
        return list(zip(items + ["BACK"], self.menu_button_rects(len(items) + 1, 520, 54, 8)))

    def handle_shop_click(self, pos: tuple[int, int]) -> None:
        for name, rect in self.shop_rects():
            if not rect.collidepoint(pos):
                continue
            if name == "BACK":
                self.shop_open = False
                self.planet_menu_open = True
            else:
                self.buy_or_equip_weapon(name)
            return

    def buy_or_equip_weapon(self, name: str) -> None:
        spec = WEAPONS[name]
        if name in self.player.owned_weapons:
            self.player.weapon_name = name
            self.audio.play("ui")
            self.say(f"Equipped {name}.")
            return
        if self.player.credits < spec.price:
            self.say(f"{name} costs {spec.price} credits.")
            return
        self.player.credits -= spec.price
        self.player.owned_weapons.append(name)
        self.player.weapon_name = name
        self.audio.play("cash")
        self.say(f"Purchased {name}.")

    def specialization_rects(self):
        labels = list(SPECIALIZATIONS) + ["BACK"]
        return list(zip(labels, self.menu_button_rects(len(labels), 520, 50, 8)))

    def handle_specialization_click(self, pos: tuple[int, int]) -> None:
        for label, rect in self.specialization_rects():
            if not rect.collidepoint(pos):
                continue
            if label == "BACK":
                self.specialization_menu_open = False
                self.planet_menu_open = True
            else:
                if self.try_specialize(SPECIALIZATIONS.index(label)):
                    self.specialization_menu_open = False
                    self.planet_menu_open = True
            return

    def diplomacy_faction_rects(self):
        sw, _ = self.screen.get_size()
        x = sw // 2 - 360
        return [
            (fid, pygame.Rect(x, 165 + i * 66, 300, 52))
            for i, fid in enumerate(self.factions)
        ]

    def diplomacy_action_rects(self):
        sw, _ = self.screen.get_size()
        x = sw // 2 + 25
        labels = ("GIFT 100", "OFFER CEASEFIRE", "TRADE PACT", "ALLIANCE", "CLOSE")
        return list(zip(labels, [
            pygame.Rect(x, 190 + i * 52, 300, 40) for i in range(len(labels))
        ]))

    def handle_diplomacy_click(self, pos: tuple[int, int]) -> None:
        for fid, rect in self.diplomacy_faction_rects():
            if rect.collidepoint(pos):
                self.selected_faction_id = fid
                return

        faction = self.factions[self.selected_faction_id]
        for label, rect in self.diplomacy_action_rects():
            if not rect.collidepoint(pos):
                continue
            if label == "CLOSE":
                self.diplomacy_open = False
            elif label == "GIFT 100":
                if self.player.credits >= 100:
                    self.player.credits -= 100
                    faction.adjust_relation(20)
                    self.say(f"{faction.name} accepted the gift.")
            elif label == "OFFER CEASEFIRE":
                if faction.treaty == "war" and faction.relation >= -80:
                    faction.treaty = "neutral"
                    faction.adjust_relation(18)
                    self.say(f"Ceasefire signed with {faction.name}.")
                else:
                    self.say("They are not interested in that offer.")
            elif label == "TRADE PACT":
                if faction.treaty != "war" and faction.relation >= 10:
                    faction.treaty = "trade"
                    faction.adjust_relation(8)
                    self.say(f"Trade pact signed with {faction.name}.")
                else:
                    self.say("Relations are not warm enough for a trade pact.")
            elif label == "ALLIANCE":
                if faction.treaty == "trade" and faction.relation >= 55:
                    faction.treaty = "alliance"
                    faction.adjust_relation(10)
                    self.say(f"Alliance formed with {faction.name}.")
                else:
                    self.say("Alliance requires a strong trade relationship.")
            return

    def quick_tab_rects(self):
        h=self.screen.get_height()
        labels=("intel","ship","sector")
        return [(name,pygame.Rect(18+i*116,h-54,108,38)) for i,name in enumerate(labels)]

    def handle_quick_tab_click(self,pos: tuple[int,int]) -> bool:
        for name,rect in self.quick_tab_rects():
            if not rect.collidepoint(pos):
                continue
            self.audio.play("ui")
            if name=="intel":
                self.intel_panel_open=not self.intel_panel_open
                if self.intel_panel_open: self.ship_panel_open=False
            elif name=="ship":
                self.ship_panel_open=not self.ship_panel_open
                if self.ship_panel_open: self.intel_panel_open=False
            else:
                self.sector_grid_open=not self.sector_grid_open
            return True
        return False

    def draw_quick_tabs(self) -> None:
        state={"intel":self.intel_panel_open,"ship":self.ship_panel_open,"sector":self.sector_grid_open}
        keys={"intel":"N","ship":"U","sector":"B"}
        for name,rect in self.quick_tab_rects():
            active=state[name]
            pygame.draw.rect(self.screen,BUTTON_HOVER if active or rect.collidepoint(pygame.mouse.get_pos()) else PANEL,rect,border_radius=5)
            pygame.draw.rect(self.screen,self.accent_color if active else PANEL_EDGE,rect,1,border_radius=5)
            icon=ASSETS.icon("icons",name,1)
            self.screen.blit(icon,(rect.x+8,rect.y+9))
            self.screen.blit(self.tiny_font.render(f"{name.upper()} [{keys[name]}]",True,TEXT if active else MUTED),(rect.x+34,rect.y+13))

    def drawer_rect(self,width: int=350) -> pygame.Rect:
        sw,sh=self.screen.get_size()
        top=188
        return pygame.Rect(max(10,sw-width-18),top,width,max(260,sh-top-70))

    def draw_panel_header(self,rect: pygame.Rect,icon_group: str,icon_name: str,title: str,subtitle: str="") -> int:
        pygame.draw.rect(self.screen,PANEL,rect,border_radius=8)
        pygame.draw.rect(self.screen,PANEL_EDGE,rect,1,border_radius=8)
        icon=ASSETS.icon(icon_group,icon_name,2)
        self.screen.blit(icon,(rect.x+14,rect.y+12))
        self.screen.blit(self.font.render(title,True,TEXT),(rect.x+62,rect.y+13))
        if subtitle:
            self.screen.blit(self.tiny_font.render(subtitle,True,MUTED),(rect.x+62,rect.y+36))
        pygame.draw.line(self.screen,PANEL_EDGE,(rect.x+12,rect.y+58),(rect.right-12,rect.y+58))
        return rect.y+70

    def draw_stat_line(self,rect: pygame.Rect,y: int,group: str,name: str,label: str,value: str,color=None) -> int:
        icon=ASSETS.icon(group,name,1)
        self.screen.blit(icon,(rect.x+14,y-2))
        self.screen.blit(self.tiny_font.render(label.upper(),True,MUTED),(rect.x+42,y))
        image=self.small_font.render(value,True,color or TEXT)
        self.screen.blit(image,(rect.x+145,y-2))
        return y+24

    def planet_owner_name(self,p: Planet) -> str:
        if p.owner is None: return "Independent"
        if p.owner==PLAYER: return self.identity.faction_name
        return self.factions[p.owner].name

    def known_average_sell_price(self,mineral: str) -> float:
        planets=self.peaceful_known_planets()
        if not planets: return 0.0
        return sum(self.market.sell_price(p,mineral) for p in planets)/len(planets)

    def draw_intel_panel(self) -> None:
        rect=self.drawer_rect(360)
        p=self.selected_planet if self.selected_planet is not None and self.planet_visible(self.selected_planet) else None
        if p is None:
            info=summarize_sector(self,self.player.pos)
            y=self.draw_panel_header(rect,"icons","sector",f"SUB-SECTOR {info.label}","current navigation cell")
            risk_color=SUCCESS if info.risk=="LOW" else WARNING if info.risk=="GUARDED" else DANGER
            rows=[
                ("icons","owner","KNOWN WORLDS",str(info.known_worlds),TEXT),
                ("icons","income","YOUR WORLDS",str(info.friendly_worlds),SUCCESS),
                ("icons","hostility","HOSTILE WORLDS",str(info.hostile_worlds),DANGER),
                ("icons","artifact","DISCOVERIES",str(info.known_sites),None),
                ("icons","ship","HOSTILE SHIPS",str(info.hostile_ships),DANGER),
                ("icons","hostility","PIRATES",str(info.pirates),PIRATE_COLOR),
                ("icons","hostility","RISK",info.risk,risk_color),
            ]
            for row in rows: y=self.draw_stat_line(rect,y,*row)
            y+=8
            self.screen.blit(self.small_font.render("Best known local trade",True,WARNING),(rect.x+14,y)); y+=24
            bounds=sector_bounds(self.player.pos)
            local=[q for q in self.peaceful_known_planets() if bounds.collidepoint(q.pos.x,q.pos.y)]
            routes=self.market.best_routes(local,3)
            if not routes:
                self.screen.blit(self.tiny_font.render("No profitable route mapped inside this sector.",True,MUTED),(rect.x+16,y))
            else:
                for profit,origin,target,mineral,buy,sell in routes:
                    line=f"{mineral}: {origin} {buy} → {target} {sell}  (+{profit})"
                    self.screen.blit(self.tiny_font.render(line,True,TEXT),(rect.x+16,y)); y+=19
            self.screen.blit(self.tiny_font.render("Shift+click a planet to inspect without flying there.",True,MUTED),(rect.x+14,rect.bottom-25))
            return

        host,host_color=hostility_label(p.owner,self.factions,PLAYER)
        y=self.draw_panel_header(rect,"icons","intel",p.name.upper(),f"{sector_label(p.pos)} • {self.planet_owner_name(p)}")
        y=self.draw_stat_line(rect,y,"icons","hostility","STATUS",host,host_color)
        y=self.draw_stat_line(rect,y,"minerals",mineral_asset_name(p.mineral),"RESOURCE",f"{p.mineral} x{p.richness:.1f}")
        y=self.draw_stat_line(rect,y,"icons","income","INCOME",f"+{max(1,p.current_income//2)}/sec")
        y=self.draw_stat_line(rect,y,"icons","development","VALUE",str(p.strategic_value))
        y=self.draw_stat_line(rect,y,"icons","garrison","GARRISON",f"{int(p.garrison)}%")
        y=self.draw_stat_line(rect,y,"icons","defense","DEFENSE",f"Tier {p.defense}")
        y=self.draw_stat_line(rect,y,"icons","infrastructure","INFRA",f"{int(p.infrastructure)}%")
        y=self.draw_stat_line(rect,y,"icons","distance","DISTANCE",f"{int(self.player.pos.distance_to(p.pos))}")
        y+=6
        spec=p.specialization or "General settlement"
        spec_name=specialization_asset_name(p.specialization) if p.specialization else None
        if spec_name:
            y=self.draw_stat_line(rect,y,"specializations",spec_name,"FACILITY",spec)
        else:
            self.screen.blit(self.tiny_font.render(f"FACILITY   {spec}",True,MUTED),(rect.x+14,y)); y+=22
        self.screen.blit(self.tiny_font.render(f"{p.climate} • habitability {p.habitability}% • traffic {p.traffic}",True,MUTED),(rect.x+14,y)); y+=19
        self.screen.blit(self.tiny_font.render(f"{p.population_millions:.1f}m people • {p.government}",True,MUTED),(rect.x+14,y)); y+=27

        self.screen.blit(self.small_font.render("MARKET PRICES",True,WARNING),(rect.x+14,y)); y+=23
        export=self.market.buy_price(p)
        self.screen.blit(self.tiny_font.render(f"Local export: buy {p.mineral} for {export}/unit",True,TEXT),(rect.x+14,y)); y+=20
        minerals=list(("Iron","Silica","Cobalt","Rare Earths","Helium-3","Uranium"))
        for i,mineral in enumerate(minerals):
            price=self.market.sell_price(p,mineral)
            avg=self.known_average_sell_price(mineral)
            delta=price-avg if avg else 0
            sign=f"{delta:+.1f}" if avg else "?"
            colx=rect.x+14+(i%2)*168
            rowy=y+(i//2)*23
            icon=ASSETS.icon("minerals",mineral_asset_name(mineral),1)
            self.screen.blit(icon,(colx,rowy-2))
            short=mineral.replace("Rare Earths","RareEarth")
            self.screen.blit(self.tiny_font.render(f"{short} {price} ({sign})",True,TEXT),(colx+24,rowy+1))
        y+=72
        self.screen.blit(self.tiny_font.render("price delta is versus known peaceful-market average",True,MUTED),(rect.x+14,y))

    def draw_ship_panel(self) -> None:
        rect=self.drawer_rect(370)
        y=self.draw_panel_header(rect,"icons","ship",self.identity.ship_name.upper(),f"{self.player.weapon_name} • live hardware view")
        sprite=player_ship_surface(self.player,self.player_color,self.accent_color)
        scale=5
        preview=pygame.transform.scale(sprite,(sprite.get_width()*scale,sprite.get_height()*scale))
        self.screen.blit(preview,preview.get_rect(center=(rect.centerx, y+72)))
        y+=148
        weapon=WEAPONS[self.player.weapon_name]
        y=self.draw_stat_line(rect,y,"weapons",weapon_asset_name(self.player.weapon_name),"WEAPON",self.player.weapon_name)
        self.screen.blit(self.tiny_font.render(f"{weapon.damage:g} dmg • {weapon.cooldown:.3f}s • {int(weapon.projectile_speed)} velocity",True,MUTED),(rect.x+42,y-4)); y+=17
        module_rows=(
            ("shield",self.player.shield_level,f"{int(self.player.max_shields)} cap / {self.player.shield_regen:.1f} regen"),
            ("engine",self.player.engine_level,f"{int(self.player.speed)} top speed"),
            ("radar",self.player.radar_level,f"{int(self.player.radar_range)} range"),
            ("cargo",self.player.cargo_level,f"{self.player.cargo_capacity} capacity"),
        )
        for group,level,value in module_rows:
            y=self.draw_stat_line(rect,y,"modules",f"{group}_t{level}",f"{group} T{level}",value)
        if self.player.unique_modules:
            y+=4
            self.screen.blit(self.small_font.render("RECOVERED TECH",True,WARNING),(rect.x+14,y)); y+=22
            for mod in self.player.unique_modules[:4]:
                y=self.draw_stat_line(rect,y,"modules",f"unique_{unique_asset_name(mod)}","ARTIFACT",mod,SUCCESS)
        self.screen.blit(self.tiny_font.render("Hardware upgrades visibly alter the flight sprite.",True,MUTED),(rect.x+14,rect.bottom-25))

    def draw_subsector_grid(self) -> None:
        sw,sh=self.screen.get_size()
        top_left=self.camera.screen_to_world((0,0))
        bottom_right=self.camera.screen_to_world((sw,sh))
        start_x=max(0,int(top_left.x//SECTOR_SIZE)*SECTOR_SIZE)
        end_x=min(int(WORLD_SIZE.x),int(bottom_right.x//SECTOR_SIZE+1)*SECTOR_SIZE)
        start_y=max(0,int(top_left.y//SECTOR_SIZE)*SECTOR_SIZE)
        end_y=min(int(WORLD_SIZE.y),int(bottom_right.y//SECTOR_SIZE+1)*SECTOR_SIZE)
        current=sector_bounds(self.player.pos)
        # current-sector wash
        tl=self.camera.world_to_screen(pygame.Vector2(current.left,current.top)); br=self.camera.world_to_screen(pygame.Vector2(current.right,current.bottom))
        wash=pygame.Surface((max(1,int(br.x-tl.x)),max(1,int(br.y-tl.y))),pygame.SRCALPHA); wash.fill((90,130,170,24))
        self.screen.blit(wash,(tl.x,tl.y))
        for x in range(start_x,end_x+1,SECTOR_SIZE):
            a=self.camera.world_to_screen(pygame.Vector2(x,start_y)); b=self.camera.world_to_screen(pygame.Vector2(x,end_y)); pygame.draw.line(self.screen,(45,65,86),a,b,1)
        for y in range(start_y,end_y+1,SECTOR_SIZE):
            a=self.camera.world_to_screen(pygame.Vector2(start_x,y)); b=self.camera.world_to_screen(pygame.Vector2(end_x,y)); pygame.draw.line(self.screen,(45,65,86),a,b,1)
        for x in range(start_x,end_x,SECTOR_SIZE):
            for y in range(start_y,end_y,SECTOR_SIZE):
                pos=pygame.Vector2(x+30,y+30); sp=self.camera.world_to_screen(pos)
                label=sector_label(pos)
                self.screen.blit(self.tiny_font.render(label,True,(83,112,140)),sp)

    def draw_hover_info(self) -> None:
        mouse=pygame.mouse.get_pos()
        # Avoid fighting the persistent drawers and quick tabs.
        if any(rect.collidepoint(mouse) for _,rect in self.quick_tab_rects()):
            return
        if self.intel_panel_open and self.drawer_rect(360).collidepoint(mouse): return
        if self.ship_panel_open and self.drawer_rect(370).collidepoint(mouse): return
        p=self.planet_at_screen(mouse)
        site=self.site_at_screen(mouse) if p is None else None
        if p is None and site is None: return
        if p is not None:
            host,host_color=hostility_label(p.owner,self.factions,PLAYER)
            lines=[p.name,f"{self.planet_owner_name(p)} • {host}",f"{p.mineral} x{p.richness:.1f} • buy {self.market.buy_price(p)}",f"{sector_label(p.pos)} • Shift+click for intel"]
            color=host_color
        else:
            lines=[site.name,site.kind,"resolved" if site.depleted else "unresolved",f"{sector_label(site.pos)} • click to investigate"]
            color=(190,160,255)
        widths=[self.tiny_font.size(line)[0] for line in lines]
        w=max(widths)+24; h=14+len(lines)*18
        x=min(mouse[0]+16,self.screen.get_width()-w-8); y=min(mouse[1]+16,self.screen.get_height()-h-8)
        rect=pygame.Rect(x,y,w,h)
        pygame.draw.rect(self.screen,(9,15,25),rect,border_radius=5); pygame.draw.rect(self.screen,color,rect,1,border_radius=5)
        for i,line in enumerate(lines):
            self.screen.blit(self.tiny_font.render(line,True,TEXT if i==0 else MUTED),(x+10,y+7+i*18))

    # ------------------------------------------------------------------
    # Menu helpers / settings
    # ------------------------------------------------------------------
    def menu_button_rects(self, count: int, width=320, height=44, gap=10, center_y=None):
        sw, sh = self.screen.get_size()
        total = count * height + max(0, count - 1) * gap
        top = (sh - total) // 2 if center_y is None else center_y - total // 2
        left = (sw - width) // 2
        return [pygame.Rect(left, top + i * (height + gap), width, height) for i in range(count)]

    def draw_button(self, rect: pygame.Rect, label: str, enabled=True) -> None:
        hover = rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(self.screen, BUTTON_HOVER if hover and enabled else BUTTON, rect, border_radius=6)
        pygame.draw.rect(self.screen, PANEL_EDGE, rect, 1, border_radius=6)
        image = self.font.render(label, True, TEXT if enabled else MUTED)
        self.screen.blit(image, image.get_rect(center=rect.center))

    def setup_rows(self):
        sw,_ = self.screen.get_size()
        labels = (
            "SEED",
            "GALAXY",
            "RIVALS",
            "STARTING CREDITS",
            "START MATCH",
            "BACK",
        )
        rects = self.menu_button_rects(len(labels), 500, 46, 9)
        return list(zip(labels,rects))

    def handle_setup_event(self, event) -> None:
        if self.setup_seed_edit:
            if event.type != pygame.KEYDOWN:
                return
            if event.key == pygame.K_ESCAPE:
                self.setup_seed_edit = False
                self.setup_seed_buffer = str(self.match_config.seed)
            elif event.key == pygame.K_RETURN:
                try:
                    self.match_config.seed = int(self.setup_seed_buffer or "97")
                except ValueError:
                    self.match_config.seed = 97
                self.setup_seed_edit = False
            elif event.key == pygame.K_BACKSPACE:
                self.setup_seed_buffer = self.setup_seed_buffer[:-1]
            elif event.unicode.isdigit() and len(self.setup_seed_buffer) < 10:
                self.setup_seed_buffer += event.unicode
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.scene = "title"
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        for label,rect in self.setup_rows():
            if not rect.collidepoint(event.pos):
                continue
            if label == "SEED":
                self.setup_seed_edit = True
                self.setup_seed_buffer = str(self.match_config.seed)
            elif label == "GALAXY":
                options = list(GALAXY_OPTIONS)
                i = options.index(self.match_config.planet_count) if self.match_config.planet_count in options else 1
                self.match_config.planet_count = options[(i+1)%len(options)]
            elif label == "RIVALS":
                options = list(RIVAL_OPTIONS)
                i = options.index(self.match_config.rival_count) if self.match_config.rival_count in options else -1
                self.match_config.rival_count = options[(i+1)%len(options)]
            elif label == "STARTING CREDITS":
                options = list(CREDIT_OPTIONS)
                i = options.index(self.match_config.starting_credits) if self.match_config.starting_credits in options else 1
                self.match_config.starting_credits = options[(i+1)%len(options)]
            elif label == "START MATCH":
                try:
                    self.match_config.seed = int(self.setup_seed_buffer or self.match_config.seed)
                except ValueError:
                    self.match_config.seed = 97
                self.reset(self.match_config)
                self.scene = "game"
            elif label == "BACK":
                self.scene = "title"
            return

    def draw_match_setup(self) -> None:
        self.screen.fill(BACKGROUND)
        self.draw_nebulae()
        self.draw_stars()
        sw,sh=self.screen.get_size()
        title=self.big_font.render("MATCH SETUP",True,self.accent_color)
        self.screen.blit(title,title.get_rect(center=(sw//2,80)))

        relay_note = "Victory paths: conquest • economy • Wayline • supremacy"
        note=self.small_font.render(relay_note,True,MUTED)
        self.screen.blit(note,note.get_rect(center=(sw//2,118)))

        values = {
            "SEED": f"SEED: {self.setup_seed_buffer}{'_' if self.setup_seed_edit else ''}",
            "GALAXY": f"GALAXY: {self.match_config.planet_count} WORLDS",
            "RIVALS": f"RIVALS: {self.match_config.rival_count}",
            "STARTING CREDITS": f"STARTING CREDITS: {self.match_config.starting_credits}",
            "START MATCH": "START MATCH",
            "BACK": "BACK",
        }
        for label,rect in self.setup_rows():
            self.draw_button(rect,values[label])

        details = (
            f"Conquest {int(self.match_config.conquest_fraction*100)}% • "
            f"Economic {self.match_config.economic_credits} cr +{self.match_config.economic_income}/sec • "
            f"Wayline {self.match_config.wayline_relays} relays"
        )
        image=self.tiny_font.render(details,True,MUTED)
        self.screen.blit(image,image.get_rect(center=(sw//2,sh-38)))

    def title_buttons(self):
        labels = ["NEW GAME"]
        if has_save():
            labels.append("CONTINUE")
        labels += ["SETTINGS", "QUIT"]
        return list(zip(
            labels,
            self.menu_button_rects(len(labels), 310, 48, 12, self.screen.get_height()//2 + 75)
        ))

    def handle_title_event(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.setup_seed_buffer = str(self.match_config.seed)
                self.scene = "setup"
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        for label, rect in self.title_buttons():
            if not rect.collidepoint(event.pos):
                continue
            if label == "NEW GAME":
                self.setup_seed_buffer = str(self.match_config.seed)
                self.setup_seed_edit = False
                self.scene = "setup"
            elif label == "CONTINUE":
                self.load_game()
            elif label == "SETTINGS":
                self.settings_return_scene = "title"
                self.scene = "settings"
            else:
                self.running = False

    def pause_buttons(self):
        labels = ("RESUME", "SAVE GAME", "LOAD GAME", "SETTINGS", "RETURN TO TITLE")
        return list(zip(labels, self.menu_button_rects(len(labels), 330, 44, 8)))

    def handle_pause_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.scene = "game"
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        for label, rect in self.pause_buttons():
            if not rect.collidepoint(event.pos):
                continue
            if label == "RESUME":
                self.scene = "game"
            elif label == "SAVE GAME":
                self.scene = "game"
                self.save_game()
            elif label == "LOAD GAME":
                self.load_game()
            elif label == "SETTINGS":
                self.settings_return_scene = "paused"
                self.scene = "settings"
            else:
                self.scene = "title"

    def settings_rows(self):
        labels = (
            "FULLSCREEN",
            "AUTO PLANET MENU",
            "HOVER INTEL",
            "RADAR RING",
            "ENEMY PRESSURE",
            "SOUND VOLUME",
            "SHOW TUTORIAL",
            "BACK",
        )
        return list(zip(labels, self.menu_button_rects(len(labels), 440, 42, 6)))

    def handle_settings_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.settings.save()
            self.scene = self.settings_return_scene
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        for label, rect in self.settings_rows():
            if not rect.collidepoint(event.pos):
                continue
            self.audio.play("ui")
            if label == "FULLSCREEN":
                self.settings.fullscreen = not self.settings.fullscreen
                flags = pygame.FULLSCREEN if self.settings.fullscreen else pygame.RESIZABLE
                self.screen = pygame.display.set_mode(SCREEN_SIZE, flags)
            elif label == "AUTO PLANET MENU":
                self.settings.auto_open_planet_menu = not self.settings.auto_open_planet_menu
            elif label == "HOVER INTEL":
                self.settings.show_hover_info = not self.settings.show_hover_info
            elif label == "RADAR RING":
                self.settings.show_radar_ring = not self.settings.show_radar_ring
            elif label == "ENEMY PRESSURE":
                self.settings.enemy_pressure = (self.settings.enemy_pressure + 1) % 3
            elif label == "SOUND VOLUME":
                levels = (0, 25, 50, 75, 100)
                current = min(levels, key=lambda n: abs(n - self.settings.master_volume))
                i = levels.index(current)
                self.settings.master_volume = levels[(i + 1) % len(levels)]
                self.audio.set_volume(self.settings.master_volume / 100.0)
                self.audio.play("ui")
            elif label == "SHOW TUTORIAL":
                self.settings.show_tutorial = not self.settings.show_tutorial
            else:
                self.scene = self.settings_return_scene
            self.settings.save()

    def handle_refit_click(self, pos: tuple[int, int]) -> None:
        yard=self.near_shipyard()
        if yard is None:
            return
        sw,sh=self.screen.get_size()
        panel=pygame.Rect(sw//2-440,sh//2-270,880,540)
        levels=(self.player.shield_level,self.player.engine_level,self.player.radar_level,self.player.cargo_level)
        rects=[pygame.Rect(panel.x+390,panel.y+120+i*78,455,64) for i in range(4)]
        for i,rect in enumerate(rects):
            if rect.collidepoint(pos) and levels[i] < MAX_MODULE_LEVEL:
                self.try_upgrade_module(i)
                return

    def say(self, text: str) -> None:
        self.message = text
        self.message_timer = 4.0

    def build_nebula_cache(self) -> None:
        self.nebula_cache = []
        for pos, radius in self.world.nebulae:
            surface = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            pygame.draw.circle(surface, (*NEBULA, 65), (radius, radius), radius)
            pygame.draw.circle(surface, (38, 28, 64, 35), (radius, radius), int(radius*0.65))
            self.nebula_cache.append((pos, radius, surface))

    def draw_tutorial(self) -> None:
        overlay=pygame.Surface(self.screen.get_size(),pygame.SRCALPHA)
        overlay.fill((0,0,0,225))
        self.screen.blit(overlay,(0,0))
        sw,sh=self.screen.get_size()
        panel=pygame.Rect(sw//2-430,45,860,sh-90)
        pygame.draw.rect(self.screen,PANEL,panel,border_radius=10)
        pygame.draw.rect(self.screen,PANEL_EDGE,panel,1,border_radius=10)
        self.screen.blit(self.big_font.render("CAPTAIN'S QUICKSTART",True,self.accent_color),(panel.x+24,panel.y+20))

        sections = [
            ("1. MOVE & EXPLORE", "Click a world or purple sensor contact to fly there. Shift+click inspects a planet. N opens Intel, U opens Ship status, and B toggles the sub-sector grid."),
            ("2. MAKE MONEY", "Mine or buy whole-number cargo. K ranks known trade routes. Planet boards offer contracts."),
            ("3. BUILD", "Colonize neutral worlds, develop them, then specialize mines, markets, yards, forts, or research outposts."),
            ("4. SURVIVE", "P handles diplomacy. Shops sell distinct weapons. Tab refits modules at your Shipyards. Pirates are fair game."),
            ("5. CONQUER", "Bombard hostile garrisons below 35%, recruit invasion troops, then invade. Preserving infrastructure costs more troops."),
            ("6. WIN", "Conquer 60%, dominate the economy, restore the regional Wayline, or eliminate every rival colony."),
        ]
        y=panel.y+82
        for heading,body in sections:
            self.screen.blit(self.font.render(heading,True,WARNING),(panel.x+30,y)); y+=25
            for line in wrap_text(self.small_font,body,panel.width-70):
                self.screen.blit(self.small_font.render(line,True,TEXT),(panel.x+42,y)); y+=19
            y+=10
        footer="F1 toggles this guide • F5 save • F9 load • Esc closes"
        self.screen.blit(self.small_font.render(footer,True,MUTED),(panel.x+24,panel.bottom-30))

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def draw(self) -> None:
        if self.scene == "title":
            self.draw_title(); pygame.display.flip(); return
        if self.scene == "setup":
            self.draw_match_setup(); pygame.display.flip(); return
        if self.scene == "settings":
            self.draw_settings(); pygame.display.flip(); return

        self.screen.fill(BACKGROUND)
        self.draw_nebulae()
        self.draw_stars()
        if self.sector_grid_open:
            self.draw_subsector_grid()
        if self.settings.show_radar_ring:
            self.draw_radar_ring()
        self.draw_planets()
        self.draw_sites()
        self.draw_bolts()
        self.draw_ships()
        self.draw_hud()
        self.draw_minimap()
        self.draw_quick_tabs()
        if self.intel_panel_open:
            self.draw_intel_panel()
        if self.ship_panel_open:
            self.draw_ship_panel()
        if self.settings.show_hover_info and not self.any_modal_open():
            self.draw_hover_info()

        if self.planet_menu_open:
            self.draw_planet_menu()
        if self.site_menu_open:
            self.draw_site_menu()
        if self.shop_open:
            self.draw_shop()
        if self.specialization_menu_open:
            self.draw_specialization_menu()
        if self.diplomacy_open:
            self.draw_diplomacy()
        if self.trade_computer_open:
            self.draw_trade_computer()
        if self.contracts_open:
            self.draw_contracts()
        if self.missions_open:
            self.draw_missions()
        if self.journal_open:
            self.draw_journal()
        if self.refit_overlay:
            self.draw_refit()
        if self.lore_overlay:
            self.draw_lore()
        if self.tutorial_open:
            self.draw_tutorial()
        if self.scene == "paused":
            self.draw_pause()
        if self.state != "playing":
            self.draw_end_state()
        pygame.display.flip()

    def draw_nebulae(self) -> None:
        expected = len(self.world.nebulae)
        if not hasattr(self, "nebula_cache") or len(self.nebula_cache) != expected:
            self.build_nebula_cache()

        w, h = self.screen.get_size()
        for pos, radius, surface in self.nebula_cache:
            sp = self.camera.world_to_screen(pos)
            if -radius <= sp.x <= w + radius and -radius <= sp.y <= h + radius:
                self.screen.blit(surface, (sp.x - radius, sp.y - radius))

    def draw_stars(self) -> None:
        w, h = self.screen.get_size()
        ticks = pygame.time.get_ticks() * 0.001
        for star in self.world.stars:
            sp = self.camera.world_to_screen(star)
            if -8 <= sp.x <= w+8 and -8 <= sp.y <= h+8:
                twinkle = 150 + int(70 * (0.5 + 0.5 * math.sin(star.x*0.013 + ticks)))
                pygame.draw.circle(self.screen, (twinkle, twinkle, min(255, twinkle+18)), sp, 1)

    def draw_radar_ring(self) -> None:
        pygame.draw.circle(
            self.screen, (25, 60, 72),
            self.camera.world_to_screen(self.player.pos),
            int(self.player.radar_range), 1
        )

    def draw_planets(self) -> None:
        w, h = self.screen.get_size()
        for p in self.world.planets:
            if not self.planet_visible(p):
                continue
            sp = self.camera.world_to_screen(p.pos)
            if not (-80 <= sp.x <= w+80 and -80 <= sp.y <= h+80):
                continue
            color = self.faction_color(p.owner)
            pygame.draw.circle(self.screen, (30, 38, 54), sp, p.radius+5)
            pygame.draw.circle(self.screen, color, sp, p.radius)
            pygame.draw.circle(self.screen, (220,225,210), sp + pygame.Vector2(-p.radius*0.25,-p.radius*0.25), max(2,p.radius//6))
            if p.defense:
                pygame.draw.circle(self.screen, color, sp, p.radius+10+p.defense*3, 1)
            if p is self.selected_planet:
                pygame.draw.circle(self.screen, TEXT, sp, p.radius+13, 2)
                spec_name=specialization_asset_name(p.specialization)
                if spec_name:
                    badge=ASSETS.icon("specializations",spec_name,1)
                    self.screen.blit(badge,(int(sp.x+p.radius+5),int(sp.y-p.radius-5)))
            label = self.tiny_font.render(p.name, True, TEXT)
            self.screen.blit(label, label.get_rect(midtop=(sp.x, sp.y+p.radius+6)))

    def draw_ships(self) -> None:
        for ship in self.all_ships():
            if not ship.alive or not self.ship_visible(ship):
                continue
            sp = self.camera.world_to_screen(ship.pos)
            heading = ship.velocity.normalize() if ship.velocity.length_squared() > 1 else pygame.Vector2(0,-1)
            draw_pixel_ship(
                self.screen, sp, heading,
                self.faction_color(ship.faction_id),
                self.faction_accent(ship.faction_id),
                enemy=ship.faction_id != PLAYER,
                ship=ship if ship.faction_id == PLAYER else None,
            )
            if ship.shields > 0 and (ship.shields < ship.max_shields or ship.last_damage_timer < 1):
                pygame.draw.circle(self.screen, self.faction_accent(ship.faction_id), sp, 28 if ship.faction_id == PLAYER else 24, 1)
            hull = pygame.Rect(int(sp.x-22), int(sp.y+27), 44, 4)
            shield = pygame.Rect(int(sp.x-22), int(sp.y+33), 44, 3)
            pygame.draw.rect(self.screen, (45,47,56), hull)
            pygame.draw.rect(self.screen, (45,47,56), shield)
            hf = hull.copy(); hf.width = int(hull.width * ship.health / ship.max_health)
            sf = shield.copy(); sf.width = int(shield.width * ship.shields / max(1, ship.max_shields))
            pygame.draw.rect(self.screen, self.faction_color(ship.faction_id), hf)
            pygame.draw.rect(self.screen, self.faction_accent(ship.faction_id), sf)

    def draw_bolts(self) -> None:
        for bolt in self.bolts:
            sp = self.camera.world_to_screen(bolt.pos)
            direction = bolt.velocity.normalize() if bolt.velocity.length_squared() else pygame.Vector2(1,0)
            pygame.draw.line(self.screen, self.faction_color(bolt.owner), sp, sp-direction*12, 3)

    def draw_hud(self) -> None:
        owned = sum(1 for p in self.world.planets if p.owner == PLAYER)
        income = sum(max(1,p.current_income//2) for p in self.world.planets if p.owner == PLAYER)
        panel = pygame.Rect(18,18,550,154)
        pygame.draw.rect(self.screen, PANEL, panel, border_radius=8)
        pygame.draw.rect(self.screen, PANEL_EDGE, panel, 1, border_radius=8)
        lines = [
            f"{self.identity.ship_name} • {self.player.weapon_name}",
            f"Credits {int(self.player.credits)}   Income +{income}/sec   Worlds {owned}",
            f"Hull {int(self.player.health)}/100   Shields {int(self.player.shields)}/{int(self.player.max_shields)}",
            f"Cargo {self.player.cargo_amount}/{self.player.cargo_capacity} {self.player.cargo_mineral or 'empty'}   Troops {self.player.marines}",
            f"Sector {sector_label(self.player.pos)}   Artifacts {self.artifact_points}   Relays {self.relays_activated}",
            "N intel • U ship • B sector grid • Shift+click inspect",
        ]
        insignia=ASSETS.icon("factions",f"insignia_{self.identity.insignia_index % 5}",1)
        self.screen.blit(insignia,(535,27))
        for i,line in enumerate(lines):
            self.screen.blit(self.small_font.render(line, True, TEXT if i<5 else MUTED), (32,29+i*20))
        if self.message_timer > 0:
            self.screen.blit(self.font.render(self.message, True, WARNING), (24,188))
        if self.mining:
            self.screen.blit(self.font.render("MINING", True, SUCCESS), (24,217))

    def draw_minimap(self) -> None:
        w,_ = self.screen.get_size()
        rect = pygame.Rect(w-226,18,196,156)
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=6)
        pygame.draw.rect(self.screen, PANEL_EDGE, rect, 1, border_radius=6)
        inner = rect.inflate(-14,-14)
        sx,sy = inner.width/WORLD_SIZE.x, inner.height/WORLD_SIZE.y
        for i,p in enumerate(self.world.planets):
            if i not in self.discovered:
                continue
            pygame.draw.circle(
                self.screen, self.faction_color(p.owner),
                (int(inner.x+p.pos.x*sx), int(inner.y+p.pos.y*sy)), 2
            )
        for site in self.sites:
            if not site.discovered:
                continue
            x=int(inner.x+site.pos.x*sx); y=int(inner.y+site.pos.y*sy)
            pygame.draw.rect(self.screen,(180,145,255),(x-2,y-2,4,4),1)
        for ship in self.all_ships():
            if not ship.alive or not self.ship_visible(ship):
                continue
            pygame.draw.circle(
                self.screen, self.faction_color(ship.faction_id),
                (int(inner.x+ship.pos.x*sx), int(inner.y+ship.pos.y*sy)), 4, 1
            )

    def draw_planet_menu(self) -> None:
        p = self.selected_planet
        if p is None:
            return
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0,0,0,190))
        self.screen.blit(overlay,(0,0))
        sw,sh = self.screen.get_size()
        owner = "Independent" if p.owner is None else self.identity.faction_name if p.owner == PLAYER else self.factions[p.owner].name
        title = self.big_font.render(p.name.upper(), True, self.faction_color(p.owner))
        self.screen.blit(title, title.get_rect(center=(sw//2,48)))
        micon=ASSETS.icon("minerals", mineral_asset_name(p.mineral), 1)
        self.screen.blit(micon,(sw//2-195,75))
        sub = self.small_font.render(
            f"{owner} • {p.mineral} x{p.richness:.1f} • {p.settlement_scale} • {p.specialization or 'general settlement'}",
            True, MUTED
        )
        self.screen.blit(sub, sub.get_rect(center=(sw//2+8,86)))
        host,_ = hostility_label(p.owner,self.factions,PLAYER)
        info=self.tiny_font.render(
            f"{p.climate} • {p.population_millions:.1f}m population • {p.government} • {host}", True, MUTED
        )
        self.screen.blit(info,info.get_rect(center=(sw//2,108)))
        for (_action,label,enabled),rect in self.planet_menu_rects():
            self.draw_button(rect,label,enabled)

    def draw_shop(self) -> None:
        p = self.selected_planet
        if p is None:
            return
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA); overlay.fill((0,0,0,205))
        self.screen.blit(overlay,(0,0))
        sw,sh = self.screen.get_size()
        title = self.big_font.render(f"{p.name.upper()} OUTFITTER", True, self.accent_color)
        self.screen.blit(title, title.get_rect(center=(sw//2,max(48,sh//2-205))))
        for name,rect in self.shop_rects():
            if name == "BACK":
                self.draw_button(rect,"BACK"); continue
            spec=WEAPONS[name]
            owned=name in self.player.owned_weapons
            status="EQUIPPED" if self.player.weapon_name==name else "OWNED" if owned else f"{spec.price} cr"
            pygame.draw.rect(self.screen,BUTTON_HOVER if rect.collidepoint(pygame.mouse.get_pos()) else BUTTON,rect,border_radius=6)
            pygame.draw.rect(self.screen,PANEL_EDGE,rect,1,border_radius=6)
            icon=ASSETS.icon("weapons",weapon_asset_name(name),2)
            self.screen.blit(icon,(rect.x+8,rect.y+3))
            self.screen.blit(self.font.render(f"{name}   {status}",True,TEXT),(rect.x+64,rect.y+8))
            desc=self.tiny_font.render(f"{spec.damage:g} dmg • {spec.cooldown:.3f}s cycle • planet x{spec.planet_multiplier:.2f}",True,MUTED)
            self.screen.blit(desc,(rect.x+64,rect.y+32))

    def draw_specialization_menu(self) -> None:
        p=self.selected_planet
        if p is None: return
        overlay=pygame.Surface(self.screen.get_size(),pygame.SRCALPHA); overlay.fill((0,0,0,210))
        self.screen.blit(overlay,(0,0))
        sw,sh=self.screen.get_size()
        title=self.big_font.render("SPECIALIZE COLONY",True,self.accent_color)
        self.screen.blit(title,title.get_rect(center=(sw//2,max(48,sh//2-205))))
        for label,rect in self.specialization_rects():
            self.draw_button(rect,label)

    def draw_diplomacy(self) -> None:
        overlay=pygame.Surface(self.screen.get_size(),pygame.SRCALPHA); overlay.fill((0,0,0,215))
        self.screen.blit(overlay,(0,0))
        sw,_=self.screen.get_size()
        title=self.big_font.render("DIPLOMACY",True,self.accent_color)
        self.screen.blit(title,title.get_rect(center=(sw//2,70)))
        for fid,rect in self.diplomacy_faction_rects():
            f=self.factions[fid]
            selected=fid==self.selected_faction_id
            pygame.draw.rect(self.screen, BUTTON_HOVER if selected else PANEL, rect, border_radius=6)
            pygame.draw.rect(self.screen, f.primary, rect, 2, border_radius=6)
            insignia=ASSETS.icon("factions",f"insignia_{fid}",2)
            self.screen.blit(insignia,(rect.x+8,rect.y+2))
            self.screen.blit(self.font.render(f.name,True,TEXT),(rect.x+62,rect.y+8))
            self.screen.blit(self.tiny_font.render(f"{f.state_name} • relation {f.relation:+d} • {f.personality}",True,MUTED),(rect.x+62,rect.y+31))
        f=self.factions[self.selected_faction_id]
        x=sw//2+25
        insignia=ASSETS.icon("factions",f"insignia_{self.selected_faction_id}",2)
        self.screen.blit(insignia,(x,126))
        self.screen.blit(self.font.render(f"Talking to: {f.name}",True,f.primary),(x+58,140))
        for label,rect in self.diplomacy_action_rects():
            self.draw_button(rect,label)

    def draw_refit(self) -> None:
        overlay=pygame.Surface(self.screen.get_size(),pygame.SRCALPHA); overlay.fill((0,0,0,215))
        self.screen.blit(overlay,(0,0))
        sw,sh=self.screen.get_size()
        panel=pygame.Rect(sw//2-440,sh//2-270,880,540)
        pygame.draw.rect(self.screen,PANEL,panel,border_radius=10)
        pygame.draw.rect(self.screen,PANEL_EDGE,panel,1,border_radius=10)
        self.screen.blit(self.big_font.render("SHIP REFIT",True,self.accent_color),(panel.x+24,panel.y+20))
        yard=self.near_shipyard()
        status=f"Docked at {yard.name}" if yard else "NOT IN SHIPYARD RANGE"
        self.screen.blit(self.font.render(status,True,SUCCESS if yard else WARNING),(panel.x+26,panel.y+70))

        sprite=player_ship_surface(self.player,self.player_color,self.accent_color)
        preview=pygame.transform.scale(sprite,(sprite.get_width()*7,sprite.get_height()*7))
        self.screen.blit(preview,preview.get_rect(center=(panel.x+190,panel.y+255)))
        self.screen.blit(self.small_font.render("Installed hardware is visible on the hull",True,MUTED),(panel.x+55,panel.y+360))

        levels=(self.player.shield_level,self.player.engine_level,self.player.radar_level,self.player.cargo_level)
        desc=(
            f"{int(self.player.max_shields)} cap • {self.player.shield_regen:.1f}/s regen",
            f"top speed {int(self.player.speed)}",
            f"sensor range {int(self.player.radar_range)}",
            f"hold capacity {self.player.cargo_capacity}",
        )
        groups=("shield","engine","radar","cargo")
        y=panel.y+120
        for i,(name,group,level,d) in enumerate(zip(MODULE_NAMES,groups,levels,desc),start=1):
            cost=upgrade_cost(level)
            rect=pygame.Rect(panel.x+390,y,455,64)
            enabled=yard is not None and cost is not None
            pygame.draw.rect(self.screen,BUTTON_HOVER if rect.collidepoint(pygame.mouse.get_pos()) and enabled else BUTTON,rect,border_radius=6)
            pygame.draw.rect(self.screen,PANEL_EDGE,rect,1,border_radius=6)
            icon=ASSETS.icon("modules",f"{group}_t{level}",2)
            self.screen.blit(icon,(rect.x+9,rect.y+8))
            price="MAX" if cost is None else f"{cost} cr"
            self.screen.blit(self.font.render(f"{i}. {name} T{level}   {price}",True,TEXT if enabled or cost is None else MUTED),(rect.x+64,rect.y+9))
            self.screen.blit(self.small_font.render(d,True,MUTED),(rect.x+64,rect.y+35))
            y+=78
        self.screen.blit(self.small_font.render("Esc closes • weapon hardware changes when you equip a different gun",True,MUTED),(panel.x+24,panel.bottom-30))

    def draw_lore(self) -> None:
        overlay=pygame.Surface(self.screen.get_size(),pygame.SRCALPHA); overlay.fill((0,0,0,215))
        self.screen.blit(overlay,(0,0))
        sw,sh=self.screen.get_size()
        panel=pygame.Rect(sw//2-390,55,780,sh-110)
        pygame.draw.rect(self.screen,PANEL,panel,border_radius=10)
        self.screen.blit(self.big_font.render("THE SEVERANCE",True,self.accent_color),(panel.x+24,panel.y+22))
        y=panel.y+82
        for line in wrap_text(self.font,SETTING_BLURB,panel.width-48):
            self.screen.blit(self.font.render(line,True,TEXT),(panel.x+24,y)); y+=25
        if self.selected_planet:
            y+=20
            self.screen.blit(self.font.render(self.selected_planet.name,True,WARNING),(panel.x+24,y)); y+=28
            for line in wrap_text(self.small_font,self.selected_planet.lore,panel.width-48):
                self.screen.blit(self.small_font.render(line,True,MUTED),(panel.x+24,y)); y+=20

    def draw_title(self) -> None:
        self.screen.fill(BACKGROUND)
        self.draw_nebulae()
        self.draw_stars()
        sw,sh=self.screen.get_size()
        title=self.big_font.render("SLOPFEST",True,self.player_color)
        sub=self.font.render("the Wayline reconnects, and everyone wants a piece",True,MUTED)
        self.screen.blit(title,title.get_rect(center=(sw//2,sh//2-165)))
        self.screen.blit(sub,sub.get_rect(center=(sw//2,sh//2-123)))
        draw_pixel_ship(
            self.screen,
            pygame.Vector2(sw//2,sh//2-62),
            pygame.Vector2(0,-1),
            self.player_color,self.accent_color
        )
        for label,rect in self.title_buttons():
            self.draw_button(rect,label)
        save_note = "Autosave available" if has_save() else "No saved match yet"
        footer=self.tiny_font.render(f"v0.96.4 • {save_note} • F1 quickstart • pygame-ce",True,MUTED)
        self.screen.blit(footer,footer.get_rect(center=(sw//2,sh-24)))
        if self.message_timer > 0 and self.scene == "title":
            msg=self.small_font.render(self.message,True,WARNING)
            self.screen.blit(msg,msg.get_rect(center=(sw//2,sh-48)))

    def draw_pause(self) -> None:
        overlay=pygame.Surface(self.screen.get_size(),pygame.SRCALPHA)
        overlay.fill((0,0,0,200))
        self.screen.blit(overlay,(0,0))
        sw,sh=self.screen.get_size()
        title=self.big_font.render("PAUSED",True,self.accent_color)
        self.screen.blit(title,title.get_rect(center=(sw//2,70)))

        y = 112
        objective_title = self.small_font.render("VICTORY PROGRESS", True, WARNING)
        self.screen.blit(objective_title, objective_title.get_rect(center=(sw//2, y)))
        y += 24
        for line in self.victory_progress_lines():
            image = self.tiny_font.render(line, True, MUTED)
            self.screen.blit(image, image.get_rect(center=(sw//2, y)))
            y += 18

        for label,rect in self.pause_buttons():
            self.draw_button(rect,label)

    def draw_settings(self) -> None:
        self.screen.fill(BACKGROUND)
        self.draw_nebulae()
        self.draw_stars()
        sw,sh=self.screen.get_size()
        title=self.big_font.render("SETTINGS",True,self.accent_color)
        self.screen.blit(title,title.get_rect(center=(sw//2,sh//2-215)))
        values={
            "FULLSCREEN":"ON" if self.settings.fullscreen else "OFF",
            "AUTO PLANET MENU":"ON" if self.settings.auto_open_planet_menu else "OFF",
            "HOVER INTEL":"ON" if self.settings.show_hover_info else "OFF",
            "RADAR RING":"ON" if self.settings.show_radar_ring else "OFF",
            "ENEMY PRESSURE":self.settings.pressure_name.upper(),
            "SOUND VOLUME":f"{self.settings.master_volume}%",
            "SHOW TUTORIAL":"ON" if self.settings.show_tutorial else "OFF",
            "BACK":"",
        }
        for label,rect in self.settings_rows():
            self.draw_button(rect,label if not values[label] else f"{label}: {values[label]}")
        foot=self.tiny_font.render("Settings persist between sessions.",True,MUTED)
        self.screen.blit(foot,foot.get_rect(center=(sw//2,sh-26)))

    def draw_end_state(self) -> None:
        overlay=pygame.Surface(self.screen.get_size(),pygame.SRCALPHA)
        overlay.fill((0,0,0,210))
        self.screen.blit(overlay,(0,0))
        sw,sh=self.screen.get_size()

        if self.state=="won":
            headline="MATCH WON"
            color=SUCCESS
        else:
            headline="MATCH LOST"
            color=DANGER

        image=self.big_font.render(headline,True,color)
        self.screen.blit(image,image.get_rect(center=(sw//2,sh//2-95)))

        y=sh//2-40
        for line in wrap_text(self.font,self.victory_reason or "The match has ended.",720)[:4]:
            rendered=self.font.render(line,True,TEXT)
            self.screen.blit(rendered,rendered.get_rect(center=(sw//2,y)))
            y+=27

        y+=12
        for line in self.victory_progress_lines():
            rendered=self.small_font.render(line,True,MUTED)
            self.screen.blit(rendered,rendered.get_rect(center=(sw//2,y)))
            y+=21

        sub=self.font.render("R rematch • Enter title",True,TEXT)
        self.screen.blit(sub,sub.get_rect(center=(sw//2,sh//2+150)))
