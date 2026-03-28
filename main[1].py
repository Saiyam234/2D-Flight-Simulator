"""
main.py – 2D Flight Simulator
Main game loop, rendering, HUD, and input handling.

Controls:
  UP    – pitch up
  DOWN  – pitch down
  RIGHT – increase throttle
  LEFT  – decrease throttle
  R     – reset / restart
  ESC   – quit
"""

import sys
import math
import pygame

from plane import Plane
from physics import landing_score

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

SCREEN_W, SCREEN_H = 1280, 720
FPS = 60
TITLE = "2D Flight Simulator"

# World scale: pixels per metre (horizontal).  Altitude uses a different scale.
PX_PER_M_H = 0.15      # horizontal
PX_PER_M_V = 0.20      # vertical

# Ground altitude in world coords
GROUND_Y = 0.0

# Runway start/end in world X (metres)
RUNWAY_X1   =  200.0
RUNWAY_X2   = 1400.0
RUNWAY_H_PX = 18        # pixel height of runway stripe

# Colour palette
C_SKY_TOP    = (10,  25,  60)
C_SKY_BOT    = (80, 140, 210)
C_GROUND     = (45,  90,  35)
C_RUNWAY     = (60,  60,  65)
C_RUNWAY_MRK = (220, 220, 60)
C_HUD_BG     = (0,   0,   0,  140)
C_WHITE      = (255, 255, 255)
C_YELLOW     = (255, 220,  50)
C_RED        = (255,  70,  70)
C_GREEN      = (80,  220, 100)
C_CYAN       = (80,  220, 255)
C_ORANGE     = (255, 150,  40)
C_DARK       = (20,  20,  30)

# ═══════════════════════════════════════════════════════════════════════════════
#  ASSET GENERATION  (draw sprites with pygame.draw – no external images needed)
# ═══════════════════════════════════════════════════════════════════════════════

def make_plane_surface(scale: float = 1.0) -> pygame.Surface:
    """Draw a top-down silhouette of a plane on a transparent surface."""
    w, h = int(80 * scale), int(30 * scale)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)

    cx, cy = w // 2, h // 2

    # Fuselage
    pygame.draw.ellipse(surf, C_WHITE, (cx - int(32*scale), cy - int(5*scale),
                                        int(64*scale), int(10*scale)))
    # Wings
    wing_pts = [
        (cx - int(8*scale),  cy),
        (cx + int(10*scale), cy),
        (cx + int(4*scale),  cy - int(14*scale)),
        (cx - int(14*scale), cy - int(14*scale)),
    ]
    pygame.draw.polygon(surf, (200, 210, 230), wing_pts)
    # Tail
    tail_pts = [
        (cx - int(28*scale), cy),
        (cx - int(20*scale), cy),
        (cx - int(22*scale), cy - int(8*scale)),
        (cx - int(30*scale), cy - int(8*scale)),
    ]
    pygame.draw.polygon(surf, (180, 190, 210), tail_pts)
    # Cockpit window
    pygame.draw.ellipse(surf, C_CYAN,
                        (cx + int(12*scale), cy - int(3*scale),
                         int(10*scale), int(6*scale)))
    # Engine nacelles
    for dy in (-9, 8):
        pygame.draw.ellipse(surf, (160, 170, 190),
                            (cx - int(4*scale), cy + int(dy*scale),
                             int(16*scale), int(5*scale)))
    return surf


def make_explosion_frames(radius: int = 40, frames: int = 12) -> list[pygame.Surface]:
    surfs = []
    colors = [C_YELLOW, C_ORANGE, C_RED, (120, 50, 20), (80, 80, 80)]
    for i in range(frames):
        r = int(radius * (i + 1) / frames)
        s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        alpha = int(255 * (1 - i / frames))
        col = colors[min(i * len(colors) // frames, len(colors) - 1)]
        pygame.draw.circle(s, (*col, alpha), (r + 1, r + 1), r)
        surfs.append(s)
    return surfs


# ═══════════════════════════════════════════════════════════════════════════════
#  CAMERA
# ═══════════════════════════════════════════════════════════════════════════════

class Camera:
    """Follows the plane, converting world coords to screen pixels."""

    def __init__(self):
        self.cam_x = 0.0   # world metres at screen centre-left
        self.cam_y = 0.0   # world metres at screen centre

    def update(self, plane: Plane, dt: float):
        # Smoothly track plane with lag
        target_x = plane.x - SCREEN_W / PX_PER_M_H * 0.35
        target_y = plane.y - SCREEN_H / PX_PER_M_V * 0.40
        lag = min(1.0, 4.0 * dt)
        self.cam_x += (target_x - self.cam_x) * lag
        self.cam_y += (target_y - self.cam_y) * lag

    def world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        sx = int((wx - self.cam_x) * PX_PER_M_H)
        sy = int(SCREEN_H - (wy - self.cam_y) * PX_PER_M_V)
        return sx, sy

    def screen_to_world(self, sx: int, sy: int) -> tuple[float, float]:
        wx = sx / PX_PER_M_H + self.cam_x
        wy = (SCREEN_H - sy) / PX_PER_M_V + self.cam_y
        return wx, wy


# ═══════════════════════════════════════════════════════════════════════════════
#  DRAWING HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def draw_sky(screen: pygame.Surface, altitude: float):
    """Gradient sky that shifts colour with altitude."""
    t = min(1.0, altitude / 8000)
    top = tuple(int(C_SKY_TOP[i] + (C_SKY_BOT[i] - C_SKY_TOP[i]) * (1 - t))
                for i in range(3))
    bot = C_SKY_BOT if t < 0.1 else C_SKY_TOP
    for row in range(SCREEN_H):
        blend = row / SCREEN_H
        color = tuple(int(top[i] + (bot[i] - top[i]) * blend) for i in range(3))
        pygame.draw.line(screen, color, (0, row), (SCREEN_W, row))


def draw_ground(screen: pygame.Surface, cam: Camera):
    ground_sy = cam.world_to_screen(0, GROUND_Y)[1]
    if ground_sy < SCREEN_H:
        pygame.draw.rect(screen, C_GROUND,
                         (0, ground_sy, SCREEN_W, SCREEN_H - ground_sy))


def draw_runway(screen: pygame.Surface, cam: Camera):
    """Draw the runway with markings."""
    x1, sy = cam.world_to_screen(RUNWAY_X1, GROUND_Y)
    x2, _  = cam.world_to_screen(RUNWAY_X2, GROUND_Y)
    rw = x2 - x1
    if rw <= 0:
        return

    rect = pygame.Rect(x1, sy - RUNWAY_H_PX, rw, RUNWAY_H_PX)
    pygame.draw.rect(screen, C_RUNWAY, rect)

    # Centre-line dashes
    dash_len = max(4, rw // 20)
    gap      = dash_len
    cx_y     = sy - RUNWAY_H_PX // 2
    for i in range(0, rw, dash_len + gap):
        pygame.draw.rect(screen, C_RUNWAY_MRK,
                         (x1 + i, cx_y - 2, dash_len, 4))

    # Threshold bars
    for tx in (x1, x2 - 6):
        pygame.draw.rect(screen, C_RUNWAY_MRK, (tx, sy - RUNWAY_H_PX, 6, RUNWAY_H_PX))


def draw_clouds(screen: pygame.Surface, cam: Camera, tick: int):
    """Simple parallax clouds."""
    cloud_data = [
        (300, 800, 180, 50),
        (900, 1200, 220, 60),
        (1800, 600, 160, 45),
        (2600, 1500, 200, 55),
        (3400, 900, 170, 48),
        (4200, 400, 190, 52),
    ]
    for wx, wy, cw, ch in cloud_data:
        drift = (tick * 0.01) % 500
        cx, cy = cam.world_to_screen(wx + drift, wy)
        if -cw < cx < SCREEN_W + cw and 0 < cy < SCREEN_H:
            # puff of ellipses
            surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
            for ox, oy, r in [(0, 0, ch//2), (cw//3, -ch//4, ch//2),
                               (2*cw//3, 0, ch//2), (cw//6, ch//4, ch//3)]:
                pygame.draw.ellipse(surf, (255, 255, 255, 160),
                                    (ox, oy + ch//2, r * 2, r))
            screen.blit(surf, (cx - cw // 2, cy - ch // 2))


def draw_stars(screen: pygame.Surface, altitude: float):
    """Stars appear above ~5000 m."""
    if altitude < 3000:
        return
    alpha = min(255, int((altitude - 3000) / 2000 * 200))
    star_positions = [(100, 30), (250, 80), (400, 20), (600, 60),
                      (750, 15), (900, 45), (1100, 70), (1200, 25)]
    for sx, sy in star_positions:
        surf = pygame.Surface((4, 4), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 255, 255, alpha), (2, 2), 2)
        screen.blit(surf, (sx, sy))


# ═══════════════════════════════════════════════════════════════════════════════
#  HUD
# ═══════════════════════════════════════════════════════════════════════════════

def draw_hud(screen: pygame.Surface, plane: Plane, font: pygame.font.Font,
             small_font: pygame.font.Font):
    """Draw instrument panel overlay."""
    panel_w, panel_h = 260, 230
    hud_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    hud_surf.fill((0, 0, 0, 160))
    pygame.draw.rect(hud_surf, (80, 120, 180, 80), (0, 0, panel_w, panel_h), 2)

    speed_kts  = plane.speed * 1.944
    alt_ft     = plane.altitude * 3.281
    vs_fpm     = plane.vy  * 196.85
    fuel_pct   = plane.fuel_pct * 100

    lines = [
        ("AIRSPEED",  f"{speed_kts:6.1f} kts", C_CYAN),
        ("ALTITUDE",  f"{alt_ft:6.0f} ft",  C_GREEN),
        ("V/SPEED",   f"{vs_fpm:+6.0f} fpm", C_YELLOW if abs(vs_fpm) < 1000 else C_RED),
        ("PITCH",     f"{plane.pitch:+5.1f}°", C_WHITE),
        ("THROTTLE",  f"{plane.throttle * 100:5.1f}%", C_ORANGE),
        ("FUEL",      f"{fuel_pct:5.1f}%",
                      C_GREEN if fuel_pct > 30 else C_RED),
        ("LIFT",      f"{plane.lift:7.0f} N", C_CYAN),
        ("DRAG",      f"{plane.drag:7.0f} N", C_RED),
    ]

    title = small_font.render("✈ INSTRUMENTS", True, C_CYAN)
    hud_surf.blit(title, (8, 6))

    for i, (label, value, color) in enumerate(lines):
        y = 30 + i * 24
        lbl = small_font.render(f"{label:<9}", True, (160, 180, 200))
        val = small_font.render(value, True, color)
        hud_surf.blit(lbl, (8, y))
        hud_surf.blit(val, (110, y))

    screen.blit(hud_surf, (10, 10))

    # ── Throttle bar ──────────────────────────────────────────────────────────
    bar_x, bar_y = 10, 250
    bar_h = 160
    pygame.draw.rect(screen, (40, 40, 40), (bar_x, bar_y, 20, bar_h))
    fill = int(bar_h * plane.throttle)
    col = C_GREEN if plane.throttle < 0.8 else C_RED
    pygame.draw.rect(screen, col, (bar_x, bar_y + bar_h - fill, 20, fill))
    pygame.draw.rect(screen, C_WHITE, (bar_x, bar_y, 20, bar_h), 1)
    lbl = small_font.render("THR", True, C_WHITE)
    screen.blit(lbl, (bar_x - 2, bar_y + bar_h + 4))

    # ── Artificial horizon ────────────────────────────────────────────────────
    ah_cx, ah_cy, ah_r = 60, 370, 40
    ah_surf = pygame.Surface((ah_r * 2 + 2, ah_r * 2 + 2), pygame.SRCALPHA)

    # Sky half
    pygame.draw.circle(ah_surf, (60, 120, 200, 220), (ah_r, ah_r), ah_r)
    # Ground half (clip with pitch)
    pitch_offset = int(plane.pitch / 45.0 * ah_r)
    ground_y_ah = ah_r - pitch_offset
    pygame.draw.rect(ah_surf, (120, 80, 40, 220),
                     (0, ground_y_ah, ah_r * 2, ah_r * 2 - ground_y_ah + ah_r))
    # Border
    pygame.draw.circle(ah_surf, C_WHITE, (ah_r, ah_r), ah_r, 2)
    # Centre cross
    pygame.draw.line(ah_surf, C_YELLOW, (ah_r - 12, ah_r), (ah_r + 12, ah_r), 2)
    pygame.draw.line(ah_surf, C_YELLOW, (ah_r, ah_r - 6), (ah_r, ah_r + 6), 2)

    screen.blit(ah_surf, (ah_cx - ah_r, ah_cy - ah_r))
    lbl = small_font.render("HORIZ", True, C_WHITE)
    screen.blit(lbl, (ah_cx - 18, ah_cy + ah_r + 4))

    # ── Controls reminder (bottom left) ───────────────────────────────────────
    hints = [
        "↑/↓  Pitch",
        "→/←  Throttle",
        "R    Reset",
        "ESC  Quit",
    ]
    for i, h in enumerate(hints):
        t = small_font.render(h, True, (150, 160, 180))
        screen.blit(t, (12, SCREEN_H - 90 + i * 18))


def draw_landing_result(screen: pygame.Surface, plane: Plane,
                        font: pygame.font.Font, small_font: pygame.font.Font):
    if plane.landing_result is None:
        return
    result = plane.landing_result
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    screen.blit(overlay, (0, 0))

    score_col = C_GREEN if result["score"] >= 70 else C_YELLOW if result["score"] >= 40 else C_RED
    verdict   = font.render(result["verdict"], True, score_col)
    score_txt = font.render(f"Score: {result['score']} / 100", True, C_WHITE)
    restart   = small_font.render("Press  R  to restart", True, (180, 180, 200))

    cx = SCREEN_W // 2
    screen.blit(verdict,   verdict.get_rect(center=(cx, SCREEN_H // 2 - 40)))
    screen.blit(score_txt, score_txt.get_rect(center=(cx, SCREEN_H // 2 + 10)))
    screen.blit(restart,   restart.get_rect(center=(cx, SCREEN_H // 2 + 60)))


def draw_crash(screen: pygame.Surface, font: pygame.font.Font,
               small_font: pygame.font.Font):
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((80, 0, 0, 160))
    screen.blit(overlay, (0, 0))

    txt     = font.render("CRASHED!", True, C_RED)
    restart = small_font.render("Press  R  to restart", True, C_WHITE)
    cx = SCREEN_W // 2
    screen.blit(txt,     txt.get_rect(center=(cx, SCREEN_H // 2 - 30)))
    screen.blit(restart, restart.get_rect(center=(cx, SCREEN_H // 2 + 30)))


def draw_fuel_warning(screen: pygame.Surface, plane: Plane,
                      small_font: pygame.font.Font, tick: int):
    if plane.fuel_pct < 0.15:
        if (tick // 30) % 2 == 0:
            warn = small_font.render("⚠  LOW FUEL  ⚠", True, C_RED)
            screen.blit(warn, warn.get_rect(center=(SCREEN_W // 2, 30)))


def draw_on_runway_indicator(screen: pygame.Surface, plane: Plane,
                             small_font: pygame.font.Font):
    """Show runway alignment cue when near runway."""
    on_rwy = RUNWAY_X1 <= plane.x <= RUNWAY_X2
    if on_rwy and plane.altitude < 500:
        txt = small_font.render("ON RUNWAY APPROACH", True, C_GREEN)
        screen.blit(txt, txt.get_rect(center=(SCREEN_W // 2, 60)))


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption(TITLE)
    clock  = pygame.time.Clock()

    font       = pygame.font.SysFont("consolas", 28, bold=True)
    small_font = pygame.font.SysFont("consolas", 16)
    big_font   = pygame.font.SysFont("consolas", 48, bold=True)

    # ── Assets ────────────────────────────────────────────────────────────────
    plane_img_base = make_plane_surface(scale=1.0)
    explosion_frames = make_explosion_frames()

    # ── Initial state ─────────────────────────────────────────────────────────
    START_X, START_Y = RUNWAY_X1, GROUND_Y
    plane  = Plane(START_X, START_Y)
    plane.throttle = 0.0
    camera = Camera()
    camera.cam_x = START_X - 200
    camera.cam_y = -200

    explosion_frame  = 0
    explosion_active = False
    tick = 0

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 0.05)   # clamp to avoid physics explosion on lag
        tick += 1

        # ── Events ────────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    plane  = Plane(START_X, START_Y)
                    camera = Camera()
                    camera.cam_x = START_X - 200
                    explosion_active = False
                    explosion_frame  = 0

        # ── Continuous key input ──────────────────────────────────────────────
        if not plane.crashed and not plane.landed:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP]:
                plane.pitch_up(dt)
            if keys[pygame.K_DOWN]:
                plane.pitch_down(dt)
            if keys[pygame.K_RIGHT]:
                plane.increase_throttle(dt)
            if keys[pygame.K_LEFT]:
                plane.decrease_throttle(dt)

        # ── Physics update ────────────────────────────────────────────────────
        plane.update(dt, GROUND_Y)
        camera.update(plane, dt)

        # ── Crash explosion trigger ───────────────────────────────────────────
        if plane.crashed and not explosion_active:
            explosion_active = True
            explosion_frame  = 0

        # ── Draw ──────────────────────────────────────────────────────────────
        draw_sky(screen, plane.altitude)
        draw_stars(screen, plane.altitude)
        draw_clouds(screen, camera, tick)
        draw_ground(screen, camera)
        draw_runway(screen, camera)

        # Plane sprite
        if not plane.crashed:
            angle  = plane.pitch  # rotate sprite by pitch
            rotated = pygame.transform.rotate(plane_img_base, angle)
            px, py  = camera.world_to_screen(plane.x, plane.y)
            rect    = rotated.get_rect(center=(px, py))
            screen.blit(rotated, rect)

        # Explosion
        if explosion_active:
            ex, ey = camera.world_to_screen(plane.x, plane.y)
            if explosion_frame < len(explosion_frames):
                ef = explosion_frames[explosion_frame]
                er = ef.get_rect(center=(ex, ey))
                screen.blit(ef, er)
                if tick % 2 == 0:
                    explosion_frame += 1

        # HUD
        draw_hud(screen, plane, font, small_font)
        draw_fuel_warning(screen, plane, small_font, tick)
        draw_on_runway_indicator(screen, plane, small_font)

        # Overlays
        if plane.crashed:
            draw_crash(screen, big_font, small_font)
        elif plane.landed:
            draw_landing_result(screen, plane, big_font, small_font)

        # Title / speed bar at top-right
        title_txt = small_font.render(f"✈ 2D FLIGHT SIMULATOR", True, (180, 200, 230))
        screen.blit(title_txt, (SCREEN_W - title_txt.get_width() - 12, 12))

        # Stall warning
        if abs(plane.pitch) > 22 and plane.altitude > 10 and plane.speed < 40:
            if (tick // 20) % 2 == 0:
                stall = font.render("STALL!", True, C_RED)
                screen.blit(stall, stall.get_rect(center=(SCREEN_W // 2, 100)))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
