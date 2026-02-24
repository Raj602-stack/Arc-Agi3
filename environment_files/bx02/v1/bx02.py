# boxxle v2 — sokoban with step limits and lives

from typing import Dict, List, Optional, Set, Tuple

import numpy as np
from arcengine import (
    ARCBaseGame,
    Camera,
    GameAction,
    Level,
    RenderableUserDisplay,
    Sprite,
)

# ============================================================
# Color Constants (ARC palette indices)
# ============================================================
C_PLAYER = 14       # Lime/Green
C_WALL = 10         # Light Blue
C_BOX = 7           # Orange
C_GOAL = 4          # Yellow
C_COIN = 12         # Pink (collectible point)
C_FLASH = 11        # White (step-limit flash)

BACKGROUND_COLOR = 0
PADDING_COLOR = 5

# ============================================================
# Sprite Templates
# ============================================================
sprites = {
    "player": Sprite(
        pixels=[[C_PLAYER]], name="player",
        visible=True, collidable=True, tags=["player"], layer=3,
    ),
    "wall": Sprite(
        pixels=[[C_WALL]], name="wall",
        visible=True, collidable=True, tags=["wall"], layer=1,
    ),
    "box": Sprite(
        pixels=[[C_BOX]], name="box",
        visible=True, collidable=True, tags=["box"], layer=2,
    ),
    "goal": Sprite(
        pixels=[[C_GOAL]], name="goal",
        visible=True, collidable=False, tags=["goal"], layer=0,
    ),
    "coin": Sprite(
        pixels=[[C_COIN]], name="coin",
        visible=True, collidable=False, tags=["coin"], layer=0,
    ),
    "flash": Sprite(
        pixels=[[C_FLASH]], name="flash",
        visible=False, collidable=False, layer=10,
    ),
}

# ============================================================
# Level Grid Definitions
# ============================================================
# Legend:
#   # = wall   . = floor   P = player   B = box
#   G = goal   C = coin (collectible point)

LEVEL_GRIDS = [
    # ----------------------------------------------------------
    # Level 1 (8x8) — 2 boxes, 2 goals
    # ----------------------------------------------------------
    (
        "########\n"
        "#......#\n"
        "#.B.G..#\n"
        "#...B..#\n"
        "#......#\n"
        "#....G.#\n"
        "#P.....#\n"
        "########"
    ),
    # ----------------------------------------------------------
    # Level 2 (10x10) — 3 boxes, 3 goals
    # ----------------------------------------------------------
    (
        "##########\n"
        "#........#\n"
        "#.....G..#\n"
        "#...B....#\n"
        "#.....G..#\n"
        "#..BB....#\n"
        "#.....G..#\n"
        "#........#\n"
        "#P.......#\n"
        "##########"
    ),
    # ----------------------------------------------------------
    # Level 3 (12x12) — 5 boxes, 5 goals, wall obstacles
    # ----------------------------------------------------------
    (
        "############\n"
        "#..........#\n"
        "#...B...G..#\n"
        "#.B........#\n"
        "#.B.####G..#\n"
        "#.......G..#\n"
        "#...####...#\n"
        "#.......G..#\n"
        "#.......G..#\n"
        "#....BB....#\n"
        "#P.........#\n"
        "############"
    ),
    # ----------------------------------------------------------
    # Level 4 (14x14) — 3 boxes, 3 goals, 3 coins
    # Boxes must pass through coins to reach goals.
    # ----------------------------------------------------------
    (
        "##############\n"
        "#............#\n"
        "#..B...B..G..#\n"
        "#............#\n"
        "#.......C....#\n"
        "#.....C...G..#\n"
        "#............#\n"
        "#............#\n"
        "#..B..C...G..#\n"
        "#............#\n"
        "#.....B......#\n"
        "#.........G..#\n"
        "#..P.........#\n"
        "##############"
    ),
    # ----------------------------------------------------------
    # Level 5 (16x16) — 3 boxes, 3 goals, 5 coins, walls
    # More coins and wall barriers between rows.
    # ----------------------------------------------------------
    (
        "################\n"
        "#..............#\n"
        "#....C......G..#\n"
        "#..B...........#\n"
        "#..B..####.....#\n"
        "#....C.........#\n"
        "#...........G..#\n"
        "#..............#\n"
        "#.....####.....#\n"
        "#..............#\n"
        "#..B...C....G..#\n"
        "#..............#\n"
        "#......C.......#\n"
        "#........C.....#\n"
        "#..P...........#\n"
        "################"
    ),
    # ----------------------------------------------------------
    # Level 6 (20x20) — 3 boxes, 3 goals, complex rooms
    # Vertical wall with gaps only on box rows, plus
    # horizontal wall segments creating a maze-like feel.
    # ----------------------------------------------------------
    (
        "####################\n"
        "#........#.........#\n"
        "#..B.....#...C.....#\n"
        "#........#.......G.#\n"
        "#........#.........#\n"
        "#........#.........#\n"
        "#.####...#...####..#\n"
        "#........#.........#\n"
        "#...C....#.........#\n"
        "#................G.#\n"
        "#........#.........#\n"
        "#........#.........#\n"
        "#.####B..#...####..#\n"
        "#........#.........#\n"
        "#........#.........#\n"
        "#..B.....#.......G.#\n"
        "#......C.#.........#\n"
        "#........#.........#\n"
        "#..P.....#.........#\n"
        "####################"
    ),
    # ----------------------------------------------------------
    # Level 7 (24x24) — 4 boxes, 4 goals, large complex maze
    # Vertical wall with gaps on box rows, horizontal wall
    # segments on both sides creating multi-room structure.
    # ----------------------------------------------------------
    (
        "########################\n"
        "#..........#...........#\n"
        "#..........#...........#\n"
        "#..B.......#....C....G.#\n"
        "#..........#...........#\n"
        "#..........#...........#\n"
        "#.#####.#.C###..#####..#\n"
        "#..........#...........#\n"
        "#..B.......#.........G.#\n"
        "#..........#...........#\n"
        "#..........#...........#\n"
        "#..........#...........#\n"
        "#.#####....#...C#####..#\n"
        "#..........#...........#\n"
        "#..B.......C.........G.#\n"
        "#..........#...........#\n"
        "#..........#...........#\n"
        "#.#####....#....#####..#\n"
        "#..........#...........#\n"
        "#..B.......#.........G.#\n"
        "#..........#...........#\n"
        "#..........#...........#\n"
        "#..P.......#...........#\n"
        "########################"
    ),
]

# Max steps allowed per level (stored in Level.data, ~2.5x baseline)
_LEVEL_MAX_STEPS = [30, 60, 95, 130, 170, 250, 350]

# ============================================================
# Grid Parsing
# ============================================================
_CHAR_MAP = {
    "#": "wall",
    "P": "player",
    "B": "box",
    "G": "goal",
    "C": "coin",
}


def _parse_grid(grid_str: str, data: Optional[Dict] = None) -> Level:
    """Parse an ASCII grid string into a Level with positioned sprites."""
    rows = grid_str.split("\n")
    height = len(rows)
    width = max(len(row) for row in rows)

    level_sprites: List[Sprite] = []
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            key = _CHAR_MAP.get(ch)
            if key:
                level_sprites.append(sprites[key].clone().set_position(x, y))

    return Level(sprites=level_sprites, grid_size=(width, height), data=data or {})


def _build_levels() -> List[Level]:
    """Build all game levels from grid definitions."""
    return [
        _parse_grid(grid, {"max_steps": ms})
        for grid, ms in zip(LEVEL_GRIDS, _LEVEL_MAX_STEPS)
    ]


# ============================================================
# Camera Sizes per Level (width, height)
# ============================================================
_CAMERA_SIZES = [
    (8, 8),       # Level 1
    (10, 10),     # Level 2
    (12, 12),     # Level 3
    (14, 14),     # Level 4
    (16, 16),     # Level 5
    (20, 20),     # Level 6
    (24, 24),     # Level 7
]


# ============================================================
# Step / Lives HUD  (like ls20's jvq RenderableUserDisplay)
# ============================================================
class StepDisplay(RenderableUserDisplay):
    """Renders a step-countdown bar and lives indicator on the
    64x64 output frame, following the same pattern as ls20."""

    BAR_WIDTH = 42
    BAR_X = 4
    BAR_Y = 61

    def __init__(self, game: "Bx02") -> None:
        self._game = game
        self.max_steps: int = 0
        self.remaining: int = 0

    # -- ls20-style helpers (match jvq interface) --

    def set_limit(self, max_steps: int) -> None:
        """Set max steps and reset remaining (like jvq.rzt + opw)."""
        self.max_steps = max_steps
        self.remaining = max_steps

    def tick(self) -> bool:
        """Decrement remaining by 1. Return False when exhausted
        (like jvq.pca)."""
        if self.remaining > 0:
            self.remaining -= 1
        return self.remaining > 0

    def reset(self) -> None:
        """Reset remaining to max (like jvq.opw)."""
        self.remaining = self.max_steps

    # -- rendering --

    def render_interface(self, frame: np.ndarray) -> np.ndarray:
        """Draw step bar + lives on the final 64x64 frame."""
        if self.max_steps == 0 or self._game._flash_active:
            return frame

        # Step bar (proportional fill)
        filled = int(self.BAR_WIDTH * self.remaining / self.max_steps)
        for i in range(self.BAR_WIDTH):
            color = 11 if i < filled else 5   # white = remaining, gray = used
            frame[self.BAR_Y: self.BAR_Y + 2, self.BAR_X + i] = color

        # Lives (up to 3, shown as cyan blocks on the right)
        for i in range(3):
            x = 52 + i * 4
            color = 8 if self._game._lives > i else 5
            frame[self.BAR_Y: self.BAR_Y + 2, x: x + 2] = color

        return frame


# ============================================================
# Game Class
# ============================================================
class Bx02(ARCBaseGame):
    """Boxxle V2 — Sokoban with step limits and lives.

    The player pushes boxes onto goal tiles across 7 progressively
    harder levels. Levels 1-3 increase the number of boxes. Levels
    4-5 introduce collectible coins. Levels 6-7 feature complex
    multi-room map structures. Every level has a maximum step count;
    exceeding it costs a life and resets the level. Lose all 3 lives
    and the game is over.
    """

    def __init__(self, seed: int = 0) -> None:
        levels = _build_levels()
        self._step_display = StepDisplay(self)
        self._lives: int = 3
        self._flash_active: bool = False

        camera = Camera(
            0, 0,
            _CAMERA_SIZES[0][0], _CAMERA_SIZES[0][1],
            BACKGROUND_COLOR, PADDING_COLOR,
            [self._step_display],
        )
        super().__init__(
            game_id="bx02",
            levels=levels,
            camera=camera,
            available_actions=[1, 2, 3, 4],
            seed=seed,
        )

    # --------------------------------------------------------
    # Step-limit loader  (like ls20.krg)
    # --------------------------------------------------------
    def _load_step_limit(self) -> None:
        """Read max_steps from current level data and configure display."""
        ms = self.current_level.get_data("max_steps")
        if ms:
            self._step_display.set_limit(ms)

    # --------------------------------------------------------
    # Level Initialization
    # --------------------------------------------------------
    def on_set_level(self, level: Level) -> None:
        """Cache sprite references and initialize per-level state."""
        idx = min(self._current_level_index, len(_CAMERA_SIZES) - 1)
        cw, ch = _CAMERA_SIZES[idx]
        self.camera.width = cw
        self.camera.height = ch

        # Sprite caches
        self._player: Sprite = self.current_level.get_sprites_by_tag("player")[0]
        self._boxes: List[Sprite] = list(self.current_level.get_sprites_by_tag("box"))
        self._goals: List[Sprite] = list(self.current_level.get_sprites_by_tag("goal"))
        self._walls: List[Sprite] = list(self.current_level.get_sprites_by_tag("wall"))
        self._coins: List[Sprite] = list(self.current_level.get_sprites_by_tag("coin"))
        self._collected_coins: Set[int] = set()
        self._removed_coins: List[Sprite] = []

        # Save initial positions for level reset
        self._init_player_pos: Tuple[int, int] = (self._player.x, self._player.y)
        self._init_box_positions: List[Tuple[int, int]] = [
            (b.x, b.y) for b in self._boxes
        ]

        # Step limit (read from Level data, like ls20.krg)
        self._load_step_limit()

        # Lives — 3 per level (like ls20.lbq)
        self._lives = 3

        # Flash overlay sprite (like ls20.egb / krg)
        self._flash_sprite: Sprite = sprites["flash"].clone()
        self.current_level.add_sprite(self._flash_sprite)
        self._flash_sprite.set_visible(False)
        self._flash_active = False

    # --------------------------------------------------------
    # Level Reset  (like ls20 reset block in step)
    # --------------------------------------------------------
    def _restore_level(self) -> None:
        """Put player, boxes and coins back to their starting state."""
        self._player.set_position(*self._init_player_pos)
        for box, (x, y) in zip(self._boxes, self._init_box_positions):
            box.set_position(x, y)
        for coin in self._removed_coins:
            coin.set_visible(True)
            self.current_level.add_sprite(coin)
            self._coins.append(coin)
        self._removed_coins.clear()
        self._collected_coins.clear()

    # --------------------------------------------------------
    # Spatial Queries
    # --------------------------------------------------------
    def _find_at(
        self, x: int, y: int, sprite_list: List[Sprite]
    ) -> Optional[Sprite]:
        """Return the first sprite from *sprite_list* at (x, y), or None."""
        for s in sprite_list:
            if s.x == x and s.y == y:
                return s
        return None

    def _is_blocked(self, x: int, y: int) -> bool:
        """True if (x, y) is blocked by a wall."""
        return self._find_at(x, y, self._walls) is not None

    # --------------------------------------------------------
    # Coin Collection
    # --------------------------------------------------------
    def _collect_coin_at(self, x: int, y: int) -> None:
        """If a coin exists at (x, y), collect it."""
        coin = self._find_at(x, y, self._coins)
        if coin and id(coin) not in self._collected_coins:
            self._collected_coins.add(id(coin))
            coin.set_visible(False)
            self.current_level.remove_sprite(coin)
            self._coins.remove(coin)
            self._removed_coins.append(coin)

    # --------------------------------------------------------
    # Win Condition
    # --------------------------------------------------------
    def _check_win(self) -> bool:
        """True when every goal has a box and all coins are collected."""
        if len(self._coins) > 0:
            return False
        for goal in self._goals:
            box = self._find_at(goal.x, goal.y, self._boxes)
            if not box:
                return False
        return True

    # --------------------------------------------------------
    # Main Step  (mirrors ls20.step structure)
    # --------------------------------------------------------
    def step(self) -> None:
        """Process one player action (move / push)."""

        # ---- flash recovery (like ls20 self.xhp block) ----
        if self._flash_active:
            self._flash_sprite.set_visible(False)
            self._flash_active = False
            self.complete_action()
            return

        # ---- parse direction ----
        dx, dy = 0, 0
        if self.action.id == GameAction.ACTION1:
            dy = -1  # Up
        elif self.action.id == GameAction.ACTION2:
            dy = 1   # Down
        elif self.action.id == GameAction.ACTION3:
            dx = -1  # Left
        elif self.action.id == GameAction.ACTION4:
            dx = 1   # Right
        else:
            self.complete_action()
            return

        px, py = self._player.x, self._player.y
        nx, ny = px + dx, py + dy

        # ---- collision checks ----
        if self._is_blocked(nx, ny):
            self.complete_action()
            return

        box = self._find_at(nx, ny, self._boxes)
        if box:
            bx, by = nx + dx, ny + dy
            if self._is_blocked(bx, by):
                self.complete_action()
                return
            if self._find_at(bx, by, self._boxes):
                self.complete_action()
                return
            box.set_position(bx, by)
            self._collect_coin_at(bx, by)

        # ---- move player ----
        self._player.set_position(nx, ny)

        # ---- win check ----
        if self._check_win():
            self.next_level()
            self.complete_action()
            return

        # ---- step countdown (like ls20 self.ggk.pca block) ----
        if not self._step_display.tick():
            self._lives -= 1
            if self._lives <= 0:
                self.lose()
                self.complete_action()
                return

            # Flash + auto-reset (like ls20 egb + xhp)
            self._flash_sprite.set_visible(True)
            self._flash_sprite.set_scale(64)
            self._flash_sprite.set_position(0, 0)
            self._flash_active = True
            self._restore_level()
            self._step_display.reset()
            return  # no complete_action — show flash frame first

        self.complete_action()
