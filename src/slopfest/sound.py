from __future__ import annotations
from array import array
import math
import pygame

class SoundManager:
    def __init__(self, volume: float = 0.7) -> None:
        self.available = False
        self.master = max(0.0, min(1.0, volume))
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=256)
            self.sounds = {
                "ui": self._tone(660, 0.045, 0.18),
                "cash": self._sequence(((720,0.045),(920,0.060)), 0.18),
                "laser": self._sweep(840, 410, 0.085, 0.20),
                "hit": self._sweep(180, 95, 0.110, 0.24),
                "discover": self._sequence(((440,0.070),(660,0.070),(990,0.120)), 0.18),
                "save": self._sequence(((520,0.050),(780,0.080)), 0.16),
            }
            self.available = True
        except pygame.error:
            self.available = False

    def set_volume(self, volume: float) -> None:
        self.master = max(0.0, min(1.0, volume))

    def play(self, name: str, gain: float = 1.0) -> None:
        if not self.available or self.master <= 0:
            return
        sound = self.sounds.get(name)
        if sound is None:
            return
        sound.set_volume(max(0.0, min(1.0, self.master * gain)))
        sound.play()

    def _buffer(self, samples: list[float]) -> pygame.mixer.Sound:
        ints = array("h", (max(-32767, min(32767, int(v * 32767))) for v in samples))
        return pygame.mixer.Sound(buffer=ints.tobytes())

    def _tone(self, hz: float, seconds: float, amplitude: float) -> pygame.mixer.Sound:
        rate = 22050
        count = max(1, int(rate * seconds))
        samples = []
        for i in range(count):
            envelope = 1.0 - i / count
            samples.append(math.sin(2*math.pi*hz*i/rate) * amplitude * envelope)
        return self._buffer(samples)

    def _sweep(self, start: float, end: float, seconds: float, amplitude: float) -> pygame.mixer.Sound:
        rate = 22050
        count = max(1, int(rate * seconds))
        phase = 0.0
        samples = []
        for i in range(count):
            t = i / max(1, count-1)
            hz = start + (end-start) * t
            phase += 2*math.pi*hz/rate
            samples.append(math.sin(phase) * amplitude * ((1.0-t) ** 0.7))
        return self._buffer(samples)

    def _sequence(self, notes: tuple[tuple[float,float],...], amplitude: float) -> pygame.mixer.Sound:
        rate = 22050
        samples: list[float] = []
        for hz, seconds in notes:
            count = max(1, int(rate * seconds))
            for i in range(count):
                envelope = 1.0 - i / count
                samples.append(math.sin(2*math.pi*hz*i/rate) * amplitude * envelope)
        return self._buffer(samples)
