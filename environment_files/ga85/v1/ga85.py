import random
import time
from collections import deque
from copy import deepcopy
from itertools import product

from arcengine import (
    ARCBaseGame,
    Camera,
    GameAction,
    Level,
    Sprite,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRID_SIZE = (32, 32)
CAM_W, CAM_H = 32, 32

BACKGROUND_COLOR = 0
PADDING_COLOR = 0

# ARC colour palette indices
# 0=black 1=blue 2=red 3=green 4=yellow 5=grey 6=magenta 7=orange 8=cyan 9=maroon
COLOR_CYCLE = [8, 2, 3, 4, 7, 6]

LEVEL_TARGET_COLORS = [2, 2, 2, 2, 2, 2]

# ---------------------------------------------------------------------------
# Level definitions — grid grows each level
# ---------------------------------------------------------------------------

LEVEL_DEFS = [
    {"pw": 3, "ph": 3, "num_colors": 2},
    {"pw": 4, "ph": 4, "num_colors": 2},
    {"pw": 5, "ph": 5, "num_colors": 3},
    {"pw": 6, "ph": 6, "num_colors": 3},
    {"pw": 7, "ph": 7, "num_colors": 4},
    {"pw": 8, "ph": 8, "num_colors": 5},
]

# Indicator in bottom-right
IND_INNER = 3
IND_BORDER = 1
IND_TOTAL = IND_INNER + IND_BORDER * 2


def _cell_size(pw, ph):
    return max(1, min(CAM_W // pw, CAM_H // ph))


# ---------------------------------------------------------------------------
# Grid helpers
# ---------------------------------------------------------------------------


def _apply_click(grid, cr, cc, pw, ph, colors_pool):
    """Apply a single click at grid position (row=cr, col=cc).
    Returns a NEW grid (shallow-copied rows)."""
    g = [row[:] for row in grid]
    nc = len(colors_pool)
    for tx, ty in [(cc, cr), (cc - 1, cr), (cc + 1, cr), (cc, cr - 1), (cc, cr + 1)]:
        if 0 <= tx < pw and 0 <= ty < ph:
            cur = g[ty][tx]
            try:
                ci = colors_pool.index(cur)
            except ValueError:
                ci = 0
            g[ty][tx] = colors_pool[(ci + 1) % nc]
    return g


def _grid_tuple(grid):
    return tuple(tuple(row) for row in grid)


def _is_solved(grid, target, pw, ph):
    for r in range(ph):
        for c in range(pw):
            if grid[r][c] != target:
                return False
    return True


# ---------------------------------------------------------------------------
# BFS solver — only used for small grids (up to 4x4 with 2 colors)
# ---------------------------------------------------------------------------


def _solve_bfs(grid, target, pw, ph, colors_pool, max_depth):
    """BFS solver. Returns list of (row, col) clicks or None."""
    if _is_solved(grid, target, pw, ph):
        return []

    start = _grid_tuple(grid)
    visited = {start}
    queue = deque([(grid, [])])

    while queue:
        g, moves = queue.popleft()
        if len(moves) >= max_depth:
            continue
        for r in range(ph):
            for c in range(pw):
                g2 = _apply_click(g, r, c, pw, ph, colors_pool)
                new_moves = moves + [(r, c)]
                if _is_solved(g2, target, pw, ph):
                    return new_moves
                t2 = _grid_tuple(g2)
                if t2 not in visited:
                    visited.add(t2)
                    queue.append((g2, new_moves))
    return None


# ---------------------------------------------------------------------------
# Solvable grid generation
#
# Strategy: scramble from solved state and RECORD every click.
# To undo a click in nc colours you must click the same cell (nc-1) times.
# So the solution for any scrambled grid is: for each scramble click,
# apply that same cell (nc-1) times.  We verify by replaying the
# solution on the generated grid to confirm it reaches the solved state.
# ---------------------------------------------------------------------------


def _verify_solution(grid, solution, target, pw, ph, colors_pool):
    """Apply solution clicks to grid, return True if it reaches solved."""
    g = [row[:] for row in grid]
    for cr, cc in solution:
        g = _apply_click(g, cr, cc, pw, ph, colors_pool)
    return _is_solved(g, target, pw, ph)


# ---------------------------------------------------------------------------
# Scramble-pattern strategies for levels 3+ (index >= 2)
#
# Each strategy returns a list of (row, col) cells to scramble-click.
# The cells are applied from a solved grid, so the result is always
# solvable.  Different strategies produce visually distinct layouts.
# ---------------------------------------------------------------------------


def _strategy_random(rng, pw, ph, num):
    """Pure random clicks (original strategy)."""
    clicks = []
    prev = (-1, -1)
    for _ in range(num * 3):
        if len(clicks) >= num:
            break
        sr, sc = rng.randint(0, ph - 1), rng.randint(0, pw - 1)
        if (sr, sc) == prev:
            continue
        clicks.append((sr, sc))
        prev = (sr, sc)
    return clicks


def _strategy_stripes(rng, pw, ph, num):
    """Scramble along randomly chosen rows OR columns → stripe patterns."""
    clicks = []
    horizontal = rng.choice([True, False])
    if horizontal:
        rows = list(range(ph))
        rng.shuffle(rows)
        for r in rows:
            if len(clicks) >= num:
                break
            cols = list(range(pw))
            rng.shuffle(cols)
            for c in cols:
                if len(clicks) >= num:
                    break
                clicks.append((r, c))
    else:
        cols = list(range(pw))
        rng.shuffle(cols)
        for c in cols:
            if len(clicks) >= num:
                break
            rows = list(range(ph))
            rng.shuffle(rows)
            for r in rows:
                if len(clicks) >= num:
                    break
                clicks.append((r, c))
    return clicks


def _strategy_diagonal(rng, pw, ph, num):
    """Scramble along diagonal lines → diagonal band patterns."""
    cells = []
    for d in range(-(ph - 1), pw):
        for r in range(ph):
            c = r + d
            if 0 <= c < pw:
                cells.append((r, c))
    # pick a random starting diagonal offset and walk from there
    rng.shuffle(cells)
    return cells[:num]


def _strategy_ring(rng, pw, ph, num):
    """Scramble from outer ring inward → concentric ring patterns."""
    cells = []
    for layer in range(max(pw, ph) // 2 + 1):
        ring = []
        for r in range(ph):
            for c in range(pw):
                dist = min(r, c, ph - 1 - r, pw - 1 - c)
                if dist == layer:
                    ring.append((r, c))
        rng.shuffle(ring)
        cells.extend(ring)
    return cells[:num]


def _strategy_cluster(rng, pw, ph, num):
    """Pick random cluster centers, then scramble nearby cells → patchy blobs."""
    n_clusters = rng.randint(2, max(2, num // 2))
    centers = [
        (rng.randint(0, ph - 1), rng.randint(0, pw - 1)) for _ in range(n_clusters)
    ]
    clicks = []
    used = set()
    for cr, cc in centers:
        # add the center and its cross-neighbours
        for dr, dc in [
            (0, 0),
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
            (-1, -1),
            (1, 1),
            (-1, 1),
            (1, -1),
        ]:
            nr, nc_ = cr + dr, cc + dc
            if 0 <= nr < ph and 0 <= nc_ < pw and (nr, nc_) not in used:
                clicks.append((nr, nc_))
                used.add((nr, nc_))
            if len(clicks) >= num:
                break
        if len(clicks) >= num:
            break
    # if still short, pad with random
    while len(clicks) < num:
        sr, sc = rng.randint(0, ph - 1), rng.randint(0, pw - 1)
        clicks.append((sr, sc))
    return clicks[:num]


def _strategy_checkerboard(rng, pw, ph, num):
    """Scramble only even or odd parity cells → checkerboard-style patterns."""
    parity = rng.choice([0, 1])
    cells = [(r, c) for r in range(ph) for c in range(pw) if (r + c) % 2 == parity]
    rng.shuffle(cells)
    return cells[:num]


def _strategy_cross(rng, pw, ph, num):
    """Scramble in a big cross / plus shape through the center."""
    mid_r, mid_c = ph // 2, pw // 2
    cells = []
    # horizontal bar
    for c in range(pw):
        cells.append((mid_r, c))
    # vertical bar (skip center to avoid duplicate)
    for r in range(ph):
        if r != mid_r:
            cells.append((r, mid_c))
    rng.shuffle(cells)
    return cells[:num]


# All advanced strategies for levels 3+
_ADVANCED_STRATEGIES = [
    _strategy_stripes,
    _strategy_diagonal,
    _strategy_ring,
    _strategy_cluster,
    _strategy_checkerboard,
    _strategy_cross,
]


def _generate_solvable_grid(rng, pw, ph, nc, target, level_idx):
    colors_pool = COLOR_CYCLE[:nc]

    # How many scramble clicks — scales with level
    min_scrambles = max(2, level_idx + 2)
    max_scrambles = min_scrambles + 3

    for _attempt in range(500):
        # --- start from solved state ---
        grid = [[target] * pw for _ in range(ph)]

        num = rng.randint(min_scrambles, max_scrambles)

        # --- choose scramble strategy ---
        if level_idx < 2:
            # Levels 1-2: simple random
            scramble_clicks = _strategy_random(rng, pw, ph, num)
        else:
            # Levels 3+: pick a random advanced strategy each time
            strategy = rng.choice(_ADVANCED_STRATEGIES)
            scramble_clicks = strategy(rng, pw, ph, num)

        # --- apply the scramble clicks ---
        prev = (-1, -1)
        filtered = []
        for sr, sc in scramble_clicks:
            # Avoid clicking same cell twice in a row (cancels for nc==2)
            if (sr, sc) == prev:
                continue
            grid = _apply_click(grid, sr, sc, pw, ph, colors_pool)
            filtered.append((sr, sc))
            prev = (sr, sc)

        scramble_clicks = filtered

        # --- reject if already solved ---
        if _is_solved(grid, target, pw, ph):
            continue

        # --- build the solution ---
        # Each scramble click needs (nc - 1) repetitions to undo it.
        # We reverse the order so we undo the last scramble first.
        solution = []
        for cr, cc in reversed(scramble_clicks):
            for _ in range(nc - 1):
                solution.append((cr, cc))

        # --- VERIFY the solution actually works ---
        if not _verify_solution(grid, solution, target, pw, ph, colors_pool):
            continue  # should never happen, but safety check

        # --- for small grids, also try BFS for a shorter solution ---
        if pw <= 4 and ph <= 4 and nc <= 2:
            bfs_sol = _solve_bfs(grid, target, pw, ph, colors_pool, 8)
            if bfs_sol is not None and len(bfs_sol) < len(solution):
                solution = bfs_sol

        return grid, solution

    # Fallback — single click at center
    grid = [[target] * pw for _ in range(ph)]
    grid = _apply_click(grid, ph // 2, pw // 2, pw, ph, colors_pool)
    # Solution: click center (nc-1) times
    solution = [(ph // 2, pw // 2)] * (nc - 1)
    return grid, solution


# =========================================================================
# Game class
# =========================================================================


class Ga85(ARCBaseGame):
    """
    Grid Alchemist — ARC-AGI-3 environment ga85

    Click a cell to advance its colour and its 4 orthogonal neighbours
    through the colour cycle.  Make every cell match the target colour
    (shown bottom-right) to clear the level.
    """

    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)
        self._seed = seed
        # Counter used to inject fresh entropy into each grid generation
        # so that every reset / level entry produces a different layout.
        self._generation_counter = 0

        # Per-level state — BEFORE super().__init__()
        self._grid = []
        self._initial_grid = []
        self._history = []
        self._cursor_gx = 0
        self._cursor_gy = 0
        self._ldef = None
        self._cs = 1
        self._origin_x = 0
        self._origin_y = 0
        self._target_color = 2

        camera = Camera(
            background=BACKGROUND_COLOR,
            letter_box=PADDING_COLOR,
            width=CAM_W,
            height=CAM_H,
            interfaces=[],
        )

        levels = [
            Level(sprites=[], grid_size=GRID_SIZE, name=f"Level {i + 1}")
            for i in range(len(LEVEL_DEFS))
        ]

        super().__init__(
            game_id="ga85",
            levels=levels,
            camera=camera,
            available_actions=[1, 2, 3, 4, 5, 6, 7],
            seed=seed,
        )

    # ------------------------------------------------------------------
    # Level setup
    # ------------------------------------------------------------------

    def on_set_level(self, level: Level) -> None:
        idx = self.level_index
        ldef = LEVEL_DEFS[idx]
        self._ldef = ldef
        pw, ph = ldef["pw"], ldef["ph"]
        nc = ldef["num_colors"]
        self._target_color = LEVEL_TARGET_COLORS[idx]

        cs = _cell_size(pw, ph)
        self._cs = cs
        # Center the puzzle in the full 32x32 camera
        self._origin_x = (CAM_W - pw * cs) // 2
        self._origin_y = (CAM_H - ph * cs) // 2

        # Always generate a fresh solvable grid with new entropy.
        # Bump the generation counter and create a one-off RNG seeded
        # from the base seed, the level index, the counter, AND the
        # current time so every call is unique.
        self._generation_counter += 1
        fresh_seed = (
            hash(
                (
                    self._seed,
                    idx,
                    self._generation_counter,
                    time.time_ns(),
                )
            )
            & 0xFFFFFFFF
        )
        gen_rng = random.Random(fresh_seed)

        grid, solution = _generate_solvable_grid(
            gen_rng, pw, ph, nc, self._target_color, idx
        )

        self._grid = grid
        self._initial_grid = deepcopy(grid)
        self._history = []
        self._cursor_gx = pw // 2
        self._cursor_gy = ph // 2

        self._rebuild_sprites(level)

    # ------------------------------------------------------------------
    # Sprite rebuilding
    # ------------------------------------------------------------------

    def _rebuild_sprites(self, level: Level) -> None:
        level.remove_all_sprites()

        pw = self._ldef["pw"]
        ph = self._ldef["ph"]
        cs = self._cs
        ox, oy = self._origin_x, self._origin_y

        # Cell sprites
        for r in range(ph):
            for c in range(pw):
                color = self._grid[r][c]
                px = [[color] * cs for _ in range(cs)]
                level.add_sprite(
                    Sprite(
                        pixels=px,
                        name=f"cell_{c}_{r}",
                        x=ox + c * cs,
                        y=oy + r * cs,
                        layer=1,
                        tags=["cell"],
                    )
                )

        # Cursor
        self._draw_cursor(level)

    def _draw_indicator(self, level: Level) -> None:
        ind_x = CAM_W - IND_TOTAL - 1
        ind_y = CAM_H - IND_TOTAL - 1

        white_pixels = [[10] * IND_TOTAL for _ in range(IND_TOTAL)]
        level.add_sprite(
            Sprite(
                pixels=white_pixels,
                name="ind_border",
                x=ind_x,
                y=ind_y,
                layer=2,
                tags=["indicator"],
            )
        )

        color_pixels = [[self._target_color] * IND_INNER for _ in range(IND_INNER)]
        level.add_sprite(
            Sprite(
                pixels=color_pixels,
                name="ind_color",
                x=ind_x + IND_BORDER,
                y=ind_y + IND_BORDER,
                layer=3,
                tags=["indicator"],
            )
        )

    def _draw_cursor(self, level: Level) -> None:
        for s in level.get_sprites_by_tag("cursor"):
            level.remove_sprite(s)

        cs = self._cs
        ox, oy = self._origin_x, self._origin_y
        cx = ox + self._cursor_gx * cs
        cy = oy + self._cursor_gy * cs

        cursor_pixels = []
        for row in range(cs):
            line = []
            for col in range(cs):
                if row == 0 or row == cs - 1 or col == 0 or col == cs - 1:
                    line.append(10)
                else:
                    line.append(-1)
            cursor_pixels.append(line)

        level.add_sprite(
            Sprite(
                pixels=cursor_pixels,
                name="cursor",
                x=cx,
                y=cy,
                layer=4,
                tags=["cursor"],
            )
        )

    # ------------------------------------------------------------------
    # Game logic
    # ------------------------------------------------------------------

    def _cycle_color(self, color: int) -> int:
        nc = self._ldef["num_colors"]
        pool = COLOR_CYCLE[:nc]
        try:
            idx = pool.index(color)
            return pool[(idx + 1) % len(pool)]
        except ValueError:
            return pool[0]

    def _activate_cell(self, gx: int, gy: int) -> None:
        pw = self._ldef["pw"]
        ph = self._ldef["ph"]
        if gx < 0 or gx >= pw or gy < 0 or gy >= ph:
            return
        self._history.append(deepcopy(self._grid))
        targets = [(gx, gy), (gx - 1, gy), (gx + 1, gy), (gx, gy - 1), (gx, gy + 1)]
        for tx, ty in targets:
            if 0 <= tx < pw and 0 <= ty < ph:
                self._grid[ty][tx] = self._cycle_color(self._grid[ty][tx])

    def _check_win(self) -> bool:
        pw = self._ldef["pw"]
        ph = self._ldef["ph"]
        for r in range(ph):
            for c in range(pw):
                if self._grid[r][c] != self._target_color:
                    return False
        return True

    def _pixel_to_grid(self, px: int, py: int):
        cs = self._cs
        ox, oy = self._origin_x, self._origin_y
        gx = (px - ox) // cs
        gy = (py - oy) // cs
        pw = self._ldef["pw"]
        ph = self._ldef["ph"]
        if 0 <= gx < pw and 0 <= gy < ph:
            return gx, gy
        return None

    # ------------------------------------------------------------------
    # Main step
    # ------------------------------------------------------------------

    def step(self) -> None:
        action = self.action
        level = self.current_level
        pw = self._ldef["pw"]
        ph = self._ldef["ph"]

        acted = False

        if action.id == GameAction.ACTION1:
            self._cursor_gy = max(0, self._cursor_gy - 1)
            self._draw_cursor(level)

        elif action.id == GameAction.ACTION2:
            self._cursor_gy = min(ph - 1, self._cursor_gy + 1)
            self._draw_cursor(level)

        elif action.id == GameAction.ACTION3:
            self._cursor_gx = max(0, self._cursor_gx - 1)
            self._draw_cursor(level)

        elif action.id == GameAction.ACTION4:
            self._cursor_gx = min(pw - 1, self._cursor_gx + 1)
            self._draw_cursor(level)

        elif action.id == GameAction.ACTION5:
            self._activate_cell(self._cursor_gx, self._cursor_gy)
            acted = True

        elif action.id == GameAction.ACTION6:
            display_x = action.data.get("x", None)
            display_y = action.data.get("y", None)
            if display_x is not None and display_y is not None:
                grid_coords = self.camera.display_to_grid(display_x, display_y)
                if grid_coords is not None:
                    result = self._pixel_to_grid(grid_coords[0], grid_coords[1])
                    if result is not None:
                        gx, gy = result
                        self._cursor_gx = gx
                        self._cursor_gy = gy
                        self._activate_cell(gx, gy)
                        acted = True

        elif action.id == GameAction.ACTION7:
            if self._history:
                self._grid = self._history.pop()
                acted = True

        if acted:
            self._rebuild_sprites(level)

        if acted and action.id not in (GameAction.ACTION7,) and self._check_win():
            self.next_level()

        self.complete_action()
