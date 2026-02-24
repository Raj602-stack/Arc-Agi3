"""cd01 - An ARC-AGI-3 puzzle game."""

import random

from arcengine import ARCBaseGame, Camera, GameAction, Level, Sprite
from arcengine.enums import BlockingMode
from arcengine.interfaces import RenderableUserDisplay

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EMPTY = 0          # palette: white (empty cell)
BRIDGE_BG = 4      # palette: dark gray (bridge marker)
CURSOR_CLR = 3     # palette: gray (cursor border when idle)
BLACK = 5          # palette: black (letterbox / endpoint dot)

PATH_PALETTE = [
    8,   # 1  -> Red
    9,   # 2  -> Blue
    11,  # 3  -> Yellow
    14,  # 4  -> Green
    12,  # 5  -> Orange
    15,  # 6  -> Purple
    6,   # 7  -> Magenta
    10,  # 8  -> Light Blue
    13,  # 9  -> Maroon
    7,   # 10 -> Light Magenta
    1,   # 11 -> Off-white
    2,   # 12 -> Light Gray
]

DIRS = [(0, -1), (0, 1), (-1, 0), (1, 0)]

LEVEL_CONFIGS = [
    {"grid": (8, 8),   "colors": 5,  "bridges": 0, "max_steps": 150},
    {"grid": (16, 16), "colors": 6,  "bridges": 0, "max_steps": 400},
    {"grid": (8, 8),   "colors": 7,  "bridges": 1, "max_steps": 300},
    {"grid": (16, 16), "colors": 8,  "bridges": 2, "max_steps": 600},
    {"grid": (32, 32), "colors": 9,  "bridges": 2, "max_steps": 1600},
    {"grid": (32, 32), "colors": 10, "bridges": 4, "max_steps": 1600},
]

# ---------------------------------------------------------------------------
# Puzzles
#
# Levels 1 & 2 are the original puzzles (unchanged).
# Levels 3-6 use a clean block/band layout:
#   each color fills a rectangular region; paths sweep along rows or columns.
# ---------------------------------------------------------------------------

PUZZLES = {
    # ── Level 1 (8×8, 5 colors, 0 bridges) — ORIGINAL ───────────────────────
    0: {
        "endpoints": {
            1: ((6, 6), (0, 4)),
            2: ((0, 3), (2, 0)),
            3: ((3, 0), (5, 3)),
            4: ((5, 4), (3, 4)),
            5: ((3, 5), (2, 1)),
        },
        "bridges": set(),
    },

    # ── Level 2 (16×16, 6 colors, 0 bridges) — ORIGINAL ─────────────────────
    1: {
        "endpoints": {
            1: ((2, 13),  (15, 14)),
            2: ((14, 14), (14, 12)),
            3: ((14, 11), (13, 11)),
            4: ((13, 12), (8, 12)),
            5: ((9, 12),  (10, 3)),
            6: ((9, 3),   (4, 8)),
        },
        "bridges": set(),
    },

    # ── Level 3 (8×8, 7 colors, 1 bridge at (3,3)) ───────────────────────────
    # Solution: 2-col × 4-row blocks.
    #   cols 0-1, rows 0-3 → color 1    cols 0-1, rows 4-7 → color 2
    #   cols 2-3, rows 0-2 → color 3    cols 2-3, rows 3-7 → color 4
    #   cols 4-5, rows 0-3 → color 5    cols 4-5, rows 4-7 → color 6
    #   cols 6-7, all rows → color 7
    # Bridge at (3,3): boundary cell where colors 3 and 4 border each other.
    2: {
        "endpoints": {
            1: ((0, 0), (1, 3)),
            2: ((0, 4), (1, 7)),
            3: ((2, 0), (3, 2)),
            4: ((2, 3), (3, 7)),
            5: ((4, 0), (5, 3)),
            6: ((4, 4), (5, 7)),
            7: ((6, 0), (7, 7)),
        },
        "bridges": {(3, 3)},
    },

    # ── Level 4 (16×16, 8 colors, 2 bridges) ─────────────────────────────────
    # Solution: 4 horizontal bands × 2 halves = 8 blocks of 8×4 each.
    #   rows 0-3:   color 1 (cols 0-7)  + color 2 (cols 8-15)
    #   rows 4-7:   color 3 (cols 0-7)  + color 4 (cols 8-15)
    #   rows 8-11:  color 5 (cols 0-7)  + color 6 (cols 8-15)
    #   rows 12-15: color 7 (cols 0-7)  + color 8 (cols 8-15)
    # Bridges at (7,4) and (8,11): column-boundary cells in mid-bands.
    3: {
        "endpoints": {
            1: ((0, 0),  (7, 3)),
            2: ((8, 0),  (15, 3)),
            3: ((0, 4),  (7, 7)),
            4: ((8, 4),  (15, 7)),
            5: ((0, 8),  (7, 11)),
            6: ((8, 8),  (15, 11)),
            7: ((0, 12), (7, 15)),
            8: ((8, 12), (15, 15)),
        },
        "bridges": {(7, 4), (8, 11)},
    },

    # ── Level 5 (32×32, 9 colors, 2 bridges) ─────────────────────────────────
    # Solution: 9 horizontal bands.
    #   rows 0-3   → color 1    rows 4-6   → color 2    rows 7-10  → color 3
    #   rows 11-13 → color 4    rows 14-17 → color 5    rows 18-20 → color 6
    #   rows 21-23 → color 7    rows 24-27 → color 8    rows 28-31 → color 9
    # Bridges at (15,6) and (16,21).
    4: {
        "endpoints": {
            1: ((0, 0),  (31, 3)),
            2: ((0, 4),  (31, 6)),
            3: ((0, 7),  (31, 10)),
            4: ((0, 11), (31, 13)),
            5: ((0, 14), (31, 17)),
            6: ((0, 18), (31, 20)),
            7: ((0, 21), (31, 23)),
            8: ((0, 24), (31, 27)),
            9: ((0, 28), (31, 31)),
        },
        "bridges": {(15, 6), (16, 21)},
    },

    # ── Level 6 (32×32, 10 colors, 4 bridges) ────────────────────────────────
    # Solution: 10 horizontal bands of 3 rows each (color 10 gets 5 rows).
    #   rows 0-2   → color 1    rows 3-5   → color 2    rows 6-8   → color 3
    #   rows 9-11  → color 4    rows 12-14 → color 5    rows 15-17 → color 6
    #   rows 18-20 → color 7    rows 21-23 → color 8    rows 24-26 → color 9
    #   rows 27-31 → color 10
    # Bridges at (10,3), (21,3), (10,20), (21,20).
    5: {
        "endpoints": {
            1:  ((0, 0),  (31, 2)),
            2:  ((0, 3),  (31, 5)),
            3:  ((0, 6),  (31, 8)),
            4:  ((0, 9),  (31, 11)),
            5:  ((0, 12), (31, 14)),
            6:  ((0, 15), (31, 17)),
            7:  ((0, 18), (31, 20)),
            8:  ((0, 21), (31, 23)),
            9:  ((0, 24), (31, 26)),
            10: ((0, 27), (31, 31)),
        },
        "bridges": {(10, 3), (21, 3), (10, 20), (21, 20)},
    },
}


# ---------------------------------------------------------------------------
# Display overlay
# ---------------------------------------------------------------------------


class GameOverlay(RenderableUserDisplay):
    """Draws cursor, endpoint dots, bridge marks, and progress bar."""

    def __init__(self):
        self.cursor_x = 0
        self.cursor_y = 0
        self.grid_w = 8
        self.grid_h = 8
        self.endpoints = {}
        self.selected_color = 0
        self.bridges = set()
        self.drawn_paths = {}
        self.step_count = 0
        self.max_steps = 300

    def _scale_info(self):
        s = min(64 // self.grid_w, 64 // self.grid_h)
        ox = (64 - self.grid_w * s) // 2
        oy = (64 - self.grid_h * s) // 2
        return s, ox, oy

    def _set_px(self, frame, x, y, color):
        if 0 <= x < 64 and 0 <= y < 64:
            frame[y, x] = color

    def render_interface(self, frame):
        s, ox, oy = self._scale_info()
        self._draw_endpoint_dots(frame, s, ox, oy)
        self._draw_bridge_marks(frame, s, ox, oy)
        self._draw_cursor(frame, s, ox, oy)
        self._draw_progress_bar(frame)
        return frame

    def _draw_progress_bar(self, frame):
        if self.max_steps <= 0:
            return
        fraction = max(0.0, 1.0 - self.step_count / self.max_steps)
        filled = int(round(fraction * 64))
        for col in range(64):
            self._set_px(frame, col, 63, 14 if col < filled else 4)

    def _draw_endpoint_dots(self, frame, s, ox, oy):
        for color_id, (ep1, ep2) in self.endpoints.items():
            for ex, ey in (ep1, ep2):
                sx = ox + ex * s
                sy = oy + ey * s
                self._set_px(frame, sx + s // 2, sy + s // 2, BLACK)

    def _draw_bridge_marks(self, frame, s, ox, oy):
        if s < 4:
            for bx, by in self.bridges:
                sx = ox + bx * s
                sy = oy + by * s
                self._set_px(frame, sx + s // 2, sy + s // 2, BRIDGE_BG)
            return
        for bx, by in self.bridges:
            sx = ox + bx * s
            sy = oy + by * s
            mark = 2 if s < 8 else 3
            for i in range(mark):
                self._set_px(frame, sx + 1 + i, sy + 1, BRIDGE_BG)
                self._set_px(frame, sx + 1, sy + 1 + i, BRIDGE_BG)
                self._set_px(frame, sx + s - 2 - i, sy + 1, BRIDGE_BG)
                self._set_px(frame, sx + s - 2, sy + 1 + i, BRIDGE_BG)
                self._set_px(frame, sx + 1 + i, sy + s - 2, BRIDGE_BG)
                self._set_px(frame, sx + 1, sy + s - 2 - i, BRIDGE_BG)
                self._set_px(frame, sx + s - 2 - i, sy + s - 2, BRIDGE_BG)
                self._set_px(frame, sx + s - 2, sy + s - 2 - i, BRIDGE_BG)

    def _draw_cursor(self, frame, s, ox, oy):
        sx = ox + self.cursor_x * s
        sy = oy + self.cursor_y * s
        clr = (
            PATH_PALETTE[self.selected_color - 1]
            if self.selected_color > 0
            else CURSOR_CLR
        )
        for i in range(s):
            self._set_px(frame, sx + i, sy, clr)
            self._set_px(frame, sx + i, sy + s - 1, clr)
            self._set_px(frame, sx, sy + i, clr)
            self._set_px(frame, sx + s - 1, sy + i, clr)


# ---------------------------------------------------------------------------
# Main game class
# ---------------------------------------------------------------------------


class Cd01(ARCBaseGame):
    """cd01 puzzle game — Connect All Paths."""

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)
        self.overlay = GameOverlay()

        self.grid_w = 8
        self.grid_h = 8
        self.grid = []
        self.endpoints = {}
        self.bridges = set()
        self.cursor_x = 0
        self.cursor_y = 0
        self.selected_color = 0
        self.drawn_paths = {}
        self.board_sprite = None
        self.step_count = 0
        self.max_steps = 150
        self._game_over = False
        self._full_reset_requested = False

        levels = [
            Level(sprites=[], grid_size=cfg["grid"], name=f"Level {i + 1}")
            for i, cfg in enumerate(LEVEL_CONFIGS)
        ]

        camera = Camera(
            background=EMPTY,
            letter_box=BLACK,
            width=LEVEL_CONFIGS[0]["grid"][0],
            height=LEVEL_CONFIGS[0]["grid"][1],
            interfaces=[self.overlay],
        )

        super().__init__(
            game_id="cd01",
            levels=levels,
            camera=camera,
            available_actions=[1, 2, 3, 4, 5, 7],
            seed=seed,
        )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def handle_reset(self):
        if self._game_over or self._full_reset_requested:
            self._full_reset_requested = False
            self.full_reset()
        else:
            self.level_reset()

    # ------------------------------------------------------------------
    # Level lifecycle
    # ------------------------------------------------------------------

    def on_set_level(self, level):
        cfg = LEVEL_CONFIGS[self.level_index]
        gw, gh = cfg["grid"]
        self.grid_w, self.grid_h = gw, gh

        pdata = PUZZLES[self.level_index]
        self.endpoints = pdata["endpoints"]
        self.bridges = pdata["bridges"]

        self.grid = [[0] * gw for _ in range(gh)]

        for cid, (ep1, ep2) in self.endpoints.items():
            self.grid[ep1[1]][ep1[0]] = cid
            self.grid[ep2[1]][ep2[0]] = cid

        self.selected_color = 0
        self.drawn_paths = {cid: [] for cid in self.endpoints}

        first_ep = self.endpoints[1][0]
        self.cursor_x, self.cursor_y = first_ep

        self.max_steps = cfg.get("max_steps", 300)
        self.step_count = 0
        self._game_over = False

        self.board_sprite = self._make_board_sprite()
        level.add_sprite(self.board_sprite)
        self._sync_overlay()

    # ------------------------------------------------------------------
    # Core game loop
    # ------------------------------------------------------------------

    def step(self):
        self.step_count += 1
        aid = self.action.id

        if aid in (GameAction.ACTION1, GameAction.ACTION2,
                   GameAction.ACTION3, GameAction.ACTION4):
            dx, dy = {
                GameAction.ACTION1: (0, -1),
                GameAction.ACTION2: (0, 1),
                GameAction.ACTION3: (-1, 0),
                GameAction.ACTION4: (1, 0),
            }[aid]
            if self.selected_color > 0:
                self._extend_path(dx, dy)
            else:
                self._move_cursor(dx, dy)
        elif aid == GameAction.ACTION5:
            self._handle_select()
        elif aid == GameAction.ACTION7:
            self._handle_undo()

        self._refresh_board()
        self._sync_overlay()

        if self._check_win():
            self.next_level()
        elif self.step_count >= self.max_steps:
            self._game_over = True
            self.lose()

        self.complete_action()

    # ------------------------------------------------------------------
    # Input handlers
    # ------------------------------------------------------------------

    def _move_cursor(self, dx, dy):
        nx = self.cursor_x + dx
        ny = self.cursor_y + dy
        if 0 <= nx < self.grid_w and 0 <= ny < self.grid_h:
            self.cursor_x, self.cursor_y = nx, ny

    def _handle_select(self):
        pos = (self.cursor_x, self.cursor_y)
        if self.selected_color > 0:
            self.selected_color = 0
            return
        for cid, (ep1, ep2) in self.endpoints.items():
            if pos in (ep1, ep2):
                self._clear_drawn_path(cid)
                self.selected_color = cid
                self.drawn_paths[cid] = [pos]
                return

    def _handle_undo(self):
        if self.selected_color <= 0:
            return
        path = self.drawn_paths.get(self.selected_color, [])
        if len(path) <= 1:
            return
        self._undo_last_cell(self.selected_color)
        path = self.drawn_paths.get(self.selected_color, [])
        if path:
            self.cursor_x, self.cursor_y = path[-1]

    # ------------------------------------------------------------------
    # Path drawing
    # ------------------------------------------------------------------

    def _extend_path(self, dx, dy):
        nx = self.cursor_x + dx
        ny = self.cursor_y + dy
        if not (0 <= nx < self.grid_w and 0 <= ny < self.grid_h):
            return

        color = self.selected_color
        path = self.drawn_paths.get(color)
        if not path:
            return

        target = (nx, ny)

        # Step back along own path (implicit undo)
        if len(path) >= 2 and target == path[-2]:
            self._undo_last_cell(color)
            self.cursor_x, self.cursor_y = nx, ny
            return

        # Cannot re-enter own path
        if target in self._path_set(color):
            return

        ep1, ep2 = self.endpoints[color]
        start_ep = path[0]
        other_ep = ep2 if start_ep == ep1 else ep1

        # Reached the destination endpoint → complete this color
        if target == other_ep:
            path.append(target)
            self.cursor_x, self.cursor_y = nx, ny
            self.selected_color = 0
            return

        # Move into an empty cell
        if self.grid[ny][nx] == 0:
            path.append(target)
            self.grid[ny][nx] = color
            self.cursor_x, self.cursor_y = nx, ny
            return

        # Cross a bridge occupied by a different color
        if target in self.bridges and self.grid[ny][nx] != color:
            path.append(target)
            self.cursor_x, self.cursor_y = nx, ny
            return

    def _undo_last_cell(self, color):
        path = self.drawn_paths[color]
        if not path:
            return
        removed = path.pop()
        rx, ry = removed

        ep1, ep2 = self.endpoints[color]
        if removed in (ep1, ep2):
            return

        if self.grid[ry][rx] == color:
            other = self._other_occupant(removed, color)
            self.grid[ry][rx] = other

    def _clear_drawn_path(self, color):
        ep1, ep2 = self.endpoints[color]
        old_path = self.drawn_paths.get(color, [])
        for pos in old_path:
            if pos in (ep1, ep2):
                continue
            px, py = pos
            if self.grid[py][px] == color:
                other = self._other_occupant(pos, color)
                self.grid[py][px] = other
        self.drawn_paths[color] = []

    def _path_set(self, color):
        return set(self.drawn_paths.get(color, []))

    def _other_occupant(self, pos, exclude_color):
        for cid, p in self.drawn_paths.items():
            if cid != exclude_color and pos in p:
                return cid
        return 0

    # ------------------------------------------------------------------
    # Win condition
    # ------------------------------------------------------------------

    def _check_win(self):
        covered = set()
        for cid, (ep1, ep2) in self.endpoints.items():
            covered.add(ep1)
            covered.add(ep2)
        for path in self.drawn_paths.values():
            covered.update(path)

        if len(covered) < self.grid_w * self.grid_h:
            return False

        for cid, (ep1, ep2) in self.endpoints.items():
            if not self._path_connects(cid, ep1, ep2):
                return False

        return True

    def _path_connects(self, color, start, end):
        cells = self._path_set(color)
        cells.add(start)
        cells.add(end)

        visited = {start}
        queue = [start]
        while queue:
            pos = queue.pop(0)
            if pos == end:
                return True
            x, y = pos
            for dx, dy in DIRS:
                nb = (x + dx, y + dy)
                if nb not in visited and nb in cells:
                    visited.add(nb)
                    queue.append(nb)
        return False

    # ------------------------------------------------------------------
    # Board rendering
    # ------------------------------------------------------------------

    def _make_board_sprite(self):
        pixels = []
        for y in range(self.grid_h):
            row = []
            for x in range(self.grid_w):
                cid = self.grid[y][x]
                if cid > 0:
                    row.append(PATH_PALETTE[cid - 1])
                elif (x, y) in self.bridges:
                    row.append(BRIDGE_BG)
                else:
                    row.append(EMPTY)
            pixels.append(row)
        return Sprite(
            pixels=pixels, name="board", x=0, y=0, layer=0,
            blocking=BlockingMode.NOT_BLOCKED, collidable=False,
        )

    def _refresh_board(self):
        if self.board_sprite is None:
            return
        for y in range(self.grid_h):
            for x in range(self.grid_w):
                cid = self.grid[y][x]
                if cid > 0:
                    self.board_sprite.pixels[y, x] = PATH_PALETTE[cid - 1]
                elif (x, y) in self.bridges:
                    self.board_sprite.pixels[y, x] = BRIDGE_BG
                else:
                    self.board_sprite.pixels[y, x] = EMPTY

    def _sync_overlay(self):
        self.overlay.cursor_x = self.cursor_x
        self.overlay.cursor_y = self.cursor_y
        self.overlay.grid_w = self.grid_w
        self.overlay.grid_h = self.grid_h
        self.overlay.endpoints = self.endpoints
        self.overlay.selected_color = self.selected_color
        self.overlay.bridges = self.bridges
        self.overlay.drawn_paths = self.drawn_paths
        self.overlay.step_count = self.step_count
        self.overlay.max_steps = self.max_steps