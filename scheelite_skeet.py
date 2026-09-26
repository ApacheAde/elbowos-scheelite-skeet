#!/usr/bin/env python3
"""Scheelite Skeet — neon skeet-gallery arcade for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "SCHEELITE SKEET"
HANDLE = "x.com/ElbowOS"
OUT = "/home/workdir/artifacts/scheelite_skeet_ElbowOS.mp4"

BG = (8, 6, 22)
GOLD = (246, 212, 74)
PALE = (255, 236, 170)
CYAN = (77, 240, 255)
MAG = (255, 61, 138)
VIO = (123, 140, 255)
ORNG = (255, 120, 48)
WHITE = (240, 246, 255)


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class Burst:
    def __init__(self, x, y, col):
        self.bits = []
        for _ in range(14):
            a = random.uniform(0, math.tau)
            s = random.uniform(4, 16)
            self.bits.append([x, y, math.cos(a) * s, math.sin(a) * s, col, 18])

    def tick(self):
        live = []
        for b in self.bits:
            b[0] += b[2]
            b[1] += b[3]
            b[3] += 0.35
            b[5] -= 1
            if b[5] > 0:
                live.append(b)
        self.bits = live

    def draw(self, s):
        for x, y, _, _, col, life in self.bits:
            pygame.draw.circle(s, col, (int(x), int(y)), max(2, life // 5))


class Pigeon:
    def __init__(self):
        self.from_left = random.random() < 0.5
        self.x = -40.0 if self.from_left else W + 40.0
        self.y = random.uniform(420, 1180)
        spd = random.uniform(11, 17)
        self.vx = spd if self.from_left else -spd
        self.vy = random.uniform(-10, -4)
        self.r = random.choice((26, 30, 34))
        self.spin = random.uniform(0, math.tau)
        self.alive = True
        self.uv = random.random() < 0.22

    def tick(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.22
        self.spin += 0.18
        if self.x < -80 or self.x > W + 80 or self.y > H + 40:
            self.alive = False

    def draw(self, s):
        col = CYAN if self.uv else GOLD
        glow = (40, 80, 110) if self.uv else (70, 50, 10)
        pygame.draw.circle(s, glow, (int(self.x), int(self.y)), self.r + 10)
        pygame.draw.circle(s, col, (int(self.x), int(self.y)), self.r)
        pygame.draw.circle(s, PALE if not self.uv else WHITE, (int(self.x), int(self.y)), self.r - 10, 3)
        dx, dy = math.cos(self.spin) * (self.r - 6), math.sin(self.spin) * (self.r - 6)
        pygame.draw.line(s, BG, (self.x - dx, self.y - dy), (self.x + dx, self.y + dy), 3)


class Bolt:
    def __init__(self, x, y, ang):
        self.x, self.y = x, y
        self.vx = math.cos(ang) * 34
        self.vy = math.sin(ang) * 34
        self.alive = True

    def tick(self):
        self.x += self.vx
        self.y += self.vy
        if self.y < -20 or self.x < -20 or self.x > W + 20:
            self.alive = False

    def draw(self, s):
        pygame.draw.circle(s, MAG, (int(self.x), int(self.y)), 9)
        pygame.draw.circle(s, WHITE, (int(self.x), int(self.y)), 4)
        pygame.draw.line(
            s, MAG,
            (self.x - self.vx * 0.6, self.y - self.vy * 0.6),
            (self.x, self.y), 4,
        )


class Game:
    def __init__(self):
        self.score = 0
        self.combo = 0
        self.ang = -math.pi / 2
        self.cool = 0
        self.pigeons = []
        self.bolts = []
        self.bursts = []
        self.spawn = 0
        self.stars = [(random.randrange(W), random.randrange(H), random.randint(1, 3)) for _ in range(90)]
        self.shake = 0
        self.flash = 0

    def fire(self):
        if self.cool > 0:
            return
        px, py = W // 2, H - 220
        self.bolts.append(Bolt(px + math.cos(self.ang) * 70, py + math.sin(self.ang) * 70, self.ang))
        self.cool = 7

    def autoplay(self):
        live = [p for p in self.pigeons if p.alive]
        if live:
            tgt = min(live, key=lambda p: (p.x - W / 2) ** 2 + (p.y - (H - 220)) ** 2)
            want = math.atan2(tgt.y - (H - 220), tgt.x - W / 2)
            diff = (want - self.ang + math.pi) % math.tau - math.pi
            self.ang += clamp(diff, -0.12, 0.12)
            if abs(diff) < 0.10 and self.cool == 0:
                self.fire()
        else:
            self.ang += math.sin(pygame.time.get_ticks() * 0.004) * 0.02
        self.ang = clamp(self.ang, -math.pi + 0.35, -0.35)

    def tick(self, keys=None, auto=False):
        if auto:
            self.autoplay()
        elif keys is not None:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.ang -= 0.08
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.ang += 0.08
            self.ang = clamp(self.ang, -math.pi + 0.35, -0.35)
            if keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]:
                self.fire()
        if self.cool:
            self.cool -= 1
        self.spawn -= 1
        if self.spawn <= 0:
            self.pigeons.append(Pigeon())
            self.spawn = random.randint(10, 20)
        for p in self.pigeons:
            p.tick()
        for b in self.bolts:
            b.tick()
        for p in self.pigeons:
            if not p.alive:
                continue
            for b in self.bolts:
                if not b.alive:
                    continue
                if (p.x - b.x) ** 2 + (p.y - b.y) ** 2 <= (p.r + 10) ** 2:
                    b.alive = False
                    p.alive = False
                    pts = 250 if p.uv else 100
                    self.combo += 1
                    self.score += pts + self.combo * 15
                    self.bursts.append(Burst(p.x, p.y, CYAN if p.uv else GOLD))
                    self.shake = 8
                    self.flash = 6
        self.pigeons = [p for p in self.pigeons if p.alive]
        self.bolts = [b for b in self.bolts if b.alive]
        for br in self.bursts:
            br.tick()
        self.bursts = [br for br in self.bursts if br.bits]
        if self.shake:
            self.shake -= 1
        if self.flash:
            self.flash -= 1
        if not self.pigeons and self.combo and self.spawn > 8:
            self.combo = max(0, self.combo - 1)

    def draw(self, s, font, big, tiny):
        ox = random.randint(-self.shake, self.shake) if self.shake else 0
        oy = random.randint(-self.shake, self.shake) if self.shake else 0
        s.fill(BG)
        for x, y, r in self.stars:
            pygame.draw.circle(s, (28, 32, 70), (x + ox // 2, y + oy // 2), r)
        for i in range(8):
            yy = 280 + i * 170
            pygame.draw.line(s, (18, 16, 48), (40, yy + oy), (W - 40, yy + oy), 1)
        pygame.draw.rect(s, (16, 12, 40), (0, H - 160, W, 160))
        pygame.draw.rect(s, GOLD, (0, H - 164, W, 6))
        pygame.draw.rect(s, (30, 22, 70), (80, H - 250, W - 160, 18), border_radius=8)
        pygame.draw.rect(s, VIO, (80, H - 250, W - 160, 18), 2, border_radius=8)
        px, py = W // 2 + ox, H - 220 + oy
        pygame.draw.circle(s, (40, 18, 50), (px, py + 28), 48)
        pygame.draw.circle(s, MAG, (px, py + 28), 36)
        pygame.draw.circle(s, WHITE, (px, py + 28), 12)
        bx = px + math.cos(self.ang) * 78
        by = py + math.sin(self.ang) * 78
        pygame.draw.line(s, GOLD, (px, py), (bx, by), 14)
        pygame.draw.circle(s, PALE, (int(bx), int(by)), 10)
        for p in self.pigeons:
            p.draw(s)
        for b in self.bolts:
            b.draw(s)
        for br in self.bursts:
            br.draw(s)
        if self.flash:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((255, 220, 90, 28 * self.flash))
            s.blit(veil, (0, 0))
        banner = pygame.Surface((W, 210), pygame.SRCALPHA)
        banner.fill((8, 6, 22, 210))
        s.blit(banner, (0, 0))
        t = big.render(TITLE, True, GOLD)
        s.blit(t, t.get_rect(center=(W // 2, 58)))
        sc = font.render(f"SCORE  {self.score}", True, CYAN)
        s.blit(sc, sc.get_rect(center=(W // 2, 118)))
        cmb = tiny.render(f"STREAK  {self.combo}    UV CLAY +250", True, MAG)
        s.blit(cmb, cmb.get_rect(center=(W // 2, 168)))
        foot = pygame.Surface((W, 90), pygame.SRCALPHA)
        foot.fill((8, 6, 22, 200))
        s.blit(foot, (0, H - 90))
        h = font.render(HANDLE, True, PALE)
        s.blit(h, h.get_rect(center=(W // 2, H - 46)))


def overlay_fonts():
    pygame.font.init()
    return (
        pygame.font.SysFont("dejavusans", 42, bold=True),
        pygame.font.SysFont("dejavusans", 56, bold=True),
        pygame.font.SysFont("dejavusans", 28, bold=True),
    )


def play():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    font, big, tiny = overlay_fonts()
    g = Game()
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                return
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                pygame.quit()
                return
        g.tick(keys=pygame.key.get_pressed(), auto=False)
        g.draw(screen, font, big, tiny)
        pygame.display.flip()
        clock.tick(FPS)


def record():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    surface = pygame.Surface((W, H))
    font, big, tiny = overlay_fonts()
    g = Game()
    frames = FPS * 15
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "20", "-preset", "fast", "-movflags", "+faststart",
        OUT,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for _ in range(frames):
            g.tick(auto=True)
            g.draw(surface, font, big, tiny)
            proc.stdin.write(pygame.image.tostring(surface, "RGB"))
    finally:
        proc.stdin.close()
        rc = proc.wait()
    pygame.quit()
    if rc != 0:
        raise SystemExit(f"ffmpeg failed with {rc}")
    print("wrote", OUT)


def main():
    if "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1":
        record()
    else:
        play()


if __name__ == "__main__":
    main()
