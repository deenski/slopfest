from __future__ import annotations

import pygame


class Camera:
    def __init__(self, viewport_size: tuple[int, int]) -> None:
        self.viewport = pygame.Vector2(viewport_size)
        self.center = pygame.Vector2(0, 0)

    def update(self, target: pygame.Vector2, dt: float) -> None:
        # Gentle smoothing keeps movement from feeling mechanically locked.
        blend = min(1.0, dt * 7.0)
        self.center += (target - self.center) * blend

    def world_to_screen(self, world_pos: pygame.Vector2) -> pygame.Vector2:
        return world_pos - self.center + self.viewport / 2

    def screen_to_world(self, screen_pos: tuple[int, int] | pygame.Vector2) -> pygame.Vector2:
        return pygame.Vector2(screen_pos) + self.center - self.viewport / 2
