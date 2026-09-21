from __future__ import annotations

from pathlib import Path
import pygame


ASSET_ROOT = Path(__file__).resolve().parent / "assets"


class AssetLibrary:
    """Small cached loader for the project's pixel-art assets.

    Missing assets intentionally return a generated placeholder so an asset typo does not
    turn into a startup crash during development.
    """

    def __init__(self) -> None:
        self._images: dict[str, pygame.Surface] = {}
        self._scaled: dict[tuple[str, int], pygame.Surface] = {}

    def image(self, relative: str) -> pygame.Surface:
        if relative in self._images:
            return self._images[relative]
        path = ASSET_ROOT / relative
        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except (pygame.error, OSError):
            image = self._placeholder(relative)
        self._images[relative] = image
        return image

    def scaled(self, relative: str, scale: int = 1) -> pygame.Surface:
        key = (relative, scale)
        if key in self._scaled:
            return self._scaled[key]
        image = self.image(relative)
        if scale == 1:
            result = image
        else:
            result = pygame.transform.scale(
                image,
                (image.get_width() * scale, image.get_height() * scale),
            )
        self._scaled[key] = result
        return result

    def icon(self, group: str, name: str, scale: int = 1) -> pygame.Surface:
        return self.scaled(f"{group}/{name}.png", scale)

    def _placeholder(self, label: str) -> pygame.Surface:
        surf = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.rect(surf, (50, 18, 25), surf.get_rect(), border_radius=2)
        pygame.draw.rect(surf, (255, 91, 100), surf.get_rect(), 1, border_radius=2)
        pygame.draw.line(surf, (255, 91, 100), (4, 4), (16, 16), 2)
        pygame.draw.line(surf, (255, 91, 100), (16, 4), (4, 16), 2)
        return surf


ASSETS = AssetLibrary()


def mineral_asset_name(mineral: str) -> str:
    return mineral.lower().replace("-", "_").replace(" ", "_")


def specialization_asset_name(specialization: str | None) -> str | None:
    if not specialization:
        return None
    return specialization.lower().replace(" ", "_")


def weapon_asset_name(weapon: str) -> str:
    return weapon.lower().replace(" ", "_").replace("-", "_")


def unique_asset_name(module: str) -> str:
    return module.lower().replace(" ", "_").replace("-", "_")
