"""Shadow of the Bamboo: an original, deterministic ninja game and Jev test harness."""

from __future__ import annotations

import argparse
import getpass
import json
import math
import os
import queue
import random
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame as pg

ROOT = Path(__file__).resolve().parent
WORLD = 2600
GROUND = 286
DT = 1 / 60
MACRO_FRAMES = 18
ACTIONS = {
    "wait": "Stand still. Let a projectile pass or wait to land.",
    "left": "Move left.",
    "right": "Move right toward the rescue gate.",
    "jump_left": "Move left and jump if grounded; hold to jump again after landing.",
    "jump_right": "Move right and jump if grounded; hold to jump again after landing.",
    "throw_left": "Move left and throw a shuriken left, if cooldown is ready.",
    "throw_right": "Move right and throw a shuriken right, if cooldown is ready.",
    "jump_throw_left": "Jump/move left and throw left, if ready.",
    "jump_throw_right": "Jump/move right and throw right, if ready.",
    "slash": "Stand and slash with sword in facing direction; reaches 54 pixels.",
}


@dataclass
class Enemy:
    x: float
    y: float = GROUND
    hp: int = 2
    cooldown: float = 1.6
    origin: float = 0

    def __post_init__(self):
        self.origin = self.x


@dataclass
class Shot:
    x: float
    y: float
    vx: float
    hostile: bool = False
    life: float = 2.0


class Game:
    def __init__(self, seed=7):
        self.seed = seed
        self.x, self.y, self.vy = 64.0, float(GROUND), 0.0
        self.facing, self.hp = 1, 5
        self.grounded = True
        self.cooldown = self.sword_cd = self.invincible = self.slash_time = 0.0
        self.elapsed = 0.0
        self.kills = 0
        self.status = "playing"
        self.platforms = [
            (220, 224, 115),
            (460, 178, 110),
            (720, 224, 140),
            (1040, 200, 125),
            (1340, 154, 140),
            (1620, 214, 140),
            (1920, 190, 150),
            (2180, 224, 120),
        ]
        self.scrolls = [[510, 162, False], [1410, 138, False], [1995, 174, False]]
        self.enemies = [
            Enemy(x, cooldown=1.4 + i * 0.25)
            for i, x in enumerate([380, 680, 960, 1240, 1560, 1860, 2170, 2380])
        ]
        self.shots: list[Shot] = []
        self.sparks: list[list] = []
        self.rng = random.Random(seed)

    @property
    def collected(self):
        return sum(bool(s[2]) for s in self.scrolls)

    def burst(self, x, y, color):
        for _ in range(10):
            self.sparks.append(
                [
                    x,
                    y,
                    self.rng.uniform(-60, 60),
                    self.rng.uniform(-90, 10),
                    0.45,
                    color,
                ]
            )

    def damage(self):
        if self.invincible <= 0:
            self.hp -= 1
            self.invincible = 1.25
            self.burst(self.x, self.y - 18, (244, 114, 109))
            if self.hp <= 0:
                self.status = "lost"

    def hit_enemy(self, e, damage=1):
        e.hp -= damage
        self.burst(e.x, e.y - 16, (235, 179, 111))
        if e.hp <= 0:
            self.enemies.remove(e)
            self.kills += 1

    def step(self, action="wait", controls=None):
        if self.status != "playing":
            return
        self.elapsed += DT
        direction, jump, throw, slash = controls or (
            -1 if "left" in action else 1 if "right" in action else 0,
            "jump" in action,
            "throw" in action,
            action == "slash",
        )
        for name in ("cooldown", "sword_cd", "invincible", "slash_time"):
            setattr(self, name, max(0, getattr(self, name) - DT))
        if direction:
            self.facing = direction
        self.x = max(12, min(WORLD - 12, self.x + direction * 145 * DT))
        if jump and self.grounded:
            self.vy = -435
            self.grounded = False
        previous_y = self.y
        self.vy += 720 * DT
        self.y += self.vy * DT
        self.grounded = False
        if self.vy >= 0:
            for px, py, pw in sorted(self.platforms, key=lambda p: p[1]):
                if px - 7 < self.x < px + pw + 7 and previous_y <= py <= self.y:
                    self.y, self.vy, self.grounded = float(py), 0, True
                    break
            if self.y >= GROUND:
                self.y, self.vy, self.grounded = float(GROUND), 0, True
        if throw and self.cooldown <= 0:
            self.shots.append(
                Shot(self.x + 12 * self.facing, self.y - 17, self.facing * 360)
            )
            self.cooldown = 0.28
        if slash and self.sword_cd <= 0:
            self.sword_cd, self.slash_time = 0.32, 0.16
            for e in list(self.enemies):
                if -8 < (e.x - self.x) * self.facing < 54 and abs(e.y - self.y) < 38:
                    self.hit_enemy(e, 2)
            self.shots = [
                s
                for s in self.shots
                if not (
                    s.hostile
                    and abs(s.x - self.x) < 54
                    and abs(s.y - (self.y - 16)) < 35
                )
            ]
        for e in self.enemies:
            distance = self.x - e.x
            if abs(distance) < 380:
                e.x += (1 if distance > 0 else -1) * 27 * DT
                e.cooldown -= DT
                if e.cooldown <= 0:
                    self.shots.append(
                        Shot(e.x, e.y - 17, 155 if distance > 0 else -155, True, 3)
                    )
                    e.cooldown = 2.5
                if abs(distance) < 20 and abs(e.y - self.y) < 25:
                    self.damage()
        for s in list(self.shots):
            s.x += s.vx * DT
            s.life -= DT
            remove = s.life <= 0
            if s.hostile:
                if abs(s.x - self.x) < 12 and self.y - 30 < s.y < self.y:
                    self.damage()
                    remove = True
            else:
                for e in list(self.enemies):
                    if abs(s.x - e.x) < 14 and e.y - 30 < s.y < e.y:
                        self.hit_enemy(e)
                        remove = True
                        break
            if remove:
                self.shots.remove(s)
        for s in self.scrolls:
            if not s[2] and abs(self.x - s[0]) < 23 and abs(self.y - 18 - s[1]) < 27:
                s[2] = True
                self.burst(s[0], s[1], (230, 205, 137))
        for p in self.sparks:
            p[0] += p[2] * DT
            p[1] += p[3] * DT
            p[3] += 220 * DT
            p[4] -= DT
        self.sparks = [p for p in self.sparks if p[4] > 0]
        if self.x > WORLD - 100 and self.collected == 3 and self.hp > 0:
            self.status = "won"

    def state(self):
        return {
            "goal": "Collect all three scrolls, then reach the rescue gate at x=2500. Stay alive.",
            "coordinates": "x rightward; y downward; player y is feet; scroll y is center.",
            "player": {
                "x": round(self.x),
                "feet_y": round(self.y),
                "vy": round(self.vy),
                "grounded": self.grounded,
                "facing": self.facing,
                "hp": self.hp,
                "throw_ready": self.cooldown == 0,
                "sword_ready": self.sword_cd == 0,
            },
            "physics": {
                "macro_frames": MACRO_FRAMES,
                "speed": 145,
                "jump_height": 130,
                "jump_distance": 175,
                "platforms": "one-way, land from above; no pits; jump auto-repeats on landing",
                "network": "Simulation pauses while awaiting your response.",
            },
            "remaining_scrolls": [
                {"x": s[0], "y": s[1], "dx": round(s[0] - self.x)}
                for s in self.scrolls
                if not s[2]
            ],
            "platforms": [
                {"x": x, "top_y": y, "width": w}
                for x, y, w in self.platforms
                if abs(x - self.x) < 550
            ],
            "enemies": [
                {"dx": round(e.x - self.x), "feet_y": e.y, "hp": e.hp}
                for e in self.enemies
                if abs(e.x - self.x) < 420
            ],
            "incoming_shuriken": [
                {"dx": round(s.x - self.x), "y": round(s.y), "vx": s.vx}
                for s in self.shots
                if s.hostile and abs(s.x - self.x) < 260
            ],
            "collected": self.collected,
            "status": self.status,
        }


def demo_action(game):
    targets = [s for s in game.scrolls if not s[2]]
    target = targets[0][0] if targets else 2520
    d = "right" if target > game.x else "left"
    nearest = next(
        (e for e in game.enemies if abs(e.x - game.x) < 48 and abs(e.y - game.y) < 30),
        None,
    )
    if nearest and (nearest.x - game.x) * game.facing > 0:
        return "slash"
    return "jump_throw_" + d if targets and abs(target - game.x) < 260 else "throw_" + d


class JevWorker:
    """One daemon worker; stale generations never modify a restarted game."""

    def __init__(self, key):
        self.key = key
        self.requests = queue.Queue(maxsize=1)
        self.results = queue.Queue()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        client = None
        try:
            from typesafe_sdk import Choice, RetryPolicy, TypeSafeClient

            client = TypeSafeClient(
                api_key=self.key, timeout=15, retry=RetryPolicy(max_retries=0)
            )
            while True:
                job = self.requests.get()
                if job is None:
                    return
                generation, state = job
                start = time.perf_counter()
                try:
                    response = client.system_one(
                        state=state,
                        questions={
                            "action": Choice(
                                instructions="Control this ninja. Collect the remaining scrolls in order, "
                                "using platforms to reach high ones. Jump toward scrolls; reverse if you "
                                "overshoot. Throw toward enemies at your height, slash nearby enemies. "
                                "After collecting all scrolls head right to x=2500. Choose one macro.",
                                criteria=ACTIONS,
                            )
                        },
                    )
                    answer = response.choices["action"]
                    if str(answer.choice) not in ACTIONS:
                        raise ValueError("Unknown action returned by model")
                    self.results.put(
                        (
                            generation,
                            str(answer.choice),
                            dict(answer.probabilities),
                            float(answer.confidence),
                            (time.perf_counter() - start) * 1000,
                            None,
                        )
                    )
                except Exception as exc:  # noqa: BLE001 - surface worker failures in the UI
                    message = str(exc).replace(self.key, "[REDACTED]")
                    self.results.put((generation, None, {}, 0, 0, message[:400]))
        except Exception as exc:  # noqa: BLE001 - surface client setup failures in the UI
            self.results.put(
                (-1, None, {}, 0, 0, str(exc).replace(self.key, "[REDACTED]")[:400])
            )
        finally:
            if client:
                client.close()

    def close(self):
        try:
            self.requests.put_nowait(None)
        except queue.Full:
            pass


# Small original pixel sprites; no ROMs or external art.
SPRITE = [
    "    hhhh    ",
    "   hhhhhhh  ",
    "   hsssssh  ",
    "   hhheehh  ",
    "    hhhh    ",
    "  bbbbbbbb  ",
    " bbbbbbbbbb ",
    " bb bbbb bb ",
    " ss bbbb ss ",
    "    gggg    ",
    "   bbbbbb   ",
    "   bb  bb   ",
    "  bbb  bbb  ",
    "  hhh  hhh  ",
]


class View:
    def __init__(self):
        pg.init()
        self.screen = pg.display.set_mode((1280, 780))
        pg.display.set_caption("竹影 · Shadow of the Bamboo | Jev Test Lab")
        self.scene = pg.Surface((480, 320))
        font_path = "/System/Library/Fonts/STHeiti Light.ttc"
        self.fonts = {
            size: pg.font.Font(font_path if Path(font_path).exists() else None, size)
            for size in (14, 16, 18, 22, 30, 42)
        }
        self.sprites = {}
        for enemy in (False, True):
            sprite = pg.Surface((24, 28), pg.SRCALPHA)
            colors = {
                "h": (22, 33, 38),
                "s": (213, 178, 147),
                "e": (249, 233, 183),
                "b": (175, 71, 70) if enemy else (72, 168, 150),
                "g": (220, 191, 112),
            }
            for y, row in enumerate(SPRITE):
                for x, c in enumerate(row):
                    if c in colors:
                        pg.draw.rect(sprite, colors[c], (x * 2, y * 2, 2, 2))
            self.sprites[enemy] = sprite
        self.buttons = {
            "manual": pg.Rect(36, 693, 128, 42),
            "demo": pg.Rect(174, 693, 128, 42),
            "ai": pg.Rect(312, 693, 128, 42),
            "restart": pg.Rect(650, 693, 112, 42),
            "pause": pg.Rect(772, 693, 112, 42),
        }

    def text(self, text, x, y, size=16, color=(199, 211, 202), surface=None):
        (surface or self.screen).blit(
            self.fonts[size].render(text, True, color), (x, y)
        )

    def ninja(self, x, y, enemy=False, facing=1, airborne=False):
        sprite = self.sprites[enemy]
        if facing == -1:
            sprite = pg.transform.flip(sprite, True, False)
        self.scene.blit(sprite, (round(x) - 12, round(y) - 28))
        scarf = (226, 161, 91) if not enemy else (181, 82, 73)
        pg.draw.polygon(
            self.scene,
            scarf,
            [
                (x - facing * 5, y - 22),
                (x - facing * 26, y - 27 if airborne else y - 18),
                (x - facing * 21, y - 20),
                (x - facing * 5, y - 19),
            ],
        )

    def world(self, g, ticks):
        c = self.scene
        cam = max(0, min(WORLD - 480, g.x - 175))
        for y in range(320):
            pg.draw.line(
                c, (13 + y // 26, 28 + y // 17, 37 + y // 26), (0, y), (480, y)
            )
        pg.draw.circle(c, (188, 205, 177), (373 - int(cam * 0.025), 57), 24)
        pg.draw.circle(c, (27, 47, 51), (385 - int(cam * 0.025), 50), 24)
        for layer, speed, color in [(0, 0.18, (28, 58, 59)), (1, 0.4, (36, 77, 70))]:
            for i in range(17):
                x = int(i * 57 - cam * speed) % 610 - 60
                top = 28 + (i * 31 + layer * 19) % 110
                pg.draw.rect(c, color, (x, top, 5 + layer * 2, 300))
                for yy in range(top + 10, 280, 33):
                    pg.draw.line(c, (48, 91, 77), (x, yy), (x + 7, yy))
                    pg.draw.polygon(
                        c, color, [(x, yy), (x - 28, yy - 14), (x - 10, yy + 2)]
                    )
                    pg.draw.polygon(
                        c, color, [(x, yy), (x + 32, yy - 17), (x + 14, yy + 2)]
                    )
        # Mist bands and drifting fireflies.
        mist = pg.Surface((480, 320), pg.SRCALPHA)
        for i in range(4):
            pg.draw.ellipse(
                mist,
                (158, 196, 174, 9),
                (-90 + math.sin(ticks * 0.15 + i) * 30, 160 + i * 26, 660, 48),
            )
        c.blit(mist, (0, 0))
        for i in range(18):
            x = (i * 47 - cam * 0.6 + math.sin(ticks + i) * 5) % 480
            y = 70 + (i * 37) % 180 + math.sin(ticks * 0.7 + i) * 6
            pg.draw.rect(c, (133, 162, 108), (x, y, 1, 1))
        pg.draw.rect(c, (20, 36, 34), (0, GROUND, 480, 34))
        pg.draw.rect(c, (99, 129, 91), (0, GROUND, 480, 3))
        for i in range(70):
            x = int(i * 17 - cam) % 500
            pg.draw.line(c, (73, 110, 80), (x, GROUND), (x + 2, GROUND - 5 - i % 4))
            pg.draw.rect(c, (39, 54, 44), (x, 299 + i % 15, 5, 2))
        for px, py, pw in g.platforms:
            x = px - cam
            if -150 < x < 490:
                pg.draw.rect(c, (61, 68, 46), (x, py, pw, 9))
                pg.draw.rect(c, (130, 143, 94), (x, py, pw, 3))
                pg.draw.line(c, (49, 63, 47), (x + 18, py + 9), (x + 18, GROUND), 4)
                pg.draw.line(
                    c, (49, 63, 47), (x + pw - 18, py + 9), (x + pw - 18, GROUND), 4
                )
        gx = 2510 - cam
        pg.draw.rect(c, (157, 81, 64), (gx - 28, 205, 6, 81))
        pg.draw.rect(c, (157, 81, 64), (gx + 27, 205, 6, 81))
        pg.draw.rect(c, (171, 93, 68), (gx - 41, 201, 89, 7))
        pg.draw.rect(c, (195, 140, 90), (gx - 35, 218, 77, 5))
        self.ninja(gx, GROUND, False, -1)
        for sx, sy, found in g.scrolls:
            if not found:
                x, y = sx - cam, sy + math.sin(ticks * 2 + sx) * 2
                pg.draw.circle(c, (64, 77, 53), (int(x), int(y)), 13, 1)
                pg.draw.rect(c, (223, 200, 145), (x - 5, y - 7, 10, 14))
                pg.draw.rect(c, (153, 104, 63), (x - 7, y - 8, 14, 3))
                pg.draw.rect(c, (153, 104, 63), (x - 7, y + 6, 14, 3))
                pg.draw.line(c, (98, 86, 56), (x - 2, y - 3), (x + 2, y + 3), 2)
        for e in g.enemies:
            if -25 < e.x - cam < 505:
                self.ninja(e.x - cam, e.y, True, 1 if g.x > e.x else -1)
        if g.invincible <= 0 or int(g.invincible * 14) % 2:
            self.ninja(g.x - cam, g.y, facing=g.facing, airborne=not g.grounded)
        if g.slash_time > 0:
            sx = g.x - cam + g.facing * 25
            pg.draw.arc(
                c,
                (243, 230, 171),
                (sx - 22, g.y - 43, 44, 44),
                -0.9 if g.facing > 0 else 2.2,
                1.4 if g.facing > 0 else 4.3,
                3,
            )
        for s in g.shots:
            x, y = s.x - cam, s.y
            color = (230, 112, 91) if s.hostile else (207, 224, 188)
            pg.draw.polygon(
                c,
                color,
                [
                    (x - 5, y),
                    (x - 1, y - 1),
                    (x, y - 5),
                    (x + 1, y - 1),
                    (x + 5, y),
                    (x + 1, y + 1),
                    (x, y + 5),
                    (x - 1, y + 1),
                ],
            )
        for x, y, _, _, _, color in g.sparks:
            pg.draw.rect(c, color, (x - cam, y, 2, 2))
        # Bottom map inside the scene.
        pg.draw.line(c, (62, 84, 69), (14, 310), (466, 310), 2)
        for sx, _, found in g.scrolls:
            pg.draw.circle(
                c,
                (95, 128, 106) if found else (222, 189, 112),
                (14 + int(sx / WORLD * 452), 310),
                3,
            )
        pg.draw.circle(c, (115, 230, 183), (14 + int(g.x / WORLD * 452), 310), 3)
        self.screen.blit(pg.transform.scale(c, (864, 576)), (28, 100))

    def draw(self, app):
        g = app.game
        self.screen.fill((12, 23, 26))
        self.text("竹影", 28, 20, 42, (224, 220, 184))
        self.text("SHADOW OF THE BAMBOO", 134, 30, 16, (142, 175, 157))
        self.text(
            "原创忍者试验场  /  CHAPTER 01 · 月下救援", 135, 55, 14, (106, 137, 127)
        )
        self.text("生命 " + "● " * max(0, g.hp), 605, 33, 18, (218, 159, 120))
        self.text(f"卷轴 {g.collected} / 3", 796, 34, 16, (218, 199, 139))
        self.world(g, pg.time.get_ticks() / 1000)
        pg.draw.rect(self.screen, (20, 36, 38), (916, 100, 336, 576), border_radius=12)
        self.text("CONTROL ROOM", 938, 122, 14, (129, 166, 146))
        names = {
            "manual": "手动游玩",
            "demo": "离线规则演示",
            "ai": "Jev AI · 官方直连",
        }
        self.text(names[app.mode], 938, 150, 22, (232, 228, 199))
        state = "游戏进行中"
        if app.busy:
            state = "正在思考 · 游戏时间已暂停"
        if app.paused:
            state = "已暂停 · P 继续"
        if app.error:
            state = "已暂停 · 查看下方提示"
        self.text(state, 938, 188, 14, (205, 177, 118))
        pg.draw.line(self.screen, (49, 69, 63), (938, 222), (1228, 222))
        self.text("当前动作", 938, 242, 14, (133, 158, 148))
        self.text(app.action.replace("_", " "), 938, 266, 22, (226, 231, 207))
        self.text(f"模型耗时  {app.latency:.0f} ms", 938, 306, 16)
        self.text(
            f"置信度    {app.confidence:.0%}" if app.mode == "ai" else "置信度    —",
            938,
            334,
        )
        self.text(f"API 调用  {app.calls} / {app.limit}", 938, 362)
        self.text(f"击败敌人  {g.kills}    游戏时间  {g.elapsed:.1f}s", 938, 390, 14)
        pg.draw.line(self.screen, (49, 69, 63), (938, 426), (1228, 426))
        if app.error:
            self.text("需要处理", 938, 446, 18, (233, 152, 123))
            lines = app.error_lines()
            for i, line in enumerate(lines[:7]):
                self.text(line, 938, 476 + i * 21, 14, (217, 174, 147))
        else:
            self.text("任务 / MISSION", 938, 446, 14, (133, 158, 148))
            for i, line in enumerate(
                [
                    "01  跳上竹台，收集三枚卷轴",
                    "02  飞镖远攻，刀击挡镖",
                    "03  到达森林尽头的朱红鸟居",
                ]
            ):
                self.text(line, 938, 478 + i * 29, 14)
            self.text("AI 每次动作执行 18 帧。", 938, 587, 14, (128, 154, 141))
            self.text(
                "等待回复时冻结世界，避免延迟误伤。", 938, 610, 14, (128, 154, 141)
            )
        for name, rect in self.buttons.items():
            active = app.mode == name
            pg.draw.rect(
                self.screen,
                (54, 100, 82) if active else (25, 44, 43),
                rect,
                border_radius=6,
            )
            label = {
                "manual": "1 手动",
                "demo": "2 规则演示",
                "ai": "3 Jev AI",
                "restart": "R 重新开始",
                "pause": "P 暂停 / 继续",
            }[name]
            self.text(label, rect.x + 12, rect.y + 12, 14, (218, 226, 202))
        self.text(
            "移动 A/D 或 ←/→    跳跃 Space/W    飞镖 J    刀击 K    退出 Esc",
            30,
            750,
            14,
            (133, 163, 149),
        )
        self.text("F2 配置 / 更换官方 Key", 982, 748, 14, (129, 166, 146))
        if g.status != "playing" or app.paused:
            veil = pg.Surface((864, 576), pg.SRCALPHA)
            veil.fill((8, 20, 24, 165))
            self.screen.blit(veil, (28, 100))
            title = (
                "月下归来 · 救援成功"
                if g.status == "won"
                else "影落竹林"
                if g.status == "lost"
                else "暂 停"
            )
            self.text(title, 250, 313, 42, (231, 221, 177))
            self.text(
                "按 R 重新开始" if g.status != "playing" else "按 P 继续", 346, 376, 18
            )
        if app.key_dialog:
            veil = pg.Surface((1280, 780), pg.SRCALPHA)
            veil.fill((5, 15, 18, 205))
            self.screen.blit(veil, (0, 0))
            pg.draw.rect(
                self.screen, (24, 43, 43), (300, 228, 680, 326), border_radius=14
            )
            self.text("连接 Jev AI", 334, 254, 30, (230, 222, 182))
            self.text("粘贴 TypeSafe 官方 API Key，按 Enter 连接。", 334, 304, 18)
            pg.draw.rect(
                self.screen, (11, 28, 29), (334, 345, 612, 48), border_radius=6
            )
            masked = "•" * min(len(app.key_buffer), 48)
            self.text(masked or "Cmd+V / Ctrl+V 粘贴密钥", 347, 359, 16)
            self.text(
                app.key_error or "密钥仅保存在当前进程内存中，不写入文件。",
                334,
                411,
                16,
                (229, 165, 132) if app.key_error else (141, 171, 151),
            )
            pg.draw.rect(
                self.screen, (60, 106, 85), (748, 463, 198, 48), border_radius=6
            )
            self.text("连接并开始 AI 测试", 768, 478, 16)
            self.text("Esc 取消    Cmd+A 全选替换", 334, 480, 14)
        pg.display.flip()


class App:
    def __init__(self, mode="manual", key=None, limit=200):
        self.game = Game()
        self.mode, self.key, self.limit = mode, key, limit
        self.worker = None
        self.generation = 0
        self.busy = False
        self.calls = self.frames_left = 0
        self.action = "wait"
        self.probabilities = {}
        self.confidence = self.latency = 0.0
        self.error = ""
        self.paused = False
        self.key_dialog = False
        self.key_buffer = ""
        self.key_error = ""
        self.key_selected = False
        self.view = View()
        (ROOT / "artifacts").mkdir(exist_ok=True)
        self.log = (
            ROOT / "artifacts" / f"session-{datetime.now(UTC):%Y%m%d-%H%M%S-%f}.jsonl"
        ).open("w")
        self.set_mode(mode)

    def set_mode(self, mode):
        self.generation += 1
        self.mode = mode
        self.frames_left = 0
        self.action = "wait"
        self.error = ""
        self.probabilities = {}
        self.confidence = self.latency = 0.0
        if mode == "ai" and not self.key:
            self.error = "缺少 TypeSafe Key，按 3 或 F2 在窗口中配置。"
            self.open_key_dialog()
        elif mode == "ai" and not self.worker:
            self.worker = JevWorker(self.key)

    def open_key_dialog(self):
        self.key_dialog = True
        self.key_buffer = ""
        self.key_error = ""
        self.key_selected = False
        pg.key.start_text_input()

    def submit_key(self):
        key = self.key_buffer.strip()
        if not key:
            self.key_error = "请先粘贴官方 Key。"
            return
        if key.startswith("vck_"):
            self.key_error = "这是 Vercel Key，请使用 TypeSafe 官方 Key。"
            return
        if any(c.isspace() for c in key) or len(key) < 16:
            self.key_error = "密钥格式不完整，请重新复制。"
            return
        if self.worker:
            self.worker.close()
        self.worker = None
        self.busy = False
        self.key = key
        self.key_buffer = ""
        self.key_dialog = False
        self.paused = False
        pg.key.stop_text_input()
        if self.game.status != "playing":
            self.game = Game()
        self.set_mode("ai")

    def key_event(self, event):
        if event.type == pg.TEXTINPUT:
            if self.key_selected:
                self.key_buffer = ""
                self.key_selected = False
            self.key_buffer = (self.key_buffer + event.text)[:512]
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if pg.Rect(748, 463, 198, 48).collidepoint(event.pos):
                self.submit_key()
        elif event.type == pg.KEYDOWN:
            modifier = event.mod & (pg.KMOD_META | pg.KMOD_CTRL)
            if event.key == pg.K_ESCAPE:
                self.key_buffer = ""
                self.key_dialog = False
                pg.key.stop_text_input()
                self.set_mode("manual")
            elif event.key == pg.K_RETURN:
                self.submit_key()
            elif modifier and event.key == pg.K_a:
                self.key_selected = True
            elif event.key == pg.K_BACKSPACE:
                self.key_buffer = "" if self.key_selected else self.key_buffer[:-1]
                self.key_selected = False
            elif modifier and event.key == pg.K_v:
                # Read clipboard only in direct response to the user's paste gesture.
                try:
                    if sys.platform == "darwin":
                        pasted = subprocess.run(
                            ["/usr/bin/pbpaste"],
                            capture_output=True,
                            text=True,
                            check=True,
                            timeout=2,
                        ).stdout
                    else:
                        if not pg.scrap.get_init():
                            pg.scrap.init()
                        pasted = (
                            (pg.scrap.get(pg.SCRAP_TEXT) or b"")
                            .decode("utf-8")
                            .rstrip("\x00")
                        )
                    self.key_buffer = pasted.strip()[:512]
                    self.key_selected = False
                    self.key_error = ""
                except (OSError, subprocess.SubprocessError, UnicodeError, pg.error):
                    self.key_error = "无法读取剪贴板，请尝试手动输入。"

    def restart(self):
        self.game = Game()
        self.paused = False
        # Session-wide API budget is intentionally not reset by R.
        self.set_mode(self.mode)

    def tick(self, controls=None):
        if self.worker:
            try:
                generation, action, probs, confidence, latency, error = (
                    self.worker.results.get_nowait()
                )
                self.busy = False
                if generation in (self.generation, -1) and self.mode == "ai":
                    if error:
                        self.error = error
                    else:
                        self.action, self.probabilities = action, probs
                        self.confidence, self.latency = confidence, latency
                        self.frames_left = MACRO_FRAMES
                        self.log.write(
                            json.dumps(
                                {
                                    "generation": generation,
                                    "call": self.calls,
                                    "state": self.game.state(),
                                    "action": action,
                                    "confidence": confidence,
                                    "latency_ms": latency,
                                    "probabilities": probs,
                                },
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
                        self.log.flush()
            except queue.Empty:
                pass
        if self.game.status != "playing" or self.paused or self.key_dialog:
            return
        if self.mode == "manual":
            self.action = "manual"
            self.game.step(controls=controls or (0, False, False, False))
        elif self.mode == "demo":
            self.action = demo_action(self.game)
            self.game.step(self.action)
        elif not self.error and not self.busy:
            if self.frames_left > 0:
                self.game.step(self.action)
                self.frames_left -= 1
            elif self.calls >= self.limit:
                self.error = (
                    "本次会话已达 API 调用上限。可切换手动模式继续，或重新启动程序。"
                )
            else:
                self.worker.requests.put_nowait((self.generation, self.game.state()))
                self.calls += 1
                self.busy = True

    def error_lines(self):
        if "rate" in self.error.lower() or "429" in self.error:
            message = "接口限流，游戏已暂停。稍后按 3 重试，或按 1 切换手动。"
        elif "401" in self.error or "unauthorized" in self.error.lower():
            message = "密钥验证失败。按 F2 输入有效的 TypeSafe 官方 Key。"
        elif "timeout" in self.error.lower():
            message = "请求超时，游戏已暂停。按 3 重试，或按 1 切换手动。"
        else:
            message = self.error
        # Pixel-width wrapping, including CJK.
        lines, line = [], ""
        for char in message:
            if self.view.fonts[14].size(line + char)[0] > 284:
                lines.append(line)
                line = ""
            line += char
        lines.append(line)
        return lines

    def run(self, smoke_frames=0, screenshot=None):
        clock = pg.time.Clock()
        running, frames = True, 0
        try:
            while running:
                for event in pg.event.get():
                    command = None
                    if event.type == pg.QUIT:
                        running = False
                    elif self.key_dialog:
                        self.key_event(event)
                        continue
                    elif event.type == pg.KEYDOWN:
                        if event.key == pg.K_F2:
                            self.open_key_dialog()
                            continue
                        command = {
                            pg.K_1: "manual",
                            pg.K_2: "demo",
                            pg.K_3: "ai",
                            pg.K_r: "restart",
                            pg.K_p: "pause",
                            pg.K_ESCAPE: "quit",
                        }.get(event.key)
                    elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                        command = next(
                            (
                                k
                                for k, r in self.view.buttons.items()
                                if r.collidepoint(event.pos)
                            ),
                            None,
                        )
                    if command in ("manual", "demo", "ai"):
                        self.set_mode(command)
                    elif command == "restart":
                        self.restart()
                    elif command == "pause":
                        self.paused = not self.paused
                    elif command == "quit":
                        running = False
                if not running:
                    break
                keys = pg.key.get_pressed()
                controls = (
                    int(keys[pg.K_d] or keys[pg.K_RIGHT])
                    - int(keys[pg.K_a] or keys[pg.K_LEFT]),
                    keys[pg.K_SPACE] or keys[pg.K_w] or keys[pg.K_UP],
                    keys[pg.K_j],
                    keys[pg.K_k],
                )
                self.tick(controls)
                self.view.draw(self)
                frames += 1
                if screenshot and frames == (smoke_frames or 1):
                    pg.image.save(self.view.screen, screenshot)
                if smoke_frames and frames >= smoke_frames:
                    break
                if not smoke_frames:
                    clock.tick(60)
        finally:
            if self.worker:
                self.worker.close()
            self.log.close()
            pg.quit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["manual", "demo", "ai"], default="manual")
    parser.add_argument("--ask-key", action="store_true")
    parser.add_argument("--max-calls", type=int, default=200)
    parser.add_argument("--smoke-frames", type=int, default=0)
    parser.add_argument("--screenshot")
    args = parser.parse_args()
    if args.max_calls < 1:
        parser.error("--max-calls must be positive")
    key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if args.ask_key and not key:
        key = getpass.getpass("TypeSafe 官方 API Key（输入不显示）: ").strip()
    App(args.mode, key, args.max_calls).run(args.smoke_frames, args.screenshot)


if __name__ == "__main__":
    main()
