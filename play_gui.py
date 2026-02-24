"""
play_gui.py — RETRO ARCADE interactive pygame window for PM07 (Pattern Master).

Properly maps ARC engine colors to a dark-background retro aesthetic.
ARC color 0 (#FFFFFF) is the game's "empty/background" → rendered as dark CRT void.
All other colors are bright, saturated, CRT-phosphor neon.

All 7 levels use ONLY arrow keys — no Space bar, no mouse clicking on the grid.

Controls:
    WASD / Arrow Keys  = ACTION1-4 (Up / Down / Left / Right)
    Ctrl+Z / Cmd+Z     = ACTION7   (Undo)
    R                  = RESET     (Reset current level)
    Ctrl+R / Cmd+R     = RESTART   (Full game restart from level 1)
    H                  = Toggle hints
    ESC / Q            = Quit

Usage:
    uv run python play_gui.py
    uv run python play_gui.py --seed 42
    uv run python play_gui.py --no-boot
"""

import argparse
import math
import sys
import time
from collections import Counter

import numpy as np
import pygame

import arc_agi
from arcengine import GameAction

# ═══════════════════════════════════════════════════════════════════════════
#  RETRO COLOR MAP
# ═══════════════════════════════════════════════════════════════════════════
# ARC engine: 0=#FFF(white) 1=#CCC 2=#999 3=#666 4=#333 5=#000(black)
#             6=#E53AA3 7=#FF7BCC 8=#F93C31 9=#1E93FF 10=#88D8F1
#             11=#FFDC00 12=#FF851B 13=#921231 14=#4FCC30 15=#A356D6
#
# For our retro dark theme:
#   - Color 0 (game background/empty) → clean light cream, clearly visible
#   - Grays 1-5                       → distinct visible gray tones
#   - Colors 6-15                     → bright, vivid, fully saturated

RETRO: dict[int, tuple[int, int, int]] = {
    0:  (235, 235, 220),    # empty/background → warm cream (clear, bright)
    1:  (190, 195, 205),    # light gray → soft silver
    2:  (145, 148, 160),    # gray → medium visible gray
    3:  (100, 105, 118),    # dark gray → slate (still clearly visible)
    4:  (65, 68, 82),       # charcoal → dark slate (visible against cream)
    5:  (35, 38, 50),       # black → deep navy (visible, not invisible)
    6:  (255, 40, 170),     # magenta → hot neon pink
    7:  (255, 120, 210),    # pink → bubblegum
    8:  (240, 50, 40),      # red → bright arcade red
    9:  (30, 140, 255),     # blue → vivid electric blue
    10: (50, 210, 240),     # cyan → bright sky cyan
    11: (255, 220, 20),     # yellow → bold pac-man yellow
    12: (255, 145, 25),     # orange → bright fire orange
    13: (190, 20, 65),      # crimson → rich cherry red
    14: (30, 210, 60),      # green → bright emerald (cursor)
    15: (165, 85, 235),     # purple → vivid violet (targets)
}

# ═══════════════════════════════════════════════════════════════════════════
#  UI COLORS
# ═══════════════════════════════════════════════════════════════════════════
BG           = (28, 30, 42)
PANEL_BG     = (22, 24, 38)
BORDER_GREEN = (40, 255, 90)
BORDER_DIM   = (20, 130, 50)
TEXT_GREEN    = (50, 255, 100)
TEXT_BRIGHT   = (150, 255, 180)
TEXT_DIM      = (30, 150, 60)
ACCENT_YELLOW = (255, 240, 40)
WARN_RED      = (255, 80, 50)
CYAN          = (40, 230, 255)
MAGENTA       = (255, 50, 220)
KEY_BG        = (22, 42, 30)
KEY_BORDER    = (50, 180, 70)
BTN_BG        = (35, 60, 45)
BTN_BORDER    = (50, 220, 80)
BTN_HOVER     = (50, 80, 60)
BTN_TEXT      = (160, 255, 180)
PLAY_AGAIN_BG = (40, 30, 60)
PLAY_AGAIN_BD = (200, 150, 255)

# ═══════════════════════════════════════════════════════════════════════════
#  LAYOUT CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════
FRAME_PX       = 64       # ARC frames are always 64x64
CELL_SIZE      = 8        # each game cell = 8x8 pixels in the frame
GRID_SCALE     = 9        # screen pixels per frame pixel
SIDEBAR_W      = 290
GRID_MARGIN    = 12       # margin around grid area
FPS            = 30
SCANLINE_ALPHA = 12       # barely-there — just a hint of CRT texture

# ═══════════════════════════════════════════════════════════════════════════
#  LEVEL DATA
# ═══════════════════════════════════════════════════════════════════════════
LEVEL_NAMES = [
    "LVL 1 : COLOR ECHO",
    "LVL 2 : FLOOD WALKER",
    "LVL 3 : ICE SLIDE",
    "LVL 4 : GEM COLLECTOR",
    "LVL 5 : TELEPORT MAZE",
    "LVL 6 : MIRROR WALK",
    "LVL 7 : SOKOBAN",
]

LEVEL_HINTS = [
    "MOVE ONTO GRAY CELLS.\nTHEY COPY THE COLOR YOU LEFT.",
    "WALK OVER CELLS TO TOGGLE.\nMAKE THE WHOLE GRID ONE COLOR.",
    "YOU SLIDE ON ICE UNTIL YOU\nHIT A WALL OR EDGE. COLLECT\nALL GREEN GEMS.",
    "NAVIGATE AROUND WALLS AND\nCOLLECT ALL YELLOW GEMS BY\nWALKING INTO THEM.",
    "NAVIGATE THE MAZE TO REACH\nTHE GREEN EXIT. COLORED CELLS\nTELEPORT YOU TO THEIR MATCH.",
    "TWO GREEN BLOCKS MOVE AT ONCE:\nONE NORMAL, ONE OPPOSITE.\nALIGN BOTH ON THE RED BLOCK.\nUSE WALLS TO MANIPULATE MOVES.",
    "WALK INTO BLOCKS TO PUSH THEM.\nPUSH EACH BLOCK ONTO ITS\nMATCHING TARGET TO WIN.",
]

BOOT_LINES = [
    "INITIALIZING ARC-AGI-3 SUBSYSTEM ...",
    "LOADING ARCENGINE v0.9 ............... OK",
    "MOUNTING ENVIRONMENT pm07-v1 ........ OK",
    "CALIBRATING CRT PHOSPHORS ........... OK",
    "SCANLINE GENERATOR .................. ONLINE",
    "PATTERN MATRIX ...................... ARMED",
    "",
    "   +----------------------------------+",
    "   |  P A T T E R N   M A S T E R    |",
    "   |          - PM07  v1 -            |",
    "   +----------------------------------+",
    "",
    " 7 LEVELS  -  HIDDEN RULES  -  DISCOVER & SOLVE",
    "",
    "PRESS ANY KEY TO START ...",
]


# ═══════════════════════════════════════════════════════════════════════════
#  FONT HELPER
# ═══════════════════════════════════════════════════════════════════════════
def load_font(size: int, bold: bool = False) -> pygame.font.Font:
    for name in ("Courier New", "Courier", "Menlo", "Monaco", "Consolas", "monospace"):
        try:
            f = pygame.font.SysFont(name, size, bold=bold)
            if f:
                return f
        except Exception:
            pass
    return pygame.font.Font(None, size)


# ═══════════════════════════════════════════════════════════════════════════
#  CRT OVERLAY SURFACES (baked once)
# ═══════════════════════════════════════════════════════════════════════════
def make_scanlines(w: int, h: int) -> pygame.Surface:
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(0, h, 3):
        pygame.draw.line(s, (0, 0, 0, SCANLINE_ALPHA), (0, y), (w, y))
    return s


def make_vignette(w: int, h: int) -> pygame.Surface:
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w / 2, h / 2
    for i in range(20):
        t = i / 20
        a = int(t * t * 30)  # very gentle vignette
        sx = int(cx * (1 - t))
        sy = int(cy * (1 - t))
        rw, rh = w - 2 * sx, h - 2 * sy
        if rw > 0 and rh > 0:
            layer = pygame.Surface((rw, rh), pygame.SRCALPHA)
            layer.fill((0, 0, 0, a))
            s.blit(layer, (sx, sy))
    return s


# ═══════════════════════════════════════════════════════════════════════════
#  DRAWING HELPERS
# ═══════════════════════════════════════════════════════════════════════════
def txt(surf, font, text, x, y, color=TEXT_GREEN, max_w=0, shadow=True):
    """Render text with newlines and word-wrap. Returns y after last line."""
    lh = font.get_linesize()
    for raw in text.split("\n"):
        lines = [raw]
        if max_w > 0 and font.size(raw)[0] > max_w:
            lines = []
            buf = ""
            for word in raw.split(" "):
                test = (buf + " " + word).strip()
                if font.size(test)[0] > max_w and buf:
                    lines.append(buf)
                    buf = word
                else:
                    buf = test
            if buf:
                lines.append(buf)
        for line in lines:
            if shadow:
                surf.blit(font.render(line, False, (0, 0, 0)), (x + 1, y + 1))
            surf.blit(font.render(line, False, color), (x, y))
            y += lh
    return y


def draw_button(surf, font, label, x, y, w, h, hover=False):
    """Draw a clickable retro button. Returns the Rect."""
    r = pygame.Rect(x, y, w, h)
    bg = BTN_HOVER if hover else BTN_BG
    pygame.draw.rect(surf, bg, r)
    pygame.draw.rect(surf, BTN_BORDER, r, 2)
    # Top bevel
    pygame.draw.line(surf, (70, 240, 100), (r.left + 2, r.top + 2), (r.right - 3, r.top + 2))
    # Bottom shadow
    pygame.draw.line(surf, (15, 30, 20), (r.left + 2, r.bottom - 2), (r.right - 3, r.bottom - 2))
    ts = font.render(label, False, BTN_TEXT)
    tr = ts.get_rect(center=r.center)
    surf.blit(font.render(label, False, (0, 0, 0)), (tr.x + 1, tr.y + 1))
    surf.blit(ts, tr)
    return r


def keycap(surf, font, label, x, y):
    """Draw a retro keycap badge, return width consumed."""
    tw, th = font.size(label)
    px, py = 5, 2
    r = pygame.Rect(x, y - py, tw + px * 2, th + py * 2)
    pygame.draw.rect(surf, KEY_BG, r)
    pygame.draw.rect(surf, KEY_BORDER, r, 1)
    # top highlight bevel
    pygame.draw.line(surf, (60, 200, 80), (r.left + 1, r.top + 1), (r.right - 2, r.top + 1))
    surf.blit(font.render(label, False, TEXT_BRIGHT), (x + px, y))
    return r.width + 5


def progress_bar(surf, x, y, w, filled, total, t):
    """Segmented progress bar. Returns y after."""
    h = 12
    seg = max(4, (w - 4) // max(total, 1))
    pygame.draw.rect(surf, BG, (x, y, w, h))
    pygame.draw.rect(surf, BORDER_DIM, (x, y, w, h), 1)
    for i in range(total):
        sx = x + 2 + i * seg
        if i < filled:
            pulse = 0.7 + 0.3 * math.sin(t * 3.0 + i * 0.7)
            g = int(220 * pulse)
            pygame.draw.rect(surf, (30, g, 50), (sx, y + 2, seg - 2, h - 4))
        else:
            pygame.draw.rect(surf, (22, 28, 26), (sx, y + 2, seg - 2, h - 4))
    return y + h + 4


def glow_border(surf, rect, color, width=2, layers=4):
    """Neon glow rectangle."""
    for i in range(layers, 0, -1):
        a = max(8, 45 // i)
        exp = rect.inflate(i * 2, i * 2)
        gs = pygame.Surface((exp.w, exp.h), pygame.SRCALPHA)
        pygame.draw.rect(gs, (*color[:3], a), gs.get_rect(), width)
        surf.blit(gs, exp.topleft)
    pygame.draw.rect(surf, color[:3], rect, width)


# ═══════════════════════════════════════════════════════════════════════════
#  FRAME → SURFACE (the core renderer)
# ═══════════════════════════════════════════════════════════════════════════
def render_frame(frame: np.ndarray, scale: int) -> pygame.Surface:
    """
    Convert a 64x64 ARC int8 frame into a properly colored pygame Surface.
    Uses nearest-neighbor scaling for crisp pixel art look.
    """
    h, w = frame.shape
    # Build 64x64 RGB image via numpy
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    for val, col in RETRO.items():
        mask = (frame == val)
        rgb[mask] = col

    # numpy array → pygame surface (transpose because pygame expects [x][y])
    small = pygame.surfarray.make_surface(rgb.transpose(1, 0, 2))

    # Scale up with nearest-neighbor (no blurring!)
    big = pygame.transform.scale(small, (w * scale, h * scale))

    # Add visible grid lines between game cells for structure
    cell_px = CELL_SIZE * scale
    if scale >= 3:
        overlay = pygame.Surface((w * scale, h * scale), pygame.SRCALPHA)
        line_color = (0, 0, 0, 30)  # dark lines on light background
        for gx in range(cell_px, w * scale, cell_px):
            pygame.draw.line(overlay, line_color, (gx, 0), (gx, h * scale - 1))
        for gy in range(cell_px, h * scale, cell_px):
            pygame.draw.line(overlay, line_color, (0, gy), (w * scale - 1, gy))
        big.blit(overlay, (0, 0))

    return big


# ═══════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════
def draw_sidebar(surf, fonts, rect, state, lvl_done, actions, avail, hints_on, t, seed, mouse_pos=(0, 0)):
    """Draw sidebar HUD. Returns dict of clickable button rects."""
    buttons = {}
    ft = fonts["title"]
    fs = fonts["sm"]
    fx = fonts["xs"]

    # Background
    pygame.draw.rect(surf, PANEL_BG, rect)
    # Double green left border
    bx = rect.left
    pygame.draw.line(surf, BORDER_DIM, (bx, 0), (bx, rect.bottom), 2)
    pygame.draw.line(surf, BORDER_GREEN, (bx + 3, 0), (bx + 3, rect.bottom), 1)

    x0 = rect.left + 16
    y = rect.top + 10
    mw = rect.width - 32

    # ── Scrolling marquee ──
    mr = pygame.Rect(x0, y, mw, ft.get_linesize() + 4)
    pygame.draw.rect(surf, BG, mr)
    pygame.draw.rect(surf, BORDER_DIM, mr, 1)
    marquee = "   *** PATTERN MASTER *** PM07 *** ARC-AGI-3 *** 7 LEVELS *** HIDDEN RULES ***   "
    mtw = ft.size(marquee)[0]
    scroll = int((t * 60) % (mtw + mw))
    clip_save = surf.get_clip()
    surf.set_clip(mr.inflate(-4, -2))
    surf.blit(ft.render(marquee, False, ACCENT_YELLOW), (mr.right - scroll, y + 2))
    surf.set_clip(clip_save)
    y += ft.get_linesize() + 12

    # ── Animated separator ──
    for i in range(mw):
        p = 0.5 + 0.5 * math.sin(t * 3.5 + i * 0.07)
        g = int(50 + 120 * p)
        surf.set_at((x0 + i, y), (12, g, 28))
    y += 8

    # ── State ──
    if state == "WON":
        sc, sd = ACCENT_YELLOW, "** VICTORY! **"
    elif "LOST" in state:
        sc, sd = WARN_RED, "XX GAME OVER XX"
    elif state == "NOT_FINISHED":
        blink = math.sin(t * 4.5) > 0
        sc = TEXT_GREEN
        sd = "> PLAYING" if blink else "  PLAYING"
    else:
        sc, sd = TEXT_DIM, state
    y = txt(surf, fs, sd, x0, y, sc, mw)
    y += 4

    # ── Level name ──
    lidx = min(lvl_done, len(LEVEL_NAMES) - 1)
    y = txt(surf, fs, LEVEL_NAMES[lidx], x0, y, CYAN, mw)
    y += 2

    # ── Progress bar ──
    y = progress_bar(surf, x0, y, mw, lvl_done, 7, t)
    y += 2

    # ── Action counter ──
    y = txt(surf, fx, f"ACTIONS: {actions:05d}", x0, y, TEXT_DIM, mw, shadow=False)
    y += 8

    # ── Separator ──
    pygame.draw.line(surf, BORDER_DIM, (x0, y), (x0 + mw, y))
    y += 8

    # ── Controls (2 columns) ──
    y = txt(surf, fs, "-- CONTROLS --", x0, y, ACCENT_YELLOW, mw)
    y += 5

    controls = [
        ("W/^",  "UP"),      ("S/v",  "DOWN"),
        ("A/<",  "LEFT"),    ("D/>",  "RIGHT"),
        ("C-Z",  "UNDO"),   (" R ",  "LVL RST"),
        ("C-R",  "RESTART"),(" H ",  "HINTS"),
    ]
    col2 = x0 + mw // 2
    rh = fx.get_linesize() + 5
    for i in range(0, len(controls), 2):
        k1, d1 = controls[i]
        w1 = keycap(surf, fx, k1, x0, y)
        txt(surf, fx, d1, x0 + w1, y, TEXT_DIM, shadow=False)
        if i + 1 < len(controls):
            k2, d2 = controls[i + 1]
            w2 = keycap(surf, fx, k2, col2, y)
            txt(surf, fx, d2, col2 + w2, y, TEXT_DIM, shadow=False)
        y += rh
    y += 6

    # ── Separator ──
    pygame.draw.line(surf, BORDER_DIM, (x0, y), (x0 + mw, y))
    y += 8

    # ── Available actions ──
    y = txt(surf, fs, "-- ACTIVE --", x0, y, ACCENT_YELLOW, mw)
    y += 3
    glyphs = {
        1: "^ UP", 2: "v DOWN", 3: "< LEFT", 4: "> RIGHT",
        7: "< UNDO", 0: "@ RESET",
    }
    for a in sorted(avail):
        g = glyphs.get(a, f"? ACT{a}")
        pulse = 0.6 + 0.4 * math.sin(t * 3.0 + a * 0.9)
        gv = int(200 * pulse)
        y = txt(surf, fx, f"  {g}", x0, y, (25, gv, 50), mw, shadow=False)
    y += 8

    # ── Hints ──
    if hints_on:
        pygame.draw.line(surf, WARN_RED, (x0, y), (x0 + mw, y))
        y += 7
        blink = math.sin(t * 5) > 0
        y = txt(surf, fs, "! HINT !" if blink else "        ", x0, y, WARN_RED, mw)
        y += 3
        hint = LEVEL_HINTS[lidx] if lidx < len(LEVEL_HINTS) else "NO DATA."
        y = txt(surf, fx, hint, x0, y, TEXT_DIM, mw)

    # ── Restart Game button ──
    y += 6
    btn_w = mw
    btn_h = 26
    hover = False
    btn_rect_abs = pygame.Rect(x0, y, btn_w, btn_h)
    if btn_rect_abs.collidepoint(mouse_pos):
        hover = True
    buttons["restart"] = draw_button(surf, fs, "[ RESTART GAME ]", x0, y, btn_w, btn_h, hover)
    y += btn_h + 8

    # ── Bottom status ──
    by = rect.bottom - 20
    txt(surf, fx, f"SEED:{seed:04d}  FPS:{FPS}  ESC=QUIT", x0, by, BORDER_DIM, mw, shadow=False)

    return buttons


# ═══════════════════════════════════════════════════════════════════════════
#  BOOT SEQUENCE
# ═══════════════════════════════════════════════════════════════════════════
def boot_screen(screen, fonts, clock):
    """Green text CRT boot. Returns False if user quit."""
    font = fonts["sm"]
    w, h = screen.get_size()
    scanlines = make_scanlines(w, h)
    lh = font.get_linesize()
    done_lines = []

    for li, line_text in enumerate(BOOT_LINES):
        # Type each character
        for ci in range(len(line_text) + 1):
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return False
                if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    return True

            screen.fill(BG)
            y = 30
            for prev in done_lines:
                c = TEXT_GREEN
                if "+--" in prev or "|" in prev:
                    c = ACCENT_YELLOW
                elif "PRESS" in prev:
                    c = MAGENTA
                elif "7 LEVELS" in prev:
                    c = CYAN
                screen.blit(font.render(prev, False, c), (20, y))
                y += lh

            # Current line partial + cursor
            partial = line_text[:ci]
            cursor = "|" if int(time.time() * 8) % 2 else " "
            c = TEXT_GREEN
            if "+--" in line_text or "|" in line_text:
                c = ACCENT_YELLOW
            screen.blit(font.render(partial + cursor, False, c), (20, y))

            screen.blit(scanlines, (0, 0))
            pygame.display.flip()
            clock.tick(180)

        done_lines.append(line_text)

    # Wait for keypress with blinking prompt
    blink = 0
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False
            if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return True

        screen.fill(BG)
        y = 30
        blink += 1
        for i, ln in enumerate(done_lines):
            c = TEXT_GREEN
            if "+--" in ln or "|" in ln:
                c = ACCENT_YELLOW
            elif "PRESS" in ln:
                c = MAGENTA if (blink // 15) % 2 == 0 else BG
            elif "7 LEVELS" in ln:
                c = CYAN
            screen.blit(font.render(ln, False, c), (20, y))
            y += lh

        screen.blit(scanlines, (0, 0))
        pygame.display.flip()
        clock.tick(30)


# ═══════════════════════════════════════════════════════════════════════════
#  LEVEL TRANSITION
# ═══════════════════════════════════════════════════════════════════════════
def level_wipe(screen, fonts, clock, level_idx):
    """Quick level transition. Returns False if quit."""
    fl = fonts["lg"]
    fs = fonts["sm"]
    w, h = screen.get_size()
    name = LEVEL_NAMES[min(level_idx, len(LEVEL_NAMES) - 1)]
    scanlines = make_scanlines(w, h)
    total = 45

    for f in range(total):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False
            if ev.type == pygame.KEYDOWN:
                return True

        p = f / total
        screen.fill(BG)

        # Horizontal wipe bars
        nbars = 10
        for b in range(nbars):
            bp = max(0, min(1, (p - b * 0.012) * 2.0))
            bw = int(w * bp)
            bh = h // nbars
            by = b * bh
            bx = 0 if b % 2 == 0 else w - bw
            shade = int(16 + 10 * math.sin(f * 0.3 + b))
            pygame.draw.rect(screen, (shade, shade + 6, shade + 2), (bx, by, bw, bh))

        # Level name
        if p > 0.25:
            alpha = min(255, int((p - 0.25) * 3.5 * 255))
            ts = fl.render(name, False, ACCENT_YELLOW)
            ts.set_alpha(alpha)
            tr = ts.get_rect(center=(w // 2, h // 2 - 14))
            # Glow behind text
            glow = pygame.Surface((tr.w + 30, tr.h + 16), pygame.SRCALPHA)
            glow.fill((*ACCENT_YELLOW, min(30, alpha // 7)))
            screen.blit(glow, (tr.x - 15, tr.y - 8))
            screen.blit(ts, tr)

        if p > 0.5:
            alpha2 = min(255, int((p - 0.5) * 4 * 255))
            sub = fs.render("-- DISCOVER THE RULE --", False, TEXT_GREEN)
            sub.set_alpha(alpha2)
            sr = sub.get_rect(center=(w // 2, h // 2 + 22))
            screen.blit(sub, sr)

        screen.blit(scanlines, (0, 0))
        pygame.display.flip()
        clock.tick(60)

    return True


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="PM07 Retro Arcade Player")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--scale", type=int, default=GRID_SCALE,
                        help=f"Pixels per frame-pixel (default {GRID_SCALE})")
    parser.add_argument("--no-boot", action="store_true")
    parser.add_argument("--no-scanlines", action="store_true")
    args = parser.parse_args()

    # ── ARC environment ──
    arc = arc_agi.Arcade(environments_dir="./environment_files")
    env = arc.make("pm07-v1", seed=args.seed)
    if env is None:
        print("ERROR: Could not create environment.")
        sys.exit(1)
    frame_data = env.reset()
    if frame_data is None:
        print("ERROR: env.reset() returned None")
        sys.exit(1)

    # ── Pygame init ──
    pygame.init()
    scale = args.scale
    grid_px = FRAME_PX * scale
    margin = GRID_MARGIN
    win_w = grid_px + margin * 2 + SIDEBAR_W
    win_h = grid_px + margin * 2

    screen = pygame.display.set_mode((win_w, win_h))
    pygame.display.set_caption("PM07 - PATTERN MASTER - ARC-AGI-3")
    clock = pygame.time.Clock()

    fonts = {
        "title": load_font(13, bold=True),
        "lg":    load_font(22, bold=True),
        "sm":    load_font(15),
        "xs":    load_font(12),
    }

    # Bake overlays
    scanlines_surf = make_scanlines(win_w, win_h)
    vignette_surf = make_vignette(win_w, win_h)
    use_scanlines = not args.no_scanlines

    # ── Boot ──
    if not args.no_boot:
        if not boot_screen(screen, fonts, clock):
            pygame.quit()
            return
        if not level_wipe(screen, fonts, clock, 0):
            pygame.quit()
            return

    # ── Game state ──
    total_actions = 0
    state_str = "NOT_FINISHED"
    levels_completed = 0
    prev_levels = 0
    available_actions = list(range(7))
    show_hints = False
    running = True
    t0 = time.time()
    hover_fx, hover_fy = -1, -1
    sidebar_buttons = {}
    mouse_pos = (0, 0)

    def sync(fd):
        nonlocal state_str, levels_completed, available_actions
        if fd is None:
            return
        state_str = fd.state.value if hasattr(fd.state, "value") else str(fd.state)
        levels_completed = fd.levels_completed
        if hasattr(fd, "available_actions") and fd.available_actions is not None and len(fd.available_actions) > 0:
            available_actions = list(fd.available_actions)

    sync(frame_data)

    def act(action, data=None):
        nonlocal frame_data, total_actions
        frame_data = env.step(action, data=data)
        total_actions += 1
        sync(frame_data)

    def full_restart():
        """Full game restart — recreate environment, back to level 1."""
        nonlocal env, frame_data, total_actions, levels_completed, prev_levels, state_str
        env = arc.make("pm07-v1", seed=args.seed)
        frame_data = env.reset()
        total_actions = 0
        levels_completed = 0
        prev_levels = 0
        state_str = "NOT_FINISHED"
        sync(frame_data)
        level_wipe(screen, fonts, clock, 0)

    # Grid position on screen
    gx0 = margin
    gy0 = margin

    # ═══════════════════════════════════════════════════════════════════
    #  MAIN LOOP
    # ═══════════════════════════════════════════════════════════════════
    while running:
        t = time.time() - t0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            if event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                    break
                if event.key == pygame.K_h:
                    show_hints = not show_hints
                    continue
                if event.key == pygame.K_z and (mods & (pygame.KMOD_CTRL | pygame.KMOD_META)):
                    act(GameAction.ACTION7)
                    continue
                if event.key == pygame.K_r and (mods & (pygame.KMOD_CTRL | pygame.KMOD_META)):
                    full_restart()
                    continue
                if event.key == pygame.K_r:
                    frame_data = env.reset()
                    total_actions = 0
                    sync(frame_data)
                    continue
                if event.key in (pygame.K_w, pygame.K_UP):
                    act(GameAction.ACTION1)
                    continue
                if event.key in (pygame.K_s, pygame.K_DOWN):
                    act(GameAction.ACTION2)
                    continue
                if event.key in (pygame.K_a, pygame.K_LEFT):
                    act(GameAction.ACTION3)
                    continue
                if event.key in (pygame.K_d, pygame.K_RIGHT):
                    act(GameAction.ACTION4)
                    continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                # Check sidebar buttons only (no grid clicking)
                for btn_name, btn_rect in sidebar_buttons.items():
                    if btn_rect.collidepoint(mx, my):
                        if btn_name == "restart":
                            full_restart()
                            break
                        elif btn_name == "play_again":
                            full_restart()
                            break

            if event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                mouse_pos = (mx, my)
                hover_fx = (mx - gx0) // scale
                hover_fy = (my - gy0) // scale

        # ── Level transition ──
        if levels_completed > prev_levels and levels_completed < 7:
            prev_levels = levels_completed
            if not level_wipe(screen, fonts, clock, levels_completed):
                running = False
                continue
        prev_levels = levels_completed

        # ═══════════════════════════════════════════════════════════════
        #  DRAW
        # ═══════════════════════════════════════════════════════════════
        screen.fill(BG)

        # ── Game grid ──
        if frame_data is not None and frame_data.frame is not None and len(frame_data.frame) > 0:
            grid_surf = render_frame(frame_data.frame[0], scale)
        else:
            grid_surf = pygame.Surface((grid_px, grid_px))
            grid_surf.fill(BG)
        screen.blit(grid_surf, (gx0, gy0))

        # ── Hover highlight + crosshair ──
        if 0 <= hover_fx < FRAME_PX and 0 <= hover_fy < FRAME_PX:
            hx = gx0 + hover_fx * scale
            hy = gy0 + hover_fy * scale

            # Highlight the cell under cursor
            cell_screen = CELL_SIZE * scale
            # Snap to game-cell boundary
            cell_col = (hover_fx // CELL_SIZE) * CELL_SIZE
            cell_row = (hover_fy // CELL_SIZE) * CELL_SIZE
            cx = gx0 + cell_col * scale
            cy = gy0 + cell_row * scale
            hs = pygame.Surface((cell_screen, cell_screen), pygame.SRCALPHA)
            hs.fill((255, 255, 255, 25))
            screen.blit(hs, (cx, cy))

            # Crosshair
            ch = pygame.Surface((grid_px, 1), pygame.SRCALPHA)
            ch.fill((255, 255, 255, 12))
            cv = pygame.Surface((1, grid_px), pygame.SRCALPHA)
            cv.fill((255, 255, 255, 12))
            screen.blit(ch, (gx0, cy + cell_screen // 2))
            screen.blit(cv, (cx + cell_screen // 2, gy0))

            # Coordinate readout (show game-cell coords, not frame-pixel coords)
            gc = hover_fx // CELL_SIZE
            gr = hover_fy // CELL_SIZE
            coord = fonts["xs"].render(f"({gc},{gr})", False, TEXT_DIM)
            screen.blit(coord, (cx + cell_screen + 4, cy))

        # ── Neon border around grid ──
        pulse = 0.7 + 0.3 * math.sin(t * 2.0)
        bc = tuple(int(c * pulse) for c in BORDER_GREEN)
        border_rect = pygame.Rect(gx0 - 4, gy0 - 4, grid_px + 8, grid_px + 8)
        glow_border(screen, border_rect, bc, 2, 4)

        # Corner accents
        cs = 8
        for cx, cy in [(border_rect.left, border_rect.top),
                        (border_rect.right - cs, border_rect.top),
                        (border_rect.left, border_rect.bottom - cs),
                        (border_rect.right - cs, border_rect.bottom - cs)]:
            pygame.draw.rect(screen, ACCENT_YELLOW, (cx, cy, cs, cs), 2)

        # ── Sidebar ──
        sb_rect = pygame.Rect(grid_px + margin * 2, 0, SIDEBAR_W, win_h)
        sidebar_buttons = draw_sidebar(screen, fonts, sb_rect, state_str, levels_completed,
                     total_actions, available_actions, show_hints, t, args.seed, mouse_pos)

        # ── CRT effects (very subtle) ──
        if use_scanlines:
            screen.blit(scanlines_surf, (0, 0))
        screen.blit(vignette_surf, (0, 0))

        # ── Win celebration ──
        if state_str == "WON":
            hue = (t * 120) % 360
            r = int(128 + 127 * math.sin(math.radians(hue)))
            g = int(128 + 127 * math.sin(math.radians(hue + 120)))
            b = int(128 + 127 * math.sin(math.radians(hue + 240)))
            wr = screen.get_rect().inflate(-8, -8)
            pygame.draw.rect(screen, (r, g, b), wr, 4)

            # Victory text
            wt = fonts["lg"].render("*** ALL LEVELS COMPLETE ***", False, (r, g, b))
            wtr = wt.get_rect(center=(gx0 + grid_px // 2, win_h // 2 - 40))
            screen.blit(fonts["lg"].render("*** ALL LEVELS COMPLETE ***", False, (0, 0, 0)),
                        (wtr.x + 2, wtr.y + 2))
            screen.blit(wt, wtr)

            # Dark overlay behind button area
            overlay = pygame.Surface((grid_px, 120), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            screen.blit(overlay, (gx0, win_h // 2 - 10))

            # PLAY AGAIN button centered on grid
            pa_w, pa_h = 260, 44
            pa_x = gx0 + grid_px // 2 - pa_w // 2
            pa_y = win_h // 2 + 10
            pa_hover = pygame.Rect(pa_x, pa_y, pa_w, pa_h).collidepoint(mouse_pos)
            pa_rect = draw_button(screen, fonts["lg"], "[ PLAY AGAIN ]", pa_x, pa_y, pa_w, pa_h, pa_hover)
            sidebar_buttons["play_again"] = pa_rect

            # Sub-text
            sub = fonts["sm"].render("or press Ctrl+R to restart", False, TEXT_DIM)
            sr = sub.get_rect(center=(gx0 + grid_px // 2, pa_y + pa_h + 20))
            screen.blit(sub, sr)

        pygame.display.flip()
        clock.tick(FPS)

    # ── Cleanup ──
    pygame.quit()
    print()
    print("+----------------------------------+")
    print("|        FINAL SCORECARD           |")
    print("+----------------------------------+")
    try:
        print(arc.get_scorecard())
    except Exception as e:
        print(f"  (Could not retrieve scorecard: {e})")
    print()


if __name__ == "__main__":
    main()
