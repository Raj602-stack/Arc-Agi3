"""
PM07 - Pattern Master: A 7-level hidden-rule grid puzzle game for ARC-AGI-3.

Every level uses ONLY arrow keys (+ Ctrl+Z for undo). No Space bar, no mouse.
Each level has a HIDDEN RULE the player must discover through experimentation.

Level 1 — "Color Echo"      (8×8)   Move onto gray cells; they copy the color
                                      of the cell you just LEFT. Paint every
                                      gray cell to win.

Level 2 — "Flood Walker"    (8×8)   Move cursor; every cell you walk over
                                      toggles between two colors. Make the
                                      entire grid one uniform color to win.

Level 3 — "Ice Slide"       (8×8)   You SLIDE on ice until you hit a wall or
                                      the edge. Collect all green gems by
                                      sliding into them.

Level 4 — "Gem Collector"   (8×8)   Navigate around walls and collect ALL
                                      yellow gems by walking into them.
                                      Simple maze navigation.

Level 5 — "Teleport Maze"  (8×8)    Navigate a maze to reach the green exit.
                                      Colored cells are teleporters — step on
                                      one and you warp to its matching pair.

Level 6 — "Mirror Walk"    (8×8)    You control TWO green blocks at once. One
                                      moves normally, the other mirrors movement.
                                      Both must land on the red destination block.

Level 7 — "Sokoban"        (10×10)  Push multiple blocks onto targets. Plan
                                      your moves — blocks can get stuck!
"""

import random
from copy import deepcopy

from arcengine import (
    ARCBaseGame,
    Camera,
    GameAction,
    Level,
    Sprite,
)

# ---------------------------------------------------------------------------
# Color palette (0-15)
# ---------------------------------------------------------------------------
C_BLACK      = 0   # background / empty
C_DARK_GRAY  = 1
C_RED        = 2
C_GREEN      = 3
C_BLUE       = 4
C_YELLOW     = 5
C_MAGENTA    = 6
C_ORANGE     = 7
C_CYAN       = 8
C_BROWN      = 9
C_PINK       = 10
C_LIME       = 11
C_PURPLE     = 12
C_TEAL       = 13
C_WHITE      = 14
C_LIGHT_GRAY = 15

# Padding / letterbox color
PADDING_COLOR = C_DARK_GRAY

# Colors used across various levels
PLAYABLE_COLORS = [C_RED, C_GREEN, C_BLUE, C_YELLOW, C_MAGENTA, C_ORANGE,
                   C_CYAN, C_BROWN, C_PINK, C_LIME, C_PURPLE, C_TEAL]

# ---------------------------------------------------------------------------
# Sprite definitions
# ---------------------------------------------------------------------------
sprites = {
    "cursor": Sprite(
        pixels=[[C_WHITE]],
        name="cursor",
        visible=True,
        collidable=False,
    ),
    "green_cursor": Sprite(
        pixels=[[C_GREEN]],
        name="green_cursor",
        visible=True,
        collidable=False,
    ),
    "cell": Sprite(
        pixels=[[C_BLACK]],
        name="cell",
        visible=True,
        collidable=True,
    ),
}

# ---------------------------------------------------------------------------
# Level definitions (grid sizes scale with difficulty)
# ---------------------------------------------------------------------------
levels = [
    Level(sprites=[], grid_size=(8, 8)),      # Level 1 — Color Echo
    Level(sprites=[], grid_size=(8, 8)),      # Level 2 — Flood Walker
    Level(sprites=[], grid_size=(8, 8)),      # Level 3 — Ice Slide
    Level(sprites=[], grid_size=(8, 8)),      # Level 4 — Gem Collector
    Level(sprites=[], grid_size=(8, 8)),      # Level 5 — Block Push
    Level(sprites=[], grid_size=(8, 8)),      # Level 6 — Mirror Walk
    Level(sprites=[], grid_size=(10, 10)),    # Level 7 — Sokoban
]


# ===================================================================
# Main game class
# ===================================================================
class Pm07(ARCBaseGame):
    """Pattern Master — 7 hidden-rule grid puzzles, ALL arrow-keys only."""

    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)
        self._seed = seed

        camera = Camera(
            background=C_BLACK,
            letter_box=PADDING_COLOR,
            width=16,
            height=16,
        )

        super().__init__(
            game_id="pm07",
            levels=levels,
            camera=camera,
        )

        # Per-level state (populated in on_set_level)
        self._grid = []
        self._goal = []
        self._cursor_x = 0
        self._cursor_y = 0
        self._history = []
        self._phase = 0
        self._prev_color = C_BLACK
        self._last_dx = 0
        self._last_dy = 0
        self._extra = {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_level_index(self) -> int:
        for i, lev in enumerate(self._levels):
            if lev is self.current_level:
                return i
        return 0

    def _blank_grid(self, w: int, h: int, color: int = C_BLACK):
        return [[color for _ in range(w)] for _ in range(h)]

    def _save_state(self):
        self._history.append((
            deepcopy(self._grid),
            self._cursor_x,
            self._cursor_y,
            self._phase,
            self._last_dx,
            self._last_dy,
            self._prev_color,
            deepcopy(self._extra),
        ))

    def _undo(self):
        if self._history:
            (self._grid, self._cursor_x, self._cursor_y,
             self._phase, self._last_dx, self._last_dy,
             self._prev_color, self._extra) = self._history.pop()
            self._render_grid()

    def _get_dir(self, action_id):
        """Return (dx, dy) for directional actions, or (0, 0)."""
        if action_id == GameAction.ACTION1:
            return 0, -1  # up
        elif action_id == GameAction.ACTION2:
            return 0, 1   # down
        elif action_id == GameAction.ACTION3:
            return -1, 0  # left
        elif action_id == GameAction.ACTION4:
            return 1, 0   # right
        return 0, 0

    def _in_bounds(self, x, y, w, h):
        return 0 <= x < w and 0 <= y < h

    # ------------------------------------------------------------------
    # Level setup
    # ------------------------------------------------------------------
    def on_set_level(self, level: Level) -> None:
        idx = self._get_level_index()
        w, h = level.grid_size
        self._history = []
        self._phase = 0
        self._last_dx = 0
        self._last_dy = 0
        self._prev_color = C_BLACK
        self._extra = {}

        setup = [
            self._setup_level_1,
            self._setup_level_2,
            self._setup_level_3,
            self._setup_level_4,
            self._setup_level_5,
            self._setup_level_6,
            self._setup_level_7,
        ]
        setup[idx](w, h)
        self._render_grid()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _render_grid(self):
        level = self.current_level
        for sp in list(level._sprites):
            level.remove_sprite(sp)

        h = len(self._grid)
        w = len(self._grid[0]) if h else 0

        for y in range(h):
            for x in range(w):
                color = self._grid[y][x]
                sp = sprites["cell"].clone()
                sp = sp.color_remap(None, color)
                sp = sp.set_position(x, y)
                level.add_sprite(sp)

        # Draw cursor on all levels
        idx = self._get_level_index()
        if idx == 5:  # Level 6 — both cursors are green
            cur = sprites["green_cursor"].clone().set_position(
                self._cursor_x, self._cursor_y
            )
            level.add_sprite(cur)

            mx = self._extra.get("mirror_x", 0)
            my = self._extra.get("mirror_y", 0)
            mirror_cur = sprites["green_cursor"].clone().set_position(mx, my)
            level.add_sprite(mirror_cur)
        else:
            cur = sprites["cursor"].clone().set_position(
                self._cursor_x, self._cursor_y
            )
            level.add_sprite(cur)

    # ------------------------------------------------------------------
    # Step (main game loop)
    # ------------------------------------------------------------------
    def step(self) -> None:
        action = self.action

        if action.id == GameAction.ACTION7:
            self._undo()
            self.complete_action()
            return

        idx = self._get_level_index()
        handler = [
            self._step_level_1,
            self._step_level_2,
            self._step_level_3,
            self._step_level_4,
            self._step_level_5,
            self._step_level_6,
            self._step_level_7,
        ]
        handler[idx]()
        self.complete_action()

    # ==================================================================
    #  LEVEL 1 — Color Echo (8×8)
    #
    #  Hidden rule: Move the cursor around. When you step onto a GRAY
    #  cell (C_LIGHT_GRAY), it copies the color of the cell you just
    #  LEFT. You need to carry colors from source cells to paint all
    #  gray cells. Paint every gray cell to win.
    #
    #  Controls: Arrow keys only.
    #  Difficulty: ★☆☆☆☆ Tutorial — very easy.
    # ==================================================================
    def _setup_level_1(self, w: int, h: int):
        self._grid = self._blank_grid(w, h, C_BLACK)
        self._cursor_x = 0
        self._cursor_y = 0

        painted = set()
        # Place 8-12 colored source cells
        num_sources = self._rng.randint(8, 12)
        for _ in range(num_sources):
            x = self._rng.randint(0, w - 1)
            y = self._rng.randint(0, h - 1)
            if (x, y) not in painted:
                self._grid[y][x] = self._rng.choice(PLAYABLE_COLORS[:6])
                painted.add((x, y))

        # Place 6-10 gray target cells
        num_targets = self._rng.randint(6, 10)
        placed = 0
        attempts = 0
        while placed < num_targets and attempts < 200:
            x = self._rng.randint(0, w - 1)
            y = self._rng.randint(0, h - 1)
            attempts += 1
            if (x, y) not in painted and (x, y) != (0, 0):
                self._grid[y][x] = C_LIGHT_GRAY
                painted.add((x, y))
                placed += 1

        self._prev_color = C_BLACK

    def _step_level_1(self):
        action = self.action
        dx, dy = self._get_dir(action.id)
        if dx == 0 and dy == 0:
            return

        self._save_state()
        w, h = self.current_level.grid_size

        # Remember color of cell we're LEAVING
        leaving_color = self._grid[self._cursor_y][self._cursor_x]
        if leaving_color != C_LIGHT_GRAY and leaving_color != C_BLACK:
            self._prev_color = leaving_color

        nx = max(0, min(w - 1, self._cursor_x + dx))
        ny = max(0, min(h - 1, self._cursor_y + dy))
        self._cursor_x, self._cursor_y = nx, ny

        # If landed on gray -> paint it with prev_color
        if self._grid[ny][nx] == C_LIGHT_GRAY and self._prev_color != C_BLACK:
            self._grid[ny][nx] = self._prev_color

        self._render_grid()

        # Win: no gray cells remain
        if not any(c == C_LIGHT_GRAY for row in self._grid for c in row):
            self.next_level()

    # ==================================================================
    #  LEVEL 2 — Flood Walker (8×8)
    #
    #  Hidden rule: The grid is filled with two colors. Every cell you
    #  walk over TOGGLES between the two colors. Make the entire grid
    #  a single uniform color to win.
    #
    #  Controls: Arrow keys only.
    #  Difficulty: ★★☆☆☆ Basic.
    # ==================================================================
    def _setup_level_2(self, w: int, h: int):
        c1, c2 = C_CYAN, C_ORANGE
        self._extra["c1"] = c1
        self._extra["c2"] = c2
        self._grid = self._blank_grid(w, h, c1)
        # Randomly set ~40% to c2
        for y in range(h):
            for x in range(w):
                if self._rng.random() < 0.4:
                    self._grid[y][x] = c2
        self._cursor_x = w // 2
        self._cursor_y = h // 2

    def _step_level_2(self):
        action = self.action
        dx, dy = self._get_dir(action.id)
        if dx == 0 and dy == 0:
            return

        self._save_state()
        w, h = self.current_level.grid_size
        nx = max(0, min(w - 1, self._cursor_x + dx))
        ny = max(0, min(h - 1, self._cursor_y + dy))
        self._cursor_x, self._cursor_y = nx, ny

        c1 = self._extra["c1"]
        c2 = self._extra["c2"]
        cur = self._grid[ny][nx]
        self._grid[ny][nx] = c2 if cur == c1 else c1

        self._render_grid()

        # Win: entire grid is one color
        first = self._grid[0][0]
        if all(self._grid[r][c] == first for r in range(h) for c in range(w)):
            self.next_level()

    # ==================================================================
    #  LEVEL 3 — Ice Slide (8×8)
    #
    #  Hidden rule: When you press an arrow key you SLIDE across the
    #  ice in that direction until you hit a wall or the grid edge.
    #  Green gems are scattered on the grid — slide into them to
    #  collect them. Collect ALL green gems to win.
    #
    #  One simple rule to discover: you don't stop after one step,
    #  you keep sliding. Use walls to position yourself.
    #
    #  Controls: Arrow keys only.
    #  Difficulty: ★★☆☆☆ Easy.
    # ==================================================================
    def _can_reach_by_slide(self, target_x, target_y, w, h):
        """BFS check: can the cursor at (0,0) reach a cell adjacent to
        or passing through (target_x, target_y) via ice-slide moves?
        Returns True if the gem at target is collectible."""
        from collections import deque

        visited = set()
        queue = deque()
        queue.append((0, 0))
        visited.add((0, 0))

        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]

        while queue:
            cx, cy = queue.popleft()
            for ddx, ddy in directions:
                # Simulate a slide from (cx, cy) in direction (ddx, ddy)
                sx, sy = cx, cy
                passed_target = False
                while True:
                    nx, ny = sx + ddx, sy + ddy
                    if not self._in_bounds(nx, ny, w, h):
                        break
                    cell = self._grid[ny][nx]
                    if cell == C_DARK_GRAY:
                        break
                    if nx == target_x and ny == target_y:
                        passed_target = True
                    sx, sy = nx, ny

                if passed_target:
                    return True
                if (sx, sy) not in visited:
                    visited.add((sx, sy))
                    queue.append((sx, sy))

        return False

    def _setup_level_3(self, w: int, h: int):
        self._grid = self._blank_grid(w, h, C_BLACK)
        self._cursor_x = 0
        self._cursor_y = 0

        used = {(0, 0)}

        # Place walls in a structured grid-like pattern so there are
        # plenty of stopping points across the board
        wall_positions = set()

        # Place a few "pillars" in a loose grid to guarantee stop points
        # This ensures you can reach most areas of the board
        pillar_spots = []
        for py in range(2, h - 1, 3):
            for px in range(2, w - 1, 3):
                if (px, py) not in used and self._rng.random() < 0.7:
                    self._grid[py][px] = C_DARK_GRAY
                    wall_positions.add((px, py))
                    used.add((px, py))
                    pillar_spots.append((px, py))

        # Add a few extra random walls
        extra = self._rng.randint(2, 4)
        for _ in range(extra):
            attempts = 0
            while attempts < 50:
                wx = self._rng.randint(1, w - 2)
                wy = self._rng.randint(1, h - 2)
                if (wx, wy) not in used:
                    self._grid[wy][wx] = C_DARK_GRAY
                    wall_positions.add((wx, wy))
                    used.add((wx, wy))
                    break
                attempts += 1

        # Place 3 green gems — each must be reachable by sliding
        num_gems = 3
        self._extra["gems_total"] = num_gems
        self._extra["gems_left"] = num_gems
        placed_gems = 0
        gem_attempts = 0
        while placed_gems < num_gems and gem_attempts < 300:
            gem_attempts += 1
            gx = self._rng.randint(0, w - 1)
            gy = self._rng.randint(0, h - 1)
            if (gx, gy) in used:
                continue
            # Temporarily place gem to test reachability
            self._grid[gy][gx] = C_GREEN
            if self._can_reach_by_slide(gx, gy, w, h):
                used.add((gx, gy))
                placed_gems += 1
            else:
                # Not reachable — remove and try again
                self._grid[gy][gx] = C_BLACK

        # Update gem count in case we couldn't place all
        self._extra["gems_total"] = placed_gems
        self._extra["gems_left"] = placed_gems

    def _step_level_3(self):
        action = self.action
        dx, dy = self._get_dir(action.id)
        if dx == 0 and dy == 0:
            return

        self._save_state()
        w, h = self.current_level.grid_size

        # ICE SLIDE: keep moving until we hit something
        cx, cy = self._cursor_x, self._cursor_y
        while True:
            nx, ny = cx + dx, cy + dy
            if not self._in_bounds(nx, ny, w, h):
                break  # hit edge
            cell = self._grid[ny][nx]
            if cell == C_DARK_GRAY:
                break  # hit wall
            # Collect gem if we slide over/into it
            if cell == C_GREEN:
                self._grid[ny][nx] = C_BLACK
                self._extra["gems_left"] = self._extra.get("gems_left", 0) - 1
            cx, cy = nx, ny

        self._cursor_x, self._cursor_y = cx, cy
        self._render_grid()

        # Win: collected all gems
        if self._extra.get("gems_left", 1) <= 0:
            self.next_level()

    # ==================================================================
    #  LEVEL 4 — Gem Collector (8×8)
    #
    #  Hidden rule: Yellow gems are scattered in a maze of walls. Walk
    #  into a gem to collect it. Collect ALL gems to win. Simple maze
    #  navigation — just find your way to each gem.
    #
    #  All gems are guaranteed reachable via BFS from the start.
    #
    #  Controls: Arrow keys only.
    #  Difficulty: ★★★☆☆ Medium.
    # ==================================================================
    def _bfs_reachable_cells(self, start_x, start_y, w, h):
        """Return set of all cells reachable by normal walking from start."""
        from collections import deque
        visited = set()
        queue = deque()
        queue.append((start_x, start_y))
        visited.add((start_x, start_y))
        while queue:
            cx, cy = queue.popleft()
            for ddx, ddy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nx, ny = cx + ddx, cy + ddy
                if (self._in_bounds(nx, ny, w, h) and
                        (nx, ny) not in visited and
                        self._grid[ny][nx] != C_DARK_GRAY):
                    visited.add((nx, ny))
                    queue.append((nx, ny))
        return visited

    def _setup_level_4(self, w: int, h: int):
        self._grid = self._blank_grid(w, h, C_BLACK)

        # Start in top-left
        self._cursor_x = 0
        self._cursor_y = 0

        used = {(0, 0)}

        # Build a maze using wall "bars" — short horizontal and vertical
        # segments that create corridors but don't isolate areas
        wall_positions = set()

        # Place horizontal bars (length 2-3)
        num_bars = self._rng.randint(3, 5)
        for _ in range(num_bars):
            attempts = 0
            while attempts < 50:
                bx = self._rng.randint(1, w - 3)
                by = self._rng.randint(1, h - 2)
                bar_len = self._rng.randint(2, 3)
                cells = [(bx + i, by) for i in range(bar_len)]
                if all((cx, cy) not in used and self._in_bounds(cx, cy, w, h)
                       for cx, cy in cells):
                    for cx, cy in cells:
                        self._grid[cy][cx] = C_DARK_GRAY
                        wall_positions.add((cx, cy))
                        used.add((cx, cy))
                    break
                attempts += 1

        # Place vertical bars (length 2-3)
        num_bars = self._rng.randint(3, 5)
        for _ in range(num_bars):
            attempts = 0
            while attempts < 50:
                bx = self._rng.randint(1, w - 2)
                by = self._rng.randint(1, h - 3)
                bar_len = self._rng.randint(2, 3)
                cells = [(bx, by + i) for i in range(bar_len)]
                if all((cx, cy) not in used and self._in_bounds(cx, cy, w, h)
                       for cx, cy in cells):
                    for cx, cy in cells:
                        self._grid[cy][cx] = C_DARK_GRAY
                        wall_positions.add((cx, cy))
                        used.add((cx, cy))
                    break
                attempts += 1

        # Find all reachable cells from start
        reachable = self._bfs_reachable_cells(0, 0, w, h)

        # Place 4-6 yellow gems in reachable cells
        num_gems = self._rng.randint(4, 6)
        self._extra["gems_total"] = num_gems
        self._extra["gems_left"] = num_gems

        # Get list of reachable empty cells (not start, not walls)
        candidates = [(x, y) for x, y in reachable
                       if (x, y) not in used and self._grid[y][x] == C_BLACK]
        self._rng.shuffle(candidates)

        placed = 0
        for gx, gy in candidates:
            if placed >= num_gems:
                break
            self._grid[gy][gx] = C_YELLOW
            used.add((gx, gy))
            placed += 1

        # Update gem count if we couldn't place all
        self._extra["gems_total"] = placed
        self._extra["gems_left"] = placed
        self._extra["wall_positions"] = wall_positions

    def _step_level_4(self):
        action = self.action
        dx, dy = self._get_dir(action.id)
        if dx == 0 and dy == 0:
            return

        self._save_state()
        w, h = self.current_level.grid_size
        wall_positions = self._extra["wall_positions"]

        nx = self._cursor_x + dx
        ny = self._cursor_y + dy

        # Check bounds
        if not self._in_bounds(nx, ny, w, h):
            return

        # Can't walk into walls
        if (nx, ny) in wall_positions:
            return

        # Move cursor
        self._cursor_x, self._cursor_y = nx, ny

        # Collect gem if we walked onto one
        if self._grid[ny][nx] == C_YELLOW:
            self._grid[ny][nx] = C_BLACK
            self._extra["gems_left"] = self._extra.get("gems_left", 0) - 1

        self._render_grid()

        # Win: collected all gems
        if self._extra.get("gems_left", 1) <= 0:
            self.next_level()

    # ==================================================================
    #  LEVEL 5 — Teleport Maze (8×8)
    #
    #  Hidden rule: Navigate a maze of walls to reach the GREEN exit
    #  cell. Colored cells are TELEPORTERS — step onto one and you
    #  instantly warp to the other cell of the same color. There are
    #  2-3 teleporter pairs (e.g. two red cells, two blue cells).
    #
    #  The player must figure out:
    #    1) Colored cells teleport you to the matching color
    #    2) Use teleporters to bypass walls
    #    3) Reach the green cell to win
    #
    #  GUARANTEED SOLVABLE: BFS verifies the exit is reachable from
    #  the start via walking + teleporting. Regenerates if not.
    #
    #  Controls: Arrow keys only.
    #  Difficulty: ★★★☆☆ Medium.
    # ==================================================================
    def _bfs_teleport_reachable(self, start_x, start_y, target_x, target_y,
                                 w, h, teleport_map):
        """BFS check: can we reach target from start via walking + teleporters?"""
        from collections import deque
        visited = set()
        queue = deque()
        queue.append((start_x, start_y))
        visited.add((start_x, start_y))

        while queue:
            cx, cy = queue.popleft()
            if cx == target_x and cy == target_y:
                return True

            for ddx, ddy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nx, ny = cx + ddx, cy + ddy
                if not self._in_bounds(nx, ny, w, h):
                    continue
                if self._grid[ny][nx] == C_DARK_GRAY:
                    continue

                # After stepping, check for teleport
                final_x, final_y = nx, ny
                if (nx, ny) in teleport_map:
                    final_x, final_y = teleport_map[(nx, ny)]

                if (final_x, final_y) not in visited:
                    visited.add((final_x, final_y))
                    queue.append((final_x, final_y))
                # Also add the pre-teleport cell as visited
                if (nx, ny) not in visited:
                    visited.add((nx, ny))

        return False

    def _setup_level_5(self, w: int, h: int):
        # Retry loop — regenerate until we get a solvable layout
        for _gen_attempt in range(50):
            self._grid = self._blank_grid(w, h, C_BLACK)

            self._cursor_x = 0
            self._cursor_y = 0
            used = {(0, 0)}
            wall_positions = set()

            # Build maze walls — horizontal and vertical bars
            num_h_bars = self._rng.randint(2, 4)
            for _ in range(num_h_bars):
                attempts = 0
                while attempts < 50:
                    bx = self._rng.randint(0, w - 2)
                    by = self._rng.randint(1, h - 2)
                    bar_len = self._rng.randint(2, 4)
                    cells = [(bx + i, by) for i in range(bar_len)
                             if self._in_bounds(bx + i, by, w, h)]
                    if all((cx, cy) not in used for cx, cy in cells) and len(cells) >= 2:
                        for cx, cy in cells:
                            self._grid[cy][cx] = C_DARK_GRAY
                            wall_positions.add((cx, cy))
                            used.add((cx, cy))
                        break
                    attempts += 1

            num_v_bars = self._rng.randint(2, 3)
            for _ in range(num_v_bars):
                attempts = 0
                while attempts < 50:
                    bx = self._rng.randint(1, w - 2)
                    by = self._rng.randint(0, h - 2)
                    bar_len = self._rng.randint(2, 4)
                    cells = [(bx, by + i) for i in range(bar_len)
                             if self._in_bounds(bx, by + i, w, h)]
                    if all((cx, cy) not in used for cx, cy in cells) and len(cells) >= 2:
                        for cx, cy in cells:
                            self._grid[cy][cx] = C_DARK_GRAY
                            wall_positions.add((cx, cy))
                            used.add((cx, cy))
                        break
                    attempts += 1

            self._extra["wall_positions"] = wall_positions

            # Place GREEN exit in bottom-right area
            ex, ey = w - 1, h - 1
            attempts = 0
            while attempts < 100:
                ex = self._rng.randint(w // 2, w - 1)
                ey = self._rng.randint(h // 2, h - 1)
                if (ex, ey) not in used:
                    break
                attempts += 1
            self._grid[ey][ex] = C_GREEN
            used.add((ex, ey))
            self._extra["exit_x"] = ex
            self._extra["exit_y"] = ey

            # Place 2 teleporter PAIRS (same color = linked)
            teleport_colors = [C_RED, C_BLUE]
            num_pairs = 2
            teleport_map = {}

            for i in range(num_pairs):
                color = teleport_colors[i]
                pair = []
                for _ in range(2):
                    attempts = 0
                    while attempts < 100:
                        tx = self._rng.randint(0, w - 1)
                        ty = self._rng.randint(0, h - 1)
                        if (tx, ty) not in used:
                            self._grid[ty][tx] = color
                            used.add((tx, ty))
                            pair.append((tx, ty))
                            break
                        attempts += 1

                if len(pair) == 2:
                    teleport_map[pair[0]] = pair[1]
                    teleport_map[pair[1]] = pair[0]

            self._extra["teleport_map"] = teleport_map

            # SOLVABILITY CHECK: BFS from start to exit using teleporters
            if self._bfs_teleport_reachable(0, 0, ex, ey, w, h, teleport_map):
                return  # Solvable! Use this layout.

            # Not solvable — wipe and try again

        # Fallback: if 50 attempts failed, create a trivial solvable level
        self._grid = self._blank_grid(w, h, C_BLACK)
        self._cursor_x = 0
        self._cursor_y = 0
        ex, ey = w - 1, h - 1
        self._grid[ey][ex] = C_GREEN
        self._extra["exit_x"] = ex
        self._extra["exit_y"] = ey
        self._extra["wall_positions"] = set()
        self._extra["teleport_map"] = {}

    def _step_level_5(self):
        action = self.action
        dx, dy = self._get_dir(action.id)
        if dx == 0 and dy == 0:
            return

        self._save_state()
        w, h = self.current_level.grid_size
        wall_positions = self._extra["wall_positions"]
        teleport_map = self._extra["teleport_map"]

        nx = self._cursor_x + dx
        ny = self._cursor_y + dy

        # Check bounds
        if not self._in_bounds(nx, ny, w, h):
            return

        # Can't walk into walls
        if (nx, ny) in wall_positions:
            return

        # Move cursor
        self._cursor_x = nx
        self._cursor_y = ny

        # Check if we landed on a teleporter
        if (nx, ny) in teleport_map:
            dest_x, dest_y = teleport_map[(nx, ny)]
            self._cursor_x = dest_x
            self._cursor_y = dest_y

        self._render_grid()

        # Win: reached the green exit
        ex = self._extra["exit_x"]
        ey = self._extra["exit_y"]
        if self._cursor_x == ex and self._cursor_y == ey:
            self.next_level()

    # ==================================================================
    #  LEVEL 6 — Mirror Walk (8×8)
    #
    #  Hidden rule: You control TWO green blocks at once. One moves
    #  normally with arrow keys. The other moves in the OPPOSITE
    #  direction. Both green blocks must be aligned and positioned
    #  on the single red destination block at the same time.
    #  Use walls to manipulate the movements — when a green block
    #  hits a wall it stays put while the other keeps moving.
    #
    #  Only colors on the board: black (empty), dark gray (walls),
    #  red (destination block), green (both moving blocks).
    #
    #  Controls: Arrow keys only.
    #  Difficulty: ★★★★☆ Hard.
    # ==================================================================
    @staticmethod
    def _bfs_mirror_solvable(w, h, walls, cx, cy, mx, my, tx, ty):
        """BFS over joint state (main_x, main_y, mirror_x, mirror_y).

        Main cursor moves (dx, dy); mirror cursor moves (-dx, -dy).
        Returns True if both cursors can simultaneously reach the
        single target at (tx, ty).
        """
        from collections import deque as _deque

        start = (cx, cy, mx, my)
        if cx == tx and cy == ty and mx == tx and my == ty:
            return True

        directions = ((0, -1), (0, 1), (-1, 0), (1, 0))
        visited = {start}
        queue = _deque([start])

        while queue:
            scx, scy, smx, smy = queue.popleft()
            for dx, dy in directions:
                ncx, ncy = scx + dx, scy + dy
                if not (0 <= ncx < w and 0 <= ncy < h) or (ncx, ncy) in walls:
                    ncx, ncy = scx, scy
                nmx, nmy = smx - dx, smy - dy
                if not (0 <= nmx < w and 0 <= nmy < h) or (nmx, nmy) in walls:
                    nmx, nmy = smx, smy
                ns = (ncx, ncy, nmx, nmy)
                if ns not in visited:
                    visited.add(ns)
                    if ncx == tx and ncy == ty and nmx == tx and nmy == ty:
                        return True
                    queue.append(ns)
        return False

    # ------------------------------------------------------------------
    # Hand-crafted level-6 puzzle library.
    #
    # Each puzzle is a dict with:
    #   "walls"  — set of (x,y) wall positions
    #   "g1"     — (x,y) start of green block 1 (main, moves normally)
    #   "g2"     — (x,y) start of green block 2 (mirror, moves opposite)
    #   "target" — (x,y) red destination block
    #
    # Design principles:
    #   • Positions symmetric about the target converge naturally.
    #   • Asymmetric positions REQUIRE walls — a block that hits a
    #     wall stays put (PINNED) while the other keeps moving.
    #   • Solutions are short (3-6 moves) and logically discoverable.
    #   • The grid is 8×8; coordinates are (col, row) with (0,0) top-left.
    #
    # All puzzles verified by BFS and step-by-step simulation.
    # ------------------------------------------------------------------
    _LEVEL6_PUZZLES = [
        # ── Puzzle 0  (tutorial — 3 moves, 8 walls) ───────────────
        # G1(3,0) and G2(3,6) symmetric about target (3,3).
        # Walls form a guiding channel so the path is obvious.
        # Solution: DOWN DOWN DOWN.
        #
        #   · · · G1 · · · ·      DOWN → G1(3,1), G2(3,5)
        #   · · ## ·  ## · · ·    DOWN → G1(3,2), G2(3,4)
        #   · · ## ·  ## · · ·    DOWN → G1(3,3), G2(3,3) ✓
        #   · · · RR · · · ·
        #   · · ## ·  ## · · ·
        #   · · ## ·  ## · · ·
        #   · · · G2 · · · ·
        #   · · · ·  · · · ·
        {
            "g1": (3, 0),
            "g2": (3, 6),
            "target": (3, 3),
            "walls": {(2,1),(4,1),(2,2),(4,2),(2,4),(4,4),(2,5),(4,5)},
        },

        # ── Puzzle 1  (4 moves, 10 walls, symmetric arena) ────────
        # G1(1,1) and G2(5,5) symmetric about target (3,3).
        # Walls form a symmetric arena. Solution: DOWN DOWN RIGHT RIGHT.
        #
        #   ## · ## · · · · ·
        #   · G1 · ## · · · ·
        #   ## · · ·  · · ## ·
        #   · · · RR · · · ·
        #   ## · · ·  · · ## ·
        #   · · · ## · G2 · ·
        #   · · · ·  ## · ## ·
        #   · · · ·  · · · ·
        {
            "g1": (1, 1),
            "g2": (5, 5),
            "target": (3, 3),
            "walls": {(0,0),(2,0),(0,2),(3,1),(3,5),(6,6),(4,6),(6,4),(0,4),(6,2)},
        },

        # ── Puzzle 2  (6 moves, 14 walls, wall ESSENTIAL) ─────────
        # G1(2,1) and G2(6,5). Asymmetric — NO SOLUTION without walls.
        # Dense maze with many pinning surfaces.
        # Solution: UP DOWN DOWN RIGHT DOWN RIGHT
        #   UP pins G2 against edge, DOWN×2 advances both,
        #   RIGHT+DOWN+RIGHT weaves through walls to converge.
        #
        #   ## · · · · ## · ·
        #   · · G1 ## · · · ·
        #   · · · ·  RR · ## ·
        #   · · · ## · · · ·
        #   ## · · ·  ## ## · ·
        #   · · · ·  · · G2 ·
        #   ## · · ## · ## ## ·
        #   ## · · ·  · · ## ·
        {
            "g1": (2, 1),
            "g2": (6, 5),
            "target": (4, 2),
            "walls": {(0,0),(5,0),(0,4),(3,1),(6,2),(3,3),(4,4),(5,4),(0,6),(3,6),(5,6),(6,6),(0,7),(6,7)},
        },

        # ── Puzzle 3  (5 moves, 13 walls, wall ESSENTIAL) ─────────
        # G1(1,1) and G2(5,5). Asymmetric — NO SOLUTION without walls.
        # G2 gets pinned twice by walls at (6,4)/(7,4) on RIGHT moves,
        # letting G1 catch up.
        # Solution: DOWN RIGHT RIGHT DOWN RIGHT
        #
        #   ## ## · · · · · ·
        #   · G1 · ## ## · · ·
        #   · · · ·  · · ## ##
        #   · · · ·  RR · ## ·
        #   · · · ·  ## · ## ##
        #   · · · ·  · G2 · ·
        #   · ## ## · · · · ·
        #   ## · · ·  · · · ·
        {
            "g1": (1, 1),
            "g2": (5, 5),
            "target": (4, 3),
            "walls": {(0,0),(1,0),(3,1),(4,1),(4,4),(6,2),(7,2),(6,3),(6,4),(7,4),(1,6),(2,6),(0,7)},
        },

        # ── Puzzle 4  (8 moves, 16 walls, wall ESSENTIAL) ─────────
        # G1(2,0) and G2(6,5). Asymmetric — NO SOLUTION without walls.
        # The fortress: heavily walled grid with rich pinning.
        # G1 gets pinned 3× going DOWN (wall at (1,1) blocks),
        # then G1 gets pinned 4× going RIGHT while G2 catches up,
        # then final DOWN converges both blocks.
        # Solution: DOWN DOWN DOWN RIGHT RIGHT RIGHT RIGHT DOWN
        #
        #   · · G1 · ## · ## ·
        #   · ## · ·  · ## · ·
        #   · · · ·  · · ## ·
        #   · · · ## ## · · ·
        #   · · RR ## · ## ## ·
        #   · · · ·  · · G2 ##
        #   · ## · ·  · · ## ·
        #   · ## · ·  · ## · ##
        {
            "g1": (2, 0),
            "g2": (6, 5),
            "target": (2, 4),
            "walls": {(1,1),(1,6),(1,7),(3,3),(3,4),(4,0),(4,3),(5,1),(5,4),(5,7),(6,0),(6,2),(6,4),(6,6),(7,5),(7,7)},
        },
    ]

    def _setup_level_6(self, w: int, h: int):
        # Pick a puzzle from the curated library based on seed.
        puzzles = self._LEVEL6_PUZZLES
        idx = self._rng.randint(0, len(puzzles) - 1)
        puzzle = puzzles[idx]

        self._grid = self._blank_grid(w, h, C_BLACK)

        wall_positions = set()
        for wx, wy in puzzle["walls"]:
            if self._in_bounds(wx, wy, w, h):
                self._grid[wy][wx] = C_DARK_GRAY
                wall_positions.add((wx, wy))
        self._extra["wall_positions"] = wall_positions

        # Place green block 1 (main cursor)
        g1x, g1y = puzzle["g1"]
        self._cursor_x = g1x
        self._cursor_y = g1y

        # Place green block 2 (mirror cursor)
        g2x, g2y = puzzle["g2"]
        self._extra["mirror_x"] = g2x
        self._extra["mirror_y"] = g2y

        # Place red destination block
        tx, ty = puzzle["target"]
        self._grid[ty][tx] = C_RED
        self._extra["target_x"] = tx
        self._extra["target_y"] = ty

        # Verify solvability (should always pass for curated puzzles)
        assert self._bfs_mirror_solvable(
            w, h, wall_positions,
            self._cursor_x, self._cursor_y,
            self._extra["mirror_x"], self._extra["mirror_y"],
            tx, ty,
        ), f"Level 6 puzzle {idx} is not solvable! This is a bug."

    def _step_level_6(self):
        action = self.action
        dx, dy = self._get_dir(action.id)
        if dx == 0 and dy == 0:
            return

        self._save_state()
        w, h = self.current_level.grid_size
        wall_positions = self._extra["wall_positions"]

        # Move main cursor normally
        mnx = self._cursor_x + dx
        mny = self._cursor_y + dy
        if self._in_bounds(mnx, mny, w, h) and (mnx, mny) not in wall_positions:
            self._cursor_x = mnx
            self._cursor_y = mny

        # Move mirror cursor in OPPOSITE direction
        mirror_x = self._extra["mirror_x"]
        mirror_y = self._extra["mirror_y"]
        mrnx = mirror_x - dx
        mrny = mirror_y - dy
        if self._in_bounds(mrnx, mrny, w, h) and (mrnx, mrny) not in wall_positions:
            self._extra["mirror_x"] = mrnx
            self._extra["mirror_y"] = mrny

        self._render_grid()

        # Win: both cursors on the single red target
        tx = self._extra["target_x"]
        ty = self._extra["target_y"]
        if (self._cursor_x == tx and self._cursor_y == ty and
                self._extra["mirror_x"] == tx and self._extra["mirror_y"] == ty):
            self.next_level()

    # ==================================================================
    #  LEVEL 7 — Sokoban (10×10)
    #
    #  Hidden rule: Classic Sokoban with 2 blocks. Walk into a block
    #  to push it one step. Push each colored block onto its matching
    #  target marker. Blocks can't be pulled. Plan carefully!
    #
    #  Uses 2 block-target pairs to keep it manageable but challenging.
    #  Blocks are placed with clear push paths to targets.
    #
    #  Controls: Arrow keys only.
    #  Difficulty: ★★★★★ Very Hard.
    # ==================================================================
    def _setup_level_7(self, w: int, h: int):
        self._grid = self._blank_grid(w, h, C_BLACK)

        used = set()
        wall_positions = set()

        # Place border walls with gaps for open feel
        for x in range(w):
            if self._rng.random() < 0.4:
                self._grid[0][x] = C_DARK_GRAY
                wall_positions.add((x, 0))
                used.add((x, 0))
            if self._rng.random() < 0.4:
                self._grid[h - 1][x] = C_DARK_GRAY
                wall_positions.add((x, h - 1))
                used.add((x, h - 1))
        for y in range(h):
            if self._rng.random() < 0.4:
                self._grid[y][0] = C_DARK_GRAY
                wall_positions.add((0, y))
                used.add((0, y))
            if self._rng.random() < 0.4:
                self._grid[y][w - 1] = C_DARK_GRAY
                wall_positions.add((w - 1, y))
                used.add((w - 1, y))

        # Some interior walls
        num_walls = self._rng.randint(6, 10)
        for _ in range(num_walls):
            attempts = 0
            while attempts < 50:
                wx = self._rng.randint(1, w - 2)
                wy = self._rng.randint(1, h - 2)
                if (wx, wy) not in used:
                    self._grid[wy][wx] = C_DARK_GRAY
                    wall_positions.add((wx, wy))
                    used.add((wx, wy))
                    break
                attempts += 1

        self._extra["wall_positions"] = wall_positions

        # Cursor in top-left area
        cx, cy = 1, 1
        self._grid[cy][cx] = C_BLACK
        wall_positions.discard((cx, cy))
        used.add((cx, cy))
        self._cursor_x = cx
        self._cursor_y = cy

        # TWO block-target pairs
        block_target_pairs = [
            (C_RED, C_BROWN),       # red block → brown target
            (C_BLUE, C_TEAL),       # blue block → teal target
        ]

        target_positions = {}

        for i in range(2):
            bc, tc = block_target_pairs[i]

            # Place target
            tx, ty = 0, 0
            attempts = 0
            while attempts < 200:
                tx = self._rng.randint(2, w - 3)
                ty = self._rng.randint(2, h - 3)
                if (tx, ty) not in used:
                    break
                attempts += 1
            self._grid[ty][tx] = tc
            target_positions[(tx, ty)] = bc
            used.add((tx, ty))

            # Place block with a clear push path to target
            placed = False
            directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
            self._rng.shuffle(directions)
            for ddx, ddy in directions:
                dist = self._rng.randint(2, 4)
                bx = tx + ddx * dist
                by = ty + ddy * dist
                if (self._in_bounds(bx, by, w, h) and (bx, by) not in used):
                    path_clear = True
                    for step in range(1, dist):
                        px = tx + ddx * step
                        py = ty + ddy * step
                        if not self._in_bounds(px, py, w, h) or (px, py) in wall_positions:
                            path_clear = False
                            break
                    if path_clear:
                        self._grid[by][bx] = bc
                        used.add((bx, by))
                        placed = True
                        break

            if not placed:
                attempts = 0
                while attempts < 100:
                    bx = self._rng.randint(1, w - 2)
                    by = self._rng.randint(1, h - 2)
                    if (bx, by) not in used:
                        self._grid[by][bx] = bc
                        used.add((bx, by))
                        break
                    attempts += 1

        self._extra["block_colors"] = {bp[0] for bp in block_target_pairs}
        self._extra["target_colors"] = {bp[1] for bp in block_target_pairs}
        self._extra["target_positions"] = target_positions
        self._extra["original_targets"] = dict(target_positions)

    def _step_level_7(self):
        action = self.action
        dx, dy = self._get_dir(action.id)
        if dx == 0 and dy == 0:
            return

        self._save_state()
        w, h = self.current_level.grid_size
        wall_positions = self._extra["wall_positions"]
        block_colors = self._extra["block_colors"]
        target_colors = self._extra["target_colors"]
        original_targets = self._extra["original_targets"]

        nx = self._cursor_x + dx
        ny = self._cursor_y + dy

        if not self._in_bounds(nx, ny, w, h):
            return

        if (nx, ny) in wall_positions:
            return

        cell = self._grid[ny][nx]

        if cell in block_colors:
            # Push the block
            push_x = nx + dx
            push_y = ny + dy

            if not self._in_bounds(push_x, push_y, w, h):
                return
            if (push_x, push_y) in wall_positions:
                return
            push_dest = self._grid[push_y][push_x]
            if push_dest in block_colors or push_dest == C_DARK_GRAY:
                return  # blocked

            block_color = cell

            # Clear old position (restore target if needed)
            if (nx, ny) in original_targets:
                self._grid[ny][nx] = original_targets[(nx, ny)]
            else:
                self._grid[ny][nx] = C_BLACK

            # Place block at new position
            self._grid[push_y][push_x] = block_color

            # Move cursor
            self._cursor_x = nx
            self._cursor_y = ny

        elif cell == C_BLACK or cell in target_colors:
            # Normal move
            self._cursor_x = nx
            self._cursor_y = ny
        else:
            return

        self._render_grid()

        # Win: every target has its matching block
        all_matched = True
        for (tx, ty), expected_bc in original_targets.items():
            if self._grid[ty][tx] != expected_bc:
                all_matched = False
                break
        if all_matched:
            self.next_level()
