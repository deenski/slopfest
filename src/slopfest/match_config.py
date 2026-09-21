from __future__ import annotations
from dataclasses import dataclass, asdict

GALAXY_OPTIONS = (26, 34, 44)
RIVAL_OPTIONS = (2, 3, 4)
CREDIT_OPTIONS = (150, 200, 300)

@dataclass
class MatchConfig:
    seed: int = 97
    planet_count: int = 34
    rival_count: int = 4
    starting_credits: int = 200

    conquest_fraction: float = 0.60
    economic_credits: int = 4500
    economic_income: int = 42
    wayline_relays: int = 4

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict) -> "MatchConfig":
        cfg = cls()
        for key in asdict(cfg):
            if key in raw:
                setattr(cfg, key, raw[key])
        cfg.seed = int(cfg.seed)
        cfg.planet_count = int(cfg.planet_count)
        cfg.rival_count = max(2, min(4, int(cfg.rival_count)))
        cfg.starting_credits = int(cfg.starting_credits)
        return cfg
