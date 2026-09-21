from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


PRESSURE_NAMES = ("Relaxed", "Standard", "Hot")


@dataclass
class Settings:
    fullscreen: bool = False
    auto_open_planet_menu: bool = True
    show_radar_ring: bool = True
    enemy_pressure: int = 0
    master_volume: int = 70
    show_tutorial: bool = True
    show_hover_info: bool = True

    @property
    def pressure_name(self) -> str:
        return PRESSURE_NAMES[self.enemy_pressure]

    @property
    def ai_profile(self) -> dict[str, float]:
        # Even Standard is intentionally gentler than the old prototype.
        return (
            {"grace": 115.0, "aggro": 315.0, "raid_after": 260.0, "raid_chance": 0.004},
            {"grace": 80.0, "aggro": 380.0, "raid_after": 190.0, "raid_chance": 0.007},
            {"grace": 45.0, "aggro": 470.0, "raid_after": 125.0, "raid_chance": 0.012},
        )[self.enemy_pressure]

    @staticmethod
    def path() -> Path:
        return Path.home() / ".slopfest_settings.json"

    @classmethod
    def load(cls) -> "Settings":
        try:
            raw = json.loads(cls.path().read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        obj = cls()
        for key in asdict(obj):
            if key in raw:
                setattr(obj, key, raw[key])
        obj.enemy_pressure = max(0, min(2, int(obj.enemy_pressure)))
        obj.master_volume = max(0, min(100, int(obj.master_volume)))
        return obj

    def save(self) -> None:
        try:
            self.path().write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        except OSError:
            # Settings persistence is nice-to-have, never a reason to crash a game.
            pass
